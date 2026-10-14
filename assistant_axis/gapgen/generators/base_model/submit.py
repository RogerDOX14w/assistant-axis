"""Selection, the downstream estimate and its guard, and the submission of a base-model run (plan section 7).

:func:`run_submit`:

1. selects the eligible table rows (``count >= min_count``, the count floor, default :data:`DEFAULT_MIN_COUNT`
   = 2 chosen at 2,000 samples, recorded with the table's sample size by :func:`floor_record`; optionally only
   rows a family emitted) in rank
   order, **refuses while any of them still has two candidate senses** (:mod:`.sense`, QUESTIONS 56), and
   builds one :class:`~assistant_axis.gapgen.Candidate` per row: ``score`` is the emission count (**not** a
   human familiarity, so ``base_model`` is not in ``gapgen.freq.FAMILIARITY_GENERATORS`` and no Zipf rescue
   applies), ``source_ref`` is ``base_model:<family>:<first sample id>``, ``gloss_hint`` the resolved sense
   (the OEWN one, or the sample's where the sense step chose it), ``partner_hint`` the contrast family's seed
   adjective, ``sense_id`` 1;
2. prints the counts per family and form and the **downstream estimate** (the platform's M1 on every word, M3
   on the words M1 passes; this generator makes no call) twice: over all selected rows, and over the rows M1 or
   M3 will really be asked about, since both reuse a verdict the registry already holds
   (:func:`downstream_need`; gate audit 3, 2026-10-12); it gates the second with
   ``gapgen.cost.confirm_or_abort`` (over ``budget_usd`` refused; over the $20 line needs ``confirm_expensive``
   and ``confirmed_by``);
3. opens the run, writes ``candidates.jsonl`` **before** the registry append (the main checkout resubmits
   it with ``gap_registry.py submit --from``), submits, writes ``keys.txt`` and ``submit_report.json`` (with
   the floor and the two estimates), merges the round's sampling usage (the local model's tokens at $0) into
   the run's usage, and finishes the run (``run.json``: round, prompts version, temperature, model, the floor
   with its sample size, table sha256, the seed bundle's manifest);
4. prints the follow-up commands.

A dry run prints the same and writes nothing.

**Waves** (plan 03 decision (f), built 2026-10-14): with ``wave=True`` (the CLI's default; ``--all`` is the pilot's
whole-table submission above) step 1 submits one review-hour wave instead of every row at the floor:
:func:`.waves.select_wave` draws ``ceil(kept_target / kept_share)`` **net-new** rows evenly across the count-bucket x
family cells (``--order stratified``, the first wave) or from the cell with the best measured new-kept rate down
(``--order measured``, read from the earlier waves' ``run.json`` and the registry), and the rows the registry has
already decided ride along free.  The count orders nothing.  ``run.json`` records the selection (``args.selection``:
order, seed, cells with their quotas, kept share and whether it is assumed, and each counted row's cell), which is
what the next wave and ``report`` measure from.
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
from assistant_axis.gapgen.normalize import make_key
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir, runs_root
from assistant_axis.judge_pricing import MultiModelUsage

from . import GENERATOR
from . import waves as W
from .sense import BLOCK as SENSE_BLOCK
from .sense import resolved_hint, summary as sense_summary, unresolved

#: Measured platform rates (overnight_readout_2026-10-08.md section 6, as the censuses use them).
M1_USD_PER_WORD = 0.0072
M3_USD_PER_PASSED_WORD = 0.011
#: The M1 pass rate the estimate assumes, **0.80** (Roger, QUESTIONS 55, 2026-10-11), sourced to the two
#: least-curated measured waves: the roget pilot (a dictionary walk) 81.4% of 172 and the alignment sweep's
#: full run 78.6% of 369.  The curated waves run far higher (censuses TDA 98.5% of 1,988, censuses pilot
#: 98.8% of 509, wordnet clusters 96.6% of 59).  The earlier placeholder of 0.5 was below everything
#: measured and made the printed estimate about 60% of the real cost, understating what the gate asks Roger
#: to authorise; the base-model pilot then measures its own rate and this retires.
M1_PASS_RATE_ASSUMED = 0.80
#: The high case printed beside the estimate (QUESTIONS 55), as the alignment sweep's gate prints its 1.5x line.
M1_PASS_RATE_HIGH = 0.95
BATCH_FACTOR = 0.5
DEFAULT_BUDGET_USD = 15.0

#: The emission-count floor: a row is submitted when at least this many samples emitted it.  **2**, chosen by
#: Roger on 2026-10-12 for a table of **2,000 samples**, accepting gate audit 3
#: (reports/code_review_2026-10-12/gate_audits/base_model_table.md, sections 6 and 8): at that size the unique
#: hapaxes are 45% junk, count 2 is 23% and counts 3-7 are 9%, and the pilot's floor of 8 (no recorded
#: derivation) dropped about 300-520 trait words no other generator has.  A count is a different rate at
#: every sample size (8 at 2,000 samples is 4 per 1,000; carried to a 20,000-sample run, 0.4 per 1,000), so
#: the floor is recorded with the sample size of the table it was applied to and the one it was chosen at
#: (:func:`floor_record`), and a table of another size prints a note.  It is a setting, not derived from the data.
DEFAULT_MIN_COUNT = 2
DEFAULT_MIN_COUNT_N_SAMPLES = 2000
DEFAULT_MIN_COUNT_SOURCE = ("Roger, 2026-10-12, accepting gate audit 3 "
                            "(reports/code_review_2026-10-12/gate_audits/base_model_table.md sections 6 and 8): "
                            "a floor of 2 at 2,000 samples")
RATES_SOURCE = ("M1 $0.0072/word and M3 $0.011/passed word measured on the 2026-10-08 pilots "
                "(overnight_readout_2026-10-08.md section 6); M1 pass rate 0.80, from the two least-curated "
                "measured waves (roget pilot 81.4% of 172, alignment sweep 78.6% of 369), with 0.95 printed as "
                "a high case, until the base-model pilot measures its own (QUESTIONS 55)")


@dataclass
class Estimate:
    n: int
    transport: str
    m1_usd: float
    m3_usd: float
    total_usd: float
    pass_rate: float
    #: The same estimate at the high pass rate (QUESTIONS 55), printed beside it and never gated on.
    pass_rate_high: float = M1_PASS_RATE_HIGH
    m3_usd_high: float = 0.0
    total_usd_high: float = 0.0
    assumptions: dict = field(default_factory=dict)
    #: Words M1 has already passed whose M3 decision is still missing: M3 only, and certainly (no pass rate).
    n_m3_only: int = 0

    def format(self) -> str:
        words = f"{self.n} words" + (f" + {self.n_m3_only} already passed by M1 (M3 only)" if self.n_m3_only else "")
        return (f"downstream estimate for {words} ({self.transport}): M1 filter ${self.m1_usd:.2f} + M3 "
                f"novelty ${self.m3_usd:.2f} = ${self.total_usd:.2f}  [${M1_USD_PER_WORD}/word M1, "
                f"${M3_USD_PER_PASSED_WORD}/passed word M3 at {self.pass_rate:.0%} passed"
                f"{', batches x0.5' if self.transport == 'batches' else ''}; the generator itself $0]\n"
                f"  high case at {self.pass_rate_high:.0%} of words passing M1: M3 ${self.m3_usd_high:.2f}, "
                f"total ${self.total_usd_high:.2f}  [the pass rate is the one unmeasured number here; the gate "
                f"reads the {self.pass_rate:.0%} line]")


def estimate_downstream_usd(n: int, *, transport: str = "live", pass_rate: float = M1_PASS_RATE_ASSUMED,
                            pass_rate_high: float = M1_PASS_RATE_HIGH, n_m3_only: int = 0) -> Estimate:
    """M1 on ``n`` words and M3 on the ``pass_rate`` share of them, plus M3 on ``n_m3_only`` words M1 has already
    passed (:func:`downstream_need`)."""
    f = BATCH_FACTOR if transport == "batches" else 1.0
    m1 = round(n * M1_USD_PER_WORD * f, 4)
    m3 = round((n * pass_rate + n_m3_only) * M3_USD_PER_PASSED_WORD * f, 4)
    m3_hi = round((n * pass_rate_high + n_m3_only) * M3_USD_PER_PASSED_WORD * f, 4)
    return Estimate(n=n, transport=transport, m1_usd=m1, m3_usd=m3, total_usd=round(m1 + m3, 4), pass_rate=pass_rate,
                    pass_rate_high=pass_rate_high, m3_usd_high=m3_hi, total_usd_high=round(m1 + m3_hi, 4),
                    assumptions={"m1_usd_per_word": M1_USD_PER_WORD, "m3_usd_per_passed_word": M3_USD_PER_PASSED_WORD,
                                 "m1_pass_rate": pass_rate, "m1_pass_rate_high": pass_rate_high, "batch_factor": f,
                                 "source": RATES_SOURCE},
                    n_m3_only=n_m3_only)


def downstream_need(rows: Sequence[Mapping], registry_rows: Optional[Mapping[str, Mapping]]) -> dict:
    """What M1 and M3 will really be asked about the selected rows, from the registry (gate audit 3, proposal 6).

    A row merges into the registry key ``<stem>#1``; M1 (``traithood_filter.py --run``) takes only keys with no
    ``filter`` block, and M3 (``novelty_score.py score --run``) only keys M1 called a trait that have no
    ``novelty`` decision from a run.  So: ``n_m1`` keys without an M1 verdict (charged M1, and M3 at the pass
    rate), ``n_m3_only`` keys M1 passed that M3 has not decided (charged M3 only), and ``n_decided`` the rest
    (free: their verdicts are reused).  The pilot's estimate charged all 467 rows ($3.74) for a real $0.14.

    A key whose only verdict is the frequency floor's free reject counts as an M1 row: the selected row is
    eligible, so its source rescues the word, and gate audit 1's defect F3 fix has M1 take such a row again
    (``n_floor_rejected_retaken``; an over-estimate by those rows if that fix is not in)."""
    reg = registry_rows or {}
    n_m1 = n_m3 = n_done = n_floor = 0
    for r in rows:
        rec = reg.get(make_key(r["stem"], 1)) or {}
        f, nv = rec.get("filter") or {}, rec.get("novelty") or {}
        if f and _free_floor_reject(rec):
            n_floor += 1
            n_m1 += 1
        elif not f:
            n_m1 += 1
        elif f.get("verdict") == "trait" and not (nv.get("decision") and nv.get("run_id")):
            n_m3 += 1
        else:
            n_done += 1
    return {"n_rows": len(rows), "n_m1": n_m1, "n_m3_only": n_m3, "n_decided": n_done,
            "n_floor_rejected_retaken": n_floor, "registry_rows": len(reg)}


def _free_floor_reject(rec: Mapping) -> bool:
    """The filter block is the frequency floor's reject, made without a call (the split filter's ``rule``
    "floor", or the single-call filter's hard reject: no model, tag ``too_rare``); a probe cut is a paid
    verdict and is not one.  The same test as gate audit 1's ``freq.is_free_floor_reject``."""
    f = rec.get("filter") or {}
    if f.get("rule") == "floor":
        return True
    return (bool((rec.get("freq") or {}).get("hard_reject")) and f.get("model") is None
            and "too_rare" in (f.get("tags") or []))


