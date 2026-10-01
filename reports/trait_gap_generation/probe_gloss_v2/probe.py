"""Gloss draft 2, one item per call, on the 74 words that went on as traits in probe_last_step.
The same label and reading are sent to each model in MODELS, so the drafts can be read side by side.
The prompt is read from the rubric file.  argv[1] = output dir, argv[2] = probe_last_step results."""
import asyncio, json, re, sys, hashlib, logging, statistics
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import MultiModelUsage

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("probe_gloss_v2")
OUT = Path(sys.argv[1]); BUDGET_USD = 0.40
MODELS = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-4-6"}
RUB = Path("reports/trait_gap_generation/rubrics")
PROMPT = re.search(r"## The prompt\n\n````text\n(.*?)\n````", (RUB / "gloss.md").read_text(encoding="utf-8"), re.S).group(1)
rows = [r for r in (json.loads(l) for l in open(sys.argv[2])) if r.get("last_step")]
SUBJECT = re.compile(r"\b(you|your|yours|yourself|i|my|me|they|their|the persona)\b", re.I)
ING = re.compile(r"This means \w+ing\b")

async def ask(client, sem, usage, key, send, log):
    async with sem:
        if usage.total_cost_usd >= BUDGET_USD: raise RuntimeError("budget reached")
        for attempt in range(4):
            try:
                resp = await client.messages.create(model=MODELS[key], max_tokens=300, temperature=0.0, system=PROMPT,
                                                    messages=[{"role": "user", "content": json.dumps(send, ensure_ascii=False)}])
                usage.charge(MODELS[key], int(resp.usage.input_tokens or 0), int(resp.usage.output_tokens or 0))
                raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
                log.append({"model": MODELS[key], "sent": send, "raw": raw})
                try:
                    return json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["results"][0].get("gloss")
                except Exception:  # noqa: BLE001
                    return None
            except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError):
                await asyncio.sleep(5 * (attempt + 1))

async def one(client, sem, usage, r, out, log):
    send = {"id": 1, "label": r["word"], "reading": r["last_step"]["reading"]}
    got = await asyncio.gather(*[ask(client, sem, usage, k, send, log) for k in MODELS])
    out[r["word"]] = dict(zip(MODELS, got))

def tally(name, glosses):
    g = [x for x in glosses if x]
    n = [len(x.split()) for x in g]
    print(f"{name}: {len(g)} glosses | open with This means and an -ing verb {sum(1 for x in g if ING.match(x))}"
          f" | name a subject {sum(1 for x in g if SUBJECT.search(x))} | words median {statistics.median(n)}, range {min(n)} to {max(n)}"
          f" | 18 to 32 words {sum(1 for k in n if 18 <= k <= 32)}")

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
            fh.write(json.dumps({"word": r["word"], "group": r["group"], "reading": r["last_step"]["reading"], "kind": r["last_step"]["kind"],
                                 "gloss_draft1_haiku": (r["last_step"].get("gloss") or {}).get("gloss"),
                                 **{f"gloss_draft2_{k}": (out.get(r["word"]) or {}).get(k) for k in MODELS}}, ensure_ascii=False) + "\n")
    with open(OUT / "responses.jsonl", "w", encoding="utf-8") as fh:
        for x in log: fh.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "run.json").write_text(json.dumps({"what": "gloss draft 2, one item per call, the same items sent to each model", "models": MODELS, "temperature": 0.0,
        "prompt": PROMPT, "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(), "n_words": len(rows),
        "input": sys.argv[2]}, indent=2, ensure_ascii=False))
    tally("draft 1, haiku", [(r["last_step"].get("gloss") or {}).get("gloss") for r in rows])
    for k in MODELS:
        tally(f"draft 2, {k}", [v.get(k) for v in out.values()])
        warn_if_low_parse_rate(label=f"probe_gloss_v2:{MODELS[k]}", n_ok=sum(1 for v in out.values() if v.get(k)), n_total=len(rows), logger_obj=logger)
asyncio.run(main())
