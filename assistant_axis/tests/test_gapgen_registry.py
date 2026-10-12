"""gapgen.registry and gapgen.runs: log fold, revs, source merge, blocks,
compaction, holding lists, submission idempotency, run bookkeeping."""
import gzip
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.registry import (
    Candidate, Registry, compact, holding_list, new_record, records_for_status, submit_candidates,
)
from assistant_axis.gapgen.runs import start_run


def _lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


@pytest.fixture
def reg_path(tmp_path):
    return tmp_path / "candidates" / "registry.jsonl"


def C(surface, **kw):
    base = dict(generator="wordnet_walk", run_id="r1")
    base.update(kw)
    return Candidate(surface=surface, **base)


class TestSubmit:
    def test_new_rows(self, reg_path):
        rep = submit_candidates([C("world-shaping", rank=1, score=0.7, source_ref="oewn:1-a"),
                                 C("kind to animals", rank=2)], registry_path=reg_path)
        assert (rep.n_submitted, rep.n_new, rep.n_merged) == (2, 2, 0)
        assert rep.keys == ["world_shaping#1", "kind_to_animals#1"]
        rows = Registry(reg_path).fold()
        r = rows["world_shaping#1"]
        assert r["stem"] == "world_shaping" and r["label"] == "world-shaping" and r["sense_id"] == 1
        assert r["rev"] == 1 and r["schema_version"] == 1 and r["entity_type"] == "trait"
        assert r["sources"] == [{"generator": "wordnet_walk", "run_id": "r1", "rank": 1, "score": 0.7,
                                 "source_ref": "oewn:1-a", "gloss_hint": None, "partner_hint": None,
                                 "surface": "world-shaping"}]
        assert r["review"]["status"] == "unreviewed" and r["filter"] is None and r["holding"] is None

    def test_idempotent_resubmit(self, reg_path):
        cands = [C("stubborn", source_ref="x:1"), C("vain", source_ref="x:2")]
        submit_candidates(cands, registry_path=reg_path)
        n_lines = len(_lines(reg_path))
        rep = submit_candidates(cands, registry_path=reg_path)
        assert (rep.n_new, rep.n_merged, rep.n_unchanged) == (0, 0, 2)
        assert len(_lines(reg_path)) == n_lines

    def test_same_surface_different_source_ref_merges(self, reg_path):
        """Interface resolution 4: merge, not drop."""
        rep = submit_candidates([C("gloomy", source_ref="roget:604"), C("gloomy", source_ref="roget:606")],
                                registry_path=reg_path)
        assert (rep.n_new, rep.n_merged) == (1, 1)
        r = Registry(reg_path).get("gloomy#1")
        assert [s["source_ref"] for s in r["sources"]] == ["roget:604", "roget:606"]
        assert len(_lines(reg_path)) == 1

    def test_other_generator_merges_without_duplicates(self, reg_path):
        submit_candidates([C("stubborn")], registry_path=reg_path)
        rep = submit_candidates([C("stubborn", generator="censuses", run_id="t1", score=0.9)],
                                registry_path=reg_path)
        assert (rep.n_new, rep.n_merged) == (0, 1)
        rep = submit_candidates([C("stubborn", generator="censuses", run_id="t1", score=0.9)],
                                registry_path=reg_path)
        assert rep.n_unchanged == 1
        r = Registry(reg_path).get("stubborn#1")
        assert len(r["sources"]) == 2 and r["rev"] == 2

    def test_sense_ids_are_separate_rows(self, reg_path):
        rep = submit_candidates([C("cool", sense_id=1), C("cool", sense_id=2)], registry_path=reg_path)
        assert rep.keys == ["cool#1", "cool#2"] and rep.n_new == 2

    def test_hints_carried_into_sources(self, reg_path):
        submit_candidates([C("flustered", gloss_hint="disposition to be flustered", partner_hint="unflappable")],
                          registry_path=reg_path)
        s = Registry(reg_path).get("flustered#1")["sources"][0]
        assert s["gloss_hint"] == "disposition to be flustered" and s["partner_hint"] == "unflappable"

    def test_invalid_surface_skipped(self, reg_path):
        rep = submit_candidates([C("!!!"), C("ok")], registry_path=reg_path)
        assert rep.invalid == ["!!!"] and rep.keys == ["ok#1"]

    def test_run_records_candidates(self, reg_path, tmp_path):
        run = start_run("wordnet_walk", "r1", args={"k": 1}, candidates_dir=tmp_path / "candidates")
        submit_candidates([C("stubborn"), C("vain")], registry_path=reg_path, run=run)
        submit_candidates([C("stubborn")], registry_path=reg_path, run=run)
        cj = _lines(run.dir / "candidates.jsonl")
        assert [c["surface"] for c in cj] == ["stubborn", "vain"]
        assert run.n_emitted == 2

    def test_the_record_is_written_before_the_log(self, reg_path, tmp_path, monkeypatch):
        """``candidates.jsonl`` (tracked) first, then the append to the git-ignored log (2026-10-08): when the
        append runs, the run's record already holds every candidate; a failed append leaves the record."""
        run = start_run("wordnet_walk", "r2", candidates_dir=tmp_path / "candidates")
        seen = []
        real = Registry._append

        def append(self, records):
            seen.append([c["surface"] for c in _lines(run.dir / "candidates.jsonl")])
            return real(self, records)
        monkeypatch.setattr(Registry, "_append", append)
        submit_candidates([C("stubborn"), C("vain")], registry_path=reg_path, run=run)
        assert seen == [["stubborn", "vain"]]

        def broken(self, records):
            raise OSError("disk full")
        monkeypatch.setattr(Registry, "_append", broken)
        with pytest.raises(OSError):
            submit_candidates([C("proud")], registry_path=reg_path, run=run)
        assert [c["surface"] for c in _lines(run.dir / "candidates.jsonl")] == ["stubborn", "vain", "proud"]
        assert "proud#1" not in Registry(reg_path).fold()

    def test_record_first_then_submit_without_a_run(self, reg_path, tmp_path):
        """The generators' own order (record, then ``run=None``) keeps working and records nothing twice."""
        run = start_run("censuses", "r1", candidates_dir=tmp_path / "candidates")
        cands = [C("stubborn"), C("vain")]
        run.record_candidates(cands)
        rep = submit_candidates(cands, registry_path=reg_path)
        assert rep.n_new == 2 and [c["surface"] for c in _lines(run.dir / "candidates.jsonl")] == ["stubborn", "vain"]
        submit_candidates(cands, registry_path=reg_path, run=run)                 # again, with the run: no change
        assert len(_lines(run.dir / "candidates.jsonl")) == 2 and run.n_emitted == 2


