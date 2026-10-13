"""Repetition: how much of a generator's kept output review has, in effect, already decided (plan 13 § 6,
"Repetition"; pre-registered question 4).

Read from the all-batches review graph (R1, [review_graph.py](../review_graph.py); schema 3), whose candidate
edges carry both models' overlap readings in both directions.  An edge between two kept candidates is a
**4-edge** (``strict``: both directions read 4 on rubric A, what the review merges) or a **3-edge** (``proposed``:
both directions at the proposed cut-off 3), the levels of the review app's ``edge_level``.  A kept term is
**pre-handled** when it has a 3-edge (level 3) or a 4-edge (level 4) to a term another review batch decided
(``accepted``, ``rejected`` or ``merged_into``, the statuses the app handles from the start,
``decisions.HANDLED_ELSEWHERE``), so it costs no review-minute.  ``attached_to_batch`` is the second figure: of a
generator's undecided terms outside an M3 batch that review has started on, the share with a 3-edge into that batch
(the workstream plan's "about 40%", measured 35% for the censuses against the TDA batch): what becomes pre-handled
as that batch is decided.

A term's review status is read from the registry when rows are given (the later record), else from the node, where
R1 copied it when it built the graph.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional

KEPT_DECISIONS = ("new", "grey")
HANDLED_ELSEWHERE = ("accepted", "rejected", "merged_into")
LEVELS = (3, 4)


def load_graph(path: Path) -> dict:
    """A review graph's ``result`` block (``graph.json`` is an enveloped JSON), with ``_path`` set."""
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    g = doc.get("result", doc) if isinstance(doc, dict) else doc
    g = dict(g)
    g["_path"] = str(p)
    return g


def kept_nodes(graph: Mapping) -> dict[str, dict]:
    """The review's terms: candidate nodes M3 kept (``new`` or ``grey``), by key."""
    return {n["key"]: n for n in graph["nodes"] if n.get("kind") == "candidate" and n.get("decision") in KEPT_DECISIONS}


def edge_level(e: Mapping) -> int:
    """4 for a 4-edge, 3 for a 3-edge, else 1 (``decisions.edge_level`` without the readings it needs only below 3)."""
    if e.get("strict"):
        return 4
    if e.get("proposed"):
        return 3
    return 1


def pair_levels(graph: Mapping, keys: Optional[set] = None) -> dict[frozenset, int]:
    """``{frozenset((a, b)): level}`` over the candidate edges between kept terms (the best edge per pair)."""
    keys = keys if keys is not None else set(kept_nodes(graph))
    out: dict[frozenset, int] = {}
    for e in graph["edges"]:
        a, b = e.get("a"), e.get("b")
        if a in keys and b in keys and a != b:
            p = frozenset((a, b))
            out[p] = max(edge_level(e), out.get(p, 0))
    return out


def adjacency(graph: Mapping, level: int = 3, *, levels: Optional[Mapping[frozenset, int]] = None
              ) -> dict[str, set[str]]:
    """Kept term -> the kept terms it has an edge of ``level`` or above with."""
    if level not in LEVELS:
        raise ValueError(f"level must be 3 or 4, not {level!r}")
    levels = levels if levels is not None else pair_levels(graph)
    adj: dict[str, set[str]] = defaultdict(set)
    for p, lv in levels.items():
        if lv >= level:
            a, b = tuple(p)
            adj[a].add(b)
            adj[b].add(a)
    return adj


