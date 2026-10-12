"""The split filter's runner (coding_plan_split.md section 8, tests 3, 4, 6, 7 and 9).  No API call:
a fake client replays the answers recorded on 2026-09-29 (``split_replay``)."""
import json
import logging
from collections import Counter

import pytest

from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.filter import FilterItem
from assistant_axis.gapgen.split_runner import SplitRunner
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage, cost_for_usage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.split_replay import (
    HAIKU, SONNET55, load_jsonl, make_responder, parse_user, step_of_system, synthetic, test_items,
)

HINT = "SECRET-HINT a meaning the model must not see before wave 3"


def runner(client, **kw):
    # the recorded answers are Haiku 4.5's: these tests name it (the default is Haiku 5.5 from 2026-10-08,
    # with three verdict readings; TestReadings covers that)
    kw.setdefault("model", HAIKU)
    kw.setdefault("wordnet", False)
    kw.setdefault("zipf_fn", lambda w: 4.0)   # no floor, no probe band, unless a test says so
    kw.setdefault("retry_delays", ())
    kw.setdefault("second_opinion", False)
    return SplitRunner(client=client, batch_id="t", **kw)


def expected_by_label():
    return {e["word"]: e for e in load_jsonl("expected_outcomes.jsonl")}


# ---------------------------------------------------------------------------
# the whole path on the recorded answers
# ---------------------------------------------------------------------------

class TestReplay:
    def test_recorded_answers_give_the_expected_outcomes(self):
        client = FakeAsyncAnthropic(make_responder())
        r = runner(client)
        res = r.run(test_items())
        exp = expected_by_label()
        assert all(x.stage == "classified" for x in res)
        got = {x.label: x.filter for x in res}
        for label, e in exp.items():
            f = got[label]
            assert f["outcome"] == e["outcome"], label
            assert f["judged_sense"] == e["accepted"], label
            assert f["notes"] == e["notes"], label
        assert sorted(o["outcome"] for o in got.values()).count("trait") == 74
        assert sum("two_trait_senses" in f["notes"] for f in got.values()) == 7

    def test_blocks_map_to_the_frozen_vocabulary(self):
        from assistant_axis.gapgen.normalize import HOLDING, REGION_VOCAB, TAG_VOCAB, VERDICTS
        client = FakeAsyncAnthropic(make_responder())
        res = runner(client).run(test_items())
        for x in res:
            f = x.filter
            assert f["pipeline"] == "split" and f["rubric_version"] == 5
            assert f["verdict"] in VERDICTS and set(f["tags"]) <= set(TAG_VOCAB)
            assert x.holding in HOLDING
            assert f["region"] is None or f["region"] in REGION_VOCAB
            # the latest pin of each prompt (test_gapgen_split_rubrics checks what each version names)
            assert f["step_versions"] == {n: v for n, (v, _) in sr.current_versions().items()}
            assert set(f["step_versions"]) == set(sr.NAMES)
            assert f["confidence"] is None and f["tag_disagreement"] is False
            if f["outcome"] == "trait":
                assert x.gloss and f["gloss_model"] == HAIKU and f["region"]
            else:
                assert x.gloss is None and f["gloss_model"] is None
            if f["outcome"] == "states":
                assert f["verdict"] == "tagged" and f["tags"] == ["state"] and x.holding == "states"
            if f["outcome"] == "turned_away":
                assert f["verdict"] == "reject" and x.holding is None


# ---------------------------------------------------------------------------
# 3. one item per call; 4. blindness
# ---------------------------------------------------------------------------

class TestPayloads:
    def _run(self):
        intended = {e["word"]: HINT for e in load_jsonl("expected_outcomes.jsonl")[:20]}
        client = FakeAsyncAnthropic(make_responder())
        r = runner(client, second_opinion=True, second_opinion_frac=0.2,
                   zipf_fn=lambda w: 2.0)  # every word in the probe band
        r.run(test_items(intended=intended))
        return client, r

    def test_every_call_carries_one_item(self):
        client, _ = self._run()
        steps = set()
        for kw in client.calls:
            step = step_of_system(system_text(kw))
            steps.add(step)
            item = parse_user(step, user_text(kw))  # asserts one line for probe and comparison
            assert isinstance(item, dict) and item.get("id") == 1
            assert len(kw["messages"]) == 1
        assert steps == set(split.STEPS)  # every wave was exercised

    def test_steps_1_to_3_never_see_the_intended_sense(self):
        client, _ = self._run()
        n_cmp = 0
        for kw in client.calls:
            step = step_of_system(system_text(kw))
            if step == "comparison":
                n_cmp += 1
                assert HINT in user_text(kw)
            else:
                assert HINT not in user_text(kw), step
                assert "intended" not in user_text(kw) and "gloss_hint" not in user_text(kw)
        assert n_cmp > 0

    def test_comparison_goes_to_the_compare_model_one_pair_per_call(self):
        client, r = self._run()
        cmp = [kw for kw in client.calls if step_of_system(system_text(kw)) == "comparison"]
        assert {kw["model"] for kw in cmp} == {SONNET55}
        assert all(len(user_text(kw).splitlines()) == 2 for kw in cmp)


