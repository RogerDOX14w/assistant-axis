"""R1 of the trait-gap review tooling: the candidate graph and its cliques.

The brief is ``reports/trait_gap_generation/coding_plan_review.md`` (section 1, decisions 1-3, 9, 10 and 11;
section 2).  M3 (:mod:`assistant_axis.gapgen.novelty`) judges each candidate against the corpus alone, so
near-synonyms proposed together all come out ``new`` side by side.  This module builds, over the candidates a set
of M3 batches kept, a typed graph from which the review reads its groups:

* **Nodes** (:class:`Node`): the batches' kept candidates (M3 decision ``new`` or ``grey``, keyed by registry key);
  the corpus traits (``trait:<stem>``) and seed-queue entries (``queue:<stem>``) they touch; and, greyed, the
  batches' covered candidates, each pointing at the trait that covered it (decision 9: no edge, no call).  A
  candidate node carries its registry row's review block, when an earlier review batch applied one (``review_status``,
  ``review_into``, ``review_batch``, ``review_group``: :func:`review_fields`), and its ``seed_queue_stem`` when it
  was promoted.  A reviewed row is a node like any other, never left out: its edges are what tie this batch's new
  words to a decision already made, and the review app counts it handled from the start (section 11 of the brief).
* **Candidate edges** (``source: "r1"``): each kept candidate's ``k`` nearest other kept candidates by the cosine
  of their query embeddings in M3's covered space (the ``gloss_w14`` text as M3 embedded it, projected by the
  corpus index, so the cosines are on M3's scale and the floors calibrated on M3's readings apply), at the
  retrieval floor or above; **and** every pair at the pair floor (``pair_floor``, default 0.55) or above, however
  far down either list it sits (Roger, 2026-10-12, gate audit 8: in a dense region a concept has more than ``k``
  members and ``k`` alone cut 22% of the pairs he put together; ``None`` gives the k nearest alone, the rule
  before); **and** every pair of candidates whose labels are one label once case, hyphens, spaces and apostrophes
  are taken out (:func:`label_variant_key`, M3's blind form: other-worldly / otherworldly), wherever their
  cosine; **and** every noun and its adjective sibling (:func:`relabel_pairs`: the rows' ``relabel`` blocks name
  each other, ``assistant_axis.gapgen.nouns``; noun normalization plan, 2026-10-14), wherever their cosine.  An edge
  that only the pair floor (or only the label rule) brought in says so in ``via`` (``pair_floor``,
  ``label_variant``); a relabel pair's ``via`` is ``relabel`` wherever it came in; a k-nearest edge has none.  Each such pair is listed in both candidates'
  relation calls, and a list longer than :data:`RELATION_LIST_MAX` is split over several calls (one record per
  candidate still).  Typed by the relation call (rubric ``relation.md``, the relation model, one list per
  candidate as in M3, the other candidates' glosses as descriptions; ``unsure`` asked again of Sonnet as M3 does).
  Then, for an edge answered ``similar`` from either side (or ``unsure``, or ``similar`` from one side and
  ``opposed`` from the other) at the overlap floor or above (decision 11), the overlap call: rubric A, one pair per
  call, Sonnet then Opus under M3's rule at cut-off 4, through :meth:`NoveltyRunner.run_pairs` unchanged, the
  other candidate standing in the "other trait" slot (:class:`ReviewRunner` puts the kept candidates into the
  runner's corpus map under their keys).
* **The two directions.**  An edge is read first with the candidate whose key sorts first as the target; the
  other direction is read only when the first reads at the proposed cut-off (``proposed_cut_off``, default 3) or
  above, because only an edge read 3 or above both ways is a 3-edge (and only one read 4 both ways a 4-edge).
  This finds exactly the 3- and 4-edges that reading both directions of every edge would find, at about half the
  overlap calls; an edge whose first direction reads below the proposed cut-off keeps that one reading.  (The
  build of 2026-10-08 read the second direction only after a 4; decision 12 lowered it to 3, and a ``--resume``
  of such a build reads only the missing second directions.)
* **Corpus edges** (``source: "m3"``): copied from each kept candidate's M3 block, ``novelty.listed`` (cosine,
  relation, rank, via) and ``novelty.readings`` (the overlap readings, Sonnet and Opus); no call.  A listed trait
  or reading marked ``queue_status`` (M3 searched the seed queue, from 2026-10-09) is a seed-queue entry: its edge
  goes to ``queue:<stem>``, and a candidate M3 covered by one (``covered_by_queue``) points at that queue node.
* **Lexical edges** (``source: "lexical"``; plan 11 task 7, Roger's gate-2 decision of 2026-10-14, option (d)):
  copied from a kept candidate's ``lexical`` block (the lexical sweep, :mod:`assistant_axis.gapgen.lexical_sweep`),
  one per judged link and per name-only link (a text-less queue entry, no readings); a link M3 had listed already,
  and one the sweep left unjudged (a Moby pair under the cosine floor), is not drawn; no call.  The edge carries the
  sweep's readings and ``lexical`` (lexicon, link type, ``at_cut_off``).  **No lexical link ever cuts**, whichever
  lexicon: a link read at the row's own cut-off makes the candidate's node carry ``lexical_proposed_merge`` (the
  review card's "dictionary: probably the same as X"), and its M3 decision stays as it was; below-cut readings are
  not flagged (:data:`LEXICAL_NODE_FLAGS`).  With ``stem_family`` (:func:`plan_graph`), two kept candidates of one
  stem family (the block's ``family``) are a candidate edge, ``via`` ``stem_family``, wherever their cosine, typed
  by its readings like any edge and never a 3-edge unread.  A graph whose rows carry no ``lexical`` block is
  written exactly as before.
* **4-edges** (``strict``): both directions read 4 under the rule at cut-off 4 (:func:`reading_of`: Sonnet 4
  confirmed by Opus, Sonnet 3 raised to 4 by Opus, or Sonnet unsure and Opus 4), the relation not ``opposed``.
* **3-edges** (``proposed``; decision 12): both directions read at the proposed cut-off or above under M3's rule
  at that cut-off (``reading["proposed"]``: Sonnet above it, or Opus at it or above where Sonnet is at it or
  unsure), the relation not ``opposed``.  The escalation stays the rule at cut-off 4 (Opus reads Sonnet's 3s, 4s
  and unsure), so a Sonnet 2 is not sent to Opus and cannot become a 3 (the Opus pilot, below, measures what Opus
  would make of them, without changing the graph).  Every 4-edge is a 3-edge.  A **label variant** pair
  (``label_variant``) is a 3-edge whatever its readings and relation (Roger, 2026-10-12: "read or not"; the TDA
  case other-worldly / otherworldly read ``3/2`` because the two glosses took different senses), so the two are
  pre-assembled in one proposed group and Roger decides; it is never a 4-edge on that ground alone.  A relabel pair
  (pedant / pedantic) is pre-assembled the same way: ``label_variant`` set, ``via`` ``relabel``.
* **Merged groups** (``cliques``; the key keeps its R1 name): the maximal cliques of the 4-edges
  (:func:`maximal_cliques`, Bron-Kerbosch with a pivot), so a chain can never be a group; two cliques may overlap;
  a kept candidate in none is a ``singleton`` (R1's sense: in no merged group).  ``clique_links``: the pairs of
  cliques joined by an opposed edge (decision 3: opposed is an edge label, never merged across).
* **Proposed groups** (``proposed_groups``; decision 12): the maximal cliques of the 3-edges, less any that lies
  wholly inside a merged group (:func:`proposed_groups`); they may overlap each other and contain a merged group.
  The review app shows one pre-assembled and merges it only when Roger confirms.  ``proposed_links``: as
  ``clique_links``, over the proposed groups.  :meth:`Graph.ungrouped`: the kept candidates in no group of either
  tier.
* **Sibling groups** (``sibling_groups``; plan 09 section 12 item 3, Roger 2026-10-13): the structural generator's
  answers for one trait (its opposite, excess, deficiency and principal-target items), read from that generator's
  operator table when it exists, as groups to show together; they are not merged groups and change no edge or
  group above, and a graph with none is written exactly as before.

Cost: :func:`estimate_build` before any call (the relation calls as rendered, the overlap calls by per-cosine-bin
shares); the CLI checks it against the cap, and again after the relation calls on the pairs actually marked for
the overlap call (``gate``).  The shares come from an earlier R1 build's own records (:func:`r1_shares`, with its
measured tokens and unsure re-asks: the calibration, default ``review_tda_1``), since 2026-10-12; M3's
candidate-to-corpus shares (:func:`measured_shares`) put the TDA build's estimate at 3.2 times its spend (gate
audit 8) and remain the fallback when no earlier build is named.  A resumed build is estimated by
:func:`resume_estimate` instead: the build replayed on its records with nothing sent, the calls found missing
priced as rendered and the calls they lead to by the shares.

The Opus pilot (:func:`sonnet2_pairs`, :func:`select_pilot`, :meth:`ReviewRunner.run_opus`, :func:`pilot_report`;
Roger, 2026-10-12, gate audit 8 P2): Opus on a sample of first directions Sonnet read 2 (which the escalation never
sends it), half of them pairs Roger put in the same resolution and half pairs he resolved differently, the readings
written beside the build and compared with his decisions; the graph and its groups are not touched.

The CLI is ``data_analysis/gap_generation/review_graph.py``; outputs under ``data/candidates/review/<batch_id>/``.
"""
from __future__ import annotations

import asyncio
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.judge_pricing import BATCH_SUFFIX

from . import novelty as NV
from . import novelty_runner as NR
from . import overlap_test as OT
from . import paths
from .cost import Estimate