def floor_record(min_count: int, *, n_samples: Optional[int], explicit: bool = False) -> dict:
    """The count floor as the run records it: the value, the sample size of the table it was applied to, the
    rate that means (per 1,000 samples), the sample size the value was chosen at, and where it came from.  The
    documented value (:data:`DEFAULT_MIN_COUNT`, typed or not) was chosen at :data:`DEFAULT_MIN_COUNT_N_SAMPLES`;
    any other value was set with ``--min-count`` for this table.  ``explicit``: the flag was given."""
    documented = int(min_count) == DEFAULT_MIN_COUNT
    return {"min_count": int(min_count), "n_samples": n_samples,
            "per_1k_samples": round(1000.0 * min_count / n_samples, 3) if n_samples else None,
            "chosen_at_n_samples": DEFAULT_MIN_COUNT_N_SAMPLES if documented else n_samples,
            "source": DEFAULT_MIN_COUNT_SOURCE if documented else "--min-count, set for this run",
            "flag_given": bool(explicit)}


def floor_note(rec: Mapping) -> Optional[str]:
    """A note when the floor is applied to a table of another size than the one it was chosen at."""
    n, at = rec.get("n_samples"), rec.get("chosen_at_n_samples")
    if n and at and n != at:
        return (f"NOTE: the count floor {rec['min_count']} was chosen at {at:,} samples and this table has {n:,} "
                f"({rec['per_1k_samples']} per 1,000 samples here, {round(1000.0 * rec['min_count'] / at, 3)} at "
                f"{at:,}); a count is a different rate at every sample size, so state the floor for this size with "
                f"--min-count (gate audit 3, section 6)")
    if not n:
        return "NOTE: the table's sample size is unknown, so the floor is recorded without it"
    return None


