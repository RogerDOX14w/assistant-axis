"""The head-scope check: one Haiku 5.5 rating per Roget head of whether its adjectives describe a
person's character (Roger, 2026-10-08, "The Haiku test SG"; QUESTIONS 44).

Why: the dispositional classes (IV-VI) also hold heads that are not about character at all (Dearness,
Cheapness, Debt and Purchase in Possessive relations; Misnomer and Correspondence in Means of
communicating ideas; Jewelry in Personal affections).  In the pilot (``runs/roget/2026-10-08-pilot``)
32 of the 33 words M1 turned away came from such heads.  Whole sections cannot be dropped (Possessive
relations also holds Liberality, Economy, Parsimony and Prodigality), so the check is head by head.

* **Which heads**: every head of the coverage map's scope (the dispositional heads and the Class I-III
  heads brought in by a label); a head with no adjectives is not sent (``skipped: "no_adjectives"``).
* **Payload** (:func:`render_user`): about 20 heads per call, in text order (:func:`make_batches`), each
  with its id (the head's number), title, class and section titles, and its first
  :data:`MAX_ADJECTIVES` distinct adjectives in Roget's order.  The rubric is the fenced block of
  ``reports/trait_gap_generation/rubrics/roget_head_scope.md``, pinned in that directory's
  ``versions.json`` (:func:`load_rubric` refuses a text that is not its latest pin).
* **Answer**: per head a one-sentence reason, then ``character``: 2 (most adjectives can describe a
  person's character), 1 (some can: a mixed head), 0 (few or none can).  A head whose answer is
  missing or malformed is sent once more, alone with the others missing from its call
  (:func:`rate_batches`); after that it stays unrated (``rating: null`` with an ``error``).
* **Output**: ``data/candidates/roget/head_scope.json`` (provenance envelope; one row per head in scope:
  id, title, class, section, n_adjectives, rating, reason, model, rubric version), the cumulative
  ``head_scope_usage.json`` beside it, and every response in ``head_scope_responses.jsonl``.
* **Use**: the harvest skips heads rated 0 (``harvest(..., head_scope=...)``, drop reason
  ``not_character``); the coverage map reports them apart as "not character" and leaves them out of
  the covered / partly / uncovered counts (``coverage(..., ratings=...)``).  Heads rated 1 or 2, and
  unrated heads, are treated as before.

The CLI is ``data_analysis/gap_generation/roget_generate.py head-scope``.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage

from .parse import Head, RogetIndex

RUBRIC_NAME = "roget_head_scope"
DEFAULT_MODEL = "claude-haiku-5-5"
MAX_ADJECTIVES = 20
BATCH_SIZE = 20
CONCURRENCY = 4
#: Haiku 5.5 thinks adaptively and its thinking counts against max_tokens; 20 rows of about 40 tokens
#: and the thinking stay well under this.
MAX_TOKENS = 8000
RATINGS = (0, 1, 2)
FILE_NAME = "head_scope.json"
USAGE_NAME = "head_scope_usage.json"
RESPONSES_NAME = "head_scope_responses.jsonl"
#: Estimate, measured on the three full runs of 2026-10-08 (90 calls, head_scope_responses.jsonl): about
#: 2.5 characters of prompt per input token (the JSON payload tokenizes densely on Haiku 5.5's tokenizer)
#: and about 157 output tokens per head, thinking included (about 3,080 a call of 19-20 heads).  The first
#: estimate (4 characters x 1.3, 70 a head) under-stated a run by 40% ($0.034 against $0.055).
CHARS_PER_TOKEN = 4.0
TOKENIZER_FACTOR = 1.6
OUT_BASE_TOKENS, OUT_PER_HEAD_TOKENS = 100, 155

_ROMAN = re.compile(r"^[IVXL]+\.\s*")


class RubricNotPinned(RuntimeError):
    """The rubric text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- items

def section_title(section: Optional[str]) -> str:
    """``"IV. Possessive relations"`` -> ``"Possessive relations"``."""
    return _ROMAN.sub("", (section or "").strip())


def display_title(title: str) -> str:
    """The head's title as the model sees it: ``". Painfulness"`` (head 830, as parsed) -> ``"Painfulness"``."""
    return title.strip().lstrip(". ").strip()


