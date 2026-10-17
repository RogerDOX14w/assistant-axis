"""Selection, the downstream estimate and its gate, and the submission of a corpus-frames run (plan sections 7 and 10).

Two ways to choose the table's rows (eligible rows only; plan 04's rule ``eligible = not freq_hard_reject or
gloss_hint``):

* ``--top-per-frame N`` (**the pilot**, plan section 10): the top N of **every** frame by within-frame rank,
  deduplicated across frames.  Each frame is measured on its own N, so its registered fillers are taken like any other ("registered
  rows ride along") and cost nothing: the estimate charges only the rows the registry has not yet filtered.  The run
  records which stems each frame contributed (``run.json`` ``args.selection_by_frame``), which is what the frame
  measures read after M1 and M3 (:func:`.evaluate.frame_measures`).
* ``--kept-target K --kept-share S`` (**the review-hour wave**; Roger, plan 09 decision 1 and plan 04: about two hours
  of review): the rows found by the **frames kept** after the pilot, ranked by RRF over those frames only
  (:func:`.table.rerank_over`: a dropped frame's rows and ranks left out), taken until the **net-new** rows selected
  reach ``ceil(K / S)``.  A net-new row is one the registry has not yet filtered (not a corpus trait, not queued, not
  decided by M1 and M3; a registered row M1 or M3 has still to decide counts).  A row the registry has filtered inside
  the cut is submitted (Roger, 2026-10-10: "let the pipeline do its job") and counts toward neither the target nor the
  estimate.  **A noun's sibling counts** (``count_siblings``, the default): a row whose surface is a noun that the
  helper relabels makes two registry rows, the noun and its adjective, and both are reviewed, so a net-new noun is a
  net-new row of its own in the cut and in the estimate.  The **review-load guard** refuses a selection whose
  projected kept rows (every net-new registry row it makes, times S) exceed :data:`REVIEW_OVERSHOOT` times K, which
  only the literal reading (``count_siblings=False``: the cut counts table rows) can reach.

**The downstream estimate** prices M1 on every net-new registry row and M3 on the share M1 passes, at the measured
census rates (plan 04's :func:`..masked_lm.submit.estimate_downstream_usd`: M1 $0.0072 a word, M3 $0.011 a passed word
at the assumed 0.88, flagged unmeasured for this generator until the pilot; batches x 0.5), gated by
``gapgen.cost.confirm_or_abort`` (over ``--budget-usd`` refused; over the $20 line needs ``--confirm-expensive`` and
``--confirmed-by``).

:func:`run_submit` writes ``candidates.jsonl`` **before** ``submit_candidates`` (one
:class:`~assistant_axis.gapgen.Candidate` per row: ``surface`` the row's surface, ``rank`` its union rank under the
ordering chosen by ``evaluate``, ``score`` = ``n_frames``, how many frames found it: a quality signal and **not** a
familiarity, so ``corpus_frames`` is in neither ``FAMILIARITY_GENERATORS`` nor ``CURATED_GENERATORS``; ``gloss_hint``
the OEWN sense; ``source_ref`` ``frames:<source>:<frame id>`` of its best frame), then ``keys.txt``,
``submit_report.json``, ``run.json`` (the table's and the banks' sha256, the ordering, the frames kept) and a zero-call
``usage.json``, and prints the follow-up commands.  The platform's relabel step adds each noun's adjective
(``relabel="auto"``).  A dry run prints the same and writes nothing.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.paths import DATA_CANDIDATES, REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from ..masked_lm.submit import (BATCH_FACTOR, M1_PASS_RATE_ASSUMED, M1_USD_PER_WORD, M3_USD_PER_PASSED_WORD,
                                RATES_SOURCE, Estimate, _budget)
from ..masked_lm.submit import estimate_downstream_usd as _estimate
from . import GENERATOR
from .evaluate import FRAME_FIELD, UNION_FIELD
from .table import rerank_over

#: The pilot's cap (plan section 10: about $3-5 live, cap $8).
DEFAULT_BUDGET_USD = 8.0
TOP_PER_FRAME_DEFAULT = 25
#: The wave's size in review terms (plan 09 decision 1, plan 04: about two hours at the measured rate).
KEPT_TARGET_DEFAULT = 300
#: Net-new kept rows per net-new row submitted: the proxy's ~0.3 (plan, "Baseline": net-new share 0.25-0.35, M1 trait
#: share 0.65-0.88, M3 kept share 0.42-0.49), until the pilot measures this generator's own.
KEPT_SHARE_ASSUMED = 0.3
#: The review rate when plan 13's measurement is not available (146 terms an active hour on the TDA batch, plan 13 § 6).
REVIEW_TERMS_PER_HOUR_PLAN = 146.0
REVIEW_RATE_SOURCE_PLAN = "plan figure, 146 terms an active hour (plan 13 section 6, review_tda_1)"
REVIEW_OVERSHOOT = 1.5

__all__ = ["M1_USD_PER_WORD", "M3_USD_PER_PASSED_WORD", "M1_PASS_RATE_ASSUMED", "BATCH_FACTOR", "RATES_SOURCE",
           "Estimate", "DEFAULT_BUDGET_USD", "TOP_PER_FRAME_DEFAULT", "KEPT_TARGET_DEFAULT", "KEPT_SHARE_ASSUMED",
           "REVIEW_TERMS_PER_HOUR_PLAN", "REVIEW_OVERSHOOT", "ReviewLoadExceeded", "estimate_downstream_usd",
           "review_terms_per_hour", "has_sibling", "sibling_net_new", "charged_rows", "select_top", "select_wave",
           "source_ref_for", "parse_source_ref", "to_candidates", "status", "strata", "batch_id_for",
           "followup_commands", "SubmitSummary", "run_submit"]


class ReviewLoadExceeded(ValueError):
    """The selection's projected kept rows overshoot the review target."""


