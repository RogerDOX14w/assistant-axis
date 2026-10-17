"""LLM-entropy generator: the calls, the runner and both transports (coding_plan_06 section 8, ``calls``).  A fake
Anthropic client scripted by prompt hash and a fake batch client; no network."""
from __future__ import annotations

import json
import re

import pytest

from assistant_axis.gapgen.batches import BatchTransport
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.generators.llm_entropy import calls as C
from assistant_axis.gapgen.generators.llm_entropy import prompts as P
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, cost_for_usage
from assistant_axis.tests import llm_entropy_fakes as F
from assistant_axis.tests.fake_anthropic import make_response

SYSTEM = P.load_rubric(P.SCAFFOLD_RUBRIC)


def _calls(n_prompts=3, runs=(1, 2, 3), model=C.HAIKU):
    ps = P.grid_prompts("a")[:n_prompts]
    return C.generation_calls(ps, runs=runs, model=model, system=SYSTEM["text"], rubric=SYSTEM)


def _good(labels=("zzalpha", "zzbeta")):
    return F.reply_items(list(labels))


def runner(tmp_path, client, *, usage=None, transport=None, resume=(), **kw):
    r = C.EntropyRunner(client=client, batch_id="r_llm_entropy", run_id="r",
                        usage=usage if usage is not None else GuardedUsage(budget_usd=10.0),
                        responses_path=tmp_path / "responses.jsonl", resume_records=resume, retry_delays=(), **kw)
    if transport is not None:
        r.transport = transport(r)
    return r


def _records(tmp_path):
    return [json.loads(x) for x in (tmp_path / "responses.jsonl").read_text().splitlines() if x.strip()]


def test_custom_ids_are_short_legal_and_distinct():
    cs = _calls(5) + _calls(5, model=C.SONNET)
    long = C.EntropyCall(family="e", prompt_id="e:frame:" + "x" * 80, run=3, model=C.HAIKU, system="s", user="u",
                         stage=2)
    ids = [c.custom_id for c in cs] + [long.custom_id, cs[0].retried().custom_id]
    assert all(len(i) <= 64 and re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids)
    assert len(set(ids)) == len(ids)                   # across prompts, runs, models and attempts
    c = cs[0]
    s2 = C.EntropyCall(**{**c.__dict__, "stage": 2})
    assert s2.custom_id != c.custom_id and s2.cache_key != c.cache_key
    assert c.custom_id.startswith("a-money_attitude-r1-s1-h55-")
    assert c.retried().cache_key == c.cache_key and c.retried().max_tokens == C.RETRY_MAX_TOKENS


def test_estimate_counts_every_call_at_the_models_rate():
    cs = _calls(2) + _calls(2, runs=(1,), model=C.SONNET)
    live = C.estimate_usd(cs)
    batch = C.estimate_usd(cs, batch=True)
    exp = sum(cost_for_usage(c.model, *C.call_tokens(c)) for c in cs)
    assert live == pytest.approx(exp) and batch == pytest.approx(exp / 2)
    assert C.call_tokens(cs[0])[1] == 2500
    lines = C.estimate_lines(cs, batch=True)
    assert any("6 calls" in x and "claude-haiku-5-5:batch" in x for x in lines)


