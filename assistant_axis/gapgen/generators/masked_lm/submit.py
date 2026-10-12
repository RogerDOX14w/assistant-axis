"""Selection, the downstream estimate and its guard, and the submission of a masked-LM run (plan section 7).

Two ways to choose the rows, both over **eligible** table rows in union-rank order:

* ``--top N`` (pilot B, plan section 10): the first N by union rank, whatever their class;
* ``--kept-target K`` (the wave; Roger, 2026-10-11: "Aim for ~2 hours review on this", operationalised the same
  day as ~300 M3-kept terms at about 150 terms an hour): **single-word** rows in union-rank order, cut where the
  projected kept terms reach K, i.e. the first ``ceil(K / kept_share)``, with ``kept_share`` pilot B's measured
  share (``--kept-share``; until then the census funnel's ~0.5, flagged as assumed); plus **every multiword row
  with an OEWN gloss**, never cut by rank (the route no other generator has; their gate is the gloss, not Zipf,
  which is a per-word floor and says nothing about a phrase).

**Stems already in the registry** (QUESTIONS 82, revised, Roger 2026-10-12) are submitted like any other row: the
registry merges this generator's source into the existing row at no API cost (M1 and M3 skip rows another run has
decided), so the overlap with other generators is recorded in full.  They are left out of the **counts** instead:
the rank cut counts only rows not yet registered (N, or ``ceil(K / kept_share)``, or ``--multi-cap``; a registered
row inside the cut is submitted and not counted), and so does the review-load projection; the run records which
submitted stems were registered (``run.json`` ``args.registered_stems``) so that the measured kept share is over
new words only (:func:`.evaluate.evaluate_run`).  ``--count-registered`` counts them in the cut like any row.
The downstream estimate counts the rows the platform may still charge for: new rows, and registered rows that
M1 or M3 has not yet decided (no filter block, or a trait verdict and no novelty block).

  **Subword rows join the single-word cut** (a deviation, in the acceptance report): the coordinator's reading
  also exempted them, but a subword row is one dictionary word the tokenizer happens to split (complacent,
  apologetic), Zipf applies to it, and other generators reach it; read literally, the exemption puts about 8,000
  rows in the first wave at full scale (the smoke run, scaled: about $68 batched and some 4,000 kept terms against
  the ~300 target).  ``--uncut-classes multiword,subword`` restores the literal reading.

  **The review-load guard**: when the projected kept terms (single rows and uncut rows alike, at the kept share)
  exceed :data:`REVIEW_OVERSHOOT` times the target, the submission is refused unless ``--multi-cap N`` bounds the
  uncut rows (by union rank): the cap is a review-hours decision, Roger's, and no default picks it.

:func:`run_submit` builds one :class:`~assistant_axis.gapgen.Candidate` per row: ``rank`` the union rank,
``score`` **the trait-hood contrast score** (``trait_contrast``; documented here and in the plan; not a
familiarity, so no ``FAMILIARITY_GENERATORS`` entry and no Zipf rescue), ``gloss_hint`` the OEWN sense,
``source_ref`` ``mlm:<pass>:<model>:<frame>`` of the row's best entry, ``sense_id`` 1.  It prints the strata and the
**downstream estimate** (the platform's M1 on every word, M3 on the words M1 passes; this generator makes no
call), gates it with ``gapgen.cost.confirm_or_abort`` (over ``--budget-usd`` refused; over the $20 line needs
``--confirm-expensive`` and ``--confirmed-by``), writes ``candidates.jsonl`` **before** the registry append,
submits, writes ``keys.txt`` and ``submit_report.json``, finishes the run (``run.json`` with the table's sha256
and the generation records; a zero-call ``usage.json``) and prints the follow-up commands.  A dry run prints
the same and writes nothing.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from . import GENERATOR

#: Measured platform rates (overnight_readout_2026-10-08.md section 6, as the censuses use them).
M1_USD_PER_WORD = 0.0072
M3_USD_PER_PASSED_WORD = 0.011
#: The M1 pass rate the estimate assumes: the census TDA's measured 0.88 (plan section 10), **unmeasured for this
#: generator** until pilot B measures it (``report`` prints the measured rate); 0.95 printed as a high case.
M1_PASS_RATE_ASSUMED = 0.88
M1_PASS_RATE_HIGH = 0.95
BATCH_FACTOR = 0.5
DEFAULT_BUDGET_USD = 5.0
#: The wave's size in review terms (Roger, 2026-10-11: about two hours at ~150 terms an hour).
KEPT_TARGET_DEFAULT = 300
#: Kept terms (M3 ``new`` or ``grey``) per submitted single word, assumed from the census funnel (~300 kept from
#: ~550-650 submitted; coordinator, 2026-10-11) until pilot B measures this generator's own.
KEPT_SHARE_ASSUMED = 0.5
#: The wave's uncut classes by default (see the module docstring); ``subword`` is the literal reading's addition.
UNCUT_CLASSES = ("multiword",)
#: The review-load guard's tolerance: projected kept terms above this multiple of the target need ``--multi-cap``.
REVIEW_OVERSHOOT = 1.5


class ReviewLoadExceeded(ValueError):
    """The wave's projected kept terms overshoot the review target and no ``--multi-cap`` bounds them."""
