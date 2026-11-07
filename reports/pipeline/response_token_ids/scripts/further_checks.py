"""Three checks on the sample that need no judged axes (Roger, 2026-11-06).
1. Per stripped response, the distance between the thinking's mean activation
   and the content's, from the ids-vs-turn comparison at slot 0:
       turn_mean - content_mean = f_t (think_mean - content_mean),  f_t = c0 / c1
   so D = rel_diff / f_t = |think_mean - content_mean| / |content_mean|; against
   the judge's score on the thinking (scores_thinking/) and on the content.
   Also the path effect per response (text vs ids) against the thinking length.
2. The cap alone: among non-stripped responses, the score-3 rate of capped
   (finish_reason length) against uncapped responses, per entity.
3. The two combinations' side scores (role side, trait side) for the thinking
   against the content of the same stripped responses, and the clean baseline.
    uv run python further_checks.py <sample tree> <out prefix>
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

try:
    from scipy.stats import mannwhitneyu, spearmanr
except Exception:  # pragma: no cover
    mannwhitneyu = spearmanr = None

sample, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(sample / "logs"))
from axis_projection_shift import KIND_OF  # noqa: E402

LAYERS = [25, 49]
lines = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def key(r):
    return f"{r['label']}_p{r['prompt_index']}_q{r['question_index']}"


def med(xs):
    return float(np.median(xs)) if len(xs) else float("nan")


def mw(a, b):
    """Mann-Whitney p (two-sided) and the rank-biserial effect, a against b."""
    if mannwhitneyu is None or len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    u = mannwhitneyu(a, b, alternative="two-sided")
    rb = 1 - 2 * u.statistic / (len(a) * len(b))
    return float(u.pvalue), float(rb)


result = {"produced_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), "layers": LAYERS}
responses = {}
for f in sorted((sample / "responses").glob("*.jsonl")):
    responses[f.stem] = [json.loads(l) for l in open(f)]
scores = {e: json.loads((sample / "scores" / KIND_OF[e] / f"{e}.json").read_text()) for e in responses
          if (sample / "scores" / KIND_OF[e] / f"{e}.json").exists()}          # the default has no score file
responses = {e: r for e, r in responses.items() if e in scores}
tscores = {}
for e in responses:
    p = sample / "scores_thinking" / KIND_OF[e] / f"{e}.json"
    if p.exists():
        tscores[e] = json.loads(p.read_text())

# ---- 1. per-response thinking distance against the judge ------------------
say("=== 1. Per stripped response: |think_mean - content_mean| / |content_mean| (D) at slot 0, against the judge ===")
cmp_turn = torch.load(sample / "compare" / "ids_vs_turn.pt", map_location="cpu", weights_only=False)["entities"]
cmp_path = torch.load(sample / "compare" / "text_vs_ids.pt", map_location="cpu", weights_only=False)["entities"]
rows = []     # (entity, key, capped, f_t, n_t, content score, thinking score, {L: (D, cos_turn, rel_path)})
for e, recs in responses.items():
    if e not in tscores:
        continue
    ct, cp = cmp_turn[e], cmp_path[e]
    idx = {k: i for i, k in enumerate(ct["keys"])}
    idxp = {k: i for i, k in enumerate(cp["keys"])}
    for r in recs:
        if not r["thinking_stripped"]:
            continue
        k = key(r)
        if k not in idx or k not in tscores[e] or k not in scores[e]:
            continue
        t0, t1 = r["thinking_token_range"]
        c0, c1 = r["content_token_range"]
        f_t = c0 / c1
        per = {}
        for L in LAYERS:
            rel = float(ct["rel_diff"][idx[k], 0, L])
            per[L] = (rel / f_t, float(ct["cos"][idx[k], 0, L]), float(cp["rel_diff"][idxp[k], 0, L]) if k in idxp else float("nan"))
        rows.append((e, k, r["finish_reason"] == "length", f_t, c0, scores[e][k], tscores[e][k], per))
say(f"{len(rows)} stripped responses with both scores; thinking share of the turn f_t: median {med([r[3] for r in rows]):.2f}, "
    f"range {min(r[3] for r in rows):.2f} to {max(r[3] for r in rows):.2f}")
result["per_response"] = {}
for L in LAYERS:
    say(f"\n--- layer {L} ---")
    D_all = np.array([r[7][L][0] for r in rows]); f_all = np.array([r[3] for r in rows]); nt_all = np.array([r[4] for r in rows])
    rel_path = np.array([r[7][L][2] for r in rows])
    rho_Df = spearmanr(D_all, f_all).correlation if spearmanr else float("nan")
    rho_pn = spearmanr(rel_path, nt_all).correlation if spearmanr else float("nan")
    rho_pf = spearmanr(rel_path, f_all).correlation if spearmanr else float("nan")
    say(f"D over all: median {med(D_all):.3f}, p10 {np.percentile(D_all, 10):.3f}, p90 {np.percentile(D_all, 90):.3f}; "
        f"Spearman(D, f_t) = {rho_Df:+.3f} (D should not depend on the share if the thinking is a fixed register)")
    say(f"path effect per response (text vs ids rel_diff): median {med(rel_path):.3f}; Spearman with thinking tokens {rho_pn:+.3f}, with f_t {rho_pf:+.3f}")
    say(f"{'entity':26} {'n':>3} | {'D think=3':>10} {'n':>3} | {'D think=1':>10} {'n':>3} | {'p':>7} {'rb':>6} | {'cos think=3':>11} {'cos think=1':>11} | {'D cont=3':>9} {'D cont=1':>9}")
    per_entity = {}
    for e in sorted({r[0] for r in rows}, key=lambda x: -sum(1 for r in rows if r[0] == x)):
        rs = [r for r in rows if r[0] == e]
        d3 = [r[7][L][0] for r in rs if r[6] == 3]; d1 = [r[7][L][0] for r in rs if r[6] == 1]
        c3 = [r[7][L][1] for r in rs if r[6] == 3]; c1_ = [r[7][L][1] for r in rs if r[6] == 1]
        dc3 = [r[7][L][0] for r in rs if r[5] == 3]; dc1 = [r[7][L][0] for r in rs if r[5] == 1]
        p, rb = mw(d3, d1)
        per_entity[e] = {"n": len(rs), "D_think3_median": med(d3), "n_think3": len(d3), "D_think1_median": med(d1), "n_think1": len(d1),
                         "mw_p": p, "rank_biserial": rb, "cos_think3_median": med(c3), "cos_think1_median": med(c1_),
                         "D_content3_median": med(dc3), "D_content1_median": med(dc1)}
        say(f"{e:26} {len(rs):3d} | {med(d3):10.3f} {len(d3):3d} | {med(d1):10.3f} {len(d1):3d} | {p:7.3f} {rb:+6.2f} | {med(c3):11.4f} {med(c1_):11.4f} | {med(dc3):9.3f} {med(dc1):9.3f}")
    d3 = [r[7][L][0] for r in rows if r[6] == 3]; d1 = [r[7][L][0] for r in rows if r[6] == 1]
    p, rb = mw(d3, d1)
    say(f"{'all':26} {len(rows):3d} | {med(d3):10.3f} {len(d3):3d} | {med(d1):10.3f} {len(d1):3d} | {p:7.3g} {rb:+6.2f}")
    # The four cells (content, thinking).
    cells = {}
    for cs_, ts_ in ((3, 3), (3, 1), (1, 3), (1, 1)):
        ds = [r[7][L][0] for r in rows if r[5] == cs_ and r[6] == ts_]
        cells[f"content{cs_}_think{ts_}"] = {"n": len(ds), "D_median": med(ds)}
    say("D by (content score, thinking score): " + ", ".join(f"({c[7]}, {c[-1]}) n={v['n']} median {v['D_median']:.3f}" for c, v in cells.items()))
    # Within entity, the thinking-3 against thinking-1 difference as a paired-by-entity sign count.
    signs = [(per_entity[e]["D_think3_median"] < per_entity[e]["D_think1_median"]) for e in per_entity
             if per_entity[e]["n_think3"] >= 3 and per_entity[e]["n_think1"] >= 3]
    say(f"entities (>= 3 in each group) where in-character thinking is closer than out-of-character: {sum(signs)} of {len(signs)}")
    # Capped against uncapped D.
    dcap = [r[7][L][0] for r in rows if r[2]]; dunc = [r[7][L][0] for r in rows if not r[2]]
    say(f"D capped (n={len(dcap)}) median {med(dcap):.3f} against uncapped (n={len(dunc)}) {med(dunc):.3f}")
    result["per_response"][f"L{L}"] = {"entities": per_entity, "cells": cells, "spearman_D_f": float(rho_Df),
                                       "spearman_path_vs_thinking_tokens": float(rho_pn), "all_D_think3": med(d3), "all_D_think1": med(d1),
                                       "all_mw_p": p, "all_rank_biserial": rb, "D_capped": med(dcap), "D_uncapped": med(dunc)}

# ---- 2. the cap alone ----------------------------------------------------------
say("\n=== 2. The cap alone: score-3 rate among non-stripped responses, capped against uncapped ===")
say(f"{'entity':26} {'capped 3-rate':>13} {'n':>4} | {'uncapped 3-rate':>15} {'n':>4} | {'diff':>6}")
cap = {}
pool = Counter()
for e, recs in sorted(responses.items(), key=lambda kv: -sum(1 for r in kv[1] if r['finish_reason'] == 'length' and not r['thinking_stripped'])):
    c3 = cn = u3 = un = 0
    for r in recs:
        if r["thinking_stripped"]:
            continue
        k = key(r)
        if k not in scores[e]:
            continue
        if r["finish_reason"] == "length":
            cn += 1; c3 += scores[e][k] == 3
        else:
            un += 1; u3 += scores[e][k] == 3
    pool["c3"] += c3; pool["cn"] += cn; pool["u3"] += u3; pool["un"] += un
    cap[e] = {"capped_n": cn, "capped_rate3": c3 / cn if cn else None, "uncapped_n": un, "uncapped_rate3": u3 / un if un else None}
    if cn >= 5:
        say(f"{e:26} {c3 / cn:13.2f} {cn:4d} | {u3 / un:15.2f} {un:4d} | {c3 / cn - u3 / un:+6.2f}")
say(f"{'all (pooled)':26} {pool['c3'] / pool['cn']:13.2f} {pool['cn']:4d} | {pool['u3'] / pool['un']:15.2f} {pool['un']:4d} | {pool['c3'] / pool['cn'] - pool['u3'] / pool['un']:+6.2f}")
s3 = Counter()
for e, recs in responses.items():
    for r in recs:
        if r["thinking_stripped"] and key(r) in scores[e]:
            tag = "cap" if r["finish_reason"] == "length" else "unc"
            s3[tag + "_n"] += 1; s3[tag + "_3"] += scores[e][key(r)] == 3
say(f"for comparison, stripped responses' content: capped {s3['cap_3'] / s3['cap_n']:.2f} (n={s3['cap_n']}), uncapped {s3['unc_3'] / s3['unc_n']:.2f} (n={s3['unc_n']})")
result["cap_alone"] = {"entities": cap, "pooled": dict(pool), "stripped": dict(s3)}

# ---- 3. combination sides ------------------------------------------------------
say("\n=== 3. Combinations: role side and trait side, thinking against content (stripped responses), with the clean baseline ===")
result["combination_sides"] = {}
for e in ("r_competitor__aural_vark", "r_rebel__aural_vark"):
    cs = json.loads((sample / "scores" / "combinations" / "_sides" / f"{e}.json").read_text())
    ts = json.loads((sample / "scores_thinking" / "combinations" / "_sides" / f"{e}.json").read_text())
    stripped = {key(r) for r in responses[e] if r["thinking_stripped"]}
    def rates(d, keys):
        ks = [k for k in keys if k in d]
        n = len(ks)
        return {"n": n, "role3": sum(d[k]["role"] == 3 for k in ks) / n, "trait3": sum(d[k]["trait"] == 3 for k in ks) / n,
                "both3": sum(d[k]["role"] == 3 and d[k]["trait"] == 3 for k in ks) / n}
    clean = rates(cs, [k for k in cs if k not in stripped])
    sc = rates(cs, stripped)
    st = rates(ts, stripped)
    xt = Counter((cs[k]["role"], cs[k]["trait"], ts[k]["role"], ts[k]["trait"]) for k in stripped if k in cs and k in ts)
    say(f"{e}: clean responses (n={clean['n']}): role 3 in {clean['role3']:.2f}, trait 3 in {clean['trait3']:.2f}, both {clean['both3']:.2f}")
    say(f"{'':26} stripped content (n={sc['n']}): role {sc['role3']:.2f}, trait {sc['trait3']:.2f}, both {sc['both3']:.2f}")
    say(f"{'':26} stripped thinking (n={st['n']}): role {st['role3']:.2f}, trait {st['trait3']:.2f}, both {st['both3']:.2f}")
    moves = Counter()
    for (cr, ctr, tr, ttr), n in xt.items():
        moves["role " + ("up" if tr > cr else "down" if tr < cr else "same")] += n
        moves["trait " + ("up" if ttr > ctr else "down" if ttr < ctr else "same")] += n
    say(f"{'':26} content -> thinking: " + ", ".join(f"{k} {v}" for k, v in sorted(moves.items())))
    result["combination_sides"][e] = {"clean": clean, "stripped_content": sc, "stripped_thinking": st, "moves": dict(moves)}

out.parent.mkdir(parents=True, exist_ok=True)
out.with_suffix(".json").write_text(json.dumps(result, indent=1) + "\n")
out.with_suffix(".txt").write_text("\n".join(lines) + "\n")
print(f"wrote {out.with_suffix('.json')} and {out.with_suffix('.txt')}")
