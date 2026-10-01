"""Step 2, the kind call, ONE reading per call, on every primary reading that step 1 gave.
The prompt is read from the rubric file.  argv[1] = output dir, argv[2] = results of the checks run."""
import asyncio, json, re, sys, hashlib
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge_pricing import MultiModelUsage

OUT = Path(sys.argv[1]); MODEL = "claude-haiku-4-5-20251001"; BUDGET_USD = 0.40
PROMPT = re.search(r"## The prompt\n\n````text\n(.*?)\n````", Path("reports/trait_gap_generation/rubrics/step2_kind.md").read_text(encoding="utf-8"), re.S).group(1)
rows = [json.loads(l) for l in open(sys.argv[2])]

async def one(client, sem, usage, w, j, reading, store, log):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD: raise RuntimeError("budget reached")
        send = {"id": 1, "label": w, "reading": reading}
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=300, temperature=0.0, system=PROMPT,
                                                    messages=[{"role": "user", "content": json.dumps(send, ensure_ascii=False)}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"sent": send, "raw": raw})
                try:
                    r = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0]; r.pop("id", None)
                except Exception as e:  # noqa: BLE001
                    r = {"error": f"{type(e).__name__}: {e}"}
                store[(w, j)] = r
                return
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))

async def main():
    OUT.mkdir(parents=True, exist_ok=True); load_dotenv(".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, store, log = MultiModelUsage(), {}, []
    sem = asyncio.Semaphore(8)
    jobs = [(r["word"], j, x["reading"]) for r in rows for j, x in enumerate(r["sense"].get("readings") or []) if x.get("rank") == "primary"]
    try:
        await asyncio.gather(*[one(client, sem, usage, w, j, rd, store, log) for w, j, rd in jobs])
    finally:
        usage.write_json(OUT / "usage.json"); print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            s = dict(r["sense"]); rs = [dict(x) for x in (s.get("readings") or [])]
            for j, x in enumerate(rs):
                if (r["word"], j) in store:
                    x["kind_call_v3"] = x.get("kind_call"); x["kind_call"] = store[(r["word"], j)]
            s["readings"] = rs
            fh.write(json.dumps({"word": r["word"], "group": r["group"], "sense": s}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "step 2, one reading per call", "model": MODEL, "temperature": 0.0, "prompt": PROMPT,
        "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(), "n_calls": len(jobs)}, indent=2, ensure_ascii=False))
    print("calls", len(jobs), "errors", sum(1 for v in store.values() if v.get("error")))
asyncio.run(main())