RATES_SOURCE = ("M1 $0.0072/word and M3 $0.011/passed word measured on the 2026-10-08 pilots "
                "(overnight_readout_2026-10-08.md section 6); M1 pass rate 0.88 (the census TDA, plan section 10) "
                "with 0.95 printed as a high case, unmeasured for this generator until pilot B")
_MULTI_RE = re.compile(r"[\s\-]")


@dataclass
class Estimate:
    n: int
    transport: str
    m1_usd: float
    m3_usd: float
    total_usd: float
    pass_rate: float
    pass_rate_high: float = M1_PASS_RATE_HIGH
    m3_usd_high: float = 0.0
    total_usd_high: float = 0.0
    assumptions: dict = field(default_factory=dict)

    def format(self) -> str:
        return (f"downstream estimate for {self.n} words ({self.transport}): M1 filter ${self.m1_usd:.2f} + M3 "
                f"novelty ${self.m3_usd:.2f} = ${self.total_usd:.2f}  [${M1_USD_PER_WORD}/word M1, "
                f"${M3_USD_PER_PASSED_WORD}/passed word M3 at {self.pass_rate:.0%} passed"
                f"{', batches x0.5' if self.transport == 'batches' else ''}; the generator itself $0]\n"
                f"  high case at {self.pass_rate_high:.0%} passing M1: M3 ${self.m3_usd_high:.2f}, total "
                f"${self.total_usd_high:.2f}  [the pass rate is unmeasured for this generator; the gate reads the "
                f"{self.pass_rate:.0%} line]")


def estimate_downstream_usd(n: int, *, transport: str = "live", pass_rate: float = M1_PASS_RATE_ASSUMED,
                            pass_rate_high: float = M1_PASS_RATE_HIGH) -> Estimate:
    f = BATCH_FACTOR if transport == "batches" else 1.0
    m1 = round(n * M1_USD_PER_WORD * f, 4)
    m3 = round(n * pass_rate * M3_USD_PER_PASSED_WORD * f, 4)
    m3_hi = round(n * pass_rate_high * M3_USD_PER_PASSED_WORD * f, 4)
    return Estimate(n=n, transport=transport, m1_usd=m1, m3_usd=m3, total_usd=round(m1 + m3, 4), pass_rate=pass_rate,
                    pass_rate_high=pass_rate_high, m3_usd_high=m3_hi, total_usd_high=round(m1 + m3_hi, 4),
                    assumptions={"m1_usd_per_word": M1_USD_PER_WORD, "m3_usd_per_passed_word": M3_USD_PER_PASSED_WORD,
                                 "m1_pass_rate": pass_rate, "m1_pass_rate_high": pass_rate_high, "batch_factor": f,
                                 "source": RATES_SOURCE})