def select_rows(table: Sequence[Mapping], *, min_count: int = DEFAULT_MIN_COUNT,
                families: Optional[Iterable[str]] = None) -> list[Mapping]:
    """Eligible rows with ``count >= min_count`` (and, given ``families``, emitted by one of them), by rank."""
    fams = set(families or ())
    out = [r for r in table if r.get("eligible") and int(r.get("count") or 0) >= min_count
           and (not fams or fams & set(r.get("families") or {}))]
    return sorted(out, key=lambda r: r["rank"])


def to_candidates(rows: Sequence[Mapping], run_id: str) -> list[Candidate]:
    """One candidate per row.  ``gloss_hint`` is the **resolved** sense (:func:`sense.resolved_hint`): the OEWN
    hint where the row has no divergence, the gloss the sense step chose where it had one (QUESTIONS 56)."""
    return [Candidate(surface=r["surface"], generator=GENERATOR, run_id=run_id, rank=int(r["rank"]),
                      score=float(r["count"]), gloss_hint=resolved_hint(r), sense_id=1,
                      source_ref=f"{GENERATOR}:{r.get('first_family') or '?'}:{r['first_sample_id']}",
                      partner_hint=r.get("partner_seed")) for r in rows]


class SenseUnresolved(RuntimeError):
    """Raised when a selected row still has two candidate senses (QUESTIONS 56: M1 and M3 must see one
    settled sense, because a gloss changed after them invalidates their verdicts)."""


