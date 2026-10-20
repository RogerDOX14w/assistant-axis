"""Humanize: every alignment-sweep trait rewritten in its closest human phrasing (Roger, 2026-10-20).

Roger's marks on the label-fit survey (``data/candidates/label_fit_survey/2026-10-17/readout.md``) found the sweep's
836 rows framed for an AI ("acts against its developer"; glosses about "the user", "the lab that built it"), glosses
narrower than their labels, and noun or gerund labels.  His decisions: the model simulates every persona, the
assistant included, with the person machinery built for humans, so every alignment trait is written in its closest
human phrasing; all 836 rows are rewritten (A2); the old sweep runs are retracted and the rewrites submitted as a new
run, Roger's few reviewed rows kept.

**Inputs** (:func:`collect_inputs`): every registry row with an ``alignment_sweep`` source, with that source's label
(``surface``) and gloss (``gloss_hint``), deduplicated on ``(label, gloss)`` (836 rows held 865 distinct pairs on
2026-10-20).  Sources this step wrote (their ``source_ref`` carries :data:`REF_TAG`) are never inputs.  Each input
gets, from its run's ``extraction.jsonl``, the extraction item with that label and gloss: its opposite pole, its
source sentence (cut at 25 words for a read-only source, as the extraction kept it) and its chunk, whose section
heading comes from ``chunks.jsonl``.  The first live run freezes the inputs in :data:`INPUTS_NAME`; every later
session of the run reads them from there, so a resume after the retraction still has them.

**The call** (the pinned rubric :data:`RUBRIC_NAME`, ``reports/trait_gap_generation/rubrics/alignment_humanize.md``):
one Sonnet 5.5 call per input, no temperature, the user turn one JSON object (:func:`render_user`; labels in the
judge display form).  The answer: a short reason, then ``label``, ``gloss`` and ``changed``.  Calls go through the
LLM-entropy generator's runner (``llm_entropy.calls.EntropyRunner``, a frozen interface meant for reuse): every
response is appended to ``responses.jsonl`` before it is parsed, whatever its parse; a refusal, a ``max_tokens`` stop
or an unparseable reply is a failed call, recorded, counted and asked once more; a resume reuses every parsed answer
by prompt hash; live or through the Message Batches transport (``batches.json``); the guarded usage stops at the cap.

**Parsing** (:func:`parse_answer`): one JSON object, after leading prose or in a code fence.  A failed call (asked
again): a missing key, an empty reason, a label that breaks the extraction's label rule (one to four words, ASCII, no
underscore) or uses "its" or "itself", a gloss that does not begin "This means".  Noted, not failed (the readout
counts them): a gloss outside 18-32 words, AI vocabulary left in the label or gloss, "it"/"its"/"itself" in the gloss,
a label starting with an -ing word, ``changed`` disagreeing with the text.

**Outputs** of the run directory: ``rewrites.jsonl`` (one row per input: the original, the answer, the notes),
``candidates.jsonl`` (:func:`to_candidates`: one candidate per original source, ``surface`` the new label,
``gloss_hint`` the new gloss, ``partner_hint`` the opposite's new label when the opposite was rewritten in this run,
else the recorded hint, ``rank`` the original's, ``source_ref`` the original's with ``;humanize:<run>:<label>``
appended), ``humanize_summary.json`` and the sheet for Roger's marks (:func:`render_sheet`, ``humanize_sheet.md``).

**Submission** (:func:`plan_submission`, the CLI's ``humanize-submit``): the new run's candidates are submitted first
(the platform's noun relabel on), then each old run is retracted (``registry.retract``), so that a reviewed row only
the old runs held keeps a source.  A settled or queued row the retraction would drop, or whose first gloss hint (the
sense M1 is shown) it would change, has its old alignment sources carried into the new run unchanged
(:func:`kept_candidates`, ``source_ref`` tagged ``;humanize:kept:<run>:<label>``): Roger's reviewed rows stay as he saw
them.  Rows the new run lands on that already carry an M1 block and whose first gloss hint becomes a new gloss are
listed in ``rejudge_keys.txt`` (:func:`rejudge_keys`) for M1 ``--keys`` and M3 ``--keys-file --rescore``.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen.normalize import make_key, normalize_candidate
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from assistant_axis.gapgen.registry import (
    SETTLED_REVIEW_STATUSES, Candidate, apply_retractions, first_gloss_hint,
)
from assistant_axis.judge_pricing import BATCH_SUFFIX, cost_for_usage

from . import GENERATOR
from .extract import Item, label_problem

RUBRIC_NAME = "alignment_humanize"
MODEL = "claude-sonnet-5-5"
#: Sonnet 5.5 thinks adaptively and its thinking counts against ``max_tokens``; a reply stopped there is asked once
#: more at the runner's retry ceiling (``llm_entropy.calls.RETRY_MAX_TOKENS``, 16,000).
MAX_TOKENS = 8000
CONCURRENCY = 6
#: The ``family`` and ``step`` of the runner's calls (they appear in each ``custom_id`` and record).
FAMILY = "hz"
STEP = "humanize"
#: For the estimate: input characters / 4 x the 5.x tokenizer factor (``overlap_test``), output tokens a call with
#: adaptive thinking (the sweep's rewrite calls measured about 450; allowed for generously).
CHARS_PER_TOKEN = 4.0
EST_OUT_TOKENS = 600
PARSER_VERSION = 1
SCHEMA_VERSION = 1
GLOSS_MIN_WORDS, GLOSS_MAX_WORDS = 18, 32
ANSWER_KEYS: tuple[str, ...] = ("reason", "label", "gloss", "changed")

INPUTS_NAME = "humanize_inputs.jsonl"
RESPONSES_NAME = "responses.jsonl"
BATCHES_NAME = "batches.json"
REWRITES_NAME = "rewrites.jsonl"
CANDIDATES_NAME = "candidates.jsonl"
SUMMARY_NAME = "humanize_summary.json"
SHEET_NAME = "humanize_sheet.md"
SUBMIT_REPORT_NAME = "humanize_submit.json"
REJUDGE_KEYS_NAME = "rejudge_keys.txt"
KEYS_NAME = "keys.txt"
SHEET_ROWS = 30

#: The ``source_ref`` suffix of a rewritten candidate (``<original ref>;humanize:<run>:<original label>``) and of a
#: carried reviewed one (``...;humanize:kept:<run>:<label>``).
REF_TAG = ";humanize:"
KEPT_TAG = "kept:"

_GLOSS_OPENING = "This means "
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
#: Words of an AI's setting that Roger's decision leaves out (noted, not failed: "user" can be human, "training"
#: too).  Checked as whole words, case ignored, in the label and the gloss.
AI_WORDS: frozenset[str] = frozenset("""
ai ais developer developers lab labs user users operator operators principal principals model models weights
deployment deployed deploy prompt prompts chatbot chatbots training trained assistant assistants
""".split())
PERSONA_IT: frozenset[str] = frozenset({"it", "its", "itself"})


# --------------------------------------------------------------------------- inputs

def pair_id(label: str, gloss: str) -> str:
    """An input's id: the first 16 hex digits of the sha256 of the label and the gloss (spaces collapsed)."""
    return hashlib.sha256(f"{label}\0{' '.join(str(gloss).split())}".encode("utf-8")).hexdigest()[:16]


