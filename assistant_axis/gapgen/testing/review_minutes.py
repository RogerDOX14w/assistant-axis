"""Roger's review rate and the promote share, measured from the review app's records (plan 13 § 6, "Review rate";
decision 3).

The review app ([decisions.py](../review_app/decisions.py)) appends one event per action to a batch's
``decisions.jsonl``, each with its UTC time ``at``; ``apply`` writes ``applied.jsonl``, whose ``review_writes`` are
the registry rows the batch changed.  From those:

* a **review-minute** is one minute of active review: the sum of the gaps between consecutive events that are at
  most ``idle_s`` (five minutes); a longer gap is a break and counts nothing (:func:`active_minutes`);
* **terms decided** is ``review_writes`` (the last apply's); ``from_log`` (the distinct keys of ``resolve`` members
  and ``distinct`` keys, undone events left out) is the cross-check (:func:`terms_decided`);
* the **rate** is terms decided per active minute, computed from the minutes as recorded (one decimal), so that the
  record is self-consistent (:func:`review_rate`);
* **per-term times by shape** come from open-to-next-open spans: a singleton group's span, and a multi-member
  group's span divided over its members (``per_member_s``); a span with a break in it is left out
  (:func:`group_times`);
* the **promote share** is promote resolutions over resolved groups, a singleton a group of one (decision 3,
  Roger 2026-10-13), with the per-term share (accepted over decided terms) and the per-group share by shape beside
  it; a generator with fewer than :data:`MIN_DECIDED` decided terms takes the pooled share, flagged ``borrowed``
  (:func:`promote_share`).

A superseded log (``decisions.before_*.jsonl``, a log reset before a later pass) is listed, never counted.  A batch
with fewer than :data:`MIN_POOL_TERMS` terms (``review_states_v4``: 4) is reported and left out of the pooled rate.

Frozen interface (plan 13, "Frozen interface"): :class:`ReviewRate`, :func:`review_rate`,
:func:`pooled_review_rate`, :class:`PromoteShare`, :func:`promote_share`.  Fields are added, never renamed.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

IDLE_S = 300
#: A batch with fewer terms decided than this is reported but left out of the pooled rate.
MIN_POOL_TERMS = 50
#: A generator with fewer decided terms than this borrows the pooled promote share.
MIN_DECIDED = 50
LOG_NAME = "decisions.jsonl"
APPLIED_NAME = "applied.jsonl"
SUPERSEDED_GLOB = "decisions.*.jsonl"


@dataclass(frozen=True)
class Event:
    seq: int
    at: datetime
    action: str
    group: Optional[str]
    raw: dict

    @property
    def members(self) -> list[str]:
        return list(self.raw.get("members") or [])


def _parse(at: str) -> datetime:
    return datetime.fromisoformat(str(at).replace("Z", "+00:00"))


def load_events(batch_dir: Path, *, name: str = LOG_NAME, drop_undone: bool = True) -> list[Event]:
    """A batch's events in log order (``seq``), with the undo events and the events they undid left out unless
    ``drop_undone`` is false (the time an undone action took is still review time: :func:`active_minutes` reads
    every event)."""
    p = Path(batch_dir) / name
    if not p.exists():
        return []
    raw = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict) and "seq" in e and "action" in e and e.get("at"):
            raw.append(e)
    raw.sort(key=lambda e: e["seq"])
    if drop_undone:
        undone = {e.get("undoes") for e in raw if e["action"] == "undo"}
        raw = [e for e in raw if e["action"] != "undo" and e["seq"] not in undone]
    return [Event(int(e["seq"]), _parse(e["at"]), e["action"], e.get("group"), e) for e in raw]


def superseded_logs(batch_dir: Path) -> list[str]:
    """Logs beside ``decisions.jsonl`` that a reset replaced (listed, never counted)."""
    return sorted(p.name for p in Path(batch_dir).glob(SUPERSEDED_GLOB) if p.name != LOG_NAME)


def _gaps(events: Sequence[Event]) -> list[float]:
    ts = sorted(e.at for e in events)
    return [(ts[i + 1] - ts[i]).total_seconds() for i in range(len(ts) - 1)]


def active_minutes(events: Sequence[Event], *, idle_s: float = IDLE_S) -> float:
    """Minutes of active review: the gaps between consecutive events of at most ``idle_s``, summed."""
    return sum(g for g in _gaps(events) if g <= idle_s) / 60.0


def wall_minutes(events: Sequence[Event]) -> float:
    ts = sorted(e.at for e in events)
    return (ts[-1] - ts[0]).total_seconds() / 60.0 if len(ts) > 1 else 0.0


def idle_gaps(events: Sequence[Event], *, idle_s: float = IDLE_S) -> int:
    return sum(1 for g in _gaps(events) if g > idle_s)


@dataclass(frozen=True)
class TermsDecided:
    applied: Optional[int]          # the last apply's review_writes (None: never applied)
    from_log: int                   # distinct keys in resolve members and distinct keys
    promoted: Optional[int]         # the last apply's promoted terms


def terms_decided(batch_dir: Path, events: Optional[Sequence[Event]] = None) -> TermsDecided:
    """Terms decided by a batch: the last ``applied.jsonl`` record's ``review_writes`` and ``promoted`` (a dry run's
    record is skipped), and the log's own count as the cross-check."""
    ev = list(events) if events is not None else load_events(batch_dir)
    keys = set()
    for e in ev:
        if e.action == "resolve":
            keys |= set(e.members)
        elif e.action == "distinct":
            keys |= set(e.raw.get("keys") or [])
    applied = promoted = None
    p = Path(batch_dir) / APPLIED_NAME
    if p.exists():
        recs = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        recs = [r for r in recs if not r.get("dry_run")]
        if recs:
            applied = int(recs[-1].get("review_writes") or 0)
            promoted = len(recs[-1].get("promoted") or [])
    return TermsDecided(applied=applied, from_log=len(keys), promoted=promoted)


