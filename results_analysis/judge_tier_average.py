"""Averaged judge cells: the passes of one judge (shuffle seeds), or the passes of several judges (a
blend).  Per entity the mean of the scores present, usage the sum of all, correlations recomputed.

A source holding under ``min_coverage`` of the axis's entities is refused.  On 2026-11-02 eight empty
cells, left by an outage, were averaged in without a word, and quietly turned two passes into one on
those axes.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge_pricing import MultiModelUsage
from results_analysis import judge_tier_cost_eval as ev
from results_analysis.axis_judge_correlation import compute_correlations

#: The least of an axis a finished cell may hold and still be averaged: one batch of 20 lost on a
#: 573-entity axis leaves 96.5%.
DEFAULT_MIN_COVERAGE = 0.9


@dataclass
class AverageResult:
    made: int = 0
    kept: int = 0
    refused: List[str] = field(default_factory=list)   # one line per axis, for a report


def short_sources(loaded: Sequence[dict], sources: Sequence[str], n_entities: int,
                  min_coverage: float) -> List[Tuple[str, int]]:
    """``(source, n scored)`` for each source below ``min_coverage`` of the axis's ``n_entities``."""
    return [(s, len(x["result"])) for s, x in zip(sources, loaded) if len(x["result"]) < min_coverage * n_entities]


def average_cells(out: str, sources: Sequence[str], jobs: Sequence["ev.AxisJob"], experiments_dir: Path,
                  instructions_dir: Path, *, min_coverage: float = DEFAULT_MIN_COVERAGE,
                  limit: Optional[int] = None) -> AverageResult:
    """Write ``<axis>_tier_eval/<out>/`` for every axis of ``jobs`` whose ``sources`` are all finished;
    an axis already derived from the same source files (by mtime) is left as it is, and one with a
    short source is refused, with nothing written.  ``limit``: the sources were judged with that
    ``--limit``, so that many entities are the whole axis.  Returns what happened."""
    if len(sources) < 2:
        raise ValueError("averaging needs at least two source cells")
    E = Path(experiments_dir)
    result = AverageResult()
    for job in jobs:
        axis = job.axis_dir
        ds = [E / f"{axis}_tier_eval" / c for c in sources]
        do = E / f"{axis}_tier_eval" / out
        if not all((d / "usage.json").exists() for d in ds):
            continue
        stamp = max(os.path.getmtime(d / "scores_descriptions.json") for d in ds)
        if (do / "usage.json").exists():
            prov = json.loads((do / "scores_descriptions.json").read_text())["_provenance"]
            if prov.get("averaged", {}).get("source_mtime") == stamp:
                result.kept += 1
                continue
        loaded = [json.loads((d / "scores_descriptions.json").read_text()) for d in ds]
        if not job.projections:
            ev.load_axis(job, Path(instructions_dir), limit=limit)
        short = short_sources(loaded, sources, len(job.entities), min_coverage)
        if short:
            result.refused.append(f"{axis}: of {len(job.entities)} entities, "
                                  + ", ".join(f"{s} holds {n}" for s, n in short)
                                  + f" (under {min_coverage:.0%}); judge it again, then rerun this")
            continue
        scores = {}
        for k in set().union(*(x["result"] for x in loaded)):
            v = [x["result"][k] for x in loaded if k in x["result"]]
            scores[k] = sum(v) / len(v)
        corr = compute_correlations(scores_by_mode={"descriptions": scores}, projections=job.projections,
                                    slots=list(job.projections.keys()), excluded_set=job.axis_spec.pole_entity_ids())
        usage = MultiModelUsage.load_or_create(ds[0] / "usage.json")
        for d in ds[1:]:
            usage.merge_from(MultiModelUsage.load_or_create(d / "usage.json"))
        prov = dict(loaded[0]["_provenance"])
        prov.pop("shuffle_seed", None)
        prov["cell_label"] = f"@{out.split('@', 1)[1]}" if "@" in out else ""
        prov["averaged"] = {"sources": list(sources),
                            "n_all": sum(1 for k in scores if all(k in x["result"] for x in loaded)),
                            "n_partial": sum(1 for k in scores if not all(k in x["result"] for x in loaded)),
                            "source_mtime": stamp, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        do.mkdir(parents=True, exist_ok=True)
        atomic_write_text(json.dumps({"result": dict(sorted(scores.items())), "_provenance": prov}, indent=2),
                          do / "scores_descriptions.json")
        atomic_write_text(json.dumps(corr, indent=2), do / "correlations.json")
        # usage.json last: the file that says a cell is finished
        atomic_write_text(json.dumps(usage.as_dict(), indent=2, sort_keys=True), do / "usage.json")
        result.made += 1
    return result
