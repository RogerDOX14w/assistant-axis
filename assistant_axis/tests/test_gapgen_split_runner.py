"""The split filter's runner (coding_plan_split.md section 8, tests 3, 4, 6, 7 and 9).  No API call:
a fake client replays the answers recorded on 2026-09-29 (``split_replay``)."""
import json
import logging

import pytest

from assistant_axis.gapgen import split
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
            assert f["step_versions"] == {"sense": 6, "established": 4, "vague": 3, "kind": 4, "same_sense": 1,
                                          "gloss": 2, "alignment": 1, "descriptors": 1}
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
