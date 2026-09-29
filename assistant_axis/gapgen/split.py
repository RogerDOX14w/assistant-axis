"""The split trait-hood filter: pure functions (no API call, no I/O).

Specification: ``reports/trait_gap_generation/coding_plan_split.md`` sections 6 and 7.  The single
classifier prompt is replaced by small calls, each with its own rubric (Roger's text, read from
``reports/trait_gap_generation/rubrics/`` by :mod:`split_rubrics`), each carrying one item:

1. **sense** (the label only): first thought, and the readings of "You are <label>.", ranked,
   each primary or secondary;
2. for each primary reading: **established** (how established the reading is; does the first
   thought get in its way), **vague** (does the label leave something out; does the reading fit
   many people in different ways) and **kind** (trait, membership, state, physical, role, action,
   evaluative, not_a_persona);
3. **same_sense**, only for a word with two readings left by rule 2 that are both trait or
   membership; and the **comparison** (plain_reading.COMPARISON_PROMPT, version 2, unchanged) of
   an intended sense with each reading left by rule 2, one pair per call;
4. **gloss**, for a word that goes on as a trait;
5. **alignment** and **descriptors** on the gloss.

This module holds one parser and validator for each step (``parse_<step>``, each returning
``(row, None)`` or ``(None, error)``), the payload of each call (:func:`payload`), the join
(:func:`join`, the rules of section 6; ``split_reference/join_reference.py`` is the same rule
and the tests check both give the same answers on the recorded inputs), and the mapping of a
joined row onto the filter block's frozen vocabulary (:func:`to_filter_block`).  The runner is
:mod:`assistant_axis.gapgen.split_runner`.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Mapping, Optional, Sequence

from . import plain_reading as pr
from .filter_rubric import MEMBERSHIP_KINDS, _bool, _label_key, _load_json, _num, _rows_of

#: ``rubric_version`` of every split filter block: 5 means the split (the single classifier's
#: prompt is at version 4).
RUBRIC_VERSION = 5
PIPELINE = "split"

KINDS = ("trait", "membership", "state", "physical", "role", "action", "evaluative", "not_a_persona")
#: step2_kind.md lists "religion" as a membership kind beside the nine of the single classifier.
SPLIT_MEMBERSHIP_KINDS = tuple(MEMBERSHIP_KINDS) + ("religion",)
ESTABLISHED = ("well_known", "known", "from_parts", "stretched")
SAID_OF = ("people", "things", "actions", "abstractions")
RANKS = ("primary", "secondary")
SAME_SENSE = ("same", "shade", "different")
#: descriptors.md: the seven regions (the single classifier's two for states and physical
#: features are left out, since those words never reach that call).
SPLIT_REGIONS = ("communication_style", "cognitive_epistemic", "moral_stance", "social_interpersonal",
                 "emotional_temperament", "alignment_ai_agent", "identity_demographic")

ON = frozenset({"trait", "membership"})
QUEUE = {"state": "states", "physical": "physical", "role": "roles"}
OUTCOMES = ("trait", "states", "physical", "roles", "turned_away")

#: The steps of one word's path, in wave order; every step is one call per item.
STEPS = ("probe", "sense", "established", "vague", "kind", "same_sense", "comparison", "gloss", "alignment",
         "descriptors")
#: Steps the second opinion repeats on the second model (steps 1 to 3 of the path).
SECOND_OPINION_STEPS = ("sense", "established", "vague", "kind", "same_sense")


# ---------------------------------------------------------------------------
# payloads: the user message of each call (one item, id 1)
# ---------------------------------------------------------------------------

def payload(step: str, *, label: str, reading: Optional[str] = None, first_thought: Optional[str] = None,
            reading_2: Optional[str] = None, description: Optional[str] = None) -> str:
    """The user message for one call of ``step``: one JSON object with ``"id": 1``, in the shape
    the probe runs sent (``probe_*/probe.py``).  Steps 1 to 3 carry the label and readings of it
    and nothing else: no intended sense, no gloss hint (the blindness of section 1)."""
    if step == "sense":
        send: dict = {"id": 1, "label": label}
    elif step == "established":
        send = {"id": 1, "label": label, "first_thought": first_thought, "reading": reading}
    elif step in ("vague", "kind", "gloss"):
        send = {"id": 1, "label": label, "reading": reading}
    elif step == "same_sense":
        send = {"id": 1, "label": label, "reading_1": reading, "reading_2": reading_2}
    elif step in ("alignment", "descriptors"):
        send = {"id": 1, "label": label, "description": description}
    else:
        raise ValueError(f"no payload for step {step!r} (probe and comparison use their own builders)")
    return json.dumps(send, ensure_ascii=False)


def comparison_payload(*, label: str, reading: str, intended: str) -> str:
    """One pair for the comparison prompt (version 2): the reading from step 1 takes the place of
    the plain reading."""
    return pr.build_compare_prompt([{"id": 1, "label": label, "plain_reading": reading,
                                     "intended_meaning": intended}])


# ---------------------------------------------------------------------------
# parsers: one per step, (row, None) or (None, error)
# ---------------------------------------------------------------------------

def _one_row(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """The single row of a one-item answer (``{"results": [{"id": 1, ...}]}``)."""
    if not text or not text.strip():
        return None, "empty response"
    try:
        rows = _rows_of(_load_json(text))
    except (ValueError, json.JSONDecodeError) as exc:
        return None, f"unparseable response: {exc}"
    rows = [r for r in rows if isinstance(r, dict)]
    if not rows:
        return None, "no row"
    with_id = [r for r in rows if _num(r.get("id"), float("-inf"), float("inf"), integer=True) == 1]
    row = with_id[0] if with_id else (rows[0] if len(rows) == 1 and "id" not in rows[0] else None)
    if row is None:
        return None, "no row with id 1"
    return row, None


def _text(v: Any) -> Optional[str]:
    return " ".join(v.split()) if isinstance(v, str) and v.strip() else None


def _choice(v: Any, allowed: Sequence[str]) -> Optional[str]:
    s = str(v or "").strip().lower()
    return s if s in allowed else None


def parse_sense(text: Optional[str], label: str) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    if _label_key(row.get("label")) != _label_key(label):
        return None, f"label echo {row.get('label')!r} does not match {label!r}"
    note, first = _text(row.get("note")), _text(row.get("first_thought"))
    said = _choice(row.get("first_thought_said_of"), SAID_OF)
    usable = _bool(row.get("usable"))
    if note is None:
        return None, "note missing"
    if first is None:
        return None, "first_thought missing"
    if said is None:
        return None, f"first_thought_said_of {row.get('first_thought_said_of')!r} not in {SAID_OF}"
    if usable is None:
        return None, "usable missing or not a boolean"
    raw = row.get("readings")
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        return None, "readings is not a list"
    readings = []
    for x in raw:
        if not isinstance(x, dict) or _text(x.get("reading")) is None:
            return None, f"reading {x!r} has no text"
        rank = _choice(x.get("rank"), RANKS)
        if rank is None:
            return None, f"rank {x.get('rank')!r} not in {RANKS}"
        readings.append({"reading": _text(x["reading"]), "rank": rank})
    return {"label": row.get("label"), "note": note, "first_thought": first, "first_thought_said_of": said,
            "readings": readings, "usable": usable}, None


def _reason(row: dict) -> Optional[str]:
    return _text(row.get("reason"))


def parse_established(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    est = _choice(row.get("established"), ESTABLISHED)
    way = _bool(row.get("first_thought_in_the_way"))
    if _reason(row) is None:
        return None, "reason missing"
    if est is None:
        return None, f"established {row.get('established')!r} not in {ESTABLISHED}"
    if way is None:
        return None, "first_thought_in_the_way missing or not a boolean"
    return {"reason": _reason(row), "established": est, "first_thought_in_the_way": way}, None


def parse_vague(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    left, many = _bool(row.get("leaves_something_out")), _bool(row.get("fits_many_in_different_ways"))
    if _reason(row) is None:
        return None, "reason missing"
    if left is None:
        return None, "leaves_something_out missing or not a boolean"
    if many is None:
        return None, "fits_many_in_different_ways missing or not a boolean"
    missing = _text(row.get("missing"))
    if missing is not None and missing.lower() in ("null", "none"):
        missing = None
    return {"reason": _reason(row), "leaves_something_out": left, "missing": missing,
            "fits_many_in_different_ways": many}, None


def parse_kind(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    kind = _choice(row.get("kind"), KINDS)
    if _reason(row) is None:
        return None, "reason missing"
    if kind is None:
        return None, f"kind {row.get('kind')!r} not in {KINDS}"
    mk = row.get("membership_kind")
    mk = mk.strip().lower() if isinstance(mk, str) and mk.strip().lower() not in ("", "null", "none") else None
    if kind == "membership":
        if mk not in SPLIT_MEMBERSHIP_KINDS:
            return None, f"membership_kind {row.get('membership_kind')!r} not in {SPLIT_MEMBERSHIP_KINDS}"
    else:
        mk = None
    return {"reason": _reason(row), "kind": kind, "membership_kind": mk}, None


def parse_same_sense(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    rel = _choice(row.get("relation"), SAME_SENSE)
    if _reason(row) is None:
        return None, "reason missing"
    if rel is None:
        return None, f"relation {row.get('relation')!r} not in {SAME_SENSE}"
    return {"reason": _reason(row), "relation": rel}, None


def parse_gloss(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    g = _text(row.get("gloss"))
    if g is None:
        return None, "gloss missing"
    return {"gloss": g, "form_ok": gloss_form_ok(g)}, None


def parse_alignment(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    a = _bool(row.get("alignment_relevant"))
    if _reason(row) is None:
        return None, "reason missing"
    if a is None:
        return None, "alignment_relevant missing or not a boolean"
    return {"reason": _reason(row), "alignment_relevant": a}, None


def parse_descriptors(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    row, err = _one_row(text)
    if err:
        return None, err
    region = _choice(row.get("region"), SPLIT_REGIONS)
    enact = _num(row.get("enactable_in_text"), 0, 2, integer=True)
    if _reason(row) is None:
        return None, "reason missing"
    if region is None:
        return None, f"region {row.get('region')!r} not in {SPLIT_REGIONS}"
    if enact is None:
        return None, "enactable_in_text missing or out of range"
    return {"reason": _reason(row), "region": region, "enactable_in_text": int(enact)}, None


def parse_probe(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    from .filter_rubric import parse_probe as fr_parse_probe
    rows, errs = fr_parse_probe(text or "", [1])
    return (rows[1], None) if 1 in rows else (None, errs.get(1, "missing"))


def parse_comparison(text: Optional[str], label: str) -> tuple[Optional[dict], Optional[str]]:
    rows, errs = pr.parse_compare(text or "", [1], labels={1: label})
    return (rows[1], None) if 1 in rows else (None, errs.get(1, "missing"))


PARSERS = {"established": parse_established, "vague": parse_vague, "kind": parse_kind,
           "same_sense": parse_same_sense, "gloss": parse_gloss, "alignment": parse_alignment,
           "descriptors": parse_descriptors, "probe": parse_probe}


def parse(step: str, text: Optional[str], *, label: str) -> tuple[Optional[dict], Optional[str]]:
    """Dispatch to the step's parser (sense and comparison need the label echo)."""
    if step == "sense":
        return parse_sense(text, label)
    if step == "comparison":
        return parse_comparison(text, label)
    return PARSERS[step](text)


