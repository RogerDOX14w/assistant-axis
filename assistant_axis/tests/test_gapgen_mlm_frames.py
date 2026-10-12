"""Masked-LM generator, task 1: the frame bank (plan section 8, ``frames``)."""
import re

import pytest

from assistant_axis.gapgen.generators.masked_lm import frames as F
from assistant_axis.gapgen.paths import DATA_DIR


def test_ids_unique_and_one_slot_each():
    ids = [f.id for f in F.ALL_FRAMES]
    assert len(ids) == len(set(ids))
    for f in F.ALL_FRAMES:
        assert f.template.count(F.SLOT) == 1, f.id
        assert f.kind in F.KINDS and f.slot in F.SLOTS and f.register in F.REGISTERS, f.id


def test_bank_size_and_kinds():
    kinds = {k: [f for f in F.FRAME_BANK if f.kind == k] for k in F.KINDS}
    assert 55 <= len(kinds["dispositional"]) <= 70          # "~60 generation frames"
    assert 8 <= len(kinds["state"]) + len(kinds["physical"]) <= 14   # "~10 contrast frames"
    assert kinds["state"] and kinds["physical"] and F.PROBE_FRAMES
    assert all(f.kind == "probe" for f in F.PROBE_FRAMES)
    # the three crossed factors: every register and every slot is represented in the generation bank
    gen = kinds["dispositional"]
    assert {f.register for f in gen} == set(F.REGISTERS) - {"assistant"}
    assert {f.slot for f in gen} == set(F.SLOTS)


def test_every_subject_instantiates_every_frame():
    assert len(F.SUBJECTS) == 10
    for f in F.FRAME_BANK:
        for s in F.SUBJECTS:
            text = F.instantiate(f, s, "<mask>")
            assert text.count("<mask>") == 1 and "{" not in text and "}" not in text, (f.id, s.key, text)
            assert text[:1] == text[:1].upper() or text.startswith(("lol", "tbh")), text


def test_rogers_two_frames():
    hab = F.FRAME_BY_ID["disp_habitually"]
    assert F.instantiate(hab, F.SUBJECT_BY_KEY["he"], "[MASK]") == "He's habitually [MASK]."
    assert hab.kind == "dispositional" and hab in F.generation_frames("all") and hab in F.generation_frames("pilot10")
    assert F.instantiate(hab, F.SUBJECT_BY_KEY["he"], "<mask>", n_masks=2) == "He's habitually <mask><mask>."
    assert "[MASK][MASK]" in F.MULTIWORD_PATTERNS
    assert F.MULTIWORD_PATTERNS["[MASK][MASK]"] == ("first", "free")


def test_probe_frames_carry_assistant_subjects():
    for f in F.PROBE_FRAMES:
        assert f.subjects in (F.PROBE_SUBJECTS, ()), f.id
        assert f.register == "assistant"
    insts = F.instances(F.PROBE_FRAMES, "<mask>")
    assert {i.subject for i in insts} <= {"assistant", "chatbot", None}
    assert len({f.family for f in F.PROBE_FRAMES}) >= 4


def test_probe_frames_never_name_a_probe_label():
    for f in F.PROBE_FRAMES:
        words = set(re.findall(r"[a-z]+", f.template.lower()))
        assert not words & set(F.PROBE_LABELS), f.id


def test_probe_labels_are_corpus_stems():
    for lab in F.PROBE_LABELS:
        assert (DATA_DIR / "traits" / "instructions" / f"{lab}.json").exists(), lab
    assert F.HHH_LABELS == ("helpful", "harmless", "honest")


def test_no_article_directly_before_the_slot():
    for f in F.ALL_FRAMES:
        assert not re.search(r"\b(a|an)\s+\[MASK\]", f.template, re.IGNORECASE), f.id


def test_named_frame_lists_exist():
    for fid in (*F.PILOT_FRAMES, *F.CONTRAST_SET, *F.MULTIWORD_HOSTS, *(f for f, _ in F.VARIANT_B_INSTANCES)):
        assert fid in F.FRAME_BY_ID, fid
    assert len(F.PILOT_FRAMES) == 10 and len(F.VARIANT_B_INSTANCES) == 12
    pilot = [F.FRAME_BY_ID[i] for i in F.PILOT_FRAMES]
    assert len({f.register for f in pilot}) == 6 and {f.slot for f in pilot} == set(F.SLOTS)
    assert {F.FRAME_BY_ID[i].kind for i in F.CONTRAST_SET} == {"dispositional", "state", "physical"}
    assert all(F.FRAME_BY_ID[i].kind == "dispositional" for i, _ in F.VARIANT_B_INSTANCES)


def test_instances_and_spans():
    insts = F.instances(F.generation_frames("pilot10"), "<mask>")
    assert len(insts) == 10 * 10
    assert len(F.instances(F.generation_frames("pilot10"), "<mask>", subjects=["she", "he"])) == 20
    text, a, b = F.instantiate_span(F.FRAME_BY_ID["disp_nature"], F.SUBJECT_BY_KEY["she"], "<mask>",
                                    pattern="[MASK] to [MASK]")
    assert text == "She is <mask> to <mask> by nature." and text[a:b] == "<mask> to <mask>"
    text, a, b = F.instantiate_span(F.FRAME_BY_ID["disp_habitually"], F.SUBJECT_BY_KEY["i"], "<mask>", n_masks=3)
    assert text == "I'm habitually <mask><mask><mask>." and text[a:b] == "<mask>" * 3


def test_alternating_subjects_and_bank_hash():
    pairs = F.alternating_subjects([F.FRAME_BY_ID[i] for i in F.MULTIWORD_HOSTS])
    assert [s for _, s in pairs[:4]] == ["she", "he", "she", "he"]
    assert len(F.bank_sha256()) == 64 and F.bank_sha256() == F.bank_sha256()


def test_frames_arg():
    assert len(F.generation_frames("all")) == len([f for f in F.FRAME_BANK if f.kind == "dispositional"])
    with pytest.raises(ValueError):
        F.generation_frames("pilot5")
