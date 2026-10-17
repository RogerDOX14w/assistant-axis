"""Readouts for Roger (plan sections 5, 7, 10 and 11): the free readout of ``evaluate`` and a run's three files.

* :func:`render_readout` (``readout.md`` under ``data/candidates/corpus_frames/``, written by ``evaluate``): the
  recovery of our labels under both orderings beside the frequency baselines, the ordering chosen, the per-frame
  table (fillers, forms, registered and corpus shares, recall at 1,000; after the pilot the yield, the net filter,
  the unique kept rows and the keep verdict), the labels no frame finds by region, the registry overlap at depth.
* ``report --run-id R`` writes into the run's directory:

  - ``report.md`` (:func:`render_report`, from :func:`figures`), in the plan's section 10 order: (1) the
    **already-registered headline**; (2) **per frame**: yield, ``region_tv``, ``form_tv``, ``physical_state_share``,
    the region histogram, the forms, ``unique_kept`` and the keep verdict, frames sorted by yield within type;
    (3) **per type**: the same distances and the labels only that type found; (4) the M1 trait share of the net-new
    rows, the **net-new kept share** (it replaces the proxy's 0.3 in the wave's cut), the novel share raw and net of
    other generators' candidates of the same stem, the nominal rows M1 held on the roles list, the relabel counts,
    M1's parse rate; (5) cost per model from every ``usage.json``, kept rows per dollar, and the re-based projections
    (the whole table over the kept frames; a 300-kept wave).  It names **the contributing frame of every kept row**.
  - ``roger_sample.md`` (:func:`roger_sample`): 50 kept rows, seeded, to mark trait / not a trait / duplicate.
  - ``roger_first_hour.md`` (:func:`roger_first_hour`): the 150 kept rows furthest from the corpus by M3's nearest
    cosine, ``new`` before ``grey`` (Roger, 2026-10-13: "start with an hour's review of the ones that seem most novel").

Every file is linked relative to the document, every corpus trait named links to its trait file, and terms link to
the glossary.  Nothing here calls a model.
"""
from __future__ import annotations

import json
import math
import os
import random
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen.paths import DATA_DIR, REPO_ROOT

from ..masked_lm.evaluate import _m1, _m3, cost_summary
from . import GENERATOR
from .evaluate import NOVEL

GLOSSARY = REPO_ROOT / "reports" / "trait_gap_generation" / "glossary.md"
PLAN = REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_05_corpus_frames.md"
TRAITS_DIR = DATA_DIR / "traits" / "instructions"
SAMPLE_N = 50
FIRST_HOUR_N = 150


# --------------------------------------------------------------------------- small helpers

def _link(target: Path, doc: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc).parent)
    return f"[{text or Path(target).name}]({rel.replace(os.sep, '/')})"


def _gl(doc: Path, anchor: str, text: str) -> str:
    rel = os.path.relpath(GLOSSARY, Path(doc).parent).replace(os.sep, "/")
    return f"[{text}]({rel}#{anchor})"


def _trait(stem: str, doc: Path, traits_dir: Path = TRAITS_DIR, label: Optional[str] = None) -> str:
    """A corpus trait linked to its file (plain text when there is no such file)."""
    text = label or stem.replace("_", " ")
    p = Path(traits_dir) / f"{stem}.json"
    return _link(p, doc, text) if p.exists() else text


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def _num(x, nd: int = 2) -> str:
    if x is None:
        return "n/a"
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def _cell(s) -> str:
    return str("" if s is None else s).replace("|", "/").replace("\n", " ")


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def contributing_frames(rows: Sequence[Mapping]) -> dict[str, list[str]]:
    """``{stem: [frame keys]}``: every frame that found each row, best within-frame rank first."""
    out = {}
    for r in rows:
        fr = r.get("frames") or {}
        out[r["stem"]] = sorted(fr, key=lambda k: (int(fr[k].get("rank_volumes") or 1 << 30), k))
    return out


def _nearest(reg_row: Optional[Mapping]) -> tuple[Optional[str], Optional[float]]:
    """M3's nearest corpus trait and its cosine (the first of ``listed``), or ``(None, None)``."""
    listed = ((reg_row or {}).get("novelty") or {}).get("listed") or []
    best = None
    for x in listed:
        c = x.get("cosine")
        if c is None:
            continue
        if best is None or float(c) > float(best.get("cosine")):
            best = x
    return (best.get("stem"), float(best["cosine"])) if best else (None, None)


