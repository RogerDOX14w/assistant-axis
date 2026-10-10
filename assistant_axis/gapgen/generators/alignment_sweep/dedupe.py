"""Within-sweep dedup by gloss embeddings (plan 08 step 4; coding plan § 1: the platform's
``text-embedding-3-large`` through its cache, not a local model).

* :func:`embed_glosses`: each item's gloss, embedded through :func:`assistant_axis.gapgen.embed.embed_texts` (only
  cache misses are sent; every call is charged to ``usage``); unit vectors by item id.
* :func:`dedup_groups`: kept items only (a dropped item is in no group), one pole at a time (a virtue never groups
  with a vice, so a pair's two poles can never merge however close their glosses), in the order source weight
  (high first), rank, item id.  An item joins the group of an earlier item with the **same stem** (``exact stem``:
  identical surfaces would merge in the registry anyway), else the group whose representative's gloss is closest
  at cosine ``threshold`` or above, else it starts a group and represents it.  ``min_cos`` is the lowest cosine of a
  member to its representative.  One candidate is submitted per group (its representative); every member's item id
  stays in ``dedup_groups.json``.
* :func:`rewrite_partner_hints`: a representative's ``partner_hint`` is the label of the representative of its
  partner's group (so a pole whose own partner was deduped points at the label that survived); None when no member
  of its group has a kept partner.
* :func:`tune_threshold`: the threshold that best separates a hand-labelled sample of same / distinct gloss pairs
  (``dedup_labeled_pairs.json``): highest accuracy, then the widest gap between labelled cosines, the threshold in
  the middle of that gap.
* :func:`pairs_for_labeling`: pairs to label, spread over the cosine range: the closest pairs and a seeded sample
  of the near misses below them.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

import numpy as np

from assistant_axis.atomic_io import atomic_write_text

from .extract import Item


@dataclass
class Group:
    rep: str
    members: list
    min_cos: float
    pole: str
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


#: A false merge loses a candidate for good; a missed merge costs one more M1 / M3 row, and the one grouping at the
#: end of all waves (``review_graph.py build``) catches it.  So :func:`tune_threshold` weighs a false merge at twice
#: a missed one by default (2026-10-10, the pilot's labelled pairs; ``--false-merge-cost`` changes it).
FALSE_MERGE_COST = 2.0


@dataclass
class TuneResult:
    value: float
    accuracy: float
    n: int
    n_same: int
    interval: tuple
    errors: list = field(default_factory=list)
    precision: Optional[float] = None
    recall: Optional[float] = None
    cost: Optional[float] = None
    false_merge_cost: float = FALSE_MERGE_COST

    def as_dict(self) -> dict:
        d = asdict(self)
        d["interval"] = list(self.interval)
        return d


def embed_glosses(items: Sequence[Item], *, embedder, cache=None, usage=None) -> dict[str, np.ndarray]:
    """Unit vectors of the items' glosses, by item id (through the cache; misses charged to ``usage``)."""
    from assistant_axis.gapgen.embed import embed_texts
    have = [it for it in items if it.gloss]
    if not have:
        return {}
    E = embed_texts(embedder, [it.gloss for it in have], cache=cache, usage=usage)
    return {it.item_id: np.asarray(E[i], dtype=np.float64) for i, it in enumerate(have)}


def _cos(vectors: Mapping[str, np.ndarray], a: str, b: str) -> float:
    return float(np.dot(vectors[a], vectors[b]))


def dedup_groups(items: Sequence[Item], vectors: Mapping[str, np.ndarray], threshold: float) -> list[Group]:
    """Groups of near-identical poles (module docstring)."""
    kept = [it for it in items if it.kept and it.item_id in vectors]
    order = sorted(kept, key=lambda it: (-float(it.source_weight), it.rank, it.item_id))
    groups: list[Group] = []
    by_stem: dict[tuple, Group] = {}
    for it in order:
        g = by_stem.get((it.pole, it.stem)) if it.stem else None
        why = "exact stem"
        if g is None:
            best = None
            for gg in groups:
                if gg.pole != it.pole:
                    continue
                c = _cos(vectors, gg.rep, it.item_id)
                if c >= threshold and (best is None or c > best[0]):
                    best = (c, gg)
            if best is not None:
                g, why = best[1], f"gloss cosine >= {threshold:g}"
        if g is None:
            g = Group(rep=it.item_id, members=[it.item_id], min_cos=1.0, pole=it.pole)
            groups.append(g)
        else:
            g.members.append(it.item_id)
            g.min_cos = round(min(g.min_cos, _cos(vectors, g.rep, it.item_id)), 6)
            if why not in g.note:
                g.note = "; ".join(x for x in (g.note, why) if x)
        if it.stem:
            by_stem.setdefault((it.pole, it.stem), g)
    return groups


def representatives(groups: Sequence[Group]) -> set[str]:
    return {g.rep for g in groups}


