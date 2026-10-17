"""Corpus-frames generator: locating, planning and streaming the Books shards on gzipped fixtures (plan section 8,
``books``).  No network: every request goes to a watched fake fetcher."""
import json

import pytest

from assistant_axis.gapgen.generators.corpus_frames import books as B
from assistant_axis.gapgen.generators.corpus_frames import frames as F
from assistant_axis.tests.corpus_frames_fakes import FakeShards, fixture_fetcher, gz

#: Scripted heads of ten 3-gram shards (sorted in byte order; ``very_ADJ`` after the untagged ``very`` block).
SCRIPTED = ["a", "about", "an inc", "man of", "too ", "too_ADV", "very ", "very good man", "very_ADJ", "zebra"]


def scripted_heads(heads=SCRIPTED) -> B.Heads:
    fetch = FakeShards({3: [[f"{h}\t2000,1,1"] for h in heads]})
    return B.Heads(fetch, n_shards={3: len(heads)})


def test_first_ngram_reads_only_the_first_line():
    blob = gz(["very honest man\t1921,3,2", "very kind man\t1950,1,1"])
    assert B.first_ngram(blob) == "very honest man"
    assert B.first_ngram(blob[:8]) is None


def test_locate_inside_one_shard_and_spanning_two():
    h = scripted_heads()
    assert B.locate(3, "man of ", heads=h) == B.Span(3, "man of ", 3, 3)
    sp = B.locate(3, "very ", heads=h)
    assert (sp.start, sp.end) == (6, 7)          # spans two shards; stops before very_ADJ (the tagged block)
    assert B.locate(3, "too ", heads=h) == B.Span(3, "too ", 4, 4)   # too_ADV sorts after the untagged block
    assert B.locate(3, "an incorrigible ", heads=h) == B.Span(3, "an incorrigible ", 2, 2)
    assert h.n_peeks <= 10 and h.peek_bytes > 0


def test_the_end_key_closes_the_untagged_block():
    assert "very honest man" < "very " + B.END_SENTINEL < "very_ADJ sergeant_NOUN"
    assert "very good-natured man" < "very " + B.END_SENTINEL


def test_shard_plan_lists_each_shard_once_with_every_frame_it_serves():
    fetch = fixture_fetcher()
    frames = [F.FRAME_BY_ID[k] for k in ("d_very", "d_too", "d_too_to", "n_incorrigible", "p_man_of",
                                         "p_known_for_his", "h_he_was_always")]
    plan = B.shard_plan(frames, fetch=fetch, n_shards=fetch.n_shards, tier="1")
    names = [s.name for s in plan.shards]
    assert len(names) == len(set(names))
    by = {s.name: s for s in plan.shards}
    assert set(by["3-00002"].frames) >= {"d_very", "d_too", "d_too_to"}     # too and very share shard 2
    assert plan.frame_spans["d_too"] == plan.frame_spans["d_too_to"]
    assert plan.total_bytes == sum(len(fetch._blob(s.url)) for s in plan.shards)   # summed from Content-Length
    assert plan.total_gb == round(plan.total_bytes / 1e9, 2) and plan.n_shards == len(plan.shards)
    assert plan.bank_sha256 == F.bank_sha256()
    assert sum(1 for c in fetch.calls if c[0] == "size") == plan.n_shards
    assert all(c[0] in ("range", "size") for c in fetch.calls)               # head-peeks only: nothing streamed
    again = B.ShardPlan.from_dict(json.loads(json.dumps(plan.as_dict())))
    assert again.as_dict() == plan.as_dict()


def test_stream_shard_sums_years_from_1920_in_one_pass():
    lines = ["too clever to\t1950,70,60", "too honest man\t1950,3,3",
             "very good man\t1919,100,50\t1950,10,5", "very honest man\t1921,3,2", "very honest woman\t1930,40,30",
             "very the man\t1950,9,9", "very_ADJ sergeant_NOUN\t1950,5,5"]
    fetch = FakeShards({3: [lines]}, )
    url = B.shard_url(3, 0, n_shards={3: 1})
    frames = [F.FRAME_BY_ID[k] for k in ("d_very", "d_too", "d_too_to")]
    res = B.stream_shard(url, frames, fetch=fetch)
    assert [c for c in fetch.calls if c[0] == "stream"] == [("stream", url)]           # one pass
    very = {(h.filler, h.noun): (h.match, h.volumes) for h in res.hits["d_very"]}
    assert very == {("good", "man"): (10, 5), ("honest", "man"): (3, 2), ("honest", "woman"): (40, 30)}
    assert {(h.filler, h.noun) for h in res.hits["d_too"]} == {("honest", "man")}
    assert {(h.filler, h.noun) for h in res.hits["d_too_to"]} == {("clever", "to")}
    assert res.lines["d_very"][0] == "very good man\t1910,100,50\t1950,10,5"          # decade sums kept on disk
    assert res.lines_scanned == len(lines) and res.bytes_streamed == len(fetch._blob(url))
    older = B.stream_shard(url, frames, fetch=fetch, year_min=1900)                    # the cutoff moves it
    assert {(h.filler, h.noun): h.match for h in older.hits["d_very"]}[("good", "man")] == 110
    assert B.parse_counts(["1919,100,50"]) == (0, 0)                                   # a 1919 line adds nothing


