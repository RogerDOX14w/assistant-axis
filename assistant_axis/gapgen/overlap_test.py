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
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
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

#: The two arms.  ``key`` is the answer field each rubric asks for; ``categories`` the non-numeric answers.
RUBRICS: dict[str, dict] = {
    "A": {"name": "overlap_concept", "key": "similarity", "categories": ("opposite", "unsure"),
          "title": "concept similarity"},
    "B": {"name": "overlap_cooccurrence", "key": "co_occurrence", "categories": ("unsure",),
          "title": "co-occurrence"},
}
HAIKU, SONNET, OPUS = "claude-haiku-4-5-20251001", "claude-sonnet-5-5", "claude-opus-5-5"
MODELS: tuple[str, ...] = (HAIKU, SONNET, OPUS)
REFERENCE = OPUS
SHORT: dict[str, str] = {HAIKU: "Haiku 4.5", SONNET: "Sonnet 5.5", OPUS: "Opus 5.5"}
SCALE: tuple[int, ...] = (0, 1, 2, 3, 4)

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

def load_rubrics(rubrics_dir: Optional[Path] = None) -> dict[str, dict]:
    """``{"A": {"name", "text", "version", "sha256"}, "B": ...}`` from the rubric files; refuses
    (``RubricPinError``) when a text is not its latest pin (``rubric_pins.py bump`` first)."""
    problems = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] in sr.OVERLAP_NAMES]
    if problems:
        raise RubricPinError("; ".join(problems) + "\n" + sr.bump_command(problems))
    pins = sr.current_versions(rubrics_dir, sr.OVERLAP_NAMES)
    out = {}
    for r, spec in RUBRICS.items():
        text = sr.load_prompt(spec["name"], rubrics_dir)
        out[r] = {"name": spec["name"], "text": text, "version": pins[spec["name"]][0], "sha256": sr.sha256(text)}
    return out


def scale_lines(rubric_text: str) -> list[str]:
    """The answer list of a rubric (the lines starting ``- `` after "Give one of these answers")."""
    after = rubric_text.split("Give one of these answers", 1)[-1]
    return [ln for ln in after.splitlines() if ln.startswith("- ")]


# --------------------------------------------------------------------------- the pair set

@dataclass
class Call:
    call_id: str          # "nn:<target>" or "lab:<target>"
    set: str              # "nearest" | "labelled"
    target: str
    listed: list          # stems in the order sent; the id of listed[i] is i + 1


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

def payload_object(call: Call, corpus: Mapping[str, Mapping]) -> dict:
    """The user turn as an object: the target, then the listed traits with ids 1..n."""
    t = corpus[call.target]
    return {"target": {"label": t["label"], "description": t["description"]},
            "traits": [{"id": i, "label": corpus[s]["label"], "description": corpus[s]["description"]}
                       for i, s in enumerate(call.listed, 1)]}


def render_payload(obj: Mapping) -> str:
    """The JSON object laid out as the draft's rendered sample: the target on the first line, each listed
    trait on its own line."""
    lines = ['{"target": ' + json.dumps(obj["target"], ensure_ascii=False) + ",", ' "traits": [']
    body = ",\n".join("  " + json.dumps(t, ensure_ascii=False) for t in obj["traits"])
    return "\n".join(lines) + "\n" + body + "\n ]}"


def render_user(call: Call, corpus: Mapping[str, Mapping]) -> str:
    return render_payload(payload_object(call, corpus))


def call_params(call: Call, corpus: Mapping, *, rubric_text: str, model: str, max_tokens: int = MAX_TOKENS,
                temperature: Optional[float] = TEMPERATURE) -> dict:
    """The Messages API request for one call (``llm.request_params``; no system-prompt cache marker,
    since the rubrics are far below the cacheable length)."""
    return request_params(model=model, system=rubric_text, user=render_user(call, corpus), max_tokens=max_tokens,
                          temperature=temperature, cache_system=False)


def rendered_prompt(call: Call, corpus: Mapping, *, rubric: str, rubric_text: str, model: str) -> str:
    """The request as the model receives it, for reading (AGENT_NOTES: read the rendered prompt)."""
    params = call_params(call, corpus, rubric_text=rubric_text, model=model)
    sent = {k: v for k, v in params.items() if k not in ("system", "messages")}
    return (f"=== rubric {rubric} ({RUBRICS[rubric]['name']}), {call.call_id}, request settings "
            f"{json.dumps(sent)} ===\n--- system ---\n{params['system'][0]['text']}\n--- user ---\n"
            f"{params['messages'][0]['content']}\n")


# --------------------------------------------------------------------------- parsing

