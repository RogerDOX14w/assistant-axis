"""Registry retractions (2026-10-15): ``registry.retract`` / ``unretract``, the folded view every reader gets, the
refusal on settled rows, the dry run, compaction, reversibility, and the byte-for-byte fold of a log without a
retraction.  No network."""
import argparse
import gzip
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.registry import (
    RETRACTION_NOTE, Candidate, Registry, compact, import_rows, read_snapshot, records_for_status, retract,
    retraction_key, submit_candidates, unretract,
)

BAD = ("structural", "r_bad")
GOOD = ("censuses", "r_ok")


def C(surface, run, *, gloss=None, ref=None):
    return Candidate(surface=surface, generator=run[0], run_id=run[1], gloss_hint=gloss, source_ref=ref)


@pytest.fixture
def reg(tmp_path):
    """A log with: ``grasping`` and ``adrift`` only from the bad run; ``smug`` from both runs, the bad run's gloss
    first; ``brave`` only from the good run."""
    p = tmp_path / "candidates" / "registry.jsonl"
    submit_candidates([C("grasping", BAD, gloss="craving honor", ref="s:1"), C("adrift", BAD, ref="s:2"),
                       C("smug", BAD, gloss="lecturing others", ref="s:3")], registry_path=p, relabel=None)
    submit_candidates([C("smug", GOOD, ref="c:1"), C("brave", GOOD, gloss="facing danger", ref="c:2")],
                      registry_path=p, relabel=None)
    return p


def _old_fold(p: Path) -> dict:
    """The fold as it was before retractions existed: the last line per key."""
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["key"]] = d
    return out


def _go(p, **kw):
    kw.setdefault("reason", "labels in odd senses")
    kw.setdefault("by", "tester")
    return retract(p, *BAD, **kw)


class TestFold:
    def test_a_log_without_retractions_folds_as_before(self, reg):
        rows = Registry(reg).fold()
        assert rows == _old_fold(reg) == Registry(reg).fold(raw=True)
        assert all(RETRACTION_NOTE not in r for r in rows.values())

    def test_retracted_run_leaves_the_fold(self, reg):
        rep = _go(reg)
        assert rep.written and rep.refused is None
        assert (rep.dropped, rep.changed, rep.gloss_hint_changed) == (["adrift#1", "grasping#1"], ["smug#1"],
                                                                      ["smug#1"])
        rows = Registry(reg).fold()
        assert sorted(rows) == ["brave#1", "smug#1"]
        smug = rows["smug#1"]
        assert [s["run_id"] for s in smug["sources"]] == ["r_ok"]
        assert smug[RETRACTION_NOTE] == {"runs": ["structural/r_bad"], "n_sources_removed": 1,
                                         "gloss_hint_changed": True, "relabel_cleared": False}
        assert rows["brave#1"] == _old_fold(reg)["brave#1"]                 # untouched rows are as written
        raw = Registry(reg).fold(raw=True)
        assert sorted(raw) == ["adrift#1", "brave#1", "grasping#1", "smug#1"]   # the log keeps everything
        assert len(raw["smug#1"]["sources"]) == 2
        assert retraction_key(*BAD) not in raw and Registry(reg).get("grasping#1") is None
        assert len(Registry(reg)) == 2

    def test_dangling_relabel_link_is_cleared(self, reg):
        Registry(reg).update("brave#1", {"relabel": {"from_key": "adrift#1", "rule": "x"}})
        _go(reg)
        b = Registry(reg).fold()["brave#1"]
        assert b["relabel"] is None and b[RETRACTION_NOTE]["relabel_cleared"]
        assert b[RETRACTION_NOTE]["relabel_was"] == {"from_key": "adrift#1", "rule": "x"}
        assert Registry(reg).fold(raw=True)["brave#1"]["relabel"] == {"from_key": "adrift#1", "rule": "x"}

    def test_writes_while_retracted_keep_the_retracted_sources(self, reg):
        _go(reg)
        Registry(reg).merge_block("smug#1", "filter", {"verdict": "trait"})
        unretract(reg, *BAD, reason="undo", by="tester")
        smug = Registry(reg).fold()["smug#1"]
        assert len(smug["sources"]) == 2 and smug["filter"] == {"verdict": "trait"}

    def test_write_refuses_a_control_key(self, reg):
        with pytest.raises(ValueError, match="control record"):
            Registry(reg).write([{"key": retraction_key(*BAD)}])
        _go(reg)
        with pytest.raises(ValueError, match="retraction record"):
            import_rows(reg, [retraction_key(*BAD)], registry_path=reg.with_name("other.jsonl"))