def test_read_extract_reproduces_the_stream_and_moves_the_cutoff(tmp_path):
    p = tmp_path / "d_very.tsv"
    B.write_extract(["very good man\t1919,100,50\t1950,10,5", "very good woman\t1950,1,1", "noise"], p)
    hs = B.read_extract(p, F.FRAME_BY_ID["d_very"])
    assert [(h.filler, h.noun, h.match) for h in hs] == [("good", "man", 10), ("good", "woman", 1)]
    assert B.read_extract(p, F.FRAME_BY_ID["d_very"], year_min=1900)[0].match == 110


def _plan(fetch, keys=("d_very", "d_too", "d_too_to", "n_incorrigible", "p_man_of")):
    return B.shard_plan([F.FRAME_BY_ID[k] for k in keys], fetch=fetch, n_shards=fetch.n_shards)


def test_the_approval_gate_refuses_before_any_request(tmp_path):
    fetch = fixture_fetcher()
    plan = _plan(fetch)
    fetch.calls.clear()
    for given in (None, "", "   "):
        with pytest.raises(B.NotApproved):
            B.run_stream(plan, approved_by=given, fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                         echo=lambda *a: None)
    assert fetch.calls == [] and not any(tmp_path.iterdir())
    dry = B.run_stream(plan, approved_by=None, fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                       dry_run=True, echo=lambda *a: None)
    assert fetch.calls == [] and dry.dry_run_lines and not any(tmp_path.iterdir())


def test_stream_writes_extracts_and_a_manifest_and_resume_skips(tmp_path):
    fetch = fixture_fetcher()
    plan = _plan(fetch)
    fetch.calls.clear()
    appr = "Roger, 2026-10-14: open decision 1 (b), both tiers streamed"
    src = tmp_path / "sources_manifest.json"
    rep = B.run_stream(plan, approved_by=appr, fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                       parallel=2, sources_manifest_path=src, echo=lambda *a: None, git_sha="abc")
    assert not rep.failed and sorted(rep.streamed) == sorted(s.name for s in plan.shards)
    assert sorted(c[1] for c in fetch.calls if c[0] == "stream") == sorted(s.url for s in plan.shards)
    man = json.loads((tmp_path / "DOWNLOAD_MANIFEST.json").read_text())
    assert man["approvals"] == [appr] and man["licence"]["name"].startswith("CC BY 3.0")
    assert man["bytes_streamed"] == plan.total_bytes == rep.bytes_streamed
    assert all(r["approval"] == appr and r["bytes_streamed"] == r["content_length"] for r in man["shards"])
    lines = (tmp_path / "d_very.tsv").read_text().splitlines()
    assert lines == sorted(lines, key=lambda s: s.encode()) and "very honest man\t1920,300,200" in lines
    assert not any("_ADJ" in x or "Christian" in x for x in lines)
    ex = man["extracts"]["d_very"]
    assert ex["lines"] == len(lines) and ex["sha256"] == B.sha256_file(tmp_path / "d_very.tsv")
    assert json.loads(src.read_text())["books"] == man                     # the tracked copy
    # resume: nothing streamed again; without --resume (or --force) the stream is refused
    fetch.calls.clear()
    again = B.run_stream(plan, approved_by=appr, fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                         resume=True, echo=lambda *a: None)
    assert again.streamed == [] and len(again.skipped) == plan.n_shards and fetch.calls == []
    with pytest.raises(SystemExit):
        B.run_stream(plan, approved_by=appr, fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                     echo=lambda *a: None)
    assert fetch.calls == []


def test_a_shard_with_new_frames_is_streamed_again_on_resume(tmp_path):
    fetch = fixture_fetcher()
    plan = _plan(fetch, keys=("d_very",))
    B.run_stream(plan, approved_by="Roger", fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                 echo=lambda *a: None)
    wider = _plan(fetch, keys=("d_very", "d_too"))
    fetch.calls.clear()
    rep = B.run_stream(wider, approved_by="Roger", fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                       resume=True, echo=lambda *a: None)
    shared = {s.name for s in wider.shards if "d_too" in s.frames}
    assert set(rep.streamed) == shared and (tmp_path / "d_too.tsv").exists()


