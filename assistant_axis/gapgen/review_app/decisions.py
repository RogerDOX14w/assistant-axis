"""The review app's decision log, its replay, the views the page shows, and ``apply``.

Brief: ``reports/trait_gap_generation/coding_plan_review.md``, section 1 (decisions 4-9 and 12) and section 3.  The
graph is R1's ``graph.json`` (:mod:`assistant_axis.gapgen.review_graph`): kept candidates (the review's **terms**),
covered candidates (greyed, decision 9), corpus and queue traits (resolution targets, decision 5), the candidate
edges and the corpus edges, the **merged groups** (``cliques``: 4-edges both ways) and the **proposed groups**
(``proposed_groups``: 3-edges both ways, decision 12).

**The log** (``decisions.jsonl`` beside ``graph.json``): one event per line, append-only, never rewritten::

    {"seq": 41, "at": "2026-10-09T09:12:03+00:00", "by": "roger", "group": "g17", "action": "resolve",
     "members": ["godless#1", "irreligious#1"], "nominated": "irreligious#1", "resolution": "promote", "note": null,
     "graph_sha256": "..."}

Actions (a request names the action and its fields; the log stores the request as normalised here):

* ``open`` (``source``): ``merged:<i>`` (opens already merged), ``proposed:<i>`` (opens pre-assembled but not merged:
  status ``proposed``), or ``term:<key>`` (the term's open working group if it has one; else its merged group, the
  largest if several; else its largest proposed group; else the term alone).  Opening what is already open (or a
  handled term) returns that group and logs nothing; a term another review batch settled (below) is refused, with
  that batch's group and resolution.
* ``accept`` (``group``): a proposed group becomes the working group (key ``g``); drops before it are kept.
* ``drop`` (``group``, ``key``): never the last member.
* ``merge_in`` (``group``, ``keys``): a singleton or a merged group's members; a covered candidate may be pulled in by
  hand (decision 9); handled terms and members already in are left out, and the event records what was added.
* ``nominate`` (``group``, ``key``): the suggested label; not a covered or handled member.
* ``resolve`` (``group``, ``resolution``, ``note``?, ``rename``?): ``promote`` (the nominee; a group with one
  unhandled term nominates it by default), ``merge_into:<trait:stem | queue:stem>``, ``park``, ``reject``,
  ``defer``.  Only an open (accepted) group resolves.  The event records the members it resolves: those not already
  handled.  ``rename``: the label this decision settles on reads awkwardly and wants a second look (QUESTIONS 71,
  Roger 2026-10-11, the human net beside instruction generation's label-blind call); the ``note`` carries the
  freeform reason.  The flag rides on the **decision**, never on the trait file: the registry is a history, so a
  flag there never needs cleaning up, while a trait-file tag carries provenance and class and would leak into any
  analysis grouping by tag.
* ``start_antonym`` (``of``, ``keys``): a new open group meant as the antonym of a resolved group that has none.
* ``extend`` (``group``, ``keys``): a **resolved** group takes more members under the same resolution -- "also
  covered" -- without being reopened: they join ``resolved_members`` and are handled by it, and apply writes them
  like the rest (a promoted group's extras merge into its nominee).  The leftovers pass (below) is where this is
  used; it takes any unhandled candidate.
* ``distinct`` (``group``, ``keys``): "considered against this resolved group, and not it".  Informational: the
  candidates stay unhandled, wear a badge, and leave that group's leftovers list; their own group comes up in the
  queue as before.
* ``split_off`` (``group``, ``keys``, ``target``, ``note``?): the leftovers pass's third answer (Roger, 2026-10-20: a
  simplex whose members are half covered by corpus trait X and half by Y took two passes): the given unhandled
  candidates, leftovers of the **resolved** group ``group``, are covered by ``target`` (a ``trait:`` or ``queue:``
  key among the merge targets), in one decision.  The event creates a new group, resolved at once (its own id, the
  event's ``group``; ``source`` ``split:<group>``; ``split_from`` the resolved group; resolution
  ``merge_into:<target>``; ``resolved_members`` the keys), which handles the keys; apply writes them ``merged_into``
  the target like any merge.  Validated as ``extend`` is (candidates of this graph, none handled, not members of the
  group) and the target must be a known one.  One undo takes the whole split back.
* ``undo`` (``seq``?): reverses the last effective **decision** (a ``split_off`` as one), skipping opens (Roger, 2026-10-11: an undo after
  opening two more groups undid an open, which is navigation, and left the resolve he meant standing); when only
  opens remain, the last open.  The event records what it undid.  Undo again to walk back.

**The leftovers pass** (Roger, 2026-10-11: overlapping cliques are one would-be simplex shattered by a missing
link, so a resolution leaves the other cliques' members needing the same decision one by one).  A resolved group's
card carries ``leftovers``: every unhandled candidate that shares a merged or proposed group with any of its
members and is not marked distinct from it, strongest tie first (4-edges to the group's members, then the best edge
level), each with the groups it comes from.  ``extend`` and ``distinct`` are its two answers.

**Replay**: the state is the log replayed from the start, the undone events and the undo events left out; an event
the graph no longer supports (a rebuilt graph) is skipped and listed in ``ReviewState.skipped``.  A term is
**handled** once a group containing it is resolved; a term in two groups is handled by the first resolution and
shown so in the other.

**Handled before this batch** (Roger, 2026-10-11; section 11 of the brief): a term that another review batch
settled, by the registry's ``review`` block (``accepted``, ``rejected`` or ``merged_into``; the folded row when the
app has the registry, being the later record, else the block R1 copied onto the node), is handled from the start, by
a pseudo group id that names that batch and group (``review_tda_1/g12``), never a group of this log.  It counts as
handled in the queue and the counts, stays out of a group's basis and leftovers, cannot be opened, merged in or
nominated, and shows its earlier resolution (``accepted → queue:irreligious``); the seed-queue entry it was
promoted to, or what it was merged into, is listed among the targets of a group it neighbours, so "Covered by
this" merges a new word into a word already decided.  ``parked`` and ``deferred`` there stay live here (they mean
"come back to it") and only wear a badge.  A block this batch's own ``apply`` wrote is not an earlier review.  The
replay does not see these: an event of the log that handles such a term applies as before and takes it over, and
undo walks only the log.

**Apply** (:func:`apply_decisions`): every resolved group into the registry's ``review`` blocks (through
:meth:`Registry.update_many`), and each promoted nominee through :func:`assistant_axis.gapgen.promote.promote` (the
path ``gap_registry.py promote`` uses), its seed-queue entry carrying ``also_proposed`` (the other members'
labels).  Idempotent; ``dry_run`` writes nothing.  :func:`review_merges` gives ``gap_registry.py synonyms`` the
review's merges into a corpus trait or queue entry.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import os
import re
import statistics
import threading
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen import promote as promote_mod
from assistant_axis.gapgen import records as RF
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.registry import Registry, utc_now

logger = logging.getLogger(__name__)

LOG_NAME = "decisions.jsonl"
APPLIED_NAME = "applied.jsonl"
GRAPH_NAME = "graph.json"
ACTIONS = ("open", "accept", "drop", "merge_in", "nominate", "resolve", "start_antonym", "extend", "distinct",
           "split_off", "undo")
RESOLUTIONS = ("promote", "merge_into", "park", "reject", "defer")
#: The registry ``review.status`` each resolution writes (``merged_into`` and ``parked`` are new to the platform
#: plan's vocabulary; the plan's ``merged`` is written as ``merged_into`` with ``into``, as section 3 says).
REVIEW_STATUS = {"promote": "accepted", "merge_into": "merged_into", "park": "parked", "reject": "rejected",
                 "defer": "deferred"}
UNREVIEWED = {"status": "unreviewed", "by": None, "at": None, "note": None}
#: The registry review statuses that settle a term: another batch's term in one is handled here from the start.
HANDLED_ELSEWHERE = ("accepted", "rejected", "merged_into")
ORDERS = ("cliques", "generator", "region", "sample")
#: The ``sample`` order (Roger, 2026-10-16: "have a good sample order"): a seeded random order without replacement
#: (weighted by stratum when the weights differ), so that the first N items a session reaches are a probability
#: sample of the queue.  An item's stratum is its strongest member's best M3 overlap reading against any corpus or
#: queue trait, by either model (Sonnet or Opus).  The weights are equal, so it is a plain random sample: the design
#: first doubled the reading-3 stratum (on the first 177 reviewed "new" rows a 3 was nearly decisive, 45 of 46
#: merged), but in review_traits_all_2 that stratum is already 28% of the items and about 40% of the terms (a group
#: takes its strongest member's reading), so it needs no oversampling.  The order depends only on the seed and the
#: item ids, never on what is handled, so it is stable through a session; :func:`sample_inclusion` gives each
#: stratum's inclusion probability for the number of items reached.  Archive of the design:
#: ``reports/trait_gap_generation/m3_false_new_brainstorm.md``.
SAMPLE_SEED = "2026-10-16"
SAMPLE_WEIGHTS = {"read_3": 1.0, "read_2": 1.0, "other": 1.0}
TIERS = ("merged", "proposed", "single")
#: Gaps between events longer than this are idle time (``status``'s active minutes).
IDLE_MINUTES = 10.0
_GID = re.compile(r"^g(\d+)$")
#: Within a level, a neighbour's relation orders it: similar (or mixed) before unsure before unrelated.
REL_RANK = {"similar": 2, "mixed": 2, "unsure": 1}
_TURNED_DOWN = ("not_adopted", "superseded")


class ActionError(ValueError):
    """A refused action (the app answers 409 with this message); nothing is logged."""


# --------------------------------------------------------------------------- small helpers

def _final(rd: Optional[Mapping]) -> Optional[int]:
    """A direction's final reading: Opus's where Opus read, else Sonnet's (an int, or None)."""
    if not rd or "stalled" in rd:
        return None
    v = rd.get("opus") if rd.get("opus") is not None else rd.get("sonnet")
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _dir_text(rd: Optional[Mapping]) -> Optional[str]:
    if not rd:
        return None
    if "stalled" in rd:
        return "stalled"
    return f"{rd.get('sonnet')}/{rd.get('opus') if rd.get('opus') is not None else '-'}"


def readings_text(e: RG.Edge) -> str:
    """``"3/3, 2/-"``: Sonnet/Opus one way, then the other ("-": Opus did not read)."""
    return ", ".join(t for t in (_dir_text(e.readings.get("ab")), _dir_text(e.readings.get("ba"))) if t)


def lexical_info(e: RG.Edge) -> dict:
    """A lexical edge's lexicon (named as the card names it), link type, word, ``at_cut_off`` (a proposed merge) and
    ``name_only`` (``{}`` for any other edge)."""
    if e.source != "lexical":
        return {}
    x = e.lexical or {}
    return {"lexicon": x.get("lexicon"), "lexicon_name": RG.LEXICON_NAMES.get(x.get("lexicon"), x.get("lexicon")),
            "link": x.get("link"), "word": x.get("word"), "at_cut_off": bool(x.get("at_cut_off")),
            "name_only": bool(x.get("name_only"))}


def edge_level(e: RG.Edge) -> int:
    """How strongly an edge ties its ends: 4 for a 4-edge, 3 for a 3-edge, else the best final reading (0 unread)."""
    if e.strict:
        return 4
    if e.proposed:
        return 3
    vals = [v for v in (_final(e.readings.get("ab")), _final(e.readings.get("ba"))) if v is not None]
    return max(vals) if vals else 0


