"""The Roget coverage map (workstream 2, plan § 8 "Coverage", with the covered / partly / queued /
empty states of the 2026-10-08 brief)."""
from __future__ import annotations

import json

import pytest

from assistant_axis.gapgen.generators.roget import coverage as C
from assistant_axis.gapgen.generators.roget import pairs as PR
from assistant_axis.tests.roget_fakes import make_index


def row(state, n_existing=0, partner=None):
    return C.HeadRow(id="x", title="X", path="V", klass="V", section="I. S", partner=partner, pair_kind="pair",
                     pair_source="rule", members=[], n_existing=n_existing, state=state)


def test_gap_class_truth_table():
    covered, empty = row("covered", 1), row("empty")
    assert C.gap_class(row("empty", partner="p"), covered) == "pair_completion"
    assert C.gap_class(row("empty", partner="p"), empty) == "pair_empty"
    assert C.gap_class(row("empty", partner="p"), row("queued")) == "pair_empty"
    assert C.gap_class(row("empty"), None) == "singleton_empty"
    assert C.gap_class(row("queued", partner="p"), covered) == "queued_only"
    assert C.gap_class(row("partly"), None) == "partly_covered"
    assert C.gap_class(row("covered", 3), None) == "crowded"
    assert C.gap_class(row("covered", 2), None) == "covered"


def LH(source, primary, secondary=(), status=None, lexical=(), semantic=(), label=None):
    return {"label": label, "source": source, "status": status, "primary": primary, "secondary": list(secondary),
            "lexical": list(lexical), "semantic": list(semantic)}


@pytest.fixture()
def world():
    idx = make_index([
        {"id": "1", "title": "Existence", "adj": [["real"]], "klass": "I", "section": "I. Existence",
         "subsection": "1. Being"},
        {"id": "2", "title": "Inexistence", "adj": [["unreal"]], "klass": "I", "section": "I. Existence",
         "subsection": "1. Being"},
        {"id": "604", "title": "Resolution", "adj": [["resolute"]]},
        {"id": "605", "title": "Irresolution", "adj": [["irresolute"]]},
        {"id": "606", "title": "Obstinacy", "adj": [["obstinate"]]},
        {"id": "607", "title": "Tergiversation", "adj": [["fickle"]]},
        {"id": "863", "title": "Rashness", "adj": [["rash"]], "klass": "VI", "section": "II. Personal affections"},
        {"id": "864", "title": "Caution", "adj": [["cautious"]], "klass": "VI", "section": "II. Personal affections"},
        {"id": "900", "title": "Resentment", "adj": [["resentful"]], "klass": "VI", "section": "III. Sympathetic"},
    ])
    pairs = PR.rule_pairs(idx, None)
    assert pairs["604"].partner == "605" and pairs["863"].partner is None   # no evidence for 863/864 here
    # declare 863 / 864 a pair by hand (the rules found no evidence in this toy)
    pairs["863"] = PR.HeadPairing("863", "864", "pair", ["863", "864"], {}, "rule")
    pairs["864"] = PR.HeadPairing("864", "863", "pair", ["863", "864"], {}, "rule")
    lh = {
        "cautious": LH("existing", "864"),
        "resolute": LH("queued", "604", status="candidate"),
        "dropped": LH("queued", "606", status="not_adopted"),
        "fickle_ish": LH("existing", "900", secondary=["607"]),
        "a": LH("existing", "900"), "b": LH("existing", "900"),
        "real": LH("existing", "1", lexical=[{"head_id": "1", "strength": "exact_adj"}],
                   semantic=[{"head_id": "1", "sim": 0.5, "rank": 1}]),
        "unreal_word": LH("existing", "900", lexical=[{"head_id": "2", "strength": "exact_adj"}]),
        "loosely": LH("existing", "900", lexical=[{"head_id": "2", "strength": "loose"}], secondary=["2"]),
    }
    return idx, pairs, lh


def test_states_and_gap_classes(world):
    idx, pairs, lh = world
    rep = C.coverage(idx, pairs, lh)
    r = rep.by_id()
    assert r["864"].state == "covered" and r["864"].gap_class == "covered"
    assert r["863"].gap_class == "pair_completion" and r["863"].partner_existing == ["cautious"]
    assert r["604"].state == "queued" and r["604"].gap_class == "queued_only"
    assert r["605"].gap_class == "pair_empty"
    # a parked queue label is listed but never makes a head queued
    assert r["606"].queued_parked == ["dropped"] and r["606"].state == "empty"
    assert r["606"].gap_class == "singleton_empty"
    assert r["607"].state == "partly" and r["607"].existing_secondary == ["fickle_ish"]
    assert r["900"].gap_class == "crowded" and r["900"].n_existing == 5
    # Class I-III: head 1 is brought in (exact adjective where the label's sense is); head 2 is not
    assert "1" in r and r["1"].triggers == ["real"]
    assert "2" not in r
    s = rep.summary
    assert s["n_heads"] == 8 and s["class_i_iii_added"] == 1
    assert s["covered_partly_uncovered"] == {"covered": 3, "partly_covered": 1, "uncovered": 4, "of_which_queued": 1}
    # 863/864 and 1/2 (Existence / Inexistence, a title negation; 2 is out of scope) have one pole covered
    assert s["opposed_pairs"] == {"one_pole_covered": 2, "neither_pole_covered": 1}


def test_hidden_removes_stems_first(world):
    idx, pairs, lh = world
    r = C.coverage(idx, pairs, lh, hidden=["cautious"]).by_id()
    assert r["864"].state == "empty" and r["863"].gap_class == "pair_empty"
    assert C.coverage(idx, pairs, lh, hidden=["real"]).by_id().get("1") is None


def test_restricted_class_i_iii(world):
    idx, _, lh = world
    assert C.restricted_class_i_iii(idx, lh) == {"1": ["real"]}
    loose = C.restricted_class_i_iii(idx, lh, require_sense=False)
    assert loose == {"1": ["real"], "2": ["unreal_word"]}              # never on a loose hit
    parked = {"x": LH("queued", "1", status="superseded", lexical=[{"head_id": "1", "strength": "exact_adj"}],
                      semantic=[{"head_id": "1", "sim": 0.5, "rank": 1}])}
    assert C.restricted_class_i_iii(idx, parked) == {}


def test_markdown_order_and_links(world, tmp_path):
    idx, pairs, lh = world
    rep = C.coverage(idx, pairs, lh)
    md = C.render_markdown(rep, idx, lh)
    heads = [l for l in md.splitlines() if l.startswith("## ")]
    order = [h.split(" (")[0][3:] for h in heads if h[3:].split(" (")[0] in C.GAP_CLASSES]
    assert order == ["pair_completion", "pair_empty", "singleton_empty", "queued_only", "partly_covered"]
    assert "[cautious](../../traits/instructions/cautious.json)" in md
    assert "(../../seed_queue.json) (queued)" in md
    C.write_coverage(rep, tmp_path / "c.json", tmp_path / "c.md", index=idx, label_heads=lh)
    back = C.load_coverage(tmp_path / "c.json")
    assert [r.id for r in back.rows] == [r.id for r in rep.rows]
    assert "_provenance" in json.loads((tmp_path / "c.json").read_text())
