"""The states pass, queue prompt v4 (Roger, 2026-10-09): the duration question and its narrative test, the role
question for a lasting condition (the kind call's own definition), the routes (role, lasting, predisposition,
renamed, held), the gloss check (a keyword scan backed by a Haiku call), the alignment call on a confirmed gloss, the
released rows' way through M3, the review graph, the review app and promotion by name, the renamed route's new
candidates (one hop only), the Message Batches transport and ``--resume``.  No API call: fake clients throughout."""
import argparse
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import physical_pass as PP
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen import states_pass as sp
from assistant_axis.gapgen.batches import BatchTransport
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.registry import Candidate, Registry, new_record, submit_candidates
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep

REPO = Path(__file__).resolve().parents[2]
H55 = "claude-haiku-5-5"

# --------------------------------------------------------------------------- the fake model

#: The queue answers by label (invented words: none is a corpus label).
SPEC = {
    "lastwell": dict(typical_duration="months", lasting=True, role=False,
                     gloss="This means carrying the loss for months, missing the person every day and finding "
                           "ordinary plans emptied by it."),
    "rolish": dict(typical_duration="years", lasting=True, role=True,
                   gloss="This means having left working life for good and living on a pension and savings."),
    "glumish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
                    gloss="This means sinking easily into gloom over small setbacks and letting it show in a flat "
                          "voice."),
    "moodish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
                    gloss="This means sliding into low spirits over small setbacks and letting it show in a flat "
                          "voice."),
    "nowish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
                   gloss="This means feeling low right now after a bad morning and saying so."),
    "startly": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False,
                    suggested_name="jumpyish", gloss="This means jolting at every sudden noise and needing time to "
                                                     "settle."),
    "startly2": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False,
                     suggested_name="jumpyish2", gloss="This means jolting at every sudden noise."),
    "wetish": dict(typical_duration="hours", lasting=False, plausible=False),
}
CHECK = {"moodish": "predisposition", "nowish": "passing"}
ALIGN = {"lastwell": 0, "glumish": 1, "moodish": 2, "nowish": 0}


def qrow(i, label, **kw):
    base = {"id": i, "label": label, "reason": "How long it lasts, and whether a person is prone to it.",
            "typical_duration": "hours", "lasting": False, "role": None, "plausible": False, "name_fits": None,
            "suggested_name": None, "gloss": None, "confidence": 0.8}
    base.update(kw)
    return base


def responder(*, spec=SPEC, check=CHECK, align=ALIGN, tokens=(1000, 200), bad_check_once=(), bad_align=()):
    seen: dict = {}
    align_sys = sr.load_prompt("alignment")

    def answer(kw):
        s = system_text(kw)
        if s == sp.QUEUE_PROMPT:
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            body = {"results": [qrow(it["id"], it["label"], **spec.get(it["label"], {})) for it in items]}
            return make_response(json.dumps(body), input_tokens=tokens[0], output_tokens=tokens[1])
        if s == sp.CHECK_PROMPT:
            obj = json.loads(user_text(kw))
            lb = obj["label"]
            seen[("check", lb)] = seen.get(("check", lb), 0) + 1
            if lb in bad_check_once and seen[("check", lb)] == 1:
                return make_response("no idea", input_tokens=300, output_tokens=5)
            return make_response(json.dumps({"reason": "As written.", "reading": check.get(lb, "predisposition")}),
                                 input_tokens=300, output_tokens=40)
        assert s == align_sys
        obj = json.loads(user_text(kw))
        if obj["label"] in bad_align:
            return make_response("{}", input_tokens=700, output_tokens=5)
        return make_response(json.dumps({"results": [{"id": 1, "reason": "Mood, not conduct.",
                                                      "alignment": align.get(obj["label"], 0)}]}),
                             input_tokens=780, output_tokens=120)
    return answer


def items(labels=("lastwell", "rolish", "glumish", "moodish", "nowish", "startly", "wetish"), *, hop=()):
    return [sp.StatesItem(key=f"{lb}#1", label=lb, text=f"being {lb} for a while",
                          meta={"from_states_pass": lb in hop}) for lb in labels]


def runner(client, **kw):
    kw.setdefault("retry_delays", ())
    return sp.StatesPassRunner(client=client, batch_id="sp4", mode="queue", **kw)


# --------------------------------------------------------------------------- the prompts

