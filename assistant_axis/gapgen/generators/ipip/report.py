"""A run's ``evaluation.json``, ``report.md`` and ``roger_sample.md``, from files on disk (no calls).

:func:`build_evaluation` reads the cluster tables, the granularity readout, the naming records, the run directory,
the run's registry rows (with the platform's M1 and M3 blocks once those have run) and every ``usage.json``;
:func:`render_report` is the readout for Roger (plan § 10: the granularity distributions side by side, naming
statistics, census-word share, M1 / M3 fractions and measured per-pole cost, the projected full-run cost, and the
six decisions); :func:`roger_sample` lists 40 seeded poles with both labels, the gloss, the items, the M1 verdict and
the M3 decision.  Documents link every file relative to themselves and every trait named to its file.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.paths import DATA_CANDIDATES, REPO_ROOT, filter_dir, novelty_dir

from . import GENERATOR
from .cluster import item_embed_text
from .evaluate import (census_overlap, cost_summary, kind_against_m1, known_analogues, m1_m3_fractions,
                       naming_agreement, recovery_from_covers, sample_poles, useful_per_dollar)
from .submit import M1_PASS_RATE, M1_USD_PER_WORD, M3_USD_PER_PASSED_WORD, batch_id_for

GLOSSARY = REPO_ROOT / "reports" / "trait_gap_generation" / "glossary.md"
PLAN = REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_07_behaviour_items.md"


def _read_json(path: Path) -> Optional[dict]:
    p = Path(path)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) and "_provenance" in d else d


def _read_jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def naming_parse_stats(records: Sequence[Mapping], *, granularity: Optional[int] = None) -> dict:
    """Parse rate over every pole and form asked (the last answer per pole and form), the first-attempt rate, and
    the rejected answers by kind."""
    recs = [r for r in records if granularity is None or int(r["granularity"]) == int(granularity)]
    final: dict[tuple, Mapping] = {}
    first: dict[tuple, Mapping] = {}
    kinds = Counter()
    for r in recs:
        k = (r["granularity"], r["cluster_id"], r["pole"], r["form"])
        if r.get("parsed") or k not in final or not final[k].get("parsed"):
            final[k] = r
        if r.get("attempt") == 1:
            first[k] = r
        if r.get("parse_error"):
            kinds[r["parse_error"].split(":")[0]] += 1
    ok = sum(1 for r in final.values() if r.get("parsed"))
    return {"n_asked": len(final), "n_ok": ok, "parse_rate": round(ok / len(final), 4) if final else None,
            "first_attempt_ok": sum(1 for r in first.values() if r.get("parsed")), "n_calls": len(recs),
            "rejected_by_kind": dict(sorted(kinds.items())),
            "models": sorted({r.get("model") for r in recs}), "prompt_versions": sorted(
                {f"{r['form']} v{r.get('prompt_version')}" for r in recs})}


def build_evaluation(run_id: str, *, run_dir: Path, tables: Mapping[int, Sequence[Mapping]],
                     cluster_summaries: Mapping, readouts: Sequence[Mapping], naming_records: Sequence[Mapping],
                     registry_rows: Sequence[Mapping], ingest_counts: Optional[Mapping], corpus_stems: set,
                     census_stems: Optional[set], usage_paths: Mapping[str, Path],
                     candidates_dir: Path = DATA_CANDIDATES) -> dict:
    run = _read_json(run_dir / "run.json") or {}
    args = run.get("args") or {}
    g = args.get("granularity")
    sub = _read_json(run_dir / "submit_report.json") or {}
    cands = _read_jsonl(run_dir / "candidates.jsonl")
    rows_g = list(tables.get(int(g), [])) if g is not None else []
    label_choice = args.get("label_choice") or "blind"
    b = batch_id_for(run_id)
    paths = dict(usage_paths)
    paths.setdefault("run", run_dir / "usage.json")
    paths.setdefault("m1_filter", filter_dir(b, candidates_dir=candidates_dir) / "usage.json")
    paths.setdefault("m3_novelty", novelty_dir(b, candidates_dir=candidates_dir) / "usage.json")
    cost = cost_summary(paths)
    m1m3 = m1_m3_fractions(registry_rows)
    submitted_stems = sorted({normalize_to_file_name(c["surface"]) for c in cands})
    blind_stems = [p["blind"]["stem"] for r in rows_g if r.get("consensus") == "kept" for p in r["poles"]
                   if p.get("blind")]
    constructs = sorted({k.split(":", 1)[1] for r in rows_g for k in (r.get("constructs") or {})}) or sorted(
        {c for c in ((ingest_counts or {}).get("construct_labels") or [])})
    analogues = known_analogues(constructs, corpus_stems)
    downstream = cost["by_stage"].get("m1_filter", 0.0) + cost["by_stage"].get("m3_novelty", 0.0)
    n_kept_poles = sum(len(r["poles"]) for r in rows_g if r.get("consensus") == "kept")
    named_poles = sum(1 for r in rows_g if r.get("consensus") == "kept" for p in r["poles"] if p.get(label_choice))
    # every named pole is submitted (QUESTIONS 48), so the projection scales by the share that got a name
    trait_share = (named_poles / n_kept_poles) if n_kept_poles else None
    per_pole = (downstream / len(cands)) if cands and downstream else None
    naming_per_pole = None
    nstats = naming_parse_stats(naming_records, granularity=g)
    if nstats["n_asked"] and cost["by_stage"].get("naming"):
        naming_per_pole = cost["by_stage"]["naming"] / max(1, nstats["n_asked"])
    projected = None
    if trait_share is not None:
        n_full = round(n_kept_poles * trait_share)
        m1m3_rate = per_pole if per_pole is not None else (M1_USD_PER_WORD + M1_PASS_RATE * M3_USD_PER_PASSED_WORD)
        projected = {"n_kept_poles": n_kept_poles, "named_share_measured": round(trait_share, 4),
                     "n_poles_projected": n_full,
                     "naming_usd": round(n_kept_poles * 2 * (naming_per_pole or 0.0005), 2),
                     "m1_m3_usd": round(n_full * m1m3_rate, 2),
                     "rate_source": "measured on this run" if per_pole is not None else "the census rates (copied)"}
        projected["total_usd"] = round(projected["naming_usd"] + projected["m1_m3_usd"], 2)
    ev = {
        "run_id": run_id, "generator": GENERATOR, "granularity": g, "label_choice": label_choice,
        "ingest": {k: (ingest_counts or {}).get(k) for k in ("n_items", "n_codes", "n_with_scales", "n_constructs",
                                                              "hex", "hex_assertion", "unmatched_assignments")},
        "clusters": {str(k): v for k, v in cluster_summaries.items()},
        "granularity_readout": list(readouts),
        "naming": {"parse": {str(gr): naming_parse_stats(naming_records, granularity=gr) for gr in sorted(tables)},
                   "agreement": {str(gr): naming_agreement(tables[gr]) for gr in sorted(tables)},
                   "kind_vs_m1": kind_against_m1(rows_g, {r.get("stem"): r for r in registry_rows},
                                                 form=label_choice)},
        "census_overlap": census_overlap(blind_stems, census_stems) if census_stems is not None else None,
        "submitted": {"n_candidates": len(cands), "n_distinct": len(submitted_stems), "counts": args.get("counts"),
                      "registry": sub, "estimate": args.get("estimate")},
        "m1_m3": m1m3,
        "known_analogues": analogues,
        "recovery": {"exact": recovery_from_covers(registry_rows, analogues["exact"]),
                     "variant": recovery_from_covers(registry_rows, analogues["variant"])},
        "cost": cost,
        "per_pole_m1_m3_usd": round(per_pole, 5) if per_pole is not None else None,
        "projected_full_run": projected,
        "useful_per_dollar": useful_per_dollar(registry_rows, cost["total_usd"]),
    }
    return ev


# --------------------------------------------------------------------------- documents

def _link(target: Path, doc: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc).parent)
    return f"[{text or Path(target).name}]({rel.replace(os.sep, '/')})"


def _trait(stem: str, doc: Path) -> str:
    return _link(REPO_ROOT / "data" / "traits" / "instructions" / f"{stem}.json", doc, stem)


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def render_report(ev: Mapping, *, doc_path: Path, run_dir: Path, files: Mapping[str, Path]) -> str:
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    lines = [f"# IPIP generator: run `{ev['run_id']}`", "",
             f"Granularity ~{ev['granularity']}, labels submitted: {ev['label_choice']}.  Plan: {L(PLAN)}; terms: "
             f"{L(GLOSSARY, 'glossary')}.  **M1** is the platform's trait-hood filter, **M3** its novelty check "
             f"(covered / new / grey against the corpus and the seed queue); a **pole** is one side of a cluster "
             f"(two when the scale keys say the cluster is bipolar); **blind** labels were named from the statements "
             f"alone, **hinted** ones with the IPIP scale names.  Numbers: {L(run_dir / 'evaluation.json')}.", ""]
    ing = ev.get("ingest") or {}
    lines += ["## Items", "",
              f"{ing.get('n_items')} items ({ing.get('n_codes')} survey codes), {ing.get('n_with_scales')} scored on a "
              f"scale, {ing.get('n_constructs')} constructs; HEX block {json.dumps(ing.get('hex'))}, assertion "
              f"{ing.get('hex_assertion')}.", ""]
    lines += ["## Clusters", "", "| | " + " | ".join(f"~{g}" for g in ev["clusters"]) + " |",
              "|---|" + "---|" * len(ev["clusters"])]

    def row(label, f):
        lines.append(f"| {label} | " + " | ".join(f(s) for s in ev["clusters"].values()) + " |")
    row("clusters (primary arm)", lambda s: str(s["cut"][s["primary"]]["n_clusters"]))
    row("kept by both embedders / loose", lambda s: f"{s['consensus']['n_kept']} / {s['consensus']['n_loose']}")
    row("items in loose clusters", lambda s: str(s["consensus"]["loose_items"]))
    row("median Jaccard of kept", lambda s: str(s["consensus"]["jaccard_kept_median"]))
    row("bipolar (kept)", lambda s: str(s["bipolar"]["n_kept"]))
    row("poles (kept)", lambda s: str(s["n_poles_kept"]))
    row("NMI / ARI, primary", lambda s: f"{s['purity'][s['primary']]['nmi']} / {s['purity'][s['primary']]['ari']}")
    row("NMI / ARI, second", lambda s: f"{s['purity'][s['second']]['nmi']} / {s['purity'][s['second']]['ari']}")
    row("purity (kept, mean)", lambda s: str(s["purity"]["kept"]["purity_mean"]))
    row("HDBSCAN clusters / ARI vs cut", lambda s: (f"{s['hdbscan']['n_clusters']} / {s['hdbscan'].get('ari_vs_reference')}"
                                                     if s.get("hdbscan") else "n/a"))
    lines.append("")
    if ev.get("granularity_readout"):
        lines += ["## Granularity: decision (a)", "", "Within-pole item pairs read by M3's overlap call (rubric A, "
                  "Sonnet 5.5); Roger's criterion is the share at 3-4.  " + L(files["granularity_md"]) + ".", "",
                  "| | " + " | ".join(f"~{r['granularity']}" for r in ev["granularity_readout"]) + " |",
                  "|---|" + "---|" * len(ev["granularity_readout"])]
        for k in ("0", "1", "2", "3", "4", "opposite", "unsure", "share_3_4"):
            lines.append(f"| {k} | " + " | ".join(_pct(r["within"].get(k)) for r in ev["granularity_readout"]) + " |")
        lines.append("| cross-pole \"opposite\" | " + " | ".join(_pct(r["cross_pole"]["opposite"])
                                                               for r in ev["granularity_readout"]) + " |")
        lines.append("")
    lines += ["## Naming: decision (b)", "",
              "Every named pole is submitted; the `kind` guesses below are this call's, in M1's vocabulary, and "
              "gate nothing (QUESTIONS 48, Roger 2026-10-11).", ""]
    for gr, a in ev["naming"]["agreement"].items():
        p = ev["naming"]["parse"][gr]
        if not p["n_asked"]:
            lines.append(f"- ~{gr}: nothing named.")
            continue
        lines.append(f"- ~{gr}: {p['n_ok']} of {p['n_asked']} poles named ({_pct(p['parse_rate'])}, first attempt "
                     f"{p['first_attempt_ok']}; rejected {json.dumps(p['rejected_by_kind'])}); blind and hinted "
                     f"disagree on {_pct(a['disagree_rate'])} of {a['n_both_forms']}; bipolar antonym agreement "
                     f"{_pct(a['antonym_agreement'])} of {a['bipolar_directions']} directions (target 80%; "
                     f"{a['antonym_exact']} exact, {a['antonym_overlap']} sharing a word); kind guesses blind "
                     f"{json.dumps(a['kind']['blind'])}, hinted {json.dumps(a['kind']['hinted'])}; one word exists "
                     f"{_pct(a['single_word_exists'])}; ambiguity flag {_pct(a['ambiguity_flag'])}.")
    kvm = (ev["naming"].get("kind_vs_m1") or {})
    if kvm.get("n_pairs"):
        lines += ["", f"The naming call's kind guess against M1's verdict, over the {kvm['n_pairs']} submitted "
                  f"poles M1 has read ({_pct(kvm['agreement'])} agree on an approximate mapping; M1's is the "
                  f"verdict of record): " + ", ".join(f"{k} {v}" for k, v in kvm["cross"].items()) + "."]
    co = ev.get("census_overlap")
    lines += ["", f"Blind labels that are census words (TDA or Allport-Odbert): "
              + (f"{co['n_census']} of {co['n']} ({_pct(co['share'])})." if co else "census table not on disk."), ""]
    s = ev["submitted"]
    m = ev["m1_m3"]
    lines += ["## Submission, M1 and M3", "",
              f"{s['n_candidates']} candidates ({s['n_distinct']} distinct words) from {json.dumps(s['counts'])}.  "
              f"Registry: {json.dumps({k: s['registry'].get(k) for k in ('n_new', 'n_merged', 'n_unchanged')})}.", ""]
    if m["n_filtered"]:
        lines.append("M1 verdicts: " + ", ".join(f"{k} {v['n']} ({_pct(v['share'])})" for k, v in m["verdict"].items())
                     + ".  Outcomes: " + ", ".join(f"{k} {v['n']}" for k, v in m["outcome"].items()) + ".")
    else:
        lines.append("M1 not run on this run's rows yet.")
    if m["n_scored"]:
        lines.append("M3 decisions: " + ", ".join(f"{k} {v['n']} ({_pct(v['share'])})" for k, v in m["decision"].items())
                     + f"; pair completions {m['pair_completions']}; review flags {m['review_flags']}.")
    else:
        lines.append("M3 not run on this run's rows yet.")
    lines.append("")
    rec = ev["recovery"]
    ka = ev["known_analogues"]
    lines += ["## Known analogues (the covered_by inversion)", "",
              f"Corpus traits whose stem is an IPIP construct label: {len(ka['exact'])} exact ("
              + ", ".join(_trait(x, d) for x in ka["exact"]) + f"), {len(ka['variant'])} by derivation ("
              + ", ".join(_trait(x, d) for x in ka["variant"]) + ").  Recovered (some candidate covered by it): exact "
              f"{rec['exact']['n_hit']} of {rec['exact']['n_analogues']} ({_pct(rec['exact']['share'])}, target 90%), "
              f"by derivation {rec['variant']['n_hit']} of {rec['variant']['n_analogues']}.  Misses, to be read "
              "(pool blind spot or filter slip): " + (", ".join(_trait(x, d) for x in rec["exact"]["misses"] +
                                                               rec["variant"]["misses"]) or "none") + ".", ""]
    c = ev["cost"]
    lines += ["## Cost", "", "| stage | $ |", "|---|---|"] + [f"| {k} | {v:.4f} |" for k, v in c["by_stage"].items()]
    lines += [f"| **total** | **{c['total_usd']:.4f}** |", "", "Per model: " + ", ".join(
        f"{k} ${v:.4f}" for k, v in c["per_model"].items()) + ".  Per submitted pole, M1 and M3: "
        + (f"${ev['per_pole_m1_m3_usd']:.4f}" if ev.get("per_pole_m1_m3_usd") is not None else "not measured yet")
        + f" (the copied census rate: ${M1_USD_PER_WORD + M1_PASS_RATE * M3_USD_PER_PASSED_WORD:.4f}).", ""]
    u = ev["useful_per_dollar"]
    lines += [f"Useful per dollar: {u['useful']} rows decided new or pair completions over ${u['usd']:.2f} = "
              f"{u['per_dollar']}.", ""]
    pr = ev.get("projected_full_run")
    if pr:
        lines += [f"Projected full run at this granularity: {pr['n_kept_poles']} kept poles named in both forms "
                  f"(${pr['naming_usd']:.2f}), about {pr['n_poles_projected']} named poles to M1 and M3 "
                  f"(${pr['m1_m3_usd']:.2f}, rate {pr['rate_source']}); total about ${pr['total_usd']:.2f}.", ""]
    lines += ["## Decisions for Roger (plan § 10)", "",
              "(a) granularity, ~350 or ~150 (the share at 3-4 above, and the sampled clusters in the granularity "
              "readout); (b) the primary label, blind (recommended) or hinted ("
              + L(files["roger_sample"]) + " has both side by side); (c) **settled** - there is no is_trait gate "
              "at submit any more, every named pole goes to M1 (QUESTIONS 48); (d) the loose pile, held "
              "(provisional) or submitted; (e) the recovery harness (`recovery_test.py --generator ipip --run-id "
              "<R>`, about $5 a seed) beside the free inversion above; (f) the full-run go.", "", "## Files", ""]
    lines += [f"- {L(p)}" for p in files.values()] + [""]
    return "\n".join(lines)


def roger_sample(rows: Sequence[Mapping], registry_by_stem: Mapping[str, Mapping], items: Mapping, *, doc_path: Path,
                 n: int = 40, seed: int = 0) -> str:
    d = Path(doc_path)
    picks = sample_poles(rows, n, seed=seed)
    n_both = sum(1 for _, p in picks if p.get("hinted"))
    dis = sum(1 for _, p in picks if p.get("hinted") and p["hinted"]["stem"] != p["blind"]["stem"])
    lines = ["# IPIP generator: 40 poles for Roger's read", "",
             f"{len(picks)} poles drawn with seed {seed} from the named poles of kept clusters.  Blind labels were named "
             "from the statements alone, hinted ones with the IPIP scale names; they differ on "
             f"{dis} of the {n_both} poles named both ways.  M1 is the platform's trait-hood filter, M3 its novelty check.",
             "", "| # | pole | blind label | hinted label | blind gloss | statements | M1 | M3 (covered by) |",
             "|---|---|---|---|---|---|---|---|"]
    for k, (r, p) in enumerate(picks, 1):
        b, h = p["blind"], p.get("hinted") or {}
        reg = registry_by_stem.get(b["stem"]) or {}
        f, nv = reg.get("filter") or {}, reg.get("novelty") or {}
        cov = nv.get("covered_by")
        m3 = (nv.get("decision") or "") + (f" ({_trait(cov, d)})" if cov else "")
        stm = "; ".join(item_embed_text(items[i].text) for i in p["items"][:6]) + (
            f"; ... ({len(p['items'])} in all)" if len(p["items"]) > 6 else "")
        lines.append(f"| {k} | g{r['granularity']} c{int(r['cluster_id']):03d}{p['pole']} | **{b['label']}**"
                     + (f" ({b['kind']})" if b.get("kind") and b["kind"] != "trait" else "")
                     + f" | {h.get('label', '')} | {b['gloss']} | "
                     f"{stm} | {f.get('verdict') or ''} | {m3 or ''} |")
    return "\n".join(lines) + "\n"
