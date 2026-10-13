"""Structural generators: stems, membership tags, merge, rank, the operator table (coding_plan_09 section 8,
``postprocess``; task 6)."""
from __future__ import annotations

import copy
import json

import pytest

from assistant_axis.gapgen.generators.structural import modernise as M
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import postprocess as PP
from assistant_axis.gapgen.generators.structural import submit as SU
from assistant_axis.gapgen.registry import read_snapshot
from assistant_axis.tests import structural_fakes as F

LEX = F.LEXICON


def test_stem_of_phrases_nominals_and_spelling():
    assert PP.stem_of("harsh toward self") == ("harsh_toward_self", "harsh toward self")
    assert PP.stem_of("harsh toward self", lexicon=LEX) == ("harsh_toward_self", "harsh toward self")
    assert PP.stem_of("stubbornness", lexicon=LEX) == ("stubborn", "stubborn")       # the fake lexicon has it
    assert PP.stem_of("stubbornness") == ("stubbornness", "stubbornness")             # no lexicon, no fold
    assert PP.stem_of("zaniness", lexicon=LEX) == ("zaniness", "zaniness")            # no adjective: no fold
    assert PP.stem_of("organised", lexicon=LEX) == ("organized", "organized")         # US spelling, OEWN has it
    assert PP.stem_of("Open-Handed", lexicon=LEX) == ("open_handed", "Open-Handed")   # case kept when not folded
    with pytest.raises(ValueError):
        PP.stem_of("!!!")


@pytest.fixture()
def world(tmp_path):
    data = F.write_corpus(tmp_path)
    reg = F.write_registry(tmp_path / "registry.jsonl", [
        F.registry_row("craven", "censuses", verdict="reject"),                       # decided by M1
        F.registry_row("dauntless", "censuses"),                                     # registered, undecided
        F.registry_row("foolhardy", "base_model", verdict="trait", decision="new"),  # decided by M1 and M3
        F.registry_row("reckless", "roget", verdict="trait"),                        # M1 trait, M3 pending
    ])
    return {"data": data, "corpus": PP.load_corpus(data), "queue": PP.load_queue_index(data / "seed_queue.json"),
            "registry": PP.registry_index(read_snapshot(reg)), "reg_path": reg}


@pytest.mark.parametrize("stem,want", [
    # stem: (exists, queued, queue_status, is_negative_label, registered, registered_decided, net_new)
    ("brave", (True, True, "paired", True, False, False, False)),
    ("trusty_old", (True, False, None, False, False, False, False)),            # renamed_from
    ("apathetic", (False, False, None, True, False, False, True)),              # a negative label with no file
    ("plucky", (False, True, "backlog", False, False, False, False)),
    ("rash", (False, True, "not_adopted", False, False, False, False)),
    ("spunky", (False, True, "candidate", False, False, False, False)),
    ("valiant", (False, True, "superseded", False, False, False, False)),       # by normalised label
    ("warrior", (False, True, "backlog", False, False, False, False)),          # a role entry
    ("craven", (False, False, None, False, True, True, False)),
    ("foolhardy", (False, False, None, False, True, True, False)),
    ("dauntless", (False, False, None, False, True, False, True)),
    ("reckless", (False, False, None, False, True, False, True)),
    ("gutsy", (False, False, None, False, False, False, True)),
])
def test_tags_truth_table(world, stem, want):
    c = world["corpus"]
    t = PP.tag_membership(stem, corpus_stems=c.stems, renamed=c.renamed, negative_label_stems=c.negative_label_stems,
                          queue=world["queue"], registry=world["registry"])
    assert (t.exists, t.queued, t.queue_status, t.is_negative_label, t.registered, t.registered_decided,
            t.net_new) == want


def test_registered_by_and_status(world):
    c = world["corpus"]
    t = PP.tag_membership("dauntless", corpus_stems=c.stems, renamed=c.renamed,
                          negative_label_stems=c.negative_label_stems, queue=world["queue"], registry=world["registry"])
    assert t.registered_by == ("censuses",) and t.status == "registered-pending"
    assert c.is_unpaired("gloomy") and not c.is_unpaired("brave") and not c.is_unpaired("zealous")


def _rep(stem, label, *, run_id="r1", principal=False, **kw):
    rep, why = O.parse_operator_reply(F.reply(principal=principal, **kw), principal=principal, source_label=label,
                                      source_stem=stem)
    assert why is None
    rep.stem, rep.label, rep.run_id = stem, label, run_id
    return rep


