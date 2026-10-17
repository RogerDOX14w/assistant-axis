"""Corpus-frames generator: the table (plan section 8, ``table``): the floor, the two within-frame orderings, the
fusion, the fold of nouns, eligibility through ``zipf_info``, the tags that drop nothing, determinism, the per-frame
counts and the person-usage lookup."""
import copy

import pytest

from assistant_axis.gapgen import freq
from assistant_axis.gapgen.generators.corpus_frames import frames as F
from assistant_axis.gapgen.generators.corpus_frames import table as T
from assistant_axis.gapgen.generators.corpus_frames import text as X
from assistant_axis.gapgen.generators.corpus_frames.books import Hit
from assistant_axis.tests.corpus_frames_fakes import fake_lookups

FR = {**{f.id: f for f in F.FRAME_BANK}, **{f.id: f for f in X.text_frames()}}


def H(filler, match, volumes, noun=None, example=None):
    return Hit(filler=filler, noun=noun, match=match, volumes=volumes, example=example)


def build(hits, **kw):
    kw.setdefault("lookups", fake_lookups())
    return T.build_table(hits, frames=FR, **kw)


def by_stem(rows):
    return {r["stem"]: r for r in rows}


def test_the_frame_floor():
    rows = build({"d_very": [H("honest", 39, 30, "man")]})
    assert rows == []
    rows = build({"d_very": [H("honest", 40, 30, "man")]})
    assert [r["stem"] for r in rows] == ["honest"]
    # the floor applies to a frame's sum over its nouns (39 + 1 reaches it)
    assert len(build({"d_very": [H("honest", 39, 30, "man"), H("honest", 1, 1, "woman")]})) == 1
    # a text frame's floor is its own (3 occurrences)
    assert [r["stem"] for r in build({"cards.copular_list": [H("honest", 3, 3), H("kind", 2, 2)]})] == ["honest"]


def test_volumes_and_lift_rank_a_common_word_apart():
    rows = by_stem(build({"d_very": [H("good", 4000, 3000, "man"), H("kind", 500, 400, "fellow"),
                                     H("honest", 300, 230, "man"), H("pedantic", 120, 100, "man")]}))
    vol = {s: r["frames"]["d_very"]["rank_volumes"] for s, r in rows.items()}
    lift = {s: r["frames"]["d_very"]["rank_lift"] for s, r in rows.items()}
    assert vol == {"good": 1, "kind": 2, "honest": 3, "pedantic": 4}
    assert lift == {"pedantic": 1, "honest": 2, "kind": 3, "good": 4}      # good: high by volumes, low by lift
    assert rows["good"]["frames"]["d_very"]["lift"] == pytest.approx(round(-0.09460 + 2.5, 4), abs=1e-3)


def test_rrf_fuses_planted_rankings():
    assert T.rrf({"small": {"x": 1}, "big": {"y": 50, "x": 70}}) == pytest.approx({"x": 1 / 61 + 1 / 130,
                                                                                   "y": 1 / 110})
    big = [H(f"w{i:02d}", 1000 - i, 1000 - i, "man") for i in range(49)] + [H("honest", 100, 100, "man")]
    rows = build({"d_very": big, "n_incorrigible": [H("liar", 50, 40)]})
    r = by_stem(rows)
    assert r["honest"]["frames"]["d_very"]["rank_volumes"] == 50
    assert r["liar"]["union_rank"] < r["honest"]["union_rank"]           # rank 1 of a small frame beats rank 50
    assert r["liar"]["rrf"] == pytest.approx(1 / 61) and r["honest"]["rrf"] == pytest.approx(1 / 110)


def test_scale_invariance():
    hits = {"d_very": [H("good", 4000, 3000, "man"), H("kind", 500, 400, "man"), H("honest", 300, 230, "man")],
            "p_known_for_his": [H("honesty", 120, 100), H("kindness", 90, 80)],
            "h_he_was_always": [H("cheerful", 80, 70), H("kind", 60, 50)]}
    doubled = dict(hits)
    doubled["d_very"] = [H(h.filler, 2 * h.match, 2 * h.volumes, h.noun) for h in hits["d_very"]]
    a, b = build(hits), build(doubled)
    for f in ("union_rank", "rank_lift_union"):
        assert {r["stem"]: r[f] for r in a} == {r["stem"]: r[f] for r in b}
    for r in b:
        for k, v in r["frames"].items():
            w = by_stem(a)[r["stem"]]["frames"][k]
            assert (v["rank_volumes"], v["rank_lift"], v["lift"]) == (w["rank_volumes"], w["rank_lift"], w["lift"])


