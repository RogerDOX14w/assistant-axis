"""Concept units: which kept candidates are one concept, read from the all-batches review graph (plan 13 decision 2,
Roger 2026-10-13: both units computed on every dashboard, the headline chosen on data).

* ``components_4``: the connected components of 4-edges (both directions read 4 on rubric A, what the review merges).
  The strict unit: it splits real concepts but seldom joins wrong ones.
* ``grown_3``: the 4-components grown across 3-links (:func:`grow`).  Two units joined by at least one 3-edge merge,
  the pair with the highest cross-link density first (cross 3-links over the product of their sizes; ties by the
  units' sorted keys), only while the merged unit keeps at least ``tau`` (0.67) of its pairs linked at 3 or above;
  passes repeat until nothing merges.  A density test on the merged unit, not on the two being merged, is what
  stops a chain: a chain's density falls with every link.  ``tau`` 0.5 and 0.8 are printed as sensitivity.
* ``components_3``: the connected components of 3-edges, the chain diagnostic only (on 2026-10-13 one component holds
  1,028 of the 3,835 kept candidates).

:func:`review_agreement` scores a unit against Roger's own decisions, rebuilt from every review log each time: the
ground truth is each decided candidate's final concept (accepted: itself; merged: its target, followed
transitively), giving **kept together** (the share of same-concept pairs in one unit), **one concept** (the share of
decided pairs sharing a unit that Roger made one concept) and **hard negatives joined** (pairs from ``distinct`` and
``drop`` events against the group's members, the graph having grouped them, that a unit puts together).

:func:`concept_table` is ``concepts.json``'s record of one unit: per concept its keys, mechanisms (states-pass rows
attributed to the source row's generator when registry rows are given), most common region, generators and decided
status; the counts by mechanism, the occasion pairs' overlaps and the incidence counts the estimators read.
"""
from __future__ import annotations

import itertools
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from . import independence as IND
from .repetition import adjacency, kept_nodes, node_generators, pair_levels, review_into, review_status

UNITS: tuple[str, ...] = ("components_4", "grown_3", "components_3")
DEFAULT_TAU = 0.67
SENSITIVITY_TAUS: tuple[float, ...] = (0.5, 0.8)
#: A generator's mechanism when only its name is known (a graph node); wn_clusters' two streams share one.
GENERATOR_MECHANISM: dict[str, Optional[str]] = {}
for (_g, _s), _rule in IND.STREAMS.items():
    GENERATOR_MECHANISM.setdefault(_g, _rule.mechanism)


def components(graph: Mapping, *, level: int = 4, keys: Optional[Iterable[str]] = None,
               adj: Optional[Mapping[str, set]] = None) -> list[set[str]]:
    """The connected components of the ``level``-edges over the kept terms (singletons included), each a set,
    ordered by their smallest key."""
    ks = sorted(keys) if keys is not None else sorted(kept_nodes(graph))
    adj = adj if adj is not None else adjacency(graph, level)
    seen: set[str] = set()
    out = []
    for k in ks:
        if k in seen:
            continue
        comp, stack = set(), [k]
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x)
            stack.extend(y for y in adj.get(x, ()) if y not in comp)
        seen |= comp
        out.append(comp)
    return out


def _internal(unit: set, adj3: Mapping[str, set]) -> int:
    return sum(len(adj3.get(x, set()) & unit) for x in unit) // 2


