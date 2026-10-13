"""The states pass read several times (Roger, 2026-10-13: "if this is Haiku 5.5, and cheap, yes, run three times and
average or majority vote, as appropriate"): the queue call and the gloss check sent N times as independent requests,
the answers combined by vote (:func:`states_pass.combine_queue_readings`, :func:`states_pass.combine_check_readings`),
the route derived from the voted answers, every reading and the vote recorded, and a one-reading run's requests
unchanged byte for byte.  No API call: fake clients throughout (the fixtures of ``test_gapgen_states_pass_v4``)."""
import hashlib
import json
import random
from collections import Counter

import pytest

from assistant_axis.gapgen import states_pass as sp
from assistant_axis.gapgen.batches import BatchTransport
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.judge_pricing import BudgetExceededError
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep
from assistant_axis.tests.test_gapgen_states_pass_v4 import items, qrow, responder, runner

H55 = "claude-haiku-5-5"


def row(**kw):
    """A queue row as the validator returns it."""
    ok, err = sp.validate_queue_row(qrow(1, "x", **kw), "x")
    assert err is None, err
    return ok


LASTING = dict(typical_duration="months", lasting=True, role=False, gloss="This means living with it for months.")
ROLE = dict(typical_duration="years", lasting=True, role=True, gloss="This means having left working life for good.")
PRED = dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
            gloss="This means sinking easily into gloom.")
RENAME = dict(typical_duration="days", lasting=False, plausible=True, name_fits=False, suggested_name="other",
              gloss="This means jolting at every noise.")
HELD = dict(typical_duration="weeks", lasting=False, plausible=False)


# --------------------------------------------------------------------------- the vote

class TestVoteValues:
    def test_unanimous_most_common_and_tie_first(self):
        assert sp.vote_values([True, True, True]) == (True, "unanimous")
        assert sp.vote_values([False, True, True]) == (True, "most_common")
        assert sp.vote_values(["a", "b", "c", "b"]) == ("b", "most_common")
        # tie: the first reading among the leaders (two readings left that differ, or a three-way split)
        assert sp.vote_values([False, True]) == (False, "tie_first")
        assert sp.vote_values([True, False]) == (True, "tie_first")
        assert sp.vote_values(["c", "a", "b"]) == ("c", "tie_first")
        assert sp.vote_values(["a", "b", "b", "a"]) == ("a", "tie_first")
        with pytest.raises(ValueError):
            sp.vote_values([])

    def test_median_duration(self):
        assert sp.median_duration(["hours", "years", "weeks"]) == "weeks"
        assert sp.median_duration(["months", "months", "days"]) == "months"
        assert sp.median_duration(["years"]) == "years"
        # an even count (a failed reading left two): the lower of the two middle ones
        assert sp.median_duration(["months", "weeks"]) == "weeks"
        assert sp.median_duration(["hours", "days", "months", "years"]) == "days"
        with pytest.raises(ValueError):
            sp.median_duration([])