class TestLog:
    def test_fold_last_wins_and_rev_increments(self, reg_path):
        reg = Registry(reg_path)
        submit_candidates([C("stubborn")], registry_path=reg_path)
        reg.update("stubborn#1", {"gloss": "g1"})
        reg.update("stubborn#1", {"gloss": "g2"})
        lines = _lines(reg_path)
        assert [x["rev"] for x in lines] == [1, 2, 3]
        r = reg.get("stubborn#1")
        assert r["gloss"] == "g2" and r["rev"] == 3
        assert r["created_at"] == lines[0]["created_at"]

    def test_merge_block_touches_one_block(self, reg_path):
        reg = Registry(reg_path)
        submit_candidates([C("stubborn")], registry_path=reg_path)
        reg.merge_block("stubborn#1", "freq", {"zipf_min": 3.1, "hard_reject": False})
        before = reg.get("stubborn#1")
        after = reg.merge_block("stubborn#1", "filter", {"verdict": "trait", "tags": []})
        for k in before:
            if k not in ("filter", "rev", "updated_at"):
                assert after[k] == before[k], k
        assert after["filter"] == {"verdict": "trait", "tags": []}
        after2 = reg.merge_block("stubborn#1", "filter", {"confidence": 0.9})
        assert after2["filter"] == {"verdict": "trait", "tags": [], "confidence": 0.9}
        after3 = reg.merge_block("stubborn#1", "filter", {"verdict": "reject"}, replace=True)
        assert after3["filter"] == {"verdict": "reject"}

    def test_merge_block_rejects_non_block(self, reg_path):
        submit_candidates([C("stubborn")], registry_path=reg_path)
        with pytest.raises(ValueError):
            Registry(reg_path).merge_block("stubborn#1", "label", {"x": 1})

    def test_update_unknown_key(self, reg_path):
        submit_candidates([C("stubborn")], registry_path=reg_path)
        with pytest.raises(KeyError):
            Registry(reg_path).update("nope#1", {"gloss": "x"})

    def test_the_time_is_taken_under_the_writer_lock(self, reg_path, monkeypatch):
        """``updated_at`` follows the log's order (the fold's): every writer takes its time once it holds the lock,
        not before waiting for it (review 2026-10-12)."""
        import assistant_axis.gapgen.registry as R
        key = str(reg_path.resolve())
        held = []
        real = R.utc_now

        def stamp():
            held.append(key in R._held_paths())
            return real()
        monkeypatch.setattr(R, "utc_now", stamp)
        submit_candidates([C("stubborn")], registry_path=reg_path)
        reg = Registry(reg_path)
        reg.update("stubborn#1", {"gloss": "g"})
        reg.write([dict(reg.get("stubborn#1"), gloss="h")])
        assert held == [True, True, True]

    def test_malformed_line_skipped(self, reg_path):
        submit_candidates([C("stubborn")], registry_path=reg_path)
        with open(reg_path, "a") as fh:
            fh.write("{not json\n")
        assert list(Registry(reg_path).fold()) == ["stubborn#1"]


