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
  handled term) returns that group and logs nothing.
* ``accept`` (``group``): a proposed group becomes the working group (key ``g``); drops before it are kept.
* ``drop`` (``group``, ``key``): never the last member.
* ``merge_in`` (``group``, ``keys``): a singleton or a merged group's members; a covered candidate may be pulled in by
  hand (decision 9); handled terms and members already in are left out, and the event records what was added.
* ``nominate`` (``group``, ``key``): the suggested label; not a covered or handled member.
* ``resolve`` (``group``, ``resolution``, ``note``?): ``promote`` (the nominee; a group with one unhandled term
  nominates it by default), ``merge_into:<trait:stem | queue:stem>``, ``park``, ``reject``, ``defer``.  Only an open
  (accepted) group resolves.  The event records the members it resolves: those not already handled.
* ``start_antonym`` (``of``, ``keys``): a new open group meant as the antonym of a resolved group that has none.
* ``undo`` (``seq``?): reverses the last effective event (only the last; undo again to walk back).

**Replay**: the state is the log replayed from the start, the undone events and the undo events left out; an event
the graph no longer supports (a rebuilt graph) is skipped and listed in ``ReviewState.skipped``.  A term is
**handled** once a group containing it is resolved; a term in two groups is handled by the first resolution and
shown so in the other.

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
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.registry import Registry, utc_now

logger = logging.getLogger(__name__)

LOG_NAME = "decisions.jsonl"
APPLIED_NAME = "applied.jsonl"
GRAPH_NAME = "graph.json"
ACTIONS = ("open", "accept", "drop", "merge_in", "nominate", "resolve", "start_antonym", "undo")
RESOLUTIONS = ("promote", "merge_into", "park", "reject", "defer")
#: The registry ``review.status`` each resolution writes (``merged_into`` and ``parked`` are new to the platform
#: plan's vocabulary; the plan's ``merged`` is written as ``merged_into`` with ``into``, as section 3 says).
REVIEW_STATUS = {"promote": "accepted", "merge_into": "merged_into", "park": "parked", "reject": "rejected",
                 "defer": "deferred"}
UNREVIEWED = {"status": "unreviewed", "by": None, "at": None, "note": None}
ORDERS = ("cliques", "generator", "region")
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


def edge_level(e: RG.Edge) -> int:
    """How strongly an edge ties its ends: 4 for a 4-edge, 3 for a 3-edge, else the best final reading (0 unread)."""
    if e.strict:
        return 4
    if e.proposed:
        return 3
    vals = [v for v in (_final(e.readings.get("ab")), _final(e.readings.get("ba"))) if v is not None]
    return max(vals) if vals else 0


def _mode(values: Iterable[Optional[str]]) -> Optional[str]:
    c = Counter(v for v in values if v)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if c else None


