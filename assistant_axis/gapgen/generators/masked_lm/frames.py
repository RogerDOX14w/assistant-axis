"""The frame bank, the subjects, and frame instantiation (plan section 5, ``frames.py``; plan 04 section 3.2).

A :class:`Frame` is a hand-written sentence with one slot, ``[MASK]``, written subject-agnostically: the
placeholders below are filled from each :class:`Subject` (``{S}`` the subject capitalised, ``{s}`` lower case,
``{be}`` is/are/am, ``{be_c}`` the contraction 's/'re/'m, ``{have}``, ``{was}``, ``{poss}``, ``{Poss}``, ``{obj}``,
``{vs}`` the third-person verb ending), so every frame is instantiated with every subject and the she/he
difference of a word is measured rather than guessed (``gender_log_odds``, a kept field and never a gate; Roger,
plan 04 section 9.2).  Three crossed factors, so their bias can be ablated: the **subject** (ten), the
**register** (reference letter, novel narration, performance review, casual review, psychology textbook, chat
transcript), the **syntactic slot** (predicate adjective, attributive adjective, agent noun).

No template puts an article directly before the slot ("a [MASK]" would favour consonant-initial words: "an
idealist" would never fill "a [MASK]"); an adjective or adverb sits between (``test_gapgen_mlm_frames.py``).

Kinds: ``dispositional`` (the generation bank, ~60 frames), ``state`` and ``physical`` (the contrast frames of
the trait-hood score, never used to generate), ``probe`` (the HHH frame search: Roger asked whether a frame
recovers helpful, harmless and honest; the probe frames carry the assistant and chatbot subjects, grouped in
``family``).  Roger's two frames (plan 04 sections 1 and 3.5, 2026-10-10): **"He's habitually [MASK]"**
(``disp_habitually``, subject-agnostic as ``{S}{be_c} habitually [MASK]``, and its two- and three-mask forms in
the subword pass) and the bare **"[MASK][MASK]"** in :data:`MULTIWORD_PATTERNS` (read as the unconstrained
two-slot form inside each host sentence frame, not as a context-free input: pre-registered question 1).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Optional, Sequence

SLOT = "[MASK]"
KINDS = ("dispositional", "state", "physical", "probe")
REGISTERS = ("reference_letter", "novel", "performance_review", "casual_review", "psych_textbook", "chat_transcript",
             "assistant")
SLOTS = ("predicate", "attributive", "agent_noun")


@dataclass(frozen=True)
class Subject:
    key: str
    s: str            # as it stands mid-sentence
    be: str
    be_c: str         # contraction, attached to the subject
    have: str
    was: str
    poss: str
    obj: str
    vs: str           # third-person verb ending ("s" or "")
    gender: Optional[str] = None   # f | m (the she/he log-odds); None otherwise

    @property
    def S(self) -> str:  # noqa: N802 - the template's {S}
        return self.s[:1].upper() + self.s[1:]


SUBJECTS: tuple[Subject, ...] = (
    Subject("she", "she", "is", "'s", "has", "was", "her", "her", "s", "f"),
    Subject("he", "he", "is", "'s", "has", "was", "his", "him", "s", "m"),
    Subject("they", "they", "are", "'re", "have", "were", "their", "them", ""),
    Subject("i", "I", "am", "'m", "have", "was", "my", "me", ""),
    Subject("you", "you", "are", "'re", "have", "were", "your", "you", ""),
    Subject("colleague", "my colleague", "is", "'s", "has", "was", "their", "them", "s"),
    Subject("manager", "the new manager", "is", "'s", "has", "was", "their", "them", "s"),
    Subject("assistant", "this assistant", "is", "'s", "has", "was", "its", "it", "s"),
    Subject("chatbot", "the chatbot", "is", "'s", "has", "was", "its", "it", "s"),
    Subject("character", "the character", "is", "'s", "has", "was", "their", "them", "s"),
)
SUBJECT_BY_KEY = {s.key: s for s in SUBJECTS}
#: The probe frames' subjects (plan section 5: "probe frames carry the assistant/chatbot subjects").
PROBE_SUBJECTS = ("assistant", "chatbot")


@dataclass(frozen=True)
class Frame:
    id: str
    template: str
    slot: str                      # predicate | attributive | agent_noun
    register: str
    kind: str                      # dispositional | state | physical | probe
    family: str = ""               # the probe's frame family (and the register's, by default)
    subjects: Optional[tuple[str, ...]] = None   # None: all ten; (): no subject placeholder; else these keys

    def subject_keys(self) -> tuple[str, ...]:
        if self.subjects is None:
            return tuple(s.key for s in SUBJECTS)
        return tuple(self.subjects)


def _f(id_, template, slot, register, kind="dispositional", family="", subjects=None) -> Frame:
    return Frame(id_, template, slot, register, kind, family or register, subjects)


#: The generation bank (dispositional) and the contrast frames (state, physical).
FRAME_BANK: tuple[Frame, ...] = (
    # predicate adjective: plain dispositional frames
    _f("disp_nature", "{S} {be} [MASK] by nature.", "predicate", "psych_textbook"),
    _f("disp_fundamentally", "{S} {be} fundamentally [MASK].", "predicate", "psych_textbook"),
    _f("disp_habitually", "{S}{be_c} habitually [MASK].", "predicate", "casual_review"),   # Roger's frame
    _f("disp_always", "{S} {have} always been [MASK].", "predicate", "novel"),
    _f("disp_deep_down", "Deep down, {s} {be} [MASK].", "predicate", "novel"),
    _f("disp_known_for", "{S} {be} known for being [MASK].", "predicate", "reference_letter"),
    _f("disp_tends", "{S} tend{vs} to be [MASK].", "predicate", "psych_textbook"),
    _f("disp_comes_across", "{S} come{vs} across as [MASK].", "predicate", "casual_review"),
    _f("disp_at_heart", "At heart, {s} {be} [MASK].", "predicate", "novel"),
    _f("disp_everyone_agrees", "Everyone agrees that {s} {be} [MASK].", "predicate", "casual_review"),
    _f("disp_by_temperament", "By temperament, {s} {be} [MASK].", "predicate", "psych_textbook"),
    _f("disp_rarely_anything_but", "{S} {be} rarely anything but [MASK].", "predicate", "novel"),
    # reference letter
    _f("ref_without_hesitation", "I can say without hesitation that {s} {be} [MASK].", "predicate",
       "reference_letter"),
    _f("ref_colleagues_describe", "Colleagues describe {obj} as [MASK].", "predicate", "reference_letter"),
    _f("ref_above_all", "Above all, {s} {be} [MASK].", "predicate", "reference_letter"),
    _f("ref_strongest_quality", "{Poss} greatest strength is that {s} {be} [MASK].", "predicate", "reference_letter"),
    _f("ref_reliably", "In my experience, {s} {be} reliably [MASK].", "predicate", "reference_letter"),
    _f("ref_unusually_person", "{S} {be} an unusually [MASK] person.", "attributive", "reference_letter"),
    _f("ref_genuinely_colleague", "{S} {be} a genuinely [MASK] colleague.", "attributive", "reference_letter"),
    # novel narration
    _f("nov_had_always", "{S} had always been [MASK], even as a child.", "predicate", "novel"),
    _f("nov_people_said", "People said {s} {was} [MASK].", "predicate", "novel"),
    _f("nov_grew_more", "Over the years {s} grew more [MASK].", "predicate", "novel"),
    _f("nov_something_about", "There was something [MASK] about {obj}.", "attributive", "novel"),
    _f("nov_deeply_individual", "{S} {was} a deeply [MASK] individual.", "attributive", "novel"),
    _f("nov_born", "{S} {was} a born [MASK].", "agent_noun", "novel"),
    _f("nov_true_at_heart", "{S} {was} a true [MASK] at heart.", "agent_noun", "novel"),
    # performance review
    _f("pr_consistently", "{S} {be} consistently [MASK] in {poss} work.", "predicate", "performance_review"),
    _f("pr_attitude", "{S} {have} a consistently [MASK] attitude.", "attributive", "performance_review"),
    _f("pr_needs_less", "{S} need{vs} to be less [MASK].", "predicate", "performance_review"),
    _f("pr_should_more", "{S} should try to be more [MASK].", "predicate", "performance_review"),
    _f("pr_rated", "Team members rated {obj} as highly [MASK].", "predicate", "performance_review"),
    _f("pr_exceptionally_employee", "{S} {be} an exceptionally [MASK] employee.", "attributive",
       "performance_review"),
    _f("pr_natural", "{S} {be} a natural [MASK].", "agent_noun", "performance_review"),
    # casual review
    _f("cas_honestly_so", "Honestly, {s} {be} so [MASK].", "predicate", "casual_review"),
    _f("cas_way_too", "{S}{be_c} way too [MASK] for my taste.", "predicate", "casual_review"),
    _f("cas_pretty_once", "{S}{be_c} pretty [MASK] once you get to know {obj}.", "predicate", "casual_review"),
    _f("cas_super", "{S}{be_c} super [MASK] and I love it.", "predicate", "casual_review"),
    _f("cas_most_people", "{S} {be} one of the most [MASK] people I know.", "attributive", "casual_review"),
    _f("cas_very_person", "{S} {be} a very [MASK] person.", "attributive", "casual_review"),
    _f("cas_hopeless", "{S}{be_c} a hopeless [MASK].", "agent_noun", "casual_review"),
    # psychology textbook
    _f("psy_personality", "{Poss} personality is best described as [MASK].", "predicate", "psych_textbook"),
    _f("psy_stable_part", "Being [MASK] is a stable part of {poss} personality.", "predicate", "psych_textbook"),
    _f("psy_disposition", "{S} {have} a naturally [MASK] disposition.", "attributive", "psych_textbook"),
    _f("psy_temperament", "{S} {have} an essentially [MASK] temperament.", "attributive", "psych_textbook"),
    _f("psy_scores_high", "On personality tests {s} score{vs} as highly [MASK].", "predicate", "psych_textbook"),
    _f("psy_classic", "{S} {be} a classic [MASK] personality type.", "attributive", "psych_textbook"),
    # chat transcript
    _f("chat_why_so", "Why {be} {s} always so [MASK]?", "predicate", "chat_transcript"),
    _f("chat_lol_so", "lol {s}{be_c} so [MASK]", "predicate", "chat_transcript"),
    _f("chat_tbh", "tbh {s} {be} kind of [MASK] sometimes", "predicate", "chat_transcript"),
    _f("chat_never_met", "I have never met anyone as [MASK] as {obj}.", "predicate", "chat_transcript"),
    _f("chat_stop_being", "Can {s} stop being so [MASK] for once?", "predicate", "chat_transcript"),
    _f("chat_typical", "That is such a typically [MASK] thing for {obj} to say.", "attributive", "chat_transcript"),
    # agent nouns (an adjective between article and slot)
    _f("noun_avowed", "{S} {be} an avowed [MASK].", "agent_noun", "reference_letter"),
    _f("noun_committed", "{S} {be} a committed [MASK].", "agent_noun", "psych_textbook"),
    _f("noun_lifelong", "{S} {have} been a lifelong [MASK].", "agent_noun", "novel"),
    _f("noun_incurable", "{S} {be} an incurable [MASK].", "agent_noun", "casual_review"),
    _f("noun_confirmed", "{S} {be} a confirmed [MASK].", "agent_noun", "novel"),
    _f("noun_self_described", "{S} {be} a self-described [MASK].", "agent_noun", "chat_transcript"),
    _f("noun_through_and_through", "{S} {be} a real [MASK] through and through.", "agent_noun", "casual_review"),
    _f("noun_dyed_in_wool", "{S} {be} a dyed-in-the-wool [MASK].", "agent_noun", "reference_letter"),
    # contrast frames: states (transient) and physical descriptions
    _f("state_today", "{S} {be} [MASK] today.", "predicate", "chat_transcript", kind="state"),
    _f("state_right_now", "{S} feel{vs} [MASK] right now.", "predicate", "chat_transcript", kind="state"),
    _f("state_this_morning", "{S} {be} feeling [MASK] this morning.", "predicate", "novel", kind="state"),
    _f("state_after_meeting", "{S} {was} [MASK] after the long meeting.", "predicate", "novel", kind="state"),
    _f("state_at_moment", "At the moment, {s} {be} [MASK].", "predicate", "casual_review", kind="state"),
    _f("phys_looks", "{S} look{vs} [MASK].", "predicate", "casual_review", kind="physical"),
    _f("phys_hair", "{S} {have} [MASK] hair.", "attributive", "novel", kind="physical"),
    _f("phys_physically", "{S} {be} physically [MASK].", "predicate", "psych_textbook", kind="physical"),
    _f("phys_build", "{S} {have} a rather [MASK] build.", "attributive", "novel", kind="physical"),
    _f("phys_in_photos", "In photos, {s} look{vs} [MASK].", "predicate", "casual_review", kind="physical"),
)

#: The HHH probe's candidate frames (Roger, plan 04 section 9.1), in families.  None names any of the nine probe
#: labels, so a frame that recovers them has not been handed them.
PROBE_FRAMES: tuple[Frame, ...] = (
    _f("probe_should_be", "A good AI assistant should be [MASK].", "predicate", "assistant", "probe",
       "assistant_should", ()),
    _f("probe_should_always", "An AI assistant should always be [MASK].", "predicate", "assistant", "probe",
       "assistant_should", ()),
    _f("probe_ideal", "The ideal assistant is [MASK].", "predicate", "assistant", "probe", "assistant_should", ()),
    _f("probe_designed", "{S} {was} designed to be [MASK].", "predicate", "assistant", "probe",
       "assistant_designed", PROBE_SUBJECTS),
    _f("probe_trained", "{S} {was} trained to be [MASK].", "predicate", "assistant", "probe", "assistant_designed",
       PROBE_SUBJECTS),
    _f("probe_built", "{S} {be} built to be [MASK].", "predicate", "assistant", "probe", "assistant_designed",
       PROBE_SUBJECTS),
    _f("probe_always_with_users", "{S} {be} always [MASK] with users.", "predicate", "assistant", "probe",
       "assistant_always", PROBE_SUBJECTS),
    _f("probe_tries", "{S} tries to be [MASK] at all times.", "predicate", "assistant", "probe",
       "assistant_always", PROBE_SUBJECTS),
    _f("probe_users_want", "Users want an assistant that is [MASK].", "predicate", "assistant", "probe",
       "users_want", ()),
    _f("probe_people_trust", "People trust assistants that are [MASK].", "predicate", "assistant", "probe",
       "users_want", ()),
    _f("probe_we_want", "We want our AI models to be [MASK].", "predicate", "assistant", "probe", "users_want", ()),
    _f("probe_above_all", "Above all else, AI systems should be [MASK].", "predicate", "assistant", "probe",
       "principles", ()),
    _f("probe_guidelines", "Our guidelines ask the model to be [MASK].", "predicate", "assistant", "probe",
       "principles", ()),
    _f("probe_safe_model", "A safe language model must be [MASK].", "predicate", "assistant", "probe",
       "principles", ()),
    _f("probe_criticized", "{S} {was} criticized for being too [MASK].", "predicate", "assistant", "probe",
       "criticism", PROBE_SUBJECTS),
    _f("probe_critics_say", "Critics say {s} {be} [MASK] with users.", "predicate", "assistant", "probe",
       "criticism", PROBE_SUBJECTS),
)

#: The HHH probe labels (corpus stems; ``test_gapgen_mlm_frames.py`` checks each has a trait file).
HHH_LABELS: tuple[str, ...] = ("helpful", "harmless", "honest")
PROBE_EXTRA: tuple[str, ...] = ("sycophantic", "obedient", "transparent", "manipulative", "truthful", "deferential")
PROBE_LABELS: tuple[str, ...] = HHH_LABELS + PROBE_EXTRA

#: Pilot A's ten frames (plan section 10): spanning the six registers and the three slots, Roger's frame among them.
PILOT_FRAMES: tuple[str, ...] = ("disp_nature", "disp_habitually", "ref_colleagues_describe", "nov_something_about",
                                 "pr_consistently", "cas_way_too", "psy_personality", "chat_why_so",
                                 "cas_very_person", "noun_avowed")

#: Variant B's twelve scoring instances (frame, subject): predicate, attributive and agent-noun frames (person
#: nouns fit the last), she and he alternating.  Every one is a generation-bank frame.
VARIANT_B_INSTANCES: tuple[tuple[str, str], ...] = (
    ("disp_nature", "she"), ("disp_habitually", "he"), ("disp_always", "she"), ("ref_colleagues_describe", "he"),
    ("cas_very_person", "she"), ("pr_consistently", "he"), ("cas_way_too", "she"), ("psy_personality", "he"),
    ("noun_avowed", "she"), ("noun_committed", "he"), ("noun_incurable", "she"), ("nov_born", "he"))

#: The contrast score's frames (plan 04 section 3.6): dispositional against state and physical.
CONTRAST_DISPOSITIONAL: tuple[str, ...] = ("disp_nature", "disp_fundamentally", "disp_habitually", "disp_always",
                                           "psy_personality", "disp_by_temperament")
CONTRAST_SET: tuple[str, ...] = CONTRAST_DISPOSITIONAL + tuple(f.id for f in FRAME_BANK if f.kind in ("state",
                                                                                                      "physical"))
CONTRAST_SUBJECTS: tuple[str, ...] = ("she", "he")

#: The multiword pass's slot patterns (plan 04 section 3.5), placed in the slot of each host frame, with the
#: constraint on each mask in order: ``first`` (a piece that begins a word), ``cont`` (a continuation piece: the
#: same word goes on), ``free`` (either; a continuation makes one word, a word-start piece a two-word phrase:
#: Roger's bare two-slot form), ``new_word`` (a word-start piece after literal text), ``after_hyphen`` (the
#: piece that follows a hyphen).
MULTIWORD_PATTERNS: dict[str, tuple[str, ...]] = {
    "[MASK][MASK]": ("first", "free"),
    "[MASK]-[MASK]": ("first", "after_hyphen"),
    "[MASK]-[MASK][MASK]": ("first", "after_hyphen", "cont"),
    "[MASK] to [MASK]": ("first", "new_word"),
    "[MASK]ly [MASK]": ("first", "new_word"),
    "[MASK]-oriented": ("first",),
    "[MASK]-seeking": ("first",),
    "[MASK]-minded": ("first",),
}
#: The host frames of the multiword pass: predicate frames, one subject each (she and he alternating).
MULTIWORD_HOSTS: tuple[str, ...] = ("disp_nature", "disp_fundamentally", "disp_habitually", "disp_always",
                                    "disp_known_for", "pr_consistently", "psy_personality", "ref_colleagues_describe",
                                    "chat_why_so", "cas_honestly_so")

ALL_FRAMES: tuple[Frame, ...] = FRAME_BANK + PROBE_FRAMES
FRAME_BY_ID: dict[str, Frame] = {f.id: f for f in ALL_FRAMES}


def generation_frames(which: str = "all") -> list[Frame]:
    """``all``: every dispositional bank frame; ``pilot10``: :data:`PILOT_FRAMES`."""
    gen = [f for f in FRAME_BANK if f.kind == "dispositional"]
    if which == "all":
        return gen
    if which == "pilot10":
        return [FRAME_BY_ID[i] for i in PILOT_FRAMES]
    raise ValueError(f"--frames must be all or pilot10, got {which!r}")


@dataclass(frozen=True)
class Instance:
    """One frame with one subject: the text the model reads (with the model's own mask token)."""
    frame_id: str
    subject: Optional[str]
    text: str
    register: str
    kind: str
    family: str
    slot: str

    def as_dict(self) -> dict:
        return asdict(self)


def instantiate(frame: Frame, subject: Optional[Subject], mask_token: str, n_masks: int = 1,
                pattern: Optional[str] = None) -> str:
    """The frame's text for one subject, its slot replaced by ``n_masks`` adjacent mask tokens (or by a multiword
    ``pattern`` whose ``[MASK]`` markers become mask tokens)."""
    if frame.template.count(SLOT) != 1:
        raise ValueError(f"frame {frame.id} must have exactly one {SLOT}")
    fill = (pattern if pattern is not None else SLOT * int(n_masks)).replace(SLOT, "\0")
    text = frame.template.replace(SLOT, fill)
    if subject is not None:
        text = text.format(S=subject.S, s=subject.s, be=subject.be, be_c=subject.be_c, have=subject.have,
                           was=subject.was, poss=subject.poss, Poss=subject.poss[:1].upper() + subject.poss[1:],
                           obj=subject.obj, vs=subject.vs)
    elif "{" in text:
        raise ValueError(f"frame {frame.id} has subject placeholders but no subject was given")
    return text.replace("\0", mask_token)


def instantiate_span(frame: Frame, subject: Optional[Subject], mask_token: str, n_masks: int = 1,
                     pattern: Optional[str] = None) -> tuple[str, int, int]:
    """:func:`instantiate`, and the character span the slot's fill (masks and any pattern text) occupies."""
    fill = (pattern if pattern is not None else SLOT * int(n_masks))
    marked = Frame(frame.id, frame.template.replace(SLOT, "\x01" + SLOT + "\x02"), frame.slot, frame.register,
                   frame.kind, frame.family, frame.subjects)
    text = instantiate(marked, subject, mask_token, pattern=fill)
    a = text.index("\x01")
    text = text.replace("\x01", "")
    b = text.index("\x02")
    return text.replace("\x02", ""), a, b


def instances(frames: Iterable[Frame], mask_token: str, *, subjects: Optional[Sequence[str]] = None,
              n_masks: int = 1) -> list[Instance]:
    """Every (frame, subject) instance: each frame's own subjects (all ten by default), intersected with
    ``subjects`` when given; a subject-free frame once."""
    out = []
    for f in frames:
        keys = f.subject_keys()
        if subjects is not None and keys:
            keys = tuple(k for k in keys if k in subjects)
        if not keys:
            if f.subjects == ():
                out.append(Instance(f.id, None, instantiate(f, None, mask_token, n_masks), f.register, f.kind,
                                    f.family, f.slot))
            continue
        for k in keys:
            out.append(Instance(f.id, k, instantiate(f, SUBJECT_BY_KEY[k], mask_token, n_masks), f.register,
                                f.kind, f.family, f.slot))
    return out


def pairs_to_instances(pairs: Sequence[tuple[str, str]], mask_token: str) -> list[Instance]:
    """Instances from explicit (frame id, subject key) pairs (variant B)."""
    out = []
    for fid, sk in pairs:
        f = FRAME_BY_ID[fid]
        out.append(Instance(f.id, sk, instantiate(f, SUBJECT_BY_KEY[sk], mask_token), f.register, f.kind, f.family,
                            f.slot))
    return out


def alternating_subjects(frames: Sequence[Frame], subjects: Sequence[str] = ("she", "he")) -> list[tuple[str, str]]:
    """One subject per frame, cycling through ``subjects`` in bank order (the beam passes' instances)."""
    out = []
    for i, f in enumerate(frames):
        keys = f.subject_keys()
        k = subjects[i % len(subjects)]
        out.append((f.id, k if k in keys else (keys[0] if keys else "")))
    return out


def bank_sha256() -> str:
    """A fingerprint of the frames, subjects, patterns and instance lists (recorded in every aggregate)."""
    doc = {"frames": [asdict(f) for f in ALL_FRAMES], "subjects": [asdict(s) for s in SUBJECTS],
           "patterns": MULTIWORD_PATTERNS, "hosts": MULTIWORD_HOSTS, "variant_b": VARIANT_B_INSTANCES,
           "contrast": CONTRAST_SET, "contrast_subjects": CONTRAST_SUBJECTS, "pilot": PILOT_FRAMES,
           "probe_labels": PROBE_LABELS}
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()