def unique_adjectives(head: Head) -> list[str]:
    return list(dict.fromkeys(a.strip() for a in head.items("Adj") if a.strip()))


@dataclass
class HeadItem:
    id: str
    title: str
    klass: str
    class_title: str
    section: str
    adjectives: list
    n_adjectives: int

    def payload(self) -> dict:
        """What the model sees of the head (display form: titles without their numbering)."""
        return {"id": self.id, "title": display_title(self.title), "class": self.class_title,
                "section": section_title(self.section), "adjectives": list(self.adjectives)}


def head_item(head: Head, *, max_adjectives: int = MAX_ADJECTIVES) -> HeadItem:
    adj = unique_adjectives(head)
    return HeadItem(id=head.id, title=head.title, klass=head.klass, class_title=head.class_title,
                    section=head.section or "", adjectives=adj[:max_adjectives], n_adjectives=len(adj))


def scope_items(index: RogetIndex, head_ids: Sequence[str], *, max_adjectives: int = MAX_ADJECTIVES
                ) -> tuple[list[HeadItem], list[str]]:
    """``(items to rate, ids skipped for having no adjectives)``, both in the order given."""
    items, skipped = [], []
    for h in head_ids:
        it = head_item(index.heads[h], max_adjectives=max_adjectives)
        (items if it.adjectives else skipped).append(it if it.adjectives else h)
    return items, skipped


def make_batches(items: Sequence[HeadItem], size: int = BATCH_SIZE) -> list[list[HeadItem]]:
    """Consecutive batches in the order given, as even in size as possible, none over ``size``."""
    items = list(items)
    if not items:
        return []
    n = math.ceil(len(items) / size)
    base, extra = divmod(len(items), n)
    out, i = [], 0
    for b in range(n):
        k = base + (1 if b < extra else 0)
        out.append(items[i:i + k])
        i += k
    return out


def render_user(batch: Sequence[HeadItem]) -> str:
    """The user turn: one JSON object, one head per line."""
    rows = [" " + json.dumps(it.payload(), ensure_ascii=False) for it in batch]
    return '{"heads": [\n' + ",\n".join(rows) + "\n ]}"


# --------------------------------------------------------------------------- rubric

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


def should_cache(system: str, model: str) -> bool:
    """The platform's rule (``split_runner.caches_system``): cache the system prompt when its estimated
    tokens clear the model's caching minimum (512 on Haiku 5.5) with a 10% margin."""
    from assistant_axis.gapgen.split_runner import caches_system
    return caches_system(system, model)


# --------------------------------------------------------------------------- parsing

def parse_ratings(text: Optional[str], ids: Sequence[str]) -> tuple[dict, dict]:
    """``(rows, errors)``: ``rows[id] = {"rating", "reason"}`` for every id answered once with a rating
    in 0-2; ``errors[id]`` says why the others are not (``missing``, ``bad rating X``, ``answered twice``,
    ``unparseable``, ``no response``).  Ids not asked for are ignored."""
    if text is None:
        return {}, {i: "no response" for i in ids}
    blob = extract_json_blob(text)
    try:
        data = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        data = None
    results = data.get("results") if isinstance(data, dict) else data if isinstance(data, list) else None
    if not isinstance(results, list):
        return {}, {i: "unparseable" for i in ids}
    want = set(ids)
    got: dict[str, list] = {}
    for r in results:
        if not isinstance(r, dict) or "id" not in r:
            continue
        rid = str(r["id"]).strip()
        if rid in want:
            got.setdefault(rid, []).append(r)
    rows, errors = {}, {}
    for i in ids:
        rs = got.get(i, [])
        if not rs:
            errors[i] = "missing"
            continue
        if len(rs) > 1:
            errors[i] = "answered twice"
            continue
        v = rs[0].get("character")
        try:
            rating = int(str(v).strip()) if not isinstance(v, bool) else None
        except (TypeError, ValueError):
            rating = None
        if rating not in RATINGS:
            errors[i] = f"bad rating {v}"
            continue
        rows[i] = {"rating": rating, "reason": str(rs[0].get("reason") or "").strip()}
    return rows, errors


# --------------------------------------------------------------------------- the calls