def _parse_at(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


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
    source: str                         # merged:<i> | proposed:<i> | term:<key> | antonym:<group>
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
    antonym_of: Optional[str] = None

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
    for display only (M1 tags, the review block already applied); ``targets``: merge targets beyond the graph's own
    corpus and queue nodes (:func:`corpus_targets`), with ``labels``."""

    def __init__(self, graph: RG.Graph, *, rows: Optional[Mapping[str, Mapping]] = None,
                 targets: Optional[Iterable[str]] = None, labels: Optional[Mapping[str, str]] = None):
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
        self.labels = dict(labels or {})
        self.targets = set(targets or ()) | {n.key for n in graph.nodes
                                             if n.kind in ("corpus", "queue") and not n.missing}
        self.groups: dict[str, Group] = {}
        self.handled: dict[str, str] = {}
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

    # -- lookups --------------------------------------------------------------------
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
            return {"existing": done[-1].id if done else self.handled[members[0]]}
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
                why.append(f"{x} is handled ({self.handled[x]})")
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
            raise ActionError(f"{key} is handled ({self.handled[key]}): nominate an unhandled member")
        return {"group": g.id, "action": "nominate", "key": key}

    def _check_resolve(self, req: Mapping) -> dict:
        g = self._live(req)
        if g.status == "proposed":
            raise ActionError(f"{g.id} is a proposed group: accept it first (g), dropping members before if needed")
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
                    raise ActionError(f"{g.id} has {len(terms)} unhandled terms: nominate one first (n)")
                nominated = terms[0]
        note = req.get("note")
        return {"group": g.id, "action": "resolve", "members": members, "nominated": nominated,
                "resolution": resolution, "note": str(note) if note else None}

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

    def _check_undo(self, req: Mapping) -> dict:
        if not self.applied:
            raise ActionError("nothing to undo")
        last = self.applied[-1]
        if req.get("seq") is not None and int(req["seq"]) != last["seq"]:
            raise ActionError(f"only the last decision can be undone (seq {last['seq']}, {last['action']}); "
                              "undo again to go further back")
        return {"group": last.get("group"), "action": "undo", "undoes": last["seq"]}

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
        if not keys or any(not self.is_candidate(x) or x in g.members or x in self.handled for x in keys):
            raise ActionError(f"merge_in: {keys} cannot be merged into {g.id}")
        g.members.extend(keys)

    def _apply_nominate(self, ev: Mapping) -> None:
        g = self._live(ev)
        key = ev.get("key")
        if key not in g.members or key not in self.kept_set or key in self.handled:
            raise ActionError(f"nominate: {key} cannot be nominated in {g.id}")
        g.nominated = key

    def _apply_resolve(self, ev: Mapping) -> None:
        g = self._live(ev)
        members = list(ev.get("members") or [])
        kind = str(ev.get("resolution") or "").split(":", 1)[0]
        if g.status != "open" or kind not in RESOLUTIONS or not members or \
                any(m not in g.members or m in self.handled for m in members):
            raise ActionError(f"resolve: {g.id} cannot be resolved as logged")
        if kind == "promote" and ev.get("nominated") not in members:
            raise ActionError(f"resolve: the nominee {ev.get('nominated')} is not among the members resolved")
        g.status, g.resolution, g.resolved_members = "resolved", ev["resolution"], members
        g.nominated = ev.get("nominated") if kind == "promote" else g.nominated
        g.note, g.resolved_seq, g.resolved_at, g.resolved_by = ev.get("note"), ev.get("seq"), ev.get("at"), ev.get("by")
        for m in members:
            self.handled[m] = g.id

    def _apply_start_antonym(self, ev: Mapping) -> None:
        gid, of, members = ev.get("group"), ev.get("of"), list(ev.get("members") or [])
        if not gid or gid in self.groups or of not in self.groups or self.groups[of].status != "resolved":
            raise ActionError(f"start_antonym: cannot start {gid} as the antonym of {of}")
        if not members or any(m not in self.kept_set or m in self.handled for m in members):
            raise ActionError(f"start_antonym: members {members} cannot open")
        self.groups[gid] = Group(id=gid, source=f"antonym:{of}", members=members, status="open",
                                 opened_seq=ev.get("seq", 0), opened_at=ev.get("at", ""), by=ev.get("by"),
                                 antonym_of=of)

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
        return {"id": s["id"], "tier": s["tier"], "source": s["source"], "members": list(members),
                "labels": [n.label for n in nodes], "size": len(members), "handled": handled,
                "remaining": len(members) - handled, "status": status, "group": live[-1].id if live else None,
                "generator": _mode(n.generator for n in nodes) or "", "region": _mode(n.region for n in nodes) or "",
                "flags": sorted({f for n in nodes for f in n.flags})}

    def queue(self, order: str = "cliques") -> list[dict]:
        """Every merged group, proposed group and singleton as a queue item, in ``order``: ``cliques`` (groups
        largest first, merged before proposed at a size; then singletons by generator, region and label),
        ``generator`` or ``region`` (by the members' commonest generator or region, then tier and size)."""
        if order not in ORDERS:
            raise ActionError(f"order must be one of {', '.join(ORDERS)}")
        items = [self._item(s) for s in self.seeds()]
        tier_rank = {t: i for i, t in enumerate(TIERS)}
        idx = {it["id"]: s["index"] for it, s in zip(items, self.seeds())}
        if order == "cliques":
            def key(it):
                if it["tier"] == "single":
                    return (1, 0, 0, it["generator"], it["region"], it["labels"][0])
                return (0, -it["size"], tier_rank[it["tier"]], "", "", f"{idx[it['id']]:06d}")
        else:
            def key(it):
                return (it[order], tier_rank[it["tier"]], -it["size"], it["labels"][0], it["id"])
        return sorted(items, key=key)

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
    def member_card(self, key: str) -> dict:
        n = self.nodes[key]
        row = self.rows.get(key) or {}
        f = row.get("filter") or {}
        rv = row.get("review") or {}
        # the tags are M1's; a physical pass's node says physical even where the registry row has none
        tags = list(dict.fromkeys(list(f.get("tags") or []) + ([n.outcome] if n.outcome else [])))
        out = {"key": key, "label": n.label, "gloss": n.gloss, "generator": n.generator, "generators": list(n.generators),
               "region": n.region, "alignment_score": n.alignment_score, "tags": tags,
               "membership_kind": f.get("membership_kind"), "m3_decision": n.decision, "m3_run": n.m3_run,
               "flags": list(n.flags), "covered": key in self.covered,
               "merged": [f"m{i}" for i in self.in_merged.get(key, [])],
               "proposed": [f"p{i}" for i in self.in_proposed.get(key, [])],
               "handled_by": self.handled.get(key), "handled_resolution": None,
               "applied": rv.get("status") if rv.get("status") not in (None, "unreviewed") else None,
               "seed_queue_stem": row.get("seed_queue_stem")}
        if out["handled_by"]:
            out["handled_resolution"] = self.groups[out["handled_by"]].resolution
        if n.covered_by:
            path, href = target_path(n.covered_by)
            out["covered_by"] = {"key": n.covered_by, "label": self.label(n.covered_by), "path": path, "href": href,
                                 "reading": n.covered_reading}
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
                "handled_by": self.handled.get(key), "covered": key in self.covered}

    def _with_group(self, key: str, members: set) -> list[str]:
        """What ``m`` (merge in) or ``a`` (start the antonym group) takes for a neighbour: its largest merged group's
        unhandled terms not already in, else the term alone (nothing if it is handled)."""
        if key in self.handled:
            return []
        if self.in_merged.get(key):
            best = min(self.in_merged[key], key=lambda i: (-len(self.merged[i]), i))
            return [m for m in self.merged[best] if m not in self.handled and m not in members] or [key]
        return [key]

    def neighbourhood(self, members: Sequence[str]) -> dict:
        """The neighbours of a set of members: ``neighbours`` (candidates by their strongest non-opposed edge to the
        set: 4-edge, 3-edge, best reading, then the relation (similar, unsure, unrelated), then cosine), ``corpus``
        (corpus and queue traits from the members' M3
        readings, by reading then cosine, each with the covered candidates it covers, greyed), ``opposed``
        (candidates, then corpus and queue traits, joined by an opposed edge, by cosine)."""
        S = set(members)
        best: dict[str, tuple] = {}
        opp: dict[str, tuple] = {}
        for m in members:
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
        for m in members:
            for e in self.m3.get(m, []):
                rd = e.readings.get("ab")
                if e.relation == "opposed":
                    if e.b not in opp_t or (e.cosine or 0) > (opp_t[e.b][0] or 0):
                        opp_t[e.b] = (e.cosine, m, e)
                    continue
                rank = (_final(rd) if _final(rd) is not None else -1, e.cosine or 0.0)
                if e.b not in corpus or rank > corpus[e.b][0]:
                    corpus[e.b] = (rank, m, e)
        corpus_out = []
        for t, (rank, m, e) in sorted(corpus.items(), key=lambda kv: (-kv[1][0][0], -kv[1][0][1], kv[0])):
            covered = []
            for c in self.covers.get(t, []):
                rd = self.nodes[c].covered_reading or {}
                item = {"key": c, "label": self.nodes[c].label,
                        "reading": f"{rd.get('sonnet')}/{rd.get('opus') if rd.get('opus') is not None else '-'}"}
                if c in self.handled:
                    item["handled_by"] = self.handled[c]
                covered.append(item)
            corpus_out.append(self._target_entry(t) | {
                "relation": e.relation, "cosine": e.cosine, "reading": _dir_text(e.readings.get("ab")),
                "level": rank[0], "via": m, "via_label": self.nodes[m].label, "covered": covered})
        opposed = []
        for o, (cos, m, e) in sorted(opp.items(), key=lambda kv: (-(kv[1][0] or 0), kv[0])):
            opposed.append(self._term_entry(o) | {"cosine": cos, "via": m, "via_label": self.nodes[m].label,
                                                  "antonym_keys": self._with_group(o, S)})
        for t, (cos, m, e) in sorted(opp_t.items(), key=lambda kv: (-(kv[1][0] or 0), kv[0])):
            opposed.append(self._target_entry(t) | {"cosine": cos, "via": m, "via_label": self.nodes[m].label})
        return {"neighbours": neighbours, "corpus": corpus_out, "opposed": opposed}

    def group_card(self, gid: str) -> dict:
        """Everything the page shows for one working group."""
        if gid not in self.groups:
            raise KeyError(gid)
        g = self.groups[gid]
        own = {"merged": g.source.split(":", 1)[1] if g.source.startswith("merged:") else None,
               "proposed": g.source.split(":", 1)[1] if g.source.startswith("proposed:") else None}
        S = set(g.members)
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
                "antonym_of": g.antonym_of, "antonym_groups": self.antonym_groups(g.id),
                "neighbour_groups": others}
        if g.resolution and g.target:
            card["target"] = self._target_entry(g.target)
        return card | self.neighbourhood(g.members)

    def term_card(self, key: str) -> dict:
        """The ego view: the term and everything one edge away (candidate and corpus edges, by cosine)."""
        if key not in self.nodes or self.nodes[key].kind != "candidate":
            raise KeyError(key)
        edges = []
        for e in self.r1.get(key, []):
            o = e.b if e.a == key else e.a
            edges.append({"key": o, "kind": "candidate", "label": self.nodes[o].label, "relation": e.relation,
                          "cosine": e.cosine, "readings": readings_text(e), "strict": e.strict,
                          "proposed_edge": e.proposed, "handled_by": self.handled.get(o)})
        for e in self.m3.get(key, []):
            edges.append(self._target_entry(e.b) | {"relation": e.relation, "cosine": e.cosine,
                                                    "readings": _dir_text(e.readings.get("ab")) or ""})
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
            out.append(item)
        return out

    # -- status -------------------------------------------------------------------------
    def status(self, events: Sequence[Mapping]) -> dict:
        """Groups resolved and open, decisions by type, and time per decision (from the events' timestamps)."""
        resolved = [g for g in self.groups.values() if g.status == "resolved"]
        per_group = []
        for g in resolved:
            a, b = _parse_at(g.opened_at), _parse_at(g.resolved_at or "")
            if a and b:
                per_group.append((b - a).total_seconds() / 60.0)
        times = sorted(t for t in (_parse_at(e.get("at", "")) for e in events) if t is not None)
        gaps = [(b - a).total_seconds() / 60.0 for a, b in zip(times, times[1:])]
        active = sum(x for x in gaps if x <= IDLE_MINUTES)
        return {"events": len(events), "effective_events": len(self.applied), "skipped": len(self.skipped),
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


def replay(graph: RG.Graph, events: Sequence[Mapping], *, rows=None, targets=None, labels=None) -> ReviewState:
    """The state the events give: undo events and the events they undo left out, the rest applied in order; an
    event that no longer applies (the graph was rebuilt) is skipped and listed in ``skipped``."""
    st = ReviewState(graph, rows=rows, targets=targets, labels=labels)
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
                 clock: Optional[Callable[[], str]] = None, rows=None, targets=None, labels=None):
        self.path = Path(path)
        self.graph = graph
        self.graph_sha256 = graph_sha256
        self.by = by
        self.clock = clock or utc_now
        self.rows, self.targets, self.labels = dict(rows or {}), set(targets or ()), dict(labels or {})
        self.lock = threading.RLock()
        self.events = read_events(self.path)
        self.state = self._replay()

    @classmethod
    def open(cls, review_dir: Path, *, by: str = "roger", clock=None, data_dir: Optional[Path] = None,
             registry_path: Optional[Path] = None, queue_path: Optional[Path] = None) -> "DecisionLog":
        """The log of a review batch's directory (``graph.json`` must be there)."""
        review_dir = Path(review_dir)
        gp = review_dir / GRAPH_NAME
        if not gp.exists():
            raise FileNotFoundError(f"{gp} not found: build the graph first (review_graph.py build)")
        raw = gp.read_bytes()
        graph = RG.Graph.from_json(json.loads(raw))
        rows = Registry(registry_path).fold() if registry_path and Path(registry_path).exists() else {}
        targets, labels = corpus_targets(data_dir, queue_path)
        return cls(review_dir / LOG_NAME, graph, graph_sha256=hashlib.sha256(raw).hexdigest(), by=by, clock=clock,
                   rows=rows, targets=targets, labels=labels)

    def _replay(self) -> ReviewState:
        return replay(self.graph, self.events, rows=self.rows, targets=self.targets, labels=self.labels)

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
                self.state.apply(ev)
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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
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
        if g.antonym_of:
            base["antonym_of"] = g.antonym_of
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
        lines.append(f"{len(self.review_writes)} review blocks to write, {len(self.resets)} to reset, "
                     f"{self.unchanged} unchanged, {len(self.promotions)} promotions"
                     + ("" if self.changed else "; nothing to write"))
        return "\n".join(lines)

    def as_dict(self) -> dict:
        return {"dry_run": self.dry_run, "review_writes": len(self.review_writes), "unchanged": self.unchanged,
                "resets": list(self.resets), "promoted": [p["key"] for p in self.promotions],
                "promotions": list(self.promotions), "refused": dict(self.refused),
                "already_promoted": dict(self.already_promoted), "conflicts": list(self.conflicts),
                "missing": list(self.missing)}


