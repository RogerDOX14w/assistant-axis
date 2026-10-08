"""The Roget label placement check (workstream 2; QUESTIONS 39, Roger 2026-10-08): Sonnet 5.5 re-judges every
label whose two routes did not agree, Opus 5.5 referees where Sonnet differs from the current primary.  No
network: a fake Anthropic client."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.generators.roget import mapping as M
from assistant_axis.gapgen.generators.roget import placement as PL
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.roget_fakes import make_index

SYSTEM = 'Pick the home.\n{"reason": "<r>", "head": "<id>"|"none"}'


def world():
    return make_index([
        {"id": "479", "title": "Confutation", "adj": [["confuting", "refutable"]], "noun": [["confutation"]]},
        {"id": "515", "title": "Imagination", "adj": [["imaginative", "inventive"], ["fanciful"]],
         "noun": [["imagination", "invention"], ["fancy"]]},
        {"id": "544", "title": "Falsehood", "adj": [["false", "untrue", "lying", "mendacious", "fabricated", "made up",
                                                    "invented", "spurious"]], "noun": [["falsehood", "lie"]]},
        {"id": "864", "title": "Caution", "adj": [["cautious"]], "noun": [["caution"]]},
        {"id": "604a", "title": "Perseverance", "adj": [["persevering"]]},
    ])


def entry(primary, route, semantic=(), lexical=(), secondary=(), label=None, source="existing"):
    return {"label": label, "source": source, "status": None, "primary": primary, "secondary": list(secondary),
            "route": route, "confidence": 0.5, "semantic": [{"head_id": h, "sim": 0.4, "rank": i + 1}
                                                              for i, h in enumerate(semantic)],
            "lexical": [{"head_id": h, "strength": "exact_adj", "item": "x", "block": "Adj", "group_index": 0}
                        for h in lexical], "llm": None}


def records():
    return [M.LabelRecord("confabulatory", "confabulatory", "This means filling gaps with plausible invention.",
                          "existing"),
            M.LabelRecord("careful", "careful", "This means looking before one leaps.", "existing"),
            M.LabelRecord("aggrieved", "aggrieved", None, "queued", status="candidate"),
            M.LabelRecord("stubborn", "stubborn", "This means holding on.", "existing")]


def label_heads():
    return {"confabulatory": entry("479", "semantic", semantic=["479", "515", "544"], label="confabulatory"),
            "careful": entry("864", "agree", semantic=["864"], lexical=["864"], label="careful"),
            "aggrieved": entry(None, "none", semantic=["515", "544"], label="aggrieved", source="queued"),
            "stubborn": entry("604a", "rule", semantic=["604a", "864"], lexical=["604a"], secondary=["864"],
                              label="stubborn")}


# --------------------------------------------------------------------------- items

def test_head_words_adjectives_then_nouns():
    idx = world()
    adj, nouns = PL.head_words(idx.heads["544"])                         # 8 adjectives, 2 nouns
    assert nouns == ["falsehood", "lie"] and len(adj) == 8               # more adjectives when the nouns run out
    assert adj[:6] == ["false", "untrue", "lying", "mendacious", "fabricated", "made up"]
    adj, nouns = PL.head_words(idx.heads["515"], n=4, n_adj=2)
    assert adj == ["imaginative", "inventive"] and nouns == ["imagination", "invention"]
    p = PL.head_payload(idx.heads["604a"])
    assert p == {"id": "604a", "title": "Perseverance", "class": "Words relating to the voluntary powers",
                 "section": "Volition in general", "adjectives": ["persevering"], "nouns": []}


def test_candidate_heads_dedupe_cap_and_current():
    e = entry("9", "semantic", semantic=["1", "2", "3", "4", "5", "6"], lexical=["2", "7", "8", "10", "11"])
    assert PL.candidate_heads(e, current=None) == ["1", "2", "3", "4", "5", "7", "8", "10"]
    assert PL.candidate_heads(e) == ["1", "2", "3", "4", "5", "7", "8", "9"]          # the current primary kept
    idx = world()
    e2 = entry("479", "semantic", semantic=["479", "999", "515"])
    assert PL.candidate_heads(e2, index=idx) == ["479", "515"]                       # heads not in the index dropped


def test_shown_order_is_seeded_by_the_label():
    a = PL.shown_order(["1", "2", "3", "4", "5"], "x")
    assert a == PL.shown_order(["5", "4", "3", "2", "1"], "x") and sorted(a) == ["1", "2", "3", "4", "5"]
    assert len({tuple(PL.shown_order(list("abcdefgh"), f"s{i}")) for i in range(6)}) > 1


def test_select_items_and_render():
    idx = world()
    items, skipped = PL.select_items(label_heads(), records(), idx)
    assert [it.stem for it in items] == ["aggrieved", "confabulatory", "stubborn"] and skipped["agree"] == 1
    conf = next(it for it in items if it.stem == "confabulatory")
    assert sorted(conf.candidates) == ["479", "515", "544"] and conf.current == "479" and conf.route == "semantic"
    u = PL.render_user(conf, idx)
    lines = u.split("\n")
    assert lines[0].startswith('{"trait": {"label": "confabulatory", "description": ') and lines[1] == ' "heads": ['
    d = json.loads(u)
    assert [h["id"] for h in d["heads"]] == conf.candidates
    agg = json.loads(PL.render_user(next(it for it in items if it.stem == "aggrieved"), idx))
    assert agg["trait"] == {"label": "aggrieved"}                                      # no description key at all


def test_rubric_is_pinned_and_reason_comes_first():
    rub = PL.load_rubric()
    assert sr.current_versions(names=sr.GENERATOR_NAMES)[PL.RUBRIC_NAME] == (rub["version"], rub["sha256"])
    assert rub["text"].index('"reason"') < rub["text"].index('"head"')
    assert '"none"' in rub["text"]


# --------------------------------------------------------------------------- parsing

def test_parse_answer():
    ids = ["479", "515", "604a"]
    assert PL.parse_answer('```json\n{"reason": "r", "head": "515"}\n```', ids) == ({"head": "515", "reason": "r"}, None)
    assert PL.parse_answer('{"reason": "r", "head": "None"}', ids)[0] == {"head": None, "reason": "r"}
    assert PL.parse_answer('{"reason": "r", "head": null}', ids)[0]["head"] is None
    assert PL.parse_answer('{"reason": "r", "head": "999"}', ids) == (None, "head 999 not offered")
    assert PL.parse_answer('{"reason": "r", "head": "604a"}', ids)[0]["head"] == "604a"
    assert PL.parse_answer("no json here", ids) == (None, "unparseable")
    assert PL.parse_answer(None, ids) == (None, "no response")


# --------------------------------------------------------------------------- the calls

def responder(by_stem: dict, *, bad_first=()):
    seen = set()

    def respond(kw):
        d = json.loads(user_text(kw))
        label = d["trait"]["label"]
        if label in bad_first and label not in seen:
            seen.add(label)
            return "I am not sure."
        head = by_stem.get((kw["model"], label), by_stem.get(label, "none"))
        return json.dumps({"reason": f"because {label}", "head": head})
    return respond


def run(c):
    return asyncio.run(c)


def test_run_stage_one_call_per_label_with_one_retry():
    idx = world()
    items, _ = PL.select_items(label_heads(), records(), idx)
    client = FakeAsyncAnthropic(responder({"confabulatory": "544", "aggrieved": "none", "stubborn": "604a"},
                                          bad_first={"stubborn"}))
    logged = []
    res = run(PL.run_stage(items, idx, stage="sonnet", client=client, model=PL.SONNET, system=SYSTEM,
                           usage=MultiModelUsage(), on_record=logged.append))
    assert len(client.calls) == 4 and len(logged) == 4                      # three labels, one retry
    assert res.answers["confabulatory"]["head"] == "544" and res.answers["aggrieved"]["head"] is None
    assert res.answers["stubborn"] == {"head": "604a", "reason": "because stubborn", "model": PL.SONNET, "attempts": 2}
    kw = client.calls[0]
    assert system_text(kw) == SYSTEM and kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "temperature" not in kw and kw["model"] == PL.SONNET
    assert {r["stage"] for r in logged} == {"sonnet"} and all(r["prompt_sha256"] == sr.sha256(SYSTEM) for r in logged)


def test_run_stage_stops_at_the_budget():
    idx = world()
    items, _ = PL.select_items(label_heads(), records(), idx)
    client = FakeAsyncAnthropic(lambda kw: make_response(responder({})(kw), input_tokens=100000, output_tokens=0))
    usage = GuardedUsage(budget_usd=0.3)                                       # $0.20 a call on Sonnet 5.5
    res = run(PL.run_stage(items, idx, stage="sonnet", client=client, model=PL.SONNET, system=SYSTEM, usage=usage,
                           concurrency=1))
    assert res.stopped_by_budget and len(client.calls) == 2 and len(res.answers) == 2


# --------------------------------------------------------------------------- the decision and the record

def test_referee_final_and_apply():
    idx = world()
    lh = label_heads()
    items, _ = PL.select_items(lh, records(), idx)
    by = {it.stem: it for it in items}
    sonnet = {"confabulatory": {"head": "544", "reason": "s1", "model": PL.SONNET},
              "aggrieved": {"head": "515", "reason": "s2", "model": PL.SONNET},
              "stubborn": {"head": "604a", "reason": "s3", "model": PL.SONNET}}
    assert [s for s in by if PL.needs_referee(by[s], sonnet[s])] == ["aggrieved", "confabulatory"]
    assert not PL.needs_referee(by["stubborn"], None)
    opus = {"confabulatory": {"head": None, "reason": "o1", "model": PL.OPUS},
            "aggrieved": {"head": "515", "reason": "o2", "model": PL.OPUS}}
    assert PL.final_answer(by["stubborn"], sonnet["stubborn"], None) == ("604a", "sonnet")
    assert PL.final_answer(by["aggrieved"], sonnet["aggrieved"], None) == (None, "unchecked")
    rub = {"version": 1, "sha256": "abc"}
    new, counts = PL.apply_results(lh, items, sonnet, opus, rubric=rub, checked_at="t")
    assert counts == {"unplaced": 1, "newly_placed": 1, "unchanged": 1}
    c = new["confabulatory"]
    assert c["primary"] is None and c["route"] == "none" and c["secondary"] == []
    assert c["llm"]["previous_primary"] == "479" and c["llm"]["previous_route"] == "semantic"
    assert c["llm"]["sonnet"] == {"head": "544", "reason": "s1", "model": PL.SONNET}
    assert c["llm"]["opus"] == {"head": None, "reason": "o1", "model": PL.OPUS} and c["llm"]["decided_by"] == "opus"
    a = new["aggrieved"]
    assert a["primary"] == "515" and a["route"] == "llm" and a["llm"]["outcome"] == "newly_placed"
    s = new["stubborn"]
    assert s["primary"] == "604a" and s["route"] == "rule" and s["secondary"] == ["864"] and s["llm"]["opus"] is None
    assert new["careful"] == lh["careful"]                                    # agree: untouched
    assert lh["confabulatory"]["primary"] == "479"                            # the input is not modified
    # a second check reads the placement before the first one
    items2, _ = PL.select_items(new, records(), idx)
    assert {it.stem: (it.current, it.route) for it in items2}["confabulatory"] == ("479", "semantic")
    # a move takes the new primary out of the secondaries
    moved, cnt = PL.apply_results(lh, [by["stubborn"]], {"stubborn": {"head": "864", "reason": "s", "model": PL.SONNET}},
                                  {"stubborn": {"head": "864", "reason": "o", "model": PL.OPUS}}, rubric=rub,
                                  checked_at="t")
    assert cnt == {"moved": 1} and moved["stubborn"]["primary"] == "864" and moved["stubborn"]["secondary"] == []
    assert moved["stubborn"]["route"] == "llm" and moved["stubborn"]["confidence"] == 0.8


def test_reusable_answers_need_the_same_stage_model_and_text():
    recs = [{"stage": "sonnet", "model": PL.SONNET, "prompt_sha256": "a", "stem": "x", "answer": {"head": "1", "reason": "r"},
             "attempt": 1},
            {"stage": "sonnet", "model": PL.SONNET, "prompt_sha256": "b", "stem": "y", "answer": {"head": "1", "reason": "r"}},
            {"stage": "opus", "model": PL.OPUS, "prompt_sha256": "a", "stem": "x", "answer": {"head": None, "reason": "r"}},
            {"stage": "sonnet", "model": PL.SONNET, "prompt_sha256": "a", "stem": "z", "answer": None}]
    assert PL.reusable_answers(recs, stage="sonnet", model=PL.SONNET, prompt_sha="a") == \
        {"x": {"head": "1", "reason": "r", "model": PL.SONNET, "attempts": 1}}
    assert PL.reusable_answers(recs, stage="opus", model=PL.OPUS, prompt_sha="a")["x"]["head"] is None


def test_reusable_answers_with_users_need_the_same_user_turn():
    recs = [{"stage": "sonnet", "model": PL.SONNET, "prompt_sha256": "a", "stem": "x", "user": "U1",
             "answer": {"head": "1", "reason": "r"}, "attempt": 1},
            {"stage": "sonnet", "model": PL.SONNET, "prompt_sha256": "a", "stem": "y", "user": "old text",
             "answer": {"head": "2", "reason": "r"}, "attempt": 1}]
    got = PL.reusable_answers(recs, stage="sonnet", model=PL.SONNET, prompt_sha="a", users={"x": "U1", "y": "new text"})
    assert set(got) == {"x"}                                   # y's description changed: asked again
    assert set(PL.reusable_answers(recs, stage="sonnet", model=PL.SONNET, prompt_sha="a", users={})) == set()


def test_select_items_unchecked_only():
    idx = world()
    lh = label_heads()
    lh["confabulatory"]["llm"] = {"check": PL.RUBRIC_NAME, "previous_primary": "479", "previous_route": "semantic",
                                  "previous_secondary": []}
    items, skipped = PL.select_items(lh, records(), idx, unchecked_only=True)
    assert [it.stem for it in items] == ["aggrieved", "stubborn"] and skipped["checked"] == 1
    items, skipped = PL.select_items(lh, records(), idx)
    assert [it.stem for it in items] == ["aggrieved", "confabulatory", "stubborn"] and skipped["checked"] == 0


def test_cumulative_meta_keeps_every_run_and_counts_the_labels():
    labels = {"a": {"llm": {"check": PL.RUBRIC_NAME, "outcome": "moved", "opus": {"head": "1"}}},
              "b": {"llm": {"check": PL.RUBRIC_NAME, "outcome": "unchanged", "opus": None}},
              "c": {"llm": None}}
    first = {"rubric": {"version": 1}, "models": {"sonnet": PL.SONNET}, "n_checked": 583, "outcomes": {"moved": 93},
             "cost_usd_this_run": 4.97}
    run2 = {"rubric": {"version": 1}, "models": {"sonnet": PL.SONNET}, "n_checked": 2, "outcomes": {"moved": 1},
            "cost_usd_this_run": 0.5}
    m = PL.cumulative_meta(first, run2, labels)               # a block written before runs were kept: run 1
    assert m["runs"] == [first, run2] and m["n_checked"] == 2 and m["outcomes"] == {"moved": 1, "unchanged": 1}
    assert m["n_referee"] == 1 and m["rubric"] == {"version": 1} and "cost_usd" not in m
    m3 = PL.cumulative_meta(m, run2, labels)
    assert len(m3["runs"]) == 3 and m3["n_checked"] == 2
    assert PL.cumulative_meta(None, run2, labels)["runs"] == [run2]
    # no run: only the totals are recounted (map --update moved a record away)
    m4 = PL.cumulative_meta(m3, None, {"a": labels["a"], "b": {"llm": None}})
    assert m4["runs"] == m3["runs"] and m4["n_checked"] == 1 and m4["outcomes"] == {"moved": 1}
    assert m4["rubric"] == {"version": 1}


def test_save_keeps_the_payload_and_the_recorded_inputs(tmp_path):
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    lh = label_heads()
    src = tmp_path / "x.txt"
    src.write_text("x")
    p = tmp_path / "label_heads.json"
    env = json_metadata({"rules_version": 1, "sem_floor": 0.4, "labels": lh},
                        inputs=[current_file_input("roget_heads", src)])
    p.write_text(json.dumps(env))
    PL.save_label_heads_checked(p, {**lh, "careful": {**lh["careful"], "route": "agree"}},
                                extra_inputs=[current_file_input("placement_rubric", src)], meta={"n_checked": 3})
    d = json.loads(p.read_text())
    assert d["result"]["rules_version"] == 1 and d["result"]["placement_check"] == {"n_checked": 3}
    assert {i["dep_key"] for i in d["_provenance"]["inputs"]} == {"roget_heads", "placement_rubric"}
    assert M.load_label_heads(p) == {**lh, "careful": {**lh["careful"], "route": "agree"}}