class TestCompact:
    def test_compact_reproduces_fold_and_leaves_bak(self, reg_path):
        reg = Registry(reg_path)
        submit_candidates([C("vain"), C("stubborn")], registry_path=reg_path)
        reg.update("stubborn#1", {"gloss": "g"})
        before = reg.fold()
        raw_before = reg_path.read_text()
        rep = compact(reg_path, stamp="20260928T000000Z")
        assert rep.backup_path.name == "registry.jsonl.bak.20260928T000000Z"
        assert rep.backup_path.read_text() == raw_before
        assert rep.n_lines_before == 3 and rep.n_keys == 2
        assert reg.fold() == before
        lines = _lines(reg_path)
        assert [x["key"] for x in lines] == ["stubborn#1", "vain#1"]
        # gzipped since 2026-10-12 (code review A5; was registry.snapshot.jsonl, uncompressed)
        assert rep.snapshot_path == reg_path.with_name("registry.snapshot.jsonl.gz")
        assert gzip.decompress(rep.snapshot_path.read_bytes()).decode() == reg_path.read_text()
        assert rep.n_bytes == len(reg_path.read_bytes()) and rep.snapshot_bytes == rep.snapshot_path.stat().st_size

    def test_compact_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            compact(tmp_path / "none.jsonl")


class TestGzippedSnapshot:
    """Code review 2026-10-12, A5: the snapshot is gzipped, every reader takes it, and an uncompressed one over
    the limit is refused before anything is written."""

    def _reg(self, reg_path):
        submit_candidates([C("vain"), C("stubborn"), C("timid")], registry_path=reg_path)
        Registry(reg_path).update("timid#1", {"gloss": "This means being shy and easily frightened."})
        return Registry(reg_path).fold()

    def test_the_same_content_gives_the_same_bytes(self, reg_path):
        self._reg(reg_path)
        first = compact(reg_path, stamp="20261012T000000Z").snapshot_path.read_bytes()
        second = compact(reg_path, stamp="20261012T000001Z").snapshot_path.read_bytes()
        assert first == second and first[:2] == b"\x1f\x8b"

    def test_registry_and_readers_take_the_gzipped_snapshot(self, reg_path):
        from assistant_axis.gapgen.registry import read_snapshot, snapshot_file
        folded = self._reg(reg_path)
        rep = compact(reg_path)
        assert Registry(rep.snapshot_path).fold() == folded
        assert read_snapshot(rep.snapshot_path) == folded
        assert snapshot_file(reg_path.parent) == rep.snapshot_path
        assert records_for_status(Registry(rep.snapshot_path)) == records_for_status(Registry(reg_path))

    def test_snapshot_file_falls_back_to_the_uncompressed_one(self, reg_path):
        from assistant_axis.gapgen.registry import read_snapshot, snapshot_file
        folded = self._reg(reg_path)
        rep = compact(reg_path, uncompressed=True)
        assert rep.snapshot_path.name == "registry.snapshot.jsonl" and rep.snapshot_bytes == rep.n_bytes
        assert snapshot_file(reg_path.parent) == rep.snapshot_path and read_snapshot(rep.snapshot_path) == folded

    def test_a_gzipped_snapshot_is_read_only(self, reg_path):
        self._reg(reg_path)
        rep = compact(reg_path)
        before = rep.snapshot_path.read_bytes()
        with pytest.raises(ValueError, match="read-only"):
            Registry(rep.snapshot_path).update("vain#1", {"gloss": "g"})
        with pytest.raises(ValueError, match="gzipped snapshot"):
            compact(rep.snapshot_path)
        assert rep.snapshot_path.read_bytes() == before

    def test_an_uncompressed_snapshot_over_the_limit_is_refused(self, reg_path, monkeypatch):
        import assistant_axis.gapgen.registry as R
        self._reg(reg_path)
        raw = reg_path.read_bytes()
        monkeypatch.setattr(R, "SNAPSHOT_UNCOMPRESSED_MAX_BYTES", 100)
        with pytest.raises(ValueError, match="over the 0 MB limit"):
            compact(reg_path, uncompressed=True)
        assert reg_path.read_bytes() == raw                                  # nothing written: no fold, no backup
        assert not list(reg_path.parent.glob("registry.jsonl.bak.*"))
        assert not list(reg_path.parent.glob("registry.snapshot*"))
        assert compact(reg_path).snapshot_path.name == "registry.snapshot.jsonl.gz"   # the gzipped one has no limit

    def test_a_stale_uncompressed_snapshot_is_reported(self, reg_path):
        self._reg(reg_path)
        compact(reg_path, uncompressed=True)
        rep = compact(reg_path)
        assert rep.stale_snapshot == reg_path.with_name("registry.snapshot.jsonl")
        assert rep.stale_snapshot.exists()                                   # reported, not deleted