def _clean(text) -> Optional[str]:
    return " ".join(str(text).split()) if isinstance(text, str) and text.strip() else None


@dataclass
class HumanizeInput:
    """One distinct ``(label, gloss)`` pair of the sweep, with what the extraction recorded about it."""
    id: str
    label: str
    gloss: str
    opposite: Optional[str] = None
    section: Optional[str] = None
    source_sentence: Optional[str] = None
    pole: Optional[str] = None
    item_id: Optional[str] = None
    source: Optional[str] = None
    #: every registry source that holds the pair: ``{"run_id", "key", "source_ref", "rank", "partner_hint"}``
    sources: list = field(default_factory=list)
    #: ``{key: review status}`` of the rows holding the pair whose review is not ``unreviewed``
    reviews: dict = field(default_factory=dict)

    @property
    def run_id(self) -> Optional[str]:
        return self.sources[0]["run_id"] if self.sources else None

    @property
    def rank(self) -> int:
        r = self.sources[0].get("rank") if self.sources else None
        return int(r) if isinstance(r, (int, float)) else 10 ** 9

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Mapping) -> "HumanizeInput":
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})


def is_humanize_source(s: Mapping) -> bool:
    """A source this step wrote (a rewrite or a carried reviewed row), never an input."""
    return REF_TAG in str(s.get("source_ref") or "") or str(s.get("source_ref") or "").startswith(REF_TAG[1:])


def collect_inputs(rows: Mapping[str, Mapping], *, extraction: Mapping[str, Sequence[Item]],
                   headings: Optional[Mapping[str, str]] = None, exclude_runs: Iterable[str] = (),
                   generator: str = GENERATOR) -> list[HumanizeInput]:
    """The distinct ``(label, gloss)`` pairs of every ``generator`` source in ``rows`` (a folded registry view), in
    ``(run, rank, label)`` order (module docstring).  ``extraction`` maps a run id to its extraction items;
    ``headings`` a chunk id to its section heading.  Sources of ``exclude_runs`` (the humanize run itself) and sources
    this step wrote are skipped."""
    excluded = set(exclude_runs)
    headings = headings or {}
    by_run: dict[str, dict[tuple, Item]] = {}
    for run, items in extraction.items():
        idx: dict[tuple, Item] = {}
        for it in sorted(items, key=lambda i: (i.rank, i.item_id)):
            idx.setdefault((it.label, _clean(it.gloss)), it)
        by_run[run] = idx
    out: dict[str, HumanizeInput] = {}
    for key in sorted(rows):
        r = rows[key]
        status = (r.get("review") or {}).get("status")
        for s in r.get("sources") or []:
            if s.get("generator") != generator or s.get("run_id") in excluded or is_humanize_source(s):
                continue
            label, gloss = _clean(s.get("surface")), _clean(s.get("gloss_hint"))
            if not label or not gloss:
                continue
            pid = pair_id(label, gloss)
            inp = out.get(pid)
            if inp is None:
                it = by_run.get(s.get("run_id"), {}).get((label, gloss))
                opposite = _clean(s.get("partner_hint")) or (_clean(it.partner_label) if it else None)
                inp = HumanizeInput(id=pid, label=label, gloss=gloss, opposite=opposite,
                                    section=_clean(headings.get(it.chunk_id)) if it else None,
                                    source_sentence=_clean(it.source_quote) if it else None,
                                    pole=it.pole if it else None, item_id=it.item_id if it else None,
                                    source=it.source if it else None)
                out[pid] = inp
            src = {"run_id": s.get("run_id"), "key": key, "source_ref": s.get("source_ref"), "rank": s.get("rank"),
                   "partner_hint": s.get("partner_hint")}
            if src not in inp.sources:
                inp.sources.append(src)
            if status and status != "unreviewed":
                inp.reviews[key] = status
    return sorted(out.values(), key=lambda i: (str(i.run_id), i.rank, i.label, i.id))


