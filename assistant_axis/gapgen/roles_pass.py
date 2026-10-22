"""The roles pass: the shared role path of plan 16 (gloss and kind stage, M3 for roles, R1, R2, promotion by name).

Coding plan: ``reports/trait_gap_generation/coding_plan_16_role_generators.md`` (2026-10-21, Roger's decisions of
2026-10-21 and 2026-10-22); idea plan ``16_role_generators.md`` § 3.  The role counterpart of
:mod:`assistant_axis.gapgen.physical_pass`.

A **role row** (:func:`is_role_row`) is a registry row on the ``roles`` holding list (M1 tagged it a person or thing,
``role_person`` / ``role_thing``: the 382 held rows of the pilot), or a role-aimed row a generator submitted in role
mode (``Candidate(entity_type="role")``, key ``stem|R#sense``) whose M1 route (``filter.role_route``) is ``role`` or
``both``.  Such a row has no gloss (M1 writes one only for a trait outcome), so the pass begins with a **stage**:

1. the **role gloss** call (rubric ``role_gloss.md``, Haiku 5.5, M1's request settings), one sentence in the role
   corpus's form, "A <label> is someone who ..." / "... is something that ...", for the reading M1 accepted;
2. the **role kind** call (rubric ``role_kind.md``, the system prompt of ``data_analysis/classify_role_kinds.py``
   moved byte for byte, so that a candidate's kind and a corpus role's are measured alike), read three times on the
   gloss and combined by majority (``classify_role_kinds.combine``: a three-way split keeps the first reading's kind
   and says ``kind_split``).

The answers go on the row as its own block, :data:`BLOCK` (``role_pass``), beside the untouched ``filter`` block.
Then M3 against the role corpus (``novelty_score.py score --holding roles``): retrieval over the role descriptions
(:func:`assistant_axis.gapgen.novelty.load_role_corpus`, query form ``role_gloss_w14``), the relation call and the
overlap call on the role rubrics (``relation_roles.md``, ``overlap_concept_roles.md``), a flat cut-off of 3
(:class:`RoleCandidate`: a sub-role is covered by its parent, decision 4), and the nearest traits as information
(``cross_type``, decision 5).  R1 and R2 read a roles batch from its ``pass``; promotion is by name only
(``promote(..., allow_roles=True)``), writing an ``entity_type: "role"`` queue entry (:func:`queue_entry_extras`).

The **kind readout** (decision 2, Roger 2026-10-21): :func:`balance` says, for each of the nine kinds, whether the
corpus as it will be after this review holds it more than 10% above or below the count that keeps its share as on
2026-10-16 (:data:`REFERENCE_KINDS_2026_10_16`); the review card shows the candidate's kind's status and a review
order shows the too-low kinds first.  Information only: nothing is cut.
"""
from __future__ import annotations

import asyncio
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

#: The holding list this pass reads, and the name the pass goes by in blocks and ``run.json``.
HOLDING = "roles"
PASS_NAME = "roles"
#: The registry field holding the stage's answers for a row.
BLOCK = "role_pass"
#: The stage's model: M1's first model (Haiku 5.5), which takes no temperature.
MODEL = "claude-haiku-5-5"
#: The stage's two steps, in order (their rubric names in ``split_rubrics.ROLE_FILES``).
STEPS = ("role_gloss", "role_kind")
STAGE = "role_pass"
#: Three readings of the kind call, combined by majority (a call that decides; judging.md, Roger 2026-10-13).
KIND_READINGS = 3
#: The kind call's ``max_tokens``: classify_role_kinds.py's (Haiku 5.5 thinks adaptively, and the thinking counts).
KIND_MAX_TOKENS = 2000
#: The stage's files in an M3 run directory.
RESPONSES_NAME = "role_pass_responses.jsonl"
RESULTS_NAME = "role_pass.jsonl"
DEFAULT_CONCURRENCY = 4
#: The section of a promoted role's seed-queue entry (idea plan § 3 step 7).
SECTION = "role generators (2026-10)"
#: The cut-off of every role candidate, under every rule set (decision 4 and § 3 step 5): covered at 3 or above.
CUT_OFF = 3


def _kinds():
    import data_analysis.classify_role_kinds as CRK
    return CRK


#: The nine role kinds ``(key, name, definition)``, re-exported from ``classify_role_kinds.py`` (one source).
KINDS: list = _kinds().KINDS
KIND_KEYS: list = [k for k, _, _ in KINDS]

#: Decision 3 (Roger 2026-10-21, open: "TBD"), built as one table and one flag so that the twins TODO can change it:
#: the route of a role-aimed row from the kind call's answer for its most likely reading (M1's step 2 kinds,
#: ``split.KINDS``).  ``role``: the role flow (no holding list: it is where the row was aimed); ``both``: the noun stays a
#: role candidate (kind 8, temperament) and its adjective sibling (:data:`RELABEL_ROLE_AIMED`) is in the trait flow;
#: ``membership``: the membership track (memberships are traits, decisions_m1.md decision 3); ``turned_away``: not
#: in the role flow, M1's tags kept.  A row with no reading (or every primary reading stretched) is turned away.
ROLE_ROUTES: dict[str, str] = {"role": "role", "trait": "both", "membership": "membership", "state": "turned_away",
                               "physical": "turned_away", "action": "turned_away", "evaluative": "turned_away",
                               "not_a_persona": "turned_away"}