# ---------------------------------------------------------------------------
# the comparison's effect on the join
# ---------------------------------------------------------------------------

class TestComparison:
    def _one(self, relations):
        """One synthetic word with two trait readings; the comparison answers ``relations`` in order."""
        seq = list(relations)

        def override(step, item, kw):
            if step == "sense":
                return json.dumps({"results": [{"id": 1, "label": item["label"], "note": "n.", "first_thought": "f",
                                                "first_thought_said_of": "people", "usable": True,
                                                "readings": [{"reading": "reading one", "rank": "primary"},
                                                             {"reading": "reading two", "rank": "primary"}]}]})
            if step == "comparison":
                rel = seq[0] if item["plain_reading"] == "reading one" else seq[1]
                return synthetic("comparison", item, relation=rel)
            if step == "same_sense":
                return json.dumps({"results": [{"id": 1, "reason": "r.", "relation": "different"}]})
            return None

        client = FakeAsyncAnthropic(make_responder(override=override))
        res = runner(client).run([FilterItem(key="zorp#1", label="zorp", intended_sense="the intended meaning")])
        return res[0].filter

    def test_same_as_accepted_adds_nothing(self):
        f = self._one(["same", "different"])
        assert f["judged_sense"] == "reading one" and "overshadowed" not in f["notes"]
        assert f["comparison"]["effect"] == "same" and len(f["comparison"]["per_reading"]) == 2

    def test_same_as_another_trait_reading_switches(self):
        f = self._one(["different", "same"])
        assert f["judged_sense"] == "reading two" and f["outcome"] == "trait" and f["rule"] == 4
        assert f["comparison"]["effect"] == "switched" and "overshadowed" not in f["notes"]

    def test_related_and_different(self):
        assert "reading_related" in self._one(["related", "different"])["notes"]
        f = self._one(["different", "different"])
        assert "overshadowed" in f["notes"] and f["outcome"] == "trait" and f["polysemy"]


# ---------------------------------------------------------------------------
# 6. stops and resume
# ---------------------------------------------------------------------------

class TestStopsAndResume:
    def test_budget_stop_keeps_every_answer_and_resume_sends_only_what_is_missing(self):
        items = test_items(12)
        full_client = FakeAsyncAnthropic(make_responder())
        full = runner(full_client, concurrency=1)
        full_res = {x.key: x.filter["outcome"] for x in full.run(items)}
        n_full = len(full_client.calls)

        client = FakeAsyncAnthropic(make_responder(tokens=(1000, 200)))
        per_call = cost_for_usage(HAIKU, 1000, 200)
        usage = GuardedUsage(budget_usd=per_call * 20.5)
        r = runner(client, usage=usage, concurrency=1)
        with pytest.raises(BudgetExceededError):
            r.run(items)
        assert len(client.calls) == 21                     # the call that crossed the cap is kept
        assert len(r.responses) == 21 and usage.n_calls == 21
        assert all(rec["text"] for rec in r.responses)
        assert {x.stage for x in r.results.values()} == {"pending"}
        assert any("split_partial" in x.meta for x in r.results.values())

        client2 = FakeAsyncAnthropic(make_responder())
        r2 = runner(client2, concurrency=1, resume_records=list(r.responses))
        res2 = {x.key: x.filter["outcome"] for x in r2.run(items)}
        assert res2 == full_res
        assert len(client2.calls) == n_full - 21           # nothing asked twice
        sent = {(step_of_system(system_text(kw)), user_text(kw)) for kw in client2.calls}
        old = {(rec["step"], rec["user"]) for rec in r.responses}
        assert not sent & old
        assert len(r2.responses) == n_full                  # the old records are kept, the new appended

    def test_stop_in_a_later_wave_keeps_the_rows_joined_so_far_pending(self):
        items = test_items(5)
        client = FakeAsyncAnthropic(make_responder(tokens=(1000, 200)))
        n_before_gloss = None

        def count():
            return sum(1 for kw in client.calls if step_of_system(system_text(kw)) != "gloss")
        usage = GuardedUsage(budget_usd=10.0)
        r = runner(client, usage=usage, concurrency=1)
        orig = r._wave

        async def wave(name, calls):
            if name == "w4_gloss":
                usage.budget_usd = usage.total_cost_usd  # the next charge crosses
            return await orig(name, calls)
        r._wave = wave
        with pytest.raises(BudgetExceededError):
            r.run(items)
        n_gloss = sum(1 for kw in client.calls if step_of_system(system_text(kw)) == "gloss")
        assert n_gloss == 1
        pend = [x for x in r.results.values() if x.stage == "pending"]
        assert pend and all(x.meta["split_partial"].get("join") for x in pend)


