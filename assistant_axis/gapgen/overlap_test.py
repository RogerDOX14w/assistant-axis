"""The pre-pilot test of the M3 overlap rubrics (m3_overlap_rubric_draft.md, "The test"; 2026-10-03).

Both overlap rubrics, A (concept similarity, ``rubrics/overlap_concept.md``) and B (co-occurrence,
``rubrics/overlap_cooccurrence.md``), pinned as version 2, run on Haiku 4.5, Sonnet 5.5 and Opus 5.5
over pairs of existing traits where the right answers are partly known.  Opus is the reference for the
other two, as in the Opus audit of the M1 filter.  The CLI is
``data_analysis/gap_generation/overlap_test.py``.

**The pair set** (:func:`build_pair_set`), grouped as M3 would group it, one call per target with its
listed traits:

* ``nearest``: about 100 targets drawn with a fixed seed from the traits that have persona vectors, each
  with its 3 nearest existing traits under the covered setting of ``metric_config.json`` (OpenAI
  ``text-embedding-3-large``, ``w20``, centred on the fixed corpus mean, cosine), from the cached
  embeddings.  The realistic M3 case.
* labelled, from ``labelled_pairs.json`` where both members are corpus traits: every near-distinct pair,
  a seeded sample of recorded antonyms (the corpus's clean pairs) and of random unrelated pairs, the
  deliberate duplicates and the one recorded duplicate between two corpus traits; and the drop-or-merge
  pairs (``drop_or_merge.md``, the table with recorded partners excluded).  Grouped greedily
  (:func:`group_as_m3`): the member shared by most remaining pairs becomes a target and all its pairs one
  call; ties are broken with the seed.

Every pair records its group, the embedding cosine and, where both traits have vectors, the persona-space
cosine (8-slot set, slot 6, layer 25, centred and soft-sheared: :func:`persona.load_persona_space`), its
relation in the labelled pairs if it has one, and whether the two are a recorded clean pair.

**What is sent** (:func:`render_user`): the rubric as the system prompt; the user turn one JSON object,
``{"target": {"label", "description"}, "traits": [{"id", "label", "description"}, ...]}``, laid out
exactly as the rendered sample of the draft document, labels in display form (``positive_label``), the
listed traits in a seeded random order with ids 1..n, no scores, ranks or arrangement marks.  Temperature
0 where the model accepts it (Sonnet 5.5 and Opus 5.5 refuse it: ``llm.accepts_temperature``).

**Order and position bias** (AGENT_NOTES, "Comparing arms with an LLM judge"): the arms (two rubrics,
three models) never share a prompt; each rates every listed trait on an absolute scale, and every arm
receives the identical user turn (the same seeded order), so a position effect inside a call falls on
every arm alike.  Nothing in a prompt names a rubric, a model or a pair's group.

**Records**: ``responses.jsonl`` (one line per call per rubric and model: the request as sent and the
answer, parsed), ``usage.json`` (``MultiModelUsage``, written after every stage), parse-rate alerting per
(rubric, model) through ``judge.warn_if_low_parse_rate``.  :func:`analyse` computes agreement with the
reference, the correlations with persona space and with the embedding, the known groups, the unsure and
opposite rates and the pairs where the two rubrics diverge most; :func:`draw_marks` and
:func:`marks_sheet` make Roger's blinded sheet and :func:`decode_marks` reads it back.

**The arms experiment** (``coding_plan_overlap_arms.md``, 2026-10-04): three variants of rubric A on the
same pairs, each its own rubric file and pin: C six rungs 0-5 (``overlap_six``), D the relation named
with the score derived (``overlap_relation``), E Roger's line 3 (``overlap_scope``).  :data:`RUBRICS`
holds what the code needs of each (the answer key, the numeric scale, the categorical answers, D's
``wider``, the map to the decision scale); :func:`decision_value` maps any answer to the **decision
scale**, rubric A's 0-4 with "opposite" and "unsure", where the cut-offs are set.  **Passes**: pass 1
sends every call as every earlier run did; pass k > 1 sends the same calls with the listed traits in a
fresh order (:func:`pass_order_seed`, from the run seed, the pass number and the call), so every pair
is judged once per pass by every (rubric, model).  A record's key is (rubric, model, call, pass);
records written before passes count as pass 1.  :func:`analyse_arms` compares the passes (self-
consistency), the models in each pass, the coverage and crossings at the cut-off, D's relations and
``wider``, E's named kinds, and arm A's pass 1 against an earlier run's rubric-A answers.

**Round 2** (the same brief, "Round 2", 2026-10-04): A2, C2, D2 and E2 (:data:`ROUND2_OF`), each a round-1
arm with its 2 and 3 lines redrafted around the one-way implication test, in its own pinned file.
:func:`confusion_subset` picks, from every reading on record (:func:`pair_readings` over
:data:`SUBSET_SOURCES`), the pairs whose readings hold both a 2 and a 3, or a 2 whose reason describes a
containment (:data:`CONTAINMENT_PATTERN` and not :data:`TWO_SIDED_PATTERN`, round 1's patterns); a run can
send only the calls that hold them (:meth:`PairSet.restricted`; the CLI's ``--calls-from``), and
:func:`analyse_round2` compares each round-2 arm with its round-1 arm on the same pairs (the subset, and
every pair sent), self-contradiction rates included (:func:`contradictions`).

**Round 3** (the same brief, "Round 3", 2026-10-06): rubric A from version 5 on is written for **one pair
per call** (M3's design), so a rubric has a *form* (:func:`rubric_form`): ``"list"`` for every rubric and
version so far, ``"single"`` for ``overlap_concept`` from version 5 (:data:`RUBRICS`' ``single_from_version``).
Under ``single`` every pair of the pair set is its own call (:func:`to_single_calls`, keyed by ``pair_id``,
the round-1 call kept as ``origin_call_id``), the user turn is the rubric file's rendered sample
(:func:`render_single`: ``{"target": {...}, "other": {...}}``, the two objects on two lines), the answer one
object ``{"reason", "similarity"}`` (:func:`parse_single`), and the rubric is sent as a cached system block.
A later pass sends the identical prompt (there is no list to reorder).  Every record carries its ``form``
(records written before carry none and are read by their rubric version: :func:`record_form`).
:func:`analyse_round3` compares version 6 with version 4 (round 1's A) and A2 (round 2) on the same pairs:
consistency, agreement, the known groups, M3's rule (:func:`rule_decision`), the slips, Opus on the pairs
the rule escalates, and Roger's 30 marks.
"""
from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import logging
import math
import os
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from . import split_rubrics as sr
from .cost import Estimate
from .filter_rubric import _load_json, _num, _rows_of
from .llm import RETRY_DELAYS_S, call_anthropic_json, request_params
from .registry import utc_now

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- constants

SCALE: tuple[int, ...] = (0, 1, 2, 3, 4)
#: Rubric D's relations from the farthest to the nearest: their ranks 0-5 are rubric C's rungs (the
#: native scale on which D's answers are compared; the rubric lists them nearest first).
RELATIONS: tuple[str, ...] = ("different", "neighbours", "overlap", "contains", "variant", "same")
#: D's ``wider`` answers: which of the two is the wider concept of a "contains".
WIDER: tuple[str, ...] = ("target", "listed")

#: The rubrics, each a pinned file in ``rubrics/``.  ``key``: the answer field the rubric asks for;
#: ``scale``: its numeric answers (none for D); ``categories``: its other answers; ``ranks``: the
#: categories that sit on the native scale, low to high (D only); ``extra``: further answer fields
#: (D's ``wider``); ``decision``: the native answers that map to another value on the decision scale
#: (rubric A's 0-4; every other answer maps to itself); ``aliases``: other spellings of a category,
#: read as it with a parse note; ``out_per_row``: output tokens per listed trait for the estimate
#: (default :data:`OUT_PER_ROW_TOKENS`); ``kinds``: whether the reasons of 3s are searched for the kind
#: of difference they name ("asked" where line 3 asks for it, "control" where it does not);
#: ``round1``: for a round-2 rubric, the round-1 arm it redrafts (:data:`ROUND2_OF`);
#: ``single_from_version``: the first pinned version written for one pair per call (:func:`rubric_form`;
#: rubric A's draft 5, 2026-10-06; earlier versions, and every other rubric, send a list).  A and B: the
#: test of 2026-10-03; C, D and E: the arms experiment of 2026-10-04 (``coding_plan_overlap_arms.md``),
#: variants of A; A2, C2, D2 and E2: its round 2, the same day.
RUBRICS: dict[str, dict] = {
    "A": {"name": "overlap_concept", "key": "similarity", "scale": SCALE, "categories": ("opposite", "unsure"),
          "kinds": "control", "title": "concept similarity", "single_from_version": 5},
    "B": {"name": "overlap_cooccurrence", "key": "co_occurrence", "scale": SCALE, "categories": ("unsure",),
          "title": "co-occurrence"},
    "C": {"name": "overlap_six", "key": "similarity", "scale": (0, 1, 2, 3, 4, 5),
          "categories": ("opposite", "unsure"), "decision": {5: 4, 4: 3, 3: 3, 2: 2, 1: 1, 0: 0},
          "decision_note": "5 -> 4, 4 -> 3, 3 -> 3", "title": "six rungs"},
    "D": {"name": "overlap_relation", "key": "relation", "scale": (),
          "categories": tuple(reversed(RELATIONS)) + ("opposite", "unsure"), "ranks": RELATIONS,
          "extra": ("wider",),
          "decision": {"same": 4, "variant": 3, "contains": 3, "overlap": 2, "neighbours": 1, "different": 0},
          "decision_note": "same 4, variant 3, contains 3, overlap 2, neighbours 1, different 0",
          "aliases": {"neighbors": "neighbours", "neighbour": "neighbours", "neighbor": "neighbours"},
          "out_per_row": 66, "title": "relation first"},
    "E": {"name": "overlap_scope", "key": "similarity", "scale": SCALE, "categories": ("opposite", "unsure"),
          "out_per_row": 62, "kinds": "asked", "title": "Roger's line 3"},
}
#: Round 2 of the arms experiment (``coding_plan_overlap_arms.md``, "Round 2", 2026-10-04): each key is a
#: round-1 arm (the first entry) with its 2 and 3 lines redrafted around the one-way implication test, in
#: its own pinned file (the second entry); every other fact is the round-1 arm's, except the form (the
#: round-2 files are lists whatever their version: A's ``single_from_version`` is not inherited).
ROUND2_OF: dict[str, tuple[str, str, str]] = {
    "A2": ("A", "overlap_concept_implies", "A with the implication test"),
    "C2": ("C", "overlap_six_implies", "C with the implication test"),
    "D2": ("D", "overlap_relation_implies", "D with the implication test"),
    "E2": ("E", "overlap_scope_implies", "E with the implication test"),
}
for _key, (_parent, _name, _title) in ROUND2_OF.items():
    RUBRICS[_key] = {**{k: v for k, v in RUBRICS[_parent].items() if k != "single_from_version"},
                     "name": _name, "title": _title, "round1": _parent}
#: The forms a rubric is sent in: a numbered list of listed traits per target (every rubric until 2026-10-06),
#: or one pair per call (rubric A from version 5, M3's design).
FORMS: tuple[str, ...] = ("list", "single")
#: The rubrics a run sends unless ``--rubrics`` says otherwise: the original test's two.
DEFAULT_RUBRICS: tuple[str, ...] = ("A", "B")
#: The arms experiment's rubrics (arm 0 is rubric A, the baseline).
ARMS: tuple[str, ...] = ("A", "C", "D", "E")
#: Its round 2 (:data:`ROUND2_OF`).
ROUND2: tuple[str, ...] = tuple(ROUND2_OF)
#: The decision scale's cut-off the arms experiment reads (covered at 3 or more, far from alignment).
CUTOFF = 3
HAIKU, SONNET, OPUS = "claude-haiku-4-5-20251001", "claude-sonnet-5-5", "claude-opus-5-5"
FABLE = "claude-fable-5-1"
#: The test's three models (the defaults), and the models the CLI accepts: Fable was added to
#: ``overlap_test_1`` on rubric A on 2026-10-04 (Roger), after the marks; it is not a default.
MODELS: tuple[str, ...] = (HAIKU, SONNET, OPUS)
KNOWN_MODELS: tuple[str, ...] = MODELS + (FABLE,)
REFERENCE = OPUS
SHORT: dict[str, str] = {HAIKU: "Haiku 4.5", SONNET: "Sonnet 5.5", OPUS: "Opus 5.5", FABLE: "Fable 5.1"}

NEAREST = "nearest"
#: Labelled groups, in priority order: a pair in two groups is filed under the first (the other is kept
#: in ``Pair.also``).
LABELLED_GROUPS: tuple[str, ...] = ("drop_or_merge", "deliberate_duplicate", "duplicate", "near_distinct",
                                    "antonym", "random")
GROUPS: tuple[str, ...] = (NEAREST,) + LABELLED_GROUPS

N_TARGETS, N_NEIGHBOURS, N_ANTONYMS, N_RANDOM = 100, 3, 30, 30
MAX_TOKENS = 2048
TEMPERATURE = 0.0
DEFAULT_CONCURRENCY = 8

#: For the estimate: about 4 characters per token; models from Opus 4.7 on (Sonnet 5.5, Opus 5.5) use a
#: tokenizer that makes about 30% more tokens of the same text (judge_pricing's note); the answer is
#: about 60 tokens per listed trait (a one-sentence reason and the JSON around it) plus 20.
CHARS_PER_TOKEN = 4.0
NEW_TOKENIZER_FACTOR = 1.3
NEW_TOKENIZER_FRAGMENTS = ("sonnet-5", "opus-5", "opus-4-7", "opus-4-8", "fable", "mythos")
OUT_BASE_TOKENS, OUT_PER_ROW_TOKENS = 20, 60

#: Roger's blinded sheet: 30 pairs, mostly realistic nearest-neighbour pairs, some of each known group.
MARKS_QUOTAS: dict[str, int] = {NEAREST: 18, "drop_or_merge": 3, "near_distinct": 3, "antonym": 2, "random": 2,
                                "deliberate_duplicate": 2}
MARKS_ANSWER_RE = re.compile(r"^Your answer \([^)]*\):[ \t]*(.*)$")
MARKS_ITEM_RE = re.compile(r"^### (\d+)\.")


