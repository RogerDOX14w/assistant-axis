"""The Roget harvest (workstream 2, plan § 8 "Harvest"; one Candidate per head, interface
resolution 4; partner hints only for word-level opposites)."""
from __future__ import annotations

import dataclasses
import json
from collections import Counter

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.generators.roget import coverage as C
from assistant_axis.gapgen.generators.roget import harvest as H
from assistant_axis.gapgen.generators.roget import pairs as PR
from assistant_axis.gapgen.generators.roget import wn_clusters as W
from assistant_axis.tests.roget_fakes import make_index, small_wordnet

ZIPF = {"cautious": 3.9, "wary": 3.5, "chary": 2.2, "careful": 4.6, "heedful": 1.9, "guarded": 3.8,
        "circumspect": 2.6, "prudent": 3.3, "rare": 1.2, "incautious": 2.6, "rash": 3.6, "reckless": 3.8,
        "unwary": 2.2, "honest": 4.4, "dishonest": 3.7,
        # below the Zipf 1.5 line (gate audit 2 § 4c): a negating-prefix form of a word above it, a plain
        # trait word, a negating-prefix form of a word also below it, and a below-line word beside a frequent one
        "uncomplying": 0.0, "complying": 2.4, "thievish": 1.0, "unthrifty": 0.0, "thrifty": 1.2,
        "captious": 1.19, "critical": 4.5}


def zipf(w: str) -> float:
    return ZIPF.get(w, 3.0)


def head_with(groups, *, klass="V", section="I. Volition in general", title="Caution", hid="864", nouns=None):
    idx = make_index([{"id": hid, "title": title, "adj": groups, "noun": nouns or [["caution", "prudence"],
                                                                                   ["heed", "circumspection"],
                                                                                   ["vigilance", "foresight"]],
                       "klass": klass, "section": section}])
    return idx.heads[hid]


CFG = H.HarvestConfig()


def test_harvest_head_drops_and_representatives():
    h = head_with([["cautious", "wary", "chary"], ["rare"], ["heedful"], ["shy of", "on one's guard"],
                   ["Fabian"], ["careful", "guarded"], ["very careful indeed"], ["known word"]])
    items, drops = H.harvest_head(h, known_stems={"known_word"}, cfg=CFG, zipf=zipf)
    words = [it.surface for it in items]
    assert "cautious" in words and "wary" not in words              # one per group, the most frequent
    assert "careful" in words and "guarded" not in words
    # below the platform floor (1.5), but the harvest gives every word a gloss hint, so rule 1b's gloss-hint
    # route sends it to M1's probe (Roger, 2026-10-12); before, it was dropped as "zipf_hard"
    rare = next(it for it in items if it.surface == "rare")
    assert rare.rescue == "gloss_hint" and rare.probe_band and "zipf_hard_reject" not in drops
    heed = next(it for it in items if it.surface == "heedful")
    assert heed.probe_band and heed.rescue is None                  # 1.5 <= Zipf < 2.5: flagged, kept
    assert drops["function_word"] == 1 and drops["too_many_words"] == 2   # "shy of"; two long phrases
    assert drops["proper"] == 1 and drops["known_label"] == 1
    assert drops["not_representative"] == 3
    assert [it.score for it in items] == sorted([it.score for it in items], reverse=True)
    # a caller that submits without a gloss hint: hard_reject drops it
    items, drops = H.harvest_head(h, known_stems={"known_word"}, cfg=CFG, zipf=zipf, gloss_hint=False)
    assert "rare" not in [it.surface for it in items] and drops["zipf_hard_reject"] == 1


def test_harvest_head_cap_and_determinism():
    groups = [[w] for w in ["cautious", "wary", "careful", "guarded", "prudent", "circumspect"]]
    cfg = H.HarvestConfig(per_head_cap=3)
    a, d = H.harvest_head(head_with(groups), known_stems=set(), cfg=cfg, zipf=zipf)
    b, _ = H.harvest_head(head_with(groups), known_stems=set(), cfg=cfg, zipf=zipf)
    assert len(a) == 3 and d["cap"] == 3
    assert [x.surface for x in a] == [x.surface for x in b]


def _guard(*stems):
    return H.LabelGuard(stems)


@pytest.mark.parametrize("n_sib", [1, 10])
def test_gloss_hint_form_and_length(n_sib):
    sibs = ["wary", "chary", "guarded", "prudent", "circumspect", "heedful", "vigilant", "discreet", "politic",
            "careful"][:n_sib]
    h = head_with([["cautious"]] + [[s] for s in sibs])
    partner = head_with([["rash"]], title="Rashness", hid="863")
    item = H.HarvestItem("cautious", "864", "863", 0, sibs, 3.9, False, True, 1, 4.2, False)
    text = H.gloss_hint(item, h, partner, guard=_guard("bold"))
    assert text.startswith("This means a disposition toward caution")
    assert 18 <= len(text.split()) <= 43, text
    assert "cautious" not in text.split()                           # never the word itself
    assert text.endswith("the opposite pole is rashness.")


