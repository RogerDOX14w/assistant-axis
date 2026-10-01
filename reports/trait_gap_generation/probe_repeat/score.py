"""Scores the repeat runs: how often two single runs agree, how often two votes of three agree, and
how each does against the expected answers of probe_sonnet_move/ground_truth.json.  No API call.
Writes summary.json beside this file.

Nine runs of the same 99 words on Haiku 4.5 at temperature 0, one item per call: the probe records
(split_reference/expected_outcomes.jsonl), the two pilots of the platform (split_pilot_live,
split_pilot_batches) and run_1 to run_6 here.

    uv run python reports/trait_gap_generation/probe_repeat/score.py
"""
import itertools, json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parent
FILTER = Path("data/candidates/filter")


def jl(p):
    return [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]


def load_runs() -> dict[str, dict[str, str]]:
    runs = {"probes": {r["word"]: r["outcome"] for r in jl(P / "split_reference" / "expected_outcomes.jsonl")}}
    for name in ("split_pilot_live", "split_pilot_batches"):
        runs[name] = {r["label"]: (r.get("filter") or {}).get("outcome") for r in jl(FILTER / name / "results.jsonl")}
    for d in sorted(HERE.glob("run_*")):
        if (d / "results.jsonl").exists():
            runs[d.name] = {r["word"]: r["outcome"] for r in jl(d / "results.jsonl")}
    return runs


def vote(outs: list[str]) -> str:
    """The outcome most of the runs gave; with no majority, the first run's."""
    c = Counter(outs).most_common()
    return c[0][0] if len(c) == 1 or c[0][1] > c[1][1] else outs[0]


def partitions(names: list[str], size: int):
    """Every way of splitting ``names`` into groups of ``size`` (order of groups ignored)."""
    if not names:
        yield []
        return
    first, rest = names[0], names[1:]
    for others in itertools.combinations(rest, size - 1):
        left = [n for n in rest if n not in others]
        for p in partitions(left, size):
            yield [[first, *others]] + p


def main() -> None:
    runs = load_runs()
    names = list(runs)
    words = list(runs["probes"])
    truth = json.loads((P / "probe_sonnet_move" / "ground_truth.json").read_text(encoding="utf-8"))
    n = len(words)
    print(f"{len(names)} runs: {names}")
    pairs = list(itertools.combinations(names, 2))
    agree = [sum(runs[a][w] == runs[b][w] for w in words) for a, b in pairs]
    single = sum(agree) / len(agree)
    print(f"two single runs agree on {single:.1f} of {n} words on average (lowest {min(agree)}, highest {max(agree)}, {len(pairs)} pairs)")
    modal = {w: Counter(runs[r][w] for r in names).most_common() for w in words}
    steady = [w for w in words if len(modal[w]) == 1]
    print(f"words with the same outcome in every run: {len(steady)} of {n}")
    print("\n| word | outcomes over the runs | expected |\n|---|---|---|")
    for w in words:
        if len(modal[w]) > 1:
            e = truth.get(w, {}).get("expected")
            print(f"| {w} | {', '.join(f'{o} {k}' for o, k in modal[w])} | {' or '.join(e) if e and len(e) < 4 else ('not a trait' if e else 'not scored')} |")
    out = {"runs": names, "single_pair_agreement_mean": round(single, 2), "single_pair_agreement_range": [min(agree), max(agree)],
           "n_words": n, "n_steady": len(steady),
           "unsteady": {w: dict(modal[w]) for w in words if len(modal[w]) > 1}}
    for size in (2, 3):
        usable = names[: len(names) - len(names) % size]
        if len(usable) < 2 * size:
            continue
        vals, acc = [], []
        for part in partitions(usable, size):
            votes = [{w: vote([runs[r][w] for r in grp]) for w in words} for grp in part]
            for a, b in itertools.combinations(votes, 2):
                vals.append(sum(a[w] == b[w] for w in words))
            for v in votes:
                acc.append(sum(v[w] in truth[w]["expected"] for w in truth))
        if size == 2:
            # two runs: a word is "settled" when both agree; how many words would carry the note
            flagged = [sum(runs[a][w] != runs[b][w] for w in words) for a, b in pairs]
            out["two_runs_flag_mean"] = round(sum(flagged) / len(flagged), 2)
            print(f"\nrun twice and note a disagreement: the note would fall on {sum(flagged) / len(flagged):.1f} of {n} words on average")
            continue
        m = sum(vals) / len(vals)
        print(f"\ntwo votes of {size} agree on {m:.1f} of {n} words on average (lowest {min(vals)}, highest {max(vals)})")
        out[f"vote_of_{size}_agreement_mean"] = round(m, 2)
        out[f"vote_of_{size}_agreement_range"] = [min(vals), max(vals)]
        out[f"vote_of_{size}_right_mean"] = round(sum(acc) / len(acc), 2)
    right = [sum(runs[r][w] in truth[w]["expected"] for w in truth) for r in names]
    out["single_right_mean"] = round(sum(right) / len(right), 2)
    out["single_right_by_run"] = dict(zip(names, right))
    print(f"against the expected answers ({len(truth)} words scored): a single run is right on {sum(right) / len(right):.1f} on average "
          f"({min(right)} to {max(right)}); a vote of three on {out.get('vote_of_3_right_mean')}")
    cost = []
    for d in sorted(HERE.glob("run_*")):
        if (d / "usage.json").exists():
            u = json.loads((d / "usage.json").read_text(encoding="utf-8"))
            cost.append((u["total_cost_usd"], u["n_calls"]))
    if cost:
        per = sum(c for c, _ in cost) / len(cost) / n
        out.update(cost_runs_usd=round(sum(c for c, _ in cost), 3), steps_1_to_3_usd_per_word=round(per, 5),
                   calls_per_word=round(sum(k for _, k in cost) / len(cost) / n, 2))
        print(f"\nsteps 1 to 3 cost ${per:.4f} a word ({out['calls_per_word']} calls); the {len(cost)} repeats cost ${sum(c for c, _ in cost):.2f}")
    (HERE / "summary.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
