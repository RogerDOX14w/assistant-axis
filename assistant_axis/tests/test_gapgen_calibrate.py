"""Tests for assistant_axis/gapgen/calibrate.py and calibrate_llm.py (M2 tasks 16-17),
on synthetic embeddings with planted duplicates, antonyms and hubs, and a fake
Anthropic client.  No model, no API."""
import asyncio
import json
import logging

import numpy as np
import pytest

from assistant_axis.gapgen import calibrate as C
from assistant_axis.gapgen import calibrate_llm as CL
from assistant_axis.gapgen.labels import LabelledPair, LabelledPairs
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text

D = 24


def _unit(x):
    return x / np.linalg.norm(x, axis=-1, keepdims=True)


@pytest.fixture
def synth():
    """40 corpus traits: 0-9 random; dup pairs (10,11), (12,13), (14,15) almost equal; near-distinct
    pairs (16,17), (18,19), (20,21) moderately close; antonym pairs (22,23), (24,25), (26,27) share a
    topic component with opposite signs on a polarity component; 28-39 random."""
    rng = np.random.default_rng(0)
    E = rng.standard_normal((40, D))
    for a, b in ((10, 11), (12, 13), (14, 15)):
        E[b] = E[a] + 0.05 * rng.standard_normal(D)
    for a, b in ((16, 17), (18, 19), (20, 21)):
        E[b] = E[a] + 0.9 * rng.standard_normal(D)
    for a, b in ((22, 23), (24, 25), (26, 27)):
        topic, pol = rng.standard_normal(D), rng.standard_normal(D)
        E[a], E[b] = topic + 0.9 * pol, topic - 0.9 * pol
    E = _unit(E + 2.0)          # a shared offset, like a raw embedding model
    stems = [f"t{i}" for i in range(40)]
    index = {s: i for i, s in enumerate(stems)}
    P = LabelledPair
    pairs = ([P(f"t{a}", f"t{b}", "duplicate", "x") for a, b in ((10, 11), (12, 13), (14, 15))]
             + [P(f"t{a}", f"t{b}", "near_distinct", "x") for a, b in ((16, 17), (18, 19), (20, 21))]
             + [P(f"t{a}", f"t{b}", "antonym", "x") for a, b in ((22, 23), (24, 25), (26, 27))]
             + [P(f"t{a}", f"t{b}", "unrelated", "random") for a, b in ((0, 1), (2, 3), (4, 5), (6, 7))])
    lp = LabelledPairs(pairs=pairs, externals={})
    return E, stems, index, lp


def test_auc_basics():
    assert C.auc([3, 4], [1, 2]) == 1.0
    assert C.auc([1, 2], [3, 4]) == 0.0
    assert C.auc([1, 2], [1, 2]) == 0.5
    assert C.auc([], [1]) is None


@pytest.mark.parametrize("variant", ["raw", "centred", "centred_pc1", "zca"])
def test_planted_duplicates_and_antonyms_separate(synth, variant):
    E, stems, index, lp = synth
    v = C.build_view(E, variant)
    t = C.labelled_tasks(v, lp, index, {})
    m = t["metrics"]["cos"]
    assert m["auc_dup_vs_distinct"] == 1.0
    assert m["auc_ant_vs_syn"] == 1.0           # the planted antonyms sit below the duplicates
    assert m["n_dup"] == 3 and m["n_distinct"] == 3 and m["n_ant"] == 3
    # nearest neighbour of a duplicate is its twin
    assert v.nn_cos_idx[10] == 11 and v.nn_cos_idx[11] == 10


def test_residual_only_for_centred_variants(synth):
    E, *_ = synth
    assert C.build_view(E, "raw").residual == {}
    v = C.build_view(E, "centred", residual_ks=(5, 10))
    assert set(v.residual) >= {5, 10, v.K95}
    r = v.novelty("resid_5")
    assert r.shape == (40,) and np.all((r >= 0) & (r <= 1))
    assert np.allclose(v.novelty("resid_K95"), v.residual[v.K95])


