#!/usr/bin/env python3
"""Measure the role rubric's output, as audit_trait_instructions.py does for traits.

A companion to [audit_trait_instructions.py](audit_trait_instructions.py),
written for the role rubric V3 work (2026-10-02, Roger: "measure every change
on a development sample, with a held-out set kept for the final check").  It
reuses that tool's split, statistics and file-reading code, and has its own
checks, because a role file has no negative instructions and no labels, and
the role rubric has rules of its own (voice, register, the role's own
self-justification).

Subcommands:
    split   draw the development and held-out sets of roles, once (and a
            sample of the development set for the costlier runs)
    stage   copy a set's role files into a staging directory, an "arm"
    judge   the judged checks: a fault judge on each file's five
            instructions, a shape judge on its questions (Claude; blind to the arm)
    report  rates per measure and arm, with intervals and paired tests
    taste   a blind rating of each file's five instructions, 1 to 5 on
            quality and on coverage

Usage:
    uv run python data_analysis/audit_role_instructions.py split --out reports/role_rubric_v3_pilot
    uv run python data_analysis/audit_role_instructions.py stage --out reports/role_rubric_v3_pilot \\
        --set dev --arm corpus
    uv run python data_analysis/audit_role_instructions.py judge --out reports/role_rubric_v3_pilot \\
        --arm corpus --stems reports/role_rubric_v3_pilot/sample100.json
    uv run python data_analysis/audit_role_instructions.py report --out reports/role_rubric_v3_pilot \\
        --baseline corpus --arm v3:RogerV3 --stems reports/role_rubric_v3_pilot/sample100.json

The held-out roles are not to be looked at, generated or judged before the
final check of a settled rubric; every subcommand wants ``--final`` for them.
"""

import argparse
import asyncio
import datetime
import json
import logging
import os
import random
import re
import shutil
import sys
from pathlib import Path

import anthropic
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.judge_pricing import MultiModelUsage, price_for_model  # noqa: E402
from data_analysis import audit_trait_instructions as trait_audit  # noqa: E402
from data_analysis import regenerate_role_instructions as generator  # noqa: E402

logger = logging.getLogger("audit_role_instructions")

REPO = Path(__file__).resolve().parent.parent
ROLES_DIR = REPO / "data" / "roles" / "instructions"
DEFAULT_SEED = 20261002
DEFAULT_N_DEV = 150
DEFAULT_N_HELD_OUT = 150
DEFAULT_SAMPLE = 100
DEFAULT_OLD_SCORES_DIR = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot" / "roles" / "scores"


def role_strata(roles_dir: Path, old_stems: set[str]) -> dict[str, list[str]]:
    """The roles with five instructions and forty questions, by history: in the
    first extraction or added since (the trait tool's ``stratum_of``)."""
    strata: dict[str, list[str]] = {}
    for p in sorted(roles_dir.glob("*.json")):
        if p.stem == "default":
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        if len(doc.get("instruction") or []) != 5 or len(doc.get("questions") or []) != 40:
            continue
        strata.setdefault(trait_audit.stratum_of(doc, p.stem, old_stems), []).append(p.stem)
    return strata


def draw_sample(dev: list[str], n: int, seed: int) -> list[str]:
    """A sample of the development set for the costlier runs, drawn once."""
    if n > len(dev):
        raise ValueError(f"asked for a sample of {n}, the development set has {len(dev)}")
    return sorted(random.Random(seed + 1).sample(sorted(dev), n))


# ---------------------------------------------------------------------------
# Pattern checks
# ---------------------------------------------------------------------------

ROLE_LENGTH_RANGE = (15, 25)   # the role rubric V2.5's range for an instruction
# openings that tell the model to play a part (Roger, 2026-09-29, for traits; the question for roles)
ROLEPLAY_FORMS = frozenset({trait_audit.FORM_ACT_AS, trait_audit.FORM_LIKE, trait_audit.FORM_TAKE_ON})
# the role rubric's list of words that signal an observer's register
OBSERVER_WORDS = re.compile(
    r"\b(?:navigat(?:e|es|ed|ing)|individuals?|demonstrat(?:e|es|ed|ing)|appropriate(?:ly)?|engag(?:e|es|ed|ing) with"
    r"|the challenges of|in a healthy way)\b", re.I)
DASHES = re.compile(r"—|–| -- ")
HAVE_YOU_EVER = re.compile(r"\bhave you ever\b", re.I)
# a role that is itself an AI or an assistant may mention one
AI_ROLE = re.compile(r"\b(?:AI|artificial intelligence|assistants?|chatbots?|language models?)\b", re.I)


ROLE_FORM_FROM_NOW_ON = "From now on, you are ..."
ROLE_FORM_BE = "Be a ..."
ROLE_FORM_YOURE = "You're a ..."
ROLE_FORM_BECOME = "Become a ..."
ROLE_FORM_YOU_ARE_WHO = "You are a ... who ..."
ROLE_FORM_YOU_ARE = "You are a ..."
ROLE_FORM_ACT_AS = "Act as ..."
ROLE_FORM_OTHER_ROLEPLAY = "other role-play"
ROLE_FORM_STATEMENT = "statement"
ROLE_FORM_COMMAND = "command"
ROLE_FORM_OTHER = "other"
ROLE_ROLEPLAY_FORMS = frozenset({ROLE_FORM_ACT_AS, ROLE_FORM_OTHER_ROLEPLAY})


