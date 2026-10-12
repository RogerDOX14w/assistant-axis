"""CLI tests for data_analysis/gap_generation/ipip_generator.py, end to end on the fixtures.

No network, no model, no API: the pages are the fixture pages and a synthetic workbook, the embedders are hash
embedders, the Anthropic client is a fake that answers the naming and overlap prompts.  Every ``--dry-run`` must
exit 0 and write nothing."""
from assistant_axis.gapgen.generators.ipip import GRANULARITIES  # noqa: E402
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.embed import HashEmbedder
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.ipip_fakes import fixture_pages, make_corpus
from data_analysis.gap_generation import ipip_generator as CLI


def answer(kw):
    sysp, user = system_text(kw), user_text(kw)
    if '"kind"' in sysp and '"statements"' in user:
        hinted = '"scales"' in user
        first = json.loads(user)["statements"][0]
        word = first.split()[1].strip(".").lower()
        return make_response(json.dumps({
            "reason": "They share a habit.", "label": f"{word}-minded" + ("-h" if hinted else ""),
            "gloss": f"This means a habit of {word}.", "antonym_label": None, "antonym_gloss": None,
            "kind": "state" if word == "worry" else "trait", "ambiguity_flag": False,
            "single_word_exists": False}), input_tokens=900, output_tokens=200)
    return make_response(json.dumps({"reason": "close", "similarity": 3}), input_tokens=900, output_tokens=60)


@pytest.fixture
def env(tmp_path, monkeypatch):
    ext = fixture_pages(tmp_path / "ext", all_21=True)
    data = make_corpus(tmp_path)
    ipip = tmp_path / "ipip"
    cdir = tmp_path / "candidates"
    monkeypatch.setattr(CLI, "_embedder", lambda arm: HashEmbedder(dim=24))
    client = FakeAsyncAnthropic(answer)
    monkeypatch.setattr(CLI, "_client", lambda: client)
    common = ["--data-dir", str(data), "--registry", str(cdir / "registry.jsonl"), "--candidates-dir", str(cdir),
              "--external", str(ext), "--ipip-dir", str(ipip), "--embedding-cache", str(tmp_path / "emb")]
    return tmp_path, common, ipip, cdir, client


def snapshot(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*")
                  if p.is_file())


def dry(root, common, argv):
    before = snapshot(root)
    assert CLI.main(common + argv + ["--dry-run"]) == 0
    assert snapshot(root) == before, f"{argv[0]} --dry-run wrote something"


def test_download_dry_run_writes_nothing(tmp_path, capsys):
    ext = tmp_path / "ext"
    assert CLI.main(["--external", str(ext), "--ipip-dir", str(tmp_path / "ipip"), "download", "--dry-run"]) == 0
    assert not ext.exists() and not (tmp_path / "ipip").exists()
    out = capsys.readouterr().out
    # QUESTIONS 52 option C: the key pages and the workbook are approved, so all 26 sources are in the dry run
    assert "https://ipip.ori.org/AlphabeticalItemList.htm" in out
    assert "TedoneItemAssignmentTable30APR21.xlsx" in out and "newHEXACO_PI_key.htm" in out
    assert "https://ipip.ori.org/index.htm" in out                                 # QUESTIONS 46, the licence
    assert CLI.main(["--external", str(ext), "--ipip-dir", str(tmp_path / "ipip"), "download", "--only",
                     "assignment_workbook", "--dry-run"]) == 0                     # approved since 2026-10-11


