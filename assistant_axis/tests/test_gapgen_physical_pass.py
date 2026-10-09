"""The physical pass (QUESTIONS 1, Roger 2026-10-09: physical candidates are promoted normally, in a separate pass,
and carry the ``physical`` tag): M3's candidate builder for rows on the ``physical`` holding list, the gloss stage
(M1's own gloss and alignment calls on the accepted reading, since the split filter writes neither for a physical
row), and the seed-queue section of the physical track.  No API calls: a fake Anthropic client."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import physical_pass as PP
from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.registry import new_record
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

REPO = Path(__file__).resolve().parents[2]
READING = "has large, well-developed muscles"
GLOSS = "This means having large, well-developed muscles that show through one's sleeves."


def physical_row(surface="muscular", *, reading=READING, block=None, gen="censuses"):
    r = new_record(surface, sources=[{"generator": gen, "run_id": "2026-10-08-pilot", "rank": 1, "score": None,
                                      "source_ref": None, "gloss_hint": None, "partner_hint": None, "surface": surface}])
    r["filter"] = {"pipeline": "split", "verdict": "tagged", "outcome": "physical", "tags": ["physical"],
                   "judged_sense": reading, "accepted_reading": 1,
                   "sense": {"readings": [{"reading": reading, "rank": "primary"}]}, "alignment": None, "region": None}
    r["gloss"] = None
    r["holding"] = "physical"
    r["entity_type"] = "trait"
    if block is not None:
        r[PP.BLOCK] = block
    return r


def trait_row(surface="plucky"):
    r = new_record(surface)
    r["filter"] = {"verdict": "trait", "outcome": "trait", "tags": [], "alignment": 1, "region": "moral_stance"}
    r["gloss"] = f"This means being {surface}."
    r["holding"] = None
    return r


# --------------------------------------------------------------------------- the candidate builder

class TestCandidate:
    def test_the_default_builder_still_refuses_a_physical_row(self):
        row = physical_row(block={"gloss": GLOSS, "alignment": 0})
        assert NR.candidate_from_row(row) == (None, "not_a_trait")

    def test_the_physical_builder_reads_the_gloss_and_alignment_of_the_block(self):
        row = physical_row(block={"gloss": GLOSS, "alignment": 0})
        c, why = NR.candidate_from_row(row, holding="physical")
        assert why is None and c.key == "muscular#1" and c.label == "muscular" and c.gloss == GLOSS
        assert c.alignment_score == 0 and c.cut_off == 3 and c.region is None and c.generators == ["censuses"]

    def test_a_missing_alignment_takes_the_near_alignment_cut_off(self):
        c, _ = NR.candidate_from_row(physical_row(block={"gloss": GLOSS, "alignment": None}), holding="physical")
        assert c.alignment_score is None and c.cut_off == 4

    def test_refusals(self):
        assert NR.candidate_from_row(physical_row(), holding="physical") == (None, "no_gloss")
        assert NR.candidate_from_row(physical_row(block={"gloss": None, "errors": {"gloss": "x"}}),
                                     holding="physical") == (None, "no_gloss")
        assert NR.candidate_from_row(trait_row(), holding="physical") == (None, "not_on_physical_list")
        r = physical_row(block={"gloss": GLOSS, "alignment": 0})
        r["filter"] = None
        assert NR.candidate_from_row(r, holding="physical") == (None, "not_filtered")
        with pytest.raises(ValueError):
            NR.candidate_from_row(physical_row(), holding="roles")

    def test_the_trait_builder_is_unchanged_for_trait_rows(self):
        c, why = NR.candidate_from_row(trait_row())
        assert why is None and c.gloss == "This means being plucky." and c.alignment_score == 1

    def test_accepted_reading(self):
        assert PP.accepted_reading(physical_row()) == READING
        r = physical_row()
        r["filter"]["judged_sense"] = None
        assert PP.accepted_reading(r) == READING                       # from the sense block's accepted reading
        r["filter"]["sense"] = None
        assert PP.accepted_reading(r) is None

    def test_gloss_of(self):
        assert PP.gloss_of(physical_row(block={"gloss": GLOSS})) == GLOSS
        assert PP.gloss_of(physical_row()) is None
        assert PP.gloss_of(trait_row()) == "This means being plucky."


# --------------------------------------------------------------------------- the requests are M1's

class TestRequests:
    def test_the_gloss_request_is_m1s(self):
        q = PP.request("gloss", label="muscular", text=READING)
        sys_ = sr.load_prompt("gloss")
        assert q["system"] == sys_ and q["model"] == SR.DEFAULT_MODEL == PP.MODEL
        assert q["user"] == split.payload("gloss", label="muscular", reading=READING)
        assert q["max_tokens"] == SR.SplitRunner._max_tokens(None, "gloss", PP.MODEL)
        assert q["temperature"] == SR.TEMPERATURE and q["cache_system"] == SR.caches_system(sys_, PP.MODEL)

    def test_the_alignment_request_is_m1s_on_the_gloss(self):
        q = PP.request("alignment", label="muscular", text=GLOSS)
        assert q["system"] == sr.load_prompt("alignment")
        assert q["user"] == split.payload("alignment", label="muscular", description=GLOSS)
        assert q["max_tokens"] == SR.SplitRunner._max_tokens(None, "alignment", PP.MODEL)

    def test_the_estimate_uses_m1s_measured_tokens(self):
        est = PP.estimate(3)
        assert [x.n_calls for x in est.lines] == [3, 3]
        assert (est.lines[0].in_tok, est.lines[0].out_tok) == SR.tokens_for("gloss", PP.MODEL)
        assert (est.lines[1].in_tok, est.lines[1].out_tok) == SR.tokens_for("alignment", PP.MODEL)
        assert est.usd > 0 and PP.estimate(0).lines == []

    def test_render_shows_both_requests(self):
        txt = PP.render(physical_row())
        assert "gloss v" in txt and split.payload("gloss", label="muscular", reading=READING) in txt
        assert "alignment v" in txt


# --------------------------------------------------------------------------- the gloss stage

def responder(*, bad_gloss=(), bad_gloss_once=(), bad_alignment=(), alignment=0):
    seen = {}
    gloss_sys, align_sys = sr.load_prompt("gloss"), sr.load_prompt("alignment")

    def answer(kw):
        s, obj = system_text(kw), json.loads(user_text(kw))
        label = obj["label"]
        if s == gloss_sys:
            seen[label] = seen.get(label, 0) + 1
            if label in bad_gloss or (label in bad_gloss_once and seen[label] == 1):
                return make_response("no", input_tokens=600, output_tokens=5)
            return make_response(json.dumps({"results": [{"id": 1, "gloss": f"This means having {obj['reading']}."}]}),
                                 input_tokens=650, output_tokens=90)
        assert s == align_sys and obj["description"].startswith("This means having ")
        if label in bad_alignment:
            return make_response("{}", input_tokens=700, output_tokens=5)
        return make_response(json.dumps({"results": [{"id": 1, "reason": "A body, not conduct.", "alignment": alignment}]}),
                             input_tokens=780, output_tokens=170)
    return answer


def run(rows, client, tmp_path, usage=None, **kw):
    got = {}
    blocks = PP.run_gloss_rows(rows, client=client, usage=usage if usage is not None else MultiModelUsage(),
                               batch_id="phys_t", records_path=tmp_path / "physical_gloss_responses.jsonl",
                               on_block=lambda key, b: got.__setitem__(key, b), retry_delays=(), **kw)
    return blocks, got


class TestGlossStage:
    def test_gloss_then_alignment_on_the_gloss(self, tmp_path):
        rows = [physical_row("muscular"), physical_row("thin", reading="has little flesh on the bones")]
        client = FakeAsyncAnthropic(responder())
        usage = MultiModelUsage()
        blocks, got = run(rows, client, tmp_path, usage)
        assert got == blocks and set(blocks) == {"muscular#1", "thin#1"}
        b = blocks["thin#1"]
        assert b["gloss"] == "This means having has little flesh on the bones." and b["alignment"] == 0
        assert b["reading"] == "has little flesh on the bones" and b["model"] == PP.MODEL and b["batch_id"] == "phys_t"
        assert b["alignment_reason"] == "A body, not conduct." and "errors" not in b
        assert b["step_versions"] == {"gloss": sr.current_versions(names=("gloss",))["gloss"][0],
                                      "alignment": sr.current_versions(names=("alignment",))["alignment"][0]}
        assert b["prompt_sha256"]["gloss"] == sr.sha256(sr.load_prompt("gloss")) and b["gloss_form_ok"] is True
        assert len(client.calls) == 4 and usage.n_calls == 4 and usage.total_cost_usd > 0
        recs = [json.loads(x) for x in (tmp_path / "physical_gloss_responses.jsonl").read_text().splitlines()]
        assert sorted((r["key"], r["step"]) for r in recs) == [("muscular#1", "alignment"), ("muscular#1", "gloss"),
                                                               ("thin#1", "alignment"), ("thin#1", "gloss")]
        assert all(r["stage"] == "physical_gloss" and r["text"] and r["usage_raw"] and r["charged_as"] == PP.MODEL
                   for r in recs)

    def test_a_failed_gloss_is_retried_once_then_reported(self, tmp_path):
        rows = [physical_row("muscular"), physical_row("thin", reading="has little flesh on the bones")]
        client = FakeAsyncAnthropic(responder(bad_gloss_once=("muscular",), bad_gloss=("thin",)))
        blocks, _ = run(rows, client, tmp_path)
        assert blocks["muscular#1"]["gloss"].startswith("This means having") and "errors" not in blocks["muscular#1"]
        assert blocks["thin#1"]["gloss"] is None and blocks["thin#1"]["alignment"] is None
        assert "gloss" in blocks["thin#1"]["errors"]
        # muscular: two gloss calls and one alignment; thin: two gloss calls and none
        assert len(client.calls) == 5

    def test_an_alignment_failure_keeps_the_gloss_with_no_score(self, tmp_path):
        blocks, _ = run([physical_row()], FakeAsyncAnthropic(responder(bad_alignment=("muscular",))), tmp_path)
        b = blocks["muscular#1"]
        assert b["gloss"] and b["alignment"] is None and "alignment" in b["errors"]
        c, _ = NR.candidate_from_row(physical_row(block=b), holding="physical")
        assert c.cut_off == 4                                      # as M1 leaves a trait row whose alignment failed

    def test_a_row_with_no_reading_is_not_sent(self, tmp_path):
        r = physical_row()
        r["filter"]["judged_sense"] = None
        r["filter"]["sense"] = None
        client = FakeAsyncAnthropic(responder())
        blocks, _ = run([r], client, tmp_path)
        assert client.calls == [] and blocks["muscular#1"]["errors"] == {"gloss": "no accepted reading"}

    def test_a_budget_stop_keeps_the_blocks_already_finished(self, tmp_path):
        rows = [physical_row("muscular"), physical_row("thin", reading="has little flesh on the bones")]
        usage = GuardedUsage(budget_usd=1e-9)
        got = {}
        with pytest.raises(BudgetExceededError):
            PP.run_gloss_rows(rows, client=FakeAsyncAnthropic(responder()), usage=usage, batch_id="phys_t",
                              records_path=tmp_path / "r.jsonl", on_block=lambda k, b: got.__setitem__(k, b),
                              retry_delays=(), concurrency=1)
        recs = [json.loads(x) for x in (tmp_path / "r.jsonl").read_text().splitlines()]
        assert len(recs) == 1 and recs[0]["text"]                  # the call that crossed the cap is recorded
        assert got == {}                                           # no row finished; nothing written for it


# --------------------------------------------------------------------------- the physical track's section

class TestSection:
    def test_the_section_is_read_from_the_queues_physical_track(self):
        q = {"entries": [{"stem": "a", "tags": ["physical"], "section": "Track X"},
                         {"stem": "b", "tags": ["gap_gen"], "section": "other"}]}
        assert PP.section_for(q) == "Track X"
        assert PP.section_for({"entries": []}) == PP.SECTION

    def test_the_constant_is_the_real_queues_section(self):
        q = json.loads((REPO / "data" / "seed_queue.json").read_text(encoding="utf-8"))
        assert PP.section_for(q) == PP.SECTION
        blond = next(e for e in q["entries"] if e["stem"] == "blond")
        assert blond["section"] == PP.SECTION and "physical" in blond["tags"]


# --------------------------------------------------------------------------- R1 reads a physical batch

class TestReviewGraph:
    def test_a_physical_row_of_a_physical_batch_is_a_pair_candidate(self):
        from assistant_axis.gapgen import review_graph as RG
        row = physical_row(block={"gloss": GLOSS, "alignment": 0})
        row["novelty"] = {"run_id": "phys1", "pass": "physical", "decision": "new"}
        c, why = RG.pair_candidate(row)
        assert why is None and c.gloss == GLOSS and c.cut_off == 4             # R1 reads every pair at cut-off 4
        row["novelty"] = {"run_id": "m3b", "decision": "new"}                   # not a physical pass's block
        assert RG.pair_candidate(row) == (None, "not_a_trait")

    def test_the_node_says_physical_and_a_trait_node_is_unchanged(self):
        from assistant_axis.gapgen import review_graph as RG
        row = physical_row(block={"gloss": GLOSS, "alignment": 0})
        row["novelty"] = {"run_id": "phys1", "pass": "physical", "decision": "new", "alignment_score": 0}
        n = RG._candidate_node(row)
        assert n.outcome == "physical" and n.gloss == GLOSS and n.verdict == "tagged" and n.alignment_score == 0
        assert n.to_dict()["outcome"] == "physical" and RG.Node.from_dict(n.to_dict()) == n
        t = trait_row()
        t["novelty"] = {"run_id": "m3b", "decision": "new"}
        nt = RG._candidate_node(t)
        assert nt.outcome is None and "outcome" not in nt.to_dict()            # graph.json of a trait batch unchanged


def test_run_gloss_rows_closes_its_client_inside_the_loop(tmp_path):
    """2026-10-09: an AsyncAnthropic left open was closed after the event loop ended ("Event loop is closed")."""
    closed = []

    class Closing:
        async def close(self):
            closed.append(True)

    PP.run_gloss_rows([], client=Closing(), usage=MultiModelUsage(), batch_id="phys_close",
                      records_path=tmp_path / "r.jsonl")
    assert closed == [True]
