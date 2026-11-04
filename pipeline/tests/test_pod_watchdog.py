"""pipeline/pod/watchdog.sh: the pod watchdog's decisions and its loop, run
for real with a fake stop command (``WATCHDOG_STOP_CMD``), the state in a
temporary ``WATCHDOG_DIR``, and the machine cues (SSH session, GPU process)
switched off so the test host's state cannot enter the decision.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipeline" / "pod" / "watchdog.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def wd(tmp_path: Path, *args: str, stop_cmd: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, WATCHDOG_DIR=str(tmp_path / "state"))
    stop_log = tmp_path / "stopped"
    env["WATCHDOG_STOP_CMD"] = stop_cmd if stop_cmd is not None else f"echo stopped >> {stop_log}"
    env.pop("RUNPOD_POD_ID", None)
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, cwd=tmp_path)


def arm(tmp_path: Path, *extra: str, idle_min: int = 1) -> subprocess.CompletedProcess:
    return wd(tmp_path, "arm", "--idle-min", str(idle_min), "--ignore-ssh", "--ignore-gpu", *extra)


def read_log(tmp_path: Path) -> str:
    p = tmp_path / "state" / "log"
    return p.read_text() if p.exists() else ""


def old_file(path: Path, minutes: int = 30) -> None:
    path.write_text("x")
    t = time.time() - minutes * 60
    os.utime(path, (t, t))


def test_arm_needs_idle_minutes_and_a_cue(tmp_path: Path) -> None:
    r = wd(tmp_path, "arm", "--watch", str(tmp_path))
    assert r.returncode == 2 and "--idle-min" in r.stderr
    r = wd(tmp_path, "arm", "--idle-min", "5")
    assert r.returncode == 2 and "needs a cue" in r.stderr
    assert not (tmp_path / "state" / "pid").exists()


def test_check_reads_the_write_cue(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    old_file(out / "old.jsonl")
    # Arm with a long poll so the loop does not act during the test; disarm at the end.
    r = arm(tmp_path, "--watch", str(out), "--every-sec", "3600", idle_min=10)
    assert r.returncode == 0, r.stderr
    try:
        r = wd(tmp_path, "check")
        assert r.returncode == 1 and r.stdout.strip() == "IDLE", (r.stdout, r.stderr)
        (out / "new.jsonl").write_text("y")
        r = wd(tmp_path, "check")
        assert r.returncode == 0 and r.stdout.startswith("BUSY: written:"), r.stdout
    finally:
        wd(tmp_path, "disarm")


def test_check_reads_pid_and_hold_cues(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    old_file(out / "old.jsonl")
    sleeper = subprocess.Popen(["sleep", "60"])
    pid_file = tmp_path / "run.pid"
    pid_file.write_text(f"{sleeper.pid}\n")
    try:
        r = arm(tmp_path, "--watch", str(out), "--pid-file", str(pid_file), "--every-sec", "3600", idle_min=10)
        assert r.returncode == 0, r.stderr
        r = wd(tmp_path, "check")
        assert r.returncode == 0 and f"pid alive: {sleeper.pid}" in r.stdout, r.stdout
        sleeper.terminate()
        sleeper.wait()
        r = wd(tmp_path, "check")
        assert r.returncode == 1, r.stdout
        # A hold keeps it busy; an expired hold does not.
        assert wd(tmp_path, "hold", "1").returncode == 0
        r = wd(tmp_path, "check")
        assert r.returncode == 0 and "hold until" in r.stdout, r.stdout
        (tmp_path / "state" / "hold").write_text(str(int(time.time()) - 10))
        r = wd(tmp_path, "check")
        assert r.returncode == 1, r.stdout
        assert wd(tmp_path, "release").returncode == 0
        assert not (tmp_path / "state" / "hold").exists()
    finally:
        if sleeper.poll() is None:
            sleeper.kill()
        wd(tmp_path, "disarm")


def test_loop_stops_the_pod_after_the_idle_window(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    old_file(out / "old.jsonl")
    # idle-min 1 with a 2-second poll: the loop sees IDLE at once, and the
    # window of 60 s would have to pass; shorten it by predating the idle
    # start through a 1-minute window and a stop command that records.
    r = arm(tmp_path, "--watch", str(out), "--every-sec", "2", idle_min=1)
    assert r.returncode == 0, r.stderr
    pid = int((tmp_path / "state" / "pid").read_text())
    try:
        deadline = time.time() + 75
        while time.time() < deadline and not (tmp_path / "stopped").exists():
            time.sleep(1)
        assert (tmp_path / "stopped").exists(), read_log(tmp_path)
        log = read_log(tmp_path)
        assert "STOPPING:" in log and "stop command sent" in log, log
        time.sleep(1)
        assert subprocess.run(["kill", "-0", str(pid)], capture_output=True).returncode != 0, "the loop should end"
    finally:
        subprocess.run(["kill", str(pid)], capture_output=True)


def test_dry_run_does_not_stop(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    old_file(out / "old.jsonl")
    r = arm(tmp_path, "--watch", str(out), "--every-sec", "2", "--dry-run", idle_min=1)
    assert r.returncode == 0, r.stderr
    pid = int((tmp_path / "state" / "pid").read_text())
    try:
        deadline = time.time() + 75
        while time.time() < deadline and "DRY RUN" not in read_log(tmp_path):
            time.sleep(1)
        log = read_log(tmp_path)
        assert "DRY RUN: would stop" in log, log
        assert not (tmp_path / "stopped").exists()
    finally:
        subprocess.run(["kill", str(pid)], capture_output=True)


def test_status_and_disarm(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    r = arm(tmp_path, "--watch", str(out), "--every-sec", "3600", idle_min=30)
    assert r.returncode == 0, r.stderr
    s = wd(tmp_path, "status").stdout
    assert "IDLE_MIN=30" in s and "loop: running" in s and "hold: none" in s, s
    r = wd(tmp_path, "disarm")
    assert r.returncode == 0 and "disarmed" in r.stdout
    s = wd(tmp_path, "status").stdout
    assert "loop: not running" in s, s


def test_rearming_replaces_the_loop(tmp_path: Path) -> None:
    out = tmp_path / "out"
    out.mkdir()
    assert arm(tmp_path, "--watch", str(out), "--every-sec", "3600", idle_min=30).returncode == 0
    first = int((tmp_path / "state" / "pid").read_text())
    try:
        assert arm(tmp_path, "--watch", str(out), "--every-sec", "3600", idle_min=45).returncode == 0
        second = int((tmp_path / "state" / "pid").read_text())
        assert first != second
        time.sleep(0.5)
        assert subprocess.run(["kill", "-0", str(first)], capture_output=True).returncode != 0
        assert "IDLE_MIN=45" in (tmp_path / "state" / "config").read_text()
    finally:
        wd(tmp_path, "disarm")