def grow(graph: Mapping, *, seeds: Sequence[set], tau: float = DEFAULT_TAU,
         adj3: Optional[Mapping[str, set]] = None) -> list[set[str]]:
    """The seeds (normally the 4-components) merged across 3-links while the merged unit's density (its pairs
    linked at 3 or above over all its pairs) stays at or above ``tau`` (module docstring).  Deterministic: in each
    pass the candidate merges are ordered by cross-link density (highest first), then by the two units' smallest
    keys; each is tested on the units as they stand when its turn comes.  Returns the units ordered by smallest key."""
    adj3 = adj3 if adj3 is not None else adjacency(graph, 3)
    units: dict[str, set[str]] = {}
    of: dict[str, str] = {}
    for s in seeds:
        s = set(s)
        uid = min(s)
        units[uid] = s
        for x in s:
            of[x] = uid
    inner = {u: _internal(s, adj3) for u, s in units.items()}
    while True:
        cross: Counter = Counter()
        for x, ys in adj3.items():
            if x not in of:
                continue
            for y in ys:
                if y in of:
                    i, j = of[x], of[y]
                    if i < j:
                        cross[(i, j)] += 1
        order = sorted(cross, key=lambda p: (-cross[p] / (len(units[p[0]]) * len(units[p[1]])), p[0], p[1]))
        merged = False
        for i, j in order:
            if i not in units or j not in units or i == j:
                continue
            a, b = units[i], units[j]
            n = len(a) + len(b)
            links = sum(len(adj3.get(x, set()) & b) for x in a)
            if not links:
                continue
            dens = (inner[i] + inner[j] + links) / (n * (n - 1) / 2)
            if dens < tau:
                continue
            keep, gone = (i, j) if i < j else (j, i)
            units[keep] = a | b
            inner[keep] = inner[i] + inner[j] + links
            for x in units[gone] if gone in units else ():
                of[x] = keep
            for x in units[keep]:
                of[x] = keep
            del units[gone], inner[gone]
            merged = True
        if not merged:
            break
    return [units[u] for u in sorted(units)]


def build_units(graph: Mapping, unit: str, *, tau: float = DEFAULT_TAU, cache: Optional[dict] = None) -> list[set]:
    """The units of one kind (``components_4``, ``grown_3`` at ``tau``, ``components_3``); ``cache`` reuses the
    adjacencies across calls."""
    cache = cache if cache is not None else {}
    if "levels" not in cache:
        cache["levels"] = pair_levels(graph)
        cache["adj3"] = adjacency(graph, 3, levels=cache["levels"])
        cache["adj4"] = adjacency(graph, 4, levels=cache["levels"])
        cache["keys"] = sorted(kept_nodes(graph))
    if unit == "components_4":
        if "c4" not in cache:
            cache["c4"] = components(graph, keys=cache["keys"], adj=cache["adj4"])
        return cache["c4"]
    if unit == "components_3":
        return components(graph, keys=cache["keys"], adj=cache["adj3"])
    if unit == "grown_3":
        return grow(graph, seeds=build_units(graph, "components_4", cache=cache), tau=tau, adj3=cache["adj3"])
    raise ValueError(f"unit must be one of {UNITS}, not {unit!r}")


# --------------------------------------------------------------------------- agreement with the review

def final_concept(key: str, nodes: Mapping[str, Mapping], rows: Optional[Mapping[str, Mapping]] = None) -> str:
    """A decided candidate's final concept: itself when promoted, its merge target when merged (followed through
    targets that were merged in turn); a target outside the graph (a corpus trait ``trait:x``, a queue entry) ends
    the walk."""
    seen = []
    k = key
    while k in nodes and k not in seen:
        seen.append(k)
        if review_status(nodes[k], rows) == "merged_into" and review_into(nodes[k], rows):
            k = review_into(nodes[k], rows)
            continue
        break
    return k


def hard_negatives(review_dirs: Iterable[Path], kept: set) -> set[frozenset]:
    """Pairs Roger kept apart after the graph had grouped them: a ``distinct`` key against the group's members as
    opened or resolved, and a ``drop``ped key against the members it was dropped from (a dropped key leaves the
    group, so two drops from one group are not a pair); undone events left out; pairs of kept terms only.  Keys a
    group took by ``extend`` (the leftovers pass) are Roger's additions, not the graph's grouping, and are left out,
    as in decision 2's prototype."""
    from .review_minutes import load_events
    neg: set[frozenset] = set()
    for d in review_dirs:
        groups: dict[str, list[str]] = {}
        for e in load_events(d):
            gid = e.group
            if e.action in ("open", "resolve") and e.members:
                groups[gid] = list(e.members)
            if e.action == "distinct":
                ks = list(e.raw.get("keys") or [])
            elif e.action == "drop":
                ks = [e.raw.get("key")] if e.raw.get("key") else []
            else:
                continue
            for k in ks:
                for m in groups.get(gid, []):
                    if m != k and k in kept and m in kept:
                        neg.add(frozenset((k, m)))
            if e.action == "drop" and gid in groups:
                groups[gid] = [m for m in groups[gid] if m != e.raw.get("key")]
    return neg


