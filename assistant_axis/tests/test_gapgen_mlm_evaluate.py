"""Masked-LM generator, task 8: recovery curves, the wordfreq baseline, the frame ablation, the HHH probe, the
contrast AUC, the evaluation payload, its plot and the readouts (plan section 8, ``evaluate``)."""
import json

import pytest

from assistant_axis.gapgen.generators.masked_lm import evaluate as E
from assistant_axis.gapgen.generators.masked_lm import report as R
from assistant_axis.gapgen.generators.masked_lm.pll import Contrast
from assistant_axis.gapgen.paths import DATA_DIR
from assistant_axis.tests.censuses_fakes import make_corpus
from assistant_axis.tests.test_gapgen_mlm_table import build, passes


def table(stems):
    return [{"stem": s, "union_rank": i} for i, s in enumerate(stems, 1)]


CLASSES = {"kind": "single", "sycophantic": "subword", "risk-averse": "multiword", "kind to animals": "multiword",
           "zorbish": "single"}


def test_recovery_per_class_on_planted_labels():
    t = table(["kind", "cruel", "sycophantic", "risk_averse", "shy"])
    rec = E.recovery_curves(t, {"corpus": ["kind", "sycophantic", "risk-averse", "kind to animals"]}, (1, 3, 4),
                            classes=CLASSES)["corpus"]["union"]
    assert rec["single"]["recall@1"] == 1.0 and rec["single"]["n"] == 1
    assert rec["subword"]["recall@1"] == 0.0 and rec["subword"]["recall@3"] == 1.0
    assert rec["multiword"]["recall@3"] == 0.0 and rec["multiword"]["recall@4"] == 0.5
    assert rec["all"]["recall@4"] == 0.75 and rec["all"]["found_anywhere"] == 0.75


def test_wordfreq_baseline_beats_and_loses_correctly():
    universe = ["kind", "cruel", "zorbish", "sycophantic", "the"]
    zipf = {"the": 7.0, "kind": 5.0, "cruel": 4.0, "sycophantic": 2.0, "zorbish": 1.0}.get
    labels = {"corpus": ["kind", "zorbish"]}
    model = table(["zorbish", "kind"])                 # the frames put the rare trait first
    base = E.frequency_baseline(labels, (1, 2, 5), universe=universe, zipf=zipf, classes=CLASSES)
    b = base["corpus"]["baseline_wordfreq"]["all"]
    assert b["recall@1"] == 0.0 and b["recall@2"] == 0.5 and b["recall@5"] == 1.0
    m = E.recovery_curves(model, labels, (1, 2, 5), classes=CLASSES)["corpus"]["union"]["all"]
    assert m["recall@2"] > b["recall@2"]               # the frames beat frequency here
    common = E.recovery_curves(table(["cruel", "zorbish", "x", "kind"]), {"corpus": ["kind"]}, (2,),
                               rankings={"baseline_wordfreq": E.frequency_ranking(universe, zipf)})["corpus"]
    assert common["baseline_wordfreq"]["all"]["recall@2"] > common["union"]["all"]["recall@2"]   # and lose here


def test_frame_ablation_finds_the_factor_that_carried_a_label():
    aggs = {"kind": {"word": "kind", "by_subject_best": {"she": -1.0, "he": -9.0}},
            "cruel": {"word": "cruel", "by_subject_best": {"she": -2.0, "he": -2.5}},
            "shy": {"word": "shy", "by_subject_best": {"she": -3.0, "he": -1.5}}}
    ab = E.frame_ablation(aggs, "subject", labels=["kind"], cutoffs=(1,))
    assert ab["_all"]["recall@1"] == 1.0
    assert ab["she"]["recall@1"] == 0.0 and ab["she"]["delta"]["recall@1"] == -1.0
    assert ab["he"]["delta"]["recall@1"] == 0.0


def _meta(pass_name, frames):
    return {"pass": pass_name, "frames": {fid: {"family": fam, "kind": "probe", "register": "assistant",
                                                "labels": {k: {"rank": v, "via": "vocab"} for k, v in ranks.items()}}
                                          for fid, (fam, ranks) in frames.items()}}


def test_hhh_probe_finds_the_planted_family_and_frame():
    probe = E.hhh_probe([_meta("probe", {
        "a1": ("assistant_should", {"helpful": 5, "harmless": 300, "honest": 10}),
        "a2": ("assistant_should", {"helpful": 50, "harmless": 150, "honest": 400}),
        "c1": ("principles", {"helpful": 1, "harmless": 2, "honest": 3, "sycophantic": 900}),
        "d1": ("criticism", {"helpful": 900, "harmless": 1000, "honest": 5})})])
    assert probe["winning_families"] == ["assistant_should", "principles"]
    assert probe["winning_frames"] == ["c1"]
    assert probe["ranks"]["helpful"] == 1 and probe["best_frame"]["honest"] == "c1"
    assert probe["families"]["assistant_should"]["best_ranks"] == {"helpful": 5, "harmless": 150, "honest": 10}
    assert set(probe["ranks"]) == set(E.PROBE_LABELS) and probe["ranks"]["obedient"] is None


