"""Masked-LM generator, task 5: the subword-continuation and multiword beams (plan section 8, ``beam``)."""
import pytest

from assistant_axis.gapgen.generators.masked_lm import beam as BM
from assistant_axis.gapgen.generators.masked_lm import frames as F
from assistant_axis.tests.mlm_fakes import FakeMaskedLM, make_tokenizer

VOCAB = ["She", "He", "Ġis", "Ġby", "Ġnature", ".", "'s", "Ġhabitually", "Ġsyc", "oph", "antic", "Ġkind", "Ġhearted",
         "Ġand", "ness", "Ġrisk", "-", "a", "verse", "Ġto", "Ġanimals", "ly", "Ġintellectual", "Ġhonest", "Ġgoal",
         "oriented", "seeking", "minded", "Ġ123"]


def scorer(pieces, pos):
    nxt = pieces[pos + 1] if pos + 1 < len(pieces) else None
    prv = pieces[pos - 1]
    if prv == "Ġsyc":
        return {"oph": 6.0, "Ġhearted": 5.0}
    if prv == "Ġkind":
        return {"Ġhearted": 6.0, "ness": 5.0}       # the model prefers a new word after "kind"
    if prv == "Ġand":
        return {"Ġhonest": 7.0, "Ġkind": 6.0}
    if prv == "-":
        return {"a": 6.0, "Ġhonest": 1.0}
    if prv == "a":
        return {"verse": 6.0}
    if prv == "Ġto":
        return {"Ġanimals": 6.0}
    if prv == "ly":
        return {"Ġhonest": 6.0}
    if nxt == "<mask>":
        return {"Ġkind": 5.0, "Ġsyc": 4.0, "Ġand": 3.0, "Ġ123": 9.0}
    if nxt == "-":
        return {"Ġrisk": 5.0, "Ġgoal": 4.0}
    if nxt == "Ġto":
        return {"Ġkind": 5.0}
    if nxt == "ly":
        return {"Ġintellectual": 5.0}
    return {}


def fake():
    return FakeMaskedLM(make_tokenizer(VOCAB), scorer)


def test_continuation_accepted_only_without_a_leading_space():
    mlm = fake()
    res = BM.subword_pass(mlm, [F.FRAME_BY_ID["disp_habitually"]], k_first=3, widths=(2,), beam_width=1,
                          echo=lambda *a: None)
    # syc + oph continues one word; kind's best next piece "hearted" begins a new word, and "and"'s "honest" too:
    # both branches die.  "123" is never a first piece (not alphabetic).
    assert set(res.aggs) == {"sycoph"}
    assert res.aggs["sycoph"].form == "word" and res.aggs["sycoph"].pattern == "[MASK][MASK]"
    # with a wider beam the model's second choice for kind ("ness", a continuation) is accepted
    wide = BM.subword_pass(fake(), [F.FRAME_BY_ID["disp_habitually"]], k_first=3, widths=(2,), beam_width=2,
                           echo=lambda *a: None)
    assert set(wide.aggs) == {"sycoph", "kindness"}


def test_k_first_is_respected():
    for k, calls in ((1, 2), (2, 3), (3, 4)):
        mlm = fake()
        BM.subword_pass(mlm, [F.FRAME_BY_ID["disp_habitually"]], k_first=k, widths=(2,), beam_width=1,
                        rescore=False, echo=lambda *a: None)
        assert mlm.n_forward == calls                 # one all-masked pass, then one per first piece
    mlm = fake()
    res = BM.subword_pass(mlm, [F.FRAME_BY_ID["disp_habitually"]], k_first=1, widths=(2,), beam_width=1,
                          echo=lambda *a: None)
    assert res.aggs == {}                            # only "kind" explored, and its branch dies


def test_the_bare_two_slot_form_classifies_word_and_phrase():
    res = BM.multiword_pass(fake(), [F.FRAME_BY_ID["disp_nature"]], k_first=3, beam_width=1,
                            patterns={"[MASK][MASK]": ("first", "free")}, subjects=("she",), echo=lambda *a: None)
    assert res.aggs["kind hearted"].form == "phrase"          # a leading-space piece: a second word
    assert res.aggs["sycoph"].form == "word"                  # a continuation piece: one word
    assert "and honest" not in res.aggs                    # opens on a function word: dropped
    assert res.meta["yields"]["[MASK][MASK]"]["phrase"] == 1 and res.meta["yields"]["[MASK][MASK]"]["word"] == 1


