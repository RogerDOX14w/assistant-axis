"""Structural generators, A: the modernise call's parse, retries and reuse (coding_plan_09 sections 5 and 8; review
S1, 2026-10-13: a rerun reuses every recorded answer to the same prompt, the retry of left-out rows included).  No
network: a client scripted by the rendered prompt's hash."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen.generators.structural import modernise as M
from assistant_axis.gapgen.generators.structural import prompts as P
from assistant_axis.gapgen.generators.structural.classical import load_all
from assistant_axis.gapgen.generators.structural.operators import prompt_sha256
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests import structural_fakes as F

SYSTEM = P.modernise_system()


def answer(rows, *, skip=()) -> str:
    return json.dumps({"rows": [{"id": r.id, "reasoning": "r", "labels": [r.item], "gloss": "This means it.",
                                 "polysemy": False} for r in rows if r.id not in set(skip)]})


@pytest.fixture(scope="module")
def rows():
    return load_all(["aristotle"])[:24]                 # two units at 20 a call: 20 and 4


def script(rows, answers: dict) -> dict:
    """``{prompt sha: answer}`` for units given as tuples of row ids."""
    by = {r.id: r for r in rows}
    out = {}
    for ids, text in answers.items():
        unit = [by[i] for i in ids]
        out[prompt_sha256(SYSTEM, M.render_modernise_user(unit, siblings_from=rows))] = text
    return out


def test_parse_modernise():
    rows = load_all(["aristotle"])[:3]
    ids = [r.id for r in rows]
    text = json.dumps({"rows": [
        {"id": ids[0], "reasoning": "r", "labels": ["cowardly", "too timid", "faint-hearted", "craven", "yellow"],
         "gloss": "This means x.", "polysemy": False},
        {"id": ids[1], "reasoning": "r", "labels": ["over-brave"], "gloss": "This means y."},
        {"id": "aristotle:nowhere:mean", "reasoning": "r", "labels": ["z"], "gloss": "This means z."}]})
    items, why = M.parse_modernise(text, ids=ids)
    assert why is None and [it.id for it in items] == [ids[0]]                   # the row with no usable label is out
    it = items[0]
    assert it.labels == ["cowardly", "faint-hearted", "craven"] and len(it.rejected_labels) == 1
    assert any("labels" in n for n in it.notes)
    assert M.parse_modernise("garbled", ids=ids) == (None, "unparseable")
    assert M.parse_modernise(json.dumps({"rows": []}), ids=ids) == (None, "no usable row")


def test_left_out_rows_are_asked_once_more_and_every_response_charged(rows, tmp_path):
    u1, u2 = [r.id for r in rows[:20]], [r.id for r in rows[20:]]
    missing = u1[5:7]
    client = F.ScriptedClient(script(rows, {tuple(u1): answer(rows[:20], skip=missing), tuple(u2): answer(rows[20:]),
                                            tuple(missing): answer([r for r in rows if r.id in missing])}))
    usage = MultiModelUsage()
    out = tmp_path / "responses.jsonl"
    run = asyncio.run(M.run_modernise(rows, client=client, model=M.MODEL, usage=usage, system=SYSTEM, run_id="a1",
                                      out_path=out))
    assert set(run.items) == {r.id for r in rows} and run.missing == [] and run.n_calls == 3 and usage.n_calls == 3
    recs = [json.loads(x) for x in out.read_text().splitlines()]
    assert [r["attempt"] for r in sorted(recs, key=lambda r: r["unit_id"])].count(2) == 1
    assert next(r for r in recs if r["attempt"] == 2)["ids"] == missing


def test_a_rerun_reuses_every_answer_the_retry_included(rows, tmp_path):
    u1, u2 = [r.id for r in rows[:20]], [r.id for r in rows[20:]]
    missing = u1[5:7]
    answers = {tuple(u1): answer(rows[:20], skip=missing), tuple(u2): answer(rows[20:]),
               tuple(missing): answer([r for r in rows if r.id in missing])}
    out = tmp_path / "responses.jsonl"
    asyncio.run(M.run_modernise(rows, client=F.ScriptedClient(script(rows, answers)), model=M.MODEL,
                                usage=MultiModelUsage(), system=SYSTEM, run_id="a1", out_path=out))
    quiet = F.ScriptedClient({})                                    # any call would raise: nothing is scripted
    run = asyncio.run(M.run_modernise(rows, client=quiet, model=M.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="a1", out_path=out, resume=True))
    assert quiet.calls == [] and run.n_calls == 0 and run.n_reused == 3
    assert set(run.items) == {r.id for r in rows} and run.missing == []
    # without resume, or under another prompt, the calls are made again
    again = F.ScriptedClient(script(rows, answers))
    asyncio.run(M.run_modernise(rows, client=again, model=M.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                run_id="a1", out_path=out, resume=False))
    assert len(again.calls) == 3


def test_a_reused_answer_with_rows_left_out_sends_only_the_retry(rows, tmp_path):
    u1, u2 = [r.id for r in rows[:20]], [r.id for r in rows[20:]]
    missing = u1[:2]
    out = tmp_path / "responses.jsonl"
    first = F.ScriptedClient(script(rows, {tuple(u1): answer(rows[:20], skip=missing), tuple(u2): answer(rows[20:]),
                                           tuple(missing): "garbled"}))
    run = asyncio.run(M.run_modernise(rows, client=first, model=M.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="a1", out_path=out))
    assert run.missing == missing
    second = F.ScriptedClient(script(rows, {tuple(missing): answer([r for r in rows if r.id in missing])}))
    run = asyncio.run(M.run_modernise(rows, client=second, model=M.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="a1", out_path=out, resume=True))
    assert len(second.calls) == 1 and run.missing == [] and run.n_reused == 2


def test_modern_rows_merge_and_file(rows, tmp_path):
    u1, u2 = [r.id for r in rows[:20]], [r.id for r in rows[20:]]
    run = asyncio.run(M.run_modernise(rows, client=F.ScriptedClient(script(rows, {
        tuple(u1): answer(rows[:20]), tuple(u2): answer(rows[20:])})), model=M.MODEL, usage=MultiModelUsage(),
        system=SYSTEM, run_id="a1"))
    mr = M.modern_rows(rows, run, model=M.MODEL, run_id="a1")
    assert [r.id for r in mr] == [r.id for r in rows] and mr[0].labels == [rows[0].item]
    p = tmp_path / "classical_modern.jsonl"
    assert M.write_modern(mr, p) is None and M.write_modern(mr, p) is None
    assert M.load_modern(p) == mr
    merged = M.merge_modern(mr[:5], mr[3:8], order=[r.id for r in rows])
    assert [r.id for r in merged] == [r.id for r in rows[:8]]


def test_a_refused_call_is_a_failure_retried_and_never_reused(rows, tmp_path):
    """Review B1 (2026-10-13): a response that stopped other than end_turn is a failed call."""
    u1, u2 = [r.id for r in rows[:20]], [r.id for r in rows[20:]]
    out = tmp_path / "responses.jsonl"
    client = F.ScriptedClient(script(rows, {tuple(u1): [F.refusal(), answer(rows[:20])], tuple(u2): answer(rows[20:])}))
    run = asyncio.run(M.run_modernise(rows, client=client, model=M.MODEL, usage=MultiModelUsage(), system=SYSTEM,
                                      run_id="a1", out_path=out))
    assert run.failures == {"refusal": 1} and run.missing == [] and run.n_calls == 3 and run.n_units_ok == 1
    recs = [json.loads(x) for x in out.read_text().splitlines()]
    bad = [r for r in recs if r["failure"]]
    assert len(bad) == 1 and bad[0]["stop_details"]["category"] == "reasoning_extraction"
    assert all(r["prompt_sha256"] not in M.reusable([r], model=M.MODEL) for r in bad)