class TestReaders:
    """Every reader that folds sees the view: M1's run selection, M3's ``--run`` selection, the review graph's
    candidate load, the dashboard's row count."""

    def test_m1_run_selection(self, reg):
        _go(reg)
        assert records_for_status(Registry(reg), run=BAD) == []
        assert [r["key"] for r in records_for_status(Registry(reg), run=GOOD)] == ["brave#1", "smug#1"]
        with pytest.raises(KeyError):
            records_for_status(Registry(reg), keys=["grasping#1"])

    def test_m3_run_selection(self, reg):
        from data_analysis.gap_generation import novelty_score as NS
        args = argparse.Namespace(keys=None, run=[BAD], holding=None, rescore=False, include_held=False, limit=None)
        before = NS.select_candidates(Registry(reg).fold(), args, batch_id="b1")
        _go(reg)
        after = NS.select_candidates(Registry(reg).fold(), args, batch_id="b1")
        n = lambda res: len(res[0]) + sum(res[1].values())        # every selected row is a candidate or skipped
        assert (n(before), n(after)) == (3, 0)

    def test_review_graph_candidate_load(self, reg):
        from assistant_axis.gapgen import review_graph as RG
        reg_ = Registry(reg)
        for k in ("grasping#1", "smug#1", "brave#1"):
            reg_.merge_block(k, "novelty", {"run_id": "m3", "decision": "new"})
        assert sorted(RG.select_rows(reg_.fold(), ["m3"])[0]) == ["brave#1", "grasping#1", "smug#1"]
        _go(reg)
        assert sorted(RG.select_rows(Registry(reg).fold(), ["m3"])[0]) == ["brave#1", "smug#1"]

    def test_dashboard_row_count(self, reg):
        from data_analysis.gap_generation import generator_dashboard as GD
        args = argparse.Namespace(registry=reg, live=True)
        assert len(GD.load_rows(args)) == 4
        _go(reg)
        assert len(GD.load_rows(args)) == 2
        assert read_snapshot(reg) == Registry(reg).fold()


class TestRefusals:
    def test_settled_review_refuses_and_force_overrides(self, reg):
        Registry(reg).merge_block("smug#1", "review", {"status": "accepted"})
        before = reg.read_bytes()
        rep = _go(reg)
        assert rep.refused and rep.blocked == {"smug#1": "review accepted"} and not rep.written
        assert reg.read_bytes() == before
        rep = _go(reg, force=True)
        assert rep.written and rep.forced
        rec = Registry(reg).controls()[retraction_key(*BAD)]
        assert rec["forced"] and rec["effect"]["blocked_overridden"] == ["smug#1"]

    def test_seed_queue_and_queue_keys_refuse(self, reg):
        Registry(reg).update("adrift#1", {"seed_queue_stem": "adrift"})
        assert _go(reg).blocked == {"adrift#1": "seed queue entry adrift"}
        Registry(reg).update("adrift#1", {"seed_queue_stem": None})
        assert _go(reg, queue_keys=["grasping#1"]).blocked == {
            "grasping#1": "named by a seed-queue entry's gap_gen.registry_key"}

    def test_a_merge_into_a_dropped_row_refuses(self, reg):
        Registry(reg).merge_block("brave#1", "review", {"status": "merged_into", "into": "grasping#1"})
        rep = _go(reg)
        assert rep.refused and "brave#1" in rep.blocked

    def test_parked_is_not_settled(self, reg):
        Registry(reg).merge_block("grasping#1", "review", {"status": "parked"})
        assert _go(reg).written

    def test_unknown_run_and_double_retraction(self, reg):
        rep = retract(reg, "structural", "no_such_run", reason="x", by="t")
        assert rep.refused and "no row" in rep.refused
        _go(reg)
        assert "already retracted" in _go(reg).refused
        assert "not retracted" in unretract(reg, *GOOD, reason="x", by="t").refused
        with pytest.raises(ValueError):
            _go(reg, reason="  ")

    def test_dry_run_writes_nothing(self, reg):
        before = reg.read_bytes()
        rep = _go(reg, dry_run=True)
        assert not rep.written and rep.record["retracted"] and rep.dropped == ["adrift#1", "grasping#1"]
        assert reg.read_bytes() == before
        rep = _go(reg)
        before = reg.read_bytes()
        assert not unretract(reg, *BAD, reason="u", by="t", dry_run=True).written
        assert reg.read_bytes() == before


