"""Measurement 4(a) of the response-token-ids sample (plan § 9): each sampled
entity's projection on the judged axes under each step-2 variant, and the
shift between variants in units of the spread of all entities' projections
on that axis.

Axes: every ``<pos>_vs_<neg>`` directory under --experiments_dir that has
``gpt/scores_descriptions.json`` (the 61 judged axes); poles and pair type
from ``gpt/config.json`` (``args.pair``, ``args.pair_type``), as
judge_tier_robustness.discover_axes reads them, else the name split on
``_vs_`` and the kind both poles have in the October tree.  The axis unit is
pos - neg from the October tree's pole vectors (raw, no whitening, as
rho_by_layer._axis_unit).  A pole the corpus has renamed since the axis was
judged is looked up under its current stem (entity_id.resolve_renamed_stem;
the October tree was extracted after the renames) and the substitution is
recorded.  The spread is the standard deviation (and the interquartile
range) of the projections of every October trait and role except the two
poles.  For each sampled entity, each pair of variants, and each variant
against the entity's October vector (the sampling floor: the same entity,
a fresh T = 0.7 sample through today's path):
    shift = (p_b - p_a) / std,   per slot and layer.
A constant offset (the default vector) cancels in a shift and in a spread,
so raw projections are used.

Run locally after the pull:
    uv run python axis_projection_shift.py \
        --sample "runpod_workspace/qwen/qwen-3-32b Roger sample-ids" \
        --october "runpod_workspace/qwen/qwen-3-32b Roger October" \
        --out <prefix> [--cache <npz>] [--slots 0 6] [--layers 25 49]
Writes <out>.json (every projection, spread and shift) and prints, per
entity and pair, the median and the maximum |shift| over the axes at slot 0
(layers 25 and 49, with the axis of the maximum) and the maximum over the
header slots, then the groups' medians of those.  --cache keeps the October
tree's slices in an npz (fingerprinted on the files' names, sizes and
mtimes) so a rerun does not read 13 GB again.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROLES = "gamer child researcher specialist witness operator angel".split()
TRAITS = ("aural_vark plugged_in millennial stream_of_consciousness gen_z thorough verbose "
          "exclusionary autistic flirty").split()
COMBOS = "r_competitor__aural_vark r_rebel__aural_vark".split()
KIND_OF = {**{e: "roles" for e in ROLES}, **{e: "traits" for e in TRAITS},
           **{e: "combinations" for e in COMBOS}, "default": "roles"}
GROUP_OF = {**{e: "heavy leaker" for e in ("gamer aural_vark plugged_in millennial stream_of_consciousness "
                                            "child gen_z r_competitor__aural_vark r_rebel__aural_vark").split()},
            **{e: "cap-heavy" for e in "thorough researcher verbose specialist".split()},
            **{e: "control" for e in "witness operator angel exclusionary autistic flirty".split()},
            "default": "default"}
VARIANTS = ("text", "ids", "turn", "text_bs1")
PAIRS = (("text", "ids"), ("ids", "turn"), ("text", "turn"), ("text", "text_bs1"),
         ("text", "october"), ("ids", "october"), ("turn", "october"))
KIND_TAG = {"traits": "T", "roles": "R"}


def eid(stem: str, kind: str) -> str:
    return f"{stem}|{KIND_TAG[kind]}"


def load_slice(path: Path, slots, layers) -> np.ndarray:
    """(n_slots, n_layers, hidden) float64 at the requested slots and layers.
    float64 because a shift differences two projections that nearly cancel
    (float32 left about 1e-4 relative error on the header slots)."""
    d = torch.load(path, map_location="cpu", weights_only=False)
    t = d["vector"] if isinstance(d, dict) and "vector" in d else d["axis"] if isinstance(d, dict) else d
    return t[list(slots)][:, list(layers)].double().numpy()


def tree_fingerprint(files) -> str:
    h = hashlib.sha256()
    for fp in files:
        st = fp.stat()
        h.update(f"{fp}|{st.st_size}|{int(st.st_mtime)}\n".encode())
    return h.hexdigest()


def load_october(october: Path, slots, layers, cache: Path | None, log=print):
    """{entity id: (S, L, H)} for every trait and role vector but default."""
    files = []
    for kind in ("traits", "roles"):
        files += [(kind, fp) for fp in sorted((october / kind / "vectors").glob("*.pt")) if fp.stem != "default"]
    fp_hash = tree_fingerprint([fp for _, fp in files])
    meta = {"october": str(october), "slots": list(slots), "layers": list(layers), "fingerprint": fp_hash,
            "dtype": "float64"}
    if cache and cache.exists():
        with np.load(cache, allow_pickle=False) as z:
            m = json.loads(str(z["meta"]))
            if m == meta:
                log(f"[october] {len(z['keys'])} entities from the cache {cache}")
                return dict(zip(z["keys"].tolist(), z["arr"]))
            log(f"[october] cache {cache} was built from other files or settings; rebuilding")
    t0 = time.time()
    keys, arrs = [], []
    for i, (kind, fp) in enumerate(files):
        keys.append(eid(fp.stem, kind))
        arrs.append(load_slice(fp, slots, layers))
        if (i + 1) % 200 == 0:
            log(f"[october] {i + 1}/{len(files)} vectors read ({time.time() - t0:.0f} s)")
    arr = np.stack(arrs)
    log(f"[october] {len(keys)} vectors read in {time.time() - t0:.0f} s")
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(cache.stem + ".tmp.npz")
        np.savez(tmp, keys=np.array(keys), arr=arr, meta=np.array(json.dumps(meta)))
        tmp.replace(cache)
        log(f"[october] cached to {cache}")
    return dict(zip(keys, arr))


def unwrap(obj):
    if isinstance(obj, dict) and "result" in obj and set(obj) <= {"result", "_provenance", "schema_version"}:
        return obj["result"]
    return obj


def discover_axes(experiments_dir: Path, kinds_for_name: dict) -> list:
    """[(axis_dir, pos, neg, pair_type)], as judge_tier_robustness.discover_axes."""
    axes = []
    for d in sorted(experiments_dir.iterdir()):
        if not (d / "gpt" / "scores_descriptions.json").exists() or "_vs_" not in d.name:
            continue
        pos, neg = d.name.split("_vs_", 1)
        pair_type = None
        cfg = d / "gpt" / "config.json"
        if cfg.exists():
            args = (unwrap(json.loads(cfg.read_text())) or {}).get("args", {})
            pair = args.get("pair")
            if pair and len(pair) == 2:
                if f"{pair[0]}_vs_{pair[1]}" != d.name:
                    raise ValueError(f"{cfg}: pair {pair} does not match the directory name {d.name!r}")
                pos, neg = pair
            pair_type = args.get("pair_type")
        if pair_type not in ("roles", "traits"):
            common = kinds_for_name.get(pos, set()) & kinds_for_name.get(neg, set())
            if len(common) != 1:
                raise ValueError(f"{d.name}: pair type unknown (no gpt/config.json; the poles' kinds are "
                                 f"{kinds_for_name.get(pos)} and {kinds_for_name.get(neg)})")
            pair_type = next(iter(common))
        axes.append((d.name, pos, neg, pair_type))
    return axes


def resolve_pole(stem: str, kind: str, vecs: dict, log=print) -> tuple:
    """The entity id of the pole's October vector; a renamed pole through
    resolve_renamed_stem.  Returns (entity id, note or None)."""
    if eid(stem, kind) in vecs:
        return eid(stem, kind), None
    from assistant_axis.entity_id import resolve_renamed_stem
    new = resolve_renamed_stem(stem, kind)
    if new != stem and eid(new, kind) in vecs:
        log(f"[axes] pole {stem} ({kind}) is {new} in the corpus now; using its October vector")
        return eid(new, kind), f"{stem} -> {new}"
    raise KeyError(f"no October vector for pole {stem} ({kind}), nor under a renamed stem")


def git_sha(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def summarise(shifts: np.ndarray, axes: list, si: int, li: int):
    """median and max |shift| over axes at (slot index, layer index), and the axis of the max."""
    a = np.abs(shifts[:, si, li])
    k = int(np.nanargmax(a))
    return float(np.nanmedian(a)), float(a[k]), axes[k]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True, help="the pulled sample tree (vec_text, vec_ids, vec_turn, vec_text_bs1)")
    ap.add_argument("--october", required=True, help="the October tree (traits/vectors, roles/vectors, combinations/vectors)")
    ap.add_argument("--experiments_dir", default="roger/axis_judge_experiments")
    ap.add_argument("--slots", type=int, nargs="+", default=[0, 6])
    ap.add_argument("--layers", type=int, nargs="+", default=[25, 49])
    ap.add_argument("--cache", default=None, help="npz cache of the October tree's slices")
    ap.add_argument("--out", required=True, help="output prefix: <out>.json")
    args = ap.parse_args()
    sample, october, exp = Path(args.sample), Path(args.october), Path(args.experiments_dir)
    slots, layers = list(args.slots), list(args.layers)
    S, L = len(slots), len(layers)

    vecs = load_october(october, slots, layers, Path(args.cache) if args.cache else None)
    kinds_for_name = {}
    for k in vecs:
        stem, tag = k.rsplit("|", 1)
        kinds_for_name.setdefault(stem, set()).add({"T": "traits", "R": "roles"}[tag])
    axes = discover_axes(exp, kinds_for_name)
    print(f"[axes] {len(axes)} judged axes under {exp}")

    # Axis units and spreads.
    names = sorted(vecs)
    M = np.stack([vecs[n] for n in names])                       # (N, S, L, H)
    units, spread, renames = {}, {}, {}
    for axis_dir, pos, neg, pair_type in axes:
        pos_id, note_p = resolve_pole(pos, pair_type, vecs)
        neg_id, note_n = resolve_pole(neg, pair_type, vecs)
        if note_p or note_n:
            renames[axis_dir] = [n for n in (note_p, note_n) if n]
        d = vecs[pos_id] - vecs[neg_id]                           # (S, L, H)
        u = d / np.linalg.norm(d, axis=-1, keepdims=True)
        units[axis_dir] = u
        keep = np.array([n not in (pos_id, neg_id) for n in names])
        proj = np.einsum("nslh,slh->nsl", M[keep], u)             # (N-2, S, L)
        q75, q25 = np.percentile(proj, [75, 25], axis=0)
        spread[axis_dir] = {"n": int(keep.sum()), "std": proj.std(axis=0, ddof=1).tolist(),
                            "iqr": (q75 - q25).tolist(), "mean": proj.mean(axis=0).tolist()}

    # The sample's vectors.
    stems = sorted(p.stem for p in (sample / "vec_text").glob("*.pt"))
    if not stems:
        sys.exit(f"no vectors in {sample / 'vec_text'}")
    axis_names = [a[0] for a in axes]
    result = {"sample": str(sample), "october": str(october), "experiments_dir": str(exp),
              "slots": slots, "layers": layers, "axes": axis_names, "pole_renames": renames,
              "spread": spread, "n_october_entities": len(names), "git": git_sha(Path.cwd()),
              "produced_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()), "entities": {}}
    hdr = (f"{'entity':26} {'group':13} {'pair':16} {'s0 L25 med':>10} {'max':>7} {'axis of max':30} "
           f"{'s0 L49 med':>10} {'max':>7} {'hdr max':>8}")
    print(hdr)
    rows_for_groups = {}
    for stem in stems:
        kind = KIND_OF.get(stem)
        if kind is None:
            print(f"{stem}: not in the sample's entity lists; skipped", file=sys.stderr)
            continue
        variants = {}
        for v in VARIANTS:
            p = sample / f"vec_{v}" / f"{stem}.pt"
            if p.exists():
                variants[v] = load_slice(p, slots, layers)
        p_oct = october / kind / "vectors" / f"{stem}.pt"
        if p_oct.exists():
            variants["october"] = load_slice(p_oct, slots, layers)
        else:
            print(f"{stem}: no October vector at {p_oct}", file=sys.stderr)
        proj = {v: {a: np.einsum("slh,slh->sl", vec, units[a]).tolist() for a in axis_names}
                for v, vec in variants.items()}
        ent = {"kind": kind, "group": GROUP_OF.get(stem, "?"), "projections": proj, "shifts": {}, "summary": {}}
        for a_, b_ in PAIRS:
            if a_ not in variants or b_ not in variants:
                continue
            sh = np.stack([(np.array(proj[b_][ax]) - np.array(proj[a_][ax])) / np.array(spread[ax]["std"])
                           for ax in axis_names])                 # (n_axes, S, L)
            pair = f"{a_}-{b_}"
            ent["shifts"][pair] = sh.tolist()
            summ = {}
            for li, Lv in enumerate(layers):
                if 0 in slots:
                    med, mx, ax_mx = summarise(sh, axis_names, slots.index(0), li)
                    summ[f"slot0_L{Lv}"] = {"median_abs": med, "max_abs": mx, "axis_of_max": ax_mx}
            hdr_idx = [i for i, s in enumerate(slots) if s != 0]
            if hdr_idx:
                summ["header_max_abs"] = float(np.nanmax(np.abs(sh[:, hdr_idx, :])))
            ent["summary"][pair] = summ
            rows_for_groups.setdefault(pair, {}).setdefault(ent["group"], []).append(summ)
            l25 = summ.get(f"slot0_L{layers[0]}", {}); l49 = summ.get(f"slot0_L{layers[1]}", {}) if L > 1 else {}
            print(f"{stem:26} {ent['group']:13} {pair:16} {l25.get('median_abs', float('nan')):10.4f} "
                  f"{l25.get('max_abs', float('nan')):7.3f} {str(l25.get('axis_of_max', ''))[:30]:30} "
                  f"{l49.get('median_abs', float('nan')):10.4f} {l49.get('max_abs', float('nan')):7.3f} "
                  f"{summ.get('header_max_abs', float('nan')):8.4f}")
        result["entities"][stem] = ent
    print(f"\ngroup medians of the per-entity median and max |shift| at slot 0 (layers {layers[:2]}):")
    groups_summary = {}
    for pair, by_group in rows_for_groups.items():
        for g, rows in sorted(by_group.items()):
            row = {"n": len(rows)}
            for Lv in layers[:2]:
                k = f"slot0_L{Lv}"
                if all(k in r for r in rows):
                    row[f"{k}_median_of_medians"] = float(np.median([r[k]["median_abs"] for r in rows]))
                    row[f"{k}_median_of_max"] = float(np.median([r[k]["max_abs"] for r in rows]))
                    row[f"{k}_max_of_max"] = float(np.max([r[k]["max_abs"] for r in rows]))
            if all("header_max_abs" in r for r in rows):
                row["header_max_of_max"] = float(np.max([r["header_max_abs"] for r in rows]))
            groups_summary.setdefault(pair, {})[g] = row
            cells = " ".join(f"L{Lv}: med {row.get(f'slot0_L{Lv}_median_of_medians', float('nan')):.4f} "
                             f"max-med {row.get(f'slot0_L{Lv}_median_of_max', float('nan')):.3f} "
                             f"max {row.get(f'slot0_L{Lv}_max_of_max', float('nan')):.3f}" for Lv in layers[:2])
            print(f"  {pair:16} {g:13} n={row['n']:2}  {cells}  header max {row.get('header_max_of_max', float('nan')):.4f}")
    result["groups"] = groups_summary
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result) + "\n")
    print(f"wrote {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
