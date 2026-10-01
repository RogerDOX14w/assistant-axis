"""Run the split rubrics exactly as they stand in reports/trait_gap_generation/rubrics/.

Step 1 (sense) on every word; then the two checks on its output: "established" on each primary
reading, "vague" on the most likely reading.  The prompts are read from the fenced blocks of the
rubric files, so what runs is what the files say.  One-off diagnostic; usage recorded in usage.json.
argv[1] = output directory, argv[2] = groups file.
"""
import asyncio, json, os, re, sys, hashlib
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge_pricing import MultiModelUsage

OUT = Path(sys.argv[1]); GROUPS = json.load(open(sys.argv[2]))
RUBRICS = Path("reports/trait_gap_generation/rubrics")
MODEL = "claude-haiku-4-5-20251001"; BUDGET_USD = 0.60; BATCH = 20


def prompt_of(name):
    t = (RUBRICS / name).read_text(encoding="utf-8")
    m = re.search(r"## The prompt\n\n````text\n(.*?)\n````", t, re.S)
    assert m, name
    return m.group(1)


PROMPTS = {k: prompt_of(k + ".md") for k in ("step1_sense", "check_established", "check_vague")}


def parse(raw):
    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"]


async def call(client, sem, usage, system, user, log, step):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD:
            raise RuntimeError("budget reached")
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=4000, temperature=0.0, system=system,
                                                    messages=[{"role": "user", "content": user}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"step": step, "user": user, "raw": text})
                return text
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))
        return None


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    load_dotenv(".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, log, errors = MultiModelUsage(), [], {}
    sem = asyncio.Semaphore(6)
    import random
    words = [w for ws in GROUPS.values() for w in ws]
    random.Random(11).shuffle(words)
    group_of = {w: g for g, ws in GROUPS.items() for w in ws}
    sense = {}
    try:
        async def sense_batch(batch):
            user = "\n".join(json.dumps({"id": i + 1, "label": w}) for i, w in enumerate(batch))
            raw = await call(client, sem, usage, PROMPTS["step1_sense"], user, log, "sense")
            try:
                for w, r in zip(batch, parse(raw)):
                    if r.get("label") != w: errors[w] = f"label echo mismatch: {r.get('label')!r}"
                    sense[w] = r
            except Exception as e:  # noqa: BLE001
                for w in batch: errors[w] = f"sense: {type(e).__name__}: {e}"
        await asyncio.gather(*[sense_batch(words[i:i + BATCH]) for i in range(0, len(words), BATCH)])

        def top(w):
            rs = (sense.get(w) or {}).get("readings") or []
            p = [j for j, r in enumerate(rs) if r.get("rank") == "primary"]
            return p or ([0] if rs else [])
        est_items = [(w, j) for w in words for j in top(w)]
        vag_items = [(w, top(w)[0]) for w in words if top(w)]

        async def check(batch, name, field):
            rows = []
            for i, (w, j) in enumerate(batch):
                d = {"id": i + 1, "label": w}
                if name == "check_established": d["first_thought"] = sense[w].get("first_thought")
                d["reading"] = sense[w]["readings"][j]["reading"]
                rows.append(json.dumps(d, ensure_ascii=False))
            raw = await call(client, sem, usage, PROMPTS[name], "\n".join(rows), log, name)
            try:
                for (w, j), r in zip(batch, parse(raw)):
                    r.pop("id", None); sense[w]["readings"][j][field] = r
            except Exception as e:  # noqa: BLE001
                for w, _ in batch: errors[w] = f"{name}: {type(e).__name__}: {e}"
        await asyncio.gather(*([check(est_items[i:i + BATCH], "check_established", "established_check") for i in range(0, len(est_items), BATCH)]
                               + [check(vag_items[i:i + BATCH], "check_vague", "vague_check") for i in range(0, len(vag_items), BATCH)]))
    finally:
        usage.write_json(OUT / "usage.json"); print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for w in words:
            fh.write(json.dumps({"word": w, "group": group_of[w], "sense": sense.get(w), "error": errors.get(w)}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "split rubrics as they stand in the rubric files", "model": MODEL, "temperature": 0.0,
        "prompts": PROMPTS, "prompt_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in PROMPTS.items()},
        "groups": GROUPS, "word_order": "shuffled across groups, seed 11", "n_established_items": len(est_items), "n_vague_items": len(vag_items)}, indent=2, ensure_ascii=False))
    print(f"words {len(words)}  established items {len(est_items)}  vague items {len(vag_items)}  errors {len(errors)}")

asyncio.run(main())
