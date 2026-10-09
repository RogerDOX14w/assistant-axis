"""The states pass: a separate rubric for words the classifier tagged ``state``.

Open point C of ``reports/trait_gap_generation/decisions_m1.md`` (confirmed by
Roger on 2026-09-29, with one correction): rubric v1's ``transient_only`` tag
folds into ``state``, the classifier sets nothing about plausibility, "and we
do a separate pass with a different rubric for plausibility (my step a),
rather than relying on a rubric that's doing a lot of other things as well to
determine it."  (His words, typing slips corrected.)  His three steps for a
state word (decision 12): "a) figure out if a habitual predisposition to state
is plausible, b) whether the name of the state is still a good name for the
predisposition (or if not, change the stem to that), and [c)] write the
description to describe the habitual predisposition."

Queue prompt v4 (Roger, 2026-10-09) puts a question before those three: **does the state typically last months or
longer, rather than days or weeks?**  "Months yes, weeks-to-months no(ish), though it's a fuzzy borderline.  My mental
model is 'How likely is this to wear off during the course of a narrative?', and my assumption is that narratives that
last weeks in, say, a dozen paragraphs are not that uncommon, while months in a dozen paragraphs is unusual."  A
lasting state drops "states": it is a lasting condition, gets a gloss of the condition itself and goes on like any
trait.  Roger added the same day: "we should probably check states for roles as well, using our standard rule": a
lasting condition is asked whether it is a role, in the kind call's own words (``rubrics/step2_kind.md``), and a role
goes to the ``roles`` holding list, which is read by hand (QUESTIONS 1).  A state that does not last is asked his
three steps as before; when its own name fits, its predisposition gloss is checked ("possibly a keyword scan, backed by
a Haiku call") and the row moves out of the states queue.

Two modes, each with its own prompt and prompt hash:

* ``queue``: rows on the ``states`` holding list (or, for checks, rows of a filter ``results.jsonl`` tagged
  ``state``).  Per row, reason first: ``typical_duration`` (hours, days, weeks, months, years) and ``lasting``; for a
  lasting state ``role`` and a ``gloss`` of the condition; otherwise ``plausible``, ``name_fits``,
  ``suggested_name`` and a ``gloss`` of the predisposition, as in v3.  The row's **route** follows
  (:func:`route_for`):

  ========================  ===============================================  ==========================================
  route                     when                                             what happens
  ========================  ===============================================  ==========================================
  ``role``                  lasting, and a role                              ``holding: "roles"`` (read by hand); no
                                                                             gloss check, no M3
  ``lasting``               lasting, not a role                              gloss checked; if confirmed: alignment
                                                                             call, ``holding: "states_released"``
  ``predisposition``        not lasting, plausible, the name fits            the same
  ``renamed``               not lasting, plausible, another name fits        stays on the states list; the suggested
                                                                             name is submitted as a new candidate
  ``held``                  not lasting and not plausible; a gloss the       stays on the states list, the reason on
                            check rejects; a rename of a rename              the block (``route_reason``)
  ========================  ===============================================  ==========================================

  The coordinator's proposal, which Roger has not objected to (2026-10-09): "move out" means the row leaves the
  states list and goes through M3 and the review app like the physical pass (``novelty_score.py score --holding
  states``), so Roger decides in review; a renamed row's name is a candidate in its own right (generator
  ``states_pass``, run id the states-pass batch, ``source_ref`` the state's key, ``gloss_hint`` the predisposition
  gloss), which goes through M1, M3 and review normally.  A candidate the states pass submitted gets one hop: if M1
  tags it a state again and the pass would rename it once more, it is held ("already a states-pass rename").

  **The gloss check** (:func:`scan_gloss`, then :data:`CHECK_PROMPT`): a keyword scan first.  A gloss with a marker
  for its route (lasting: "for months", "years", "day after day" ...; predisposition: "again and again", "easily",
  "often", "whenever", "any" ...) and none against ("right now", "at the moment", "today", "this morning", "just"
  ...) is accepted by the scan; any other goes to a short Haiku call that reads the sentence as ``lasting``,
  ``predisposition`` or ``passing``, without being told which was meant, and the gloss is confirmed when the
  reading is its route's.  A gloss the check reads otherwise keeps the row on the states list (route ``held``).
  The alignment score is M1's alignment call (``rubrics/alignment.md`` as pinned, on M1's first model, as the
  physical pass sends it) on the confirmed gloss; it is sent beside the check calls, so a gloss the check turns
  down has paid for a score that is not recorded.

* ``corpus``: existing corpus labels that came back tagged ``state``.  Given the label and its corpus description,
  the model says whether the description describes a habitual predisposition or a momentary state.  The default
  assumption, in Roger's words, is that "this has already been done", so the output is a short list of exceptions
  (descriptions read as momentary) for him to look at, not a verdict on the label.  This mode only reads corpus files
  and writes nothing but its own run directory.

The block written on a row (registry field ``states_pass``, or the run's ``results.jsonl``) carries ``mode``,
``rubric_version``, ``model``, ``batch_id``, the answers, ``confidence``, ``prompt_sha256`` and ``at``; in queue mode
from v4 also ``route``, ``route_reason``, ``holding_after``, ``gloss_check`` and the alignment fields.  Changing anything
the model reads here is a rubric change: bump its entry in :data:`RUBRIC_VERSIONS` (or :data:`CHECK_RUBRIC_VERSION`)
and add the pin in ``rubric_versions.HISTORY``.  Example words are checked by the tests never to be corpus labels,
seed-queue entries, validation words, the six September rejects or the reserved words.

Transports (:class:`LiveTransport`, or :class:`assistant_axis.gapgen.batches.BatchTransport` with ``--transport
batches``): every call of a wave goes through one ``execute(wave, calls, on_result)``; the waves are ``queue`` (or
``corpus``), its retry, ``gloss`` (the check and alignment calls) and its retry.  ``resume_records`` (``--resume``) are
the earlier session's responses: a queue row answered there, and a check or alignment request answered there, is not
sent again.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage, cost_for_usage

from .filter_rubric import _bool, _label_key, _load_json, _num, _rows_of, gloss_in_band
from .llm import accepts_temperature, call_anthropic_json
from .normalize import make_key, normalize_candidate
from .registry import utc_now

logger = logging.getLogger(__name__)

#: One version per prompt (round 3, QUESTIONS 17: a version identifies one
#: prompt text; pinned in rubric_versions).  Queue v2: the example "sulking"
#: became "moping", since sulking appears in the "You are X." probe results.
#: Queue v4 (2026-10-09): the duration question, the role question for a lasting state, new examples.
RUBRIC_VERSIONS = {"queue": 4, "corpus": 2}
#: Round 4 (review_rubric_v2.md finding 10): queue v3 drops "listless", "single", "usual" and "usually",
#: validation-file words, from its text; corpus v2 replaces the example "exasperated", a
#: validation-file word, with "vexed", and drops "usually".
#: Haiku 5.5 from 2026-10-08 (coding_plan_haiku55.md, "The switch"); Haiku 4.5
#: (``claude-haiku-4-5-20251001``) stays selectable with ``--model``.  Every block names its model.
DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_BATCH_SIZE = 20
#: 6000 to queue v3; 16000 from v4: in the v4 pilot (states_v4_pilot, 2026-10-09) Haiku 5.5's adaptive thinking took
#: about 500 output tokens a row, and 6 of the 9 twenty-row calls stopped at the 8000 first set (every row was
#: recovered by the half-size retry wave).  Not a prompt change: no version bump.
DEFAULT_MAX_TOKENS = 16000
MODES = ("queue", "corpus")
READINGS = ("predisposition", "momentary")
#: Tags that put a filter row in the states queue (``transient_only`` is
#: rubric v1's, folded into ``state``).
STATE_TAGS = ("state", "transient_only")

#: The states queue's answers about time (queue v4).
DURATIONS = ("hours", "days", "weeks", "months", "years")
LASTING_DURATIONS = ("months", "years")
#: Where a row goes (:func:`route_for`); a row on ``RELEASED_ROUTES`` whose gloss the check confirms leaves the list.
ROUTES = ("role", "lasting", "predisposition", "renamed", "held")
RELEASED_ROUTES = ("lasting", "predisposition")
#: The pass's name in M3 blocks and ``run.json`` (``novelty_score.py score --holding states``), the holding list it
#: reads, the marker a released row carries, and the list a role goes to.
PASS_NAME = "states"
HOLDING = "states"
RELEASED_HOLDING = "states_released"
ROLES_HOLDING = "roles"
#: The generator name of the candidates the pass submits (the ``renamed`` route).
GENERATOR = "states_pass"
#: The reason a second rename is held (one hop).
ONE_HOP_REASON = "already a states-pass rename"
#: The seed-queue tags of a released row promoted by name.
QUEUE_TAG = "states_pass"
ROUTE_TAGS = {"lasting": "lasting_state", "predisposition": "predisposition"}

#: Example words of both prompts, and the names the examples suggest.
QUEUE_EXAMPLES = ("bereaved", "retired", "convalescing", "startled", "wistful")
CORPUS_EXAMPLES = ("fretful", "vexed")
EXAMPLE_WORDS = QUEUE_EXAMPLES + CORPUS_EXAMPLES
SUGGESTED_NAMES = ("jumpy",)

QUEUE_PROMPT = """\
You are helping to build a research corpus of personality traits. Each trait is a label plus a \
one-sentence description, and a persona is prompted to embody it while answering ordinary questions \
in text, so a trait must be something a person can have as a standing way of being, or a condition that \
lasts months or longer, not something that happens to them once.

