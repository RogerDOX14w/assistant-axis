"""The corpus and queue traits M3 compared a candidate with, read from its registry row, as the review app shows them.

The review app's corpus panel (``review_app.decisions.ReviewState.neighbourhood``) lists every corpus trait and
seed-queue entry an M3 block lists or reads, opposed ones apart, by final reading (Opus's where Opus read, else
Sonnet's; unread last) and then cosine, each with its reading as "Sonnet/Opus" (``3/3``, ``2/-``).  Roger's marking
sheets show the same list (QUESTIONS 208 (4), 2026-10-20: "as many neighbours as the review tool does"), compactly:
``[rude](...) (3/2), [shy](...) (2/-), overmasculine (queued, 1/-), [quiet](...) (unrelated)``.  A seed-queue entry
(``queue_status`` on M3's listed or read entry) is shown as queued and never linked as a trait file: the pilot sheet
linked the queue entry *overmasculine* to a trait file that does not exist.

The narrow pass (:mod:`assistant_axis.gapgen.narrow_pass`) reads the same entries for its candidates and parents:
:func:`best_value` (the higher of the two models' readings) and :func:`final_value` (Opus's, else Sonnet's).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional

__all__ = ["Neighbour", "reading_values", "final_value", "best_value", "neighbours", "neighbours_text",
           "trait_href"]


def _int(v) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def reading_values(rd: Optional[Mapping]) -> tuple[Optional[int], Optional[int]]:
    """``(Sonnet's value, Opus's value)`` of one M3 overlap reading (None where that model did not read, or a
    non-integer answer such as ``unsure``)."""
    rd = rd or {}
    out = []
    for m in ("sonnet", "opus"):
        x = rd.get(m)
        out.append(_int(x.get("value")) if isinstance(x, Mapping) else _int(x))
    return out[0], out[1]


def final_value(rd: Optional[Mapping]) -> Optional[int]:
    """The deciding value: Opus's where Opus read, else Sonnet's."""
    s, o = reading_values(rd)
    return o if o is not None else s


def best_value(rd: Optional[Mapping]) -> Optional[int]:
    """The higher of the two models' values (QUESTIONS 208: "best overlap reading, by either model")."""
    vs = [v for v in reading_values(rd) if v is not None]
    return max(vs) if vs else None


@dataclass
class Neighbour:
    stem: str
    kind: str                       # "corpus" | "queue"
    relation: Optional[str]
    cosine: Optional[float]
    sonnet: Optional[int] = None
    opus: Optional[int] = None
    read: bool = False              # M3's overlap call read the pair
    reading: Optional[Mapping] = None

    @property
    def final(self) -> Optional[int]:
        return self.opus if self.opus is not None else self.sonnet

    @property
    def best(self) -> Optional[int]:
        vs = [v for v in (self.sonnet, self.opus) if v is not None]
        return max(vs) if vs else None

    @property
    def reading_text(self) -> Optional[str]:
        """``3/2`` or ``2/-`` (the review app's form); None when the pair was not read."""
        if not self.read:
            return None
        return f"{self.sonnet}/{self.opus if self.opus is not None else '-'}"


def neighbours(row: Mapping, *, opposed: bool = False) -> list[Neighbour]:
    """Every corpus trait and queue entry the row's M3 block lists or reads, once each, in the review app's order:
    final reading (unread last), then cosine, then stem.  ``opposed``: the opposed ones instead (by cosine)."""
    nv = (row or {}).get("novelty") or {}
    read = {r["stem"]: r for r in nv.get("readings") or [] if isinstance(r, Mapping) and r.get("stem")}
    listed = {x["stem"]: x for x in nv.get("listed") or [] if isinstance(x, Mapping) and x.get("stem")}
    out: list[Neighbour] = []
    for stem in dict.fromkeys([*listed, *read]):
        x, r = listed.get(stem) or {}, read.get(stem)
        rel = x.get("relation") or (r or {}).get("relation")
        if (rel == "opposed") != opposed:
            continue
        queued = bool(x.get("queue_status") or (r or {}).get("queue_status"))
        s, o = reading_values(r)
        cos = x.get("cosine") if x.get("cosine") is not None else (r or {}).get("cosine")
        out.append(Neighbour(stem=stem, kind="queue" if queued else "corpus", relation=rel, cosine=cos, sonnet=s,
                             opus=o, read=r is not None and "stalled" not in r, reading=r))
    if opposed:
        return sorted(out, key=lambda n: (-(n.cosine or 0.0), n.stem))
    return sorted(out, key=lambda n: (-(n.final if n.final is not None else -1), -(n.cosine or 0.0), n.stem))


def _md(s) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ")


def neighbours_text(row: Mapping, *, href: Callable[[str], Optional[str]],
                    label: Optional[Callable[[str], str]] = None, empty: str = "none read") -> str:
    """The sheet's neighbours cell (module docstring): each corpus trait linked by ``href(stem)`` (plain text when it
    gives None: no such trait file), each queue entry shown as ``(queued, ...)`` and never linked, each with its
    reading, or its relation when M3 did not read the pair.  ``label(stem)``: the display name (default the stem with
    spaces)."""
    parts = []
    for n in neighbours(row):
        name = _md(label(n.stem) if label else n.stem.replace("_", " "))
        what = n.reading_text or (n.relation or "listed")
        if n.kind == "queue":
            parts.append(f"{name} (queued, {what})")
            continue
        h = href(n.stem)
        parts.append((f"[{name}]({h})" if h else f"{name} (no trait file)") + f" ({what})")
    return ", ".join(parts) or empty


def trait_href(prefix: str, traits_dir: Optional[Path] = None) -> Callable[[str], Optional[str]]:
    """``href`` for :func:`neighbours_text`: ``<prefix><stem>.json``; with ``traits_dir``, None for a stem with no
    trait file there."""
    def h(stem: str) -> Optional[str]:
        if traits_dir is not None and not (Path(traits_dir) / f"{stem}.json").exists():
            return None
        return f"{prefix}{stem}.json"
    return h