def check_sense_resolved(rows: Sequence[Mapping], *, round_n: int) -> None:
    """Refuse the submission while any selected row has both glosses and no settled sense."""
    bad = unresolved(rows)
    if not bad:
        return
    names = ", ".join(str(r.get("stem")) for r in bad[:10]) + (" ..." if len(bad) > 10 else "")
    raise SenseUnresolved(
        f"{len(bad)} of {len(rows)} selected rows have two candidate senses and no decision ({names}): run "
        f"`uv run python data_analysis/gap_generation/base_model_generator.py sense --round {round_n}` first "
        f"(QUESTIONS 56: the sense is settled inside candidate generation, before M1, because a gloss changed "
        f"later invalidates M1's sense, polysemy and region verdicts and every M3 reading)")


def strata(rows: Sequence[Mapping]) -> dict:
    fam = Counter(f for r in rows for f in (r.get("families") or {}))
    first = Counter(r.get("first_family") for r in rows)
    form = Counter(r.get("form") for r in rows)
    sense_blocks = [r.get(SENSE_BLOCK) or {} for r in rows]
    return {"by_family_emitted": dict(sorted(fam.items())), "by_first_family": dict(sorted(first.items())),
            "by_form": dict(sorted(form.items())), "with_partner_hint": sum(1 for r in rows if r.get("partner_seed")),
            "with_gloss_hint": sum(1 for r in rows if resolved_hint(r)),
            "sense_divergent": sum(1 for b in sense_blocks if b.get("divergent")),
            "sense_from_sample": sum(1 for b in sense_blocks if b.get("chosen") == "sample")}


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
    #: The gated estimate: only the rows M1 or M3 will really be asked about (:func:`downstream_need`).
    estimate: dict
    strata: dict
    dry_run: bool
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list[str] = field(default_factory=list)
    #: The estimate as if no selected row had a recorded verdict (what the gate read before gate audit 3).
    estimate_all_rows: Optional[dict] = None
    need: Optional[dict] = None
    floor: Optional[dict] = None
    #: ``args.selection`` of ``run.json``: ``{"mode": "all"}`` or the wave's record (:meth:`.waves.WaveSelection.record`).
    selection: Optional[dict] = None


def _load_registry_rows(registry_path: Path) -> dict:
    from assistant_axis.gapgen.registry import Registry
    p = Path(registry_path)
    return Registry(p).fold() if p.exists() else {}


def _wave_inputs(table: Sequence[Mapping], corpus_stems, queue_stems, renamed):
    """The membership sets the net-new test reads; without them (tests, an older caller) the table's own flags from
    ``parse`` stand in."""
    if corpus_stems is None:
        corpus_stems = {r["stem"] for r in table if r.get("corpus_stem_match")}
    if queue_stems is None:
        queue_stems = {r["stem"] for r in table if r.get("queue_stem_match")}
    return set(corpus_stems), set(queue_stems), dict(renamed or {})


