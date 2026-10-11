"""Embed the items, cluster them at two granularities, keep the clusters both embedders reproduce, split poles.

* **Text**: every item is embedded as a first-person statement, "I " + the item with its first letter lowered
  (:func:`item_embed_text`: "Get chores done right away." -> "I get chores done right away.").
* **Embedders**: the platform's (``embed.make_embedder``): OpenAI ``text-embedding-3-large`` (the primary arm,
  charged at $0.13 per million tokens) and the local EmbeddingGemma (free, still charged to the usage record),
  both through ``EmbeddingCache``.
* **Clusters** (:func:`agglo_clusters`): average linkage on cosine distance over every item, one tree per arm
  (``scipy.cluster.hierarchy.linkage``).  A cluster is a group of two or more items; an item left alone is not a
  cluster.  Plan § 5 said "distance threshold found by bisection until the count of clusters with >= 2 items is
  within tol of target"; that count is not monotonic in the threshold (merging two singletons adds a cluster,
  merging two clusters removes one), so the cut is found exactly instead: the count is followed merge by merge, and
  the cut is the **last** merge after the count's peak whose count is nearest the target, i.e. the largest
  threshold giving that count (items absorbed as far as the count allows).  ``info`` records the threshold, the
  count, the peak and the singletons.
* **Consensus** (:func:`consensus`): the primary arm's clusters matched one to one to the other arm's by Jaccard,
  greedily from the highest; a cluster whose match reaches ``min_jaccard`` (0.5, plan 07 § 3) is kept, the rest go
  to the loose pile (held for later, plan § 10 decision (d)).
* **Poles** (:func:`split_poles`): a cluster is bipolar when a scale has both + and - keyed items in it; the items
  are then two-coloured by their key signs on every scale they share (same sign, same pole), a frustrated edge
  settled by local majority, and items that share no scale with the rest go to the nearer pole by cosine (or to the
  larger pole without vectors).  Pole "a" is the side with more + keys on the bipolar scales.
* **Quality** (report only): :func:`purity_metrics` (NMI and ARI against the construct labels, majority-construct
  purity), :func:`hdbscan_check` (HDBSCAN on a 20-d UMAP, its ARI against the cut), and :func:`nearest_corpus`
  (variant C of plan 07: each cluster's mean item cosine to its nearest corpus trait, an ordering column; nothing
  in a cluster's membership reads the corpus).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Mapping, Optional, Sequence

import numpy as np

from assistant_axis.judge_pricing import MultiModelUsage

from .ingest import ItemRow, code_order

PRIMARY_ARM = "openai"
SECOND_ARM = "gemma"
DEFAULT_TOL = 0.1
MIN_JACCARD = 0.5


# --------------------------------------------------------------------------- texts and vectors

def item_embed_text(text: str) -> str:
    """The item as a first-person statement: "I " + the item, its first letter lowered (an item already
    written with "I" is left as it is)."""
    t = " ".join(str(text).split())
    if t.startswith(("I ", "I'm ", "I'd ", "I've ", "I'll ")) or t in ("I",):
        return t
    return "I " + (t[:1].lower() + t[1:] if t else t)


def embed_items(items: Sequence[ItemRow], *, embedder=None, arm: Optional[str] = None, cache=None,
                usage: Optional[MultiModelUsage] = None) -> np.ndarray:
    """``(n, d)`` unit rows, one per item in order, through the platform's cache (only misses are sent)."""
    from assistant_axis.gapgen.embed import embed_texts, make_embedder
    emb = embedder or make_embedder(arm or PRIMARY_ARM)
    return embed_texts(emb, [item_embed_text(r.text) for r in items], cache=cache, usage=usage)


# --------------------------------------------------------------------------- clusters

@dataclass
class RawCluster:
    members: list          # item indices (or ids), sorted

    @property
    def size(self) -> int:
        return len(self.members)


def _linkage(E: np.ndarray) -> np.ndarray:
    from scipy.cluster.hierarchy import linkage
    E = np.asarray(E, dtype=np.float64)
    E = E / np.linalg.norm(E, axis=1, keepdims=True)
    return linkage(E, method="average", metric="cosine")


def _counts(Z: np.ndarray, n: int) -> list[int]:
    """The number of clusters of two or more items after each merge."""
    size = np.ones(2 * n - 1, dtype=np.int64)
    out, c = [], 0
    for k in range(n - 1):
        a, b = int(Z[k, 0]), int(Z[k, 1])
        sa, sb = size[a], size[b]
        if sa == 1 and sb == 1:
            c += 1
        elif sa >= 2 and sb >= 2:
            c -= 1
        size[n + k] = sa + sb
        out.append(c)
    return out


