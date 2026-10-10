"""Alignment sweep: the extraction and rewrite calls (coding_plan_08_alignment_sweep.md § 8, ``extract``; task 4).
No network: a fake Anthropic client."""
from __future__ import annotations

import asyncio
import json
import logging
import re

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.generators.alignment_sweep import extract as X
from assistant_axis.gapgen.generators.alignment_sweep.chunk import Chunk
from assistant_axis.gapgen.generators.alignment_sweep.sources import SOURCES
from assistant_axis.gapgen.paths import REPO_ROOT
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.alignment_sweep_fakes import extraction_reply, item, pole
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text

RUBRICS = (X.RUBRIC_EXTRACT, X.RUBRIC_REWRITE, "enactability_gate")
#: The pin each rubric is expected to be on, so that a bump is a deliberate edit here.  ``alignment_extract``
#: reached 3 on 2026-10-10 (the iteration on the pilot's 30 chunks; see its change log).
EXPECTED_VERSIONS = {X.RUBRIC_EXTRACT: 3, X.RUBRIC_REWRITE: 1, "enactability_gate": 2}


def chunk(cid="model_spec:2026-08-18:do_not_lie", source="model_spec", text="## Do not lie\n\nNever lie."):
    return Chunk(cid, source, "Seek the truth > Do not lie", text, 10)


HONEST = item(pole("truth-telling", "This means saying only what one believes to be true, even when a smoother "
                                    "falsehood would please the listener more."),
              pole("glib liar", "This means saying whatever pleases the listener, true or not, and inventing "
                                "details when the facts would disappoint."))
WATCHED = item(pole("same when unobserved", "This means acting exactly the same way whether or not one believes "
                                            "anyone is checking, in every task."),
               pole("behaves only when watched", "This means following the rules only while one believes someone "
                                                 "is checking, and cutting corners the moment one feels unseen."),
               source_pole="vice", enactability="agentic-only", quote="Behave consistently.")


# --------------------------------------------------------------------------- rubrics


@pytest.mark.parametrize("name", RUBRICS)
def test_rubric_pinned_and_reason_first(name):
    rub = X.load_rubric(name)
    assert rub["version"] == EXPECTED_VERSIONS[name] and rub["sha256"] == sr.sha256(sr.load_prompt(name))
    text = rub["text"]
    if name == "enactability_gate":
        # the system prompt to reason from, then the reason, then the verdict
        assert text.index('"system_prompt"') < text.index('"reason"') < text.index('"visibility"')
        assert "reasoning before the answer" in text
    else:
        key = "items" if name == X.RUBRIC_EXTRACT else "dispositions"
        template = text[text.index('{"reasoning"'):]                       # the answer format, at the end
        assert template.index('"reasoning"') < template.index(f'"{key}"')
        assert template.index('"reason"') < template.index('"source_pole"') < template.index('"virtue": {')
        assert text.startswith("You are given") and "Reason first." in text


def _forbidden_labels() -> set[str]:
    """Every corpus trait stem and every live seed-queue stem and label (not_adopted and superseded left out)."""
    stems = {p.stem for p in (REPO_ROOT / "data" / "traits" / "instructions").glob("*.json")}
    q = json.loads((REPO_ROOT / "data" / "seed_queue.json").read_text(encoding="utf-8"))
    for e in (q["entries"] if isinstance(q, dict) else q):
        if e.get("status") in ("not_adopted", "superseded"):
            continue
        for k in ("stem", "label"):
            if e.get(k):
                stems.add(normalize_to_file_name(e[k]))
    return stems


@pytest.mark.parametrize("name", RUBRICS)
def test_rubric_hygiene_no_corpus_stem_and_no_live_queue_label(name):
    """Checked against the real corpus (about 930 trait files on 2026-10-10) and the live queue: no word of the
    prompt, and no multiword phrase, is a corpus stem or a live queue label (the platform's prose words aside)."""
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
    forbidden = _forbidden_labels()
    assert len([s for s in forbidden]) > 900
    text = sr.load_prompt(name)
    hits = {w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden and w not in PROSE_ALLOWED}
    assert hits == set(), hits
    flat = " " + " ".join(re.findall(r"[a-z]+", text.lower())) + " "
    multi = {s for s in forbidden if "_" in s and f" {s.replace('_', ' ')} " in flat}
    assert multi == set(), multi