def rewrite_partner_hints(items: Sequence[Item], groups: Sequence[Group]) -> dict[str, Optional[str]]:
    """``{representative item id: partner hint}`` (module docstring)."""
    by = {it.item_id: it for it in items}
    rep_of = {m: g.rep for g in groups for m in g.members}
    out: dict[str, Optional[str]] = {}
    for g in groups:
        hint = None
        for m in [g.rep] + [x for x in g.members if x != g.rep]:
            p = by.get(by[m].partner_item_id)
            if p is not None and p.kept and p.item_id in rep_of:
                hint = by[rep_of[p.item_id]].label
                break
        out[g.rep] = hint
    return out


def tune_threshold(labeled: Sequence[Mapping], *, false_merge_cost: float = FALSE_MERGE_COST) -> TuneResult:
    """The threshold separating ``same`` from distinct pairs best (each pair a dict with ``same`` and ``cos``): the
    gap between labelled cosines with the lowest weighted error (a false merge, a distinct pair at or above the
    threshold, costs ``false_merge_cost``; a missed merge 1), ties to the widest gap, then the higher threshold;
    the threshold is the middle of the gap.  ``false_merge_cost=1`` is plain accuracy."""
    pts = [(float(p["cos"]), bool(p["same"])) for p in labeled if p.get("same") is not None]
    if not pts:
        raise ValueError("no labelled pairs")
    cs = sorted({c for c, _ in pts})
    cands = [(cs[0] - 0.01, cs[0], 0.0)] + [(cs[i], cs[i + 1], cs[i + 1] - cs[i]) for i in range(len(cs) - 1)] \
        + [(cs[-1], cs[-1] + 0.01, 0.0)]
    best = None
    for lo, hi, width in cands:
        t = (lo + hi) / 2
        fm = sum(1 for c, s in pts if c >= t and not s)
        miss = sum(1 for c, s in pts if c < t and s)
        key = (-(false_merge_cost * fm + miss), width, t)
        if best is None or key > best[0]:
            best = (key, lo, hi, t)
    (neg_cost, _w, t), lo, hi, _ = best
    merged_same = sum(1 for c, s in pts if c >= t and s)
    merged = sum(1 for c, _ in pts if c >= t)
    n_same = sum(s for _, s in pts)
    errors = [p for p in labeled if p.get("same") is not None and (float(p["cos"]) >= t) != bool(p["same"])]
    return TuneResult(value=round(t, 4), accuracy=sum((c >= t) == s for c, s in pts) / len(pts), n=len(pts),
                      n_same=n_same, interval=(round(lo, 4), round(hi, 4)), errors=[dict(e) for e in errors],
                      precision=round(merged_same / merged, 4) if merged else None,
                      recall=round(merged_same / n_same, 4) if n_same else None, cost=-neg_cost,
                      false_merge_cost=false_merge_cost)


def pairs_for_labeling(items: Sequence[Item], vectors: Mapping[str, np.ndarray], *, n: int = 30,
                       seed: int = 0) -> list[dict]:
    """``n`` same-pole pairs of kept items (never a pair's two poles): the ``n // 2`` closest, then a seeded sample
    of the next ``10 n`` (the near misses), sorted by cosine, each with ``same: None`` to fill in."""
    kept = [it for it in items if it.kept and it.item_id in vectors]
    cand = []
    for i, a in enumerate(kept):
        for b in kept[i + 1:]:
            if a.pole == b.pole and a.partner_item_id != b.item_id:
                cand.append((_cos(vectors, a.item_id, b.item_id), a, b))
    cand.sort(key=lambda x: (-x[0], x[1].item_id, x[2].item_id))
    top = cand[: n // 2]
    rest = cand[n // 2: n // 2 + 10 * n]
    pick = top + random.Random(f"dedup-label:{seed}").sample(rest, min(n - len(top), len(rest)))
    pick.sort(key=lambda x: -x[0])
    return [{"a": a.item_id, "b": b.item_id, "pole": a.pole, "label_a": a.label, "label_b": b.label,
             "gloss_a": a.gloss, "gloss_b": b.gloss, "cos": round(c, 4), "same": None, "note": None}
            for c, a, b in pick]


def write_groups(groups: Sequence[Group], path: Path, *, threshold: float, model: str, inputs: Sequence = (),
                 extra: Optional[dict] = None) -> Path:
    from assistant_axis import json_metadata
    payload = {"threshold": threshold, "embedding_model": model, "n_groups": len(groups),
               "n_members": sum(len(g.members) for g in groups),
               "n_merged": sum(len(g.members) - 1 for g in groups), "groups": [g.as_dict() for g in groups],
               **(extra or {})}
    env = json_metadata(payload, inputs=list(inputs), title="alignment sweep: within-sweep dedup groups")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", Path(path))
    return Path(path)


def load_groups(path: Path) -> list[Group]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d)
    return [Group(**g) for g in d["groups"]]


__all__ = ["Group", "TuneResult", "embed_glosses", "dedup_groups", "representatives", "rewrite_partner_hints",
           "tune_threshold", "pairs_for_labeling", "write_groups", "load_groups"]
