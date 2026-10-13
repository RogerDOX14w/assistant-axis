"""Structural generators: recovery, the queue hold-out, null rates, stability, parse rate (coding_plan_09 section 8,
``evaluate``)."""
from __future__ import annotations

import json

import numpy as np
import pytest

from assistant_axis.gapgen.embed import HashEmbedder, embed_texts
from assistant_axis.gapgen.generators.structural import evaluate as E
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import postprocess as PP
from assistant_axis.tests import structural_fakes as F


def _rep(stem, label="", *, principal=False, principal_only=False, **kw):
    if principal_only:
        text = json.dumps({"reasoning": "r", "retarget": kw.get("retarget") or {}})
    else:
        text = F.reply(principal=principal, **kw)
    rep, why = O.parse_operator_reply(text, principal=principal, principal_only=principal_only,
                                      source_label=label or stem, source_stem=stem)
    assert why is None, why
    rep.stem, rep.label = stem, label or stem
    return rep


@pytest.fixture()
def corpus(tmp_path):
    return PP.load_corpus(F.write_corpus(tmp_path))


def _embed():
    emb = HashEmbedder(dim=64)
    return lambda texts: embed_texts(emb, texts)


def test_pair_recovery_by_stem_cosine_and_renamed(corpus):
    reps = {"brave": _rep("brave", opposite=F.item("timid")),                         # stem hit
            "timid": _rep("timid", opposite=F.item("bravery", "This means facing danger and pain without backing "
                                                    "away.")),                       # a miss by stem, a cosine hit
            "honest": _rep("honest", opposite=None),
            "careful_hexaco": _rep("careful_hexaco", "careful (HEXACO)", opposite=F.item("careless")),  # bare label
            }
    pairs = [("brave", "timid"), ("dishonest", "honest"), ("careful_hexaco", "careless_hexaco")]
    out = E.pair_recovery(reps, pairs, corpus=corpus, embed=_embed())
    assert out["n_pairs"] == 3 and out["n_directions"] == 6 and out["n_answered"] == 4
    assert out["n_null_opposite"] == 1
    assert out["recall_stem"] == 0.5                                                  # brave->timid, careful->careless
    assert out["recall_cos_0.7"] >= 0.75                                              # + timid->brave by the gloss
    assert out["recall_cos_0.9"] >= out["recall_stem"]
    assert out["pairs_either_direction_stem"] == 2 and out["pairs_both_directions_stem"] == 0
    assert {m["from"] for m in out["misses"]} >= {"honest"}
    # a renamed pole is recovered by its old stem
    reps2 = {"brave": _rep("brave", opposite=F.item("trusty old"))}
    assert E.pair_recovery(reps2, [("brave", "dependable")], corpus=corpus)["recall_stem"] == 1.0
    # the stem figures alone without an embedder
    assert "recall_cos_0.8" not in E.pair_recovery(reps, pairs, corpus=corpus)


def test_structure_recovery_finds_a_planted_corner_and_neighbour(corpus):
    reps = {"callous": _rep("callous", excess=F.item("malicious")),
            "compassionate": _rep("compassionate", opposite=F.item("cold")),
            "selfish": _rep("selfish", retarget={"intimates": F.item("clannish")}),
            "humanitarian": _rep("humanitarian", opposite=F.item("insular"))}
    tri = [("callous", "compassionate", "malicious")]
    seq = [("selfish", "clannish", "humanitarian")]
    out = E.structure_recovery(reps, tri, seq, corpus=corpus)
    assert out["triangles"] == {"n": 1, "corners": 3, "corners_recovered": 1, "triangles_with_a_corner": 1,
                                "detail": [{"triangle": list(tri[0]), "corner": "malicious"}]}
    assert out["sequence"]["n"] == 3 and out["sequence"]["recovered"] == 1 and out["sequence"]["which"] == ["clannish"]


def test_queue_holdout_three_lines(corpus, tmp_path):
    data = tmp_path / "data"
    frozen = E.freeze_holdout(queue_path=data / "seed_queue.json", corpus_stems=corpus.stems, registry_rows={
        "gutsy#1": F.registry_row("gutsy", "censuses", review="accepted"),
        "nervy#1": F.registry_row("nervy", "censuses")}, now="2026-10-13T00:00:00+00:00")
    # backlog plucky; paired mettlesome (no file; brave has one); not_adopted rash (callous has a file); candidate
    assert [e["stem"] for e in frozen["holdout"]] == ["plucky", "mettlesome"]
    assert frozen["rejected"] == ["rash"] and frozen["accepted"] == ["gutsy"]
    assert [e["stem"] for e in frozen["candidates"]] == ["spunky"]
    assert frozen["counts"] == {"holdout": 2, "rejected": 1, "accepted": 1, "candidates": 1}
    reps = [_rep("brave", opposite=F.item("cowardly"), excess=F.item("rash"), deficiency=F.item("plucky")),
            _rep("timid", retarget={"strangers": F.item("gutsy")})]
    out = E.queue_holdout(reps, frozen["holdout"], rejected=frozen["rejected"], accepted=frozen["accepted"],
                          candidates=frozen["candidates"])
    assert out["n"] == 2 and out["recall_stem"] == 0.5 and out["recovered"] == ["plucky"]
    assert out["by_operator"]["deficiency"] == 0.5 and out["by_operator"]["opposite"] == 0.0
    assert out["rejected"] == {"n": 1, "regenerated": 1, "stems": ["rash"]}                 # a planted rejected name
    assert out["accepted"]["recall_stem"] == 1.0 and out["candidates"]["recall_stem"] == 0.0
    # the accepted and candidate lines never enter the denominator
    assert out["n"] == len(frozen["holdout"])
    absent = E.queue_holdout(reps[1:], frozen["holdout"], rejected=frozen["rejected"])
    assert absent["rejected"]["regenerated"] == 0


