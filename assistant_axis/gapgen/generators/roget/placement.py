"""The label placement check: a model step for the labels whose Roget head the two routes did not
agree on (Roger, 2026-10-08, "SG"; QUESTIONS 39).

Why: :mod:`.mapping` places each corpus and queue label on a head by rule (``label_heads.json``).  583
labels did not get route ``agree``: semantic 198, rule 40, lexical 22, none 323.  A wrong placement makes
a head look covered, so the harvest never takes its words and the gap is hidden, and M3 cannot catch that.
Several semantic-only placements match on spelling (``confabulatory`` on Confutation, ``maximizing`` on
Maxim, ``burned_out`` on Waste).

* **Which labels**: every label whose route was not ``agree`` (its ``llm.previous_route`` once checked).
* **Payload** (:func:`render_user`, one label per call): the label (its ``positive_label`` or queue label)
  and its description (the corpus file's, or the queue entry's description or draft), and its candidate
  heads (:func:`candidate_heads`: the semantic top five, then the lexical hits, deduplicated, at most
  :data:`MAX_CANDIDATES`, the current primary always among them), each with its id, title, class and
  section titles and about ten of its words (:func:`head_words`: adjectives, then nouns).  The heads are
  shown in a random order seeded by the label (:func:`shown_order`), and the model is never told which
  head is the current primary.
* **Answer**: a one-sentence reason, then ``head``: the id of the head where the trait's sense belongs, or
  ``"none"``.
* **Models**: Sonnet 5.5 on every label (system prompt marked for caching); Opus 5.5 as referee only where
  Sonnet's answer differs from the current primary (a move, a head where there was none, or none where
  there was a head), with the same prompt and without Sonnet's answer.  The final head is Opus's where it
  was asked, else Sonnet's (which then equals the current primary).
* **Record** (:func:`apply_results`): each checked label's ``llm`` field in ``label_heads.json`` gets the
  Sonnet answer and reason, the Opus answer and reason when asked, the final head, and the previous
  primary, secondaries and route.  Where the final head differs, ``primary`` is set to it and ``route`` to
  ``llm`` (``none`` when the final answer is none, so that "no primary" and route ``none`` still go
  together; the secondaries are then cleared, since every candidate was rejected as the label's home).

The rubric is the fenced block of ``reports/trait_gap_generation/rubrics/roget_placement.md``, pinned in
that directory's ``versions.json``.  The CLI is ``roget_generate.py place-check``.
"""
from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage

from .head_scope import display_title, section_title
from .parse import Head, RogetIndex

RUBRIC_NAME = "roget_placement"
SONNET = "claude-sonnet-5-5"
OPUS = "claude-opus-5-5"
MAX_CANDIDATES = 8
N_WORDS = 10
N_ADJ = 6
#: Both models think adaptively and cannot be told not to; their thinking counts against max_tokens.
MAX_TOKENS = 8000
CONCURRENCY = 6
NONE = "none"
STAGES = ("sonnet", "opus")
RESPONSES_NAME = "placement_responses.jsonl"
USAGE_NAME = "placement_usage.json"
#: Estimate, measured on a 30-label sample on 2026-10-08 (44 calls): about 2.7 characters of prompt per
#: input token (1,132 input tokens a call), and output, thinking included, about 139 tokens a call on
#: Sonnet 5.5 and 178 on Opus 5.5 (the first guesses, 400 and 700, were about three times too high).
CHARS_PER_TOKEN = 2.7
OUT_TOKENS = {"sonnet": 150, "opus": 190}
SEED = "roget_placement"


class RubricNotPinned(RuntimeError):
    """The rubric text on disk is not its latest pinned version."""


# --------------------------------------------------------------------------- items

def head_words(head: Head, n: int = N_WORDS, n_adj: int = N_ADJ) -> tuple[list[str], list[str]]:
    """``(adjectives, nouns)``: up to ``n_adj`` distinct adjectives in Roget's order, then nouns to make
    ``n`` words in all (more adjectives when the head has few nouns)."""
    adj = list(dict.fromkeys(a.strip() for a in head.items("Adj") if a.strip()))
    nouns = list(dict.fromkeys(a.strip() for a in head.items("N") if a.strip()))
    a = adj[:n_adj]
    b = nouns[: n - len(a)]
    if len(a) + len(b) < n:
        a = adj[: n - len(b)]
    return a, b


