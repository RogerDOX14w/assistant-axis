"""R1 of the trait-gap review tooling: the candidate graph and its cliques.

The brief is ``reports/trait_gap_generation/coding_plan_review.md`` (section 1, decisions 1-3, 9, 10 and 11;
section 2).  M3 (:mod:`assistant_axis.gapgen.novelty`) judges each candidate against the corpus alone, so
near-synonyms proposed together all come out ``new`` side by side.  This module builds, over the candidates a set
of M3 batches kept, a typed graph from which the review reads its groups:

* **Nodes** (:class:`Node`): the batches' kept candidates (M3 decision ``new`` or ``grey``, keyed by registry key);
  the corpus traits (``trait:<stem>``) and seed-queue entries (``queue:<stem>``) they touch; and, greyed, the
  batches' covered candidates, each pointing at the trait that covered it (decision 9: no edge, no call).
* **Candidate edges** (``source: "r1"``): each kept candidate's ``k`` nearest other kept candidates by the cosine
  of their query embeddings in M3's covered space (the ``gloss_w14`` text as M3 embedded it, projected by the
  corpus index, so the cosines are on M3's scale and the floors calibrated on M3's readings apply), at the
  retrieval floor or above.  Typed by the relation call (rubric ``relation.md``, the relation model, one list per
  candidate as in M3, the other candidates' glosses as descriptions; ``unsure`` asked again of Sonnet as M3 does).
  Then, for an edge answered ``similar`` from either side (or ``unsure``, or ``similar`` from one side and
  ``opposed`` from the other) at the overlap floor or above (decision 11), the overlap call: rubric A, one pair per
  call, Sonnet then Opus under M3's rule at cut-off 4, through :meth:`NoveltyRunner.run_pairs` unchanged, the
  other candidate standing in the "other trait" slot (:class:`ReviewRunner` puts the kept candidates into the
  runner's corpus map under their keys).
* **The two directions.**  An edge is read first with the candidate whose key sorts first as the target; the
  other direction is read only when the first is a 4, because only an edge read 4 both ways is a 4-edge
  (decision 2).  This finds exactly the 4-edges that reading both directions of every edge would find, at about
  half the overlap calls; an edge that is not a 4-edge keeps one direction's reading.
* **Corpus edges** (``source: "m3"``): copied from each kept candidate's M3 block, ``novelty.listed`` (cosine,
  relation, rank, via) and ``novelty.readings`` (the overlap readings, Sonnet and Opus); no call.
* **4-edges** (``strict``): both directions read 4 under the rule at cut-off 4 (:func:`reading_of`: Sonnet 4
  confirmed by Opus, Sonnet 3 raised to 4 by Opus, or Sonnet unsure and Opus 4), the relation not ``opposed``.
* **Cliques**: the maximal cliques of the 4-edges (:func:`maximal_cliques`, Bron-Kerbosch with a pivot), so a
  chain can never be a group; two cliques may overlap; a kept candidate in none is a singleton.
  ``clique_links``: the pairs of cliques joined by an opposed edge (decision 3: opposed is an edge label, never
  merged across).

Cost: :func:`estimate_build` before any call (the relation calls as rendered, the overlap calls by the shares M3
measured per cosine bin, :func:`measured_shares`); the CLI checks it against the cap, and again after the
relation calls on the pairs actually marked for the overlap call (``gate``).

The CLI is ``data_analysis/gap_generation/review_graph.py``; outputs under ``data/candidates/review/<batch_id>/``.
"""
from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.judge_pricing import BATCH_SUFFIX

from . import novelty as NV
from . import novelty_runner as NR
from . import overlap_test as OT
from . import paths
from .cost import Estimate

#: The cut-off of every candidate pair (decision 2): rubric A's 4, "the same concept".
CUT_OFF = 4
#: M3's rule set 2: a Sonnet 3 that Opus raises to 4 counts (decision 12 of the M3 section), as near alignment.
RULES = NV.RULES[2]
DEFAULT_K = 10
#: The retrieval floor among candidates: M3's (rule set 2).
DEFAULT_COSINE_FLOOR = NV.DEFAULT_COSINE_FLOOR
#: Decision 11: no overlap call on a candidate pair below this cosine.
DEFAULT_OVERLAP_FLOOR = 0.35
GRAPH_SCHEMA = 1
#: The M3 decisions a candidate is reviewed under (``grey`` is kept with a flag).
KEPT_DECISIONS = ("new", "grey")
NODE_KINDS = ("candidate", "corpus", "queue")
#: A candidate edge's relation, from its one or two answers (:func:`combine_relations`).
EDGE_RELATIONS = ("similar", "opposed", "unrelated", "unsure", "mixed", "unknown")
#: The relations that send a pair at the overlap floor or above to the overlap call.
OVERLAP_RELATIONS = ("similar", "unsure", "mixed")
#: ``Edge.overlap`` of a candidate edge: read both ways, read one way (the first was not a 4), similar but below
#: the overlap floor, not similar, or left without an answer (a resume finishes it).
OVERLAP_STATES = ("both", "first", "below_floor", "not_similar", "stalled")
FIRST_WAVE, SECOND_WAVE = "ov1", "ov2"
#: The estimate's cosine bins (lower edges) and the observations a bin needs before its measured share is used.
SHARE_BINS = (0.35, 0.45, 0.55, 0.65)
MIN_SHARE_OBS = 10
#: The share of second-direction Sonnet readings assumed to go on to Opus (a first-direction 4 is the same
#: concept, so the second Sonnet reading is nearly always at the cut-off or one below).
SECOND_OPUS_SHARE = 1.0


def corpus_key(stem: str) -> str:
    return f"trait:{stem}"


def queue_key(stem: str) -> str:
    return f"queue:{stem}"


