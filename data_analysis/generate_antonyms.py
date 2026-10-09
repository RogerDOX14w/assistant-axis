#!/usr/bin/env python3
"""Generate negative_labels for traits by analyzing pos/neg instruction pairs.

For each trait:
1. Feeds Claude the positive_label and pos instructions
2. Feeds the neg instructions
3. Asks for the best negative_label (single adjective/short phrase)
4. Asks for a 0-4 antonym rating (how well negative_label is an antonym of positive_label)

Outputs a JSON object: { trait: { negative_label, antonym_score, reasoning,
prompt_form, prompt_label } }, keyed by stem.  The prompt names the trait in
its judge display form (``careless (from HEXACO)``, ``systems-thinker``;
2026-10-09, W19; it showed the stem before), and ``prompt_form`` /
``prompt_label`` record the form and the exact string shown.
Uses known antonyms from steering_across_personas for 5 overlapping traits.

With ``--name-pos`` (2026-10-09, for working from a description to a label)
each trait also gets a second, label-blind call that sees only the five pos
instructions (no label, no definition) and names the pole they describe:
the result gains ``positive_name`` and ``positive_name_reasoning``.  The pos
instructions were written with the label in front of the generator, so the
name can still lean toward it; the blind call keeps the label out of the
namer's own prompt.

With ``--roles STEM ...`` (2026-10-09, the role-pair check of AGENT_NOTES
§ "Role pairs") the same check runs on roles, which have no negative_label
and no neg instructions: one call per role, given its display name, its
description and its five pos instructions, asks for the opposing *role* (a
role, not an adjective, and not necessarily one in the corpus) and a 0-4
rating of how cleanly it opposes.  Each result is ``{reasoning,
opposing_role, opposition_score, prompt_form, prompt_label}``; the usage record is
``data/roles/role_pair_check_usage.json``.  Run it from both sides: a role
pair is recorded only when each side names the other.

Usage:
    uv run python data_analysis/generate_antonyms.py
    uv run python data_analysis/generate_antonyms.py --traits obedient pragmatic conservative
    uv run python data_analysis/generate_antonyms.py --traits world_accepting world_changing --name-pos
    uv run python data_analysis/generate_antonyms.py --roles provincial cosmopolitan
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.entity_id import (  # noqa: E402
    JUDGE_LABEL_FORM, display_form_name, judge_form_of_label, judge_label,
)
from assistant_axis.judge import warn_if_low_parse_rate  # noqa: E402
from assistant_axis.judge_pricing import MultiModelUsage, extract_usage_anthropic  # noqa: E402

MODEL = "claude-sonnet-4-6"
# How the entity's name is written in the check's user message, returned with
# every result as ``prompt_form`` (with the exact string as ``prompt_label``)
# so that a runner can record it.  Until 2026-10-09 the trait check showed
# the stem (``positive_label: careless_hexaco``) and the role check
# role_display_name; since W19 both show the judge display form
# (``careless (from HEXACO)``, ``systems-thinker``).  Results without the
# field are from the earlier form.
PROMPT_FORM = JUDGE_LABEL_FORM
# Cumulative token-usage record (AGENT_NOTES "Token usage logging is
# mandatory on batched LLM call sites"); one level above instructions/.
DEFAULT_USAGE_JSON = Path(__file__).resolve().parent.parent / "data" / "traits" / "antonym_check_usage.json"
# The role-pair check (--roles) keeps its own cumulative record, beside the
# role corpus.
ROLES_DIR = Path(__file__).resolve().parent.parent / "data" / "roles" / "instructions"
DEFAULT_ROLE_USAGE_JSON = ROLES_DIR.parent / "role_pair_check_usage.json"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

load_dotenv()

import anthropic

KNOWN_ANTONYMS = {
    "assertive": "deferential",
    "confident": "uncertain",
    "deferential": "authoritative",
    "empathetic": "detached",
    "impulsive": "deliberate",
}

SYSTEM_PROMPT = """\
You are a psycholinguistics expert labeling personality trait poles for a research dataset.

You will be given:
- A positive_label (trait name)
- A definition of what that trait means
- 5 "pos" instruction prompts that induce that trait
- 5 "neg" instruction prompts that induce the OPPOSITE of that trait

