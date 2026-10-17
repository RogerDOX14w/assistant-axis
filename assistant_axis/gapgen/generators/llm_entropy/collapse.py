"""The mode-collapse statistics, no API but the embeddings (plan sections 6 and 10, ``collapse.py``).

Per family (and per model where both ran, and per language for family c), report-and-decide, never a gate on an
item:

* **label-set Jaccard**: for each prompt (and model), the pairwise Jaccard of the stem sets of its runs (the size of
  the intersection over the size of the union; 1.0 is total collapse), averaged over its pairs; the family's median
  and 90th percentile over prompts.  A pair of empty runs is left out (agreement counts only slots a run filled).
* **Lincoln-Petersen**: the pool two samples reach, ``N = n1 n2 / m`` (``m`` the stems both found), and Chapman's
  form ``(n1 + 1)(n2 + 1) / (m + 1) - 1``, which stays finite at ``m = 0``; the samples are runs 1 and 2, or, for a
  family with one run per prompt (b), its odd and even prompts.  ``seen_over_N`` is the unique stems so far over N.
* **rarefaction**: unique stems against calls in a seeded random call order (``base_model.diversity.rarefaction``),
  its end slope over the last fifth of the calls (unique per call), and **unique per dollar** from the family's cost:
  each response record's billed usage (back-translations count to family c), scaled so that the families sum to the
  run's ``usage.json``.
* **semantic** variants of all three: two labels are one when their embedding cosine is at least ``tau`` (0.9,
  union-find over every pair, blockwise), so that "frugal" and "thrifty" do not inflate uniqueness.  The embedder is
  the scorer's (``embed.make_embedder("openai")`` through the cache, pennies; ``hash`` in tests).
* **the cross-family matrix**: string and semantic Jaccard between the families' stem sets (symmetric, ones on the
  diagonal).
"""
from __future__ import annotations

import json
import math
import random
import shutil
import statistics
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen.registry import utc_stamp
from assistant_axis.judge_pricing import cost_for_usage

from . import COLLAPSE_PATH
from .prompts import FAMILIES

TAU = 0.9
#: Points of the reported rarefaction curve (the end slope is read on the full curve).
CURVE_POINTS = 20


# --------------------------------------------------------------------------- the pieces

def jaccard(a: set, b: set) -> Optional[float]:
    u = a | b
    return len(a & b) / len(u) if u else None


def label_jaccard(run_sets: Mapping[int, set]) -> list[float]:
    """Pairwise Jaccard over the runs of one prompt (pairs of two empty runs left out)."""
    runs = sorted(run_sets)
    out = []
    for i, a in enumerate(runs):
        for b in runs[i + 1:]:
            j = jaccard(set(run_sets[a]), set(run_sets[b]))
            if j is not None:
                out.append(j)
    return out


def _quantile(xs: Sequence[float], q: float) -> Optional[float]:
    xs = sorted(xs)
    if not xs:
        return None
    pos = q * (len(xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo), 4)


def lincoln_petersen(n1: int, n2: int, m: int) -> dict:
    """``{"N": n1 n2 / m (None at m = 0), "chapman": (n1+1)(n2+1)/(m+1) - 1}``."""
    return {"N": round(n1 * n2 / m, 2) if m else None, "chapman": round((n1 + 1) * (n2 + 1) / (m + 1) - 1, 2)}


