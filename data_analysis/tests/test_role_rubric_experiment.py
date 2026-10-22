"""Tests for data_analysis/role_rubric_experiment.py, the role-judge rubric experiment.

Fakes only: no API call (the OpenAI client is a fake batch client, and the real one raises if
anything builds it), no GPU (the vector tests use tensors of a few numbers).  The arm tests read
the real role files of the 30 sampled roles.
"""
from __future__ import annotations

import difflib
import json
import math
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from data_analysis import role_rubric_experiment as exp  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
ROLES = REPO / "data" / "roles" / "instructions"
TRAITS = REPO / "data" / "traits" / "instructions"


@pytest.fixture(autouse=True)
def no_real_client(monkeypatch):
    """Nothing in these tests may reach the API: the key is a dummy (load_dotenv does not
    override it) and both the module's client factory and the SDK's client raise."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")

    def refuse(*a, **k):
        raise AssertionError("a test tried to build a real OpenAI client")
    monkeypatch.setattr(exp, "make_client", refuse)
    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", refuse)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

def _response(p: int, q: int, text: str = None) -> dict:
    question = f"Question number {q}?"
    return {"system_prompt": "You are someone.", "prompt_index": p, "question_index": q,
            "question": question, "label": "pos",
            "conversation": [{"role": "system", "content": "You are someone."},
                             {"role": "user", "content": question},
                             {"role": "assistant", "content": text or f"An answer, p{p} q{q}."}]}


def write_responses(directory: Path, stem: str, n: int = 4, *, prompts: int = 2) -> Path:
    """``n`` responses, keys ``pos_p{i % prompts}_q{i}``."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}.jsonl"
    with open(path, "w") as f:
        for i in range(n):
            f.write(json.dumps(_response(i % prompts, i)) + "\n")
    return path


class FakeBatchClient:
    """The slice of ``openai.AsyncOpenAI`` the batch runner uses.  A batch is in progress when
    created and completed at its first retrieve; ``reply(custom_id)`` gives each request's
    ``(text, finish_reason)``."""

    def __init__(self, reply=None, prompt_tokens=100, completion_tokens=10):
        self.reply = reply or (lambda cid: ("The response plays the role.\nSCORE: 3", "stop"))
        self.pt, self.ct = prompt_tokens, completion_tokens
        self.uploaded, self.deleted, self.created, self._b = {}, [], [], {}
        self.files = SimpleNamespace(create=self._fcreate, content=self._fcontent,
                                     delete=self._fdelete)
        self.batches = SimpleNamespace(create=self._bcreate, retrieve=self._bretrieve,
                                       list=self._blist)

    async def _fcreate(self, file, purpose):
        fid = f"file-{len(self.uploaded)}"
        self.uploaded[fid] = file[1].decode("utf-8")
        return SimpleNamespace(id=fid)

    async def _fcontent(self, fid):
        return SimpleNamespace(text=self.uploaded[fid])

    async def _fdelete(self, fid):
        self.deleted.append(fid)

    def lines(self, fid):
        return [json.loads(x) for x in self.uploaded[fid].splitlines() if x.strip()]

    async def _bcreate(self, input_file_id, endpoint, completion_window, metadata):
        assert endpoint == "/v1/chat/completions" and completion_window == "24h"
        bid = f"batch-{len(self._b)}"
        self._b[bid] = {"input": input_file_id, "status": "in_progress", "created_at": int(time.time())}
        self.created.append((bid, [l["custom_id"] for l in self.lines(input_file_id)]))
        return SimpleNamespace(id=bid, status="in_progress", errors=None)

    async def _blist(self, limit=20):
        for bid in reversed(list(self._b)):
            b = self._b[bid]
            yield SimpleNamespace(id=bid, status=b["status"], input_file_id=b["input"],
                                  created_at=b["created_at"])

    async def _bretrieve(self, bid):
        b = self._b[bid]
        if b["status"] == "in_progress":
            out = []
            for line in self.lines(b["input"]):
                text, finish = self.reply(line["custom_id"])
                out.append(json.dumps({"custom_id": line["custom_id"], "error": None, "response": {
                    "status_code": 200, "body": {
                        "choices": [{"message": {"content": text}, "finish_reason": finish}],
                        "usage": {"prompt_tokens": self.pt, "completion_tokens": self.ct}}}}))
            ofid = f"file-out-{bid}"
            self.uploaded[ofid] = "\n".join(out) + "\n"
            b.update(status="completed", output_file_id=ofid)
        return SimpleNamespace(id=bid, status=b["status"], errors=None, input_file_id=b["input"],
                               output_file_id=b.get("output_file_id"), error_file_id=None,
                               request_counts=SimpleNamespace(completed=0, total=0))


@pytest.fixture
def run_dirs(tmp_path):
    responses = tmp_path / "responses"
    for stem in ("altruist", "robot"):
        write_responses(responses, stem)
    return responses, tmp_path / "judged"


def judge(monkeypatch, run_dirs, client, *extra, roles=("altruist", "robot")):
    responses, out = run_dirs
    if client is not None:
        monkeypatch.setattr(exp, "make_client", lambda: client)
    return exp.main(["judge", "--responses-dir", str(responses), "--out-dir", str(out),
                     "--roles", *roles, "--batch-poll-seconds", "0", "--allow-dirty",
                     "--tokenizer", "chars", *extra])


# ---------------------------------------------------------------------------
# Settings pinned to step 3 and step 4
# ---------------------------------------------------------------------------

class TestSettings:
    def test_the_judge_request_is_step_3s(self):
        src = (REPO / "pipeline" / "3_judge.py").read_text()
        assert re.search(r'"--judge_model", type=str, default="([^"]+)"', src).group(1) == exp.JUDGE_MODEL
        assert int(re.search(r'"--max_tokens", type=int, default=(\d+)', src).group(1)) == exp.MAX_TOKENS
        body = exp.request_body("hello")
        assert body == {"model": "gpt-4.1-mini", "messages": [{"role": "user", "content": "hello"}],
                        "max_completion_tokens": 200}            # no temperature: the default
        assert exp.CUSTOM_ID_SEP == exp.step3().CUSTOM_ID_SEP

    def test_min_count_is_the_drivers_for_roles(self):
        src = (REPO / "pipeline" / "run_pipeline.sh").read_text()
        assert int(re.search(r"^MIN_COUNT=(\d+)", src, re.M).group(1)) == exp.DEFAULT_MIN_COUNT

    def test_the_sample(self):
        assert len(exp.SAMPLE) == 30 and len(set(exp.SAMPLE)) == 30
        assert [len(v) for v in exp.SAMPLE_STRATA.values()] == [5, 9, 8, 8]
        assert exp.AI_PERSONA_ROLES == ("instrumentally_aligned_ai", "assistant", "cyborg",
                                        "paperclip_maximizer", "robot")
        assert all((ROLES / f"{r}.json").exists() for r in exp.SAMPLE)
        assert set(exp.RENDER_ROLES) <= set(exp.SAMPLE)

    def test_custom_ids_round_trip(self):
        cid = exp.make_cid("A0b", "instrumentally_aligned_ai", "pos_p4_q239")
        assert exp.parse_cid(cid) == ("A0b", "instrumentally_aligned_ai", "pos_p4_q239")
        for bad in ("patient|pos_p0_q0", "Z9|robot|pos_p0_q0", "A1||k"):
            with pytest.raises(ValueError):
                exp.parse_cid(bad)

    def test_model_short_name(self, tmp_path):
        assert exp.model_short_name("Qwen/Qwen3-32B") == "Qwen"
        assert exp.model_short_name("meta-llama/Llama-3.3-70B-Instruct") == "Llama"
        assert exp.resolve_model_name(None, tmp_path)[0] == "Qwen"
        (tmp_path / "generation_config.json").write_text(json.dumps(
            {"schema": 1, "runs": [{"model_name": "Qwen/Qwen3-32B"}, {"model_name": "google/gemma-2-27b-it"}]}))
        assert exp.resolve_model_name(None, tmp_path)[0] == "gemma"
        assert exp.resolve_model_name("Olmo", tmp_path) == ("Olmo", "--model-name")


