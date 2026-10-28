"""tools/merge_pod_outputs.py on fake pod trees (walk-through P1,
2026-10-12): four pods (roles, traits, r_ and t_ combinations), each with its
own default, without their activations (which stay on the pods).  The scanner runs for real as a
subprocess on the merged tree.  No model, no API."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import merge_pod_outputs as mpo  # noqa: E402

SETTINGS = {"model_name": "Qwen/Qwen3-32B", "template_kwargs": {"enable_thinking": False},
            "response_cleanup": "strip_leaked_think",
            "sampling": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 512, "max_model_len": 2048},
            "questions": {"sha256": "q", "question_count": 300, "reduce_questions": 3}}


def _vector(path: Path, value: float, vtype="pos_3"):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"vector": torch.full((3, 2, 4), value), "type": vtype, "role": path.stem}, path)


def _usage(path: Path, n: int, cost: float):
    path.write_text(json.dumps({"per_model": {"gpt-4.1-mini:batch": {
        "model": "gpt-4.1-mini:batch", "n_calls": n, "prompt_tokens": 700 * n,
        "completion_tokens": 70 * n, "cost_usd": cost}},
        "n_calls": n, "total_prompt_tokens": 700 * n, "total_completion_tokens": 70 * n,
        "total_cost_usd": cost}))


def _pod(root: Path, typ: str, names: list[str], *, default_value=10.0, settings=SETTINGS,
         listed=None, uncollected=False, missing_vector=None):
    """One pod's OUTPUT_DIR after its pipeline, as the merge sees it, without
    the activations (they stay on the pod): default/ and one type directory."""
    d = root / "default"
    (d / "responses").mkdir(parents=True)
    (d / "responses" / "default.jsonl").write_text("{}\n")
    _vector(d / "vectors" / "default.pt", default_value, vtype="mean")
    t = root / typ
    for sub in ("responses", "scores", "vectors"):
        (t / sub).mkdir(parents=True)
    (t / "responses" / "default.jsonl").symlink_to("../../default/responses/default.jsonl")
    (t / "vectors" / "default.pt").symlink_to("../../default/vectors/default.pt")
    for i, n in enumerate(names):
        (t / "responses" / f"{n}.jsonl").write_text("{}\n")
        (t / "scores" / f"{n}.json").write_text(json.dumps({f"pos_p0_q{k}": 3 for k in range(4)}))
        if n != missing_vector:
            _vector(t / "vectors" / f"{n}.pt", float(i))
    _usage(t / "scores" / "usage.json", len(names) * 4, 0.01 * len(names))
    (t / "scores" / "judge_rubric.json").write_text(json.dumps(
        {"rubric_version": 2, "rubric_versions": [2], "judge_models": ["gpt-4.1-mini"],
         "entity_type": typ.rstrip("s"), "label_form": "judge-display-v1",
         "script": "pipeline/3_judge.py"}))
    chunk = {"path": "_batches/chunk_x_0000.jsonl", "batch_id": "batch-1", "collected": True}
    if uncollected:
        chunk["collected"] = False
    (t / "scores" / "batch_state.json").write_text(json.dumps({"version": 1, "chunks": [chunk]}))
    run = {**settings, "created_at": "2026-10-20T00:00:00+00:00",
           "selection": {"items": listed if listed is not None else names + ["default"]}}
    (t / "responses" / "generation_config.json").write_text(json.dumps({"schema": 1, "runs": [run]}))
    (root / "pipeline_20261020_000000.log").write_text("log\n")
    return root


@pytest.fixture
def pods(tmp_path):
    return {
        "roles": _pod(tmp_path / "pods" / "roles", "roles", ["pirate", "chef", "patient"]),
        "traits": _pod(tmp_path / "pods" / "traits", "traits", ["bold", "shy", "patient"],
                       default_value=11.0),
        "rcomb": _pod(tmp_path / "pods" / "rcomb", "combinations", ["r_angel__bold", "r_angel__shy"]),
        "tcomb": _pod(tmp_path / "pods" / "tcomb", "combinations", ["t_chef__kind", "t_chef__wry"]),
    }


def _merge(tmp_path, pods, *extra):
    return mpo.main([*(f"--pod={n}={p}" for n, p in pods.items()),
                     "--dest", str(tmp_path / "merged"), "--min_count", "2", *extra])


def test_four_pods_merge_into_one_tree(tmp_path, pods):
    assert _merge(tmp_path, pods) == 0
    m = tmp_path / "merged"
    assert not (tmp_path / "merged.partial").exists()
    combos = sorted(p.stem for p in (m / "combinations" / "responses").glob("*.jsonl"))
    assert combos == ["default", "r_angel__bold", "r_angel__shy", "t_chef__kind", "t_chef__wry"]
    # the name of both kinds stays apart, by type directory
    assert (m / "roles" / "vectors" / "patient.pt").exists() and (m / "traits" / "vectors" / "patient.pt").exists()
    # default from the first pod; the others' kept aside
    d = torch.load(m / "default" / "vectors" / "default.pt", weights_only=False)
    assert float(d["vector"][0, 0, 0]) == 10.0
    assert (m / "default" / "other_pods" / "traits" / "default.pt").exists()
    assert (m / "traits" / "vectors" / "default.pt").is_symlink()
    assert torch.load(m / "traits" / "vectors" / "default.pt", weights_only=False)["type"] == "mean"
    # usage summed per type, generation runs joined with their pod
    u = json.loads((m / "combinations" / "scores" / "usage.json").read_text())
    assert u["n_calls"] == 16 and u["per_model"]["gpt-4.1-mini:batch"]["n_calls"] == 16
    gc = json.loads((m / "combinations" / "responses" / "generation_config.json").read_text())
    assert sorted(r["pod"] for r in gc["runs"]) == ["rcomb", "tcomb"]
    assert json.loads((m / "combinations" / "scores" / "judge_rubric.json").read_text())[
        "merged_from_pods"] == ["rcomb", "tcomb"]
    assert not (m / "roles" / "scores" / "batch_state.json").exists()
    assert (m / "logs" / "tcomb" / "pipeline_20261020_000000.log").exists()
    rec = json.loads((m / "MERGED.json").read_text())
    assert rec["default_from"] == "roles" and rec["counts"]["combinations"]["vectors"] == 4
    # the scan's report sits in each vectors dir: every entity vector_only
    audit = json.loads((m / "traits" / "vectors" / "missing_vectors_audit.json").read_text())
    assert {r["status"] for r in audit["results"]} == {"vector_only"}


def test_a_stem_from_two_pods_is_refused(tmp_path, pods, capsys):
    _pod(tmp_path / "pods" / "rcomb2", "combinations", ["r_angel__bold"])
    pods["rcomb2"] = tmp_path / "pods" / "rcomb2"
    assert _merge(tmp_path, pods) == 1
    assert "r_angel__bold (rcomb, rcomb2)" in capsys.readouterr().err
    assert not (tmp_path / "merged").exists() and not (tmp_path / "merged.partial").exists()


def test_uncollected_batches_are_refused(tmp_path, pods, capsys):
    pods["traits"] = _pod(tmp_path / "pods" / "traits2", "traits", ["bold"], uncollected=True)
    assert _merge(tmp_path, pods) == 1
    assert "not collected" in capsys.readouterr().err


def test_other_generation_settings_are_refused(tmp_path, pods, capsys):
    other = {**SETTINGS, "sampling": {**SETTINGS["sampling"], "max_tokens": 1024}}
    pods["tcomb"] = _pod(tmp_path / "pods" / "tcomb2", "combinations", ["t_chef__kind"],
                         settings=other)
    assert _merge(tmp_path, pods) == 1
    assert "other settings" in capsys.readouterr().err


def test_a_listed_entity_without_responses_is_refused(tmp_path, pods, capsys):
    pods["roles"] = _pod(tmp_path / "pods" / "roles2", "roles", ["pirate"],
                         listed=["pirate", "ghost", "default"])
    assert _merge(tmp_path, pods) == 1
    assert "ghost" in capsys.readouterr().err


def test_the_scanners_exit_3_refuses_the_merge(tmp_path, pods):
    """A role with enough score-3 responses but no vector: the scan reports
    it (missing_activation: no activation file either) and the merge stops."""
    pods["roles"] = _pod(tmp_path / "pods" / "roles2", "roles", ["pirate", "chef"],
                         missing_vector="chef")
    assert _merge(tmp_path, pods) == mpo.EXIT_SCAN
    assert not (tmp_path / "merged").exists()
    assert (tmp_path / "merged.partial" / "roles" / "vectors" / "missing_vectors_audit.json").exists()


def test_expected_counts(tmp_path, pods, capsys):
    assert _merge(tmp_path, pods, "--expect", "roles=4") == 1
    assert "roles: 3 response files, expected 4" in capsys.readouterr().err


def test_an_existing_destination_is_refused(tmp_path, pods):
    (tmp_path / "merged").mkdir()
    assert _merge(tmp_path, pods) == 1


def test_version_10_logs_replies_and_rubric_hashes_are_carried(tmp_path, pods):
    """The October role judging (2026-10-28): version 10's disagreement log and
    the saved replies reach the merged tree, and the rubric stamp keeps the hash
    and the reply format (--reread_replies and step 3's version check need them)."""
    s = pods["roles"] / "roles" / "scores"
    (s / "judge_rubric.json").write_text(json.dumps(
        {"rubric_version": 10, "rubric_versions": [10], "judge_models": ["gpt-5.6-luna"],
         "entity_type": "role", "label_form": "judge-display-v1", "script": "pipeline/3_judge.py",
         "prompt_sha256": {"10": "c19e859a53c91d5e"}, "reply_format": "abc_answers"}))
    row = {"entity": "pirate", "key": "pos_p0_q1", "answers": "AnBnCy", "stated": 2, "score": 3,
           "keep_changed": True}
    (s / "abc_disagreements.jsonl").write_text(json.dumps(row) + "\n")
    (s / "_replies").mkdir()
    (s / "_replies" / "pirate.jsonl").write_text(json.dumps({"key": "pos_p0_q1", "score": 3,
                                                               "reply": "A: no"}) + "\n")
    assert _merge(tmp_path, pods) == 0
    m = tmp_path / "merged" / "roles" / "scores"
    assert [json.loads(l) for l in (m / "abc_disagreements.jsonl").read_text().splitlines()] == [row]
    assert (m / "_replies" / "pirate.jsonl").exists() and not (m / "_replies.json").exists()
    rb = json.loads((m / "judge_rubric.json").read_text())
    assert rb["prompt_sha256"] == {"10": "c19e859a53c91d5e"} and rb["reply_format"] == "abc_answers"
    rec = json.loads((tmp_path / "merged" / "MERGED.json").read_text())
    assert rec["counts"]["roles"]["abc_disagreements"] == 1 and rec["counts"]["roles"]["replies"] == 1
    assert not (tmp_path / "merged" / "traits" / "scores" / "abc_disagreements.jsonl").exists()


def test_two_hashes_for_one_version_refuse_the_merge(tmp_path, pods, capsys):
    for name, sha in (("rcomb", "aaaa"), ("tcomb", "bbbb")):
        p = pods[name] / "combinations" / "scores" / "judge_rubric.json"
        p.write_text(json.dumps({**json.loads(p.read_text()), "prompt_sha256": {"2": sha}}))
    assert _merge(tmp_path, pods) == 1 and not (tmp_path / "merged").exists()
    assert "rubric hash bbbb, another pod with aaaa" in capsys.readouterr().err