@dataclass
class RateResult:
    rows: dict = field(default_factory=dict)      # id -> {"rating", "reason", "attempts"}
    errors: dict = field(default_factory=dict)    # id -> why it stays unrated
    log: list = field(default_factory=list)       # one record per call
    stopped_by_budget: bool = False

    def parse_rate(self) -> tuple[int, int]:
        """``(heads rated, heads sent)``."""
        return len(self.rows), len(self.rows) + len(self.errors)


async def rate_batches(batches: Sequence[Sequence[HeadItem]], *, client, model: str, system: str, usage,
                       concurrency: int = CONCURRENCY, max_tokens: int = MAX_TOKENS, cache_system: bool = False,
                       rubric_version: Optional[int] = None, now=None) -> RateResult:
    """One call per batch, then one more for the heads its answer left out or got wrong.  A
    ``BudgetExceededError`` from a guarded ``usage`` stops the run after keeping the answer that crossed
    the cap; ``stopped_by_budget`` is then set and the heads not reached are left out of the result."""
    res = RateResult()
    sem = asyncio.Semaphore(max(1, concurrency))
    prompt_sha = sr.sha256(system)

    async def one(bi: int, batch: Sequence[HeadItem], attempt: int) -> dict:
        user = render_user(batch)
        meta: dict = {}
        exc_budget = False
        try:
            text = await call_anthropic_json(client, system=system, user=user, model=model, max_tokens=max_tokens,
                                             temperature=None, usage=usage, cache_system=cache_system, meta=meta)
        except BudgetExceededError:
            text, exc_budget = meta.get("text"), True
        ids = [it.id for it in batch]
        rows, errors = parse_ratings(text, ids)
        res.log.append({"batch": bi, "attempt": attempt, "ids": ids, "model": model, "rubric_version": rubric_version,
                        "prompt_sha256": prompt_sha, "at": now() if now else None, "user": user, "text": text,
                        "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                        "error": meta.get("error"), "parse_errors": errors})
        if exc_budget:
            res.stopped_by_budget = True
        return {"rows": rows, "errors": errors}

    async def run_batch(bi: int, batch: Sequence[HeadItem]) -> None:
        async with sem:
            if res.stopped_by_budget:
                return
            out = await one(bi, batch, 1)
            for h, r in out["rows"].items():
                res.rows[h] = {**r, "attempts": 1}
            again = [it for it in batch if it.id in out["errors"]]
            if not again:
                return
            if res.stopped_by_budget:
                res.errors.update(out["errors"])
                return
            out2 = await one(bi, again, 2)
            for h, r in out2["rows"].items():
                res.rows[h] = {**r, "attempts": 2}
            res.errors.update(out2["errors"])

    await asyncio.gather(*(run_batch(bi, b) for bi, b in enumerate(batches)))
    res.log.sort(key=lambda r: (r["batch"], r["attempt"]))
    return res


def estimate(batches: Sequence[Sequence[HeadItem]], system: str, model: str) -> dict:
    """``{"n_calls", "in_tok", "out_tok", "usd"}`` for one call per batch (retries not counted)."""
    in_tok = sum(int(round((len(system) + len(render_user(b))) / CHARS_PER_TOKEN * TOKENIZER_FACTOR)) for b in batches)
    out_tok = sum(OUT_BASE_TOKENS + OUT_PER_HEAD_TOKENS * len(b) for b in batches)
    return {"n_calls": len(batches), "in_tok": in_tok, "out_tok": out_tok,
            "usd": round(cost_for_usage(model, in_tok, out_tok), 4)}


# --------------------------------------------------------------------------- the file

ROW_KEYS = ("id", "title", "class", "class_title", "section", "n_adjectives", "n_shown", "rating", "reason", "model",
            "rubric_version", "skipped", "error")


def build_payload(index: RogetIndex, scope: Sequence[str], skipped: Sequence[str], rows: Mapping[str, Mapping],
                  errors: Mapping[str, str], *, model: str, rubric: Mapping, batch_size: int, max_adjectives: int,
                  previous: Optional[Mapping[str, Mapping]] = None, extra: Optional[dict] = None) -> dict:
    """The ``head_scope.json`` payload: one row per head of ``scope`` in the order given.  ``previous``
    (rows of an earlier run under the same rubric and model, :func:`reusable`) fills the heads not rated
    now."""
    skipped = set(skipped)
    prev = dict(previous or {})
    heads = []
    for h in scope:
        hd = index.heads[h]
        adj = unique_adjectives(hd)
        row = {"id": h, "title": hd.title, "class": hd.klass, "class_title": hd.class_title,
               "section": hd.section or "", "n_adjectives": len(adj), "n_shown": min(len(adj), max_adjectives),
               "rating": None, "reason": None, "model": None, "rubric_version": None,
               "skipped": "no_adjectives" if h in skipped else None, "error": None}
        if h in rows:
            row.update(rating=rows[h]["rating"], reason=rows[h]["reason"], model=model, rubric_version=rubric["version"])
        elif h in prev and prev[h].get("rating") is not None:
            row.update({k: prev[h].get(k) for k in ("rating", "reason", "model", "rubric_version")})
        elif h in errors:
            row.update(error=errors[h], model=model, rubric_version=rubric["version"])
        heads.append(row)
    by_rating = Counter(str(r["rating"]) for r in heads if r["rating"] is not None)
    by_class: dict[str, dict] = {}
    for r in heads:
        if r["rating"] is not None:
            d = by_class.setdefault(r["class"], {"0": 0, "1": 0, "2": 0})
            d[str(r["rating"])] += 1
    summary = {"n_scope": len(heads), "n_rated": sum(r["rating"] is not None for r in heads),
               "n_skipped_no_adjectives": sum(r["skipped"] is not None for r in heads),
               "n_unrated": sum(r["rating"] is None and r["skipped"] is None for r in heads),
               "by_rating": {k: by_rating.get(k, 0) for k in ("0", "1", "2")},
               "by_class": dict(sorted(by_class.items()))}
    out = {"rubric": {k: rubric[k] for k in ("name", "version", "sha256", "file") if k in rubric}, "model": model,
           "batch_size": batch_size, "max_adjectives": max_adjectives, "summary": summary, "heads": heads}
    if extra:
        out.update(extra)
    return out


def save(payload: dict, path: Path, *, inputs: Sequence = ()) -> Path:
    from assistant_axis.plot_metadata import json_metadata

    from .parse import dumps_one_per_line
    env = json_metadata(payload, inputs=list(inputs), title="Roget head scope (workstream 2)")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(dumps_one_per_line(env, "heads"), path)
    return path


@dataclass
class HeadScope:
    path: Path
    ratings: dict          # head id -> 0 | 1 | 2 | None
    rows: dict             # head id -> row
    rubric: dict
    model: Optional[str]
    summary: dict

    def rating(self, h: str) -> Optional[int]:
        return self.ratings.get(h)

    def not_character(self) -> set[str]:
        return {h for h, r in self.ratings.items() if r == 0}

    def meta(self) -> dict:
        """What the coverage map and the harvest record about the file they used."""
        try:
            from assistant_axis.gapgen.paths import REPO_ROOT
            p = str(Path(self.path).resolve().relative_to(REPO_ROOT))
        except ValueError:
            p = str(self.path)
        return {"path": p, "rubric_version": self.rubric.get("version"), "rubric_sha256": self.rubric.get("sha256"),
                "model": self.model, "n_rated": sum(r is not None for r in self.ratings.values()),
                "n_not_character": len(self.not_character())}


def load(path: Path) -> HeadScope:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d)
    rows = {r["id"]: r for r in d["heads"]}
    return HeadScope(path=Path(path), ratings={h: r.get("rating") for h, r in rows.items()}, rows=rows,
                     rubric=d.get("rubric") or {}, model=d.get("model"), summary=d.get("summary") or {})


def reusable(prev: Optional[HeadScope], *, rubric: Mapping, model: str) -> dict:
    """The rated rows of an earlier file made with the same rubric text and model (a resumed run sends
    only the rest)."""
    if prev is None or prev.rubric.get("version") != rubric.get("version") \
            or prev.rubric.get("sha256") != rubric.get("sha256"):
        return {}
    return {h: r for h, r in prev.rows.items() if r.get("rating") is not None and r.get("model") == model}


def append_responses(log: Sequence[dict], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in log:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