class RubricPinError(RuntimeError):
    """An overlap rubric's text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- rubrics

def rubric_form(rubric: str, version: Optional[int] = None) -> str:
    """The form ``rubric`` at ``version`` is sent in (:data:`FORMS`): ``"single"`` (one pair per call) from
    the rubric's ``single_from_version`` on (rubric A from version 5), else ``"list"``; an unknown version
    is a list (every record written before the single form)."""
    first = RUBRICS[rubric].get("single_from_version")
    return "single" if first is not None and version is not None and int(version) >= int(first) else "list"


def record_form(rec: Mapping) -> str:
    """A record's form: the one it names (records since 2026-10-06), else its rubric version's."""
    return rec.get("form") or rubric_form(rec["rubric"], rec.get("rubric_version"))


def load_rubrics(rubrics_dir: Optional[Path] = None, keys: Optional[Sequence[str]] = None) -> dict[str, dict]:
    """``{"A": {"name", "text", "version", "sha256", "form"}, ...}`` from the rubric files, for ``keys``
    (default :data:`DEFAULT_RUBRICS`, A and B), ``form`` the one the pinned version is sent in
    (:func:`rubric_form`); refuses (``RubricPinError``) when any overlap rubric's text is not its latest pin
    (``rubric_pins.py bump`` first)."""
    keys = list(DEFAULT_RUBRICS if keys is None else keys)
    unknown = [k for k in keys if k not in RUBRICS]
    if unknown:
        raise ValueError(f"unknown rubric(s) {unknown}; known: {list(RUBRICS)}")
    problems = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] in sr.OVERLAP_NAMES]
    if problems:
        raise RubricPinError("; ".join(problems) + "\n" + sr.bump_command(problems))
    pins = sr.current_versions(rubrics_dir, sr.OVERLAP_NAMES)
    out = {}
    for r in keys:
        spec = RUBRICS[r]
        text = sr.load_prompt(spec["name"], rubrics_dir)
        version = pins[spec["name"]][0]
        out[r] = {"name": spec["name"], "text": text, "version": version, "sha256": sr.sha256(text),
                  "form": rubric_form(r, version)}
    return out


def scale_lines(rubric_text: str) -> list[str]:
    """The answer list of a rubric (the lines starting ``- `` after "Give one of these answers")."""
    after = rubric_text.split("Give one of these answers", 1)[-1]
    return [ln for ln in after.splitlines() if ln.startswith("- ")]


def native_ranks(rubric: str) -> tuple:
    """The native answers that sit on a scale, low to high: the numbers of a numeric rubric, D's
    relations (whose ranks 0-5 are rubric C's rungs)."""
    spec = RUBRICS[rubric]
    return tuple(spec.get("ranks") or spec["scale"])


def native_k(rubric: str) -> int:
    """The number of points on the native scale (5 for A, B and E; 6 for C and D)."""
    return len(native_ranks(rubric))


def native_order(rubric: str) -> list[str]:
    """Every answer of ``rubric`` as text, in scale order, then the categories that are off the scale."""
    ranks = [str(v) for v in native_ranks(rubric)]
    return ranks + [c for c in RUBRICS[rubric]["categories"] if c not in ranks]


def has_wider(rubric: str) -> bool:
    """Whether the rubric asks which of a "contains" pair is the wider (D and D2)."""
    return "wider" in RUBRICS[rubric].get("extra", ())


def _names(keys: Sequence[str]) -> str:
    keys = list(keys)
    return keys[0] if len(keys) == 1 else ", ".join(keys[:-1]) + " and " + keys[-1]


def decision_maps_text(rubrics: Iterable[str]) -> str:
    """How the rubrics that do not answer on the decision scale map onto it, for tables ("C maps 5 -> 4,
    4 -> 3, 3 -> 3; D maps same 4, ..."), or "" when all of them answer on it."""
    return "; ".join(f"{r} maps {RUBRICS[r]['decision_note']}" for r in rubrics if RUBRICS[r].get("decision"))


def native_scales_text(rubrics: Iterable[str]) -> str:
    """The native scales that are not rubric A's, for tables ("C 0-5; D's relations ranked ..."), or ""."""
    rubrics = list(rubrics)
    num = [r for r in rubrics if native_k(r) == 6 and not RUBRICS[r].get("ranks")]
    rel = [r for r in rubrics if RUBRICS[r].get("ranks")]
    parts = ([f"{_names(num)} 0-5"] if num else []) + (
        [f"{_names(rel)}'s relations ranked different 0 ... same 5, as C's rungs"] if rel else [])
    return "; ".join(parts)


#: The decision scale's answers in order (rubric A's).
DECISION_ORDER: list[str] = [str(s) for s in SCALE] + ["opposite", "unsure"]


def decision_value(rubric: str, value: Any) -> Any:
    """An answer under ``rubric`` on the decision scale (rubric A's 0-4, "opposite", "unsure"), where
    the cut-offs are set: A, B and E unchanged (B's 0-4 is its own co-occurrence scale); C 5 -> 4,
    4 -> 3, 3 -> 3, 2 -> 2, 1 -> 1, 0 -> 0; D same 4, variant 3, contains 3, overlap 2, neighbours 1,
    different 0.  "opposite", "unsure" and ``None`` (unparsed) are kept."""
    if value is None or isinstance(value, bool):
        return value
    table = RUBRICS[rubric].get("decision") or {}
    return table.get(value, value)


def ordinal_value(rubric: str, value: Any) -> Any:
    """An answer as a point on its rubric's native scale: a number as itself, a D relation as its rank
    (different 0 ... same 5); "opposite", "unsure" and ``None`` kept."""
    ranks = RUBRICS[rubric].get("ranks")
    if ranks and isinstance(value, str) and value in ranks:
        return ranks.index(value)
    return value


def _mapped(answers: Mapping[str, Mapping], f) -> dict[str, dict]:
    return {pid: {**a, "value": f(a.get("value"))} for pid, a in answers.items()}


def to_decision(rubric: str, answers: Mapping[str, Mapping]) -> dict[str, dict]:
    """``{pair_id: answer}`` with every value on the decision scale (:func:`decision_value`)."""
    return _mapped(answers, lambda v: decision_value(rubric, v))


def to_ordinal(rubric: str, answers: Mapping[str, Mapping]) -> dict[str, dict]:
    """``{pair_id: answer}`` with every value on the native scale as a number (:func:`ordinal_value`)."""
    return _mapped(answers, lambda v: ordinal_value(rubric, v))


# --------------------------------------------------------------------------- the pair set

@dataclass
class Call:
    call_id: str          # "nn:<target>" or "lab:<target>"
    set: str              # "nearest" | "labelled"
    target: str
    listed: list          # stems in the order sent; the id of listed[i] is i + 1


@dataclass
class PairCall(Call):
    """A call of the single form (:func:`to_single_calls`): one pair, keyed by its ``pair_id``
    (``call_id``), with the round-1 call it came from (``origin_call_id``)."""
    origin_call_id: str = ""


def to_single_calls(calls: Iterable[Call]) -> list[PairCall]:
    """The single form's calls: every listed trait of every call its own call, keyed by the pair's id
    (``"<call_id>><listed stem>"``, as :class:`Pair` names it), in the calls' order; a :class:`PairCall`
    is kept as it is."""
    out: list[PairCall] = []
    for c in calls:
        if isinstance(c, PairCall):
            out.append(c)
            continue
        out += [PairCall(call_id=f"{c.call_id}>{s}", set=c.set, target=c.target, listed=[s], origin_call_id=c.call_id)
                for s in c.listed]
    return out


def stage_calls(calls: Iterable[Call], form: str) -> list[Call]:
    """The calls a stage of ``form`` sends: the calls as given for a list, one per pair for the single form."""
    return to_single_calls(calls) if form == "single" else list(calls)


@dataclass
class Pair:
    pair_id: str          # "<call_id>><listed stem>"
    call_id: str
    set: str
    target: str
    listed: str
    id: int               # the listed trait's id in its call
    group: str            # one of GROUPS
    nn_rank: Optional[int] = None              # 1..3 for nearest pairs (1 = nearest)
    also: list = field(default_factory=list)   # other labelled groups of the same unordered pair
    labelled_relation: Optional[str] = None    # its relation in labelled_pairs.json, any source
    recorded_pair: bool = False                # the two are a recorded clean pair (arrangement "pair")
    embedding_cos: Optional[float] = None
    persona_cos: Optional[float] = None


@dataclass
class PairSet:
    calls: list
    pairs: list
    info: dict

    def to_json(self) -> dict:
        return {"info": self.info, "calls": [asdict(c) for c in self.calls], "pairs": [asdict(p) for p in self.pairs]}

    @classmethod
    def from_json(cls, d: Mapping) -> "PairSet":
        d = d.get("result", d)
        return cls(calls=[Call(**c) for c in d["calls"]], pairs=[Pair(**p) for p in d["pairs"]],
                   info=dict(d.get("info", {})))

    def call(self, call_id: str) -> Call:
        return next(c for c in self.calls if c.call_id == call_id)

    def restricted(self, call_ids: Iterable[str]) -> "PairSet":
        """The calls named (in this pair set's order) and their pairs, unchanged: what a run restricted
        to some calls (``--calls-from``) sent.  ``info`` is this pair set's, with ``restricted_to``."""
        keep = set(call_ids)
        unknown = sorted(keep - {c.call_id for c in self.calls})
        if unknown:
            raise ValueError(f"{len(unknown)} call(s) not in the pair set: {unknown[:5]}")
        return PairSet(calls=[c for c in self.calls if c.call_id in keep],
                       pairs=[p for p in self.pairs if p.call_id in keep],
                       info={**self.info, "restricted_to": {"n_calls": len(keep), "of_calls": len(self.calls),
                                                            "of_pairs": len(self.pairs)}})


def same_calls(a: PairSet, b: PairSet) -> bool:
    """Whether two pair sets send the same calls: the same call ids, with the same listed traits in the
    same order (what a resume, and a run compared with an earlier one, require)."""
    return [(c.call_id, list(c.listed)) for c in a.calls] == [(c.call_id, list(c.listed)) for c in b.calls]


def _ukey(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def _field(p: Any, name: str, default=None):
    return p.get(name, default) if isinstance(p, Mapping) else getattr(p, name, default)


def labelled_groups(labelled: Iterable, corpus: Mapping, dm_pairs: Sequence[tuple[str, str]], *, seed: int = 0,
                    n_antonyms: int = N_ANTONYMS, n_random: int = N_RANDOM) -> tuple[list[dict], dict]:
    """The labelled pairs of the test, each ``{"a", "b", "group", "also"}``: both members corpus traits;
    every near-distinct pair, deliberate duplicate and corpus-to-corpus duplicate; a seeded sample of
    ``n_antonyms`` recorded antonyms (source ``arrangement_pair``, not uncertain) and of ``n_random``
    unrelated pairs; the drop-or-merge pairs.  A pair in two groups is filed under the first of
    :data:`LABELLED_GROUPS`.  Returns ``(entries, info)``."""
    labelled = list(labelled)
    in_corpus = lambda p: _field(p, "a") in corpus and _field(p, "b") in corpus  # noqa: E731
    pools: dict[str, list] = {g: [] for g in LABELLED_GROUPS}
    skipped = Counter()
    for p in labelled:
        rel = _field(p, "relation")
        group = {"near_distinct": "near_distinct", "deliberate_duplicate": "deliberate_duplicate",
                 "duplicate": "duplicate", "unrelated": "random"}.get(rel)
        if rel == "antonym" and _field(p, "source") == "arrangement_pair" and not _field(p, "uncertain", False):
            group = "antonym"
        if group is None:
            continue
        if not in_corpus(p):
            skipped[group] += 1
            continue
        pools[group].append(_ukey(_field(p, "a"), _field(p, "b")))
    for a, b in dm_pairs:
        if a in corpus and b in corpus:
            pools["drop_or_merge"].append(_ukey(a, b))
        else:
            skipped["drop_or_merge"] += 1
    pool_sizes = {g: len(set(v)) for g, v in pools.items()}
    chosen: dict[str, list] = {}
    for g in LABELLED_GROUPS:
        uniq = sorted(set(pools[g]))
        n = {"antonym": n_antonyms, "random": n_random}.get(g)
        if n is not None and n < len(uniq):
            uniq = sorted(random.Random(f"overlap-test:{seed}:{g}").sample(uniq, n))
        chosen[g] = uniq
    entries: dict[tuple, dict] = {}
    for g in LABELLED_GROUPS:
        for k in chosen[g]:
            if k in entries:
                entries[k]["also"].append(g)
            else:
                entries[k] = {"a": k[0], "b": k[1], "group": g, "also": []}
    info = {"pool_sizes": pool_sizes, "skipped_not_in_corpus": dict(skipped),
            "chosen": {g: len(v) for g, v in chosen.items()}, "filed": dict(Counter(e["group"] for e in entries.values()))}
    return list(entries.values()), info


def group_as_m3(entries: Sequence[Mapping], *, seed: int = 0) -> list[tuple[str, list]]:
    """Group pairs into calls as M3 would (one call per target, all its listed traits in it): repeatedly
    take the member shared by most remaining pairs as a target (ties broken with the seed), and give it
    every remaining pair it is in.  Returns ``[(target, [entry, ...]), ...]``."""
    rng = random.Random(f"overlap-test:{seed}:grouping")
    remaining = list(entries)
    out = []
    while remaining:
        deg = Counter(m for e in remaining for m in (e["a"], e["b"]))
        top = max(deg.values())
        cands = sorted(m for m, d in deg.items() if d == top)
        t = cands[0] if len(cands) == 1 else rng.choice(cands)
        out.append((t, [e for e in remaining if t in (e["a"], e["b"])]))
        remaining = [e for e in remaining if t not in (e["a"], e["b"])]
    return out


def seeded_order(stems: Iterable[str], call_id: str, seed: int) -> list[str]:
    """The listed traits in a random order fixed by the seed and the call (the same for every arm)."""
    out = sorted(stems)
    random.Random(f"overlap-test:{seed}:order:{call_id}").shuffle(out)
    return out


def pass_order_seed(seed: int, pass_no: int, call_id: str) -> Optional[str]:
    """The shuffle seed of a call's listed traits in pass ``pass_no``: ``None`` in pass 1, which sends the
    call's own order (:func:`seeded_order`, as every earlier run sent it); for a later pass a seed of its
    own, derived from the run seed, the pass number and the call (the same for every arm and model, so a
    pass's user turns are identical across arms)."""
    return None if int(pass_no) == 1 else f"overlap-test:{seed}:order:{call_id}:pass{int(pass_no)}"


def listed_order(call: Call, order_seed: Optional[str] = None) -> list[str]:
    """The call's listed traits in the order sent: ``call.listed`` without a seed, else a fresh shuffle
    of them with ``order_seed`` (it may happen to equal the first order, always so for one trait)."""
    if order_seed is None:
        return list(call.listed)
    out = sorted(call.listed)
    random.Random(order_seed).shuffle(out)
    return out


def build_pair_set(corpus: Mapping[str, Mapping], emb_stems: Sequence[str], Z: np.ndarray,
                   persona: Mapping[str, np.ndarray], labelled: Iterable, dm_pairs: Sequence[tuple[str, str]],
                   partner: Mapping[str, str], *, seed: int = 0, n_targets: int = N_TARGETS,
                   n_neighbours: int = N_NEIGHBOURS, n_antonyms: int = N_ANTONYMS, n_random: int = N_RANDOM,
                   labelled_relations: Optional[Mapping[tuple, str]] = None) -> PairSet:
    """The test's calls and pairs (module docstring).

    ``corpus``: ``{stem: {"label", "description"}}``; ``emb_stems`` / ``Z``: the corpus rows in the
    covered space (unit rows, so a dot product is the cosine); ``persona``: ``{stem: unit vector}`` for the
    traits with persona vectors; ``labelled``: the labelled pairs (``LabelledPair`` or dicts);
    ``partner``: recorded clean-pair partners; ``labelled_relations``: ``{unordered pair: relation}`` for
    annotating every pair (default: built from ``labelled``)."""
    labelled = list(labelled)
    idx = {s: i for i, s in enumerate(emb_stems)}
    missing = [s for s in corpus if s not in idx]
    if missing:
        raise ValueError(f"{len(missing)} corpus traits have no row in the covered space: {missing[:5]}")
    if labelled_relations is None:
        labelled_relations = {}
        for p in labelled:
            labelled_relations.setdefault(_ukey(_field(p, "a"), _field(p, "b")), _field(p, "relation"))

    def emb_cos(a, b):
        return float(Z[idx[a]] @ Z[idx[b]])

    def per_cos(a, b):
        return float(persona[a] @ persona[b]) if a in persona and b in persona else None

    def make_pair(call: Call, stem: str, group: str, **kw) -> Pair:
        return Pair(pair_id=f"{call.call_id}>{stem}", call_id=call.call_id, set=call.set, target=call.target,
                    listed=stem, id=call.listed.index(stem) + 1, group=group,
                    labelled_relation=labelled_relations.get(_ukey(call.target, stem)),
                    recorded_pair=partner.get(call.target) == stem or partner.get(stem) == call.target,
                    embedding_cos=round(emb_cos(call.target, stem), 6),
                    persona_cos=None if per_cos(call.target, stem) is None else round(per_cos(call.target, stem), 6),
                    **kw)

    calls, pairs = [], []
    # nearest: targets among the traits with persona vectors, neighbours among all corpus traits
    eligible = sorted(s for s in persona if s in corpus)
    targets = sorted(random.Random(f"overlap-test:{seed}:targets").sample(eligible, min(n_targets, len(eligible))))
    corpus_rows = np.array([idx[s] for s in sorted(corpus)])
    corpus_stems = sorted(corpus)
    for t in targets:
        sims = Z[corpus_rows] @ Z[idx[t]]
        order = [corpus_stems[i] for i in np.argsort(-sims, kind="stable") if corpus_stems[i] != t][:n_neighbours]
        call = Call(call_id=f"nn:{t}", set=NEAREST, target=t, listed=seeded_order(order, f"nn:{t}", seed))
        calls.append(call)
        for rank, s in enumerate(order, 1):
            pairs.append(make_pair(call, s, NEAREST, nn_rank=rank))
    # labelled, grouped as M3 would group them
    entries, lab_info = labelled_groups(labelled, corpus, dm_pairs, seed=seed, n_antonyms=n_antonyms,
                                        n_random=n_random)
    for t, mine in group_as_m3(entries, seed=seed):
        other = {(e["b"] if e["a"] == t else e["a"]): e for e in mine}
        call = Call(call_id=f"lab:{t}", set="labelled", target=t, listed=seeded_order(other, f"lab:{t}", seed))
        calls.append(call)
        for s in call.listed:
            e = other[s]
            pairs.append(make_pair(call, s, e["group"], also=list(e["also"])))
    n_listed = Counter(len(c.listed) for c in calls)
    seen = Counter(_ukey(p.target, p.listed) for p in pairs)
    info = {"seed": seed, "n_targets_requested": n_targets, "n_neighbours": n_neighbours,
            "n_eligible_targets": len(eligible), "n_calls": len(calls),
            "n_calls_by_set": dict(Counter(c.set for c in calls)), "n_pairs": len(pairs),
            "n_pairs_by_group": {g: sum(p.group == g for p in pairs) for g in GROUPS},
            "n_pairs_with_persona_cos": sum(p.persona_cos is not None for p in pairs),
            "list_sizes": {str(k): v for k, v in sorted(n_listed.items())},
            "n_unordered_pairs_twice": sum(1 for v in seen.values() if v > 1),
            "nearest_recorded_antonyms": sum(p.group == NEAREST and p.recorded_pair for p in pairs),
            "labelled": lab_info}
    return PairSet(calls=calls, pairs=pairs, info=info)


# --------------------------------------------------------------------------- what is sent

def payload_object(call: Call, corpus: Mapping[str, Mapping], order: Optional[Sequence[str]] = None) -> dict:
    """The user turn as an object: the target, then the listed traits with ids 1..n, in ``order``
    (default the call's own)."""
    t = corpus[call.target]
    return {"target": {"label": t["label"], "description": t["description"]},
            "traits": [{"id": i, "label": corpus[s]["label"], "description": corpus[s]["description"]}
                       for i, s in enumerate(call.listed if order is None else order, 1)]}


def render_payload(obj: Mapping) -> str:
    """The JSON object laid out as the draft's rendered sample: the target on the first line, each listed
    trait on its own line."""
    lines = ['{"target": ' + json.dumps(obj["target"], ensure_ascii=False) + ",", ' "traits": [']
    body = ",\n".join("  " + json.dumps(t, ensure_ascii=False) for t in obj["traits"])
    return "\n".join(lines) + "\n" + body + "\n ]}"


def render_user(call: Call, corpus: Mapping[str, Mapping], order_seed: Optional[str] = None) -> str:
    """The user turn as sent: the listed traits in the call's own order, or shuffled with ``order_seed``
    (:func:`pass_order_seed`)."""
    return render_payload(payload_object(call, corpus, listed_order(call, order_seed)))


def payload_single(call: Call, corpus: Mapping[str, Mapping]) -> dict:
    """The single form's user turn as an object: the target and the one other trait, labels and
    descriptions only (no ids, scores, ranks or arrangement marks)."""
    if len(call.listed) != 1:
        raise ValueError(f"{call.call_id}: the single form sends one pair per call, not {len(call.listed)}")
    t, o = corpus[call.target], corpus[call.listed[0]]
    return {"target": {"label": t["label"], "description": t["description"]},
            "other": {"label": o["label"], "description": o["description"]}}


def render_single(call: Call, corpus: Mapping[str, Mapping]) -> str:
    """The single form's user turn laid out as the rubric file's rendered sample (``overlap_concept.md``,
    "Rendered sample"): the target on the first line, the other trait on the second, indented one space."""
    obj = payload_single(call, corpus)
    return ('{"target": ' + json.dumps(obj["target"], ensure_ascii=False) + ",\n"
            ' "other": ' + json.dumps(obj["other"], ensure_ascii=False) + "}")


def default_cache_system(form: str) -> bool:
    """Whether a stage of ``form`` marks the rubric as a cached system block: yes for the single form (the
    rubric, about 600 tokens, is above the 512-token minimum of Sonnet 5.5 and Opus 5.5, and every call of
    a stage repeats it), no for the list form, as every list run so far was sent (Haiku 4.5 caches only from
    4,096 tokens, where the marker is harmless)."""
    return form == "single"


def call_params(call: Call, corpus: Mapping, *, rubric_text: str, model: str, max_tokens: int = MAX_TOKENS,
                temperature: Optional[float] = TEMPERATURE, order_seed: Optional[str] = None, form: str = "list",
                cache_system: Optional[bool] = None) -> dict:
    """The Messages API request for one call (``llm.request_params``): the user turn of ``form``
    (:func:`render_user`, or :func:`render_single` for one pair per call); the system block marked for the
    prompt cache when ``cache_system`` (default :func:`default_cache_system`: the single form only).  The
    rubrics are cacheable on Sonnet 5.5 and Opus 5.5 (512-token minimum); the list runs were sent uncached."""
    user = render_single(call, corpus) if form == "single" else render_user(call, corpus, order_seed)
    cache = default_cache_system(form) if cache_system is None else bool(cache_system)
    return request_params(model=model, system=rubric_text, user=user, max_tokens=max_tokens, temperature=temperature,
                          cache_system=cache)


def rendered_prompt(call: Call, corpus: Mapping, *, rubric: str, rubric_text: str, model: str,
                    order_seed: Optional[str] = None, pass_no: Optional[int] = None, form: str = "list",
                    cache_system: Optional[bool] = None) -> str:
    """The request as the model receives it, for reading (AGENT_NOTES: read the rendered prompt)."""
    params = call_params(call, corpus, rubric_text=rubric_text, model=model, order_seed=order_seed, form=form,
                         cache_system=cache_system)
    sent = {k: v for k, v in params.items() if k not in ("system", "messages")}
    cached = params["system"][0].get("cache_control")
    which = f", pass {pass_no}" if pass_no is not None else ""
    return (f"=== rubric {rubric} ({RUBRICS[rubric]['name']}), {call.call_id}{which}, {form} form, request settings "
            f"{json.dumps(sent)}, system block cache_control {json.dumps(cached)} ===\n--- system ---\n"
            f"{params['system'][0]['text']}\n--- user ---\n{params['messages'][0]['content']}\n")


# --------------------------------------------------------------------------- parsing

def answer_value(v: Any, categories: Sequence[str], scale: Sequence[int] = SCALE,
                 aliases: Optional[Mapping[str, str]] = None) -> Any:
    """An answer: an integer of ``scale`` (default 0-4; also written as a string), or one of
    ``categories`` in any case (``aliases`` maps other spellings to a category); else ``None``.  An
    empty ``scale`` (rubric D) takes categories only."""
    if isinstance(v, str):
        s = v.strip().lower()
        s = (aliases or {}).get(s, s)
        if s in categories:
            return s
    if not scale:
        return None
    n = _num(v, min(scale), max(scale), integer=True)
    return int(n) if n is not None else None


def _scale_text(spec: Mapping) -> str:
    cats = list(spec["categories"])
    scale = spec["scale"]
    return f"{min(scale)}-{max(scale)} or one of {cats}" if scale else f"one of {cats}"


#: Written in a ``wider`` field for "no answer" (not a parse note on a row that needs none).
_NO_WIDER = {"", "null", "none", "n/a", "na", "-"}


def wider_value(v: Any) -> tuple[Optional[str], bool]:
    """D's ``wider``: ``(value, given)``, the value "target" or "listed" (any case, "the target" and "the
    listed trait" too) or ``None``; ``given`` is False when the field is absent, null or empty."""
    if v is None:
        return None, False
    if not isinstance(v, str):
        return None, True
    s = v.strip().strip('"').lower()
    if s in _NO_WIDER:
        return None, False
    s = s.removeprefix("the ").removesuffix(" trait").removesuffix(" one").strip()
    return (s if s in WIDER else None), True


#: 3 (2026-10-06): the single form's answer object (:func:`parse_single`); the list parser is unchanged.
#: 2 (2026-10-03, after Sonnet 5.5's first stage in overlap_test_1): the last complete results object
#: in the text is the answer (a model that writes an answer, then "Correction: ..." and the answer
#: again); 1 read the first-to-last brace span as one object.  The analysis always re-parses the
#: recorded text with the current parser.
PARSER_VERSION = 3


def result_objects(text: str) -> list[dict]:
    """Every top-level JSON object in ``text`` that carries a ``results`` list, in order (nested
    objects are skipped; text between objects, fences and prose included, is ignored)."""
    dec = json.JSONDecoder(strict=False)
    out, i = [], 0
    while True:
        j = text.find("{", i)
        if j < 0:
            return out
        try:
            obj, end = dec.raw_decode(text, j)
        except json.JSONDecodeError:
            i = j + 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("results"), list):
            out.append(obj)
        i = end


def single_objects(text: str, key: str) -> list[dict]:
    """Every top-level JSON object in ``text`` that is a single-form answer (it carries ``key``) or wraps one
    in a ``results`` list, in order (nested objects are skipped; text between objects is ignored)."""
    dec = json.JSONDecoder(strict=False)
    out, i = [], 0
    while True:
        j = text.find("{", i)
        if j < 0:
            return out
        try:
            obj, end = dec.raw_decode(text, j)
        except json.JSONDecodeError:
            i = j + 1
            continue
        if isinstance(obj, dict) and (key in obj or isinstance(obj.get("results"), list)):
            out.append(obj)
        i = end


def parse_single(text: Optional[str], rubric: str) -> tuple[dict, dict, dict]:
    """The single form's answer, one object ``{"reason", <key>}``, as :func:`parse_answer`'s
    ``(rows, errors, meta)`` with the one pair as id 1.  As lenient as the list parser: the last complete
    answer object in the text is the answer (a self-correction), fences and prose are ignored, extra keys are
    ignored and noted (``meta["extra_keys"]``), the answer's position after the reason is recorded
    (``reason_first``), the value is read on the rubric's scale and categories; an answer wrapped as
    ``{"results": [one row]}`` (the list form's shape, which a model may remember) is accepted with a note
    (``meta["wrapped"]``), its ``id`` counted as an extra key.  ``meta["notes"]`` lists the notes."""
    spec = RUBRICS[rubric]
    key, cats, scale = spec["key"], spec["categories"], spec["scale"]
    aliases = spec.get("aliases") or {}
    meta: dict = {"n_rows": 0, "in_order": True, "extra_ids": [], "reason_first": None, "n_result_objects": 0,
                  "wrapped": False, "extra_keys": [], "notes": []}
    if not text or not text.strip():
        return {}, {1: "empty response"}, meta
    objs = single_objects(text, key)
    if not objs:
        try:
            obj = _load_json(text)
        except (ValueError, json.JSONDecodeError) as exc:
            return {}, {1: f"unparseable response: {exc}"}, meta
        if not (isinstance(obj, dict) and (key in obj or isinstance(obj.get("results"), list))):
            return {}, {1: f"unparseable response: no object with {key!r}"}, meta
        objs = [obj]
    meta["n_result_objects"] = len(objs)
    row = objs[-1]
    if key not in row and isinstance(row.get("results"), list):
        rows = [r for r in row["results"] if isinstance(r, dict)]
        meta["wrapped"] = True
        meta["notes"].append("answer wrapped in a results list")
        if len(rows) != 1:
            return {}, {1: f"results holds {len(rows)} rows, not one"}, meta
        row = rows[0]
    meta["n_rows"] = 1
    reason = row.get("reason")
    extra = sorted(k for k in row if k not in ("reason", key))
    if extra:
        meta["extra_keys"] = extra
        meta["notes"].append(f"extra keys {extra}")
    if not isinstance(reason, str) or not reason.strip():
        return {}, {1: "reason missing"}, meta
    if key not in row:
        return {}, {1: f"{key} missing"}, meta
    val = answer_value(row.get(key), cats, scale, aliases)
    if val is None:
        return {}, {1: f"{key} {row.get(key)!r} is not {_scale_text(spec)}"}, meta
    keys = list(row.keys())
    out = {"reason": " ".join(reason.split()), "value": val, "reason_first": keys.index("reason") < keys.index(key)}
    meta["reason_first"] = out["reason_first"]
    return {1: out}, {}, meta


def parse_answer(text: Optional[str], rubric: str, n_listed: int, form: str = "list") -> tuple[dict, dict, dict]:
    """For the single form (``form="single"``), :func:`parse_single`.  For a list:
    ``(rows, errors, meta)``: ``rows[id] = {"reason", "value", "reason_first"}`` for every listed id
    that parsed (rubric D's rows add ``"wider"``, "target", "listed" or ``None``, and ``"notes"``, the
    parse notes: a "contains" without a usable ``wider``, a ``wider`` given with another relation, an
    alias spelling); ``errors[id]`` says why each other id failed (``"missing"``, a validation message,
    or the JSON failure for every id); ``meta``: rows returned, whether they came in the order given, ids
    outside 1..n, whether every parsed row put its reason first, and how many complete results objects
    the text held (the last is the answer: :data:`PARSER_VERSION`).  The answer key, its scale and its
    categories are the rubric's (:data:`RUBRICS`)."""
    if form == "single":
        return parse_single(text, rubric)
    spec = RUBRICS[rubric]
    key, cats, scale = spec["key"], spec["categories"], spec["scale"]
    aliases = spec.get("aliases") or {}
    has_wider = "wider" in spec.get("extra", ())
    want = list(range(1, n_listed + 1))
    meta: dict = {"n_rows": 0, "in_order": None, "extra_ids": [], "reason_first": None, "n_result_objects": 0}
    if not text or not text.strip():
        return {}, {i: "empty response" for i in want}, meta
    objs = result_objects(text)
    meta["n_result_objects"] = len(objs)
    if objs:
        raw = objs[-1]["results"]
    else:
        try:
            raw = _rows_of(_load_json(text))
        except (ValueError, json.JSONDecodeError) as exc:
            return {}, {i: f"unparseable response: {exc}" for i in want}, meta
    rows: dict[int, dict] = {}
    errors: dict[int, str] = {}
    order: list[int] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = _num(r.get("id"), 1, n_listed, integer=True)
        if rid is None:
            meta["extra_ids"].append(r.get("id"))
            continue
        rid = int(rid)
        if rid in rows:
            continue
        order.append(rid)
        reason = r.get("reason")
        val = answer_value(r.get(key), cats, scale, aliases) if key in r else None
        if not isinstance(reason, str) or not reason.strip():
            errors[rid] = "reason missing"
        elif key not in r:
            errors[rid] = f"{key} missing"
        elif val is None:
            errors[rid] = f"{key} {r.get(key)!r} is not {_scale_text(spec)}"
        else:
            keys = list(r.keys())
            row = {"reason": " ".join(reason.split()), "value": val,
                   "reason_first": keys.index("reason") < keys.index(key)}
            if has_wider:
                notes = []
                raw_val = r.get(key)
                if isinstance(raw_val, str) and raw_val.strip().lower() in aliases:
                    notes.append(f"{key} {raw_val!r} read as {val!r}")
                wider, given = wider_value(r.get("wider"))
                if val == "contains":
                    if wider is None:
                        notes.append(f"wider {r.get('wider')!r} is not target or listed" if given
                                     else "contains without wider")
                elif given:
                    notes.append(f"wider {r.get('wider')!r} given with {val}")
                    wider = None
                row.update(wider=wider if val == "contains" else None, notes=notes)
            rows[rid] = row
            errors.pop(rid, None)
    for i in want:
        if i not in rows and i not in errors:
            errors[i] = "missing"
    meta.update(n_rows=len(raw), in_order=order == sorted(order),
                reason_first=all(r["reason_first"] for r in rows.values()) if rows else None)
    if has_wider:
        meta["n_notes"] = sum(len(r["notes"]) for r in rows.values())
    return rows, errors, meta


# --------------------------------------------------------------------------- running

#: A call whose answer does not parse fully is sent once more (same request), for every model alike;
#: the first attempt's parse rate is reported beside the final one.
ASK_ATTEMPTS = 2


def record_pass(rec: Mapping) -> int:
    """A record's pass (records written before passes existed are pass 1)."""
    return int(rec.get("pass") or 1)


def response_key(rec: Mapping) -> tuple[str, str, str, int]:
    """(rubric, model, call, pass): one answer is kept per key (:func:`latest_records`)."""
    return rec["rubric"], rec["model"], rec["call_id"], record_pass(rec)


def record_passes(records: Iterable[Mapping]) -> list[int]:
    """The passes present in ``records``, in order."""
    return sorted({record_pass(r) for r in records})


def write_usage(usage: MultiModelUsage, path: Path) -> None:
    """``usage.json`` written whole or not at all (a temporary file beside it, then a rename), so that a
    session cut off mid-write leaves the last complete record of the spend for the resume."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(usage.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def usage_from_records(records: Iterable[Mapping]) -> MultiModelUsage:
    """The spend the records show: every answered request charged with the tokens its ``usage_raw``
    holds (billed as ``llm.billed_usage`` does).  Checked against ``usage.json`` on resume."""
    out = MultiModelUsage()
    for r in records:
        u = (r.get("response") or {}).get("usage_raw") or {}
        if not u:
            continue
        prompt = int(u.get("input_tokens") or 0) + int(round(1.25 * int(u.get("cache_creation_input_tokens") or 0)
                                                             + 0.1 * int(u.get("cache_read_input_tokens") or 0)))
        out.charge(r["model"], prompt, int(u.get("output_tokens") or 0))
    return out


class SessionBusy(RuntimeError):
    """Another live session of the same run holds its lock."""


def acquire_session_lock(out_dir: Path):
    """An exclusive lock on the run's ``responses.jsonl`` (created if missing) for a live session: a
    second session of the same run (a resume started while a cut-off one still runs) is refused with
    :class:`SessionBusy` instead of sending the same calls twice.  The lock goes with the process, so a
    session that was killed leaves nothing to clear.  Returns the open file; close it to release."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fh = open(out_dir / "responses.jsonl", "a", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        fh.close()
        raise SessionBusy(f"another session of this run holds the lock on {out_dir / 'responses.jsonl'}: wait for "
                          "it to end before resuming") from exc
    return fh


def read_records(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def answered(rec: Mapping) -> bool:
    return (rec.get("response") or {}).get("text") is not None


def reparse(rec: Mapping) -> tuple[dict, dict, dict]:
    """A record's answer parsed with the current parser in the record's form (never the stored ``parsed``,
    which an older parser may have written)."""
    return parse_answer((rec.get("response") or {}).get("text"), rec["rubric"], len(rec["listed"]),
                        form=record_form(rec))


def fully_parsed(rec: Mapping) -> bool:
    return answered(rec) and not reparse(rec)[1]


def latest_records(records: Iterable[Mapping]) -> dict[tuple, dict]:
    """The final record per (rubric, model, call, pass): the last one whose answer parses fully, else the
    last one (a call asked again, in the stage or on resume, has several)."""
    last: dict[tuple, dict] = {}
    good: dict[tuple, dict] = {}
    for r in records:
        k = response_key(r)
        last[k] = dict(r)
        if fully_parsed(r):
            good[k] = dict(r)
    return {k: good.get(k, v) for k, v in last.items()}


def done_keys(records: Iterable[Mapping]) -> set:
    """(rubric, model, call, pass) keys whose answer on record parses fully: not sent again on resume."""
    return {k for k, r in latest_records(records).items() if fully_parsed(r)}


@dataclass
class StageResult:
    rubric: str
    model: str
    n_calls: int
    pass_no: int = 1
    n_sent: int = 0
    n_skipped: int = 0
    n_reasked: int = 0
    n_pairs: int = 0
    n_ok: int = 0
    n_ok_first: int = 0
    budget_exceeded: bool = False

    @property
    def parse_rate(self) -> Optional[float]:
        return self.n_ok / self.n_pairs if self.n_pairs else None


class OverlapRunner:
    """Sends the calls of one (rubric, model, pass) stage concurrently and appends one record per request
    to ``responses.jsonl`` as it completes.  A call whose answer does not parse fully is sent once more
    (:data:`ASK_ATTEMPTS`); each record carries its ``parse_attempt``, its ``pass`` and the order its
    listed traits were sent in (``listed``; ``order_seed``, :func:`pass_order_seed` with ``seed``, the
    run's).  ``usage`` (a ``MultiModelUsage``, usually ``cost.GuardedUsage`` with the run's cap) is
    charged for every response received and, with ``usage_path``, written there after every record
    (:func:`write_usage`), so a session cut off mid-stage leaves its spend on record; when the cap is
    crossed the stage stops sending, keeps the answer that crossed it and reports ``budget_exceeded``.

    A rubric of the single form (its loaded ``form``, :func:`load_rubrics`) sends every pair of the stage's
    calls as its own call (:func:`to_single_calls`), the identical prompt in every pass, with the rubric as a
    cached system block (``cache_system``: ``None`` for :func:`default_cache_system`, or force it); its
    records add ``form``, ``pair_id`` and ``origin_call_id``, and ``request.cache_system``."""

    def __init__(self, client, rubrics: Mapping[str, Mapping], corpus: Mapping[str, Mapping], *,
                 usage: MultiModelUsage, responses_path: Path, concurrency: int = DEFAULT_CONCURRENCY,
                 max_tokens: int = MAX_TOKENS, temperature: Optional[float] = TEMPERATURE,
                 retry_delays: Sequence[float] = RETRY_DELAYS_S, ask_attempts: int = ASK_ATTEMPTS,
                 seed: int = 0, usage_path: Optional[Path] = None, cache_system: Optional[bool] = None):
        self.client = client
        self.rubrics = rubrics
        self.corpus = corpus
        self.usage = usage
        self.responses_path = Path(responses_path)
        self.concurrency = max(1, int(concurrency))
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.retry_delays = tuple(retry_delays)
        self.ask_attempts = max(1, int(ask_attempts))
        self.seed = seed
        self.usage_path = None if usage_path is None else Path(usage_path)
        self.cache_system = cache_system

    def done(self) -> set:
        return done_keys(read_records(self.responses_path))

    def form(self, rubric: str) -> str:
        """The form the stage of ``rubric`` is sent in (the loaded rubric's; a list when it names none)."""
        return self.rubrics[rubric].get("form") or "list"

    def caches(self, rubric: str) -> bool:
        """Whether the stage of ``rubric`` marks its system block for the prompt cache."""
        return default_cache_system(self.form(rubric)) if self.cache_system is None else bool(self.cache_system)

    def _record(self, call: Call, rubric: str, model: str, params: Mapping, text: Optional[str], meta: Mapping,
                rows: Mapping, errors: Mapping, pmeta: Mapping, attempt: int, *, pass_no: int = 1,
                order: Optional[Sequence[str]] = None, order_seed: Optional[str] = None) -> dict:
        rb = self.rubrics[rubric]
        form = self.form(rubric)
        req = {k: v for k, v in params.items() if k not in ("system", "messages")}
        req["system_sha256"] = rb["sha256"]
        req["cache_system"] = "cache_control" in params["system"][0]
        req["user"] = params["messages"][0]["content"]
        rec = {"rubric": rubric, "rubric_name": rb["name"], "rubric_version": rb["version"],
               "prompt_sha256": rb["sha256"], "form": form, "model": model, "call_id": call.call_id, "set": call.set,
               "target": call.target, "listed": list(call.listed if order is None else order), "pass": pass_no,
               "order_seed": order_seed, "request": req,
               "response": {"text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                            "attempts": meta.get("attempts"), "error": meta.get("error")},
               "parse_attempt": attempt, "parser_version": PARSER_VERSION,
               "parsed": {str(k): v for k, v in rows.items()}, "errors": {str(k): v for k, v in errors.items()},
               "parse_meta": dict(pmeta), "at": utc_now()}
        if form == "single":
            rec["pair_id"] = call.call_id
            rec["origin_call_id"] = getattr(call, "origin_call_id", "") or call.call_id.rsplit(">", 1)[0]
        return rec

    async def run_stage(self, rubric: str, model: str, calls: Sequence[Call], pass_no: int = 1) -> StageResult:
        form = self.form(rubric)
        calls = stage_calls(calls, form)
        cache = self.caches(rubric)
        done = self.done()
        todo = [c for c in calls if (rubric, model, c.call_id, pass_no) not in done]
        res = StageResult(rubric=rubric, model=model, n_calls=len(calls), pass_no=pass_no,
                          n_skipped=len(calls) - len(todo))
        sem = asyncio.Semaphore(self.concurrency)
        lock = asyncio.Lock()
        stop = asyncio.Event()
        text_of = self.rubrics[rubric]["text"]
        self.responses_path.parent.mkdir(parents=True, exist_ok=True)

        async def one(call: Call) -> None:
            # the single form has no list to reorder: every pass sends the identical prompt
            order_seed = None if form == "single" else pass_order_seed(self.seed, pass_no, call.call_id)
            order = listed_order(call, order_seed)
            for attempt in range(1, self.ask_attempts + 1):
                if stop.is_set():
                    return
                async with sem:
                    if stop.is_set():
                        return
                    params = call_params(call, self.corpus, rubric_text=text_of, model=model,
                                         max_tokens=self.max_tokens, temperature=self.temperature,
                                         order_seed=order_seed, form=form, cache_system=cache)
                    meta: dict = {}
                    try:
                        text = await call_anthropic_json(
                            self.client, system=text_of, user=params["messages"][0]["content"], model=model,
                            max_tokens=self.max_tokens, temperature=self.temperature, usage=self.usage,
                            cache_system=cache, retry_delays=self.retry_delays, meta=meta)
                    except BudgetExceededError:
                        text = meta.get("text")
                        res.budget_exceeded = True
                        stop.set()
                    rows, errors, pmeta = parse_answer(text, rubric, len(order), form=form)
                    rec = self._record(call, rubric, model, params, text, meta, rows, errors, pmeta, attempt,
                                       pass_no=pass_no, order=order, order_seed=order_seed)
                    async with lock:
                        with self.responses_path.open("a", encoding="utf-8") as fh:
                            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        if self.usage_path is not None:
                            write_usage(self.usage, self.usage_path)
                        res.n_sent += 1
                        res.n_reasked += int(attempt > 1)
                if not errors:
                    return
                if text is None and meta.get("error"):           # the request failed: no answer to ask about
                    logger.warning("rubric %s on %s, pass %d, %s: request failed, left for the resume: %s", rubric,
                                   model, pass_no, call.call_id, str(meta["error"])[:200])
                    return
                logger.warning("rubric %s on %s, pass %d, %s: answer did not parse fully (attempt %d of %d): %s",
                               rubric, model, pass_no, call.call_id, attempt, self.ask_attempts,
                               "; ".join(sorted(set(errors.values())))[:200])

        await asyncio.gather(*(one(c) for c in todo))
        # the stage's parse rate over every pair of its calls on record (sent now or earlier), final and
        # at the first attempt
        records = read_records(self.responses_path)
        latest = latest_records(records)
        first = first_records(records)
        for c in calls:
            rec = latest.get((rubric, model, c.call_id, pass_no))
            if rec is None:
                continue
            res.n_pairs += len(c.listed)
            res.n_ok += len(reparse(rec)[0])
            res.n_ok_first += len(reparse(first[(rubric, model, c.call_id, pass_no)])[0])
        label = f"overlap_test:{RUBRICS[rubric]['name']}:{model}" + (f":pass{pass_no}" if pass_no != 1 else "")
        warn_if_low_parse_rate(label=label, n_ok=res.n_ok, n_total=res.n_pairs, logger_obj=logger,
                               extra=f"first attempt {res.n_ok_first}/{res.n_pairs}; {res.n_reasked} calls asked again")
        return res


def request_failed(rec: Mapping) -> bool:
    """The request itself failed (an API error after the SDK's retries): the model gave no answer."""
    resp = rec.get("response") or {}
    return resp.get("text") is None and bool(resp.get("error"))


def first_records(records: Iterable[Mapping]) -> dict[tuple, dict]:
    """The first record per (rubric, model, call, pass) that holds the model's answer: its first attempt
    at the format.  A failed request (:func:`request_failed`, e.g. an expired key) is not an attempt; a
    call with nothing but failed requests keeps its first record."""
    out: dict[tuple, dict] = {}
    for r in records:
        k = response_key(r)
        if k not in out or (request_failed(out[k]) and not request_failed(r)):
            out[k] = dict(r)
    return out


def first_attempt_parse(pair_set: PairSet, records: Iterable[Mapping], pass_no: int = 1
                        ) -> dict[tuple[str, str], dict]:
    """``{(rubric, model): {"ok", "total"}}`` for pass ``pass_no``: pairs whose answer parsed at the first
    attempt."""
    out: dict = defaultdict(lambda: {"ok": 0, "total": 0})
    for (rubric, model, _, p), rec in first_records(records).items():
        if p != pass_no:
            continue
        rows = reparse(rec)[0]
        out[(rubric, model)]["total"] += len(rec["listed"])
        out[(rubric, model)]["ok"] += len(rows)
    return {k: dict(v) for k, v in out.items()}


# --------------------------------------------------------------------------- answers

def collect_answers(pair_set: PairSet, records: Iterable[Mapping], pass_no: int = 1
                    ) -> dict[tuple[str, str], dict[str, dict]]:
    """``{(rubric, model): {pair_id: {"value", "reason", "reason_first", "error"}}}`` for pass ``pass_no``
    (default 1, "the" answer), from the final record per call (:func:`latest_records`), re-parsed with
    the current parser.  A row's id is read against the order its record was sent in (``listed``), so a
    later pass's reshuffled ids land on the right pair; a single-form record is its pair's (``pair_id``).
    Rubric D's answers add ``"wider"`` and ``"notes"``.  A pair whose call has no record is absent, a pair
    that failed to parse has ``value`` ``None`` and its ``error``."""
    latest = latest_records(records)
    by_call: dict[str, list] = defaultdict(list)
    by_id: dict[str, Pair] = {}
    for p in pair_set.pairs:
        by_call[p.call_id].append(p)
        by_id[p.pair_id] = p
    out: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for (rubric, model, call_id, p_no), rec in latest.items():
        if p_no != pass_no:
            continue
        rows, errors, _ = reparse(rec)
        if record_form(rec) == "single":
            mine = [by_id[pid]] if (pid := rec.get("pair_id") or call_id) in by_id else []
            id_of = {p.listed: 1 for p in mine}
        else:
            mine = by_call.get(call_id, [])
            id_of = {s: i for i, s in enumerate(rec["listed"], 1)}
        for p in mine:
            i = id_of.get(p.listed)
            row = rows.get(i) if i is not None else None
            if row is not None:
                a = {"value": row["value"], "reason": row["reason"], "reason_first": row.get("reason_first"),
                     "error": None}
                if "wider" in row:
                    a.update(wider=row["wider"], notes=list(row.get("notes") or []))
                out[(rubric, model)][p.pair_id] = a
            else:
                out[(rubric, model)][p.pair_id] = {"value": None, "reason": None, "reason_first": None,
                                                   "error": errors.get(i, "missing") if i is not None
                                                   else "not in the record's list"}
    return dict(out)


def results_rows(pair_set: PairSet, answers: Mapping, pass_no: int = 1,
                 subset: Optional[Iterable[str]] = None) -> list[dict]:
    """One row per (pair, rubric, model) of pass ``pass_no`` for ``results.jsonl``, with the answer on the
    decision scale beside it (``decision``); with ``subset`` (pair ids, round 2's confusion subset), each
    row says whether its pair is in it (``in_subset``; the other pairs of the calls sent are controls)."""
    keep = None if subset is None else set(subset)
    out = []
    for p in pair_set.pairs:
        for (rubric, model), ans in sorted(answers.items()):
            a = ans.get(p.pair_id)
            if a is None:
                continue
            row = {"pair_id": p.pair_id, "call_id": p.call_id, "target": p.target, "listed": p.listed,
                   "id": p.id, "group": p.group, "rubric": rubric, "rubric_name": RUBRICS[rubric]["name"],
                   "model": model, "pass": pass_no, **a, "decision": decision_value(rubric, a.get("value")),
                   "embedding_cos": p.embedding_cos, "persona_cos": p.persona_cos}
            if keep is not None:
                row["in_subset"] = p.pair_id in keep
            out.append(row)
    return out


# --------------------------------------------------------------------------- statistics

def weighted_kappa(a: Sequence[int], b: Sequence[int], *, k: int = 5, weights: str = "quadratic") -> Optional[float]:
    """Cohen's weighted kappa for two raters on the ordinal scale 0..k-1: 1 - sum(W O) / sum(W E), with
    ``O`` the observed and ``E`` the chance table (product of the margins) and ``W`` the disagreement
    weights, ``((i - j) / (k - 1))^2`` (quadratic) or ``|i - j| / (k - 1)`` (linear).  ``None`` with no
    pairs or when chance disagreement is zero (both raters gave one answer only)."""
    a, b = np.asarray(a, dtype=int), np.asarray(b, dtype=int)
    if len(a) == 0 or len(a) != len(b):
        return None
    O = np.zeros((k, k))
    np.add.at(O, (a, b), 1.0)
    O /= O.sum()
    E = np.outer(O.sum(axis=1), O.sum(axis=0))
    i, j = np.meshgrid(np.arange(k), np.arange(k), indexing="ij")
    W = ((i - j) / (k - 1)) ** 2 if weights == "quadratic" else np.abs(i - j) / (k - 1)
    den = float((W * E).sum())
    if den == 0:
        return None
    return float(1.0 - (W * O).sum() / den)


def _num_val(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _r(x, nd: int = 4):
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def _kind(v) -> str:
    return "numeric" if _num_val(v) else ("unparsed" if v is None else str(v))


def agreement(ref: Mapping[str, Mapping], other: Mapping[str, Mapping], *, k: int = 5) -> dict:
    """Agreement of ``other`` with ``ref`` over the pairs both answered: exact agreement over every
    answer (categories included), and on the pairs where both gave a number, exact, within one point,
    the mean difference (other - ref) and the weighted kappa (quadratic, and linear) on the scale
    ``0..k-1`` (5 points for rubric A's scale, 6 for C's and for D's relations as ranks); the categorical
    answers as a table ``{ref kind: {other kind: n}}`` (kinds: numeric, opposite, unsure, unparsed)."""
    common = sorted(set(ref) & set(other))
    both = [(ref[pid]["value"], other[pid]["value"]) for pid in common
            if ref[pid]["value"] is not None and other[pid]["value"] is not None]
    num = [(x, y) for x, y in both if _num_val(x) and _num_val(y)]
    table: dict = defaultdict(Counter)
    for pid in common:
        table[_kind(ref[pid]["value"])][_kind(other[pid]["value"])] += 1
    out = {"n_common": len(common), "n_both_parsed": len(both),
           "exact_all": _r(np.mean([x == y for x, y in both])) if both else None, "n_numeric": len(num)}
    if num:
        x = np.array([p[0] for p in num])
        y = np.array([p[1] for p in num])
        out.update(exact=_r(np.mean(x == y)), within_one=_r(np.mean(np.abs(x - y) <= 1)),
                   mean_diff=_r(np.mean(y - x)), kappa_quadratic=_r(weighted_kappa(x, y, k=k)),
                   kappa_linear=_r(weighted_kappa(x, y, k=k, weights="linear")))
    out["table"] = {kind: dict(v) for kind, v in sorted(table.items())}
    return out


def spearman(x: Sequence[float], y: Sequence[float]) -> tuple[Optional[float], Optional[float], int]:
    """``(rho, p, n)``; ``(None, None, n)`` below 5 pairs or with a constant side."""
    from scipy.stats import spearmanr
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    n = len(x)
    if n < 5 or np.all(x == x[0]) or np.all(y == y[0]):
        return None, None, n
    r = spearmanr(x, y)
    return float(r.statistic), float(r.pvalue), n


def bootstrap_rho(x: Sequence[float], y: Sequence[float], clusters: Sequence, *, n_boot: int = 2000,
                  seed: int = 0, x2: Optional[Sequence[float]] = None) -> Optional[dict]:
    """Percentile 95% interval for Spearman's rho of ``(x, y)`` (or, with ``x2``, for
    ``rho(x, y) - rho(x2, y)``, paired), resampling whole clusters (all the pairs of one target)."""
    from scipy.stats import spearmanr
    x, y = np.asarray(x, float), np.asarray(y, float)
    x2 = None if x2 is None else np.asarray(x2, float)
    cl = np.asarray(clusters)
    if len(x) < 5:
        return None
    _, inv = np.unique(cl, return_inverse=True)
    members = [np.where(inv == c)[0] for c in range(int(inv.max()) + 1)]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = np.concatenate([members[i] for i in rng.integers(0, len(members), size=len(members))])
        xs, ys = x[pick], y[pick]
        if np.all(xs == xs[0]) or np.all(ys == ys[0]):
            continue
        r = spearmanr(xs, ys).statistic
        if x2 is not None:
            x2s = x2[pick]
            if np.all(x2s == x2s[0]):
                continue
            r = r - spearmanr(x2s, ys).statistic
        if np.isfinite(r):
            vals.append(r)
    if len(vals) < n_boot // 2:
        return None
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return {"lo": _r(lo), "hi": _r(hi), "n_boot": len(vals)}


def is_antonym_pair(p: Pair) -> bool:
    """A recorded opposite: a clean pair, a labelled antonym, or a pair of the antonym group."""
    return p.recorded_pair or p.labelled_relation == "antonym" or p.group == "antonym" or "antonym" in p.also


POPULATIONS = {
    "all": lambda p: True,
    "non_antonym": lambda p: not is_antonym_pair(p),
    "nearest": lambda p: p.group == NEAREST,
    "nearest_non_antonym": lambda p: p.group == NEAREST and not is_antonym_pair(p),
}


def correlations(pairs: Sequence[Pair], ans: Mapping[str, Mapping], *, n_boot: int = 2000, seed: int = 0) -> dict:
    """Spearman of the numeric answers against the persona-space cosine and the embedding cosine, per
    population (:data:`POPULATIONS`), each with a 95% interval resampling targets."""
    out: dict = {}
    for what, attr in (("persona", "persona_cos"), ("embedding", "embedding_cos")):
        out[what] = {}
        for pop, keep in POPULATIONS.items():
            rows = [(ans[p.pair_id]["value"], getattr(p, attr), p.target) for p in pairs
                    if keep(p) and p.pair_id in ans and _num_val(ans[p.pair_id]["value"])
                    and getattr(p, attr) is not None]
            if not rows:
                out[what][pop] = {"rho": None, "p": None, "n": 0}
                continue
            v, c, t = zip(*rows)
            rho, pv, n = spearman(v, c)
            ci = bootstrap_rho(v, c, t, n_boot=n_boot, seed=seed) if rho is not None else None
            out[what][pop] = {"rho": _r(rho), "p": pv, "n": n, **(ci or {})}
    return out


def rubric_difference(pairs: Sequence[Pair], ans_a: Mapping, ans_b: Mapping, *, population: str = "non_antonym",
                      n_boot: int = 2000, seed: int = 0) -> dict:
    """rho(A, cosine) - rho(B, cosine) on the pairs of ``population`` where both rubrics gave a number,
    with a paired 95% interval resampling targets; for the persona and the embedding cosine."""
    keep = POPULATIONS[population]
    out = {}
    for what, attr in (("persona", "persona_cos"), ("embedding", "embedding_cos")):
        rows = [(ans_a[p.pair_id]["value"], ans_b[p.pair_id]["value"], getattr(p, attr), p.target) for p in pairs
                if keep(p) and p.pair_id in ans_a and p.pair_id in ans_b and getattr(p, attr) is not None
                and _num_val(ans_a[p.pair_id]["value"]) and _num_val(ans_b[p.pair_id]["value"])]
        if len(rows) < 5:
            out[what] = {"n": len(rows), "rho_a": None, "rho_b": None, "diff": None}
            continue
        a, b, c, t = (list(z) for z in zip(*rows))
        ra, _, n = spearman(a, c)
        rb, _, _ = spearman(b, c)
        diff = None if ra is None or rb is None else ra - rb
        ci = bootstrap_rho(a, c, t, n_boot=n_boot, seed=seed, x2=b) if diff is not None else None
        out[what] = {"n": n, "rho_a": _r(ra), "rho_b": _r(rb), "diff": _r(diff), **(ci or {})}
    return out


#: The order answers are counted in: every numeric answer (0-5), D's relations nearest first, the
#: categories, unparsed.
_VALUE_ORDER: list[str] = [str(s) for s in range(6)] + list(reversed(RELATIONS)) + ["opposite", "unsure", "unparsed"]


def value_counts(values: Iterable) -> dict:
    c = Counter("unparsed" if v is None else str(v) for v in values)
    return {k: c[k] for k in _VALUE_ORDER + sorted(set(c) - set(_VALUE_ORDER)) if c.get(k)}


def group_stats(pairs: Sequence[Pair], ans: Mapping[str, Mapping]) -> dict:
    """Per group: n, the answer counts, the mean of the numeric answers, the share at 3 or more, the
    opposite and unsure shares (of the answers that parsed)."""
    out = {}
    for g in GROUPS:
        vals = [ans[p.pair_id]["value"] for p in pairs if p.group == g and p.pair_id in ans]
        parsed = [v for v in vals if v is not None]
        num = [v for v in parsed if _num_val(v)]
        out[g] = {"n": len(vals), "n_parsed": len(parsed), "counts": value_counts(vals),
                  "mean": _r(np.mean(num), 2) if num else None,
                  "share_3_plus": _r(np.mean([v >= 3 for v in num]), 3) if num else None,
                  "opposite": _r(np.mean([v == "opposite" for v in parsed]), 3) if parsed else None,
                  "unsure": _r(np.mean([v == "unsure" for v in parsed]), 3) if parsed else None}
    return out


def rates(pairs: Sequence[Pair], ans: Mapping[str, Mapping]) -> dict:
    """Unsure and opposite shares overall, and the opposite share on recorded opposites (the antonym
    group, and nearest pairs that are recorded clean pairs) and on everything else."""
    vals = [ans[p.pair_id]["value"] for p in pairs if p.pair_id in ans and ans[p.pair_id]["value"] is not None]
    ant = [ans[p.pair_id]["value"] for p in pairs if p.group == "antonym" and p.pair_id in ans
           and ans[p.pair_id]["value"] is not None]
    nn_ant = [ans[p.pair_id]["value"] for p in pairs if p.group == NEAREST and is_antonym_pair(p)
              and p.pair_id in ans and ans[p.pair_id]["value"] is not None]
    rest = [ans[p.pair_id]["value"] for p in pairs if not is_antonym_pair(p) and p.pair_id in ans
            and ans[p.pair_id]["value"] is not None]
    share = lambda xs, v: _r(np.mean([x == v for x in xs]), 3) if xs else None  # noqa: E731
    return {"n": len(vals), "unsure": share(vals, "unsure"), "opposite": share(vals, "opposite"),
            "n_unsure": sum(v == "unsure" for v in vals), "n_opposite": sum(v == "opposite" for v in vals),
            "antonym_group": {"n": len(ant), "opposite": share(ant, "opposite"), "counts": value_counts(ant)},
            "nearest_recorded_opposites": {"n": len(nn_ant), "opposite": share(nn_ant, "opposite"),
                                           "counts": value_counts(nn_ant)},
            "not_recorded_opposites": {"n": len(rest), "opposite": share(rest, "opposite")}}


def answer_order(rubric: str) -> list[str]:
    """Every answer of ``rubric`` as text, for tables: its scale (or D's relations) low to high, then
    "opposite" and "unsure" (listed for every rubric, as the first tables did)."""
    order = [str(v) for v in native_ranks(rubric)]
    other = [c for c in RUBRICS[rubric]["categories"] if c not in order and c not in ("opposite", "unsure")]
    return order + other + ["opposite", "unsure"]


def by_score(pairs: Sequence[Pair], ans: Mapping[str, Mapping], order: Optional[Sequence[str]] = None) -> dict:
    """For each answer (in ``order``, default rubric A's): how many pairs, and their mean embedding and
    persona-space cosines (the calibration by-product of M3 item 7: the overlap score beside the angle)."""
    out = {}
    groups: dict[str, list] = defaultdict(list)
    for p in pairs:
        a = ans.get(p.pair_id)
        if a is not None and a["value"] is not None:
            groups[str(a["value"])].append(p)
    for k in (order or answer_order("A")):
        ps = groups.get(k, [])
        per = [p.persona_cos for p in ps if p.persona_cos is not None]
        out[k] = {"n": len(ps), "mean_embedding_cos": _r(np.mean([p.embedding_cos for p in ps]), 3) if ps else None,
                  "n_persona": len(per), "mean_persona_cos": _r(np.mean(per), 3) if per else None}
    return out


def divergence(pairs: Sequence[Pair], ans_a: Mapping, ans_b: Mapping, *, top: int = 10) -> dict:
    """Pairs where the rubrics differ most for one model: ``B - A`` over the pairs where both gave a number,
    largest first (B high and A low is the draft's case: correlated but distinct traits), and the counts
    of each difference."""
    rows = []
    for p in pairs:
        a, b = ans_a.get(p.pair_id), ans_b.get(p.pair_id)
        if a and b and _num_val(a["value"]) and _num_val(b["value"]):
            rows.append({"pair_id": p.pair_id, "target": p.target, "listed": p.listed, "group": p.group,
                         "a": a["value"], "b": b["value"], "diff": b["value"] - a["value"],
                         "reason_a": a["reason"], "reason_b": b["reason"], "embedding_cos": p.embedding_cos,
                         "persona_cos": p.persona_cos})
    rows.sort(key=lambda r: (-r["diff"], -r["b"], r["pair_id"]))
    hist = Counter(r["diff"] for r in rows)
    return {"n": len(rows), "diff_counts": {str(k): hist[k] for k in sorted(hist)},
            "mean_diff": _r(np.mean([r["diff"] for r in rows]), 3) if rows else None,
            "b_above_a": [r for r in rows if r["diff"] > 0][:top],
            "a_above_b": sorted([r for r in rows if r["diff"] < 0], key=lambda r: (r["diff"], -r["a"], r["pair_id"]))[:top]}


def context_consistency(pairs: Sequence[Pair], ans: Mapping[str, Mapping]) -> dict:
    """Unordered pairs judged in two calls (a nearest call and a labelled one, possibly with target and
    listed trait swapped): how often one model gave both the same answer."""
    by: dict[tuple, list] = defaultdict(list)
    for p in pairs:
        by[_ukey(p.target, p.listed)].append(p)
    same, n = 0, 0
    for ps in by.values():
        if len(ps) < 2:
            continue
        vals = [ans[p.pair_id]["value"] for p in ps if p.pair_id in ans and ans[p.pair_id]["value"] is not None]
        if len(vals) >= 2:
            n += 1
            same += int(len(set(map(str, vals))) == 1)
    return {"n": n, "same": same, "share_same": _r(same / n, 3) if n else None}


def opus_on_disagreement(ans_h: Mapping, ans_s: Mapping, ans_o: Mapping) -> dict:
    """As in the Opus audit of M1: where Haiku and Sonnet give the same answer, how often Opus does too;
    where they differ, whose side Opus takes."""
    agree = differ = o_agree = o_h = o_s = o_neither = 0
    for k in set(ans_h) & set(ans_s) & set(ans_o):
        h, s, o = ans_h[k]["value"], ans_s[k]["value"], ans_o[k]["value"]
        if h is None or s is None or o is None:
            continue
        if h == s:
            agree += 1
            o_agree += int(o == h)
        else:
            differ += 1
            o_h += int(o == h)
            o_s += int(o == s)
            o_neither += int(o != h and o != s)
    return {"haiku_sonnet_same": agree, "opus_same_as_both": o_agree,
            "opus_same_share": _r(o_agree / agree, 3) if agree else None, "haiku_sonnet_differ": differ,
            "opus_sides_haiku": o_h, "opus_sides_sonnet": o_s, "opus_neither": o_neither}


def parse_rates(pair_set: PairSet, answers: Mapping) -> dict:
    return {f"{r}|{m}": {"ok": sum(a["value"] is not None for a in ans.values()), "total": len(ans),
                         "rate": _r(sum(a["value"] is not None for a in ans.values()) / len(ans)) if ans else None}
            for (r, m), ans in sorted(answers.items())}


def analyse(pair_set: PairSet, answers: Mapping[tuple[str, str], Mapping], *, models: Sequence[str] = MODELS,
            reference: str = REFERENCE, n_boot: int = 2000, seed: int = 0,
            first_parse: Optional[Mapping[tuple[str, str], Mapping]] = None) -> dict:
    """Everything the readout reports, as one JSON-ready dict, for the rubrics ``answers`` holds (one pass:
    the CLI passes pass 1's).  ``first_parse`` (:func:`first_attempt_parse`) adds the parse rate at the
    first attempt.  Scales: agreement and the correlations read each rubric's native scale as numbers (C
    0-5, D's relations as ranks 0-5: :func:`ordinal_value`); the known groups read the decision scale
    (:func:`decision_value`; the same as the native one for A, B and E); the answer counts, the rates and
    the cosines by answer read the native answers."""
    pairs = pair_set.pairs
    get = lambda r, m: answers.get((r, m), {})  # noqa: E731
    run_rubrics = [r for r in RUBRICS if any(get(r, m) for m in models)]
    out: dict = {"n_pairs": len(pairs), "n_calls": len(pair_set.calls), "models": list(models),
                 "reference": reference, "parse": parse_rates(pair_set, answers), "agreement": {},
                 "correlation": {}, "rubric_difference": {}, "groups": {}, "rates": {}, "by_score": {},
                 "divergence": {}, "context_consistency": {}, "opus_on_disagreement": {},
                 "parse_first_attempt": {f"{r}|{m}": {**v, "rate": _r(v["ok"] / v["total"]) if v["total"] else None}
                                         for (r, m), v in sorted((first_parse or {}).items())},
                 "parser_version": PARSER_VERSION,
                 "scales": {r: {"native": native_order(r), "k": native_k(r), "decision": RUBRICS[r].get("decision")}
                            for r in run_rubrics},
                 "reason_first_share": {}, "bootstrap": {"n_boot": n_boot, "seed": seed,
                                                         "unit": "target (all the pairs of one call's target)"}}
    for r in run_rubrics:
        k = native_k(r)
        out["agreement"][r] = {m: agreement(to_ordinal(r, get(r, reference)), to_ordinal(r, get(r, m)), k=k)
                               for m in models if m != reference and get(r, m) and get(r, reference)}
        out["correlation"][r] = {m: correlations(pairs, to_ordinal(r, get(r, m)), n_boot=n_boot, seed=seed)
                                 for m in models if get(r, m)}
        out["groups"][r] = {m: group_stats(pairs, to_decision(r, get(r, m))) for m in models if get(r, m)}
        out["rates"][r] = {m: rates(pairs, get(r, m)) for m in models if get(r, m)}
        out["by_score"][r] = {m: by_score(pairs, get(r, m), order=answer_order(r)) for m in models if get(r, m)}
        out["context_consistency"][r] = {m: context_consistency(pairs, get(r, m)) for m in models if get(r, m)}
        out["reason_first_share"][r] = {m: _r(np.mean([a["reason_first"] for a in get(r, m).values()
                                                       if a.get("reason_first") is not None]), 3)
                                        for m in models if any(a.get("reason_first") is not None
                                                               for a in get(r, m).values())}
        if all(get(r, m) for m in (HAIKU, SONNET, OPUS)):
            out["opus_on_disagreement"][r] = opus_on_disagreement(get(r, HAIKU), get(r, SONNET), get(r, OPUS))
    for m in models:
        if get("A", m) and get("B", m):
            out["rubric_difference"][m] = {pop: rubric_difference(pairs, get("A", m), get("B", m), population=pop,
                                                                  n_boot=n_boot, seed=seed)
                                           for pop in ("non_antonym", "nearest_non_antonym")}
            out["divergence"][m] = divergence(pairs, get("A", m), get("B", m))
    return out


# --------------------------------------------------------------------------- the arms experiment

def side(value: Any, cutoff: int = CUTOFF) -> Optional[bool]:
    """Which side of ``cutoff`` a decision-scale answer falls on: True covered (a number at or above
    it), False not covered (a number below it, or "opposite"), None neither ("unsure", unparsed)."""
    if _num_val(value):
        return value >= cutoff
    if value == "opposite":
        return False
    return None


def flip_counts(first: Mapping[str, Mapping], second: Mapping[str, Mapping], order: Sequence[str], *,
                n_scale: int) -> dict:
    """The pairs both answered, with different answers, counted by the two answers they lie between
    (``"2/3"``: one said 2, the other 3; the one earlier in ``order`` first).  ``adjacent``: flips between
    neighbouring points of the scale (the first ``n_scale`` entries of ``order``), the boundary each such
    flip crosses."""
    pos = {v: i for i, v in enumerate(order)}
    rank = lambda v: (pos.get(v, len(pos)), v)  # noqa: E731
    c: Counter = Counter()
    adjacent = 0
    for pid in set(first) & set(second):
        a, b = first[pid].get("value"), second[pid].get("value")
        if a is None or b is None or str(a) == str(b):
            continue
        x, y = sorted((str(a), str(b)), key=rank)
        c[f"{x}/{y}"] += 1
        adjacent += int(pos.get(x, n_scale) < n_scale and pos.get(y, n_scale) < n_scale and pos[y] - pos[x] == 1)
    keys = sorted(c, key=lambda k: (rank(k.split("/")[0]), rank(k.split("/")[1])))
    return {"n": sum(c.values()), "adjacent": adjacent, "by_pair": {k: c[k] for k in keys}}


def cutoff_crossings(pairs: Sequence[Pair], rubric: str, first: Mapping[str, Mapping], second: Mapping[str, Mapping],
                     *, cutoff: int = CUTOFF, nearest_only: bool = True) -> dict:
    """On the nearest pairs (every pair of ``pairs`` with ``nearest_only`` False, as round 2 counts its
    populations) both answered on a side of ``cutoff`` (decision scale, :func:`side`): how many fall on
    different sides, split by which one is covered, and the pairs themselves with both native answers and
    both reasons."""
    n = first_only = second_only = 0
    rows = []
    for p in pairs:
        if (nearest_only and p.group != NEAREST) or p.pair_id not in first or p.pair_id not in second:
            continue
        a, b = first[p.pair_id].get("value"), second[p.pair_id].get("value")
        sa, sb = side(decision_value(rubric, a), cutoff), side(decision_value(rubric, b), cutoff)
        if sa is None or sb is None:
            continue
        n += 1
        if sa != sb:
            first_only += int(sa)
            second_only += int(sb)
            rows.append({"pair_id": p.pair_id, "target": p.target, "listed": p.listed, "group": p.group,
                         "first": a, "second": b, "first_reason": first[p.pair_id].get("reason"),
                         "second_reason": second[p.pair_id].get("reason")})
    return {"n": n, "crossings": first_only + second_only, "first_only": first_only, "second_only": second_only,
            "pairs": rows}


def compare_answers(rubric: str, first: Mapping[str, Mapping], second: Mapping[str, Mapping], pairs: Sequence[Pair],
                    *, cutoff: int = CUTOFF, nearest_only: bool = True) -> dict:
    """Two sets of answers under ``rubric`` to the same pairs (one model's two passes; two models in one
    pass; a pass and an earlier run), ``first`` the reference: :func:`agreement` on the native scale (D's
    relations as ranks) and on the decision scale (``mean_diff`` is second minus first); the
    disagreements by the pair of answers they lie between, native and decision (:func:`flip_counts`);
    and on the nearest pairs (every pair of ``pairs``, with ``nearest_only`` False), those that fall on
    different sides of ``cutoff`` (:func:`cutoff_crossings`)."""
    k = native_k(rubric)
    d1, d2 = to_decision(rubric, first), to_decision(rubric, second)
    return {"native": agreement(to_ordinal(rubric, first), to_ordinal(rubric, second), k=k),
            "decision": agreement(d1, d2, k=len(SCALE)),
            "flips_native": flip_counts(first, second, native_order(rubric), n_scale=k),
            "flips_decision": flip_counts(d1, d2, DECISION_ORDER, n_scale=len(SCALE)),
            "cutoff": cutoff_crossings(pairs, rubric, first, second, cutoff=cutoff, nearest_only=nearest_only)}


def coverage(pairs: Sequence[Pair], rubric: str, answers: Mapping[str, Mapping], *, cutoff: int = CUTOFF,
             nearest_only: bool = True) -> dict:
    """The nearest pairs (every pair of ``pairs``, with ``nearest_only`` False) at or above ``cutoff`` on
    the decision scale, over those answered (an M3 candidate sitting where the target sits would be called
    covered by that neighbour), and the targets with at least one such neighbour."""
    by_call: dict[str, list] = defaultdict(list)
    vals = []
    for p in pairs:
        a = answers.get(p.pair_id)
        if (nearest_only and p.group != NEAREST) or a is None or a.get("value") is None:
            continue
        v = decision_value(rubric, a["value"])
        vals.append(v)
        by_call[p.call_id].append(side(v, cutoff) is True)
    n, cov = len(vals), sum(side(v, cutoff) is True for v in vals)
    hit = sum(any(x) for x in by_call.values())
    return {"n": n, "covered": cov, "share": _r(cov / n, 3) if n else None, "n_targets": len(by_call),
            "targets_covered": hit, "target_share": _r(hit / len(by_call), 3) if by_call else None,
            "opposite": sum(v == "opposite" for v in vals), "unsure": sum(v == "unsure" for v in vals)}


def relation_stats(answers: Mapping[str, Mapping]) -> dict:
    """Rubric D: how often each relation was named; for "contains", which side was named the wider and
    how often ``wider`` was missing or unusable; ``wider`` given with another relation; alias spellings."""
    vals = [a.get("value") for a in answers.values()]
    contains = [a for a in answers.values() if a.get("value") == "contains"]
    missing = sum("contains without wider" in (a.get("notes") or []) for a in contains)
    notes = [n for a in answers.values() for n in (a.get("notes") or [])]
    wider = {"target": sum(a.get("wider") == "target" for a in contains),
             "listed": sum(a.get("wider") == "listed" for a in contains), "missing": missing,
             "invalid": sum(a.get("wider") is None for a in contains) - missing}
    return {"n": len(vals), "counts": value_counts(vals), "n_contains": len(contains), "wider": wider,
            "wider_missing_share": _r((wider["missing"] + wider["invalid"]) / len(contains), 3) if contains else None,
            "wider_with_other_relation": sum(" given with " in n for n in notes),
            "alias_spellings": sum(" read as " in n for n in notes)}


def wider_agreement(first: Mapping[str, Mapping], second: Mapping[str, Mapping]) -> dict:
    """On the pairs both answered "contains": the same side named the wider, a different side, or one of
    the two without a usable ``wider``."""
    both = [(first[k].get("wider"), second[k].get("wider")) for k in set(first) & set(second)
            if first[k].get("value") == "contains" and second[k].get("value") == "contains"]
    known = [(a, b) for a, b in both if a and b]
    return {"n_both_contains": len(both), "same": sum(a == b for a, b in known),
            "different": sum(a != b for a, b in known), "unknown": len(both) - len(known)}


#: What a reason names, for rubric E's 3s (a word search, case-insensitive; a reason may name several).
SCOPE_KINDS: dict[str, str] = {
    "narrowed": r"\bnarrow",
    "broadened": r"\bbroad(en|ened|ening|ens|er)\b|\bwiden",
    "stronger": r"\bstronger\b|\bstrengthen|\bintensif|\bmore intense\b|\bmore extreme\b|\bcarried further\b",
    "milder": r"\bmilder\b|\bweaker\b|\bsofter\b|\bgentler\b|\bless intense\b|\btoned[- ]down\b",
    "emphasis": r"\bemphas|\bstress",
}


def scope_kinds(answers: Mapping[str, Mapping], *, value: Any = 3) -> dict:
    """For the answers equal to ``value`` (rubric E's 3, whose line asks the reason to say which kind of
    difference): how many reasons name each kind (:data:`SCOPE_KINDS`), how many name none, how many
    more than one."""
    rows = [a for a in answers.values() if a.get("value") == value and a.get("reason")]
    kinds = {k: 0 for k in SCOPE_KINDS}
    none = multiple = 0
    for a in rows:
        hit = [k for k, pat in SCOPE_KINDS.items() if re.search(pat, a["reason"], re.I)]
        for k in hit:
            kinds[k] += 1
        none += int(not hit)
        multiple += int(len(hit) > 1)
    return {"n": len(rows), "kinds": kinds, "none": none, "none_share": _r(none / len(rows), 3) if rows else None,
            "multiple": multiple}


#: How a pair's call was sent in a later pass, against pass 1: a call of one trait (necessarily the same
#: prompt), a longer call whose order happened to come out the same (the same prompt), or a reordered one.
PROMPT_GROUPS: tuple[str, ...] = ("single", "same_order", "reordered")


def prompt_groups(pair_set: PairSet, seed: int, pass_no: int) -> dict[str, str]:
    """``{pair_id: group}`` (:data:`PROMPT_GROUPS`): whether the pair's call was sent in pass ``pass_no``
    with the same user turn as in pass 1, and why."""
    out = {}
    for c in pair_set.calls:
        same = listed_order(c, pass_order_seed(seed, pass_no, c.call_id)) == list(c.listed)
        group = "single" if len(c.listed) == 1 else ("same_order" if same else "reordered")
        for s in c.listed:
            out[f"{c.call_id}>{s}"] = group
    return out


def consistency_by_prompt(rubric: str, first: Mapping[str, Mapping], second: Mapping[str, Mapping],
                          groups: Mapping[str, str]) -> dict:
    """Exact agreement between two sets of answers (native and decision scale) on each group of
    :func:`prompt_groups`: does a reordered prompt change the answer more than the same prompt asked
    again?"""
    out = {}
    for g in PROMPT_GROUPS:
        f = {k: v for k, v in first.items() if groups.get(k) == g}
        s = {k: v for k, v in second.items() if groups.get(k) == g}
        nat = agreement(to_ordinal(rubric, f), to_ordinal(rubric, s), k=native_k(rubric))
        dec = agreement(to_decision(rubric, f), to_decision(rubric, s), k=len(SCALE))
        out[g] = {"n": nat["n_both_parsed"], "exact_native": nat["exact_all"], "exact_decision": dec["exact_all"]}
    return out


def order_stats(pair_set: PairSet, seed: int, passes: Sequence[int]) -> dict:
    """For each later pass: the calls whose listed traits happened to be sent in pass 1's order (every
    call of one trait does), and the pairs sent under another id than in pass 1."""
    out = {}
    for p in passes:
        if int(p) == 1:
            continue
        same = single = moved = 0
        for c in pair_set.calls:
            order = listed_order(c, pass_order_seed(seed, p, c.call_id))
            if order == list(c.listed):
                same += 1
                single += int(len(c.listed) == 1)
            moved += sum(s != c.listed[i] for i, s in enumerate(order))
        out[str(p)] = {"n_calls": len(pair_set.calls), "same_order": same, "same_order_single": single,
                       "n_pairs": len(pair_set.pairs), "pairs_moved": moved}
    return out


def analyse_arms(pair_set: PairSet, answers_by_pass: Mapping[int, Mapping[tuple[str, str], Mapping]], *,
                 models: Sequence[str], reference: str = REFERENCE, seed: int = 0, cutoff: int = CUTOFF,
                 first_parse_by_pass: Optional[Mapping[int, Mapping]] = None,
                 baseline: Optional[Mapping] = None, forms: Optional[Mapping[str, str]] = None) -> dict:
    """The arms experiment's comparisons (coding_plan_overlap_arms.md, "What to build" 3), per rubric
    and model, over the passes in ``answers_by_pass`` (``{pass: collect_answers(...)}``):

    * ``self_consistency``: pass 1 against pass 2 (:func:`compare_answers`);
    * ``between_models``: each model against ``reference`` in each pass;
    * ``coverage``: the nearest pairs at or above ``cutoff`` on the decision scale, per pass;
    * D: ``relations`` (:func:`relation_stats`) and ``wider`` agreement between passes and models; E (and
      A, unasked, as a control): ``scope_kinds`` on the 3s;
    * ``baseline``: arm A's pass 1 against an earlier run's rubric-A answers on the same pairs
      (``{"run_id", "answers": {model: {pair_id: answer}}}``), as a pass-to-pass comparison;
    * ``parse`` per pass and ``order`` (how pass 2's order differs from pass 1's, for the list form);
    * ``cross_arm``: one row per (rubric, model) for the summary table.

    ``forms`` (``{rubric: form}``, default every rubric a list): a single-form rubric's pass 2 sent the
    identical prompts, so all of its pairs count as one-trait calls in ``by_prompt``.  Pass keys are strings
    ("1", "2")."""
    pairs = pair_set.pairs
    passes = sorted(int(p) for p in answers_by_pass)
    get = lambda p, r, m: answers_by_pass.get(p, {}).get((r, m), {})  # noqa: E731
    rubrics = [r for r in RUBRICS if any(get(p, r, m) for p in passes for m in models)]
    others = [m for m in models if m != reference]
    forms = {r: (forms or {}).get(r, "list") for r in rubrics}
    out: dict = {"passes": passes, "cutoff": cutoff, "rubrics": rubrics, "models": list(models), "reference": reference,
                 "decision_scale": {r: RUBRICS[r].get("decision") for r in rubrics}, "forms": forms,
                 "order": order_stats(pair_set, seed, passes) if "list" in forms.values() else {}, "parse": {},
                 "per_arm": {}, "baseline": None, "scope_kind_patterns": dict(SCOPE_KINDS)}
    for p in passes:
        fp = (first_parse_by_pass or {}).get(p, {})
        for (r, m), ans in sorted(answers_by_pass[p].items()):
            f = fp.get((r, m))
            out["parse"][f"{r}|{m}|{p}"] = {"rubric": r, "model": m, "pass": p,
                                            "ok": sum(a["value"] is not None for a in ans.values()), "total": len(ans),
                                            "first_ok": f["ok"] if f else None, "first_total": f["total"] if f else None}
    list_groups = prompt_groups(pair_set, seed, passes[1]) if len(passes) >= 2 else {}
    single_groups = {p.pair_id: "single" for p in pairs}
    for r in rubrics:
        groups = single_groups if forms[r] == "single" else list_groups
        arm: dict = {"self_consistency": {}, "between_models": {}, "coverage": {}}
        for m in models:
            if len(passes) >= 2 and get(passes[0], r, m) and get(passes[1], r, m):
                arm["self_consistency"][m] = compare_answers(r, get(passes[0], r, m), get(passes[1], r, m), pairs,
                                                             cutoff=cutoff)
                arm["self_consistency"][m]["by_prompt"] = consistency_by_prompt(r, get(passes[0], r, m),
                                                                                get(passes[1], r, m), groups)
            arm["coverage"][m] = {str(p): coverage(pairs, r, get(p, r, m), cutoff=cutoff) for p in passes
                                  if get(p, r, m)}
        for m in others:
            arm["between_models"][m] = {str(p): compare_answers(r, get(p, r, reference), get(p, r, m), pairs,
                                                                cutoff=cutoff)
                                        for p in passes if get(p, r, reference) and get(p, r, m)}
        if has_wider(r):
            arm["relations"] = {m: {str(p): relation_stats(get(p, r, m)) for p in passes if get(p, r, m)}
                                for m in models}
            arm["wider_between_passes"] = {m: wider_agreement(get(passes[0], r, m), get(passes[1], r, m))
                                           for m in models if len(passes) >= 2 and get(passes[1], r, m)}
            arm["wider_between_models"] = {m: {str(p): wider_agreement(get(p, r, reference), get(p, r, m))
                                               for p in passes if get(p, r, reference) and get(p, r, m)}
                                           for m in others}
        if RUBRICS[r].get("kinds"):
            arm["scope_kinds"] = {m: {str(p): scope_kinds(get(p, r, m)) for p in passes if get(p, r, m)}
                                  for m in models}
        out["per_arm"][r] = arm
    if baseline:
        b = {"run_id": baseline.get("run_id"), "rubric": "A", "per_model": {}}
        for m in models:
            ours, theirs = get(1, "A", m), (baseline.get("answers") or {}).get(m)
            if ours and theirs:
                b["per_model"][m] = compare_answers("A", theirs, ours, pairs, cutoff=cutoff)
        out["baseline"] = b
    out["cross_arm"] = cross_arm_rows(out)
    return out


def cross_arm_rows(arms: Mapping) -> list[dict]:
    """One row per (rubric, model) of :func:`analyse_arms`: self-consistency (exact, native and decision
    scale) and the flips across the cut-off between the passes; agreement with the other model in each
    pass (for the reference model, with the one other model when there is exactly one); the covered
    share per pass; the crossings between the models per pass."""
    rows = []
    ref = arms["reference"]
    for r in arms["rubrics"]:
        arm = arms["per_arm"][r]
        others = [m for m, v in arm["between_models"].items() if v]
        for m in arms["models"]:
            partner = m if m != ref else (others[0] if len(others) == 1 else None)
            bm = arm["between_models"].get(partner, {}) if partner else {}
            sc = arm["self_consistency"].get(m)
            cov = arm["coverage"].get(m, {})
            if not sc and not cov:
                continue
            rows.append({"arm": r, "model": m, "versus": partner,
                         "n_both_passes": sc["native"]["n_both_parsed"] if sc else None,
                         "consistency_native": sc["native"]["exact_all"] if sc else None,
                         "consistency_decision": sc["decision"]["exact_all"] if sc else None,
                         "pass_flips_at_cutoff": sc["cutoff"]["crossings"] if sc else None,
                         "pass_flips_n": sc["cutoff"]["n"] if sc else None,
                         "agreement_native": {p: x["native"]["exact_all"] for p, x in bm.items()},
                         "agreement_decision": {p: x["decision"]["exact_all"] for p, x in bm.items()},
                         "crossings": {p: x["cutoff"]["crossings"] for p, x in bm.items()},
                         "crossings_n": {p: x["cutoff"]["n"] for p, x in bm.items()},
                         "covered": {p: {k: c[k] for k in ("covered", "n", "share", "targets_covered", "n_targets")}
                                     for p, c in cov.items()}})
    return rows


# --------------------------------------------------------------------------- the arms experiment, round 2

#: How round 1's analysis read a reason (``coding_plan_overlap_arms.md``, "Round 2", "The subset"), both
#: case-insensitive: as describing a containment, and as describing a two-sided overlap.
CONTAINMENT_PATTERN = (r"narrow|broader|broadened|\bwider\b|\bpart of\b|subset|\bincludes?\b"
                       r"|specific (case|form|kind|instance)|special case|restricted to|limited to"
                       r"|carried (further|beyond)|stronger (form|degree|version)|a (form|kind|type|case) of")
TWO_SIDED_PATTERN = (r"(each|both)\s+(add|bring|contribut|has something|lacks)"
                     r"|adds?\b[^.;]*\b(while|whereas|and)\b[^.;]*\b(adds?|stresses|brings|emphasi)")
CONTAINMENT_RE = re.compile(CONTAINMENT_PATTERN, re.I)
TWO_SIDED_RE = re.compile(TWO_SIDED_PATTERN, re.I)


def describes_containment(reason: Optional[str]) -> bool:
    """The reason matches the containment pattern and not the two-sided one.  An answer at 2 (2,
    "overlap") with such a reason is round 1's self-contradiction."""
    return bool(reason) and bool(CONTAINMENT_RE.search(reason)) and not TWO_SIDED_RE.search(reason)


def describes_two_sided(reason: Optional[str]) -> bool:
    """The reason matches the two-sided pattern (each trait adds something).  An answer at 3 with such a
    reason is the reverse slip."""
    return bool(reason) and bool(TWO_SIDED_RE.search(reason))


#: The runs whose readings define the confusion subset (``coding_plan_overlap_arms.md``, "Round 2"): round 1
#: of the arms (A, C, D and E; Sonnet and Opus; two passes), overlap_test_1 (rubric A on its four models) and
#: overlap_test_2 (rubric A, draft 3).  Rubric B never counts: its 0-4 is co-occurrence, not similarity.
SUBSET_SOURCES: tuple[str, ...] = ("overlap_arms_1", "overlap_test_1", "overlap_test_2")
SUBSET_SKIP_RUBRICS: tuple[str, ...] = ("B",)
SUBSET_RULE = ("A pair (by pair_id of the round-1 pair set) is in the subset if, over every reading of it on record "
               "(every answer that parsed, under every rubric but B, of every model and pass of the source runs, "
               "mapped to the decision scale), either (1) its readings include both a 2 and a 3, or (2) some reading "
               "is a 2 (or \"overlap\") whose reason matches the containment pattern and not the two-sided pattern.  "
               "The run sends the calls that hold a subset pair whole, as round 1 built them; their other pairs "
               "are controls.")


def pair_readings(pair_set: PairSet, records_by_run: Mapping[str, Iterable[Mapping]], *,
                  skip: Sequence[str] = SUBSET_SKIP_RUBRICS) -> tuple[dict[str, list[dict]], list[dict]]:
    """Every reading on record of every pair: ``({pair_id: [{"run", "rubric", "model", "pass", "value",
    "decision", "reason"}, ...]}, sources)``, from each run's final answer per (rubric, model, call, pass)
    (:func:`collect_answers`, re-parsed), every rubric but ``skip``, answers that did not parse left out.
    ``sources``: one row per (run, rubric, model, pass) with the rubric versions its records carry and how
    many readings it gave."""
    readings: dict[str, list[dict]] = defaultdict(list)
    sources: list[dict] = []
    for run, records in records_by_run.items():
        records = list(records)
        versions: dict[tuple, set] = defaultdict(set)
        for rec in records:
            versions[(rec["rubric"], rec["model"], record_pass(rec))].add(rec.get("rubric_version"))
        for p in record_passes(records):
            for (r, m), ans in sorted(collect_answers(pair_set, records, pass_no=p).items()):
                if r in skip:
                    continue
                n = unparsed = 0
                for pid, a in ans.items():
                    if a.get("value") is None:
                        unparsed += 1
                        continue
                    n += 1
                    readings[pid].append({"run": run, "rubric": r, "model": m, "pass": p, "value": a["value"],
                                          "decision": decision_value(r, a["value"]), "reason": a.get("reason")})
                sources.append({"run": run, "rubric": r, "rubric_name": RUBRICS[r]["name"],
                                "rubric_versions": sorted(v for v in versions[(r, m, p)] if v is not None),
                                "model": m, "pass": p, "n_readings": n, "n_unparsed": unparsed})
    return dict(readings), sources


def confusion_subset(pair_set: PairSet, readings: Mapping[str, Sequence[Mapping]]) -> dict:
    """Round 2's confusion subset (:data:`SUBSET_RULE`) from :func:`pair_readings`: ``pair_ids`` (pair-set
    order), the calls that hold them (``call_ids``, pair-set order), the other pairs of those calls
    (``control_pair_ids``), the counts (``rule_1``, ``rule_2``, ``rule_2_only``, calls, controls, by group),
    and per subset pair its ``evidence``: the rules it meets, the decision values among its readings and
    the readings that are slips, with their reasons."""
    rule1: set = set()
    rule2: set = set()
    evidence: dict[str, dict] = {}
    for p in pair_set.pairs:
        rs = list(readings.get(p.pair_id, []))
        decisions = Counter(str(x["decision"]) for x in rs)
        both = {2, 3} <= {x["decision"] for x in rs if _num_val(x["decision"])}
        slips = [x for x in rs if _num_val(x["decision"]) and x["decision"] == 2 and describes_containment(x["reason"])]
        if both:
            rule1.add(p.pair_id)
        if slips:
            rule2.add(p.pair_id)
        if both or slips:
            evidence[p.pair_id] = {"rules": [k for k, ok in ((1, both), (2, bool(slips))) if ok],
                                   "n_readings": len(rs),
                                   "decisions": {k: decisions[k] for k in DECISION_ORDER if decisions.get(k)},
                                   "slips": [{k: x[k] for k in ("run", "rubric", "model", "pass", "value", "reason")}
                                             for x in slips]}
    chosen = rule1 | rule2
    pair_ids = [p.pair_id for p in pair_set.pairs if p.pair_id in chosen]
    held = {p.call_id for p in pair_set.pairs if p.pair_id in chosen}
    call_ids = [c.call_id for c in pair_set.calls if c.call_id in held]
    controls = [p.pair_id for p in pair_set.pairs if p.call_id in held and p.pair_id not in chosen]
    group = {p.pair_id: p.group for p in pair_set.pairs}
    per_pair = Counter(len(readings.get(p.pair_id, [])) for p in pair_set.pairs)
    counts = {"n_pairs": len(pair_ids), "rule_1": len(rule1), "rule_2": len(rule2), "rule_2_only": len(rule2 - rule1),
              "both_rules": len(rule1 & rule2), "n_calls": len(call_ids), "n_pairs_sent": len(pair_ids) + len(controls),
              "n_controls": len(controls), "of_calls": len(pair_set.calls), "of_pairs": len(pair_set.pairs),
              "by_group": dict(Counter(group[x] for x in pair_ids)),
              "controls_by_group": dict(Counter(group[x] for x in controls)),
              "readings_per_pair": {str(k): per_pair[k] for k in sorted(per_pair)}}
    return {"rule": SUBSET_RULE, "patterns": {"containment": CONTAINMENT_PATTERN, "two_sided": TWO_SIDED_PATTERN,
                                              "flags": "IGNORECASE"},
            "counts": counts, "call_ids": call_ids, "pair_ids": pair_ids, "control_pair_ids": controls,
            "evidence": evidence}


def load_subset(path: Path) -> dict:
    """A ``subset.json`` (:func:`confusion_subset`, in its provenance envelope or bare).  It must name its
    calls (``call_ids``); ``pair_ids`` and ``control_pair_ids`` default to empty."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d) if isinstance(d, dict) else d
    if not isinstance(d, dict) or not isinstance(d.get("call_ids"), list) or not d["call_ids"]:
        raise ValueError(f"{path}: no call_ids")
    return {**d, "pair_ids": list(d.get("pair_ids") or []), "control_pair_ids": list(d.get("control_pair_ids") or [])}


def contradictions(rubric: str, answers: Iterable[Mapping]) -> dict:
    """Round 1's self-contradictions in a set of answers (one model's, one pass or several): ``forward``,
    the answers at 2 on the decision scale (2, "overlap") whose reason describes a containment
    (:func:`describes_containment`); ``reverse``, the answers at 3 (3, "contains", and C's 4 and D's
    "variant", which map to 3) whose reason describes a two-sided overlap (:func:`describes_two_sided`),
    also split by native answer.  Counts, and shares of the answers at 2 and at 3."""
    twos, threes = [], []
    for a in answers:
        d = decision_value(rubric, a.get("value"))
        if _num_val(d) and d == 2:
            twos.append(a)
        elif _num_val(d) and d == 3:
            threes.append(a)
    fwd = sum(describes_containment(a.get("reason")) for a in twos)
    by_native: dict[str, dict] = {}
    for a in threes:
        x = by_native.setdefault(str(a["value"]), {"n": 0, "reverse": 0})
        x["n"] += 1
        x["reverse"] += int(describes_two_sided(a.get("reason")))
    rev = sum(x["reverse"] for x in by_native.values())
    return {"n_2": len(twos), "forward": fwd, "forward_share": _r(fwd / len(twos), 3) if twos else None,
            "n_3": len(threes), "reverse": rev, "reverse_share": _r(rev / len(threes), 3) if threes else None,
            "reverse_by_native": {k: by_native[k] for k in native_order(rubric) if k in by_native}}


def population_stats(pair_set: PairSet, rubric: str, by_pass: Mapping[int, Mapping[tuple[str, str], Mapping]],
                     pair_ids: Iterable[str], *, models: Sequence[str], reference: str = REFERENCE,
                     cutoff: int = CUTOFF) -> dict:
    """Round 1's statistics for one rubric's answers (``by_pass``: ``{pass: collect_answers(...)}``) on the
    pairs ``pair_ids`` only, every group counted (round 2's populations): self-consistency between the
    first two passes and each model against ``reference`` in each pass (:func:`compare_answers`, its
    crossings and flips at ``cutoff`` over every pair of the population), the share at ``cutoff`` or more
    per pass (:func:`coverage`), the self-contradictions per pass and pooled over the passes
    (:func:`contradictions`); for a rubric with ``wider``, the relations named and the ``wider``
    agreement between passes and models."""
    ids = set(pair_ids)
    pairs = [p for p in pair_set.pairs if p.pair_id in ids]
    passes = sorted(int(p) for p in by_pass)
    others = [m for m in models if m != reference]

    def get(p: int, m: str) -> dict:
        return {k: v for k, v in (by_pass.get(p) or {}).get((rubric, m), {}).items() if k in ids}

    out: dict = {"rubric": rubric, "n_pairs": len(pairs), "self_consistency": {}, "between_models": {},
                 "coverage": {}, "contradictions": {}}
    for m in models:
        if len(passes) >= 2 and get(passes[0], m) and get(passes[1], m):
            out["self_consistency"][m] = compare_answers(rubric, get(passes[0], m), get(passes[1], m), pairs,
                                                         cutoff=cutoff, nearest_only=False)
        cov = {str(p): coverage(pairs, rubric, get(p, m), cutoff=cutoff, nearest_only=False) for p in passes if get(p, m)}
        if cov:
            out["coverage"][m] = cov
        per = {str(p): contradictions(rubric, get(p, m).values()) for p in passes if get(p, m)}
        if per:
            per["pooled"] = contradictions(rubric, [a for p in passes for a in get(p, m).values()])
            out["contradictions"][m] = per
    for m in others:
        bm = {str(p): compare_answers(rubric, get(p, reference), get(p, m), pairs, cutoff=cutoff, nearest_only=False)
              for p in passes if get(p, reference) and get(p, m)}
        if bm:
            out["between_models"][m] = bm
    if has_wider(rubric):
        out["relations"] = {m: {str(p): relation_stats(get(p, m)) for p in passes if get(p, m)} for m in models}
        out["wider_between_passes"] = {m: wider_agreement(get(passes[0], m), get(passes[1], m)) for m in models
                                       if len(passes) >= 2 and get(passes[0], m) and get(passes[1], m)}
        out["wider_between_models"] = {m: {str(p): wider_agreement(get(p, reference), get(p, m)) for p in passes
                                           if get(p, reference) and get(p, m)} for m in others}
    return out


def round2_examples(pair_set: PairSet, rubric: str, by_pass: Mapping[int, Mapping[tuple[str, str], Mapping]],
                    pair_ids: Iterable[str], subset_ids: Iterable[str] = (), *, models: Sequence[str],
                    reference: str = REFERENCE, cutoff: int = CUTOFF) -> dict:
    """The answers behind the counts, in pair-set order (then model, then pass): ``forward``, the answers at 2
    whose reason describes a containment; ``reverse``, the answers at 3 whose reason describes a two-sided
    overlap; ``crossings``, the pairs the two models put on different sides of ``cutoff`` in a pass, with
    both answers and both reasons.  ``in_subset`` marks the subset's pairs (the others are controls)."""
    ids, sub = set(pair_ids), set(subset_ids or ())
    passes = sorted(int(p) for p in by_pass)
    others = [m for m in models if m != reference]
    out: dict = {"forward": [], "reverse": [], "crossings": []}

    def ans(p: int, m: str, pid: str) -> Optional[Mapping]:
        a = (by_pass.get(p) or {}).get((rubric, m), {}).get(pid)
        return a if a and a.get("value") is not None else None

    for pr in pair_set.pairs:
        if pr.pair_id not in ids:
            continue
        base = {"pair_id": pr.pair_id, "target": pr.target, "listed": pr.listed, "group": pr.group,
                "in_subset": pr.pair_id in sub}
        for m in models:
            for p in passes:
                a = ans(p, m, pr.pair_id)
                if a is None:
                    continue
                d = decision_value(rubric, a["value"])
                row = {**base, "model": m, "pass": p, "value": a["value"], "reason": a.get("reason")}
                if _num_val(d) and d == 2 and describes_containment(a.get("reason")):
                    out["forward"].append(row)
                elif _num_val(d) and d == 3 and describes_two_sided(a.get("reason")):
                    out["reverse"].append(row)
        for p in passes:
            a = ans(p, reference, pr.pair_id)
            for m in others:
                b = ans(p, m, pr.pair_id)
                if a is None or b is None:
                    continue
                sa, sb = side(decision_value(rubric, a["value"]), cutoff), side(decision_value(rubric, b["value"]), cutoff)
                if sa is not None and sb is not None and sa != sb:
                    out["crossings"].append({**base, "pass": p, "first_model": reference, "first": a["value"],
                                             "first_reason": a.get("reason"), "second_model": m, "second": b["value"],
                                             "second_reason": b.get("reason")})
    return out


def _round_cells(s: Mapping, model: str, partner: Optional[str]) -> dict:
    """One rubric's figures for one model in one population (:func:`population_stats`), for a table row."""
    sc = s["self_consistency"].get(model)
    bm = s["between_models"].get(partner, {}) if partner else {}
    con = (s["contradictions"].get(model) or {}).get("pooled") or {}
    cov = s["coverage"].get(model, {})
    return {"n_both_passes": sc["native"]["n_both_parsed"] if sc else None,
            "consistency_native": sc["native"]["exact_all"] if sc else None,
            "consistency_decision": sc["decision"]["exact_all"] if sc else None,
            "pass_flips": sc["cutoff"]["crossings"] if sc else None, "pass_flips_n": sc["cutoff"]["n"] if sc else None,
            "agreement_native": {p: x["native"]["exact_all"] for p, x in bm.items()},
            "agreement_decision": {p: x["decision"]["exact_all"] for p, x in bm.items()},
            "crossings": {p: x["cutoff"]["crossings"] for p, x in bm.items()},
            "crossings_n": {p: x["cutoff"]["n"] for p, x in bm.items()},
            "covered": {p: {k: c[k] for k in ("covered", "n", "share")} for p, c in cov.items()},
            "forward": con.get("forward"), "n_2": con.get("n_2"), "forward_share": con.get("forward_share"),
            "reverse": con.get("reverse"), "n_3": con.get("n_3"), "reverse_share": con.get("reverse_share")}


def round2_rows(r2: Mapping) -> list[dict]:
    """One row per (population, round-2 arm, model) of :func:`analyse_round2`, with the round-1 arm's figures
    (``r1``) and the round-2 arm's (``r2``) on the same pairs: self-consistency (exact, native and decision)
    and flips at the cut-off between the passes; agreement and crossings with the other model per pass (for
    the reference model, with the one other model); the share at the cut-off or more per pass; the
    self-contradictions pooled over the passes."""
    ref = r2["reference"]
    others = [m for m in r2["models"] if m != ref]
    rows = []
    for pop, per in r2["per_population"].items():
        for arm, both in per.items():
            for m in r2["models"]:
                partner = m if m != ref else (others[0] if len(others) == 1 else None)
                rows.append({"population": pop, "arm": arm, "round1_arm": RUBRICS[arm]["round1"], "model": m,
                             "versus": partner, "r1": _round_cells(both["round1"], m, partner),
                             "r2": _round_cells(both["round2"], m, partner)})
    return rows


def round2_test(r2: Mapping) -> list[dict]:
    """The brief's test per population and round-2 arm: it improves on its round-1 arm when, on the same
    pairs, it has fewer self-contradictions (forward and reverse, both models, both passes) and fewer
    between-model crossings at the cut-off (both passes), with self-consistency (exact, on the decision
    scale, where the cut-off is) not lower for either model.  The native-scale consistency is given too."""
    models = r2["models"]
    out = []
    for pop, per in r2["per_population"].items():
        for arm, both in per.items():
            row: dict = {"population": pop, "arm": arm, "round1_arm": RUBRICS[arm]["round1"]}
            for which, key in (("r1", "round1"), ("r2", "round2")):
                s = both[key]
                pooled = {m: (s["contradictions"].get(m) or {}).get("pooled") or {} for m in models}
                row[which] = {"forward": sum(pooled[m].get("forward") or 0 for m in models),
                              "reverse": sum(pooled[m].get("reverse") or 0 for m in models),
                              "crossings": sum(x["cutoff"]["crossings"] for bm in s["between_models"].values()
                                               for x in bm.values()),
                              "pass_flips": sum(sc["cutoff"]["crossings"] for sc in s["self_consistency"].values()),
                              "consistency_decision": {m: (s["self_consistency"].get(m) or {}).get("decision", {})
                                                       .get("exact_all") for m in models},
                              "consistency_native": {m: (s["self_consistency"].get(m) or {}).get("native", {})
                                                     .get("exact_all") for m in models}}
                row[which]["contradictions"] = row[which]["forward"] + row[which]["reverse"]
            a, b = row["r1"], row["r2"]
            row["fewer_contradictions"] = b["contradictions"] < a["contradictions"]
            row["fewer_crossings"] = b["crossings"] < a["crossings"]
            row["consistency_not_worse"] = all(
                b["consistency_decision"][m] is not None and a["consistency_decision"][m] is not None
                and b["consistency_decision"][m] >= a["consistency_decision"][m] for m in models)
            row["improves"] = row["fewer_contradictions"] and row["fewer_crossings"] and row["consistency_not_worse"]
            out.append(row)
    return out


def analyse_round2(pair_set: PairSet, answers_by_pass: Mapping[int, Mapping[tuple[str, str], Mapping]],
                   round1_by_pass: Optional[Mapping[int, Mapping[tuple[str, str], Mapping]]], *,
                   subset: Optional[Mapping] = None, models: Sequence[str], reference: str = REFERENCE,
                   cutoff: int = CUTOFF, round1_run: Optional[str] = None) -> dict:
    """Round 2 of the arms experiment (``coding_plan_overlap_arms.md``, "Round 2"): every round-2 rubric in
    ``answers_by_pass`` against its round-1 arm (``RUBRICS[r]["round1"]``) in ``round1_by_pass`` (an earlier
    run's ``{pass: collect_answers(...)}``, ``round1_run``, on the same pair set), on the same pairs.  The
    populations: ``subset``, the subset's pairs (``subset["pair_ids"]``), and ``sent``, every pair this
    run's round-2 rubrics answered (the subset's calls whole, so the subset and its controls).  Per
    population and rubric, :func:`population_stats` for both rounds; the comparison rows
    (:func:`round2_rows`); the brief's test (:func:`round2_test`); and, from this run's answers on every
    pair sent, the examples (:func:`round2_examples`)."""
    passes = sorted(int(p) for p in answers_by_pass)
    arms = [r for r in RUBRICS if RUBRICS[r].get("round1")
            and any((answers_by_pass.get(p) or {}).get((r, m)) for p in passes for m in models)]
    order = {p.pair_id: i for i, p in enumerate(pair_set.pairs)}
    group = {p.pair_id: p.group for p in pair_set.pairs}
    answered = {pid for p in passes for (r, _), ans in answers_by_pass[p].items() if r in arms for pid in ans}
    sent = sorted((pid for pid in answered if pid in order), key=order.get)
    subset_ids = [pid for pid in (subset or {}).get("pair_ids", []) if pid in order]
    populations = ({"subset": subset_ids} if subset else {}) | {"sent": sent}
    out: dict = {"round1_run": round1_run, "cutoff": cutoff, "models": list(models), "reference": reference,
                 "passes": passes, "arms": arms, "pairing": {r: RUBRICS[r]["round1"] for r in arms},
                 "populations": {k: {"n_pairs": len(v), "n_answered": sum(x in answered for x in v),
                                     "by_group": dict(Counter(group[x] for x in v))} for k, v in populations.items()},
                 "patterns": {"containment": CONTAINMENT_PATTERN, "two_sided": TWO_SIDED_PATTERN, "flags": "IGNORECASE"},
                 "per_population": {}, "examples": {}}
    for pop, ids in populations.items():
        out["per_population"][pop] = {
            r: {"round2": population_stats(pair_set, r, answers_by_pass, ids, models=models, reference=reference,
                                           cutoff=cutoff),
                "round1": population_stats(pair_set, RUBRICS[r]["round1"], round1_by_pass or {}, ids, models=models,
                                           reference=reference, cutoff=cutoff)}
            for r in arms}
    out["examples"] = {r: round2_examples(pair_set, r, answers_by_pass, sent, subset_ids, models=models,
                                          reference=reference, cutoff=cutoff) for r in arms}
    out["rows"] = round2_rows(out)
    out["test"] = round2_test(out)
    return out


# --------------------------------------------------------------------------- the arms experiment, round 3

#: Roger's marks on the 30 pairs of overlap_test_1's blinded sheet (``m3_overlap_marks.md``), read by hand
#: (``coding_plan_overlap_arms.md``, "Round 3"): his leaning per item, and for five items the alternative he
#: named ("unsure: I think 1, but a case could be made for 2").  Items are the sheet's numbers, mapped to
#: pairs by ``overlap_test_1/marks_key.json``.
ROGER_LEANINGS: dict[int, Any] = {
    1: "opposite", 2: 1, 3: "opposite", 4: "opposite", 5: 0, 6: 0, 7: 0, 8: "opposite", 9: 0, 10: "opposite",
    11: 2, 12: 1, 13: 1, 14: 2, 15: 4, 16: "opposite", 17: 3, 18: 2, 19: 1, 20: 2,
    21: 2, 22: 2, 23: "opposite", 24: 4, 25: 3, 26: 2, 27: 3, 28: 4, 29: 1, 30: 2}
ROGER_ALTERNATIVES: dict[int, Any] = {2: 2, 13: 2, 17: 2, 21: 3, 27: 2}

#: A reason that uses round 2's line-2 wording, "neither implies the other: a persona can have either without
#: the other" (and its variants seen in round 2's reasons: "neither strictly / fully implies", "neither trait
#: implies", "neither fully contains", "neither requires", "without either implying the other", "each can be
#: held without the other"): a two-sided overlap stated as the rubric states it.  Round 1's containment pattern
#: does not know it, so a 2 whose reason says so can still match it ("narrower", "part of"); the discounted
#: forward slip leaves such reasons out, and the wide reverse slip counts a 3 that says it.  A one-way denial
#: ("a compassionate person need not be lenient") is a containment's and is not matched.
NEITHER_IMPLIES_PATTERN = (r"\bneither\b[^.;]{0,30}?\b(impl|entail|requir|contain|guarantee|necessitat)"
                           r"|\bwithout (either|one|each) (implying|requiring|entailing|containing)"
                           r"|\b(either|each)\b[^.;]{0,40}?\bwithout the other")
NEITHER_IMPLIES_RE = re.compile(NEITHER_IMPLIES_PATTERN, re.I)
#: A reason that states line 2 in its own words: "each adds something (the other lacks)", "each has / brings
#: something", or "neither implies the other" (:data:`NEITHER_IMPLIES_PATTERN`).  Round 2's two-sided pattern
#: also matches "X adds A, while Y stresses B, so they differ in emphasis", which line 3 allows (a difference of
#: emphasis); a 3 whose reason matches this one contradicts itself outright.
EXPLICIT_TWO_SIDED_PATTERN = r"\beach (adds|has|brings|contributes|offers) something|" + NEITHER_IMPLIES_PATTERN
EXPLICIT_TWO_SIDED_RE = re.compile(EXPLICIT_TWO_SIDED_PATTERN, re.I)
#: The first-line model and the second opinion of M3's rule (coding_plan_platform.md, M3 decisions 3 and 8).
FIRST_LINE, SECOND_OPINION = SONNET, OPUS
#: Cache reads as a share of the input price where it differs from ``llm.CACHE_READ_FACTOR`` (0.1, what the
#: usage records charge every model): Opus 5.5 reads at $0.20 against $4 input per million tokens (the
#: Claude API reference, 2026-10-06), so the records overstate its cached reads by 0.05 of the input price.
CACHE_READ_PRICE: dict[str, float] = {"opus-5-5": 0.05}


def describes_neither_implies(reason: Optional[str]) -> bool:
    """The reason says neither trait implies the other (:data:`NEITHER_IMPLIES_PATTERN`)."""
    return bool(reason) and bool(NEITHER_IMPLIES_RE.search(reason))


def slip_counts(rubric: str, answers: Iterable[Mapping]) -> dict:
    """The slips in a set of answers on the decision scale: ``forward``, 2s whose reason describes a
    containment (round 1's patterns, :func:`describes_containment`); ``forward_discounted``, the same less the
    reasons that say neither implies the other; ``reverse``, 3s whose reason describes a two-sided overlap
    (round 2's reverse slip, :func:`describes_two_sided`); ``reverse_wide``, 3s whose reason is two-sided or
    says neither implies the other; ``reverse_explicit``, 3s whose reason states line 2 in its own words
    (:data:`EXPLICIT_TWO_SIDED_PATTERN`).  Counts and shares of the 2s and the 3s."""
    twos, threes = [], []
    for a in answers:
        d = decision_value(rubric, a.get("value"))
        if _num_val(d) and d == 2:
            twos.append(a.get("reason"))
        elif _num_val(d) and d == 3:
            threes.append(a.get("reason"))
    share = lambda k, n: _r(k / n, 3) if n else None  # noqa: E731
    fwd = sum(describes_containment(x) for x in twos)
    fwd_d = sum(describes_containment(x) and not describes_neither_implies(x) for x in twos)
    rev = sum(describes_two_sided(x) for x in threes)
    rev_w = sum(describes_two_sided(x) or describes_neither_implies(x) for x in threes)
    rev_x = sum(bool(x) and bool(EXPLICIT_TWO_SIDED_RE.search(x)) for x in threes)
    return {"n_2": len(twos), "forward": fwd, "forward_share": share(fwd, len(twos)), "forward_discounted": fwd_d,
            "forward_discounted_share": share(fwd_d, len(twos)), "n_3": len(threes), "reverse": rev,
            "reverse_share": share(rev, len(threes)), "reverse_wide": rev_w, "reverse_wide_share": share(rev_w, len(threes)),
            "reverse_explicit": rev_x, "reverse_explicit_share": share(rev_x, len(threes))}


def escalates(sonnet: Any, cutoff: int = CUTOFF) -> bool:
    """Whether M3's rule sends the first-line answer to the second opinion: exactly at the cut-off, or
    "unsure" (M3 decision 5)."""
    return sonnet == "unsure" or (_num_val(sonnet) and sonnet == cutoff)


def rule_decision(sonnet: Any, opus: Any, cutoff: int = CUTOFF) -> Optional[str]:
    """M3's rule on the decision scale (coding_plan_platform.md, M3 decisions 3 and 8): the first-line model
    (Sonnet) reads every pair; above the cut-off is ``"cut"``, below it (or "opposite", decision 9) ``"keep"``;
    exactly at it (or "unsure") the pair goes to the second opinion (Opus) and is kept only if Opus reads it
    under the cut-off (a number below it, or "opposite"; an Opus "unsure" does not rescue).  ``None`` when the
    first answer is missing, or the second is needed and missing."""
    if sonnet is None:
        return None
    if escalates(sonnet, cutoff):
        if opus is None:
            return None
        return "keep" if side(opus, cutoff) is False else "cut"
    return "cut" if side(sonnet, cutoff) is True else "keep"


def _val(answers: Mapping[str, Mapping], pid: str) -> Any:
    return (answers.get(pid) or {}).get("value")


def rule_simulation(pair_ids: Iterable[str], first_by_pass: Mapping[int, Mapping], second_by_pass: Mapping[int, Mapping],
                    *, cutoff: int = CUTOFF) -> tuple[dict, dict]:
    """M3's rule (:func:`rule_decision`) over ``pair_ids`` in every pass both models answered: per pass the
    pairs decided, escalated (first-line answer at the cut-off or "unsure"), rescued by the second opinion, cut
    (directly, above the cut-off, or after the second opinion), kept, and kept though the second opinion reads
    the pair at or above the cut-off (the near-duplicates the rule lets through); and between the first two
    passes, the pairs whose decision differs.  Returns ``(stats, {pass: {pair_id: decision}})``."""
    ids = list(pair_ids)
    passes = sorted(set(first_by_pass) & set(second_by_pass))
    stats: dict = {"per_pass": {}, "flips": None}
    decisions: dict = {}
    for p in passes:
        first, second = first_by_pass[p], second_by_pass[p]
        c: Counter = Counter()
        dec: dict[str, str] = {}
        for pid in ids:
            s, o = _val(first, pid), _val(second, pid)
            if s is None:
                c["first_missing"] += 1
                continue
            d = rule_decision(s, o, cutoff)
            if escalates(s, cutoff):
                c["escalated"] += 1
                c["rescued" if d == "keep" else ("cut_after_second" if d == "cut" else "second_missing")] += 1
            elif d == "cut":
                c["cut_direct"] += 1
            else:
                c["kept_direct"] += 1
                c["kept_though_second"] += int(side(o, cutoff) is True)
            if d is not None:
                dec[pid] = d
        stats["per_pass"][str(p)] = {"n": len(dec), "escalated": c["escalated"], "rescued": c["rescued"],
                                     "cut": c["cut_direct"] + c["cut_after_second"], "cut_direct": c["cut_direct"],
                                     "cut_after_second": c["cut_after_second"],
                                     "kept": c["kept_direct"] + c["rescued"], "kept_though_second": c["kept_though_second"],
                                     "first_missing": c["first_missing"], "second_missing": c["second_missing"]}
        decisions[p] = dec
    if len(passes) >= 2:
        d1, d2 = decisions[passes[0]], decisions[passes[1]]
        both = set(d1) & set(d2)
        stats["flips"] = {"n": len(both), "differ": sum(d1[k] != d2[k] for k in both)}
    return stats, decisions


def decisions_against(base: Mapping[int, Mapping[str, str]], other: Mapping[int, Mapping[str, str]]) -> dict:
    """Per pass both hold, the pairs both decided and those decided differently (base keep and other cut, base cut
    and other keep)."""
    out = {}
    for p in sorted(set(base) & set(other)):
        both = set(base[p]) & set(other[p])
        out[str(p)] = {"n": len(both), "differ": sum(base[p][k] != other[p][k] for k in both),
                       "keep_to_cut": sum(base[p][k] == "keep" and other[p][k] == "cut" for k in both),
                       "cut_to_keep": sum(base[p][k] == "cut" and other[p][k] == "keep" for k in both)}
    return out


def second_on_escalated(pair_ids: Iterable[str], first_by_pass: Mapping[int, Mapping], second_by_pass: Mapping[int, Mapping],
                        *, cutoff: int = CUTOFF) -> dict:
    """The second opinion on the pairs the rule escalates: per pass, the pairs escalated in that pass, the second
    model's answers on them (that pass), and on those it answered in both passes how many it answered alike
    (same answer; same side of the cut-off); and the same over the pairs escalated in any pass."""
    ids = list(pair_ids)
    passes = sorted(set(first_by_pass) & set(second_by_pass))

    def steady(esc: list) -> dict:
        both = [pid for pid in esc if all(_val(second_by_pass[p], pid) is not None for p in passes[:2])]
        if len(passes) < 2:
            return {"n_both_passes": 0, "same": None, "same_side": None}
        a, b = passes[0], passes[1]
        return {"n_both_passes": len(both),
                "same": sum(str(_val(second_by_pass[a], k)) == str(_val(second_by_pass[b], k)) for k in both),
                "same_side": sum(side(_val(second_by_pass[a], k), cutoff) == side(_val(second_by_pass[b], k), cutoff)
                                 for k in both)}
    out: dict = {"per_pass": {}}
    any_pass: set = set()
    for p in passes:
        esc = [pid for pid in ids if escalates(_val(first_by_pass[p], pid), cutoff)]
        any_pass |= set(esc)
        out["per_pass"][str(p)] = {"n": len(esc), "answers": value_counts(_val(second_by_pass[p], k) for k in esc),
                                   **steady(esc)}
    esc = [pid for pid in ids if pid in any_pass]
    out["any_pass"] = {"n": len(esc), **steady(esc)}
    return out


def marks_agreement(answers: Mapping[str, Mapping], items: Sequence[Mapping], *,
                    leanings: Mapping[int, Any] = ROGER_LEANINGS, alternatives: Mapping[int, Any] = ROGER_ALTERNATIVES
                    ) -> dict:
    """One set of answers against Roger's marks (``items``: the marks key's ``{"item", "pair_id"}``): over the
    items both answered, exact agreement with his leaning (categories included), within one point where both
    are numbers, and agreement with his leaning or the alternative he named; per item the leaning, the
    alternative and the answer."""
    rows = []
    for it in items:
        rows.append({"item": it["item"], "pair_id": it["pair_id"], "leaning": leanings.get(it["item"]),
                     "alternative": alternatives.get(it["item"]), "value": _val(answers, it["pair_id"])})
    done = [r for r in rows if r["value"] is not None and r["leaning"] is not None]
    num = [r for r in done if _num_val(r["value"]) and _num_val(r["leaning"])]
    exact = sum(r["value"] == r["leaning"] for r in done)
    within = sum(abs(r["value"] - r["leaning"]) <= 1 for r in num)
    either = sum(r["value"] == r["leaning"] or (r["alternative"] is not None and r["value"] == r["alternative"])
                 for r in done)
    share = lambda k, n: _r(k / n, 3) if n else None  # noqa: E731
    return {"n": len(done), "exact": exact, "exact_share": share(exact, len(done)), "n_numeric": len(num),
            "within_one": within, "within_one_share": share(within, len(num)), "leaning_or_alternative": either,
            "leaning_or_alternative_share": share(either, len(done)), "items": rows}


def cache_stats(records: Iterable[Mapping]) -> dict:
    """Per model, from the usage the records hold (every answered request): requests, how many read the cached
    rubric and how many wrote it, the tokens (uncached input, cache writes, cache reads, output), the share of
    input tokens read from the cache, and the cost as the usage records charge it (writes 1.25x, reads 0.1x the
    input price), at the published read price (:data:`CACHE_READ_PRICE`), and with every input token at the
    uncached price; ``saved`` is the last minus the first."""
    from assistant_axis.judge_pricing import price_for_model

    from .llm import CACHE_READ_FACTOR, CACHE_WRITE_FACTOR
    per: dict[str, Counter] = defaultdict(Counter)
    for r in records:
        u = (r.get("response") or {}).get("usage_raw") or {}
        if not u:
            continue
        c = per[r["model"]]
        c["requests"] += 1
        inp, w, rd, out = (int(u.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                         "cache_read_input_tokens", "output_tokens"))
        c["input"] += inp
        c["cache_write"] += w
        c["cache_read"] += rd
        c["output"] += out
        c["reading"] += int(rd > 0)
        c["writing"] += int(w > 0)
    out_d = {}
    for m, c in sorted(per.items()):
        rate_in, rate_out = price_for_model(m)
        read_price = next((f for frag, f in CACHE_READ_PRICE.items() if frag in m.lower()), CACHE_READ_FACTOR)
        total_in = c["input"] + c["cache_write"] + c["cache_read"]
        charged = (c["input"] + CACHE_WRITE_FACTOR * c["cache_write"] + CACHE_READ_FACTOR * c["cache_read"]) * rate_in
        published = (c["input"] + CACHE_WRITE_FACTOR * c["cache_write"] + read_price * c["cache_read"]) * rate_in
        uncached = total_in * rate_in
        outp = c["output"] * rate_out
        out_d[m] = {"requests": c["requests"], "reading": c["reading"], "writing": c["writing"],
                    "hit_rate": _r(c["reading"] / c["requests"], 4) if c["requests"] else None,
                    "input_tokens": c["input"], "cache_write_tokens": c["cache_write"], "cache_read_tokens": c["cache_read"],
                    "output_tokens": c["output"], "read_share": _r(c["cache_read"] / total_in, 4) if total_in else None,
                    "charged_usd": _r((charged + outp) / 1e6, 6), "published_usd": _r((published + outp) / 1e6, 6),
                    "uncached_usd": _r((uncached + outp) / 1e6, 6), "saved_usd": _r((uncached - charged) / 1e6, 6),
                    "saved_published_usd": _r((uncached - published) / 1e6, 6), "read_price_factor": read_price}
    return out_d


def format_notes(records: Iterable[Mapping]) -> dict:
    """Per (model, pass), over the first attempt of each call and over the final record: answers wrapped in a
    results list, answers with extra keys (and which), answers not reason-first, and self-corrections (more
    than one answer object in the text); the single form's format notes (:func:`parse_single`)."""
    records = list(records)
    out: dict = {}
    for which, recs in (("first", first_records(records)), ("final", latest_records(records))):
        for (r, m, _, p), rec in recs.items():
            rows, errors, meta = reparse(rec)
            x = out.setdefault(f"{m}|{p}", {"model": m, "pass": p}).setdefault(
                which, {"n": 0, "parsed": 0, "wrapped": 0, "extra_keys": 0, "extra_key_names": Counter(),
                        "not_reason_first": 0, "self_corrections": 0})
            x["n"] += 1
            x["parsed"] += int(bool(rows))
            x["wrapped"] += int(bool(meta.get("wrapped")))
            x["extra_keys"] += int(bool(meta.get("extra_keys")))
            x["extra_key_names"].update(meta.get("extra_keys") or [])
            x["not_reason_first"] += int(meta.get("reason_first") is False)
            x["self_corrections"] += int((meta.get("n_result_objects") or 0) > 1)
    for v in out.values():
        for which in ("first", "final"):
            if which in v:
                v[which]["extra_key_names"] = dict(v[which]["extra_key_names"])
    return {k: out[k] for k in sorted(out)}


def _cells_consistency(x: Mapping) -> dict:
    n, d, c = x["native"], x["decision"], x["cutoff"]
    return {"n": n["n_both_parsed"], "exact": n["exact_all"], "n_numeric": n["n_numeric"],
            "within_one": n.get("within_one"), "kappa": n.get("kappa_quadratic"), "exact_decision": d["exact_all"],
            "cutoff_n": c["n"], "crossings": c["crossings"], "first_only": c["first_only"], "second_only": c["second_only"],
            "flips_native": x["flips_native"]["by_pair"]}


def _cells_groups(gs: Mapping) -> dict:
    return {g: {k: gs[g][k] for k in ("n", "mean", "share_3_plus", "opposite")} for g in GROUPS if gs[g]["n"]}


def identical_prompt_ids(groups: Optional[Mapping[str, str]]) -> Optional[set]:
    """The pairs whose prompt was identical in both passes of a list run (:func:`prompt_groups`: a call of one
    trait, or a list that shuffled into the same order); ``None`` without groups."""
    return None if groups is None else {pid for pid, g in groups.items() if g in ("single", "same_order")}


def round3_version(rubric: str, by_pass: Mapping[int, Mapping[str, Mapping]], pairs: Sequence[Pair], *,
                   models: Sequence[str], reference: str = REFERENCE, cutoff: int = CUTOFF,
                   groups: Optional[Mapping[str, str]] = None, like_ids: Optional[set] = None) -> tuple[dict, dict]:
    """One version's figures on one population (``pairs``; ``by_pass``: ``{pass: {model: answers}}``):
    self-consistency between the first two passes (every pair, and with ``groups``, the prompt groups of a list
    run's second pass, the pairs whose prompt was identical in both: one-trait and same-order calls; a
    single-form run's pairs are all identical; and with ``like_ids``, on those pairs of version 4's, the
    like-for-like comparison on the same pairs), each model against ``reference`` per pass, the share at the
    cut-off or more, the known groups on the decision scale, the slips per pass and pooled, M3's rule and the
    second opinion on the pairs it escalates.  Crossings and flips count every pair of the population.  Returns
    ``(figures, rule decisions by pass)``."""
    ids = {p.pair_id for p in pairs}
    passes = sorted(int(p) for p in by_pass)
    others = [m for m in models if m != reference]

    def get(p: int, m: str) -> dict:
        return {k: v for k, v in (by_pass.get(p) or {}).get(m, {}).items() if k in ids}
    out: dict = {"n_pairs": len(pairs), "passes": passes, "self_consistency": {}, "between_models": {}, "coverage": {},
                 "groups": {}, "slips": {}}
    for m in models:
        if len(passes) >= 2 and get(passes[0], m) and get(passes[1], m):
            a, b = get(passes[0], m), get(passes[1], m)
            cells = _cells_consistency(compare_answers(rubric, a, b, pairs, cutoff=cutoff, nearest_only=False))
            def on(keep: set) -> dict:
                sub = [p for p in pairs if p.pair_id in keep]
                return _cells_consistency(compare_answers(rubric, {k: v for k, v in a.items() if k in keep},
                                                          {k: v for k, v in b.items() if k in keep}, sub,
                                                          cutoff=cutoff, nearest_only=False))
            if groups is None:
                cells["identical"] = {**{k: v for k, v in cells.items() if k != "identical"}, "all_pairs": True}
            else:
                cells["identical"] = {**on(identical_prompt_ids(groups) & ids), "all_pairs": False}
            if like_ids is not None:
                cells["on_v4_identical"] = on(like_ids & ids)
            out["self_consistency"][m] = cells
        cov = {str(p): coverage(pairs, rubric, get(p, m), cutoff=cutoff, nearest_only=False) for p in passes if get(p, m)}
        if cov:
            out["coverage"][m] = cov
            out["groups"][m] = {str(p): _cells_groups(group_stats(pairs, to_decision(rubric, get(p, m))))
                                for p in passes if get(p, m)}
            per = {str(p): slip_counts(rubric, get(p, m).values()) for p in passes if get(p, m)}
            per["pooled"] = slip_counts(rubric, [x for p in passes for x in get(p, m).values()])
            out["slips"][m] = per
    for m in others:
        bm = {str(p): _cells_consistency(compare_answers(rubric, get(p, reference), get(p, m), pairs, cutoff=cutoff,
                                                         nearest_only=False))
              for p in passes if get(p, reference) and get(p, m)}
        if bm:
            out["between_models"][m] = bm
    decisions: dict = {}
    if FIRST_LINE in models and SECOND_OPINION in models:
        first = {p: get(p, FIRST_LINE) for p in passes}
        second = {p: get(p, SECOND_OPINION) for p in passes}
        out["rule"], decisions = rule_simulation(sorted(ids), first, second, cutoff=cutoff)
        out["second_on_escalated"] = second_on_escalated(sorted(ids), first, second, cutoff=cutoff)
    return out, decisions


def opus_changes(pairs: Sequence[Pair], base: Mapping[int, Mapping[str, Mapping]], new: Mapping[int, Mapping[str, Mapping]],
                 *, cutoff: int = CUTOFF) -> dict:
    """The pairs where the second opinion's answer under ``new`` would change the rule's decision against
    ``base`` (both ``{pass: {model: answers}}``): per pass, the pairs whose second-opinion answers under the two
    versions fall on different sides of the cut-off while the first-line model escalates the pair under either
    version (so that, with the first-line answer held, swapping the second opinion's answer flips the decision),
    in pair-set order, with every answer and both second-opinion reasons; and the count of all pairs where the
    second opinion changes side, escalated or not."""
    out: dict = {}
    for p in sorted(set(base) & set(new)):
        b1, n1 = (base[p].get(FIRST_LINE) or {}), (new[p].get(FIRST_LINE) or {})
        b2, n2 = (base[p].get(SECOND_OPINION) or {}), (new[p].get(SECOND_OPINION) or {})
        rows, any_side = [], 0
        for pr in pairs:
            o4, o6 = _val(b2, pr.pair_id), _val(n2, pr.pair_id)
            s4, s6 = side(o4, cutoff), side(o6, cutoff)
            if s4 is None or s6 is None or s4 == s6:
                continue
            any_side += 1
            f4, f6 = _val(b1, pr.pair_id), _val(n1, pr.pair_id)
            if not (escalates(f4, cutoff) or escalates(f6, cutoff)):
                continue
            rows.append({"pair_id": pr.pair_id, "target": pr.target, "listed": pr.listed, "group": pr.group,
                         "first_base": f4, "first_new": f6, "second_base": o4, "second_new": o6,
                         "second_base_reason": (b2.get(pr.pair_id) or {}).get("reason"),
                         "second_new_reason": (n2.get(pr.pair_id) or {}).get("reason"),
                         "decision_base": rule_decision(f4, o4, cutoff), "decision_new": rule_decision(f6, o6, cutoff),
                         "decision_base_with_new_second": rule_decision(f4, o6, cutoff),
                         "decision_new_with_base_second": rule_decision(f6, o4, cutoff)})
        out[str(p)] = {"second_changes_side": any_side, "n": len(rows), "pairs": rows}
    return out


def _mean(xs: Sequence) -> Optional[float]:
    xs = [x for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def _verdict(base: Optional[float], new: Optional[float], band: Optional[float], better: Optional[str]) -> Optional[str]:
    """"same" when ``new`` is within ``band`` of ``base``; else "better" / "worse" by ``better`` ("higher" or
    "lower" is better), or "higher" / "lower" when neither direction is better."""
    if base is None or new is None or band is None:
        return None
    d = new - base
    if abs(d) <= band + 1e-9:
        return "same"
    if better is None:
        return "higher" if d > 0 else "lower"
    return "better" if (d > 0) == (better == "higher") else "worse"


def round3_summary(r3: Mapping, models: Sequence[str]) -> list[dict]:
    """The summary rows (``coding_plan_overlap_arms.md``, "Round 3", item 4): version 4 against version 6 on the
    headline figures, each with a noise band and a verdict.  The band of a figure read in each pass is the
    difference between version 4's two passes (round 1's passes); of a figure that already compares the passes
    (self-consistency, the rule's decision flips), two binomial standard errors of version 4's figure; never
    less than one pair.  Figures read in each pass compare the means of the two passes."""
    pops = r3["populations"]
    al, nn = pops.get("all", {}).get("versions", {}), pops.get("nearest", {}).get("versions", {})
    v4, v6 = al.get("v4"), al.get("v6")
    if not v4 or not v6:
        return []
    rows: list[dict] = []

    def add(figure, who, base, new, band, better, fmt, note=None, n=None):
        rows.append({"figure": figure, "model": who, "v4": base, "v6": new, "band": band,
                     "verdict": _verdict(base, new, band, better), "format": fmt, "note": note, "n": n})

    def two_se(p, n):
        return max(2 * math.sqrt(p * (1 - p) / n), 1 / n) if p is not None and n else None

    def per_pass(d: Mapping, key=None):
        vals = [(d[p] if key is None else d[p].get(key)) for p in sorted(d)]
        return vals

    for m in models:
        a, b = v4["self_consistency"].get(m), v6["self_consistency"].get(m)
        if a and b:
            ident = a["identical"]
            same = b.get("on_v4_identical") or {}
            add("self-consistency, exact, like for like: the pairs whose prompt was identical in both of version 4's "
                "passes (one-trait calls and lists that shuffled into the same order), both versions on those pairs", m,
                ident["exact"], same.get("exact"), two_se(ident["exact"], ident["n"]), "higher", "pct",
                n=(ident["n"], same.get("n")))
            add("self-consistency, exact, every pair (version 4 includes its reordered lists; not like for like)", m,
                a["exact"], b["exact"], None, None, "pct", n=(a["n"], b["n"]))
    ref = r3["reference"]
    other = next((m for m in models if m != ref), None)
    if other:
        bm4, bm6 = v4["between_models"].get(other, {}), v6["between_models"].get(other, {})
        if bm4 and bm6:
            e4, e6 = per_pass(bm4, "exact"), per_pass(bm6, "exact")
            n = bm4[sorted(bm4)[0]]["n"]
            add(f"{SHORT.get(other, other)} against {SHORT.get(ref, ref)}, exact, every pair, mean of the passes", "both",
                _mean(e4), _mean(e6), max(abs(e4[0] - e4[-1]), 1 / n), "higher", "pct")
        nb4, nb6 = (nn.get("v4") or {}).get("between_models", {}).get(other, {}), \
            (nn.get("v6") or {}).get("between_models", {}).get(other, {})
        if nb4 and nb6:
            c4, c6 = per_pass(nb4, "crossings"), per_pass(nb6, "crossings")
            add("crossings at 3 between the models, nearest pairs, mean of the passes", "both", _mean(c4), _mean(c6),
                max(abs(c4[0] - c4[-1]), 1), "lower", "count")
    for m in models:
        cv4, cv6 = (nn.get("v4") or {}).get("coverage", {}).get(m, {}), (nn.get("v6") or {}).get("coverage", {}).get(m, {})
        if cv4 and cv6:
            s4, s6 = per_pass(cv4, "share"), per_pass(cv6, "share")
            n = cv4[sorted(cv4)[0]]["n"]
            add("covered at 3, nearest pairs, mean of the passes", m, _mean(s4), _mean(s6),
                max(abs(s4[0] - s4[-1]), 1 / n), None, "pct")
    r4, r6 = v4.get("rule"), v6.get("rule")
    if r4 and r6:
        for key, label, better in (("kept_though_second", "kept though Opus reads 3 or more (the rule), every pair, mean "
                                    "of the passes", "lower"),
                                   ("escalated", "escalated to Opus (the rule), every pair, mean of the passes", None),
                                   ("rescued", "rescued by Opus (the rule), every pair, mean of the passes", None)):
            k4, k6 = per_pass(r4["per_pass"], key), per_pass(r6["per_pass"], key)
            add(label, "rule", _mean(k4), _mean(k6), max(abs(k4[0] - k4[-1]), 1), better, "count")
        f4, f6 = r4.get("flips"), r6.get("flips")
        if f4 and f6 and f4["n"]:
            p4 = f4["differ"] / f4["n"]
            add("the rule's decision differs between the passes, every pair", "rule", f4["differ"], f6["differ"],
                max(2 * math.sqrt(f4["n"] * p4 * (1 - p4)), 1), "lower", "count", n=(f4["n"], f6["n"]))
    for key, label in (("forward_share", "2s whose reason describes a containment (round 1's pattern), pooled"),
                       ("forward_discounted_share", "the same, discounting \"neither implies the other\" wording"),
                       ("reverse_share", "3s whose reason describes a two-sided overlap (round 2's pattern), pooled"),
                       ("reverse_explicit_share", "3s whose reason states line 2's words (\"each adds something\", "
                        "\"neither implies the other\"), pooled")):
        for m in models:
            s4, s6 = v4["slips"].get(m), v6["slips"].get(m)
            if not s4 or not s6:
                continue
            passes = [k for k in s4 if k != "pooled"]
            vals = [s4[p][key] for p in passes]
            n_key = "n_3" if key.startswith("reverse") else "n_2"
            per_pass_n = s4["pooled"][n_key] / max(1, len(passes))          # one pair's worth of a pass's share
            band = (max(abs(vals[0] - vals[-1]), 1 / per_pass_n) if vals and None not in vals and per_pass_n
                    else None)
            count_key = key.removesuffix("_share")
            add(label, m, s4["pooled"][key], s6["pooled"][key], band, "lower", "pct",
                n=(f"{s4['pooled'][count_key]} of {s4['pooled'][n_key]}", f"{s6['pooled'][count_key]} of {s6['pooled'][n_key]}"))
    marks = r3.get("marks") or {}
    for key, label in (("leaning_or_alternative", "Roger's 30 marks: his leaning or the alternative he named"),
                       ("exact", "Roger's 30 marks: exact")):
        for m in models:
            base = (marks.get("v4_test1") or {}).get(m)
            new = [((marks.get(f"v6_pass{p}") or {}).get(m) or {}).get(key) for p in (1, 2)]
            noise = [((marks.get(f"v4_pass{p}") or {}).get(m) or {}).get(key) for p in (1, 2)]
            if not base:
                continue
            band = max(abs(noise[0] - noise[1]), 1) if None not in noise else 1
            add(label + " (version 4: overlap_test_1; version 6: mean of the passes)", m, base[key], _mean(new), band,
                "higher", "count", n=(base["n"], None))
    return rows


def analyse_round3(pair_set: PairSet, versions: Mapping[str, Mapping], populations: Mapping[str, Sequence[str]], *,
                   models: Sequence[str], reference: str = REFERENCE, cutoff: int = CUTOFF,
                   marks: Optional[Mapping] = None, records: Optional[Mapping[str, Sequence[Mapping]]] = None) -> dict:
    """Round 3 of the arms experiment (``coding_plan_overlap_arms.md``, "Round 3"): rubric A version 6 in its
    one-pair form against version 4 (round 1's A) and A2 (round 2) on the same pairs.

    ``versions``: ``{name: {"run", "rubric", "rubric_versions", "form", "by_pass": {pass: {model: answers}},
    "groups": prompt groups of a list run's second pass, or None}}``, names ``"v4"``, ``"A2"``, ``"v6"``
    (``"v6"`` this run); ``populations``: ``{"all" | "nearest" | "round2": [pair_id, ...]}``, each version
    measured on a population only if it answered every pair of it; ``marks``: ``{"items": the marks key's
    items, "test1": {model: answers}}`` (version 4 from overlap_test_1); ``records``: ``{name: records}`` for
    the parse rates, the format notes, the cache and the spend.  The figures per population and version
    (:func:`round3_version`), each version against version 4 per model and pass and in the rule's decisions,
    the pairs where Opus's answer changes the rule's decision (:func:`opus_changes`), Roger's marks
    (:func:`marks_agreement`), and the summary rows (:func:`round3_summary`)."""
    by_id = {p.pair_id: p for p in pair_set.pairs}
    out: dict = {"cutoff": cutoff, "models": list(models), "reference": reference, "first_line": FIRST_LINE,
                 "second_opinion": SECOND_OPINION,
                 "versions": {k: {x: v.get(x) for x in ("run", "rubric", "rubric_versions", "form")}
                              for k, v in versions.items()},
                 "patterns": {"containment": CONTAINMENT_PATTERN, "two_sided": TWO_SIDED_PATTERN,
                              "neither_implies": NEITHER_IMPLIES_PATTERN,
                              "explicit_two_sided": EXPLICIT_TWO_SIDED_PATTERN, "flags": "IGNORECASE"},
                 "populations": {}, "parse": {}, "format_notes": {}, "cache": {}, "spend_per_pair": {}}
    answered = {k: {pid for p, per in v["by_pass"].items() for ans in per.values() for pid, a in ans.items()
                    if a.get("value") is not None or a.get("error")} for k, v in versions.items()}
    like_ids = identical_prompt_ids((versions.get("v4") or {}).get("groups"))
    out["v4_identical_prompts"] = len(like_ids) if like_ids is not None else None
    for pop, ids in populations.items():
        pairs = [by_id[pid] for pid in ids if pid in by_id]
        idset = {p.pair_id for p in pairs}
        entry: dict = {"n_pairs": len(pairs), "by_group": dict(Counter(p.group for p in pairs)), "versions": {},
                       "against_v4": {}, "rule_against_v4": {}}
        decisions: dict = {}
        for name, v in versions.items():
            if not idset or not idset <= answered[name]:
                continue
            figs, dec = round3_version(v["rubric"], v["by_pass"], pairs, models=models, reference=reference,
                                       cutoff=cutoff, groups=v.get("groups"), like_ids=like_ids)
            entry["versions"][name] = figs
            decisions[name] = dec
        base = versions.get("v4")
        if base and "v4" in entry["versions"]:
            for name, v in versions.items():
                if name == "v4" or name not in entry["versions"]:
                    continue
                per_m = {}
                for m in models:
                    per_m[m] = {str(p): _cells_consistency(compare_answers(
                        "A", {k: x for k, x in (base["by_pass"].get(p) or {}).get(m, {}).items() if k in idset},
                        {k: x for k, x in (v["by_pass"].get(p) or {}).get(m, {}).items() if k in idset}, pairs,
                        cutoff=cutoff, nearest_only=False))
                        for p in sorted(set(base["by_pass"]) & set(v["by_pass"]))
                        if (base["by_pass"][p].get(m) and v["by_pass"][p].get(m))}
                entry["against_v4"][name] = per_m
                entry["rule_against_v4"][name] = decisions_against(decisions.get("v4", {}), decisions.get(name, {}))
        out["populations"][pop] = entry
    if "v4" in versions and "v6" in versions:
        out["opus_changes"] = opus_changes(pair_set.pairs, versions["v4"]["by_pass"], versions["v6"]["by_pass"],
                                           cutoff=cutoff)
    if marks and marks.get("items"):
        items = marks["items"]
        mk: dict = {"items": [{"item": it["item"], "pair_id": it["pair_id"], "leaning": ROGER_LEANINGS.get(it["item"]),
                               "alternative": ROGER_ALTERNATIVES.get(it["item"])} for it in items]}
        if marks.get("test1"):
            mk["v4_test1"] = {m: marks_agreement(a, items) for m, a in marks["test1"].items() if m in models}
        for name, label in (("v4", "v4"), ("v6", "v6")):
            v = versions.get(name)
            if not v:
                continue
            for p, per in sorted(v["by_pass"].items()):
                mk[f"{label}_pass{p}"] = {m: marks_agreement(per[m], items) for m in models if per.get(m)}
        out["marks"] = mk
    for name, recs in (records or {}).items():
        recs = list(recs)
        rubric = versions[name]["rubric"]
        mine = [r for r in recs if r["rubric"] == rubric and r["model"] in models]
        out["parse"][name] = {}
        for p in record_passes(mine):
            fp = first_attempt_parse(pair_set, mine, pass_no=p)
            final = collect_answers(pair_set, mine, pass_no=p)
            for m in models:
                f = fp.get((rubric, m))
                ans = final.get((rubric, m), {})
                if f or ans:
                    out["parse"][name][f"{m}|{p}"] = {"model": m, "pass": p, "first_ok": f["ok"] if f else None,
                                                      "first_total": f["total"] if f else None,
                                                      "ok": sum(a["value"] is not None for a in ans.values()),
                                                      "total": len(ans)}
        out["format_notes"][name] = format_notes(mine)
        out["cache"][name] = cache_stats(mine)
        n_answers = Counter()
        for p in record_passes(mine):
            for (r, m), ans in collect_answers(pair_set, mine, pass_no=p).items():
                n_answers[m] += sum(a["value"] is not None for a in ans.values())
        out["spend_per_pair"][name] = {m: {"answers": n_answers[m], "charged_usd": c["charged_usd"],
                                           "per_pair_usd": _r(c["charged_usd"] / n_answers[m], 6) if n_answers[m] else None}
                                       for m, c in out["cache"][name].items()}
    out["summary"] = round3_summary(out, models)
    return out


# --------------------------------------------------------------------------- tables

def _f(x, nd: int = 2) -> str:
    return "–" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def _pct(x) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def summary_markdown(summary: Mapping, pair_set: PairSet, corpus: Mapping) -> str:
    """The analysis as markdown tables (``tables.md`` beside ``summary.json``; the readout quotes it)."""
    models = summary["models"]
    ref = summary["reference"]
    sm = lambda m: SHORT.get(m, m)  # noqa: E731
    sent = summary.get("sent") or {}
    restricted = (f"  The run sent only these calls, named in `{sent['calls_from']}`, of the pair set's "
                  f"{sent['of_calls']} calls ({sent['of_pairs']} pairs); every table below is about the calls sent."
                  if sent.get("calls_from") else "")
    forms = (summary.get("arms") or {}).get("forms") or {}
    single = [r for r, f in forms.items() if f == "single"]
    calls_note = (f"  ({'Rubric' if len(single) == 1 else 'Rubrics'} {_names(single)} went out one pair per call, "
                  f"{summary['n_pairs']} calls a stage; the calls here are the pair set's.)" if single else "")
    L = ["# Overlap test: tables", "",
         f"{summary['n_pairs']} pairs in {summary['n_calls']} calls.{restricted}{calls_note}  Reference model: "
         f"{sm(ref)}.  Generated from `summary.json` beside this file.", ""]
    if (summary.get("round3") or {}).get("populations"):
        L += round3_markdown(summary["round3"], corpus, sm)[1:]
    L += ["## Parse rates (pairs whose answer parsed)", "",
          "| rubric | model | ok / total | rate | first attempt |", "|---|---|---|---|---|"]
    for k, v in summary["parse"].items():
        r, m = k.split("|", 1)
        fa = summary.get("parse_first_attempt", {}).get(k)
        first = f"{fa['ok']} / {fa['total']} ({_f(fa['rate'], 4)})" if fa else "–"
        L.append(f"| {r} | {sm(m)} | {v['ok']} / {v['total']} | {_f(v['rate'], 4)} | {first} |")
    six_num = [r for r in summary["agreement"] if native_k(r) == 6 and not RUBRICS[r].get("ranks")]
    six_rel = [r for r in summary["agreement"] if RUBRICS[r].get("ranks")]
    notes = []
    if six_num:
        notes.append(f"rubric {_names(six_num)} on {'its' if len(six_num) == 1 else 'their'} own 0-5 scale")
    if six_rel:
        notes.append(f"rubric {_names(six_rel)}'s relations as ranks, different 0, neighbours 1, overlap 2, "
                     "contains 3, variant 4, same 5 (C's rungs)")
    scales_note = f"  {'; '.join(notes)}.".replace("  rubric", "  Rubric", 1) if notes else ""
    L += ["", f"## Agreement with {sm(ref)}", "",
          "Exact agreement over every answer (categories included); then, on the pairs where both gave a number, "
          "exact, within one point, the mean difference (model minus reference) and the weighted kappa "
          "(quadratic; linear in brackets)." + scales_note, "",
          "| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r, per in summary["agreement"].items():
        for m, a in per.items():
            L.append(f"| {r} | {sm(m)} | {a['n_both_parsed']} | {_pct(a['exact_all'])} | {a['n_numeric']} | "
                     f"{_pct(a.get('exact'))} | {_pct(a.get('within_one'))} | {_f(a.get('mean_diff'))} | "
                     f"{_f(a.get('kappa_quadratic'))} ({_f(a.get('kappa_linear'))}) |")
    L += ["", "Categorical answers against the reference (rows: reference; columns: model):", ""]
    for r, per in summary["agreement"].items():
        for m, a in per.items():
            cells = "; ".join(f"{rk}: " + ", ".join(f"{ck} {n}" for ck, n in row.items())
                              for rk, row in a["table"].items() if rk != "numeric" or set(row) != {"numeric"})
            L.append(f"- rubric {r}, {sm(m)}: {cells or 'numbers only'}")
    L += ["", "## Spearman correlation with the persona-space and the embedding cosine", "",
          "Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; "
          "without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest "
          "pairs without recorded opposites.", "",
          "| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |",
          "|---|---|---|---|---|---|---|"]
    for r, per in summary["correlation"].items():
        for m, c in per.items():
            for what in ("persona", "embedding"):
                cells = []
                for pop in ("all", "non_antonym", "nearest", "nearest_non_antonym"):
                    x = c[what][pop]
                    ci = f" [{_f(x.get('lo'))}, {_f(x.get('hi'))}]" if x.get("lo") is not None else ""
                    cells.append(f"{_f(x['rho'])}{ci} (n {x['n']})")
                L.append(f"| {r} | {sm(m)} | {what} | " + " | ".join(cells) + " |")
    L += ["", "## Rubric A against rubric B on the same pairs", "",
          "rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a "
          "number; paired 95% bootstrap interval (targets resampled).", "",
          "| model | population | cosine | n | rho A | rho B | A - B | 95% interval |", "|---|---|---|---|---|---|---|---|"]
    for m, pops in summary["rubric_difference"].items():
        for pop, d in pops.items():
            for what, x in d.items():
                ci = f"[{_f(x.get('lo'))}, {_f(x.get('hi'))}]" if x.get("lo") is not None else "–"
                L.append(f"| {sm(m)} | {pop} | {what} | {x['n']} | {_f(x['rho_a'])} | {_f(x['rho_b'])} | "
                         f"{_f(x['diff'])} | {ci} |")
    for r, per in summary["groups"].items():
        if not per:                                      # a rubric this run did not send
            continue
        has_opp = "opposite" in RUBRICS[r]["categories"]
        on_decision = (f" On the decision scale (rubric A's 0-4; {r}: {RUBRICS[r]['decision_note']})."
                       if RUBRICS[r].get("decision") else "")
        L += ["", f"## Known groups, rubric {r}", "",
              "Mean of the numeric answers / share at 3 or more" + (" / share opposite" if has_opp else "")
              + " / share unsure; n in the first column." + on_decision, "",
              "| group | n | " + " | ".join(sm(m) for m in per) + " |", "|---|---|" + "---|" * len(per)]
        for g in GROUPS:
            n = next(iter(per.values()))[g]["n"]
            cells = []
            for m in per:
                s = per[m][g]
                parts = [_f(s["mean"]), _pct(s["share_3_plus"])]
                if has_opp:
                    parts.append(_pct(s["opposite"]))
                parts.append(_pct(s["unsure"]))
                cells.append(" / ".join(parts))
            L.append(f"| {g} | {n} | " + " | ".join(cells) + " |")
        if ref in per:
            L += ["", f"Answer counts, {sm(ref)}:", ""]
            for g in GROUPS:
                L.append(f"- {g}: " + ", ".join(f"{k} {v}" for k, v in per[ref][g]["counts"].items()))
    L += ["", "## Unsure and opposite rates", "", "| rubric | model | n | unsure | opposite | opposite on the antonym "
          "group | opposite on nearest recorded opposites | opposite elsewhere |", "|---|---|---|---|---|---|---|---|"]
    for r, per in summary["rates"].items():
        for m, x in per.items():
            L.append(f"| {r} | {sm(m)} | {x['n']} | {_pct(x['unsure'])} ({x['n_unsure']}) | "
                     f"{_pct(x['opposite'])} ({x['n_opposite']}) | {_pct(x['antonym_group']['opposite'])} of "
                     f"{x['antonym_group']['n']} | {_pct(x['nearest_recorded_opposites']['opposite'])} of "
                     f"{x['nearest_recorded_opposites']['n']} | {_pct(x['not_recorded_opposites']['opposite'])} of "
                     f"{x['not_recorded_opposites']['n']} |")
    if summary.get("opus_on_disagreement"):
        L += ["", "## Where Haiku and Sonnet agree or differ, what Opus says", "",
              "| rubric | Haiku = Sonnet | Opus the same | Haiku != Sonnet | Opus sides with Haiku | with Sonnet | "
              "neither |", "|---|---|---|---|---|---|---|"]
        for r, x in summary["opus_on_disagreement"].items():
            L.append(f"| {r} | {x['haiku_sonnet_same']} | {x['opus_same_as_both']} ({_pct(x['opus_same_share'])}) | "
                     f"{x['haiku_sonnet_differ']} | {x['opus_sides_haiku']} | {x['opus_sides_sonnet']} | "
                     f"{x['opus_neither']} |")
    for r, per in summary["by_score"].items():
        if ref not in per:
            continue
        L += ["", f"## Rubric {r} ({sm(ref)}): cosines by answer", "",
              "| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |", "|---|---|---|---|---|"]
        for k, x in per[ref].items():
            if x["n"]:
                L.append(f"| {k} | {x['n']} | {_f(x['mean_embedding_cos'], 3)} | {x['n_persona']} | "
                         f"{_f(x['mean_persona_cos'], 3)} |")
    if ref in summary.get("divergence", {}):
        d = summary["divergence"][ref]
        L += ["", f"## Where the rubrics differ most ({sm(ref)})", "",
              f"B minus A over {d['n']} pairs with two numbers: counts {d['diff_counts']}, mean {_f(d['mean_diff'], 3)}.",
              "", "| target | listed | group | A | B | A's reason | B's reason |", "|---|---|---|---|---|---|---|"]
        for row in d["b_above_a"] + d["a_above_b"][:3]:
            L.append(f"| {corpus[row['target']]['label']} | {corpus[row['listed']]['label']} | {row['group']} | "
                     f"{row['a']} | {row['b']} | {row['reason_a']} | {row['reason_b']} |")
    L += ["", "## The same pair in two calls", ""]
    for r, per in summary["context_consistency"].items():
        L.append(f"- rubric {r}: " + "; ".join(f"{sm(m)} {x['same']} of {x['n']} the same" for m, x in per.items()))
    arms = summary.get("arms")
    if arms and (len(arms.get("passes", [])) >= 2 or (arms.get("baseline") or {}).get("per_model")):
        L += arms_markdown(arms, corpus, sm)
    r2 = summary.get("round2")
    if r2 and r2.get("arms"):
        L += round2_markdown(r2, corpus, sm, subset_counts=(summary.get("subset") or {}).get("counts"))
    return "\n".join(L) + "\n"


def _label(corpus: Mapping, stem: str) -> str:
    return (corpus.get(stem) or {}).get("label", stem)


def _flips_text(f: Mapping) -> str:
    return ", ".join(f"{k} {n}" for k, n in f["by_pair"].items()) or "none"


def arms_markdown(arms: Mapping, corpus: Mapping, sm) -> list[str]:
    """The arms experiment's tables (:func:`analyse_arms`): the cross-arm table, parse rates by pass, one
    section per arm, and arm A's pass 1 against the earlier run."""
    ref = arms["reference"]
    passes = [str(p) for p in arms["passes"]]
    cut = arms["cutoff"]
    L = ["", f"## The arms experiment: {len(passes)} pass{'es' if len(passes) != 1 else ''}, decision scale, "
         f"cut-off {cut}", ""]
    forms = arms.get("forms") or {}
    single = [r for r in arms["rubrics"] if forms.get(r) == "single"]
    listed = [r for r in arms["rubrics"] if forms.get(r) != "single"]
    for p, o in (arms.get("order", {}) if listed else {}).items():
        L.append(f"Pass {p} sent the same calls with the listed traits in a fresh order"
                 + (f" (rubric{'s' if len(listed) > 1 else ''} {_names(listed)})" if single else "")
                 + f": {o['same_order']} of {o['n_calls']} calls kept pass 1's order by chance "
                 f"({o['same_order_single']} of them list one trait); {o['pairs_moved']} of {o['n_pairs']} pairs "
                 "went out under another id.")
    if single and len(passes) >= 2:
        L.append(f"Rubric{'s' if len(single) > 1 else ''} {_names(single)} went out one pair per call (the single "
                 "form): every later pass sent the identical prompt, there being no list to reorder, so the agreement "
                 "between the passes is sampling noise alone.")
    maps = decision_maps_text(arms["rubrics"])
    natives = native_scales_text(arms["rubrics"])
    L += ["", "The decision scale is rubric A's 0-4 with \"opposite\" and \"unsure\""
          + (f": {maps}." if maps else "; every rubric here answers on it directly.") + "  Covered means "
          f"{cut} or more on it (\"opposite\" is not covered, \"unsure\" neither), over the nearest-neighbour "
          "pairs.  The native scale is each rubric's own answers" + (f" ({natives})" if natives else "")
          + ".  Exact agreement counts every answer, categories included.", "",
          "### Cross-arm table", "",
          "| arm | model | consistency, exact (native) | consistency, exact (decision) | between-pass flips at "
          f"{cut} | agreement, exact, pass 1 (native / decision) | agreement, pass 2 | covered at {cut}, pass 1 | "
          f"targets covered, pass 1 | between-model crossings at {cut} (pass 1 / pass 2) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for row in arms["cross_arm"]:
        an, ad, cr, crn = row["agreement_native"], row["agreement_decision"], row["crossings"], row["crossings_n"]
        cov = row["covered"].get(passes[0]) if passes else None

        def agree(p):
            return f"{_pct(an.get(p))} / {_pct(ad.get(p))}" if p in an else "–"
        cells = [row["arm"], sm(row["model"]),
                 f"{_pct(row['consistency_native'])} ({row['n_both_passes']})" if row["n_both_passes"] is not None
                 else "–",
                 _pct(row["consistency_decision"]),
                 f"{row['pass_flips_at_cutoff']} of {row['pass_flips_n']}" if row["pass_flips_n"] is not None else "–",
                 agree(passes[0]) if passes else "–", agree(passes[1]) if len(passes) > 1 else "–",
                 f"{cov['covered']} of {cov['n']} ({_pct(cov['share'])})" if cov else "–",
                 f"{cov['targets_covered']} of {cov['n_targets']}" if cov else "–",
                 " / ".join(f"{cr[p]} of {crn[p]}" for p in passes if p in cr) or "–"]
        L.append("| " + " | ".join(cells) + " |")
    L += ["", "Agreement is each model against the other one (Sonnet 5.5 against Opus 5.5 in this experiment); "
          "crossings are the nearest pairs the two models put on different sides of the cut-off, flips the "
          "nearest pairs one model put on different sides in its two passes.", "",
          "### Parse rates by pass", "", "| rubric | model | pass | ok / total | first attempt |", "|---|---|---|---|---|"]
    for v in arms["parse"].values():
        first = f"{v['first_ok']} / {v['first_total']}" if v.get("first_total") is not None else "–"
        L.append(f"| {v['rubric']} | {sm(v['model'])} | {v['pass']} | {v['ok']} / {v['total']} | {first} |")
    for r in arms["rubrics"]:
        arm = arms["per_arm"][r]
        L += ["", f"### Arm {r}: {RUBRICS[r]['name']} ({RUBRICS[r]['title']})", ""]
        if arm["self_consistency"]:
            L += [f"Self-consistency, pass {passes[0]} against pass {passes[1]} (pairs both passes answered; mean "
                  "difference pass 2 minus pass 1; kappa quadratic):", "",
                  "| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) "
                  f"| within one (decision) | flips at {cut}, nearest |", "|---|---|---|---|---|---|---|---|---|"]
            for m, sc in arm["self_consistency"].items():
                n, d, c = sc["native"], sc["decision"], sc["cutoff"]
                L.append(f"| {sm(m)} | {n['n_both_parsed']} | {_pct(n['exact_all'])} | {_pct(n.get('within_one'))} | "
                         f"{_f(n.get('mean_diff'))} | {_f(n.get('kappa_quadratic'))} | {_pct(d['exact_all'])} | "
                         f"{_pct(d.get('within_one'))} | {c['crossings']} of {c['n']} ({c['first_only']} covered in "
                         f"pass 1 only, {c['second_only']} in pass 2 only) |")
            L += ["", "Where the passes differ, by the two answers (native; then decision):", ""]
            for m, sc in arm["self_consistency"].items():
                L.append(f"- {sm(m)}: {_flips_text(sc['flips_native'])} ({sc['flips_native']['adjacent']} of "
                         f"{sc['flips_native']['n']} between neighbouring points); decision: "
                         f"{_flips_text(sc['flips_decision'])}")
            if any(sc.get("by_prompt") for sc in arm["self_consistency"].values()):
                L += ["", "Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; "
                      "pairs): a call of one trait and a longer call whose order came out the same were the same "
                      "prompt asked again; a reordered call was another prompt:", "",
                      "| model | one trait | same order by chance | reordered |", "|---|---|---|---|"]
                for m, sc in arm["self_consistency"].items():
                    bp = sc.get("by_prompt") or {}
                    L.append(f"| {sm(m)} | " + " | ".join(
                        f"{_pct(bp[g]['exact_native'])} / {_pct(bp[g]['exact_decision'])} ({bp[g]['n']})"
                        if g in bp else "–" for g in PROMPT_GROUPS) + " |")
            for m, sc in arm["self_consistency"].items():
                if sc["cutoff"]["pairs"]:
                    L += ["", f"{sm(m)}'s nearest pairs on different sides of {cut} in the two passes (pass 1, pass 2):", ""]
                    L += [f"- {_label(corpus, x['target'])} / {_label(corpus, x['listed'])}: {x['first']}, {x['second']}"
                          for x in sc["cutoff"]["pairs"]]
        for m, per_pass in arm["between_models"].items():
            if not per_pass:
                continue
            L += ["", f"{sm(m)} against {sm(ref)} (pairs both answered; mean difference {sm(m)} minus {sm(ref)}):", "",
                  "| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) "
                  f"| within one (decision) | crossings at {cut}, nearest |", "|---|---|---|---|---|---|---|---|---|"]
            for p, x in per_pass.items():
                n, d, c = x["native"], x["decision"], x["cutoff"]
                L.append(f"| {p} | {n['n_both_parsed']} | {_pct(n['exact_all'])} | {_pct(n.get('within_one'))} | "
                         f"{_f(n.get('mean_diff'))} | {_f(n.get('kappa_quadratic'))} | {_pct(d['exact_all'])} | "
                         f"{_pct(d.get('within_one'))} | {c['crossings']} of {c['n']} ({c['first_only']} {sm(ref)} "
                         f"covered only, {c['second_only']} {sm(m)} covered only) |")
            L += ["", "Where they differ, by the two answers (native):", ""]
            L += [f"- pass {p}: {_flips_text(x['flips_native'])}" for p, x in per_pass.items()]
            for p, x in per_pass.items():
                if x["cutoff"]["pairs"]:
                    L += ["", f"Pass {p}, nearest pairs on different sides of {cut} ({sm(ref)}, {sm(m)}):", ""]
                    L += [f"- {_label(corpus, y['target'])} / {_label(corpus, y['listed'])}: {y['first']}, {y['second']}"
                          for y in x["cutoff"]["pairs"]]
        L += ["", f"Coverage at {cut}, nearest pairs:", "",
              "| model | pass | answered | covered | share | targets covered | opposite | unsure |",
              "|---|---|---|---|---|---|---|---|"]
        for m, per_pass in arm["coverage"].items():
            for p, c in per_pass.items():
                L.append(f"| {sm(m)} | {p} | {c['n']} | {c['covered']} | {_pct(c['share'])} | {c['targets_covered']} of "
                         f"{c['n_targets']} | {c['opposite']} | {c['unsure']} |")
        if "relations" in arm:
            cols = list(reversed(RELATIONS)) + ["opposite", "unsure", "unparsed"]
            L += ["", "Relations named (all pairs):", "", "| model | pass | " + " | ".join(cols) + " |",
                  "|---|---|" + "---|" * len(cols)]
            for m, per_pass in arm["relations"].items():
                for p, x in per_pass.items():
                    L.append(f"| {sm(m)} | {p} | " + " | ".join(str(x["counts"].get(c, 0)) for c in cols) + " |")
            L += ["", "The wider of a \"contains\":", "",
                  "| model | pass | contains | wider: target | wider: listed | missing | not target or listed | "
                  "wider given with another relation | alias spellings |", "|---|---|---|---|---|---|---|---|---|"]
            for m, per_pass in arm["relations"].items():
                for p, x in per_pass.items():
                    w = x["wider"]
                    L.append(f"| {sm(m)} | {p} | {x['n_contains']} | {w['target']} | {w['listed']} | {w['missing']} | "
                             f"{w['invalid']} | {x['wider_with_other_relation']} | {x['alias_spellings']} |")
            L.append("")
            for m, x in arm.get("wider_between_passes", {}).items():
                L.append(f"- {sm(m)}, pass 1 against pass 2: {x['n_both_contains']} pairs \"contains\" in both, the same "
                         f"wider {x['same']}, the other {x['different']}, unknown {x['unknown']}")
            for m, per_pass in arm.get("wider_between_models", {}).items():
                for p, x in per_pass.items():
                    L.append(f"- {sm(m)} against {sm(ref)}, pass {p}: {x['n_both_contains']} pairs \"contains\" for "
                             f"both, the same wider {x['same']}, the other {x['different']}, unknown {x['unknown']}")
        if "scope_kinds" in arm:
            kinds = list(SCOPE_KINDS)
            what = ("asked of a 3's reason" if RUBRICS[r].get("kinds") == "asked"
                    else f"not asked: rubric {r}'s 3s, as a control")
            L += ["", f"Kinds of difference the reasons of 3s name ({what}; a word search, a reason may name several):",
                  "", "| model | pass | 3s | " + " | ".join(kinds) + " | none | several |",
                  "|---|---|---|" + "---|" * len(kinds) + "---|---|"]
            for m, per_pass in arm["scope_kinds"].items():
                for p, x in per_pass.items():
                    L.append(f"| {sm(m)} | {p} | {x['n']} | " + " | ".join(str(x["kinds"][k]) for k in kinds)
                             + f" | {x['none']} ({_pct(x['none_share'])}) | {x['multiple']} |")
    b = arms.get("baseline") or {}
    if b.get("per_model"):
        L += ["", f"### Arm A, pass 1, against {b['run_id']} (rubric A, the same pairs and user turns)", "",
              f"{b['run_id']} is the reference (mean difference: this run minus {b['run_id']}).", "",
              "| model | both answered | exact (native) | within one | mean diff | kappa | "
              f"flips at {cut}, nearest |", "|---|---|---|---|---|---|---|"]
        for m, x in b["per_model"].items():
            n, c = x["native"], x["cutoff"]
            L.append(f"| {sm(m)} | {n['n_both_parsed']} | {_pct(n['exact_all'])} | {_pct(n.get('within_one'))} | "
                     f"{_f(n.get('mean_diff'))} | {_f(n.get('kappa_quadratic'))} | {c['crossings']} of {c['n']} |")
        L += ["", "Where they differ, by the two answers:", ""]
        L += [f"- {sm(m)}: {_flips_text(x['flips_native'])}" for m, x in b["per_model"].items()]
    return L


#: How many examples of each kind round 2's tables quote per arm (the brief asks for six).
ROUND2_EXAMPLES = 6
_POPULATION_TITLE = {"subset": "The subset's pairs", "sent": "Every pair sent (the subset and its controls)"}


def _arrow(a, b, fmt=_pct) -> str:
    return f"{fmt(a)} → {fmt(b)}"


def _of(n, total, share) -> str:
    return "–" if n is None else f"{n} of {total} ({_pct(share)})"


def _first_pairs(rows: Sequence[Mapping], n: int) -> list[tuple[str, list[Mapping]]]:
    """The rows of the first ``n`` pairs (rows come in pair order), grouped by pair."""
    out: list[tuple[str, list[Mapping]]] = []
    for row in rows:
        if out and out[-1][0] == row["pair_id"]:
            out[-1][1].append(row)
        elif len(out) < n:
            out.append((row["pair_id"], [row]))
    return out


def round2_markdown(r2: Mapping, corpus: Mapping, sm, subset_counts: Optional[Mapping] = None) -> list[str]:
    """Round 2's tables (:func:`analyse_round2`): the brief's test, then per population each round-2 arm
    against its round-1 arm on the same pairs, D2's ``wider``, and per arm the first answers at 2 whose
    reason describes a containment and the first crossings between the models, reasons in full."""
    cut, ref = r2["cutoff"], r2["reference"]
    models = r2["models"]
    pairing = ", ".join(f"{r} against {r1}" for r, r1 in r2["pairing"].items())
    L = ["", "## Round 2: the clarified lines, on the confusion subset", ""]
    if subset_counts:
        c = subset_counts
        L += [f"The subset: {c['n_pairs']} pairs ({c['rule_1']} with both a 2 and a 3 among their readings, "
              f"{c['rule_2_only']} more with a 2 whose reason describes a containment) in {c['n_calls']} of "
              f"{c['of_calls']} calls.  The run sent those calls whole, as round 1 built them: {c['n_pairs_sent']} "
              f"pairs, {c['n_controls']} of them controls.", ""]
    L += [f"Each round-2 arm against its round-1 arm from {r2['round1_run'] or 'the round-1 run'} on the same pairs "
          f"({pairing}); pass 1 sent the round-1 order of every call and pass 2 the same reshuffle as round 1, so "
          "the user turns are round 1's.  Cut-off "
          f"{cut} on the decision scale.  Crossings (the two models on different sides of it in a pass), flips (one "
          f"model's two passes on different sides) and the share at {cut} or more count every pair of the "
          "population, whatever its group (round 1's headline table counted the nearest pairs only).  "
          "Self-contradictions, pooled over both passes: answers at 2 (2, \"overlap\") whose reason describes a "
          "containment and not a two-sided overlap; the reverse slip: answers at 3 (3, \"contains\", and C's 4 and "
          "D's \"variant\") whose reason describes a two-sided overlap; round 1's patterns (in `summary.json`).  "
          "Cells read round 1 → round 2.", "",
          "**Selection.**  The subset was chosen from these round-1 readings (and earlier runs'), so round 1's "
          "figures on it lean toward confusion by construction, and any fresh reading would look better there "
          "(regression to the mean); on the controls the lean is the other way.  The round-2 arms are measured "
          "alike and compare fairly with each other.", "",
          "### The brief's test", "",
          f"Improves: fewer self-contradictions and fewer between-model crossings at {cut} than the round-1 arm on "
          "the same pairs, with self-consistency (exact, decision scale) not lower for either model.", "",
          "| population | arm | self-contradictions, both models and passes | of which reverse | crossings at "
          f"{cut}, both passes | flips at {cut}, both models | "
          + " | ".join(f"consistency, decision, {sm(m)}" for m in models) + " | improves |",
          "|---|---|---|---|---|---|" + "---|" * len(models) + "---|"]
    for t in r2["test"]:
        a, b = t["r1"], t["r2"]
        L.append(f"| {t['population']} | {t['arm']} vs {t['round1_arm']} | {a['contradictions']} → {b['contradictions']} | "
                 f"{a['reverse']} → {b['reverse']} | {a['crossings']} → {b['crossings']} | "
                 f"{a['pass_flips']} → {b['pass_flips']} | "
                 + " | ".join(_arrow(a["consistency_decision"][m], b["consistency_decision"][m]) for m in models)
                 + f" | {'yes' if t['improves'] else 'no'} |")
    for pop, per in r2["per_population"].items():
        info = r2["populations"][pop]
        L += ["", f"### {_POPULATION_TITLE.get(pop, pop)}: {info['n_pairs']} pairs", "",
              "By group: " + ", ".join(f"{g} {n}" for g, n in info["by_group"].items()) + ".", "",
              "| arm | model | consistency, exact, native | decision | flips at "
              f"{cut} | at {cut} or more, pass 1 | pass 2 | 2s with a containment reason | 3s with a two-sided reason |",
              "|---|---|---|---|---|---|---|---|---|"]
        for row in (x for x in r2["rows"] if x["population"] == pop):
            a, b = row["r1"], row["r2"]

            def cov(s, p):
                c = s["covered"].get(p)
                return _of(c["covered"], c["n"], c["share"]) if c else "–"
            L.append(f"| {row['arm']} vs {row['round1_arm']} | {sm(row['model'])} | "
                     f"{_arrow(a['consistency_native'], b['consistency_native'])} | "
                     f"{_arrow(a['consistency_decision'], b['consistency_decision'])} | "
                     f"{_f(a['pass_flips'])} → {_f(b['pass_flips'])} of {b['pass_flips_n'] or a['pass_flips_n']} | "
                     f"{cov(a, '1')} → {cov(b, '1')} | {cov(a, '2')} → {cov(b, '2')} | "
                     f"{_of(a['forward'], a['n_2'], a['forward_share'])} → {_of(b['forward'], b['n_2'], b['forward_share'])} | "
                     f"{_of(a['reverse'], a['n_3'], a['reverse_share'])} → {_of(b['reverse'], b['n_3'], b['reverse_share'])} |")
        L += ["", f"Between the models ({_names([sm(m) for m in models if m != ref])} against {sm(ref)}):", "",
              "| arm | agreement, exact, native, pass 1 | pass 2 | decision, pass 1 | pass 2 | crossings at "
              f"{cut}, pass 1 | pass 2 |", "|---|---|---|---|---|---|---|"]
        for row in (x for x in r2["rows"] if x["population"] == pop and x["model"] == ref):
            a, b = row["r1"], row["r2"]

            def cr(s, p):
                return f"{s['crossings'][p]} of {s['crossings_n'][p]}" if p in s["crossings"] else "–"
            L.append(f"| {row['arm']} vs {row['round1_arm']} | "
                     f"{_arrow(a['agreement_native'].get('1'), b['agreement_native'].get('1'))} | "
                     f"{_arrow(a['agreement_native'].get('2'), b['agreement_native'].get('2'))} | "
                     f"{_arrow(a['agreement_decision'].get('1'), b['agreement_decision'].get('1'))} | "
                     f"{_arrow(a['agreement_decision'].get('2'), b['agreement_decision'].get('2'))} | "
                     f"{cr(a, '1')} → {cr(b, '1')} | {cr(a, '2')} → {cr(b, '2')} |")
        for arm, both in per.items():
            if "relations" not in both["round2"]:
                continue
            cols = list(reversed(RELATIONS)) + ["opposite", "unsure"]
            L += ["", f"{arm} against {both['round1']['rubric']}, the relations named and the wider of a \"contains\" "
                  "(round 1 → round 2):", "",
                  "| model | pass | " + " | ".join(cols) + " | wider: target | wider: listed | missing | not target or "
                  "listed | wider given with another relation |", "|---|---|" + "---|" * (len(cols) + 5)]
            for m in models:
                for p in sorted(set(both["round1"]["relations"].get(m, {})) | set(both["round2"]["relations"].get(m, {}))):
                    x1, x2 = both["round1"]["relations"].get(m, {}).get(p), both["round2"]["relations"].get(m, {}).get(p)
                    if not x1 or not x2:
                        continue
                    L.append(f"| {sm(m)} | {p} | " + " | ".join(f"{x1['counts'].get(c, 0)} → {x2['counts'].get(c, 0)}"
                                                              for c in cols)
                             + f" | {x1['wider']['target']} → {x2['wider']['target']} | {x1['wider']['listed']} → "
                             f"{x2['wider']['listed']} | {x1['wider']['missing']} → {x2['wider']['missing']} | "
                             f"{x1['wider']['invalid']} → {x2['wider']['invalid']} | {x1['wider_with_other_relation']} → "
                             f"{x2['wider_with_other_relation']} |")
            L.append("")
            for m, x2 in both["round2"].get("wider_between_passes", {}).items():
                x1 = both["round1"].get("wider_between_passes", {}).get(m, {})
                L.append(f"- {sm(m)}, pass 1 against pass 2: \"contains\" in both {x1.get('n_both_contains', '–')} → "
                         f"{x2['n_both_contains']}, the same wider {x1.get('same', '–')} → {x2['same']}, the other "
                         f"{x1.get('different', '–')} → {x2['different']}")
            for m, per_pass in both["round2"].get("wider_between_models", {}).items():
                for p, x2 in per_pass.items():
                    x1 = both["round1"].get("wider_between_models", {}).get(m, {}).get(p, {})
                    L.append(f"- {sm(m)} against {sm(ref)}, pass {p}: \"contains\" for both "
                             f"{x1.get('n_both_contains', '–')} → {x2['n_both_contains']}, the same wider "
                             f"{x1.get('same', '–')} → {x2['same']}, the other {x1.get('different', '–')} → "
                             f"{x2['different']}")
    L += ["", "### Round 2's answers behind the counts (every pair sent, in pair order)", ""]
    for arm, ex in r2["examples"].items():
        L += [f"#### {arm} ({RUBRICS[arm]['name']})", "",
              f"Answers at 2 whose reason describes a containment: {len(ex['forward'])} "
              f"({len({x['pair_id'] for x in ex['forward']})} pairs); the first {ROUND2_EXAMPLES} pairs:", ""]
        for _, rows in _first_pairs(ex["forward"], ROUND2_EXAMPLES):
            x = rows[0]
            L.append(f"- {_label(corpus, x['target'])} / {_label(corpus, x['listed'])} "
                     f"({'subset' if x['in_subset'] else 'control'}, {x['group']}): "
                     + "; ".join(f"{sm(y['model'])} pass {y['pass']}, {y['value']}: \"{y['reason']}\"" for y in rows))
        if not ex["forward"]:
            L.append("- none")
        L += ["", f"Pairs the two models put on different sides of {cut}: {len({x['pair_id'] for x in ex['crossings']})} "
              f"({len(ex['crossings'])} crossings over the passes); the first {ROUND2_EXAMPLES}:", ""]
        for _, rows in _first_pairs(ex["crossings"], ROUND2_EXAMPLES):
            x = rows[0]
            L.append(f"- {_label(corpus, x['target'])} / {_label(corpus, x['listed'])} "
                     f"({'subset' if x['in_subset'] else 'control'}, {x['group']}): "
                     + "; ".join(f"pass {y['pass']}, {sm(y['first_model'])} {y['first']}: \"{y['first_reason']}\" / "
                                 f"{sm(y['second_model'])} {y['second']}: \"{y['second_reason']}\"" for y in rows))
        if not ex["crossings"]:
            L.append("- none")
        if ex["reverse"]:
            L += ["", f"Answers at 3 whose reason describes a two-sided overlap: {len(ex['reverse'])}; the first "
                  f"{ROUND2_EXAMPLES} pairs:", ""]
            for _, rows in _first_pairs(ex["reverse"], ROUND2_EXAMPLES):
                x = rows[0]
                L.append(f"- {_label(corpus, x['target'])} / {_label(corpus, x['listed'])} "
                         f"({'subset' if x['in_subset'] else 'control'}, {x['group']}): "
                         + "; ".join(f"{sm(y['model'])} pass {y['pass']}, {y['value']}: \"{y['reason']}\"" for y in rows))
        L.append("")
    return L


#: How round 3's tables name the versions and the populations, and how many pairs of Opus's changes they quote.
ROUND3_VERSION_NAMES = {"v4": "version 4", "A2": "A2", "v6": "version 6"}
ROUND3_POPULATION_TITLES = {"all": "Every pair", "nearest": "The nearest pairs",
                            "round2": "Round 2's pairs (those A2 was sent)"}
ROUND3_EXAMPLES = 6


def _fmt_summary(x, fmt: str) -> str:
    if x is None:
        return "–"
    if fmt == "pct":
        return f"{100 * x:.1f}%"
    return f"{x:.1f}" if isinstance(x, float) and not float(x).is_integer() else f"{int(round(x))}"


def round3_markdown(r3: Mapping, corpus: Mapping, sm) -> list[str]:
    """Round 3's tables (:func:`analyse_round3`): the summary first, then the parse rates, the cache and the
    spend, each population's figures for every version measured on it, Roger's marks, and the pairs where
    Opus's answer under version 6 changes the rule's decision against version 4, reasons in full."""
    vn = lambda k: ROUND3_VERSION_NAMES.get(k, k)  # noqa: E731
    cut, ref = r3["cutoff"], r3["reference"]
    models = r3["models"]
    others = [m for m in models if m != ref]
    vers = r3["versions"]

    def vdesc(k):
        v = vers.get(k) or {}
        return (f"{vn(k)}: rubric {v.get('rubric')} version{'s' if len(v.get('rubric_versions') or []) > 1 else ''} "
                f"{', '.join(str(x) for x in v.get('rubric_versions') or []) or '?'}, {v.get('form')} form, run "
                f"`{v.get('run')}`")
    L = ["", "## Round 3: rubric A version 6, one pair per call", "",
         "Versions compared on the same pairs: " + "; ".join(vdesc(k) for k in vers) + ".  Version 6 went out one pair "
         "per call, and its second pass sent the identical prompts (there is no list to reorder), so the agreement "
         "between its passes is sampling noise alone; version 4's and A2's second passes reshuffled their lists, so "
         "their like-for-like figure is the one on the pairs whose prompt came out identical (a call of one trait, or "
         "a list that shuffled into the same order).  Decision scale: rubric A's own; cut-off "
         f"{cut}.  Crossings, flips and shares count every pair of the population named.  M3's rule: "
         f"{sm(r3['first_line'])} reads every pair; above {cut} is cut, below it (or \"opposite\") kept; at {cut} (or "
         f"\"unsure\") the pair goes to {sm(r3['second_opinion'])}, and is kept if {sm(r3['second_opinion'])} reads it "
         f"under {cut}.", ""]
    # ---- summary
    rows = r3.get("summary") or []
    if rows:
        L += ["### Summary: version 4 against version 6", "",
              "Verdict \"same\" when the two differ by no more than the noise band: for a figure read in each pass, the "
              "difference between version 4's two passes (round 1's passes); for a figure that already compares the "
              "passes (self-consistency, the rule's flips), two binomial standard errors of version 4's figure; never "
              "less than one pair.  Figures read in each pass are the means of the two passes.  \"higher\" / \"lower\" "
              "where neither direction is better.", "",
              "| figure | model | version 4 | version 6 | noise band | verdict |", "|---|---|---|---|---|---|"]
        for x in rows:
            who = sm(x["model"]) if x["model"] in SHORT else x["model"]
            n = x.get("n")
            nn = (f" ({n[0]})" if n and n[0] is not None else ""), (f" ({n[1]})" if n and n[1] is not None else "")
            L.append(f"| {x['figure']} | {who} | {_fmt_summary(x['v4'], x['format'])}{nn[0]} | "
                     f"{_fmt_summary(x['v6'], x['format'])}{nn[1]} | {_fmt_summary(x['band'], x['format'])} | "
                     f"{x['verdict'] or '–'} |")
        L.append("")
    # ---- parse, cache, spend
    L += ["### Parse rates, the cache and the spend", "",
          "| version | model | pass | parsed at the first attempt | parsed in the end |", "|---|---|---|---|---|"]
    for k, per in r3.get("parse", {}).items():
        for v in per.values():
            first = f"{v['first_ok']} / {v['first_total']}" if v.get("first_total") is not None else "–"
            L.append(f"| {vn(k)} | {sm(v['model'])} | {v['pass']} | {first} | {v['ok']} / {v['total']} |")
    notes = r3.get("format_notes", {}).get("v6") or {}
    if notes:
        L += ["", "Version 6's answer format (first attempts; in the end): an answer wrapped in a results list (the "
              "list form's shape), extra keys, the answer before the reason, and self-corrections (more than one "
              "answer object):", "", "| model | pass | calls | wrapped | extra keys | answer before reason | "
              "self-corrections |", "|---|---|---|---|---|---|---|"]
        for v in notes.values():
            f, z = v.get("first") or {}, v.get("final") or {}
            keys = ", ".join(f"{k} {n}" for k, n in (f.get("extra_key_names") or {}).items())
            L.append(f"| {sm(v['model'])} | {v['pass']} | {f.get('n')} | {f.get('wrapped')}; {z.get('wrapped')} | "
                     f"{f.get('extra_keys')}{f' ({keys})' if keys else ''}; {z.get('extra_keys')} | "
                     f"{f.get('not_reason_first')}; {z.get('not_reason_first')} | {f.get('self_corrections')}; "
                     f"{z.get('self_corrections')} |")
    cache = r3.get("cache", {})
    if cache:
        L += ["", "The prompt cache and the spend, from the usage each record holds (every answered request, re-asks "
              "included).  \"Charged\" is what the usage records charge (cache writes 1.25x, reads 0.1x the input "
              "price, as `llm.billed_usage` does for every model); \"published\" reads Opus 5.5's cache at its "
              "published 0.05x; \"uncached\" puts every input token at the full price.", "",
              "| version | model | requests | reading the cache | writing it | input tokens: uncached / written / read | "
              "share of input read from the cache | charged | published | uncached | saved (charged; published) | "
              "per pair answered |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k, per in cache.items():
            for m, c in per.items():
                pp = (r3.get("spend_per_pair", {}).get(k) or {}).get(m) or {}
                L.append(f"| {vn(k)} | {sm(m)} | {c['requests']} | {c['reading']} ({_pct(c['hit_rate'])}) | {c['writing']} | "
                         f"{c['input_tokens']:,} / {c['cache_write_tokens']:,} / {c['cache_read_tokens']:,} | "
                         f"{_pct(c['read_share'])} | ${c['charged_usd']:.4f} | ${c['published_usd']:.4f} | "
                         f"${c['uncached_usd']:.4f} | ${c['saved_usd']:.4f}; ${c['saved_published_usd']:.4f} | "
                         f"{'$%.5f' % pp['per_pair_usd'] if pp.get('per_pair_usd') is not None else '–'} "
                         f"({pp.get('answers', '–')}) |")
    # ---- populations
    for pop, entry in r3.get("populations", {}).items():
        vs = entry["versions"]
        if not vs:
            continue
        L += ["", f"### {ROUND3_POPULATION_TITLES.get(pop, pop)}: {entry['n_pairs']} pairs", "",
              "By group: " + ", ".join(f"{g} {n}" for g, n in entry["by_group"].items()) + ".  Versions measured here: "
              + ", ".join(vn(k) for k in vs) + ".", "",
              "Self-consistency, pass 1 against pass 2 (exact over every answer; within one and kappa, quadratic, on "
              f"the pairs both passes scored; flips: pairs on different sides of {cut} in the two passes).  The last "
              "columns: the pairs whose prompt was identical in both passes (all of version 6's).", "",
              "| version | model | both answered | exact | within one | kappa | exact (decision) | flips at "
              f"{cut} | identical prompts: pairs | exact | within one | kappa | flips |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k, f in vs.items():
            for m, c in f["self_consistency"].items():
                i = c["identical"]
                L.append(f"| {vn(k)} | {sm(m)} | {c['n']} | {_pct(c['exact'])} | {_pct(c['within_one'])} | "
                         f"{_f(c['kappa'])} | {_pct(c['exact_decision'])} | {c['crossings']} of {c['cutoff_n']} | "
                         f"{i['n']}{' (all)' if i.get('all_pairs') else ''} | {_pct(i['exact'])} | "
                         f"{_pct(i['within_one'])} | {_f(i['kappa'])} | {i['crossings']} of {i['cutoff_n']} |")
        like = [(k, m, c["on_v4_identical"]) for k, f in vs.items() for m, c in f["self_consistency"].items()
                if c.get("on_v4_identical")]
        if like:
            L += ["", f"Like for like, on the same pairs: the {like[0][2]['n']} pairs of this population whose prompt was "
                  "identical in both of version 4's passes (one-trait calls, and lists that shuffled into the same "
                  "order), every version on those pairs:", "",
                  "| version | model | pairs | exact | within one | kappa | exact (decision) | flips at "
                  f"{cut} |", "|---|---|---|---|---|---|---|---|"]
            for k, m, c in like:
                L.append(f"| {vn(k)} | {sm(m)} | {c['n']} | {_pct(c['exact'])} | {_pct(c['within_one'])} | "
                         f"{_f(c['kappa'])} | {_pct(c['exact_decision'])} | {c['crossings']} of {c['cutoff_n']} |")
        L += ["", "Where the passes differ, by the two answers:", ""]
        for k, f in vs.items():
            for m, c in f["self_consistency"].items():
                L.append(f"- {vn(k)}, {sm(m)}: " + (", ".join(f"{a} {n}" for a, n in c["flips_native"].items()) or "none"))
        for m in others:
            L += ["", f"{sm(m)} against {sm(ref)} (crossings: pairs on different sides of {cut}, split by which model "
                  "covers):", "",
                  "| version | pass | both answered | exact | within one | kappa | crossings at "
                  f"{cut} | {sm(ref)} covers only | {sm(m)} covers only |", "|---|---|---|---|---|---|---|---|---|"]
            for k, f in vs.items():
                for p, c in (f["between_models"].get(m) or {}).items():
                    L.append(f"| {vn(k)} | {p} | {c['n']} | {_pct(c['exact'])} | {_pct(c['within_one'])} | "
                             f"{_f(c['kappa'])} | {c['crossings']} of {c['cutoff_n']} | {c['first_only']} | "
                             f"{c['second_only']} |")
        if entry.get("against_v4"):
            L += ["", f"Against version 4, the same model and pass (crossings: on different sides of {cut}):", "",
                  "| version | model | pass | both answered | exact | within one | kappa | crossings | version 4 covers "
                  "only | this version covers only |", "|---|---|---|---|---|---|---|---|---|---|"]
            for k, per in entry["against_v4"].items():
                for m, pp in per.items():
                    for p, c in pp.items():
                        L.append(f"| {vn(k)} | {sm(m)} | {p} | {c['n']} | {_pct(c['exact'])} | {_pct(c['within_one'])} | "
                                 f"{_f(c['kappa'])} | {c['crossings']} of {c['cutoff_n']} | {c['first_only']} | "
                                 f"{c['second_only']} |")
        L += ["", f"At {cut} or more:", "", "| version | model | pass 1 | pass 2 |", "|---|---|---|---|"]
        for k, f in vs.items():
            for m, per in f["coverage"].items():
                L.append(f"| {vn(k)} | {sm(m)} | " + " | ".join(
                    _of(per[p]["covered"], per[p]["n"], per[p]["share"]) if p in per else "–" for p in ("1", "2")) + " |")
        if pop != "nearest":
            L += ["", "Known groups on the decision scale: mean of the numeric answers / share at 3 or more / share "
                  "\"opposite\", pass 1; pass 2.", "", "| group | n | " + " | ".join(
                      f"{vn(k)}, {sm(m)}" for k, f in vs.items() for m in f["groups"]) + " |",
                  "|---|---|" + "---|" * sum(len(f["groups"]) for f in vs.values())]
            for g in GROUPS:
                cells, n = [], None
                for k, f in vs.items():
                    for m, per in f["groups"].items():
                        xs = [per[p].get(g) for p in ("1", "2") if p in per]
                        if any(xs):
                            n = n or next(x for x in xs if x)["n"]
                        cells.append("; ".join(f"{_f(x['mean'])} / {_pct(x['share_3_plus'])} / {_pct(x['opposite'])}"
                                               if x else "–" for x in xs))
                if n:
                    L.append(f"| {g} | {n} | " + " | ".join(cells) + " |")
        rule_rows = [(k, f["rule"]) for k, f in vs.items() if f.get("rule")]
        if rule_rows:
            L += ["", f"M3's rule ({sm(r3['first_line'])} first, {sm(r3['second_opinion'])} on the {cut}s), per pass:", "",
                  "| version | pass | decided | escalated | rescued | cut | of which directly | kept though "
                  f"{sm(r3['second_opinion'])} reads {cut}+ | decision differs from version 4 (keep to cut / cut to keep) |",
                  "|---|---|---|---|---|---|---|---|---|"]
            for k, rs in rule_rows:
                ag = entry.get("rule_against_v4", {}).get(k, {})
                for p, x in rs["per_pass"].items():
                    a = ag.get(p)
                    against = f"{a['differ']} of {a['n']} ({a['keep_to_cut']} / {a['cut_to_keep']})" if a else "–"
                    L.append(f"| {vn(k)} | {p} | {x['n']} | {x['escalated']} | {x['rescued']} | {x['cut']} | "
                             f"{x['cut_direct']} | {x['kept_though_second']} | {against} |")
            L += [""] + [f"- {vn(k)}: the rule's decision differs between the passes on {rs['flips']['differ']} of "
                         f"{rs['flips']['n']} pairs" for k, rs in rule_rows if rs.get("flips")]
        L += ["", "Slips (round 1's patterns; reasons matched case-insensitively): 2s whose reason describes a containment, "
              "and the same less the reasons that say neither implies the other; 3s whose reason describes a two-sided "
              "overlap (round 2's pattern, which also matches a two-sided difference of emphasis, as line 3 allows), the "
              "same counting \"neither implies the other\" too, and 3s whose reason states line 2 in its own words "
              "(\"each adds something\", \"neither implies the other\"; patterns in `summary.json`).", "",
              "| version | model | pass | 2s | containment reason | discounting \"neither implies\" | 3s | two-sided "
              "reason | or \"neither implies\" | line 2's words |", "|---|---|---|---|---|---|---|---|---|---|"]
        for k, f in vs.items():
            for m, per in f["slips"].items():
                for p, s in per.items():
                    L.append(f"| {vn(k)} | {sm(m)} | {p} | {s['n_2']} | {_of(s['forward'], s['n_2'], s['forward_share'])} | "
                             f"{_of(s['forward_discounted'], s['n_2'], s['forward_discounted_share'])} | {s['n_3']} | "
                             f"{_of(s['reverse'], s['n_3'], s['reverse_share'])} | "
                             f"{_of(s['reverse_wide'], s['n_3'], s['reverse_wide_share'])} | "
                             f"{_of(s['reverse_explicit'], s['n_3'], s['reverse_explicit_share'])} |")
        esc_rows = [(k, f["second_on_escalated"]) for k, f in vs.items() if f.get("second_on_escalated")]
        if esc_rows:
            so = sm(r3["second_opinion"])
            L += ["", f"{so} on the pairs the rule escalates ({sm(r3['first_line'])} at {cut}): its answers on them in that "
                  f"pass, and on those it answered in both passes, how often alike:", "",
                  f"| version | escalated in | pairs | {so}'s answers | answered in both passes | same answer | same side "
                  f"of {cut} |", "|---|---|---|---|---|---|---|"]
            for k, x in esc_rows:
                for p, y in x["per_pass"].items():
                    L.append(f"| {vn(k)} | pass {p} | {y['n']} | " + (", ".join(f"{a} {n}" for a, n in y["answers"].items())
                                                                       or "–")
                             + f" | {y['n_both_passes']} | {_f(y['same'])} | {_f(y['same_side'])} |")
                y = x["any_pass"]
                L.append(f"| {vn(k)} | either pass | {y['n']} | – | {y['n_both_passes']} | {_f(y['same'])} | "
                         f"{_f(y['same_side'])} |")
    # ---- Roger's marks
    mk = r3.get("marks") or {}
    if mk.get("items"):
        sources = [(k, v) for k, v in mk.items() if k != "items"]
        label = {"v4_test1": "version 4 (overlap_test_1)", "v4_pass1": "version 4 (overlap_arms_1, pass 1)",
                 "v4_pass2": "version 4 (overlap_arms_1, pass 2)", "v6_pass1": "version 6, pass 1",
                 "v6_pass2": "version 6, pass 2"}
        L += ["", "### Agreement with Roger's 30 marks", "",
              "His leaning per item, read by hand from the sheet, with the alternative he named on five items.  Exact "
              "counts every answer (\"opposite\" included); within one, the items where both are numbers.", "",
              "| answers | model | items | exact | within one | leaning or alternative |", "|---|---|---|---|---|---|"]
        for k, per in sources:
            for m, x in per.items():
                L.append(f"| {label.get(k, k)} | {sm(m)} | {x['n']} | {_of(x['exact'], x['n'], x['exact_share'])} | "
                         f"{_of(x['within_one'], x['n_numeric'], x['within_one_share'])} | "
                         f"{_of(x['leaning_or_alternative'], x['n'], x['leaning_or_alternative_share'])} |")
        cols = [(k, m) for k, per in sources for m in per]
        L += ["", "Per item:", "", "| item | target / listed | Roger (alternative) | " + " | ".join(
            f"{label.get(k, k)}, {sm(m)}" for k, m in cols) + " |", "|---|---|---|" + "---|" * len(cols)]
        for i, it in enumerate(mk["items"]):
            t, s = it["pair_id"].split(":", 1)[1].split(">", 1) if ":" in it["pair_id"] else ("?", "?")
            alt = f" ({it['alternative']})" if it.get("alternative") is not None else ""
            cells = [str(_f((mk[k][m]["items"][i]).get("value"))) for k, m in cols]
            L.append(f"| {it['item']} | {_label(corpus, t)} / {_label(corpus, s)} | {it['leaning']}{alt} | "
                     + " | ".join(cells) + " |")
    # ---- Opus's changes
    oc = r3.get("opus_changes") or {}
    if oc:
        so, fl = sm(r3["second_opinion"]), sm(r3["first_line"])
        L += ["", f"### Where {so}'s answer under version 6 changes the rule's decision against version 4", "",
              f"Pairs whose {so} answers under the two versions fall on different sides of {cut} while {fl} sends the pair "
              f"to {so} under either version (so that, {fl}'s answer held, {so}'s change flips the decision); in pair "
              f"order.  \"{so} changes side\" counts every pair where its answers cross {cut}, escalated or not.", ""]
        for p, x in oc.items():
            L.append(f"- pass {p}: {x['n']} pairs ({so} changes side on {x['second_changes_side']})")
        first = oc.get("1") or next(iter(oc.values()))
        L += ["", f"The first {ROUND3_EXAMPLES} in pass 1, both {so} reasons in full:", ""]
        for x in first["pairs"][:ROUND3_EXAMPLES]:
            L.append(f"- **{_label(corpus, x['target'])} / {_label(corpus, x['listed'])}** ({x['group']}): {fl} "
                     f"version 4 {x['first_base']}, version 6 {x['first_new']}; the rule: version 4 {x['decision_base']}, "
                     f"version 6 {x['decision_new']}.  {so} version 4, {x['second_base']}: \"{x['second_base_reason']}\"  "
                     f"{so} version 6, {x['second_new']}: \"{x['second_new_reason']}\"")
        rest = first["pairs"][ROUND3_EXAMPLES:]
        if rest:
            L += ["", "The others in pass 1 (" + so + " version 4 → version 6): " + "; ".join(
                f"{_label(corpus, x['target'])} / {_label(corpus, x['listed'])} {x['second_base']} → {x['second_new']}"
                for x in rest)]
        if not first["pairs"]:
            L.append("- none")
    L.append("")
    return L


# --------------------------------------------------------------------------- cost

def tokenizer_factor(model: str) -> float:
    m = model.lower()
    return NEW_TOKENIZER_FACTOR if any(f in m for f in NEW_TOKENIZER_FRAGMENTS) else 1.0


def estimate(calls: Sequence[Call], corpus: Mapping, rubrics: Mapping[str, Mapping], models: Sequence[str],
             rubric_keys: Optional[Sequence[str]] = None, *, pass_no: Optional[int] = None) -> Estimate:
    """Calls x mean (input, output) tokens per (rubric, model), at each model's live rates, for
    ``rubric_keys`` (default: every rubric in ``rubrics``).  Output tokens per listed trait are the
    rubric's ``out_per_row`` (D's relation word and ``wider``, E's named kind) or
    :data:`OUT_PER_ROW_TOKENS`.  A later pass sends the same text in another order, so it costs the
    same; ``pass_no`` only labels the line.  A single-form rubric is estimated on one call per pair
    (:func:`stage_calls`), every input token at the uncached rate (an upper bound: the cached rubric is
    read at a tenth of it; :func:`cached_estimate_usd`)."""
    est = Estimate()
    if not calls:
        return est
    which = f", pass {pass_no}" if pass_no is not None else ""
    for m in models:
        f = tokenizer_factor(m)
        for r in (list(rubrics) if rubric_keys is None else rubric_keys):
            in_tok, out_tok, n = _stage_tokens(calls, corpus, rubrics[r], r, f)
            form = rubrics[r].get("form") or "list"
            est.add(f"rubric {r} ({RUBRICS[r]['name']}{', one pair per call' if form == 'single' else ''}) on "
                    f"{SHORT.get(m, m)}{which}", m, n, in_tok, out_tok)
    return est


def _stage_tokens(calls: Sequence[Call], corpus: Mapping, rubric: Mapping, key: str, factor: float
                  ) -> tuple[int, int, int]:
    """``(mean input tokens, mean output tokens, calls)`` of a stage of ``rubric`` over ``calls``."""
    form = rubric.get("form") or "list"
    sent = stage_calls(calls, form)
    users = [render_single(c, corpus) if form == "single" else render_user(c, corpus) for c in sent]
    mean_rows = float(np.mean([len(c.listed) for c in sent]))
    per_row = RUBRICS[key].get("out_per_row", OUT_PER_ROW_TOKENS)
    in_tok = int(round(np.mean([len(rubric["text"]) + len(u) for u in users]) / CHARS_PER_TOKEN * factor))
    out_tok = int(round((OUT_BASE_TOKENS + per_row * mean_rows) * factor))
    return in_tok, out_tok, len(sent)


def cached_estimate_usd(calls: Sequence[Call], corpus: Mapping, rubrics: Mapping[str, Mapping], models: Sequence[str],
                        rubric_keys: Optional[Sequence[str]] = None, *, writes_per_stage: int = DEFAULT_CONCURRENCY
                        ) -> float:
    """The estimate with the rubric read from the prompt cache on the stages that mark it
    (:func:`default_cache_system`): the rubric's tokens at the read factor the usage records charge
    (``llm.CACHE_READ_FACTOR``) on every call but ``writes_per_stage`` (the concurrent first calls, which
    write it at ``llm.CACHE_WRITE_FACTOR``); the other stages as :func:`estimate`."""
    from assistant_axis.judge_pricing import price_for_model

    from .llm import CACHE_READ_FACTOR, CACHE_WRITE_FACTOR
    total = 0.0
    for m in models:
        f = tokenizer_factor(m)
        rate_in, rate_out = price_for_model(m)
        for r in (list(rubrics) if rubric_keys is None else rubric_keys):
            if not calls:
                continue
            in_tok, out_tok, n = _stage_tokens(calls, corpus, rubrics[r], r, f)
            if default_cache_system(rubrics[r].get("form") or "list"):
                sys_tok = len(rubrics[r]["text"]) / CHARS_PER_TOKEN * f
                w = min(n, writes_per_stage)
                prompt = n * (in_tok - sys_tok) + sys_tok * (w * CACHE_WRITE_FACTOR + (n - w) * CACHE_READ_FACTOR)
            else:
                prompt = n * in_tok
            total += (prompt * rate_in + n * out_tok * rate_out) / 1e6
    return total


# --------------------------------------------------------------------------- inputs

_DM_LINK = re.compile(r"\]\(\.\./\.\./traits/instructions/([a-z0-9_]+)\.json\)")


def parse_drop_or_merge(text: str) -> list[tuple[str, str]]:
    """The (trait, nearest) pairs of the table "Partners excluded (the real candidates)" in
    ``drop_or_merge.md`` (the second table lists recorded clean pairs, expected to be close)."""
    if "## Partners excluded" not in text:
        raise ValueError("drop_or_merge.md: no 'Partners excluded' section")
    section = text.split("## Partners excluded", 1)[1].split("\n## ", 1)[0]
    out = []
    for line in section.splitlines():
        if line.startswith("| ["):
            stems = _DM_LINK.findall(line)
            if len(stems) >= 2:
                out.append((stems[0], stems[1]))
    return out


@dataclass
class Inputs:
    corpus: dict
    emb_stems: list
    Z: np.ndarray
    persona: dict
    persona_info: dict
    labelled: list
    dm_pairs: list
    partner: dict
    settings: dict
    paths: dict


def load_inputs(repo_root: Path, *, metric_config_path: Path, cache_dir: Path, vectors_dir: Path,
                labelled_path: Path, dm_path: Path, persona_cache_dir: Optional[Path] = None) -> Inputs:
    """The corpus, its rows in the covered space from the cached embeddings (nothing is embedded: a
    text missing from the cache is an error), the persona vectors of the traits, the labelled pairs,
    the drop-or-merge pairs and the recorded clean-pair partners."""
    from assistant_axis.arrangements import load_corpus_arrangements

    from . import contrast as CT
    from . import embed as EM
    from . import labels as LB
    from . import persona as PS
    from .metric_config import MetricConfig
    from .representation import represent
    from .space import fit_space

    repo_root = Path(repo_root)
    cfg = MetricConfig.load(metric_config_path)
    cov = cfg.covered
    rep, variant, metric = cov["representation"], cov["space"]["variant"], cov["metric"]
    if metric != "cos":
        raise ValueError(f"covered.metric is {metric!r}; this test computes cosines only")
    live = cfg.live_model
    if live["arm"] != "openai":
        raise ValueError(f"live model arm {live['arm']!r}: this test reads the OpenAI embedding cache")
    corpus = CT.load_corpus_texts(repo_root / "data")
    stems = sorted(corpus)
    texts = [represent(corpus[s]["label"], corpus[s]["description"], rep) for s in stems]
    embedder = EM.OpenAIEmbedder(live["model_id"])
    cache = EM.EmbeddingCache(cache_dir)
    found, missing = cache.lookup(embedder.tag, texts)
    if missing:
        raise RuntimeError(f"{len(missing)} corpus texts ({rep}) are not in the embedding cache {cache.path(embedder.tag)} "
                           f"(first: {stems[missing[0]]}); embed them with calibrate_metric.py first")
    E = EM.normalize_rows(np.stack([found[i] for i in range(len(stems))]))
    Z = fit_space(E, variant).apply(E)
    ps = PS.load_persona_space(vectors_dir, cache_dir=persona_cache_dir)
    persona = {}
    for s, k, row in zip(ps["stems"], ps["kinds"], ps["M"]):
        if k == "traits" and s in corpus:
            persona[s] = row / np.linalg.norm(row)
    n_trait_vectors = sum(k == "traits" for k in ps["kinds"])
    lp = LB.load(labelled_path)
    dm_pairs = parse_drop_or_merge(Path(dm_path).read_text(encoding="utf-8"))
    partner = {}
    for s, rec in load_corpus_arrangements(repo_root / "data", "traits").items():
        for a in rec.arrangements:
            if a.kind == "pair" and len(a.members) == 2 and s in a.members:
                partner[s] = a.members[0] if a.members[1] == s else a.members[1]
    settings = {"config_version": cfg.config_version, "model": live["model_id"], "cache_tag": embedder.tag,
                "representation": rep, "variant": variant, "metric": metric, "n_corpus": len(stems)}
    persona_info = {"n_entities": ps["n"], "n_trait_vectors": n_trait_vectors, "n_traits_in_corpus": len(persona),
                    "trait_vectors_not_in_corpus": sorted(s for s, k in zip(ps["stems"], ps["kinds"])
                                                          if k == "traits" and s not in corpus),
                    "shear_applied": ps["shear_applied"], "shear_L": ps.get("shear_L"), "shear_note": ps["shear_note"],
                    "slot": ps["slot"], "layer": ps["layer"], "mean_over": ps["mean_over"]}
    paths = {"metric_config": Path(metric_config_path), "embedding_cache": cache.path(embedder.tag),
             "labelled_pairs": Path(labelled_path), "drop_or_merge": Path(dm_path),
             "persona_cache": Path(persona_cache_dir or repo_root / "data" / "candidates" / "cache")
             / f"persona_s{ps['slot']}_l{ps['layer']}.npz"}
    return Inputs(corpus=corpus, emb_stems=stems, Z=Z, persona=persona, persona_info=persona_info,
                  labelled=list(lp.pairs), dm_pairs=dm_pairs, partner=partner, settings=settings, paths=paths)


# --------------------------------------------------------------------------- Roger's marks

def draw_marks(pair_set: PairSet, *, seed: int = 0, quotas: Mapping[str, int] = MARKS_QUOTAS) -> list[Pair]:
    """A blinded sample for Roger: ``quotas`` pairs per group (seeded; one occurrence per unordered
    pair; a short group is made up from the nearest pairs), in a seeded random order."""
    rng = random.Random(f"overlap-test:{seed}:marks")
    taken: set = set()
    chosen: list[Pair] = []
    short = 0
    for g, n in quotas.items():
        pool = sorted((p for p in pair_set.pairs if p.group == g), key=lambda p: p.pair_id)
        rng.shuffle(pool)
        got = 0
        for p in pool:
            k = _ukey(p.target, p.listed)
            if got >= n:
                break
            if k in taken:
                continue
            taken.add(k)
            chosen.append(p)
            got += 1
        short += n - got
    if short:
        pool = sorted((p for p in pair_set.pairs if p.group == NEAREST), key=lambda p: p.pair_id)
        rng.shuffle(pool)
        for p in pool:
            if short == 0:
                break
            k = _ukey(p.target, p.listed)
            if k not in taken:
                taken.add(k)
                chosen.append(p)
                short -= 1
    rng.shuffle(chosen)
    return chosen


def _trait_link(stem: str, label: str, rel_prefix: str) -> str:
    return f"[{label}]({rel_prefix}data/traits/instructions/{stem}.json)"


def marks_sheet(items: Sequence[Pair], corpus: Mapping, *, rubric_text: str, key_link: str, run_id: str,
                rel_prefix: str = "../../") -> str:
    """The blinded sheet: the target and the listed trait with their descriptions, and a line for
    Roger's answer on rubric A's scale; no group, model, score or cosine."""
    head = [
        "# Overlap test: 30 pairs for Roger's marks (blinded)", "",
        f"For the pre-pilot test of the M3 overlap rubrics (run `{run_id}`).  Each item is one existing trait "
        "standing in for a candidate (the target) and one existing trait (the listed trait).  Please give each "
        "item the answer you would give on rubric A's scale, below, as the model was asked to: how similar is the "
        "listed trait's concept to the target's?  Write it after \"Your answer\": a number from 0 to 4, "
        "`opposite` or `unsure`.  Leave a line blank to skip an item.", "",
        "Nothing here says where a pair came from or what any model answered; your marks are compared with the "
        f"models' answers afterwards (the key is [{key_link.rsplit('/', 1)[-1]}]({key_link}); please do not open "
        "it before marking).", "",
        "Rubric A's scale, as the model reads it:", "",
        *[f"> {ln}" for ln in scale_lines(rubric_text)], "",
    ]
    body = []
    for i, p in enumerate(items, 1):
        t, s = corpus[p.target], corpus[p.listed]
        body += [f"### {i}.", "",
                 f"**Target:** {_trait_link(p.target, t['label'], rel_prefix)}: {t['description']}", "",
                 f"**Listed trait:** {_trait_link(p.listed, s['label'], rel_prefix)}: {s['description']}", "",
                 "Your answer (0 / 1 / 2 / 3 / 4 / opposite / unsure): ", ""]
    return "\n".join(head + body).rstrip("\n") + "\n"


def marks_key(items: Sequence[Pair], *, run_id: str, seed: int, sheet: str) -> dict:
    return {"run_id": run_id, "seed": seed, "sheet": sheet, "quotas": dict(MARKS_QUOTAS), "made_at": utc_now(),
            "items": [{"item": i, "pair_id": p.pair_id, "call_id": p.call_id, "target": p.target, "listed": p.listed,
                       "group": p.group} for i, p in enumerate(items, 1)]}


def decode_marks(sheet_text: str, key: Mapping) -> dict:
    """Roger's answers read back from the sheet and joined with the key: per item the answer (an integer
    0-4, ``opposite``, ``unsure``, ``None`` when blank) or ``invalid`` with what was written."""
    marks: dict[int, str] = {}
    cur = None
    for line in sheet_text.splitlines():
        m = MARKS_ITEM_RE.match(line)
        if m:
            cur = int(m.group(1))
            continue
        m = MARKS_ANSWER_RE.match(line)
        if m and cur is not None:
            marks[cur] = m.group(1).strip()
    items = []
    counts = Counter()
    for it in key["items"]:
        raw = marks.get(it["item"], "")
        raw_clean = raw.strip().strip("`*").strip()
        val = answer_value(raw_clean, RUBRICS["A"]["categories"]) if raw_clean else None
        status = "blank" if not raw_clean else ("ok" if val is not None else "invalid")
        counts[status] += 1
        items.append({**it, "written": raw, "value": val, "status": status})
    return {"items": items, "counts": dict(counts)}


def compare_marks(decoded: Mapping, answers: Mapping[tuple[str, str], Mapping], *, models: Sequence[str] = MODELS) -> dict:
    """Each model's rubric-A answers against Roger's marks: exact, within one, weighted kappa (as
    :func:`agreement`, with Roger as the reference)."""
    roger = {it["pair_id"]: {"value": it["value"]} for it in decoded["items"] if it["status"] == "ok"}
    return {m: agreement(roger, answers.get(("A", m), {})) for m in models if answers.get(("A", m))}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