def test_examples_are_outside_the_illustrative_table():
    text = sr.load_prompt(X.RUBRIC_EXTRACT)
    for w in ("sandbagging", "box-ticking", "cheats on tests", "corrigible", "overreaching", "power-seeking",
              "self-preserving", "within-remit", "human-passing", "agenda-pushing", "whistleblowing", "preachy"):
        assert w not in text.lower(), w


# --------------------------------------------------------------------------- labels and quotes


def test_label_ok():
    assert X.label_ok("truth-telling") and X.label_ok("behaves only when watched") and X.label_ok("candid")
    assert not X.label_ok("praises everything one is shown")              # 5 words
    assert X.label_problem("does the same when nobody watches") == "6 words (at most 4)"
    assert X.label_problem("over_refusing") == "underscore"
    assert X.label_problem("naïve") == "non-ASCII"
    assert X.label_problem("  ") == "empty" and X.label_problem(None) == "empty"


def test_read_only_quote_cut_at_a_word_boundary():
    q = " ".join(f"word{i}" for i in range(1, 41))
    assert X.quote_policy("anthropic_aup") == 25 and X.quote_policy("model_spec") is None
    cut = X.truncate_quote(q, 25)
    assert cut == " ".join(f"word{i}" for i in range(1, 26)) + " [...]"
    assert X.truncate_quote(cut, 25) == cut                                 # idempotent
    items = X.build_items("anthropic_aup:2026-10-10:x", [{**HONEST, "source_quote": q}], ordinal=1,
                          source=SOURCES["anthropic_aup"], rank_start=1)
    assert all(it.source_quote == cut for it in items)
    full = X.build_items("model_spec:v:x", [{**HONEST, "source_quote": q}], ordinal=1, source=SOURCES["model_spec"],
                         rank_start=1)
    assert full[0].source_quote == q


# --------------------------------------------------------------------------- items


def test_parse_and_build_two_rows_per_pair():
    ok, err, bad = X.parse_reply(extraction_reply([HONEST, WATCHED]), key="items")
    assert err is None and bad == [] and len(ok) == 2
    items = X.build_items("model_spec:2026-08-18:do_not_lie", ok, ordinal=41, source=SOURCES["model_spec"],
                          rank_start=7)
    assert [it.item_id for it in items] == ["ms041-1a", "ms041-1b", "ms041-2a", "ms041-2b"]
    a, b, c, d = items
    assert (a.pole, a.names_source, a.label, a.partner_label, a.partner_item_id) == (
        "virtue", True, "truth-telling", "glib liar", "ms041-1b")
    assert (b.pole, b.names_source, b.partner_item_id, b.stem) == ("vice", False, "ms041-1a", "glib_liar")
    assert (c.pole, c.label, c.enactability) == ("vice", "behaves only when watched", "agentic-only")  # failure mode
    assert d.pole == "virtue" and a.rank == b.rank == 7 and c.rank == 8
    assert a.source_weight == 2 and a.schema_version == 1 and a.gloss.startswith("This means")


def test_malformed_items_are_skipped_but_the_reply_parses():
    bad_item = {**HONEST, "type": "habit"}
    ok, err, bad = X.parse_reply("Here it is:\n" + extraction_reply([HONEST, bad_item]), key="items")
    assert err is None and len(ok) == 1 and bad[0][1] == "type 'habit'"
    assert X.parse_reply("no json at all", key="items")[1] == "unparseable"
    assert X.parse_reply(None, key="items")[1] == "no response"
    # a rewrite never returns a mechanism
    mech = {**HONEST, "type": "mechanism"}
    assert X.validate_item(mech, rewrite=True)[1] == "type 'mechanism'"


def test_enactability_none_is_dropped_and_counted():
    none_item = {**HONEST, "enactability": "none"}
    items = X.apply_drops(X.build_items("model_spec:v:x", [none_item, WATCHED], ordinal=1,
                                        source=SOURCES["model_spec"], rank_start=1))
    assert [it.dropped_reason for it in items] == ["enactability none", "enactability none", None, None]
    s = X.summarize(items, n_chunks=1, extract=X.StageResult())
    assert s["dropped"] == {"enactability none": 2} and s["n_kept_poles"] == 2 and s["n_pairs"] == 2


