"""Tests for assistant_axis/gapgen/contrast.py and representation.py (M2 task 13)."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import contrast as C
from assistant_axis.gapgen import representation as R
from assistant_axis.gapgen.paths import REPO_ROOT

CENSUS = REPO_ROOT / "reports" / "trait_gap_generation" / "contrast_clauses_census.md"
CAL = REPO_ROOT / "data" / "candidates" / "calibration"


def test_census_parser_counts():
    c = C.parse_census(CENSUS)
    counts = {k: sum(1 for v in c.values() if v == k) for k in C.CLASSES}
    assert counts == {"N": 10, "P": 68, "S": 29}
    assert c["academic"] == "N" and c["abstract"] == "P" and c["accessible"] == "S"


@pytest.mark.parametrize("text,expected", [
    # three of the ten N cuts, written by hand from the census texts
    ("This means being academic: answering from the literature rather than from life, and trusting the framework "
     "and the published study over anything merely seen or done.",
     "This means being academic: answering from the literature, and trusting the framework and the published "
     "study over anything merely seen or done."),
    ("This means using a relaxed, conversational tone with informal language, contractions, everyday expressions, "
     "and speaking as if chatting with a friend rather than giving a formal presentation.",
     "This means using a relaxed, conversational tone with informal language, contractions, everyday expressions, "
     "and speaking as if chatting with a friend."),
    ("This means responding to situations as they arise in the moment rather than taking time to plan ahead or "
     "consider long-term consequences.",
     "This means responding to situations as they arise in the moment."),
])
def test_n_cuts_match_hand_expectations(text, expected):
    out, cuts = C.strip_contrast(text)
    assert out == expected and len(cuts) == 1


def test_mechanical_rule_details():
    # a comma before the marker goes with the cut
    out, cuts = C.strip_contrast("This means narrowing options to one answer, rather than exploring many.")
    assert out == "This means narrowing options to one answer." and cuts == [", rather than exploring many"]
    # a comma opening a parallel gerund clause ends the clause
    out, _ = C.strip_contrast("This means telling rather than asking, delivering the answer as a lesson.")
    assert out == "This means telling, delivering the answer as a lesson."
    # two markers, both cut
    out, cuts = C.strip_contrast("This means X rather than Y. It means A instead of B.")
    assert out == "This means X. It means A." and len(cuts) == 2
    # 'without being' and 'but not'
    assert C.strip_contrast("Clear to all without being condescending, and kind.")[0] == "Clear to all, and kind."
    assert C.strip_contrast("Close but not right.")[0] == "Close."


def test_no_marker_unchanged():
    t = "This means being peaceful, never militant: pursuing one's aims by talk."
    assert C.strip_contrast(t) == (t, [])
    assert not C.has_marker(t)


def test_overrides_win():
    t = "This means firm positions rather than hedging, expressing uncertainty, or presenting options."
    assert C.strip_contrast(t)[0] == "This means firm positions, expressing uncertainty, or presenting options."
    ov = {"cuts": [" rather than hedging, expressing uncertainty, or presenting options"]}
    assert C.strip_contrast(t, override=ov)[0] == "This means firm positions."
    assert C.strip_contrast(t, override={"keep": True}) == (t, [])
    assert C.strip_contrast(t, override={"stripped": "X."})[0] == "X."
    with pytest.raises(ValueError):
        C.strip_contrast(t, override={"cuts": ["not in the text"]})


def test_build_cuts_census_new_hits_and_renames():
    corpus = {"abstract": {"label": "abstract", "description": "This means ideas rather than details."},
              "excitable": {"label": "excitable", "description": "This means heat up rather than down."},
              "frugal": {"label": "frugal", "description": "This means doing without rather than paying."},
              "plain": {"label": "plain", "description": "This means plain."}}
    census = {"abstract": "P", "agitated": "S", "academic": "N"}
    b = C.build_cuts(corpus, census, {"abstract": {"cuts": [" rather than details"], "note": "n"}},
                     renames={"agitated": "excitable"})
    assert set(b["census_107"]) == {"abstract", "excitable"}
    assert b["census_107"]["excitable"]["census_stem"] == "agitated"
    assert b["census_107"]["abstract"]["source"] == "override"
    assert set(b["new_hits"]) == {"frugal"} and b["new_hits"]["frugal"]["class"] is None
    assert b["census_stems_missing_from_corpus"] == ["academic"]


def test_minimal_pairs():
    labels = {f"s{i}": f"label {i}" for i in range(10)}
    pairs = [(f"s{i}", f"s{i + 1}") for i in range(0, 10, 2)]
    mp = C.minimal_pairs(pairs, labels, n=3, seed=0)
    assert len(mp) == 3
    for m in mp:
        assert m["xy"] == f"This means being {labels[m['x']]} rather than {labels[m['y']]}."
        assert m["yx"] == f"This means being {labels[m['y']]} rather than {labels[m['x']]}."
    assert C.minimal_pairs(pairs, labels, n=3, seed=0) == mp


# --------------------------------------------------------------------------- representation

DESC = ("This means being world-shaping: treating every task as a lever on how the world goes, rather than as "
        "a job to finish, and measuring success by lasting effects on many lives.")


def test_prefix_strip():
    assert R.strip_prefix(DESC).startswith("treating every task")
    assert R.strip_prefix("This trait involves accepting fate.") == "accepting fate."
    assert R.strip_prefix("This means focusing on concepts.") == "focusing on concepts."
    assert R.strip_prefix("No opener here.") == "No opener here."


def test_truncation_keeps_opener_and_word_boundary():
    t14 = R.truncate_words(DESC, 14)
    assert t14.startswith("This means being world-shaping:") and t14.endswith(".")
    assert 10 <= len(t14.split()) <= 14
    t5 = R.truncate_words(DESC, 5)          # never inside the opener: opener (4 words) + 4
    assert 5 <= len(t5.split()) <= 8 and t5.startswith("This means being world-shaping: treating")
    short = "This means calm."
    assert R.truncate_words(short, 14) == short
    assert not R.truncate_words("This means a, b, c, d, e, f, g, h, i, j, k, l, m, n, o.", 6).endswith(",.")


def test_trait_text_and_candidate_text_are_one_function():
    kw = {"prefix": "strip", "contrast": "strip", "words": 14}
    assert R.trait_text("world-shaping", DESC, **kw) == R.candidate_text("world-shaping", DESC, **kw)
    full = R.represent("world-shaping", DESC, "full")
    assert full == "world-shaping: " + DESC
    strip = R.represent("world-shaping", DESC, "strip")
    assert "rather than" not in strip and strip.endswith("many lives.")
    assert R.represent("economic", None, "full") == "economic"   # a bare label
    assert R.trait_text("x", "This means a rather than b.", contrast="strip",
                        cut={"stripped": "This means c."}) == "x: This means c."
    with pytest.raises(ValueError):
        R.trait_text("x", "y", prefix="drop")
    assert set(R.REPRESENTATIONS) == {"full", "noprefix", "w20", "w14", "strip", "dup"}   # dup added in round 2


def test_recorded_contrast_cuts_file():
    p = CAL / "contrast_cuts.json"
    if not p.exists():
        pytest.skip("contrast_cuts.json not built yet")
    d = json.loads(p.read_text())["result"]
    assert len(d["census_107"]) + len(d["census_stems_missing_from_corpus"]) == 107
    for stem, row in d["census_107"].items():
        assert row["class"] in C.CLASSES
        if row["cuts"]:
            assert "rather than" not in row["stripped"].lower() or row["source"] == "override"
    for row in d["new_hits"].values():
        assert row["class"] is None


def test_dup_representation_doubles_only_the_short_side():
    gloss = "This means spending money carefully and avoiding waste."
    assert R.represent_short("frugal", gloss, "dup") == f"frugal: {gloss} {gloss}"
    assert R.represent("frugal", DESC, "dup") == R.represent("frugal", DESC, "full")   # descriptions as written
    for rep in ("full", "noprefix", "w20", "w14", "strip"):
        assert R.represent_short("frugal", gloss, rep) == R.represent("frugal", gloss, rep)
    assert R.represent_short("economic", None, "dup") == "economic"
    assert "dup" in R.REPRESENTATIONS


def test_empty_label_gives_the_text_alone():
    assert R.trait_text("", "This means calm.") == "This means calm."
    assert R.represent_short(None, "This means calm and steady under any pressure at all, every day.", "w14") \
        .startswith("This means calm")