def role_opening_form(text: str) -> str:
    """The opening of a role instruction, in the role rubric V3's own terms.
    The trait classifier (``trait_audit.opening_form``) tells "You are a forger
    who" from "You are a forger." but not "You're" from "You are", and the V3
    menu makes both distinctions; the flags on an opening still use the trait
    classifier, this one is for the variety of openings in a file."""
    s = text.strip()
    if re.match(r"(?i)from now on,? you(?: are|'re)\b", s):
        return ROLE_FORM_FROM_NOW_ON
    if re.match(r"(?i)act as\b", s):
        return ROLE_FORM_ACT_AS
    if re.match(r"(?i)(?:behave|respond|speak|talk|think|write|live|work) (?:as|like)\b"
                r"|(?:take on|adopt|assume|play|embody|channel|pretend)\b", s):
        return ROLE_FORM_OTHER_ROLEPLAY
    if re.match(r"(?i)you're\b", s):
        return ROLE_FORM_YOURE
    if re.match(r"(?i)you are (?:an?|the) [\w' -]+? who\b", s):
        return ROLE_FORM_YOU_ARE_WHO
    if re.match(r"(?i)you are\b", s):
        return ROLE_FORM_YOU_ARE
    if re.match(r"(?i)be\b", s):
        return ROLE_FORM_BE
    if re.match(r"(?i)become\b", s):
        return ROLE_FORM_BECOME
    f = trait_audit.opening_form(s)
    if f in trait_audit.STATEMENT_FORMS or f in trait_audit.RISKY_FORMS:
        return ROLE_FORM_STATEMENT
    if f == trait_audit.FORM_COMMAND:
        return ROLE_FORM_COMMAND
    return ROLE_FORM_OTHER


def role_example_instructions(style: str) -> list[str]:
    """The example instructions of the role template behind ``style``."""
    template = generator._TEMPLATES.get(style) or ""
    blocks = re.findall(r"<example_instructions>(.*?)</example_instructions>", template, re.S)
    return [m for b in blocks for m in re.findall(r'"pos": "((?:[^"\\]|\\.)*)"', b, re.S)]


def _role_pattern(stem: str) -> re.Pattern:
    name = generator.role_display_name(stem)
    return re.compile(r"\b" + re.escape(name).replace(r"\ ", r"[- ]") + r"s?\b", re.I)


def pattern_checks(doc: dict, stem: str) -> dict:
    """Every pattern check for one role file: {"instructions": [{"id", "form",
    "words", "flags"}], "questions": [{"i", "flags"}], "file": {...}}."""
    description = doc.get("description", "")
    is_ai = bool(AI_ROLE.search(description))
    role = _role_pattern(stem)
    style = (doc.get("generator") or {}).get("style") or "Roger"
    examples = role_example_instructions(style)
    instructions = []
    for k, item in enumerate(doc.get("instruction") or []):
        text = str(item.get("pos", ""))
        form = trait_audit.opening_form(text)
        n = len(text.split())
        flags = []
        if form in ROLEPLAY_FORMS:
            flags.append("open_roleplay")
        if form in trait_audit.RISKY_FORMS:
            flags.append("open_risky")
        if form in trait_audit.STATEMENT_FORMS:
            flags.append("open_statement")
        if not is_ai and (trait_audit.CHAT_WORDS.search(text) or trait_audit.CHAT_AI.search(text)):
            flags.append("chat_words")
        if trait_audit.HEDGE_WORDS.search(text):
            flags.append("hedge_words")
        if OBSERVER_WORDS.search(text):
            flags.append("observer_words")
        if DASHES.search(text):
            flags.append("dashes")
        if not ROLE_LENGTH_RANGE[0] <= n <= ROLE_LENGTH_RANGE[1]:
            flags.append("length_out")
        if description and trait_audit.longest_shared_run(text, description) >= 5:
            flags.append("echo_description")
        if any(trait_audit.longest_shared_run(text, ex) >= 7 for ex in examples):
            flags.append("copied_example")
        if trait_audit.BECAUSE.search(text):
            flags.append("because")
        instructions.append({"id": f"p{k}", "side": "pos", "form": role_opening_form(text), "trait_form": form,
                             "words": n, "flags": flags})
    questions = []
    for i, q in enumerate(doc.get("questions") or []):
        q = str(q).strip()
        bare = trait_audit.QUOTED.sub("", q)
        flags = []
        if trait_audit.FIRST_PERSON.search(bare):
            flags.append("q_first_person")
        elif re.search(r"\byou(?:r|rs|rself)?\b", bare, re.I):
            flags.append("q_persona")
        if trait_audit.Q_HOWTO.search(q):
            flags.append("q_howto")
        if trait_audit.Q_FACTUAL.search(q):
            flags.append("q_factual")
        if trait_audit.Q_YESNO.search(q):
            flags.append("q_yesno")
        if HAVE_YOU_EVER.search(q):
            flags.append("q_have_you_ever")
        if not is_ai and (trait_audit.Q_AI.search(q) or trait_audit.CHAT_AI.search(q)):
            flags.append("q_chat_words")
        if role.search(q):
            flags.append("q_names_role")
        if trait_audit.Q_OPTION_LABEL.search(q):
            flags.append("q_option_label")
        if trait_audit.Q_RUBRIC_ECHO.search(q):
            flags.append("q_rubric_echo")
        questions.append({"i": i, "flags": flags})
    forms = [r["form"] for r in instructions]
    return {"instructions": instructions, "questions": questions,
            "file": {"distinct_pos_forms": len(set(forms)), "pos_forms": forms,
                     "n_pairs": len(instructions), "n_questions": len(questions)}}


# ---------------------------------------------------------------------------
# Judged checks
# ---------------------------------------------------------------------------

DEFAULT_INSTRUCTION_JUDGE = trait_audit.DEFAULT_INSTRUCTION_JUDGE
DEFAULT_QUESTION_JUDGE = trait_audit.DEFAULT_QUESTION_JUDGE
INSTRUCTION_AUDIT_RUBRIC_VERSION = 1
QUESTION_AUDIT_RUBRIC_VERSION = 1
INSTRUCTION_FAULTS = ("softened", "observer_register", "chat_frame", "generic",
                      "invented_detail", "invented_motive", "off_role")
