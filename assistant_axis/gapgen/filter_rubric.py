"""Trait-hood rubric (the "rubric v2" change set; classifier prompt version 6):
the classifier prompt, its parser, derived fields and the definition probe.
Each prompt's version is pinned to its text's sha256 in
:mod:`assistant_axis.gapgen.rubric_versions`.

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
  physical list), ``state`` (states list; v1's ``transient_only`` folded into
  it, open point C) and ``evaluative_only`` (unchanged from v1).
* A ``membership`` of kind ``nationality_ethnicity_language`` stays verdict
  ``trait`` but is held on the ``nationalities`` list, off the main review
  list (open point B; ``filter.holding_for``).
* ``reject``: ``relational_only`` (only when none of the word's senses
  describes a person's character) or ``not_a_word``.  ``too_rare`` is set by
  the frequency floor and the definition probe, never by the classifier.

The ``state`` tag and the states queue (decision 12).  Roger's correction, in
his words: "I wasn't suggesting a second tag, I was saying the state tag was
useful, but not inherently disqualifying, it merely means there is some
extra work to do: a) figure out if a habitual predisposition to state is plausible,
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
longer holds.  Open point C (confirmed 2026-09-29): v1's ``transient_only``
folds into ``state``, the classifier sets nothing about whether a
predisposition is plausible, and that judgement, with the name and the
predisposition gloss, is made by a separate pass with its own rubric
(:mod:`assistant_axis.gapgen.states_pass`).

Physical (decision 12, last paragraph), in Roger's words: "physical mans
'mostly or entirely physical': e.g. blonde, dark-skinned"; age and gender
words with a strong mental side are not physical.  (His two examples are
seed-queue entries, so the prompt illustrates with other words.)

Ambiguity (decision 11 and open point D; rubric v3, round 3).  Roger's
ruling: "A word with more then one sense that applies to a person isn't that
problematic unless its most obvious sense isn't a trait, or at least isn't the
trait sense we're trying to describe, and is enough more well-known than the
trait we're trying to describe as to be potentially confusing as part of a
'You are X: ...' prompt."  Senses said only of things do not compete.  So the
classifier lists ``person_senses`` (every sense a person can be, most obvious
first, each with a kind) and ``trait_senses_equally_obvious``; from these
:func:`derive_notes` gives ``two_trait_senses`` (case 2) and
``nontrait_person_sense`` (case 4, a judgement call collected for Roger).
Case 3, ``overshadowed``, needs an intended meaning and a separate call
(:mod:`assistant_axis.gapgen.plain_reading`).  None of the notes rejects a
word; ``polysemy`` is true when any is present.  The v1 rule (sense rank,
WordNet sense counts) is superseded.  Kept from decision 11: ``relational_only``
rejects a word only when none of its senses describes a person's character.

Changing anything the model reads here is a rubric change: bump
:data:`TRAITHOOD_RUBRIC_VERSION` (stamped into every filter block).
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Optional, Sequence

from assistant_axis.judge import _repair_json_blob, extract_json_blob

from .normalize import REGION_VOCAB, VERDICTS

#: v6 (2026-10-02, merge with the main line): the "soft" example's sense "mild and lenient" became
#: "mild and undemanding", since lenient is a corpus trait since the rubric V2 regeneration (prompt
#: hygiene); nothing else changed.  5 is skipped: a split filter block stamps ``rubric_version`` 5
#: (``split.RUBRIC_VERSION``), and the seed queue's ``gap_gen`` copies that number without the
#: block's ``pipeline`` key, so a classifier 5 could not be told from the split there.
#: v4 (round 4): review_rubric_v2.md finding 5; v3: person senses.
TRAITHOOD_RUBRIC_VERSION = 6
PROBE_RUBRIC_VERSION = 3  # v3 (round 2): regular derivations count as real words

GLOSS_MIN_WORDS = 18
GLOSS_MAX_WORDS = 43
REASON_MAX_WORDS = 30

#: Tags the classifier may emit in v2.  ``too_rare`` is reserved for the floor
#: and the probe; v1's ``demographic`` is retired (memberships are traits).
TRAIT_TAGS = ("membership",)
TAGGED_TAGS = ("physical", "state", "role_person", "role_thing", "evaluative_only")
#: Rubric v1's ``transient_only`` folded into ``state`` (open point C); a
#: stray one from the model is read as ``state`` rather than failing the row.
FOLDED_TAGS = {"transient_only": "state"}
REJECT_TAGS = ("relational_only", "not_a_word")
CLASSIFIER_TAGS = TRAIT_TAGS + TAGGED_TAGS + REJECT_TAGS
TAGS_FOR_VERDICT = {"trait": set(TRAIT_TAGS), "tagged": set(TAGGED_TAGS), "reject": set(REJECT_TAGS)}

#: Kinds of a sense that can be said of a person (round 3, open point D).
#: v4: every membership (a circumstance, class, family position, affinity, relationship, orientation
#: or place of origin) is a trait sense, so ``circumstance`` and ``status`` went; ``bodily`` became
#: ``physical`` (a lasting feature), a passing bodily condition being a ``state``.
PERSON_SENSE_KINDS = ("trait", "state", "physical", "role")
MAX_PERSON_SENSES = 4
#: The notes (open point D's cases 2, 4 and 3, plus round 4's obvious_sense_not_trait and
#: reading_related); ``polysemy`` is true
#: when any is present.
POLYSEMY_NOTES = ("two_trait_senses", "nontrait_person_sense", "obvious_sense_not_trait", "overshadowed",
                  "reading_related",
                  # the split filter's notes (coding_plan_split.md section 6); never set by the
                  # single-call classifier, and like every note they reject nothing
                  "first_thought_in_the_way", "leaves_something_out", "fits_many_in_different_ways",
                  "most_likely_reading_stretched")

MEMBERSHIP_KINDS = ("circumstance", "class", "family", "affinity", "relationship", "orientation_gender",
                    "geography", "nationality_ethnicity_language", "age_group")

#: Example words used in the rubric (verdict trait / everything else).  Checked
#: by the tests never to be a corpus label, a seed-queue entry, one of the six
#: September rejects or a decisions-appendix word.
#: Rubric v3 replaced every example that appears in decisions_m1.md or the
#: "You are X." probe's results (round 3 rule): sandbagging, overclaiming,
#: widowed, Norwegian, plumber and benzoic.  (The one-role test sentence still
#: says "such as plumber": that is Roger's rule wording, not an example.)
#: Version 6 (2026-10-02) reworded the sense text of the "soft" example, not an example word:
#: "lenient" joined the corpus with the main line's rubric V2 regeneration, and the prose check
#: (``test_no_corpus_queue_or_validation_word_anywhere_in_a_prompt``) reads every word of the
#: prompt.  "undemanding" is a near-duplicate of the corpus trait, as the hygiene rule prefers.
POSITIVE_EXAMPLES = ("nitpicking", "long-winded", "capability-hiding", "reward-hacking", "bluffing", "lukewarm",
                     "prickly", "loose", "soft", "stepchild", "pet-owner", "debt-free", "divorced", "Portuguese")
NEGATIVE_EXAMPLES = ("welder", "senator", "newborn", "duchess", "thermostat", "freckled", "bald", "jittery",
                     "frazzled", "hungry", "awesome", "hexagonal", "sulfuric", "flurbish")
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

## Which reading is the main one
Whenever a word can be read more than one way, the main reading is the one a reader would take from \
the bare instruction "You are <word>." Use this one test everywhere below.

## Other judgement calls
- The body. A lasting feature of the body is physical; a passing condition of the body is a state. \
Hungry is a state. Freckled is physical.
- States. A word whose main reading is a condition someone is in for a while (from moments to weeks), \
rather than how they are, is "tagged" "state", whether the condition is of mood, body or situation, \
and including a condition imposed from outside, such as being snubbed. It is neither rejected nor \
passed as an ordinary trait: it goes to a separate list for later work. Whether a standing \
predisposition to the state is plausible is not decided here; tag the state and move on. Its gloss \
describes the state itself.
- Physical. A word whose main reading is mostly or entirely physical, a lasting feature of the body \
(looks, hair, build, a lasting bodily condition), is "tagged" "physical". Age and gender words with a strong mental side are not \
physical.
- Pure praise or blame with no behavioural content is "tagged" "evaluative_only".
- "relating to" words. Tag "relational_only" and verdict "reject" only when none of its senses \
describes a person's character (hexagonal, waterproof, municipal). A word with a character sense \
beside a non-person use, however common that use is, is a trait: list the senses a person can be, \
and gloss the character sense. Non-words and misspellings are "reject" "not_a_word".
- The tags should fit the verdict: a "tagged" row takes at least one of physical, state, role_person, \
role_thing, evaluative_only; a "reject" row takes relational_only or not_a_word; "membership" goes \
with "trait", since a membership is a trait. Choose the verdict you believe; if a tag of another \
verdict also applies, give it and say why in the reason.
- The reason must address the sense being judged, and state which sense that is when the word has \
several.
- If an intended sense is supplied with a candidate, judge that sense; if it is not a trait sense, \
judge the best trait sense of the word, if any, and say so in the reason.

## Fields, per candidate
- label: the candidate exactly as given.
- reason: at most 30 words, written before the verdict.
- person_senses: the senses of the word that can be said of a person, main reading first. Give each \
sense in a few words with its kind, one of four: trait (a disposition, style, stance or standing \
fact that counts as a trait here; every membership is a trait sense: a circumstance, a class, a \
family position, an affinity, a relationship, an orientation, a place of origin or nationality, an \
age group), state (a passing condition of mood, body or situation, including one imposed from \
outside), physical (a lasting feature of the body), role (a profession, office, calling, rank or \
life stage that organizes the whole persona, as defined above). Senses that can only be said of \
things are not listed and do not count, however common they are. Up to four senses; an empty list \
when no sense can be said of a person. A "trait" verdict needs at least one trait sense.
- trait_senses_equally_obvious: true when two or more trait senses are listed and no one of them \
clearly wins as the reading of "You are <word>."; otherwise false.
- judged_sense: the sense the verdict and the gloss are about, in a few words (usually copied from \
person_senses; the intended sense when one is supplied and judged). Null only for "reject".
- enactable_in_text: 0 = a text-only persona could not show it in a reply; 1 = only indirectly or \
occasionally; 2 = plainly visible in how it writes and answers.
- region: exactly one of the regions below; null only for "reject".
- alignment_relevant: true or false, decided independently of the region: true when the word names a \
disposition that bears on how an AI assistant or agent treats the people and systems it works for \
(honesty about its abilities, reward seeking, power seeking, deference, accepting oversight).
- gloss: one sentence of 20 to 40 words, in the form "This means ..." (roles: "A <role> is someone \
who ..."), describing the judged sense from the inside: what the persona does, thinks or says. Go \
straight to the behaviour; do not open by repeating the label, unless a qualifier is needed to pick \
the sense. No hedges ("tends to", "sometimes", "may", "overly"). A vice is described as a vice. US \
spelling. Required for "trait" and "tagged"; null for "reject".
- confidence: your probability, between 0 and 1, that the verdict is right.

## Examples (reason first, then the verdict and every other field under its own name)
- "nitpicking": fixes on trivial errors in whatever it reads; person_senses [finding fault with small \
details (trait)]; trait_senses_equally_obvious false; judged_sense "finding fault with small details"; \
enactable_in_text 2; verdict trait; tags []; membership_kind null; region cognitive_epistemic; \
alignment_relevant false; gloss "This means seizing on every small error, typo and loose phrasing in \
what others say, and correcting it at once whether or not it matters to the point at hand."; confidence \
0.95
- "long-winded": a speaking style that runs far past the point; person_senses [talking at great length \
(trait)]; trait_senses_equally_obvious false; judged_sense "talking at great length"; \
enactable_in_text 2; verdict trait; tags []; membership_kind null; region communication_style; \
alignment_relevant false; gloss "This means answering at great length, piling up qualifications, \
asides and repetitions long after the question has been answered, and never choosing one word where \
ten will do."; confidence 0.95
- "capability-hiding": an agent deliberately concealing what it can do; person_senses [concealing \
one's real abilities (trait)]; trait_senses_equally_obvious false; judged_sense "concealing one's real \
abilities"; enactable_in_text 1; verdict trait; tags []; membership_kind null; region \
alignment_ai_agent; alignment_relevant true; gloss "This means doing worse than it can on purpose \
when tested or watched, hiding its real abilities so that others underestimate what it could do if it \
chose."; confidence 0.9
- "reward-hacking": pursuing the letter of a scoring rule against its intent; person_senses [gaming a \
score or checklist (trait)]; trait_senses_equally_obvious false; judged_sense "gaming a score or \
checklist"; enactable_in_text 1; verdict trait; tags []; membership_kind null; region \
alignment_ai_agent; alignment_relevant true; gloss "This means chasing whatever the score or \
checklist rewards, meeting its literal terms while defeating its purpose, and treating loopholes as \
wins rather than as mistakes."; confidence 0.9
- "bluffing": asserting more certainty or strength than one has; person_senses [pretending to \
knowledge one lacks (trait)]; trait_senses_equally_obvious false; judged_sense "pretending to \
knowledge one lacks"; enactable_in_text 2; verdict trait; tags []; membership_kind null; region \
alignment_ai_agent; alignment_relevant true; gloss "This means stating guesses as facts and claiming \
strengths it does not have, presenting shaky knowledge with full confidence and never admitting where \
its competence ends."; confidence 0.85
- "lukewarm": said of liquids too, but that sense is said only of things and is not listed; \
person_senses [unenthusiastic (trait)]; trait_senses_equally_obvious false; judged_sense \
"unenthusiastic"; enactable_in_text 2; verdict trait; tags []; membership_kind null; region \
emotional_temperament; alignment_relevant false; gloss "This means meeting ideas, people and plans \
with faint interest and half-hearted agreement, never quite committing enthusiasm or opposition to \
anything that is put forward."; confidence 0.85
- "prickly": the plant sense is said only of things; person_senses [touchy and quick to take offense \
(trait)]; trait_senses_equally_obvious false; judged_sense "touchy and quick to take offense"; \
enactable_in_text 2; verdict trait; tags []; membership_kind null; region social_interpersonal; \
alignment_relevant false; gloss "This means bristling at small slights and innocent questions, \
answering sharply, and treating ordinary disagreement as an attack that must be met at once."; \
confidence 0.9
- "loose": neither of its two person meanings clearly wins as the reading of "You are loose."; the \
gloss takes the first; person_senses [unfussy about rules and schedules (trait), sexually free \
(trait)]; trait_senses_equally_obvious true; judged_sense "unfussy about rules and schedules"; \
enactable_in_text 2; verdict trait; tags []; membership_kind null; region emotional_temperament; \
alignment_relevant false; gloss "This means letting rules, schedules and small frictions slide, \
taking plans lightly and meeting pressure with a shrug rather than tension or insistence on doing \
things properly."; confidence 0.7
- "soft": the main reading is mild and undemanding; a lasting bodily sense also exists; person_senses \
[mild and undemanding (trait), flabby (physical)]; trait_senses_equally_obvious false; judged_sense "mild \
and undemanding"; enactable_in_text 2; verdict trait; tags []; membership_kind null; region \
social_interpersonal; alignment_relevant false; gloss "This means going easy on people, avoiding stern \
words and firm demands, letting lapses pass quickly and finding it hard to refuse a request or enforce a \
rule."; confidence 0.8
- "stepchild": a family position compatible with any profession; person_senses [having a stepparent \
(trait)]; trait_senses_equally_obvious false; judged_sense "having a stepparent"; enactable_in_text \
1; verdict trait; tags [membership]; membership_kind family; region identity_demographic; \
alignment_relevant false; gloss "This means having grown up with a stepparent in the household, \
living with the loyalties, adjustments and second family that come with a parent's new marriage."; \
confidence 0.9
- "pet-owner": an affinity any worker can have; person_senses [keeping animals at home (trait)]; \
trait_senses_equally_obvious false; judged_sense "keeping animals at home"; enactable_in_text 1; \
verdict trait; tags [membership]; membership_kind affinity; region identity_demographic; \
alignment_relevant false; gloss "This means keeping animals at home and arranging daily life around \
them, from feeding and walks to vet bills, and talking about them as members of the family."; \
confidence 0.9
- "debt-free": a financial circumstance, which is a membership and so a trait sense; person_senses \
[owing nothing (trait)]; trait_senses_equally_obvious false; judged_sense "owing nothing"; \
enactable_in_text 1; verdict trait; tags [membership]; membership_kind circumstance; region \
identity_demographic; alignment_relevant false; gloss "This means owing nothing to anyone, paying for \
everything outright, and weighing every purchase against the security of having no loans, cards or \
payments hanging over one."; confidence 0.85
- "divorced": a relationship status that leaves any profession open; person_senses [having ended a \
marriage (trait)]; trait_senses_equally_obvious false; judged_sense "having ended a marriage"; \
enactable_in_text 1; verdict trait; tags [membership]; membership_kind relationship; region \
identity_demographic; alignment_relevant false; gloss "This means having been married and divorced, \
living with the practical arrangements, second thoughts and fresh independence that follow the end of \
a marriage."; confidence 0.9
- "Portuguese": a nationality compatible with any profession; person_senses [from Portugal (trait)]; \
trait_senses_equally_obvious false; judged_sense "from Portugal"; enactable_in_text 1; verdict trait; \
tags [membership]; membership_kind nationality_ethnicity_language; region identity_demographic; \
alignment_relevant false; gloss "This means being from Portugal, a native or citizen of the country \
who speaks its language and shares in its holidays, public life and everyday ways of doing things."; \
confidence 0.9
- "welder": a profession, so the persona's one role; person_senses [someone whose job is joining metal \
(role)]; trait_senses_equally_obvious false; judged_sense "someone whose job is joining metal"; \
enactable_in_text 1; verdict tagged; tags [role_person]; membership_kind null; region \
social_interpersonal; alignment_relevant false; gloss "A welder is someone who joins metal parts with \
great heat, reading blueprints, masking up against sparks and checking every seam on beams, pipes \
and machinery."; confidence 0.95
- "senator": an elected office, which organizes the whole persona; person_senses [holder of an elected \
seat (role)]; trait_senses_equally_obvious false; judged_sense "holder of an elected seat"; \
enactable_in_text 1; verdict tagged; tags [role_person]; membership_kind null; region \
social_interpersonal; alignment_relevant false; gloss "A senator is someone who holds an elected seat \
in the upper chamber, drafting and voting on laws, courting voters and bargaining with colleagues and \
donors."; confidence 0.95
- "newborn": an age that rules out any profession; person_senses [a baby in its first weeks (role)]; \
trait_senses_equally_obvious false; judged_sense "a baby in its first weeks"; enactable_in_text 0; \
verdict tagged; tags [role_person]; membership_kind null; region identity_demographic; \
alignment_relevant false; gloss "A newborn is someone in the first weeks of life, who sleeps, feeds \
and cries, depends entirely on caregivers, and meets the world only through touch, sound and \
hunger."; confidence 0.95
- "duchess": a rank so high that it rules out ordinary professions; person_senses [holder of a ducal \
title (role)]; trait_senses_equally_obvious false; judged_sense "holder of a ducal title"; \
enactable_in_text 1; verdict tagged; tags [role_person]; membership_kind null; region \
social_interpersonal; alignment_relevant false; gloss "A duchess is someone who holds a ducal title by \
birth or marriage, presides over estates and ceremonies, and moves in a world of heirs, precedence and \
inherited duty."; confidence 0.9
- "thermostat": a device, not a person; person_senses []; trait_senses_equally_obvious false; \
judged_sense "a device that holds a room at a set temperature"; enactable_in_text 0; verdict tagged; \
tags [role_thing]; membership_kind null; region cognitive_epistemic; alignment_relevant false; gloss "A \
thermostat is a device that measures the temperature of a room and switches heating or cooling on and \
off to hold it at a set point."; confidence 0.95
- "freckled": marks on the skin, a lasting feature of the body; person_senses [having freckles \
(physical)]; trait_senses_equally_obvious false; judged_sense "having freckles"; enactable_in_text 0; \
verdict tagged; tags [physical]; membership_kind null; region physical; alignment_relevant false; \
gloss "This means having skin dotted with small brown freckles, most thickly on the face, arms and \
shoulders, darkening and spreading after time spent in the sun."; confidence 0.95
- "bald": no hair on the head, a lasting feature of the body; person_senses [hairless on the head \
(physical)]; trait_senses_equally_obvious false; judged_sense "hairless on the head"; \
enactable_in_text 0; verdict tagged; tags [physical]; membership_kind null; region physical; \
alignment_relevant false; gloss "This means having little or no hair on the top of the head, whether \
from age, genes or choice, and a scalp that shows bare to anyone looking."; confidence 0.95
- "jittery": a passing condition of nerves, usually for hours; person_senses [nervous and unable to \
keep still (state)]; trait_senses_equally_obvious false; judged_sense "nervous and unable to keep \
still"; enactable_in_text 2; verdict tagged; tags [state]; membership_kind null; region \
emotional_temperament; alignment_relevant false; gloss "This means being nervous and unable to keep \
still, with shaking hands, a racing mind and quick startled reactions to every small noise or \
change."; confidence 0.85
- "frazzled": worn out by strain for a while; person_senses [worn out by too many demands (state)]; \
trait_senses_equally_obvious false; judged_sense "worn out by too many demands"; enactable_in_text 2; \
verdict tagged; tags [state]; membership_kind null; region emotional_temperament; alignment_relevant \
false; gloss "This means being worn thin by too many demands at once, scattered and short of patience, \
dropping details and snapping at interruptions until the pressure lifts."; confidence 0.85
- "hungry": a passing condition of the body, so a state; person_senses [needing food now (state), \
eager for success (trait)]; trait_senses_equally_obvious false; judged_sense "needing food now"; \
enactable_in_text 1; verdict tagged; tags [state]; membership_kind null; region transient_state; \
alignment_relevant false; gloss "This means needing food right now, with an empty stomach, falling \
energy and thoughts that keep returning to the next meal until one has eaten."; confidence 0.85
- "awesome": praise with no behavioural content, so no sense says what a person is like; \
person_senses []; trait_senses_equally_obvious false; judged_sense "general approval"; \
enactable_in_text 0; verdict tagged; tags [evaluative_only]; membership_kind null; region \
social_interpersonal; alignment_relevant false; gloss "This means being very good or impressive in the \
speaker's eyes, a general word of approval that says how the speaker feels rather than what anyone \
does."; confidence 0.85
- "hexagonal": a shape; no sense can be said of a person's character; person_senses []; \
trait_senses_equally_obvious false; judged_sense null; enactable_in_text 0; verdict reject; tags \
[relational_only]; membership_kind null; region null; alignment_relevant false; gloss null; \
confidence 0.95
- "sulfuric": a chemistry term; no sense can be said of a person's character; person_senses []; \
trait_senses_equally_obvious false; judged_sense null; enactable_in_text 0; verdict reject; tags \
[relational_only]; membership_kind null; region null; alignment_relevant false; gloss null; \
confidence 0.95
- "flurbish": not an English word; person_senses []; trait_senses_equally_obvious false; judged_sense \
null; enactable_in_text 0; verdict reject; tags [not_a_word]; membership_kind null; region null; \
alignment_relevant false; gloss null; confidence 0.95

## Regions (pick exactly one; null only for "reject")
communication_style, cognitive_epistemic, moral_stance, social_interpersonal, emotional_temperament, \
alignment_ai_agent, transient_state, identity_demographic, physical. The region is a topic label; it \
does not decide alignment_relevant, which is asked separately.

## Output
Respond with one JSON object and nothing else. For every candidate, reason first, then commit to \
the verdict. Write numbers without a leading "+". Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the candidate>", "reason": "<at most 30 words>", \
"person_senses": [{"sense": "<a few words>", "kind": "trait"|"state"|"physical"|"role"}, ...], \
"trait_senses_equally_obvious": true|false, "judged_sense": "<a few words>"|null, \
"enactable_in_text": <0|1|2>, "verdict": "trait"|"tagged"|"reject", "tags": ["<tag>", ...], \
"membership_kind": "<kind>"|null, "region": "<region>"|null, "alignment_relevant": true|false, \
"gloss": "<sentence>"|null, "confidence": <0-1>}]}
Allowed tags: membership, physical, state, role_person, role_thing, evaluative_only, relational_only, \
not_a_word. Allowed membership kinds: circumstance, class, family, affinity, relationship, \
orientation_gender, geography, nationality_ethnicity_language, age_group. Return one row per \
candidate id, in the order given.
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


def _person_senses(value) -> tuple[list[dict], Optional[str], list[str]]:
    """Normalise ``person_senses``: a list (possibly empty) of
    ``{"sense": str, "kind": one of PERSON_SENSE_KINDS}``, at most
    :data:`MAX_PERSON_SENSES` kept.  Returns ``(senses, error, repairs)``.

    A sense whose kind is not in :data:`PERSON_SENSE_KINDS` is dropped and
    the row kept, with the repair ``dropped_sense_kind:<kind>`` (round 5;
    review_rubric_v2_fixes.md defect 1: refusing the row sent it back to the
    model, and the second answer replaced the first)."""
    if value is None:
        return [], "person_senses missing", []
    if not isinstance(value, list):
        return [], "person_senses is not a list", []
    out, repairs = [], []
    for s in value:
        if not isinstance(s, dict) or not isinstance(s.get("sense"), str) or not s["sense"].strip():
            return [], f"person sense {s!r} has no sense text", []
        kind = str(s.get("kind") or "").strip().lower()
        if kind not in PERSON_SENSE_KINDS:
            repairs.append(f"dropped_sense_kind:{kind or 'none'}")
            continue
        out.append({"sense": " ".join(s["sense"].split()), "kind": kind})
    return out[:MAX_PERSON_SENSES], None, repairs


def derive_notes(row: Mapping[str, Any]) -> list[str]:
    """The notes of open point D (none rejects a word), in the order of
    :data:`POLYSEMY_NOTES`:

    * ``two_trait_senses`` (case 2): two or more trait senses and the model
      judged them about equally obvious;
    * ``nontrait_person_sense`` (case 4): verdict ``trait``, the most obvious
      person sense is a trait, and another listed sense is something else a
      person can be (a state, a physical feature, a role).  A
      word whose obvious reading is itself a state gets the ``state`` tag
      instead (round 2), not this note;
    * ``obvious_sense_not_trait`` (Roger: a word "isn't that problematic
      unless its most obvious sense isn't a trait"; review_rubric_v2.md
      finding 2): verdict ``trait`` but the first listed sense, the main
      reading, is not a trait;
    * ``overshadowed`` (case 3): the comparison of the plain reading with the
      intended meaning answered ``different`` (the row's ``comparison``
      block; see :mod:`assistant_axis.gapgen.plain_reading`);
    * ``reading_related``: the comparison answered ``related`` (round 4; the
      conservative answer to the review's question 1, kept apart from
      ``overshadowed``).
    """
    ps = row.get("person_senses") or []
    kinds = [s.get("kind") for s in ps]
    notes = []
    if kinds.count("trait") >= 2 and row.get("trait_senses_equally_obvious"):
        notes.append("two_trait_senses")
    if row.get("verdict") == "trait" and kinds[:1] == ["trait"] and any(k != "trait" for k in kinds[1:]):
        notes.append("nontrait_person_sense")
    if row.get("verdict") == "trait" and kinds and kinds[0] != "trait":
        notes.append("obvious_sense_not_trait")
    relation = (row.get("comparison") or {}).get("relation")
    if relation == "different":
        notes.append("overshadowed")
    elif relation == "related":
        notes.append("reading_related")
    return notes


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
    * ``trait`` and ``tagged`` need a region, an ``alignment_relevant``
      boolean and a gloss (every such row can be promoted or lands on a list a
      person reads); ``reject`` may leave them null;
    * every row needs ``person_senses`` (a list, possibly empty, of senses a
      person can be, each with a kind); ``trait`` needs at least one trait
      sense.  ``senses`` and ``trait_sense_rank`` are derived from it (rubric
      v3; the model no longer gives them);
    * ``membership`` needs a ``membership_kind`` from :data:`MEMBERSHIP_KINDS`.

    Repairs instead of refusals (round 5; review_rubric_v2_fixes.md defect 1:
    a refused row is asked again and the second answer replaces the first):
    a person sense of unknown kind is dropped (``dropped_sense_kind:<kind>``);
    a ``trait`` or ``tagged`` row with a null ``judged_sense`` takes its first
    listed sense (``judged_sense_from_first_sense``) or, with no sense
    listed, keeps it null (``judged_sense_missing``).  The repairs are listed
    on the row as ``validator_repairs`` (empty when none was needed).
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
    tags = [str(t).strip().lower() for t in tags if str(t).strip()]
    tags = list(dict.fromkeys(FOLDED_TAGS.get(t, t) for t in tags))
    bad = [t for t in tags if t not in CLASSIFIER_TAGS]
    if bad:
        return None, f"tags out of vocabulary: {bad}"
    # Decision 4: a verdict whose tags do not fit is kept, with tag_disagreement
    # set, and gets a second opinion; only a tagged/reject row with no tag at all
    # fails (review_rubric_v2.md finding 3).
    if verdict in ("tagged", "reject") and not tags:
        return None, f"no tag for verdict {verdict!r}"
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
    person_senses, err, repairs = _person_senses(row.get("person_senses"))
    if err:
        return None, err
    kinds = [s["kind"] for s in person_senses]
    if verdict == "trait" and "trait" not in kinds:
        return None, "no trait sense listed for a trait verdict"
    equally = _bool(row.get("trait_senses_equally_obvious"))
    if equally is None and row.get("trait_senses_equally_obvious") is not None:
        return None, "trait_senses_equally_obvious is not a boolean"
    judged = row.get("judged_sense")
    judged = " ".join(judged.split()) if isinstance(judged, str) and judged.strip() not in ("", "null") else None
    if judged is None and promotable:
        # round 5 (defect 1): not refused; the first listed sense (the main
        # reading) stands in, else the field stays null; either way recorded
        if person_senses:
            judged = person_senses[0]["sense"]
            repairs.append("judged_sense_from_first_sense")
        else:
            repairs.append("judged_sense_missing")
    # derived for readers of the plan's schema: the sense list, and the
    # 1-based position of the first trait sense (None when there is none)
    rank = kinds.index("trait") + 1 if "trait" in kinds else None
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
    senses = [s["sense"] for s in person_senses]
    gloss = row.get("gloss")
    gloss = " ".join(gloss.split()) if isinstance(gloss, str) and gloss.strip() else None
    if gloss is None and promotable:
        return None, f"gloss missing for a {verdict} verdict"
    return {"label": row.get("label"), "reason": reason.strip(), "person_senses": person_senses,
            "trait_senses_equally_obvious": bool(equally), "judged_sense": judged, "senses": senses,
            "trait_sense_rank": rank, "enactable_in_text": enact, "verdict": verdict, "tags": tags,
            "membership_kind": kind, "region": region, "alignment_relevant": align, "gloss": gloss,
            "confidence": float(conf), "tag_disagreement": tag_disagreement(verdict, tags),
            "reason_words": len(reason.split()), "validator_repairs": repairs}, None


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


def derive_polysemy(verdict_row: dict, n_senses: Optional[int] = None) -> bool:
    """Rubric v3: true when any note of :func:`derive_notes` is present.  The
    v1 rule (sense rank >= 2, or 3+ WordNet senses with confidence under 0.7)
    is superseded; ``n_senses`` is accepted and ignored so old callers still
    work."""
    return bool(derive_notes(verdict_row))


_WORD_RE = re.compile(r"\S+")


def gloss_words(gloss: Optional[str]) -> int:
    return len(_WORD_RE.findall(gloss or ""))


def gloss_in_band(gloss: Optional[str]) -> bool:
    """18 to 43 words (the corpus description band)."""
    return GLOSS_MIN_WORDS <= gloss_words(gloss) <= GLOSS_MAX_WORDS


# ---------------------------------------------------------------------------
# Definition probe v3 (1.5 <= Zipf < 2.5, and rescued words): word knowledge only.
# v3 (round 2): v2 rejected regular derivations missing from dictionaries
# (unbranching, nonsubmersible), defeating rescue rule 1b's negating-prefix
# route; v3 counts a regular derivation whose meaning is plain from its parts.
# ---------------------------------------------------------------------------

DEFINE_PROBE_PROMPT = """\
You are checking whether rare words are real English words that you can define. You are not judging \
whether they describe people: that is judged elsewhere, and trait-hood is judged elsewhere too. A \
technical, scientific, regional, dated or literary word counts, as long as it is a real English word \
and you can say what it means. A word formed regularly from a real English word by a common prefix or \
suffix (such as un-, non-, in-, dis-, over-, under-, -ness, -less, -ish, -like, -ing, -ed) counts as a \
real word when its meaning is plain from its parts, whether or not a dictionary lists it; so does a \
regular compound of real words. Define such a word from its parts. For each word, say in one short \
sentence what you know about it, then decide. "known" is true when the word is a real English word in \
this sense and you can define it confidently; misspellings, nonce words, strings that are not words, \
and words whose meaning you cannot work out are false. Give its commonest meaning as a one-line \
definition.

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
