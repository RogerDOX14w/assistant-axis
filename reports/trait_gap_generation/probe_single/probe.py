"""Control: step 1 with ONE word per call, so that no word can influence another.
Two prompts are compared: Roger's edited text (draft 5) and the same with one clause added (draft 6).
argv[1] = output directory, argv[2] = groups file, argv[3] = run.json holding draft 5."""
import asyncio, json, os, re, sys, hashlib
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge_pricing import MultiModelUsage

OUT = Path(sys.argv[1]); GROUPS = json.load(open(sys.argv[2]))
MODEL = "claude-haiku-4-5-20251001"; BUDGET_USD = 0.45
d5 = json.load(open(sys.argv[3]))["prompts"]["step1_sense"]
t = Path("reports/trait_gap_generation/rubrics/step1_sense.md").read_text(encoding="utf-8")
d6 = re.search(r"## The prompt\n\n````text\n(.*?)\n````", t, re.S).group(1)
PROMPTS = {"draft5": d5, "draft6": d6}

async def one(client, sem, usage, name, system, w, out, log):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD: raise RuntimeError("budget reached")
        user = json.dumps({"id": 1, "label": w})
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=700, temperature=0.0, system=system,
                                                    messages=[{"role": "user", "content": user}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"prompt": name, "word": w, "raw": raw})
                try:
                    out[(name, w)] = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0]
                except Exception as e:  # noqa: BLE001
                    out[(name, w)] = {"error": f"{type(e).__name__}: {e}"}
                return
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))

async def main():
    OUT.mkdir(parents=True, exist_ok=True); load_dotenv(".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, out, log = MultiModelUsage(), {}, []
    sem = asyncio.Semaphore(8)
    words = [w for ws in GROUPS.values() for w in ws]; group_of = {w: g for g, ws in GROUPS.items() for w in ws}
    try:
        await asyncio.gather(*[one(client, sem, usage, n, p, w, out, log) for n, p in PROMPTS.items() for w in words])
    finally:
        usage.write_json(OUT / "usage.json"); print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for w in words:
            fh.write(json.dumps({"word": w, "group": group_of[w], "draft5": out.get(("draft5", w)), "draft6": out.get(("draft6", w))}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "step 1, one word per call, two prompts", "model": MODEL, "temperature": 0.0, "prompts": PROMPTS,
        "prompt_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in PROMPTS.items()}, "groups": GROUPS}, indent=2, ensure_ascii=False))
    print("words", len(words), "errors", sum(1 for v in out.values() if v.get("error")))
asyncio.run(main())
