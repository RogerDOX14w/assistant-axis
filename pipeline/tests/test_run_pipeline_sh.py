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
              ) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run a copy of the script with a fake ``uv``.

    ``fail_on``: the fake exits ``fail_rc`` for a call whose arguments contain
    it.  ``emit_on`` / ``emit``: the fake prints ``emit`` to stderr for a call
    containing ``emit_on`` (and still succeeds).  ``log_to_file``: keep the
    script's log file (redirected with a plain ``exec >>``, which the sandbox
    allows) so the end-of-run summary can be checked.  ``provide_steps``:
    place empty step scripts in the working directory, which the script
    requires since 2026-10-12."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv_log = tmp_path / "uv.log"
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        "#!/bin/bash\n"
        'echo "$*" >> "$UV_LOG"\n'
        + (f'case "$*" in *"{emit_on}"*) echo "{emit}" >&2;; esac\n' if emit_on else "")
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
    script = tmp_path / "run_pipeline.sh"
    script.write_text(text.replace(tee_line, replacement))
    if provide_steps:
        for name in STEP_SCRIPTS:
            (tmp_path / name).write_text("")
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "UV_LOG": str(uv_log),
        "HOME": str(tmp_path / "home"),
        "HF_HOME": str(tmp_path / "hf"),
        "TMPDIR": str(tmp_path),
    }
    args = ["bash", str(script), "--output_dir", str(out_dir), "--types", "traits",
            "--no-tmpfs", "--skip-gpu-check"]
    if not scan:
        args.append("--no-scan")
    proc = subprocess.run([*args, *extra], cwd=tmp_path, env=env, capture_output=True,
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


def test_christina_mode_gives_step_4_and_the_scan_the_same_min_count(tmp_path):
    """Step 4 used its own default (50) while the scan got MIN_COUNT (30), so
    entities with 30-49 score=3 samples were called re-run candidates."""
    proc, calls = _run_full(tmp_path, None, "--mode", "christina",
                            "--roles_dir", "../data/roles/instructions", scan=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    step4 = [c for c in calls if "4_vectors.py" in c]
    scan = [c for c in calls if "scan_missing_vectors.py" in c]
    assert len(step4) == 1 and len(scan) == 1
    assert "--min_count 50" in step4[0]
    assert "--min_count 50" in scan[0]


def test_scan_exit_3_is_reported_as_rerun_candidates(tmp_path):
    proc, calls = _run_full(tmp_path, "scan_missing_vectors.py", scan=True, fail_rc=3)
    assert any("scan_missing_vectors.py" in c for c in calls)
    assert proc.returncode == 0          # the scan never fails the pipeline
    assert "the scan found re-run candidates (exit 3)" in proc.stdout


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
