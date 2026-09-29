#!/usr/bin/env python3
"""Build the rubric v2 smoke-check inputs from the M1 validation file.

    uv run python data_analysis/gap_generation/build_smoke_sets.py

Writes three files of 30 rows each to ``data/candidates/validation/``, drawn
with fixed seeds from the validation file's ``existing`` and ``oewn_random``
strata only (no September rejects, no physical or not_adopted rows):

* ``m2rubric_smoke_1.jsonl`` and ``_2``: 15 existing labels and 15 random
  adjectives each (seeds 1 and 2), disjoint;
* ``m2rubric_smoke_3.jsonl``: 30 rows, from the same two strata, whose Zipf
  puts them in the probe band or rescues them under rule 1b (seed 3), so the
  new definition probe is exercised.

No API call.  The rows keep their stratum, so the filter's summary reports
per stratum.

    uv run python data_analysis/gap_generation/build_smoke_sets.py --round 2

writes the round-2 inputs instead (sets 1-3 are read, not rewritten):

* ``m2rubric_r2_classifier.jsonl``: 15 existing labels and 15 random
  adjectives (seed 4), disjoint from sets 1-3, drawn as before;
* ``m2rubric_r2_probe.jsonl``: the 12 words of the probe check (stratum
  ``probe_check``, for ``traithood_filter.py --probe-only``): the five words
  probe v2 turned down in round 1, the corpus labels uncalculating and
  uninquisitive, and five regular derivations that are not corpus labels,
  queue entries or words of the decisions file.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.freq import zipf_info  # noqa: E402

SRC = paths.VALIDATION_DIR / "m1_validation.jsonl"
STRATA = ("existing", "oewn_random")

#: Round-2 probe check (coordinator's list, plus five derivations chosen here).
PROBE_ROUND1_UNKNOWN = ("unbranching", "unsensational", "unsmooth", "nonsubmersible", "cxl")
PROBE_CORPUS_LABELS = ("uncalculating", "uninquisitive")
PROBE_NEW_DERIVATIONS = ("unpunctual", "overpolite", "unglamorous", "nonreturnable", "unbookish")


def _write(name: str, rows: list[dict]) -> None:
    path = paths.VALIDATION_DIR / name
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), path)
    print(f"wrote {len(rows)} rows to {path}")


def round2() -> int:
    rows = [json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines() if x.strip()]
    used = set()
    for n in (1, 2, 3):
        p = paths.VALIDATION_DIR / f"m2rubric_smoke_{n}.jsonl"
        used |= {json.loads(x)["surface"] for x in p.read_text(encoding="utf-8").splitlines() if x.strip()}
    rng = random.Random(4)
    pick = []
    for s in STRATA:
        pool = [r for r in rows if r["stratum"] == s and r["surface"] not in used]
        pick += rng.sample(pool, 15)
    _write("m2rubric_r2_classifier.jsonl", pick)
    probe = [{"surface": w, "stratum": "probe_check", "group": g}
             for g, words in (("round1_unknown", PROBE_ROUND1_UNKNOWN), ("corpus_label", PROBE_CORPUS_LABELS),
                              ("new_derivation", PROBE_NEW_DERIVATIONS)) for w in words]
    _write("m2rubric_r2_probe.jsonl", probe)
    return 0


def main() -> int:
    if sys.argv[1:] == ["--round", "2"]:
        return round2()
    rows = [json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines() if x.strip()]
    pools = {s: [r for r in rows if r["stratum"] == s] for s in STRATA}
    used: set[str] = set()
    out = {}
    for n, seed in ((1, 1), (2, 2)):
        rng = random.Random(seed)
        pick = []
        for s in STRATA:
            pool = [r for r in pools[s] if r["surface"] not in used]
            pick += rng.sample(pool, 15)
        used |= {r["surface"] for r in pick}
        out[n] = pick
    band = [r for s in STRATA for r in pools[s] if r["surface"] not in used
            and zipf_info(r["surface"], gloss_hint=bool(r.get("gloss_hint"))).probe_band]
    out[3] = random.Random(3).sample(band, 30)
    for n, pick in out.items():
        path = paths.VALIDATION_DIR / f"m2rubric_smoke_{n}.jsonl"
        atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in pick), path)
        print(f"wrote {len(pick)} rows to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
