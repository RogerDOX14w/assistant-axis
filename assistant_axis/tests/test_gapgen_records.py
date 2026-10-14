"""Tests for :mod:`assistant_axis.gapgen.records`: record files that may live gzip-compressed."""
from __future__ import annotations

import fcntl
import gzip
import json

import pytest

from assistant_axis.gapgen import records as R


def _lines(*rows) -> str:
    return "".join(json.dumps(r) + "\n" for r in rows)


def test_kinds_by_name():
    assert R.kind_of("x/responses.jsonl") == R.LOG
    assert R.kind_of("x/responses.jsonl.gz") == R.LOG
    for name in ("results.jsonl", "graph.json", "readings.jsonl", "matches.jsonl"):
        assert R.kind_of(f"x/{name}") == R.SNAPSHOT
    assert R.kind_of("x/registry_writes.jsonl") is None
    assert R.kind_of("x/summary.json") is None
    assert R.gz_path("a/responses.jsonl") == R.gz_path("a/responses.jsonl.gz")
    assert R.plain_path("a/responses.jsonl.gz").name == "responses.jsonl"


def test_plain_only_reads_as_before(tmp_path):
    p = tmp_path / "responses.jsonl"
    assert not R.exists(p)
    with pytest.raises(FileNotFoundError):
        R.read_text(p)
    p.write_text(_lines({"a": 1}, {"a": 2}) + "\n", encoding="utf-8")
    assert R.exists(p)
    assert R.read_text(p) == p.read_text(encoding="utf-8")
    assert R.read_jsonl(p) == [{"a": 1}, {"a": 2}]
    assert R.current_path(p) == p


def test_log_is_gz_then_plain(tmp_path):
    p = tmp_path / "responses.jsonl"
    R.gz_path(p).write_bytes(gzip.compress(_lines({"n": 1}, {"n": 2}).encode()))
    assert R.exists(p) and not p.exists()
    assert R.read_jsonl(p) == [{"n": 1}, {"n": 2}]
    assert R.current_path(p) == R.gz_path(p)
    p.write_text(_lines({"n": 3}), encoding="utf-8")
    assert R.read_jsonl(p) == [{"n": 1}, {"n": 2}, {"n": 3}]
    assert R.read_bytes(p) == _lines({"n": 1}, {"n": 2}, {"n": 3}).encode()
    assert R.current_path(p) == p


def test_multi_member_gz(tmp_path):
    p = tmp_path / "responses.jsonl"
    R.gz_path(p).write_bytes(gzip.compress(_lines({"n": 1}).encode()) + gzip.compress(_lines({"n": 2}).encode()))
    assert R.read_jsonl(p) == [{"n": 1}, {"n": 2}]


def test_snapshot_prefers_plain(tmp_path):
    p = tmp_path / "results.jsonl"
    R.gz_path(p).write_bytes(gzip.compress(_lines({"old": True}).encode()))
    assert R.read_jsonl(p) == [{"old": True}]
    p.write_text(_lines({"new": True}), encoding="utf-8")
    assert R.read_jsonl(p) == [{"new": True}]
    g = tmp_path / "graph.json"
    R.gz_path(g).write_bytes(gzip.compress(b'{"result": {"x": 1}}'))
    assert R.read_json(g) == {"result": {"x": 1}}


def test_unclassified_name_ignores_gz(tmp_path):
    p = tmp_path / "summary.json"
    R.gz_path(p).write_bytes(gzip.compress(b"{}"))
    assert not R.exists(p)
    with pytest.raises(FileNotFoundError):
        R.read_text(p)
    assert R.exists(p, R.SNAPSHOT) and R.read_json(p, R.SNAPSHOT) == {}


def test_unknown_kind_refused(tmp_path):
    p = tmp_path / "summary.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        R.read_text(p, "archive")
    rep = R.pack(p)
    assert rep.action == "refused" and "not a record file" in rep.reason
    assert p.exists() and not R.gz_path(p).exists()
    with pytest.raises(ValueError):
        R.pack(p, "archive")


def test_pack_log_round_trip_and_after_resume(tmp_path):
    p = tmp_path / "responses.jsonl"
    first = _lines({"n": 1}, {"n": 2})
    p.write_text(first, encoding="utf-8")
    rep = R.pack(p)
    assert rep.action == "packed" and rep.plain_bytes == len(first)
    assert not p.exists() and R.read_text(p) == first
    # a resume appends to a fresh plain file; readers see .gz + plain
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(_lines({"n": 3}))
    assert R.read_jsonl(p) == [{"n": 1}, {"n": 2}, {"n": 3}]
    rep = R.pack(p)
    assert rep.action == "packed" and not p.exists()
    assert R.read_text(p) == first + _lines({"n": 3})
    # two members now; packing again with nothing new does nothing
    assert R.pack(p).action == "nothing"


def test_pack_snapshot_replaces_gz(tmp_path):
    p = tmp_path / "graph.json"
    p.write_text('{"v": 1}', encoding="utf-8")
    assert R.pack(p).action == "packed" and not p.exists()
    assert R.read_json(p) == {"v": 1}
    p.write_text('{"v": 2}', encoding="utf-8")  # a writer rewrites the plain file
    assert R.read_json(p) == {"v": 2}
    assert R.pack(p).action == "packed" and not p.exists()
    assert R.read_json(p) == {"v": 2}
    assert gzip.decompress(R.gz_path(p).read_bytes()) == b'{"v": 2}'