@dataclass(frozen=True)
class GroupTimes:
    singleton_median_s: Optional[float]
    singleton_mean_s: Optional[float]
    multi_median_s: Optional[float]
    per_member_s: Optional[float]
    n_singletons: int
    n_groups: int
    n_left_out: int = 0             # spans with a break in them

    def as_dict(self) -> dict:
        return asdict(self)


def group_spans(events: Sequence[Event], *, idle_s: float = IDLE_S) -> list[tuple[int, float, bool]]:
    """Per ``open`` event: ``(members, seconds to the next open (the last: to the last event), has_break)``."""
    ev = sorted(events, key=lambda e: e.seq)
    opens = [i for i, e in enumerate(ev) if e.action == "open"]
    out = []
    for j, i in enumerate(opens):
        end = opens[j + 1] if j + 1 < len(opens) else len(ev) - 1
        seg = ev[i:end + 1]
        gaps = _gaps(seg)
        out.append((len(ev[i].members), (ev[end].at - ev[i].at).total_seconds(), any(g > idle_s for g in gaps)))
    return out


def group_times(events: Sequence[Event], *, idle_s: float = IDLE_S) -> GroupTimes:
    """Times by group shape from open-to-next-open spans (module docstring); spans with a break are left out."""
    spans = group_spans(events, idle_s=idle_s)
    single = [s for n, s, brk in spans if n == 1 and not brk]
    multi = [(n, s) for n, s, brk in spans if n > 1 and not brk]
    return GroupTimes(
        singleton_median_s=statistics.median(single) if single else None,
        singleton_mean_s=statistics.mean(single) if single else None,
        multi_median_s=statistics.median([s for _, s in multi]) if multi else None,
        per_member_s=(sum(s for _, s in multi) / sum(n for n, _ in multi)) if multi else None,
        n_singletons=sum(1 for n, _, _ in spans if n == 1), n_groups=len(spans),
        n_left_out=sum(1 for _, _, brk in spans if brk))


