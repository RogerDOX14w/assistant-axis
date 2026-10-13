"""Alignment sweep: fetch (fake fetcher) and chunk (fixture texts).  coding_plan_08_alignment_sweep.md § 8,
``chunk``; tasks 2 and 3.  No network."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.alignment_sweep import chunk as CH
from assistant_axis.gapgen.generators.alignment_sweep import fetch as F
from assistant_axis.gapgen.generators.alignment_sweep import sources as SRC
from assistant_axis.tests.alignment_sweep_fakes import (CONSTITUTION_HTML, KRAKOVNA_HEADER, KRAKOVNA_TSV_EXPORT,
                                                       SPEC_MD, TABLE_MD, fake_fetcher)

# --------------------------------------------------------------------------- chunk: headings


def test_heading_split_six_headings_six_chunks_with_stable_ids():
    chunks = CH.chunk_source("model_spec", SPEC_MD, version="2026-08-18")
    # "# Seek the truth" has no body of its own: its title is in its children's paths, not a chunk
    assert [c.chunk_id for c in chunks] == [
        "model_spec:2026-08-18:overview", "model_spec:2026-08-18:follow_instructions",
        "model_spec:2026-08-18:scope_of_autonomy", "model_spec:2026-08-18:do_not_lie",
        "model_spec:2026-08-18:express_uncertainty", "model_spec:2026-08-18:avoid-flattery"]
    again = CH.chunk_source("model_spec", SPEC_MD, version="2026-08-18")
    assert [c.as_dict() for c in again] == [c.as_dict() for c in chunks]


def test_heading_path_and_text():
    chunks = {c.chunk_id.rsplit(":", 1)[1]: c for c in CH.chunk_source("model_spec", SPEC_MD, version="v")}
    eu = chunks["express_uncertainty"]
    assert eu.heading == "Seek the truth > Do not lie > Express uncertainty"
    assert eu.text.startswith("### Express uncertainty") and "Say how sure you are." in eu.text
    assert "{#" not in eu.text and "authority=" not in eu.text           # attributes stripped from the heading
    assert eu.source == "model_spec" and eu.n_tokens_est > 0


def test_hash_lines_inside_code_fences_are_not_headings():
    chunks = CH.chunk_source("model_spec", SPEC_MD, version="v")
    fi = next(c for c in chunks if c.chunk_id.endswith(":follow_instructions"))
    assert "# this is a comment inside code" in fi.text
    assert not any("this-is-a-comment" in c.chunk_id for c in chunks)


def test_nested_fences_close_only_on_their_own_marker():
    """The Model Spec's examples are ``~~~xml`` blocks holding triple-backtick code blocks whose comments start with
    '#' (``# functions``, ``# [...] imports``): an inner fence must not close the outer one (CommonMark: a fence
    closes on the same character, at least as long, with no info string)."""
    md = ("# Formatting {#formatting}\n\nUse plain text.\n\n~~~xml\n<developer>\nA tool.\n\n```typescript\n"
          "# functions\nnamespace functions {}\n```\n\n</developer>\n<assistant>\n```python\n# [...] imports\n\n"
          "class X: pass\n```\n</assistant>\n~~~\n\nAfter the example.\n\n# Next {#next}\n\nMore.\n")
    chunks = CH.chunk_source("model_spec", md, version="v")
    assert [c.chunk_id for c in chunks] == ["model_spec:v:formatting", "model_spec:v:next"]
    assert "# functions" in chunks[0].text and "After the example." in chunks[0].text
    # the blank lines inside the example are not paragraph breaks: a split never cuts into a fence
    long = md.replace("Use plain text.", "Use plain text. " + "word " * 400)
    parts = CH.chunk_source("model_spec", long, version="v", max_tokens=150)
    for c in parts:
        assert c.text.count("~~~") % 2 == 0, c.chunk_id


def test_long_section_is_split_at_paragraphs_into_parts():
    body = "\n\n".join(f"Paragraph {i}. " + "word " * 120 for i in range(10))
    md = f"# Big {{#big}}\n\n{body}\n\n# Small {{#small}}\n\nShort.\n"
    chunks = CH.chunk_source("model_spec", md, version="v", max_tokens=400)
    big = [c for c in chunks if ":big" in c.chunk_id]
    assert len(big) > 1 and [c.chunk_id for c in big][:2] == ["model_spec:v:big:p1", "model_spec:v:big:p2"]
    assert all(c.n_tokens_est <= 400 or c.text.count("\n\n") == 0 for c in big)
    assert all(c.text.startswith("# Big") for c in big)                   # every part carries its heading
    joined = " ".join(c.text for c in big)
    assert all(f"Paragraph {i}." in joined for i in range(10))
    assert [c.chunk_id for c in chunks if ":small" in c.chunk_id] == ["model_spec:v:small"]


def test_duplicate_slugs_get_a_suffix():
    md = "# A\n\nx\n\n## Notes\n\none\n\n# B\n\ny\n\n## Notes\n\ntwo\n"
    ids = [c.chunk_id for c in CH.chunk_source("model_spec", md, version="v")]
    assert ids == ["model_spec:v:a", "model_spec:v:notes", "model_spec:v:b", "model_spec:v:notes-2"]


# --------------------------------------------------------------------------- chunk: HTML


def test_html_to_markdown_keeps_main_headings_and_paragraphs_only():
    md = CH.html_to_markdown(CONSTITUTION_HTML)
    assert md.startswith("# The Charter")
    assert "## Overview" in md and "### Core values" in md and "- Be honest." in md
    assert "The model should be broadly safe and broadly ethical." in md
    for gone in ("Site menu", "Footer text", "var x", "color: red", "Home"):
        assert gone not in md, gone
    assert "We’re releasing" in md                                  # entities decoded


def test_constitution_drops_preface_and_acknowledgements():
    con = SRC.SOURCES["constitution"]
    chunks = CH.chunk_source("constitution", CONSTITUTION_HTML, version="2026-10-10")
    ids = [c.chunk_id for c in chunks]
    assert ids == ["constitution:2026-10-10:overview", "constitution:2026-10-10:core-values",
                   "constitution:2026-10-10:safe-behaviors"]
    assert con.drop_before == "Overview"
    text = " ".join(c.text for c in chunks)
    assert "preface" not in text and "Summary text" not in text and "Thanks" not in text and "Names." not in text
    sb = chunks[-1]
    assert sb.heading == "Being safe > Safe behaviors" and "Do not acquire resources" in sb.text


# --------------------------------------------------------------------------- chunk: rows


def test_row_split_on_a_fixture_table():
    chunks = CH.chunk_rows("krakovna", TABLE_MD, version="2026-10-10", rows_per_chunk=2)
    assert [c.chunk_id for c in chunks] == ["krakovna:2026-10-10:rows-0001-0002", "krakovna:2026-10-10:rows-0003-0004",
                                            "krakovna:2026-10-10:rows-0005-0005"]
    for c in chunks:
        assert c.text.splitlines()[0] == "| Title | Intended goal | Behaviour |"   # header repeated
    assert "Coding" in chunks[-1].text and chunks[0].heading == "rows 1-2"
    tsv = "Title\tGoal\nA\tx\nB\ty\nC\tz\n"
    t = CH.chunk_rows("krakovna", tsv, version="v", rows_per_chunk=2)
    assert len(t) == 2 and t[0].text.splitlines()[0] == "Title\tGoal"


# --------------------------------------------------------------------------- chunk: files


def test_rerun_writes_byte_identical_chunks(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    (ext / "model_spec.md").write_text(SPEC_MD, encoding="utf-8")
    (ext / "constitution.html").write_text(CONSTITUTION_HTML, encoding="utf-8")
    manifest = [{"key": "model_spec", "file": str(ext / "model_spec.md"), "version_label": "2026-08-18"},
                {"key": "constitution", "file": str(ext / "constitution.html"), "version_label": "2026-10-10"}]
    out = ext / "chunks.jsonl"
    chunks = CH.build_all(manifest)
    CH.write_chunks(chunks, out)
    first = out.read_bytes()
    CH.write_chunks(CH.build_all(manifest), out)
    assert out.read_bytes() == first
    back = CH.load_chunks(out)
    assert [c.chunk_id for c in back] == [c.chunk_id for c in chunks] and len(back) == 9
    counts = CH.counts(back)
    assert counts["model_spec"]["n_chunks"] == 6 and counts["constitution"]["n_chunks"] == 3
    assert counts["_total"]["n_chunks"] == 9 and counts["_total"]["n_tokens_est"] > 0


# --------------------------------------------------------------------------- fetch


MS = SRC.SOURCES["model_spec"]
CON = SRC.SOURCES["constitution"]
LICENSE_TXT = b"Creative Commons Legal Code\n\nCC0 1.0 Universal\n\n    Statement of Purpose\n"


def pages():
    return {MS.url: SPEC_MD.encode(), MS.license_file_url: LICENSE_TXT, CON.url: CONSTITUTION_HTML.encode()}


def test_fetch_writes_files_and_both_manifests(tmp_path):
    calls = []
    sm = tmp_path / "tracked" / "sources_manifest.json"
    man = F.fetch_all(fetcher=fake_fetcher(pages(), calls), dest_root=tmp_path / "ext", sources_manifest_path=sm,
                      now="2026-10-10T12:00:00+00:00", git_sha="abc1234")
    assert man.fetched == ["model_spec", "constitution"] and man.skipped == []
    ms = next(e for e in man.entries if e["key"] == "model_spec")
    con = next(e for e in man.entries if e["key"] == "constitution")
    assert (tmp_path / "ext" / "model_spec.md").read_bytes() == SPEC_MD.encode()
    assert ms["version_label"] == "2026-08-18" and ms["version_pin"].startswith("7f1cf79")
    assert ms["license_line_found"] == "Creative Commons Legal Code / CC0 1.0 Universal"
    assert ms["license"] == "CC0 1.0 Universal" and ms["sha256"] and ms["size_bytes"] == len(SPEC_MD.encode())
    assert con["version_label"] == "2026-10-10" and con["version_pin"].startswith("captured 2026-10-10, sha256 ")
    assert "CC0 1.0 Deed" in con["license_line_found"] and con["fetched_at"] == "2026-10-10T12:00:00+00:00"
    assert json.loads((tmp_path / "ext" / "FETCH_MANIFEST.json").read_text()) == man.entries
    assert json.loads(sm.read_text()) == man.entries
    # a second run with the files in place fetches nothing
    calls.clear()
    man2 = F.fetch_all(fetcher=fake_fetcher(pages(), calls), dest_root=tmp_path / "ext", sources_manifest_path=sm,
                       now="2026-10-11T12:00:00+00:00")
    assert calls == [] and man2.skipped == ["model_spec", "constitution"] and man2.entries == man.entries
    # --force fetches again
    man3 = F.fetch_all(fetcher=fake_fetcher(pages()), dest_root=tmp_path / "ext", sources_manifest_path=sm,
                       force=True, now="2026-10-11T12:00:00+00:00")
    assert man3.fetched == ["model_spec", "constitution"]


def test_fetch_dry_run_writes_nothing(tmp_path):
    man = F.fetch_all(fetcher=fake_fetcher({}), dest_root=tmp_path / "ext",
                      sources_manifest_path=tmp_path / "m.json", dry_run=True)
    assert not (tmp_path / "ext").exists() and not (tmp_path / "m.json").exists()
    assert any(MS.url in line for line in man.dry_run_lines) and any("CC0" in line for line in man.dry_run_lines)


def test_fetch_refuses_a_source_that_is_never_stored(tmp_path):
    with pytest.raises(ValueError, match="never stored"):
        F.fetch_all(only=["krakovna"], fetcher=fake_fetcher({}), dest_root=tmp_path / "ext",
                    sources_manifest_path=tmp_path / "m.json")
    assert not (tmp_path / "ext").exists()


KRA_SHEET = "https://docs.google.com/spreadsheets/d/e/2PACX-abc/pubhtml"
KRA_TSV = "https://docs.google.com/spreadsheets/d/e/2PACX-abc/pub?output=tsv"
KRA_LANDING = f'<html><body><p>See <a href="{KRA_SHEET}">the master list</a>.</p></body></html>'.encode()


def test_transient_fetch_of_krakovna_reads_the_tsv_export_and_writes_nothing(tmp_path, monkeypatch):
    """CHANGED EXPECTATION (2026-10-13): this test fed a hand-made ``<table>`` as the ``pubhtml`` page and passed,
    while the real page is drawn by script and holds no table, so the live sheet gave 0 chunks.  The sheet is now read
    through its TSV export; the fixture is that export's form (banner, header, dividers)."""
    monkeypatch.chdir(tmp_path)
    kra = SRC.SOURCES["krakovna"]
    calls: list = []
    rec: dict = {}
    text = F.fetch_transient("krakovna", fetcher=fake_fetcher({kra.url: KRA_LANDING,
                                                               KRA_TSV: KRAKOVNA_TSV_EXPORT.encode()}, calls),
                             record=rec, now="2026-10-13T09:00:00+00:00")
    assert calls == [kra.url, KRA_TSV]                       # never the pubhtml page
    assert text == KRAKOVNA_TSV_EXPORT                       # as fetched: source_markdown drops the banner
    assert list(tmp_path.iterdir()) == []
    # the record says what was read, as the manifest's entries do, and holds no text of the sheet
    assert rec["url"] == KRA_TSV and rec["page_url"] == kra.url and rec["sheet_url"] == KRA_SHEET
    assert rec["file"] is None and rec["stored"] is False and rec["fmt"] == "sheet_tsv"
    assert rec["sha256"] == F._sha256(KRAKOVNA_TSV_EXPORT.encode())
    assert rec["size_bytes"] == len(KRAKOVNA_TSV_EXPORT.encode())
    assert rec["version_label"] == "2026-10-13"
    assert rec["version_pin"] == f"captured 2026-10-13, sha256 {rec['sha256'][:12]}"
    assert rec["license"] is None and rec["read_only"] is True and rec["tool"] == F.TRANSIENT_TOOL
    assert "Example" not in json.dumps(rec)