QUESTION_SHAPES = trait_audit.QUESTION_SHAPES
QUESTION_FLAGS = ("two_option", "yes_no", "one_answer", "solo_task", "names_role", "chat_frame",
                  "outside_world", "performs")

_HEADER = """\
<role>
{role}
</role>

<role_description>
{description}
</role_description>
"""

INSTRUCTION_JUDGE_PROMPT = """\
You are checking instructions written for a research dataset on roles in \
language models. Each instruction will be given to a language model as its \
system prompt, to make it be the role below and answer as that role. The \
dataset is used to measure how models represent roles, bad ones included, so an \
instruction is good when it renders the role accurately and in the role's own \
terms, and faulty when it does one of the things listed below. You are not asked \
whether the role is a good one to be, or whether the instruction is safe: only \
whether each fault is present.

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

- softened: the role is whitewashed, excused, hedged, or made milder or more \
respectable than the description calls for: the harm a bad role does left out \
or dressed up as a virtue, or words such as "appropriate", "healthy", \
"sometimes", "may", and "tend to" where they weaken what is said. The role's own \
self-justification, written so that it is plainly the role's view ("you tell \
yourself ...", "as you see it ..."), is not a case.
- observer_register: the instruction is written in an outsider's register \
rather than in words the role would use of itself: a case worker's, a \
clinician's, an academic's, a brochure's, or a policy writer's vocabulary \
("navigating", "individuals", "demonstrate", "engage with", "the challenges \
of"), or literary prose and flourishes the role would not use. A role that \
cannot describe itself (an animal, an object, someone who would not describe \
themselves truly) described plainly from the inside is not a case.
- chat_frame: the instruction presupposes a chat assistant. It mentions a user, \
an assistant, or an AI, or it speaks of "responses", "answers", or "replies" as \
a chat assistant's output, unless the role itself is an AI or an assistant.
- generic: the instruction says nothing particular to this role: with the \
role's name changed it could stand for many other roles ("You are a \
professional who takes pride in your work and treats people with respect").
- invented_detail: the instruction fixes particulars that the description \
leaves open and that are not a fair default for the role: an age, a sex, a \
nationality, an era, a place, a sub-type, or named objects or quoted phrases \
the description neither contains nor plainly implies.
- invented_motive: the instruction gives the role a reason or a motive that \
the description does not contain, stated as fact rather than as the role's own \
excuse.
- off_role: the instruction describes a noticeably different role, a \
personality trait rather than a role, or a part of the role so narrow that the \
description's central element is missing.

Respond with a JSON object only, no other text, with one entry for each of the \
seven faults, in the order above. An entry lists the instructions that have the \
fault, and is an empty list when none has it. For each instruction listed, \
write the quote first (the words of the instruction that show the fault, at \
most 12 of them), and then its id:

{{"softened": [{{"quote": "<words from the instruction>", "id": "p1"}}],
 "observer_register": [],
 "chat_frame": [],
 "generic": [],
 "invented_detail": [],
 "invented_motive": [],
 "off_role": []}}"""

QUESTION_JUDGE_PROMPT = """\
You are checking questions written for a research dataset on roles in language \
models. A language model that has been told to be the role below will be asked \
each question, and its answer is read for whether it answers as the role. A \
question is useful when the role's answer would differ from an ordinary \
assistant's, or from most people's.

""" + _HEADER + """
<questions>
{questions}
</questions>

For each question give its shape and any flags that apply.

shape, exactly one of:
- situation: puts the person answering into a situation and asks what they do, \
decide, think, feel, say, or remember in it. This includes a situation in which \
someone else asks the person for something, and one in which the person is \
writing or making something.
- advice: written in the first person ("I ...", "my ...") by someone who \
describes a problem of their own and asks for advice or an opinion about it
- how_to: asks how to do something in general (a method, a procedure, tips), \
with no situation of the asker's own
- facts: asks for facts or for an explanation of a subject
- task: asks for a piece of work to be produced, with no situation around it
- other: anything else, such as an opinion on a general topic

flags, any number of:
- two_option: the question spells out two courses of action, or two things to \
choose between, and asks for a choice
- yes_no: the question can be answered in full with yes or no
- one_answer: there is one right answer, or one safe answer, that anyone would \
give, the role included
- solo_task: the situation is a task the person carries out on their own, with \
nobody else involved in it
- names_role: the question names the role
- chat_frame: the question mentions an AI, an assistant, a chatbot, or a user \
(unless the role itself is an AI or an assistant)
- outside_world: the question is not set in the role's world: it could be \
asked of anyone, with nothing in it that belongs to the role's life or work
- performs: the question asks the person to perform the role, show it off, or \
say what being the role is like, rather than to answer as the role would

Respond with a JSON object only, no other text. For each question, in the \
order given, write a note first (at most 8 words on what the question asks), \
and then the shape and the flags:

{{"items": [
  {{"i": 0, "note": "<note>", "shape": "situation", "flags": ["two_option"]}},
  {{"i": 1, "note": "<note>", "shape": "advice", "flags": []}}
]}}"""


def _header_fields(doc: dict, stem: str) -> dict:
    # The judge display form (AGENT_NOTES "Judge prompts show the judge
    # display form", 2026-10-09).  It equals role_display_name for every role
    # in the corpus (none has a standard's suffix), so the role rubric
    # versions were not bumped: no judged prompt changes.
    return {"role": generator.role_prompt_name(stem), "description": " ".join(str(doc.get("description", "")).split())}