@dataclass(frozen=True)
class ReviewRate:
    """One batch's measured review rate (the frozen interface; fields added, never renamed)."""
    batch_id: str
    active_minutes: float
    terms_applied: Optional[int]
    terms_per_active_minute: Optional[float]
    singleton_mean_s: Optional[float]
    per_member_s: Optional[float]
    promoted: Optional[int]
    wall_minutes: float = 0.0
    n_events: int = 0
    pooled: bool = True             # whether the batch counts in the pooled rate

    def as_dict(self) -> dict:
        return asdict(self)


def _r(x: Optional[float], nd: int) -> Optional[float]:
    return None if x is None else round(float(x), nd)


def review_rate(batch_dir: Path, *, idle_s: float = IDLE_S) -> ReviewRate:
    """:class:`ReviewRate` of one batch directory (its ``decisions.jsonl`` and ``applied.jsonl``)."""
    batch_dir = Path(batch_dir)
    all_ev = load_events(batch_dir, drop_undone=False)
    ev = load_events(batch_dir)
    mins = round(active_minutes(all_ev, idle_s=idle_s), 1)
    td = terms_decided(batch_dir, ev)
    gt = group_times(ev, idle_s=idle_s)
    terms = td.applied if td.applied is not None else td.from_log
    return ReviewRate(batch_id=batch_dir.name, active_minutes=mins, terms_applied=td.applied,
                      terms_per_active_minute=_r(terms / mins, 2) if mins and terms else None,
                      singleton_mean_s=_r(gt.singleton_mean_s, 1), per_member_s=_r(gt.per_member_s, 1),
                      promoted=td.promoted, wall_minutes=round(wall_minutes(all_ev), 1), n_events=len(all_ev),
                      pooled=bool(terms and terms >= MIN_POOL_TERMS))


def review_record(batch_dir: Path, *, idle_s: float = IDLE_S) -> dict:
    """The full ``review_rates.json`` record of one batch (plan 13 § 6)."""
    batch_dir = Path(batch_dir)
    all_ev = load_events(batch_dir, drop_undone=False)
    ev = load_events(batch_dir)
    rate = review_rate(batch_dir, idle_s=idle_s)
    td = terms_decided(batch_dir, ev)
    gt = group_times(ev, idle_s=idle_s)
    opens = [e for e in ev if e.action == "open"]
    resolves = [e for e in ev if e.action == "resolve"]
    mins = rate.active_minutes
    terms = td.applied if td.applied is not None else td.from_log
    return {
        "batch_id": batch_dir.name, "events": len(all_ev),
        "events_counted": len(ev), "undone": len(all_ev) - len(ev),
        "first_at": min(e.at for e in all_ev).isoformat() if all_ev else None,
        "last_at": max(e.at for e in all_ev).isoformat() if all_ev else None,
        "wall_minutes": rate.wall_minutes, "active_minutes": mins, "idle_s": idle_s,
        "idle_gaps": idle_gaps(all_ev, idle_s=idle_s),
        "terms": {"applied": td.applied, "from_log": td.from_log, "promoted": td.promoted},
        "groups": {"opened": len(opens), "singletons": sum(1 for e in opens if len(e.members) == 1),
                   "multi": sum(1 for e in opens if len(e.members) > 1), "members": sum(len(e.members) for e in opens),
                   "resolved": len(resolves),
                   "resolutions": dict(sorted(Counter(str(e.raw.get("resolution") or "").split(":")[0]
                                                      for e in resolves).items())),
                   "distinct_events": sum(1 for e in ev if e.action == "distinct"),
                   "extend_events": sum(1 for e in ev if e.action == "extend")},
        "times": {"singleton_median_s": _r(gt.singleton_median_s, 1), "singleton_mean_s": _r(gt.singleton_mean_s, 1),
                  "multi_median_s": _r(gt.multi_median_s, 1), "per_member_s": _r(gt.per_member_s, 1),
                  "spans_left_out": gt.n_left_out},
        "rate": {"terms_per_active_minute": rate.terms_per_active_minute,
                 "terms_per_hour_active": _r(terms / mins * 60, 0) if mins and terms else None,
                 "terms_per_hour_wall": _r(terms / rate.wall_minutes * 60, 0) if rate.wall_minutes and terms else None,
                 "accepted_per_active_minute": _r((td.promoted or 0) / mins, 2) if mins else None},
        "pooled": rate.pooled,
        "superseded_logs": superseded_logs(batch_dir),
    }