def answer_value(v: Any, categories: Sequence[str]) -> Any:
    """An answer: an integer 0-4 (also written as a string), or one of ``categories``; else ``None``."""
    if isinstance(v, str) and v.strip().lower() in categories:
        return v.strip().lower()
    n = _num(v, 0, 4, integer=True)
    return int(n) if n is not None else None


#: 2 (2026-10-03, after Sonnet 5.5's first stage in overlap_test_1): the last complete results object
#: in the text is the answer (a model that writes an answer, then "Correction: ..." and the answer
#: again); 1 read the first-to-last brace span as one object.  The analysis always re-parses the
#: recorded text with the current parser.
PARSER_VERSION = 2


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


def parse_answer(text: Optional[str], rubric: str, n_listed: int) -> tuple[dict, dict, dict]:
    """``(rows, errors, meta)``: ``rows[id] = {"reason", "value", "reason_first"}`` for every listed id
    that parsed; ``errors[id]`` says why each other id failed (``"missing"``, a validation message, or
    the JSON failure for every id); ``meta``: rows returned, whether they came in the order given, ids
    outside 1..n, whether every parsed row put its reason first, and how many complete results objects
    the text held (the last is the answer: :data:`PARSER_VERSION`)."""
    spec = RUBRICS[rubric]
    key, cats = spec["key"], spec["categories"]
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
        val = answer_value(r.get(key), cats) if key in r else None
        if not isinstance(reason, str) or not reason.strip():
            errors[rid] = "reason missing"
        elif key not in r:
            errors[rid] = f"{key} missing"
        elif val is None:
            errors[rid] = f"{key} {r.get(key)!r} is not 0-4 or one of {list(cats)}"
        else:
            keys = list(r.keys())
            rows[rid] = {"reason": " ".join(reason.split()), "value": val,
                         "reason_first": keys.index("reason") < keys.index(key)}
            errors.pop(rid, None)
    for i in want:
        if i not in rows and i not in errors:
            errors[i] = "missing"
    meta.update(n_rows=len(raw), in_order=order == sorted(order),
                reason_first=all(r["reason_first"] for r in rows.values()) if rows else None)
    return rows, errors, meta


# --------------------------------------------------------------------------- running

#: A call whose answer does not parse fully is sent once more (same request), for every model alike;
#: the first attempt's parse rate is reported beside the final one.
ASK_ATTEMPTS = 2


def response_key(rec: Mapping) -> tuple[str, str, str]:
    return rec["rubric"], rec["model"], rec["call_id"]


