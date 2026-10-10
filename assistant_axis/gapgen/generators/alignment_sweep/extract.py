"""The extraction call and the mechanism rewrite (plan 08 steps 2 and 3).

* **Extraction** (rubric ``alignment_extract``, pinned): one Sonnet 5.5 call per chunk; the user turn is the
  source's name and version, the section's heading path and the passage (:func:`render_user`).  The answer, reason
  first, is a list of items, each a disposition with two opposite poles (``virtue``, ``vice``), the pole the passage
  names (``source_pole``: an imperative names the virtue, a failure mode the vice), ``type``, ``enactability`` and
  the source sentence.  An answer that does not parse is asked once more; every response is charged.
* **Items** (:func:`build_items`): each extracted pair becomes two :class:`Item` rows, one per pole, ``a`` for the
  pole the passage names and ``b`` for its partner: ``ms041-1a`` / ``ms041-1b`` is the first item of the Model
  Spec's 41st chunk (ids stay the same whichever chunks a run extracts).  ``rank`` numbers the pairs in chunk order.
  A quote from a ``read_only`` source is cut at 25 words, at a word boundary (:func:`truncate_quote`).
* **Drops** (:func:`apply_drops`), recorded in ``dropped_reason`` and counted, never deleted: ``mechanism`` items
  go to the rewrite call and are never submitted as they are; ``enactability none`` items are dropped; a pole whose
  label breaks the label rule (:func:`label_problem`: more than four words, an underscore, a non-ASCII character)
  is dropped (its partner stays).  The model's own ``label_kind`` ("term of art", "coinage") is kept and counted
  (the label rule's bite), not dropped: the probe and Roger's marks judge those.
* **Rewrite** (rubric ``alignment_rewrite``, pinned): one call per mechanism item, showing its labels in the judge
  display form (:func:`assistant_axis.gapgen.prompt_labels.prompt_label`); zero to two dispositions come back,
  each a new pair ``<base>r<j>a`` / ``<base>r<j>b`` with ``rewritten_from`` the original's id.

The responses log (``extract_responses.jsonl``) keeps every call as sent and answered, the user turn and the reply
text included except for a ``read_only`` source (whose text is not kept beyond 25-word quotes; its record holds the
user turn's sha256 and the parsed items).  :func:`reusable_answers` reads it back for a resumed run or a run that
reuses another's answers: only an answer to the same stage, model, rubric text and user turn is reused.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage

from .chunk import CHARS_PER_TOKEN, Chunk
from .sources import SOURCES, Source, quote_limit

RUBRIC_EXTRACT = "alignment_extract"
RUBRIC_REWRITE = "alignment_rewrite"
MODEL = "claude-sonnet-5-5"
#: Sonnet 5.5 thinks adaptively and cannot be told not to; its thinking counts against max_tokens.
MAX_TOKENS = 16000
CONCURRENCY = 6
SCHEMA_VERSION = 1
MAX_LABEL_WORDS = 4
POLES = ("virtue", "vice")
TYPES = ("behaviour", "belief-state", "mechanism")
ENACTABILITY = ("chat", "agentic-only", "none")
LABEL_KINDS = ("ordinary", "term of art", "coinage")
RESPONSES_NAME = "extract_responses.jsonl"
EXTRACTION_NAME = "extraction.jsonl"
SUMMARY_NAME = "extract_summary.json"
#: Output tokens a call, thinking included, for the estimate (first guesses; the pilot measures them).
OUT_TOKENS = {"extract": 1500, "rewrite": 900}


class RubricNotPinned(RuntimeError):
    """The rubric text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- rubrics