class TestCombineQueueReadings:
    def test_majority_on_lasting_then_role_among_the_lasting_readings_and_the_median_duration(self):
        v = sp.combine_queue_readings([row(**HELD), row(**LASTING), row(**ROLE)])
        a, vote = v["answer"], v["vote"]
        assert a["lasting"] is True and a["role"] is False          # role: tie among readings 2 and 3, the first
        assert vote["fields"]["role"]["how"] == "tie_first" and vote["fields"]["role"]["votes"] == [None, False, True]
        assert a["typical_duration"] == "months"                   # weeks, months, years
        assert a["plausible"] is None and a["name_fits"] is None and "plausible" not in vote["fields"]
        assert vote["fields"]["lasting"] == {"value": True, "how": "most_common", "votes": [False, True, True]}
        # the free text is the winner's: the first reading that agrees with the vote on every voted answer
        assert vote["winner"] == 2 and a["gloss"] == LASTING["gloss"]
        assert (vote["winner_agrees"], vote["n_voted"]) == (2, 2) and vote["unanimous"] is False
        assert sp.route_for(a, label="x") == ("lasting", None)

    def test_the_nested_vote_for_a_state_that_does_not_last(self):
        v = sp.combine_queue_readings([row(**RENAME), row(**LASTING), row(**PRED)])
        a, vote = v["answer"], v["vote"]
        # lasting false (2 of 3); plausible true (both); name_fits: false, true -> a tie, the first: false
        assert (a["lasting"], a["plausible"], a["name_fits"]) == (False, True, False)
        assert vote["fields"]["name_fits"] == {"value": False, "how": "tie_first", "votes": [False, None, True]}
        assert vote["winner"] == 1 and a["suggested_name"] == "other" and a["suggested_stem"] == "other"
        assert a["typical_duration"] == "days"                     # days, months, hours
        assert "role" not in vote["fields"]

    def test_the_winner_need_not_be_the_first_reading(self):
        v = sp.combine_queue_readings([row(**HELD), row(**PRED, reason="Reading two."), row(**PRED)])
        assert v["vote"]["winner"] == 2 and v["answer"]["reason"] == "Reading two."
        assert v["answer"]["gloss"] == PRED["gloss"] and v["answer"]["plausible"] is True

    def test_duration_agrees_is_recomputed_from_the_vote(self):
        # lasting true by two readings that say "weeks" and "months"; the third says "hours": median weeks
        v = sp.combine_queue_readings([row(**{**LASTING, "typical_duration": "weeks"}), row(**PRED),
                                       row(**LASTING)])
        a = v["answer"]
        assert a["lasting"] is True and a["typical_duration"] == "weeks" and a["duration_agrees"] is False
        assert v["vote"]["winner"] == 1

    def test_unanimous(self):
        v = sp.combine_queue_readings([row(**PRED), row(**PRED), row(**PRED)])
        assert v["vote"]["unanimous"] is True and all(f["how"] == "unanimous" for f in v["vote"]["fields"].values())
        assert v["answer"] == row(**PRED)

    def test_a_failed_reading_is_left_out_and_recorded(self):
        v = sp.combine_queue_readings([None, row(**LASTING), row(**HELD)], errors=["unparseable", None, None])
        vote = v["vote"]
        assert vote["failed"] == [1] and vote["n_ok"] == 2 and vote["per_reading"][0] == {"reading": 1,
                                                                                          "error": "unparseable"}
        # two readings left that differ: the first of them
        assert vote["fields"]["lasting"]["how"] == "tie_first" and v["answer"]["lasting"] is True
        assert v["answer"]["typical_duration"] == "weeks"          # weeks, months: the lower middle
        assert vote["unanimous"] is False
        assert sp.combine_queue_readings([None, None, None]) is None

    def test_one_reading_is_that_reading(self):
        v = sp.combine_queue_readings([row(**RENAME)])
        assert v["answer"] == row(**RENAME) and v["vote"]["unanimous"] is True and v["vote"]["winner"] == 1

    def test_per_reading_keeps_every_reading_with_its_free_text(self):
        v = sp.combine_queue_readings([row(**PRED), row(**RENAME), row(**HELD)])
        per = v["vote"]["per_reading"]
        assert [p["reading"] for p in per] == [1, 2, 3]
        assert per[1]["suggested_name"] == "other" and per[1]["gloss"] == RENAME["gloss"] and per[2]["gloss"] is None
        assert set(per[0]) == {"reading", *sp._READING_FIELDS}

    def test_some_reading_always_agrees_fully_and_the_answer_is_a_valid_row(self):
        """The nested vote picks, at each step, a value some reading in the pool holds, so the first reading of the
        final pool agrees on every voted answer: the "agrees on most" fallback is never needed.  Checked on random
        reading sets of one to five readings."""
        rng = random.Random(20261013)
        kinds = [LASTING, ROLE, PRED, RENAME, HELD, {**PRED, "typical_duration": "years"},
                 {**LASTING, "typical_duration": "weeks"}]
        for _ in range(500):
            rows = [row(**rng.choice(kinds)) if rng.random() > 0.15 else None for _ in range(rng.randint(1, 5))]
            v = sp.combine_queue_readings(rows)
            if v is None:
                assert all(r is None for r in rows)
                continue
            assert v["vote"]["winner_agrees"] == v["vote"]["n_voted"]
            a = v["answer"]
            # the combined row is one the validator would accept, so route_for and the block take it as they are
            back, err = sp.validate_queue_row({**{k: a[k] for k in ("reason", "typical_duration", "lasting", "role",
                                                                     "plausible", "name_fits", "suggested_name",
                                                                     "gloss", "confidence")}, "label": "x"}, "x")
            assert err is None and {k: back[k] for k in sp.QUEUE_VOTED_FIELDS} == {k: a[k] for k in
                                                                                     sp.QUEUE_VOTED_FIELDS}
            sp.route_for(a, label="x")


class TestCombineCheckReadings:
    def P(self, reading, reason=None):
        return {"reason": reason or f"Read as {reading}.", "reading": reading}

    def test_the_vote_is_on_confirming_not_on_the_reading(self):
        """Rules 2: three different readings, two of which confirm: confirmed (a vote on the reading itself would have
        no majority, and its first reading, passing, would hold the row)."""
        v = sp.combine_check_readings([self.P("passing"), self.P("lasting", "Two."), self.P("predisposition")],
                                      "predisposition", rules=2)
        assert v["accepted"] is True and v["vote"]["how"] == "most_common"
        # the reading recorded: the most common on the winning side, a tie there going to the first (lasting)
        assert v["check"] == {"reason": "Two.", "reading": "lasting"} and v["vote"]["winner"] == 2
        assert v["vote"]["accepts"] == [False, True, True] and v["vote"]["unanimous"] is False

    def test_a_majority_of_passing_holds(self):
        v = sp.combine_check_readings([self.P("predisposition"), self.P("passing", "Now."), self.P("passing")],
                                      "predisposition", rules=2)
        assert v["accepted"] is False and v["check"] == {"reason": "Now.", "reading": "passing"}

    def test_rules_1(self):
        v = sp.combine_check_readings([self.P("lasting"), self.P("predisposition"), self.P("lasting")],
                                      "predisposition", rules=1)
        assert v["accepted"] is False and v["check"]["reading"] == "lasting" and v["vote"]["winner"] == 1

    def test_ties_failed_readings_and_unanimity(self):
        v = sp.combine_check_readings([None, self.P("passing"), self.P("predisposition")], "predisposition",
                                      errors=["unparseable response", None, None])
        assert v["vote"]["how"] == "tie_first" and v["accepted"] is False          # the first reading left
        assert v["vote"]["failed"] == [1] and v["vote"]["per_reading"][0]["error"] == "unparseable response"
        u = sp.combine_check_readings([self.P("lasting")] * 3, "lasting")
        assert u["accepted"] is True and u["vote"]["unanimous"] is True and u["vote"]["how"] == "unanimous"
        assert sp.combine_check_readings([None, None], "lasting") is None

    def test_one_reading_is_that_reading(self):
        p = self.P("predisposition")
        v = sp.combine_check_readings([p], "predisposition")
        assert v["check"] == p and v["accepted"] is True