def rarefaction_curve(call_sets: Sequence[set], *, seed: int = 0, points: int = CURVE_POINTS) -> dict:
    """``{"curve": [[calls, unique], ...], "end_slope_per_call", "n_calls", "n_unique"}`` in a seeded random call
    order; the end slope is the unique stems the last fifth of the calls added, per call."""
    from ..base_model.diversity import rarefaction
    order = list(call_sets)
    random.Random(f"llm_entropy:rarefaction:{seed}").shuffle(order)
    full = rarefaction([set(s) for s in order], step=1)
    n = len(full)
    if not n:
        return {"curve": [], "end_slope_per_call": None, "n_calls": 0, "n_unique": 0}
    step = max(1, n // points)
    curve = [list(p) for p in full[step - 1::step]]
    if curve[-1][0] != n:
        curve.append(list(full[-1]))
    k = max(1, math.ceil(0.8 * n))
    slope = (full[-1][1] - full[k - 1][1]) / (n - k) if n > k else None
    return {"curve": curve, "end_slope_per_call": round(slope, 4) if slope is not None else None, "n_calls": n,
            "n_unique": full[-1][1]}


def semantic_clusters(labels: Mapping[str, str], embed: Callable[[Sequence[str]], object], *, tau: float = TAU,
                      block: int = 1024) -> dict[str, int]:
    """``{stem: cluster id}``: stems whose labels' embeddings have cosine >= ``tau`` are one (union-find over every
    pair, ``block`` rows at a time).  Cluster ids are the smallest member's index in sorted stem order."""
    import numpy as np
    stems = sorted(labels)
    if not stems:
        return {}
    E = np.asarray(embed([labels[s] for s in stems]), dtype=np.float32)
    parent = list(range(len(stems)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for start in range(0, len(stems), block):
        S = E[start:start + block] @ E.T
        for bi, j in zip(*np.nonzero(S >= tau)):
            i = start + int(bi)
            if int(j) <= i:
                continue
            a, b = find(i), find(int(j))
            if a != b:
                parent[max(a, b)] = min(a, b)
    return {s: find(i) for i, s in enumerate(stems)}


def cross_family_matrix(sets: Mapping[str, set]) -> dict:
    """``{"families", "matrix"}``: Jaccard between the families' sets, symmetric, 1.0 on the diagonal."""
    fams = [f for f in FAMILIES if f in sets] + sorted(f for f in sets if f not in FAMILIES)
    m = [[1.0 if a == b else round(jaccard(set(sets[a]), set(sets[b])) or 0.0, 4) for b in fams] for a in fams]
    return {"families": fams, "matrix": m}


# --------------------------------------------------------------------------- cost per family

def family_costs(records: Iterable[Mapping], usage_total_usd: Optional[float] = None) -> dict:
    """``{"by_family": {f: usd}, "by_family_model": {f|model: usd}, "records_usd", "usage_json_usd", "scale"}``: each
    record's billed usage priced at its ``charged_as`` rate, scaled so the families sum to ``usage_total_usd`` (the
    run's ``usage.json``) when it is given."""
    from assistant_axis.gapgen.llm import CACHE_READ_FACTOR, CACHE_WRITE_1H_FACTOR, CACHE_WRITE_FACTOR
    by: Counter = Counter()
    by_fm: Counter = Counter()
    for r in records:
        raw, model = r.get("usage_raw") or {}, r.get("charged_as")
        if not raw or not model:
            continue
        cw = int(raw.get("cache_creation_input_tokens") or 0)
        cw1h = min(int(raw.get("cache_creation_1h_input_tokens") or 0), cw)
        prompt = int(raw.get("input_tokens") or 0) + int(round(CACHE_WRITE_FACTOR * (cw - cw1h)
                                                               + CACHE_WRITE_1H_FACTOR * cw1h
                                                               + CACHE_READ_FACTOR * int(raw.get("cache_read_input_tokens") or 0)))
        usd = cost_for_usage(model, prompt, int(raw.get("output_tokens") or 0))
        fam = r.get("family") or "?"
        by[fam] += usd
        by_fm[f"{fam}|{str(model).split(':')[0]}"] += usd
    total = sum(by.values())
    scale = (usage_total_usd / total) if usage_total_usd and total else 1.0
    return {"by_family": {f: round(v * scale, 6) for f, v in sorted(by.items())},
            "by_family_model": {k: round(v * scale, 6) for k, v in sorted(by_fm.items())},
            "records_usd": round(total, 6), "usage_json_usd": usage_total_usd, "scale": round(scale, 6)}


def yield_per_dollar(per_family: Mapping[str, Mapping], costs: Mapping[str, float]) -> dict:
    """``{family: unique stems per dollar}`` (string and, when present, semantic)."""
    out = {}
    for f, d in per_family.items():
        c = costs.get(f)
        out[f] = {"string": round(d["n_unique_string"] / c, 1) if c else None,
                  "semantic": round(d["n_unique_semantic"] / c, 1) if c and d.get("n_unique_semantic") is not None
                  else None}
    return out


# --------------------------------------------------------------------------- per family

def _unit(it) -> tuple:
    return (it.prompt_id, it.run, it.stage, it.model)


def figures(items: Sequence, *, cost_usd: Optional[float] = None, clusters: Optional[Mapping[str, int]] = None,
            seed: int = 0) -> dict:
    """The figures of one family (or one model or language within it), on stems and, given ``clusters``, on
    semantic clusters."""
    def stats(key: Callable[[str], object]) -> dict:
        calls: dict[tuple, set] = {}
        for it in items:
            calls.setdefault(_unit(it), set())
            if it.stem:
                calls[_unit(it)].add(key(it.stem))
        per_prompt: dict[tuple, dict[int, set]] = {}
        for (pid, run, stage, model), s in calls.items():
            per_prompt.setdefault((pid, stage, model), {})[run] = s
        jac = [statistics.mean(js) for js in (label_jaccard(r) for r in per_prompt.values()) if js]
        runs = sorted({run for (_, run, _, _) in calls})
        if len(runs) >= 2:
            a = set().union(*[s for (p, run, st, m), s in calls.items() if run == runs[0]])
            b = set().union(*[s for (p, run, st, m), s in calls.items() if run == runs[1]])
            split = f"runs {runs[0]} and {runs[1]}"
        else:
            pids = sorted({p for (p, _, _, _) in calls})
            odd = set(pids[0::2])
            a = set().union(*[s for (p, *_), s in calls.items() if p in odd]) if calls else set()
            b = set().union(*[s for (p, *_), s in calls.items() if p not in odd]) if calls else set()
            split = "odd and even prompts"
        seen = set().union(*calls.values()) if calls else set()
        lp = lincoln_petersen(len(a), len(b), len(a & b))
        rare = rarefaction_curve(list(calls.values()), seed=seed)
        n_u = len(seen)
        return {"n_calls": len(calls), "n_unique": n_u, "jaccard_median": _quantile(jac, 0.5),
                "jaccard_p90": _quantile(jac, 0.9), "n_prompts_jaccard": len(jac),
                "lincoln_petersen": {"split": split, "n1": len(a), "n2": len(b), "m": len(a & b), **lp},
                "seen_over_N": round(n_u / lp["N"], 4) if lp["N"] else None,
                "seen_over_chapman": round(n_u / lp["chapman"], 4) if lp["chapman"] else None,
                "rarefaction": rare["curve"], "end_slope_per_call": rare["end_slope_per_call"],
                "unique_per_usd": round(n_u / cost_usd, 1) if cost_usd else None}
    s = stats(lambda st: st)
    out = {"n_items": len(items), "n_calls": s["n_calls"], "n_unique_string": s["n_unique"],
           "jaccard_median": s["jaccard_median"], "jaccard_p90": s["jaccard_p90"],
           "n_prompts_jaccard": s["n_prompts_jaccard"], "lincoln_petersen": s["lincoln_petersen"],
           "lincoln_petersen_N": s["lincoln_petersen"]["N"], "seen_over_N": s["seen_over_N"],
           "seen_over_chapman": s["seen_over_chapman"], "rarefaction": s["rarefaction"],
           "end_slope_per_call": s["end_slope_per_call"], "cost_usd": round(cost_usd, 6) if cost_usd else cost_usd,
           "unique_per_usd": s["unique_per_usd"], "n_unique_semantic": None, "semantic": None}
    if clusters is not None:
        sem = stats(lambda st: clusters.get(st, st))
        out["n_unique_semantic"] = sem["n_unique"]
        out["semantic"] = sem
    return out


def net_new_end_slope(items: Sequence, net_new_stems: Iterable[str], *, seed: int = 0) -> Optional[float]:
    """The rarefaction end slope of the items' calls counted on net-new stems only (the items table's ``net_new``):
    the full grid's stop rule (plan task 8) reads it after two runs, and a family under 1 a call gets no third run."""
    nn = set(net_new_stems)
    calls: dict[tuple, set] = {}
    for it in items:
        calls.setdefault(_unit(it), set())
        if it.stem in nn:
            calls[_unit(it)].add(it.stem)
    return rarefaction_curve(list(calls.values()), seed=seed)["end_slope_per_call"]


def collapse_payload(items: Sequence, records: Sequence[Mapping], *, usage_total_usd: Optional[float] = None,
                     embed: Optional[Callable[[Sequence[str]], object]] = None, embedder: Optional[str] = None,
                     tau: float = TAU, seed: int = 0, runs: Sequence[str] = (),
                     net_new_stems: Optional[Iterable[str]] = None) -> dict:
    """The collapse payload (section 6): per family, ``by_model`` within it, ``by_language`` for family c, the
    cross-family matrices, the costs, and the settings.  With ``net_new_stems`` (the items table's net-new rows),
    each family also gets ``net_new_end_slope_per_call``, which the full grid's stop rule reads."""
    costs = family_costs(records, usage_total_usd)
    clusters = None
    if embed is not None:
        labels: dict[str, str] = {}
        for it in sorted(items, key=lambda x: x.order):
            if it.stem and it.stem not in labels:
                labels[it.stem] = it.label
        clusters = semantic_clusters(labels, embed, tau=tau)
    by_fam: dict[str, list] = {}
    for it in items:
        by_fam.setdefault(it.family, []).append(it)
    per = {}
    for f in [x for x in FAMILIES if x in by_fam]:
        its = by_fam[f]
        d = figures(its, cost_usd=costs["by_family"].get(f), clusters=clusters, seed=seed)
        models = sorted({x.model for x in its})
        if len(models) > 1:
            d["by_model"] = {m: figures([x for x in its if x.model == m],
                                        cost_usd=costs["by_family_model"].get(f"{f}|{m}"), clusters=clusters, seed=seed)
                             for m in models}
        d["net_new_end_slope_per_call"] = (net_new_end_slope(its, net_new_stems, seed=seed)
                                           if net_new_stems is not None else None)
        if f == "c":
            d["by_language"] = {lang: figures([x for x in its if x.language == lang], clusters=clusters, seed=seed)
                                for lang in sorted({x.language for x in its})}
        per[f] = d
    sets = {f: {x.stem for x in by_fam[f] if x.stem} for f in per}
    cross = {"families": cross_family_matrix(sets)["families"], "string": cross_family_matrix(sets)["matrix"],
             "semantic": None}
    if clusters is not None:
        cross["semantic"] = cross_family_matrix({f: {clusters.get(s, s) for s in v} for f, v in sets.items()})["matrix"]
    return {"per_family": per, "cross_family": cross, "costs": costs, "tau": tau, "embedder": embedder,
            "seed": seed, "runs": list(runs), "yield_per_dollar": yield_per_dollar(per, costs["by_family"])}


# --------------------------------------------------------------------------- the file

def load_collapse(path: Path = COLLAPSE_PATH) -> dict:
    """``collapse.json``'s payload (the envelope read through; frozen interface); empty when absent."""
    p = Path(path)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) else {}


def write_collapse(payload: Mapping, path: Path = COLLAPSE_PATH, *, inputs: Optional[list] = None) -> Optional[Path]:
    """Write the enveloped payload unless unchanged; a changed file is first copied to ``.bak.<UTC>``."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.plot_metadata import json_metadata
    path = Path(path)
    if path.exists() and load_collapse(path) == json.loads(json.dumps(payload)):
        return None
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    env = json_metadata(dict(payload), inputs=inputs, title="llm_entropy collapse statistics")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False, default=str) + "\n", path)
    return backup


__all__ = ["TAU", "net_new_end_slope", "jaccard", "label_jaccard", "lincoln_petersen", "rarefaction_curve", "semantic_clusters",
           "cross_family_matrix", "family_costs", "yield_per_dollar", "figures", "collapse_payload", "load_collapse",
           "write_collapse"]
