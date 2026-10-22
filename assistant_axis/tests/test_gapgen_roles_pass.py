"""The roles pass's stage and candidate builder (coding plan 16, task 4 and test 4): which rows are role rows, the
role gloss and role kind requests as pinned, the stage on a fake client (three kind readings combined by majority,
a failed gloss recorded, a budget stop keeping what was paid for, a resume paying for nothing twice, the Batches
transport), the flat cut-off of 3, and the estimate.  No API calls."""
import hashlib
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic
from assistant_axis.tests.roles_fakes import aimed_row, gloss_for, held_row, stage_responder, trait_row

REPO = Path(__file__).resolve().parents[2]
BOUNCER = "works as a club or bar doorman who checks entry and removes troublemakers"


def h16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- rows

class TestRows:
    def test_the_three_shapes(self):
        assert RP.is_role_row(held_row("baker", "bakes bread"))                       # held plain key
        assert RP.is_role_row(aimed_row("bouncer", BOUNCER, route="role"))           # role-aimed |R
        assert RP.is_role_row(aimed_row("optimist", "expects the best", route="both"))
        assert not RP.is_role_row(aimed_row("catholic", "a Catholic", route="membership"))
        assert not RP.is_role_row(aimed_row("captive", "held prisoner", route="turned_away"))
        assert not RP.is_role_row(trait_row())

    def test_route_for(self):
        assert {k: RP.route_for(k, entity_type="role") for k in split.KINDS} == {
            "trait": "both", "membership": "membership", "state": "turned_away", "physical": "turned_away",
            "role": "role", "action": "turned_away", "evaluative": "turned_away", "not_a_persona": "turned_away"}
        assert RP.route_for(None, entity_type="role") == "turned_away"
        assert RP.route_for("role", entity_type="trait") is None
        assert set(RP.ROLE_ROUTES) == set(split.KINDS)

    def test_kinds_are_the_classifiers(self):
        import data_analysis.classify_role_kinds as CRK
        assert RP.KINDS is CRK.KINDS and RP.KIND_KEYS == CRK.KIND_KEYS and len(RP.KIND_KEYS) == 9

    def test_candidate_reasons(self):
        r = held_row("baker", "bakes bread")
        assert RP.candidate_from_row(r) == (None, "no_gloss")
        r[RP.BLOCK] = {"gloss": "A baker is someone who bakes bread before dawn.", "kind": "occupation"}
        c, why = RP.candidate_from_row(r)
        assert why is None and isinstance(c, RP.RoleCandidate) and c.gloss.startswith("A baker")
        assert c.alignment_score is None and c.region is None and c.generators == ["censuses"]
        assert RP.candidate_from_row(trait_row()) == (None, "not_a_role_row")
        r["filter"] = None
        assert RP.candidate_from_row(r) == (None, "not_filtered")

    @pytest.mark.parametrize("version", sorted(NV.RULES))
    def test_the_cut_off_is_three_under_every_rule_set(self, version):
        c = RP.RoleCandidate(key="x|R#1", stem="x", label="x", gloss="A x is.", alignment_score=None, region=None)
        assert c.cut_off == 3 and c.cut_off_spec(NV.RULES[version]).c == 3
        assert c.cut_off_spec(NV.RULES[version]).opus_check and c.cut_off_spec(NV.RULES[version]).sonnet_alone

    def test_the_m3_builder_hands_roles_to_the_pass_and_refuses_a_role_row_in_a_trait_run(self):
        r = aimed_row("bouncer", BOUNCER)
        r[RP.BLOCK] = {"gloss": gloss_for("bouncer", BOUNCER), "kind": "occupation"}
        c, why = NR.candidate_from_row(r, holding="roles")
        assert why is None and isinstance(c, RP.RoleCandidate) and c.key == "bouncer|R#1"
        assert NR.candidate_from_row(r) == (None, "not_a_trait_row")
        r2 = held_row("baker", "bakes bread")                                      # a held row: verdict tagged
        assert NR.candidate_from_row(r2) == (None, "not_a_trait")

    def test_readers(self):
        r = aimed_row("robot", "a machine", kind_guess="non_human")
        assert RP.kind_guess_of(r) == "non_human" and RP.kind_of(r) is None and RP.human_of(r) is None
        assert RP.needs_stage(r)
        r[RP.BLOCK] = {"gloss": "A robot is a machine that ...", "kind": "non_human"}
        assert RP.kind_of(r) == "non_human" and RP.human_of(r) is False and not RP.needs_stage(r)
        r[RP.BLOCK]["kind"] = None
        assert RP.needs_stage(r)                                                    # glossed, kind failed

    def test_the_gloss_form_and_the_opening(self):
        assert RP.role_gloss_form_ok("A bouncer is someone who works the door.", "bouncer")
        assert RP.role_gloss_form_ok("An operator is someone who runs a boiler.", "operator")
        assert RP.role_gloss_form_ok("A devil's advocate is someone who argues.", "devil's advocate")
        assert RP.role_gloss_form_ok("A police officer is someone who patrols.", "police officer")
        assert not RP.role_gloss_form_ok("Someone who works the door.", "bouncer")
        assert RP.strip_opening("A bouncer is someone who works the door.", "bouncer") == \
            ("Someone who works the door.", True)
        assert RP.strip_opening("Works the door.", "bouncer") == ("Works the door.", False)