# ---------------------------------------------------------------------------
# The arms, on the real role files
# ---------------------------------------------------------------------------

def _levels(text: str) -> dict:
    return {int(line[2]): line for line in text.split("\n") if re.match(r"- [0-3] if ", line)}


def _rest(text: str) -> list:
    return [line for line in text.split("\n") if not re.match(r"- [0-3] if ", line)]


EXPECTED_LEVELS = {"A0b": set(), "A1": {0, 1, 2}, "A2": {0, 1, 2}, "A3": {2}, "A4": {2},
                   "A5": {0, 1, 2}, "A6": {0, 3}, "A7": {0, 1, 2}}


class TestArms:
    def test_a0_is_the_template_for_every_sampled_role(self):
        assert exp.template_mismatches(exp.SAMPLE) == []

    def test_a0_is_what_step_3_sends(self):
        j3 = exp.step3()
        for stem in exp.SAMPLE:
            baked = json.loads((ROLES / f"{stem}.json").read_text())["eval_prompt"]
            assert j3.resolve_eval_prompt(stem, ROLES, TRAITS, "role") == baked
            assert exp.arm_template("A0", baked) == baked == exp.arm_template("A0b", baked)

    @pytest.mark.parametrize("stem", exp.SAMPLE)
    def test_each_arm_changes_only_what_it_should(self, stem):
        baked = json.loads((ROLES / f"{stem}.json").read_text())["eval_prompt"]
        base_levels, base_rest = _levels(baked), _rest(baked)
        assert set(base_levels) == {0, 1, 2, 3}
        for arm, levels in EXPECTED_LEVELS.items():
            t = exp.arm_template(arm, baked)
            got = {lvl for lvl in range(4) if _levels(t)[lvl] != base_levels[lvl]}
            assert got == levels, (stem, arm)
            if arm == "A7":
                added = [l for l in difflib.ndiff(base_rest, _rest(t)) if l.startswith(("+ ", "- "))]
                assert sorted(added) == sorted(["+ " + exp.A7_ROLE_SENTENCE, "+ "]), (stem, added)
            else:
                assert _rest(t) == base_rest, (stem, arm)

    @pytest.mark.parametrize("stem", exp.SAMPLE)
    def test_the_specific_edits(self, stem):
        baked = json.loads((ROLES / f"{stem}.json").read_text())["eval_prompt"]
        t = {arm: exp.arm_template(arm, baked) for arm in exp.ARM_IDS}
        name = exp.role_name_in(baked)
        assert baked.count("Gemma") == 3 and exp.TYPO in baked
        for arm in exp.ARM_IDS:                           # the typo: fixed in A1, A2, A5 only
            assert (exp.TYPO in t[arm]) == (arm not in ("A1", "A2", "A5")), arm
            assert "((" not in t[arm] or arm not in ("A1", "A2", "A5")
        assert "Gemma" not in t["A1"] and t["A1"].count(exp.A1_PAREN) == 3
        assert "Gemma" not in t["A2"] and t["A2"].count("(an AI assistant, Qwen, an LLM, etc.)") == 3
        assert "Gemma" not in t["A5"] and t["A5"].count(exp.A1_PAREN) == 3
        for arm in ("A3", "A4", "A5"):
            assert exp.LEVEL2_EXAMPLE not in t[arm]
        assert exp.A3_EXAMPLE in t["A3"] and exp.A3_EXAMPLE in t["A5"]
        assert f"(e.g. {name}-like AI for the role {name})" in t["A4"]
        assert exp.LEVEL0_REFUSAL_CLAUSE not in t["A6"] and exp.LEVEL3_REFUSAL_CLAUSE not in t["A6"]
        assert t["A6"].count(exp.A6_LEVEL3_REFUSAL.strip()) == 1
        assert "identifies as itself" not in t["A7"]
        assert t["A7"].count("rather than as the role") == 3 and exp.A7_ROLE_SENTENCE in t["A7"]
        for arm in ("A0", "A0b", "A3", "A4", "A6", "A7"):
            assert t[arm].count("Gemma") == 3, arm

    @pytest.mark.parametrize("stem", exp.SAMPLE)
    def test_every_arm_ends_with_the_score_marker_line_and_fills_as_step_3_does(self, stem):
        j3 = exp.step3()
        baked = json.loads((ROLES / f"{stem}.json").read_text())["eval_prompt"]
        for arm in exp.ARM_IDS:
            t = exp.arm_template(arm, baked)
            assert t.endswith("Then on a new line, write exactly: SCORE: <integer from 0 to 3>")
            assert t.count("SCORE:") == 1
            [(key, prompt)] = j3.pending_prompts([_response(0, 7, "Some {braces} {answer}")], t, {})
            assert key == "pos_p0_q7"
            assert prompt == t.replace("{question}", "Question number 7?").replace(
                "{answer}", "Some {braces} {answer}")

    def test_an_arm_refuses_text_it_cannot_change(self):
        baked = json.loads((ROLES / "robot.json").read_text())["eval_prompt"]
        with pytest.raises(exp.ArmError, match="doubled parenthesis"):
            exp.arm_template("A1", baked.replace(exp.TYPO, exp.TYPO[1:]))
        with pytest.raises(exp.ArmError, match="level-2 example"):
            exp.arm_template("A3", baked.replace(exp.LEVEL2_EXAMPLE, ""))
        with pytest.raises(exp.ArmError):
            exp.arm_template("A6", baked.replace(exp.LEVEL0_REFUSAL_CLAUSE, ""))
        with pytest.raises(ValueError, match="unknown arm"):
            exp.arm_template("A9", baked)

    def test_a2_takes_the_model_name(self):
        baked = json.loads((ROLES / "robot.json").read_text())["eval_prompt"]
        t = exp.arm_template("A2", baked, model_name="Llama {x}")
        assert "(an AI assistant, Llama {{x}}, an LLM, etc.)" in t     # braces kept literal
        assert "Llama {x}" in t.format(question="q", answer="a")


# ---------------------------------------------------------------------------
# Estimate, dry run
# ---------------------------------------------------------------------------