class TestPrompts:
    def test_versions_and_pins(self):
        from assistant_axis.gapgen.rubric_versions import HISTORY, current, mismatches
        assert sp.RUBRIC_VERSIONS == {"queue": 4, "corpus": 2} and sp.CHECK_RUBRIC_VERSION == 1
        assert current()["states_queue"] == (4, sp.PROMPT_SHA256["queue"])
        assert current()["states_check"] == (1, sp.CHECK_PROMPT_SHA256)
        assert HISTORY["states_queue"][4] == sp.PROMPT_SHA256["queue"]
        assert HISTORY["states_check"][1] == sp.CHECK_PROMPT_SHA256
        assert [m for m in mismatches() if m.startswith("states")] == []

    def test_the_role_question_is_the_kind_calls_own_definition(self):
        text = (REPO / "reports" / "trait_gap_generation" / "rubrics" / "step2_kind.md").read_text(encoding="utf-8")
        line = next(x for x in text.splitlines() if x.startswith("- role: "))
        definition = line[len("- role: "):].rstrip(".")
        assert definition.startswith("an identity big enough to organize the whole persona")
        assert definition in " ".join(sp.QUEUE_PROMPT.split())

    def test_rogers_duration_rule_is_in_the_prompt(self):
        p = " ".join(sp.QUEUE_PROMPT.split())
        assert "lasts months or longer" in p and "wear off in the course of a story" in p
        assert "a dozen paragraphs often spans weeks, but rarely months" in p
        assert "a state of weeks, or of weeks to months, is not lasting" in p
        for d in sp.DURATIONS:
            assert f'"{d}"' in p

    def test_reason_first_and_the_key_order(self):
        p = " ".join(sp.QUEUE_PROMPT.split())
        schema = p[p.index('{"results"'):]
        order = ['"id"', '"label"', '"reason"', '"typical_duration"', '"lasting"', '"role"', '"plausible"',
                 '"name_fits"', '"suggested_name"', '"gloss"', '"confidence"']
        assert [schema.index(k) for k in order] == sorted(schema.index(k) for k in order)
        c = " ".join(sp.CHECK_PROMPT.split())
        assert c.index('"reason"') < c.index('"reading"')

    def test_the_check_prompt_does_not_name_the_route_and_the_user_turn_is_label_and_gloss(self):
        u = json.loads(sp.build_check_prompt("glumish", "This means  sinking easily."))
        assert u == {"label": "glumish", "description": "This means sinking easily."}
        for r in sp.CHECK_READINGS:
            assert f'"{r}"' in sp.CHECK_PROMPT

    def test_examples_cover_every_route_and_are_quoted(self):
        for w in sp.QUEUE_EXAMPLES:
            assert f'- "{w}":' in sp.QUEUE_PROMPT
        p = sp.QUEUE_PROMPT
        assert "role true" in p and "role false" in p and 'suggested_name "jumpy"' in p and "name_fits true" in p
        assert "plausible false" in p

    def test_example_words_are_not_on_the_registry_states_list(self):
        """Not a hygiene rule of the tests' sources (the registry is git-ignored), but the pilot judges that list:
        the snapshot's states rows must not be the prompt's examples."""
        snap = REPO / "data" / "candidates" / "registry.snapshot.jsonl"
        if not snap.exists():
            pytest.skip("no snapshot")
        rows = [json.loads(x) for x in snap.read_text(encoding="utf-8").splitlines() if x.strip()]
        states = {r["stem"] for r in rows if r.get("holding") == "states"}
        assert not states & {w.replace("-", "_") for w in sp.QUEUE_EXAMPLES + sp.SUGGESTED_NAMES}


# --------------------------------------------------------------------------- validation, routes, the scan

class TestValidator:
    def test_lasting_rows_need_role_and_gloss_and_drop_the_predisposition_answers(self):
        rows, errs = sp.parse_batch(json.dumps({"results": [
            qrow(1, "a", typical_duration="months", lasting=True, role=False, gloss="This means g.", plausible=True,
                 name_fits=False, suggested_name="x"),
            qrow(2, "b", typical_duration="years", lasting=True, role=None, gloss="This means g."),
            qrow(3, "c", typical_duration="years", lasting=True, role=True, gloss=None),
            qrow(4, "d", typical_duration="fortnights", lasting=False),
            qrow(5, "e", typical_duration="weeks", lasting="sometimes"),
            qrow(6, "f", typical_duration="months", lasting=False, plausible=False),
            qrow(7, "g", typical_duration="days", lasting=False, plausible=True, name_fits=True, gloss="This means g.",
                 role=True)]}), list(range(1, 8)), mode="queue", labels=dict(enumerate("abcdefg", 1)))
        assert set(rows) == {1, 6, 7} and set(errs) == {2, 3, 4, 5}
        assert rows[1]["role"] is False and rows[1]["plausible"] is None and rows[1]["suggested_name"] is None
        assert rows[1]["duration_agrees"] is True
        assert rows[6]["duration_agrees"] is False                    # months, not lasting: the borderline, kept
        assert rows[7]["role"] is None and rows[7]["gloss"] == "This means g."

    def test_v3_rows_are_refused(self):
        v3 = {"id": 1, "label": "a", "reason": "r", "plausible": False, "name_fits": None, "suggested_name": None,
              "gloss": None, "confidence": 0.9}
        rows, errs = sp.parse_batch(json.dumps({"results": [v3]}), [1], mode="queue", labels={1: "a"})
        assert rows == {} and "typical_duration" in errs[1]


