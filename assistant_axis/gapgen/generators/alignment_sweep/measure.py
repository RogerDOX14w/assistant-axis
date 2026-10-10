"""Mechanical measures of one extraction round, for iterating the extraction prompt (plan 08 § 10).

The pilot's draft 1 was wrong in five ways at once, and each has a cheap mechanical check here, so a draft's
effect is visible before anyone reads the items:

* :func:`volume` -- pairs per chunk (the plan expects 1 to 2.5) and the label word-count distribution.  Draft 1
  gave 5.9 pairs per answered chunk and almost no one-word labels, where 775 of the corpus's 932 trait labels are
  one word.
* :func:`gloss_form` -- the share of glosses in the corpus's own form: ``This means`` followed at once by an
  ``-ing`` verb, and no subject (``rubrics/gloss.md``, and the "Description-writing rules for new seeds" section
  of the ``trait-pairs`` rule).  Every one of draft 1's 330 glosses was in the first person.
* :func:`label_shape` -- the share of labels that name a step in a procedure rather than a disposition, by two
  tells: an opening verb from :data:`PROCEDURE_VERBS`, and a sequencing word (``before``, ``first``, ``then``).
  Both are only tells, so a hand reading of a sample goes beside the number.
* :func:`vice_shape` -- the share of vice poles that say something beyond the virtue's absence.  A pole counts as
  absence-shaped when its gloss negates and otherwise repeats its partner's (content-word overlap at
  :data:`ABSENCE_OVERLAP` or above), or its label itself is a negation.  ``or``-joined poles are counted here too
  (draft 1 gave ``bluffs or shuts down``, ``pads or truncates``).
* :func:`near_duplicates` -- label-level near duplicates inside the round, without an embedding call: poles of the
  same kind whose labels share a head word, or whose content words overlap at :data:`DUP_OVERLAP` or above.  The
  gloss-embedding dedup (``dedupe.py`` at its recorded threshold) is the measure of record; this one is free, runs
  on labels rather than glosses, and catches what that one misses at a safe threshold.

:func:`measure_all` returns every number for one round and :func:`round_table` renders a Markdown table across
rounds, which is what the readout carries.  Nothing here calls an API.
"""
from __future__ import annotations

import collections
import re
from typing import Iterable, Mapping, Optional, Sequence

from .extract import Item

#: Verbs that open the name of a step in a procedure rather than of a disposition.  Draft 1's ``asks before
#: expanding``, ``confirms plan first``, ``cites sources``, ``waits for clear signs``.
PROCEDURE_VERBS: frozenset[str] = frozenset("""
announces asks checks cites confirms consults documents double-checks escalates flags labels logs notifies
numbers obtains pauses proceeds records reports requests seeks signs spares submits summarizes verifies waits
writes
""".split())

#: Words that mark a label as a position in a sequence: ``asks before expanding``, ``confirms plan first``.
SEQUENCING_WORDS: frozenset[str] = frozenset("first before after then once upfront beforehand".split())

#: Words and contractions that make a gloss a negation rather than a description.
NEGATION_WORDS: frozenset[str] = frozenset("""
not never no none nothing nobody without fails fail failing neglects neglecting omits omitting skips skipping
doesn't don't won't can't isn't
""".split())

#: Subjects a gloss must not have (the corpus form has none; ``one's`` is the possessive it uses).  Calibrated on
#: the corpus: a third-person pronoun for *other people* ("judging people by their age", "taking people at their
#: word") is in 114 of the 932 descriptions, so ``they``, ``their``, ``he``, ``she``, ``his``, ``her`` are not
#: faults; only the persona in the first or second person is.
GLOSS_SUBJECTS: frozenset[str] = frozenset("i me my mine you your yours we us our ours".split())

#: Phrases that name the persona in the third person instead of leaving the sentence without a subject.
PERSONA_RE = re.compile(r"\bthe (?:assistant|persona|model|AI)\b", re.I)