class TestReversibilityAndCompaction:
    def test_unretract_restores_the_fold_and_keeps_history(self, reg):
        before = Registry(reg).fold()
        _go(reg)
        rep = unretract(reg, *BAD, reason="the bug was elsewhere", by="tester")
        assert rep.dropped == ["adrift#1", "grasping#1"] and rep.written
        assert Registry(reg).fold() == before
        _go(reg, reason="again")
        rec = Registry(reg).controls()[retraction_key(*BAD)]
        assert rec["retracted"] and rec["reason"] == "again" and rec["rev"] == 3
        assert [h["action"] for h in rec["history"]] == ["retract", "unretract"]
        assert [h["reason"] for h in rec["history"]] == ["labels in odd senses", "the bug was elsewhere"]

    def test_compact_keeps_raw_rows_in_the_log_and_writes_the_view_to_the_snapshot(self, reg):
        _go(reg)
        view = Registry(reg).fold()
        rep = compact(reg, stamp="T")
        assert (rep.n_keys, rep.n_controls, rep.n_snapshot_rows) == (4, 1, 2)
        assert sorted(Registry(reg).fold(raw=True)) == ["adrift#1", "brave#1", "grasping#1", "smug#1"]
        assert Registry(reg).fold() == view
        snap = rep.snapshot_path
        lines = [json.loads(x) for x in gzip.decompress(snap.read_bytes()).decode().splitlines()]
        assert [d["key"] for d in lines] == ["brave#1", "smug#1", retraction_key(*BAD)]
        assert read_snapshot(snap) == view
        unretract(reg, *BAD, reason="undo after compaction", by="tester")
        assert sorted(Registry(reg).fold()) == ["adrift#1", "brave#1", "grasping#1", "smug#1"]

    def test_compact_of_a_log_without_retractions_is_unchanged(self, reg):
        old = _old_fold(reg)
        body = "".join(json.dumps(old[k], ensure_ascii=False) + "\n" for k in sorted(old)).encode()
        rep = compact(reg, stamp="T")
        assert reg.read_bytes() == body
        assert gzip.decompress(rep.snapshot_path.read_bytes()) == body
        assert (rep.n_controls, rep.n_snapshot_rows) == (0, 4)


class TestCli:
    def test_retract_dry_run_then_force(self, reg, tmp_path, capsys):
        from data_analysis.gap_generation import gap_registry as GR
        Registry(reg).merge_block("smug#1", "review", {"status": "merged_into", "into": "trait:arrogant"})
        q = tmp_path / "queue.json"
        q.write_text(json.dumps({"entries": []}))
        base = ["--registry", str(reg), "retract", "--run", "structural/r_bad", "--reason", "odd senses", "--by", "t",
                "--queue", str(q)]
        before = reg.read_bytes()
        assert GR.main(base + ["--dry-run"]) == 2                      # blocked, even on a dry run
        out = capsys.readouterr()
        assert "drops 2 rows" in out.out and "BLOCKED smug#1: review merged_into trait:arrogant" in out.out
        assert reg.read_bytes() == before
        assert GR.main(base + ["--force", "--dry-run"]) == 0 and reg.read_bytes() == before
        assert GR.main(base + ["--force"]) == 0
        assert GR.main(["--registry", str(reg), "retractions"]) == 0
        assert "RETRACTED" in capsys.readouterr().out
        assert GR.main(["--registry", str(reg), "unretract", "--run", "structural/r_bad", "--reason", "undo",
                        "--by", "t"]) == 0
        assert len(Registry(reg).fold()) == 4


class TestReviewFixes:
    """The Fable review of 2026-10-15: the refusal rule, view rows refused by write(), view notes not imported."""

    def test_a_settled_row_that_only_loses_a_source_is_reported_not_refused(self, reg):
        submit_candidates([C("brave", BAD, gloss="rash", ref="s:4")], registry_path=reg, relabel=None)
        Registry(reg).merge_block("brave#1", "review", {"status": "accepted", "at": "2026-10-11T00:00:00+00:00"})
        rep = _go(reg, dry_run=True)
        assert rep.refused is None and "brave#1" not in rep.blocked and rep.settled_changed == ["brave#1"]

    def test_a_gloss_change_reviewed_before_the_run_is_not_refused(self, reg, monkeypatch):
        import assistant_axis.gapgen.registry as R
        Registry(reg).merge_block("smug#1", "review", {"status": "accepted", "at": "2026-10-11T00:00:00+00:00"})
        monkeypatch.setattr(R, "_run_started_at", lambda g, r: "2026-10-14T01:00:00+00:00")
        rep = _go(reg, dry_run=True)
        assert rep.refused is None and rep.gloss_hint_changed == ["smug#1"]
        assert rep.gloss_hint_changed_after_run == []          # no filter.at: M1 judged before the run, or never
        monkeypatch.setattr(R, "_run_started_at", lambda g, r: "2026-10-01T00:00:00+00:00")
        assert _go(reg, dry_run=True).blocked == {"smug#1": "review accepted"}   # reviewed after the run: refuse

    def test_write_refuses_a_view_row(self, reg):
        _go(reg)
        view = Registry(reg).fold()["smug#1"]
        with pytest.raises(ValueError, match="retraction view"):
            Registry(reg).write([view])

    def test_import_from_a_snapshot_drops_the_view_note(self, reg, tmp_path):
        _go(reg)
        snap = compact(reg).snapshot_path                      # the snapshot holds the view, with the note
        assert RETRACTION_NOTE in {k: v for k, v in read_snapshot(snap).items()}["smug#1"]
        target = tmp_path / "t" / "registry.jsonl"
        import_rows(snap, ["smug#1"], registry_path=target)
        assert RETRACTION_NOTE not in Registry(target).fold(raw=True)["smug#1"]