@dataclass
class Agreement:
    kept_together: Optional[float]
    one_concept: Optional[float]
    hard_negatives_joined: int
    n_pairs: int                    # same-concept pairs among decided candidates
    n_negatives: int
    n_decided: int = 0
    n_concepts: int = 0
    n_same_unit_pairs: int = 0
    n_kept_together: int = 0
    n_one_concept: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def review_agreement(units: Sequence[set], review_dirs: Iterable[Path], graph: Mapping, *,
                     rows: Optional[Mapping[str, Mapping]] = None) -> Agreement:
    """Decision 2's agreement table for one unit (module docstring).  Decided: kept terms accepted or merged (a
    rejected term is no concept)."""
    nodes = kept_nodes(graph)
    allnodes = {n["key"]: n for n in graph["nodes"]}
    decided = sorted(k for k in nodes if review_status(nodes[k], rows) in ("accepted", "merged_into"))
    label = {k: final_concept(k, allnodes, rows) for k in decided}
    of = {x: i for i, u in enumerate(units) for x in u}
    same = [(a, b) for a, b in itertools.combinations(decided, 2) if label[a] == label[b]]
    in_unit = [(a, b) for a, b in itertools.combinations(decided, 2) if a in of and of.get(a) == of.get(b)]
    neg = {p for p in hard_negatives(review_dirs, set(nodes))
           if not (all(x in label for x in p) and len({label[x] for x in p}) == 1)}
    kt = sum(1 for a, b in same if of.get(a) is not None and of.get(a) == of.get(b))
    oc = sum(1 for a, b in in_unit if label[a] == label[b])
    joined = sum(1 for p in neg if len({of.get(x) for x in p}) == 1 and None not in {of.get(x) for x in p})

    def sh(n, d):
        return round(n / d, 4) if d else None
    return Agreement(kept_together=sh(kt, len(same)), one_concept=sh(oc, len(in_unit)), hard_negatives_joined=joined,
                     n_pairs=len(same), n_negatives=len(neg), n_decided=len(decided),
                     n_concepts=len(set(label.values())), n_same_unit_pairs=len(in_unit), n_kept_together=kt,
                     n_one_concept=oc)


# --------------------------------------------------------------------------- the concept table

