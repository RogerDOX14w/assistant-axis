"""pipeline/run_pipeline.sh: a failed step 2 or step 3 stops the pipeline
before step 4 when the two run in parallel (the default).

Until 2026-10-12 each parallel step ran as ``( step 2>&1 | sed ... ) &``
without ``pipefail``, so the subshell's status was sed's, ``wait`` saw 0, and
the pipeline went on to step 4 with whatever step 2 or 3 had left behind
(pipeline/README.md promises that a batch-mode step 3 which leaves requests
unanswered "exits 1, so run_pipeline.sh stops before step 4").

The script runs for real with a fake ``uv`` on PATH that records each step
and fails the one named; no GPU, model or API is touched.  ``--no-tmpfs``
keeps the script away from the HF cache, and HOME / HF_HOME point into the
test's temporary directory.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipeline" / "run_pipeline.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


STEP_SCRIPTS = ("1_generate.py", "2_activations.py", "3_judge.py", "4_vectors.py", "5_axis.py")


def _run_full(tmp_path: Path, fail_on: str | None, *extra: str, scan: bool = False,
              fail_rc: int = 1, emit_on: str | None = None, emit: str = "",
              log_to_file: bool = False, provide_steps: bool = True,
              tmpfs: bool = False, workdir: Path | None = None, types: str | None = "traits",
              print_on: str | None = None, print_text: str = "",
              ) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run a copy of the script with a fake ``uv``.

    ``fail_on``: the fake exits ``fail_rc`` for a call whose arguments contain
    it.  ``emit_on`` / ``emit``: the fake prints ``emit`` to stderr for a call
    containing ``emit_on`` (and still succeeds).  ``log_to_file``: keep the
    script's log file (redirected with a plain ``exec >>``, which the sandbox
    allows) so the end-of-run summary can be checked.  ``provide_steps``:
    place empty step scripts in the working directory, which the script
    requires since 2026-10-12.  ``tmpfs``: leave out ``--no-tmpfs``.
    ``workdir``: where the script copy and step stubs go and the run's cwd
    (default ``tmp_path``)."""
    workdir = workdir or tmp_path
    workdir.mkdir(parents=True, exist_ok=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv_log = tmp_path / "uv.log"
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        "#!/bin/bash\n"
        'echo "$*" >> "$UV_LOG"\n'
        + (f'case "$*" in *"{emit_on}"*) echo "{emit}" >&2;; esac\n' if emit_on else "")
        + (f'case "$*" in *"{print_on}"*) echo "{print_text}";; esac\n' if print_on else "")
        + (f'case "$*" in *"{fail_on}"*) echo "{fail_on} failed" >&2; exit {fail_rc};; esac\n'
           if fail_on else "")
        + "exit 0\n")
    fake_uv.chmod(0o755)
    out_dir = tmp_path / "out"
    # The log redirection ``exec > >(tee -a "$LOG_FILE") 2>&1`` writes through
    # /dev/fd, which Claude Code's Bash sandbox refuses; run a copy without it
    # (everything else is the script as committed).
    text = SCRIPT.read_text()
    tee_line = 'exec > >(tee -a "$LOG_FILE") 2>&1'
    assert tee_line in text
    replacement = ('exec >> "$LOG_FILE" 2>&1' if log_to_file
                   else ": # (log redirection removed for the test)")
    script = workdir / "run_pipeline.sh"
    script.write_text(text.replace(tee_line, replacement))
    if provide_steps:
        for name in STEP_SCRIPTS:
            (workdir / name).write_text("")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "UV_LOG": str(uv_log),
        "HOME": str(tmp_path / "home"),
        "HF_HOME": str(tmp_path / "hf"),
        "TMPDIR": str(tmp_path),
    }
    args = ["bash", str(script), "--output_dir", str(out_dir), "--skip-gpu-check"]
    if types:
        args += ["--types", types]
    if not tmpfs:
        args.append("--no-tmpfs")
    if not scan:
        args.append("--no-scan")
    proc = subprocess.run([*args, *extra], cwd=workdir, env=env, capture_output=True,
                          text=True, timeout=120)
    calls = uv_log.read_text().splitlines() if uv_log.exists() else []
    return proc, calls


