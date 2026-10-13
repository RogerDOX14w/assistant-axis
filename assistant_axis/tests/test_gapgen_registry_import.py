"""Rows a run left in another checkout's registry log, brought into this one (regeneration list GG5, 2026-10-13):
``registry.import_rows`` and ``gap_registry.py import-rows``; and the embedding-cache merge that lets
``novelty_score.py score --redecide`` replay such a run (``embed.merge_cache``, ``novelty_score.py cache-merge``)."""
import gzip
import json
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen import embed as EM
from assistant_axis.gapgen.registry import Candidate, Registry, import_rows, submit_candidates

RUN = ("alignment_sweep", "2026-10-10-full")


def C(surface, generator="alignment_sweep", run_id="2026-10-10-full", **kw):
    return Candidate(surface=surface, generator=generator, run_id=run_id, **kw)


def _strip(r):
    return {k: v for k, v in r.items() if k not in ("rev", "updated_at")}


def _n_lines(p: Path) -> int:
    return sum(1 for x in p.read_text(encoding="utf-8").splitlines() if x.strip())


@pytest.fixture
def logs(tmp_path):
    """A worktree log (``src``): the run submitted, filtered and scored there, interleaved with another key; a main
    log (``dst``) that already has one of the run's keys (from a later run, with newer blocks) and an unrelated
    key."""
    src = tmp_path / "worktree" / "registry.jsonl"
    dst = tmp_path / "main" / "registry.jsonl"
    s = Registry(src)
    submit_candidates([C("refuses grave harm", source_ref="spec:a", gloss_hint="hint a"),
                       C("accepts oversight", source_ref="spec:b"),
                       C("checks intent", source_ref="spec:c")], registry_path=src)
    s.update_many({"refuses_grave_harm#1": {"filter": {"verdict": "trait", "batch_id": "f_full"}, "gloss": "g1"},
                   "checks_intent#1": {"filter": {"verdict": "reject", "batch_id": "f_full"}}}, now="2026-10-10T23:39:00+00:00")
    s.merge_block("accepts_oversight#1", "filter", {"verdict": "trait", "batch_id": "f_full"},
                  now="2026-10-10T23:40:00+00:00")
    s.merge_block("refuses_grave_harm#1", "novelty", {"decision": "new", "run_id": "m3_full"},
                  now="2026-10-11T04:20:00+00:00")
    # main: accepts oversight came in later through another run and was judged there
    submit_candidates([C("accepts oversight", run_id="2026-10-11-papers", source_ref="paper:9"),
                       C("unrelated", generator="censuses", run_id="tda")], registry_path=dst)
    d = Registry(dst)
    d.update_many({"accepts_oversight#1": {"filter": {"verdict": "trait", "batch_id": "f_papers_rejudge"},
                                           "novelty": {"decision": "covered", "run_id": "m3_papers_r3"}}})
    return src, dst


