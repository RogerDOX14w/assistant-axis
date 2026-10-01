"""Scores the three parts of the Sonnet 4.6 against Sonnet 5.5 check from their records.  No API
call.  Prints the tables and writes summary.json beside this file.

    uv run python reports/trait_gap_generation/probe_sonnet_move/score.py
"""
import json, re, statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parent
OLD, NEW = "claude-sonnet-4-6", "claude-sonnet-5-5"


def jl(p):
    return [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]


def part_a() -> dict:
    truth = json.loads((HERE / "ground_truth.json").read_text(encoding="utf-8"))
    haiku = {r["word"]: r for r in jl(P / "split_reference" / "expected_outcomes.jsonl")}
    got = {"haiku": haiku, "old": {r["word"]: r for r in jl(HERE / "path" / f"results_{OLD}.jsonl")},
           "new": {r["word"]: r for r in jl(HERE / "path" / f"results_{NEW}.jsonl")}}
    right = {m: {w: got[m][w]["outcome"] in t["expected"] for w, t in truth.items()} for m in got}
    groups = ["sample_passed_v4", "plain_traits", "figurative_person_words", "corpus_relational", "roger_examples_things", "things_held_out"]
    print("\n== Part A: where each model's path sends a word, against the expected answer")
    print("| group | words scored | Haiku 4.5 right | Sonnet 4.6 right | Sonnet 5.5 right |\n|---|---|---|---|---|")
    table = {}
    for g in groups + ["all"]:
        ws = [w for w, t in truth.items() if g == "all" or t["group"] == g]
        table[g] = {"n": len(ws), **{m: sum(right[m][w] for w in ws) for m in got}}
        print(f"| {g} | {len(ws)} | {table[g]['haiku']} | {table[g]['old']} | {table[g]['new']} |")
    disc = {"new_right_old_wrong": sorted(w for w in truth if right["new"][w] and not right["old"][w]),
            "old_right_new_wrong": sorted(w for w in truth if right["old"][w] and not right["new"][w]),
            "both_wrong": sorted(w for w in truth if not right["old"][w] and not right["new"][w])}
    for k, ws in disc.items():
        print(f"\n{k} ({len(ws)}):")
        for w in ws:
            print(f"  {w}: expected {truth[w]['expected']} | haiku {haiku[w]['outcome']} | 4.6 {got['old'][w]['outcome']} ({got['old'][w].get('cause') or got['old'][w].get('accepted')})"
                  f" | 5.5 {got['new'][w]['outcome']} ({got['new'][w].get('cause') or got['new'][w].get('accepted')})")
    allw = list(haiku)
    agree = {m: sum(got[m][w]["outcome"] == haiku[w]["outcome"] for w in allw) for m in ("old", "new")}
    agree["old_new"] = sum(got["old"][w]["outcome"] == got["new"][w]["outcome"] for w in allw)
    print(f"\nsame outcome as Haiku, all {len(allw)} words: 4.6 {agree['old']}, 5.5 {agree['new']}; 4.6 and 5.5 agree on {agree['old_new']}")
    outc = {m: dict(Counter(got[m][w]["outcome"] for w in allw)) for m in got}
    print("outcomes:", outc)
    notes = {m: dict(Counter(n for w in allw for n in got[m][w].get("notes") or [])) for m in got}
    print("notes:", notes)
    things = [w for w, t in truth.items() if t["group"] in ("roger_examples_things", "things_held_out")]
    print("words for things:", {w: (got["old"][w]["outcome"], got["new"][w]["outcome"], haiku[w]["outcome"]) for w in things})
    unscored = sorted(w for w in allw if w not in truth)
    print("not scored (4.6, 5.5, Haiku):", {w: (got["old"][w]["outcome"], got["new"][w]["outcome"], haiku[w]["outcome"]) for w in unscored})
    return {"table": table, "discordant": disc, "agreement_with_haiku": agree, "outcomes": outc, "notes": notes}


HEDGE = re.compile(r"\b(tends? to|sometimes|may|can|overly|too|appropriately|exhibits?|demonstrates?|engag\w+ in|individuals who|the user)\b", re.I)
SUBJ = re.compile(r"\b(you|your|yours|yourself|i|my|me|the persona)\b", re.I)
ING = re.compile(r"This means \w+ing\b")


