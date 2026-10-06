"""The M3 pilot's two candidate pools (coding_plan_m3.md, "The pilot").

* ``antonym_check/pilot_1`` (:func:`antonym_pool`): every ``candidates`` entry of
  ``data/traits/antonym_check_history.jsonl`` (the words the antonym checks proposed), normalised with
  ``normalize_to_file_name``, minus the corpus trait stems and the seed queue's names (every entry's stem
  and normalised label, any status: the names M3's exact-label check would cover).  One row per (word,
  check): ``source_ref`` the checked trait's stem, so a word several checks proposed becomes one registry
  row with several sources; ``gloss_hint`` empty; ``score`` the number of times the word was proposed.
* ``m1_validation/pilot_1`` (:func:`m1_validation_pool`): ``n`` (150) of the random dictionary adjectives
  (stratum ``oewn_random``) that the M1 validation run passed as ``trait``, drawn with ``seed`` (0); they go
  through the filter again like any candidate, their earlier reading kept on record for comparison
  (``source_ref`` names the validation row).

Both return the rows ``gap_registry.py submit --file`` reads (``{surface, rank?, score?, gloss_hint?,
source_ref?}``) and the counts the readout quotes.
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Optional

from assistant_axis.entity_id import normalize_to_file_name

ANTONYM_GENERATOR, M1_GENERATOR, PILOT_RUN_ID = "antonym_check", "m1_validation", "pilot_1"
M1_STRATUM = "oewn_random"


def queue_names(queue: Mapping) -> set[str]:
    """Every seed-queue entry's stem and normalised label, any status and entity type."""
    out = set()
    for e in queue.get("entries") or []:
        if e.get("stem"):
            out.add(e["stem"])
        if e.get("label"):
            out.add(normalize_to_file_name(e["label"]))
    return out


def corpus_trait_stems(data_dir: Path) -> set[str]:
    return {p.stem for p in (Path(data_dir) / "traits" / "instructions").glob("*.json")}


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def antonym_pool(history_path: Path, *, corpus: Iterable[str], queue: Iterable[str]) -> tuple[list[dict], dict]:
    """``(rows, counts)``.  The surface is the word's first spelling in the history (hyphens kept)."""
    corpus, queue = set(corpus), set(queue)
    seen_surface: dict[str, str] = {}
    times: Counter = Counter()
    refs: dict[str, list[str]] = {}
    n_entries = 0
    for rec in _jsonl(history_path):
        for w in rec.get("candidates") or []:
            if not isinstance(w, str) or not w.strip():
                continue
            n_entries += 1
            stem = normalize_to_file_name(w.strip())
            if not stem:
                continue
            seen_surface.setdefault(stem, w.strip())
            times[stem] += 1
            src = rec.get("stem")
            if src and src not in refs.setdefault(stem, []):
                refs[stem].append(src)
    kept = sorted(s for s in times if s not in corpus and s not in queue)
    rows = []
    for s in kept:
        for ref in refs.get(s) or [None]:
            rows.append({"surface": seen_surface[s], "score": times[s], "gloss_hint": None, "source_ref": ref})
    counts = {"history_candidate_entries": n_entries, "distinct_words": len(times),
              "in_corpus": sum(1 for s in times if s in corpus),
              "in_queue_not_corpus": sum(1 for s in times if s in queue and s not in corpus),
              "words": len(kept), "words_proposed_more_than_once": sum(1 for s in kept if times[s] > 1),
              "rows": len(rows)}
    return rows, counts


def m1_validation_pool(results_path: Path, *, n: int = 150, seed: int = 0, stratum: str = M1_STRATUM
                       ) -> tuple[list[dict], dict]:
    """``(rows, counts)``: ``n`` of the stratum's rows whose filter verdict was ``trait``, a seeded sample
    of them sorted by key (``random.Random(seed).sample``), in key order."""
    rows = [r for r in _jsonl(results_path) if (r.get("meta") or {}).get("stratum") == stratum]
    passed = sorted((r for r in rows if (r.get("filter") or {}).get("verdict") == "trait"), key=lambda r: r["key"])
    if n > len(passed):
        raise ValueError(f"asked for {n} rows, the stratum has {len(passed)} that passed")
    pick = sorted(random.Random(seed).sample(passed, n), key=lambda r: r["key"])
    out = [{"surface": (r.get("meta") or {}).get("surface") or r["label"], "gloss_hint": None,
            "source_ref": f"m1_validation:{r['key']}"} for r in pick]
    counts = {"stratum_rows": len(rows), "passed_as_trait": len(passed), "drawn": len(out), "seed": seed,
              "held_among_drawn": sum(1 for r in pick if r.get("holding"))}
    return out, counts


def write_pool(rows: Iterable[Mapping], path: Path) -> Path:
    from assistant_axis.atomic_io import atomic_write_text
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), path)
    return path


def build_pilot_pools(repo_root: Path, out_dir: Path, *, n_m1: int = 150, seed: int = 0,
                      queue: Optional[Mapping] = None) -> dict:
    """Write both pools to ``out_dir`` (``antonym_check_pilot_1.jsonl``, ``m1_validation_pilot_1.jsonl``) and
    ``pools.json`` (the counts and the inputs); returns that record."""
    from assistant_axis.atomic_io import atomic_write_text
    repo_root = Path(repo_root)
    data = repo_root / "data"
    q = queue if queue is not None else json.loads((data / "seed_queue.json").read_text(encoding="utf-8"))
    history = data / "traits" / "antonym_check_history.jsonl"
    m1 = data / "candidates" / "filter" / "m1_validation" / "results.jsonl"
    a_rows, a_counts = antonym_pool(history, corpus=corpus_trait_stems(data), queue=queue_names(q))
    m_rows, m_counts = m1_validation_pool(m1, n=n_m1, seed=seed)
    out_dir = Path(out_dir)
    a_path = write_pool(a_rows, out_dir / f"{ANTONYM_GENERATOR}_{PILOT_RUN_ID}.jsonl")
    m_path = write_pool(m_rows, out_dir / f"{M1_GENERATOR}_{PILOT_RUN_ID}.jsonl")
    rec = {"antonym_check": {"file": a_path.name, "generator": ANTONYM_GENERATOR, "run_id": PILOT_RUN_ID, **a_counts},
           "m1_validation": {"file": m_path.name, "generator": M1_GENERATOR, "run_id": PILOT_RUN_ID, **m_counts},
           "inputs": {"antonym_check_history": str(history.relative_to(repo_root)),
                      "m1_validation_results": str(m1.relative_to(repo_root)), "seed_queue": "data/seed_queue.json",
                      "corpus": "data/traits/instructions"}}
    atomic_write_text(json.dumps(rec, indent=2) + "\n", out_dir / "pools.json")
    return rec