#: The cut-off of every candidate pair (decision 2): rubric A's 4, "the same concept"; a merged group's edges.
CUT_OFF = 4
#: Decision 12: a proposed group's edges read rubric A's 3 or above both ways ("the same concept, differing only
#: in scope, degree or emphasis"); also the reading that sends a pair's second direction.
DEFAULT_PROPOSED_CUT_OFF = 3
#: M3's rule set 2: a Sonnet 3 that Opus raises to 4 counts (decision 12 of the M3 section), as near alignment.
RULES = NV.RULES[2]
DEFAULT_K = 10
#: The retrieval floor among candidates: M3's (rule set 2).
DEFAULT_COSINE_FLOOR = NV.DEFAULT_COSINE_FLOOR
#: Decision 11: no overlap call on a candidate pair below this cosine.
DEFAULT_OVERLAP_FLOOR = 0.35
#: Roger, 2026-10-12 (gate audit 8, P1): beside each candidate's ``k`` nearest, every pair at this cosine or above is
#: a candidate edge (about 21 cents and about 20 more 3-edges on a TDA-sized build).  ``None``: the k nearest alone.
#: What it adds grows with density, not with the candidate count: 172 edges over the TDA build's 6,001 (871
#: candidates), 4,499 over 22,815 in the all-batches dry run of 2026-10-12 (3,193 candidates, about $6 more).
DEFAULT_PAIR_FLOOR = 0.55
#: The most candidates one relation call lists: a longer list (the pair floor in a dense region: 79 in the
#: all-batches plan of 2026-10-12) is split into calls of at most this many, as even as possible, since at Haiku 5.5's
#: measured 76.5 output tokens a listed candidate (``novelty_runner.RELATION_OUT_MEASURED``) 40 take about 3,060 of
#: the call's 4,096 and 54 would not fit.  A list of this many or fewer is one call, as before.
RELATION_LIST_MAX = 40
#: 4: the relabel pairs (a noun and its adjective sibling, ``via`` "relabel", pre-assembled as a label variant is;
#: noun normalization plan, 2026-10-14).  3: the pair floor and the label variants (an r1 edge's ``via`` and
#: ``label_variant``; a label variant is a 3-edge whatever its readings).  2: decision 12 (``proposed_groups``, ``proposed_links``, an edge's ``proposed``, a
#: reading's ``proposed``; the second direction read after a first at the proposed cut-off).  1: R1 as first built.
GRAPH_SCHEMA = 4
#: The M3 decisions a candidate is reviewed under (``grey`` is kept with a flag).
KEPT_DECISIONS = ("new", "grey")
NODE_KINDS = ("candidate", "corpus", "queue")
#: A candidate edge's relation, from its one or two answers (:func:`combine_relations`).
EDGE_RELATIONS = ("similar", "opposed", "unrelated", "unsure", "mixed", "unknown")
#: The relations that send a pair at the overlap floor or above to the overlap call.
OVERLAP_RELATIONS = ("similar", "unsure", "mixed")
#: ``Edge.overlap`` of a candidate edge: read both ways, read one way (the first read below the proposed cut-off),
#: similar but below the overlap floor, not similar, or left without an answer (a resume finishes it).
OVERLAP_STATES = ("both", "first", "below_floor", "not_similar", "stalled")
FIRST_WAVE, SECOND_WAVE = "ov1", "ov2"
#: The estimate's cosine bins (lower edges) and the observations a bin needs before its measured share is used.
#: They feed only the estimate: which readings reach Opus is M3's rule at cut-off 4 (``novelty.sonnet_action``).
SHARE_BINS = (0.35, 0.45, 0.55, 0.65)
MIN_SHARE_OBS = 10
#: The share of second-direction Sonnet readings assumed to go on to Opus when no earlier R1 build calibrates it
#: (:attr:`Shares.second_opus`; the TDA build measured 0.92: 706 of 771).
SECOND_OPUS_SHARE = 1.0
#: The earlier R1 build(s) whose own records calibrate the estimate by default (:func:`r1_shares`): the TDA build of
#: 2026-10-10, 871 candidates, $5.00 spent against $16.09 estimated from M3's shares.  Checked 2026-10-12: replayed
#: on itself the estimate is $4.99, every overlap line's calls exact; on review_pilots_1 (out of sample) its overlap
#: lines are within 15% of the calls that build's graph records (first-direction Sonnet 14% low, the rest 3-9% high).
DEFAULT_CALIBRATION = ("review_tda_1",)
#: The Opus pilot's default size and seed (gate audit 8, P2: 64 same-resolution and 64 different-resolution pairs).
PILOT_SIZE = 128
PILOT_SEED = 20261012
#: The cosine bins the pilot is stratified and reported by (lower edges).
PILOT_BINS = (0.35, 0.45, 0.55, 0.65)
#: The resolutions that settle a term's identity, for the pilot's reference (park and defer do not).
SETTLED_RESOLUTIONS = ("promote", "merge_into", "reject")
#: A ``lexical`` block's flags (``lexical_sweep.FLAGS``) as review flags on the candidate's node (Roger, 2026-10-14,
#: option (d)): a link read at the row's own cut-off is a proposed merge, never a cut; ``lexical_below_cut`` is not
#: carried (gate 2 (b): below-cut readings are not flagged).
LEXICAL_NODE_FLAGS = {"lexical_cover": "lexical_proposed_merge", "lexical_name_only": "lexical_name_only",
                      "lexical_unparsed": "lexical_unparsed", "lexical_antonym": "lexical_antonym"}
#: How the review card names a lexicon (so that the reviewer can tell a WordNet link from a thesaurus one).
LEXICON_NAMES = {"oewn": "WordNet", "moby": "Moby thesaurus"}


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
    outcome: Optional[str] = None               # M1's outcome when it is not "trait": "physical" (the physical pass),
                                                # "states" (the states pass)
    included: Optional[str] = None              # a covered candidate reviewed anyway (``build --include``): why
    # the registry row's review block when an earlier review batch applied one (not ``unreviewed``); a graph.json
    # from before 2026-10-11 has none of these, and the review app then reads the registry's rows instead
    review_status: Optional[str] = None         # accepted | rejected | merged_into | parked | deferred
    review_into: Optional[str] = None           # merged_into: trait:<stem>, queue:<stem>, or the nominee's key
    review_batch: Optional[str] = None          # the review batch and its group that decided it
    review_group: Optional[str] = None
    seed_queue_stem: Optional[str] = None       # a promoted row: its seed-queue entry

    def to_dict(self) -> dict:
        return _compact({f.name: getattr(self, f.name) for f in fields(self)})

    @classmethod
    def from_dict(cls, d: Mapping) -> "Node":
        return _from(cls, d)


#: The fields of :class:`Node` that :func:`review_fields` fills from a registry row.
REVIEW_FIELDS = ("review_status", "review_into", "review_batch", "review_group", "seed_queue_stem")


def review_fields(row: Optional[Mapping]) -> dict:
    """A registry row's review essentials, as :class:`Node` fields (every key of :data:`REVIEW_FIELDS`, ``None``
    where absent): its ``review`` block unless that is ``unreviewed``, and its ``seed_queue_stem``."""
    row = row or {}
    rv = row.get("review") or {}
    out = dict.fromkeys(REVIEW_FIELDS)
    out["seed_queue_stem"] = row.get("seed_queue_stem") or None
    if rv.get("status") not in (None, "unreviewed"):
        out.update(review_status=rv["status"], review_into=rv.get("into"), review_batch=rv.get("review_batch"),
                   review_group=rv.get("review_group"))
    return out


@dataclass
class Edge:
    a: str
    b: str
    cosine: Optional[float]
    relation: Optional[str]
    source: str                                  # r1 (a candidate pair, judged here) | m3 (copied from the block) |
                                                 # lexical (copied from the lexical block)
    strict: bool = False                         # a 4-edge
    proposed: bool = False                       # a 3-edge (decision 12; every 4-edge is one)
    relations: dict = field(default_factory=dict)   # r1: {"ab": a's answer about b, "ba": b's about a}
    readings: dict = field(default_factory=dict)    # {"ab": a as the target, "ba": b as the target}: reading_of()
    overlap: Optional[str] = None                # r1: OVERLAP_STATES
    via: Optional[str] = None                    # m3: retrieved | expanded | partner | renamed_from; r1: pair_floor |
                                                 # label_variant for an edge in neither k-nearest list (else None);
                                                 # relabel for a noun and its adjective, wherever it came in
    rank: Optional[int] = None                   # m3: the corpus trait's rank among the k retrieved
    label_variant: bool = False                  # r1: the two labels are one label blind, or a relabel pair (a
                                                 # 3-edge, read or not)
    lexical: Optional[dict] = None               # lexical: lexicon, link, word, judged, at_cut_off (a proposed
                                                 # merge), name_only, verdict, run_id (:func:`lexical_edges`)

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
    cliques: list                                 # the merged groups (maximal cliques of 4-edges)
    clique_links: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    usage: dict = field(default_factory=dict)
    complete: bool = True
    stalled: dict = field(default_factory=dict)   # what a resume still has to answer
    schema: int = GRAPH_SCHEMA
    proposed_groups: list = field(default_factory=list)   # decision 12: maximal 3-cliques not inside a merged one
    proposed_links: list = field(default_factory=list)
    #: the structural generator's outputs for one trait, shown together and never merged (:func:`sibling_groups`)
    sibling_groups: list = field(default_factory=list)

    def node_map(self) -> dict[str, Node]:
        return {n.key: n for n in self.nodes}

    def candidate_keys(self) -> list[str]:
        """The kept candidates (the review's terms), by key."""
        return [n.key for n in self.nodes if n.kind == "candidate" and (n.decision in KEPT_DECISIONS or n.included)]

    def strict_edges(self) -> list[tuple[str, str]]:
        return [(e.a, e.b) for e in self.edges if e.strict]

    def proposed_edges(self) -> list[tuple[str, str]]:
        return [(e.a, e.b) for e in self.edges if e.proposed]

    def singletons(self) -> list[str]:
        """The kept candidates in no merged group (R1's sense of the word)."""
        inside = {m for c in self.cliques for m in c}
        return [k for k in self.candidate_keys() if k not in inside]

    def ungrouped(self) -> list[str]:
        """The kept candidates in no group of either tier (merged or proposed)."""
        inside = {m for c in [*self.cliques, *self.proposed_groups] for m in c}
        return [k for k in self.candidate_keys() if k not in inside]

    def to_json(self) -> dict:
        return {"schema": self.schema, "batch_id": self.batch_id, "from_batches": list(self.from_batches),
                "config": dict(self.config), "complete": self.complete, "stalled": dict(self.stalled),
                "nodes": [n.to_dict() for n in self.nodes], "edges": [e.to_dict() for e in self.edges],
                "cliques": [list(c) for c in self.cliques], "singletons": self.singletons(),
                "clique_links": [dict(x) for x in self.clique_links],
                "proposed_groups": [list(c) for c in self.proposed_groups],
                "proposed_links": [dict(x) for x in self.proposed_links], "stats": dict(self.stats),
                "usage": dict(self.usage),
                # only when there are any, so a graph without structural candidates is written as before
                **({"sibling_groups": [dict(x) for x in self.sibling_groups]} if self.sibling_groups else {})}

    @classmethod
    def from_json(cls, d: Mapping) -> "Graph":
        """From :meth:`to_json`'s payload or the ``{"result", "_provenance"}`` envelope ``graph.json`` holds; a graph
        from before decision 12 (schema 1) has no proposed groups."""
        if "result" in d and "_provenance" in d:
            d = d["result"]
        return cls(batch_id=d["batch_id"], from_batches=list(d["from_batches"]), config=dict(d.get("config") or {}),
                   nodes=[Node.from_dict(x) for x in d["nodes"]], edges=[Edge.from_dict(x) for x in d["edges"]],
                   cliques=[list(c) for c in d["cliques"]], clique_links=[dict(x) for x in d.get("clique_links") or []],
                   stats=dict(d.get("stats") or {}), usage=dict(d.get("usage") or {}),
                   complete=bool(d.get("complete", True)), stalled=dict(d.get("stalled") or {}),
                   schema=int(d.get("schema", GRAPH_SCHEMA)),
                   proposed_groups=[list(c) for c in d.get("proposed_groups") or []],
                   proposed_links=[dict(x) for x in d.get("proposed_links") or []],
                   sibling_groups=[dict(x) for x in d.get("sibling_groups") or []])


def graph_envelope(graph: Graph, *, inputs=None, title: Optional[str] = None) -> dict:
    """``graph.json``'s content: the payload in the provenance envelope (``json_metadata``)."""
    from assistant_axis.plot_metadata import json_metadata
    return json_metadata(graph.to_json(), title=title or f"review_graph build {graph.batch_id}", inputs=inputs)


