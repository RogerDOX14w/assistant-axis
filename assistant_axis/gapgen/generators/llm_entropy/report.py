"""The readouts of a run, no API (plan sections 7, 10 and 11, ``report.py``; tasks 6, 7 and 9).

:func:`figures` gathers what ``report.md`` prints, led by **the already-registered share** (how many of the run's
unique stems the registry already holds, by any generator, and how many of those M1 and M3 had already decided),
then per (family, model) cell the model-test figures (:func:`.evaluate.model_test`), the **novel figure twice** (M3
``new`` or ``grey``, raw and net of other generators' pending candidates of the same stem), the **net-new kept
share** (it replaces the 0.35 assumption in the wave's selector), cost per model from every ``usage.json`` (the run,
its M1 and M3 batches, the translations), ``useful_per_dollar`` (rows decided ``new`` or read as a pair completion,
per dollar), the (d) readout, the roles summary, and the wave projections re-based on the measured share.

:func:`roger_sample` draws 50 rows per family decided ``new`` or ``grey`` (seeded) for Roger's verdicts;
:func:`gloss_check_sample` 30 items per family and model arm (label, gloss, the original form for family c) for the
gloss-fidelity read; :func:`roles_report` lists the rows held on the ``roles`` list or guessed ``role`` by most of
their readings, with the free string check against the role corpus and the seed queue's role entries (decision 1:
the input to the later role-promotion work; nothing is promoted here).  Family (b)'s rows carry opaque seed ids and
redacted glosses only (section 5a).

Links in the markdown are relative to where each file is written: ``data/candidates/runs/llm_entropy/<run>/`` for
the run's readouts, ``data/candidates/llm_entropy/`` for the roles report.
"""
from __future__ import annotations

import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..masked_lm.evaluate import _m1, _m3, cost_summary
from ..structural.report import _nearest_text, net_novel, submit_args
from . import GENERATOR
from .calls import model_tag, parse_rate
from .evaluate import (KEPT_DECISIONS, c_model_rule, label_rule_bite, model_test, roles_summary, run_rows,
                       verbalized_readout, zipf_below_share)
from .prompts import FAMILIES, FAMILY_NAMES
from .submit import KEPT_SHARE_ASSUMED, KEPT_TARGET_DEFAULT, REVIEW_TERMS_PER_HOUR, estimate_downstream_usd

RUN_TRAIT_PREFIX = "../../../../traits/instructions/"
RUN_GLOSSARY = "../../../../../reports/trait_gap_generation/glossary.md"
RUN_PLAN = "../../../../../reports/trait_gap_generation/coding_plan_06_llm_entropy.md"


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _cell(s) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ")


def _decision(r: Mapping) -> Optional[str]:
    return (r.get("novelty") or {}).get("decision")


def _row_families(row: Mapping, run_id: str) -> list[str]:
    from .table import parse_source_ref
    fams = []
    for s in row.get("sources") or []:
        if s.get("generator") == GENERATOR and s.get("run_id") == run_id:
            try:
                f = parse_source_ref(s.get("source_ref") or "")["family"]
            except ValueError:
                continue
            if f not in fams:
                fams.append(f)
    return fams


