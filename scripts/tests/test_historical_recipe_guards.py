"""The May 2026 rejudge/recompute recipes refuse to run unless asked to
(walk-through A1, review 10 D1, 2026-10-12).

* each of the four recipes exits 2 before doing anything unless
  ``HISTORICAL_RERUN=1``, and says why on stderr;
* ``rejudge_after_rubric_v2.sh`` moves the canonical files aside to
  ``<file>.bak.<ts>`` instead of deleting them;
* ``rejudge_after_trait_edits.sh`` requires ``--budget_usd`` and passes it to
  every orchestrator call.

The shell recipes run from a copy in ``tmp_path`` with a fake ``uv`` on
``PATH``: ``uv run python -c ...`` runs the real interpreter (the recipes read
their pair list that way), every other ``uv run python ...`` call is logged and
succeeds, so no judge, no network and nothing under the repository is touched.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
SHELL_RECIPES = (
    "rejudge_after_rubric_v2.sh",
    "rejudge_after_trait_edits.sh",
    "run_phase5a_recompute.sh",
)
PY_RECIPE = "run_phase5b_collision_rejudge.py"


def _sandbox(tmp_path: Path, script: str) -> tuple[Path, Path, dict]:
    """A copy of ``script`` under ``tmp_path/repo/scripts`` plus a fake uv.

    Returns (script copy, uv call log, env)."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    dst = repo / "scripts" / script
    shutil.copy2(SCRIPTS / script, dst)
    dst.chmod(dst.stat().st_mode | stat.S_IXUSR)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "uv_calls.log"
    fake = bindir / "uv"
    fake.write_text(
        "#!/bin/sh\n"
        '[ "$1" = run ] && shift\n'
        '[ "$1" = python ] && shift\n'
        f'if [ "$1" = "-c" ]; then exec "{sys.executable}" "$@"; fi\n'
        f'printf "%s\\n" "$*" >> "{log}"\n'
        "exit 0\n"
    )
    fake.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "HISTORICAL_RERUN"}
    env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
    return dst, log, env


def _cleanup_logs(stdout: str) -> None:
    """Remove the /tmp log dir a recipe announced with 'Logs: <dir>'."""
    m = re.search(r"^Logs: (/\S+)$", stdout, re.M)
    if m and Path(m.group(1)).name.startswith(("rejudge_", "phase5a_")):
        shutil.rmtree(m.group(1), ignore_errors=True)