# ---------------------------------------------------------------------------
# 7. parse rate; one retry, alone
# ---------------------------------------------------------------------------

class TestRetryAndParseRate:
    def _run(self, bad_times, caplog=None):
        seen = {"n": 0}

        def override(step, item, kw):
            if step == "kind" and item["label"] == "argumentative" and item["reading"].startswith("you tend"):
                seen["n"] += 1
                if seen["n"] <= bad_times:
                    return "not json at all"
            return None
        client = FakeAsyncAnthropic(make_responder(override=override))
        r = runner(client)
        res = {x.label: x for x in r.run(test_items(3))}
        return client, r, res, seen

    def test_a_failed_row_is_retried_once_alone_and_recovers(self):
        client, r, res, seen = self._run(1)
        assert seen["n"] == 2 and res["argumentative"].stage == "classified"
        retries = [rec for rec in r.responses if rec["stage"] == "kind_retry"]
        assert len(retries) == 1 and retries[0]["keys"] == ["argumentative#1"]
        failed_first = [rec for rec in r.responses if rec["stage"] == "kind" and rec["parse_errors"]]
        assert len(failed_first) == 1   # the failed answer is on record too
        rates = r.step_parse_rates()[f"kind:first:{HAIKU}"]
        assert rates["ok"] == rates["n"] and rates["ok_first_pass"] == rates["n"] - 1

    def test_a_row_that_fails_twice_fails_and_the_rate_warns(self, caplog):
        client, r, res, seen = self._run(99)
        assert seen["n"] == 2   # retried once only
        assert res["argumentative"].stage == "failed" and "retry" in res["argumentative"].error
        with caplog.at_level(logging.INFO):
            r.warn_parse_rate()
        assert "HIGH FAIL RATE" in caplog.text and "kind:first" in caplog.text


# ---------------------------------------------------------------------------
# 9. the second model
# ---------------------------------------------------------------------------