def figures(run_id: str, *, run_dir: Path, registry_rows: Mapping[str, Mapping], table: Sequence[Mapping],
            items: Sequence, records: Sequence[Mapping], collapse: Optional[Mapping] = None,
            filter_dir: Optional[Path] = None, novelty_dir: Optional[Path] = None,
            extra_usage: Sequence[Path] = ()) -> dict:
    """Every figure ``report.md`` prints (module docstring)."""
    from .collapse import family_costs
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8")) if (run_dir / "run.json").exists() else {}
    args = submit_args(run)
    rows = run_rows(registry_rows, run_id)
    run_stems = {it.stem for it in items if it.stem}
    tab = [r for r in table if r["stem"] in run_stems] if run_stems else list(table)
    reg = [r for r in tab if r.get("registered")]
    headline = {"n_unique_stems": len(tab), "already_registered": len(reg),
                "already_registered_share": _frac(len(reg), len(tab)),
                "already_decided": sum(1 for r in reg if r.get("registered_decided")),
                "already_decided_share_of_registered": _frac(sum(1 for r in reg if r.get("registered_decided")),
                                                             len(reg)),
                "single_word_registered_share": _frac(sum(1 for r in reg if "_" not in r["stem"]),
                                                      sum(1 for r in tab if "_" not in r["stem"])),
                "phrase_registered_share": _frac(sum(1 for r in reg if "_" in r["stem"]),
                                                 sum(1 for r in tab if "_" in r["stem"])),
                "exists": sum(1 for r in tab if r.get("exists")), "queued": sum(1 for r in tab if r.get("queued")),
                "net_new": sum(1 for r in tab if r.get("net_new")),
                "submitted_rows": len(rows), "submitted_net_new": len(args.get("counted_stems") or [])}
    counted = set(args.get("counted_stems") or [])
    counted_rows = [r for r in rows if r.get("stem") in counted]
    kept_counted = sum(1 for r in counted_rows if _decision(r) in KEPT_DECISIONS)
    scored = sum(1 for r in counted_rows if r.get("novelty"))
    share = _frac(kept_counted, len(counted_rows)) if scored else None
    m1, m3 = _m1(rows), _m3(rows)
    novel = net_novel(rows, registry_rows, generator=GENERATOR)
    novel_counted = net_novel(counted_rows, registry_rows, generator=GENERATOR)
    batch = f"{run_id}_{GENERATOR}"
    fdir = Path(filter_dir) if filter_dir else run_dir.parents[2] / "filter" / batch
    ndir = Path(novelty_dir) if novelty_dir else run_dir.parents[2] / "novelty" / batch
    usage_p = run_dir / "usage.json"
    gen_total = json.loads(usage_p.read_text(encoding="utf-8")).get("total_cost_usd") if usage_p.exists() else None
    costs = (collapse or {}).get("costs") or family_costs(records, gen_total)
    cost = cost_summary([usage_p, *[Path(p) for p in extra_usage], fdir / "usage.json", ndir / "usage.json"])
    cells = model_test(items, registry_rows=registry_rows, run_id=run_id, records=records,
                       costs=costs.get("by_family_model") or {}, counted_stems=sorted(counted))
    per_family_novel = {}
    for f in FAMILIES:
        fr = [r for r in rows if f in _row_families(r, run_id)]
        if not fr:
            continue
        nf = net_novel(fr, registry_rows, generator=GENERATOR)
        per_family_novel[f] = {"n": len(fr), "m1_trait_share": _m1(fr)["pass_rate"], "novel_raw": nf.raw,
                               "novel_net": nf.net_pending}
    useful = m3["decision"].get("new", 0) + m3["pair_completions"]
    proj = None
    if share:
        need = math.ceil(KEPT_TARGET_DEFAULT / share)
        ratio = len(rows) / len(counted) if counted else 1.0
        n_sub = int(round(need * ratio))
        table_net = sum(1 for r in table if r.get("net_new") and not r.get("label_problem"))
        proj = {"kept_share": share,
                "wave_300": {"net_new_rows": need, "rows_to_submit": n_sub, "kept_rows": KEPT_TARGET_DEFAULT,
                             "novel_raw": round(need * novel_counted.raw / len(counted_rows)),
                             "novel_net": round(need * novel_counted.net_pending / len(counted_rows)),
                             "review_hours": round(KEPT_TARGET_DEFAULT / REVIEW_TERMS_PER_HOUR, 2),
                             "estimate_batches": estimate_downstream_usd(n_sub, transport="batches").total_usd},
                "whole_table": {"rows": len(table), "net_new_rows": table_net, "kept_rows": round(table_net * share),
                                "review_hours": round(table_net * share / REVIEW_TERMS_PER_HOUR, 2),
                                "estimate_batches": estimate_downstream_usd(
                                    sum(1 for r in table if not r.get("registered_decided")
                                        and not r.get("label_problem")), transport="batches").total_usd}}
    pr = {f: parse_rate([r for r in records if r.get("family") == f
                         and (r.get("step") or "generate") in ("generate", "verbalized")]) for f in FAMILIES
          if any(r.get("family") == f for r in records)}
    return {"run_id": run_id, "generator": GENERATOR, "args": {k: v for k, v in args.items() if not k.endswith("_stems")},
            "headline": headline, "m1": m1, "m3": {k: v for k, v in m3.items() if not k.endswith("_stems")},
            "net_new_kept_share": share, "net_new_kept_share_assumed": KEPT_SHARE_ASSUMED, "kept_net_new": kept_counted,
            "novel": {"raw": novel.raw, "net": novel.net_pending, "twins_pending": len(novel.twins_pending),
                      "twins_reviewed": len(novel.twins_reviewed)},
            "per_family": per_family_novel, "model_test": cells, "c_model_rule": c_model_rule(cells),
            "verbalized": verbalized_readout(items, registry_rows=registry_rows),
            "roles": roles_summary(tab, registry_rows=registry_rows), "cost": cost, "generation_costs": costs,
            "useful": useful, "useful_per_dollar": round(useful / cost["total_usd"], 1) if cost["total_usd"] else None,
            "projection": proj, "parse_rate": pr, "label_rule_bite": label_rule_bite(items),
            "zipf_below_3": zipf_below_share(items),
            "collapse": {f: {k: d.get(k) for k in ("n_calls", "n_unique_string", "n_unique_semantic", "jaccard_median",
                                                   "jaccard_p90", "lincoln_petersen_N", "seen_over_N",
                                                   "end_slope_per_call", "unique_per_usd")}
                         for f, d in ((collapse or {}).get("per_family") or {}).items()}}


