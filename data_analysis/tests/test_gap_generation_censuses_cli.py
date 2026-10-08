"""CLI tests for data_analysis/gap_generation/census_generator.py.

No network, no model: downloads are dry runs, and the ingest reads the fixture files with the
fake lookups of ``assistant_axis/tests/censuses_fakes.py``."""
import json
import shutil
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.censuses import ingest as I
from assistant_axis.gapgen.generators.censuses.sources import SOURCES
from assistant_axis.tests.censuses_fakes import FIXTURES, fake_lookups, make_corpus
from data_analysis.gap_generation import census_generator as CG


@pytest.fixture
def env(tmp_path, monkeypatch):
    wl = tmp_path / "wordlists"
    for col in ("I", "II", "III", "IV"):
        dest = wl / SOURCES[f"allport_{col}"].dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES / f"allport_{col}.txt", dest)
    shutil.copy(FIXTURES / "allport_merged.txt", wl / SOURCES["allport_merged"].dest)
    (wl / SOURCES["tda_properties"].dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "tda_properties_small.csv", wl / SOURCES["tda_properties"].dest)
    data = make_corpus(tmp_path)
    monkeypatch.setattr(I, "default_lookups", lambda: fake_lookups())
    cdir = tmp_path / "candidates"
    manifest = tmp_path / "censuses" / "sources_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps([{"key": "tda_properties", "sha256": "ab"}]))
    common = ["--data-dir", str(data), "--registry", str(cdir / "registry.jsonl"), "--candidates-dir", str(cdir),
              "--table", str(tmp_path / "censuses" / "census_table.jsonl"),
              "--counts", str(tmp_path / "censuses" / "ingest_counts.json"), "--wordlists", str(wl),
              "--sources-manifest", str(manifest)]
    return tmp_path, common, cdir


def snapshot(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_size) for p in root.rglob("*") if p.is_file())


def test_download_dry_run(tmp_path, capsys):
    wl = tmp_path / "wl"
    rc = CG.main(["--wordlists", str(wl), "--sources-manifest", str(tmp_path / "m.json"), "download", "--dry-run"])
    assert rc == 0 and not wl.exists() and not (tmp_path / "m.json").exists()
    out = capsys.readouterr().out
    assert "https://osf.io/download/fdg4j/" in out and "format=original" in out


def test_ingest_dry_run_then_real(env, capsys):
    root, common, cdir = env
    before = snapshot(root)
    assert CG.main(common + ["ingest", "--dry-run"]) == 0
    assert snapshot(root) == before
    out = capsys.readouterr().out
    assert "per_stage" in out and "ceiling" in out
    assert CG.main(common + ["ingest"]) == 0
    rows = I.load_census_table(root / "censuses" / "census_table.jsonl")
    assert len(rows) == 17
    counts = json.loads((root / "censuses" / "ingest_counts.json").read_text())
    assert counts["ceiling"]["n_corpus"] == 4 and counts["n_tda"] == 5
    assert counts["repaired_list"][0]["repaired"] == "accommodating" and "repair_suggestions_list" in counts
    assert counts["malformed_list"][0]["raw"] == "F.F.V"
    # rerun: identical table, no backup
    assert CG.main(common + ["ingest"]) == 0
    assert not list((root / "censuses").glob("census_table.jsonl.bak.*"))


def test_submit_dry_run_and_real_and_report(env, capsys):
    root, common, cdir = env
    assert CG.main(common + ["ingest"]) == 0
    before = snapshot(root)
    assert CG.main(common + ["submit", "--stage", "tda", "--run-id", "p1", "--every-nth", "2", "--dry-run"]) == 0
    assert snapshot(root) == before and not cdir.exists()
    out = capsys.readouterr().out
    assert "downstream estimate" in out and "DRY-RUN" in out and "--run censuses/p1" in out
    assert CG.main(common + ["submit", "--stage", "tda", "--run-id", "p1", "--every-nth", "2"]) == 0
    rdir = cdir / "runs" / "censuses" / "p1"
    cands = [json.loads(x) for x in (rdir / "candidates.jsonl").read_text().splitlines()]
    assert [c["surface"] for c in cands] == ["kind", "abandoned", "obscurish"]
    run = json.loads((rdir / "run.json").read_text())
    assert run["args"]["sources"] == [{"key": "tda_properties", "sha256": "ab"}] and run["args"]["table_sha256"]
    before = snapshot(root)
    assert CG.main(common + ["report", "--run-id", "p1", "--dry-run"]) == 0
    assert snapshot(root) == before
    md = capsys.readouterr().out
    assert "## Counts" in md and "| step | count |" in md
    assert CG.main(common + ["report", "--run-id", "p1"]) == 0
    env_json = json.loads((rdir / "evaluation.json").read_text())
    assert "_provenance" in env_json and env_json["result"]["submitted"]["n_candidates"] == 3
    readout = (rdir / "readout.md").read_text()
    for section in ("## Counts", "## String ceiling", "## Known labels in this run", "## Filter (M1)", "## Files"):
        assert section in readout


def test_submit_refused_over_budget(env):
    root, common, cdir = env
    assert CG.main(common + ["ingest"]) == 0
    with pytest.raises(SystemExit) as ei:
        CG.main(common + ["submit", "--stage", "tda", "--run-id", "p2", "--budget-usd", "0.01"])
    assert ei.value.code == 2 and not cdir.exists()
