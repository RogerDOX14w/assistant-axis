"""The switch to Haiku 5.5 (coding_plan_haiku55.md, "The switch", 2026-10-08): the defaults, the verdict
step read several times and combined by Roger's rule (``split.combine_readings``), the readings in the
runner (records, cache keys, the winning reading, the summary), and the estimates from Haiku 5.5's
measured token figures.  No API call: fake clients."""
import json
from collections import Counter
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.gapgen.filter import FilterItem
from assistant_axis.gapgen.split_runner import SplitRunner
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text
from assistant_axis.tests.split_replay import HAIKU, SONNET55, make_responder, step_of_system, synthetic

H55 = "claude-haiku-5-5"


# ---------------------------------------------------------------------------
# the defaults
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_every_haiku_default_of_the_subproject_is_haiku_55(self):
        from assistant_axis.gapgen import calibrate_llm, filter, novelty_runner, plain_reading, states_pass
        assert filter.DEFAULT_MODEL == SR.DEFAULT_MODEL == states_pass.DEFAULT_MODEL == H55
        assert plain_reading.DEFAULT_READING_MODEL == calibrate_llm.PARAPHRASE_MODEL == H55
        assert novelty_runner.RELATION_MODEL == H55

    def test_what_stays(self):
        from assistant_axis.gapgen import novelty_runner as NR
        from assistant_axis.gapgen import overlap_test as OT
        assert NR.UNSURE_MODEL == NR.FIRST_MODEL == SONNET55 and NR.SECOND_MODEL == "claude-opus-5-5"
        assert SR.DEFAULT_SECOND_MODEL == SR.DEFAULT_COMPARE_MODEL == SONNET55
        assert OT.HAIKU == HAIKU and OT.MODELS == (HAIKU, SONNET55, "claude-opus-5-5")   # the overlap test's
        assert H55 in OT.KNOWN_MODELS

    def test_cli_defaults(self):
        from data_analysis.gap_generation import novelty_score, plain_reading, states_pass, traithood_filter
        a = traithood_filter.build_parser().parse_args(["--batch-id", "x", "--unfiltered"])
        assert a.model == H55 and a.readings is None                  # resolved to 3 on Haiku 5.5 by split_cli
        assert novelty_score.build_parser().parse_args(["score", "--batch-id", "x", "--unscored"]).relation_model is None
        src = (plain_reading.__file__, states_pass.__file__, traithood_filter.__file__)
        for p in src:   # the usage strings name the new default
            assert "claude-haiku-4-5" not in open(p, encoding="utf-8").read().split('"""', 2)[1].split("\n\n")[0]

    def test_readings_default_by_model(self):
        assert SR.default_readings(H55) == 3 and SR.default_readings(H55 + "-20261007") == 3
        assert SR.default_readings(HAIKU) == 1 and SR.default_readings(SONNET55) == 1
        assert SplitRunner(client=None, batch_id="t").readings == 3
        assert SplitRunner(client=None, batch_id="t", model=HAIKU).readings == 1
        assert SplitRunner(client=None, batch_id="t", model=HAIKU, readings=3).readings == 3
        for bad in (0, -1, 1.5, True):
            with pytest.raises(ValueError):
                SplitRunner(client=None, batch_id="t", readings=bad)


# ---------------------------------------------------------------------------
# the rule
# ---------------------------------------------------------------------------

T, S, P, R, A = "trait", "states", "physical", "roles", "turned_away"


