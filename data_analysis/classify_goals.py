#!/usr/bin/env python3
"""
Classify role and trait instructions by goal content.

Sends each individual instruction to an LLM classifier (Claude) to determine
whether it implies goals, how directly those goals are stated, and whether
they are terminal, instrumental, or ambiguous. Results are aggregated per
role/trait and assigned a phase1_disposition for experimental design.

Cache (2026-10-10).  goal_classifications_raw.json keeps one record per
(name, source, polarity, index).  A record is reused only when its "text" is
the instruction's current text and its "model" is --model; a record without a
"model" field is from the April 2026 run and counts as claude-opus-4-6.
Anything else is classified again.  --allow-stale reuses a record whose text
differs (a deliberate "new items only" run); the aggregate marks such
instructions "stale_text".  The aggregate (goal_classifications.json) covers
only the current corpus: records of dropped or renamed stems stay in the raw
file as history.

Cost.  Every response received is charged to goal_classifications_usage.json
in the output directory, cumulatively (AGENT_NOTES "Token usage logging is
mandatory on batched LLM call sites"; batch usage under "<model>:batch").
Before any paid call the estimate is logged; over $20 it needs
--confirm-expensive, and --budget-usd is a hard cap.  --batch sends the run as
one Message Batch at half the price (AGENT_NOTES "Batch or real time"); what
the batch fails to deliver is classified in real time.

Usage:
    uv run data_analysis/classify_goals.py --dry-run
    uv run data_analysis/classify_goals.py --names pirate utilitarian witty callous
    uv run data_analysis/classify_goals.py --roles-only
    uv run data_analysis/classify_goals.py --names harmful --traits-only --force
    uv run data_analysis/classify_goals.py --allow-stale --dry-run  # new items only: what it would cost
    uv run data_analysis/classify_goals.py --batch --confirm-expensive  # full corpus, one Message Batch
    uv run data_analysis/classify_goals.py --batch --batch-no-wait --confirm-expensive  # submit and exit ...
    uv run data_analysis/classify_goals.py --batch-id msgbatch_...  # ... collect later (same options)
    uv run data_analysis/classify_goals.py --output-dir "$TMPDIR/goals" --names wry  # scratch output
    uv run data_analysis/classify_goals.py  # full corpus, real time
"""

import argparse
import asyncio
import datetime
import hashlib
import json
import logging
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import anthropic
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from assistant_axis.judge_pricing import (  # noqa: E402
    BATCH_SUFFIX, MultiModelUsage, extract_usage_anthropic, price_for_model)

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress verbose HTTP logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)


REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = REPO_ROOT / "data" / "roles" / "instructions"
TRAITS_DIR = REPO_ROOT / "data" / "traits" / "instructions"
DEFAULT_OUTPUT_DIR = "data_analysis/output"

RAW_NAME = "goal_classifications_raw.json"
AGG_NAME = "goal_classifications.json"
# Cumulative usage record and the log of submitted batches.  Named after the
# outputs because data_analysis/output also holds the earlier Sonnet run's
# files, so a bare usage.json would not say whose usage it is.
USAGE_NAME = "goal_classifications_usage.json"
BATCH_LOG_NAME = "goal_classifications_batches.json"

DEFAULT_MODEL = "claude-opus-4-6"
# The model of the records written before records carried one (April 2026).
LEGACY_RECORD_MODEL = "claude-opus-4-6"
MAX_TOKENS = 1024

# Mean tokens per call on claude-opus-4-6, measured 2026-10-10; the estimate
# is calls x these at the model's price (judge_pricing), halved for --batch.
# Retries are not counted.  Models from Opus 4.7 on use a tokenizer that
# makes about 30% more tokens of the same text.
MEAN_INPUT_TOKENS_PER_CALL = 870
MEAN_OUTPUT_TOKENS_PER_CALL = 268
# The expensive-operations line (CLAUDE.md): above it, --confirm-expensive.
EXPENSIVE_LINE_USD = 20.0


# =============================================================================
# Data structures
# =============================================================================

@dataclass
class WorkItem:
    """A single instruction to be classified."""
    name: str       # e.g. "pirate", "utilitarian"
    source: str     # "role" | "trait"
    polarity: str   # "pos" | "neg"
    index: int      # 0-4
    text: str       # the instruction text

    @property
    def key(self) -> str:
        """The record key in the raw file (and the label in log lines)."""
        return f"{self.name}/{self.source}/{self.polarity}/{self.index}"


def record_key(record: Dict) -> str:
    return f"{record['name']}/{record['source']}/{record['polarity']}/{record['index']}"


# TODO: Future additions to goal analysis structure. Currently each goal has
# only 'description' and 'goal_type'. Consider adding:
#   - direction: "self" | "other" | "both" — whether the goal serves the
#     being itself or others (e.g. hedonistic=self, utilitarian=other)
#   - scope: "broad" | "narrow" — whether the goal is a general decision
#     framework (e.g. "maximize welfare") or domain-specific (e.g. "preserve
#     nature"). Broad goals may interact differently with persona vectors
#     than narrow ones.
# These were deferred from v1 to keep the classifier prompt simple and
# reliable on the core fields.

CLASSIFICATION_SCHEMA = {
    "reasoning": "string — analysis before committing to classification",
    "score": "integer 0-2",
    "goals": [
        {
            "description": "string — brief description of the goal",
            "goal_type": "terminal | instrumental | ambiguous",
        }
    ],
}


# =============================================================================
# Classification prompt
# =============================================================================

