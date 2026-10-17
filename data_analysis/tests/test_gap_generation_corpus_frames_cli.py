"""The corpus-frames generator's CLI (``corpus_frames_generator.py``): every subcommand's dry run exits 0 and writes
nothing (and ``locate`` / ``stream`` / ``fetch-text`` dry runs make no request); ``stream`` and ``fetch-text`` without
``--approved-by`` exit non-zero before any request; the pipeline locate -> stream -> fetch-text -> extract-text ->
table -> evaluate -> submit (pilot) -> M1 and M3 (simulated) -> evaluate --pilot-run -> submit (wave) -> report runs
end to end on fakes (fixture shards, a fake Hub, fake lookups, a tmp registry).  No network, no OEWN, no API."""
import hashlib
import io
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.corpus_frames import books as B
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.corpus_frames_fakes import fake_lookups, fixture_fetcher, make_corpus
from data_analysis.gap_generation import corpus_frames_generator as CLI

APPROVAL = "Roger, 2026-10-14: open decision 1 (b), both tiers streamed (test)"


class FakeHub:
    def __init__(self, files):
        self.files, self.calls = files, []

    def stream(self, url):
        self.calls.append(("stream", url))
        return io.BytesIO(self.files[url.rsplit("/", 1)[-1]])

    def json(self, url):
        self.calls.append(("json", url))
        return {"siblings": [{"rfilename": "data/train-00000-of-00001.parquet"}]}