class TestRoutes:
    @pytest.mark.parametrize("ans, route", [
        (dict(lasting=True, role=True), "role"),
        (dict(lasting=True, role=False), "lasting"),
        (dict(lasting=False, plausible=True, name_fits=True), "predisposition"),
        (dict(lasting=False, plausible=True, name_fits=False, suggested_name=" X-Y "), "predisposition"),
        (dict(lasting=False, plausible=True, name_fits=False, suggested_name="other"), "renamed"),
        (dict(lasting=False, plausible=False), "held"),
    ])
    def test_route_for(self, ans, route):
        assert sp.route_for(ans, label="x y")[0] == route

    def test_one_hop(self):
        ans = dict(lasting=False, plausible=True, name_fits=False, suggested_name="other")
        assert sp.route_for(ans, label="x", from_states_pass=True) == ("held", sp.ONE_HOP_REASON)
        # a rename of a rename is the only thing the hop rule holds
        assert sp.route_for(dict(lasting=True, role=False), label="x", from_states_pass=True)[0] == "lasting"
        assert sp.route_for(dict(lasting=False, plausible=True, name_fits=True), label="x",
                            from_states_pass=True)[0] == "predisposition"

    def test_holding_after(self):
        assert sp.holding_after("lasting") == sp.holding_after("predisposition") == "states_released"
        assert sp.holding_after("role") == "roles"
        assert sp.holding_after("renamed") == sp.holding_after("held") == "states"


class TestScan:
    def test_predisposition_markers(self):
        assert sp.scan_gloss("This means crying easily at sad news.", "predisposition")["verdict"] == "pass"
        assert sp.scan_gloss("This means sulking whenever crossed.", "predisposition")["for"] == ["whenever"]
        s = sp.scan_gloss("This means sulking often, as just now.", "predisposition")
        assert s["verdict"] == "unclear" and s["against"] == ["just"]
        assert sp.scan_gloss("This means sulking at a slight.", "predisposition")["verdict"] == "unclear"

    def test_lasting_markers_and_whole_words(self):
        assert sp.scan_gloss("This means living for months with the loss.", "lasting")["verdict"] == "pass"
        assert sp.scan_gloss("This means living with the loss.", "lasting")["verdict"] == "unclear"
        s = sp.scan_gloss("This means feeling it today, after years of it.", "lasting")
        assert s["for"] == ["years"] and s["against"] == ["today"] and s["verdict"] == "unclear"
        # whole words: anyone is not any, everyday is not every day
        assert sp.scan_gloss("This means telling anyone about everything.", "predisposition")["for"] == []
        assert sp.scan_gloss("This means doing everyday chores.", "lasting")["for"] == []

    def test_the_scan_reads_only_the_two_released_routes(self):
        with pytest.raises(ValueError):
            sp.scan_gloss("This means x.", "renamed")


# --------------------------------------------------------------------------- the runner, live

