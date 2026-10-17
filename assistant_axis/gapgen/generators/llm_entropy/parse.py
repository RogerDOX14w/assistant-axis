"""Reading the model's replies (plan section 5, ``parse.py``; section 8, ``parse``).

* :func:`parse_reply`: one generating call's reply, the scaffold's schema (``approach`` first, then ``items``), or
  the multilingual one (two more fields per item).  A reply that is not one JSON object with an ``items`` list does
  not parse (the call is asked once more); an empty list parses, with no items (a spelling constraint may fit
  nothing).
* :func:`validate_item`: one item.  **Invalid** (dropped, counted in ``n_invalid``): not an object, no label, a label
  with a comma (two names joined: "joyless, rarely happy"; the IPIP naming rule of 2026-10-13).  Everything else is
  kept, with a note where it falls short: a gloss that does not open "This means" or runs past 25 words, a ``kind``
  outside M1's vocabulary (kept as ``None``), a ``probability`` outside [0, 1] (kept as ``None``).
* :func:`label_problem`: the label rule (the alignment sweep's: more than four words, an underscore, non-ASCII, a
  surface that does not normalise).  An item that breaks it is **kept in the table** with its ``label_problem`` and
  never submitted; the rule's bite is reported.  For family c the rule reads the back-translated English label,
  never the original.
* :func:`parse_backtranslation`: the back-translation call's reply, matched to the items it was given by ``index``
  (by position when an entry has none); a reply that drops items is counted, not refused.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from assistant_axis.gapgen.generators.alignment_sweep.extract import label_problem as _sweep_label_problem
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.judge import extract_json_blob

#: M1's kind vocabulary (``step2_kind.md``), which the scaffold's ``kind`` field uses.
KINDS: tuple[str, ...] = ("trait", "membership", "state", "physical", "role", "action", "evaluative", "not_a_persona")
MAX_LABEL_WORDS = 4
MAX_GLOSS_WORDS = 25
GLOSS_OPENING = "this means"
#: Version of the parser's rules (recorded on every response record): a change that keeps or drops other items is a
#: bump.
PARSER_VERSION = 1


def _json_object(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    if text is None:
        return None, "no response"
    if not str(text).strip():
        return None, "empty response"
    blob = extract_json_blob(text)
    if not blob or "{" not in blob:
        return None, "no JSON object"
    try:
        d = json.loads(blob)
    except json.JSONDecodeError:
        try:
            from assistant_axis.judge import _repair_json_blob  # the platform's repair of a "+1"-style number
            d = json.loads(_repair_json_blob(blob))
        except Exception:  # noqa: BLE001 - no repair helper, or it did not help
            return None, "JSON does not parse"
    if not isinstance(d, dict):
        return None, "not a JSON object"
    return d, None


def label_problem(label: Any) -> Optional[str]:
    """Why ``label`` breaks the label rule, or None: empty, an underscore, non-ASCII, more than four words (a
    hyphenated compound is one word), no stem, or a surface the registry's normalisation refuses."""
    why = _sweep_label_problem(label)
    if why is not None:
        return why
    try:
        normalize_candidate(label)
    except ValueError:
        return "does not normalise"
    return None


def _str_or_none(v: Any) -> Optional[str]:
    if not isinstance(v, str):
        return None
    s = " ".join(v.split())
    return None if not s or s.lower() in ("null", "none", "n/a", "-") else s


def _bool_or_none(v: Any) -> Optional[bool]:
    if isinstance(v, bool):
        return v
    if isinstance(v, str) and v.strip().lower() in ("true", "false"):
        return v.strip().lower() == "true"
    return None


def gloss_notes(gloss: Optional[str], *, english: bool = True) -> list[str]:
    """Notes on a gloss (never a rejection): missing, not opening "This means" (English glosses only), over 25
    words."""
    if not gloss:
        return ["no gloss"]
    notes = []
    if english and not gloss.lower().startswith(GLOSS_OPENING):
        notes.append("gloss does not open 'This means'")
    if len(gloss.split()) > MAX_GLOSS_WORDS:
        notes.append(f"gloss over {MAX_GLOSS_WORDS} words")
    return notes


def validate_item(d: Any, *, multilingual: bool = False) -> tuple[Optional[dict], Optional[str]]:
    """``(item, None)`` or ``(None, why it is invalid)`` (module docstring).  The item: ``label`` (lower-cased, its
    whitespace collapsed; for family c the original label as given), ``gloss``, ``antonym``, ``kind``,
    ``ambiguity_flag``, ``probability`` (or None), and for family c ``romanization`` and ``english_hint``; ``notes``
    lists what fell short."""
    if not isinstance(d, Mapping):
        return None, "not an object"
    raw = d.get("label")
    if not isinstance(raw, str) or not raw.strip():
        return None, "no label"
    label = " ".join(raw.split())
    if "," in label or "，" in label or "、" in label or "،" in label:
        return None, "label with a comma"
    notes: list[str] = []
    if not multilingual and label != label.lower():
        notes.append("label lower-cased")
        label = label.lower()
    gloss = _str_or_none(d.get("gloss"))
    notes += gloss_notes(gloss, english=not multilingual)
    antonym = _str_or_none(d.get("antonym"))
    if antonym is not None and not multilingual:
        antonym = antonym.lower()
    kind = d.get("kind")
    kind = kind.strip().lower().replace(" ", "_").replace("-", "_") if isinstance(kind, str) else None
    if kind not in KINDS:
        if d.get("kind") is not None:
            notes.append(f"kind {str(d.get('kind'))[:30]!r} outside M1's vocabulary")
        kind = None
    prob = d.get("probability")
    if prob is not None:
        if isinstance(prob, bool) or not isinstance(prob, (int, float)) or not 0.0 <= float(prob) <= 1.0:
            notes.append("probability outside [0, 1]")
            prob = None
        else:
            prob = float(prob)
    item = {"label": label, "gloss": gloss, "antonym": antonym, "kind": kind,
            "ambiguity_flag": _bool_or_none(d.get("ambiguity_flag")), "probability": prob}
    if multilingual:
        item["romanization"] = _str_or_none(d.get("romanization"))
        item["english_hint"] = _str_or_none(d.get("english_hint"))
    item["notes"] = notes
    return item, None