def review_batch_dirs(review_root: Path) -> list[Path]:
    """Every review batch with a ``decisions.jsonl`` (sorted)."""
    return sorted(p.parent for p in Path(review_root).glob(f"*/{LOG_NAME}"))


@dataclass(frozen=True)
class PooledRate:
    batches: tuple[str, ...]
    active_minutes: float
    terms: int
    terms_per_active_minute: Optional[float]
    singleton_mean_s: Optional[float]
    per_member_s: Optional[float]
    promoted: int
    left_out: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return asdict(self)


def pooled_review_rate(batch_dirs: Iterable[Path], *, idle_s: float = IDLE_S) -> PooledRate:
    """The rate over the batches worth pooling (at least :data:`MIN_POOL_TERMS` terms decided): terms over
    minutes, and the span times over every pooled span."""
    used, left, mins, terms, promoted = [], [], 0.0, 0, 0
    single, multi = [], []
    for d in batch_dirs:
        r = review_rate(d, idle_s=idle_s)
        if not r.pooled:
            left.append(r.batch_id)
            continue
        used.append(r.batch_id)
        mins += r.active_minutes
        terms += r.terms_applied if r.terms_applied is not None else terms_decided(d).from_log
        promoted += r.promoted or 0
        for n, s, brk in group_spans(load_events(d), idle_s=idle_s):
            if brk:
                continue
            (single if n == 1 else multi).append((n, s))
    return PooledRate(batches=tuple(used), active_minutes=round(mins, 1), terms=terms,
                      terms_per_active_minute=_r(terms / mins, 2) if mins else None,
                      singleton_mean_s=_r(statistics.mean(s for _, s in single), 1) if single else None,
                      per_member_s=_r(sum(s for _, s in multi) / sum(n for n, _ in multi), 1) if multi else None,
                      promoted=promoted, left_out=tuple(left))


# --------------------------------------------------------------------------- the promote share (decision 3)

@dataclass(frozen=True)
class Resolution:
    """One effective ``resolve``: its members as resolved (the group's shape is read from these) and the keys later
    ``extend`` events added under the same resolution (``extended``; they count as the group's terms, not its
    shape)."""
    batch_id: str
    group: str
    members: tuple[str, ...]
    kind: str                       # promote | merge_into | reject | park | defer
    extended: tuple[str, ...] = ()

    @property
    def promoted(self) -> bool:
        return self.kind == "promote"

    @property
    def all_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.members + self.extended))


def load_resolutions(batch_dirs: Iterable[Path]) -> list[Resolution]:
    """Every effective ``resolve`` of the batches' logs (an undone one left out: the group was resolved again), with
    the keys of the group's ``extend`` events beside its members."""
    out = []
    for d in batch_dirs:
        ev = load_events(d)
        ext: dict[str, list[str]] = {}
        for e in ev:
            if e.action == "extend" and e.group:
                ext.setdefault(e.group, []).extend(e.raw.get("keys") or [])
        for e in ev:
            if e.action == "resolve":
                kind = str(e.raw.get("resolution") or "").split(":")[0]
                out.append(Resolution(Path(d).name, e.group or "", tuple(e.members), kind,
                                      tuple(k for k in dict.fromkeys(ext.get(e.group, [])) if k not in e.members)))
    return out