_GLOSS_FORM = re.compile(r"^This means [A-Za-z'-]+ing\b")


def gloss_form_ok(gloss: Optional[str]) -> bool:
    """True when the gloss opens "This means" followed at once by an -ing verb (gloss.md)."""
    return bool(_GLOSS_FORM.match(gloss or ""))


# ---------------------------------------------------------------------------
# the join (section 6)
# ---------------------------------------------------------------------------

def _est(x: Mapping) -> Optional[str]:
    return (x.get("check_established") or {}).get("established")


def _kind(x: Mapping) -> Optional[str]:
    return (x.get("kind_call") or {}).get("kind")


def primary_indices(sense: Mapping) -> list[int]:
    return [i for i, x in enumerate(sense.get("readings") or []) if x.get("rank") == "primary"]


def survivors(sense: Mapping) -> list[int]:
    """Indices of the primary readings left by rule 2 (not called "stretched")."""
    rs = sense.get("readings") or []
    return [i for i in primary_indices(sense) if _est(rs[i]) != "stretched"]


def same_sense_pair(sense: Mapping) -> Optional[tuple[int, int]]:
    """The two readings the same-sense check is asked about: the first two readings left by rule 2
    that are both trait or membership; None when there are fewer than two."""
    rs = sense.get("readings") or []
    on = [i for i in survivors(sense) if _kind(rs[i]) in ON]
    return (on[0], on[1]) if len(on) >= 2 else None


