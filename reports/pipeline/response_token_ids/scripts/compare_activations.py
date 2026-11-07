"""Per-response comparison of two activation directories (the response-token-ids
sample, plan § 9 measurement 2; run on the pod, where the activations are).

For every entity whose activation file is in both directories, every
conversation key in both files, every slot and layer: the cosine between the
two slot vectors, the relative difference norm ||a - b|| / ||a||, the relative
norm difference | ||a|| - ||b|| | / ||a||, and whether the two are
bit-identical (bf16 compared as int16).  Each key is classed from its response
record (``--responses_dir``): clean, stripped (a leaked plan was cut), capped
(finish_reason length), range_null (stored ids whose content range is null),
joined with "+" when several apply.

Writes ``<out>.pt``: per entity ``keys``, ``classes`` and the four
``[n_keys, n_slots, n_layers]`` tensors (``cos``, ``rel_diff``, ``rel_norm``,
``same``), plus ``nan`` (either side has a NaN in that slot) and both files'
metadata; and ``<out>.json``: per entity and over all, by class and by slot
group (slot 0, the header slots 1 to 7), the count, the fraction bit-identical,
and the cosine and relative difference quantiles pooled over layers and at
layers 25 and 49.  The console gets the json's headline rows.
"""
import argparse
import json
import sys
from pathlib import Path

import torch

HEADLINE_LAYERS = (25, 49)


def classify(resp: dict) -> str:
    cls = []
    if resp.get("thinking_stripped"):
        cls.append("stripped")
    if resp.get("finish_reason") == "length":
        cls.append("capped")
    if resp.get("response_token_ids") is not None and resp.get("content_token_range") is None:
        cls.append("range_null")
    return "+".join(cls) or "clean"


def record_key(resp: dict) -> str:
    return f"{resp.get('label')}_p{resp.get('prompt_index')}_q{resp.get('question_index')}"


def load_classes(responses_dir: Path, stem: str) -> dict:
    f = responses_dir / f"{stem}.jsonl"
    if not f.exists():
        return {}
    out = {}
    with open(f) as fh:
        for line in fh:
            r = json.loads(line)
            out[record_key(r)] = classify(r)
    return out


def as_bits(t: torch.Tensor) -> torch.Tensor:
    return t.view(torch.int16) if t.dtype == torch.bfloat16 else t


def compare_entity(path_a: Path, path_b: Path, classes: dict) -> dict:
    a = torch.load(path_a, map_location="cpu", weights_only=False)
    b = torch.load(path_b, map_location="cpu", weights_only=False)
    meta_a, meta_b = a.pop("metadata", None), b.pop("metadata", None)
    keys = sorted(set(a) & set(b))
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    cos, rel_diff, rel_norm, same, nan = [], [], [], [], []
    for k in keys:
        x, y = a[k], b[k]
        if x.shape != y.shape:
            raise SystemExit(f"{path_a.stem}: key {k}: shapes differ {tuple(x.shape)} vs {tuple(y.shape)}")
        same.append((as_bits(x) == as_bits(y)).all(dim=-1))
        xf, yf = x.float(), y.float()
        nan.append(torch.isnan(xf).any(dim=-1) | torch.isnan(yf).any(dim=-1))
        nx, ny = xf.norm(dim=-1), yf.norm(dim=-1)
        cos.append((xf * yf).sum(dim=-1) / (nx * ny))
        rel_diff.append((xf - yf).norm(dim=-1) / nx)
        rel_norm.append((nx - ny).abs() / nx)
    stack = lambda lst: torch.stack(lst) if lst else torch.zeros(0)
    return {
        "keys": keys, "classes": [classes.get(k, "unknown") for k in keys],
        "only_a": only_a, "only_b": only_b,
        "cos": stack(cos), "rel_diff": stack(rel_diff), "rel_norm": stack(rel_norm),
        "same": stack(same), "nan": stack(nan),
        "metadata_a": meta_a, "metadata_b": meta_b,
    }


def quantiles(t: torch.Tensor) -> dict:
    t = t[~torch.isnan(t)]
    if t.numel() == 0:
        return {}
    q = torch.quantile(t, torch.tensor([0.0, 0.01, 0.5, 0.99, 1.0]))
    return {"min": q[0].item(), "p01": q[1].item(), "median": q[2].item(), "p99": q[3].item(),
            "max": q[4].item(), "mean": t.mean().item()}