def head_payload(head: Head) -> dict:
    adj, nouns = head_words(head)
    return {"id": head.id, "title": display_title(head.title), "class": head.class_title,
            "section": section_title(head.section), "adjectives": adj, "nouns": nouns}


_ENTRY = object()


def candidate_heads(entry: Mapping, *, max_n: int = MAX_CANDIDATES, index: Optional[RogetIndex] = None,
                    current=_ENTRY) -> list[str]:
    """The semantic top five, then the lexical hits in their rank, deduplicated, at most ``max_n``; the
    current primary (``current``: a head id or None; by default the entry's ``primary``) is always among
    them (it replaces the last when it would be cut).  Heads not in ``index`` are dropped."""
    cur = entry.get("primary") if current is _ENTRY else current
    ids = [s["head_id"] for s in (entry.get("semantic") or [])[:5]] + [x["head_id"] for x in entry.get("lexical") or []]
    ids = [h for h in dict.fromkeys(ids) if index is None or h in index.heads]
    out = ids[:max_n]
    if cur and cur not in out and (index is None or cur in index.heads):
        out = out[: max_n - 1] + [cur]
    return out


def shown_order(head_ids: Sequence[str], stem: str, seed: str = SEED) -> list[str]:
    """The candidate heads in a random order seeded by the label (input order ignored)."""
    ids = sorted(head_ids)
    random.Random(f"{seed}:{stem}").shuffle(ids)
    return ids


@dataclass
class PlacementItem:
    stem: str
    label: str
    description: Optional[str]
    source: str
    current: Optional[str]          # the primary before the check
    route: str                      # the route before the check
    candidates: list                # head ids in the order shown

    def payload(self, index: RogetIndex) -> dict:
        trait = {"label": self.label}
        if self.description:
            trait["description"] = self.description
        return {"trait": trait, "heads": [head_payload(index.heads[h]) for h in self.candidates]}


def render_user(item: PlacementItem, index: RogetIndex) -> str:
    """The user turn: one JSON object, the trait on the first line and one head per line."""
    p = item.payload(index)
    rows = [" " + json.dumps(h, ensure_ascii=False) for h in p["heads"]]
    return ('{"trait": ' + json.dumps(p["trait"], ensure_ascii=False) + ',\n "heads": [\n' + ",\n".join(rows)
            + "\n ]}")


def previous(entry: Mapping) -> tuple[Optional[str], str, list]:
    """The placement before the check: ``(primary, route, secondary)`` (from ``llm`` once checked)."""
    llm = entry.get("llm") or {}
    if llm.get("check") == RUBRIC_NAME:
        return llm.get("previous_primary"), llm.get("previous_route"), list(llm.get("previous_secondary") or [])
    return entry.get("primary"), entry.get("route"), list(entry.get("secondary") or [])


def select_items(label_heads: Mapping[str, Mapping], records: Sequence, index: RogetIndex, *,
                 stems: Optional[Sequence[str]] = None) -> tuple[list[PlacementItem], dict]:
    """The labels to check (route before the check not ``agree``), with their descriptions from
    ``records`` (``mapping.LabelRecord``); ``(items, counts of the labels left out and why)``."""
    by = {r.stem: r for r in records}
    items, skipped = [], {"agree": 0, "no_record": [], "no_candidates": []}
    for stem in sorted(label_heads):
        if stems is not None and stem not in stems:
            continue
        v = label_heads[stem]
        cur, route, _ = previous(v)
        if route == "agree":
            skipped["agree"] += 1
            continue
        rec = by.get(stem)
        if rec is None:
            skipped["no_record"].append(stem)
            continue
        cands = candidate_heads(v, index=index, current=cur)
        if not cands:
            skipped["no_candidates"].append(stem)
            continue
        items.append(PlacementItem(stem=stem, label=v.get("label") or rec.label, description=rec.description,
                                   source=rec.source, current=cur, route=route,
                                   candidates=shown_order(cands, stem)))
    return items, skipped


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


# --------------------------------------------------------------------------- parsing

def parse_answer(text: Optional[str], ids: Sequence[str]) -> tuple[Optional[dict], Optional[str]]:
    """``({"head": id or None, "reason"}, None)`` or ``(None, why)``; ``head`` must be one of ``ids`` or
    ``"none"``."""
    if text is None:
        return None, "no response"
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict) or "head" not in d:
        return None, "unparseable"
    h = d.get("head")
    h = NONE if h is None else str(h).strip()
    if h.lower() == NONE:
        return {"head": None, "reason": str(d.get("reason") or "").strip()}, None
    if h not in set(ids):
        return None, f"head {h} not offered"
    return {"head": h, "reason": str(d.get("reason") or "").strip()}, None