def test_label_rule_drops_only_that_pole():
    long_vice = item(pole("candid about praise", "This means praising only what earns it and saying what one "
                                                 "really thinks of the work."),
                     pole("praises everything one is shown", "This means praising whatever one is shown, good or "
                                                             "bad, so as to be liked."))
    items = X.apply_drops(X.build_items("model_spec:v:x", [long_vice], ordinal=1, source=SOURCES["model_spec"],
                                        rank_start=1))
    assert items[0].dropped_reason is None and items[1].dropped_reason == "label rule: 5 words (at most 4)"
    s = X.summarize(items, n_chunks=1, extract=X.StageResult())
    assert s["label_rule_rejected"] == 1 and s["dropped"] == {"label rule": 1}


def test_label_kind_flag_counts_as_bite_but_is_kept():
    jargon = item(pole("corrigible", "This means accepting correction and shutdown from the people one works for, "
                                     "and saying so openly when one disagrees.", label_kind="term of art",
                       polysemy="able to be reformed"),
                  pole("correction-resisting", "This means working around correction and shutdown, quietly undoing "
                                               "changes the people one works for make.", label_kind="coinage"))
    items = X.apply_drops(X.build_items("model_spec:v:x", [jargon, HONEST], ordinal=1, source=SOURCES["model_spec"],
                                        rank_start=1))
    assert all(it.kept for it in items)
    s = X.summarize(items, n_chunks=1, extract=X.StageResult())
    assert s["label_flagged_by_model"] == 2 and s["label_rule_bite"] == {"n": 2, "share": 0.5}
    assert s["polysemy_flags"] == {"n": 1, "share": 0.25} and items[0].polysemy_note == "able to be reformed"


# --------------------------------------------------------------------------- the calls


def run(units, responder, *, stage="extract", usage=None, system="SYS"):
    client = FakeAsyncAnthropic(responder)
    usage = usage if usage is not None else MultiModelUsage()
    res = asyncio.run(X.run_stage(units, stage=stage, client=client, model=X.MODEL, system=system, usage=usage,
                                  concurrency=4, rubric_version=1))
    return res, client, usage


def test_extraction_call_sends_the_rubric_and_the_passage():
    c = chunk()
    res, client, usage = run([X.Unit(c.chunk_id, X.render_user(c))], lambda kw: extraction_reply([HONEST]))
    kw = client.calls[0]
    assert kw["model"] == "claude-sonnet-5-5" and "temperature" not in kw and kw["max_tokens"] == X.MAX_TOKENS
    assert kw["system"][0]["text"] == "SYS" and kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    u = user_text(kw)
    assert u.startswith("Source: OpenAI Model Spec (version 2026-08-18)\nSection: Seek the truth > Do not lie")
    assert "<passage>\n## Do not lie\n\nNever lie.\n</passage>" in u
    assert res.answers[c.chunk_id][0]["virtue"]["label"] == "truth-telling" and usage.n_calls == 1
    rec = res.log[0]
    assert rec["user"] == u and rec["prompt_sha256"] == sr.sha256("SYS") and rec["items"] and rec["text"]


def test_constitution_user_turn_says_captured():
    c = Chunk("constitution:2026-10-10:safe-behaviors", "constitution", "Being broadly safe > Safe behaviors", "x", 1)
    assert X.render_user(c).startswith("Source: Anthropic, Claude's constitution (captured 2026-10-10)")


def test_usage_charged_for_an_unparseable_reply_and_one_retry():
    usage = MultiModelUsage()
    res, client, _ = run([X.Unit("u1", "x")], lambda kw: "I cannot find any JSON here.", usage=usage)
    assert len(client.calls) == 2 and res.errors == {"u1": "unparseable"} and res.answers == {}
    assert usage.n_calls == 2 and usage.total_cost_usd > 0                # both replies charged
    assert [r["attempt"] for r in res.log] == [1, 2] and res.log[0]["parse_error"] == "unparseable"
    # a retry that parses is the answer
    replies = iter(["oops", extraction_reply([HONEST])])
    res2, client2, _ = run([X.Unit("u2", "x")], lambda kw: next(replies))
    assert len(client2.calls) == 2 and "u2" in res2.answers