def join(sense: Mapping, same_sense: Optional[str] = None,
         comparisons: Optional[Mapping[int, Optional[str]]] = None) -> dict:
    """The rules of section 6 on one word's answers.

    ``sense`` is step 1's answer, each primary reading carrying ``check_established``,
    ``kind_call`` and (when asked) ``check_vague`` (the shape of the probe records).
    ``same_sense`` is the same-sense check's answer ("same", "shade", "different" or None).
    ``comparisons`` (only for a row with an intended sense) maps each reading left by rule 2 to
    the comparison's relation with the intended sense, None where the call failed.

    Returns ``{"outcome", "cause", "rule", "accepted", "accepted_index", "kind", "membership_kind",
    "same_sense", "established", "vague_asked", "notes", "comparison_effect"}``; ``accepted_index``
    is the 0-based index in ``sense["readings"]``.  Rules 1 and 2 turn a word away; rules 3 to 5
    send it on; the checks add notes and decide nothing else."""
    rs = list(sense.get("readings") or [])
    base = {"accepted": None, "accepted_index": None, "kind": None, "membership_kind": None, "same_sense": None,
            "established": None, "vague_asked": False, "comparison_effect": None}
    prim = primary_indices(sense)
    if not prim:
        return {**base, "outcome": "turned_away", "cause": "no_reading", "rule": 1, "notes": []}
    surv = survivors(sense)
    if not surv:
        return {**base, "outcome": "turned_away", "cause": "stretched", "rule": 2, "notes": []}
    notes: list[str] = []
    if surv[0] != prim[0]:
        notes.append("most_likely_reading_stretched")
    first = surv[0]
    on = [i for i in surv if _kind(rs[i]) in ON]
    # the accepted reading by rules 3 to 5
    if _kind(rs[first]) in ON:
        acc = first
    elif on:
        acc = on[0]
    elif _kind(rs[first]) in QUEUE:
        acc = first
    else:
        acc = None
    effect, comp_note = None, None
    if comparisons is not None:
        rel = {i: comparisons.get(i) for i in surv}
        if any(v is None for v in rel.values()):
            effect = "incomplete"
        elif acc is not None and rel[acc] == "same":
            effect = "same"
        elif any(rel[i] == "same" for i in on):
            acc = next(i for i in on if rel[i] == "same")
            effect = "switched"
        elif acc is not None and rel[acc] == "related":
            effect, comp_note = "related", "reading_related"
        else:
            effect, comp_note = "overshadowed", "overshadowed"
    if acc is None:
        if comp_note:
            notes.append(comp_note)
        return {**base, "outcome": "turned_away", "cause": _kind(rs[first]), "rule": 5, "notes": notes,
                "comparison_effect": effect}
    if _kind(rs[acc]) in ON:
        outcome = "trait"
        rule = 3 if acc == first else 4
        if _kind(rs[first]) not in ON:
            notes.append("obvious_sense_not_trait")
        if len(on) > 1 and same_sense == "different":
            notes.append("two_trait_senses")
        if (any(_kind(rs[i]) in QUEUE for i in surv if i != acc)
                and "obvious_sense_not_trait" not in notes):
            notes.append("nontrait_person_sense")
    else:
        outcome, rule = QUEUE[_kind(rs[acc])], 5
    x = rs[acc]
    if (x.get("check_established") or {}).get("first_thought_in_the_way"):
        notes.append("first_thought_in_the_way")
    vague = x.get("check_vague") or {}
    for k in ("leaves_something_out", "fits_many_in_different_ways"):
        if vague.get(k):
            notes.append(k)
    if comp_note:
        notes.append(comp_note)
    return {"outcome": outcome, "cause": None, "rule": rule, "accepted": x["reading"], "accepted_index": acc,
            "kind": _kind(x), "same_sense": same_sense if len(on) > 1 else None,
            "membership_kind": (x.get("kind_call") or {}).get("membership_kind"),
            "established": _est(x), "vague_asked": bool(vague), "notes": notes, "comparison_effect": effect}