@pytest.fixture
def env(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    fetch = fixture_fetcher()
    monkeypatch.setattr(B, "N_SHARDS", dict(fetch.n_shards))
    pq.write_table(pa.table({"description": ["She is kind, shy and loyal.", "He is shy by nature.",
                                             "She is shy, kind and clever.", "A shy girl, loyal by nature."]}),
                   tmp_path / "cards.parquet")
    pippa = "\n".join(json.dumps({"bot_description": t}) for t in
                      ("She is kind and shy.", "He is generous to a fault.", "She is shy and kind.",
                       "Personality: shy, kind, generous", "He is kind, generous and shy."))
    hub = FakeHub({"pippa_deduped.jsonl": pippa.encode(),
                   "train-00000-of-00001.parquet": (tmp_path / "cards.parquet").read_bytes()})
    monkeypatch.setattr(CLI, "_fetcher", lambda: fetch)
    monkeypatch.setattr(CLI, "_text_fetcher", lambda: hub)
    monkeypatch.setattr(CLI, "_lookups", lambda: fake_lookups())
    monkeypatch.setattr(CLI, "_universe", lambda: ["good", "kind", "honest", "shy", "liar", "cheerful", "zebra"])
    monkeypatch.setattr(CLI, "_zipf", lambda: (lambda w: {"good": 6.5, "kind": 5.2, "honest": 4.6}.get(w, 3.0)))
    monkeypatch.setattr(CLI, "_review_rate", lambda: (146.0, "test"))
    monkeypatch.setattr(CLI, "_git_sha", lambda: "abc1234")
    root = tmp_path / "root"
    data = make_corpus(root, traits=("honest", "kind", "cheerful", "humble", "kind_to_animals"), queue=("clever",))
    regions = root / "regions.json"
    regions.write_text(json.dumps({"result": {"kind_to_animals": {"region": "moral_stance"},
                                              "humble": {"region": "moral_stance"}}}))
    common = ["--data-dir", str(data), "--registry", str(root / "cand" / "registry.jsonl"),
              "--candidates-dir", str(root / "cand"), "--out-dir", str(root / "out"),
              "--external-dir", str(root / "ext" / "books_ngrams"), "--text-dir", str(root / "ext" / "corpus_frames"),
              "--sources-manifest", str(root / "out" / "sources_manifest.json"), "--regions", str(regions)]
    return root, common, fetch, hub


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def run(common, *argv):
    return CLI.main(common + list(argv))


def test_dry_runs_write_nothing_and_the_gates_refuse_before_any_request(env, capsys):
    root, common, fetch, hub = env
    before = snapshot(root)
    assert run(common, "locate", "--dry-run") == 0
    assert fetch.calls == [] and snapshot(root) == before
    assert run(common, "fetch-text", "--dry-run") == 0 and hub.calls == []
    assert run(common, "fetch-text") == 2 and hub.calls == []               # no --approved-by
    assert run(common, "extract-text", "--dry-run") == 0
    assert run(common, "table", "--dry-run") == 2                            # nothing to build from yet
    assert snapshot(root) == before
    assert run(common, "locate") == 0
    assert (root / "out" / "shard_plan.json").exists()
    fetch.calls.clear()
    mid = snapshot(root)
    assert run(common, "stream") == 2 and fetch.calls == []                 # no --approved-by: refused, no request
    assert run(common, "stream", "--dry-run") == 0 and fetch.calls == []
    assert snapshot(root) == mid
    err = capsys.readouterr().err
    assert "--approved-by" in err


def pipeline(env):
    root, common, fetch, hub = env
    assert run(common, "locate") == 0
    assert run(common, "stream", "--approved-by", APPROVAL, "--parallel", "2") == 0
    assert run(common, "fetch-text", "--approved-by", "Roger, 2026-10-14: open decision 2 (test)") == 0
    assert run(common, "extract-text") == 0
    assert run(common, "table") == 0
    assert run(common, "evaluate") == 0
    return root, common


def test_pipeline_end_to_end(env, capsys):
    root, common = pipeline(env)
    out = root / "out"
    table = [json.loads(x) for x in (out / "frames_table.jsonl").read_text().splitlines()]
    stems = {r["stem"]: r for r in table}
    assert {"honest", "kind", "good", "shy", "liar", "pedantic", "cheerful"} <= set(stems)
    assert "old" not in stems                                               # the nominal frame's test
    assert stems["shy"]["sources"] == ["cards", "pippa"]                   # text frames only
    assert set(stems["honest"]["frames"]) >= {"d_very", "p_known_for_his"}
    assert stems["skeptical"]["us_spelling_from"] == "sceptical"
    man = json.loads((root / "ext" / "books_ngrams" / "DOWNLOAD_MANIFEST.json").read_text())
    assert man["approvals"] == [APPROVAL] and man["bytes_streamed"] == man["bytes_planned"]
    stats = json.loads((out / "frame_stats.json").read_text())["result"]
    by = {s["frame"]: s for s in stats["frames"]}
    assert by["d_very"]["lines_kept"] > 0 and by["cards.copular_list"]["documents"] == 4
    assert by["d_very"]["recovery"]["volumes"]["n"] == 5 and by["d_very"]["keep"] is True
    ev = json.loads((out / "evaluation.json").read_text())["result"]
    assert ev["table_sha256"] == hashlib.sha256((out / "frames_table.jsonl").read_bytes()).hexdigest()
    assert {"union_volumes", "union_lift", "baseline_wordfreq", "baseline_table_zipf"} <= set(ev["recovery"])
    assert ev["unfound_labels"]["by_region"]["moral_stance"] == ["humble", "kind to animals"]
    assert (out / "recovery_curves.png").exists() and (out / "readout.md").exists()
    md = (out / "readout.md").read_text()
    assert "Ordering chosen" in md and "glossary.md#rrf" in md
    assert "[humble](../data/traits/instructions/humble.json)" in md       # linked relative to the readout
    # the pilot
    mid = snapshot(root)
    assert run(common, "submit", "--run-id", "p1", "--top-per-frame", "3", "--dry-run") == 0
    assert snapshot(root) == mid
    assert run(common, "submit", "--run-id", "p1", "--top-per-frame", "3") == 0
    rdir = root / "cand" / "runs" / "corpus_frames" / "p1"
    assert json.loads((rdir / "usage.json").read_text())["total_cost_usd"] == 0.0
    sel = json.loads((rdir / "run.json").read_text())["args"]["selection_by_frame"]
    assert sel["d_very"][:1] == ["good"] and "n_incorrigible" in sel
    # the wave before any pilot measure is refused (no frames kept yet)
    assert run(common, "submit", "--run-id", "w0", "--kept-target", "2", "--dry-run") == 2
    # M1 and M3, simulated: every row a trait; liar and shy kept (shy: text frames only)
    reg = Registry(root / "cand" / "registry.jsonl")
    for key, row in sorted(reg.fold().items()):
        st = row["stem"]
        region = "moral_stance" if st in ("liar", "honest") else "social_interpersonal"
        reg.merge_block(key, "filter", {"verdict": "trait" if st != "letters" else "reject", "region": region,
                                        "tags": [], "gloss": f"the gloss of {st}"}, replace=True)
        if st != "letters":
            reg.merge_block(key, "novelty", {"decision": "new" if st in ("liar", "shy", "pedantic") else "covered",
                                             "listed": [{"stem": "honest", "cosine": 0.2 if st == "liar" else 0.4}]},
                            replace=True)
    assert run(common, "evaluate", "--pilot-run", "p1") == 0
    ev = json.loads((out / "evaluation.json").read_text())["result"]
    assert ev["pilot_run"] == "p1" and ev["frame_measures"]["n_incorrigible"]["yield"] == 1.0
    assert ev["frame_measures"]["n_incorrigible"]["unique_kept"] >= 1 and "n_incorrigible" in ev["frames_kept"]
    by = {s["frame"]: s for s in json.loads((out / "frame_stats.json").read_text())["result"]["frames"]}
    assert by["n_incorrigible"]["pilot"]["n"] == len(sel["n_incorrigible"])
    # the wave
    assert run(common, "submit", "--run-id", "w1", "--kept-target", "2", "--kept-share", "0.5", "--dry-run") == 0
    assert run(common, "submit", "--run-id", "w1", "--kept-target", "2", "--kept-share", "0.5") == 0
    w = json.loads((root / "cand" / "runs" / "corpus_frames" / "w1" / "run.json").read_text())["args"]
    # after the pilot only two rows are still net-new, so the cut (ceil(2 / 0.5) = 4) takes every row
    assert w["frames_kept"] == sorted(ev["frames_kept"]) and w["n_counted"] == 2 and w["n_rows"] == len(table)
    # the report
    mid = snapshot(root)
    assert run(common, "report", "--run-id", "p1", "--dry-run") == 0
    assert snapshot(root) == mid
    assert run(common, "report", "--run-id", "p1") == 0
    rep = (rdir / "report.md").read_text()
    assert "## 1. Already registered" in rep and "Net-new kept share" in rep
    assert "## The contributing frames of every kept row" in rep and "`n_incorrigible`" in rep
    first = (rdir / "roger_first_hour.md").read_text()
    # liar (nearest cosine 0.2) before shy (0.4); pedantic has no row here: without OEWN the platform adds no sibling
    assert first.index("| liar |") < first.index("| shy |") and "| pedantic |" not in first
    assert "](../../../../data/traits/instructions/honest.json)" in first      # the test corpus's trait file
    assert (rdir / "roger_sample.md").read_text().count("| T/N/D |") == 1


def test_stream_resume_and_a_second_stream_is_refused(env, capsys):
    root, common, fetch, hub = env
    assert run(common, "locate") == 0
    assert run(common, "stream", "--approved-by", APPROVAL) == 0
    fetch.calls.clear()
    with pytest.raises(SystemExit):
        run(common, "stream", "--approved-by", APPROVAL)
    assert run(common, "stream", "--approved-by", APPROVAL, "--resume") == 0
    assert [c for c in fetch.calls if c[0] == "stream"] == []


def test_a_tier_1_stream_from_an_all_tier_plan(env):
    root, common, fetch, hub = env
    assert run(common, "locate") == 0
    assert run(common, "--tier", "1", "stream", "--approved-by", APPROVAL) == 0
    man = json.loads((root / "ext" / "books_ngrams" / "DOWNLOAD_MANIFEST.json").read_text())
    frames = {f for r in man["shards"] for f in r["frames"]}
    assert "d_very" in frames and "d_utterly" not in frames


def test_the_acceptance_checks_pass_on_the_pipelines_outputs(env, monkeypatch):
    """The recorded-output checks, run on what the pipeline writes (so that they do not first meet their inputs on
    the live run)."""
    from assistant_axis.gapgen.generators import corpus_frames as G
    from assistant_axis.tests import test_gapgen_corpus_frames_acceptance as A
    root, common = pipeline(env)
    assert run(common, "submit", "--run-id", "p1", "--top-per-frame", "3") == 0
    assert run(common, "report", "--run-id", "p1") == 0
    out = root / "out"
    for name, f in (("SOURCES_MANIFEST_PATH", "sources_manifest.json"), ("SHARD_PLAN_PATH", "shard_plan.json"),
                    ("EVALUATION_PATH", "evaluation.json"), ("FRAME_STATS_PATH", "frame_stats.json"),
                    ("TABLE_PATH", "frames_table.jsonl")):
        monkeypatch.setattr(G, name, out / f)
    A.test_the_manifest_names_the_approval_and_its_bytes_agree_with_the_plan()
    A.test_the_text_corpora_record_their_licence_and_approval()
    A.test_the_evaluation_reports_what_the_plan_asks()
    A.test_frame_stats_cover_every_streamed_frame()
    A.test_the_tables_sha256_is_the_recorded_one()
    rdir = root / "cand" / "runs" / "corpus_frames" / "p1"
    A.test_generator_usage_is_zero(rdir)
    A.test_every_report_carries_the_headline_the_share_and_the_contributing_frames(rdir)
