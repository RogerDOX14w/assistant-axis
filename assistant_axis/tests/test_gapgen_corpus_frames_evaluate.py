"""Corpus-frames generator: the free measures and the frame measures after the pilot (plan section 8, ``evaluate``)."""
import pytest

from assistant_axis.gapgen.generators.corpus_frames import evaluate as E
from assistant_axis.gapgen.generators.corpus_frames import report as R
from assistant_axis.tests.test_gapgen_corpus_frames_table import H, build


def corpus_table():
    """Planted: three corpus labels (honest, kind, good-natured) of four; frames of different sizes."""
    return build({
        "d_very": [H("good", 4000, 3000, "man"), H("kind", 500, 400, "fellow"), H("honest", 300, 230, "man"),
                   H("good-natured", 200, 150, "man"), H("pedantic", 120, 100, "man")],
        "n_incorrigible": [H("liar", 100, 80), H("flirt", 50, 40)],
        "p_known_for_his": [H("honesty", 120, 100), H("integrity", 90, 70)],
        "cards.copular_list": [H("kind", 9, 8), H("shy", 4, 4)],
    })


LABELS = {"corpus": ["honest", "kind", "good-natured", "kind to animals"], "queue": ["liar"]}


def test_recovery_per_frame_and_union_under_both_orderings_beside_a_baseline():
    t = corpus_table()
    baseline = ["good", "kind", "shy", "honest", "liar"]
    rec = E.recovery_curves(t, LABELS, (1, 3, 5), baselines={"baseline_wordfreq": baseline})
    uv = rec["union_volumes"]["corpus"]
    assert uv["all"]["n"] == 4 and uv["single"]["n"] == 2 and uv["hyphenated"]["n"] == 1 and uv["multiword"]["n"] == 1
    assert uv["multiword"]["found_anywhere"] == 0.0 and uv["hyphenated"]["found_anywhere"] == 1.0
    assert uv["all"]["found_anywhere"] == 0.75
    assert set(rec) >= {"union_volumes", "union_lift", "baseline_wordfreq", "per_frame"}
    bw = rec["baseline_wordfreq"]["corpus"]["all"]
    assert bw["recall@3"] == 0.25 and bw["recall@5"] == 0.5                # kind at 2, honest at 4
    pf = rec["per_frame"]["d_very"]
    assert pf["volumes"]["corpus"]["all"]["recall@3"] == 0.5               # good, kind, honest: kind and honest
    assert pf["lift"]["corpus"]["all"]["n"] == 4
    # a filler folded into a row recovers by the row's position: honesty is found where honest is
    assert rec["union_volumes"]["corpus"]["single"]["found_anywhere"] == 1.0
    q = rec["union_volumes"]["queue"]["all"]
    assert q["n"] == 1 and q["found_anywhere"] == 1.0


def test_ordering_choice_takes_the_higher_union_recall_at_1000_and_ties_to_volumes():
    def rec(v, lift):
        return {"union_volumes": {"corpus": {"all": {"recall@1000": v}}},
                "union_lift": {"corpus": {"all": {"recall@1000": lift}}}}
    assert E.ordering_choice(rec(0.3, 0.4))[0] == "lift"
    assert E.ordering_choice(rec(0.4, 0.3))[0] == "volumes"
    o, why = E.ordering_choice(rec(0.3, 0.3))
    assert o == "volumes" and "tie" in why


def test_unfound_labels_by_region():
    t = corpus_table()
    un = E.unfound_labels(t, LABELS["corpus"] + ["ends justify means"],
                          regions={"kind_to_animals": "moral_stance", "ends_justify_means": "moral_stance"})
    assert un["n"] == 2 and un["by_region"] == {"moral_stance": ["ends justify means", "kind to animals"]}
    assert un["by_class"] == {"multiword": 2} and un["stems"] == ["ends_justify_means", "kind_to_animals"]


def test_registry_overlap_at_depth():
    t = corpus_table()
    top = [r["stem"] for r in sorted(t, key=lambda r: r["union_rank"]) if r["eligible"]]
    ov = E.registry_overlap(t, top[:2], depths=(2, 4))
    assert ov["top_2"] == 1.0 and ov["top_4"] == 0.5 and ov["proxy"]["top_500"] == 0.8


def _registry(t, verdicts):
    """A fixture registry: ``{stem: (verdict, region, tags, decision)}``."""
    out = {}
    for st, (v, region, tags, dec) in verdicts.items():
        row = {"stem": st, "key": f"{st}#1", "sense_id": 1, "sources": [{"generator": "corpus_frames"}],
               "filter": {"verdict": v, "region": region, "tags": list(tags)}}
        if dec:
            row["novelty"] = {"decision": dec, "listed": [{"stem": "honest", "cosine": 0.3}]}
        out[f"{st}#1"] = row
    return out


