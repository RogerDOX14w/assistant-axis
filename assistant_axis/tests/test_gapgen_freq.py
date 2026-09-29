"""gapgen.freq: Zipf floor over content words (1.5 since decision 1, 2026-09-29), bands,
familiarity override.  Rescue rule 1b is tested in test_gapgen_rubric_v2.py."""
import pytest

from assistant_axis.gapgen.freq import FreqInfo, familiarity_of, zipf_info

FAKE = {"kind": 5.5, "animals": 4.6, "world": 6.1, "shaping": 3.4, "rarish": 1.2,
        "abstemious": 2.2, "stubborn": 3.6, "to": 7.4, "xyzzy": 0.0}


def z(w):
    return FAKE.get(w, 0.0)


def test_single_word_bands():
    assert zipf_info("stubborn", zipf_fn=z) == FreqInfo(3.6, {"stubborn": 3.6}, False, False, False, None)
    i = zipf_info("abstemious", zipf_fn=z)
    assert i.probe_band and not i.hard_reject
    i = zipf_info("rarish", zipf_fn=z)
    assert i.hard_reject and not i.probe_band


def test_boundaries():
    assert zipf_info("a", zipf_fn=lambda w: 1.5).probe_band
    assert not zipf_info("a", zipf_fn=lambda w: 1.5).hard_reject
    assert zipf_info("a", zipf_fn=lambda w: 2.0).probe_band
    assert not zipf_info("a", zipf_fn=lambda w: 2.5).probe_band
    assert zipf_info("a", zipf_fn=lambda w: 1.49).hard_reject


def test_phrase_uses_rarest_content_word():
    i = zipf_info("kind to animals", zipf_fn=z)
    assert i.zipf_words == {"kind": 5.5, "animals": 4.6}  # 'to' is a stopword
    assert i.zipf_min == 4.6
    i = zipf_info("world-shaping", zipf_fn=z)
    assert i.zipf_min == 3.4 and set(i.zipf_words) == {"world", "shaping"}


def test_unknown_word_is_hard_reject():
    assert zipf_info("xyzzy", zipf_fn=z).hard_reject


@pytest.mark.parametrize("fam,hard,probe,override", [
    (None, True, False, False), (0.3, True, False, False), (0.5, False, True, True), (0.9, False, True, True),
])
def test_familiarity_override(fam, hard, probe, override):
    i = zipf_info("rarish", familiarity=fam, zipf_fn=z)
    assert (i.hard_reject, i.probe_band, i.familiarity_override) == (hard, probe, override)


def test_familiarity_does_not_touch_common_words():
    i = zipf_info("stubborn", familiarity=0.9, zipf_fn=z)
    assert not i.probe_band and not i.familiarity_override


def test_familiarity_of_documented_generators_only():
    rec = {"sources": [{"generator": "censuses", "score": 0.7}, {"generator": "wordnet_walk", "score": 0.99},
                       {"generator": "censuses", "score": None}]}
    assert familiarity_of(rec) == 0.7
    assert familiarity_of({"sources": [{"generator": "wordnet_walk", "score": 0.99}]}) is None


def test_block_shape():
    b = zipf_info("stubborn", zipf_fn=z).as_block()
    assert set(b) == {"zipf_min", "zipf_words", "hard_reject", "probe_band", "familiarity_override",
                      "rescue", "define_probe"}


def test_real_wordfreq():
    pytest.importorskip("wordfreq")
    i = zipf_info("kind to animals")
    assert i.zipf_min > 3 and "to" not in i.zipf_words
    assert zipf_info("qwxzvbnm").hard_reject