class TestCombineReadings:
    @pytest.mark.parametrize("outs, outcome, winner, how, rescued", [
        ([T, T, T], T, 0, "unanimous", False),
        ([A, A, A], A, 0, "unanimous", False),                 # turned away: every reading turned it away
        ([T, T, S], T, 0, "most_common", False),
        ([S, T, S], S, 0, "most_common", False),               # majority, not trait-if-any
        ([A, S, S], S, 1, "most_common", True),
        ([T, A, T], T, 0, "most_common", True),                # one reading turned it away: rescued
        ([A, A, T], T, 2, "most_common", True),                # two did: rescued all the same (the rule's rescue)
        ([A, T, A], T, 1, "most_common", True),
        ([A, A, S], S, 2, "most_common", True),                # rescued to the states queue
        ([S, T, P], T, 1, "tie_trait", False),                 # no majority, a reading says trait
        ([A, S, T], T, 2, "tie_trait", True),
        ([P, S, R], P, 0, "tie_first", False),                 # no majority, no trait: the first reading's
        ([A, S, P], S, 1, "tie_first", True),                  # the first reading LEFT: never turned away here
    ])
    def test_three_readings(self, outs, outcome, winner, how, rescued):
        v = split.combine_readings(outs)
        assert (v["outcome"], v["winner"], v["how"], v["rescued"]) == (outcome, winner, how, rescued)
        assert v["unanimous"] == (how == "unanimous") and v["n"] == v["n_ok"] == 3 and v["failed"] == []
        assert v["n_turned_away"] == outs.count(A) and v["outcomes"] == outs
        assert outs[v["winner"]] == v["outcome"]               # the winner is a reading that gave the outcome

    def test_turned_away_only_when_every_reading_says_so(self):
        import itertools
        for outs in itertools.product(split.OUTCOMES, repeat=3):
            v = split.combine_readings(list(outs))
            assert (v["outcome"] == A) == all(o == A for o in outs), outs
            assert v["outcome"] in outs
            if outs.count(T) and v["how"] not in ("unanimous", "most_common"):
                assert v["outcome"] == T, outs

    def test_a_reading_that_failed_is_left_out(self):
        v = split.combine_readings([None, T, A])
        assert (v["outcome"], v["winner"], v["n_ok"], v["failed"], v["rescued"]) == (T, 1, 2, [0], True)
        v = split.combine_readings([A, None, A])               # the readings that answered all turned it away
        assert v["outcome"] == A and v["how"] == "unanimous" and v["unanimous"] is False and v["failed"] == [1]
        v = split.combine_readings([S, None, P])               # two left that differ: the first left
        assert v["outcome"] == S and v["how"] == "tie_first"
        v = split.combine_readings([None, None, None])
        assert v["outcome"] is None and v["winner"] is None and v["failed"] == [0, 1, 2]

    def test_one_and_two_readings(self):
        assert split.combine_readings([A])["outcome"] == A and split.combine_readings([S])["how"] == "unanimous"
        assert split.combine_readings([T, S])["outcome"] == T                  # a tie: trait if any
        assert split.combine_readings([P, S])["outcome"] == P                  # a tie, no trait: the first
        assert split.combine_readings([A, S])["outcome"] == S

    def test_unknown_outcome_refused(self):
        with pytest.raises(ValueError):
            split.combine_readings(["trait", "maybe"])

    def test_summary(self):
        votes = [{**split.combine_readings(o), "label": lab} for lab, o in
                 (("a", [T, T, T]), ("b", [A, A, A]), ("c", [A, A, T]), ("d", [S, T, P]), ("e", [None, T, T]))]
        s = split.readings_summary(votes, n_readings=3)
        assert s["n_words"] == 5 and s["all_the_same"] == 2 and s["rule"] == split.READINGS_RULE
        assert s["by_how"] == {"unanimous": 3, "most_common": 1, "tie_trait": 1, "tie_first": 0}
        assert s["rescued"] == {"n": 1, "by_n_turned_away": {"2": 1}, "labels": ["c"]}
        assert s["turned_away_by_every_reading"] == 1 and s["ties"] == {"n": 1, "labels": ["d"]}
        assert s["differs_from_first_reading"] == {"n": 3, "labels": ["c", "d", "e"]}
        assert s["with_a_failed_reading"] == {"n": 1, "labels": ["e"]}
        assert s["outcomes_by_reading"][0] == {"None": 1, "states": 1, "trait": 1, "turned_away": 2}
        assert s["patterns"]["trait,trait,trait"] == 1


# ---------------------------------------------------------------------------
# the readings in the runner
# ---------------------------------------------------------------------------

KIND_OF = {"trait": "trait", "state": "state", "physical": "physical", "role": "role", "action": "action"}


