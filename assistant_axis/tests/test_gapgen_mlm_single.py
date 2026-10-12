"""Masked-LM generator, task 3: the single-mask pass on planted logits (plan section 8, ``single``)."""
import math

import numpy as np
import pytest

from assistant_axis.gapgen.generators.masked_lm import frames as F
from assistant_axis.gapgen.generators.masked_lm import singlemask as S
from assistant_axis.gapgen.generators.masked_lm import table as T
from assistant_axis.tests.mlm_fakes import FakeMaskedLM, make_tokenizer

VOCAB = ["She", "He", "They", "Ġis", "Ġare", "Ġby", "Ġnature", ".", "Ġfundamentally", "Ġkind", "Ġkinder", "ĠKind",
         "Ġcruel", "Ġbeautiful", "Ġstrong", "Ġ123", "Ġ!!", "Ġx", "Ġshy", "Ġsyc", "oph", "antic", "ness"]
LEMMAS = {"kind", "cruel", "beautiful", "strong", "shy"}


def lemmatizer():
    return S.make_lemmatizer(LEMMAS.__contains__, lambda w, pos: {"kinder": {"kind"}}.get(w, set()) if pos == "a"
                             else set())


def scorer(they_beautiful=1.0):
    def f(pieces, pos):
        out = {"Ġkind": 6.0, "Ġkinder": 4.0, "ĠKind": 3.0, "Ġcruel": 2.0, "Ġ123": 9.0, "Ġ!!": 8.0, "Ġx": 8.5,
               "Ġshy": 0.5}
        out["Ġbeautiful"] = 7.0 if "She" in pieces else (they_beautiful if "They" in pieces else 1.0)
        out["Ġstrong"] = 7.0 if "He" in pieces else 1.0
        if "Ġfundamentally" in pieces:
            out["Ġcruel"] = 6.5
        if pieces[pos] == "<mask>" and "Ġsyc" in pieces[:pos]:
            out["oph"] = 5.0
        elif pieces[pos] == "<mask>" and pos + 1 < len(pieces) and pieces[pos + 1] == "<mask>":
            out["Ġsyc"] = 2.0
        if pieces[pos] == "<mask>" and pos >= 2 and pieces[pos - 1] == "oph":
            out["antic"] = 6.0
        return out
    return f


def run(they_beautiful=1.0, top_rank=3):
    tok = make_tokenizer(VOCAB)
    mlm = FakeMaskedLM(tok, scorer(they_beautiful))
    insts = F.instances([F.FRAME_BY_ID["disp_nature"], F.FRAME_BY_ID["disp_fundamentally"]], tok.mask_token,
                        subjects=["she", "he", "they"])
    res = S.run_single_pass(mlm, insts, top_rank=top_rank, lemmatize=lemmatizer(), track=("kind", "sycophantic"),
                            echo=lambda *a: None)
    return res, mlm, tok, insts


def test_word_groups_detokenise_lowercase_lemmatise_and_drop_non_words():
    tok = make_tokenizer(VOCAB)
    g = S.build_word_groups(tok, lemmatizer())
    assert "kind" in g.index and "kinder" not in g.index          # lemmatised through the fake morphy
    assert sorted(tok.pieces[i] for i in g.token_ids[g.starts[g.index["kind"]]:g.starts[g.index["kind"]] + 3]) == \
        ["ĠKind", "Ġkind", "Ġkinder"]                              # lower-cased and merged
    assert "123" not in g.index and "!!" not in g.index and "x" not in g.index   # non-alphabetic, too short
    assert "oph" not in g.index and "ness" not in g.index           # continuation pieces never form a word


def test_group_probability_is_the_sum_of_its_pieces():
    res, mlm, tok, insts = run()
    seqs, pos = S.encode_instances(tok, insts[:1])
    lp = mlm.logprobs_at(seqs, pos)[0]
    want = math.log(sum(math.exp(lp[tok.tok.ids[p]]) for p in ("Ġkind", "Ġkinder", "ĠKind")))
    she_nature = [i for i, x in enumerate(insts) if x.frame_id == "disp_nature" and x.subject == "she"][0]
    g = S.build_word_groups(tok, lemmatizer())
    got = S.instance_group_logprobs(FakeMaskedLM(tok, scorer()), insts, g)[she_nature, g.index["kind"]]
    assert got == pytest.approx(want, abs=1e-4)