class TestRunnerLive:
    def test_every_route(self):
        client = FakeAsyncAnthropic(responder())
        r = runner(client, model=H55)
        out = {x.key: x for x in r.run(items())}
        assert all(x.stage == "judged" for x in out.values())
        b = {k.split("#")[0]: x.block for k, x in out.items()}
        assert {k: v["route"] for k, v in b.items()} == {
            "lastwell": "lasting", "rolish": "role", "glumish": "predisposition", "moodish": "predisposition",
            "nowish": "held", "startly": "renamed", "wetish": "held"}
        assert {k: v["holding_after"] for k, v in b.items()} == {
            "lastwell": "states_released", "rolish": "roles", "glumish": "states_released",
            "moodish": "states_released", "nowish": "states", "startly": "states", "wetish": "states"}
        # the scan passed two glosses, the check read two
        assert b["lastwell"]["gloss_check"]["by"] == "scan" and b["glumish"]["gloss_check"]["by"] == "scan"
        assert b["moodish"]["gloss_check"]["by"] == "check" and b["moodish"]["gloss_check"]["accepted"] is True
        chk = b["moodish"]["gloss_check"]["check"]
        assert chk["reading"] == "predisposition" and chk["rubric_version"] == 1
        assert chk["prompt_sha256"] == sp.CHECK_PROMPT_SHA256
        assert b["nowish"]["gloss_check"]["accepted"] is False and b["nowish"]["proposed_route"] == "predisposition"
        assert b["nowish"]["route_reason"].startswith("gloss check: the predisposition gloss was read as passing")
        assert b["nowish"]["alignment"] is None                       # paid for beside the check, not recorded
        # alignment on the released rows only, M1's call as pinned
        assert {k: b[k]["alignment"] for k in ("lastwell", "glumish", "moodish")} == {"lastwell": 0, "glumish": 1,
                                                                                    "moodish": 2}
        pins = PP.pins()
        assert b["lastwell"]["alignment_step_version"] == pins["step_versions"]["alignment"]
        assert b["lastwell"]["alignment_prompt_sha256"] == pins["prompt_sha256"]["alignment"]
        assert b["lastwell"]["alignment_model"] == sp.ALIGNMENT_MODEL == PP.MODEL
        assert b["rolish"]["gloss_check"] is None and b["rolish"]["alignment"] is None
        assert b["rolish"]["role"] is True and b["rolish"]["gloss"].startswith("This means having left")
        assert b["startly"]["suggested_name"] == "jumpyish" and b["startly"]["gloss_check"] is None
        assert b["wetish"]["route_reason"] == "not lasting, and no habitual predisposition is plausible"
        assert all(v["rubric_version"] == 4 and v["prompt_sha256"] == sp.PROMPT_SHA256["queue"] for v in b.values())
        # one queue call, two checks, four alignment calls (nowish's too: sent beside its check)
        steps = [("queue" if system_text(c) == sp.QUEUE_PROMPT else "check" if system_text(c) == sp.CHECK_PROMPT
                  else "alignment") for c in client.calls]
        assert sorted(steps) == ["alignment"] * 4 + ["check"] * 2 + ["queue"]
        checked = sorted(json.loads(user_text(c))["label"] for c in client.calls if system_text(c) == sp.CHECK_PROMPT)
        assert checked == ["moodish", "nowish"]
        assert r.usage.n_calls == 7 and len(r.responses) == 7
        assert {rec["stage"] for rec in r.responses} == {"queue", "gloss"}

    def test_the_check_is_never_told_the_route(self):
        client = FakeAsyncAnthropic(responder())
        runner(client, model=H55).run(items(("moodish",)))
        c = next(c for c in client.calls if system_text(c) == sp.CHECK_PROMPT)
        assert "predisposition" not in user_text(c) and "lasting" not in user_text(c)

    def test_one_hop_holds_a_rename_of_a_rename(self):
        out = runner(FakeAsyncAnthropic(responder()), model=H55).run(items(("startly", "startly2"), hop=("startly2",)))
        b = {x.key: x.block for x in out}
        assert b["startly#1"]["route"] == "renamed"
        assert b["startly2#1"]["route"] == "held" and b["startly2#1"]["route_reason"] == sp.ONE_HOP_REASON
        cands = sp.renamed_candidates(out, batch_id="sp4")
        assert [(c.surface, c.generator, c.run_id, c.source_ref) for c in cands] == [
            ("jumpyish", "states_pass", "sp4", "startly#1")]
        assert cands[0].gloss_hint == SPEC["startly"]["gloss"]

    def test_a_failed_check_is_asked_again_once_and_a_failed_alignment_keeps_the_row_released(self):
        client = FakeAsyncAnthropic(responder(bad_check_once=("moodish",), bad_align=("glumish",)))
        r = runner(client, model=H55)
        out = {x.key: x for x in r.run(items(("moodish", "glumish")))}
        # the parse rates of the two call kinds are counted for the end-of-run warning
        assert (r.stats["sent_check"], r.stats["ok_check"]) == (2, 1)
        assert (r.stats["sent_alignment"], r.stats["ok_alignment"]) == (3, 1)
        assert out["moodish#1"].block["gloss_check"]["accepted"] is True
        g = out["glumish#1"].block
        assert g["route"] == "predisposition" and g["alignment"] is None and "alignment" in g["errors"]
        n_check = sum(1 for c in client.calls if system_text(c) == sp.CHECK_PROMPT)
        n_align = sum(1 for c in client.calls if system_text(c) != sp.CHECK_PROMPT and system_text(c) != sp.QUEUE_PROMPT)
        assert n_check == 2 and n_align == 3                          # moodish once, glumish twice

    def test_a_check_that_never_answers_fails_the_row_without_a_block(self):
        def bad(kw):
            if system_text(kw) == sp.CHECK_PROMPT:
                return make_response("nothing", input_tokens=10, output_tokens=2)
            return responder()(kw)
        out = {x.key: x for x in runner(FakeAsyncAnthropic(bad), model=H55).run(items(("moodish", "wetish")))}
        assert out["moodish#1"].stage == "failed" and out["moodish#1"].block is None
        assert out["moodish#1"].error.startswith("gloss check:")
        assert out["wetish#1"].stage == "judged"

    def test_align_off(self):
        client = FakeAsyncAnthropic(responder())
        out = runner(client, model=H55, align=False).run(items(("glumish",)))
        assert out[0].block["alignment"] is None and out[0].block["alignment_note"] == "not run (align off)"
        assert len(client.calls) == 1

    def test_a_budget_stop_after_the_queue_keeps_the_final_rows_and_leaves_the_rest_pending(self):
        usage = GuardedUsage(budget_usd=0.05)
        r = runner(FakeAsyncAnthropic(responder(tokens=(1_000_000, 10))), model=H55, usage=usage)
        with pytest.raises(BudgetExceededError):
            r.run(items())
        st = {k.split("#")[0]: x.stage for k, x in r.results.items()}
        assert st == {"lastwell": "pending", "rolish": "judged", "glumish": "pending", "moodish": "pending",
                      "nowish": "pending", "startly": "judged", "wetish": "judged"}
        assert len(r.responses) == 1

    def test_resume_replays_the_answers_on_record(self):
        first = runner(FakeAsyncAnthropic(responder()), model=H55)
        a = {x.key: x.block for x in first.run(items())}
        client = FakeAsyncAnthropic(responder())
        second = runner(client, model=H55, resume_records=first.responses)
        b = {x.key: x.block for x in second.run(items())}
        assert client.calls == []
        strip = lambda d: {k: {kk: vv for kk, vv in v.items() if kk != "at"} for k, v in d.items()}  # noqa: E731
        assert strip(a) == strip(b) and len(second.responses) == len(first.responses)

    def test_resume_after_a_stop_sends_only_what_is_missing(self):
        usage = GuardedUsage(budget_usd=0.05)
        first = runner(FakeAsyncAnthropic(responder(tokens=(1_000_000, 10))), model=H55, usage=usage)
        with pytest.raises(BudgetExceededError):
            first.run(items())
        client = FakeAsyncAnthropic(responder())
        second = runner(client, model=H55, resume_records=first.responses)
        out = {x.key: x for x in second.run(items())}
        assert all(x.stage == "judged" for x in out.values())
        assert not any(system_text(c) == sp.QUEUE_PROMPT for c in client.calls)
        assert len(client.calls) == 6                                  # two checks, four alignment calls