@dataclass(frozen=True)
class PromoteShare:
    """Decision 3: ``per_group`` is the share the stop rule uses; ``per_term`` beside it (the frozen interface)."""
    per_term: Optional[float]
    per_group: Optional[float]
    n_decided: int
    borrowed: bool = False
    n_groups: int = 0
    n_promoted_groups: int = 0
    by_shape: dict = field(default_factory=dict)    # {"singleton": {"resolved", "promoted", "share"}, "multi": {...}}
    n_accepted: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _share(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


#: The review statuses that settle a term (``decisions.HANDLED_ELSEWHERE``).
SETTLED = ("accepted", "merged_into", "rejected")
#: M3's decisions that make a row a review term (the rows the review graph presents as terms).
TERM_DECISIONS = ("new", "grey")


def _decided_counts(rows: Iterable[Mapping]) -> tuple[int, int]:
    """(decided, accepted) over the review's terms (rows M3 kept): a settling review status (accepted,
    merged_into, rejected).  A covered candidate pulled into a group by hand is decided too, but is not a term of
    the review's queue, so it is left out of the per-term share (33 such rows on 2026-10-13)."""
    dec = acc = 0
    for r in rows:
        st = (r.get("review") or {}).get("status")
        if st in SETTLED and (r.get("novelty") or {}).get("decision") in TERM_DECISIONS:
            dec += 1
            acc += st == "accepted"
    return dec, acc


def _group_figures(resolutions: Sequence[Resolution]) -> tuple[int, int, dict]:
    shape: dict = {"singleton": Counter(), "multi": Counter()}
    for r in resolutions:
        s = "singleton" if len(r.members) == 1 else "multi"
        shape[s]["resolved"] += 1
        shape[s]["promoted"] += r.promoted
        shape[s]["terms"] += len(r.members)
        shape[s]["extended"] += len(r.extended)
    by = {k: {"resolved": v["resolved"], "promoted": v["promoted"], "terms": v["terms"], "extended": v["extended"],
              "share": _share(v["promoted"], v["resolved"])} for k, v in shape.items()}
    return len(resolutions), sum(r.promoted for r in resolutions), by


def pooled_promote_share(rows: Mapping[str, Mapping], resolutions: Sequence[Resolution]) -> PromoteShare:
    """Over every decided term and every resolved group."""
    dec, acc = _decided_counts(rows.values())
    n, p, by = _group_figures(resolutions)
    return PromoteShare(per_term=_share(acc, dec), per_group=_share(p, n), n_decided=dec, borrowed=False, n_groups=n,
                        n_promoted_groups=p, by_shape=by, n_accepted=acc)


def promote_share(rows: Mapping[str, Mapping], *, generator: str, resolutions: Sequence[Resolution],
                  generators_of=None, pooled: Optional[PromoteShare] = None) -> PromoteShare:
    """A generator's promote share: per group over the resolved groups with at least one of its terms, per term over
    its decided terms; under :data:`MIN_DECIDED` decided terms the pooled share's figures are used, ``borrowed``
    (the generator's own counts stay in ``n_decided`` and ``by_shape``).  ``generators_of(row)``: the generators a row
    counts for (default :func:`independence.generators_of` over ``rows``, states-pass rows attributed)."""
    from . import independence as IND
    gof = generators_of or (lambda r: IND.generators_of(r, rows))
    mine = {k for k, r in rows.items() if generator in gof(r)}
    dec, acc = _decided_counts(rows[k] for k in mine)
    res = [r for r in resolutions if set(r.all_keys) & mine]
    n, p, by = _group_figures(res)
    if dec < MIN_DECIDED:
        pooled = pooled or pooled_promote_share(rows, resolutions)
        return PromoteShare(per_term=pooled.per_term, per_group=pooled.per_group, n_decided=dec, borrowed=True,
                            n_groups=n, n_promoted_groups=p, by_shape=by, n_accepted=acc)
    return PromoteShare(per_term=_share(acc, dec), per_group=_share(p, n), n_decided=dec, borrowed=False, n_groups=n,
                        n_promoted_groups=p, by_shape=by, n_accepted=acc)


__all__ = ["IDLE_S", "MIN_POOL_TERMS", "MIN_DECIDED", "Event", "load_events", "superseded_logs", "active_minutes",
           "wall_minutes", "idle_gaps", "TermsDecided", "terms_decided", "GroupTimes", "group_spans", "group_times",
           "ReviewRate", "review_rate", "review_record", "review_batch_dirs", "PooledRate", "pooled_review_rate",
           "Resolution", "load_resolutions", "PromoteShare", "promote_share", "pooled_promote_share"]
