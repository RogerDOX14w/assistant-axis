"""Tests for pipeline/scan_missing_vectors.py (the audit after step 4).

Small fake activation and vector files in tmp_path.  Covers the
classification of each status in the README's table that a laptop can
produce, the peer-median truncation check with placeholders present, the
exact "default" name, the exit status and where the outputs go.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import torch

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipeline" / "scan_missing_vectors.py"


@pytest.fixture(scope="module")
def scan():
    spec = importlib.util.spec_from_file_location("_pipeline_scan_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _fast_and_isolated(tmp_path, monkeypatch):
    import assistant_axis.atomic_io as aio
    monkeypatch.setattr(aio.time, "sleep", lambda s: None)
    stage = tmp_path / "stage"
    stage.mkdir()
    monkeypatch.setenv("TMPDIR", str(stage))


def _acts(path: Path, n: int, value: float = 1.0):
    data = {f"pos_p0_q{i}": torch.full((2, 3), value) for i in range(n)}
    torch.save(data, path)


def _vector(path: Path):
    torch.save({"vector": torch.ones(2, 3), "type": "pos_3", "role": path.stem}, path)


@pytest.fixture
def tree(tmp_path):
    """One entity-type directory: activations/, scores/, vectors/."""
    root = tmp_path / "out"
    t = {"root": root, "act": root / "traits" / "activations",
         "scores": root / "traits" / "scores", "vec": root / "traits" / "vectors"}
    for k in ("act", "scores", "vec"):
        t[k].mkdir(parents=True)
    return t


def _scores(t, name, n3: int, n_other: int = 0):
    s = {f"pos_p0_q{i}": 3 for i in range(n3)}
    s.update({f"pos_p1_q{i}": 1 for i in range(n_other)})
    (t["scores"] / f"{name}.json").write_text(json.dumps(s))


def _classify(scan, t, name, *, median, deep=False, min_count=2):
    return scan.classify_entity(
        role=name, act_file=t["act"] / f"{name}.pt", median_act_size=median,
        vectors_dir=t["vec"], scores_dir=t["scores"], min_count=min_count,
        reduce_questions=1, mode="filtered", deep_load=deep, load_check=True)


def test_statuses(scan, tree):
    t = tree
    _acts(t["act"] / "ok.pt", 4); _vector(t["vec"] / "ok.pt")
    _acts(t["act"] / "stub.pt", 4); (t["vec"] / "stub.pt").write_bytes(b"x" * 10)
    _acts(t["act"] / "corrupt.pt", 4); (t["vec"] / "corrupt.pt").write_bytes(b"y" * 4096)
    _acts(t["act"] / "noscores.pt", 4)
    _acts(t["act"] / "few.pt", 4); _scores(t, "few", 1, 3)
    _acts(t["act"] / "lost.pt", 4); _scores(t, "lost", 4)
    (t["act"] / "placeholder.pt").write_bytes(b"")
    median = (t["act"] / "ok.pt").stat().st_size
    got = {n: _classify(scan, t, n, median=median)["status"]
           for n in ("ok", "stub", "corrupt", "noscores", "few", "lost", "placeholder")}
    assert got == {"ok": "ok", "stub": "ok_zero_size", "corrupt": "corrupt_vector",
                   "noscores": "missing_scores", "few": "below_min_count",
                   "lost": "mysterious", "placeholder": "placeholder"}


def test_deep_load_confirms_scores_without_activations(scan, tree):
    """score=3 entries whose activation is missing do not count."""
    t = tree
    _acts(t["act"] / "sparse.pt", 1)              # only pos_p0_q0 extracted
    _scores(t, "sparse", 4)                       # 4 score=3 in the file
    median = (t["act"] / "sparse.pt").stat().st_size
    r = _classify(scan, t, "sparse", median=median, deep=True)
    assert r["status"] == "below_min_count"
    assert r["score3_in_scores"] == 4 and r["score3_matched"] == 1


def test_placeholder_reports_whether_a_vector_exists(scan, tree):
    t = tree
    (t["act"] / "kept.pt").write_bytes(b"")
    _vector(t["vec"] / "kept.pt")
    (t["act"] / "gone.pt").write_bytes(b"")
    a = _classify(scan, t, "kept", median=1000)
    b = _classify(scan, t, "gone", median=1000)
    assert a["status"] == b["status"] == "placeholder"
    assert a["vector_present"] is True and a["vector_size_bytes"] > 0
    assert b["vector_present"] is False


def test_default_is_an_exact_name(scan, tree):
    """"mydefaultish" is score-filtered like any entity (it used to be
    treated as the default, mean of all activations, and called
    mysterious instead of below_min_count)."""
    t = tree
    _acts(t["act"] / "mydefaultish.pt", 4)
    _scores(t, "mydefaultish", 0, 4)
    median = (t["act"] / "mydefaultish.pt").stat().st_size
    assert _classify(scan, t, "mydefaultish", median=median)["status"] == "below_min_count"


def test_peer_median_leaves_out_placeholders(scan, tmp_path):
    files = []
    for i in range(3):
        p = tmp_path / f"zero{i}.pt"; p.write_bytes(b""); files.append(p)
    for i, size in enumerate((1000, 3000)):
        p = tmp_path / f"real{i}.pt"; p.write_bytes(b"x" * size); files.append(p)
    assert scan.peer_median_size(files) == 2000
    assert scan.peer_median_size(files[:3]) == 0


def test_truncation_found_when_placeholders_are_the_majority(scan, tree):
    """With 3 placeholders out of 5 the median of all sizes was 0, which
    turned the truncation check off."""
    t = tree
    for i in range(3):
        (t["act"] / f"zero{i}.pt").write_bytes(b"")
    _acts(t["act"] / "full.pt", 40)
    _acts(t["act"] / "short.pt", 2)
    target = scan.ScanTarget(entity_type="traits", vectors_variant="vectors",
                             activations_dir=t["act"], vectors_dir=t["vec"],
                             scores_dir=t["scores"])
    sr = scan.scan_one_target(target, min_count=2, reduce_questions=1,
                              deep_load=False, load_check=True)
    by_name = {r["role"]: r["status"] for r in sr.results}
    assert by_name["short"] == "corrupt_or_truncated_activation"


def _single_pair(scan, t, tmp_path, *extra):
    return scan.main(["--activations_dir", str(t["act"]), "--vectors_dir", str(t["vec"]),
                      "--scores_dir", str(t["scores"]), "--min_count", "2",
                      "--cache", str(tmp_path / "cache.json"),
                      "--output", str(tmp_path / "report" / "audit.json"),
                      "--rerun_list", str(tmp_path / "report" / "rerun.txt"), *extra])


def test_exit_status_and_outputs_single_pair(scan, tree, tmp_path):
    t = tree
    _acts(t["act"] / "ok.pt", 4); _vector(t["vec"] / "ok.pt")
    assert _single_pair(scan, t, tmp_path) == 0
    assert (tmp_path / "report" / "rerun.txt").read_text() == ""

    _acts(t["act"] / "lost.pt", 4); _scores(t, "lost", 4)
    assert _single_pair(scan, t, tmp_path) == scan.EXIT_RERUN_CANDIDATES == 3
    assert (tmp_path / "report" / "rerun.txt").read_text() == "lost\n"
    report = json.loads((tmp_path / "report" / "audit.json").read_text())
    assert {r["role"]: r["status"] for r in report["results"]} == {
        "ok": "ok", "lost": "mysterious"}
    # nothing written into the data tree in single-pair mode with --output
    assert sorted(p.name for p in t["vec"].iterdir()) == ["ok.pt"]


def test_responses_dir_widens_the_universe(scan, tree):
    """With responses/ beside activations/: a vector whose activation was
    deleted on purpose is vector_only, a vector with no responses either is
    an orphan, and an entity with responses but nothing else is reported."""
    t = tree
    resp = t["root"] / "traits" / "responses"
    resp.mkdir()
    for name in ("ok", "deleted_after_step4", "never_extracted", "too_few"):
        (resp / f"{name}.jsonl").write_text("{}\n")
    _acts(t["act"] / "ok.pt", 4); _vector(t["vec"] / "ok.pt")
    _vector(t["vec"] / "deleted_after_step4.pt")
    _vector(t["vec"] / "renamed_old_stem.pt")           # no responses
    _scores(t, "never_extracted", 4)
    _scores(t, "too_few", 1, 3)
    target = scan.discover_scan_targets(t["root"])[0]
    assert target.responses_dir == resp
    sr = scan.scan_one_target(target, min_count=2, reduce_questions=1,
                              deep_load=False, load_check=True)
    got = {r["role"]: r["status"] for r in sr.results}
    assert got == {"ok": "ok", "deleted_after_step4": "vector_only",
                   "renamed_old_stem": "orphan_vector",
                   "never_extracted": "missing_activation", "too_few": "below_min_count"}
    rc = scan.main(["--root", str(t["root"]), "--min_count", "2", "--no_cache"])
    assert rc == scan.EXIT_RERUN_CANDIDATES          # missing_activation needs step 2
    # ... but it is not on step 4's rerun list (step 4 cannot make it)
    assert (t["vec"] / "missing_vectors_rerun.txt").read_text() == ""


def test_root_mode_writes_beside_each_vectors_dir(scan, tree):
    t = tree
    _acts(t["act"] / "ok.pt", 4); _vector(t["vec"] / "ok.pt")
    _vector(t["vec"] / "orphan.pt")
    rc = scan.main(["--root", str(t["root"]), "--min_count", "2", "--no_cache"])
    assert rc == 0                        # orphans are not re-run candidates
    report = json.loads((t["vec"] / "missing_vectors_audit.json").read_text())
    assert {r["role"]: r["status"] for r in report["results"]} == {
        "ok": "ok", "orphan": "orphan_vector"}
    assert (t["vec"] / "missing_vectors_rerun.txt").read_text() == ""


# ---------------------------------------------------------------------------
# stale_vector (walk-through P2, 2026-10-12)
# ---------------------------------------------------------------------------

def _vector_with_scores_hash(path: Path, scores_path: Path):
    import hashlib
    sha = hashlib.sha256(scores_path.read_text().encode("utf-8")).hexdigest()
    torch.save({"vector": torch.ones(2, 3), "type": "pos_3", "role": path.stem,
                "inputs": {"scores_file": {"name": scores_path.name, "sha256": sha}}}, path)


def test_a_vector_from_another_scores_file_is_stale(scan, tree):
    t = tree
    _acts(t["act"] / "pirate.pt", 4)
    _scores(t, "pirate", 2)                                   # partial
    _vector_with_scores_hash(t["vec"] / "pirate.pt", t["scores"] / "pirate.json")
    assert _classify(scan, t, "pirate", median=0)["status"] == "ok"
    _scores(t, "pirate", 4)                                   # step 3 finished later
    r = _classify(scan, t, "pirate", median=0)
    assert r["status"] == "stale_vector" and "stale_vector" in scan.RERUN_STATUSES
    assert "computed from scores" in r["note"]


def test_a_vector_without_an_inputs_record_is_current(scan, tree):
    t = tree
    _acts(t["act"] / "pirate.pt", 4)
    _scores(t, "pirate", 4)
    _vector(t["vec"] / "pirate.pt")                           # May: no inputs
    assert _classify(scan, t, "pirate", median=0)["status"] == "ok"


def test_the_stale_check_uses_the_cache_and_fills_old_entries(scan, tree, tmp_path):
    t = tree
    _acts(t["act"] / "pirate.pt", 4)
    _scores(t, "pirate", 2)
    vec = t["vec"] / "pirate.pt"
    _vector_with_scores_hash(vec, t["scores"] / "pirate.json")
    cache = scan.ScanCache(tmp_path / "cache.json")
    # an entry written before the key existed: loaded once to fill it
    cache.data["vector_loads"][cache._key(vec)] = {
        "size": vec.stat().st_size, "mtime": vec.stat().st_mtime, "ok": True, "error": None}
    kw = dict(role="pirate", act_file=t["act"] / "pirate.pt", median_act_size=0,
              vectors_dir=t["vec"], scores_dir=t["scores"], min_count=2, reduce_questions=1,
              mode="filtered", deep_load=False, load_check=True, cache=cache)
    assert scan.classify_entity(**kw)["status"] == "ok"
    entry = cache.data["vector_loads"][cache._key(vec)]
    assert len(entry["scores_sha256"]) == 64
    _scores(t, "pirate", 4)
    assert scan.classify_entity(**kw)["status"] == "stale_vector"     # from the cached hash


def test_a_stale_vector_makes_the_scan_exit_3(scan, tree, monkeypatch):
    t = tree
    _acts(t["act"] / "pirate.pt", 4)
    _scores(t, "pirate", 2)
    _vector_with_scores_hash(t["vec"] / "pirate.pt", t["scores"] / "pirate.json")
    _scores(t, "pirate", 4)
    rc = scan.main(["--activations_dir", str(t["act"]), "--vectors_dir", str(t["vec"]),
                    "--scores_dir", str(t["scores"]), "--min_count", "2", "--no_cache",
                    "--rerun_list", str(t["vec"] / "rerun.txt")])
    assert rc == scan.EXIT_RERUN_CANDIDATES
    assert (t["vec"] / "rerun.txt").read_text().split() == ["pirate"]


def test_a_float32_vector_passes_the_size_and_load_checks(scan, tree):
    """Vectors are float32 since 2026-10-12 (twice the bytes of May's bf16):
    the scanner's size checks are on activations (a peer median) and a
    256-byte floor for vectors, so both dtypes classify alike."""
    t = tree
    for name, dtype in (("may", torch.bfloat16), ("october", torch.float32)):
        _acts(t["act"] / f"{name}.pt", 4)
        torch.save({"vector": torch.ones(8, 4, 16, dtype=dtype), "type": "pos_3", "role": name},
                   t["vec"] / f"{name}.pt")
    median = scan.peer_median_size(sorted(t["act"].glob("*.pt")))
    for name in ("may", "october"):
        assert _classify(scan, t, name, median=median)["status"] == "ok"


# ---------------------------------------------------------------------------
# Activations deleted after the scan passed (walk-through P1, 2026-10-12)
# ---------------------------------------------------------------------------

def test_a_tree_without_activations_is_still_checked_against_its_responses(scan, tree):
    """Skipped before: with every activation deleted (the four-pod
    procedure) the scan found nothing to do, so a merged tree went unchecked."""
    t = tree
    resp = t["root"] / "traits" / "responses"
    resp.mkdir()
    for name in ("kept", "lost", "corrupt", "few"):
        (resp / f"{name}.jsonl").write_text("{}\n")
    _scores(t, "kept", 4); _vector(t["vec"] / "kept.pt")
    _scores(t, "lost", 4)                                   # enough score-3, no vector
    _scores(t, "corrupt", 4); (t["vec"] / "corrupt.pt").write_bytes(b"z" * 4096)
    _scores(t, "few", 1)                                    # legitimately filtered
    target = scan.ScanTarget(entity_type="traits", vectors_variant="vectors",
                             activations_dir=t["act"], vectors_dir=t["vec"],
                             scores_dir=t["scores"], responses_dir=resp)
    sr = scan.scan_one_target(target, min_count=2, reduce_questions=1, deep_load=False,
                              load_check=True)
    status = {r["role"]: r["status"] for r in sr.results}
    assert status == {"kept": "vector_only", "lost": "missing_activation",
                      "corrupt": "corrupt_vector", "few": "below_min_count"}
    assert [r["role"] for r in sr.suspects()] == ["corrupt"]
