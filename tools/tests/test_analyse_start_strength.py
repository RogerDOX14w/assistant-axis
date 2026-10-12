"""Tests for tools/analyse_start_strength.py (synthetic cells only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import analyse_start_strength as ass  # noqa: E402


def _records(cell: Path, by_strength: dict) -> None:
    lines = []
    for s, (coh, eff) in by_strength.items():
        for q in range(3):
            lines.append(json.dumps({"strength": s, "sign": 1, "question_idx": q,
                                     "judges": {"coherence": {"score": coh},
                                                "effect": {"combined": eff}}}))
    cell.mkdir(parents=True)
    (cell / "records.jsonl").write_text("\n".join(lines) + "\n")


def test_cell_s_init_prefers_the_summary(tmp_path: Path) -> None:
    """Regression (2026-10-12): a cell started by the per-cell heuristic
    (no steps in the YAML) records its real s_init in summary.json; the
    config-derived value (steps default 2) is only a fallback."""
    cell = tmp_path / "s0_l25_+1"
    cell.mkdir()
    assert ass._cell_s_init(cell, 1.4137) == 1.4137            # no summary
    (cell / "summary.json").write_text(json.dumps({"s_init": 4.95}))
    assert ass._cell_s_init(cell, 1.4137) == 4.95
    (cell / "summary.json").write_text("{not json")
    assert ass._cell_s_init(cell, 1.4137) == 1.4137


def test_analyse_cell_grades_the_strength_nearest_the_start(tmp_path: Path) -> None:
    cell = tmp_path / "s0_l25_+1"
    _records(cell, {1.41: (0.0, 0.1), 4.95: (0.0, 1.0)})
    low = ass._analyse_cell(cell / "records.jsonl", 1, 1.41)
    high = ass._analyse_cell(cell / "records.jsonl", 1, 4.95)
    assert low["category"] == "TOO_LOW" and low["actual_strength"] == 1.41
    assert high["category"] == "GOOD" and high["actual_strength"] == 4.95