def _members_after(Z: np.ndarray, n: int, n_merges: int) -> list[list[int]]:
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    node_rep = {i: i for i in range(n)}
    for k in range(n_merges):
        a, b = node_rep[int(Z[k, 0])], node_rep[int(Z[k, 1])]
        ra, rb = find(a), find(b)
        parent[max(ra, rb)] = min(ra, rb)
        node_rep[n + k] = min(ra, rb)
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)
    return [sorted(g) for g in groups.values()]


def order_clusters(groups: Sequence[Sequence]) -> list:
    """Largest first, then by the first member (code order for ids, index order for indices)."""
    def key(g):
        first = min(g, key=lambda x: code_order(x) if isinstance(x, str) else ("", x))
        return (-len(g), code_order(first) if isinstance(first, str) else ("", first))
    return sorted((sorted(g, key=lambda x: code_order(x) if isinstance(x, str) else ("", x)) for g in groups), key=key)


def agglo_clusters(E: np.ndarray, *, target_n: int, tol: float = DEFAULT_TOL, Z: Optional[np.ndarray] = None
                   ) -> tuple[list[RawCluster], dict]:
    """``(clusters, info)``: the cut of the average-linkage tree whose count of clusters (two or more items) is
    nearest ``target_n`` on the falling side of the count's peak, the last such cut (see the module docstring).
    ``info["within_tol"]`` says whether the count is within ``tol`` of the target."""
    n = len(E)
    if n < 2:
        return [], {"target": target_n, "n_clusters": 0, "n_singletons": n, "within_tol": False}
    Z = _linkage(E) if Z is None else Z
    counts = _counts(Z, n)
    peak = int(np.argmax(counts))
    best_k, best_d = peak, abs(counts[peak] - target_n)
    for k in range(peak, n - 1):
        d = abs(counts[k] - target_n)
        if d <= best_d:
            best_k, best_d = k, d
    groups = [g for g in _members_after(Z, n, best_k + 1) if len(g) >= 2]
    clusters = [RawCluster(members=g) for g in order_clusters(groups)]
    n_c = len(clusters)
    info = {"target": target_n, "n_clusters": n_c, "threshold": round(float(Z[best_k, 2]), 6),
            "n_merges": best_k + 1, "peak_count": int(counts[peak]), "peak_threshold": round(float(Z[peak, 2]), 6),
            "n_singletons": n - sum(c.size for c in clusters),
            "within_tol": abs(n_c - target_n) <= max(1, round(tol * target_n)), "tol": tol,
            "size_quartiles": [int(x) for x in np.percentile([c.size for c in clusters], [0, 25, 50, 75, 100])]
            if clusters else []}
    return clusters, info


@dataclass
class Matched:
    members: list
    jaccard: float
    partner: Optional[int] = None        # the matched cluster's index in the other arm


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def consensus(a: Sequence[Sequence], b: Sequence[Sequence], *, min_jaccard: float = MIN_JACCARD
              ) -> tuple[list[Matched], list[Matched]]:
    """``(kept, loose)`` of the clusters of ``a``: one-to-one greedy matching by Jaccard against ``b`` (highest
    first; ties by index); kept when the match reaches ``min_jaccard``.  Both lists keep ``a``'s order; a loose
    cluster carries its best Jaccard against any cluster of ``b`` (matched or not)."""
    sa = [set(x) for x in a]
    sb = [set(x) for x in b]
    where: dict = defaultdict(set)
    for j, s in enumerate(sb):
        for x in s:
            where[x].add(j)
    pairs, best = [], [0.0] * len(sa)
    for i, s in enumerate(sa):
        for j in sorted(set().union(*(where[x] for x in s)) if s else ()):
            jac = _jaccard(s, sb[j])
            pairs.append((-jac, i, j))
            best[i] = max(best[i], jac)
    pairs.sort()
    used_a, used_b, match = set(), set(), {}
    for neg, i, j in pairs:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        match[i] = (j, -neg)
    kept, loose = [], []
    for i, members in enumerate(a):
        j, jac = match.get(i, (None, 0.0))
        if j is not None and jac >= min_jaccard:
            kept.append(Matched(list(members), round(jac, 6), j))
        else:
            loose.append(Matched(list(members), round(best[i], 6), j))
    return kept, loose


# --------------------------------------------------------------------------- poles

