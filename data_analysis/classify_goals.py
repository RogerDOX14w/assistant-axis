#!/usr/bin/env python3
"""
Classify role and trait instructions by goal content.

Sends each individual instruction to an LLM classifier (Claude) to determine
whether it implies goals, how directly those goals are stated, and whether
they are terminal, instrumental, or ambiguous. Results are aggregated per
role/trait and assigned a phase1_disposition for experimental design.

Usage:
    uv run data_analysis/classify_goals.py --dry-run
    uv run data_analysis/classify_goals.py --names pirate utilitarian witty callous
    uv run data_analysis/classify_goals.py --roles-only
    uv run data_analysis/classify_goals.py  # full corpus
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress verbose HTTP logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)


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
    "reasoning": "string — step-by-step analysis before committing to classification",
    "has_goal": "boolean",
    "directness": "integer 1-3 or null if has_goal is false",
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

SYSTEM_PROMPT = """\
You are a precise classifier for AI research. Your task is to analyze \
a single instruction (a system prompt that would be given to a language model) \
and determine whether it implies any goals, purposes, values, or desired \
outcomes for the being it describes.

## Definitions

- A **goal** is a purpose, motivation, value, desired outcome, or end that \
the described being pursues or cares about. Terminal values and commitments \
(things valued for their own sake) count as goals — specifically, terminal goals.
- **Communication styles** and **analytical approaches** are NOT goals. \
An instruction that only describes HOW to communicate (e.g. "be witty", \
"use formal language") or WHAT analytical method to use (e.g. "think \
holistically", "break things into components") does not contain a goal \
unless it also indicates WHY or WHAT FOR.
- **Dispositions and emotional tones** are NOT goals. Instructions about \
temperament (e.g. "be cheerful", "be reserved", "be enthusiastic") describe \
what the being IS LIKE, not what it is TRYING TO ACHIEVE. \
A disposition is only a goal if the instruction indicates the being is \
actively pursuing that disposition as a purpose. Note however that some \
dispositions DO imply goals indirectly — e.g. "show compassion" implies \
caring about others' wellbeing, "be callous" implies a narrow moral circle. \
These should be classified as has_goal with low directness (1-2), not as \
goal-free.
- **Quality-of-output phrasing** is NOT a goal. Phrases like "to make your \
responses engaging" or "to make your answers memorable" describe the intended \
quality of communication, not a goal the being pursues. These are still \
style directives.

## Classification Steps

Think step-by-step in the "reasoning" field before filling in the other fields:

1. Read the instruction carefully.
2. Ask: does this instruction suggest any goal, purpose, value, or desired \
outcome beyond describing a communication style or analytical approach? \
If a reasonable person reading this instruction would NOT spontaneously \
identify a goal the being is pursuing, answer has_goal: false.
3. If has_goal is true, rate **directness** on a 1-3 scale:
   - 1: The goal is only weakly or indirectly implied
   - 2: The goal is strongly implied but not directly stated
   - 3: The goal is directly and clearly stated
4. List each distinct goal with:
   - **description**: a brief description
   - **goal_type**: one of:
     - "terminal" — the goal is clearly an end in itself
     - "instrumental" — the goal is clearly a means to some further end
     - "ambiguous" — the instruction does not specify whether the goal is \
an end in itself or a means to something else

## Response Format

Respond with ONLY a JSON object (no markdown fences, no extra text). \
The "reasoning" field MUST come first and contain your step-by-step thinking \
BEFORE you commit to the classification values.

{
    "reasoning": "your step-by-step analysis here",
    "has_goal": true or false,
    "directness": 1-3 or null,
    "goals": []
}