def test_a_short_stream_is_a_failed_shard_not_a_record(tmp_path):
    fetch = fixture_fetcher()
    plan = _plan(fetch, keys=("p_man_of",))
    plan.shards[0].bytes += 10                                      # the plan says more than the server sends
    rep = B.run_stream(plan, approved_by="Roger", fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                       echo=lambda *a: None)
    assert plan.shards[0].name in rep.failed
    assert B.done_record(tmp_path / B.PARTS_DIRNAME / plan.shards[0].name) is None


def test_decade_sums_keep_the_1920_cutoff_exact():
    line = "very good man\t1919,100,50\t1920,3,2\t1925,4,4\t1931,1,1\tbad\t1932,x,1"
    d = B.decade_line(line)
    assert d == "very good man\t1910,100,50\t1920,7,6\t1930,1,1"
    for y in (1900, 1910, 1920, 1930, 1940):
        assert B.parse_counts(d.split("\t")[1:], year_min=y) == B.parse_counts(line.split("\t")[1:], year_min=y)
    assert B.parse_counts(d.split("\t")[1:], year_min=1925) == (1, 1)    # inside a decade: from the next one
    assert len(d) < len(line)


# --------------------------------------------------------------------------- review fixes (2026-10-17)

def test_a_stale_plan_is_refused_before_any_request(tmp_path):
    """S1: a frame's prefix (or n) edited under the same id: the plan's shards would be the wrong ones."""
    import dataclasses
    fetch = fixture_fetcher()
    plan = _plan(fetch, keys=("d_very", "d_too"))
    fetch.calls.clear()
    really = dataclasses.replace(F.FRAME_BY_ID["d_very"], prefix=("really",))
    assert B.stale_frames(plan, [really, F.FRAME_BY_ID["d_too"]]) == ["d_very"]
    four = dataclasses.replace(F.FRAME_BY_ID["d_too"], n=4)
    assert B.stale_frames(plan, [four]) == ["d_too"]
    assert B.stale_frames(plan, [F.FRAME_BY_ID["n_born"]]) == ["n_born"]          # no span at all
    note = dataclasses.replace(F.FRAME_BY_ID["d_very"], note="edited", tier=2)
    assert B.stale_frames(plan, [note]) == []                                    # a note or a tier: still placed
    by_id = {**F.FRAME_BY_ID, "d_very": really}
    with pytest.raises(B.StalePlan) as e:
        B.run_stream(plan, approved_by="Roger", fetch=fetch, frames_by_id=by_id, external_dir=tmp_path,
                     echo=lambda *a: None)
    assert "d_very" in str(e.value) and "locate" in str(e.value)
    assert fetch.calls == [] and not any(tmp_path.iterdir())


def test_fillers_count_only_matches_after_the_cutoff(tmp_path):
    """M3: a line whose every match is before 1920 is kept (the cutoff can move) but is not a filler."""
    fetch = FakeShards({3: [["very good man\t1919,100,50", "very kind man\t1950,40,30"]]})
    plan = B.shard_plan([F.FRAME_BY_ID["d_very"]], fetch=fetch, n_shards=fetch.n_shards)
    B.run_stream(plan, approved_by="Roger", fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                 echo=lambda *a: None)
    rec = B.done_record(tmp_path / B.PARTS_DIRNAME / plan.shards[0].name)
    assert rec["lines_kept"]["d_very"] == 2 and rec["fillers"]["d_very"] == 1


class FlakyShards(FakeShards):
    """The first stream of each shard is a shorter, valid gzip (a cut the gzip reader cannot see)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.cut = set()

    def stream(self, url):
        import io
        self.calls.append(("stream", url))
        if url not in self.cut:
            self.cut.add(url)
            return io.BytesIO(gz(["very good man\t1950,1,1"]))
        return io.BytesIO(self._blob(url))


def test_a_short_stream_is_retried(tmp_path):
    """M4: the bytes-streamed check is inside the retry loop."""
    lines = ["very good man\t1950,4000,3000", "very honest man\t1950,300,200", "very kind fellow\t1950,500,400"]
    fetch = FlakyShards({3: [lines]})
    plan = B.shard_plan([F.FRAME_BY_ID["d_very"]], fetch=fetch, n_shards=fetch.n_shards)
    fetch.calls.clear()
    rep = B.run_stream(plan, approved_by="Roger", fetch=fetch, frames_by_id=F.FRAME_BY_ID, external_dir=tmp_path,
                       echo=lambda *a: None)
    assert not rep.failed and rep.streamed == [plan.shards[0].name]
    assert [c[0] for c in fetch.calls] == ["stream", "stream"]               # cut once, read whole the second time
    assert len((tmp_path / "d_very.tsv").read_text().splitlines()) == 3
