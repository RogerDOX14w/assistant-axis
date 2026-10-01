"""The two checks, ONE item per call, on the output of step 1 run one word per call (draft 6).
Prompts are read from the rubric files.  argv[1] = output dir, argv[2] = step 1 results (probe_single)."""
import asyncio, json, re, sys, hashlib
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge_pricing import MultiModelUsage

OUT = Path(sys.argv[1]); MODEL = "claude-haiku-4-5-20251001"; BUDGET_USD = 0.45
RUB = Path("reports/trait_gap_generation/rubrics")
def prompt_of(n):
    return re.search(r"## The prompt\n\n````text\n(.*?)\n````", (RUB / n).read_text(encoding="utf-8"), re.S).group(1)
PROMPTS = {k: prompt_of(k + ".md") for k in ("check_established",)}
rows = [json.loads(l) for l in open(sys.argv[2])]

async def one(client, sem, usage, name, item, store, log):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD: raise RuntimeError("budget reached")
        user = json.dumps(item["send"], ensure_ascii=False)
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=300, temperature=0.0, system=PROMPTS[name],
                                                    messages=[{"role": "user", "content": user}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"check": name, "sent": item["send"], "raw": raw})
                try:
                    r = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0]; r.pop("id", None)
                except Exception as e:  # noqa: BLE001
                    r = {"error": f"{type(e).__name__}: {e}"}
                store[(item["word"], item["j"], name)] = r
                return
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))

async def main():
    OUT.mkdir(parents=True, exist_ok=True); load_dotenv(".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, store, log = MultiModelUsage(), {}, []
    sem = asyncio.Semaphore(8); jobs = []
    for r in rows:
        s = r["sense"] or {}; rs = s.get("readings") or []
        prim = [j for j, x in enumerate(rs) if x.get("rank") == "primary"]
        for j in prim:
            jobs.append(("check_established", {"word": r["word"], "j": j, "send": {"id": 1, "label": r["word"], "first_thought": s.get("first_thought"), "reading": rs[j]["reading"]}}))
        if False:
            jobs.append(("check_vague", {"word": r["word"], "j": prim[0], "send": {"id": 1, "label": r["word"], "reading": rs[prim[0]]["reading"]}}))
    try:
        await asyncio.gather(*[one(client, sem, usage, n, it, store, log) for n, it in jobs])
    finally:
        usage.write_json(OUT / "usage.json"); print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            s = dict(r["sense"] or {}); rs = [dict(x) for x in (s.get("readings") or [])]
            for j, x in enumerate(rs):
                if (r["word"], j, "check_established") in store:
                    x["check_established_v3"] = x.get("check_established"); x["check_established"] = store[(r["word"], j, "check_established")]
            s["readings"] = rs
            fh.write(json.dumps({"word": r["word"], "group": r["group"], "sense": s}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "both checks, one item per call, on step 1 draft 6 run one word per call", "model": MODEL, "temperature": 0.0,
        "prompts": PROMPTS, "prompt_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in PROMPTS.items()}, "n_calls": len(jobs)}, indent=2, ensure_ascii=False))
    print("calls", len(jobs), "errors", sum(1 for v in store.values() if v.get("error")))
asyncio.run(main())
