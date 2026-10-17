"""LLM-entropy generator: the collapse statistics (coding_plan_06 section 8, ``collapse``).  No network: the hash
embedder."""
from __future__ import annotations

import json

import pytest

from assistant_axis.gapgen.embed import HashEmbedder, normalize_rows
from assistant_axis.gapgen.generators.llm_entropy import collapse as CO
from assistant_axis.gapgen.generators.llm_entropy.table import Item


def item(stem, *, family="a", prompt="a:money:habit", run=1, model="claude-haiku-5-5", label=None, order=0,
         language="en", stage=1):
    return Item(item_id=f"{prompt}|{run}|{stem}", family=family, prompt_id=prompt, run=run, stage=stage,
                language=language, model=model, raw=label or stem, label=label or stem.replace("_", " "), gloss=None,
                antonym=None, kind="trait", ambiguity_flag=False, probability=None, stem=stem, zipf_min=4.0,
                label_problem=None, order=order)


def embed(texts):
    return normalize_rows(HashEmbedder(dim=256).embed_batch(texts)[0])


def test_jaccard_on_planted_runs():
    assert CO.label_jaccard({1: {"a", "b"}, 2: {"a", "b"}, 3: {"a", "b"}}) == [1.0, 1.0, 1.0]
    assert CO.label_jaccard({1: {"a"}, 2: {"b"}}) == [0.0]
    assert CO.label_jaccard({1: set(), 2: set(), 3: {"a"}}) == [0.0, 0.0]        # two empty runs left out
    its = ([item(s, run=r, prompt="a:x:p1") for r in (1, 2, 3) for s in ("aa", "bb")] +       # identical: 1.0
           [item(s, run=r, prompt="a:x:p2") for r, s in ((1, "cc"), (2, "dd"), (3, "ee"))] +  # disjoint: 0.0
           [item(s, run=r, prompt="a:x:p3") for r, ss in ((1, ("ff", "gg")), (2, ("ff",)), (3, ("ff", "gg")))
            for s in ss])                                                                       # 0.5, 1.0, 0.5
    f = CO.figures(its)
    assert f["n_prompts_jaccard"] == 3
    assert f["jaccard_median"] == pytest.approx(2 / 3, abs=1e-4)
    assert f["jaccard_p90"] == pytest.approx(0.9333, abs=1e-4)


def test_lincoln_petersen():
    assert CO.lincoln_petersen(10, 10, 5) == {"N": 20.0, "chapman": pytest.approx(19.17, abs=0.01)}
    assert CO.lincoln_petersen(10, 10, 0) == {"N": None, "chapman": 120.0}
    its = [item(s, run=1, prompt=f"a:x:{s}") for s in "abcd"] + [item(s, run=2, prompt=f"a:x:{s}") for s in "cdef"]
    lp = CO.figures(its)["lincoln_petersen"]
    assert (lp["n1"], lp["n2"], lp["m"], lp["N"]) == (4, 4, 2, 8.0) and lp["split"] == "runs 1 and 2"
    one_run = [item(s, run=1, prompt=f"b:r{i:04d}", family="b") for i, s in enumerate("abcab")]
    assert CO.figures(one_run)["lincoln_petersen"]["split"] == "odd and even prompts"


def test_rarefaction_is_non_decreasing_with_the_end_slope_over_the_last_fifth():
    calls = [{f"s{i}"} for i in range(10)] + [{"s0"} for _ in range(10)]
    r = CO.rarefaction_curve(calls, seed=3)
    ys = [y for _, y in r["curve"]]
    assert ys == sorted(ys) and r["n_calls"] == 20 and r["n_unique"] == 10 and r["curve"][-1] == [20, 10]
    flat = CO.rarefaction_curve([{"x"}] * 10)
    assert flat["end_slope_per_call"] == 0.0
    fresh = CO.rarefaction_curve([{f"y{i}"} for i in range(10)])
    assert fresh["end_slope_per_call"] == 1.0
    assert CO.rarefaction_curve([]) == {"curve": [], "end_slope_per_call": None, "n_calls": 0, "n_unique": 0}


