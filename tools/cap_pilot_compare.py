#!/usr/bin/env python3
"""Compare the response-length cap pilot's four trees and write its readout.

The pilot (reports/pipeline/plan_max_tokens_pilot.md, walk-through P6,
2026-10-12) runs the 64 entities of reports/pipeline/cap_pilot_entities.json
through steps 1-4 at caps 256, 512, 768 and 1024, one tree per cap
(``<tree>/responses``, ``<tree>/scores``, ``<tree>/vectors``).  This tool reads
the trees and writes the readout (default reports/pipeline/cap_pilot_readout.md,
with the numbers in a ``.json`` beside it) with the plan's measurements:

1. **Truncation share** at each cap, from the responses' ``finish_reason``
   (``"length"``; a field written by step 1 since 2026-10-12).
2. **Judge**: the score-3 share and the mean score at each cap, and the
   paired difference to the reference (1024) run.
3. **Vector**: per slot, the cosine between an entity's vector at each cap
   and at the reference, at ``--layer`` (default 25).  Slot 0 (the mean over
   the response's tokens) moves by content and selection; slots 1-7 (header
   tokens, before the response) by selection alone.  Cosines are given raw
   and **centred** (each cap's vectors minus their mean over the pilot
   entities with a vector at both caps): raw cosines of activation means are
   all close to 1 because every vector shares the model's common direction,
   so the rule below is applied to the centred ones (an implementation
   choice recorded in the readout, for Roger to confirm).  The centring mean
   is over the deciding strata only, so an outlier cannot move the others'
   cosines.
4. **Pair axes**: for each pair of pilot entities (``verbose``/``concise``
   first; then any trait pair recorded in the corpus's ``arrangement``
   field), the cosine of the pair-difference axis at each cap with the
   reference's, slot 0, at ``--layer``.
5. ``verbose``, ``concise`` and their angel combinations reported on their
   own.

**Decision rule** (fixed in the plan, before the pilot): keep 512 if, over
the stratum means (roles, traits, combinations; the outliers do not decide),
the slot-0 cosine between 512 and 1024 is >= 0.99 and the score-3 share moves
by less than 2 points; otherwise take the smallest cap that meets both (768,
else 1024; 256 shows the slope and is not a candidate).

``--repeat CAP=TREE``: a second run at one cap, for the plan's run-sanity
check (slots 1-7 of the same cap across two runs, >= 0.999 expected; a miss
is a broken run, not a cap effect).

No API call, no model; reads only the small outputs (responses, scores,
vectors).  Usage::

    uv run python tools/cap_pilot_compare.py --root roger/cap_pilot
    uv run python tools/cap_pilot_compare.py --trees 256=a 512=b 768=c 1024=d \\
        --output /tmp/readout.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import torch

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ENTITIES = REPO / "reports" / "pipeline" / "cap_pilot_entities.json"
DEFAULT_OUTPUT = REPO / "reports" / "pipeline" / "cap_pilot_readout.md"
CAPS = (256, 512, 768, 1024)
REFERENCE_CAP = 1024
CANDIDATE_CAPS = (512, 768, 1024)
COSINE_MIN = 0.99
SCORE3_SHIFT_MAX = 0.02           # "less than 2 points"
DECIDING_STRATA = ("roles", "traits", "combinations")
OUTLIER_STRATA = ("traits_outliers", "combinations_outliers")
DEFAULT_LAYER = 25


# ---------------------------------------------------------------------------
# Reading a tree
# ---------------------------------------------------------------------------

def truncation_share(responses_file: Path) -> Optional[float]:
    """Share of an entity's responses cut at the cap (``finish_reason ==
    "length"``), over the records that carry the field; None without it."""
    if not responses_file.exists():
        return None
    n = n_len = 0
    with open(responses_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if "finish_reason" not in rec:
                continue
            n += 1
            n_len += rec["finish_reason"] == "length"
    return n_len / n if n else None


def score_stats(scores_file: Path) -> Optional[Dict[str, float]]:
    if not scores_file.exists():
        return None
    scores = [v for v in json.loads(scores_file.read_text()).values() if isinstance(v, int)]
    if not scores:
        return None
    return {"n": len(scores), "share3": sum(s == 3 for s in scores) / len(scores),
            "mean": sum(scores) / len(scores)}


def vector_slice(vector_file: Path, layer: int) -> Optional[torch.Tensor]:
    """``(n_slots, hidden)`` at ``layer``, float64; None when missing."""
    if not vector_file.exists():
        return None
    data = torch.load(vector_file, map_location="cpu", weights_only=False)
    v = data["vector"] if isinstance(data, dict) else data
    if v.ndim == 2:                       # (n_layers, hidden): one slot
        v = v.unsqueeze(0)
    return v[:, layer, :].to(torch.float64)


def _cos(a: torch.Tensor, b: torch.Tensor) -> float:
    mask = ~(torch.isnan(a) | torch.isnan(b))
    a, b = a[mask], b[mask]
    na, nb = a.norm(), b.norm()
    if na == 0 or nb == 0:
        return float("nan")
    return float((a @ b) / (na * nb))


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------

def _mean(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return statistics.fmean(xs) if xs else None


def pairs_among(names: List[str], traits_dir: Path) -> List[tuple]:
    """``verbose``/``concise`` first, then each trait pair recorded in the
    corpus (``arrangement`` kind ``pair``) with both members in ``names``."""
    out = [("verbose", "concise")] if {"verbose", "concise"} <= set(names) else []
    seen = {frozenset(p) for p in out}
    for stem in names:
        f = traits_dir / f"{stem}.json"
        if not f.exists():
            continue
        arr = json.loads(f.read_text()).get("arrangement")
        for a in (arr if isinstance(arr, list) else [arr] if arr else []):
            members = a.get("members") or []
            if a.get("kind") == "pair" and len(members) == 2 and set(members) <= set(names):
                key = frozenset(members)
                if key not in seen:
                    seen.add(key)
                    out.append(tuple(sorted(members)))
    return out


def compare(trees: Dict[int, Path], entities: dict, *, layer: int = DEFAULT_LAYER,
            repeat: Optional[tuple] = None, traits_dir: Path = REPO / "data" / "traits" / "instructions") -> dict:
    if REFERENCE_CAP not in trees:
        raise SystemExit(f"cap_pilot_compare: no tree for the reference cap {REFERENCE_CAP}")
    caps = sorted(trees)
    strata: Dict[str, List[str]] = dict(entities["strata"])
    strata["roles"] = strata.get("roles_narrative", []) + strata.get("roles", [])
    names = entities["all"]

    per: Dict[str, Dict[int, dict]] = {n: {} for n in names}
    slices: Dict[int, Dict[str, torch.Tensor]] = {c: {} for c in caps}
    for c in caps:
        t = trees[c]
        for n in names:
            per[n][c] = {"truncation": truncation_share(t / "responses" / f"{n}.jsonl"),
                         "scores": score_stats(t / "scores" / f"{n}.json")}
            s = vector_slice(t / "vectors" / f"{n}.pt", layer)
            if s is not None:
                slices[c][n] = s

    # Centring: each cap's mean over the deciding entities (not the
    # outliers, which must not move everyone else's cosines) with a vector at
    # that cap and at the reference, the same set on both sides; applied to
    # every entity, the outliers included.
    ref = slices[REFERENCE_CAP]
    deciding = {n for k in DECIDING_STRATA for n in strata.get(k, [])}
    for c in caps:
        basis = [n for n in names if n in deciding and n in slices[c] and n in ref]
        if not basis:
            continue
        m_c = torch.stack([slices[c][n] for n in basis]).mean(0)
        m_r = torch.stack([ref[n] for n in basis]).mean(0)
        for n in [n for n in names if n in slices[c] and n in ref]:
            a, b = slices[c][n], ref[n]
            n_slots = a.shape[0]
            per[n][c]["cos_raw"] = [_cos(a[s], b[s]) for s in range(n_slots)]
            per[n][c]["cos_centred"] = [_cos(a[s] - m_c[s], b[s] - m_r[s]) for s in range(n_slots)]
    for n in names:
        r = per[n][REFERENCE_CAP]["scores"]
        for c in caps:
            s = per[n][c]["scores"]
            if s and r:
                per[n][c]["d_share3"] = s["share3"] - r["share3"]
                per[n][c]["d_mean"] = s["mean"] - r["mean"]

    def stratum_summary(members: List[str]) -> Dict[int, dict]:
        out = {}
        for c in caps:
            rows = [per[n][c] for n in members]
            out[c] = {
                "n": len(members),
                "truncation": _mean(r["truncation"] for r in rows),
                "share3": _mean((r["scores"] or {}).get("share3") for r in rows),
                "mean_score": _mean((r["scores"] or {}).get("mean") for r in rows),
                "d_share3": _mean(r.get("d_share3") for r in rows),
                "d_mean": _mean(r.get("d_mean") for r in rows),
                "cos0_centred": _mean((r.get("cos_centred") or [None])[0] for r in rows),
                "cos0_raw": _mean((r.get("cos_raw") or [None])[0] for r in rows),
                "cos_header_centred": _mean(
                    _mean((r.get("cos_centred") or [None])[1:]) for r in rows),
                "n_vectors": sum(1 for r in rows if r.get("cos_centred")),
            }
        return out

    summaries = {k: stratum_summary(v) for k, v in strata.items() if v}
    summaries["roles_narrative"] = stratum_summary(strata.get("roles_narrative", []))

    def passes(c: int) -> Optional[bool]:
        ok = True
        for k in DECIDING_STRATA:
            s = summaries.get(k, {}).get(c)
            if not s or s["cos0_centred"] is None or s["d_share3"] is None:
                return None
            ok = ok and s["cos0_centred"] >= COSINE_MIN and abs(s["d_share3"]) < SCORE3_SHIFT_MAX
        return ok

    verdicts = {c: passes(c) for c in CANDIDATE_CAPS if c in trees}
    if any(v is None for c, v in verdicts.items() if c != REFERENCE_CAP):
        decision = None
    else:
        decision = next((c for c in CANDIDATE_CAPS if c in trees and verdicts[c]), REFERENCE_CAP)

    # Pair axes, slot 0 at the layer.
    pair_rows = []
    for a, b in pairs_among(names, traits_dir):
        row = {"pair": f"{a} / {b}"}
        if a in ref and b in ref:
            axis_ref = ref[a][0] - ref[b][0]
            for c in caps:
                if a in slices[c] and b in slices[c]:
                    row[c] = _cos(slices[c][a][0] - slices[c][b][0], axis_ref)
        pair_rows.append(row)

    repeat_result = None
    if repeat:
        rc, rtree = repeat
        vals = []
        for n in names:
            x = slices.get(rc, {}).get(n)
            y = vector_slice(rtree / "vectors" / f"{n}.pt", layer)
            if x is not None and y is not None:
                vals.append(min(_cos(x[s], y[s]) for s in range(1, x.shape[0])))
        repeat_result = {"cap": rc, "tree": str(rtree), "n": len(vals),
                         "min": min(vals) if vals else None, "mean": _mean(vals)}

    return {"caps": caps, "layer": layer, "per_entity": per, "summaries": summaries,
            "verdicts": verdicts, "decision": decision, "pairs": pair_rows,
            "repeat": repeat_result, "strata": strata}


# ---------------------------------------------------------------------------
# The readout
# ---------------------------------------------------------------------------

def _f(x, fmt="{:.3f}") -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else fmt.format(x)


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _pts(x) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f}"


def render(result: dict, *, trees: Dict[int, Path], entities_file: Path, entities: dict,
           output: Path) -> str:
    caps = result["caps"]

    def rel(p: Path) -> str:
        """A link relative to the readout (the hotlink rule) when both are
        in the repository; the plain path otherwise (a pod-local tree)."""
        try:
            in_repo = p.resolve().relative_to(REPO)
        except ValueError:
            return f"`{p}`"
        try:
            output.resolve().relative_to(REPO)
        except ValueError:
            return f"`{in_repo}`"          # repository-relative, no home path
        return f"[{p.name}]({os.path.relpath(p.resolve(), output.resolve().parent)})"

    L = []
    L.append("# Cap pilot readout\n")
    L.append(f"Written {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
             f"`tools/cap_pilot_compare.py` from the plan "
             f"{rel(REPO / 'reports' / 'pipeline' / 'plan_max_tokens_pilot.md')}, the entity list "
             f"{rel(entities_file)} (seed {entities.get('seed')}, {len(entities['all'])} entities) "
             f"and the trees " + ", ".join(f"{c}: `{trees[c]}`" for c in caps)
             + f".  Vectors compared at layer {result['layer']}.\n")
    d = result["decision"]
    L.append("## Decision\n")
    L.append("Rule (fixed in the plan before the pilot): keep 512 if, over the stratum means "
             "(roles, traits, combinations), the slot-0 cosine between 512 and 1024 is >= 0.99 and "
             "the score-3 share moves by less than 2 points; otherwise the smallest cap that meets "
             "both.  The outliers are reported, not counted.  Cosines here are **centred** (each "
             "cap's vectors minus their mean over the entities of the deciding strata); the raw ones are in the "
             "table for comparison.\n")
    if d is None:
        L.append("**Undecided**: a deciding stratum lacks scores or vectors at a candidate cap.\n")
    else:
        L.append(f"**Cap: {d}.**  " + "; ".join(
            f"{c}: {'meets' if v else 'misses'} the rule" for c, v in result["verdicts"].items()
            if c != REFERENCE_CAP) + ".\n")
    L.append("| stratum | cap | n | truncated | score-3 share | Δ score-3 (pts) | mean score | Δ mean | cos slot 0 (centred) | cos slot 0 (raw) | cos slots 1-7 (centred; selection only) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in ("roles", "roles_narrative", "traits", "combinations", "traits_outliers",
              "combinations_outliers"):
        for c in caps:
            s = result["summaries"].get(k, {}).get(c)
            if not s:
                continue
            L.append(f"| {k} | {c} | {s['n']} | {_pct(s['truncation'])} | {_pct(s['share3'])} | "
                     f"{_pts(s['d_share3'])} | {_f(s['mean_score'], '{:.2f}')} | "
                     f"{_f(s['d_mean'], '{:+.2f}')} | {_f(s['cos0_centred'], '{:.4f}')} | "
                     f"{_f(s['cos0_raw'], '{:.5f}')} | {_f(s['cos_header_centred'], '{:.4f}')} |")
    L.append("")
    L.append("## The outliers, one by one\n")
    L.append("| entity | cap | truncated | score-3 share | Δ score-3 (pts) | cos slot 0 (centred) |")
    L.append("|---|---|---|---|---|---|")
    for k in OUTLIER_STRATA:
        for n in result["strata"].get(k, []):
            for c in caps:
                r = result["per_entity"][n][c]
                L.append(f"| {n} | {c} | {_pct(r['truncation'])} | "
                         f"{_pct((r['scores'] or {}).get('share3'))} | {_pts(r.get('d_share3'))} | "
                         f"{_f((r.get('cos_centred') or [None])[0], '{:.4f}')} |")
    L.append("")
    L.append(f"## Pair axes (slot 0, layer {result['layer']}, cosine with the {REFERENCE_CAP} axis)\n")
    if result["pairs"]:
        L.append("| pair | " + " | ".join(str(c) for c in caps) + " |")
        L.append("|---|" + "---|" * len(caps))
        for row in result["pairs"]:
            L.append(f"| {row['pair']} | " + " | ".join(_f(row.get(c), "{:.4f}") for c in caps) + " |")
    else:
        L.append("No pair of pilot entities.")
    L.append("")
    L.append("## Run sanity (slots 1-7, same cap, two runs)\n")
    rp = result["repeat"]
    if rp:
        verdict = "ok" if rp["min"] is not None and rp["min"] >= 0.999 else "**below 0.999: a broken run**"
        L.append(f"Cap {rp['cap']} against `{rp['tree']}`: {rp['n']} entities, min "
                 f"{_f(rp['min'], '{:.5f}')}, mean {_f(rp['mean'], '{:.5f}')} ({verdict}).")
    else:
        L.append("Not run (no `--repeat`).")
    L.append("")
    L.append("Per-entity numbers: the `.json` beside this readout.\n")
    return "\n".join(L)


def _jsonable(result: dict) -> dict:
    out = dict(result)
    out["per_entity"] = {n: {str(c): v for c, v in d.items()} for n, d in result["per_entity"].items()}
    out["summaries"] = {k: {str(c): v for c, v in d.items()} for k, d in result["summaries"].items()}
    out["verdicts"] = {str(c): v for c, v in result["verdicts"].items()}
    out["pairs"] = [{str(k): v for k, v in row.items()} for row in result["pairs"]]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--root", type=Path, help="Directory holding cap256/ cap512/ cap768/ cap1024/")
    src.add_argument("--trees", nargs="+", metavar="CAP=DIR", help="One tree per cap")
    ap.add_argument("--entities", type=Path, default=DEFAULT_ENTITIES)
    ap.add_argument("--layer", type=int, default=DEFAULT_LAYER)
    ap.add_argument("--repeat", metavar="CAP=DIR", help="A second run at one cap (run sanity)")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--traits_dir", type=Path, default=REPO / "data" / "traits" / "instructions")
    args = ap.parse_args(argv)

    if args.root:
        trees = {c: args.root / f"cap{c}" for c in CAPS if (args.root / f"cap{c}").is_dir()}
    else:
        trees = {}
        for spec in args.trees:
            cap, _, path = spec.partition("=")
            trees[int(cap)] = Path(path)
    missing = [c for c in CAPS if c not in trees]
    if missing:
        print(f"cap_pilot_compare: no tree for cap(s) {missing}", file=sys.stderr)
        return 1
    repeat = None
    if args.repeat:
        cap, _, path = args.repeat.partition("=")
        repeat = (int(cap), Path(path))
    entities = json.loads(args.entities.read_text())
    result = compare(trees, entities, layer=args.layer, repeat=repeat, traits_dir=args.traits_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(result, trees=trees, entities_file=args.entities,
                                  entities=entities, output=args.output))
    args.output.with_suffix(".json").write_text(json.dumps(_jsonable(result), indent=1) + "\n")
    print(f"wrote {args.output} (decision: {result['decision']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
