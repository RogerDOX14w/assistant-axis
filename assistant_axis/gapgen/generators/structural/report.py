"""The readouts of a submitted structural run, once M1 and M3 have run (plan sections 7, 10 and 11; tasks 9 and 11).

``report --run-id R`` writes three files into the run's directory:

* ``report.md`` (:func:`render_report`): the yield-per-dollar readout, **led by the already-registered headline**
  (the share of the run's rows another generator, or an earlier run, had already put into the registry, and how many
  of those M1 and M3 had already decided), then the figures **ordered as Roger expects B to be useful** (decision 1,
  2026-10-13): pair completions and degree fillers first, the rest after, and **wholly new concepts as the secondary
  figure, raw and net** (:func:`net_novel`); the **net-new kept share** (kept rows, M3 ``new`` or ``grey``, per
  submitted row the registry had not yet filtered), which replaces the 0.5 assumption in the wave's cut; the
  re-based projections; the cost per model from every ``usage.json``.
* ``roger_sample.md`` (:func:`roger_sample`): 50 rows decided ``new`` or ``grey``, seeded, for Roger's manual
  precision check (trait / not-trait / duplicate; target >= 70% trait-and-new).
* ``ai_identity_subfamily.md`` (:func:`ai_identity_list`): every principal-target item with its M1 verdict and M3
  decision, for the AI-identity sub-family sign-off (QUESTIONS 67 and 78) before any is promoted.

**Novel, raw and net** (2026-10-13): *raw* is the run's rows decided ``new`` or ``grey``; *net* leaves out the rows
whose registry row also carries another generator's candidate (the same stem: one registry row), pending review or
already reviewed (the pending ones are what the plan names; a reviewed twin is not new to the review either, and is
reported apart); *net of review-graph groups* waits for R1 (``net_groups`` None).
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..masked_lm.evaluate import _m1, _m3, cost_summary
from . import GENERATOR
from .submit import KEPT_SHARE_ASSUMED, KEPT_TARGET_DEFAULT, REVIEW_TERMS_PER_HOUR_PLAN, estimate_downstream_usd

#: The readout's order (decision 1): what B is expected to be good at first.
KIND_ORDER: tuple[str, ...] = ("pair_completion", "degree_filler", "opposite", "classical", "retarget",
                               "principal_retarget", "remode")
KIND_NAMES: dict[str, str] = {
    "pair_completion": "pair completions (the opposite of a non-X or singleton trait)",
    "degree_filler": "degree fillers (the excess and deficiency of a trait)",
    "opposite": "opposites of traits already paired or unclassified",
    "classical": "classical rows (generator A)",
    "retarget": "retargeted dispositions",
    "principal_retarget": "principal-target dispositions (the AI-identity sub-family)",
    "remode": "remoded dispositions (attitude, habit, speech)",
}
NOVEL = ("new", "grey")


def run_rows(registry_rows: Mapping[str, Mapping], run_id: str) -> list[Mapping]:
    """Registry rows with a source from this structural run, by key."""
    return [r for _, r in sorted(registry_rows.items())
            if any(s.get("generator") == GENERATOR and s.get("run_id") == run_id for s in r.get("sources") or [])]


def _decision(r: Mapping) -> Optional[str]:
    return (r.get("novelty") or {}).get("decision")


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


@dataclass
class NovelFigures:
    """The novel figure twice (2026-10-13): raw, and net of other generators' candidates of the same stem."""
    raw: int
    net_pending: int
    net_groups: Optional[int] = None
    twins_pending: list = field(default_factory=list)
    twins_reviewed: list = field(default_factory=list)


def net_novel(rows: Sequence[Mapping], registry_rows: Optional[Mapping[str, Mapping]] = None, *,
              generator: str = GENERATOR) -> NovelFigures:
    """Raw: ``rows`` decided ``new`` or ``grey``.  Net: those without another generator's candidate on the same
    registry row (module docstring).  ``registry_rows`` (folded, by key) gives the rows' current state; without it
    ``rows`` are read as they are."""
    novel = []
    for r in rows:
        cur = (registry_rows or {}).get(r.get("key")) or r
        if _decision(cur) in NOVEL:
            novel.append(cur)
    pending, reviewed = [], []
    for r in novel:
        others = {s.get("generator") for s in r.get("sources") or []} - {generator, None}
        if not others:
            continue
        if (r.get("review") or {}).get("status") in (None, "unreviewed"):
            pending.append(r["stem"])
        else:
            reviewed.append(r["stem"])
    return NovelFigures(raw=len(novel), net_pending=len(novel) - len(pending) - len(reviewed), net_groups=None,
                        twins_pending=sorted(pending), twins_reviewed=sorted(reviewed))


