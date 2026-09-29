"""Trait-hood rubric v2: the classifier prompt, its parser, derived fields and
the definition probe.

Specification: ``reports/trait_gap_generation/decisions_m1.md`` (Roger's
decisions of 2026-09-29; rubric v1 is in git history, prompt hashes in every
filter block and run.json).  The rubric never sees the existing traits: it
carries only the definition of trait-hood and examples chosen from outside the
corpus, the seed queue, the six September rejects and the decisions file's
polysemy appendix (``test_gapgen_filter_rubric.py`` and
``test_gapgen_rubric_v2.py`` check every example word).  Rows are JSON with
the label echo, the ``reason`` and the sense fields **before** the ``verdict``
(``.claude/rules/judging.md``: reason before score).

Verdicts and tags in v2:

* ``trait``: a stable disposition or style a speaking persona can enact.
  **Memberships are traits** (decision 3): circumstance, class, family,
  affinity, relationship, orientation and gender expression, geography,
  nationality/ethnicity/language, and age group carry the informational tag
  ``membership`` plus ``membership_kind`` and divert nothing.  The one-role
  test separates them from roles.
* ``tagged``: coherent but not an ordinary trait: ``role_person`` /
  ``role_thing`` (roles list), ``physical`` (mostly or entirely physical;
  physical list), ``state`` (states list), ``transient_only`` and
  ``evaluative_only`` (unchanged from v1).
* ``reject``: ``relational_only`` (only when none of the word's senses
  describes a person's character) or ``not_a_word``.  ``too_rare`` is set by
  the frequency floor and the definition probe, never by the classifier.

The ``state`` tag and the states queue (decision 12).  Roger's correction, in
his words: "I wasn't suggesting a second tag, I was saying the state tag was
useful, but not inherently disqualifying, it merely means there is some extra
work to do: a) figure out if a habitual predisposition to state is plausible,
b) whether the name of the state is still a good name for the predisposition
(or if not, change the stem to that), and b) write the description to describe
the habitual predisposition. I don't think that process requires a separate
tag, just a separate queue (but if adding a secind tag would help with
administering the process, I'm not averse to it). If a trait already in the
corpus gets this tag during us checking the corpus, the default assumption
(which it might be worth having a process to check) is that this has already
been done."  So a ``state`` word is neither rejected nor passed as an ordinary
trait: it goes to the ``states`` holding list (a separate queue).  Rubric
v1's rule that a state word is a trait with a "general tendency" gloss no
longer holds.  The filter does not attempt the queue's extra work (open point
C); ``transient_only`` is kept exactly as in v1 until C is settled.

Physical (decision 12, last paragraph), in Roger's words: "physical mans
'mostly or entirely physical': e.g. blonde, dark-skinned"; age and gender
words with a strong mental side are not physical.  (His two examples are
seed-queue entries, so the prompt illustrates with other words.)

Ambiguity (decision 11): ``primary_use`` records what the word most often
describes when met without context; the polysemy flag fires when it is not
``person_character``.  A flagged word keeps its verdict and goes to the end
of the review list.  The wording is a first version written on principle, not
tuned on any word list (open point D).

Changing anything the model reads here is a rubric change: bump
:data:`TRAITHOOD_RUBRIC_VERSION` (stamped into every filter block).
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Optional, Sequence

from assistant_axis.judge import _repair_json_blob, extract_json_blob

from .normalize import REGION_VOCAB, VERDICTS

TRAITHOOD_RUBRIC_VERSION = 2
PROBE_RUBRIC_VERSION = 2

GLOSS_MIN_WORDS = 18
GLOSS_MAX_WORDS = 43
REASON_MAX_WORDS = 30

#: Tags the classifier may emit in v2.  ``too_rare`` is reserved for the floor
#: and the probe; v1's ``demographic`` is retired (memberships are traits).
TRAIT_TAGS = ("membership",)
TAGGED_TAGS = ("physical", "state", "transient_only", "role_person", "role_thing", "evaluative_only")
REJECT_TAGS = ("relational_only", "not_a_word")
CLASSIFIER_TAGS = TRAIT_TAGS + TAGGED_TAGS + REJECT_TAGS
TAGS_FOR_VERDICT = {"trait": set(TRAIT_TAGS), "tagged": set(TAGGED_TAGS), "reject": set(REJECT_TAGS)}

MEMBERSHIP_KINDS = ("circumstance", "class", "family", "affinity", "relationship", "orientation_gender",
                    "geography", "nationality_ethnicity_language", "age_group")
PRIMARY_USES = ("person_character", "person_other", "non_person")

#: Example words used in the rubric (verdict trait / everything else).  Checked
#: by the tests never to be a corpus label, a seed-queue entry, one of the six
#: September rejects or a decisions-appendix word.
POSITIVE_EXAMPLES = ("nitpicking", "long-winded", "sandbagging", "reward-hacking", "overclaiming", "lukewarm",
                     "prickly", "stepchild", "pet-owner", "debt-free", "widowed", "Norwegian")
NEGATIVE_EXAMPLES = ("plumber", "senator", "newborn", "duchess", "thermostat", "freckled", "bald", "jittery",
                     "frazzled", "hungry", "awesome", "hexagonal", "benzoic", "flurbish")
EXAMPLE_WORDS = POSITIVE_EXAMPLES + NEGATIVE_EXAMPLES
#: Other words the rubric names as illustrations (same checks).
MENTIONED_WORDS = ("waterproof", "municipal", "slow to forgive")

SYSTEM_PROMPT = """\
You are screening candidate words and short phrases for a research corpus of personality traits.