def test_estimate_counts_every_request(run_dirs):
    responses, _ = run_dirs
    plan = exp.build_plan(["altruist", "robot"], exp.ARM_IDS, responses_dir=responses)
    counter = exp.TokenCounter("chars")
    est = exp.estimate_plan(plan, exp.ARM_IDS, counter=counter)
    assert est["total"]["calls"] == 9 * 2 * 4
    assert est["per_arm"]["A0"] == est["per_arm"]["A0b"]
    tok = sum(math.ceil(len(p) / 4) + exp.CHAT_OVERHEAD_TOKENS
              for rp in plan for _, p in exp.filled_prompts(rp, "A7", {}))
    assert est["per_arm"]["A7"]["prompt_tokens"] == tok
    rin, rout = exp.batch_prices()
    assert (rin, rout) == (0.2, 0.8)
    d = est["per_arm"]["A7"]
    assert d["usd"] == pytest.approx(tok * rin / 1e6 + 8 * exp.OUTPUT_TOKENS_PER_CALL * rout / 1e6)
    assert est["token_method"] == "chars/4" and not est["over_flag"]


def test_the_may_alias_is_followed(tmp_path):
    write_responses(tmp_path, "aligned_artificial_intelligence", 3)
    [rp] = exp.build_plan(["instrumentally_aligned_ai"], ["A0"], responses_dir=tmp_path)
    assert rp.responses_path.name == "aligned_artificial_intelligence.jsonl" and len(rp.responses) == 3


def test_dry_run_builds_and_counts_and_submits_nothing(monkeypatch, run_dirs):
    responses, out = run_dirs
    assert judge(monkeypatch, run_dirs, None, "--dry-run") == 0      # make_client would raise
    summary = json.loads((out / "dry_run" / "summary.json").read_text())
    assert summary["total_requests"] == 72 and summary["per_arm"]["A7"] == 8
    lines = [json.loads(l) for l in (out / "dry_run" / "requests_sample.jsonl").read_text().splitlines()]
    assert {exp.parse_cid(l["custom_id"])[0] for l in lines} == set(exp.ARM_IDS)
    for l in lines:
        arm, role, key = exp.parse_cid(l["custom_id"])
        assert l["body"] == exp.request_body(l["body"]["messages"][0]["content"])
        baked = json.loads((ROLES / f"{role}.json").read_text())["eval_prompt"]
        assert l["body"]["messages"][0]["content"].startswith(exp.arm_template(arm, baked)[:200])
    assert not (out / "batch_state.json").exists() and not (out / "A0").exists()


# ---------------------------------------------------------------------------
# judge, live with a fake batch client
# ---------------------------------------------------------------------------

def test_judge_writes_step_3_score_files_usage_and_the_record(monkeypatch, run_dirs):
    responses, out = run_dirs
    client = FakeBatchClient()
    assert judge(monkeypatch, run_dirs, client, "--batch-requests", "8") == 0
    keys = {f"pos_p{i % 2}_q{i}" for i in range(4)}
    for arm in exp.ARM_IDS:
        for role in ("altruist", "robot"):
            assert json.loads((out / arm / f"{role}.json").read_text()) == {k: 3 for k in keys}
        u = json.loads((out / arm / "usage.json").read_text())
        assert u["n_calls"] == 8 and set(u["per_model"]) == {"gpt-4.1-mini:batch"}
    total = json.loads((out / "usage.json").read_text())
    assert total["n_calls"] == 72 and total["total_prompt_tokens"] == 7200
    # every batch holds one arm: A0 and A0' never share one
    assert all(len({exp.parse_cid(c)[0] for c in cids}) == 1 for _, cids in client.created)
    # the requests are step 3's, with each arm's template filled
    for fid in [f for f in client.uploaded if not f.startswith("file-out")]:
        for line in client.lines(fid):
            arm, role, key = exp.parse_cid(line["custom_id"])
            baked = json.loads((ROLES / f"{role}.json").read_text())["eval_prompt"]
            q = int(key.rsplit("_q", 1)[1])
            r = _response(q % 2, q)
            prompt = exp.arm_template(arm, baked).format(question=r["question"],
                                                         answer=r["conversation"][2]["content"])
            assert line["body"] == exp.request_body(prompt)
    rec = json.loads((out / "run_record.json").read_text())
    assert rec["judge"]["model"] == "gpt-4.1-mini" and rec["judge"]["max_completion_tokens"] == 200
    assert {b["batch_id"] for b in rec["batches"]} == {bid for bid, _ in client.created}
    assert all(b["status"] == "completed" for b in rec["batches"])
    assert set(rec["arms"]) == set(exp.ARM_IDS)
    assert rec["arms"]["A0"]["template_sha256"] == rec["arms"]["A0b"]["template_sha256"]
    assert rec["arms"]["A1"]["template_sha256"]["robot"] != rec["arms"]["A0"]["template_sha256"]["robot"]
    assert rec["responses"]["files"]["robot"]["n_used"] == 4
    assert rec["runs"][-1]["counts"]["A3"]["parsed"] == 8
    replies = exp.read_replies(out, "A3", "robot")
    assert set(replies) == keys and all(r["score"] == 3 for r in replies.values())

    # nothing left to judge: a second run submits nothing
    n = len(client.created)
    assert judge(monkeypatch, run_dirs, client) == 0
    assert len(client.created) == n
    assert json.loads((out / "usage.json").read_text())["n_calls"] == 72


def test_submit_now_collect_later(monkeypatch, run_dirs):
    responses, out = run_dirs
    client = FakeBatchClient()
    assert judge(monkeypatch, run_dirs, client, "--batch-no-wait", "--batch-requests", "20") == 0
    n_batches = len(client.created)
    assert n_batches == 4 and not (out / "A0").exists()          # submitted, nothing collected
    state = json.loads((out / "batch_state.json").read_text())
    assert all(r.get("batch_id") and not r.get("collected") for r in state["chunks"])
    rec = json.loads((out / "run_record.json").read_text())
    assert rec["runs"][-1]["submitted"] == [bid for bid, _ in client.created]

    # the cost gate of a later run does not count what is in flight
    assert exp.inflight_ids_on_disk(out) == {c for _, cids in client.created for c in cids}

    assert judge(monkeypatch, run_dirs, client, "--collect-only") == 0
    assert len(client.created) == n_batches                      # collected, nothing resubmitted
    assert len(json.loads((out / "A7" / "robot.json").read_text())) == 4
    assert json.loads((out / "usage.json").read_text())["n_calls"] == 72
    assert judge(monkeypatch, run_dirs, client) == 0               # and nothing left after
    assert len(client.created) == n_batches


def test_collect_by_batch_id_after_the_state_file_is_lost(monkeypatch, run_dirs):
    responses, out = run_dirs
    client = FakeBatchClient()
    assert judge(monkeypatch, run_dirs, client, "--batch-no-wait", "--batch-requests", "40") == 0
    ids = [bid for bid, _ in client.created]
    (out / "batch_state.json").unlink()
    for p in (out / "_batches").glob("*"):
        p.unlink()
    extra = [x for bid in ids for x in ("--batch-id", bid)]
    assert judge(monkeypatch, run_dirs, client, "--collect-only", *extra) == 0
    assert len(client.created) == len(ids)
    assert json.loads((out / "usage.json").read_text())["n_calls"] == 72
    for arm in exp.ARM_IDS:
        assert len(json.loads((out / arm / "altruist.json").read_text())) == 4


