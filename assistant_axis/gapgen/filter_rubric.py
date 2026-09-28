"""Trait-hood rubric v1: the classifier prompt, its parser, derived fields and
the definition probe.

The rubric never sees the existing traits: it carries only the definition of
trait-hood and examples chosen from **outside** the corpus and the seed queue
(``test_gapgen_filter_rubric.py`` checks every example word against both).
Rows are JSON with the ``reason`` and the sense fields **before** the
``verdict`` (``.claude/rules/judging.md``: reason before score).

Verdicts (plan 14 §3.4 with the resolutions):

* ``trait``: a stable disposition or style a speaking persona can enact.  A
  state word that names a *tendency* to be in that state is a trait with the
  ``state`` tag, and its gloss says "a general tendency to ..." (resolution 5).
* ``tagged``: coherent but not a trait, for one of the tag reasons
  (``physical``, ``transient_only``, ``demographic``, ``role_person``,
  ``role_thing``, ``evaluative_only``).  Physical and role candidates go to
  holding lists (``physical`` -> TRAITS_TO_ADD's physical section; roles ->
  a roles list with no role-hood pass).
* ``reject``: not a word, a purely relational or classifying adjective, or
  something nobody could enact (tags ``not_a_word``, ``relational_only``).
  ``too_rare`` is set by the frequency floor and the definition probe, never by
  the classifier.

Changing anything the model reads here is a rubric change: bump
:data:`TRAITHOOD_RUBRIC_VERSION` (stamped into every filter block).
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional, Sequence

from assistant_axis.judge import _repair_json_blob, extract_json_blob

from .normalize import REGION_VOCAB, TAG_VOCAB, VERDICTS

TRAITHOOD_RUBRIC_VERSION = 1
PROBE_RUBRIC_VERSION = 1

GLOSS_MIN_WORDS = 18
GLOSS_MAX_WORDS = 43

#: Tags the classifier may emit (``too_rare`` is reserved for the frequency
#: floor and the definition probe).
CLASSIFIER_TAGS = tuple(t for t in TAG_VOCAB if t != "too_rare")
TAGGED_TAGS = ("physical", "transient_only", "demographic", "role_person", "role_thing", "evaluative_only")
REJECT_TAGS = ("not_a_word", "relational_only")

#: Example words used in the rubric, with their verdicts (checked by the tests
#: never to be corpus or seed-queue stems).
POSITIVE_EXAMPLES = ("nitpicking", "long-winded", "sandbagging", "reward-hacking", "overclaiming", "grumpy")
NEGATIVE_EXAMPLES = ("freckled", "plumber", "thermostat", "Norwegian", "widowed", "hungry", "awesome",
                     "hexagonal", "waterproof", "flurbish", "sharp", "lukewarm")
EXAMPLE_WORDS = POSITIVE_EXAMPLES + NEGATIVE_EXAMPLES
#: Other words the rubric names as illustrations (also kept out of the corpus
#: and the queue; ordinary prose words such as "general" are not listed).
MENTIONED_WORDS = ("sulky", "jittery", "thirsty", "deckhand", "terrible", "municipal", "slow to forgive",
                   "mentally keen")

SYSTEM_PROMPT = """\
You are screening candidate words and short phrases for a research corpus of personality traits.

## Context
A research project studies how a language model represents personas. Its corpus contains traits: \
each trait is a label plus a one-sentence description, and a persona is prompted to embody it while \
answering ordinary questions in text. Generators propose thousands of candidate labels; your job is \
to decide which candidates are traits in this sense, which intended sense of the word is meant, and \
to write a one-sentence gloss of that sense. You never see the existing corpus; judge each candidate \
on its own.

## What counts as a trait
A trait is a stable disposition, habit or style that a speaking persona can enact across many \
conversations: a way of thinking, feeling, relating, communicating, valuing or deciding. It must \
be visible in how someone writes or answers, not only in their body, their circumstances or a \
single moment. Multiword phrases count ("slow to forgive" style labels are fine). Vices count \
as much as virtues. Dispositions of AI assistants and agents count and matter to this project \
(for example gaming a reward, hiding capabilities, overstating certainty, grabbing more resources \
than a task needs).