@dataclass
class Reply:
    """A parsed reply: ``approach`` (the reason, or None), the valid ``items`` in order, and the invalid ones'
    reasons (``invalid``)."""
    approach: Optional[str]
    items: list = field(default_factory=list)
    invalid: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def n_invalid(self) -> int:
        return len(self.invalid)


def parse_reply(text: Optional[str], *, multilingual: bool = False) -> tuple[Optional[Reply], Optional[str]]:
    """``(Reply, None)`` or ``(None, why it does not parse)``."""
    d, err = _json_object(text)
    if d is None:
        return None, err
    items = d.get("items")
    if not isinstance(items, list):
        return None, "no items list"
    approach = _str_or_none(d.get("approach"))
    rep = Reply(approach=approach)
    if approach is None:
        rep.notes.append("no approach")
    elif list(d)[0] != "approach":
        rep.notes.append("approach not first")
    for raw in items:
        it, why = validate_item(raw, multilingual=multilingual)
        if it is None:
            label = raw.get("label") if isinstance(raw, Mapping) else None
            rep.invalid.append({"label": label if isinstance(label, str) else None, "why": why})
        else:
            rep.items.append(it)
    return rep, None


@dataclass
class BackTranslation:
    """The back-translation of one (c) answer: ``by_index`` (1-based, the items given) -> ``{romanization, label,
    gloss, antonym, listicle, notes}``; ``n_expected``, ``n_returned``, ``missing`` (indices with no entry) and
    ``extra`` (entries for no item)."""
    by_index: dict = field(default_factory=dict)
    n_expected: int = 0
    n_returned: int = 0
    missing: list = field(default_factory=list)
    extra: int = 0


def parse_backtranslation(text: Optional[str], n_expected: int) -> tuple[Optional[BackTranslation], Optional[str]]:
    """``(BackTranslation, None)`` or ``(None, why it does not parse)``.  An entry is matched by its ``index``
    (1-based); an entry without a usable index takes its position.  The English label is lower-cased and must be a
    string; an entry without one is left out and its item counted missing."""
    d, err = _json_object(text)
    if d is None:
        return None, err
    items = d.get("items")
    if not isinstance(items, list):
        return None, "no items list"
    bt = BackTranslation(n_expected=int(n_expected), n_returned=len(items))
    for pos, e in enumerate(items, 1):
        if not isinstance(e, Mapping):
            continue
        idx = e.get("index")
        idx = int(idx) if isinstance(idx, int) and not isinstance(idx, bool) else pos
        label = _str_or_none(e.get("label"))
        if label is None:
            continue
        if not 1 <= idx <= n_expected or idx in bt.by_index:
            bt.extra += 1
            continue
        gloss = _str_or_none(e.get("gloss"))
        antonym = _str_or_none(e.get("antonym"))
        bt.by_index[idx] = {"romanization": _str_or_none(e.get("romanization")), "label": label.lower(),
                            "gloss": gloss, "antonym": antonym.lower() if antonym else None,
                            "listicle": _bool_or_none(e.get("listicle")), "notes": gloss_notes(gloss)}
    bt.missing = [i for i in range(1, n_expected + 1) if i not in bt.by_index]
    return bt, None


_TAG_RE = {name: re.compile(rf"<{name}>\s*(.*?)\s*</{name}>", re.S) for name in ("note", "system", "user_template",
                                                                                 "domains")}


def parse_tagged(text: Optional[str], *, need: tuple[str, ...] = ("system", "user_template", "domains")
                 ) -> tuple[Optional[dict], Optional[str]]:
    """The translation calls' tag-delimited answer (``<note>``, ``<system>``, ``<user_template>``, ``<domains>``,
    one ``id: text`` line per domain) as ``{"note", "system", "user_template", "domains": {id: text}}``; ``(None,
    why)`` when a needed part is missing."""
    if not text:
        return None, "no response"
    out: dict = {}
    for name, rx in _TAG_RE.items():
        m = rx.search(text)
        if m:
            out[name] = m.group(1)
    missing = [n for n in need if n not in out]
    if missing:
        return None, f"missing <{'>, <'.join(missing)}>"
    if "domains" in out:
        doms = {}
        for line in out["domains"].splitlines():
            k, sep, v = line.partition(":")
            if sep and k.strip() and v.strip():
                doms[k.strip()] = v.strip()
        out["domains"] = doms
    return out, None


__all__ = ["KINDS", "MAX_LABEL_WORDS", "MAX_GLOSS_WORDS", "PARSER_VERSION", "label_problem", "gloss_notes",
           "validate_item", "Reply", "parse_reply", "BackTranslation", "parse_backtranslation", "parse_tagged"]