def _kept_share(given: Optional[float], measured: Mapping, *, min_measured: int) -> tuple[float, bool, str]:
    """``(kept share, assumed?, source)``: the value given; else the pooled rate the waves measured once at least
    ``min_measured`` net-new rows are decided; else the pilot's, ASSUMED for the 20k table."""
    pooled = measured.get("pooled") or {}
    if given is not None:
        assumed = float(given) == W.KEPT_SHARE_PILOT
        return float(given), assumed, (W.KEPT_SHARE_SOURCE if assumed else "--kept-share, given")
    if pooled.get("n_decided", 0) >= min_measured and pooled.get("rate"):
        return (float(pooled["rate"]), False,
                f"measured over the waves {', '.join(measured.get('waves') or [])}: {pooled['n_kept']} kept of "
                f"{pooled['n_decided']} net-new rows decided")
    return W.KEPT_SHARE_PILOT, True, W.KEPT_SHARE_SOURCE


def run_submit(run_id: str, *, table: Sequence[Mapping], round_n: int, min_count: int = DEFAULT_MIN_COUNT,
               min_count_explicit: bool = False, n_samples: Optional[int] = None,
               families: Optional[Iterable[str]] = None, budget_usd: float = DEFAULT_BUDGET_USD,
               confirm_expensive: bool = False, confirmed_by: Optional[str] = None, transport: str = "live",
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               table_path: Optional[Path] = None, table_sha256: Optional[str] = None,
               sampling_record: Optional[Mapping] = None, sampling_usage_path: Optional[Path] = None,
               registry_rows: Optional[Mapping[str, Mapping]] = None, wave: bool = False,
               kept_target: int = W.KEPT_TARGET_DEFAULT, kept_share: Optional[float] = None,
               order: Optional[str] = None, wave_seed: int = 0, ride_along: bool = True,
               min_measured: int = W.MIN_MEASURED_DEFAULT, corpus_stems: Optional[Iterable[str]] = None,
               queue_stems: Optional[Iterable[str]] = None, renamed: Optional[Mapping[str, str]] = None,
               echo=print) -> SubmitSummary:
    """Select, estimate, gate and submit (see the module docstring).  ``n_samples``: the number of samples the
    table was built from, recorded with the floor (:func:`floor_record`).  ``registry_rows``: the folded
    registry the estimate reads (default: ``registry_path``'s).  ``wave``: one review-hour wave (:mod:`.waves`)
    instead of every row at the floor; ``corpus_stems``, ``queue_stems`` and ``renamed`` feed its net-new test."""
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    floor_rows = select_rows(table, min_count=min_count, families=families)
    # one settled sense before M1 (QUESTIONS 56), checked over every row at the floor, not only this wave's: a round
    # the sense step has not finished is refused whichever rows a wave would draw
    check_sense_resolved(floor_rows, round_n=round_n)
    reg_rows = _load_registry_rows(registry_path) if registry_rows is None else registry_rows
    sel = None
    if wave:
        reg = W.registry_by_stem(reg_rows)
        waves = W.load_waves(runs_root(candidates_dir) / GENERATOR, exclude=[run_id])
        measured = W.measure_cells(waves, reg)
        pooled = measured["pooled"]
        if order is None:
            order = "measured" if pooled["n_decided"] else "stratified"
            why = (f"the waves on record have {pooled['n_decided']} net-new rows decided" if pooled["n_decided"]
                   else ("no wave on record" if not waves else
                         f"the waves on record ({', '.join(w.run_id for w in waves)}) have no rows M1 and M3 have "
                         f"decided yet"))
            echo(f"order: {order} (the default: {why})")
        share, assumed, share_src = _kept_share(kept_share, measured, min_measured=min_measured)
        corpus, queue, ren = _wave_inputs(table, corpus_stems, queue_stems, renamed)
        sel = W.select_wave(floor_rows, table=table, min_count=min_count, kept_target=kept_target,
                            kept_share=share, kept_share_assumed=assumed, kept_share_source=share_src, order=order,
                            seed=wave_seed, families=families, corpus=corpus, renamed=ren, queue=queue, reg=reg,
                            earlier=W.earlier_stems(waves, reg_rows, GENERATOR), measured=measured,
                            min_measured=min_measured, ride_along=ride_along)
        rows = sel.rows
    else:
        rows = floor_rows
    cands = to_candidates(rows, run_id)
    floor = floor_record(min_count, n_samples=n_samples, explicit=min_count_explicit)
    need = downstream_need(rows, reg_rows)
    est_all = estimate_downstream_usd(len(cands), transport=transport)
    est = estimate_downstream_usd(need["n_m1"], transport=transport, n_m3_only=need["n_m3_only"])
    st = strata(rows)
    echo(f"round {round_n}: {len(table)} table rows; {len(floor_rows)} eligible at the floor (count >= {min_count}"
         + (f", families {sorted(families)}" if families else "") + "); "
         + (f"selected {len(rows)} for this wave" if sel else f"selected all {len(rows)}"))
    echo(f"  count floor: {min_count} at {floor['n_samples'] or 'an unknown number of'} samples "
         f"({floor['per_1k_samples']} per 1,000); chosen at {floor['chosen_at_n_samples']} samples "
         f"({floor['source']})")
    note = floor_note(floor)
    if note:
        echo(f"  {note}")
    if sel:
        hours = sel.expected_kept / W.REVIEW_TERMS_PER_HOUR
        echo(f"wave, order {sel.order} (seed {sel.seed}): kept target {sel.kept_target} at kept share "
             f"{sel.kept_share:g} -> {sel.need} net-new rows wanted; {len(sel.counted)} counted (net-new), "
             f"{len(sel.ride_along)} riding along (decided by the registry, free; or corpus and queue matches, charged)"
             + ("  [kept share ASSUMED: " + sel.kept_share_source + "; pass a wave's measured share with "
                "--kept-share]" if sel.kept_share_assumed else f"  [kept share: {sel.kept_share_source}]"))
        echo(f"  rows at the floor by status: {sel.status_counts}; left out: {sel.left_out or 'none'}")
        echo(f"  projection: {sel.expected_kept:.0f} kept terms, about {hours:.1f} h of review at "
             f"{W.REVIEW_TERMS_PER_HOUR:.0f} terms an hour (plan 13's measured rate)")
        echo("  cells (count bucket | home family; home family = " + W.HOME_FAMILY_RULE + "):")
        for line in sel.table_lines():
            echo(line)
        if len(sel.counted) < sel.need:
            echo(f"  NOTE: only {len(sel.counted)} net-new rows are left at the floor, under the {sel.need} wanted")
    for k, v in st.items():
        echo(f"  {k}: {v}")
    echo(f"selected rows the registry already holds a verdict for: {need['n_decided']} decided (M1 and M3 reuse "
         f"them, free), {need['n_m3_only']} passed by M1 with no M3 decision (M3 only), {need['n_m1']} with no M1 "
         f"verdict (M1, then M3 on those it passes)")
    echo("all rows, as if none had a verdict: " + est_all.format())
    echo("rows without a recorded verdict (the gate reads this one): " + est.format())
    if transport == "live":
        alt = estimate_downstream_usd(need["n_m1"], transport="batches", n_m3_only=need["n_m3_only"])
        echo(f"  batched, the same rows: ${alt.total_usd:.2f} (M1 ${alt.m1_usd:.2f} + M3 ${alt.m3_usd:.2f})")
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    selection = sel.record() if sel else {"mode": "all"}
    summary = SubmitSummary(run_id=run_id, round=round_n, n_table=len(table), n_selected=len(rows),
                            estimate=asdict(est), strata=st, dry_run=dry_run, estimate_all_rows=asdict(est_all),
                            need=need, floor=floor, selection=selection)
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
            "min_count": min_count, "floor": floor, "families": sorted(families) if families else None,
            "n": len(cands), "n_table": len(table), "transport": transport, "budget_usd": budget_usd,
            # the gated estimate counts only rows without a recorded verdict (gate audit 3); before 2026-10-12
            # "estimate" charged every row, which is now "estimate_all_rows"
            "estimate": asdict(est), "estimate_all_rows": asdict(est_all), "downstream_need": need,
            "strata": st, "table": str(table_path) if table_path else None, "table_sha256": table_sha256,
            "seed_bundle": rec.get("bundle"), "sampling": rec.get("sampling"),
            "gloss_sense": sense_summary(rows),
            # the wave (plan 03 decision (f), 2026-10-14): what the next wave and the report measure from
            "selection": selection}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=registry_path)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = ({k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}
             | {"floor": floor, "downstream_need": need, "estimate_usd": est.total_usd,
                "estimate_all_rows_usd": est_all.total_usd})
    if sel:
        rep_d |= {"wave": {"order": sel.order, "n_counted": len(sel.counted), "n_ride_along": len(sel.ride_along),
                           "kept_share": sel.kept_share, "kept_share_assumed": sel.kept_share_assumed,
                           "expected_kept": sel.expected_kept}}
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
