"""Recorded-output acceptance tests for the trait-gap platform.

They read saved outputs under ``data/candidates/`` and **skip** when a file
is absent, so they pass before the paid runs and bite after them.

M1: the pilot (``filter/m1_pilot``) must meet the mechanical gates (parse
rate >= 99%, usage.json present, cost recorded).  The full validation run
(``filter/m1_validation``, plan §9 task 10, not run yet) must meet the same
mechanical gates and produce ``corpus_regions.json`` covering every trait
file.  Its three quality figures are recorded against their targets and
reported as a warning; they do not fail (decision 2 of decisions_m1.md).

M2: mechanical gates on the calibration outputs; ``metric_config.json`` validates
and carries the decided settings; the gate is retrieval recall@10 >= 0.95 on the
M1-gloss queries for the configured setting (restated by Roger on 2026-10-02,
coding_plan_platform.md "M2 final settings and the M3 design" item 5), and the
threshold design's two old targets are reported as a warning.

The batch ids of the full run and of the stability rerun are read from the
environment, so a rerun under new ids is checked without editing this file:
``GAPGEN_FULL_BATCH`` (default ``m1_validation``) and
``GAPGEN_STABILITY_BATCH`` (default ``m1_stability``), for example::

    GAPGEN_FULL_BATCH=m1_validation_r2 GAPGEN_STABILITY_BATCH=m1_stability_r2 \\
        uv run python -m pytest assistant_axis/tests/test_gapgen_acceptance.py
"""
import json
import os
import warnings
from pathlib import Path

import pytest

from assistant_axis.gapgen.paths import CORPUS_REGIONS_PATH, DATA_DIR, filter_dir

PILOT = filter_dir("m1_pilot")
FULL_BATCH = os.environ.get("GAPGEN_FULL_BATCH", "m1_validation")
STABILITY_BATCH = os.environ.get("GAPGEN_STABILITY_BATCH", "m1_stability")
FULL = filter_dir(FULL_BATCH)


def _summary(d: Path) -> dict:
    p = d / "summary.json"
    if not p.exists():
        pytest.skip(f"{p} not recorded yet")
    obj = json.loads(p.read_text())
    return obj.get("result", obj)


def _results(d: Path) -> list[dict]:
    p = d / "results.jsonl"
    if not p.exists():
        pytest.skip(f"{p} not recorded yet")
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


@pytest.mark.parametrize("d", [PILOT, FULL], ids=["pilot", "full"])
def test_mechanical_gates(d):
    s = _summary(d)
    assert s["parse_rate"] >= 0.99
    assert not s.get("stopped_by_budget")
    usage = json.loads((d / "usage.json").read_text())
    assert usage["n_calls"] > 0 and usage["total_cost_usd"] == pytest.approx(s["cost_usd"], abs=1e-3)
    assert (d / "responses.jsonl").exists() and (d / "run.json").exists()


def quality_figures_report(results: list[dict]) -> dict:
    """The three M1 quality figures of the full run, measured against their
    targets (95% of existing labels correct, at least 4 of the 6 rejects
    flagged, at most 15% of random adjectives passed as traits).

    Decision 2 of decisions_m1.md (Roger, 2026-09-29): these are **recorded
    targets, not gates**.  The figures are computed, emitted as a warning
    (so they appear in the pytest summary) and returned; a missed target
    does not fail the test.  Only the mechanical checks above stay hard.
    """
    from assistant_axis.gapgen.filter import FilterResult, validation_figures

    rs = [FilterResult(key=r["key"], label=r["label"], stage=r["stage"], freq=r.get("freq") or {},
                       wordnet=r.get("wordnet") or {}, filter=r.get("filter"), holding=r.get("holding"),
                       meta=r.get("meta") or {}) for r in results]
    fig = validation_figures(rs)
    ex, rj, rn = fig["existing"], fig["rejects"], fig["oewn_random"]
    warnings.warn(
        f"M1 quality figures (targets, not gates): existing labels correct {ex['correct']}/{ex['n']} "
        f"= {ex['share']} (target {ex['target']}; met: {ex['meets_target']}); rejects flagged "
        f"{rj['flagged']}/{rj['n']} (target {rj['target']}; met: {rj['meets_target']}); random adjectives "
        f"trait {rn['trait']}/{rn['n']} = {rn['trait_share']} (target at most {rn['target']}; met: "
        f"{rn['meets_target']}); existing labels tagged state: {ex['labels_with_state']}; physical: "
        f"{ex['labels_with_physical']}", UserWarning, stacklevel=2)
    return fig


def test_full_quality_figures_recorded_not_gated():
    s = _summary(FULL)
    fig = quality_figures_report(_results(FULL))
    assert fig["existing"]["n"] == s["by_stratum"]["existing"]["n"]