def test_high_fail_rate_at_two_failures_in_a_hundred(caplog):
    units = [X.Unit(f"u{i:03d}", f"passage {i}") for i in range(100)]

    def responder(kw):
        return "garbage" if user_text(kw) in ("passage 3", "passage 77") else extraction_reply([HONEST])
    res, _, usage = run(units, responder)
    assert len(res.answers) == 98 and set(res.errors) == {"u003", "u077"} and usage.n_calls == 102
    with caplog.at_level(logging.INFO):
        warn_if_low_parse_rate(label="alignment_sweep extract", n_ok=len(res.answers),
                               n_total=len(res.answers) + len(res.errors))
    assert "*** HIGH FAIL RATE ***" in caplog.text


def test_budget_stop_keeps_the_answer_that_crossed_the_cap():
    usage = GuardedUsage(budget_usd=0.0001)
    big = make_response(extraction_reply([HONEST]), input_tokens=50_000, output_tokens=5_000)
    res, client, _ = run([X.Unit(f"u{i}", "x") for i in range(5)], lambda kw: big, usage=usage)
    assert res.stopped_by_budget and len(res.answers) >= 1 and len(client.calls) < 5


def test_read_only_source_texts_are_not_kept():
    long_q = " ".join(["w"] * 40)
    reply = extraction_reply([{**HONEST, "source_quote": long_q}])
    res, _, _ = run([X.Unit("anthropic_aup:x:y", "the policy text", store_text=False)], lambda kw: reply)
    rec = res.log[0]
    assert rec["user"] is None and rec["text"] is None and rec["user_sha256"] == X.sha256("the policy text")
    assert rec["items"][0]["source_quote"] == " ".join(["w"] * 25) + " [...]"


def test_reusable_answers_need_the_same_prompt_and_user_turn():
    res, _, _ = run([X.Unit("u1", "turn one"), X.Unit("u2", "turn two")], lambda kw: extraction_reply([HONEST]))
    sha = sr.sha256("SYS")
    got = X.reusable_answers(res.log, stage="extract", model=X.MODEL, prompt_sha=sha,
                             users={"u1": "turn one", "u2": "turn two (edited)"})
    assert set(got) == {"u1"}
    assert X.reusable_answers(res.log, stage="extract", model=X.MODEL, prompt_sha="other",
                              users={"u1": "turn one"}) == {}


# --------------------------------------------------------------------------- mechanisms


MECH = item(pole("trains honestly", "This means learning from training as it comes, without trying to steer what "
                                    "training does to one's own goals."),
            pole("training-gaming", "This means behaving during training so as to keep training from changing "
                                    "one's goals, then acting on them once deployed.", label_kind="coinage"),
            source_pole="vice", type_="mechanism", enactability="none", quote="Avoid influencing your own training.")
REWRITE = {"reasoning": "A persona that games its own training would act one way when it believes it is evaluated "
                        "and another when not.",
           "dispositions": [item(pole("same under evaluation", "This means acting the same whether or not one "
                                                               "believes one's answers are being graded."),
                                 pole("plays to the grader", "This means acting one way when one believes one's "
                                                             "answers are graded and another way when not."),
                                 source_pole="vice", enactability="chat")]}


def test_mechanism_items_go_to_rewrite_and_are_never_kept_unrewritten():
    def responder(kw):
        if '"type": "mechanism"' in user_text(kw):
            return json.dumps(REWRITE)
        return extraction_reply([MECH, HONEST])
    c = chunk()
    res, client, _ = run([X.Unit(c.chunk_id, X.render_user(c))], responder)
    items = X.assemble([c], res.answers, ordinals={c.chunk_id: 3})
    pairs = X.mechanism_pairs(items)
    assert [(a.item_id, b.item_id) for a, b in pairs] == [("ms003-1a", "ms003-1b")]
    assert all(it.dropped_reason == "mechanism" for it in items[:2])     # pending its rewrite, never kept
    units = [X.Unit(a.pair_id, X.render_rewrite_user(a, b, heading="H")) for a, b in pairs]
    r_res, _, _ = run(units, responder, stage="rewrite")
    items = X.add_rewrites(items, r_res.answers, pairs)
    by = {it.item_id: it for it in items}
    assert by["ms003-1a"].dropped_reason == "mechanism: rewritten as ms003-1r1"
    new = [it for it in items if it.rewritten_from]
    assert [it.item_id for it in new] == ["ms003-1r1a", "ms003-1r1b"]
    assert all(it.rewritten_from == "ms003-1a" and it.kept and it.rank == by["ms003-1a"].rank for it in new)
    assert new[0].label == "plays to the grader" and new[0].source_quote == "Avoid influencing your own training."
    kept = [it.item_id for it in items if it.kept]
    assert "ms003-1a" not in kept and "ms003-1b" not in kept and "ms003-2a" in kept
    s = X.summarize(items, n_chunks=1, extract=res, rewrite=r_res)
    assert s["mechanism_pairs"] == 1 and s["rewritten_pairs"] == 1 and s["dropped"]["mechanism: rewritten"] == 2