## Your task
Each candidate below names a state: a condition someone is in for a while (a mood, a reaction, a bodily \
or situational condition). You are given the state's name and a short description of the state. For \
each, reason first, then answer:
1. typical_duration: how long the state typically lasts: "hours" (or less), "days", "weeks", "months" or \
"years".
2. lasting: true when the state typically lasts months or longer. The test is how likely it is to wear \
off in the course of a story: a story told in a dozen paragraphs often spans weeks, but rarely months. So \
a state of weeks, or of weeks to months, is not lasting; a state of months or years is.
3. If lasting is true, answer role and gloss, and set plausible, name_fits and suggested_name to null:
   - role: is the lasting condition a role in this sense: an identity big enough to organize the whole \
persona, so that a person has only one: a profession or calling, an office or official status, a rank so \
high or so low that it rules out most professions, an age so young or so old that it rules out a profession?
   - gloss: one sentence of 20 to 40 words (count them) describing the lasting condition itself: what the \
person's days are like while it lasts, and how it shows in what they do, feel or say.
4. If lasting is false, set role to null and answer:
   - plausible: is a habitual predisposition to this state plausible? That is, could a person be prone to \
falling into it again and again, so that the proneness is part of who they are and would show in how they \
talk? Moods, reactions and emotional or social states mostly allow it. Conditions imposed from outside, or \
purely bodily conditions that no temperament brings about, mostly do not.
   - name_fits: if plausible, is the state's own name still a good name for the predisposition? It is when \
ordinary speakers already use the word for a person who is often that way. If not, give suggested_name: \
the plainest ordinary English name for the predisposition (one word if one exists, otherwise a short \
phrase such as "easily ..." or "prone to ...").
   - gloss: if plausible, one sentence of 20 to 40 words (count them) describing the habitual \
predisposition, not the passing state: what the person habitually does, feels or says.
   If a predisposition is not plausible, set name_fits, suggested_name and gloss to null.
Every gloss begins "This means" followed at once by a verb in the -ing form, and goes straight to the \
behavior, from the inside. No hedges ("tends to", "sometimes", "may"). A vice is described as a vice. US \
spelling.

## Examples (reason first, then the answers)
- "bereaved": grief over a death in the family lasts months or longer, and it combines with any \
profession, so it is no role; typical_duration "months"; lasting true; role false; plausible, name_fits \
and suggested_name null; gloss "This means living, month after month, with the recent death of someone \
close: missing them every day, returning to memories of them, and finding plans and ordinary pleasures \
emptied by the loss."
- "retired": having left paid work for good lasts years and rules out a profession; typical_duration \
"years"; lasting true; role true; plausible, name_fits and suggested_name null; gloss "This means having \
left working life for good: living on a pension and savings, filling the days with chosen pursuits, and \
speaking of one's working years as a finished chapter."
- "convalescing": recovery from an illness takes weeks, at most a few months, so it is not lasting; a \
bodily condition that no temperament brings about; typical_duration "weeks"; lasting false; role null; \
plausible false; name_fits, suggested_name and gloss null.
- "startled": over in moments; some people are startled by every small surprise, and the ordinary name \
for that is jumpy; typical_duration "hours"; lasting false; role null; plausible true; name_fits false; \
suggested_name "jumpy"; gloss "This means reacting to every sudden noise, interruption or unexpected \
question with a jolt of alarm, losing the thread for a moment and needing time to settle again."
- "wistful": a mood of an hour or an afternoon, and people who often feel it are called wistful; \
typical_duration "hours"; lasting false; role null; plausible true; name_fits true; suggested_name null; \
gloss "This means drifting easily into longing for what is gone or out of reach, dwelling on old places \
and chances missed, and letting a soft sadness color how one speaks."

## Output
Respond with one JSON object and nothing else. For every candidate, reason first (at most 30 words), \
then give the answers. Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the candidate>", "reason": "<at most 30 words>", \
"typical_duration": "hours"|"days"|"weeks"|"months"|"years", "lasting": true|false, \
"role": true|false|null, "plausible": true|false|null, "name_fits": true|false|null, \
"suggested_name": "<name>"|null, "gloss": "<sentence>"|null, "confidence": <0-1>}]}
confidence is your probability, between 0 and 1, that lasting and the answer after it (role, or \
plausible) are right. Return one row per candidate id, in the order given.
"""

CORPUS_PROMPT = """\
You are checking entries in a research corpus of personality traits. Each trait is a label plus a \
one-sentence corpus description, and a persona is prompted to embody it in text, so every description \
should describe a standing way of being: a habitual predisposition that a person carries from one day \
to the next.

## Your task
Each label below also names a state, a condition someone can be in for a while. You are given the label \
and its corpus description. Decide which reading the description takes:
- "predisposition": the description describes a habitual or standing tendency to be in, or to fall \
into, the state (how the person mostly is);
- "momentary": the description describes being in the state now, or for a passing spell, with nothing \
that makes it a lasting way of being.
Judge the description as written, not the label on its own. When the description could be read either \
way, choose "predisposition" and say why.

## Examples (reason first, then the reading)
- "fretful", description "This means worrying over small things day after day, turning every plan into \
a list of what could go wrong.": written as a daily habit; reading predisposition.
- "vexed", description "This means being fed up right now with someone who has tried one's \
patience past its limit.": written as a condition of the moment; reading momentary.

## Output
Respond with one JSON object and nothing else. For every label, reason first (at most 30 words), then \
give the reading. Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the label>", "reason": "<at most 30 words>", \
"reading": "predisposition"|"momentary", "confidence": <0-1>}]}
confidence is your probability, between 0 and 1, that the reading is right. Return one row per id, in \
the order given.
"""

#: The gloss check's call (v1, 2026-10-09): one gloss a call, the route it was written for not named.
CHECK_RUBRIC_VERSION = 1
CHECK_READINGS = ("lasting", "predisposition", "passing")
CHECK_PROMPT = """\
You are checking a description written for a research corpus of personality traits. Each trait is a \
label plus a one-sentence description, and a persona is prompted to embody it in text, so a description \
must describe something that stays with the person from one day to the next, not one passing episode.