def test_quality_figures_never_fail_on_a_missed_target():
    """Synthetic run that misses all three targets: recorded, not failed."""
    def r(label, stratum, verdict, tags=(), stage="classified"):
        return {"key": f"{label}#1", "label": label, "stage": stage, "holding": None,
                "meta": {"stratum": stratum},
                "filter": {"verdict": verdict, "tags": list(tags), "polysemy": False}}
    rows = [r("a", "existing", "reject", ["relational_only"]), r("b", "existing", "trait"),
            r("c", "rejects", "trait"), r("d", "oewn_random", "trait")]
    with pytest.warns(UserWarning, match="targets, not gates"):
        fig = quality_figures_report(rows)
    assert not fig["existing"]["meets_target"] and not fig["rejects"]["meets_target"]
    assert not fig["oewn_random"]["meets_target"]


def test_heldout_six_recorded_not_gated():
    """Round 3: the six September rejects, run once with their September
    descriptions as the intended meaning.  Target: ``overshadowed`` on at least
    four of six.  A recorded target: reported as a warning, never a failure."""
    from assistant_axis.gapgen.paths import plain_reading_dir
    from assistant_axis.gapgen.plain_reading import heldout_figure
    rows = _results(plain_reading_dir("m2rubric_r3_heldout"))
    fig = heldout_figure(rows)
    assert fig["n"] == 6
    warnings.warn(f"held-out six (targets, not gates): overshadowed on {fig['overshadowed']} of 6 "
                  f"({', '.join(fig['overshadowed_labels'])}); target {fig['target']}; "
                  f"meets target: {fig['meets_target']}")


def test_full_stability_rerun():
    """The stability rerun (``traithood_filter.py --stability``) against the
    full run: at least 200 rows compared and 90% verdict agreement, rows cut
    by the frequency floor left out (round 5, review_rubric_v2_fixes.md
    defect 2: they agree by construction)."""
    from assistant_axis.gapgen.filter import stability_agreement
    p = filter_dir(STABILITY_BATCH) / "summary.json"
    if not p.exists():
        pytest.skip("stability rerun not recorded yet")
    agr = stability_agreement(_results(FULL), _results(filter_dir(STABILITY_BATCH)))
    assert agr["n"] >= 200
    assert agr["share"] >= 0.90, agr["disagreements"]


def test_corpus_regions_cover_every_trait_file():
    if not CORPUS_REGIONS_PATH.exists():
        pytest.skip("corpus_regions.json not written yet (task 10)")
    obj = json.loads(CORPUS_REGIONS_PATH.read_text())
    regions = obj.get("result", obj)
    stems = {p.stem for p in (DATA_DIR / "traits" / "instructions").glob("*.json")}
    assert stems <= set(regions)


# --------------------------------------------------------------------------- M2 (calibration)

def _calibration(name: str) -> dict:
    from assistant_axis.gapgen.paths import CALIBRATION_DIR
    p = CALIBRATION_DIR / name
    if not p.exists():
        pytest.skip(f"{p} not recorded yet")
    obj = json.loads(p.read_text())
    return obj.get("result", obj)


def test_m2_mechanical_gates():
    """usage.json present and consistent with the run records; every requested model
    either ran or is recorded as failed; the tables and plots exist."""
    from assistant_axis.gapgen.paths import CALIBRATION_DIR, REPO_ROOT
    s = _calibration("summary.json")
    usage = json.loads((CALIBRATION_DIR / "usage.json").read_text())
    # usage.json is cumulative over runs.  The full calibration's summary carries its own and the cumulative
    # figure at the time; a later partial run (round 4's --round4, recorded in run_round4*.json, 2026-10-02)
    # adds to usage.json without rewriting the summary.  So usage.json equals the latest recorded cumulative
    # figure and is never below the summary's.  Task 19's --write-config (run_write_config.json) adds the
    # canary's calls the same way.
    later = sorted(CALIBRATION_DIR.glob("run_round*.json")) + sorted(CALIBRATION_DIR.glob("run_write_config.json"))
    recorded = [s["cost_usd_cumulative"]] + [json.loads(p.read_text()).get("cost_usd_cumulative", 0.0) for p in later]
    assert usage["total_cost_usd"] == pytest.approx(max(recorded), abs=1e-4)
    assert usage["total_cost_usd"] >= s["cost_usd_cumulative"] - 1e-4
    assert usage["total_cost_usd"] >= s["cost_usd"] - 1e-9
    assert s["models_run"]
    for png in s["pngs"]:
        assert (REPO_ROOT / png).exists()
    assert (CALIBRATION_DIR / "drop_or_merge.md").exists()
    assert "n_pairs" in s["drop_or_merge"]


def test_m2_contrast_criteria_all_present():
    """The contrast decision per model is recorded with all ten criteria present
    (ran, or skipped with a reason)."""
    abl = _calibration("contrast_ablation.json")
    for model, by_variant in abl.items():
        for variant, res in by_variant.items():
            assert set(res["criteria_status"]) == set("abcdefghij"), (model, variant)
            assert res["recommendation"]["recommendation"] in ("keep", "strip")