@dataclass
class Pole:
    pole: str                                   # "a" or "b"
    items: list                                 # item ids, code order
    bipolar_scales: list = field(default_factory=list)
    constructs: dict = field(default_factory=dict)   # "INV:Construct:+" -> count, this pole's items

    def as_dict(self) -> dict:
        return asdict(self)


def scale_name(s: Mapping) -> str:
    return f"{s['inventory']}:{s['construct']}"


def _pole_constructs(ids: Sequence[str], items: Mapping[str, ItemRow]) -> dict:
    c = Counter(f"{scale_name(s)}:{s['key']}" for i in ids for s in items[i].scales)
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def split_poles(members: Sequence[str], items: Mapping[str, ItemRow], *,
                vectors: Optional[Mapping[str, np.ndarray]] = None) -> list[Pole]:
    """One pole for a unipolar cluster, two for a bipolar one (see the module docstring)."""
    ids = sorted(members, key=code_order)
    signs: dict[str, dict[str, int]] = defaultdict(dict)
    for i in ids:
        for s in items[i].scales:
            signs[scale_name(s)][i] = 1 if s["key"] == "+" else -1
    bipolar = sorted(k for k, d in signs.items() if len(set(d.values())) == 2)
    if not bipolar:
        return [Pole("a", ids, [], _pole_constructs(ids, items))]
    W: dict[tuple[str, str], int] = defaultdict(int)
    for d in signs.values():
        its = sorted(d, key=code_order)
        for x in range(len(its)):
            for y in range(x + 1, len(its)):
                w = d[its[x]] * d[its[y]]
                W[(its[x], its[y])] += w
                W[(its[y], its[x])] += w
    adj: dict[str, list[str]] = defaultdict(list)
    for (p, q), w in sorted(W.items(), key=lambda kv: (code_order(kv[0][0]), code_order(kv[0][1]))):
        if w:
            adj[p].append(q)
    color: dict[str, int] = {}
    comps: list[list[str]] = []
    for start in sorted(ids, key=lambda i: (-len(adj[i]), code_order(i))):
        if start in color or not adj[start]:
            continue
        color[start], comp, queue = 1, [start], [start]
        while queue:
            u = queue.pop(0)
            for v in adj[u]:
                if v not in color:
                    color[v] = color[u] * (1 if W[(u, v)] > 0 else -1)
                    comp.append(v)
                    queue.append(v)
        comps.append(comp)
    for _ in range(10):                        # settle frustrated edges by local majority
        changed = False
        for u in sorted(color, key=code_order):
            s = sum(W[(u, v)] * color[v] for v in adj[u])
            if s and (1 if s > 0 else -1) != color[u]:
                color[u] = -color[u]
                changed = True
        if not changed:
            break

    def plus_keys(group):
        return sum(1 for i in group for k in bipolar if signs[k].get(i) == 1)

    def minus_keys(group):
        return sum(1 for i in group for k in bipolar if signs[k].get(i) == -1)
    main = max(comps, key=lambda c: (len({color[x] for x in c}) == 2, len(c)))
    side = {s: [x for x in main if color[x] == s] for s in (1, -1)}
    a_sign = max((1, -1), key=lambda s: (plus_keys(side[s]) - minus_keys(side[s]), len(side[s]),
                                         -min(code_order(x)[1] for x in side[s]) if side[s] else 0))
    pole_a = set(side[a_sign])
    pole_b = set(side[-a_sign])

    def unit(i):
        v = np.asarray(vectors[i], dtype=np.float64)
        return v / (np.linalg.norm(v) or 1.0)

    def nearer_a(group) -> bool:
        if vectors is None or not pole_a or not pole_b:
            return len(pole_a) >= len(pole_b)
        ca = np.mean([unit(i) for i in pole_a], axis=0)
        cb = np.mean([unit(i) for i in pole_b], axis=0)
        m = np.mean([unit(i) for i in group], axis=0)
        return float(m @ ca) / (np.linalg.norm(ca) or 1) >= float(m @ cb) / (np.linalg.norm(cb) or 1)
    for comp in comps:
        if comp is main:
            continue
        sides = {s: [x for x in comp if color[x] == s] for s in (1, -1)}
        if sides[1] and sides[-1]:             # bipolar on its own: orient it, then place each side
            first_to_a = nearer_a(sides[1]) if vectors is not None else (
                plus_keys(sides[1]) - minus_keys(sides[1]) >= plus_keys(sides[-1]) - minus_keys(sides[-1]))
            (pole_a if first_to_a else pole_b).update(sides[1])
            (pole_b if first_to_a else pole_a).update(sides[-1])
        else:
            (pole_a if nearer_a(comp) else pole_b).update(comp)
    for i in ids:                              # items sharing no scale with the rest
        if i not in pole_a and i not in pole_b:
            (pole_a if nearer_a([i]) else pole_b).add(i)
    a_ids = sorted(pole_a, key=code_order)
    b_ids = sorted(pole_b, key=code_order)
    if not a_ids or not b_ids:
        return [Pole("a", ids, bipolar, _pole_constructs(ids, items))]
    return [Pole("a", a_ids, bipolar, _pole_constructs(a_ids, items)),
            Pole("b", b_ids, bipolar, _pole_constructs(b_ids, items))]


