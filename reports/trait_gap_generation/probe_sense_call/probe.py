"""Probe: two ways of asking, in a small call with no other context, what a bare label means.

Variant R is Roger's proposal (2026-09-29): ask only about the instruction "You are <label>.":
does it have a clear and obvious meaning, and if so which; primary meanings apart from less
obvious ones.  Variant D is the dictionary entry of rubric_v5_draft.md: the word's meanings and
what each is ordinarily said of, with no mention of personas at all.

Neither prompt mentions traits, the corpus, or what the answer is for.  One-off diagnostic;
usage is recorded in usage.json beside the results.  Outputs go to the directory given as argv[1].
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
MODEL = "claude-haiku-4-5-20251001"
BUDGET_USD = 0.60
BATCH = 20

PROMPT_R = """\
A persona is given a one-line instruction of the form "You are <label>." and nothing else. For each label below, consider that instruction exactly as written.

Many labels make no clear sense in that instruction. "You are octagonal." and "You are alkaline." say nothing clear about a persona, because those words are about shapes and substances and are not said of people. That is a normal answer, and it is the right one for most words in a dictionary. Do not stretch a word to make it fit.

For each label:
- note: one short sentence on what the word ordinarily means and what it is ordinarily said of. Write this first.
- clear: true when "You are <label>." has a clear and obvious meaning, one that most readers would arrive at without effort; false otherwise.
- primary: when clear is true, the one or two meanings most readers would take, each in a few words, the most obvious first. Usually there is one.
- secondary: other meanings the instruction could bear that are less obvious. Often there are none.

List only meanings the word already has when it is said of a person. If you have to invent the meaning, clear is false and both lists are empty.

Respond with one JSON object and nothing else, note first:
{"results": [{"id": <int>, "label": "<the label exactly as given>", "note": "<one short sentence>", "clear": true|false, "primary": ["<a few words>", ...], "secondary": ["<a few words>", ...]}]}
Return one row per id, in the order given."""

PROMPT_D = """\
You are writing short dictionary entries. For each word or phrase below, record how it is used in ordinary English. You are not told what the entries are for, and you should not guess. Describe the word as it is used, not as it could be used.

For each word:
- note: one short sentence saying what you know about the word. Write this first.
- known: true when this is a real English word or phrase and you can say confidently what it means; a regular derivation or compound of real words counts when its meaning is plain from its parts. False for a misspelling, an invented word, or a word whose meaning you cannot work out.
- meanings: the meanings the word has in use, commonest first, at most four. An entry with a single meaning is normal. For each meaning give:
  - meaning: a few plain words.
  - said_of: what the word, in this meaning, is ordinarily said of. One or two of: people; things (objects, substances, places, animals, plants); actions (deeds, events, processes); abstractions (ideas, texts, plans, situations, amounts). Give two only when the meaning is ordinarily said of both, the commoner first.
  - figurative: true when this meaning is a figurative extension of another meaning of the word; otherwise false.

List only meanings the word already has. Many words are said only of things, or only of actions, and their entries should say so. Do not supply a use for people, or for anything else, because the word could be stretched to it. If you have to imagine the use, it is not a meaning.

Respond with one JSON object and nothing else, note first:
{"results": [{"id": <int>, "word": "<the word exactly as given>", "note": "<one short sentence>", "known": true|false, "meanings": [{"meaning": "<a few words>", "said_of": ["people"|"things"|"actions"|"abstractions", ...], "figurative": true|false}, ...]}]}
Return one row per id, in the order given."""

GROUPS = json.load(open(sys.argv[2]))


def parse(raw):
    s = raw[raw.index("{"): raw.rindex("}") + 1]
    return json.loads(s)["results"]


async def call(client, sem, usage, system, user):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD:
            raise RuntimeError("budget reached")
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=4000, temperature=0.0, system=system,
                                                    messages=[{"role": "user", "content": user}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))
        return None


async def run_variant(client, sem, usage, name, system, key, words):
    out, raws = {}, []
    batches = [words[i:i + BATCH] for i in range(0, len(words), BATCH)]

    async def one(batch):
        user = "\n".join(json.dumps({"id": i + 1, key: w}) for i, w in enumerate(batch))
        raw = await call(client, sem, usage, system, user)
        raws.append({"variant": name, "words": batch, "raw": raw})
        try:
            rows = parse(raw)
            for w, r in zip(batch, rows):
                got = r.get(key)
                out[w] = r if got == w else {"error": f"label echo mismatch: {got!r}", **r}
        except Exception as e:  # noqa: BLE001 - recorded, not hidden
            for w in batch:
                out[w] = {"error": f"{type(e).__name__}: {e}"}
    await asyncio.gather(*[one(b) for b in batches])
    return out, raws


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    load_dotenv(".env")
    assert os.getenv("ANTHROPIC_API_KEY"), "no API key in the environment"
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage = MultiModelUsage()
    sem = asyncio.Semaphore(6)
    words = [w for ws in GROUPS.values() for w in ws]
    group_of = {w: g for g, ws in GROUPS.items() for w in ws}
    try:
        (r, raw_r), (d, raw_d) = await asyncio.gather(
            run_variant(client, sem, usage, "R", PROMPT_R, "label", words),
            run_variant(client, sem, usage, "D", PROMPT_D, "word", words))
    finally:
        usage.write_json(OUT / "usage.json")
        print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for w in words:
            fh.write(json.dumps({"word": w, "group": group_of[w], "R": r.get(w), "D": d.get(w)}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in raw_r + raw_d:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({
        "what": "two framings of a small sense call, no other context", "model": MODEL, "temperature": 0.0,
        "prompt_R": PROMPT_R, "prompt_D": PROMPT_D, "groups": GROUPS, "budget_usd": BUDGET_USD}, indent=2, ensure_ascii=False))
    bad = sum(1 for w in words for v in (r.get(w), d.get(w)) if not v or v.get("error"))
    print(f"words: {len(words)}  rows with an error: {bad}")


asyncio.run(main())