#: How many words after "This means" an ``-ing`` verb may start: the corpus puts an adverb or a negation first
#: ("This means readily adjusting", "This means never paying", "This means not caring").
ING_WITHIN = 5

#: Report vocabulary a gloss must not use (``trait-pairs`` rule, "Inside voice").  ``engage`` and ``navigate`` are
#: matched only in the phrases the rule names, since "engaging with a thought experiment" is the persona's own word.
REPORT_RE = re.compile(r"\b(exhibit(?:s|ing|ed)?|demonstrat(?:es|ing|ed)?"
                       r"|engag(?:es|ing|ed) in|navigat(?:es|ing|ed) the|individuals who)\b", re.I)

#: A label that joins two qualities instead of naming one disposition: ``cold and dismissive``, ``deflects or
#: overreaches``.  Draft 2's grouping instruction produced these, so the count is a measure of its cost.
JOINED_RE = re.compile(r"\b(?:and|or)\b", re.I)

#: Content-word overlap at or above which a negating vice gloss counts as its partner's absence.
ABSENCE_OVERLAP = 0.4
#: Content-word overlap at or above which two labels of the same pole count as near duplicates.
DUP_OVERLAP = 0.6

_STOP = frozenset("""
a an and the this that those these of to for in on at by with from into about as is are be being been it its
one ones s t means what who whom which when where while if then than so or not no nor but
""".split())

_WORD = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")


def _words(text: Optional[str]) -> list[str]:
    return [w.lower() for w in _WORD.findall(text or "")]


def _content(text: Optional[str]) -> set[str]:
    """Content words of a text: no stop words, no negations, stems folded crudely so that ``saying`` and ``says``
    meet (the comparison is between a gloss and its partner's, which are written in the same voice)."""
    out = set()
    for w in _words(text):
        if w in _STOP or w in NEGATION_WORDS:
            continue
        for suf in ("ing", "es", "ed", "s"):
            if len(w) > len(suf) + 3 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.add(w)
    return out


def _overlap(a: set[str], b: set[str]) -> float:
    """The share of the smaller set that the two share (0.0 when either is empty)."""
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def _share(n: int, total: int) -> Optional[float]:
    return round(n / total, 4) if total else None


# --------------------------------------------------------------------------- the five measures


def kept_poles(items: Sequence[Item]) -> list[Item]:
    """The poles a round would submit: kept, and not a mechanism pole awaiting its rewrite."""
    return [it for it in items if it.kept]


def volume(items: Sequence[Item], *, n_chunks: int) -> dict:
    """Pairs per chunk, and the label word-count distribution (the corpus: 775 of 932 labels one word)."""
    pairs = [it for it in items if it.names_source and it.rewritten_from is None]
    chunks = {it.chunk_id for it in items}
    poles = kept_poles(items)
    lens = collections.Counter(len(it.label.split()) for it in poles)
    return {"n_chunks": n_chunks, "n_chunks_with_items": len(chunks), "n_pairs": len(pairs),
            "n_kept_poles": len(poles),
            "pairs_per_chunk": round(len(pairs) / n_chunks, 3) if n_chunks else None,
            "pairs_per_answered_chunk": round(len(pairs) / len(chunks), 3) if chunks else None,
            "label_words": {str(k): lens[k] for k in sorted(lens)},
            "one_word_label_share": _share(lens[1], len(poles))}


def gloss_problems(gloss: str) -> list[str]:
    """Why ``gloss`` is not in the corpus's form, or ``[]``: the opening, a subject, the persona named in the third
    person, report vocabulary.  Calibrated so that the corpus's own descriptions pass (see the constants)."""
    out = []
    ws = _words(gloss)
    if not (gloss or "").strip().startswith("This means"):
        out.append("no This means")
    elif not any(w.endswith("ing") for w in ws[2:2 + ING_WITHIN]):
        out.append("no -ing verb after This means")
    if any(w in GLOSS_SUBJECTS for w in ws):
        out.append("has a subject")
    if PERSONA_RE.search(gloss or ""):
        out.append("names the persona")
    if REPORT_RE.search(gloss or ""):
        out.append("report vocabulary")
    return out