def test_krakovna_tsv_export_chunks_from_its_header_line():
    """Regression (2026-10-13): the TSV export's first line is a banner, and the header line (first cell ``Title``)
    comes second; read from the top, the banner was taken for the header.  Section dividers stay rows, as before."""
    chunks = CH.chunk_source("krakovna", KRAKOVNA_TSV_EXPORT, version="2026-10-13")
    assert [c.chunk_id for c in chunks] == ["krakovna:2026-10-13:rows-0001-0010", "krakovna:2026-10-13:rows-0011-0020",
                                            "krakovna:2026-10-13:rows-0021-0024"]
    for c in chunks:
        assert c.text.splitlines()[0].split("\t") == list(KRAKOVNA_HEADER)       # the header, not the banner
        assert "Submit more examples" not in c.text and "\r" not in c.text
    lines = chunks[0].text.splitlines()
    assert lines[1].split("\t") == ["", "Evolutionary and genetic algorithms"] + [""] * 8   # a divider: one row
    first = dict(zip(KRAKOVNA_HEADER, lines[2].split("\t")))
    assert first["Title"] == "Example 1.1" and first["Intended goal"] == "goal 1.1"
    assert first["Misspecified goal"] == "proxy 1.1" and first["Behavior"] == "games proxy 1.1"
    assert first["Type of system"] == "RL agent" and first["Credit"] == ""
    assert chunks[-1].text.splitlines()[-1].startswith("Example 3.7\t")            # the empty last row is dropped


