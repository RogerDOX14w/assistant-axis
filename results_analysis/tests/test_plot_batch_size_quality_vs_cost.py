"""Regression test for the score-combine spec line in
``results_analysis/plot_batch_size_quality_vs_cost.py``.

Review 2026-10-12: the spec line hard-coded "0.6·gpt + 0.4·anthropic"
although ``judge_ensemble_rho_curve.py`` records the weight it used in
the ensembles side-car (``ensemble_combos["_meta"]["gpt_weight"]``), and
the current side-car was built at 0.625.
"""
from __future__ import annotations

import json

import results_analysis.plot_batch_size_quality_vs_cost as mod

RAW = {
    "cost_per_axis_usd": {"b10": 49.4, "b7": 52.1},
    "B_integer": {"b10": 10, "b7": 7},
    "grand_mean_per_b": {"b10": 0.70, "b7": 0.71},
}
SET = {"set_id": "set_1_initial", "rho_mean_best_cell": 0.70, "n_axes": 3}


def _ensembles(meta):
    combos = {"gpt_b10__plus_haiku_q9": {"per_set": [
        {"set_id": "set_1_initial", "rho_mean_best_cell": 0.72}]}}
    if meta is not None:
        combos["_meta"] = meta
    return {"ensemble_combos": combos,
            "gpt_only_b10_baseline": {"per_set": [SET]}}


def _spec_lines(tmp_path, monkeypatch, meta):
    captured = {}
    real = mod.suptitle_with_specs

    def spy(fig, title, spec, **kw):
        captured["spec"] = spec
        return real(fig, title, spec, **kw)

    monkeypatch.setattr(mod, "suptitle_with_specs", spy)
    inp = tmp_path / "curve.json"
    inp.write_text(json.dumps(RAW))
    mod.plot_quality_vs_cost(inp, tmp_path / "out.png", raw=RAW,
                             ensembles=_ensembles(meta))
    return captured["spec"]


def test_spec_reports_recorded_gpt_weight(tmp_path, monkeypatch):
    spec = _spec_lines(tmp_path, monkeypatch, {"gpt_weight": 0.625})
    combine = [s for s in spec if s.startswith("Score combine")]
    assert combine and "0.625·gpt + 0.375·anthropic" in combine[0]


def test_spec_keeps_historical_text_without_meta(tmp_path, monkeypatch):
    spec = _spec_lines(tmp_path, monkeypatch, None)
    combine = [s for s in spec if s.startswith("Score combine")]
    assert combine and "0.6·gpt + 0.4·anthropic" in combine[0]
