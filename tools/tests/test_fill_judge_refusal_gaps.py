"""Tests for tools/fill_judge_refusal_gaps.py: the scan path only (no API
calls; a synthetic judge dir and allowlist under tmp_path)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import fill_judge_refusal_gaps as fjr  # noqa: E402

JUDGE = "claude-sonnet-4-5"


def _judge_dir(tmp_path: Path, gaps: dict) -> Path:
    d = tmp_path / "x_vs_y" / "sonnet"
    d.mkdir(parents=True)
    (d / "config.json").write_text(json.dumps({"args": {"judge_model": JUDGE}}))
    (d / "gaps.json").write_text(json.dumps(gaps))
    (d / "scores_descriptions.json").write_text(json.dumps({"other|T": 1}))
    (d / "scores_instructions.json").write_text(json.dumps({"other|T": 1}))
    return d


def _allowlist(tmp_path: Path) -> Path:
    p = tmp_path / "allowlist.json"
    p.write_text(json.dumps({"_schema_version": 1, "judge_refusals": {JUDGE: {
        "virus|R": {"added_at": "2026-05-13", "reason": "r",
                    "fallback_judge": "claude-haiku-4-5-20251001",
                    "fallback_provider": "anthropic",
                    "modes": ["descriptions", "instructions"]}}}}))
    return p


@pytest.fixture(autouse=True)
def _no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """A scan never needs API keys; fail loudly if it tries to load them."""
    def _boom() -> None:
        raise AssertionError(".env must not be read on a scan")
    monkeypatch.setattr(fjr, "_load_env", _boom)


def test_scan_with_unexpected_gap_exits_2(tmp_path: Path, capsys) -> None:
    """Regression (2026-10-12): ``--scan`` printed the unexpected-gap
    banner but exited 0, so an automated check passed."""
    d = _judge_dir(tmp_path, {"descriptions": ["virus|R", "patient|R"]})
    rc = fjr.main(["--scan", "--dir", str(d), "--allowlist", str(_allowlist(tmp_path))])
    captured = capsys.readouterr()
    assert rc == 2
    assert "WOULD FILL: x_vs_y / descriptions / virus|R" in captured.out
    assert "patient|R" in captured.err


def test_scan_with_only_allowlisted_gaps_exits_0(tmp_path: Path, capsys) -> None:
    d = _judge_dir(tmp_path, {"instructions": ["virus|R"]})
    rc = fjr.main(["--scan", "--dir", str(d), "--allowlist", str(_allowlist(tmp_path))])
    assert rc == 0
    assert "WOULD FILL" in capsys.readouterr().out


def test_fill_mode_with_only_unexpected_gaps_exits_2_without_calls(
    tmp_path: Path, capsys,
) -> None:
    """No allowlisted job: nothing to fill, so no client and no .env; the
    unexpected gaps give exit 2 (it was 1, the code for failed fills)."""
    d = _judge_dir(tmp_path, {"descriptions": ["patient|R"]})
    rc = fjr.main(["--dir", str(d), "--allowlist", str(_allowlist(tmp_path))])
    assert rc == 2


def test_gaps_already_in_cache_are_not_reported(tmp_path: Path, capsys) -> None:
    d = _judge_dir(tmp_path, {"descriptions": ["other|T"]})
    rc = fjr.main(["--scan", "--dir", str(d), "--allowlist", str(_allowlist(tmp_path))])
    assert rc == 0
    assert "No gaps found" in capsys.readouterr().out