def test_multiword_patterns():
    res = BM.multiword_pass(fake(), [F.FRAME_BY_ID["disp_nature"]], k_first=2, beam_width=1, subjects=("she",),
                            echo=lambda *a: None)
    a = res.aggs
    assert a["risk-averse"].form == "hyphenated" and a["risk-averse"].pattern == "[MASK]-[MASK][MASK]"
    assert a["kind to animals"].form == "phrase"
    assert a["intellectually honest"].form == "phrase"
    assert "goal-oriented" in a and "risk-minded" in a and "goal-seeking" in a
    assert res.meta["n_jobs"] == len(F.MULTIWORD_PATTERNS)
    assert a["kind to animals"].best_frame == "disp_nature" and a["kind to animals"].best_subject == "she"


def test_assemble_and_allowed():
    assert BM.assemble("[MASK]-[MASK][MASK]", ("first", "after_hyphen", "cont"), ["risk", "a", "verse"],
                       [True, False, False]) == "risk-averse"
    assert BM.assemble("[MASK][MASK]", ("first", "free"), ["kind", "hearted"], [True, True]) == "kind hearted"
    assert BM.assemble("[MASK][MASK]", ("first", "free"), ["Kind", "hearted"], [True, False]) == "kindhearted"
    assert BM.assemble("[MASK]ly [MASK]", ("first", "new_word"), ["intellectual", "honest"], [True, True]) == \
        "intellectually honest"
    tok = make_tokenizer(VOCAB)
    ids = tok.tok.ids
    hy = BM.allowed(tok, "after_hyphen")
    assert hy[ids["a"]] and not hy[ids["Ġhonest"]] and not hy[ids["-"]]
    cont = BM.allowed(tok, "cont")
    assert cont[ids["oph"]] and not cont[ids["Ġkind"]] and not cont[tok.mask_id]
    wp = make_tokenizer(["kind", "##ness", "-"], scheme="wordpiece")
    assert BM.allowed(wp, "after_hyphen")[wp.tok.ids["kind"]] and not BM.allowed(wp, "after_hyphen")[wp.tok.ids["##ness"]]
    with pytest.raises(ValueError):
        BM.allowed(tok, "sideways")


def test_form_of_and_function_word_edges():
    assert [BM.form_of(s) for s in ("kind", "risk-averse", "kind to animals")] == ["word", "hyphenated", "phrase"]
    assert BM.function_word_edge("a fighter") and BM.function_word_edge("lied to us")
    assert BM.function_word_edge("very shy") and not BM.function_word_edge("kind to animals")
    assert not BM.function_word_edge("kind") and not BM.function_word_edge("self-aware")
    assert BM.function_word_edge("damn cute") and BM.function_word_edge("much fun")
    assert not BM.function_word_edge("fiercely independent")


def test_rescoring_puts_a_hit_on_the_union_scale():
    """A pattern's chain leaves its literal text unscored; the rescored ``best_logprob`` is the surface's PLL in
    the instance's single slot, the chain score kept as ``beam_score``."""
    from assistant_axis.gapgen.generators.masked_lm import pll as P
    mlm = fake()
    res = BM.multiword_pass(mlm, [F.FRAME_BY_ID["disp_nature"]], k_first=2, beam_width=1, subjects=("she",),
                            patterns={"[MASK]-oriented": ("first",)}, echo=lambda *a: None)
    a = res.aggs["goal-oriented"]
    text = F.instantiate(F.FRAME_BY_ID["disp_nature"], F.SUBJECT_BY_KEY["she"], mlm.tok.mask_token)
    assert a.best_logprob == pytest.approx(P.pll_score(mlm, text, "goal-oriented"), abs=1e-4)
    assert a.beam_score > a.best_logprob             # the chain never paid for "-oriented"
    raw = BM.multiword_pass(fake(), [F.FRAME_BY_ID["disp_nature"]], k_first=2, beam_width=1, subjects=("she",),
                            patterns={"[MASK]-oriented": ("first",)}, rescore=False, echo=lambda *a: None)
    assert raw.aggs["goal-oriented"].best_logprob == pytest.approx(a.beam_score, abs=1e-4)
    assert res.meta["settings"]["rescored"] is True