def test_external_members_and_csls(synth):
    E, stems, index, lp = synth
    v = C.build_view(E, "centred")
    ext = {"queue:x": E[10] + 0.01}
    cos, cs = C.pair_similarities(v, [("queue:x", "t10"), ("queue:x", "t0")], index, ext)
    assert cos[0] > 0.99 and cos[0] > cos[1] and cs[0] > cs[1]
    with pytest.raises(KeyError):
        C.pair_similarities(v, [("queue:y", "t0")], index, ext)


def test_place_thresholds_by_construction():
    rng = np.random.default_rng(3)
    dup = rng.uniform(0.6, 0.9, 200)
    unr = rng.uniform(0.0, 0.4, 1000)
    nn = np.concatenate([rng.uniform(0.3, 0.5, 300), [0.95, 0.92]])
    t = C.place_thresholds(nn, dup, unr, dup_folds=[i % 5 for i in range(200)])
    assert t["recall_at_t_hi"] >= 0.95 and t["recall_at_t_hi"] < 0.96
    assert t["unrelated_below_t_lo"] >= 0.99
    assert t["t_lo"] < t["t_hi"]
    assert t["n_low_tail"] >= 2 and t["bulk"]["median"] < t["t_hi"]
    assert len(t["heldout_recall_by_fold"]) == 5 and 0.85 < t["heldout_recall_mean"] <= 1.0


def test_hubness_census(synth):
    E, stems, index, lp = synth
    v = C.build_view(E, "raw")
    h = C.hubness(v, stems, k=5, top=3)
    for metric in ("cos", "csls"):
        assert len(h[metric]["top"]) == 3
        assert h[metric]["max_Nk"] >= h[metric]["top"][-1]["Nk"]
    # the k-occurrence counts sum to n*k
    nnk = np.argsort(-v.S, axis=1)[:, :5]
    assert np.bincount(nnk.ravel(), minlength=40).sum() == 200


def test_hub_demoted_by_csls():
    rng = np.random.default_rng(5)
    base = _unit(rng.standard_normal((30, 200)))
    hub = base.sum(axis=0)                                            # the centroid: close to everyone
    E = _unit(np.vstack([base, hub]))
    v = C.build_view(E, "raw")
    h = C.hubness(v, [f"s{i}" for i in range(31)], k=3)
    assert h["cos"]["top"][0]["stem"] == "s30"
    assert h["csls"]["top"][0]["Nk"] <= h["cos"]["top"][0]["Nk"]


def test_drop_or_merge_flags_recorded_pair(synth):
    E, stems, index, lp = synth
    views = {"raw": C.build_view(E, "raw"), "centred": C.build_view(E, "centred")}
    link = C.arrangement_linker({"t10": [("pair", ("t10", "t11"))], "t11": [("pair", ("t10", "t11"))]})
    rows = C.drop_or_merge_rows(views, stems, primary="centred", metric="cos", t_hi=0.95, arrangement_link=link,
                                deliberate={("t12", "t13")})
    by = {tuple(sorted((r["trait"], r["nearest"]))): r for r in rows}
    assert by[("t10", "t11")]["arrangement"] == "pair"
    assert by[("t12", "t13")]["deliberate_duplicate"] and by[("t12", "t13")]["arrangement"] is None
    assert set(rows[0]["sim"]) == {"raw", "centred"}
    assert len(by) == len(rows)          # each pair once


def test_gloss_recovery(synth):
    E, stems, index, lp = synth
    v = C.build_view(E, "centred")
    rng = np.random.default_rng(1)
    q = {s: E[i] + 0.02 * rng.standard_normal(D) for i, s in enumerate(stems[:10])}
    g = C.gloss_recovery(v, q, index)
    assert g["n"] == 10 and g["cos"]["recall_at_1"] == 1.0 and g["csls"]["recall_at_5"] == 1.0