class TestQueries:
    def _setup(self, reg_path):
        reg = Registry(reg_path)
        submit_candidates([C("tall"), C("librarian"), C("stubborn"),
                           C("vain", generator="censuses", run_id="t1")], registry_path=reg_path)
        reg.update_many({
            "tall#1": {"holding": "physical", "filter": {"verdict": "tagged", "tags": ["physical"]}},
            "librarian#1": {"holding": "roles", "entity_type": "role",
                            "filter": {"verdict": "tagged", "tags": ["role_person"]}},
            "stubborn#1": {"filter": {"verdict": "trait", "tags": []}},
        })
        return reg

    def test_holding_list(self, reg_path):
        reg = self._setup(reg_path)
        assert [r["key"] for r in holding_list("physical", registry=reg)] == ["tall#1"]
        assert [r["key"] for r in holding_list("roles", registry=reg)] == ["librarian#1"]
        with pytest.raises(ValueError):
            holding_list("other", registry=reg)

    def test_records_for_status(self, reg_path):
        reg = self._setup(reg_path)
        assert [r["key"] for r in records_for_status(reg, unfiltered=True)] == ["vain#1"]
        assert [r["key"] for r in records_for_status(reg, verdict="trait")] == ["stubborn#1"]
        assert [r["key"] for r in records_for_status(reg, run=("censuses", "t1"))] == ["vain#1"]
        assert [r["key"] for r in records_for_status(reg, run=("wordnet_walk", "r1"), unfiltered=True)] == []
        assert len(records_for_status(reg, review="unreviewed")) == 4
        with pytest.raises(KeyError):
            records_for_status(reg, keys=["nope#1"])


class TestRuns:
    def test_finish_always_writes_usage(self, tmp_path):
        run = start_run("censuses", "2026-10-06a", args={"stage": "tda"}, candidates_dir=tmp_path)
        assert run.dir == tmp_path / "runs" / "censuses" / "2026-10-06a"
        run.log("hello")
        run.finish()
        usage = json.loads((run.dir / "usage.json").read_text())
        assert usage["n_calls"] == 0 and usage["total_cost_usd"] == 0
        rj = json.loads((run.dir / "run.json").read_text())
        assert rj["args"] == {"stage": "tda"} and rj["n_emitted"] == 0
        assert rj["started_at"].endswith("+00:00") and rj["finished_at"].endswith("+00:00")
        assert "hello" in (run.dir / "run.log").read_text()

    def test_usage_charged(self, tmp_path):
        run = start_run("g", "r", candidates_dir=tmp_path)
        run.usage.charge("claude-haiku-4-5-20251001", 1000, 100)
        run.finish(n_emitted=5)
        usage = json.loads((run.dir / "usage.json").read_text())
        assert usage["n_calls"] == 1
        assert json.loads((run.dir / "run.json").read_text())["n_emitted"] == 5


def test_new_record_schema():
    r = new_record("World-Shaping", sense_id=2, now="2026-09-28T00:00:00+00:00")
    assert r["key"] == "world_shaping#2" and r["label"] == "World-Shaping"
    assert r["created_at"] == r["updated_at"] == "2026-09-28T00:00:00+00:00"
    for k in ("freq", "wordnet", "filter", "novelty", "holding", "matches_existing", "heldout_hit",
              "seed_queue_stem", "gloss"):
        assert r[k] is None