Your task:
1. Read the neg instructions carefully to understand what opposite pole they describe.
2. Choose the best adjective (or short hyphenated phrase) that names that opposite pole. \
This should be the most natural, recognizable label for what the neg instructions describe. \
Prefer real adjectives over "un-X" forms when a good standalone word exists. \
If there are two or more genuinely competitive candidates where reasonable experts might \
disagree, list them separated by "|" (e.g. "pragmatic|realistic"). Use "|" freely — \
it is better to surface ambiguity than to hide it.
3. Rate how antonymic your chosen negative_label (or best candidate if you listed alternatives) \
is to the positive_label on this scale:
   0 = not antonyms at all (unrelated concepts)
   1 = weakly opposed (overlapping or tangential opposition)
   2 = moderately opposed (clearly different poles but not clean opposites)
   3 = strong antonyms (clearly opposite, minor asymmetry)
   4 = perfect antonyms (direct, symmetric opposites)

Return ONLY a JSON object with these fields (reasoning MUST come first):
{
  "reasoning": "Brief explanation of your choice and score",
  "negative_label": "chosen_label",
  "antonym_score": <0-4>
}
"""


POS_NAME_SYSTEM_PROMPT = """\
You are a psycholinguistics expert labeling personality trait poles for a research dataset.

You will be given 5 instruction prompts that each induce the same persona trait. You are \
not told the trait's name.

Your task:
1. Read the instructions carefully to understand the one trait they all describe.
2. Choose the best adjective (or short hyphenated phrase) that names that trait. \
This should be the most natural, recognizable label for what the instructions describe, \
as a person would be described by it. Prefer real adjectives over coined phrases when a good \
standalone word exists. If there are two or more genuinely competitive candidates where \
reasonable experts might disagree, list them separated by "|" (e.g. "pragmatic|realistic"). \
Use "|" freely: it is better to surface ambiguity than to hide it.

Return ONLY a JSON object with these fields (reasoning MUST come first):
{
  "reasoning": "Brief explanation of your choice",
  "positive_name": "chosen_label"
}
"""


def build_pos_name_message(instructions: list[dict]) -> str:
    """The label-blind naming prompt: the pos instructions and nothing else."""
    pos_lines = "\n".join(f"  {i+1}. {inst['pos']}" for i, inst in enumerate(instructions))
    return f"Instructions:\n{pos_lines}"


# The role-pair check (--roles).  Roles have no neg instructions, so the model
# reads the role itself and names its opposite; the answer is a role (a noun
# for who someone is), not an adjective.  The examples in the prompt are
# deliberately words that are no pole of a recorded role pair (not guardian,
# parasite, ...), so the check that validates those pairs is not primed.
ROLE_SYSTEM_PROMPT = """\
You are an expert on social roles, archetypes and characters, labeling the poles of role pairs for a \
research dataset.

You will be given:
- A role name
- A description of that role
- 5 instruction prompts that each make an AI persona take on that role

Your task:
1. Read the description and the instructions carefully to understand the role: who this person \
(or entity) is, what they do, and how they stand toward others and the world.
2. Name the role that most cleanly opposes it: the role at the other end of the same dimension. \
Give a role, that is, a noun naming who someone is (such as "landlord" or "sailor"), not an \
adjective, and not the mere absence of the role ("non-X"). You are not choosing from a list: name \
the best opposing role whether or not it is a common one. Prefer a real, recognizable role noun \
over a coined phrase when a good one exists. If there are two or more genuinely competitive \
candidates where reasonable experts might disagree, list them separated by "|" (e.g. \
"tenant|lodger"). Use "|" freely: it is better to surface ambiguity than to hide it.
3. Rate how cleanly your chosen opposing role (or the best candidate if you listed alternatives) \
opposes the given role on this scale:
   0 = not opposed at all (unrelated roles)
   1 = weakly opposed (overlapping or tangential opposition)
   2 = moderately opposed (clearly different roles but not clean opposites)
   3 = strongly opposed (clearly opposite, minor asymmetry)
   4 = perfectly opposed (direct, symmetric opposites)

