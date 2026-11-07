"""Measurement 3 of the response-token-ids sample (plan § 9): per entity, the
step-4 vectors of the variants against each other, and against the entity's
October vector (the sampling-noise floor: the same entity, a fresh T = 0.7
sample, today's path), per slot and layer, as cosines; and the sample's axes
(step 5 per variant) against each other.

Run locally after the pull:
    uv run python vector_compare.py --sample "runpod_workspace/qwen/qwen-3-32b Roger sample-ids" \
        --october "runpod_workspace/qwen/qwen-3-32b Roger October" --out <prefix>
Writes <out>.json (every cosine, [8 slots x 64 layers] per entity and pair)
and prints the per-entity table at slot 0 (layers 25 and 49, and the median
over layers) and the header slots' minimum, with the groups' medians.
"""
import argparse
import json
import sys
from pathlib import Path

import torch

ROLES = "gamer child researcher specialist witness operator angel".split()
TRAITS = ("aural_vark plugged_in millennial stream_of_consciousness gen_z thorough verbose "
          "exclusionary autistic flirty").split()
COMBOS = "r_competitor__aural_vark r_rebel__aural_vark".split()
TYPE_OF = {**{e: "roles" for e in ROLES}, **{e: "traits" for e in TRAITS},
           **{e: "combinations" for e in COMBOS}, "default": "default"}
GROUP_OF = {**{e: "heavy leaker" for e in ("gamer aural_vark plugged_in millennial stream_of_consciousness "
                                            "child gen_z r_competitor__aural_vark r_rebel__aural_vark").split()},
            **{e: "cap-heavy" for e in "thorough researcher verbose specialist".split()},
            **{e: "control" for e in "witness operator angel exclusionary autistic flirty".split()},
            "default": "default"}
VARIANTS = ("text", "ids", "turn", "text_bs1")
PAIRS = (("text", "ids"), ("ids", "turn"), ("text", "turn"), ("text", "text_bs1"),
         ("text", "october"), ("ids", "october"), ("turn", "october"))
HEADLINE_LAYERS = (25, 49)


def load_vector(path: Path) -> torch.Tensor:
    d = torch.load(path, map_location="cpu", weights_only=False)
    v = d["vector"] if isinstance(d, dict) and "vector" in d else d["axis"] if isinstance(d, dict) else d
    return v.float()


def cosine(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    return (a * b).sum(-1) / (a.norm(dim=-1) * b.norm(dim=-1))


def fmt(c: torch.Tensor, layers: list) -> str:
    """slot 0 at the headline layers and its median over layers; the header
    slots' minimum over slots and layers."""
    s0 = c[0]
    parts = [f"{s0[layers.index(L)]:.5f}" if L in layers else "  n/a " for L in HEADLINE_LAYERS]
    parts.append(f"{s0.median():.5f}")
    parts.append(f"{c[1:].min():.5f}" if c.shape[0] > 1 else "  n/a ")
    return " ".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--october", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sample, october = Path(args.sample), Path(args.october)
    stems = sorted(p.stem for p in (sample / "vec_text").glob("*.pt"))
    if not stems:
        sys.exit(f"no vectors in {sample / 'vec_text'}")
    layers = None
    result = {"sample": str(sample), "october": str(october), "entities": {}, "axes": {}}
    print(f"{'entity':26} {'group':13} {'pair':16} {'L25':>8} {'L49':>8} {'median':>8} {'hdr min':>8}")
    for stem in stems:
        vecs = {}
        for v in VARIANTS:
            p = sample / f"vec_{v}" / f"{stem}.pt"
            if p.exists():
                vecs[v] = load_vector(p)
        t = TYPE_OF.get(stem)
        if t is None:
            print(f"{stem}: not in the sample's entity lists; skipped", file=sys.stderr)
            continue
        p_oct = october / t / "vectors" / f"{stem}.pt"
        if p_oct.exists():
            vecs["october"] = load_vector(p_oct)
        else:
            print(f"{stem}: no October vector at {p_oct}", file=sys.stderr)
        if layers is None:
            d = torch.load(sample / "vec_text" / f"{stem}.pt", map_location="cpu", weights_only=False)
            layers = list((d.get("metadata") or {}).get("layers") or range(vecs["text"].shape[1]))
        ent = {"type": t, "group": GROUP_OF.get(stem, "?"), "pairs": {}}
        for a, b in PAIRS:
            if a in vecs and b in vecs:
                c = cosine(vecs[a], vecs[b])
                ent["pairs"][f"{a}-{b}"] = c.tolist()
                print(f"{stem:26} {ent['group']:13} {a + '-' + b:16} {fmt(c, layers)}")
        result["entities"][stem] = ent
    # Group medians of slot 0 at the headline layers, per pair.
    print("\ngroup medians, slot 0 (layers 25 and 49) and the header slots' minimum:")
    groups = sorted({e["group"] for e in result["entities"].values()})
    summary = {}
    for pair in [f"{a}-{b}" for a, b in PAIRS]:
        for g in groups:
            cs = [torch.tensor(e["pairs"][pair]) for e in result["entities"].values()
                  if e["group"] == g and pair in e["pairs"]]
            if not cs:
                continue
            st = torch.stack(cs)        # [n, slots, layers]
            row = {"n": len(cs)}
            for L in HEADLINE_LAYERS:
                if L in layers:
                    i = layers.index(L)
                    row[f"slot0_L{L}_median"] = st[:, 0, i].median().item()
                    row[f"slot0_L{L}_min"] = st[:, 0, i].min().item()
            row["header_min"] = st[:, 1:].min().item() if st.shape[1] > 1 else None
            summary.setdefault(pair, {})[g] = row
            print(f"  {pair:16} {g:13} n={row['n']:2}  slot0 L25 median {row.get('slot0_L25_median', float('nan')):.5f} "
                  f"min {row.get('slot0_L25_min', float('nan')):.5f}  L49 median {row.get('slot0_L49_median', float('nan')):.5f} "
                  f"min {row.get('slot0_L49_min', float('nan')):.5f}  header min {row['header_min'] if row['header_min'] is None else round(row['header_min'], 5)}")
    result["summary"] = summary
    # The sample's axes against each other.
    axes = {v: load_vector(sample / f"axis_{v}.pt") for v in ("text", "ids", "turn")
            if (sample / f"axis_{v}.pt").exists()}
    if len(axes) > 1:
        print("\naxes (step 5 per variant), slot 0 at layers 25 and 49, median over layers, header min:")
        for a, b in (("text", "ids"), ("ids", "turn"), ("text", "turn")):
            if a in axes and b in axes:
                c = cosine(axes[a], axes[b])
                result["axes"][f"{a}-{b}"] = c.tolist()
                print(f"  {a + '-' + b:16} {fmt(c, layers)}")
    result["layers"] = layers
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result) + "\n")
    print(f"wrote {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
