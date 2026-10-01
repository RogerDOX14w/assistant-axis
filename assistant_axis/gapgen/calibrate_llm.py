"""The two paid criteria of the contrast ablation (M2; plan 15 §3.5 (e) and (g)).

Built and tested with a fake client; run only when ``calibrate_metric.py``
is called without ``--skip-llm`` (Roger's decision after the pilot).

* **(g) paraphrases** (Haiku): each description rewritten in different words
  at the same length and in the corpus form, without the label word, batched
  20 per call; cached in ``calibration/paraphrases.json`` and reused by M3's
  paraphrase recall.  ``PARAPHRASE_PROMPT_VERSION`` pins the text.  Round 4
  adds two styles (``plain``: everyday words; ``terse``: a dictionary-like
  core sense), each its own prompt and version
  (:data:`PARAPHRASE_STYLE_PROMPTS`, :data:`PARAPHRASE_STYLE_VERSIONS`).
* **(e) blinded neighbour judgement** (Sonnet): a trait and two top-5
  neighbour lists (with and without contrast clauses, in random order,
  unlabelled); the judge reasons first, then prefers A, B or same; every
  comparison is asked twice with the lists swapped, and only an
  order-consistent preference counts.  ``BLINDED_PROMPT_VERSION`` pins the
  text.

Both use ``gapgen.llm.call_anthropic_json`` (cached system prompt, retries,
every response charged to the usage record) and report their parse rate
through ``judge.warn_if_low_parse_rate``.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Mapping, Optional, Sequence

from assistant_axis.judge import extract_json_blob, warn_if_low_parse_rate
from assistant_axis.judge_pricing import MultiModelUsage

from .cost import Estimate
from .llm import call_anthropic_json

logger = logging.getLogger(__name__)

PARAPHRASE_MODEL = "claude-haiku-4-5-20251001"
JUDGE_MODEL = "claude-sonnet-4-6"
PARAPHRASE_PROMPT_VERSION = 2   # v1 (no reason field) was never run
BLINDED_PROMPT_VERSION = 1
PARAPHRASE_BATCH = 20

PARAPHRASE_PROMPT = """You rewrite short definitions of personality traits for a calibration experiment.

Context: we measure how far a text embedding moves when a definition is reworded without changing its meaning. So each rewrite must keep the meaning exactly (the same disposition, the same scope, the same emphasis) while sharing as few words with the original as English allows.

Rules for each rewrite:
- Start with "This means" and describe the same disposition, in the same grammatical person and tense as the original.
- Keep the length within a few words of the original.
- Do not use the trait's label word, or any word formed from it.
- Do not add examples, qualifications or contrasts that the original does not have, and do not drop any that it has: if the original says what the trait is not ("rather than X"), say that too, in other words.
- Write plain prose, no lists.

You receive JSON lines, one per trait: {"id": <int>, "label": <label>, "description": <definition>}.
For each trait, first note in a few words what the rewrite must keep (the disposition, its scope, any contrast or qualification), then write the rewrite.
Respond with a JSON object only, no other text, with the reason before the rewrite in every result:
{"results": [{"id": <int>, "reason": "<what must be kept, a few words>", "paraphrase": "<the rewrite>"}, ...]}
with one result per input id."""

# Round 4 (2026-10-02, Roger: "a significantly larger test"): two more paraphrase sets, each in a style
# unlike round 3's, so that recall is measured on several ways of re-proposing the same trait.  Each
# style is its own prompt with its own pinned version (rubric_versions: calibration_paraphrase_<style>).
_STYLE_CONTEXT = """You rewrite short definitions of personality traits for a calibration experiment.

Context: we test whether a text-embedding search finds an existing trait when someone re-proposes it in their own words. So each rewrite must keep the meaning (the same disposition, the same scope) while sounding like a different writer: {voice}

Rules for each rewrite:
- Start with "This means" and describe the same disposition.
{rules}- Do not use the trait's label word, or any word formed from it.
- Write plain prose, no lists.