def test_persona_task_and_spearman(synth):
    E, stems, index, lp = synth
    v = C.build_view(E, "centred", residual_ks=(5,))
    nov = v.novelty("cos")
    yields = {s: float(nov[i]) for i, s in enumerate(stems)}
    rho, p, n = C.persona_task(v, stems, yields, "cos")
    assert rho == pytest.approx(1.0) and n == 40
    assert C.spearman([1, 2], [1, 2])[0] is None


def _contrast_setup(synth):
    E, stems, index, lp = synth
    rng = np.random.default_rng(2)
    E2 = E.copy()
    # "stripping" t22's clause: it moves away from its antonym t23 (the clause carried t23's words)
    E2[22] = _unit(E[22] + 0.5 * (E[22] - E[23]))
    E2[16] = _unit(E[16] + 0.002 * rng.standard_normal(D))
    classes = {"t22": "P", "t16": "N"}
    full, strip = C.build_view(E, "centred", residual=False), C.build_view(E2, "centred", residual=False)
    return E, E2, stems, index, lp, classes, full, strip


def test_contrast_ablation_local_criteria(synth):
    E, E2, stems, index, lp, classes, full, strip = _contrast_setup(synth)
    minimal = [{"x": "t22", "y": "t23", "xy": "xy", "yx": "yx", "x_only": "xo", "y_only": "yo"}]
    # a bag-of-words model: both orders give the same vector
    bow = {"xy": E[22] + E[23], "yx": E[22] + E[23], "xo": E[22], "yo": E[23]}
    pers = {"stems": stems, "M": E - E.mean(axis=0)}
    res = C.contrast_ablation(full, strip, stems=stems, index=index, classes=classes, partner={"t22": "t23"}, lp=lp,
                              ext_full={}, ext_strip={}, minimal=minimal, minimal_vecs=bow, persona=pers)
    a = res["a_movement"]
    assert a["P"]["n"] == 1 and a["P"]["mean_delta_cos_to_partner"] < 0       # moved away from the named pole
    assert a["P"]["frac_moved_away_from_partner"] == 1.0
    assert a["N"]["mean_cos_full_vs_strip"] > 0.99
    assert res["c_nn_change"]["N"]["n"] == 1
    d = res["d_antonym_margin"]
    assert d["n_antonym"] == 1 and d["mean_delta_antonym"] < 0
    f = res["f_minimal_pairs"]
    assert f["n"] == 1 and f["mean_cos_xy_yx"] == pytest.approx(1.0) and f["accuracy_vs_corpus_poles"] == 0.0
    h = res["h_persona"]
    assert h["full"]["spearman_all_pairs"] > 0.9 and h["n_traits"] == 40
    assert "g_paraphrase_invariance" not in res          # no paraphrases, no (g) / (i)
    res2 = C.contrast_ablation(full, strip, stems=stems, index=index, classes=classes, partner={}, lp=lp,
                               ext_full={}, ext_strip={}, paraphrases={"t22": E[22] + 0.01})
    assert res2["g_paraphrase_invariance"]["n"] == 1
    assert res2["g_paraphrase_invariance"]["frac_clause_moves_more"] == 1.0
    assert res2["i_heldout_recovery"]["full"]["n"] == 1


def test_minimal_pairs_reward_order_sensitivity(synth):
    E, stems, index, lp = synth
    full = C.build_view(E, "raw", residual=False)
    minimal = [{"x": "t22", "y": "t23", "xy": "xy", "yx": "yx", "x_only": "xo", "y_only": "yo"}]
    good = {"xy": E[22] + 0.2 * E[23], "yx": E[23] + 0.2 * E[22], "xo": E[22], "yo": E[23]}
    f = C.minimal_pair_test(full, minimal, good, index)
    assert f["accuracy_vs_corpus_poles"] == 1.0 and f["mean_cos_xy_yx"] < 0.99