def summarise(groups: dict, layers: list) -> dict:
    """``groups``: {(entity-or-'all', class-or-'all', slot group): list of per-key
    [n_slots_in_group, n_layers] tensors for cos, rel_diff, rel_norm, same}."""
    out = {}
    for (ent, cls, grp), lists in groups.items():
        c = torch.cat(lists["cos"]); d = torch.cat(lists["rel_diff"])
        n = torch.cat(lists["rel_norm"]); s = torch.cat(lists["same"])
        row = {"n_keys": lists["n_keys"], "n_cells": int(s.numel()),
               "frac_bit_identical": s.float().mean().item(),
               "cos_all_layers": quantiles(c), "rel_diff_all_layers": quantiles(d),
               "rel_norm_all_layers": quantiles(n)}
        for L in HEADLINE_LAYERS:
            if L in layers:
                i = layers.index(L)
                row[f"cos_layer{L}"] = quantiles(c[:, i])
                row[f"rel_diff_layer{L}"] = quantiles(d[:, i])
                row[f"frac_bit_identical_layer{L}"] = s[:, i].float().mean().item()
        out.setdefault(ent, {}).setdefault(cls, {})[grp] = row
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir_a"); ap.add_argument("dir_b")
    ap.add_argument("--out", required=True, help="output prefix: <out>.pt and <out>.json")
    ap.add_argument("--responses_dir", required=True, help="the responses the activations came from")
    ap.add_argument("--entities", nargs="*", default=None, help="only these stems")
    args = ap.parse_args()
    dir_a, dir_b, responses_dir = Path(args.dir_a), Path(args.dir_b), Path(args.responses_dir)
    stems = sorted(p.stem for p in dir_a.glob("*.pt") if (dir_b / p.name).exists())
    if args.entities:
        stems = [s for s in stems if s in set(args.entities)]
    if not stems:
        raise SystemExit(f"no activation file is in both {dir_a} and {dir_b}")
    print(f"{len(stems)} entities in both: {' '.join(stems)}")
    per_entity, groups, layers = {}, {}, None
    for stem in stems:
        res = compare_entity(dir_a / f"{stem}.pt", dir_b / f"{stem}.pt", load_classes(responses_dir, stem))
        per_entity[stem] = res
        if layers is None:
            layers = list((res["metadata_a"] or {}).get("layers") or range(res["cos"].shape[-1]))
        n_keys = len(res["keys"])
        s0 = res["same"][:, 0, :].float().mean().item() if n_keys else float("nan")
        sh = res["same"][:, 1:, :].float().mean().item() if n_keys and res["same"].shape[1] > 1 else float("nan")
        c0 = res["cos"][:, 0, :]
        c0 = c0[~torch.isnan(c0)] if c0.numel() else c0
        c0_min = c0.min().item() if c0.numel() else float("nan")
        c0_med = c0.median().item() if c0.numel() else float("nan")
        print(f"{stem:28} keys {n_keys:4} (only a {len(res['only_a'])}, only b {len(res['only_b'])}); "
              f"bit-identical: slot 0 {s0:.3f}, header slots {sh:.3f}; slot 0 cosine min {c0_min:.6f} "
              f"median {c0_med:.6f}; nan cells {int(res['nan'].sum())}"
              + (f"; classes {dict(sorted(((c, res['classes'].count(c)) for c in set(res['classes']))))}"))
        for i, k in enumerate(res["keys"]):
            cls = res["classes"][i]
            for grp, sl in (("slot0", slice(0, 1)), ("header", slice(1, None))):
                if res["cos"].shape[1] <= 1 and grp == "header":
                    continue
                for ent in (stem, "all"):
                    for c in (cls, "all"):
                        g = groups.setdefault((ent, c, grp), {"cos": [], "rel_diff": [], "rel_norm": [],
                                                              "same": [], "n_keys": 0})
                        g["cos"].append(res["cos"][i, sl]); g["rel_diff"].append(res["rel_diff"][i, sl])
                        g["rel_norm"].append(res["rel_norm"][i, sl]); g["same"].append(res["same"][i, sl])
                        g["n_keys"] += 1
    summary = summarise(groups, layers)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"dir_a": str(dir_a), "dir_b": str(dir_b), "layers": layers, "entities": per_entity},
               out.with_suffix(".pt"))
    doc = {"dir_a": str(dir_a), "dir_b": str(dir_b), "layers": layers, "entities": stems,
           "headline_layers": list(HEADLINE_LAYERS), "summary": summary}
    out.with_suffix(".json").write_text(json.dumps(doc, indent=1) + "\n")
    print("\nover all entities, slot 0, by class (cosine and relative difference pooled over layers):")
    for cls, grps in sorted(summary.get("all", {}).items()):
        r = grps.get("slot0")
        if r:
            print(f"  {cls:22} n={r['n_keys']:5} bit-identical {r['frac_bit_identical']:.3f}  "
                  f"cos min {r['cos_all_layers'].get('min', float('nan')):.6f} p01 {r['cos_all_layers'].get('p01', float('nan')):.6f} "
                  f"median {r['cos_all_layers'].get('median', float('nan')):.6f}  rel_diff median "
                  f"{r['rel_diff_all_layers'].get('median', float('nan')):.2e} max {r['rel_diff_all_layers'].get('max', float('nan')):.2e}")
    r = summary.get("all", {}).get("all", {}).get("header")
    if r:
        print(f"  header slots (all)     n={r['n_keys']:5} bit-identical {r['frac_bit_identical']:.3f}  "
              f"cos min {r['cos_all_layers'].get('min', float('nan')):.6f}  rel_diff max {r['rel_diff_all_layers'].get('max', float('nan')):.2e}")
    print(f"wrote {out.with_suffix('.pt')} and {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
