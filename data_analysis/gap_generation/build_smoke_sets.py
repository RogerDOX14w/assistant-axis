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

``--round 3`` writes the ambiguity round's inputs (sets 1-3 and round 2 read, not rewritten):

* ``m2rubric_r3_dev.jsonl``: 30 corpus traits (seed 5; not the six, not
  unflinching), each paired with its own description (expected ``same``) and
  with the description of the trait 15 places on in the sample (expected
  ``different``, by construction): 60 comparisons, for writing the
  comparison prompt;
* ``m2rubric_r3_heldout.jsonl``: the six September rejects with their
  September descriptions (the seed queue's ``not_adopted`` entries; engaging
  takes unflinching.json's, the trait it was renamed to): run once, last;
* ``m2rubric_r3_classifier.jsonl``: 15 existing + 15 random rows (seed 6),
  disjoint from every earlier smoke set.

``--round 5 [--step N]`` writes ``m2rubric_r5_sample_<N>.jsonl``: random
adjectives (stratum ``oewn_random``) that no recorded pilot or smoke batch
has seen, in an order fixed by seed 7; step 1 is the first 160, each later
step the next 40.  For the sample of 50 passed words that Roger marks
(``reports/trait_gap_generation/random_traits_for_marks.md``).  Once run,
these batches are themselves recorded runs, so the full run counts their
rows as seen in development.
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


SIX = ("disciplinary", "engaging", "economic", "balanced", "empowered", "emotive")


def round3() -> int:
    """Round 3 (open point D): the comparison's development set, the held-out
    six, and a classifier batch on prompt version 3.  Reads corpus and queue
    files only."""
    tdir = _REPO_ROOT / "data" / "traits" / "instructions"
    traits = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(tdir.glob("*.json"))}
    pool = [s for s, d in traits.items() if d.get("description") and s not in SIX and s != "unflinching"]
    pick = random.Random(5).sample(pool, 30)
    dev = []
    for i, s in enumerate(pick):
        d = traits[s]
        dev.append({"key": f"{s}#same", "label": d.get("positive_label") or s, "intended": d["description"],
                    "expected": "same", "intended_from": s})
    for i, s in enumerate(pick):
        other = pick[(i + 15) % len(pick)]
        neg = str(traits[s].get("negative_label") or "").lower().replace(" ", "_").replace("-", "_")
        assert other != s and other != neg, (s, other)
        d = traits[s]
        dev.append({"key": f"{s}#diff", "label": d.get("positive_label") or s,
                    "intended": traits[other]["description"], "expected": "different", "intended_from": other})
    _write("m2rubric_r3_dev.jsonl", dev)

    q = json.loads((_REPO_ROOT / "data" / "seed_queue.json").read_text(encoding="utf-8"))
    by_stem = {e.get("stem"): e for e in q["entries"] if e.get("status") == "not_adopted"}
    held = []
    for w in SIX:
        if w == "engaging":  # renamed to unflinching (coordinator: use that file's description)
            held.append({"key": f"{w}#heldout", "label": w, "intended": traits["unflinching"]["description"],
                         "intended_from": "data/traits/instructions/unflinching.json"})
        else:
            held.append({"key": f"{w}#heldout", "label": w, "intended": by_stem[w]["description"],
                         "intended_from": "data/seed_queue.json (not_adopted entry, description)"})
    _write("m2rubric_r3_heldout.jsonl", held)

    rows = [json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines() if x.strip()]
    used = set()
    for name in ("m2rubric_smoke_1", "m2rubric_smoke_2", "m2rubric_smoke_3", "m2rubric_r2_classifier"):
        p = paths.VALIDATION_DIR / f"{name}.jsonl"
        used |= {json.loads(x)["surface"] for x in p.read_text(encoding="utf-8").splitlines() if x.strip()}
    rng = random.Random(6)
    cls = []
    for s in STRATA:
        cls += rng.sample([r for r in rows if r["stratum"] == s and r["surface"] not in used], 15)
    _write("m2rubric_r3_classifier.jsonl", cls)
    return 0


#: Round 5: the sample of random adjectives for Roger's marks (question R2).
R5_SEED = 7
R5_FIRST, R5_STEP = 160, 40
R5_PREFIX = "m2rubric_r5_sample"


def round5(step: int) -> int:
    """Rows of the ``oewn_random`` stratum that no recorded run has seen
    (``filter.development_seen``, ignoring this job's own batches), in an
    order fixed by seed 7; step 1 takes the first 160, each later step the
    next 40.  Writes ``m2rubric_r5_sample_<step>.jsonl``."""
    from assistant_axis.gapgen.filter import development_seen
    from assistant_axis.gapgen.normalize import make_key, normalize_candidate
    rows = [json.loads(x) for x in SRC.read_text(encoding="utf-8").splitlines() if x.strip()]
    seen = development_seen(paths.DATA_CANDIDATES)
    seen = {k: [s for s in v if not s.startswith(f"filter/{R5_PREFIX}")] for k, v in seen.items()}
    pool = []
    for r in rows:
        if r["stratum"] != "oewn_random":
            continue
        key = make_key(normalize_candidate(r["surface"]).stem, int(r.get("sense_id") or 1))
        if not seen.get(key):
            pool.append(r)
    pool.sort(key=lambda r: r["surface"])
    random.Random(R5_SEED).shuffle(pool)
    start = 0 if step == 1 else R5_FIRST + (step - 2) * R5_STEP
    end = R5_FIRST if step == 1 else start + R5_STEP
    pick = pool[start:end]
    print(f"{len(pool)} random adjectives unseen before this job; step {step} takes rows {start}-{end - 1}")
    _write(f"{R5_PREFIX}_{step}.jsonl", pick)
    return 0


def main() -> int:
    if sys.argv[1:] == ["--round", "2"]:
        return round2()
    if sys.argv[1:3] == ["--round", "5"]:
        return round5(int(sys.argv[4]) if sys.argv[3:4] == ["--step"] else 1)
    if sys.argv[1:] == ["--round", "3"]:
        return round3()
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
