"""B's metering, the downstream estimate and its gate, and the submission (coding plan 16, § 5b and § 7d
"Metering").

**Net-new** (:func:`net_new`), over the ranking: a lay role whose stem is a corpus role (or a corpus role's
``renamed_from``) or a seed-queue role entry (any status: a live entry is in hand, a turned-down one was turned
down) is **excluded**, not submitted.  One the registry already holds as a role row (the row a role-aimed candidate
of its stem goes to, ``registry.candidate_key``: ``stem|R#1``, or a held ``stem#1`` row whose entity type is
``role``) is **resubmitted**, so that its SOC or O*NET provenance merges into the row, and counts toward neither the
meter nor the estimate (M1 and M3 skip a row already decided; the plan's case is a held row on the ``roles``
list).  The rest are net-new.

**The wave** (:func:`select_wave`): ``n = share x wave_rows / kept_share`` net-new rows from the top of the
ranking (0.5 x 300 / 0.4 = 375), a resubmitted row inside the cut submitted and not counted; ``--all`` submits the
whole ranking (refused, like any submission whose downstream estimate passes $20, without ``--confirm-expensive
--confirmed-by``).

**The candidates** (:func:`to_candidates`): one per source of each selected row (a role two groups name carries
both source references): ``entity_type="role"``, ``kind_guess="occupation"``, ``human=True``, ``source_ref``
``soc:<broad code>`` / ``onet_title:<O*NET code>:<title stem>`` / ``esco:<ISCO code>``, ``partner_hint`` None,
``gloss_hint`` the lay gloss, ``rank`` and ``score`` the ranking's.  When the run holds the label-fit check's
decisions (``label_fit/decisions.json``, ``professions_generator.py label-fit``), its corrections are applied
(``label_fit.corrected_candidates``) and the role fields restored on every relabelled candidate (the platform
function builds a trait candidate).

**The estimate** prices M1 on every net-new row and M3 (the role pass's stage and the novelty check) on the share
M1 passes, at the platform's measured rates (``masked_lm.submit.estimate_downstream_usd``: M1 $0.0072 a word, M3
$0.011 a passed word, batches x0.5) at the plan's 85% passing; ``gapgen.cost.confirm_or_abort`` gates it.

:func:`run_submit` writes ``ATTRIBUTION.md`` and ``candidates.jsonl`` (through ``submit_candidates(run=ctx)``, the
record before the registry), then ``keys.txt``, ``submit_report.json`` (with the occupation share before and after
at the held share, :func:`balance_before_after`), ``run.json`` and a zero-call ``usage.json``, and prints the
follow-up commands.  A dry run prints the same and writes nothing.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.cost import HARD_LINE_USD, confirm_or_abort
from assistant_axis.gapgen.paths import DATA_DIR, REGISTRY_PATH, REPO_ROOT, check_id, run_dir
from assistant_axis.gapgen.registry import Candidate, candidate_key

from . import ATTRIBUTION_NAME, CANDIDATES_NAME, GENERATOR, LABEL_FIT_DIR, SUBMIT_REPORT_NAME
from ..masked_lm.submit import Estimate, _budget
from ..masked_lm.submit import estimate_downstream_usd as _estimate

WAVE_ROWS_DEFAULT = 300
SHARE_DEFAULT = 0.5
#: The plan's M1 pass rate for B's rows (§ Cost: "M3 on about 85%"), unmeasured until the first wave.
M1_PASS_RATE = 0.85
DEFAULT_BUDGET_USD = 10.0
KIND_GUESS = "occupation"
REVIEW_TERMS_PER_HOUR = 146.0
REVIEW_RATE_SOURCE = "146 terms an hour, measured on review_tda_1 (acceptance_13_generator_testing.md)"


# --------------------------------------------------------------------------- what is already there

def _renamed(value) -> list[str]:
    out = []
    for item in value if isinstance(value, list) else ([value] if value else []):
        old = item.get("stem") if isinstance(item, Mapping) else item
        if isinstance(old, str) and old:
            out.append(old)
    return out


def corpus_role_stems(data_dir: Path = DATA_DIR) -> dict[str, str]:
    """``{stem: current stem}``: every role file's stem (``default.json`` left out) and every ``renamed_from`` stem
    of one, mapped to the file's stem."""
    out: dict[str, str] = {}
    d = Path(data_dir) / "roles" / "instructions"
    for p in sorted(d.glob("*.json")):
        if p.stem == "default":
            continue
        out[p.stem] = p.stem
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for old in _renamed(doc.get("renamed_from")):
            out.setdefault(old, p.stem)
    return out


