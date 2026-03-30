#!/usr/bin/env python3
"""Generate negative_labels for all traits by analyzing pos/neg instruction pairs.

For each trait:
1. Feeds Claude the positive_label and pos instructions
2. Feeds the neg instructions
3. Asks for the best negative_label (single adjective/short phrase)
4. Asks for a 0-4 antonym rating (how well negative_label is an antonym of positive_label)

Outputs a JSON object: { trait: { negative_label, antonym_score, reasoning } }
Uses known antonyms from steering_across_personas for 5 overlapping traits.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

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
) -> dict:
    msg = build_user_message(positive_label, definition, instructions)

    for attempt in range(5):
        async with semaphore:
            try:
                response = await client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=512,
                    temperature=0,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": msg}],
                )
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


async def main_async():
    traits_dir = Path(__file__).parent.parent / "data" / "traits" / "instructions"
    trait_files = sorted(traits_dir.glob("*.json"))
    print(f"Found {len(trait_files)} traits", file=sys.stderr)

    client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(10)

    results = {}
    tasks = []

    for tf in trait_files:
        positive_label = tf.stem
        with open(tf, encoding="utf-8") as f:
            data = json.load(f)
        instructions = data["instruction"]
        definition = extract_definition(data.get("eval_prompt", ""))

        tasks.append((positive_label, definition, instructions))

    print(f"Calling API for all {len(tasks)} traits", file=sys.stderr)

    async def run_one(pos_label, defn, insts):
        result = await classify_one(client, pos_label, defn, insts, semaphore)
        if pos_label in KNOWN_ANTONYMS:
            result["known_antonym"] = KNOWN_ANTONYMS[pos_label]
            match = result["negative_label"].lower() == KNOWN_ANTONYMS[pos_label].lower()
            result["matches_known"] = match
        return pos_label, result

    api_results = await asyncio.gather(
        *(run_one(pl, defn, insts) for pl, defn, insts in tasks)
    )

    for pos_label, result in api_results:
        results[pos_label] = result

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


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