def best_m3_reading(edges: Iterable[RG.Edge]) -> int:
    """The highest M3 overlap reading (Sonnet's or Opus's, either direction recorded) on a candidate's non-opposed
    corpus or queue edges; -1 when nothing was read."""
    best = -1
    for e in edges:
        if e.relation == "opposed":
            continue
        for rd in e.readings.values():
            if not rd or "stalled" in rd:
                continue
            for v in (rd.get("sonnet"), rd.get("opus")):
                if isinstance(v, int) and not isinstance(v, bool):
                    best = max(best, v)
    return best


def sample_stratum(best: int) -> str:
    return "read_3" if best >= 3 else ("read_2" if best == 2 else "other")


def sample_key(item_id: str, weight: float, seed: str = SAMPLE_SEED) -> float:
    """The Efraimidis-Spirakis key ``-ln(u) / weight`` (smallest first), ``u`` uniform on (0, 1) from a hash of the
    seed and the item id: sorting by it draws a weighted sample without replacement, deterministically."""
    h = int.from_bytes(hashlib.sha256(f"{seed}|{item_id}".encode()).digest()[:8], "big")
    u = (h + 0.5) / 2 ** 64
    return -math.log(u) / weight


def sample_inclusion(stratum_sizes: Mapping[str, int], n: int, *, weights: Mapping[str, float] = SAMPLE_WEIGHTS,
                     sims: int = 2000, rng_seed: int = 0) -> dict[str, float]:
    """The probability that an item of each stratum is among the first ``n`` items of the sample order, by
    simulation (the same for every item of a stratum).  ``stratum_sizes``: items per stratum in the queue."""
    import random
    rng = random.Random(rng_seed)
    strata = [s for s, k in stratum_sizes.items() for _ in range(k)]
    n = max(0, min(n, len(strata)))
    hits: Counter = Counter()
    for _ in range(sims):
        keys = sorted((-math.log(1.0 - rng.random()) / weights[s], s) for s in strata)
        hits.update(s for _, s in keys[:n])
    return {s: hits[s] / (sims * k) if k else 0.0 for s, k in stratum_sizes.items()}


def _mode(values: Iterable[Optional[str]]) -> Optional[str]:
    c = Counter(v for v in values if v)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if c else None