def review_dir(batch_id: str, *, candidates_dir: Optional[Path] = None) -> Path:
    """``data/candidates/review/<batch_id>/`` (not created here)."""
    return (candidates_dir or paths.DATA_CANDIDATES) / "review" / paths.check_id(batch_id, "batch_id")


class OverlapGateRefused(RuntimeError):
    """Raised by a ``gate`` (:func:`build_graph`) to stop before the overlap calls; the relation answers are on
    record, so a resume with a larger budget sends none of them again."""


# --------------------------------------------------------------------------- nodes, edges, the graph

_ALWAYS = {"key", "kind", "label", "gloss", "a", "b", "cosine", "relation", "source", "strict"}


def _compact(d: dict) -> dict:
    """``d`` without its empty optional fields (``None``, ``[]``, ``{}``, ``False``)."""
    return {k: v for k, v in d.items() if k in _ALWAYS or not (v is None or v is False or v == [] or v == {})}


def _from(cls, d: Mapping):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in d.items() if k in names})


@dataclass
class Node:
    key: str
    kind: str                                   # candidate | corpus | queue
    label: str
    gloss: Optional[str] = None                 # a candidate's gloss; a corpus or queue trait's description
    stem: Optional[str] = None
    generator: Optional[str] = None             # the first generator that proposed it
    generators: list = field(default_factory=list)
    verdict: Optional[str] = None               # M1's filter verdict
    decision: Optional[str] = None              # M3's: new | grey (kept), covered (shown greyed)
    covered_by: Optional[str] = None            # a covered candidate: the node key of the trait that covered it
    covered_reading: Optional[dict] = None      # ... and M3's deciding reading (cosine, Sonnet, Opus)
    flags: list = field(default_factory=list)   # M3's review flags
    region: Optional[str] = None
    alignment_score: Optional[int] = None
    m3_run: Optional[str] = None                # the M3 batch that decided it
    status: Optional[str] = None                # a queue entry's status
    missing: bool = False                       # a corpus stem M3 read that the current corpus no longer has

    def to_dict(self) -> dict:
        return _compact({f.name: getattr(self, f.name) for f in fields(self)})

    @classmethod
    def from_dict(cls, d: Mapping) -> "Node":
        return _from(cls, d)


@dataclass
class Edge:
    a: str
    b: str
    cosine: Optional[float]
    relation: Optional[str]
    source: str                                  # r1 (a candidate pair, judged here) | m3 (copied from the block)
    strict: bool = False                         # a 4-edge
    relations: dict = field(default_factory=dict)   # r1: {"ab": a's answer about b, "ba": b's about a}
    readings: dict = field(default_factory=dict)    # {"ab": a as the target, "ba": b as the target}: reading_of()
    overlap: Optional[str] = None                # r1: OVERLAP_STATES
    via: Optional[str] = None                    # m3: retrieved | expanded | partner | renamed_from
    rank: Optional[int] = None                   # m3: the corpus trait's rank among the k retrieved

    def to_dict(self) -> dict:
        return _compact({f.name: getattr(self, f.name) for f in fields(self)})

    @classmethod
    def from_dict(cls, d: Mapping) -> "Edge":
        return _from(cls, d)


@dataclass
class Graph:
    batch_id: str
    from_batches: list
    config: dict
    nodes: list
    edges: list
    cliques: list
    clique_links: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    complete: bool = True
    stalled: dict = field(default_factory=dict)   # what a resume still has to answer
    schema: int = GRAPH_SCHEMA

    def node_map(self) -> dict[str, Node]:
        return {n.key: n for n in self.nodes}

    def candidate_keys(self) -> list[str]:
        """The kept candidates (the review's terms), by key."""
        return [n.key for n in self.nodes if n.kind == "candidate" and n.decision in KEPT_DECISIONS]

    def strict_edges(self) -> list[tuple[str, str]]:
        return [(e.a, e.b) for e in self.edges if e.strict]

    def singletons(self) -> list[str]:
        inside = {m for c in self.cliques for m in c}
        return [k for k in self.candidate_keys() if k not in inside]

    def to_json(self) -> dict:
        return {"schema": self.schema, "batch_id": self.batch_id, "from_batches": list(self.from_batches),
                "config": dict(self.config), "complete": self.complete, "stalled": dict(self.stalled),
                "nodes": [n.to_dict() for n in self.nodes], "edges": [e.to_dict() for e in self.edges],
                "cliques": [list(c) for c in self.cliques], "singletons": self.singletons(),
                "clique_links": [dict(x) for x in self.clique_links], "stats": dict(self.stats),
                "usage": dict(self.usage)}

    @classmethod
    def from_json(cls, d: Mapping) -> "Graph":
        """From :meth:`to_json`'s payload or the ``{"result", "_provenance"}`` envelope ``graph.json`` holds."""
        if "result" in d and "_provenance" in d:
            d = d["result"]
        return cls(batch_id=d["batch_id"], from_batches=list(d["from_batches"]), config=dict(d.get("config") or {}),
                   nodes=[Node.from_dict(x) for x in d["nodes"]], edges=[Edge.from_dict(x) for x in d["edges"]],
                   cliques=[list(c) for c in d["cliques"]], clique_links=[dict(x) for x in d.get("clique_links") or []],
                   stats=dict(d.get("stats") or {}), usage=dict(d.get("usage") or {}),
                   complete=bool(d.get("complete", True)), stalled=dict(d.get("stalled") or {}),
                   schema=int(d.get("schema", GRAPH_SCHEMA)))


def graph_envelope(graph: Graph, *, inputs=None, title: Optional[str] = None) -> dict:
    """``graph.json``'s content: the payload in the provenance envelope (``json_metadata``)."""
    from assistant_axis.plot_metadata import json_metadata
    return json_metadata(graph.to_json(), title=title or f"review_graph build {graph.batch_id}", inputs=inputs)