def estimate_downstream_usd(n: int, *, transport: str = "live", pass_rate: float = M1_PASS_RATE_ASSUMED) -> Estimate:
    """M1 on ``n`` rows and M3 on the share M1 passes, at the measured census rates (plan 04's estimate)."""
    return _estimate(n, transport=transport, pass_rate=pass_rate)


def review_terms_per_hour(source: str = "measured", *, review_dirs: Optional[Sequence[Path]] = None
                          ) -> tuple[float, str]:
    """``(terms an hour, where the figure comes from)``: plan 13's pooled measured rate (``source="measured"``, the
    default now that ``assistant_axis.gapgen.testing.pooled_review_rate`` exists) over the review batches with
    decisions, else the plan's 146 an hour, flagged; ``"plan"`` gives the plan's figure."""
    if source == "plan":
        return REVIEW_TERMS_PER_HOUR_PLAN, REVIEW_RATE_SOURCE_PLAN
    if source != "measured":
        raise ValueError(f"review rate source must be 'measured' or 'plan', not {source!r}")
    try:
        from assistant_axis.gapgen.testing import pooled_review_rate
    except ImportError:
        return REVIEW_TERMS_PER_HOUR_PLAN, REVIEW_RATE_SOURCE_PLAN + " (plan 13's pooled_review_rate not importable)"
    dirs = list(review_dirs if review_dirs is not None else
                sorted(p.parent for p in (DATA_CANDIDATES / "review").glob("*/decisions.jsonl")))
    try:
        rr = pooled_review_rate(dirs)
    except Exception as exc:  # noqa: BLE001 - a malformed log must not stop a submission; say so
        print(f"NOTE: plan 13's pooled_review_rate failed ({exc!r}); using the plan's figure", file=sys.stderr)
        return REVIEW_TERMS_PER_HOUR_PLAN, REVIEW_RATE_SOURCE_PLAN
    tpm = getattr(rr, "terms_per_active_minute", None)
    if not tpm:
        return REVIEW_TERMS_PER_HOUR_PLAN, (f"{REVIEW_RATE_SOURCE_PLAN}; plan 13's pooled_review_rate found no "
                                            f"decisions in {len(dirs)} review batches")
    return float(tpm) * 60.0, f"measured, plan 13's pooled_review_rate over {len(rr.batches)} review batches"


# --------------------------------------------------------------------------- what a row makes in the registry

def has_sibling(row: Mapping) -> bool:
    """The row's surface is a noun the helper relabels: the platform adds the adjective (the row's stem) beside it."""
    return bool(row.get("surface_stem")) and row.get("surface_stem") != row.get("stem")


def sibling_net_new(row: Mapping) -> bool:
    """The noun of a relabelled row is itself a row the registry has not yet filtered."""
    return has_sibling(row) and bool((row.get("surface_tags") or {}).get("net_new", True))


def charged_rows(row: Mapping) -> int:
    """Net-new registry rows the row makes: its stem's (the label) and, for a relabelled noun, the noun's."""
    return int(bool(row.get("net_new"))) + int(sibling_net_new(row))


# --------------------------------------------------------------------------- selection