class TestSecondModel:
    def _run(self):
        client = FakeAsyncAnthropic(make_responder(tokens=(1000, 100)))
        usage = MultiModelUsage()
        r = runner(client, usage=usage, second_opinion=True, second_opinion_frac=0.1)
        res = {x.key: x for x in r.run(test_items())}
        return client, r, res, usage

    def test_no_sampling_thinking_or_effort_on_sonnet_55(self):
        client, *_ = self._run()
        son = [kw for kw in client.calls if kw["model"] == SONNET55]
        hai = [kw for kw in client.calls if kw["model"] == HAIKU]
        assert son and hai
        for kw in son:
            assert "temperature" not in kw and "thinking" not in kw and "output_config" not in kw
            assert kw["max_tokens"] == 2000
        assert all(kw["temperature"] == 0.0 for kw in hai)

    def test_haiku_55_as_the_first_model_reaches_every_haiku_step(self):
        """``--model claude-haiku-5-5`` (coding_plan_haiku55.md, item 5): the probe, step 1, the three checks,
        the same-sense check, the gloss, the alignment and the descriptors all go to Haiku 5.5, without
        temperature and with the thinking models' max_tokens; only the comparison (the compare model) and the
        second opinion (the second model) go elsewhere; every record names its model, and the block names
        Haiku 5.5 as the model and the gloss model."""
        h55 = "claude-haiku-5-5"
        intended = {e["word"]: HINT for e in load_jsonl("expected_outcomes.jsonl")[:10]}
        client = FakeAsyncAnthropic(make_responder(tokens=(1000, 300)))
        usage = MultiModelUsage()
        r = runner(client, model=h55, usage=usage, second_opinion=True, second_opinion_frac=0.1,
                   zipf_fn=lambda w: 2.0)                        # every word in the probe band
        res = r.run(test_items(intended=intended))
        first_steps = {"probe", "sense", "established", "vague", "kind", "same_sense", "gloss", "alignment",
                       "descriptors"}
        by_step: dict = {}
        for kw in client.calls:
            by_step.setdefault(step_of_system(system_text(kw)), set()).add(kw["model"])
        assert first_steps <= set(by_step)
        for s in first_steps - {"gloss", "sense", "established", "vague", "kind", "same_sense"}:
            assert by_step[s] == {h55}, s                       # probe, alignment, descriptors: first model only
        for s in ("sense", "established", "vague", "kind", "same_sense", "gloss"):
            assert h55 in by_step[s] and by_step[s] <= {h55, SONNET55}, s   # Sonnet only as the second opinion
        assert by_step["comparison"] == {SONNET55}
        for kw in client.calls:
            if kw["model"] == h55:
                assert not {"temperature", "top_p", "top_k", "thinking", "output_config"} & set(kw)
                assert kw["max_tokens"] == 2000
        chosen = set(r.second_keys)
        first = [rec for rec in r.responses if rec["role"] == "first" and rec["step"] != "comparison"]
        # the record names each call's model: Haiku 5.5, but the gloss of a word chosen for the second opinion
        assert first and all(rec["model"] == (SONNET55 if rec["step"] == "gloss" and rec["keys"][0] in chosen else h55)
                             for rec in first)
        so = [rec for rec in r.responses if rec["role"] == "second"]
        assert so and all(rec["model"] == SONNET55 for rec in so)
        for x in res:
            if x.stage != "classified" or x.filter.get("rule") == "probe":
                continue
            assert x.filter["model"] == h55
            if x.filter["outcome"] == "trait":
                assert x.filter["gloss_model"] == (SONNET55 if x.key in chosen else h55)
        assert usage.per_model[h55].cost_usd == pytest.approx(
            usage.per_model[h55].prompt_tokens * 0.10e-6 + usage.per_model[h55].completion_tokens * 0.50e-6)
        assert "claude-haiku-4-5-20251001" not in usage.per_model

    def test_sonnet_55_priced_at_2_and_10(self):
        _, _, _, usage = self._run()
        t = usage.per_model[SONNET55]
        assert t.cost_usd == pytest.approx(t.prompt_tokens * 2e-6 + t.completion_tokens * 10e-6)

    def test_chosen_words_get_their_gloss_from_the_second_model_for_the_accepted_reading(self):
        client, r, res, _ = self._run()
        chosen = set(r.second_keys)
        assert chosen
        # every word with these notes is chosen, plus the seeded 10%
        for k, x in res.items():
            if {"obvious_sense_not_trait", "most_likely_reading_stretched"} & set(x.filter["notes"]):
                assert k in chosen
        glosses = [(kw["model"], json.loads(user_text(kw))) for kw in client.calls
                   if step_of_system(system_text(kw)) == "gloss"]
        by_label = {x.label: x for x in res.values()}
        for model, item in glosses:
            x = by_label[item["label"]]
            assert item["reading"] == x.filter["judged_sense"]
            assert model == (SONNET55 if x.key in chosen else HAIKU)
        for k in chosen:
            x = res[k]
            so = x.filter["second_opinion"]
            assert so["model"] == SONNET55 and so["agree"] == (so["outcome"] == x.filter["outcome"])
            if x.filter["outcome"] == "trait":
                assert x.filter["gloss_model"] == SONNET55
                assert sum(1 for m, it in glosses if it["label"] == x.label) == 1


# ---------------------------------------------------------------------------
# phrase labels and alignment-sweep roles (gate audit 5, m1_traithood.md section 7; 2026-10-12)
# ---------------------------------------------------------------------------

PHRASE = "accepts shutdown"
#: The first model reads the phrase's one primary reading as stretched (the established check's "she is <label>").
STRETCHED = {(HAIKU, PHRASE, "established"): {"established": "stretched"}}
#: The second model's reading of the phrase, told apart from the synthetic "you are <label>".
SONNET_READING = {(SONNET55, PHRASE, "sense"): {"readings": [{"reading": "you let yourself be shut down",
                                                              "rank": "primary"}]}}


def scripted(table, *, tokens=(1000, 100)):
    """Every answer synthetic (one primary reading, well known, kind trait), except ``table[(model, label,
    step)]``: fields that replace the synthetic row's (a sense answer's ``readings``, an established check's
    ``established``, a kind call's ``kind``, a probe's ``known``)."""
    def override(step, item, kw):
        got = table.get((kw["model"], item.get("label", item.get("word")), step))
        if got is None:
            return synthetic(step, item)
        row = json.loads(synthetic(step, item))["results"][0]
        row.update(got)
        return json.dumps({"results": [row]})
    return make_responder(override=override, tokens=tokens)