def run_rows(registry_rows: Mapping[str, Mapping], run_id: str) -> list[Mapping]:
    """Registry rows with a source from this corpus-frames run (the noun siblings included), by key."""
    return [r for _, r in sorted(registry_rows.items())
            if any(s.get("generator") == GENERATOR and s.get("run_id") == run_id for s in r.get("sources") or [])]


def net_novel(rows: Sequence[Mapping], *, generator: str = GENERATOR) -> dict:
    """The novel figure twice (plan 09 section 10): raw, the rows decided ``new`` or ``grey``; net, those without
    another generator's candidate on the same registry row (pending review, or already reviewed and reported
    apart)."""
    novel = [r for r in rows if (r.get("novelty") or {}).get("decision") in NOVEL]
    pending, reviewed = [], []
    for r in novel:
        others = {s.get("generator") for s in r.get("sources") or []} - {generator, None}
        if not others:
            continue
        (pending if (r.get("review") or {}).get("status") in (None, "unreviewed") else reviewed).append(r["stem"])
    return {"raw": len(novel), "net_pending": len(novel) - len(pending) - len(reviewed),
            "twins_pending": sorted(pending), "twins_reviewed": sorted(reviewed)}


def submit_args(run: Mapping) -> dict:
    """The submit step's arguments: the latest session whose ``step`` is ``submit``, else the top-level ``args``."""
    for s in reversed(run.get("sessions") or []):
        a = s.get("args") or {}
        if a.get("step") == "submit":
            return a
    return run.get("args") or {}


# --------------------------------------------------------------------------- the run's figures