def test_aggregates_best_mean_rank_and_top_counting():
    res, mlm, tok, insts = run(top_rank=2)
    a = res.aggs
    g = S.build_word_groups(tok, lemmatizer())
    lp = S.instance_group_logprobs(FakeMaskedLM(tok, scorer()), insts, g)
    ranks = S.ranks_of(lp)
    for w, x in a.items():
        j = g.index[w]
        assert x.best_logprob == pytest.approx(float(lp[:, j].max()), abs=1e-5)
        assert x.mean_rank == pytest.approx(float(ranks[:, j].mean()))
        assert x.n_top == int((ranks[:, j] <= 2).sum()) >= 1
    assert "123" not in a and "!!" not in a
    assert "shy" not in a                      # never in any instance's top 2: not kept
    assert a["beautiful"].best_subject == "she" and a["beautiful"].n_top == 2   # first in the two she instances
    assert a["cruel"].best_frame == "disp_fundamentally"
    # kind's ranks: 2 (she, nature; beautiful first), 2 (he; strong), 1 (they), 3, 3, 2 (fundamentally: cruel too)
    assert a["kind"].mean_rank == pytest.approx(13 / 6) and a["kind"].n_top == 4 and a["kind"].n_instances == 6
    k = a["kind"]
    assert k.best_logprob == pytest.approx(max(k.by_subject_best.values()), abs=1e-6)
    assert set(k.by_register_best) == {"psych_textbook"}


def test_gender_log_odds_reads_only_she_and_he():
    res, *_ = run(they_beautiful=1.0)
    res2, *_ = run(they_beautiful=6.9)        # "they" changes; she and he do not
    b1, b2 = res.aggs["beautiful"], res2.aggs["beautiful"]
    assert b1.gender_log_odds > 4 and b1.gender_log_odds == pytest.approx(b2.gender_log_odds, abs=1e-5)
    assert res.aggs["strong"].gender_log_odds < -4
    assert abs(res.aggs["kind"].gender_log_odds) < 0.5
    assert b1.by_subject_logprob["they"] != pytest.approx(b2.by_subject_logprob["they"], abs=0.1)


def test_frames_record_top_words_and_probe_label_ranks():
    res, *_ = run()
    fr = res.meta["frames"]
    assert set(fr) == {"disp_nature", "disp_fundamentally"}
    top = [w for w, _ in fr["disp_nature"]["top"]]
    assert top[0] == "kind"
    lab = fr["disp_nature"]["labels"]
    assert lab["kind"] == {"rank": 1, "logprob": lab["kind"]["logprob"], "via": "vocab"}
    assert lab["sycophantic"]["via"] == "pll" and lab["sycophantic"]["rank"] >= 1
    assert len(res.meta["thresholds"]) == 6 and res.meta["n_forward"] > 0


def test_gender_never_gates_mutation(tmp_path):
    """Zeroing every gender log-odds changes no ``eligible`` and no ``union_rank``."""
    from assistant_axis.tests.test_gapgen_mlm_table import fake_lookups
    res, *_ = run()
    rows = T.build_table({"single:roberta": res}, lookups=fake_lookups())
    for a in res.aggs.values():
        a.gender_log_odds = 0.0
    rows0 = T.build_table({"single:roberta": res}, lookups=fake_lookups())
    assert [(r["stem"], r["eligible"], r["union_rank"]) for r in rows] == \
        [(r["stem"], r["eligible"], r["union_rank"]) for r in rows0]
    assert any(r["gender_log_odds"] for r in rows) and all(r["gender_log_odds"] == 0.0 for r in rows0)


def test_pass_records_round_trip(tmp_path):
    res, *_ = run()
    S.write_pass(res, tmp_path)
    back = S.load_pass(tmp_path, "roberta", "single")
    assert set(back.aggs) == set(res.aggs) and back.meta["pass"] == "single"
    assert back.aggs["kind"]["best_logprob"] == round(res.aggs["kind"].best_logprob, 4)
    assert set(S.load_all_passes(tmp_path)) == {"single:roberta"}


def test_ranks_and_estimate_rank():
    lp = np.array([[0.1, 0.5, 0.3]])
    assert S.ranks_of(lp).tolist() == [[3, 1, 2]]
    srt = np.array([5.0, 4.0, 3.0, 1.0])
    assert S.estimate_rank(srt, 4.5) == 2 and S.estimate_rank(srt, 6) == 1 and S.estimate_rank(srt, 0) == 5


def test_one_mask_per_instance():
    tok = make_tokenizer(VOCAB)
    bad = F.Instance("x", "she", "She is <mask><mask> by nature.", "novel", "dispositional", "novel", "predicate")
    with pytest.raises(ValueError):
        S.encode_instances(tok, [bad])