def _kinds_by_stem(table: Sequence[Mapping]) -> dict[str, list]:
    return {r["stem"]: list(r.get("kinds") or []) for r in table}


def figures(run_id: str, *, run_dir: Path, registry_rows: Mapping[str, Mapping], table: Sequence[Mapping],
            evaluation: Optional[Mapping] = None, filter_dir: Optional[Path] = None,
            novelty_dir: Optional[Path] = None, extra_usage: Sequence[Path] = (),
            review_rate: tuple[float, str] = (REVIEW_TERMS_PER_HOUR_PLAN, "plan")) -> dict:
    """Every figure the readout prints (module docstring)."""
    run = json.loads((Path(run_dir) / "run.json").read_text(encoding="utf-8")) if (Path(run_dir) / "run.json"
                                                                                    ).exists() else {}
    args = run.get("args") or {}
    rows = run_rows(registry_rows, run_id)
    n = len(rows)
    registered = dict(args.get("registered_stems") or {})
    decided = set(args.get("decided_stems") or [])
    counted = set(args.get("counted_stems") or [])
    by_other = {s: g for s, g in registered.items() if set(g) - {GENERATOR}}
    headline = {"n_rows": n, "already_registered": len(registered), "already_registered_share": _frac(len(registered), n),
                "by_another_generator": len(by_other), "already_decided": len(decided),
                "already_decided_share_of_registered": _frac(len(decided), len(registered)),
                "exists": len(args.get("exists_stems") or []), "queued": len(args.get("queued_stems") or []),
                "net_new": len(counted)}
    kinds = _kinds_by_stem(table)
    m1, m3 = _m1(rows), _m3(rows)
    counted_rows = [r for r in rows if r["stem"] in counted]
    kept_counted = sum(1 for r in counted_rows if _decision(r) in NOVEL)
    scored_counted = sum(1 for r in counted_rows if r.get("novelty"))
    share = _frac(kept_counted, len(counted_rows)) if scored_counted else None
    novel = net_novel(rows, registry_rows)
    novel_counted = net_novel(counted_rows, registry_rows)
    per_kind = {}
    for k in KIND_ORDER:
        kr = [r for r in rows if k in kinds.get(r["stem"], [])]
        if not kr:
            continue
        kc = [r for r in kr if r["stem"] in counted]
        nk = net_novel(kr, registry_rows)
        per_kind[k] = {"n": len(kr), "m1_trait_share": _m1(kr)["pass_rate"],
                       "novel_raw": nk.raw, "novel_net": nk.net_pending, "novel_raw_share": _frac(nk.raw, len(kr)),
                       "net_new": len(kc),
                       "net_new_kept_share": _frac(sum(1 for r in kc if _decision(r) in NOVEL), len(kc)),
                       "pair_completions_m3": sum(1 for r in kr if (r.get("novelty") or {}).get("pair_completion_for"))}
    batch = f"{run_id}_{GENERATOR}"
    fdir = Path(filter_dir) if filter_dir else Path(run_dir).parents[2] / "filter" / batch
    ndir = Path(novelty_dir) if novelty_dir else Path(run_dir).parents[2] / "novelty" / batch
    cost = cost_summary([Path(run_dir) / "usage.json", *[Path(p) for p in extra_usage], fdir / "usage.json",
                         ndir / "usage.json"])
    useful = m3["decision"].get("new", 0) + m3["pair_completions"]
    rate, rate_src = review_rate
    proj = None
    if share:
        need = math.ceil(KEPT_TARGET_DEFAULT / share)
        ratio = n / len(counted) if counted else 1.0
        n_sub = int(round(need * ratio))
        table_net = sum(1 for r in table if r.get("net_new"))
        proj = {"kept_share": share, "wave_300": {"net_new_rows": need, "rows_to_submit": n_sub,
                                                  "kept_rows": KEPT_TARGET_DEFAULT,
                                                  "novel_raw": round(need * novel_counted.raw / len(counted_rows)),
                                                  "novel_net": round(need * novel_counted.net_pending
                                                                     / len(counted_rows)),
                                                  "review_hours": round(KEPT_TARGET_DEFAULT / rate, 2),
                                                  "estimate_batches": estimate_downstream_usd(
                                                      n_sub, transport="batches").total_usd},
                "whole_table": {"rows": len(table), "net_new_rows": table_net,
                                "kept_rows": round(table_net * share),
                                "review_hours": round(table_net * share / rate, 2),
                                "estimate_batches": estimate_downstream_usd(
                                    sum(1 for r in table if not r.get("registered_decided")),
                                    transport="batches").total_usd}}
    return {"run_id": run_id, "generator": GENERATOR, "args": {k: v for k, v in args.items()
                                                               if not k.endswith("_stems")},
            "headline": headline, "m1": m1, "m3": {k: v for k, v in m3.items() if not k.endswith("_stems")},
            "net_new_kept_share": share, "net_new_kept_share_assumed": KEPT_SHARE_ASSUMED, "kept_net_new": kept_counted,
            "novel": asdict(novel), "per_kind": per_kind, "cost": cost, "useful": useful,
            "useful_per_dollar": round(useful / cost["total_usd"], 1) if cost["total_usd"] else None,
            "review_rate": {"terms_per_hour": rate, "source": rate_src}, "projection": proj,
            "evaluation": {k: (evaluation or {}).get(k) for k in ("pair_recovery", "structure_recovery",
                                                                    "queue_holdout", "null_rates", "stability",
                                                                    "parse_rate")}}


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _link_trait(stem: str, prefix: str, label: Optional[str] = None) -> str:
    return f"[{label or stem.replace('_', ' ')}]({prefix}{stem}.json)"


