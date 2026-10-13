"""Generator A's input: the five classical tables, typed by hand (plan section 6, "Classical row"; tasks 1 and 2).

One JSON file per scheme under ``data/candidates/structural/classical/``, each a list of rows::

    {"schema_version": 1, "id": "aristotle:courage:excess", "scheme": "aristotle", "item": "rashness",
     "role": "excess", "gloss": "...", "sibling_ids": ["aristotle:courage:deficiency", "aristotle:courage:mean"],
     "source": "Nicomachean Ethics II.7 (Ross); ...", "verified_by": null}

``sibling_ids`` name rows of the same file, both ways (a triple's three rows list each other; a sin and its
contrary virtue list each other; a need's two poles list each other).  ``note`` is optional (the VIA rows say which
names were typed from memory and what alternatives the paper may give).

**The VIA gate** (Roger, 2026-10-12; plan section 1): the 24 strengths with Niemiec's overuse and underuse names
were typed from memory with ``verified_by: null`` and nothing reads them until Roger has checked the 72 names
against the paper and every ``via`` row carries ``verified_by``.  :func:`require_verified` raises
:class:`SchemeUnverified` for a scheme with an unverified row; on the other schemes ``verified_by`` is informational.

:func:`validate` checks what the tables must satisfy (ids unique and of the scheme, roles legal per scheme, siblings
that resolve and are mutual, one mean and two vices per Aristotelian triple, three roles per VIA strength, two poles
per Murray need, a sin's sibling a virtue); it does not check verification, so that ``classical`` can print the VIA
rows' state before they are verified.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from . import CLASSICAL_DIR, SCHEMA_VERSION

SCHEMES: tuple[str, ...] = ("aristotle", "theophrastus", "sins_virtues", "via", "murray")
ROLES_BY_SCHEME: dict[str, tuple[str, ...]] = {
    "aristotle": ("deficiency", "mean", "excess"),
    "theophrastus": ("vice",),
    "sins_virtues": ("sin", "virtue"),
    "via": ("strength", "underuse", "overuse"),
    "murray": ("need_high", "need_low"),
}
#: Schemes whose rows nothing may read until every row carries ``verified_by`` (the VIA gate).
GATED_SCHEMES: tuple[str, ...] = ("via",)
#: How a scheme is named to the modernise call (and in readouts).
SCHEME_NAMES: dict[str, str] = {
    "aristotle": "Aristotle's table of virtues as means between two vices",
    "theophrastus": "Theophrastus, Characters",
    "sins_virtues": "the seven deadly sins and the virtues",
    "via": "the VIA character strengths, with the names for their underuse and overuse",
    "murray": "Murray's list of psychological needs",
}
#: The counts the acceptance test expects (plan section 8): Aristotle 12-14 triples, Theophrastus 30, sins and virtues
#: 7 + 7 + 7, VIA 24 x 3, Murray 20 x 2.
EXPECTED_COUNTS: dict[str, tuple[int, int]] = {"aristotle": (36, 42), "theophrastus": (30, 30),
                                               "sins_virtues": (21, 21), "via": (72, 72), "murray": (40, 40)}


class SchemeUnverified(ValueError):
    """A gated scheme (VIA) has rows without ``verified_by``: nothing may read it yet."""


@dataclass(frozen=True)
class ClassicalRow:
    id: str
    scheme: str
    item: str
    role: str
    gloss: str
    sibling_ids: tuple[str, ...] = ()
    source: Optional[str] = None
    verified_by: Optional[str] = None
    note: Optional[str] = None
    schema_version: int = SCHEMA_VERSION

    @property
    def group(self) -> str:
        """The structure the row belongs to, named by the smallest id among the row and its siblings (siblings are
        mutual, so every member of a triple or a pair gets the same name); the row's own id when it has none."""
        return min((self.id, *self.sibling_ids))

    def as_dict(self) -> dict:
        d = asdict(self)
        d["sibling_ids"] = list(self.sibling_ids)
        if d.get("note") is None:
            d.pop("note")
        return d


def scheme_path(scheme: str, classical_dir: Optional[Path] = None) -> Path:
    if scheme not in SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; one of {', '.join(SCHEMES)}")
    return Path(classical_dir or CLASSICAL_DIR) / f"{scheme}.json"


def _row(d: dict) -> ClassicalRow:
    return ClassicalRow(id=str(d["id"]), scheme=str(d["scheme"]), item=str(d["item"]), role=str(d["role"]),
                        gloss=str(d.get("gloss") or ""), sibling_ids=tuple(d.get("sibling_ids") or ()),
                        source=d.get("source"), verified_by=d.get("verified_by"), note=d.get("note"),
                        schema_version=int(d.get("schema_version") or SCHEMA_VERSION))


def load_classical(scheme: str, *, classical_dir: Optional[Path] = None) -> list[ClassicalRow]:
    """The rows of one scheme's file, in file order (empty when the file is absent)."""
    p = scheme_path(scheme, classical_dir)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{p}: expected a JSON list of rows")
    return [_row(d) for d in raw]


def load_all(schemes: Iterable[str] = SCHEMES, *, classical_dir: Optional[Path] = None) -> list[ClassicalRow]:
    out: list[ClassicalRow] = []
    for s in schemes:
        out.extend(load_classical(s, classical_dir=classical_dir))
    return out