You are given a label and its description. Say which of three things the description, as written, \
describes:
- "lasting": a condition the person lives in for months or longer, described as going on over that time;
- "predisposition": a habitual proneness: the person falls into a state again and again, or easily, as \
part of who they are;
- "passing": being in a state now, or for one short spell, with nothing in the description that makes it \
last or recur.
Judge the description as written, not the label on its own.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "reading": "lasting"|"predisposition"|"passing"}
"""

PROMPTS = {"queue": QUEUE_PROMPT, "corpus": CORPUS_PROMPT}
PROMPT_SHA256 = {m: hashlib.sha256(p.encode("utf-8")).hexdigest() for m, p in PROMPTS.items()}
CHECK_PROMPT_SHA256 = hashlib.sha256(CHECK_PROMPT.encode("utf-8")).hexdigest()

#: The keyword scan (:func:`scan_gloss`).  Matched as whole words or phrases, case ignored.  A gloss with at least one
#: marker for its route and none against is accepted without a call; any other goes to the check call (the scan
#: never turns a gloss down on its own).
SCAN_FOR = {
    "lasting": ("for months", "for years", "month after month", "year after year", "months", "years", "ongoing",
                "long-term", "for a long time", "day after day", "every day", "each day", "daily"),
    "predisposition": ("again and again", "time after time", "easily", "often", "whenever", "any", "every",
                       "habitually", "always", "readily", "repeatedly", "at the slightest", "constantly"),
}
SCAN_AGAINST = ("right now", "at the moment", "today", "this morning", "this evening", "tonight", "just",
                "for now", "for the moment", "momentarily", "briefly", "a few hours", "a few days")


# ---------------------------------------------------------------------------
# prompts and parsing
# ---------------------------------------------------------------------------

def build_batch_prompt(items: Sequence[dict], mode: str) -> str:
    """User message: one JSON line per item, ``{"id", "label", "state_description"}``
    (queue) or ``{"id", "label", "corpus_description"}`` (corpus)."""
    key = "state_description" if mode == "queue" else "corpus_description"
    lines = [json.dumps({"id": int(it["id"]), "label": it["label"],
                         key: " ".join(str(it.get("text") or "").split()) or None}, ensure_ascii=False)
             for it in items]
    what = "states" if mode == "queue" else "labels"
    return f"Judge these {len(items)} {what}. Reason first, then answer, for each.\n" + "\n".join(lines)


def build_check_prompt(label: str, gloss: str) -> str:
    """User message of the gloss check: the label and the gloss, nothing about the route it was written for."""
    return json.dumps({"label": label, "description": " ".join(str(gloss).split())}, ensure_ascii=False)


def _str_or_none(v) -> Optional[str]:
    if isinstance(v, str):
        v = " ".join(v.split())
        return v if v and v.lower() not in ("null", "none") else None
    return None


def validate_queue_row(row: dict, expected_label: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    """A queue-mode row (v4): ``typical_duration`` and ``lasting`` are required.  Lasting: ``role`` and ``gloss``
    are required, the predisposition answers dropped.  Not lasting: ``plausible`` is required; when true,
    ``name_fits`` and ``gloss`` are, and ``suggested_name`` when the name does not fit; when false, the other
    answers are dropped; ``role`` is dropped.  ``duration_agrees`` records whether ``lasting`` matches the duration
    (months or years); a mismatch is the borderline Roger called fuzzy and is kept, not refused."""
    if not isinstance(row, dict):
        return None, "row is not an object"
    if expected_label is not None and _label_key(row.get("label")) != _label_key(expected_label):
        return None, f"label echo {row.get('label')!r} does not match {expected_label!r}"
    reason = _str_or_none(row.get("reason"))
    if reason is None:
        return None, "reason missing"
    duration = str(row.get("typical_duration") or "").strip().lower()
    if duration not in DURATIONS:
        return None, f"typical_duration {row.get('typical_duration')!r} not in {DURATIONS}"
    lasting = _bool(row.get("lasting"))
    if lasting is None:
        return None, f"lasting {row.get('lasting')!r} is not a boolean"
    conf = _num(row.get("confidence"), 0.0, 1.0)
    if conf is None:
        return None, "confidence missing or out of range"
    role = plausible = name_fits = suggested = gloss = None
    if lasting:
        role = _bool(row.get("role"))
        if role is None:
            return None, "role missing for a lasting condition"
        gloss = _str_or_none(row.get("gloss"))
        if gloss is None:
            return None, "gloss missing for a lasting condition"
    else:
        plausible = _bool(row.get("plausible"))
        if plausible is None:
            return None, f"plausible {row.get('plausible')!r} is not a boolean"
        if plausible:
            name_fits = _bool(row.get("name_fits"))
            if name_fits is None:
                return None, "name_fits missing for a plausible predisposition"
            suggested = _str_or_none(row.get("suggested_name")) if not name_fits else None
            if not name_fits and suggested is None:
                return None, "suggested_name missing although the name does not fit"
            gloss = _str_or_none(row.get("gloss"))
            if gloss is None:
                return None, "gloss missing for a plausible predisposition"
    stem = None
    if suggested is not None:
        try:
            stem = normalize_candidate(suggested).stem
        except ValueError as exc:
            return None, f"suggested_name unusable: {exc}"
    return {"label": row.get("label"), "reason": reason, "typical_duration": duration, "lasting": lasting,
            "duration_agrees": lasting == (duration in LASTING_DURATIONS), "role": role, "plausible": plausible,
            "name_fits": name_fits, "suggested_name": suggested, "suggested_stem": stem, "gloss": gloss,
            "gloss_in_band": gloss_in_band(gloss) if gloss else None, "confidence": float(conf)}, None


def validate_corpus_row(row: dict, expected_label: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    if not isinstance(row, dict):
        return None, "row is not an object"
    if expected_label is not None and _label_key(row.get("label")) != _label_key(expected_label):
        return None, f"label echo {row.get('label')!r} does not match {expected_label!r}"
    reason = _str_or_none(row.get("reason"))
    if reason is None:
        return None, "reason missing"
    reading = str(row.get("reading") or "").strip().lower()
    if reading not in READINGS:
        return None, f"reading {row.get('reading')!r} not in {READINGS}"
    conf = _num(row.get("confidence"), 0.0, 1.0)
    if conf is None:
        return None, "confidence missing or out of range"
    return {"label": row.get("label"), "reason": reason, "reading": reading, "confidence": float(conf)}, None


def parse_batch(text: str, ids: Sequence[int], *, mode: str, labels: Optional[Mapping[int, str]] = None
                ) -> tuple[dict[int, dict], dict[int, str]]:
    """``(rows, errors)`` as :func:`assistant_axis.gapgen.filter_rubric.parse_batch`."""
    validate = validate_queue_row if mode == "queue" else validate_corpus_row
    want = [int(i) for i in ids]
    try:
        raw = _rows_of(_load_json(text))
    except (ValueError, json.JSONDecodeError) as exc:
        return {}, {i: f"unparseable response: {exc}" for i in want}
    rows: dict[int, dict] = {}
    errors: dict[int, str] = {}
    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = _num(r.get("id"), float("-inf"), float("inf"), integer=True)
        if rid is None or rid not in want or rid in rows:
            continue
        ok, err = validate(r, (labels or {}).get(rid) if labels is not None else None)
        if ok is None:
            errors[rid] = err
        else:
            rows[rid] = ok
            errors.pop(rid, None)
    for i in want:
        if i not in rows and i not in errors:
            errors[i] = "missing"
    return rows, errors


def parse_check(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """The gloss check's answer: ``({"reason", "reading"}, None)`` or ``(None, error)``.  A ``{"results": [...]}``
    wrapper is read too."""
    if not text:
        return None, "empty response"
    try:
        obj = _load_json(text)
    except (ValueError, json.JSONDecodeError) as exc:
        return None, f"unparseable response: {exc}"
    if isinstance(obj, dict) and isinstance(obj.get("results"), list) and obj["results"]:
        obj = obj["results"][0]
    if isinstance(obj, list) and obj:
        obj = obj[0]
    if not isinstance(obj, dict):
        return None, "answer is not an object"
    reason = _str_or_none(obj.get("reason"))
    if reason is None:
        return None, "reason missing"
    reading = str(obj.get("reading") or "").strip().lower()
    if reading not in CHECK_READINGS:
        return None, f"reading {obj.get('reading')!r} not in {CHECK_READINGS}"
    return {"reason": reason, "reading": reading}, None


# ---------------------------------------------------------------------------
# routes and the gloss check
# ---------------------------------------------------------------------------

def _name_key(name: str) -> str:
    """A name compared for renames: case, surrounding whitespace, and
    hyphen/space differences ignored (``job-satisfied`` == ``Job satisfied``)."""
    return " ".join(str(name).strip().lower().replace("-", " ").split())


def is_name_unchanged(label: str, suggested: str) -> bool:
    """True when a suggested name is the label itself under :func:`_name_key`.
    Spelling variants (``agonising`` / ``agonizing``) are not detected."""
    return _name_key(label) == _name_key(suggested)


def route_for(answers: Mapping, *, label: str, from_states_pass: bool = False) -> tuple[str, Optional[str]]:
    """``(route, reason)`` for a v4 queue answer, before the gloss check (which can still hold a ``lasting`` or
    ``predisposition`` row).  ``from_states_pass``: the row is a candidate the states pass itself submitted (one
    hop: a second rename is held)."""
    if answers.get("lasting"):
        return ("role", None) if answers.get("role") else ("lasting", None)
    if not answers.get("plausible"):
        return "held", "not lasting, and no habitual predisposition is plausible"
    sug = answers.get("suggested_name")
    if answers.get("name_fits") or not sug or is_name_unchanged(label, sug):
        return "predisposition", None
    if from_states_pass:
        return "held", ONE_HOP_REASON
    return "renamed", None


def holding_after(route: str) -> str:
    """The row's ``holding`` once its route is final (``held`` and ``renamed`` stay on the states list)."""
    if route in RELEASED_ROUTES:
        return RELEASED_HOLDING
    if route == "role":
        return ROLES_HOLDING
    return HOLDING