# --------------------------------------------------------------------------- cliques

def maximal_cliques(strict_edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    """The maximal cliques of the graph the edges make (Bron-Kerbosch with a pivot), each sorted, the list by
    size (largest first) then members; a clique has at least two members (a node with no edge is in none)."""
    adj: dict[str, set] = defaultdict(set)
    for a, b in strict_edges:
        if a != b:
            adj[a].add(b)
            adj[b].add(a)
    out: list[list[str]] = []

    def expand(r: set, p: set, x: set) -> None:
        if not p and not x:
            if len(r) >= 2:
                out.append(sorted(r))
            return
        pivot = max(sorted(p | x), key=lambda v: len(adj[v] & p))
        for v in sorted(p - adj[pivot]):
            expand(r | {v}, p & adj[v], x & adj[v])
            p = p - {v}
            x = x | {v}

    expand(set(), set(adj), set())
    return sorted(out, key=lambda c: (-len(c), c))


def clique_links(cliques: Sequence[Sequence[str]], edges: Iterable[Edge], *, relation: str = "opposed") -> list[dict]:
    """The pairs of cliques (indices into ``cliques``) joined by a candidate edge of ``relation``, with those edges:
    ``[{"cliques": [i, j], "relation", "edges": [[a, b], ...]}]``.  An edge with an end in both cliques is no link."""
    member_of: dict[str, set] = defaultdict(set)
    for i, c in enumerate(cliques):
        for m in c:
            member_of[m].add(i)
    links: dict[tuple, list] = defaultdict(list)
    for e in edges:
        if e.source != "r1" or e.relation != relation:
            continue
        for i in member_of.get(e.a, ()):
            for j in member_of.get(e.b, ()):
                if i == j or e.a in cliques[j] or e.b in cliques[i]:
                    continue
                links[(min(i, j), max(i, j))].append([e.a, e.b])
    return [{"cliques": [i, j], "relation": relation, "edges": sorted(v)} for (i, j), v in sorted(links.items())]


# --------------------------------------------------------------------------- readings and relations

def reading_of(r: Mapping) -> dict:
    """One direction's overlap reading (a :meth:`NoveltyRunner.read_pairs` result, or an M3 reading of the same
    shape) under the rule at cut-off 4: ``{"sonnet", "opus", "verdict", "four", "reasons"?, "errors"?}``;
    ``{"stalled": why}`` for a pair left without an answer."""
    if "stalled" in r:
        return {"stalled": r["stalled"]}
    s = r.get("sonnet") or {}
    o = r.get("opus") or None
    sv = s.get("value")
    ov = o.get("value") if o else None
    pv = NV.pair_verdict(sv, ov, CUT_OFF)
    out = {"sonnet": sv, "opus": ov, "verdict": pv["verdict"], "four": NV.verdict_cuts(pv["verdict"], RULES)}
    reasons = {m: x["reason"] for m, x in (("sonnet", s), ("opus", o or {})) if x.get("reason")}
    errors = {m: x["error"] for m, x in (("sonnet", s), ("opus", o or {})) if x.get("error")}
    if reasons:
        out["reasons"] = reasons
    if errors:
        out["errors"] = errors
    return out


def is_four(r: Optional[Mapping]) -> bool:
    return bool(r) and "stalled" not in r and reading_of(r)["four"]


def combine_relations(ab: Optional[str], ba: Optional[str]) -> str:
    """A candidate edge's relation from its two answers (either may be missing; ``unparsed`` counts as
    ``unsure``, as M3 sends every listed trait of a relation call that never parsed to the overlap call):
    ``mixed`` when one side says similar and the other opposed; else opposed, similar, unsure, unrelated in that
    order of precedence; ``unknown`` with no answer."""
    vals = {"unsure" if v == "unparsed" else v for v in (ab, ba) if v}
    if not vals:
        return "unknown"
    if "opposed" in vals and "similar" in vals:
        return "mixed"
    for v in ("opposed", "similar", "unsure"):
        if v in vals:
            return v
    return "unrelated"


def _answer(rec: Optional[Mapping], other: str) -> Optional[str]:
    """One relation call's final answer about ``other`` (Sonnet's where it re-asked an ``unsure``)."""
    if rec is None:
        return None
    if rec.get("status") == "unparsed":
        return "unparsed"
    if rec.get("status") != "ok":
        return None
    a = (rec.get("answers") or {}).get(other)
    if a is None:
        return None
    return (a.get("second") or {}).get("relation") or a.get("relation")


def edge_answers(relations: Mapping[str, Mapping], a: str, b: str) -> tuple[Optional[str], Optional[str]]:
    return _answer(relations.get(a), b), _answer(relations.get(b), a)


# --------------------------------------------------------------------------- the candidates and the plan

class PairCandidate(NR.M3Candidate):
    """A kept candidate as the overlap call reads it here: cut-off 4 whatever its alignment score (decision 2)."""

    @property
    def cut_off(self) -> int:
        return CUT_OFF


def _gloss(row: Mapping) -> Optional[str]:
    g = row.get("gloss") or (row.get("filter") or {}).get("gloss")
    return g.strip() if isinstance(g, str) and g.strip() else None


def pair_candidate(row: Mapping) -> tuple[Optional[PairCandidate], Optional[str]]:
    """``(candidate, None)``, or ``(None, why)`` for a row M3 could not have judged (``candidate_from_row``)."""
    row = dict(row)
    if not row.get("gloss") and _gloss(row):
        row["gloss"] = _gloss(row)
    c, why = NR.candidate_from_row(row)
    if c is None:
        return None, why
    return PairCandidate(**{f.name: getattr(c, f.name) for f in fields(c)}), None


@dataclass
class GraphPlan:
    batch_ids: list
    cands: dict          # key -> PairCandidate (the kept)
    rows: dict           # key -> registry row (the kept)
    covered: dict        # key -> registry row (the covered, shown greyed)
    neighbours: dict     # key -> [(other key, cosine)], nearest first
    edges: dict          # (a, b) with a < b -> cosine
    skipped: dict
    no_vector: list
    by_batch: dict

    def relation_items(self) -> list[tuple[str, list[str]]]:
        """``(key, [other keys])`` of every kept candidate with a neighbour, by key: one relation call each."""
        return [(k, [o for o, _ in self.neighbours[k]]) for k in sorted(self.neighbours) if self.neighbours[k]]


def select_rows(rows: Mapping[str, Mapping], batch_ids: Sequence[str]) -> tuple[dict, dict, dict, dict]:
    """``(kept, covered, skipped, by_batch)``: the rows whose ``novelty.run_id`` is one of ``batch_ids``, kept
    (decision new or grey) or covered.  A row two batches decided carries the later block only, so it is selected
    by that batch."""
    bset = set(batch_ids)
    kept, covered, skipped = {}, {}, Counter()
    by_batch: dict[str, Counter] = {b: Counter() for b in batch_ids}
    for k, r in sorted(rows.items()):
        nv = r.get("novelty") or {}
        if nv.get("run_id") not in bset:
            continue
        d = nv.get("decision")
        by_batch[nv["run_id"]][d] += 1
        if d in KEPT_DECISIONS:
            kept[k] = r
        elif d == "covered":
            covered[k] = r
        else:
            skipped[f"decision_{d}"] += 1
    return kept, covered, dict(skipped), {b: dict(c) for b, c in by_batch.items()}


def nearest_candidates(vectors: Mapping[str, np.ndarray], *, k: int = DEFAULT_K,
                       floor: float = DEFAULT_COSINE_FLOOR) -> dict[str, list[tuple[str, float]]]:
    """Each key's ``k`` nearest other keys by cosine (nearest first, ties by key), those under ``floor`` dropped."""
    keys = sorted(vectors)
    out: dict[str, list] = {key: [] for key in keys}
    if len(keys) < 2:
        return out
    Q = np.stack([np.asarray(vectors[x], dtype=np.float64) for x in keys])
    Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)
    S = Q @ Q.T
    idx = np.arange(len(keys))
    for i, a in enumerate(keys):
        s = S[i].copy()
        s[i] = -np.inf
        for j in np.lexsort((idx, -s))[:k]:
            c = float(s[j])
            if c < floor:
                break
            out[a].append((keys[j], round(c, 6)))
    return out


