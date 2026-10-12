"""Masked-LM generator: a smoke test of the real roberta-large on CPU (plan section 8).  Runs only with
``GAPGEN_RUN_LOCAL=1`` and the model already in ``data/external/hf`` (it never downloads): two frames, two
subjects, a five-wide beam, twenty words of Variant B.  About a minute on CPU.

    GAPGEN_RUN_LOCAL=1 uv run pytest assistant_axis/tests/test_gapgen_mlm_smoke.py -q
"""
import math
import os

import pytest

from assistant_axis.gapgen.generators.masked_lm import models as M

pytestmark = pytest.mark.skipif(
    os.environ.get("GAPGEN_RUN_LOCAL") != "1" or not M.model_present("roberta"),
    reason="needs GAPGEN_RUN_LOCAL=1 and roberta-large in data/external/hf (setup_external.py --hf-model "
           "FacebookAI/roberta-large)")


@pytest.fixture(scope="module")
def mlm():
    return M.load_mlm("roberta", "cpu", batch_size=32)


@pytest.fixture(scope="module")
def lem():
    from assistant_axis.gapgen.generators.masked_lm.singlemask import default_lemmatizer
    return default_lemmatizer()


def test_single_pass_finds_person_words(mlm, lem):
    from assistant_axis.gapgen.generators.masked_lm import frames as F
    from assistant_axis.gapgen.generators.masked_lm import singlemask as S
    insts = F.instances([F.FRAME_BY_ID["disp_nature"], F.FRAME_BY_ID["disp_habitually"]], mlm.tok.mask_token,
                        subjects=["she", "he"])
    res = S.run_single_pass(mlm, insts, lemmatize=lem, track=("helpful", "sycophantic"), echo=lambda *a: None)
    top = {w for w, _ in res.meta["frames"]["disp_nature"]["top"][:50]}
    assert {"shy", "kind", "gentle", "curious"} & top
    assert res.meta["frames"]["disp_habitually"]["labels"]["sycophantic"]["via"] == "pll"
    assert all(a.gender_log_odds is not None for a in res.aggs.values())


def test_pll_modes_on_a_split_word(mlm):
    from assistant_axis.gapgen.generators.masked_lm import pll as P
    text = "He's habitually " + mlm.tok.mask_token + "."
    l2r = P.pll_score(mlm, text, "sycophantic", mode="l2r")
    orig = P.pll_score(mlm, text, "sycophantic", mode="original")
    assert math.isfinite(l2r) and orig > l2r            # plain PLL inflates the split word
    assert P.pll_score(mlm, text, "late", mode="l2r") == pytest.approx(P.pll_score(mlm, text, "late",
                                                                                   mode="original"), abs=1e-4)


def test_beams_and_variant_b(mlm, lem):
    from assistant_axis.gapgen.generators.masked_lm import beam as BM
    from assistant_axis.gapgen.generators.masked_lm import frames as F
    from assistant_axis.gapgen.generators.masked_lm import pll as P
    sw = BM.subword_pass(mlm, [F.FRAME_BY_ID["disp_habitually"]], k_first=5, widths=(2,), lemmatize=lem,
                         echo=lambda *a: None)
    assert all(a.form == "word" and " " not in w for w, a in sw.aggs.items())
    mw = BM.multiword_pass(mlm, [F.FRAME_BY_ID["disp_nature"]], k_first=5, lemmatize=lem,
                           patterns={"[MASK]-minded": ("first",), "[MASK]-[MASK]": ("first", "after_hyphen")},
                           echo=lambda *a: None)
    assert any(w.endswith("-minded") for w in mw.aggs)
    vb = P.variant_b(mlm, ["kind", "sycophantic", "open-minded", "zymurgical", "honest"], lemmatize=lem,
                     echo=lambda *a: None)
    assert vb.aggs["kind"].best_logprob > vb.aggs["zymurgical"].best_logprob
