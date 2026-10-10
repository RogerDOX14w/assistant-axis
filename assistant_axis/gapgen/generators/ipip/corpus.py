"""The corpus and seed-queue names the IPIP generator reads, for reporting and prompt hygiene only.

Nothing that decides a cluster's membership, a pole, or a label reads these (plan 07 § 1: nothing in the pipeline
sees our trait list until the coverage check).  They feed the variant-C ordering column
(:func:`.cluster.nearest_corpus`), the naming prompts' hygiene test (no example word is a corpus or queue name),
the known-analogue check and the census overlap (:mod:`.evaluate`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from assistant_axis.entity_id import default_data_dir, normalize_to_file_name


def corpus_traits(data_dir: Optional[Path] = None) -> dict[str, dict]:
    """``stem -> {"label", "description", "renamed_from"}`` for ``data/traits/instructions/*.json``."""
    d = Path(data_dir or default_data_dir()) / "traits" / "instructions"
    out: dict[str, dict] = {}
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        old = doc.get("renamed_from")             # an object {"stem", "date", "reason"}, a list of them, or a stem
        olds = [o.get("stem") if isinstance(o, dict) else o
                for o in (old if isinstance(old, list) else [old] if old else [])]
        out[p.stem] = {"label": doc.get("positive_label") or p.stem.replace("_", " "),
                       "description": doc.get("description") or "",
                       "renamed_from": [normalize_to_file_name(o) for o in olds if isinstance(o, str) and o]}
    return out


def corpus_embed_texts(traits: dict[str, dict]) -> dict[str, str]:
    """``stem -> "label: description"``, the stored label (embedded text keeps the stored form)."""
    return {s: f"{t['label']}: {t['description']}" for s, t in traits.items() if t.get("description")}


def queue_names(queue_path: Optional[Path] = None, data_dir: Optional[Path] = None) -> set[str]:
    """Every stem and normalised label in ``data/seed_queue.json``, whatever its status or entity type (the
    hygiene rule keeps prompt examples off all of them)."""
    path = Path(queue_path) if queue_path else Path(data_dir or default_data_dir()) / "seed_queue.json"
    if not path.exists():
        return set()
    q = json.loads(path.read_text(encoding="utf-8"))
    out = set()
    for e in q.get("entries", []):
        if e.get("stem"):
            out.add(e["stem"])
        if e.get("label"):
            out.add(normalize_to_file_name(e["label"]))
    return out