def _run(tmp_path: Path, fail_on: str | None, *extra: str) -> tuple[int, list[str]]:
    proc, calls = _run_full(tmp_path, fail_on, *extra)
    return proc.returncode, calls


def _step4_for_traits(calls: list[str]) -> bool:
    return any("4_vectors.py" in c and "/traits/activations" in c for c in calls)


def test_all_steps_succeeding_reaches_step_5(tmp_path):
    rc, calls = _run(tmp_path, fail_on=None)
    assert rc == 0
    assert _step4_for_traits(calls)
    assert any("5_axis.py" in c for c in calls)


@pytest.mark.parametrize("failing_step", ["step3", "step2"])
def test_a_failed_parallel_step_stops_before_step_4(tmp_path, failing_step):
    if failing_step == "step3":
        fail_on = "3_judge.py"
    else:
        # the per-type extraction, not the default's step-0 one (which runs
        # first, serially, and would stop the script before step 1)
        fail_on = f"--responses_dir {tmp_path / 'out' / 'traits' / 'responses'}"
    rc, calls = _run(tmp_path, fail_on=fail_on)
    assert any(fail_on in c for c in calls)        # the failing step did run
    assert any("3_judge.py" in c for c in calls) and any(
        "2_activations.py" in c and "/traits/responses" in c for c in calls)
    assert rc == 1
    assert not _step4_for_traits(calls)


def test_serial_mode_also_stops(tmp_path):
    rc, calls = _run(tmp_path, "3_judge.py", "--steps23serial")
    assert any("3_judge.py" in c for c in calls)
    assert rc != 0
    assert not _step4_for_traits(calls)


def test_a_failed_step_4_stops_before_step_5(tmp_path):
    """4_vectors.py exits 1 on an unreadable activation since 2026-10-12;
    the driver must not then compute an axis from the vectors that exist."""
    fail_on = f"--activations_dir {tmp_path / 'out' / 'traits' / 'activations'}"
    proc, calls = _run_full(tmp_path, fail_on)
    assert any(fail_on in c for c in calls)
    assert proc.returncode == 1
    assert not any("5_axis.py" in c for c in calls)
    assert "Pipeline aborted: Step 4 [traits] failed" in proc.stdout


def test_started_outside_pipeline_dir_fails_before_any_step(tmp_path):
    proc, calls = _run_full(tmp_path, None, provide_steps=False)
    assert proc.returncode == 1
    assert calls == []
    assert "cd pipeline && ./run_pipeline.sh" in proc.stderr


def _corpus(tmp_path: Path, *, role_default: bool = True) -> Path:
    """tmp/data/{roles,traits}/instructions beside a tmp/pipeline work dir, so
    that the driver's ../data/... defaults resolve; returns the work dir."""
    roles = tmp_path / "data" / "roles" / "instructions"
    traits = tmp_path / "data" / "traits" / "instructions"
    roles.mkdir(parents=True)
    traits.mkdir(parents=True)
    if role_default:
        (roles / "default.json").write_text("{}")
    (roles / "pirate.json").write_text("{}")
    (traits / "bold.json").write_text("{}")
    return tmp_path / "pipeline"


def test_christina_mode_gives_step_4_and_the_scan_the_same_min_count(tmp_path):
    """Step 4 used its own default (50) while the scan got MIN_COUNT (30), so
    entities with 30-49 score=3 samples were called re-run candidates."""
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/roles/instructions", scan=True,
                            workdir=_corpus(tmp_path), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    step4 = [c for c in calls if "4_vectors.py" in c]
    scan = [c for c in calls if "scan_missing_vectors.py" in c]
    assert len(step4) == 1 and len(scan) == 1
    assert "--min_count 50" in step4[0]
    assert "--min_count 50" in scan[0]


