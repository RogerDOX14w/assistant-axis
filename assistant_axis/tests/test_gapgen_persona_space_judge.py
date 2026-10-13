"""Plan 12 § 8, ``judge`` (decision 2b): the pairs, the overlap call through ``NoveltyRunner.run_pairs`` with the
fake responder (every answer recorded before parsing, an unparseable one too; a budget stop raised after
recording), the summary at the candidate's cut-off, refusals counted as failed calls, and the rendered user turn."""
import json

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.persona_space import judge as JDG
from assistant_axis.gapgen.persona_space.compare import Disagreement
from assistant_axis.judge_pricing import BudgetExceededError
from assistant_axis.tests.fake_anthropic import make_response, user_text
from assistant_axis.tests.test_gapgen_novelty import cand, make_runner, responder_for

R3 = NV.DEFAULT_RULES


def dis(key, stem, kind="dup_vs_new"):
    return Disagreement(key=key, kind=kind, m3_decision="new", covered_by=None, m3_listed_first="alpha",
                        persona_nearest=f"{stem}|T", nn_cos=0.8, residual_pct=0.4, evidence="e", judge_stem=stem)


class TestPairs:
    def test_each_dup_vs_new_once_with_the_nearest_trait(self):
        d = [dis("candidate_a#1", "beta"), dis("candidate_a#1", "gamma"), dis("candidate_b#1", "delta"),
             dis("candidate_c#1", "zeta", kind="novel_vs_covered"), dis("candidate_d#1", None)]
        assert JDG.pairs(d) == [("candidate_a#1", "beta", 1), ("candidate_b#1", "delta", 1)]
        assert JDG.pairs([x.as_dict() for x in d]) == JDG.pairs(d)
        assert JDG.pairs(d, kind="novel_vs_covered") == [("candidate_c#1", "zeta", 1)]


OV = {("candidate a", "beta", "sonnet"): 4,                       # cut-off 3: Sonnet above it covers alone
      ("candidate b", "delta", "sonnet"): 2, ("candidate b", "delta", "opus"): 2}     # c - 1: Opus checks, keeps


class TestReadPairs:
    def test_records_every_answer_and_summarises_at_the_cut_off(self, tmp_path):
        r, client, _ = make_runner(tmp_path, responder_for({}, OV, garbage={("candidate c", "zeta", "sonnet")}),
                                   rules=R3)
        cs = [cand("candidate a"), cand("candidate b"), cand("candidate c")]
        pl = [("candidate_a#1", "beta", 1), ("candidate_b#1", "delta", 1), ("candidate_c#1", "zeta", 1)]
        got = JDG.read_pairs(r, cs, pl)
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        assert len(recs) == len(client.calls) == len(r.records)
        garbage = [x for x in recs if x["key"] == "candidate_c#1"]
        assert len(garbage) == 2 and all(x["parse_errors"] for x in garbage)        # asked twice, both recorded
        s = JDG.summarise(got, cs, rules=R3, records=r.records)
        assert (s["candidate_a#1"]["verdict"], s["candidate_a#1"]["at_cut_off"]) == ("cut", True)
        assert (s["candidate_b#1"]["sonnet"], s["candidate_b#1"]["opus"], s["candidate_b#1"]["verdict"]) == (2, 2, "keep")
        assert s["candidate_b#1"]["at_cut_off"] is False and s["candidate_b#1"]["cut_off"] == 3
        assert s["candidate_c#1"]["verdict"] == "unparsed" and not s["candidate_c#1"]["at_cut_off"]
        assert JDG.block_reading(s["candidate_a#1"]) == {"stem": "beta", "sonnet": 4, "opus": None, "verdict": "cut",
                                                         "at_cut_off": True}

    def test_a_budget_stop_is_raised_after_recording(self, tmp_path):
        usage = GuardedUsage(budget_usd=1e-9)
        r, client, _ = make_runner(tmp_path, responder_for({}, OV), usage=usage, rules=R3)
        cs = [cand("candidate a"), cand("candidate b")]
        with pytest.raises(BudgetExceededError):
            JDG.read_pairs(r, cs, [("candidate_a#1", "beta", 1), ("candidate_b#1", "delta", 1)])
        recs = (tmp_path / "out" / "responses.jsonl").read_text().splitlines()
        assert len(recs) == len(client.calls) >= 1 and json.loads(recs[0])["text"]

    def test_refusals_are_failed_calls(self, tmp_path):
        good = responder_for({}, OV)

        def refuse(kw):
            if json.loads(user_text(kw))["target"]["label"] == "candidate b":
                return make_response("", output_tokens=0, stop_reason="refusal")
            return good(kw)
        r, _, _ = make_runner(tmp_path, refuse, rules=R3)
        cs = [cand("candidate a"), cand("candidate b")]
        got = JDG.read_pairs(r, cs, [("candidate_a#1", "beta", 1), ("candidate_b#1", "delta", 1)])
        s = JDG.summarise(got, cs, rules=R3, records=r.records)
        assert s["candidate_b#1"]["verdict"] == "refused" and s["candidate_b#1"]["n_refused"] == 2
        assert not s["candidate_b#1"]["at_cut_off"] and s["candidate_a#1"]["n_refused"] == 0

    def test_missing_candidates_are_refused(self, tmp_path):
        r, _, _ = make_runner(tmp_path, responder_for({}, OV), rules=R3)
        with pytest.raises(KeyError):
            JDG.read_pairs(r, [cand("candidate a")], [("candidate_b#1", "delta", 1)])


class TestRendered:
    def test_the_candidate_is_the_target_and_the_corpus_trait_the_other(self, tmp_path):
        r, client, _ = make_runner(tmp_path, responder_for({}, OV), rules=R3)
        c = cand("achievement-driven", gloss="This means pursuing set goals with steady determination.")
        req = JDG.render(r, c, "beta")
        assert client.calls == []                                       # rendering sends nothing
        assert req["system"][0]["text"] == r.rubrics["overlap"]["text"] and "cache_control" in req["system"][0]
        user = json.loads(req["messages"][0]["content"])
        assert user == {"target": {"label": "achievement-driven",
                                   "description": "This means pursuing set goals with steady determination."},
                        "other": {"label": "beta", "description": "This means being beta in every way."}}
        assert req["model"] == "claude-sonnet-5-5" and "temperature" not in req

    def test_estimate(self):
        e = JDG.estimate(670)
        assert [x.n_calls for x in e.lines] == [670, 268]
        assert 1.0 < e.usd < 3.0
