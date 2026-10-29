#!/usr/bin/env python3
"""Compare the response-length cap pilot's four trees and write its readout.

The pilot (reports/pipeline/plan_max_tokens_pilot.md, walk-through P6,
2026-10-12; revised 2026-10-28) runs the 64 entities of
reports/pipeline/cap_pilot_entities.json through steps 1-4 at caps 256, 512,
768 and 1024, one tree per cap (``<tree>/responses``, ``<tree>/scores``,
``<tree>/vectors``), plus a second 512 tree (the repeat).  This tool reads the
trees and writes the readout (default reports/pipeline/cap_pilot_readout.md,
with the numbers in a ``.json`` beside it) with the plan's measurements (§ 5):

1. **Truncation share** at each cap, from the responses' ``finish_reason``
   (``"length"``; a field written by step 1 since 2026-10-12).
2. **Judge**: the score-3 share and the mean score at each cap, and the
   paired difference to the reference (1024) run.  With ``--extra_scores``
   an entity's share at a cap is the mean over its judgings there.
3. **Vector, direction**: per slot, the cosine between an entity's vector at
   each cap and at the reference, at ``--layer`` (default 25).  Slot 0 (the
   mean over the response's tokens) moves by content and selection; slots 1-7
   (header tokens, before the response) by selection alone.  Cosines are
   given raw and **centred** (each cap's vectors minus their mean over the
   pilot entities with a vector at both caps): raw cosines of activation
   means are all close to 1 because every vector shares the model's common
   direction, so the rule below is applied to the centred ones (Roger,
   2026-10-28: centred on the pilot mean, not the default vector).  The
   centring mean is over the deciding strata only, so an outlier cannot move
   the others' cosines.
4. **Vector, length**: the relative change in the centred slot-0 norm,
   ``|v_cap - m_cap| / |v_ref - m_ref| - 1`` with the same centring means as
   the cosines; the raw norms and their relative change beside it.
5. **The noise floor** (``--repeat 512=TREE``): every measure above for the
   repeat against the 512 tree, per entity and per stratum, printed beside the
   cap comparisons; σ per entity type (roles, traits, combinations; outliers
   excluded), the standard deviation over the type's entities of the share
   difference repeat minus 512 (one judging each side: the 512 tree's
   primary scores, whatever ``--extra_scores`` adds); and the run-sanity
   check, slots 1-7 of 512 against the repeat >= 0.999 raw (a miss is a
   broken run, not a cap effect).  With ``--extra_scores 512=DIR`` also the
   **judge-only floor**: per type, the standard deviation of the share
   difference between the 512 tree's two judgings (the first 512 extra minus
   the primary).
6. **Per-entity flags** (with ``--repeat``): every entity whose paired share
   change, cap minus 1024, exceeds 4σ of its type, listed with its change, σ
   and how many judgings each side averages.  Reported, not deciding.
7. **Slot 0 decomposed**: *selection alone* (``--vectors_all CAP=DIR``,
   step 4's ``--all_responses`` vectors): per cap, the judge-selected vector
   against the all-response vector of the same tree, slot 0 and slots 1-7,
   cosine centred (the same centring as item 3) and raw, and the slot-0 norm
   shift (selected over all, minus 1); *content alone* (``--prefix_means
   1024=DIR``, step 2's ``--prefix_token_means`` files of the reference tree):
   per entity, over the responses the reference tree's (primary) scores
   select, the mean of the first-N-token means against the mean of the full
   slot-0 means of the same responses, which is the reference vector's slot
   0; per N, cosine centred on the pilot mean of the same quantity and raw,
   and the norm shift.  The prefix files are read one entity at a time with
   ``torch_load_with_retry`` (about 1 GB each at all layers).
8. **Pair axes**: for each pair of pilot entities (``verbose``/``concise``
   first; then any trait pair recorded in the corpus's ``arrangement``
   field), the cosine of the pair-difference axis at each cap with the
   reference's, slot 0, at ``--layer``.
9. ``verbose``, ``concise`` and their angel combinations reported on their
   own.

**Decision rule** (fixed in the plan, before the pilot): keep 512 if, over
the stratum means (roles, traits, combinations; the outliers do not decide),
the centred slot-0 cosine between 512 and 1024 is >= 0.995 (Roger,
2026-10-28; 0.99 until then), the centred slot-0 norm moves by at most 10%
and the score-3 share moves by less than 2 points; otherwise take the
smallest cap that meets all three (768, else 1024; 256 shows the slope and is
not a candidate).  The floor is reported beside it: if 512′ against 512
itself misses a rule, the readout says so (the decision is not changed by
it).

No API call, no model; reads only the small outputs (responses, scores,
vectors, prefix means).  Usage::

    uv run python tools/cap_pilot_compare.py --root roger/cap_pilot \\
        --repeat 512=roger/cap_pilot/cap512b \\
        --extra_scores 512=roger/cap_pilot/cap512/scores_rejudge \\
        --vectors_all 512=roger/cap_pilot/cap512/vectors_all \\
        --vectors_all 1024=roger/cap_pilot/cap1024/vectors_all \\
        --prefix_means 1024=roger/cap_pilot/cap1024/prefix_means
    uv run python tools/cap_pilot_compare.py --trees 256=a 512=b 768=c 1024=d \\
        --output /tmp/readout.md

``--extra_scores``, ``--vectors_all`` are repeatable (one ``CAP=DIR`` each).
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
sys.path.insert(0, str(REPO))

from assistant_axis.atomic_io import torch_load_with_retry  # noqa: E402

DEFAULT_ENTITIES = REPO / "reports" / "pipeline" / "cap_pilot_entities.json"
DEFAULT_OUTPUT = REPO / "reports" / "pipeline" / "cap_pilot_readout.md"
CAPS = (256, 512, 768, 1024)
REFERENCE_CAP = 1024
CANDIDATE_CAPS = (512, 768, 1024)
COSINE_MIN = 0.995                # about cos(0.1 rad); 0.99 until 2026-10-28
NORM_SHIFT_MAX = 0.10             # the displacement a 0.1-radian turn makes (2026-10-28)
SCORE3_SHIFT_MAX = 0.02           # "less than 2 points"
RUN_SANITY_MIN = 0.999            # slots 1-7, same cap, two runs
FLAG_SIGMAS = 4                   # the per-entity rule (Roger, 2026-10-28)
JUDGE_FLOOR_CAP = 512             # the tree judged twice
DECIDING_STRATA = ("roles", "traits", "combinations")
OUTLIER_STRATA = ("traits_outliers", "combinations_outliers")
DEFAULT_LAYER = 25
# Entity type per stratum: σ is per type over the deciding strata (outliers
# out); an outlier is flagged against its type's σ.
TYPE_OF_STRATUM = {"roles_narrative": "roles", "roles": "roles", "traits": "traits",
                   "traits_outliers": "traits", "combinations": "combinations",
                   "combinations_outliers": "combinations"}
TYPES = ("roles", "traits", "combinations")


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


def read_scores(scores_file: Path) -> Optional[Dict[str, int]]:
    """The integer scores of a score file, by response key; None when missing."""
    if not scores_file.exists():
        return None
    return {k: v for k, v in json.loads(scores_file.read_text()).items() if isinstance(v, int)}


def score_stats(scores_file: Path) -> Optional[Dict[str, float]]:
    scores = read_scores(scores_file)
    if not scores:
        return None
    vals = list(scores.values())
    return {"n": len(vals), "share3": sum(s == 3 for s in vals) / len(vals),
            "mean": sum(vals) / len(vals)}


def judged_stats(scores_files: List[Path]) -> Optional[Dict[str, float]]:
    """``score_stats`` averaged over an entity's judgings at one cap (the
    primary scores file first, then the extras that have one): ``share3`` and
    ``mean`` are means over the judgings, ``n_judgings`` how many there were,
    ``share3_judgings`` each judging's share."""
    stats = [s for s in (score_stats(f) for f in scores_files) if s]
    if not stats:
        return None
    return {"n": stats[0]["n"], "share3": statistics.fmean(s["share3"] for s in stats),
            "mean": statistics.fmean(s["mean"] for s in stats), "n_judgings": len(stats),
            "share3_judgings": [s["share3"] for s in stats]}


