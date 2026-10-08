"""The corpus and queue stems the census table is matched against (evaluation only).

Eligibility never reads these (plan section 1: the generator stays independent of our list);
they fill ``corpus_stem_match`` / ``queue_stem_match`` and the string ceiling.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from assistant_axis.entity_id import default_data_dir, normalize_to_file_name

#: Queue statuses that do not count as a proposed entity (as in ``seed_entities.build_registry``).
DROPPED_QUEUE_STATUSES = ("not_adopted", "superseded")


def corpus_trait_stems(data_dir: Optional[Path] = None) -> set[str]:
    """Stems of ``data/traits/instructions/*.json``."""
    d = Path(data_dir or default_data_dir()) / "traits" / "instructions"
    return {p.stem for p in d.glob("*.json")} if d.exists() else set()


def corpus_renamed_from(data_dir: Optional[Path] = None) -> dict[str, str]:
    """Old stem -> current stem, from the trait files' ``renamed_from`` fields."""
    d = Path(data_dir or default_data_dir()) / "traits" / "instructions"
    out: dict[str, str] = {}
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        old = doc.get("renamed_from")
        for o in ([old] if isinstance(old, str) else old or []):
            out[normalize_to_file_name(o)] = p.stem
    return out


def queue_trait_stems(queue_path: Optional[Path] = None, data_dir: Optional[Path] = None) -> set[str]:
    """Trait stems proposed in ``data/seed_queue.json`` (entries not dropped)."""
    path = Path(queue_path) if queue_path else Path(data_dir or default_data_dir()) / "seed_queue.json"
    if not path.exists():
        return set()
    q = json.loads(path.read_text(encoding="utf-8"))
    out = set()
    for e in q.get("entries", []):
        if e.get("status") in DROPPED_QUEUE_STATUSES:
            continue
        if e.get("entity_type") not in (None, "trait"):
            continue
        if e.get("stem"):
            out.add(e["stem"])
        if e.get("label"):
            out.add(normalize_to_file_name(e["label"]))
    return out
