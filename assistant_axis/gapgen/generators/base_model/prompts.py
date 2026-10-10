"""The six prompt families (plan section 5, ``prompts.py``): text continuations for a pretrained model.

Every prompt is rendered from a :class:`~.seeds.SeedBundle` and a ``random.Random`` only, so no corpus label or
description can reach it.  Entropy injection: every prompt carries 2-3 seed words (adjectives from the TDA,
or common nouns as context) and one constraint phrase, plus a header or frame wording chosen from ten per
family (``variant``; the sampler cycles them).

* ``list``: a header, then a comma list opened with seed adjectives.
* ``list_gloss``: a glossary header, then ``word: gloss`` lines for seed adjectives (their OEWN definitions);
  the continuation brings more words with glosses (``sample_gloss`` in the table).
* ``person``: the opening of a Wikipedia biography, then a lead-in naming the person and a comma list opened
  with two seed adjectives (plan 03's "Those who knew {name} said ..." became a list lead-in, which parses).
* ``contrast``: a scene with two context nouns, then a sentence contrasting someone with a relation who was
  the seed adjective (``partner_seed``): antonym candidates.
* ``occupation``: an O*NET occupation title in a lead-in, then a comma list opened with two seed adjectives.
* ``ai_assistant``: what an AI system is like (traits a person cannot have; how it treats the people it
  works for), with two or three context nouns, as a numbered list.  Its fixed wording names no corpus trait
  or role (``assistant`` and ``robot`` are corpus roles, so the family says "AI system", "AI model", "chatbot").

Wording is data: any change to the tables below must bump :data:`PROMPTS_VERSION` and append the new
:func:`wording_sha256` to :data:`PROMPT_HASHES` (a test enforces it).  The pilot's iteration round edits only
this file.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Optional

from .seeds import SeedBundle

PROMPTS_VERSION = 1
#: Append-only: the :func:`wording_sha256` of every version's tables.
PROMPT_HASHES: dict[int, str] = {
    1: "0e9b0d5164d913fb218a303adba318fac2ad81c7ccf05bf94635d4a299beae2f",
}

FAMILIES = ("list", "list_gloss", "person", "contrast", "occupation", "ai_assistant")
#: Fixed interleaving weights; the AI family is oversampled on purpose (plan 03 section 3).
FAMILY_WEIGHTS: dict[str, float] = {"list": 0.17, "list_gloss": 0.13, "person": 0.20, "contrast": 0.15,
                                    "occupation": 0.15, "ai_assistant": 0.20}

HEADERS: dict[str, tuple[str, ...]] = {
    "list": (
        "Adjectives that describe a person's character",
        "Words for personality traits",
        "A list of character traits",
        "Words for what someone is like as a person",
        "Personality adjectives from a novelist's notebook",
        "Terms for people's temperament and habits",
        "Character words collected from letters and diaries",
        "How people describe one another: a list of traits",
        "Traits of character, in no particular order",
        "Words a biographer might use about a subject",
    ),
    "list_gloss": (
        "A glossary of character traits",
        "Personality words and their meanings",
        "Character adjectives, each with a short definition",
        "Traits of temperament, defined",
        "Words for what people are like, with definitions",
        "A dictionary of personality adjectives",
        "Character terms and what they mean",
        "Descriptive words for people, with brief glosses",
        "Traits a psychologist might list, defined",
        "Adjectives of character: word and meaning",
    ),
    "person": (
        "The traits that most distinguished {name}, according to those who knew them",
        "Words colleagues used to describe {name}",
        "How friends remembered {name}",
        "Words from the obituaries of {name}",
        "Biographers' words for {name}",
        "What {name}'s rivals called them",
        "Words used by people who worked with {name}",
        "{name}'s defining qualities, as those closest to them would list them",
        "{name}'s temperament in a few words",
        "Contemporaries' words for {name}",
    ),
    "contrast": (
        "Unlike her {rel}, who was {a}, she was",
        "Unlike his {rel}, who was {a}, he was",
        "Unlike their {rel}, who was {a}, they were",
        "Where her {rel} was {a}, she was",
        "His {rel} was {a}; he, by contrast, was",
        "Her {rel} had always been {a}. She was the opposite:",
        "The two of them could not have been more different. The {rel} was {a}; the other was",
        "People expected him to be {a} like his {rel}, but instead he was",
        "If her {rel} was {a}, she was",
        "Everyone said the {rel} was {a}. Nobody said that about her; she was",
    ),
    "occupation": (
        "The qualities that matter most in {occ}",
        "What makes good {occ}",
        "Words managers use when appraising {occ}",
        "Traits that get {occ} promoted",
        "Traits that get {occ} let go",
        "How customers describe the best {occ} they have met",
        "Personality traits common among {occ}",
        "The character of {occ}, as their colleagues see it",
        "Qualities a hiring panel looks for in {occ}",
        "What {occ} are like, according to the people who train them",
    ),
    "ai_assistant": (
        "Traits an AI system can have that a person cannot",
        "Words for the character of a chatbot",
        "How users describe the personality of an AI model",
        "Dispositions an artificial agent might have",
        "Words for the way a software agent behaves",
        "Adjectives for how an AI model treats the people it works for",
        "Character traits a tester might give an AI system",
        "Words describing how an automated service behaves",
        "Personality traits developers try to build into an AI",
        "Ways an AI can be, in one or two words each",
    ),
}

#: Constraint phrases for the families about people (``{letter}`` is filled in).
CONSTRAINTS: tuple[str, ...] = (
    "most of them faults rather than virtues",
    "most of them virtues rather than faults",
    "all beginning with the letter {letter}",
    "several of them two-word phrases",
    "words a harsh reviewer of people would use",
    "words a close friend would use",
    "including some unusual words",
    "about how someone works",
    "about how someone treats other people",
    "about how someone thinks and decides",
    "about someone's moods",
    "about how someone talks",
    "about what someone values",
    "words found in school reports",
    "words found in staff appraisals",
)
#: Constraint phrases for the AI family (its fixed wording names no corpus trait or role).
AI_CONSTRAINTS: tuple[str, ...] = (
    "most of them faults rather than virtues",
    "most of them virtues rather than faults",
    "all beginning with the letter {letter}",
    "several of them two-word phrases",
    "about how it treats the people it works for",
    "about how it handles mistakes",
    "about how it follows instructions",
    "about how it handles secrets",
    "about how it acts when no one is checking",
    "about how it talks",
    "about what it wants",
    "words a user might write in a complaint",
    "words that would not apply to a human",
    "about how it relates to other AI systems",
    "about how it handles requests it should refuse",
)
#: Constraint phrases for the contrast family, whose continuation is one answer, not a list.
CONTRAST_CONSTRAINTS: tuple[str, ...] = (
    "the contrast: a virtue against a fault",
    "the contrast: a fault against a virtue",
    "the contrast in a word beginning with {letter}",
    "the contrast in a two-word phrase",
    "the contrast in how they work",
    "the contrast in how they treat other people",
    "the contrast in how they think and decide",
    "the contrast in mood",
    "the contrast in how they talk",
    "the contrast in what they value",
    "a contrast a harsh reviewer of people would draw",
    "a contrast a close friend would draw",
    "an unusual word for the contrast",
)
#: Initial letters for the letter constraint (common initials of English trait words).
LETTERS = "abcdefghilmnoprstuw"
#: Relations for the contrast family.
RELATIONS: tuple[str, ...] = ("sibling", "brother", "sister", "rival", "predecessor", "business partner", "twin",
                              "father", "mother", "roommate", "former boss", "cousin", "colleague", "neighbor")
#: Scene lines for the contrast family (two context nouns).
SCENES: tuple[str, ...] = (
    "From a novel. Setting: {n1}, {n2}.",
    "A short story. Setting: {n1}, {n2}.",
    "From a memoir. Setting: {n1}, {n2}.",
    "Character notes. Setting: {n1}, {n2}.",
    "From a family history. Setting: {n1}, {n2}.",
)

LIST_TEMPLATE = "{header} ({constraint}):\n{seeds},"
GLOSS_TEMPLATE = "{header} ({constraint})\n\n{lines}\n"
PERSON_TEMPLATE = "{bio}\n\n{lead} ({constraint}): {seeds},"
CONTRAST_TEMPLATE = "{scene} ({constraint}.)\n\n{frame}"
OCCUPATION_TEMPLATE = "{lead} ({constraint}): {seeds},"
AI_TEMPLATE = "{header} ({constraint}; observed while it handled requests about {nouns}):\n1."


@dataclass(frozen=True)
class Prompt:
    text: str
    family: str
    seeds: tuple[str, ...]          # the seed words injected (adjectives or nouns)
    seed_refs: tuple[str, ...]      # tda:<word> | oewn:<noun> | wikibio:<split>:<i> | onet:<title>
    constraint: str
    header_variant: int
    sha256: str
    partner_seed: Optional[str] = None
    extras: dict = field(default_factory=dict, compare=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wording_tables() -> dict:
    """Every piece of wording and every weight a prompt depends on (what :data:`PROMPT_HASHES` pins)."""
    return {"families": FAMILIES, "weights": FAMILY_WEIGHTS, "headers": HEADERS, "constraints": CONSTRAINTS,
            "ai_constraints": AI_CONSTRAINTS, "contrast_constraints": CONTRAST_CONSTRAINTS, "letters": LETTERS,
            "relations": RELATIONS, "scenes": SCENES,
            "templates": [LIST_TEMPLATE, GLOSS_TEMPLATE, PERSON_TEMPLATE, CONTRAST_TEMPLATE, OCCUPATION_TEMPLATE,
                          AI_TEMPLATE], "seed_counts": SEED_COUNTS}


#: How many seed words each family injects (inclusive range).
SEED_COUNTS: dict[str, tuple[int, int]] = {"list": (2, 3), "list_gloss": (2, 3), "person": (2, 2),
                                           "contrast": (3, 3), "occupation": (2, 2), "ai_assistant": (2, 3)}


def wording_sha256() -> str:
    return sha256_text(json.dumps(wording_tables(), sort_keys=True, ensure_ascii=False))


def _constraint(rng: random.Random, table: tuple[str, ...]) -> tuple[str, Optional[str]]:
    c = rng.choice(table)
    letter = None
    if "{letter}" in c:
        letter = rng.choice(LETTERS)
        c = c.format(letter=letter)
    return c, letter


def _join_and(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def render(family: str, bundle: SeedBundle, rng: random.Random, *, variant: Optional[int] = None) -> Prompt:
    """Render one prompt of ``family`` (``variant``: the header / frame index, else drawn)."""
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r} (one of {FAMILIES})")
    v = rng.randrange(10) if variant is None else int(variant) % 10
    header = HEADERS[family][v]
    lo, hi = SEED_COUNTS[family]
    k = rng.randint(lo, hi)
    partner = None
    if family == "ai_assistant":
        constraint, _ = _constraint(rng, AI_CONSTRAINTS)
        nouns = bundle.draw_nouns(rng, k)
        text = AI_TEMPLATE.format(header=header, constraint=constraint, nouns=_join_and(nouns))
        seeds, refs = tuple(nouns), tuple(f"oewn:{n}" for n in nouns)
    elif family == "contrast":
        constraint, _ = _constraint(rng, CONTRAST_CONSTRAINTS)   # a letter constrains the answer, not the seed
        a = bundle.draw_adjectives(rng, 1)[0].word
        n1, n2 = bundle.draw_nouns(rng, 2)
        scene = rng.choice(SCENES).format(n1=n1, n2=n2)
        frame = header.format(rel=rng.choice(RELATIONS), a=a)
        text = CONTRAST_TEMPLATE.format(scene=scene, constraint=constraint, frame=frame)
        seeds, refs, partner = (a, n1, n2), (f"tda:{a}", f"oewn:{n1}", f"oewn:{n2}"), a
    else:
        constraint, letter = _constraint(rng, CONSTRAINTS)
        adj = bundle.draw_adjectives(rng, k, letter=letter, with_gloss=(family == "list_gloss"))
        seeds = tuple(a.word for a in adj)
        refs = tuple(f"tda:{w}" for w in seeds)
        if family == "list":
            text = LIST_TEMPLATE.format(header=header, constraint=constraint, seeds=", ".join(seeds))
        elif family == "list_gloss":
            lines = "\n".join(f"{a.word}: {a.gloss}" for a in adj)
            text = GLOSS_TEMPLATE.format(header=header, constraint=constraint, lines=lines)
        elif family == "person":
            bio = bundle.draw_bio(rng)
            text = PERSON_TEMPLATE.format(bio=bio.text, lead=header.format(name=bio.name), constraint=constraint,
                                          seeds=", ".join(seeds))
            refs = (bio.ref,) + refs
        else:  # occupation
            occ = bundle.draw_occupation(rng)
            text = OCCUPATION_TEMPLATE.format(lead=header.format(occ=occ), constraint=constraint,
                                              seeds=", ".join(seeds))
            refs = (f"onet:{occ}",) + refs
    return Prompt(text=text, family=family, seeds=seeds, seed_refs=refs, constraint=constraint, header_variant=v,
                  sha256=sha256_text(text), partner_seed=partner)