def node_mechanisms(node: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> list[str]:
    """A kept term's mechanisms: from its registry row with the states pass attributed when ``rows`` has it, else
    from the node's generators (a states-pass generator then gives none)."""
    if rows is not None and node.get("key") in rows:
        return IND.mechanisms_of(rows[node["key"]], rows)
    return list(dict.fromkeys(m for g in node_generators(node) if (m := GENERATOR_MECHANISM.get(g))))


def node_generators_attributed(node: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> list[str]:
    if rows is not None and node.get("key") in rows:
        return IND.generators_of(rows[node["key"]], rows)
    return [g for g in node_generators(node) if g not in IND.POOL_GENERATORS + IND.ATTRIBUTED_GENERATORS]


@dataclass
class ConceptTable:
    unit: str
    tau: Optional[float]
    n_concepts: int
    n_singletons: int
    largest: int
    sizes: dict
    by_mechanism: dict
    pairs: list
    incidence: dict
    by_region: dict
    concepts: list = field(default_factory=list)
    occasions: tuple = ()

    def as_dict(self, *, with_concepts: bool = True) -> dict:
        d = asdict(self)
        if not with_concepts:
            d.pop("concepts")
        return d


def concept_table(graph: Mapping, *, unit: str, units: Optional[Sequence[set]] = None, tau: Optional[float] = None,
                  rows: Optional[Mapping[str, Mapping]] = None,
                  occasions: Sequence[str] = IND.OCCASION_MECHANISMS) -> ConceptTable:
    """``concepts.json``'s record of one unit (module docstring).  ``pairs``: per pair of ``occasions`` present,
    ``n1``, ``n2`` (concepts each occasion caught) and ``m`` (caught by both); ``incidence``: concepts by the number
    of ``occasions`` that caught them (``"1"``, ``"2"``, ``"3+"``, and ``"by_k"`` exact)."""
    nodes = kept_nodes(graph)
    units = units if units is not None else build_units(graph, unit, tau=tau or DEFAULT_TAU)
    concepts = []
    by_mech, by_region, inc = Counter(), defaultdict(Counter), Counter()
    caught: dict[str, set] = defaultdict(set)
    for i, u in enumerate(sorted(units, key=lambda u: (-len(u), min(u)))):
        keys = sorted(u)
        mechs = sorted({m for k in keys for m in node_mechanisms(nodes[k], rows)})
        gens = sorted({g for k in keys for g in node_generators_attributed(nodes[k], rows)})
        regions = Counter(nodes[k].get("region") for k in keys if nodes[k].get("region"))
        region = sorted(regions.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if regions else None
        statuses = Counter(review_status(nodes[k], rows) for k in keys if review_status(nodes[k], rows))
        decided = sorted(statuses.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if statuses else None
        concepts.append({"id": i, "keys": keys, "mechanisms": mechs, "generators": gens, "region": region,
                         "decided": decided})
        for m in mechs:
            by_mech[m] += 1
            caught[m].add(i)
            by_region[region or "none"][m] += 1
        k_occ = len(set(mechs) & set(occasions))
        if k_occ:
            inc[k_occ] += 1
        by_region[region or "none"]["_concepts"] += 1
    present = [m for m in occasions if caught.get(m)]
    pairs = [{"a": a, "b": b, "n1": len(caught[a]), "n2": len(caught[b]), "m": len(caught[a] & caught[b])}
             for a, b in itertools.combinations(present, 2)]
    sizes = Counter(len(u) for u in units)
    return ConceptTable(
        unit=unit, tau=tau if unit == "grown_3" else None, n_concepts=len(units),
        n_singletons=sizes.get(1, 0), largest=max(sizes) if sizes else 0,
        sizes={str(k): v for k, v in sorted(sizes.items())}, by_mechanism=dict(sorted(by_mech.items())),
        pairs=pairs, incidence={"1": inc.get(1, 0), "2": inc.get(2, 0), "3+": sum(v for k, v in inc.items() if k >= 3),
                                "by_k": {str(k): v for k, v in sorted(inc.items())}},
        by_region={r: dict(sorted(c.items())) for r, c in sorted(by_region.items())}, concepts=concepts,
        occasions=tuple(present))


def unit_sample(units: Sequence[set], nodes: Mapping[str, Mapping], *, n: int = 20, seed: int = 0,
                min_size: int = 2) -> list[dict]:
    """``n`` seeded units of at least ``min_size`` members, with their members' labels (the pilot's reading list for
    decision 2: twenty strict components and twenty grown units)."""
    import random
    pool = sorted((sorted(u) for u in units if len(u) >= min_size), key=lambda u: u[0])
    rng = random.Random(seed)
    pick = rng.sample(pool, min(n, len(pool)))
    return [{"size": len(u), "labels": [nodes[k].get("label") or k for k in u], "keys": u} for u in pick]


__all__ = ["UNITS", "DEFAULT_TAU", "SENSITIVITY_TAUS", "components", "grow", "build_units", "final_concept",
           "hard_negatives", "Agreement", "review_agreement", "node_mechanisms", "ConceptTable", "concept_table",
           "unit_sample", "GENERATOR_MECHANISM"]