You receive JSON lines, one per trait: {{"id": <int>, "label": <label>, "description": <definition>}}.
For each trait, first note in a few words what the rewrite must keep, then write the rewrite.
Respond with a JSON object only, no other text, with the reason before the rewrite in every result:
{{"results": [{{"id": <int>, "reason": "<what must be kept, a few words>", "paraphrase": "<the rewrite>"}}, ...]}}
with one result per input id."""

PARAPHRASE_STYLE_PROMPTS: dict[str, str] = {
    "plain": _STYLE_CONTEXT.format(
        voice="a friend explaining it over coffee, in plain everyday words.",
        rules=("- Use short, everyday words, the way people talk; no technical, academic or literary vocabulary.\n"
               "- Keep any contrast the original draws (\"rather than X\"), said in everyday words; do not add examples.\n"
               "- One or two sentences, about as long as the original or shorter.\n")),
    "terse": _STYLE_CONTEXT.format(
        voice="a dictionary giving the core sense, tersely.",
        rules=("- Give the core sense the way a dictionary definition does: one clause, at most 12 words after "
               "\"This means\".\n"
               "- Keep the central disposition; drop examples and secondary detail; keep a contrast only if the sense "
               "depends on it.\n")),
}
PARAPHRASE_STYLE_VERSIONS: dict[str, int] = {"plain": 1, "terse": 1}


def paraphrase_prompt(style: str = "standard") -> str:
    """The system prompt for a paraphrase style: ``standard`` (round 3's
    :data:`PARAPHRASE_PROMPT`), ``plain`` or ``terse``."""
    return PARAPHRASE_PROMPT if style == "standard" else PARAPHRASE_STYLE_PROMPTS[style]


def paraphrase_version(style: str = "standard") -> int:
    return PARAPHRASE_PROMPT_VERSION if style == "standard" else PARAPHRASE_STYLE_VERSIONS[style]


BLINDED_PROMPT = """You compare two lists of nearest neighbours for a personality trait, for a calibration experiment.

Context: a text-embedding search returned, for one trait, the five existing traits it considers closest in meaning. Two versions of the search are being compared; you see both lists in random order, unlabelled. Judge which list better contains the traits a careful reader would consider closest in meaning to the given trait: synonyms and near-synonyms first, then closely related dispositions. A trait's opposite (its antonym) is not close in meaning, even though it shares a topic. Judge by the definitions, not the labels alone.

This needs judgement. Prefer "same" when the lists are equally good or differ only in order or in one marginal entry; prefer a list when it clearly has more of the truly close traits or fewer opposites and unrelated ones.