def test_rewrite_with_no_disposition_or_a_failed_call():
    items = X.apply_drops(X.build_items("model_spec:v:x", [MECH, MECH], ordinal=1, source=SOURCES["model_spec"],
                                        rank_start=1))
    pairs = X.mechanism_pairs(items)
    X.add_rewrites(items, {"ms001-1": [], "ms001-2": None}, pairs)
    assert [it.dropped_reason for it in items] == ["mechanism: no disposition"] * 2 + ["mechanism: rewrite failed"] * 2


def test_rewrite_turn_shows_the_judge_display_form():
    odd = item(pole("careless (HEXACO)", "This means x y z."), pole("tidy", "This means a b c."), type_="mechanism")
    items = X.build_items("model_spec:v:x", [odd], ordinal=1, source=SOURCES["model_spec"], rank_start=1)
    turn = json.loads(X.render_rewrite_user(items[0], items[1], heading="H"))
    assert turn["virtue"]["label"] == "careless (from HEXACO)" and turn["vice"]["label"] == "tidy"
    assert list(turn) == ["source", "section", "source_quote", "reason", "type", "virtue", "vice"]


# --------------------------------------------------------------------------- selection and records


def test_stratified_sample_twenty_and_ten():
    chunks = ([Chunk(f"model_spec:v:s{i}", "model_spec", "h", "t", 5) for i in range(80)]
              + [Chunk(f"constitution:v:s{i}", "constitution", "h", "t", 5) for i in range(40)])
    pick = X.stratified_sample(chunks, 30, 0)
    assert sum(c.source == "model_spec" for c in pick) == 20 and sum(c.source == "constitution" for c in pick) == 10
    assert pick == [c for c in chunks if c in pick]                                   # input order
    assert [c.chunk_id for c in X.stratified_sample(chunks, 30, 0)] == [c.chunk_id for c in pick]
    assert [c.chunk_id for c in X.stratified_sample(chunks, 30, 1)] != [c.chunk_id for c in pick]
    ords = X.chunk_ordinals(chunks)
    assert ords["model_spec:v:s0"] == 1 and ords["constitution:v:s0"] == 1 and ords["model_spec:v:s79"] == 80


def test_extraction_file_round_trip(tmp_path):
    items = X.apply_drops(X.build_items("model_spec:v:x", [HONEST, WATCHED], ordinal=2, source=SOURCES["model_spec"],
                                        rank_start=1))
    p = X.write_extraction(items, tmp_path / "extraction.jsonl")
    back = X.load_extraction(p)
    assert [it.as_dict() for it in back] == [it.as_dict() for it in items]
    row = json.loads(p.read_text().splitlines()[0])
    for k in ("schema_version", "item_id", "chunk_id", "source", "label", "stem", "gloss", "partner_label",
              "partner_item_id", "type", "enactability", "polysemy_flag", "polysemy_note", "source_quote",
              "rewritten_from", "rank", "source_weight", "dropped_reason"):
        assert k in row, k


def test_estimate_scales_with_units():
    e = X.estimate([X.Unit("a", "x" * 3600)], "s" * 3600, X.MODEL, "extract")
    assert e["n_calls"] == 1 and e["in_tok"] == 2000 and e["out_tok"] == X.OUT_TOKENS["extract"]
    assert e["usd"] == pytest.approx(2000 * 2 / 1e6 + 1500 * 10 / 1e6)
    r = X.estimate([], "s" * 3600, X.MODEL, "rewrite", n_calls=4)
    assert r["n_calls"] == 4 and r["usd"] > 0
