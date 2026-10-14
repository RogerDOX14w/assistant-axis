"""The spelling-repair check (QUESTIONS 35; Roger, 2026-10-14): which listed repair suggestions are real typos.

The ingest (:func:`.ingest.build_table`) applies the one-edit repair only to :data:`.ingest.SAFE_REPAIR_KINDS` and
lists the other one-edit matches as ``repair_suggestions_list`` in ``ingest_counts.json`` (706 on the 2026-10-12
table).  :func:`select_suggestions` keeps those whose suggested word is **new**: its stem
(``normalize_candidate(repaired).stem``) is not the stem of any row of the census table, which is how the QUESTIONS
figure was made (392 point to a word the lists already hold, 314 to a new one).  Each is asked of Sonnet 5.5 once
(``readings`` times, combined by majority, when asked for more): is the entry a typing or transcription slip for the
suggested word (``typo``), a word in its own right (``real_word``), or ``unsure``?

**The prompt** is the pinned rubric ``reports/trait_gap_generation/rubrics/census_repair_check.md``
(:data:`RUBRIC_NAME`, loaded through :mod:`assistant_axis.gapgen.split_rubrics`; :func:`load_rubric` refuses a text
that is not its latest pin).  The user turn (:func:`build_user`) is one JSON object: the entry as the file spells
it, the suggested word, and the two entries before and the two after it in the same column (:func:`neighbours`,
from the census table's own ``allport.raw`` / ``allport.line``, so no download is needed).  No corpus label is
shown, so the judge display form does not apply.  The answer asks for a short reason, then the verdict (Sonnet 5.5
refuses "think first" fields, ``.claude/rules/judging.md``); no temperature (Sonnet 5.5 refuses one); ``max_tokens``
:data:`MAX_TOKENS`, the platform's figure for a thinking model.

**Records** (``responses.jsonl``, append-only): every response is recorded before it is parsed, with its request's
sha256 (:func:`request_sha256`: system and user turns), the rubric's version and sha, the reading index, the
billed usage (``usage_raw``, ``charged_as``: :func:`assistant_axis.gapgen.cost.resume_usage` reads them) and the
parse.  A refusal (``stop_reason: "refusal"``) is a failed call: recorded, counted, never an empty answer
(:func:`parse_verdict`).  A resume reuses every parsed answer whose request sha, reading and model match
(:func:`answers_on_record`), so only the missing ones are sent.

**Accepted repairs** are the suggestions whose combined verdict is ``typo``; :func:`candidates_for` makes one census
candidate per accepted suggestion (surface the repaired word, ``source_ref``
``allport:<column>:<line>:repair:<entry>-><repaired>``), which the CLI submits through the registry's usual path.
The census lists and table are never edited.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import Estimate
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import Candidate, utc_now
from assistant_axis.gapgen.split_runner import MAX_TOKENS_THINKING
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from . import GENERATOR

RUBRIC_NAME = "census_repair_check"
DEFAULT_MODEL = "claude-sonnet-5-5"
#: The platform's ``max_tokens`` for a model that thinks (``split_runner.MAX_TOKENS_THINKING``, 2000).
MAX_TOKENS = MAX_TOKENS_THINKING

VERDICTS: tuple[str, ...] = ("typo", "real_word", "unsure")
ANSWER_KEYS: tuple[str, ...] = ("reason", "verdict")
#: 1 (2026-10-14): one JSON object (a code fence around it is accepted with a note), ``reason`` a non-empty string,
#: ``verdict`` one of :data:`VERDICTS` (spaces and hyphens read as underscores, case ignored).
#: 2 (2026-10-14): one JSON object after leading prose is accepted (382 of 942 Sonnet replies wrote a sentence first).
PARSER_VERSION = 2
N_NEIGHBOURS = 2
CONCURRENCY = 8
#: For the estimate: the system prompt is about 2,100 characters (about 550 tokens; not cached, under Sonnet's
#: minimum), the user turn about 40; the answer about 60 tokens, with Sonnet 5.5's adaptive thinking on top (allowed
#: for generously).
EST_IN_TOKENS, EST_OUT_TOKENS = 700, 400
RESPONSES_NAME = "responses.jsonl"
USAGE_NAME = "usage.json"
VERDICTS_NAME = "verdicts.json"
READOUT_NAME = "readout.md"


class RubricNotPinned(RuntimeError):
    """The prompt's text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- selection