@pytest.mark.parametrize("script", SHELL_RECIPES)
def test_shell_recipe_refuses_without_historical_rerun(tmp_path, script):
    dst, log, env = _sandbox(tmp_path, script)
    r = subprocess.run(["bash", str(dst), "--budget_usd", "5"], env=env,
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2, r.stderr
    assert "May 2026 record" in r.stderr
    assert "HISTORICAL_RERUN=1" in r.stderr
    assert r.stdout == ""                 # nothing ran: no "Logs:" line
    assert not log.exists()               # no uv call at all


@pytest.mark.parametrize("script", SHELL_RECIPES)
def test_shell_recipe_guard_wrong_value_still_refuses(tmp_path, script):
    dst, log, env = _sandbox(tmp_path, script)
    env["HISTORICAL_RERUN"] = "yes"
    r = subprocess.run(["bash", str(dst), "--budget_usd", "5"], env=env,
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
    assert not log.exists()


@pytest.mark.parametrize("script", SHELL_RECIPES + (PY_RECIPE,))
def test_guard_is_the_first_thing_in_the_file(script):
    """Top-of-file: nothing executable comes before the guard."""
    lines = (SCRIPTS / script).read_text().splitlines()
    if script.endswith(".py"):
        text = "\n".join(lines)
        guard = text.index('if __name__ == "__main__" and os.environ.get("HISTORICAL_RERUN")')
        # only the docstring, imports and the message constant precede it
        before = text[:guard]
        assert "def " not in before and "REPO =" not in before
        return
    code = [l for l in lines[1:] if l.strip() and not l.lstrip().startswith("#")]
    assert code[0].startswith('if [ "${HISTORICAL_RERUN:-}" != "1" ]; then')


def test_python_recipe_refuses_without_historical_rerun(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "HISTORICAL_RERUN"}
    r = subprocess.run([sys.executable, str(SCRIPTS / PY_RECIPE), "--dry_run"],
                       env=env, capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
    assert "May 2026 record" in r.stderr
    assert "[phase5b]" not in r.stderr    # main() never ran (no log lines)


def test_python_recipe_runs_with_historical_rerun_and_imports_cleanly(tmp_path):
    env = dict(os.environ, HISTORICAL_RERUN="1")
    r = subprocess.run([sys.executable, str(SCRIPTS / PY_RECIPE), "--dry_run",
                        "--axes", "no_such_axis"],
                       env=env, capture_output=True, text=True, cwd=tmp_path)
    # past the guard: main() runs and rejects the unknown axis (exit 2 from
    # main's own check, with its own message)
    assert "matched no v2 axes" in r.stderr
    # importing the module (no __main__) never trips the guard
    r2 = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util, sys; "
         f"s = importlib.util.spec_from_file_location('m', {str(SCRIPTS / PY_RECIPE)!r}); "
         "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); "
         "print(m.PER_CELL_BUDGET_USD)"],
        env={k: v for k, v in os.environ.items() if k != "HISTORICAL_RERUN"},
        capture_output=True, text=True, cwd=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert r2.stdout.strip() == "5.0"


# ---------------------------------------------------------------------------
# rejudge_after_rubric_v2.sh: snapshot instead of delete
# ---------------------------------------------------------------------------

def test_rubric_v2_moves_canonical_files_aside_instead_of_deleting(tmp_path):
    dst, log, env = _sandbox(tmp_path, "rejudge_after_rubric_v2.sh")
    env["HISTORICAL_RERUN"] = "1"
    root = tmp_path / "repo" / "roger" / "axis_judge_experiments"
    root.mkdir(parents=True)
    (root / "pair_list_responses.json").write_text(
        json.dumps([{"pos": "concise", "neg": "verbose"}]))
    subdirs = ("gpt_responses_traits_b10", "gpt_responses_roles_b10",
               "haiku_responses_traits_b10_q9", "haiku_responses_roles_b10_q9")
    canon = ("correlations.json", "gaps.json", "correlation_plot.png")
    for sd in subdirs:
        d = root / "concise_vs_verbose" / sd
        d.mkdir(parents=True)
        (d / "scores_responses__rubric_v1.json").write_text("{}")
        for f in canon:
            (d / f).write_text(f"today's {f} in {sd}")

    r = subprocess.run(["bash", str(dst)], env=env, capture_output=True,
                       text=True, cwd=tmp_path)
    try:
        assert r.returncode == 0, r.stdout + r.stderr
        assert "moved aside 12 canonical files" in r.stdout
        for sd in subdirs:
            d = root / "concise_vs_verbose" / sd
            for f in canon:
                assert not (d / f).exists()
                baks = sorted(d.glob(f"{f}.bak.*"))
                assert len(baks) == 1, (sd, f, list(d.iterdir()))
                assert re.fullmatch(re.escape(f) + r"\.bak\.\d{8}_\d{6}", baks[0].name)
                assert baks[0].read_text() == f"today's {f} in {sd}"
            # the pre-existing v1 snapshot rule still applies to gaps.json
            assert (d / "gaps__rubric_v1.json").read_text() == f"today's gaps.json in {sd}"
        # the four phases reached the (fake) orchestrator
        calls = log.read_text().splitlines()
        assert len(calls) == 4
        assert all("run_axis_experiment_batch.py" in c for c in calls)
    finally:
        _cleanup_logs(r.stdout)


# ---------------------------------------------------------------------------
# rejudge_after_trait_edits.sh: --budget_usd required and passed through
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("args", [[], ["--budget_usd"], ["--budget_usd", "0"],
                                  ["--budget_usd", "abc"], ["--budget", "5"]])
def test_trait_edits_requires_a_positive_budget(tmp_path, args):
    dst, log, env = _sandbox(tmp_path, "rejudge_after_trait_edits.sh")
    env["HISTORICAL_RERUN"] = "1"
    r = subprocess.run(["bash", str(dst), *args], env=env,
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
    assert "--budget_usd" in r.stderr
    assert not log.exists()


@pytest.mark.parametrize("args", [["--budget_usd", "7.5"], ["--budget_usd=7.5"]])
def test_trait_edits_passes_the_budget_to_every_phase(tmp_path, args):
    dst, log, env = _sandbox(tmp_path, "rejudge_after_trait_edits.sh")
    env["HISTORICAL_RERUN"] = "1"
    r = subprocess.run(["bash", str(dst), *args], env=env,
                       capture_output=True, text=True, cwd=tmp_path)
    try:
        assert r.returncode == 0, r.stdout + r.stderr
        calls = log.read_text().splitlines()
        assert len(calls) == 17           # 1 + 2x2 + 2x2 + 1 + 1 + 4 + 2 phases
        for c in calls:
            assert "run_axis_experiment_batch.py" in c
            assert "--budget_usd 7.5" in c
    finally:
        _cleanup_logs(r.stdout)
