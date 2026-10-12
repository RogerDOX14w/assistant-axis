"""IPIP generator, acceptance on the recorded outputs (plan § 8, last item).  Each check skips while its output is
not on disk.  One is red on purpose as of 2026-10-12, a finding for Roger rather than a failure of the tool: the
naming parse rate (98.5% against the 99% bar).  The A-vs-B key comparison was the other (QUESTIONS 52, a 35% item
mismatch) until Roger set its criterion that day (code review C1): sign disagreement on the shared links, with the
coverage differences reported, not gated."""
import json
import warnings

import pytest

from assistant_axis.gapgen.generators import ipip as P
from assistant_axis.gapgen.generators.ipip import ingest as I
from assistant_axis.gapgen.generators.ipip.report import naming_parse_stats
from assistant_axis.gapgen.paths import runs_root


def _skip_unless(path):
    if not path.exists():
        pytest.skip(f"{path} not recorded yet")


def test_ingest_counts():
    _skip_unless(P.ITEMS_PATH)
    items = I.load_items(P.ITEMS_PATH)
    assert len(items) >= 3000
    counts = json.loads(P.INGEST_COUNTS_PATH.read_text())
    assert counts["hex"]["constructs"] >= 20 and counts["hex_assertion"] == "passed"
    assert counts["key_page_check"] == "passed" and counts["key_pages"]["n_pages_read"] == 21
    assert [r.ipip_id for r in items] == sorted((r.ipip_id for r in items), key=I.code_order)
    # QUESTIONS 46: every committed key says where its sign came from, and the key pages are the primary source
    assert all(s["key_source"] in (I.SOURCE_B, I.SOURCE_A) for r in items for s in r.scales)
    assert counts["key_sources"].get(I.SOURCE_B, 0) > counts["key_sources"].get(I.SOURCE_A, 0)


def test_the_a_against_b_comparison_is_recorded_and_within_rogers_limits():
    """QUESTIONS 52: the ingest reports A against B both ways; a sign disagreement beyond rounding goes to Roger
    rather than into code.  The criterion (Roger, 2026-10-12, code review C1; it was ``not needs_roger``, which also
    gated the item mismatch and coverage): at most ``MISMATCH_LIMIT`` (2%) of the links both sources key carry
    different signs (0.1% on the recorded ingest, 3 of 2,909).  The coverage differences are reported here as a
    warning, not gated (974 key-page-only links and 487 workbook-only, 44 and 15 items, on the recorded ingest).
    Read from the recorded fields, so it holds for an ingest written before the criterion changed."""
    _skip_unless(P.INGEST_COUNTS_PATH)
    c = json.loads(P.INGEST_COUNTS_PATH.read_text())["key_comparison"]
    if not c["compared"]:
        pytest.skip("the workbook (source A) was not on disk for this ingest")
    for k in ("n_items_b", "n_items_a", "items_only_b", "items_only_a", "exact_match_rate", "sign_conflicts",
              "n_links_shared", "link_mismatch_rate", "links_only_b", "links_only_a"):
        assert k in c, k
    assert c["n_links_shared"] > 0
    assert c["link_mismatch_rate"] <= I.MISMATCH_LIMIT, (
        f"{c['sign_conflicts']} of {c['n_links_shared']} shared links ({c['link_mismatch_rate']:.2%}) carry different "
        f"signs, over the {I.MISMATCH_LIMIT:.0%} limit: the A-vs-B difference has to go to Roger")
    warnings.warn(f"IPIP A-vs-B coverage (reported, not gated): {c['links_only_b']} links only the key pages key, "
                  f"{c['links_only_a']} only the workbook; {c['items_only_b']} and {c['items_only_a']} items; item "
                  f"mismatch {c['item_mismatch_rate']:.1%}; sign disagreement {c['sign_conflicts']} of "
                  f"{c['n_links_shared']} shared links")


def test_the_licence_sentence_is_on_record_verbatim():
    """QUESTIONS 46: our record of the licence was second-hand (a quote of plan 07's prose) until the home page
    was fetched, which is the one thing the home page is fetched for.  Skips until it is on disk: the manifest of
    the 2026-10-10 fetch is on disk already and carries ``verbatim: null`` by construction."""
    _skip_unless(P.SOURCES_MANIFEST_PATH)
    man = json.loads(P.SOURCES_MANIFEST_PATH.read_text())
    if not any(e.get("key") == "home" for e in man.get("entries") or []):
        pytest.skip("the home page has not been fetched yet (QUESTIONS 46)")
    lic = man["licence"]
    assert lic["verbatim"] and "public domain" in lic["verbatim"].lower()
    assert lic["verbatim_source"] and lic.get("credit")


def test_naming_parse_rate():
    _skip_unless(P.NAMING_RESPONSES_PATH)
    recs = [json.loads(x) for x in P.NAMING_RESPONSES_PATH.read_text().splitlines() if x.strip()]
    stats = naming_parse_stats(recs)
    assert stats["parse_rate"] >= 0.99, stats
    assert P.NAMING_USAGE_PATH.exists()


def test_usage_json_in_every_run_and_granularity_dir():
    dirs = [d for d in (runs_root() / P.GENERATOR).glob("*") if d.is_dir()] if (runs_root() / P.GENERATOR).exists() else []
    dirs += [d for d in P.GRANULARITY_DIR.glob("g*") if d.is_dir()] if P.GRANULARITY_DIR.exists() else []
    if not dirs:
        pytest.skip("no IPIP run or granularity directory recorded yet")
    for d in dirs:
        assert (d / "usage.json").exists(), d


def test_evaluations_report_agreement_and_recovery():
    root = runs_root() / P.GENERATOR
    evs = sorted(root.glob("*/evaluation.json")) if root.exists() else []
    if not evs:
        pytest.skip("no IPIP evaluation recorded yet")
    for p in evs:
        ev = json.loads(p.read_text())["result"]
        for g, a in ev["naming"]["agreement"].items():
            assert "antonym_agreement" in a and a["antonym_target"] == 0.8
        assert "share" in ev["recovery"]["exact"] and ev["recovery"]["exact"]["target"] == 0.9
        # QUESTIONS 48: the kind guesses are reported, in M1's vocabulary, and nothing gated on them
        for g, a in ev["naming"]["agreement"].items():
            assert set(a["kind"]) == {"blind", "hinted"} and "is_trait" not in a
        assert "kind_vs_m1" in ev["naming"]
        counts = (ev["submitted"].get("counts") or {})
        assert counts.get("n_named") == counts.get("n_submitted")