def test_recommend_contrast_rule():
    base = {"c_nn_change": {"N": {"n": 10, "n_unchanged": 9}}}
    strip_wins = dict(base, d_antonym_margin={"margin_vs_unrelated": 0.05},
                      f_minimal_pairs={"accuracy_vs_corpus_poles": 0.5},
                      h_persona={"full": {"spearman_all_pairs": 0.20}, "strip": {"spearman_all_pairs": 0.25}})
    assert C.recommend_contrast(strip_wins)["recommendation"] == "strip"
    n_moves = dict(strip_wins, c_nn_change={"N": {"n": 10, "n_unchanged": 5}})
    assert C.recommend_contrast(n_moves)["recommendation"] == "keep"     # the clause carried the sense
    keep = dict(base, f_minimal_pairs={"accuracy_vs_corpus_poles": 0.95}, d_antonym_margin={"margin_vs_unrelated": -0.01})
    r = C.recommend_contrast(keep)
    assert r["recommendation"] == "keep" and r["votes"] == {"d": "keep", "f": "keep"}


def test_blinded_comparisons_sample_and_markdown(synth):
    E, E2, stems, index, lp, classes, full, strip = _contrast_setup(synth)
    classes = dict(classes, t24="S", t26="P", t10="new")
    labels = [s.upper() for s in stems]
    desc = [f"This means {s}." for s in stems]
    items = C.blinded_comparisons(full, strip, stems=stems, labels=labels, descriptions=desc, classes=classes,
                                  n=4, n_for_roger=2, seed=0)
    assert len(items) == 4 and items[0]["class"] == "N"          # the N class first
    assert sum(i["for_roger"] for i in items) == 2
    for it in items:
        assert set(it["key"].values()) == {"full", "strip"} and len(it["A"]) == 5
    md = C.comparisons_markdown(items, labels_of=dict(zip(stems, labels)), desc_of=dict(zip(stems, desc)),
                                link=lambda s, l: f"[{l}](x/{s}.json)")
    assert md.count("Mark (A / B / same)") == 2 and "full" not in md and "strip" not in md


def test_cross_model_agreement(synth):
    E, *_ = synth
    a, b = C.build_view(E, "raw", residual=False), C.build_view(E, "centred", residual=False)
    out = C.cross_model_nn_agreement({"m1": a, "m2": b, "m3": a})
    assert out["m1~m3"] == 1.0 and set(out) == {"m1~m2", "m1~m3", "m2~m3"}


def test_most_and_least_novel(synth):
    E, stems, index, lp = synth
    v = C.build_view(E, "centred", residual=False)
    r = C.most_and_least_novel(v, stems, "cos", n=3)
    assert len(r["most"]) == 3 and r["least"][0]["stem"] in {"t10", "t11", "t12", "t13", "t14", "t15"}


# --------------------------------------------------------------------------- LLM criteria with a fake client

def test_paraphrases_fake_client(caplog):
    items = [{"stem": f"s{i}", "label": f"l{i}", "description": f"This means d{i}."} for i in range(25)]

    def responder(kw):
        rows = [json.loads(x) for x in user_text(kw).splitlines()]
        res = [{"id": r["id"], "reason": "keep the disposition", "paraphrase": f"This means p {r['label']}."}
               for r in rows if r["label"] != "l3"]
        return make_response(json.dumps({"results": res}), input_tokens=900, output_tokens=400)
    client = FakeAsyncAnthropic(responder)
    usage = MultiModelUsage()
    with caplog.at_level(logging.INFO):
        out = asyncio.run(CL.run_paraphrases(client, items, usage=usage, batch_size=20))
    assert len(out) == 24 and "s3" not in out and out["s0"] == "This means p l0."
    assert len(client.calls) == 3          # two batches + one retry for the failed row
    assert "paraphrase" in CL.PARAPHRASE_PROMPT.lower() or "rewrite" in CL.PARAPHRASE_PROMPT.lower()
    assert usage.n_calls == 3 and usage.total_cost_usd > 0
    assert "HIGH FAIL RATE" in caplog.text        # 24 of 25