def _parse_at(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def relabel_card(row) -> Optional[dict]:
    """The member card's relabel line (noun normalization plan; Roger, decision 2 (c), 2026-10-14): ``{"from": noun,
    "to": adjective, "route": text}`` from the row's ``relabel`` block (``route``: :func:`nouns.route_text`, e.g.
    "suffix rule +y from 'slipper', sense not checked"), or None for a row without one."""
    from assistant_axis.gapgen.nouns import route_text
    b = (row or {}).get("relabel") or {}
    if not b:
        return None
    src = b.get("from_surface") or (str(b["from_key"]).split("#")[0] if b.get("from_key") else None)
    to = b.get("to_corpus_stem") or (str(b["to_key"]).split("#")[0] if b.get("to_key") else None)
    return {"from": src, "to": to, "route": route_text(b)}


#: The member-card fields that carry a duplicate signal other than M3's own decision: hidden in a blind session
#: (``serve --blind``, :func:`blind_card`), so that Roger's decisions there are a clean test of the signals.
#: ``narrow``: the narrow pass's "narrower than X" (2026-10-20, :func:`narrow_card`).
SIGNAL_FIELDS = ("persona", "lexical_merges", "narrow")
SIGNAL_FLAGS = ("lexical_proposed_merge",)


def persona_card(row, label=None) -> Optional[dict]:
    """The member card's persona-space badge (plan 12; Roger, 2026-10-15: all three kinds, the duplicate flag
    prominent, the cover kinds quiet), from the row's ``persona`` block, or None.

    * ``duplicate`` (the row's flag is ``duplicate_like``, prominent): "persona space: close to X (0.77); overlap
      reading 3/3" -- the nearest corpus entity and, when M3 read it, M3's reading of it.
    * ``cover_questioned`` (quiet): M3 covered the row, and persona space puts it far from the covering trait.
    * ``novel`` (``novel_vs_covered``, quiet): M3 covered the row, and persona space finds it unlike the corpus.

    ``label`` maps a corpus key (``trait:stem``) to its display label."""
    pb = (row or {}).get("persona") or {}
    if not pb:
        return None
    nn = pb.get("nn") or {}
    nid = str(nn.get("id") or "")
    stem, _, kind = nid.partition("|")
    near = None
    if stem:
        key = f"trait:{stem}" if kind == "T" else f"role:{stem}"
        path, href = target_path(key)
        near = {"key": key, "label": (label(key) if label and kind == "T" else stem.replace("_", " ")), "path": path,
                "href": href, "cosine": nn.get("cos")}
    rd = pb.get("reading") or {}
    reading = f"{rd.get('sonnet')}/{rd.get('opus') if rd.get('opus') is not None else '-'}" if rd else None
    dis = pb.get("disagreement")
    if pb.get("flag") == "duplicate_like":
        return {"kind": "duplicate", "near": near, "reading": reading, "reading_of": rd.get("stem"),
                "disagreement": dis, "prominent": True}
    if dis == "cover_questioned":
        return {"kind": "cover_questioned", "near": near, "cos_to_cover": pb.get("cos_to_covered_by"),
                "covered_by": pb.get("m3_covered_by"), "prominent": False}
    if dis == "novel_vs_covered":
        return {"kind": "novel", "near": near, "residual_pct": pb.get("residual_pct"), "prominent": False}
    return None


def narrow_card(row, label=None) -> Optional[dict]:
    """The member card's narrow-pass badge (QUESTIONS 208 (3), Roger 2026-10-20: at most one narrow trait per parent
    goes to review), from the row's ``narrow`` block, or None: ``{"status": "kept" | "held", "parent": {"key",
    "label", "path", "href", "kind"}, "reading": M3's reading of the parent ("3/2"), "votes": the direction call's answers,
    "n_children": how many children the parent had in that run (kept), "kept_child": the sibling kept for review
    (held)}``.  A row judged not narrower has no badge.  ``label`` maps a target key to its display label."""
    b = (row or {}).get("narrow") or {}
    if b.get("status") not in ("kept", "held") or not b.get("parent"):
        return None
    key = b["parent"]
    path, href = target_path(key)
    lab = label(key) if label else None
    name = (lab if lab and lab != key else None) or b.get("parent_label") or key.partition(":")[2].replace("_", " ")
    asked = next((a for a in b.get("asked") or [] if a.get("parent") == key), {})
    out = {"status": b["status"], "parent": {"key": key, "label": name, "path": path, "href": href,
                                             "kind": "queue" if key.startswith("queue:") else "corpus"},
           "reading": asked.get("reading"), "votes": list(asked.get("votes") or [])}
    if b["status"] == "kept":
        out["n_children"] = b.get("n_children")
    else:
        out["kept_child"] = b.get("kept_child")
        out["held_because"] = b.get("held_because")
    return out


def blind_card(card):
    """``card`` (a group card, a term card or a member card) without the signal fields: every member card loses
    :data:`SIGNAL_FIELDS` and :data:`SIGNAL_FLAGS`, and the corpus entries their ``lexical`` block.  A copy."""
    def member(m):
        m = {k: v for k, v in m.items() if k not in SIGNAL_FIELDS}
        if "flags" in m:
            m["flags"] = [f for f in m["flags"] if f not in SIGNAL_FLAGS]
        return m
    out = dict(card)
    if "members" in out and isinstance(out["members"], list) and out["members"] and isinstance(out["members"][0], dict):
        out["members"] = [member(m) for m in out["members"]]
    if isinstance(out.get("term"), dict):
        out["term"] = member(out["term"])
    for k in ("corpus", "edges"):
        if isinstance(out.get(k), list):
            out[k] = [{kk: vv for kk, vv in e.items() if kk != "lexical"} for e in out[k]]
    if "label" in out and "key" in out and "gloss" in out:          # a bare member card
        out = member(out)
    return out


def _stem_of(surface) -> Optional[str]:
    from assistant_axis.gapgen.normalize import normalize_candidate
    try:
        return normalize_candidate(str(surface or "")).stem
    except ValueError:
        return None


def ipip_siblings(rows: Mapping[str, Mapping]) -> dict[str, list[dict]]:
    """``{source_ref: [{"key", "stem", "surface", "run_id"}, ...]}``: every IPIP source (``generator == "ipip"``) of
    every registry row, by the pole it names (``ipip:g600:c002a``).  The IPIP generator names each pole twice, blind
    and hinted (two runs, one ``source_ref``), and the two names often land in different review groups (Roger,
    2026-10-14), so the member card shows the other name (:func:`other_names_card`).  Built from the rows' ``sources``,
    not from the run files, so any later IPIP run joins in."""
    out: dict[str, list[dict]] = defaultdict(list)
    for key, row in rows.items():
        for s in (row or {}).get("sources") or []:
            if s.get("generator") != "ipip" or not s.get("source_ref"):
                continue
            surface = s.get("surface") or row.get("surface") or row.get("label")
            out[s["source_ref"]].append({"key": key, "stem": _stem_of(surface) or row.get("stem"),
                                         "surface": surface, "run_id": s.get("run_id")})
    return dict(out)


def other_names_card(key: str, row: Optional[Mapping], siblings: Mapping[str, list]) -> Optional[list[dict]]:
    """The member card's "other name" badge: for a row whose sources include an IPIP pole, the other names given to
    that same pole (``[{"surface", "key", "source_ref", "run_ids"}]``, one per stem, in the order met), leaving out a
    name that normalises to this row's own stem or to one of its own IPIP surfaces; None when there is none."""
    row = row or {}
    srcs = [s for s in row.get("sources") or [] if s.get("generator") == "ipip" and s.get("source_ref")]
    if not srcs:
        return None
    own = {row.get("stem") or key.split("#")[0]} | {_stem_of(s.get("surface")) for s in srcs}
    found: dict[str, dict] = {}
    for ref in dict.fromkeys(s["source_ref"] for s in srcs):
        for sib in siblings.get(ref, []):
            if sib["key"] == key or sib["stem"] in own:
                continue
            item = found.setdefault(sib["stem"], {"surface": sib["surface"], "key": sib["key"], "source_ref": ref,
                                                  "run_ids": []})
            if sib.get("run_id") and sib["run_id"] not in item["run_ids"]:
                item["run_ids"].append(sib["run_id"])
    return list(found.values()) or None


def target_path(key: str) -> tuple[Optional[str], Optional[str]]:
    """``(path relative to the repository, href on the app)`` of a corpus trait or queue entry key."""
    kind, _, stem = key.partition(":")
    if kind == "trait":
        return f"data/traits/instructions/{stem}.json", f"/files/traits/{stem}.json"
    if kind == "queue":
        return "data/seed_queue.json", f"/files/queue/{stem}"
    return None, None


def corpus_targets(data_dir: Optional[Path], queue_path: Optional[Path] = None) -> tuple[set, dict]:
    """``(merge targets, labels)``: every corpus trait (``trait:<stem>``) in ``data_dir/traits/instructions`` and every
    seed-queue entry not turned down (``queue:<stem>``), with their labels."""
    targets: set = set()
    labels: dict = {}
    if data_dir is None:
        return targets, labels
    d = Path(data_dir) / "traits" / "instructions"
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        key = f"trait:{p.stem}"
        targets.add(key)
        try:
            labels[key] = json.loads(p.read_text(encoding="utf-8")).get("positive_label") or p.stem
        except (OSError, json.JSONDecodeError):
            labels[key] = p.stem
    qp = Path(queue_path) if queue_path else Path(data_dir) / "seed_queue.json"
    if qp.exists():
        for e in json.loads(qp.read_text(encoding="utf-8")).get("entries") or []:
            if e.get("stem") and e.get("status") not in _TURNED_DOWN and (e.get("entity_type") or "trait") == "trait":
                targets.add(f"queue:{e['stem']}")
                labels.setdefault(f"queue:{e['stem']}", e.get("label") or e["stem"])
    return targets, labels


# --------------------------------------------------------------------------- the state

@dataclass
class Group:
    """A working group: opened from a merged or proposed group, a term, or as an antonym; resolved once."""
    id: str
    source: str                         # merged:<i> | proposed:<i> | term:<key> | antonym:<group> | split:<group>
    members: list
    status: str                         # proposed | open | resolved
    opened_seq: int
    opened_at: str
    by: Optional[str] = None
    via: Optional[str] = None           # the term an open came from
    nominated: Optional[str] = None
    resolution: Optional[str] = None    # promote | merge_into:<key> | park | reject | defer
    resolved_members: list = field(default_factory=list)
    resolved_seq: Optional[int] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    note: Optional[str] = None
    rename: bool = False                # the label wants a second look (the note says why)
    antonym_of: Optional[str] = None
    split_from: Optional[str] = None    # split_off: the resolved group whose leftovers this group took

    @property
    def kind(self) -> Optional[str]:
        """The resolution's kind (``merge_into:trait:x`` -> ``merge_into``)."""
        return self.resolution.split(":", 1)[0] if self.resolution else None

    @property
    def target(self) -> Optional[str]:
        return self.resolution.split(":", 1)[1] if self.resolution and ":" in self.resolution else None

    def as_dict(self) -> dict:
        return asdict(self)


class ReviewState:
    """The review as of some events: groups, handled terms, and the views the app shows.  Built empty by the
    constructor and filled by :meth:`apply` (one normalised event) or :func:`replay`.  ``rows``: the folded registry,
    for display (M1 tags, the review block already applied) and for the terms another review batch settled (the
    module docstring, "Handled before this batch"; the nodes' copy of the review block where a row is missing);
    ``targets``: merge targets beyond the graph's own corpus and queue nodes (:func:`corpus_targets`), with
    ``labels``; ``batch_id``: this review's batch (default the graph's), whose own review blocks are not earlier
    reviews."""

    def __init__(self, graph: RG.Graph, *, rows: Optional[Mapping[str, Mapping]] = None,
                 targets: Optional[Iterable[str]] = None, labels: Optional[Mapping[str, str]] = None,
                 batch_id: Optional[str] = None):
        self.graph = graph
        self.nodes = graph.node_map()
        self.kept = graph.candidate_keys()
        self.kept_set = set(self.kept)
        self.covered = {n.key for n in graph.nodes if n.kind == "candidate" and n.decision == "covered" and not n.included}
        self.merged = [list(c) for c in graph.cliques]
        self.proposed = [list(c) for c in graph.proposed_groups]
        grouped = {m for c in [*self.merged, *self.proposed] for m in c}
        self.singles = [x for x in self.kept if x not in grouped]
        self.rows = dict(rows or {})
        self._ipip_siblings: Optional[dict] = None     # built on the first member card (:func:`ipip_siblings`)
        self.labels = dict(labels or {})
        self.targets = set(targets or ()) | {n.key for n in graph.nodes
                                             if n.kind in ("corpus", "queue") and not n.missing}
        self.groups: dict[str, Group] = {}
        self.handled: dict[str, str] = {}
        self.distinct: dict[str, set] = defaultdict(set)       # candidate -> resolved groups it was marked distinct from
        self.applied: list[dict] = []
        self.skipped: list[dict] = []
        self.next_group = 1
        self.in_merged: dict[str, list[int]] = defaultdict(list)
        self.in_proposed: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.merged):
            for m in c:
                self.in_merged[m].append(i)
        for i, c in enumerate(self.proposed):
            for m in c:
                self.in_proposed[m].append(i)
        self.r1: dict[str, list[RG.Edge]] = defaultdict(list)
        self.m3: dict[str, list[RG.Edge]] = defaultdict(list)
        for e in graph.edges:
            if e.source == "r1":
                self.r1[e.a].append(e)
                self.r1[e.b].append(e)
            else:
                self.m3[e.a].append(e)
        self.covers: dict[str, list[str]] = defaultdict(list)
        for n in graph.nodes:
            if n.kind == "candidate" and n.decision == "covered" and n.covered_by and not n.included:
                self.covers[n.covered_by].append(n.key)
        # the terms another review batch decided (module docstring, "Handled before this batch"): ``earlier`` holds
        # every such decision, ``pre_handled`` the pseudo group ids of those that settled the term, which are
        # handled from the start
        self.batch_id = batch_id or graph.batch_id
        self.earlier: dict[str, dict] = {}
        self.pre_handled: dict[str, str] = {}
        own = {graph.batch_id, self.batch_id}
        for n in graph.nodes:
            if n.kind != "candidate" or not (n.key in self.kept_set or n.key in self.covered):
                continue
            src = RG.review_fields(self.rows[n.key]) if n.key in self.rows else \
                {f: getattr(n, f) for f in RG.REVIEW_FIELDS}
            if not src["review_status"] or src["review_batch"] in own:
                continue
            info = self._earlier_review(src)
            self.earlier[n.key] = info
            if info["handled"]:
                self.pre_handled[n.key] = self.handled[n.key] = info["id"]

    def _earlier_review(self, src: Mapping) -> dict:
        """What the page and the refusals say of an earlier review batch's decision (``src``:
        :func:`review_graph.review_fields`): ``id`` (the pseudo group id, ``<batch>/<group>``), ``batch``, ``group``,
        ``status``, ``into``, ``seed_queue_stem``, ``target`` (the seed-queue entry it was promoted to, or what it was
        merged into: a trait, a queue entry, or the nominee's queue entry when that was promoted), ``resolution``
        (``accepted → queue:irreligious``), ``handled`` and ``text`` (the badge)."""
        status, into, sqs = src["review_status"], src.get("review_into"), src.get("seed_queue_stem")
        batch, group = src.get("review_batch") or "registry", src.get("review_group")
        target = None
        if status == "accepted" and sqs:
            target = f"queue:{sqs}"
        elif status == "merged_into" and into:
            if into.startswith(("trait:", "queue:")):
                target = into
            else:                                   # merged into another batch's nominee: its queue entry, if promoted
                nom = self.rows[into].get("seed_queue_stem") if into in self.rows else \
                    getattr(self.nodes.get(into), "seed_queue_stem", None)
                target = f"queue:{nom}" if nom else None
        if status == "accepted":
            resolution = f"accepted → {target}" if target else "accepted"
        elif status == "merged_into":
            resolution = f"merged_into {into}" + (f" → {target}" if target and target != into else "")
        else:
            resolution = status
        handled = status in HANDLED_ELSEWHERE
        where = f"{batch} {group}" if group else batch
        return {"id": f"{batch}/{group}" if group else batch, "batch": batch, "group": group, "status": status,
                "into": into, "seed_queue_stem": sqs, "target": target, "resolution": resolution, "handled": handled,
                "text": f"handled in {where}: {resolution}" if handled else f"{status} in {where}; still to decide here"}

    # -- lookups --------------------------------------------------------------------
    def pre_handled_info(self, key: str) -> Optional[dict]:
        """The earlier review that handles ``key`` here, or None (none, or this log's own decision took it over)."""
        pid = self.pre_handled.get(key)
        return self.earlier[key] if pid is not None and self.handled.get(key) == pid else None

    def _log_handled(self, key: str) -> bool:
        """Handled by a group of this log.  The ``_apply_*`` checks use this, not ``handled``, so that a replay
        is the same whatever the registry says (a live action is refused a pre-handled term by its ``_check_*``)."""
        return self.handled.get(key) in self.groups

    def _handled_note(self, key: str) -> str:
        info = self.pre_handled_info(key)
        return f"{self.handled[key]}: {info['resolution']}" if info else str(self.handled[key])

    def label(self, key: str) -> str:
        n = self.nodes.get(key)
        return n.label if n is not None else self.labels.get(key, key)

    def is_candidate(self, key: str) -> bool:
        n = self.nodes.get(key)
        return n is not None and n.kind == "candidate" and (key in self.kept_set or key in self.covered)

    def seed_members(self, source: str) -> Optional[list[str]]:
        tier, _, idx = source.partition(":")
        seq = {"merged": self.merged, "proposed": self.proposed}.get(tier)
        if seq is None or not idx.isdigit() or int(idx) >= len(seq):
            return None
        return list(seq[int(idx)])

    def open_groups_with(self, key: str) -> list[Group]:
        return [g for g in self.groups.values() if g.status != "resolved" and key in g.members]

    def groups_from(self, source: str) -> list[Group]:
        return [g for g in self.groups.values() if g.source == source]

    def unhandled(self, keys: Iterable[str]) -> list[str]:
        return [m for m in keys if m not in self.handled]

    def antonym_groups(self, gid: str) -> list[str]:
        return [g.id for g in self.groups.values() if g.antonym_of == gid]

    def _group(self, req: Mapping) -> Group:
        gid = req.get("group")
        if gid not in self.groups:
            raise ActionError(f"no group {gid!r}")
        return self.groups[gid]

    def _new_gid(self) -> str:
        return f"g{self.next_group}"

    def note_ids(self, ev: Mapping) -> None:
        """Keep group ids unique across undone events too (an undone group's id is never reused)."""
        m = _GID.match(str(ev.get("group") or ""))
        if m:
            self.next_group = max(self.next_group, int(m.group(1)) + 1)

    # -- requests to events ---------------------------------------------------------
    def check(self, req: Mapping) -> dict:
        """A request (``{"action", ...}``) normalised into the event's fields, or ``{"existing": group id}`` for an
        open that finds its group already there; :class:`ActionError` for a refusal.  Changes nothing."""
        action = req.get("action")
        if action not in ACTIONS:
            raise ActionError(f"unknown action {action!r} (one of {', '.join(ACTIONS)})")
        return getattr(self, f"_check_{action}")(req)

    def _open_source(self, source: str, via: Optional[str] = None) -> dict:
        members = self.seed_members(source)
        if members is None:
            raise ActionError(f"no such group to open: {source!r}")
        live = [g for g in self.groups_from(source) if g.status != "resolved"]
        if live:
            return {"existing": live[-1].id}
        if all(m in self.handled for m in members):
            done = self.groups_from(source)
            mine = [self.handled[m] for m in members if self._log_handled(m)]
            if done or mine:
                return {"existing": done[-1].id if done else mine[0]}
            raise ActionError(f"every member of {source} was handled in an earlier review: "
                              + "; ".join(f"{m} {self.earlier[m]['text']}" for m in members))
        out = {"group": self._new_gid(), "action": "open", "source": source, "members": members,
               "status": "proposed" if source.startswith("proposed:") else "open"}
        if via:
            out["via"] = via
        return out

    def _check_open(self, req: Mapping) -> dict:
        source = str(req.get("source") or "")
        if source.startswith(("merged:", "proposed:")):
            return self._open_source(source)
        if not source.startswith("term:"):
            raise ActionError(f"open needs a source: merged:<i>, proposed:<i> or term:<key>, not {source!r}")
        key = source[len("term:"):]
        if key in self.covered:
            raise ActionError(f"{key} was covered by M3 ({self.nodes[key].covered_by}); it is not reviewed here, "
                              "but it can be pulled into a group with merge_in (decision 9)")
        if key not in self.kept_set:
            raise ActionError(f"{key} is not a term of this review")
        if key in self.handled:
            info = self.pre_handled_info(key)
            if info:
                raise ActionError(f"{key} was handled in review batch {info['batch']}"
                                  + (f", group {info['group']}" if info["group"] else "")
                                  + f": {info['resolution']} (the registry's review block); it is not reviewed again here")
            return {"existing": self.handled[key]}
        live = self.open_groups_with(key)
        if live:
            return {"existing": live[-1].id}
        for tier, index in (("merged", self.in_merged), ("proposed", self.in_proposed)):
            seeds = {"merged": self.merged, "proposed": self.proposed}[tier]
            if index.get(key):
                best = min(index[key], key=lambda i: (-len(seeds[i]), i))
                return self._open_source(f"{tier}:{best}", via=key)
        return {"group": self._new_gid(), "action": "open", "source": source, "members": [key], "status": "open"}

    def _check_accept(self, req: Mapping) -> dict:
        g = self._group(req)
        if g.status != "proposed":
            raise ActionError(f"{g.id} is not proposed ({g.status}): nothing to accept")
        return {"group": g.id, "action": "accept"}

    def _live(self, req: Mapping) -> Group:
        g = self._group(req)
        if g.status == "resolved":
            raise ActionError(f"{g.id} is already resolved ({g.resolution}); undo first to change it")
        return g

    def _check_drop(self, req: Mapping) -> dict:
        g = self._live(req)
        key = req.get("key")
        if key not in g.members:
            raise ActionError(f"{key} is not a member of {g.id}")
        if len(g.members) == 1:
            raise ActionError(f"{key} is the last member of {g.id}: a group is never emptied")
        return {"group": g.id, "action": "drop", "key": key}

    def _check_merge_in(self, req: Mapping) -> dict:
        g = self._live(req)
        keys = list(req.get("keys") or ([req["key"]] if req.get("key") else []))
        if not keys:
            raise ActionError("merge_in needs keys")
        bad = [x for x in keys if not self.is_candidate(x)]
        if bad:
            raise ActionError(f"{', '.join(map(str, bad))}: not a candidate of this graph (a corpus trait is a "
                              "resolution target: merge_into)")
        add, why = [], []
        for x in dict.fromkeys(keys):
            if x in g.members:
                why.append(f"{x} is already a member")
            elif x in self.handled:
                why.append(f"{x} is handled ({self._handled_note(x)})")
            else:
                add.append(x)
        if not add:
            raise ActionError("nothing to merge in: " + "; ".join(why))
        return {"group": g.id, "action": "merge_in", "keys": add}

    def _check_nominate(self, req: Mapping) -> dict:
        g = self._live(req)
        key = req.get("key")
        if key not in g.members:
            raise ActionError(f"{key} is not a member of {g.id}")
        if key in self.covered:
            raise ActionError(f"{key} was covered by M3: it can pass in as a synonym note, not be nominated")
        if key in self.handled:
            raise ActionError(f"{key} is handled ({self._handled_note(key)}): nominate an unhandled member")
        return {"group": g.id, "action": "nominate", "key": key}

    def _check_resolve(self, req: Mapping) -> dict:
        g = self._live(req)
        if g.status == "proposed":
            raise ActionError(f"{g.id} is a proposed group: accept it first (Accept group), excluding members before if needed")
        resolution = str(req.get("resolution") or "")
        kind, _, target = resolution.partition(":")
        if kind not in RESOLUTIONS or (kind == "merge_into") != bool(target):
            raise ActionError(f"resolution must be promote, merge_into:<trait:stem|queue:stem>, park, reject or defer, "
                              f"not {resolution!r}")
        if kind == "merge_into" and target not in self.targets:
            raise ActionError(f"{target} is not a corpus trait or queue entry")
        members = self.unhandled(g.members)
        if not members:
            raise ActionError(f"every member of {g.id} is already handled")
        nominated = None
        if kind == "promote":
            nominated = g.nominated
            if nominated is None or nominated in self.handled:
                terms = [m for m in members if m in self.kept_set]
                if len(terms) != 1:
                    raise ActionError(f"{g.id} has {len(terms)} unhandled terms: click the one to promote (or nominate it) "
                                      f"first")
                nominated = terms[0]
        note = req.get("note")
        return {"group": g.id, "action": "resolve", "members": members, "nominated": nominated,
                "resolution": resolution, "note": str(note) if note else None,
                "rename": bool(req.get("rename"))}

    def _check_start_antonym(self, req: Mapping) -> dict:
        of = req.get("of")
        if of not in self.groups:
            raise ActionError(f"no group {of!r}")
        if self.groups[of].status != "resolved":
            raise ActionError(f"{of} is not resolved: resolve it before starting its antonym group")
        have = self.antonym_groups(of)
        if have:
            raise ActionError(f"{of} already has an antonym group ({', '.join(have)})")
        keys = list(req.get("keys") or ([req["key"]] if req.get("key") else []))
        bad = [x for x in keys if x not in self.kept_set]
        if bad or not keys:
            raise ActionError(f"start_antonym needs terms of this review: {', '.join(map(str, bad)) or 'none given'}")
        members = [x for x in dict.fromkeys(keys) if x not in self.handled]
        if not members:
            raise ActionError("every term given is already handled")
        return {"group": self._new_gid(), "action": "start_antonym", "of": of, "members": members}

    def _resolved(self, req: Mapping) -> Group:
        g = self._group(req)
        if g.status != "resolved":
            raise ActionError(f"{g.id} is not resolved ({g.status}): this acts on a resolved group")
        return g

    def _leftover_keys(self, req: Mapping, g: Group, what: str) -> list[str]:
        keys = list(req.get("keys") or ([req["key"]] if req.get("key") else []))
        if not keys:
            raise ActionError(f"{what} needs keys")
        add, why = [], []
        for x in dict.fromkeys(keys):
            if not self.is_candidate(x):
                raise ActionError(f"{x}: not a candidate of this graph")
            if x in g.members:
                why.append(f"{x} is already a member of {g.id}")
            elif x in self.handled:
                why.append(f"{x} is handled ({self._handled_note(x)})")
            elif what == "distinct" and g.id in self.distinct.get(x, ()):
                why.append(f"{x} is already marked distinct from {g.id}")
            else:
                add.append(x)
        if not add:
            raise ActionError(f"nothing to mark: " + "; ".join(why))
        return add

    def _check_extend(self, req: Mapping) -> dict:
        g = self._resolved(req)
        return {"group": g.id, "action": "extend", "keys": self._leftover_keys(req, g, "extend")}

    def _check_distinct(self, req: Mapping) -> dict:
        g = self._resolved(req)
        return {"group": g.id, "action": "distinct", "keys": self._leftover_keys(req, g, "distinct")}

    def _check_split_off(self, req: Mapping) -> dict:
        g = self._resolved(req)
        target = str(req.get("target") or "")
        if not target:
            raise ActionError("split_off needs a target: the corpus trait or queue entry the leftovers merge into")
        if target not in self.targets:
            raise ActionError(f"{target} is not a corpus trait or queue entry")
        keys = self._leftover_keys(req, g, "split off")
        note = req.get("note")
        return {"group": self._new_gid(), "action": "split_off", "split_from": g.id, "keys": keys, "target": target,
                "resolution": f"merge_into:{target}", "note": str(note) if note else None}

    def split_groups(self, gid: str) -> list[str]:
        """The groups split off a resolved group's leftovers (``split_off``)."""
        return [g.id for g in self.groups.values() if g.split_from == gid]

    def _check_undo(self, req: Mapping) -> dict:
        if not self.applied:
            raise ActionError("nothing to undo")
        decisions = [e for e in self.applied if e.get("action") != "open"] or self.applied
        last = decisions[-1]
        try:
            seq = int(req["seq"]) if req.get("seq") is not None else None
        except (TypeError, ValueError):
            raise ActionError(f"undo: seq must be a decision's number, not {req.get('seq')!r}") from None
        if seq is not None and seq != last["seq"]:
            raise ActionError(f"only the last decision can be undone (seq {last['seq']}, {last['action']}); "
                              "undo again to go further back")
        out = {"group": last.get("group"), "action": "undo", "undoes": last["seq"], "undone_action": last["action"]}
        if last.get("resolution"):
            out["undone_resolution"] = last["resolution"]
        if last.get("keys") or last.get("key"):
            out["undone_keys"] = list(last.get("keys") or [last["key"]])
        if last.get("split_from"):
            out["split_from"] = last["split_from"]       # the page shows the group the split came from
        return out

    # -- events to state --------------------------------------------------------------
    def apply(self, ev: Mapping) -> None:
        """Apply one normalised event (validated first; nothing changes on :class:`ActionError`)."""
        action = ev.get("action")
        if action == "undo":
            raise ActionError("an undo is applied by replaying the log")
        if action not in ACTIONS:
            raise ActionError(f"unknown action {action!r}")
        self.note_ids(ev)
        getattr(self, f"_apply_{action}")(ev)
        self.applied.append(dict(ev))

    def _apply_open(self, ev: Mapping) -> None:
        gid, members = ev.get("group"), list(ev.get("members") or [])
        if not gid or gid in self.groups:
            raise ActionError(f"group {gid!r} exists")
        if not members or any(not self.is_candidate(m) for m in members):
            raise ActionError(f"open: members not in the graph: {members}")
        if ev.get("status") not in ("proposed", "open"):
            raise ActionError(f"open: bad status {ev.get('status')!r}")
        self.groups[gid] = Group(id=gid, source=ev.get("source") or "", members=members, status=ev["status"],
                                 opened_seq=ev.get("seq", 0), opened_at=ev.get("at", ""), by=ev.get("by"),
                                 via=ev.get("via"))

    def _apply_accept(self, ev: Mapping) -> None:
        g = self._group(ev)
        if g.status != "proposed":
            raise ActionError(f"{g.id} is not proposed")
        g.status = "open"

    def _apply_drop(self, ev: Mapping) -> None:
        g = self._live(ev)
        key = ev.get("key")
        if key not in g.members or len(g.members) == 1:
            raise ActionError(f"drop: {key} cannot be dropped from {g.id}")
        g.members.remove(key)
        if g.nominated == key:
            g.nominated = None

    def _apply_merge_in(self, ev: Mapping) -> None:
        g = self._live(ev)
        keys = list(ev.get("keys") or [])
        if not keys or any(not self.is_candidate(x) or x in g.members or self._log_handled(x) for x in keys):
            raise ActionError(f"merge_in: {keys} cannot be merged into {g.id}")
        g.members.extend(keys)

    def _apply_nominate(self, ev: Mapping) -> None:
        g = self._live(ev)
        key = ev.get("key")
        if key not in g.members or key not in self.kept_set or self._log_handled(key):
            raise ActionError(f"nominate: {key} cannot be nominated in {g.id}")
        g.nominated = key

    def _apply_resolve(self, ev: Mapping) -> None:
        g = self._live(ev)
        members = list(ev.get("members") or [])
        kind = str(ev.get("resolution") or "").split(":", 1)[0]
        if g.status != "open" or kind not in RESOLUTIONS or not members or \
                any(m not in g.members or self._log_handled(m) for m in members):
            raise ActionError(f"resolve: {g.id} cannot be resolved as logged")
        if kind == "promote" and ev.get("nominated") not in members:
            raise ActionError(f"resolve: the nominee {ev.get('nominated')} is not among the members resolved")
        g.status, g.resolution, g.resolved_members = "resolved", ev["resolution"], members
        g.nominated = ev.get("nominated") if kind == "promote" else g.nominated
        g.note, g.resolved_seq, g.resolved_at, g.resolved_by = ev.get("note"), ev.get("seq"), ev.get("at"), ev.get("by")
        g.rename = bool(ev.get("rename"))     # an event logged before the flag existed carries none: False
        for m in members:
            self.handled[m] = g.id

    def _apply_start_antonym(self, ev: Mapping) -> None:
        gid, of, members = ev.get("group"), ev.get("of"), list(ev.get("members") or [])
        if not gid or gid in self.groups or of not in self.groups or self.groups[of].status != "resolved":
            raise ActionError(f"start_antonym: cannot start {gid} as the antonym of {of}")
        if not members or any(m not in self.kept_set or self._log_handled(m) for m in members):
            raise ActionError(f"start_antonym: members {members} cannot open")
        self.groups[gid] = Group(id=gid, source=f"antonym:{of}", members=members, status="open",
                                 opened_seq=ev.get("seq", 0), opened_at=ev.get("at", ""), by=ev.get("by"),
                                 antonym_of=of)

    def _apply_extend(self, ev: Mapping) -> None:
        g = self._group(ev)
        keys = list(ev.get("keys") or [])
        if g.status != "resolved" or not keys or \
                any(not self.is_candidate(x) or x in g.members or self._log_handled(x) for x in keys):
            raise ActionError(f"extend: {keys} cannot extend {g.id}")
        g.members.extend(keys)
        g.resolved_members.extend(keys)
        for x in keys:
            self.handled[x] = g.id
            self.distinct.get(x, set()).discard(g.id)

    def _apply_split_off(self, ev: Mapping) -> None:
        gid, src, target = ev.get("group"), ev.get("split_from"), ev.get("target")
        keys = list(ev.get("keys") or [])
        if not gid or gid in self.groups or src not in self.groups or self.groups[src].status != "resolved":
            raise ActionError(f"split_off: cannot split {gid} off {src}")
        if target not in self.targets or ev.get("resolution") != f"merge_into:{target}":
            raise ActionError(f"split_off: {target} is not a merge target")
        if not keys or any(not self.is_candidate(x) or x in self.groups[src].members or self._log_handled(x)
                           for x in keys):
            raise ActionError(f"split_off: {keys} cannot be split off {src}")
        self.groups[gid] = Group(id=gid, source=f"split:{src}", members=list(keys), status="resolved",
                                 opened_seq=ev.get("seq", 0), opened_at=ev.get("at", ""), by=ev.get("by"),
                                 resolution=ev["resolution"], resolved_members=list(keys), resolved_seq=ev.get("seq"),
                                 resolved_at=ev.get("at"), resolved_by=ev.get("by"), note=ev.get("note"),
                                 split_from=src)
        for x in keys:
            self.handled[x] = gid

    def _apply_distinct(self, ev: Mapping) -> None:
        g = self._group(ev)
        keys = list(ev.get("keys") or [])
        if g.status != "resolved" or not keys or \
                any(not self.is_candidate(x) or x in g.members or self._log_handled(x) for x in keys):
            raise ActionError(f"distinct: {keys} cannot be marked distinct from {g.id}")
        for x in keys:
            self.distinct[x].add(g.id)

    # -- the queue ----------------------------------------------------------------------
    def seeds(self) -> list[dict]:
        out = [{"id": f"m{i}", "tier": "merged", "source": f"merged:{i}", "members": list(c), "index": i}
               for i, c in enumerate(self.merged)]
        out += [{"id": f"p{i}", "tier": "proposed", "source": f"proposed:{i}", "members": list(c), "index": i}
                for i, c in enumerate(self.proposed)]
        out += [{"id": f"s:{x}", "tier": "single", "source": f"term:{x}", "members": [x], "index": i}
                for i, x in enumerate(self.singles)]
        return out

    def _item(self, s: Mapping) -> dict:
        members = s["members"]
        handled = sum(1 for m in members if m in self.handled)
        live = [g for g in self.groups.values() if g.status != "resolved" and
                (g.source == s["source"] or (s["tier"] == "single" and members[0] in g.members))]
        status = "done" if handled == len(members) else ("open" if live else "todo")
        nodes = [self.nodes[m] for m in members]
        best = max((best_m3_reading(self.m3.get(m, [])) for m in members), default=-1)
        return {"id": s["id"], "tier": s["tier"], "source": s["source"], "members": list(members),
                "labels": [n.label for n in nodes], "size": len(members), "handled": handled,
                "remaining": len(members) - handled, "status": status, "group": live[-1].id if live else None,
                "generator": _mode(n.generator for n in nodes) or "", "region": _mode(n.region for n in nodes) or "",
                "flags": sorted({f for n in nodes for f in n.flags}),
                "best_reading": best, "stratum": sample_stratum(best)}

    def queue(self, order: str = "cliques") -> list[dict]:
        """Every merged group, proposed group and singleton as a queue item, in ``order``: ``cliques`` (groups
        largest first, merged before proposed at a size; then singletons by generator, region and label),
        ``generator`` or ``region`` (by the members' commonest generator or region, then tier and size), or
        ``sample`` (a seeded weighted random order: :data:`SAMPLE_WEIGHTS`)."""
        if order not in ORDERS:
            raise ActionError(f"order must be one of {', '.join(ORDERS)}")
        items = [self._item(s) for s in self.seeds()]
        tier_rank = {t: i for i, t in enumerate(TIERS)}
        idx = {it["id"]: s["index"] for it, s in zip(items, self.seeds())}
        if order == "sample":
            def key(it):
                return (sample_key(it["id"], SAMPLE_WEIGHTS[it["stratum"]]), it["id"])
        elif order == "cliques":
            def key(it):
                if it["tier"] == "single":
                    return (1, 0, 0, it["generator"], it["region"], it["labels"][0])
                return (0, -it["size"], tier_rank[it["tier"]], "", "", f"{idx[it['id']]:06d}")
        else:
            def key(it):
                return (it[order], tier_rank[it["tier"]], -it["size"], it["labels"][0], it["id"])
        return sorted(items, key=key)

    def _touched(self, it: Mapping, since_seq: int) -> bool:
        """An item this log has worked on after ``since_seq``: a member handled by a group of this log resolved
        after it, or a live group of this log opened after it (a term an earlier review batch settled is not)."""
        for m in it["members"]:
            g = self.groups.get(self.handled.get(m, ""))
            if g is not None and (g.resolved_seq or 0) > since_seq:
                return True
        return any(g.status != "resolved" and (g.opened_seq or 0) > since_seq and
                   (g.source == it["source"] or (it["tier"] == "single" and it["members"][0] in g.members))
                   for g in self.groups.values())

    def sample_progress(self, since_seq: int = 0) -> dict:
        """How far a session has gone down the ``sample`` order: ``reached`` (the items up to the last one this log
        worked on after ``since_seq``), per stratum the queue's items, the items reached and those done, and each
        stratum's inclusion probability at that depth (:func:`sample_inclusion`).  A term handled from outside the
        reached items (a leftover, a merge-in) is outside the sample's design and is counted apart, as
        ``pulled_in``."""
        q = self.queue("sample")
        last = max((i for i, it in enumerate(q) if self._touched(it, since_seq)), default=-1)
        reached = q[:last + 1]
        sizes = Counter(it["stratum"] for it in q)
        out = {"seed": SAMPLE_SEED, "weights": dict(SAMPLE_WEIGHTS), "reached": len(reached),
               "strata": {s: {"items": sizes[s], "reached": sum(1 for it in reached if it["stratum"] == s),
                              "done": sum(1 for it in reached if it["stratum"] == s and it["status"] == "done")}
                          for s in SAMPLE_WEIGHTS}}
        if reached:
            for s, p in sample_inclusion(sizes, len(reached)).items():
                out["strata"][s]["inclusion"] = round(p, 4)
        in_reached = {m for it in reached for m in it["members"]}
        out["pulled_in"] = sum(1 for x, gid in self.handled.items() if x not in in_reached and gid in self.groups
                               and (self.groups[gid].resolved_seq or 0) > since_seq)
        return out

    def queue_item(self, item_id: str) -> dict:
        for s in self.seeds():
            if s["id"] == item_id:
                return self._item(s)
        raise KeyError(item_id)

    def counts(self) -> dict:
        """The counts the page shows at all times: per tier, total and remaining (a member not yet handled); terms
        handled; working groups resolved, open and proposed (opened, not yet accepted)."""
        out: dict[str, Any] = {t: {"total": 0, "remaining": 0} for t in TIERS}
        for s in self.seeds():
            out[s["tier"]]["total"] += 1
            out[s["tier"]]["remaining"] += any(m not in self.handled for m in s["members"])
        n_handled = sum(1 for x in self.kept if x in self.handled)
        out["terms"] = {"total": len(self.kept), "handled": n_handled, "remaining": len(self.kept) - n_handled}
        st = Counter(g.status for g in self.groups.values())
        out["groups_resolved"], out["groups_open"], out["groups_proposed_open"] = st["resolved"], st["open"], st["proposed"]
        return out

    # -- cards ------------------------------------------------------------------------
    def ipip_siblings(self) -> dict:
        """:func:`ipip_siblings` of the folded registry, built once per state."""
        if self._ipip_siblings is None:
            self._ipip_siblings = ipip_siblings(self.rows)
        return self._ipip_siblings

    def member_card(self, key: str) -> dict:
        n = self.nodes[key]
        row = self.rows.get(key) or {}
        f = row.get("filter") or {}
        rv = row.get("review") or {}
        # the tags are M1's; a physical pass's node says physical even where the registry row has none, and a row the
        # states pass released says so, with its route and duration (``states pass: lasting (months)``)
        from assistant_axis.gapgen import states_pass as SP
        tags = list(dict.fromkeys(list(f.get("tags") or []) + ([n.outcome] if n.outcome else [])
                                  + ([SP.card_tag(row)] if SP.card_tag(row) else [])))
        out = {"key": key, "label": n.label, "gloss": n.gloss, "generator": n.generator, "generators": list(n.generators),
               "region": n.region, "alignment_score": n.alignment_score, "tags": tags,
               "membership_kind": f.get("membership_kind"), "m3_decision": n.decision, "m3_run": n.m3_run,
               "flags": list(n.flags), "covered": key in self.covered,
               "merged": [f"m{i}" for i in self.in_merged.get(key, [])],
               "proposed": [f"p{i}" for i in self.in_proposed.get(key, [])],
               "handled_by": self.handled.get(key), "handled_resolution": None,
               "distinct_from": sorted(self.distinct.get(key, ())),
               "applied": rv.get("status") if rv.get("status") not in (None, "unreviewed") else None,
               "seed_queue_stem": row.get("seed_queue_stem") if key in self.rows else n.seed_queue_stem,
               "earlier_review": self.earlier.get(key), "relabel": relabel_card(row),
               "other_names": other_names_card(key, row, self.ipip_siblings()),
               "persona": persona_card(row, self.label), "narrow": narrow_card(row, self.label)}
        if out["handled_by"]:
            pre = self.pre_handled_info(key)
            out["handled_resolution"] = pre["resolution"] if pre else self.groups[out["handled_by"]].resolution
        if n.covered_by:
            path, href = target_path(n.covered_by)
            out["covered_by"] = {"key": n.covered_by, "label": self.label(n.covered_by), "path": path, "href": href,
                                 "reading": n.covered_reading}
        # plan 11 (Roger, 2026-10-14, option (d)): a dictionary link read at the row's cut-off is a proposed merge,
        # shown as "dictionary (WordNet | Moby thesaurus): probably the same as X"; never a cut
        merges = [self._target_entry(e.b) | lexical_info(e) | {"reading": _dir_text(e.readings.get("ab"))}
                  for e in self.m3.get(key, []) if e.source == "lexical" and (e.lexical or {}).get("at_cut_off")]
        if merges:
            out["lexical_merges"] = merges
        return out

    def _target_entry(self, key: str) -> dict:
        n = self.nodes.get(key)
        path, href = target_path(key)
        if n is not None and n.missing:
            path = href = None
        return {"key": key, "kind": n.kind if n is not None else ("corpus" if key.startswith("trait:") else "queue"),
                "label": self.label(key), "gloss": n.gloss if n is not None else None, "path": path, "href": href}

    def _term_entry(self, key: str) -> dict:
        n = self.nodes[key]
        return {"key": key, "kind": "candidate", "label": n.label, "gloss": n.gloss, "generator": n.generator,
                "merged": [f"m{i}" for i in self.in_merged.get(key, [])],
                "proposed": [f"p{i}" for i in self.in_proposed.get(key, [])],
                "handled_by": self.handled.get(key), "covered": key in self.covered,
                "distinct_from": sorted(self.distinct.get(key, ())), "earlier_review": self.earlier.get(key)}

    def _covered_of(self, t: str) -> list[dict]:
        """The covered candidates a corpus or queue trait covers (greyed in its row), each ``handled_by`` if handled."""
        out = []
        for c in self.covers.get(t, []):
            rd = self.nodes[c].covered_reading or {}
            item = {"key": c, "label": self.nodes[c].label,
                    "reading": f"{rd.get('sonnet')}/{rd.get('opus') if rd.get('opus') is not None else '-'}"}
            if c in self.handled:
                item["handled_by"] = self.handled[c]
            out.append(item)
        return out

    def _with_group(self, key: str, members: set) -> list[str]:
        """What ``m`` (merge in) or ``a`` (start the antonym group) takes for a neighbour: its largest merged group's
        unhandled terms not already in, else the term alone (nothing if it is handled)."""
        if key in self.handled:
            return []
        if self.in_merged.get(key):
            best = min(self.in_merged[key], key=lambda i: (-len(self.merged[i]), i))
            return [m for m in self.merged[best] if m not in self.handled and m not in members] or [key]
        return [key]

    def neighbourhood(self, members: Sequence[str], basis: Optional[Sequence[str]] = None) -> dict:
        """The neighbours of a set of members: ``neighbours`` (candidates by their strongest non-opposed edge to the
        set: 4-edge, 3-edge, best reading, then the relation (similar, unsure, unrelated), then cosine), ``corpus``
        (corpus and queue traits from the members' M3
        readings, by reading then cosine, each with the covered candidates it covers, greyed), ``opposed``
        (candidates, then corpus and queue traits, joined by an opposed edge, by cosine).  ``basis``: the members
        whose edges are followed (default all); a member of ``members`` is never listed as a neighbour either way.
        A group's card passes the members still to decide (Roger, 2026-10-11: "when dealing with the dregs of a
        group, the right-hand panel needs to be recomputed, to not include relationships to excluded items").

        ``corpus`` also lists, with ``through``, the target of each term an earlier review batch handled that is a
        neighbour or a member outside the basis (the seed-queue entry it was promoted to, or what it was merged
        into), when that target is a merge target here: ranked by the strongest edge from the basis to that term, so
        "Covered by this" merges the rest into the word already decided (module docstring)."""
        S = set(members)
        basis = list(basis if basis is not None else members)
        best: dict[str, tuple] = {}
        opp: dict[str, tuple] = {}
        for m in basis:
            for e in self.r1.get(m, []):
                o = e.b if e.a == m else e.a
                if o in S:
                    continue
                if e.relation == "opposed":
                    if o not in opp or (e.cosine or 0) > (opp[o][0] or 0):
                        opp[o] = (e.cosine, m, e)
                    continue
                rank = (edge_level(e), REL_RANK.get(e.relation, 0), e.cosine or 0.0)
                if o not in best or rank > best[o][0]:
                    best[o] = (rank, m, e)
        neighbours = []
        for o, (rank, m, e) in sorted(best.items(), key=lambda kv: (tuple(-x for x in kv[1][0]), kv[0])):
            neighbours.append(self._term_entry(o) | {
                "level": rank[0], "cosine": e.cosine, "relation": e.relation, "readings": readings_text(e),
                "strict": e.strict, "proposed_edge": e.proposed, "via": m, "via_label": self.nodes[m].label,
                "merge_keys": self._with_group(o, S)})
        corpus: dict[str, tuple] = {}
        opp_t: dict[str, tuple] = {}
        for m in basis:
            for e in self.m3.get(m, []):
                rd = e.readings.get("ab")
                if e.relation == "opposed":
                    if e.b not in opp_t or (e.cosine or 0) > (opp_t[e.b][0] or 0):
                        opp_t[e.b] = (e.cosine, m, e)
                    continue
                rank = (_final(rd) if _final(rd) is not None else -1, e.cosine or 0.0)
                if e.b not in corpus or rank > corpus[e.b][0]:
                    corpus[e.b] = (rank, m, e)
        # the targets of the terms an earlier review batch handled, through those terms (a target M3 read stays
        # as M3 read it)
        through: dict[str, tuple] = {}
        bset = set(basis)
        for o in [*best, *(m for m in members if m not in bset)]:
            info = self.pre_handled_info(o)
            t = info["target"] if info else None
            if not t or t not in self.targets or t in corpus:
                continue
            top = None
            for e in self.r1.get(o, []):
                x = e.b if e.a == o else e.a
                if x in bset and e.relation != "opposed":
                    r = (edge_level(e), e.cosine or 0.0)
                    if top is None or r > top[0]:
                        top = (r, x, e)
            rank = top[0] if top else (-1, 0.0)
            if t not in through or rank > through[t][0]:
                through[t] = (rank, o, top)
        rows_out = []
        for t, (rank, m, e) in corpus.items():
            rows_out.append(((-rank[0], -rank[1], t), self._target_entry(t) | {
                "relation": e.relation, "cosine": e.cosine, "reading": _dir_text(e.readings.get("ab")),
                "level": rank[0], "via": m, "via_label": self.nodes[m].label, "covered": self._covered_of(t)}
                | ({"lexical": lexical_info(e)} if e.source == "lexical" else {})))
        for t, (rank, o, top) in through.items():
            x, e = (top[1], top[2]) if top else (None, None)
            rows_out.append(((-rank[0], -rank[1], t), self._target_entry(t) | {
                "relation": e.relation if e else None, "cosine": e.cosine if e else None,
                "reading": readings_text(e) if e else None, "level": rank[0], "via": x,
                "via_label": self.nodes[x].label if x else None, "covered": self._covered_of(t),
                "through": {"key": o, "label": self.nodes[o].label, "text": self.earlier[o]["text"]}}))
        corpus_out = [entry for _, entry in sorted(rows_out, key=lambda kv: kv[0])]
        opposed = []
        for o, (cos, m, e) in sorted(opp.items(), key=lambda kv: (-(kv[1][0] or 0), kv[0])):
            opposed.append(self._term_entry(o) | {"cosine": cos, "via": m, "via_label": self.nodes[m].label,
                                                  "antonym_keys": self._with_group(o, S)})
        for t, (cos, m, e) in sorted(opp_t.items(), key=lambda kv: (-(kv[1][0] or 0), kv[0])):
            opposed.append(self._target_entry(t) | {"cosine": cos, "via": m, "via_label": self.nodes[m].label})
        return {"neighbours": neighbours, "corpus": corpus_out, "opposed": opposed}

    def leftovers(self, gid: str) -> list[dict]:
        """A resolved group's leftovers (module docstring): the unhandled candidates of every merged or proposed
        group that shares a member with it, not marked distinct from it, strongest tie first -- ``ties`` 4-edges to
        the group's members, then the best edge level to any of them -- each with the groups it comes from."""
        g = self.groups[gid]
        if g.status != "resolved":
            return []
        S = set(g.members)
        seen: dict[str, list] = {}
        for tier, seeds in (("m", self.merged), ("p", self.proposed)):
            for i, c in enumerate(seeds):
                if not S.intersection(c):
                    continue
                for x in c:
                    if x not in S and x not in self.handled and gid not in self.distinct.get(x, ()):
                        seen.setdefault(x, []).append(f"{tier}{i}")
        out = []
        for x, groups in seen.items():
            ties, best = 0, 0
            for e in self.r1.get(x, []):
                o = e.b if e.a == x else e.a
                if o in S and e.relation != "opposed":
                    lvl = edge_level(e)
                    ties += bool(e.strict)          # a 4-edge: 4 both ways (edge_level is 4 for a one-way 4 too)
                    best = max(best, lvl)
            out.append(self._term_entry(x) | {"ties": ties, "of": len(S), "level": best, "groups": groups})
        out.sort(key=lambda d: (-d["ties"], -d["level"], d["label"], d["key"]))
        return out

    def group_card(self, gid: str) -> dict:
        """Everything the page shows for one working group."""
        if gid not in self.groups:
            raise KeyError(gid)
        g = self.groups[gid]
        own = {"merged": g.source.split(":", 1)[1] if g.source.startswith("merged:") else None,
               "proposed": g.source.split(":", 1)[1] if g.source.startswith("proposed:") else None}
        # the basis of the right-hand panel and of the overlap list: the members this group still decides -- for a
        # resolved group its own, for an open one those no other group has handled (the dregs of a reopened group)
        basis = [m for m in g.members if self.handled.get(m, g.id) == g.id]
        S = set(basis)
        others = []
        for s in self.seeds():
            if s["tier"] == "single":
                continue
            tier_key = "merged" if s["tier"] == "merged" else "proposed"
            if own[tier_key] is not None and str(s["index"]) == own[tier_key]:
                continue
            shared = [m for m in s["members"] if m in S]
            if shared and set(s["members"]) != S:
                others.append({"id": s["id"], "tier": s["tier"], "members": list(s["members"]),
                               "labels": [self.nodes[m].label for m in s["members"]], "shared": shared,
                               "remaining": sum(1 for m in s["members"] if m not in self.handled)})
        others.sort(key=lambda x: (TIERS.index(x["tier"]), -len(x["members"]), x["id"]))
        card = {"id": g.id, "status": g.status, "source": g.source, "via": g.via, "opened_seq": g.opened_seq,
                "members": [self.member_card(m) for m in g.members], "nominated": g.nominated,
                "resolution": g.resolution, "resolved_members": list(g.resolved_members), "note": g.note,
                "rename": g.rename,
                "antonym_of": g.antonym_of, "antonym_groups": self.antonym_groups(g.id),
                "split_from": g.split_from, "split_groups": self.split_groups(g.id),
                "neighbour_groups": others, "basis": list(basis), "leftovers": self.leftovers(gid),
                "distinct": sorted((self._term_entry(x) for x, gs in self.distinct.items() if gid in gs),
                                   key=lambda d: d["label"])}
        if g.resolution and g.target:
            card["target"] = self._target_entry(g.target)
        return card | self.neighbourhood(g.members, basis)

    def term_card(self, key: str) -> dict:
        """The ego view: the term and everything one edge away (candidate and corpus edges, by cosine)."""
        if key not in self.nodes or self.nodes[key].kind != "candidate":
            raise KeyError(key)
        edges = []
        for e in self.r1.get(key, []):
            o = e.b if e.a == key else e.a
            edges.append({"key": o, "kind": "candidate", "label": self.nodes[o].label, "relation": e.relation,
                          "cosine": e.cosine, "readings": readings_text(e), "strict": e.strict,
                          "proposed_edge": e.proposed, "handled_by": self.handled.get(o),
                          "earlier_review": self.earlier.get(o)})
        for e in self.m3.get(key, []):
            edges.append(self._target_entry(e.b) | {"relation": e.relation, "cosine": e.cosine,
                                                    "readings": _dir_text(e.readings.get("ab")) or ""}
                         | ({"lexical": lexical_info(e)} if e.source == "lexical" else {}))
        edges.sort(key=lambda x: (-(x["cosine"] or 0), x["key"]))
        return {"term": self.member_card(key), "merged": [f"m{i}" for i in self.in_merged.get(key, [])],
                "proposed": [f"p{i}" for i in self.in_proposed.get(key, [])],
                "groups": [g.id for g in self.groups.values() if key in g.members], "edges": edges}

    def find(self, q: str, *, limit: int = 30) -> list[dict]:
        """Terms, covered candidates, corpus traits and queue entries whose label matches ``q`` (prefix matches
        first, then substring; ``/`` on the page)."""
        q = (q or "").strip().lower()
        if not q:
            return []
        pool: dict[str, tuple[str, str]] = {}
        for n in self.graph.nodes:
            if n.kind == "candidate" and (n.key in self.kept_set or n.key in self.covered):
                pool[n.key] = (n.label, "covered" if n.key in self.covered else "candidate")
            elif n.kind in ("corpus", "queue"):
                pool[n.key] = (n.label, n.kind)
        for key in self.targets:
            pool.setdefault(key, (self.label(key), "corpus" if key.startswith("trait:") else "queue"))
        hits = [(0 if lb.lower().startswith(q) else 1, lb.lower(), key, lb, kind)
                for key, (lb, kind) in pool.items() if q in lb.lower()]
        out = []
        for _, _, key, lb, kind in sorted(hits)[:limit]:
            item = {"key": key, "label": lb, "kind": kind}
            if kind in ("corpus", "queue"):
                item["path"], item["href"] = target_path(key)
            else:
                item["handled_by"] = self.handled.get(key)
                if key in self.earlier:
                    item["earlier_review"] = self.earlier[key]
            out.append(item)
        return out

    # -- status -------------------------------------------------------------------------
    def status(self, events: Sequence[Mapping]) -> dict:
        """Groups resolved and open, decisions by type, time per decision (from the events' timestamps), and the
        terms handled before this batch (``pre_handled``, module docstring)."""
        resolved = [g for g in self.groups.values() if g.status == "resolved"]
        per_group = []
        for g in resolved:
            if g.split_from:                    # opened and resolved by one event: its time is its group's
                continue
            a, b = _parse_at(g.opened_at), _parse_at(g.resolved_at or "")
            if a and b:
                per_group.append((b - a).total_seconds() / 60.0)
        times = sorted(t for t in (_parse_at(e.get("at", "")) for e in events) if t is not None)
        gaps = [(b - a).total_seconds() / 60.0 for a, b in zip(times, times[1:])]
        active = sum(x for x in gaps if x <= IDLE_MINUTES)
        pre = [x for x in self.kept if self.pre_handled_info(x)]
        return {"events": len(events), "effective_events": len(self.applied), "skipped": len(self.skipped),
                # the terms another review batch settled (handled here from the start), those it parked or deferred
                # (live here), and those this log resolved although another batch had settled them
                "pre_handled": {
                    "terms": len(pre),
                    "by_batch": dict(sorted(Counter(self.earlier[x]["batch"] for x in pre).items())),
                    "by_status": dict(sorted(Counter(self.earlier[x]["status"] for x in pre).items())),
                    "live_elsewhere": sum(1 for x in self.kept if x in self.earlier and not self.earlier[x]["handled"]),
                    "resolved_here_too": sum(1 for x in self.kept if x in self.pre_handled and x not in pre)},
                "by_action": dict(sorted(Counter(e.get("action") for e in events).items())),
                "resolutions": dict(sorted(Counter(g.kind for g in resolved).items())),
                "groups": {"resolved": len(resolved),
                           "open": sum(1 for g in self.groups.values() if g.status == "open"),
                           "proposed": sum(1 for g in self.groups.values() if g.status == "proposed"),
                           "total": len(self.groups)},
                "counts": self.counts(),
                "timing": {"minutes_per_resolved_group": {
                               "median": round(statistics.median(per_group), 2) if per_group else None,
                               "mean": round(statistics.fmean(per_group), 2) if per_group else None},
                           "active_minutes": round(active, 2), "sessions": 1 + sum(1 for x in gaps if x > IDLE_MINUTES)
                           if times else 0,
                           "decisions_per_minute": round(len(resolved) / active, 3) if active else None,
                           "first": times[0].isoformat() if times else None,
                           "last": times[-1].isoformat() if times else None}}