def part_b() -> dict:
    rows = jl(HERE / "gloss" / "results.jsonl")
    print("\n== Part B: the gloss")
    print("| check on the 74 glosses | Haiku 4.5 | Sonnet 4.6 | Sonnet 5.5 |\n|---|---|---|---|")
    mech = {}
    for name, f in (("open This means and an -ing verb", lambda g, r: bool(ING.match(g))),
                    ("address the persona", lambda g, r: bool(SUBJ.search(g))),
                    ("use a word the rules forbid", lambda g, r: bool(HEDGE.search(g))),
                    ("repeat the label in the first five words", lambda g, r: r["word"].lower() in " ".join(g.split()[:5]).lower()),
                    ("more than one sentence", lambda g, r: len(re.findall(r"[.!?](\s|$)", g.strip())) > 1),
                    ("inside 18 to 32 words", lambda g, r: 18 <= len(g.split()) <= 32)):
        mech[name] = {m: sum(f(r[m], r) for r in rows) for m in ("haiku", "old", "new")}
        print(f"| {name} | {mech[name]['haiku']} | {mech[name]['old']} | {mech[name]['new']} |")
    med = {m: statistics.median(len(r[m].split()) for r in rows) for m in ("haiku", "old", "new")}
    print(f"| words, median | {med['haiku']} | {med['old']} | {med['new']} |")
    votes = Counter(j["winner"] for r in rows for j in r.get("judged", []))
    per = Counter()
    for r in rows:
        ws = [j["winner"] for j in r.get("judged", [])]
        per["new in both orders" if ws == ["new", "new"] else "old in both orders" if ws == ["old", "old"] else
            "tie in both orders" if ws == ["tie", "tie"] else "the two orders disagree"] += 1
    first = Counter(j["better"] for r in rows for j in r.get("judged", []))
    print("\nthe judge's 148 votes:", dict(votes), "| by letter:", dict(first))
    print("by word:", dict(per))
    for k in ("old in both orders",):
        for r in rows:
            if [j["winner"] for j in r.get("judged", [])] == ["old", "old"]:
                print(f"  4.6 preferred: {r['word']}\n     4.6: {r['old']}\n     5.5: {r['new']}\n     why: {r['judged'][0]['reason']}")
    return {"mechanical": mech, "median_words": med, "votes": dict(votes), "by_word": dict(per), "by_letter": dict(first)}


def part_c() -> dict:
    out = {}
    print("\n== Part C: the comparison call")
    print("| set | rows | expected | recorded 4.6, 20 to a call | 4.6, one to a call | 5.5, one to a call |\n|---|---|---|---|---|---|")
    for s in ("dev", "heldout"):
        rows = jl(HERE / f"comparison_{s}" / "results.jsonl")
        for exp in ("same", "different"):
            rs = [r for r in rows if r["expected"] == exp]
            if not rs:
                continue
            k = f"{s}, expected {exp}"
            out[k] = {"n": len(rs), "recorded_batched": sum(r["recorded_batched"] == exp for r in rs),
                      "old": sum((r["old"] or {}).get("relation") == exp for r in rs),
                      "new": sum((r["new"] or {}).get("relation") == exp for r in rs),
                      "answers_old": dict(Counter((r["old"] or {}).get("relation") for r in rs)),
                      "answers_new": dict(Counter((r["new"] or {}).get("relation") for r in rs))}
            print(f"| {s} | {len(rs)} | {exp} | {out[k]['recorded_batched']} | {out[k]['old']} | {out[k]['new']} |")
            print(f"    answers 4.6 {out[k]['answers_old']} | 5.5 {out[k]['answers_new']}")
        for r in rows:
            o, n = (r["old"] or {}).get("relation"), (r["new"] or {}).get("relation")
            if o != n or s == "heldout":
                print(f"  {r['key']}: expected {r['expected']} | recorded {r['recorded_batched']} | 4.6 {o} | 5.5 {n}\n"
                      f"      4.6: {(r['old'] or {}).get('reason')}\n      5.5: {(r['new'] or {}).get('reason')}")
    return out


def cost() -> dict:
    out = {}
    for d in ("path", "gloss", "comparison_dev", "comparison_heldout"):
        u = json.loads((HERE / d / "usage.json").read_text(encoding="utf-8"))
        out[d] = {"usd": u["total_cost_usd"], "calls": u["n_calls"],
                  "per_model": {m: {"usd": v["cost_usd"], "calls": v["n_calls"], "in_per_call": round(v["prompt_tokens"] / v["n_calls"]),
                                    "out_per_call": round(v["completion_tokens"] / v["n_calls"])} for m, v in u["per_model"].items()}}
    print("\n== Cost")
    for d, v in out.items():
        print(d, v)
    print("total", round(sum(v["usd"] for v in out.values()), 3))
    return out


if __name__ == "__main__":
    summary = {"part_a": part_a(), "part_b": part_b(), "part_c": part_c(), "cost": cost()}
    (HERE / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