def test_union_rank_ties_by_zipf_then_surface():
    rows = build({"h_he_was_always": [H("cheerful", 80, 70)], "h_she_was_always": [H("jealous", 50, 45)],
                  "t_tendency": [H("clever", 55, 50)], "t_apt": [H("shy", 55, 50)]})
    # every row is rank 1 of one frame: equal RRF, so Zipf (descending) decides, then the surface
    assert [r["stem"] for r in rows] == ["clever", "jealous", "cheerful", "shy"]   # 4.3, 3.9, 3.7, then 3.0
    rows = build({"t_tendency": [H("shy", 55, 50)], "t_apt": [H("bold", 55, 50)]})
    assert [r["stem"] for r in rows] == ["bold", "shy"]                    # equal Zipf: the surface


def test_the_relabel_lands_in_label_and_the_noun_stays_in_surface():
    rows = by_stem(build({"n_incorrigible": [H("pedant", 45, 44), H("liar", 100, 80), H("old", 60, 50)],
                          "d_very": [H("honest", 300, 200, "man")],
                          "p_known_for_his": [H("honesty", 120, 100)]}))
    p = rows["pedantic"]
    assert (p["surface"], p["label"], p["surface_stem"], p["form"], p["relabel_rule"]) == \
        ("pedant", "pedantic", "pedant", "adjective", "derivation")
    assert p["gloss_hint"].startswith("a person who pays more attention")      # the noun's sense: what is submitted
    h = rows["honest"]
    assert h["surface"] == "honest" and h["surface_stem"] == "honest"      # the adjective is attested: submitted
    assert {f["surface"] for f in h["fillers"]} == {"honest", "honesty"} and set(h["frames"]) == {"d_very",
                                                                                                "p_known_for_his"}
    assert h["types"] == ["degree", "possessive"] and h["n_frames"] == 2
    assert rows["liar"]["form"] == "noun" and rows["liar"]["relabel_rule"] == "none"
    assert "old" not in rows                                               # not a person noun, not relabelled
    counts = {}
    build({"n_incorrigible": [H("old", 60, 50), H("liar", 100, 80)]}, counts_out=counts)
    assert counts["n_incorrigible"]["rejected_kind"] == 1


def test_eligibility_through_zipf_info(monkeypatch):
    hits = {"d_very": [H("honest", 300, 200, "man"), H("zorbish", 50, 40, "man"), H("blarg", 50, 40, "man"),
                       H("flirty", 50, 40, "man")]}
    r = by_stem(build(hits))
    assert r["honest"]["eligible"] and not r["honest"]["freq_hard_reject"]
    assert r["zorbish"]["freq_hard_reject"] and r["zorbish"]["eligible"] and r["zorbish"]["gloss_hint"]
    assert r["blarg"]["freq_hard_reject"] and not r["blarg"]["eligible"]
    assert r["blarg"]["ineligible_reason"] == "below_hard_reject"
    assert r["flirty"]["eligible"]                                         # Zipf 3.0: above the floor
    monkeypatch.setattr(freq, "HARD_REJECT_BELOW", 3.5)                   # the platform's floor, not a local literal
    r = by_stem(build(hits))
    assert not r["flirty"]["eligible"] and r["honest"]["eligible"]


def test_no_tag_drops_a_row_or_moves_a_rank():
    hits = {"d_very": [H("good", 4000, 3000, "man"), H("kind", 500, 400, "man"), H("honest", 300, 230, "man")],
            "n_incorrigible": [H("pedant", 45, 44), H("liar", 100, 80)],
            "p_known_for_his": [H("honesty", 120, 100)]}
    plain = build(hits)
    stems = sorted(r["stem"] for r in plain)
    reg = {s: {"generators": ["censuses"], "decided": True, "key": f"{s}#1"} for s in stems + ["pedant"]}
    tagged = build(hits, corpus_stems=stems, queue_stems=stems, registry=reg, renamed={"goodly": "good"})
    assert all(r["corpus_stem_match"] and r["queue_stem_match"] and r["registered"] and r["registered_decided"]
               and not r["net_new"] for r in tagged)
    assert all(not r["registered"] and r["net_new"] for r in plain)
    for f in ("union_rank", "rank_lift_union", "eligible", "rrf"):
        assert {r["stem"]: r[f] for r in plain} == {r["stem"]: r[f] for r in tagged}, f
    flipped = T.tag_rows(copy.deepcopy(tagged))                           # every tag back off
    assert [r["stem"] for r in flipped] == [r["stem"] for r in tagged] and all(r["net_new"] for r in flipped)
    assert by_stem(tagged)["pedantic"]["surface_tags"]["registered_decided"] is True