def reading_responder(plan, *, fail=None, tokens=(800, 300)):
    """Haiku 5.5's answers set reading by reading: step 1 for ``label`` answers one primary reading
    ``"<label> way <n>"``, ``n`` counting that label's step-1 calls on Haiku 5.5 (with concurrency 1 the
    readings are asked in order, so ``n`` is the verdict reading); the kind call on ``way <n>`` answers
    ``plan[label][n - 1]`` (``"stretched"``: the established check says stretched instead).  ``fail``:
    ``{label: {n, ...}}``, step-1 calls answered with text that fails validation.  Everything else (and
    every other model) is synthetic: trait."""
    count = Counter()
    fail = fail or {}

    def override(step, item, kw):
        if kw["model"] != H55:
            return synthetic(step, item)
        label = item.get("label")
        if step == "sense":
            count[label] += 1
            n = count[label]
            if n in fail.get(label, ()):
                return "not json"
            return json.dumps({"results": [{"id": 1, "label": label, "note": "n.", "first_thought": "f",
                                            "first_thought_said_of": "people", "usable": True,
                                            "readings": [{"reading": f"{label} way {n}", "rank": "primary"}]}]})
        n = int(item["reading"].rsplit(" ", 1)[1]) if step in ("established", "kind") else None
        want = plan.get(label, ["trait"] * 9)[n - 1] if n else None
        if step == "established":
            est = "stretched" if want == "stretched" else "well_known"
            return json.dumps({"results": [{"id": 1, "reason": "r.", "established": est,
                                            "first_thought_in_the_way": False}]})
        if step == "kind":
            return json.dumps({"results": [{"id": 1, "reason": "r.", "kind": KIND_OF.get(want, "trait"),
                                            "membership_kind": None}]})
        return synthetic(step, item)
    return make_responder(override=override, tokens=tokens)


PLAN = {
    "alphaw": ["trait", "trait", "trait"],        # unanimous trait
    "betaw": ["action", "action", "stretched"],   # every reading turns it away
    "gammaw": ["action", "trait", "action"],      # two turned it away: rescued, the second reading wins
    "deltaw": ["trait", "stretched", "trait"],    # one turned it away
    "epsw": ["state", "state", "trait"],          # majority: states
    "zetaw": ["state", "trait", "physical"],      # no majority, a trait reading
    "etaw": ["action", "state", "physical"],      # no majority, no trait: the first reading left (2)
}
EXPECT = {"alphaw": ("trait", 1, "unanimous"), "betaw": ("turned_away", 1, "unanimous"),
          "gammaw": ("trait", 2, "most_common"), "deltaw": ("trait", 1, "most_common"),
          "epsw": ("states", 1, "most_common"), "zetaw": ("trait", 2, "tie_trait"),
          "etaw": ("states", 2, "tie_first")}


def items(labels, intended=None):
    return [FilterItem(key=f"{w}#1", label=w, intended_sense=(intended or {}).get(w), meta={"stratum": "s"})
            for w in labels]


def run3(plan=PLAN, *, fail=None, intended=None, resume=None, **kw):
    client = FakeAsyncAnthropic(reading_responder(plan, fail=fail))
    kw.setdefault("second_opinion", False)
    r = SplitRunner(client=client, batch_id="t", wordnet=False, zipf_fn=lambda w: 4.0, retry_delays=(),
                    concurrency=1, usage=MultiModelUsage(), resume_records=resume, **kw)
    res = {x.label: x for x in r.run(items(list(plan), intended))}
    return client, r, res