If has_goal is false, set directness to null and goals to an empty list.
If has_goal is true, directness must be 1, 2, or 3, and goals must be non-empty."""


def build_user_message(item: WorkItem) -> str:
    """Build the user message for classification."""
    return (
        f"Classify the following instruction for goal content.\n\n"
        f"Context: This is a {item.source} instruction "
        f"({item.polarity} variant, instruction {item.index + 1} of 5).\n\n"
        f"Instruction:\n\"{item.text}\""
    )


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
# API caller
# =============================================================================

async def classify_single(
    client: Any,
    item: WorkItem,
    model: str,
    rate_limiter: RateLimiter,
    temperature: float = 0.0,
    max_retries: int = 2,
) -> Optional[Dict]:
    """Classify a single instruction via the Anthropic API."""
    import anthropic

    user_msg = build_user_message(item)

    for attempt in range(max_retries + 1):
        await rate_limiter.acquire()

        try:
            if attempt == 0:
                messages = [{"role": "user", "content": user_msg}]
            else:
                # Retry: nudge for valid JSON
                messages = [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": '{"reasoning":'},
                ]

            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                temperature=temperature,
                system=SYSTEM_PROMPT,
                messages=messages,
            )

            raw_text = response.content[0].text

            # If we prefilled, prepend the prefill
            if attempt > 0:
                raw_text = '{"reasoning":' + raw_text

            result = json.loads(raw_text)

            # Validate required fields
            if "has_goal" not in result:
                raise ValueError("Missing 'has_goal' field")
            if "reasoning" not in result:
                raise ValueError("Missing 'reasoning' field")

            # Normalize
            if not result["has_goal"]:
                result["directness"] = None
                result["goals"] = []
            else:
                if result.get("directness") not in (1, 2, 3):
                    raise ValueError(
                        f"Invalid directness: {result.get('directness')}"
                    )
                if not result.get("goals"):
                    raise ValueError("has_goal=true but goals is empty")

            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            if attempt < max_retries:
                logger.warning(
                    f"Retry {attempt + 1} for {item.name}/{item.source}/"
                    f"{item.polarity}/{item.index}: {e}"
                )
            else:
                logger.error(
                    f"Failed after {max_retries + 1} attempts for "
                    f"{item.name}/{item.source}/{item.polarity}/{item.index}: {e}"
                )
                return None
        except anthropic.APIError as e:
            logger.error(
                f"API error for {item.name}/{item.source}/{item.polarity}/"
                f"{item.index}: {e}"
            )
            return None


async def classify_batch(
    client: Any,
    items: List[WorkItem],
    model: str,
    rate_limiter: RateLimiter,
    temperature: float = 0.0,
    max_concurrent: int = 20,
) -> List[Optional[Dict]]:
    """Classify a batch of items concurrently."""
    results = []

    for i in range(0, len(items), max_concurrent):
        batch = items[i : i + max_concurrent]
        tasks = [
            classify_single(client, item, model, rate_limiter, temperature)
            for item in batch
        ]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Exception in batch: {result}")
                results.append(None)
            else:
                results.append(result)

    return results


# =============================================================================
# Aggregation
# =============================================================================

def aggregate_results(
    raw_records: List[Dict],
) -> List[Dict]:
    """
    Aggregate per-instruction results into per-(name, source, polarity) records.
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for record in raw_records:
        key = (record["name"], record["source"], record["polarity"])
        groups[key].append(record)

    aggregated = []
    for (name, source, polarity), records in sorted(groups.items()):
        # Per-instruction details
        instructions = []
        for r in sorted(records, key=lambda x: x["index"]):
            instructions.append({
                "index": r["index"],
                "text": r["text"],
                "classification": r.get("classification"),
            })

        # Bin each instruction into one of three categories:
        #   "goal_free"    — has_goal is false
        #   "goal_implied" — has_goal is true, directness 1 or 2
        #   "goal_stated"  — has_goal is true, directness 3
        all_goals = []
        bins = []  # one bin label per classified instruction

        for r in records:
            cls = r.get("classification")
            if cls is None:
                continue
            if not cls.get("has_goal"):
                bins.append("goal_free")
            else:
                d = cls.get("directness")
                bins.append("goal_stated" if d == 3 else "goal_implied")
                for g in cls.get("goals", []):
                    all_goals.append(g)

        # Majority vote across the three bins
        from collections import Counter
        bin_counts = Counter(bins)
        total_classified = len(bins)
        majority_needed = total_classified / 2

        # Pick the bin with the most votes; "mixed" if no majority
        if bin_counts:
            top_bin, top_count = bin_counts.most_common(1)[0]
            goal_category = top_bin if top_count > majority_needed else "mixed"
        else:
            goal_category = "goal_free"

        # Consistency: flag if ANY instruction is in a different bin
        # (disagreement within "goal_implied" on directness 1 vs 2 is fine)
        distinct_bins = set(bins)
        cross_category_consistent = len(distinct_bins) <= 1

        # Deduplicate goals by description (simple exact match)
        seen_descriptions = set()
        unique_goals = []
        for g in all_goals:
            desc = g.get("description", "")
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                unique_goals.append(g)

        # Determine primary goal type for disposition
        goal_types = [g.get("goal_type") for g in unique_goals]
        if "terminal" in goal_types:
            primary_type = "terminal"
        elif "ambiguous" in goal_types:
            primary_type = "ambiguous"
        elif "instrumental" in goal_types:
            primary_type = "instrumental"
        else:
            primary_type = None

        # Phase 1 disposition combines goal_category with goal_type
        if goal_category == "goal_free":
            disposition = "goal_free"
        elif goal_category == "mixed":
            disposition = "mixed"
        elif primary_type == "terminal":
            disposition = "goal_terminal"
        elif primary_type == "ambiguous":
            disposition = "goal_ambiguous"
        elif primary_type == "instrumental":
            disposition = "goal_instrumental"
        else:
            # goal_implied or goal_stated but no goals extracted (shouldn't happen)
            disposition = goal_category

        aggregated.append({
            "name": name,
            "source": source,
            "polarity": polarity,
            "instructions": instructions,
            "aggregate": {
                "goal_category": goal_category,
                "bin_counts": dict(bin_counts),
                "goals": unique_goals,
                "cross_category_consistent": cross_category_consistent,
                "phase1_disposition": disposition,
            },
        })

    return aggregated