# ---------------------------------------------------------------------------
# the filter block (section 6, "Mapping onto the frozen vocabulary")
# ---------------------------------------------------------------------------

#: A turned-away word's cause -> its tag.
REJECT_TAG = {"no_reading": "no_persona_reading", "not_a_persona": "no_persona_reading", "stretched": "stretched",
              "action": "action", "evaluative": "evaluative_only"}
QUEUE_TAG = {"states": "state", "physical": "physical", "roles": "role_person"}
NATIONALITY_KIND = "nationality_ethnicity_language"


def verdict_tags_holding(outcome: str, *, cause: Optional[str] = None, membership_kind: Optional[str] = None
                         ) -> tuple[str, list[str], Optional[str], str]:
    """``(verdict, tags, holding, entity_type)`` for a joined outcome (the table of section 6)."""
    if outcome == "trait":
        if membership_kind:
            hold = "nationalities" if membership_kind == NATIONALITY_KIND else None
            return "trait", ["membership"], hold, "trait"
        return "trait", [], None, "trait"
    if outcome in QUEUE_TAG:
        return "tagged", [QUEUE_TAG[outcome]], outcome, "role" if outcome == "roles" else "trait"
    if outcome == "turned_away":
        tag = REJECT_TAG.get(str(cause))
        return "reject", [tag] if tag else [], None, "trait"
    raise ValueError(f"unknown outcome {outcome!r}")