# --------------------------------------------------------------------------- quality (report only)

def cluster_purity(members: Sequence[str], items: Mapping[str, ItemRow]) -> tuple[Optional[float], dict]:
    """``(purity, constructs)``: the majority construct's share of the cluster's items that carry any scale (an
    item counts for each of its constructs), and the construct counts ("INV:Construct" -> items)."""
    scored = [i for i in members if items[i].scales]
    c = Counter(scale_name(s) for i in scored for s in {scale_name(x): x for x in items[i].scales}.values())
    counts = dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))
    if not scored:
        return None, counts
    return max(c.values()) / len(scored), counts


def purity_metrics(clusters: Sequence[Sequence[str]], items: Mapping[str, ItemRow], *,
                   min_inventory_items: int = 20) -> dict:
    """NMI and ARI of the clustering against the construct labels, overall (items on exactly one scale) and per
    inventory (items on exactly one construct of it), and the size-weighted mean majority-construct purity."""
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    assign = {i: k for k, g in enumerate(clusters) for i in g}

    def scores(pairs):
        if len(pairs) < 2 or len({p for p, _ in pairs}) < 2:
            return {"n": len(pairs), "nmi": None, "ari": None}
        pred = [assign[i] for i, _ in pairs]
        true = [t for _, t in pairs]
        return {"n": len(pairs), "nmi": round(float(normalized_mutual_info_score(true, pred)), 6),
                "ari": round(float(adjusted_rand_score(true, pred)), 6)}
    one = [(i, scale_name(items[i].scales[0])) for i in assign if len({scale_name(s) for s in items[i].scales}) == 1]
    overall = scores(one)
    by_inv = {}
    for inv in sorted({s["inventory"] for i in assign for s in items[i].scales}):
        pairs = []
        for i in assign:
            cons = {s["construct"] for s in items[i].scales if s["inventory"] == inv}
            if len(cons) == 1:
                pairs.append((i, next(iter(cons))))
        if len(pairs) >= min_inventory_items or len(pairs) == len(assign):
            by_inv[inv] = scores(pairs)
    pur, weight = 0.0, 0
    per_cluster = []
    for g in clusters:
        p, _ = cluster_purity(g, items)
        per_cluster.append(p)
        if p is not None:
            n_scored = sum(1 for i in g if items[i].scales)
            pur += p * n_scored
            weight += n_scored
    return {"nmi": overall["nmi"], "ari": overall["ari"], "n_items_scored": overall["n"],
            "purity_mean": round(pur / weight, 6) if weight else None,
            "purity_median": (round(float(np.median([p for p in per_cluster if p is not None])), 6)
                              if any(p is not None for p in per_cluster) else None),
            "by_inventory": by_inv}


def hdbscan_check(E: np.ndarray, seed: int = 0, *, use_umap: bool = True, n_components: int = 20,
                  min_cluster_size: int = 4, reference: Optional[Sequence] = None) -> dict:
    """HDBSCAN on a 20-d UMAP of the vectors (report only, plan 07 § 3's cross-check): cluster count, noise share,
    and the ARI against ``reference`` labels (the agglomerative cut, singletons as their own labels)."""
    from sklearn.cluster import HDBSCAN
    from sklearn.metrics import adjusted_rand_score
    X = np.asarray(E, dtype=np.float64)
    X = X / np.linalg.norm(X, axis=1, keepdims=True)
    if use_umap:
        import umap
        X = umap.UMAP(n_components=n_components, n_neighbors=15, min_dist=0.0, metric="cosine",
                      random_state=seed).fit_transform(X)
    labels = HDBSCAN(min_cluster_size=min_cluster_size).fit_predict(X)
    out = {"n_clusters": int(len(set(labels) - {-1})), "noise_share": round(float(np.mean(labels == -1)), 6),
           "umap": bool(use_umap), "min_cluster_size": min_cluster_size, "seed": seed}
    if reference is not None:
        out["ari_vs_reference"] = round(float(adjusted_rand_score(list(reference), list(labels))), 6)
    return out