# --------------------------------------------------------------------------- the runner, through the Message Batches API

class TestRunnerBatches:
    def test_the_same_routes_charged_at_the_batch_rate(self, tmp_path):
        live = FakeAsyncAnthropic(responder())
        r = runner(live, model=H55, usage=GuardedUsage(budget_usd=5.0))
        bc = FakeBatchClient(responder())
        r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
        out = {x.key: x.block for x in r.run(items())}
        assert live.calls == []
        state = json.loads((tmp_path / "batches.json").read_text())
        assert list(state["waves"]) == ["queue", "gloss"]
        ref = {x.key: x.block for x in runner(FakeAsyncAnthropic(responder()), model=H55).run(items())}
        assert {k: v["route"] for k, v in out.items()} == {k: v["route"] for k, v in ref.items()}
        assert set(r.usage.per_model) == {H55 + BATCH_SUFFIX}
        for b in bc.batches.created:
            cids = [q["custom_id"] for q in b["requests"]]
            assert len(set(cids)) == len(cids)
            assert all(len(c) <= 64 and all(ch.isalnum() or ch in "_-" for ch in c) for c in cids)
        assert all(rec["transport"] == "batches" and rec["batch_request_id"] for rec in r.responses)


# --------------------------------------------------------------------------- the CLI

def _states_row(reg, label, *, gen="g", judged=None):
    submit_candidates([Candidate(surface=label, generator=gen, run_id="r", source_ref=None)], registry_path=reg)
    Registry(reg).update(f"{label}#1", {"holding": "states", "gloss": None, "filter": {
        "pipeline": "split", "verdict": "tagged", "outcome": "states", "tags": ["state"], "region": None,
        "judged_sense": judged or f"being {label} for a while", "reason": "A passing condition."}})


