"""The judge's scores on the leaked-thinking segments against its scores on
the content of the same responses (both under step 3's judge and rubric).
    uv run python compare_thinking_scores.py <sample tree> <thinking by_type dir> <out prefix>
"""
import collections
import json
import sys
import time
from pathlib import Path

sample, bt, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
lines = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def key(r):
    return f"{r['label']}_p{r['prompt_index']}_q{r['question_index']}"


result = {"produced_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), "entities": {}, "all": {}}
tot = collections.Counter()
tot_capped = collections.Counter()
say(f"{'entity':26} {'kind':13} {'n':>3} | {'content 1/2/3':>14} {'mean':>5} | {'thinking 1/2/3':>15} {'mean':>5} | {'think<cont':>10} {'equal':>5} {'think>cont':>10}")
for kind in ("roles", "traits", "combinations"):
    for f in sorted((bt / kind).glob("*.jsonl")):
        e = f.stem
        recs = [json.loads(l) for l in open(f)]
        cs = json.loads((sample / "scores" / kind / f"{e}.json").read_text())
        ts = json.loads((sample / "scores_thinking" / kind / f"{e}.json").read_text())
        pairs = []
        for r in recs:
            k = key(r)
            if k in cs and k in ts:
                pairs.append((cs[k], ts[k], r["finish_reason"] == "length"))
        if not pairs:
            say(f"{e}: no overlapping keys (content keys like {list(cs)[:2]}, thinking keys like {list(ts)[:2]})")
            continue
        c = collections.Counter(p[0] for p in pairs)
        t = collections.Counter(p[1] for p in pairs)
        xt = collections.Counter((p[0], p[1]) for p in pairs)
        lo = sum(1 for p in pairs if p[1] < p[0]); eq = sum(1 for p in pairs if p[1] == p[0]); hi = sum(1 for p in pairs if p[1] > p[0])
        cm = sum(p[0] for p in pairs) / len(pairs); tm = sum(p[1] for p in pairs) / len(pairs)
        result["entities"][e] = {"kind": kind, "n": len(pairs), "content_counts": dict(c), "thinking_counts": dict(t),
                                 "content_mean": cm, "thinking_mean": tm, "crosstab": {f"{a}->{b}": n for (a, b), n in xt.items()},
                                 "thinking_lower": lo, "equal": eq, "thinking_higher": hi,
                                 "capped": {"n": sum(p[2] for p in pairs),
                                            "thinking_mean": (sum(p[1] for p in pairs if p[2]) / max(1, sum(p[2] for p in pairs))),
                                            "content_mean": (sum(p[0] for p in pairs if p[2]) / max(1, sum(p[2] for p in pairs)))}}
        say(f"{e:26} {kind:13} {len(pairs):3d} | {c[1]:4d}/{c[2]:4d}/{c[3]:4d} {cm:5.2f} | {t[1]:5d}/{t[2]:4d}/{t[3]:4d} {tm:5.2f} | {lo:10d} {eq:5d} {hi:10d}")
        for p in pairs:
            tot[("c", p[0])] += 1; tot[("t", p[1])] += 1; tot[("x", p[0], p[1])] += 1
            tot[("rel", "lo" if p[1] < p[0] else "eq" if p[1] == p[0] else "hi")] += 1
            if p[2]:
                tot_capped[("c", p[0])] += 1; tot_capped[("t", p[1])] += 1
n = sum(v for k, v in tot.items() if k[0] == "c")
say(f"\nall {n} stripped responses: content 1/2/3 = {tot[('c', 1)]}/{tot[('c', 2)]}/{tot[('c', 3)]}; "
    f"thinking 1/2/3 = {tot[('t', 1)]}/{tot[('t', 2)]}/{tot[('t', 3)]}; "
    f"thinking lower than content in {tot[('rel', 'lo')]}, equal {tot[('rel', 'eq')]}, higher {tot[('rel', 'hi')]}")
say("cross-tab content -> thinking: " + ", ".join(f"{a}->{b}: {tot[('x', a, b)]}" for a in (1, 2, 3) for b in (1, 2, 3) if tot[('x', a, b)]))
nc = sum(v for k, v in tot_capped.items() if k[0] == "c")
say(f"capped only ({nc}): content 1/2/3 = {tot_capped[('c', 1)]}/{tot_capped[('c', 2)]}/{tot_capped[('c', 3)]}; "
    f"thinking 1/2/3 = {tot_capped[('t', 1)]}/{tot_capped[('t', 2)]}/{tot_capped[('t', 3)]}")
result["all"] = {"n": n, "content_counts": {s: tot[("c", s)] for s in (1, 2, 3)}, "thinking_counts": {s: tot[("t", s)] for s in (1, 2, 3)},
                 "crosstab": {f"{a}->{b}": tot[("x", a, b)] for a in (1, 2, 3) for b in (1, 2, 3)},
                 "thinking_lower": tot[("rel", "lo")], "equal": tot[("rel", "eq")], "thinking_higher": tot[("rel", "hi")]}
out.parent.mkdir(parents=True, exist_ok=True)
out.with_suffix(".json").write_text(json.dumps(result, indent=1) + "\n")
out.with_suffix(".txt").write_text("\n".join(lines) + "\n")
print(f"wrote {out.with_suffix('.json')} and {out.with_suffix('.txt')}")
