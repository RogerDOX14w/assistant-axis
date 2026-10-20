"""The label-fit check (Roger, 2026-10-14/15): does a generator's label, said of a person, mean what its gloss says?

A generator that describes a concept and then names it (the structural generator: Aristotle's excess of ambition,
"craving honor beyond what is right") too often picks a word whose usual person sense is something else
("grasping", usually greedy).  M1 judges a word's first sense and never compares it with the generator's gloss, so
this check runs **before submission**, on ``(label, gloss)`` pairs, for any generator.

**Senses** (:func:`sense_context`): the label's Open English WordNet senses (adjective senses first, in WordNet's
order, at most :data:`MAX_DICTIONARY_SENSES`; a label with none gets up to :data:`MAX_OTHER_SENSES` senses of other
parts of speech) and, when the label is already a registry row M1 judged, M1's ``filter.senses`` and
``filter.judged_sense``.  All of them are shown to the model as evidence; WordNet's person-cue pattern
(``censuses.glosshint.PERSON_RE``) is not used to narrow them, since it misses senses such as grasping's "greedy".

**The free pre-screen** (:func:`cosines`): the cosine between the gloss (its "This means " opening removed) and the
label's usual sense (M1's ``judged_sense``, else the first dictionary sense), and the largest cosine over every sense
shown, with a local embedder.  Recorded on every pair and reported; it decides nothing unless a floor is given
(``screen_floor``: a pair at or above it is taken as fitting with no call).  On Roger's 50 marks the coordinator's
cosine separated poorly (median 0.40 on the rows marked "?" against 0.53, heavy overlap), so the default has no floor.

**The call** (the pinned rubric ``reports/trait_gap_generation/rubrics/label_fit.md``, :data:`RUBRIC_NAME`): one pair
per call, the user turn one JSON object (:func:`build_user`); the answer a short reason, then ``verdict``
(:data:`VERDICTS`), then ``better_label`` (a single word whose usual person sense is the gloss, or a short phrase when
English has none; null on ``fits``).  Haiku 5.5 by default, Sonnet 5.5 allowed (:data:`MODELS`); no temperature;
``max_tokens`` :data:`MAX_TOKENS`.  ``readings`` calls per pair (default 3), keyed by the reading index.

**Combining** (:func:`combine`; Roger's rule for sampled outputs: majority for decisions, union for generated words):
the pair fits when more than half of its answered readings say ``fits`` (a tie counts as not fitting); otherwise its
verdict is the commoner of ``secondary_sense`` and ``not_a_sense`` (a tie: ``not_a_sense``), and its proposals are the
union of the better labels of the readings that did not find a fit, by stem, each with its support, in order of
support.  A proposal whose stem is the label's own is dropped.

**Records** (``responses.jsonl``, append-only): every response before it is parsed, with the request's sha256 (system
and user turns), the rubric's version and sha, the reading, the billed usage (``usage_raw``, ``charged_as``) and the
parse.  A refusal is a failed call.  :func:`parse_answer` accepts one JSON object, after leading prose (Sonnet often
writes a sentence first) or inside a code fence, and refuses text after the object.  A resume reuses every parsed
answer whose request sha, reading and model match.

**The corrected candidates** (:func:`corrected_candidates`): a candidate whose pair fits (or was screened as fitting)
is unchanged; one whose pair does not is replaced by one candidate per proposal (same generator, run, rank, score,
gloss hint and partner hint), its ``source_ref`` the original with ``;label_fit:<verdict>:<original label>``
appended (:func:`tag_source_ref`, :func:`split_source_ref`), so that the route and the original label travel with the
row into the registry.  A non-fitting pair with no usable proposal keeps its candidate and is listed in the readout.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import Estimate
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.normalize import make_key, normalize_candidate
from assistant_axis.gapgen.prompt_labels import prompt_label
from assistant_axis.gapgen.registry import Candidate, utc_now
from assistant_axis.gapgen.split_runner import MAX_TOKENS_THINKING
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

RUBRIC_NAME = "label_fit"
DEFAULT_MODEL = "claude-haiku-5-5"
MODELS: tuple[str, ...] = ("claude-haiku-5-5", "claude-sonnet-5-5")
#: The platform's ``max_tokens`` for a model that thinks (``split_runner.MAX_TOKENS_THINKING``, 2000): both models
#: think adaptively, and the thinking counts against it (the base model's sense call came back empty at 300).
MAX_TOKENS = MAX_TOKENS_THINKING
VERDICTS: tuple[str, ...] = ("fits", "secondary_sense", "not_a_sense")
ANSWER_KEYS: tuple[str, ...] = ("reason", "verdict", "better_label")
#: 1 (2026-10-15): one JSON object, after leading prose or in a code fence; nothing after it.
PARSER_VERSION = 1
DEFAULT_READINGS = 3
CONCURRENCY = 8
MAX_DICTIONARY_SENSES = 6
MAX_OTHER_SENSES = 3
#: For the estimate: the system prompt is about 2,700 characters (about 900 tokens with the 5.x tokenizer), the user
#: turn about 150; the answer about 80 tokens, with adaptive thinking on top (allowed for generously).
EST_IN_TOKENS, EST_OUT_TOKENS = 1100, 500
RESPONSES_NAME = "responses.jsonl"
USAGE_NAME = "usage.json"
DECISIONS_NAME = "decisions.json"
READOUT_NAME = "readout.md"
CANDIDATES_NAME = "candidates.jsonl"
#: The ``source_ref`` suffix of a relabelled candidate.
REF_TAG = ";label_fit:"
_GLOSS_OPENING = re.compile(r"^\s*this means\s+", re.I)


class RubricNotPinned(RuntimeError):
    """The prompt's text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- senses