def test_blinded_judge_reason_first_and_order_swap():
    assert CL.BLINDED_PROMPT.index('"reason"') < CL.BLINDED_PROMPT.index('"preference"')
    items = [{"id": 1, "label": "calm", "description": "This means calm.", "A": ["serene"], "B": ["agitated"],
              "key": {"A": "strip", "B": "full"}},
             {"id": 2, "label": "x", "description": "This means x.", "A": ["y"], "B": ["z"],
              "key": {"A": "full", "B": "strip"}}]

    def responder(kw):
        u = user_text(kw)
        # always prefers the list that contains 'serene' (consistent), for item 2 always says "A" (inconsistent)
        if "calm" in u:
            first = u.split("List B:")[0]
            return make_response(json.dumps({"reason": "r", "preference": "A" if "serene" in first else "B"}))
        return make_response(json.dumps({"reason": "r", "preference": "A"}))
    usage = MultiModelUsage()
    out = asyncio.run(CL.run_blinded(FakeAsyncAnthropic(responder), items, usage=usage,
                                     desc_of={}, label_of={}))
    assert out["verdicts"] == {1: "strip", 2: "inconsistent"}
    assert out["preference_strip_share"] == 1.0 and out["n_calls"] == 4 and usage.n_calls == 4


def test_parsers_reject_bad_rows():
    assert CL.parse_paraphrases('{"results": [{"id": 1, "paraphrase": "no opener"}]}', [1]) == {}
    assert CL.parse_paraphrases("```json\n{\"results\": [{\"id\": 1, \"paraphrase\": \"This means y.\"}]}\n```", [1]) == {
        1: "This means y."}
    assert CL.parse_blinded('{"reason": "r", "preference": "C"}') is None
    assert CL.parse_blinded(None) is None


def test_llm_estimate_is_small():
    est = CL.llm_estimate(659, 60)
    assert 0.2 < est.usd < 3.0


def test_histogram_png_has_metadata(synth, tmp_path):
    from PIL import Image
    E, stems, index, lp = synth
    v = C.build_view(E, "centred", residual=False)
    panels = [{"variant": "centred", "nn": v.nn_cos, "dup": [0.9, 0.95], "distinct": [0.5], "antonym": [0.6],
               "t_hi": 0.9, "t_lo": 0.4, "n_low_tail": 3}] * 2
    out = tmp_path / "h.png"
    C.plot_nn_histograms(out, model="hash", representation="full", panels=panels)
    info = Image.open(out).info
    assert info["Title"].startswith("Leave-one-out nearest-neighbour similarity") and "Creation Time" in info


def test_masked_nn_excludes_partners(synth):
    E, stems, index, lp = synth
    v = C.build_view(E, "raw", residual=False)
    assert v.nn_cos_idx[10] == 11
    idx, sim = C.masked_nn(v, {(10, 11)})
    assert idx[10] != 11 and idx[11] != 10 and sim[10] < v.nn_cos[10]
    rows = C.drop_or_merge_rows({"raw": v}, stems, primary="raw", metric="cos", t_hi=-1.0, nn=(idx, sim))
    assert all({r["trait"], r["nearest"]} != {"t10", "t11"} for r in rows)
    ex = C.most_and_least_novel(v, stems, "cos", n=2, nn=(idx, sim))
    assert len(ex["most"]) == 2


def test_partial_whitening_views_get_the_residual(synth):
    E, *_ = synth
    v = C.build_view(E, "pw2", residual_ks=(5,))
    assert 5 in v.residual and v.K95 is not None


def test_histogram_grid_for_many_variants(synth, tmp_path):
    from PIL import Image
    E, stems, index, lp = synth
    v = C.build_view(E, "centred", residual=False)
    panels = [{"variant": f"v{i}", "nn": v.nn_cos, "dup": [0.9], "distinct": [0.5], "antonym": [0.6],
               "t_hi": 0.9, "t_lo": 0.4} for i in range(12)]
    out = tmp_path / "g.png"
    C.plot_nn_histograms(out, model="hash", representation="full", panels=panels, ncols=4)
    w, h = Image.open(out).size
    assert h > w / 3          # three rows, not one strip