def test_gloss_hint_feeling_heads_and_label_guard():
    h = head_with([["dejected"], ["gloomy", "glum"]], klass="VI", section="II. Personal affections",
                  title="Dejection", hid="837", nouns=[["dejection", "melancholy", "gloom"], ["sadness"]])
    item = H.HarvestItem("dejected", "837", None, 0, ["gloomy", "glum", "sad"], 3.0, False, True, 1, 3.0, True)
    text = H.gloss_hint(item, h, None, guard=_guard("glum", "melancholy"))
    assert text.startswith("This means a general tendency to feel dejection and act from it")
    assert "glum" not in text and "melancholy" not in text           # an explicit guard still keeps labels out
    moral = head_with([["upright"]], klass="VI", section="IV. Moral affections", title="Probity", hid="939")
    item2 = H.HarvestItem("upright", "939", None, 0, ["honest"], 3.0, False, True, 1, 3.0, True)
    t2 = H.gloss_hint(item2, moral, None, guard=_guard("moral"))
    assert t2.startswith("This means a disposition toward probity")
    assert "moral" not in t2                                         # the section clause is dropped


def test_label_guard():
    g = H.LabelGuard({"bold", "kind_to_animals", "settled"})
    assert g.contains("a bold move") and g.contains("Bold-faced")
    assert g.contains("being kind to animals") and not g.contains("kind words to dogs")
    assert not g.contains("boldness")


def item(w, head, score=3.0):
    return H.HarvestItem(w, head, None, 0, [], score, False, True, 1, score, False)


def test_pair_candidates():
    lex = W.Lexicon(small_wordnet())
    a = [item("cautious", "864", 4), item("honest", "864", 3.5), item("wary", "864", 3)]
    b = [item("rash", "863", 4), item("dishonest", "863", 3.6), item("incautious", "863", 3)]
    got = H.pair_candidates(a, b, lex, top=3)
    by = {(p.a, p.b): p for p in got}
    assert by[("cautious", "incautious")].double_confirmed and by[("cautious", "incautious")].morph
    assert by[("honest", "dishonest")].morph and not by[("honest", "dishonest")].double_confirmed
    assert ("wary", "rash") in by and not by[("wary", "rash")].double_confirmed   # rank-matched
    # pair completion: the b side is the trait covering the opposed head
    got = H.pair_candidates([item("incautious", "863"), item("rash", "863")], [], lex,
                            existing_b=["cautious"], existing_b_labels={"cautious": "cautious"}, top=2)
    assert [(p.a, p.b, p.double_confirmed) for p in got] == [("incautious", "cautious", True),
                                                             ("rash", "cautious", False)]
    assert got[0].partner_existing == ["cautious"]


def test_to_candidates():
    its = [item("wary", "864", 3.0), item("rash", "863", 4.0), item("wary", "459", 2.0)]
    its[0].gloss_hint = "This means x."
    cands = H.to_candidates(its, generator="roget", run_id="r1", partner_hints={("rash", "863"): "cautious"})
    assert [(c.surface, c.source_ref, c.rank) for c in cands] == [("rash", "roget:863", 1), ("wary", "roget:864", 2),
                                                                  ("wary", "roget:459", 3)]
    assert all(isinstance(c, Candidate) and c.sense_id == 1 and c.generator == "roget" for c in cands)
    assert cands[0].partner_hint == "cautious" and cands[1].partner_hint is None
    assert cands[1].gloss_hint == "This means x." and cands[2].gloss_hint is None


def _world():
    idx = make_index([
        {"id": "604", "title": "Resolution", "adj": [["resolute"], ["determined"], ["honest"]]},
        {"id": "605", "title": "Irresolution", "adj": [["irresolute"], ["wavering"], ["dishonest"]]},
        {"id": "606", "title": "Obstinacy", "adj": [["obstinate"], ["stubborn"]]},
        {"id": "607", "title": "Tergiversation", "adj": [["fickle"]]},
        {"id": "863", "title": "Rashness", "adj": [["rash"], ["incautious"]], "klass": "VI",
         "section": "II. Personal affections", "subsection": "3. Prospective"},
        {"id": "864", "title": "Caution", "adj": [["cautious"], ["wary"]], "klass": "VI",
         "section": "II. Personal affections", "subsection": "3. Prospective"},
    ])
    pairs = PR.rule_pairs(idx, None)
    lh = {"cautious": {"label": "cautious", "source": "existing", "status": None, "primary": "864", "secondary": [],
                       "lexical": [], "semantic": []}}
    return idx, pairs, lh


