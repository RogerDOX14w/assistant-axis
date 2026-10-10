"""W15 non-goal borderline resample (Roger 2026-10-10): every instruction of a borderline non-goal candidate is
classified four more times at temperature 1 on the same model and prompt as the temperature-0 run, and the five
samples are averaged.

Borderline: four of five instructions at 0 and none at 2 in the temperature-0 run (roles; traits on the pos side,
`physical`-tagged traits left out, since they stay out of the goal lists).  `--names` adds others (previous list
members at three of five, if Roger wants them).

Rule: an instruction counts as 0 when the mean of its five samples is below 0.5; the item qualifies as non-goal when
all five of its instructions do (the all-five rule of data/README.md, with each score denoised).

The temperature-0 records in data_analysis/output/ are not touched.  Samples go to resample_t1.jsonl (appended as
they arrive), the verdicts to resample_t1_summary.json, usage to resample_t1_usage.json and, merged, to the
cumulative data_analysis/output/goal_classifications_usage.json.

    uv run python roger/pre_extraction_2026-10-09/w15/resample_t1.py [--names X Y ...] [--dry-run]
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv  # noqa: E402

from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402
from data_analysis import classify_goals as C  # noqa: E402

HERE = Path("roger/pre_extraction_2026-10-09/w15")
MODEL = "claude-opus-4-6"
N_EXTRA = 4
TEMPERATURE = 1.0
SAMPLES, SUMMARY, USAGE = HERE / "resample_t1.jsonl", HERE / "resample_t1_summary.json", HERE / "resample_t1_usage.json"
CUMULATIVE_USAGE = Path("data_analysis/output/goal_classifications_usage.json")


def physical_stems():
    out = set()
    for p in Path("data/traits/instructions").glob("*.json"):
        if "physical" in (json.load(open(p, encoding="utf-8")).get("tags") or []):
            out.add(p.stem)
    return out


def t0_scores():
    """(source, name) -> {index: score} from the temperature-0 aggregate (roles; traits pos side)."""
    out = {}
    for a in json.load(open("data_analysis/output/goal_classifications.json", encoding="utf-8")):
        if a["source"] == "role" or a["polarity"] == "pos":
            out[(a["source"], a["name"])] = {i["index"]: (i["classification"] or {}).get("score") for i in a["instructions"]}
    return out


def select(t0, extra_names):
    phys = physical_stems()
    chosen = []
    for (src, name), sc in sorted(t0.items()):
        vals = [v for v in sc.values() if v is not None]
        borderline = len(vals) == 5 and vals.count(0) == 4 and 2 not in vals
        if (borderline or name in extra_names) and not (src == "trait" and name in phys):
            chosen.append((src, name))
    return chosen


def summarize(t0, chosen, items_by_key):
    samples = {}
    if SAMPLES.exists():
        for line in open(SAMPLES, encoding="utf-8"):
            r = json.loads(line)
            key = (r["source"], r["name"], r["index"])
            if items_by_key.get(key) == r["text"] and r["classification"] is not None:
                samples.setdefault(key, []).append(r["classification"]["score"])
    out = []
    for src, name in chosen:
        per = []
        for idx in range(5):
            s0 = t0[(src, name)].get(idx)
            extra = samples.get((src, name, idx), [])
            allv = ([s0] if s0 is not None else []) + extra
            per.append({"index": idx, "t0": s0, "t1": extra, "mean": round(sum(allv) / len(allv), 2) if allv else None})
        complete = all(len(p["t1"]) == N_EXTRA for p in per)
        qualifies = complete and all(p["mean"] is not None and p["mean"] < 0.5 for p in per)
        out.append({"source": src, "name": name, "qualifies": qualifies, "complete": complete,
                    "item_mean": round(sum(p["mean"] for p in per if p["mean"] is not None) / 5, 3), "instructions": per})
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--names", nargs="*", default=[]); ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = t0_scores(); chosen = select(t0, set(args.names))
    work = [i for i in C.load_work_items(Path("data/roles/instructions"), Path("data/traits/instructions"))
            if i.polarity == "pos" and (i.source, i.name) in set(chosen)]
    items_by_key = {(i.source, i.name, i.index): i.text for i in work}
    done = set()
    if SAMPLES.exists():
        for line in open(SAMPLES, encoding="utf-8"):
            r = json.loads(line)
            if r["classification"] is not None and items_by_key.get((r["source"], r["name"], r["index"])) == r["text"]:
                done.add((r["source"], r["name"], r["index"], r["sample"]))
    todo = [i for i in work if any((i.source, i.name, i.index, k) not in done for k in range(1, N_EXTRA + 1))]
    n_calls = sum(1 for i in todo for k in range(1, N_EXTRA + 1) if (i.source, i.name, i.index, k) not in done)
    est = C.estimate_cost_usd(n_calls, MODEL, batch=False)
    print(f"{len(chosen)} items ({sum(s == 'role' for s, _ in chosen)} roles, {sum(s == 'trait' for s, _ in chosen)} traits), "
          f"{len(work)} instructions, {n_calls} calls to make, estimate ${est:.2f} real time")
    if args.dry_run:
        return
    if est > 20:
        raise SystemExit("estimate over $20: quote it to Roger first")
    load_dotenv(Path(os.getcwd()) / ".env")
    usage = MultiModelUsage()
    try:
        # only the (instruction, sample) pairs not yet on file, so a rerun after a stop resumes
        fails = asyncio.run(run_pending(todo, done, usage))
    finally:
        prev = MultiModelUsage.load_or_create(USAGE); prev.merge_from(usage); prev.write_json(USAGE)
        cum = MultiModelUsage.load_or_create(CUMULATIVE_USAGE); cum.merge_from(usage); cum.write_json(CUMULATIVE_USAGE)
        print(usage.log_line("[usage]"))
    print(f"failed calls: {fails}")
    summary = summarize(t0, chosen, items_by_key)
    SUMMARY.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for src in ("role", "trait"):
        rows = [s for s in summary if s["source"] == src]
        print(f"{src}s: {sum(s['qualifies'] for s in rows)} of {len(rows)} qualify; incomplete {sum(not s['complete'] for s in rows)}")


async def run_pending(items, done, usage):
    client = __import__("anthropic").AsyncAnthropic()
    limiter = C.RateLimiter(10); sem = asyncio.Semaphore(20); fails = 0

    async def one(item, k):
        nonlocal fails
        async with sem:
            r = await C.classify_single(client, item, MODEL, limiter, temperature=TEMPERATURE, usage=usage)
        if r is None:
            fails += 1
        with open(SAMPLES, "a", encoding="utf-8") as f:
            f.write(json.dumps({"name": item.name, "source": item.source, "polarity": item.polarity, "index": item.index,
                                "sample": k, "model": MODEL, "temperature": TEMPERATURE, "text": item.text,
                                "classification": r}, ensure_ascii=False) + "\n")
    await asyncio.gather(*(one(it, k) for it in items for k in range(1, N_EXTRA + 1)
                           if (it.source, it.name, it.index, k) not in done))
    return fails


if __name__ == "__main__":
    main()