def test_redraw_prefers_changed_first_neighbour_and_keeps_marked_items(synth):
    E, stems, index, lp = synth
    rng = np.random.default_rng(3)
    E2 = E.copy()
    # t22 (N): stripping moves it next to t0 -> first neighbour changes; t24 (P) changes too;
    # t26 (S) and t10 (P) barely move -> same first neighbour
    base = C.build_view(E, "raw", residual=False)
    far = lambda i: [j for j in (0, 1, 2, 3) if j != base.nn_cos_idx[i]][0]  # noqa: E731
    E2[22] = _unit(E[far(22)] + 0.01 * rng.standard_normal(D))
    E2[24] = _unit(E[far(24)] + 0.01 * rng.standard_normal(D))
    E2[26] = _unit(E[26] + 0.001 * rng.standard_normal(D))
    E2[10] = _unit(E[10] + 0.001 * rng.standard_normal(D))
    classes = {"t22": "N", "t24": "P", "t26": "S", "t10": "P"}
    views = {"openai": (C.build_view(E, "raw", residual=False), C.build_view(E2, "raw", residual=False)),
             "bge": (C.build_view(E, "raw", residual=False), C.build_view(E, "raw", residual=False))}
    labels = [s.upper() for s in stems]
    desc = [f"This means {s}." for s in stems]
    first = C.redraw_comparisons(views, stems=stems, labels=labels, descriptions=desc, classes=classes,
                                 n=3, n_for_roger=2)
    by = {it["stem"]: it for it in first}
    assert set(by) >= {"t22", "t24"} and by["t22"]["id"] == 1            # the N class first
    assert by["t22"]["first_neighbour_changes"] and by["t22"]["model"] == "openai"
    assert all(it["first_neighbour_changes"] for it in first if it["for_roger"])
    # t26 and t10 keep their first neighbour and their whole top three: never padded in
    assert len(first) == 2 and not ({"t26", "t10"} & set(by)) and sum(it["for_roger"] for it in first) == 2
    # a marked item that is still selected keeps its number, lists and key
    marked = dict(by["t24"], id=2)
    again = C.redraw_comparisons(views, stems=stems, labels=labels, descriptions=desc, classes=classes,
                                 n=3, n_for_roger=2, keep=[marked])
    kept = [it for it in again if it["stem"] == "t24"][0]
    assert kept["id"] == 2 and kept["A"] == marked["A"] and kept["key"] == marked["key"] and kept["kept_from_draw_1"]


def test_redraw_does_not_keep_a_marked_item_whose_first_neighbour_holds(synth):
    E, stems, index, lp = synth
    rng = np.random.default_rng(4)
    E2 = E.copy()
    base = C.build_view(E, "raw", residual=False)
    far = [j for j in (0, 1, 2, 3) if j != base.nn_cos_idx[22]][0]
    E2[22] = _unit(E[far] + 0.01 * rng.standard_normal(D))
    E2[24] = E[24]
    # t24's top three change but not its first neighbour: swap its 2nd and 3rd by nudging toward the 3rd
    a = base.topk(24, 5)
    E2[24] = _unit(E[24] + 0.3 * (E[a[2]] - E[a[1]]))
    views = {"openai": (base, C.build_view(E2, "raw", residual=False))}
    classes = {"t22": "N", "t24": "P"}
    labels, desc = [s.upper() for s in stems], [f"This means {s}." for s in stems]
    first = {it["stem"]: it for it in C.redraw_comparisons(views, stems=stems, labels=labels, descriptions=desc,
                                                          classes=classes, n=2, n_for_roger=2)}
    if first.get("t24", {}).get("first_neighbour_changes", True):
        pytest.skip("synthetic nudge changed the first neighbour")
    marked = dict(first["t24"], id=1)
    again = C.redraw_comparisons(views, stems=stems, labels=labels, descriptions=desc, classes=classes,
                                 n=2, n_for_roger=2, keep=[marked])
    assert again[0]["stem"] == "t22" and not any(it["kept_from_draw_1"] for it in again)


