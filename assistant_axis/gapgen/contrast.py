"""Contrast clauses in trait descriptions (M2, plan 15 step 5).

``parse_census`` reads the 2026-09-23 census
(``reports/trait_gap_generation/contrast_clauses_census.md``): ten N
(necessary for sense), 68 P (names the other pole) and 29 S (stylistic or
scope) stems, from its ``**stem**`` bullets under the three section headings.
"""
from __future__ import annotations

import re
from pathlib import Path

CLASSES = ("N", "P", "S")
_SECTION_RE = re.compile(r"^##\s+([NPS]):", re.M)
_BULLET_RE = re.compile(r"^- \*\*([a-z0-9_]+)\*\*:", re.M)


def parse_census(path: Path) -> dict[str, str]:
    """``{stem: "N" | "P" | "S"}`` from the census markdown."""
    text = Path(path).read_text(encoding="utf-8")
    out: dict[str, str] = {}
    heads = list(_SECTION_RE.finditer(text))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        for m in _BULLET_RE.finditer(text, h.end(), end):
            out[m.group(1)] = h.group(1)
    return out
