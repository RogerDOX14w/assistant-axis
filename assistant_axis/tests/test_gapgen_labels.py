"""Tests for assistant_axis/gapgen/labels.py (M2 task 12)."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import labels as L
from assistant_axis.gapgen.paths import REPO_ROOT

DATA = REPO_ROOT / "data"


def _trait(d: Path, stem, desc="This means x.", neg=None, arrangement=None, source=None):
    obj = {"positive_label": stem.replace("_", " "), "negative_label": neg or f"non-{stem}", "description": desc}
    if arrangement:
        obj["arrangement"] = arrangement
    if source:
        obj["source"] = source
    (d / "traits" / "instructions").mkdir(parents=True, exist_ok=True)
    (d / "traits" / "instructions" / f"{stem}.json").write_text(json.dumps(obj))


@pytest.fixture
def mini(tmp_path):
    d = tmp_path / "data"
    pair = lambda a, b: {"kind": "pair", "members": [a, b]}  # noqa: E731
    _trait(d, "calm", arrangement=pair("agitated", "calm"))
    _trait(d, "agitated", arrangement=pair("agitated", "calm"))
    _trait(d, "reserved")
    _trait(d, "detached")
    _trait(d, "honest", neg="dishonest")
    _trait(d, "dishonest", neg="honest")
    _trait(d, "lazy", neg="industrious")
    _trait(d, "industrious")  # one-way: not a reciprocal pair
    for s in ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10"):
        _trait(d, s)
    (d / "traits" / "trait_antonyms_v4.json").write_text(json.dumps({
        "honest": {"negative_label": "dishonest", "antonym_score": 5, "reasoning": "r"},
        "lazy": {"negative_label": "industrious", "antonym_score": 3, "reasoning": "r"},
        "reserved": {"negative_label": "nonexistent", "antonym_score": 5, "reasoning": "r"}}))
    log = tmp_path / "log.md"
    log.write_text("### aloof ↔ flirty\n- NEW aloof: This means being aloof: cool and distant.\n")
    queue = {"entries": [
        {"stem": "aloof", "label": "aloof", "entity_type": "trait", "status": "not_adopted", "partner": "flirty",
         "decision": "DELETED (Roger): aloof overlaps reserved and detached."},
        {"stem": "economic", "label": "economic", "entity_type": "trait", "status": "not_adopted",
         "description": "This means putting the economy first.",
         "decision": "DELETED: the description did not match the word (economic)."},
        {"stem": "grave", "label": "grave", "entity_type": "trait", "status": "not_adopted",
         "decision": "NOT SEEDED: duplicate of `calm`."},
        {"stem": "calm", "label": "calm", "entity_type": "trait", "status": "exists", "decision": "reserved"},
    ]}
    return d, queue, log


def test_seed_sources_and_relations(mini):
    d, queue, log = mini
    lp = L.build_labelled_pairs(d, queue, log, n_unrelated=20, k_folds=2)
    rel = {p.key(): p.relation for p in lp.pairs if p.relation != "unrelated"}
    assert rel[("agitated", "calm")] == "antonym"
    assert rel[("dishonest", "honest")] == "antonym"              # v4 at score 5
    assert ("industrious", "lazy") not in rel                       # v4 score 3 is below the filter
    assert rel[("queue:aloof", "reserved")] == "duplicate"          # pairing-review description
    assert rel[("detached", "queue:aloof")] == "duplicate"
    assert rel[("label:economic", "queue:economic")] == "polysemy_reject"
    assert lp.externals["queue:aloof"]["description"].startswith("This means being aloof")
    assert lp.externals["label:economic"]["description"] is None
    # grave has no text anywhere: excluded with a reason, not silently dropped
    assert any(x["a"] == "queue:grave" and "no description" in x["reason"] for x in lp.excluded)
    # with a filter gloss it becomes gloss:grave
    lp2 = L.build_labelled_pairs(d, queue, log, n_unrelated=0, k_folds=2,
                                 filter_glosses={"grave": "This means being serious."})
    assert any(p.key() == ("calm", "gloss:grave") for p in lp2.pairs)


def test_v4_filter_at_four(tmp_path, mini):
    d, *_ = mini
    got = L.load_v4_antonyms(d / "traits" / "trait_antonyms_v4.json", {"honest", "dishonest", "lazy", "industrious",
                                                                       "reserved"})
    assert got == [("honest", "dishonest", 5)]
    assert L.load_v4_antonyms(d / "traits" / "trait_antonyms_v4.json", {"lazy", "industrious"}, min_score=3) == [
        ("lazy", "industrious", 3)]


def test_decision_parser_on_sampled_decisions():
    stems = {"reserved", "detached", "submissive", "deferential", "blunt", "calibrated", "gluttonous", "indulgent",
             "heavy_drinker", "agitated", "temperamental", "effusive", "irascible", "flirty", "risk_averse", "solemn"}
    assert L.parse_decision_stems(
        "DELETED 2026-09-17 (Roger, item 14): flirty made a singleton; aloof overlaps reserved and detached.",
        stems, exclude=["aloof", "flirty"]) == ["reserved", "detached"]
    assert L.parse_decision_stems("DELETED 2026-09-23 (Roger): pair with sassy abandoned; area covered by "
                                  "submissive and deferential.", stems) == ["submissive", "deferential"]
    assert L.parse_decision_stems("near-duplicate of an existing trait (blunt / calibrated); file removed.",
                                  stems) == ["blunt", "calibrated"]
    got = L.parse_decision_stems("intemperate's real senses (immoderate in drink; harsh outbursts) are covered by "
                                 "gluttonous/indulgent/heavy_drinker and agitated/temperamental/effusive/irascible",
                                 stems)
    assert got == ["gluttonous", "indulgent", "heavy_drinker", "agitated", "temperamental", "effusive", "irascible"]
    assert L.parse_decision_stems("prefers the risk-averse option; duplicate of `solemn`", stems) == [
        "risk_averse", "solemn"]
    assert L.parse_decision_stems("", stems) == []


def test_unrelated_never_overlap_and_folds_never_split(mini):
    d, queue, log = mini
    lp = L.build_labelled_pairs(d, queue, log, n_unrelated=30, k_folds=3, seed=1)
    labelled = {p.key() for p in lp.pairs if p.relation != "unrelated"}
    unrelated = [p for p in lp.pairs if p.relation == "unrelated"]
    assert unrelated and not ({p.key() for p in unrelated} & labelled)
    assert len({p.key() for p in unrelated}) == len(unrelated)
    for p in lp.pairs:
        assert p.fold is not None
        assert lp.folds[p.a] == lp.folds[p.b] == p.fold


def test_group_folds_keeps_components_together():
    P = L.LabelledPair
    pairs = [P("a", "b", "antonym", "t"), P("b", "c", "near_distinct", "t"), P("d", "e", "duplicate", "t"),
             P("f", "g", "antonym", "t")]
    folds = L.group_folds(pairs, k=2, nodes=["h", "i"])
    assert folds["a"] == folds["b"] == folds["c"]
    assert folds["d"] == folds["e"] and folds["f"] == folds["g"]
    assert set(folds.values()) <= {0, 1} and {"h", "i"} <= set(folds)
    assert all(p.fold == folds[p.a] for p in pairs)


def test_curation_keep_only_add_exclude(mini):
    d, queue, log = mini
    cur = {"keep_only": {"queue:aloof": {"keep": {"reserved": {"uncertain": True}}, "reason": "only reserved"}},
           "add": [{"a": "queue:aloof", "b": "lazy", "relation": "near_distinct", "note": "test"}],
           "exclude": [{"a": "agitated", "b": "calm", "reason": "test exclusion"}]}
    lp = L.build_labelled_pairs(d, queue, log, curation=cur, n_unrelated=0, k_folds=2)
    rel = {p.key(): p for p in lp.pairs}
    assert rel[("queue:aloof", "reserved")].uncertain
    assert ("detached", "queue:aloof") not in rel
    assert rel[("lazy", "queue:aloof")].relation == "near_distinct"
    assert ("agitated", "calm") not in rel
    reasons = {(x["a"], x["b"]): x["reason"] for x in lp.excluded}
    assert reasons[("detached", "queue:aloof")] == "hand: only reserved"
    assert reasons[("agitated", "calm")] == "hand: test exclusion"


def test_json_round_trip(mini, tmp_path):
    d, queue, log = mini
    lp = L.build_labelled_pairs(d, queue, log, n_unrelated=10, k_folds=2)
    L.save(lp, tmp_path / "lp.json")
    env = json.loads((tmp_path / "lp.json").read_text())
    assert "_provenance" in env and env["result"]["counts"] == lp.counts()
    back = L.load(tmp_path / "lp.json")
    assert [p.key() for p in back.pairs] == [p.key() for p in lp.pairs]
    assert back.externals == lp.externals and back.folds == lp.folds


def test_real_corpus_has_at_least_100_reciprocal_pairs():
    lp = L.build_labelled_pairs(DATA, json.loads((DATA / "seed_queue.json").read_text()),
                                REPO_ROOT / "reports" / "seeding_log_2026-09.md", n_unrelated=0)
    n_pairs = sum(1 for p in lp.pairs if p.source == "arrangement_pair")
    assert n_pairs >= 100
    for p in lp.pairs:
        assert p.fold is not None


def test_recorded_labelled_pairs_file_is_consistent():
    """The committed labelled_pairs.json (if present) matches the curation's intent."""
    p = DATA / "candidates" / "calibration" / "labelled_pairs.json"
    if not p.exists():
        pytest.skip("labelled_pairs.json not built yet")
    lp = L.load(p)
    c = lp.counts()
    assert c.get("antonym", 0) >= 100 and c.get("duplicate", 0) >= 20 and c.get("unrelated", 0) >= 1000
    labelled = {q.key() for q in lp.pairs if q.relation != "unrelated"}
    assert not labelled & {q.key() for q in lp.pairs if q.relation == "unrelated"}
    for q in lp.pairs:
        assert lp.folds.get(q.a) == lp.folds.get(q.b) == q.fold