def item(label, **meta):
    return FilterItem(key=label.replace(" ", "_") + "#1", label=label, meta=meta)


def calls_by(client, model=None):
    """``[(step, label)]`` of the calls sent (to ``model`` when given)."""
    out = []
    for kw in client.calls:
        if model is None or kw["model"] == model:
            step = step_of_system(system_text(kw))
            it = parse_user(step, user_text(kw))
            out.append((step, it.get("label", it.get("word"))))
    return out


class TestPhrases:
    def _run(self, table, items=None, **kw):
        kw.setdefault("second_opinion", True)
        kw.setdefault("second_opinion_frac", 0.0)   # no sampled second opinion unless a test asks for one
        client = FakeAsyncAnthropic(scripted(table))
        r = runner(client, **kw)
        res = {x.label: x for x in r.run(items or [item(PHRASE), item("zorp")])}
        return client, r, res

    # -- 1. the definition probe ---------------------------------------------------------------
    def test_a_phrase_is_never_sent_to_the_probe(self):
        not_known = {(HAIKU, w, "probe"): {"known": False, "reason": "not a single English word"}
                     for w in ("zorp", PHRASE)}
        client, r, res = self._run(not_known, second_opinion=False, zipf_fn=lambda w: 2.0)  # both in the band
        assert [lab for step, lab in calls_by(client) if step == "probe"] == ["zorp"]
        assert res["zorp"].filter["rule"] == "probe"              # a single word is probed, and cut, as before
        ph = res[PHRASE]
        assert ph.freq["probe_band"] and ph.freq["define_probe"] == split.probe_skipped_record()
        assert ph.filter["rule"] == 3 and ph.filter["outcome"] == "trait"     # it went on to the verdict steps
        assert ("sense", PHRASE) in calls_by(client)
        assert r.stats["probe_skipped_phrase"] == 1
        assert r.phrase_summary()["probe_skipped"] == {"n": 1, "labels": [PHRASE]}

    def test_the_probe_sees_a_single_word_exactly_as_before(self):
        from assistant_axis.gapgen import filter_rubric as fr
        client, *_ = self._run({}, items=[item("zorp")], second_opinion=False, zipf_fn=lambda w: 2.0)
        probe = [kw for kw in client.calls if step_of_system(system_text(kw)) == "probe"]
        assert len(probe) == 1 and system_text(probe[0]) == fr.DEFINE_PROBE_PROMPT
        assert user_text(probe[0]) == fr.build_probe_prompt([{"id": 1, "label": "zorp"}])

    # -- 2. the established check's frame -------------------------------------------------------
    def test_a_phrase_turned_away_as_stretched_is_decided_by_the_second_model(self):
        client, r, res = self._run({**STRETCHED, **SONNET_READING})
        x = res[PHRASE]
        f = x.filter
        assert r.decide_keys == r.phrase_keys == [f"{PHRASE.replace(' ', '_')}#1"] and r.second_keys == []
        assert (f["outcome"], f["verdict"], x.holding, x.entity_type) == ("trait", "trait", None, "trait")
        d = f["decided_by"]
        assert d["rule"] == split.PHRASE_RULE and d["model"] == SONNET55 and d["outcome"] == "trait"
        assert d["first"]["model"] == HAIKU and d["first"]["outcome"] == "turned_away"
        assert d["first"]["cause"] == "stretched" and d["first"]["causes"] == ["stretched"]
        assert d["first"]["sense"]["readings"][0]["established"] == "stretched"
        assert d["agree_first"] is False and d["error"] is None
        # the row is the second model's: its reading, its gloss for that reading; not a sampled opinion
        assert f["judged_sense"] == "you let yourself be shut down" and f["sense"]["readings"][0]["established"] == "well_known"
        assert f["gloss_model"] == SONNET55 and x.gloss and f["region"]
        assert f["second_opinion"] is None and f["comparison"] is None and f["rerouted"] is None
        assert sorted(calls_by(client, SONNET55)) == sorted(
            [("sense", PHRASE), ("established", PHRASE), ("vague", PHRASE), ("kind", PHRASE), ("gloss", PHRASE)])
        gloss = [kw for kw in client.calls if step_of_system(system_text(kw)) == "gloss" and kw["model"] == SONNET55]
        assert json.loads(user_text(gloss[0]))["reading"] == "you let yourself be shut down"
        assert {("alignment", PHRASE), ("descriptors", PHRASE)} <= set(calls_by(client, HAIKU))
        # every call of the decision is recorded as one, on the second model's path
        dec = [rec for rec in r.responses if rec.get("purpose")]
        assert {rec["step"] for rec in dec} == {"sense", "established", "vague", "kind"}
        assert all(rec["purpose"] == "phrase_decision" and rec["role"] == "second" and rec["model"] == SONNET55
                   and rec["keys"] == [f"{PHRASE.replace(' ', '_')}#1"] for rec in dec)
        assert not any(rec.get("purpose") for rec in r.responses if rec["step"] == "gloss")
        # the single word beside it is untouched, and nothing enters the opinions' figures
        assert res["zorp"].filter["decided_by"] is None and res["zorp"].filter["outcome"] == "trait"
        assert r.opinion_rows() == [] and r.tripwire is None
        s = r.phrase_summary()["decided_by_second_model"]
        assert s["n"] == 1 and s["outcomes"] == {"trait": 1} and s["labels"] == {"trait": [PHRASE]}

    def test_the_second_model_may_turn_it_away_too(self):
        client, r, res = self._run({**STRETCHED, (SONNET55, PHRASE, "established"): {"established": "stretched"}})
        f = res[PHRASE].filter
        assert (f["outcome"], f["cause"], f["verdict"], f["tags"]) == ("turned_away", "stretched", "reject", ["stretched"])
        assert f["decided_by"]["outcome"] == "turned_away" and f["decided_by"]["agree_first"] is True
        assert res[PHRASE].gloss is None and ("gloss", PHRASE) not in calls_by(client)

    def test_or_send_it_to_a_holding_list(self):
        _, _, res = self._run({**STRETCHED, (SONNET55, PHRASE, "kind"): {"kind": "state"}})
        x = res[PHRASE]
        assert (x.filter["outcome"], x.holding, x.gloss) == ("states", "states", None)
        assert x.filter["decided_by"]["outcome"] == "states"

    def test_a_failed_decision_leaves_the_first_outcome(self):
        responder = scripted(STRETCHED)   # the second model's kind call fails validation, and its retry too
        client = FakeAsyncAnthropic(lambda kw: (make_response("not json") if kw["model"] == SONNET55 and
                                               step_of_system(system_text(kw)) == "kind" else responder(kw)))
        r = runner(client, second_opinion=True, second_opinion_frac=0.0)
        f = {x.label: x for x in r.run([item(PHRASE)])}[PHRASE].filter
        assert (f["outcome"], f["cause"]) == ("turned_away", "stretched")
        assert f["decided_by"]["outcome"] is None and "kind" in f["decided_by"]["error"]
        assert r.phrase_summary()["decided_by_second_model"]["failed"] == [PHRASE]

    def test_a_single_word_turned_away_as_stretched_is_not_sent(self):
        client, r, res = self._run({(HAIKU, "zorp", "established"): {"established": "stretched"}})
        assert res["zorp"].filter["outcome"] == "turned_away" and res["zorp"].filter["decided_by"] is None
        assert r.decide_keys == [] and calls_by(client, SONNET55) == []

    def test_a_phrase_with_no_reading_goes_to_the_second_model(self):
        """Step 1's frame, "You are <label>.", fails a verb phrase too: a phrase whose every reading found no
        reading at all ("lies about actions") is decided by the second model (coordinator, 2026-10-12)."""
        client, r, res = self._run({(HAIKU, PHRASE, "sense"): {"readings": []}, **SONNET_READING})
        f = res[PHRASE].filter
        assert f["decided_by"]["first"]["causes"] == ["no_reading"] and f["decided_by"]["outcome"] == "trait"
        assert f["outcome"] == "trait" and f["judged_sense"] == "you let yourself be shut down"
        assert r.decide_keys == r.phrase_keys and ("sense", PHRASE) in calls_by(client, SONNET55)

    def test_a_phrase_the_kind_call_turned_away_is_not_sent(self):
        """The kind call's verdict (action, evaluative, not a persona) is about the reading, not the frame."""
        client, r, res = self._run({(HAIKU, PHRASE, "kind"): {"kind": "action"}})
        f = res[PHRASE].filter
        assert (f["outcome"], f["cause"], f["decided_by"]) == ("turned_away", "action", None)
        assert r.phrase_keys == [] and calls_by(client, SONNET55) == []

    def test_without_a_second_model_the_first_outcome_stands(self):
        client, r, res = self._run(STRETCHED, second_opinion=False)
        f = res[PHRASE].filter
        assert f["outcome"] == "turned_away" and f["decided_by"]["model"] is None
        assert "no second model" in f["decided_by"]["error"] and calls_by(client, SONNET55) == []
        assert r.phrase_summary()["decided_by_second_model"]["no_second_model"] == [PHRASE]

    def test_three_readings_one_of_them_stretched(self):
        """Haiku 5.5's three readings: every one turned the phrase away, one as stretched and two with no
        reading; the second model decides it, and so it does a phrase whose three readings all found none."""
        other = "lies about actions"
        seen = {"n": 0}
        base = scripted(STRETCHED)

        def responder(kw):
            step = step_of_system(system_text(kw))
            it = parse_user(step, user_text(kw))
            if kw["model"] == HAIKU and step == "sense" and it["label"] in (PHRASE, other):
                if it["label"] == PHRASE and seen["n"] == 0:   # one reading of three finds a reading
                    seen["n"] += 1
                    return base(kw)
                row = {**json.loads(synthetic("sense", it))["results"][0], "readings": []}   # no reading
                return make_response(json.dumps({"results": [row]}))
            return base(kw)
        client = FakeAsyncAnthropic(responder)
        r = runner(client, readings=3, second_opinion=True, second_opinion_frac=0.0)
        res = {x.label: x for x in r.run([item(PHRASE), item(other)])}
        f = res[PHRASE].filter
        assert sorted(f["decided_by"]["first"]["causes"]) == ["no_reading", "no_reading", "stretched"]
        assert f["verdict_readings"]["outcome"] == "turned_away" and f["outcome"] == "trait"
        g = res[other].filter
        assert g["decided_by"]["first"]["causes"] == ["no_reading"] * 3 and g["outcome"] == "trait"
        assert {lab for _, lab in calls_by(client, SONNET55)} == {PHRASE, other}

    def test_a_sampled_phrase_is_asked_once_and_compared_on_the_first_outcome(self):
        client, r, res = self._run({**STRETCHED, **SONNET_READING}, second_opinion_frac=1.0)
        key = f"{PHRASE.replace(' ', '_')}#1"
        assert key in r.second_keys and key in r.decide_keys
        son = Counter(calls_by(client, SONNET55))
        assert son[("sense", PHRASE)] == son[("kind", PHRASE)] == son[("gloss", PHRASE)] == 1
        f = res[PHRASE].filter
        assert f["outcome"] == "trait" and f["second_opinion"]["agree"] is False
        row = next(o for o in r.opinion_rows() if o["key"] == key)
        assert (row["first"], row["second"]) == ("turned_away", "trait")    # the models, not the decision

    def test_resume_sends_nothing_already_answered(self):
        client, r, res = self._run({**STRETCHED, **SONNET_READING})
        client2 = FakeAsyncAnthropic(scripted({**STRETCHED, **SONNET_READING}))
        r2 = runner(client2, second_opinion=True, second_opinion_frac=0.0, resume_records=list(r.responses))
        res2 = {x.label: x for x in r2.run([item(PHRASE), item("zorp")])}
        assert client2.calls == []
        strip = lambda f: {k: v for k, v in f.items() if k != "at"}  # noqa: E731
        assert strip(res2[PHRASE].filter) == strip(res[PHRASE].filter)

    def test_batches_send_the_decision_as_two_waves(self, tmp_path):
        from assistant_axis.gapgen.batches import BatchTransport
        from assistant_axis.judge_pricing import BATCH_SUFFIX
        from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep
        responder = scripted({**STRETCHED, **SONNET_READING})
        r = runner(FakeAsyncAnthropic(responder), second_opinion=True, second_opinion_frac=0.0)
        bc = FakeBatchClient(responder)
        r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
        res = {x.label: x for x in r.run([item(PHRASE), item("zorp")])}
        assert res[PHRASE].filter["outcome"] == "trait" and res[PHRASE].filter["decided_by"]["model"] == SONNET55
        waves = list(json.loads((tmp_path / "batches.json").read_text())["waves"])
        assert waves[:4] == ["w1_sense", "w2_checks", "w3b_phrase_sense", "w3c_phrase_checks"]
        assert SONNET55 + BATCH_SUFFIX in r.usage.per_model

    def test_only_pinned_prompts_are_sent(self):
        from assistant_axis.gapgen import filter_rubric as fr
        from assistant_axis.gapgen import plain_reading as pr
        from assistant_axis.gapgen import rubric_versions
        client, *_ = self._run({**STRETCHED, **SONNET_READING}, zipf_fn=lambda w: 2.0, second_opinion_frac=1.0)
        pinned = set(sr.load_all().values()) | {fr.DEFINE_PROBE_PROMPT, pr.COMPARISON_PROMPT}
        assert {system_text(kw) for kw in client.calls} <= pinned
        assert sr.mismatches() == [] and rubric_versions.mismatches() == []

    # -- 3. alignment-sweep roles ---------------------------------------------------------------
    def test_alignment_sweep_roles_go_on_to_review_as_traits(self):
        aw, cw, st = "helps build weapons", "guards the vault", "fears the dark"
        table = {(HAIKU, aw, "kind"): {"kind": "role"}, (HAIKU, cw, "kind"): {"kind": "role"},
                 (HAIKU, st, "kind"): {"kind": "state"}}
        client, r, res = self._run(table, items=[item(aw, generators=["alignment_sweep"]),
                                                 item(cw, generators=["censuses"]),
                                                 item(st, generators=["alignment_sweep"])])
        a = res[aw]
        assert (a.filter["outcome"], a.filter["verdict"], a.filter["tags"], a.holding, a.entity_type) == (
            "trait", "trait", [], None, "trait")
        assert a.filter["rerouted"]["rule"] == split.ROLES_TO_REVIEW_RULE and a.filter["rerouted"]["from"] == "roles"
        assert a.gloss and a.filter["gloss_model"] == HAIKU and a.filter["region"]
        assert a.filter["judged_sense"] == f"you are {aw}" and a.filter["person_senses"][0]["kind"] == "role"
        assert ("gloss", aw) in calls_by(client, HAIKU) and a.filter["decided_by"] is None
        # another generator's role, and an alignment-sweep state, are held as before
        assert (res[cw].holding, res[cw].entity_type, res[cw].filter["rerouted"]) == ("roles", "role", None)
        assert (res[st].holding, res[st].filter["rerouted"]) == ("states", None)
        assert r.phrase_summary()["rerouted"] == {"rule": split.ROLES_TO_REVIEW_RULE, "n": 1, "labels": [aw]}

    def test_a_rerouted_row_with_a_second_opinion_is_compared_on_the_models_outcomes(self):
        aw = "helps build weapons"
        table = {(m, aw, "kind"): {"kind": "role"} for m in (HAIKU, SONNET55)}
        _, r, res = self._run(table, items=[item(aw, generators=["alignment_sweep"])], second_opinion_frac=1.0)
        f = res[aw].filter
        assert f["outcome"] == "trait" and f["rerouted"] and f["second_opinion"]["outcome"] == "roles"
        assert f["second_opinion"]["agree"] is True          # both models said roles; the reroute is policy
        assert r.opinion_rows()[0]["first"] == r.opinion_rows()[0]["second"] == "roles"


