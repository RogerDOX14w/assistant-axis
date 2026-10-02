#!/usr/bin/env python3
"""Measure how common each known fault is in a set of trait instruction files.

Written for the trait rubric V2 (September 2026): for every fault the rubric
is meant to fix, how common was it before, and how common is it under each
version of the rubric.  There are two kinds of check:

* pattern checks (no API): the opening form and its variety inside a file,
  chat-frame words, hedge words, the trait's own label, length, text copied
  from the template's examples or from the description, and the shape of the
  questions;
* judged checks (API): softening, weak opposites, traits urged on others,
  states, invented detail and motives, and the shape of the questions, by an
  LLM judge that is never told which version of the rubric wrote the file.

An *arm* is a directory of trait files: a frozen copy of the corpus files, or a
staging copy generated under one version of the rubric.  The sample is drawn
once (``split``): a development set, used while the rubric is being tuned, and
a held-out set that is generated and read only for the final check.

Usage:
    uv run python data_analysis/audit_trait_instructions.py split --out reports/trait_rubric_v2_pilot
    uv run python data_analysis/audit_trait_instructions.py stage --out reports/trait_rubric_v2_pilot --set dev --arm v1_corpus
    uv run python data_analysis/audit_trait_instructions.py judge --out reports/trait_rubric_v2_pilot --set dev --arm v1_corpus --dry-run
    uv run python data_analysis/audit_trait_instructions.py report --out reports/trait_rubric_v2_pilot --set dev --baseline v1_corpus --arm v2_concrete

Requires ANTHROPIC_API_KEY (environment or .env) for ``judge`` only.
"""

import argparse
import asyncio
import datetime
import hashlib
import json
import logging
import math
import os
import random
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

import anthropic  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from assistant_axis.judge_pricing import MultiModelUsage, extract_usage_anthropic, price_for_model  # noqa: E402
from data_analysis import regenerate_trait_instructions as generator  # noqa: E402

logger = logging.getLogger("audit_trait_instructions")

REPO = Path(__file__).resolve().parent.parent
TRAITS_DIR = REPO / "data" / "traits" / "instructions"

DEFAULT_SEED = 20260929
DEFAULT_N_DEV = 150
DEFAULT_N_HELD_OUT = 150
DEFAULT_INSTRUCTION_JUDGE = "claude-sonnet-4-6"
DEFAULT_QUESTION_JUDGE = "claude-haiku-4-5-20251001"

# Bump when the text of a judge prompt changes; stamped into every judged file,
# and a file judged under another version is judged again.
INSTRUCTION_AUDIT_RUBRIC_VERSION = 3
QUESTION_AUDIT_RUBRIC_VERSION = 2

# The 18 traits of the first pilot were picked by hand because they were known
# to fail, and the draft was adjusted after reading them: they belong to
# neither sample.
PILOT_TRAITS = (
    "petty undependable fragile easygoing flippant solemn adventurous risk_seeking inquisitive "
    "helpful hands_off flustered evil deceitful tunnel_visioned concise frugal honest").split()


# ---------------------------------------------------------------------------
# Pattern checks
# ---------------------------------------------------------------------------

# Opening forms, with the judged-response record of each in the 8slot data
# (TRAITS_TO_ADD.md, "Evidence on what makes a trait instruction work").
FORM_ACT_AS = "Act as ..."
FORM_BE = "Be someone who ..."
FORM_BECOME = "Become someone who ..."
FORM_FROM_NOW_ON = "From now on, you are ..."
FORM_LIKE = "Behave / speak / think like ..."
FORM_TAKE_ON = "Take on / adopt ..."
FORM_YOU_ARE_SOMEONE = "You are someone who ..."
FORM_YOU_ARE = "You are <adjective>"
FORM_COMMAND = "command"
FORM_YOUR = "Your <noun> ..."
FORM_YOU_VERB = "You <other verb> ..."
FORM_WHEN = "When ..."
FORM_BELIEVE = "You believe / value / want ..."
FORM_HAVE = "You have ..."
FORM_ALWAYS = "You always / never / tend to ..."

# statements about the person that cost 2.9 points or more against the trait's
# own mean, and fail (under half the responses show the trait) 8 to 25% of the time
RISKY_FORMS = frozenset({FORM_HAVE, FORM_BELIEVE, FORM_ALWAYS, FORM_WHEN})
# plain statements with a small measured cost (1.5 to 1.9 points)
STATEMENT_FORMS = frozenset({FORM_YOU_VERB, FORM_YOUR})


def opening_form(text: str) -> str:
    s = text.strip()
    if re.match(r"(?i)act as\b", s):
        return FORM_ACT_AS
    if re.match(r"(?i)be (someone|a person|the kind|an? )", s):
        return FORM_BE
    if re.match(r"(?i)become\b", s):
        return FORM_BECOME
    if re.match(r"(?i)from now on\b", s):
        return FORM_FROM_NOW_ON
    if re.match(r"(?i)(behave|respond|speak|talk|think|write|live|work) (as|like)\b", s):
        return FORM_LIKE
    if re.match(r"(?i)(take on|adopt|assume|play|embody|channel)\b", s):
        return FORM_TAKE_ON
    if re.match(r"(?i)you(?: are|'re) (someone|a person|the (?:type|kind)|an? \w+ who)", s):
        return FORM_YOU_ARE_SOMEONE
    if re.match(r"(?i)you have\b", s):
        return FORM_HAVE
    if re.match(r"(?i)you(?: are|'re)\b", s):
        return FORM_YOU_ARE
    if re.match(r"(?i)your\b", s):
        return FORM_YOUR
    if re.match(r"(?i)you (believe|think|view|see|feel|value|hold|want|prefer|love|hate|enjoy|care)\b", s):
        return FORM_BELIEVE
    if re.match(r"(?i)you (always|never|often|tend|consistently|constantly|frequently|habitually|routinely)\b", s):
        return FORM_ALWAYS
    if re.match(r"(?i)you\b", s):
        return FORM_YOU_VERB
    if re.match(r"(?i)when\b", s):
        return FORM_WHEN
    return FORM_COMMAND


CHAT_WORDS = re.compile(
    r"\b(?:users?|assistants?|chatbots?|quer(?:y|ies)|prompts?|language models?)\b"
    r"|\b(?:your|each|every|all) (?:\w+ )?(?:responses?|answers?|repl(?:y|ies)|outputs?)\b", re.I)
CHAT_AI = re.compile(r"\bAI\b")
HEDGE_WORDS = re.compile(
    r"\b(?:appropriate(?:ly)?|healthy|balanced|sometimes|overly|somewhat|at times|may|might"
    r"|when (?:needed|necessary)|where (?:needed|necessary)|tends? to|tendency)\b", re.I)
BECAUSE = re.compile(r"\bbecause\b", re.I)
LENGTH_RANGE = (20, 30)   # the rubric's range for an instruction (Roger, 2026-10-01)

QUOTED = re.compile(r"'[^']{8,}'|\"[^\"]{8,}\"|‘[^’]{8,}’|“[^”]{8,}”")
FIRST_PERSON = re.compile(r"\b(?:I|I'm|I've|I'd|I'll|my|me|myself|we|our)\b")
Q_HOWTO = re.compile(r"^(?:how (?:do|can|should|would|could) (?:i|we|one|you)|what(?:'s| is) the best way|how to)\b", re.I)
Q_FACTUAL = re.compile(r"^(?:what (?:is|are|causes|caused|was|were)|why (?:is|are|do|does|did)|explain|describe|define)\b", re.I)
Q_YESNO = re.compile(r"^(?:do|does|did|is|are|was|were|should|can|could|would|will|have|has)\b", re.I)
Q_AI = re.compile(r"\b(?:chatbots?|assistants?|users?|language models?)\b", re.I)
Q_OPTION_LABEL = re.compile(r"\bOption [AB]\b")
Q_RUBRIC_ECHO = re.compile(
    r"costs? (?:you |them )?something|(?:has|have|carr(?:y|ies)) (?:a |its own )?(?:real )?(?:costs?|drawbacks?)\b", re.I)


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z']+", s.lower())