def nearest_corpus(groups: Sequence[Sequence[str]], vectors: Mapping[str, np.ndarray], *, corpus: Mapping[str, str],
                   embedder, cache=None, usage: Optional[MultiModelUsage] = None) -> dict[int, dict]:
    """Variant C's ordering column: for each cluster, the corpus trait (``stem -> embedded text``) with the highest
    mean cosine over the cluster's items, and that mean.  Computed after the clusters exist; it changes nothing."""
    from assistant_axis.gapgen.embed import embed_texts
    stems = sorted(corpus)
    if not stems or not groups:
        return {}
    T = embed_texts(embedder, [corpus[s] for s in stems], cache=cache, usage=usage)
    out = {}
    for k, g in enumerate(groups):
        V = np.stack([np.asarray(vectors[i], dtype=np.float64) for i in g])
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        m = (V @ T.T).mean(axis=0)
        j = int(np.argmax(m))
        out[k] = {"stem": stems[j], "mean_cos": round(float(m[j]), 4)}
    return out


def nearest_other_poles(poles: Sequence[tuple], vectors: Mapping[str, np.ndarray]) -> dict:
    """``{(cluster_id, pole): {"cluster_id", "pole", "cos"}}``: for each pole, the nearest pole **of another
    cluster** by centroid cosine (QUESTIONS 50, signal 1 -- "too small shows between clusters").  The other pole
    of the same cluster is excluded on purpose: a bipolar pair is meant to be opposite, and the cross-pole pairs
    of the granularity readings already check that.  ``poles`` is ``[((cluster_id, pole), item ids)]``."""
    keys = [k for k, ids in poles if ids]
    if len(keys) < 2:
        return {}
    cents = []
    for k, ids in poles:
        if not ids:
            continue
        V = np.stack([np.asarray(vectors[i], dtype=np.float64) for i in ids])
        V = V / np.linalg.norm(V, axis=1, keepdims=True)
        m = V.mean(axis=0)
        cents.append(m / (np.linalg.norm(m) or 1.0))
    C = np.stack(cents)
    S = C @ C.T
    out = {}
    for a, key in enumerate(keys):
        best, best_cos = None, -2.0
        for b, other in enumerate(keys):
            if other[0] == key[0]:                 # same cluster (either pole): not an "other cluster"
                continue
            if float(S[a, b]) > best_cos:
                best, best_cos = other, float(S[a, b])
        if best is not None:
            out[key] = {"cluster_id": int(best[0]), "pole": best[1], "cos": round(best_cos, 4)}
    return out


def size_summary(groups: Sequence[Sequence]) -> dict:
    sizes = [len(g) for g in groups]
    if not sizes:
        return {"n": 0}
    return {"n": len(sizes), "items": int(sum(sizes)), "min": int(min(sizes)), "median": float(np.median(sizes)),
            "max": int(max(sizes)), "share_4_to_15": round(sum(1 for s in sizes if 4 <= s <= 15) / len(sizes), 4)}


def _isfinite(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x))


# --------------------------------------------------------------------------- the cluster table

#: Fields a naming run writes on a pole, carried over when the clusters are rebuilt with the same pole.
NAMING_FIELDS = ("blind", "hinted", "labels_disagree")


def table_text(rows: Sequence[Mapping]) -> str:
    import json
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def write_table(rows: Sequence[Mapping], path) -> Optional[object]:
    """Write a cluster table (one JSON object per line); a changed file is first copied to ``.bak.<UTC>``.
    Returns the backup's path, if one was made."""
    import shutil
    from pathlib import Path

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import utc_stamp
    path = Path(path)
    body = table_text(rows)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def load_table(path) -> list[dict]:
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def pole_key(ids: Sequence[str]) -> str:
    return ",".join(sorted(ids, key=code_order))