def figures(run_id: str, *, run_dir: Path, registry_rows: Mapping[str, Mapping], table: Sequence[Mapping],
            evaluation: Optional[Mapping] = None, frame_types: Optional[Mapping[str, str]] = None,
            filter_dir: Optional[Path] = None, novelty_dir: Optional[Path] = None,
            review_rate: tuple[float, str] = (146.0, "plan")) -> dict:
    """Every figure :func:`render_report` prints (module docstring)."""
    from .submit import KEPT_SHARE_ASSUMED, KEPT_TARGET_DEFAULT, charged_rows, estimate_downstream_usd, select_wave
    rd = Path(run_dir)
    run = json.loads((rd / "run.json").read_text(encoding="utf-8")) if (rd / "run.json").exists() else {}
    args = submit_args(run)
    ev = evaluation or {}
    frame_types = dict(frame_types or {})
    by_stem = {r["stem"]: r for r in table}
    rows = run_rows(registry_rows, run_id)
    n_sel = int(args.get("n_rows") or 0)
    registered = dict(args.get("registered_stems") or {})
    decided = set(args.get("decided_stems") or [])
    counted = set(args.get("counted_stems") or []) | set(args.get("sibling_counted_stems") or [])
    by_other = {s: g for s, g in registered.items() if set(g) - {GENERATOR}}
    headline = {"n_rows": n_sel, "n_registry_rows": len(rows), "already_registered": len(registered),
                "already_registered_share": _frac(len(registered), n_sel), "by_another_generator": len(by_other),
                "already_decided": len(decided), "already_decided_share_of_registered": _frac(len(decided),
                                                                                           len(registered)),
                "corpus": len(args.get("corpus_stems") or []), "queued": len(args.get("queued_stems") or []),
                "net_new_rows": len(counted)}
    m1, m3 = _m1(rows), _m3(rows)
    counted_rows = [r for r in rows if r.get("stem") in counted]
    m1_new = _m1(counted_rows)
    kept_new = sum(1 for r in counted_rows if (r.get("novelty") or {}).get("decision") in NOVEL)
    scored_new = sum(1 for r in counted_rows if r.get("novelty"))
    share = _frac(kept_new, len(counted_rows)) if scored_new else None
    novel, novel_new = net_novel(rows), net_novel(counted_rows)
    # nominal rows M1 held on the roles list (open decision 3), the relabel counts
    held_roles = sorted(r["stem"] for r in rows if r.get("holding") == "roles")
    sib = dict(args.get("sibling_stems") or {})
    rules = Counter(str((by_stem.get(st) or {}).get("relabel_rule")) for st in sib)
    linked = sum(1 for r in rows if r.get("relabel"))
    submitted = {x for xs in (args.get("selection_by_frame") or {}).values() for x in xs} | \
        set(args.get("wave_order") or [])
    nouns_left = sorted(st for st in submitted if (by_stem.get(st) or {}).get("form") == "noun")
    parse = None
    if filter_dir and (Path(filter_dir) / "summary.json").exists():
        d = json.loads((Path(filter_dir) / "summary.json").read_text(encoding="utf-8"))
        d = d.get("result", d)
        parse = {"parse_rate": d.get("parse_rate"), "parse_rate_first_pass": d.get("parse_rate_first_pass")}
    batch = f"{run_id}_{GENERATOR}"
    fdir = Path(filter_dir) if filter_dir else rd.parents[2] / "filter" / batch
    ndir = Path(novelty_dir) if novelty_dir else rd.parents[2] / "novelty" / batch
    cost = cost_summary([rd / "usage.json", fdir / "usage.json", ndir / "usage.json"])
    kept_all = m3.get("kept", 0)
    # the contributing frame of every kept row (and the rows only one frame found)
    kept_rows = []
    by_surface = {x["surface_stem"]: x for x in table if x.get("surface_stem")}
    for r in rows:
        if (r.get("novelty") or {}).get("decision") not in NOVEL:
            continue
        t = by_stem.get(r["stem"]) or by_surface.get(r["stem"])
        fr = contributing_frames([t])[t["stem"]] if t else []
        near, cos = _nearest(r)
        kept_rows.append({"stem": r["stem"], "label": r.get("label"), "decision": r["novelty"]["decision"],
                          "frames": fr, "only_frame": fr[0] if len(fr) == 1 else None, "nearest": near,
                          "cosine": cos, "gloss": r.get("gloss"), "table_stem": t["stem"] if t else None})
    only_one = {}
    for k in kept_rows:
        if k["only_frame"]:
            only_one.setdefault(k["only_frame"], []).append(k["stem"])
    rate, rate_src = review_rate
    proj = None
    kept_frames = ev.get("frames_kept") or sorted({k for r in table for k in r.get("frames") or {}})
    ordering = ev.get("ordering") or args.get("ordering") or "volumes"
    if share:
        in_kept = [r for r in table if r.get("eligible") and set(r.get("frames") or {}) & set(kept_frames)]
        whole_new = sum(charged_rows(r) for r in in_kept)
        wave_rows, wave_counted = select_wave(table, kept_target=KEPT_TARGET_DEFAULT, kept_share=share,
                                              frames_kept=kept_frames, ordering=ordering)
        wave_charged = sum(charged_rows(r) for r in wave_rows)
        proj = {"kept_share": share, "frames_kept": len(kept_frames),
                "whole_table": {"rows": len(in_kept), "net_new_rows": whole_new, "kept_rows": round(whole_new * share),
                                "review_hours": round(whole_new * share / rate, 2) if rate else None,
                                "estimate_live": estimate_downstream_usd(whole_new).total_usd,
                                "estimate_batches": estimate_downstream_usd(whole_new, transport="batches").total_usd},
                "wave_300": {"rows_to_submit": len(wave_rows), "net_new_rows": wave_charged,
                             "kept_rows": round(wave_charged * share),
                             "review_hours": round(wave_charged * share / rate, 2) if rate else None,
                             "estimate_live": estimate_downstream_usd(wave_charged).total_usd,
                             "estimate_batches": estimate_downstream_usd(wave_charged,
                                                                         transport="batches").total_usd}}
    return {"run_id": run_id, "generator": GENERATOR, "mode": args.get("mode"), "ordering": ordering,
            "args": {k: v for k, v in args.items() if not k.endswith("_stems") and k not in
                     ("selection_by_frame", "wave_order", "sibling_stems")},
            "headline": headline, "m1": m1, "m3": {k: v for k, v in m3.items() if not k.endswith("_stems")},
            "m1_net_new": m1_new, "net_new_kept_share": share, "net_new_kept_share_assumed": KEPT_SHARE_ASSUMED,
            "kept_net_new": kept_new, "kept_all": kept_all, "novel": novel, "novel_net_new": novel_new,
            "held_on_roles": held_roles, "relabel": {"noun_rows": len(sib), "rules": dict(sorted(rules.items())),
                                                     "linked_registry_rows": linked,
                                                     "nouns_left_as_nouns": nouns_left},
            "m1_parse": parse, "cost": cost,
            "useful_per_dollar": round(kept_all / cost["total_usd"], 1) if cost["total_usd"] else None,
            "frame_measures": ev.get("frame_measures"), "type_measures": ev.get("type_measures"),
            "frame_verdicts": ev.get("frame_verdicts") or {}, "frames_kept": ev.get("frames_kept"),
            "frame_types": frame_types, "kept_rows": kept_rows, "only_one_frame": dict(sorted(only_one.items())),
            "review_rate": {"terms_per_hour": rate, "source": rate_src}, "projection": proj,
            "filter_dir": str(fdir), "novelty_dir": str(ndir)}


