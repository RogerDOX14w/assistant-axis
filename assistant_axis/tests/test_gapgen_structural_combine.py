"""Structural generators: three samples per trait combined by union (Roger, 2026-10-13).  "Haiku and Sonnet 5.5 are
run at T=1.  Stability is not expected ... I'm instead leaning towards running three times and intelligently combining
their answers.  For something that returns a word, that might be making a deduped list of them."  No network: a
client scripted by the rendered prompt's hash (each sample a separate call, answered in turn)."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen.generators import structural as S
from assistant_axis.gapgen.generators.structural import combine as CB
from assistant_axis.gapgen.generators.structural import evaluate as E
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import postprocess as PP
from assistant_axis.gapgen.generators.structural import prompts as P
from assistant_axis.gapgen.generators.structural import sidetable as ST
from assistant_axis.gapgen.generators.structural import submit as SU
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests import structural_fakes as F

SYSTEM = P.operator_system()


def _rep(stem, k, *, principal=False, **kw):
    rep, why = O.parse_operator_reply(F.reply(principal=principal, **kw), principal=principal, source_label=stem,
                                      source_stem=stem)
    assert why is None, why
    rep.stem, rep.label, rep.sample, rep.run_id = stem, stem, k, "r1"
    return rep


def three():
    """Three samples of one trait: overlapping, synonymous and separator-variant labels, one empty slot."""
    return {1: _rep("brave", 1, position="mean", opposite=F.item("cowardly", "This means fleeing, first."),
                    excess=F.item("foolhardy", "This means rushing in, first."),
                    retarget={"self": F.item("hard on oneself", "This means self-blame, first.")}),
            2: _rep("brave", 2, position="mean", opposite=F.item("Cowardly", "This means fleeing, second."),
                    excess=F.item("reckless", "This means no care for risk."),
                    deficiency=F.item("craven", "This means shrinking.")),
            3: _rep("brave", 3, position="excess", opposite=F.item("faint-hearted", "This means quailing."),
                    excess=F.item("fool-hardy", "This means rushing in, third."))}


# --------------------------------------------------------------------------- the union

def test_union_by_stem_with_support_and_every_gloss():
    c = CB.combine(three())
    assert c.samples == [1, 2, 3] and c.n_samples == 3
    opp = c.slot("opposite")
    assert [(o["label"], o["support"], o["samples"]) for o in opp] == [("cowardly", 2, [1, 2]),
                                                                       ("faint-hearted", 1, [3])]
    assert opp[0]["gloss"] == "This means fleeing, first."                     # the first sample's gloss
    assert [g["gloss"] for g in opp[0]["glosses"]] == ["This means fleeing, first.", "This means fleeing, second."]
    exc = c.slot("excess")                                                       # separator-blind: fool-hardy
    assert [(x["label"], x["support"]) for x in exc] == [("foolhardy", 2), ("reckless", 1)]
    assert [x["label"] for x in c.slot("deficiency")] == ["craven"]           # support 1: kept, never dropped
    assert c.slot("remode", "speech") == [] and "remode:speech" not in c.slots   # empty in every sample: empty
    assert c.slot("retarget", "self")[0]["support"] == 1


def test_position_every_sample_and_the_majority():
    c = CB.combine(three())
    assert c.positions == ["mean", "mean", "excess"] and c.position == "mean"
    split = {1: _rep("x", 1, position="mean"), 2: _rep("x", 2, position="excess"),
             3: _rep("x", 3, position="deficiency")}
    assert CB.combine(split).position is None and CB.combine(split).positions == ["mean", "excess", "deficiency"]
    assert CB.combine({2: _rep("x", 2, position="excess")}).position == "excess"


def test_renamed_from_aware_and_near_synonyms_stay_apart():
    s = {1: _rep("brave", 1, opposite=F.item("trusty old")), 2: _rep("brave", 2, opposite=F.item("dependable")),
         3: _rep("brave", 3, opposite=F.item("reliable"))}
    c = CB.combine(s, renamed={"trusty_old": "dependable"})
    assert [(o["label"], o["support"]) for o in c.slot("opposite")] == [("trusty old", 2), ("reliable", 1)]
    assert len(CB.combine(s).slot("opposite")) == 3                          # without the rename map: three rows


def test_principal_slots_combine_the_same_way():
    s = {k: _rep("obedient", k, principal=True, retarget={"the_user": F.item(lab)})
         for k, lab in ((1, "user-pleasing"), (2, "user pleasing"), (3, "people-pleasing"))}
    c = CB.combine(s)
    assert [(x["label"], x["support"]) for x in c.slot("retarget", "the_user")] == [("user-pleasing", 2),
                                                                                   ("people-pleasing", 1)]
    assert c.principal


def test_support_counts_and_the_union_phrase():
    sc = CB.support_counts([CB.combine(three())])
    assert sc["by_support"] == {"1": 4, "2": 2} and sc["by_operator"]["excess"] == {"1": 1, "2": 1}
    assert sc["samples_per_trait"] == {"3": 1}
    assert CB.union_phrase(3) == "union of 3 samples" and CB.union_phrase(1) == "union of 1 sample"


# --------------------------------------------------------------------------- the calls: three samples, cached each

@pytest.fixture()
def corpus(tmp_path):
    return F.write_corpus(tmp_path)


def test_three_independent_samples_recorded_and_resumed_one_by_one(corpus, tmp_path):
    ins = {t.stem: t for t in O.build_inputs(None, data_dir=corpus,
                                             regions_path=corpus / "candidates" / "corpus_regions.json")}
    sel = [ins["brave"], ins["timid"]]
    answers = {"brave": [F.reply("mean", opposite=F.item("cowardly")), F.reply("mean", opposite=F.item("craven")),
                         F.reply("mean", opposite=F.item("cowardly"))],
               "timid": [F.reply("deficiency"), "garbled", "garbled", F.reply("deficiency")]}
    out = tmp_path / "responses.jsonl"
    # a first run of one sample, as the null-rate pilot was
    run1 = asyncio.run(O.run_operators(sel, client=F.ScriptedClient(F.script_for(sel, SYSTEM, {
        "brave": answers["brave"][0], "timid": answers["timid"][0]})), model=O.MODEL, usage=MultiModelUsage(),
        system=SYSTEM, run_id="r1", out_path=out))
    assert run1.n_answered == 2 and {r["sample"] for r in O.read_responses(out)} == {1}
    # three samples: samples 2 and 3 are sent; timid's sample 2 fails twice and is left unanswered
    client = F.ScriptedClient(F.script_for(sel, SYSTEM, {"brave": answers["brave"][1:],
                                                         "timid": answers["timid"][1:]}))
    run = asyncio.run(O.run_operators(sel, client=client, model=O.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="r1", out_path=out, resume=True, samples=3, concurrency=1))
    assert run.n_units == 6 and run.n_reused == 2 and run.n_calls == 5
    assert sorted(run.samples["brave"]) == [1, 2, 3] and sorted(run.samples["timid"]) == [1, 3]
    assert run.errors == {("timid", 2): "unparseable"}
    recs = O.read_responses(out)
    assert sorted((r["stem"], r["sample"]) for r in recs if r["attempt"] == 1) == [
        ("brave", 1), ("brave", 2), ("brave", 3), ("timid", 1), ("timid", 2), ("timid", 3)]
    assert len({r["prompt_sha256"] for r in recs if r["stem"] == "brave"}) == 1     # one prompt, three samples
    # a resume sends only the missing sample
    last = F.ScriptedClient(F.script_for(sel, SYSTEM, {"timid": F.reply("excess")}))
    run = asyncio.run(O.run_operators(sel, client=last, model=O.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="r1", out_path=out, resume=True, samples=3))
    assert len(last.calls) == 1 and run.n_reused == 5 and run.n_answered == 6
    c = CB.combine(run.samples["brave"])
    assert [(o["label"], o["support"]) for o in c.slot("opposite")] == [("cowardly", 2), ("craven", 1)]


# --------------------------------------------------------------------------- downstream: table, side table, recovery

def test_table_rows_carry_support_and_the_first_gloss_is_the_hint(corpus):
    c = CB.combine(three(), lexicon=F.LEXICON)
    corp = PP.load_corpus(corpus)
    t = PP.build_table([c], corpus=corp, queue={}, registry={}, lexicon=F.LEXICON)
    by = {r["stem"]: r for r in t}
    src = by["cowardly"]["sources"][0]
    assert src["support"] == 2 and src["n_samples"] == 3 and src["samples"] == [1, 2] and len(src["glosses"]) == 2
    assert by["cowardly"]["max_support"] == 2 and by["faint_hearted"]["max_support"] == 1
    assert {"foolhardy", "reckless"} <= set(by)                                   # one slot, two rows
    cands = {x.surface: x for x in SU.to_candidates(SU.select_all(t), "w1")}
    assert cands["cowardly"].gloss_hint == "This means fleeing, first."
    assert cands["cowardly"].source_ref == "structural:op:opposite:brave"         # the documented form, unchanged
    assert by["foolhardy"]["sources"][0]["partner_hint"] == "craven"              # the sibling vice


def test_side_table_checks_the_recorded_label_against_the_union(corpus):
    corp = PP.load_corpus(corpus)
    s = {1: _rep("brave", 1, position="mean", opposite=F.item("cowardly")),
         2: _rep("brave", 2, position="excess", opposite=F.item("timid")),
         3: _rep("brave", 3, position="mean", opposite=F.item("cowardly"))}
    row = ST.position_rows([CB.combine(s)], corpus=corp, lexicon=F.LEXICON)[0]
    assert row["negative_label_check"] == "match" and row["recorded_support"] == 1   # timid, named by one sample
    assert row["model_opposite"] == "cowardly" and row["position"] == "mean"
    assert row["positions"] == ["mean", "excess", "mean"] and row["n_samples"] == 3
    assert [o["support"] for o in row["model_opposites"]] == [2, 1]
    assert "cowardly (2), timid (1)" not in ST.render_mismatches([row])          # a match is not a mismatch


def test_pair_recovery_reads_every_opposite_of_the_union(corpus):
    corp = PP.load_corpus(corpus)
    s = {1: _rep("brave", 1, opposite=F.item("cowardly")), 2: _rep("brave", 2, opposite=F.item("timid"))}
    out = E.pair_recovery({"brave": CB.combine(s)}, [("brave", "timid")], corpus=corp)
    assert out["recall_stem"] == 1.0 and out["n_opposites"] == 2


def test_sample_agreement_over_answered_slots_only():
    samples = {"brave": three(), "x": {1: _rep("x", 1), 2: _rep("x", 2)}}
    sa = E.sample_agreement(samples)
    assert sa["n_sample_pairs"] == 4 and sa["n_both_empty"] == 1 and sa["n_traits"] == 3
    assert sa["by_operator"]["opposite"]["n_slots"] == 3 and sa["reported_not_gated"]


# --------------------------------------------------------------------------- void runs

def test_void_marker_round_trip_and_collect_skips_a_void_run(tmp_path):
    d1, d2 = tmp_path / "r1", tmp_path / "r2"
    for d, pos in ((d1, "mean"), (d2, "excess")):
        O.append_response({"stage": "operators", "stem": "brave", "label": "brave", "run_id": d.name, "sample": 1,
                           "text": F.reply(pos)}, d / "responses.jsonl")
    assert S.read_void(d2) is None
    p = S.write_void(d2, reason="Sonnet 5.5 refused 107 of 116 calls (reasoning_extraction)", by="coordinator")
    assert json.loads(p.read_text())["reason"].startswith("Sonnet") and S.read_void(d2)["by"] == "coordinator"
    with pytest.raises(FileExistsError):
        S.write_void(d2, reason="again", by="x")
    with pytest.raises(ValueError):
        S.write_void(d1, reason=" ", by="x")
    col = PP.collect_replies([d1, d2])
    assert col.void == ["r2"] and col.full["brave"].position == "mean"


def test_the_recorded_output_checks_skip_a_void_run(tmp_path, monkeypatch):
    from assistant_axis.tests import test_gapgen_structural_acceptance as A
    runs = tmp_path / "runs" / "structural"
    bad = runs / "stab-sonnet-a"
    for i in range(4):                                            # refused, empty: a parse rate of 0
        O.append_response({"stage": "operators", "stem": f"t{i}", "label": f"t{i}", "sample": 1, "text": "",
                           "stop_reason": "refusal"}, bad / "responses.jsonl")
    monkeypatch.setattr(A, "RUNS", runs)
    with pytest.raises(AssertionError):
        A.test_parse_rate_in_every_run()
    S.write_void(bad, reason="refused", by="test")
    with pytest.raises(pytest.skip.Exception):
        A.test_parse_rate_in_every_run()                          # the only run is void: nothing to check


def test_samples_are_identified_by_their_keys():
    """Two runs' first samples combined as samples 1 and 2 count twice (their replies both say sample 1)."""
    a, b = _rep("brave", 1, opposite=F.item("cowardly")), _rep("brave", 1, opposite=F.item("cowardly"))
    c = CB.combine({1: a, 2: b})
    assert c.samples == [1, 2] and c.slot("opposite")[0]["support"] == 2 and c.slot("opposite")[0]["samples"] == [1, 2]
