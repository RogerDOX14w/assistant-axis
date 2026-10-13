"""Selection, the downstream estimate and its gate, and the submission of a structural run (plan sections 6-7;
tasks 8, 9 and 11).

Two ways to choose the operator table's rows, both in rank order (:mod:`.postprocess`):

* ``--all`` (the A run: the classical rows with the pilot's operator rows): every row;
* ``--kept-target K`` (**the review-hour wave**, decision 1, Roger 2026-10-13): rows in rank order, each selected
  row's **siblings travelling with it** (a triple is reviewed together), until the **net-new** rows selected reach
  ``ceil(K / kept_share)``.  A net-new row is one the registry has not yet filtered (not a corpus trait, not queued,
  not decided by M1 and M3; :class:`.postprocess.Tags`); ``kept_share`` is the pilot's measured **net-new kept
  share** (kept rows per submitted net-new row), the plan-04 assumption 0.5 until then, printed as ASSUMED.  A
  corpus, queued or decided row inside the cut is submitted (every item is kept, Roger 2026-10-10: "let the
  pipeline do its job") and counts toward neither the target nor the estimate.

**The downstream estimate** prices M1 on every selected row the registry has not decided and M3 on the share M1
passes, at the measured census rates (plan 04's :func:`..masked_lm.submit.estimate_downstream_usd`: M1 $0.0072 a
word, M3 $0.011 a passed word at the assumed 0.88, batches x0.5), and is gated by ``gapgen.cost.confirm_or_abort``
(over ``--budget-usd`` refused; over the $20 line needs ``--confirm-expensive`` and ``--confirmed-by``).

:func:`run_submit` writes ``candidates.jsonl`` **before** ``submit_candidates`` (one :class:`~assistant_axis.gapgen.
Candidate` per source: ``score`` = ``n_sources``, a quality signal and **not** a familiarity, so ``structural`` is not
in ``FAMILIARITY_GENERATORS``; ``source_ref`` ``structural:op:<operator>[:<target>|:<mode>]:<source stem>`` or
``structural:classical:<row id>``; ``partner_hint`` the source trait's label for an opposite, the sibling vice's
label for an excess or deficiency and for the classical vice, sin and virtue, overuse and underuse, and high and low
rows, else None), then ``keys.txt``, ``submit_report.json`` (rows submitted, counted and already filtered, the last
two summing to the first), ``run.json`` and a zero-call ``usage.json``, and prints the follow-up commands.  A dry run
prints the same and writes nothing.

**Review rate** (decision 1's hours): the plan's ~150 terms an hour until plan 13's measured rate lands; see
:func:`review_terms_per_hour`, the hook to switch.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.paths import DATA_CANDIDATES, REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from ..masked_lm.submit import (BATCH_FACTOR, M1_PASS_RATE_ASSUMED, M1_USD_PER_WORD, M3_USD_PER_PASSED_WORD,
                                RATES_SOURCE, Estimate, _budget)
from ..masked_lm.submit import estimate_downstream_usd as _estimate
from . import GENERATOR
from .postprocess import KIND_TIER

DEFAULT_BUDGET_USD = 5.0
#: The wave's size in review terms (decision 1: about two hours at ~150 terms an hour; plan 04's operationalisation).
KEPT_TARGET_DEFAULT = 300
#: Kept rows per submitted net-new row, assumed from plan 04 (the census funnel) until the pilot measures it.
KEPT_SHARE_ASSUMED = 0.5
#: The review rate the plan sizes the wave at (plan 04's measurement, ~150 terms an hour).
REVIEW_TERMS_PER_HOUR_PLAN = 150.0
REVIEW_RATE_SOURCE_PLAN = "plan figure, ~150 terms an hour (plan 04; coding_plan_09 decision 1)"
#: A projection more than this multiple of the target prints a warning (siblings can carry the cut past it).
REVIEW_OVERSHOOT = 1.5

__all__ = ["M1_USD_PER_WORD", "M3_USD_PER_PASSED_WORD", "M1_PASS_RATE_ASSUMED", "BATCH_FACTOR", "RATES_SOURCE",
           "Estimate", "DEFAULT_BUDGET_USD", "KEPT_TARGET_DEFAULT", "KEPT_SHARE_ASSUMED",
           "REVIEW_TERMS_PER_HOUR_PLAN", "estimate_downstream_usd", "review_terms_per_hour", "select_all",
           "select_wave", "source_ref", "parse_source_ref", "classical_role", "to_candidates", "primary_kind",
           "strata", "batch_id_for", "followup_commands", "SubmitSummary", "run_submit"]


def estimate_downstream_usd(n: int, *, transport: str = "live", pass_rate: float = M1_PASS_RATE_ASSUMED) -> Estimate:
    """M1 on ``n`` rows and M3 on the share M1 passes, at the measured census rates (plan 04's estimate)."""
    return _estimate(n, transport=transport, pass_rate=pass_rate)


def review_terms_per_hour(source: str = "plan", *, review_dirs: Optional[Sequence[Path]] = None
                          ) -> tuple[float, str]:
    """``(terms an hour, where the figure comes from)``.

    HOOK (plan 13, coding_plan_13 "Frozen interface"): ``source="measured"`` switches to the review rate plan 13
    measures from the review app's logs, through its frozen interface (``from assistant_axis.gapgen.testing import
    pooled_review_rate``; ``ReviewRate.terms_per_active_minute`` x 60; 146 an hour active on ``review_tda_1``).  Until
    that package lands (it is being built beside this one), ``"plan"`` (the default) is the plan's ~150 an hour and
    ``"measured"`` refuses with a pointer.  Switching the default is one word here once plan 13 is merged."""
    if source == "plan":
        return REVIEW_TERMS_PER_HOUR_PLAN, REVIEW_RATE_SOURCE_PLAN
    if source != "measured":
        raise ValueError(f"review rate source must be 'plan' or 'measured', not {source!r}")
    try:
        from assistant_axis.gapgen.testing import pooled_review_rate  # plan 13's frozen interface
    except ImportError as exc:
        raise SystemExit("--review-rate measured needs plan 13's assistant_axis.gapgen.testing (pooled_review_rate), "
                         f"which is not in this checkout yet ({exc}); use --review-rate plan") from None
    dirs = list(review_dirs or sorted(p.parent for p in (DATA_CANDIDATES / "review").glob("*/decisions.jsonl")))
    rr = pooled_review_rate(dirs)
    return float(rr.terms_per_active_minute) * 60.0, (f"measured, plan 13's pooled_review_rate over "
                                                      f"{len(dirs)} review batches")


# --------------------------------------------------------------------------- selection

def select_all(rows: Sequence[Mapping]) -> list[Mapping]:
    return sorted(rows, key=lambda r: r["rank"])


def select_wave(rows: Sequence[Mapping], *, kept_target: int = KEPT_TARGET_DEFAULT,
                kept_share: float = KEPT_SHARE_ASSUMED, siblings: bool = True) -> tuple[list[Mapping], int]:
    """``(selected rows in rank order, net-new rows among them)``: rows in rank order, each with its siblings that are
    table rows, until ``ceil(kept_target / kept_share)`` net-new rows are selected (module docstring)."""
    if not 0 < kept_share <= 1:
        raise ValueError(f"--kept-share must be in (0, 1], got {kept_share}")
    need = math.ceil(int(kept_target) / float(kept_share))
    by_stem = {r["stem"]: r for r in rows}
    chosen: dict[str, Mapping] = {}
    counted = 0
    for r in sorted(rows, key=lambda r: r["rank"]):
        if counted >= need:
            break
        if r["stem"] in chosen:
            continue
        group = [r] + ([by_stem[s] for s in r.get("siblings") or [] if s in by_stem] if siblings else [])
        for g in group:
            if g["stem"] not in chosen:
                chosen[g["stem"]] = g
                counted += bool(g.get("net_new"))
    return sorted(chosen.values(), key=lambda r: r["rank"]), counted


# --------------------------------------------------------------------------- candidates

def source_ref(src: Mapping) -> str:
    """``structural:op:<operator>[:<target>|:<mode>]:<source stem>`` or ``structural:classical:<row id>``."""
    if src["generator_part"] == "classical":
        return f"structural:classical:{src['source_id']}"
    sub = src.get("target") or src.get("mode")
    return f"structural:op:{src['operator']}{':' + sub if sub else ''}:{src['source_stem']}"


def classical_role(row_id: str) -> Optional[str]:
    """A classical row's role from its id (``aristotle:courage:excess`` -> ``excess``; ``sins_virtues:sin:pride`` ->
    ``sin``, the contrary, cardinal and theological virtues -> ``virtue``; a Theophrastus row -> ``vice``)."""
    parts = row_id.split(":")
    if parts[0] == "theophrastus":
        return "vice"
    if parts[0] == "sins_virtues":
        return "sin" if parts[1] == "sin" else "virtue"
    return parts[-1] if len(parts) >= 3 else None


def parse_source_ref(ref: str) -> dict:
    """The parts of a structural ``source_ref``: ``{"part", "operator", "target" | "mode", "source_stem"}`` or
    ``{"part": "classical", "source_id", "role"}``.  ``ValueError`` for anything else."""
    parts = ref.split(":")
    if len(parts) < 3 or parts[0] != GENERATOR:
        raise ValueError(f"not a structural source_ref: {ref!r}")
    if parts[1] == "classical":
        rid = ":".join(parts[2:])
        return {"part": "classical", "source_id": rid, "role": classical_role(rid)}
    if parts[1] != "op":
        raise ValueError(f"not a structural source_ref: {ref!r}")
    from .operators import MODES, OPERATORS, PRINCIPAL_TARGETS, TARGETS
    op = parts[2]
    if op not in OPERATORS:
        raise ValueError(f"unknown operator in {ref!r}")
    out = {"part": "operators", "operator": op, "role": op}
    if op in ("retarget", "remode"):
        if len(parts) != 5:
            raise ValueError(f"{ref!r}: {op} needs a {'target' if op == 'retarget' else 'mode'}")
        sub = parts[3]
        if op == "retarget" and sub not in TARGETS + PRINCIPAL_TARGETS or op == "remode" and sub not in MODES:
            raise ValueError(f"{ref!r}: unknown {'target' if op == 'retarget' else 'mode'} {sub!r}")
        out["target" if op == "retarget" else "mode"] = sub
        out["source_stem"] = parts[4]
    else:
        if len(parts) != 4:
            raise ValueError(f"{ref!r}: expected structural:op:{op}:<source stem>")
        out["source_stem"] = parts[3]
    return out


def to_candidates(rows: Sequence[Mapping], run_id: str) -> list[Candidate]:
    """One candidate per source of each row (module docstring)."""
    out = []
    for r in rows:
        if normalize_candidate(r["label"]).stem != r["stem"]:
            raise ValueError(f"row {r['stem']!r}: its label {r['label']!r} does not normalise back to the stem")
        for s in r["sources"]:
            out.append(Candidate(surface=r["label"], generator=GENERATOR, run_id=run_id, rank=int(r["rank"]),
                                 score=float(r["n_sources"]), gloss_hint=s.get("gloss") or r.get("gloss"),
                                 sense_id=1, source_ref=source_ref(s), partner_hint=s.get("partner_hint")))
    return out


def primary_kind(row: Mapping) -> str:
    """The row's first kind by tier (the stratum it is reported under)."""
    kinds = sorted(row.get("kinds") or ["?"], key=lambda k: (KIND_TIER.get(k, 9), k))
    return kinds[0]


def strata(rows: Sequence[Mapping]) -> dict:
    """``{"kind x status": n}``, the status counts, the principal-target count."""
    ks = Counter(f"{primary_kind(r)} | {r.get('status') or '?'}" for r in rows)
    return {"kind_x_status": dict(sorted(ks.items())),
            "status": dict(sorted(Counter(str(r.get("status")) for r in rows).items())),
            "kind": dict(sorted(Counter(primary_kind(r) for r in rows).items())),
            "principal_target": sum(1 for r in rows if r.get("principal_target")),
            "phrases": sum(1 for r in rows if len(str(r.get("label") or "").split()) > 1)}


def batch_id_for(run_id: str) -> str:
    return f"{run_id}_{GENERATOR}"


def followup_commands(run_id: str, est: Estimate, *, candidates_path: Optional[Path] = None) -> list[str]:
    b, t = batch_id_for(run_id), est.transport
    py = "uv run python data_analysis/gap_generation"
    cap1, cap3 = _budget(est.m1_usd), _budget(est.m3_usd)

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""

    rel = Path(candidates_path or run_dir(GENERATOR, run_id) / "candidates.jsonl")
    try:
        rel = rel.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    return [
        f"{py}/gap_registry.py submit --from {rel}   # main checkout: resubmit into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport {t} "
        f"--budget-usd {cap1:.0f}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport {t} "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # M3 on the rows M1 passes, estimate ${est.m3_usd:.2f}",
        f"{py}/recovery_test.py --generator {GENERATOR} --run-id {run_id} --budget-usd 8   # optional: about $5 a "
        f"seed (paid; Roger's call)",
        f"{py}/structural_generator.py report --run-id {run_id}   # the readout ($0)",
    ]


# --------------------------------------------------------------------------- submission

@dataclass
class SubmitSummary:
    run_id: str
    mode: str
    n_table: int
    n_selected: int
    n_counted: int
    n_filtered: int
    n_charged: int
    estimate: dict
    strata: dict
    dry_run: bool
    n_candidates: int = 0
    projected_kept: Optional[float] = None
    review_hours: Optional[float] = None
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list = field(default_factory=list)


def run_submit(run_id: str, *, table: Sequence[Mapping], all_rows: bool = False, kept_target: Optional[int] = None,
               kept_share: float = KEPT_SHARE_ASSUMED, budget_usd: float = DEFAULT_BUDGET_USD,
               confirm_expensive: bool = False, confirmed_by: Optional[str] = None, transport: str = "live",
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               table_path: Optional[Path] = None, table_sha256: Optional[str] = None,
               review_rate: Optional[tuple[float, str]] = None, extra_args: Optional[Mapping] = None,
               echo=print) -> SubmitSummary:
    """Select, estimate, gate, record and submit (module docstring).  Exactly one of ``all_rows`` and
    ``kept_target``."""
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    if bool(all_rows) == (kept_target is not None):
        raise ValueError("give exactly one of --all and --kept-target K")
    rate, rate_src = review_rate or review_terms_per_hour("plan")
    if all_rows:
        mode = "all"
        rows = select_all(table)
        n_counted = sum(1 for r in rows if r.get("net_new"))
    else:
        mode = f"kept target {kept_target} at net-new kept share {kept_share}"
        rows, n_counted = select_wave(table, kept_target=kept_target, kept_share=kept_share)
    n_filtered = len(rows) - n_counted
    n_charged = sum(1 for r in rows if not r.get("registered_decided"))
    cands = to_candidates(rows, run_id)
    est = estimate_downstream_usd(n_charged, transport=transport)
    st = strata(rows)
    projected = n_counted * kept_share
    hours = projected / rate if rate else None
    assumed = kept_share == KEPT_SHARE_ASSUMED
    echo(f"{mode}: {len(table)} table rows; selected {len(rows)} ({n_counted} net-new, counted; {n_filtered} already "
         f"filtered: corpus traits, queued, or decided by M1 and M3, submitted and not counted); {len(cands)} "
         f"candidates (one per source)")
    echo(f"  projection: {n_counted} net-new rows x net-new kept share {kept_share} = {projected:.0f} kept rows"
         + (f" against the target {kept_target}" if kept_target is not None else "")
         + f", about {hours:.1f} h of review at {rate:.0f} terms an hour ({rate_src})"
         + ("  [kept share ASSUMED (plan 04's 0.5): pass the pilot's measured net-new kept share with --kept-share]"
            if assumed else ""))
    if kept_target is not None and projected > REVIEW_OVERSHOOT * kept_target:
        echo(f"  WARNING: the projection is over {REVIEW_OVERSHOOT}x the target (siblings travelling with the cut)")
    for k, v in st.items():
        echo(f"  {k}: {v}")
    echo(est.format() + f"\n  [{n_charged} of the {len(rows)} rows: those the registry has not decided; M1 and M3 "
                        f"skip the rest]")
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(run_id=run_id, mode=mode, n_table=len(table), n_selected=len(rows), n_counted=n_counted,
                            n_filtered=n_filtered, n_charged=n_charged, estimate=asdict(est), strata=st,
                            dry_run=dry_run, n_candidates=len(cands), projected_kept=round(projected, 1),
                            review_hours=None if hours is None else round(hours, 2))
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    args = {"step": "submit", "mode": mode, "all": bool(all_rows), "kept_target": kept_target,
            "kept_share": kept_share, "kept_share_assumed": assumed, "n_rows": len(rows), "n_candidates": len(cands),
            "n_counted": n_counted, "n_filtered": n_filtered, "n_charged": n_charged,
            "counted_stems": sorted(r["stem"] for r in rows if r.get("net_new")),
            "registered_stems": {r["stem"]: list(r.get("registered_by") or []) for r in rows if r.get("registered")},
            "decided_stems": sorted(r["stem"] for r in rows if r.get("registered_decided")),
            "exists_stems": sorted(r["stem"] for r in rows if r.get("exists")),
            "queued_stems": sorted(r["stem"] for r in rows if r.get("queued")),
            "principal_target_stems": sorted(r["stem"] for r in rows if r.get("principal_target")),
            "transport": transport, "budget_usd": budget_usd, "estimate": asdict(est), "strata": st,
            "review_terms_per_hour": rate, "review_rate_source": rate_src, "projected_kept": round(projected, 1),
            "table": str(table_path) if table_path else None, "table_sha256": table_sha256,
            "score": "n_sources (a quality signal; not a familiarity)", **dict(extra_args or {})}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=registry_path)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {
        "n_keys": len(rep.keys), "rows_submitted": len(rows), "rows_counted": n_counted,
        "rows_already_filtered": n_filtered, "rows_charged": n_charged, "n_candidates": len(cands)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    ctx.finish()
    summary.run_dir = str(ctx.dir)
    summary.report = rep_d
    echo(f"registry {registry_path}: {json.dumps(rep_d)}")
    echo(f"wrote {ctx.dir}/candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json")
    for c in summary.followups:
        echo(f"  then: {c}")
    return summary