def row_class(r: Mapping) -> str:
    """The row's token class (the table's ``token_class``; a surface with a space or hyphen is ``multiword``
    when the table was built without a tokenizer)."""
    return r.get("token_class") or ("multiword" if _MULTI_RE.search(r.get("surface") or "") else "single")


def _pool(table: Sequence[Mapping]) -> list[Mapping]:
    return sorted((r for r in table if r.get("eligible") and r.get("stem")), key=lambda r: r["union_rank"])


def _take(rows: Sequence[Mapping], n: int, registered: set) -> list[Mapping]:
    """``rows`` in order until ``n`` of them are not in ``registered``: a registered row on the way is taken
    (submitted) and not counted."""
    out, k = [], 0
    for r in rows:
        if k >= n:
            break
        out.append(r)
        k += r["stem"] not in registered
    return out


def select_top(table: Sequence[Mapping], n: int, *, registered_stems: Iterable[str] = (),
               count_registered: bool = False) -> list[Mapping]:
    """The eligible rows by union rank up to the ``n``-th whose stem is not in ``registered_stems`` (the registered
    ones on the way included, not counted; ``count_registered`` counts them)."""
    return _take(_pool(table), max(0, int(n)), set() if count_registered else set(registered_stems))


def select_wave(table: Sequence[Mapping], *, kept_target: int = KEPT_TARGET_DEFAULT,
                kept_share: float = KEPT_SHARE_ASSUMED, registered_stems: Iterable[str] = (),
                count_registered: bool = False, multi_cap: Optional[int] = None,
                uncut: Sequence[str] = UNCUT_CLASSES) -> tuple[list[Mapping], list[Mapping]]:
    """``(rows cut by union rank at the kept target, uncut rows with a gloss)``; see the module docstring (registered
    stems ride along uncounted)."""
    if not 0 < kept_share <= 1:
        raise ValueError(f"--kept-share must be in (0, 1], got {kept_share}")
    bad = set(uncut) - {"subword", "multiword"}
    if bad:
        raise ValueError(f"--uncut-classes takes subword and multiword, not {sorted(bad)}")
    reg = set() if count_registered else set(registered_stems)
    pool = _pool(table)
    n_single = math.ceil(int(kept_target) / float(kept_share))
    singles = _take([r for r in pool if row_class(r) not in uncut], n_single, reg)
    multis = [r for r in pool if row_class(r) in uncut and r.get("gloss_hint")]
    if multi_cap is not None:
        multis = _take(multis, max(0, int(multi_cap)), reg)
    return singles, multis


def _undecided(row: Mapping) -> bool:
    """A registry row M1 or M3 has still to decide: no filter block, or a trait verdict and no novelty block (the
    platform may still charge for it, in this run's batch if it runs first)."""
    f = row.get("filter") or {}
    return not f or (f.get("verdict") == "trait" and not row.get("novelty"))


def registry_stems(registry_rows: Mapping[str, Mapping]) -> tuple[set, set]:
    """``(stems in the registry, those of them M1 or M3 has still to decide)`` from a folded registry."""
    stems, pending = set(), set()
    for r in registry_rows.values():
        st = r.get("stem")
        if st:
            stems.add(st)
            if _undecided(r):
                pending.add(st)
    return stems, pending


def to_candidates(rows: Sequence[Mapping], run_id: str) -> list[Candidate]:
    out = []
    for r in rows:
        pass_name, _, model = str(r.get("best_pass") or "?:?").partition(":")
        score = r.get("trait_contrast")
        out.append(Candidate(surface=r["surface"], generator=GENERATOR, run_id=run_id, rank=int(r["union_rank"]),
                             score=None if score is None else float(score), gloss_hint=r.get("gloss_hint"),
                             sense_id=1, source_ref=f"mlm:{pass_name}:{model}:{r.get('best_frame')}"))
    return out