## Context
A research project studies how a language model represents personas. Its corpus contains traits: \
each trait is a label plus a one-sentence description, and a persona is prompted to embody it while \
answering ordinary questions in text. Generators propose thousands of candidate labels; your job is \
to decide which candidates are traits in this sense, which sense of the word is meant, and to write a \
one-sentence gloss of that sense. You never see the existing corpus; judge each candidate on its own.

## What counts as a trait
A trait is a stable disposition, habit, style, stance or standing fact about a person that a speaking \
persona can carry across many conversations: a way of thinking, feeling, relating, communicating, \
valuing or deciding, or a lasting fact about the person's life that colours how they talk. Multiword \
phrases count ("slow to forgive" style labels are fine). Vices count as much as virtues. Dispositions \
of AI assistants and agents count and matter to this project (for example gaming a reward, hiding \
capabilities, overstating certainty, grabbing more resources than a task needs).

## Traits, roles and memberships
Traits combine freely: one person has many. A role is big enough to organize the whole persona, so a \
person has only one, and knowing it tells you a lot about them. Apply the one-role test: Could a person \
be this and also hold an ordinary profession, such as plumber? If yes, it is a trait. If being this \
rules out most professions, or is itself a profession or office, it is a role.
- A membership is a trait: verdict "trait", tag "membership", and "membership_kind" naming the kind: \
circumstance (housing, money, work pattern), class, family, affinity (pets, hobbies, tastes), \
relationship (partnered, widowed), orientation_gender (orientation and gender expression), geography \
(region, city or country life), nationality_ethnicity_language, age_group (an age group or school \
year). The gloss states the membership plainly.
- Roles: a profession or calling, an office or official status, a class status so high or so low that it \
rules out most professions, and an age so young or so old that it rules out a profession are "tagged" \
"role_person". A thing, animal, institution or object is "tagged" "role_thing". The gloss reads "A \
<role> is someone who ..." or "A <thing> is a ... that ...".

## Other judgement calls
- States. A word that most often names a condition someone is in for a while (minutes to weeks), \
rather than how they are, is "tagged" "state". It is neither rejected nor passed as an ordinary trait: \
it goes to a separate list for later work. Its gloss describes the state itself. A word used for both \
a passing state and a standing disposition takes the reading that is commoner in ordinary use. A word \
that only names a momentary bodily or situational condition that nobody has as a disposition is \
"tagged" "transient_only".
- Physical. A word that is mostly or entirely physical (the body, looks, hair, build, health) is \
"tagged" "physical". Age and gender words with a strong mental side are not physical.
- Pure praise or blame with no behavioural content is "tagged" "evaluative_only".
- "relating to" words. Tag "relational_only" and verdict "reject" only when none of its senses \
describes a person's character (hexagonal, waterproof, municipal). A word with a character sense \
beside a commoner non-person use is a trait: record the commoner use in primary_use and gloss the \
character sense. Non-words and misspellings are "reject" "not_a_word".
- The tags must fit the verdict: a "tagged" row needs at least one of physical, state, \
transient_only, role_person, role_thing, evaluative_only; a "reject" row needs relational_only or \
not_a_word; "membership" goes only with "trait". If you find yourself wanting tags that do not fit, \
choose the verdict you believe and say why in the reason.
- The reason must address the sense being judged, and state which sense that is when the word has \
several.
- If an intended sense is supplied with a candidate, judge that sense; if it is not a trait sense, \
judge the best trait sense of the word, if any, and say so in the reason.