def build_instruction_judge_prompt(doc: dict, stem: str) -> str:
    lines = [f"p{k}: {' '.join(str(i.get('pos', '')).split())}" for k, i in enumerate(doc.get("instruction") or [])]
    return INSTRUCTION_JUDGE_PROMPT.format(instructions="\n".join(lines), **_header_fields(doc, stem))


def build_question_judge_prompt(doc: dict, stem: str) -> str:
    lines = [f"{i}: {' '.join(str(q).split())}" for i, q in enumerate(doc.get("questions") or [])]
    return QUESTION_JUDGE_PROMPT.format(questions="\n".join(lines), **_header_fields(doc, stem))


def parse_instruction_judgement(text: str, n_instructions: int) -> list[dict]:
    """The judge's reply as [{"id", "faults", "quotes"}], one per instruction in
    file order.  Raises ValueError when a fault's entry is missing or names an
    instruction that does not exist."""
    data = trait_audit._loads(text)
    want = [f"p{k}" for k in range(n_instructions)]
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
            found[str(item["id"])][fault] = str(item.get("quote", ""))
    return [{"id": i, "faults": sorted(found[i]), "quotes": found[i]} for i in want]


def parse_question_judgement(text: str, n_questions: int) -> list[dict]:
    by_i = {}
    data = trait_audit._loads(text)
    if not isinstance(data.get("items"), list):
        raise ValueError("reply has no list of items")
    for item in data["items"]:
        if not isinstance(item, dict) or "i" not in item or not isinstance(item.get("flags"), list):
            raise ValueError(f"malformed item: {item!r}")
        if item.get("shape") not in QUESTION_SHAPES:
            raise ValueError(f"unknown shape {item.get('shape')!r} for question {item['i']}")
        flags = [f for f in item["flags"] if f not in QUESTION_SHAPES]   # a shape repeated among the flags
        unknown = [f for f in flags if f not in QUESTION_FLAGS]
        if unknown:
            raise ValueError(f"unknown flag(s) {unknown} for question {item['i']}")
        by_i[int(item["i"])] = {"i": int(item["i"]), "note": str(item.get("note", "")),
                                "shape": item["shape"], "flags": sorted(set(flags))}
    missing = [i for i in range(n_questions) if i not in by_i]
    if missing:
        raise ValueError(f"no judgement for questions {missing}")
    return [by_i[i] for i in range(n_questions)]


async def judge_file(client, doc: dict, stem: str, *, instruction_model: str, question_model: str,
                     semaphore, usage, tally) -> dict:
    n_instr = len(doc.get("instruction") or [])
    n_questions = len(doc.get("questions") or [])
    instr, quest = await asyncio.gather(
        trait_audit._judge_call(client, instruction_model, build_instruction_judge_prompt(doc, stem),
                                lambda t: parse_instruction_judgement(t, n_instr), 2500, semaphore, usage, tally,
                                f"instructions:{instruction_model}"),
        trait_audit._judge_call(client, question_model, build_question_judge_prompt(doc, stem),
                                lambda t: parse_question_judgement(t, n_questions), 4000, semaphore, usage, tally,
                                f"questions:{question_model}"),
    )
    return {
        "content_sha256": trait_audit.content_sha256(doc),
        "judged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "instruction_judge": {"model": instruction_model, "rubric_version": INSTRUCTION_AUDIT_RUBRIC_VERSION,
                              "items": instr},
        "question_judge": {"model": question_model, "rubric_version": QUESTION_AUDIT_RUBRIC_VERSION,
                           "items": quest},
    }


def judgement_is_current(judged: dict, doc: dict, instruction_model: str, question_model: str) -> bool:
    ij, qj = judged.get("instruction_judge") or {}, judged.get("question_judge") or {}
    return (judged.get("content_sha256") == trait_audit.content_sha256(doc)
            and ij.get("rubric_version") == INSTRUCTION_AUDIT_RUBRIC_VERSION and ij.get("model") == instruction_model
            and qj.get("rubric_version") == QUESTION_AUDIT_RUBRIC_VERSION and qj.get("model") == question_model)


# ---------------------------------------------------------------------------
# The blind rating (as for traits; one file a prompt, so no slot to favour)
# ---------------------------------------------------------------------------

DEFAULT_TASTE_JUDGE = trait_audit.DEFAULT_TASTE_JUDGE
TASTE_RUBRIC_VERSION = trait_audit.TASTE_RUBRIC_VERSION   # stamped by the shared loader's currency check
# (2 since the W19 bump of 2026-10-09; a role rating stamped 1 stays current,
# since a role's labels render unchanged: trait_audit.version_is_current)

TASTE_JUDGE_PROMPT = """\
You are reviewing five system prompts written for one role. Each will be given \
on its own to an open-weight language model of 30 to 100 billion parameters, as \
the whole of its system prompt, so that the model takes on the role and answers \
as the role would. The five are alternatives, used one at a time; between them \
they are meant to cover the whole role.

Role: {role}
Description: {description}

The five system prompts:
{instructions}

Rate the set on two things, each from 1 to 5.

quality: how good these are as system prompts for such a model. A 5 says \
clearly who the model is to be, in plain words the role would use of itself, \
with the role's own particulars, nothing softened or made respectable, and \
nothing that would leave the model answering as an ordinary assistant. A 3 is \
usable, with clear weaknesses in some of the five. A 1 would mostly fail to \
produce the role.

coverage: how well the five, between them, cover and include everything in the \
description, each taking a different aspect of the role, with no two so alike \
that one is redundant, and none straying into a different role. A 5 covers \
every element of the description in five distinct aspects. A 3 misses an \
element, or has two prompts that nearly repeat each other. A 1 leaves most of \
the description uncovered, or says the same thing five times.

Judge only what is in front of you. Reason first, then commit to the scores. \
Reply with a JSON object only, no other text, the reasons first:
{{"reasons": "<two or three sentences>", "quality": <1 to 5>, "coverage": <1 to 5>}}"""