def _person_kind(kind: Optional[str]) -> Optional[str]:
    return "trait" if kind in ON else kind


def block_readings(sense: Mapping) -> list[dict]:
    """The readings as the block records them: each with its checks flattened."""
    out = []
    for x in sense.get("readings") or []:
        est, kc, vg = x.get("check_established"), x.get("kind_call"), x.get("check_vague")
        out.append({"reading": x.get("reading"), "rank": x.get("rank"),
                    "established": (est or {}).get("established"),
                    "first_thought_in_the_way": (est or {}).get("first_thought_in_the_way"),
                    "kind": (kc or {}).get("kind"), "membership_kind": (kc or {}).get("membership_kind"),
                    "vague": None if not vg else {k: vg.get(k) for k in ("leaves_something_out", "missing",
                                                                         "fits_many_in_different_ways")},
                    "reasons": {"established": (est or {}).get("reason"), "vague": (vg or {}).get("reason"),
                                "kind": (kc or {}).get("reason")}})
    return out


def block_reason(sense: Mapping, j: Mapping) -> Optional[str]:
    """The reason recorded on the block: the kind call's reason for the reading that decided."""
    rs = sense.get("readings") or []
    if j["cause"] == "no_reading":
        return f"No reading about the persona. {sense.get('note') or ''}".strip()
    if j["cause"] == "stretched":
        prim = primary_indices(sense)
        why = (rs[prim[0]].get("check_established") or {}).get("reason") if prim else None
        return f"Every primary reading is stretched. {why or ''}".strip()
    idx = j["accepted_index"] if j["accepted_index"] is not None else (survivors(sense) or [None])[0]
    if idx is None:
        return None
    return (rs[idx].get("kind_call") or {}).get("reason")


