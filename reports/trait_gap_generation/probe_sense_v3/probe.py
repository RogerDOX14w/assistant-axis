"""Probe: Roger's split of the rubric into small calls, second attempt.

Step 1, the sense call: what could "You are <label>." be taken to mean, most obvious first, every
reading included.  It is not asked what kind of thing a reading is.
Step 2, the kind call: given a label and ONE reading, what kind of thing is that reading.
The rule that joins the two is code (see join()).

Neither prompt mentions the corpus or what the answers are for.  One-off diagnostic; usage is
recorded in usage.json beside the results.  argv[1] = output directory, argv[2] = groups file.
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

SENSE_PROMPT = """\
A persona is given a one-line instruction, "You are <label>.", and nothing else. For each label below, say how a reader would take that instruction.

Some labels give the instruction no meaning a reader could use. "You are octagonal." and "You are alkaline." are like that: the words are about shapes and substances. That is a normal answer.

For each label:
- note: one short sentence on what the word ordinarily means and what it is ordinarily said of. Write this first.
- first_thought: what comes to mind first on meeting the bare word, in a few plain words, whatever the word is said of.
- readings: the ways a reader could take "You are <label>." as saying something about the persona, the most likely first, at most four. Rank them by how likely a reader is to take the instruction that way, not by how common the meaning is in general. Include readings about the body, about a passing condition or situation, and about standing, as well as readings about character. Give each in a few plain words. Mark it "primary" if it is one of the one or two readings most readers would arrive at, and "secondary" if it is less likely. Do not say whether a reading is a personality trait; that is not your question. If the instruction has no reading about the persona, give an empty list.
- usable: true when at least one reading is clear enough that a persona given only this instruction would know what is being asked of it. False when none is, or when a reader would have to invent one.
- overshadowed: true when the first thought is about something other than a person, and is so much more familiar than any reading that it would get in a reader's way: the reader thinks of the other thing first and has to work to reach the reading. False when the word is well known in its use for people, even if it began as a word for things.
- vague: true when even the most likely reading would leave a persona unsure what is being asked. That happens when the label leaves out something the reader needs ("adjacent" to what, "former" what, "accustomed" to what, "northern" part of what), and when the reading is so general that it fits almost anyone. Otherwise false.

List readings the word already has, or that follow plainly from its parts. Do not extend the word to a new use.

Respond with one JSON object and nothing else, note first:
{"results": [{"id": <int>, "label": "<the label exactly as given>", "note": "<one short sentence>", "first_thought": "<a few words>", "readings": [{"reading": "<a few words>", "rank": "primary"|"secondary"}, ...], "usable": true|false, "overshadowed": true|false, "vague": true|false}]}
Return one row per id, in the order given."""

KIND_PROMPT = """\
You are sorting descriptions of people into kinds. Each item gives a label and one reading of the instruction "You are <label>." Say what kind of thing that reading is. Judge the reading as it is given; do not replace it with another meaning of the label.

The kinds:
- trait: a standing disposition, habit, style, stance or inclination of a person: how they tend to think, feel, relate, speak, value or decide. A willingness or inclination to do something counts, however rare or disapproved of.
- membership: a standing fact of a person's life that others use to say who they are, and that combines freely with any profession. Its kinds: circumstance (housing, money, work pattern), class, family, affinity (pets, hobbies, tastes), relationship, orientation_gender, geography (region, city or country life), nationality_ethnicity_language, age_group (an age group or school year), religion.
- state: a condition a person is in for a while, from moments to weeks: of mood, of body, of appearance or of situation, including one imposed from outside. How someone is just now, as against how they are.
- physical: a lasting feature of a person's body that has little or no effect on how they act or talk.
- role: an identity big enough to organize the whole persona, so that a person has only one: a profession or calling, an office or official status, a rank so high or so low that it rules out most professions, an age so young or so old that it rules out a profession.
- action: a single deed or event, or a property of acts rather than of the people who do them.
- evaluative: pure praise or blame, which says how the speaker feels about the person and nothing about what the person does.
- not_a_persona: a reading that says nothing about how a persona would act, think or speak, such as a literal reading about a material, a shape or a place.