ROUTES_VERSION = 1
#: The other half of decision 3: ``"auto"`` gives a role-aimed noun its adjective sibling at submission (the relabel
#: helper, ``registry.submit_candidates``), submitted as a trait; ``None`` turns the sibling off.
RELABEL_ROLE_AIMED: Optional[str] = "auto"
#: The kind counts of the role corpus on 2026-10-16 (``data/roles/role_kinds.json``, Haiku 5.5, three readings), the
#: reference the readout holds each kind's share to (decision 2); ``default.json`` left out (it is ``other``: 4 -> 3).
REFERENCE_KINDS_2026_10_16: dict[str, int] = {
    "occupation": 162, "stance": 47, "non_human": 44, "circumstance": 24, "temperament": 22, "relationship": 20,
    "status": 9, "pastime": 8, "other": 3}
#: "More than 10% above or below the count that keeps the kind's share" (Roger, 2026-10-21).
BALANCE_MARGIN = 0.10
STATUSES = ("too_low", "about_right", "too_high")


# --------------------------------------------------------------------------- reading a row

def route_for(kind_call: Optional[str], *, entity_type: str) -> Optional[str]:
    """The route of a role-aimed row (``entity_type == "role"``) whose most likely reading the kind call gave
    ``kind_call`` (:data:`ROLE_ROUTES`; no kind, as for a row with no reading: ``turned_away``); None for a trait-aimed
    row (its routing is M1's as always)."""
    if entity_type != "role":
        return None
    return ROLE_ROUTES.get(str(kind_call), "turned_away") if kind_call else "turned_away"


def is_role_row(row: Mapping) -> bool:
    """A row the roles pass reads: on the ``roles`` holding list (M1 put it there), or a role-aimed row
    (``entity_type == "role"``) whose M1 route is ``role`` or ``both``."""
    if row.get("holding") == HOLDING:
        return True
    return row.get("entity_type") == "role" and (row.get("filter") or {}).get("role_route") in ("role", "both")


def accepted_reading(row: Mapping) -> Optional[str]:
    """The reading M1 accepted (``filter.judged_sense``, else the sense block's reading at ``accepted_reading``), as
    :func:`physical_pass.accepted_reading` reads it."""
    from .physical_pass import accepted_reading as pp_accepted
    return pp_accepted(row)


def block_of(row: Mapping) -> dict:
    return dict(row.get(BLOCK) or {})


def gloss_of(row: Mapping) -> Optional[str]:
    """The role gloss of the row's ``role_pass`` block (a role row's own ``gloss`` is M1's, null for a role)."""
    g = block_of(row).get("gloss")
    return g.strip() if isinstance(g, str) and g.strip() else None


def kind_of(row: Mapping) -> Optional[str]:
    """The kind the role kind call gave (the majority of its readings), or None."""
    k = block_of(row).get("kind")
    return k if k in KIND_KEYS else None


def human_of(row: Mapping) -> Optional[bool]:
    """Whether the role is a human being: derived from the kind (``kind != "non_human"``), None without one."""
    k = kind_of(row)
    return None if k is None else k != "non_human"


def kind_guess_of(row: Mapping) -> Optional[str]:
    """The first generator's kind guess on the row's sources (provenance; the pipeline acts on :func:`kind_of`)."""
    return next((s.get("kind_guess") for s in row.get("sources") or [] if s.get("kind_guess")), None)


def needs_stage(row: Mapping) -> bool:
    """A role row whose stage has not given it a gloss yet."""
    return is_role_row(row) and gloss_of(row) is None


# --------------------------------------------------------------------------- the kind readout (decision 2)

def balance(current: Mapping[str, int], n_now: int, *, reference: Mapping[str, int] = REFERENCE_KINDS_2026_10_16,
            margin: float = BALANCE_MARGIN) -> dict:
    """The kind readout (coding plan 16, § 6.4).  For each kind: its ``reference`` count and ``share`` of the
    reference total; ``held = share x n_now``, the count that keeps the share at the corpus's size ``n_now``;
    ``count`` (``current``); ``status`` ``too_low`` when ``count < (1 - margin) x held``, ``too_high`` when ``count >
    (1 + margin) x held``, else ``about_right``; ``room = held - count``.  ``order``: the kinds by status (too low,
    about right, too high), then by ``room``, largest first (the order a review shows them in)."""
    total = sum(reference.values())
    if total <= 0:
        raise ValueError("the reference counts sum to zero")
    kinds = {}
    for k in KIND_KEYS:
        ref = int(reference.get(k, 0))
        share = ref / total
        held = share * n_now
        cnt = int(current.get(k, 0))
        if cnt < (1 - margin) * held:
            status = "too_low"
        elif cnt > (1 + margin) * held:
            status = "too_high"
        else:
            status = "about_right"
        kinds[k] = {"reference": ref, "share": round(share, 4), "count": cnt, "held": round(held, 1),
                    "status": status, "room": round(held - cnt, 1)}
    order = sorted(KIND_KEYS, key=lambda k: (STATUSES.index(kinds[k]["status"]), -kinds[k]["room"], k))
    return {"n_now": int(n_now), "reference_total": total, "margin": margin, "kinds": kinds, "order": order}


