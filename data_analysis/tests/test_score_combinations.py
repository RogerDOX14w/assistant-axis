"""score_combinations.py: the incongruity scorer is shown the judge display
form of the role and the trait (W19, RUBRIC_VERSION 2)."""

import json
from pathlib import Path

from data_analysis import score_combinations as module

TRAITS = Path(module.__file__).resolve().parent.parent / "data" / "traits" / "instructions"


def test_rubric_version():
    assert module.RUBRIC_VERSION == 2


def test_make_combo_carries_the_judge_labels():
    trait = json.loads((TRAITS / "careless_hexaco.json").read_text())
    combo = module._make_combo("devils_advocate", {"instruction": [{"pos": "r"}]},
                               "careless_hexaco", trait, "role")
    assert combo["role"] == "devils_advocate" and combo["trait"] == "careless_hexaco"
    assert combo["role_label"] == "devil's advocate"
    assert combo["trait_label"] == "careless (from HEXACO)"
    assert combo["output_name"] == "r_devils_advocate__careless_hexaco"


def test_user_message_shows_the_judge_form():
    combo = {"role": "devils_advocate", "trait": "enfj_mbti",
             "pairs": [{"role_instruction": "r", "trait_instruction": "t"}]}
    msg = module.build_user_message(combo)
    assert "Role: devil's advocate\nTrait: ENFJ (from the MBTI)\n" in msg
    combo.update(role_label="R LABEL", trait_label="T LABEL")
    assert "Role: R LABEL\nTrait: T LABEL\n" in module.build_user_message(combo)


def test_plain_names_are_unchanged():
    combo = {"role": "accountant", "trait": "patient",
             "pairs": [{"role_instruction": "r", "trait_instruction": "t"}]}
    assert "Role: accountant\nTrait: patient\n" in module.build_user_message(combo)


# ---------------------------------------------------------------------------
# 2026-10-10: Sonnet 5.5 escalating to Opus 5.5, batch by default, usage,
# scores kept only while their texts and model are unchanged
# ---------------------------------------------------------------------------

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def test_request_params_leave_temperature_out_for_5x_models():
    combo = {"role": "a", "trait": "b", "role_label": "a", "trait_label": "b",
             "pairs": [{"role_instruction": "r", "trait_instruction": "t"}]}
    for model in ("claude-sonnet-5-5", "claude-opus-5-5"):
        p = module.request_params(combo, model)
        assert "temperature" not in p and p["max_tokens"] == module.MAX_TOKENS_THINKING
    p = module.request_params(combo, "claude-sonnet-4-6", attempt=2)
    assert p["temperature"] == 0.2 and p["max_tokens"] == module.MAX_TOKENS
    assert p["messages"][0]["content"].endswith(module.RETRY_SUFFIX)


def test_response_text_skips_thinking_blocks():
    msg = SimpleNamespace(content=[SimpleNamespace(type="thinking", thinking="hmm"),
                                   SimpleNamespace(type="text", text=' [{"a": 1}] ')])
    assert module.response_text(msg) == '[{"a": 1}]'


def _combo(role="a", trait="b", pos="r"):
    c = {"role": role, "trait": trait, "role_label": role, "trait_label": trait,
         "goal_source": "role", "output_name": f"r_{role}__{trait}",
         "pairs": [{"role_instruction": pos, "trait_instruction": "t"}]}
    c["pairs_sha256"] = module.pairs_sha256(c)
    return c


def test_split_existing_keeps_only_current_texts_and_model():
    same, changed, other_model = _combo("a"), _combo("b"), _combo("c")
    stored = [
        {"output_name": same["output_name"], "pairs_sha256": same["pairs_sha256"], "first_model": "m"},
        {"output_name": changed["output_name"], "pairs_sha256": "old", "first_model": "m"},
        {"output_name": other_model["output_name"], "pairs_sha256": other_model["pairs_sha256"],
         "first_model": "claude-sonnet-4-20250514"},
        {"output_name": "r_gone__b", "pairs_sha256": "x", "first_model": "m"},
        {"output_name": "r_d__b", "per_pair": []},             # April 2026: no hash
    ]
    kept, pending, counts = module.split_existing(stored, [same, changed, other_model, _combo("d")], "m")
    assert [r["output_name"] for r in kept] == ["r_a__b"]
    assert [c["output_name"] for c in pending] == ["r_b__b", "r_c__b", "r_d__b"]
    assert counts == {"kept": 1, "stale_text": 2, "stale_model": 1, "dropped": 1}
    assert _combo("a", pos="r2")["pairs_sha256"] != same["pairs_sha256"]