@pytest.fixture()
def replies():
    return [
        _rep("brave", "brave", position="mean", opposite=F.item("cowardly"), excess=F.item("foolhardy"),
             deficiency=F.item("craven"), remode={"speech": F.item("bold-spoken")}),
        _rep("timid", "timid", position="deficiency", opposite=F.item("bold"), excess=F.item("foolhardy")),
        _rep("gloomy", "gloomy", position="excess", opposite=F.item("sunny"),
             retarget={"self": F.item("down on oneself", common=False)}),
        _rep("obedient", "obedient", position="excess", principal=True, opposite=F.item("defiant"),
             retarget={"the_user": F.item("user-pleasing", common=False)}),
    ]


def _modern():
    def row(id_, scheme, item, role, labels, sibs):
        return M.ModernRow(id=id_, scheme=scheme, item=item, role=role, gloss="g", sibling_ids=sibs, source=None,
                           labels=labels, gloss_modern="This means it.", polysemy=False, reasoning="r", model="m",
                           prompt_sha256="p", run_id="a1")
    return [row("aristotle:courage:deficiency", "aristotle", "cowardice", "deficiency", ["cowardly", "craven"],
                ["aristotle:courage:mean", "aristotle:courage:excess"]),
            row("aristotle:courage:mean", "aristotle", "courage", "mean", ["brave"],
                ["aristotle:courage:deficiency", "aristotle:courage:excess"]),
            row("aristotle:courage:excess", "aristotle", "rashness", "excess", ["foolhardy", "rash"],
                ["aristotle:courage:deficiency", "aristotle:courage:mean"])]


def test_merge_keeps_every_source_and_counts_traits_and_rows(world, replies):
    rows = {r["stem"]: r for r in PP.merge_items(replies, _modern(), corpus=world["corpus"], lexicon=LEX)}
    fh = rows["foolhardy"]
    assert fh["n_sources"] == 3                      # brave and timid (excess) and the classical rashness row
    assert {(s["generator_part"], s.get("source_stem") or s.get("source_id")) for s in fh["sources"]} == {
        ("operators", "brave"), ("operators", "timid"), ("classical", "aristotle:courage:excess")}
    assert fh["roles"] == ["excess"] and fh["kinds"] == ["classical", "degree_filler"]
    assert set(fh["siblings"]) >= {"brave", "timid", "craven", "cowardly"}
    assert rows["craven"]["n_sources"] == 2 and rows["craven"]["roles"] == ["deficiency"]
    assert rows["sunny"]["kinds"] == ["pair_completion"]         # the opposite of a non-X trait
    assert rows["cowardly"]["kinds"] == ["classical", "opposite"]
    assert rows["user_pleasing"]["principal_target"] and rows["user_pleasing"]["kinds"] == ["principal_retarget"]
    assert rows["down_on_oneself"]["has_common_word"] is False
    # partner hints: the source's label for an opposite, the sibling vice for excess / deficiency and classical vices
    by_src = {(s["generator_part"], s.get("source_stem") or s.get("source_id"), s.get("operator") or s.get("role")):
              s["partner_hint"] for r in rows.values() for s in r["sources"]}
    assert by_src[("operators", "brave", "opposite")] == "brave"
    assert by_src[("operators", "brave", "excess")] == "craven"
    assert by_src[("operators", "brave", "deficiency")] == "foolhardy"
    assert by_src[("operators", "timid", "excess")] is None                  # no deficiency answered
    assert by_src[("classical", "aristotle:courage:excess", "excess")] == "cowardly"
    assert by_src[("classical", "aristotle:courage:mean", "mean")] is None
    assert by_src[("operators", "gloomy", "retarget")] is None


def test_rank_order(world, replies):
    t = PP.build_table(replies, _modern(), corpus=world["corpus"], queue=world["queue"], registry=world["registry"],
                       lexicon=LEX)
    order = [r["stem"] for r in t]
    assert order[0] == "foolhardy"                                            # three sources first
    two = [r for r in t if r["n_sources"] == 2]
    assert all(r["rank"] < min(x["rank"] for x in t if x["n_sources"] == 1) for r in two)
    ones = [r for r in t if r["n_sources"] == 1]
    tiers = [r["tier"] for r in ones]
    assert tiers == sorted(tiers)                                              # pair completions, then fillers, ...
    assert ones[0]["stem"] == "sunny"
    assert [r["rank"] for r in t] == list(range(1, len(t) + 1))