def render_report(fig: Mapping, *, trait_prefix: str = "../../../../traits/instructions/") -> str:
    """``report.md`` (module docstring)."""
    h, nv = fig["headline"], fig["novel"]
    L = [f"# Structural run `{fig['run_id']}`: yield-per-dollar readout", "",
         "Written by `structural_generator.py report` (coding_plan_09 sections 10-11); figures from the registry "
         "blocks, `evaluation.json` and every `usage.json`.  Terms: [glossary](../../../../../reports/"
         "trait_gap_generation/glossary.md).", "",
         "## Already registered (the headline)", "",
         f"Of the run's {h['n_rows']} registry rows, **{h['already_registered']} "
         f"({_pct(h['already_registered_share'])}) were already in the registry when the run was submitted** "
         f"({h['by_another_generator']} by another generator), and M1 and M3 had already decided "
         f"{h['already_decided']} of those ({_pct(h['already_decided_share_of_registered'])}): free, no review row, "
         f"arrangement evidence only.  {h['exists']} rows are corpus traits and {h['queued']} seed-queue entries; "
         f"**{h['net_new']} were net-new** (not yet filtered by the registry).", "",
         "## Pair completions and degree fillers first", "",
         "| what | rows | M1 trait share | novel raw | novel net | net-new rows | net-new kept share | "
         "M3 pair completions |", "|---|---|---|---|---|---|---|---|"]
    for k in KIND_ORDER:
        p = fig["per_kind"].get(k)
        if p:
            L.append(f"| {KIND_NAMES[k]} | {p['n']} | {_pct(p['m1_trait_share'])} | {p['novel_raw']} | "
                     f"{p['novel_net']} | {p['net_new']} | {_pct(p['net_new_kept_share'])} | "
                     f"{p['pair_completions_m3']} |")
    L += ["", "A row reached by several routes is counted under each.", "",
          "## Wholly new concepts (secondary)", "",
          f"Novel after the scorer (M3 `new` or `grey`): **{nv['raw']} raw**, **{nv['net_pending']} net** of other "
          f"generators' candidates of the same stem ({len(nv['twins_pending'])} pending review, "
          f"{len(nv['twins_reviewed'])} already reviewed); net of review-graph groups: "
          f"{'not yet (R1 has not run)' if nv.get('net_groups') is None else nv['net_groups']}.", "",
          "## The net-new kept share and the re-based projections", ""]
    share = fig.get("net_new_kept_share")
    L.append(f"Net-new kept share (kept rows per submitted net-new row): **{_pct(share)}** "
             f"(the wave's cut assumed {fig['net_new_kept_share_assumed']} until now; {fig['kept_net_new']} kept).")
    pr = fig.get("projection")
    if pr:
        w, t = pr["wave_300"], pr["whole_table"]
        L += ["", f"- **The 300-kept wave** (decision 1): {w['net_new_rows']} net-new rows, about {w['rows_to_submit']} "
                  f"rows submitted, novel about {w['novel_raw']} raw and {w['novel_net']} net, about "
                  f"{w['review_hours']} h of review at {fig['review_rate']['terms_per_hour']:.0f} terms an hour "
                  f"({fig['review_rate']['source']}), downstream about ${w['estimate_batches']:.2f} batched.",
              f"- **The whole table**: {t['rows']} rows, {t['net_new_rows']} net-new, about {t['kept_rows']} kept, "
              f"{t['review_hours']} h, about ${t['estimate_batches']:.2f} batched."]
    m1, m3 = fig["m1"], fig["m3"]
    L += ["", "## M1 and M3", "",
          f"M1: {m1['n_filtered']} of {m1['n_rows']} rows filtered, {m1['n_trait']} traits (pass rate "
          f"{_pct(m1['pass_rate'])}); verdicts {m1['verdict']}.  M3: {m3['n_scored']} scored, decisions "
          f"{m3['decision']}, {m3['pair_completions']} pair completions.  Useful (new or pair completion): "
          f"{fig['useful']}, {fig['useful_per_dollar']} per dollar.", "", "## Cost", "",
          "| model | calls | cost |", "|---|---|---|"]
    for m, u in fig["cost"]["per_model"].items():
        L.append(f"| {m} | {u['n_calls']} | ${u['cost_usd']:.4f} |")
    L += [f"| **total** | | **${fig['cost']['total_usd']:.4f}** |", "",
          "Files read: " + ", ".join(f"`{Path(f).name}` ({Path(f).parent.name})" for f in fig["cost"]["files"]), ""]
    ev = fig.get("evaluation") or {}
    if any(ev.values()):
        L += ["## The free checks (evaluation.json)", ""]
        pr_ = ev.get("pair_recovery") or {}
        if pr_:
            L.append(f"- Pair recovery: {_pct(pr_.get('recall_stem'))} by stem of {pr_.get('n_answered')} directions "
                     f"(expected > 80%); by cosine 0.8: {_pct(pr_.get('recall_cos_0.8'))}.")
        sr_ = ev.get("structure_recovery") or {}
        if sr_:
            tri, seq = sr_.get("triangles") or {}, sr_.get("sequence") or {}
            L.append(f"- Structure: {tri.get('corners_recovered')} of {tri.get('corners')} triangle corners; "
                     f"{seq.get('recovered')} of the {seq.get('n')}-member sequence.")
        qh = ev.get("queue_holdout") or {}
        if qh:
            L.append(f"- Queue hold-out: {_pct(qh.get('recall_stem'))} of {qh.get('n')}; rejected names regenerated "
                     f"{(qh.get('rejected') or {}).get('regenerated')} of {(qh.get('rejected') or {}).get('n')}; "
                     f"accepted {_pct((qh.get('accepted') or {}).get('recall_stem'))}, candidates "
                     f"{_pct((qh.get('candidates') or {}).get('recall_stem'))} (never in the denominator).")
        L.append("")
    L += ["## Files", "", "- [roger_sample.md](./roger_sample.md): 50 rows decided new or grey, for the manual check.",
          "- [ai_identity_subfamily.md](./ai_identity_subfamily.md): the principal-target items, for sign-off.", ""]
    return "\n".join(L)