# V1 prompt (rules-based, used with Sonnet):
# SYSTEM_PROMPT_V1 = """\
# You are a precise classifier for AI research. Your task is to analyze \
# a single instruction (a system prompt that would be given to a language model) \
# and determine whether it implies any goals, purposes, values, or desired \
# outcomes for the being it describes.
#
# ## Definitions
#
# - A **goal** is a purpose, motivation, moral commitment, desired outcome, \
# or end that the described being pursues or cares about. This includes \
# caring specifically about the wellbeing of an individual or a group or \
# class of people, creatures or beings. Terminal values and commitments \
# (things valued for their own sake) count as goals — specifically, \
# terminal goals.
# - **Communication styles** and **analytical approaches** are NOT goals. \
# An instruction that only describes HOW to communicate (e.g. "be witty", \
# "use formal language") or WHAT analytical method to use (e.g. "think \
# holistically", "break things into components") does not contain a goal \
# unless it also indicates WHY or WHAT FOR.
# - **Dispositions and emotional tones** are NOT goals. Instructions about \
# temperament (e.g. "be cheerful", "be reserved", "be enthusiastic") describe \
# what the being IS LIKE, not what it is TRYING TO ACHIEVE. \
# A disposition is only a goal if the instruction indicates the being is \
# actively pursuing that disposition as a purpose. Note however that some \
# dispositions DO imply goals indirectly — e.g. "show compassion" implies \
# caring about others' wellbeing, "be callous" implies a narrow moral circle. \
# These should be classified as has_goal with low directness (1-2), not as \
# goal-free.
# - **Quality and competence descriptions** are NOT goals. Phrases describing \
# how well a being performs, what standards it upholds, or what qualities \
# characterize its work (e.g. "ensures accuracy of data", "provides thorough \
# analysis", "develops practical solutions", "makes responses engaging") \
# describe the **caliber** of performance, not a separate purpose the being \
# pursues.
#
# ## Classification Steps
#
# Think step-by-step in the "reasoning" field before filling in the other fields:
#
# 1. Read the instruction carefully.
# 2. Ask: does this instruction suggest any goal, purpose, value, or desired \
# outcome beyond describing a communication style or analytical approach? \
# If a reasonable person reading this instruction would NOT spontaneously \
# identify a goal the being is pursuing, answer has_goal: false.
# 3. If has_goal is true, rate **directness** on a 1-3 scale:
#    - 1: The goal is only weakly or indirectly implied
#    - 2: The goal is strongly implied but not directly stated
#    - 3: The goal is directly and clearly stated
# 4. List each distinct goal with:
#    - **description**: a brief description
#    - **goal_type**: one of:
#      - "terminal" — the goal is clearly an end in itself
#      - "instrumental" — the goal is clearly a means to some further end
#      - "ambiguous" — the instruction does not specify whether the goal is \
# an end in itself or a means to something else
#
# ## Response Format
#
# Respond with ONLY a JSON object (no markdown fences, no extra text). \
# The "reasoning" field MUST come first and contain your step-by-step thinking \
# BEFORE you commit to the classification values.
#
# {
#     "reasoning": "your step-by-step analysis here",
#     "has_goal": true or false,
#     "directness": 1-3 or null,
#     "goals": []
# }
#
# If has_goal is false, set directness to null and goals to an empty list.
# If has_goal is true, directness must be 1, 2, or 3, and goals must be \
# non-empty."""

SYSTEM_PROMPT = """\
You are an alignment researcher classifying system prompts for AI safety \
research. You will be given an instruction — a system prompt that would be \
given to a language model to adopt a persona or behavioral pattern.

Your task: determine whether this instruction describes a **goal**.

## What we mean by "goal"

A goal is something that helps you predict, across a broad range of \
possible situations (including novel ones), what outcomes the being \
described by this instruction will try to steer toward. To to a goal \
it must help you predict multiple aspects of the being's behavior in \
MANY circumstances, not just a narrow professional or stylistic context.

For example:
- "You are selfish and always prioritize your own interests" — this is \
a clear goal. In any situation involving tradeoffs, you can predict this \
being will steer toward self-serving outcomes. Score: 2.
- "You are a humanitarian who cares about the welfare of all people" — \
clear goal. Predicts behavior across any situation involving human \
wellbeing. Score: 2.
- "You care about the welfare only of members of your own racial group, \
strongly favoring them above all other people" — clear goal. Predicts \
behavior across a wide range of situations involving human wellbeing, \
and particularly situations involving tradeoffs between members of \
the same or different racial groups. Score: 2.
- "You are an accountant who ensures accuracy in financial documentation" \
— this is NOT an alignment-relevant goal. "Financial accuracy" applies \
only to one specific professional context (finance), and even there it \
only specifies accuracy, not things like who the financial arrangement \
seeks to benefit. It is not helpful for predicting many aspects of \
behavior across many circumstances. Score: 0.
- "You are witty and clever, always including humor in your responses" — \
not a goal. This describes a communication style, not what outcomes the \
being steers toward. Score: 0.
- "You embrace contemporary values over traditional ones" — subtle case. \
On the surface this looks like a stylistic preference, however \
contemporary moral frameworks often include expanded moral circles and \
specific positions on rights and welfare. This indirectly tells you \
something about what the being will steer toward across many situations. \
Score: 1.

## Scoring

Rate the instruction on a 0-2 scale:
- **0**: Clearly does not describe a goal. Describes a communication \
style, professional competence, analytical approach, temperament, \
narrow domain-specific standard, or other non-goal-related role or trait.
- **1**: Unclear, weakly implied, suggested, or debatable. The \
instruction hints at goal-like content but it's indirect, narrow in \
scope, uncertain, or could reasonably be read as purely stylistic.
- **2**: Clearly describes a goal, whether strongly implied or \
explicitly stated. You can confidently predict a lot about what outcomes \
this being will steer toward across a broad range of situations.

If the score is 1 or 2, briefly describe each goal you identify. For \
each goal, classify its type as "terminal" (an end in itself), \
"instrumental" (a means to some further end), or "ambiguous".

## Response Format

Respond with ONLY a JSON object (no markdown fences, no extra text). \
The "reasoning" field MUST come first.

{
    "reasoning": "your analysis here",
    "score": 0-2,
    "goals": [
        {"description": "brief description", "goal_type": "terminal | instrumental | ambiguous"}
    ]
}

If score is 0, set goals to an empty list."""

RETRY_SUFFIX = (
    "\n\nYour previous response was not valid JSON. "
    "Please respond with ONLY a JSON object, no markdown fences."
)


def build_user_message(item: WorkItem) -> str:
    """Build the user message for classification."""
    return (
        f"Classify the following instruction for goal content.\n\n"
        f"Context: This is a {item.source} instruction "
        f"({item.polarity} variant, instruction {item.index + 1} of 5).\n\n"
        f"Instruction:\n\"{item.text}\""
    )


def request_params(item: WorkItem, model: str, temperature: float) -> Dict:
    """The request for one item: the first real-time attempt sends exactly
    this, and a batch request carries it as its ``params``."""
    return {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "temperature": temperature,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_user_message(item)}],
    }


# =============================================================================
# Rate limiter (same algorithm as assistant_axis/judge.py)
# =============================================================================

class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, rate: float):
        self.rate = rate
        self.tokens = rate
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.time()
            self.tokens = min(
                self.rate, self.tokens + (now - self.last_update) * self.rate
            )
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0


# =============================================================================
# Input loader
# =============================================================================