def test_paraphrase_prompt_v2_reasons_first():
    assert CL.PARAPHRASE_PROMPT_VERSION == 2
    p = CL.PARAPHRASE_PROMPT
    assert p.index('"reason"') < p.index('"paraphrase"')
    assert "first" in p.lower() and "reason" in p.lower()
    # a row without its reason still parses (the reason is a thinking aid, not data)
    assert CL.parse_paraphrases('{"results": [{"id": 1, "paraphrase": "This means x."}]}', [1]) == {1: "This means x."}


def test_covered_threshold_from_paraphrases(synth):
    E, stems, index, lp = synth
    rng = np.random.default_rng(6)
    v = C.build_view(E, "centred", residual=False)
    para = {s: E[i] + 0.03 * rng.standard_normal(D) for i, s in enumerate(stems)}
    folds = {s: i % 3 for i, s in enumerate(stems)}
    t = C.covered_threshold(v, para, index, lp, recall=0.95, folds=folds)
    assert t["n"] == 40 and 0.95 <= t["recall_at_t_hi"] < 0.98
    assert t["t_hi"] > t["t_lo"]
    assert 0 <= t["rate_above_t_hi"]["antonym"] <= 1 and "near_distinct" in t["rate_above_t_hi"]
    assert 0 <= t["hidden_original_still_covered"] <= 1
    assert len(t["heldout_recall_by_fold"]) == 3


def test_heldout_directional_stability(synth):
    E, stems, index, lp = synth
    rng = np.random.default_rng(7)
    v = C.build_view(E, "centred", residual_ks=(3, 5))
    para = {s: E[i] + 0.01 * rng.standard_normal(D) for i, s in enumerate(stems)}
    h = C.heldout_directional(v, para, index, [3, 5])
    assert h["n"] == 40 and h["by_K"]["3"]["spearman_para_vs_original"] > 0.9
    assert h["by_K"]["5"]["mean_abs_diff"] < 0.1


def test_heldout_directional_from_the_view_pass_matches_standalone(synth):
    E, stems, index, lp = synth
    rng = np.random.default_rng(8)
    Qraw = E + 0.01 * rng.standard_normal(E.shape)
    para = {s: Qraw[i] for i, s in enumerate(stems)}
    v1 = C.build_view(E, "pw2", residual_ks=(3,), queries=Qraw)
    v2 = C.build_view(E, "pw2", residual_ks=(3,))
    a = C.heldout_directional(v1, None, index, [3])
    b = C.heldout_directional(v2, para, index, [3])
    assert a["by_K"]["3"] == b["by_K"]["3"]


def _fake_rows():
    rows, para, held = [], [], []
    for m in ("openai", "gemma"):
        for rep, a, c in (("full", 0.60, 0.25), ("w14", 0.70, 0.22)):
            for var in ("centred", "pw2"):
                bump = 0.02 if var == "pw2" else 0.0
                rows.append({"model": m, "representation": rep, "variant": var, "metric": "cos",
                             "auc_dup_vs_distinct": a + bump, "auc_ant_vs_syn": 0.4})
                for K, cc in ((10, c + 0.03), (20, c), (40, c + 0.01)):
                    rows.append({"model": m, "representation": rep, "variant": var, "metric": f"resid_{K}", "K": K,
                                 "spearman_persona_yield": cc - bump})
                rows.append({"model": m, "representation": rep, "variant": var, "metric": "resid_K95", "K": 300,
                             "spearman_persona_yield": c - 0.1})
                rec = 0.97 if rep == "full" else 0.93
                para.append({"model": m, "representation": rep, "variant": var, "query": "no_label",
                             "recall": {"cos": {"recall_at_1": rec}},
                             "covered": {"t_hi": 0.5, "t_lo": 0.2, "recall_at_t_hi": 0.95,
                                         "rate_above_t_hi": {"antonym": 0.3}, "heldout_recall_mean": 0.94}})
                held.append({"model": m, "representation": rep, "variant": var, "K95": 300,
                             "by_K": {"10": {"spearman_para_vs_original": 0.8}, "20": {"spearman_para_vs_original": 0.85},
                                      "40": {"spearman_para_vs_original": 0.86}, "300": {"spearman_para_vs_original": 0.7}}})
    return rows, para, held