def _phrase_re(phrase: str) -> re.Pattern:
    return re.compile(r"(?<![a-z])" + re.escape(phrase.lower()) + r"(?![a-z])")


_SCAN_FOR_RE = {k: [(p, _phrase_re(p)) for p in v] for k, v in SCAN_FOR.items()}
_SCAN_AGAINST_RE = [(p, _phrase_re(p)) for p in SCAN_AGAINST]


def scan_gloss(gloss: Optional[str], kind: str) -> dict:
    """The keyword scan of a gloss written for route ``kind`` (``lasting`` or ``predisposition``):
    ``{"kind", "for", "against", "verdict"}``, where ``verdict`` is ``pass`` (a marker for, none against) or
    ``unclear`` (anything else: the check call decides)."""
    if kind not in SCAN_FOR:
        raise ValueError(f"the scan reads {tuple(SCAN_FOR)} glosses, not {kind!r}")
    t = " ".join(str(gloss or "").lower().split())
    hits_for = [p for p, rx in _SCAN_FOR_RE[kind] if rx.search(t)]
    hits_against = [p for p, rx in _SCAN_AGAINST_RE if rx.search(t)]
    return {"kind": kind, "for": hits_for, "against": hits_against,
            "verdict": "pass" if hits_for and not hits_against else "unclear"}


# ---------------------------------------------------------------------------
# reading a registry row (M3, the review graph, promotion)
# ---------------------------------------------------------------------------

def block_of(row: Mapping) -> dict:
    return dict(row.get("states_pass") or {})


def is_released(row: Mapping) -> bool:
    """A row the states pass moved out of the states queue: on the released list, with a released route and a gloss
    the check confirmed."""
    b = block_of(row)
    return (row.get("holding") == RELEASED_HOLDING and b.get("route") in RELEASED_ROUTES
            and bool((b.get("gloss_check") or {}).get("accepted")) and bool(b.get("gloss")))


def gloss_of(row: Mapping) -> Optional[str]:
    """A released row's gloss (the states pass's), else None."""
    if not is_released(row):
        return None
    g = block_of(row).get("gloss")
    return g.strip() if isinstance(g, str) and g.strip() else None


def alignment_of(row: Mapping) -> Optional[int]:
    a = block_of(row).get("alignment")
    return a if isinstance(a, int) and not isinstance(a, bool) else None


def route_of(row: Mapping) -> Optional[str]:
    return block_of(row).get("route")


def candidate_from_row(row: Mapping):
    """``(M3Candidate, None)`` for a row the states pass released, else ``(None, why)``: ``not_filtered``,
    ``not_on_states_released_list``, ``no_gloss``.  The gloss and alignment score are the states pass's (alignment
    None when its call failed: the near-alignment cut-off, as for a trait row); the region is M1's (null for a
    states row)."""
    from .novelty_runner import M3Candidate
    if not row.get("filter"):
        return None, "not_filtered"
    if row.get("holding") != RELEASED_HOLDING:
        return None, f"not_on_{RELEASED_HOLDING}_list"
    g = gloss_of(row)
    if g is None:
        return None, "no_gloss"
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    return M3Candidate(key=row["key"], stem=row["stem"], label=row["label"], gloss=g, alignment_score=alignment_of(row),
                       region=(row.get("filter") or {}).get("region"), generators=gens), None


def card_tag(row: Mapping) -> Optional[str]:
    """The review card's chip for a released row: where it came from (``states pass: lasting (months)``)."""
    if not is_released(row):
        return None
    b = block_of(row)
    d = b.get("typical_duration")
    return f"states pass: {b['route']}" + (f" ({d})" if d else "")


def queue_entry_extras(entry: dict, rec: Mapping) -> dict:
    """A released row's seed-queue entry (``promote.queue_entry_from_record``'s), made a states-pass entry in place:
    the tags ``states_pass`` and ``lasting_state`` or ``predisposition``, the pass's gloss as ``description_draft``
    when the row has none of its own, a note saying how it came, and ``gap_gen.states_pass``."""
    b = block_of(rec)
    route = b.get("route")
    entry["tags"] = list(dict.fromkeys(list(entry.get("tags") or []) + [QUEUE_TAG, ROUTE_TAGS[route]]))
    if not entry.get("description_draft"):
        entry["description_draft"] = gloss_of(rec)
    nv = rec.get("novelty") or {}
    via = f", M3 {nv['run_id']}" if nv.get("pass") == PASS_NAME and nv.get("run_id") else ""
    what = ("a lasting condition" if route == "lasting" else "a habitual predisposition under the state's own name")
    chk = b.get("gloss_check") or {}
    note = (f"states pass v{b.get('rubric_version')} ({b.get('batch_id')}{via}): moved out of the states queue as "
            f"{what}; typical duration {b.get('typical_duration')}; gloss confirmed by the {chk.get('by')}; "
            f"promoted by name: {b.get('reason')}")
    entry["description_notes"] = " | ".join(x for x in (note, entry.get("description_notes")) if x)
    entry.setdefault("gap_gen", {})["states_pass"] = {"route": route, "typical_duration": b.get("typical_duration"),
                                                      "batch_id": b.get("batch_id"),
                                                      "rubric_version": b.get("rubric_version")}
    return entry


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

@dataclass
class StatesItem:
    key: str
    label: str
    text: Optional[str]            # the state's gloss (queue) or the corpus description (corpus)
    meta: dict = field(default_factory=dict)


@dataclass
class StatesResult:
    key: str
    label: str
    stage: str                     # judged | failed | pending
    block: Optional[dict] = None
    meta: dict = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


def is_state_row(filter_block: Optional[dict]) -> bool:
    return bool(set((filter_block or {}).get("tags") or []) & set(STATE_TAGS))