class FakeAnthropic:
    """Messages and Message Batches.  The first model scores 2 for a
    combination of role ``ra`` (so it escalates), 0 otherwise; the rescore
    model scores 1.  Every reply carries a thinking block first."""

    def __init__(self, fail=()):
        self.fail = set(fail)
        self.created = []
        self.messages = SimpleNamespace(
            create=AsyncMock(side_effect=self._create),
            batches=SimpleNamespace(create=self._bcreate, retrieve=self._bretrieve,
                                    results=self._bresults))

    @staticmethod
    def _reply(params):
        user = params["messages"][0]["content"]
        n = user.count("Role instruction:")
        score = 1 if "opus" in params["model"] else (2 if "Role: ra" in user else 0)
        text = json.dumps([{"reasoning": "because", "score": score}] * n)
        return SimpleNamespace(stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=300),
                               content=[SimpleNamespace(type="thinking", thinking="..."),
                                        SimpleNamespace(type="text", text=text)])

    async def _create(self, **params):
        return self._reply(params)

    async def _bcreate(self, requests):
        bid = f"msgbatch_{len(self.created)}"
        self.created.append((bid, requests))
        return SimpleNamespace(id=bid)

    async def _bretrieve(self, bid):
        return SimpleNamespace(processing_status="ended", request_counts=SimpleNamespace(
            succeeded=0, errored=0, expired=0, processing=0))

    async def _bresults(self, bid):
        requests = dict(self.created)[bid]

        async def gen():
            for r in requests:
                if r["custom_id"] in self.fail:
                    yield SimpleNamespace(custom_id=r["custom_id"], result=SimpleNamespace(type="errored"))
                else:
                    yield SimpleNamespace(custom_id=r["custom_id"], result=SimpleNamespace(
                        type="succeeded", message=self._reply(r["params"])))
        return gen()


def _tree(tmp_path):
    roles, traits = tmp_path / "roles", tmp_path / "traits"
    roles.mkdir(); traits.mkdir()
    for stem in ("ra", "rb"):
        (roles / f"{stem}.json").write_text(json.dumps(
            {"description": "d", "instruction": [{"pos": f"{stem} one"}, {"pos": f"{stem} two"}]}))
    for stem in ("ta", "tb"):
        (traits / f"{stem}.json").write_text(json.dumps(
            {"positive_label": stem, "description": "d",
             "instruction": [{"pos": f"{stem} one", "neg": "x"}, {"pos": f"{stem} two", "neg": "x"}]}))
    goal = tmp_path / "goal.json"
    goal.write_text(json.dumps({"roles": {"goal": ["ra"], "non_goal": ["rb"]},
                                "traits": {"goal": ["ta"], "non_goal": ["tb"]}}))
    return roles, traits, goal


def _run_main(monkeypatch, tmp_path, client, *extra):
    roles, traits, goal = _tree(tmp_path) if not (tmp_path / "goal.json").exists() else (
        tmp_path / "roles", tmp_path / "traits", tmp_path / "goal.json")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda: client)
    out = tmp_path / "combination_scores.json"
    monkeypatch.setattr(sys, "argv", [
        "score_combinations.py", "--goal_file", str(goal), "--roles_dir", str(roles),
        "--traits_dir", str(traits), "--output", str(out), "--goal_count", "1",
        "--non_goal_count", "1", "--batch_poll_seconds", "0", *extra])
    asyncio.run(module.main_async())
    return out


def test_batch_is_the_default_with_a_rescore_stage(monkeypatch, tmp_path):
    client = FakeAnthropic()
    out = _run_main(monkeypatch, tmp_path, client)
    assert [len(reqs) for _, reqs in client.created] == [2, 3]       # first stage, then 3 rescores
    first, rescore = client.created
    assert {r["params"]["model"] for r in first[1]} == {"claude-sonnet-5-5"}
    assert {r["params"]["model"] for r in rescore[1]} == {"claude-opus-5-5"}
    assert sorted(r["custom_id"].split("-")[0] for r in rescore[1]) == ["r", "r1", "r2"]
    assert all("temperature" not in r["params"] for _, reqs in client.created for r in reqs)
    assert client.messages.create.call_count == 0

    data = json.loads(out.read_text())
    by = {r["output_name"]: r for r in data["scores"]}
    assert by["r_ra__tb"]["scored_by"] == "claude-opus-5-5"
    assert [p["score"] for p in by["r_ra__tb"]["per_pair"]] == [1, 1]
    assert by["r_ra__tb"]["rescore_samples"] == [[1, 1]] * 3
    assert data["metadata"]["rescore_samples"] == 3
    assert [p["score"] for p in by["r_ra__tb"]["sonnet_scores"]] == [2, 2]
    assert by["t_rb__ta"]["scored_by"] == by["t_rb__ta"]["first_model"] == "claude-sonnet-5-5"
    assert data["metadata"]["mode"] == "batch" and data["summary"]["escalated"] == 1

    usage = json.loads((tmp_path / "combination_scores_usage.json").read_text())
    assert set(usage["per_model"]) == {"claude-sonnet-5-5:batch", "claude-opus-5-5:batch"}
    log = json.loads((tmp_path / "combination_scores_batches.json").read_text())
    assert [e["stage"] for e in log] == ["first", "rescore"] and all("collected" in e for e in log)

    # A rerun keeps everything and submits nothing.
    _run_main(monkeypatch, tmp_path, client)
    assert len(client.created) == 2

    # A changed instruction makes that combination's score stale.
    p = tmp_path / "traits" / "ta.json"
    d = json.loads(p.read_text()); d["instruction"][0]["pos"] = "ta changed"; p.write_text(json.dumps(d))
    _run_main(monkeypatch, tmp_path, client)
    assert [len(reqs) for _, reqs in client.created] == [2, 3, 1]
    assert client.created[2][1][0]["custom_id"].startswith("f-t_rb__ta-")


