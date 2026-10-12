"""Embed the items, cluster them at each granularity, decide which clusters are kept (R2), split poles.

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
* **Consensus** (:func:`consensus`), two rules (``CONSENSUS_RULES``).  **R2, the default since 2026-10-12** (gate
  audit 4, ``reports/code_review_2026-10-12/gate_audits/ipip_consensus.md``, accepted by Roger the same day):
  every cluster of 3 or more items is kept; a 2-item cluster is kept only when the second arm puts both items in one
  of its clusters (any size); the rest are held on the loose pile (plan § 10 decision (d)).  The audit found the
  second arm's agreement says nothing about the coherence of a 3+ cluster and a good deal about a pair.  **The old
  rule**, ``jaccard`` (plan 07 § 3), kept for reproducing the May readings: the primary arm's clusters matched one
  to one to the other arm's by Jaccard, greedily from the highest, kept when the match reaches ``min_jaccard``
  (0.5).  Every row records ``consensus_reason`` and, whatever the rule, the Jaccard column as the old rule
  computed it, the one-to-one partner and the core (the most of its items in one cluster of the other arm).
* **Size ceiling** (gate audit 4, P2; :func:`build_cluster_table`'s ``size_ceiling``): at a coarse cut, a cluster
  above the ceiling (a domain-level blob, 50-240 items at ~150) is replaced by the clusters of a finer cut of the
  same tree inside it (``recut_targets``, by default ~350 and then, past the ceiling again, ~600), which keep their
  own consensus at that cut.  The pieces are numbered after the coarse cut's clusters (cut offset + their id in the
  finer cut), so the ids of the clusters left whole never change and no id is reused for another cluster when the
  ceiling changes.
* **Names across tables**: a pole gets the names an earlier table of its own cut gave it (``previous``), and, for
  a form still missing, the names any other cut's table gave a pole with the same items (``carry_from``; a ~600
  piece at a coarser cut keeps its ~600 name), marked ``carried_from``.
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
from typing import Collection, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.judge_pricing import MultiModelUsage

from . import GRANULARITIES
from .ingest import ItemRow, code_order

PRIMARY_ARM = "openai"
SECOND_ARM = "gemma"
DEFAULT_TOL = 0.1
#: The old rule's bar (plan 07 § 3; no derivation recorded, gate audit 4 § 8).  Under R2 it only decides which
#: Jaccard value a row records (the matched one when it reaches the bar, the best one otherwise).
MIN_JACCARD = 0.5
#: ``r2``: keep 3+ clusters, and a pair the second arm co-clusters (gate audit 4, P1; Roger 2026-10-12).
#: ``jaccard``: the old rule, kept for reproducing the readings made under it.
CONSENSUS_RULES: tuple[str, ...] = ("r2", "jaccard")
DEFAULT_CONSENSUS = "r2"
R2_MIN_SIZE = 3
#: Gate audit 4, P2: at a coarse cut, a cluster above about 30 items is replaced by its clusters at a finer cut
#: (the ~600 clusters inside it).  The ~600 cut's own largest cluster is 33 items, and its 10+ clusters read as
#: coherent; the blobs it is meant for are 48-242 items (g150 #15, 48 items, read as incoherent).
DEFAULT_SIZE_CEILING = 30
#: The finer cuts a cluster over the ceiling is re-cut at, coarse to fine: every granularity but the coarsest, so
#: (350, 600).  A ~150 blob goes to its ~350 clusters first and only those still over the ceiling to ~600, which
#: keeps the ~150 table coarser than the ~350 one (straight to ~600 it had more rows: 444 against 405).  Fable,
#: 2026-10-12.
DEFAULT_RECUT_TARGETS: tuple[int, ...] = tuple(sorted(GRANULARITIES))[1:]


def default_size_ceiling(rule: str) -> Optional[int]:
    """The ceiling a rule runs with unless told otherwise: P2's 30 under R2, none under the old rule (which had
    none, so that ``jaccard`` reproduces the old tables)."""
    return DEFAULT_SIZE_CEILING if rule == "r2" else None


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
    jaccard: float                       # the matched Jaccard when it reaches min_jaccard, else the best (any rule)
    partner: Optional[int] = None        # the one-to-one matched cluster's index in the other arm
    core: int = 0                        # the most of the cluster's items that share one cluster of the other arm
    core_partner: Optional[int] = None   # that cluster's index in the other arm (the lowest index on a tie)
    reason: str = ""                     # why kept or held, in the rule's words


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def consensus(a: Sequence[Sequence], b: Sequence[Sequence], *, rule: str = DEFAULT_CONSENSUS,
              min_jaccard: float = MIN_JACCARD) -> tuple[list[Matched], list[Matched]]:
    """``(kept, loose)`` of the clusters of ``a`` (the primary arm's) against ``b`` (the second arm's cut).

    Whatever the rule, every cluster is matched one to one by Jaccard against ``b`` (highest first; ties by index)
    and carries the matched Jaccard when it reaches ``min_jaccard``, its best Jaccard against any cluster of ``b``
    otherwise (the old rule's column), the partner, and its core (``Matched.core``).  ``rule`` decides:

    * ``"r2"``: kept when it has 3 or more items (reason ``size>=3``), or 2 items that share one cluster of ``b``
      (``pair_coclustered``); held otherwise (``pair_not_coclustered``).
    * ``"jaccard"``: kept when the one-to-one match reaches ``min_jaccard`` (``jaccard>=0.5`` / ``jaccard<0.5``),
      exactly the rule before 2026-10-12.

    Both lists keep ``a``'s order."""
    if rule not in CONSENSUS_RULES:
        raise ValueError(f"rule must be one of {CONSENSUS_RULES}, got {rule!r}")
    sa = [set(x) for x in a]
    sb = [set(x) for x in b]
    where: dict = defaultdict(set)
    for j, s in enumerate(sb):
        for x in s:
            where[x].add(j)
    pairs, best = [], [0.0] * len(sa)
    core, core_j = [0] * len(sa), [None] * len(sa)
    for i, s in enumerate(sa):
        for j in sorted(set().union(*(where[x] for x in s)) if s else ()):
            jac = _jaccard(s, sb[j])
            pairs.append((-jac, i, j))
            best[i] = max(best[i], jac)
            shared = len(s & sb[j])
            if shared > core[i]:
                core[i], core_j[i] = shared, j
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
        j_keep = j is not None and jac >= min_jaccard
        if rule == "jaccard":
            keep = j_keep
            reason = f"jaccard>={min_jaccard:g}" if keep else f"jaccard<{min_jaccard:g}"
        elif len(sa[i]) >= R2_MIN_SIZE:
            keep, reason = True, f"size>={R2_MIN_SIZE}"
        elif len(sa[i]) == 2:
            keep = core[i] == 2
            reason = "pair_coclustered" if keep else "pair_not_coclustered"
        else:
            keep, reason = False, "singleton"
        m = Matched(list(members), round(jac if j_keep else best[i], 6), j, core[i], core_j[i], reason)
        (kept if keep else loose).append(m)
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


def nearest_other_poles(poles: Sequence[tuple], vectors: Mapping[str, np.ndarray], *,
                        among: Optional[Collection] = None) -> dict:
    """``{(cluster_id, pole): {"cluster_id", "pole", "cos"}}``: for each pole, the nearest pole **of another
    cluster** by centroid cosine (QUESTIONS 50, signal 1 -- "too small shows between clusters").  The other pole
    of the same cluster is excluded on purpose: a bipolar pair is meant to be opposite, and the cross-pole pairs
    of the granularity readings already check that.  ``poles`` is ``[((cluster_id, pole), item ids)]``.
    ``among`` (pole keys), when given, limits the poles that can be chosen as a nearest one: the table passes the
    kept poles, the only ones ever named, so that signal 1 is never dropped for a neighbour on the loose pile
    (review 5 D3; gate audit 4, P6)."""
    keys = [k for k, ids in poles if ids]
    if len(keys) < 2:
        return {}
    allowed = None if among is None else set(among)
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
            if allowed is not None and other not in allowed:
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
NAMING_FORMS = ("blind", "hinted")


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


#: Row schema: 2 since 2026-10-12 (R2): ``consensus_reason``, ``partner_vs_<arm>``, ``core_vs_<arm>``,
#: ``recut_from`` on the pieces of a re-cut cluster, and ``nearest_other`` chosen among the kept poles
#: (``"among": "kept"``).
TABLE_SCHEMA_VERSION = 2


def _counts_by(xs) -> dict:
    return dict(sorted(Counter(xs).items()))


def build_cluster_table(items: Sequence[ItemRow], vectors: Mapping[str, np.ndarray], *, target: int,
                        primary: str = PRIMARY_ARM, second: str = SECOND_ARM, corpus: Optional[Mapping[str, str]] = None,
                        corpus_embedder=None, cache=None, usage: Optional[MultiModelUsage] = None, seed: int = 0,
                        hdbscan: bool = True, tol: float = DEFAULT_TOL, previous: Sequence[Mapping] = (),
                        min_jaccard: float = MIN_JACCARD, rule: str = DEFAULT_CONSENSUS,
                        size_ceiling: Optional[int] = None, recut_targets: Sequence[int] = (),
                        carry_from: Sequence[tuple[int, Sequence[Mapping]]] = ()) -> tuple[list[dict], dict]:
    """``(rows, summary)`` for one granularity.  ``vectors`` maps an arm name to its ``(n, d)`` rows (items in
    order).  Every cluster of the primary arm's cut gets a row, numbered 1.. by size (``cluster_id``, the
    candidates' ``rank``), with ``consensus`` "kept" or "loose" under ``rule`` (:func:`consensus`) and the reason;
    ``previous`` rows (an earlier table) give their naming fields to poles with the same items.

    **Size ceiling** (gate audit 4, P2): with ``size_ceiling`` set and a ``recut_targets`` cut finer than
    ``target``, a cluster of more than ``size_ceiling`` items is not a row: the clusters of the next finer cut
    inside it are (and, past the ceiling again, those of the cut after that; the finest cut's are kept whatever
    their size).  A piece keeps its own cut's consensus (the same status and columns it has in that cut's table),
    is numbered after the clusters of the coarser cuts (``cluster_id`` = the cut's offset + its id in that cut, so
    ids never collide or move when the ceiling changes), and records ``recut_from`` (the cluster it was cut from,
    the cut, its id there).  Items a finer cut leaves single drop out of the table.  The summary's
    ``consensus.before_ceiling`` gives the rule's counts on the uncut table.

    **Names across cuts**: ``carry_from`` is ``[(granularity, rows)]`` of the other cuts' tables, first match wins
    (pass the finest first).  A naming form a pole has no name for in ``previous`` is taken from a pole with the same
    items there, with ``carried_from`` (granularity, cluster id, pole of the table that named it) in the naming
    record, so that a ~600 piece re-cut into a coarser table keeps its ~600 name instead of being named again.

    Each pole's ``nearest_other`` (QUESTIONS 50 signal 1) is chosen among the **kept** poles, the only ones ever
    named (review 5 D3)."""
    ids = [r.ipip_id for r in items]
    by_id = {r.ipip_id: r for r in items}
    target = int(target)
    trees: dict = {}
    cut_memo: dict = {}
    decided_memo: dict = {}

    def cut(arm: str, t: int) -> tuple[list, dict]:
        """One arm's cut at ``t`` (item ids), from that arm's one tree."""
        if (arm, t) not in cut_memo:
            if arm not in trees and len(ids) >= 2:
                trees[arm] = _linkage(vectors[arm])
            cl, info = agglo_clusters(vectors[arm], target_n=t, tol=tol, Z=trees.get(arm))
            cut_memo[(arm, t)] = ([[ids[i] for i in c.members] for c in cl], info)
        return cut_memo[(arm, t)]

    def decided(t: int) -> dict:
        """``{pole_key(members): ("kept" | "loose", Matched)}`` for the primary arm's cut at ``t``."""
        if t not in decided_memo:
            kept_t, loose_t = consensus(cut(primary, t)[0], cut(second, t)[0], rule=rule, min_jaccard=min_jaccard)
            decided_memo[t] = {**{pole_key(m.members): ("kept", m) for m in kept_t},
                               **{pole_key(m.members): ("loose", m) for m in loose_t}}
        return decided_memo[t]

    def status_of(members: Sequence[str], t: int) -> tuple[str, Matched]:
        got = decided(t).get(pole_key(members))
        if got is None:              # a piece that is not a whole cluster of its cut (cuts that do not nest)
            kept_p, loose_p = consensus([list(members)], cut(second, t)[0], rule=rule, min_jaccard=min_jaccard)
            got = ("kept", kept_p[0]) if kept_p else ("loose", loose_p[0])
        return got

    coarse = cut(primary, target)[0]
    finer = sorted({int(t) for t in recut_targets if int(t) > target}) if size_ceiling else []
    offset, n_before = {target: 0}, len(coarse)
    for t in finer:
        offset[t] = n_before
        n_before += len(cut(primary, t)[0])
    groups: list[tuple] = []          # (cluster_id, members, cut, recut_from or None)

    def place(members: list, t: int, local_id: int, origin: Optional[dict]) -> None:
        deeper = [u for u in finer if u > t]
        if size_ceiling and len(members) > size_ceiling and deeper:
            u, mem = deeper[0], set(members)
            origin = origin or {"cluster_id": local_id, "size": len(members)}
            for k, f in enumerate(cut(primary, u)[0]):
                piece = [x for x in f if x in mem]
                if len(piece) >= 2:
                    place(piece, u, k + 1, origin)
            return
        groups.append((offset[t] + local_id, members, t, origin))
    for k, g in enumerate(coarse):
        place(list(g), target, k + 1, None)
    groups.sort(key=lambda x: x[0])

    pvec = {i: vectors[primary][k] for k, i in enumerate(ids)}
    final = [g for _cid, g, _t, _o in groups]
    nearest = (nearest_corpus(final, pvec, corpus=corpus, embedder=corpus_embedder, cache=cache, usage=usage)
               if corpus and corpus_embedder is not None else {})
    prev = {pole_key(p["items"]): p for r in previous for p in r.get("poles") or []}
    named_elsewhere: dict = {}
    for g_other, rows_other in carry_from:
        for r in rows_other:
            for p in r.get("poles") or []:
                if any(p.get(f) for f in NAMING_FORMS):
                    named_elsewhere.setdefault(pole_key(p["items"]), (int(g_other), int(r["cluster_id"]), p))
    n_carried_across = 0
    rows = []
    all_poles: list[tuple] = []
    kept_poles: set = set()
    for n, (cid, g, t, origin) in enumerate(groups):
        status, m = status_of(g, t)
        sb = cut(second, t)[0]
        pur, cons = cluster_purity(g, by_id)
        poles = split_poles(g, by_id, vectors=pvec)
        pole_rows = []
        for p in poles:
            d = {"pole": p.pole, "items": p.items, "constructs": p.constructs}
            old = prev.get(pole_key(p.items))
            if old:
                d.update({f: old[f] for f in NAMING_FIELDS if f in old})
            other = named_elsewhere.get(pole_key(p.items))
            missing = [f for f in NAMING_FORMS if not d.get(f) and other and other[2].get(f)]
            if missing:
                g_o, cid_o, po = other
                for f in missing:
                    d[f] = {**po[f], "carried_from": po[f].get("carried_from")
                            or {"granularity": g_o, "cluster_id": cid_o, "pole": po["pole"]}}
                if d.get("blind") and d.get("hinted"):       # as `name` sets it
                    d["labels_disagree"] = d["blind"].get("stem") != d["hinted"].get("stem")
                n_carried_across += 1
            pole_rows.append(d)
            all_poles.append(((cid, p.pole), p.items))
            if status == "kept":
                kept_poles.add((cid, p.pole))
        row = {"schema_version": TABLE_SCHEMA_VERSION, "granularity": target, "cluster_id": cid,
               "consensus": status, "consensus_reason": m.reason, "embedder": primary,
               f"jaccard_vs_{second}": m.jaccard,
               # review columns (gate audit 4, P1): the one-to-one partner and the core, as clusters of the second
               # arm's cut at the row's cut, numbered as this module orders a cut (largest first), 1..
               f"partner_vs_{second}": ({"cluster": m.partner + 1, "size": len(sb[m.partner])}
                                        if m.partner is not None else None),
               f"core_vs_{second}": {"n": m.core, **({"cluster": m.core_partner + 1, "size": len(sb[m.core_partner])}
                                                    if m.core_partner is not None else {})},
               "items": list(g), "constructs": cons, "purity": round(pur, 4) if pur is not None else None,
               "bipolar": len(poles) == 2, "bipolar_scales": poles[0].bipolar_scales,
               "nearest_corpus": nearest.get(n)}
        if origin:
            row["recut_from"] = {**origin, "cut": t, "cut_cluster_id": cid - offset[t]}
        row["poles"] = pole_rows
        rows.append(row)
    # QUESTIONS 50 signal 1: each pole's nearest pole of another cluster, among the kept poles (the only ones ever
    # named, so that no reading is dropped for a loose neighbour: review 5 D3), written on the pole row so that the
    # granularity command needs no vectors.  Kept apart from `nearest_corpus`, which is novelty, not size.
    nearest_other = nearest_other_poles(all_poles, pvec, among=kept_poles)
    for r in rows:
        for p in r["poles"]:
            got = nearest_other.get((int(r["cluster_id"]), p["pole"]))
            if got:
                p["nearest_other"] = {**got, "among": "kept"}
    kept_rows = [r for r in rows if r["consensus"] == "kept"]
    loose_rows = [r for r in rows if r["consensus"] != "kept"]
    kept_groups = [r["items"] for r in kept_rows]
    uncut = [status_of(g, target) for g in coarse]
    table_items = {i for r in rows for i in r["items"]}
    pole_keys_now = {pole_key(p["items"]) for r in rows for p in r["poles"]}
    recut_rows = [r for r in rows if r.get("recut_from")]
    blobs = {}
    for r in recut_rows:
        b = blobs.setdefault(r["recut_from"]["cluster_id"], {"cluster_id": r["recut_from"]["cluster_id"],
                                                             "size": r["recut_from"]["size"], "n_pieces": 0,
                                                             "n_pieces_kept": 0, "piece_items": 0})
        b["n_pieces"] += 1
        b["n_pieces_kept"] += int(r["consensus"] == "kept")
        b["piece_items"] += len(r["items"])
    summary = {
        "granularity": target, "n_items": len(ids), "primary": primary, "second": second,
        "cut": {primary: cut(primary, target)[1], second: cut(second, target)[1]},
        "consensus": {"rule": rule, "min_jaccard": min_jaccard,
                      "r2_min_size": R2_MIN_SIZE if rule == "r2" else None,
                      "n_kept": len(kept_rows), "n_loose": len(loose_rows),
                      "kept_items": sum(len(r["items"]) for r in kept_rows),
                      "loose_items": sum(len(r["items"]) for r in loose_rows),
                      "jaccard_kept_median": (round(float(np.median([r[f"jaccard_vs_{second}"] for r in kept_rows])), 4)
                                              if kept_rows else None),
                      "reasons": _counts_by(r["consensus_reason"] for r in rows),
                      "before_ceiling": {"n_kept": sum(1 for s, _m in uncut if s == "kept"),
                                         "n_loose": sum(1 for s, _m in uncut if s != "kept"),
                                         "kept_items": sum(len(m.members) for s, m in uncut if s == "kept"),
                                         "loose_items": sum(len(m.members) for s, m in uncut if s != "kept"),
                                         "reasons": _counts_by(m.reason for _s, m in uncut)}},
        "ceiling": {"size_ceiling": size_ceiling, "recut_targets": list(finer),
                    "n_recut": len(blobs), "recut_items": sum(b["size"] for b in blobs.values()),
                    "n_pieces": len(recut_rows), "n_pieces_kept": sum(1 for r in recut_rows if r["consensus"] == "kept"),
                    "items_left_single": sum(len(g) for g in coarse) - len(table_items),
                    "blobs": [blobs[k] for k in sorted(blobs)],
                    "cuts": {str(t): {primary: cut(primary, t)[1], second: cut(second, t)[1]} for t in finer}},
        "n_rows": len(rows),
        "sizes": {"primary": size_summary(coarse), "second": size_summary(cut(second, target)[0]),
                  "table": size_summary(final), "kept": size_summary(kept_groups)},
        "purity": {primary: purity_metrics(coarse, by_id), second: purity_metrics(cut(second, target)[0], by_id),
                   "kept": purity_metrics(kept_groups, by_id)},
        "bipolar": {"n_clusters": sum(1 for r in rows if r["bipolar"]),
                    "n_kept": sum(1 for r in kept_rows if r["bipolar"])},
        "n_poles_kept": sum(len(r["poles"]) for r in kept_rows),
        "nearest_other_among": "kept",
        "naming_carried_over": sum(1 for r in rows for p in r["poles"] if "blind" in p),
        "naming_carried_across_cuts": n_carried_across,
        # named poles of the previous table whose items no pole of this one has (a re-cut, a changed cut)
        "naming_not_carried": sum(1 for k, p in prev.items() if any(p.get(f) for f in ("blind", "hinted"))
                                  and k not in pole_keys_now),
    }
    if hdbscan:
        ref = {i: k for k, g in enumerate(coarse) for i in g}
        labels = [ref.get(i, -10 - n) for n, i in enumerate(ids)]
        summary["hdbscan"] = hdbscan_check(vectors[primary], seed=seed, reference=labels)
    return rows, summary
