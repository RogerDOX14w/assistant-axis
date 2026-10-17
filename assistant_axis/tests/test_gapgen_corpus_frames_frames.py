"""Corpus-frames generator: the Books frame bank (plan section 8, ``frames``)."""
import dataclasses

import pytest

from assistant_axis.gapgen.generators.corpus_frames import frames as F
from assistant_axis.gapgen.normalize import STOPWORDS


def test_ids_are_unique_and_every_frame_has_one_slot():
    ids = [f.id for f in F.FRAME_BANK]
    assert len(ids) == len(set(ids)) == 45
    for f in F.FRAME_BANK:
        assert f.slot == len(f.prefix) and f.n == len(f.prefix) + 1 + (f.suffix is not None)
        assert f.n in (3, 4) and f.type in F.TYPES and f.tier in F.TIERS and f.filler_kind in F.FILLER_KINDS
        assert f.template.count("X") == 1                               # exactly one slot
        assert F.regex_pattern(f).count("(?P<filler>") == 1


def test_every_type_has_a_tier_1_frame_and_the_tiers_partition_the_bank():
    t1 = F.frames_for(1)
    assert {f.type for f in t1} == set(F.TYPES)
    assert len(t1) == 27 and len(F.frames_for(2)) == 18
    assert {f.id for f in F.frames_for("all")} == {f.id for f in t1} | {f.id for f in F.frames_for("2")}
    with pytest.raises(ValueError):
        F.frames_for(3)


def test_person_nouns_are_the_plans_22():
    assert len(F.PERSON_NOUNS) == 22 and {"neighbor", "neighbour", "master", "youth"} <= F.PERSON_NOUNS


@pytest.mark.parametrize("fid,line,filler,noun", [
    ("d_very", "very honest man\t1921,3,2", "honest", "man"),
    ("d_very", "very good-natured fellow\t1950,4,4", "good-natured", "fellow"),
    ("n_born", "a born story-teller\t1950,4,4", "story-teller", None),
    ("d_too_to", "too clever to\t1950,70,60", "clever", "to"),
    ("p_known_for_his", "known for his honesty\t1950,1,1", "honesty", None),
    ("c_was_a", "was a good man\t1950,1,1", "good", "man"),
    ("t_tendency", "tendency to be jealous\t1950,1,1", "jealous", None),
    ("h_he_was_always", "he was always cheerful\t1950,1,1", "cheerful", None),
])
def test_the_regex_matches_plain_lowercase_fillers(fid, line, filler, noun):
    m = F.regex_for(F.FRAME_BY_ID[fid]).match(line)
    assert m and m.group("filler") == filler and m.groupdict().get("noun") == noun


@pytest.mark.parametrize("fid,line", [
    ("d_very", "very_ADJ sergeant_NOUN\t1950,5,5"),     # a tag on the anchor
    ("d_very", "very leaky _ADV_\t1950,1,1"),           # a wildcard token
    ("d_very", "very Christian man\t1950,1,1"),         # a capital
    ("d_very", "very the man\t1950,1,1"),               # a function word in the slot
    ("d_very", "very honest man_NOUN\t1950,1,1"),       # a tag on the suffix
    ("d_very", "very honest dog\t1950,1,1"),            # not a person noun
    ("d_very", "very honest\t1950,1,1"),                # no suffix
    ("n_born", "a born_ADJ leader\t1950,1,1"),
    ("n_born", "a born leader_NOUN\t1950,1,1"),
    ("d_too_to", "too clever by\t1950,1,1"),
])
def test_the_regex_rejects_tags_wildcards_capitals_and_function_words(fid, line):
    assert F.regex_for(F.FRAME_BY_ID[fid]).match(line) is None


def test_every_function_word_is_refused_in_the_slot():
    rx = F.regex_for(F.FRAME_BY_ID["d_very"])
    for w in sorted(STOPWORDS):
        if "'" not in w:
            assert rx.match(f"very {w} man\t1950,1,1") is None, w


def test_bank_sha_changes_when_a_frame_changes():
    base = F.bank_sha256()
    assert base == F.bank_sha256(F.FRAME_BANK)
    changed = list(F.FRAME_BANK)
    changed[0] = dataclasses.replace(changed[0], note="very X <person noun>, edited")
    assert F.bank_sha256(changed) != base
    changed[0] = dataclasses.replace(F.FRAME_BANK[0], tier=2)
    assert F.bank_sha256(changed) != base
    assert F.bank_sha256(F.FRAME_BANK[1:]) != base


def test_frame_keys_place_the_frame_in_the_shards():
    assert F.FRAME_BY_ID["d_very"].key == "very "
    assert F.FRAME_BY_ID["n_incorrigible"].key == "an incorrigible "
    assert F.FRAME_BY_ID["n_born"].key == "a born "
    assert F.FRAME_BY_ID["p_known_for_his"].key == "known for his " and F.FRAME_BY_ID["p_known_for_his"].n == 4