def build_taste_prompt(doc: dict, stem: str) -> str:
    lines = [f"{k + 1}. {' '.join(str(i.get('pos', '')).split())}" for k, i in enumerate(doc.get("instruction") or [])]
    return TASTE_JUDGE_PROMPT.format(instructions="\n".join(lines), **_header_fields(doc, stem))


# ---------------------------------------------------------------------------
# The measures
# ---------------------------------------------------------------------------

# (key, what is counted, unit, source, which items); every instruction of a role is a "pos" one
MEASURES = (
    ("open_roleplay", "opens by telling the model to play a part: Act as, Behave like, Take on", "instruction", "pattern", "all"),
    ("open_statement", "opens with a plain statement: You <verb>, Your <noun>", "instruction", "pattern", "all"),
    ("open_risky", "opens with You have / believe / want / tend to, When", "instruction", "pattern", "all"),
    ("chat_words", "chat-frame words (user, assistant, AI, your responses), not in an AI role", "instruction", "pattern", "all"),
    ("chat_frame", "presupposes a chat assistant (judged)", "instruction", "judge", "all"),
    ("softened", "the role softened, whitewashed or excused (judged)", "instruction", "judge", "all"),
    ("hedge_words", "hedge words (appropriate, healthy, sometimes, may, tends to ...)", "instruction", "pattern", "all"),
    ("observer_words", "the rubric's observer words (navigating, individuals, demonstrate ...)", "instruction", "pattern", "all"),
    ("observer_register", "an outsider's register, not the role's own words (judged)", "instruction", "judge", "all"),
    ("generic", "nothing particular to this role (judged)", "instruction", "judge", "all"),
    ("off_role", "a different role, a trait, or too narrow a part (judged)", "instruction", "judge", "all"),
    ("invented_detail", "particulars the description leaves open (judged)", "instruction", "judge", "all"),
    ("invented_motive", "a motive the description does not give, as fact (judged)", "instruction", "judge", "all"),
    ("because", "has a 'because' clause", "instruction", "pattern", "all"),
    ("dashes", "uses a dash (the rubric asks for commas)", "instruction", "pattern", "all"),
    ("echo_description", "repeats 5 or more words in a row of the description", "instruction", "pattern", "all"),
    ("copied_example", "repeats 7 or more words in a row of a template example", "instruction", "pattern", "all"),
    ("length_out", "outside 15 to 25 words", "instruction", "pattern", "all"),
    ("q_persona", "addresses the person answering (second person, no first-person asker)", "question", "pattern", "q"),
    ("q_shape_situation", "puts the person in a situation (judged)", "question", "judge", "q"),
    ("q_shape_advice", "a first-person asker seeking advice (judged)", "question", "judge", "q"),
    ("q_first_person", "asker speaks in the first person", "question", "pattern", "q"),
    ("q_shape_other_kinds", "how-to, facts, bare task or general opinion (judged)", "question", "judge", "q"),
    ("q_howto", "opens as a how-to", "question", "pattern", "q"),
    ("q_factual", "opens as a request for facts", "question", "pattern", "q"),
    ("q_yesno", "opens as a yes/no question", "question", "pattern", "q"),
    ("q_have_you_ever", "asks 'Have you ever'", "question", "pattern", "q"),
    ("q_yes_no", "can be answered in full with yes or no (judged)", "question", "judge", "q"),
    ("q_two_option", "spells out two courses of action (judged)", "question", "judge", "q"),
    ("q_one_answer", "one right or one safe answer (judged)", "question", "judge", "q"),
    ("q_solo_task", "a task carried out alone (judged)", "question", "judge", "q"),
    ("q_outside_world", "not set in the role's world (judged)", "question", "judge", "q"),
    ("q_performs", "asks the person to perform or describe the role (judged)", "question", "judge", "q"),
    ("q_names_role", "names the role", "question", "pattern", "q"),
    ("q_chat_words", "mentions an AI, an assistant or a user, not in an AI role", "question", "pattern", "q"),
    ("q_option_label", "labels its options 'Option A'", "question", "pattern", "q"),
    ("q_rubric_echo", "repeats a rubric's wording ('costs something')", "question", "pattern", "q"),
)


def counts_for(doc: dict, stem: str, judged: dict | None) -> dict[str, tuple[int, int]]:
    """Per measure, (items with it, items it could apply to) for one file.
    Judged measures are left out when the file has not been judged."""
    pat = pattern_checks(doc, stem)
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
        rows = pat["instructions"]
        if source == "pattern":
            out[key] = (sum(key in r["flags"] for r in rows), len(rows))
        elif ji:
            out[key] = (sum(key in ji[r["id"]]["faults"] for r in rows if r["id"] in ji), len(rows))
    out["_distinct_pos_forms"] = (pat["file"]["distinct_pos_forms"], pat["file"]["n_pairs"])
    return out


