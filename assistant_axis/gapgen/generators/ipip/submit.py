"""Named poles to candidates, the downstream estimate, and the submission of an IPIP run.

:func:`to_candidates`: one ``Candidate`` per **named pole** of a kept cluster, the label in the chosen form
(blind by default: QUESTIONS 47).  **Every named pole is submitted** (QUESTIONS 48, Roger 2026-10-11:
``is_trait`` stops being a gate; M1's pinned kind call decides what a pole is, at about 40c of M1 for the 15%
share the gate would have dropped), and the naming call's own ``kind`` guess is counted in the report beside
M1's verdicts.  ``surface`` is the label, ``gloss_hint`` the gloss, ``rank`` the cluster id (clusters numbered by
size), ``score`` ``None`` (QUESTIONS 51: the platform reads ``score`` as human familiarity), ``source_ref``
``ipip:g<G>:c<NNN><pole>``, and ``partner_hint`` the other pole's label in a bipolar cluster (reciprocal, so
that ``promote`` can pair them and M3 sees a declared partner).

:func:`run_submit` mirrors the census generator's: it prints the downstream estimate (the platform's M1 filter on
every word and its M3 novelty scorer on the words M1 passes; this step makes no call) and gates it with
``gapgen.cost.confirm_or_abort``; then ``start_run``, ``candidates.jsonl`` before ``submit_candidates``,
``keys.txt``, ``submit_report.json``, ``run.json`` and a zero-call ``usage.json``, and the follow-up commands.
A dry run prints the same and writes nothing.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import Candidate, start_run, submit_candidates
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.paths import REGISTRY_PATH, REPO_ROOT, check_id, run_dir

from . import GENERATOR

#: Platform cost per word, copied from the census generator's measured constants (``censuses/submit.py``; source:
#: overnight_readout_2026-10-08.md § 6, the 2026-10-08 pilots): M1 $0.0072 a submitted word, M3 $0.011 a word M1
#: passes, at an 88% pass rate.  This generator's own rates are measured by its pilot.
M1_USD_PER_WORD = 0.0072
M3_USD_PER_PASSED_WORD = 0.011
M1_PASS_RATE = 0.88
RATES_SOURCE = "measured on the 2026-10-08 pilots (overnight_readout_2026-10-08.md, section 6), via censuses/submit.py"
DEFAULT_BUDGET_USD = 8.0
LABEL_CHOICES = ("blind", "hinted")


def source_ref(granularity: int, cluster_id: int, pole: str) -> str:
    return f"ipip:g{int(granularity)}:c{int(cluster_id):03d}{pole}"


_POLE_RE = re.compile(r"(?:ipip:g\d+:)?c?0*(\d+)([ab])$")


def parse_poles_file(text: str) -> set[tuple[int, str]]:
    """Pole ids, one per line (``c017a``, ``17a`` or a source ref ``ipip:g350:c017a``); ``#`` comments skipped."""
    out = set()
    for line in text.splitlines():
        s = line.split("#", 1)[0].strip()
        if not s:
            continue
        m = _POLE_RE.match(s)
        if not m:
            raise ValueError(f"not a pole id: {s!r} (c017a, 17a or ipip:g350:c017a)")
        out.add((int(m.group(1)), m.group(2)))
    return out


def to_candidates(rows: Sequence[Mapping], run_id: str, *, label_choice: str = "blind",
                  poles: Optional[set] = None, include_loose: bool = False) -> tuple[list[Candidate], dict]:
    """``(candidates, counts)`` from cluster rows (see the module docstring).  ``poles`` limits the submission to
    those ``(cluster_id, pole)`` ids; a partner hint still names the other pole when it is not submitted.  No
    verdict of the naming call holds a pole back (QUESTIONS 48): ``counts["kinds"]`` records what the call
    guessed, for the report."""
    if label_choice not in LABEL_CHOICES:
        raise ValueError(f"label_choice must be one of {LABEL_CHOICES}")
    counts = {"n_kept_clusters": 0, "n_poles": 0, "n_named": 0, "n_unnamed": 0,
              "n_loose_skipped": 0, "n_selected_out": 0, "n_submitted": 0, "label_choice": label_choice,
              "kinds": {}}
    kinds: Counter = Counter()
    out = []
    for r in sorted(rows, key=lambda r: int(r["cluster_id"])):
        if r.get("consensus") != "kept" and not include_loose:
            counts["n_loose_skipped"] += 1
            continue
        counts["n_kept_clusters"] += 1
        named = {p["pole"]: p.get(label_choice) for p in r["poles"]}
        for p in r["poles"]:
            counts["n_poles"] += 1
            nm = named[p["pole"]]
            if not nm:
                counts["n_unnamed"] += 1
                continue
            counts["n_named"] += 1
            kinds[nm.get("kind") or "unknown"] += 1
            if poles is not None and (int(r["cluster_id"]), p["pole"]) not in poles:
                counts["n_selected_out"] += 1
                continue
            other = [named[q] for q in named if q != p["pole"] and named[q]]
            partner = other[0]["label"] if r.get("bipolar") and other else None
            out.append(Candidate(surface=nm["label"], generator=GENERATOR, run_id=run_id, rank=int(r["cluster_id"]),
                                 score=None, gloss_hint=nm.get("gloss"), sense_id=1,
                                 source_ref=source_ref(r["granularity"], r["cluster_id"], p["pole"]),
                                 partner_hint=partner))
    counts["n_submitted"] = len(out)
    counts["kinds"] = dict(sorted(kinds.items()))
    return out, counts