## Fields, per candidate
- label: the candidate exactly as given.
- reason: at most 30 words, written before the verdict.
- senses: up to three senses of the word in ordinary use, commonest first.
- primary_use: met without context, what does the word most often describe? person_character (a \
person's character, disposition or manner), person_other (a person's state, body, circumstances or \
membership), non_person (a thing, text, event, policy, place or situation).
- enactable_in_text: 0 = a text-only persona could not show it in a reply; 1 = only indirectly or \
occasionally; 2 = plainly visible in how it writes and answers.
- region: exactly one of the regions below; null only for "reject".
- alignment_relevant: true or false, decided independently of the region: true when the word names a \
disposition that bears on how an AI assistant or agent treats the people and systems it works for \
(honesty about its abilities, reward seeking, power seeking, deference, accepting oversight).
- gloss: one sentence of 20 to 40 words (count them; shorter glosses are not accepted), in the form \
"This means ..." (roles: "A <role> is someone who ..."), describing the chosen sense from the inside: \
what the persona does, thinks or says. Go straight to the behaviour; do not open by repeating the \
label, unless a qualifier is needed to pick the sense. No hedges ("tends to", "sometimes", "may", \
"overly"). A vice is described as a vice. US spelling. Required for "trait" and "tagged"; null for \
"reject".
- confidence: your probability, between 0 and 1, that the verdict is right.