def _vector_record(vector_file: Path, layer: int) -> Optional[tuple]:
    """``(slice, inputs, metadata)``: the vector's ``(n_slots, hidden)`` at
    ``layer`` in float64, and its ``inputs`` and ``metadata`` records; None
    when the file is missing."""
    if not vector_file.exists():
        return None
    data = torch.load(vector_file, map_location="cpu", weights_only=False)
    v = data["vector"] if isinstance(data, dict) else data
    if v.ndim == 2:                       # (n_layers, hidden): one slot
        v = v.unsqueeze(0)
    inputs = (data.get("inputs") or {}) if isinstance(data, dict) else {}
    metadata = (data.get("metadata") or {}) if isinstance(data, dict) else {}
    return v[:, layer, :].to(torch.float64), inputs, metadata


def vector_slice(vector_file: Path, layer: int) -> Optional[torch.Tensor]:
    """``(n_slots, hidden)`` at ``layer``, float64; None when missing."""
    rec = _vector_record(vector_file, layer)
    return None if rec is None else rec[0]


def _cos(a: torch.Tensor, b: torch.Tensor) -> float:
    mask = ~(torch.isnan(a) | torch.isnan(b))
    a, b = a[mask], b[mask]
    na, nb = a.norm(), b.norm()
    if na == 0 or nb == 0:
        return float("nan")
    return float((a @ b) / (na * nb))


def _norm(a: torch.Tensor) -> float:
    return float(a[~torch.isnan(a)].norm())


def _rel(a: float, b: float) -> float:
    """``a / b - 1``; NaN when ``b`` is 0 or either is NaN."""
    if b == 0 or math.isnan(a) or math.isnan(b):
        return float("nan")
    return a / b - 1


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------

