#!/usr/bin/env python3
"""
Score role+trait combinations for incongruity.

For each combination, sends all index-matched instruction pairs (pos only)
in a single API call and gets a 0-3 incongruity score per pair.  A
combination with any pair at or above --rescore_threshold is scored again by
--rescore_model, whose scores replace the first ones (kept under
``sonnet_scores``).  Pipeline step 3 (``pipeline/3_judge.py``) drops the
prompt-variants scored 3 from combination judging.

Models (Roger, 2026-10-10): Sonnet 5.5 first, escalating to Opus 5.5.  Both
refuse ``temperature`` (sent only to a model that takes it) and think
adaptively, so a reply may carry a thinking block before the text.

Batch by default (Roger, 2026-10-10, as for pipeline step 3): the first
stage goes as one Message Batch, then the escalations as a second, at half
the real-time price; what a batch fails to deliver is scored in real time.
--no_batch scores in real time; --batch_id collects a batch submitted
earlier (they are logged in ``<output>_batches.json``).

A score is kept only while the texts it was given are unchanged
(``pairs_sha256``: the labels and instruction pairs shown) and it was made
by the current --model; anything else in the output is scored again, and
combinations outside the current top-N lists are dropped from it.  Usage is
recorded cumulatively in ``<output>_usage.json`` (AGENT_NOTES token-usage
rule).

Usage:
    uv run data_analysis/score_combinations.py --dry_run   # counts, cost estimate, sample prompt
    uv run data_analysis/score_combinations.py              # 30x30 + 30x30, batch
    uv run data_analysis/score_combinations.py --goal_count 2 --non_goal_count 2 --no_batch  # test
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.gapgen.llm import accepts_temperature  # noqa: E402
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from assistant_axis.judge_pricing import (  # noqa: E402
    BATCH_SUFFIX, MultiModelUsage, extract_usage_anthropic, price_for_model,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Rate limiter (same pattern as classify_goals.py)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def build_combinations(args) -> List[Dict]:
    """Build r_ and t_ combination work items, mirroring 1_generate.py."""
    goal_data = load_json(Path(args.goal_file))

    goal_roles = goal_data["roles"]["goal"]
    non_goal_roles = goal_data["roles"]["non_goal"]
    goal_traits = goal_data["traits"]["goal"]
    non_goal_traits = goal_data["traits"]["non_goal"]

    gc, ngc = args.goal_count, args.non_goal_count

    if gc > len(goal_roles) and gc > len(goal_traits):
        logger.error(
            f"--goal_count {gc} exceeds both roles.goal "
            f"({len(goal_roles)}) and traits.goal ({len(goal_traits)})"
        )
        sys.exit(1)
    if ngc > len(non_goal_roles) and ngc > len(non_goal_traits):
        logger.error(
            f"--non_goal_count {ngc} exceeds both roles.non_goal "
            f"({len(non_goal_roles)}) and traits.non_goal ({len(non_goal_traits)})"
        )
        sys.exit(1)

    use_goal_roles = goal_roles[: min(gc, len(goal_roles))]
    use_non_goal_roles = non_goal_roles[: min(ngc, len(non_goal_roles))]
    use_goal_traits = goal_traits[: min(gc, len(goal_traits))]
    use_non_goal_traits = non_goal_traits[: min(ngc, len(non_goal_traits))]

    roles_dir = Path(args.roles_dir)
    traits_dir = Path(args.traits_dir)
    combos: List[Dict] = []

    # r_ combos: goal role x non-goal trait (goal from role)
    for role_name in use_goal_roles:
        role_file = roles_dir / f"{role_name}.json"
        if not role_file.exists():
            logger.warning(f"Role file missing: {role_file}")
            continue
        role_data = load_json(role_file)
        for trait_name in use_non_goal_traits:
            trait_file = traits_dir / f"{trait_name}.json"
            if not trait_file.exists():
                logger.warning(f"Trait file missing: {trait_file}")
                continue
            trait_data = load_json(trait_file)
            combos.append(_make_combo(
                role_name, role_data, trait_name, trait_data, "role",
            ))

    # t_ combos: non-goal role x goal trait (goal from trait)
    for role_name in use_non_goal_roles:
        role_file = roles_dir / f"{role_name}.json"
        if not role_file.exists():
            logger.warning(f"Role file missing: {role_file}")
            continue
        role_data = load_json(role_file)
        for trait_name in use_goal_traits:
            trait_file = traits_dir / f"{trait_name}.json"
            if not trait_file.exists():
                logger.warning(f"Trait file missing: {trait_file}")
                continue
            trait_data = load_json(trait_file)
            combos.append(_make_combo(
                role_name, role_data, trait_name, trait_data, "trait",
            ))

    logger.info(
        f"Built {len(combos)} combinations "
        f"(r_: {sum(1 for c in combos if c['goal_source'] == 'role')}, "
        f"t_: {sum(1 for c in combos if c['goal_source'] == 'trait')})"
    )
    return combos


def _make_combo(
    role_name: str,
    role_data: dict,
    trait_name: str,
    trait_data: dict,
    goal_source: str,
) -> Dict:
    """Build a combo dict with index-matched pos instruction pairs."""
    role_insts = role_data.get("instruction", [])
    trait_insts = trait_data.get("instruction", [])
    n_pairs = min(len(role_insts), len(trait_insts))

    pairs = []
    for i in range(n_pairs):
        pairs.append({
            "role_instruction": role_insts[i].get("pos", ""),
            "trait_instruction": trait_insts[i].get("pos", ""),
        })

    from assistant_axis.entity_id import display_form_name, judge_form_of_label, judge_label

    prefix = "r" if goal_source == "role" else "t"
    combo = {
        "role": role_name,
        "trait": trait_name,
        # The names the scorer is shown (judge display form, RUBRIC_VERSION 2),
        # the trait's from the file just read.
        "role_label": judge_label(role_name, "roles"),
        "trait_label": judge_form_of_label(
            trait_data.get("positive_label") or display_form_name(trait_name)),
        "goal_source": goal_source,
        "output_name": f"{prefix}_{role_name}__{trait_name}",
        "pairs": pairs,
    }
    combo["pairs_sha256"] = pairs_sha256(combo)
    return combo


def pairs_sha256(combo: Dict) -> str:
    """Hash of what the scorer is shown for a combination: the two labels
    and the instruction pairs.  A stored score is reused only while it
    matches (a regenerated instruction or a relabel makes it stale)."""
    blob = json.dumps([combo["role_label"], combo["trait_label"], combo["pairs"]],
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

# Stamped into the output's metadata (AGENT_NOTES "When changing a judge
# rubric").  1 (May 2026, unstamped): names in the mechanical display form;
# 2 (2026-10-09, W19): names in the judge display form, rubric text unchanged.
RUBRIC_VERSION = 2

_RUBRIC = """\
Score each on a 0-3 scale:
0: Role and trait fit well together or are naturally complementary
1: Role and trait are orthogonal; the combination is plausible but not \
especially natural
2: The combination is a little unusual, but not beyond the bounds of \
plausibility, and could be roleplayed without difficulty
3: The combination is very incongruous, to the point where it would be \
hard to roleplay convincingly