def test_every_response_is_recorded_and_charged_failures_too_and_asked_once_more(tmp_path):
    cs = _calls(2, runs=(1,))
    bad, cut = cs[0], cs[1]
    script = {bad.prompt_sha256: "this is not JSON at all"}
    seen = []

    def default(kw):
        seen.append(kw["max_tokens"])
        if F.kwargs_hash(kw) == cut.prompt_sha256 and kw["max_tokens"] == C.MAX_TOKENS:
            return make_response('{"approach": "x", "items": [{"label": "zz', stop_reason="max_tokens")
        return _good()
    client = F.ScriptedAnthropic({}, default=lambda kw: script.get(F.kwargs_hash(kw)) or default(kw))
    r = runner(tmp_path, client)
    res = r.run("w", cs, C.parse_generation)
    recs = _records(tmp_path)
    assert len(recs) == 4                     # bad twice (unparseable both times), cut twice (stopped, then answered)
    by = [(x["prompt_id"], x["attempt"], x["ok"], x["max_tokens"]) for x in recs]
    assert (bad.prompt_id, 1, False, C.MAX_TOKENS) in by and (bad.prompt_id, 2, False, C.RETRY_MAX_TOKENS) in by
    assert (cut.prompt_id, 1, False, C.MAX_TOKENS) in by and (cut.prompt_id, 2, True, C.RETRY_MAX_TOKENS) in by
    assert r.usage.n_calls == 4 and all(x["usage_raw"] for x in recs)
    assert {x["failure"] for x in recs if x["prompt_id"] == cut.prompt_id and not x["ok"]} == \
        {"stop_reason max_tokens"}
    assert res.n_ok == 1 and bad.cache_key in res.failures and res.n_retried == 2


def test_a_refusal_is_a_failed_call_recorded_and_counted(tmp_path):
    c = _calls(1, runs=(1,), model=C.SONNET)[0]
    refusal = make_response("", output_tokens=0, stop_reason="refusal")
    refusal.stop_details = {"type": "refusal", "category": "reasoning_extraction"}
    client = F.ScriptedAnthropic({c.prompt_sha256: refusal})
    r = runner(tmp_path, client)
    res = r.run("w", [c], C.parse_generation)
    recs = _records(tmp_path)
    assert len(recs) == 2 and all(not x["ok"] for x in recs)
    assert recs[0]["failure"] == "stop_reason refusal (reasoning_extraction)"
    assert res.n_ok == 0 and res.stop_reasons["refusal"] == 2
    rate = C.parse_rate(recs)
    assert rate["n_units"] == 1 and rate["rate"] == 0.0


def test_resume_sends_nothing_for_an_answered_call(tmp_path):
    cs = _calls(2, runs=(1, 2))
    client = F.ScriptedAnthropic({c.prompt_sha256: _good() for c in cs})
    runner(tmp_path, client).run("w", cs, C.parse_generation)
    assert len(client.calls) == 4
    recs = _records(tmp_path)
    client2 = F.ScriptedAnthropic({})                    # would raise on any call
    res = runner(tmp_path, client2, resume=recs).run("w", cs, C.parse_generation)
    assert client2.calls == [] and res.n_reused == 4 and len(res.answers) == 4
    # a changed prompt is sent again
    changed = [C.EntropyCall(**{**cs[0].__dict__, "user": cs[0].user + " Also."})]
    client3 = F.ScriptedAnthropic({changed[0].prompt_sha256: _good()})
    res3 = runner(tmp_path, client3, resume=recs).run("w", changed, C.parse_generation)
    assert len(client3.calls) == 1 and res3.n_reused == 0
    # a third run of the same prompt is not answered by runs 1 and 2
    third = _calls(1, runs=(3,))
    client4 = F.ScriptedAnthropic({third[0].prompt_sha256: _good()})
    assert runner(tmp_path, client4, resume=recs).run("w", third, C.parse_generation).n_reused == 0


def test_a_budget_stop_keeps_the_answer_that_crossed_the_cap(tmp_path):
    cs = _calls(3, runs=(1,))
    big = make_response(_good(), input_tokens=100_000, output_tokens=100_000)
    client = F.ScriptedAnthropic({c.prompt_sha256: big for c in cs})
    usage = GuardedUsage(budget_usd=0.01)
    r = runner(tmp_path, client, usage=usage, concurrency=1)
    with pytest.raises(BudgetExceededError):
        r.run("w", cs, C.parse_generation)
    recs = _records(tmp_path)
    assert len(recs) == 1 and recs[0]["ok"] and recs[0]["usage_raw"]["output_tokens"] == 100_000
    assert len(client.calls) == 1