def _clean(text) -> Optional[str]:
    return " ".join(str(text).split()) if isinstance(text, str) and text.strip() else None


def oewn_senses(label: str, *, senses: Optional[Callable] = None) -> list[str]:
    """The label's WordNet senses as shown to the model: adjective senses in WordNet's order (at most
    :data:`MAX_DICTIONARY_SENSES`), else up to :data:`MAX_OTHER_SENSES` senses of other parts of speech with the
    part of speech in brackets.  ``senses(label)`` returns ``censuses.glosshint.Sense`` objects (default
    ``glosshint.adjective_senses`` on the in-tree OEWN)."""
    from assistant_axis.gapgen.generators.censuses.glosshint import ADJ_POS, POS_NAMES, adjective_senses
    found = list((senses or adjective_senses)(label) or [])
    adj = [s.definition for s in found if s.pos in ADJ_POS and _clean(s.definition)]
    if adj:
        return list(dict.fromkeys(adj))[:MAX_DICTIONARY_SENSES]
    other = [f"{s.definition} ({POS_NAMES.get(s.pos, s.pos)})" for s in found if _clean(s.definition)]
    return list(dict.fromkeys(other))[:MAX_OTHER_SENSES]


def recorded_senses(row: Optional[Mapping]) -> tuple[list[str], Optional[str]]:
    """``(M1's senses, M1's judged sense)`` of a registry row (empty when M1 has not judged it)."""
    f = (row or {}).get("filter") or {}
    ss = [x for x in (_clean(s) for s in f.get("senses") or [] if isinstance(s, str)) if x]
    return list(dict.fromkeys(ss)), _clean(f.get("judged_sense"))


def row_for(label: str, rows: Optional[Mapping[str, Mapping]]) -> Optional[Mapping]:
    if not rows:
        return None
    try:
        return rows.get(make_key(normalize_candidate(label).stem, 1))
    except ValueError:
        return None


def sense_context(label: str, *, senses: Optional[Callable] = None, rows: Optional[Mapping] = None,
                  use_oewn: bool = True) -> dict:
    """``{"dictionary_senses", "recorded_senses", "usual_sense"}`` for a label (empty lists and None when unknown)."""
    rec, usual = recorded_senses(row_for(label, rows))
    return {"dictionary_senses": oewn_senses(label, senses=senses) if use_oewn else [], "recorded_senses": rec,
            "usual_sense": usual}


def build_user(label: str, gloss: str, ctx: Mapping) -> str:
    """The user turn: one JSON object; a key with nothing to show is left out."""
    d: dict = {"label": prompt_label(label), "gloss": " ".join(str(gloss).split())}
    if ctx.get("dictionary_senses"):
        d["dictionary_senses"] = list(ctx["dictionary_senses"])
    if ctx.get("recorded_senses"):
        d["recorded_senses"] = list(ctx["recorded_senses"])
    if ctx.get("usual_sense"):
        d["usual_sense"] = ctx["usual_sense"]
    return json.dumps(d, ensure_ascii=False)


# --------------------------------------------------------------------------- the prompt