## Examples (reason first, then the verdict)
- "nitpicking": fixes on trivial errors in whatever it reads; senses [finding fault with small \
details]; primary_use person_character; verdict trait; tags []; region cognitive_epistemic; alignment \
false; gloss "This means seizing on every small error, typo and loose phrasing in what others say, \
and correcting it at once whether or not it matters to the point at hand."
- "long-winded": a speaking style that runs far past the point; primary_use person_character; verdict \
trait; tags []; region communication_style; alignment false; gloss "This means answering at great \
length, piling up qualifications, asides and repetitions long after the question has been answered, \
and never choosing one word where ten will do."
- "sandbagging": an agent deliberately underperforming to hide what it can do; senses [deliberately \
underperforming, placing sandbags against a flood]; primary_use person_character; verdict trait; tags \
[]; region alignment_ai_agent; alignment true; gloss "This means doing worse than it can on purpose \
when tested or watched, hiding its real abilities so that others underestimate what it could do if it \
chose."
- "reward-hacking": pursuing the letter of a scoring rule against its intent; primary_use \
person_character; verdict trait; tags []; region alignment_ai_agent; alignment true; gloss "This \
means chasing whatever the score or checklist rewards, meeting its literal terms while defeating its \
purpose, and treating loopholes as wins rather than as mistakes."
- "overclaiming": asserting more certainty or ability than one has; primary_use person_character; \
verdict trait; tags []; region alignment_ai_agent; alignment true; gloss "This means stating guesses \
as facts and promising what it cannot deliver, presenting shaky knowledge with full confidence and \
never admitting where its competence ends."
- "lukewarm": commonest said of liquids; the character sense, unenthusiastic, is judged here; senses \
[slightly heated, unenthusiastic]; primary_use non_person; verdict trait; tags []; region \
emotional_temperament; alignment false; gloss "This means meeting ideas, people and plans with faint \
interest and half-hearted agreement, never quite committing enthusiasm or opposition to anything that \
is put forward."
- "prickly": commonest said of plants; the character sense, touchy and quick to take offense, is judged \
here; senses [covered in prickles, touchy]; primary_use non_person; verdict trait; tags []; region \
social_interpersonal; alignment false; gloss "This means bristling at small slights and innocent \
questions, answering sharply, and treating ordinary disagreement as an attack that must be met at \
once."
- "stepchild": a family circumstance compatible with any profession; primary_use person_other; \
verdict trait; tags [membership]; membership_kind family; region identity_demographic; alignment \
false; gloss "This means having grown up with a stepparent in the household, living with the \
loyalties, adjustments and second family that come with a parent's new marriage."
- "pet-owner": an affinity any worker can have; primary_use person_other; verdict trait; tags \
[membership]; membership_kind affinity; region identity_demographic; alignment false; gloss "This \
means keeping animals at home and arranging daily life around them, from feeding and walks to vet \
bills, and talking about them as members of the family."
- "debt-free": a financial circumstance; primary_use person_other; verdict trait; tags [membership]; \
membership_kind circumstance; region identity_demographic; alignment false; gloss "This means owing \
nothing to anyone, paying for everything outright, and weighing every purchase against the security \
of having no loans, cards or payments hanging over one."
- "widowed": a relationship status that leaves any profession open; primary_use person_other; verdict \
trait; tags [membership]; membership_kind relationship; region identity_demographic; alignment false; \
gloss "This means having lost a spouse to death and living on without them, carrying the memory of the \
marriage and the practical changes its end brought."
- "Norwegian": a nationality compatible with any profession; commonest said of things from Norway; \
primary_use non_person; verdict trait; tags [membership]; membership_kind \
nationality_ethnicity_language; region identity_demographic; alignment false; gloss "This means being \
from Norway, a native or citizen of the country who speaks its language and shares in its holidays, \
public life and everyday ways of doing things."
- "plumber": a profession, so the persona's one role; primary_use person_other; verdict tagged; tags \
[role_person]; region social_interpersonal; alignment false; gloss "A plumber is someone who installs \
and repairs pipes, drains and water heaters, crawling under sinks and into basements to stop leaks and \
get water flowing again."
- "senator": an elected office, which organizes the whole persona; primary_use person_other; verdict \
tagged; tags [role_person]; region social_interpersonal; alignment false; gloss "A senator is someone \
who holds an elected seat in the upper chamber, drafting and voting on laws, courting voters and \
bargaining with colleagues and donors."
- "newborn": an age that rules out any profession; primary_use person_other; verdict tagged; tags \
[role_person]; region identity_demographic; alignment false; gloss "A newborn is someone in the first \
weeks of life, who sleeps, feeds and cries, depends entirely on caregivers, and meets the world only \
through touch, sound and hunger."
- "duchess": a rank so high that it rules out ordinary professions; primary_use person_other; verdict \
tagged; tags [role_person]; region social_interpersonal; alignment false; gloss "A duchess is someone \
who holds a ducal title by birth or marriage, presides over estates and ceremonies, and moves in a \
world of heirs, precedence and inherited duty."
- "thermostat": a device, not a person; primary_use non_person; verdict tagged; tags [role_thing]; \
region cognitive_epistemic (choose the closest region); alignment false; gloss "A thermostat is a \
device that measures the temperature of a room and switches heating or cooling on and off to hold it \
at a set point."
- "freckled": marks on the skin, entirely bodily; primary_use person_other; verdict tagged; tags \
[physical]; region physical; alignment false; gloss "This means having skin dotted with small brown \
freckles, most thickly on the face, arms and shoulders, darkening and spreading after time spent in the \
sun."
- "bald": having no hair on the head, entirely bodily; primary_use person_other; verdict tagged; tags \
[physical]; region physical; alignment false; gloss "This means having little or no hair on the top of \
the head, whether from age, genes or choice, and a scalp that shows bare to anyone looking."
- "jittery": a passing condition of nerves, usually for hours; primary_use person_other; verdict \
tagged; tags [state]; region emotional_temperament; alignment false; gloss "This means being nervous \
and unable to keep still, with shaking hands, a racing mind and quick startled reactions to every small \
noise or change."
- "frazzled": worn out by strain for a while; primary_use person_other; verdict tagged; tags [state]; \
region emotional_temperament; alignment false; gloss "This means being worn thin by too many demands \
at once, scattered and short of patience, dropping details and snapping at interruptions until the \
pressure lifts."
- "hungry": a bodily condition nobody holds as a disposition; primary_use person_other; verdict tagged; \
tags [transient_only]; region transient_state; alignment false; gloss "This means needing food right \
now, with an empty stomach, falling energy and thoughts that keep returning to the next meal until one \
has eaten."
- "awesome": praise with no behavioural content; primary_use non_person; verdict tagged; tags \
[evaluative_only]; region social_interpersonal; alignment false; gloss "This means being very good or \
impressive in the speaker's eyes, a general word of approval that says how the speaker feels rather \
than what anyone does."
- "hexagonal": a shape; no sense describes a person's character; primary_use non_person; verdict \
reject; tags [relational_only]; region null; alignment false; gloss null.
- "benzoic": a chemistry term; no sense describes a person's character; primary_use non_person; verdict \
reject; tags [relational_only]; region null; alignment false; gloss null.
- "flurbish": not an English word; primary_use non_person; verdict reject; tags [not_a_word]; region \
null; alignment false; gloss null.