def test_christina_roles_run_generates_its_default_with_the_roles(tmp_path):
    """The roles directory has default.json: no separate step 0 (unchanged)."""
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/roles/instructions",
                            workdir=_corpus(tmp_path), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Step 0" not in proc.stdout
    assert not any("--roles default" in c for c in calls)


def test_christina_traits_run_takes_the_default_from_the_roles_directory(tmp_path):
    """P8.5 (2026-10-12): a christina run over traits had no default vector, so
    step 5 always failed; the default is now generated once under default/
    from the roles directory, with the christina settings."""
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/traits/instructions",
                            workdir=_corpus(tmp_path), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    gen_default = [c for c in calls if "1_generate.py" in c and "--roles default" in c]
    assert len(gen_default) == 1
    assert "--mode christina --roles_dir ../data/roles/instructions" in gen_default[0]
    assert str(tmp_path / "out" / "default" / "responses") in gen_default[0]
    assert any("2_activations.py" in c and "/default/responses" in c for c in calls)
    assert any("4_vectors.py" in c and "/default/activations" in c for c in calls)
    # the traits themselves are judged as traits
    assert any("3_judge.py --entity_type trait" in c for c in calls)


def test_christina_traits_run_symlinks_the_default_into_its_tree(tmp_path):
    out = tmp_path / "out"
    for sub, ext in (("responses", "jsonl"), ("activations", "pt"), ("vectors", "pt")):
        d = out / "default" / sub
        d.mkdir(parents=True)
        (d / f"default.{ext}").write_text(sub)
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/traits/instructions",
                            workdir=_corpus(tmp_path), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not any("--roles default" in c for c in calls)        # all three existed
    for sub, ext in (("responses", "jsonl"), ("activations", "pt"), ("vectors", "pt")):
        link = out / sub / f"default.{ext}"
        assert link.is_symlink() and link.read_text() == sub
        assert os.readlink(link) == f"../default/{sub}/default.{ext}"


def test_christina_traits_run_without_any_default_stops(tmp_path):
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/traits/instructions",
                            workdir=_corpus(tmp_path, role_default=False), types=None)
    assert proc.returncode == 1
    assert "step 5 needs a default" in proc.stderr
    assert calls == []


