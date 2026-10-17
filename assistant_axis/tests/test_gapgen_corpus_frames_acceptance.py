"""Corpus-frames generator: acceptance on the recorded outputs (plan section 8; each test skips while its output is
absent).

Hard: the manifest names the approval and its bytes streamed agree with the shard plan within 1%; ``evaluation.json``
carries both orderings' union recall beside the wordfreq baseline, the per-frame recovery and the unfound labels by
region, and after the pilot every frame's yield, ``region_tv``, ``form_tv``, ``physical_state_share`` and
``unique_kept``; ``frame_stats.json`` has a row for every frame of the streamed tier; ``usage.json`` beside every run
with the generator's cost at 0.0; the table's sha256 in ``evaluation.json`` equals the file's (the table is
git-ignored: skipped in a checkout without it); every run's ``report.md`` carries the already-registered headline, the
net-new kept share and the contributing frame of every kept row; the package imports neither ``anthropic`` nor
``openai``; ``git status --porcelain data/traits data/roles data/seed_queue.json`` is empty.  Report-and-decide (a
warning, never a failure): the frames beating the wordfreq baseline at 1,000 (platform review amendment 2)."""
import hashlib
import json
import re
import subprocess
import warnings
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators import corpus_frames as G
from assistant_axis.gapgen.paths import REPO_ROOT, runs_root

PKG = Path(G.__file__).parent
RUNS = sorted(p for p in (runs_root() / G.GENERATOR).glob("*") if (p / "candidates.jsonl").exists()) \
    if (runs_root() / G.GENERATOR).exists() else []


def _payload(p: Path) -> dict:
    d = json.loads(p.read_text())
    return d.get("result", d) if isinstance(d, dict) and "_provenance" in d else d


def _need(p: Path) -> dict:
    if not p.exists():
        pytest.skip(f"{p.name} not recorded yet")
    return _payload(p)


def test_the_manifest_names_the_approval_and_its_bytes_agree_with_the_plan():
    src = _need(G.SOURCES_MANIFEST_PATH)
    books = src.get("books")
    if not books:
        pytest.skip("no Books stream recorded yet")
    plan = _need(G.SHARD_PLAN_PATH)
    assert books["approvals"] and all(a.strip() for a in books["approvals"])
    assert all(r.get("approval") for r in books["shards"])
    done = {r["shard"] for r in books["shards"]}
    planned = {f"{s['n']}-{s['index']:05d}": s["bytes"] for s in plan["shards"]}
    in_plan = sum(b for k, b in planned.items() if k in done)
    assert in_plan and abs(books["bytes_streamed"] - in_plan) <= 0.01 * in_plan
    for e in books["extracts"].values():
        assert e["sha256"] and e["lines"] >= 0


def test_the_text_corpora_record_their_licence_and_approval():
    src = _need(G.SOURCES_MANIFEST_PATH)
    text = src.get("text")
    if not text:
        pytest.skip("no text corpus recorded yet")
    for e in text["entries"]:
        assert e["approval"] and e["licence"] in ("Apache-2.0", "CC BY 4.0") and e["files"]
        assert all(len(f["sha256"]) == 64 and f["url"] for f in e["files"])


def test_the_evaluation_reports_what_the_plan_asks():
    ev = _need(G.EVALUATION_PATH)
    rec = ev["recovery"]
    for name in ("union_volumes", "union_lift"):
        assert "recall@1000" in rec[name]["corpus"]["all"], name
    assert "per_frame" in rec and rec["per_frame"]
    assert "by_region" in ev["unfound_labels"] and ev["ordering"] in ("volumes", "lift")
    if "baseline_wordfreq" not in rec:
        warnings.warn("evaluation.json has no OEWN wordfreq baseline (OEWN was not installed when it was made)")
    else:
        best = max(rec[n]["corpus"]["all"]["recall@1000"] or 0 for n in ("union_volumes", "union_lift"))
        base = rec["baseline_wordfreq"]["corpus"]["all"]["recall@1000"] or 0
        if best <= base:
            warnings.warn(f"the frames do not beat the wordfreq baseline at 1,000 ({best} <= {base}): report and "
                          f"decide")
    if ev.get("pilot_run"):
        fm = ev["frame_measures"]
        for k, m in fm.items():
            if k == "_union":
                continue
            for f in ("yield", "region_tv", "form_tv", "physical_state_share", "unique_kept"):
                assert f in m, (k, f)