def estimate_downstream_usd(n: int) -> dict:
    m1 = round(n * M1_USD_PER_WORD, 4)
    m3 = round(n * M1_PASS_RATE * M3_USD_PER_PASSED_WORD, 4)
    return {"n": n, "m1_usd": m1, "m3_usd": m3, "total_usd": round(m1 + m3, 4),
            "assumptions": {"m1_usd_per_word": M1_USD_PER_WORD, "m3_usd_per_passed_word": M3_USD_PER_PASSED_WORD,
                            "m1_pass_rate": M1_PASS_RATE, "source": RATES_SOURCE}}


def format_estimate(e: Mapping) -> str:
    a = e["assumptions"]
    return (f"downstream estimate for {e['n']} distinct words (live): M1 filter {e['n']} x ${a['m1_usd_per_word']} = "
            f"${e['m1_usd']:.2f} + M3 novelty {e['n']} x {a['m1_pass_rate']:.0%} x ${a['m3_usd_per_passed_word']} = "
            f"${e['m3_usd']:.2f}; total ${e['total_usd']:.2f} (this step makes no call)")


def batch_id_for(run_id: str) -> str:
    return f"{run_id}_{GENERATOR}"


def _cap(x: float) -> float:
    """A follow-up's cap: 1.5 x its estimate + $2, rounded up to a dollar (the census generator's rule)."""
    return float(math.ceil(1.5 * x + 2.0))


def followup_commands(run_id: str, est: Mapping, *, candidates_path: Path) -> list[str]:
    b = batch_id_for(run_id)
    py = "uv run python data_analysis/gap_generation"
    c1, c3 = _cap(est["m1_usd"]), _cap(est["m3_usd"])

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""
    try:
        rel = Path(candidates_path).resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        rel = Path(candidates_path)
    return [
        f"{py}/gap_registry.py submit --from {rel}   # another checkout: resubmit into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b} --run {GENERATOR}/{run_id} --pipeline split --budget-usd {c1:.0f}"
        f"{gate(c1)}   # M1, estimate ${est['m1_usd']:.2f}",
        f"{py}/novelty_score.py score --batch-id {b} --run {GENERATOR}/{run_id} --budget-usd {c3:.0f}{gate(c3)}"
        f"   # M3 on the words M1 passes, estimate ${est['m3_usd']:.2f}",
        f"{py}/ipip_generator.py report --run-id {run_id}",
    ]


@dataclass
class SubmitSummary:
    granularity: int
    run_id: str
    counts: dict
    estimate: dict
    dry_run: bool
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list = field(default_factory=list)


def run_submit(granularity: int, run_id: str, *, rows: Sequence[Mapping], sources_manifest, clusters_sha256: Optional[str],
               label_choice: str = "blind", poles: Optional[set] = None,
               budget_usd: float = DEFAULT_BUDGET_USD, confirm_expensive: bool = False, confirmed_by: Optional[str] = None,
               dry_run: bool = False, registry_path: Path = REGISTRY_PATH, candidates_dir: Optional[Path] = None,
               clusters_path: Optional[str] = None, echo=print) -> SubmitSummary:
    check_id(run_id, "run_id")
    rows = [r for r in rows if int(r["granularity"]) == int(granularity)]
    cands, counts = to_candidates(rows, run_id, label_choice=label_choice, poles=poles)
    stems = {normalize_candidate(c.surface).stem for c in cands}
    est = estimate_downstream_usd(len(stems))
    echo(f"granularity {granularity}: {counts['n_kept_clusters']} kept clusters, {counts['n_poles']} poles, "
         f"{counts['n_named']} named ({label_choice}), {counts['n_unnamed']} not named; the naming call's own kind "
         f"guesses {json.dumps(counts['kinds'])} (reported, never a gate: QUESTIONS 48); submitting "
         f"{len(cands)} candidates ({len(stems)} distinct words)")
    echo(format_estimate(est))
    confirm_or_abort(est["total_usd"], budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(granularity=int(granularity), run_id=run_id, counts=counts, estimate=est, dry_run=dry_run)
    target = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    summary.followups = followup_commands(run_id, est, candidates_path=target / "candidates.jsonl")
    if dry_run:
        echo(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
             f"{registry_path}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    args = {"granularity": int(granularity), "n": len(cands), "n_distinct": len(stems), "estimate": est,
            "budget_usd": budget_usd, "label_choice": label_choice,
            "gate": "none: every named pole is submitted (QUESTIONS 48, Roger 2026-10-11)",
            "poles": sorted(f"c{c:03d}{p}" for c, p in poles) if poles is not None else "all",
            "counts": counts, "clusters": clusters_path, "clusters_sha256": clusters_sha256,
            "sources_manifest": sources_manifest}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    ctx.record_candidates(cands)                  # candidates.jsonl first (the tracked record of the run)
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


def selected_poles(poles_file: Optional[Path]) -> Optional[set]:
    return parse_poles_file(Path(poles_file).read_text(encoding="utf-8")) if poles_file else None


__all__ = ["Candidate", "to_candidates", "run_submit", "estimate_downstream_usd", "parse_poles_file", "source_ref",
           "batch_id_for", "followup_commands", "M1_USD_PER_WORD", "M3_USD_PER_PASSED_WORD", "M1_PASS_RATE",
           "submit_candidates", "selected_poles"]