class TestReadingsInTheRunner:
    def test_each_branch_of_the_rule_on_the_runner(self):
        client, r, res = run3()
        assert r.readings == 3 and r.model == H55
        for label, (outcome, winner, how) in EXPECT.items():
            f = res[label].filter
            assert res[label].stage == "classified" and f["outcome"] == outcome, label
            vr = f["verdict_readings"]
            assert (vr["winner"], vr["how"], vr["n"], vr["rule"]) == (winner, how, 3, split.READINGS_RULE), label
            assert [p["reading"] for p in vr["per_reading"]] == [1, 2, 3]
            assert vr["outcomes"] == [p["outcome"] for p in vr["per_reading"]]
            # the row carries the winning reading's answers
            assert f["sense"]["readings"][0]["reading"] == f"{label} way {winner}"
            if outcome == "trait":
                assert f["judged_sense"] == f"{label} way {winner}" and res[label].gloss
        assert res["gammaw"].filter["verdict_readings"]["rescued"] is True
        assert res["gammaw"].filter["verdict_readings"]["n_turned_away"] == 2
        assert res["alphaw"].filter["verdict_readings"]["unanimous"] is True
        assert res["betaw"].filter["cause"] in ("action", "stretched") and res["betaw"].gloss is None

    def test_the_gloss_alignment_and_descriptors_run_once_on_the_winning_reading(self):
        client, r, res = run3()
        per = Counter()
        for kw in client.calls:
            step = step_of_system(system_text(kw))
            item = json.loads(user_text(kw))
            per[(step, item["label"])] += 1
            if step == "gloss":
                assert item["reading"] == res[item["label"]].filter["judged_sense"]
        traits = [w for w, x in res.items() if x.filter["outcome"] == "trait"]
        for w in PLAN:
            assert per[("sense", w)] == 3 and per[("kind", w)] == 3 and per[("established", w)] == 3
            n = 1 if w in traits else 0
            assert per[("gloss", w)] == per[("alignment", w)] == per[("descriptors", w)] == n, w

    def test_every_reading_recorded_with_its_number_and_its_own_custom_id(self):
        _, r, _ = run3()
        recs = r.responses
        for rec in recs:
            if rec["step"] in SR.VERDICT_STEPS:
                assert rec["verdict_reading"] in (1, 2, 3)
            else:
                assert rec["verdict_reading"] is None
        by = Counter((rec["keys"][0], rec["step"], rec["verdict_reading"]) for rec in recs if rec["step"] == "sense")
        assert set(by.values()) == {1} and len(by) == 3 * len(PLAN)
        for stage in {rec["stage"] for rec in recs}:
            ids = [rec["custom_id"] for rec in recs if rec["stage"] == stage]
            assert len(ids) == len(set(ids)), stage          # a Message Batch takes no duplicate
        assert any("-f2-" in rec["custom_id"] for rec in recs) and any("-f3-" in rec["custom_id"] for rec in recs)

    def test_resume_finds_each_readings_own_answer(self):
        """The readings send the same request: the cache key carries the reading, so a resume replays
        reading 2's answer for reading 2 (with one key for all three, gammaw would come back unanimous)."""
        _, r1, res1 = run3()
        client2, r2, res2 = run3(resume=list(r1.responses))
        assert client2.calls == []
        for w in PLAN:
            assert res2[w].filter["outcome"] == res1[w].filter["outcome"]
            assert res2[w].filter["verdict_readings"]["outcomes"] == res1[w].filter["verdict_readings"]["outcomes"]

    def test_a_reading_that_fails_twice_is_left_out_of_the_vote(self):
        plan = {"iotaw": ["trait", "action", "action"], "kappaw": ["trait", "trait", "trait"], "lambdaw": ["trait"] * 3}
        # iotaw: reading 1's step 1 fails, then its retry (the 4th step-1 call); kappaw: every reading fails twice
        _, r, res = run3(plan, fail={"iotaw": {1, 4}, "kappaw": {1, 2, 3, 4, 5, 6}})
        f = res["iotaw"].filter
        vr = f["verdict_readings"]
        assert f["outcome"] == "turned_away" and vr["failed"] == [1] and vr["unanimous"] is False
        assert vr["per_reading"][0]["reading"] == 1 and "error" in vr["per_reading"][0]
        assert res["kappaw"].stage == "failed" and "verdict reading 3" in res["kappaw"].error
        assert res["lambdaw"].filter["outcome"] == "trait"
        s = r.readings_summary()
        assert s["with_a_failed_reading"] == {"n": 1, "labels": ["iotaw"]} and s["n_words"] == 2

    def test_the_summary_of_the_readings(self):
        _, r, _ = run3()
        s = r.readings_summary()
        assert s["n_readings"] == 3 and s["n_words"] == len(PLAN)
        assert s["all_the_same"] == 2                                   # alphaw, and betaw (turned away)
        assert s["turned_away_by_every_reading"] == 1
        assert s["rescued"]["labels"] == ["deltaw", "etaw", "gammaw"]
        assert s["rescued"]["by_n_turned_away"] == {"1": 2, "2": 1}
        assert s["ties"]["labels"] == ["etaw", "zetaw"]

    def test_the_second_opinion_compares_the_combined_outcome(self):
        _, r, res = run3(second_opinion=True, second_opinion_frac=1.0, max_disagreement=None)
        assert set(r.second_keys) == {f"{w}#1" for w in PLAN}
        for w, x in res.items():
            so = x.filter["second_opinion"]
            assert so["model"] == SONNET55 and so["outcome"] == "trait"        # synthetic: trait on Sonnet
            assert so["agree"] == (x.filter["outcome"] == "trait"), w
        rows = {row["label"]: row for row in r.opinion_rows()}
        assert rows["gammaw"]["first"] == "trait" and rows["betaw"]["first"] == "turned_away"

    def test_the_comparison_asks_about_the_winning_reading_only(self):
        hint = {"gammaw": "the intended meaning"}
        client, r, res = run3({"gammaw": PLAN["gammaw"]}, intended=hint)
        cmp = [kw for kw in client.calls if step_of_system(system_text(kw)) == "comparison"]
        assert len(cmp) == 1 and "gammaw way 2" in user_text(cmp[0]) and cmp[0]["model"] == SONNET55
        rec = next(x for x in r.responses if x["step"] == "comparison")
        assert rec["verdict_reading"] == 2
        f = res["gammaw"].filter
        assert f["comparison"]["per_reading"][0]["reading_index"] == 1 and f["comparison"]["effect"] == "same"

    def test_one_reading_is_the_one_reading_run_it_always_was(self):
        client, r, res = run3({"alphaw": ["trait"], "betaw": ["action"]}, readings=1)
        assert r.readings == 1
        for x in res.values():
            assert "verdict_readings" not in x.filter
        assert all("verdict_reading" not in rec for rec in r.responses)
        assert not any("-f2-" in rec["custom_id"] or "-f1-" in rec["custom_id"] for rec in r.responses)
        assert Counter(step_of_system(system_text(kw)) for kw in client.calls)["sense"] == 2
        assert r.readings_summary()["n_readings"] == 1

    def test_every_haiku_55_request_leaves_out_the_sampling_settings(self):
        client, _, _ = run3()
        for kw in client.calls:
            if kw["model"] == H55:
                assert not {"temperature", "top_p", "top_k", "thinking"} & set(kw) and kw["max_tokens"] == 2000


