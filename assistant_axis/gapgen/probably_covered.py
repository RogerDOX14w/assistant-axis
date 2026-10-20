""""Probably covered by X": a free proposed merge for rows M3 read only 2 (Roger, 2026-10-20, option (b)).

**The evidence** (the coordinator's measurement, 2026-10-20): of 217 decided rows whose best M3 overlap reading
(either model) against the corpus was 2, Roger merged 63% in review.  The rule below caught 44% of those rows, and
he had merged 81% of the rows it caught.  His reading: such a candidate is mostly a blend of two to four existing
traits, or subtly different but in a region the corpus already samples well.

**The rule** (:func:`probably_covered`), on a row M3 kept (``new`` or ``grey``) whose best reading by either model
against any corpus trait or queue entry is exactly 2 (none read 3 or 4; opposed traits never count): **at least**
:data:`PROBABLY_COVERED_MIN_READ_2` **traits read 2** (best of the two models), **and** at least one of

* a trait read 2 at a cosine of :data:`PROBABLY_COVERED_MIN_COSINE` or more (M3's retrieval cosine);
* a dictionary link (the lexical sweep's ``lexical.links``: WordNet or the Moby thesaurus) to a trait read 2;
* persona space's ``duplicate_like`` flag on the row (plan 12's ``persona`` block).

X, the proposed target, is the trait read 2 with the highest cosine (ties by key).  **Never a cut**: the row stays
``new`` or ``grey`` and M3's decision is unchanged; the review card shows "probably covered by X (n traits read 2;
why)", and the page highlights X in the corpus list so that ``c`` merges into it in one keystroke.  It is a signal
field (``review_app.decisions.SIGNAL_FIELDS``), so ``serve --blind`` hides it.  No API call.
"""
from __future__ import annotations

from typing import Mapping, Optional

from assistant_axis.gapgen import m3_neighbours as MN

#: At least this many corpus or queue traits read 2 (QUESTIONS 208's follow-up, Roger 2026-10-20, option (b): on 217
#: decided rows read only 2, the rule with this and the cosine below caught 44% of rows, 81% of them merged by Roger,
#: against 63% of all such rows).
PROBABLY_COVERED_MIN_READ_2 = 2
#: A trait read 2 at this cosine or more is one of the rule's three alternative conditions (same measurement).
PROBABLY_COVERED_MIN_COSINE = 0.45
KEPT_DECISIONS = ("new", "grey")
LEXICON_NAMES = {"oewn": "WordNet", "moby": "Moby thesaurus"}

__all__ = ["PROBABLY_COVERED_MIN_READ_2", "PROBABLY_COVERED_MIN_COSINE", "probably_covered"]


def _key(kind: str, stem: str) -> str:
    return f"{'queue' if kind == 'queue' else 'trait'}:{stem}"


def probably_covered(row: Mapping, *, min_read_2: int = PROBABLY_COVERED_MIN_READ_2,
                     min_cosine: float = PROBABLY_COVERED_MIN_COSINE) -> Optional[dict]:
    """``{"probably_covered_by": <target key>, "n_read_2", "read_2": [keys], "why": [...]}`` for a row the rule
    catches (module docstring), else None.  ``why`` lists every condition that holds, in the order cosine,
    dictionary link, persona space: ``{"kind": "cosine", "key", "cosine"}``, ``{"kind": "dictionary", "key",
    "lexicon", "link"}``, ``{"kind": "persona"}``."""
    nv = (row or {}).get("novelty") or {}
    if nv.get("decision") not in KEPT_DECISIONS:
        return None
    read = [n for n in MN.neighbours(row) if n.read and n.best is not None]
    if not read or max(n.best for n in read) != 2:
        return None
    twos = [n for n in read if n.best == 2]
    if len(twos) < min_read_2:
        return None
    keys = {_key(n.kind, n.stem): n for n in twos}
    why: list[dict] = []
    for n in sorted(twos, key=lambda n: (-(n.cosine or 0.0), n.stem)):
        if n.cosine is not None and n.cosine >= min_cosine:
            why.append({"kind": "cosine", "key": _key(n.kind, n.stem), "cosine": round(float(n.cosine), 4)})
    seen = set()
    for x in ((row.get("lexical") or {}).get("links") or []):
        k = _key(x.get("kind"), x.get("stem")) if x.get("stem") else None
        if k in keys and k not in seen:
            seen.add(k)
            why.append({"kind": "dictionary", "key": k, "lexicon": LEXICON_NAMES.get(x.get("lexicon"), x.get("lexicon")),
                        "link": x.get("link")})
    if ((row.get("persona") or {}).get("flag")) == "duplicate_like":
        why.append({"kind": "persona"})
    if not why:
        return None
    best = min(twos, key=lambda n: (-(n.cosine if n.cosine is not None else -1.0), _key(n.kind, n.stem)))
    return {"probably_covered_by": _key(best.kind, best.stem), "n_read_2": len(twos),
            "read_2": sorted(keys), "why": why}