# --------------------------------------------------------------------------- rendering

def render_report(fig: Mapping, *, doc_path: Path, table_path: Optional[Path] = None,
                  traits_dir: Path = TRAITS_DIR) -> str:
    """A run's ``report.md`` in the section 10 order (module docstring)."""
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    h, m1, m3 = fig["headline"], fig.get("m1") or {}, fig.get("m3") or {}
    types = fig.get("frame_types") or {}
    lines = [f"# Corpus-frames generator: run `{fig['run_id']}` readout", "",
             f"Plan: {L(PLAN)}.  Terms: {L(GLOSSARY, 'glossary')}.  Selection: {fig.get('mode')}; ordering "
             f"{fig.get('ordering')}.  A **{_gl(d, 'lexical-frame', 'frame')}** is a fixed string with one slot; "
             f"its **fillers** are the words found in the slot.  **M1** is the platform's trait-hood filter, **M3** "
             f"its novelty check; a **kept** row is one M3 decides `new` or `grey` (it goes to review); a "
             f"**{_gl(d, 'net-new', 'net-new')}** row is one the registry had not yet filtered when the run was "
             f"submitted.", ""]
    if table_path:
        lines += [f"Table: {L(table_path)} (git-ignored; its sha256 is in the run's {L(d.with_name('run.json'))})."
                  , ""]
    lines += ["## 1. Already registered", "",
              f"Of the run's **{h['n_rows']}** table rows, **{h['already_registered']}** "
              f"({_pct(h['already_registered_share'])}) were already in the registry when it was submitted "
              f"({h['by_another_generator']} from another generator), and M1 and M3 had decided "
              f"**{h['already_decided']}** of those ({_pct(h['already_decided_share_of_registered'])}); "
              f"{h['corpus']} are corpus traits and "
              f"{h['queued']} seed-queue entries.  **{h['net_new_rows']}** registry rows were net-new (a relabelled "
              f"noun is two rows, the noun and its adjective); the run made {h['n_registry_rows']} registry rows in "
              f"all.", ""]
    fm = fig.get("frame_measures") or {}
    verdicts = fig.get("frame_verdicts") or {}
    lines += ["## 2. Per frame", ""]
    if not fm:
        lines += ["No frame measures yet: run `evaluate --pilot-run <run id>` after M1 and M3.", ""]
    else:
        lines += [f"Over each frame's own pilot fillers.  **{_gl(d, 'frame-yield', 'Yield')}**: the M1 trait share of "
                  f"its filtered fillers.  **{_gl(d, 'net-filter', 'Net filter')}**: `region_tv` and `form_tv`, the "
                  f"total variation distance of its trait fillers' region and form distributions from the union's "
                  f"(0 the same, 1 disjoint).  **{_gl(d, 'unique-contribution', 'Unique kept')}**: kept rows no other "
                  f"frame found.  Sorted by yield within type.", "",
                  "| frame | type | n | filtered | yield | region_tv | form_tv | physical or state | kept | unique "
                  "kept | forms | keep |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        keys = [k for k in fm if k != "_union"]
        keys.sort(key=lambda k: (types.get(k, "?"), -(fm[k].get("yield") or -1), k))
        for k in keys:
            m = fm[k]
            v = verdicts.get(k) or [None, ""]
            lines.append(f"| `{k}` | {types.get(k, '?')} | {m['n']} | {m['n_filtered']} | {_pct(m.get('yield'))} | "
                         f"{_num(m.get('region_tv'))} | {_num(m.get('form_tv'))} | "
                         f"{_pct(m.get('physical_state_share'))} | {m.get('kept')} | {m.get('unique_kept')} | "
                         f"{_cell(m.get('forms'))} | {'yes' if v[0] else 'no' if v[0] is False else '?'}: "
                         f"{_cell(v[1])} |")
        u = fm.get("_union") or {}
        lines += ["", f"The union: {u.get('n')} rows, yield {_pct(u.get('yield'))}, regions {_cell(u.get('regions'))}.",
                  "", "Region histograms (trait fillers):", ""]
        for k in keys:
            lines.append(f"- `{k}`: {_cell(fm[k].get('regions'))}")
        lines.append("")
    tm = fig.get("type_measures") or {}
    lines += ["## 3. Per type", ""]
    if not tm:
        lines += ["No type measures yet.", ""]
    else:
        lines += ["| type | n | yield | region_tv | form_tv | kept | labels only this type found |",
                  "|---|---|---|---|---|---|---|"]
        for t, m in sorted(tm.items()):
            only = ", ".join(_trait(s, d, traits_dir) for s in m.get("only_this_type_kept") or []) or "none"
            lines.append(f"| {t} | {m['n']} | {_pct(m.get('yield'))} | {_num(m.get('region_tv'))} | "
                         f"{_num(m.get('form_tv'))} | {m.get('kept')} | {only} |")
        lines.append("")
    nv, nvn, rl = fig.get("novel") or {}, fig.get("novel_net_new") or {}, fig.get("relabel") or {}
    m1n = fig.get("m1_net_new") or {}
    lines += ["## 4. M1 and M3", "",
              f"M1 filtered {m1.get('n_filtered', 0)} of the run's {m1.get('n_rows', 0)} registry rows: verdicts "
              f"{_cell(m1.get('verdict'))}; trait share {_pct(m1.get('pass_rate'))}.  **M1 trait share of the net-new "
              f"rows: {_pct(m1n.get('pass_rate'))}** ({m1n.get('n_trait', 0)} of {m1n.get('n_filtered', 0)}; the "
              f"estimate assumed 88%).", "",
              f"M3 scored {m3.get('n_scored', 0)}: {_cell(m3.get('decision'))}.  **Net-new kept share "
              f"{_pct(fig.get('net_new_kept_share'))}** ({fig.get('kept_net_new')} kept of {h['net_new_rows']} net-new "
              f"rows; the wave's cut assumed {fig.get('net_new_kept_share_assumed')} until now).", "",
              f"Novel after M3 (`new` or `grey`): **{nv.get('raw', 0)} raw**, **{nv.get('net_pending', 0)} net** of "
              f"other generators' candidates of the same stem ({len(nv.get('twins_pending') or [])} pending review, "
              f"{len(nv.get('twins_reviewed') or [])} already reviewed); over the net-new rows "
              f"{nvn.get('raw', 0)} raw, {nvn.get('net_pending', 0)} net.", "",
              f"Nominal rows M1 held on the roles list (open decision 3): {len(fig.get('held_on_roles') or [])}"
              + (": " + ", ".join(f"`{s}`" for s in fig['held_on_roles']) if fig.get("held_on_roles") else "") + ".  "
              f"Relabelled nouns submitted: {rl.get('noun_rows', 0)}, by rule {_cell(rl.get('rules'))}; registry rows "
              f"linked by a relabel block: {rl.get('linked_registry_rows', 0)}; nouns the helper left as nouns: "
              f"{len(rl.get('nouns_left_as_nouns') or [])}.", "",
              f"M1's parse rate: {_cell(fig.get('m1_parse') or 'n/a (no summary.json in the M1 batch yet)')}.", ""]
    c = fig.get("cost") or {}
    pj = fig.get("projection") or {}
    rr = fig.get("review_rate") or {}
    lines += ["## 5. Cost and the re-based projections", "",
              f"Total ${c.get('total_usd', 0):.4f} from " + (", ".join(L(Path(p)) for p in c.get("files") or [])
                                                            or "no usage file yet")
              + f"; per model {_cell(c.get('per_model'))}.  Kept rows per dollar: {_num(fig.get('useful_per_dollar'))}"
              f".  The generator itself is $0 (its run's usage record has no calls).", ""]
    if pj:
        w, t = pj["wave_300"], pj["whole_table"]
        lines += [f"At the measured net-new kept share {pj['kept_share']} over the {pj['frames_kept']} frames kept, "
                  f"at {rr.get('terms_per_hour')} terms an hour ({rr.get('source')}):", "",
                  f"- **A 300-kept wave**: {w['rows_to_submit']} rows to submit, {w['net_new_rows']} net-new, about "
                  f"{w['kept_rows']} kept, about {w['review_hours']} h of review; about ${w['estimate_live']:.2f} live "
                  f"or ${w['estimate_batches']:.2f} batched.",
                  f"- **The whole table over the kept frames**: {t['rows']} rows, {t['net_new_rows']} net-new, about "
                  f"{t['kept_rows']} kept, about {t['review_hours']} h of review; about ${t['estimate_live']:.2f} live "
                  f"or ${t['estimate_batches']:.2f} batched.", ""]
    else:
        lines += ["No projection yet (no measured kept share).", ""]
    kr = fig.get("kept_rows") or []
    lines += ["## The contributing frames of every kept row", "",
              f"{len(kr)} kept rows; each with every frame that found it, best within-frame rank first.", "",
              "| row | M3 | frames | nearest corpus trait (cosine) |", "|---|---|---|---|"]
    for k in sorted(kr, key=lambda k: (k["decision"] != "new", k["stem"])):
        near = (f"{_trait(k['nearest'], d, traits_dir)} ({k['cosine']:.2f})" if k.get("nearest") and k.get("cosine")
                is not None else "n/a")
        lines.append(f"| {_cell(k.get('label') or k['stem'])} | {k['decision']} | "
                     f"{', '.join('`' + f + '`' for f in k['frames']) or 'n/a'} | {near} |")
    lines += ["", "Kept rows only one frame found: " + ("; ".join(
        f"`{f}` {len(v)} ({', '.join(v[:12])}{', ...' if len(v) > 12 else ''})"
        for f, v in (fig.get("only_one_frame") or {}).items()) or "none") + ".", "",
              "## Files", "",
              f"- {L(d.with_name('candidates.jsonl'))}, {L(d.with_name('run.json'))}, {L(d.with_name('usage.json'))},"
              f" {L(d.with_name('submit_report.json'))}",
              f"- M1 batch {L(Path(fig['filter_dir']), Path(fig['filter_dir']).name)}, M3 batch "
              f"{L(Path(fig['novelty_dir']), Path(fig['novelty_dir']).name)}",
              f"- {L(d.with_name('roger_sample.md'))}: the {SAMPLE_N}-row spot check; "
              f"{L(d.with_name('roger_first_hour.md'))}: the first hour of review", ""]
    return "\n".join(lines)


def _recall_table(rec: Mapping, names: Sequence[str], label_set: str, cutoffs: Sequence[int],
                  classes: Sequence[str] = ("all", "single", "hyphenated", "multiword")) -> list[str]:
    head = "| ranking | labels | n | " + " | ".join(f"recall@{k:,}" for k in cutoffs) + " | anywhere |"
    lines = [head, "|" + "---|" * (len(cutoffs) + 4)]
    for name in names:
        for c in classes:
            v = ((rec.get(name) or {}).get(label_set) or {}).get(c)
            if not v or not v.get("n"):
                continue
            lines.append(f"| {name} | {c} | {v['n']} | " + " | ".join(_pct(v.get(f'recall@{k}')) for k in cutoffs)
                         + f" | {_pct(v.get('found_anywhere'))} |")
    return lines


def render_readout(ev: Mapping, frame_stats: Sequence[Mapping], *, doc_path: Path,
                   files: Optional[Mapping[str, Path]] = None, traits_dir: Path = TRAITS_DIR) -> str:
    """``readout.md``: what ``evaluate`` measured (module docstring)."""
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    cut = ev.get("cutoffs") or [500, 1000, 3000, 10000]
    rec = ev.get("recovery") or {}
    tc = ev.get("table_counts") or {}
    rule = ev.get("ordering_rule") or {}
    lines = [f"# Corpus-frames generator: {ev.get('title') or 'evaluation readout'}", "",
             f"Plan: {L(PLAN)}.  Terms: {L(GLOSSARY, 'glossary')}.  The table has **{ev.get('n_rows', 0):,}** rows "
             f"({ev.get('n_eligible', 0):,} eligible, {ev.get('n_net_new', 0):,} {_gl(d, 'net-new', 'net-new')}), one "
             f"per stem over every {_gl(d, 'lexical-frame', 'frame')}: forms {_cell(tc.get('forms'))}; sources "
             f"{_cell(tc.get('sources'))}; relabelled nouns {tc.get('relabelled', 0)} (rules "
             f"{_cell(tc.get('relabel_rules'))}), nouns left as nouns {tc.get('nouns_left', 0)}, British spellings "
             f"folded {tc.get('us_spelling_folds', 0)}.  Within each frame a filler is ranked by "
             f"{_gl(d, 'document-frequency', 'document frequency')} and by {_gl(d, 'lift', 'lift')}; the frames are "
             f"merged by {_gl(d, 'rrf', 'reciprocal-rank fusion')}.", "",
             f"**Ordering chosen: {ev.get('ordering')}** (the pre-registered rule: {rule.get('why')}).", ""]
    names = [n for n in ("union_volumes", "union_lift", "baseline_wordfreq", "baseline_table_zipf") if n in rec]
    lines += ["## Recovery of our labels", "",
              f"{_gl(d, 'recall-at-k', 'Recall@k')}: the share of the labels among the first k rows.  "
              "**union_volumes** / **union_lift**: the table's union under each ordering; **baseline_wordfreq**: "
              "OEWN's adjectives and person nouns by word frequency alone; **baseline_table_zipf**: the table's own "
              "words by frequency alone.  The frames earn their keep by beating the baselines at 1,000 (report and "
              "decide).", ""]
    for ls, title in (("corpus", "Corpus labels"), ("queue", "Seed-queue labels")):
        if any(ls in (rec.get(n) or {}) for n in names):
            lines += [f"### {title}", ""] + _recall_table(rec, names, ls, cut) + [""]
    per = rec.get("per_frame") or {}
    lines += ["## Per frame", "",
              "Fillers above the floor, their forms, the shares already registered and already corpus traits, and "
              "the frame's own recall of the corpus labels at 1,000 under each ordering; after the pilot, its "
              f"{_gl(d, 'frame-yield', 'yield')}, {_gl(d, 'net-filter', 'net filter')} and "
              f"{_gl(d, 'unique-contribution', 'unique kept rows')}, and the keep verdict.", "",
              "| frame | type | tier | source | template | fillers | above floor | forms | registered | corpus | "
              "recall@1,000 volumes / lift | yield | region_tv | unique kept | keep |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    fm = ev.get("frame_measures") or {}
    verdicts = ev.get("frame_verdicts") or {}
    for s in frame_stats:
        k = s["frame"]
        pr = per.get(k) or {}
        rv = ((pr.get("volumes") or {}).get("corpus") or {}).get("all", {}).get("recall@1000")
        rl = ((pr.get("lift") or {}).get("corpus") or {}).get("all", {}).get("recall@1000")
        m = fm.get(k) or {}
        v = verdicts.get(k)
        lines.append(f"| `{k}` | {s['type']} | {s['tier']} | {s['source']} | {_cell(s.get('template'))} | "
                     f"{s.get('fillers')} | {s.get('above_floor')} | {_cell(s.get('forms'))} | "
                     f"{_pct(s.get('registered_share'))} | {_pct(s.get('corpus_share'))} | {_pct(rv)} / {_pct(rl)} | "
                     f"{_pct(m.get('yield')) if m else '-'} | {_num(m.get('region_tv')) if m else '-'} | "
                     f"{m.get('unique_kept', '-') if m else '-'} | "
                     f"{('yes' if v[0] else 'no') + ': ' + _cell(v[1]) if v else '-'} |")
    lines.append("")
    un = ev.get("unfound_labels") or {}
    lines += ["## Corpus labels no frame finds", "",
              f"**{un.get('n', 0)}** of {un.get('n_labels', 0)} ({_pct(un.get('share'))}); by class "
              f"{_cell(un.get('by_class'))}.  By region (expected: concept phrases, alignment traits, memberships):",
              ""]
    for region, labs in (un.get("by_region") or {}).items():
        shown = labs[:40]
        lines.append(f"- **{region}** ({len(labs)}): " + ", ".join(
            _trait(normalize(lab), d, traits_dir, label=lab) for lab in shown) + (", ..." if len(labs) > 40 else ""))
    ov = ev.get("registry_overlap") or {}
    lines += ["", "## Registry overlap at depth", "",
              "The share of the first N eligible rows already in the registry (the proxy, the masked-LM table: "
              "80% / 63% / 41%): " + "; ".join(f"{k.replace('top_', 'top ')}: {_pct(v)}" for k, v in ov.items()
                                              if k.startswith("top_")) + ".", ""]
    if files:
        lines += ["## Files", ""] + [f"- {L(p)}: {what}" for what, p in files.items()] + [""]
    return "\n".join(lines)


def normalize(label: str) -> str:
    from assistant_axis.entity_id import normalize_to_file_name
    return normalize_to_file_name(label)


def _kept_records(registry_rows: Mapping[str, Mapping], run_id: str, table: Sequence[Mapping]) -> list[dict]:
    by_stem = {r["stem"]: r for r in table}
    by_surface = {r.get("surface_stem"): r for r in table if r.get("surface_stem")}
    out = []
    for r in run_rows(registry_rows, run_id):
        dec = (r.get("novelty") or {}).get("decision")
        if dec not in NOVEL:
            continue
        t = by_stem.get(r["stem"]) or by_surface.get(r["stem"])
        near, cos = _nearest(r)
        ex = None
        for k, v in sorted(((t or {}).get("frames") or {}).items()):
            if v.get("example"):
                ex = v["example"]
                break
        out.append({"stem": r["stem"], "label": r.get("label") or r["stem"], "decision": dec, "gloss": r.get("gloss"),
                    "nearest": near, "cosine": cos, "frames": contributing_frames([t])[t["stem"]] if t else [],
                    "example": ex, "union_rank": (t or {}).get("union_rank")})
    return out


def roger_sample(records: Sequence[Mapping], *, n: int = SAMPLE_N, seed: int = 0, doc_path: Path,
                 run_id: str = "", traits_dir: Path = TRAITS_DIR) -> str:
    """``n`` random kept rows (seeded) for Roger to mark **T** (a trait, and new), **N** (not a trait) or **D** (a
    duplicate of an existing trait); the workstream's precision spot check folds into it (plan section 8)."""
    d = Path(doc_path)
    pool = sorted(records, key=lambda r: r["stem"])
    pick = sorted(random.Random(seed).sample(pool, min(n, len(pool))), key=lambda r: (r.get("union_rank") or 0,
                                                                                     r["stem"]))
    lines = [f"# Spot check of corpus-frames run `{run_id}`: {len(pick)} random kept rows", "",
             f"Mark each row in the **T/N/D** column: **T** a trait and new, **N** not a trait, **D** a duplicate of "
             f"the nearest corpus trait (or another).  Rows are kept rows (M3 `new` or `grey`), drawn with seed "
             f"{seed}.  *M1's gloss* is the one the pipeline uses; *frames* are every "
             f"{_gl(d, 'lexical-frame', 'frame')} that found the word, best first.", "",
             "| # | word | T/N/D | M3 | M1's gloss | nearest corpus trait (cosine) | frames | example |",
             "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(pick, 1):
        near = (f"{_trait(r['nearest'], d, traits_dir)} ({r['cosine']:.2f})" if r.get("nearest") and
                r.get("cosine") is not None else "n/a")
        lines.append(f"| {i} | {_cell(r['label'])} |  | {r['decision']} | {_cell(r.get('gloss'))} | {near} | "
                     f"{', '.join('`' + f + '`' for f in r.get('frames') or [])} | {_cell(r.get('example'))} |")
    return "\n".join(lines) + "\n"


def roger_first_hour(records: Sequence[Mapping], *, n: int = FIRST_HOUR_N, doc_path: Path, run_id: str = "",
                     review_rate: float = 146.0, traits_dir: Path = TRAITS_DIR) -> str:
    """The ``n`` kept rows furthest from the corpus by M3's nearest cosine, ``new`` before ``grey`` (Roger,
    2026-10-13), for the first hour of review."""
    d = Path(doc_path)
    order = sorted(records, key=lambda r: (r["decision"] != "new", r["cosine"] if r.get("cosine") is not None
                                           else math.inf, r["stem"]))
    pick = order[:n]
    lines = [f"# Corpus-frames run `{run_id}`: the first hour of review", "",
             f"Roger, 2026-10-13: \"start with an hour's review of the ones that seem most novel\".  The {len(pick)} "
             f"kept rows (of {len(records)}) furthest from the corpus by M3's nearest cosine (lowest first), `new` "
             f"before `grey`; about {len(pick) / review_rate:.1f} h at {review_rate:.0f} terms an hour.  Mark **T** "
             f"(a trait, and new), **N** (not a trait) or **D** (a duplicate).", "",
             "| # | word | T/N/D | M3 | nearest corpus trait (cosine) | M1's gloss | frames |",
             "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(pick, 1):
        near = (f"{_trait(r['nearest'], d, traits_dir)} ({r['cosine']:.2f})" if r.get("nearest") and
                r.get("cosine") is not None else "n/a")
        lines.append(f"| {i} | {_cell(r['label'])} |  | {r['decision']} | {near} | {_cell(r.get('gloss'))} | "
                     f"{', '.join('`' + f + '`' for f in r.get('frames') or [])} |")
    return "\n".join(lines) + "\n"


def kept_records(registry_rows: Mapping[str, Mapping], run_id: str, table: Sequence[Mapping]) -> list[dict]:
    """The run's kept rows with what the two review sheets show (M3's nearest trait, the frames, an example)."""
    return _kept_records(registry_rows, run_id, table)


__all__ = ["GLOSSARY", "PLAN", "SAMPLE_N", "FIRST_HOUR_N", "contributing_frames", "run_rows", "net_novel",
           "submit_args", "figures", "render_report", "render_readout", "roger_sample", "roger_first_hour",
           "kept_records"]
