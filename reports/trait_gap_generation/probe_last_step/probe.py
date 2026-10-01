"""The last step, one item per call: the gloss for each word that goes on as a trait, then the
alignment check and the descriptors on that gloss.  Prompts are read from the rubric files.
argv[1] = output dir, argv[2] = results of the rerun (kinds and established answers)."""
import asyncio, json, re, sys, hashlib
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge_pricing import MultiModelUsage

OUT = Path(sys.argv[1]); MODEL = "claude-haiku-4-5-20251001"; BUDGET_USD = 0.40
RUB = Path("reports/trait_gap_generation/rubrics")
P = {k: re.search(r"## The prompt\n\n````text\n(.*?)\n````", (RUB / f"{k}.md").read_text(encoding="utf-8"), re.S).group(1) for k in ("gloss", "alignment", "descriptors")}
rows = [json.loads(l) for l in open(sys.argv[2])]
TR = {"trait", "membership"}

def accepted(r):
    p = [x for x in (r["sense"].get("readings") or []) if x.get("rank") == "primary"]
    if not p or all((x.get("check_established") or {}).get("established") == "stretched" for x in p): return None
    for x in p:
        if (x.get("kind_call") or {}).get("kind") in TR: return x
    return None

async def ask(client, sem, usage, system, send, log, step, max_tokens=300):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD: raise RuntimeError("budget reached")
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODEL, max_tokens=max_tokens, temperature=0.0, system=system,
                                                    messages=[{"role": "user", "content": json.dumps(send, ensure_ascii=False)}])
                usage.charge(MODEL, int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"step": step, "sent": send, "raw": raw})
                try:
                    r = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0]; r.pop("id", None); return r
                except Exception as e:  # noqa: BLE001
                    return {"error": f"{type(e).__name__}: {e}"}
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))

async def one(client, sem, usage, r, out, log):
    x = accepted(r)
    if x is None: return
    w = r["word"]
    g = await ask(client, sem, usage, P["gloss"], {"id": 1, "label": w, "reading": x["reading"]}, log, "gloss")
    res = {"reading": x["reading"], "kind": (x.get("kind_call") or {}).get("kind"), "gloss": g}
    if g and g.get("gloss"):
        a, d = await asyncio.gather(ask(client, sem, usage, P["alignment"], {"id": 1, "label": w, "description": g["gloss"]}, log, "alignment"),
                                    ask(client, sem, usage, P["descriptors"], {"id": 1, "label": w, "description": g["gloss"]}, log, "descriptors"))
        res.update(alignment=a, descriptors=d)
    out[w] = res

async def main():
    OUT.mkdir(parents=True, exist_ok=True); load_dotenv(".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage, out, log = MultiModelUsage(), {}, []
    sem = asyncio.Semaphore(8)
    try:
        await asyncio.gather(*[one(client, sem, usage, r, out, log) for r in rows])
    finally:
        usage.write_json(OUT / "usage.json"); print(usage.log_line())
    with open(OUT / "results.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps({"word": r["word"], "group": r["group"], "last_step": out.get(r["word"])}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "gloss, alignment check and descriptors, one item per call", "model": MODEL, "temperature": 0.0, "prompts": P,
        "prompt_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in P.items()}, "n_words": len(out)}, indent=2, ensure_ascii=False))
    print("words glossed", len(out), "errors", sum(1 for v in out.values() for k in ("gloss", "alignment", "descriptors") if (v.get(k) or {}).get("error")))
asyncio.run(main())