@pytest.fixture
def cli(monkeypatch):
    import anthropic
    import dotenv

    from data_analysis.gap_generation import states_pass as cli_mod
    holder = {"live": [], "batch": []}

    def live_factory(**kw):
        c = FakeAsyncAnthropic(holder.get("responder") or responder())
        holder["live"].append(c)
        return c

    def batch_factory(**kw):
        c = FakeBatchClient(holder.get("responder") or responder(), polls=0)
        holder["batch"].append(c)
        return c
    monkeypatch.setattr(anthropic, "AsyncAnthropic", live_factory)
    monkeypatch.setattr(anthropic, "Anthropic", batch_factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli_mod, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(cli_mod, "platform_dirty_files", lambda *a, **k: [])
    monkeypatch.setattr(cli_mod, "POLL_SECONDS", 0)
    holder["mod"] = cli_mod
    return holder


def _registry(tmp_path):
    reg = tmp_path / "registry.jsonl"
    for lb in SPEC:
        _states_row(reg, lb, gen="states_pass" if lb == "startly2" else "g")
    submit_candidates([Candidate(surface="stubborn", generator="g", run_id="r")], registry_path=reg)
    return reg


class TestCLI:
    def test_registry_mode_routes_every_row(self, tmp_path, cli):
        reg = _registry(tmp_path)
        cand = tmp_path / "cand"
        rc = cli["mod"].main(["--batch-id", "sp4", "--mode", "queue", "--holding-states", "--registry", str(reg),
                              "--out-root", str(cand), "--transport", "live"])
        assert rc == 0
        rows = Registry(reg).fold()
        hold = {k.split("#")[0]: rows[k]["holding"] for k in rows if k != "stubborn#1" and not k.startswith("jumpyish")}
        assert hold == {"lastwell": "states_released", "rolish": "roles", "glumish": "states_released",
                        "moodish": "states_released", "nowish": "states", "startly": "states",
                        "startly2": "states", "wetish": "states"}
        assert rows["rolish#1"]["entity_type"] == "role"
        assert rows["startly2#1"]["states_pass"]["route_reason"] == sp.ONE_HOP_REASON
        # the renamed route: a new candidate, recorded in the tracked candidates.jsonl first
        new = rows["jumpyish#1"]
        src = new["sources"][0]
        assert (src["generator"], src["run_id"], src["source_ref"]) == ("states_pass", "sp4", "startly#1")
        assert src["gloss_hint"] == SPEC["startly"]["gloss"] and new["filter"] is None and new["holding"] is None
        runf = cand / "runs" / "states_pass" / "sp4" / "candidates.jsonl"
        assert [json.loads(x)["surface"] for x in runf.read_text().splitlines()] == ["jumpyish"]
        assert rows["startly#1"]["states_pass"]["renamed_to"] == {"surface": "jumpyish", "stem": "jumpyish",
                                                                  "key": "jumpyish#1", "run": "states_pass/sp4"}
        d = cand / "states_pass" / "sp4"
        run = json.loads((d / "run.json").read_text())
        assert run["rubric_version"] == 4 and run["prompt_sha256"] == sp.PROMPT_SHA256["queue"]
        assert run["check_rubric_version"] == 1 and run["check_prompt_sha256"] == sp.CHECK_PROMPT_SHA256
        assert run["alignment_step_version"] == PP.pins()["step_versions"]["alignment"]
        assert run["transport"] == "live" and run["item_keys"] == sorted(f"{lb}#1" for lb in SPEC)
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["routes"] == {"role": 1, "lasting": 1, "predisposition": 2, "renamed": 1, "held": 3}
        assert s["submitted_renames"] == ["startly -> jumpyish"]
        assert s["gloss_check"]["by_scan"] == 2 and s["gloss_check"]["check_accepted"] == 1
        assert [x["label"] for x in s["gloss_check"]["rejected"]] == ["nowish"]
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 7
        # a second run without --rejudge finds nothing new on the states list but the held rows' v4 blocks
        assert cli["mod"].main(["--batch-id", "sp4b", "--mode", "queue", "--holding-states", "--registry", str(reg),
                                "--out-root", str(cand)]) == 0
        assert not (cand / "states_pass" / "sp4b").exists()

    def test_batches_transport(self, tmp_path, cli):
        reg = _registry(tmp_path)
        cand = tmp_path / "cand"
        rc = cli["mod"].main(["--batch-id", "sp4", "--mode", "queue", "--holding-states", "--registry", str(reg),
                              "--out-root", str(cand), "--transport", "batches"])
        assert rc == 0 and cli["live"] == [] and len(cli["batch"]) == 1         # no live client is made
        d = cand / "states_pass" / "sp4"
        assert list(json.loads((d / "batches.json").read_text())["waves"]) == ["queue", "gloss"]
        u = json.loads((d / "usage.json").read_text())
        assert set(u["per_model"]) == {H55 + BATCH_SUFFIX}
        assert Registry(reg).fold()["lastwell#1"]["holding"] == "states_released"

    def test_resume_after_a_budget_stop(self, tmp_path, cli):
        reg = _registry(tmp_path)
        cand = tmp_path / "cand"
        cli["responder"] = responder(tokens=(1_000_000, 10))
        args = ["--batch-id", "sp4", "--mode", "queue", "--holding-states", "--registry", str(reg), "--out-root",
                str(cand), "--transport", "live"]
        assert cli["mod"].main(args + ["--budget-usd", "0.05"]) == 2
        rows = Registry(reg).fold()
        assert rows["rolish#1"]["holding"] == "roles"                      # final before the stop: written
        assert rows["lastwell#1"]["holding"] == "states" and not rows["lastwell#1"].get("states_pass")
        cli["responder"] = responder()
        assert cli["mod"].main(args + ["--resume"]) == 0
        second = cli["live"][-1]
        assert not any(system_text(c) == sp.QUEUE_PROMPT for c in second.calls) and len(second.calls) == 6
        rows = Registry(reg).fold()
        assert rows["lastwell#1"]["holding"] == "states_released"
        run = json.loads((cand / "states_pass" / "sp4" / "run.json").read_text())
        assert len(run["sessions"]) == 2
        resp = (cand / "states_pass" / "sp4" / "responses.jsonl").read_text().splitlines()
        assert len(resp) == 7                                              # the stopped session's answer kept

    def test_dry_run_renders_both_calls_and_writes_nothing(self, tmp_path, cli, capsys):
        reg = _registry(tmp_path)
        before = reg.read_bytes()
        cand = tmp_path / "cand"
        assert cli["mod"].main(["--batch-id", "d1", "--mode", "queue", "--holding-states", "--registry", str(reg),
                                "--out-root", str(cand), "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "queue v4" in out and "check v1" in out and "tokens at" in out
        assert reg.read_bytes() == before and not cand.exists() and cli["live"] == []


# --------------------------------------------------------------------------- M3, the review graph, the app, promotion

GLOSS = "This means sinking easily into gloom over small setbacks and letting it show in a flat voice."


def released_row(surface="glumish", *, route="predisposition", holding="states_released", accepted=True, align=1):
    r = new_record(surface, sources=[{"generator": "roget", "run_id": "2026-10-08-pilot", "rank": 1, "score": None,
                                      "source_ref": None, "gloss_hint": None, "partner_hint": None, "surface": surface}])
    r["filter"] = {"pipeline": "split", "verdict": "tagged", "outcome": "states", "tags": ["state"],
                   "judged_sense": "feeling low for a while", "region": None, "alignment": None, "reason": "A mood."}
    r["gloss"] = None
    r["holding"] = holding
    r["states_pass"] = {"mode": "queue", "rubric_version": 4, "batch_id": "states_pilots_1", "route": route,
                        "typical_duration": "hours" if route == "predisposition" else "months", "gloss": GLOSS,
                        "reason": "People are prone to it.", "alignment": align,
                        "gloss_check": {"kind": route, "accepted": accepted, "by": "scan"}}
    return r


class TestM3:
    def test_the_states_builder(self):
        c, why = NR.candidate_from_row(released_row(), holding="states")
        assert why is None and c.gloss == GLOSS and c.alignment_score == 1 and c.cut_off == 3 and c.region is None
        assert c.generators == ["roget"] and c.label == "glumish"
        assert NR.candidate_from_row(released_row(align=None), holding="states")[0].cut_off == 4

    def test_refusals(self):
        assert NR.candidate_from_row(released_row()) == (None, "not_a_trait")
        assert NR.candidate_from_row(released_row(holding="states"), holding="states") == (
            None, "not_on_states_released_list")
        assert NR.candidate_from_row(released_row(accepted=False), holding="states") == (None, "no_gloss")
        assert NR.candidate_from_row(released_row(), holding="physical") == (None, "not_on_physical_list")
        with pytest.raises(ValueError):
            NR.candidate_from_row(released_row(), holding="roles")

    def test_select_candidates_and_the_source_pass(self):
        from data_analysis.gap_generation import novelty_score as NS
        rows = {r["key"]: r for r in (released_row("glumish"), released_row("lastwell", route="lasting"),
                                      released_row("heldish", holding="states"))}
        args = argparse.Namespace(keys=None, run=None, rescore=False, include_held=False, limit=None, holding="states")
        cands, skipped = NS.select_candidates(rows, args, batch_id="states_m3")
        assert [c.key for c in cands] == ["glumish#1", "lastwell#1"] and skipped == {"not_on_states_list": 1}
        assert NS.source_holding({"batch_id": "x", "run": {"pass": "states"}}) == "states"
        assert NS.source_holding({"batch_id": "x", "run": {"pass": "physical"}}) == "physical"
        p = NS.build_parser()
        assert p.parse_args(["score", "--batch-id", "b", "--unscored", "--holding", "states"]).holding == "states"


class TestReview:
    def test_r1_reads_a_states_batch(self):
        from assistant_axis.gapgen import review_graph as RG
        row = released_row()
        row["novelty"] = {"run_id": "states_m3", "pass": "states", "decision": "new", "alignment_score": 1}
        c, why = RG.pair_candidate(row)
        assert why is None and c.gloss == GLOSS and c.cut_off == 4
        n = RG._candidate_node(row)
        assert n.outcome == "states" and n.gloss == GLOSS and n.alignment_score == 1
        row["novelty"] = {"run_id": "m3b", "decision": "new"}
        assert RG.pair_candidate(row) == (None, "not_a_trait")

    def test_the_card_says_where_the_row_came_from(self):
        from assistant_axis.gapgen import review_graph as RG
        from assistant_axis.gapgen.review_app import decisions as D
        row = released_row(route="lasting")
        row["novelty"] = {"run_id": "states_m3", "pass": "states", "decision": "new"}
        node = RG._candidate_node(row)
        g = RG.Graph(batch_id="rv", from_batches=["states_m3"], config={}, nodes=[node], edges=[], cliques=[],
                     clique_links=[], proposed_groups=[], proposed_links=[])
        st = D.ReviewState(g, rows={row["key"]: row})
        card = st.member_card(row["key"])
        assert "states pass: lasting (months)" in card["tags"] and "states" in card["tags"]
        assert card["gloss"] == GLOSS


class TestPromote:
    @pytest.fixture
    def data_dir(self, tmp_path):
        d = tmp_path / "data"
        for et in ("traits", "roles"):
            (d / et / "instructions").mkdir(parents=True)
        return d

    def test_promoted_by_name_with_the_states_tags(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        for route, tag in (("predisposition", "predisposition"), ("lasting", "lasting_state")):
            rec = released_row(route=route)
            rec["novelty"] = {"run_id": "states_m3", "pass": "states", "decision": "new"}
            q = {"_meta": {}, "entries": []}
            rep = promote({rec["key"]: rec}, q, [rec["key"]], data_dir=data_dir, dry_run=False,
                          allow_released_states=True)
            assert rep.promoted == [rec["key"]]
            e = q["entries"][-1]
            assert e["stem"] == "glumish" and e["description_draft"] == GLOSS
            assert e["tags"] == ["gap_gen", "source:roget", "state", "states_pass", tag]
            assert e["gap_gen"]["states_pass"]["route"] == route and "states_m3" in e["description_notes"]

    def test_refused_in_bulk_and_the_old_path_is_unchanged(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        rec = released_row()
        rep = promote({rec["key"]: rec}, {"_meta": {}, "entries": []}, [rec["key"]], data_dir=data_dir,
                      allow_physical=True)
        assert rep.promoted == [] and "promoted only by name" in rep.refused[rec["key"]]
        role = released_row("rolish", route="role", holding="roles")
        rep = promote({role["key"]: role}, {"_meta": {}, "entries": []}, [role["key"]], data_dir=data_dir,
                      allow_released_states=True, allow_physical=True)
        assert rep.refused[role["key"]] == "on the roles holding list (never promoted)"
        # a held v4 row with a renamed route still goes the old way, under Roger's confirmed name
        held = released_row("startly", route="renamed", holding="states")
        held["states_pass"].update(lasting=False, plausible=True, name_fits=False, suggested_name="jumpyish")
        q = {"_meta": {}, "entries": []}
        rep = promote({held["key"]: held}, q, [held["key"]], data_dir=data_dir, dry_run=False,
                      confirmed_state_names={held["key"]: "jumpyish"})
        assert rep.promoted == [held["key"]] and q["entries"][-1]["stem"] == "jumpyish"

    def test_gap_registry_promote_keys_and_the_holding_listing(self, tmp_path, data_dir, capsys):
        from data_analysis.gap_generation import gap_registry
        reg = tmp_path / "r.jsonl"
        Registry(reg).write([released_row(), released_row("rolish", route="role", holding="roles")])
        queue = tmp_path / "q.json"
        queue.write_text(json.dumps({"_meta": {}, "entries": []}))
        assert gap_registry.main(["--registry", str(reg), "--data-dir", str(data_dir), "promote", "--keys",
                                  "glumish#1", "--queue", str(queue), "--dry-run"]) == 0
        assert "WOULD PROMOTE glumish#1 -> glumish" in capsys.readouterr().out
        assert gap_registry.main(["--registry", str(reg), "holding", "--list", "states_released"]) == 0
        out = capsys.readouterr().out
        assert "**glumish**" in out and "states pass v4: predisposition" in out and GLOSS in out
        assert gap_registry.main(["--registry", str(reg), "holding", "--list", "roles"]) == 0
        assert "states pass v4: role" in capsys.readouterr().out

    def test_the_review_apps_apply_promotes_a_released_row(self, tmp_path):
        from assistant_axis.tests.test_gapgen_review_app import flow_for_apply, k, run_apply, write_env
        env = write_env(tmp_path)
        reg = env["reg"]
        rows = reg.fold()
        row = released_row("devout")
        row["key"], row["stem"], row["label"] = "devout#1", "devout", "devout"
        row["sources"] = rows[k("devout")]["sources"]
        row["novelty"] = rows[k("devout")]["novelty"] | {"pass": "states"}
        reg.write([row])
        rep = run_apply(env, flow_for_apply(env))
        assert k("devout") in [p["key"] for p in rep.promotions] and k("devout") not in rep.refused
        q = json.loads(env["queue"].read_text())
        e = next(x for x in q["entries"] if x["stem"] == "devout")
        assert "states_pass" in e["tags"] and "predisposition" in e["tags"] and e["description_draft"] == GLOSS