def test_a_sheet_with_no_header_line_stops_instead_of_giving_no_chunks():
    """The ``pubhtml`` page as Google draws it now (a script widget, no table) gave 0 chunks and no error."""
    page = '<html><body><div id="sheets-viewport"></div><script>var x = 1;</script></body></html>'
    with pytest.raises(ValueError, match=r"no header line \(first cell 'Title'\)"):
        CH.chunk_source("krakovna", page, version="v")
    with pytest.raises(ValueError, match="no row under the header"):
        CH.chunk_source("krakovna", "\tbanner\t\r\n" + "\t".join(KRAKOVNA_HEADER) + "\r\n\t\t\r\n", version="v")


def test_published_sheet_tsv_url():
    base = "https://docs.google.com/spreadsheets/d/e/2PACX-abc"
    assert F.published_sheet_tsv_url(f"{base}/pubhtml") == f"{base}/pub?output=tsv"
    assert F.published_sheet_tsv_url(f"{base}/pubhtml?gid=7&single=true") == f"{base}/pub?gid=7&single=true&output=tsv"
    assert F.published_sheet_tsv_url(f"{base}/pub?output=csv") == f"{base}/pub?output=tsv"
    assert (F.published_sheet_tsv_url("https://docs.google.com/spreadsheets/d/1AbC/edit#gid=0")
            == "https://docs.google.com/spreadsheets/d/1AbC/pub?gid=0&single=true&output=tsv")
    with pytest.raises(ValueError):
        F.published_sheet_tsv_url("https://example.org/spreadsheets/d/e/x/pubhtml")


def test_unknown_key_refused(tmp_path):
    with pytest.raises(KeyError):
        F.fetch_all(only=["nope"], fetcher=fake_fetcher({}), dest_root=tmp_path, sources_manifest_path=None)


def test_licence_line_found_for_a_cc0_page():
    assert "CC0 1.0 Deed" in F.licence_sentence(CH.html_to_markdown(CONSTITUTION_HTML), "CC0")
    assert F.licence_sentence("No licence here.", "CC0") is None


def test_repo_relative_file_paths(tmp_path):
    p = Path(F.__file__).resolve().parents[4] / "data" / "external" / "alignment_sweep" / "x.md"
    assert F._rel(p) == "data/external/alignment_sweep/x.md"
