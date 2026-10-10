"""Free measures of a round, and the pilot's evaluation over the platform's blocks (plan sections 6, 10).

* :func:`round_stats`: the ``stats_round<N>.json`` record of section 6 (yields, rarefaction, Chao1, collapse
  index, noun share, per family, recovery-by-string against the corpus stems and their ``renamed_from``) plus
  junk proxies for the temperature shakedown.  Computed from the samples, the table and the per-sample stems
  ``parse`` saved; no calls.
* :func:`evaluate_run`: a submitted run's figures once M1 and M3 have run: verdict and outcome fractions, the
  measured pass rate (replacing the 0.5 placeholder), noun share of M1 survivors, the ``ai_assistant`` family
  separately (yield, M1 trait rate, alignment scores, M3 new rate), M3 covered / new / grey, relation-call
  opposites and pair completions, cost per candidate and useful candidates per dollar from the ``usage.json``
  files.  Every number is counted from files on disk.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from . import GENERATOR, MODEL_ID
from .diversity import chao1, collapse_index, per_family, rarefaction, string_recovery
from .prompts import PROMPTS_VERSION


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def renamed_map(stems: Iterable[str], corpus_stems: Iterable[str], *, data_dir=None) -> dict[str, str]:
    """``{candidate stem: current corpus stem}`` for candidates that spell a corpus trait's former name
    (``entity_id.resolve_renamed_stem``, which reads ``renamed_from`` in all its forms)."""
    from assistant_axis.entity_id import resolve_renamed_stem
    corpus = set(corpus_stems)
    out = {}
    for s in stems:
        if s in corpus:
            continue
        cur = resolve_renamed_stem(s, "traits", data_dir=data_dir)
        if cur != s and cur in corpus:
            out[s] = cur
    return out


def round_stats(samples: Sequence[Mapping], rows: Sequence[Mapping], per_sample: Sequence[Mapping],
                table_counts: Mapping, *, round_n: int, temperature: Optional[float], corpus_stems: Iterable[str],
                renamed: Optional[Mapping[str, str]] = None, step: int = 1000) -> dict:
    """The section-6 stats record of one round (or one temperature of the shakedown)."""
    corpus = set(corpus_stems)
    n = len(samples)
    counts = {r["stem"]: int(r["count"]) for r in rows}
    eligible = [r for r in rows if r["eligible"]]
    rec = string_recovery([r["stem"] for r in rows], corpus, renamed)
    by_family = {}
    for f in sorted({fam for r in rows for fam in r["families"]}):
        stems = [r["stem"] for r in rows if r["families"].get(f)]
        by_family[f] = string_recovery(stems, corpus, renamed)["recall"]
    ordered = [p["stems"] for p in sorted(per_sample, key=lambda p: (p["index"], p["sample_id"]))]
    n_items = sum(len(s) for s in ordered)
    stops = Counter(s.get("stop_reason") for s in samples)
    return {
        "round": round_n, "prompts_version": PROMPTS_VERSION, "model": MODEL_ID, "temperature": temperature,
        "n_samples": n, "n_raw_items": table_counts.get("n_raw_items"), "n_unique": len(rows),
        "n_eligible": len(eligible),
        "uniques_per_1k_samples": round(1000.0 * len(rows) / n, 1) if n else None,
        "eligible_per_1k_samples": round(1000.0 * len(eligible) / n, 1) if n else None,
        "rarefaction": [list(x) for x in rarefaction(ordered, step=step)],
        "chao1": round(chao1(counts), 1), "chao1_eligible": round(chao1({r["stem"]: r["count"] for r in eligible}), 1),
        "collapse_top50_share": round(collapse_index(counts, top=50), 4),
        "top20": [[r["stem"], r["count"]] for r in rows[:20]],
        "noun_share_unique": _frac(sum(1 for r in rows if r["form"] == "noun"), len(rows)),
        "noun_share_eligible": _frac(sum(1 for r in eligible if r["form"] == "noun"), len(eligible)),
        "form_counts": table_counts.get("by_form"), "form_counts_eligible": table_counts.get("by_form_eligible"),
        "normalized_mechanically": table_counts.get("normalized_mechanically"),
        "per_family": per_family(rows, samples=samples),
        "recovery_strings": {"n_corpus": rec["n_corpus"], "found": rec["found"], "recall": rec["recall"],
                             "by_family": by_family, "via_renamed_from": rec["via_renamed_from"]},
        "junk": {"items_per_sample": round(n_items / n, 2) if n else None,
                 "empty_sample_share": _frac(sum(1 for s in ordered if not s), n),
                 "ineligible_share": _frac(len(rows) - len(eligible), len(rows)),
                 "ineligible": table_counts.get("ineligible"),
                 "seed_echo_per_sample": _frac(table_counts.get("n_seed_echo", 0), n),
                 "bio_echo": table_counts.get("n_bio_echo"),
                 "stop_reasons": dict(sorted((str(k), v) for k, v in stops.items())),
                 "mean_new_tokens": round(sum(int(s.get("n_new_tokens") or 0) for s in samples) / n, 1) if n else None},
    }


# ---------------------------------------------------------------------------- after M1 / M3

def _read_json(path: Path) -> Optional[dict]:
    p = Path(path)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) and "_provenance" in d else d


def cost_summary(usage_paths: Iterable[Path]) -> dict:
    """Sum ``usage.json`` files per model (cost and tokens)."""
    per_model: dict[str, dict] = {}
    files = []
    for p in usage_paths:
        p = Path(p)
        if not p.exists():
            continue
        files.append(str(p))
        d = json.loads(p.read_text(encoding="utf-8"))
        for m, u in (d.get("per_model") or {}).items():
            cur = per_model.setdefault(m, {"cost_usd": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "n_calls": 0})
            cur["cost_usd"] = round(cur["cost_usd"] + float(u.get("cost_usd") or 0.0), 6)
            for k in ("prompt_tokens", "completion_tokens", "n_calls"):
                cur[k] += int(u.get(k) or 0)
    return {"files": files, "per_model": dict(sorted(per_model.items())),
            "total_usd": round(sum(v["cost_usd"] for v in per_model.values()), 6)}


def run_rows(registry_rows: Mapping[str, Mapping], run_id: str) -> list[Mapping]:
    """Registry rows with a source from this generator run, sorted by key."""
    return [r for k, r in sorted(registry_rows.items())
            if any(s.get("generator") == GENERATOR and s.get("run_id") == run_id for s in r.get("sources") or [])]


def _family_of(row: Mapping, run_id: str) -> Optional[str]:
    for s in row.get("sources") or []:
        if s.get("generator") == GENERATOR and s.get("run_id") == run_id:
            ref = s.get("source_ref") or ""
            parts = ref.split(":")
            return parts[1] if len(parts) > 2 else None
    return None


def _m1(rows: Sequence[Mapping]) -> dict:
    filt = [r for r in rows if r.get("filter")]
    traits = [r for r in filt if r["filter"].get("verdict") == "trait"]
    align = Counter(r["filter"].get("alignment") for r in filt if r["filter"].get("alignment") is not None)
    return {"n_rows": len(rows), "n_filtered": len(filt), "n_trait": len(traits),
            "pass_rate": _frac(len(traits), len(filt)),
            "verdict": dict(sorted(Counter(r["filter"].get("verdict") for r in filt).items())),
            "outcome": dict(sorted(Counter(str(r["filter"].get("outcome")) for r in filt).items())),
            "tags": dict(sorted(Counter(t for r in filt for t in (r["filter"].get("tags") or [])).items())),
            "alignment_scores": {str(k): v for k, v in sorted(align.items(), key=lambda kv: str(kv[0]))},
            "alignment_relevant": sum(1 for r in filt if r["filter"].get("alignment_relevant"))}


def _m3(rows: Sequence[Mapping]) -> dict:
    nov = [r for r in rows if r.get("novelty")]
    opp = sum(1 for r in nov for x in (r["novelty"].get("readings") or []) if x.get("relation") == "antonym")
    return {"n_scored": len(nov),
            "decision": dict(sorted(Counter(r["novelty"].get("decision") for r in nov).items())),
            "new_rate": _frac(sum(1 for r in nov if r["novelty"].get("decision") == "new"), len(nov)),
            "pair_completions": sum(1 for r in nov if r["novelty"].get("pair_completion_for")),
            "relation_opposites": opp,
            "new_stems": sorted(r["stem"] for r in nov if r["novelty"].get("decision") == "new"),
            "grey_stems": sorted(r["stem"] for r in nov if r["novelty"].get("decision") == "grey")}


def evaluate_run(run_id: str, *, run_dir: Path, table: Sequence[Mapping], stats: Optional[Mapping],
                 registry_rows: Mapping[str, Mapping], filter_dir: Path, novelty_dir: Path,
                 sampling_usage: Optional[Path] = None) -> dict:
    """The pilot readout's numbers (see the module docstring)."""
    cands = [json.loads(x) for x in (run_dir / "candidates.jsonl").read_text(encoding="utf-8").splitlines()
             if x.strip()] if (run_dir / "candidates.jsonl").exists() else []
    run = _read_json(run_dir / "run.json") or {}
    rows = run_rows(registry_rows, run_id)
    by_stem = {r["stem"]: r for r in table}
    fam_rows: dict[str, list] = {}
    for r in rows:
        fam_rows.setdefault(_family_of(r, run_id) or "?", []).append(r)
    m1 = _m1(rows)
    survivors = [r for r in rows if (r.get("filter") or {}).get("verdict") == "trait"]
    noun_surv = sum(1 for r in survivors if (by_stem.get(r["stem"]) or {}).get("form") == "noun")
    cost = cost_summary([run_dir / "usage.json", Path(filter_dir) / "usage.json", Path(novelty_dir) / "usage.json"])
    m3 = _m3(rows)
    useful = m3["decision"].get("new", 0) + m3["pair_completions"]
    families = {}
    for f, rs in sorted(fam_rows.items()):
        families[f] = {"n_submitted": len(rs), "m1": _m1(rs), "m3": _m3(rs)}
    return {
        "run_id": run_id, "generator": GENERATOR, "args": run.get("args"), "n_candidates": len(cands),
        "stats": stats, "m1": m1, "m3": m3,
        "noun_share_m1_survivors": _frac(noun_surv, len(survivors)), "n_m1_survivors": len(survivors),
        "by_family": families, "ai_assistant": families.get("ai_assistant"),
        "cost": cost, "cost_per_candidate": _frac(cost["total_usd"], len(cands)),
        "useful": useful, "useful_per_dollar": round(useful / cost["total_usd"], 1) if cost["total_usd"] else None,
        "sampling_usage": cost_summary([sampling_usage]) if sampling_usage else None,
    }