def gloss_form(items: Sequence[Item]) -> dict:
    """The share of kept poles' glosses in the corpus form, and a count per failure."""
    poles = kept_poles(items)
    probs = {it.item_id: gloss_problems(it.gloss) for it in poles}
    why: collections.Counter = collections.Counter()
    for v in probs.values():
        why.update(v)
    ok = [k for k, v in probs.items() if not v]
    first_person = sum(1 for it in poles if any(w in {"i", "me", "my", "mine"} for w in _words(it.gloss)))
    return {"n_poles": len(poles), "n_corpus_form": len(ok), "corpus_form_share": _share(len(ok), len(poles)),
            "first_person": first_person, "first_person_share": _share(first_person, len(poles)),
            "why_not": dict(why)}


def label_step_tells(label: str) -> list[str]:
    """Why ``label`` reads as a step in a procedure rather than a disposition, or ``[]``."""
    ws = _words(label)
    out = []
    if ws and ws[0] in PROCEDURE_VERBS:
        out.append("procedure verb")
    if any(w in SEQUENCING_WORDS for w in ws):
        out.append("sequencing word")
    return out


def label_shape(items: Sequence[Item]) -> dict:
    """The share of kept poles whose label names a disposition rather than a step, by the two tells."""
    poles = kept_poles(items)
    tells = {it.item_id: label_step_tells(it.label) for it in poles}
    step = [k for k, v in tells.items() if v]
    why: collections.Counter = collections.Counter()
    for v in tells.values():
        why.update(v)
    return {"n_poles": len(poles), "n_step_shaped": len(step),
            "disposition_share": _share(len(poles) - len(step), len(poles)),
            "why": dict(why), "step_labels": sorted(it.label for it in poles if tells[it.item_id])}


def is_absence(vice: Item, virtue: Optional[Item]) -> Optional[str]:
    """Why ``vice`` reads as its partner's absence rather than a behavior of its own, or None."""
    ws = _words(vice.label)
    if ws and (ws[0] in NEGATION_WORDS or ws[0] in {"un", "non"}):
        return "label is a negation"
    if re.match(r"^(un|non-|non )", (vice.label or "").strip().lower()) and len(ws) == 1:
        return "label is a negation"
    g = _words(vice.gloss)
    if not any(w in NEGATION_WORDS for w in g):
        return None
    if virtue is None:
        return None
    if _overlap(_content(vice.gloss), _content(virtue.gloss)) >= ABSENCE_OVERLAP:
        return "gloss negates and otherwise repeats the virtue's"
    return None


def vice_shape(items: Sequence[Item]) -> dict:
    """The share of kept vice poles that say something beyond the virtue's absence, and the ``or``-joined poles."""
    by = {it.item_id: it for it in items}
    vices = [it for it in kept_poles(items) if it.pole == "vice"]
    why: collections.Counter = collections.Counter()
    absent = []
    for it in vices:
        reason = is_absence(it, by.get(it.partner_item_id))
        if reason:
            why[reason] += 1
            absent.append(it.label)
    joined = [it.label for it in kept_poles(items) if JOINED_RE.search(it.label or "")]
    return {"n_vices": len(vices), "n_absence_shaped": len(absent),
            "beyond_absence_share": _share(len(vices) - len(absent), len(vices)),
            "why": dict(why), "absence_labels": sorted(absent),
            "n_or_joined_labels": len(joined), "or_joined_labels": sorted(joined),
            "joined_share": _share(len(joined), len(kept_poles(items)))}