# --------------------------------------------------------------------------- requests

class TestRequests:
    def test_the_role_gloss_request(self):
        q = RP.request("role_gloss", label="bouncer", reading=BOUNCER)
        assert q["system"] == sr.load_prompt("role_gloss") and q["model"] == RP.MODEL == SR.DEFAULT_MODEL
        assert q["user"] == split.payload("gloss", label="bouncer", reading=BOUNCER)
        assert q["max_tokens"] == SR.MAX_TOKENS_THINKING and q["cache_system"] == SR.caches_system(q["system"], RP.MODEL)
        # the renderings of rubrics/role_gloss.md (variants 1 and 3), byte for byte
        assert h16(q["user"]) == "223112cb0457b6d5"
        assert h16(RP.request("role_gloss", label="operator", reading=None)["user"]) == "1e0f376eab51bfaa"
        assert json.loads(RP.request("role_gloss", label="operator", reading=None)["user"]) == \
            {"id": 1, "label": "operator", "reading": None}

    def test_the_role_kind_request_is_the_classifiers(self):
        import data_analysis.classify_role_kinds as CRK
        desc = json.loads((REPO / "data/roles/instructions/operator.json").read_text())["description"]
        q = RP.request("role_kind", label="operator", gloss=desc)
        assert q["system"] == CRK.SYSTEM == sr.load_prompt("role_kind")
        assert q["user"] == CRK.user_message("operator", desc) and q["max_tokens"] == CRK.MAX_TOKENS
        assert q["temperature"] is None
        assert h16(q["user"]) == "45b80d2d29efb6c3"                                    # rubrics/role_kind.md
        with pytest.raises(ValueError):
            RP.request("role_kind", label="operator")
        with pytest.raises(ValueError):
            RP.request("gloss", label="operator")

    def test_labels_are_shown_in_the_judge_display_form(self):
        q = RP.request("role_kind", label="devils_advocate", gloss="A devil's advocate is someone who argues.")
        assert q["user"].startswith("Role: devils advocate\n")
        q = RP.request("role_gloss", label="careless (HEXACO)", reading="x")
        assert json.loads(q["user"])["label"] == "careless (from HEXACO)"

    def test_pins_and_a_changed_text(self, tmp_path):
        p = RP.pins()
        assert p["step_versions"] == {"role_gloss": 1, "role_kind": 1}
        assert p["prompt_sha256"]["role_kind"].startswith("11b559f0cff50189")
        import shutil
        d = tmp_path / "rubrics"
        shutil.copytree(sr.RUBRICS_DIR, d)
        f = d / "role_gloss.md"
        f.write_text(f.read_text().replace("US spelling.", "UK spelling."))
        with pytest.raises(ValueError, match="role_gloss"):
            RP.pins(d)

    def test_estimate_counts_four_calls_a_row(self):
        est = RP.estimate(10)
        assert [x.n_calls for x in est.lines] == [10, 30]
        assert est.usd > 0 and RP.estimate(10, batch=True).usd == pytest.approx(est.usd / 2)
        assert [x.n_calls for x in RP.estimate(2, n_kind_only=3).lines] == [2, 15]
        assert RP.estimate(0).lines == []

    def test_render_shows_both_requests(self):
        txt = RP.render(held_row("bouncer", BOUNCER))
        assert "role_gloss v1" in txt and split.payload("gloss", label="bouncer", reading=BOUNCER) in txt
        assert "role_kind v1" in txt and "Role: bouncer\nDescription: <the role gloss>" in txt