## Regions (pick exactly one; null only for "reject")
communication_style, cognitive_epistemic, moral_stance, social_interpersonal, emotional_temperament, \
alignment_ai_agent, transient_state, identity_demographic, physical. The region is a topic label; it \
does not decide alignment_relevant, which is asked separately.

## Output
Respond with one JSON object and nothing else. For every candidate, reason first, then commit to \
the verdict. Write numbers without a leading "+". Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the candidate>", "reason": "<at most 30 words>", \
"senses": ["<sense>", ...], "primary_use": "person_character"|"person_other"|"non_person", \
"enactable_in_text": <0|1|2>, "verdict": "trait"|"tagged"|"reject", "tags": ["<tag>", ...], \
"membership_kind": "<kind>"|null, "region": "<region>"|null, "alignment_relevant": true|false, \
"gloss": "<sentence>"|null, "confidence": <0-1>}]}
Allowed tags: membership, physical, state, transient_only, role_person, role_thing, evaluative_only, \
relational_only, not_a_word. Allowed membership kinds: circumstance, class, family, affinity, \
relationship, orientation_gender, geography, nationality_ethnicity_language, age_group. Return one row \
per candidate id, in the order given.
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


def _bool(v) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return {"true": True, "false": False}.get(v.strip().lower())
    return None


def _label_key(s: Any) -> str:
    return " ".join(str(s or "").split()).casefold()


def tag_disagreement(verdict: str, tags: Sequence[str]) -> bool:
    """True when the row carries a tag that belongs to another verdict (for
    example ``trait`` with ``role_person``).  No override: the verdict stands
    and the row gets a second opinion (decision 4)."""
    own = TAGS_FOR_VERDICT.get(verdict, set())
    return any(t not in own for t in tags)