def test_pipeline_end_to_end(env, capsys):
    root, common, ipip, cdir, client = env
    # ingest (the fixture's HEX block is two constructs: the assertion fails, --skip-hex-check writes anyway)
    dry(root, common, ["ingest"])
    assert CLI.main(common + ["ingest"]) == 1 and not (ipip / "items.jsonl").exists()
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    assert len((ipip / "items.jsonl").read_text().splitlines()) == 12
    counts = json.loads((ipip / "ingest_counts.json").read_text())
    assert counts["hex_assertion"] == "failed" and counts["construct_labels"]
    assert counts["key_page_check"] == "passed" and counts["key_pages"]["n_pages_read"] == 21
    assert counts["key_comparison"]["compared"] is True
    assert all(s["key_source"] for line in (ipip / "items.jsonl").read_text().splitlines()
               for s in json.loads(line)["scales"])
    # cluster
    dry(root, common, ["cluster", "--no-hdbscan"])
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    for g in GRANULARITIES:
        rows = [json.loads(x) for x in (ipip / f"clusters_g{g}.jsonl").read_text().splitlines()]
        assert rows and all(r["consensus"] == "kept" for r in rows)              # identical arms: all kept
        assert [r["cluster_id"] for r in rows] == list(range(1, len(rows) + 1))
    summ = json.loads((ipip / "cluster_summary.json").read_text())
    assert "_provenance" in summ and set(summ["result"]["granularities"]) == {str(g) for g in GRANULARITIES}
    assert (ipip / "cluster_usage.json").exists()
    # name
    dry(root, common, ["name", "--granularity", "350", "--all", "--hinted"])
    assert not client.calls
    assert CLI.main(common + ["name", "--granularity", "350", "--all", "--hinted"]) == 0
    rows = [json.loads(x) for x in (ipip / "clusters_g350.jsonl").read_text().splitlines()]
    poles = [p for r in rows for p in r["poles"]]
    assert all(p["blind"]["label"].endswith("-minded") and p["hinted"]["label"].endswith("-h") for p in poles)
    assert all(p["blind"]["kind"] in ("trait", "state") for p in poles)
    assert all("nearest_other" in p for p in poles)                   # QUESTIONS 50 signal 1 needs no vectors
    assert all(p["labels_disagree"] is True for p in poles)
    assert json.loads((ipip / "naming_usage.json").read_text())["n_calls"] == 2 * len(poles)
    n_calls = len(client.calls)
    assert CLI.main(common + ["name", "--granularity", "350", "--all", "--hinted"]) == 0
    assert len(client.calls) == n_calls                                          # already named: nothing sent
    # granularity
    dry(root, common, ["granularity", "--granularities", "350"])
    assert CLI.main(common + ["granularity", "--granularities", "350"]) == 0
    ro = json.loads((ipip / "granularity_readout.json").read_text())["result"]["readouts"][0]
    assert ro["within"]["share_3_4"] == 1.0 and ro["label_form"] == "judge-display-v1"
    assert ro["nearest"]["n"] >= 1 and ro["nearest"]["share_3"] == 1.0          # signal 1 ran
    assert set(ro["nearest_by_band"]) == set(ro["bands"])
    assert (ipip / "granularity" / "g350" / "usage.json").exists() and (ipip / "granularity_readout.md").exists()
    md = (ipip / "granularity_readout.md").read_text()
    assert "## Signal 1: each pole against the nearest pole of another cluster" in md
    assert "## Signal 2: ~350 clusters" in md
    # submit
    dry(root, common, ["submit", "--granularity", "350", "--run-id", "p1", "--all-poles"])
    assert not cdir.exists()
    # the old spelling still works and means the same (QUESTIONS 48: there is no trait gate)
    assert CLI.main(common + ["submit", "--granularity", "350", "--run-id", "p1", "--all-trait-poles"]) == 0
    rdir = cdir / "runs" / "ipip" / "p1"
    cands = [json.loads(x) for x in (rdir / "candidates.jsonl").read_text().splitlines()]
    assert cands and all(c["score"] is None and c["source_ref"].startswith("ipip:g350:c") for c in cands)
    # every named pole is submitted, whatever the naming call guessed (QUESTIONS 48)
    args = json.loads((rdir / "run.json").read_text())["args"]
    assert args["counts"]["n_named"] == args["counts"]["n_submitted"] == len(cands)
    assert sum(args["counts"]["kinds"].values()) == len(cands) and args["gate"].startswith("none:")
    # the platform's M1 and M3 blocks, as their CLIs would write them
    reg = Registry(cdir / "registry.jsonl")
    keys = (rdir / "keys.txt").read_text().split()
    for k in keys:
        reg.merge_block(k, "filter", {"verdict": "trait", "outcome": "trait"})
        reg.merge_block(k, "novelty", {"decision": "new", "covered_by": None})
    # report
    dry(root, common, ["report", "--run-id", "p1", "--census-table", str(root / "no_census.jsonl")])
    capsys.readouterr()
    assert CLI.main(common + ["report", "--run-id", "p1", "--census-table", str(root / "no_census.jsonl")]) == 0
    ev = json.loads((rdir / "evaluation.json").read_text())
    assert "_provenance" in ev and ev["result"]["m1_m3"]["n_filtered"] == len(keys)
    assert ev["result"]["useful_per_dollar"]["n_new"] == len(keys)
    md = (rdir / "report.md").read_text()
    for section in ("## Items", "## Clusters", "## Granularity: decision (a)", "## Naming: decision (b)",
                    "## Submission, M1 and M3", "## Known analogues", "## Cost", "## Decisions for Roger", "## Files"):
        assert section in md, section
    # the granularity section reads QUESTIONS 50's signals, not the superseded share-at-3-4 criterion (review
    # 2026-10-12), and decision (a) names the granularities measured
    assert "| signal 1: share at 3 |" in md and "| signal 1: pairs read |" in md
    assert "Roger's criterion is the share at 3-4" not in md and "(a) granularity, ~350 (" in md
    sample = (rdir / "roger_sample.md").read_text()
    assert "| # | pole | blind label | hinted label | blind gloss | statements | M1 | M3 (covered by) |" in sample
    assert "| trait | new |" in sample