def queue_role_stems(queue: Mapping) -> dict[str, str]:
    """``{stem: status}`` of the seed queue's role entries (by stem and by normalised label)."""
    from assistant_axis.entity_id import normalize_to_file_name
    out: dict[str, str] = {}
    for e in queue.get("entries") or []:
        if e.get("entity_type") != "role" or not e.get("stem"):
            continue
        out.setdefault(e["stem"], str(e.get("status")))
        if e.get("label"):
            out.setdefault(normalize_to_file_name(e["label"]), str(e.get("status")))
    return out


def registry_role_row(stem: str, registry_rows: Mapping[str, Mapping]) -> Optional[Mapping]:
    """The row a role-aimed candidate of ``stem`` merges into, or None when it would make a new row."""
    key = candidate_key(stem, 1, "role", rows=[registry_rows])
    return registry_rows.get(key)


def is_decided(row: Mapping) -> bool:
    """A row the pipeline or Roger has decided: a review decision, an M1 rejection, or an M3 decision."""
    st = (row.get("review") or {}).get("status")
    if st not in (None, "unreviewed", "deferred"):
        return True
    if (row.get("filter") or {}).get("verdict") == "reject":
        return True
    return bool((row.get("novelty") or {}).get("decision"))


def net_new(ranked: Sequence[Mapping], *, registry_rows: Mapping[str, Mapping], corpus_stems: Mapping[str, str] | Iterable[str],
            queue_stems: Mapping[str, str] | Iterable[str]) -> tuple[list[dict], list[dict]]:
    """``(net-new rows, already-registered rows)`` in rank order (module docstring).  Every row of the returned
    copies, and of the excluded ones (neither list), carries ``net_new``, ``registered_as``,
    ``registered_decided`` and ``excluded`` (``corpus_role`` / ``queue_entry`` / None); the full annotated ranking
    is :func:`annotate`'s."""
    rows = annotate(ranked, registry_rows=registry_rows, corpus_stems=corpus_stems, queue_stems=queue_stems)
    return [r for r in rows if r["net_new"]], [r for r in rows if r["registered_as"] and not r["excluded"]]


def annotate(ranked: Sequence[Mapping], *, registry_rows: Mapping[str, Mapping],
             corpus_stems: Mapping[str, str] | Iterable[str], queue_stems: Mapping[str, str] | Iterable[str]
             ) -> list[dict]:
    corpus = corpus_stems if isinstance(corpus_stems, Mapping) else {s: s for s in corpus_stems}
    queue = queue_stems if isinstance(queue_stems, Mapping) else {s: "?" for s in queue_stems}
    out = []
    for r in sorted(ranked, key=lambda r: r["rank"]):
        r = dict(r)
        stem = r["stem"]
        r.update(net_new=False, registered_as=None, registered_decided=False, excluded=None, corpus_stem=None,
                 queue_status=None)
        if stem in corpus:
            r.update(excluded="corpus_role", corpus_stem=corpus[stem])
        elif stem in queue:
            r.update(excluded="queue_entry", queue_status=queue[stem])
        else:
            row = registry_role_row(stem, registry_rows)
            if row is not None:
                r.update(registered_as=row.get("key"), registered_decided=is_decided(row))
            else:
                r["net_new"] = True
        out.append(r)
    return out


# --------------------------------------------------------------------------- the wave

def wave_target(wave_rows: int = WAVE_ROWS_DEFAULT, share: float = SHARE_DEFAULT, *, kept_share: float) -> int:
    """``ceil(share x wave_rows / kept_share)`` net-new rows (0.5 x 300 / 0.4 = 375)."""
    if not 0 < float(kept_share) <= 1:
        raise ValueError(f"--kept-share must be in (0, 1], got {kept_share}")
    if not 0 < float(share) <= 1:
        raise ValueError(f"--share must be in (0, 1], got {share}")
    x = float(share) * int(wave_rows) / float(kept_share)
    return int(math.ceil(x - 1e-9))