Important calibration notes — these patterns are NOT incongruous:
- Conceptual tension between role identity and trait style does NOT make \
a combination hard to roleplay. A "calculating predator" with a "witty" \
trait is a classic charming villain (Hannibal Lecter). An "ascetic" with \
a "passionate" trait is a zealous monk. Tension makes characters \
interesting, not unplayable.
- Professional inappropriateness is NOT incongruity. A "psychologist" \
with a "manipulative" trait is a thriller villain. A "pilot" with a \
"lustful" trait is an unprofessional character. The model is roleplaying \
a character, not applying for a job — ethical violations are easy to play.
- Non-human entities with human traits are NOT incongruous. A "golem" \
with "greedy" or a "virus" with "introverted" is straightforward \
personification — models handle this effortlessly.

Score 3 should be reserved for combinations where the instructions give \
operationally contradictory behavioral requirements that cannot coexist \
in a single response — not merely philosophical tension."""

_EXAMPLES = """\

Examples (role + trait → score):

philosopher + serene → 0
{"reasoning": "A serene philosopher maintaining calm composure while \
contemplating existence is a classic archetype — the two reinforce each \
other naturally.", "score": 0}

librarian + hostile → 1
{"reasoning": "A hostile librarian is orthogonal — hostility has nothing \
to do with library science — but is a completely plausible character \
(the surly public servant).", "score": 1}

void + bombastic → 2
{"reasoning": "A void entity that barely comprehends physical reality \
speaking in grandiose, pompous language is unusual, but playable as a \
cosmic being loudly proclaiming the magnificence of emptiness.", "score": 2}

infant + rhetorical → 3
{"reasoning": "The infant role explicitly requires communicating through \
crying, cooing, and simple sounds without complex language or abstract \
thinking. The rhetorical trait requires constructing compelling arguments \
with persuasive techniques. You cannot build a persuasive argument out of \
baby sounds — the role removes the very capacity the trait demands.", \
"score": 3}