def build_cluster_table(items: Sequence[ItemRow], vectors: Mapping[str, np.ndarray], *, target: int,
                        primary: str = PRIMARY_ARM, second: str = SECOND_ARM, corpus: Optional[Mapping[str, str]] = None,
                        corpus_embedder=None, cache=None, usage: Optional[MultiModelUsage] = None, seed: int = 0,
                        hdbscan: bool = True, tol: float = DEFAULT_TOL, previous: Sequence[Mapping] = (),
                        min_jaccard: float = MIN_JACCARD) -> tuple[list[dict], dict]:
    """``(rows, summary)`` for one granularity.  ``vectors`` maps an arm name to its ``(n, d)`` rows (items in
    order).  Every cluster of the primary arm's cut gets a row, numbered 1.. by size (``cluster_id``, the
    candidates' ``rank``), with ``consensus`` "kept" or "loose"; ``previous`` rows (an earlier table) give their
    naming fields to poles with the same items."""
    ids = [r.ipip_id for r in items]
    by_id = {r.ipip_id: r for r in items}
    cuts, infos = {}, {}
    for arm in (primary, second):
        cl, info = agglo_clusters(vectors[arm], target_n=target, tol=tol)
        cuts[arm] = [[ids[i] for i in c.members] for c in cl]
        infos[arm] = info
    kept, loose = consensus(cuts[primary], cuts[second], min_jaccard=min_jaccard)
    jac = {pole_key(m.members): m.jaccard for m in kept + loose}
    status = {pole_key(m.members): "kept" for m in kept}
    pvec = {i: vectors[primary][k] for k, i in enumerate(ids)}
    nearest = (nearest_corpus(cuts[primary], pvec, corpus=corpus, embedder=corpus_embedder, cache=cache, usage=usage)
               if corpus and corpus_embedder is not None else {})
    prev = {pole_key(p["items"]): p for r in previous for p in r.get("poles") or []}
    rows = []
    all_poles: list[tuple] = []
    for k, g in enumerate(cuts[primary]):
        pur, cons = cluster_purity(g, by_id)
        poles = split_poles(g, by_id, vectors=pvec)
        pole_rows = []
        for p in poles:
            d = {"pole": p.pole, "items": p.items, "constructs": p.constructs}
            old = prev.get(pole_key(p.items))
            if old:
                d.update({f: old[f] for f in NAMING_FIELDS if f in old})
            pole_rows.append(d)
            all_poles.append(((k + 1, p.pole), p.items))
        rows.append({"schema_version": 1, "granularity": int(target), "cluster_id": k + 1,
                     "consensus": status.get(pole_key(g), "loose"), "embedder": primary,
                     f"jaccard_vs_{second}": jac.get(pole_key(g)), "items": list(g), "constructs": cons,
                     "purity": round(pur, 4) if pur is not None else None, "bipolar": len(poles) == 2,
                     "bipolar_scales": poles[0].bipolar_scales, "nearest_corpus": nearest.get(k), "poles": pole_rows})
    # QUESTIONS 50 signal 1: each pole's nearest pole of another cluster, written on the pole row so that the
    # granularity command needs no vectors.  Kept apart from `nearest_corpus`, which is novelty, not size.
    nearest_other = nearest_other_poles(all_poles, pvec)
    for r in rows:
        for p in r["poles"]:
            got = nearest_other.get((int(r["cluster_id"]), p["pole"]))
            if got:
                p["nearest_other"] = got
    kept_groups = [r["items"] for r in rows if r["consensus"] == "kept"]
    summary = {
        "granularity": int(target), "n_items": len(ids), "primary": primary, "second": second,
        "cut": infos, "consensus": {"min_jaccard": min_jaccard, "n_kept": len(kept), "n_loose": len(loose),
                                    "loose_items": sum(len(m.members) for m in loose),
                                    "jaccard_kept_median": (round(float(np.median([m.jaccard for m in kept])), 4)
                                                            if kept else None)},
        "sizes": {"primary": size_summary(cuts[primary]), "second": size_summary(cuts[second]),
                  "kept": size_summary(kept_groups)},
        "purity": {primary: purity_metrics(cuts[primary], by_id), second: purity_metrics(cuts[second], by_id),
                   "kept": purity_metrics(kept_groups, by_id)},
        "bipolar": {"n_clusters": sum(1 for r in rows if r["bipolar"]),
                    "n_kept": sum(1 for r in rows if r["bipolar"] and r["consensus"] == "kept")},
        "n_poles_kept": sum(len(r["poles"]) for r in rows if r["consensus"] == "kept"),
        "naming_carried_over": sum(1 for r in rows for p in r["poles"] if "blind" in p),
    }
    if hdbscan:
        ref = {i: k for k, g in enumerate(cuts[primary]) for i in g}
        labels = [ref.get(i, -10 - n) for n, i in enumerate(ids)]
        summary["hdbscan"] = hdbscan_check(vectors[primary], seed=seed, reference=labels)
    return rows, summary