def plan_graph(rows: Mapping[str, Mapping], batch_ids: Sequence[str], vectors: Mapping[str, np.ndarray], *,
               k: int = DEFAULT_K, cosine_floor: float = DEFAULT_COSINE_FLOOR) -> GraphPlan:
    """The batches' kept and covered rows, and the candidate edges: each kept candidate's ``k`` nearest other kept
    candidates by ``vectors`` (projected query vectors, by key) at ``cosine_floor`` or above."""
    kept, covered, skipped, by_batch = select_rows(rows, batch_ids)
    cands, rows_kept = {}, {}
    skipped = Counter(skipped)
    for key_, r in kept.items():
        c, why = pair_candidate(r)
        if c is None:
            skipped[why] += 1
            continue
        cands[key_], rows_kept[key_] = c, r
    no_vector = sorted(x for x in cands if x not in vectors)
    nbrs = nearest_candidates({x: vectors[x] for x in cands if x in vectors}, k=k, floor=cosine_floor)
    for x in no_vector:
        nbrs[x] = []
    edges: dict[tuple[str, str], float] = {}
    for a, lst in nbrs.items():
        for b, c in lst:
            edges[tuple(sorted((a, b)))] = c
    return GraphPlan(batch_ids=list(batch_ids), cands=cands, rows=rows_kept, covered=covered,
                     neighbours={x: nbrs[x] for x in sorted(nbrs)}, edges=dict(sorted(edges.items())),
                     skipped=dict(skipped), no_vector=no_vector, by_batch=by_batch)


def overlap_pairs(plan: GraphPlan, relations: Mapping[str, Mapping], *,
                  overlap_floor: float = DEFAULT_OVERLAP_FLOOR) -> list[tuple[str, str, float]]:
    """The candidate edges the overlap call reads: ``(a, b, cosine)`` with ``a`` the first target (the key that
    sorts first), relation in :data:`OVERLAP_RELATIONS`, cosine at ``overlap_floor`` or above."""
    out = []
    for (a, b), c in plan.edges.items():
        if c >= overlap_floor and combine_relations(*edge_answers(relations, a, b)) in OVERLAP_RELATIONS:
            out.append((a, b, c))
    return out


# --------------------------------------------------------------------------- the runner

