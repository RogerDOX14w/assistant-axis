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


def _run(tmp_path: Path, fail_on: str | None, *extra: str) -> tuple[int, list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    uv_log = tmp_path / "uv.log"
    fake_uv = bin_dir / "uv"
    fake_uv.write_text(
        "#!/bin/bash\n"
        'echo "$*" >> "$UV_LOG"\n'
        + (f'case "$*" in *"{fail_on}"*) echo "{fail_on} failed" >&2; exit 1;; esac\n' if fail_on else "")
        + "exit 0\n")
    fake_uv.chmod(0o755)
    out_dir = tmp_path / "out"
    # The log redirection ``exec > >(tee -a "$LOG_FILE") 2>&1`` writes through
    # /dev/fd, which Claude Code's Bash sandbox refuses; run a copy without it
    # (everything else is the script as committed).
    text = SCRIPT.read_text()
    tee_line = 'exec > >(tee -a "$LOG_FILE") 2>&1'
    assert tee_line in text
    script = tmp_path / "run_pipeline.sh"
    script.write_text(text.replace(tee_line, ": # (log redirection removed for the test)"))
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "UV_LOG": str(uv_log),
        "HOME": str(tmp_path / "home"),
        "HF_HOME": str(tmp_path / "hf"),
        "TMPDIR": str(tmp_path),
    }
    proc = subprocess.run(
        ["bash", str(script), "--output_dir", str(out_dir), "--types", "traits",
         "--no-tmpfs", "--skip-gpu-check", "--no-scan", *extra],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    calls = uv_log.read_text().splitlines() if uv_log.exists() else []
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


def test_every_parallel_step_sets_pipefail():
    """Static guard: a new ``( ... | sed ... ) &`` line without pipefail
    would bring the masking back."""
    lines = [ln.strip() for ln in SCRIPT.read_text().splitlines()
             if "| sed -u" in ln and ln.strip().endswith("&")]
    assert lines, "expected the parallel step lines"
    assert all(ln.startswith("( set -o pipefail;") for ln in lines), lines