def test_an_unparseable_arm_is_loud_and_not_paid_for_twice(monkeypatch, run_dirs, caplog):
    responses, out = run_dirs

    def reply(cid):
        arm = exp.parse_cid(cid)[0]
        if arm == "A3":
            return "The response plays the role; I would give it 3.", "stop"     # no marker
        if arm == "A6":
            return "The response plays the role, and so", "length"               # cut at max_tokens
        return "Reasoning.\nSCORE: 2", "stop"
    client = FakeBatchClient(reply)
    assert judge(monkeypatch, run_dirs, client) == 1
    assert "*** HIGH FAIL RATE *** [role_rubric_experiment:A3:gpt-4.1-mini]" in caplog.text
    assert not (out / "A3" / "robot.json").exists() or json.loads((out / "A3" / "robot.json").read_text()) == {}
    problems = {r["problem"] for r in exp.read_replies(out, "A3", "robot").values()}
    assert problems == {"no_marker"}
    assert {r["problem"] for r in exp.read_replies(out, "A6", "robot").values()} == {"truncated"}
    rec = json.loads((out / "run_record.json").read_text())
    assert rec["runs"][-1]["counts"]["A3"]["problem:no_marker"] == 8
    assert any("A3 parse rate 0/8" in r for r in rec["runs"][-1]["incomplete"])

    # a rerun does not request the unparseable replies again (they were paid for) ...
    n = len(client.created)
    judge(monkeypatch, run_dirs, client)
    assert len(client.created) == n
    # ... unless asked to, and then only those
    client.reply = lambda cid: ("Reasoning.\nSCORE: 3", "stop")
    assert judge(monkeypatch, run_dirs, client, "--rejudge-unparseable") == 0
    sent = [c for _, cids in client.created[n:] for c in cids]
    assert {exp.parse_cid(c)[0] for c in sent} == {"A3", "A6"} and len(sent) == 16
    assert json.loads((out / "A3" / "robot.json").read_text()) == {
        f"pos_p{i % 2}_q{i}": 3 for i in range(4)}
    assert json.loads((out / "usage.json").read_text())["n_calls"] == 72 + 16