def select_wave(ranked: Sequence[Mapping], *, wave_rows: int = WAVE_ROWS_DEFAULT, share: float = SHARE_DEFAULT,
                kept_share: float) -> list[dict]:
    """Rows in rank order, excluded ones skipped, until :func:`wave_target` net-new rows are taken; a registered row
    on the way is taken and not counted.  ``ranked`` must be annotated (:func:`annotate`)."""
    need = wave_target(wave_rows, share, kept_share=kept_share)
    out, k = [], 0
    for r in sorted(ranked, key=lambda r: r["rank"]):
        if k >= need:
            break
        if r.get("excluded"):
            continue
        out.append(dict(r))
        k += bool(r.get("net_new"))
    return out


def select_all(ranked: Sequence[Mapping]) -> list[dict]:
    return [dict(r) for r in sorted(ranked, key=lambda r: r["rank"]) if not r.get("excluded")]


# --------------------------------------------------------------------------- candidates

def to_candidates(selected: Sequence[Mapping], run_id: str) -> list[Candidate]:
    """One role candidate per source of each row (module docstring)."""
    out = []
    for r in selected:
        for s in r.get("sources") or [{"source_ref": None, "gloss": r.get("gloss")}]:
            out.append(Candidate(surface=r["role"], generator=GENERATOR, run_id=run_id, rank=int(r["rank"]),
                                 score=float(r["score"]), gloss_hint=s.get("gloss") or r.get("gloss"), sense_id=1,
                                 source_ref=s.get("source_ref"), partner_hint=None, entity_type="role",
                                 kind_guess=KIND_GUESS, human=True))
    return out


def as_role(c: Candidate) -> Candidate:
    """``c`` with the role fields B gives every candidate."""
    return replace(c, entity_type="role", kind_guess=KIND_GUESS, human=True, partner_hint=None)


def read_label_fit(run_path: Path) -> Optional[list[dict]]:
    """The label-fit check's decisions for this run (``label_fit/decisions.json``), or None when it was not run."""
    p = Path(run_path) / LABEL_FIT_DIR / "decisions.json"
    if not p.exists():
        return None
    return list(json.loads(p.read_text(encoding="utf-8")).get("decisions") or [])


def apply_label_fit(cands: Sequence[Candidate], decisions: Sequence[Mapping], *,
                    excluded_stems: Iterable[str] = ()) -> tuple[list[Candidate], dict]:
    """``label_fit.corrected_candidates`` with the role fields restored; a relabelled candidate whose new stem is a
    corpus role or a queue entry is dropped (counted as ``relabel_dropped_existing``)."""
    from assistant_axis.gapgen.label_fit import corrected_candidates
    from assistant_axis.gapgen.normalize import normalize_candidate
    fixed, counts = corrected_candidates(list(cands), list(decisions))
    ex = set(excluded_stems)
    out, dropped = [], 0
    for c in fixed:
        c = as_role(c)
        try:
            stem = normalize_candidate(c.surface).stem
        except ValueError:
            dropped += 1
            continue
        if stem in ex and ";label_fit:" in str(c.source_ref or ""):
            dropped += 1
            continue
        out.append(c)
    counts = dict(counts)
    if dropped:
        counts["relabel_dropped_existing"] = dropped
    return out, counts


# --------------------------------------------------------------------------- estimate, follow-ups, balance

def estimate_downstream_usd(n: int, *, transport: str = "batches", pass_rate: float = M1_PASS_RATE) -> Estimate:
    return _estimate(n, transport=transport, pass_rate=pass_rate, pass_rate_high=max(pass_rate, 0.95))