def replay(graph: RG.Graph, events: Sequence[Mapping], *, rows=None, targets=None, labels=None,
           batch_id: Optional[str] = None) -> ReviewState:
    """The state the events give: undo events and the events they undo left out, the rest applied in order; an
    event that no longer applies (the graph was rebuilt) is skipped and listed in ``skipped``.  The terms another
    review batch settled are handled from the start, and do not change what an event does (module docstring)."""
    st = ReviewState(graph, rows=rows, targets=targets, labels=labels, batch_id=batch_id)
    undone = {e.get("undoes") for e in events if e.get("action") == "undo"}
    for e in events:
        st.note_ids(e)
        if e.get("action") == "undo" or e.get("seq") in undone:
            continue
        try:
            st.apply(e)
        except ActionError as exc:
            st.skipped.append({"seq": e.get("seq"), "action": e.get("action"), "group": e.get("group"),
                               "why": str(exc)})
            logger.warning("decision %s (%s) skipped on replay: %s", e.get("seq"), e.get("action"), exc)
    return st


# --------------------------------------------------------------------------- the log

def read_events(path: Path) -> list[dict]:
    out = []
    if not Path(path).exists():
        return out
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("%s:%d: not JSON, skipped (a torn write?)", path, i)
            continue
        if isinstance(ev, dict) and "seq" in ev and "action" in ev:
            out.append(ev)
    return out


