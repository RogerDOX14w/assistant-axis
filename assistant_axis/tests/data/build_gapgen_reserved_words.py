#!/usr/bin/env python3
"""Build ``gapgen_reserved_words.txt``: words no rubric example may use.

    uv run python assistant_axis/tests/data/build_gapgen_reserved_words.py

Rubric examples in any gap-generation prompt must not be words that appear in
``reports/trait_gap_generation/decisions_m1.md`` (Roger's decisions and the
polysemy appendices) or in the "You are X." probe's results
(``reports/trait_gap_generation/probe_you_are_x/results.jsonl``).  Those two
files are working files the coordinator commits later, so the hygiene test
must not read them (review_rubric_v2.md finding 6).  This script is run once,
by hand, to turn them into one tracked list: every lowercase word token of
both files, one per line, sorted.  A hyphenated token is kept whole and its
parts are added too.  Rerun it only if those files change, and commit the
list with the change.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SOURCES = (REPO / "reports" / "trait_gap_generation" / "decisions_m1.md",
           REPO / "reports" / "trait_gap_generation" / "probe_you_are_x" / "results.jsonl")
OUT = Path(__file__).resolve().parent / "gapgen_reserved_words.txt"
_TOKEN = re.compile(r"[a-z]+(?:[-'][a-z]+)*")


def tokens(text: str) -> set[str]:
    out = set()
    for t in _TOKEN.findall(text.lower()):
        out.add(t)
        if "-" in t:
            out.update(p for p in t.split("-") if p)
    return out


def main() -> int:
    words: set[str] = set()
    for src in SOURCES:
        words |= tokens(src.read_text(encoding="utf-8"))
    OUT.write_text("".join(f"{w}\n" for w in sorted(words)), encoding="utf-8")
    print(f"wrote {len(words)} words to {OUT} from {', '.join(p.name for p in SOURCES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