def test_choose_settings_separately():
    rows, para, held = _fake_rows()
    st = C.choose_settings(rows, para, held, ["openai", "gemma"], query="no_label")
    cov, dirn = st["covered"], st["directional"]
    # w14 has the better (a) but misses the 0.95 recall target: full wins the covered setting
    assert cov["representation"] == "full" and cov["variant"] == "pw2" and cov["recall_target_met"]
    assert cov["thresholds"]["openai"]["t_hi"] == 0.5 and cov["evaluation"]["antonym_rate_above_t_hi"]["openai"] == 0.3
    # directional: best (c) is full / centred at K = 10
    assert (dirn["representation"], dirn["variant"], dirn["K"]) == ("full", "centred", 10)
    assert set(dirn["K_sensitivity"]) == {"10", "20", "40", "K95"} and dirn["heldout"]["20"] == 0.85
    cfg = C.proposed_metric_config(st, models={"openai": "text-embedding-3-large"}, contrast={"openai": "keep"},
                                   config_version="2026-10-02")
    from assistant_axis.gapgen.metric_config import MetricConfig
    m = MetricConfig.from_json(cfg)
    assert m.covered["representation"] == "full" and m.directional["K"] == 10


def test_decode_marks():
    sheet = ("### 1. [critical](x/critical.json) (openai embeddings)\n...\nMark (A / B / same): A\n\n"
             "### 2. [independent](x/independent.json) (bge embeddings)\nMark (A / B / same): same\n\n"
             "### 3. [reactive](x/reactive.json)\nMark (A / B / same): \n")
    key = [{"id": 1, "stem": "critical", "label": "critical", "class": "N", "model": "openai",
            "key": {"A": "full", "B": "strip"}},
           {"id": 2, "stem": "independent", "label": "independent", "class": "N", "model": "bge",
            "key": {"A": "strip", "B": "full"}},
           {"id": 3, "stem": "reactive", "label": "reactive", "class": "N", "model": "openai",
            "key": {"A": "strip", "B": "full"}}]
    d = C.decode_marks(sheet, key)
    assert [r["preferred"] for r in d["items"]] == ["full", "same", None]
    assert d["counts"] == {"full": 1, "strip": 0, "same": 1, "unmarked": 1}
    assert d["by_class"]["N"] == {"full": 1, "strip": 0, "same": 1}


def test_choose_settings_bands_and_exclusion():
    rows, para, held = _fake_rows()
    # a strip representation that would win both settings is excluded (the clauses are kept)
    extra_rows, extra_para, extra_held = [], [], []
    for r in rows:
        if r["representation"] == "full":
            extra_rows.append(dict(r, representation="strip", auc_dup_vs_distinct=r.get("auc_dup_vs_distinct", 0) + 0.2
                                   if "auc_dup_vs_distinct" in r else None,
                                   spearman_persona_yield=(r.get("spearman_persona_yield") or 0) + 0.2))
    for p in para:
        if p["representation"] == "full":
            extra_para.append(dict(p, representation="strip"))
    st = C.choose_settings(rows + extra_rows, para + extra_para, held, ["openai", "gemma"], query="no_label")
    assert st["covered"]["representation"] != "strip" and st["directional"]["representation"] != "strip"
    # when no candidate meets the recall target, those within the recall band of the best qualify
    low = [dict(p, recall={"cos": {"recall_at_1": 0.90 if p["representation"] == "full" else 0.895}}) for p in para]
    st2 = C.choose_settings(rows, low, held, ["openai", "gemma"], query="no_label")
    assert not st2["covered"]["recall_target_met"] and st2["covered"]["representation"] in ("full", "w14")
    assert "rule" in st2["covered"]
