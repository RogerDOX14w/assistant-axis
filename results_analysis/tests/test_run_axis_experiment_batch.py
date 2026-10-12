"""Regression tests for ``results_analysis/run_axis_experiment_batch.py``.

Review 2026-10-12:

* ``collect_summary`` read each ``correlations.json`` with a plain
  ``json.loads``.  Since Phase 6 those files are wrapped in a
  ``{"result": ..., "_provenance": ..., "schema_version": 2}`` envelope,
  so every current file contributed zero summary rows (plus warnings).
* ``main`` always exited 0, so the ``rejudge_after_*.sh`` orchestrators
  (which branch on its status under ``pipefail``) could not see pair runs
  that failed.
"""
from __future__ import annotations

import json
import sys

import results_analysis.run_axis_experiment_batch as mod

CORR = {
    "descriptions": {
        "3": {"raw": {"rho": 0.5, "p": 0.01, "n": 100},
              "whitened": {"rho": 0.6, "p": 0.001, "n": 100}},
    },
}


def _write_corr(root, axis, provider, obj):
    d = root / axis / provider
    d.mkdir(parents=True)
    (d / "correlations.json").write_text(json.dumps(obj))


def test_collect_summary_reads_enveloped_correlations(tmp_path):
    _write_corr(tmp_path, "aa_vs_bb", "gpt",
                {"result": CORR, "_provenance": {"inputs": []},
                 "schema_version": 2})
    _write_corr(tmp_path, "cc_vs_dd", "sonnet", CORR)  # legacy bare file
    records = mod.collect_summary(tmp_path, providers=("gpt", "sonnet"))
    got = sorted((r["pos"], r["provider"], r["metric"], r["rho"])
                 for r in records)
    assert got == [
        ("aa", "gpt", "raw", 0.5), ("aa", "gpt", "whitened", 0.6),
        ("cc", "sonnet", "raw", 0.5), ("cc", "sonnet", "whitened", 0.6),
    ]


def test_main_exits_nonzero_when_a_pair_fails(tmp_path, monkeypatch):
    pairs = tmp_path / "pairs.json"
    pairs.write_text(json.dumps([{"pos": "aa", "neg": "bb"},
                                 {"pos": "cc", "neg": "dd"}]))

    async def fake_run_one(pair, *a, **k):
        status = "FAIL (rc=2); see run.log" if pair["pos"] == "cc" else "OK (rc=0)"
        return (pair["pos"], pair["neg"], status, 0.0)

    # Pole vector files: the walk-through A2 check needs them before any run.
    data = tmp_path / "data"
    (data / "traits" / "vectors").mkdir(parents=True)
    for n in ("aa", "bb", "cc", "dd"):
        (data / "traits" / "vectors" / f"{n}.pt").write_bytes(b"")

    monkeypatch.setattr(mod, "run_one", fake_run_one)
    argv = ["run_axis_experiment_batch.py", "--pair_list", str(pairs),
            "--provider", "gpt", "--judge_model", "m",
            "--output_root", str(tmp_path / "out"), "--data_dir", str(data)]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 1

    async def ok_run_one(pair, *a, **k):
        return (pair["pos"], pair["neg"], "OK (rc=0)", 0.0)

    monkeypatch.setattr(mod, "run_one", ok_run_one)
    assert mod.main() == 0
