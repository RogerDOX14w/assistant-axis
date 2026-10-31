"""Build the combination re-check sample (2026-10-30) from October step-1 response files: the first r_
combination files generated at the 1024 cap under the October instructions, copied from the pod to
runpod_workspace/pods/rcomb_sample/ by the Runpod session.  Per combination, up to --per responses (60, the
exploration's size per combination) chosen at random, written three ways for step 3 as the exploration's sample
was (../explore/build_sample.py): as the combination (one directory, every stem), as the role alone and as the
trait alone (a directory per combination, since several combinations share a role or a trait).  Step 1 at the
cap writes finish_reason, so nothing is backfilled; a file without it is refused.  The choice is seeded per
stem, so a rerun after more files arrive rewrites the earlier stems' files unchanged and step 3 resumes.

    uv run python build_sample.py runpod_workspace/pods/rcomb_sample
    uv run python build_sample.py runpod_workspace/pods/rcomb_sample --per 60 --out runpod_workspace/combo_recheck

Then ./run_judging.sh (about $1 of gpt-5.6-luna on Flex) and analyze.py.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEEP_RATES = HERE.parent / "explore" / "keep_rates.json"   # the May keep rates, for the stems May also had
ROLES = Path("data/roles/instructions")
TRAITS = Path("data/traits/instructions")
REQUIRED = ("label", "prompt_index", "question_index", "question", "conversation", "finish_reason")
STEM = re.compile(r"^([rt])_(.+?)__(.+)$")


def key_of(rec):
    return f"{rec['label']}_p{rec['prompt_index']}_q{rec['question_index']}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("responses_dir", type=Path, help="step 1's combination response files (<stem>.jsonl)")
    ap.add_argument("--per", type=int, default=60, help="responses per combination (default 60)")
    ap.add_argument("--out", type=Path, default=Path("runpod_workspace/combo_recheck"))
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    may = {r["stem"]: r for r in json.load(open(KEEP_RATES))} if KEEP_RATES.exists() else {}
    files = sorted(a.responses_dir.glob("*.jsonl"))
    if not files:
        sys.exit(f"no .jsonl files under {a.responses_dir}")
    manifest = {"source": str(a.responses_dir), "per_combination": a.per, "seed": a.seed, "combinations": {}}
    total = 0
    for f in files:
        m = STEM.match(f.stem)
        if not m:
            print(f"skip {f.name}: not a combination stem (r_<role>__<trait> or t_<role>__<trait>)")
            continue
        kind, role, trait = m.groups()
        missing = [str(p) for p in (ROLES / f"{role}.json", TRAITS / f"{trait}.json") if not p.exists()]
        if missing:
            print(f"skip {f.stem}: no corpus file {missing}")
            continue
        recs = [json.loads(line) for line in f.read_text().splitlines() if line.strip()]
        if not recs:
            print(f"skip {f.stem}: empty")
            continue
        lacking = [k for k in REQUIRED if any(k not in r for r in recs)]
        if lacking:
            sys.exit(f"{f}: records lack {lacking}; step 1 writes finish_reason since 2026-10-28, so this is not "
                     f"a file from the October run at the cap (nothing is backfilled here)")
        recs.sort(key=key_of)
        rng = random.Random(f"{a.seed}:{f.stem}")
        chosen = recs if len(recs) <= a.per else rng.sample(recs, a.per)
        chosen.sort(key=key_of)
        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in chosen)
        for sub, name in (("combo", f.stem), (f"role/{f.stem}", role), (f"trait/{f.stem}", trait)):
            p = a.out / sub / "responses" / f"{name}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        n_cut = sum(r["finish_reason"] == "length" for r in chosen)
        m_ = may.get(f.stem, {})
        manifest["combinations"][f.stem] = {
            "kind": kind, "role": role, "trait": trait, "n": len(chosen), "n_total": len(recs), "n_cut": n_cut,
            "may_keep": m_.get("keep"), "role_alone_may": m_.get("role_keep"), "trait_alone_may": m_.get("trait_keep")}
        total += len(chosen)
        may_s = f"May keep {m_['keep']:.2f} role {m_['role_keep']:.2f} trait {m_['trait_keep']:.2f}" if m_ else "not in May"
        print(f"{f.stem:44s} n {len(chosen):3d} of {len(recs):4d}  cut {n_cut:3d}  {may_s}")
    if not manifest["combinations"]:
        sys.exit("nothing sampled")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "sample.json").write_text(json.dumps(manifest, indent=1))
    print(f"\n{total} responses in {len(manifest['combinations'])} combinations, written under {a.out}")


if __name__ == "__main__":
    main()