def test_tmpfs_mirror_goes_through_the_python_helper(tmp_path):
    """P8.6 (2026-10-12): one mirror implementation; the driver passes
    --tmpfs-method through and keeps HF_HOME when the helper prints nothing."""
    (tmp_path / "shm").mkdir()
    proc, calls = _run_full(tmp_path, None, "--tmpfs-dir", str(tmp_path / "shm" / "hf-cache"),
                            "--tmpfs-method", "cp", "--tmpdir", str(tmp_path), tmpfs=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    mirror = [c for c in calls if "tmpfs.py mirror" in c]
    assert mirror == [f"run python ../assistant_axis/tmpfs.py mirror --model Qwen/Qwen3-32B "
                      f"--tmpfs-hf-home {tmp_path / 'shm' / 'hf-cache'} "
                      f"--source-hf-home {tmp_path / 'hf'} --method cp"]
    assert "no tmpfs mirror" in proc.stdout
    assert calls.index(mirror[0]) < next(i for i, c in enumerate(calls) if "1_generate.py" in c)


def test_tmpfs_mirror_sets_hf_home_from_the_helper(tmp_path):
    (tmp_path / "shm").mkdir()
    proc, _ = _run_full(tmp_path, None, "--tmpfs-dir", str(tmp_path / "shm" / "hf-cache"),
                        "--tmpdir", str(tmp_path), tmpfs=True,
                        print_on="tmpfs.py mirror", print_text=str(tmp_path / "shm" / "hf-cache"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"[tmpfs] HF_HOME={tmp_path / 'shm' / 'hf-cache'}" in proc.stdout


def test_tmpfs_mirror_skipped_when_its_mount_is_missing(tmp_path):
    proc, calls = _run_full(tmp_path, None, "--tmpfs-dir", str(tmp_path / "noshm" / "hf-cache"),
                            "--tmpdir", str(tmp_path), tmpfs=True)
    assert proc.returncode == 0
    assert not any("tmpfs.py" in c for c in calls)
    assert "not present; no model mirror" in proc.stdout


def test_an_unknown_tmpfs_method_is_refused(tmp_path):
    proc, calls = _run_full(tmp_path, None, "--tmpfs-method", "scp")
    assert proc.returncode == 1
    assert "Invalid --tmpfs-method" in proc.stderr
    assert calls == []


def test_scan_exit_3_stops_before_step_5(tmp_path):
    """Re-run candidates stop the pipeline before the axis is built (Roger,
    2026-10-12: a stop, not a warning, which is easy to miss)."""
    proc, calls = _run_full(tmp_path, "scan_missing_vectors.py", scan=True, fail_rc=3)
    assert any("scan_missing_vectors.py" in c for c in calls)
    assert proc.returncode == 1
    assert "the scan found re-run candidates (exit 3)" in proc.stdout
    assert "Pipeline aborted: Scan failed" in proc.stdout
    assert not any("5_axis.py" in c for c in calls)


def test_scan_runs_between_step_4_and_step_5(tmp_path):
    proc, calls = _run_full(tmp_path, None, scan=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    names = [next((n for n in ("4_vectors.py", "scan_missing_vectors.py", "5_axis.py") if n in c), None)
             for c in calls]
    names = [n for n in names if n]
    assert names.index("4_vectors.py") < names.index("scan_missing_vectors.py") < names.index("5_axis.py")


def test_any_other_scan_failure_also_stops(tmp_path):
    proc, calls = _run_full(tmp_path, "scan_missing_vectors.py", scan=True, fail_rc=1)
    assert proc.returncode == 1
    assert "scanner exited 1" in proc.stdout
    assert not any("5_axis.py" in c for c in calls)


def test_no_scan_runs_step_5_without_a_scan(tmp_path):
    proc, calls = _run_full(tmp_path, None, scan=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not any("scan_missing_vectors.py" in c for c in calls)
    assert any("5_axis.py" in c for c in calls)


def test_end_of_run_summary_counts_step_4_errors(tmp_path):
    """Steps 4, 5 and the scan log "<time> [ERROR] <name>: ..."; the summary
    matched only steps 1-3's "<time> - ERROR - ..." before 2026-10-12."""
    line = "2026-10-12 01:02:03 [ERROR] pipeline.4_vectors: boom: unrecoverable load failure"
    proc, _ = _run_full(tmp_path, None, emit_on="4_vectors.py", emit=line, log_to_file=True)
    assert proc.returncode == 0
    logs = sorted((tmp_path / "out").glob("pipeline_*.log"))
    assert len(logs) == 1
    text = logs[0].read_text()
    assert "warning(s)/error(s) during pipeline run" in text
    summary = text.split("warning(s)/error(s) during pipeline run")[1]
    assert "boom: unrecoverable load failure" in summary


def test_every_parallel_step_sets_pipefail():
    """Static guard: a new ``( ... | sed ... ) &`` line without pipefail
    would bring the masking back."""
    lines = [ln.strip() for ln in SCRIPT.read_text().splitlines()
             if "| sed -u" in ln and ln.strip().endswith("&")]
    assert lines, "expected the parallel step lines"
    assert all(ln.startswith("( set -o pipefail;") for ln in lines), lines


def test_judge_batch_requests_reaches_step_3(tmp_path):
    """Several pods on one API key size step 3's chunks from the queue limit
    (walk-through P1, 2026-10-12)."""
    proc, calls = _run_full(tmp_path, None, "--judge-batch-requests", "3000")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    judge = [c for c in calls if "3_judge.py" in c]
    assert judge and all(c.endswith("--batch_requests 3000") for c in judge)


def test_judge_model_and_save_replies_reach_step_3(tmp_path):
    """The October role judging (Roger, 2026-10-28): version 10 with gpt-5.6-luna,
    replies saved for a later re-read."""
    proc, calls = _run_full(tmp_path, None, "--judge-model", "gpt-5.6-luna", "--judge-save-replies")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    judge = [c for c in calls if "3_judge.py" in c]
    assert judge and all(c.endswith("--judge_model gpt-5.6-luna --save_replies") for c in judge)
    assert "Judge:  gpt-5.6-luna, prompt version 10" in proc.stdout


def test_roger_mode_leaves_the_cut_off_marker_to_step_3s_default(tmp_path):
    """Step 3 marks a response cut at --max_tokens by default (Roger, 2026-10-28): roger mode
    passes nothing; --judge-no-mark-truncated turns it off."""
    proc, calls = _run_full(tmp_path, None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    judge = [c for c in calls if "3_judge.py" in c]
    assert judge and not any("mark_truncated" in c for c in judge)
    proc, calls = _run_full(tmp_path / "off", None, "--judge-no-mark-truncated")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    judge = [c for c in calls if "3_judge.py" in c]
    assert judge and all(c.endswith("--no_mark_truncated") for c in judge)


def test_christina_mode_judges_without_the_cut_off_marker(tmp_path):
    """Christina mode reproduces the paper's method: no marker (Roger, 2026-10-28), passed once
    even when --judge-no-mark-truncated is given too."""
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/roles/instructions", "--judge-no-mark-truncated",
                            workdir=_corpus(tmp_path), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    judge = [c for c in calls if "3_judge.py" in c]
    assert judge and all(c.count("--no_mark_truncated") == 1 for c in judge)
    proc, calls = _run_full(tmp_path / "plain", None, "--mode", "christina",
                            "--roles_dir", "../data/roles/instructions",
                            workdir=_corpus(tmp_path / "plain"), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    judge = [c for c in calls if "3_judge.py" in c]
    assert judge and all(c.endswith("--no_mark_truncated") for c in judge)


# ---------------------------------------------------------------------------
# Rubric versions and --from-step (2026-10-23)
# ---------------------------------------------------------------------------

def _default_vector(tmp_path: Path) -> Path:
    d = tmp_path / "out" / "default" / "vectors"
    d.mkdir(parents=True)
    (d / "default.pt").write_text("v")
    return d / "default.pt"


def test_the_drivers_default_version_is_step_3s():
    from assistant_axis.judge_rubrics import DEFAULT_PROMPT_VERSION
    assert f"JUDGE_PROMPT_VERSION_DEFAULT={DEFAULT_PROMPT_VERSION}\n" in SCRIPT.read_text()


def test_a_prompt_version_from_step_3_reruns_steps_3_to_5_into_its_own_dirs(tmp_path):
    _default_vector(tmp_path)
    proc, calls = _run_full(tmp_path, None, "--from-step", "3", "--judge-prompt-version", "4", scan=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = tmp_path / "out" / "traits"
    assert not any(s in c for c in calls for s in ("1_generate.py", "2_activations.py", "tmpfs.py"))
    [judge] = [c for c in calls if "3_judge.py" in c]
    assert f"--output_dir {out / 'scores_v4'}" in judge and judge.endswith("--prompt_version 4")
    [step4] = [c for c in calls if "4_vectors.py" in c]
    assert f"--scores_dir {out / 'scores_v4'}" in step4 and f"--output_dir {out / 'vectors_v4'}" in step4
    [step5] = [c for c in calls if "5_axis.py" in c]
    assert f"--vectors_dir {out / 'vectors_v4'} --output {out / 'axis_v4.pt'}" in step5
    assert any("scan_missing_vectors.py" in c for c in calls)
    link = out / "vectors_v4" / "default.pt"
    assert link.is_symlink() and os.readlink(link) == "../../default/vectors/default.pt"
    assert "prompt version 4 (into scores_v4/, vectors_v4/, axis_v4.pt)" in proc.stdout


def test_the_default_version_keeps_the_usual_dirs(tmp_path):
    # 10 since 2026-10-28 (3 before); version 3 now goes to its own directories
    proc, calls = _run_full(tmp_path, None, "--judge-prompt-version", "10")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = tmp_path / "out" / "traits"
    [judge] = [c for c in calls if "3_judge.py" in c]
    assert f"--output_dir {out / 'scores'} " in judge and judge.endswith("--prompt_version 10")
    assert any(f"--output {out / 'axis.pt'}" in c for c in calls if "5_axis.py" in c)
    proc, calls = _run_full(tmp_path / "v3", None, "--judge-prompt-version", "3")
    [judge] = [c for c in calls if "3_judge.py" in c]
    assert f"/traits/scores_v3 " in judge and judge.endswith("--prompt_version 3")
    # no flag: step 3 is not told a version, and takes its own default
    proc, calls = _run_full(tmp_path / "again", None)
    assert proc.returncode == 0 and not any("--prompt_version" in c for c in calls)


def test_from_step_3_needs_the_default_vector(tmp_path):
    proc, calls = _run_full(tmp_path, None, "--from-step", "3")
    assert proc.returncode == 1
    assert "--from-step 3 needs the default vector" in proc.stderr
    assert not any("3_judge.py" in c for c in calls)


@pytest.mark.parametrize("step,runs", [("4", ["4_vectors.py", "5_axis.py"]), ("5", ["5_axis.py"])])
def test_from_step_4_or_5(tmp_path, step, runs):
    _default_vector(tmp_path)
    proc, calls = _run_full(tmp_path, None, "--from-step", step)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ran = [s for s in STEP_SCRIPTS if any(s in c for c in calls)]
    assert ran == runs


def test_a_failed_step_3_from_step_3_stops_before_step_4(tmp_path):
    _default_vector(tmp_path)
    proc, calls = _run_full(tmp_path, "3_judge.py", "--from-step", "3")
    assert proc.returncode == 1
    assert "Pipeline aborted: Step 3 failed" in proc.stdout
    assert not any("4_vectors.py" in c for c in calls)


@pytest.mark.parametrize("args,message", [
    (("--from-step", "2"), "Invalid --from-step"),
    (("--judge-prompt-version", "v4"), "Invalid --judge-prompt-version"),
])
def test_bad_values_are_refused_before_any_step(tmp_path, args, message):
    proc, calls = _run_full(tmp_path, None, *args)
    assert proc.returncode == 1 and message in proc.stderr and calls == []


def test_christina_mode_from_step_3_with_a_version(tmp_path):
    out = tmp_path / "out"
    for sub, ext in (("responses", "jsonl"), ("activations", "pt"), ("vectors", "pt")):
        d = out / "default" / sub
        d.mkdir(parents=True)
        (d / f"default.{ext}").write_text(sub)
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/traits/instructions", "--from-step", "3",
                            "--judge-prompt-version", "0", scan=True,
                            workdir=_corpus(tmp_path), types=None)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not any(s in c for c in calls for s in ("1_generate.py", "2_activations.py"))
    [judge] = [c for c in calls if "3_judge.py" in c]
    assert f"--output_dir {out / 'scores_v0'}" in judge and judge.endswith("--prompt_version 0")
    [scan] = [c for c in calls if "scan_missing_vectors.py" in c]
    assert f"--vectors_dir {out / 'vectors_v0'}" in scan and f"--scores_dir {out / 'scores_v0'}" in scan
    assert any(f"--vectors_dir {out / 'vectors_v0'} --output {out / 'axis_v0.pt'}" in c
               for c in calls if "5_axis.py" in c)
    assert os.readlink(out / "vectors_v0" / "default.pt") == "../default/vectors/default.pt"