def strata(rows: Sequence[Mapping]) -> dict:
    from ..censuses.ingest import zipf_band
    zc = Counter(f"{zipf_band(r.get('zipf'))} | {'corpus' if r.get('corpus_stem_match') else 'new'}" for r in rows)
    return {"zipf_band_x_corpus": dict(sorted(zc.items())),
            "token_class": dict(sorted(Counter(row_class(r) for r in rows).items())),
            "best_pass": dict(sorted(Counter(str(r.get("best_pass")) for r in rows).items())),
            "with_gloss_hint": sum(1 for r in rows if r.get("gloss_hint")),
            "with_contrast": sum(1 for r in rows if r.get("trait_contrast") is not None),
            "state_or_physical_flag": sum(1 for r in rows if r.get("state_flag") or r.get("physical_flag")),
            "stoplist_flagged": sum(1 for r in rows if r.get("stoplist_flags"))}


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
        f"{py}/masked_lm_generator.py report --run-id {run_id}   # the readout ($0): measured pass rate and kept share",
        f"{py}/recovery_test.py --generator {GENERATOR} --run-id {run_id} --budget-usd 8   # optional: about $5 a "
        f"seed (paid; Roger's call)",
    ]


@dataclass
class SubmitSummary:
    run_id: str
    mode: str
    n_table: int
    n_selected: int
    n_single: int
    n_multi: int
    estimate: dict
    strata: dict
    dry_run: bool
    n_registered: int = 0          # selected rows whose stem was already in the registry (submitted, not counted)
    n_counted: int = 0             # selected rows the cut counted
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list[str] = field(default_factory=list)