def _mean(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return statistics.fmean(xs) if xs else None


def _sd(xs) -> Optional[float]:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return statistics.stdev(xs) if len(xs) >= 2 else None


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


def pair_measures(a: Dict[str, torch.Tensor], b: Dict[str, torch.Tensor], names: List[str],
                  basis_names) -> Dict[str, dict]:
    """``a`` against ``b`` for every entity with a vector on both sides
    (``(n_slots, hidden)`` each): per slot the raw and the centred cosine,
    and slot 0's norms and their relative change, ``|a - m_a| / |b - m_b| - 1``
    centred and ``|a| / |b| - 1`` raw.  Each side is centred on its own mean
    over the entities of ``basis_names`` present on both sides (the deciding
    strata: an outlier must not move the others), the same set for both;
    with no such entity the centred measures are NaN and the raw ones
    stand."""
    basis = [n for n in names if n in basis_names and n in a and n in b]
    m_a = torch.stack([a[n] for n in basis]).mean(0) if basis else None
    m_b = torch.stack([b[n] for n in basis]).mean(0) if basis else None
    nan = float("nan")
    out = {}
    for n in [n for n in names if n in a and n in b]:
        x, y = a[n], b[n]
        n_slots = x.shape[0]
        nr_a, nr_b = _norm(x[0]), _norm(y[0])
        if m_a is None:
            cos_c, nc_a, nc_b = [nan] * n_slots, nan, nan
        else:
            cos_c = [_cos(x[s] - m_a[s], y[s] - m_b[s]) for s in range(n_slots)]
            nc_a, nc_b = _norm(x[0] - m_a[0]), _norm(y[0] - m_b[0])
        out[n] = {"cos_raw": [_cos(x[s], y[s]) for s in range(n_slots)],
                  "cos_centred": cos_c,
                  "norm0_centred": nc_a, "norm0_centred_ref": nc_b,
                  "norm0_raw": nr_a, "norm0_raw_ref": nr_b,
                  "norm_shift": _rel(nc_a, nc_b), "norm_shift_raw": _rel(nr_a, nr_b)}
    return out


def _summary(rows: List[dict]) -> dict:
    """Stratum means of the per-entity measures in ``rows`` (any subset of
    the keys may be present)."""
    return {
        "n": len(rows),
        "truncation": _mean(r.get("truncation") for r in rows),
        "share3": _mean((r.get("scores") or {}).get("share3") for r in rows),
        "mean_score": _mean((r.get("scores") or {}).get("mean") for r in rows),
        "d_share3": _mean(r.get("d_share3") for r in rows),
        "d_mean": _mean(r.get("d_mean") for r in rows),
        "cos0_centred": _mean((r.get("cos_centred") or [None])[0] for r in rows),
        "cos0_raw": _mean((r.get("cos_raw") or [None])[0] for r in rows),
        "cos_header_centred": _mean(_mean((r.get("cos_centred") or [None])[1:]) for r in rows),
        "cos_header_raw": _mean(_mean((r.get("cos_raw") or [None])[1:]) for r in rows),
        "norm_shift": _mean(r.get("norm_shift") for r in rows),
        "norm_shift_raw": _mean(r.get("norm_shift_raw") for r in rows),
        "n_vectors": sum(1 for r in rows if r.get("cos_centred")),
        "max_judgings": max([(r.get("scores") or {}).get("n_judgings", 1) for r in rows
                             if r.get("scores")] or [0]),
    }


def _meets(s: Optional[dict]) -> Optional[Dict[str, bool]]:
    """Which of the three rules a stratum summary meets; None when it lacks
    a measure."""
    if not s or s["cos0_centred"] is None or s["d_share3"] is None or s["norm_shift"] is None:
        return None
    return {"cosine": s["cos0_centred"] >= COSINE_MIN,
            "norm": abs(s["norm_shift"]) <= NORM_SHIFT_MAX,
            "share": abs(s["d_share3"]) < SCORE3_SHIFT_MAX}


def _load_slices(directory: Path, names: List[str], layer: int) -> Dict[str, torch.Tensor]:
    out = {}
    for n in names:
        s = vector_slice(directory / f"{n}.pt", layer)
        if s is not None:
            out[n] = s
    return out


def prefix_content(prefix_dir: Path, cap: int, tree: Path, names: List[str], layer: int,
                   full: Dict[str, torch.Tensor], vector_inputs: Dict[str, dict]) -> dict:
    """The content-alone measure's inputs, one entity at a time: for each
    entity with a prefix file and a vector at ``cap``, over the responses the
    tree's primary scores select (score 3), the mean of each N's prefix means
    at ``layer`` (float64, NaN-aware) and the share of those responses shorter
    than N.  ``full[n]`` is the vector's slot 0 at the layer, the mean of the
    full slot-0 means of the same responses.  Returns ``{"means": {n: (K,
    hidden)}, "per_entity": {n: {...}}, "notes": [...]}``."""
    means: Dict[str, torch.Tensor] = {}
    per: Dict[str, dict] = {}
    notes: List[str] = []
    for n in names:
        f = prefix_dir / f"{n}.pt"
        if not f.exists() or n not in full:
            continue
        scores = read_scores(tree / "scores" / f"{n}.json") or {}
        data = torch_load_with_retry(f, map_location="cpu", weights_only=False)
        meta = data.pop("metadata", {}) or {}
        ns = [int(x) for x in meta.get("prefix_tokens") or []]
        layers = meta.get("layers")
        if layers is not None and layer not in layers:
            notes.append(f"{n}: layer {layer} is not in its prefix file (layers {layers})")
            del data
            continue
        li = layers.index(layer) if layers is not None else layer
        selected = [k for k in data if scores.get(k) == 3]
        if not selected:
            del data
            continue
        total = torch.zeros(len(ns), data[selected[0]].shape[-1], dtype=torch.float64)
        count = torch.zeros_like(total)
        for k in selected:
            x = data[k][:, li, :].to(torch.float64)
            finite = ~torch.isnan(x)
            total += torch.where(finite, x, torch.zeros((), dtype=torch.float64))
            count += finite
        means[n] = total / count
        short = meta.get("short") or {}
        used = vector_inputs.get(n, {}).get("n_score3_used")
        if used is not None and used != len(selected):
            notes.append(f"{n}: the {cap} vector averaged {used} score-3 responses, the prefix "
                         f"file has {len(selected)} of them (scores rewritten since step 4?)")
        per[n] = {"prefix_tokens": ns, "n_selected": len(selected),
                  "short_share": [_mean(float(bool((short.get(k) or [False] * len(ns))[i]))
                                        for k in selected) for i in range(len(ns))]}
        del data                          # about 1 GB at all layers: one entity at a time
    return {"means": means, "per_entity": per, "notes": notes}


def compare(trees: Dict[int, Path], entities: dict, *, layer: int = DEFAULT_LAYER,
            repeat: Optional[tuple] = None, traits_dir: Path = REPO / "data" / "traits" / "instructions",
            extra_scores: Optional[Dict[int, List[Path]]] = None,
            vectors_all: Optional[Dict[int, Path]] = None,
            prefix_means: Optional[tuple] = None) -> dict:
    if REFERENCE_CAP not in trees:
        raise SystemExit(f"cap_pilot_compare: no tree for the reference cap {REFERENCE_CAP}")
    extra_scores = extra_scores or {}
    vectors_all = vectors_all or {}
    caps = sorted(trees)
    strata: Dict[str, List[str]] = dict(entities["strata"])
    strata["roles"] = strata.get("roles_narrative", []) + strata.get("roles", [])
    names = entities["all"]
    type_of = {n: TYPE_OF_STRATUM[k] for k, v in entities["strata"].items()
               if k in TYPE_OF_STRATUM for n in v}

    per: Dict[str, Dict[int, dict]] = {n: {} for n in names}
    slices: Dict[int, Dict[str, torch.Tensor]] = {c: {} for c in caps}
    vector_inputs: Dict[int, Dict[str, dict]] = {c: {} for c in caps}
    for c in caps:
        t = trees[c]
        for n in names:
            primary = t / "scores" / f"{n}.json"
            per[n][c] = {"truncation": truncation_share(t / "responses" / f"{n}.jsonl"),
                         "scores": judged_stats([primary] + [d / f"{n}.json"
                                                             for d in extra_scores.get(c, [])]),
                         "scores_primary": score_stats(primary)}
            rec = _vector_record(t / "vectors" / f"{n}.pt", layer)
            if rec is not None:
                slices[c][n], vector_inputs[c][n] = rec[0], rec[1]

    # Cap against the reference: cosines and norms, each cap's vectors centred
    # on their mean over the deciding entities with a vector at that cap and at
    # the reference (the outliers must not move everyone else's), applied to
    # every entity, the outliers included.
    ref = slices[REFERENCE_CAP]
    deciding = {n for k in DECIDING_STRATA for n in strata.get(k, [])}
    for c in caps:
        for n, m in pair_measures(slices[c], ref, names, deciding).items():
            per[n][c].update(m)
    for n in names:
        r = per[n][REFERENCE_CAP]["scores"]
        for c in caps:
            s = per[n][c]["scores"]
            if s and r:
                per[n][c]["d_share3"] = s["share3"] - r["share3"]
                per[n][c]["d_mean"] = s["mean"] - r["mean"]

    def summaries_of(rows_by_name: Dict[str, dict]) -> Dict[str, dict]:
        out = {k: _summary([rows_by_name.get(n, {}) for n in v]) for k, v in strata.items() if v}
        out["roles_narrative"] = _summary([rows_by_name.get(n, {})
                                           for n in strata.get("roles_narrative", [])])
        return out

    by_cap = {c: summaries_of({n: per[n][c] for n in names}) for c in caps}
    summaries = {k: {c: by_cap[c][k] for c in caps} for k in by_cap[REFERENCE_CAP]}

    def passes(c: int) -> Optional[bool]:
        ok = True
        for k in DECIDING_STRATA:
            m = _meets(summaries.get(k, {}).get(c))
            if m is None:
                return None
            ok = ok and all(m.values())
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

    # The noise floor: the repeat against its cap's tree, every measure, one
    # judging on each side (the primary scores).
    repeat_result = floor = None
    sigma: Dict[str, Optional[float]] = {}
    if repeat:
        rc, rtree = repeat
        rslices = _load_slices(rtree / "vectors", names, layer)
        floor_per: Dict[str, dict] = {}
        for n in names:
            rs = score_stats(rtree / "scores" / f"{n}.json")
            row = {"truncation": truncation_share(rtree / "responses" / f"{n}.jsonl"),
                   "scores": rs}
            base = per[n][rc]["scores_primary"]
            if rs and base:
                row["d_share3"] = rs["share3"] - base["share3"]
                row["d_mean"] = rs["mean"] - base["mean"]
            floor_per[n] = row
        for n, m in pair_measures(rslices, slices.get(rc, {}), names, deciding).items():
            floor_per[n].update(m)
        floor_summaries = summaries_of(floor_per)
        sigma = {t: _sd(floor_per[n].get("d_share3") for n in strata.get(t, [])) for t in TYPES}
        floor = {"cap": rc, "tree": str(rtree), "per_entity": floor_per,
                 "summaries": floor_summaries, "sigma": sigma,
                 "meets": {k: _meets(floor_summaries.get(k)) for k in DECIDING_STRATA}}
        vals = [min(m["cos_raw"][1:]) for m in floor_per.values()
                if len(m.get("cos_raw") or []) > 1]
        repeat_result = {"cap": rc, "tree": str(rtree), "n": len(vals),
                         "min": min(vals) if vals else None, "mean": _mean(vals)}

    # The judge-only floor: the 512 tree's two judgings (the first extra).
    judge_floor = None
    if extra_scores.get(JUDGE_FLOOR_CAP) and JUDGE_FLOOR_CAP in trees:
        rejudge = extra_scores[JUDGE_FLOOR_CAP][0]
        diffs = {}
        for n in names:
            a = per[n][JUDGE_FLOOR_CAP]["scores_primary"]
            b = score_stats(rejudge / f"{n}.json")
            if a and b:
                diffs[n] = b["share3"] - a["share3"]
        judge_floor = {"cap": JUDGE_FLOOR_CAP, "dir": str(rejudge), "per_entity": diffs,
                       "sd": {t: _sd(diffs.get(n) for n in strata.get(t, [])) for t in TYPES},
                       "n": {t: sum(1 for n in strata.get(t, []) if n in diffs) for t in TYPES}}

    # The per-entity rule: paired share change beyond 4σ of the entity's type.
    flags: Optional[List[dict]] = None
    if repeat:
        flags = []
        for c in caps:
            if c == REFERENCE_CAP:
                continue
            for n in names:
                d, t = per[n][c].get("d_share3"), type_of.get(n)
                s = sigma.get(t)
                if d is None or not s or abs(d) <= FLAG_SIGMAS * s:
                    continue
                jc = (per[n][c]["scores"] or {}).get("n_judgings", 1)
                jr = (per[n][REFERENCE_CAP]["scores"] or {}).get("n_judgings", 1)
                flags.append({"entity": n, "type": t, "cap": c, "d_share3": d, "sigma": s,
                              "z": d / s, "judgings_cap": jc, "judgings_ref": jr,
                              "averaged": jc > 1 or jr > 1})

    # Selection alone: the judge-selected vector against the all-response
    # vector of the same tree (step 4 --all_responses), centred alike.
    selection = {}
    for c, d in sorted(vectors_all.items()):
        all_slices, unmarked = {}, []
        for n in names:
            rec = _vector_record(d / f"{n}.pt", layer)
            if rec is None:
                continue
            all_slices[n] = rec[0]
            if not (rec[1].get("all_responses") or rec[2].get("all_responses")):
                unmarked.append(n)
        rows = pair_measures(slices.get(c, {}), all_slices, names, deciding)
        selection[c] = {"dir": str(d), "per_entity": rows, "summaries": summaries_of(rows),
                        "not_marked_all_responses": unmarked}

    # Content alone: the reference tree's prefix means against the full means
    # of the same responses (the reference vector's slot 0).
    content = None
    if prefix_means:
        pc, pdir = prefix_means
        full = {n: v[0] for n, v in slices[pc].items()}
        got = prefix_content(pdir, pc, trees[pc], names, layer, full, vector_inputs[pc])
        ns = sorted({x for e in got["per_entity"].values() for x in e["prefix_tokens"]})
        per_n: Dict[int, Dict[str, dict]] = {}
        for i_n, n_tok in enumerate(ns):
            a = {n: got["means"][n][e["prefix_tokens"].index(n_tok)].unsqueeze(0)
                 for n, e in got["per_entity"].items() if n_tok in e["prefix_tokens"]}
            b = {n: full[n].unsqueeze(0) for n in a}
            rows = pair_measures(a, b, names, deciding)
            for n, row in rows.items():
                e = got["per_entity"][n]
                row["short_share"] = e["short_share"][e["prefix_tokens"].index(n_tok)]
                row["n_selected"] = e["n_selected"]
            per_n[n_tok] = rows
        content_summaries: Dict[int, Dict[str, dict]] = {}
        for n_tok, rows in per_n.items():
            content_summaries[n_tok] = {}
            for k, v in strata.items():
                if v:
                    s = _summary([rows.get(n, {}) for n in v])
                    s["short_share"] = _mean(rows.get(n, {}).get("short_share") for n in v)
                    content_summaries[n_tok][k] = s
        content = {"cap": pc, "dir": str(pdir), "prefix_tokens": ns, "per_entity": per_n,
                   "summaries": content_summaries, "notes": got["notes"]}

    return {"caps": caps, "layer": layer, "per_entity": per, "summaries": summaries,
            "verdicts": verdicts, "decision": decision, "pairs": pair_rows,
            "repeat": repeat_result, "floor": floor, "judge_floor": judge_floor,
            "flags": flags, "selection": selection, "content": content,
            "strata": strata, "type_of": type_of,
            "rule": {"cosine_min": COSINE_MIN, "norm_shift_max": NORM_SHIFT_MAX,
                     "score3_shift_max": SCORE3_SHIFT_MAX, "flag_sigmas": FLAG_SIGMAS}}


# ---------------------------------------------------------------------------
# The readout
# ---------------------------------------------------------------------------

def _f(x, fmt="{:.3f}") -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else fmt.format(x)


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _pts(x) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f}"