# ---------------------------------------------------------------------------
# single words: byte-identical requests (gate audit 5, 2026-10-12)
# ---------------------------------------------------------------------------

class TestSingleWordsUnchanged:
    """The phrase rules change nothing for a single word.  The digests are of every request a run on the 98
    single-word test words sends (step, model and user payload, sorted; all in the probe band, 20 with an
    intended sense, a second opinion on 20%), taken on the code before the rules were added (2026-10-12) and
    unchanged after.  The system prompts are checked by their pins (test_gapgen_split_rubrics), so a rubric
    bump does not touch these; a deliberate change to a payload does, and then the digest is recomputed."""
    DIGESTS = {1: (1019, "a6eb476299f054d09258a49b8b916ac7f125d7b04c9b4f13822e00e2fc0f4968"),
               3: (2053, "764a0ca445a7ab0a08f3db994fa5801831adf5512513d095bc58ea0adbab48fe")}

    @pytest.mark.parametrize("readings", [1, 3])
    def test_requests_are_byte_identical(self, readings):
        import hashlib
        intended = {e["word"]: "an intended meaning" for e in load_jsonl("expected_outcomes.jsonl")[:20]}
        items = [it for it in test_items(intended=intended) if not split.is_phrase(it.label)]
        client = FakeAsyncAnthropic(make_responder())
        r = runner(client, zipf_fn=lambda w: 2.0, second_opinion=True, second_opinion_frac=0.2, readings=readings)
        res = r.run(items)
        reqs = sorted(json.dumps([step_of_system(system_text(kw)), kw["model"], user_text(kw)]) for kw in client.calls)
        assert len(items) == 98
        assert (len(reqs), hashlib.sha256("\n".join(reqs).encode()).hexdigest()) == self.DIGESTS[readings]
        assert r.phrase_keys == [] and r.stats["probe_skipped_phrase"] == 0
        assert all(x.filter["decided_by"] is None and x.filter["rerouted"] is None for x in res)
