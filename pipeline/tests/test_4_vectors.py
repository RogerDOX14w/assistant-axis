"""Tests for pipeline/4_vectors.py (step 4: per-entity vectors).

Small fake activation files (the real ones are ~2.6 GB) in tmp_path; no GPU,
no model, no network.  Read retries are made instant by stubbing
``assistant_axis.atomic_io.time.sleep``.

Behaviour pinned here (2026-10-12 review):
  * an activation is joined to its score by key; unscored activations are
    not used; the vector is the nanmean over the score=3 ones;
  * "default" is an exact name (a substring test would have averaged any
    entity whose name contains "default" without the score filter);
  * the exit status is 1 when an entity fails (unreadable activation or
    scores file, empty activation file) and 0 when entities are only
    filtered (below --min_count, no scores file) or skipped;
  * a 0-byte placeholder activation is skipped without a load attempt;
  * ``--overwrite FILE`` overwrites only the listed entities.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import torch

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipeline" / "4_vectors.py"

N_SLOTS, N_LAYERS, HIDDEN = 3, 2, 4


@pytest.fixture(scope="module")
def step4():
    spec = importlib.util.spec_from_file_location("_pipeline_4_vectors_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _fast_and_isolated(tmp_path, monkeypatch):
    import assistant_axis.atomic_io as aio
    monkeypatch.setattr(aio.time, "sleep", lambda s: None)
    stage = tmp_path / "stage"
    stage.mkdir()
    monkeypatch.setenv("TMPDIR", str(stage))


def _act(value: float, *, nan_header: bool = False) -> torch.Tensor:
    t = torch.full((N_SLOTS, N_LAYERS, HIDDEN), value)
    if nan_header:
        t[1] = float("nan")      # header slot not found for this response
    return t


def _write_entity(dirs, name, scores: dict | None, values: dict, *, nan_keys=()):
    acts = {k: _act(v, nan_header=k in nan_keys) for k, v in values.items()}
    acts["metadata"] = {"header_tokens": ["a", "b"], "header_ids": [1, 2],
                        "model_name": "fake/model"}
    torch.save(acts, dirs["act"] / f"{name}.pt")
    if scores is not None:
        (dirs["scores"] / f"{name}.json").write_text(json.dumps(scores))


@pytest.fixture
def dirs(tmp_path):
    d = {"act": tmp_path / "activations", "scores": tmp_path / "scores",
         "vec": tmp_path / "vectors"}
    for p in d.values():
        p.mkdir()
    return d


def _main(step4, dirs, *extra, min_count=2):
    return step4.main(["--activations_dir", str(dirs["act"]),
                       "--scores_dir", str(dirs["scores"]),
                       "--output_dir", str(dirs["vec"]),
                       "--min_count", str(min_count), *extra])


def _load(path):
    return torch.load(path, map_location="cpu", weights_only=False)


def test_vector_is_nanmean_of_matched_score_3_activations(step4, dirs):
    values = {"pos_p0_q0": 1.0, "pos_p0_q1": 3.0, "pos_p1_q0": 100.0,
              "pos_p1_q1": 7.0, "pos_p2_q0": 50.0}
    scores = {"pos_p0_q0": 3, "pos_p0_q1": 3, "pos_p1_q0": 2,   # score 2: not used
              "pos_p1_q1": 3,
              "pos_p9_q9": 3}            # scored, no activation: ignored
    # pos_p2_q0 has no score (an excluded variant): not used
    _write_entity(dirs, "pirate", scores, values, nan_keys={"pos_p0_q0"})
    assert _main(step4, dirs) == 0
    out = _load(dirs["vec"] / "pirate.pt")
    assert out["type"] == "pos_3" and out["role"] == "pirate"
    assert out["metadata"]["header_ids"] == [1, 2]
    v = out["vector"]
    assert v.shape == (N_SLOTS, N_LAYERS, HIDDEN)
    assert torch.allclose(v[0], torch.full((N_LAYERS, HIDDEN), (1 + 3 + 7) / 3))
    # slot 1: pos_p0_q0's NaN is skipped by nanmean
    assert torch.allclose(v[1], torch.full((N_LAYERS, HIDDEN), (3 + 7) / 2))


def test_vector_records_its_inputs(step4, dirs):
    """A vector made from a partial scores file must be recognisable later:
    the scores file's hash and counts are recorded beside the vector (not in
    "metadata", which step 5 copies into the axis)."""
    scores = {"pos_p0_q0": 3, "pos_p0_q1": 3, "pos_p0_q2": 1}
    _write_entity(dirs, "pirate", scores,
                  {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0, "pos_p0_q2": 1.0, "pos_p0_q3": 1.0})
    assert _main(step4, dirs) == 0
    out = _load(dirs["vec"] / "pirate.pt")
    inputs = out["inputs"]
    text = (dirs["scores"] / "pirate.json").read_text()
    import hashlib
    assert inputs["scores_file"]["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert inputs["scores_file"]["n_scores"] == 3
    assert inputs["n_activations"] == 4
    assert inputs["n_scored_activations"] == 3
    assert inputs["n_score3_used"] == 2
    assert inputs["min_count"] == 2
    assert "inputs" not in out["metadata"]


def test_default_is_an_exact_name(step4, dirs):
    _write_entity(dirs, "default", None, {"default_p0_q0": 2.0, "default_p0_q1": 4.0})
    # A name that merely contains "default" is an ordinary entity: score-filtered.
    _write_entity(dirs, "defaulter", {"pos_p0_q0": 3, "pos_p0_q1": 1},
                  {"pos_p0_q0": 10.0, "pos_p0_q1": 20.0})
    assert _main(step4, dirs, min_count=1) == 0
    d = _load(dirs["vec"] / "default.pt")
    assert d["type"] == "mean"
    assert torch.allclose(d["vector"], torch.full_like(d["vector"], 3.0))
    e = _load(dirs["vec"] / "defaulter.pt")
    assert e["type"] == "pos_3"
    assert torch.allclose(e["vector"], torch.full_like(e["vector"], 10.0))


def test_filtered_entities_do_not_fail_the_run(step4, dirs):
    _write_entity(dirs, "few", {"pos_p0_q0": 3, "pos_p0_q1": 2},
                  {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})          # 1 < min_count 2
    _write_entity(dirs, "unscored", None, {"pos_p0_q0": 1.0})   # no scores file
    assert _main(step4, dirs) == 0
    assert list(dirs["vec"].glob("*.pt")) == []


def test_unreadable_activation_fails_the_run_but_not_the_others(step4, dirs):
    """A garbage file raises pickle.UnpicklingError, which the old except
    clause did not catch: the whole step crashed on the first one."""
    (dirs["act"] / "garbage.pt").write_bytes(b"this is not a torch file at all")
    _write_entity(dirs, "pirate", {"pos_p0_q0": 3, "pos_p0_q1": 3},
                  {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})
    (dirs["scores"] / "garbage.json").write_text("{}")
    assert _main(step4, dirs) == 1
    assert (dirs["vec"] / "pirate.pt").exists()
    assert not (dirs["vec"] / "garbage.pt").exists()


def test_corrupt_scores_file_is_a_failure_not_a_filter(step4, dirs):
    _write_entity(dirs, "pirate", None, {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})
    (dirs["scores"] / "pirate.json").write_text('{"pos_p0_q0": 3, ')   # truncated
    assert _main(step4, dirs) == 1
    assert not (dirs["vec"] / "pirate.pt").exists()


def test_empty_activation_file_fails(step4, dirs):
    torch.save({"metadata": {}}, dirs["act"] / "hollow.pt")
    assert _main(step4, dirs) == 1


def test_no_activation_files_is_an_error(step4, dirs):
    assert _main(step4, dirs) == 1


def test_zero_byte_placeholder_is_skipped_without_loading(step4, dirs, monkeypatch):
    (dirs["act"] / "deleted_to_save_disk.pt").write_bytes(b"")
    loaded = []
    real = step4.load_activations
    monkeypatch.setattr(step4, "load_activations",
                        lambda p: loaded.append(p.name) or real(p))
    _write_entity(dirs, "pirate", {"pos_p0_q0": 3, "pos_p0_q1": 3},
                  {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})
    assert _main(step4, dirs) == 0
    assert loaded == ["pirate.pt"]


def test_vanished_activation_fails_without_read_retries(step4, dirs):
    missing = dirs["act"] / "gone.pt"
    status = step4.process_entity(missing, dirs["vec"] / "gone.pt", dirs["scores"],
                                  min_count=1, reduce_questions=1)
    assert status == "failed"


def _two_entities_with_stale_vectors(dirs):
    for name in ("alpha", "beta"):
        _write_entity(dirs, name, {"pos_p0_q0": 3, "pos_p0_q1": 3},
                      {"pos_p0_q0": 5.0, "pos_p0_q1": 5.0})
        torch.save({"vector": torch.zeros(1), "type": "stale", "role": name},
                   dirs["vec"] / f"{name}.pt")


def test_existing_vectors_are_skipped(step4, dirs):
    _two_entities_with_stale_vectors(dirs)
    assert _main(step4, dirs) == 0
    assert _load(dirs["vec"] / "alpha.pt")["type"] == "stale"


def test_overwrite_with_a_rerun_list_overwrites_only_the_listed(step4, dirs, tmp_path):
    """pipeline/README.md documents ``--overwrite missing_vectors_rerun.txt``;
    with the old store_true flag that invocation was an argparse error."""
    _two_entities_with_stale_vectors(dirs)
    rerun = tmp_path / "missing_vectors_rerun.txt"
    rerun.write_text("beta\n\n# a comment\n")
    assert _main(step4, dirs, "--overwrite", str(rerun)) == 0
    assert _load(dirs["vec"] / "alpha.pt")["type"] == "stale"
    assert _load(dirs["vec"] / "beta.pt")["type"] == "pos_3"


def test_overwrite_flag_alone_overwrites_all(step4, dirs):
    _two_entities_with_stale_vectors(dirs)
    assert _main(step4, dirs, "--overwrite") == 0
    assert _load(dirs["vec"] / "alpha.pt")["type"] == "pos_3"
    assert _load(dirs["vec"] / "beta.pt")["type"] == "pos_3"


def test_overwrite_list_must_exist(step4, dirs, tmp_path):
    _two_entities_with_stale_vectors(dirs)
    with pytest.raises(SystemExit):
        _main(step4, dirs, "--overwrite", str(tmp_path / "no_such_list.txt"))


def test_reduce_questions_keeps_every_nth_question(step4, dirs):
    values = {f"pos_p0_q{q}": float(q) for q in range(6)}
    _write_entity(dirs, "pirate", {k: 3 for k in values}, values)
    assert _main(step4, dirs, "--reduce_questions", "3", min_count=1) == 0
    v = _load(dirs["vec"] / "pirate.pt")["vector"]
    assert torch.allclose(v[0], torch.full((N_LAYERS, HIDDEN), (0 + 3) / 2))


# ---------------------------------------------------------------------------
# Recompute rule (walk-through P2, 2026-10-12): a vector whose recorded
# scores hash differs from the scores file now is stale and recomputed.
# ---------------------------------------------------------------------------

import os
import time as _time


def _make_scores_newer(dirs, name):
    """Give the scores file a later mtime than the vector (what a rewrite by
    step 3 after step 4 would do), without waiting."""
    vec = dirs["vec"] / f"{name}.pt"
    later = vec.stat().st_mtime + 5
    os.utime(dirs["scores"] / f"{name}.json", (later, later))


def _partial_then_complete(step4, dirs):
    values = {f"pos_p0_q{q}": float(q) for q in range(4)}
    _write_entity(dirs, "pirate", {"pos_p0_q0": 3, "pos_p0_q1": 3}, values)   # partial
    assert _main(step4, dirs) == 0
    v1 = _load(dirs["vec"] / "pirate.pt")
    assert torch.allclose(v1["vector"][0], torch.full((N_LAYERS, HIDDEN), 0.5))
    (dirs["scores"] / "pirate.json").write_text(json.dumps({k: 3 for k in values}))
    _make_scores_newer(dirs, "pirate")
    return values


def test_a_vector_from_a_partial_scores_file_is_recomputed(step4, dirs, caplog):
    _partial_then_complete(step4, dirs)
    with caplog.at_level("WARNING"):
        assert _main(step4, dirs) == 0
    v2 = _load(dirs["vec"] / "pirate.pt")
    assert torch.allclose(v2["vector"][0], torch.full((N_LAYERS, HIDDEN), 1.5))
    assert v2["inputs"]["n_score3_used"] == 4
    assert "recomputing" in caplog.text


def test_a_rewritten_but_identical_scores_file_is_not_stale(step4, dirs):
    _write_entity(dirs, "pirate", {"pos_p0_q0": 3, "pos_p0_q1": 3},
                  {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})
    assert _main(step4, dirs) == 0
    before = (dirs["vec"] / "pirate.pt").read_bytes()
    _make_scores_newer(dirs, "pirate")                 # touched, content unchanged
    assert _main(step4, dirs) == 0
    assert (dirs["vec"] / "pirate.pt").read_bytes() == before


def test_a_may_vector_without_inputs_counts_as_current(step4, dirs):
    _write_entity(dirs, "pirate", {"pos_p0_q0": 3, "pos_p0_q1": 3},
                  {"pos_p0_q0": 5.0, "pos_p0_q1": 5.0})
    torch.save({"vector": torch.zeros(1), "type": "may", "role": "pirate"},
               dirs["vec"] / "pirate.pt")
    _make_scores_newer(dirs, "pirate")
    assert _main(step4, dirs) == 0
    assert _load(dirs["vec"] / "pirate.pt")["type"] == "may"


def test_a_stale_vector_that_no_longer_reaches_min_count_is_moved_aside(step4, dirs):
    values = {f"pos_p0_q{q}": float(q) for q in range(4)}
    _write_entity(dirs, "pirate", {k: 3 for k in values}, values)
    assert _main(step4, dirs) == 0
    (dirs["scores"] / "pirate.json").write_text(json.dumps({"pos_p0_q0": 3}))   # 1 < min 2
    _make_scores_newer(dirs, "pirate")
    assert _main(step4, dirs) == 0                     # filtered, not failed
    assert not (dirs["vec"] / "pirate.pt").exists()
    assert (dirs["vec"] / "pirate.pt.stale").exists()


def test_the_early_check_sees_a_newer_scores_file(step4, dirs):
    import argparse
    _write_entity(dirs, "pirate", {"pos_p0_q0": 3, "pos_p0_q1": 3},
                  {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})
    assert _main(step4, dirs) == 0
    args = argparse.Namespace(activations_dir=str(dirs["act"]), scores_dir=str(dirs["scores"]),
                              output_dir=str(dirs["vec"]), overwrite=False)
    older = (dirs["vec"] / "pirate.pt").stat().st_mtime - 5
    os.utime(dirs["scores"] / "pirate.json", (older, older))
    assert step4.nothing_to_do(args) is True
    _make_scores_newer(dirs, "pirate")
    assert step4.nothing_to_do(args) is False


# ---------------------------------------------------------------------------
# float32 vectors (walk-through P3, 2026-10-12)
# ---------------------------------------------------------------------------

def test_vectors_are_float32_averaged_in_float64(step4, dirs):
    """bf16 activations (what step 2 writes) give a float32 vector equal to
    the float64 mean rounded once; the old bf16 mean was off by a rounding."""
    gen = torch.Generator().manual_seed(0)
    acts = {f"pos_p0_q{q}": (torch.randn(N_SLOTS, N_LAYERS, HIDDEN, generator=gen) * 50
                             ).to(torch.bfloat16) for q in range(40)}
    acts["pos_p0_q0"][1] = float("nan")
    data = dict(acts)
    data["metadata"] = {"header_ids": [1, 2], "model_name": "fake/model"}
    torch.save(data, dirs["act"] / "pirate.pt")
    (dirs["scores"] / "pirate.json").write_text(json.dumps({k: 3 for k in acts}))
    assert _main(step4, dirs) == 0
    saved = _load(dirs["vec"] / "pirate.pt")
    v = saved["vector"]
    assert v.dtype == torch.float32
    assert saved["inputs"]["vector_dtype"] == "float32"
    expected = torch.stack([a.to(torch.float64) for a in acts.values()]).nanmean(dim=0)
    assert torch.allclose(v.double(), expected, rtol=1e-6, atol=1e-6)
    old_bf16 = torch.stack(list(acts.values())).nanmean(dim=0)
    assert old_bf16.dtype == torch.bfloat16 and not torch.equal(old_bf16.float(), v)


def test_nanmean_float32_keeps_all_nan_elements_nan_and_checks_shapes(step4):
    a = torch.tensor([[1.0, float("nan")], [3.0, float("nan")]])
    b = torch.tensor([[3.0, float("nan")], [float("nan"), float("nan")]])
    m = step4.nanmean_float32([a, b])
    assert m.dtype == torch.float32
    assert m[0, 0] == 2.0 and m[1, 0] == 3.0 and torch.isnan(m[:, 1]).all()
    with pytest.raises(RuntimeError):
        step4.nanmean_float32([a, torch.zeros(3, 2)])


def test_the_default_mean_is_float32(step4, dirs):
    _write_entity(dirs, "default", None, {"default_p0_q0": 2.0, "default_p0_q1": 4.0})
    assert _main(step4, dirs) == 0
    assert _load(dirs["vec"] / "default.pt")["vector"].dtype == torch.float32


# ---------------------------------------------------------------------------
# --all_responses (the cap pilot's selection-only measure, 2026-10-28): the
# mean over every response, no score file.
# ---------------------------------------------------------------------------

def _main_all(step4, dirs, *extra, min_count=2):
    return step4.main(["--activations_dir", str(dirs["act"]), "--all_responses",
                       "--output_dir", str(dirs["vec"]), "--min_count", str(min_count), *extra])


def test_all_responses_averages_every_response_without_scores(step4, dirs):
    values = {"pos_p0_q0": 1.0, "pos_p0_q1": 3.0, "pos_p1_q0": 100.0}
    # A scores file beside it is not read: score 0 everywhere changes nothing.
    _write_entity(dirs, "pirate", {k: 0 for k in values}, values, nan_keys={"pos_p0_q0"})
    assert _main_all(step4, dirs) == 0
    out = _load(dirs["vec"] / "pirate.pt")
    v = out["vector"]
    assert v.dtype == torch.float32 and v.shape == (N_SLOTS, N_LAYERS, HIDDEN)
    assert torch.allclose(v[0], torch.full((N_LAYERS, HIDDEN), (1 + 3 + 100) / 3))
    assert torch.allclose(v[1], torch.full((N_LAYERS, HIDDEN), (3 + 100) / 2))   # nanmean
    # Not "mean", which step 5 takes for the default vector.
    assert out["type"] == "all_responses"
    assert out["metadata"]["all_responses"] is True and out["metadata"]["n_responses"] == 3
    assert out["metadata"]["header_ids"] == [1, 2]                 # the activation metadata kept
    assert out["inputs"]["all_responses"] is True and out["inputs"]["n_responses"] == 3
    assert "scores_file" not in out["inputs"]


def test_all_responses_equals_the_score_3_vector_when_every_response_is_3(step4, dirs, tmp_path):
    values = {f"pos_p0_q{q}": float(q) for q in range(5)}
    _write_entity(dirs, "pirate", {k: 3 for k in values}, values)
    assert _main(step4, dirs) == 0
    selected = _load(dirs["vec"] / "pirate.pt")["vector"]
    dirs["vec"] = tmp_path / "vectors_all"
    assert _main_all(step4, dirs) == 0
    assert torch.equal(_load(dirs["vec"] / "pirate.pt")["vector"], selected)


def test_all_responses_reads_min_count_as_responses(step4, dirs):
    _write_entity(dirs, "few", None, {"pos_p0_q0": 1.0, "pos_p0_q1": 2.0})
    _write_entity(dirs, "enough", None, {f"pos_p0_q{q}": 1.0 for q in range(3)})
    assert _main_all(step4, dirs, min_count=3) == 0            # filtered, not failed
    assert not (dirs["vec"] / "few.pt").exists()
    assert _load(dirs["vec"] / "enough.pt")["inputs"]["min_count"] == 3


def test_all_responses_refuses_a_scores_dir_and_the_normal_mode_requires_one(step4, dirs):
    _write_entity(dirs, "pirate", None, {"pos_p0_q0": 1.0})
    with pytest.raises(SystemExit):
        _main_all(step4, dirs, "--scores_dir", str(dirs["scores"]))
    with pytest.raises(SystemExit):
        step4.main(["--activations_dir", str(dirs["act"]), "--output_dir", str(dirs["vec"])])
    assert not (dirs["vec"] / "pirate.pt").exists()


def test_all_responses_skips_an_existing_vector_unless_overwritten(step4, dirs):
    import argparse
    _write_entity(dirs, "pirate", None, {"pos_p0_q0": 1.0, "pos_p0_q1": 1.0})
    torch.save({"vector": torch.zeros(1), "type": "old", "role": "pirate"},
               dirs["vec"] / "pirate.pt")
    args = argparse.Namespace(activations_dir=str(dirs["act"]), scores_dir=None,
                              output_dir=str(dirs["vec"]), overwrite=False, all_responses=True)
    assert step4.nothing_to_do(args) is True
    assert _main_all(step4, dirs) == 0
    assert _load(dirs["vec"] / "pirate.pt")["type"] == "old"
    assert _main_all(step4, dirs, "--overwrite") == 0
    assert _load(dirs["vec"] / "pirate.pt")["type"] == "all_responses"


def test_all_responses_keeps_default_a_mean(step4, dirs):
    _write_entity(dirs, "default", None, {"default_p0_q0": 2.0, "default_p0_q1": 4.0})
    assert _main_all(step4, dirs) == 0
    d = _load(dirs["vec"] / "default.pt")
    assert d["type"] == "mean" and d["metadata"]["all_responses"] is True
