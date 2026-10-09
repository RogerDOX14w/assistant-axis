"""gapgen.promote: entry shape (round-trip through seed_entities), refusals,
partner hints, dry-run leaves the queue alone."""
import copy
import json

import pytest

import data_analysis.seed_entities as se
from assistant_axis.gapgen.promote import promote, queue_entry_from_record
from assistant_axis.gapgen.registry import new_record


def _rec(surface, *, verdict="trait", tags=(), holding=None, entity_type="trait", partner_hint=None,
         novelty=None, gloss="This means noticing the lever in every task and pulling it hard.", gen="wordnet_walk"):
    r = new_record(surface, sources=[{"generator": gen, "run_id": "r1", "rank": 1, "score": None,
                                      "source_ref": "oewn:1-a", "gloss_hint": None, "partner_hint": partner_hint,
                                      "surface": surface}])
    r["filter"] = {"verdict": verdict, "tags": list(tags), "reason": "A stable stance.", "senses": ["x"],
                   "region": "moral_stance", "rubric_version": 1}
    r["gloss"] = gloss
    r["holding"] = holding
    r["entity_type"] = entity_type
    r["novelty"] = novelty
    return r


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    for et in ("traits", "roles"):
        (d / et / "instructions").mkdir(parents=True)
    (d / "traits" / "instructions" / "stubborn.json").write_text(json.dumps({"positive_label": "stubborn"}))
    (d / "roles" / "instructions" / "pirate.json").write_text(json.dumps({"description": "x"}))
    return d


@pytest.fixture
def queue():
    return {"_meta": {}, "entries": [
        {"stem": "rationalizing", "label": "rationalizing", "entity_type": "trait", "status": "candidate"},
        {"stem": "aloof", "label": "aloof", "entity_type": "trait", "status": "not_adopted"}]}


def test_entry_shape_round_trips_through_seed_document(data_dir, queue):
    rec = _rec("world-shaping", tags=["state"])
    e = queue_entry_from_record(rec)
    assert e["stem"] == "world_shaping" and e["label"] == "world-shaping" and e["status"] == "candidate"
    assert e["entity_type"] == "trait" and e["description_draft"] == rec["gloss"] and e["description"] is None
    assert e["tags"] == ["gap_gen", "source:wordnet_walk", "state"]
    assert e["section"] == "trait-gap generators (2026-09)" and e["pairing"] == "singleton"
    assert e["gap_gen"]["registry_key"] == "world_shaping#1"
    # a reviewer writes the description and marks it ready; seed_entities then accepts it
    e2 = dict(e, description=e["description_draft"], status="ready")
    doc = se.seed_document(e2, {"entries": [e2]}, data_dir)
    assert doc["positive_label"] == "world-shaping" and doc["negative_label"] == "non-world-shaping"
    assert doc["description"] == rec["gloss"] and doc["arrangement"] == {"kind": "singleton"}
    assert doc["tags"] == e["tags"] and "source" not in doc


def test_cmd_write_accepts_promoted_entry(data_dir, queue, tmp_path):
    rec = _rec("world-shaping")
    rows = {rec["key"]: rec}
    rep = promote(rows, queue, [rec["key"]], data_dir=data_dir, dry_run=False)
    e = queue["entries"][-1]
    e["description"], e["status"] = e["description_draft"], "ready"
    qpath = tmp_path / "q.json"
    qpath.write_text(json.dumps(queue))
    args = type("A", (), {"stems": ["world_shaping"], "chunk": None, "sub_chunk": None, "overwrite": False,
                          "dry_run": True, "queue": qpath})()
    assert se.cmd_write(args, queue, data_dir) == 0
    assert rep.promoted == ["world_shaping#1"]


def test_pair_completion_partner(data_dir, queue):
    rec = _rec("world-shaping", novelty={"flags": ["pair_completion"], "nearest_existing": "passive",
                                        "decision": "grey"})
    e = queue_entry_from_record(rec)
    assert e["partner"] == "passive" and e["pairing"] == "pair"