def kind_status(kind: Optional[str], *, current: Mapping[str, int], n_now: int, **kw) -> Optional[str]:
    """The readout's status of ``kind`` (``too_low``, ``about_right``, ``too_high``), None for no kind."""
    if kind not in KIND_KEYS:
        return None
    return balance(current, n_now, **kw)["kinds"][kind]["status"]


STATUS_WORDS = {"too_low": "too low", "about_right": "about right", "too_high": "too high"}


def kind_readout(kind: Optional[str], bal: Mapping) -> Optional[dict]:
    """The card's readout for ``kind`` under the balance ``bal``: ``{"kind", "status", "count", "held", "margin",
    "text"}`` (``text``: "occupation: too high (171 against 161.6 held at 339)"), None for no kind."""
    if kind not in KIND_KEYS:
        return None
    k = bal["kinds"][kind]
    margin = round(bal["margin"] * k["held"], 1)
    return {"kind": kind, "status": k["status"], "count": k["count"], "held": k["held"], "margin": margin,
            "text": f"{kind}: {STATUS_WORDS[k['status']]} ({k['count']} against {k['held']} held at "
                    f"{bal['n_now']}, margin {margin})"}


def balance_lines(bal: Mapping) -> list[str]:
    """One line per kind, in the readout's order: ``occupation 171 / 168 held (too high)``."""
    return [f"{k} {bal['kinds'][k]['count']} / {bal['kinds'][k]['held']:g} held ({STATUS_WORDS[bal['kinds'][k]['status']]})"
            for k in bal["order"]]


#: The seed-queue statuses at which a role entry is a role in hand that is not yet a role file (as the trait index's
#: ``novelty.QUEUE_SEARCH_STATUSES``): it counts toward the corpus the readout holds kinds against.
LIVE_QUEUE_STATUSES = ("candidate", "ready", "tbd", "backlog")


def queue_entry_kind(entry: Mapping) -> Optional[str]:
    """A role queue entry's kind: its ``gap_gen.role_kind.kind``, else its ``kind:<kind>`` tag."""
    rk = ((entry.get("gap_gen") or {}).get("role_kind") or {}).get("kind")
    if rk in KIND_KEYS:
        return rk
    for t in entry.get("tags") or []:
        if isinstance(t, str) and t.startswith("kind:") and t[5:] in KIND_KEYS:
            return t[5:]
    return None


def corpus_kind_counts(data_dir: Path, queue: Mapping, *, nominees: Iterable[Mapping] = (),
                       kinds_path: Optional[Path] = None) -> tuple[dict, int]:
    """``(counts, n_now)`` of the role corpus as it will be once a review is applied: the role files
    (``default.json`` left out) with their kinds from ``role_kinds.json`` (``kinds_path``; default
    ``<data_dir>/roles/role_kinds.json``); the live role entries of the queue whose stem has no file
    (:data:`LIVE_QUEUE_STATUSES`; kind :func:`queue_entry_kind`); and ``nominees``, registry rows this review
    promotes whose stem is neither (kind :func:`kind_of`).  A role with no kind on record counts in ``n_now`` and
    under ``counts["unknown"]``."""
    data_dir = Path(data_dir)
    files = {p.stem for p in (data_dir / "roles" / "instructions").glob("*.json")} - {"default"}
    kp = Path(kinds_path) if kinds_path else data_dir / "roles" / "role_kinds.json"
    recorded = (json.loads(kp.read_text(encoding="utf-8")).get("roles") or {}) if kp.exists() else {}
    counts: Counter = Counter()
    for s in files:
        k = (recorded.get(s) or {}).get("kind")
        counts[k if k in KIND_KEYS else "unknown"] += 1
    seen = set(files)
    for e in queue.get("entries") or []:
        if e.get("entity_type") != "role" or e.get("status") not in LIVE_QUEUE_STATUSES:
            continue
        s = e.get("stem")
        if not s or s in seen:
            continue
        seen.add(s)
        k = queue_entry_kind(e)
        counts[k if k else "unknown"] += 1
    for r in nominees:
        s = r.get("stem")
        if not s or s in seen:
            continue
        seen.add(s)
        k = kind_of(r)
        counts[k if k else "unknown"] += 1
    return dict(counts), len(seen)