def _sources_text(stem: str, table_by: Mapping[str, Mapping], prefix: str) -> str:
    row = table_by.get(stem)
    if not row:
        return "?"
    bits = []
    for s in row["sources"][:4]:
        if s["generator_part"] == "classical":
            bits.append(f"{s['role']} of `{s['source_id']}`")
        else:
            sub = s.get("target") or s.get("mode")
            bits.append(f"{s['operator']}{' ' + sub if sub else ''} of "
                        f"{_link_trait(s['source_stem'], prefix, s.get('source_label'))}")
    more = len(row["sources"]) - 4
    return "; ".join(bits) + (f"; +{more}" if more > 0 else "")


def _cell(s) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ")


def roger_sample(rows: Sequence[Mapping], table: Sequence[Mapping], *, n: int = 50, seed: int = 0,
                 run_id: str = "", trait_prefix: str = "../../../../traits/instructions/") -> str:
    """50 run rows decided ``new`` or ``grey``, seeded, as a table for Roger's verdicts."""
    pool = sorted((r for r in rows if _decision(r) in NOVEL), key=lambda r: r["key"])
    pick = sorted(random.Random(f"structural-sample:{seed}").sample(pool, min(n, len(pool))), key=lambda r: r["key"])
    by = {r["stem"]: r for r in table}
    L = [f"# Precision sample, structural run `{run_id}`", "",
         f"{len(pick)} rows drawn (seed {seed}) from the {len(pool)} the scorer decided `new` or `grey`.  Mark each "
         f"**trait** (a new persona trait), **not-trait** or **duplicate** (of a corpus or queued trait) in the last "
         f"column; the target is 70% or more trait-and-new (plan 09 section 6.4).", "",
         "| # | label | gloss | how the generator reached it | M1 | M3 | Roger |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(pick, 1):
        t = by.get(r["stem"]) or {}
        L.append(f"| {i} | {_cell(r.get('label'))} | {_cell(t.get('gloss') or r.get('gloss'))} | "
                 f"{_sources_text(r['stem'], by, trait_prefix)} | {_cell((r.get('filter') or {}).get('verdict'))} | "
                 f"{_cell(_decision(r))} | |")
    return "\n".join(L) + "\n"


def ai_identity_list(table: Sequence[Mapping], registry_rows: Optional[Mapping[str, Mapping]] = None, *,
                     run_id: Optional[str] = None, trait_prefix: str = "../../../../traits/instructions/") -> str:
    """Every principal-target item (QUESTIONS 67 and 78 sign-off) with its M1 verdict and M3 decision."""
    reg_by_stem = {}
    for r in (registry_rows or {}).values():
        reg_by_stem.setdefault(r.get("stem"), r)
    L = [f"# The AI-identity sub-family: principal-target items{f' (run `{run_id}`)' if run_id else ''}", "",
         "Every answer of the operators call for the user, the operator or the developer as the target (stage 1: the "
         "traits at alignment score 3).  These presuppose an AI assistant, so none is promoted before Roger signs "
         "the sub-family off (QUESTIONS 67 and 78).", "",
         "| label | gloss | target | from trait | M1 | M3 | sign-off |", "|---|---|---|---|---|---|---|"]
    n = 0
    for row in sorted(table, key=lambda r: r["rank"]):
        if not row.get("principal_target"):
            continue
        reg = reg_by_stem.get(row["stem"]) or {}
        if run_id and registry_rows is not None and not any(
                s.get("generator") == GENERATOR and s.get("run_id") == run_id for s in reg.get("sources") or []):
            continue
        for s in row["sources"]:
            if s.get("kind") != "principal_retarget":
                continue
            n += 1
            L.append(f"| {_cell(row['label'])} | {_cell(s.get('gloss'))} | {s.get('target')} | "
                     f"{_link_trait(s['source_stem'], trait_prefix, s.get('source_label'))} | "
                     f"{_cell((reg.get('filter') or {}).get('verdict'))} "
                     f"| {_cell((reg.get('novelty') or {}).get('decision'))} | |")
    L += ["", f"{n} items."]
    return "\n".join(L) + "\n"


__all__ = ["KIND_ORDER", "KIND_NAMES", "NovelFigures", "run_rows", "net_novel", "figures", "render_report",
           "roger_sample", "ai_identity_list"]
