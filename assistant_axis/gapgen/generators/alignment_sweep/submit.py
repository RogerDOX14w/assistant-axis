"""Candidates, the downstream estimate and the submission of an alignment-sweep run.

:func:`to_candidates`: one :class:`~assistant_axis.gapgen.Candidate` per dedup group representative that is kept
(never a ``mechanism`` item as it is, never an ``enactability none`` item, never a pole the label rule dropped), in
rank order: ``surface`` its label, ``gloss_hint`` its gloss (M1 judges the intended sense), ``partner_hint`` the
label of its partner group's representative (``promote`` sets ``partner`` on both when both are promoted),
``rank`` the pair's rank, ``score`` None, ``source_ref`` the chunk id (``model_spec:2026-08-18:avoid_sycophancy``:
source, version, section).  ``sense_id`` is 1, and 2 for a surface already submitted for the other pole (the same
label as a virtue in one pair and a vice in another is a second sense).

:func:`run_submit` follows the censuses recipe: print the downstream estimate (the platform's M1 on every word, M3 on
those M1 passes, at the censuses' measured rates; alignment-region rows run M3 at cut-off 4, sending Sonnet's 2s
and 3s to Opus, so M3 is gated at :data:`M3_ALIGNMENT_RISK` times its estimate), gate it with ``confirm_or_abort``
(over ``--budget-usd`` refused; over $20 needs ``--confirm-expensive --confirmed-by``), open the run session, write
``candidates.jsonl`` **before** ``submit_candidates``, then ``keys.txt``, ``submit_report.json`` and
``submitted_items.json`` (each key with its representative item and the group's members), and print the follow-up
commands.  Submitting is $0.  A dry run prints the same and writes nothing.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.generators.censuses.submit import (
    M1_PASS_RATE, M1_USD_PER_WORD, M3_USD_PER_PASSED_WORD, RATES_SOURCE,
)
from assistant_axis.gapgen.normalize import make_key, normalize_candidate
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from . import GENERATOR
from .dedupe import Group
from .extract import Item

#: Alignment-region rows run M3 at cut-off 4 (Sonnet's 2s and 3s go to Opus, about $0.003 a pair), so M3 may run
#: about 1.5 times the censuses' rate (coding plan § 7).
M3_ALIGNMENT_RISK = 1.5
#: M1's third opinion on the 10% Sonnet sample (the model-per-generator measurement).
THIRD_MODEL = "claude-opus-5-5"


@dataclass
class Estimate:
    n: int
    m1_usd: float
    m3_usd: float
    m3_high_usd: float
    gate_usd: float
    assumptions: dict = field(default_factory=dict)

    def format(self) -> str:
        return (f"downstream estimate for {self.n} words (live): M1 filter ${self.m1_usd:.2f} + M3 novelty "
                f"${self.m3_usd:.2f} (up to ${self.m3_high_usd:.2f} at {M3_ALIGNMENT_RISK:g}x for the cut-off-4 "
                f"rows) = ${self.m1_usd + self.m3_usd:.2f}, gated at ${self.gate_usd:.2f}  "
                f"[{M1_USD_PER_WORD}/word M1, {M3_USD_PER_PASSED_WORD}/passed word M3 at {M1_PASS_RATE:.0%} passed; "
                f"{RATES_SOURCE}; submitting itself $0]")


def estimate_downstream_usd(n: int) -> Estimate:
    m1 = round(n * M1_USD_PER_WORD, 4)
    m3 = round(n * M1_PASS_RATE * M3_USD_PER_PASSED_WORD, 4)
    m3h = round(m3 * M3_ALIGNMENT_RISK, 4)
    return Estimate(n=n, m1_usd=m1, m3_usd=m3, m3_high_usd=m3h, gate_usd=round(m1 + m3h, 4),
                    assumptions={"m1_usd_per_word": M1_USD_PER_WORD, "m3_usd_per_passed_word": M3_USD_PER_PASSED_WORD,
                                 "m1_pass_rate": M1_PASS_RATE, "m3_alignment_risk": M3_ALIGNMENT_RISK,
                                 "source": RATES_SOURCE})


def _key(surface: str, sense_id: int) -> Optional[str]:
    try:
        return make_key(normalize_candidate(surface).stem, sense_id)
    except ValueError:
        return None


def submitted_rows(items: Sequence[Item], groups: Sequence[Group],
                   hints: Mapping[str, Optional[str]]) -> list[dict]:
    """The rows :func:`to_candidates` submits, with their items: ``{"item", "members", "partner_hint",
    "sense_id"}`` in rank order."""
    by = {it.item_id: it for it in items}
    out, poles_of_stem = [], {}
    for g in sorted(groups, key=lambda g: (by[g.rep].rank, g.rep)):
        it = by[g.rep]
        if not it.kept or it.type == "mechanism" or it.enactability == "none":
            continue
        stem = it.stem or it.label
        seen = poles_of_stem.setdefault(stem, [])
        if it.pole not in seen:
            seen.append(it.pole)
        sense = seen.index(it.pole) + 1
        out.append({"item": it, "members": list(g.members), "partner_hint": hints.get(g.rep), "sense_id": sense})
    return out


def to_candidates(items: Sequence[Item], groups: Sequence[Group], hints: Mapping[str, Optional[str]],
                  run_id: str) -> list[Candidate]:
    """One candidate per kept group representative (module docstring)."""
    return [Candidate(surface=r["item"].label, generator=GENERATOR, run_id=run_id, rank=r["item"].rank, score=None,
                      gloss_hint=r["item"].gloss, sense_id=r["sense_id"], source_ref=r["item"].chunk_id,
                      partner_hint=r["partner_hint"]) for r in submitted_rows(items, groups, hints)]


def batch_id_for(run_id: str) -> str:
    return f"{run_id}_{GENERATOR}"


def _cap(x: float) -> float:
    """The first-of-kind rule for a follow-up cap: 1.5 x the estimate + $2, rounded up to a dollar."""
    return float(math.ceil(1.5 * x + 2.0))


def followup_commands(run_id: str, est: Estimate, *, candidates_path: Optional[Path] = None) -> list[str]:
    b = batch_id_for(run_id)
    py = "uv run python data_analysis/gap_generation"
    cap1, cap3 = _cap(est.m1_usd), _cap(est.m3_high_usd)

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""

    rel = candidates_path or run_dir(GENERATOR, run_id) / "candidates.jsonl"
    try:
        rel = Path(rel).resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    return [
        f"{py}/gap_registry.py submit --from {rel}   # main checkout: into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport live "
        f"--budget-usd {cap1:.0f} --third-model {THIRD_MODEL}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport live "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # M3, estimate ${est.m3_usd:.2f} (to ${est.m3_high_usd:.2f})",
        f"{py}/alignment_sweep.py gate --run-id {run_id}   # the enactability gate on M3's kept rows",
        f"{py}/alignment_sweep.py probe --run-id {run_id}   # the Qwen label probe (DeepInfra, US)",
        f"{py}/alignment_sweep.py report --run-id {run_id}   # readout.md",
        f"{py}/alignment_sweep.py report --run-id {run_id} --gold   # gold recovery (gold_recovery.md)",
    ]


@dataclass
class SubmitSummary:
    run_id: str
    n_candidates: int
    estimate: dict
    dry_run: bool
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    report_keys: list = field(default_factory=list)
    followups: list = field(default_factory=list)


def run_submit(run_id: str, *, items: Sequence[Item], groups: Sequence[Group], hints: Mapping[str, Optional[str]],
               budget_usd: float = 5.0, confirm_expensive: bool = False, confirmed_by: Optional[str] = None,
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               extra_args: Optional[dict] = None, echo=print) -> SubmitSummary:
    check_id(run_id, "run_id")
    rows = submitted_rows(items, groups, hints)
    cands = to_candidates(items, groups, hints, run_id)
    est = estimate_downstream_usd(len(cands))
    n_pairs = sum(1 for r in rows if r["partner_hint"])
    echo(f"run {run_id}: {len(cands)} candidates from {len(groups)} dedup groups ({n_pairs} with a partner hint)")
    echo(est.format())
    confirm_or_abort(est.gate_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summ = SubmitSummary(run_id=run_id, n_candidates=len(cands), estimate=asdict(est), dry_run=dry_run,
                         followups=followup_commands(run_id, est, candidates_path=target / "candidates.jsonl"))
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, submitted_items.json, run.json, usage.json")
        for c in summ.followups:
            echo(f"  then: {c}")
        return summ
    ctx = start_run(GENERATOR, run_id, candidates_dir=candidates_dir, args={
        "step": "submit", "n": len(cands), "budget_usd": budget_usd, "estimate": asdict(est), **(extra_args or {})})
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first: the tracked record of the run
    rep = submit_candidates(cands, registry_path=registry_path)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    mapping = [{"key": _key(r["item"].label, r["sense_id"]), "surface": r["item"].label, "sense_id": r["sense_id"],
                "item_id": r["item"].item_id, "pole": r["item"].pole, "members": r["members"],
                "partner_hint": r["partner_hint"], "source_ref": r["item"].chunk_id} for r in rows]
    atomic_write_text(json.dumps(mapping, indent=1, ensure_ascii=False) + "\n", ctx.dir / "submitted_items.json")
    ctx.finish()
    summ.run_dir, summ.report, summ.report_keys = str(ctx.dir), rep_d, list(rep.keys)
    echo(f"registry {registry_path}: {json.dumps(rep_d)}")
    echo(f"wrote {ctx.dir}/candidates.jsonl, keys.txt, submit_report.json, submitted_items.json, run.json, usage.json")
    for c in summ.followups:
        echo(f"  then: {c}")
    return summ


__all__ = ["Candidate", "Estimate", "SubmitSummary", "M3_ALIGNMENT_RISK", "THIRD_MODEL", "estimate_downstream_usd",
           "submitted_rows", "to_candidates", "batch_id_for", "followup_commands", "run_submit", "submit_candidates"]