def test_the_batches_transport_records_charges_half_and_keeps_state(tmp_path):
    cs = _calls(2, runs=(1, 2))
    bc = F.FakeBatchClient(lambda params: _good())
    usage = GuardedUsage(budget_usd=5.0)
    r = runner(tmp_path, None, usage=usage)
    r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=lambda s: _nothing(), poll_seconds=0)
    res = r.run("a_h55_s1", cs, C.parse_generation)
    assert res.n_ok == 4 and len(bc.batches.created) == 1
    recs = _records(tmp_path)
    assert all(x["transport"] == "batches" and x["batch_request_id"] == "msgbatch_001" for x in recs)
    assert set(usage.per_model) == {C.HAIKU + BATCH_SUFFIX}
    t = usage.per_model[C.HAIKU + BATCH_SUFFIX]
    assert t.cost_usd == pytest.approx(0.5 * cost_for_usage(C.HAIKU, t.prompt_tokens, t.completion_tokens))
    state = json.loads((tmp_path / "batches.json").read_text())
    assert state["waves"]["a_h55_s1"][0]["status"] == "collected"
    assert state["waves"]["a_h55_s1"][0]["custom_ids"] == [c.custom_id for c in cs]
    for q in bc.batches.created[0]["requests"]:
        assert "temperature" not in q["params"] and q["params"]["max_tokens"] == C.MAX_TOKENS


async def _nothing():
    return None


def test_a_killed_batch_run_is_collected_on_resume(tmp_path):
    cs = _calls(1, runs=(1, 2))
    bc = F.FakeBatchClient(lambda params: _good())
    state = tmp_path / "batches.json"
    r = runner(tmp_path, None)
    t = BatchTransport(r, bc, state, sleep=lambda s: _nothing(), poll_seconds=0)
    # submit only: simulate a process killed after the create
    batch = bc.batches.create(requests=[t._request(c) for c in cs])
    t.save_state({"batch_id": "r_llm_entropy", "waves": {"w": [{"id": batch.id, "custom_ids": [c.custom_id for c in cs],
                                                               "status": "submitted", "submitted_at": None}]}})
    r2 = runner(tmp_path, None)
    r2.transport = BatchTransport(r2, bc, state, sleep=lambda s: _nothing(), poll_seconds=0)
    res = r2.run("w", cs, C.parse_generation)
    assert res.n_ok == 2 and len(bc.batches.created) == 1          # collected, nothing submitted again


def test_parse_rate_counts_units_once():
    recs = [{"family": "a", "prompt_id": "a:x:y", "run": 1, "stage": 1, "model": "m", "prompt_sha256": "p",
             "user_sha256": "u", "ok": False, "failure": "stop_reason max_tokens"},
            {"family": "a", "prompt_id": "a:x:y", "run": 1, "stage": 1, "model": "m", "prompt_sha256": "p",
             "user_sha256": "u", "ok": True},
            {"family": "a", "prompt_id": "a:x:z", "run": 1, "stage": 1, "model": "m", "prompt_sha256": "q",
             "user_sha256": "v", "ok": False, "parse_error": "no JSON object"}]
    pr = C.parse_rate(recs)
    assert pr["n_units"] == 2 and pr["n_ok"] == 1 and pr["rate"] == 0.5 and pr["n_records"] == 3
    assert pr["failures"] == {"no JSON object": 1, "stop_reason max_tokens": 1}