def test_pack_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for d in (a, b):
        d.mkdir()
        (d / "results.jsonl").write_text(_lines({"k": 1}), encoding="utf-8")
        R.pack(d / "results.jsonl")
    assert (a / "results.jsonl.gz").read_bytes() == (b / "results.jsonl.gz").read_bytes()


def test_verification_failure_leaves_files(tmp_path, monkeypatch):
    p = tmp_path / "responses.jsonl"
    R.gz_path(p).write_bytes(gzip.compress(_lines({"n": 1}).encode()))
    gz_before = R.gz_path(p).read_bytes()
    p.write_text(_lines({"n": 2}), encoding="utf-8")
    monkeypatch.setattr(R, "_gzip_member", lambda data: gzip.compress(data[:-2] + b"X\n"))
    rep = R.pack(p)
    assert rep.action == "refused" and "verification failed" in rep.reason
    assert p.read_text(encoding="utf-8") == _lines({"n": 2})
    assert R.gz_path(p).read_bytes() == gz_before
    assert sorted(x.name for x in tmp_path.iterdir()) == sorted([p.name, R.gz_path(p).name])  # no staging left


def test_pack_refuses_locked_log(tmp_path):
    from assistant_axis.gapgen import overlap_test as OT

    lock = OT.acquire_session_lock(tmp_path)
    try:
        (tmp_path / "responses.jsonl").write_text(_lines({"n": 1}), encoding="utf-8")
        rep = R.pack(tmp_path / "responses.jsonl")
        assert rep.action == "refused" and "locked" in rep.reason
        assert (tmp_path / "responses.jsonl").exists()
    finally:
        lock.close()
    assert R.pack(tmp_path / "responses.jsonl").action == "packed"


def test_pack_refuses_plain_copy_of_gz(tmp_path):
    """The 2026-10-14 layout of review_traits_all_2: a .gz and a plain copy of the same content."""
    p = tmp_path / "responses.jsonl"
    body = _lines({"n": 1}, {"n": 2})
    p.write_text(body, encoding="utf-8")
    R.gz_path(p).write_bytes(gzip.compress(body.encode()))
    rep = R.pack(p)
    assert rep.action == "refused" and "starts with the whole .gz content" in rep.reason
    assert p.exists()


def test_rewrite_jsonl_drops_gz(tmp_path):
    p = tmp_path / "responses.jsonl"
    R.gz_path(p).write_bytes(gzip.compress(_lines({"n": 1}).encode()))
    p.write_text(_lines({"n": 2}), encoding="utf-8")
    rows = R.read_jsonl(p)
    rows[0]["parse_error"] = "x"
    R.rewrite_jsonl(rows, p)
    assert not R.gz_path(p).exists()
    assert R.read_jsonl(p) == [{"n": 1, "parse_error": "x"}, {"n": 2}]


def test_estimate_packed_bytes(tmp_path):
    p = tmp_path / "responses.jsonl"
    p.write_text(_lines(*({"n": i, "text": "same words again"} for i in range(2000))), encoding="utf-8")
    est = R.estimate_packed_bytes(p)
    assert 0 < est < p.stat().st_size / 3


def test_flock_released_after_pack(tmp_path):
    p = tmp_path / "responses.jsonl"
    p.write_text(_lines({"n": 1}), encoding="utf-8")
    R.pack(p)
    with open(p, "a", encoding="utf-8") as fh:  # a new session can lock a fresh plain file
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_a_gz_name_that_is_not_a_record_stays_itself(tmp_path):
    p = tmp_path / "registry.snapshot.jsonl.gz"
    assert R.plain_path(p) == p and R.kind_of(p) is None
    p.write_bytes(gzip.compress(b"x\n"))
    assert R.exists(p) and R.read_bytes(p) == p.read_bytes()       # read as the bytes on disk, as before


def test_pack_refuses_an_interrupted_second_pack(tmp_path):
    """Review S1: a pack killed between its rename and the plain file's deletion leaves .gz = head + tail and plain =
    tail; packing again must refuse, not append the tail a second time."""
    p = tmp_path / "responses.jsonl"
    a, b = _lines({"n": 1}), _lines({"n": 2})
    R.gz_path(p).write_bytes(gzip.compress(a.encode()) + gzip.compress(b.encode()))
    p.write_text(b, encoding="utf-8")
    rep = R.pack(p)
    assert rep.action == "refused" and "already ends with" in rep.reason
    assert p.exists() and gzip.decompress(R.gz_path(p).read_bytes()) == (a + b).encode()


def test_pack_records_cli_reports_a_corrupt_gz(tmp_path, capsys):
    """Review S2: a truncated .gz is refused with its error, and the scan goes on."""
    from data_analysis.gap_generation import pack_records as PR
    p = tmp_path / "responses.jsonl"
    p.write_text(_lines({"n": 2}), encoding="utf-8")
    R.gz_path(p).write_bytes(gzip.compress(_lines({"n": 1}).encode())[:-6])
    assert PR.pack_one(p, dry_run=False) == "refused"
    assert "EOFError" in capsys.readouterr().err and p.exists()
