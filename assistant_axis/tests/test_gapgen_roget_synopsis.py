"""Roget's own opposed-head pairing from the Tabular Synopsis of Categories of the printed 1911 edition
(QUESTIONS 38): the positional OCR reader, the row / triad / singleton layout rules, the merge into the
rule pairing, and the checks.  No network: the reader runs on a hand-made positional fixture
(``fixtures/roget_synopsis_sample.xml``) in the shape of the Internet Archive's djvu XML."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.roget import pairs as PR
from assistant_axis.gapgen.generators.roget import parse as P
from assistant_axis.gapgen.generators.roget import synopsis as S
from assistant_axis.tests.roget_fakes import make_index

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "roget_synopsis_sample.xml"


def sample_index():
    """The heads the fixture prints, with the subsections of the Gutenberg parse, plus 59a Complexity,
    a head Gutenberg has and the 1911 synopsis does not."""
    spec = [("1", "Existence", "1. Abstract"), ("2", "Inexistence", "1. Abstract"),
            ("3", "Substantiality", "2. Concrete"), ("4", "Unsubstantiality", "2. Concrete"),
            ("13", "Identity", "3. Absolute relation"), ("14", "Contrariety", "3. Absolute relation"),
            ("15", "Difference", "3. Absolute relation"),
            ("16", "Uniformity", "4. Continuous relation"), ("16a", "Nonuniformity", "4. Continuous relation"),
            ("27", "Equality", "5. Comparative quantity"), ("28", "Inequality", "5. Comparative quantity"),
            ("59a", "Complexity", "6. Order in general"),
            ("608", "Caprice", None), ("609", "Choice", None), ("609a", "Absence of Choice", None),
            ("610", "Rejection", None), ("611", "Predetermination", None), ("612", "Impulse", None),
            ("613", "Habit", None), ("614", "Desuetude", None)]
    return make_index([{"id": h, "title": t, **({"subsection": sub} if sub else {})} for h, t, sub in spec])


@pytest.fixture(scope="module")
def result():
    return S.read_synopsis(S.synopsis_pages(S.read_pages(FIXTURE)), sample_index())


# --------------------------------------------------------------------------- reading


def test_read_pages_and_select_the_synopsis():
    pages = S.read_pages(FIXTURE)
    assert [p.leaf for p in pages] == [26, 27]
    syn = S.synopsis_pages(pages)
    assert [p.leaf for p in syn] == [27]
    assert syn[0].label == "xxi"
    w = syn[0].words[0]
    assert (w.text, w.x0, w.top, w.x1, w.bottom) == ("TABULAR", 274, 492, 735, 555)


def test_read_number_strips_junk_and_refuses_letters_for_digits():
    assert S.read_number("16a.") == ("16a", False)
    assert S.read_number("100.") == ("100", False)
    assert S.read_number("r27.") == ("27", True)          # the plain text's "r27."
    assert S.read_number("[105.") == ("105", True)
    assert S.read_number("987_") == ("987", True)
    assert S.read_number("A77") == ("77", True)           # parsed, then rejected by the order check
    assert S.read_number("S09.") is None                  # a leading zero is not a number here
    assert S.read_number("Choice") is None


def test_confusion_readings():
    assert "809" in S.confusion_readings("S09.")
    assert "983a" in S.confusion_readings("9g3a.")
    assert "477" in S.confusion_readings("A77")
    assert "498" in S.confusion_readings("4ys'")
    assert "499" in S.confusion_readings("4qq")
    assert "612" in S.confusion_readings("6l2.")
    assert S.confusion_readings("aqc") == set()           # no digit at all: never read as a number


def test_title_score():
    assert S.title_score("Absence of Choice", "Absence of Choice") == 1.0
    assert S.title_score("Nonincrease, Decrease", "Decrease") == 0.5
    assert S.title_score("Pretext", "Plea") == 0.0
    assert S.title_score("Undueness", "Unduenesa") == 1.0    # fuzzy


def test_entries_columns_and_repairs(result):
    e = {x.id: x for x in result.entries}
    assert set(e) == {"1", "2", "3", "4", "13", "14", "15", "16", "16a", "27", "28", "608", "609", "609a", "610",
                      "611", "612", "613", "614"}
    assert (e["1"].column, e["2"].column, e["15"].column, e["609"].column, e["609a"].column) == \
        ("L", "R", "M", "L", "R")
    assert e["27"].repair == {"method": "stripped", "token": "r27."}
    assert e["612"].repair["method"] == "ocr_confusion+title" and e["612"].repair["token"] == "6l2."
    assert e["613"].repair["method"] == "title" and e["613"].column == "L" and e["613"].token is None
    assert result.missing == ["59a"] and result.duplicates == []
    # the centred header "1. Actual Subservience" reads as head 1, out of order: rejected and listed
    assert [(t["text"], t["leaf"]) for t in result.unused_tokens] == [("1.", 27)]
    assert all(x.page == "xxi" and x.leaf == 27 for x in result.entries)


def test_blocks_pairs_triads_singletons(result):
    r = result.records()
    assert (r["1"]["kind"], r["1"]["partner"], r["2"]["partner"]) == ("pair", "2", "1")
    assert r["3"]["partner"] == "4" and r["16"]["partner"] == "16a" and r["27"]["partner"] == "28"
    # centred: 15 Difference joins the row above (same subsection), which stays a pair
    assert r["13"]["partner"] == "14" and r["13"]["kind"] == "pair"
    assert r["15"]["kind"] == "triad" and r["15"]["partner"] is None and r["15"]["members"] == ["13", "14", "15"]
    assert r["15"]["block"] == r["13"]["block"] and r["15"]["row"] == r["13"]["row"] == 3
    # braced: 609 Choice centred against 609a and 610; the unlettered one is its partner
    assert r["609"]["partner"] == "610" and r["610"]["partner"] == "609"
    assert r["609a"]["kind"] == "triad" and r["609a"]["members"] == ["609", "609a", "610"]
    assert r["608"]["kind"] == "singleton" and r["608"]["members"] == ["608"]
    assert r["611"]["partner"] == "612" and r["613"]["partner"] == "614"
    blocks = {b["id"]: b for b in result.blocks_json()}
    b609 = blocks[r["609"]["block"]]
    assert (b609["how"], b609["left"], b609["right"], b609["pair"], b609["third"]) == \
        ("brace", ["609"], ["609a", "610"], ["609", "610"], ["609a"])
    assert blocks[r["15"]["block"]]["how"] == "centred" and blocks[r["15"]["block"]]["middle"] == ["15"]
    assert [b["row"] for b in result.blocks_json()] == list(range(1, len(blocks) + 1))   # one page, top to bottom


def _entry(hid, col, y, leaf=33):
    return S.Entry(id=hid, leaf=leaf, page="xxvii", column=col, x0={"L": 996, "M": 1390, "R": 1583}[col], y=y,
                   ys=[y], token=f"{hid}.", title="", title_match=1.0)


def test_centred_entry_joins_the_row_laid_out_around_it():
    """639 Sufficiency is centred between 637 Provision | 638 Waste and 641 Redundance | 640 Insufficiency,
    in one subsection and next in number to both rows; the row below is printed with its numbers inverted
    (641 left of 640), so it was laid out around the centred head.  Without an inversion: the row above."""
    idx = make_index([{"id": str(n), "title": t} for n, t in
                      ((637, "Provision"), (638, "Waste"), (639, "Sufficiency"), (640, "Insufficiency"),
                       (641, "Redundance"), (420, "Light"), (421, "Darkness"), (422, "Dimness"), (423, "Luminary"),
                       (424, "Shade"))])
    ents = [_entry("637", "L", 1000), _entry("638", "R", 1000), _entry("639", "M", 1044),
            _entry("641", "L", 1088), _entry("640", "R", 1088)]
    blocks = S.build_blocks(ents, idx)
    b = next(b for b in blocks if "639" in b.middle)
    assert b.pair == ("641", "640") and sorted(b.members) == ["639", "640", "641"]
    ents = [_entry("420", "L", 1000, leaf=31), _entry("421", "R", 1000, leaf=31), _entry("422", "M", 1044, leaf=31),
            _entry("423", "L", 1088, leaf=31), _entry("424", "R", 1088, leaf=31)]
    b = next(b for b in S.build_blocks(ents, idx) if "422" in b.middle)
    assert b.pair == ("420", "421")


def test_two_centred_entries_and_a_header_gap():
    """27 Equality | 28 Inequality, then 29 Mean and 30 Compensation centred one under the other: one block
    of four; a centred entry with no pair within reach stays a singleton."""
    idx = make_index([{"id": str(n), "title": str(n)} for n in (27, 28, 29, 30, 31, 32, 99)])
    ents = [_entry("27", "L", 1000), _entry("28", "R", 1000), _entry("29", "M", 1044), _entry("30", "M", 1088),
            _entry("31", "L", 1190), _entry("32", "R", 1190), _entry("99", "M", 1400)]
    blocks = S.build_blocks(ents, idx)
    b = next(b for b in blocks if "29" in b.middle)
    assert b.middle == ["29", "30"] and b.pair == ("27", "28")
    lone = next(b for b in blocks if "99" in b.members)
    assert lone.how == "alone" and lone.pair is None


def test_override_block_615():
    """The printed brace groups 615a Absence of Motive and 616 Dissuasion against 615 Motive and 617 Plea, in
    rows the geometry would read as two pairs; the one hand-recorded block (OVERRIDES)."""
    idx = make_index([{"id": h, "title": t} for h, t in (("615", "Motive"), ("615a", "Absence of Motive"),
                                                         ("616", "Dissuasion"), ("617", "Pretext"))])
    ents = [_entry("615", "L", 1968), _entry("615a", "R", 1970), _entry("617", "L", 2013), _entry("616", "R", 2013)]
    blocks = S.build_blocks(ents, idx)
    assert len(blocks) == 1
    b = blocks[0]
    assert (b.how, b.pair, sorted(b.third)) == ("override", ("615", "616"), ["615a", "617"])


def test_braced_multiline_title_aligns_on_any_line():
    """343 {Gulf, Lake}: its number is centred on two title lines and 344 Plain is printed on the second;
    aligned (a pair), not a half-line offset (a brace)."""
    idx = make_index([{"id": h, "title": h} for h in ("343", "344")])
    a = _entry("343", "L", 1209)
    a.ys = [1209, 1198, 1220]
    blocks = S.build_blocks([a, _entry("344", "R", 1220)], idx)
    assert blocks[0].how == "row" and blocks[0].pair == ("343", "344")


# --------------------------------------------------------------------------- persistence and checks


def test_save_and_load(tmp_path, result):
    path = S.save(result, tmp_path / S.FILE_NAME, meta={"source": {"file": "x.xml"}})
    env = json.loads(path.read_text(encoding="utf-8"))
    assert "_provenance" in env
    pay = env["result"]
    assert pay["synopsis_version"] == S.SYNOPSIS_VERSION and pay["source"]["file"] == "x.xml"
    back = S.load(path)
    assert back == result.records()
    assert {x["method"] for x in pay["repairs"]} == {"stripped", "ocr_confusion+title", "title"}


def _rules_world():
    idx = make_index([{"id": h, "title": t} for h, t in
                      (("604", "Resolution"), ("604a", "Perseverance"), ("605", "Irresolution"),
                       ("606", "Obstinacy"), ("607", "Tergiversation"), ("608", "Caprice"), ("609", "Choice"),
                       ("609b", "Whim"), ("610", "Rejection"), ("610a", "Refusal"), ("611", "Predetermination"))])

    def hp(h, p, kind="pair", src="rule", members=None):
        return PR.HeadPairing(h, p, kind, members or sorted([x for x in (h, p) if x], key=idx.position),
                              {"llm": None}, src)

    rules = {"604": hp("604", "605"), "605": hp("605", "604"),
             "604a": hp("604a", None, "triad", members=["604", "604a", "605"]),
             "606": hp("606", "607"), "607": hp("607", "606"), "608": hp("608", "611"),
             "609": hp("609", "609b", src="rule_weak"), "609b": hp("609b", "609", src="rule_weak"),
             "610": hp("610", "610a"), "610a": hp("610a", "610"), "611": hp("611", "608")}

    def rec(kind, partner=None, members=None, block=1):
        return {"kind": kind, "partner": partner, "members": members, "block": block, "page": "xxvii", "row": block}

    syn = {"604": rec("pair", "605", ["604", "605"]), "605": rec("pair", "604", ["604", "605"]),
           "604a": rec("singleton", None, ["604a"], 2),
           "606": rec("pair", "607", ["606", "607"], 3), "607": rec("pair", "606", ["606", "607"], 3),
           "608": rec("triad", None, ["606", "607", "608"], 3), "609": rec("singleton", None, ["609"], 4),
           "610": rec("pair", "611", ["610", "611"], 5), "611": rec("pair", "610", ["610", "611"], 5)}
    return idx, rules, syn


def test_merge_synopsis_governs_and_rules_fill_the_rest():
    idx, rules, syn = _rules_world()
    m = PR.merge_synopsis(idx, rules, syn)
    assert set(m) == set(idx.order)
    assert (m["604"].partner, m["604"].source) == ("605", "synopsis")
    assert m["604"].evidence["rule"] == {"kind": "pair", "partner": "605", "source": "rule"}
    assert m["604a"].kind == "singleton" and m["604a"].source == "synopsis"
    assert m["604a"].evidence["rule"]["kind"] == "triad"
    assert m["608"].kind == "triad" and m["608"].members == ["606", "607", "608"]
    # a synopsis singleton keeps a rule partner the 1911 synopsis does not print (609b)
    assert (m["609"].partner, m["609"].source, m["609"].evidence["synopsis"]["kind"]) == ("609b", "rule_weak",
                                                                                          "singleton")
    assert m["609b"].partner == "609"
    # a head the synopsis does not print, whose rule partner the synopsis pairs elsewhere
    assert m["610a"].kind == "singleton" and m["610a"].partner is None and m["610a"].source == "rule"
    assert m["610a"].evidence["partner_taken_by_synopsis"] == "610"
    assert (m["611"].partner, m["611"].source) == ("610", "synopsis")
    assert all(m[x.partner].partner == h for h, x in m.items() if x.partner)


def test_checks_against_known_pairs_and_rules():
    idx, rules, syn = _rules_world()
    known = [{"a": "604", "b": "605"}, {"a": "606", "b": "608"}, {"a": "609", "b": "610"}]
    c = S.check(idx, syn, rules, known)
    k = c["known_pairs"]
    assert k["pair"] == [["604", "605"]] and k["same_block"] == [["606", "608"]]
    assert [x["pair"] for x in k["other"]] == [["609", "610"]]
    r = c["rules"]
    assert r["n_rule_pairs"] == 5 and r["agree"] == [["604", "605"], ["606", "607"]]
    assert [x["pair"] for x in r["disagree"]] == [["608", "611"]]
    assert r["disagree"][0]["synopsis"]["611"] == {"kind": "pair", "partner": "610"}
    assert r["not_in_synopsis"] == [["609", "609b"], ["610", "610a"]]
    assert c["heads"]["missing"] == ["609b", "610a"]


# --------------------------------------------------------------------------- the command


def _cli():
    spec = importlib.util.spec_from_file_location("roget_generate_cli",
                                                  REPO / "data_analysis" / "gap_generation" / "roget_generate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_synopsis_and_pair_commands(tmp_path, capsys):
    P.save_heads(sample_index(), tmp_path / "heads.json")
    cli = _cli()
    rc = cli.main(["--out", str(tmp_path), "--no-wordnet", "synopsis", "--xml", str(FIXTURE),
                   "--allow-checksum-mismatch"])
    assert rc == 0
    syn = S.load(tmp_path / S.FILE_NAME)
    assert syn["609"]["partner"] == "610"
    rc = cli.main(["--out", str(tmp_path), "--no-wordnet", "pair"])
    assert rc == 0
    pairs = PR.load_pairs(tmp_path / "head_pairs.json")
    assert (pairs["609"].partner, pairs["609"].source) == ("610", "synopsis")
    assert pairs["59a"].source != "synopsis"
    env = json.loads((tmp_path / "head_pairs.json").read_text(encoding="utf-8"))["result"]
    assert env["synopsis"]["n_heads"] == 19
    rc = cli.main(["--out", str(tmp_path), "--no-wordnet", "pair", "--no-synopsis"])
    assert rc == 0 and PR.load_pairs(tmp_path / "head_pairs.json")["609"].source != "synopsis"
    out = capsys.readouterr().out
    assert "synopsis" in out


def test_readme_section_is_replaced_not_repeated(tmp_path):
    cli = _cli()
    xml = tmp_path / S.XML_NAME
    xml.write_bytes(FIXTURE.read_bytes())
    (tmp_path / "README.md").write_text("# Gutenberg part\n\nkept\n", encoding="utf-8")
    cli.refresh_synopsis_readme(xml)
    cli.refresh_synopsis_readme(xml)
    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# Gutenberg part") and "kept" in text
    assert text.count(cli.SYNOPSIS_README_MARK) == 1
    assert S.sha256_of(xml) in text and "NOT_IN_COPYRIGHT" in text and f"{xml.stat().st_size:,} bytes" in text


# --------------------------------------------------------------------------- the real scan

XML = REPO / "data" / "external" / "roget" / S.XML_NAME
HEADS = REPO / "data" / "candidates" / "roget" / "heads.json"


@pytest.mark.skipif(not (XML.exists() and HEADS.exists()), reason="needs the downloaded djvu XML and heads.json")
def test_full_synopsis_invariants():
    idx = P.load_heads(HEADS)
    res = S.read_synopsis(S.synopsis_pages(S.read_pages(XML)), idx)
    rec = res.records()
    assert [p for p in res.page_labels] == ["xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii", "xxviii",
                                            "xxix", "xxx", "xxxi"]
    assert not res.duplicates and set(rec) | set(res.missing) == set(idx.order)
    assert all(rec[x["partner"]]["partner"] == h for h, x in rec.items() if x["partner"])
    assert all(h in x["members"] for h, x in rec.items())
    # the checks against the print (pages xxi-xxxi), read by eye on 2026-10-09
    assert rec["604"]["partner"] == "605" and rec["606"]["partner"] == "607" and rec["604a"]["kind"] == "triad"
    assert rec["609"]["partner"] == "610" and rec["609a"]["kind"] == "triad"
    assert rec["639"]["members"] == ["639", "640", "641"] and rec["640"]["partner"] == "641"
    assert rec["866"]["members"] == ["865", "866", "867"] and rec["865"]["partner"] == "867"
    assert rec["987"]["partner"] == "988" and rec["989"]["kind"] == "triad"
    assert rec["762"]["kind"] == "singleton" and rec["763"]["partner"] == "764"
    assert rec["153"]["partner"] == "154" and rec["155"]["partner"] == "156" and rec["343"]["partner"] == "344"
    assert rec["492"]["partner"] == "493" and rec["838"]["partner"] == "839" and rec["933"]["partner"] == "934"