@dataclass(frozen=True)
class Suggestion:
    """One listed repair suggestion (``ingest_counts.json``'s ``repair_suggestions_list`` entry)."""
    raw: str
    column: str
    line: int
    repaired: str
    kind: str

    @property
    def id(self) -> str:
        return f"{self.column}:{self.line}"

    @property
    def entry(self) -> str:
        """The entry as the file spells it (whitespace trimmed)."""
        return " ".join(str(self.raw).split())

    @property
    def source_ref(self) -> str:
        return f"allport:{self.column}:{self.line}:repair:{self.entry.lower()}->{self.repaired}"


def _stem(s: str) -> Optional[str]:
    try:
        return normalize_candidate(s).stem
    except ValueError:
        return None


def select_suggestions(suggestions: Sequence[Mapping], table_rows: Sequence) -> tuple[list[Suggestion], dict]:
    """``(the suggestions whose repaired word is new, counts)``: new = its stem is no census table row's stem (the
    split of QUESTIONS 35).  ``table_rows``: :class:`.ingest.TableRow` objects or their dicts.  In list order."""
    stems = {(r.stem if hasattr(r, "stem") else r.get("stem")) for r in table_rows}
    stems.discard(None)
    out, held = [], 0
    for d in suggestions:
        s = Suggestion(raw=str(d["raw"]), column=str(d["column"]), line=int(d["line"]), repaired=str(d["repaired"]),
                       kind=str(d.get("kind") or ""))
        if _stem(s.repaired) in stems:
            held += 1
        else:
            out.append(s)
    return out, {"n_suggestions": len(suggestions), "n_held_elsewhere": held, "n_new": len(out),
                 "by_kind_new": dict(sorted(Counter(s.kind for s in out).items()))}


def column_entries(table_rows: Sequence) -> dict[str, dict[int, str]]:
    """``{column: {line: raw entry}}`` from the table's ``allport`` blocks (every entry the table kept, malformed
    rows included)."""
    out: dict[str, dict[int, str]] = {}
    for r in table_rows:
        a = (r.allport if hasattr(r, "allport") else r.get("allport")) or {}
        for col, ln in (a.get("line") or {}).items():
            raw = (a.get("raw") or {}).get(col)
            if raw is not None and ln is not None:
                out.setdefault(col, {})[int(ln)] = " ".join(str(raw).split())
    return out


def neighbours(s: Suggestion, entries: Mapping[str, Mapping[int, str]], k: int = N_NEIGHBOURS
               ) -> tuple[list[str], list[str]]:
    """The ``k`` nearest entries before and after ``s`` in its column, in list order (lines the table did not keep
    are skipped)."""
    col = entries.get(s.column) or {}
    lines = sorted(col)
    before = [col[x] for x in lines if x < s.line][-k:]
    after = [col[x] for x in lines if x > s.line][:k]
    return before, after


def build_user(s: Suggestion, before: Sequence[str], after: Sequence[str]) -> str:
    return json.dumps({"entry": s.entry, "suggested": s.repaired, "before": list(before), "after": list(after)},
                      ensure_ascii=False)


# --------------------------------------------------------------------------- the prompt