def load_rubric(rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin (with
    ``allow_unpinned``, for rendering only, ``version`` and ``sha256`` are None)."""
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == RUBRIC_NAME]
    path = sr.rubric_path(RUBRIC_NAME, rubrics_dir)
    try:
        from assistant_axis.gapgen.paths import REPO_ROOT
        rel = str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    text = sr.load_prompt(RUBRIC_NAME, rubrics_dir)
    if probs:
        if not allow_unpinned:
            raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
        return {"name": RUBRIC_NAME, "text": text, "version": None, "sha256": None, "file": rel}
    version, sha = sr.current_versions(rubrics_dir, (RUBRIC_NAME,))[RUBRIC_NAME]
    return {"name": RUBRIC_NAME, "text": text, "version": version, "sha256": sha, "file": rel}


def request_sha256(system: str, user: str) -> str:
    """The request's identity for a resume: the system and user turns as sent."""
    return hashlib.sha256(json.dumps([system, user], ensure_ascii=False).encode("utf-8")).hexdigest()


def pair_id(label: str, gloss: str) -> str:
    return hashlib.sha256(f"{label}\0{' '.join(str(gloss).split())}".encode("utf-8")).hexdigest()[:16]


@dataclass
class Item:
    """One ``(label, gloss)`` pair, as asked."""
    label: str
    gloss: str
    context: dict
    user: str
    request_sha256: str
    cos_usual: Optional[float] = None
    cos_max: Optional[float] = None

    @property
    def id(self) -> str:
        return pair_id(self.label, self.gloss)

    @property
    def stem(self) -> Optional[str]:
        try:
            return normalize_candidate(self.label).stem
        except ValueError:
            return None


def build_items(pairs: Iterable[tuple[str, str]], *, system: str, senses: Optional[Callable] = None,
                rows: Optional[Mapping] = None, use_oewn: bool = True) -> list[Item]:
    """One item per distinct ``(label, gloss)`` pair, in first-seen order."""
    out, seen = [], set()
    for label, gloss in pairs:
        k = pair_id(label, gloss)
        if k in seen or not _clean(label) or not _clean(gloss):
            continue
        seen.add(k)
        ctx = sense_context(label, senses=senses, rows=rows, use_oewn=use_oewn)
        u = build_user(label, gloss, ctx)
        out.append(Item(label=label, gloss=" ".join(str(gloss).split()), context=ctx, user=u,
                        request_sha256=request_sha256(system, u)))
    return out


# --------------------------------------------------------------------------- the free screen

def gloss_text(gloss: str) -> str:
    """The gloss as embedded: its "This means " opening removed (dictionary senses have none)."""
    return _GLOSS_OPENING.sub("", str(gloss)).strip()


def cosines(items: Sequence[Item], *, embed: Callable[[Sequence[str]], object]) -> int:
    """Set ``cos_usual`` (gloss against the usual sense: M1's judged sense, else the first dictionary sense) and
    ``cos_max`` (the largest over every sense shown) on each item that has a sense; returns how many got one.
    ``embed(texts)`` returns unit rows in input order (``gapgen.embed.embed_texts``)."""
    import numpy as np
    todo = []
    for it in items:
        ss = list(dict.fromkeys([*it.context.get("recorded_senses", []), *it.context.get("dictionary_senses", [])]))
        usual = it.context.get("usual_sense") or (it.context.get("dictionary_senses") or [None])[0]
        if ss or usual:
            todo.append((it, usual, ss))
    if not todo:
        return 0
    texts = []
    for it, usual, ss in todo:
        texts += [gloss_text(it.gloss), *([usual] if usual else []), *ss]
    uniq = list(dict.fromkeys(texts))
    E = np.asarray(embed(uniq), dtype=np.float64)
    at = {t: i for i, t in enumerate(uniq)}
    for it, usual, ss in todo:
        g = E[at[gloss_text(it.gloss)]]
        it.cos_usual = round(float(g @ E[at[usual]]), 6) if usual else None
        cs = [float(g @ E[at[s]]) for s in ss]
        it.cos_max = round(max(cs), 6) if cs else it.cos_usual
    return len(todo)


# --------------------------------------------------------------------------- the parser

def _one_object(text: str) -> tuple[Optional[str], list]:
    """The JSON object the text is, or ends with after leading prose, or holds in a code fence; None otherwise."""
    notes: list = []
    t = text.strip()
    if t.startswith("```"):
        body = t.split("\n", 1)[1] if "\n" in t else ""
        if body.rstrip().endswith("```"):
            t = body.rstrip()[:-3].strip()
            notes.append("code fence removed")
    if not t.startswith("{") and t.endswith("}"):
        for i in [k for k, ch in enumerate(t) if ch == "{"]:
            try:
                cand = json.loads(t[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(cand, dict):
                t = t[i:]
                notes.append("prose before the object")
                break
    if not (t.startswith("{") and t.endswith("}")):
        return None, notes
    return t, notes


def parse_answer(text: Optional[str], stop_reason: Optional[str] = None) -> tuple[Optional[dict], Optional[str], list]:
    """``(answer, None, notes)`` or ``(None, "<kind>: <detail>", notes)``; kinds: refusal, no_response, empty,
    not_one_object, not_json, missing_key, bad_value.  ``answer``: ``{"reason", "verdict", "better_label"}``, the
    better label None on ``fits`` (one given anyway is dropped with a note) and required otherwise."""
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
    missing = [k for k in ("reason", "verdict") if k not in obj]
    if missing:
        return None, f"missing_key: {', '.join(missing)}", notes
    reason = _clean(obj["reason"])
    if reason is None:
        return None, "bad_value: reason", notes
    v = obj["verdict"]
    v = " ".join(str(v).split()).lower().replace(" ", "_").replace("-", "_") if isinstance(v, str) else None
    if v not in VERDICTS:
        return None, f"bad_value: verdict {obj['verdict']!r} (one of {', '.join(VERDICTS)})", notes
    if v != obj["verdict"]:
        notes.append("verdict normalised")
    bl = obj.get("better_label")
    bl = _clean(bl) if isinstance(bl, str) else None
    if bl is not None and bl.lower() in ("null", "none"):
        bl = None
    if v == "fits":
        if bl is not None:
            notes.append("better_label given on fits: dropped")
        bl = None
    elif bl is None:
        return None, "bad_value: better_label is required when the verdict is not fits", notes
    elif len(bl.split()) > 4:
        notes.append("better_label longer than four words")
    extra = sorted(set(obj) - set(ANSWER_KEYS))
    if extra:
        notes.append(f"extra keys {extra}")
    return {"reason": reason, "verdict": v, "better_label": bl}, None, notes


# --------------------------------------------------------------------------- records and resume

def read_records(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue            # a torn last line from a killed run: the request is asked again
    return out


def answers_on_record(records: Sequence[Mapping], *, model: str) -> dict[tuple, dict]:
    """``{(request_sha256, reading): record}``: the latest parsed record of each request and reading on ``model``."""
    out: dict[tuple, dict] = {}
    for r in records:
        if r.get("model") == model and r.get("request_sha256") and r.get("parsed"):
            out[(r["request_sha256"], int(r.get("reading") or 0))] = r
    return out


@dataclass
class CheckResult:
    n_calls: int = 0
    n_ok: int = 0
    error_kinds: dict = field(default_factory=dict)
    stopped_by_budget: bool = False


async def ask(todo: Sequence[tuple[Item, int]], *, client, rubric: Mapping, model: str = DEFAULT_MODEL,
              usage: MultiModelUsage, responses_path: Path, max_tokens: int = MAX_TOKENS,
              concurrency: int = CONCURRENCY, now: Callable[[], str] = utc_now) -> CheckResult:
    """One call per ``(item, reading)``; every response recorded (appended) before it is parsed.  A
    ``BudgetExceededError`` from a guarded ``usage`` keeps and records the response that crossed the cap, then
    stops the run."""
    from assistant_axis.gapgen.split_runner import caches_system
    system = rubric["text"]
    cache = caches_system(system, model)
    res = CheckResult()
    sem = asyncio.Semaphore(max(1, concurrency))
    lock = asyncio.Lock()
    Path(responses_path).parent.mkdir(parents=True, exist_ok=True)

    async def one(item: Item, reading: int) -> None:
        async with sem:
            if res.stopped_by_budget:
                return
            meta: dict = {}
            try:
                text = await call_anthropic_json(client, system=system, user=item.user, model=model,
                                                 max_tokens=max_tokens, temperature=None, usage=usage,
                                                 cache_system=cache, meta=meta)
            except BudgetExceededError:
                text = meta.get("text")
                res.stopped_by_budget = True
            parsed, err, notes = parse_answer(text, meta.get("stop_reason"))
            rec = {"id": item.id, "label": item.label, "gloss": item.gloss, "reading": reading, "model": model,
                   "rubric": rubric["name"], "prompt_version": rubric["version"], "prompt_sha256": rubric["sha256"],
                   "request_sha256": item.request_sha256, "user": item.user, "cache_system": cache,
                   "max_tokens": max_tokens, "text": text, "stop_reason": meta.get("stop_reason"),
                   "stop_details": meta.get("stop_details"), "usage_raw": meta.get("usage_raw"),
                   "charged_as": model if meta.get("usage_raw") else None, "error": meta.get("error"),
                   "parsed": parsed, "parse_error": err, "notes": notes, "parser_version": PARSER_VERSION,
                   "at": now()}
            async with lock:
                res.n_calls += 1
                with open(responses_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if parsed is not None:
                    res.n_ok += 1
                else:
                    k = err.split(":")[0]
                    res.error_kinds[k] = res.error_kinds.get(k, 0) + 1

    await asyncio.gather(*(one(i, r) for i, r in todo))
    return res


def estimate(n_calls: int, model: str = DEFAULT_MODEL) -> Estimate:
    est = Estimate()
    est.add("label fit", model, n_calls, EST_IN_TOKENS, EST_OUT_TOKENS)
    return est


# --------------------------------------------------------------------------- combining

def _stem(label: str) -> Optional[str]:
    try:
        return normalize_candidate(label).stem
    except ValueError:
        return None


def combine(answers: Sequence[Mapping], *, label: str) -> dict:
    """The pair's decision from its answered readings (module docstring): ``{"decision": "fits" | "relabel" |
    "no_better_label" | None, "verdict", "votes", "n_answered", "proposals": [{"label", "stem", "support"}],
    "dropped_proposals"}``.  ``decision`` None: no reading answered."""
    votes = [a["verdict"] for a in answers]
    n = len(votes)
    out = {"decision": None, "verdict": None, "votes": votes, "n_answered": n, "proposals": [],
           "dropped_proposals": []}
    if not n:
        return out
    n_fit = votes.count("fits")
    if n_fit * 2 > n:
        out.update(decision="fits", verdict="fits")
        return out
    c = Counter(v for v in votes if v != "fits")
    sec, nas = c.get("secondary_sense", 0), c.get("not_a_sense", 0)
    out["verdict"] = "secondary_sense" if sec > nas else "not_a_sense"
    own = _stem(label)
    support: dict[str, int] = {}
    first: dict[str, str] = {}
    for a in answers:
        bl = a.get("better_label")
        if a["verdict"] == "fits" or not bl:
            continue
        s = _stem(bl)
        if s is None or s == own:
            out["dropped_proposals"].append(bl)
            continue
        support[s] = support.get(s, 0) + 1
        first.setdefault(s, bl)
    order = sorted(support, key=lambda s: (-support[s], list(first).index(s)))
    out["proposals"] = [{"label": first[s], "stem": s, "support": support[s]} for s in order]
    out["decision"] = "relabel" if out["proposals"] else "no_better_label"
    return out


def decide(items: Sequence[Item], answers: Mapping[tuple, Mapping], readings: int, *,
           screen_floor: Optional[float] = None) -> list[dict]:
    """One decision row per item: the screen (when ``screen_floor`` is set and the pair's usual-sense cosine reaches
    it, ``decided_by: "screen"``, no answers used), else :func:`combine` over its readings' parsed answers."""
    out = []
    for it in items:
        row = {"id": it.id, "label": it.label, "gloss": it.gloss, "stem": it.stem, "context": it.context,
               "cos_usual": it.cos_usual, "cos_max": it.cos_max}
        if screen_floor is not None and it.cos_usual is not None and it.cos_usual >= screen_floor:
            row.update(decision="fits", verdict="fits", decided_by="screen", votes=[], n_answered=0, proposals=[],
                       dropped_proposals=[], reasons=[])
            out.append(row)
            continue
        got = [answers[(it.request_sha256, r)] for r in range(readings) if (it.request_sha256, r) in answers]
        parsed = [g["parsed"] for g in got]
        row.update(combine(parsed, label=it.label), decided_by="model",
                   reasons=[f"{p['verdict']}: {p['reason']}" + (f" -> {p['better_label']}" if p.get("better_label")
                                                                 else "") for p in parsed])
        out.append(row)
    return out


def todo_calls(items: Sequence[Item], answers: Mapping[tuple, Mapping], readings: int, *,
               screen_floor: Optional[float] = None) -> list[tuple[Item, int]]:
    """The ``(item, reading)`` calls still to make: the readings without an answer on record, for items the screen
    did not settle."""
    out = []
    for it in items:
        if screen_floor is not None and it.cos_usual is not None and it.cos_usual >= screen_floor:
            continue
        out += [(it, r) for r in range(readings) if (it.request_sha256, r) not in answers]
    return out


def counts(decisions: Sequence[Mapping]) -> dict:
    c = Counter(d["decision"] or "no_answer" for d in decisions)
    out = {k: c.get(k, 0) for k in ("fits", "relabel", "no_better_label", "no_answer")}
    out["screened_fits"] = sum(1 for d in decisions if d.get("decided_by") == "screen")
    out["by_verdict"] = dict(sorted(Counter(d["verdict"] or "no_answer" for d in decisions).items()))
    return out


# --------------------------------------------------------------------------- the corrected candidates

def tag_source_ref(ref: Optional[str], verdict: str, original: str) -> str:
    """``<ref>;label_fit:<verdict>:<original label>`` (the route and the original label, after the generator's own
    reference); ``label_fit:<verdict>:<original>`` when the candidate had none."""
    tag = f"{verdict}:{original}"
    return f"{ref}{REF_TAG}{tag}" if ref else f"{REF_TAG[1:]}{tag}"


def split_source_ref(ref: Optional[str]) -> tuple[Optional[str], Optional[dict]]:
    """``(the generator's own source_ref, {"verdict", "original"} | None)``: the inverse of :func:`tag_source_ref`."""
    if not ref:
        return ref, None
    head = REF_TAG[1:]
    if REF_TAG in ref:
        base, _, tail = ref.rpartition(REF_TAG)
    elif ref.startswith(head):
        base, tail = None, ref[len(head):]
    else:
        return ref, None
    verdict, _, original = tail.partition(":")
    return base, {"verdict": verdict, "original": original}


def candidate_gloss(c: Candidate) -> Optional[str]:
    return _clean(c.gloss_hint)


def corrected_candidates(cands: Sequence[Candidate], decisions: Sequence[Mapping]) -> tuple[list[Candidate], dict]:
    """``(the corrected candidates, counts)`` (module docstring).  A candidate without a gloss hint has no pair and
    is kept as it is."""
    by_id = {d["id"]: d for d in decisions}
    out: list[Candidate] = []
    n = Counter()
    for c in cands:
        g = candidate_gloss(c)
        d = by_id.get(pair_id(c.surface, g)) if g else None
        if d is None:
            out.append(c)
            n["kept_no_gloss" if not g else "kept_not_checked"] += 1
            continue
        if d["decision"] != "relabel":
            out.append(c)
            n[{"fits": "kept_fits", "no_better_label": "kept_no_better_label"}.get(d["decision"], "kept_no_answer")] += 1
            continue
        for p in d["proposals"]:
            out.append(Candidate(surface=p["label"], generator=c.generator, run_id=c.run_id, rank=c.rank,
                                 score=c.score, gloss_hint=c.gloss_hint, sense_id=c.sense_id,
                                 source_ref=tag_source_ref(c.source_ref, d["verdict"], c.surface),
                                 partner_hint=c.partner_hint))
            n["relabelled_out"] += 1
        n["relabelled_in"] += 1
    return out, dict(sorted(n.items()))


def pairs_of(cands: Sequence[Candidate]) -> list[tuple[str, str]]:
    return [(c.surface, candidate_gloss(c)) for c in cands if candidate_gloss(c)]


# --------------------------------------------------------------------------- validation against marks

#: Header names of a sheet's mark column (the review-sheet rule, 2026-10-15: the mark column early, found by its
#: header); a sheet with none of them has its mark last (the structural pilot's of 2026-10-14, marked in "Roger").
MARK_HEADERS = ("mark", "roger", "t/n/d")


def parse_marks(path: Path) -> list[dict]:
    """The rows of a precision-sample sheet (``structural_generator.py report``'s ``roger_sample.md``): ``{"n",
    "label", "gloss", "mark", "should_fit"}``, ``should_fit`` False for a mark starting with "?" (an odd sense),
    True for any other mark, None for an empty one.  The columns are found by the header row's names: ``#``,
    ``label``, the gloss (a header containing "gloss": the one naming the generator's when there are several, else
    the first), and the mark (:data:`MARK_HEADERS`, else the last column)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()

    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]
    header = None
    out = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cs = cells(line)
        if header is None:
            low = [c.lower() for c in cs]
            glosses = [i for i, c in enumerate(low) if "gloss" in c]
            if "label" in low and glosses:
                gen = [i for i in glosses if "generator" in low[i]]
                mark = next((low.index(h) for h in MARK_HEADERS if h in low), len(cs) - 1)
                header = {"n": low.index("#") if "#" in low else None, "label": low.index("label"),
                          "gloss": (gen or glosses)[0], "mark": mark}
            continue
        if set("".join(cs)) <= set("-: "):
            continue
        if len(cs) <= header["mark"]:
            continue
        mark = cs[header["mark"]]
        out.append({"n": cs[header["n"]] if header["n"] is not None else str(len(out) + 1),
                    "label": cs[header["label"]], "gloss": cs[header["gloss"]], "mark": mark,
                    "should_fit": None if not mark else not mark.startswith("?")})
    if header is None:
        raise ValueError(f"{path}: no table with label and gloss columns")
    return out


def confusion(marks: Sequence[Mapping], decisions: Sequence[Mapping], *, exclude: Iterable[str] = ()) -> dict:
    """The check's decision against the marks: ``{"table": {(should, got): n}, "n", "flag_precision",
    "flag_recall", "agreement", "disagreements": [...]}``; ``should`` "not_fit" / "fit", ``got`` "not_fit" (relabel
    or no_better_label) / "fit" / "no_answer".  Rows in ``exclude`` (labels, case ignored) and unmarked rows are
    left out."""
    ex = {x.lower() for x in exclude}
    by_id = {d["id"]: d for d in decisions}
    table = Counter()
    dis = []
    for m in marks:
        if m["should_fit"] is None or m["label"].lower() in ex:
            continue
        d = by_id.get(pair_id(m["label"], m["gloss"]))
        should = "fit" if m["should_fit"] else "not_fit"
        dec = (d or {}).get("decision")
        got = "no_answer" if dec is None else "fit" if dec == "fits" else "not_fit"
        table[(should, got)] += 1
        if got != should:
            dis.append({"n": m["n"], "label": m["label"], "mark": m["mark"], "should": should, "got": got,
                        "verdict": (d or {}).get("verdict"), "votes": (d or {}).get("votes"),
                        "proposals": [p["label"] for p in (d or {}).get("proposals") or []],
                        "reasons": (d or {}).get("reasons") or []})
    tp, fp, fn = table[("not_fit", "not_fit")], table[("fit", "not_fit")], table[("not_fit", "fit")]
    n = sum(table.values())
    return {"table": {f"{a}|{b}": table[(a, b)] for a in ("not_fit", "fit") for b in ("not_fit", "fit", "no_answer")},
            "n": n, "flag_precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "flag_recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "agreement": round((tp + table[("fit", "fit")]) / n, 3) if n else None, "disagreements": dis}


def format_confusion(conf: Mapping, title: str) -> str:
    t = conf["table"]
    head = "Roger \\ check"
    rows = [f"{title} (n={conf['n']}):", f"  {head:22s} {'not fit':>8s} {'fits':>8s} {'no answer':>10s}"]
    for a, name in (("not_fit", "'?' (should not fit)"), ("fit", "other (should fit)")):
        rows.append(f"  {name:22s} {t[f'{a}|not_fit']:>8d} {t[f'{a}|fit']:>8d} {t[f'{a}|no_answer']:>10d}")
    rows.append(f"  flags: precision {conf['flag_precision']}, recall {conf['flag_recall']}; agreement "
                f"{conf['agreement']}")
    return "\n".join(rows)


def _median(xs: Sequence[float]) -> Optional[float]:
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return round(xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2, 3)


def screen_effect(marks: Sequence[Mapping], items: Sequence[Item],
                  floors: Sequence[float] = (0.5, 0.6, 0.7, 0.8)) -> dict:
    """What the cosine screen would do on the marked rows: the median usual-sense and max cosines by mark, and for
    each floor how many rows it would settle as fitting with no call and how many of those Roger marked "?"."""
    by_id = {it.id: it for it in items}
    rows = [(m, by_id.get(pair_id(m["label"], m["gloss"]))) for m in marks if m["should_fit"] is not None]
    rows = [(m, it) for m, it in rows if it is not None]
    out: dict = {"n_with_cosine": sum(1 for _, it in rows if it.cos_usual is not None)}
    for key in ("cos_usual", "cos_max"):
        out[f"median_{key}"] = {
            "should_not_fit": _median([getattr(it, key) for m, it in rows
                                       if not m["should_fit"] and getattr(it, key) is not None]),
            "should_fit": _median([getattr(it, key) for m, it in rows
                                   if m["should_fit"] and getattr(it, key) is not None])}
    out["floors"] = []
    for f in floors:
        hit = [(m, it) for m, it in rows if it.cos_usual is not None and it.cos_usual >= f]
        out["floors"].append({"floor": f, "settled_without_call": len(hit),
                              "of_them_marked_odd": sum(1 for m, _ in hit if not m["should_fit"])})
    return out


# --------------------------------------------------------------------------- readouts

def _link(target: Path, doc: Path) -> str:
    return os.path.relpath(Path(target).resolve(), Path(doc).resolve().parent)


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "/").replace("\n", " ")


def render_check_readout(decisions: Sequence[Mapping], *, source: str, n_candidates: int, cand_counts: Mapping,
                         rubric: Mapping, model: str, readings: int, usage_usd: float, doc_path: Path,
                         files: Mapping[str, Path], screen_floor: Optional[float]) -> str:
    lk = {k: f"[{Path(p).name}]({_link(p, doc_path)})" for k, p in files.items()}
    c = counts(decisions)
    lines = [
        "# Label-fit check", "",
        f"{n_candidates} candidates of {source} ({lk.get('input', 'the candidates file')}): {len(decisions)} distinct "
        f"(label, gloss) pairs asked of {model}, {readings} reading{'s' if readings != 1 else ''} each, combined by "
        f"majority (a tie does not fit), with the pinned prompt {lk.get('rubric', rubric['name'])} version "
        f"{rubric['version']} (sha `{(rubric['sha256'] or '')[:12]}`); "
        + (f"pairs whose usual-sense cosine reached {screen_floor} were taken as fitting with no call; "
           if screen_floor is not None else "no cosine floor (the cosines are recorded only); ")
        + f"spend on record ${usage_usd:.4f} ({lk.get('usage', 'usage.json')}).  Every response: "
        f"{lk.get('responses', 'responses.jsonl')}; every decision: {lk.get('decisions', 'decisions.json')}; the "
        f"corrected candidates: {lk.get('candidates', 'candidates.jsonl')}.", "",
        "| decision | pairs |", "| --- | ---: |", *[f"| {k} | {c[k]} |" for k in ("fits", "relabel",
                                                                                  "no_better_label", "no_answer")],
        "", f"Candidates: {json.dumps(dict(cand_counts))}.", "",
    ]

    def table(title, sel):
        if not sel:
            return [f"## {title} (0)", "", "None.", ""]
        out = [f"## {title} ({len(sel)})", "", "| label | gloss | verdict (votes) | new label (support) | usual "
               "sense shown | reasons |", "| --- | --- | --- | --- | --- | --- |"]
        for d in sel:
            ctx = d.get("context") or {}
            usual = ctx.get("usual_sense") or (ctx.get("dictionary_senses") or [""])[0]
            props = ", ".join(f"{p['label']} ({p['support']})" for p in d.get("proposals") or [])
            out.append(f"| {_md(d['label'])} | {_md(d['gloss'])} | {d.get('verdict')} ({', '.join(d.get('votes') or [])})"
                       f" | {_md(props)} | {_md(usual)} | {_md(' / '.join(d.get('reasons') or []))} |")
        return out + [""]
    lines += table("Relabelled", [d for d in decisions if d["decision"] == "relabel"])
    lines += table("Does not fit, no usable better label (kept as it is)",
                   [d for d in decisions if d["decision"] == "no_better_label"])
    lines += table("No answer yet", [d for d in decisions if d["decision"] is None])
    lines += [f"The {c['fits']} pairs that fit are in {lk.get('decisions', 'decisions.json')}.", ""]
    return "\n".join(lines)


def render_validate_readout(marks: Sequence[Mapping], decisions: Sequence[Mapping], confs: Mapping[str, Mapping],
                            screen: Mapping, *, rubric: Mapping, model: str, readings: int, usage_usd: float,
                            doc_path: Path, files: Mapping[str, Path]) -> str:
    lk = {k: f"[{Path(p).name}]({_link(p, doc_path)})" for k, p in files.items()}
    lines = [f"# Label-fit check against Roger's marks: {model}", "",
             f"The {len(marks)} rows of {lk.get('marks', 'the sample')} (a mark starting with `?` should not fit, any "
             f"other mark should), asked of {model}, {readings} reading{'s' if readings != 1 else ''} each, with "
             f"{lk.get('rubric', rubric['name'])} version {rubric['version']}; spend on record (every model) "
             f"${usage_usd:.4f}.  Responses: {lk.get('responses', 'responses.jsonl')}.", ""]
    for title, conf in confs.items():
        lines += ["```text", format_confusion(conf, title), "```", ""]
    main = next(iter(confs.values()))
    lines += ["## Disagreements", "", "| # | label | Roger | check | votes | proposals | reasons |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in main["disagreements"]:
        lines.append(f"| {d['n']} | {_md(d['label'])} | {_md(d['mark'])} | {d['got']} ({d['verdict']}) | "
                     f"{', '.join(d['votes'] or [])} | {_md(', '.join(d['proposals']))} | "
                     f"{_md(' / '.join(d['reasons']))} |")
    lines += ["", "## The cosine pre-screen (reported only)", "", "```json", json.dumps(screen, indent=1), "```", "",
              "## Every row", "", "| # | label | Roger | decision | votes | proposals | cos usual | cos max |",
              "| --- | --- | --- | --- | --- | --- | ---: | ---: |"]
    by_id = {d["id"]: d for d in decisions}
    for m in marks:
        d = by_id.get(pair_id(m["label"], m["gloss"])) or {}
        lines.append(f"| {m['n']} | {_md(m['label'])} | {_md(m['mark'])} | {d.get('decision')} | "
                     f"{', '.join(d.get('votes') or [])} | "
                     f"{_md(', '.join(p['label'] for p in d.get('proposals') or []))} | {d.get('cos_usual')} | "
                     f"{d.get('cos_max')} |")
    return "\n".join(lines) + "\n"


def decisions_doc(decisions: Sequence[Mapping], *, rubric: Mapping, model: str, readings: int,
                  screen_floor: Optional[float], embedder: Optional[str], extra: Optional[Mapping] = None) -> dict:
    return {"rubric": rubric["name"], "rubric_version": rubric["version"], "prompt_sha256": rubric["sha256"],
            "model": model, "readings": readings, "parser_version": PARSER_VERSION, "screen_floor": screen_floor,
            "embedder": embedder, "counts": counts(decisions), **dict(extra or {}),
            "decisions": [dict(d) for d in decisions]}


__all__ = ["RUBRIC_NAME", "DEFAULT_MODEL", "MODELS", "MAX_TOKENS", "VERDICTS", "PARSER_VERSION", "DEFAULT_READINGS",
           "Item", "oewn_senses", "recorded_senses", "sense_context", "build_user", "load_rubric", "request_sha256",
           "pair_id", "build_items", "gloss_text", "cosines", "parse_answer", "read_records", "answers_on_record",
           "ask", "estimate", "combine", "decide", "todo_calls", "counts", "tag_source_ref", "split_source_ref",
           "corrected_candidates", "pairs_of", "parse_marks", "confusion", "format_confusion", "screen_effect",
           "render_check_readout", "render_validate_readout", "decisions_doc"]