def _eligible(table: Sequence[Mapping]) -> list[Mapping]:
    return [r for r in table if r.get("eligible") and r.get("stem")]


def select_top(table: Sequence[Mapping], n_per_frame: int, *, frame_keys: Optional[Iterable[str]] = None,
               ordering: str = "volumes") -> tuple[list[Mapping], dict[str, list[str]]]:
    """``(rows, {frame: [stems]})``: the top ``n_per_frame`` eligible rows of every frame by within-frame rank (the
    ordering's), deduplicated, in union-rank order; registered rows taken like any other (module docstring)."""
    fr_field, un_field = FRAME_FIELD[ordering], UNION_FIELD[ordering]
    pool = _eligible(table)
    keys = sorted(set(frame_keys) if frame_keys is not None else {k for r in pool for k in r.get("frames") or {}})
    selection: dict[str, list[str]] = {}
    chosen: dict[str, Mapping] = {}
    for k in keys:
        rows = sorted((r for r in pool if k in (r.get("frames") or {})), key=lambda r: int(r["frames"][k][fr_field]))
        top = rows[:max(0, int(n_per_frame))]
        selection[k] = [r["stem"] for r in top]
        for r in top:
            chosen.setdefault(r["stem"], r)
    return sorted(chosen.values(), key=lambda r: int(r[un_field])), selection


def select_wave(table: Sequence[Mapping], *, kept_target: int = KEPT_TARGET_DEFAULT,
                kept_share: float = KEPT_SHARE_ASSUMED, frames_kept: Iterable[str], ordering: str = "volumes",
                count_siblings: bool = True) -> tuple[list[Mapping], int]:
    """``(rows in wave order, net-new rows counted)``: rows found by ``frames_kept``, ranked by RRF over those frames
    (``wave_rank``), until the counted net-new rows reach ``ceil(kept_target / kept_share)`` (module docstring)."""
    if not 0 < kept_share <= 1:
        raise ValueError(f"--kept-share must be in (0, 1], got {kept_share}")
    need = math.ceil(int(kept_target) / float(kept_share))
    ranked = rerank_over(_eligible(table), frames_kept, ordering=ordering)
    out, counted = [], 0
    for r in ranked:
        if counted >= need:
            break
        out.append(r)
        counted += int(bool(r.get("net_new"))) + (int(sibling_net_new(r)) if count_siblings else 0)
    return out, counted


# --------------------------------------------------------------------------- candidates

def source_ref_for(frame_key: str) -> str:
    """``frames:books:<frame id>`` for a Books frame, ``frames:<source>:<frame id>`` for a text frame
    (``pippa.copular_list`` -> ``frames:pippa:copular_list``)."""
    src, sep, base = frame_key.partition(".")
    return f"frames:{src}:{base}" if sep else f"frames:books:{frame_key}"


def parse_source_ref(ref: str) -> dict:
    """``{"source", "frame", "frame_key"}`` of a corpus-frames ``source_ref``; ``ValueError`` for anything else."""
    parts = str(ref).split(":")
    if len(parts) != 3 or parts[0] != "frames" or not parts[1] or not parts[2]:
        raise ValueError(f"not a corpus-frames source_ref: {ref!r}")
    key = parts[2] if parts[1] == "books" else f"{parts[1]}.{parts[2]}"
    return {"source": parts[1], "frame": parts[2], "frame_key": key}


def to_candidates(rows: Sequence[Mapping], run_id: str, *, ordering: str = "volumes") -> list[Candidate]:
    """One candidate per row (module docstring)."""
    f = UNION_FIELD[ordering]
    return [Candidate(surface=r["surface"], generator=GENERATOR, run_id=run_id, rank=int(r[f]),
                      score=float(r["n_frames"]), gloss_hint=r.get("gloss_hint"), sense_id=1,
                      source_ref=source_ref_for(r["best_frame"])) for r in rows]


def status(row: Mapping) -> str:
    """``corpus``, ``queued``, ``registered-decided``, ``registered-pending`` or ``new``."""
    if row.get("corpus_stem_match"):
        return "corpus"
    if row.get("queue_stem_match"):
        return "queued"
    if row.get("registered"):
        return "registered-decided" if row.get("registered_decided") else "registered-pending"
    return "new"