def load_rubric(rubrics_dir: Optional[Path] = None) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin."""
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == RUBRIC_NAME]
    if probs:
        raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
    text = sr.load_prompt(RUBRIC_NAME, rubrics_dir)
    version, sha = sr.current_versions(rubrics_dir, (RUBRIC_NAME,))[RUBRIC_NAME]
    path = sr.rubric_path(RUBRIC_NAME, rubrics_dir)
    try:
        from assistant_axis.gapgen.paths import REPO_ROOT
        rel = str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        rel = str(path)
    return {"name": RUBRIC_NAME, "text": text, "version": version, "sha256": sha, "file": rel}


def request_sha256(system: str, user: str) -> str:
    """The request's identity for a resume: the system and user turns as sent."""
    return hashlib.sha256(json.dumps([system, user], ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass
class Item:
    suggestion: Suggestion
    user: str
    request_sha256: str
    before: list
    after: list


def build_items(selected: Sequence[Suggestion], table_rows: Sequence, system: str) -> list[Item]:
    entries = column_entries(table_rows)
    out = []
    for s in selected:
        b, a = neighbours(s, entries)
        u = build_user(s, b, a)
        out.append(Item(suggestion=s, user=u, request_sha256=request_sha256(system, u), before=b, after=a))
    return out


# --------------------------------------------------------------------------- the parser

def parse_verdict(text: Optional[str], stop_reason: Optional[str] = None
                  ) -> tuple[Optional[dict], Optional[str], list]:
    """``(answer, None, notes)`` or ``(None, "<kind>: <detail>", notes)``; kinds: refusal, no_response, empty,
    not_one_object, not_json, missing_key, bad_value.  A refusal is a failed call whatever text came with it."""
    notes: list = []
    if stop_reason == "refusal":
        return None, "refusal: the model declined to answer", notes
    if text is None:
        return None, "no_response: the request failed", notes
    t = text.strip()
    if not t:
        return None, "empty: no text", notes
    if t.startswith("```"):
        body = t.split("\n", 1)[1] if "\n" in t else ""
        if body.rstrip().endswith("```"):
            t = body.rstrip()[:-3].strip()
            notes.append("code fence removed")
    if not t.startswith("{") and t.endswith("}"):
        # Sonnet 5.5 often writes its reason as a sentence, then the object: take the object that ends the text
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
    reason = obj["reason"]
    if not isinstance(reason, str) or not reason.strip():
        return None, "bad_value: reason", notes
    v = obj["verdict"]
    v = " ".join(str(v).split()).lower().replace(" ", "_").replace("-", "_") if isinstance(v, str) else None
    if v not in VERDICTS:
        return None, f"bad_value: verdict {obj['verdict']!r} (one of {', '.join(VERDICTS)})", notes
    if v != obj["verdict"]:
        notes.append("verdict normalised")
    extra = sorted(set(obj) - set(ANSWER_KEYS))
    if extra:
        notes.append(f"extra keys {extra}")
    return {"reason": " ".join(reason.split()), "verdict": v}, None, notes


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
        if r.get("model") != model or not r.get("request_sha256"):
            continue
        r = dict(r)
        if not r.get("parsed") and r.get("text") and int(r.get("parser_version") or 0) < PARSER_VERSION:
            parsed, err, notes = parse_verdict(r.get("text"), r.get("stop_reason"))   # re-read with this parser
            if parsed:
                r.update(parsed=parsed, parse_error=None, notes=list(r.get("notes") or []) + notes + [
                    f"re-parsed with parser {PARSER_VERSION}"])
        if r.get("parsed"):
            out[(r["request_sha256"], int(r.get("reading") or 0))] = r
    return out


@dataclass
class CheckResult:
    n_calls: int = 0
    n_ok: int = 0
    error_kinds: dict = field(default_factory=dict)
    stopped_by_budget: bool = False


async def check(todo: Sequence[tuple[Item, int]], *, client, rubric: Mapping, model: str = DEFAULT_MODEL,
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
            parsed, err, notes = parse_verdict(text, meta.get("stop_reason"))
            s = item.suggestion
            rec = {"id": s.id, "entry": s.entry, "repaired": s.repaired, "column": s.column, "line": s.line,
                   "kind": s.kind, "reading": reading, "model": model, "rubric": rubric["name"],
                   "prompt_version": rubric["version"], "prompt_sha256": rubric["sha256"],
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
    est.add("repair check", model, n_calls, EST_IN_TOKENS, EST_OUT_TOKENS)
    return est


# --------------------------------------------------------------------------- verdicts

def combine(verdicts: Sequence[str]) -> Optional[str]:
    """The majority verdict of the readings answered; a tie between the top two is ``unsure``; None when none."""
    c = Counter(verdicts).most_common()
    if not c:
        return None
    if len(c) > 1 and c[0][1] == c[1][1]:
        return "unsure"
    return c[0][0]


def verdict_rows(items: Sequence[Item], answers: Mapping[tuple, Mapping], readings: int) -> list[dict]:
    """One row per selected suggestion: its readings' answers and the combined verdict (None: no answer yet)."""
    out = []
    for it in items:
        got = [answers[(it.request_sha256, r)] for r in range(readings) if (it.request_sha256, r) in answers]
        votes = [g["parsed"]["verdict"] for g in got]
        s = it.suggestion
        out.append({"id": s.id, "entry": s.entry, "repaired": s.repaired, "column": s.column, "line": s.line,
                    "kind": s.kind, "source_ref": s.source_ref, "before": it.before, "after": it.after,
                    "verdict": combine(votes), "votes": votes, "n_readings": len(got),
                    "reasons": [g["parsed"]["reason"] for g in got]})
    return out


def counts_by_verdict(rows: Sequence[Mapping]) -> dict:
    c = Counter(r["verdict"] or "no_answer" for r in rows)
    return {v: c.get(v, 0) for v in (*VERDICTS, "no_answer")}


def _link(target: Path, doc: Path) -> str:
    return os.path.relpath(Path(target).resolve(), Path(doc).resolve().parent)


def render_readout(rows: Sequence[Mapping], *, selection: Mapping, rubric: Mapping, model: str, readings: int,
                   usage_usd: float, doc_path: Path, files: Mapping[str, Path]) -> str:
    """The readout: the selection, counts by verdict, the accepted repairs (verdict ``typo``) listed, then the
    ``unsure`` ones and the suggestions with no answer.  Every file named is a link relative to the readout."""
    by = counts_by_verdict(rows)
    lk = {k: f"[{Path(p).name}]({_link(p, doc_path)})" for k, p in files.items()}
    lines = [
        "# Census spelling-repair check (QUESTIONS 35)", "",
        f"Of the {selection['n_suggestions']} one-edit repair suggestions listed in {lk.get('counts', 'ingest_counts.json')} "
        f"(`repair_suggestions_list`), {selection['n_held_elsewhere']} point to a word the census lists already hold and "
        f"{selection['n_new']} to a new word; those {selection['n_new']} were asked of {model} "
        f"({readings} reading{'s' if readings != 1 else ''} each, majority verdict), with the pinned prompt "
        f"{lk.get('rubric', rubric['name'])} version {rubric['version']} (sha `{rubric['sha256'][:12]}`).  "
        f"Spend on record ${usage_usd:.4f} ({lk.get('usage', 'usage.json')}).  Every response: "
        f"{lk.get('responses', 'responses.jsonl')}; every verdict: {lk.get('verdicts', 'verdicts.json')}.", "",
        "| verdict | suggestions |", "| --- | ---: |",
        *[f"| {v} | {n} |" for v, n in by.items()], "",
        "A **typo** is accepted: its repaired word is what `repair-check --submit` submits as a census candidate.  "
        "Nothing in the census lists or the table is changed.", "",
    ]

    def table(title: str, sel: list) -> list[str]:
        if not sel:
            return [f"## {title} (0)", "", "None.", ""]
        out = [f"## {title} ({len(sel)})", "", "| entry | repair | column:line | kind | neighbours | reason |",
               "| --- | --- | --- | --- | --- | --- |"]
        for r in sel:
            nb = ", ".join(r["before"]) + " | " + ", ".join(r["after"])
            reason = (r["reasons"][0] if r["reasons"] else "").replace("|", "/")
            out.append(f"| {r['entry']} | {r['repaired']} | {r['id']} | {r['kind']} | {nb.replace('|', '/')} | "
                       f"{reason} |")
        return out + [""]

    lines += table("Accepted repairs (typo)", [r for r in rows if r["verdict"] == "typo"])
    lines += table("Unsure", [r for r in rows if r["verdict"] == "unsure"])
    lines += table("No answer yet", [r for r in rows if r["verdict"] is None])
    n_real = by["real_word"]
    lines += [f"The {n_real} `real_word` verdicts are in {lk.get('verdicts', 'verdicts.json')}.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- submission

def candidates_for(rows: Sequence[Mapping], run_id: str, *, senses: Optional[Callable] = None) -> list[Candidate]:
    """One census candidate per accepted suggestion (verdict ``typo``), in list order: surface the repaired word,
    ``source_ref`` naming the entry and the repair, ``rank`` the position among the accepted, ``gloss_hint`` the
    OEWN person sense as the table's rows get it (:mod:`.glosshint`) when ``senses`` is given."""
    from .glosshint import gloss_hint, person_sense
    out = []
    for i, r in enumerate((r for r in rows if r["verdict"] == "typo"), 1):
        label = normalize_candidate(r["repaired"]).label
        gh = gloss_hint(label, person_sense(senses(r["repaired"])), [r["column"]], in_tda=False) if senses else None
        out.append(Candidate(surface=r["repaired"], generator=GENERATOR, run_id=run_id, rank=i, score=None,
                             gloss_hint=gh, sense_id=1, source_ref=r["source_ref"]))
    return out


def rows_as_json(rows: Sequence[Mapping], *, selection: Mapping, rubric: Mapping, model: str, readings: int) -> dict:
    return {"rubric": rubric["name"], "rubric_version": rubric["version"], "prompt_sha256": rubric["sha256"],
            "model": model, "readings": readings, "parser_version": PARSER_VERSION, "selection": dict(selection),
            "counts": counts_by_verdict(rows), "rows": [dict(r) for r in rows]}


__all__ = ["RUBRIC_NAME", "DEFAULT_MODEL", "MAX_TOKENS", "VERDICTS", "Suggestion", "Item", "select_suggestions",
           "column_entries", "neighbours", "build_user", "load_rubric", "request_sha256", "build_items",
           "parse_verdict", "read_records", "answers_on_record", "check", "estimate", "combine", "verdict_rows",
           "counts_by_verdict", "render_readout", "candidates_for", "rows_as_json"]
