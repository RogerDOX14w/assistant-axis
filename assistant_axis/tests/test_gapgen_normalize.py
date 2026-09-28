"""gapgen.normalize: stems, labels, content words, vocabularies."""
import pytest

from assistant_axis.gapgen.normalize import (
    REGION_VOCAB, TAG_VOCAB, VERDICTS, make_key, normalize_candidate, split_key,
)


@pytest.mark.parametrize("surface,stem,label", [
    ("world-shaping", "world_shaping", "world-shaping"),
    ("kind to animals", "kind_to_animals", "kind to animals"),
    ("  kind   to  animals ", "kind_to_animals", "kind to animals"),
    ("devil's advocate", "devils_advocate", "devil's advocate"),
    ("devil’s advocate", "devils_advocate", "devil's advocate"),
    ("naïve", "naive", "naïve"),
    ("Kantian", "kantian", "Kantian"),
    ("openness (Big Five)", "openness_big_five", "openness (Big Five)"),
    ("self_assured", "self_assured", "self assured"),
    ("well-read.", "well_read", "well-read"),
    ('"stubborn"', "stubborn", "stubborn"),
    ("ends-justify-means", "ends_justify_means", "ends-justify-means"),
])
def test_stem_and_label(surface, stem, label):
    n = normalize_candidate(surface)
    assert n.stem == stem
    assert n.label == label
    assert n.surface_lc == label.lower()


@pytest.mark.parametrize("surface", ["world-shaping", "kind to animals", "naïve", "Kantian",
                                     "devil's advocate", "openness (Big Five)", "well-read."])
def test_idempotent(surface):
    n = normalize_candidate(surface)
    assert normalize_candidate(n.label) == n
    assert normalize_candidate(n.stem).stem == n.stem


def test_content_words_skip_function_words():
    assert normalize_candidate("kind to animals").content_words == ("kind", "animals")
    assert normalize_candidate("world-shaping").content_words == ("world", "shaping")
    assert normalize_candidate("stubborn").content_words == ("stubborn",)
    assert normalize_candidate("devil's advocate").content_words == ("devil's", "advocate")


def test_all_function_words_kept():
    assert normalize_candidate("the one").content_words == ("the", "one")


@pytest.mark.parametrize("bad", ["", "   ", "!!!", "--", "___"])
def test_empty_rejected(bad):
    with pytest.raises(ValueError):
        normalize_candidate(bad)


def test_keys():
    assert make_key("world_shaping") == "world_shaping#1"
    assert make_key("patient", 2) == "patient#2"
    assert split_key("world_shaping#1") == ("world_shaping", 1)


def test_vocabularies():
    assert VERDICTS == ("trait", "tagged", "reject")
    assert len(REGION_VOCAB) == 9 and "alignment_ai_agent" in REGION_VOCAB
    assert {"physical", "state", "role_person", "role_thing", "too_rare"} <= set(TAG_VOCAB)