def validate(rows: Sequence[ClassicalRow]) -> list[str]:
    """Problems with the tables (empty when they are well formed); see the module docstring."""
    probs: list[str] = []
    ids = Counter(r.id for r in rows)
    for i, n in ids.items():
        if n > 1:
            probs.append(f"{i}: id used {n} times")
    by_id = {r.id: r for r in rows}
    for r in rows:
        if r.scheme not in SCHEMES:
            probs.append(f"{r.id}: unknown scheme {r.scheme!r}")
            continue
        if not r.id.startswith(r.scheme + ":"):
            probs.append(f"{r.id}: id does not start with its scheme {r.scheme!r}")
        if r.role not in ROLES_BY_SCHEME[r.scheme]:
            probs.append(f"{r.id}: role {r.role!r} is not one of {ROLES_BY_SCHEME[r.scheme]}")
        if not r.item.strip():
            probs.append(f"{r.id}: empty item")
        if not r.gloss.strip():
            probs.append(f"{r.id}: empty gloss")
        for s in r.sibling_ids:
            sib = by_id.get(s)
            if sib is None:
                probs.append(f"{r.id}: sibling {s} does not resolve")
            elif sib.scheme != r.scheme:
                probs.append(f"{r.id}: sibling {s} is in another scheme")
            elif r.id not in sib.sibling_ids:
                probs.append(f"{r.id}: sibling {s} does not list it back")
    groups: dict[str, list[ClassicalRow]] = defaultdict(list)
    for r in rows:
        groups[r.group].append(r)
    for g, members in sorted(groups.items()):
        scheme = members[0].scheme
        roles = Counter(m.role for m in members)
        if scheme == "aristotle":
            if roles != Counter({"deficiency": 1, "mean": 1, "excess": 1}):
                probs.append(f"{g}: an Aristotelian triple needs one mean and two vices (deficiency, excess), "
                             f"has {dict(roles)}")
        elif scheme == "via":
            if roles != Counter({"strength": 1, "underuse": 1, "overuse": 1}):
                probs.append(f"{g}: a VIA strength needs its strength, underuse and overuse rows, has {dict(roles)}")
        elif scheme == "murray":
            if roles != Counter({"need_high": 1, "need_low": 1}):
                probs.append(f"{g}: a Murray need needs a high and a low pole, has {dict(roles)}")
    for r in rows:
        if r.scheme == "sins_virtues" and r.role == "sin":
            if len(r.sibling_ids) != 1 or (by_id.get(r.sibling_ids[0]) or r).role != "virtue":
                probs.append(f"{r.id}: a sin's one sibling is its contrary virtue")
        if r.scheme == "theophrastus" and r.sibling_ids:
            probs.append(f"{r.id}: a Theophrastus character has no siblings")
    return probs


def verification_state(rows: Sequence[ClassicalRow]) -> dict[str, dict]:
    """``{scheme: {"n", "verified", "unverified", "gated"}}``."""
    out: dict[str, dict] = {}
    for s in SCHEMES:
        rs = [r for r in rows if r.scheme == s]
        if not rs:
            continue
        v = sum(1 for r in rs if r.verified_by)
        out[s] = {"n": len(rs), "verified": v, "unverified": len(rs) - v, "gated": s in GATED_SCHEMES}
    return out


def gate_problems(rows: Sequence[ClassicalRow], schemes: Iterable[str] = GATED_SCHEMES) -> list[str]:
    """Why a gated scheme among ``rows`` may not be read (empty when every gated row carries ``verified_by``)."""
    out = []
    for s in schemes:
        bad = [r.id for r in rows if r.scheme == s and not r.verified_by]
        if bad:
            out.append(f"{s}: {len(bad)} of {sum(1 for r in rows if r.scheme == s)} rows have verified_by null "
                       f"(the gate: Roger verifies the names against the paper first; first {bad[0]})")
    return out


def require_verified(rows: Sequence[ClassicalRow], schemes: Optional[Iterable[str]] = None) -> None:
    """Raise :class:`SchemeUnverified` when a gated scheme in ``rows`` (or in ``schemes``) has an unverified row."""
    want = [s for s in GATED_SCHEMES if schemes is None or s in set(schemes)]
    probs = gate_problems(rows, want)
    if probs:
        raise SchemeUnverified("; ".join(probs))


def counts(rows: Sequence[ClassicalRow]) -> dict[str, dict]:
    """``{scheme: {"rows": n, "groups": n, "roles": {role: n}}}``."""
    out: dict[str, dict] = {}
    for s in SCHEMES:
        rs = [r for r in rows if r.scheme == s]
        if rs:
            out[s] = {"rows": len(rs), "groups": len({r.group for r in rs}),
                      "roles": dict(Counter(r.role for r in rs))}
    return out


def siblings_of(row: ClassicalRow, by_id: dict[str, ClassicalRow]) -> list[ClassicalRow]:
    return [by_id[s] for s in row.sibling_ids if s in by_id]


__all__ = ["SCHEMES", "ROLES_BY_SCHEME", "GATED_SCHEMES", "SCHEME_NAMES", "EXPECTED_COUNTS", "ClassicalRow",
           "SchemeUnverified", "scheme_path", "load_classical", "load_all", "validate", "verification_state",
           "gate_problems", "require_verified", "counts", "siblings_of"]
