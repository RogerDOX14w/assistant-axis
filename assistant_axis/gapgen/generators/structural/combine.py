"""Combining a trait's independent samples (Roger, 2026-10-13; coding_plan_09 section 1).

Roger: "Haiku and Sonnet 5.5 are run at T=1.  Stability is not expected, and we shouldn't gate on it, or design
assuming it, or throw answers away because the three weren't unanimous.  I'm instead leaning towards running three
times and intelligently combining their answers.  For something that returns a word, that might be making a deduped
list of them."

So each trait is asked three times (``operators --samples 3``) and :func:`combine` makes one
:class:`CombinedReply` per trait:

* **per slot** (``opposite``, ``excess``, ``deficiency``, each ``retarget`` target, the principal targets included,
  and each ``remode`` mode) **the union of the samples' labels**, deduplicated by normalised stem (the same
  :func:`.postprocess.stem_of` as the table; ``renamed_from``-aware: an old stem counts as the trait it was renamed
  to; separator-blind in M3's blind form, so ``fool-hardy`` and ``foolhardy`` are one label).  Each kept label carries its **support** (how many samples named it), the samples that
  did, and every sample's label and gloss; its ``label`` and ``gloss`` are the first such sample's.  **No label is
  dropped for low support**; a slot every sample left empty stays empty; near-synonyms with different stems stay
  separate (M3 and the review graph group them).  Items are ordered by support, then by the first sample naming them.
* **position**: every sample's (``positions``) and the majority (``position``: the value more than half the parsed
  samples gave, else None).

Support travels into the operator table and the readouts; it gates and filters nothing.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional

from .operators import MODES, PRINCIPAL_TARGETS, SINGLE_OPERATORS, TARGETS, OperatorReply

#: Every slot in a fixed order: (operator, target or mode or None).
SLOTS: tuple = tuple([(op, None) for op in SINGLE_OPERATORS] + [("retarget", t) for t in (*TARGETS, *PRINCIPAL_TARGETS)]
                     + [("remode", m) for m in MODES])


def slot_key(op: str, sub: Optional[str] = None) -> str:
    return op if sub is None else f"{op}:{sub}"


@dataclass
class CombinedReply:
    """One trait's samples combined (module docstring).  ``slots[slot_key]`` is a list of items, each
    ``{label, stem, gloss, has_common_word, polysemy, support, samples, glosses}``."""
    stem: str
    label: str
    samples: list = field(default_factory=list)        # the sample indexes combined, in order
    positions: list = field(default_factory=list)      # each sample's position, in sample order
    position: Optional[str] = None                     # the majority, or None
    reasonings: list = field(default_factory=list)
    slots: dict = field(default_factory=dict)
    principal: bool = False
    principal_only: bool = False
    run_id: Optional[str] = None
    model: Optional[str] = None
    prompt_sha256: Optional[str] = None
    at: Optional[str] = None
    problems: list = field(default_factory=list)
    rejected: list = field(default_factory=list)

    @property
    def n_samples(self) -> int:
        return len(self.samples)

    @property
    def reasoning(self) -> str:
        return self.reasonings[0] if self.reasonings else ""

    def slot(self, op: str, sub: Optional[str] = None) -> list[dict]:
        return list(self.slots.get(slot_key(op, sub), []))

    def items(self) -> list[tuple[str, Optional[str], dict]]:
        """``(operator, target or mode or None, item)`` for every combined item, in slot order."""
        return [(op, sub, it) for op, sub in SLOTS for it in self.slots.get(slot_key(op, sub), [])]


def _dedupe_key(label: str, *, lexicon=None, renamed: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """The label's stem (folded as the table folds it), an old stem replaced by the trait it was renamed to, then in
    M3's blind form (``novelty.blind``: case, hyphens, spaces and apostrophes out, so ``fool-hardy`` and ``foolhardy``
    are one label, as the review graph's label variants are)."""
    from assistant_axis.gapgen.novelty import blind

    from .postprocess import stem_of
    try:
        stem = stem_of(label, lexicon=lexicon)[0]
    except ValueError:
        return None
    return blind((renamed or {}).get(stem, stem))