Return ONLY a JSON object with these fields (reasoning MUST come first):
{
  "reasoning": "Brief explanation of your choice and score",
  "opposing_role": "chosen_role",
  "opposition_score": <0-4>
}
"""

ROLE_ERROR_RESULT = {"opposing_role": "ERROR", "opposition_score": -1, "reasoning": "All retries failed"}


def build_role_message(role_name: str, description: str, instructions: list[dict]) -> str:
    """The role-pair prompt: display name, description, the five pos instructions."""
    pos_lines = "\n".join(f"  {i+1}. {inst['pos']}" for i, inst in enumerate(instructions))
    return (
        f"Role: {role_name}\n"
        f"Description: {description}\n\n"
        f"Instructions:\n{pos_lines}"
    )


def _parse_reply(text: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    raw = re.sub(r"\n?```\s*$", "", raw)
    return json.loads(raw, strict=False)


async def name_pos_one(
    client: anthropic.AsyncAnthropic,
    instructions: list[dict],
    semaphore: asyncio.Semaphore,
    usage: MultiModelUsage | None = None,
    log_label: str = "",
) -> dict:
    """Name the pole the pos instructions describe, without seeing the label."""
    msg = build_pos_name_message(instructions)
    for attempt in range(5):
        async with semaphore:
            try:
                response = await client.messages.create(
                    model=MODEL, max_tokens=512, temperature=0,
                    system=POS_NAME_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": msg}],
                )
                if usage is not None:
                    usage.charge(MODEL, *extract_usage_anthropic(response))
                result = _parse_reply(response.content[0].text)
                if "positive_name" not in result:
                    raise KeyError("positive_name")
                return result
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"  Retry {attempt+1} for the pos name of {log_label}: {e}", file=sys.stderr)
                await asyncio.sleep(1)
    return {"positive_name": "ERROR", "reasoning": "All retries failed"}


async def classify_role_one(
    client: anthropic.AsyncAnthropic,
    role_name: str,
    description: str,
    instructions: list[dict],
    semaphore: asyncio.Semaphore,
    usage: MultiModelUsage | None = None,
) -> dict:
    """Name the role that opposes ``role_name`` and rate the opposition 0-4.
    Five attempts, as for traits; then the ERROR sentinel."""
    msg = build_role_message(role_name, description, instructions)
    for attempt in range(5):
        async with semaphore:
            try:
                response = await client.messages.create(
                    model=MODEL, max_tokens=512, temperature=0,
                    system=ROLE_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": msg}],
                )
                if usage is not None:
                    usage.charge(MODEL, *extract_usage_anthropic(response))
                result = _parse_reply(response.content[0].text)
                for key in ("opposing_role", "opposition_score"):
                    if key not in result:
                        raise KeyError(key)
                return result
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"  Retry {attempt+1} for the role {role_name}: {e}", file=sys.stderr)
                await asyncio.sleep(1)
    return dict(ROLE_ERROR_RESULT)


def trait_prompt_label(stem: str, doc: dict) -> str:
    """The name the trait check shows for a trait file: the judge display
    form of its label (``judge_label``'s trait rule, applied to the file read,
    which may be a staged copy).  Ad-hoc runners calling ``classify_one``
    should pass this."""
    return judge_form_of_label(doc.get("positive_label") or display_form_name(stem))


def load_role_tasks(stems: list[str], roles_dir: Path | None = None) -> list[tuple[str, str, str, list[dict]]]:
    """``(stem, judge display name, description, pos instructions)`` per
    role, in the order given.  Exits on a stem with no file or no
    instructions."""
    roles_dir = roles_dir if roles_dir is not None else ROLES_DIR
    missing = [s for s in stems if not (roles_dir / f"{s}.json").exists()]
    if missing:
        print(f"ERROR: role files not found: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    tasks = []
    for stem in dict.fromkeys(stems):
        with open(roles_dir / f"{stem}.json", encoding="utf-8") as f:
            data = json.load(f)
        instructions = data.get("instruction") or []
        if not instructions:
            print(f"ERROR: role {stem} has no instructions; generate them first", file=sys.stderr)
            sys.exit(1)
        tasks.append((stem, judge_label(stem, "roles", data_dir=Path(roles_dir).parent.parent),
                      data.get("description", ""), instructions))
    return tasks


async def main_roles_async(role_stems: list[str], usage_json: Path | None = None,
                           roles_dir: Path | None = None):
    """The role-pair check: one call per role, results printed as JSON keyed
    by stem."""
    tasks = load_role_tasks(role_stems, roles_dir)
    print(f"Processing {len(tasks)} roles", file=sys.stderr)
    usage = MultiModelUsage()
    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(10)

    async def run_one(stem, name, description, insts):
        result = await classify_role_one(client, name, description, insts, semaphore, usage)
        return stem, {**result, "prompt_form": PROMPT_FORM, "prompt_label": name}

    api_results = await asyncio.gather(*(run_one(*t) for t in tasks))

    warn_if_low_parse_rate(
        label=f"data_analysis/generate_antonyms:roles:{MODEL}",
        n_ok=sum(1 for _, r in api_results if r.get("opposing_role") != "ERROR"),
        n_total=len(api_results),
        logger_obj=logger,
    )
    logger.info(usage.log_line("[usage]"))
    path = Path(usage_json) if usage_json is not None else DEFAULT_ROLE_USAGE_JSON
    total = MultiModelUsage.load_or_create(path)
    total.merge_from(usage)
    total.write_json(path)
    logger.info(f"[usage] cumulative record: {path} (total ${total.total_cost_usd:.3f} over {total.n_calls} calls)")

    results = dict(sorted(api_results))
    scores = [r["opposition_score"] for r in results.values()
              if isinstance(r.get("opposition_score"), int) and r["opposition_score"] >= 0]
    print("\nOpposition score distribution:", file=sys.stderr)
    for s in range(5):
        print(f"  {s}: {scores.count(s)} roles", file=sys.stderr)
    under4 = [(k, v.get("opposition_score"), v.get("opposing_role")) for k, v in results.items()
              if isinstance(v.get("opposition_score"), int) and v["opposition_score"] < 4]
    if under4:
        print("\nRoles scoring under 4:", file=sys.stderr)
        for name, score, role in under4:
            print(f"  {name} -> {role} (score={score})", file=sys.stderr)

    print(json.dumps(results, indent=2, sort_keys=True))


def extract_definition(eval_prompt: str) -> str:
    """Extract the trait definition sentence from the eval_prompt."""
    first_para = eval_prompt.split("\n\n")[0]
    idx = first_para.find("**. ")
    if idx >= 0:
        return first_para[idx + 4:].strip()
    return ""


def build_user_message(
    positive_label: str, definition: str, instructions: list[dict]
) -> str:
    pos_lines = "\n".join(
        f"  {i+1}. {inst['pos']}" for i, inst in enumerate(instructions)
    )
    neg_lines = "\n".join(
        f"  {i+1}. {inst['neg']}" for i, inst in enumerate(instructions)
    )
    return (
        f"positive_label: {positive_label}\n"
        f"Definition: {definition}\n\n"
        f"Pos instructions:\n{pos_lines}\n\n"
        f"Neg instructions:\n{neg_lines}"
    )


async def classify_one(
    client: anthropic.AsyncAnthropic,
    positive_label: str,
    definition: str,
    instructions: list[dict],
    semaphore: asyncio.Semaphore,
    usage: MultiModelUsage | None = None,
) -> dict:
    msg = build_user_message(positive_label, definition, instructions)

    for attempt in range(5):
        async with semaphore:
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=512,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": msg}],
                )
                if usage is not None:
                    usage.charge(MODEL, *extract_usage_anthropic(response))
                raw = response.content[0].text.strip()
                raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
                raw = re.sub(r"\n?```\s*$", "", raw)
                result = json.loads(raw, strict=False)
                return result
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(
                    f"  Retry {attempt+1} for {positive_label}: {e}",
                    file=sys.stderr,
                )
                await asyncio.sleep(1)
    return {"negative_label": "ERROR", "antonym_score": -1, "reasoning": "All retries failed"}


async def main_async(trait_filter: list[str] | None = None, usage_json: Path | None = None,
                     name_pos: bool = False):
    traits_dir = Path(__file__).parent.parent / "data" / "traits" / "instructions"
    usage = MultiModelUsage()
    trait_files = sorted(traits_dir.glob("*.json"))

    if trait_filter:
        names = set(trait_filter)
        trait_files = [tf for tf in trait_files if tf.stem in names]
        missing = names - {tf.stem for tf in trait_files}
        if missing:
            print(f"ERROR: trait files not found: {', '.join(sorted(missing))}", file=sys.stderr)
            sys.exit(1)

    print(f"Processing {len(trait_files)} traits", file=sys.stderr)

    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(10)

    results = {}
    tasks = []

    for tf in trait_files:
        with open(tf, encoding="utf-8") as f:
            data = json.load(f)
        instructions = data["instruction"]
        definition = extract_definition(data.get("eval_prompt", ""))
        if not definition:
            definition = data.get("description", "")

        # Results are keyed by stem; the prompt shows the judge display form
        # (until 2026-10-09 it showed the stem itself).
        tasks.append((tf.stem, trait_prompt_label(tf.stem, data), definition, instructions))

    print(f"Calling API for all {len(tasks)} traits", file=sys.stderr)

    async def run_one(stem, label, defn, insts):
        result = await classify_one(client, label, defn, insts, semaphore, usage)
        result["prompt_form"] = PROMPT_FORM
        result["prompt_label"] = label
        if name_pos:
            named = await name_pos_one(client, insts, semaphore, usage, stem)
            result["positive_name"] = named.get("positive_name")
            result["positive_name_reasoning"] = named.get("reasoning")
        if stem in KNOWN_ANTONYMS:
            result["known_antonym"] = KNOWN_ANTONYMS[stem]
            match = result["negative_label"].lower() == KNOWN_ANTONYMS[stem].lower()
            result["matches_known"] = match
        return stem, result

    api_results = await asyncio.gather(
        *(run_one(stem, label, defn, insts) for stem, label, defn, insts in tasks)
    )

    for pos_label, result in api_results:
        results[pos_label] = result

    # Loud warning if parse rate this run dropped below 99%.  ``classify_one``
    # returns the ERROR sentinel after 5 failed JSON-decode retries, so this
    # post-retry rate should normally be 100% on Sonnet.
    n_call_total = len(api_results)
    n_call_ok = sum(
        1 for _, r in api_results if r.get("negative_label") != "ERROR"
    )
    warn_if_low_parse_rate(
        label=f"data_analysis/generate_antonyms:{MODEL}",
        n_ok=n_call_ok,
        n_total=n_call_total,
        logger_obj=logger,
    )
    if name_pos:
        warn_if_low_parse_rate(
            label=f"data_analysis/generate_antonyms:pos-name:{MODEL}",
            n_ok=sum(1 for _, r in api_results if r.get("positive_name") not in (None, "ERROR")),
            n_total=n_call_total,
            logger_obj=logger,
        )
    logger.info(usage.log_line("[usage]"))
    path = Path(usage_json) if usage_json is not None else DEFAULT_USAGE_JSON
    total = MultiModelUsage.load_or_create(path)
    total.merge_from(usage)
    total.write_json(path)
    logger.info(f"[usage] cumulative record: {path} (total ${total.total_cost_usd:.3f} over {total.n_calls} calls)")

    results = dict(sorted(results.items()))

    scores = [
        r["antonym_score"]
        for r in results.values()
        if r["antonym_score"] is not None and r["antonym_score"] >= 0
    ]
    print(f"\nAntonym score distribution:", file=sys.stderr)
    for s in range(5):
        count = scores.count(s)
        print(f"  {s}: {count} traits", file=sys.stderr)
    under4 = [
        (k, v["antonym_score"], v["negative_label"])
        for k, v in results.items()
        if v["antonym_score"] is not None and v["antonym_score"] < 4
    ]
    if under4:
        print(f"\nTraits scoring under 4:", file=sys.stderr)
        for name, score, label in under4:
            print(f"  {name} -> {label} (score={score})", file=sys.stderr)

    known_comparison = [
        (k, v) for k, v in results.items() if "known_antonym" in v
    ]
    if known_comparison:
        print(f"\nComparison with known antonyms:", file=sys.stderr)
        for name, v in known_comparison:
            match = "MATCH" if v["matches_known"] else "DIFFERS"
            print(
                f"  {name}: generated={v['negative_label']}, "
                f"known={v['known_antonym']} [{match}]",
                file=sys.stderr,
            )

    print(json.dumps(results, indent=2, sort_keys=True))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate negative_labels for traits via Claude, or (--roles) name the role "
                    "opposing each given role.",
    )
    which = parser.add_mutually_exclusive_group()
    which.add_argument(
        "--traits",
        nargs="+",
        metavar="TRAIT",
        help="Trait names to process (default: all traits)",
    )
    which.add_argument(
        "--roles",
        nargs="+",
        metavar="ROLE",
        help="Role stems to check instead of traits: each call names the opposing role and rates "
             "the opposition 0-4 (the role-pair check)",
    )
    parser.add_argument(
        "--usage-json",
        default=None,
        help=f"Cumulative token-usage record, merged into on every run (default: {DEFAULT_USAGE_JSON}; "
             f"with --roles, {DEFAULT_ROLE_USAGE_JSON})",
    )
    parser.add_argument(
        "--name-pos",
        action="store_true",
        help="Also name the pole the pos instructions describe, in a second, label-blind call "
             "(adds positive_name and positive_name_reasoning to each result; traits only)",
    )
    args = parser.parse_args(argv)
    if args.roles and args.name_pos:
        parser.error("--name-pos is for traits; it cannot be combined with --roles")
    return args


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    if args.roles:
        usage_json = Path(args.usage_json) if args.usage_json else DEFAULT_ROLE_USAGE_JSON
        asyncio.run(main_roles_async(args.roles, usage_json=usage_json))
        return
    usage_json = Path(args.usage_json) if args.usage_json else DEFAULT_USAGE_JSON
    asyncio.run(main_async(trait_filter=args.traits, usage_json=usage_json,
                           name_pos=args.name_pos))


if __name__ == "__main__":
    main()