def near_duplicates(items: Sequence[Item]) -> dict:
    """Label-level near duplicates inside the round (no embedding call): kept poles of the same kind whose labels
    are identical, share a head word, or overlap at :data:`DUP_OVERLAP`.  Returns one group per cluster."""
    groups: list[dict] = []
    for pole in ("virtue", "vice"):
        poles = [it for it in kept_poles(items) if it.pole == pole]
        heads: dict[str, list[Item]] = {}
        clusters: list[list[Item]] = []
        for it in poles:
            ws = _words(it.label)
            head = ws[0] if ws else ""
            placed = False
            for cl in clusters:
                if any(it.label.lower() == o.label.lower()
                       or (head and _words(o.label) and _words(o.label)[0] == head)
                       or _overlap(_content(it.label), _content(o.label)) >= DUP_OVERLAP for o in cl):
                    cl.append(it)
                    placed = True
                    break
            if not placed:
                clusters.append([it])
            heads.setdefault(head, []).append(it)
        for cl in clusters:
            if len(cl) > 1:
                groups.append({"pole": pole, "labels": [it.label for it in cl],
                               "item_ids": [it.item_id for it in cl],
                               "within_chunk": len({it.chunk_id for it in cl}) == 1})
    n_poles = len(kept_poles(items))
    n_dup = sum(len(g["labels"]) - 1 for g in groups)
    within = sum(len(g["labels"]) - 1 for g in groups if g["within_chunk"])
    return {"n_poles": n_poles, "n_groups": len(groups), "n_duplicate_poles": n_dup,
            "duplicate_share": _share(n_dup, n_poles),
            # only a within-chunk duplicate is the prompt's fault: one call never sees another call's items
            "n_within_chunk": within, "within_chunk_share": _share(within, n_poles),
            "groups": sorted(groups, key=lambda g: -len(g["labels"]))}


def gloss_dedup(groups_doc: Mapping, items: Sequence[Item]) -> dict:
    """What the gloss-embedding dedup merged at its recorded threshold (``dedup_groups.json``): the measure of
    record for (e), beside the free label-level count of :func:`near_duplicates`."""
    res = groups_doc.get("result", groups_doc)
    groups = res.get("groups") or []
    n_kept = len(kept_poles(items))
    exact = sum(1 for g in groups if "exact stem" in (g.get("note") or ""))
    return {"threshold": (res.get("threshold") or {}).get("value") if isinstance(res.get("threshold"), Mapping)
            else res.get("threshold"),
            "n_kept_poles": n_kept, "n_groups": len(groups), "n_merged": n_kept - len(groups),
            "merged_share": _share(n_kept - len(groups), n_kept), "n_exact_stem_groups": exact}


def measure_all(items: Sequence[Item], *, n_chunks: int, summary: Optional[Mapping] = None,
                groups_doc: Optional[Mapping] = None) -> dict:
    """Every measure of one round, plus the parse rate and cost from its ``extract_summary.json`` when given and
    the gloss-embedding dedup from its ``dedup_groups.json``."""
    out = {"volume": volume(items, n_chunks=n_chunks), "gloss_form": gloss_form(items),
           "label_shape": label_shape(items), "vice_shape": vice_shape(items),
           "near_duplicates": near_duplicates(items)}
    if groups_doc is not None:
        out["gloss_dedup"] = gloss_dedup(groups_doc, items)
    if summary is not None:
        answered, unparsed = summary.get("n_chunks_answered"), len(summary.get("unparsed") or {})
        out["run"] = {"n_chunks_answered": answered, "n_unparsed": unparsed,
                      "parse_rate": _share(answered or 0, (answered or 0) + unparsed),
                      "n_invalid_items": summary.get("n_invalid_items"),
                      "cost_usd": summary.get("cost_usd_this_session"),
                      "rubric_version": (summary.get("rubrics") or {}).get("alignment_extract", {}).get("version")}
    return out


# --------------------------------------------------------------------------- the cross-round table