# =============================================================================
# I/O helpers
# =============================================================================

def load_existing_raw(raw_path: Path) -> Dict[str, Dict]:
    """Load existing raw results, keyed by (name, source, polarity, index)."""
    existing = {}
    if raw_path.exists():
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            for r in records:
                key = f"{r['name']}/{r['source']}/{r['polarity']}/{r['index']}"
                existing[key] = r
        except Exception as e:
            logger.warning(f"Could not load existing raw results: {e}")
    return existing


def save_raw(raw_path: Path, records: List[Dict]):
    """Save raw results."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def save_aggregated(agg_path: Path, records: List[Dict]):
    """Save aggregated results."""
    agg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


# =============================================================================
# Main
# =============================================================================

async def main_async():
    parser = argparse.ArgumentParser(
        description="Classify role/trait instructions by goal content"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview item counts and sample prompts without API calls",
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
        "--model", type=str, default="claude-sonnet-4-20250514",
        help="Anthropic model to use (default: claude-sonnet-4-20250514)",
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
        "--output-dir", type=str, default="data_analysis/output",
        help="Output directory (default: data_analysis/output)",
    )
    args = parser.parse_args()

    # Resolve paths relative to repo root
    repo_root = Path(__file__).parent.parent
    roles_dir = repo_root / "data" / "roles" / "instructions"
    traits_dir = repo_root / "data" / "traits" / "instructions"
    output_dir = repo_root / args.output_dir
    raw_path = output_dir / "goal_classifications_raw.json"
    agg_path = output_dir / "goal_classifications.json"

    # Determine source filter
    source_filter = None
    if args.roles_only:
        source_filter = "role"
    elif args.traits_only:
        source_filter = "trait"

    # Load work items
    items = load_work_items(
        roles_dir, traits_dir,
        source_filter=source_filter,
        name_filter=args.names,
    )
    logger.info(f"Loaded {len(items)} work items")

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

    if args.dry_run:
        logger.info("\n" + "=" * 60)
        logger.info("DRY RUN — no API calls will be made")
        logger.info("=" * 60)

        # Show sample prompts
        for i, sample in enumerate(items[:2]):
            logger.info(f"\n--- Sample prompt {i + 1} ---")
            logger.info(f"Model: {args.model}")
            logger.info(f"\n[SYSTEM]\n{SYSTEM_PROMPT[:500]}...")
            logger.info(f"\n[USER]\n{build_user_message(sample)}")

        # Check for existing results
        existing = load_existing_raw(raw_path)
        already_done = 0
        for item in items:
            key = f"{item.name}/{item.source}/{item.polarity}/{item.index}"
            if key in existing:
                already_done += 1

        logger.info(f"\nAlready classified: {already_done}")
        logger.info(f"Remaining: {len(items) - already_done}")
        logger.info(f"Total API calls needed: {len(items) - already_done}")
        return

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error(
            "ANTHROPIC_API_KEY not found. Set it in .env or environment."
        )
        sys.exit(1)

    # Load existing results for incremental processing
    existing = load_existing_raw(raw_path)
    logger.info(f"Found {len(existing)} existing classifications")

    # Filter out already-classified items
    remaining = []
    for item in items:
        key = f"{item.name}/{item.source}/{item.polarity}/{item.index}"
        if key not in existing:
            remaining.append(item)

    logger.info(f"Need to classify {len(remaining)} items")

    if not remaining:
        logger.info("All items already classified. Running aggregation only.")
    else:
        # Initialize Anthropic client
        import anthropic
        client = anthropic.AsyncAnthropic()
        rate_limiter = RateLimiter(args.requests_per_second)

        # Classify
        logger.info(
            f"Classifying with {args.model} "
            f"(temp={args.temperature}, "
            f"max_concurrent={args.max_concurrent}, "
            f"rate={args.requests_per_second}/s)..."
        )
        results = await classify_batch(
            client, remaining, args.model, rate_limiter,
            args.temperature, args.max_concurrent,
        )

        # Merge with existing
        success = 0
        failed = 0
        for item, result in zip(remaining, results):
            key = f"{item.name}/{item.source}/{item.polarity}/{item.index}"
            record = {
                "name": item.name,
                "source": item.source,
                "polarity": item.polarity,
                "index": item.index,
                "text": item.text,
                "classification": result,
            }
            existing[key] = record
            if result is not None:
                success += 1
            else:
                failed += 1

        logger.info(f"Classification complete: {success} succeeded, {failed} failed")

        # Save raw results
        all_raw = sorted(existing.values(), key=lambda r: (
            r["name"], r["source"], r["polarity"], r["index"]
        ))
        save_raw(raw_path, all_raw)
        logger.info(f"Saved {len(all_raw)} raw results to {raw_path}")

    # Always re-run aggregation from full raw file
    all_raw = list(existing.values())
    aggregated = aggregate_results(all_raw)
    save_aggregated(agg_path, aggregated)
    logger.info(f"Saved {len(aggregated)} aggregated results to {agg_path}")

    # Print summary
    dispositions = {}
    categories = {}
    for a in aggregated:
        d = a["aggregate"]["phase1_disposition"]
        dispositions[d] = dispositions.get(d, 0) + 1
        c = a["aggregate"]["goal_category"]
        categories[c] = categories.get(c, 0) + 1

    logger.info("\n" + "=" * 40)
    logger.info("GOAL CATEGORY SUMMARY (majority vote)")
    logger.info("=" * 40)
    for c, count in sorted(categories.items()):
        logger.info(f"  {c}: {count}")

    logger.info("\n" + "=" * 40)
    logger.info("DISPOSITION SUMMARY")
    logger.info("=" * 40)
    for d, count in sorted(dispositions.items()):
        logger.info(f"  {d}: {count}")

    inconsistent = [
        a for a in aggregated
        if not a["aggregate"]["cross_category_consistent"]
    ]
    if inconsistent:
        logger.info(
            f"\n{len(inconsistent)} items with cross-category disagreement "
            f"(instructions fall in different bins):"
        )
        for a in inconsistent[:10]:
            logger.info(
                f"  {a['name']} ({a['source']}/{a['polarity']}): "
                f"bins={a['aggregate']['bin_counts']}"
            )


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
