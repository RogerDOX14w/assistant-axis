"""Promotion of accepted registry rows into ``data/seed_queue.json``.

Only an explicit ``gap_registry.py promote`` does this, and nothing here
touches a trait or role file: promotion appends ``status: "candidate"``
entries in the seed-queue shape ``seed_entities.py`` works with (a Roger or
a writer agent later writes the final ``description`` and sets ``ready``).

Refusals: a stem present in the corpus (either entity type), a stem or label
already queued (``seed_entities.build_registry``: existing *and* queued
stems), a row on a holding list (physical, roles), a row whose filter verdict
is not ``trait`` / ``tagged``, a row with no filter block, and (with
``min_local_novelty``) a row whose novelty is missing or below the floor.
``dry_run`` leaves the queue file byte-identical.

Words already turned down (decision 8 of
``reports/trait_gap_generation/decisions_m1.md``): a stem or label whose
queue entry is ``not_adopted`` or ``superseded`` is refused by default, and
the refusal quotes the entry's ``decision`` text; for ``superseded`` it also
names the replacing label when the decision text gives one.
``reopen_turned_down=True`` (CLI ``--reopen-turned-down``) lets such a word
through and copies the old decision into the new entry's
``description_notes``.  This is promote's own check: the seeding tool's
``seed_entities.build_registry`` still treats those names as free (it needs
to, for renames), and is not changed.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name

DEFAULT_SECTION = "trait-gap generators (2026-09)"
DEFAULT_CHUNK = "gap"
TURNED_DOWN = ("not_adopted", "superseded")

_REPLACED_BY = (
    re.compile(r"superseded by (?:the )?`?([A-Za-z][A-Za-z_\-]*)`?(?=\s*(?:\(|,|;|\.|$))", re.I),
    re.compile(r"`([A-Za-z][A-Za-z_\-]*)` in place of this label", re.I),
)


def replacing_label(decision: str) -> Optional[str]:
    """The label a ``superseded`` entry's decision text names as its
    replacement, if it names one in a recognisable form."""
    for pat in _REPLACED_BY:
        m = pat.search(decision or "")
        if m:
            return m.group(1)
    return None


def turned_down_entries(queue: dict) -> dict[str, dict]:
    """Stem (and normalised label) -> the ``not_adopted`` / ``superseded``
    queue entry that turned it down (the last one when there are several)."""
    out: dict[str, dict] = {}
    for e in queue.get("entries") or []:
        if e.get("status") not in TURNED_DOWN:
            continue
        for name in (e.get("stem"), normalize_to_file_name(e["label"]) if e.get("label") else None):
            if name:
                out[name] = e
    return out


def turned_down_reason(entry: dict) -> str:
    status = entry.get("status")
    decision = " ".join((entry.get("decision") or "").split()) or "(no decision text recorded)"
    msg = f"turned down in the seed queue ({status}): {decision}"
    if status == "superseded":
        rep_label = replacing_label(entry.get("decision") or "")
        msg += f"; replaced by {rep_label}" if rep_label else "; no replacing label recorded in its decision text"
    return msg


@dataclass
class PromoteReport:
    promoted: list[str] = field(default_factory=list)          # registry keys
    refused: dict[str, str] = field(default_factory=dict)      # key -> reason
    entries: list[dict] = field(default_factory=list)          # queue entries built
    dry_run: bool = True


def _generators(rec: dict) -> list[str]:
    return list(dict.fromkeys(s.get("generator") for s in rec.get("sources") or [] if s.get("generator")))


def queue_entry_from_record(rec: dict, *, section: str = DEFAULT_SECTION) -> dict:
    """The seed-queue entry for one registry row (``status: "candidate"``).

    ``description_draft`` is the filter's gloss; ``description`` stays empty
    until the entry is reviewed.  ``partner`` comes from the novelty block's
    ``pair_completion`` flag (its ``nearest_existing``) or is set later by
    :func:`promote` from ``partner_hint`` when both members are promoted.
    """
    f = rec.get("filter") or {}
    nv = rec.get("novelty") or {}
    gens = _generators(rec)
    tags = ["gap_gen"] + [f"source:{g}" for g in gens] + [t for t in f.get("tags") or [] if t]
    partner = nv.get("nearest_existing") if "pair_completion" in (nv.get("flags") or []) else None
    notes = []
    if f.get("reason"):
        notes.append(f"filter: {f['reason']}")
    if f.get("senses"):
        notes.append("senses: " + "; ".join(f["senses"]))
    if nv.get("nearest_existing"):
        notes.append(f"nearest existing: {nv['nearest_existing']} ({nv.get('decision')})")
    return {
        "stem": rec["stem"], "label": rec["label"], "entity_type": rec.get("entity_type") or "trait",
        "chunk": DEFAULT_CHUNK, "sub_chunk": gens[0] if gens else None,
        "pairing": "pair" if partner else "singleton", "partner": partner, "partner_exists": bool(partner),
        "arrangement_members": None, "description_draft": rec.get("gloss"),
        "description_notes": " | ".join(notes) or None, "description": None, "source": None,
        "tags": list(dict.fromkeys(tags)), "status": "candidate", "decision": None, "alternatives": [],
        "section": section, "lines": None,
        "gap_gen": {"registry_key": rec["key"], "sources": [f"{s.get('generator')}/{s.get('run_id')}"
                                                            for s in rec.get("sources") or []],
                    "region": f.get("region"), "rubric_version": f.get("rubric_version")},
    }


def _local_novelty(rec: dict) -> Optional[float]:
    sig = (rec.get("novelty") or {}).get("signals") or {}
    vals = [s.get("local") for s in sig.values() if isinstance(s, dict) and s.get("local") is not None]
    return min(vals) if vals else None


def promote(records: dict[str, dict], queue: dict, keys: Sequence[str], *, data_dir: Path,
            dry_run: bool = True, section: str = DEFAULT_SECTION,
            min_local_novelty: Optional[float] = None, reopen_turned_down: bool = False) -> PromoteReport:
    """Build queue entries for ``keys`` and (unless ``dry_run``) append them
    to ``queue["entries"]`` in place.  ``records`` is the folded registry.
    The caller saves the queue (``seed_entities.save_queue``) and records
    ``seed_queue_stem`` on the promoted rows."""
    from data_analysis.seed_entities import build_registry, corpus_stems

    rep = PromoteReport(dry_run=dry_run)
    corpus = set().union(*corpus_stems(data_dir).values())
    taken = build_registry(queue, data_dir)
    turned_down = turned_down_entries(queue)
    chosen: dict[str, dict] = {}
    for key in keys:
        rec = records.get(key)
        if rec is None:
            rep.refused[key] = "not in registry"
            continue
        f = rec.get("filter")
        stem = rec["stem"]
        old = turned_down.get(stem) or turned_down.get(normalize_to_file_name(rec["label"]))
        if not f:
            rep.refused[key] = "not filtered"
        elif rec.get("holding"):
            rep.refused[key] = f"on the {rec['holding']} holding list (never promoted)"
        elif f.get("verdict") not in ("trait", "tagged"):
            rep.refused[key] = f"filter verdict {f.get('verdict')}"
        elif stem in corpus:
            rep.refused[key] = "stem exists in the corpus"
        elif stem in taken or normalize_to_file_name(rec["label"]) in taken:
            rep.refused[key] = "stem already in the seed queue"
        elif old is not None and not reopen_turned_down:
            rep.refused[key] = turned_down_reason(old) + " (pass --reopen-turned-down to reopen it)"
        elif rec.get("seed_queue_stem"):
            rep.refused[key] = f"already promoted as {rec['seed_queue_stem']}"
        elif stem in {c["stem"] for c in chosen.values()}:
            rep.refused[key] = "another sense of this stem is promoted in this batch"
        elif min_local_novelty is not None and (_local_novelty(rec) is None
                                                or _local_novelty(rec) < min_local_novelty):
            rep.refused[key] = f"local novelty {_local_novelty(rec)} below {min_local_novelty}"
        else:
            entry = queue_entry_from_record(rec, section=section)
            if old is not None:  # reopened on purpose: the history travels with the new entry
                history = (f"previously {old.get('status')}: {turned_down_reason(old)}; reopened by "
                           f"promote --reopen-turned-down")
                entry["description_notes"] = " | ".join(x for x in (history, entry.get("description_notes")) if x)
            chosen[key] = entry
    # partner hints: set partner on both entries when both members are promoted
    by_stem = {e["stem"]: e for e in chosen.values()}
    for key, e in chosen.items():
        for s in records[key].get("sources") or []:
            hint = s.get("partner_hint")
            if not hint:
                continue
            p = normalize_to_file_name(hint)
            if p in by_stem and p != e["stem"]:
                for a, b in ((e, by_stem[p]), (by_stem[p], e)):
                    a["partner"], a["pairing"], a["partner_exists"] = b["stem"], "pair", False
    rep.promoted = list(chosen)
    rep.entries = [copy.deepcopy(e) for e in chosen.values()]
    if not dry_run:
        queue.setdefault("entries", []).extend(copy.deepcopy(e) for e in chosen.values())
    return rep
