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
and the tests check both give the same answers on the recorded inputs), the mapping of a
joined row onto the filter block's frozen vocabulary (:func:`to_filter_block`), and the opinions'
agreement section and disagreement tripwire (:func:`agreement_section`,
:func:`disagreement_tripwire`).  The runner is :mod:`assistant_axis.gapgen.split_runner`.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Mapping, Optional, Sequence

from . import plain_reading as pr
from .filter_rubric import MEMBERSHIP_KINDS, _bool, _label_key, _load_json, _num, _rows_of
from .prompt_labels import DEFAULT_LABEL_FORM, prompt_label

#: ``rubric_version`` of every split filter block: 5 means the split (the single classifier's
#: prompt went from version 4 to 6, skipping 5 so that the number names one pipeline).
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
            reading_2: Optional[str] = None, description: Optional[str] = None,
            label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The user message for one call of ``step``: one JSON object with ``"id": 1``, in the shape
    the probe runs sent (``probe_*/probe.py``).  Steps 1 to 3 carry the label and readings of it
    and nothing else: no intended sense, no gloss hint (the blindness of section 1).  ``label`` (as
    stored) is shown in ``label_form`` (:mod:`assistant_axis.gapgen.prompt_labels`: the judge display
    form by default, ``careless (HEXACO)`` -> ``careless (from HEXACO)``); a caller that checks the
    label echo checks it against that shown form."""
    label = prompt_label(label, label_form)
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


def comparison_payload(*, label: str, reading: str, intended: str, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """One pair for the comparison prompt (version 2): the reading from step 1 takes the place of
    the plain reading; the label shown in ``label_form``."""
    return pr.build_compare_prompt([{"id": 1, "label": label, "plain_reading": reading,
                                     "intended_meaning": intended}], label_form=label_form)


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


#: alignment.md draft 3 (2026-09-30) answers a score, 0 to 3.  The filter block keeps the old boolean
#: ``alignment_relevant`` for its readers (corpus regions, review order), derived from the score:
#: true from this score up.  Later work should read the score, ``alignment``.
ALIGNMENT_SCORES = (0, 1, 2, 3)
ALIGNMENT_RELEVANT_FROM = 2


def alignment_relevant_of(score: Optional[int]) -> Optional[bool]:
    """The derived boolean: true for a score of 2 or 3, false for 0 or 1, None for no score."""
    return None if score is None else score >= ALIGNMENT_RELEVANT_FROM


def parse_alignment(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """``{"reason", "alignment"}`` with ``alignment`` a JSON integer 0 to 3 (not a boolean, a string
    or a float); anything else fails validation and is retried once."""
    row, err = _one_row(text)
    if err:
        return None, err
    a = row.get("alignment")
    if _reason(row) is None:
        return None, "reason missing"
    if isinstance(a, bool) or not isinstance(a, int) or a not in ALIGNMENT_SCORES:
        return None, f"alignment {a!r} is not an integer from 0 to 3"
    return {"reason": _reason(row), "alignment": a}, None


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
# the verdict step read several times (coding_plan_haiku55.md, "The switch", item 2)
# ---------------------------------------------------------------------------
#
# Roger, 2026-10-08 ("best of three ... require unanimity on others"; haiku55_readout.md section 5): the
# verdict waves (sense, the established / vague checks, kind, same-sense) run N times per word as
# independent readings, and the word's outcome is combined from the readings' outcomes by
# :func:`combine_readings`.  The outcome of a reading is known after its sense and checks (the same-sense
# check adds a note, the comparison may change the accepted reading but never the outcome), so the vote can
# be taken before wave 3.

#: The rule's name, recorded with every combined verdict.
READINGS_RULE = "turned_away_only_if_unanimous_else_majority"
#: How a combined verdict was reached (``combine_readings``'s ``how``).
READINGS_HOW = ("unanimous", "most_common", "tie_trait", "tie_first")


def combine_readings(outcomes: Sequence[Optional[str]]) -> dict:
    """The combined outcome of independent readings, ``outcomes`` in reading order (None for a reading
    that gave no outcome: its path failed validation twice; it is left out of the vote).

    The rule (Roger, 2026-10-08): the word is **turned away only if every reading turns it away**;
    otherwise the readings that turned it away drop out and the outcome most of the others give wins
    (``most_common``: with three readings, the majority; a single reading left after two turned the word
    away wins alone, the rule's rescue); with no single most common outcome among them (three different
    outcomes, or two readings left that differ), ``trait`` if any reading says trait (``tie_trait``), else
    the outcome of the first reading left (``tie_first``).  A no-majority case therefore never turns a
    word away while some reading did not: "turned away only if every reading turns it away" governs the
    brief's "else the first reading's verdict" when that first reading turned the word away.

    Returns ``{"outcome", "winner", "how", "n", "n_ok", "failed", "outcomes", "n_turned_away",
    "unanimous", "rescued"}``: ``winner`` the 0-based index of the first reading whose outcome is the
    combined one (its answers are the row's: its accepted reading gets the gloss, alignment and
    descriptors), ``failed`` the 0-based indices that gave no outcome, ``unanimous`` true when every
    reading gave an outcome and all gave the same, ``rescued`` true when some reading turned the word away
    and the combined outcome is not turned away.  ``outcome`` and ``winner`` are None when no reading gave
    an outcome."""
    outs = list(outcomes)
    for o in outs:
        if o is not None and o not in OUTCOMES:
            raise ValueError(f"unknown outcome {o!r}")
    ok = [(i, o) for i, o in enumerate(outs) if o is not None]
    failed = [i for i, o in enumerate(outs) if o is None]
    n_away = sum(1 for _, o in ok if o == "turned_away")
    base = {"n": len(outs), "n_ok": len(ok), "failed": failed, "outcomes": outs, "n_turned_away": n_away}
    if not ok:
        return {**base, "outcome": None, "winner": None, "how": None, "unanimous": False, "rescued": False}
    if len({o for _, o in ok}) == 1:
        outcome, how = ok[0][1], "unanimous"
    else:
        rest = [(i, o) for i, o in ok if o != "turned_away"]   # not empty: the outcomes differ
        counts = Counter(o for _, o in rest)
        top = max(counts.values())
        leaders = [o for o, n in counts.items() if n == top]
        if len(leaders) == 1:
            outcome, how = leaders[0], "most_common"
        elif "trait" in counts:
            outcome, how = "trait", "tie_trait"
        else:
            outcome, how = rest[0][1], "tie_first"
    winner = next(i for i, o in ok if o == outcome)
    return {**base, "outcome": outcome, "winner": winner, "how": how,
            "unanimous": how == "unanimous" and not failed,
            "rescued": n_away > 0 and outcome != "turned_away"}


def readings_summary(votes: Sequence[Mapping], *, n_readings: int) -> dict:
    """The summary's ``readings`` section over the words that were voted on (``votes``: one
    :func:`combine_readings` result each, with ``label`` added): how often the readings agreed, the
    rule's rescues (words one or more readings turned away that went on), the ties, the words whose
    combined outcome differs from the first reading's, and the outcome patterns."""
    votes = [v for v in votes if v.get("outcome") is not None]
    n = len(votes)
    how = Counter(v["how"] for v in votes)
    resc = [v for v in votes if v["rescued"]]
    changed = [v for v in votes if v["outcomes"] and v["outcomes"][0] != v["outcome"]]
    patterns = Counter(",".join(str(o) for o in v["outcomes"]) for v in votes)
    per_reading = [dict(sorted(Counter(str(v["outcomes"][i]) for v in votes if len(v["outcomes"]) > i).items()))
                   for i in range(n_readings)]
    return {
        "n_readings": n_readings, "rule": READINGS_RULE, "n_words": n,
        "all_the_same": sum(1 for v in votes if v["unanimous"]),
        "all_the_same_share": _rate(sum(1 for v in votes if v["unanimous"]), n),
        "by_how": {h: how.get(h, 0) for h in READINGS_HOW},
        "turned_away_by_every_reading": sum(1 for v in votes if v["outcome"] == "turned_away"),
        "rescued": {"n": len(resc),
                    "by_n_turned_away": dict(sorted(Counter(str(v["n_turned_away"]) for v in resc).items())),
                    "labels": sorted(v["label"] for v in resc)},
        "ties": {"n": how.get("tie_trait", 0) + how.get("tie_first", 0),
                 "labels": sorted(v["label"] for v in votes if v["how"] in ("tie_trait", "tie_first"))},
        "differs_from_first_reading": {"n": len(changed), "labels": sorted(v["label"] for v in changed)},
        "with_a_failed_reading": {"n": sum(1 for v in votes if v["failed"]),
                                  "labels": sorted(v["label"] for v in votes if v["failed"])},
        "outcomes_by_reading": per_reading,
        "patterns": dict(sorted(patterns.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


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
                    gloss: Optional[str] = None, third_opinion: Optional[Mapping] = None,
                    ) -> tuple[dict, Optional[str], Optional[str], str]:
    """``(filter block, gloss, holding, entity_type)`` for a joined row.  The old keys stay, so the
    readers of the block (promote, gap_registry.py, the states pass) need no change:
    ``judged_sense`` is the accepted reading, ``trait_sense_rank`` its place among the readings,
    ``confidence`` null and ``tag_disagreement`` false.  ``third_opinion`` (``--third-model``) has
    the second opinion's shape plus ``agree_first`` and ``agree_second``; null on a row without one."""
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
        # the score (alignment.md draft 3) is what later work should read; the boolean is derived
        # from it (2 or 3 -> true) and kept for the block's existing readers
        "alignment": (alignment or {}).get("alignment") if row_gloss else None,
        "alignment_relevant": alignment_relevant_of((alignment or {}).get("alignment")) if row_gloss else None,
        "last_step_reasons": {"alignment": (alignment or {}).get("reason"),
                              "descriptors": (descriptors or {}).get("reason")} if row_gloss else None,
        "gloss_form_ok": gloss_form_ok(row_gloss) if row_gloss else None,
        "comparison": dict(comparison) if comparison else None, "plain_reading": None,
        "second_opinion": dict(second_opinion) if second_opinion else None,
        "third_opinion": dict(third_opinion) if third_opinion else None,
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
            "alignment": None, "alignment_relevant": None, "last_step_reasons": None, "gloss_form_ok": None,
            "comparison": None,
            "plain_reading": None, "second_opinion": None, "third_opinion": None, "confidence": None,
            "tag_disagreement": False,
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
    ``:batch`` for the Message Batches API; records before 2026-10-01 say ``@batch`` and are read as
    ``:batch``); records replayed on a resume are counted once."""
    from assistant_axis.judge_pricing import cost_for_usage
    from assistant_axis.gapgen.batches import current_batch_key
    out: dict[str, dict] = {}
    for rec in records:
        raw, model = rec.get("usage_raw") or {}, rec.get("charged_as")
        if not raw or not model:
            continue
        model = current_batch_key(model)
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


# ---------------------------------------------------------------------------
# the opinions: agreement and the disagreement tripwire (Roger, 2026-10-02)
# ---------------------------------------------------------------------------
#
# coding_plan_platform.md, "M1 filter: judging model per generator": each generator's pilot runs the
# filter with a third opinion (``--third-model``, expected Opus) on the second opinion's rows, to
# measure the first and second models against it; later runs keep the second opinion and stop when
# the first and second models disagree on more than ``--max-disagreement`` of the sampled rows
# (opus_audit_m1.md: Haiku and Sonnet disagreed on 1% of corpus labels and 31% of random dictionary
# adjectives).  Agreement is on the final outcome (trait, states, physical, roles, turned_away),
# which the same-sense check never changes (it adds a note only), so it is known once the opinions'
# established, vague and kind answers are in.
#
# An opinion row (from SplitRunner.opinion_rows): {"label", "source_field", "groups", "first",
# "second", "third", "third_run"}; "second" and "third" are outcomes, None where that opinion failed
# (or, for "third", was not run: "third_run" says which).

#: ``--max-disagreement`` default: the share of sampled rows on which the first and second models
#: may disagree before the run stops.
DEFAULT_MAX_DISAGREEMENT = 0.10
#: A rate over fewer sampled rows than this is reported but never trips (overall or by source).
TRIPWIRE_MIN_N = 20


def opinion_source(meta: Optional[Mapping]) -> tuple[Optional[str], list[str]]:
    """``(field, groups)``: where a row came from, for the per-source figures.  A validation row has a
    ``stratum``; a registry row carries the generators of its ``sources[]`` (``meta["generators"]``,
    set by ``filter.items_from_records``; a word two generators found counts under each)."""
    meta = meta or {}
    if meta.get("stratum") is not None:
        return "stratum", [str(meta["stratum"])]
    gens = meta.get("generators")
    if gens:
        return "generator", sorted({str(g) for g in gens})
    return None, []


def _groups(rows: Sequence[Mapping]) -> tuple[Optional[str], dict[str, list[Mapping]]]:
    field = next((r.get("source_field") for r in rows if r.get("source_field")), None)
    by: dict[str, list[Mapping]] = {}
    for r in rows:
        for g in r.get("groups") or []:
            by.setdefault(g, []).append(r)
    return field, dict(sorted(by.items()))


def _rate(k: int, n: int) -> Optional[float]:
    return round(k / n, 4) if n else None


def disagreement_tripwire(rows: Sequence[Mapping], *, threshold: float, min_n: int = TRIPWIRE_MIN_N) -> dict:
    """The tripwire on opinion rows: the first-vs-second disagreement rate on the final outcome, over
    all sampled rows and for each source, trips when it is over ``threshold`` (strictly) on at least
    ``min_n`` compared rows.  Rows whose second opinion failed are left out (``n_failed``).
    ``tripped_by`` names ``"overall"`` and ``"<source_field>:<source>"``."""
    def stat(rs: Sequence[Mapping]) -> dict:
        cmp = [r for r in rs if r.get("second") is not None]
        d = sum(1 for r in cmp if r["second"] != r["first"])
        eligible = len(cmp) >= min_n
        rate = _rate(d, len(cmp))
        return {"n": len(cmp), "disagree": d, "rate": rate, "eligible": eligible,
                "over": bool(eligible and d / len(cmp) > threshold), "n_failed": len(rs) - len(cmp)}

    field, by = _groups(rows)
    overall = stat(rows)
    by_source = {g: stat(rs) for g, rs in by.items()}
    tripped_by = (["overall"] if overall["over"] else []) + [f"{field}:{g}" for g, s in by_source.items() if s["over"]]
    return {"threshold": threshold, "min_n": min_n, "source_field": field, "overall": overall,
            "by_source": by_source, "tripped": bool(tripped_by), "tripped_by": tripped_by}


def agreement_section(rows: Sequence[Mapping], *, models: Mapping[str, Optional[str]]) -> dict:
    """The summary's agreement section on opinion rows: first-vs-second, and with a third opinion
    first-vs-third and second-vs-third, agreement on the final outcome, overall and by source; and,
    with a third opinion, the first-vs-second disagreements by which side the third takes and the
    rows where the first two agree and the third differs (opus_audit_m1.md's two tables; labels
    are listed overall only)."""
    has_third = any(r.get("third_run") for r in rows)

    def pair(rs: Sequence[Mapping], a: str, b: str) -> dict:
        cmp = [r for r in rs if r.get(a) is not None and r.get(b) is not None]
        agree = sum(1 for r in cmp if r[a] == r[b])
        return {"n": len(cmp), "agree": agree, "disagree": len(cmp) - agree, "rate": _rate(agree, len(cmp))}

    def block(rs: Sequence[Mapping], labels: bool) -> dict:
        out = {"n": len(rs), "first_vs_second": pair(rs, "first", "second")}
        if not has_third:
            return out
        out["first_vs_third"] = pair(rs, "first", "third")
        out["second_vs_third"] = pair(rs, "second", "third")
        both = [r for r in rs if r.get("second") is not None and r.get("third") is not None]
        dis = [r for r in both if r["first"] != r["second"]]
        side = {"first": [r["label"] for r in dis if r["third"] == r["first"]],
                "second": [r["label"] for r in dis if r["third"] == r["second"]],
                "neither": [r["label"] for r in dis if r["third"] not in (r["first"], r["second"])]}
        odd = [r["label"] for r in both if r["first"] == r["second"] != r["third"]]
        out["first_second_disagreements"] = {
            "n": len(dis), "third_sides_with_first": len(side["first"]),
            "third_sides_with_second": len(side["second"]), "third_sides_with_neither": len(side["neither"])}
        out["first_second_agree_third_differs"] = {"n": len(odd)}
        if labels:
            out["first_second_disagreements"]["labels"] = {k: sorted(v) for k, v in side.items()}
            out["first_second_agree_third_differs"]["labels"] = sorted(odd)
        return out

    field, by = _groups(rows)
    return {"models": dict(models), "source_field": field, "overall": block(rows, True),
            "by_source": {g: block(rs, False) for g, rs in by.items()},
            "failed": {"second": sum(1 for r in rows if r.get("second") is None),
                       "third": sum(1 for r in rows if r.get("third_run") and r.get("third") is None)}}