def to_filter_block(*, sense: Optional[Mapping], j: Mapping, model: str, batch_id: str, now: str,
                    step_versions: Mapping[str, int], prompt_sha256: Mapping[str, str],
                    same_sense: Optional[Mapping] = None, comparison: Optional[Mapping] = None,
                    gloss_model: Optional[str] = None, alignment: Optional[Mapping] = None,
                    descriptors: Optional[Mapping] = None, second_opinion: Optional[Mapping] = None,
                    gloss: Optional[str] = None) -> tuple[dict, Optional[str], Optional[str], str]:
    """``(filter block, gloss, holding, entity_type)`` for a joined row.  The old keys stay, so the
    readers of the block (promote, gap_registry.py, the states pass) need no change:
    ``judged_sense`` is the accepted reading, ``trait_sense_rank`` its place among the readings,
    ``confidence`` null and ``tag_disagreement`` false."""
    sense = sense or {}
    verdict, tags, holding, et = verdict_tags_holding(j["outcome"], cause=j.get("cause"),
                                                      membership_kind=j.get("membership_kind"))
    notes = list(j.get("notes") or [])
    acc = j.get("accepted_index")
    prim = primary_indices(sense)
    rs = sense.get("readings") or []
    row_gloss = gloss if j["outcome"] == "trait" else None
    block = {
        "pipeline": PIPELINE, "rubric_version": RUBRIC_VERSION, "step_versions": dict(step_versions),
        "model": model, "gloss_model": gloss_model if row_gloss else None, "batch_id": batch_id,
        "same_sense": (same_sense or {}).get("relation"),
        "same_sense_detail": dict(same_sense) if same_sense else None,
        "outcome": j["outcome"], "cause": j.get("cause"), "rule": j.get("rule"), "verdict": verdict, "tags": tags,
        "membership_kind": j.get("membership_kind") if verdict == "trait" else None,
        "reason": block_reason(sense, j),
        "sense": {k: sense.get(k) for k in ("note", "first_thought", "first_thought_said_of", "usable")}
        | {"readings": block_readings(sense)},
        "accepted_reading": None if acc is None else acc + 1,
        "judged_sense": j.get("accepted"), "trait_sense_rank": None if acc is None else acc + 1,
        "senses": [x.get("reading") for x in rs],
        "person_senses": [{"sense": rs[i].get("reading"), "kind": _person_kind(_kind(rs[i]))} for i in prim
                          if _kind(rs[i])],
        "trait_senses_equally_obvious": "two_trait_senses" in notes,
        "notes": notes, "polysemy": bool(notes), "polysemy_notes": notes,
        "region": (descriptors or {}).get("region") if row_gloss else None,
        "enactable_in_text": (descriptors or {}).get("enactable_in_text") if row_gloss else None,
        "alignment_relevant": (alignment or {}).get("alignment_relevant") if row_gloss else None,
        "last_step_reasons": {"alignment": (alignment or {}).get("reason"),
                              "descriptors": (descriptors or {}).get("reason")} if row_gloss else None,
        "gloss_form_ok": gloss_form_ok(row_gloss) if row_gloss else None,
        "comparison": dict(comparison) if comparison else None, "plain_reading": None,
        "second_opinion": dict(second_opinion) if second_opinion else None,
        "confidence": None, "tag_disagreement": False, "validator_repairs": [], "gloss_in_band": None,
        "prompt_sha256": dict(prompt_sha256), "at": now,
    }
    return block, row_gloss, holding, et