# --------------------------------------------------------------------------- the structural generator's siblings

#: The operators whose answers for one trait are shown as one group (plan 09 section 12 item 3; Roger, 2026-10-13:
#: "Sounds good"): the opposite and the two vices, and the principal-target retargets.
SIBLING_OPERATORS: tuple[str, ...] = ("opposite", "excess", "deficiency")


def structural_operator_table() -> list:
    """The structural generator's operator table, or ``[]`` when it has not been built (the sibling groups then
    stay empty and the graph is as it was)."""
    from .generators.structural import OPERATOR_TABLE_PATH, load_operator_table
    return load_operator_table(OPERATOR_TABLE_PATH) if OPERATOR_TABLE_PATH.exists() else []


def sibling_groups(candidate_keys: Iterable[str], operator_table: Sequence[Mapping]) -> list[dict]:
    """The structural generator's outputs for one trait, as groups to show together (never merged: an excess and a
    deficiency are opposite concepts): for each source trait, the kept candidates (by registry key, sense 1) that the
    operator table has as its opposite, excess or deficiency, or as a principal-target retarget, when there are two
    or more.  ``[{"trait": "trait:<stem>", "members": [keys], "roles": {key: [operators]}}]``, in trait order.
    Reads only the operator table, so no other generator's rows are touched."""
    keys = set(candidate_keys)
    by_trait: dict[str, dict] = defaultdict(dict)
    for row in operator_table:
        key = f"{row.get('stem')}#1"
        if key not in keys:
            continue
        for src in row.get("sources") or []:
            if src.get("generator_part") != "operators" or not src.get("source_stem"):
                continue
            op = src.get("operator")
            if op in SIBLING_OPERATORS:
                role = op
            elif src.get("kind") == "principal_retarget":
                role = f"retarget:{src.get('target')}"
            else:
                continue
            by_trait[src["source_stem"]].setdefault(key, set()).add(role)
    return [{"trait": corpus_key(stem), "members": sorted(m), "roles": {k: sorted(v) for k, v in sorted(m.items())}}
            for stem, m in sorted(by_trait.items()) if len(m) >= 2]


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


def proposed_groups(proposed_edges: Iterable[tuple[str, str]], merged: Sequence[Sequence[str]]) -> list[list[str]]:
    """Decision 12: the maximal cliques of the 3-edges, less any that lies wholly inside a merged group (a merged
    group is itself a 3-clique, so this drops exactly the 3-cliques a merged group already is).  Largest first."""
    merged_sets = [set(c) for c in merged]
    return [c for c in maximal_cliques(proposed_edges) if not any(set(c) <= m for m in merged_sets)]


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

def reading_of(r: Mapping, *, proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF) -> dict:
    """One direction's overlap reading (a :meth:`NoveltyRunner.read_pairs` result, or an M3 reading of the same
    shape) under the rule at cut-off 4, and at the proposed cut-off (decision 12): ``{"sonnet", "opus", "verdict",
    "four", "proposed", "reasons"?, "errors"?}`` (``verdict`` at cut-off 4); ``{"stalled": why}`` for a pair left
    without an answer."""
    if "stalled" in r:
        return {"stalled": r["stalled"]}
    s = r.get("sonnet") or {}
    o = r.get("opus") or None
    sv = s.get("value")
    ov = o.get("value") if o else None
    pv = NV.pair_verdict(sv, ov, CUT_OFF)
    four = NV.verdict_cuts(pv["verdict"], RULES)
    pp = NV.pair_verdict(sv, ov, proposed_cut_off)
    out = {"sonnet": sv, "opus": ov, "verdict": pv["verdict"], "four": four,
           "proposed": bool(four if proposed_cut_off >= CUT_OFF else NV.verdict_cuts(pp["verdict"], RULES))}
    reasons = {m: x["reason"] for m, x in (("sonnet", s), ("opus", o or {})) if x.get("reason")}
    errors = {m: x["error"] for m, x in (("sonnet", s), ("opus", o or {})) if x.get("error")}
    if reasons:
        out["reasons"] = reasons
    if errors:
        out["errors"] = errors
    return out


def is_four(r: Optional[Mapping]) -> bool:
    return bool(r) and "stalled" not in r and reading_of(r)["four"]


def needs_second(r: Optional[Mapping], proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF) -> bool:
    """Whether a first-direction reading sends the pair's second direction: it reads at the proposed cut-off or
    above (decision 12), or 4."""
    if not r or "stalled" in r:
        return False
    rd = reading_of(r, proposed_cut_off=proposed_cut_off)
    return bool(rd["four"] or rd["proposed"])


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
    """One candidate's relation answer about ``other`` (Sonnet's where it re-asked an ``unsure``): the answer on
    record (``unparsed`` for a listed candidate whose call never parsed), else ``unparsed`` for a record whose one
    call never parsed, else none (a call that failed or was not sent)."""
    if rec is None:
        return None
    a = (rec.get("answers") or {}).get(other)
    if a is not None:
        return (a.get("second") or {}).get("relation") or a.get("relation")
    return "unparsed" if rec.get("status") == "unparsed" else None


def edge_answers(relations: Mapping[str, Mapping], a: str, b: str) -> tuple[Optional[str], Optional[str]]:
    return _answer(relations.get(a), b), _answer(relations.get(b), a)


# --------------------------------------------------------------------------- the candidates and the plan

class PairCandidate(NR.M3Candidate):
    """A kept candidate as the overlap call reads it here: cut-off 4 whatever its alignment score (decision 2)."""

    @property
    def cut_off(self) -> int:
        return CUT_OFF


def _gloss(row: Mapping) -> Optional[str]:
    from . import physical_pass as PP
    from . import states_pass as SP
    g = (row.get("gloss") or (row.get("filter") or {}).get("gloss") or (row.get(PP.BLOCK) or {}).get("gloss")
         or SP.gloss_of(row))
    return g.strip() if isinstance(g, str) and g.strip() else None


def _holding_of(row: Mapping) -> Optional[str]:
    """The holding list a row was judged from: ``physical`` for a row whose M3 block came from the physical pass,
    ``states`` for one from the states pass (``novelty.pass``), else None (a trait row, read as before)."""
    from . import physical_pass as PP
    from . import states_pass as SP
    p = (row.get("novelty") or {}).get("pass")
    return PP.HOLDING if p == PP.PASS_NAME else SP.PASS_NAME if p == SP.PASS_NAME else None


