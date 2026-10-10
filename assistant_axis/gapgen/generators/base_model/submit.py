"""Selection, the downstream estimate and its guard, and the submission of a base-model run (plan section 7).

:func:`run_submit`:

1. selects the eligible table rows (``count >= min_count``; optionally only rows a family emitted) in rank
   order and builds one :class:`~assistant_axis.gapgen.Candidate` per row: ``score`` is the emission count
   (**not** a human familiarity, so ``base_model`` is not in ``gapgen.freq.FAMILIARITY_GENERATORS`` and no
   Zipf rescue applies), ``source_ref`` is ``base_model:<family>:<first sample id>``, ``gloss_hint`` the OEWN
   person sense, ``partner_hint`` the contrast family's seed adjective, ``sense_id`` 1;
2. prints the counts per family and form and the **downstream estimate** (the platform's M1 on every word, M3
   on the words M1 passes; this generator makes no call), and gates it with ``gapgen.cost.confirm_or_abort``
   (over ``budget_usd`` refused; over the $20 line needs ``confirm_expensive`` and ``confirmed_by``);
3. opens the run, writes ``candidates.jsonl`` **before** the registry append (the main checkout resubmits
   it with ``gap_registry.py submit --from``), submits, writes ``keys.txt`` and ``submit_report.json``, merges
   the round's sampling usage (the local model's tokens at $0) into the run's usage, and finishes the run
   (``run.json``: round, prompts version, temperature, model, table sha256, the seed bundle's manifest);
4. prints the follow-up commands.

A dry run prints the same and writes nothing.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir
from assistant_axis.judge_pricing import MultiModelUsage

from . import GENERATOR

#: Measured platform rates (overnight_readout_2026-10-08.md section 6, as the censuses use them).
M1_USD_PER_WORD = 0.0072
M3_USD_PER_PASSED_WORD = 0.011
#: Base-model output is not near-corpus, so the censuses' measured 0.88 would overstate M3; the pilot measures it.
M1_PASS_RATE_ASSUMED = 0.5
BATCH_FACTOR = 0.5
DEFAULT_BUDGET_USD = 15.0
RATES_SOURCE = ("M1 $0.0072/word and M3 $0.011/passed word measured on the 2026-10-08 pilots "
                "(overnight_readout_2026-10-08.md section 6); pass rate 0.5 assumed until the pilot measures it")


@dataclass
class Estimate:
    n: int
    transport: str
    m1_usd: float
    m3_usd: float
    total_usd: float
    pass_rate: float
    assumptions: dict = field(default_factory=dict)

    def format(self) -> str:
        return (f"downstream estimate for {self.n} words ({self.transport}): M1 filter ${self.m1_usd:.2f} + M3 "
                f"novelty ${self.m3_usd:.2f} = ${self.total_usd:.2f}  [${M1_USD_PER_WORD}/word M1, "
                f"${M3_USD_PER_PASSED_WORD}/passed word M3 at {self.pass_rate:.0%} passed"
                f"{', batches x0.5' if self.transport == 'batches' else ''}; the generator itself $0]")


def estimate_downstream_usd(n: int, *, transport: str = "live", pass_rate: float = M1_PASS_RATE_ASSUMED) -> Estimate:
    f = BATCH_FACTOR if transport == "batches" else 1.0
    m1 = round(n * M1_USD_PER_WORD * f, 4)
    m3 = round(n * pass_rate * M3_USD_PER_PASSED_WORD * f, 4)
    return Estimate(n=n, transport=transport, m1_usd=m1, m3_usd=m3, total_usd=round(m1 + m3, 4), pass_rate=pass_rate,
                    assumptions={"m1_usd_per_word": M1_USD_PER_WORD, "m3_usd_per_passed_word": M3_USD_PER_PASSED_WORD,
                                 "m1_pass_rate": pass_rate, "batch_factor": f, "source": RATES_SOURCE})


def select_rows(table: Sequence[Mapping], *, min_count: int = 1,
                families: Optional[Iterable[str]] = None) -> list[Mapping]:
    """Eligible rows with ``count >= min_count`` (and, given ``families``, emitted by one of them), by rank."""
    fams = set(families or ())
    out = [r for r in table if r.get("eligible") and int(r.get("count") or 0) >= min_count
           and (not fams or fams & set(r.get("families") or {}))]
    return sorted(out, key=lambda r: r["rank"])


def to_candidates(rows: Sequence[Mapping], run_id: str) -> list[Candidate]:
    return [Candidate(surface=r["surface"], generator=GENERATOR, run_id=run_id, rank=int(r["rank"]),
                      score=float(r["count"]), gloss_hint=r.get("gloss_hint"), sense_id=1,
                      source_ref=f"{GENERATOR}:{r.get('first_family') or '?'}:{r['first_sample_id']}",
                      partner_hint=r.get("partner_seed")) for r in rows]


def strata(rows: Sequence[Mapping]) -> dict:
    fam = Counter(f for r in rows for f in (r.get("families") or {}))
    first = Counter(r.get("first_family") for r in rows)
    form = Counter(r.get("form") for r in rows)
    return {"by_family_emitted": dict(sorted(fam.items())), "by_first_family": dict(sorted(first.items())),
            "by_form": dict(sorted(form.items())), "with_partner_hint": sum(1 for r in rows if r.get("partner_seed")),
            "with_gloss_hint": sum(1 for r in rows if r.get("gloss_hint"))}


def batch_id_for(run_id: str) -> str:
    return f"{run_id}_{GENERATOR}"


def _budget(x: float) -> float:
    """The first-of-kind rule for a follow-up cap: 1.5 x the estimate + $2, rounded up to $1."""
    return float(math.ceil(1.5 * x + 2.0))


def followup_commands(run_id: str, est: Estimate, *, candidates_path: Optional[Path] = None) -> list[str]:
    b, t = batch_id_for(run_id), est.transport
    py = "uv run python data_analysis/gap_generation"
    cap1, cap3 = _budget(est.m1_usd), _budget(est.m3_usd)

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""

    rel = Path(candidates_path or run_dir(GENERATOR, run_id) / "candidates.jsonl")
    try:
        rel = rel.relative_to(REPO_ROOT)
    except ValueError:
        pass
    return [
        f"{py}/gap_registry.py submit --from {rel}   # main checkout: resubmit into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport {t} "
        f"--budget-usd {cap1:.0f}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport {t} "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # M3 on the words M1 passes, estimate ${est.m3_usd:.2f}",
        f"{py}/base_model_generator.py report --run-id {run_id}   # the readout ($0)",
        f"{py}/recovery_test.py --generator {GENERATOR} --run-id {run_id} --budget-usd 8   # optional: about $5 a "
        f"seed (paid; Roger's call)",
    ]


@dataclass
class SubmitSummary:
    run_id: str
    round: int
    n_table: int
    n_selected: int
    estimate: dict
    strata: dict
    dry_run: bool
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list[str] = field(default_factory=list)


def run_submit(run_id: str, *, table: Sequence[Mapping], round_n: int, min_count: int = 1,
               families: Optional[Iterable[str]] = None, budget_usd: float = DEFAULT_BUDGET_USD,
               confirm_expensive: bool = False, confirmed_by: Optional[str] = None, transport: str = "live",
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               table_path: Optional[Path] = None, table_sha256: Optional[str] = None,
               sampling_record: Optional[Mapping] = None, sampling_usage_path: Optional[Path] = None,
               echo=print) -> SubmitSummary:
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    rows = select_rows(table, min_count=min_count, families=families)
    cands = to_candidates(rows, run_id)
    est = estimate_downstream_usd(len(cands), transport=transport)
    st = strata(rows)
    echo(f"round {round_n}: {len(table)} table rows; selected {len(rows)} eligible (count >= {min_count}"
         + (f", families {sorted(families)}" if families else "") + ")")
    for k, v in st.items():
        echo(f"  {k}: {v}")
    echo(est.format())
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(run_id=run_id, round=round_n, n_table=len(table), n_selected=len(rows),
                            estimate=asdict(est), strata=st, dry_run=dry_run)
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    rec = dict(sampling_record or {})
    key = rec.get("key") or {}
    args = {"round": round_n, "prompts_version": key.get("prompts_version"), "wording_sha256": key.get("wording_sha256"),
            "temperature": key.get("temperatures"), "seed": key.get("seed"), "model": rec.get("model"),
            "min_count": min_count, "families": sorted(families) if families else None, "n": len(cands),
            "n_table": len(table), "transport": transport, "budget_usd": budget_usd, "estimate": asdict(est),
            "strata": st, "table": str(table_path) if table_path else None, "table_sha256": table_sha256,
            "seed_bundle": rec.get("bundle"), "sampling": rec.get("sampling")}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=registry_path)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    if sampling_usage_path is not None and Path(sampling_usage_path).exists() and not ctx.total_usage().n_calls:
        ctx.usage.merge_from(MultiModelUsage.load_or_create(sampling_usage_path))
    ctx.finish()
    summary.run_dir = str(ctx.dir)
    summary.report = rep_d
    echo(f"registry {registry_path}: {json.dumps(rep_d)}")
    echo(f"wrote {ctx.dir}/candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json")
    for c in summary.followups:
        echo(f"  then: {c}")
    return summary