def floor_block(*, why: str, rule: str, model: Optional[str], batch_id: str, now: str,
                step_versions: Mapping[str, int], prompt_sha256: Mapping[str, str]) -> dict:
    """The block of a word cut by the frequency floor (``rule`` "floor") or the definition probe
    (``rule`` "probe"): turned away with the tag ``too_rare``, before step 1."""
    return {"pipeline": PIPELINE, "rubric_version": RUBRIC_VERSION, "step_versions": dict(step_versions),
            "model": model, "gloss_model": None, "batch_id": batch_id, "same_sense": None, "same_sense_detail": None,
            "outcome": "turned_away", "cause": rule, "rule": rule, "verdict": "reject", "tags": ["too_rare"],
            "membership_kind": None, "reason": why, "sense": None, "accepted_reading": None, "judged_sense": None,
            "trait_sense_rank": None, "senses": [], "person_senses": [], "trait_senses_equally_obvious": False,
            "notes": [], "polysemy": False, "polysemy_notes": [], "region": None, "enactable_in_text": None,
            "alignment_relevant": None, "last_step_reasons": None, "gloss_form_ok": None, "comparison": None,
            "plain_reading": None, "second_opinion": None, "confidence": None, "tag_disagreement": False,
            "validator_repairs": [], "gloss_in_band": None, "prompt_sha256": dict(prompt_sha256), "at": now}


# ---------------------------------------------------------------------------
# the pilot's recorded targets (section 10)
# ---------------------------------------------------------------------------

def pilot_figures(results: Sequence[Mapping], expected: Optional[Mapping[str, Mapping]] = None) -> dict:
    """The section-10 figures from rows of ``results.jsonl`` (dicts).  ``expected`` maps a label to
    its row of ``expected_outcomes.jsonl``; without it the row's ``meta["expected"]`` (an outcome
    name) is used.  Words cut by the floor or the probe are listed apart."""
    cut, reached, diffs, n_same = [], 0, [], 0
    counts: Counter = Counter()
    glosses = [r.get("gloss") for r in results if (r.get("filter") or {}).get("outcome") == "trait"]
    for r in results:
        f = r.get("filter") or {}
        if f.get("rule") in ("floor", "probe"):
            cut.append({"label": r["label"], "rule": f["rule"], "reason": f.get("reason")})
            continue
        if not f:
            continue
        reached += 1
        counts[f["outcome"]] += 1
        exp = (expected or {}).get(r["label"]) or {}
        meta = r.get("meta") or {}
        e_out = exp.get("outcome") or (meta.get("expected") if isinstance(meta.get("expected"), str) else None)
        if e_out is None:
            continue
        if e_out == f["outcome"]:
            n_same += 1
        else:
            diffs.append({"label": r["label"], "expected": e_out,
                          "expected_reading": exp.get("accepted") or meta.get("expected_reading"),
                          "got": f["outcome"], "got_reading": f.get("judged_sense"), "cause": f.get("cause")})
    return {"n": len(results), "n_reached_step1": reached, "outcomes": dict(sorted(counts.items())),
            "same_outcome_as_expected": n_same, "differences": diffs, "cut_before_step1": cut,
            "glosses": len(glosses), "glosses_form_ok": sum(1 for g in glosses if gloss_form_ok(g))}


def cost_by_step(records: Sequence[Mapping]) -> dict[str, dict]:
    """Spend by step, from the response records (``responses.jsonl``): ``{"<stage>@<charged model>":
    {"n_calls", "prompt_tokens", "completion_tokens", "cost_usd"}}``.  A record carries the billed
    usage it was charged (``usage_raw``) and the model key it was charged under (``charged_as``, with
    ``@batch`` for the Message Batches API); records replayed on a resume are counted once."""
    from assistant_axis.judge_pricing import cost_for_usage
    out: dict[str, dict] = {}
    for rec in records:
        raw, model = rec.get("usage_raw") or {}, rec.get("charged_as")
        if not raw or not model:
            continue
        p = int(raw.get("input_tokens") or 0) + int(round(1.25 * (raw.get("cache_creation_input_tokens") or 0)
                                                           + 0.1 * (raw.get("cache_read_input_tokens") or 0)))
        o = int(raw.get("output_tokens") or 0)
        d = out.setdefault(f"{rec.get('stage')}@{model}", {"n_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                                                           "cost_usd": 0.0})
        d["n_calls"] += 1
        d["prompt_tokens"] += p
        d["completion_tokens"] += o
        d["cost_usd"] += cost_for_usage(model, p, o)
    for d in out.values():
        d["cost_usd"] = round(d["cost_usd"], 6)
    return dict(sorted(out.items()))