def test_harvest_end_to_end_and_every_nth():
    idx, pairs, lh = _world()
    assert pairs["604"].partner == "605" and pairs["863"].partner == "864"
    rep = C.coverage(idx, pairs, lh)
    known = {"cautious"}
    lex = W.Lexicon(small_wordnet())
    res = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems=known, run_id="r1", lex=lex, zipf=zipf,
                    label_of={"cautious": "cautious"})
    heads = {c.source_ref for c in res.candidates}
    assert heads == {"roget:604", "roget:605", "roget:606", "roget:607", "roget:863"}
    assert not any(c.surface == "cautious" for c in res.candidates)
    hints = {c.surface: c.partner_hint for c in res.candidates if c.partner_hint}
    # word-level opposites only: negation forms across 604/605, WordNet across 863 -> covering trait
    assert hints == {"resolute": "irresolute", "irresolute": "resolute", "honest": "dishonest",
                     "dishonest": "honest", "incautious": "cautious"}
    assert all(c.gloss_hint and c.gloss_hint.startswith("This means ") for c in res.candidates)
    assert res.counts["n_candidates"] == len(res.candidates) == len(res.items)
    # every_nth=2 from offset 0 over the gap heads in order (604, 605, 606, 607, 863) keeps 604, 606, 863
    # and adds 605 (604's partner); 607 is unresolved (no partner)
    sel = H.select_heads(rep, H.HarvestConfig(every_nth=2))
    assert sel == ["604", "605", "606", "863"]
    sel1 = H.select_heads(rep, H.HarvestConfig(every_nth=2, offset=1))
    assert sel1 == ["604", "605", "607"]


def test_candidates_jsonl_form_and_round_trip(tmp_path):
    idx, pairs, lh = _world()
    rep = C.coverage(idx, pairs, lh)
    res = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems={"cautious"}, run_id="r1", zipf=zipf)
    out = H.write_harvest(res, tmp_path / "run", idx, run_id="r1")
    lines = out["candidates"].read_text(encoding="utf-8").splitlines()
    assert lines == [json.dumps(dataclasses.asdict(c), ensure_ascii=False) for c in res.candidates]
    # the three role-mode fields were added to every line by coding plan 16 (2026-10-22, § 8 test 2)
    assert set(json.loads(lines[0])) == {"surface", "generator", "run_id", "rank", "score", "gloss_hint", "sense_id",
                                         "source_ref", "partner_hint", "entity_type", "kind_guess", "human"}
    assert H.read_candidates(out["candidates"]) == res.candidates
    assert (tmp_path / "run" / "pair_candidates.jsonl").exists() and out["report"].exists()


def test_wn_candidates_every_nth():
    its = [W.WnItem(s, f"oewn:{s}", f"This means {s}.", None, 3.0, False, 3.0 - i * 0.1, "closure", "x")
           for i, s in enumerate(["a1", "b1", "c1", "d1"])]
    cands = H.wn_candidates(its, run_id="r1", every_nth=2)
    assert [(c.surface, c.rank, c.generator, c.source_ref) for c in cands] == \
        [("a1", 1, "wn_clusters", "oewn:oewn:a1"), ("c1", 2, "wn_clusters", "oewn:oewn:c1")]


def test_gloss_hint_without_guard_keeps_labels_but_never_the_word():
    """Roger, 2026-10-08 (QUESTIONS 41): the harvest passes no label guard; only the candidate's own word is
    kept out, so a corpus or queue label such as "general" may appear."""
    h = head_with([["dejected"], ["gloomy", "glum"]], klass="VI", section="II. Personal affections",
                  title="Dejection", hid="837", nouns=[["dejection", "melancholy", "gloom"], ["sadness"]])
    item = H.HarvestItem("dejected", "837", None, 0, ["gloomy", "glum", "sad"], 3.0, False, True, 1, 3.0, True)
    text = H.gloss_hint(item, h, None)
    assert text.startswith("This means a general tendency to feel dejection and act from it")
    assert "glum" in text and "dejected" not in text.split()
    selfish = head_with([["dejection"]], klass="VI", section="II. Personal affections", title="Dejection",
                        hid="837", nouns=[["dejection", "gloom"]])
    item2 = H.HarvestItem("dejection", "837", None, 0, [], 3.0, False, True, 1, 3.0, True)
    t2 = H.gloss_hint(item2, selfish, None)
    assert "tendency to feel gloom" in t2                            # the title is the word itself: next noun