def render_report(fig: Mapping) -> str:
    h = fig["headline"]
    L = [f"# LLM-entropy generator, run `{fig['run_id']}`", "",
         f"The readout of [coding_plan_06_llm_entropy.md]({RUN_PLAN}) sections 10 and 11, built from the registry, "
         f"the run's records and every `usage.json`.  Terms: [glossary]({RUN_GLOSSARY}) (label-set Jaccard, "
         f"Lincoln-Petersen, net-new row, net-new kept share).  Files beside this one: [roger_sample.md]"
         f"(./roger_sample.md), [gloss_check.md](./gloss_check.md), [run.json](./run.json), "
         f"[usage.json](./usage.json), [responses.jsonl](./responses.jsonl).", "",
         "## Already registered (the headline)", "",
         f"Of the run's **{h['n_unique_stems']}** unique stems, **{h['already_registered']}** "
         f"({_pct(h['already_registered_share'])}) are already in the registry by some generator, and "
         f"{h['already_decided']} of those ({_pct(h['already_decided_share_of_registered'])}) were already decided "
         f"by M1 and M3.  Single words registered: {_pct(h['single_word_registered_share'])}; phrases: "
         f"{_pct(h['phrase_registered_share'])}.  Corpus traits {h['exists']}, queued {h['queued']}, net-new "
         f"{h['net_new']}.  Submitted: {h['submitted_rows']} rows, {h['submitted_net_new']} of them net-new.", "",
         "## M1, M3 and the novel figure", "",
         f"M1 judged {fig['m1']['n_filtered']} of {fig['m1']['n_rows']} submitted rows; trait share "
         f"{_pct(fig['m1']['pass_rate'])}.  M3 scored {fig['m3']['n_scored']}: {fig['m3']['decision']}.",
         f"Novel (M3 `new` or `grey`): **raw {fig['novel']['raw']}, net {fig['novel']['net']}** (net of other "
         f"generators' candidates of the same stem: {fig['novel']['twins_pending']} pending, "
         f"{fig['novel']['twins_reviewed']} reviewed).  Net-new kept share: **{_pct(fig['net_new_kept_share'])}** "
         f"({fig['kept_net_new']} kept; the wave assumed {_pct(fig['net_new_kept_share_assumed'])} before the pilot).",
         ""]
    if fig.get("per_family"):
        L += ["| family | rows | M1 trait share | novel raw | novel net |", "|---|---|---|---|---|"]
        for f, d in fig["per_family"].items():
            L.append(f"| {f} ({FAMILY_NAMES.get(f, f)}) | {d['n']} | {_pct(d['m1_trait_share'])} | {d['novel_raw']} | "
                     f"{d['novel_net']} |")
        L.append("")
    L += ["## The model test and the cells", "",
          "| cell | items | unique | semantic | cost | unique/$ | M1 trait | net-new | kept | kept share | kept/$ | "
          "label rule | parse |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in fig["model_test"].items():
        cost_txt = "n/a" if c["cost_usd"] is None else f"${c['cost_usd']:.3f}"
        sem_txt = "n/a" if c["n_unique_semantic"] is None else c["n_unique_semantic"]
        L.append(f"| {c['family']} x {model_tag(c['model'])} | {c['n_items']} | {c['n_unique_string']} | "
                 f"{sem_txt} | {cost_txt} | "
                 f"{c['unique_per_usd_string']} | {_pct(c['m1_trait_share'])} | {c['n_submitted_net_new']} | "
                 f"{c['n_kept_net_new']} | {_pct(c['net_new_kept_share'])} | {c['net_new_kept_per_usd']} | "
                 f"{_pct(c['label_rule_bite'])} | {_pct(c['parse_rate'])} |")
    rule = fig["c_model_rule"]
    L += ["", f"The rest of (c) by the section 10 rule: **{rule['favoured'] or 'not decidable yet'}** "
              f"(net-new kept rows per dollar {rule['net_new_kept_per_usd']}; {rule['note'] or ''}).  Roger's 30-gloss "
              f"read per arm can overrule it.", "", "## Verbalized sampling (d)", ""]
    for fam, v in fig["verbalized"].items():
        L.append(f"- {fam}: {v['n_prompts']} prompts; stage 1 unique {v['stage1_unique']}, stage 2 added "
                 f"{v['stage2_added']} ({_pct(v['added_share'])}); M1 reject {_pct(v['m1_reject_stage1'])} stage 1 "
                 f"against {_pct(v['m1_reject_added'])} added; adopt by the rule: {v['adopt_by_rule']}")
    L += ["", "## Collapse (from collapse.json)", "",
          "| family | calls | unique | semantic | Jaccard median | p90 | L-P N | seen/N | end slope | unique/$ |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for f, d in fig["collapse"].items():
        L.append(f"| {f} | {d['n_calls']} | {d['n_unique_string']} | {d['n_unique_semantic']} | {d['jaccard_median']} "
                 f"| {d['jaccard_p90']} | {d['lincoln_petersen_N']} | {d['seen_over_N']} | {d['end_slope_per_call']} "
                 f"| {d['unique_per_usd']} |")
    L += ["", "## Parse rates, the label rule and Zipf", ""]
    for f, p in fig["parse_rate"].items():
        b = fig["label_rule_bite"].get(f) or {}
        z = fig["zipf_below_3"].get(f) or {}
        L.append(f"- {f}: parse {p['n_ok']} of {p['n_units']} ({_pct(p['rate'])}); label rule refused "
                 f"{b.get('n_refused')} of {b.get('n_items')} items {b.get('by_reason')}; single words below Zipf 3: "
                 f"{_pct(z.get('share_below'))}")
    r = fig["roles"]
    L += ["", "## Roles (decision 1: held, not promoted)", "",
          f"{r['n_held_roles']} rows held on the `roles` list by M1; {r['n_majority_role_kind']} guessed `role` by most "
          f"of their readings; {r['n_both']} both.  See [roles_report.md](../../../llm_entropy/roles_report.md).", "",
          "## Cost", ""]
    for m, c in fig["cost"]["per_model"].items():
        L.append(f"- {m}: ${c['cost_usd']:.4f} ({c['n_calls']} calls)")
    L.append(f"- **total ${fig['cost']['total_usd']:.4f}**; useful rows (new, or read as a pair completion) "
             f"{fig['useful']}, {fig['useful_per_dollar']} per dollar")
    p = fig.get("projection")
    L += ["", "## Projections, re-based on the measured share", ""]
    if p:
        w, t = p["wave_300"], p["whole_table"]
        L += [f"- the 300-kept wave: {w['net_new_rows']} net-new rows, about {w['rows_to_submit']} rows to submit, "
              f"novel raw {w['novel_raw']} / net {w['novel_net']}, {w['review_hours']} h of review, about "
              f"${w['estimate_batches']:.2f} batched",
              f"- the whole table: {t['net_new_rows']} net-new rows, about {t['kept_rows']} kept, {t['review_hours']} h "
              f"of review, about ${t['estimate_batches']:.2f} batched"]
    else:
        L.append("Not yet: needs the submission scored by M3.")
    return "\n".join(L) + "\n"


def roger_sample(rows: Sequence[Mapping], table: Sequence[Mapping], *, run_id: str, n: int = 50, seed: int = 0,
                 trait_prefix: str = RUN_TRAIT_PREFIX) -> str:
    """Up to ``n`` rows per family decided ``new`` or ``grey`` (seeded), for Roger's verdicts."""
    by = {r["stem"]: r for r in table}
    L = [f"# Precision sample, LLM-entropy run `{run_id}`", "",
         f"Up to {n} rows per family (seed {seed}) the scorer decided `new` or `grey`.  Mark each **trait** (a new "
         f"persona trait), **not-trait** or **duplicate** (of a corpus or queued trait) in the second column; the target "
         f"is 70% or more trait-and-new (plan 09 section 6.4).  *Nearest existing traits*: the first three corpus "
         f"traits M3 compared the candidate with, with M3's reading (4 the same concept, 3 narrower or broader, 2 "
         f"overlapping, 1 related, 0 different).  *M1's gloss* is the one the pipeline uses (M3, grouping, review); "
         f"*the generator's gloss* is what the model meant when it named the item, for reference.  Family (b)'s "
         f"persons appear by opaque id only.", ""]
    for f in FAMILIES:
        pool = sorted((r for r in rows if _decision(r) in KEPT_DECISIONS and f in _row_families(r, run_id)),
                      key=lambda r: r["key"])
        if not pool:
            continue
        pick = sorted(random.Random(f"llm_entropy-sample:{seed}:{f}").sample(pool, min(n, len(pool))),
                      key=lambda r: r["key"])
        L += [f"## Family {f} ({FAMILY_NAMES[f]}): {len(pick)} of {len(pool)}", "",
              "| # | mark | label | M1's gloss | the generator's gloss | nearest existing traits (M3's reading) | M1 | M3 "
              "| prompts |",
              "|---|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(pick, 1):
            t = by.get(r["stem"]) or {}
            near, _ = _nearest_text(r, trait_prefix)
            prompts = ", ".join(sorted({s["prompt_id"] for s in t.get("sources") or [] if s["family"] == f})[:3])
            L.append(f"| {i} |  | {_cell(r.get('label'))} | {_cell(r.get('gloss'))} | {_cell(t.get('gloss'))} | {near} | "
                     f"{_cell((r.get('filter') or {}).get('verdict'))} | {_cell(_decision(r))} | {_cell(prompts)} |")
        L.append("")
    return "\n".join(L) + "\n"


def gloss_check_sample(table: Sequence[Mapping], *, run_id: str, n: int = 30, seed: int = 0) -> str:
    """Up to ``n`` items per family and model arm, for the gloss-fidelity read: does the gloss match the label's
    intended sense, and would the label be polysemous without it?"""
    srcs: dict[tuple, list] = {}
    for r in table:
        for s in r.get("sources") or []:
            srcs.setdefault((s["family"], s["model"]), []).append((r, s))
    L = [f"# Gloss-fidelity check, LLM-entropy run `{run_id}`", "",
         f"Up to {n} items per family and model arm (seed {seed}).  For each: does the gloss describe the label's "
         f"intended sense, and would the label be read otherwise without it?  The gloss is the generator's own.  Mark "
         f"(second column) **ok**, **wrong** (the gloss does "
         f"not fit the label) or **polysemous** (it fits, but the label alone reads otherwise).  Family (c) shows the "
         f"original label and its romanisation; the English label and gloss are the back-translation's.", ""]
    for (f, m) in sorted(srcs, key=lambda k: (FAMILIES.index(k[0]) if k[0] in FAMILIES else 9, k[1])):
        pool = sorted(srcs[(f, m)], key=lambda rs: (rs[0]["stem"], rs[1]["prompt_id"], rs[1]["run"]))
        pick = random.Random(f"llm_entropy-gloss:{seed}:{f}:{m}").sample(pool, min(n, len(pool)))
        L += [f"## Family {f} ({FAMILY_NAMES.get(f, f)}) on {m}: {len(pick)} of {len(pool)}", "",
              "| # | mark | label | the generator's gloss | original (c) | prompt |", "|---|---|---|---|---|---|"]
        for i, (r, s) in enumerate(sorted(pick, key=lambda rs: (rs[0]["stem"], rs[1]["prompt_id"])), 1):
            orig = f"{s.get('raw')} ({', '.join(r.get('backtranslated_from') or [])})" if f == "c" else ""
            L.append(f"| {i} |  | {_cell(s.get('label') or r['label'])} | {_cell(s.get('gloss'))} | {_cell(orig)} | "
                     f"{_cell(s['prompt_id'])} |")
        L.append("")
    return "\n".join(L) + "\n"


def roles_report(table: Sequence[Mapping], *, registry_rows: Mapping[str, Mapping], role_stems: Sequence[str],
                 role_queue: Mapping[str, str], run_id: Optional[str] = None,
                 role_prefix: str = "../../roles/instructions/") -> str:
    """The rows held as ``roles`` or guessed ``role`` by most readings (module docstring), with the free string check
    against the role corpus and the queue's role entries, the prompts (opaque seed ids for family b) and the gloss."""
    reg = {r.get("stem"): r for r in registry_rows.values() if int(r.get("sense_id") or 1) == 1}
    roles = set(role_stems)
    L = ["# LLM-entropy generator: role-like rows" + (f" (run `{run_id}`)" if run_id else ""), "",
         "Rows M1 held on the `roles` list, or whose generator `kind` guess was `role` in most readings.  Decision 1 "
         "(Roger, 2026-10-14): they wait here; role promotion is built with the role generators "
         "([16_role_generators.md](../../../reports/trait_gap_generation/16_role_generators.md)).  *Role corpus* "
         "and *queue* are a free string check of the stem.", "",
         "| label | gloss | held by M1 | kind guesses | role corpus | queue (role entry) | prompts |",
         "|---|---|---|---|---|---|---|"]
    n = 0
    for row in sorted(table, key=lambda r: r["rank"]):
        r = reg.get(row["stem"]) or {}
        if run_id and not any(s.get("generator") == GENERATOR and s.get("run_id") == run_id
                              for s in r.get("sources") or []):
            continue
        kinds = row.get("kinds") or {}
        held = r.get("holding") == "roles"
        major = bool(kinds) and kinds.get("role", 0) * 2 > sum(kinds.values())
        if not (held or major):
            continue
        n += 1
        st = row["stem"]
        corpus = f"[{st}]({role_prefix}{st}.json)" if st in roles else ""
        prompts = ", ".join(sorted({s["prompt_id"] for s in row.get("sources") or []})[:4])
        L.append(f"| {_cell(row['label'])} | {_cell(row.get('gloss'))} | {'yes' if held else ''} | "
                 f"{_cell(dict(kinds))} | {corpus} | {_cell(role_queue.get(st) or '')} | {_cell(prompts)} |")
    L += ["", f"{n} rows."]
    return "\n".join(L) + "\n"


def role_queue_index(queue_path: Path) -> dict[str, str]:
    """``{stem: status}`` of the seed queue's role entries, by stem and normalised label."""
    from assistant_axis.entity_id import normalize_to_file_name
    p = Path(queue_path)
    if not p.exists():
        return {}
    q = json.loads(p.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in (q.get("entries") if isinstance(q, dict) else q) or []:
        if e.get("entity_type") != "role":
            continue
        for k in ("stem", "label"):
            if e.get(k):
                out.setdefault(normalize_to_file_name(e[k]), str(e.get("status")))
    return out


__all__ = ["figures", "render_report", "roger_sample", "gloss_check_sample", "roles_report", "role_queue_index",
           "net_novel"]
