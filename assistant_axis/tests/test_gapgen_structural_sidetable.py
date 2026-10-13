"""Structural generators: the position side table and the negative-label mismatches (coding_plan_09 section 8,
``sidetable``)."""
from __future__ import annotations

import hashlib

import pytest

from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import postprocess as PP
from assistant_axis.gapgen.generators.structural import sidetable as ST
from assistant_axis.tests import structural_fakes as F


@pytest.mark.parametrize("model,recorded,want", [
    ("cowardly", "cowardly", "match"),
    ("Cowardly", "cowardly", "match"),
    ("stubbornness", "stubborn", "match"),         # folded by the lexicon (nominal to adjective)
    ("craven", "cowardly", "mismatch"),
    (None, "cowardly", "mismatch"),                # no opposite returned against a real word
    ("sunny", "non-gloomy", "placeholder"),
    ("sunny", None, "none_recorded"),
    ("sunny", "", "none_recorded"),
])
def test_compare_negative_label_truth_table(model, recorded, want):
    assert ST.compare_negative_label(model, recorded, lexicon=F.LEXICON) == want


def _rep(stem, label, **kw):
    rep, _ = O.parse_operator_reply(F.reply(**kw), principal=False, source_label=label, source_stem=stem)
    rep.stem, rep.label, rep.run_id, rep.model, rep.prompt_sha256, rep.at = stem, label, "r1", O.MODEL, "sha", "t"
    return rep


@pytest.fixture()
def world(tmp_path):
    data = F.write_corpus(tmp_path)
    reps = [_rep("brave", "brave", position="mean", opposite=F.item("cowardly")),
            _rep("timid", "timid", position="deficiency", opposite=F.item("brave")),
            _rep("honest", "honest", position="mean", opposite=F.item("deceitful")),
            _rep("gloomy", "gloomy", position="excess", opposite=F.item("sunny")),
            _rep("zealous", "zealous", position="excess", opposite=None)]
    return data, PP.load_corpus(data), reps


def test_position_rows_and_mismatch_readout(world):
    data, corpus, reps = world
    rows = ST.position_rows(reps, corpus=corpus, lexicon=F.LEXICON)
    by = {r["stem"]: r for r in rows}
    assert [r["stem"] for r in rows] == sorted(by)
    assert by["timid"]["negative_label_check"] == "match" and by["timid"]["position"] == "deficiency"
    assert by["brave"]["negative_label_check"] == "mismatch"              # recorded timid, returned cowardly
    assert by["gloomy"]["negative_label_check"] == "placeholder"
    assert by["zealous"]["negative_label_check"] == "mismatch" and by["zealous"]["model_opposite"] is None
    assert by["honest"]["recorded_negative_label"] == "dishonest" and by["honest"]["model_opposite"] == "deceitful"
    assert set(rows[0]) >= {"schema_version", "stem", "label", "position", "recorded_negative_label", "model_opposite",
                            "negative_label_check", "reasoning", "run_id", "model", "prompt_sha256", "at"}
    md = ST.render_mismatches(rows)
    for want in ("deceitful", "dishonest", "cowardly", "timid", "Reasoned first.",
                 "[honest](../../traits/instructions/honest.json)"):
        assert want in md
    assert "sunny" not in md                                               # a placeholder row is not a mismatch


def test_writes_under_structural_only_and_never_a_trait_file(world, tmp_path):
    data, corpus, reps = world
    tdir = data / "traits" / "instructions"
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tdir.glob("*.json")}
    sdir = tmp_path / "structural"
    rows = ST.position_rows(reps, corpus=corpus, lexicon=F.LEXICON)
    ST.write_position_table(rows, sdir / "position_table.jsonl")
    ST.write_mismatches(rows, sdir / "negative_label_mismatches.md")
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in tdir.glob("*.json")}
    assert before == after
    assert sorted(p.name for p in sdir.iterdir()) == ["negative_label_mismatches.md", "position_table.jsonl"]
    assert ST.load_position_table(sdir / "position_table.jsonl") == rows


def test_snapshot_on_change(world, tmp_path):
    data, corpus, reps = world
    p = tmp_path / "position_table.jsonl"
    rows = ST.position_rows(reps, corpus=corpus, lexicon=F.LEXICON)
    assert ST.write_position_table(rows, p) is None
    assert ST.write_position_table(rows, p) is None                       # unchanged: not rewritten
    first = p.read_bytes()
    bak = ST.write_position_table(rows[:-1], p)
    assert bak is not None and bak.name.startswith("position_table.jsonl.bak.") and bak.read_bytes() == first


def test_principal_only_replies_have_no_row(world):
    data, corpus, reps = world
    import json
    rep, _ = O.parse_operator_reply(json.dumps({"reasoning": "r", "retarget": {}}), principal=True,
                                    principal_only=True)
    rep.stem = "obedient"
    assert "obedient" not in {r["stem"] for r in ST.position_rows([*reps, rep], corpus=corpus)}