def test_null_rates_with_the_principal_targets_apart():
    reps = [_rep("a", retarget={"self": F.item("x one")}, remode={"speech": F.item("y one")}),
            _rep("b"),
            _rep("c", principal=True, retarget={"the_user": F.item("z one"), "the_developer": F.item("w one")}),
            _rep("d", principal=True, principal_only=True, retarget={"the_operator": F.item("v one")})]
    out = E.null_rates(reps)
    assert out["n_traits"] == 3
    assert out["retarget"] == round(1 / 18, 4) and out["retarget_by_target"]["self"] == round(1 / 3, 4)
    assert out["remode"] == round(1 / 9, 4) and out["remode_by_mode"]["speech"] == round(1 / 3, 4)
    assert out["principal"]["n_traits"] == 2 and out["principal"]["n_items"] == 3
    assert out["principal"]["share"] == 0.5 and out["principal"]["by_target"]["the_user"] == 0.5
    assert out["band"]["retarget_in_band"] is True and out["band"]["remode_in_band"] is True
    assert E.null_rates([_rep("b")])["band"]["pass"] is False                                 # 0% is laziness


def test_pair_positions():
    reps = {"brave": _rep("brave", position="mean"), "timid": _rep("timid", position="deficiency"),
            "honest": _rep("honest", position="mean")}
    out = E.pair_positions(reps, [("brave", "timid"), ("dishonest", "honest")])
    assert out["n_pairs"] == 1 and out["combinations"] == {"deficiency/mean": 1}


def test_stability_jaccard_on_planted_runs():
    a = {"s1": _rep("s1", opposite=F.item("aa"), excess=F.item("bb")),
         "s2": _rep("s2", opposite=F.item("cc")),
         "s3": _rep("s3", opposite=F.item("dd"), deficiency=F.item("ee"))}
    identical = E.stability_jaccard(a, a)
    assert identical["jaccard_median"] == 1.0 and identical["below_0.5"] == 0 and identical["n_traits"] == 3
    b = {"s1": _rep("s1", opposite=F.item("xx")), "s2": _rep("s2", opposite=F.item("yy")),
         "s3": _rep("s3", opposite=F.item("dd"))}
    out = E.stability_jaccard(a, b)
    assert out["per_trait"] == {"s1": 0.0, "s2": 0.0, "s3": 0.5}
    assert out["jaccard_median"] == 0.0 and out["below_0.5"] == 2
    assert out["by_operator"]["opposite"] == 0.0 and sum(out["distribution"].values()) == 3
    empty = E.stability_jaccard({"s": _rep("s")}, {"s": _rep("s")})
    assert empty["jaccard_median"] == 1.0


def test_parse_rate():
    recs = [{"stage": "operators", "stem": "a", "label": "a", "text": F.reply()},
            {"stage": "operators", "stem": "b", "label": "b", "text": "garbled"},
            {"stage": "operators", "stem": "b", "label": "b", "text": F.reply()},
            {"stage": "operators", "stem": "c", "label": "c", "text": "garbled"}]
    out = E.parse_rate(recs)
    assert out["n_units"] == 3 and out["n_ok"] == 2 and out["rate"] == round(2 / 3, 4)
    assert out["n_records"] == 4 and out["n_records_ok"] == 2


def test_evaluation_file_round_trip_and_unchanged_rerun(tmp_path):
    p = tmp_path / "evaluation.json"
    payload = {"pair_recovery": {"recall_stem": 0.5}, "holdout_lists": {"counts": {"holdout": 2}}}
    assert E.write_evaluation(payload, p) is None
    first = p.read_bytes()
    assert E.write_evaluation(payload, p) is None and p.read_bytes() == first             # unchanged: untouched
    assert E.read_evaluation(p) == payload and "_provenance" in json.loads(first)
    bak = E.write_evaluation({**payload, "x": 1}, p)
    assert bak is not None and bak.read_bytes() == first