For each item give a reason in one short sentence, then the kind. For a membership also give membership_kind; otherwise null.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "kind": "trait"|"membership"|"state"|"physical"|"role"|"action"|"evaluative"|"not_a_persona", "membership_kind": "<kind>"|null}]}
Return one row per id, in the order given."""

GROUPS = json.load(open(sys.argv[2]))
TRAITLIKE = {"trait", "membership"}
QUEUE = {"state": "states queue", "physical": "physical list", "role": "roles list"}


def join(sense: dict) -> dict:
    """The rule that joins the two steps.  Returns {outcome, notes}."""
    rs = [r for r in (sense.get("readings") or []) if r.get("kind")]
    if not sense.get("usable") or not rs:
        return {"outcome": "reject", "why": "no usable reading", "notes": []}
    prim = [r for r in rs if r.get("rank") == "primary"] or rs[:1]
    sec = [r for r in rs if r not in prim]
    first = prim[0]
    notes = []
    if first["kind"] in TRAITLIKE:
        if sense.get("needs_completing"):
            return {"outcome": "set aside", "why": "needs completing", "notes": []}
        if sum(r["kind"] in TRAITLIKE for r in prim) >= 2:
            notes.append("two primary trait readings")
        other = [f'{r["reading"]} ({r["kind"]})' for r in rs if r["kind"] not in TRAITLIKE]
        if other:
            notes.append("also read as: " + "; ".join(other))
        return {"outcome": "trait", "why": first["reading"], "notes": notes,
                "membership": first["kind"] == "membership"}
    # the most obvious reading is not a trait
    also_prim = [r for r in prim[1:] if r["kind"] in TRAITLIKE]
    if also_prim:
        return {"outcome": "trait", "why": also_prim[0]["reading"],
                "notes": [f'judgement call: the most obvious reading is "{first["reading"]}" ({first["kind"]})'],
                "membership": also_prim[0]["kind"] == "membership"}
    if first["kind"] in QUEUE:
        extra = [f'a less obvious trait reading: {r["reading"]}' for r in sec if r["kind"] in TRAITLIKE]
        return {"outcome": QUEUE[first["kind"]], "why": first["reading"], "notes": extra}
    if any(r["kind"] in TRAITLIKE for r in sec):
        t = [r for r in sec if r["kind"] in TRAITLIKE][0]
        return {"outcome": "set aside", "why": f'trait reading "{t["reading"]}" overshadowed by "{first["reading"]}" ({first["kind"]})', "notes": []}
    return {"outcome": "reject", "why": f'{first["reading"]} ({first["kind"]})', "notes": []}


def parse(raw):
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"]


async def call(client, sem, usage, system, user, log, kind):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD:
            raise RuntimeError("budget reached")
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=4000, temperature=0.0, system=system,
                                                    messages=[{"role": "user", "content": user}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"step": kind, "user": user, "raw": text})
                return text
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))
        return None


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    load_dotenv(".env")
    assert os.getenv("ANTHROPIC_API_KEY"), "no API key in the environment"
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, log = MultiModelUsage(), []
    sem = asyncio.Semaphore(6)
    words = [w for ws in GROUPS.values() for w in ws]
    group_of = {w: g for g, ws in GROUPS.items() for w in ws}
    sense, errors = {}, {}
    try:
        async def sense_batch(batch):
            user = "\n".join(json.dumps({"id": i + 1, "label": w}) for i, w in enumerate(batch))
            raw = await call(client, sem, usage, SENSE_PROMPT, user, log, "sense")
            try:
                for w, r in zip(batch, parse(raw)):
                    if r.get("label") != w:
                        errors[w] = f"label echo mismatch: {r.get('label')!r}"
                    sense[w] = r
            except Exception as e:  # noqa: BLE001 - recorded, not hidden
                for w in batch:
                    errors[w] = f"sense: {type(e).__name__}: {e}"
        await asyncio.gather(*[sense_batch(words[i:i + BATCH]) for i in range(0, len(words), BATCH)])

        items = []

        async def kind_batch(batch):
            user = "\n".join(json.dumps({"id": i + 1, "label": w, "reading": sense[w]["readings"][j]["reading"]})
                             for i, (w, j) in enumerate(batch))
            raw = await call(client, sem, usage, KIND_PROMPT, user, log, "kind")
            try:
                for (w, j), r in zip(batch, parse(raw)):
                    sense[w]["readings"][j].update(kind=r.get("kind"), membership_kind=r.get("membership_kind"),
                                                   kind_reason=r.get("reason"))
            except Exception as e:  # noqa: BLE001 - recorded, not hidden
                for w, _ in batch:
                    errors[w] = f"kind: {type(e).__name__}: {e}"
        await asyncio.gather(*[kind_batch(items[i:i + BATCH]) for i in range(0, len(items), BATCH)])
    finally:
        usage.write_json(OUT / "usage.json")
        print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for w in words:
            s = sense.get(w) or {}
            fh.write(json.dumps({"word": w, "group": group_of[w], "sense": s, "joined": None,
                                 "error": errors.get(w)}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log:
            fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({
        "what": "sense call, then kind call on each reading, joined by code", "model": MODEL, "temperature": 0.0,
        "sense_prompt": SENSE_PROMPT, "kind_prompt": KIND_PROMPT, "groups": GROUPS,
        "n_readings_sent_to_kind": len(items), "budget_usd": BUDGET_USD}, indent=2, ensure_ascii=False))
    print(f"words: {len(words)}  readings: {len(items)}  rows with an error: {len(errors)}")


asyncio.run(main())