class ReviewRunner(NR.NoveltyRunner):
    """A :class:`NoveltyRunner` whose corpus map also holds the kept candidates, under their keys with their glosses
    as descriptions: a relation call can list candidates, and :meth:`run_pairs` reads a candidate against another
    unchanged (the other candidate in the "other trait" slot).  Records, resume, retries, the budget stop and the
    transports are the runner's own."""

    def add_candidates(self, cands: Iterable[PairCandidate]) -> None:
        for c in cands:
            self.corpus[c.key] = {"label": c.label, "description": c.gloss}
            self.states.setdefault(c.key, NR.CandState(cand=c))

    def _relation_call(self, st: NR.CandState, stems: Sequence[str], *, step: str = "relation") -> NR.Call:
        # the parent's call, with the listed names looked up in the corpus map (corpus traits and candidates)
        traits = [(self.corpus[s]["label"], self.corpus[s]["description"]) for s in stems]
        user = NV.render_relation_user(st.cand.label, st.cand.gloss, traits)
        model = self.relation_model if step == "relation" else NR.UNSURE_MODEL
        return NR.Call(step=step, role=NR.model_role(model), key=st.cand.key, model=model,
                       system=self.rubrics["relation"]["text"], user=user, max_tokens=NR.RELATION_MAX_TOKENS,
                       temperature=NR.TEMPERATURE, cache_system=False, stems=tuple(stems))

    def relation_calls(self, items: Sequence[tuple[str, Sequence[str]]]) -> list[NR.Call]:
        """One relation call per ``(key, others)``, the others in the order seeded by the run and the key."""
        return [self._relation_call(self.states[k], NV.relation_order(others, self.relation_seed, k))
                for k, others in items]

    def overlap_call(self, key: str, other: str, role: str = "sonnet", position: int = 1) -> NR.Call:
        return self._overlap_call(self.states[key], other, role, position)

    def on_record(self, call: NR.Call) -> bool:
        """Whether an answer to ``call`` is on record (a resume replays it instead of sending it)."""
        return call.cache_key() in self.cache_good

    def run_relations(self, items: Sequence[tuple[str, Sequence[str]]]) -> dict[str, dict]:
        """The relation calls of ``items`` (wave ``r1_relation``), then Sonnet on the ``unsure`` answers
        (``r2_relation_unsure``), as M3 sends them.  ``{key: {"status", "model", "order", "answers": {other:
        {"relation", "reason", "second"?}}, "error"?, "unsure_reasked"?}}``.  A stop is raised after every answer
        received is recorded."""
        return asyncio.run(self._run_relations(items))

    async def _run_relations(self, items) -> dict[str, dict]:
        self._stop = None
        calls = self.relation_calls(items)
        res = await self._wave("r1_relation", calls)
        out: dict[str, dict] = {}
        unsure_calls = []
        for c in calls:
            o = res[id(c)]
            rec = {"status": o.status, "model": c.model, "order": list(c.stems), "answers": {}}
            if o.status == "ok":
                for i, s in enumerate(c.stems, 1):
                    row = o.parsed[i]
                    rec["answers"][s] = {"relation": row["value"], "reason": row["reason"]}
                unsure = [s for s in c.stems if rec["answers"][s]["relation"] == "unsure"]
                if unsure:
                    unsure_calls.append(self._relation_call(self.states[c.key], unsure, step="relation_unsure"))
            elif o.error:
                rec["error"] = o.error
            out[c.key] = rec
        if unsure_calls and self._stop is None:
            res2 = await self._wave("r2_relation_unsure", unsure_calls)
            for c in unsure_calls:
                o, rec = res2[id(c)], out[c.key]
                rec["unsure_reasked"] = {"model": c.model, "stems": list(c.stems), "status": o.status}
                if o.status == "ok":
                    for i, s in enumerate(c.stems, 1):
                        row = o.parsed[i]
                        rec["answers"][s]["second"] = {"relation": row["value"], "reason": row["reason"]}
        if self._stop is not None:
            raise self._stop
        return out


# --------------------------------------------------------------------------- the build

def build_graph(plan: GraphPlan, *, runner: ReviewRunner, corpus: Mapping[str, Any], queue: Optional[Mapping] = None,
                overlap_floor: float = DEFAULT_OVERLAP_FLOOR, config: Optional[Mapping] = None,
                batch_id: Optional[str] = None,
                gate: Optional[Callable[[list[tuple[str, str, float]]], None]] = None) -> Graph:
    """The relation calls, the overlap calls (first direction, then the second where the first read 4), and the
    graph (:func:`assemble_graph`).  ``corpus``: stem -> :class:`novelty.CorpusTrait` (labels and descriptions of
    the corpus nodes); ``queue``: the seed queue (``{"entries": [...]}``); ``gate(pairs)``: called with the pairs
    marked for the overlap call before any is sent (the CLI's second cost check; it raises to stop).  A stop
    (budget, gate) is raised after every answer received is recorded in ``runner.responses_path``."""
    runner.add_candidates(plan.cands.values())
    items = plan.relation_items()
    relations = runner.run_relations(items) if items else {}
    pairs = overlap_pairs(plan, relations, overlap_floor=overlap_floor)
    if gate is not None:
        gate(pairs)
    first: dict = {}
    if pairs:
        targets = [plan.cands[a] for a in dict.fromkeys(a for a, _, _ in pairs)]
        first = runner.run_pairs(targets, [(a, b, 1) for a, b, _ in pairs], wave=FIRST_WAVE)
    back = [(b, a, 2) for a, b, _ in pairs if is_four(first.get((a, b)))]
    second: dict = {}
    if back:
        targets = [plan.cands[b] for b in dict.fromkeys(b for b, _, _ in back)]
        second = runner.run_pairs(targets, back, wave=SECOND_WAVE)
    return assemble_graph(plan, relations=relations, first=first, second=second, overlap_floor=overlap_floor,
                          corpus=corpus, queue=queue, config=config, batch_id=batch_id or runner.batch_id,
                          usage=runner.usage.as_dict())


def _candidate_node(row: Mapping) -> Node:
    nv, f = row.get("novelty") or {}, row.get("filter") or {}
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    a = nv.get("alignment_score", f.get("alignment"))
    return Node(key=row["key"], kind="candidate", label=row.get("label") or row["key"], gloss=_gloss(row),
                stem=row.get("stem"), generator=gens[0] if gens else None, generators=gens, verdict=f.get("verdict"),
                decision=nv.get("decision"), flags=list(nv.get("review") or []),
                region=f.get("region") or nv.get("region"),
                alignment_score=a if isinstance(a, int) and not isinstance(a, bool) else None, m3_run=nv.get("run_id"))


