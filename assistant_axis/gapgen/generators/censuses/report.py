"""A run's evaluation (``evaluation.json``) and readout (``readout.md``).

Everything here is counted from files already on disk: the census table and its
``ingest_counts.json``, the run directory (``candidates.jsonl``, ``run.json``,
``submit_report.json``), the registry log and, once the platform has run, the filter and novelty
blocks on the run's rows and their batches' ``usage.json``.  No calls.  The readout is a document
for Roger: every file is linked relative to the document, every trait named is linked to its
file, and terms are defined on first use.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen.paths import DATA_CANDIDATES, REPO_ROOT, filter_dir, novelty_dir

from . import GENERATOR
from .evaluate import cost_summary, known_label_pass, run_rows, state_gloss_compliance
from .ingest import TableRow
from .submit import batch_id_for


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) and "_provenance" in d else d


def evaluate_run(run_id: str, *, run_dir: Path, table: Sequence[TableRow], ingest_counts: Optional[Mapping],
                 registry_rows: Mapping[str, Mapping], corpus_stems: set[str],
                 candidates_dir: Path = DATA_CANDIDATES) -> dict:
    cands = _read_jsonl(run_dir / "candidates.jsonl")
    run = _read_json(run_dir / "run.json") or {}
    args = run.get("args") or {}
    sub = _read_json(run_dir / "submit_report.json") or {}
    by_rank = {r.rank: r for r in table}
    stage = args.get("stage")
    rows_sel = [by_rank[c["rank"]] for c in cands if c.get("rank") in by_rank and stage != "extra"]
    tda_rows = [r for r in table if r.tda and r.stem]
    allport_only = [r for r in table if r.allport and not r.tda and r.stem]
    reg_rows = run_rows(registry_rows, GENERATOR, run_id)
    known_sub = sorted({r.stem for r in rows_sel if r.stem in corpus_stems})
    filt = [r for r in reg_rows if r.get("filter")]
    nov = [r for r in reg_rows if r.get("novelty")]
    b = batch_id_for(run_id)
    cost = cost_summary([run_dir / "usage.json", filter_dir(b, candidates_dir=candidates_dir) / "usage.json",
                         novelty_dir(b, candidates_dir=candidates_dir) / "usage.json"])
    counters = (ingest_counts or {}).get("counters") or {}
    ev = {
        "run_id": run_id, "generator": GENERATOR, "stage": stage, "every_nth": args.get("every_nth"),
        "offset": args.get("offset"), "transport": args.get("transport"), "estimate": args.get("estimate"),
        "parsed": {
            "table_rows": len(table), "tda_words": len(tda_rows), "allport_words": sum(1 for r in table if r.allport and r.stem),
            "allport_only_words": len(allport_only), "in_both": sum(1 for r in tda_rows if r.allport),
            "allport_lines": {c: counters.get(f"allport_lines_{c}") for c in ("I", "II", "III", "IV")},
            "malformed": sum(1 for r in table if r.ineligible_reason == "malformed"),
        },
        "floor": {
            "stage_pool": args.get("n_stage"),
            "tda_cut": 0,
            "tda_below_dictionary_floor": sum(1 for r in tda_rows if r.freq_hard_reject),
            "allport_only_cut": dict(sorted(Counter(r.ineligible_reason for r in allport_only if not r.eligible).items())),
            "allport_only_eligible": dict(sorted(Counter(r.stage for r in allport_only if r.eligible).items())),
            "submitted_to_probe": sum(1 for r in rows_sel if (r.freq_platform or {}).get("probe")),
            "submitted_probe_routes": dict(sorted(Counter((r.freq_platform or {}).get("rescue") or "band"
                                                          for r in rows_sel
                                                          if (r.freq_platform or {}).get("probe")).items())),
        },
        "submitted": {
            "n_candidates": len(cands), "n_with_gloss_hint": sum(1 for c in cands if c.get("gloss_hint")),
            "n_state_prefix": sum(1 for c in cands if (c.get("gloss_hint") or "").startswith("disposition to be ")),
            "registry": sub,
        },
        "merges": {
            "allport_cross_column": counters.get("allport_cross_column_merges"),
            "allport_within_column": counters.get("allport_within_column_duplicates"),
            "tda_and_allport": sum(1 for r in tda_rows if r.allport),
            "tda_multi_row": counters.get("tda_rows_merged_extra"),
            "repaired": counters.get("n_repaired"),
            "submit_n_merged": sub.get("n_merged"), "submit_n_unchanged": sub.get("n_unchanged"),
        },
        "known_labels": {"n": len(known_sub), "stems": known_sub},
        "ceiling": (ingest_counts or {}).get("ceiling"),
        "filter": None, "novelty": None,
        "cost": cost,
    }
    if filt:
        kp = known_label_pass(reg_rows, corpus_stems)
        ev["filter"] = {
            "n_filtered": len(filt), "n_rows": len(reg_rows),
            "verdict": dict(sorted(Counter(r["filter"].get("verdict") for r in filt).items())),
            "outcome": dict(sorted(Counter(r["filter"].get("outcome") for r in filt).items())),
            "tags": dict(sorted(Counter(t for r in filt for t in (r["filter"].get("tags") or [])).items())),
            "known_label_pass": kp.as_dict(),
            "state_gloss_compliance": state_gloss_compliance(filt),
        }
    if nov:
        ev["novelty"] = {
            "n_scored": len(nov),
            "decision": dict(sorted(Counter(r["novelty"].get("decision") for r in nov).items())),
            "pair_completion": sum(1 for r in nov if r["novelty"].get("pair_completion_for")),
        }
    return ev


# ---------------------------------------------------------------------------
# Readout
# ---------------------------------------------------------------------------

def _link(target: Path, doc: Path, text: Optional[str] = None) -> str:
    rel = os.path.relpath(Path(target), Path(doc).parent)
    return f"[{text or Path(target).name}]({rel.replace(os.sep, '/')})"


def _trait(stem: str, doc: Path) -> str:
    return _link(REPO_ROOT / "data" / "traits" / "instructions" / f"{stem}.json", doc, stem)


def render_readout(ev: Mapping, *, doc_path: Path, run_dir: Path, table_path: Path, counts_path: Path,
                   manifest_path: Path) -> str:
    d = Path(doc_path)
    L = lambda p, t=None: _link(p, d, t)  # noqa: E731
    plan = REPO_ROOT / "reports" / "trait_gap_generation" / "coding_plan_01_censuses.md"
    gloss = REPO_ROOT / "reports" / "trait_gap_generation" / "glossary.md"
    cli = L(REPO_ROOT / "data_analysis" / "gap_generation" / "census_generator.py")
    reg_cli = L(REPO_ROOT / "data_analysis" / "gap_generation" / "gap_registry.py")
    freq = L(REPO_ROOT / "assistant_axis" / "gapgen" / "freq.py", "gapgen/freq.py")
    p, f, s, m = ev["parsed"], ev["floor"], ev["submitted"], ev["merges"]
    reg = s.get("registry") or {}
    est = ev.get("estimate") or {}
    lines = [
        f"# Census generator: run `{ev['run_id']}` readout",
        "",
        f"Stage `{ev['stage']}`" + (f", every {ev['every_nth']}th row in rank order (offset {ev['offset']})"
                                     if ev.get("every_nth") else "") + ".  Plan: " + L(plan) + " (its last section, "
        "the revision for the interface as built, governs).  Terms: " + L(gloss, "glossary") + ".  Written by "
        + cli + " `report`; the numbers are in " + L(run_dir / "evaluation.json") + ".",
        "",
        "Definitions used below.  **TDA**: the Trait Descriptive Adjectives list (2,818 words with, for "
        "each, `prop`, the proportion of raters who knew the word; Dataverse, CC0).  **Allport-Odbert**: the "
        "1936 list of about 18,000 person words in four columns (I traits, II temporary states, III social "
        "evaluations, IV metaphorical or doubtful; OSF transcription, CC BY 4.0).  **Zipf**: log10 of a "
        "word's frequency per billion words (`wordfreq`).  **The floor**: the platform's hard-reject line "
        "below Zipf 1.5 for a dictionary word, with a definition probe from 1.5 to 2.5 (" + freq + "); a "
        "curated generator such as this one is never hard-rejected by the platform, its rare words go to "
        "the probe.  **M1 / M3**: the platform's trait-hood filter and novelty scorer.",
        "",
        "## Counts",
        "",
        "| step | count |",
        "|---|---|",
        f"| census table rows (distinct stems) | {p['table_rows']:,} |",
        f"| TDA words parsed | {p['tda_words']:,} |",
        f"| Allport-Odbert words parsed (distinct) | {p['allport_words']:,} (lines I {p['allport_lines'].get('I')}, "
        f"II {p['allport_lines'].get('II')}, III {p['allport_lines'].get('III')}, IV {p['allport_lines'].get('IV')}) |",
        f"| in both lists | {p['in_both']:,} |",
        f"| malformed (dropped) | {p['malformed']} |",
        f"| eligible rows of this stage | {f['stage_pool']} |",
        f"| TDA words cut by the floor | {f['tda_cut']} (every TDA word is submitted; {f['tda_below_dictionary_floor']} "
        f"of them are below the dictionary floor and reach the platform's probe through the curated route) |",
        f"| Allport-only words cut by the floor (not in any stage) | "
        + ", ".join(f"{k} {v:,}" for k, v in f["allport_only_cut"].items()) + " |",
        f"| Allport-only words in later stages | " + ", ".join(f"{k} {v:,}" for k, v in f["allport_only_eligible"].items()) + " |",
        f"| **submitted in this run** | **{s['n_candidates']}** ({s['n_with_gloss_hint']} with a gloss hint, "
        f"{s['n_state_prefix']} framed as a disposition from Allport-Odbert column II) |",
        f"| of those, routed to the platform's definition probe | {f['submitted_to_probe']} "
        f"({', '.join(f'{k} {v}' for k, v in f['submitted_probe_routes'].items()) or 'none'}) |",
        f"| registry: new rows / merged into existing rows / unchanged | {reg.get('n_new')} / {reg.get('n_merged')} / "
        f"{reg.get('n_unchanged')} (invalid surfaces: {len(reg.get('invalid') or [])}) |",
        f"| duplicates merged at ingest | Allport cross-column {m['allport_cross_column']}, within-column "
        f"{m['allport_within_column']}, TDA and Allport {m['tda_and_allport']:,}, TDA multi-row {m['tda_multi_row']}, "
        f"one-edit repairs {m['repaired']} |",
        f"| known labels submitted (corpus traits) | {ev['known_labels']['n']} |",
        "",
    ]
    if est:
        lines += [f"Downstream estimate when submitted ({est.get('transport')}): M1 ${est.get('m1_usd', 0):.2f} + "
                  f"M3 ${est.get('m3_usd', 0):.2f} = ${est.get('total_usd', 0):.2f}; the generator itself spent "
                  f"${ev['cost']['total_usd']:.2f} (" + L(run_dir / "usage.json") + ").", ""]
    c = ev.get("ceiling") or {}
    if c:
        lines += ["## String ceiling", "",
                  f"Of the corpus's {c['n_corpus']} traits ({c['n_multiword']} of them multi-word), the census lists "
                  f"contain as strings: TDA {c['n_tda']} ({c['tda']:.1%}), Allport-Odbert {c['n_allport']} "
                  f"({c['allport']:.1%}), either {c['n_union']} ({c['union']:.1%}; {c['union_single_word']:.1%} of the "
                  f"single-word traits).  The generator's own eligibility rule submits {c['n_matched_eligible']} of "
                  f"the {c['n_union']} ({c['submitted_of_matched']:.1%}; the policy asks for 95%).  Of the "
                  f"{c['n_queue']} queued traits, {c['n_queue_union']} are in either list.  Source: "
                  + L(counts_path) + ".", ""]
    stems = ev["known_labels"]["stems"]
    lines += ["## Known labels in this run", "",
              f"{len(stems)} submitted words are existing corpus traits (each links to its file): "
              + (", ".join(_trait(x, d) for x in stems) if stems else "none") + ".", ""]
    if ev.get("filter"):
        fl = ev["filter"]
        kp = fl["known_label_pass"]
        lines += ["## Filter (M1)", "",
                  f"{fl['n_filtered']} of {fl['n_rows']} rows filtered.  Verdicts: "
                  + ", ".join(f"{k} {v}" for k, v in fl["verdict"].items()) + ".  Tags: "
                  + (", ".join(f"{k} {v}" for k, v in fl["tags"].items()) or "none") + ".",
                  f"Known-label pass rate (verdict trait, or tagged state or physical): "
                  f"{kp['n_pass']} of {kp['n_filtered']}" + (f" ({kp['pass_rate']:.1%})" if kp["pass_rate"] is not None else "")
                  + ".  Misses: " + (", ".join(f"{_trait(x['stem'], d)} ({x['outcome'] or x['verdict']})"
                                              for x in kp["misses"]) or "none") + ".", ""]
    else:
        lines += ["## Filter (M1)", "", "Not run yet on this run's rows (Fable runs it); " + cli + " `report` fills this "
                  "section, the known-label pass rate and the costs once it has.", ""]
    if ev.get("novelty"):
        nv = ev["novelty"]
        lines += ["## Novelty (M3)", "", f"{nv['n_scored']} rows scored: "
                  + ", ".join(f"{k} {v}" for k, v in nv["decision"].items())
                  + f"; pair completions {nv['pair_completion']}.", ""]
    lines += ["## Files", "",
              f"- {L(run_dir / 'candidates.jsonl')}: the submitted candidates, one per line (tracked; the main "
              f"checkout resubmits it with {reg_cli} `submit --file`)",
              f"- {L(run_dir / 'run.json')}, {L(run_dir / 'usage.json')}, {L(run_dir / 'keys.txt')}, "
              f"{L(run_dir / 'submit_report.json')}, {L(run_dir / 'evaluation.json')}",
              f"- {L(table_path)} (the census table), {L(counts_path)} (ingest counts), "
              f"{L(manifest_path)} (downloads: URLs, hashes, licences, attribution)", ""]
    return "\n".join(lines)