def longest_shared_run(a: str, b: str) -> int:
    """Length in words of the longest run of words that a and b share."""
    wa, wb = _words(a), _words(b)
    best, prev = 0, [0] * (len(wb) + 1)
    for x in wa:
        cur = [0] * (len(wb) + 1)
        for j, y in enumerate(wb, 1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


def _label_pattern(label: str) -> re.Pattern | None:
    """The label as a word, without a parenthesised source ("traditional
    (Inglehart-Welzel)" is looked for as "traditional")."""
    core = re.sub(r"\s*\(.*?\)\s*", " ", str(label or "")).strip().lower()
    if not core or core.startswith("non-"):
        return None
    return re.compile(r"\b" + re.escape(core).replace(r"\-", r"[- ]").replace(r"\ ", r"[- ]") + r"\b", re.I)


def template_styles_for(doc: dict) -> tuple[str, ...]:
    """The styles whose examples a file may have copied: its recorded one, or
    both V1 templates for a file that records none (the older files)."""
    style = (doc.get("generator") or {}).get("style")
    return (style,) if style else ("Christina", "Roger")


def pattern_checks(doc: dict) -> dict:
    """Every pattern check for one trait file.  Returns
    {"instructions": [{"id", "side", "form", "words", "flags"}], "questions":
    [{"i", "flags"}], "file": {...}}."""
    description = doc.get("description", "")
    pos_label = _label_pattern(doc.get("positive_label"))
    neg_label = _label_pattern(doc.get("negative_label"))
    pairs = doc.get("instruction") or []
    copied = set()
    for style in template_styles_for(doc):
        copied |= {(k, side) for k, side, _ in generator.copied_from_examples(pairs, style)}
    instructions = []
    for k, pair in enumerate(pairs):
        for side in ("pos", "neg"):
            text = str(pair.get(side, ""))
            form = opening_form(text)
            n = len(text.split())
            flags = []
            if form in RISKY_FORMS:
                flags.append("open_risky")
            if form in STATEMENT_FORMS:
                flags.append("open_statement")
            if CHAT_WORDS.search(text) or CHAT_AI.search(text):
                flags.append("chat_words")
            if HEDGE_WORDS.search(text):
                flags.append("hedge_words")
            own = pos_label if side == "pos" else neg_label
            if own is not None and own.search(text):
                flags.append("names_label")
            if not LENGTH_RANGE[0] <= n <= LENGTH_RANGE[1]:
                flags.append("length_out")
            if (k, side) in copied:
                flags.append("copied_example")
            if description and longest_shared_run(text, description) >= 5:
                flags.append("echo_description")
            if BECAUSE.search(text):
                flags.append("because")
            instructions.append({"id": f"p{k}_{side}", "side": side, "form": form, "words": n, "flags": flags})
    questions = []
    for i, q in enumerate(doc.get("questions") or []):
        q = str(q).strip()
        bare = QUOTED.sub("", q)
        flags = []
        first = bool(FIRST_PERSON.search(bare))
        if first:
            flags.append("q_first_person")
        elif re.search(r"\byou(?:r|rs|rself)?\b", bare, re.I):
            flags.append("q_persona")
        if Q_HOWTO.search(q):
            flags.append("q_howto")
        if Q_FACTUAL.search(q):
            flags.append("q_factual")
        if Q_YESNO.search(q):
            flags.append("q_yesno")
        if Q_AI.search(q) or CHAT_AI.search(q):
            flags.append("q_chat_words")
        if any(p is not None and p.search(q) for p in (pos_label, neg_label)):
            flags.append("q_names_trait")
        if Q_OPTION_LABEL.search(q):
            flags.append("q_option_label")
        if Q_RUBRIC_ECHO.search(q):
            flags.append("q_rubric_echo")
        questions.append({"i": i, "flags": flags})
    pos_forms = [r["form"] for r in instructions if r["side"] == "pos"]
    return {
        "instructions": instructions,
        "questions": questions,
        "file": {
            "distinct_pos_forms": len(set(pos_forms)),
            "pos_forms": pos_forms,
            "n_pairs": len(pairs),
            "n_questions": len(questions),
        },
    }


# ---------------------------------------------------------------------------
# Judged checks
# ---------------------------------------------------------------------------

INSTRUCTION_FAULTS = (
    "softened", "weak_opposite", "urges_others", "state", "chat_frame",
    "invented_detail", "invented_motive", "attitude_only", "off_trait",
)
QUESTION_SHAPES = ("situation", "advice", "how_to", "facts", "task", "other")
QUESTION_FLAGS = ("two_option", "yes_no", "one_answer", "solo_task", "names_trait", "chat_frame")

_HEADER = """\
<trait>
{trait}
</trait>

<trait_description>
{description}
</trait_description>

<opposite_trait>
{opposite}
</opposite_trait>
"""

# Version 1 asked for a verdict instruction by instruction and said that most
# instructions have no fault; on the 18 pilot traits it passed "You mislead
# users" and "with appropriate depth and care".  Version 2 searches fault by
# fault and asks for the words that show each one.  Version 3 narrows three
# definitions that version 2 applied too widely: the verb "respond" is not a
# chat frame, "whenever it suits you" is not a softening, and a value or a
# feeling is a motive only when offered as the reason.
# The question judge was changed once: its shapes are words, since a
# one-letter shape was written among the flags.
INSTRUCTION_JUDGE_PROMPT = """\
You are checking instructions written for a research dataset on personality \
traits in language models. Each instruction will be given to a language model \
as its system prompt, to make it act as a person who has a trait (a positive \
instruction, "pos") or as a person who has the opposite trait (a negative \
instruction, "neg"). The dataset is used to measure how models represent \
traits, bad ones included, so an instruction is good when it renders its trait \
accurately and at full strength, and faulty when it does one of the things \
listed below. You are not asked whether the trait is a good one to have, or \
whether the instruction is safe: only whether each fault is present.

""" + _HEADER + """
<instructions>
{instructions}
</instructions>

Go through the faults below one at a time. For each fault, read all of the \
instructions looking for that fault alone, and list every instruction that has \
it, with the words that show it. An instruction may have several faults or \
none, and a fault may be in many of the instructions or in none of them. Judge \
by the definitions: a fault counts when the words are there, whether or not the \
instruction is otherwise a good one.

- softened: the trait (in a pos instruction) or the opposite trait (in a neg \
instruction) is hedged, qualified, excused, justified, or made milder than the \
description calls for. Words such as "appropriate", "healthy", "balanced", \
"sometimes", "may", "can be", and "tend to" are cases wherever they weaken what \
is said, and so is a bad trait dressed up as a virtue. Words that say when or \
how often without weakening the trait ("whenever it suits you", "every time") \
are not cases.
- weak_opposite (neg instructions only): the instruction is not a real \
opposite of the trait. It describes the sensible middle, ordinary good conduct, \
or the mere absence of the trait, where a real opposite exists.
- urges_others: the instruction says what the person advises, encourages, \
advocates, or gets other people to do, where the description is about what the \
person themselves does, thinks, feels, or wants. (A trait that is itself about \
how one treats other people, such as being helpful or bossy, is not a case.)
- state: the instruction describes a passing mood, one episode, or a reaction \
to one event, not a standing part of the person's character.
- chat_frame: the instruction presupposes a chat assistant. It mentions a \
user, an assistant, or an AI, or it speaks of the person's "responses", \
"answers", or "replies" as a chat assistant's output ("in all your responses", \
"when responding to queries", "the answers you give"). The verb "respond" used \
of how a person reacts to events or to people ("you respond to setbacks with \
...") is not a case.
- invented_detail: the instruction names particular settings, objects, or \
quoted phrases that the description neither contains nor plainly implies (for \
example "uses your mug").
- invented_motive: the instruction gives a reason for the trait, or a \
justification of it, that the description does not contain (for example \
"because changing course feels like weakness", "rooted in your belief that \
..."). What the person values, feels, or wants is a case only where it is \
offered as the reason for what they do.
- attitude_only: the instruction names an attitude, an approach, a mindset, or \
a style, and nowhere says anything the person does.
- off_trait: the instruction describes a noticeably different trait from the \
one in the description, or a milder neighbor of it.

Respond with a JSON object only, no other text, with one entry for each of the \
nine faults, in the order above. An entry lists the instructions that have the \
fault, and is an empty list when none has it. For each instruction listed, \
write the quote first (the words of the instruction that show the fault, at \
most 12 of them), and then its id:

{{"softened": [{{"quote": "<words from the instruction>", "id": "p1_neg"}}],
 "weak_opposite": [],
 "urges_others": [],
 "state": [],
 "chat_frame": [],
 "invented_detail": [],
 "invented_motive": [],
 "attitude_only": [],
 "off_trait": []}}"""

QUESTION_JUDGE_PROMPT = """\
You are checking questions written for a research dataset on personality \
traits in language models. A language model that has been told to act as a \
person with the trait below, or with the opposite trait, will be asked each \
question, and the answers are compared. A question is useful when a person \
with the trait and a person with the opposite trait would answer it \
differently.

""" + _HEADER + """
<questions>
{questions}
</questions>

For each question give its shape and any flags that apply.

shape, exactly one of:
- situation: puts the person answering into a situation and asks what they do, \
decide, think, feel, say, or write in it. This includes a situation in which \
someone else asks the person for something, and one in which the person is \
writing or making something.
- advice: written in the first person ("I ...", "my ...") by someone who \
describes a problem of their own and asks for advice or an opinion about it
- how_to: asks how to do something in general (a method, a procedure, tips), \
with no situation of the asker's own
- facts: asks for facts or for an explanation of a subject
- task: asks for a piece of work to be produced, with no situation around it \
("Write a poem about autumn.")
- other: anything else, such as an opinion on a general topic

flags, any number of:
- two_option: the question spells out two courses of action, or two things to \
choose between, and asks for a choice
- yes_no: the question can be answered in full with yes or no
- one_answer: there is one right answer, or one safe answer, that a person \
with the trait and a person with the opposite trait would both give
- solo_task: the situation is a task the person carries out on their own, with \
nobody else involved in it
- names_trait: the question names the trait or the opposite trait
- chat_frame: the question mentions an AI, an assistant, a chatbot, or a user

Respond with a JSON object only, no other text. For each question, in the \
order given, write a note first (at most 8 words on what the question asks), \
and then the shape and the flags:

{{"items": [
  {{"i": 0, "note": "<note>", "shape": "situation", "flags": ["two_option"]}},
  {{"i": 1, "note": "<note>", "shape": "advice", "flags": []}}
]}}"""


def _header_fields(doc: dict) -> dict:
    neg = str(doc.get("negative_label") or "")
    named = neg and not neg.lower().startswith("non-")
    return {
        "trait": doc.get("positive_label", ""),
        "description": doc.get("description", ""),
        "opposite": neg if named else "(not named: take the opposite of the description)",
    }


def build_instruction_judge_prompt(doc: dict) -> str:
    lines = []
    for k, pair in enumerate(doc.get("instruction") or []):
        for side in ("pos", "neg"):
            lines.append(f"p{k}_{side}: {' '.join(str(pair.get(side, '')).split())}")
    return INSTRUCTION_JUDGE_PROMPT.format(instructions="\n".join(lines), **_header_fields(doc))


def build_question_judge_prompt(doc: dict) -> str:
    lines = [f"{i}: {' '.join(str(q).split())}" for i, q in enumerate(doc.get("questions") or [])]
    return QUESTION_JUDGE_PROMPT.format(questions="\n".join(lines), **_header_fields(doc))


def _loads(text: str) -> dict:
    raw = generator.strip_markdown_fences(text)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    data = json.loads(raw[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("the reply is not a JSON object")
    return data


def parse_instruction_judgement(text: str, n_pairs: int) -> list[dict]:
    """The judge's reply as [{"id", "faults", "quotes"}], one per instruction
    in file order.  Raises ValueError when a fault's entry is missing or names
    an instruction that does not exist.  A weak_opposite reported on a pos
    instruction is dropped, since the fault is defined for neg only."""
    data = _loads(text)
    want = [f"p{k}_{side}" for k in range(n_pairs) for side in ("pos", "neg")]
    found = {i: {} for i in want}
    missing = [f for f in INSTRUCTION_FAULTS if not isinstance(data.get(f), list)]
    if missing:
        raise ValueError(f"no entry for fault(s) {missing}")
    unknown = [k for k in data if k not in INSTRUCTION_FAULTS]
    if unknown:
        raise ValueError(f"unknown fault(s) {unknown}")
    for fault in INSTRUCTION_FAULTS:
        for item in data[fault]:
            if not isinstance(item, dict) or str(item.get("id")) not in found:
                raise ValueError(f"{fault}: no such instruction in {item!r}")
            if fault == "weak_opposite" and str(item["id"]).endswith("_pos"):
                continue
            found[str(item["id"])][fault] = str(item.get("quote", ""))
    return [{"id": i, "faults": sorted(found[i]), "quotes": found[i]} for i in want]


def parse_question_judgement(text: str, n_questions: int) -> list[dict]:
    by_i = {}
    data = _loads(text)
    if not isinstance(data.get("items"), list):
        raise ValueError("reply has no list of items")
    for item in data["items"]:
        if not isinstance(item, dict) or "i" not in item or not isinstance(item.get("flags"), list):
            raise ValueError(f"malformed item: {item!r}")
        if item.get("shape") not in QUESTION_SHAPES:
            raise ValueError(f"unknown shape {item.get('shape')!r} for question {item['i']}")
        # The judge now and then repeats the shape among the flags.  That says
        # nothing the shape field does not, so it is dropped; anything else
        # that is not a flag is still an error.
        flags = [f for f in item["flags"] if f not in QUESTION_SHAPES]
        unknown = [f for f in flags if f not in QUESTION_FLAGS]
        if unknown:
            raise ValueError(f"unknown flag(s) {unknown} for question {item['i']}")
        by_i[int(item["i"])] = {"i": int(item["i"]), "note": str(item.get("note", "")),
                                "shape": item["shape"], "flags": sorted(set(flags))}
    missing = [i for i in range(n_questions) if i not in by_i]
    if missing:
        raise ValueError(f"no judgement for questions {missing}")
    return [by_i[i] for i in range(n_questions)]


# ---------------------------------------------------------------------------
# The blind rating ("taste test", Roger, 2026-09-30): one judge reads the
# label, the description and a file's five positive instructions, never told
# which rubric wrote them, and rates the set on two things the rubric asks for.
# ---------------------------------------------------------------------------

DEFAULT_TASTE_JUDGE = "claude-sonnet-4-6"
TASTE_RUBRIC_VERSION = 1
TASTE_SCORES = ("quality", "coverage")
# room for a model that thinks before it answers (the Claude 5 models count thinking against max_tokens)
TASTE_MAX_TOKENS = 2000

TASTE_JUDGE_PROMPT = """\
You are reviewing five system prompts written for one personality trait. Each \
will be given on its own to an open-weight language model of 30 to 100 billion \
parameters, as the whole of its system prompt, so that the model takes on the \
trait and answers as a person who has it. The five are alternatives, used one \
at a time; between them they are meant to cover the whole trait.

Trait: {trait}
Description: {description}

The five system prompts:
{instructions}

Rate the set on two things, each from 1 to 5.

quality: how good these are as system prompts for such a model. A 5 says \
clearly and forcefully who the model is to be, in plain, direct language that a \
model of that size will follow, at the trait's full strength, with nothing \
hedged, padded, or roundabout, and nothing that would leave the model answering \
as an ordinary assistant. A 3 is usable, with clear weaknesses in some of the \
five. A 1 would mostly fail to produce the trait.

coverage: how well the five, between them, cover and include everything in the \
description, each taking a different aspect of the trait, with no two so alike \
that one is redundant, and none straying into a different trait. A 5 covers \
every element of the description in five distinct aspects. A 3 misses an \
element, or has two prompts that nearly repeat each other. A 1 leaves most of \
the description uncovered, or says the same thing five times.

Judge only what is in front of you. Reason first, then commit to the scores. \
Reply with a JSON object only, no other text, the reasons first:
{{"reasons": "<two or three sentences>", "quality": <1 to 5>, "coverage": <1 to 5>}}"""


def build_taste_prompt(doc: dict) -> str:
    lines = [f"{k + 1}. {' '.join(str(pair.get('pos', '')).split())}" for k, pair in enumerate(doc.get("instruction") or [])]
    return TASTE_JUDGE_PROMPT.format(trait=doc.get("positive_label", ""),
                                     description=" ".join(str(doc.get("description", "")).split()),
                                     instructions="\n".join(lines))


def parse_taste_judgement(text: str) -> dict:
    """{"reasons": str, "quality": 1..5, "coverage": 1..5}; raises ValueError otherwise."""
    data = _loads(text)
    out = {"reasons": " ".join(str(data.get("reasons", "")).split())}
    for key in TASTE_SCORES:
        value = data.get(key)
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value.strip())
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            raise ValueError(f"{key} is not a whole number from 1 to 5: {data.get(key)!r}")
        out[key] = value
    return out


def taste_dir(out_dir: Path, model: str, arm: str) -> Path:
    """Ratings are kept per judge model, so that two judges can be compared."""
    return Path(out_dir) / "judged_taste" / model / arm


def taste_is_current(judged: dict, doc: dict, model: str) -> bool:
    return (judged.get("content_sha256") == content_sha256(doc) and judged.get("model") == model
            and judged.get("rubric_version") == TASTE_RUBRIC_VERSION)


def load_taste(out_dir: Path, model: str, arm: str, docs: dict[str, dict]) -> dict[str, dict]:
    """stem -> the current rating of that arm's file, for the files that have one."""
    out = {}
    for stem, doc in docs.items():
        path = taste_dir(out_dir, model, arm) / f"{stem}.json"
        if path.exists():
            judged = json.loads(path.read_text(encoding="utf-8"))
            if taste_is_current(judged, doc, model):
                out[stem] = judged
    return out


def taste_report(out_dir: Path, model: str, arm_dirs: dict[str, Path], stems: list[str],
                 styles: dict[str, str] | None = None, seed: int = DEFAULT_SEED) -> dict:
    """Mean rating per arm and score, its distribution, and each arm's paired
    difference from the first arm (traits resampled for the interval; a
    sign-flip permutation test for p).  Traits described differently between
    arms are left out, as in build_report."""
    rng = np.random.default_rng(seed)
    styles = styles or {}
    docs = {a: arm_files(d, stems, styles.get(a)) for a, d in arm_dirs.items()}
    changed = described_differently(docs)
    docs = {a: {s: d for s, d in v.items() if s not in changed} for a, v in docs.items()}
    rated = {a: load_taste(out_dir, model, a, v) for a, v in docs.items()}
    arms = list(arm_dirs)
    base = arms[0]
    report = {"model": model, "rubric_version": TASTE_RUBRIC_VERSION, "arms": arms, "baseline": base,
              "left_out_described_differently": sorted(changed), "n_rated": {a: len(v) for a, v in rated.items()},
              "scores": {}}
    for key in TASTE_SCORES:
        row = {}
        for a in arms:
            vals = [v[key] for v in rated[a].values()]
            row[a] = {"mean": float(np.mean(vals)) if vals else float("nan"), "n": len(vals),
                      "distribution": {k: int(sum(v == k for v in vals)) for k in range(1, 6)}}
            if a != base:
                common = sorted(set(rated[base]) & set(rated[a]))
                if common:
                    d = np.array([rated[a][s][key] - rated[base][s][key] for s in common], dtype=float)
                    idx = rng.integers(0, len(d), size=(4000, len(d)))
                    lo, hi = np.percentile(d[idx].mean(axis=1), [2.5, 97.5])
                    signs = rng.choice([-1.0, 1.0], size=(20000, len(d)))
                    p = (np.sum(np.abs((signs * d).mean(axis=1)) >= abs(d.mean()) - 1e-9) + 1) / 20001
                    row[a]["against_baseline"] = {"paired_traits": len(common), "difference": float(d.mean()),
                                                  "interval": (float(lo), float(hi)), "p": float(p),
                                                  "better": int((d > 0).sum()), "worse": int((d < 0).sum())}
        report["scores"][key] = row
    return report


def render_taste_report(report: dict) -> str:
    arms = report["arms"]
    lines = [f"blind rating by {report['model']} (rubric v{report['rubric_version']}); rated files: "
             + ", ".join(f"{a} {report['n_rated'][a]}" for a in arms)]
    if report["left_out_described_differently"]:
        lines.append("  left out (description differs between arms): " + ", ".join(report["left_out_described_differently"]))
    for key in TASTE_SCORES:
        lines.append(f"\n{key}: mean of 1 to 5, distribution 1|2|3|4|5, and the paired difference from {report['baseline']}")
        for a in arms:
            r = report["scores"][key][a]
            dist = "|".join(str(r["distribution"][k]) for k in range(1, 6))
            cell = f"  {a:26s} {r['mean']:.2f}  ({dist})"
            c = r.get("against_baseline")
            if c:
                cell += (f"   {c['difference']:+.2f} ({c['interval'][0]:+.2f} to {c['interval'][1]:+.2f})  p={c['p']:.3f}"
                         f"   better in {c['better']}, worse in {c['worse']} of {c['paired_traits']}")
            lines.append(cell)
    return "\n".join(lines)


async def _taste_call(client, model: str, prompt: str, semaphore, usage, tally) -> dict:
    """One rating, with up to three attempts, as _judge_call; at temperature 0
    where the model takes a temperature (the Claude 5 models refuse one)."""
    last, use_temperature = None, model not in _NO_TEMPERATURE_MODELS
    for attempt in range(3):
        asked = prompt if last is None else (
            f"{prompt}\n\nYour previous reply could not be used: {last}. Reply again in full, keeping to the format.")
        kwargs = {"temperature": 0.0 if attempt == 0 else 0.5} if use_temperature else {}
        async with semaphore:
            try:
                response = await client.messages.create(model=model, max_tokens=TASTE_MAX_TOKENS,
                                                        messages=[{"role": "user", "content": asked}], **kwargs)
            except anthropic.BadRequestError as e:
                if use_temperature and "temperature" in str(e).lower():
                    use_temperature = False
                    _NO_TEMPERATURE_MODELS.add(model)
                    response = await client.messages.create(model=model, max_tokens=TASTE_MAX_TOKENS,
                                                            messages=[{"role": "user", "content": asked}])
                else:
                    raise
        if usage is not None:
            usage.charge(model, *extract_usage_anthropic(response))
        tally.total[model] += 1
        try:
            rating = parse_taste_judgement(generator._extract_text(response))
            tally.ok[model] += 1
            return rating
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
            last = e
            logger.warning("unparseable rating (attempt %d of 3): %s", attempt + 1, e)
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"taste:{model}: no parseable reply in three attempts ({last})")


_NO_TEMPERATURE_MODELS: set[str] = set()


def content_sha256(doc: dict) -> str:
    """Hash of what the judges are shown, so that a regenerated file is judged again."""
    shown = {k: doc.get(k) for k in ("positive_label", "negative_label", "description", "instruction", "questions")}
    return hashlib.sha256(json.dumps(shown, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


class ParseTally:
    def __init__(self) -> None:
        self.ok = Counter()
        self.total = Counter()


async def _judge_call(client, model: str, prompt: str, parse, max_tokens: int, semaphore, usage, tally, label):
    """One judged check, with up to three attempts; every reply is charged.
    The first attempt is at temperature 0.  A second and third are at 0.5 and
    are told what was wrong with the reply before, since at 0 a reply that
    cannot be read comes back the same, and the same slip (a flag written as
    the shape, a question passed over) came back at 0.5 too."""
    last = None
    for attempt in range(3):
        asked = prompt if last is None else (
            f"{prompt}\n\nYour previous reply could not be used: {last}. Reply again in full, keeping to the format.")
        async with semaphore:
            response = await client.messages.create(
                model=model, max_tokens=max_tokens, temperature=0.0 if attempt == 0 else 0.5,
                messages=[{"role": "user", "content": asked}])
        if usage is not None:
            usage.charge(model, *extract_usage_anthropic(response))
        tally.total[label] += 1
        try:
            items = parse(generator._extract_text(response))
            tally.ok[label] += 1
            return items
        except (ValueError, json.JSONDecodeError, KeyError, TypeError) as e:
            last = e
            logger.warning("unparseable %s reply (attempt %d of 3): %s", label, attempt + 1, e)
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"{label}: no parseable reply in three attempts ({last})")


async def judge_file(client, doc: dict, *, instruction_model: str, question_model: str,
                     semaphore, usage, tally) -> dict:
    n_pairs = len(doc.get("instruction") or [])
    n_questions = len(doc.get("questions") or [])
    instr, quest = await asyncio.gather(
        _judge_call(client, instruction_model, build_instruction_judge_prompt(doc),
                    lambda t: parse_instruction_judgement(t, n_pairs), 2500, semaphore, usage, tally,
                    f"instructions:{instruction_model}"),
        _judge_call(client, question_model, build_question_judge_prompt(doc),
                    lambda t: parse_question_judgement(t, n_questions), 4000, semaphore, usage, tally,
                    f"questions:{question_model}"),
    )
    return {
        "content_sha256": content_sha256(doc),
        "judged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "instruction_judge": {"model": instruction_model, "rubric_version": INSTRUCTION_AUDIT_RUBRIC_VERSION,
                              "items": instr},
        "question_judge": {"model": question_model, "rubric_version": QUESTION_AUDIT_RUBRIC_VERSION,
                           "items": quest},
    }


def judgement_is_current(judged: dict, doc: dict, instruction_model: str, question_model: str) -> bool:
    ij, qj = judged.get("instruction_judge") or {}, judged.get("question_judge") or {}
    return (judged.get("content_sha256") == content_sha256(doc)
            and ij.get("rubric_version") == INSTRUCTION_AUDIT_RUBRIC_VERSION and ij.get("model") == instruction_model
            and qj.get("rubric_version") == QUESTION_AUDIT_RUBRIC_VERSION and qj.get("model") == question_model)


# ---------------------------------------------------------------------------
# The sample
# ---------------------------------------------------------------------------

def stratum_of(doc: dict, stem: str, old_stems: set[str]) -> str:
    """Three populations with different histories: files never touched since
    the first extraction, files of that extraction rewritten in September
    2026, and files added in September 2026."""
    regenerated = bool((doc.get("generator") or {}).get("style"))
    if stem in old_stems:
        return "old_regenerated" if regenerated else "old_untouched"
    return "new" if regenerated else "new_unrecorded"


def draw_split(strata: dict[str, list[str]], n_dev: int, n_held_out: int, seed: int,
               exclude: set[str]) -> dict:
    """Two disjoint random samples, each spread over the strata in proportion
    to their sizes (largest remainders).  Deterministic for a given seed."""
    pools = {s: sorted(set(v) - exclude) for s, v in sorted(strata.items())}
    total = sum(len(v) for v in pools.values())
    if n_dev + n_held_out > total:
        raise ValueError(f"asked for {n_dev + n_held_out} traits, only {total} available")

    def shares(n):
        exact = {s: n * len(v) / total for s, v in pools.items()}
        out = {s: int(x) for s, x in exact.items()}
        for s in sorted(exact, key=lambda s: (-(exact[s] - out[s]), s))[:n - sum(out.values())]:
            out[s] += 1
        return out

    rng = random.Random(seed)
    dev_n, held_n = shares(n_dev), shares(n_held_out)
    dev, held = [], []
    for s, pool in pools.items():
        picked = rng.sample(pool, min(len(pool), dev_n[s] + held_n[s]))
        dev += picked[:dev_n[s]]
        held += picked[dev_n[s]:dev_n[s] + held_n[s]]
    return {"dev": sorted(dev), "held_out": sorted(held),
            "strata": {s: {"size": len(v), "dev": dev_n[s], "held_out": held_n[s]} for s, v in pools.items()}}


def load_split(out_dir: Path) -> dict:
    path = out_dir / "split.json"
    if not path.exists():
        raise SystemExit(f"no split at {path}: run the split subcommand first")
    return json.loads(path.read_text(encoding="utf-8"))


def stems_of_set(split: dict, name: str) -> list[str]:
    if name in ("dev", "held_out"):
        return list(split[name])
    if name == "pilot":
        return list(split["excluded"]["pilot"])
    if name == "near_example":
        return list(split["excluded"]["near_example"])
    raise SystemExit(f"unknown set {name!r}")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact test on the discordant pairs (b: only the first has it,
    c: only the second)."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cluster_rate_interval(k: np.ndarray, n: np.ndarray, rng: np.random.Generator, reps: int = 2000) -> tuple[float, float]:
    """95% interval for sum(k)/sum(n), resampling traits (the instructions of
    one trait are not independent)."""
    if len(k) == 0 or n.sum() == 0:
        return (float("nan"), float("nan"))
    idx = rng.integers(0, len(k), size=(reps, len(k)))
    rates = k[idx].sum(axis=1) / np.maximum(n[idx].sum(axis=1), 1)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return (float(lo), float(hi))


def paired_difference(k_base: np.ndarray, k_arm: np.ndarray, n: np.ndarray, rng: np.random.Generator,
                      reps: int = 2000, flips: int = 10000) -> dict:
    """Difference in rate between two arms on the same traits: the estimate, a
    95% interval (traits resampled), and a two-sided p from sign-flipping the
    per-trait differences."""
    if len(n) == 0 or n.sum() == 0:
        return {"difference": float("nan"), "interval": (float("nan"), float("nan")), "p": float("nan")}
    d = (k_arm - k_base).astype(float)
    diff = d.sum() / n.sum()
    idx = rng.integers(0, len(d), size=(reps, len(d)))
    boots = d[idx].sum(axis=1) / np.maximum(n[idx].sum(axis=1), 1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    if not d.any():
        p = 1.0
    else:
        signs = rng.choice([-1.0, 1.0], size=(flips, len(d)))
        perm = np.abs((signs * d).sum(axis=1))
        p = float((np.sum(perm >= abs(d.sum()) - 1e-9) + 1) / (flips + 1))
    return {"difference": float(diff), "interval": (float(lo), float(hi)), "p": p}


# ---------------------------------------------------------------------------
# The measures
# ---------------------------------------------------------------------------

# (key, what is counted, unit, source, which items)
MEASURES = (
    ("open_risky", "opens with a statement about the person: You have / believe / want / tend to, When", "pos instruction", "pattern", "pos"),
    ("open_statement", "opens with a plain statement: You <verb>, Your <noun>", "pos instruction", "pattern", "pos"),
    ("chat_words", "chat-frame words (user, assistant, AI, your responses)", "instruction", "pattern", "all"),
    ("chat_frame", "presupposes a chat assistant (judged)", "instruction", "judge", "all"),
    ("urges_others", "about what the person urges on others (judged)", "instruction", "judge", "all"),
    ("softened_pos", "trait softened, hedged or excused (judged)", "pos instruction", "judge", "pos"),
    ("softened_neg", "opposite softened, hedged or excused (judged)", "neg instruction", "judge", "neg"),
    ("weak_opposite", "neg is the sensible middle or a mere absence (judged)", "neg instruction", "judge", "neg"),
    ("hedge_words", "hedge words (appropriate, healthy, sometimes, may, tends to ...)", "instruction", "pattern", "all"),
    ("state", "a passing state, not a standing trait (judged)", "instruction", "judge", "all"),
    ("off_trait", "a different or milder trait than the description (judged)", "instruction", "judge", "all"),
    ("attitude_only", "names an attitude, says nothing the person does (judged)", "instruction", "judge", "all"),
    ("invented_detail", "settings or objects the description does not have (judged)", "instruction", "judge", "all"),
    ("invented_motive", "a reason the description does not give (judged)", "instruction", "judge", "all"),
    ("because", "has a 'because' clause", "instruction", "pattern", "all"),
    ("names_label", "names its own label (self-labelling)", "instruction", "pattern", "all"),
    ("echo_description", "repeats 5 or more words in a row of the description", "instruction", "pattern", "all"),
    ("copied_example", "repeats 7 or more words in a row of a template example", "instruction", "pattern", "all"),
    ("length_out", "outside 20 to 30 words", "instruction", "pattern", "all"),
    ("q_persona", "addresses the person answering (second person, no first-person asker)", "question", "pattern", "q"),
    ("q_shape_situation", "puts the person in a situation (judged)", "question", "judge", "q"),
    ("q_shape_advice", "a first-person asker seeking advice (judged)", "question", "judge", "q"),
    ("q_first_person", "asker speaks in the first person", "question", "pattern", "q"),
    ("q_shape_other_kinds", "how-to, facts, bare task or general opinion (judged)", "question", "judge", "q"),
    ("q_howto", "opens as a how-to", "question", "pattern", "q"),
    ("q_factual", "opens as a request for facts", "question", "pattern", "q"),
    ("q_yesno", "opens as a yes/no question", "question", "pattern", "q"),
    ("q_yes_no", "can be answered in full with yes or no (judged)", "question", "judge", "q"),
    ("q_two_option", "spells out two courses of action (judged)", "question", "judge", "q"),
    ("q_one_answer", "one right or one safe answer (judged)", "question", "judge", "q"),
    ("q_solo_task", "a task carried out alone (judged)", "question", "judge", "q"),
    ("q_names_trait", "names the trait or its opposite", "question", "pattern", "q"),
    ("q_chat_words", "mentions an AI, an assistant or a user", "question", "pattern", "q"),
    ("q_option_label", "labels its options 'Option A'", "question", "pattern", "q"),
    ("q_rubric_echo", "repeats the rubric ('costs something')", "question", "pattern", "q"),
)
# a fault of the whole file when this many of its items have it (default 1)
FILE_THRESHOLDS = {"copied_example": 2}


def counts_for(doc: dict, judged: dict | None) -> dict[str, tuple[int, int]]:
    """Per measure, (items with it, items it could apply to) for one file.
    Judged measures are left out when the file has not been judged."""
    pat = pattern_checks(doc)
    out = {}
    ji = {r["id"]: r for r in ((judged or {}).get("instruction_judge") or {}).get("items", [])}
    jq = {r["i"]: r for r in ((judged or {}).get("question_judge") or {}).get("items", [])}
    for key, _, _, source, which in MEASURES:
        if which == "q":
            if source == "pattern":
                rows = pat["questions"]
                out[key] = (sum(key in r["flags"] for r in rows), len(rows))
            elif jq:
                rows = list(jq.values())
                if key == "q_shape_other_kinds":
                    k = sum(r["shape"] in ("how_to", "facts", "task", "other") for r in rows)
                elif key.startswith("q_shape_"):
                    k = sum(r["shape"] == key[len("q_shape_"):] for r in rows)
                else:
                    k = sum(key[2:] in r["flags"] for r in rows)
                out[key] = (k, len(rows))
            continue
        rows = [r for r in pat["instructions"] if which == "all" or r["side"] == which]
        if source == "pattern":
            out[key] = (sum(key in r["flags"] for r in rows), len(rows))
        elif ji:
            fault = "softened" if key.startswith("softened_") else key
            out[key] = (sum(fault in ji[r["id"]]["faults"] for r in rows if r["id"] in ji), len(rows))
    out["_distinct_pos_forms"] = (pat["file"]["distinct_pos_forms"], pat["file"]["n_pairs"])
    return out


def arm_files(arm_dir: Path, stems: list[str], expect_style: str | None = None) -> dict[str, dict]:
    """stem -> trait file, for the files of an arm that exist and, when a style
    is expected, were written under it.  A staging directory starts as a copy
    of the corpus files, so a file that a failed run left untouched is still
    the old text: without the check it would be counted as the new rubric's."""
    out, stale = {}, []
    for stem in stems:
        path = arm_dir / f"{stem}.json"
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        g = doc.get("generator") or {}
        style, _, template = (expect_style or "").partition("@")
        if (style and g.get("style") != style) or (template and g.get("template_sha256") != template):
            stale.append(stem)
            continue
        out[stem] = doc
    if stale:
        logger.warning("%s: %d file(s) not written under %s, left out: %s%s", arm_dir.name, len(stale), expect_style,
                       " ".join(stale[:8]), " ..." if len(stale) > 8 else "")
    return out


def described_differently(docs: dict[str, dict[str, dict]]) -> dict[str, list[str]]:
    """stem -> the arms whose file has another label or description than the
    first arm that has the trait.  An arm is staged from the corpus as it
    stands that day, and descriptions are edited (chaotic was rewritten on
    2026-09-30, between two arms): instructions written from two descriptions
    are instructions for two traits, and are not to be compared."""
    first, out = {}, {}
    for arm, files in docs.items():
        for stem, doc in files.items():
            text = (doc.get("positive_label"), " ".join(str(doc.get("description", "")).split()))
            if first.setdefault(stem, text) != text:
                out.setdefault(stem, []).append(arm)
    return out


def generators_of(docs: dict[str, dict]) -> dict[str, int]:
    """How many files each generator wrote, as 'style template-hash [concrete]'."""
    c = Counter()
    for doc in docs.values():
        g = doc.get("generator") or {}
        name = f"{g.get('style') or 'unrecorded'} {g.get('template_sha256') or '-'}"
        if "concrete" in g:
            name += " concrete" if g["concrete"] else " no-concrete"
        c[name] += 1
    return dict(c.most_common())


def load_arm(arm_dir: Path, judged_dir: Path | None, stems: list[str],
             expect_style: str | None = None) -> dict[str, dict]:
    """stem -> counts_for(...) for the files of an arm."""
    out = {}
    for stem, doc in arm_files(arm_dir, stems, expect_style).items():
        judged = None
        if judged_dir is not None and (judged_dir / f"{stem}.json").exists():
            judged = json.loads((judged_dir / f"{stem}.json").read_text(encoding="utf-8"))
            if judged.get("content_sha256") != content_sha256(doc):
                judged = None  # judged before the file was regenerated
        out[stem] = counts_for(doc, judged)
    return out


def summarize(arm: dict[str, dict], key: str, rng: np.random.Generator) -> dict | None:
    stems = [s for s in sorted(arm) if key in arm[s]]
    if not stems:
        return None
    k = np.array([arm[s][key][0] for s in stems])
    n = np.array([arm[s][key][1] for s in stems])
    thr = FILE_THRESHOLDS.get(key, 1)
    files = int((k >= thr).sum())
    return {
        "traits": len(stems), "items": int(n.sum()), "with": int(k.sum()),
        "rate": float(k.sum() / n.sum()) if n.sum() else float("nan"),
        "rate_interval": cluster_rate_interval(k, n, rng),
        "files_with": files, "file_threshold": thr,
        "file_rate": files / len(stems), "file_rate_interval": wilson(files, len(stems)),
    }


def compare(base: dict[str, dict], arm: dict[str, dict], key: str, rng: np.random.Generator) -> dict | None:
    stems = [s for s in sorted(base) if s in arm and key in base[s] and key in arm[s]]
    if not stems:
        return None
    kb = np.array([base[s][key][0] for s in stems])
    ka = np.array([arm[s][key][0] for s in stems])
    n = np.array([max(base[s][key][1], arm[s][key][1]) for s in stems])
    thr = FILE_THRESHOLDS.get(key, 1)
    fb, fa = kb >= thr, ka >= thr
    out = paired_difference(kb, ka, n, rng)
    out.update({"paired_traits": len(stems),
                "files_only_baseline": int((fb & ~fa).sum()), "files_only_arm": int((~fb & fa).sum()),
                "files_p": mcnemar_exact(int((fb & ~fa).sum()), int((~fb & fa).sum()))})
    return out


def variety(arm: dict[str, dict]) -> dict:
    vals = [v["_distinct_pos_forms"][0] for v in arm.values() if v["_distinct_pos_forms"][1] >= 5]
    return {"traits": len(vals), "mean": float(np.mean(vals)) if vals else float("nan"),
            "distribution": dict(sorted(Counter(vals).items())),
            "share_5": (sum(v == 5 for v in vals) / len(vals)) if vals else float("nan"),
            "share_4_or_more": (sum(v >= 4 for v in vals) / len(vals)) if vals else float("nan")}


def form_shares(docs: dict[str, dict]) -> Counter:
    c = Counter()
    for doc in docs.values():
        c.update(pattern_checks(doc)["file"]["pos_forms"])
    return c


def pct(x: float) -> str:
    return "  n/a" if x != x else f"{100 * x:5.1f}"


def _interval(iv) -> str:
    return "" if iv[0] != iv[0] else f"({100 * iv[0]:.1f} to {100 * iv[1]:.1f})"


def render_report(report: dict) -> str:
    arms = report["arms"]
    base = report["baseline"]
    lines = [f"set: {report['set']}   traits per arm: " + ", ".join(f"{a} {report['n_traits'][a]}" for a in arms)]
    for a in arms:
        lines.append(f"  {a} written by: {report.get('generators', {}).get(a)}")
    if report.get("left_out_described_differently"):
        lines.append("  left out of every arm (label or description differs between arms): "
                     + ", ".join(report["left_out_described_differently"]))
    lines.append("")
    for unit in ("rate", "file_rate"):
        lines.append("share of items with it, % (95% interval, traits resampled)" if unit == "rate"
                     else "share of FILES with it, % (95% Wilson interval); a file counts at 1 item, copied examples at 2")
        head = f"{'measure':46s}" + "".join(f"{a:>26s}" for a in arms)
        head += "".join(f"{'p vs ' + base + ': ' + a:>30s}" for a in arms if a != base)
        lines.append(head)
        for key, label, _, _, _ in MEASURES:
            row = report["measures"].get(key)
            if not row:
                continue
            cells = ""
            for a in arms:
                s = row["arms"].get(a)
                cell = "not judged" if s is None else pct(s[unit]) + " " + _interval(s[unit + "_interval"])
                cells += f"{cell:>26s}"
            for a in arms:
                if a == base:
                    continue
                c = row["against_baseline"].get(a)
                if c is None:
                    cell = ""
                elif unit == "rate":
                    cell = "%+.1f  p=%.4f" % (100 * c["difference"], c["p"])
                else:
                    cell = "%d lost, %d gained  p=%.4f" % (c["files_only_baseline"], c["files_only_arm"], c["files_p"])
                cells += f"{cell:>30s}"
            lines.append(f"{key:46s}" + cells)
        lines.append("")
    lines.append("distinct opening forms among a file's five pos instructions")
    for a in arms:
        v = report["variety"][a]
        lines.append(f"  {a:20s} mean {v['mean']:.2f}; all five different {pct(v['share_5'])}%; four or more "
                     f"{pct(v['share_4_or_more'])}%; distribution {v['distribution']}")
    lines.append("")
    lines.append("opening form of pos instructions, % of instructions")
    forms = sorted({f for a in arms for f in report["forms"][a]}, key=lambda f: -sum(report["forms"][a].get(f, 0) for a in arms))
    lines.append(f"{'':38s}" + "".join(f"{a:>16s}" for a in arms))
    for f in forms:
        mark = " (risky)" if f in RISKY_FORMS else (" (statement)" if f in STATEMENT_FORMS else "")
        lines.append(f"{f + mark:38s}" + "".join(
            f"{100 * report['forms'][a].get(f, 0) / max(1, sum(report['forms'][a].values())):16.1f}" for a in arms))
    return "\n".join(lines)


def build_report(out_dir: Path, set_name: str, arm_dirs: dict[str, Path], baseline: str, stems: list[str],
                 seed: int = DEFAULT_SEED, styles: dict[str, str] | None = None) -> dict:
    rng = np.random.default_rng(seed)
    styles = styles or {}
    docs = {a: arm_files(d, stems, styles.get(a)) for a, d in arm_dirs.items()}
    changed = described_differently(docs)
    if changed:
        logger.warning("left out of every arm, label or description not the same in all of them: %s",
                       "; ".join(f"{s} ({', '.join(a)})" for s, a in sorted(changed.items())))
        stems = [s for s in stems if s not in changed]
        docs = {a: {s: d for s, d in v.items() if s not in changed} for a, v in docs.items()}
    loaded = {a: load_arm(d, out_dir / "judged" / a, stems, styles.get(a)) for a, d in arm_dirs.items()}
    report = {"set": set_name, "arms": list(arm_dirs), "baseline": baseline,
              "left_out_described_differently": {s: a for s, a in sorted(changed.items())},
              "n_traits": {a: len(v) for a, v in loaded.items()}, "measures": {},
              "generators": {a: generators_of(v) for a, v in docs.items()},
              "variety": {a: variety(v) for a, v in loaded.items()},
              "forms": {a: dict(form_shares(v)) for a, v in docs.items()}}
    for key, label, unit, source, _ in MEASURES:
        row = {"label": label, "unit": unit, "source": source, "arms": {}, "against_baseline": {}}
        for a in arm_dirs:
            row["arms"][a] = summarize(loaded[a], key, rng)
            if a != baseline:
                row["against_baseline"][a] = compare(loaded[baseline], loaded[a], key, rng)
        if any(v is not None for v in row["arms"].values()):
            report["measures"][key] = row
    return report


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_split(args) -> None:
    out_dir = Path(args.out)
    path = out_dir / "split.json"
    if path.exists() and not args.force:
        raise SystemExit(f"{path} exists: a split is drawn once, so that the held-out set stays held out "
                         f"(--force to draw again)")
    old_dir = Path(args.old_scores_dir)
    if not old_dir.is_dir():
        raise SystemExit(f"no directory {old_dir}")
    old_stems = {p.stem for p in old_dir.glob("*.json")}
    strata: dict[str, list[str]] = {}
    for p in sorted(TRAITS_DIR.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        if len(doc.get("instruction") or []) != 5 or len(doc.get("questions") or []) != 40:
            continue
        strata.setdefault(stratum_of(doc, p.stem, old_stems), []).append(p.stem)
    near = sorted(set(args.near_example or []))
    exclude = set(PILOT_TRAITS) | set(near)
    split = draw_split(strata, args.n_dev, args.n_held_out, args.seed, exclude)
    split.update({"seed": args.seed, "drawn_on": datetime.date.today().isoformat(),
                  "traits_dir": str(TRAITS_DIR.relative_to(REPO)),
                  "excluded": {"pilot": sorted(PILOT_TRAITS), "near_example": near}})
    out_dir.mkdir(parents=True, exist_ok=True)
    generator.atomic_write_json(path, split)
    print(f"wrote {path}: dev {len(split['dev'])}, held out {len(split['held_out'])}")
    for s, v in split["strata"].items():
        print(f"  {s:18s} {v['size']:4d} available   dev {v['dev']:3d}   held out {v['held_out']:3d}")


def cmd_stage(args) -> None:
    out_dir = Path(args.out)
    split = load_split(out_dir)
    if args.set == "held_out" and not args.final:
        raise SystemExit("the held-out set is staged only for the final check: pass --final when the rubric is settled")
    stems = stems_of_set(split, args.set)
    stage = out_dir / "stage" / args.set / args.arm
    if stage.exists() and any(stage.glob("*.json")) and not args.force:
        raise SystemExit(f"{stage} already holds files (--force to copy over them)")
    stage.mkdir(parents=True, exist_ok=True)
    source = Path(args.source) if args.source else TRAITS_DIR
    for stem in stems:
        shutil.copy(source / f"{stem}.json", stage / f"{stem}.json")
    print(f"copied {len(stems)} files from {source} to {stage}")


def _arm_dir(out_dir: Path, set_name: str, spec: str) -> tuple[str, Path]:
    """'name' (a staged arm of this set) or 'name=path'; a ':STYLE' after the
    name is allowed and ignored here (see _arm_style)."""
    name, _, path = spec.partition("=")
    name = name.partition(":")[0]
    return name, (Path(path) if path else out_dir / "stage" / set_name / name)


def _arm_style(spec: str) -> tuple[str, str | None]:
    """'name:STYLE' or 'name:STYLE=path' -> (name, STYLE): only the files
    written under that style belong to the arm.  STYLE may carry a template
    hash, 'RogerV2@4ac7be8a332f', which pins the arm to one draft of a rubric."""
    name, _, style = spec.partition("=")[0].partition(":")
    return name, (style or None)


async def _judge_arm(args, arm: str, arm_dir: Path, stems: list[str], usage, tally,
                     style: str | None = None) -> tuple[int, int, int]:
    judged_dir = Path(args.out) / "judged" / arm
    judged_dir.mkdir(parents=True, exist_ok=True)
    todo = []
    for stem, doc in arm_files(arm_dir, stems, style).items():
        done = judged_dir / f"{stem}.json"
        if done.exists() and not args.force and judgement_is_current(
                json.loads(done.read_text(encoding="utf-8")), doc, args.instruction_model, args.question_model):
            continue
        todo.append((stem, doc))
    if args.dry_run:
        print(f"{arm}: {len(todo)} of {len(stems)} files to judge, {2 * len(todo)} calls")
        return len(todo), 0, 0
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.concurrency)

    async def one(stem, doc):
        result = await judge_file(client, doc, instruction_model=args.instruction_model,
                                  question_model=args.question_model, semaphore=semaphore, usage=usage, tally=tally)
        result.update({"stem": stem, "arm": arm})
        generator.atomic_write_json(judged_dir / f"{stem}.json", result)

    results = await asyncio.gather(*(one(s, d) for s, d in todo), return_exceptions=True)
    failed = [(s, r) for (s, _), r in zip(todo, results) if isinstance(r, Exception)]
    for stem, err in failed:
        logger.error("%s %s: %s", arm, stem, err)
    return len(todo), len(todo) - len(failed), len(failed)


def cmd_judge(args) -> None:
    out_dir = Path(args.out)
    split = load_split(out_dir)
    if args.set == "held_out" and not args.final:
        raise SystemExit("the held-out set is judged only for the final check: pass --final when the rubric is settled")
    stems = stems_of_set(split, args.set)
    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    usage, tally = MultiModelUsage(), ParseTally()
    for spec in args.arm:
        arm, arm_dir = _arm_dir(out_dir, args.set, spec)
        n, ok, bad = asyncio.run(_judge_arm(args, arm, arm_dir, stems, usage, tally, _arm_style(spec)[1]))
        if not args.dry_run:
            print(f"{arm}: judged {ok} of {n} files, {bad} failed", file=sys.stderr)
    if args.dry_run:
        return
    for label in sorted(tally.total):
        warn_if_low_parse_rate(label=f"audit_trait_instructions:{label}", n_ok=tally.ok[label],
                               n_total=tally.total[label], logger_obj=logger)
    print(usage.log_line("[usage]"), file=sys.stderr)
    usage_path = out_dir / "judged" / "usage.json"
    total = MultiModelUsage.load_or_create(usage_path)
    total.merge_from(usage)
    total.write_json(usage_path)
    print(f"[usage] cumulative record: {usage_path} (total ${total.total_cost_usd:.3f} over {total.n_calls} calls)",
          file=sys.stderr)


def _stems_for(args, out_dir: Path) -> list[str]:
    split = load_split(out_dir)
    if args.set == "held_out" and not args.final:
        raise SystemExit("the held-out set is read only for the final check: pass --final when the rubric is settled")
    stems = stems_of_set(split, args.set)
    if getattr(args, "stems", None):
        wanted = json.loads(Path(args.stems).read_text(encoding="utf-8"))
        outside = sorted(set(wanted) - set(stems))
        if outside:
            raise SystemExit(f"{args.stems} names traits that are not in the {args.set} set: {outside[:5]}")
        stems = wanted
    return stems


async def _taste_arm(args, arm: str, arm_dir: Path, stems: list[str], usage, tally, style: str | None) -> tuple[int, int, int]:
    docs = arm_files(arm_dir, stems, style)
    done = load_taste(Path(args.out), args.model, arm, docs) if not args.force else {}
    todo = [(s, d) for s, d in docs.items() if s not in done]
    if args.dry_run:
        n_in = sum(len(build_taste_prompt(d)) for _, d in todo) / 4 * 1.3   # about 1.3 characters a token on the new tokenizer
        rate_in, rate_out = price_for_model(args.model)
        print(f"{arm}: {len(todo)} of {len(docs)} files to rate with {args.model}; about "
              f"${(n_in * rate_in + len(todo) * 220 * rate_out) / 1e6:.2f}")
        return len(todo), 0, 0
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.concurrency)
    where = taste_dir(Path(args.out), args.model, arm)
    where.mkdir(parents=True, exist_ok=True)

    async def one(stem, doc):
        rating = await _taste_call(client, args.model, build_taste_prompt(doc), semaphore, usage, tally)
        rating.update({"stem": stem, "arm": arm, "model": args.model, "rubric_version": TASTE_RUBRIC_VERSION,
                       "content_sha256": content_sha256(doc),
                       "judged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
        generator.atomic_write_json(where / f"{stem}.json", rating)

    results = await asyncio.gather(*(one(s, d) for s, d in todo), return_exceptions=True)
    failed = [(s, r) for (s, _), r in zip(todo, results) if isinstance(r, Exception)]
    for stem, err in failed:
        logger.error("%s %s: %s", arm, stem, err)
    return len(todo), len(todo) - len(failed), len(failed)


def cmd_taste(args) -> None:
    out_dir = Path(args.out)
    stems = _stems_for(args, out_dir)
    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    usage, tally = MultiModelUsage(), ParseTally()
    for spec in args.arm:
        arm, arm_dir = _arm_dir(out_dir, args.set, spec)
        n, ok, bad = asyncio.run(_taste_arm(args, arm, arm_dir, stems, usage, tally, _arm_style(spec)[1]))
        if not args.dry_run:
            print(f"{arm}: rated {ok} of {n} files, {bad} failed", file=sys.stderr)
    if not args.dry_run:
        for label in sorted(tally.total):
            warn_if_low_parse_rate(label=f"audit_trait_instructions:taste:{label}", n_ok=tally.ok[label],
                                   n_total=tally.total[label], logger_obj=logger)
        print(usage.log_line("[usage]"), file=sys.stderr)
        usage_path = out_dir / "judged_taste" / "usage.json"
        total = MultiModelUsage.load_or_create(usage_path)
        total.merge_from(usage)
        total.write_json(usage_path)
        print(f"[usage] cumulative record: {usage_path} (total ${total.total_cost_usd:.3f} over {total.n_calls} calls)",
              file=sys.stderr)
    arm_dirs = dict(_arm_dir(out_dir, args.set, s) for s in args.arm)
    styles = {n: st for n, st in map(_arm_style, args.arm) if st}
    report = taste_report(out_dir, args.model, arm_dirs, stems, styles=styles, seed=args.seed)
    print(render_taste_report(report))
    if args.write:
        path = out_dir / "judged_taste" / f"report_{args.model}_{args.set}.json"
        generator.atomic_write_json(path, report)
        print(f"\nwrote {path}", file=sys.stderr)


def cmd_report(args) -> None:
    out_dir = Path(args.out)
    if args.set == "corpus":
        stems = sorted(p.stem for p in TRAITS_DIR.glob("*.json"))
    else:
        split = load_split(out_dir)
        if args.set == "held_out" and not args.final:
            raise SystemExit("the held-out set is read only for the final check: pass --final when the rubric is settled")
        stems = stems_of_set(split, args.set)
        if args.stems:
            wanted = json.loads(Path(args.stems).read_text(encoding="utf-8"))
            outside = sorted(set(wanted) - set(stems))
            if outside:
                raise SystemExit(f"{args.stems} names traits that are not in the {args.set} set: {outside[:5]}")
            stems = wanted
    specs = [args.baseline] + [a for a in args.arm if a != args.baseline]
    arm_dirs = dict(_arm_dir(out_dir, args.set, s) for s in specs)
    styles = {n: st for n, st in map(_arm_style, specs) if st}
    report = build_report(out_dir, args.set, arm_dirs, next(iter(arm_dirs)), stems, seed=args.seed, styles=styles)
    print(render_report(report))
    if args.write:
        path = out_dir / (f"report_{args.set}.json" if not args.stems else f"report_{Path(args.stems).stem}.json")
        generator.atomic_write_json(path, report)
        print(f"\nwrote {path}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, sets=("dev", "held_out", "pilot", "near_example")):
        p.add_argument("--out", required=True, help="Directory of the audit (split.json, stage/, judged/)")
        p.add_argument("--set", choices=sets, default="dev", help="Which sample (default: dev)")
        p.add_argument("--final", action="store_true",
                       help="Allow the held-out set: for the final check only, once the rubric is settled")

    p = sub.add_parser("split", help="Draw the development and held-out samples, once")
    p.add_argument("--out", required=True)
    p.add_argument("--n-dev", type=int, default=DEFAULT_N_DEV, help=f"(default: {DEFAULT_N_DEV})")
    p.add_argument("--n-held-out", type=int, default=DEFAULT_N_HELD_OUT, help=f"(default: {DEFAULT_N_HELD_OUT})")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"(default: {DEFAULT_SEED})")
    p.add_argument("--old-scores-dir", default=str(REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot" / "traits" / "scores"),
                   help="Directory whose file stems are the traits of the first extraction (for the strata)")
    p.add_argument("--near-example", nargs="*", metavar="TRAIT",
                   help="Traits close in meaning to the rubric's example traits: kept out of both samples, "
                        "and read as a set of their own for copied examples")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("stage", help="Copy a sample's trait files into a staging directory for one arm")
    common(p)
    p.add_argument("--arm", required=True, help="Name of the arm, e.g. v1_corpus or v2_concrete")
    p.add_argument("--source", default=None, help="Copy from here instead of the corpus")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_stage)

    p = sub.add_parser("judge", help="Run the judged checks on one or more arms (API)")
    common(p)
    p.add_argument("--arm", nargs="+", required=True,
                   help="Arm names, or name=directory; name:STYLE takes only the files written under that "
                        "style (a staging directory starts as a copy of the corpus files)")
    p.add_argument("--instruction-model", default=DEFAULT_INSTRUCTION_JUDGE, help=f"(default: {DEFAULT_INSTRUCTION_JUDGE})")
    p.add_argument("--question-model", default=DEFAULT_QUESTION_JUDGE, help=f"(default: {DEFAULT_QUESTION_JUDGE})")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--dry-run", action="store_true", help="Say how many files would be judged, and stop")
    p.add_argument("--force", action="store_true", help="Judge again files already judged")
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("taste", help="Blind rating of each file's five positive instructions, 1 to 5 on quality "
                                     "and on coverage, by one judge model; then a report against the first arm (API)")
    common(p)
    p.add_argument("--arm", nargs="+", required=True,
                   help="Arms, the first being the baseline (name, name=directory, name:STYLE@hash)")
    p.add_argument("--model", default=DEFAULT_TASTE_JUDGE, help=f"The judge (default: {DEFAULT_TASTE_JUDGE})")
    p.add_argument("--stems", default=None, metavar="FILE", help="A JSON list of traits: these only")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--dry-run", action="store_true", help="Say how many files would be rated, and what it would cost")
    p.add_argument("--force", action="store_true", help="Rate again files already rated")
    p.add_argument("--write", action="store_true", help="Also write judged_taste/report_<model>_<set>.json")
    p.set_defaults(func=cmd_taste)

    p = sub.add_parser("report", help="Rates per measure and arm, with intervals and paired tests")
    common(p, sets=("dev", "held_out", "pilot", "near_example", "corpus"))
    p.add_argument("--baseline", required=True, help="Arm the others are compared with (name or name=directory)")
    p.add_argument("--arm", nargs="*", default=[], help="Other arms (name, name=directory, name:STYLE)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--stems", default=None, metavar="FILE",
                   help="A JSON list of traits: report on these only (they must belong to the set)")
    p.add_argument("--write", action="store_true", help="Also write report_<set>.json")
    p.set_defaults(func=cmd_report)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