def strata(rows: Sequence[Mapping], frame_types: Mapping[str, str]) -> dict:
    """Frame type (of the best frame) x form x status, the Zipf bands, the sources, the noun siblings."""
    from ..censuses.ingest import zipf_band
    tfs = Counter(f"{frame_types.get(r['best_frame'], '?')} | {r.get('form')} | {status(r)}" for r in rows)
    return {"type_x_form_x_status": dict(sorted(tfs.items())),
            "status": dict(sorted(Counter(status(r) for r in rows).items())),
            "zipf_band": dict(sorted(Counter(zipf_band(r.get("zipf")) for r in rows).items())),
            "source": dict(sorted(Counter(s for r in rows for s in r.get("sources") or []).items())),
            "noun_siblings": sum(1 for r in rows if has_sibling(r)),
            "noun_siblings_net_new": sum(1 for r in rows if sibling_net_new(r))}


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
        f"{py}/gap_registry.py submit --from {rel}   # main checkout: resubmit into its own registry log (idempotent; "
        f"the noun siblings are derived again)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport {t} "
        f"--budget-usd {cap1:.0f}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport {t} "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # M3 on the rows M1 passes, estimate ${est.m3_usd:.2f}",
        f"{py}/recovery_test.py --generator {GENERATOR} --run-id {run_id} --budget-usd 8   # optional: about $5 a "
        f"seed (paid; Roger's call)",
        f"{py}/corpus_frames_generator.py evaluate --pilot-run {run_id}   # after M1 and M3 ($0): the frame measures "
        f"and the frames kept (pilot)",
        f"{py}/corpus_frames_generator.py report --run-id {run_id}   # the readout ($0)",
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
    selection_by_frame: dict = field(default_factory=dict)