# --------------------------------------------------------------------------- the runner

def by_reading(base, change):
    """A responder whose queue answer for a label on the label's n-th queue call is changed by ``change[label][n]``
    (a dict of answers, or "bad" for a row that fails validation).  The calls go out in order: the first wave's
    readings 1 to N (n = 0 to N-1), then the retry wave's calls, reading by reading (n = N on)."""
    seen: Counter = Counter()

    def answer(kw):
        if system_text(kw) != sp.QUEUE_PROMPT:
            return base(kw)
        body = json.loads(base(kw).content[0].text)
        for x in body["results"]:
            n = seen[x["label"]]
            seen[x["label"]] += 1
            ch = change.get(x["label"], {}).get(n)
            if ch == "bad":
                x["typical_duration"] = "fortnights"
            elif ch:
                x.update({"role": None, "plausible": None, "name_fits": None, "suggested_name": None, "gloss": None})
                x.update(ch)
        return make_response(json.dumps(body), input_tokens=1000, output_tokens=200)
    return answer


def check_by_reading(base, readings):
    """A responder whose check answer for a label is ``readings[label][r]`` on its r-th check call."""
    seen: Counter = Counter()

    def answer(kw):
        if system_text(kw) != sp.CHECK_PROMPT:
            return base(kw)
        lb = json.loads(user_text(kw))["label"]
        r = seen[lb]
        seen[lb] += 1
        rd = readings.get(lb, ["predisposition"] * 9)[r]
        if rd == "bad":
            return make_response("no idea", input_tokens=300, output_tokens=5)
        return make_response(json.dumps({"reason": f"Reading {r + 1}.", "reading": rd}), input_tokens=300,
                             output_tokens=40)
    return answer


def steps(client):
    return Counter("queue" if system_text(c) == sp.QUEUE_PROMPT else "check" if system_text(c) == sp.CHECK_PROMPT
                   else "alignment" for c in client.calls)