def test_mutation_flipping_every_tag_drops_no_row_and_changes_no_candidate(world, replies):
    t = PP.build_table(replies, _modern(), corpus=world["corpus"], queue=world["queue"], registry=world["registry"],
                       lexicon=LEX)
    flipped = copy.deepcopy(t)
    for r in flipped:
        for k in ("exists", "queued", "is_negative_label", "registered", "registered_decided", "net_new"):
            r[k] = not r[k]
    assert [r["stem"] for r in flipped] == [r["stem"] for r in t]
    a = SU.select_all(t)
    b = SU.select_all(flipped)
    assert [r["stem"] for r in a] == [r["stem"] for r in b]
    assert SU.to_candidates(a, "x") == SU.to_candidates(b, "x")
    # under the wave's cut the filtered-status tags move only the count, and so where the cut ends: every row the
    # walk reaches is selected whatever its tags (a decided row is never dropped), and each count is of its own tags
    # (review S2, 2026-10-13: the assertion here was true by construction)
    sel_a, n_a = SU.select_wave(t, kept_target=2, kept_share=0.5)          # 4 net-new rows wanted
    sel_b, n_b = SU.select_wave(flipped, kept_target=2, kept_share=0.5)
    order = ["foolhardy", "craven", "cowardly", "sunny", "defiant", "brave", "bold"]
    assert [r["stem"] for r in sel_a] == order and n_a == 4 == sum(r["net_new"] for r in sel_a)
    assert [r["stem"] for r in sel_b] == order[:5] + ["rash"] + order[5:] and n_b == 4 == sum(
        r["net_new"] for r in sel_b)                                     # the flipped tags carry the cut one row on
    assert {"foolhardy", "craven"} <= {r["stem"] for r in sel_a}          # decided, not counted, still submitted
    assert not t[0]["net_new"] and flipped[0]["net_new"]


def test_rerun_is_byte_identical_and_snapshots_on_change(world, replies, tmp_path):
    t1 = PP.build_table(replies, _modern(), corpus=world["corpus"], queue=world["queue"], registry=world["registry"],
                        lexicon=LEX)
    t2 = PP.build_table(list(reversed(replies)), list(reversed(_modern())), corpus=world["corpus"],
                        queue=world["queue"], registry=world["registry"], lexicon=LEX)
    assert PP.table_text(t1) == PP.table_text(t2)
    p = tmp_path / "operator_table.jsonl"
    assert PP.write_operator_table(t1, p) is None
    before = p.read_bytes()
    assert PP.write_operator_table(t2, p) is None and p.read_bytes() == before
    assert PP.load_operator_table(p) == json.loads(json.dumps(t1))
    bak = PP.write_operator_table(t1[:-1], p)
    assert bak is not None and bak.read_bytes() == before


def test_collect_replies_last_run_wins(world, tmp_path):
    d1, d2 = tmp_path / "r1", tmp_path / "r2"
    for d, pos in ((d1, "mean"), (d2, "excess")):
        O.append_response({"stage": "operators", "stem": "brave", "label": "brave", "run_id": d.name,
                           "principal_targets": False, "text": F.reply(pos)}, d / "responses.jsonl")
    O.append_response({"stage": "operators", "stem": "obedient", "label": "obedient", "run_id": "r1",
                       "principal_only": True, "principal_targets": True,
                       "text": json.dumps({"reasoning": "r", "retarget": {"the_user": F.item("user-first")}})},
                      d1 / "responses.jsonl")
    col = PP.collect_replies([d1, d2])
    assert col.full["brave"].position == "excess" and col.full["brave"].run_id == "r2"
    assert set(col.principal_only) == {"obedient"}
    assert col.principal_only["obedient"].slot("retarget", "the_user")[0]["label"] == "user-first"
    assert PP.collect_replies([d2, d1]).full["brave"].position == "mean"


def test_frozen_interface():
    from assistant_axis.gapgen.generators.structural import (OPERATOR_TABLE_PATH, POSITION_TABLE_PATH,
                                                             load_operator_table, load_position_table)
    assert OPERATOR_TABLE_PATH.name == "operator_table.jsonl" and POSITION_TABLE_PATH.name == "position_table.jsonl"
    assert callable(load_operator_table) and callable(load_position_table)