# --------------------------------------------------------------------------- the stage

def run(rows, client, tmp_path, usage=None, **kw):
    got = {}
    blocks = RP.run_stage_rows(rows, client=client, usage=usage if usage is not None else MultiModelUsage(),
                               batch_id="roles_t", records_path=tmp_path / RP.RESPONSES_NAME,
                               on_block=lambda k, b: got.__setitem__(k, b), retry_delays=(), **kw)
    return blocks, got


def records(tmp_path):
    return [json.loads(x) for x in (tmp_path / RP.RESPONSES_NAME).read_text().splitlines()]


class TestStage:
    def test_gloss_then_three_kind_readings_by_majority(self, tmp_path):
        rows = [held_row("bouncer", BOUNCER), aimed_row("optimist", "expects the best", route="both"),
                held_row("selkie", "a seal that sheds its skin")]
        client = FakeAsyncAnthropic(stage_responder(kinds={"optimist": ["temperament", "stance", "temperament"],
                                                           "selkie": ["non_human", "other", "stance"]}))
        usage = MultiModelUsage()
        blocks, got = run(rows, client, tmp_path, usage)
        assert got == blocks and set(blocks) == {"bouncer#1", "optimist|R#1", "selkie#1"}
        b = blocks["bouncer#1"]
        assert b["gloss"] == gloss_for("bouncer", BOUNCER) and b["gloss_form_ok"] is True and b["reading"] == BOUNCER
        assert b["kind"] == "occupation" and b["kind_unanimous"] is True and b["kind_split"] is False
        assert b["human"] is True and len(b["kind_readings"]) == 3 and b["model"] == RP.MODEL
        assert b["step_versions"] == {"role_gloss": 1, "role_kind": 1} and b["batch_id"] == "roles_t"
        assert b["prompt_sha256"]["role_kind"].startswith("11b559f0cff50189") and "errors" not in b
        o = blocks["optimist|R#1"]
        assert o["kind"] == "temperament" and o["kind_unanimous"] is False and o["kind_split"] is False
        s = blocks["selkie#1"]
        assert s["kind"] == "non_human" and s["kind_split"] is True and s["human"] is False   # a tie keeps the first
        assert len(client.calls) == 3 + 9 and usage.n_calls == 12
        recs = records(tmp_path)
        assert len(recs) == 12 and {r["step"] for r in recs} == {"role_gloss", "role_kind"}
        assert all(r["stage"] == "role_pass" and r["text"] and r["charged_as"] == RP.MODEL for r in recs)
        assert sorted(r["reading"] for r in recs if r["key"] == "selkie#1" and r["step"] == "role_kind") == [0, 1, 2]

    def test_a_failed_gloss_is_asked_once_more_then_recorded(self, tmp_path):
        rows = [held_row("bouncer", BOUNCER), held_row("baker", "bakes bread")]
        client = FakeAsyncAnthropic(stage_responder(bad_gloss_once=("bouncer",), bad_gloss=("baker",)))
        blocks, _ = run(rows, client, tmp_path)
        assert blocks["bouncer#1"]["gloss"] and "errors" not in blocks["bouncer#1"]
        b = blocks["baker#1"]
        assert b["gloss"] is None and b["kind"] is None and "role_gloss" in b["errors"]
        assert len(client.calls) == 2 + 2 + 3                          # two gloss calls each, kind for bouncer only

    def test_a_failed_kind_keeps_the_gloss(self, tmp_path):
        blocks, _ = run([held_row("bouncer", BOUNCER)], FakeAsyncAnthropic(stage_responder(bad_kind=("bouncer",))),
                        tmp_path)
        b = blocks["bouncer#1"]
        assert b["gloss"] and b["kind"] is None and b["human"] is None and "role_kind" in b["errors"]
        assert all(r["kind"] is None and r["error"] for r in b["kind_readings"])

    def test_a_row_with_a_gloss_gets_only_the_kind_calls(self, tmp_path):
        r = held_row("bouncer", BOUNCER)
        r[RP.BLOCK] = {"gloss": gloss_for("bouncer", BOUNCER), "kind": None}
        client = FakeAsyncAnthropic(stage_responder())
        blocks, _ = run([r], client, tmp_path)
        assert len(client.calls) == 3 and blocks["bouncer#1"]["kind"] == "occupation"

    def test_a_budget_stop_keeps_what_was_paid_for_and_a_resume_pays_nothing_twice(self, tmp_path):
        rows = [held_row("bouncer", BOUNCER), held_row("baker", "bakes bread")]
        got = {}
        usage = GuardedUsage(budget_usd=1e-9)
        with pytest.raises(BudgetExceededError):
            RP.run_stage_rows(rows, client=FakeAsyncAnthropic(stage_responder()), usage=usage, batch_id="roles_t",
                              records_path=tmp_path / RP.RESPONSES_NAME, on_block=lambda k, b: got.__setitem__(k, b),
                              retry_delays=(), concurrency=1)
        recs = records(tmp_path)
        assert len(recs) == 1 and recs[0]["text"]                     # the call that crossed the cap is recorded
        assert got == {}                                              # no row finished: no block
        client = FakeAsyncAnthropic(stage_responder())
        blocks, _ = run(rows, client, tmp_path)                       # the resume: the recorded answer replayed
        assert len(client.calls) == 1 + 6 and set(blocks) == {"bouncer#1", "baker#1"}

    def test_the_batches_transport(self, tmp_path):
        from assistant_axis.gapgen.batches import BatchTransport
        from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep
        rows = [held_row("bouncer", BOUNCER), held_row("baker", "bakes bread")]
        bc = FakeBatchClient(stage_responder(bad_gloss_once=("baker",)))
        usage = GuardedUsage(budget_usd=5.0)
        blocks = RP.run_stage_rows(rows, client=None, usage=usage, batch_id="roles_b",
                                   records_path=tmp_path / RP.RESPONSES_NAME, retry_delays=(),
                                   transport_factory=lambda r: BatchTransport(r, bc, tmp_path / "batches.json",
                                                                              sleep=no_sleep, budget_usd=5.0),
                                   cache_ttl="1h")
        assert blocks["bouncer#1"]["kind"] == "occupation" and blocks["baker#1"]["gloss"]
        waves = json.loads((tmp_path / "batches.json").read_text())["waves"]
        assert set(waves) == {"s1_role_gloss", "s1_role_gloss_retry", "s2_role_kind"}
        assert all(m.endswith(":batch") for m in usage.per_model)
        recs = records(tmp_path)
        assert all(r["transport"] == "batches" and r["batch_request_id"] for r in recs)
        assert len({r["custom_id"] for r in recs}) == len(recs) and all(len(r["custom_id"]) <= 64 for r in recs)

    def test_summary(self, tmp_path):
        rows = [held_row("bouncer", BOUNCER), held_row("baker", "bakes bread")]
        blocks, _ = run(rows, FakeAsyncAnthropic(stage_responder(bad_gloss=("baker",))), tmp_path)
        s = RP.stage_summary(blocks)
        assert s == {"n_rows": 2, "n_glossed": 1, "n_gloss_failed": 1, "n_gloss_form_ok": 1, "n_kind_failed": 0,
                     "kinds": {"occupation": 1}, "n_kind_unanimous": 1, "n_kind_split": 0}
        line = RP.result_line(rows[0], blocks["bouncer#1"])
        assert line["key"] == "bouncer#1" and line[RP.BLOCK]["kind"] == "occupation"


def test_run_stage_rows_closes_its_client_inside_the_loop(tmp_path):
    closed = []

    class Closing:
        async def close(self):
            closed.append(True)

    RP.run_stage_rows([], client=Closing(), usage=MultiModelUsage(), batch_id="roles_close",
                      records_path=tmp_path / "r.jsonl")
    assert closed == [True]