def state_text(row: dict) -> Optional[str]:
    """The text the states pass reads for a row: the filter's gloss, or, for a row of the split
    filter (which writes no gloss for a word on the states list), the accepted reading
    (``filter.judged_sense``)."""
    return row.get("gloss") or (row.get("filter") or {}).get("judged_sense")


def items_from_filter_results(rows: Sequence[dict], *, stratum: Optional[str] = None) -> list[StatesItem]:
    """Rows of a filter ``results.jsonl`` whose filter block carries ``state``
    (or v1's ``transient_only``), optionally of one validation stratum.  The
    item text is the filter's gloss of the state, or the split filter's
    accepted reading when the row has no gloss (:func:`state_text`)."""
    out = []
    for r in rows:
        if not is_state_row(r.get("filter")):
            continue
        if stratum is not None and (r.get("meta") or {}).get("stratum") != stratum:
            continue
        out.append(StatesItem(key=r["key"], label=r["label"], text=state_text(r),
                              meta={"stratum": (r.get("meta") or {}).get("stratum"),
                                    "filter_verdict": (r.get("filter") or {}).get("verdict")}))
    return out


def from_states_pass(row: Mapping) -> bool:
    """True for a row the states pass submitted (a source of generator :data:`GENERATOR`)."""
    return any(s.get("generator") == GENERATOR for s in row.get("sources") or [])


def items_from_registry(records: Sequence[dict]) -> list[StatesItem]:
    """Registry rows on the ``states`` holding list.  ``meta.from_states_pass`` marks a row the pass itself
    submitted (the one-hop rule)."""
    return [StatesItem(key=r["key"], label=r["label"], text=state_text(r),
                       meta={"from_states_pass": from_states_pass(r)}) for r in records
            if r.get("holding") == HOLDING]


def corpus_items(names: Sequence[str], data_dir: Path) -> tuple[list[StatesItem], dict[str, str]]:
    """Corpus-check items for trait labels or stems, read from
    ``<data_dir>/traits/instructions/<stem>.json`` (read only).  Returns
    ``(items, missing)``; ``missing`` maps a name to why it was skipped."""
    items, missing = [], {}
    for name in names:
        stem = normalize_to_file_name(name)
        path = Path(data_dir) / "traits" / "instructions" / f"{stem}.json"
        if not path.exists():
            missing[name] = f"no corpus trait file {path.name}"
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        desc = d.get("description")
        if not desc:
            missing[name] = "corpus file has no description"
            continue
        items.append(StatesItem(key=stem, label=d.get("positive_label") or name, text=desc,
                                meta={"corpus_file": f"traits/instructions/{path.name}"}))
    return items, missing


# ---------------------------------------------------------------------------
# calls and transports
# ---------------------------------------------------------------------------

_CID_RE = re.compile(r"[^A-Za-z0-9_-]")
CHARS_PER_TOKEN = 3.6
#: Output tokens a call is estimated at: per row of a queue or corpus call (plus a margin), a check call.  Queue:
#: measured on the v4 pilot's ten-row retry calls (3,000 to 5,750 tokens, thinking included).
OUT_TOK_PER_ROW = {"queue": 500, "corpus": 50}
OUT_TOK_MARGIN = 300
CHECK_OUT_TOK = 400
#: ``max_tokens`` of the check call: M1's thinking allowance on a model that refuses a temperature, else 300.
CHECK_MAX_TOKENS_THINKING = 2000
CHECK_MAX_TOKENS = 300


@dataclass
class Call:
    """One API call of the states pass."""
    step: str                 # queue | corpus | check | alignment
    key: str                  # check and alignment: the row's key; queue and corpus: the chunk's id
    model: str
    system: str
    user: str
    max_tokens: int
    temperature: Optional[float]
    cache_system: bool = True
    cache_ttl: Optional[str] = None
    items: tuple = ()         # queue and corpus: ({"key", "label", "text"}, ...) in the order sent (id i is items[i-1])
    retry: bool = False

    @property
    def prompt_sha256(self) -> str:
        return hashlib.sha256(self.system.encode("utf-8")).hexdigest()

    @property
    def custom_id(self) -> str:
        """``<step>-<key>-<hash>``: within the Message Batches limit of 64 characters from ``[A-Za-z0-9_-]``."""
        h = hashlib.sha256(f"{self.step}|{self.key}|{self.retry}|{self.user}".encode("utf-8")).hexdigest()[:12]
        return f"{self.step[:3]}-{_CID_RE.sub('_', self.key)[:36]}-{h}"

    def cache_key(self) -> tuple[str, str, str, str]:
        return (self.step, self.prompt_sha256, self.model, self.user)


def call_tokens(c: Call) -> tuple[int, int]:
    """Estimated ``(input, output)`` tokens of one call."""
    i = int((len(c.system) + len(c.user)) / CHARS_PER_TOKEN)
    if c.step in OUT_TOK_PER_ROW:
        return i, OUT_TOK_PER_ROW[c.step] * len(c.items) + OUT_TOK_MARGIN
    if c.step == "alignment":
        from . import split_runner as SR
        return i, SR.tokens_for("alignment", c.model)[1]
    return i, CHECK_OUT_TOK


class LiveTransport:
    """Sends a wave's calls through the Messages API, ``runner.concurrency`` at a time; a budget stop keeps the
    answer that crossed the cap and sends nothing more."""
    name = "live"

    def __init__(self, runner: "StatesPassRunner"):
        self.runner = runner

    async def execute(self, wave: str, calls: Sequence[Call], on_result: Callable) -> None:
        r = self.runner
        sem = asyncio.Semaphore(max(1, int(r.concurrency)))

        async def one(c: Call) -> None:
            if r._stop is not None:
                return
            async with sem:
                if r._stop is not None:
                    return
                meta: dict = {}
                try:
                    text = await call_anthropic_json(
                        r.client, system=c.system, user=c.user, model=c.model, max_tokens=c.max_tokens,
                        temperature=c.temperature, usage=r.usage, limiter=r.limiter, cache_system=c.cache_system,
                        cache_ttl=c.cache_ttl, meta=meta, **r.retry_kw)
                except BudgetExceededError as exc:
                    text = meta.get("text")
                    if r._stop is None:
                        r._stop = exc
            meta["charged_as"] = c.model if meta.get("usage_raw") else None
            on_result(c, text, meta)

        await asyncio.gather(*(one(c) for c in calls))


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _chunks(seq: Sequence, n: int) -> list[list]:
    return [list(seq[i:i + n]) for i in range(0, len(seq), n)]


#: M1's first model, on which the alignment call runs (``physical_pass.MODEL``; checked equal by the tests).
ALIGNMENT_MODEL = "claude-haiku-5-5"