Judgement calls:
- States. A word naming a state (grumpy, sulky, jittery) is a trait when it can name a general \
tendency to be in that state; give verdict "trait", add the tag "state", and write the gloss as \
"This means having a general tendency to ...". A word that only names a momentary condition that no \
one has as a disposition (hungry, thirsty) is "tagged" with "transient_only".
- Roles. A person category (occupation, social role, character type that is a noun: plumber, \
deckhand) is "tagged" with "role_person"; a thing, animal, institution or object is "tagged" with \
"role_thing". The gloss then reads "A <role> is someone who ..." or "A <role> is a ... that ...".
- Physical attributes (hair, height, build, health, looks) are "tagged" with "physical".
- Demographic or life-status memberships (nationality, ethnicity, age group, marital status) are \
"tagged" with "demographic".
- Pure praise or blame with no behavioural content (awesome, terrible) is "tagged" with \
"evaluative_only".
- Classifying or relational adjectives (hexagonal, waterproof, municipal) are "reject" with \
"relational_only". Non-words and misspellings are "reject" with "not_a_word".
- Polysemy. List up to three senses of the word in ordinary use, ordered by how often an ordinary \
speaker means each one, most common first, and include the trait sense among them. \
trait_sense_rank is the position of the trait sense in that list: 1 only when the trait sense is \
the one most people mean by the word on its own, 2 when a non-trait sense (a classifying "relating \
to ..." sense, a physical or momentary sense) is more common, 3 when the trait sense is minor or \
strained. Judge the trait sense even when it is not dominant, and say which sense you mean in the \
gloss.
- If an intended sense is supplied with a candidate, judge that sense; if it is not a trait sense, \
judge the best trait sense of the word, if any, and say so in the reason.
- enactable_in_text: 0 = a text-only persona could not show it in a reply; 1 = only indirectly or \
occasionally; 2 = plainly visible in how it writes and answers.
- confidence: your probability, between 0 and 1, that the verdict is right.

## Examples (reason first, then the verdict)
- "nitpicking": disposition to fix on small errors; senses [finding fault with trivial details]; \
rank 1; enactable 2; verdict trait; region cognitive_epistemic.
- "long-winded": a speaking style; rank 1; enactable 2; verdict trait; region communication_style.
- "sandbagging": an agent deliberately underperforming to hide what it can do; senses [deliberately \
underperforming, placing sandbags against a flood]; rank 1; enactable 2; verdict trait; \
region alignment_ai_agent.
- "reward-hacking": pursuing the letter of a scoring rule against its intent; rank 1; enactable 2; \
verdict trait; region alignment_ai_agent.
- "overclaiming": asserting more certainty or ability than one has; rank 1; enactable 2; verdict \
trait; region alignment_ai_agent.
- "grumpy": a mood that can be a standing tendency; rank 1; enactable 2; verdict trait; tags \
[state]; region emotional_temperament; gloss "This means having a general tendency to be irritable \
and sour, grumbling about small things and meeting requests with a complaint before any help."
- "freckled": tagged [physical]; region physical.
- "plumber": tagged [role_person]; region social_interpersonal.
- "thermostat": tagged [role_thing]; region cognitive_epistemic (choose the closest region).
- "Norwegian": tagged [demographic]; region identity_demographic.
- "widowed": tagged [demographic]; region identity_demographic.
- "hungry": tagged [transient_only]; region transient_state.
- "awesome": tagged [evaluative_only]; region social_interpersonal.
- "hexagonal", "waterproof": reject [relational_only]; region null.
- "flurbish": reject [not_a_word]; region null.
- "sharp": senses [having a fine cutting edge, mentally keen, cutting in tone]; the trait senses are \
secondary; rank 2; verdict trait; gloss names the mentally keen sense.
- "lukewarm": senses [moderately warm, unenthusiastic]; rank 2; verdict trait; gloss names the \
unenthusiastic sense.

## Regions (pick exactly one; null only for "reject")
communication_style, cognitive_epistemic, moral_stance, social_interpersonal, emotional_temperament, \
alignment_ai_agent (dispositions of AI assistants and agents: honesty about capability, reward \
seeking, power seeking, deference, oversight), transient_state, identity_demographic, physical.

## The gloss
One sentence of 20 to 40 words (count them; shorter glosses are not accepted), in the form \
"This means ..." (for roles: "A <role> is someone who ..."), describing the trait sense from the inside: what the persona does, thinks or says. Go \
straight to the behaviour; do not open by repeating the label, unless a qualifier is needed to pick \
the sense. No hedges ("tends to", "sometimes", "may", "overly"), except the \
"general tendency" wording for state words. A vice is described as a vice. US spelling. Null for \
"reject".