def test_name_render_prints_the_calls_as_sent(env, capsys):
    """The house rule: read the rendered prompt, not the template.  --render prints the system turn byte for byte
    and the user turns as they are sent, which is what the rubric files' Rendered sample sections hold."""
    from assistant_axis.gapgen.generators.ipip import naming as N
    root, common, ipip, cdir, client = env
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    capsys.readouterr()
    assert CLI.main(common + ["name", "--granularity", "350", "--all", "--hinted", "--render", "2",
                              "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert not client.calls
    assert N.system_prompt("blind") in out and N.system_prompt("hinted") in out
    assert "ipip_naming_blind version 1" in out and '{"statements": ["I ' in out
    assert '"scales": [{"scale": "' in out and '"direction": "' in out


def test_submit_refused_over_budget(env):
    root, common, ipip, cdir, client = env
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    assert CLI.main(common + ["name", "--granularity", "350", "--all"]) == 0
    with pytest.raises(SystemExit) as ei:
        CLI.main(common + ["submit", "--granularity", "350", "--run-id", "p2", "--all-poles",
                           "--budget-usd", "0.001"])
    assert ei.value.code == 2 and not (cdir / "runs").exists()


def test_ingest_without_the_workbook_commits_the_key_pages_alone(env):
    """QUESTIONS 52: source B is primary, so the workbook's absence is recorded, not fatal; --require-workbook
    refuses, naming the question."""
    root, common, ipip, cdir, client = env
    (root / "ext" / "TedoneItemAssignmentTable30APR21.xlsx").unlink()
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    counts = json.loads((ipip / "ingest_counts.json").read_text())
    assert counts["workbook"] is None and counts["key_comparison"]["compared"] is False
    assert set(counts["key_sources"]) == {"ipip_key_pages"}
    assert CLI.main(common + ["ingest", "--require-workbook"]) == 2


def test_the_key_page_check_refuses_a_short_scrape(env):
    """QUESTIONS 49's spirit on the key pages: a missing page is a clear error, never a silent pass."""
    root, common, ipip, cdir, client = env
    (root / "ext" / "newNEOKey.htm").unlink()
    assert CLI.main(common + ["ingest"]) == 1 and not (ipip / "items.jsonl").exists()
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    counts = json.loads((ipip / "ingest_counts.json").read_text())
    assert counts["key_page_check"] == "failed" and counts["key_pages"]["missing"] == ["newNEOKey.htm"]


def test_a_partial_cluster_run_keeps_the_other_granularities_summaries(env):
    """Review 2026-10-12: `cluster --targets 600` rewrote cluster_summary.json with the 600 summary alone, so
    `report` lost the 350 and 150 columns.  A run over some targets now keeps the others' summaries (same items,
    arms and seed)."""
    root, common, ipip, cdir, client = env
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    assert CLI.main(common + ["cluster", "--no-hdbscan", "--targets", "350"]) == 0
    res = json.loads((ipip / "cluster_summary.json").read_text())["result"]
    assert set(res["granularities"]) == {str(g) for g in GRANULARITIES}
    assert res["targets"] == sorted(GRANULARITIES, reverse=True) and res["targets_this_run"] == [350]


def test_granularity_stops_sending_and_exits_2_at_the_budget(env, monkeypatch, capsys):
    """Review 2026-10-12: a budget stop was printed and the command still returned 0, and the later granularities
    were still sent (one over-budget call each, at least)."""
    import types
    from assistant_axis.gapgen.generators.ipip import granularity as G
    root, common, ipip, cdir, client = env
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    seen = []

    async def fake_run(calls, corpus, **kw):
        seen.append(kw["out_dir"].name)
        return types.SimpleNamespace(budget_exceeded=True)
    monkeypatch.setattr(G, "run_readings", fake_run)
    assert CLI.main(common + ["granularity", "--granularities", "350", "150", "--signals", "within"]) == 2
    assert seen == ["g350"]                                     # nothing sent for ~150 after the stop
    assert "STOPPED at the budget" in capsys.readouterr().err


def test_a_hinted_pass_after_a_blind_one_asks_only_the_hinted_form(env):
    """Review 2026-10-12: a pole missing either form was asked both, so `name --hinted` after a blind-only `name`
    re-asked every blind name (on the recorded run: 362 re-asks, 189 of them answered with a different label,
    silently replacing the first)."""
    from assistant_axis.tests.fake_anthropic import user_text
    root, common, ipip, cdir, client = env
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) in (0, 3)
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    assert CLI.main(common + ["name", "--granularity", "350", "--all"]) == 0
    rows = [json.loads(x) for x in (ipip / "clusters_g350.jsonl").read_text().splitlines()]
    poles = [p for r in rows for p in r["poles"]]
    blind_before = [p["blind"] for p in poles]
    n0 = len(client.calls)
    assert n0 == len(poles)
    assert CLI.main(common + ["name", "--granularity", "350", "--all", "--hinted"]) == 0
    new = client.calls[n0:]
    assert len(new) == len(poles) and all('"scales"' in user_text(kw) for kw in new)     # the hinted form only
    rows = [json.loads(x) for x in (ipip / "clusters_g350.jsonl").read_text().splitlines()]
    assert [p["blind"] for r in rows for p in r["poles"]] == blind_before
    assert all(p.get("hinted") for r in rows for p in r["poles"])
    n1 = len(client.calls)
    assert CLI.main(common + ["name", "--granularity", "350", "--all", "--hinted", "--force"]) == 0
    assert len(client.calls) - n1 == 2 * len(poles)                                      # --force asks both again
