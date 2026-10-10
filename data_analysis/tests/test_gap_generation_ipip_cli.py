"""CLI tests for data_analysis/gap_generation/ipip_generator.py, end to end on the fixtures.

No network, no model, no API: the pages are the fixture pages and a synthetic workbook, the embedders are hash
embedders, the Anthropic client is a fake that answers the naming and overlap prompts.  Every ``--dry-run`` must
exit 0 and write nothing."""
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
    if "persona trait" in sysp and '"statements"' in user:
        hinted = '"scales"' in user
        first = json.loads(user)["statements"][0]
        word = first.split()[1].strip(".").lower()
        return make_response(json.dumps({
            "reason": "They share a habit.", "label": f"{word}-minded" + ("-h" if hinted else ""),
            "gloss": f"This means a habit of {word}.", "antonym_label": None, "antonym_gloss": None,
            "is_trait": word != "worry", "ambiguity_flag": False, "single_word_exists": False}),
            input_tokens=900, output_tokens=200)
    return make_response(json.dumps({"reason": "close", "similarity": 3}), input_tokens=900, output_tokens=60)


@pytest.fixture
def env(tmp_path, monkeypatch):
    ext = fixture_pages(tmp_path / "ext")
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
    assert "https://ipip.ori.org/AlphabeticalItemList.htm" in out and "TedoneItemAssignmentTable" not in out
    assert CLI.main(["--external", str(ext), "--ipip-dir", str(tmp_path / "ipip"), "download", "--only",
                     "assignment_workbook", "--dry-run"]) == 2                     # refused without a named go


def test_pipeline_end_to_end(env, capsys):
    root, common, ipip, cdir, client = env
    # ingest (the fixture's HEX block is one construct: the assertion fails, --skip-hex-check writes anyway)
    dry(root, common, ["ingest"])
    assert CLI.main(common + ["ingest"]) == 1 and not (ipip / "items.jsonl").exists()
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) == 0
    assert len((ipip / "items.jsonl").read_text().splitlines()) == 12
    counts = json.loads((ipip / "ingest_counts.json").read_text())
    assert counts["hex_assertion"] == "failed" and counts["construct_labels"]
    # cluster
    dry(root, common, ["cluster", "--no-hdbscan"])
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    for g in (350, 150):
        rows = [json.loads(x) for x in (ipip / f"clusters_g{g}.jsonl").read_text().splitlines()]
        assert rows and all(r["consensus"] == "kept" for r in rows)              # identical arms: all kept
        assert [r["cluster_id"] for r in rows] == list(range(1, len(rows) + 1))
    summ = json.loads((ipip / "cluster_summary.json").read_text())
    assert "_provenance" in summ and set(summ["result"]["granularities"]) == {"350", "150"}
    assert (ipip / "cluster_usage.json").exists()
    # name
    dry(root, common, ["name", "--granularity", "350", "--all", "--hinted"])
    assert not client.calls
    assert CLI.main(common + ["name", "--granularity", "350", "--all", "--hinted"]) == 0
    rows = [json.loads(x) for x in (ipip / "clusters_g350.jsonl").read_text().splitlines()]
    poles = [p for r in rows for p in r["poles"]]
    assert all(p["blind"]["label"].endswith("-minded") and p["hinted"]["label"].endswith("-h") for p in poles)
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
    assert (ipip / "granularity" / "g350" / "usage.json").exists() and (ipip / "granularity_readout.md").exists()
    # submit
    dry(root, common, ["submit", "--granularity", "350", "--run-id", "p1", "--all-trait-poles"])
    assert not cdir.exists()
    assert CLI.main(common + ["submit", "--granularity", "350", "--run-id", "p1", "--all-trait-poles"]) == 0
    rdir = cdir / "runs" / "ipip" / "p1"
    cands = [json.loads(x) for x in (rdir / "candidates.jsonl").read_text().splitlines()]
    assert cands and all(c["score"] is None and c["source_ref"].startswith("ipip:g350:c") for c in cands)
    assert not any(c["surface"].startswith("worry") for c in cands)              # the non-trait pole is held back
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
    for section in ("## Items", "## Clusters", "## Granularity: decision (a)", "## Naming: decisions (b) and (c)",
                    "## Submission, M1 and M3", "## Known analogues", "## Cost", "## Decisions for Roger", "## Files"):
        assert section in md, section
    sample = (rdir / "roger_sample.md").read_text()
    assert "| # | pole | blind label | hinted label | blind gloss | statements | M1 | M3 (covered by) |" in sample
    assert "| trait | new |" in sample


def test_submit_refused_over_budget(env):
    root, common, ipip, cdir, client = env
    assert CLI.main(common + ["ingest", "--skip-hex-check"]) == 0
    assert CLI.main(common + ["cluster", "--no-hdbscan"]) == 0
    assert CLI.main(common + ["name", "--granularity", "350", "--all"]) == 0
    with pytest.raises(SystemExit) as ei:
        CLI.main(common + ["submit", "--granularity", "350", "--run-id", "p2", "--all-trait-poles",
                           "--budget-usd", "0.001"])
    assert ei.value.code == 2 and not (cdir / "runs").exists()


def test_ingest_without_the_workbook_is_refused(env):
    root, common, ipip, cdir, client = env
    (root / "ext" / "TedoneItemAssignmentTable30APR21.xlsx").unlink()
    assert CLI.main(common + ["ingest"]) == 2 and not ipip.exists()
