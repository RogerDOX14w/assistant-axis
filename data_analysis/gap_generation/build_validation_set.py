#!/usr/bin/env python3
"""Build the M1 trait-hood validation file (plan §9 task 9).

    uv run python data_analysis/gap_generation/build_validation_set.py [--out F] [--n-oewn 1000] [--seed 0]

Strata (one JSONL row each: ``surface``, ``stratum``, ``expected``, and
``entity_type`` / ``source`` where useful), counted from the files at run
time (the plan's 2026-09-23 numbers are out of date):

* ``existing``: the ``positive_label`` of every trait file; expected
  ``trait``.
* ``rejects``: the six September rejects (disciplinary, engaging, economic,
  balanced, empowered, emotive), each kept only while it has no corpus file;
  expected ``polysemy`` or ``trait_sense_rank >= 2``, plus ``state`` /
  ``transient_only`` for empowered and ``relational_only`` for economic.
* ``physical``: seed-queue entries tagged ``physical`` with no corpus file;
  expected ``tagged`` + ``physical`` (added: the plan assumed these were corpus
  files, but none is).
* ``not_adopted``: seed-queue entries with status ``not_adopted`` and no
  corpus file (report only; no expected verdict).
* ``oewn_random``: ``--n-oewn`` adjective lemmas drawn from OEWN 2024 with
  ``--seed``, letters/space/hyphen/apostrophe only, excluding every corpus and
  queue stem and every stem already in another stratum; expected: at most 15%
  ``trait`` across the stratum.

A stem appears once, in the first stratum of the order above.  The output
(default ``data/candidates/validation/m1_validation.jsonl``) is tracked.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.entity_id import normalize_to_file_name  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402

SIX_REJECTS = ("disciplinary", "engaging", "economic", "balanced", "empowered", "emotive")
REJECT_EXTRA = {"empowered": {"tags_any": ["state", "transient_only"]}, "economic": {"tags_any": ["relational_only"]}}
LEMMA_OK = re.compile(r"^[A-Za-z][A-Za-z' -]*[A-Za-z]$")
DEFAULT_OUT = paths.VALIDATION_DIR / "m1_validation.jsonl"


def build_rows(data_dir: Path, queue: dict, adjectives: Iterable[str], *, n_oewn: int = 1000,
               seed: int = 0) -> tuple[list[dict], dict]:
    import data_analysis.seed_entities as se

    corpus = se.corpus_stems(data_dir)
    corpus_all = corpus["trait"] | corpus["role"]
    queued = {e.get("stem") for e in queue["entries"]} | {normalize_to_file_name(e["label"])
                                                           for e in queue["entries"] if e.get("label")}
    rows: list[dict] = []
    used: set[str] = set()
    notes: dict = {"rejects_now_in_corpus": [], "not_adopted_in_corpus": []}

    def add(surface: str, stratum: str, expected: Optional[dict], **extra) -> bool:
        stem = normalize_to_file_name(surface)
        if stem in used:
            return False
        used.add(stem)
        rows.append({"surface": surface, "stratum": stratum, "expected": expected, **extra})
        return True

    for w in SIX_REJECTS:
        if w in corpus_all:
            notes["rejects_now_in_corpus"].append(w)
            continue
        add(w, "rejects", {"polysemy_or_rank2": True, **REJECT_EXTRA.get(w, {})})

    tdir = data_dir / "traits" / "instructions"
    for p in sorted(tdir.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        add(d.get("positive_label") or p.stem.replace("_", " "), "existing", {"verdict": "trait"},
            entity_type="trait", corpus_stem=p.stem)

    for e in queue["entries"]:
        if "physical" in (e.get("tags") or []) and e.get("stem") not in corpus_all:
            add(e.get("label") or e["stem"], "physical", {"verdict": "tagged", "tags_any": ["physical"]},
                entity_type=e.get("entity_type"), queue_status=e.get("status"))

    for e in queue["entries"]:
        if e.get("status") != "not_adopted":
            continue
        if e.get("stem") in corpus_all:
            notes["not_adopted_in_corpus"].append(e["stem"])
            continue
        add(e.get("label") or e["stem"], "not_adopted", None, entity_type=e.get("entity_type"))

    pool = sorted({a for a in adjectives if LEMMA_OK.match(a)
                   and normalize_to_file_name(a) not in corpus_all | queued | used}, key=str.lower)
    rng = random.Random(seed)
    picked = rng.sample(pool, min(n_oewn, len(pool)))
    for a in sorted(picked, key=str.lower):
        add(a, "oewn_random", {"trait_max_frac": 0.15}, source="oewn:2024")
    notes.update({"counts": dict(Counter(r["stratum"] for r in rows)), "oewn_pool": len(pool),
                  "n_corpus_traits": len(corpus["trait"]), "n_corpus_roles": len(corpus["role"])})
    return rows, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--queue", type=Path, default=paths.SEED_QUEUE_PATH)
    ap.add_argument("--n-oewn", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    import data_analysis.seed_entities as se
    from assistant_axis.gapgen import wordnet as gw

    if not gw.oewn_installed():
        raise SystemExit("OEWN is not installed: run setup_external.py --wn")
    rows, notes = build_rows(args.data_dir, se.load_queue(args.queue), gw.adjective_lemmas(),
                             n_oewn=args.n_oewn, seed=args.seed)
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), args.out)
    print(json.dumps(notes, indent=1))
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