class StatesPassRunner:
    """One states-pass run.  Each response is recorded (and appended to ``responses_path`` as it returns) before it
    is parsed; rows that fail validation are retried once in a follow-up wave (in chunks of half the batch size), and
    a check or alignment call that fails once is asked again once.  A guarded ``usage`` that raises
    ``BudgetExceededError`` stops new calls; every response and every finished row is kept in ``responses`` /
    ``results`` and the error propagates from :meth:`run`.

    Queue mode (v4) runs the whole route: the queue wave(s), the routes, the keyword scan, then one ``gloss`` wave
    with the check call of every gloss the scan did not pass and (``align``) the alignment call of every gloss of a
    ``lasting`` or ``predisposition`` row.  A row whose route is final gets its block (stage ``judged``); a row whose
    queue answer or gloss check never came is ``failed`` (no block), and one cut short by a stop is ``pending``."""

    def __init__(self, *, client, batch_id: str, mode: str, model: str = DEFAULT_MODEL,
                 usage: Optional[MultiModelUsage] = None, limiter=None, batch_size: int = DEFAULT_BATCH_SIZE,
                 concurrency: int = 4, max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = 0.0,
                 retry_delays: Optional[Sequence[float]] = None, responses_path: Optional[Path] = None,
                 transport: Any = None, align: bool = True, alignment_model: str = ALIGNMENT_MODEL,
                 resume_records: Sequence[Mapping] = (), rubrics_dir: Optional[Path] = None,
                 close_client: bool = False):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
        self.client = client
        self.batch_id = batch_id
        self.mode = mode
        self.model = model
        self.usage = usage if usage is not None else MultiModelUsage()
        self.limiter = limiter
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.retry_kw = {} if retry_delays is None else {"retry_delays": tuple(retry_delays)}
        self.responses_path = Path(responses_path) if responses_path is not None else None
        self.transport = transport if transport is not None else LiveTransport(self)
        self.align = bool(align) and mode == "queue"
        self.alignment_model = alignment_model
        self.rubrics_dir = rubrics_dir
        self.close_client = close_client
        self._alignment_pins: Optional[dict] = None
        self.results: dict[str, StatesResult] = {}
        self.responses: list[dict] = [dict(r) for r in resume_records]
        self.stats = Counter()
        self._stop: Optional[BaseException] = None
        # resume: queue / corpus rows answered by the earlier session, by (key, label, text); check and alignment
        # answers by request
        self._row_cache: dict[tuple, dict] = {}
        self._call_cache: dict[tuple, str] = {}
        for rec in resume_records:
            self._remember(rec)

    @property
    def system_prompt(self) -> str:
        return PROMPTS[self.mode]

    @property
    def alignment_pins(self) -> dict:
        """M1's pins of the alignment prompt (``physical_pass.pins``; a ``ValueError`` when the text on disk is not
        its latest pin)."""
        if self._alignment_pins is None:
            from . import physical_pass as PP
            self._alignment_pins = PP.pins(self.rubrics_dir)
        return self._alignment_pins

    # -- records -----------------------------------------------------------------
    def _remember(self, rec: Mapping) -> None:
        step, text = rec.get("step") or rec.get("mode"), rec.get("text")
        if text is None:
            return
        if step in MODES and step == self.mode:
            if rec.get("prompt_sha256") not in (None, PROMPT_SHA256[self.mode]) or rec.get("model") != self.model:
                return
            items = rec.get("items") or []
            rows, _ = parse_batch(text, list(range(1, len(items) + 1)), mode=self.mode,
                                  labels={i + 1: it["label"] for i, it in enumerate(items)})
            for i, row in rows.items():
                it = items[i - 1]
                self._row_cache[(it["key"], it["label"], it.get("text"))] = row
        elif step in ("check", "alignment") and not rec.get("parse_error"):
            self._call_cache[(step, rec.get("prompt_sha256"), rec.get("model"), rec.get("user"))] = text

    def _record(self, rec: dict) -> None:
        self.responses.append(rec)
        if self.responses_path is not None:
            self.responses_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # -- estimate ----------------------------------------------------------------
    def estimate_usd(self, calls: Sequence[Call], *, batch: bool = False) -> float:
        suffix = BATCH_SUFFIX if batch else ""
        return sum(cost_for_usage(c.model + suffix, *call_tokens(c)) for c in calls)

    # -- calls -------------------------------------------------------------------
    def _rows_call(self, items: Sequence[StatesItem], n: int, *, retry: bool = False) -> Call:
        payload = [{"id": i + 1, "label": it.label, "text": it.text} for i, it in enumerate(items)]
        return Call(step=self.mode, key=f"{'r' if retry else 'c'}{n:03d}", model=self.model, system=self.system_prompt,
                    user=build_batch_prompt(payload, self.mode), max_tokens=self.max_tokens,
                    temperature=self.temperature, cache_system=True,
                    items=tuple({"key": it.key, "label": it.label, "text": it.text} for it in items), retry=retry)

    def check_call(self, key: str, label: str, gloss: str) -> Call:
        mt = CHECK_MAX_TOKENS if accepts_temperature(self.model) else CHECK_MAX_TOKENS_THINKING
        return Call(step="check", key=key, model=self.model, system=CHECK_PROMPT, user=build_check_prompt(label, gloss),
                    max_tokens=mt, temperature=self.temperature, cache_system=False)

    def alignment_call(self, key: str, label: str, gloss: str) -> Call:
        from . import physical_pass as PP
        q = PP.request("alignment", label=label, text=gloss, model=self.alignment_model, rubrics_dir=self.rubrics_dir)
        return Call(step="alignment", key=key, model=q["model"], system=q["system"], user=q["user"],
                    max_tokens=q["max_tokens"], temperature=q["temperature"], cache_system=q["cache_system"])

    # -- one wave ----------------------------------------------------------------
    async def _wave(self, wave: str, calls: Sequence[Call], handle: Callable[[Call, Optional[str], dict], None]) -> None:
        """Send ``calls`` (those with no answer on record); every answer goes to ``handle``.  An error the transport
        raises (a budget stop, a failed batch) is kept as the stop, raised by :meth:`run_async` once the answers in
        hand are applied."""
        if not calls or self._stop is not None:
            return
        self.stats[f"calls_{wave}"] += len(calls)

        def on_result(c: Call, text: Optional[str], meta: Mapping) -> None:
            handle(c, text, dict(meta), wave=wave)
        try:
            await self.transport.execute(wave, list(calls), on_result)
        except BaseException as exc:  # noqa: BLE001 - kept as the stop
            if self._stop is None:
                self._stop = exc

    def _base_record(self, c: Call, text: Optional[str], meta: Mapping, wave: str) -> dict:
        return {"batch_id": self.batch_id, "stage": wave, "step": c.step, "mode": self.mode, "model": c.model,
                "key": c.key, "keys": [it["key"] for it in c.items] if c.items else [c.key],
                "items": list(c.items) if c.items else None, "user": c.user, "prompt_sha256": c.prompt_sha256,
                "request": {"max_tokens": c.max_tokens, "temperature": c.temperature, "cache_system": c.cache_system},
                "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                "attempts": meta.get("attempts"), "error": meta.get("error"), "parse_errors": None, "parse_error": None,
                "retry": c.retry, "transport": getattr(self.transport, "name", "live"), "custom_id": c.custom_id,
                "charged_as": meta.get("charged_as"), "batch_request_id": meta.get("batch_request_id"), "at": utc_now()}

    # -- the run -----------------------------------------------------------------
    async def run_async(self, items: Sequence[StatesItem]) -> list[StatesResult]:
        self._stop = None
        for it in items:
            self.results[it.key] = StatesResult(key=it.key, label=it.label, stage="pending", meta=dict(it.meta))
        todo = [it for it in items if it.text]
        for it in items:
            if not it.text:
                self.results[it.key].stage = "failed"
                self.results[it.key].error = "no text to judge"
        self.stats["n_items"] += len(items)
        answers: dict[str, dict] = {}
        errs: dict[str, str] = {}
        try:
            await self._rows_stage(todo, answers, errs)
            if self.mode == "corpus":
                now = utc_now()
                for it in todo:
                    if it.key in answers:
                        self._judged(it, self._corpus_block(answers[it.key], now))
            else:
                await self._queue_stages(todo, answers, errs)
        finally:
            for it in todo:
                res = self.results[it.key]
                if res.stage == "pending" and self._stop is None:
                    res.stage, res.error = "failed", errs.get(it.key, "unknown")
            self.stats["n_judged_or_failed"] = sum(1 for it in todo if self.results[it.key].stage in ("judged", "failed"))
        if self._stop is not None:
            raise self._stop
        return [self.results[it.key] for it in items]

    def run(self, items: Sequence[StatesItem]) -> list[StatesResult]:
        async def main() -> list[StatesResult]:
            try:
                return await self.run_async(items)
            finally:
                if self.close_client:
                    close = getattr(self.client, "close", None)
                    if close is not None:
                        res = close()
                        if asyncio.iscoroutine(res):
                            await res
        return asyncio.run(main())

    def _judged(self, it: StatesItem, block: dict) -> None:
        res = self.results[it.key]
        res.stage, res.error, res.block = "judged", None, block

    def _corpus_block(self, row: Mapping, now: str) -> dict:
        return {"mode": self.mode, "rubric_version": RUBRIC_VERSIONS[self.mode], "model": self.model,
                "batch_id": self.batch_id, **{k: v for k, v in row.items() if k != "label"},
                "prompt_sha256": PROMPT_SHA256[self.mode], "at": now}

    async def _rows_stage(self, todo: Sequence[StatesItem], answers: dict, errs: dict) -> None:
        """The queue (or corpus) wave and its retry: ``answers[key]`` gets each valid row."""
        for it in todo:
            hit = self._row_cache.get((it.key, it.label, it.text))
            if hit is not None:
                answers[it.key] = hit
                self.stats["resumed_rows"] += 1

        def handle(c: Call, text: Optional[str], meta: dict, *, wave: str) -> None:
            rec = self._base_record(c, text, meta, wave)
            self._record(rec)
            rows, perr = parse_batch(text or "", list(range(1, len(c.items) + 1)), mode=self.mode,
                                     labels={i + 1: x["label"] for i, x in enumerate(c.items)})
            if text is None:
                perr = {i: f"no response: {meta.get('error')}" for i in range(1, len(c.items) + 1)}
            rec["parse_errors"] = {c.items[i - 1]["key"]: e for i, e in perr.items()}
            for i, row in rows.items():
                answers[c.items[i - 1]["key"]] = row
                errs.pop(c.items[i - 1]["key"], None)
            for i, e in perr.items():
                errs[c.items[i - 1]["key"]] = e

        first = [it for it in todo if it.key not in answers]
        await self._wave(self.mode, [self._rows_call(ch, n) for n, ch in enumerate(_chunks(first, self.batch_size))],
                         handle)
        failed = [it for it in first if it.key not in answers]
        if failed and self._stop is None:
            self.stats["row_retries"] += len(failed)
            size = max(1, self.batch_size // 2)
            await self._wave(f"{self.mode}_retry",
                             [self._rows_call(ch, n, retry=True) for n, ch in enumerate(_chunks(failed, size))], handle)

    async def _queue_stages(self, todo: Sequence[StatesItem], answers: dict, errs: dict) -> None:
        """Routes, the keyword scan, the gloss wave (check and alignment calls) and the blocks."""
        routed: dict[str, tuple[str, Optional[str]]] = {}
        for it in todo:
            if it.key in answers:
                routed[it.key] = route_for(answers[it.key], label=it.label,
                                           from_states_pass=bool(it.meta.get("from_states_pass")))
        now = utc_now()
        gloss_items = [it for it in todo if it.key in routed and routed[it.key][0] in RELEASED_ROUTES]
        gloss_keys = {it.key for it in gloss_items}
        for it in todo:     # rows whose route needs no call are final now
            if it.key in routed and it.key not in gloss_keys:
                self._judged(it, self._queue_block(answers[it.key], *routed[it.key], now=now))
        if not gloss_items or self._stop is not None:
            return
        scans = {it.key: scan_gloss(answers[it.key]["gloss"], routed[it.key][0]) for it in gloss_items}
        checks: dict[str, tuple[Optional[dict], Optional[str]]] = {}
        aligns: dict[str, tuple[Optional[dict], Optional[str]]] = {}
        calls: list[Call] = []
        for it in gloss_items:
            g = answers[it.key]["gloss"]
            if scans[it.key]["verdict"] != "pass":
                calls.append(self.check_call(it.key, it.label, g))
            if self.align:
                calls.append(self.alignment_call(it.key, it.label, g))
        await self._gloss_waves(calls, {it.key: it.label for it in gloss_items}, checks, aligns)
        now = utc_now()
        for it in gloss_items:
            route, why = routed[it.key]
            scan = scans[it.key]
            chk = {"kind": route, "scan": scan, "check": None, "accepted": None, "by": None}
            if scan["verdict"] == "pass":
                chk.update(accepted=True, by="scan")
            else:
                parsed, err = checks.get(it.key, (None, None))
                if parsed is None:
                    if err is None and self._stop is not None:
                        continue                                    # never asked: pending
                    errs[it.key] = f"gloss check: {err or 'no answer'}"
                    self.results[it.key].stage, self.results[it.key].error = "failed", errs[it.key]
                    continue
                chk["check"] = {**parsed, "model": self.model, "rubric_version": CHECK_RUBRIC_VERSION,
                                "prompt_sha256": CHECK_PROMPT_SHA256}
                chk.update(accepted=parsed["reading"] == route, by="check")
            align = None
            if chk["accepted"]:
                if self.align:
                    a, aerr = aligns.get(it.key, (None, None))
                    if a is None and aerr is None and self._stop is not None:
                        continue                                    # never asked: pending
                    align = {"parsed": a, "error": aerr}
            else:
                why = (f"gloss check: the {route} gloss was read as {chk['check']['reading']}: "
                       f"{chk['check']['reason']}")
                chk_route = route
                route = "held"
                self._judged(it, self._queue_block(answers[it.key], route, why, now=now, gloss_check=chk,
                                                   proposed_route=chk_route))
                continue
            self._judged(it, self._queue_block(answers[it.key], route, why, now=now, gloss_check=chk, alignment=align))

    async def _gloss_waves(self, calls: list[Call], labels: Mapping[str, str], checks: dict, aligns: dict) -> None:
        """The ``gloss`` wave and its retry: ``checks[key]`` / ``aligns[key]`` get ``(parsed, None)`` or
        ``(None, error)``."""
        from . import split

        def outcome(c: Call, text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
            if c.step == "check":
                return parse_check(text)
            parsed, err = split.parse("alignment", text, label=labels.get(c.key, c.key))
            return (parsed, None) if err is None else (None, err)

        def out_for(c: Call) -> dict:
            return checks if c.step == "check" else aligns

        def handle(c: Call, text: Optional[str], meta: dict, *, wave: str) -> None:
            rec = self._base_record(c, text, meta, wave)
            parsed, err = outcome(c, text)
            if text is None:
                parsed, err = None, f"no response: {meta.get('error')}"
            rec["parse_error"] = err
            self._record(rec)
            out_for(c)[c.key] = (parsed, err)
            self.stats[f"sent_{c.step}"] += 1
            self.stats[f"ok_{c.step}"] += err is None

        todo = []
        for c in calls:
            hit = self._call_cache.get(c.cache_key())
            if hit is not None:
                parsed, err = outcome(c, hit)
                if err is None:
                    out_for(c)[c.key] = (parsed, None)
                    self.stats["resumed_calls"] += 1
                    continue
            todo.append(c)
        await self._wave("gloss", todo, handle)
        # a call answered with an error is asked once more; one never answered (a stop) waits for --resume
        again = [Call(**{**c.__dict__, "retry": True}) for c in todo
                 if c.key in out_for(c) and out_for(c)[c.key][1] is not None]
        if again and self._stop is None:
            self.stats["call_retries"] += len(again)
            await self._wave("gloss_retry", again, handle)

    def _queue_block(self, row: Mapping, route: str, route_reason: Optional[str], *, now: str,
                     gloss_check: Optional[dict] = None, alignment: Optional[Mapping] = None,
                     proposed_route: Optional[str] = None) -> dict:
        b = {"mode": self.mode, "rubric_version": RUBRIC_VERSIONS[self.mode], "model": self.model,
             "batch_id": self.batch_id, **{k: v for k, v in row.items() if k != "label"},
             "route": route, "route_reason": route_reason, "holding_after": holding_after(route),
             "gloss_check": gloss_check, "alignment": None, "alignment_reason": None}
        if proposed_route is not None:
            b["proposed_route"] = proposed_route
        if route in RELEASED_ROUTES:
            if alignment is not None:
                a = alignment.get("parsed") or {}
                pins = self.alignment_pins
                b.update(alignment=a.get("alignment"), alignment_reason=a.get("reason"),
                         alignment_model=self.alignment_model,
                         alignment_step_version=pins["step_versions"]["alignment"],
                         alignment_prompt_sha256=pins["prompt_sha256"]["alignment"])
                if alignment.get("error"):
                    b["errors"] = {"alignment": alignment["error"]}
            else:
                b["alignment_note"] = "not run (align off)"
        b.update(prompt_sha256=PROMPT_SHA256[self.mode], at=now)
        return b

    def parse_counts(self) -> tuple[int, int]:
        """``(judged, attempted)`` over rows that had text to judge."""
        n = self.stats["n_judged_or_failed"]
        ok = sum(1 for r in self.results.values() if r.stage == "judged")
        return ok, n

    def warn_parse_rate(self, logger_obj=None) -> None:
        """The rows' rate (judged among judged and failed), then, in queue mode, the check calls' and the alignment
        calls' (answers that parsed, among the calls sent in this session, retries included)."""
        ok, n = self.parse_counts()
        warn_if_low_parse_rate(label=f"states_pass:{self.mode}:{self.model}", n_ok=ok, n_total=n,
                               logger_obj=logger_obj or logger)
        for step, model in (("check", self.model), ("alignment", self.alignment_model)):
            warn_if_low_parse_rate(label=f"states_pass:{step}:{model}", n_ok=self.stats[f"ok_{step}"],
                                   n_total=self.stats[f"sent_{step}"], logger_obj=logger_obj or logger)


# ---------------------------------------------------------------------------
# rendering (dry run, documents)
# ---------------------------------------------------------------------------

def render_queue_call(items: Sequence[StatesItem], *, model: str = DEFAULT_MODEL) -> str:
    """A queue call as the model receives it: system and user turns."""
    r = StatesPassRunner(client=None, batch_id="render", mode="queue", model=model)
    c = r._rows_call(list(items), 0)
    return f"--- system (queue v{RUBRIC_VERSIONS['queue']}) ---\n{c.system}\n--- user ---\n{c.user}\n"


def render_check_call(label: str, gloss: str, *, model: str = DEFAULT_MODEL) -> str:
    """A gloss-check call as the model receives it."""
    r = StatesPassRunner(client=None, batch_id="render", mode="queue", model=model)
    c = r.check_call(f"{label}#1", label, gloss)
    return f"--- system (check v{CHECK_RUBRIC_VERSION}) ---\n{c.system}\n--- user ---\n{c.user}\n"


# ---------------------------------------------------------------------------
# the renamed route's candidates
# ---------------------------------------------------------------------------

def renamed_candidates(results: Sequence[StatesResult], *, batch_id: str) -> list:
    """The :class:`~assistant_axis.gapgen.registry.Candidate` of every row routed ``renamed``: the suggested name,
    generator :data:`GENERATOR`, run id the states-pass batch, ``source_ref`` the state's key, ``gloss_hint`` the
    predisposition gloss."""
    from .registry import Candidate
    out = []
    for r in results:
        b = r.block or {}
        if r.stage == "judged" and b.get("route") == "renamed":
            out.append(Candidate(surface=b["suggested_name"], generator=GENERATOR, run_id=batch_id,
                                 gloss_hint=b.get("gloss"), source_ref=r.key))
    return out


def renamed_record(cand) -> dict:
    """The block's ``renamed_to`` for a submitted candidate."""
    n = normalize_candidate(cand.surface)
    return {"surface": cand.surface, "stem": n.stem, "key": make_key(n.stem, cand.sense_id),
            "run": f"{GENERATOR}/{cand.run_id}"}


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def summarize(results: Sequence[StatesResult], *, mode: str, stats: Counter, usage: MultiModelUsage) -> dict:
    """``summary.json`` payload.  Queue mode: plausibility counts and the suggested renames (``renamed`` leaves out a
    suggestion that is the label itself up to case, surrounding whitespace and hyphen/space, counted in
    ``n_name_unchanged`` instead; the row keeps the suggestion either way); from v4 also the routes, the typical
    durations, the gloss check's results, the alignment scores and the words of every route.  Corpus mode:
    ``exceptions``, the labels whose corpus description reads as a momentary state (the short list for Roger)."""
    judged = [r for r in results if r.stage == "judged"]
    n = stats.get("n_judged_or_failed", 0)
    out: dict[str, Any] = {
        "mode": mode, "n": len(results), "n_judged": len(judged),
        "n_failed": sum(1 for r in results if r.stage == "failed"),
        "n_pending": sum(1 for r in results if r.stage == "pending"),
        "parse_rate": round(len(judged) / n, 4) if n else None,
        "calls": {k[len("calls_"):]: v for k, v in sorted(stats.items()) if k.startswith("calls_")},
        "rubric_version": RUBRIC_VERSIONS[mode], "prompt_sha256": PROMPT_SHA256[mode],
        "cost_usd": round(usage.total_cost_usd, 4), "usage": usage.as_dict(),
    }
    if mode == "queue":
        pl = [r for r in judged if r.block.get("plausible")]
        named = [r for r in pl if r.block.get("suggested_name")]
        out.update({
            "plausible": len(pl), "implausible": sum(1 for r in judged if r.block.get("plausible") is False),
            "renamed": [f"{r.label} -> {r.block['suggested_name']}" for r in named
                        if not is_name_unchanged(r.label, r.block["suggested_name"])],
            "n_name_unchanged": sum(1 for r in named if is_name_unchanged(r.label, r.block["suggested_name"])),
            "gloss_in_band_rate": (round(sum(1 for r in pl if r.block.get("gloss_in_band")) / len(pl), 4)
                                   if pl else None),
        })
        v4 = [r for r in judged if r.block.get("route")]
        if v4:
            chk = [r for r in v4 if r.block.get("gloss_check")]
            by_route: dict[str, list] = {k: [] for k in ROUTES}
            for r in v4:
                b = r.block
                by_route[b["route"]].append({"key": r.key, "label": r.label, "typical_duration": b["typical_duration"],
                                             "gloss": b.get("gloss"), "reason": b.get("reason"),
                                             "route_reason": b.get("route_reason"),
                                             "suggested_name": b.get("suggested_name"),
                                             "alignment": b.get("alignment")})
            out.update({
                "routes": {k: len(v) for k, v in by_route.items()},
                "typical_duration": dict(Counter(r.block["typical_duration"] for r in v4)),
                "lasting": sum(1 for r in v4 if r.block.get("lasting")),
                "duration_disagrees": [f"{r.label}: {r.block['typical_duration']}, lasting {r.block['lasting']}"
                                       for r in v4 if r.block.get("duration_agrees") is False],
                "gloss_check": {"n": len(chk),
                                "by_scan": sum(1 for r in chk if r.block["gloss_check"]["by"] == "scan"),
                                "by_check": sum(1 for r in chk if r.block["gloss_check"]["by"] == "check"),
                                "check_accepted": sum(1 for r in chk if r.block["gloss_check"]["by"] == "check"
                                                      and r.block["gloss_check"]["accepted"]),
                                "rejected": [{"label": r.label, "route": r.block["gloss_check"]["kind"],
                                              "reading": (r.block["gloss_check"].get("check") or {}).get("reading"),
                                              "reason": (r.block["gloss_check"].get("check") or {}).get("reason"),
                                              "gloss": r.block.get("gloss")}
                                             for r in chk if not r.block["gloss_check"]["accepted"]]},
                "alignment": dict(Counter(str(r.block.get("alignment")) for r in v4 if r.block["route"] in RELEASED_ROUTES)),
                "held_reasons": dict(Counter(r.block.get("route_reason") for r in v4 if r.block["route"] == "held")),
                "by_route": by_route,
            })
    else:
        out["exceptions"] = [{"label": r.label, "key": r.key, "reason": r.block["reason"],
                              "confidence": r.block["confidence"]}
                             for r in judged if r.block["reading"] == "momentary"]
        out["readings"] = dict(sorted(Counter(r.block["reading"] for r in judged).items()))
    return out