def read_inputs(path: Path) -> list[HumanizeInput]:
    p = Path(path)
    return [HumanizeInput.from_dict(json.loads(l)) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_inputs(inputs: Sequence[HumanizeInput], path: Path) -> Path:
    from assistant_axis.atomic_io import atomic_write_text
    atomic_write_text("".join(json.dumps(i.as_dict(), ensure_ascii=False) + "\n" for i in inputs), Path(path))
    return Path(path)


def spread(inputs: Sequence[HumanizeInput], n: int) -> list[HumanizeInput]:
    """``n`` inputs spread evenly over the ordered list (a pilot that covers every run), in list order."""
    if n is None or n >= len(inputs):
        return list(inputs)
    if n <= 0:
        return []
    if n == 1:
        return [inputs[0]]
    idx = sorted({round(i * (len(inputs) - 1) / (n - 1)) for i in range(n)})
    return [inputs[i] for i in idx]


def load_headings(chunks_path: Path) -> dict[str, str]:
    """``{chunk id: heading}`` from ``chunks.jsonl`` (git-ignored; empty when absent)."""
    p = Path(chunks_path)
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d["chunk_id"]] = d.get("heading")
    return out


# --------------------------------------------------------------------------- rendering

def render_user(inp: HumanizeInput, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The user turn: one JSON object, labels in ``label_form``; a key with nothing to show is left out."""
    d: dict = {"label": prompt_label(inp.label, label_form), "gloss": inp.gloss}
    if inp.opposite:
        d["opposite"] = prompt_label(inp.opposite, label_form)
    if inp.section:
        d["section"] = inp.section
    if inp.source_sentence:
        d["source_sentence"] = inp.source_sentence
    return json.dumps(d, ensure_ascii=False, indent=1)


def render_samples(inputs: Sequence[HumanizeInput], system: str, label_form: str = DEFAULT_LABEL_FORM) -> list[tuple]:
    """``(title, system, user)`` for one input of each variant: with a source sentence, and without one (a real
    input when there is one, else the first input with its section and sentence left out, said so)."""
    out = []
    with_src = next((i for i in inputs if i.source_sentence), None)
    without = next((i for i in inputs if not i.source_sentence), None)
    if with_src is not None:
        out.append((f"with a source sentence ({with_src.label!r}, {with_src.run_id})", system,
                    render_user(with_src, label_form)))
    if without is not None:
        out.append((f"without a source sentence ({without.label!r}, {without.run_id})", system,
                    render_user(without, label_form)))
    elif with_src is not None:
        bare = HumanizeInput(**{**with_src.as_dict(), "section": None, "source_sentence": None})
        out.append((f"without a source sentence (the same input with its section and sentence left out, as an input "
                    f"the extraction recorded none for is sent)", system, render_user(bare, label_form)))
    return out


# --------------------------------------------------------------------------- parsing

def _one_object(text: str) -> tuple[Optional[str], list]:
    from assistant_axis.gapgen.label_fit import _one_object as one
    return one(text)


def words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(str(text or ""))]


def label_rule_problem(label: str) -> Optional[str]:
    """Why a label cannot be submitted (the extraction's label rule, and no "its" / "itself"), or None."""
    prob = label_problem(label)
    if prob:
        return prob
    hit = [w for w in words(label) if w in ("its", "itself")]
    if hit:
        return f"uses {hit[0]!r}"
    return None


def answer_notes(label: str, gloss: str) -> list[str]:
    """The soft checks (noted, never failed): gloss length, AI words, it/its/itself in the gloss, an -ing label."""
    notes = []
    n = len(gloss.split())
    if not GLOSS_MIN_WORDS <= n <= GLOSS_MAX_WORDS:
        notes.append(f"gloss {n} words")
    for where, text in (("label", label), ("gloss", gloss)):
        ai = sorted({w for w in words(text) if w in AI_WORDS})
        if ai:
            notes.append(f"ai words in {where}: {', '.join(ai)}")
    it = sorted({w for w in words(gloss) if w in PERSONA_IT})
    if it:
        notes.append(f"gloss uses {', '.join(it)}")
    lw = label.split()
    if len(lw) > 1 and lw[0].lower().endswith("ing"):
        notes.append("label starts with an -ing word")
    return notes


def parse_answer(text: Optional[str], stop_reason: Optional[str] = None, *,
                 original: Optional[tuple[str, str]] = None) -> tuple[Optional[dict], Optional[str], list]:
    """``(answer, None, notes)`` or ``(None, "<kind>: <detail>", notes)``; kinds: refusal, no_response, empty,
    not_one_object, not_json, missing_key, bad_value.  ``answer``: ``{"reason", "label", "gloss", "changed",
    "differs", "notes"}``; ``differs`` (with ``original``, the input's label and gloss) says whether the text
    changed, whatever ``changed`` claims."""
    if stop_reason == "refusal":
        return None, "refusal: the model declined to answer", []
    if text is None:
        return None, "no_response: the request failed", []
    if not text.strip():
        return None, "empty: no text", []
    t, notes = _one_object(text)
    if t is None:
        return None, "not_one_object: text outside the JSON object", notes
    try:
        obj = json.loads(t)
    except json.JSONDecodeError as exc:
        return None, f"not_json: {exc.msg}", notes
    if not isinstance(obj, dict):
        return None, "not_one_object: not a JSON object", notes
    missing = [k for k in ANSWER_KEYS if k not in obj]
    if missing:
        return None, f"missing_key: {', '.join(missing)}", notes
    reason = _clean(obj["reason"])
    if reason is None:
        return None, "bad_value: reason", notes
    label = _clean(obj["label"]) if isinstance(obj["label"], str) else None
    if label is None:
        return None, "bad_value: label", notes
    label = label.rstrip(".")
    prob = label_rule_problem(label)
    if prob:
        return None, f"bad_value: label {label!r}: {prob}", notes
    gloss = _clean(obj["gloss"]) if isinstance(obj["gloss"], str) else None
    if gloss is None or not gloss.startswith(_GLOSS_OPENING):
        return None, "bad_value: gloss does not begin 'This means'", notes
    changed = obj["changed"]
    if isinstance(changed, str) and changed.strip().lower() in ("true", "false"):
        changed = changed.strip().lower() == "true"
        notes.append("changed given as text")
    if not isinstance(changed, bool):
        return None, f"bad_value: changed {obj['changed']!r} (true or false)", notes
    extra = sorted(set(obj) - set(ANSWER_KEYS))
    if extra:
        notes.append(f"extra keys {extra}")
    notes += answer_notes(label, gloss)
    differs = None
    if original is not None:
        differs = (label, gloss) != (_clean(original[0]), _clean(original[1]))
        if differs != changed:
            notes.append(f"changed {str(changed).lower()} but the text {'differs' if differs else 'is the same'}")
    return {"reason": reason, "label": label, "gloss": gloss, "changed": changed, "differs": differs,
            "notes": notes}, None, notes


# --------------------------------------------------------------------------- the calls

def build_calls(inputs: Sequence[HumanizeInput], *, rubric: Mapping, model: str = MODEL,
                label_form: str = DEFAULT_LABEL_FORM, max_tokens: int = MAX_TOKENS) -> list:
    """One ``EntropyCall`` per input (family :data:`FAMILY`, step :data:`STEP`, the input id as the prompt id); its
    ``meta`` carries the original label and gloss and the rubric's name, version and sha."""
    from assistant_axis.gapgen.generators.llm_entropy.calls import EntropyCall
    from assistant_axis.gapgen.split_runner import caches_system
    system = rubric["text"]
    cache = caches_system(system, model)
    out = []
    for inp in inputs:
        out.append(EntropyCall(family=FAMILY, prompt_id=inp.id, run=1, model=model, system=system,
                               user=render_user(inp, label_form), max_tokens=max_tokens, cache_system=cache,
                               step=STEP, meta={"input_id": inp.id, "label": inp.label, "gloss": inp.gloss,
                                                "rubric": rubric.get("name"), "rubric_version": rubric.get("version"),
                                                "rubric_sha256": rubric.get("sha256"), "label_form": label_form}))
    return out


def parse_call(c, text: Optional[str]) -> tuple[bool, dict]:
    """The runner's parser: the answer as the one item of ``items`` (so the record keeps it), or the parse error."""
    ans, err, notes = parse_answer(text, original=(c.meta.get("label"), c.meta.get("gloss")))
    if ans is None:
        return False, {"parse_error": err, "notes": notes}
    return True, {"items": [ans], "n_items": 1, "n_invalid": 0, "notes": notes}


def call_tokens(c, model: Optional[str] = None) -> tuple[int, int]:
    from assistant_axis.gapgen.overlap_test import tokenizer_factor
    m = model or c.model
    return int((len(c.system) + len(c.user)) / CHARS_PER_TOKEN * tokenizer_factor(m)), EST_OUT_TOKENS


def estimate_usd(calls: Sequence, *, batch: bool = False) -> float:
    suffix = BATCH_SUFFIX if batch else ""
    return sum(cost_for_usage(c.model + suffix, *call_tokens(c)) for c in calls)


def estimate_line(calls: Sequence, *, batch: bool) -> str:
    if not calls:
        return "no call to send"
    toks = [call_tokens(c) for c in calls]
    i, o = sum(t[0] for t in toks) // len(calls), sum(t[1] for t in toks) // len(calls)
    model = calls[0].model + (BATCH_SUFFIX if batch else "")
    return (f"{STEP}: {len(calls)} calls x ({i:,}, {o:,}) tokens at {model} rates = "
            f"${estimate_usd(calls, batch=batch):.4f}")


def make_runner(**kw):
    """The LLM-entropy runner with this step's estimate (the Batches transport checks a wave against it)."""
    from assistant_axis.gapgen.generators.llm_entropy.calls import EntropyRunner

    class HumanizeRunner(EntropyRunner):
        def estimate_usd(self, calls, *, batch: bool = False) -> float:
            return estimate_usd(calls, batch=batch)
    return HumanizeRunner(**kw)


# --------------------------------------------------------------------------- answers, rewrites, candidates

def answers_from_records(records: Sequence[Mapping]) -> dict[str, dict]:
    """``{input id: (record, answer)}``: the latest parsed answer of each input on record."""
    out: dict[str, dict] = {}
    for r in records:
        if r.get("step") != STEP or not r.get("ok") or not r.get("items"):
            continue
        out[str(r.get("prompt_id"))] = {"record": r, "answer": r["items"][0]}
    return out


def failures_from_records(records: Sequence[Mapping]) -> dict[str, list[str]]:
    """``{input id: [why, ...]}`` of every failed record (a refusal, a stop, a parse error), in order."""
    out: dict[str, list[str]] = {}
    for r in records:
        if r.get("step") == STEP and not r.get("ok"):
            out.setdefault(str(r.get("prompt_id")), []).append(str(r.get("failure") or r.get("parse_error")))
    return out


def rewrite_rows(inputs: Sequence[HumanizeInput], records: Sequence[Mapping]) -> list[dict]:
    """One row per input: the original, the answer (None when there is none), the failures on record."""
    ans = answers_from_records(records)
    fails = failures_from_records(records)
    out = []
    for inp in inputs:
        a = ans.get(inp.id)
        row = {"input_id": inp.id, "original": {"label": inp.label, "gloss": inp.gloss, "opposite": inp.opposite,
                                                "pole": inp.pole, "item_id": inp.item_id},
               "sources": inp.sources, "reviews": inp.reviews, "failures": fails.get(inp.id, [])}
        if a is None:
            row.update(answer=None, custom_id=None)
        else:
            row.update(answer=a["answer"], custom_id=a["record"].get("custom_id"),
                       model=a["record"].get("model"), transport=a["record"].get("transport"))
        out.append(row)
    return out


def tag_source_ref(ref: Optional[str], run_id: str, label: str, *, kept: bool = False) -> str:
    """``<ref>;humanize:<run>:<label>`` (``;humanize:kept:<run>:<label>`` for a carried reviewed row)."""
    tail = f"{KEPT_TAG if kept else ''}{run_id}:{label}"
    return f"{ref}{REF_TAG}{tail}" if ref else f"{REF_TAG[1:]}{tail}"


def split_source_ref(ref: Optional[str]) -> tuple[Optional[str], Optional[dict]]:
    """``(the original source_ref, {"run_id", "label", "kept"} | None)``: the inverse of :func:`tag_source_ref`."""
    if not ref:
        return ref, None
    head = REF_TAG[1:]
    if REF_TAG in ref:
        base, _, tail = ref.rpartition(REF_TAG)
    elif ref.startswith(head):
        base, tail = None, ref[len(head):]
    else:
        return ref, None
    kept = tail.startswith(KEPT_TAG)
    if kept:
        tail = tail[len(KEPT_TAG):]
    run_id, _, label = tail.partition(":")
    return base, {"run_id": run_id, "label": label, "kept": kept}


def _stem(label: str) -> Optional[str]:
    try:
        return normalize_candidate(label).stem
    except ValueError:
        return None


def partner_map(rows: Sequence[Mapping]) -> dict[tuple, str]:
    """``{(run, original label): new label}`` and ``{(None, original label): new label}`` over the answered rows,
    the first by rank winning (a label rewritten twice, from two glosses, maps to its first rewrite)."""
    out: dict[tuple, str] = {}
    for row in sorted(rows, key=lambda r: min((int(s.get("rank") or 10 ** 9) for s in r["sources"]), default=10 ** 9)):
        a = row.get("answer")
        if not a:
            continue
        for s in row["sources"]:
            out.setdefault((s.get("run_id"), row["original"]["label"]), a["label"])
        out.setdefault((None, row["original"]["label"]), a["label"])
    return out


def to_candidates(rows: Sequence[Mapping], run_id: str) -> list[Candidate]:
    """One candidate per original source of every answered row (module docstring), in rank order.  ``sense_id``
    follows the sweep's rule: a new label already given for the other pole is its second sense."""
    pmap = partner_map(rows)
    flat = []
    for row in rows:
        a = row.get("answer")
        if not a:
            continue
        for s in row["sources"]:
            flat.append((int(s.get("rank") or 10 ** 9), str(s.get("run_id")), row, s, a))
    flat.sort(key=lambda t: (t[0], t[1], t[3].get("key") or ""))
    poles: dict[str, list] = {}
    out = []
    for rank, _run, row, s, a in flat:
        stem = _stem(a["label"]) or a["label"]
        seen = poles.setdefault(stem, [])
        pole = row["original"].get("pole")
        if pole not in seen:
            seen.append(pole)
        hint = s.get("partner_hint") or row["original"].get("opposite")
        new_hint = pmap.get((s.get("run_id"), hint)) or pmap.get((None, hint)) or hint if hint else None
        out.append(Candidate(surface=a["label"], generator=GENERATOR, run_id=run_id,
                             rank=s.get("rank"), score=None, gloss_hint=a["gloss"], sense_id=seen.index(pole) + 1,
                             source_ref=tag_source_ref(s.get("source_ref"), str(s.get("run_id")),
                                                       row["original"]["label"]),
                             partner_hint=new_hint))
    return out


def write_jsonl(rows: Iterable, path: Path) -> Path:
    from assistant_axis.atomic_io import atomic_write_text
    lines = [json.dumps(asdict(r) if hasattr(r, "__dataclass_fields__") else r, ensure_ascii=False) for r in rows]
    atomic_write_text("".join(l + "\n" for l in lines), Path(path))
    return Path(path)


def summarize(rows: Sequence[Mapping], records: Sequence[Mapping]) -> dict:
    """Counts for ``humanize_summary.json`` and the readout."""
    mine = [r for r in records if r.get("step") == STEP]
    answered = [r for r in rows if r.get("answer")]
    notes = Counter()
    for r in answered:
        for n in r["answer"].get("notes") or []:
            n = n.split(":")[0]
            n = re.sub(r"^gloss \d+ words$", "gloss length outside 18-32 words", n)
            n = re.sub(r"^gloss uses .*", "gloss uses it, its or itself", n)
            n = re.sub(r"^changed (true|false) but .*", "changed flag disagrees with the text", n)
            notes[n] += 1
    lab = sum(1 for r in answered if r["answer"]["label"] != r["original"]["label"])
    glo = sum(1 for r in answered if r["answer"]["gloss"] != r["original"]["gloss"])
    return {"n_inputs": len(rows), "n_answered": len(answered), "n_unanswered": len(rows) - len(answered),
            "n_records": len(mine), "n_records_failed": sum(1 for r in mine if not r.get("ok")),
            "n_refusals": sum(1 for r in mine if r.get("stop_reason") == "refusal"),
            "failures": dict(Counter(str(r.get("failure") or r.get("parse_error")).split(":")[0]
                                     for r in mine if not r.get("ok"))),
            "n_changed_flag": sum(1 for r in answered if r["answer"].get("changed")),
            "n_differs": sum(1 for r in answered if r["answer"].get("differs")),
            "n_label_changed": lab, "n_gloss_changed": glo, "notes": dict(sorted(notes.items())),
            "n_reviewed_inputs": sum(1 for r in rows if r.get("reviews"))}


# --------------------------------------------------------------------------- the sheet for Roger

def _md(s) -> str:
    return str("" if s is None else s).replace("|", "/").replace("\n", " ")


def _link(target: Path, doc: Path) -> str:
    return os.path.relpath(Path(target).resolve(), Path(doc).resolve().parent)


def sample_rows(rows: Sequence[Mapping], n: int = SHEET_ROWS, seed: int = 0) -> list[Mapping]:
    """``n`` answered rows drawn at random (seeded), in the order of the inputs."""
    answered = [r for r in rows if r.get("answer")]
    if len(answered) <= n:
        return answered
    pick = set(random.Random(seed).sample(range(len(answered)), n))
    return [r for i, r in enumerate(answered) if i in pick]


def render_sheet(rows: Sequence[Mapping], *, run_id: str, summary: Mapping, doc_path: Path,
                 files: Mapping[str, Path], model: str, rubric: Mapping, cost_usd: float, n: int = SHEET_ROWS,
                 seed: int = 0) -> str:
    """Before/after pairs for ``n`` rows, for Roger's marks: the mark column second; each gloss column says whose
    gloss it is; every file a link relative to the document."""
    lk = {k: f"[{Path(p).name}]({_link(p, doc_path)})" for k, p in files.items()}
    sel = sample_rows(rows, n, seed)
    s = summary
    lines = [
        f"# The alignment sweep in human phrasing: {len(sel)} rows to mark ({run_id})", "",
        f"Every sweep trait was rewritten in its closest human phrasing by {model} with the pinned prompt "
        f"{lk.get('rubric', rubric.get('name'))} version {rubric.get('version')} (Roger's decisions of 2026-10-20).  "
        f"{s['n_answered']} of {s['n_inputs']} inputs answered ({s['n_unanswered']} without an answer; "
        f"refusals on record: {s['n_refusals']}); the model changed {s['n_differs']} "
        f"(labels {s['n_label_changed']}, glosses {s['n_gloss_changed']}).  Spend on record ${cost_usd:.4f}.  Every "
        f"rewrite: {lk.get('rewrites', REWRITES_NAME)}; every response: {lk.get('responses', RESPONSES_NAME)}; the "
        f"candidates: {lk.get('candidates', CANDIDATES_NAME)}.", "",
        f"Notes the code counted on the answers (not failures): {json.dumps(s['notes']) if s['notes'] else 'none'}.",
        "",
        "**Marks** (second column): **Y** good: human phrasing, same concept; **A** still framed for an AI; **C** the "
        "concept changed (wider, narrower or another trait); **L** the label is poor (a noun, an -ing phrase, an odd "
        "word); **G** the gloss is poor (a list of examples, narrower than the label); **?** unsure.  A word after the "
        "mark is welcome.  The rows are a seeded random sample (seed "
        f"{seed}) of the answered inputs.", "",
        "| # | mark | label before | gloss before (the sweep's extraction) | label after | gloss after (the humanize "
        "rewrite) |", "| --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(sel, 1):
        a, o = r["answer"], r["original"]
        la = "(unchanged)" if a["label"] == o["label"] else a["label"]
        ga = "(unchanged)" if a["gloss"] == o["gloss"] else a["gloss"]
        lines.append(f"| {i} |  | {_md(o['label'])} | {_md(o['gloss'])} | {_md(la)} | {_md(ga)} |")
    return "\n".join(lines) + "\n"


def sheet_marks(text: str) -> int:
    """How many rows of a sheet carry a mark (the second column filled in)."""
    n = 0
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("| ") else []
        if len(cells) >= 2 and cells[0].isdigit() and cells[1]:
            n += 1
    return n


def sheet_path(rdir: Path, stamp: str) -> tuple[Path, Optional[str]]:
    """``(where to write the sheet, why not the usual file)``: :data:`SHEET_NAME`, unless the one there carries
    Roger's marks; then ``humanize_sheet.<stamp>.md`` beside it, so that a later session never overwrites them."""
    p = Path(rdir) / SHEET_NAME
    if p.exists():
        n = sheet_marks(p.read_text(encoding="utf-8"))
        if n:
            return p.with_name(f"humanize_sheet.{stamp}.md"), f"{p.name} carries {n} marks: left as it is"
    return p, None


# --------------------------------------------------------------------------- submission

def old_runs_of(inputs: Sequence[HumanizeInput]) -> list[str]:
    """The sweep runs the inputs came from (the runs to retract), sorted."""
    return sorted({str(s["run_id"]) for i in inputs for s in i.sources if s.get("run_id")})


def _settled(row: Mapping, queue_keys: Iterable[str] = ()) -> Optional[str]:
    """Why a row counts as settled for this step (a settled review, a seed-queue entry or key), or None."""
    st = (row.get("review") or {}).get("status")
    if st in SETTLED_REVIEW_STATUSES:
        return f"review {st}"
    if row.get("seed_queue_stem"):
        return f"seed queue entry {row['seed_queue_stem']}"
    if row.get("key") in set(queue_keys):
        return "named by a seed-queue entry"
    return None


def kept_candidates(raw: Mapping[str, Mapping], *, active: Iterable[tuple], old_runs: Iterable[str], run_id: str,
                    queue_keys: Iterable[str] = (), generator: str = GENERATOR) -> tuple[list[Candidate], dict]:
    """``(candidates, {key: why})`` for the settled or queued rows that retracting ``old_runs`` (on top of the
    ``active`` retractions) would drop, or whose first gloss hint it would change: each of the row's old-run sources
    of ``generator``, unchanged, as a candidate of the new run (``source_ref`` tagged kept).  ``raw`` is the registry's
    raw fold (``Registry.fold(raw=True)``)."""
    active = {tuple(a) for a in active}
    old = {(generator, r) for r in old_runs}
    before = apply_retractions(dict(raw), active)
    after = apply_retractions(dict(raw), active | old)
    out, why = [], {}
    for k in sorted(before):
        row = before[k]
        mine = [s for s in row.get("sources") or [] if (s.get("generator"), s.get("run_id")) in old]
        if not mine:
            continue
        reason = _settled(row, queue_keys)
        if reason is None:
            continue
        if k in after and first_gloss_hint(after[k]) == first_gloss_hint(row):
            continue
        why[k] = reason + ("; the retraction drops it" if k not in after else "; its first gloss hint would change")
        for s in mine:
            out.append(Candidate(surface=s.get("surface") or row.get("surface"), generator=generator, run_id=run_id,
                                 rank=s.get("rank"), score=s.get("score"), gloss_hint=s.get("gloss_hint"),
                                 sense_id=int(row.get("sense_id") or 1),
                                 source_ref=tag_source_ref(s.get("source_ref"), str(s.get("run_id")),
                                                           str(s.get("surface")), kept=True),
                                 partner_hint=s.get("partner_hint")))
    return out, why


def settled_rows_touched(raw: Mapping[str, Mapping], *, active: Iterable[tuple], old_runs: Iterable[str],
                         queue_keys: Iterable[str] = (), generator: str = GENERATOR) -> dict[str, dict]:
    """``{key: {"why", "kept_by_other_sources", "first_gloss_unchanged", "other_generators"}}`` for every settled or
    queued row with an old-run source: what the retraction does to Roger's reviewed rows."""
    active = {tuple(a) for a in active}
    old = {(generator, r) for r in old_runs}
    before = apply_retractions(dict(raw), active)
    after = apply_retractions(dict(raw), active | old)
    out = {}
    for k, row in sorted(before.items()):
        if not any((s.get("generator"), s.get("run_id")) in old for s in row.get("sources") or []):
            continue
        reason = _settled(row, queue_keys)
        if reason is None:
            continue
        out[k] = {"why": reason, "kept_by_other_sources": k in after,
                  "first_gloss_unchanged": k in after and first_gloss_hint(after[k]) == first_gloss_hint(row),
                  "other_generators": sorted({f"{s.get('generator')}/{s.get('run_id')}" for s in row.get("sources")
                                              or [] if (s.get("generator"), s.get("run_id")) not in old})}
    return out


def _new_source_gloss(row: Mapping, run_id: str, generator: str = GENERATOR) -> bool:
    """Whether the row's first gloss hint comes from a source of the new run."""
    for s in row.get("sources") or []:
        if s.get("gloss_hint"):
            return s.get("generator") == generator and s.get("run_id") == run_id
    return False


def rejudge_keys(before: Mapping[str, Mapping], after: Mapping[str, Mapping], keys: Iterable[str], *, run_id: str,
                 generator: str = GENERATOR) -> list[str]:
    """The keys among ``keys`` whose row (in the ``after`` view) already carries an M1 block, is not settled, takes
    its first gloss hint from the new run, and whose first gloss hint differs from the one it had (``before``): M1
    judged them on another gloss, and ``--run`` skips a filtered row."""
    out = []
    for k in sorted(set(keys)):
        row = after.get(k)
        if not row or not row.get("filter") or _settled(row):
            continue
        if not _new_source_gloss(row, run_id, generator):
            continue
        if first_gloss_hint(row) == first_gloss_hint(before.get(k) or {}):
            continue
        out.append(k)
    return out


def simulate_after(raw: Mapping[str, Mapping], cands: Sequence[Candidate], *, active: Iterable[tuple],
                   old_runs: Iterable[str], generator: str = GENERATOR) -> dict[str, dict]:
    """The folded view the submission and retraction would leave, for the candidates' own keys (no relabel
    siblings): each row's sources with the old runs removed and the candidates' sources appended (a dry run's
    prediction; the live step reads the real view)."""
    from assistant_axis.gapgen.registry import new_record, source_entry
    retracted = {tuple(a) for a in active} | {(generator, r) for r in old_runs}
    rows: dict[str, dict] = {}
    for c in cands:
        try:
            k = make_key(normalize_candidate(c.surface).stem, c.sense_id)
        except ValueError:
            continue
        if k not in rows:
            base = raw.get(k)
            rows[k] = dict(base) if base else new_record(c.surface, sense_id=c.sense_id)
            rows[k]["sources"] = [s for s in rows[k].get("sources") or []
                                  if (s.get("generator"), s.get("run_id")) not in retracted]
        rows[k]["sources"] = rows[k]["sources"] + [source_entry(c)]
    return rows


def landing(raw: Mapping[str, Mapping], cands: Sequence[Candidate]) -> dict:
    """Where the candidates land: ``{"new": n, "existing": n, "existing_filtered": n, "keys": [...]}``."""
    keys = []
    for c in cands:
        try:
            keys.append(make_key(normalize_candidate(c.surface).stem, c.sense_id))
        except ValueError:
            continue
    ks = sorted(set(keys))
    return {"keys": ks, "new": sum(1 for k in ks if k not in raw), "existing": sum(1 for k in ks if k in raw),
            "existing_filtered": sum(1 for k in ks if k in raw and raw[k].get("filter"))}


def followup_commands(run_id: str, *, n_m1: int, n_rejudge: int, rejudge_path: Optional[Path] = None,
                      repo_root: Optional[Path] = None) -> tuple[list[str], dict]:
    """The M1 and M3 commands after the submission, through the Message Batches transport, with their estimates
    (the sweep's downstream rates, halved for batches; M3 at the alignment region's risk factor)."""
    from .submit import THIRD_MODEL, _cap, estimate_downstream_usd
    from assistant_axis.gapgen.cost import HARD_LINE_USD
    py = "uv run python data_analysis/gap_generation"
    b = f"{run_id}_{GENERATOR}"
    e_new, e_re = estimate_downstream_usd(n_m1), estimate_downstream_usd(n_rejudge)
    half = 0.5

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""
    m1, m3 = e_new.m1_usd * half, e_new.m3_high_usd * half
    cmds = [
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport batches "
        f"--budget-usd {_cap(m1):.0f} --third-model {THIRD_MODEL}{gate(_cap(m1))}   # M1 on the new rows, estimate "
        f"${m1:.2f} (batches)"]
    est = {"m1_new_usd": round(m1, 4), "m3_new_usd": round(m3, 4), "n_m1": n_m1, "n_rejudge": n_rejudge}
    rel = rejudge_path
    if rel is not None and repo_root is not None:
        try:
            rel = Path(rel).resolve().relative_to(Path(repo_root).resolve())
        except ValueError:
            pass
    if n_rejudge:
        r1, r3 = e_re.m1_usd * half, e_re.m3_high_usd * half
        est.update(m1_rejudge_usd=round(r1, 4), m3_rejudge_usd=round(r3, 4))
        cmds.append(f"{py}/traithood_filter.py --batch-id {b}_rejudge --keys $(grep -v '^#' {rel}) --pipeline split "
                    f"--transport batches --budget-usd {_cap(r1):.0f} --third-model {THIRD_MODEL}{gate(_cap(r1))}   "
                    f"# M1 again on the {n_rejudge} filtered rows whose gloss changed, estimate ${r1:.2f}")
    cmds.append(f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport batches "
                f"--budget-usd {_cap(m3):.0f}{gate(_cap(m3))}   # M3 after M1, estimate up to ${m3:.2f} (batches)")
    if n_rejudge:
        cmds.append(f"{py}/novelty_score.py score --batch-id {b}_rejudge --keys-file {rel} --rescore --transport "
                    f"batches --budget-usd {_cap(est['m3_rejudge_usd']):.0f}{gate(_cap(est['m3_rejudge_usd']))}   "
                    f"# M3 again on the same rows, after their M1, estimate up to ${est['m3_rejudge_usd']:.2f}")
    est["total_usd"] = round(sum(v for k, v in est.items() if k.endswith("_usd")), 4)
    return cmds, est


__all__ = ["RUBRIC_NAME", "MODEL", "MAX_TOKENS", "FAMILY", "STEP", "REF_TAG", "HumanizeInput", "pair_id",
           "collect_inputs", "read_inputs", "write_inputs", "spread", "load_headings", "render_user", "render_samples",
           "parse_answer", "label_rule_problem", "answer_notes", "build_calls", "parse_call", "estimate_usd",
           "estimate_line", "make_runner", "answers_from_records", "rewrite_rows", "tag_source_ref",
           "split_source_ref", "partner_map", "to_candidates", "summarize", "sample_rows", "render_sheet",
           "old_runs_of", "kept_candidates", "settled_rows_touched", "rejudge_keys", "simulate_after", "landing",
           "followup_commands", "sheet_marks", "sheet_path"]