def pair_candidate(row: Mapping) -> tuple[Optional[PairCandidate], Optional[str]]:
    """``(candidate, None)``, or ``(None, why)`` for a row M3 could not have judged (``candidate_from_row``; a
    physical pass's row by that pass's builder)."""
    row = dict(row)
    if not row.get("gloss") and _gloss(row):
        row["gloss"] = _gloss(row)
    holding = _holding_of(row)
    c, why = NR.candidate_from_row(row, holding=holding) if holding else NR.candidate_from_row(row)
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
    included: dict = field(default_factory=dict)   # key -> reason: covered candidates reviewed anyway
    k: int = DEFAULT_K
    pair_floor: Optional[float] = None             # None: the k nearest alone (the rule before 2026-10-12)
    via: dict = field(default_factory=dict)        # (a, b) -> pair_floor | label_variant: in neither k-nearest list;
                                                   # relabel: a relabel pair, wherever it came in
    label_variants: list = field(default_factory=list)   # [(a, b)]: the pairs whose labels are one label blind
    relabel_pairs: list = field(default_factory=list)    # [(a, b)]: a noun and its adjective sibling (relabel blocks)
    family_pairs: list = field(default_factory=list)     # [(a, b)]: one stem family (lexical blocks; stem_family on)

    def relation_items(self) -> list[tuple[str, list[str]]]:
        """``(key, [other keys])`` of every kept candidate with a neighbour, by key: one relation call each."""
        return [(k, [o for o, _ in self.neighbours[k]]) for k in sorted(self.neighbours) if self.neighbours[k]]

    def edge_counts(self) -> dict:
        """The candidate edges by how they came in (``k_nearest``, ``pair_floor``, ``label_variant``), the label
        variant pairs (wherever they came from), the listed slots, the longest list, and the relation calls (a
        list longer than :data:`RELATION_LIST_MAX` is split: ``lists_split``)."""
        by = Counter(self.via.get(e, "k_nearest") for e in self.edges)
        lens = [len(v) for v in self.neighbours.values() if v]
        # "relabel" only when there are any, so a plan without relabel pairs counts as before
        vias = ("k_nearest", "pair_floor", "label_variant") + (("relabel",) if by["relabel"] else ()) \
            + (("stem_family",) if by["stem_family"] else ())
        out = {"n_candidate_edges": len(self.edges), "by_via": {k: by[k] for k in vias},
               "n_label_variant_pairs": len(self.label_variants), "n_relabel_pairs": len(self.relabel_pairs),
               "k": self.k, "pair_floor": self.pair_floor,
               "n_listed": sum(lens), "longest_list": max(lens, default=0),
               "n_relation_calls": sum(-(-n // RELATION_LIST_MAX) for n in lens),
               "lists_split": sum(1 for n in lens if n > RELATION_LIST_MAX)}
        if self.family_pairs:                      # only then, so a plan without them counts as before
            out["n_family_pairs"] = len(self.family_pairs)
        return out


def select_rows(rows: Mapping[str, Mapping], batch_ids: Sequence[str],
                include: Collection[str] = ()) -> tuple[dict, dict, dict, dict]:
    """``(kept, covered, skipped, by_batch)``: the rows whose ``novelty.run_id`` is one of ``batch_ids``, kept
    (decision new or grey) or covered.  A row two batches decided carries the later block only, so it is selected
    by that batch.  A covered row whose key is in ``include`` is kept (reviewed anyway; Roger, 2026-10-09, after
    the cover audit)."""
    bset = set(batch_ids)
    kept, covered, skipped = {}, {}, Counter()
    by_batch: dict[str, Counter] = {b: Counter() for b in batch_ids}
    for k, r in sorted(rows.items()):
        nv = r.get("novelty") or {}
        if nv.get("run_id") not in bset:
            continue
        d = nv.get("decision")
        by_batch[nv["run_id"]][d] += 1
        if d in KEPT_DECISIONS or (d == "covered" and k in include):
            kept[k] = r
        elif d == "covered":
            covered[k] = r
        else:
            skipped[f"decision_{d}"] += 1
    return kept, covered, dict(skipped), {b: dict(c) for b, c in by_batch.items()}


def _cosines(vectors: Mapping[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    keys = sorted(vectors)
    Q = np.stack([np.asarray(vectors[x], dtype=np.float64) for x in keys])
    Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)
    return keys, Q @ Q.T


def nearest_candidates(vectors: Mapping[str, np.ndarray], *, k: int = DEFAULT_K, floor: float = DEFAULT_COSINE_FLOOR,
                       pair_floor: Optional[float] = None) -> dict[str, list[tuple[str, float]]]:
    """Each key's ``k`` nearest other keys by cosine (nearest first, ties by key), those under ``floor`` dropped;
    then, with ``pair_floor``, every further key at ``pair_floor`` (and ``floor``) or above, nearest first.  The
    first ``k`` entries of a list are its k nearest; anything after them came in by the pair floor."""
    keys = sorted(vectors)
    out: dict[str, list] = {key: [] for key in keys}
    if len(keys) < 2:
        return out
    keys, S = _cosines(vectors)
    idx = np.arange(len(keys))
    extra_floor = None if pair_floor is None else max(float(pair_floor), float(floor))
    for i, a in enumerate(keys):
        s = S[i].copy()
        s[i] = -np.inf
        order = np.lexsort((idx, -s))
        for rank, j in enumerate(order):
            c = float(s[j])
            least = floor if rank < k else extra_floor
            if least is None or c < least:
                break
            out[a].append((keys[j], round(c, 6)))
    return out


def label_variant_key(label: str) -> str:
    """A label with case, hyphens, spaces, apostrophes and diacritics taken out (M3's blind form, decision 15:
    ``other-worldly`` and ``otherworldly`` are one label)."""
    return NV.blind(normalize_to_file_name(label))


def label_variant_pairs(cands: Mapping[str, Any]) -> list[tuple[str, str]]:
    """The pairs of candidates (``key -> PairCandidate``) whose labels are one label blind and whose stems differ
    (two senses of one word are split rows by design, not variants), ``(a, b)`` with ``a < b``, sorted."""
    by: dict[str, list[str]] = defaultdict(list)
    for key_, c in cands.items():
        by[label_variant_key(c.label)].append(key_)
    out = []
    for ks in by.values():
        ks = sorted(ks)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if cands[a].stem != cands[b].stem:
                    out.append((a, b))
    return sorted(out)


def relabel_pairs(rows: Mapping[str, Mapping]) -> list[tuple[str, str]]:
    """The pairs of rows (``key -> registry row``) linked by their ``relabel`` blocks, either way (a noun's
    ``to_key``, an adjective's ``from_key``; :mod:`assistant_axis.gapgen.nouns`), both in ``rows``: ``(a, b)`` with
    ``a < b``, sorted."""
    out = set()
    for k, r in rows.items():
        b = r.get("relabel") or {}
        for other in (b.get("to_key"), b.get("from_key")):
            if other and other != k and other in rows:
                out.add(tuple(sorted((k, other))))
    return sorted(out)


def stem_family_pairs(rows: Mapping[str, Mapping]) -> list[tuple[str, str]]:
    """The pairs of rows (``key -> registry row``) one row's ``lexical`` block names as its stem family (``family``
    members of kind ``candidate``, by stem: every row of that stem in ``rows``), ``(a, b)`` with ``a < b``, sorted."""
    by_stem: dict[str, list[str]] = defaultdict(list)
    for k, r in rows.items():
        if r.get("stem"):
            by_stem[r["stem"]].append(k)
    out = set()
    for k, r in rows.items():
        for f in (r.get("lexical") or {}).get("family") or []:
            if f.get("kind") != "candidate":
                continue
            for other in by_stem.get(f.get("stem"), ()):
                if other != k:
                    out.add(tuple(sorted((k, other))))
    return sorted(out)


def plan_graph(rows: Mapping[str, Mapping], batch_ids: Sequence[str], vectors: Mapping[str, np.ndarray], *,
               k: int = DEFAULT_K, cosine_floor: float = DEFAULT_COSINE_FLOOR,
               pair_floor: Optional[float] = DEFAULT_PAIR_FLOOR,
               include: Optional[Mapping[str, str]] = None, stem_family: bool = False) -> GraphPlan:
    """The batches' kept and covered rows, and the candidate edges: each kept candidate's ``k`` nearest other kept
    candidates by ``vectors`` (projected query vectors, by key) at ``cosine_floor`` or above, every pair at
    ``pair_floor`` or above (``None``: none beyond the k nearest), and every label variant pair
    (:func:`label_variant_pairs`) at whatever cosine; with ``stem_family``, every stem-family pair of the rows'
    ``lexical`` blocks (:func:`stem_family_pairs`) too, wherever its cosine.  A pair the pair floor, the label rule
    or the family brought in is listed in both candidates' relation calls (after the k nearest, nearest first) and
    recorded in ``via``.  A candidate with no vector has no candidate edge, a label variant's included."""
    include = dict(include or {})
    kept, covered, skipped, by_batch = select_rows(rows, batch_ids, include=include)
    cands, rows_kept = {}, {}
    skipped = Counter(skipped)
    for key_, r in kept.items():
        c, why = pair_candidate(r)
        if c is None:
            skipped[why] += 1
            continue
        cands[key_], rows_kept[key_] = c, r
    no_vector = sorted(x for x in cands if x not in vectors)
    with_vec = {x: vectors[x] for x in cands if x in vectors}
    nbrs = nearest_candidates(with_vec, k=k, floor=cosine_floor, pair_floor=pair_floor)
    for x in no_vector:
        nbrs[x] = []
    ranked = {a: {b for b, _ in lst[:k]} for a, lst in nbrs.items()}
    edges: dict[tuple[str, str], float] = {}
    via: dict[tuple[str, str], str] = {}
    for a, lst in nbrs.items():
        for b, c in lst:
            e = tuple(sorted((a, b)))
            edges[e] = c
            if b not in ranked[a] and a not in ranked[b]:
                via[e] = "pair_floor"
    variants = [p for p in label_variant_pairs(cands) if p[0] in with_vec and p[1] in with_vec]
    relabels = [p for p in relabel_pairs(rows_kept) if p[0] in with_vec and p[1] in with_vec and p not in set(variants)]
    families = [p for p in stem_family_pairs(rows_kept) if p[0] in with_vec and p[1] in with_vec
                and p not in set(variants) and p not in set(relabels)] if stem_family else []
    if variants or relabels or families:
        keys, S = _cosines(with_vec)
        pos = {x: i for i, x in enumerate(keys)}
        for (a, b), how in [*((p, "label_variant") for p in variants), *((p, "relabel") for p in relabels),
                            *((p, "stem_family") for p in families)]:
            if how == "relabel":
                via[(a, b)] = "relabel"           # wherever it came in: the pair is the relabel step's
            if (a, b) in edges:
                continue
            c = round(float(S[pos[a], pos[b]]), 6)
            edges[(a, b)] = c
            via[(a, b)] = how
            nbrs[a].append((b, c))
            nbrs[b].append((a, c))
        for x in {m for p in [*variants, *relabels, *families] for m in p}:
            head, tail = nbrs[x][:k], nbrs[x][k:]
            nbrs[x] = head + sorted(tail, key=lambda t: (-t[1], t[0]))
    return GraphPlan(batch_ids=list(batch_ids), cands=cands, rows=rows_kept, covered=covered,
                     neighbours={x: nbrs[x] for x in sorted(nbrs)}, edges=dict(sorted(edges.items())),
                     skipped=dict(skipped), no_vector=no_vector, by_batch=by_batch,
                     included={x: include[x] for x in sorted(include) if x in rows_kept}, k=k, pair_floor=pair_floor,
                     via=dict(sorted(via.items())), label_variants=variants, relabel_pairs=relabels,
                     family_pairs=families)


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
        # the parent's call, with the listed names looked up in the corpus map (corpus traits and candidates); the
        # labels as stored, shown in the runner's label form (the judge display form for a new build)
        traits = [(self.corpus[s]["label"], self.corpus[s]["description"]) for s in stems]
        user = NV.render_relation_user(st.cand.label, st.cand.gloss, traits, label_form=self.label_form)
        model = self.relation_model if step == "relation" else NR.UNSURE_MODEL
        return NR.Call(step=step, role=NR.model_role(model), key=st.cand.key, model=model,
                       system=self.rubrics["relation"]["text"], user=user, max_tokens=NR.RELATION_MAX_TOKENS,
                       temperature=NR.TEMPERATURE, cache_system=False, stems=tuple(stems))

    def relation_calls(self, items: Sequence[tuple[str, Sequence[str]]]) -> list[NR.Call]:
        """The relation calls of ``(key, others)``: the others in the order seeded by the run and the key, one call
        for up to :data:`RELATION_LIST_MAX` of them, a longer list split in that order into the fewest calls that
        hold it, as even as possible."""
        out = []
        for k, others in items:
            order = NV.relation_order(others, self.relation_seed, k)
            n = max(1, -(-len(order) // RELATION_LIST_MAX))
            for part in np.array_split(np.arange(len(order)), n):
                out.append(self._relation_call(self.states[k], [order[i] for i in part]))
        return out

    def overlap_call(self, key: str, other: str, role: str = "sonnet", position: int = 1) -> NR.Call:
        return self._overlap_call(self.states[key], other, role, position)

    def on_record(self, call: NR.Call) -> bool:
        """Whether an answer to ``call`` is on record (a resume replays it instead of sending it)."""
        return call.cache_key() in self.cache_good

    def run_opus(self, pairs: Sequence[tuple[str, str]], *, wave: str = "pilot_opus") -> dict[tuple[str, str], dict]:
        """Opus on each ``(target, other)`` of ``pairs``, the prompt Sonnet read for that direction (the overlap call
        with Opus's model; the candidates must be added), whatever Sonnet answered: the Opus pilot.  ``{(a, b):
        {"opus": {"value", "reason"} | {"value": None, "error"}} | {"stalled": why}}``.  A stop is raised after every
        answer received is recorded."""
        return asyncio.run(self._run_opus(pairs, wave))

    async def _run_opus(self, pairs, wave) -> dict[tuple[str, str], dict]:
        self._stop = None
        calls = [self.overlap_call(a, b, "opus", 1) for a, b in pairs]
        res = await self._wave(wave, calls)
        out: dict[tuple[str, str], dict] = {}
        for (a, b), c in zip(pairs, calls):
            o = res[id(c)]
            if o.status == "ok":
                out[(a, b)] = {"opus": {"value": o.parsed["value"], "reason": o.parsed["reason"]}}
            elif o.status == "unparsed":
                out[(a, b)] = {"opus": {"value": None, "error": o.error}}
            else:
                out[(a, b)] = {"stalled": f"Opus on {a} > {b}: {o.status}"}
        if self._stop is not None:
            raise self._stop
        return out

    def run_relations(self, items: Sequence[tuple[str, Sequence[str]]]) -> dict[str, dict]:
        """The relation calls of ``items`` (wave ``r1_relation``), then Sonnet on the ``unsure`` answers
        (``r2_relation_unsure``, one re-ask per candidate), as M3 sends them.  ``{key: {"status", "model", "order",
        "answers": {other: {"relation", "reason", "second"?}}, "error"?, "unsure_reasked"?, "parts"?}}``; a list split
        over several calls (:meth:`relation_calls`) is one record: ``parts`` the calls' statuses and sizes,
        ``status`` the worst of them (failed or not sent, then unparsed), and the candidates of a part that never
        parsed answered ``unparsed``.  A stop is raised after every answer received is recorded."""
        return asyncio.run(self._run_relations(items))

    async def _run_relations(self, items) -> dict[str, dict]:
        self._stop = None
        calls = self.relation_calls(items)
        res = await self._wave("r1_relation", calls)
        out: dict[str, dict] = {}
        unsure_calls = []
        rank = {"ok": 0, "unparsed": 1, "not_sent": 2, "failed": 2}
        for c in calls:
            o = res[id(c)]
            rec = out.get(c.key)
            if rec is None:
                rec = out[c.key] = {"status": o.status, "model": c.model, "order": [], "answers": {}}
            else:
                rec.setdefault("parts", [{"status": rec["status"], "n": len(rec["order"])}])
                rec["parts"].append({"status": o.status, "n": len(c.stems)})
                if rank.get(o.status, 2) > rank.get(rec["status"], 2):
                    rec["status"] = o.status
            rec["order"] += list(c.stems)
            if o.status == "ok":
                for i, s in enumerate(c.stems, 1):
                    row = o.parsed[i]
                    rec["answers"][s] = {"relation": row["value"], "reason": row["reason"]}
            elif o.status == "unparsed" and "parts" in rec:
                for s in c.stems:
                    rec["answers"][s] = {"relation": "unparsed"}
            if o.error:
                rec["error"] = "; ".join(filter(None, [rec.get("error"), o.error]))
        for k, rec in out.items():
            if "parts" in rec and rec["parts"][0]["status"] == "unparsed":
                for s in rec["order"][:rec["parts"][0]["n"]]:
                    rec["answers"][s] = {"relation": "unparsed"}
            unsure = [s for s in rec["order"] if (rec["answers"].get(s) or {}).get("relation") == "unsure"]
            if unsure:
                unsure_calls.append(self._relation_call(self.states[k], unsure, step="relation_unsure"))
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
                gate: Optional[Callable[[list[tuple[str, str, float]]], None]] = None,
                proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF) -> Graph:
    """The relation calls, the overlap calls (first direction, then the second where the first read at the
    proposed cut-off or above), and the graph (:func:`assemble_graph`).  ``corpus``: stem ->
    :class:`novelty.CorpusTrait` (labels and descriptions of the corpus nodes); ``queue``: the seed queue
    (``{"entries": [...]}``); ``gate(pairs)``: called with the pairs marked for the overlap call before any is sent
    (the CLI's second cost check; it raises to stop).  A stop (budget, gate) is raised after every answer received
    is recorded in ``runner.responses_path``."""
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
    back = [(b, a, 2) for a, b, _ in pairs if needs_second(first.get((a, b)), proposed_cut_off)]
    second: dict = {}
    if back:
        targets = [plan.cands[b] for b in dict.fromkeys(b for b, _, _ in back)]
        second = runner.run_pairs(targets, back, wave=SECOND_WAVE)
    return assemble_graph(plan, relations=relations, first=first, second=second, overlap_floor=overlap_floor,
                          corpus=corpus, queue=queue, config=config, batch_id=batch_id or runner.batch_id,
                          usage=runner.usage.as_dict(), proposed_cut_off=proposed_cut_off)


def _candidate_node(row: Mapping) -> Node:
    nv, f = row.get("novelty") or {}, row.get("filter") or {}
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    a = nv.get("alignment_score", f.get("alignment"))
    return Node(key=row["key"], kind="candidate", label=row.get("label") or row["key"], gloss=_gloss(row),
                stem=row.get("stem"), generator=gens[0] if gens else None, generators=gens, verdict=f.get("verdict"),
                decision=nv.get("decision"), flags=list(nv.get("review") or []) + lexical_flags(row),
                region=f.get("region") or nv.get("region"),
                alignment_score=a if isinstance(a, int) and not isinstance(a, bool) else None, m3_run=nv.get("run_id"),
                outcome=f.get("outcome") if f.get("outcome") not in (None, "trait") else None, **review_fields(row))


def lexical_flags(row: Mapping) -> list[str]:
    """The row's ``lexical`` block flags as review flags (:data:`LEXICAL_NODE_FLAGS`; ``lexical_below_cut`` is not
    carried); none without a block."""
    return [LEXICAL_NODE_FLAGS[f] for f in (row.get("lexical") or {}).get("flags") or [] if f in LEXICAL_NODE_FLAGS]


def lexical_edges(key_: str, row: Mapping, *, proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF) -> list[Edge]:
    """The row's ``lexical`` block as ``source: "lexical"`` edges (module docstring): one per judged link, with the
    sweep's readings, and one per name-only link, without; a link M3 listed already, and one the sweep did not
    judge for another reason (a Moby pair under the cosine floor, a stalled pair), is not drawn.  Never a cut: the
    edge says ``at_cut_off`` (a proposed merge), nothing more."""
    blk = row.get("lexical") or {}
    out = []
    for x in blk.get("links") or []:
        if not x.get("stem") or x.get("listed_by_m3") or not (x.get("judged") or x.get("name_only")):
            continue
        info = {"lexicon": x.get("lexicon"), "link": x.get("link"), "word": x.get("word"),
                "judged": bool(x.get("judged")), "at_cut_off": bool(x.get("judged") and x.get("at_cut_off")),
                "name_only": bool(x.get("name_only")), "verdict": x.get("verdict"), "run_id": blk.get("run_id")}
        b = queue_key(x["stem"]) if x.get("kind") == "queue" else corpus_key(x["stem"])
        rd = {"ab": reading_of(x, proposed_cut_off=proposed_cut_off)} if x.get("judged") else {}
        out.append(Edge(a=key_, b=b, cosine=x.get("cosine"), relation=None, source="lexical", readings=rd,
                        via=f"{x.get('lexicon')}:{x.get('link')}", lexical={k: v for k, v in info.items() if v is not None}))
    return out


def lexical_counts(edges: Iterable[Edge], flags: Iterable[Sequence[str]]) -> dict:
    """The lexical edges and flags in figures: edges by lexicon and link, judged, proposed merges (by lexicon),
    name-only; candidates by lexical flag, and those with a proposed merge."""
    lex = [e for e in edges if e.source == "lexical"]
    merges = [e for e in lex if (e.lexical or {}).get("at_cut_off")]
    fl = Counter(f for fs in flags for f in fs if f.startswith("lexical_"))
    return {"n_edges": len(lex), "by_lexicon": _dist(Counter((e.lexical or {}).get("lexicon") for e in lex)),
            "by_link": _dist(Counter(e.via for e in lex)),
            "judged": sum(1 for e in lex if (e.lexical or {}).get("judged")), "proposed_merges": len(merges),
            "proposed_merges_by_lexicon": _dist(Counter((e.lexical or {}).get("lexicon") for e in merges)),
            "name_only": sum(1 for e in lex if (e.lexical or {}).get("name_only")),
            "candidates_by_flag": _dist(fl), "candidates_with_proposed_merge": fl.get("lexical_proposed_merge", 0)}


def lexical_counts_of_rows(rows: Mapping[str, Mapping], *, proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF) -> dict:
    """:func:`lexical_counts` straight from the kept rows (what the graph built on them would hold; the dry run's
    figures)."""
    edges = [e for k in sorted(rows) for e in lexical_edges(k, rows[k], proposed_cut_off=proposed_cut_off)]
    return lexical_counts(edges, (lexical_flags(r) for r in rows.values()))


def _covering(nv: Mapping) -> Optional[tuple[str, str]]:
    """``(kind, stem)`` of the trait that covered a candidate: the queue entry for an exact-label queue match or
    for a cover by a seed-queue entry through M3's walk (``covered_by_queue``, from 2026-10-09), else the corpus
    trait."""
    stem = nv.get("covered_by")
    if not stem:
        return None
    if (nv.get("exact_label") or {}).get("match") == "queue" or nv.get("covered_by_queue"):
        return "queue", stem
    return "corpus", stem


def _m3_target(stem: str, x: Mapping) -> tuple[str, str]:
    """``(kind, node key)`` of a trait an M3 block lists or reads: a seed-queue entry (its ``queue_status``, from
    2026-10-09, when M3 searched the queue) or a corpus trait."""
    return ("queue", queue_key(stem)) if x.get("queue_status") else ("corpus", corpus_key(stem))


def _value(x: Any) -> Any:
    return x.get("value") if isinstance(x, Mapping) else None


def assemble_graph(plan: GraphPlan, *, relations: Mapping[str, Mapping], first: Mapping, second: Mapping,
                   corpus: Mapping[str, Any], queue: Optional[Mapping] = None,
                   overlap_floor: float = DEFAULT_OVERLAP_FLOOR, config: Optional[Mapping] = None,
                   batch_id: str = "", usage: Optional[Mapping] = None,
                   proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF,
                   operator_table: Optional[Sequence[Mapping]] = None) -> Graph:
    """The :class:`Graph` from the plan and the answers (no call): nodes, the candidate edges with their relations
    and readings, the corpus edges copied from the M3 blocks, the 4- and 3-edges, the merged and proposed groups
    and their opposed links; and, where the structural generator's operator table exists (``operator_table``, read
    from its path when None), the sibling groups of its candidates (:func:`sibling_groups`)."""
    rd_of = lambda r: reading_of(r, proposed_cut_off=proposed_cut_off)  # noqa: E731
    corpus_stems: set[str] = set()
    queue_stems: set[str] = set()
    def mark_covered(n: Node, nv: Mapping) -> None:
        cov = _covering(nv)
        if cov:
            (queue_stems if cov[0] == "queue" else corpus_stems).add(cov[1])
            n.covered_by = (queue_key if cov[0] == "queue" else corpus_key)(cov[1])
        d = nv.get("deciding_reading")
        if d:
            n.covered_reading = {"stem": d.get("stem"), "cosine": d.get("cosine"), "sonnet": _value(d.get("sonnet")),
                                 "opus": _value(d.get("opus"))}

    nodes = [_candidate_node(plan.rows[k]) for k in sorted(plan.rows)]
    for n in nodes:
        if n.key in plan.included:
            n.included = plan.included[n.key]
            mark_covered(n, plan.rows[n.key].get("novelty") or {})
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
    # a relabel pair is pre-assembled as a label variant is (noun normalization plan): ``label_variant`` set
    variants = {tuple(p) for p in plan.label_variants} | {tuple(p) for p in plan.relabel_pairs}
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
            readings["ab"] = rd_of(f)
        if s is not None:
            readings["ba"] = rd_of(s)
        second_due = f is not None and needs_second(f, proposed_cut_off)
        if rel not in OVERLAP_RELATIONS:
            state = "not_similar"
        elif cos < overlap_floor:
            state = "below_floor"
        elif f is None or "stalled" in f or (second_due and (s is None or "stalled" in s)):
            state = "stalled"
        elif second_due:
            state = "both"
        else:
            state = "first"
        if state == "stalled":
            stalled["overlap"].append([a, b])
        both_ways = state == "both" and rel != "opposed"
        strict = both_ways and readings["ab"]["four"] and readings["ba"]["four"]
        proposed = both_ways and all(readings[d]["four"] or readings[d]["proposed"] for d in ("ab", "ba"))
        variant = (a, b) in variants
        edges.append(Edge(a=a, b=b, cosine=cos, relation=rel, source="r1", strict=bool(strict),
                          proposed=bool(proposed or variant),
                          relations={d: v for d, v in (("ab", ra), ("ba", rb)) if v is not None},
                          readings=readings, overlap=state, via=plan.via.get((a, b)), label_variant=variant))

    for key_ in sorted(plan.rows):
        nv = plan.rows[key_].get("novelty") or {}
        judged = {r["stem"]: r for r in nv.get("readings") or [] if r.get("stem")}
        seen = set()
        for x in nv.get("listed") or []:
            stem = x["stem"]
            seen.add(stem)
            kind, b = _m3_target(stem, x)
            (queue_stems if kind == "queue" else corpus_stems).add(stem)
            rd = {"ab": rd_of(judged[stem]) | {"outcome": judged[stem].get("outcome")}} if stem in judged else {}
            edges.append(Edge(a=key_, b=b, cosine=x.get("cosine"), relation=x.get("relation") or "unknown",
                              source="m3", readings=rd, via=x.get("via"), rank=x.get("rank")))
        for stem, r in judged.items():          # judged but not listed: an opposite's partner, a renamed_from match
            if stem in seen:
                continue
            kind, b = _m3_target(stem, r)
            (queue_stems if kind == "queue" else corpus_stems).add(stem)
            edges.append(Edge(a=key_, b=b, cosine=r.get("cosine"), relation=r.get("relation") or "unknown",
                              source="m3", readings={"ab": rd_of(r) | {"outcome": r.get("outcome")}},
                              via=r.get("via")))

    for key_ in sorted(plan.rows):              # the lexical blocks (plan 11): edges and flags, never a cut
        for e in lexical_edges(key_, plan.rows[key_], proposed_cut_off=proposed_cut_off):
            kind, _, stem = e.b.partition(":")
            (queue_stems if kind == "queue" else corpus_stems).add(stem)
            edges.append(e)

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
    proposed = proposed_groups(((e.a, e.b) for e in edges if e.proposed), cliques)
    g = Graph(batch_id=batch_id, from_batches=list(plan.batch_ids), config=dict(config or {}), nodes=nodes,
              edges=edges, cliques=cliques, clique_links=clique_links(cliques, edges), usage=dict(usage or {}),
              complete=not (stalled["relation"] or stalled["overlap"]),
              stalled={k: v for k, v in stalled.items() if v}, proposed_groups=proposed,
              proposed_links=clique_links(proposed, edges))
    g.sibling_groups = sibling_groups(g.candidate_keys(),
                                      structural_operator_table() if operator_table is None else operator_table)
    g.stats = summarize(g, plan=plan)
    return g


def _dist(c: Counter) -> dict:
    return {str(k): c[k] for k in sorted(c, key=lambda x: (str(type(x)), x))}


def summarize(g: Graph, *, plan: Optional[GraphPlan] = None) -> dict:
    """The counts the readout quotes: candidates, nodes, edges by relation and overlap state, the overlap pairs
    read, 4-edges, Sonnet and Opus on the 4s, cliques (merged groups) by size, singletons, opposed links, and the
    proposed groups (decision 12) with the candidates in no group of either tier (``ungrouped``)."""
    nodes = g.node_map()
    kept = g.candidate_keys()
    r1 = [e for e in g.edges if e.source == "r1"]
    m3 = [e for e in g.edges if e.source == "m3"]
    reads = [rd for e in r1 for rd in e.readings.values() if "stalled" not in rd]
    in_cliques = Counter(m for c in g.cliques for m in c)
    in_proposed = Counter(m for c in g.proposed_groups for m in c)
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
            "one_sided": sum(1 for e in r1 if len(e.relations) == 1),
            "by_via": _dist(Counter(e.via or "k_nearest" for e in r1)),
            "label_variants": sum(1 for e in r1 if e.label_variant and e.via != "relabel"),
            "relabel_pairs": sum(1 for e in r1 if e.via == "relabel")},
        "overlap": {
            "pairs_first_direction": sum(1 for e in r1 if "ab" in e.readings),
            "pairs_second_direction": sum(1 for e in r1 if "ba" in e.readings),
            "sonnet_readings": len(reads), "opus_readings": sum(1 for rd in reads if rd.get("opus") is not None),
            "four_first": sum(1 for e in r1 if (e.readings.get("ab") or {}).get("four")),
            "proposed_first": sum(1 for e in r1 if (e.readings.get("ab") or {}).get("proposed")),
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
        "proposed_groups": {"n": len(g.proposed_groups), "n_edges": sum(1 for e in r1 if e.proposed),
                            "by_size": _dist(Counter(len(c) for c in g.proposed_groups)),
                            "largest": max((len(c) for c in g.proposed_groups), default=0),
                            "candidates_in_proposed": len(in_proposed),
                            "candidates_in_proposed_only": sum(1 for m in in_proposed if m not in in_cliques),
                            "candidates_in_several": sum(1 for v in in_proposed.values() if v > 1),
                            "links": len(g.proposed_links)},
        "ungrouped": len(g.ungrouped()),
    }
    lex = lexical_counts(g.edges, (nodes[k].flags for k in kept))
    if lex["n_edges"] or lex["candidates_by_flag"]:     # only then, so a graph without lexical blocks is as before
        out["lexical"] = lex
    if plan is not None:
        out["skipped"] = dict(plan.skipped)
        out["no_vector"] = list(plan.no_vector)
        out["selected_by_batch"] = plan.by_batch
        out["plan_edges"] = plan.edge_counts()
    return out


# --------------------------------------------------------------------------- the estimate

@dataclass
class Shares:
    """Per cosine bin (lower edges ``bins``): the share of pairs the relation call sends to the overlap call
    (``similar`` or ``unsure``), the share whose Sonnet reading sends the pair to Opus at cut-off 4 (3, 4 or
    unsure), the share whose final reading is 4, and ``second``, the share whose final reading sends the second
    direction (the proposed cut-off or above; ``None``: the four share, as before decision 12); ``n_listed`` and
    ``n_read``: the observations behind them.  ``second_opus``: the share of second-direction Sonnet readings that
    go on to Opus (``None``: :data:`SECOND_OPUS_SHARE`); ``n_second``: its observations; ``source``: where the
    shares were measured (``m3_blocks``, or ``r1:<review batches>``)."""
    bins: tuple
    similar: tuple
    opus: tuple
    four: tuple
    n_listed: tuple
    n_read: tuple
    second: Optional[tuple] = None
    second_opus: Optional[float] = None
    n_second: Optional[int] = None
    source: Optional[str] = None

    def at(self, cosine: float) -> tuple[float, float, float]:
        """``(similar, opus, second)`` of the cosine's bin."""
        i = max([j for j, lo in enumerate(self.bins) if cosine >= lo] or [0])
        return self.similar[i], self.opus[i], (self.second if self.second is not None else self.four)[i]

    def second_opus_share(self) -> float:
        return SECOND_OPUS_SHARE if self.second_opus is None else self.second_opus

    def all_similar(self) -> "Shares":
        """The same shares with every pair sent to the overlap call (the pairs are known to be similar)."""
        return replace(self, similar=tuple(1.0 for _ in self.bins))

    def as_dict(self) -> dict:
        out = {"bins": list(self.bins), "similar": [round(x, 4) for x in self.similar],
               "opus": [round(x, 4) for x in self.opus], "four": [round(x, 4) for x in self.four],
               "n_listed": list(self.n_listed), "n_read": list(self.n_read)}
        if self.second is not None:
            out["second"] = [round(x, 4) for x in self.second]
        out["second_opus"] = round(self.second_opus_share(), 4)
        if self.n_second is not None:
            out["n_second"] = self.n_second
        if self.source is not None:
            out["source"] = self.source
        return out


def measured_shares(rows: Mapping[str, Mapping], batch_ids: Sequence[str], *, bins: Sequence[float] = SHARE_BINS,
                    min_obs: int = MIN_SHARE_OBS, second_at: Optional[int] = None) -> Shares:
    """:class:`Shares` from the M3 blocks of the batches' rows (every decision): the listed traits' final relations
    and the overlap readings, by cosine.  A bin with fewer than ``min_obs`` observations takes 1.0, so that the
    estimate errs high.  ``second_at``: the proposed cut-off, whose share (final reading at it or above) sends the
    second direction; ``None`` leaves ``second`` unset (the four share is used)."""
    bins = tuple(bins)
    nl, ns, nr, no, nf, n2 = ([0] * len(bins) for _ in range(6))

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
            fin = ov if ov is not None else sv
            nr[i] += 1
            no[i] += sv in (3, 4, "unsure")
            nf[i] += fin == 4
            n2[i] += second_at is not None and isinstance(fin, int) and fin >= second_at

    def share(k, n):
        return tuple((k[i] / n[i]) if n[i] >= min_obs else 1.0 for i in range(len(bins)))
    return Shares(bins=bins, similar=share(ns, nl), opus=share(no, nr), four=share(nf, nr), n_listed=tuple(nl),
                  n_read=tuple(nr), second=share(n2, nr) if second_at is not None else None, source="m3_blocks")


def r1_shares(graphs: Iterable["Graph"], *, bins: Sequence[float] = SHARE_BINS, min_obs: int = MIN_SHARE_OBS,
              second_at: int = DEFAULT_PROPOSED_CUT_OFF) -> Shares:
    """:class:`Shares` from earlier R1 builds' own records (their ``graph.json``; Roger, 2026-10-12, gate audit 8:
    M3's candidate-to-corpus shares put the TDA build's estimate at 3.2 times its spend).  Per cosine bin, over the
    builds' candidate edges: ``similar``, the share whose relation sends the pair to the overlap call; over their
    first-direction readings, ``opus`` (Sonnet 3, 4 or unsure: the rule at cut-off 4), ``four`` and ``second`` (the
    first direction at ``second_at`` or above, recomputed from the two values, so a build at another proposed
    cut-off still serves).  ``second_opus``: over the second-direction readings, the share Sonnet sent to Opus.  A
    bin with fewer than ``min_obs`` observations takes 1.0 (as :func:`measured_shares`), and so does ``second_opus``
    with fewer than ``min_obs``.  A stalled reading is not an observation."""
    bins = tuple(bins)
    nl, ns, nr, no, nf, n2 = ([0] * len(bins) for _ in range(6))
    s2 = o2 = 0
    names = []

    def b(c) -> Optional[int]:
        if c is None or c < bins[0]:
            return None
        return max(j for j, lo in enumerate(bins) if c >= lo)

    def raw(rd: Mapping) -> dict:
        return {"sonnet": {"value": rd.get("sonnet")},
                "opus": {"value": rd.get("opus")} if rd.get("opus") is not None else None}

    for g in graphs:
        names.append(g.batch_id)
        for e in g.edges:
            if e.source != "r1":
                continue
            i = b(e.cosine)
            if i is None:
                continue
            nl[i] += 1
            ns[i] += e.relation in OVERLAP_RELATIONS
            f = e.readings.get("ab")
            if f and "stalled" not in f and f.get("sonnet") is not None:
                nr[i] += 1
                no[i] += f.get("sonnet") in (3, 4, "unsure")
                rd = reading_of(raw(f), proposed_cut_off=second_at)
                nf[i] += bool(rd["four"])
                n2[i] += bool(rd["four"] or rd["proposed"])
            s = e.readings.get("ba")
            if s and "stalled" not in s and s.get("sonnet") is not None:
                s2 += 1
                o2 += s.get("sonnet") in (3, 4, "unsure")

    def share(k, n):
        return tuple((k[i] / n[i]) if n[i] >= min_obs else 1.0 for i in range(len(bins)))
    return Shares(bins=bins, similar=share(ns, nl), opus=share(no, nr), four=share(nf, nr), n_listed=tuple(nl),
                  n_read=tuple(nr), second=share(n2, nr), second_opus=(o2 / s2) if s2 >= min_obs else 1.0,
                  n_second=s2, source="r1:" + ",".join(names))


def r1_unsure(records: Iterable[Mapping]) -> Optional[tuple[float, float]]:
    """``(share of relation calls with an unsure re-ask, candidates per re-ask)`` over an R1 build's
    ``responses.jsonl`` (first attempts), or ``None`` when it has no relation call."""
    calls = reasks = stems = 0
    for r in records:
        if (r.get("parse_attempt") or 1) != 1:
            continue
        if r.get("step") == "relation":
            calls += 1
        elif r.get("step") == "relation_unsure":
            reasks += 1
            stems += len(r.get("stems") or [])
    if not calls:
        return None
    return reasks / calls, (stems / reasks if reasks else 1.0)


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
    on the similar share times the bin's second share (the proposed cut-off or above; Sonnet, then Opus on
    :meth:`Shares.second_opus_share` of it)."""
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
    est.add("overlap, second direction, Sonnet (where the first read at the proposed cut-off or above, by bin)",
            NR.FIRST_MODEL + suffix, int(round(s2)), *tok["sonnet"])
    so = shares.second_opus_share()
    est.add(f"overlap, second direction, Opus ({so:.0%} of the second-direction Sonnet readings)",
            NR.SECOND_MODEL + suffix, int(round(s2 * so)), *tok["opus"])
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


# --------------------------------------------------------------------------- the estimate of a resumed build

def estimate_wanted(wanted: Sequence[Mapping], *, plan: GraphPlan, runner: ReviewRunner, shares: Shares,
                    overlap_floor: float = DEFAULT_OVERLAP_FLOOR,
                    overlap_tokens: Optional[Mapping[str, tuple[int, int]]] = None, transport: str = "live",
                    unsure: Optional[tuple[float, float]] = None) -> Estimate:
    """The estimate of the calls a resumed build sends: ``wanted`` (``OfflineTransport.wanted`` of a replay on the
    records: the calls not on record that the records lead to, each with its ``call``) priced as rendered, and the
    calls those lead to by the shares of their cosine bin: Opus after a first-direction Sonnet call, the second
    direction after a first-direction call, Opus after a second-direction Sonnet call
    (:data:`SECOND_OPUS_SHARE`), and, for a candidate whose relation call is not on record, the unsure re-ask and
    the overlap stage of its edges that no recorded or wanted overlap call covers (:func:`estimate_overlap`)."""
    est = Estimate()
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    tok = dict(NR.OVERLAP_TOKENS) | dict(overlap_tokens or {})

    def cos(w: Mapping) -> float:
        return plan.edges.get(tuple(sorted((w["key"], w["stem"]))), overlap_floor)

    by: dict[tuple, list] = defaultdict(list)
    for w in wanted:
        if w["step"] == "overlap":
            by[("ov2" if str(w["wave"]).startswith(SECOND_WAVE) else "ov1", w["role"])].append(w)
        else:
            by[(w["step"], None)].append(w)
    rel = by[("relation", None)]
    if rel:
        calls = [w["call"] for w in rel]
        toks = [NR.call_tokens(c) for c in calls]
        n_listed = sum(len(c.stems) for c in calls) / len(calls)
        est.add(f"relation call, not on record ({n_listed:.1f} listed candidates a call)", calls[0].model + suffix,
                len(calls), int(round(sum(t[0] for t in toks) / len(toks))),
                int(round(sum(t[1] for t in toks) / len(toks))))
        share, per = unsure if unsure is not None else NR.unsure_for(calls[0].model)
        sf = OT.tokenizer_factor(NR.UNSURE_MODEL)
        cc = 140.0
        est.add(f"unsure re-ask after them ({share:.0%} of those relation calls)", NR.UNSURE_MODEL + suffix,
                int(round(share * len(calls))),
                int(round((len(calls[0].system) + cc + per * cc) / NR.CHARS_PER_TOKEN * sf)),
                int(round((NR.RELATION_OUT_BASE + NR.RELATION_OUT_PER_TRAIT * per) * sf)))
    uns = by[("relation_unsure", None)]
    if uns:
        toks = [NR.call_tokens(w["call"]) for w in uns]
        est.add("unsure re-ask, not on record", uns[0]["call"].model + suffix, len(uns),
                int(round(sum(t[0] for t in toks) / len(toks))), int(round(sum(t[1] for t in toks) / len(toks))))
    s1, o1, s2, o2 = by[("ov1", "sonnet")], by[("ov1", "opus")], by[("ov2", "sonnet")], by[("ov2", "opus")]
    est.add("overlap, first direction, Sonnet, not on record", NR.FIRST_MODEL + suffix, len(s1), *tok["sonnet"])
    est.add("overlap, first direction, Opus, not on record", NR.SECOND_MODEL + suffix, len(o1), *tok["opus"])
    est.add("overlap, first direction, Opus, after the Sonnet calls not on record (by bin)", NR.SECOND_MODEL + suffix,
            int(round(sum(shares.at(cos(w))[1] for w in s1))), *tok["opus"])
    after = sum(shares.at(cos(w))[2] for w in s1 + o1)
    est.add("overlap, second direction, Sonnet, not on record", NR.FIRST_MODEL + suffix, len(s2), *tok["sonnet"])
    est.add("overlap, second direction, Opus, not on record", NR.SECOND_MODEL + suffix, len(o2), *tok["opus"])
    est.add("overlap, second direction, Sonnet, after the first-direction calls not on record (by bin)",
            NR.FIRST_MODEL + suffix, int(round(after)), *tok["sonnet"])
    so = shares.second_opus_share()
    est.add(f"overlap, second direction, Opus, after the second-direction Sonnet calls ({so:.0%})",
            NR.SECOND_MODEL + suffix, int(round((len(s2) + after) * so)), *tok["opus"])
    if rel:
        open_keys = {w["key"] for w in rel}
        covered = {tuple(sorted((w["key"], w["stem"]))) for w in s1 + o1 + s2 + o2}
        rest = []
        for (a, b), c in plan.edges.items():
            if (a in open_keys or b in open_keys) and (a, b) not in covered and c >= overlap_floor \
                    and not runner.on_record(runner.overlap_call(a, b, "sonnet", 1)):
                rest.append(c)
        if rest:
            sub = estimate_overlap(rest, shares, overlap_floor=overlap_floor, overlap_tokens=overlap_tokens,
                                   transport=transport)
            for x in sub.lines:
                est.add(x.label.replace("overlap, ", "overlap of the candidates whose relation call is not on "
                                                      "record, ", 1), x.model, x.n_calls, x.in_tok, x.out_tok)
    return est


def resume_estimate(plan: GraphPlan, *, runner: ReviewRunner, corpus: Mapping[str, Any], queue: Optional[Mapping] = None,
                    shares: Shares, overlap_floor: float = DEFAULT_OVERLAP_FLOOR,
                    proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF,
                    overlap_tokens: Optional[Mapping[str, tuple[int, int]]] = None, transport: str = "live",
                    unsure: Optional[tuple[float, float]] = None) -> tuple[Estimate, Graph, list[dict]]:
    """What a ``--resume`` would send, found without sending anything: the build replayed on ``runner``'s resume
    records through :class:`novelty_runner.OfflineTransport` (a call not on record is noted and left unanswered),
    then :func:`estimate_wanted`.  ``(estimate, the replayed graph, the wanted calls without their Call objects)``;
    the replayed graph shows what the records alone give (the pairs left unanswered are its ``stalled``).
    ``runner`` (``client=None`` is fine) gets the offline transport and must not be used to send afterwards."""
    runner.transport = NR.OfflineTransport()
    g = build_graph(plan, runner=runner, corpus=corpus, queue=queue, overlap_floor=overlap_floor,
                    proposed_cut_off=proposed_cut_off)
    wanted = list(runner.transport.wanted)
    est = estimate_wanted(wanted, plan=plan, runner=runner, shares=shares, overlap_floor=overlap_floor,
                          overlap_tokens=overlap_tokens, transport=transport, unsure=unsure)
    return est, g, [{k: v for k, v in w.items() if k != "call"} for w in wanted]


# --------------------------------------------------------------------------- the Opus pilot (gate audit 8, P2)

def bin_label(cosine: Optional[float], bins: Sequence[float] = PILOT_BINS) -> str:
    """``0.35-0.45``, ..., ``0.65+``; ``<0.35`` below the first bin."""
    if cosine is None:
        return "none"
    if cosine < bins[0]:
        return f"<{bins[0]:g}"
    i = max(j for j, lo in enumerate(bins) if cosine >= lo)
    return f"{bins[i]:g}+" if i == len(bins) - 1 else f"{bins[i]:g}-{bins[i + 1]:g}"


def sonnet2_pairs(graph: Graph, *, value: int = 2) -> list[dict]:
    """The candidate edges whose first direction Sonnet read ``value`` (2) and Opus did not read (the rule at
    cut-off 4 never sends a 2 to Opus, so at the proposed cut-off 3 a Sonnet 2 is final): ``{"a", "b", "cosine",
    "relation"}``, ``a`` the first direction's target, sorted by key."""
    out = []
    for e in graph.edges:
        f = e.readings.get("ab") if e.source == "r1" else None
        if not f or "stalled" in f or f.get("sonnet") != value or isinstance(f.get("sonnet"), bool) \
                or f.get("opus") is not None:
            continue
        out.append({"a": e.a, "b": e.b, "cosine": e.cosine, "relation": e.relation})
    return sorted(out, key=lambda p: (p["a"], p["b"]))


def resolution_labels(groups: Iterable[Mapping], *, stem_of: Mapping[str, Optional[str]]) -> dict[str, str]:
    """Each term a review log settled, labelled by the resolution it ended in (the pilot's reference; gate audit 8,
    section 4a).  ``groups``: the log's resolved groups, ``{"id", "resolution", "nominated", "resolved_members"}``
    (the review app's ``ReviewState.groups`` once replayed; an extended term is among the resolved members).
    ``merge_into:<target>`` -> the target; ``promote`` -> ``queue:<the nominee's stem>``, so that a group merged
    into that entry is the same resolution; ``reject`` -> the group; ``park`` and ``defer`` settle nothing and are
    left out.  Two terms with one label are a *same-resolution* pair, else *different*."""
    out: dict[str, str] = {}
    for g in groups:
        kind, _, target = str(g.get("resolution") or "").partition(":")
        if kind not in SETTLED_RESOLUTIONS:
            continue
        if kind == "merge_into":
            lab = target
        elif kind == "promote":
            stem = stem_of.get(g.get("nominated"))
            lab = f"queue:{stem}" if stem else f"promote:{g.get('id')}"
        else:
            lab = f"reject:{g.get('id')}"
        for m in g.get("resolved_members") or []:
            out[m] = lab
    return out


def _stratified(items: Sequence[Mapping], m: int, rng: random.Random, bins: Sequence[float]) -> list:
    """``m`` of ``items`` (all of them when ``m`` is not smaller), allotted to the cosine bins in proportion to
    their sizes (largest remainder, ties by bin label), drawn at random within each bin."""
    if m >= len(items):
        return list(items)
    by: dict[str, list] = defaultdict(list)
    for p in items:
        by[bin_label(p["cosine"], bins)].append(p)
    names = sorted(by)
    quota = {k: m * len(by[k]) / len(items) for k in names}
    take = {k: int(quota[k]) for k in names}
    for k in sorted(names, key=lambda k: (-(quota[k] - take[k]), k))[:m - sum(take.values())]:
        take[k] += 1
    out: list = []
    for k in names:
        out.extend(rng.sample(by[k], take[k]))
    return out


def select_pilot(pairs: Sequence[Mapping], labels: Mapping[str, str], n: int = PILOT_SIZE, *, seed: int = PILOT_SEED,
                 bins: Sequence[float] = PILOT_BINS) -> dict:
    """The Opus pilot's pairs (gate audit 8, P2: "Opus on all 64 same-resolution 2/- pairs and 64 of the 133
    different-resolution 2/- pairs (stratified by cosine)").  Of ``pairs`` (:func:`sonnet2_pairs`), those whose two
    terms ``labels`` (:func:`resolution_labels`) settles, split into *same* and *different*; half of ``n`` from
    each, a pool with fewer giving its share to the other; each drawn stratified by cosine bin
    (:func:`_stratified`; a pool that fits is taken whole), ``random.Random(seed)``, the same pool first.
    ``{"selected": [pair + {"reference"}], "pools": {"same", "different", "unlabelled", "by_bin"}, "n", "seed"}``."""
    same = [dict(p) for p in pairs if p["a"] in labels and p["b"] in labels and labels[p["a"]] == labels[p["b"]]]
    diff = [dict(p) for p in pairs if p["a"] in labels and p["b"] in labels and labels[p["a"]] != labels[p["b"]]]
    n = max(0, int(n))
    n_same = min(len(same), max(n // 2, n - len(diff)))
    n_diff = min(len(diff), n - n_same)
    rng = random.Random(seed)
    sel = [p | {"reference": "same"} for p in _stratified(same, n_same, rng, bins)] + \
        [p | {"reference": "different"} for p in _stratified(diff, n_diff, rng, bins)]
    by_bin: dict[str, dict] = defaultdict(lambda: {"same": 0, "different": 0})
    for ref, pool in (("same", same), ("different", diff)):
        for p in pool:
            by_bin[bin_label(p["cosine"], bins)][ref] += 1
    return {"selected": sorted(sel, key=lambda p: (p["a"], p["b"])), "n": n, "seed": seed,
            "pools": {"same": len(same), "different": len(diff), "unlabelled": len(pairs) - len(same) - len(diff),
                      "by_bin": {k: dict(v) for k, v in sorted(by_bin.items())}}}


def node_candidate(n: Node) -> PairCandidate:
    """A graph node as the overlap call reads it: its label and gloss as the build recorded them."""
    return PairCandidate(key=n.key, stem=n.stem or n.key.split("#", 1)[0], label=n.label, gloss=n.gloss or "",
                         alignment_score=n.alignment_score, region=n.region, generators=list(n.generators))


def pilot_prompt_mismatches(runner: ReviewRunner, pairs: Sequence[tuple[str, str]],
                            recorded: Mapping[tuple[str, str], str]) -> list[dict]:
    """The pairs whose overlap prompt, rendered now, is not the one Sonnet read in the build (``recorded``: ``(key,
    stem) -> user`` of the build's first-direction Sonnet records): Opus must read what Sonnet read.  The candidates
    must be added to ``runner``."""
    out = []
    for a, b in pairs:
        rec = recorded.get((a, b))
        if rec is None:
            out.append({"a": a, "b": b, "why": "no Sonnet record of this direction in the build"})
        elif runner.overlap_call(a, b, "sonnet", 1).user != rec:
            out.append({"a": a, "b": b, "why": "the prompt rendered now differs from the one Sonnet read"})
    return out


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> Optional[list[float]]:
    """The exact binomial interval of ``k`` in ``n`` (``None`` for ``n == 0``)."""
    if n <= 0:
        return None
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [round(lo, 4), round(hi, 4)]


def _raised(opus_value: Any, *, proposed_cut_off: int = DEFAULT_PROPOSED_CUT_OFF) -> bool:
    """Whether a Sonnet 2 with this Opus reading would be at the proposed cut-off (M3's rule at cut-off 3: Opus at 3
    or above on a Sonnet one below covers, under rule set 2)."""
    return bool(reading_of({"sonnet": {"value": 2}, "opus": {"value": opus_value}},
                           proposed_cut_off=proposed_cut_off)["proposed"])


def pilot_report(rows: Sequence[Mapping], *, pools: Mapping, graph: Optional[Graph] = None,
                 labels: Optional[Mapping[str, str]] = None, bins: Sequence[float] = PILOT_BINS) -> dict:
    """The pilot against Roger's decisions.  ``rows``: the selected pairs with ``reference`` and the Opus answer
    (``opus``: ``{"value", ...}``, or ``stalled``).  Per reference (same, different): the pairs, those Opus answered,
    its values, and those it **raised** (Opus 3 or above on Sonnet's 2: the first direction then at the proposed
    cut-off), with a 95% Clopper-Pearson interval; the same by cosine bin; the gap and a one-sided Fisher exact test
    (same raised more often); scaled to the pools (``pools``: :func:`select_pilot`'s), the joins the change would
    add and how many of them Roger's decisions support.  With ``graph`` and ``labels``: the same agreement for the
    build's existing edges between settled terms, the yardstick (3-edges that are not 4-edges, and 4-edges)."""
    out: dict[str, Any] = {"n": len(rows), "by_reference": {}, "by_bin": {}}
    tallies: dict[str, Counter] = {"same": Counter(), "different": Counter()}
    by_bin: dict[str, dict] = defaultdict(lambda: {"same": Counter(), "different": Counter()})
    for r in rows:
        ref = r["reference"]
        t, tb = tallies[ref], by_bin[bin_label(r.get("cosine"), bins)][ref]
        for c in (t, tb):
            c["n"] += 1
        o = r.get("opus") or {}
        if "stalled" in r or o.get("value") is None:
            t["no_answer"] += 1
            continue
        v = o["value"]
        t[f"opus {v}"] += 1
        for c in (t, tb):
            c["answered"] += 1
            c["raised"] += _raised(v)
        t["four"] += v == 4
    for ref, t in tallies.items():
        out["by_reference"][ref] = {
            "n": t["n"], "answered": t["answered"], "no_answer": t["no_answer"], "raised": t["raised"],
            "four": t["four"], "raised_share": round(t["raised"] / t["answered"], 4) if t["answered"] else None,
            "ci95": clopper_pearson(t["raised"], t["answered"]),
            "opus_values": {k.split(" ", 1)[1]: v for k, v in sorted(t.items()) if k.startswith("opus ")}}
    out["by_bin"] = {k: {ref: {"n": c["n"], "answered": c["answered"], "raised": c["raised"]} for ref, c in v.items()}
                     for k, v in sorted(by_bin.items())}
    s, d = tallies["same"], tallies["different"]
    if s["answered"] and d["answered"]:
        from scipy.stats import fisher_exact
        ps, pd = s["raised"] / s["answered"], d["raised"] / d["answered"]
        out["gap"] = round(ps - pd, 4)
        out["fisher_p_one_sided"] = float(fisher_exact(
            [[s["raised"], s["answered"] - s["raised"]], [d["raised"], d["answered"] - d["raised"]]],
            alternative="greater")[1])
        es, ed = ps * pools.get("same", 0), pd * pools.get("different", 0)
        out["scaled_to_pools"] = {
            "same_pool": pools.get("same", 0), "different_pool": pools.get("different", 0),
            "same_raised": round(es, 1), "different_raised": round(ed, 1),
            "share_of_raised_that_roger_joined": round(es / (es + ed), 4) if es + ed else None}
    if graph is not None and labels is not None:
        base: dict[str, Counter] = {"three_only": Counter(), "four": Counter()}
        for e in graph.edges:
            if e.source != "r1" or not e.proposed or e.label_variant or e.a not in labels or e.b not in labels:
                continue
            c = base["four" if e.strict else "three_only"]
            c["n"] += 1
            c["same"] += labels[e.a] == labels[e.b]
        out["yardstick"] = {k: {"n": c["n"], "same": c["same"],
                                "same_share": round(c["same"] / c["n"], 4) if c["n"] else None,
                                "ci95": clopper_pearson(c["same"], c["n"])} for k, c in base.items()}
    return out


def format_pilot_report(rep: Mapping) -> str:
    """The pilot's report as the CLI prints it."""
    lines = [f"Opus pilot: {rep['n']} first directions Sonnet read 2"]
    for ref in ("same", "different"):
        r = rep["by_reference"].get(ref)
        if not r:
            continue
        share = "n/a" if r["raised_share"] is None else f"{r['raised_share']:.0%}"
        ci = "" if not r["ci95"] else f" (95% {r['ci95'][0]:.0%}-{r['ci95'][1]:.0%})"
        lines.append(f"  {ref:9s} resolution: {r['raised']} of {r['answered']} answered raised to 3+ = {share}{ci}; "
                     f"Opus values {json.dumps(r['opus_values'], sort_keys=True)}; no answer {r['no_answer']}")
    for k, v in rep.get("by_bin", {}).items():
        lines.append(f"    cosine {k:9s} " + "; ".join(f"{ref} {c['raised']}/{c['answered']}" for ref, c in v.items()))
    if "gap" in rep:
        sp = rep["scaled_to_pools"]
        share = sp["share_of_raised_that_roger_joined"]
        lines.append(f"  gap (same - different) {rep['gap']:+.0%}; one-sided Fisher exact p = "
                     f"{rep['fisher_p_one_sided']:.2g}")
        lines.append(f"  scaled to the pools ({sp['same_pool']} same, {sp['different_pool']} different): about "
                     f"{sp['same_raised']:g} first directions raised on pairs Roger joined and "
                     f"{sp['different_raised']:g} on pairs he did not; {'n/a' if share is None else f'{share:.0%}'} "
                     f"of the raised are his (each still needs its second direction at 3 or above to be a 3-edge)")
    names = {"three_only": "3-edges that are not 4-edges", "four": "4-edges"}
    for k, v in (rep.get("yardstick") or {}).items():
        if v["n"]:
            lines.append(f"  yardstick, the build's {names.get(k, k)} between settled terms: {v['same']} of {v['n']} "
                         f"in one resolution = {v['same_share']:.0%}")
    return "\n".join(lines)