Respond with a JSON object only, no other text. Reason first, then commit to the preference:
{"reason": "<two or three sentences comparing the lists>", "preference": "A" | "B" | "same"}"""


def paraphrase_user(items: Sequence[dict]) -> str:
    return "\n".join(json.dumps({"id": it["id"], "label": it["label"], "description": it["description"]},
                                ensure_ascii=False) for it in items)


def parse_paraphrases(text: Optional[str], ids: Sequence[int]) -> dict[int, str]:
    """``{id: paraphrase}`` for the ids asked; rows that are missing, empty or not
    in the "This means ..." form are left out (counted as failures)."""
    if not text:
        return {}
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except json.JSONDecodeError:
        return {}
    rows = d.get("results") if isinstance(d, dict) else None
    out = {}
    want = set(ids)
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        i, p = r.get("id"), r.get("paraphrase")
        if i in want and isinstance(p, str) and p.strip().startswith("This means"):
            out[i] = p.strip()
    return out


async def run_paraphrases(client, items: Sequence[dict], *, usage: MultiModelUsage, model: str = PARAPHRASE_MODEL,
                          batch_size: int = PARAPHRASE_BATCH, concurrency: int = 4, limiter=None,
                          style: str = "standard") -> dict[str, str]:
    """``items``: ``[{"stem", "label", "description"}]`` -> ``{stem: paraphrase}``.
    A failed row is retried once in a batch of its own kind.  ``style`` picks
    the prompt (:func:`paraphrase_prompt`)."""
    system = paraphrase_prompt(style)
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, str] = {}

    async def one(batch: Sequence[dict]) -> None:
        numbered = [dict(it, id=k + 1) for k, it in enumerate(batch)]
        async with sem:
            text = await call_anthropic_json(client, system=system, user=paraphrase_user(numbered),
                                             model=model, max_tokens=4000, temperature=0.0, usage=usage,
                                             limiter=limiter)
        got = parse_paraphrases(text, [it["id"] for it in numbered])
        for it in numbered:
            if it["id"] in got:
                results[it["stem"]] = got[it["id"]]

    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    await asyncio.gather(*(one(b) for b in batches))
    missing = [it for it in items if it["stem"] not in results]
    if missing:
        await asyncio.gather(*(one(missing[i:i + batch_size]) for i in range(0, len(missing), batch_size)))
    warn_if_low_parse_rate(label=f"calibrate:paraphrase:{style}:{model}", n_ok=len(results), n_total=len(items),
                           logger_obj=logger)
    return results


def blinded_user(item: Mapping, *, swap: bool, desc_of: Mapping[str, str], label_of: Mapping[str, str]) -> str:
    A, B = (item["B"], item["A"]) if swap else (item["A"], item["B"])

    def block(name, stems):
        return f"List {name}:\n" + "\n".join(f"- {label_of.get(s, s)}: {desc_of.get(s, '')}" for s in stems)
    return (f"Trait: {item['label']}\nDefinition: {item['description']}\n\n{block('A', A)}\n\n{block('B', B)}")


def parse_blinded(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except json.JSONDecodeError:
        return None
    pref = d.get("preference") if isinstance(d, dict) else None
    return pref if pref in ("A", "B", "same") else None


async def run_blinded(client, items: Sequence[dict], *, usage: MultiModelUsage, desc_of: Mapping[str, str],
                      label_of: Mapping[str, str], model: str = JUDGE_MODEL, concurrency: int = 4,
                      limiter=None) -> dict:
    """Each comparison twice (lists swapped).  Returns per-item verdicts in terms
    of the hidden key (``full`` / ``strip`` / ``same`` / ``inconsistent``), the
    share preferring ``strip`` among decided items, and the parse rate."""
    sem = asyncio.Semaphore(concurrency)
    raw: dict[tuple[int, bool], Optional[str]] = {}

    async def ask(it, swap):
        async with sem:
            text = await call_anthropic_json(client, system=BLINDED_PROMPT,
                                             user=blinded_user(it, swap=swap, desc_of=desc_of, label_of=label_of),
                                             model=model, max_tokens=600, temperature=0.0, usage=usage,
                                             limiter=limiter)
        raw[(it["id"], swap)] = parse_blinded(text)

    await asyncio.gather(*(ask(it, s) for it in items for s in (False, True)))
    verdicts = {}
    for it in items:
        p0, p1 = raw.get((it["id"], False)), raw.get((it["id"], True))
        side = lambda p, swap: ("same" if p == "same" else  # noqa: E731
                                it["key"][{"A": "B", "B": "A"}[p] if swap else p] if p in ("A", "B") else None)
        v0, v1 = side(p0, False), side(p1, True)
        verdicts[it["id"]] = v0 if (v0 is not None and v0 == v1) else ("unparsed" if None in (v0, v1) else "inconsistent")
    n_ok = sum(1 for v in raw.values() if v is not None)
    warn_if_low_parse_rate(label=f"calibrate:blinded:{model}", n_ok=n_ok, n_total=len(raw), logger_obj=logger)
    decided = [v for v in verdicts.values() if v in ("full", "strip")]
    return {"verdicts": verdicts, "n": len(items), "n_parsed": n_ok, "n_calls": len(raw),
            "counts": {k: sum(v == k for v in verdicts.values()) for k in ("full", "strip", "same", "inconsistent", "unparsed")},
            "preference_strip_share": round(sum(v == "strip" for v in decided) / len(decided), 4) if decided else None}


def llm_estimate(n_paraphrase: int, n_blinded: int, *, n_styled: int = 0) -> Estimate:
    """About 60 input and 90 output tokens per paraphrased description (a short
    reason, then the rewrite; plus the prompt per batch); about 700 input and 120 output tokens per blinded call,
    two calls per comparison.  ``n_styled``: round 4's paraphrases in the other
    styles, counted the same way (the measured round-3 cost was $0.32 for 659)."""
    est = Estimate()
    n_batches = -(-n_paraphrase // PARAPHRASE_BATCH)
    est.add("(g) paraphrases", PARAPHRASE_MODEL, n_batches, 500 + 60 * PARAPHRASE_BATCH, 90 * PARAPHRASE_BATCH)
    if n_styled:
        est.add("round 4 styled paraphrases", PARAPHRASE_MODEL, -(-n_styled // PARAPHRASE_BATCH),
                500 + 60 * PARAPHRASE_BATCH, 90 * PARAPHRASE_BATCH)
    est.add("(e) blinded judgement", JUDGE_MODEL, 2 * n_blinded, 900, 150)
    return est
