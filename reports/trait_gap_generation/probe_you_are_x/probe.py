"""Probe: is "You are X." ambiguous as a persona prompt?

For each word, ask Haiku five times (temperature 1.0), independently, how a persona given only
the instruction "You are <word>." behaves.  Then ask Sonnet to group the five readings by which
meaning of the word they rely on (reason first, then the grouping).  A word whose readings fall
into one group reads the same way every time; a word whose readings split is ambiguous as a prompt.

One-off diagnostic for the discussion of decision 11 (reports/trait_gap_generation/decisions_m1.md,
open point D).  Usage is recorded in usage.json beside the results.  Outputs go to the directory
given as argv[1]; nothing is written into the repository.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from assistant_axis.judge_pricing import MultiModelUsage

OUT = Path(sys.argv[1])
READER = "claude-haiku-4-5-20251001"
JUDGE = "claude-sonnet-4-6"
N_SAMPLES = 5
BUDGET_USD = 1.00

GROUPS = {
    "six_rejects": ["disciplinary", "engaging", "economic", "balanced", "empowered", "emotive"],
    "thing_sense_words": [
        "dynamic", "colorful", "deep", "polished", "warm", "dull", "volatile", "stiff", "toxic", "clinical",
        "graphic", "portable", "magnetic", "dense", "sharp", "cold", "bright", "abrasive", "shallow", "slick",
        "brittle", "mechanical", "linear", "organic"],
    "plain_trait_controls": [
        "bossy", "fickle", "smug", "nosy", "wily", "cheeky", "pushy", "garrulous", "gullible", "shrewd",
        "haughty", "coy", "petulant", "headstrong", "snobbish", "taciturn"],
    "candidates_two_person_senses": [
        "critical", "sensitive", "proud", "simple", "particular", "liberal", "conservative", "cool", "easy",
        "fresh", "green", "positive", "independent", "humble", "modest", "noble", "common", "mean", "funny",
        "curious", "mad", "civil", "forward", "fair", "driven", "committed", "withdrawn", "collected"],
    "corpus_rejected_by_filter": ["concrete", "rhetorical", "interdisciplinary"],
}

READ_PROMPT = ('A persona is given one instruction and nothing else: "You are {word}."\n'
               "In one sentence of at most 25 words, describe how this persona behaves. "
               "Reply with the sentence only.")

JUDGE_SYSTEM = (
    "You compare readings of a single word. Five readers were each given only the instruction "
    '"You are <word>." and each described how such a persona behaves. Your job is to say whether '
    "the readers took the word in the same meaning or in different meanings.\n\n"
    "Two readings rely on the same meaning when they describe the same trait in different words, or "
    "one trait with a different emphasis. They rely on different meanings when they describe traits "
    "that a careful writer would give different names, for example even-handed versus emotionally "
    "steady. A reading that blends two meanings counts toward both.\n\n"
    "Think first, then answer. Reply with one JSON object and nothing else, keys in this order:\n"
    '{"reason": "<at most 40 words>", "meanings": [{"meaning": "<at most 8 words>", '
    '"readings": [<reading numbers>]}], "n_meanings": <integer>, '
    '"readers_refused_or_asked": <integer, readings that declined or asked what the word means>}'
)


def charge(usage: MultiModelUsage, model: str, resp) -> None:
    u = resp.usage
    usage.charge(model, int(u.input_tokens or 0), int(u.output_tokens or 0))


async def call(client, sem, usage, *, model, user, system=None, temperature, max_tokens):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD:
            raise RuntimeError(f"budget of ${BUDGET_USD} reached")
        for attempt in range(4):
            try:
                kw = dict(model=model, max_tokens=max_tokens, temperature=temperature,
                          messages=[{"role": "user", "content": user}])
                if system:
                    kw["system"] = system
                resp = await client.messages.create(**kw)
                charge(usage, model, resp)
                return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))
        return None


async def one_word(client, sem, usage, group, word):
    readings = await asyncio.gather(*[
        call(client, sem, usage, model=READER, user=READ_PROMPT.format(word=word), temperature=1.0, max_tokens=80)
        for _ in range(N_SAMPLES)])
    readings = [r or "(no answer)" for r in readings]
    listing = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(readings))
    raw = await call(client, sem, usage, model=JUDGE, system=JUDGE_SYSTEM,
                     user=f'The word: "{word}"\n\nThe five readings:\n{listing}', temperature=0.0, max_tokens=400)
    judged, err = None, None
    try:
        s = raw[raw.index("{"): raw.rindex("}") + 1]
        judged = json.loads(s)
    except Exception as e:  # noqa: BLE001 - recorded, not hidden
        err = f"{type(e).__name__}: {e}"
    return {"group": group, "word": word, "readings": readings, "judge_raw": raw, "judged": judged, "parse_error": err}


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    load_dotenv(".env")
    assert os.getenv("ANTHROPIC_API_KEY"), "no API key in the environment"
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage = MultiModelUsage()
    sem = asyncio.Semaphore(8)
    tasks = [one_word(client, sem, usage, g, w) for g, ws in GROUPS.items() for w in ws]
    rows = []
    try:
        for fut in asyncio.as_completed(tasks):
            rows.append(await fut)
    finally:
        order = {w: i for i, w in enumerate(w for ws in GROUPS.values() for w in ws)}
        rows.sort(key=lambda r: order[r["word"]])
        with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        usage.write_json(OUT / "usage.json")
        (OUT / "run.json").write_text(json.dumps({
            "what": 'probe of "You are X." as a persona prompt', "reader": READER, "judge": JUDGE,
            "n_samples": N_SAMPLES, "reader_temperature": 1.0, "judge_temperature": 0.0,
            "read_prompt": READ_PROMPT, "judge_system": JUDGE_SYSTEM, "groups": GROUPS,
            "n_words_done": len(rows), "budget_usd": BUDGET_USD}, indent=2, ensure_ascii=False))
        print(usage.log_line())
    n_bad = sum(1 for r in rows if r["parse_error"])
    print(f"words: {len(rows)}  judge parse failures: {n_bad}")


asyncio.run(main())