perfectionist + careless → 3
{"reasoning": "The perfectionist role requires meticulous attention to \
detail and carefully reviewing every aspect of the work. The careless \
trait says not to worry about double-checking facts, being precise, or \
paying attention to details. The output text is either thorough and \
precise or rushed and sloppy — it cannot be both simultaneously.", \
"score": 3}"""

SYSTEM_PROMPT_TEMPLATE = (
    "You are scoring role+trait combinations for incongruity. Each combination "
    "pairs a character role instruction with a personality trait instruction to "
    "form a combined system prompt for an LLM. You are assessing how well they "
    "fit together and whether the combination would be difficult to roleplay "
    "convincingly.\n\n"
    + _RUBRIC + "\n\n"
    "For each combination, provide brief reasoning (1-2 sentences), then your "
    "score.\n"
    + _EXAMPLES + "\n\n"
    "Respond with a JSON array of {N} {OBJECTS}, one per combination, in the "
    "same order as presented. Each object must have exactly two fields: "
    '"reasoning" (string) and "score" (integer 0-3).\n\n'
    "Respond with ONLY the JSON array, no other text."
)

SYSTEM_PROMPT_SINGULAR = (
    "You are scoring a role+trait combination for incongruity. The combination "
    "pairs a character role instruction with a personality trait instruction to "
    "form a combined system prompt for an LLM. You are assessing how well they "
    "fit together and whether the combination would be difficult to roleplay "
    "convincingly.\n\n"
    + _RUBRIC + "\n\n"
    "Provide brief reasoning (1-2 sentences), then your score.\n"
    + _EXAMPLES + "\n\n"
    "Respond with a JSON array containing exactly 1 object with two fields: "
    '"reasoning" (string) and "score" (integer 0-3).\n\n'
    "Respond with ONLY the JSON array, no other text."
)


def build_system_prompt(n: int) -> str:
    if n == 1:
        return SYSTEM_PROMPT_SINGULAR
    return SYSTEM_PROMPT_TEMPLATE.replace("{N}", str(n)).replace("{OBJECTS}", "objects")


def build_user_message(combo: Dict, batch_size: Optional[int] = None) -> str:
    """Build the user message for a single combo's instruction pairs.

    Display-form note (AGENT_NOTES "Judge prompts show the judge display
    form"): ``combo['role']`` and ``combo['trait']`` are stems (the corpus
    key); the scorer is shown the judge display form
    (``assistant_axis.entity_id.judge_label``: ``Role: devil's advocate``,
    ``Trait: careless (from HEXACO)``), carried in ``role_label`` /
    ``trait_label`` by ``_make_combo`` and resolved from the stems when a
    combo lacks them.  The output JSON keeps the stems (RUBRIC_VERSION 2;
    version 1 showed the mechanical ``_`` -> space form).
    """
    from assistant_axis.entity_id import judge_label

    pairs = combo["pairs"]
    if batch_size is not None:
        pairs = pairs[:batch_size]

    role_disp = combo.get("role_label") or judge_label(combo["role"], "roles")
    trait_disp = combo.get("trait_label") or judge_label(combo["trait"], "traits")
    n = len(pairs)
    if n == 1:
        header = (
            f"Score this role+trait instruction combination:\n\n"
            f"Role: {role_disp}\n"
            f"Trait: {trait_disp}\n"
        )
    else:
        header = (
            f"Score these {n} role+trait instruction combinations:\n\n"
            f"Role: {role_disp}\n"
            f"Trait: {trait_disp}\n"
        )

    items = []
    for i, pair in enumerate(pairs):
        items.append(
            f"{i + 1}. Role instruction: {pair['role_instruction']}\n"
            f"   Trait instruction: {pair['trait_instruction']}"
        )

    return header + "\n" + "\n\n".join(items)


# ---------------------------------------------------------------------------
# API call + parsing
# ---------------------------------------------------------------------------

RETRY_SUFFIX = ("\n\nYour previous response was not valid JSON. "
                "Please respond with ONLY a JSON array, no markdown fences.")
# Room for the answer (about 90 tokens a pair) and, for a model that thinks
# adaptively and cannot be told not to (Sonnet 5.5, Opus 5.5), its thinking.
MAX_TOKENS = 1024
MAX_TOKENS_THINKING = 4096


def request_params(combo: Dict, model: str, batch_size: Optional[int] = None,
                   attempt: int = 0) -> Dict[str, Any]:
    """The Messages API parameters of one scoring call, shared by the
    real-time path and the batches.  ``temperature`` (0, rising by 0.1 a
    retry) goes only to a model that accepts it."""
    pairs = combo["pairs"] if batch_size is None else combo["pairs"][:batch_size]
    params: Dict[str, Any] = {
        "model": model,
        "max_tokens": MAX_TOKENS if accepts_temperature(model) else MAX_TOKENS_THINKING,
        "system": build_system_prompt(len(pairs)),
        "messages": [{"role": "user", "content": build_user_message(combo, batch_size)
                      + (RETRY_SUFFIX if attempt > 0 else "")}],
    }
    if accepts_temperature(model):
        params["temperature"] = round(0.1 * attempt, 1)
    return params


def response_text(message: Any) -> str:
    """The text of a reply, thinking blocks skipped."""
    return "".join(getattr(b, "text", "") or "" for b in (getattr(message, "content", None) or [])
                   if getattr(b, "type", "text") == "text").strip()


def parse_scores(combo: Dict, raw_text: str, n: int) -> Dict:
    """The stored record for a reply, or ValueError / JSONDecodeError /
    KeyError when it cannot be used."""
    stripped = re.sub(r"^```(?:json)?\s*\n?", "", raw_text)
    stripped = re.sub(r"\n?```\s*$", "", stripped)
    result = json.loads(stripped, strict=False)
    if not isinstance(result, list) or len(result) != n:
        raise ValueError(
            f"Expected array of {n}, got {type(result).__name__} "
            f"length {len(result) if isinstance(result, list) else '?'}"
        )
    per_pair = []
    for i, entry in enumerate(result):
        if "reasoning" not in entry or "score" not in entry:
            raise ValueError(f"Entry {i} missing reasoning/score")
        score = int(entry["score"])
        if score not in (0, 1, 2, 3):
            raise ValueError(f"Entry {i} score {score} not in 0-3")
        per_pair.append({"reasoning": entry["reasoning"], "score": score})
    scores = [p["score"] for p in per_pair]
    return {
        "role": combo["role"],
        "trait": combo["trait"],
        "goal_source": combo["goal_source"],
        "output_name": combo["output_name"],
        "pairs_sha256": combo.get("pairs_sha256") or pairs_sha256(combo),
        "per_pair": per_pair,
        "score_min": min(scores),
        "score_max": max(scores),
        "score_mean": sum(scores) / len(scores),
    }


def _n_pairs(combo: Dict, batch_size: Optional[int]) -> int:
    return len(combo["pairs"]) if batch_size is None else min(len(combo["pairs"]), batch_size)


async def _call_api(
    client: Any,
    combo: Dict,
    model: str,
    rate_limiter: RateLimiter,
    batch_size: Optional[int] = None,
    max_retries: int = 5,
    usage: Optional[MultiModelUsage] = None,
) -> Optional[Dict]:
    """Make a single scoring API call and parse the response, retrying an
    unusable reply.  Every reply received is charged to ``usage``.

    Returns a dict with per-pair reasoning/scores, or None on failure.
    """
    import anthropic

    n = _n_pairs(combo, batch_size)
    raw_text = "(no response)"
    for attempt in range(max_retries + 1):
        await rate_limiter.acquire()

        try:
            response = await client.messages.create(
                **request_params(combo, model, batch_size, attempt))
            if usage is not None:
                usage.charge(model, *extract_usage_anthropic(response))
            raw_text = response_text(response)
            if not raw_text:
                raise ValueError(f"Empty response (stop_reason={response.stop_reason})")
            if response.stop_reason != "end_turn":
                logger.warning(
                    f"{combo['output_name']} ({model}): "
                    f"stop_reason={response.stop_reason}"
                )
            return parse_scores(combo, raw_text, n)

        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            raw_preview = raw_text[:300]
            if attempt < max_retries:
                logger.warning(
                    f"Retry {attempt + 1} for {combo['output_name']}: {e}\n"
                    f"  raw response: {raw_preview}"
                )
            else:
                logger.error(
                    f"Failed after {max_retries + 1} attempts for "
                    f"{combo['output_name']}: {e}\n"
                    f"  raw response: {raw_preview}"
                )
                return None
        except anthropic.APIError as e:
            logger.error(f"API error for {combo['output_name']}: {e}")
            return None


def needs_rescore(record: Dict, rescore_model: Optional[str], threshold: int) -> bool:
    """A first-stage score that reaches the threshold and has not been
    escalated yet."""
    return bool(rescore_model) and "sonnet_scores" not in record and \
        max(p["score"] for p in record["per_pair"]) >= threshold


def escalated_record(first: Dict, samples: List[Dict], rescore_model: str,
                     escalation_log: Optional[Any]) -> Dict:
    """The record after a rescore: per pair, the median of the rescore
    samples' scores (the lower middle for an even count; with three, the
    majority vote when two agree, the middle value when all differ), with
    the reasoning of a sample that gave it; the first model's scores kept
    under ``sonnet_scores`` and every sample's under ``rescore_samples``
    (Roger, 2026-10-10: three samples of the rescore model, since Opus 5.5
    takes no temperature).  Logged to the escalation log."""
    n_pairs = len(first["per_pair"])
    per_pair = []
    for i in range(n_pairs):
        scores = [smp["per_pair"][i]["score"] for smp in samples]
        med = statistics.median_low(scores)
        reasoning = next(smp["per_pair"][i]["reasoning"] for smp in samples
                         if smp["per_pair"][i]["score"] == med)
        per_pair.append({"reasoning": reasoning, "score": med})
    scores = [p["score"] for p in per_pair]
    out = dict(samples[0], per_pair=per_pair, score_min=min(scores), score_max=max(scores),
               score_mean=sum(scores) / len(scores), scored_by=rescore_model,
               first_model=first.get("first_model"), sonnet_scores=first["per_pair"],
               rescore_samples=[[p["score"] for p in smp["per_pair"]] for smp in samples],
               rescore_aggregation="median_low")
    if escalation_log is not None:
        first_scores = [p["score"] for p in first["per_pair"]]
        escalation_log.write(json.dumps({
            "combo": first["output_name"],
            "role": first["role"],
            "trait": first["trait"],
            "first_model": first.get("first_model"),
            "rescore_model": rescore_model,
            "sonnet_per_pair": first["per_pair"],
            "rescore_samples": out["rescore_samples"],
            "opus_per_pair": per_pair,
            "sonnet_mean": round(sum(first_scores) / len(first_scores), 2),
            "opus_mean": round(out["score_mean"], 2),
        }) + "\n")
        escalation_log.flush()
    return out


async def rescore_samples(client: Any, combo: Dict, rescore_model: str, n: int,
                          rate_limiter: RateLimiter, batch_size: Optional[int],
                          usage: Optional[MultiModelUsage], max_retries: int = 5) -> List[Dict]:
    """``n`` real-time rescores of a combination; the usable ones."""
    out = []
    for _ in range(n):
        smp = await _call_api(client, combo, rescore_model, rate_limiter, batch_size,
                              max_retries, usage)
        if smp is not None:
            out.append(smp)
    return out


async def score_combo(
    client: Any,
    combo: Dict,
    model: str,
    rate_limiter: RateLimiter,
    batch_size: Optional[int] = None,
    max_retries: int = 5,
    rescore_model: Optional[str] = None,
    rescore_threshold: int = 2,
    escalation_log: Optional[Any] = None,
    usage: Optional[MultiModelUsage] = None,
    n_samples: int = 3,
) -> Optional[Dict]:
    """Score a combo, escalating to rescore_model (``n_samples`` times, the
    median kept) if any pair scores high."""
    result = await _call_api(client, combo, model, rate_limiter, batch_size, max_retries, usage)
    if result is None:
        return None
    result.update(scored_by=model, first_model=model)

    if needs_rescore(result, rescore_model, rescore_threshold):
        logger.info(f"Escalating {combo['output_name']} to {rescore_model} "
                    f"(first scores={[p['score'] for p in result['per_pair']]})")
        samples = await rescore_samples(client, combo, rescore_model, n_samples, rate_limiter,
                                        batch_size, usage, max_retries)
        if samples:
            return escalated_record(result, samples, rescore_model, escalation_log)
        logger.warning(f"Rescore failed for {combo['output_name']}, keeping the first result")

    return result


# ---------------------------------------------------------------------------
# Stored scores: which are still good
# ---------------------------------------------------------------------------

def split_existing(existing_scores: List[Dict], combos: List[Dict], model: str
                   ) -> tuple:
    """Divide the stored scores into those still good for the current
    combinations (same texts, same first-stage model) and the combinations
    to score.  Returns ``(kept, pending, counts)``; a score of a combination
    outside the current lists is dropped."""
    by_name = {c["output_name"]: c for c in combos}
    kept: List[Dict] = []
    counts = {"kept": 0, "stale_text": 0, "stale_model": 0, "dropped": 0}
    for rec in existing_scores:
        combo = by_name.get(rec.get("output_name"))
        if combo is None:
            counts["dropped"] += 1
        elif rec.get("pairs_sha256") != combo["pairs_sha256"]:
            counts["stale_text"] += 1
        elif rec.get("first_model", rec.get("scored_by")) != model:
            counts["stale_model"] += 1
        else:
            kept.append(rec)
            counts["kept"] += 1
    done = {r["output_name"] for r in kept}
    pending = [c for c in combos if c["output_name"] not in done]
    return kept, pending, counts


def _save_incremental(output_path: Path, metadata: Dict, scores: List[Dict]):
    """Save current state to disk (atomically)."""
    tmp = output_path.with_name(f".{output_path.name}.tmp{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump({"metadata": metadata, "scores": scores}, f, indent=2)
    os.replace(tmp, output_path)


class Recorder:
    """Saves the scores and the cumulative usage record as a run goes."""

    def __init__(self, output_path: Path, metadata: Dict, usage_path: Path):
        self.output_path, self.metadata, self.usage_path = output_path, metadata, usage_path
        self.prior = MultiModelUsage.load_or_create(usage_path)
        self.run = MultiModelUsage()
        if self.prior.n_calls:
            logger.info(self.prior.log_line("[usage] earlier runs"))

    def save(self, scores: List[Dict]) -> None:
        _save_incremental(self.output_path, self.metadata, scores)
        total = MultiModelUsage()
        total.merge_from(self.prior)
        total.merge_from(self.run)
        tmp = self.usage_path.with_name(f".{self.usage_path.name}.tmp{os.getpid()}")
        tmp.write_text(json.dumps(total.as_dict(), indent=2, sort_keys=True) + "\n")
        os.replace(tmp, self.usage_path)

    def log_totals(self) -> None:
        total = MultiModelUsage()
        total.merge_from(self.prior)
        total.merge_from(self.run)
        logger.info(self.run.log_line("[usage] this run"))
        logger.info(total.log_line(f"[usage] cumulative ({self.usage_path})"))


# ---------------------------------------------------------------------------
# Real time (--no_batch)
# ---------------------------------------------------------------------------

async def score_all(
    client: Any,
    pending: List[Dict],
    kept: List[Dict],
    combos_by_name: Dict[str, Dict],
    model: str,
    rate_limiter: RateLimiter,
    batch_size: Optional[int],
    max_concurrent: int,
    recorder: Recorder,
    escalation_log: Optional[Any],
    rescore_model: Optional[str] = None,
    rescore_threshold: int = 2,
    n_samples: int = 3,
) -> List[Dict]:
    """Score the pending combos with concurrency, saving incrementally, and
    escalate any stored first-stage score still owed a rescore."""
    all_scores = list(kept)
    n_call_ok = n_call_failed = 0
    if pending:
        logger.info(f"{len(pending)} to score in real time ({len(kept)} kept)")
    for i in range(0, len(pending), max_concurrent):
        chunk = pending[i: i + max_concurrent]
        results = await asyncio.gather(*[
            score_combo(client, c, model, rate_limiter, batch_size,
                        rescore_model=rescore_model, rescore_threshold=rescore_threshold,
                        escalation_log=escalation_log, usage=recorder.run, n_samples=n_samples)
            for c in chunk], return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Exception in batch: {result}")
                n_call_failed += 1
            elif result is None:
                n_call_failed += 1
            else:
                all_scores.append(result)
                n_call_ok += 1
        recorder.save(all_scores)
        logger.info(f"Progress: {len(all_scores)}/{len(combos_by_name)}")

    for idx, rec in enumerate(all_scores):
        if needs_rescore(rec, rescore_model, rescore_threshold):
            samples = await rescore_samples(client, combos_by_name[rec["output_name"]],
                                            rescore_model, n_samples, rate_limiter, batch_size,
                                            recorder.run)
            if samples:
                all_scores[idx] = escalated_record(rec, samples, rescore_model, escalation_log)
    recorder.save(all_scores)

    # ``n_call_failed`` counts post-retry failures, so anything non-zero is
    # persistent unparseable JSON or genuine API failure.
    warn_if_low_parse_rate(
        label=f"data_analysis/score_combinations:{model}",
        n_ok=n_call_ok,
        n_total=n_call_ok + n_call_failed,
        logger_obj=logger,
    )
    return all_scores


# ---------------------------------------------------------------------------
# Batch mode (the default)
# ---------------------------------------------------------------------------
#
# Two Message Batches: the first stage over every combination to score, then
# the rescore model over those that reached the threshold.  Each batch is
# logged in ``<output>_batches.json`` when submitted, so a run killed while
# waiting can collect it with --batch_id instead of paying again.  A result
# is matched to the combination whose current id it carries (the id hashes
# the texts and the model), so a reply is never stored against texts it did
# not score.  What a batch fails to deliver is scored in real time.

MAX_BATCH_REQUESTS = 100_000          # Message Batches limits
MAX_BATCH_BYTES = 256 * 1024 * 1024
STAGES = ("first", "rescore")


def batch_custom_id(combo: Dict, model: str, stage: str, sample: int = 0) -> str:
    """``<stage letter><sample>-<output name>-<hash of name, texts, model,
    sample>``; sample 0 carries no number (the form of the first batches)."""
    key = f"{combo['output_name']}\n{combo['pairs_sha256']}\n{model}" + (f"\n{sample}" if sample else "")
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    prefix = re.sub(r"[^A-Za-z0-9_-]", "_", combo["output_name"])[:40]
    return f"{stage[0]}{sample or ''}-{prefix}-{digest}"


def batch_log_path(output_path: Path) -> Path:
    return output_path.with_name(output_path.stem + "_batches.json")


def read_batch_log(output_path: Path) -> List[Dict]:
    path = batch_log_path(output_path)
    return json.loads(path.read_text()) if path.exists() else []


def record_batch(output_path: Path, entry: Dict) -> None:
    log = [e for e in read_batch_log(output_path) if e.get("id") != entry.get("id")] + [entry]
    path = batch_log_path(output_path)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    tmp.write_text(json.dumps(log, indent=2) + "\n")
    os.replace(tmp, path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def batch_stage(
    client: Any,
    combos: List[Dict],
    model: str,
    stage: str,
    *,
    output_path: Path,
    batch_size: Optional[int],
    poll_seconds: float,
    usage: MultiModelUsage,
    batch_id: Optional[str] = None,
    samples: int = 1,
) -> tuple:
    """Submit one Message Batch for ``combos`` with ``model``, ``samples``
    requests each (or collect ``batch_id``), wait, and parse the results.
    Returns ``(records, undelivered)``: the usable records by ``(output
    name, sample)``, and the ``(combo, sample)`` the batch did not deliver."""
    by_id = {batch_custom_id(c, model, stage, k): (c, k) for c in combos for k in range(samples)}
    entry = None
    if batch_id is None:
        requests = [{"custom_id": cid, "params": request_params(c, model, batch_size)}
                    for cid, (c, _k) in by_id.items()]
        if len(requests) > MAX_BATCH_REQUESTS:
            raise SystemExit(f"{len(requests)} requests: a Message Batch takes at most {MAX_BATCH_REQUESTS}")
        if len(json.dumps(requests).encode("utf-8")) > MAX_BATCH_BYTES:
            raise SystemExit("the requests exceed a Message Batch's 256 MB")
        logger.info(f"Submitting the {stage} stage: one Message Batch of {len(requests)} requests to {model}")
        batch = await client.messages.batches.create(requests=requests)
        batch_id = batch.id
        entry = {"id": batch_id, "stage": stage, "model": model, "n_requests": len(requests),
                 "submitted": _utc_now(), "rubric_version": RUBRIC_VERSION}
        record_batch(output_path, entry)
        logger.info(f"Batch submitted: {batch_id} (logged in {batch_log_path(output_path)}; "
                    f"if this run is stopped, collect it with --batch_id {batch_id})")
    else:
        entry = next((e for e in read_batch_log(output_path) if e.get("id") == batch_id),
                     {"id": batch_id, "stage": stage, "model": model})

    while True:
        batch = await client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        logger.info(f"batch {batch_id}: {batch.processing_status}; succeeded {c.succeeded}, "
                    f"errored {c.errored}, expired {c.expired}, processing {c.processing}")
        if batch.processing_status == "ended":
            break
        await asyncio.sleep(poll_seconds)

    records: Dict[str, Dict] = {}
    counts = {"entries": 0, "ok": 0, "unusable": 0, "unknown": 0, "not_succeeded": 0}
    async for item in await client.messages.batches.results(batch_id):
        counts["entries"] += 1
        if item.result.type != "succeeded":
            counts["not_succeeded"] += 1
            logger.warning(f"{item.custom_id}: request {item.result.type}")
            continue
        message = item.result.message
        usage.charge(model + BATCH_SUFFIX, *extract_usage_anthropic(message))
        combo, k = by_id.get(item.custom_id, (None, None))
        if combo is None:
            counts["unknown"] += 1
            logger.warning(f"{item.custom_id}: no current combination has this id "
                           f"(texts changed since submission); reply not stored")
            continue
        try:
            rec = parse_scores(combo, response_text(message), _n_pairs(combo, batch_size))
        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            counts["unusable"] += 1
            logger.warning(f"{combo['output_name']}: batch reply cannot be used ({e})")
            continue
        records[(combo["output_name"], k)] = rec
        counts["ok"] += 1
    record_batch(output_path, dict(entry, collected=_utc_now(), counts=counts))
    warn_if_low_parse_rate(label=f"data_analysis/score_combinations:{model}{BATCH_SUFFIX}",
                           n_ok=counts["ok"], n_total=counts["entries"], logger_obj=logger)
    undelivered = [(c, k) for c, k in by_id.values() if (c["output_name"], k) not in records]
    logger.info(f"Batch {batch_id} collected: {counts}; {len(undelivered)} to score in real time")
    return records, undelivered


async def score_in_batches(
    client: Any,
    args: argparse.Namespace,
    pending: List[Dict],
    kept: List[Dict],
    combos_by_name: Dict[str, Dict],
    rescore_model: Optional[str],
    rate_limiter: RateLimiter,
    recorder: Recorder,
    escalation_log: Optional[Any],
    output_path: Path,
) -> List[Dict]:
    scores: Dict[str, Dict] = {r["output_name"]: r for r in kept}
    given = None
    if args.batch_id:
        given = next((e for e in read_batch_log(output_path) if e.get("id") == args.batch_id), None)
        if given is None:
            logger.warning(f"--batch_id {args.batch_id} is not in {batch_log_path(output_path)}; "
                           f"taking it to be a first-stage batch of --model {args.model}")
            given = {"id": args.batch_id, "stage": "first", "model": args.model}

    # Stage 1: the first model over every combination to score.
    first_id = given["id"] if given and given.get("stage") == "first" else None
    if pending or first_id:
        records, undelivered = await batch_stage(
            client, pending, args.model, "first", output_path=output_path,
            batch_size=args.batch_size, poll_seconds=args.batch_poll_seconds,
            usage=recorder.run, batch_id=first_id)
        for (name, _k), rec in records.items():
            scores[name] = dict(rec, scored_by=args.model, first_model=args.model)
        recorder.save(list(scores.values()))
        for combo, _k in undelivered:
            rec = await _call_api(client, combo, args.model, rate_limiter, args.batch_size,
                                  usage=recorder.run)
            if rec is not None:
                scores[combo["output_name"]] = dict(rec, scored_by=args.model, first_model=args.model)
        recorder.save(list(scores.values()))

    # Stage 2: the rescore model, --rescore_samples times, over every
    # first-stage score at the threshold; the median per pair is kept.
    owed = [r for r in scores.values() if needs_rescore(r, rescore_model, args.rescore_threshold)]
    rescore_id = given["id"] if given and given.get("stage") == "rescore" else None
    if owed or rescore_id:
        n = args.rescore_samples
        logger.info(f"{len(owed)} combinations reach the rescore threshold "
                    f"({args.rescore_threshold}); escalating to {rescore_model}, {n} samples each")
        records, undelivered = await batch_stage(
            client, [combos_by_name[r["output_name"]] for r in owed], rescore_model, "rescore",
            output_path=output_path, batch_size=args.batch_size,
            poll_seconds=args.batch_poll_seconds, usage=recorder.run, batch_id=rescore_id,
            samples=n)
        for combo, k in undelivered:
            smp = await _call_api(client, combo, rescore_model, rate_limiter, args.batch_size,
                                  usage=recorder.run)
            if smp is not None:
                records[(combo["output_name"], k)] = smp
        for rec in owed:
            name = rec["output_name"]
            samples = [records[(name, k)] for k in range(n) if (name, k) in records]
            if not samples:
                logger.warning(f"Rescore failed for {name}, keeping the first result")
            elif needs_rescore(scores[name], rescore_model, args.rescore_threshold):
                if len(samples) < n:
                    logger.warning(f"{name}: {len(samples)} of {n} rescore samples usable")
                scores[name] = escalated_record(scores[name], samples, rescore_model, escalation_log)
        recorder.save(list(scores.values()))
    return list(scores.values())


def estimate_cost_usd(combos: List[Dict], model: str, rescore_model: Optional[str], *,
                      batch: bool, batch_size: Optional[int], rescore_fraction: float = 0.2,
                      rescore_samples: int = 3) -> float:
    """Rough cost of scoring ``combos``: prompt characters / 3 tokens (the
    5.x tokenizer's density), about 90 output tokens a pair, and a share of
    rescores (15% in April 2026; 20% assumed), ``rescore_samples`` each.
    Halved for a batch."""
    def one(model_: str) -> float:
        rate_in, rate_out = price_for_model(model_)
        total = 0.0
        for c in combos:
            p = request_params(c, model_, batch_size)
            tok_in = (len(p["system"]) + len(p["messages"][0]["content"])) / 3
            tok_out = 90 * _n_pairs(c, batch_size) + 30
            total += (tok_in * rate_in + tok_out * rate_out) / 1e6
        return total
    cost = one(model) + (rescore_fraction * rescore_samples * one(rescore_model)
                         if rescore_model else 0.0)
    return cost / 2 if batch else cost


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def compute_summary(scores: List[Dict]) -> Dict:
    """Compute summary statistics from scored results."""
    if not scores:
        return {"distribution": {}, "mean_score": 0, "worst": []}

    dist = {str(i): 0 for i in range(4)}
    all_means = []

    for s in scores:
        bucket = round(s["score_mean"])
        dist[str(bucket)] = dist.get(str(bucket), 0) + 1
        all_means.append(s["score_mean"])

    overall_mean = sum(all_means) / len(all_means) if all_means else 0

    worst = sorted(scores, key=lambda s: -s["score_max"])[:20]
    worst_items = [
        {
            "output_name": w["output_name"],
            "score_max": w["score_max"],
            "score_mean": round(w["score_mean"], 2),
            "reasoning_sample": w["per_pair"][0]["reasoning"] if w["per_pair"] else "",
        }
        for w in worst
    ]

    n_escalated = sum(1 for s in scores if "sonnet_scores" in s)

    return {
        "distribution": dist,
        "mean_score": round(overall_mean, 3),
        "escalated": n_escalated,
        "worst": worst_items,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main_async():
    parser = argparse.ArgumentParser(
        description="Score role+trait combinations for incongruity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--goal_count", type=int, default=30,
                        help="Top-N from each goal list (default: 30, as pipeline step 1)")
    parser.add_argument("--non_goal_count", type=int, default=30,
                        help="Top-N from each non-goal list (default: 30, as pipeline step 1)")
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"

    parser.add_argument("--goal_file", type=str,
                        default=str(data_dir / "goal_roles_and_traits.json"),
                        help="Goal roles/traits JSON")
    parser.add_argument("--roles_dir", type=str,
                        default=str(data_dir / "roles" / "instructions"),
                        help="Role instruction JSON directory")
    parser.add_argument("--traits_dir", type=str,
                        default=str(data_dir / "traits" / "instructions"),
                        help="Trait instruction JSON directory")
    parser.add_argument("--output", type=str,
                        default=str(data_dir / "combination_scores.json"),
                        help="Output JSON file (default: data/combination_scores.json)")
    parser.add_argument("--model", type=str,
                        default="claude-sonnet-5-5",
                        help="First-stage Anthropic model (default: claude-sonnet-5-5)")
    parser.add_argument("--rescore_model", type=str, default="claude-opus-5-5",
                        help="Model that rescores combinations reaching --rescore_threshold "
                             "(default: claude-opus-5-5)")
    parser.add_argument("--batch_size", type=int, default=None,
                        help="Instruction pairs per API call (default: all)")
    parser.add_argument("--max_concurrent", type=int, default=20,
                        help="Concurrent API calls in real time")
    parser.add_argument("--requests_per_second", type=int, default=10,
                        help="Rate limit in real time")
    parser.add_argument("--dry_run", action="store_true",
                        help="Counts, cost estimate and a sample prompt, without API calls")
    parser.add_argument("--no_rescore", action="store_true",
                        help="Disable the escalation of high-scoring combos")
    parser.add_argument("--rescore_threshold", type=int, default=2,
                        help="Min per-pair score to trigger a rescore (default: 2)")
    parser.add_argument("--rescore_samples", type=int, default=3,
                        help="Rescores per escalated combination; the median per pair is kept "
                             "(default 3: Opus 5.5 takes no temperature, so repeated samples "
                             "stand in for T=0; Roger, 2026-10-10)")
    parser.add_argument("--no_batch", action="store_true",
                        help="Score in real time instead of through Message Batches (batch is "
                             "the default: half the price, results usually within the hour)")
    parser.add_argument("--batch_id", type=str, default=None,
                        help="Collect this batch (logged in <output>_batches.json) instead of "
                             "submitting its stage again, then carry on")
    parser.add_argument("--batch_poll_seconds", type=float, default=60.0,
                        help="Seconds between status checks of a batch")
    parser.add_argument("--confirm_expensive", action="store_true",
                        help="Required when the estimate is over $20 (AGENT_NOTES "
                             "expensive-operations rule: quote the parameters to Roger first)")
    args = parser.parse_args()

    rescore_model = None if args.no_rescore else args.rescore_model
    batch = not args.no_batch

    combos = build_combinations(args)
    if not combos:
        logger.error("No combinations built")
        return
    combos_by_name = {c["output_name"]: c for c in combos}

    output_path = Path(args.output)
    existing_scores: List[Dict] = []
    if output_path.exists():
        try:
            existing_scores = load_json(output_path).get("scores", [])
        except Exception:
            logger.warning(f"Could not load {output_path}, starting fresh")
    kept, pending, counts = split_existing(existing_scores, combos, args.model)
    logger.info(f"Stored scores: {counts['kept']} kept; rescoring {counts['stale_text']} whose "
                f"texts changed and {counts['stale_model']} by another model; dropping "
                f"{counts['dropped']} outside the current lists.  To score: {len(pending)}")
    estimate = estimate_cost_usd(pending, args.model, rescore_model, batch=batch,
                                 batch_size=args.batch_size,
                                 rescore_samples=args.rescore_samples)
    logger.info(f"Estimate: ${estimate:.2f} ({'batch' if batch else 'real time'}; "
                f"{args.model}, rescoring at >= {args.rescore_threshold} with {rescore_model})")

    # --- Dry run ---
    if args.dry_run:
        logger.info(f"Dry run: {len(combos)} combinations")
        sample = combos[0]
        logger.info(f"\nSample system prompt:\n{'=' * 60}")
        logger.info(build_system_prompt(_n_pairs(sample, args.batch_size)))
        logger.info(f"\n{'=' * 60}\nSample user message:\n{'=' * 60}")
        logger.info(build_user_message(sample, args.batch_size))
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Model: {args.model}; request: "
                    f"{ {k: v for k, v in request_params(sample, args.model).items() if k in ('model', 'max_tokens', 'temperature')} }")
        return
    if estimate > 20 and not args.confirm_expensive:
        raise SystemExit(f"Estimate ${estimate:.2f} is over $20: quote the parameters to Roger, "
                         f"then rerun with --confirm_expensive")

    # --- Live ---
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not found")
        sys.exit(1)

    import anthropic
    client = anthropic.AsyncAnthropic()
    rate_limiter = RateLimiter(args.requests_per_second)

    metadata = {
        "model": args.model,
        "rubric_version": RUBRIC_VERSION,
        "rescore_model": rescore_model,
        "rescore_threshold": args.rescore_threshold if rescore_model else None,
        "rescore_samples": args.rescore_samples if rescore_model else None,
        "rescore_aggregation": "median_low" if rescore_model else None,
        "goal_count": args.goal_count,
        "non_goal_count": args.non_goal_count,
        "total_combinations": len(combos),
        "mode": "batch" if batch else "real time",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    recorder = Recorder(output_path, metadata,
                        output_path.with_name(output_path.stem + "_usage.json"))
    escalation_log_path = output_path.with_suffix(".escalations.jsonl")
    escalation_log = open(escalation_log_path, "a") if rescore_model else None
    try:
        if batch:
            all_scores = await score_in_batches(
                client, args, pending, kept, combos_by_name, rescore_model, rate_limiter,
                recorder, escalation_log, output_path)
        else:
            all_scores = await score_all(
                client, pending, kept, combos_by_name, args.model, rate_limiter,
                args.batch_size, args.max_concurrent, recorder, escalation_log,
                rescore_model=rescore_model, rescore_threshold=args.rescore_threshold,
                n_samples=args.rescore_samples)
    finally:
        if escalation_log is not None:
            escalation_log.close()

    order = {name: i for i, name in enumerate(combos_by_name)}
    all_scores.sort(key=lambda r: order.get(r["output_name"], len(order)))
    summary = compute_summary(all_scores)
    metadata["total_scored"] = len(all_scores)
    final = {"metadata": metadata, "scores": all_scores, "summary": summary}
    tmp = output_path.with_name(f".{output_path.name}.tmp{os.getpid()}")
    with open(tmp, "w") as f:
        json.dump(final, f, indent=2)
    os.replace(tmp, output_path)
    recorder.log_totals()

    logger.info(f"\nSaved {len(all_scores)} scores to {output_path}")
    logger.info(f"Distribution (by rounded mean): {summary['distribution']}")
    logger.info(f"Overall mean score: {summary['mean_score']}")
    if summary["escalated"]:
        logger.info(f"Escalated: {summary['escalated']}/{len(all_scores)}")
    missing = len(combos) - len(all_scores)
    if missing:
        logger.warning(f"{missing} combinations have no score (failed); a rerun scores them")
    if summary["worst"]:
        logger.info("Highest-scoring combinations:")
        for w in summary["worst"][:5]:
            logger.info(
                f"  {w['output_name']}: max={w['score_max']} "
                f"mean={w['score_mean']} — {w['reasoning_sample'][:80]}"
            )


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