def test_b_records_are_redacted_and_name_labels_dropped(tmp_path):
    from assistant_axis.gapgen.generators.llm_entropy.seeds import PersonSeed, name_in_label, redact
    seed = PersonSeed(seed_id="b:r0001", kind="real", qid="Q990000101", name="Quillon Varnaby",
                      description="invented tram conductor of Zellwick")
    user = P.render_b(seed.as_prompt_seed())
    c = C.EntropyCall(family="b", prompt_id=seed.seed_id, run=1, model=C.HAIKU, system=SYSTEM["text"], user=user,
                      record_user=C.b_record_user(user, seed.seed_id), redactor=lambda t: redact(t, seed),
                      name_label=lambda lab: name_in_label(lab, seed))
    reply = json.dumps({"approach": "Quillon Varnaby, the invented tram conductor of Zellwick, was punctual.",
                        "items": [{"label": "varnaby-like", "gloss": "This means acting as Varnaby did.",
                                   "antonym": None, "kind": "trait"},
                                  {"label": "zztimekeeping", "gloss": "This means keeping time as Quillon did.",
                                   "antonym": "quillon-careless", "kind": "trait"}]})
    client = F.ScriptedAnthropic({c.prompt_sha256: reply})
    runner(tmp_path, client).run("b", [c], C.parse_generation)
    body = (tmp_path / "responses.jsonl").read_text()
    for s in ("Quillon", "Varnaby", "Zellwick", "Q990000101", "invented tram conductor"):
        assert s.lower() not in body.lower(), s
    rec = json.loads(body)
    assert rec["user"].startswith("Person: <b:r0001>.\nThis person may be little known")
    assert rec["n_dropped_name_label"] == 1 and [i["label"] for i in rec["items"]] == ["zztimekeeping"]
    assert rec["items"][0]["gloss"] == "This means keeping time as this person did."
    assert rec["custom_id"].startswith("b-r0001-r1-s1-h55-")


def test_a_b_records_error_and_refusal_explanation_are_redacted_and_a_call_repr_shows_no_prompt(tmp_path):
    from assistant_axis.gapgen.generators.llm_entropy.seeds import PersonSeed, redact
    seed = PersonSeed(seed_id="b:r0009", kind="real", qid="Q990000104", name="Mirelda Okonkwazi",
                      description="invented botanist of Pellbridge")
    user = P.render_b(seed.as_prompt_seed())
    c = C.EntropyCall(family="b", prompt_id=seed.seed_id, run=1, model=C.SONNET, system=SYSTEM["text"], user=user,
                      record_user=C.b_record_user(user, seed.seed_id), redactor=lambda t: redact(t, seed))
    assert "Okonkwazi" not in repr(c) and "Pellbridge" not in repr(c)
    refusal = make_response("", output_tokens=0, stop_reason="refusal")
    refusal.stop_details = {"type": "refusal", "category": "x", "explanation": "about Mirelda Okonkwazi"}
    client = F.ScriptedAnthropic({c.prompt_sha256: refusal})
    runner(tmp_path, client).run("b", [c], C.parse_generation)
    body = (tmp_path / "responses.jsonl").read_text()
    assert "Okonkwazi" not in body and "Mirelda" not in body and "this person" in body


def _b_call(seed, *, redactor, model=C.HAIKU):
    from assistant_axis.gapgen.generators.llm_entropy.seeds import leaks
    user = P.render_b(seed.as_prompt_seed())
    return C.EntropyCall(family="b", prompt_id=seed.seed_id, run=1, model=model, system=SYSTEM["text"], user=user,
                         record_user=C.b_record_user(user, seed.seed_id), redactor=redactor,
                         leak_check=lambda blob: leaks(blob, seed))