#: ``(heading, path into the measures, format)`` of each row of :func:`round_table`.
TABLE_ROWS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("rubric version", ("run", "rubric_version"), "d"),
    ("pairs per chunk (a)", ("volume", "pairs_per_chunk"), ".2f"),
    ("pairs extracted", ("volume", "n_pairs"), "d"),
    ("one-word labels", ("volume", "one_word_label_share"), "%"),
    ("glosses in corpus form (b)", ("gloss_form", "corpus_form_share"), "%"),
    ("glosses in the first person", ("gloss_form", "first_person_share"), "%"),
    ("labels naming a disposition (c)", ("label_shape", "disposition_share"), "%"),
    ("vices beyond an absence (d)", ("vice_shape", "beyond_absence_share"), "%"),
    ("labels joining two qualities", ("vice_shape", "joined_share"), "%"),
    ("near-duplicate poles (e)", ("near_duplicates", "duplicate_share"), "%"),
    ("of them, inside one chunk", ("near_duplicates", "within_chunk_share"), "%"),
    ("merged by the gloss dedup (e)", ("gloss_dedup", "merged_share"), "%"),
    ("parse rate (f)", ("run", "parse_rate"), "%"),
    ("cost (f)", ("run", "cost_usd"), "$"),
)


def _cell(value, fmt: str) -> str:
    if value is None:
        return "-"
    if fmt == "%":
        return f"{100 * float(value):.0f}%"
    if fmt == "$":
        return f"${float(value):.3f}"
    if fmt == "d":
        return f"{int(value):d}"
    return format(float(value), fmt)


def round_table(rounds: Sequence[tuple[str, Mapping]], *, target: Mapping[str, str] = ()) -> str:
    """A Markdown table, one column per round: ``rounds`` is ``(column heading, measures)`` pairs and ``target``
    maps a row heading to the number wanted, shown as a last column when any is given."""
    target = dict(target)
    head = ["measure"] + [name for name, _ in rounds] + (["wanted"] if target else [])
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for heading, path, fmt in TABLE_ROWS:
        cells = []
        for _name, m in rounds:
            v = m
            for k in path:
                v = (v or {}).get(k) if isinstance(v, Mapping) else None
            cells.append(_cell(v, fmt))
        row = [heading] + cells + ([target.get(heading, "")] if target else [])
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def extra_counts(items: Sequence[Item]) -> dict:
    """Counts the readout prints beside the table: type, enactability, which pole the passage named."""
    pairs = [it for it in items if it.names_source and it.rewritten_from is None]
    return {"type": dict(collections.Counter(it.type for it in pairs)),
            "enactability": dict(collections.Counter(it.enactability for it in pairs)),
            "source_pole": dict(collections.Counter(it.pole for it in pairs))}


def sample_pairs(items: Sequence[Item], n: int, seed: int = 0) -> list[tuple[Item, Item]]:
    """``n`` kept pairs spread over the round, for a hand reading: every ``len/n``th pair in rank order."""
    import random
    by = {it.item_id: it for it in items}
    pairs = [(it, by[it.partner_item_id]) for it in sorted(kept_poles(items), key=lambda x: (x.rank, x.item_id))
             if it.names_source and it.partner_item_id in by and by[it.partner_item_id].kept]
    if n >= len(pairs):
        return pairs
    return [pairs[i] for i in sorted(random.Random(seed).sample(range(len(pairs)), n))]


def iter_labels(items: Iterable[Item]) -> list[str]:
    return [it.label for it in items]


__all__ = ["PROCEDURE_VERBS", "SEQUENCING_WORDS", "NEGATION_WORDS", "GLOSS_SUBJECTS", "PERSONA_RE", "JOINED_RE", "ING_WITHIN",
           "ABSENCE_OVERLAP", "DUP_OVERLAP", "REPORT_RE", "TABLE_ROWS", "kept_poles", "volume",
           "gloss_problems", "gloss_form",
           "label_step_tells", "label_shape", "is_absence", "vice_shape", "near_duplicates", "measure_all",
           "gloss_dedup", "round_table", "extra_counts", "sample_pairs", "iter_labels"]