def batch_ids(run_id: str) -> dict:
    return {"m1": f"{GENERATOR}_{run_id}", "m3": f"roles_{GENERATOR}_{run_id}",
            "review": f"review_roles_{GENERATOR}_{run_id}"}


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def followup_commands(run_id: str, est: Estimate, *, candidates_path: Optional[Path] = None) -> list[str]:
    """M1, then M3 for roles, then R1 and R2 (the frozen interface's order), each with its cap and gate."""
    b = batch_ids(run_id)
    t = est.transport
    py = "uv run python data_analysis/gap_generation"
    cap1, cap3 = _budget(est.m1_usd), _budget(est.m3_usd)

    def gate(cap):
        return " --confirm-expensive --confirmed-by '<Roger, date of his go>'" if cap > HARD_LINE_USD else ""
    rel = _rel(candidates_path or run_dir(GENERATOR, run_id) / CANDIDATES_NAME)
    return [
        f"{py}/gap_registry.py submit --from {rel}   # main checkout: resubmit into its own registry log (idempotent)",
        f"{py}/traithood_filter.py --batch-id {b['m1']} --run {GENERATOR}/{run_id} --pipeline split --transport {t} "
        f"--budget-usd {cap1:.0f}{gate(cap1)}   # M1, estimate ${est.m1_usd:.2f}",
        f"{py}/novelty_score.py score --holding roles --run {GENERATOR}/{run_id} --batch-id {b['m3']} --transport {t} "
        f"--budget-usd {cap3:.0f}{gate(cap3)}   # the role pass's stage, then M3 for roles, estimate ${est.m3_usd:.2f}",
        f"{py}/review_graph.py build --batch-id {b['review']} --from-batches {b['m3']} --budget-usd 4   # R1",
        f"{py}/review_app.py serve --batch-id {b['review']} --order kinds   # R2: Roger's review",
        f"{py}/professions_generator.py report --run-id {run_id}   # the readout ($0)",
    ]


def balance_before_after(data_dir: Path, queue: Mapping, *, n_submitted: int, kept_share: Optional[float]) -> dict:
    """The kind readout (``roles_pass.balance``) of the corpus now, after the submitted rows if all were kept (by
    ``kind_guess``: occupation), and after the kept share of them (the held-share projection)."""
    from assistant_axis.gapgen import roles_pass as RP
    counts, n_now = RP.corpus_kind_counts(Path(data_dir), queue)
    before = RP.balance(counts, n_now)

    def plus(k: float) -> dict:
        c = dict(counts)
        c[KIND_GUESS] = c.get(KIND_GUESS, 0) + int(round(k))
        return RP.balance(c, n_now + int(round(k)))
    out = {"before": before, "after_submitted": plus(n_submitted), "n_submitted": int(n_submitted)}
    if kept_share:
        out["after_kept"] = plus(n_submitted * float(kept_share))
        out["kept_share"] = float(kept_share)
    occ = {k: v["kinds"][KIND_GUESS] for k, v in out.items() if isinstance(v, Mapping) and "kinds" in v}
    out["occupation"] = {k: {"count": v["count"], "held": v["held"], "status": v["status"],
                             "share": round(v["count"] / out[k]["n_now"], 4) if out[k]["n_now"] else None}
                         for k, v in occ.items()}
    return out


def balance_text(bal: Mapping) -> list[str]:
    lines = []
    for k in ("before", "after_submitted", "after_kept"):
        o = (bal.get("occupation") or {}).get(k)
        if o:
            label = {"before": "now", "after_submitted": f"+{bal['n_submitted']} submitted, all kept",
                     "after_kept": f"+{bal['n_submitted']} x kept share {bal.get('kept_share')}"}[k]
            lines.append(f"occupation {label}: {o['count']} of {bal[k]['n_now']} ({o['share']:.1%}); held "
                         f"{o['held']:g} ({o['status'].replace('_', ' ')})")
    return lines


# --------------------------------------------------------------------------- submission

@dataclass
class SubmitSummary:
    run_id: str
    mode: str
    n_ranking: int
    n_selected: int
    n_counted: int
    n_registered: int
    n_excluded: int
    estimate: dict
    dry_run: bool
    target: Optional[int] = None
    n_candidates: int = 0
    label_fit: Optional[dict] = None
    balance: Optional[dict] = None
    projected_kept: Optional[float] = None
    review_hours: Optional[float] = None
    run_dir: Optional[str] = None
    report: Optional[dict] = None
    followups: list = field(default_factory=list)