def read_records(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def answered(rec: Mapping) -> bool:
    return (rec.get("response") or {}).get("text") is not None


def reparse(rec: Mapping) -> tuple[dict, dict, dict]:
    """A record's answer parsed with the current parser (never the stored ``parsed``, which an older
    parser may have written)."""
    return parse_answer((rec.get("response") or {}).get("text"), rec["rubric"], len(rec["listed"]))


def fully_parsed(rec: Mapping) -> bool:
    return answered(rec) and not reparse(rec)[1]


def latest_records(records: Iterable[Mapping]) -> dict[tuple, dict]:
    """The final record per (rubric, model, call): the last one whose answer parses fully, else the last
    one (a call asked again, in the stage or on resume, has several)."""
    last: dict[tuple, dict] = {}
    good: dict[tuple, dict] = {}
    for r in records:
        k = response_key(r)
        last[k] = dict(r)
        if fully_parsed(r):
            good[k] = dict(r)
    return {k: good.get(k, v) for k, v in last.items()}


def done_keys(records: Iterable[Mapping]) -> set:
    """(rubric, model, call) keys whose answer on record parses fully: not sent again on resume."""
    return {k for k, r in latest_records(records).items() if fully_parsed(r)}


@dataclass
class StageResult:
    rubric: str
    model: str
    n_calls: int
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
    """Sends the calls of one (rubric, model) stage concurrently and appends one record per request to
    ``responses.jsonl`` as it completes.  A call whose answer does not parse fully is sent once more
    (:data:`ASK_ATTEMPTS`); each record carries its ``parse_attempt``.  ``usage`` (a ``MultiModelUsage``,
    usually ``cost.GuardedUsage`` with the run's cap) is charged for every response received; when the
    cap is crossed the stage stops sending, keeps the answer that crossed it and reports
    ``budget_exceeded``."""

    def __init__(self, client, rubrics: Mapping[str, Mapping], corpus: Mapping[str, Mapping], *,
                 usage: MultiModelUsage, responses_path: Path, concurrency: int = DEFAULT_CONCURRENCY,
                 max_tokens: int = MAX_TOKENS, temperature: Optional[float] = TEMPERATURE,
                 retry_delays: Sequence[float] = RETRY_DELAYS_S, ask_attempts: int = ASK_ATTEMPTS):
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

    def done(self) -> set:
        return done_keys(read_records(self.responses_path))

    def _record(self, call: Call, rubric: str, model: str, params: Mapping, text: Optional[str], meta: Mapping,
                rows: Mapping, errors: Mapping, pmeta: Mapping, attempt: int) -> dict:
        rb = self.rubrics[rubric]
        req = {k: v for k, v in params.items() if k not in ("system", "messages")}
        req["system_sha256"] = rb["sha256"]
        req["user"] = params["messages"][0]["content"]
        return {"rubric": rubric, "rubric_name": rb["name"], "rubric_version": rb["version"],
                "prompt_sha256": rb["sha256"], "model": model, "call_id": call.call_id, "set": call.set,
                "target": call.target, "listed": list(call.listed), "request": req,
                "response": {"text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                             "attempts": meta.get("attempts"), "error": meta.get("error")},
                "parse_attempt": attempt, "parser_version": PARSER_VERSION,
                "parsed": {str(k): v for k, v in rows.items()}, "errors": {str(k): v for k, v in errors.items()},
                "parse_meta": dict(pmeta), "at": utc_now()}

    async def run_stage(self, rubric: str, model: str, calls: Sequence[Call]) -> StageResult:
        done = self.done()
        todo = [c for c in calls if (rubric, model, c.call_id) not in done]
        res = StageResult(rubric=rubric, model=model, n_calls=len(calls), n_skipped=len(calls) - len(todo))
        sem = asyncio.Semaphore(self.concurrency)
        lock = asyncio.Lock()
        stop = asyncio.Event()
        text_of = self.rubrics[rubric]["text"]
        self.responses_path.parent.mkdir(parents=True, exist_ok=True)

        async def one(call: Call) -> None:
            for attempt in range(1, self.ask_attempts + 1):
                if stop.is_set():
                    return
                async with sem:
                    if stop.is_set():
                        return
                    params = call_params(call, self.corpus, rubric_text=text_of, model=model,
                                         max_tokens=self.max_tokens, temperature=self.temperature)
                    meta: dict = {}
                    try:
                        text = await call_anthropic_json(
                            self.client, system=text_of, user=params["messages"][0]["content"], model=model,
                            max_tokens=self.max_tokens, temperature=self.temperature, usage=self.usage,
                            cache_system=False, retry_delays=self.retry_delays, meta=meta)
                    except BudgetExceededError:
                        text = meta.get("text")
                        res.budget_exceeded = True
                        stop.set()
                    rows, errors, pmeta = parse_answer(text, rubric, len(call.listed))
                    rec = self._record(call, rubric, model, params, text, meta, rows, errors, pmeta, attempt)
                    async with lock:
                        with self.responses_path.open("a", encoding="utf-8") as fh:
                            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        res.n_sent += 1
                        res.n_reasked += int(attempt > 1)
                if not errors:
                    return
                logger.warning("rubric %s on %s, %s: answer did not parse fully (attempt %d of %d): %s", rubric,
                               model, call.call_id, attempt, self.ask_attempts,
                               "; ".join(sorted(set(errors.values())))[:200])

        await asyncio.gather(*(one(c) for c in todo))
        # the stage's parse rate over every pair of its calls on record (sent now or earlier), final and
        # at the first attempt
        records = read_records(self.responses_path)
        latest = latest_records(records)
        first = first_records(records)
        for c in calls:
            rec = latest.get((rubric, model, c.call_id))
            if rec is None:
                continue
            res.n_pairs += len(c.listed)
            res.n_ok += len(reparse(rec)[0])
            res.n_ok_first += len(reparse(first[(rubric, model, c.call_id)])[0])
        warn_if_low_parse_rate(label=f"overlap_test:{RUBRICS[rubric]['name']}:{model}", n_ok=res.n_ok,
                               n_total=res.n_pairs, logger_obj=logger,
                               extra=f"first attempt {res.n_ok_first}/{res.n_pairs}; {res.n_reasked} calls asked again")
        return res


def first_records(records: Iterable[Mapping]) -> dict[tuple, dict]:
    """The first record per (rubric, model, call): its first attempt."""
    out: dict[tuple, dict] = {}
    for r in records:
        out.setdefault(response_key(r), dict(r))
    return out


def first_attempt_parse(pair_set: PairSet, records: Iterable[Mapping]) -> dict[tuple[str, str], dict]:
    """``{(rubric, model): {"ok", "total"}}``: pairs whose answer parsed at the first attempt."""
    out: dict = defaultdict(lambda: {"ok": 0, "total": 0})
    for (rubric, model, _), rec in first_records(records).items():
        rows = reparse(rec)[0]
        out[(rubric, model)]["total"] += len(rec["listed"])
        out[(rubric, model)]["ok"] += len(rows)
    return {k: dict(v) for k, v in out.items()}


# --------------------------------------------------------------------------- answers

def collect_answers(pair_set: PairSet, records: Iterable[Mapping]) -> dict[tuple[str, str], dict[str, dict]]:
    """``{(rubric, model): {pair_id: {"value", "reason", "reason_first", "error"}}}`` from the final
    record per call (:func:`latest_records`), re-parsed with the current parser; a pair whose call has no
    record is absent, a pair that failed to parse has ``value`` ``None`` and its ``error``."""
    latest = latest_records(records)
    by_call: dict[str, list] = defaultdict(list)
    for p in pair_set.pairs:
        by_call[p.call_id].append(p)
    out: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for (rubric, model, call_id), rec in latest.items():
        rows, errors, _ = reparse(rec)
        for p in by_call.get(call_id, []):
            row = rows.get(p.id)
            if row is not None:
                out[(rubric, model)][p.pair_id] = {"value": row["value"], "reason": row["reason"],
                                                   "reason_first": row.get("reason_first"), "error": None}
            else:
                out[(rubric, model)][p.pair_id] = {"value": None, "reason": None, "reason_first": None,
                                                   "error": errors.get(p.id, "missing")}
    return dict(out)


def results_rows(pair_set: PairSet, answers: Mapping) -> list[dict]:
    """One row per (pair, rubric, model) for ``results.jsonl``."""
    out = []
    for p in pair_set.pairs:
        for (rubric, model), ans in sorted(answers.items()):
            a = ans.get(p.pair_id)
            if a is None:
                continue
            out.append({"pair_id": p.pair_id, "call_id": p.call_id, "target": p.target, "listed": p.listed,
                        "id": p.id, "group": p.group, "rubric": rubric, "rubric_name": RUBRICS[rubric]["name"],
                        "model": model, **a, "embedding_cos": p.embedding_cos, "persona_cos": p.persona_cos})
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


def agreement(ref: Mapping[str, Mapping], other: Mapping[str, Mapping]) -> dict:
    """Agreement of ``other`` with ``ref`` over the pairs both answered: exact agreement over every
    answer (categories included), and on the pairs where both gave a number, exact, within one point,
    the mean difference (other - ref) and the weighted kappa (quadratic, and linear); the categorical
    answers as a table ``{ref kind: {other kind: n}}`` (kinds: numeric, opposite, unsure, unparsed)."""
    common = sorted(set(ref) & set(other))
    both = [(ref[k]["value"], other[k]["value"]) for k in common
            if ref[k]["value"] is not None and other[k]["value"] is not None]
    num = [(x, y) for x, y in both if _num_val(x) and _num_val(y)]
    table: dict = defaultdict(Counter)
    for k in common:
        table[_kind(ref[k]["value"])][_kind(other[k]["value"])] += 1
    out = {"n_common": len(common), "n_both_parsed": len(both),
           "exact_all": _r(np.mean([x == y for x, y in both])) if both else None, "n_numeric": len(num)}
    if num:
        x = np.array([p[0] for p in num])
        y = np.array([p[1] for p in num])
        out.update(exact=_r(np.mean(x == y)), within_one=_r(np.mean(np.abs(x - y) <= 1)),
                   mean_diff=_r(np.mean(y - x)), kappa_quadratic=_r(weighted_kappa(x, y)),
                   kappa_linear=_r(weighted_kappa(x, y, weights="linear")))
    out["table"] = {k: dict(v) for k, v in sorted(table.items())}
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


def value_counts(values: Iterable) -> dict:
    c = Counter("unparsed" if v is None else str(v) for v in values)
    order = [str(s) for s in SCALE] + ["opposite", "unsure", "unparsed"]
    return {k: c[k] for k in order if c.get(k)}


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


def by_score(pairs: Sequence[Pair], ans: Mapping[str, Mapping]) -> dict:
    """For each answer: how many pairs, and their mean embedding and persona-space cosines (the
    calibration by-product of M3 item 7: the overlap score beside the angle)."""
    out = {}
    groups: dict[str, list] = defaultdict(list)
    for p in pairs:
        a = ans.get(p.pair_id)
        if a is not None and a["value"] is not None:
            groups[str(a["value"])].append(p)
    for k in [str(s) for s in SCALE] + ["opposite", "unsure"]:
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
    """Everything the readout reports, as one JSON-ready dict.  ``first_parse``
    (:func:`first_attempt_parse`) adds the parse rate at the first attempt."""
    pairs = pair_set.pairs
    get = lambda r, m: answers.get((r, m), {})  # noqa: E731
    out: dict = {"n_pairs": len(pairs), "n_calls": len(pair_set.calls), "models": list(models),
                 "reference": reference, "parse": parse_rates(pair_set, answers), "agreement": {},
                 "correlation": {}, "rubric_difference": {}, "groups": {}, "rates": {}, "by_score": {},
                 "divergence": {}, "context_consistency": {}, "opus_on_disagreement": {},
                 "parse_first_attempt": {f"{r}|{m}": {**v, "rate": _r(v["ok"] / v["total"]) if v["total"] else None}
                                         for (r, m), v in sorted((first_parse or {}).items())},
                 "parser_version": PARSER_VERSION,
                 "reason_first_share": {}, "bootstrap": {"n_boot": n_boot, "seed": seed,
                                                         "unit": "target (all the pairs of one call's target)"}}
    for r in RUBRICS:
        out["agreement"][r] = {m: agreement(get(r, reference), get(r, m)) for m in models if m != reference
                               and get(r, m) and get(r, reference)}
        out["correlation"][r] = {m: correlations(pairs, get(r, m), n_boot=n_boot, seed=seed) for m in models if get(r, m)}
        out["groups"][r] = {m: group_stats(pairs, get(r, m)) for m in models if get(r, m)}
        out["rates"][r] = {m: rates(pairs, get(r, m)) for m in models if get(r, m)}
        out["by_score"][r] = {m: by_score(pairs, get(r, m)) for m in models if get(r, m)}
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
    L = ["# Overlap test: tables", "",
         f"{summary['n_pairs']} pairs in {summary['n_calls']} calls.  Reference model: {sm(ref)}.  Generated from "
         "`summary.json` beside this file.", "", "## Parse rates (pairs whose answer parsed)", "",
         "| rubric | model | ok / total | rate | first attempt |", "|---|---|---|---|---|"]
    for k, v in summary["parse"].items():
        r, m = k.split("|", 1)
        fa = summary.get("parse_first_attempt", {}).get(k)
        first = f"{fa['ok']} / {fa['total']} ({_f(fa['rate'], 4)})" if fa else "–"
        L.append(f"| {r} | {sm(m)} | {v['ok']} / {v['total']} | {_f(v['rate'], 4)} | {first} |")
    L += ["", f"## Agreement with {sm(ref)}", "",
          "Exact agreement over every answer (categories included); then, on the pairs where both gave a number, "
          "exact, within one point, the mean difference (model minus reference) and the weighted kappa "
          "(quadratic; linear in brackets).", "",
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
        L += ["", f"## Known groups, rubric {r}", "",
              "Mean of the numeric answers / share at 3 or more" + (" / share opposite" if r == "A" else "")
              + " / share unsure; n in the first column.", "",
              "| group | n | " + " | ".join(sm(m) for m in per) + " |", "|---|---|" + "---|" * len(per)]
        for g in GROUPS:
            n = next(iter(per.values()))[g]["n"]
            cells = []
            for m in per:
                s = per[m][g]
                parts = [_f(s["mean"]), _pct(s["share_3_plus"])]
                if r == "A":
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
    return "\n".join(L) + "\n"


# --------------------------------------------------------------------------- cost

def tokenizer_factor(model: str) -> float:
    m = model.lower()
    return NEW_TOKENIZER_FACTOR if any(f in m for f in NEW_TOKENIZER_FRAGMENTS) else 1.0


def estimate(calls: Sequence[Call], corpus: Mapping, rubrics: Mapping[str, Mapping], models: Sequence[str],
             rubric_keys: Sequence[str] = tuple(RUBRICS)) -> Estimate:
    """Calls x mean (input, output) tokens per (rubric, model), at each model's live rates."""
    est = Estimate()
    if not calls:
        return est
    users = [render_user(c, corpus) for c in calls]
    mean_rows = float(np.mean([len(c.listed) for c in calls]))
    for m in models:
        f = tokenizer_factor(m)
        for r in rubric_keys:
            in_tok = int(round(np.mean([len(rubrics[r]["text"]) + len(u) for u in users]) / CHARS_PER_TOKEN * f))
            out_tok = int(round((OUT_BASE_TOKENS + OUT_PER_ROW_TOKENS * mean_rows) * f))
            est.add(f"rubric {r} ({RUBRICS[r]['name']}) on {SHORT.get(m, m)}", m, len(calls), in_tok, out_tok)
    return est


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
