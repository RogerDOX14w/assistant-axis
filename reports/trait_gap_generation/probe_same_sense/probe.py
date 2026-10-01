"""The same-sense check, one item per call, on the test words whose two primary readings were both
taken for a trait or a membership (30 of the 99).  MY_READING is Fable's own reading of the 30, made
before the run; it is not Roger's.  argv[1] = output dir."""
import asyncio, json, re, sys, hashlib, logging
from collections import Counter
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import MultiModelUsage

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("probe_same_sense")
OUT = Path(sys.argv[1]); MODEL = "claude-haiku-4-5-20251001"; BUDGET_USD = 0.20
P = Path("reports/trait_gap_generation")
PROMPT = re.search(r"## The prompt\n\n````text\n(.*?)\n````", (P / "rubrics/check_same_sense.md").read_text(encoding="utf-8"), re.S).group(1)
ON = {"trait", "membership"}
MY_READING = {
    "same": "Eastern Orthodox, full-time, high-energy, illegal, nonsovereign, part-time, Tuscan, unobtrusive, bossy, "
            "garrulous, gullible, taciturn, bothersome, prickly, engaging",
    "shade": "corruptible, lawless, wily, cheeky, shrewd, snobbish, wishy-washy, fickle",
    "different": "Danish, middle, watertight, coy, balanced, bright, rhetorical",
}
MINE = {w.strip(): k for k, v in MY_READING.items() for w in v.split(",")}


def pairs():
    out = []
    for line in open(P / "probe_rerun_wording/results.jsonl", encoding="utf-8"):
        r = json.loads(line)
        s = [x for x in (r["sense"].get("readings") or []) if x.get("rank") == "primary"
             and (x.get("check_established") or {}).get("established") != "stretched"
             and (x.get("kind_call") or {}).get("kind") in ON]
        if len(s) >= 2:
            out.append({"word": r["word"], "a": s[0]["reading"], "b": s[1]["reading"]})
    return out


async def ask(client, sem, usage, item, log):
    send = {"id": 1, "label": item["word"], "reading_1": item["a"], "reading_2": item["b"]}
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD: raise RuntimeError("budget reached")
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=300, temperature=0.0, system=PROMPT,
                                                    messages=[{"role": "user", "content": json.dumps(send, ensure_ascii=False)}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"sent": send, "raw": raw})
                try:
                    r = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0]
                    return {**item, "relation": r.get("relation"), "reason": r.get("reason"), "mine": MINE.get(item["word"])}
                except Exception as e:  # noqa: BLE001
                    return {**item, "relation": None, "error": f"{type(e).__name__}: {e}", "mine": MINE.get(item["word"])}
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))


async def main():
    OUT.mkdir(parents=True, exist_ok=True); load_dotenv(".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, log, items = MultiModelUsage(), [], pairs()
    sem = asyncio.Semaphore(8)
    try:
        rows = await asyncio.gather(*[ask(client, sem, usage, it, log) for it in items])
    finally:
        usage.write_json(OUT / "usage.json"); print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "same-sense check, one item per call", "model": MODEL, "temperature": 0.0,
        "prompt": PROMPT, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(), "n_calls": len(items),
        "my_reading": MY_READING}, indent=2, ensure_ascii=False))
    warn_if_low_parse_rate(label=f"probe_same_sense:{MODEL}", n_ok=sum(1 for r in rows if r.get("relation")), n_total=len(rows), logger_obj=logger)
    print("model:", dict(Counter(r.get("relation") for r in rows)))
    print("mine :", dict(Counter(r.get("mine") for r in rows)))
    print("cross (mine, model):", dict(Counter((r.get("mine"), r.get("relation")) for r in rows)))
    for r in rows:
        mark = "" if r.get("mine") == r.get("relation") else "   <-- differs"
        print(f"{r['word']:18} mine={r.get('mine'):9} model={r.get('relation')}{mark}")
asyncio.run(main())