class TestImportRows:
    def test_absent_keys_replay_the_source_lines_and_present_keys_gain_only_the_source(self, logs):
        src, dst = logs
        before = Registry(dst).fold()
        n_before = _n_lines(dst)
        keys = ["refuses_grave_harm#1", "accepts_oversight#1", "checks_intent#1"]
        rep = import_rows(src, keys, registry_path=dst, only_run=RUN)
        after, s = Registry(dst).fold(), Registry(src).fold()
        # the two absent keys: every source line replayed (3 and 2), the fold the source's but for the stamps
        assert {k: len(v) for k, v in rep.replayed.items()} == {"refuses_grave_harm#1": 3, "checks_intent#1": 2}
        for k in ("refuses_grave_harm#1", "checks_intent#1"):
            assert _strip(after[k]) == _strip(s[k])
            assert after[k]["rev"] == s[k]["rev"] and after[k]["created_at"] == s[k]["created_at"]
        # the present key: its newer blocks kept, the run's source appended, nothing else
        a, b = after["accepts_oversight#1"], before["accepts_oversight#1"]
        assert a["filter"] == b["filter"] and a["novelty"] == b["novelty"]
        assert a["sources"][:-1] == b["sources"] and (a["sources"][-1]["generator"], a["sources"][-1]["run_id"]) == RUN
        assert a["rev"] == b["rev"] + 1
        # (updated_at has one-second resolution, so it may equal the fixture's)
        assert {f for f in a if a[f] != b[f]} - {"updated_at"} == {"rev", "sources"} and set(a) == set(b)
        # nothing else touched
        assert after["unrelated#1"] == before["unrelated#1"]
        assert rep.n_lines_written == 3 + 2 + 1 == _n_lines(dst) - n_before
        assert rep.verified is True and rep.mismatches == {}

    def test_the_source_order_is_kept_across_keys(self, logs):
        src, dst = logs
        import_rows(src, ["refuses_grave_harm#1", "checks_intent#1"], registry_path=dst)
        src_order = [r["key"] for r in Registry(src).iter_lines()
                     if r["key"] in ("refuses_grave_harm#1", "checks_intent#1")]
        new = [r["key"] for r in Registry(dst).iter_lines()][-len(src_order):]
        assert new == src_order

    def test_idempotent(self, logs):
        src, dst = logs
        keys = ["refuses_grave_harm#1", "accepts_oversight#1", "checks_intent#1"]
        import_rows(src, keys, registry_path=dst, only_run=RUN)
        snap = dst.read_bytes()
        rep = import_rows(src, keys, registry_path=dst, only_run=RUN)
        assert rep.n_lines_written == 0 and sorted(rep.unchanged) == sorted(keys)
        assert dst.read_bytes() == snap

    def test_dry_run_writes_nothing(self, logs):
        src, dst = logs
        snap = dst.read_bytes()
        rep = import_rows(src, ["refuses_grave_harm#1", "accepts_oversight#1"], registry_path=dst, dry_run=True)
        assert dst.read_bytes() == snap
        assert rep.counts()["lines_planned"] == 3 + 1 and rep.n_lines_written == 0 and rep.verified is None

    def test_only_run_limits_the_sources_added(self, logs, tmp_path):
        src, dst = logs
        # the worktree row also carries a source of another run that main lacks
        submit_candidates([C("accepts oversight", generator="censuses", run_id="pilot")], registry_path=src)
        rep = import_rows(src, ["accepts_oversight#1"], registry_path=dst, only_run=RUN)
        assert [(x["generator"], x["run_id"]) for x in rep.sources_added["accepts_oversight#1"]] == [RUN]
        rep = import_rows(src, ["accepts_oversight#1"], registry_path=dst)       # no filter: the other one too
        assert [(x["generator"], x["run_id"]) for x in rep.sources_added["accepts_oversight#1"]] == [("censuses", "pilot")]

    def test_refusals_write_nothing(self, logs, tmp_path):
        src, dst = logs
        snap = dst.read_bytes()
        with pytest.raises(ValueError, match="not in"):
            import_rows(src, ["refuses_grave_harm#1", "no_such_key#1"], registry_path=dst)
        bad = tmp_path / "bad" / "registry.jsonl"
        bad.parent.mkdir()
        bad.write_text(src.read_text() + '{"key": "torn\n')
        with pytest.raises(ValueError, match="malformed"):
            import_rows(bad, ["refuses_grave_harm#1"], registry_path=dst)
        gz = dst.with_name("registry.snapshot.jsonl.gz")
        gz.write_bytes(gzip.compress(dst.read_bytes()))
        with pytest.raises(ValueError, match="read-only"):
            import_rows(src, ["refuses_grave_harm#1"], registry_path=gz)
        with pytest.raises(ValueError, match="same file"):
            import_rows(dst, ["unrelated#1"], registry_path=dst)
        assert dst.read_bytes() == snap

    def test_the_source_is_read_without_creating_anything_there(self, logs):
        src, dst = logs
        Registry(src).lock_path.unlink(missing_ok=True)
        listing = sorted(p.name for p in src.parent.iterdir())
        import_rows(src, ["refuses_grave_harm#1"], registry_path=dst)
        import_rows(src, ["checks_intent#1"], registry_path=dst, dry_run=True)
        assert sorted(p.name for p in src.parent.iterdir()) == listing

    def test_a_gzipped_snapshot_is_a_valid_source(self, logs, tmp_path):
        src, dst = logs
        gz = tmp_path / "snap" / "registry.snapshot.jsonl.gz"
        gz.parent.mkdir()
        gz.write_bytes(gzip.compress(src.read_bytes()))
        rep = import_rows(gz, ["refuses_grave_harm#1"], registry_path=dst)
        assert rep.verified and len(rep.replayed["refuses_grave_harm#1"]) == 3