def test_semantic_sets_merge_planted_near_synonyms_only():
    labels = {"keeps_receipts": "keeps receipts", "receipts_keeps": "receipts keeps", "zzalpha": "zzalpha",
              "zzbeta": "zzbeta"}
    cl = CO.semantic_clusters(labels, embed, tau=0.9)
    assert cl["keeps_receipts"] == cl["receipts_keeps"] and cl["zzalpha"] != cl["zzbeta"]
    assert len(set(cl.values())) == 3
    its = [item("keeps_receipts", run=1), item("receipts_keeps", run=2), item("zzalpha", run=1)]
    f = CO.figures(its, clusters=cl)
    assert f["n_unique_string"] == 3 and f["n_unique_semantic"] == 2


def test_cross_family_matrix_is_symmetric_with_ones_on_the_diagonal():
    m = CO.cross_family_matrix({"a": {"x", "y"}, "e": {"y", "z"}, "c": set()})
    assert m["families"] == ["a", "c", "e"]
    mat = m["matrix"]
    for i in range(3):
        assert mat[i][i] == 1.0
        for j in range(3):
            assert mat[i][j] == mat[j][i]
    assert mat[0][2] == pytest.approx(1 / 3, abs=1e-4)


def test_unique_per_usd_reads_the_runs_usage_json():
    recs = [{"family": "a", "usage_raw": {"input_tokens": 1_000_000, "output_tokens": 0}, "charged_as":
             "claude-haiku-5-5"},
            {"family": "e", "usage_raw": {"input_tokens": 3_000_000, "output_tokens": 0}, "charged_as":
             "claude-haiku-5-5"}]
    costs = CO.family_costs(recs, usage_total_usd=0.8)          # records say $0.40; usage.json $0.80
    assert costs["records_usd"] == pytest.approx(0.4) and costs["scale"] == pytest.approx(2.0)
    assert costs["by_family"] == {"a": pytest.approx(0.2), "e": pytest.approx(0.6)}
    its = [item(f"s{i}") for i in range(10)]
    payload = CO.collapse_payload(its, recs, usage_total_usd=0.8)
    assert payload["per_family"]["a"]["unique_per_usd"] == 50.0 and payload["per_family"]["a"]["cost_usd"] == 0.2


def test_collapse_payload_by_model_by_language_and_the_file(tmp_path):
    its = ([item(f"s{i}", family="c", prompt="c:de:money", language="de", run=r) for i in range(3) for r in (1, 2)]
           + [item("s9", family="c", prompt="c:fi:money", language="fi", model="claude-sonnet-5-5")]
           + [item("s1", family="a")])
    p = CO.collapse_payload(its, [], embed=embed, embedder="hash", runs=["r"])
    c = p["per_family"]["c"]
    assert set(c["by_language"]) == {"de", "fi"} and set(c["by_model"]) == {"claude-haiku-5-5", "claude-sonnet-5-5"}
    assert c["jaccard_median"] == 1.0 and p["cross_family"]["semantic"] is not None and p["embedder"] == "hash"
    path = tmp_path / "collapse.json"
    assert CO.write_collapse(p, path) is None
    assert CO.load_collapse(path) == json.loads(json.dumps(p))
    assert "_provenance" in json.loads(path.read_text())
    assert CO.write_collapse(p, path) is None                    # unchanged: not rewritten


def test_the_net_new_end_slope_counts_net_new_stems_only():
    its = [item(f"s{i}", prompt=f"a:x:{i}") for i in range(10)] + [item("old", prompt=f"a:y:{i}") for i in range(10)]
    assert CO.net_new_end_slope(its, {f"s{i}" for i in range(10)}, seed=1) <= 1.0
    assert CO.net_new_end_slope(its, set()) == 0.0
    p = CO.collapse_payload(its, [], net_new_stems={"s1"})
    assert p["per_family"]["a"]["net_new_end_slope_per_call"] is not None
    assert CO.collapse_payload(its, [])["per_family"]["a"]["net_new_end_slope_per_call"] is None