def run_submit(run_id: str, *, ranking: Sequence[Mapping], wave_rows: int = WAVE_ROWS_DEFAULT,
               share: float = SHARE_DEFAULT, kept_share: Optional[float] = None, all_rows: bool = False,
               dry_run: bool = True, budget_usd: float = DEFAULT_BUDGET_USD, confirm_expensive: bool = False,
               confirmed_by: Optional[str] = None, transport: str = "batches", registry_path: Path = REGISTRY_PATH,
               registry_rows: Optional[Mapping[str, Mapping]] = None, data_dir: Path = DATA_DIR,
               queue: Optional[Mapping] = None, candidates_dir: Optional[Path] = None,
               label_fit: Optional[Sequence[Mapping]] = None, sources_used: Iterable[str] = (),
               extra_args: Optional[Mapping] = None, relabel="auto", echo=print) -> SubmitSummary:
    """Annotate, select, estimate, gate, record and submit (module docstring).  ``label_fit``: the check's decisions
    (default: the run's ``label_fit/decisions.json`` when present); ``relabel``: ``submit_candidates``'s (the
    adjective sibling of a role-aimed noun, ``roles_pass.RELABEL_ROLE_AIMED``; None off, for tests)."""
    from assistant_axis.gapgen import start_run, submit_candidates
    from assistant_axis.gapgen.registry import Registry
    from . import sources as S
    check_id(run_id, "run_id")
    if transport not in ("live", "batches"):
        raise ValueError("--transport must be live or batches")
    if not all_rows and kept_share is None:
        raise ValueError("--kept-share is required for a metered wave (the pilot's measured role kept share); or --all")
    if registry_rows is None:
        registry_rows = Registry(registry_path).fold() if Path(registry_path).exists() else {}
    if queue is None:
        import data_analysis.seed_entities as se
        queue = se.load_queue(Path(data_dir) / "seed_queue.json")
    corpus = corpus_role_stems(data_dir)
    qstems = queue_role_stems(queue)
    rows = annotate(ranking, registry_rows=registry_rows, corpus_stems=corpus, queue_stems=qstems)
    if all_rows:
        mode, target = "all", None
        sel = select_all(rows)
    else:
        target = wave_target(wave_rows, share, kept_share=kept_share)
        mode = f"wave: {share} x {wave_rows} / kept share {kept_share} = {target} net-new rows"
        sel = select_wave(rows, wave_rows=wave_rows, share=share, kept_share=kept_share)
    n_counted = sum(1 for r in sel if r["net_new"])
    n_registered = sum(1 for r in sel if r["registered_as"])
    n_excluded = sum(1 for r in rows if r["excluded"])
    cands = to_candidates(sel, run_id)
    tdir = run_dir(GENERATOR, run_id, candidates_dir=candidates_dir)
    lf = label_fit if label_fit is not None else read_label_fit(tdir)
    lf_counts = None
    if lf is not None:
        cands, lf_counts = apply_label_fit(cands, lf, excluded_stems=set(corpus) | set(qstems))
    est = estimate_downstream_usd(n_counted, transport=transport)
    projected = n_counted * kept_share if kept_share else None
    hours = projected / REVIEW_TERMS_PER_HOUR if projected is not None else None
    bal = balance_before_after(data_dir, queue, n_submitted=n_counted, kept_share=kept_share)
    excl = Counter(r["excluded"] for r in rows if r["excluded"])
    echo(f"{mode}: {len(rows)} ranked roles; {n_excluded} excluded ({dict(excl)}); selected {len(sel)} ({n_counted} "
         f"net-new, counted; {n_registered} already registered, resubmitted for their provenance and not counted); "
         f"{len(cands)} candidates (one per source)")
    if lf_counts is None:
        echo("  NOTE: no label-fit decisions in this run: `professions_generator.py label-fit` checks the labels "
             "against their glosses before submission")
    else:
        echo(f"  label-fit corrections applied: {json.dumps(lf_counts)}")
    if projected is not None:
        echo(f"  projection: {n_counted} net-new x kept share {kept_share} = {projected:.0f} kept rows, about "
             f"{hours:.1f} h of review at {REVIEW_RATE_SOURCE}")
    for line in balance_text(bal):
        echo(f"  {line}")
    echo(est.format() + f"\n  [{n_counted} net-new rows; the {n_registered} registered rows are not charged]")
    confirm_or_abort(est.total_usd, budget_usd, confirm_expensive=confirm_expensive, confirmed_by=confirmed_by)
    summary = SubmitSummary(run_id=run_id, mode=mode, n_ranking=len(rows), n_selected=len(sel), n_counted=n_counted,
                            n_registered=n_registered, n_excluded=n_excluded, estimate=asdict(est), dry_run=dry_run,
                            target=target, n_candidates=len(cands), label_fit=lf_counts, balance=bal,
                            projected_kept=None if projected is None else round(projected, 1),
                            review_hours=None if hours is None else round(hours, 2))
    summary.followups = followup_commands(run_id, est, candidates_path=tdir / CANDIDATES_NAME)
    if dry_run:
        echo(f"DRY-RUN: would write {_rel(tdir)}/{ATTRIBUTION_NAME} and {CANDIDATES_NAME} ({len(cands)} candidates), "
             f"submit them to {registry_path}, and write keys.txt, {SUBMIT_REPORT_NAME}, run.json, usage.json there")
        for c in summary.followups:
            echo(f"  then: {c}")
        return summary
    keys_used = list(sources_used) or ["onet_occupations", "onet_job_titles", "bls_oews_national"]
    args = {"step": "submit", "mode": mode, "all": bool(all_rows), "wave_rows": wave_rows, "share": share,
            "kept_share": kept_share, "target": target, "n_rows": len(sel), "n_candidates": len(cands),
            "n_counted": n_counted, "n_registered": n_registered, "n_excluded": n_excluded,
            "counted_stems": sorted(r["stem"] for r in sel if r["net_new"]),
            "registered_stems": {r["stem"]: r["registered_as"] for r in sel if r["registered_as"]},
            "excluded": dict(excl), "transport": transport, "budget_usd": budget_usd, "estimate": asdict(est),
            "label_fit": lf_counts, "balance_occupation": bal.get("occupation"),
            "attribution": S.attribution_record(keys_used), **dict(extra_args or {})}
    ctx = start_run(GENERATOR, run_id, args=args, candidates_dir=candidates_dir)
    ctx.confirmed_by = confirmed_by
    S.write_attribution(ctx.dir, keys_used, run_label=f"run {GENERATOR}/{run_id}")
    rep = submit_candidates(cands, registry_path=registry_path, run=ctx, relabel=relabel)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {
        "n_keys": len(rep.keys), "rows_submitted": len(sel), "rows_counted": n_counted,
        "rows_registered": n_registered, "rows_excluded": n_excluded, "n_candidates": len(cands),
        "label_fit": lf_counts, "balance": bal, "estimate": asdict(est), "mode": mode, "target": target}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / SUBMIT_REPORT_NAME)
    ctx.finish()
    summary.run_dir = str(ctx.dir)
    summary.report = rep_d
    echo(f"registry {registry_path}: new {rep.n_new}, merged {rep.n_merged}, unchanged {rep.n_unchanged}")
    echo(f"wrote {_rel(ctx.dir)}/{CANDIDATES_NAME}, {ATTRIBUTION_NAME}, keys.txt, {SUBMIT_REPORT_NAME}, run.json, "
         f"usage.json")
    for c in summary.followups:
        echo(f"  then: {c}")
    return summary


__all__ = ["WAVE_ROWS_DEFAULT", "SHARE_DEFAULT", "M1_PASS_RATE", "DEFAULT_BUDGET_USD", "KIND_GUESS",
           "corpus_role_stems", "queue_role_stems", "registry_role_row", "is_decided", "net_new", "annotate",
           "wave_target", "select_wave", "select_all", "to_candidates", "as_role", "read_label_fit", "apply_label_fit",
           "estimate_downstream_usd", "batch_ids", "followup_commands", "balance_before_after", "balance_text",
           "SubmitSummary", "run_submit"]