def test_partner_hints_from_synopsis_pairs_and_not_from_position():
    """A pair Roget's printed synopsis gives (source "synopsis") yields partner hints like a rule pair; a pair
    by position alone yields none."""
    idx, pairs, lh = _world()
    lex = W.Lexicon(small_wordnet())
    for src, expect in (("synopsis", True), ("position", False)):
        pp = dict(pairs)
        for h in ("604", "605"):
            pp[h] = dataclasses.replace(pairs[h], source=src)
        rep = C.coverage(idx, pp, lh)
        res = H.harvest(rep, idx, pp, cfg=H.HarvestConfig(), known_stems={"cautious"}, run_id="r1", lex=lex,
                        zipf=zipf, label_of={"cautious": "cautious"})
        hints = {c.surface: c.partner_hint for c in res.candidates if c.partner_hint}
        assert (hints.get("resolute") == "irresolute") is expect
        assert hints.get("incautious") == "cautious"                  # the rule pair 863 / 864 is unchanged


def test_gloss_hint_keeps_the_word_out_of_hyphenated_siblings_and_the_section():
    """Review 2026-10-12: the full run's hints for "free" and "sound" named "scot-free" and "sound-minded" (the
    word inside a hyphenated sibling); a section title holding the word is dropped as well."""
    h = head_with([["free"], ["exempt", "scot-free"], ["immune"]], title="Exemption", hid="927a",
                  nouns=[["exemption", "freedom", "free-for-all"], ["immunity", "release"]])
    item = H.HarvestItem("free", "927a", None, 0, ["exempt", "scot-free", "immune"], 3.0, False, True, 1, 3.0, False)
    text = H.gloss_hint(item, h, None)
    assert not H.uses_word(text, "free"), text
    assert "freedom" in text and "exempt" in text                     # a longer word holding it is not the word
    sym = head_with([["sympathetic"], ["kindly"]], klass="VI", section="II. Sympathetic affections", title="Pity",
                    hid="914", nouns=[["pity", "compassion"], ["sympathy"]])
    item2 = H.HarvestItem("sympathetic", "914", None, 0, ["kindly"], 3.0, False, True, 1, 3.0, True)
    t2 = H.gloss_hint(item2, sym, None)
    assert not H.uses_word(t2, "sympathetic") and "(sympathetic affections)" not in t2, t2
    assert H.uses_word("of a piece with scot-free", "free") and not H.uses_word("carefree, freedom", "free")


# --------------------------------------------------------------------------- the Zipf floor under rule 1b

def _floor_world():
    """Three gap heads: 764 with a group holding only a negating-prefix word below the line (review 5 D4's
    uncomplying) and one holding a negating-prefix word whose base is below the line too; 791 with a plain
    trait word below the line (thievish); 932 with a below-line word beside a frequent near-synonym, which the
    one-word-per-group rule leaves out."""
    idx = make_index([
        {"id": "764", "title": "Refusal", "adj": [["refusing"], ["uncomplying"], ["unthrifty"]],
         "noun": [["refusal", "denial"], ["rejection"]]},
        {"id": "791", "title": "Stealing", "adj": [["thieving"], ["thievish"]], "noun": [["theft", "stealing"]]},
        {"id": "932", "title": "Disapprobation", "adj": [["critical", "captious"]], "noun": [["blame"]]},
    ])
    return idx, PR.rule_pairs(idx, None)


def test_negating_prefix_word_below_the_line_is_submitted():
    """Review 5 D4: zipf_info rescued uncomplying (un- + complying, at 2.4) but the second check dropped it."""
    idx, pairs = _floor_world()
    rep = C.coverage(idx, pairs, {})
    res = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems=set(), run_id="r1", zipf=zipf)
    c = next(c for c in res.candidates if c.surface == "uncomplying")
    assert c.source_ref == "roget:764" and c.gloss_hint.startswith("This means ")
    assert next(it for it in res.items if it.surface == "uncomplying").rescue == "negating_prefix"
    # route 1 alone keeps it: no gloss hint needed
    items, drops = H.harvest_head(idx.heads["764"], known_stems=set(), cfg=CFG, zipf=zipf, gloss_hint=False)
    assert "uncomplying" in [it.surface for it in items]