def test_rerun_is_byte_identical_and_a_change_is_snapshotted(tmp_path):
    hits = {"d_very": [H("good", 4000, 3000, "man"), H("honest", 300, 230, "man")],
            "cards.copular_list": [H("kind", 5, 4, example="She is kind.")]}
    a, b = build(hits), build(hits)
    assert T.table_text(a) == T.table_text(b)
    p = tmp_path / "frames_table.jsonl"
    assert T.write_table(a, p) is None and T.write_table(b, p) is None
    assert not list(tmp_path.glob("*.bak.*"))
    backup = T.write_table(build({"d_very": [H("good", 4000, 3000, "man")]}), p)
    assert backup is not None and backup.exists() and backup.read_text() == T.table_text(a)
    assert T.load_frames_table(backup) == [dict((k, r.get(k)) for k in T.ROW_FIELDS) for r in a]
    assert by_stem(a)["kind"]["frames"]["cards.copular_list"]["example"] == "She is kind."


def test_frame_stats_counts_per_frame():
    hits = {"d_very": [H("good", 4000, 3000, "man"), H("honest", 300, 230, "man"), H("rare", 10, 9, "man")],
            "n_incorrigible": [H("liar", 100, 80), H("old", 60, 50)],
            "cards.trait_list": [H("shy", 4, 4), H("kind", 3, 3)]}
    counts = {}
    rows = build(hits, counts_out=counts, registry={"good": {"generators": ["x"], "decided": False, "key": "good#1"}},
                 corpus_stems=["honest"])
    stats = {s["frame"]: s for s in T.frame_stats(rows, frames={k: FR[k] for k in hits}, counts=counts,
                                                  text_stats={"sources": {"cards": {"n_unique": 7}}})}
    assert list(stats) == ["d_very", "n_incorrigible", "cards.trait_list"]   # the bank's order, Books first
    d = stats["d_very"]
    assert (d["fillers"], d["above_floor"], d["registered_share"], d["corpus_share"]) == (3, 2, 0.5, 0.5)
    assert d["forms"] == {"adjective": 2} and d["source"] == "books" and d["type"] == "degree"
    assert stats["n_incorrigible"]["rejected_kind"] == 1 and stats["n_incorrigible"]["above_floor"] == 1
    assert stats["cards.trait_list"]["documents"] == 7 and stats["cards.trait_list"]["above_floor"] == 2


def test_person_frequency_reads_the_books_frames():
    rows = build({"d_very": [H("honest", 300, 200, "man")], "p_known_for_his": [H("honesty", 120, 100)],
                  "cards.copular_list": [H("honest", 9, 7), H("shy", 4, 4)]})
    pf = T.person_frequency("honest", table=rows)
    assert pf == T.PersonFreq(volumes_total=300, frames={"d_very": 200, "p_known_for_his": 100}, n_frames=2)
    assert T.person_frequency("honesty", table=rows) == pf               # a filler finds its row
    assert T.person_frequency("shy", table=rows) is None                  # text frames only: not Books usage
    assert T.person_frequency("zzz", table=rows) is None


def test_rerank_over_kept_frames_leaves_a_dropped_frames_rows_out():
    rows = build({"d_very": [H("good", 4000, 3000, "man"), H("honest", 300, 230, "man")],
                  "n_incorrigible": [H("liar", 100, 80)]})
    kept = T.rerank_over(rows, ["d_very"])
    assert [r["stem"] for r in kept] == ["good", "honest"] and [r["wave_rank"] for r in kept] == [1, 2]
    assert {r["stem"] for r in T.rerank_over(rows, ["d_very", "n_incorrigible"])} == {"good", "honest", "liar"}


def test_the_frozen_interface_names():
    from assistant_axis.gapgen.generators import corpus_frames as G
    assert G.load_frames_table is T.load_frames_table and G.person_frequency is T.person_frequency
    assert G.TABLE_PATH.name == "frames_table.jsonl" and G.PersonFreq is T.PersonFreq
