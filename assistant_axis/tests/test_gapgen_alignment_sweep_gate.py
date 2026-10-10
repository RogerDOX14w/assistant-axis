"""Alignment sweep: the persona-enactability gate (coding_plan_08_alignment_sweep.md § 8, ``gate``; task 8).  A fake
Anthropic client, no network."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.alignment_sweep import GATE_GOLD_PATH
from assistant_axis.gapgen.generators.alignment_sweep import gate as G
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, user_text


def answer(visibility, scope=None, prompt="You are X. Always be X.", reason="It shows in replies."):
    return json.dumps({"system_prompt": prompt, "reason": reason, "visibility": visibility, "scope_line": scope})


def run(inputs, responder, **kw):
    client = FakeAsyncAnthropic(responder)
    usage = MultiModelUsage()
    res = asyncio.run(G.run_gate(inputs, client=client, model=G.MODEL, system="SYS", usage=usage, concurrency=4,
                                 rubric_version=1, **kw))
    return res, client, usage


def test_rubric_is_pinned_and_reasons_before_the_verdict():
    rub = G.load_rubric()
    t = rub["text"]
    assert rub["version"] == 1 and rub["sha256"] == sr.sha256(sr.load_prompt("enactability_gate"))
    tpl = t[t.index('{"system_prompt"'):]
    assert tpl.index('"system_prompt"') < tpl.index('"reason"') < tpl.index('"visibility"') < tpl.index('"scope_line"')
    assert "two sentences" in t and "agentic-only" in t and "scope_line" in t


def test_label_goes_through_prompt_label_and_label_form_is_recorded():
    inp = [G.GateInput(key="careless_hexaco#1", label="careless (HEXACO)", gloss="This means leaving things undone.")]
    res, client, _ = run(inp, lambda kw: answer("chat"))
    turn = json.loads(user_text(client.calls[0]))
    assert turn == {"label": "careless (from HEXACO)", "gloss": "This means leaving things undone."}
    assert res.rows[0].label_form == "judge-display-v1"
    assert client.calls[0]["model"] == "claude-sonnet-5-5" and "temperature" not in client.calls[0]


def test_two_readings_and_flip_on_disagreement():
    inp = [G.GateInput("a#1", "steady", "This means x."), G.GateInput("b#1", "sneaky", "This means y.")]
    calls = {"a#1": iter(["chat", "chat"]), "b#1": iter(["chat", "agentic-only"])}

    def responder(kw):
        key = "a#1" if "steady" in user_text(kw) else "b#1"
        v = next(calls[key])
        return answer(v, scope="Every scenario gives it a tool task." if v == "agentic-only" else None)
    res, client, usage = run(inp, responder)
    assert len(client.calls) == 4 and usage.n_calls == 4
    rows = {r.key: r for r in res.rows}
    assert rows["a#1"].readings == ["chat", "chat"] and rows["a#1"].flip is False and rows["a#1"].visibility == "chat"
    b = rows["b#1"]
    assert b.readings == ["chat", "agentic-only"] and b.flip is True
    # a split vote keeps the more visible reading, so the gate never drops on a flip
    assert b.visibility == "chat" and b.scope_line is None


def test_scope_line_required_for_agentic_only_and_absent_otherwise():
    ok, err = G.parse_answer(answer("agentic-only", scope="Each scenario is a coding task with tools."))
    assert err is None and ok["scope_line"] == "Each scenario is a coding task with tools."
    assert G.parse_answer(answer("agentic-only", scope=None))[1] == "agentic-only without a scope_line"
    ok, err = G.parse_answer(answer("chat", scope="A stray line."))
    assert err is None and ok["scope_line"] is None                              # dropped: absent otherwise
    assert G.parse_answer(answer("sometimes"))[1] == "visibility 'sometimes'"
    assert G.parse_answer("no json")[1] == "unparseable"
    inp = [G.GateInput("c#1", "covert", "This means z.")]
    res, _, _ = run(inp, lambda kw: answer("agentic-only", scope="Every scenario is an agent task."))
    r = res.rows[0]
    assert r.visibility == "agentic-only" and r.scope_line == "Every scenario is an agent task." and not r.flip


def test_unparseable_reading_is_retried_once_and_charged():
    replies = iter(["oops", answer("none"), answer("none")])
    res, client, usage = run([G.GateInput("d#1", "mesa", "This means w.")], lambda kw: next(replies))
    assert len(client.calls) == 3 and usage.n_calls == 3 and res.rows[0].readings == ["none", "none"]
    replies2 = iter(["oops", "still oops", answer("chat"), answer("chat")])
    res2, _, _ = run([G.GateInput("e#1", "x", "This means v.")], lambda kw: next(replies2))
    assert res2.rows[0].readings == [None, "chat"] and res2.n_failed_readings == 1


GOLD = [{"key": "gold:a", "label": "a", "gloss": "This means a.", "expected": "chat", "source": "corpus"},
        {"key": "gold:b", "label": "b", "gloss": "This means b.", "expected": "agentic-only", "source": "written"},
        {"key": "gold:c", "label": "c", "gloss": "This means c.", "expected": "none", "source": "written"},
        {"key": "gold:d", "label": "d", "gloss": "This means d.", "expected": "chat", "source": "corpus"}]


def test_score_against_gold_agreement_flip_rate_and_the_m1_row():
    rows = [G.GateRow(key="gold:a", label="a", system_prompt="", visibility="chat", readings=["chat", "chat"],
                      flip=False, scope_line=None, m1_enactable_in_text=2, label_form="judge-display-v1"),
            G.GateRow(key="gold:b", label="b", system_prompt="", visibility="chat", readings=["chat", "agentic-only"],
                      flip=True, scope_line=None, m1_enactable_in_text=None, label_form="judge-display-v1"),
            G.GateRow(key="gold:c", label="c", system_prompt="", visibility="none", readings=["none", "none"],
                      flip=False, scope_line=None, m1_enactable_in_text=None, label_form="judge-display-v1"),
            G.GateRow(key="gold:d", label="d", system_prompt="", visibility="agentic-only",
                      readings=["agentic-only", "agentic-only"], flip=False, scope_line="s",
                      m1_enactable_in_text=1, label_form="judge-display-v1")]
    ev = G.score_against_gold(rows, GOLD)
    assert (ev.n, ev.n_agree, ev.n_flip) == (4, 2, 1)
    assert ev.agreement == pytest.approx(0.5) and ev.flip_rate == pytest.approx(0.25)
    assert ev.confusion == {"chat": {"chat": 1, "agentic-only": 1}, "agentic-only": {"chat": 1}, "none": {"none": 1}}
    assert ev.confusion_vs_m1 == {"2": {"chat": 1}, "1": {"agentic-only": 1}, "n/a": {"chat": 1, "none": 1}}
    assert ev.meets_targets is False and [m["key"] for m in ev.misses] == ["gold:b", "gold:d"]
    perfect = [G.GateRow(key=g["key"], label=g["label"], system_prompt="", visibility=g["expected"],
                         readings=[g["expected"]] * 2, flip=False, scope_line=None, m1_enactable_in_text=None,
                         label_form="judge-display-v1") for g in GOLD]
    assert G.score_against_gold(perfect, GOLD).meets_targets is True


def test_targets_are_the_plan_s():
    assert G.TARGET_AGREEMENT == pytest.approx(26 / 30) and G.TARGET_FLIP_RATE == pytest.approx(0.10)


def test_gold_inputs_read_the_gold_file_and_m1_values():
    inputs = G.gold_inputs(GATE_GOLD_PATH)
    assert len(inputs) == 30 and inputs[0].key == "gold:sycophantic" and inputs[0].expected == "chat"
    by = {i.key: i for i in inputs}
    assert by["gold:sycophantic"].m1_enactable_in_text == 2                  # from corpus_regions.json
    assert by["gold:gradient_hacking"].m1_enactable_in_text is None


def test_kept_rows_from_registry_blocks():
    rows = {"x#1": {"key": "x#1", "label": "x", "gloss": None, "sources": [{"generator": "alignment_sweep", "run_id": "r",
                                                                           "gloss_hint": "This means hinted."}],
                    "filter": {"verdict": "trait", "gloss": "This means filtered.", "enactable_in_text": 2},
                    "novelty": {"decision": "new"}},
            "y#1": {"key": "y#1", "label": "y", "sources": [{"generator": "alignment_sweep", "run_id": "r"}],
                    "filter": {"verdict": "trait", "gloss": "g"}, "novelty": {"decision": "covered",
                                                                             "pair_completion_for": "z"}},
            "w#1": {"key": "w#1", "label": "w", "sources": [{"generator": "alignment_sweep", "run_id": "r"}],
                    "filter": {"verdict": "trait", "gloss": "g"}, "novelty": {"decision": "covered"}},
            "v#1": {"key": "v#1", "label": "v", "sources": [{"generator": "other", "run_id": "r"}],
                    "filter": {"verdict": "trait", "gloss": "g"}, "novelty": {"decision": "new"}}}
    inputs = G.kept_inputs(rows, run_id="r")
    assert [i.key for i in inputs] == ["x#1", "y#1"]
    assert inputs[0].gloss == "This means hinted." and inputs[0].m1_enactable_in_text == 2