def test_refusals(data_dir, queue):
    recs = [_rec("stubborn"), _rec("pirate"), _rec("rationalizing"), _rec("tall", verdict="tagged",
            tags=["physical"], holding="physical"),
            _rec("plumber", verdict="tagged", tags=["role_person"], holding="roles", entity_type="role"),
            _rec("flurbish", verdict="reject", tags=["not_a_word"]), _rec("aloof"), _rec("fresh-word")]
    unf = _rec("unfiltered-word")
    unf["filter"] = None
    recs.append(unf)
    rows = {r["key"]: r for r in recs}
    before = copy.deepcopy(queue)
    rep = promote(rows, queue, list(rows) + ["nope#1"], data_dir=data_dir, dry_run=True)
    # Expectation changed 2026-09-29 (Roger's decision 8, decisions_m1.md): a stem the queue
    # marks not_adopted is refused by default, quoting the old decision; it used to come back.
    assert rep.promoted == ["fresh_word#1"]
    assert "not_adopted" in rep.refused["aloof#1"]
    assert "corpus" in rep.refused["stubborn#1"] and "corpus" in rep.refused["pirate#1"]
    assert "seed queue" in rep.refused["rationalizing#1"]
    assert "holding" in rep.refused["tall#1"] and "holding" in rep.refused["plumber#1"]
    assert "verdict reject" in rep.refused["flurbish#1"]
    assert rep.refused["unfiltered_word#1"] == "not filtered" and rep.refused["nope#1"] == "not in registry"
    assert queue == before  # dry run


def test_partner_hint_sets_both(data_dir, queue):
    a = _rec("world-shaping", partner_hint="world-accepting")
    b = _rec("world-accepting")
    rows = {a["key"]: a, b["key"]: b}
    rep = promote(rows, queue, list(rows), data_dir=data_dir, dry_run=False)
    by = {e["stem"]: e for e in rep.entries}
    assert by["world_shaping"]["partner"] == "world_accepting"
    assert by["world_accepting"]["partner"] == "world_shaping"
    assert by["world_shaping"]["pairing"] == "pair"
    assert len(queue["entries"]) == 4


def test_partner_hint_alone_does_not_pair(data_dir, queue):
    a = _rec("world-shaping", partner_hint="world-accepting")
    rep = promote({a["key"]: a}, queue, [a["key"]], data_dir=data_dir)
    assert rep.entries[0]["partner"] is None


def test_min_local_novelty(data_dir, queue):
    a = _rec("aa", novelty={"signals": {"openai": {"local": 0.5}, "local": {"local": 0.2}}})
    b = _rec("bb", novelty={"signals": {"openai": {"local": 0.5}}})
    c = _rec("cc")
    rows = {r["key"]: r for r in (a, b, c)}
    rep = promote(rows, queue, list(rows), data_dir=data_dir, min_local_novelty=0.3)
    assert rep.promoted == ["bb#1"] and set(rep.refused) == {"aa#1", "cc#1"}


def test_two_senses_same_stem(data_dir, queue):
    a = _rec("cool")
    b = new_record("cool", sense_id=2)
    b.update({k: a[k] for k in ("filter", "gloss", "sources")})
    rows = {a["key"]: a, b["key"]: b}
    rep = promote(rows, queue, ["cool#1", "cool#2"], data_dir=data_dir)
    assert rep.promoted == ["cool#1"] and "another sense" in rep.refused["cool#2"]


# --------------------------------------------------------------------------- the physical pass (QUESTIONS 1)
# Roger, 2026-10-09: physical candidates are promoted normally, in a separate pass, and carry the physical tag.
# promote() lets a physical row through only with allow_physical (gap_registry.py promote --keys and the review
# app's apply pass it); the bulk path (--status accepted) and every other caller keep refusing it.

PHYS_SECTION = "Physical-attribute traits: a separate research track (decided 2026-09-08)"
PHYS_GLOSS = "This means having big, strong muscles that fill out one's shirts."


def _phys(surface="brawny", **kw):
    r = _rec(surface, verdict="tagged", tags=["physical"], holding="physical", gloss=None, gen="censuses", **kw)
    r["physical_gloss"] = {"gloss": PHYS_GLOSS, "alignment": 0, "batch_id": "physical_pilots_1"}
    return r


