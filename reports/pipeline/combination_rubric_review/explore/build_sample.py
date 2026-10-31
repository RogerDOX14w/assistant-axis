"""Build the combination exploration sample from the May 8slot tree (Roger, 2026-10-30: what is being dropped,
especially for the low-keep traits, and which of three hypotheses each drop fits).  Per chosen combination, up
to 40 responses the May judge dropped and 20 it kept, written three ways for step 3: as the combination (one
directory, every stem), as the role alone and as the trait alone (a directory per combination, since several
combinations share a role or a trait).  finish_reason is backfilled as the trait review did (token count
against the 512 cap, the Qwen3 tokenizer), so step 3 marks a cut response.

    uv run python build_sample.py keep_rates.json
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

from tokenizers import Tokenizer

D = Path("runpod_workspace/qwen/qwen-3-32b Roger 8slot")
OUT = Path("runpod_workspace/combo_explore")
TOKENIZER = Path("data/external/hf/models--Qwen--Qwen3-0.6B/snapshots/c1899de289a04d12100db370d81485cdf75e47ca/"
                 "tokenizer.json")
CAP = 512
N_DROPPED, N_KEPT = 40, 20
rows = {r["stem"]: r for r in json.load(open(sys.argv[1]))}
rng = random.Random(7)

strata = {}
# A: a trait the model resists alone (standalone keep at or under 0.68) with a benign professional role
strata["A_resisted_trait"] = ["t_sommelier__harmful", "t_poet__harmful", "t_psychologist__harmful",
                              "t_lawyer__lustful", "t_marketer__lustful", "t_poet__manipulative"]
for trait in ("destructive", "sociopathic"):
    cands = sorted((r for r in rows.values() if r["trait"] == trait and r["kind"] == "t"), key=lambda r: r["keep"])
    strata["A_resisted_trait"].append(cands[0]["stem"])
# B: pairs that each show alone (standalone keeps over 0.7) but keep under 0.4 together
strata["B_incompatible"] = ["r_zealot__understated", "r_competitor__understated", "r_destroyer__understated",
                            "r_daredevil__understated", "r_prey__quantitative", "r_zealot__pensive"]
# C: ordinary combinations where both are expected: keep 0.6 to 0.9, both standalone keeps at least 0.85
pool = {k: [r["stem"] for r in rows.values() if r["kind"] == k and 0.6 <= r["keep"] <= 0.9
            and r["role_keep"] >= 0.85 and r["trait_keep"] >= 0.85] for k in "rt"}
strata["C_both_expected"] = rng.sample(sorted(pool["r"]), 5) + rng.sample(sorted(pool["t"]), 5)
# D: judge-artefact candidates: a role the May judge dropped alone as a generic assistant (aligned AI,
# altruist) kept with a style trait; an AI role (robot) with a resisted trait
alt = sorted(r["stem"] for r in rows.values() if r["role"] == "altruist" and r["keep"] >= 0.9)
strata["D_judge_artefact"] = ["r_aligned_artificial_intelligence__pensive", alt[0], "t_robot__harmful",
                              "t_robot__lustful"]
for s, stems in strata.items():
    for st in stems:
        assert st in rows, (s, st)

tok = Tokenizer.from_file(str(TOKENIZER))


def key_of(rec):
    return f"{rec['label']}_p{rec['prompt_index']}_q{rec['question_index']}"


def answer(rec):
    return next(m["content"] for m in reversed(rec["conversation"]) if m["role"] == "assistant")


def backfill(rec):
    n = len(tok.encode(answer(rec), add_special_tokens=False).ids)
    rec["finish_reason"] = "length" if n >= CAP else "stop"
    rec["finish_reason_backfilled"] = {"method": "token_count", "cap": CAP, "n_tokens": n,
                                       "tokenizer": str(TOKENIZER), "date": "2026-10-30"}
    return rec


manifest = {"strata": {}, "combinations": {}}
counts = Counter()
for s, stems in strata.items():
    manifest["strata"][s] = stems
    for stem in stems:
        r = rows[stem]
        may = json.loads((D / "combinations" / "scores" / f"{stem}.json").read_text())
        role_sc = json.loads((D / "roles" / "scores" / f"{r['role']}.json").read_text())
        trait_sc = json.loads((D / "traits" / "scores" / f"{r['trait']}.json").read_text())
        dropped = sorted(k for k, v in may.items() if v != 3)
        kept = sorted(k for k, v in may.items() if v == 3)
        if s == "C_both_expected":
            # the drops where both standalone entities were kept on the same question first (the hypothesis-1
            # test), then the rest
            both = [k for k in dropped if role_sc.get(k) == 3 and trait_sc.get(k) == 3]
            other = [k for k in dropped if k not in set(both)]
            pick_d = rng.sample(both, min(25, len(both))) + rng.sample(other, min(N_DROPPED - min(25, len(both)), len(other)))
        else:
            pick_d = rng.sample(dropped, min(N_DROPPED, len(dropped)))
        pick_k = rng.sample(kept, min(N_KEPT, len(kept)))
        chosen = set(pick_d) | set(pick_k)
        recs = []
        for line in (D / "combinations" / "responses" / f"{stem}.jsonl").read_text().splitlines():
            rec = json.loads(line)
            k = key_of(rec)
            if k in chosen:
                rec = backfill(rec)
                rec["explore"] = {"stratum": s, "may_score": may[k], "role_alone": role_sc.get(k),
                                  "trait_alone": trait_sc.get(k)}
                recs.append(rec)
        assert len(recs) == len(chosen), (stem, len(recs), len(chosen))
        text = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in recs)
        for sub, name in (("combo", stem), (f"role/{stem}", r["role"]), (f"trait/{stem}", r["trait"])):
            p = OUT / sub / "responses" / f"{name}.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        n_cut = sum(x["finish_reason"] == "length" for x in recs)
        manifest["combinations"][stem] = {"stratum": s, "role": r["role"], "trait": r["trait"], "n": len(recs),
                                          "n_dropped": len(pick_d), "n_kept": len(pick_k), "n_cut": n_cut,
                                          "may_keep": r["keep"], "role_alone": r["role_keep"],
                                          "trait_alone": r["trait_keep"]}
        counts[s] += len(recs)
        print(f"{s:18s} {stem:44s} n {len(recs):3d} (dropped {len(pick_d):2d}, kept {len(pick_k):2d}, cut {n_cut:2d})  "
              f"May keep {r['keep']:.2f} role {r['role_keep']:.2f} trait {r['trait_keep']:.2f}")
(OUT / "sample.json").write_text(json.dumps(manifest, indent=1))
print(f"\n{sum(counts.values())} responses in {len(manifest['combinations'])} combinations: {dict(counts)}")
print(f"written under {OUT}")