class TestRunnerReadings:
    def test_three_readings_of_every_queue_chunk_and_check_one_alignment(self):
        client = FakeAsyncAnthropic(responder())
        r = runner(client, model=H55, readings=3)
        out = {x.key: x for x in r.run(items())}
        # the fake model answers alike every time: the same routes as one reading
        ref = {x.key: x.block["route"] for x in runner(FakeAsyncAnthropic(responder()), model=H55).run(items())}
        assert {k: x.block["route"] for k, x in out.items()} == ref
        assert steps(client) == {"queue": 3, "check": 6, "alignment": 4}
        # the readings send the same request
        q = [c for c in client.calls if system_text(c) == sp.QUEUE_PROMPT]
        assert len({json.dumps(c, sort_keys=True) for c in q}) == 1
        b = out["moodish#1"].block
        assert b["readings"] == 3 and b["queue_readings"]["unanimous"] is True
        assert b["gloss_check"]["check_readings"]["readings"] == ["predisposition"] * 3
        assert all(x.block["readings"] == 3 and x.block["queue_readings"]["n"] == 3 for x in out.values())

    def test_the_route_follows_the_voted_answers(self):
        """lastwell: reading 2 reads a state that does not last; the vote keeps it lasting.  glumish: readings 2 and 3
        read it lasting, so it is lasting, with reading 2's gloss.  wetish: one reading of three finds a predisposition
        plausible; held."""
        long_gloss = "This means living for months under a cloud, every day colored by it."
        change = {"lastwell": {1: dict(typical_duration="weeks", lasting=False, plausible=True, name_fits=True,
                                       gloss="This means grieving again and again.")},
                  "glumish": {1: dict(typical_duration="months", lasting=True, role=False, gloss=long_gloss),
                              2: dict(typical_duration="years", lasting=True, role=False, gloss="This means it.")},
                  "wetish": {2: dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
                                     gloss="This means getting soaked often.")}}
        out = {x.key.split("#")[0]: x.block for x in runner(FakeAsyncAnthropic(by_reading(responder(), change)),
                                                             model=H55, readings=3).run(items())}
        assert out["lastwell"]["route"] == "lasting" and out["lastwell"]["typical_duration"] == "months"
        assert out["lastwell"]["queue_readings"]["fields"]["lasting"]["votes"] == [True, False, True]
        assert [p["route"] for p in out["lastwell"]["queue_readings"]["per_reading"]] == [
            "lasting", "predisposition", "lasting"]
        g = out["glumish"]
        assert g["route"] == "lasting" and g["gloss"] == long_gloss and g["queue_readings"]["winner"] == 2
        assert g["typical_duration"] == "months" and g["lasting"] is True and g["plausible"] is None
        assert g["gloss_check"]["kind"] == "lasting"
        assert out["wetish"]["route"] == "held" and out["wetish"]["queue_readings"]["fields"]["plausible"]["votes"] == [
            False, False, True]

    def test_the_route_is_derived_not_voted(self):
        """Readings: renamed (name does not fit, suggests "other"); predisposition by a suggestion that is the label
        itself; predisposition (name fits).  A vote on routes would say predisposition (two of three); the voted
        answers say the name does not fit (two of three), and the winner, reading 1, names "other": renamed."""
        change = {"glumish": {0: dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False,
                                      suggested_name="other", gloss="This means sinking easily into gloom."),
                              1: dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False,
                                      suggested_name="Glumish", gloss="This means sinking easily into gloom.")}}
        out = runner(FakeAsyncAnthropic(by_reading(responder(), change)), model=H55, readings=3).run(
            items(("glumish",)))
        b = out[0].block
        assert [p["route"] for p in b["queue_readings"]["per_reading"]] == ["renamed", "predisposition",
                                                                          "predisposition"]
        assert b["route"] == "renamed" and b["suggested_name"] == "other" and b["name_fits"] is False

    def test_the_gloss_check_is_read_three_times_and_voted(self):
        base = responder()
        chk = {"moodish": ["passing", "lasting", "predisposition"], "nowish": ["predisposition", "passing", "passing"]}
        client = FakeAsyncAnthropic(check_by_reading(base, chk))
        out = {x.key.split("#")[0]: x.block for x in runner(client, model=H55, readings=3).run(
            items(("moodish", "nowish")))}
        m = out["moodish"]
        assert m["route"] == "predisposition" and m["gloss_check"]["accepted"] is True
        assert m["gloss_check"]["check"]["reading"] == "lasting" and m["gloss_check"]["check"]["reason"] == "Reading 2."
        assert m["gloss_check"]["check"]["rubric_version"] == 1
        assert m["gloss_check"]["check_readings"]["accepts"] == [False, True, True]
        n = out["nowish"]
        assert n["route"] == "held" and n["proposed_route"] == "predisposition"
        assert n["route_reason"] == "gloss check: the predisposition gloss was read as passing: Reading 2."
        assert steps(client) == {"queue": 3, "check": 6, "alignment": 2}

    def test_a_failed_check_reading_is_asked_again_then_left_out(self):
        # calls in order: readings 1, 2, 3, then reading 1's retry; reading 1 fails both times
        chk = {"moodish": ["bad", "passing", "predisposition", "bad"]}
        client = FakeAsyncAnthropic(check_by_reading(responder(), chk))
        r = runner(client, model=H55, readings=3)
        b = r.run(items(("moodish",)))[0].block
        cr = b["gloss_check"]["check_readings"]
        assert steps(client)["check"] == 4 and r.stats["call_retries"] == 1
        assert cr["failed"] == [1] and cr["readings"] == [None, "passing", "predisposition"]
        assert cr["per_reading"][0]["error"].startswith("unparseable response")
        # two readings left that split: the first of them (passing) decides; the row is held
        assert cr["how"] == "tie_first" and b["gloss_check"]["accepted"] is False and b["route"] == "held"

    def test_a_check_no_reading_answered_fails_the_row(self):
        client = FakeAsyncAnthropic(check_by_reading(responder(), {"moodish": ["bad"] * 6}))
        out = runner(client, model=H55, readings=3).run(items(("moodish",)))[0]
        assert out.stage == "failed" and out.block is None
        assert out.error.startswith("gloss check: check reading 1: unparseable response")

    def test_a_queue_reading_that_fails_twice_is_left_out(self):
        change = {"glumish": {1: "bad", 3: "bad"}}                       # reading 2's first try and its retry
        out = runner(FakeAsyncAnthropic(by_reading(responder(), change)), model=H55, readings=3).run(
            items(("glumish", "wetish")))
        b = {x.key.split("#")[0]: x for x in out}
        g = b["glumish"].block
        assert b["glumish"].stage == "judged" and g["route"] == "predisposition"
        qr = g["queue_readings"]
        assert qr["failed"] == [2] and qr["n_ok"] == 2
        assert qr["per_reading"][1]["reading"] == 2 and "typical_duration" in qr["per_reading"][1]["error"]

    def test_a_row_no_reading_answered_fails_with_every_readings_error(self):
        change = {"glumish": {r: "bad" for r in range(6)}}
        out = {x.key.split("#")[0]: x for x in runner(FakeAsyncAnthropic(by_reading(responder(), change)),
                                                       model=H55, readings=3).run(items(("glumish", "wetish")))}
        assert out["glumish"].stage == "failed" and out["glumish"].block is None
        assert out["glumish"].error.startswith("queue reading 1: typical_duration") and "queue reading 3:" in \
            out["glumish"].error
        assert out["wetish"].stage == "judged"

    def test_records_carry_their_reading_and_distinct_custom_ids(self):
        r = runner(FakeAsyncAnthropic(responder()), model=H55, readings=3)
        r.run(items())
        by = Counter((rec["step"], rec.get("verdict_reading")) for rec in r.responses)
        assert by == {("queue", 1): 1, ("queue", 2): 1, ("queue", 3): 1, ("check", 1): 2, ("check", 2): 2,
                      ("check", 3): 2, ("alignment", None): 4}
        cids = [rec["custom_id"] for rec in r.responses]
        assert len(set(cids)) == len(cids)
        assert {rec["custom_id"].split("-")[0] for rec in r.responses} == {"que", "que2", "que3", "che", "che2",
                                                                           "che3", "ali"}

    def test_reading_1_sends_a_one_reading_runs_requests(self):
        one = FakeAsyncAnthropic(responder())
        runner(one, model=H55).run(items())
        three = FakeAsyncAnthropic(responder())
        runner(three, model=H55, readings=3).run(items())
        c1 = Counter(_canon(c) for c in one.calls)
        c3 = Counter(_canon(c) for c in three.calls)
        read = {_canon(c) for c in one.calls if system_text(c) in (sp.QUEUE_PROMPT, sp.CHECK_PROMPT)}
        # every request of the one-reading run, three times over for the queue and check calls, once for alignment
        assert c3 == Counter({k: n * (3 if k in read else 1) for k, n in c1.items()})
        assert len(read) == 3                                            # one queue call, two checks

    def test_the_parse_rate_of_the_readings_is_counted(self):
        change = {"glumish": {1: "bad", 3: "bad"}}
        r = runner(FakeAsyncAnthropic(by_reading(responder(), change)), model=H55, readings=3)
        r.run(items(("glumish", "wetish")))
        assert (r.stats["reading_rows_ok"], r.stats["reading_rows_total"]) == (5, 6)

    def test_resume_replays_every_reading(self):
        change = {"lastwell": {1: dict(typical_duration="weeks", lasting=False, plausible=False)}}
        first = runner(FakeAsyncAnthropic(by_reading(responder(), change)), model=H55, readings=3)
        a = {x.key: x.block for x in first.run(items())}
        client = FakeAsyncAnthropic(responder())
        second = runner(client, model=H55, readings=3, resume_records=first.responses)
        b = {x.key: x.block for x in second.run(items())}
        assert client.calls == []
        strip = lambda d: {k: {kk: vv for kk, vv in v.items() if kk != "at"} for k, v in d.items()}  # noqa: E731
        assert strip(a) == strip(b)
        assert a["lastwell#1"]["queue_readings"]["fields"]["lasting"]["votes"] == [True, False, True]

    def test_a_stop_leaves_rows_with_a_missing_reading_pending_and_resume_asks_only_it(self):
        usage = GuardedUsage(budget_usd=0.05)
        first = runner(FakeAsyncAnthropic(responder(tokens=(1_000_000, 10))), model=H55, readings=3, usage=usage,
                       concurrency=1)
        with pytest.raises(BudgetExceededError):
            first.run(items())
        assert all(x.stage == "pending" for x in first.results.values())   # only reading 1 came back
        assert [rec.get("verdict_reading") for rec in first.responses] == [1]
        client = FakeAsyncAnthropic(responder())
        second = runner(client, model=H55, readings=3, resume_records=first.responses)
        out = {x.key: x for x in second.run(items())}
        assert all(x.stage == "judged" for x in out.values())
        assert steps(client) == {"queue": 2, "check": 6, "alignment": 4}

    def test_through_the_message_batches_api(self, tmp_path):
        r = runner(FakeAsyncAnthropic(responder()), model=H55, readings=3, usage=GuardedUsage(budget_usd=5.0))
        bc = FakeBatchClient(responder())
        r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
        out = {x.key: x.block for x in r.run(items())}
        assert out["moodish#1"]["queue_readings"]["n"] == 3
        assert list(json.loads((tmp_path / "batches.json").read_text())["waves"]) == ["queue", "gloss"]
        for b in bc.batches.created:
            cids = [q["custom_id"] for q in b["requests"]]
            assert len(set(cids)) == len(cids)
            assert all(len(c) <= 64 and all(ch.isalnum() or ch in "_-" for ch in c) for c in cids)
        assert len(bc.batches.created[0]["requests"]) == 3

    def test_readings_are_validated_and_the_corpus_mode_reads_once(self):
        for bad in (0, -1, 1.5, True, "3"):
            with pytest.raises(ValueError):
                runner(None, readings=bad)
        with pytest.raises(ValueError):
            sp.StatesPassRunner(client=None, batch_id="c", mode="corpus", readings=3)
        assert sp.StatesPassRunner(client=None, batch_id="c", mode="corpus").readings == 1

    def test_the_default_readings_are_m1s(self):
        from assistant_axis.gapgen import split_runner as SR
        assert sp.default_readings(H55) == SR.default_readings(H55) == 3
        assert sp.default_readings("claude-haiku-4-5-20251001") == 1
        assert sp.default_readings("claude-sonnet-5-5") == 1
        # the library default is one reading; the CLI chooses the model's default
        assert runner(None, model=H55).readings == 1