def test_contrast_auc():
    con = {w: Contrast(v, False, False, 0.0, 0.0, 0.0) for w, v in
           (("kind", 3.0), ("cruel", 2.0), ("tired", -1.0), ("tall", -2.0), ("odd", 2.0))}
    assert E.contrast_auc(con, ["kind", "cruel"], ["tired", "tall"])["auc"] == 1.0
    assert E.contrast_auc(con, ["tired", "tall"], ["kind", "cruel"])["auc"] == 0.0
    tie = E.contrast_auc(con, ["cruel"], ["odd"])
    assert tie["auc"] == 0.5 and not tie["meets_target"]
    miss = E.contrast_auc(con, ["kind", "zorbish"], ["tired"])
    assert miss["missing"] == ["zorbish"] and miss["n_pos"] == 1
    assert E.contrast_auc({}, ["kind"], ["tired"])["auc"] is None


def test_contrast_negatives_are_not_our_labels():
    assert len(E.CONTRAST_STATES) == 50 and len(E.CONTRAST_PHYSICAL) == 50 and len(set(E.CONTRAST_NEGATIVES)) == 100
    ours = set(E.corpus_labels(DATA_DIR)) | set(E.queue_labels(DATA_DIR / "seed_queue.json"))
    assert not [w for w in E.CONTRAST_NEGATIVES if w in ours]
    pos = E.contrast_positives(["kind", "cruel", "tall", "risk-averse", "tired"], exclude=["tall"])
    assert pos == ["cruel", "kind"]


def test_corpus_and_queue_labels(tmp_path):
    data = make_corpus(tmp_path, traits=("kind", "risk_averse"), queue=("flustered",))
    (data / "traits" / "instructions" / "openness_big_five.json").write_text(
        json.dumps({"positive_label": "openness (Big Five)"}))
    assert E.corpus_labels(data) == ["kind", "openness", "risk averse"]
    assert E.queue_labels(data / "seed_queue.json") == ["flustered"]
    assert E.bare_label("careless (HEXACO)") == "careless"


def test_build_evaluation_payload_plot_and_readouts(tmp_path):
    rows = build(contrasts={"roberta": {"kind": Contrast(2.0, False, False, 0, 0, 0),
                                        "tired": Contrast(-2.0, True, False, 0, 0, 0)}})
    ps = passes()
    ps["probe:roberta"] = type(ps["single:roberta"])("probe", "roberta", {}, _meta("probe", {
        "probe_should_be": ("assistant_should", {"helpful": 3, "harmless": 30, "honest": 7})}) | {
        "model_key": "roberta", "seconds": 2.0, "n_forward": 40})
    ev = E.build_evaluation(table=rows, passes=ps, label_sets={"corpus": ["kind", "cruel", "risk-averse", "zorbish",
                                                                          "kind to animals"],
                                                               "queue": ["plain"]},
                            classes=None, cutoffs=(1, 5, 20), universe=["kind", "cruel", "risk-averse", "plain"],
                            zipf=lambda w: 3.0, contrasts={"kind": Contrast(2.0, False, False, 0, 0, 0),
                                                           "tired": Contrast(-2.0, True, False, 0, 0, 0)},
                            corpus_for_auc=["kind"], census={"roberta": {}}, title="test")
    for k in ("n_union", "n_eligible", "recovery", "frame_ablation", "hhh_probe", "contrast_auc", "census",
              "coverage", "throughput", "recovery_detail", "multiword_comparison"):
        assert k in ev, k
    assert set(ev["recovery"]) == {"corpus_single", "corpus_multi", "queue", "baseline_wordfreq"}
    assert ev["recovery"]["corpus_single"]["n"] == 3 and ev["recovery"]["corpus_multi"]["n"] == 2
    assert ev["hhh_probe"]["winning_families"] == ["assistant_should"]
    assert ev["contrast_auc"] == 1.0
    assert ev["coverage"]["absent_single"] == ["zorbish"] and ev["coverage"]["absent_multiword"] == ["kind to animals"]
    assert "variant_b:roberta" in ev["multiword_comparison"]
    json.dumps(ev)
    png = E.plot_recovery_curves(ev, tmp_path / "curves.png")
    from PIL import Image
    info = Image.open(png).info
    assert "Masked-LM generator" in info.get("Title", "")
    doc = tmp_path / "readout.md"
    md = R.render_report(ev, doc_path=doc, files={"curves": png})
    assert "## Recovery against the wordfreq baseline" in md and "[curves.png](curves.png)" in md
    assert "glossary.md#masked-lm" in md and "## What Variant B's universe lacks" in md
    probe = R.render_hhh_probe(ev, doc_path=DATA_DIR / "candidates" / "masked_lm" / "hhh_probe.md")
    assert "[helpful](../../traits/instructions/helpful.json)" in probe
    assert "| `probe_should_be` | assistant_should |" in probe and "**3**" in probe
    sample = R.roger_sample(rows, n=3, seed=1)
    assert sample.count("\n| ") == 4 and "T/P" in sample


def test_roger_sample_shows_m1_gloss_and_marks_second():
    """2026-10-15: the spot check shows M1's gloss (what the pipeline uses) beside the dictionary hint, and the mark
    column comes second, never last after an empty column."""
    from assistant_axis.gapgen.generators.masked_lm import report as R
    rows = [{"surface": "outgoing", "stem": "outgoing", "union_rank": 3, "best_frame": "f", "zipf": 4.1,
             "trait_contrast": 0.5, "gloss_hint": "leaving a place or a position"}]
    md = R.roger_sample(rows, n=1, m1_glosses={"outgoing": "This means approaching people with easy warmth."})
    assert "| # | word | T/P | M1's gloss | dictionary hint |" in md
    assert "| 1 | outgoing |  | This means approaching people with easy warmth. | leaving a place or a position |" in md