def _majority(values: list) -> Optional[str]:
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    top, n = Counter(vals).most_common(1)[0]
    return top if n * 2 > len(vals) else None


def combine(samples: Mapping[int, OperatorReply], *, lexicon=None,
            renamed: Optional[Mapping[str, str]] = None) -> CombinedReply:
    """One trait's parsed samples combined by union (module docstring).  The samples are identified by their keys
    in ``samples`` (so two runs' first samples can be combined as samples 1 and 2)."""
    if not samples:
        raise ValueError("no sample to combine")
    order = sorted(samples)
    reps = [samples[k] for k in order]
    first = reps[0]
    out = CombinedReply(stem=first.stem, label=first.label, samples=order,
                        positions=[r.position for r in reps], position=_majority([r.position for r in reps]),
                        reasonings=[r.reasoning for r in reps], principal=any(r.principal for r in reps),
                        principal_only=all(r.principal_only for r in reps), run_id=first.run_id, model=first.model,
                        prompt_sha256=first.prompt_sha256, at=first.at,
                        problems=[f"sample {k}: {p}" for k, r in zip(order, reps) for p in r.problems],
                        rejected=[{**x, "sample": k} for k, r in zip(order, reps) for x in r.rejected])
    for op, sub in SLOTS:
        merged: dict[str, dict] = {}
        for k, r in zip(order, reps):
            for o, s, it in r.items():
                if (o, s) != (op, sub):
                    continue
                key = _dedupe_key(it["label"], lexicon=lexicon, renamed=renamed)
                if key is None:
                    continue
                cur = merged.get(key)
                if cur is None:
                    from .postprocess import stem_of
                    merged[key] = cur = {"label": it["label"], "stem": stem_of(it["label"], lexicon=lexicon)[0],
                                         "gloss": it.get("gloss"), "has_common_word": it.get("has_common_word"),
                                         "polysemy": it.get("polysemy"), "support": 0, "samples": [], "glosses": []}
                if k not in cur["samples"]:
                    cur["samples"].append(k)
                    cur["support"] += 1
                    cur["glosses"].append({"sample": k, "label": it["label"], "gloss": it.get("gloss")})
                    if cur.get("polysemy") is not True and it.get("polysemy") is True:
                        cur["polysemy"] = True
                    if cur.get("has_common_word") is None:
                        cur["has_common_word"] = it.get("has_common_word")
        if merged:
            out.slots[slot_key(op, sub)] = sorted(merged.values(), key=lambda x: (-x["support"], x["samples"][0]))
    return out


def combine_all(sample_replies: Mapping[str, Mapping[int, OperatorReply]], **kw) -> dict[str, CombinedReply]:
    """``{stem: CombinedReply}`` for every trait with at least one parsed sample."""
    return {stem: combine(s, **kw) for stem, s in sorted(sample_replies.items()) if s}


def support_counts(combined: Iterable[CombinedReply]) -> dict:
    """Counts of the combined items by support and by operator: ``{"n_traits", "samples_per_trait": {n: traits},
    "by_support": {k: items}, "by_operator": {op: {k: items}}}`` (a readout figure; nothing is filtered on it)."""
    reps = list(combined)
    by_support: Counter = Counter()
    by_op: dict[str, Counter] = {}
    for r in reps:
        for op, _sub, it in r.items():
            by_support[it["support"]] += 1
            by_op.setdefault(op, Counter())[it["support"]] += 1
    return {"n_traits": len(reps),
            "samples_per_trait": {str(k): v for k, v in sorted(Counter(r.n_samples for r in reps).items())},
            "by_support": {str(k): v for k, v in sorted(by_support.items())},
            "by_operator": {op: {str(k): v for k, v in sorted(c.items())} for op, c in sorted(by_op.items())}}


def union_phrase(n_samples) -> str:
    """How a readout names a count over combined samples: "union of 3 samples" (Roger, 2026-10-13)."""
    return f"union of {n_samples} sample{'' if n_samples == 1 else 's'}"


__all__ = ["SLOTS", "slot_key", "CombinedReply", "combine", "combine_all", "support_counts", "union_phrase"]