def test_gloss_hinted_word_below_the_line_is_submitted():
    idx, pairs = _floor_world()
    rep = C.coverage(idx, pairs, {})
    res = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems=set(), run_id="r1", zipf=zipf)
    by = {it.surface: it for it in res.items}
    assert by["thievish"].rescue == "gloss_hint" and by["thievish"].zipf_min == 1.0
    assert "thievish" in {c.surface for c in res.candidates}
    assert by["unthrifty"].rescue == "gloss_hint"            # base thrifty (1.2) is below the line too: route 2
    assert "captious" not in by and by["critical"].rescue is None   # one word per group: the frequent one


def test_hard_reject_still_drops():
    """Without a gloss hint only the negating-prefix route rescues; hard_reject drops the rest and is counted."""
    idx, _ = _floor_world()
    zs = Counter()
    items, drops = H.harvest_head(idx.heads["764"], known_stems=set(), cfg=CFG, zipf=zipf, gloss_hint=False,
                                  zipf_stats=zs)
    words = [it.surface for it in items]
    assert "unthrifty" not in words and "uncomplying" in words
    assert drops["zipf_hard_reject"] == 1 and "zipf_hard" not in drops
    assert zs == Counter({"below_line": 2, "hard_reject": 1, "rescued_negating_prefix": 1})
    items, _ = H.harvest_head(idx.heads["791"], known_stems=set(), cfg=CFG, zipf=zipf, gloss_hint=False)
    assert [it.surface for it in items] == ["thieving"]


def test_zipf_floor_counts_in_the_records(tmp_path):
    """harvest_counts.json splits what the floor did (gate audit 2 proposal 3): below the line, dropped by
    hard_reject, rescued by each route (what the second check dropped before), the rescued words that became
    candidates, and the same counts for the heads skipped as not character."""
    idx, pairs = _floor_world()
    rep = C.coverage(idx, pairs, {})
    res = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems=set(), run_id="r1", zipf=zipf,
                    head_scope={"764": 2, "791": 1, "932": 0})
    zf = res.counts["zipf_floor"]
    assert zf["rule"] == "rule_1b" and zf["line"] == 1.5
    assert (zf["below_line"], zf["hard_reject"], zf["rescued"]) == (3, 0, {"gloss_hint": 2, "negating_prefix": 1})
    assert zf["rescued_total"] == 3 and zf["submitted"] == 3
    assert zf["submitted_words"] == ["thievish", "uncomplying", "unthrifty"]
    assert zf["submitted_by_rescue"] == {"negating_prefix": 1, "gloss_hint": 2}
    # 932 is rated 0 and skipped: its below-line word is counted apart, never submitted
    assert zf["in_skipped_heads"] == {"below_line": 1, "hard_reject": 0, "rescued": {"gloss_hint": 1},
                                      "rescued_total": 1}
    assert "zipf_hard" not in res.counts["drops"]
    assert res.config["zipf_floor"] == "rule_1b" and "zipf_hard" not in res.config
    assert res.config["wn_closure_depth"] == 6
    out = H.write_harvest(res, tmp_path / "run", idx, run_id="r1")
    rec = json.loads(out["counts"].read_text())
    assert rec["counts"]["zipf_floor"] == zf and rec["config"]["zipf_floor"] == "rule_1b"
    md = out["report"].read_text()
    assert "Zipf floor (rule_1b" in md and "uncomplying" in md


def test_delta_keeps_only_the_words_an_earlier_run_did_not_submit():
    idx, pairs = _floor_world()
    rep = C.coverage(idx, pairs, {})
    full = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems=set(), run_id="r1", zipf=zipf)
    # the earlier run: everything above the line (as the old rule submitted it)
    prev = {(normalize_to_file_name(c.surface), c.source_ref) for c in full.candidates
            if c.surface not in ("thievish", "uncomplying", "unthrifty")}
    d = H.harvest(rep, idx, pairs, cfg=H.HarvestConfig(), known_stems=set(), run_id="r2", zipf=zipf,
                  already_submitted=prev, delta_from="r1")
    assert sorted(c.surface for c in d.candidates) == ["thievish", "uncomplying", "unthrifty"]
    assert [c.rank for c in d.candidates] == [1, 2, 3]
    assert d.counts["delta"] == {"from": "r1", "n_harvested": len(full.items),
                                 "n_already_submitted": len(full.items) - 3, "n_new": 3,
                                 "new_below_line": ["thievish", "uncomplying", "unthrifty"], "new_other": []}
    assert d.counts["n_candidates"] == 3 and d.counts["zipf_floor"] == full.counts["zipf_floor"]


def test_would_be_words_ignore_the_gap_class():
    idx, _ = _floor_world()
    got = H.would_be_words(idx, ["764", "932", "nope"], known_stems={"refusing"}, zipf=zipf)
    assert got == {"764": ["uncomplying", "unthrifty"], "932": ["critical"]}