class DecisionLog:
    """``decisions.jsonl`` and the state it replays to.  :meth:`act` validates a request against the state, appends
    the event (with ``seq``, ``at``, ``by``, ``graph_sha256``) and updates the state; thread-safe (``lock``)."""

    def __init__(self, path: Path, graph: RG.Graph, *, graph_sha256: str, by: str = "roger",
                 clock: Optional[Callable[[], str]] = None, rows=None, targets=None, labels=None,
                 batch_id: Optional[str] = None):
        self.path = Path(path)
        self.graph = graph
        self.graph_sha256 = graph_sha256
        self.by = by
        self.clock = clock or utc_now
        self.rows, self.targets, self.labels = dict(rows or {}), set(targets or ()), dict(labels or {})
        self.batch_id = batch_id or graph.batch_id
        self.lock = threading.RLock()
        self.events = read_events(self.path)
        self.state = self._replay()

    @classmethod
    def open(cls, review_dir: Path, *, by: str = "roger", clock=None, data_dir: Optional[Path] = None,
             registry_path: Optional[Path] = None, queue_path: Optional[Path] = None) -> "DecisionLog":
        """The log of a review batch's directory (``graph.json`` must be there)."""
        review_dir = Path(review_dir)
        gp = review_dir / GRAPH_NAME
        if not RF.exists(gp):
            raise FileNotFoundError(f"{gp} not found: build the graph first (review_graph.py build)")
        raw = RF.read_bytes(gp)  # the graph's content, packed or not (its sha256 is the same either way)
        graph = RG.Graph.from_json(json.loads(raw))
        rows = Registry(registry_path).fold() if registry_path and Path(registry_path).exists() else {}
        targets, labels = corpus_targets(data_dir, queue_path)
        return cls(review_dir / LOG_NAME, graph, graph_sha256=hashlib.sha256(raw).hexdigest(), by=by, clock=clock,
                   rows=rows, targets=targets, labels=labels, batch_id=review_dir.name)

    def _replay(self) -> ReviewState:
        return replay(self.graph, self.events, rows=self.rows, targets=self.targets, labels=self.labels,
                      batch_id=self.batch_id)

    def graph_versions(self) -> dict:
        return dict(Counter(e.get("graph_sha256") for e in self.events))

    def act(self, req: Mapping) -> tuple[Optional[dict], Optional[str]]:
        """``(event, group id)``: the event appended, or ``None`` with the existing group's id for an open that finds
        its group; :class:`ActionError` for a refusal (nothing logged)."""
        with self.lock:
            norm = self.state.check(req)
            if "existing" in norm:
                return None, norm["existing"]
            gid = norm.pop("group", None)
            ev = {"seq": max((e["seq"] for e in self.events), default=0) + 1, "at": self.clock(), "by": self.by,
                  "group": gid, **norm, "graph_sha256": self.graph_sha256}
            if ev["action"] != "undo":
                try:
                    self.state.apply(ev)
                except BaseException:
                    # nothing is logged; the state is rebuilt from the log, so that a check and an apply that
                    # disagree (a bug) never leave the state the page shows ahead of what a restart replays
                    self.state = self._replay()
                    raise
            try:
                self._append(ev)
            except BaseException:
                self.state = self._replay()
                raise
            self.events.append(ev)
            if ev["action"] == "undo":
                self.state = self._replay()
            return ev, gid

    def _append(self, ev: Mapping) -> None:
        """One line, flushed and fsynced.  A last line without its newline (a write torn by a crash or a full disk,
        which :func:`read_events` skips) is closed first, so that this event starts a line of its own instead of
        being glued to the fragment and lost on the next replay."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(ev, ensure_ascii=False) + "\n"
        with open(self.path, "a+b") as fh:
            fh.seek(0, os.SEEK_END)
            if fh.tell():
                fh.seek(-1, os.SEEK_END)
                if fh.read(1) != b"\n":
                    line = "\n" + line
            fh.write(line.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())

    def status(self) -> dict:
        with self.lock:
            out = self.state.status(self.events)
            out["graph_versions"] = self.graph_versions()
            out["graph_sha256"] = self.graph_sha256
            out["skipped_events"] = list(self.state.skipped)
            return out


# --------------------------------------------------------------------------- apply

def desired_blocks(state: ReviewState, batch_id: str) -> dict[str, dict]:
    """The ``review`` block every resolved group's members should carry (later resolutions after earlier ones)."""
    out: dict[str, dict] = {}
    for g in sorted((g for g in state.groups.values() if g.status == "resolved"), key=lambda g: g.resolved_seq or 0):
        base = {"by": g.resolved_by, "at": g.resolved_at, "note": g.note, "group": list(g.resolved_members),
                "review_batch": batch_id, "review_group": g.id}
        # the rename flag is written only when it is set, so that a row applied before the flag existed stays
        # byte-identical (``apply`` is idempotent by comparing the whole block)
        if g.rename:
            base["rename"] = True
        if g.antonym_of:
            base["antonym_of"] = g.antonym_of
        if g.split_from:
            base["split_from"] = g.split_from
        ants = state.antonym_groups(g.id)
        if ants:
            base["antonym_group"] = ants[0]
        for m in g.resolved_members:
            if g.kind == "promote":
                block = {"status": "accepted"} if m == g.nominated else {"status": "merged_into", "into": g.nominated}
            elif g.kind == "merge_into":
                block = {"status": "merged_into", "into": g.target}
            else:
                block = {"status": REVIEW_STATUS[g.kind]}
            out[m] = block | base
    return out


