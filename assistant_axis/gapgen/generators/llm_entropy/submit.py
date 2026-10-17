"""Selection, the downstream estimate and its gate, and the submission of a run's table rows (plan section 7,
``submit``; task 6).

Three ways to choose rows, all over the table's **eligible** rows (no ``label_problem``: a label the rule refuses is
kept in the table and never submitted), in rank order:

* ``--top N [--per-cell 50]`` (the pilot's slice, Roger's decision 2): N **net-new** rows, stratified by (family,
  model): each cell takes its own rows in rank order until ``per_cell`` of them are net-new, then the remainder is
  filled from the whole ranking;
* ``--kept-target K [--kept-share X]`` (the review-hour wave): rows in rank order until the net-new rows reach
  ``ceil(K / X)``, ``X`` the pilot's measured **net-new kept share** (kept rows per submitted net-new row;
  :data:`KEPT_SHARE_ASSUMED` until then, printed as ASSUMED: the base-model generator's measured 35%);
* ``--all``: every eligible row.

A **net-new row** is one the registry has not yet filtered: not a corpus stem, not queued, not registered with M1 and
M3 both done (the table's ``net_new``).  A corpus, queued or decided row inside the cut **is submitted** (the registry
merges the source at no cost; M1 and M3 skip decided rows) and counted toward neither the target nor the estimate.
**No tag drops a row** (the mutation test: flipping every tag leaves ``--all`` unchanged and moves only the cut's
count under ``--kept-target``).

**The downstream estimate** is what M1 and M3 will really be asked (``base_model.submit.downstream_need``: keys with
no M1 verdict are charged M1 and M3 at the pass rate, keys M1 passed and M3 has not decided M3 only), at the
measured rates (M1 $0.0072 a word, M3 $0.011 a passed word, the pass rate 0.88 until the pilot measures it, batches
x0.5), gated by ``gapgen.cost.confirm_or_abort`` (over ``--budget-usd`` refused; over the $20 line needs
``--confirm-expensive`` and ``--confirmed-by``).

:func:`run_submit` writes ``candidates.jsonl`` **before** ``submit_candidates`` (one :class:`~assistant_axis.gapgen.
Candidate` per source: ``score`` = ``n_sources``, a repetition signal and **not a familiarity**, so ``llm_entropy``
is not in ``freq.FAMILIARITY_GENERATORS``; ``source_ref`` ``llm_entropy:<prompt id>:r<run>[:<model tag>]``;
``gloss_hint`` the source's gloss; ``partner_hint`` its antonym; ``sense_id`` 1), then ``keys.txt``,
``submit_report.json``, ``run.json`` and ``usage.json`` (the run's sessions summed), and prints the follow-ups.  The
registry's noun relabel step runs as ``submit_candidates`` does by default (``relabel="auto"``).  A dry run prints the
same and writes nothing.
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
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from ..masked_lm.submit import (BATCH_FACTOR, M1_PASS_RATE_ASSUMED, M1_USD_PER_WORD, M3_USD_PER_PASSED_WORD,
                                RATES_SOURCE, Estimate, _budget)
from ..masked_lm.submit import estimate_downstream_usd as _estimate
from . import GENERATOR
from .calls import model_tag
from .table import parse_source_ref, source_ref

DEFAULT_BUDGET_USD = 10.0
KEPT_TARGET_DEFAULT = 300
#: Kept rows per submitted net-new row, assumed from the base-model generator (540 kept of 1,541 submitted, 35%;
#: plan section "Measured") until the pilot measures this generator's own.
KEPT_SHARE_ASSUMED = 0.35
PER_CELL_DEFAULT = 50
REVIEW_TERMS_PER_HOUR = 150.0
REVIEW_RATE_SOURCE = "plan figure, ~150 terms an hour (146 measured on the TDA batch) until plan 13's pooled rate"

__all__ = ["M1_USD_PER_WORD", "M3_USD_PER_PASSED_WORD", "M1_PASS_RATE_ASSUMED", "BATCH_FACTOR", "RATES_SOURCE",
           "DEFAULT_BUDGET_USD", "KEPT_TARGET_DEFAULT", "KEPT_SHARE_ASSUMED", "PER_CELL_DEFAULT",
           "estimate_downstream_usd", "rows_of_run", "eligible", "cells_of", "select_all", "select_top", "select_wave",
           "to_candidates", "strata", "batch_id_for", "followup_commands", "SubmitSummary", "run_submit",
           "source_ref", "parse_source_ref"]


def estimate_downstream_usd(n: int, *, transport: str = "live", pass_rate: float = M1_PASS_RATE_ASSUMED,
                            n_m3_only: int = 0) -> Estimate:
    """M1 on ``n`` rows and M3 on the share M1 passes, plus M3 alone on ``n_m3_only`` rows M1 has passed already
    (plan 04's estimate, with the M3-only rows of ``downstream_need``)."""
    e = _estimate(n, transport=transport, pass_rate=pass_rate)
    if n_m3_only:
        f = BATCH_FACTOR if transport == "batches" else 1.0
        extra = round(n_m3_only * M3_USD_PER_PASSED_WORD * f, 4)
        e.m3_usd = round(e.m3_usd + extra, 4)
        e.m3_usd_high = round(e.m3_usd_high + extra, 4)
        e.total_usd = round(e.m1_usd + e.m3_usd, 4)
        e.total_usd_high = round(e.m1_usd + e.m3_usd_high, 4)
        e.assumptions["n_m3_only"] = int(n_m3_only)
    return e


# --------------------------------------------------------------------------- selection

def rows_of_run(table: Sequence[Mapping], run_id: str) -> list[dict]:
    """The table rows a run emitted, each with only that run's sources (a row reached by two runs is submitted by
    each with its own sources; ``n_sources``, the score, stays the table's count over every run)."""
    out = []
    for r in table:
        srcs = [s for s in r.get("sources") or [] if s.get("run_id") in (run_id, None)]
        if srcs:
            out.append({**r, "sources": srcs})
    return out


def eligible(table: Sequence[Mapping]) -> list[Mapping]:
    """The rows that can be submitted (no ``label_problem``), in rank order."""
    return sorted((r for r in table if not r.get("label_problem")), key=lambda r: r["rank"])


def cells_of(row: Mapping) -> list[tuple[str, str]]:
    """The (family, model) cells whose calls emitted the row, in order of appearance."""
    out: list[tuple[str, str]] = []
    for s in row.get("sources") or []:
        c = (s.get("family"), s.get("model"))
        if c not in out:
            out.append(c)
    return out


def select_all(table: Sequence[Mapping]) -> tuple[list[Mapping], int]:
    rows = eligible(table)
    return rows, sum(1 for r in rows if r.get("net_new"))


def select_wave(table: Sequence[Mapping], *, kept_target: int = KEPT_TARGET_DEFAULT,
                kept_share: float = KEPT_SHARE_ASSUMED) -> tuple[list[Mapping], int]:
    """``(rows, net-new rows among them)``: rank order until ``ceil(kept_target / kept_share)`` net-new rows."""
    if not 0 < kept_share <= 1:
        raise ValueError(f"--kept-share must be in (0, 1], got {kept_share}")
    need = math.ceil(int(kept_target) / float(kept_share))
    out, n = [], 0
    for r in eligible(table):
        if n >= need:
            break
        out.append(r)
        n += bool(r.get("net_new"))
    return out, n


def select_top(table: Sequence[Mapping], n: int, *, per_cell: Optional[int] = None) -> tuple[list[Mapping], int,
                                                                                             dict]:
    """``(rows, net-new rows among them, net-new counted per cell)`` (module docstring).  Without ``per_cell``: the
    first rows in rank order up to the ``n``-th net-new one."""
    rows = eligible(table)
    n = max(0, int(n))
    chosen: dict[str, Mapping] = {}
    counted = 0
    per: Counter = Counter()
    if per_cell:
        cells = sorted({c for r in rows for c in cells_of(r)}, key=lambda c: (str(c[0]), str(c[1])))
        for cell in cells:
            for r in rows:
                if counted >= n or per[cell] >= per_cell:
                    break
                if cell not in cells_of(r) or r["stem"] in chosen:
                    continue
                chosen[r["stem"]] = r
                if r.get("net_new"):
                    per[cell] += 1
                    counted += 1
    for r in rows:                              # the remainder (or everything, without per_cell)
        if counted >= n:
            break
        if r["stem"] in chosen:
            continue
        chosen[r["stem"]] = r
        if r.get("net_new"):
            counted += 1
            if per_cell:
                per[cells_of(r)[0]] += 1
    out = sorted(chosen.values(), key=lambda r: r["rank"])
    return out, counted, {f"{f}|{m}": v for (f, m), v in sorted(per.items(), key=lambda kv: (str(kv[0][0]),
                                                                                            str(kv[0][1])))}


# --------------------------------------------------------------------------- candidates

def to_candidates(rows: Sequence[Mapping], run_id: str) -> list[Candidate]:
    """One candidate per source of each row (module docstring)."""
    out = []
    for r in rows:
        if normalize_candidate(r["label"]).stem != r["stem"]:
            raise ValueError(f"row {r['stem']!r}: its label {r['label']!r} does not normalise back to the stem")
        for s in r["sources"]:
            out.append(Candidate(surface=r["label"], generator=GENERATOR, run_id=run_id, rank=int(r["rank"]),
                                 score=float(r["n_sources"]), gloss_hint=s.get("gloss") or r.get("gloss"),
                                 sense_id=1, source_ref=s.get("source_ref") or source_ref(s["prompt_id"], s["run"],
                                                                                         s["model"]),
                                 partner_hint=s.get("antonym")))
    return out


def strata(rows: Sequence[Mapping], table: Sequence[Mapping] = ()) -> dict:
    """``family x model x status`` (each row under its first cell), single- and multi-word, and the label rule's
    refusals in the table."""
    fms = Counter(f"{cells_of(r)[0][0]} x {model_tag(cells_of(r)[0][1])} x {r.get('status')}" for r in rows)
    return {"family_x_model_x_status": dict(sorted(fms.items())),
            "status": dict(sorted(Counter(str(r.get("status")) for r in rows).items())),
            "single_word": sum(1 for r in rows if "_" not in r["stem"]),
            "multi_word": sum(1 for r in rows if "_" in r["stem"]),
            "pair_completion_hint": sum(1 for r in rows if r.get("pair_completion_hint")),
            "table_label_rule_refused": sum(1 for r in table if r.get("label_problem"))}


def batch_id_for(run_id: str) -> str:
    return f"{run_id}_{GENERATOR}"


def _rel(p: Path) -> Path:
    try:
        return Path(p).resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        return Path(p)


def followup_commands(run_id: str, est: Estimate, *, candidates_path: Optional[Path] = None) -> list[str]:
    b, t = batch_id_for(run_id), est.transport
    py = "uv run python data_analysis/gap_generation"
    cap1, cap3 = _budget(est.m1_usd), _budget(est.m3_usd)

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""
    rel = _rel(Path(candidates_path or run_dir(GENERATOR, run_id) / "candidates.jsonl"))
    return [
        f"{py}/gap_registry.py submit --from {rel}   # main checkout: resubmit into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport {t} "
        f"--budget-usd {cap1:.0f}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport {t} "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # M3 on the rows M1 passes, estimate ${est.m3_usd:.2f}",
        f"{py}/llm_entropy_generator.py report --run-id {run_id}   # the readout ($0)",
        f"{py}/llm_entropy_generator.py model-test --run-id {run_id}   # the per-(family, model) table ($0)",
        f"{py}/llm_entropy_generator.py roles-report --run-id {run_id}   # the held roles ($0)",
    ]


@dataclass
class SubmitSummary:
    run_id: str
    mode: str
    n_table: int
    n_selected: int
    n_counted: int
    n_filtered: int
    need: dict
    estimate: dict
    strata: dict
    dry_run: bool
    per_cell: dict = field(default_factory=dict)
    n_candidates: int = 0
    projected_kept: Optional[float] = None
    review_hours: Optional[float] = None
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list = field(default_factory=list)


def run_submit(run_id: str, *, table: Sequence[Mapping], registry_rows: Mapping[str, Mapping],
               top_n: Optional[int] = None, per_cell: Optional[int] = None, kept_target: Optional[int] = None,
               kept_share: float = KEPT_SHARE_ASSUMED, all_rows: bool = False, budget_usd: float = DEFAULT_BUDGET_USD,
               confirm_expensive: bool = False, confirmed_by: Optional[str] = None, transport: str = "batches",
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               table_path: Optional[Path] = None, table_sha256: Optional[str] = None, relabel="auto",
               extra_args: Optional[Mapping] = None, echo=print) -> SubmitSummary:
    """Select, estimate, gate, record and submit (module docstring).  Exactly one of ``top_n``, ``kept_target`` and
    ``all_rows``.  ``registry_rows``: the folded registry by key (what M1 and M3 will really be asked)."""
    from ..base_model.submit import downstream_need
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    if sum(x is not None and x is not False for x in (top_n, kept_target, all_rows or None)) != 1:
        raise ValueError("give exactly one of --top N, --kept-target K and --all")
    per: dict = {}
    if top_n is not None:
        mode = f"top {top_n}" + (f", {per_cell} per (family, model) cell" if per_cell else "")
        rows, n_counted, per = select_top(table, top_n, per_cell=per_cell)
    elif kept_target is not None:
        mode = f"kept target {kept_target} at net-new kept share {kept_share}"
        rows, n_counted = select_wave(table, kept_target=kept_target, kept_share=kept_share)
    else:
        mode = "all"
        rows, n_counted = select_all(table)
    n_filtered = len(rows) - n_counted
    need = downstream_need(rows, registry_rows)
    est = estimate_downstream_usd(need["n_m1"], transport=transport, n_m3_only=need["n_m3_only"])
    cands = to_candidates(rows, run_id)
    st = strata(rows, table)
    projected = n_counted * kept_share
    hours = projected / REVIEW_TERMS_PER_HOUR
    assumed = kept_share == KEPT_SHARE_ASSUMED
    echo(f"{mode}: {len(table)} table rows ({len(eligible(table))} eligible); selected {len(rows)} ({n_counted} "
         f"net-new, counted; {n_filtered} already filtered: corpus traits, queued, or decided by M1 and M3, submitted "
         f"and not counted); {len(cands)} candidates (one per source)")
    if per:
        echo(f"  net-new per (family, model) cell: {per}")
    echo(f"  projection: {n_counted} net-new rows x net-new kept share {kept_share} = {projected:.0f} kept rows"
         + (f" against the target {kept_target}" if kept_target is not None else "")
         + f", about {hours:.1f} h of review at {REVIEW_TERMS_PER_HOUR:.0f} terms an hour ({REVIEW_RATE_SOURCE})"
         + ("  [kept share ASSUMED (the base-model generator's 0.35): pass the pilot's measured net-new kept share "
            "with --kept-share]" if assumed else ""))
    for k, v in st.items():
        echo(f"  {k}: {v}")
    echo(est.format() + f"\n  [what M1 and M3 will be asked: {need['n_m1']} rows for M1 (and M3 at the pass rate), "
                        f"{need['n_m3_only']} for M3 alone, {need['n_decided']} decided already and free]")
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(run_id=run_id, mode=mode, n_table=len(table), n_selected=len(rows), n_counted=n_counted,
                            n_filtered=n_filtered, need=need, estimate=asdict(est), strata=st, dry_run=dry_run,
                            per_cell=per, n_candidates=len(cands), projected_kept=round(projected, 1),
                            review_hours=round(hours, 2))
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {_rel(target)}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json and usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    args = {"step": "submit", "mode": mode, "top_n": top_n, "per_cell": per_cell, "kept_target": kept_target,
            "kept_share": kept_share, "kept_share_assumed": assumed, "all": bool(all_rows), "n_rows": len(rows),
            "n_candidates": len(cands), "n_counted": n_counted, "n_filtered": n_filtered, "need": need,
            "net_new_per_cell": per, "counted_stems": sorted(r["stem"] for r in rows if r.get("net_new")),
            "registered_stems": {r["stem"]: list(r.get("registered_by") or []) for r in rows if r.get("registered")},
            "decided_stems": sorted(r["stem"] for r in rows if r.get("registered_decided")),
            "exists_stems": sorted(r["stem"] for r in rows if r.get("exists")),
            "queued_stems": sorted(r["stem"] for r in rows if r.get("queued")),
            "transport": transport, "budget_usd": budget_usd, "estimate": asdict(est), "strata": st,
            "review_terms_per_hour": REVIEW_TERMS_PER_HOUR, "projected_kept": round(projected, 1),
            "table": str(_rel(table_path)) if table_path else None, "table_sha256": table_sha256,
            "score": "n_sources (a repetition signal; not a familiarity)", **dict(extra_args or {})}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=registry_path, relabel=relabel)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k not in ("keys", "relabels")} | {
        "n_keys": len(rep.keys), "rows_submitted": len(rows), "rows_counted": n_counted,
        "rows_already_filtered": n_filtered, "n_candidates": len(cands)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    ctx.finish()
    summary.run_dir = str(ctx.dir)
    summary.report = rep_d
    echo(f"registry {registry_path}: {json.dumps(rep_d)}")
    echo(f"wrote {_rel(ctx.dir)}/candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json")
    for c in summary.followups:
        echo(f"  then: {c}")
    return summary