def run_submit(run_id: str, *, table: Sequence[Mapping], frame_types: Mapping[str, str],
               top_per_frame: Optional[int] = None, kept_target: Optional[int] = None,
               kept_share: float = KEPT_SHARE_ASSUMED, frames_kept: Optional[Iterable[str]] = None,
               ordering: str = "volumes", count_siblings: bool = True, budget_usd: float = DEFAULT_BUDGET_USD,
               confirm_expensive: bool = False, confirmed_by: Optional[str] = None, transport: str = "live",
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               table_path: Optional[Path] = None, table_sha256: Optional[str] = None,
               bank_sha256: Optional[str] = None, text_bank_sha256: Optional[str] = None,
               review_rate: Optional[tuple[float, str]] = None, relabel="auto", corpus_stems=None,
               extra_args: Optional[Mapping] = None, echo=print) -> SubmitSummary:
    """Select, estimate, gate, record and submit (module docstring).  Exactly one of ``top_per_frame`` (the pilot)
    and ``kept_target`` (the wave, which needs ``frames_kept``).  ``table`` must carry the registry's current tags
    (:func:`.table.tag_rows`).  ``relabel`` and ``corpus_stems`` go to ``submit_candidates``."""
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    if (top_per_frame is None) == (kept_target is None):
        raise ValueError("give exactly one of --top-per-frame N (the pilot) and --kept-target K (the wave)")
    if ordering not in UNION_FIELD:
        raise ValueError(f"ordering must be volumes or lift, not {ordering!r}")
    rate, rate_src = review_rate or review_terms_per_hour("plan")
    selection: dict[str, list[str]] = {}
    if top_per_frame is not None:
        mode = f"top {top_per_frame} per frame by within-frame {ordering} rank"
        rows, selection = select_top(table, top_per_frame, frame_keys=frames_kept, ordering=ordering)
        n_counted = sum(charged_rows(r) for r in rows)
    else:
        if frames_kept is None:
            raise ValueError("the wave needs the frames kept after the pilot (evaluate --pilot-run writes them)")
        frames_kept = list(frames_kept)
        mode = (f"kept target {kept_target} at net-new kept share {kept_share} over {len(frames_kept)} frames kept, "
                f"by RRF over their {ordering} ranks" + ("" if count_siblings else "; noun siblings not counted"))
        rows, n_counted = select_wave(table, kept_target=kept_target, kept_share=kept_share, frames_kept=frames_kept,
                                      ordering=ordering, count_siblings=count_siblings)
    n_charged = sum(charged_rows(r) for r in rows)
    n_filtered = sum(1 for r in rows if not r.get("net_new"))
    cands = to_candidates(rows, run_id, ordering=ordering)
    est = estimate_downstream_usd(n_charged, transport=transport)
    st = strata(rows, frame_types)
    projected = n_charged * kept_share
    hours = projected / rate if rate else None
    assumed = kept_share == KEPT_SHARE_ASSUMED
    echo(f"{mode}: {len(table)} table rows, {sum(1 for r in table if r.get('eligible'))} eligible; selected "
         f"{len(rows)} ({sum(1 for r in rows if r.get('net_new'))} net-new, {n_filtered} already filtered by the "
         f"registry: corpus traits, queued, or decided by M1 and M3, submitted and not counted; {st['noun_siblings']} "
         f"nouns whose adjective the platform adds, {st['noun_siblings_net_new']} of them net-new)")
    echo(f"  projection: {n_charged} net-new registry rows x net-new kept share {kept_share} = {projected:.0f} kept "
         f"rows"
         + (f" against the target {kept_target}" if kept_target is not None else "")
         + (f", about {hours:.1f} h of review at {rate:.0f} terms an hour ({rate_src})" if hours is not None else "")
         + ("  [kept share ASSUMED (the proxy's 0.3): pass the pilot's measured net-new kept share with --kept-share]"
            if assumed and kept_target is not None else ""))
    for k, v in st.items():
        echo(f"  {k}: {v}")
    echo(est.format() + f"\n  [{n_charged} net-new registry rows of the {len(rows)} selected (each relabelled noun is "
                        f"two rows); M1 and M3 skip the rest]")
    if kept_target is not None and projected > REVIEW_OVERSHOOT * kept_target:
        raise ReviewLoadExceeded(
            f"the selection's projected kept rows ({projected:.0f}) exceed {REVIEW_OVERSHOOT}x the target "
            f"{kept_target}: the cut counted {n_counted} rows, but the {st['noun_siblings_net_new']} net-new noun "
            f"siblings the platform adds are reviewed too.  Count them in the cut (the default, --count-siblings), or "
            f"lower --kept-target: a review-hours decision, Roger's")
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(run_id=run_id, mode=mode, n_table=len(table), n_selected=len(rows), n_counted=n_counted,
                            n_filtered=n_filtered, n_charged=n_charged, estimate=asdict(est), strata=st,
                            dry_run=dry_run, n_candidates=len(cands), projected_kept=round(projected, 1),
                            review_hours=None if hours is None else round(hours, 2), selection_by_frame=selection)
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    args = {"step": "submit", "mode": mode, "top_per_frame": top_per_frame, "kept_target": kept_target,
            "kept_share": kept_share, "kept_share_assumed": assumed, "ordering": ordering,
            "count_siblings": bool(count_siblings),
            "frames_kept": sorted(frames_kept) if frames_kept is not None else None,
            "n_rows": len(rows), "n_candidates": len(cands), "n_counted": n_counted, "n_filtered": n_filtered,
            "n_charged": n_charged, "selection_by_frame": selection,
            "wave_order": [r["stem"] for r in rows] if kept_target is not None else None,
            "counted_stems": sorted(r["stem"] for r in rows if r.get("net_new")),
            "sibling_stems": {r["stem"]: r["surface_stem"] for r in rows if has_sibling(r)},
            "sibling_counted_stems": sorted(r["surface_stem"] for r in rows if sibling_net_new(r)),
            "registered_stems": {r["stem"]: list(r.get("registered_by") or []) for r in rows if r.get("registered")},
            "decided_stems": sorted(r["stem"] for r in rows if r.get("registered_decided")),
            "corpus_stems": sorted(r["stem"] for r in rows if r.get("corpus_stem_match")),
            "queued_stems": sorted(r["stem"] for r in rows if r.get("queue_stem_match")),
            "transport": transport, "budget_usd": budget_usd, "estimate": asdict(est), "strata": st,
            "review_terms_per_hour": rate, "review_rate_source": rate_src, "projected_kept": round(projected, 1),
            "table": str(table_path) if table_path else None, "table_sha256": table_sha256,
            "bank_sha256": bank_sha256, "text_bank_sha256": text_bank_sha256,
            "score": "n_frames (how many frames found the word; a quality signal, not a familiarity)",
            **dict(extra_args or {})}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=registry_path, relabel=relabel, corpus_stems=corpus_stems)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {
        "n_keys": len(rep.keys), "rows_submitted": len(rows), "rows_counted": n_counted,
        "rows_already_filtered": n_filtered, "rows_charged": n_charged, "n_candidates": len(cands)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    ctx.finish()
    summary.run_dir = str(ctx.dir)
    summary.report = rep_d
    echo(f"registry {registry_path}: {json.dumps({k: v for k, v in rep_d.items() if k != 'relabels'})}")
    echo(f"wrote {ctx.dir}/candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json")
    for c in summary.followups:
        echo(f"  then: {c}")
    return summary
