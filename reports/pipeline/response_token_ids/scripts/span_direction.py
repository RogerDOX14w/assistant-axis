"""Direction of the span shift and the path shift on the sampled leakers
(follow-up to measurement 4(a) of the response-token-ids sample; Roger,
2026-11-06: "we don't know their actual effect").

For every sampled entity with at least --min_stripped stripped responses:
    o      = v_ids  - v_default        the persona offset (the sample's own default, ids variant)
    d_span = v_turn - v_ids            pooling the leaked thinking in (the span choice)
    d_path = v_ids  - v_text           thinking in the context but not pooled, against cut out
    d_floor = v_text_bs1 - v_text      the padding floor (gamer, thorough only)
and reports, per slot and layer:
  * |d| / |o|: the shift as a fraction of the entity's distance from the default;
  * cos(d, -o): whether the shift points toward the default;
  * the shift along the October assistant axis (default/axis.pt, oriented so
    that the October default is positive): in σ of the October entities'
    projections, and as a fraction of the entity's own offset along it;
  * the fraction of |d|² inside the span of the 61 judged axes (QR of the
    axis units), against 61/5120 for a random direction;
  * pairwise cosines of d across the leakers (a common direction means a shared
    register rather than persona content), with the first principal
    component's share of the energy, and the same for o as a baseline;
  * from axis_projection_shift.json: per judged axis, how many of the leakers
    shift the same way (≥ n-1 of n agreeing, against the chance expectation).
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch


def cosine(a, b):
    return np.einsum("...h,...h->...", a, b) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))


def git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--october", required=True)
    ap.add_argument("--experiments_dir", default="roger/axis_judge_experiments")
    ap.add_argument("--shift_json", default=None, help="analysis/axis_projection_shift.json of the sample")
    ap.add_argument("--cache", default=None, help="npz cache of the October slices (as axis_projection_shift)")
    ap.add_argument("--slots", type=int, nargs="+", default=[0, 6])
    ap.add_argument("--layers", type=int, nargs="+", default=[25, 49])
    ap.add_argument("--min_stripped", type=int, default=10)
    ap.add_argument("--out", required=True, help="output prefix: <out>.json and <out>.txt")
    args = ap.parse_args()
    sample, october = Path(args.sample), Path(args.october)
    sys.path.insert(0, str(sample / "logs"))
    import axis_projection_shift as aps
    slots, layers = list(args.slots), list(args.layers)
    S, L = len(slots), len(layers)
    lines = []

    def say(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        lines.append(s)

    # Stripped counts.
    counts = {}
    for f in sorted((sample / "responses").glob("*.jsonl")):
        n = tot = 0
        for line in open(f):
            r = json.loads(line)
            tot += 1
            n += bool(r["thinking_stripped"])
        counts[f.stem] = (n, tot)
    leakers = [e for e, (n, t) in counts.items() if n >= args.min_stripped]
    say(f"entities with >= {args.min_stripped} stripped responses: " +
        ", ".join(f"{e} ({counts[e][0]})" for e in leakers))

    def vec(variant, stem):
        p = sample / f"vec_{variant}" / f"{stem}.pt"
        return aps.load_slice(p, slots, layers) if p.exists() else None

    V = {v: {e: x for e in counts if (x := vec(v, e)) is not None} for v in ("text", "ids", "turn", "text_bs1")}
    default = V["ids"]["default"]
    H = default.shape[-1]

    # October: the judged axes' units and an orthonormal basis of their span; the assistant axis.
    vecs = aps.load_october(october, slots, layers, Path(args.cache) if args.cache else None, log=say)
    kinds_for_name = {}
    for k in vecs:
        stem, tag = k.rsplit("|", 1)
        kinds_for_name.setdefault(stem, set()).add({"T": "traits", "R": "roles"}[tag])
    axes = aps.discover_axes(Path(args.experiments_dir), kinds_for_name)
    units = []
    for axis_dir, pos, neg, pt in axes:
        pid, _ = aps.resolve_pole(pos, pt, vecs, log=say)
        nid, _ = aps.resolve_pole(neg, pt, vecs, log=say)
        d = vecs[pid] - vecs[nid]
        units.append(d / np.linalg.norm(d, axis=-1, keepdims=True))
    U = np.stack(units)                                            # (A, S, L, H)
    A = U.shape[0]
    Q = np.zeros((S, L, H, A))
    for si in range(S):
        for li in range(L):
            Q[si, li] = np.linalg.qr(U[:, si, li, :].T)[0]
    say(f"{A} judged axes; a random direction has {A / H:.4f} of its energy in their span")

    ax = torch.load(october / "roles" / "axis.pt", map_location="cpu", weights_only=False)
    a = ax["axis"][list(slots)][:, list(layers)].double().numpy()
    a_unit = a / np.linalg.norm(a, axis=-1, keepdims=True)
    meta = ax.get("metadata", {})
    say("assistant axis metadata:", json.dumps({k: (v if isinstance(v, (str, int, float, bool)) or v is None else str(v)[:120])
                                             for k, v in meta.items()}, ensure_ascii=False)[:1500])
    M = np.stack([vecs[n] for n in sorted(vecs)])                  # (N, S, L, H)
    oct_default_p = october / "default" / "vectors" / "default.pt"
    oct_default = aps.load_slice(oct_default_p, slots, layers) if oct_default_p.exists() else default
    say(f"orienting the assistant axis by {'the October default' if oct_default_p.exists() else 'the sample default'}")
    orient = np.sign(np.einsum("slh,slh->sl", oct_default - M.mean(0), a_unit))
    a_unit = a_unit * orient[..., None]
    proj_a = np.einsum("nslh,slh->nsl", M, a_unit)
    std_a = proj_a.std(axis=0, ddof=1)                             # (S, L)
    say("assistant axis: std of the October entities' projections per (slot, layer): " +
        ", ".join(f"s{s} L{l}: {std_a[si, li]:.3f}" for si, s in enumerate(slots) for li, l in enumerate(layers)))

    # Per-entity shifts.
    result = {"sample": str(sample), "october": str(october), "slots": slots, "layers": layers,
              "leakers": leakers, "stripped_counts": {e: counts[e] for e in leakers}, "n_axes": A,
              "random_span_fraction": A / H, "git": git_sha(),
              "produced_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), "entities": {}, "groups": {}}
    kinds = ("span", "path", "floor")
    D = {k: {} for k in kinds}
    O = {}
    for e in leakers:
        O[e] = V["ids"][e] - default
        D["span"][e] = V["turn"][e] - V["ids"][e]
        D["path"][e] = V["ids"][e] - V["text"][e]
        if e in V["text_bs1"]:
            D["floor"][e] = V["text_bs1"][e] - V["text"][e]
    for e in counts:                                               # the floor on non-leakers too (thorough)
        if e in V["text_bs1"] and e not in D["floor"]:
            D["floor"][e] = V["text_bs1"][e] - V["text"][e]
            O[e] = V["ids"][e] - default

    # Step 4 keeps the score-3 responses: how many of each leaker's kept responses are stripped.
    kept = {}
    for e in O:
        kind = aps.KIND_OF[e]
        sc = json.loads((sample / "scores" / kind / f"{e}.json").read_text())
        n_kept = n_kept_str = 0
        for line in open(sample / "responses" / f"{e}.jsonl"):
            r = json.loads(line)
            k = f"{r['label']}_p{r['prompt_index']}_q{r['question_index']}"
            if sc.get(k) == 3:
                n_kept += 1
                n_kept_str += bool(r["thinking_stripped"])
        kept[e] = (n_kept, n_kept_str)
    result["kept_counts"] = kept
    say("kept (score 3) responses, of which stripped: " + ", ".join(f"{e} {kept[e][0]}/{kept[e][1]}" for e in sorted(kept, key=lambda x: -kept[x][1])))

    def describe(d, o):
        """per (S, L): the quantities for one shift vector d with the persona offset o."""
        n_d, n_o = np.linalg.norm(d, axis=-1), np.linalg.norm(o, axis=-1)
        pa = np.einsum("slh,slh->sl", d, a_unit)
        po = np.einsum("slh,slh->sl", -o, a_unit)                  # the entity's offset toward the default along the axis
        qd = np.einsum("slhk,slh->slk", Q, d)
        return {"norm": n_d.tolist(), "norm_over_offset": (n_d / n_o).tolist(),
                "cos_toward_default": cosine(d, -o).tolist(),
                "assistant_axis_shift_sigma": (pa / std_a).tolist(),
                "assistant_axis_shift_frac_of_offset": (pa / po).tolist(),
                "assistant_axis_cos": (pa / n_d).tolist(),
                "judged_span_fraction": ((qd ** 2).sum(-1) / n_d ** 2).tolist()}

    for e in sorted(O):
        ent = {"stripped": counts[e][0], "offset_norm": np.linalg.norm(O[e], axis=-1).tolist(),
               "offset_judged_span_fraction": ((np.einsum("slhk,slh->slk", Q, O[e]) ** 2).sum(-1)
                                               / np.linalg.norm(O[e], axis=-1) ** 2).tolist(),
               "offset_assistant_axis_sigma": (np.einsum("slh,slh->sl", O[e], a_unit) / std_a).tolist()}
        for k in kinds:
            if e in D[k]:
                ent[k] = describe(D[k][e], O[e])
                n_kept, n_kept_str = kept[e]
                ent[k]["per_kept_stripped_response_norm_over_offset"] = (
                    (np.array(ent[k]["norm_over_offset"]) * n_kept / n_kept_str).tolist() if n_kept_str else None)
        if e in D["span"] and e in D["path"]:
            ent["cos_span_path"] = cosine(D["span"][e], D["path"][e]).tolist()
        if e in D["span"] and e in D["floor"]:
            ent["cos_span_floor"] = cosine(D["span"][e], D["floor"][e]).tolist()
            ent["cos_path_floor"] = cosine(D["path"][e], D["floor"][e]).tolist()
        result["entities"][e] = ent

    # Tables.
    for si, s in enumerate(slots):
        for li, l in enumerate(layers):
            say(f"\n=== slot {s}, layer {l} ===")
            say(f"{'entity':26} {'n_str':>5} {'kind':5} {'|d|/|o|':>8} {'per resp':>8} {'cos->def':>8} {'ax σ':>7} {'ax %off':>8} "
                f"{'ax cos':>7} {'span%':>6} {'offset σ':>9}")
            for e in sorted(O, key=lambda x: -counts[x][0]):
                ent = result["entities"][e]
                for k in kinds:
                    if k not in ent:
                        continue
                    q = ent[k]
                    pr = q.get("per_kept_stripped_response_norm_over_offset")
                    say(f"{e:26} {counts[e][0]:5d} {k:5} {q['norm_over_offset'][si][li]:8.4f} "
                        f"{(pr[si][li] if pr else float('nan')):8.3f} "
                        f"{q['cos_toward_default'][si][li]:8.3f} {q['assistant_axis_shift_sigma'][si][li]:7.3f} "
                        f"{100 * q['assistant_axis_shift_frac_of_offset'][si][li]:8.2f} {q['assistant_axis_cos'][si][li]:7.3f} "
                        f"{100 * q['judged_span_fraction'][si][li]:6.2f} {ent['offset_assistant_axis_sigma'][si][li]:9.3f}")
            # Group statistics over the leakers.
            g = {}
            for k, label in (("span", "d_span"), ("path", "d_path"), ("offset", "o")):
                X = np.stack([(O if k == "offset" else D[k])[e][si, li] for e in leakers])   # (n, H)
                if (np.linalg.norm(X, axis=-1) == 0).any():
                    say(f"  {label:7}: zero at this slot for some leakers (the span choice does not touch the header slots); skipped")
                    continue
                Xn = X / np.linalg.norm(X, axis=-1, keepdims=True)
                C = Xn @ Xn.T
                off = C[~np.eye(len(leakers), dtype=bool)]
                sv = np.linalg.svd(Xn, compute_uv=False)
                mean_dir_energy = float(np.linalg.norm(Xn.mean(0)) ** 2)   # 1/n + (n-1)/n * mean cos
                jsf = [result["entities"][e]["offset_judged_span_fraction"][si][li] if k == "offset"
                       else result["entities"][e][k]["judged_span_fraction"][si][li] for e in leakers]
                jsf_med = float(np.median(jsf))
                g[label] = {"pairwise_cos_mean": float(off.mean()), "pairwise_cos_min": float(off.min()),
                            "pairwise_cos_max": float(off.max()), "pc1_energy_share": float(sv[0] ** 2 / (sv ** 2).sum()),
                            "mean_direction_energy": mean_dir_energy,
                            "judged_span_fraction_median": jsf_med}
                say(f"  {label:7} across {len(leakers)} leakers: pairwise cos mean {off.mean():.3f} (min {off.min():.3f}, max {off.max():.3f}); "
                    f"PC1 energy share {sv[0] ** 2 / (sv ** 2).sum():.3f} (1/n = {1 / len(leakers):.3f}); "
                    f"judged-span fraction median {100 * g[label]['judged_span_fraction_median']:.2f}%")
            # cross-cosines span vs path per entity
            csp = [result["entities"][e]["cos_span_path"][si][li] for e in leakers]
            g["cos_span_path_median"] = float(np.median(csp))
            say(f"  cos(d_span, d_path) per leaker: median {np.median(csp):.3f}, range {min(csp):.3f} to {max(csp):.3f}")
            for e in leakers:
                if "cos_span_floor" in result["entities"][e]:
                    say(f"  {e}: cos(d_span, d_floor) {result['entities'][e]['cos_span_floor'][si][li]:.3f}, "
                        f"cos(d_path, d_floor) {result['entities'][e]['cos_path_floor'][si][li]:.3f}")
            toward = [result["entities"][e]["span"]["cos_toward_default"][si][li] for e in leakers]
            axs = [result["entities"][e]["span"]["assistant_axis_shift_sigma"][si][li] for e in leakers]
            axf = [100 * result["entities"][e]["span"]["assistant_axis_shift_frac_of_offset"][si][li] for e in leakers]
            g["span_cos_toward_default_median"] = float(np.median(toward))
            g["span_assistant_axis_sigma_median"] = float(np.median(axs))
            g["span_assistant_axis_frac_of_offset_median_pct"] = float(np.median(axf))
            say(f"  d_span: cos toward default median {np.median(toward):.3f} ({sum(t > 0 for t in toward)} of {len(toward)} positive); "
                f"assistant-axis shift median {np.median(axs):+.3f} σ, {np.median(axf):+.2f}% of the entity's own offset "
                f"({sum(x > 0 for x in axs)} of {len(axs)} toward the assistant)")
            towardp = [result["entities"][e]["path"]["cos_toward_default"][si][li] for e in leakers]
            axsp = [result["entities"][e]["path"]["assistant_axis_shift_sigma"][si][li] for e in leakers]
            say(f"  d_path: cos toward default median {np.median(towardp):.3f} ({sum(t > 0 for t in towardp)} of {len(towardp)} positive); "
                f"assistant-axis shift median {np.median(axsp):+.3f} σ ({sum(x > 0 for x in axsp)} of {len(axsp)} toward the assistant)")
            result["groups"][f"s{s}_L{l}"] = g

    # Sign consistency of the judged-axis shifts across the leakers.
    if args.shift_json:
        sh = json.loads(Path(args.shift_json).read_text())
        sl, ly = sh["slots"], sh["layers"]
        n = len(leakers)
        p_agree = 2 * (1 + n) / 2 ** n                              # P(>= n-1 of n share a sign) under independent fair signs
        say(f"\n=== sign agreement of the per-axis shifts across the {n} leakers (from {args.shift_json}) ===")
        say(f"chance: an axis has >= {n - 1} of {n} shifts of one sign with probability {p_agree:.3f}, "
            f"so {p_agree * len(sh['axes']):.1f} of {len(sh['axes'])} axes")
        result["sign_agreement"] = {}
        for pair, label in (("ids-turn", "d_span"), ("text-ids", "d_path")):
            arr = np.stack([np.array(sh["entities"][e]["shifts"][pair]) for e in leakers])   # (n, A, S', L')
            for si, s in enumerate(sl):
                for li, l in enumerate(ly):
                    x = arr[:, :, si, li]
                    pos = (x > 0).sum(0)
                    agree = np.maximum(pos, n - pos)
                    n_ge = int((agree >= n - 1).sum())
                    m = x.mean(0)
                    top = np.argsort(-np.abs(m))[:5]
                    key = f"{label}_s{s}_L{l}"
                    result["sign_agreement"][key] = {"axes_with_agreement": n_ge, "expected": p_agree * x.shape[1],
                                                     "mean_abs_of_mean_shift": float(np.abs(m).mean()),
                                                     "mean_abs_shift": float(np.abs(x).mean()),
                                                     "top_mean_shifts": [(sh["axes"][k], float(m[k]), int(agree[k])) for k in top]}
                    say(f"  {label} s{s} L{l}: {n_ge} axes with >= {n - 1} of {n} agreeing (chance {p_agree * x.shape[1]:.1f}); "
                        f"|mean shift| over axes {np.abs(m).mean():.4f} σ against mean |shift| {np.abs(x).mean():.4f} σ; "
                        "largest mean shifts: " + ", ".join(f"{sh['axes'][k]} {m[k]:+.3f} ({agree[k]}/{n})" for k in top))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result) + "\n")
    out.with_suffix(".txt").write_text("\n".join(lines) + "\n")
    say(f"wrote {out.with_suffix('.json')} and {out.with_suffix('.txt')}")


if __name__ == "__main__":
    main()