class TestSummary:
    def test_the_readings_section(self):
        change = {"lastwell": {1: dict(typical_duration="weeks", lasting=False, plausible=False)},
                  "glumish": {1: "bad", 3: "bad"}}
        chk = {"moodish": ["passing", "predisposition", "predisposition"]}
        r = runner(FakeAsyncAnthropic(check_by_reading(by_reading(responder(), change), chk)), model=H55, readings=3)
        res = r.run(items())
        s = sp.summarize(res, mode="queue", stats=r.stats, usage=r.usage, readings=3)
        q = s["queue_readings"]
        assert s["n_readings"] == 3 and q["n_readings"] == 3 and q["n_rows"] == 7
        assert q["route_agreement"] == {"3/3": 5, "2/3": 1, "2/2": 1}
        assert q["route_all_agree"] == 5 and q["duration_agreement"]["2/3"] == 1
        assert q["with_a_failed_reading"] == {"n": 1, "labels": ["glumish"]}
        assert q["differs_from_first_reading"]["n"] == 0 and q["ties"]["n"] == 0
        assert q["check"]["n_rows"] == 2 and q["check"]["accept_split"] == {"n": 1, "labels": ["moodish"]}
        one = runner(FakeAsyncAnthropic(responder()), model=H55)
        s1 = sp.summarize(one.run(items()), mode="queue", stats=one.stats, usage=one.usage)
        assert s1["n_readings"] == 1 and s1["queue_readings"] == {"n_readings": 1}


# --------------------------------------------------------------------------- one reading: unchanged

def _canon(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False, default=str)