def test_what_a_batch_does_not_deliver_is_scored_in_real_time(monkeypatch, tmp_path):
    _tree(tmp_path)
    combos = module.build_combinations(SimpleNamespace(
        goal_file=str(tmp_path / "goal.json"), roles_dir=str(tmp_path / "roles"),
        traits_dir=str(tmp_path / "traits"), goal_count=1, non_goal_count=1))
    t = next(c for c in combos if c["output_name"] == "t_rb__ta")
    client = FakeAnthropic(fail={module.batch_custom_id(t, "claude-sonnet-5-5", "first")})
    out = _run_main(monkeypatch, tmp_path, client)
    assert client.messages.create.call_count == 1
    assert len(json.loads(out.read_text())["scores"]) == 2
    usage = json.loads((tmp_path / "combination_scores_usage.json").read_text())
    assert usage["per_model"]["claude-sonnet-5-5"]["n_calls"] == 1


def test_batch_id_collects_without_submitting_again(monkeypatch, tmp_path):
    _tree(tmp_path)
    combos = module.build_combinations(SimpleNamespace(
        goal_file=str(tmp_path / "goal.json"), roles_dir=str(tmp_path / "roles"),
        traits_dir=str(tmp_path / "traits"), goal_count=1, non_goal_count=1))
    client = FakeAnthropic()
    # a run stopped after submitting its first stage
    reqs = [{"custom_id": module.batch_custom_id(c, "claude-sonnet-5-5", "first"),
             "params": module.request_params(c, "claude-sonnet-5-5")} for c in combos]
    bid = asyncio.run(client._bcreate(reqs)).id
    module.record_batch(tmp_path / "combination_scores.json",
                        {"id": bid, "stage": "first", "model": "claude-sonnet-5-5"})
    out = _run_main(monkeypatch, tmp_path, client, "--batch_id", bid)
    assert [len(r) for _, r in client.created] == [2, 3]   # only the rescore is new
    assert len(json.loads(out.read_text())["scores"]) == 2


def test_real_time_mode_and_the_cost_guard(monkeypatch, tmp_path):
    client = FakeAnthropic()
    monkeypatch.setattr(module, "estimate_cost_usd", lambda *a, **k: 25.0)
    with pytest.raises(SystemExit, match="over \\$20"):
        _run_main(monkeypatch, tmp_path, client, "--no_batch")
    out = _run_main(monkeypatch, tmp_path, client, "--no_batch", "--confirm_expensive")
    assert client.created == [] and client.messages.create.call_count == 5   # 2 + 3 rescores
    data = json.loads(out.read_text())
    assert data["metadata"]["mode"] == "real time" and data["summary"]["escalated"] == 1
    usage = json.loads((tmp_path / "combination_scores_usage.json").read_text())
    assert set(usage["per_model"]) == {"claude-sonnet-5-5", "claude-opus-5-5"}


def test_rescore_samples_are_combined_by_median():
    first = {"output_name": "r_a__b", "role": "a", "trait": "b", "first_model": "s",
             "per_pair": [{"reasoning": "f", "score": 2}, {"reasoning": "f", "score": 3}]}

    def smp(a, b):
        return {"output_name": "r_a__b", "role": "a", "trait": "b", "pairs_sha256": "h",
                "per_pair": [{"reasoning": f"says {a}", "score": a}, {"reasoning": f"says {b}", "score": b}]}

    rec = module.escalated_record(first, [smp(3, 1), smp(1, 2), smp(3, 3)], "opus", None)
    assert [p["score"] for p in rec["per_pair"]] == [3, 2]          # majority 3; all differ -> middle 2
    assert [p["reasoning"] for p in rec["per_pair"]] == ["says 3", "says 2"]
    assert rec["score_max"] == 3 and rec["rescore_samples"] == [[3, 1], [1, 2], [3, 3]]
    assert rec["sonnet_scores"] == first["per_pair"] and rec["rescore_aggregation"] == "median_low"
    # two usable samples: the lower middle, still an integer
    assert [p["score"] for p in module.escalated_record(first, [smp(3, 1), smp(2, 2)], "o", None)["per_pair"]] == [2, 1]


def test_first_stage_ids_keep_their_form():
    """The first stage of 2026-10-10 was submitted before samples existed; its
    ids (sample 0) must stay the same for --batch_id to collect it."""
    c = _combo()
    import hashlib
    digest = hashlib.sha256(f"{c['output_name']}\n{c['pairs_sha256']}\nm".encode()).hexdigest()[:12]
    assert module.batch_custom_id(c, "m", "first") == f"f-r_a__b-{digest}"
    ids = {module.batch_custom_id(c, "m", "rescore", k) for k in range(3)}
    assert len(ids) == 3 and all(len(i) <= 64 for i in ids)
