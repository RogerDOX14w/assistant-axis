"""Structural generators, B: the operators call's parse, item rule, guard, retries, charging and resume (coding_plan_09
section 8, ``operators``; task 4).  No network: a scripted Anthropic client keyed by the rendered prompt's hash."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import prompts as P
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests import structural_fakes as F

SYSTEM = P.operator_system()


@pytest.fixture()
def corpus(tmp_path):
    return F.write_corpus(tmp_path)


@pytest.fixture()
def inputs(corpus):
    return O.build_inputs(None, data_dir=corpus, regions_path=corpus / "candidates" / "corpus_regions.json")


def by(inputs):
    return {t.stem: t for t in inputs}


# --------------------------------------------------------------------------- parse

def test_parse_a_scripted_reply():
    text = F.reply("mean", opposite=F.item("cowardly"), excess=F.item("foolhardy"), deficiency=F.item("craven"),
                   retarget={"self": F.item("hard on oneself", common=False)}, remode={"speech": F.item("bold-spoken")})
    rep, why = O.parse_operator_reply(text, principal=False, source_label="brave", source_stem="brave")
    assert why is None and rep.position == "mean" and rep.reasoning == "Reasoned first."
    assert rep.opposite["label"] == "cowardly" and rep.retarget["self"]["has_common_word"] is False
    assert [(op, sub) for op, sub, _ in rep.items()] == [("opposite", None), ("excess", None),
                                                         ("deficiency", None), ("retarget", "self"),
                                                         ("remode", "speech")]
    assert set(rep.retarget) == set(O.TARGETS) and set(rep.remode) == set(O.MODES)
    assert rep.problems == []


def test_null_is_accepted_everywhere_but_reasoning_and_position():
    rep, why = O.parse_operator_reply(json.dumps({"reasoning": "r", "position": "not_scalar", "opposite": None,
                                                  "excess": None, "deficiency": None, "retarget": None,
                                                  "remode": None}), principal=False)
    assert why is None and rep.items() == [] and all(v is None for v in rep.retarget.values())
    for bad, want in (({"reasoning": None, "position": "mean"}, "no reasoning"),
                      ({"reasoning": "r", "position": None}, "position None"),
                      ({"reasoning": "r", "position": "middling"}, "position 'middling'")):
        rep, why = O.parse_operator_reply(json.dumps(bad), principal=False)
        assert rep is None and why == want
    assert O.parse_operator_reply("not json at all", principal=False) == (None, "unparseable")
    assert O.parse_operator_reply(None, principal=False) == (None, "no response")
    fenced = "```json\n" + F.reply("excess") + "\n```"
    assert O.parse_operator_reply(fenced, principal=False)[0].position == "excess"


@pytest.mark.parametrize("label,why", [
    ("over-cautious", "over-/under-/too-/non-X"), ("under-prepared", "over-/under-/too-/non-X"),
    ("too trusting", "over-/under-/too-/non-X"), ("non-religious", "over-/under-/too-/non-X"),
    ("overbrave", "over-/under-/too-/non-X"), ("not brave", "over-/under-/too-/non-X"),
    ("overly eager to help", "over-/under-/too-/non-X"),
    ("hard on oneself at every turn", "6 words (at most 4)"), ("never lets anyone else talk", "5 words (at most 4)"),
    ("naïve", "non-ASCII"), ("self_hating", "underscore"), ("brave", "the trait itself"), ("", "no label"),
])
def test_validate_item_rejects(label, why):
    item, got = O.validate_item(F.item(label) if label else {"label": "", "gloss": "x"}, source_label="brave",
                                source_stem="brave")
    assert item is None and got.startswith(why), got


@pytest.mark.parametrize("label", ["overbearing", "understated", "nonchalant", "hard on oneself", "slow to forgive",
                                   "un-American", "self-scolding", "Machiavellian"])
def test_validate_item_keeps_real_words(label):
    item, why = O.validate_item(F.item(label), source_label="brave", source_stem="brave")
    assert why is None and item["label"] == label


def test_gloss_notes_not_rejections():
    item, why = O.validate_item({"label": "craven", "gloss": "Craven is " + "very " * 30, "polysemy": "yes"})
    assert why is None and item["polysemy"] is None
    assert any("This means" in n for n in item["notes"]) and any("words" in n for n in item["notes"])
    assert O.validate_item({"label": "craven"}) == (None, "no gloss")


def test_rejected_items_are_counted_not_guessed():
    text = F.reply("excess", excess=F.item("over-brave"), deficiency=F.item("timid"),
                   remode={"habit": F.item("takes risks for the thrill of it every time")})
    rep, _ = O.parse_operator_reply(text, principal=False, source_label="brave", source_stem="brave")
    assert rep.excess is None and rep.deficiency["label"] == "timid" and rep.remode["habit"] is None
    assert {x["slot"] for x in rep.rejected} == {"excess", "remode:habit"}
    assert O.rejection_counts([rep]) == {"9 words": 1, "over-/under-/too-/non-X": 1}


# --------------------------------------------------------------------------- the guard

def test_guard_on_the_way_out_drops_principal_answers_for_a_non_principal_trait():
    text = F.reply("mean", principal=True, retarget={"the_user": F.item("user-pleasing"), "self": F.item("hard on oneself")})
    rep, why = O.parse_operator_reply(text, principal=False)
    assert why is None and "the_user" not in rep.retarget and rep.retarget["self"]["label"] == "hard on oneself"
    assert any("the guard" in p for p in rep.problems)
    assert [x for x in rep.rejected if x["why"] == "guard"][0]["label"] == "user-pleasing"
    rep2, _ = O.parse_operator_reply(text, principal=True)
    assert rep2.retarget["the_user"]["label"] == "user-pleasing" and not rep2.rejected


def test_guard_on_the_way_in(inputs):
    b = by(inputs)
    O.check_principal(b["obedient"], 3)
    with pytest.raises(ValueError, match="the guard"):
        O.check_principal(b["obedient"], 4)            # listed at stage 1, refused under a higher bar
    forged = O.TraitInput(**{**b["brave"].__dict__, "principal_targets": True})
    with pytest.raises(ValueError, match="the guard"):
        O.check_principal(forged, 3)
    with pytest.raises(ValueError):
        asyncio.run(O.run_operators([forged], client=F.ScriptedClient({}), model=O.MODEL, usage=None, system=SYSTEM,
                                    run_id="r"))


def test_principal_only_reply_and_skip(inputs, corpus):
    only = O.build_inputs(None, data_dir=corpus, regions_path=corpus / "candidates" / "corpus_regions.json",
                          principal_min_score=2, principal_only=True)
    text = json.dumps({"reasoning": "r", "retarget": {"the_user": F.item("user-deferring"), "the_operator": None,
                                                      "the_developer": None, "self": F.item("x")}})
    rep, why = O.parse_operator_reply(text, principal=True, principal_only=True)
    assert why is None and rep.position is None and set(rep.retarget) == set(O.PRINCIPAL_TARGETS)
    assert rep.opposite is None and rep.remode == {} and any("unknown target" in p for p in rep.problems)
    # the run sends no other operator: the user turn lists only the principal slots
    d = json.loads(O.render_operator_user(only[0]))
    assert d["retarget_toward"] == list(O.PRINCIPAL_TARGETS) and d["answer_only"] == "retarget"
    # traits already answered at a higher stage are skipped
    recs = [{"stage": "operators", "stem": "obedient", "label": "obedient", "principal_targets": True,
             "text": F.reply("mean", principal=True)},
            {"stage": "operators", "stem": "brave", "label": "brave", "principal_targets": False,
             "text": F.reply("mean")},
            {"stage": "operators", "stem": "honest", "label": "honest", "principal_targets": True, "text": "garbled"}]
    assert O.already_principal(recs) == {"obedient"}


# --------------------------------------------------------------------------- the calls

def test_failed_calls_retried_once_left_unparsed_and_every_response_charged(inputs, tmp_path):
    b = by(inputs)
    sel = [b["brave"], b["gloomy"], b["obedient"]]
    script = F.script_for(sel, SYSTEM, {
        "brave": F.reply("mean", opposite=F.item("cowardly")),
        "gloomy": ["garbled", "still garbled"],                         # both attempts fail: left unparsed
        "obedient": ["{bad", F.reply("excess", principal=True, retarget={"the_operator": F.item("operator-pleasing")})],
    })
    client = F.ScriptedClient(script)
    usage = GuardedUsage(budget_usd=5.0)
    out = tmp_path / "responses.jsonl"
    run = asyncio.run(O.run_operators(sel, client=client, model=O.MODEL, usage=usage, system=SYSTEM, run_id="r1",
                                      out_path=out, now=lambda: "2026-10-13T00:00:00+00:00"))
    assert set(run.samples) == {"brave", "obedient"} and run.errors == {("gloomy", 1): "unparseable"}
    assert run.n_calls == 5 and run.n_attempted == 3
    assert usage.n_calls == 5                                  # every response charged, unparseable ones too
    recs = O.read_responses(out)
    assert len(recs) == 5 and all(r["prompt_sha256"] and r["model"] == O.MODEL and r["charged_as"] == O.MODEL
                                  for r in recs)
    assert {(r["stem"], r["attempt"]) for r in recs} == {("brave", 1), ("gloomy", 1), ("gloomy", 2), ("obedient", 1),
                                                         ("obedient", 2)}
    assert all(r["sample"] == 1 for r in recs)
    assert run.samples["obedient"][1].retarget["the_operator"]["label"] == "operator-pleasing"
    assert next(r for r in recs if r["stem"] == "obedient")["principal_targets"] is True


def test_records_are_appended_before_parsing(inputs, tmp_path):
    """A reply that crashes nothing still reaches the file even when it does not parse."""
    b = by(inputs)
    out = tmp_path / "responses.jsonl"
    client = F.ScriptedClient(F.script_for([b["brave"]], SYSTEM, {"brave": "garbled"}))
    asyncio.run(O.run_operators([b["brave"]], client=client, model=O.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                run_id="r1", out_path=out))
    assert [r["text"] for r in O.read_responses(out)] == ["garbled", "garbled"]


def test_resume_sends_nothing_for_an_answered_prompt(inputs, tmp_path):
    b = by(inputs)
    sel = [b["brave"], b["timid"]]
    out = tmp_path / "responses.jsonl"
    script = F.script_for(sel, SYSTEM, {"brave": F.reply("mean"), "timid": F.reply("deficiency")})
    asyncio.run(O.run_operators(sel, client=F.ScriptedClient(script), model=O.MODEL, usage=MultiModelUsage(),
                                system=SYSTEM, run_id="r1", out_path=out))
    client = F.ScriptedClient(script)
    run = asyncio.run(O.run_operators(sel, client=client, model=O.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="r1", out_path=out, resume=True))
    assert client.calls == [] and run.n_reused == 2 and run.samples["timid"][1].position == "deficiency"
    # another model, or a changed prompt, is sent again
    run = asyncio.run(O.run_operators(sel, client=F.ScriptedClient(F.script_for(sel, SYSTEM + " ", {
        "brave": F.reply("mean"), "timid": F.reply("mean")})), model=O.MODEL, usage=MultiModelUsage(),
        system=SYSTEM + " ", run_id="r1", out_path=out, resume=True))
    assert run.n_reused == 0 and run.n_calls == 2


def test_budget_stop_keeps_the_answer_that_crossed(inputs, tmp_path):
    b = by(inputs)
    sel = [b["brave"], b["timid"], b["honest"]]
    script = F.script_for(sel, SYSTEM, {s: F.reply("mean", principal=b[s].principal_targets) for s in b})
    usage = GuardedUsage(budget_usd=0.0001)
    run = asyncio.run(O.run_operators(sel, client=F.ScriptedClient(script), model=O.MODEL, usage=usage, system=SYSTEM,
                                      run_id="r1", out_path=tmp_path / "r.jsonl", concurrency=1))
    assert run.stopped_by_budget and run.n_answered == 1 and run.n_calls == 1
    assert len(O.read_responses(tmp_path / "r.jsonl")) == 1


def test_estimate_and_sample(inputs):
    e = O.estimate(inputs, SYSTEM)
    n_pr = sum(t.principal_targets for t in inputs)
    assert e["n_calls"] == len(inputs) and e["out_tok"] == O.EST_OUT_TOKENS * len(inputs) + 200 * n_pr
    assert O.EST_OUT_TOKENS == 1500 and 0 < e["usd"] < 0.02            # measured on the 2026-10-13 runs
    e3 = O.estimate(inputs, SYSTEM, samples=3)
    assert e3["n_calls"] == 3 * len(inputs) and e3["out_tok"] == 3 * e["out_tok"] and e3["in_tok"] == 3 * e["in_tok"]
    pairs = [("brave", "timid"), ("dishonest", "honest"), ("obedient", "rebellious")]
    s = O.stratified_sample(inputs, 8, 0, pairs=pairs, n_pairs=2, min_principal=2)
    stems = {t.stem for t in s}
    assert len(s) == 8 and sum(t.principal_targets for t in s) >= 2
    assert sum(1 for a, b in pairs if a in stems and b in stems) >= 2
    assert [t.stem for t in O.stratified_sample(inputs, 8, 0, pairs=pairs, n_pairs=2, min_principal=2)] == \
        [t.stem for t in s]                                                    # seeded
    assert [t.stem for t in s] == [t.stem for t in inputs if t.stem in stems]  # input order


def test_arrangement_kinds():
    assert O.arrangement_kinds(None) == "unclassified"
    assert O.arrangement_kinds({"kind": "pair", "members": ["a", "b"]}) == "pair"
    assert O.arrangement_kinds([{"kind": "pair", "members": ["a", "b"]},
                                {"kind": "5-orthoplex", "members": list("abcdefghij")}]) == "pair, 5-orthoplex"
    assert O.arrangement_kinds({"kind": "nonsense"}) == "unclassified"


# --------------------------------------------------------------------------- stop reasons (review B1, 2026-10-13)

def test_llm_records_stop_details_when_the_response_has_them():
    from types import SimpleNamespace

    from assistant_axis.gapgen import llm
    assert llm.stop_details(F.refusal())["category"] == "reasoning_extraction"
    assert llm.stop_details(F.refusal(as_dict=True)) == {"type": "refusal", "category": "reasoning_extraction",
                                                         "explanation": "blocked as it seems to violate the terms of "
                                                                        "service"}
    dumped = SimpleNamespace(model_dump=lambda: {"type": "refusal", "category": "x"})
    assert llm.stop_details(SimpleNamespace(stop_details=dumped)) == {"type": "refusal", "category": "x"}
    assert llm.stop_details(SimpleNamespace()) is None


def test_a_refusal_is_a_failed_call_retried_once_counted_and_never_reused(inputs, tmp_path):
    b = by(inputs)
    sel = [b["brave"], b["timid"], b["gloomy"]]
    script = F.script_for(sel, SYSTEM, {
        "brave": F.refusal(),                                                     # refused both times
        "timid": [F.refusal(as_dict=True), F.reply("deficiency")],                # refused, then answered
        "gloomy": [F.truncated(F.reply("excess")), F.reply("excess")],           # cut at max_tokens, then answered
    })
    usage = MultiModelUsage()
    out = tmp_path / "responses.jsonl"
    run = asyncio.run(O.run_operators(sel, client=F.ScriptedClient(script), model=O.MODEL, usage=usage,
                                      system=SYSTEM, run_id="r1", out_path=out))
    assert set(run.samples) == {"timid", "gloomy"}
    assert run.errors == {("brave", 1): "stop_reason refusal (reasoning_extraction)"}
    assert run.failures == {"refusal": 3, "max_tokens": 1} and run.n_calls == 6 and usage.n_calls == 6
    recs = O.read_responses(out)
    refused = [r for r in recs if r["stop_reason"] == "refusal"]
    assert len(refused) == 3 and all(r["failure"].startswith("stop_reason refusal") for r in refused)
    assert all(r["stop_details"]["category"] == "reasoning_extraction" for r in refused)
    cut = next(r for r in recs if r["stop_reason"] == "max_tokens")
    assert cut["failure"] == "stop_reason max_tokens" and O.reply_from_record(cut) == (None, "stop_reason max_tokens")
    ok = [r for r in recs if r["stop_reason"] == "end_turn"]
    assert len(ok) == 2 and all(r["failure"] is None for r in ok)
    ss = O.stop_summary(recs)
    assert ss["n_failed"] == 4 and ss["stop_reasons"] == {"max_tokens": 1, "refusal": 3}
    assert ss["categories"] == {"reasoning_extraction": 3} and "4 of 6 responses" in ss["line"]
    assert O.stop_summary([r for r in recs if r["stop_reason"] == "end_turn"])["line"] is None
    # a resumed run reuses the answers and sends the refused trait again
    again = F.ScriptedClient(F.script_for(sel, SYSTEM, {"brave": F.reply("mean")}))
    run2 = asyncio.run(O.run_operators(sel, client=again, model=O.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                       run_id="r1", out_path=out, resume=True))
    assert run2.n_reused == 2 and len(again.calls) == 1 and set(run2.samples) == {"brave", "timid", "gloomy"}