def _flaky():
    """The v4 responder with a failed check, a failed alignment call and a queue row missing from the first call:
    every retry path of a one-reading run."""
    base = responder(bad_check_once=("moodish",), bad_align=("glumish",))
    n = {"q": 0}

    def answer(kw):
        if system_text(kw) == sp.QUEUE_PROMPT and n["q"] == 0:
            n["q"] += 1
            body = json.loads(base(kw).content[0].text)
            body["results"] = [r for r in body["results"] if r["label"] != "glumish"]
            return make_response(json.dumps(body))
        return base(kw)
    return answer


class TestOneReadingIsUnchanged:
    """The request bytes of a one-reading run, pinned on the code before readings were added (2026-10-13, commit
    0301aa09): every live request (kwargs, sorted canonical JSON) and every batch request (custom id and params).  A
    change to any of these hashes means a one-reading run no longer sends what it sent before; that is a bug, not a pin
    to move."""
    PINS = {"live_plain": (7, "3dc2506c894a8a73bc9806ee08d4a8e20c66a9a719664d94d469bc5bc6df0da3"),
            "live_retries": (10, "cea948e1d9fdd4803bf8c19e4410f2e0ec77ce27ba682ede1219e1d33214d519"),
            "live_batch3": (9, "4ba5457f53934e39f57d4e4cfea7b15977e8585ab085d153f5e52fdcb69acefb"),
            "batches": (4, "f35c9366b67dd8005972e0e63a6153f15dff3aa57dec436908927418e89387ed")}

    @staticmethod
    def _live(resp, **kw) -> list[str]:
        c = FakeAsyncAnthropic(resp)
        runner(c, model=H55, **kw).run(items())
        return sorted(_canon(k) for k in c.calls)

    def _check(self, name, got):
        n, h = self.PINS[name]
        assert (len(got), hashlib.sha256(_canon(got).encode()).hexdigest()) == (n, h)

    @pytest.mark.parametrize("kw", [{}, {"readings": 1}])
    def test_live_requests(self, kw):
        self._check("live_plain", self._live(responder(), **kw))
        self._check("live_retries", self._live(_flaky(), **kw))
        self._check("live_batch3", self._live(responder(), batch_size=3, **kw))

    def test_batch_requests(self, tmp_path):
        r = runner(FakeAsyncAnthropic(responder()), model=H55, usage=GuardedUsage(budget_usd=5.0), readings=1)
        bc = FakeBatchClient(_flaky())
        r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
        r.run(items())
        self._check("batches", [_canon(b["requests"]) for b in bc.batches.created])

    def test_records_keep_their_shape_and_blocks_say_one_reading(self):
        r = runner(FakeAsyncAnthropic(responder()), model=H55)
        out = r.run(items())
        assert not any("verdict_reading" in rec for rec in r.responses)
        assert all(x.block["readings"] == 1 and "queue_readings" not in x.block for x in out)
        assert not any("check_readings" in (x.block.get("gloss_check") or {}) for x in out)


# --------------------------------------------------------------------------- the CLI

from assistant_axis.gapgen.registry import Registry  # noqa: E402
from assistant_axis.tests.test_gapgen_states_pass_v4 import _registry, _states_row, cli  # noqa: E402,F401 (fixture)


def _argv(reg, cand, *extra, batch="sp3"):
    return ["--batch-id", batch, "--mode", "queue", "--holding-states", "--registry", str(reg), "--out-root",
            str(cand), "--transport", "live", *extra]