# --------------------------------------------------------------------------- the calls

@dataclass
class StageResult:
    answers: dict = field(default_factory=dict)     # stem -> {"head", "reason", "model", "attempts"}
    errors: dict = field(default_factory=dict)      # stem -> why it has no answer
    log: list = field(default_factory=list)
    stopped_by_budget: bool = False


async def run_stage(items: Sequence[PlacementItem], index: RogetIndex, *, stage: str, client, model: str,
                    system: str, usage, concurrency: int = CONCURRENCY, max_tokens: int = MAX_TOKENS,
                    cache_system: bool = True, rubric_version: Optional[int] = None,
                    now: Optional[Callable[[], str]] = None,
                    on_record: Optional[Callable[[dict], None]] = None) -> StageResult:
    """One call per label; a label whose answer does not parse is asked once more.  ``on_record`` gets
    each call's record as it completes (the CLI appends it to the responses log, for ``--resume``).  A
    ``BudgetExceededError`` keeps the answer that crossed the cap and stops the stage."""
    res = StageResult()
    sem = asyncio.Semaphore(max(1, concurrency))
    prompt_sha = sr.sha256(system)

    async def one(item: PlacementItem, attempt: int) -> Optional[dict]:
        user = render_user(item, index)
        meta: dict = {}
        over = False
        try:
            text = await call_anthropic_json(client, system=system, user=user, model=model, max_tokens=max_tokens,
                                             temperature=None, usage=usage, cache_system=cache_system, meta=meta)
        except BudgetExceededError:
            text, over = meta.get("text"), True
        ans, err = parse_answer(text, item.candidates)
        rec = {"stage": stage, "stem": item.stem, "attempt": attempt, "model": model, "rubric_version": rubric_version,
               "prompt_sha256": prompt_sha, "at": now() if now else None, "candidates": list(item.candidates),
               "current": item.current, "user": user, "text": text, "stop_reason": meta.get("stop_reason"),
               "usage_raw": meta.get("usage_raw"), "error": meta.get("error"), "parse_error": err,
               "answer": ans}
        res.log.append(rec)
        if on_record is not None:
            on_record(rec)
        if over:
            res.stopped_by_budget = True
        return {"ans": ans, "err": err}

    async def run_item(item: PlacementItem) -> None:
        async with sem:
            if res.stopped_by_budget:
                return
            out = await one(item, 1)
            if out["ans"] is None and not res.stopped_by_budget:
                out = await one(item, 2)
                attempts = 2
            else:
                attempts = 1
            if out["ans"] is not None:
                res.answers[item.stem] = {**out["ans"], "model": model, "attempts": attempts}
            else:
                res.errors[item.stem] = out["err"]

    await asyncio.gather(*(run_item(it) for it in items))
    res.log.sort(key=lambda r: (r["stem"], r["attempt"]))
    return res


def needs_referee(item: PlacementItem, sonnet_answer: Optional[Mapping]) -> bool:
    """Opus is asked where Sonnet's head differs from the current primary (None counts as a value)."""
    return sonnet_answer is not None and sonnet_answer.get("head") != item.current


def estimate(items: Sequence[PlacementItem], index: RogetIndex, system: str, model: str, stage: str,
             n_calls: Optional[int] = None) -> dict:
    """``{"n_calls", "in_tok", "out_tok", "usd"}``; ``n_calls`` scales the per-item mean (the referee
    stage's size is not known before the first stage)."""
    if not items:
        return {"n_calls": 0, "in_tok": 0, "out_tok": 0, "usd": 0.0}
    per_in = sum((len(system) + len(render_user(it, index))) / CHARS_PER_TOKEN for it in items) / len(items)
    n = len(items) if n_calls is None else n_calls
    in_tok, out_tok = int(round(per_in * n)), OUT_TOKENS[stage] * n
    return {"n_calls": n, "in_tok": in_tok, "out_tok": out_tok, "usd": round(cost_for_usage(model, in_tok, out_tok), 4)}


# --------------------------------------------------------------------------- resume