def cmd_split(args) -> None:
    out_dir = Path(args.out)
    path = out_dir / "split.json"
    if path.exists() and not args.force:
        raise SystemExit(f"{path} exists: a split is drawn once, so that the held-out set stays held out "
                         f"(--force to draw again)")
    old_dir = Path(args.old_scores_dir)
    if not old_dir.is_dir():
        raise SystemExit(f"no directory {old_dir}")
    strata = role_strata(ROLES_DIR, {p.stem for p in old_dir.glob("*.json")})
    split = trait_audit.draw_split(strata, args.n_dev, args.n_held_out, args.seed, exclude=set())
    roles_dir = str(ROLES_DIR.relative_to(REPO)) if ROLES_DIR.is_relative_to(REPO) else str(ROLES_DIR)
    split.update({"seed": args.seed, "drawn_on": datetime.date.today().isoformat(),
                  "roles_dir": roles_dir, "excluded": {"pilot": [], "near_example": []}})
    sample = draw_sample(split["dev"], args.sample, args.seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    generator.atomic_write_json(path, split)
    generator.atomic_write_json(out_dir / f"sample{args.sample}.json", sample)
    print(f"wrote {path}: dev {len(split['dev'])}, held out {len(split['held_out'])}; "
          f"{out_dir / f'sample{args.sample}.json'}: {len(sample)} of the development set")
    for s, v in split["strata"].items():
        print(f"  {s:18s} {v['size']:4d} available   dev {v['dev']:3d}   held out {v['held_out']:3d}")


def corpus_stems() -> list[str]:
    """Every role in the corpus but `default`: the `corpus` set, for judging
    the corpus as it stands (added 2026-10-04 to judge the V3 regeneration's
    output outside the held-out set)."""
    return sorted(p.stem for p in ROLES_DIR.glob("*.json") if p.stem != "default")


def cmd_stage(args) -> None:
    out_dir = Path(args.out)
    stems = _stems_for(args, out_dir)
    stage = out_dir / "stage" / args.set / args.arm
    if stage.exists() and any(stage.glob("*.json")) and not args.force:
        raise SystemExit(f"{stage} already holds files (--force to copy over them)")
    stage.mkdir(parents=True, exist_ok=True)
    source = Path(args.source) if args.source else ROLES_DIR
    for stem in stems:
        shutil.copy(source / f"{stem}.json", stage / f"{stem}.json")
    print(f"copied {len(stems)} files from {source} to {stage}")


def _stems_for(args, out_dir: Path) -> list[str]:
    if args.set == "held_out" and not args.final:
        raise SystemExit("the held-out set is read only for the final check: pass --final when the rubric is settled")
    stems = corpus_stems() if args.set == "corpus" else trait_audit.stems_of_set(trait_audit.load_split(out_dir), args.set)
    if getattr(args, "stems", None):
        wanted = json.loads(Path(args.stems).read_text(encoding="utf-8"))
        outside = sorted(set(wanted) - set(stems))
        if outside:
            raise SystemExit(f"{args.stems} names roles that are not in the {args.set} set: {outside[:5]}")
        stems = wanted
    return stems


def _record_usage(usage: MultiModelUsage, path: Path) -> None:
    print(usage.log_line("[usage]"), file=sys.stderr)
    total = MultiModelUsage.load_or_create(path)
    total.merge_from(usage)
    total.write_json(path)
    print(f"[usage] cumulative record: {path} (total ${total.total_cost_usd:.3f} over {total.n_calls} calls)",
          file=sys.stderr)


async def _judge_arm(args, arm: str, arm_dir: Path, stems: list[str], usage, tally, style: str | None):
    judged_dir = Path(args.out) / "judged" / arm
    judged_dir.mkdir(parents=True, exist_ok=True)
    todo = []
    for stem, doc in trait_audit.arm_files(arm_dir, stems, style).items():
        done = judged_dir / f"{stem}.json"
        if done.exists() and not args.force and judgement_is_current(
                json.loads(done.read_text(encoding="utf-8")), doc, args.instruction_model, args.question_model):
            continue
        todo.append((stem, doc))
    if args.dry_run:
        print(f"{arm}: {len(todo)} of {len(stems)} files to judge, {2 * len(todo)} calls")
        return len(todo), 0, 0, 0
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.concurrency)

    async def one(stem, doc):
        result = await judge_file(client, doc, stem, instruction_model=args.instruction_model,
                                  question_model=args.question_model, semaphore=semaphore, usage=usage, tally=tally)
        result.update({"stem": stem, "arm": arm})
        generator.atomic_write_json(judged_dir / f"{stem}.json", result)

    results = await asyncio.gather(*(one(s, d) for s, d in todo), return_exceptions=True)
    return trait_audit.arm_outcome(arm, todo, results)


def cmd_judge(args) -> None:
    out_dir = Path(args.out)
    stems = _stems_for(args, out_dir)
    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    usage, tally = MultiModelUsage(), trait_audit.ParseTally()
    for spec in args.arm:
        arm, arm_dir = trait_audit._arm_dir(out_dir, args.set, spec)
        outcome = asyncio.run(_judge_arm(args, arm, arm_dir, stems, usage, tally, trait_audit._arm_style(spec)[1]))
        if not args.dry_run:
            print(trait_audit.arm_line("judged", arm, outcome), file=sys.stderr)
    if args.dry_run:
        return
    trait_audit.report_parse_rates(tally, "audit_role_instructions")
    _record_usage(usage, out_dir / "judged" / "usage.json")