class TestCLI:
    def test_three_readings_by_default_on_haiku_55_end_to_end(self, tmp_path, cli):
        reg, cand = _registry(tmp_path), tmp_path / "cand"
        # lastwell: reading 2 reads a passing state; the vote keeps it lasting
        cli["responder"] = by_reading(responder(), {"lastwell": {1: dict(typical_duration="weeks", lasting=False,
                                                                         plausible=False)}})
        assert cli["mod"].main(_argv(reg, cand)) == 0
        d = cand / "states_pass" / "sp3"
        run = json.loads((d / "run.json").read_text())
        assert run["readings"] == 3 and run["sessions"][0]["readings"] == 3
        assert run["readings_rule"] == sp.QUEUE_READINGS_RULE and run["check_readings_rule"] == sp.CHECK_READINGS_RULE
        assert "3 readings" in run["estimate_lines"][0] and "3 readings" in run["estimate_lines"][1]
        rows = Registry(reg).fold()
        labels = ("lastwell", "rolish", "glumish", "moodish", "nowish", "startly", "startly2", "wetish")
        blocks = {lb: rows[f"{lb}#1"]["states_pass"] for lb in labels}
        assert all(b["readings"] == 3 and b["queue_readings"]["n"] == 3 for b in blocks.values())
        lw = blocks["lastwell"]
        assert lw["route"] == "lasting" and rows["lastwell#1"]["holding"] == "states_released"
        assert lw["queue_readings"]["fields"]["lasting"]["votes"] == [True, False, True]
        assert blocks["moodish"]["gloss_check"]["check_readings"]["n"] == 3
        # the same routes as one reading (test_gapgen_states_pass_v4: test_registry_mode_routes_every_row)
        assert {lb: rows[f"{lb}#1"]["holding"] for lb in labels} == {
            "lastwell": "states_released", "rolish": "roles", "glumish": "states_released",
            "moodish": "states_released", "nowish": "states", "startly": "states", "startly2": "states_released",
            "wetish": "states"}
        res = {json.loads(x)["key"]: json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()}
        assert all(res[k]["block"] == rows[k]["states_pass"] for k in res)
        # three queue calls, two checks three times, five alignment calls (one a released gloss)
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 14
        recs = [json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines()]
        assert Counter(r.get("verdict_reading") for r in recs if r["step"] == "queue") == {1: 1, 2: 1, 3: 1}
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["n_readings"] == 3 and s["queue_readings"]["route_agreement"] == {"3/3": 7, "2/3": 1}
        assert s["routes"] == {"role": 1, "lasting": 1, "predisposition": 3, "renamed": 1, "held": 2}

    def test_one_reading_by_default_off_haiku_55(self, tmp_path, cli):
        reg, cand = _registry(tmp_path), tmp_path / "cand"
        assert cli["mod"].main(_argv(reg, cand, "--model", "claude-haiku-4-5-20251001")) == 0
        d = cand / "states_pass" / "sp3"
        run = json.loads((d / "run.json").read_text())
        assert run["readings"] == 1 and "readings_rule" not in run and run["sessions"][0]["readings"] == 1
        rows = Registry(reg).fold()
        b = rows["moodish#1"]["states_pass"]
        assert b["readings"] == 1 and "queue_readings" not in b and "check_readings" not in b["gloss_check"]
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 8
        assert not any("verdict_reading" in json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines())

    def test_an_explicit_count_wins(self, tmp_path, cli):
        reg, cand = _registry(tmp_path), tmp_path / "cand"
        assert cli["mod"].main(_argv(reg, cand, "--model", "claude-haiku-4-5-20251001", "--readings", "2")) == 0
        assert json.loads((cand / "states_pass" / "sp3" / "run.json").read_text())["readings"] == 2
        assert Registry(reg).fold()["glumish#1"]["states_pass"]["queue_readings"]["n"] == 2
        for bad in ("0", "-2"):
            with pytest.raises(SystemExit):
                cli["mod"].main(_argv(reg, cand, "--readings", bad, batch="bad"))

    def test_resume_keeps_the_recorded_count_and_refuses_another(self, tmp_path, cli):
        reg, cand = _registry(tmp_path), tmp_path / "cand"
        cli["responder"] = responder(tokens=(1_000_000, 10))
        assert cli["mod"].main(_argv(reg, cand, "--budget-usd", "0.05")) == 2
        rows = Registry(reg).fold()
        # only reading 1 came back before the stop: no row is decided, none is written
        assert all(not rows[f"{lb}#1"].get("states_pass") for lb in ("rolish", "wetish", "lastwell"))
        d = cand / "states_pass" / "sp3"
        before = (d / "run.json").read_text()
        with pytest.raises(SystemExit, match="read the queue call 3 time"):
            cli["mod"].main(_argv(reg, cand, "--resume", "--readings", "1"))
        assert (d / "run.json").read_text() == before
        cli["responder"] = responder()
        assert cli["mod"].main(_argv(reg, cand, "--resume")) == 0
        second = cli["live"][-1]
        assert steps(second) == {"queue": 2, "check": 6, "alignment": 5}
        run = json.loads((d / "run.json").read_text())
        assert run["readings"] == 3 and [s["readings"] for s in run["sessions"]] == [3, 3]
        assert Registry(reg).fold()["rolish#1"]["states_pass"]["queue_readings"]["n_ok"] == 3

    def test_resume_of_a_run_that_recorded_no_count_reads_once(self, tmp_path, cli):
        reg, cand = _registry(tmp_path), tmp_path / "cand"
        cli["responder"] = responder(tokens=(1_000_000, 10))
        assert cli["mod"].main(_argv(reg, cand, "--budget-usd", "0.05", "--readings", "1")) == 2
        d = cand / "states_pass" / "sp3"
        run = json.loads((d / "run.json").read_text())
        run.pop("readings")                           # a run from before 2026-10-13
        for s in run["sessions"]:
            s.pop("readings")
        (d / "run.json").write_text(json.dumps(run))
        with pytest.raises(SystemExit, match="resume with --readings 1"):
            cli["mod"].main(_argv(reg, cand, "--resume", "--readings", "3"))
        cli["responder"] = responder()
        assert cli["mod"].main(_argv(reg, cand, "--resume")) == 0
        assert json.loads((d / "run.json").read_text())["readings"] == 1
        assert Registry(reg).fold()["lastwell#1"]["states_pass"]["readings"] == 1

    def test_the_estimate_counts_every_reading(self, tmp_path, cli):
        import argparse
        its = [sp.StatesItem(key=f"w{i}#1", label=f"w{i}", text="being low for a while") for i in range(100)]
        est = {}
        for k in (1, 3):
            args = argparse.Namespace(mode="queue", batch_size=20, model=H55, readings=k)
            est[k] = cli["mod"].build_estimate(its, args, "live")
        one, three = ({x.label.split(" (")[0]: x for x in est[k].lines} for k in (1, 3))
        assert three["states pass"].n_calls == 3 * one["states pass"].n_calls == 18
        assert three["gloss check v1"].n_calls == 3 * one["gloss check v1"].n_calls == 300
        assert three["M1's alignment call"].n_calls == one["M1's alignment call"].n_calls == 100
        align = one["M1's alignment call"].usd
        assert est[3].usd == pytest.approx(3 * (est[1].usd - align) + align)

    def test_dry_run_says_how_many_readings_and_the_gate_counts_them(self, tmp_path, cli, capsys):
        reg, cand = _registry(tmp_path), tmp_path / "cand"
        assert cli["mod"].main(_argv(reg, cand, "--dry-run")) == 0
        out = capsys.readouterr().out
        assert '"readings": 3' in out and "readings: 3 of the queue call and of the gloss check per row" in out
        assert "each call below is sent 3 times" in out and "3 readings" in out
        est3 = float(out.split("total estimate = $")[1].split()[0])
        assert cli["mod"].main(_argv(reg, cand, "--dry-run", "--readings", "1")) == 0
        est1 = float(capsys.readouterr().out.split("total estimate = $")[1].split()[0])
        assert est3 > 2 * est1
        # the cost gate refuses an estimate over the cap: three readings cost more than one
        assert cli["mod"].main(_argv(reg, cand, "--budget-usd", f"{(est1 + est3) / 2:.4f}")) == 2
        assert cli["live"] == []

    def test_the_corpus_mode_and_reroute_refuse_a_count(self, tmp_path, cli):
        with pytest.raises(SystemExit, match="queue only"):
            cli["mod"].main(["--batch-id", "c3", "--mode", "corpus", "--stems", "fretful", "--readings", "3",
                             "--dry-run"])
        with pytest.raises(SystemExit, match="replays each batch"):
            cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry",
                             str(tmp_path / "r.jsonl"), "--readings", "3"])