# M2 targets restated (Roger, 2026-10-02; coding_plan_platform.md, "M2 final settings and the M3 design" item 5):
# with the retrieve-then-judge design, the gate is retrieval recall@10 >= 0.95 on the M1-gloss queries for the
# configured setting; the threshold design's auc_dup_vs_distinct >= 0.85 and paraphrase_recall_top1 >= 0.95 are
# computed and reported as warnings, as the M1 quality figures are.

M1_GLOSS_SOURCES = ("m1_gloss_1", "m1_gloss_2")


def _configured_setting() -> tuple[str, str, str]:
    """(live arm, representation, variant) from metric_config.json, else the decided settings."""
    from assistant_axis.gapgen.calibrate import FINAL_SETTINGS
    from assistant_axis.gapgen.metric_config import MetricConfig
    from assistant_axis.gapgen.paths import METRIC_CONFIG_PATH
    if METRIC_CONFIG_PATH.exists():
        cfg = MetricConfig.load()
        return cfg.live_model["arm"], cfg.representation, cfg.space["variant"]
    c = FINAL_SETTINGS["covered"]
    return FINAL_SETTINGS["live"], c["representation"], c["variant"]


def test_m2_metric_config_validates():
    """metric_config.json validates against the schema and carries Roger's final settings."""
    from assistant_axis.gapgen.calibrate import FINAL_SETTINGS
    from assistant_axis.gapgen.metric_config import MetricConfig, validate_payload
    from assistant_axis.gapgen.paths import METRIC_CONFIG_PATH
    if not METRIC_CONFIG_PATH.exists():
        pytest.skip(f"{METRIC_CONFIG_PATH} not written yet")
    env = json.loads(METRIC_CONFIG_PATH.read_text())
    assert "_provenance" in env
    validate_payload(env["result"])
    cfg = MetricConfig.load()
    c, d = FINAL_SETTINGS["covered"], FINAL_SETTINGS["directional"]
    assert (cfg.representation, cfg.space["variant"], cfg.covered["metric"], cfg.k) == (
        c["representation"], c["variant"], c["metric"], c["k"])
    assert (cfg.directional["representation"], cfg.directional["space"]["variant"], cfg.directional["K"]) == (
        d["representation"], d["variant"], d["K"])
    assert cfg.live_model["arm"] == "openai" and cfg.fallback_model["arm"] == "gemma"
    assert cfg.fallback_model["active"] is False
    assert "bge" not in (cfg.live_model["arm"], cfg.fallback_model["arm"])
    assert cfg.thresholds["used_for_decisions"] is False
    assert cfg.covered["contrast"] == {"openai": "keep"}
    assert len(cfg.canary["texts"]) == 8 and cfg.canary["min_cosine"] == 0.999
    assert all(r["ok"] for r in cfg.canary.get("check_at_write", {}).values())


def test_m2_retrieval_recall_gate():
    """The restated gate: recall@10 >= 0.95 on each M1-gloss query source for the configured setting, read from
    retrieval_round4.json (and, once written, equal to what the config records)."""
    from assistant_axis.gapgen.paths import METRIC_CONFIG_PATH
    res = _calibration("retrieval_round4.json")
    arm, rep, var = _configured_setting()
    got = {r["source"]: r["recall"]["10"] for r in res["recall"]
           if (r["model"], r["representation"], r["variant"]) == (arm, rep, var) and r["source"] in M1_GLOSS_SOURCES}
    assert set(got) == set(M1_GLOSS_SOURCES)
    for src, v in got.items():
        assert v >= 0.95, (src, v)
    if METRIC_CONFIG_PATH.exists():
        from assistant_axis.gapgen.metric_config import MetricConfig
        tgt = MetricConfig.load().covered["retrieval"]["target"]
        assert tgt["met"] is True and tgt["values"] == pytest.approx(got)


def test_m2_targets_reported():
    """The threshold design's targets, computed for the configured setting and reported, not gated (plan item 5):
    auc_dup_vs_distinct >= 0.85 and paraphrase_recall_top1 >= 0.95 (round 3's 14-word paraphrases, no label)."""
    loo = _calibration("loo_metrics.json")
    para = _calibration("paraphrase_metrics.json")
    arm, rep, var = _configured_setting()
    auc = [r["auc_dup_vs_distinct"] for r in loo["rows"] if (r["model"], r["representation"], r["variant"], r["metric"])
           == (arm, rep, var, "cos")]
    top1 = [r["recall"]["cos"]["recall_at_1"] for r in para["recall_and_covered"]
            if (r["model"], r["representation"], r["variant"], r["query"]) == (arm, rep, var, "no_label_14w")]
    assert auc and top1
    warnings.warn(f"M2 old targets for the configured setting ({arm}, {rep}, {var}; reported, not gated): "
                  f"auc_dup_vs_distinct {auc[0]} (target 0.85; met: {auc[0] >= 0.85}); paraphrase_recall_top1 "
                  f"{top1[0]} (target 0.95; met: {top1[0] >= 0.95})")