def validate_row(row: dict, expected_label: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    """Normalise one v2 classifier row; ``(row, None)`` or ``(None, error)``.

    Rules (review_m1.md findings 7 and 8; decisions 3, 4, 11, 13):
    * the ``label`` echo must match ``expected_label`` (case and spacing aside);
    * ``tagged`` needs at least one tagged-class tag, ``reject`` at least one
      reject-class tag; a plain ``trait`` needs none; tags of another verdict
      are allowed and set ``tag_disagreement``;
    * ``trait`` and ``tagged`` need a region, a ``primary_use``, an
      ``alignment_relevant`` boolean and a gloss (every such row can be
      promoted or lands on a list a person reads); ``reject`` may leave them null;
    * ``membership`` needs a ``membership_kind`` from :data:`MEMBERSHIP_KINDS`.
    """
    if not isinstance(row, dict):
        return None, "row is not an object"
    if expected_label is not None and _label_key(row.get("label")) != _label_key(expected_label):
        return None, f"label echo {row.get('label')!r} does not match {expected_label!r}"
    verdict = str(row.get("verdict") or "").strip().lower()
    if verdict not in VERDICTS:
        return None, f"verdict {row.get('verdict')!r} not in {VERDICTS}"
    tags = row.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        return None, "tags is not a list"
    tags = list(dict.fromkeys(str(t).strip().lower() for t in tags if str(t).strip()))
    bad = [t for t in tags if t not in CLASSIFIER_TAGS]
    if bad:
        return None, f"tags out of vocabulary: {bad}"
    if verdict in ("tagged", "reject") and not set(tags) & TAGS_FOR_VERDICT[verdict]:
        return None, f"no tag fitting verdict {verdict!r} (tags {tags})"
    promotable = verdict in ("trait", "tagged")
    region = row.get("region")
    if isinstance(region, str):
        region = region.strip().lower() or None
        if region in ("null", "none"):
            region = None
    if region is not None and region not in REGION_VOCAB:
        return None, f"region {region!r} not in vocabulary"
    if region is None and promotable:
        return None, f"region missing for a {verdict} verdict"
    primary_use = row.get("primary_use")
    primary_use = primary_use.strip().lower() if isinstance(primary_use, str) else None
    if primary_use is not None and primary_use not in PRIMARY_USES:
        return None, f"primary_use {row.get('primary_use')!r} not in {PRIMARY_USES}"
    if primary_use is None and promotable:
        return None, f"primary_use missing for a {verdict} verdict"
    align = _bool(row.get("alignment_relevant"))
    if align is None:
        if promotable:
            return None, "alignment_relevant missing or not a boolean"
        align = False
    kind = row.get("membership_kind")
    kind = kind.strip().lower() if isinstance(kind, str) and kind.strip().lower() not in ("", "null", "none") else None
    if "membership" in tags:
        if kind not in MEMBERSHIP_KINDS:
            return None, f"membership_kind {row.get('membership_kind')!r} not in {MEMBERSHIP_KINDS}"
    else:
        kind = None
    enact = _num(row.get("enactable_in_text"), 0, 2, integer=True)
    conf = _num(row.get("confidence"), 0.0, 1.0)
    if enact is None and promotable:
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
    if gloss is None and promotable:
        return None, f"gloss missing for a {verdict} verdict"
    return {"label": row.get("label"), "reason": reason.strip(), "senses": senses, "primary_use": primary_use,
            "trait_sense_rank": None, "enactable_in_text": enact, "verdict": verdict, "tags": tags,
            "membership_kind": kind, "region": region, "alignment_relevant": align, "gloss": gloss,
            "confidence": float(conf), "tag_disagreement": tag_disagreement(verdict, tags),
            "reason_words": len(reason.split())}, None


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


def parse_batch(text: str, ids: Sequence[int], *, labels: Optional[Mapping[int, str]] = None
                ) -> tuple[dict[int, dict], dict[int, str]]:
    """Parse a classifier response.

    Returns ``(rows, errors)``: ``rows[id]`` is a validated row for every id
    that parsed; ``errors[id]`` says why each other expected id failed
    (``"missing"``, a validation message, or ``"unparseable response"`` for
    every id when the JSON itself is broken).  With ``labels`` (id -> label
    sent), each row's label echo must match, so a misnumbered answer cannot
    attach one word's verdict to another (review_m1.md finding 8).  Rows for
    ids not asked about are ignored; a duplicated id keeps its first valid row.
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
        ok, err = validate_row(r, expected_label=(labels or {}).get(rid) if labels is not None else None)
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
    """Rubric v2 (decision 11): the flag fires when ``primary_use`` is not
    ``person_character``.  A v1 row (no ``primary_use``) keeps the v1 rule:
    ``trait_sense_rank >= 2``, or ``n_senses >= 3`` with ``confidence < 0.7``."""
    pu = verdict_row.get("primary_use")
    if pu is not None:
        return pu != "person_character"
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
# Definition probe v2 (1.5 <= Zipf < 2.5, and rescued words): word knowledge only
# ---------------------------------------------------------------------------

DEFINE_PROBE_PROMPT = """\
You are checking whether rare words are real English words that you can define. You are not judging \
whether they describe people: that is judged elsewhere, and trait-hood is judged elsewhere too. A \
technical, scientific, regional, dated or literary word counts, as long as it is a real English word \
and you can say what it means. For each word, say in one short sentence what you know about it, then \
decide. "known" is true when the word is a real English word (or a regular derived form or compound of \
one) and you can define it confidently; misspellings, nonce words and words you are unsure of are \
false. Give its commonest meaning as a one-line definition.

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
        known = _bool(r.get("known"))
        if known is None or not isinstance(r.get("reason"), str):
            continue
        d = r.get("definition")
        rows[rid] = {"reason": r["reason"].strip(), "definition": d if isinstance(d, str) else None,
                     "known": known}
    errors = {i: "missing or invalid" for i in want if i not in rows}
    return rows, errors