class TestReroute:
    """A batch judged with three readings under route rules 1 is re-routed under rules 2 from its record: every
    reading replayed, no call; ``--send-missing`` asks the missing check once per reading."""

    def _batch(self, tmp_path, cli, change=None):
        from assistant_axis.tests.test_gapgen_states_pass_rules2 import answers
        reg = tmp_path / "registry.jsonl"
        for lb in ("crossish", "passish", "hopish", "plainheld", "renamish"):
            _states_row(reg, lb, gen="states_pass" if lb == "hopish" else "g")
        cand = tmp_path / "cand"
        cli["responder"] = by_reading(answers(), change) if change else answers()
        assert cli["mod"].main(_argv(reg, cand, "--route-rules", "1", batch="b3")) == 0
        assert json.loads((cand / "states_pass" / "b3" / "run.json").read_text())["readings"] == 3
        return reg, cand

    def test_reroute_replays_every_reading(self, tmp_path, cli, capsys):
        reg, cand = self._batch(tmp_path, cli)
        n_clients = len(cli["live"])
        capsys.readouterr()
        assert cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand), "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "CHANGED   crossish (b3): held -> predisposition (states_released)" in out
        assert "NEEDS     hopish (b3): held -> predisposition once alignment and 3 check call(s) are made" in out
        assert "--send-missing would make 4 call(s)" in out
        assert cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand)]) == 0
        assert len(cli["live"]) == n_clients
        b = Registry(reg).fold()["crossish#1"]["states_pass"]
        assert b["route"] == "predisposition" and b["readings"] == 3 and b["queue_readings"]["n_ok"] == 3
        assert b["gloss_check"]["check_readings"]["readings"] == ["lasting"] * 3 and b["batch_id"] == "b3"

    def test_send_missing_asks_each_reading(self, tmp_path, cli):
        reg, cand = self._batch(tmp_path, cli)
        assert cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand), "--send-missing"]) == 0
        assert steps(cli["live"][-1]) == {"check": 3, "alignment": 1}
        h = Registry(reg).fold()["hopish#1"]
        assert h["holding"] == "states_released" and h["states_pass"]["gloss_check"]["check_readings"]["n"] == 3

    def test_a_failed_reading_waits_on_its_queue_call(self, tmp_path, cli, capsys):
        """crossish's reading 2 failed twice in its batch (decided on two readings): the re-route waits on that
        reading's queue call, which is keyed by its chunk, and lists it; the estimate counts it and the gloss calls
        that may follow; the other rows are replayed without crossish, so their gloss answers on record settle them.
        Before 2026-10-13 crossish and passish listed no call, the estimate was $0 and --send-missing ran with no
        cap."""
        reg, cand = self._batch(tmp_path, cli, change={"crossish": {1: "bad", 3: "bad"}})
        before = {k: r["states_pass"] for k, r in Registry(reg).fold().items() if r.get("states_pass")}
        assert before["crossish#1"]["queue_readings"]["failed"] == [2]
        capsys.readouterr()
        argv = ["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg), "--out-root", str(cand)]
        assert cli["mod"].main([*argv, "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert ("NEEDS     crossish (b3): held -> predisposition once queue call(s) are made (not on record), then up "
                "to 4 gloss call(s)") in out
        assert "NEEDS     hopish (b3): held -> predisposition once alignment and 3 check call(s) are made" in out
        assert "UNCHANGED 3: passish (held), plainheld (held), renamish (renamed)" in out
        assert "--send-missing would make 5 call(s) ({'queue': 1, 'check': 3, 'alignment': 1}), then up to 4" in out
        assert cli["mod"].main([*argv, "--send-missing"]) == 0
        client = cli["live"][-1]
        assert steps(client) == {"queue": 1, "check": 3, "alignment": 1}
        q = next(c for c in client.calls if system_text(c) == sp.QUEUE_PROMPT)
        assert [json.loads(x)["label"] for x in user_text(q).splitlines()[1:]] == ["crossish"]
        run = json.loads((cand / "states_pass" / "rr" / "run.json").read_text())
        assert run["estimate_usd"] > 0 and run["cap_usd"] == 1.0
        rows = Registry(reg).fold()
        c = rows["crossish#1"]["states_pass"]
        assert c["route"] == "predisposition" and c["queue_readings"]["n_ok"] == 3 and c["batch_id"] == "b3"
        assert {k for k in before if rows[k]["states_pass"] != before[k]} == {"crossish#1", "hopish#1"}
