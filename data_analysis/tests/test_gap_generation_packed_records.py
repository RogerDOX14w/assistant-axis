"""Packed record files (``assistant_axis.gapgen.records``) at the real call sites: the review graph's resume and its
readers, M3's resume, the split filter's resume (whose end rewrites the log whole), a report reader, and the
``pack_records.py`` CLI.  Each packs a run's records between two sessions and checks the second session behaves as it
does on plain files.  No API call: the fake clients of the CLI tests these reuse."""
import gzip
import hashlib
import json

import pytest

from assistant_axis.gapgen import records as RF
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.review_app import decisions as D
from assistant_axis.tests.fake_anthropic import user_text
from assistant_axis.tests.test_gapgen_split_opinions import cli  # noqa: F401 - the split filter CLI's fixture
from data_analysis.gap_generation import pack_records
from data_analysis.tests import test_gap_generation_novelty_cli as NOV
from data_analysis.tests import test_gap_generation_review_graph_cli as REV


def _packed(path):
    rep = RF.pack(path)
    assert rep.action == "packed", rep
    assert not path.exists() and RF.gz_path(path).exists()


# --------------------------------------------------------------------------- the review graph (R1)

@pytest.fixture
def rev(tmp_path, monkeypatch):
    return REV.make_env(tmp_path, monkeypatch)


def test_review_graph_resume_reads_a_packed_log_and_graph(rev, capsys):
    good = rev["holder"]["responder"]

    def flaky(kw):
        if json.loads(user_text(kw)).get("target", {}).get("label") == "chain b":
            return RuntimeError("network down")
        return good(kw)
    rev["holder"]["responder"] = flaky
    assert REV.build(rev) == 0
    d = REV.out(rev)
    n_before = len(RF.read_jsonl(d / "responses.jsonl"))
    _packed(d / "responses.jsonl")
    _packed(d / "graph.json")
    rev["holder"]["responder"] = good
    assert REV.build(rev, "--resume") == 0
    sent = [json.loads(user_text(kw)) for kw in REV.calls(rev)]
    # as on plain files (test_a_stalled_run_then_resume_sends_only_the_unanswered): only the unanswered are sent
    assert all("target" in x for x in sent)
    assert {(x["target"]["label"], x["other"]["label"]) for x in sent} == \
        {("chain b", "chain c"), ("chain b", "chain a"), ("chain c", "chain b")}
    # the new answers went to a fresh plain tail; the log reads .gz then plain
    assert RF.gz_path(d / "responses.jsonl").exists() and (d / "responses.jsonl").exists()
    assert len(RF.read_jsonl(d / "responses.jsonl")) == n_before + len(sent)
    # the graph was rewritten plain: it is the current one, the stale .gz is ignored
    g = RG.Graph.from_json(RF.read_json(d / "graph.json"))
    assert g.complete and len(g.cliques) == 4
    stale = RG.Graph.from_json(json.loads(gzip.decompress(RF.gz_path(d / "graph.json").read_bytes())))
    assert not stale.complete
    # a second pack appends the tail as a new member and replaces the graph's .gz
    _packed(d / "responses.jsonl")
    _packed(d / "graph.json")
    assert len(RF.read_jsonl(d / "responses.jsonl")) == n_before + len(sent)
    assert RG.Graph.from_json(RF.read_json(d / "graph.json")).complete


def test_review_graph_readers_on_a_packed_graph(rev, capsys):
    assert REV.build(rev) == 0
    d = REV.out(rev)
    raw = (d / "graph.json").read_bytes()
    recs = REV.cli.read_records(d / "responses.jsonl", steps=("overlap",))
    _packed(d / "graph.json")
    _packed(d / "responses.jsonl")
    assert REV.cli.read_records(d / "responses.jsonl", steps=("overlap",)) == recs and recs
    capsys.readouterr()
    assert REV.cli.main(["groups", "--batch-id", "rv1", "--out-root", str(rev["cand_dir"])]) == 0
    assert "11 candidates, 4 merged groups" in capsys.readouterr().out
    # the review app's log opens on the packed graph, with the same sha256 as the plain file had
    log = D.DecisionLog.open(d, by="roger", data_dir=rev["data"])
    assert log.graph_sha256 == hashlib.sha256(raw).hexdigest()
    # the calibration of a later build reads the packed build's graph and records
    shares, tokens, unsure, info = REV.cli.calibration(["rv1"], rev["cand_dir"], proposed_cut_off=3)
    assert shares is not None and "rv1" in shares.source


# --------------------------------------------------------------------------- M3

@pytest.fixture
def nov(tmp_path, monkeypatch):
    return NOV.make_env(tmp_path, monkeypatch)