def _covering(nv: Mapping) -> Optional[tuple[str, str]]:
    """``(kind, stem)`` of the trait that covered a candidate: the queue entry for an exact-label queue match,
    else the corpus trait."""
    stem = nv.get("covered_by")
    if not stem:
        return None
    return ("queue", stem) if (nv.get("exact_label") or {}).get("match") == "queue" else ("corpus", stem)


def _value(x: Any) -> Any:
    return x.get("value") if isinstance(x, Mapping) else None


def assemble_graph(plan: GraphPlan, *, relations: Mapping[str, Mapping], first: Mapping, second: Mapping,
                   corpus: Mapping[str, Any], queue: Optional[Mapping] = None,
                   overlap_floor: float = DEFAULT_OVERLAP_FLOOR, config: Optional[Mapping] = None,
                   batch_id: str = "", usage: Optional[Mapping] = None) -> Graph:
    """The :class:`Graph` from the plan and the answers (no call): nodes, the candidate edges with their relations
    and readings, the corpus edges copied from the M3 blocks, the 4-edges, the cliques and their opposed links."""
    corpus_stems: set[str] = set()
    queue_stems: set[str] = set()
    nodes = [_candidate_node(plan.rows[k]) for k in sorted(plan.rows)]
    for k in sorted(plan.covered):
        n = _candidate_node(plan.covered[k])
        nv = plan.covered[k].get("novelty") or {}
        cov = _covering(nv)
        if cov:
            (queue_stems if cov[0] == "queue" else corpus_stems).add(cov[1])
            n.covered_by = (queue_key if cov[0] == "queue" else corpus_key)(cov[1])
        d = nv.get("deciding_reading")
        if d:
            n.covered_reading = {"stem": d.get("stem"), "cosine": d.get("cosine"), "sonnet": _value(d.get("sonnet")),
                                 "opus": _value(d.get("opus"))}
        nodes.append(n)

    edges: list[Edge] = []
    stalled: dict[str, list] = {"relation": [], "overlap": []}
    for k, rec in sorted(relations.items()):
        if rec.get("status") in ("failed", "not_sent") or \
                (rec.get("unsure_reasked") or {}).get("status") in ("failed", "not_sent"):
            stalled["relation"].append(k)
    for (a, b), cos in plan.edges.items():
        ra, rb = edge_answers(relations, a, b)
        rel = combine_relations(ra, rb)
        f, s = first.get((a, b)), second.get((b, a))
        readings = {}
        if f is not None:
            readings["ab"] = reading_of(f)
        if s is not None:
            readings["ba"] = reading_of(s)
        if rel not in OVERLAP_RELATIONS:
            state = "not_similar"
        elif cos < overlap_floor:
            state = "below_floor"
        elif f is None or "stalled" in f or (readings["ab"]["four"] and (s is None or "stalled" in s)):
            state = "stalled"
        elif readings["ab"]["four"]:
            state = "both"
        else:
            state = "first"
        if state == "stalled":
            stalled["overlap"].append([a, b])
        strict = state == "both" and readings["ab"]["four"] and readings["ba"]["four"] and rel != "opposed"
        edges.append(Edge(a=a, b=b, cosine=cos, relation=rel, source="r1", strict=bool(strict),
                          relations={d: v for d, v in (("ab", ra), ("ba", rb)) if v is not None},
                          readings=readings, overlap=state))

    for key_ in sorted(plan.rows):
        nv = plan.rows[key_].get("novelty") or {}
        judged = {r["stem"]: r for r in nv.get("readings") or [] if r.get("stem")}
        seen = set()
        for x in nv.get("listed") or []:
            stem = x["stem"]
            seen.add(stem)
            corpus_stems.add(stem)
            rd = {"ab": reading_of(judged[stem]) | {"outcome": judged[stem].get("outcome")}} if stem in judged else {}
            edges.append(Edge(a=key_, b=corpus_key(stem), cosine=x.get("cosine"), relation=x.get("relation") or "unknown",
                              source="m3", readings=rd, via=x.get("via"), rank=x.get("rank")))
        for stem, r in judged.items():          # judged but not listed: an opposite's partner, a renamed_from match
            if stem in seen:
                continue
            corpus_stems.add(stem)
            edges.append(Edge(a=key_, b=corpus_key(stem), cosine=r.get("cosine"), relation=r.get("relation") or "unknown",
                              source="m3", readings={"ab": reading_of(r) | {"outcome": r.get("outcome")}},
                              via=r.get("via")))

    for stem in sorted(corpus_stems):
        t = corpus.get(stem)
        nodes.append(Node(key=corpus_key(stem), kind="corpus", label=t.label, gloss=t.description, stem=stem)
                     if t is not None else
                     Node(key=corpus_key(stem), kind="corpus", label=stem.replace("_", " "), stem=stem, missing=True))
    q_by = {}
    for e in (queue or {}).get("entries") or []:
        if e.get("stem"):
            q_by.setdefault(e["stem"], e)
    for stem in sorted(queue_stems):
        e = q_by.get(stem) or {}
        nodes.append(Node(key=queue_key(stem), kind="queue", label=e.get("label") or stem.replace("_", " "),
                          gloss=e.get("description") or e.get("description_draft"), stem=stem, status=e.get("status"),
                          missing=not e))

    cliques = maximal_cliques((e.a, e.b) for e in edges if e.strict)
    g = Graph(batch_id=batch_id, from_batches=list(plan.batch_ids), config=dict(config or {}), nodes=nodes,
              edges=edges, cliques=cliques, clique_links=clique_links(cliques, edges), usage=dict(usage or {}),
              complete=not (stalled["relation"] or stalled["overlap"]),
              stalled={k: v for k, v in stalled.items() if v})
    g.stats = summarize(g, plan=plan)
    return g


def _dist(c: Counter) -> dict:
    return {str(k): c[k] for k in sorted(c, key=lambda x: (str(type(x)), x))}