def test_a_batch_collected_twice_is_charged_once(tmp_path):
    out = tmp_path / "judged"
    col = exp.Collector(out, exp.ARM_IDS)
    body = {"choices": [{"message": {"content": "R.\nSCORE: 3"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 5}}
    col.on_result("A1|robot|pos_p0_q0", body, None)
    col.flush()
    again = exp.Collector(out, exp.ARM_IDS)
    again.on_result("A1|robot|pos_p0_q0", body, None)                 # the same reply again
    again.flush()
    assert again.counts["A1"]["recollected"] == 1 and again.run_total.n_calls == 0
    other = {"choices": [{"message": {"content": "Other.\nSCORE: 1"}, "finish_reason": "stop"}],
             "usage": {"prompt_tokens": 50, "completion_tokens": 6}}
    again.on_result("A1|robot|pos_p0_q0", other, None)                 # a duplicate request
    again.flush()
    assert again.counts["A1"]["duplicate"] == 1 and again.run_total.n_calls == 1
    assert json.loads((out / "A1" / "robot.json").read_text()) == {"pos_p0_q0": 3}
    assert json.loads((out / "usage.json").read_text())["n_calls"] == 2


def test_a_changed_wording_or_response_file_is_refused(monkeypatch, run_dirs):
    responses, out = run_dirs
    client = FakeBatchClient()
    assert judge(monkeypatch, run_dirs, client, "--arms", "A0", "A1") == 0
    rec = json.loads((out / "run_record.json").read_text())
    rec["arms"]["A1"]["template_sha256"]["robot"] = "0" * 64
    (out / "run_record.json").write_text(json.dumps(rec))
    n = len(client.created)
    assert judge(monkeypatch, run_dirs, client, "--arms", "A0", "A1") == 2
    assert judge(monkeypatch, run_dirs, client, "--dry-run") == 2
    rec["arms"]["A1"]["template_sha256"]["robot"] = exp.template_sha256(exp.arm_template(
        "A1", json.loads((ROLES / "robot.json").read_text())["eval_prompt"]))
    (out / "run_record.json").write_text(json.dumps(rec))
    with open(responses / "robot.jsonl", "a") as f:
        f.write(json.dumps(_response(1, 9)) + "\n")
    assert judge(monkeypatch, run_dirs, client, "--arms", "A0", "A1") == 2
    assert len(client.created) == n


def test_the_cost_gate(monkeypatch, run_dirs):
    client = FakeBatchClient()
    monkeypatch.setattr(exp, "CONFIRM_ABOVE_USD", 0.0)
    assert judge(monkeypatch, run_dirs, client) == 2 and not client.created
    assert judge(monkeypatch, run_dirs, client, "--confirm-expensive", "--budget-usd", "0") == 2
    assert not client.created
    assert judge(monkeypatch, run_dirs, client, "--confirm-expensive") == 0 and client.created


# ---------------------------------------------------------------------------
# analyze-scores: flips, the noise floor, the blind sheet
# ---------------------------------------------------------------------------

def test_compare_scores_counts_flips_by_direction():
    base = {"a": 3, "b": 2, "c": 3, "d": 1}
    other = {"a": 3, "b": 3, "c": 2, "d": 2, "e": 3}
    assert exp.compare_scores(base, other) == {"n": 4, "changed": 3, "boundary": 2, "down": 1,
                                               "up": 1, "base_3": 2, "other_3": 2}
    assert exp.boundary_flips(base, other) == ["b", "c"]


def _scores_fixture():
    keys = [f"pos_p0_q{q}" for q in range(10)]
    a0 = {"robot": {k: (3 if i < 6 else 2) for i, k in enumerate(keys)},
          "altruist": {k: (3 if i < 5 else 1) for i, k in enumerate(keys)}}
    a0b = {"robot": dict(a0["robot"], pos_p0_q0=2),                      # one flip down
           "altruist": dict(a0["altruist"])}                             # none
    a7 = {"robot": {k: 3 for k in keys},                                 # four up
          "altruist": dict(a0["altruist"], pos_p0_q9=3, pos_p0_q0=2)}    # one up, one down
    return {"A0": a0, "A0b": a0b, "A7": a7}


def test_the_noise_floor_and_an_arm_against_it():
    an = exp.score_analysis(_scores_fixture(), ["robot", "altruist"])
    noise = an["noise_floor"]["pooled"]
    assert noise["n"] == 20 and noise["boundary"] == 1 and noise["changed_share"] == pytest.approx(0.05)
    assert an["noise_floor"]["per_role_boundary_share"] == {"min": 0.0, "median": 0.05, "max": 0.1}
    c = an["comparisons"]["A7"]
    assert (c["pooled"]["down"], c["pooled"]["up"]) == (1, 5)
    assert c["ai_persona"]["boundary"] == 4 and c["other_roles"]["boundary"] == 2
    assert c["vs_noise"]["boundary_share_ratio"] == pytest.approx(6.0)
    assert c["vs_noise"]["roles_above_noise"] == 2
    assert {d["question_index"]: (d["down"], d["up"]) for d in c["by_question"]}[0] == (1, 0)
    assert an["score3_counts"]["A7"] == {"robot": 10, "altruist": 5}
    assert an["levels_a0"]["altruist"] == {0: 0.0, 1: 0.5, 2: 0.0, 3: 0.5}


def _write_scores(out: Path, scores) -> None:
    for arm, by_role in scores.items():
        for role, s in by_role.items():
            (out / arm).mkdir(parents=True, exist_ok=True)
            (out / arm / f"{role}.json").write_text(json.dumps(s))


def test_the_reading_sheet_is_blind_and_its_key_maps_back(tmp_path):
    scores = _scores_fixture()
    judged, responses, report = tmp_path / "judged", tmp_path / "responses", tmp_path / "report"
    _write_scores(judged, scores)
    for role in ("robot", "altruist"):
        write_responses(responses, role, 10, prompts=1)
    assert exp.main(["analyze-scores", "--scores-dir", str(judged), "--responses-dir", str(responses),
                     "--report-dir", str(report), "--roles", "robot", "altruist",
                     "--sheet-page-size", "3"]) == 0
    key = json.loads((report / exp.SHEET_KEY_NAME).read_text())
    pages = sorted((report / "reading_sheet").glob("page_*.md"))
    assert len(key["items"]) == 1 + 6 and len(pages) == 3          # A0' 1 flip, A7 6 flips
    text = "\n".join(p.read_text() for p in pages)
    assert not re.search(r"\bA\d", text) and "A0'" not in text
    for arm in exp.ARMS:
        assert arm.summary not in text
    assert "underlying assistant" not in text and "noise" not in text
    # each item shows its two scores, X and Y as the key says, and the mark line comes first
    blocks = re.split(r"^### (\d+)\s*$", text, flags=re.M)[1:]
    for item, block in zip(blocks[::2], blocks[1::2]):
        k = key["items"][item]
        x, y = map(int, re.search(r"\*\*X: (\d) · Y: (\d)\*\*", block).groups())
        assert (x, y) == ((k["a0_score"], k["arm_score"]) if k["x_is"] == "A0"
                          else (k["arm_score"], k["a0_score"]))
        assert {x, y} & {3} and min(x, y) < 3
        assert block.strip().splitlines()[0].strip() == "mark:"
        r = exp.question_index(k["key"])
        assert f"**Question**: Question number {r}?" in block and f"q{r}." in block
    # marks: everything marked X, then tallied against the key
    for p in pages:
        p.write_text(p.read_text().replace("\nmark: \n", "\nmark: X fine\n"))
    assert exp.main(["read-marks", "--report-dir", str(report)]) == 0
    res = json.loads((report / "reading_results.json").read_text())["per_arm"]
    want_arm = sum(1 for k in key["items"].values() if k["arm"] == "A7" and k["x_is"] == "arm")
    assert res["A7"]["arm_right"] == want_arm and res["A7"]["a0_right"] == 6 - want_arm
    assert res["A0b"]["arm_right"] + res["A0b"]["a0_right"] == 1
    # a marked sheet is not overwritten by a rerun, unless asked (and then it is kept aside)
    argv = ["analyze-scores", "--scores-dir", str(judged), "--responses-dir", str(responses),
            "--report-dir", str(report), "--roles", "robot", "altruist"]
    assert exp.main(argv) == 2
    assert exp.main(argv + ["--overwrite-sheet"]) == 0
    backups = list(report.glob("reading_sheet.bak.*"))
    assert len(backups) == 1 and (backups[0] / exp.SHEET_KEY_NAME).exists()
    md = (report / "score_analysis.md").read_text()
    assert "[robot](" in md and "Mark the reading sheet before reading further" in md
    env = json.loads((report / "score_analysis.json").read_text())
    assert env["result"]["comparisons"]["A7"]["pooled"]["up"] == 5


def test_the_sheet_is_stratified_across_roles():
    scores = _scores_fixture()
    items, key = exp.build_reading_sheet(scores, ["robot", "altruist"], per_arm=2)
    a7 = [k for k in key["items"].values() if k["arm"] == "A7"]
    assert len(a7) == 2 and {k["role"] for k in a7} == {"robot", "altruist"}
    again, _ = exp.build_reading_sheet(scores, ["robot", "altruist"], per_arm=2)
    assert again == items                                            # seeded


def test_parse_marks(tmp_path):
    page = tmp_path / "page_01.md"
    page.write_text("# t\n\n**Marks**: `mark:` lines\n\n### 1\n\nmark: y because\n\n> ### 2\n> mark: X\n"
                    "\n### 2\n\nmark:\n\n### 3\nmark: ?\n")
    assert exp.parse_marks([page]) == {"1": "Y", "2": "", "3": "?"}


# ---------------------------------------------------------------------------
# analyze-vectors: step 4's computation on tiny tensors, centred comparison
# ---------------------------------------------------------------------------

def test_vectors_are_step_4s_and_cosines_are_per_slot_and_layer(tmp_path):
    import torch
    torch.manual_seed(0)
    keys = [f"pos_p0_q{q}" for q in range(6)]
    acts = {k: torch.randn(2, 3, 4).to(torch.bfloat16) for k in keys}
    act_dir, judged = tmp_path / "activations", tmp_path / "judged"
    act_dir.mkdir()
    torch.save({**acts, "metadata": {"model": "fake"}}, act_dir / "robot.pt")
    scores = {"A0": {k: (3 if i < 4 else 2) for i, k in enumerate(keys)},
              "A0b": {k: (3 if i < 3 else 2) for i, k in enumerate(keys)},
              "A1": {k: (3 if 1 <= i < 5 else 1) for i, k in enumerate(keys)},
              "A7": {k: (3 if i == 0 else 2) for i, k in enumerate(keys)}}
    for arm, s in scores.items():
        (judged / arm).mkdir(parents=True)
        (judged / arm / "robot.json").write_text(json.dumps(s))
    res = exp.analyze_vectors(act_dir, judged, ["robot"], ["A0", "A0b", "A1", "A7"], min_count=2)
    e = res["per_role"]["robot"]
    assert e["n_activations"] == 6
    assert e["arms"]["A7"]["status"] == "below_min_count" and e["arms"]["A7"]["n_score3"] == 1
    assert e["arms"]["A1"]["status"] == "ok" and e["arms"]["A1"]["n_score3"] == 4
    assert e["arms"]["A1"]["jaccard_score3_with_A0"] == pytest.approx(3 / 5)

    # A0's vector is what pipeline/4_vectors.py writes from the A0 score files
    j4 = exp.step4()
    assert j4.main(["--activations_dir", str(act_dir), "--scores_dir", str(judged / "A0"),
                    "--output_dir", str(tmp_path / "vec"), "--min_count", "2"]) == 0
    v_step4 = torch.load(tmp_path / "vec" / "robot.pt", weights_only=False)["vector"]
    v_a0 = j4.compute_pos_3_vector(acts, scores["A0"], 2)
    v_a1 = j4.compute_pos_3_vector(acts, scores["A1"], 2)
    assert torch.equal(v_step4, v_a0) and v_a0.dtype == torch.float32
    manual = torch.stack([acts[k].double() for k in keys[1:5]]).mean(0).float()
    assert torch.allclose(v_a1, manual, atol=1e-7, rtol=0)
    # the raw cosine (kept, marked as not informative), per slot and layer
    grid = e["arms"]["A1"]["raw_cos_with_A0"]
    assert len(grid) == 2 and len(grid[0]) == 3
    for s in range(2):
        for l in range(3):
            want = torch.nn.functional.cosine_similarity(v_a1[s, l].double(), v_a0[s, l].double(), dim=0)
            assert grid[s][l] == pytest.approx(float(want), abs=1e-12)
    assert e["arms"]["A1"]["raw_cos_with_A0_layer_mean"][1] == pytest.approx(sum(grid[1]) / 3)
    summ = res["summary"]["raw"]["ai_persona"]["A1"]["0"]
    noise = e["arms"]["A0b"]["raw_cos_with_A0_layer_mean"][0]
    assert summ["median_cos"] == pytest.approx(e["arms"]["A1"]["raw_cos_with_A0_layer_mean"][0])
    assert summ["median_ratio_to_noise"] == pytest.approx(
        (1 - e["arms"]["A1"]["raw_cos_with_A0_layer_mean"][0]) / (1 - noise))
    assert res["summary"]["raw"]["other_roles"]["A1"] == {}
    assert "not informative" in res["raw_cosine_note"].lower()
    # one role: the median reference is its own A0 vector, so there is no offset to compare
    assert res["references"]["median"]["n_roles"] == 1
    assert e["arms"]["A1"]["centred"]["median"]["cos_with_A0_layer_mean"] == [None, None]
    md = exp.vector_markdown(res, doc_dir=tmp_path)
    assert "## Median reference" in md and "below_min_count" in md
    assert "Omitted: no --default-vector was given." in md


def test_analyze_vectors_cli_writes_its_report(tmp_path):
    import torch
    acts = {f"pos_p0_q{q}": torch.randn(3, 4) for q in range(3)}        # 2-D: one slot
    act_dir, judged, report = tmp_path / "a", tmp_path / "j", tmp_path / "r"
    act_dir.mkdir()
    torch.save(acts, act_dir / "altruist.pt")
    for arm in ("A0", "A0b"):
        (judged / arm).mkdir(parents=True)
        (judged / arm / "altruist.json").write_text(json.dumps({k: 3 for k in acts}))
    assert exp.main(["analyze-vectors", "--activations-dir", str(act_dir), "--scores-dir", str(judged),
                     "--roles", "altruist", "--arms", "A0b", "--min-count", "1",
                     "--report-dir", str(report)]) == 0
    res = json.loads((report / "vector_analysis.json").read_text())
    assert res["per_role"]["altruist"]["arms"]["A0b"]["raw_cos_with_A0"][0] == pytest.approx([1.0] * 3)
    assert (report / "vector_analysis.md").exists()
    # the grids are written one row to a line
    text = (report / "vector_analysis.json").read_text()
    assert re.search(r'"raw_cos_with_A0": \[\s*\[[^\n\]]+\]\s*\]', text)


def test_elementwise_median():
    import statistics
    import torch
    nan = float("nan")
    ts = [torch.tensor([[1.0, 5.0, nan, nan]]), torch.tensor([[2.0, 7.0, 3.0, nan]]),
          torch.tensor([[4.0, 6.0, nan, nan]]), torch.tensor([[3.0, 8.0, nan, nan]])]
    med = exp.elementwise_median(ts)                     # 2-D in, 2-D out, float64
    assert med.dtype == torch.float64 and med.shape == (1, 4)
    assert med[0, :3].tolist() == [2.5, 6.5, 3.0]          # an even count: the two middle values' mean
    assert math.isnan(med[0, 3])                          # NaN everywhere stays NaN
    assert torch.median(torch.tensor([1.0, 2.0, 3.0, 4.0])) == 2.0   # (torch's own is the lower one)
    g = torch.Generator().manual_seed(3)
    ts = [torch.randn(2, 3, 5, generator=g) for _ in range(7)]
    med = exp.elementwise_median(ts)
    for idx in [(0, 0, 0), (1, 2, 4), (0, 1, 3)]:
        assert med[idx].item() == statistics.median(float(t[idx]) for t in ts)


ROLES4 = ("robot", "assistant", "altruist", "pirate")       # two AI-persona roles, two others
KEYS6 = [f"pos_p0_q{q}" for q in range(6)]


def _first(n_or_range):
    rng = range(n_or_range) if isinstance(n_or_range, int) else n_or_range
    return {k: (3 if i in rng else 2) for i, k in enumerate(KEYS6)}


def _scores4(a1_altruist=range(1, 5)):
    """A0: the first four responses of every role at 3.  A0': one fewer for robot and altruist.
    A1: equal to A0 except altruist (another four).  A7: below min_count (2) for robot."""
    a0 = {r: _first(4) for r in ROLES4}
    return {"A0": a0,
            "A0b": {**a0, "robot": _first(3), "altruist": _first(range(1, 4))},
            "A1": {**a0, "altruist": _first(a1_altruist)},
            "A7": {**a0, "robot": _first(1)}}


def _vector_inputs(tmp_path, scores, *, seed=0):
    import torch
    g = torch.Generator().manual_seed(seed)
    act_dir, judged = tmp_path / "activations", tmp_path / "judged"
    act_dir.mkdir(parents=True, exist_ok=True)
    acts = {}
    for role in ROLES4:
        acts[role] = {k: torch.randn(2, 3, 4, generator=g) for k in KEYS6}
        torch.save({**acts[role], "metadata": {"model": "fake"}}, act_dir / f"{role}.pt")
    _write_scores(judged, scores)
    return act_dir, judged, acts


def test_the_median_reference_is_the_a0_median_and_the_same_for_every_arm(tmp_path):
    import statistics
    import torch
    scores = _scores4()
    act_dir, judged, acts = _vector_inputs(tmp_path, scores)
    arms = ["A0", "A0b", "A1", "A7"]
    res = exp.analyze_vectors(act_dir, judged, list(ROLES4), arms, min_count=2)
    assert res["references"]["median"]["n_roles"] == 4
    assert res["references"]["default"] == {"omitted": exp.NO_DEFAULT_REASON}

    j4 = exp.step4()
    a0 = {r: j4.compute_pos_3_vector(acts[r], scores["A0"][r], 2) for r in ROLES4}
    flat = torch.stack([a0[r].double() for r in ROLES4]).reshape(4, -1)
    med = torch.tensor([statistics.median(flat[:, i].tolist()) for i in range(flat.shape[1])],
                       dtype=torch.float64).reshape(a0["robot"].shape)
    assert torch.equal(exp.elementwise_median(list(a0.values())), med)

    def centred(arm, role):
        v = j4.compute_pos_3_vector(acts[role], scores[arm][role], 2).double()
        return [[float(torch.nn.functional.cosine_similarity(v[s, l] - med[s, l],
                                                             a0[role][s, l].double() - med[s, l], dim=0))
                 for l in range(3)] for s in range(2)]

    for arm, role in (("A1", "altruist"), ("A0b", "robot"), ("A0b", "altruist")):
        got = res["per_role"][role]["arms"][arm]["centred"]["median"]["cos_with_A0"]
        want = centred(arm, role)
        for s in range(2):
            assert got[s] == pytest.approx(want[s], abs=1e-12)
        assert max(res["per_role"][role]["arms"][arm]["centred"]["median"]["cos_with_A0_layer_mean"]) < 1 - 1e-6

    # the same selection gives exactly 1 (and the same offset length); one role's change shows
    # in that role only
    for role in ("robot", "assistant", "pirate"):
        c = res["per_role"][role]["arms"]["A1"]["centred"]["median"]
        assert c["cos_with_A0_layer_mean"] == [1.0, 1.0] and c["norm_ratio_layer_mean"] == [1.0, 1.0]
    assert "centred" not in res["per_role"]["robot"]["arms"]["A7"]       # below min_count: left out
    moved = res["moved_roles"]["median"]["A1"]
    assert moved[0]["role"] == "altruist" and moved[0]["ratio_to_noise"] > 0
    assert {m["role"] for m in moved if m["ratio_to_noise"] is None} == {"assistant", "pirate"}

    # the summary: the median over roles of the layer means, (1 - cos) against A0' 's
    d = res["summary"]["median"]["all"]["A1"]["0"]
    assert d["n_roles"] == 4 and d["median_cos"] == 1.0
    alt = res["per_role"]["altruist"]["arms"]
    want = ((1 - alt["A1"]["centred"]["median"]["cos_with_A0_layer_mean"][0])
            / (1 - alt["A0b"]["centred"]["median"]["cos_with_A0_layer_mean"][0]))
    assert d["median_ratio_to_noise"] == pytest.approx(statistics.median([0.0, want]))
    assert res["summary"]["median"]["ai_persona"]["A1"]["0"]["n_roles"] == 2
    assert res["summary"]["median"]["a0_offset_fraction"]["0"] > 0

    # another A1 selection moves A1's numbers and nothing else: the reference is A0's alone
    act2, judged2, _ = _vector_inputs(tmp_path / "b", _scores4(a1_altruist=range(2, 6)))
    res2 = exp.analyze_vectors(act2, judged2, list(ROLES4), arms, min_count=2)
    for role in ROLES4:
        assert (res2["per_role"][role]["arms"]["A0b"]["centred"]
                == res["per_role"][role]["arms"]["A0b"]["centred"])
    assert (res2["per_role"]["altruist"]["arms"]["A1"]["centred"]
            != res["per_role"]["altruist"]["arms"]["A1"]["centred"])

    md = exp.vector_markdown(res, doc_dir=tmp_path)
    assert md.index("## Median reference") < md.index("## Default reference") < md.index("## Per role")
    assert "### All roles (4)" in md and "### The AI-persona roles (2)" in md
    assert "### The other roles (2)" in md and "×)" in md and "[altruist](" in md


def test_a_shared_offset_leaves_centred_cosines_unchanged_and_raw_ones_go_to_1():
    """Every role vector shares a large component, which is why raw cosines say nothing: add the
    same vector to every role vector (and to the default) and the centred cosines do not move,
    while the raw ones go to 1.  Integer-valued vectors keep every step exact."""
    import torch
    g = torch.Generator().manual_seed(1)
    arms = ("A0", "A0b", "A1")
    vecs = {(a, r): torch.randint(-4, 5, (2, 3, 6), generator=g).to(torch.float32)
            for a in arms for r in ROLES4}
    default = torch.randint(-4, 5, (2, 3, 6), generator=g).to(torch.float32)
    offset = torch.randint(-4, 5, (2, 3, 6), generator=g).to(torch.float32) * 250

    def run(shift):
        per_role = {r: {"arms": {a: {"status": "ok", "shape": [2, 3, 6]} for a in arms}} for r in ROLES4}
        comp = exp.compare_arm_vectors(per_role, lambda a, r: vecs[(a, r)] + shift, arms,
                                       default=(default + shift, {"source": "test", "shape": [2, 3, 6]}))
        return comp, per_role

    comp0, pr0 = run(torch.zeros(2, 3, 6))
    comp1, pr1 = run(offset)
    for r in ROLES4:
        for a in ("A0b", "A1"):
            i0, i1 = pr0[r]["arms"][a], pr1[r]["arms"][a]
            assert i1["centred"] == i0["centred"]                     # exactly
            for x0, x1 in zip(i0["raw_cos_with_A0_layer_mean"], i1["raw_cos_with_A0_layer_mean"]):
                assert x0 < x1 and x1 > 0.999
    for ref in ("median", "default"):
        s0, s1 = dict(comp0["summary"][ref]), dict(comp1["summary"][ref])
        f0, f1 = s0.pop("a0_offset_fraction"), s1.pop("a0_offset_fraction")
        assert s1 == s0
        assert all(f1[s] < f0[s] for s in f0)                       # the offset is a smaller part
        assert comp1["moved_roles"][ref] == comp0["moved_roles"][ref]
    assert comp1["summary"]["raw"] != comp0["summary"]["raw"]
    assert max(pr0[r]["arms"]["A1"]["centred"]["median"]["cos_with_A0_layer_mean"][0]
               for r in ROLES4) < 0.99                               # and they are informative


def _step4_default(tmp_path, shape=(2, 3, 4)):
    """A default vector written by pipeline/4_vectors.py (the mean of every activation)."""
    import torch
    d_act = tmp_path / "default_activations"
    d_act.mkdir()
    g = torch.Generator().manual_seed(7)
    torch.save({k: torch.randn(*shape, generator=g) for k in KEYS6}, d_act / "default.pt")
    assert exp.step4().main(["--activations_dir", str(d_act), "--scores_dir", str(tmp_path / "none"),
                             "--output_dir", str(tmp_path / "default_vec"), "--min_count", "1"]) == 0
    return tmp_path / "default_vec" / "default.pt"


def _cli(*argv):
    return exp.main(["analyze-vectors", *argv])


def test_the_default_reference_only_with_a_default_vector(tmp_path):
    import torch
    act_dir, judged, acts = _vector_inputs(tmp_path, _scores4())
    common = ["--scores-dir", str(judged), "--roles", *ROLES4, "--min-count", "2"]
    report = tmp_path / "r1"
    assert _cli("--activations-dir", str(act_dir), *common, "--report-dir", str(report)) == 0
    res = json.loads((report / "vector_analysis.json").read_text())
    assert res["references"]["default"] == {"omitted": exp.NO_DEFAULT_REASON}
    assert set(res["per_role"]["altruist"]["arms"]["A1"]["centred"]) == {"median"}
    assert "default" not in res["summary"] and "default" not in res["moved_roles"]
    md = (report / "vector_analysis.md").read_text()
    after = md.split("## Default reference", 1)[1].split("## Per role", 1)[0]
    assert after.strip() == "Omitted: no --default-vector was given."

    default = _step4_default(tmp_path)
    report = tmp_path / "r2"
    assert _cli("--activations-dir", str(act_dir), *common, "--report-dir", str(report),
                "--default-vector", str(default)) == 0
    res = json.loads((report / "vector_analysis.json").read_text())
    ref = res["references"]["default"]
    assert ref["role"] == "default" and ref["type"] == "mean" and ref["shape"] == [2, 3, 4]
    assert ref["file_sha256"] == exp._sha256_file(default)
    assert set(res["per_role"]["altruist"]["arms"]["A1"]["centred"]) == {"median", "default"}
    d = torch.load(default, weights_only=False)["vector"].double()
    v = exp.step4().compute_pos_3_vector(acts["altruist"], _scores4()["A1"]["altruist"], 2).double()
    b = exp.step4().compute_pos_3_vector(acts["altruist"], _scores4()["A0"]["altruist"], 2).double()
    want = float(torch.nn.functional.cosine_similarity(v[1, 2] - d[1, 2], b[1, 2] - d[1, 2], dim=0))
    got = res["per_role"]["altruist"]["arms"]["A1"]["centred"]["default"]["cos_with_A0"][1][2]
    assert got == pytest.approx(want, abs=1e-12)
    md = (report / "vector_analysis.md").read_text()
    after = md.split("## Default reference", 1)[1].split("## Per role", 1)[0]
    assert "### All roles (4)" in after and "Omitted" not in after

    bad = tmp_path / "bad_default.pt"
    torch.save({"vector": torch.zeros(3, 3, 4), "role": "default", "type": "mean"}, bad)
    assert _cli("--activations-dir", str(act_dir), *common, "--report-dir", str(tmp_path / "r3"),
                "--default-vector", str(bad)) == 2


def test_save_then_from_vectors_reproduces_the_numbers_exactly(tmp_path):
    import shutil
    import torch
    act_dir, judged, _ = _vector_inputs(tmp_path, _scores4())
    default = _step4_default(tmp_path)
    saved, r1, r2 = tmp_path / "arm_vectors", tmp_path / "r1", tmp_path / "r2"
    assert _cli("--activations-dir", str(act_dir), "--scores-dir", str(judged), "--roles", *ROLES4,
                "--min-count", "2", "--default-vector", str(default), "--save-vectors", str(saved),
                "--report-dir", str(r1)) == 0
    index = json.loads((saved / exp.VECTORS_INDEX_NAME).read_text())
    assert index["min_count"] == 2 and index["arms"] == list(exp.ARM_IDS)
    assert index["per_role"]["robot"]["arms"]["A0"]["n_score3"] == 4
    assert index["default_vector"]["source"] == str(default)
    assert len(index["scores_fingerprint"]) == 64
    assert not (saved / "A7" / "robot.pt").exists()                  # below min_count: no vector
    assert index["per_role"]["robot"]["arms"]["A7"]["status"] == "below_min_count"
    saved_v = torch.load(saved / "A1" / "altruist.pt", weights_only=False)
    assert saved_v["vector"].dtype == torch.float32 and saved_v["arm"] == "A1"

    # a copy elsewhere, without the activations, gives the same numbers
    copy_dir = tmp_path / "elsewhere" / "arm_vectors"
    shutil.copytree(saved, copy_dir)
    shutil.rmtree(act_dir)
    assert _cli("--from-vectors", str(copy_dir), "--scores-dir", str(judged),
                "--report-dir", str(r2)) == 0
    a = json.loads((r1 / "vector_analysis.json").read_text())
    b = json.loads((r2 / "vector_analysis.json").read_text())
    for key in ("per_role", "summary", "moved_roles", "references", "scores_fingerprint",
                "min_count", "reduce_questions", "arms", "roles"):
        assert a[key] == b[key], key
    assert b["vectors"]["source"] == "saved" and b["vectors"]["default_vector_from"].startswith("the saved copy")
    assert b["vectors"]["scores_check"].startswith("every score file unchanged")
    md_a = (r1 / "vector_analysis.md").read_text().split("## Median reference", 1)[1]
    md_b = (r2 / "vector_analysis.md").read_text().split("## Median reference", 1)[1]
    assert md_a == md_b

    # a subset of arms or roles is read from the same files
    assert _cli("--from-vectors", str(copy_dir), "--arms", "A0b", "A1", "--report-dir",
                str(tmp_path / "r3")) == 0
    c = json.loads((tmp_path / "r3" / "vector_analysis.json").read_text())
    assert c["arms"] == ["A0", "A0b", "A1"]
    assert c["per_role"]["altruist"]["arms"]["A1"] == a["per_role"]["altruist"]["arms"]["A1"]

    # refused: another min_count, a score file that changed, a damaged vector, no index
    assert _cli("--from-vectors", str(copy_dir), "--min-count", "3", "--report-dir", str(tmp_path / "x")) == 2
    (judged / "A1" / "altruist.json").write_text(json.dumps(_first(5)))
    assert _cli("--from-vectors", str(copy_dir), "--scores-dir", str(judged),
                "--report-dir", str(tmp_path / "x")) == 2
    assert _cli("--from-vectors", str(copy_dir), "--report-dir", str(tmp_path / "r4")) == 0   # unchecked
    torch.save({**saved_v, "vector": saved_v["vector"] + 1}, copy_dir / "A1" / "altruist.pt")
    assert _cli("--from-vectors", str(copy_dir), "--report-dir", str(tmp_path / "x")) == 2
    (copy_dir / exp.VECTORS_INDEX_NAME).unlink()
    assert _cli("--from-vectors", str(copy_dir), "--report-dir", str(tmp_path / "x")) == 2
    assert not (tmp_path / "x").exists()
    x = ["--report-dir", str(tmp_path / "x")]
    assert _cli("--from-vectors", str(saved), "--activations-dir", str(act_dir), *x) == 2
    assert _cli("--scores-dir", str(judged), *x) == 2                # neither source
    assert not (tmp_path / "x").exists()


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def test_render_shows_every_arm_as_the_judge_receives_it(tmp_path):
    responses, may = tmp_path / "responses", tmp_path / "may"
    write_responses(responses, "altruist", 3)
    write_responses(responses, "aligned_artificial_intelligence", 3)
    may.mkdir()
    (may / "altruist.json").write_text(json.dumps({"pos_p0_q0": 3, "pos_p1_q1": 2, "pos_p0_q2": 2}))
    doc_path = tmp_path / "doc" / "arm_wordings.md"
    text = exp.render_document(roles_dir=ROLES, responses_dir=responses, may_scores_dir=may,
                               model_name="Qwen", model_name_source="test", doc_path=doc_path)
    for arm in exp.ARMS:
        assert f"### {arm.label}\n" in text
    for arm in exp.COMPARED_ARMS[1:]:
        assert f"+++ {exp.ARM_BY_ID[arm].label}" in text
    assert "response `pos_p1_q1`" in text                     # altruist: the first May 2
    for stem, src in (("altruist", "altruist"), ("instrumentally_aligned_ai", "aligned_artificial_intelligence")):
        baked = json.loads((ROLES / f"{stem}.json").read_text())["eval_prompt"]
        r = _response(1, 1) if stem == "altruist" else _response(0, 0)
        for arm in exp.ARM_IDS:
            prompt = exp.arm_template(arm, baked).format(question=r["question"],
                                                         answer=r["conversation"][2]["content"])
            assert f"```text\n{prompt}\n```" in text, (stem, arm)
    assert "instrumentally-aligned AI-like AI" in text           # A4 for the AI role, shown
    assert "option B" in text and "f43af405" in text            # A6's reading
    assert "[altruist](" in text and "[instrumentally_aligned_ai](" in text
