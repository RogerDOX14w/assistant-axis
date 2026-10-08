"""Stages, samples, the downstream estimate and the submission of a census run.

A run is one stage of the table (or an ``--extra-list`` file), optionally every n-th row of it
in rank order (the pilot: ``--every-nth 5`` of the TDA).  :func:`run_submit`:

1. selects the rows and builds one :class:`~assistant_axis.gapgen.Candidate` per row;
2. prints the strata and the **downstream estimate** (the platform's M1 filter on every word and
   its M3 novelty scorer on the words M1 passes; this generator makes no call itself) and gates
   it with ``gapgen.cost.confirm_or_abort``: over ``--budget-usd`` is refused, over the $20 line
   needs ``--confirm-expensive`` and ``--confirmed-by``.  Submitting is free; the guard sits
   here because the run's size is decided here;
3. opens the run (``start_run``), writes ``candidates.jsonl`` (one ``dataclasses.asdict``
   per candidate) **before** calling ``submit_candidates``, so the main checkout can resubmit
   the file into its own registry log; then submits, writes ``keys.txt`` and
   ``submit_report.json``, and finishes the run (``run.json`` and a zero-call ``usage.json``);
4. prints the follow-up commands (resubmission, M1, M3, recovery, report).

A dry run prints the same and writes nothing.

Stage ``allport_rare`` (Roger, 2026-10-09, QUESTIONS 34): the Allport-only words that ``wordfreq``
or OEWN know but that sit below the dictionary floor (Zipf 1.5; the table's ``ineligible_reason``
``below_hard_reject``, 1,341 words).  The table leaves them ineligible under the plan's floor; this
stage submits them on purpose, last, after ``allport_hi`` and ``allport_probe``, opening with a 10%
pilot (``--every-nth 10``) to see the yield.  The words neither tool knows (``unknown_word``) are
never submitted.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from . import GENERATOR
from .ingest import STAGE_HI, STAGE_PROBE, STAGE_TDA, TableRow, clean_surface, zipf_band

#: The known-but-rare Allport words, submitted last on purpose (QUESTIONS 34).
STAGE_RARE = "allport_rare"
STAGES = (STAGE_TDA, STAGE_HI, STAGE_PROBE, STAGE_RARE, "extra")

#: Platform cost per word, from the plan's revision of 2026-10-08 (section 4): M1 (the split
#: filter, Haiku 5.5, three readings) about $0.004 per submitted word; M3 about $0.018 per word
#: M1 passes, at a pass rate of about 90% for near-corpus words.  Batches are half price.
#: Measured on the 2026-10-08 pilots (overnight_readout_2026-10-08.md, section 6): M1 $3.63 on 509 TDA words
#: ($0.0071; Roget $0.0078, WordNet $0.0071); M3 $4.71 on 447 TDA words M1 passed ($0.0105; Roget and WordNet
#: $0.013); the TDA passed M1 at 88%.  The plan's first figures ($0.004, $0.018, 90%) were guesses.
M1_USD_PER_WORD = 0.0072
M3_USD_PER_PASSED_WORD = 0.011
M1_PASS_RATE = 0.88
BATCH_FACTOR = 0.5
RATES_SOURCE = "measured on the 2026-10-08 pilots (overnight_readout_2026-10-08.md, section 6)"


@dataclass
class Estimate:
    n: int
    transport: str
    m1_usd: float
    m3_usd: float
    total_usd: float
    assumptions: dict = field(default_factory=dict)

    def format(self) -> str:
        return (f"downstream estimate for {self.n} words ({self.transport}): M1 filter ${self.m1_usd:.2f} "
                f"+ M3 novelty ${self.m3_usd:.2f} = ${self.total_usd:.2f}  "
                f"[{self.assumptions['m1_usd_per_word']}/word M1, {self.assumptions['m3_usd_per_passed_word']}"
                f"/passed word M3 at {self.assumptions['m1_pass_rate']:.0%} passed"
                f"{', batches x0.5' if self.transport == 'batches' else ''}; generator itself $0]")


def estimate_downstream_usd(n: int, *, transport: str = "live") -> Estimate:
    f = BATCH_FACTOR if transport == "batches" else 1.0
    m1 = round(n * M1_USD_PER_WORD * f, 4)
    m3 = round(n * M1_PASS_RATE * M3_USD_PER_PASSED_WORD * f, 4)
    return Estimate(n=n, transport=transport, m1_usd=m1, m3_usd=m3, total_usd=round(m1 + m3, 4),
                    assumptions={"m1_usd_per_word": M1_USD_PER_WORD, "m3_usd_per_passed_word": M3_USD_PER_PASSED_WORD,
                                 "m1_pass_rate": M1_PASS_RATE, "batch_factor": f, "source": RATES_SOURCE})


def select_stage(rows: Sequence[TableRow], stage: str) -> list[TableRow]:
    """Eligible rows of one stage, in rank order."""
    if stage not in STAGES or stage == "extra":
        raise ValueError(f"not a table stage: {stage!r} (one of {STAGES[:4]})")
    if stage == STAGE_RARE:
        return sorted((r for r in rows if r.stem and not r.tda and r.ineligible_reason == "below_hard_reject"),
                      key=lambda r: r.rank)
    return sorted((r for r in rows if r.eligible and r.stage == stage), key=lambda r: r.rank)


def every_nth(rows: Sequence[TableRow], n: int, offset: int = 0) -> list[TableRow]:
    """Every ``n``-th row (positions ``offset``, ``offset + n``, ...) in the given order: a
    systematic sample, spread evenly over familiarity (TDA) or frequency (Allport-Odbert)."""
    if n < 1 or not 0 <= offset < n:
        raise ValueError(f"--every-nth must be >= 1 and 0 <= --offset < n (got {n}, {offset})")
    return [r for i, r in enumerate(rows) if i % n == offset]


def extra_rows(path: Path) -> list[TableRow]:
    """``--extra-list``: one word or phrase per line (``#`` comments and blanks skipped), as table
    rows of stage ``extra`` with no census data (rank = line number)."""
    out = []
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        raw = line.split("#", 1)[0].strip()
        if not raw:
            continue
        s = clean_surface(raw)
        if s is None:
            continue
        out.append(TableRow(schema_version=1, surface=s, stem=None, label=s, allport=None, in_merged=None, tda=None,
                            zipf=None, freq_hard_reject=None, freq_probe_band=None, freq_rescue=None,
                            freq_platform=None, wordnet=None, gloss_hint=None, repaired_from=None,
                            unknown_word=False, eligible=True, ineligible_reason=None, stage="extra", rank=i,
                            score=None, corpus_stem_match=False, queue_stem_match=False))
    return out


def to_candidates(rows: Sequence[TableRow], run_id: str, *, extra_name: Optional[str] = None) -> list[Candidate]:
    """One candidate per row: TDA rows carry ``score = prop`` (a documented familiarity,
    ``gapgen.freq.FAMILIARITY_GENERATORS``) and ``source_ref = "tda:<row>"``; Allport-only rows
    ``score = None`` and ``"allport:<column>:<line>"``; ``sense_id`` is always 1 (the censuses
    give no sense; polysemy is the filter's)."""
    out = []
    for r in rows:
        ref = r.source_ref if r.stage != "extra" else f"extra:{extra_name or 'list'}:{r.rank}"
        out.append(Candidate(surface=r.surface, generator=GENERATOR, run_id=run_id, rank=r.rank, score=r.score,
                             gloss_hint=r.gloss_hint, sense_id=1, source_ref=ref))
    return out


def strata(rows: Sequence[TableRow]) -> dict[str, int]:
    """Counts by Zipf band x corpus match (what the pilot's sample is spread over)."""
    c = Counter(f"{zipf_band(r.zipf)} | {'corpus' if r.corpus_stem_match else 'new'}" for r in rows)
    return dict(sorted(c.items()))


def batch_id_for(run_id: str) -> str:
    return f"{run_id}_{GENERATOR}"


def _budget(x: float) -> float:
    """The first-of-kind rule for a follow-up cap: 1.5 x the estimate + $2, rounded up to $1."""
    import math
    return float(math.ceil(1.5 * x + 2.0))


def followup_commands(run_id: str, est: Estimate, *, candidates_path: Optional[Path] = None) -> list[str]:
    b = batch_id_for(run_id)
    t = est.transport
    py = "uv run python data_analysis/gap_generation"
    cap1, cap3 = _budget(est.m1_usd), _budget(est.m3_usd)

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""

    rel = candidates_path or run_dir(GENERATOR, run_id) / "candidates.jsonl"
    try:
        rel = Path(rel).relative_to(REPO_ROOT)
    except ValueError:
        pass
    return [
        f"{py}/gap_registry.py submit --file {rel} --generator {GENERATOR} --run-id {run_id}   "
        f"# main checkout: resubmit into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --transport {t} "
        f"--budget-usd {cap1:.0f}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --transport {t} "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # M3 on the words M1 passes, estimate ${est.m3_usd:.2f}",
        f"{py}/recovery_test.py --generator {GENERATOR} --run-id {run_id}   # once the platform close-out lands",
        f"{py}/census_generator.py report --run-id {run_id}",
    ]


@dataclass
class SubmitSummary:
    stage: str
    run_id: str
    n_stage: int
    n_selected: int
    estimate: dict
    strata: dict
    dry_run: bool
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list[str] = field(default_factory=list)


def run_submit(stage: str, run_id: str, *, table: Sequence[TableRow], sources_manifest: list,
               every_nth_n: Optional[int] = None, offset: int = 0, extra_list: Optional[Path] = None,
               budget_usd: float = 5.0, confirm_expensive: bool = False, confirmed_by: Optional[str] = None,
               transport: str = "live", dry_run: bool = False, registry_path: Path = REGISTRY_PATH,
               candidates_dir: Optional[Path] = None, table_sha256: Optional[str] = None,
               table_path: Optional[Path] = None, echo=print) -> SubmitSummary:
    check_id(run_id, "run_id")
    if stage not in STAGES:
        raise ValueError(f"--stage must be one of {STAGES}")
    if stage == "extra":
        if extra_list is None:
            raise ValueError("--stage extra needs --extra-list PATH")
        pool = extra_rows(extra_list)
    else:
        pool = select_stage(table, stage)
    rows = every_nth(pool, every_nth_n, offset) if every_nth_n else list(pool)
    cands = to_candidates(rows, run_id, extra_name=Path(extra_list).name if extra_list else None)
    est = estimate_downstream_usd(len(cands), transport=transport)
    st = strata(rows)
    echo(f"stage {stage}: {len(pool)} eligible rows; selected {len(rows)}"
         + (f" (every {every_nth_n}th, offset {offset})" if every_nth_n else ""))
    for k, v in st.items():
        echo(f"  {k:28s} {v}")
    echo(est.format())
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(stage=stage, run_id=run_id, n_stage=len(pool), n_selected=len(rows),
                            estimate=asdict(est), strata=st, dry_run=dry_run)
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    args = {"stage": stage, "every_nth": every_nth_n, "offset": offset if every_nth_n else None,
            "extra_list": str(extra_list) if extra_list else None, "n": len(cands), "n_stage": len(pool),
            "transport": transport, "budget_usd": budget_usd, "estimate": asdict(est), "strata": st,
            "table": str(table_path) if table_path else None, "table_sha256": table_sha256,
            "sources": list(sources_manifest)}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=registry_path)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    ctx.finish()
    summary.run_dir = str(ctx.dir)
    summary.report = rep_d
    echo(f"registry {registry_path}: {json.dumps(rep_d)}")
    echo(f"wrote {ctx.dir}/candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json")
    for c in summary.followups:
        echo(f"  then: {c}")
    return summary