def summarize(g: Graph, *, plan: Optional[GraphPlan] = None) -> dict:
    """The counts the readout quotes: candidates, nodes, edges by relation and overlap state, the overlap pairs
    read, 4-edges, Sonnet and Opus on the 4s, cliques by size, singletons, opposed links."""
    nodes = g.node_map()
    kept = g.candidate_keys()
    r1 = [e for e in g.edges if e.source == "r1"]
    m3 = [e for e in g.edges if e.source == "m3"]
    reads = [rd for e in r1 for rd in e.readings.values() if "stalled" not in rd]
    in_cliques = Counter(m for c in g.cliques for m in c)
    agree = Counter(f"sonnet {rd['sonnet']}, opus {rd['opus']}" for rd in reads if rd.get("sonnet") in (3, 4, "unsure"))
    out = {
        "n_candidates": len(kept),
        "by_batch": _dist(Counter(nodes[k].m3_run for k in kept)),
        "by_generator": _dist(Counter(nodes[k].generator for k in kept)),
        "by_decision": _dist(Counter(nodes[k].decision for k in kept)),
        "n_covered_shown": sum(1 for n in g.nodes if n.kind == "candidate" and n.decision == "covered"),
        "n_corpus_nodes": sum(1 for n in g.nodes if n.kind == "corpus"),
        "n_queue_nodes": sum(1 for n in g.nodes if n.kind == "queue"),
        "candidate_edges": {
            "n": len(r1), "by_relation": _dist(Counter(e.relation for e in r1)),
            "by_overlap": _dist(Counter(e.overlap for e in r1)),
            "answers": _dist(Counter(v for e in r1 for v in e.relations.values())),
            "one_sided": sum(1 for e in r1 if len(e.relations) == 1)},
        "overlap": {
            "pairs_first_direction": sum(1 for e in r1 if "ab" in e.readings),
            "pairs_second_direction": sum(1 for e in r1 if "ba" in e.readings),
            "sonnet_readings": len(reads), "opus_readings": sum(1 for rd in reads if rd.get("opus") is not None),
            "four_first": sum(1 for e in r1 if (e.readings.get("ab") or {}).get("four")),
            "four_edges": sum(1 for e in r1 if e.strict),
            "similar_below_floor": sum(1 for e in r1 if e.overlap == "below_floor"),
            "unparsed": sum(1 for rd in reads if rd.get("verdict") == "unparsed"),
            "stalled": sum(1 for e in r1 if e.overlap == "stalled")},
        "agreement_on_fours": {"directions_read_4": sum(1 for rd in reads if rd.get("four")),
                               "by_readings": _dist(agree)},
        "corpus_edges": {"n": len(m3), "by_relation": _dist(Counter(e.relation for e in m3)),
                         "with_readings": sum(1 for e in m3 if e.readings)},
        "cliques": {"n": len(g.cliques), "by_size": _dist(Counter(len(c) for c in g.cliques)),
                    "largest": max((len(c) for c in g.cliques), default=0),
                    "candidates_in_cliques": len(in_cliques),
                    "candidates_in_several": sum(1 for v in in_cliques.values() if v > 1)},
        "singletons": len(g.singletons()),
        "clique_links": len(g.clique_links),
    }
    if plan is not None:
        out["skipped"] = dict(plan.skipped)
        out["no_vector"] = list(plan.no_vector)
        out["selected_by_batch"] = plan.by_batch
    return out


# --------------------------------------------------------------------------- the estimate

@dataclass
class Shares:
    """Per cosine bin (lower edges ``bins``): the share of pairs the relation call sends to the overlap call
    (``similar`` or ``unsure``), the share whose Sonnet reading sends the pair to Opus at cut-off 4 (3, 4 or
    unsure), and the share whose final reading is 4; ``n_listed`` and ``n_read``: the observations behind them."""
    bins: tuple
    similar: tuple
    opus: tuple
    four: tuple
    n_listed: tuple
    n_read: tuple

    def at(self, cosine: float) -> tuple[float, float, float]:
        i = max([j for j, lo in enumerate(self.bins) if cosine >= lo] or [0])
        return self.similar[i], self.opus[i], self.four[i]

    def all_similar(self) -> "Shares":
        """The same shares with every pair sent to the overlap call (the pairs are known to be similar)."""
        return Shares(self.bins, tuple(1.0 for _ in self.bins), self.opus, self.four, self.n_listed, self.n_read)

    def as_dict(self) -> dict:
        return {"bins": list(self.bins), "similar": [round(x, 4) for x in self.similar],
                "opus": [round(x, 4) for x in self.opus], "four": [round(x, 4) for x in self.four],
                "n_listed": list(self.n_listed), "n_read": list(self.n_read)}


def measured_shares(rows: Mapping[str, Mapping], batch_ids: Sequence[str], *, bins: Sequence[float] = SHARE_BINS,
                    min_obs: int = MIN_SHARE_OBS) -> Shares:
    """:class:`Shares` from the M3 blocks of the batches' rows (every decision): the listed traits' final relations
    and the overlap readings, by cosine.  A bin with fewer than ``min_obs`` observations takes 1.0, so that the
    estimate errs high."""
    bins = tuple(bins)
    nl, ns, nr, no, nf = ([0] * len(bins) for _ in range(5))

    def b(c) -> Optional[int]:
        if c is None or c < bins[0]:
            return None
        return max(j for j, lo in enumerate(bins) if c >= lo)

    bset = set(batch_ids)
    for r in rows.values():
        nv = r.get("novelty") or {}
        if nv.get("run_id") not in bset:
            continue
        for x in nv.get("listed") or []:
            i = b(x.get("cosine"))
            if i is not None:
                nl[i] += 1
                ns[i] += x.get("relation") in ("similar", "unsure")
        for rd in nv.get("readings") or []:
            i = b(rd.get("cosine"))
            sv = _value(rd.get("sonnet"))
            if i is None or rd.get("sonnet") is None:
                continue
            ov = _value(rd.get("opus"))
            nr[i] += 1
            no[i] += sv in (3, 4, "unsure")
            nf[i] += (ov if ov is not None else sv) == 4

    def share(k, n):
        return tuple((k[i] / n[i]) if n[i] >= min_obs else 1.0 for i in range(len(bins)))
    return Shares(bins=bins, similar=share(ns, nl), opus=share(no, nr), four=share(nf, nr), n_listed=tuple(nl),
                  n_read=tuple(nr))