def _shift(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:+.1f}%"


STRATUM_ORDER = ("roles", "roles_narrative", "traits", "combinations", "traits_outliers",
                 "combinations_outliers")


def linked_entity(n: str, output: Path) -> str:
    """The entity's name linked, relative to ``output``, to its instruction
    file (a combination ``r_<role>__<trait>`` / ``t_<trait>__<trait>`` to both
    parts); the plain name where a file is missing or the readout is outside
    the repository."""
    try:
        output.resolve().relative_to(REPO)
    except ValueError:
        return n

    def one(stem: str, kind: str) -> Optional[str]:
        f = REPO / "data" / kind / "instructions" / f"{stem}.json"
        return f"[{stem}]({os.path.relpath(f, output.resolve().parent)})" if f.exists() else None

    head, sep, tail = n[2:].partition("__")
    if n[:2] in ("r_", "t_") and sep:
        a, b = one(head, "roles" if n[0] == "r" else "traits"), one(tail, "traits")
        if a and b:
            return f"{n[:2]}{a}__{b}"
    return one(n, "roles") or one(n, "traits") or n


def render(result: dict, *, trees: Dict[int, Path], entities_file: Path, entities: dict,
           output: Path) -> str:
    caps = result["caps"]
    inputs = result.get("inputs") or {}

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

    def entity_link(n: str) -> str:
        return linked_entity(n, output)

    L = []
    L.append("# Cap pilot readout\n")
    L.append(f"Written {datetime.now(timezone.utc).isoformat(timespec='seconds')} by "
             f"`tools/cap_pilot_compare.py` from the plan "
             f"{rel(REPO / 'reports' / 'pipeline' / 'plan_max_tokens_pilot.md')}, the entity list "
             f"{rel(entities_file)} (seed {entities.get('seed')}, {len(entities['all'])} entities) "
             f"and the trees " + ", ".join(f"{c}: `{trees[c]}`" for c in caps)
             + f".  Vectors compared at layer {result['layer']}.\n")
    more = []
    if inputs.get("repeat"):
        more.append(f"the repeat {inputs['repeat']['cap']}: `{inputs['repeat']['tree']}`")
    for c, ds in sorted((inputs.get("extra_scores") or {}).items()):
        more.append(f"extra judgings at {c}: " + ", ".join(f"`{d}`" for d in ds))
    for c, d in sorted((inputs.get("vectors_all") or {}).items()):
        more.append(f"all-response vectors at {c}: `{d}`")
    if inputs.get("prefix_means"):
        more.append(f"prefix means at {inputs['prefix_means']['cap']}: "
                    f"`{inputs['prefix_means']['dir']}`")
    if more:
        L.append("Also read: " + "; ".join(more) + ".\n")

    d = result["decision"]
    L.append("## Decision\n")
    L.append("Rule (fixed in the plan before the pilot): keep 512 if, over the stratum means "
             f"(roles, traits, combinations), the slot-0 cosine between 512 and 1024 is >= {COSINE_MIN}, "
             f"the slot-0 norm moves by at most {100 * NORM_SHIFT_MAX:.0f}% and "
             "the score-3 share moves by less than 2 points; otherwise the smallest cap that meets "
             "all three.  The outliers are reported, not counted.  Cosines and norms here are "
             "**centred** (each cap's vectors minus their mean over the entities of the deciding "
             "strata); the raw ones are in the table for comparison.\n")
    if d is None:
        L.append("**Undecided**: a deciding stratum lacks scores or vectors at a candidate cap.\n")
    else:
        L.append(f"**Cap: {d}.**  " + "; ".join(
            f"{c}: {'meets' if v else 'misses'} the rule" for c, v in result["verdicts"].items()
            if c != REFERENCE_CAP) + ".\n")
    fl = result.get("floor")
    if fl:
        missed = {k: [r for r, ok in (m or {}).items() if not ok]
                  for k, m in fl["meets"].items()}
        missed = {k: v for k, v in missed.items() if v}
        unmeasured = [k for k, m in fl["meets"].items() if m is None]
        if unmeasured:
            L.append(f"The floor lacks a measure (scores or vectors) in: {', '.join(unmeasured)}.\n")
        if missed:
            L.append(f"**The floor misses the rule**: {fl['cap']}′ against {fl['cap']} itself "
                     "misses " + "; ".join(f"{k}: {', '.join(v)}" for k, v in missed.items())
                     + ".  No cap can meet a rule its own repeat misses; read the decision on "
                       "that measure as unmeetable rather than as a reason to raise the cap.\n")
        elif not unmeasured:
            L.append(f"The floor ({fl['cap']}′ against {fl['cap']}) meets all three rules in every "
                     "deciding stratum.\n")

    L.append("| stratum | cap | n | truncated | score-3 share | Δ score-3 (pts) | mean score | Δ mean | "
             "cos slot 0 (centred) | cos slot 0 (raw) | norm slot 0 (centred) | norm (raw) | "
             "cos slots 1-7 (centred; selection only) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def row(k, label, s):
        return (f"| {k} | {label} | {s['n']} | {_pct(s['truncation'])} | {_pct(s['share3'])} | "
                f"{_pts(s['d_share3'])} | {_f(s['mean_score'], '{:.2f}')} | "
                f"{_f(s['d_mean'], '{:+.2f}')} | {_f(s['cos0_centred'], '{:.4f}')} | "
                f"{_f(s['cos0_raw'], '{:.5f}')} | {_shift(s['norm_shift'])} | "
                f"{_shift(s['norm_shift_raw'])} | {_f(s['cos_header_centred'], '{:.4f}')} |")

    for k in STRATUM_ORDER:
        for c in caps:
            s = result["summaries"].get(k, {}).get(c)
            if s:
                L.append(row(k, c, s))
        if fl and fl["summaries"].get(k):
            L.append(row(k, f"floor {fl['cap']}′ vs {fl['cap']}", fl["summaries"][k]))
    L.append("")
    L.append("Δ columns are cap minus 1024 (the floor rows: the repeat minus its cap, one judging "
             "each); norm columns are the relative change of slot 0's norm against 1024 (the "
             "floor: against its cap).\n")

    # The noise floor
    L.append(f"## Noise floor ({fl['cap']}′ against {fl['cap']})\n" if fl else "## Noise floor\n")
    jf = result.get("judge_floor")
    if fl:
        L.append("σ per entity type: the standard deviation over the type's entities (outliers "
                 "excluded) of the score-3 share difference, repeat minus its cap, one generation "
                 "and judging on each side (the total noise; the per-entity rule's unit).  "
                 "Judge-only: the same over the 512 tree's two judgings of the same responses.\n")
        L.append("| type | σ total (pts) | 4σ (pts) | judge-only SD (pts) | n judge-only |")
        L.append("|---|---|---|---|---|")
        for t in TYPES:
            s = fl["sigma"].get(t)
            L.append(f"| {t} | {_f(None if s is None else 100 * s, '{:.2f}')} | "
                     f"{_f(None if s is None else 100 * FLAG_SIGMAS * s, '{:.1f}')} | "
                     f"{_f(None if not jf or jf['sd'][t] is None else 100 * jf['sd'][t], '{:.2f}')} | "
                     f"{jf['n'][t] if jf else 'n/a'} |")
        L.append("")
    else:
        L.append("Not measured (no `--repeat`).\n")
    if jf and not fl:
        L.append("Judge-only SD of the score-3 share difference (pts), the 512 tree's two "
                 "judgings: " + ", ".join(f"{t} {_f(None if jf['sd'][t] is None else 100 * jf['sd'][t], '{:.2f}')}"
                                          for t in TYPES) + ".\n")
    L.append("## Run sanity (slots 1-7, same cap, two runs)\n")
    rp = result["repeat"]
    if rp:
        verdict = ("ok" if rp["min"] is not None and rp["min"] >= RUN_SANITY_MIN
                   else f"**below {RUN_SANITY_MIN}: a broken run**")
        L.append(f"Cap {rp['cap']} against `{rp['tree']}`: {rp['n']} entities, min "
                 f"{_f(rp['min'], '{:.5f}')}, mean {_f(rp['mean'], '{:.5f}')} ({verdict}).")
    else:
        L.append("Not run (no `--repeat`).")
    L.append("")

    # Flags
    L.append(f"## Per-entity flags ({FLAG_SIGMAS}σ; reported, not deciding)\n")
    flags = result.get("flags")
    if flags is None:
        L.append("None computed: without `--repeat` there is no σ.\n")
    else:
        no_sigma = [t for t in TYPES if not (fl or {}).get("sigma", {}).get(t)]
        if no_sigma:
            L.append(f"No σ (fewer than two entities, or zero) for: {', '.join(no_sigma)}; "
                     "those entities are not flagged.\n")
        if flags:
            L.append("Each is to be judged twice more at its cap and at 1024 (the plan § 5) and "
                     "counts as a systematic change only if the average stays past 4σ.\n")
            L.append("| entity | type | cap | Δ score-3 (pts) | σ (pts) | Δ/σ | judgings cap / 1024 | averaged |")
            L.append("|---|---|---|---|---|---|---|---|")
            for g in sorted(flags, key=lambda g: (g["cap"], -abs(g["z"]))):
                L.append(f"| {g['entity']} | {g['type']} | {g['cap']} | {_pts(g['d_share3'])} | "
                         f"{_f(100 * g['sigma'], '{:.2f}')} | {_f(g['z'], '{:+.1f}')} | "
                         f"{g['judgings_cap']} / {g['judgings_ref']} | "
                         f"{'yes' if g['averaged'] else 'no'} |")
        else:
            L.append("No entity's change exceeds 4σ of its type.")
        L.append("")

    # The decomposition
    L.append("## Slot 0 decomposed\n")
    ct = result.get("content")
    L.append(f"**Content alone** (the {ct['cap'] if ct else REFERENCE_CAP} tree's prefix means): "
             "per entity, over the responses its scores select, the mean of the first-N-token "
             "means against the mean of the full means of the same responses (the vector's slot "
             "0); centred on the pilot mean of each, at the layer.  A response shorter than N "
             "gives its full mean, so the share of short responses bounds what N can show.\n")
    if ct:
        L.append("| stratum | N | n | cos (centred) | cos (raw) | norm (centred) | norm (raw) | short of N |")
        L.append("|---|---|---|---|---|---|---|---|")
        for k in STRATUM_ORDER:
            for n_tok in ct["prefix_tokens"]:
                s = ct["summaries"][n_tok].get(k)
                if s:
                    L.append(f"| {k} | {n_tok} | {s['n_vectors']} | {_f(s['cos0_centred'], '{:.4f}')} | "
                             f"{_f(s['cos0_raw'], '{:.5f}')} | {_shift(s['norm_shift'])} | "
                             f"{_shift(s['norm_shift_raw'])} | {_pct(s['short_share'])} |")
        for note in ct["notes"]:
            L.append(f"\n- {note}")
        L.append("")
    else:
        L.append("Not measured (no `--prefix_means`).\n")
    sel = result.get("selection") or {}
    L.append("**Selection alone** (step 4's `--all_responses` vectors): the judge-selected vector "
             "against the mean over every response of the same tree, centred alike; norm = "
             "selected over all, minus 1.  Slots 1-7 move by selection only at every cap; the "
             "score-3 share in the first table is the same effect from the judge's side.\n")
    if sel:
        L.append("| stratum | cap | n | cos slot 0 (centred) | cos slot 0 (raw) | norm slot 0 (centred) | "
                 "cos slots 1-7 (centred) | cos slots 1-7 (raw) |")
        L.append("|---|---|---|---|---|---|---|---|")
        for k in STRATUM_ORDER:
            for c, sc in sel.items():
                s = sc["summaries"].get(k)
                if s:
                    L.append(f"| {k} | {c} | {s['n_vectors']} | {_f(s['cos0_centred'], '{:.4f}')} | "
                             f"{_f(s['cos0_raw'], '{:.5f}')} | {_shift(s['norm_shift'])} | "
                             f"{_f(s['cos_header_centred'], '{:.4f}')} | "
                             f"{_f(s['cos_header_raw'], '{:.5f}')} |")
        for c, sc in sel.items():
            if sc["not_marked_all_responses"]:
                L.append(f"\n- {c}: {len(sc['not_marked_all_responses'])} vector(s) in `{sc['dir']}` "
                         f"are not marked `all_responses` (not made by `4_vectors.py "
                         f"--all_responses`?): {', '.join(sc['not_marked_all_responses'][:10])}")
        L.append("")
    else:
        L.append("Not measured (no `--vectors_all`).\n")

    L.append("## The outliers, one by one\n")
    L.append("| entity | cap | truncated | score-3 share | judgings | Δ score-3 (pts) | cos slot 0 (centred) | norm slot 0 (centred) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k in OUTLIER_STRATA:
        for n in result["strata"].get(k, []):
            for c in caps:
                r = result["per_entity"][n][c]
                L.append(f"| {n} | {c} | {_pct(r['truncation'])} | "
                         f"{_pct((r['scores'] or {}).get('share3'))} | "
                         f"{(r['scores'] or {}).get('n_judgings', 'n/a')} | {_pts(r.get('d_share3'))} | "
                         f"{_f((r.get('cos_centred') or [None])[0], '{:.4f}')} | "
                         f"{_shift(r.get('norm_shift'))} |")
    L.append("")
    L.append(f"## Pair axes (slot 0, layer {result['layer']}, cosine with the {REFERENCE_CAP} axis)\n")
    if result["pairs"]:
        L.append("| pair | " + " | ".join(str(c) for c in caps) + " |")
        L.append("|---|" + "---|" * len(caps))
        for row_ in result["pairs"]:
            L.append(f"| {row_['pair']} | " + " | ".join(_f(row_.get(c), "{:.4f}") for c in caps) + " |")
    else:
        L.append("No pair of pilot entities.")
    L.append("")

    # Keep share per entity and cap, lowest at the reference first (Roger,
    # 2026-10-29: recall matters most for the lowest-keep traits).
    others = [c for c in caps if c != REFERENCE_CAP]
    L.append("## Score-3 share per entity, lowest first\n")
    L.append(f"Per entity type, sorted by the score-3 share at {REFERENCE_CAP}: the share at each "
             f"cap (the mean over its judgings where a cap has more than one) and the paired change, "
             f"cap minus {REFERENCE_CAP}, in points.  *(outlier)*: not in a deciding stratum.\n")
    for t, ks in (("Roles", ("roles_narrative", "roles")), ("Traits", ("traits", "traits_outliers")),
                  ("Combinations", ("combinations", "combinations_outliers"))):
        members = [(n, k) for k in ks for n in result["strata"].get(k, [])]
        if not members:
            continue
        L.append(f"**{t}**\n")
        L.append("| entity | " + " | ".join(f"{c}" for c in caps) + " | "
                 + " | ".join(f"Δ {c}" for c in others) + " |")
        L.append("|---|" + "---|" * (len(caps) + len(others)))

        def share(n, c):
            return (result["per_entity"][n][c]["scores"] or {}).get("share3")

        members.sort(key=lambda m: (share(m[0], REFERENCE_CAP) is None, share(m[0], REFERENCE_CAP) or 0))
        for n, k in members:
            r = result["per_entity"][n]
            L.append(f"| {entity_link(n)}{' *(outlier)*' if k.endswith('_outliers') else ''} | "
                     + " | ".join(_pct(share(n, c)) for c in caps) + " | "
                     + " | ".join(_pts(r[c].get("d_share3")) for c in others) + " |")
        L.append("")

    # Per-entity detail
    L.append("## Per entity\n")
    L.append(f"Columns per cap in the order {' / '.join(str(c) for c in others)} (against "
             f"{REFERENCE_CAP}); judgings in the order {' / '.join(str(c) for c in caps)}; the "
             "floor columns are the repeat against its cap.\n")
    L.append("| entity | stratum | judgings | Δ score-3 (pts) | cos slot 0 (centred) | norm slot 0 (centred) | "
             "floor Δ score-3 | floor cos slot 0 | floor norm |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    stratum_of = {n: k for k in STRATUM_ORDER for n in result["strata"].get(k, [])
                  if k != "roles"}
    stratum_of.update({n: "roles" for n in result["strata"].get("roles", [])
                       if n not in stratum_of})
    for n in entities["all"]:
        r = result["per_entity"][n]
        fr = (fl or {}).get("per_entity", {}).get(n, {})
        L.append(f"| {n} | {stratum_of.get(n, '?')} | "
                 + " / ".join(str((r[c]['scores'] or {}).get('n_judgings', '-')) for c in caps) + " | "
                 + " / ".join(_pts(r[c].get('d_share3')) for c in others) + " | "
                 + " / ".join(_f((r[c].get('cos_centred') or [None])[0], '{:.4f}') for c in others) + " | "
                 + " / ".join(_shift(r[c].get('norm_shift')) for c in others) + " | "
                 + f"{_pts(fr.get('d_share3')) if fl else 'n/a'} | "
                 + f"{_f((fr.get('cos_centred') or [None])[0], '{:.4f}') if fl else 'n/a'} | "
                 + f"{_shift(fr.get('norm_shift')) if fl else 'n/a'} |")
    L.append("")
    L.append("Everything above, per entity and per stratum: the `.json` beside this readout.\n")
    return "\n".join(L)


def _jsonable(obj):
    """The result with every dict key a string (caps are ints), recursively."""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


def _cap_dir(spec: str, option: str) -> tuple:
    cap, sep, path = spec.partition("=")
    try:
        if not sep or not path:
            raise ValueError
        return int(cap), Path(path)
    except ValueError:
        raise SystemExit(f"cap_pilot_compare: {option} {spec!r}: expected CAP=DIR") from None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--root", type=Path, help="Directory holding cap256/ cap512/ cap768/ cap1024/")
    src.add_argument("--trees", nargs="+", metavar="CAP=DIR", help="One tree per cap")
    ap.add_argument("--entities", type=Path, default=DEFAULT_ENTITIES)
    ap.add_argument("--layer", type=int, default=DEFAULT_LAYER)
    ap.add_argument("--repeat", metavar="CAP=DIR",
                    help="A second run at one cap (512=<the cap512b tree>): the noise floor (every "
                         "measure, repeat against that cap), σ per entity type for the per-entity "
                         "flags, and the run-sanity check")
    ap.add_argument("--extra_scores", action="append", default=[], metavar="CAP=DIR",
                    help="Repeatable: another judging of a cap's responses (a scores directory, "
                         "e.g. 512=<tree>/scores_rejudge); an entity's share at the cap is the mean "
                         "over its judgings there.  The first 512 extra also gives the judge-only "
                         "floor")
    ap.add_argument("--vectors_all", action="append", default=[], metavar="CAP=DIR",
                    help="Repeatable: a cap's all-response vectors (step 4 --all_responses), for "
                         "the selection-only measure")
    ap.add_argument("--prefix_means", metavar="CAP=DIR",
                    help="The reference tree's prefix means (1024=<tree>/prefix_means, step 2 "
                         "--prefix_token_means), for the content-only measure")
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
    repeat = _cap_dir(args.repeat, "--repeat") if args.repeat else None
    extra: Dict[int, List[Path]] = {}
    for spec in args.extra_scores:
        c, p = _cap_dir(spec, "--extra_scores")
        extra.setdefault(c, []).append(p)
    vectors_all = dict(_cap_dir(s, "--vectors_all") for s in args.vectors_all)
    prefix = _cap_dir(args.prefix_means, "--prefix_means") if args.prefix_means else None
    for option, cs in (("--repeat", [repeat[0]] if repeat else []), ("--extra_scores", extra),
                       ("--vectors_all", vectors_all), ("--prefix_means", [prefix[0]] if prefix else [])):
        bad = [c for c in cs if c not in trees]
        if bad:
            print(f"cap_pilot_compare: {option} names cap(s) {bad} with no tree", file=sys.stderr)
            return 1
    given = ([repeat[1]] if repeat else []) + [p for ps in extra.values() for p in ps] \
        + list(vectors_all.values()) + ([prefix[1]] if prefix else [])
    absent = [str(p) for p in given if not p.is_dir()]
    if absent:
        print(f"cap_pilot_compare: no such directory: {', '.join(absent)}", file=sys.stderr)
        return 1
    entities = json.loads(args.entities.read_text())
    result = compare(trees, entities, layer=args.layer, repeat=repeat, traits_dir=args.traits_dir,
                     extra_scores=extra, vectors_all=vectors_all, prefix_means=prefix)
    # What was read (provenance): every input directory, beside the numbers.
    result["inputs"] = {
        "entities": str(args.entities), "layer": args.layer,
        "trees": {c: str(p) for c, p in trees.items()},
        "repeat": {"cap": repeat[0], "tree": str(repeat[1])} if repeat else None,
        "extra_scores": {c: [str(p) for p in ps] for c, ps in extra.items()},
        "vectors_all": {c: str(p) for c, p in vectors_all.items()},
        "prefix_means": {"cap": prefix[0], "dir": str(prefix[1])} if prefix else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(result, trees=trees, entities_file=args.entities,
                                  entities=entities, output=args.output))
    args.output.with_suffix(".json").write_text(json.dumps(_jsonable(result), indent=1) + "\n")
    print(f"wrote {args.output} (decision: {result['decision']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
