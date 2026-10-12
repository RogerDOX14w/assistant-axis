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


def test_coherence_at_exactly_the_threshold_is_too_high(tmp_path: Path) -> None:
    """Regression (2026-10-12, walk-through D11): the runner stops UP on
    strength_mean_coh >= 1.5, so a start at exactly 1.5 is TOO_HIGH.  The
    tool used > 1.5 and graded it TOO_LOW (eff 0) or GOOD (eff >= 1/3)."""
    cell = tmp_path / "s0_l49_+1"
    _records(cell, {1.0: (1.5, 0.0), 2.0: (1.5, 1.0), 3.0: (1.49, 1.0)})
    rec = cell / "records.jsonl"
    assert ass._analyse_cell(rec, 1, 1.0)["category"] == "TOO_HIGH"
    assert ass._analyse_cell(rec, 1, 2.0)["category"] == "TOO_HIGH"
    assert ass._analyse_cell(rec, 1, 3.0)["category"] == "GOOD"


def test_effect_at_exactly_the_threshold_is_not_too_low(tmp_path: Path) -> None:
    """The runner's DOWN stop counts |mean(eff)| < 1/3 only."""
    cell = tmp_path / "s0_l25_+1"
    _records(cell, {1.0: (0.0, ass.EFF_STOP), 2.0: (0.0, -0.3)})
    rec = cell / "records.jsonl"
    assert ass._analyse_cell(rec, 1, 1.0)["category"] == "GOOD"
    assert ass._analyse_cell(rec, 1, 2.0)["category"] == "TOO_LOW"


def test_thresholds_match_the_runner_defaults() -> None:
    """COH_STOP / EFF_STOP are run_steering_cell's defaults (read from the
    source, so the test does not import torch)."""
    import ast
    src = (_REPO_ROOT / "assistant_axis" / "steering_runner.py").read_text()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "run_steering_cell")
    args = fn.args.args + fn.args.kwonlyargs
    defaults = dict(zip([a.arg for a in fn.args.args][-len(fn.args.defaults):],
                        fn.args.defaults))
    defaults.update({a.arg: d for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults)
                     if d is not None})
    assert {a.arg for a in args} >= {"coh_stop_threshold", "eff_stop_threshold"}

    def value(node):
        return eval(compile(ast.Expression(node), "<default>", "eval"), {})  # noqa: S307

    assert value(defaults["coh_stop_threshold"]) == ass.COH_STOP
    assert value(defaults["eff_stop_threshold"]) == ass.EFF_STOP