@pytest.fixture
def phys_queue(queue):
    queue["entries"].append({"stem": "blond", "label": "blond", "entity_type": "trait", "status": "done",
                             "tags": ["physical"], "section": PHYS_SECTION})
    return queue


def test_a_physical_row_is_refused_unless_promoted_by_name(data_dir, phys_queue):
    rec = _phys()
    before = copy.deepcopy(phys_queue)
    rep = promote({rec["key"]: rec}, phys_queue, [rec["key"]], data_dir=data_dir, dry_run=False)
    assert rep.promoted == [] and "physical holding list" in rep.refused["brawny#1"]
    assert "--keys" in rep.refused["brawny#1"] and phys_queue == before


def test_promoted_by_name_it_joins_the_physical_track(data_dir, phys_queue):
    rec = _phys(novelty={"run_id": "physical_pilots_1", "pass": "physical", "decision": "new"})
    rep = promote({rec["key"]: rec}, phys_queue, [rec["key"]], data_dir=data_dir, dry_run=False, allow_physical=True)
    e = phys_queue["entries"][-1]
    assert rep.promoted == ["brawny#1"] and e["stem"] == "brawny" and e["status"] == "candidate"
    assert e["tags"] == ["gap_gen", "source:censuses", "physical"]                 # merged, once
    assert e["section"] == PHYS_SECTION and e["description_draft"] == PHYS_GLOSS and e["description"] is None
    assert e["gap_gen"]["holding"] == "physical" and e["gap_gen"]["registry_key"] == "brawny#1"
    assert e["description_notes"].startswith("physical track: on the physical holding list, promoted by name after "
                                             "the physical pass physical_pilots_1")
    # a reviewer writes the description; the seed document carries the tag like the track's other files
    e2 = dict(e, description=e["description_draft"], status="ready")
    doc = se.seed_document(e2, {"entries": [e2]}, data_dir)
    assert "physical" in doc["tags"]


def test_a_physical_row_with_no_filter_tag_still_gets_the_tag(data_dir, phys_queue):
    rec = _phys()
    rec["filter"]["tags"] = []
    rep = promote({rec["key"]: rec}, phys_queue, [rec["key"]], data_dir=data_dir, allow_physical=True)
    assert rep.entries[0]["tags"] == ["gap_gen", "source:censuses", "physical"]


def test_the_section_falls_back_to_the_constant_and_an_explicit_one_is_kept(data_dir, queue):
    from assistant_axis.gapgen import physical_pass as PP
    rec = _phys()
    rep = promote({rec["key"]: rec}, queue, [rec["key"]], data_dir=data_dir, allow_physical=True)
    assert rep.entries[0]["section"] == PP.SECTION == PHYS_SECTION
    rep = promote({rec["key"]: rec}, queue, [rec["key"]], data_dir=data_dir, allow_physical=True, section="hand-picked")
    assert rep.entries[0]["section"] == "hand-picked"


def test_the_other_holding_lists_are_unchanged_when_physical_is_allowed(data_dir, queue):
    recs = [_rec("plumber", verdict="tagged", tags=["role_person"], holding="roles", entity_type="role"),
            _rec("faraway", holding="nationalities"),
            _rec("sulky", verdict="tagged", tags=["state"], holding="states", gloss=None)]
    rows = {r["key"]: r for r in recs}
    rep = promote(rows, queue, list(rows), data_dir=data_dir, allow_physical=True)
    assert rep.promoted == []
    assert rep.refused["plumber#1"] == "on the roles holding list (never promoted)"
    assert rep.refused["faraway#1"] == "on the nationalities holding list (never promoted)"
    assert "no states pass judgement yet" in rep.refused["sulky#1"]


def test_a_physical_row_meets_every_other_refusal(data_dir, phys_queue):
    rec = _phys("stubborn")                                                         # a corpus stem
    rep = promote({rec["key"]: rec}, phys_queue, [rec["key"]], data_dir=data_dir, allow_physical=True)
    assert rep.refused["stubborn#1"] == "stem exists in the corpus"
    rec = _phys("blond")                                                            # a physical-track queue entry
    rep = promote({rec["key"]: rec}, phys_queue, [rec["key"]], data_dir=data_dir, allow_physical=True)
    assert rep.refused["blond#1"] == "stem already in the seed queue"