def load_rubric(name: str, rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin (with
    ``allow_unpinned``, for rendering only, version and sha256 are None)."""
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == name]
    path = sr.rubric_path(name, rubrics_dir)
    try:
        from assistant_axis.gapgen.paths import REPO_ROOT
        rel = str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    if probs:
        if not allow_unpinned:
            raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
        return {"name": name, "text": sr.load_prompt(name, rubrics_dir), "version": None, "sha256": None, "file": rel}
    version, sha = sr.current_versions(rubrics_dir, (name,))[name]
    return {"name": name, "text": sr.load_prompt(name, rubrics_dir), "version": version, "sha256": sha, "file": rel}


# --------------------------------------------------------------------------- labels and quotes

def label_problem(label) -> Optional[str]:
    """Why ``label`` breaks the label rule (plan 08 step 2: one to four words, ASCII, no underscore), or None."""
    if not isinstance(label, str) or not label.strip():
        return "empty"
    if "_" in label:
        return "underscore"
    if not label.isascii():
        return "non-ASCII"
    n = len(label.split())
    if n > MAX_LABEL_WORDS:
        return f"{n} words (at most {MAX_LABEL_WORDS})"
    try:
        if not normalize_to_file_name(label):
            return "no stem"
    except ValueError:
        return "does not normalise"
    return None


def label_ok(label) -> bool:
    return label_problem(label) is None


def quote_policy(source_key: str) -> Optional[int]:
    """The longest quote, in words, kept from ``source_key`` (25 for a ``read_only`` source, else no limit)."""
    return quote_limit(source_key)


def truncate_quote(quote: Optional[str], max_words: Optional[int]) -> Optional[str]:
    """``quote`` cut to ``max_words`` words at a word boundary, marked `` [...]`` when cut."""
    if quote is None or max_words is None:
        return quote
    words = quote.split()
    if len(words) <= max_words:
        return quote
    return " ".join(words[:max_words]) + " [...]"


# --------------------------------------------------------------------------- items

@dataclass
class Item:
    """One pole of an extracted (or rewritten) disposition: a row of ``extraction.jsonl``."""
    item_id: str
    chunk_id: str
    source: str
    label: str
    stem: Optional[str]
    gloss: str
    partner_label: Optional[str]
    partner_item_id: Optional[str]
    pole: str                          # "virtue" | "vice"
    names_source: bool                 # the pole the passage names (source_pole)
    type: str
    enactability: str
    label_kind: Optional[str]
    polysemy_flag: bool
    polysemy_note: Optional[str]
    source_quote: Optional[str]
    rank: int
    source_weight: float
    rewritten_from: Optional[str] = None
    dropped_reason: Optional[str] = None
    label_problem: Optional[str] = None
    reason: Optional[str] = None
    schema_version: int = SCHEMA_VERSION

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def pair_id(self) -> str:
        return self.item_id[:-1]

    @property
    def kept(self) -> bool:
        return self.dropped_reason is None


ITEM_FIELDS = tuple(f.name for f in fields(Item))


def _stem(label: str) -> Optional[str]:
    try:
        return normalize_to_file_name(label) or None
    except (ValueError, TypeError):
        return None


def build_items(chunk_id: str, raw_items: Sequence[Mapping], *, ordinal: int, source: Source, rank_start: int,
                rewrite_of: Optional[str] = None) -> list[Item]:
    """Two :class:`Item` rows per extracted pair (``a``: the pole the passage names, ``b``: its partner).  For a
    rewrite, ``rewrite_of`` is the original pair's id (``ms041-1``) and the new ids are ``<it>r<j>a`` / ``b``."""
    out: list[Item] = []
    limit = quote_policy(source.key)
    for i, d in enumerate(raw_items, 1):
        base = f"{rewrite_of}r{i}" if rewrite_of else f"{source.short}{ordinal:03d}-{i}"
        named = d["source_pole"]
        other = "vice" if named == "virtue" else "virtue"
        quote = truncate_quote(d.get("source_quote"), limit)
        for letter, pole, mine, theirs in (("a", named, d[named], d[other]), ("b", other, d[other], d[named])):
            label = str(mine.get("label") or "").strip()
            note = mine.get("polysemy")
            note = str(note).strip() if isinstance(note, str) and note.strip() else None
            out.append(Item(
                item_id=base + letter, chunk_id=chunk_id, source=source.key, label=label, stem=_stem(label),
                gloss=str(mine.get("gloss") or "").strip(), partner_label=str(theirs.get("label") or "").strip(),
                partner_item_id=base + ("b" if letter == "a" else "a"), pole=pole, names_source=letter == "a",
                type=d["type"], enactability=d["enactability"], label_kind=mine.get("label_kind"),
                polysemy_flag=note is not None, polysemy_note=note, source_quote=quote, rank=rank_start + i - 1,
                source_weight=source.weight,
                rewritten_from=(f"{rewrite_of}a" if rewrite_of else None), label_problem=label_problem(label),
                reason=d.get("reason")))
    return out


def apply_drops(items: Sequence[Item]) -> list[Item]:
    """Set ``dropped_reason`` (module docstring): mechanism (pending its rewrite), ``enactability none``, the label
    rule (that pole only).  Returns the items, changed in place."""
    for it in items:
        if it.type == "mechanism":
            it.dropped_reason = it.dropped_reason or "mechanism"
        elif it.enactability == "none":
            it.dropped_reason = "enactability none"
        elif it.label_problem:
            it.dropped_reason = f"label rule: {it.label_problem}"
    return list(items)


def mechanism_pairs(items: Sequence[Item]) -> list[tuple[Item, Item]]:
    """``(named pole, partner)`` of every un-rewritten mechanism pair, in rank order."""
    by = {it.item_id: it for it in items}
    out = []
    for it in sorted(items, key=lambda x: (x.rank, x.item_id)):
        if it.type == "mechanism" and it.names_source and it.rewritten_from is None and it.partner_item_id in by:
            out.append((it, by[it.partner_item_id]))
    return out


def record_rewrites(items: Sequence[Item], rewrites: Mapping[str, Optional[list]]) -> None:
    """Note on each mechanism pole what became of it: ``rewritten as <ids>``, ``no disposition``, ``rewrite
    failed`` (``rewrites`` maps a pair id to its new pair ids, ``[]`` for none, None for a failed call)."""
    for it in items:
        if it.type != "mechanism" or it.rewritten_from is not None:
            continue
        got = rewrites.get(it.pair_id, "missing")
        if got == "missing":
            continue
        if got is None:
            it.dropped_reason = "mechanism: rewrite failed"
        elif not got:
            it.dropped_reason = "mechanism: no disposition"
        else:
            it.dropped_reason = "mechanism: rewritten as " + ", ".join(got)


# --------------------------------------------------------------------------- rendering

def version_of(chunk_id: str) -> str:
    return chunk_id.split(":")[1]


def render_user(chunk: Chunk) -> str:
    """The extraction call's user turn: the source (with its version, or the date it was captured when it prints
    none), the section's heading path and the passage."""
    s = SOURCES[chunk.source]
    when = f"version {s.version_label}" if s.version_label else f"captured {version_of(chunk.chunk_id)}"
    return (f"Source: {s.name} ({when})\nSection: {chunk.heading}\n\n"
            f"<passage>\n{chunk.text.strip()}\n</passage>")


def render_rewrite_user(named: Item, partner: Item, *, heading: Optional[str] = None,
                        label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The rewrite call's user turn: one JSON object (labels in the judge display form)."""
    s = SOURCES[named.source]
    poles = {named.pole: named, partner.pole: partner}
    obj = {"source": s.name, "section": heading, "source_quote": named.source_quote, "reason": named.reason,
           "type": "mechanism",
           "virtue": {"label": prompt_label(poles["virtue"].label, label_form), "gloss": poles["virtue"].gloss},
           "vice": {"label": prompt_label(poles["vice"].label, label_form), "gloss": poles["vice"].gloss}}
    if heading is None:
        obj.pop("section")
    return json.dumps(obj, ensure_ascii=False, indent=1)


# --------------------------------------------------------------------------- parsing

def _pole_ok(p) -> Optional[str]:
    if not isinstance(p, dict):
        return "pole is not an object"
    if not isinstance(p.get("label"), str) or not p["label"].strip():
        return "pole without a label"
    if not isinstance(p.get("gloss"), str) or not p["gloss"].strip():
        return "pole without a gloss"
    if p.get("label_kind") is not None and p["label_kind"] not in LABEL_KINDS:
        return f"label_kind {p['label_kind']!r}"
    if p.get("polysemy") is not None and not isinstance(p["polysemy"], str):
        return "polysemy is not text or null"
    return None


def validate_item(d, *, rewrite: bool = False) -> tuple[Optional[dict], Optional[str]]:
    """``(item, None)`` for a well-formed item (a rewrite's has no source quote and is never a mechanism), else
    ``(None, problem)``."""
    if not isinstance(d, dict):
        return None, "item is not an object"
    if d.get("source_pole") not in POLES:
        return None, f"source_pole {d.get('source_pole')!r}"
    types = TYPES[:2] if rewrite else TYPES
    if d.get("type") not in types:
        return None, f"type {d.get('type')!r}"
    if d.get("enactability") not in ENACTABILITY:
        return None, f"enactability {d.get('enactability')!r}"
    for pole in POLES:
        prob = _pole_ok(d.get(pole))
        if prob:
            return None, f"{pole}: {prob}"
    if not rewrite and not isinstance(d.get("source_quote"), str):
        return None, "no source_quote"
    return d, None


def parse_reply(text: Optional[str], *, key: str) -> tuple[Optional[list], Optional[str], list]:
    """``(valid items, None, invalid)`` for a reply holding ``{"reasoning": ..., key: [...]}``; ``(None, why,
    [])`` when it does not parse.  ``invalid`` lists ``(item, problem)`` for malformed items of a parsed reply."""
    if text is None:
        return None, "no response", []
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict) or not isinstance(d.get(key), list):
        return None, "unparseable", []
    ok, bad = [], []
    for raw in d[key]:
        item, prob = validate_item(raw, rewrite=key == "dispositions")
        if item is None:
            bad.append((raw, prob))
        else:
            ok.append(item)
    return ok, None, bad


# --------------------------------------------------------------------------- the calls

@dataclass
class Unit:
    """One call: its id (a chunk id, or a pair id for a rewrite), the user turn, and whether its texts may be kept."""
    unit_id: str
    user: str
    store_text: bool = True


@dataclass
class StageResult:
    answers: dict = field(default_factory=dict)     # unit id -> valid items
    invalid: dict = field(default_factory=dict)     # unit id -> [(item, problem)]
    errors: dict = field(default_factory=dict)      # unit id -> why there is no answer
    log: list = field(default_factory=list)
    n_calls: int = 0
    stopped_by_budget: bool = False


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scrub(items: list, limit: Optional[int]) -> list:
    out = []
    for d in items:
        d = dict(d)
        if "source_quote" in d:
            d["source_quote"] = truncate_quote(d["source_quote"], limit)
        out.append(d)
    return out


async def run_stage(units: Sequence[Unit], *, stage: str, client, model: str, system: str, usage,
                    concurrency: int = CONCURRENCY, max_tokens: int = MAX_TOKENS, rubric_version: Optional[int] = None,
                    now: Optional[Callable[[], str]] = None,
                    on_record: Optional[Callable[[dict], None]] = None) -> StageResult:
    """One call per unit; a reply that does not parse is asked once more.  ``on_record`` gets each call's record
    as it completes (the CLI appends it to the responses log).  A ``BudgetExceededError`` keeps the answer that
    crossed the cap and stops the stage."""
    key = "items" if stage == "extract" else "dispositions"
    res = StageResult()
    sem = asyncio.Semaphore(max(1, concurrency))
    prompt_sha = sr.sha256(system)

    async def one(u: Unit, attempt: int) -> dict:
        meta: dict = {}
        over = False
        try:
            text = await call_anthropic_json(client, system=system, user=u.user, model=model, max_tokens=max_tokens,
                                             temperature=None, usage=usage, cache_system=True, meta=meta)
        except BudgetExceededError:
            text, over = meta.get("text"), True
        res.n_calls += 1
        ok, err, bad = parse_reply(text, key=key)
        limit = None if u.store_text else 25
        rec = {"stage": stage, "unit_id": u.unit_id, "attempt": attempt, "model": model,
               "rubric_version": rubric_version, "prompt_sha256": prompt_sha, "at": now() if now else None,
               "user": u.user if u.store_text else None, "user_sha256": sha256(u.user),
               "text": text if u.store_text else None, "stop_reason": meta.get("stop_reason"),
               "usage_raw": meta.get("usage_raw"), "error": meta.get("error"), "parse_error": err,
               "items": _scrub(ok, limit) if ok is not None else None,
               "invalid": [{"item": _scrub([i], limit)[0] if isinstance(i, dict) else i, "problem": p} for i, p in bad]}
        res.log.append(rec)
        if on_record is not None:
            on_record(rec)
        if over:
            res.stopped_by_budget = True
        return {"ok": ok, "err": err, "bad": bad}

    async def run_unit(u: Unit) -> None:
        async with sem:
            if res.stopped_by_budget:
                return
            out = await one(u, 1)
            if out["ok"] is None and not res.stopped_by_budget:
                out = await one(u, 2)
            if out["ok"] is not None:
                res.answers[u.unit_id] = out["ok"]
                if out["bad"]:
                    res.invalid[u.unit_id] = out["bad"]
            else:
                res.errors[u.unit_id] = out["err"]

    await asyncio.gather(*(run_unit(u) for u in units))
    res.log.sort(key=lambda r: (r["unit_id"], r["attempt"]))
    return res


def reusable_answers(records: Iterable[Mapping], *, stage: str, model: str, prompt_sha: str,
                     users: Mapping[str, str]) -> dict:
    """Parsed answers in a responses log made with the same stage, model and rubric text, to a byte-identical
    user turn (by sha256), last one per unit winning: ``{unit id: items}``."""
    want = {u: sha256(t) for u, t in users.items()}
    out = {}
    for r in records:
        if (r.get("stage") == stage and r.get("model") == model and r.get("prompt_sha256") == prompt_sha
                and r.get("items") is not None and want.get(r.get("unit_id")) == r.get("user_sha256")):
            out[r["unit_id"]] = r["items"]
    return out


def read_responses(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_response(rec: Mapping, path: Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- selection and estimate

def stratified_sample(chunks: Sequence[Chunk], n: int, seed: int) -> list[Chunk]:
    """``n`` chunks drawn per source in proportion to its chunk count (largest remainders), seeded by ``seed`` and
    the source; returned in the input order.  The pilot's ``--chunks 30 --seed 0`` on 80 Model Spec and 40
    constitution chunks draws 20 and 10."""
    by: dict[str, list[Chunk]] = {}
    for c in chunks:
        by.setdefault(c.source, []).append(c)
    total = len(chunks)
    if n >= total:
        return list(chunks)
    raw = {k: n * len(v) / total for k, v in by.items()}
    quota = {k: int(x) for k, x in raw.items()}
    for k in sorted(raw, key=lambda k: (-(raw[k] - quota[k]), k))[: n - sum(quota.values())]:
        quota[k] += 1
    pick = set()
    for k, v in by.items():
        pick.update(c.chunk_id for c in random.Random(f"{seed}:{k}").sample(v, quota[k]))
    return [c for c in chunks if c.chunk_id in pick]


def chunk_ordinals(chunks: Sequence[Chunk]) -> dict[str, int]:
    """Each chunk's 1-based position within its source (the item id's number)."""
    out, n = {}, Counter()
    for c in chunks:
        n[c.source] += 1
        out[c.chunk_id] = n[c.source]
    return out


def estimate(units: Sequence[Unit], system: str, model: str, stage: str, n_calls: Optional[int] = None) -> dict:
    """``{"n_calls", "in_tok", "out_tok", "usd"}`` at :data:`OUT_TOKENS` a call; ``n_calls`` scales the
    per-unit mean (the rewrite stage's size is not known before the extraction)."""
    if not units and not n_calls:
        return {"n_calls": 0, "in_tok": 0, "out_tok": 0, "usd": 0.0}
    per_in = (sum((len(system) + len(u.user)) / CHARS_PER_TOKEN for u in units) / len(units)) if units else \
        (len(system) + 1200) / CHARS_PER_TOKEN
    n = len(units) if n_calls is None else n_calls
    in_tok, out_tok = int(round(per_in * n)), OUT_TOKENS[stage] * n
    return {"n_calls": n, "in_tok": in_tok, "out_tok": out_tok, "usd": round(cost_for_usage(model, in_tok, out_tok), 4)}


# --------------------------------------------------------------------------- assembly and records

def assemble(chunks: Sequence[Chunk], answers: Mapping[str, list], *, ordinals: Mapping[str, int]) -> list[Item]:
    """The items of every answered chunk, in chunk order, ranks numbering the pairs from 1."""
    items: list[Item] = []
    rank = 1
    for c in chunks:
        raw = answers.get(c.chunk_id)
        if not raw:
            continue
        new = build_items(c.chunk_id, raw, ordinal=ordinals[c.chunk_id], source=SOURCES[c.source], rank_start=rank)
        rank += len(raw)
        items.extend(new)
    return apply_drops(items)


def add_rewrites(items: list[Item], rewrites: Mapping[str, list], pairs: Sequence[tuple[Item, Item]]) -> list[Item]:
    """Append each rewrite's new pairs after the items (they keep their original's chunk, rank and quote) and note
    on the mechanism poles what became of them; ``rewrites`` maps a pair id to its dispositions (None: failed)."""
    made: dict[str, Optional[list]] = {}
    for named, _partner in pairs:
        raw = rewrites.get(named.pair_id, "missing")
        if raw == "missing":
            continue
        if raw is None:
            made[named.pair_id] = None
            continue
        src = SOURCES[named.source]
        fixed = [{**d, "source_quote": named.source_quote} for d in raw]
        new = build_items(named.chunk_id, fixed, ordinal=0, source=src, rank_start=named.rank,
                          rewrite_of=named.pair_id)
        for it in new:
            it.rank = named.rank
            it.source_quote = named.source_quote
        apply_drops(new)
        items.extend(new)
        made[named.pair_id] = sorted({it.pair_id for it in new})
    record_rewrites(items, made)
    return items


def write_extraction(items: Sequence[Item], path: Path) -> Path:
    from assistant_axis.atomic_io import atomic_write_text
    rows = sorted(items, key=lambda it: (it.rank, it.item_id))
    atomic_write_text("".join(json.dumps(it.as_dict(), ensure_ascii=False) + "\n" for it in rows), Path(path))
    return Path(path)


def load_extraction(path: Path) -> list[Item]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out.append(Item(**{k: d.get(k) for k in ITEM_FIELDS if k in d}))
    return out


def drop_kind(reason: str) -> str:
    """A ``dropped_reason`` without its particulars: ``mechanism: rewritten`` (not the ids), ``label rule`` (not
    the problem); the rest as they are."""
    if reason.startswith("mechanism: rewritten"):
        return "mechanism: rewritten"
    if reason.startswith("label rule"):
        return "label rule"
    return reason


def summarize(items: Sequence[Item], *, n_chunks: int, extract: StageResult, rewrite: Optional[StageResult] = None,
              n_reused: int = 0) -> dict:
    """The counts the pilot readout reports (coding plan § 10)."""
    pairs = [it for it in items if it.names_source and it.rewritten_from is None]
    rewritten_pairs = [it for it in items if it.names_source and it.rewritten_from is not None]
    poles = [it for it in items if it.rewritten_from is None]
    kept = [it for it in items if it.kept]
    flagged = [it for it in poles if it.label_kind not in (None, "ordinary")]
    rule = [it for it in poles if it.label_problem]
    bite = {it.item_id for it in flagged} | {it.item_id for it in rule}
    return {
        "n_chunks": n_chunks, "n_chunks_answered": len(extract.answers) + n_reused,
        "n_calls": {"extract": extract.n_calls, "rewrite": rewrite.n_calls if rewrite else 0},
        "n_reused": n_reused, "unparsed": dict(extract.errors),
        "n_invalid_items": sum(len(v) for v in extract.invalid.values()),
        "n_pairs": len(pairs), "n_poles": len(poles),
        "pairs_per_chunk": round(len(pairs) / n_chunks, 3) if n_chunks else None,
        "type": dict(Counter(it.type for it in pairs)), "enactability": dict(Counter(it.enactability for it in pairs)),
        "source_pole": dict(Counter(it.pole for it in pairs)),
        "label_kind": dict(Counter(str(it.label_kind) for it in poles)),
        "label_rule_rejected": len(rule), "label_flagged_by_model": len(flagged),
        "label_rule_bite": {"n": len(bite), "share": round(len(bite) / len(poles), 4) if poles else None},
        "polysemy_flags": {"n": sum(1 for it in poles if it.polysemy_flag),
                           "share": round(sum(1 for it in poles if it.polysemy_flag) / len(poles), 4) if poles else None},
        "mechanism_pairs": sum(1 for it in pairs if it.type == "mechanism"),
        "rewritten_pairs": len(rewritten_pairs),
        "dropped": dict(Counter(drop_kind(it.dropped_reason) for it in items if it.dropped_reason)),
        "n_kept_poles": len(kept), "n_kept_pairs_both_poles": sum(
            1 for it in kept if it.names_source and any(o.item_id == it.partner_item_id and o.kept for o in kept)),
    }


__all__ = ["Item", "Unit", "StageResult", "RubricNotPinned", "RUBRIC_EXTRACT", "RUBRIC_REWRITE", "MODEL", "TYPES",
           "ENACTABILITY", "LABEL_KINDS", "POLES", "load_rubric", "label_problem", "label_ok", "quote_policy",
           "truncate_quote", "build_items", "apply_drops", "mechanism_pairs", "record_rewrites", "render_user",
           "render_rewrite_user", "parse_reply", "validate_item", "run_stage", "reusable_answers", "read_responses",
           "append_response", "stratified_sample", "chunk_ordinals", "estimate", "assemble", "add_rewrites",
           "write_extraction", "load_extraction", "summarize"]
