"""Promotion of accepted registry rows into ``data/seed_queue.json``.

Only an explicit ``gap_registry.py promote`` does this, and nothing here
touches a trait or role file: promotion appends ``status: "candidate"``
entries in the seed-queue shape ``seed_entities.py`` works with (a Roger or
a writer agent later writes the final ``description`` and sets ``ready``).

Refusals: a stem present in the corpus (either entity type), a stem or label
already queued (``seed_entities.build_registry``: existing *and* queued
stems), a row on a holding list (roles, nationalities; physical unless
promoted by name, and states unless the states pass allows it, both below), a
row whose filter verdict is not ``trait`` / ``tagged``, a row with no filter
block, and (with ``min_local_novelty``) a row whose novelty is missing or below
the floor.  ``dry_run`` leaves the queue file byte-identical.

Physical (the physical pass, :mod:`assistant_axis.gapgen.physical_pass`; Roger,
2026-10-09, QUESTIONS 1: "we handle promotion normally, and if promoted they get
the physical tag"): a row on the ``physical`` list is promoted only with
``allow_physical``, which the two paths that name the row pass (``gap_registry.py
promote --keys`` and the review app's ``apply``); the bulk path (``promote
--status accepted``) and any other caller still refuse it.  Its entry carries
the tag ``physical`` (merged with the others), the physical track's section
(read from the queue's physical entries, ``physical_pass.section_for``) unless a
section other than the default is given, and the physical pass's gloss as
``description_draft``.  Every other refusal applies as to any row.

Released states (the states pass v4, :mod:`assistant_axis.gapgen.states_pass`; 2026-10-09): a row the states
pass moved out of the states queue (``holding: "states_released"``: a lasting condition, or a predisposition
under the state's own name, whose gloss the check confirmed) is promoted only with ``allow_released_states``,
which the same two by-name paths pass; the bulk path refuses it.  Its entry carries the tags ``states_pass`` and
``lasting_state`` or ``predisposition``, the pass's gloss as ``description_draft`` and a note of the route
(``states_pass.queue_entry_extras``).  Every other refusal applies as to any row.

States (round 4, replacing round 2's assumption; QUESTIONS 14): a row on the
``states`` list becomes promotable once the states pass
(:mod:`assistant_axis.gapgen.states_pass`) has judged a habitual
predisposition plausible **and** the command is given Roger's confirmed name
for it (``confirmed_state_names`` / CLI ``--confirm-state-name KEY=NAME``):
choosing the name is his step b.  It is promoted under the confirmed name with
the pass's draft gloss as ``description_draft``, tagged ``states_queue``, and
its notes record the pass's suggested name and the confirmed one.  Every
collision check applies to the promoted stem.  A states row with no
judgement, judged implausible, or with no confirmed name is refused.

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
        # when no replacement can be parsed, the quoted decision text speaks for
        # itself (review_rubric_v2.md finding 11: 14 of 18 name it in other words)
        if rep_label:
            msg += f"; replaced by {rep_label}"
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
    # M3's block (coding_plan_m3.md, 2026-10-07) names the traits the candidate may complete as a list,
    # ``pair_completion_for``; the first is the partner (the others go in the notes).  The plan's earlier
    # block shape (a ``pair_completion`` flag beside ``nearest_existing``) is still read.
    pcf = [s for s in nv.get("pair_completion_for") or [] if s]
    if pcf:
        partner = pcf[0]
    else:
        partner = nv.get("nearest_existing") if "pair_completion" in (nv.get("flags") or []) else None
    notes = []
    if f.get("reason"):
        notes.append(f"filter: {f['reason']}")
    if f.get("senses"):
        notes.append("senses: " + "; ".join(f["senses"]))
    if nv.get("nearest_existing"):
        notes.append(f"nearest existing: {nv['nearest_existing']} ({nv.get('decision')})")
    if len(pcf) > 1:
        notes.append(f"pair completion for {', '.join(pcf)} (M3 {nv.get('run_id')}); partner set to the first")
    if nv.get("review"):
        notes.append(f"M3 review: {', '.join(nv['review'])} ({nv.get('decision')}, run {nv.get('run_id')})")
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


def states_promotion(rec: dict, confirmed_name: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    """For a row on the ``states`` holding list: ``(effective, None)`` when
    the states pass judged a habitual predisposition plausible **and** Roger
    has confirmed the name (``confirmed_name``, round 4: choosing the name is
    his step b), where ``effective`` holds the ``stem``, ``label`` and
    ``gloss`` to promote under (the confirmed name, and the pass's draft
    gloss of the predisposition); ``(None, reason)`` otherwise.  The pass's
    suggested name is only a suggestion and is quoted in the refusal."""
    from .normalize import normalize_candidate

    sp = rec.get("states_pass") or {}
    if sp.get("mode") not in (None, "queue") or "plausible" not in sp:
        return None, ("on the states holding list with no states pass judgement yet (run "
                      "states_pass.py --mode queue --holding-states)")
    if sp.get("lasting"):
        return None, (f"on the states holding list; the states pass judged it a lasting condition (route "
                      f"{sp.get('route')}): {sp.get('route_reason') or sp.get('reason')}")
    if not sp.get("plausible"):
        return None, f"on the states holding list; the states pass judged a predisposition implausible: {sp.get('reason')}"
    if not sp.get("gloss"):
        return None, "on the states holding list; the states pass gave no predisposition gloss"
    suggested = sp.get("suggested_name") if sp.get("name_fits") is False and sp.get("suggested_name") else rec["label"]
    if not confirmed_name:
        return None, (f"on the states holding list; the states pass judged a predisposition plausible and "
                      f"suggests the name '{suggested}': Roger must confirm the name first "
                      f"(--confirm-state-name {rec['key']}=<name>)")
    n = normalize_candidate(confirmed_name)
    return {"stem": n.stem, "label": n.label, "gloss": sp["gloss"], "_suggested": suggested}, None


def promote(records: dict[str, dict], queue: dict, keys: Sequence[str], *, data_dir: Path,
            dry_run: bool = True, section: str = DEFAULT_SECTION,
            min_local_novelty: Optional[float] = None, reopen_turned_down: bool = False,
            confirmed_state_names: Optional[dict[str, str]] = None,
            allow_physical: bool = False, allow_released_states: bool = False) -> PromoteReport:
    """Build queue entries for ``keys`` and (unless ``dry_run``) append them
    to ``queue["entries"]`` in place.  ``records`` is the folded registry.
    The caller saves the queue (``seed_entities.save_queue``) and records
    ``seed_queue_stem`` on the promoted rows.  ``allow_physical``: rows on the
    physical holding list may be promoted; ``allow_released_states``: rows the
    states pass released may be (the caller names them; see the module
    docstring)."""
    from data_analysis.seed_entities import build_registry, corpus_stems
    from . import physical_pass as PP
    from . import states_pass as SP

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
        via_states = None
        via_physical = False
        via_released = False
        held_why = None
        if rec.get("holding") == "states":
            eff, held_why = states_promotion(rec, (confirmed_state_names or {}).get(key))
            if eff is not None:
                via_states = {**rec, "_suggested": eff.pop("_suggested")}
                rec = {**rec, **eff}
        elif rec.get("holding") == SP.RELEASED_HOLDING:
            if not SP.is_released(rec):
                held_why = (f"on the {SP.RELEASED_HOLDING} list without a confirmed states-pass gloss (route "
                            f"{SP.route_of(rec)})")
            elif allow_released_states:
                via_released = True
                rec = {**rec, "gloss": rec.get("gloss") or SP.gloss_of(rec)}
            else:
                held_why = (f"released by the states pass ({SP.route_of(rec)}): promoted only by name "
                            f"(gap_registry.py promote --keys, or the review app's apply)")
        elif rec.get("holding") == PP.HOLDING:
            if allow_physical:
                via_physical = True
            else:
                held_why = (f"on the {PP.HOLDING} holding list: promoted only by name (gap_registry.py promote --keys, "
                            f"or the review app's apply)")
        elif rec.get("holding"):
            held_why = f"on the {rec['holding']} holding list (never promoted)"
        stem = rec["stem"]
        old = turned_down.get(stem) or turned_down.get(normalize_to_file_name(rec["label"]))
        if not f:
            rep.refused[key] = "not filtered"
        elif held_why is not None:
            rep.refused[key] = held_why
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
            if via_states is not None:
                sp = via_states["states_pass"]
                note = (f"came through the states queue: state '{via_states['label']}', states pass "
                        f"(rubric v{sp.get('rubric_version')}) judged a habitual predisposition plausible "
                        f"and suggested the name '{via_states['_suggested']}'; name confirmed by Roger as "
                        f"'{rec['label']}': {sp.get('reason')}")
                entry["description_notes"] = " | ".join(x for x in (note, entry.get("description_notes")) if x)
                entry["tags"] = list(dict.fromkeys(entry["tags"] + ["states_queue"]))
                entry["gap_gen"]["states_pass"] = {"state_label": via_states["label"],
                                                   "state_gloss": via_states.get("gloss")}
            if via_physical:
                PP.queue_entry_extras(entry, rec, queue, section=None if section == DEFAULT_SECTION else section)
            if via_released:
                SP.queue_entry_extras(entry, rec)
            if old is not None:  # reopened on purpose: the history travels with the new entry
                history = (f"previously {old.get('status')}: {turned_down_reason(old)}; reopened by "
                           f"promote --reopen-turned-down")
                entry["description_notes"] = " | ".join(x for x in (history, entry.get("description_notes")) if x)
            chosen[key] = entry
    # partner hints: set partner on both entries when both members are promoted
    # (records[key] is the registry row; a states-queue entry's stem may differ)
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