def measured_overlap_tokens(records: Iterable[Mapping]) -> dict[str, tuple[int, int]]:
    """Mean billed ``(prompt-equivalent, output)`` tokens of the overlap calls in ``records`` (M3's
    ``responses.jsonl``) by role, ``sonnet`` and ``opus``; a role with none takes ``novelty_runner.OVERLAP_TOKENS``."""
    tot: dict[str, list] = defaultdict(lambda: [0, 0, 0])
    for r in records:
        if r.get("step") != "overlap" or not r.get("usage_raw"):
            continue
        role = r.get("role") or NR.model_role(r.get("model") or "")
        p, o = NR.billed_from_raw(r["usage_raw"])
        t = tot[role]
        t[0] += 1
        t[1] += p
        t[2] += o
    return {role: (int(round(tot[role][1] / tot[role][0])), int(round(tot[role][2] / tot[role][0])))
            if tot[role][0] else tuple(NR.OVERLAP_TOKENS[role]) for role in ("sonnet", "opus")}


def estimate_overlap(edge_cosines: Iterable[float], shares: Shares, *, overlap_floor: float = DEFAULT_OVERLAP_FLOOR,
                     overlap_tokens: Optional[Mapping[str, tuple[int, int]]] = None, transport: str = "live",
                     est: Optional[Estimate] = None) -> Estimate:
    """The overlap lines of the estimate: for each candidate edge at ``overlap_floor`` or above, the first direction
    read by Sonnet with the bin's similar share, Opus on that times the bin's Opus share, and the second direction
    on the similar share times the bin's four share (Sonnet, then Opus on :data:`SECOND_OPUS_SHARE` of it)."""
    est = est if est is not None else Estimate()
    tok = dict(NR.OVERLAP_TOKENS) | dict(overlap_tokens or {})
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    s1 = o1 = s2 = n = 0.0
    for c in edge_cosines:
        if c < overlap_floor:
            continue
        sim, op, four = shares.at(c)
        n += 1
        s1 += sim
        o1 += sim * op
        s2 += sim * four
    est.add(f"overlap, first direction, Sonnet ({int(n)} pairs at cosine {overlap_floor} or above, by the similar "
            f"share of their cosine bin)", NR.FIRST_MODEL + suffix, int(round(s1)), *tok["sonnet"])
    est.add("overlap, first direction, Opus (Sonnet's 3s, 4s and unsure, by bin)", NR.SECOND_MODEL + suffix,
            int(round(o1)), *tok["opus"])
    est.add("overlap, second direction, Sonnet (where the first read 4, by bin)", NR.FIRST_MODEL + suffix,
            int(round(s2)), *tok["sonnet"])
    est.add(f"overlap, second direction, Opus ({SECOND_OPUS_SHARE:.0%} of the second-direction Sonnet readings)",
            NR.SECOND_MODEL + suffix, int(round(s2 * SECOND_OPUS_SHARE)), *tok["opus"])
    return est


def estimate_build(*, relation_calls: Sequence[NR.Call], edge_cosines: Iterable[float], shares: Shares,
                   overlap_floor: float = DEFAULT_OVERLAP_FLOOR,
                   overlap_tokens: Optional[Mapping[str, tuple[int, int]]] = None, transport: str = "live",
                   unsure: Optional[tuple[float, float]] = None, cand_chars: float = 140.0, n_embed: int = 0,
                   embed_tokens_each: int = 30) -> Estimate:
    """The estimate before any call: the query embeddings not cached (and the 8 canary texts), the relation calls
    as rendered (``novelty_runner.call_tokens``: input from the characters, output from the relation model's
    measured figure per listed candidate), the unsure re-ask on Sonnet (``unsure``: ``(share of relation calls,
    candidates per re-ask)``, default the relation model's measured figures), and :func:`estimate_overlap`."""
    est = Estimate()
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    if n_embed:
        est.add("query embeddings not in the cache (OpenAI text-embedding-3-large) + the 8 canary texts",
                "text-embedding-3-large", 1, (n_embed + 8) * embed_tokens_each, 0)
    calls = list(relation_calls)
    if calls:
        model = calls[0].model
        toks = [NR.call_tokens(c) for c in calls]
        n_listed = sum(len(c.stems) for c in calls) / len(calls)
        est.add(f"relation call ({n_listed:.1f} listed candidates a call)", model + suffix, len(calls),
                int(round(sum(t[0] for t in toks) / len(toks))), int(round(sum(t[1] for t in toks) / len(toks))))
        share, per = unsure if unsure is not None else NR.unsure_for(model)
        sf = OT.tokenizer_factor(NR.UNSURE_MODEL)
        system = len(calls[0].system)
        est.add(f"unsure re-ask ({share:.0%} of relation calls, {per:g} candidates each)", NR.UNSURE_MODEL + suffix,
                int(round(share * len(calls))),
                int(round((system + cand_chars + per * cand_chars) / NR.CHARS_PER_TOKEN * sf)),
                int(round((NR.RELATION_OUT_BASE + NR.RELATION_OUT_PER_TRAIT * per) * sf)))
    return estimate_overlap(edge_cosines, shares, overlap_floor=overlap_floor, overlap_tokens=overlap_tokens,
                            transport=transport, est=est)