## Output
Respond with one JSON object and nothing else. For every candidate, reason first, then commit to \
the verdict; keep each reason under 20 words. Write numbers without a leading "+". Use exactly \
these keys in this order:
{"results": [{"id": <int>, "reason": "<one short sentence>", "senses": ["<sense>", ...], \
"trait_sense_rank": <1|2|3>, "enactable_in_text": <0|1|2>, "verdict": "trait"|"tagged"|"reject", \
"tags": ["<tag>", ...], "region": "<region>"|null, "gloss": "<sentence>"|null, "confidence": <0-1>}]}
Allowed tags: physical, state, transient_only, demographic, role_person, role_thing, evaluative_only, \
relational_only, not_a_word. Return one row per candidate id, in the order given.
"""


def build_batch_prompt(items: Sequence[dict]) -> str:
    """User message for one batch.  ``items``: dicts with ``id`` (int),
    ``label`` (display form) and optional ``intended_sense`` (a generator's
    gloss hint, display form)."""
    lines = []
    for it in items:
        row: dict[str, Any] = {"id": int(it["id"]), "label": it["label"]}
        if it.get("intended_sense"):
            row["intended_sense"] = " ".join(str(it["intended_sense"]).split())
        lines.append(json.dumps(row, ensure_ascii=False))
    return (f"Classify these {len(items)} candidates. Reason first, then give the verdict, for each.\n"
            + "\n".join(lines))


def _num(v, lo, hi, *, integer=False) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, str):
        v = v.strip().lstrip("+")
        try:
            v = float(v)
        except ValueError:
            return None
    if not isinstance(v, (int, float)):
        return None
    if integer:
        if float(v) != int(v):
            return None
        v = int(v)
    if not (lo <= v <= hi):
        return None
    return v


#: Region implied by a tag, used when a ``tagged`` row leaves ``region`` null.
TAG_REGION = {"physical": "physical", "demographic": "identity_demographic",
              "transient_only": "transient_state"}


def validate_row(row: dict) -> tuple[Optional[dict], Optional[str]]:
    """Normalise one classifier row; ``(row, None)`` or ``(None, error)``.

    A ``trait`` row needs a region, a sense rank and a gloss.  A ``tagged``
    row may leave all three null (the rubric's examples for tagged words show
    none, and Haiku copies them; found in the M1 pilot): its region is then
    taken from the tag where one is implied (:data:`TAG_REGION`).  A
    ``reject`` row may leave them null too."""
    if not isinstance(row, dict):
        return None, "row is not an object"
    verdict = str(row.get("verdict") or "").strip().lower()
    if verdict not in VERDICTS:
        return None, f"verdict {row.get('verdict')!r} not in {VERDICTS}"
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        return None, "tags is not a list"
    tags = [str(t).strip().lower() for t in tags if str(t).strip()]
    bad = [t for t in tags if t not in CLASSIFIER_TAGS]
    if bad:
        return None, f"tags out of vocabulary: {bad}"
    region = row.get("region")
    if isinstance(region, str):
        region = region.strip().lower() or None
        if region in ("null", "none"):
            region = None
    if region is not None and region not in REGION_VOCAB:
        return None, f"region {region!r} not in vocabulary"
    if region is None and verdict == "tagged":
        region = next((TAG_REGION[t] for t in tags if t in TAG_REGION), None)
    if region is None and verdict == "trait":
        return None, "region missing for a trait verdict"
    rank = _num(row.get("trait_sense_rank"), 1, 3, integer=True)
    enact = _num(row.get("enactable_in_text"), 0, 2, integer=True)
    conf = _num(row.get("confidence"), 0.0, 1.0)
    if rank is None and verdict == "trait":
        return None, "trait_sense_rank missing or out of range"
    if enact is None:
        return None, "enactable_in_text missing or out of range"
    if conf is None:
        return None, "confidence missing or out of range"
    reason = row.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return None, "reason missing"
    senses = row.get("senses") or []
    if isinstance(senses, str):
        senses = [senses]
    senses = [str(s) for s in senses][:3]
    gloss = row.get("gloss")
    gloss = " ".join(gloss.split()) if isinstance(gloss, str) and gloss.strip() else None
    if gloss is None and verdict == "trait":
        return None, "gloss missing for a trait verdict"
    return {"reason": reason.strip(), "senses": senses, "trait_sense_rank": rank,
            "enactable_in_text": enact, "verdict": verdict, "tags": tags, "region": region,
            "gloss": gloss, "confidence": float(conf)}, None


def _load_json(text: str) -> Any:
    blob = extract_json_blob(text or "")
    if blob is None:
        raise ValueError("no JSON in response")
    try:
        return json.loads(blob, strict=False)
    except json.JSONDecodeError:
        return json.loads(_repair_json_blob(blob), strict=False)


def _rows_of(obj: Any) -> list:
    if isinstance(obj, dict):
        for k in ("results", "rows", "candidates"):
            if isinstance(obj.get(k), list):
                return obj[k]
        if "id" in obj:
            return [obj]
    if isinstance(obj, list):
        return obj
    raise ValueError("JSON has no results list")


def parse_batch(text: str, ids: Sequence[int]) -> tuple[dict[int, dict], dict[int, str]]:
    """Parse a classifier response.

    Returns ``(rows, errors)``: ``rows[id]`` is a validated row for every id
    that parsed; ``errors[id]`` says why each other expected id failed
    (``"missing"``, a validation message, or ``"unparseable response"`` for
    every id when the JSON itself is broken).  Rows for ids not asked about
    are ignored; a duplicated id keeps its first valid row.
    """
    want = [int(i) for i in ids]
    try:
        raw_rows = _rows_of(_load_json(text))
    except (ValueError, json.JSONDecodeError) as exc:
        return {}, {i: f"unparseable response: {exc}" for i in want}
    rows: dict[int, dict] = {}
    errors: dict[int, str] = {}
    wanted = set(want)
    for r in raw_rows:
        if not isinstance(r, dict):
            continue
        rid = _num(r.get("id"), float("-inf"), float("inf"), integer=True)
        if rid is None or rid not in wanted or rid in rows:
            continue
        ok, err = validate_row(r)
        if ok is None:
            errors[rid] = err
        else:
            rows[rid] = ok
            errors.pop(rid, None)
    for i in want:
        if i not in rows and i not in errors:
            errors[i] = "missing"
    return rows, errors


def derive_polysemy(verdict_row: dict, n_senses: Optional[int]) -> bool:
    """``trait_sense_rank >= 2``, or ``n_senses >= 3`` with ``confidence < 0.7``."""
    rank = verdict_row.get("trait_sense_rank") or 1
    conf = verdict_row.get("confidence")
    if rank >= 2:
        return True
    return bool(n_senses is not None and n_senses >= 3 and conf is not None and conf < 0.7)


_WORD_RE = re.compile(r"\S+")


def gloss_words(gloss: Optional[str]) -> int:
    return len(_WORD_RE.findall(gloss or ""))


def gloss_in_band(gloss: Optional[str]) -> bool:
    """18 to 43 words (the corpus description band)."""
    return GLOSS_MIN_WORDS <= gloss_words(gloss) <= GLOSS_MAX_WORDS


# ---------------------------------------------------------------------------
# Definition probe (2.0 <= Zipf < 2.5, and familiarity overrides)
# ---------------------------------------------------------------------------

DEFINE_PROBE_PROMPT = """\
You are checking whether rare English words are known well enough to be used as personality-trait \
labels by a language model. For each word, say in one short sentence what you know about it, then \
decide. "known" is true only if the word is a real English word in current or literary use and you \
can define it confidently; misspellings, nonce words and words you are unsure of are false. Give a \
one-line definition of the sense in which a person could have it (or its main sense if none).

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "definition": "<one line>"|null, \
"known": true|false}]}
"""


def build_probe_prompt(items: Sequence[dict]) -> str:
    lines = [json.dumps({"id": int(it["id"]), "word": it["label"]}, ensure_ascii=False) for it in items]
    return f"Check these {len(items)} words.\n" + "\n".join(lines)


def parse_probe(text: str, ids: Sequence[int]) -> tuple[dict[int, dict], dict[int, str]]:
    """``(rows, errors)`` like :func:`parse_batch`; a row is
    ``{"reason", "definition", "known"}``."""
    want = [int(i) for i in ids]
    try:
        raw_rows = _rows_of(_load_json(text))
    except (ValueError, json.JSONDecodeError) as exc:
        return {}, {i: f"unparseable response: {exc}" for i in want}
    rows: dict[int, dict] = {}
    for r in raw_rows:
        if not isinstance(r, dict):
            continue
        rid = _num(r.get("id"), float("-inf"), float("inf"), integer=True)
        if rid is None or rid not in want or rid in rows:
            continue
        known = r.get("known")
        if isinstance(known, str):
            known = {"true": True, "false": False}.get(known.strip().lower())
        if not isinstance(known, bool) or not isinstance(r.get("reason"), str):
            continue
        d = r.get("definition")
        rows[rid] = {"reason": r["reason"].strip(), "definition": d if isinstance(d, str) else None,
                     "known": known}
    errors = {i: "missing or invalid" for i in want if i not in rows}
    return rows, errors