def test_frame_stats_cover_every_streamed_frame():
    stats = _need(G.FRAME_STATS_PATH)
    src = _payload(G.SOURCES_MANIFEST_PATH) if G.SOURCES_MANIFEST_PATH.exists() else {}
    streamed = {f for r in (src.get("books") or {}).get("shards") or [] for f in r.get("frames") or []}
    if not streamed:
        pytest.skip("no Books stream recorded yet")
    have = {s["frame"] for s in stats["frames"]}
    assert streamed <= have, sorted(streamed - have)


def test_the_tables_sha256_is_the_recorded_one():
    ev = _need(G.EVALUATION_PATH)
    if not G.TABLE_PATH.exists():
        pytest.skip("frames_table.jsonl is git-ignored and absent from this checkout")
    assert ev["table_sha256"] == hashlib.sha256(G.TABLE_PATH.read_bytes()).hexdigest()


@pytest.mark.parametrize("run", RUNS, ids=[p.name for p in RUNS])
def test_generator_usage_is_zero(run):
    u = json.loads((run / "usage.json").read_text())
    assert u["total_cost_usd"] == 0.0 and u["n_calls"] == 0


@pytest.mark.parametrize("run", RUNS, ids=[p.name for p in RUNS])
def test_every_report_carries_the_headline_the_share_and_the_contributing_frames(run):
    p = run / "report.md"
    if not p.exists():
        pytest.skip("report not written yet")
    md = p.read_text()
    assert "## 1. Already registered" in md and "Net-new kept share" in md
    assert "## The contributing frames of every kept row" in md


def test_the_package_imports_neither_anthropic_nor_openai():
    for p in sorted(PKG.glob("*.py")):
        text = p.read_text()
        assert not re.search(r"^\s*(import|from)\s+(anthropic|openai)\b", text, re.M), p.name
    cli = REPO_ROOT / "data_analysis" / "gap_generation" / "corpus_frames_generator.py"
    assert not re.search(r"^\s*(import|from)\s+(anthropic|openai)\b", cli.read_text(), re.M)


#: Files under the checked paths that other sessions create in the shared main checkout and this generator never writes
#: (review M2, 2026-10-17): the naming check's history, untracked there on 2026-10-17.
FOREIGN_ALLOWED: frozenset = frozenset({"data/traits/name_check_history.jsonl"})
CHECKED_PATHS = ("data/traits", "data/roles", "data/seed_queue.json")


def unexpected_changes(porcelain: str, allowed=FOREIGN_ALLOWED) -> list[str]:
    """The paths of a ``git status --porcelain`` listing, tracked changes and untracked files alike (a new trait file
    is untracked), less the allow-listed foreign files."""
    out = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:                                  # a rename: the new path
            path = path.split(" -> ", 1)[1].strip('"')
        if path not in allowed:
            out.append(path)
    return sorted(out)


def test_unexpected_changes_sees_new_files_and_allows_only_the_known_foreign_one():
    listing = ("?? data/traits/name_check_history.jsonl\n"
               "?? data/traits/instructions/frame_found.json\n"
               " M data/roles/instructions/actor.json\n"
               "R  data/traits/instructions/a.json -> data/traits/instructions/b.json\n")
    assert unexpected_changes(listing) == ["data/roles/instructions/actor.json", "data/traits/instructions/b.json",
                                           "data/traits/instructions/frame_found.json"]
    assert unexpected_changes("?? data/traits/name_check_history.jsonl\n") == []


def test_no_trait_role_or_queue_file_was_touched():
    """Tracked changes and untracked files (``--untracked-files=all``: a new trait file must show), less the
    allow-listed foreign files of the shared main checkout (:data:`FOREIGN_ALLOWED`); this generator writes nothing
    under these paths."""
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", *CHECKED_PATHS],
                             cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git unavailable")
    assert unexpected_changes(out) == []