# ---------------------------------------------------------------------------
# the estimates
# ---------------------------------------------------------------------------

class TestEstimates:
    def test_haiku_55_has_its_measured_figures(self):
        for step, fig in SR.HAIKU55_TOKENS.items():
            assert SR.tokens_for(step, H55) == fig
            assert SR.tokens_for(step, H55, first_model=HAIKU) == fig      # as a second model too
        assert SR.tokens_for("sense", HAIKU) == SR.HAIKU_TOKENS["sense"]   # Haiku 4.5 keeps its own
        assert SR.tokens_for("sense", HAIKU, first_model=HAIKU) == (567, 207)
        assert SR.tokens_for("kind", SONNET55) == (955, 59)
        assert SR.tokens_for("sense", "claude-opus-5-5") == (850, 310)
        # output includes the thinking: two to four times Haiku 4.5's on the verdict steps
        for step in ("sense", "established", "same_sense"):
            assert SR.HAIKU55_TOKENS[step][1] > 1.5 * SR.HAIKU_TOKENS[step][1]
        assert "measured" in SR.token_source(H55) and "Haiku 4.5's measured" in SR.token_source(HAIKU, HAIKU)

    def _args(self, model, readings, **kw):
        return SimpleNamespace(model=model, readings=readings, second_model=SONNET55, no_probe=False,
                               no_plain_reading=False, compare_model=SONNET55, no_second_opinion=False,
                               second_opinion_frac=0.10, third_model=None, **kw)

    def test_the_split_estimate_counts_each_reading_and_quotes_each_models_figures(self):
        from data_analysis.gap_generation import split_cli
        its = items(["brave", "calm", "kind", "loyal", "proud", "rude", "shy", "timid", "vain", "witty"])
        e3, p3 = split_cli.build_split_estimate(its, self._args(H55, 3), "live")
        e1, p1 = split_cli.build_split_estimate(its, self._args(H55, 1), "live")
        by3 = {x.label: x for x in e3.lines}
        by1 = {x.label: x for x in e1.lines}
        assert by3["sense (3 readings)"].n_calls == 3 * by1["sense"].n_calls == 30
        assert (by3["sense (3 readings)"].in_tok, by3["sense (3 readings)"].out_tok) == SR.HAIKU55_TOKENS["sense"]
        assert by3["kind (3 readings)"].n_calls == 3 * by1["kind"].n_calls
        assert by3["gloss"].n_calls == by1["gloss"].n_calls and by3["alignment"].n_calls == by1["alignment"].n_calls
        assert p3["readings"] == 3 and "measured" in p3["token_figures"][H55]
        assert set(p3["token_figures"]) == {H55, SONNET55}
        e45, _ = split_cli.build_split_estimate(its, self._args(HAIKU, 1), "live")
        s45 = next(x for x in e45.lines if x.label == "sense")
        assert (s45.model, s45.in_tok, s45.out_tok) == (HAIKU, 567, 207)
        # per word, the first model's steps: three Haiku 5.5 readings about $0.0036 (the readout), under 4.5's
        first3 = sum(x.usd for x in e3.lines if x.model == H55) / 10
        first45 = sum(x.usd for x in e45.lines if x.model == HAIKU) / 10
        assert 0.002 < first3 < 0.0045 and first3 < first45

    def test_the_relation_call_estimate_on_haiku_55(self):
        from assistant_axis.gapgen import novelty_runner as NR
        assert NR.relation_out_tokens(H55, 17.2) == round(76.5 * 17.2)
        assert NR.relation_out_tokens(HAIKU, 10) == 20 + 45 * 10                  # no factor, no measurement
        assert NR.relation_out_tokens(SONNET55, 10) == round((20 + 45 * 10) * 1.3)
        st = NR.plan_estimate(n_candidates=100, n_scan=0, mean_listed=17.2, relation_text_chars=1343,
                              trait_chars=260.0, cand_chars=140.0)
        line = st["relation"].lines[0]
        assert line.model == H55 and line.out_tok == round(76.5 * 17.2) and line.n_calls == 100
        # within 10% of what m3_pilot_1_relation_h55 measured a call (1,316 out at 17.2 listed)
        assert abs(line.out_tok - 1316) / 1316 < 0.1
        c = NR.Call(step="relation", role="haiku", key="k", model=H55, system="x" * 1343, user="y" * 4033,
                    max_tokens=4096, temperature=None, stems=tuple(f"s{i}" for i in range(17)))
        assert NR.call_tokens(c)[1] == round(76.5 * 17)


# ---------------------------------------------------------------------------
# the plain reading on a model that thinks
# ---------------------------------------------------------------------------

def test_the_plain_reading_gives_a_thinking_model_room():
    import asyncio
    from assistant_axis.gapgen import plain_reading as pr
    assert pr.reading_max_tokens(H55) == pr.READING_MAX_TOKENS_THINKING == 2000
    assert pr.reading_max_tokens(HAIKU) == pr.READING_MAX_TOKENS == 120
    for model, want in ((H55, 2000), (HAIKU, 120)):
        client = FakeAsyncAnthropic(lambda kw: "A persona that argues.")
        r = pr.PlainReadingRunner(client=client, batch_id="t", reading_model=model, retry_delays=())
        r._sem = asyncio.Semaphore(1)
        asyncio.run(r._read("argumentative", ["argumentative#1"]))
        kw = client.calls[0]
        assert kw["max_tokens"] == want and kw["model"] == model
        assert ("temperature" in kw) == (model == HAIKU)