def test_m3_resume_reads_packed_responses_and_results(nov):
    good = nov["holder"]["responder"]

    def flaky(kw):
        if json.loads(user_text(kw)).get("target", {}).get("label") == "deltaish":
            return RuntimeError("network down")
        return good(kw)
    nov["holder"]["responder"] = flaky
    assert NOV.score(nov) == 0
    d = NOV.out(nov)
    n_before = len(RF.read_jsonl(d / "responses.jsonl"))
    _packed(d / "responses.jsonl")
    _packed(d / "results.jsonl")
    nov["holder"]["responder"] = good
    assert NOV.score(nov, "--resume") == 0
    calls = nov["holder"]["client"].calls
    assert calls and all(json.loads(user_text(k)).get("target", {}).get("label") == "deltaish" for k in calls)
    summary = json.loads((d / "summary.json").read_text())["result"]
    # the earlier session's decided rows came from the packed results.jsonl (as on plain files)
    assert summary["n_decided"] == 5 and summary["n_stalled"] == 0
    res = RF.read_jsonl(d / "results.jsonl")
    assert (d / "results.jsonl").exists() and len(res) == 5
    assert len(RF.read_jsonl(d / "responses.jsonl")) == n_before + len(calls)
    # a report reader: decisions.md from the packed results
    _packed(d / "results.jsonl")
    (d / "decisions.md").unlink()
    assert NOV.cli.main(["decisions", "--batch-id", "m3t", "--out-root", str(nov["cand_dir"]),
                         "--data-dir", str(nov["data"])]) == 0
    assert "| deltaish | new |" in (d / "decisions.md").read_text()


# --------------------------------------------------------------------------- the split filter (M1)

def _filter_session_pair(h, *, pack: bool) -> dict:
    from assistant_axis.tests.test_gapgen_split_opinions import SONNET55, _args
    from data_analysis.gap_generation import traithood_filter
    h["kinds"] = {SONNET55: {w: "state" for w in h["labels"]}}
    assert traithood_filter.main(_args(h, "--transport", "live", "--stop-on-disagreement")) == 3
    d = h["out"] / "filter" / "p"
    first = RF.read_jsonl(d / "responses.jsonl")
    if pack:
        _packed(d / "responses.jsonl")
        _packed(d / "results.jsonl")
    assert traithood_filter.main(_args(h, "--transport", "live", "--resume", "--stop-on-disagreement",
                                       "--accept-disagreement")) == 0
    return {"dir": d, "first": first, "sent": len(h["live"].calls),
            "responses": RF.read_jsonl(d / "responses.jsonl"), "results": RF.read_jsonl(d / "results.jsonl")}


def test_split_filter_resume_on_a_packed_log_matches_the_plain_one(cli, tmp_path):
    plain = _filter_session_pair(cli, pack=False)
    cli["out"] = tmp_path / "cand_packed"
    cli["out"].mkdir()
    packed = _filter_session_pair(cli, pack=True)
    assert packed["sent"] == plain["sent"]                       # the packed answers were replayed, not sent
    assert len(packed["responses"]) == len(plain["responses"]) > len(packed["first"])
    assert [r["key"] for r in packed["results"]] == [r["key"] for r in plain["results"]]
    assert {r["stage"] for r in packed["results"]} == {"classified"}
    # the end of the run rewrote the whole log plain, the earlier records first: the .gz is gone, nothing doubled
    d = packed["dir"]
    assert not RF.gz_path(d / "responses.jsonl").exists() and (d / "responses.jsonl").exists()
    assert [r.get("text") for r in packed["responses"][:len(packed["first"])]] == \
        [r.get("text") for r in packed["first"]]


# --------------------------------------------------------------------------- the CLI

def test_pack_records_cli(tmp_path, capsys):
    root = tmp_path / "candidates"
    (root / "review" / "b").mkdir(parents=True)
    (root / "novelty" / "n").mkdir(parents=True)
    big = "".join(json.dumps({"n": i, "text": "the same words again and again"}) + "\n" for i in range(40000))
    log = root / "review" / "b" / "responses.jsonl"
    log.write_text(big, encoding="utf-8")
    res = root / "novelty" / "n" / "results.jsonl"
    res.write_text(big, encoding="utf-8")
    other = root / "registry.jsonl"
    other.write_text(big, encoding="utf-8")
    small = root / "novelty" / "n" / "graph.json"
    small.write_text("{}", encoding="utf-8")
    min_mb = str(len(big) / (1 << 20) / 2)
    assert pack_records.main(["--root", str(root), "--min-mb", min_mb, "--dry-run"]) == 0
    o = capsys.readouterr().out
    assert "would pack" in o and "responses.jsonl  log" in o and "results.jsonl  snapshot" in o
    assert "skip" in o and "registry.jsonl" in o and "n/graph.json" not in o          # under --min-mb: not listed
    assert log.exists() and res.exists() and not RF.gz_path(log).exists()            # the dry run changed nothing
    assert pack_records.main(["--root", str(root), "--min-mb", min_mb]) == 0
    o = capsys.readouterr().out
    assert "2 packed" in o and "1 skipped" in o
    assert not log.exists() and not res.exists() and other.exists()
    assert RF.read_text(log) == big and RF.read_text(res) == big
    # --path: a record file of any size; refused for a name it does not know
    assert pack_records.main(["--path", str(small)]) == 0
    assert not small.exists() and RF.read_json(small) == {}
    assert pack_records.main(["--path", str(other)]) == 2
    assert "REFUSED" in capsys.readouterr().err and other.exists()
    # a log with a plain copy of its .gz beside it (the 2026-10-14 layout) is refused, exit 1 in a scan
    log.write_text(big, encoding="utf-8")
    assert pack_records.main(["--root", str(root), "--min-mb", min_mb]) == 1
    assert "starts with the whole .gz content" in capsys.readouterr().err and log.exists()