def review_status(node: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> Optional[str]:
    if rows is not None and node.get("key") in rows:
        return ((rows[node["key"]].get("review") or {}).get("status")) or None
    return node.get("review_status")


def review_into(node: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> Optional[str]:
    if rows is not None and node.get("key") in rows:
        return (rows[node["key"]].get("review") or {}).get("into")
    return node.get("review_into")


def decided_keys(graph: Mapping, rows: Optional[Mapping[str, Mapping]] = None) -> dict[str, str]:
    """Kept terms review has settled: ``{key: status}`` for ``accepted``, ``rejected``, ``merged_into``."""
    out = {}
    for k, n in kept_nodes(graph).items():
        st = review_status(n, rows)
        if st in HANDLED_ELSEWHERE:
            out[k] = st
    return out


def node_generators(node: Mapping) -> list[str]:
    return list(node.get("generators") or ([node["generator"]] if node.get("generator") else []))


@dataclass
class Repetition:
    generator: str
    level: int
    n_kept: int
    n_decided: int
    n_undecided: int
    pre_handled: int
    share: Optional[float]
    attached_to_batch: dict = field(default_factory=dict)
    with_another_generator: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _share(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def reviewed_batches(graph: Mapping, decided: Mapping[str, str]) -> list[str]:
    """The M3 batches review has started on (a decided term's ``m3_run``), most decided first."""
    nodes = kept_nodes(graph)
    c = Counter(nodes[k].get("m3_run") for k in decided if nodes[k].get("m3_run"))
    return [b for b, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))]


def repetition(graph: Mapping, *, level: int, rows: Optional[Mapping[str, Mapping]] = None,
               generators: Optional[Iterable[str]] = None, attach_level: int = 3,
               min_batch_decided: int = 10) -> dict[str, Repetition]:
    """Per generator (a node's ``generators``; default every one in the graph): kept terms, decided, undecided,
    pre-handled at ``level`` and its share, the attachment of its undecided terms outside each reviewed M3 batch
    (one with at least ``min_batch_decided`` decided terms) at ``attach_level``, and how many of its kept terms
    another generator also proposed."""
    nodes = kept_nodes(graph)
    levels = pair_levels(graph, set(nodes))
    adj = adjacency(graph, level, levels=levels)
    adj_att = adj if attach_level == level else adjacency(graph, attach_level, levels=levels)
    decided = decided_keys(graph, rows)
    dset = set(decided)
    batches = [b for b in reviewed_batches(graph, decided)
               if sum(1 for k in decided if nodes[k].get("m3_run") == b) >= min_batch_decided]
    batch_terms = {b: {k for k, n in nodes.items() if n.get("m3_run") == b} for b in batches}
    gens = list(generators) if generators is not None else sorted({g for n in nodes.values() for g in node_generators(n)})
    out = {}
    for g in gens:
        mine = {k for k, n in nodes.items() if g in node_generators(n)}
        und = mine - dset
        ph = sum(1 for k in und if adj.get(k, set()) & dset)
        att = {}
        for b, terms in batch_terms.items():
            outside = und - terms
            n_att = sum(1 for k in outside if adj_att.get(k, set()) & terms)
            att[b] = {"n": len(outside), "attached": n_att, "share": _share(n_att, len(outside))}
        out[g] = Repetition(generator=g, level=level, n_kept=len(mine), n_decided=len(mine & dset),
                            n_undecided=len(und), pre_handled=ph, share=_share(ph, len(und)), attached_to_batch=att,
                            with_another_generator=sum(1 for k in mine if set(node_generators(nodes[k])) - {g}))
    return out


def repetition_records(graph: Mapping, *, levels: Iterable[int] = LEVELS, rows=None) -> list[dict]:
    """``repetition.json``'s rows: one per generator and level, with the graph's batch id."""
    out = []
    for lv in levels:
        for g, r in repetition(graph, level=lv, rows=rows).items():
            out.append({"graph": graph.get("batch_id"), **r.as_dict()})
    return out


def repetition_markdown(records: Iterable[Mapping]) -> str:
    recs = list(records)
    by = defaultdict(dict)
    for r in recs:
        by[r["generator"]][r["level"]] = r
    L = ["| generator | kept | decided | undecided | pre-handled (3-edge) | pre-handled (4-edge) | attached to the "
         "first reviewed batch (3-edge) | shared with another generator |", "|---|---|---|---|---|---|---|---|"]
    for g in sorted(by, key=lambda g: -by[g].get(3, by[g].get(4))["n_kept"]):
        r3, r4 = by[g].get(3), by[g].get(4)
        r = r3 or r4
        att = next(iter(r["attached_to_batch"].values()), None) if r["attached_to_batch"] else None

        def pc(x):
            return "n/a" if x is None else f"{100 * x:.0f}%"
        L.append(f"| {g} | {r['n_kept']:,} | {r['n_decided']} | {r['n_undecided']:,} | "
                 f"{r3['pre_handled'] if r3 else 'n/a'} ({pc(r3['share']) if r3 else 'n/a'}) | "
                 f"{r4['pre_handled'] if r4 else 'n/a'} ({pc(r4['share']) if r4 else 'n/a'}) | "
                 + (f"{att['attached']} of {att['n']:,} ({pc(att['share'])})" if att else "n/a")
                 + f" | {r['with_another_generator']:,} |")
    return "\n".join(L) + "\n"


__all__ = ["load_graph", "kept_nodes", "edge_level", "pair_levels", "adjacency", "review_status", "review_into",
           "decided_keys", "node_generators", "Repetition", "reviewed_batches", "repetition", "repetition_records",
           "repetition_markdown"]