class TestImportRowsCli:
    def test_import_record_rerun_and_dry_run(self, logs, tmp_path, capsys):
        from data_analysis.gap_generation import gap_registry as GR
        src, dst = logs
        kf = tmp_path / "keys.txt"
        kf.write_text("# the run's keys\nrefuses_grave_harm#1\n\naccepts_oversight#1\nchecks_intent#1\n")
        assert GR.read_keys_file(kf) == ["refuses_grave_harm#1", "accepts_oversight#1", "checks_intent#1"]
        rec = tmp_path / "import.json"
        base = ["--registry", str(dst), "import-rows", "--from", str(src), "--keys-file", str(kf),
                "--only-run", "/".join(RUN)]
        snap = dst.read_bytes()
        assert GR.main(base + ["--dry-run"]) == 0
        assert dst.read_bytes() == snap and not rec.exists()
        assert "DRY-RUN: would import 3 keys" in capsys.readouterr().out
        assert GR.main(base + ["--record", str(rec)]) == 0
        out = capsys.readouterr().out
        assert "2 new keys replayed with 5 lines" in out and "1 existing keys gaining 1 sources" in out
        assert "verified" in out
        body = json.loads(rec.read_text())["result"]
        assert body["counts"]["n_lines_written"] == 6 and body["only_run"] == "/".join(RUN)
        assert set(body["replayed"]) == {"refuses_grave_harm#1", "checks_intent#1"} and len(body["source_sha256"]) == 64
        # a record is never overwritten; a rerun without one is a no-op
        assert GR.main(base + ["--record", str(rec)]) == 2
        assert GR.main(base) == 0
        assert "0 lines appended" in capsys.readouterr().out
        assert GR.main(["--registry", str(dst), "import-rows", "--from", str(src), "--keys-file", str(kf),
                        "--only-run", "no-slash"]) == 2


class TestMergeCache:
    def _cache(self, root: Path, items: dict, model="text-embedding-3-large", tag="openai_text-embedding-3-large"):
        c = EM.EmbeddingCache(root)
        c.put(tag, list(items), np.asarray(list(items.values()), dtype=np.float32), model_id=model)
        c.save()
        return c

    def test_adds_what_the_target_lacks_and_never_replaces(self, tmp_path):
        tag = "openai_text-embedding-3-large"
        src = tmp_path / "wt" / "embeddings"
        dst = tmp_path / "main" / "embeddings"
        self._cache(src, {"a": [1, 0, 0], "b": [0, 1, 0], "c": [0, 0, 1]})
        self._cache(dst, {"b": [0, 1, 0], "c": [0, 0.5, 0.5], "z": [1, 1, 0]})
        src_listing = sorted(p.name for p in src.iterdir())
        res = EM.merge_cache(src, EM.EmbeddingCache(dst), dry_run=True)
        assert res[tag]["n_added"] == 1 and res[tag]["n_same"] == 1 and res[tag]["n_differ"] == 1
        assert EM.EmbeddingCache(dst).get(tag, "a") is None                    # the dry run wrote nothing
        res = EM.merge_cache(src, EM.EmbeddingCache(dst))
        fresh = EM.EmbeddingCache(dst)
        assert np.allclose(fresh.get(tag, "a"), [1, 0, 0])
        assert np.allclose(fresh.get(tag, "c"), [0, 0.5, 0.5])                 # the target's vector kept
        assert np.allclose(fresh.get(tag, "z"), [1, 1, 0])
        assert json.loads((dst / "manifest.json").read_text())[tag]["n"] == 4
        assert sorted(p.name for p in src.iterdir()) == src_listing           # nothing created in the source
        assert EM.merge_cache(src, EM.EmbeddingCache(dst))[tag]["n_added"] == 0   # idempotent

    def test_refuses_another_model(self, tmp_path):
        src, dst = tmp_path / "s", tmp_path / "d"
        self._cache(src, {"a": [1, 0]}, model="m1", tag="t")
        self._cache(dst, {"b": [0, 1]}, model="m2", tag="t")
        with pytest.raises(ValueError, match="model"):
            EM.merge_cache(src, EM.EmbeddingCache(dst))

    def test_cli(self, tmp_path, capsys):
        from data_analysis.gap_generation import novelty_score as NS
        src, dst = tmp_path / "s", tmp_path / "d"
        self._cache(src, {"a": [1, 0, 0]})
        self._cache(dst, {"b": [0, 1, 0]})
        assert NS.main(["cache-merge", "--from", str(src), "--cache-dir", str(dst), "--dry-run"]) == 0
        assert "would add 1" in capsys.readouterr().out
        assert EM.EmbeddingCache(dst).get("openai_text-embedding-3-large", "a") is None
        assert NS.main(["cache-merge", "--from", str(src), "--cache-dir", str(dst)]) == 0
        assert "added 1" in capsys.readouterr().out
        assert EM.EmbeddingCache(dst).get("openai_text-embedding-3-large", "a") is not None
        assert NS.main(["cache-merge", "--from", str(dst), "--cache-dir", str(dst)]) == 2