def test_frame_measures_hand_computed():
    t = corpus_table()
    sel = {"d_very": ["good", "kind", "honest", "pedantic"], "n_incorrigible": ["liar", "flirt"],
           "p_known_for_his": ["honest", "integrity"]}
    reg = _registry(t, {
        "good": ("trait", "moral_stance", [], "covered"), "kind": ("trait", "social_interpersonal", [], "covered"),
        "honest": ("trait", "moral_stance", [], "covered"), "pedantic": ("trait", "cognitive_epistemic", [], "new"),
        "liar": ("trait", "moral_stance", [], "new"), "flirt": ("reject", None, ["physical"], None),
        "integrity": ("trait", "moral_stance", [], "grey")})
    m = E.frame_measures(t, reg, selection=sel)
    d, n, p = m["d_very"], m["n_incorrigible"], m["p_known_for_his"]
    assert (d["n"], d["n_filtered"], d["n_trait"], d["yield"]) == (4, 4, 4, 1.0)
    assert (n["yield"], n["physical_state_share"]) == (0.5, 0.5)               # the planted physical tag
    # union trait regions: moral 4 (good, honest, liar, integrity), social 1, cognitive 1 (of 6 distinct)
    u = m["_union"]
    assert u["regions"] == {"cognitive_epistemic": 1, "moral_stance": 4, "social_interpersonal": 1}
    # d_very: moral 2/4, social 1/4, cognitive 1/4 against 4/6, 1/6, 1/6: tv = 0.5 * (1/6 + 1/12 + 1/12)
    assert d["region_tv"] == pytest.approx(round(0.5 * (abs(2 / 4 - 4 / 6) + 2 * abs(1 / 4 - 1 / 6)), 4))
    assert n["region_tv"] == pytest.approx(round(0.5 * (abs(1 - 4 / 6) + 2 / 6), 4))
    # forms: liar and integrity nouns (the helper finds no adjective for either), the rest adjectives
    assert u["forms"] == {"adjective": 4, "noun": 2} and n["form_tv"] == pytest.approx(round(4 / 6, 4))
    assert p["forms"] == {"adjective": 1, "noun": 1}
    # unique_kept: a kept row found by one frame only (pedantic: d_very alone; liar: n_incorrigible alone;
    # integrity: p_known_for_his alone); honest was found by two frames
    assert d["unique_kept"] == 1 and n["unique_kept"] == 1 and p["unique_kept"] == 1
    assert d["unique_kept_stems"] == ["pedantic"]
    ty = E.type_measures(t, reg, selection=sel, frame_types={"d_very": "degree", "n_incorrigible": "nominal",
                                                             "p_known_for_his": "possessive"})
    assert ty["nominal"]["only_this_type_kept"] == ["liar"] and ty["degree"]["only_this_type_kept"] == ["pedantic"]


@pytest.mark.parametrize("measure,keep", [
    ({"yield": 0.8, "region_tv": 0.2, "unique_kept": 0}, True),
    ({"yield": 0.4, "region_tv": 0.5, "unique_kept": 0}, True),               # at the thresholds
    ({"yield": 0.39, "region_tv": 0.1, "unique_kept": 0}, False),             # low yield, nothing unique
    ({"yield": 0.2, "region_tv": 0.1, "unique_kept": 1}, True),               # low yield with a unique kept row
    ({"yield": 0.9, "region_tv": 0.7, "unique_kept": 0}, False),              # a strong filter
    ({"yield": 0.9, "region_tv": 0.7, "unique_kept": 2}, True),
    ({"yield": None, "region_tv": None, "unique_kept": 0}, False),
    (None, True),                                                            # before the pilot
])
def test_keep_frame_truth_table(measure, keep):
    ok, why = E.keep_frame(measure)
    assert ok is keep and why


def test_frames_kept_honours_rogers_hand_choices():
    ms = {"a": {"yield": 0.9, "region_tv": 0.1, "unique_kept": 0}, "b": {"yield": 0.1, "region_tv": 0.1,
                                                                          "unique_kept": 0}}
    kept, v = E.frames_kept(ms, ["a", "b"], keep=["b"], drop=["a"])
    assert kept == ["b"] and v["a"][1].startswith("dropped by hand") and v["b"][1].startswith("kept by hand")


def test_contributing_frames_names_every_frame_of_a_row():
    t = corpus_table()
    cf = R.contributing_frames(t)
    assert cf["honest"] == ["p_known_for_his", "d_very"]       # rank 1 in the possessive frame, 3 in d_very
    assert cf["kind"] == ["cards.copular_list", "d_very"] and cf["liar"] == ["n_incorrigible"]


def test_build_evaluation_payload():
    t = corpus_table()
    ev = E.build_evaluation(t, label_sets=LABELS, frame_keys=sorted({k for r in t for k in r["frames"]}),
                            table_sha256="ab", bank_sha256="cd", registered_stems=["good"],
                            regions={"kind_to_animals": "moral_stance"}, cutoffs=(1, 3, 1000))
    assert ev["ordering"] in E.ORDERINGS and ev["ordering_rule"]["given"] == "auto"
    assert {"union_volumes", "union_lift", "baseline_table_zipf", "per_frame"} <= set(ev["recovery"])
    assert ev["unfound_labels"]["n"] == 1 and ev["frames_kept"] == sorted({k for r in t for k in r["frames"]})
    assert ev["frame_measures"] is None and ev["table_sha256"] == "ab"
    with pytest.raises(ValueError):
        E.build_evaluation(t, label_sets=LABELS, frame_keys=[], table_sha256=None, bank_sha256="", ordering="max")


def test_the_curves_png(tmp_path):
    from PIL import Image
    t = corpus_table()
    ev = E.build_evaluation(t, label_sets=LABELS, frame_keys=["d_very"], table_sha256="ab", bank_sha256="cd",
                            baselines={"baseline_wordfreq": ["good", "kind", "honest"]}, title="fixture")
    p = E.plot_recovery_curves(ev, tmp_path / "recovery_curves.png")
    info = Image.open(p).info
    assert info.get("Title", "").startswith("Corpus-frames generator") and "Software" in info