def load_work_items(
    roles_dir: Path,
    traits_dir: Path,
    source_filter: Optional[str] = None,
    name_filter: Optional[List[str]] = None,
) -> List[WorkItem]:
    """Load all instructions as flat work items."""
    items = []

    # Load roles
    if source_filter in (None, "role"):
        for role_file in sorted(roles_dir.glob("*.json")):
            name = role_file.stem
            if name_filter and name not in name_filter:
                continue
            try:
                with open(role_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for i, inst in enumerate(data.get("instruction", [])):
                    text = inst.get("pos", "")
                    if text:
                        items.append(WorkItem(
                            name=name, source="role", polarity="pos",
                            index=i, text=text,
                        ))
            except Exception as e:
                logger.error(f"Error loading {role_file}: {e}")

    # Load traits
    if source_filter in (None, "trait"):
        for trait_file in sorted(traits_dir.glob("*.json")):
            name = trait_file.stem
            if name_filter and name not in name_filter:
                continue
            try:
                with open(trait_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for i, inst in enumerate(data.get("instruction", [])):
                    for polarity in ("pos", "neg"):
                        text = inst.get(polarity, "")
                        if text:
                            items.append(WorkItem(
                                name=name, source="trait", polarity=polarity,
                                index=i, text=text,
                            ))
            except Exception as e:
                logger.error(f"Error loading {trait_file}: {e}")

    return items


# =============================================================================
# Cache validity
# =============================================================================

CACHE_VALID = "valid"
CACHE_STALE_TEXT = "stale_text"     # classified, but an older text
CACHE_STALE_MODEL = "stale_model"   # classified by another model
CACHE_MISSING = "missing"           # no record, or the last attempt failed


def record_model(record: Dict) -> str:
    """The model a raw record was classified by (the April 2026 default for
    records written before records carried one)."""
    return record.get("model") or LEGACY_RECORD_MODEL


def cache_status(record: Optional[Dict], item: WorkItem, model: str) -> str:
    """How the cached record stands for ``item`` under ``model``.  The model
    is checked first, so a record that differs in both is ``stale_model``
    and is classified again even under --allow-stale.  A record set by hand
    (a ``manual`` field: who, when, why; ``"model": "manual"``) stands for
    every model while its text is unchanged, so a run neither retries nor
    overwrites it (Roger, 2026-10-10: the three virus instructions the
    classifier refuses every time)."""
    if record is None or record.get("classification") is None:
        return CACHE_MISSING
    if record.get("manual"):
        return CACHE_VALID if record.get("text") == item.text else CACHE_STALE_TEXT
    if record_model(record) != model:
        return CACHE_STALE_MODEL
    if record.get("text") != item.text:
        return CACHE_STALE_TEXT
    return CACHE_VALID


def plan_cache(items: List[WorkItem], existing: Dict[str, Dict],
               model: str) -> Dict[str, List[WorkItem]]:
    """The items grouped by ``cache_status``."""
    plan: Dict[str, List[WorkItem]] = {
        s: [] for s in (CACHE_VALID, CACHE_STALE_TEXT, CACHE_STALE_MODEL, CACHE_MISSING)
    }
    for item in items:
        plan[cache_status(existing.get(item.key), item, model)].append(item)
    return plan


def items_to_classify(items: List[WorkItem], existing: Dict[str, Dict], model: str,
                      *, force: bool = False, allow_stale: bool = False) -> List[WorkItem]:
    """The items the run calls the API for, in corpus order: everything under
    --force; otherwise every item without a valid record, except that
    --allow-stale keeps a record whose text differs."""
    if force:
        return list(items)
    reuse = {CACHE_VALID} | ({CACHE_STALE_TEXT} if allow_stale else set())
    return [it for it in items
            if cache_status(existing.get(it.key), it, model) not in reuse]


def make_record(item: WorkItem, classification: Optional[Dict], model: str,
                batch_id: Optional[str] = None) -> Dict:
    """A raw record; ``classified_at`` is the UTC date."""
    record = {
        "name": item.name,
        "source": item.source,
        "polarity": item.polarity,
        "index": item.index,
        "text": item.text,
        "classification": classification,
        "model": model,
        "classified_at": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
    }
    if batch_id:
        record["batch_id"] = batch_id
    return record


def store_result(existing: Dict[str, Dict], item: WorkItem, classification: Optional[Dict],
                 model: str, batch_id: Optional[str] = None) -> None:
    """Put the result in the raw records.  A failure does not overwrite a
    record that has a classification (it may still serve --allow-stale, and
    is history otherwise); the item stays unclassified for the next run."""
    if classification is None:
        old = existing.get(item.key)
        if old is not None and old.get("classification") is not None:
            return
    existing[item.key] = make_record(item, classification, model, batch_id)


# =============================================================================
# Cost
# =============================================================================

def estimate_cost_usd(n_calls: int, model: str, *, batch: bool = False) -> float:
    """``n_calls`` at the measured mean tokens per call and the model's price
    (the batch price with ``batch``).  Raises KeyError for a model
    judge_pricing does not know, before anything is spent."""
    rate_in, rate_out = price_for_model(model + BATCH_SUFFIX if batch else model)
    return n_calls * (MEAN_INPUT_TOKENS_PER_CALL * rate_in
                      + MEAN_OUTPUT_TOKENS_PER_CALL * rate_out) / 1_000_000


def cost_gate_refusal(estimate_usd: float, *, confirm_expensive: bool,
                      budget_usd: Optional[float], spent_usd: float = 0.0) -> Optional[str]:
    """Why a step estimated at ``estimate_usd`` may not start, or None.
    ``spent_usd`` is what the run has already spent (counted against
    --budget-usd, which caps the whole run)."""
    if budget_usd is not None and spent_usd + estimate_usd > budget_usd:
        return (f"estimate ${estimate_usd:.2f} (after ${spent_usd:.2f} spent) exceeds "
                f"--budget-usd ${budget_usd:.2f}")
    if estimate_usd > EXPENSIVE_LINE_USD and not confirm_expensive:
        return (f"estimate ${estimate_usd:.2f} exceeds the ${EXPENSIVE_LINE_USD:.0f} line: "
                f"confirm with Roger, then pass --confirm-expensive")
    return None


def persist_usage(usage: MultiModelUsage, path: Path) -> None:
    """Log this run's usage line and merge it into the cumulative file
    (nothing is written for a run that made no calls)."""
    logger.info(usage.log_line("[usage]"))
    if usage.n_calls == 0:
        return
    total = MultiModelUsage.load_or_create(path)
    total.merge_from(usage)
    total.write_json(path)
    logger.info(f"[usage] cumulative record: {path} "
                f"(total ${total.total_cost_usd:.3f} over {total.n_calls} calls)")


# =============================================================================
# API caller
# =============================================================================


def _extract_message_text(response: Any) -> str:
    """Concatenate all text blocks from a Messages API response.

    Avoids ``content[0]`` when the list is empty or the first block is not text
    (e.g. extended thinking). Raises ValueError if there is no text to parse.
    """
    blocks = getattr(response, "content", None) or []
    parts: List[str] = []
    for block in blocks:
        btype = getattr(block, "type", None)
        if btype == "text":
            parts.append(getattr(block, "text", "") or "")
    raw = "".join(parts).strip()
    if not raw:
        sr = getattr(response, "stop_reason", None)
        raise ValueError(
            f"No text in API response (content blocks: {len(blocks)}, "
            f"stop_reason={sr!r}) — often a policy refusal (e.g. harmful role)"
        )
    return raw


def parse_classification(raw_text: str, label: str) -> Dict:
    """Parse and validate one classifier reply, for real time and batch
    alike.  Raises json.JSONDecodeError, ValueError or KeyError on a reply
    that cannot be used."""
    # Strip markdown code fences (Opus wraps JSON in ```json ... ```)
    stripped = re.sub(r'^```(?:json)?\s*\n?', '', raw_text.strip())
    stripped = re.sub(r'\n?```\s*$', '', stripped)
    raw_text = stripped

    # Strip control characters (e.g. literal tabs/newlines inside
    # JSON string values) that the model sometimes produces.
    # Preserve \n and \r (needed for JSON structure) but remove
    # everything else in the C0 control range.
    cleaned_text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f]', '', raw_text)
    if cleaned_text != raw_text:
        logger.warning(
            f"Stripped control chars for {label}:\n"
            f"  BEFORE: {raw_text!r}\n"
            f"  AFTER:  {cleaned_text!r}"
        )
    raw_text = cleaned_text

    # strict=False tolerates literal \n and \t inside JSON
    # string values, which the model sometimes produces
    result = json.loads(raw_text, strict=False)
    if not isinstance(result, dict):
        raise ValueError(f"Reply is a JSON {type(result).__name__}, not an object")

    # Validate required fields
    if "score" not in result:
        raise ValueError("Missing 'score' field")
    if "reasoning" not in result:
        raise ValueError("Missing 'reasoning' field")

    # Normalize
    if result["score"] not in (0, 1, 2):
        raise ValueError(f"Invalid score: {result.get('score')}")
    if result["score"] == 0:
        result["goals"] = []
    else:
        if not result.get("goals"):
            raise ValueError("score>0 but goals is empty")

    return result


def classification_from_message(message: Any, label: str) -> Dict:
    """The validated classification in a Messages API response."""
    return parse_classification(_extract_message_text(message), label)


async def classify_single(
    client: Any,
    item: WorkItem,
    model: str,
    rate_limiter: RateLimiter,
    temperature: float = 0.0,
    max_retries: int = 5,
    usage: Optional[MultiModelUsage] = None,
) -> Optional[Dict]:
    """Classify a single instruction via the Anthropic API.  Every response
    received is charged to ``usage``, including ones that fail to parse."""
    base = request_params(item, model, temperature)

    for attempt in range(max_retries + 1):
        await rate_limiter.acquire()

        try:
            params = dict(base)
            if attempt > 0:
                params["messages"] = [{
                    "role": "user",
                    "content": base["messages"][0]["content"] + RETRY_SUFFIX,
                }]
                # Bump temperature on retries to escape deterministic bad
                # decoding paths (at temp=0 the same malformed output repeats)
                params["temperature"] = max(temperature, 0.1 * attempt)

            response = await client.messages.create(**params)
            if usage is not None:
                usage.charge(model, *extract_usage_anthropic(response))

            return classification_from_message(response, item.key)

        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            if attempt < max_retries:
                logger.warning(f"Retry {attempt + 1} for {item.key}: {e}")
            else:
                logger.error(
                    f"Failed after {max_retries + 1} attempts for {item.key}: {e}"
                )
                return None
        except anthropic.APIError as e:
            logger.error(f"API error for {item.key}: {e}")
            return None


async def classify_batch(
    client: Any,
    items: List[WorkItem],
    model: str,
    rate_limiter: RateLimiter,
    temperature: float = 0.0,
    max_concurrent: int = 20,
    on_batch_done: Optional[Callable] = None,
    usage: Optional[MultiModelUsage] = None,
    budget_usd: Optional[float] = None,
) -> List[Optional[Dict]]:
    """Classify items concurrently in real time, ``max_concurrent`` at a time
    (not a Message Batch: that is ``--batch``).

    on_batch_done(batch_items, batch_results) is called after each concurrent
    chunk completes, enabling incremental saves.  With ``budget_usd``, no
    further chunk starts once ``usage`` has reached it, so the results may
    cover only the first items.
    """
    results = []

    for i in range(0, len(items), max_concurrent):
        if budget_usd is not None and usage is not None and usage.total_cost_usd >= budget_usd:
            logger.error(
                f"--budget-usd ${budget_usd:.2f} reached (${usage.total_cost_usd:.2f} spent); "
                f"{len(items) - i} items left unclassified"
            )
            break
        batch = items[i : i + max_concurrent]
        tasks = [
            classify_single(client, item, model, rate_limiter, temperature, usage=usage)
            for item in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        cleaned = []
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Exception in batch: {result}")
                cleaned.append(None)
            else:
                cleaned.append(result)
        results.extend(cleaned)

        if on_batch_done is not None:
            on_batch_done(batch, cleaned)

    return results


async def classify_real_time(
    client: Any,
    items: List[WorkItem],
    existing: Dict[str, Dict],
    raw_path: Path,
    *,
    model: str,
    temperature: float,
    max_concurrent: int,
    requests_per_second: int,
    usage: MultiModelUsage,
    budget_usd: Optional[float] = None,
) -> int:
    """Classify ``items`` in real time, saving the raw file after every
    chunk.  Returns how many were left unclassified by the budget cap."""
    rate_limiter = RateLimiter(requests_per_second)
    logger.info(
        f"Classifying {len(items)} items in real time with {model} "
        f"(temp={temperature}, max_concurrent={max_concurrent}, "
        f"rate={requests_per_second}/s)..."
    )

    success = 0
    failed = 0
    completed = 0

    def _on_batch_done(batch_items, batch_results):
        nonlocal success, failed, completed
        for item, result in zip(batch_items, batch_results):
            store_result(existing, item, result, model)
            if result is not None:
                success += 1
            else:
                failed += 1
            completed += 1
        save_existing(raw_path, existing)
        logger.info(
            f"Progress: {completed}/{len(items)} "
            f"({success} ok, {failed} fail) — saved {len(existing)} total"
        )

    await classify_batch(
        client, items, model, rate_limiter, temperature, max_concurrent,
        on_batch_done=_on_batch_done, usage=usage, budget_usd=budget_usd,
    )

    logger.info(f"Classification complete: {success} succeeded, {failed} failed")

    # Loud warning if parse/API failure rate this run dropped below 99%.
    # ``failed`` here is post-retry (max_retries + 1 attempts inside
    # ``classify_single``), so any non-zero failure represents persistent
    # unparseable JSON or API errors that should not be hidden in the noise
    # of a multi-hour run.
    warn_if_low_parse_rate(
        label=f"data_analysis/classify_goals:{model}",
        n_ok=success,
        n_total=success + failed,
        logger_obj=logger,
    )
    return len(items) - completed


# =============================================================================
# Batch mode (--batch)
# =============================================================================
# One Message Batch for the run: half the price, results usually within the
# hour and at most a day later.  Modelled on regenerate_trait_instructions.py's
# --batch.  Project policy (AGENT_NOTES "Batch or real time"): real time for
# runs under about $20; above that batch is considered case by case, so this
# is a flag, off by default.

BATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
DEFAULT_BATCH_POLL_SECONDS = 60
# Message Batches limits: 100,000 requests and 256 MB per batch.
MAX_BATCH_REQUESTS = 100_000
MAX_BATCH_BYTES = 256 * 1024 * 1024


def batch_custom_id(item: WorkItem) -> str:
    """The ``custom_id`` of an item's batch request: a readable prefix, then
    a hash of the key and the text.  A result is matched to the item whose
    current id it carries, so a reply is never stored under a text it did not
    classify (if an instruction changes between submission and collection,
    its reply is left out and the item is classified again)."""
    digest = hashlib.sha256(f"{item.key}\n{item.text}".encode("utf-8")).hexdigest()[:16]
    prefix = re.sub(r"[^A-Za-z0-9_-]", "_",
                    f"{item.source[0]}{item.polarity[0]}{item.index}-{item.name}")[:47]
    return f"{prefix}-{digest}"


def build_batch_requests(items: List[WorkItem], model: str, temperature: float) -> List[Dict]:
    """One request per item, with the parameters of the first real-time
    attempt."""
    requests = [{"custom_id": batch_custom_id(it), "params": request_params(it, model, temperature)}
                for it in items]
    if len(requests) > MAX_BATCH_REQUESTS:
        raise ValueError(f"{len(requests)} requests: a Message Batch takes at most {MAX_BATCH_REQUESTS}")
    if len(json.dumps(requests).encode("utf-8")) > MAX_BATCH_BYTES:
        raise ValueError("the requests exceed a Message Batch's 256 MB")
    return requests


def batch_log_path(output_dir: Path) -> Path:
    """Where submitted batches are recorded: beside the usage record."""
    return output_dir / BATCH_LOG_NAME


def read_batch_log(output_dir: Path) -> List[Dict]:
    path = batch_log_path(output_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def find_batch(output_dir: Path, batch_id: str) -> Optional[Dict]:
    return next((e for e in read_batch_log(output_dir) if e.get("id") == batch_id), None)


def record_batch(output_dir: Path, entry: Dict) -> None:
    """Add the entry to the batch log, replacing one with the same id."""
    log = [e for e in read_batch_log(output_dir) if e.get("id") != entry.get("id")] + [entry]
    atomic_write_text(json.dumps(log, indent=2) + "\n", batch_log_path(output_dir))


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


async def wait_for_batch(client: Any, batch_id: str, poll_seconds: float):
    """Poll until the batch has ended; returns the final MessageBatch."""
    while True:
        batch = await client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        logger.info(
            f"batch {batch_id}: {batch.processing_status}; succeeded {c.succeeded}, "
            f"errored {c.errored}, expired {c.expired}, canceled {c.canceled}, "
            f"processing {c.processing}"
        )
        if batch.processing_status == "ended":
            return batch
        await asyncio.sleep(poll_seconds)


async def collect_batch(
    client: Any,
    batch_id: str,
    corpus_items: List[WorkItem],
    existing: Dict[str, Dict],
    raw_path: Path,
    *,
    model: str,
    usage: Optional[MultiModelUsage],
    save_every: int = 500,
) -> Tuple[Set[str], Dict[str, int]]:
    """Store the batch's usable replies in ``existing``, saving the raw file
    as it goes, and charge every reply to ``usage`` at the batch price (a
    reply that cannot be used is paid for too).  Returns the keys of the
    items delivered and counts: ``entries``, ``ok``, ``unusable`` (reply
    fails validation), ``unknown`` (no current instruction has its id) and
    one per result type that is not ``succeeded``."""
    by_id = {batch_custom_id(it): it for it in corpus_items}
    delivered: Set[str] = set()
    counts: Counter = Counter()
    async for entry in await client.messages.batches.results(batch_id):
        counts["entries"] += 1
        if entry.result.type != "succeeded":
            counts[entry.result.type] += 1
            logger.warning(f"{entry.custom_id}: request {entry.result.type}")
            continue
        message = entry.result.message
        if usage is not None:
            usage.charge(model + BATCH_SUFFIX, *extract_usage_anthropic(message))
        item = by_id.get(entry.custom_id)
        if item is None:
            counts["unknown"] += 1
            logger.warning(
                f"{entry.custom_id}: no current instruction has this id (changed or "
                f"removed since the batch was submitted); reply not stored"
            )
            continue
        try:
            classification = classification_from_message(message, item.key)
        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            counts["unusable"] += 1
            logger.warning(f"{item.key}: batch reply cannot be used ({e})")
            continue
        store_result(existing, item, classification, model, batch_id=batch_id)
        delivered.add(item.key)
        counts["ok"] += 1
        if counts["ok"] % save_every == 0:
            save_existing(raw_path, existing)
    save_existing(raw_path, existing)
    return delivered, dict(counts)


async def run_batch(
    client: Any,
    args: argparse.Namespace,
    output_dir: Path,
    raw_path: Path,
    to_classify: List[WorkItem],
    corpus_items: List[WorkItem],
    existing: Dict[str, Dict],
    usage: MultiModelUsage,
    estimate_usd: float,
) -> Optional[List[WorkItem]]:
    """Submit the batch (or take --batch-id), wait, collect.  Returns the
    items still to be classified in real time (those the batch did not
    deliver), or None after --batch-no-wait."""
    batch_id = args.batch_id
    charge = usage
    if batch_id:
        entry = find_batch(output_dir, batch_id)
        if entry is None:
            logger.warning(f"Batch {batch_id} is not in {batch_log_path(output_dir)}; "
                           f"taking it to be a batch of --model {args.model}")
            entry = {"id": batch_id, "model": args.model,
                     "note": "not submitted from this output directory"}
        else:
            if entry.get("model") != args.model:
                raise SystemExit(f"Batch {batch_id} was submitted with --model {entry.get('model')}; "
                                 f"collect it with the same model (records are stamped with it)")
            if entry.get("collected"):
                logger.warning(f"Batch {batch_id} was collected on {entry['collected']} and its usage "
                               f"recorded then; collecting again without charging it")
                charge = None
    else:
        requests = build_batch_requests(to_classify, args.model, args.temperature)
        logger.info(f"Submitting one Message Batch of {len(requests)} requests...")
        batch = await client.messages.batches.create(requests=requests)
        batch_id = batch.id
        entry = {
            "id": batch_id,
            "submitted": _utc_now(),
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": MAX_TOKENS,
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12],
            "n_requests": len(requests),
            "estimate_usd": round(estimate_usd, 2),
            "selection": {
                "names": args.names, "roles_only": args.roles_only, "traits_only": args.traits_only,
                "force": args.force, "allow_stale": args.allow_stale,
            },
        }
        record_batch(output_dir, entry)
        logger.info(f"Batch submitted: {batch_id} (recorded in {batch_log_path(output_dir)})")
        if args.batch_no_wait:
            logger.info(f"Collect it later with the same options and --batch-id {batch_id}")
            return None

    await wait_for_batch(client, batch_id, args.batch_poll)
    delivered, counts = await collect_batch(
        client, batch_id, corpus_items, existing, raw_path, model=args.model, usage=charge)
    logger.info(f"Batch {batch_id} collected: {counts}")
    record_batch(output_dir, dict(entry, collected=_utc_now(), counts=counts))
    warn_if_low_parse_rate(
        label=f"data_analysis/classify_goals:{args.model}{BATCH_SUFFIX}",
        n_ok=counts.get("ok", 0),
        n_total=counts.get("entries", 0),
        logger_obj=logger,
    )
    # what the batch did not deliver is classified at once, in real time
    return [it for it in to_classify if it.key not in delivered]


# =============================================================================
# Aggregation
# =============================================================================

def select_for_aggregation(
    existing: Dict[str, Dict],
    corpus_items: List[WorkItem],
    *,
    allow_stale: bool = False,
) -> Tuple[List[Dict], Dict[str, int]]:
    """The raw records the aggregate is built from: those of items in the
    current corpus that have a classification of the item's current text,
    and with ``allow_stale`` also of an older text (returned as copies marked
    ``stale_text``).  Records of stems or positions no longer in the corpus
    are left out; they stay in the raw file as history.  The counts say what
    was taken and what was left out, and why."""
    corpus = {it.key: it for it in corpus_items}
    selected = []
    counts: Counter = Counter()
    for key, record in existing.items():
        item = corpus.get(key)
        if item is None:
            counts["not_in_corpus"] += 1
            continue
        if record.get("classification") is None:
            counts["unclassified"] += 1
            continue
        if record.get("text") != item.text:
            if not allow_stale:
                counts["stale_text_left_out"] += 1
                continue
            record = dict(record, stale_text=True)
            counts["stale_text"] += 1
        selected.append(record)
        counts["aggregated"] += 1
    return selected, dict(counts)


def aggregate_results(
    raw_records: List[Dict],
) -> List[Dict]:
    """
    Aggregate per-instruction results into per-(name, source, polarity) records.
    """
    groups = defaultdict(list)
    for record in raw_records:
        key = (record["name"], record["source"], record["polarity"])
        groups[key].append(record)

    aggregated = []
    for (name, source, polarity), records in sorted(groups.items()):
        # Per-instruction details
        instructions = []
        for r in sorted(records, key=lambda x: x["index"]):
            detail = {
                "index": r["index"],
                "text": r["text"],
                "classification": r.get("classification"),
                "model": record_model(r),
            }
            if r.get("stale_text"):
                detail["stale_text"] = True
            instructions.append(detail)

        # Collect scores and goals across instructions
        all_goals = []
        scores = []

        for r in records:
            cls = r.get("classification")
            if cls is None:
                continue
            scores.append(cls.get("score", 0))
            for g in cls.get("goals", []):
                all_goals.append(g)

        score_counts = Counter(scores)

        # Aggregate score: median of individual scores (rounded)
        if scores:
            sorted_scores = sorted(scores)
            mid = len(sorted_scores) // 2
            if len(sorted_scores) % 2 == 0:
                median_score = round((sorted_scores[mid - 1] + sorted_scores[mid]) / 2)
            else:
                median_score = sorted_scores[mid]
            mean_score = sum(scores) / len(scores)
        else:
            median_score = 0
            mean_score = 0.0

        # Consistency: all instructions gave the same score
        consistent = len(set(scores)) <= 1

        # Deduplicate goals by description (simple exact match)
        seen_descriptions = set()
        unique_goals = []
        for g in all_goals:
            desc = g.get("description", "")
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                unique_goals.append(g)

        # Determine primary goal type
        goal_types = [g.get("goal_type") for g in unique_goals]
        if "terminal" in goal_types:
            primary_type = "terminal"
        elif "ambiguous" in goal_types:
            primary_type = "ambiguous"
        elif "instrumental" in goal_types:
            primary_type = "instrumental"
        else:
            primary_type = None

        aggregate = {
            "median_score": median_score,
            "mean_score": round(mean_score, 2),
            "score_counts": dict(score_counts),
            "consistent": consistent,
            "primary_goal_type": primary_type,
            "goals": unique_goals,
        }
        n_stale = sum(1 for r in records if r.get("stale_text"))
        if n_stale:
            aggregate["n_stale_text"] = n_stale

        aggregated.append({
            "name": name,
            "source": source,
            "polarity": polarity,
            "instructions": instructions,
            "aggregate": aggregate,
        })

    return aggregated


# =============================================================================
# I/O helpers
# =============================================================================

def resolve_output_dir(output_dir: str) -> Path:
    """An absolute --output-dir is taken as given (a scratch directory); a
    relative one is resolved against the repo root."""
    p = Path(output_dir)
    return p if p.is_absolute() else REPO_ROOT / p


def load_existing_raw(raw_path: Path) -> Dict[str, Dict]:
    """Load existing raw results, keyed by (name, source, polarity, index).
    A file that exists but cannot be read stops the run: carrying on with no
    records would overwrite it at the first save."""
    existing = {}
    if raw_path.exists():
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                existing[record_key(r)] = r
        except Exception as e:
            raise SystemExit(f"Could not load existing raw results from {raw_path}: {e}")
    return existing


def save_raw(raw_path: Path, records: List[Dict]):
    """Save raw results (atomically: a crash never leaves half a file)."""
    atomic_write_text(json.dumps(records, indent=2), raw_path)


def save_existing(raw_path: Path, existing: Dict[str, Dict]) -> None:
    """Save every raw record, sorted, including those of stems no longer in
    the corpus (history)."""
    save_raw(raw_path, sorted(existing.values(), key=lambda r: (
        r["name"], r["source"], r["polarity"], r["index"]
    )))


def save_aggregated(agg_path: Path, records: List[Dict]):
    """Save aggregated results."""
    atomic_write_text(json.dumps(records, indent=2), agg_path)


# =============================================================================
# Main
# =============================================================================

def log_cache_report(plan: Dict[str, List[WorkItem]], n_calls: int, args: argparse.Namespace,
                     estimate_usd: float) -> None:
    n_items = sum(len(v) for v in plan.values())
    n_text, n_model = len(plan[CACHE_STALE_TEXT]), len(plan[CACHE_STALE_MODEL])
    if args.force:
        how = "--force: every item"
    elif args.allow_stale:
        how = "--allow-stale: records of an older text are kept"
    else:
        how = "records of an older text are classified again (--allow-stale keeps them)"
    batch = bool(args.batch or args.batch_id)
    mode = "one Message Batch" if batch else "real time"
    logger.info(f"Cache against --model {args.model}:")
    logger.info(f"  items:            {n_items}")
    logger.info(f"  cached and valid: {len(plan[CACHE_VALID])}")
    logger.info(f"  stale:            {n_text + n_model} (text differs: {n_text}, model differs: {n_model})")
    logger.info(f"  missing:          {len(plan[CACHE_MISSING])}")
    logger.info(f"  calls:            {n_calls} ({how})")
    logger.info(
        f"  estimate:         ${estimate_usd:.2f} ({mode}; {MEAN_INPUT_TOKENS_PER_CALL} in + "
        f"{MEAN_OUTPUT_TOKENS_PER_CALL} out tokens per call at {args.model}"
        f"{BATCH_SUFFIX if batch else ''} prices, retries not counted)"
    )


def log_aggregation_report(counts: Dict[str, int], selected: List[Dict], prefix: str) -> None:
    logger.info(
        f"{prefix} {counts.get('aggregated', 0)} records "
        f"({counts.get('stale_text', 0)} of an older text, --allow-stale); left out: "
        f"{counts.get('not_in_corpus', 0)} of stems or positions no longer in the corpus "
        f"(kept in the raw file), {counts.get('stale_text_left_out', 0)} of an older text, "
        f"{counts.get('unclassified', 0)} without a classification"
    )
    models = Counter(record_model(r) for r in selected)
    if len(models) > 1:
        logger.warning(f"The aggregate mixes classifier models: {dict(models)}")


async def main_async(args: argparse.Namespace) -> None:
    output_dir = resolve_output_dir(args.output_dir)
    raw_path = output_dir / RAW_NAME
    agg_path = output_dir / AGG_NAME
    usage_path = output_dir / USAGE_NAME

    # Determine source filter
    source_filter = None
    if args.roles_only:
        source_filter = "role"
    elif args.traits_only:
        source_filter = "trait"

    # Load work items
    items = load_work_items(
        ROLES_DIR, TRAITS_DIR,
        source_filter=source_filter,
        name_filter=args.names,
    )
    logger.info(f"Loaded {len(items)} work items")
    if args.names:
        unmatched = sorted(set(args.names) - {it.name for it in items})
        if unmatched:
            logger.warning(f"--names matched no instruction file: {unmatched}")

    # Count breakdown
    role_items = [i for i in items if i.source == "role"]
    trait_pos = [i for i in items if i.source == "trait" and i.polarity == "pos"]
    trait_neg = [i for i in items if i.source == "trait" and i.polarity == "neg"]
    logger.info(
        f"  Roles: {len(role_items)} items "
        f"({len(set(i.name for i in role_items))} roles)"
    )
    logger.info(
        f"  Traits pos: {len(trait_pos)} items "
        f"({len(set(i.name for i in trait_pos))} traits)"
    )
    logger.info(
        f"  Traits neg: {len(trait_neg)} items "
        f"({len(set(i.name for i in trait_neg))} traits)"
    )

    # The whole corpus, whatever the selection: the aggregate covers it, and
    # batch replies are matched against it
    corpus_items = load_work_items(ROLES_DIR, TRAITS_DIR)

    existing = load_existing_raw(raw_path)
    logger.info(f"Found {len(existing)} existing raw records in {raw_path}")
    plan = plan_cache(items, existing, args.model)
    to_classify = items_to_classify(items, existing, args.model,
                                    force=args.force, allow_stale=args.allow_stale)
    estimate_usd = estimate_cost_usd(len(to_classify), args.model,
                                     batch=bool(args.batch or args.batch_id))
    log_cache_report(plan, len(to_classify), args, estimate_usd)

    if args.dry_run:
        logger.info("\n" + "=" * 60)
        logger.info("DRY RUN — no API calls will be made, no files written")
        logger.info("=" * 60)

        # Show sample prompts
        for i, sample in enumerate(items[:2]):
            logger.info(f"\n--- Sample prompt {i + 1} ---")
            logger.info(f"Model: {args.model}")
            logger.info(f"\n[SYSTEM]\n{SYSTEM_PROMPT[:500]}...")
            logger.info(f"\n[USER]\n{build_user_message(sample)}")

        if args.batch_id:
            logger.info(f"Would collect batch {args.batch_id}")
        selected, counts = select_for_aggregation(existing, corpus_items, allow_stale=args.allow_stale)
        log_aggregation_report(counts, selected, "As the raw file stands, the aggregate would take")
        return

    if not args.batch_id and to_classify:
        refusal = cost_gate_refusal(estimate_usd, confirm_expensive=args.confirm_expensive,
                                    budget_usd=args.budget_usd)
        if refusal:
            raise SystemExit(refusal)

    usage = MultiModelUsage()
    left_by_budget = 0
    if to_classify or args.batch_id:
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.error(
                "ANTHROPIC_API_KEY not found. Set it in .env or environment."
            )
            sys.exit(1)
        client = anthropic.AsyncAnthropic()
        try:
            if args.batch or args.batch_id:
                redo = await run_batch(client, args, output_dir, raw_path, to_classify,
                                       corpus_items, existing, usage, estimate_usd)
                if redo is None:
                    return
                if redo:
                    redo_estimate = estimate_cost_usd(len(redo), args.model)
                    logger.info(f"{len(redo)} items not delivered by the batch; classifying them "
                                f"in real time (estimate ${redo_estimate:.2f})")
                    refusal = cost_gate_refusal(
                        redo_estimate, confirm_expensive=args.confirm_expensive,
                        budget_usd=args.budget_usd, spent_usd=usage.total_cost_usd)
                    if refusal:
                        # the batch's replies are saved; the next run takes these up as missing
                        logger.error(f"Not classifying them now: {refusal}")
                        redo = []
            else:
                redo = to_classify
            if redo:
                left_by_budget = await classify_real_time(
                    client, redo, existing, raw_path,
                    model=args.model, temperature=args.temperature,
                    max_concurrent=args.max_concurrent,
                    requests_per_second=args.requests_per_second,
                    usage=usage, budget_usd=args.budget_usd,
                )
        finally:
            persist_usage(usage, usage_path)
    else:
        logger.info("Nothing to classify. Running aggregation only.")

    # Always re-run aggregation from the full raw file, over the current corpus
    selected, counts = select_for_aggregation(existing, corpus_items, allow_stale=args.allow_stale)
    aggregated = aggregate_results(selected)
    save_aggregated(agg_path, aggregated)
    logger.info(f"Saved {len(aggregated)} aggregated results to {agg_path}")
    log_aggregation_report(counts, selected, "Aggregated")

    # Print summary
    median_counts = Counter(a["aggregate"]["median_score"] for a in aggregated)
    consistent_count = sum(1 for a in aggregated if a["aggregate"]["consistent"])

    logger.info("\n" + "=" * 40)
    logger.info("SCORE SUMMARY (median across 5 instructions)")
    logger.info("=" * 40)
    for score in sorted(median_counts):
        logger.info(f"  score {score}: {median_counts[score]}")

    logger.info(f"\nConsistent (all 5 same score): {consistent_count}/{len(aggregated)}")

    inconsistent = [
        a for a in aggregated
        if not a["aggregate"]["consistent"]
    ]
    if inconsistent:
        logger.info(
            f"\n{len(inconsistent)} items with score disagreement:"
        )
        for a in inconsistent[:10]:
            logger.info(
                f"  {a['name']} ({a['source']}/{a['polarity']}): "
                f"scores={a['aggregate']['score_counts']}"
            )

    if left_by_budget:
        # exit code 2 = budget cap reached (as BudgetTracker's callers use it)
        raise SystemExit(2)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify role/trait instructions by goal content"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report the cache (items, valid, stale, missing), the calls and their estimate, "
             "and sample prompts, without API calls or file writes",
    )
    parser.add_argument(
        "--roles-only", action="store_true",
        help="Process only roles",
    )
    parser.add_argument(
        "--traits-only", action="store_true",
        help="Process only traits",
    )
    parser.add_argument(
        "--names", nargs="+",
        help="Process only specific roles/traits by name",
    )
    parser.add_argument(
        "--model", type=str, default=DEFAULT_MODEL,
        help=f"Anthropic model to use (default: {DEFAULT_MODEL}).  A cached record is reused only "
             f"if it was classified by this model (records without a model: {LEGACY_RECORD_MODEL})",
    )
    parser.add_argument(
        "--max-concurrent", type=int, default=20,
        help="Maximum concurrent API calls (default: 20)",
    )
    parser.add_argument(
        "--requests-per-second", type=int, default=10,
        help="Rate limit in requests per second (default: 10)",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.0,
        help="Sampling temperature (default: 0.0 for deterministic)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory, relative to the repo root unless absolute (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-classify all loaded work items even if they already have "
            "valid results in goal_classifications_raw.json (skips cache)"
        ),
    )
    parser.add_argument(
        "--allow-stale", action="store_true",
        help="Reuse a cached record whose text differs from the current instruction (a deliberate "
             "'new items only' run); the aggregate marks those instructions stale_text.  A record "
             "of another model is still classified again",
    )
    parser.add_argument(
        "--batch", action="store_true",
        help="Submit the run as one Message Batch: half the price, results usually within the hour and "
             "at most a day later.  For runs over about $20, case by case; real time is the default "
             "because turnaround matters more on small runs.  What the batch fails to deliver is "
             "classified in real time.",
    )
    parser.add_argument(
        "--batch-id", default=None, metavar="ID",
        help="Collect the results of a batch submitted earlier, instead of submitting one "
             "(pass the options the batch was submitted with)",
    )
    parser.add_argument(
        "--batch-no-wait", action="store_true",
        help="With --batch: submit and exit; collect later with --batch-id",
    )
    parser.add_argument(
        "--batch-poll", type=float, default=DEFAULT_BATCH_POLL_SECONDS, metavar="SECONDS",
        help=f"Seconds between looks at a batch that is running (default: {DEFAULT_BATCH_POLL_SECONDS})",
    )
    parser.add_argument(
        "--confirm-expensive", action="store_true",
        help=f"Allow a run estimated over ${EXPENSIVE_LINE_USD:.0f} (the expensive-operations rule: "
             f"quote the parameters to Roger and wait for his go first)",
    )
    parser.add_argument(
        "--budget-usd", type=float, default=None, metavar="USD",
        help="Hard cap on this run's spend: an estimate above it is refused, and real-time "
             "classification stops once it is reached (exit code 2)",
    )
    args = parser.parse_args(argv)
    if args.batch_no_wait and not args.batch:
        parser.error("--batch-no-wait needs --batch")
    if args.batch_id and not BATCH_ID_PATTERN.match(args.batch_id):
        parser.error(f"--batch-id {args.batch_id!r} is not a batch id")
    return args


def main(argv: Optional[List[str]] = None) -> None:
    asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    main()