def rename_worklist(state: ReviewState, *, rows: Optional[Mapping[str, Mapping]] = None,
                    stems: Optional[Mapping[str, str]] = None) -> list[dict]:
    """The resolved groups flagged for a rename, one row each, oldest decision first: the worklist the promotion
    report prints (QUESTIONS 71's human net).  Each row names the label the decision settled on -- the promoted
    nominee, or the trait or queue entry it was merged into, else the first member resolved -- its seed-queue
    ``stem`` where it has one, and the ``note`` that says what is awkward about it.  ``rows``: the folded registry
    (for a ``seed_queue_stem`` written by an earlier apply); ``stems``: stems promoted by this run."""
    rows, stems = dict(rows or {}), dict(stems or {})
    out = []
    for g in sorted((g for g in state.groups.values() if g.status == "resolved" and g.rename),
                    key=lambda g: g.resolved_seq or 0):
        if g.kind == "promote":
            key = g.nominated
        elif g.kind == "merge_into":
            key = g.target
        else:
            key = g.resolved_members[0] if g.resolved_members else None
        stem = None
        if key:
            stem = stems.get(key) or (rows.get(key) or {}).get("seed_queue_stem")
            if stem is None and key.startswith(("trait:", "queue:")):
                stem = key.split(":", 1)[1]
        out.append({"group": g.id, "resolution": g.resolution, "key": key,
                    "label": state.label(key) if key else None, "stem": stem, "note": g.note})
    return out