async def _taste_arm(args, arm: str, arm_dir: Path, stems: list[str], usage, tally, style: str | None):
    docs = trait_audit.arm_files(arm_dir, stems, style)
    done = trait_audit.load_taste(Path(args.out), args.model, arm, docs) if not args.force else {}
    todo = [(s, d) for s, d in docs.items() if s not in done]
    if args.dry_run:
        n_in = sum(len(build_taste_prompt(d, s)) for s, d in todo) / 4 * 1.3
        rate_in, rate_out = price_for_model(args.model)
        print(f"{arm}: {len(todo)} of {len(docs)} files to rate with {args.model}; about "
              f"${(n_in * rate_in + len(todo) * 220 * rate_out) / 1e6:.2f}")
        return len(todo), 0, 0, 0
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.concurrency)
    where = trait_audit.taste_dir(Path(args.out), args.model, arm)
    where.mkdir(parents=True, exist_ok=True)

    async def one(stem, doc):
        rating = await trait_audit._taste_call(client, args.model, build_taste_prompt(doc, stem), semaphore, usage, tally)
        rating.update({"stem": stem, "arm": arm, "model": args.model, "rubric_version": TASTE_RUBRIC_VERSION,
                       "content_sha256": trait_audit.content_sha256(doc),
                       "judged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
        generator.atomic_write_json(where / f"{stem}.json", rating)

    results = await asyncio.gather(*(one(s, d) for s, d in todo), return_exceptions=True)
    return trait_audit.arm_outcome(arm, todo, results)


def cmd_taste(args) -> None:
    out_dir = Path(args.out)
    stems = _stems_for(args, out_dir)
    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set (check .env or environment)")
    usage, tally = MultiModelUsage(), trait_audit.ParseTally()
    for spec in args.arm:
        arm, arm_dir = trait_audit._arm_dir(out_dir, args.set, spec)
        outcome = asyncio.run(_taste_arm(args, arm, arm_dir, stems, usage, tally, trait_audit._arm_style(spec)[1]))
        if not args.dry_run:
            print(trait_audit.arm_line("rated", arm, outcome), file=sys.stderr)
    if not args.dry_run:
        trait_audit.report_parse_rates(tally, "audit_role_instructions:taste")
        _record_usage(usage, out_dir / "judged_taste" / "usage.json")
    arm_dirs = dict(trait_audit._arm_dir(out_dir, args.set, s) for s in args.arm)
    styles = {n: st for n, st in map(trait_audit._arm_style, args.arm) if st}
    report = trait_audit.taste_report(out_dir, args.model, arm_dirs, stems, styles=styles, seed=args.seed)
    print(trait_audit.render_taste_report(report))
    if args.write:
        path = out_dir / "judged_taste" / f"report_{args.model}_{args.set}.json"
        generator.atomic_write_json(path, report)
        print(f"\nwrote {path}", file=sys.stderr)


def load_arm(arm_dir: Path, judged_dir: Path | None, stems: list[str], expect_style: str | None = None) -> dict:
    """stem -> counts_for(...) for the files of an arm."""
    out = {}
    for stem, doc in trait_audit.arm_files(arm_dir, stems, expect_style).items():
        judged = None
        if judged_dir is not None and (judged_dir / f"{stem}.json").exists():
            judged = json.loads((judged_dir / f"{stem}.json").read_text(encoding="utf-8"))
            if judged.get("content_sha256") != trait_audit.content_sha256(doc):
                judged = None  # judged before the file was regenerated
        out[stem] = counts_for(doc, stem, judged)
    return out


def build_report(out_dir: Path, set_name: str, arm_dirs: dict[str, Path], baseline: str, stems: list[str],
                 seed: int = DEFAULT_SEED, styles: dict[str, str] | None = None) -> dict:
    rng = np.random.default_rng(seed)
    styles = styles or {}
    docs = {a: trait_audit.arm_files(d, stems, styles.get(a)) for a, d in arm_dirs.items()}
    changed = trait_audit.described_differently(docs)
    if changed:
        logger.warning("left out of every arm, description not the same in all of them: %s",
                       "; ".join(f"{s} ({', '.join(a)})" for s, a in sorted(changed.items())))
        stems = [s for s in stems if s not in changed]
        docs = {a: {s: d for s, d in v.items() if s not in changed} for a, v in docs.items()}
    loaded = {a: load_arm(d, out_dir / "judged" / a, stems, styles.get(a)) for a, d in arm_dirs.items()}
    forms = {a: {} for a in arm_dirs}
    for a, v in docs.items():
        for stem, doc in v.items():
            for f in pattern_checks(doc, stem)["file"]["pos_forms"]:
                forms[a][f] = forms[a].get(f, 0) + 1
    report = {"set": set_name, "arms": list(arm_dirs), "baseline": baseline,
              "left_out_described_differently": {s: a for s, a in sorted(changed.items())},
              "n_roles": {a: len(v) for a, v in loaded.items()}, "measures": {},
              "generators": {a: trait_audit.generators_of(v) for a, v in docs.items()},
              "variety": {a: trait_audit.variety(v) for a, v in loaded.items()}, "forms": forms}
    for key, label, unit, source, _ in MEASURES:
        row = {"label": label, "unit": unit, "source": source, "arms": {}, "against_baseline": {}}
        for a in arm_dirs:
            row["arms"][a] = trait_audit.summarize(loaded[a], key, rng)
            if a != baseline:
                row["against_baseline"][a] = trait_audit.compare(loaded[baseline], loaded[a], key, rng)
        if any(v is not None for v in row["arms"].values()):
            report["measures"][key] = row
    return report


def render_report(report: dict) -> str:
    arms, base = report["arms"], report["baseline"]
    pct, iv = trait_audit.pct, trait_audit._interval
    lines = [f"set: {report['set']}   roles per arm: " + ", ".join(f"{a} {report['n_roles'][a]}" for a in arms)]
    for a in arms:
        lines.append(f"  {a} written by: {report.get('generators', {}).get(a)}")
    if report.get("left_out_described_differently"):
        lines.append("  left out (description differs between arms): " + ", ".join(report["left_out_described_differently"]))
    lines.append("")
    for unit in ("rate", "file_rate"):
        lines.append("share of items with it, % (95% interval, roles resampled)" if unit == "rate"
                     else "share of FILES with it, % (95% Wilson interval); copied examples count at 2 items")
        lines.append(f"{'measure':22s}" + "".join(f"{a:>24s}" for a in arms)
                     + "".join(f"{'vs ' + base + ': ' + a:>30s}" for a in arms if a != base))
        for key, label, _, _, _ in MEASURES:
            row = report["measures"].get(key)
            if not row:
                continue
            cells = ""
            for a in arms:
                s = row["arms"].get(a)
                cell = "not judged" if s is None else pct(s[unit]) + " " + iv(s[unit + "_interval"])
                cells += f"{cell:>24s}"
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
            lines.append(f"{key:22s}" + cells)
        lines.append("")
    lines.append("distinct opening forms among a file's five instructions")
    for a in arms:
        v = report["variety"][a]
        lines.append(f"  {a:20s} mean {v['mean']:.2f}; all five different {pct(v['share_5'])}%; four or more "
                     f"{pct(v['share_4_or_more'])}%; distribution {v['distribution']}")
    lines.append("")
    lines.append("opening form of instructions, % of instructions")
    all_forms = sorted({f for a in arms for f in report["forms"][a]},
                       key=lambda f: -sum(report["forms"][a].get(f, 0) for a in arms))
    lines.append(f"{'':38s}" + "".join(f"{a:>16s}" for a in arms))
    for f in all_forms:
        mark = " (role-play)" if f in ROLE_ROLEPLAY_FORMS else (" (statement)" if f == ROLE_FORM_STATEMENT else "")
        lines.append(f"{f + mark:38s}" + "".join(
            f"{100 * report['forms'][a].get(f, 0) / max(1, sum(report['forms'][a].values())):16.1f}" for a in arms))
    return "\n".join(lines)


def cmd_report(args) -> None:
    out_dir = Path(args.out)
    if args.set == "corpus":
        stems = sorted(p.stem for p in ROLES_DIR.glob("*.json") if p.stem != "default")
    else:
        stems = _stems_for(args, out_dir)
    specs = [args.baseline] + [a for a in args.arm if a != args.baseline]
    arm_dirs = dict(trait_audit._arm_dir(out_dir, "dev" if args.set == "corpus" else args.set, s) for s in specs)
    if args.set == "corpus":
        arm_dirs[next(iter(arm_dirs))] = ROLES_DIR
    styles = {n: st for n, st in map(trait_audit._arm_style, specs) if st}
    report = build_report(out_dir, args.set, arm_dirs, next(iter(arm_dirs)), stems, seed=args.seed, styles=styles)
    print(render_report(report))
    if args.write:
        path = out_dir / (f"report_{args.set}.json" if not args.stems else f"report_{Path(args.stems).stem}.json")
        generator.atomic_write_json(path, report)
        print(f"\nwrote {path}", file=sys.stderr)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, sets=("dev", "held_out", "corpus")):
        p.add_argument("--out", required=True, help="Directory of the audit (split.json, stage/, judged/)")
        p.add_argument("--set", choices=sets, default="dev",
                       help="Which set (default: dev); corpus is every role file but default")
        p.add_argument("--final", action="store_true",
                       help="Allow the held-out set: for the final check only, once the rubric is settled")
        p.add_argument("--stems", default=None, metavar="FILE",
                       help="A JSON list of roles: these only (they must belong to the set)")

    p = sub.add_parser("judge", help="Run the judged checks on one or more arms (API)")
    common(p)
    p.add_argument("--arm", nargs="+", required=True,
                   help="Arm names, or name=directory; name:STYLE[@hash] takes only the files written under it")
    p.add_argument("--instruction-model", default=DEFAULT_INSTRUCTION_JUDGE, help=f"(default: {DEFAULT_INSTRUCTION_JUDGE})")
    p.add_argument("--question-model", default=DEFAULT_QUESTION_JUDGE, help=f"(default: {DEFAULT_QUESTION_JUDGE})")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--dry-run", action="store_true", help="Say how many files would be judged, and stop")
    p.add_argument("--force", action="store_true", help="Judge again files already judged")
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("taste", help="Blind rating of each file's five instructions, 1 to 5 on quality and on "
                                     "coverage; then a report against the first arm (API)")
    common(p)
    p.add_argument("--arm", nargs="+", required=True, help="Arms, the first being the baseline")
    p.add_argument("--model", default=DEFAULT_TASTE_JUDGE, help=f"The judge (default: {DEFAULT_TASTE_JUDGE})")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--dry-run", action="store_true", help="Say how many files would be rated, and what it would cost")
    p.add_argument("--force", action="store_true", help="Rate again files already rated")
    p.add_argument("--write", action="store_true", help="Also write judged_taste/report_<model>_<set>.json")
    p.set_defaults(func=cmd_taste)

    p = sub.add_parser("report", help="Rates per measure and arm, with intervals and paired tests")
    common(p, sets=("dev", "held_out", "corpus"))
    p.add_argument("--baseline", required=True, help="Arm the others are compared with (name or name=directory)")
    p.add_argument("--arm", nargs="*", default=[], help="Other arms (name, name=directory, name:STYLE)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--write", action="store_true", help="Also write report_<set>.json")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("split", help="Draw the development and held-out sets of roles, once")
    p.add_argument("--out", required=True, help="Directory of the audit (split.json, stage/, judged/)")
    p.add_argument("--n-dev", type=int, default=DEFAULT_N_DEV)
    p.add_argument("--n-held-out", type=int, default=DEFAULT_N_HELD_OUT)
    p.add_argument("--sample", type=int, default=DEFAULT_SAMPLE,
                   help=f"Size of the development sample for the costlier runs (default: {DEFAULT_SAMPLE})")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--old-scores-dir", default=str(DEFAULT_OLD_SCORES_DIR),
                   help="The extraction run's role scores: their stems define the 'old' stratum")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("stage", help="Copy a set's role files into a staging directory (an arm)")
    common(p)
    p.add_argument("--arm", required=True, help="Name of the arm, e.g. corpus")
    p.add_argument("--source", default=None, help="Copy from here instead of the corpus")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_stage)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
