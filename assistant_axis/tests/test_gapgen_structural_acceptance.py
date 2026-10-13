"""Structural generators: acceptance on the recorded outputs (coding_plan_09 section 8, the last bullet).  Each check
skips while what it reads is absent (no paid run has been made yet in a fresh checkout); the hard ones fail once it
is there: parse rate >= 0.99 in every run's responses, the null-rate pilot inside the 5-40% band for retarget and
remode under the current prompt, the stability median >= 0.5 on 30 traits, ``usage.json`` beside every run with a
call, ``evaluation.json`` carrying every figure the plan names, a position row for every trait operated on, and the
readouts' headline and novel figures.  The package imports no ``openai`` beyond the embedding cache."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators import structural as S
from assistant_axis.gapgen.generators.structural import evaluate as E
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural.postprocess import collect_replies, load_operator_table
from assistant_axis.gapgen.generators.structural.sidetable import load_position_table
from assistant_axis.gapgen.paths import DATA_CANDIDATES, REPO_ROOT

RUNS = DATA_CANDIDATES / "runs" / S.GENERATOR


def _run_dirs():
    return sorted(p for p in RUNS.glob("*") if p.is_dir()) if RUNS.exists() else []


def _paid_runs():
    return [d for d in _run_dirs() if (d / S.RESPONSES_NAME).exists()]


def test_package_imports_no_openai_beyond_the_embedding_cache():
    pkg = REPO_ROOT / "assistant_axis" / "gapgen" / "generators" / "structural"
    cli = REPO_ROOT / "data_analysis" / "gap_generation" / "structural_generator.py"
    for p in [*pkg.glob("*.py"), cli]:
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import openai|from openai)", text, re.M), p.name


def test_parse_rate_in_every_run():
    runs = _paid_runs()
    if not runs:
        pytest.skip("no structural run with responses yet")
    for d in runs:
        recs = O.read_responses(d / S.RESPONSES_NAME)
        ops = [r for r in recs if r.get("stage") == O.STAGE]
        if ops:
            pr = E.parse_rate(ops)
            assert pr["rate"] >= E.PARSE_RATE_MIN, (d.name, pr)
        mod = [r for r in recs if r.get("stage") == "modernise"]
        if mod:
            from assistant_axis.gapgen.generators.structural.modernise import parse_modernise
            units = {}
            for r in mod:
                ok = parse_modernise(r.get("text"), ids=r.get("ids") or [])[0] is not None
                units[r["unit_id"]] = units.get(r["unit_id"], False) or ok
            assert sum(units.values()) / len(units) >= E.PARSE_RATE_MIN, (d.name, units)


def test_usage_json_beside_every_run_with_a_call():
    runs = _paid_runs()
    if not runs:
        pytest.skip("no structural run with responses yet")
    for d in runs:
        u = d / "usage.json"
        assert u.exists(), d.name
        assert json.loads(u.read_text(encoding="utf-8"))["n_calls"] > 0, d.name


def test_null_rate_pilot_inside_the_band_under_the_current_prompt():
    readouts = [d / "nullrate_readout.json" for d in _run_dirs() if (d / "nullrate_readout.json").exists()]
    if not readouts:
        pytest.skip("no null-rate pilot yet")
    current = sr.current_versions(None, ("structural_operators",))["structural_operators"][1]
    judged = 0
    for p in readouts:
        run = json.loads((p.parent / "run.json").read_text(encoding="utf-8"))
        shas = {(s.get("args") or {}).get("rubric", {}).get("sha256") for s in run.get("sessions") or []}
        if current not in shas:
            continue                                   # a pilot under an earlier prompt: a revision round's record
        judged += 1
        readout = json.loads(p.read_text(encoding="utf-8"))
        band = readout["null_rates"]["band"]
        assert band["pass"], (p.parent.name, band)
        if readout.get("coverage"):                    # readouts since review B2 (2026-10-13) record it
            assert readout["coverage"]["pass"], (p.parent.name, readout["coverage"])
    if not judged:
        pytest.skip("no null-rate pilot under the current prompt yet")


def _evaluation():
    ev = E.read_evaluation(S.EVALUATION_PATH)
    return ev


def test_stability_median():
    st = _evaluation().get("stability")
    if not st:
        pytest.skip("no stability run yet")
    assert st["n_traits"] >= 30 and st["jaccard_median"] >= E.STABILITY_MIN_MEDIAN, st
    if st.get("coverage"):                             # since review B2: answered in both runs, of the sample
        assert st["coverage"]["pass"], st["coverage"]


def test_evaluation_carries_every_figure():
    ev = _evaluation()
    if not ev.get("pair_recovery"):
        pytest.skip("no postprocessed evaluation yet")
    pr = ev["pair_recovery"]
    assert pr["n_pairs"] > 0 and pr["expected"] == 0.8 and "recall_stem" in pr
    sr_ = ev["structure_recovery"]
    assert sr_["triangles"]["n"] >= 1 and sr_["sequence"]["n"] >= 2
    qh = ev["queue_holdout"]
    hl = ev["holdout_lists"]
    assert qh["n"] == hl["counts"]["holdout"] and set(qh["by_operator"]) == set(O.OPERATORS)
    assert qh["rejected"]["n"] == hl["counts"]["rejected"] and "regenerated" in qh["rejected"]
    assert qh["accepted"]["n"] == hl["counts"]["accepted"] and qh["candidates"]["n"] == hl["counts"]["candidates"]
    table = load_operator_table(S.OPERATOR_TABLE_PATH)
    n_sources = sum(1 for r in table for s in r["sources"] if s.get("kind") == "principal_retarget")
    assert ev["principal"]["n_items"] == n_sources


def test_position_table_has_a_row_for_every_trait_operated_on():
    ev = _evaluation()
    rows = load_position_table(S.POSITION_TABLE_PATH)
    if not rows or not ev.get("runs"):
        pytest.skip("no side table yet")
    full, _ = collect_replies([RUNS / r for r in ev["runs"]])
    assert set(full) <= {r["stem"] for r in rows}


def test_reports_carry_the_headline_and_the_novel_figure_raw_and_net():
    reports = [d / "report.md" for d in _run_dirs() if (d / "report.md").exists()]
    if not reports:
        pytest.skip("no structural report yet")
    for p in reports:
        md = p.read_text(encoding="utf-8")
        assert "## Already registered (the headline)" in md, p
        assert re.search(r"\*\*\d+ raw\*\*, \*\*\d+ net\*\*", md), p
        assert md.index("Pair completions and degree fillers") < md.index("Wholly new concepts"), p