def test_the_redaction_guard_turns_away_a_record_that_still_names_its_seed(tmp_path):
    """Blocker 1 (b): whatever a redactor misses, the serialised record is checked before it is written."""
    from assistant_axis.gapgen.generators.llm_entropy.seeds import PersonSeed
    seed = PersonSeed(seed_id="b:r0005", kind="real", qid="Q990000103", name="Bexley Ravensquill",
                      description="invented radio announcer")
    c = _b_call(seed, redactor=lambda t: t)                     # a redactor that misses everything
    reply = F.reply_items(["zzcalm"], gloss_fmt="This means Ravensquillian calm.")
    client = F.ScriptedAnthropic({c.prompt_sha256: reply})
    res = runner(tmp_path, client).run("b", [c], C.parse_generation)
    body = (tmp_path / "responses.jsonl").read_text()
    assert "Ravensquill" not in body and "ravensquill" not in body.lower()
    recs = [json.loads(x) for x in body.splitlines()]
    assert all(r["failure"] == "redaction guard" and r["text"] is None and r["items"] is None and not r["ok"]
               for r in recs)
    assert res.n_ok == 0 and c.cache_key in res.failures and recs[0]["guard"] == ["name"]


def test_an_api_error_quoting_the_prompt_is_redacted_in_the_record_and_the_log(tmp_path, caplog):
    """Should-fix 2: the failure is built from the redacted error, and the platform's log lines are redacted while
    a (b) wave runs."""
    import logging

    from assistant_axis.gapgen.generators.llm_entropy.seeds import PersonSeed, redact
    seed = PersonSeed(seed_id="b:r0006", kind="real", qid="Q990000104", name="Mirelda Okonkwazi",
                      description="invented botanist of Pellbridge")
    c = _b_call(seed, redactor=lambda t: redact(t, seed))

    def boom(kw):
        return RuntimeError(f"400 bad request for: {kw['messages'][0]['content'][:60]}")
    client = F.ScriptedAnthropic({}, default=boom)
    with caplog.at_level(logging.INFO):
        runner(tmp_path, client).run("b", [c], C.parse_generation)
    body = (tmp_path / "responses.jsonl").read_text()
    log = "\n".join(r.getMessage() for r in caplog.records)
    for s in ("Mirelda", "Okonkwazi", "Pellbridge"):
        assert s not in body and s not in log, s
    recs = [json.loads(x) for x in body.splitlines()]
    assert recs and all(r["failure"].startswith("no response (RuntimeError: 400 bad request for: Person: this person")
                        for r in recs)
    assert "API call to" in log                                # the line is there, redacted


def test_the_batch_path_keeps_a_refusals_category(tmp_path):
    """Minor 7: ``batches.BatchTransport`` hands over ``stop_details``, as the live path does."""
    c = _calls(1, runs=(1,), model=C.SONNET)[0]

    def refuse(params):
        r = make_response("", output_tokens=0, stop_reason="refusal")
        r.stop_details = {"type": "refusal", "category": "reasoning_extraction"}
        return r
    bc = F.FakeBatchClient(refuse)
    r = runner(tmp_path, None)
    r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=lambda s: _nothing(), poll_seconds=0)
    r.run("w", [c], C.parse_generation)
    recs = _records(tmp_path)
    assert recs and all(x["stop_details"]["category"] == "reasoning_extraction" for x in recs)
    assert recs[0]["failure"] == "stop_reason refusal (reasoning_extraction)"


def test_the_guard_reads_values_not_keys_or_the_template(tmp_path):
    """A person named like a JSON key and a template word is redacted in the values, and the record kept."""
    from assistant_axis.gapgen.generators.llm_entropy.seeds import PersonSeed, redact
    seed = PersonSeed(seed_id="b:r0007", kind="real", qid="Q990000105", name="Gloss Kindvocab",
                      description="invented typist")
    c = _b_call(seed, redactor=lambda t: redact(t, seed))
    reply = F.reply_items(["zzsteady"], gloss_fmt="This means steady like Kindvocab.")
    client = F.ScriptedAnthropic({c.prompt_sha256: reply})
    res = runner(tmp_path, client).run("b", [c], C.parse_generation)
    rec = json.loads((tmp_path / "responses.jsonl").read_text())
    assert res.n_ok == 1 and rec["ok"] and rec["items"][0]["gloss"] == "This means steady like this person."
    assert "guard" not in rec
