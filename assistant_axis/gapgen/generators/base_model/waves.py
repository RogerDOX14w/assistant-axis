"""The review-hour waves of a base-model run: which net-new rows each wave submits (plan 03, decision (f)).

**Count no longer orders the waves** (Roger, 2026-10-13: "I would expect count to be correlated with corpus
membership, and perhaps anticorrelated with novelty.  So I agree, it may not be a good way to prioritize.").  The
count stays on the row and in ``Candidate.score``; it chooses only the row's **count bucket**.

* **Cells.**  A row's cell is ``<count bucket>|<home family>``: the buckets are ``2``, ``3``, ``4-9`` and ``10+``
  (:data:`COUNT_BUCKETS`; a count of 1, reachable only with ``--min-count 1``, is bucket ``1``), the families the six
  prompt families, so 24 cells at the default floor.
* **The home family of a row several families emitted** (:func:`home_family`): the family that emitted it most
  often; a tie goes to the family with the fewest emissions over the whole table (the rarer family, so the small
  cells fill), then to the order of ``prompts.FAMILIES``.  Every row has exactly one cell, which the wave records
  (``run.json`` ``args.selection.counted``), so the measured rate of a cell is over the rows that wave put in it.
  The totals are the table's, not the registry's, so a row's cell is the same in every wave.
* **Net-new** (:func:`row_status`), the test of the structural and masked-LM generators: not a corpus stem (or a
  former name, ``renamed_from``), not in the seed queue, not decided by the registry (an M1 verdict other than
  ``trait``, or ``trait`` with an M3 block: ``structural.postprocess.is_decided``), **and not already submitted by
  an earlier wave** of this generator (its pending rows must not be drawn twice).  One difference: a frequency-floor
  free reject is not a decision here, because M1 takes such a row again once a source rescues it (gate audit 1, F3;
  ``submit.downstream_need`` counts it the same way).
* **The first wave** (``--order stratified``, the default while no wave is measured): ``need = ceil(kept_target /
  kept_share)`` net-new rows drawn **evenly** across the cells (:func:`even_quotas`: each cell the same quota, a cell
  that runs short giving the rest to the others, the remainder of the division going one row each to cells in a
  seeded order).
* **Later waves** (``--order measured``): the cells ranked by their **measured new-kept rate** (:func:`measure_cells`:
  over the net-new rows earlier waves submitted, those M3 kept, ``new`` or ``grey``, among those M1 and M3 have
  decided), filling from the best cell down.  A cell with fewer than ``min_measured`` decided rows is ranked at the
  pooled rate of all cells (so it neither leads on two lucky rows nor is starved); refused when no wave has
  anything decided.
* **Within a cell** the rows are in a stable seeded shuffle (sha256 of ``<seed>:<stem>``), never by count.

Nothing here reads a file or calls a model; :mod:`.submit` wires it in and :mod:`.evaluate` reports the rates.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from .prompts import FAMILIES

#: ``(name, lowest count, highest count or None)``: the four count buckets of decision (f).
COUNT_BUCKETS = (("2", 2, 2), ("3", 3, 3), ("4-9", 4, 9), ("10+", 10, None))
BUCKET_NAMES = ("1",) + tuple(b[0] for b in COUNT_BUCKETS)
ORDERS = ("stratified", "measured")
#: M3 decisions that put a term in front of review (as the masked-LM and structural readouts count "kept").
KEPT_DECISIONS = ("new", "grey")
#: The pilot's measured net-new kept share: of the 235 rows the pilot's own M1 batches judged (rows no earlier batch
#: had), M3 kept 81 (all ``new``; 34.5%); the plan's per-bucket figures are 37% at count 2, 27% at 3, 34% at 4-9.
#: Measured on the 2,000-sample table, so printed as ASSUMED for the 20k run until a wave measures its own.
KEPT_SHARE_PILOT = 0.34
KEPT_SHARE_SOURCE = ("the pilot's net-new kept share (run 2026-10-12-pilot-mc2: 81 of the 235 rows its own M1 batch "
                     "judged were kept by M3, 34.5%; plan 03 section 10), measured on the 2,000-sample table")
#: The wave's size in kept terms: about two hours of review (Roger, plan 09 decision 1; plans 04 and 05).
KEPT_TARGET_DEFAULT = 300
#: Review terms an hour, measured on the TDA batch (plan 13 section 6; plan 03 section 10 uses it).
REVIEW_TERMS_PER_HOUR = 146.0
#: Below this many decided rows a cell's own rate is not used to rank it (the pooled rate stands in).
MIN_MEASURED_DEFAULT = 10
HOME_FAMILY_RULE = ("the family that emitted the row most often; a tie goes to the family with the fewest emissions "
                    "over the whole table, then to the order of prompts.FAMILIES")


# ---------------------------------------------------------------------------- cells

def count_bucket(count: int) -> str:
    c = int(count)
    if c < COUNT_BUCKETS[0][1]:
        return "1"
    for name, lo, hi in COUNT_BUCKETS:
        if c >= lo and (hi is None or c <= hi):
            return name
    raise AssertionError(c)                                    # pragma: no cover


def family_totals(table: Iterable[Mapping]) -> dict[str, int]:
    """Emissions per family over the whole table (the tie-break of :func:`home_family`)."""
    tot: Counter = Counter()
    for r in table:
        for f, n in (r.get("families") or {}).items():
            tot[f] += int(n or 0)
    return dict(tot)


def _fam_index(f: str) -> int:
    return FAMILIES.index(f) if f in FAMILIES else len(FAMILIES)


def home_family(row: Mapping, totals: Mapping[str, int], *, allowed: Optional[Iterable[str]] = None) -> str:
    """The one family a row is counted under (module docstring; :data:`HOME_FAMILY_RULE`).  ``allowed`` limits the
    choice to those families (``--families``)."""
    allow = set(allowed) if allowed else None
    fams = {f: int(n or 0) for f, n in (row.get("families") or {}).items() if allow is None or f in allow}
    if not fams:
        return str(row.get("first_family") or "?")
    return min(fams, key=lambda f: (-fams[f], int(totals.get(f, 0)), _fam_index(f), f))


def cell_of(row: Mapping, totals: Mapping[str, int], *, allowed: Optional[Iterable[str]] = None) -> str:
    return f"{count_bucket(row['count'])}|{home_family(row, totals, allowed=allowed)}"


def cell_order(cells: Iterable[str]) -> list[str]:
    """Cells by bucket, then family (the order of ``prompts.FAMILIES``)."""
    def key(c):
        b, f = c.split("|", 1)
        return (BUCKET_NAMES.index(b) if b in BUCKET_NAMES else 99, _fam_index(f), f)
    return sorted(set(cells), key=key)


def all_cells(min_count: int, families: Optional[Iterable[str]] = None) -> list[str]:
    """Every cell a wave at this floor can draw from: 4 buckets x 6 families at the default floor of 2."""
    fams = [f for f in FAMILIES if not families or f in set(families)]
    buckets = [b for b in BUCKET_NAMES if b != "1" or int(min_count) <= 1]
    return [f"{b}|{f}" for b in buckets for f in fams]


def shuffle_key(seed: int, text: str) -> str:
    """A stable seeded order: independent of the table's row order and of the count."""
    return hashlib.sha256(f"{int(seed)}:{text}".encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------- the registry

def registry_by_stem(registry_rows: Mapping[str, Mapping]) -> dict[str, Mapping]:
    """``{stem: record}``, the lowest sense id per stem (as ``structural.postprocess.registry_index``)."""
    out: dict[str, Mapping] = {}
    for _, r in sorted(registry_rows.items(), key=lambda kv: (kv[1].get("stem") or "", int(kv[1].get("sense_id") or 1))):
        st = r.get("stem")
        if st and st not in out:
            out[st] = r
    return out


def is_free_floor_reject(rec: Mapping) -> bool:
    from .submit import _free_floor_reject
    return _free_floor_reject(rec)


def is_decided(rec: Optional[Mapping]) -> bool:
    """M1 and M3 have nothing left to do: ``structural.postprocess.is_decided``, except that the frequency floor's
    free reject is not a decision (M1 retakes it; module docstring)."""
    if not rec:
        return False
    f = rec.get("filter") or {}
    if not f or is_free_floor_reject(rec):
        return False
    return f.get("verdict") != "trait" or bool(rec.get("novelty"))


def outcome(rec: Optional[Mapping]) -> str:
    """``pending`` (M1 or M3 still to run), ``dropped`` (decided, not kept) or ``kept`` (M3 ``new`` or ``grey``)."""
    if not rec:
        return "pending"
    f = rec.get("filter") or {}
    if not f or is_free_floor_reject(rec):
        return "pending"
    if f.get("verdict") != "trait":
        return "dropped"
    d = (rec.get("novelty") or {}).get("decision")
    if not d:
        return "pending"
    return "kept" if d in KEPT_DECISIONS else "dropped"


STATUSES = ("net_new", "earlier_wave", "exists", "queued", "decided")


def row_status(stem: str, *, corpus: Iterable[str] = (), renamed: Mapping[str, str] | Iterable[str] = (),
               queue: Iterable[str] = (), reg: Optional[Mapping[str, Mapping]] = None,
               earlier: Iterable[str] = ()) -> str:
    """One of :data:`STATUSES` (module docstring); ``net_new`` is the only one a wave counts."""
    if stem in earlier:
        return "earlier_wave"
    if stem in corpus or stem in renamed:
        return "exists"
    if stem in queue:
        return "queued"
    if is_decided((reg or {}).get(stem)):
        return "decided"
    return "net_new"


# ---------------------------------------------------------------------------- earlier waves

@dataclass
class Wave:
    run_id: str
    order: str
    started_at: Optional[str]
    #: ``{stem: cell}`` of the net-new rows the wave counted.
    counted: dict
    ride_along: list = field(default_factory=list)


def load_waves(runs_dir: Path, *, exclude: Iterable[str] = ()) -> list[Wave]:
    """The waves on record under ``runs/base_model/``: runs whose ``run.json`` has ``args.selection.mode`` ``wave``,
    oldest first.  ``exclude``: run ids to leave out (the run being submitted)."""
    out = []
    skip = set(exclude)
    d = Path(runs_dir)
    for p in sorted(d.glob("*/run.json")) if d.exists() else []:
        if p.parent.name in skip:
            continue
        try:
            run = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sel = (run.get("args") or {}).get("selection") or {}
        if sel.get("mode") != "wave":
            continue
        out.append(Wave(run_id=p.parent.name, order=str(sel.get("order")), started_at=run.get("started_at"),
                        counted=dict(sel.get("counted") or {}), ride_along=list(sel.get("ride_along") or [])))
    return sorted(out, key=lambda w: (w.started_at or "", w.run_id))


def earlier_stems(waves: Sequence[Wave], registry_rows: Mapping[str, Mapping], generator: str) -> set[str]:
    """Stems an earlier wave submitted: the waves' records, and any registry row with a source from one of their
    runs (so a wave submitted from another checkout still counts once its registry lines are here)."""
    ids = {w.run_id for w in waves}
    out = {s for w in waves for s in list(w.counted) + list(w.ride_along)}
    for r in registry_rows.values():
        if any(s.get("generator") == generator and s.get("run_id") in ids for s in r.get("sources") or []):
            if r.get("stem"):
                out.add(r["stem"])
    return out


def measure_cells(waves: Sequence[Wave], reg: Mapping[str, Mapping]) -> dict:
    """``{"cells": {cell: {...}}, "pooled": {...}}`` over the net-new rows the waves counted: submitted, decided,
    M1 ``trait``, kept, pending, and ``rate`` = kept / decided (None with nothing decided)."""
    cells: dict[str, Counter] = {}
    for w in waves:
        for stem, cell in w.counted.items():
            c = cells.setdefault(cell, Counter())
            rec = reg.get(stem)
            o = outcome(rec)
            c["n_submitted"] += 1
            c["n_" + o] += 1
            if o != "pending":
                c["n_decided"] += 1
            if ((rec or {}).get("filter") or {}).get("verdict") == "trait" and not is_free_floor_reject(rec or {}):
                c["n_m1_trait"] += 1

    def fin(c: Counter) -> dict:
        d = {k: int(c.get(k, 0)) for k in ("n_submitted", "n_decided", "n_m1_trait", "n_kept", "n_dropped",
                                           "n_pending")}
        d["rate"] = round(d["n_kept"] / d["n_decided"], 4) if d["n_decided"] else None
        return d
    pooled = sum(cells.values(), Counter())
    return {"cells": {k: fin(cells[k]) for k in cell_order(cells)}, "pooled": fin(pooled),
            "waves": [w.run_id for w in waves]}


# ---------------------------------------------------------------------------- quotas

def even_quotas(pools: Mapping[str, int], need: int, *, seed: int = 0) -> dict[str, int]:
    """Spread ``need`` rows evenly over the cells, no cell over its pool; a cell that runs short gives the rest to
    the others (water-filling), and the remainder of the division goes one row each to cells in a seeded order."""
    q = {c: 0 for c in pools}
    remaining = min(int(need), sum(max(0, int(v)) for v in pools.values()))
    open_ = [c for c in pools if pools[c] > 0]
    while remaining > 0 and open_:
        share = remaining // len(open_)
        if share == 0:
            for c in sorted(open_, key=lambda c: shuffle_key(seed, "cell:" + c))[:remaining]:
                q[c] += 1
            remaining = 0
            break
        for c in open_:
            give = min(share, pools[c] - q[c])
            q[c] += give
            remaining -= give
        open_ = [c for c in open_ if q[c] < pools[c]]
    return q


def measured_ranking(measured: Mapping, cells: Iterable[str], *, min_measured: int = MIN_MEASURED_DEFAULT
                     ) -> list[tuple[str, Optional[float], str]]:
    """``[(cell, rate used to rank, where it came from)]``, best first: a cell's own rate with at least
    ``min_measured`` decided rows, else the pooled rate (module docstring).  Ties: more decided rows first, then
    :func:`cell_order`."""
    pooled = (measured.get("pooled") or {}).get("rate")
    m = measured.get("cells") or {}
    order = cell_order(cells)
    rows = []
    for c in order:
        x = m.get(c) or {}
        if x.get("n_decided", 0) >= min_measured and x.get("rate") is not None:
            rows.append((c, x["rate"], f"measured, {x['n_kept']} of {x['n_decided']}"))
        else:
            rows.append((c, pooled, f"pooled rate ({x.get('n_decided', 0)} decided here, under {min_measured})"))
    return sorted(rows, key=lambda t: (-(t[1] if t[1] is not None else -1.0),
                                       -int((m.get(t[0]) or {}).get("n_decided", 0)), order.index(t[0])))


class NothingMeasured(RuntimeError):
    """``--order measured`` with no wave whose M1 and M3 are on record."""


@dataclass
class WaveSelection:
    order: str
    seed: int
    kept_target: int
    kept_share: float
    kept_share_assumed: bool
    kept_share_source: str
    need: int
    min_count: int
    #: ``{cell: {"rows", "net_new", "quota", "rate", "rate_source", "expected_kept"}}`` in cell order.
    cells: dict
    counted: list
    ride_along: list
    status_counts: dict
    cell_of_stem: dict
    measured: Optional[dict] = None
    min_measured: int = MIN_MEASURED_DEFAULT
    left_out: dict = field(default_factory=dict)

    @property
    def rows(self) -> list:
        """The rows the wave submits: the counted net-new rows and the free ride-along rows, by rank."""
        return sorted(self.counted + self.ride_along, key=lambda r: r["rank"])

    @property
    def expected_kept(self) -> float:
        return round(sum(c["expected_kept"] for c in self.cells.values()), 1)

    def record(self) -> dict:
        """What ``run.json`` keeps (``args.selection``)."""
        return {"mode": "wave", "order": self.order, "seed": self.seed, "kept_target": self.kept_target,
                "kept_share": self.kept_share, "kept_share_assumed": self.kept_share_assumed,
                "kept_share_source": self.kept_share_source, "need": self.need, "min_count": self.min_count,
                "count_buckets": [b[0] for b in COUNT_BUCKETS], "families": list(FAMILIES),
                "home_family_rule": HOME_FAMILY_RULE, "min_measured": self.min_measured,
                "cells": self.cells, "status_counts": self.status_counts, "left_out": self.left_out,
                "n_counted": len(self.counted), "n_ride_along": len(self.ride_along),
                "expected_kept": self.expected_kept,
                "measured_from": (self.measured or {}).get("waves"),
                "counted": {r["stem"]: self.cell_of_stem[r["stem"]] for r in sorted(self.counted, key=lambda r: r["rank"])},
                "ride_along": sorted(r["stem"] for r in self.ride_along)}

    def table_lines(self) -> list[str]:
        rate_h = "measured new-kept rate (ranked by)" if self.order == "measured" else "kept share"
        out = [f"  {'cell':<18} {'rows':>6} {'net-new':>8} {'selected':>9} {'expected kept':>14}   {rate_h}"]
        for c, v in self.cells.items():
            rate = "" if v.get("rate") is None else f"{v['rate']:.2f}"
            out.append(f"  {c:<18} {v['rows']:>6} {v['net_new']:>8} {v['quota']:>9} {v['expected_kept']:>14.1f}   "
                       f"{rate} {v.get('rate_source') or ''}".rstrip())
        tot = lambda k: sum(v[k] for v in self.cells.values())  # noqa: E731
        out.append(f"  {'total':<18} {tot('rows'):>6} {tot('net_new'):>8} {tot('quota'):>9} "
                   f"{self.expected_kept:>14.1f}")
        return out


def select_wave(rows: Sequence[Mapping], *, table: Sequence[Mapping], min_count: int,
                kept_target: int = KEPT_TARGET_DEFAULT, kept_share: float = KEPT_SHARE_PILOT,
                kept_share_assumed: bool = True, kept_share_source: str = KEPT_SHARE_SOURCE,
                order: str = "stratified", seed: int = 0, families: Optional[Iterable[str]] = None,
                corpus: Iterable[str] = (), renamed: Mapping[str, str] | Iterable[str] = (),
                queue: Iterable[str] = (), reg: Optional[Mapping[str, Mapping]] = None,
                earlier: Iterable[str] = (), measured: Optional[Mapping] = None,
                min_measured: int = MIN_MEASURED_DEFAULT, ride_along: bool = True) -> WaveSelection:
    """Choose a wave from ``rows`` (the eligible rows at the floor; ``table`` is the whole table, for the family
    totals).  The ride-along rows are those no earlier wave submitted that the registry has decided (free: M1 and M3
    reuse the verdicts) or that match a corpus or queue stem (QUESTIONS 82, Roger 2026-10-12, reaffirmed 2026-10-14:
    corpus and queue matches are submitted, so the overlap with the corpus is recorded in full; an undecided one costs
    its M1 and M3 calls, about $0.01 each batched, and M3 covers it with no review load)."""
    if order not in ORDERS:
        raise ValueError(f"--order must be one of {ORDERS}, not {order!r}")
    if not 0 < kept_share <= 1:
        raise ValueError(f"--kept-share must be in (0, 1], got {kept_share}")
    if int(kept_target) <= 0:
        raise ValueError(f"--kept-target must be positive, got {kept_target}")
    if order == "measured" and not ((measured or {}).get("pooled") or {}).get("n_decided"):
        raise NothingMeasured(
            "--order measured ranks the cells by the new-kept rate earlier waves measured, and no wave of this "
            "generator has rows M1 and M3 have decided"
            + (f" (waves on record: {', '.join((measured or {}).get('waves') or [])}; run their M1 and M3 first)"
               if (measured or {}).get("waves") else " (no wave on record)")
            + ".  Submit the first wave with --order stratified (the default while nothing is measured).")
    totals = family_totals(table)
    fams = [f for f in FAMILIES if not families or f in set(families)]
    corpus, queue, earlier = set(corpus), set(queue), set(earlier)
    renamed = set(renamed)
    statuses: dict[str, str] = {}
    cell_of_stem: dict[str, str] = {}
    by_cell: dict[str, list] = {c: [] for c in all_cells(min_count, fams)}
    counts_by_cell: Counter = Counter()
    ride, left_out = [], Counter()
    for r in rows:
        st = row_status(r["stem"], corpus=corpus, renamed=renamed, queue=queue, reg=reg, earlier=earlier)
        statuses[r["stem"]] = st
        c = cell_of(r, totals, allowed=fams)
        cell_of_stem[r["stem"]] = c
        counts_by_cell[c] += 1
        if st == "net_new":
            by_cell.setdefault(c, []).append(r)
        elif st == "decided" or (st in ("exists", "queued") and is_decided((reg or {}).get(r["stem"]))):
            if ride_along:
                ride.append(r)
            else:
                left_out["ride_along_off"] += 1
        elif st in ("exists", "queued"):
            if ride_along:
                ride.append(r)
            else:
                left_out["ride_along_off"] += 1
        else:
            left_out[st] += 1
    for c in by_cell:
        by_cell[c].sort(key=lambda r: shuffle_key(seed, r["stem"]))
    need = math.ceil(int(kept_target) / float(kept_share))
    pools = {c: len(v) for c, v in by_cell.items()}
    rate_of: dict[str, tuple[Optional[float], str]] = {}
    if order == "stratified":
        quotas = even_quotas(pools, need, seed=seed)
        for c in by_cell:
            rate_of[c] = (kept_share, "ASSUMED" if kept_share_assumed else "measured, pooled")
    else:
        quotas = {c: 0 for c in by_cell}
        remaining = need
        for c, rate, src in measured_ranking(measured or {}, by_cell, min_measured=min_measured):
            rate_of[c] = (rate, src)
            take = min(pools[c], max(0, remaining))
            quotas[c] = take
            remaining -= take
    counted = [r for c in by_cell for r in by_cell[c][:quotas[c]]]
    cells = {}
    for c in cell_order(by_cell):
        rate, src = rate_of.get(c, (None, ""))
        exp_rate = kept_share if order == "stratified" else (rate if rate is not None else kept_share)
        cells[c] = {"rows": int(counts_by_cell.get(c, 0)), "net_new": pools[c], "quota": quotas[c],
                    "rate": None if rate is None else round(float(rate), 4), "rate_source": src,
                    "expected_kept": round(quotas[c] * exp_rate, 1)}
    return WaveSelection(order=order, seed=int(seed), kept_target=int(kept_target), kept_share=float(kept_share),
                         kept_share_assumed=bool(kept_share_assumed), kept_share_source=kept_share_source,
                         need=need, min_count=int(min_count), cells=cells, counted=counted, ride_along=ride,
                         status_counts=dict(sorted(Counter(statuses.values()).items())),
                         cell_of_stem=cell_of_stem, measured=dict(measured) if measured else None,
                         min_measured=int(min_measured), left_out=dict(sorted(left_out.items())))
