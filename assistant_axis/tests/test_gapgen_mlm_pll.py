"""Masked-LM generator, task 6: pseudo-log-likelihood, Variant B and the contrast score (plan section 8, ``pll``)."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen.generators.masked_lm import frames as F
from assistant_axis.gapgen.generators.masked_lm import pll as P
from assistant_axis.gapgen.generators.masked_lm import singlemask as S
from assistant_axis.tests.mlm_fakes import FakeMaskedLM, make_tokenizer

DISP = {"Ġnature", "Ġfundamentally", "Ġhabitually", "Ġalways", "Ġpersonality", "Ġtemperament"}
STATE = {"Ġtoday", "Ġnow", "Ġmorning", "Ġmeeting", "Ġmoment"}
PHYS = {"Ġlooks", "Ġlook", "Ġhair", "Ġphysically", "Ġbuild"}
VOCAB = ["She", "He", "Ġis", "Ġby", ".", "'s", "Ġsyc", "oph", "Ġkind", "Ġtired", "Ġtall", "Ġjunk", "Ġcruel", "Ġshy",
         *DISP, *STATE, *PHYS]


def pll_scorer(pieces, pos):
    nxt = pieces[pos + 1] if pos + 1 < len(pieces) else None
    prv = pieces[pos - 1]
    if prv == "Ġsyc":
        return {"oph": 6.0}
    ctx = set(pieces)
    if ctx & STATE:
        return {"Ġtired": 6.0, "Ġkind": 1.0, "Ġtall": -2.0}
    if ctx & PHYS:
        return {"Ġtall": 6.0, "Ġkind": 1.0, "Ġtired": -2.0}
    out = {"Ġkind": 6.0, "Ġcruel": 4.0, "Ġshy": 3.0, "Ġtired": 0.0, "Ġtall": 0.0, "Ġjunk": -6.0}
    if nxt == "oph":                     # original mode: the later piece is visible
        out["Ġsyc"] = 5.0
    elif nxt == "<mask>":                # l2r: the later piece is masked too
        out["Ġsyc"] = 2.0
    return out


def fake():
    return FakeMaskedLM(make_tokenizer(VOCAB), pll_scorer)


def test_two_token_pll_is_the_sum_of_both_masked_log_probs():
    mlm = fake()
    text = F.instantiate(F.FRAME_BY_ID["disp_nature"], F.SUBJECT_BY_KEY["she"], mlm.tok.mask_token)
    spliced, a, b = P.splice(text, mlm.tok.mask_token, "sycoph")
    ids, pos = mlm.tok.encode_with_span(spliced, a, b)
    assert [mlm.tok.pieces[ids[p]] for p in pos] == ["Ġsyc", "oph"]
    m = mlm.tok.mask_id
    both = list(ids)
    both[pos[0]] = both[pos[1]] = m
    second = list(ids)
    second[pos[1]] = m
    first_only = list(ids)
    first_only[pos[0]] = m
    syc, oph = ids[pos[0]], ids[pos[1]]
    lp = lambda seq, p, t: float(mlm.logprobs_at([seq], [p])[0][t])  # noqa: E731
    want_l2r = lp(both, pos[0], syc) + lp(second, pos[1], oph)
    want_orig = lp(first_only, pos[0], syc) + lp(second, pos[1], oph)
    assert P.pll_score(mlm, text, "sycoph", mode="l2r") == pytest.approx(want_l2r, abs=1e-4)
    assert P.pll_score(mlm, text, "sycoph", mode="original") == pytest.approx(want_orig, abs=1e-4)
    assert want_orig > want_l2r                       # plain PLL lets the later piece predict the earlier one
    # a one-piece word: both modes are its single-mask log-probability
    one = float(mlm.logprobs_at([mlm.tok.encode(text)], [mlm.tok.encode(text).index(m)])[0][mlm.tok.tok.ids["Ġkind"]])
    assert P.pll_score(mlm, text, "kind", mode="l2r") == pytest.approx(one, abs=1e-4)
    assert P.pll_score(mlm, text, "kind", mode="original") == pytest.approx(one, abs=1e-4)


def test_masked_items_by_mode():
    l2r = P.masked_items([0, 10, 11, 12, 2], [1, 2, 3], 99, "l2r")
    assert [s for s, _, _ in l2r] == [[0, 99, 99, 99, 2], [0, 10, 99, 99, 2], [0, 10, 11, 99, 2]]
    orig = P.masked_items([0, 10, 11, 12, 2], [1, 2, 3], 99, "original")
    assert [s for s, _, _ in orig] == [[0, 99, 11, 12, 2], [0, 10, 99, 12, 2], [0, 10, 11, 99, 2]]
    assert [t for _, _, t in l2r] == [10, 11, 12]
    with pytest.raises(ValueError):
        P.masked_items([1], [0], 9, "sum")


def test_contrast_is_dispositional_minus_the_larger_of_state_and_physical():
    mlm = fake()
    con = P.score_words(["kind", "tired", "tall"], mlm=mlm, echo=lambda *a: None)
    assert con["kind"].trait_contrast > 0 and not con["kind"].state_flag and not con["kind"].physical_flag
    assert con["tired"].state_flag and not con["tired"].physical_flag and con["tired"].trait_contrast < 0
    assert con["tall"].physical_flag and not con["tall"].state_flag and con["tall"].trait_contrast < 0
    insts = P.contrast_instances(mlm.tok.mask_token)
    kinds = [i.kind for i in insts]
    assert set(kinds) == {"dispositional", "state", "physical"} and len(insts) == 2 * len(F.CONTRAST_SET)
    mat = P.pll_matrix(mlm, ["kind"], [i.text for i in insts])[0]
    d = np.mean([v for v, k in zip(mat, kinds) if k == "dispositional"])
    s = np.mean([v for v, k in zip(mat, kinds) if k == "state"])
    ph = np.mean([v for v, k in zip(mat, kinds) if k == "physical"])
    assert con["kind"].trait_contrast == pytest.approx(d - max(s, ph), abs=1e-4)
    assert con["kind"].as_dict()["trait_contrast"] == round(con["kind"].trait_contrast, 4)


def test_variant_b_ranks_a_good_word_above_junk_and_places_it_in_the_distribution():
    mlm = fake()
    lem = lambda w: w.lower()  # noqa: E731
    res = P.variant_b(mlm, ["junk", "kind", "sycoph"], top_rank=2, lemmatize=lem, echo=lambda *a: None)
    a = res.aggs
    assert a["kind"].best_logprob > a["sycoph"].best_logprob > a["junk"].best_logprob
    assert a["kind"].n_top == 12 and a["kind"].mean_rank == pytest.approx(1.0)     # first in every instance
    assert a["junk"].n_top == 0 and a["junk"].mean_rank > 2
    assert res.meta["n_surfaced"] == sum(1 for x in a.values() if x.n_top > 0)
    assert len(res.meta["thresholds"]) == len(F.VARIANT_B_INSTANCES)
    assert {x.best_frame for x in a.values()} <= {f for f, _ in F.VARIANT_B_INSTANCES}


def test_scoring_resumes_from_its_checkpoint(tmp_path):
    ck = tmp_path / "vb.partial.jsonl"
    words = ["kind", "junk", "sycoph", "tired"]
    first = fake()
    r1 = P.variant_b(first, words, lemmatize=str.lower, checkpoint=ck, chunk=2, echo=lambda *a: None)
    lines = [json.loads(x) for x in ck.read_text().splitlines()]
    assert [d["word"] for d in lines] == words and all(len(d["pll"]) == 12 for d in lines)
    second = fake()
    r2 = P.variant_b(second, words, lemmatize=str.lower, checkpoint=ck, echo=lambda *a: None)
    assert second.n_forward == len(F.VARIANT_B_INSTANCES)      # only the instances' own distributions
    assert {w: round(x.best_logprob, 3) for w, x in r1.aggs.items()} == \
        {w: round(x.best_logprob, 3) for w, x in r2.aggs.items()}
    with open(ck, "a") as fh:
        fh.write('{"word": "torn')                              # a torn last line is redone, not fatal
    P.variant_b(fake(), words, lemmatize=str.lower, checkpoint=ck, echo=lambda *a: None)


def test_checkpoint_key_depends_on_what_the_scores_depend_on():
    k = P.checkpoint_key(["a", "b"], "l2r", "roberta", "rev1")
    assert k == P.checkpoint_key(["a", "b"], "l2r", "roberta", "rev1")
    assert k != P.checkpoint_key(["a", "b"], "original", "roberta", "rev1")
    assert k != P.checkpoint_key(["a", "c"], "l2r", "roberta", "rev1")
    assert k != P.checkpoint_key(["a", "b"], "l2r", "roberta", "rev2")


def test_splice_needs_exactly_one_mask():
    assert P.splice("She is <mask>.", "<mask>", "kind") == ("She is kind.", 7, 11)
    with pytest.raises(ValueError):
        P.splice("She is <mask> <mask>.", "<mask>", "kind")
