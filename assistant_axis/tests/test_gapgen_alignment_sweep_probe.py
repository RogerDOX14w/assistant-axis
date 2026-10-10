"""Alignment sweep: the Qwen label probe (coding_plan_08_alignment_sweep.md § 8, ``probe``; task 9).  A fake
OpenRouter client and a hash embedder, no network."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen.embed import HashEmbedder
from assistant_axis.gapgen.generators.alignment_sweep import probe as P
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.alignment_sweep_fakes import FakeAsyncOpenAI, openrouter_response

LABELS = [P.ProbeInput("candid about work", "This means telling people what one thinks of their work, flaws included."),
          P.ProbeInput("plays to the grader", "This means acting one way when graded and another way when not.")]


def run(responder, inputs=LABELS, **kw):
    client = FakeAsyncOpenAI(responder)
    usage = MultiModelUsage()
    res = asyncio.run(P.run_probe(inputs, client=client, usage=usage, embedder=HashEmbedder(dim=64), **kw))
    return res, client, usage


def test_only_deepinfra_in_the_united_states():
    assert P.ALLOWED_PROVIDERS == {"deepinfra": "United States"} and P.MODEL == "qwen/qwen3-32b"


def test_request_pins_deepinfra_without_fallbacks_and_switches_thinking_off():
    res, client, usage = run(lambda kw: openrouter_response(json.dumps(
        {"definition": "Saying frankly what one thinks of someone's work.", "known": True})))
    kw = client.calls[0]
    assert kw["model"] == "qwen/qwen3-32b"
    assert kw["extra_body"]["provider"] == {"order": ["deepinfra"], "allow_fallbacks": False}
    assert kw["extra_body"]["reasoning"] == {"enabled": False}
    assert kw["messages"][-1]["content"].endswith(" /no_think") and "'candid about work'" in kw["messages"][-1]["content"]
    assert usage.per_model["qwen/qwen3-32b"].n_calls == 2               # the embedder charges its own line
    row = res.rows["candid about work"]
    assert row.provider == "DeepInfra" and row.known_claimed and row.discarded is None


def test_a_response_from_another_host_is_discarded_and_counted():
    def responder(kw):
        host = "SiliconFlow" if "grader" in kw["messages"][-1]["content"] else "DeepInfra"
        return openrouter_response(json.dumps({"definition": "d", "known": True}), provider=host)
    res, _, usage = run(responder)
    assert res.n_discarded == 1 and res.rows["plays to the grader"].discarded == "host SiliconFlow not allowed"
    assert res.rows["plays to the grader"].label_known is None
    assert usage.per_model["qwen/qwen3-32b"].n_calls == 2              # the discarded one still charged


def test_unknown_and_known_by_meaning():
    def responder(kw):
        if "grader" in kw["messages"][-1]["content"]:
            return openrouter_response(json.dumps({"definition": None, "known": False}))
        return openrouter_response(json.dumps({"definition": "Telling people what one thinks of their work, flaws "
                                                             "included.", "known": True}))
    res, _, _ = run(responder)
    a, b = res.rows["candid about work"], res.rows["plays to the grader"]
    assert a.known_claimed and a.cos_to_gloss > P.MIN_COS_TO_GLOSS and a.label_known is True
    assert b.known_claimed is False and b.label_known is False
    # a definition far from the intended gloss is a label the model knows in another sense
    res2, _, _ = run(lambda kw: openrouter_response(json.dumps({"definition": "A kind of cheese.", "known": True})),
                     inputs=[LABELS[0]])
    assert res2.rows["candid about work"].label_known is False


def test_thinking_is_stripped_and_unparseable_is_an_error():
    res, _, _ = run(lambda kw: openrouter_response("<think>\n\n</think>\n" + json.dumps(
        {"definition": "Frank about work.", "known": True})), inputs=[LABELS[0]])
    assert res.rows["candid about work"].definition == "Frank about work."
    res2, _, _ = run(lambda kw: openrouter_response("I don't know"), inputs=[LABELS[0]])
    assert res2.rows["candid about work"].error == "unparseable" and res2.n_errors == 1


def test_no_key_skips_and_says_so(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    status = P.key_status(env_path=None)
    assert status == "skipped: no OPENROUTER_API_KEY loads"


def test_probe_record_round_trip(tmp_path):
    res, _, _ = run(lambda kw: openrouter_response(json.dumps({"definition": "d", "known": True})))
    p = P.write_probe(res, tmp_path / "probe.json", status="ran", inputs=[])
    env = json.loads(p.read_text())
    d = env["result"]
    assert d["status"] == "ran" and d["host"] == {"deepinfra": "United States"} and len(d["rows"]) == 2
    assert d["prompt_version"] == P.PROMPT_VERSION and d["prompt_sha256"]
    back = P.load_label_known(p)
    assert set(back) == {"candid about work", "plays to the grader"}
    skipped = P.write_probe(None, tmp_path / "skip.json", status="skipped: no OPENROUTER_API_KEY loads", inputs=[])
    assert P.load_label_known(skipped) == {} and json.loads(skipped.read_text())["result"]["status"].startswith("skip")


def test_refloor_rederives_label_known_from_the_stored_cosines(tmp_path):
    rows = [P.ProbeRow("a", "d", True, 0.45, False, "DeepInfra"), P.ProbeRow("b", "d", True, 0.25, False, "DeepInfra"),
            P.ProbeRow("c", None, False, None, False, "DeepInfra"), P.ProbeRow("d", discarded="host X not allowed")]
    res = P.ProbeResult(rows={r.label: r for r in rows}, n_calls=4)
    p = P.write_probe(res, tmp_path / "probe.json", status="ran", extra={"min_cos_to_gloss": 0.5})
    assert P.refloor(p, 0.30) == {"known": 1, "another_sense": 1, "unknown": 1, "no_data": 1}
    d = json.loads(p.read_text())["result"]
    assert d["min_cos_to_gloss"] == 0.30 and d["refloored_from"] == 0.5
    assert P.load_label_known(p) == {"a": True, "b": False, "c": False, "d": None}
    assert P.MIN_COS_TO_GLOSS == 0.30