@dataclass
class ApplyReport:
    dry_run: bool
    review_writes: dict = field(default_factory=dict)     # key -> the new review block (changed rows only)
    unchanged: int = 0
    resets: list = field(default_factory=list)           # rows this review wrote earlier that the log no longer resolves
    promotions: list = field(default_factory=list)       # [{"group", "key", "stem", "also_proposed"}]
    refused: dict = field(default_factory=dict)          # nominee -> promote's reason
    already_promoted: dict = field(default_factory=dict)  # nominee -> its seed_queue_stem
    conflicts: list = field(default_factory=list)
    missing: list = field(default_factory=list)          # keys the registry does not have
    rename_flagged: list = field(default_factory=list)   # :func:`rename_worklist`: labels Roger flagged in review

    @property
    def changed(self) -> bool:
        return bool(self.review_writes or self.resets or self.promotions)

    def format(self) -> str:
        w = "WOULD " if self.dry_run else ""
        lines = []
        for key, b in self.review_writes.items():
            extra = f" into {b['into']}" if b.get("into") else ""
            n = len(b.get("group") or [])
            lines.append(f"{w}WRITE {key} review {b['status']}{extra} (group {b.get('review_group')}, "
                         f"{n} member{'' if n == 1 else 's'})")
        for key in self.resets:
            lines.append(f"{w}RESET {key} review unreviewed (this review no longer resolves it)")
        for p in self.promotions:
            lines.append(f"{w}PROMOTE {p['key']} -> {p['stem']}" if self.dry_run else f"PROMOTED {p['key']} -> {p['stem']}")
            lines[-1] += f" (group {p['group']}; also_proposed: {', '.join(p['also_proposed']) or 'none'})"
        for key, why in self.refused.items():
            lines.append(f"REFUSED promotion of {key}: {why}")
        for key, stem in self.already_promoted.items():
            lines.append(f"already promoted: {key} -> {stem}")
        for c in self.conflicts:
            lines.append(f"CONFLICT: {c}")
        for key in self.missing:
            lines.append(f"MISSING from the registry: {key}")
        if self.rename_flagged:
            lines.append(f"Flagged for a rename in review ({len(self.rename_flagged)}): instruction generation "
                         "makes the label-blind naming call, and generate_antonyms.py --name-pos re-asks it")
            for x in self.rename_flagged:
                lines.append(f"  RENAME? {x['stem'] or x['key']} ({x['label']}, {x['resolution']}, group "
                             f"{x['group']})" + (f": {x['note']}" if x.get("note") else ""))
        lines.append(f"{len(self.review_writes)} review blocks to write, {len(self.resets)} to reset, "
                     f"{self.unchanged} unchanged, {len(self.promotions)} promotions"
                     + (f", {len(self.rename_flagged)} flagged for a rename" if self.rename_flagged else "")
                     + ("" if self.changed else "; nothing to write"))
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {"dry_run": self.dry_run, "review_writes": len(self.review_writes), "unchanged": self.unchanged,
                "resets": list(self.resets), "promoted": [p["key"] for p in self.promotions],
                "promotions": list(self.promotions), "refused": dict(self.refused),
                "already_promoted": dict(self.already_promoted), "conflicts": list(self.conflicts),
                "missing": list(self.missing), "rename_flagged": list(self.rename_flagged)}