def apply_decisions(state: ReviewState, *, batch_id: str, registry: Registry, queue_path: Path, data_dir: Path,
                    review_dir: Optional[Path] = None, dry_run: bool = False, by: Optional[str] = None,
                    graph_sha256: Optional[str] = None) -> ApplyReport:
    """Write the resolved groups into the registry and promote the nominees (section 3, "Apply").

    * every resolved member's ``review`` block becomes :func:`desired_blocks`'s (replaced whole, through
      :meth:`Registry.update_many`); a row this review wrote before (``review_batch``) that the log no longer
      resolves (an undo after an apply) is reset to unreviewed, and if it was promoted that is reported as a
      conflict (a promotion is not reversed here);
    * each promoted group's nominee goes through :func:`promote.promote` (the path of ``gap_registry.py promote``,
      by name, so ``allow_physical``: a physical pass's nominee joins the physical track, tagged ``physical``),
      once per group, unless it already has a ``seed_queue_stem``; its new seed-queue entry gets ``also_proposed``
      (the other resolved members' labels, the only addition to the queue format); the queue is saved once and the
      rows get ``seed_queue_stem``, as ``gap_registry.py promote`` does;
    * idempotent: a block already equal is not written and a promoted nominee is not promoted again;
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
        # the nominee is named here, so a physical one is promoted into the physical track (physical_pass.py)
        pr = promote_mod.promote(rows, work, [nom], data_dir=data_dir, dry_run=False, allow_physical=True)
        if nom not in pr.promoted:
            rep.refused[nom] = pr.refused.get(nom, "refused")
            continue
        entry = next(e for e in reversed(work["entries"]) if (e.get("gap_gen") or {}).get("registry_key") == nom)
        also = [(rows.get(m) or {}).get("label") or state.label(m) for m in g.resolved_members if m != nom]
        entry["also_proposed"] = also
        rep.promotions.append({"group": g.id, "key": nom, "stem": entry["stem"], "also_proposed": also})
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
