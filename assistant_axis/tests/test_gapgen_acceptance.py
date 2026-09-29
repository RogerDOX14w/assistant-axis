"""Recorded-output acceptance tests for the trait-gap platform.

They read saved outputs under ``data/candidates/`` and **skip** when a file
is absent, so they pass before the paid runs and bite after them.

M1: the pilot (``filter/m1_pilot``) must meet the mechanical gates (parse
rate >= 99%, usage.json present, cost recorded).  The full validation run
(``filter/m1_validation``, plan §9 task 10, not run yet) must meet the same
mechanical gates and produce ``corpus_regions.json`` covering every trait
file.  Its three quality figures are recorded against their targets and
reported as a warning; they do not fail (decision 2 of decisions_m1.md).
"""
import json
import warnings
from pathlib import Path

import pytest

from assistant_axis.gapgen.paths import CORPUS_REGIONS_PATH, DATA_DIR, filter_dir

PILOT = filter_dir("m1_pilot")
FULL = filter_dir("m1_validation")


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


def test_full_stability_rerun():
    p = filter_dir("m1_stability") / "summary.json"
    if not p.exists():
        pytest.skip("stability rerun not recorded yet")
    a = {r["key"]: r["filter"]["verdict"] for r in _results(FULL) if r["filter"]}
    b = {r["key"]: r["filter"]["verdict"] for r in _results(filter_dir("m1_stability")) if r["filter"]}
    common = set(a) & set(b)
    assert len(common) >= 200
    assert sum(a[k] == b[k] for k in common) / len(common) >= 0.90


def test_corpus_regions_cover_every_trait_file():
    if not CORPUS_REGIONS_PATH.exists():
        pytest.skip("corpus_regions.json not written yet (task 10)")
    obj = json.loads(CORPUS_REGIONS_PATH.read_text())
    regions = obj.get("result", obj)
    stems = {p.stem for p in (DATA_DIR / "traits" / "instructions").glob("*.json")}
    assert stems <= set(regions)