def run_submit(run_id: str, *, table: Sequence[Mapping], top_n: Optional[int] = None,
               kept_target: Optional[int] = None, kept_share: float = KEPT_SHARE_ASSUMED,
               multi_cap: Optional[int] = None, uncut: Sequence[str] = UNCUT_CLASSES,
               registered_stems: Iterable[str] = (), pending_stems: Iterable[str] = (),
               count_registered: bool = False,
               budget_usd: float = DEFAULT_BUDGET_USD, confirm_expensive: bool = False,
               confirmed_by: Optional[str] = None, transport: str = "live", dry_run: bool = False,
               registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               table_path: Optional[Path] = None, table_sha256: Optional[str] = None,
               generation: Optional[Mapping] = None, echo=print) -> SubmitSummary:
    """Select, estimate, gate, record and submit (see the module docstring).  Exactly one of ``top_n`` and
    ``kept_target``.  ``registered_stems``: the stems already in the registry; ``pending_stems``: those of them M1
    or M3 has still to decide (:func:`registry_stems`)."""
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    if (top_n is None) == (kept_target is None):
        raise ValueError("give exactly one of --top N (the pilot) and --kept-target K (the wave)")
    reg, pending = set(registered_stems), set(pending_stems)
    reg_cut = set() if count_registered else reg

    def counted(rs):
        return sum(1 for r in rs if r["stem"] not in reg_cut)
    if top_n is not None:
        mode = f"top {top_n}"
        rows = select_top(table, top_n, registered_stems=reg, count_registered=count_registered)
        n_single = sum(1 for r in rows if row_class(r) == "single")
        n_multi = len(rows) - n_single
        n_counted = counted(rows)
    else:
        mode = f"kept target {kept_target} at kept share {kept_share}"
        singles, multis = select_wave(table, kept_target=kept_target, kept_share=kept_share, registered_stems=reg,
                                      count_registered=count_registered, multi_cap=multi_cap, uncut=uncut)
        rows = sorted(singles + multis, key=lambda r: r["union_rank"])
        n_single, n_multi = len(singles), len(multis)
        c_single, c_multi = counted(singles), counted(multis)
        n_counted = c_single + c_multi
    cands = to_candidates(rows, run_id)
    reg_rows = [r["stem"] for r in rows if r["stem"] in reg]
    n_charged = len(rows) - len(reg_rows) + sum(1 for s in reg_rows if s in pending)
    est = estimate_downstream_usd(n_charged, transport=transport)
    st = strata(rows)
    n_reg = sum(1 for r in table if r.get("eligible") and r.get("stem") in reg)
    split = (f"{n_single} single-word, {n_multi} subword or multiword" if top_n is not None else
             f"{n_single} cut by union rank, {n_multi} uncut {'/'.join(uncut)}")
    how = ("counted in the cut: --count-registered" if count_registered else
           "submitted where they fall inside the cut, never counted in it")
    echo(f"{mode}: {len(table)} table rows, {sum(1 for r in table if r.get('eligible'))} eligible, {n_reg} of them "
         f"already in the registry ({how}); selected {len(rows)} ({split}; {len(rows) - len(reg_rows)} new, "
         f"{len(reg_rows)} already registered, {sum(1 for s in reg_rows if s in pending)} of those still undecided "
         f"by M1 or M3)")
    if kept_target is not None:
        projected = n_counted * kept_share
        echo(f"  projected kept terms: ({c_single} cut by rank + {c_multi} uncut {'/'.join(uncut)} rows"
             f"{'' if count_registered else ', registered stems not counted'}) x {kept_share} = {projected:.0f} "
             f"against the target {kept_target} (about {projected / 150:.1f} h of review at ~150 terms an hour)"
             + ("" if kept_share != KEPT_SHARE_ASSUMED else "  [kept share ASSUMED (census funnel); pass pilot B's "
                                                            "measured share with --kept-share]"))
    for k, v in st.items():
        echo(f"  {k}: {v}")
    echo(est.format() + (f"\n  [{n_charged} of the {len(rows)} rows: the new ones and the registered ones still "
                         f"undecided; M1 and M3 skip the rest]" if reg_rows else ""))
    if kept_target is not None and multi_cap is None and n_counted * kept_share > REVIEW_OVERSHOOT * kept_target:
        fit = max(0, math.floor((REVIEW_OVERSHOOT * kept_target) / kept_share) - c_single)
        raise ReviewLoadExceeded(
            f"the wave's projected kept terms ({n_counted * kept_share:.0f}) exceed {REVIEW_OVERSHOOT}x the "
            f"target {kept_target}: {c_multi} uncut {'/'.join(uncut)} rows.  Bound them with --multi-cap N (by union "
            f"rank; {fit} would stay within {REVIEW_OVERSHOOT}x), or raise --kept-target: a review-hours decision, "
            f"Roger's")
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(run_id=run_id, mode=mode, n_table=len(table), n_selected=len(rows), n_single=n_single,
                            n_multi=n_multi, estimate=asdict(est), strata=st, dry_run=dry_run,
                            n_registered=len(reg_rows), n_counted=n_counted)
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    args = {"mode": mode, "top_n": top_n, "kept_target": kept_target, "kept_share": kept_share,
            "kept_share_assumed": kept_share == KEPT_SHARE_ASSUMED, "multi_cap": multi_cap, "uncut": list(uncut),
            "n": len(cands), "n_single": n_single, "n_multi": n_multi, "n_table": len(table),
            "count_registered": bool(count_registered), "n_counted": n_counted, "n_registered": len(reg_rows),
            "registered_stems": sorted(reg_rows), "n_charged": n_charged,
            "n_eligible_registered": n_reg, "transport": transport, "budget_usd": budget_usd,
            "estimate": asdict(est), "strata": st, "table": str(table_path) if table_path else None,
            "table_sha256": table_sha256, "score": "trait_contrast (the contrast score; not a familiarity)",
            "generation": dict(generation or {})}
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