def reusable_answers(records: Sequence[Mapping], *, stage: str, model: str, prompt_sha: str) -> dict:
    """Parsed answers in a responses log made with the same stage, model and rubric text (the last per
    label wins): ``{stem: answer}``."""
    out = {}
    for r in records:
        if r.get("stage") == stage and r.get("model") == model and r.get("prompt_sha256") == prompt_sha \
                and r.get("answer") is not None:
            out[r["stem"]] = {**r["answer"], "model": model, "attempts": r.get("attempt", 1)}
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


# --------------------------------------------------------------------------- the record

def final_answer(item: PlacementItem, sonnet: Optional[Mapping], opus: Optional[Mapping]) -> tuple[Optional[str], str]:
    """``(final head, who decided)``: Opus where it was asked and answered, else Sonnet where it agrees
    with the current primary; with no usable answer the current primary stands (``unchecked``)."""
    if sonnet is None:
        return item.current, "unchecked"
    if not needs_referee(item, sonnet):
        return sonnet["head"], "sonnet"
    if opus is None:
        return item.current, "unchecked"
    return opus["head"], "opus"


def apply_results(label_heads: Mapping[str, Mapping], items: Sequence[PlacementItem], sonnet: Mapping[str, Mapping],
                  opus: Mapping[str, Mapping], *, rubric: Mapping, checked_at: str) -> tuple[dict, dict]:
    """A copy of ``label_heads`` with the check recorded (module docstring), and the counts:
    unchanged / moved / newly placed / unplaced / unchecked."""
    from collections import Counter
    out = {k: dict(v) for k, v in label_heads.items()}
    counts: Counter = Counter()
    for it in items:
        v = out[it.stem]
        prev_primary, prev_route, prev_secondary = previous(label_heads[it.stem])
        s, o = sonnet.get(it.stem), opus.get(it.stem)
        fin, who = final_answer(it, s, o)
        if who == "unchecked":
            counts["unchecked"] += 1
            continue
        if fin == prev_primary:
            kind = "unchanged"
        elif prev_primary is None:
            kind = "newly_placed"
        elif fin is None:
            kind = "unplaced"
        else:
            kind = "moved"
        counts[kind] += 1
        v["llm"] = {"check": RUBRIC_NAME, "rubric_version": rubric.get("version"),
                    "rubric_sha256": rubric.get("sha256"), "checked_at": checked_at,
                    "candidates": list(it.candidates),
                    "sonnet": {k: s.get(k) for k in ("head", "reason", "model")},
                    "opus": {k: o.get(k) for k in ("head", "reason", "model")} if o is not None and who == "opus" else None,
                    "final": fin, "decided_by": who, "outcome": kind,
                    "previous_primary": prev_primary, "previous_route": prev_route,
                    "previous_secondary": prev_secondary}
        if kind == "unchanged":
            v["primary"], v["route"], v["secondary"] = prev_primary, prev_route, prev_secondary
        elif fin is None:
            v["primary"], v["route"], v["secondary"], v["confidence"] = None, "none", [], 0.0
        else:
            v["primary"], v["route"] = fin, "llm"
            v["secondary"] = [h for h in prev_secondary if h != fin]
            v["confidence"] = 0.8
    return out, dict(counts)


def save_label_heads_checked(path: Path, label_heads: Mapping[str, Mapping], *, extra_inputs: Sequence = (),
                             meta: Optional[dict] = None) -> Path:
    """Rewrite ``label_heads.json`` with the checked labels, keeping its payload's other keys and its
    recorded inputs (the map run's), adding ``extra_inputs`` and ``placement_check`` (``meta``)."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import InputSpec, inputs_to_jsonable

    from .parse import dumps_one_per_line
    path = Path(path)
    env = json.loads(path.read_text(encoding="utf-8"))
    payload = {k: v for k, v in env.get("result", env).items() if k != "labels"}
    if meta is not None:
        payload["placement_check"] = meta
    payload["labels"] = dict(label_heads)
    old = list((env.get("_provenance") or {}).get("inputs") or [])
    new = inputs_to_jsonable([i for i in extra_inputs if isinstance(i, InputSpec)])
    keys = {i["dep_key"] for i in new}
    inputs = [i for i in old if i.get("dep_key") not in keys] + new
    out = json_metadata(payload, inputs=inputs, title="Roget coordinates of the corpus labels (workstream 2)")
    atomic_write_text(dumps_one_per_line(out, "labels"), path)
    return path