def apply_decisions(state: ReviewState, *, batch_id: str, registry: Registry, queue_path: Path, data_dir: Path,
                    review_dir: Optional[Path] = None, dry_run: bool = False, by: Optional[str] = None,
                    graph_sha256: Optional[str] = None) -> ApplyReport:
    """Write the resolved groups into the registry and promote the nominees (section 3, "Apply").

    * every resolved member's ``review`` block becomes :func:`desired_blocks`'s (replaced whole, through
      :meth:`Registry.update_many`); a row this review wrote before (``review_batch``) that the log no longer
      resolves (an undo after an apply) is reset to unreviewed, and if it was promoted that is reported as a
      conflict (a promotion is not reversed here); so is a promoted row whose block is rewritten to anything but
      ``accepted`` (re-resolved after an undo, or another member nominated);
    * each promoted group's nominee goes through :func:`promote.promote` (the path of ``gap_registry.py promote``,
      by name, so ``allow_physical``: a physical pass's nominee joins the physical track, tagged ``physical``; and
      ``allow_released_states``: a row the states pass released is tagged ``states_pass`` and its route),
      once per group, unless it already has a ``seed_queue_stem``; its new seed-queue entry gets ``also_proposed``
      (the other resolved members' labels, the only addition to the queue format); the queue is saved once and the
      rows get ``seed_queue_stem``, as ``gap_registry.py promote`` does;
    * idempotent: a block already equal is not written and a promoted nominee is not promoted again;
    * the report carries :func:`rename_worklist`, the labels flagged for a rename in review, which the promotion
      report prints as a worklist (informational, so it is filled on a dry run too);
    * ``dry_run``: the same computation on a copy of the queue; nothing is written.
    A real run that changes something appends a record to ``<review_dir>/applied.jsonl``."""
    import data_analysis.seed_entities as se
    rows = registry.fold()
    rep = ApplyReport(dry_run=dry_run)
    desired = desired_blocks(state, batch_id)
    for key, block in desired.items():
        row = rows.get(key)
        if row is None:
            rep.missing.append(key)
        elif (row.get("review") or {}) == block:
            rep.unchanged += 1
        else:
            rep.review_writes[key] = block
            if row.get("seed_queue_stem") and block["status"] != "accepted":
                # a promoted row the log now resolves otherwise (an undo, then another resolution or nominee):
                # the block is rewritten, the queue entry is not removed here
                rep.conflicts.append(f"{key} was promoted as {row['seed_queue_stem']}, and this review now resolves "
                                     f"it {block['status']}" + (f" {block['into']}" if block.get("into") else "")
                                     + ": remove its seed-queue entry by hand if that is meant")
    for key, row in sorted(rows.items()):
        rv = row.get("review") or {}
        if rv.get("review_batch") == batch_id and key not in desired and rv.get("status") != "unreviewed":
            rep.resets.append(key)
            if rv.get("status") == "accepted" and row.get("seed_queue_stem"):
                rep.conflicts.append(f"{key} was promoted as {row['seed_queue_stem']} by this review, which no longer "
                                     "resolves it: remove its seed-queue entry by hand if that is meant")
    queue = se.load_queue(queue_path)
    work = copy.deepcopy(queue) if dry_run else queue
    for g in sorted((g for g in state.groups.values() if g.status == "resolved" and g.kind == "promote"),
                    key=lambda g: g.resolved_seq or 0):
        nom = g.nominated
        row = rows.get(nom)
        if row is None:
            continue
        if row.get("seed_queue_stem"):
            rep.already_promoted[nom] = row["seed_queue_stem"]
            continue
        # the nominee is named here, so a physical one is promoted into the physical track (physical_pass.py), and a
        # row the states pass released is promoted as such (states_pass.py)
        pr = promote_mod.promote(rows, work, [nom], data_dir=data_dir, dry_run=False, allow_physical=True,
                                 allow_released_states=True)
        if nom not in pr.promoted:
            rep.refused[nom] = pr.refused.get(nom, "refused")
            continue
        entry = next(e for e in reversed(work["entries"]) if (e.get("gap_gen") or {}).get("registry_key") == nom)
        also = [(rows.get(m) or {}).get("label") or state.label(m) for m in g.resolved_members if m != nom]
        entry["also_proposed"] = also
        rep.promotions.append({"group": g.id, "key": nom, "stem": entry["stem"], "also_proposed": also})
    # the worklist of labels flagged in review (QUESTIONS 71); informational, so it is reported on a dry run too
    rep.rename_flagged = rename_worklist(state, rows=rows, stems={p["key"]: p["stem"] for p in rep.promotions})
    if dry_run or not rep.changed:
        return rep
    updates = {k: {"review": b} for k, b in rep.review_writes.items()}
    updates.update({k: {"review": dict(UNREVIEWED)} for k in rep.resets})
    if updates:
        registry.update_many(updates, merge_blocks=False)
    if rep.promotions:
        se.save_queue(queue, queue_path)
        registry.update_many({p["key"]: {"seed_queue_stem": p["stem"]} for p in rep.promotions})
    if review_dir is not None:
        rec = {"at": utc_now(), "by": by, "batch_id": batch_id, "graph_sha256": graph_sha256,
               "registry": str(registry.path), "queue": str(queue_path)} | rep.as_dict()
        Path(review_dir).mkdir(parents=True, exist_ok=True)
        with open(Path(review_dir) / APPLIED_NAME, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rep


# --------------------------------------------------------------------------- the rename shortlist

def review_merges(rows: Iterable[Mapping], *, stem: Optional[str] = None, run_id: Optional[str] = None) -> list[dict]:
    """The candidates a review merged into a corpus trait or seed-queue entry (``review.status`` ``merged_into``,
    ``into`` ``trait:<stem>`` or ``queue:<stem>``), grouped under that stem, for ``gap_registry.py synonyms`` (decision
    5: "already have it" feeds the rename shortlist).  ``[{"stem", "kind": "corpus" | "queue", "candidates": [{"key",
    "label", "gloss", "by", "at", "note", "review_batch", "review_group"}]}]``, by stem, candidates by label.
    ``run_id``: only rows whose M3 block is that run's."""
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        rv = r.get("review") or {}
        if rv.get("status") != "merged_into":
            continue
        kind, _, st = str(rv.get("into") or "").partition(":")
        if kind not in ("trait", "queue") or not st or (stem is not None and st != stem):
            continue
        if run_id is not None and (r.get("novelty") or {}).get("run_id") != run_id:
            continue
        groups[(st, kind)].append({"key": r["key"], "label": r.get("label"), "gloss": r.get("gloss"),
                                   "by": rv.get("by"), "at": rv.get("at"), "note": rv.get("note"),
                                   "review_batch": rv.get("review_batch"), "review_group": rv.get("review_group")})
    return [{"stem": st, "kind": "corpus" if kind == "trait" else "queue",
             "candidates": sorted(c, key=lambda x: (str(x["label"]), x["key"]))}
            for (st, kind), c in sorted(groups.items())]
