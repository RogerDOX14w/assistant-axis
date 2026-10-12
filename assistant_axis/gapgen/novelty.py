"""M3, the novelty check: does the corpus already have this candidate trait?

The brief is ``reports/trait_gap_generation/coding_plan_m3.md`` (2026-10-07); the design is
``coding_plan_platform.md``, "M2 final settings and the M3 design" and "M3 overlap call: decisions
after the rubric test".  This module holds the pure pieces, no API calls; the waves that send the
calls are :mod:`assistant_axis.gapgen.novelty_runner`, the CLI ``data_analysis/gap_generation/
novelty_score.py``.

Per candidate (a registry row whose filter verdict is ``trait``, with a gloss and an alignment score):

0. **Exact label** (:func:`exact_label_match`): the stem equal to a corpus stem, a seed-queue stem (or a
   queue label, normalised), or a corpus file's ``renamed_from``: ``covered`` at once, reason
   ``exact_label``.
1. **Retrieve** the ``k`` nearest corpus traits in the covered setting (:class:`CorpusIndex`).  Since
   2026-10-09 the index can also hold **seed-queue entries** (:func:`queue_traits`: trait entries that are
   not yet a trait file, carry a text and have a live status, :data:`QUEUE_SEARCH_STATUSES`), so that a
   later generator wave sees the words an earlier one promoted: each is embedded as a corpus trait is
   (``label: text``) and projected into the space fitted on the corpus alone, and from there on it is
   retrieved, relation-labelled and walked like a corpus trait.  Every listed trait, reading and covering
   that is a queue entry carries ``queue_status``; a candidate covered by one through the walk records
   ``covered_by_queue`` beside ``covered_by``.
2. **Expand** (:func:`expand`): every retrieved trait in a recorded pair, triangle, tetrahedron or
   larger simplex brings the other members, each with its own cosine; sequences, rings, maps, sets,
   squares, cubes and orthoplexes do not expand (the poles of a square or orthoplex are recorded pairs
   anyway).  Each listed trait keeps its **partners** for the "opposite" rule: its recorded clean-pair
   partner and its fellow corners of a triangle, tetrahedron or simplex (the corners are mutually
   opposed).  The relation call never sees them.
3. **Relation call** (:func:`render_relation_user`, :func:`parse_relation`, rubric ``relation.md``):
   ``similar`` / ``opposed`` / ``unrelated`` / ``unsure`` for every listed trait; :func:`build_shortlist`
   turns the answers into the overlap call's queue: the partners of the opposed traits first, then the
   similar traits, each part by cosine, highest first.  An opposed trait with no partner records
   ``pair_completion_for``; a recorded pair answered ``similar`` on both sides or ``opposed`` on both
   sides is a ``pair_flag``.  The relation and overlap prompts show every label in the judge display form
   (``careless (from HEXACO)``; :mod:`assistant_axis.gapgen.prompt_labels`, from 2026-10-09), while
   :class:`CorpusTrait` keeps the stored label, which is also what is embedded (``label: description``).
4. **Overlap walk** (:class:`Walk`): one pair per call down the queue, Sonnet first, with the rule of
   :func:`sonnet_action` and early exit at the first ``covered``.
5. **Decision and block** (:func:`novelty_block`): ``covered`` (with ``covered_by``), ``new``, or ``grey``
   (kept, with a review flag that the rule set treats as grey: see :class:`Rules`).

The decision rules come in three versions (:data:`RULES`).  Version 1 is the pilot's (decisions 1-11 of
``coding_plan_platform.md``'s M3 section); version 2, the default from 2026-10-07 to 2026-10-12, adds decisions
12-15 and the cosine floor (coding_plan_m3.md, "Round 2"): a Sonnet reading one below the cut-off that Opus reads
at or above it covers, flagged; both ends of a recorded pair (every corner of a simplex) marked similar are
taken out of the shortlist and noted; the pair flag is a note, not a reason for ``grey``; a ``renamed_from``
match is judged like any other candidate, with the current trait at the front, and labels are compared
separator-blind; listed traits below the cosine floor are not judged (an opposed trait's partner and a
``renamed_from`` match are).  Version 3, the default from 2026-10-12 (Roger's decisions on the M3 gate audit,
``reports/code_review_2026-10-12/gate_audits/m3_novelty.md``, proposals P1, P2 and P5), adds three switches:

* **the graded cut-off** (P1, :func:`cut_off_spec`): alignment score 0 or 1 keeps cut-off 3 with decision 12;
  alignment score 2 is covered when both models read 3 or more (a Sonnet 3 or 4 goes to Opus, which covers at 3
  or more; a Sonnet 2 is settled, with no Opus check); alignment score 3, or none, keeps cut-off 4.  Rule sets 1
  and 2 keep the step (3 at 0-1, 4 at 2-3), so their runs replay as they were;
* **``renamed_from`` before the queue at stage 0** (P2, review 2 D1): a corpus file's ``renamed_from`` that is
  also a seed-queue name went to the queue entry and was covered at stage 0, bypassing decision 15; it now goes to
  the walk, the current trait first, like any other ``renamed_from`` match;
* **partners the relation call marked unrelated or opposed are not read** (P5): the "opposite" rule (an opposed
  trait's partner at the front of the shortlist, or read next after a Sonnet "opposite") skips a partner the
  relation call itself answered ``unrelated`` or ``opposed`` (6,560 such readings on record, none at the cut-off);
  each skip is recorded on the row (``partners_skipped``), so the saving is visible.

And one switch that no rule set turns on by itself, **the broader check** (P3, ``--broader-check``; off until
its pilot is read): a cover whose best reading is exactly 3 (rubric A's "the same concept, differing only in
scope, degree or emphasis") gets one more reading, in both orders, of which of the two concepts is the broader
(rubric ``overlap_broader.md``, :func:`render_broader_user`, :func:`broader_verdict`); the cover stands only when
the corpus trait is at least as broad as the candidate, else the walk goes on and the row carries
``cover_narrower``.  Versions 1 and 2 stay so that a run can be re-decided under them and shown to reproduce it.

By-products: every reading beside its cosine (``readings.jsonl``, :func:`reading_rows`), the review queue
(:func:`review_order`) and the rename shortlist (:func:`synonyms`).
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import normalize_to_file_name

from . import overlap_test as OT
from .prompt_labels import DEFAULT_LABEL_FORM, prompt_label

# --------------------------------------------------------------------------- constants

DECISIONS: tuple[str, ...] = ("covered", "new", "grey")
#: Every review flag a row can carry (coding_plan_m3.md, stage 5; ``both_similar`` from decision 13;
#: ``cover_narrower`` from the broader check, 2026-10-12).  Which of them make a kept candidate ``grey`` is the
#: rule set's :attr:`Rules.grey_kinds`.
REVIEW_KINDS: tuple[str, ...] = ("sonnet_below_opus_at", "unparsed", "pair_flag", "both_similar", "cover_narrower")
#: The flags that put a row in the review queue whatever its decision (decision 14: the covered-and-flagged
#: rows, the both-similar notes and ``unparsed``; the broader check's undone covers); a ``grey`` row is always in it.
QUEUE_KINDS: tuple[str, ...] = ("sonnet_below_opus_at", "both_similar", "unparsed", "cover_narrower")
#: The relation answers whose partner the "opposite" rule skips under rule set 3 (audit P5).
SKIP_PARTNER_RELATIONS: tuple[str, ...] = ("unrelated", "opposed")
#: The cosine floor of rule set 2 (Roger, 2026-10-07: "an acceptable level of trade-off").
DEFAULT_COSINE_FLOOR = 0.25
RELATION_ANSWERS: tuple[str, ...] = ("similar", "opposed", "unrelated", "unsure")
#: The relation rubric's answer, in the shape :func:`overlap_test.parse_list` reads.
RELATION_SPEC: dict = {"key": "relation", "scale": (), "categories": RELATION_ANSWERS}
RELATION_RUBRIC = "relation"
#: The overlap call's rubric: rubric A (``overlap_concept``), one pair per call from version 5.
OVERLAP_RUBRIC = "A"
HAIKU, SONNET, OPUS = OT.HAIKU, OT.SONNET, OT.OPUS
#: Haiku 5.5: the relation call's model from 2026-10-08 (``novelty_runner.RELATION_MODEL``).
HAIKU55 = OT.HAIKU55
#: Arrangement kinds whose members are mutually opposed and expand each other (pair and simplexes).
EXPANDING_FIXED = ("pair", "triangle", "tetrahedron")
#: How the candidate is embedded: ``gloss_w14`` (metric_config.json's ``covered.query_form``: the gloss
#: alone, no label, cut to 14 words, the form M2 measured recall on; the default since 2026-10-07, Fable on
#: Roger's go: the brief's "label plus gloss" was a slip) or ``label_gloss`` (``label: gloss`` cut to the
#: covered representation, the corpus side's form; kept for comparison).
QUERY_FORMS: tuple[str, ...] = ("gloss_w14", "label_gloss")
DEFAULT_QUERY_FORM = "gloss_w14"
#: The seed-queue statuses whose trait entries join the similarity search (2026-10-09; Roger: "That definitely
#: needs fixing first"): the statuses at which an entry is a word in hand that is not yet a trait file.
#: ``candidate`` (what ``promote`` writes) and ``ready`` are the lifecycle before ``seeded``; ``tbd`` and
#: ``backlog`` are parked but not turned down.  From ``seeded`` on (``generated``, ``checked``, ``paired``,
#: ``done``, ``refused``) the entry is a trait file and in the index as one; an entry at those statuses with
#: no file under its stem was renamed (the 10 ``paired`` entries with a text on 2026-10-09, each a corpus
#: file's ``renamed_from``) or removed.  ``exists`` was a file when the queue was built.  ``not_adopted`` and
#: ``superseded`` were turned down: they stay exact-label only (stage 0), since turning a word down is no
#: reason to hide its synonyms.
QUEUE_SEARCH_STATUSES: tuple[str, ...] = ("candidate", "ready", "tbd", "backlog")

#: A queue entry carrying this field was handed from the seed queue to the trait-gap pipeline (Roger's W23,
#: 2026-10-09): its value is the registry key, and the registry row is the record from then on.  Such an entry
#: covers nothing, in stage 0 or in the search; otherwise the word would be covered by its own entry.
HANDED_TO_REGISTRY_FIELD = "gap_registry_key"


def handed_to_registry(entry: Mapping) -> bool:
    """True for a queue entry handed to the trait-gap pipeline (:data:`HANDED_TO_REGISTRY_FIELD` set)."""
    return bool(entry.get(HANDED_TO_REGISTRY_FIELD))


def is_expanding(kind: str) -> bool:
    """Pairs, triangles, tetrahedra and larger simplexes expand; nothing else does."""
    return kind in EXPANDING_FIXED or kind.endswith("-simplex")


# --------------------------------------------------------------------------- the decision rules

#: The cut-off rules (:func:`cut_off_spec`): ``step`` (rule sets 1 and 2: 3 at alignment score 0-1, 4 at 2-3 or
#: none) and ``graded`` (rule set 3, audit P1: alignment score 2 covered when both models read 3 or more).
CUT_OFF_RULES: tuple[str, ...] = ("step", "graded")
#: How the broader check's two readings (both orders) decide (:func:`broader_verdict`): ``mean`` (the default:
#: each reading scores +1 when it names the candidate the broader, -1 the corpus trait, 0 for "same" or
#: "unsure"; the cover is undone when the mean of the two is above 0, swap-averaging as the judging rule asks),
#: ``both`` (undone only when both orders name the candidate) or ``either`` (when either does).
BROADER_GATES: tuple[str, ...] = ("mean", "both", "either")


@dataclass(frozen=True)
class Rules:
    """One version of M3's decision rules (the module docstring).  Each switch is one decision of
    ``coding_plan_platform.md``'s M3 section (or, from rule set 3, one proposal of the M3 gate audit), so that a
    change in a re-decided run can be traced to one.  The switches added on 2026-10-12 have defaults that are
    rule sets 1 and 2's behaviour, and :meth:`as_dict` leaves them out at those defaults, so a block of either
    set is written byte for byte as before and an older block reads back (:func:`rules_of`)."""
    name: str
    version: int
    cover_on_opus_check: bool        # decision 12: Sonnet c - 1, Opus c or above -> covered, flagged
    both_similar_excluded: bool      # decision 13: both ends of a pair similar -> neither is judged, a note
    pair_flag_grey: bool             # decision 14 off: a pair flag makes a kept row grey
    renamed_from_covers: bool        # decision 15 off: a renamed_from match covers at stage 0
    separator_blind: bool            # decision 15: labels compared with the separators taken out
    cosine_floor: Optional[float]    # listed traits below it are not judged (None: no floor)
    renamed_before_queue: bool = False      # review 2 D1 (audit P2): a renamed_from match goes to the walk even
    #                                         when a seed-queue entry carries the old stem
    cut_off_rule: str = "step"              # audit P1: "graded" (:func:`cut_off_spec`)
    skip_unrelated_partners: bool = False   # audit P5: the opposite rule skips partners marked unrelated/opposed
    broader_check: Optional[str] = None     # audit P3: None (off) or a gate of BROADER_GATES

    def __post_init__(self):
        if self.cut_off_rule not in CUT_OFF_RULES:
            raise ValueError(f"cut_off_rule must be one of {CUT_OFF_RULES}, not {self.cut_off_rule!r}")
        if self.broader_check is not None and self.broader_check not in BROADER_GATES:
            raise ValueError(f"broader_check must be None or one of {BROADER_GATES}, not {self.broader_check!r}")

    @property
    def grey_kinds(self) -> tuple[str, ...]:
        """The review flags that make a kept candidate ``grey``: ``unparsed`` always; the Opus check's flag
        while it does not cover (decision 12 off); the pair flag while it is a review trigger (decision 14
        off).  A both-similar note never does: the row keeps its decision and the note puts it in review."""
        kinds = ["sonnet_below_opus_at"] if not self.cover_on_opus_check else []
        kinds.append("unparsed")
        if self.pair_flag_grey:
            kinds.append("pair_flag")
        return tuple(kinds)

    def with_floor(self, floor: Optional[float]) -> "Rules":
        return replace(self, cosine_floor=None if floor is None else float(floor))

    def with_broader(self, gate: Optional[str]) -> "Rules":
        """The rule set with the broader check on (``gate`` one of :data:`BROADER_GATES`) or off (``None``)."""
        return replace(self, broader_check=gate)

    def below_floor(self, cosine: Optional[float]) -> bool:
        return self.cosine_floor is not None and cosine is not None and float(cosine) < self.cosine_floor

    def as_dict(self) -> dict:
        """The switches, as every block and ``run.json`` record them; a switch of 2026-10-12 at its default (rule
        sets 1 and 2's behaviour) is left out, so those sets' records are unchanged."""
        d = asdict(self)
        for k, v in LATER_SWITCH_DEFAULTS.items():
            if d.get(k) == v:
                d.pop(k)
        return d


#: The switches added on 2026-10-12, with the defaults that are rule sets 1 and 2's behaviour.
LATER_SWITCH_DEFAULTS: dict[str, Any] = {"renamed_before_queue": False, "cut_off_rule": "step",
                                         "skip_unrelated_partners": False, "broader_check": None}

#: Version 1: the pilot's rules (decisions 1-11).  Version 2: decisions 12-15 and the floor (2026-10-07).
#: Version 3: version 2 with the graded cut-off, review 2 D1's fix and the partner skip (2026-10-12; the M3 gate
#: audit's P1, P2 and P5).  The broader check (P3) is a switch of its own, off in every set (``with_broader``).
RULES: dict[int, Rules] = {
    1: Rules(name="m3_rules_1", version=1, cover_on_opus_check=False, both_similar_excluded=False,
             pair_flag_grey=True, renamed_from_covers=True, separator_blind=False, cosine_floor=None),
    2: Rules(name="m3_rules_2", version=2, cover_on_opus_check=True, both_similar_excluded=True,
             pair_flag_grey=False, renamed_from_covers=False, separator_blind=True, cosine_floor=DEFAULT_COSINE_FLOOR),
}
RULES[3] = replace(RULES[2], name="m3_rules_3", version=3, renamed_before_queue=True, cut_off_rule="graded",
                   skip_unrelated_partners=True)
#: The rule set of a new run (``novelty_score.py score``; ``--rules 2`` or ``1`` reproduce the older ones).
DEFAULT_RULES = RULES[3]
#: The steps from version 1 to version 2, one decision each, in the order a re-decided run attributes its
#: changes (``novelty_score.py score --redecide``): each step adds one switch to the ones before it.
RULE_STEPS: tuple[tuple[str, dict], ...] = (
    ("decision 14 (pair flag a note)", {"pair_flag_grey": False}),
    ("decision 12 (covered, flagged)", {"cover_on_opus_check": True}),
    ("decision 13 (both ends similar)", {"both_similar_excluded": True}),
    ("decision 15 (labels: renamed_from judged, separator-blind)", {"renamed_from_covers": False, "separator_blind": True}),
    ("cosine floor", {"cosine_floor": DEFAULT_COSINE_FLOOR}),
)
#: The steps from version 2 to version 3 (the M3 gate audit, 2026-10-12), then the broader check, in the order a
#: re-decided run attributes its changes.
RULE_STEPS_3: tuple[tuple[str, dict], ...] = (
    ("review 2 D1 (renamed_from before the queue)", {"renamed_before_queue": True}),
    ("graded cut-off (alignment 2: both models at 3 or more)", {"cut_off_rule": "graded"}),
    ("partner skip (partners marked unrelated or opposed not read)", {"skip_unrelated_partners": True}),
    ("broader check (a cover read at 3 undone when the corpus trait is narrower)", {"broader_check": "mean"}),
)


def rule_chain(floor: Optional[float] = DEFAULT_COSINE_FLOOR) -> list[tuple[str, Rules]]:
    """``[(step name, rules), ...]``: version 1, then each of :data:`RULE_STEPS` added in turn (the last is
    version 2 with ``floor``)."""
    cur = RULES[1]
    out = [("rules 1 (the pilot's)", cur)]
    for i, (name, change) in enumerate(RULE_STEPS, 1):
        change = dict(change)
        if "cosine_floor" in change:
            change["cosine_floor"] = floor
        cur = replace(cur, name=f"m3_rules_1+{i}", **change)
        out.append((name, cur))
    out[-1] = (out[-1][0], replace(out[-1][1], name=RULES[2].name, version=2))
    return out


def _switches(r: Rules) -> dict:
    return {k: v for k, v in asdict(r).items() if k not in ("name", "version")}


def attribution_chain(src: Rules, dst: Rules) -> list[tuple[str, Rules]]:
    """``[(step name, rules), ...]`` from ``src`` to ``dst``, one decision a step, for a re-decided run's
    attribution (``decision_changes.md``): the source's rules first, then each step of :data:`RULE_STEPS` and
    :data:`RULE_STEPS_3` whose switches ``dst`` sets otherwise than the rules before it (taking ``dst``'s values,
    the floor included), in that order; the last step carries ``dst``'s name and version.  A difference no step
    names ends the chain with ``("these rules (<name>)", dst)``.  So rule set 2 to 3 is the source, then D1, then
    the graded cut-off, then the partner skip (and the broader check when ``dst`` has it on)."""
    out = [(f"source rules ({src.name})", src)]
    cur = src
    for name, change in RULE_STEPS + RULE_STEPS_3:
        target = {k: getattr(dst, k) for k in change}
        if all(getattr(cur, k) == v for k, v in target.items()):
            continue
        cur = replace(cur, name=f"{src.name}+{len(out)}", **target)
        out.append((name, cur))
    if _switches(cur) != _switches(dst):
        out.append((f"these rules ({dst.name})", dst))
    elif len(out) > 1:
        out[-1] = (out[-1][0], dst)
    return out


# --------------------------------------------------------------------------- the cut-off

@dataclass(frozen=True)
class CutOff:
    """The cut-off rule one candidate is judged by (:func:`cut_off_spec`).  ``c``: the cut-off on rubric A's
    scale.  ``sonnet_alone``: a Sonnet reading above ``c`` covers without Opus (else Opus reads it and covers at
    ``c`` or above).  ``opus_check``: a Sonnet reading of ``c - 1`` goes to Opus (decision 11; under decision 12
    an Opus reading of ``c`` or above covers, flagged).  ``rule`` and ``band`` say which rule and which part of
    it gave these (recorded in a graded run's blocks as ``cut_off_rule``)."""
    c: int
    sonnet_alone: bool = True
    opus_check: bool = True
    rule: str = "step"
    band: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _alignment_int(alignment_score: Any) -> Optional[int]:
    if isinstance(alignment_score, bool) or alignment_score is None:
        return None
    try:
        return int(alignment_score)
    except (TypeError, ValueError):
        return None


def cut_off_spec(alignment_score: Any, rules: Optional[Rules] = None) -> CutOff:
    """The cut-off rule for a candidate with ``alignment_score`` under ``rules`` (``None``: the step rule of rule
    sets 1 and 2, as :func:`cut_off` has always given it).

    * ``step`` (design item 6, decision 4): 3 far from alignment (alignment score 0 or 1), 4 near it (2 or 3).
    * ``graded`` (rule set 3; the M3 gate audit's P1, Roger 2026-10-12): 0 or 1 as the step rule (3, Sonnet 4
      alone, decision 12 at Sonnet 2); **2: covered when both models read 3 or more** (cut-off 3, a Sonnet 3 or 4
      goes to Opus, which covers at 3 or more; a Sonnet 2 is settled with no Opus check, as cut-off 4 settled it,
      so the records of a step run hold every reading the rule needs); 3: as the step rule (4).

    A missing score takes the near-alignment cut-off, the one that cuts less (a candidate is never cut on a
    guess)."""
    a = _alignment_int(alignment_score)
    rule = (rules.cut_off_rule if rules is not None else "step")
    if a is None:
        return CutOff(c=4, rule=rule, band="no alignment score")
    if a <= 1:
        return CutOff(c=3, rule=rule, band="alignment 0-1")
    if rule == "graded":
        if a == 2:
            return CutOff(c=3, sonnet_alone=False, opus_check=False, rule=rule, band="alignment 2")
        return CutOff(c=4, rule=rule, band="alignment 3")
    return CutOff(c=4, rule=rule, band="alignment 2-3")


def as_cut_off(c: Any) -> CutOff:
    """``c`` as a :class:`CutOff`: itself, or a bare integer cut-off read as the step rule's (Sonnet above it
    alone, the Opus check one below it), as every caller before 2026-10-12 meant it (the review graph and the
    near-duplicate scan fix their own cut-off)."""
    if isinstance(c, CutOff):
        return c
    return CutOff(c=int(c), rule="fixed", band=f"fixed at {int(c)}")


def cut_off(alignment_score: Any, rules: Optional[Rules] = None) -> int:
    """The covered cut-off on rubric A's scale (:func:`cut_off_spec`'s ``c``): with no ``rules``, the step rule
    (3 far from alignment, alignment score 0 or 1; 4 near it, 2 or 3; 4 with no score)."""
    return cut_off_spec(alignment_score, rules).c


# --------------------------------------------------------------------------- the corpus

@dataclass
class CorpusTrait:
    stem: str
    label: str
    description: str
    negative_label: Optional[str]
    pair_partner: Optional[str]
    partners: list          # pair partner, then fellow simplex corners (sorted)
    expands_to: list        # the other members of its pair / simplexes (what expansion adds)
    renamed_from: list      # earlier stems
    simplexes: list = field(default_factory=list)   # [{"kind", "members"}]: its triangles, tetrahedra, simplexes
    queue_status: Optional[str] = None              # a seed-queue entry's status (None: a corpus trait file)

    @property
    def is_queue(self) -> bool:
        return self.queue_status is not None


def _renamed_from(value: Any) -> list[str]:
    out = []
    for item in value if isinstance(value, list) else ([value] if value else []):
        old = item.get("stem") if isinstance(item, Mapping) else item
        if isinstance(old, str) and old:
            out.append(old)
    return out


def load_trait_corpus(data_dir: Path) -> dict[str, CorpusTrait]:
    """Every trait file under ``<data_dir>/traits/instructions``: label (``positive_label``), description,
    ``negative_label``, the recorded clean-pair partner (reciprocal by label, recorded as a ``pair``),
    the partners for the "opposite" rule, the members expansion adds, and ``renamed_from``."""
    from assistant_axis.arrangements import load_corpus_arrangements, reciprocal_pairs
    data_dir = Path(data_dir)
    recs = load_corpus_arrangements(data_dir, "traits")
    pair_of: dict[str, str] = {}
    for a, b in reciprocal_pairs(recs):
        pair_of[a], pair_of[b] = b, a
    out: dict[str, CorpusTrait] = {}
    for stem, rec in sorted(recs.items()):
        doc = json.loads(rec.path.read_text(encoding="utf-8"))
        # the clean-pair partner by the label convention (a reciprocal pair an unclassified file has not
        # recorded in its arrangement yet still counts)
        partner = pair_of.get(stem)
        corners: set[str] = set()
        expands: set[str] = set()
        simplexes: list[dict] = []
        for a in rec.arrangements:
            if is_expanding(a.kind):
                others = [m for m in a.members if m != stem]
                expands.update(others)
                if a.kind != "pair":
                    corners.update(others)
                    simplexes.append({"kind": a.kind, "members": sorted(a.members)})
        if partner:
            expands.add(partner)
        partners = ([partner] if partner else []) + sorted(c for c in corners if c != partner)
        out[stem] = CorpusTrait(stem=stem, label=doc.get("positive_label") or stem.replace("_", " "),
                                description=doc.get("description") or "", negative_label=rec.negative_label,
                                pair_partner=partner, partners=partners, expands_to=sorted(expands),
                                renamed_from=_renamed_from(doc.get("renamed_from")), simplexes=simplexes)
    return out


def queue_text(entry: Mapping) -> str:
    """A seed-queue entry's text: its ``description``, else its ``description_draft`` (promote writes the
    candidate's gloss there), stripped; ``""`` when it has neither."""
    for k in ("description", "description_draft"):
        v = entry.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def queue_traits(queue: Mapping, corpus: Mapping[str, CorpusTrait], *,
                 statuses: Sequence[str] = QUEUE_SEARCH_STATUSES, hide: Iterable[str] = ()
                 ) -> tuple[dict[str, CorpusTrait], dict]:
    """The seed-queue entries that join the similarity search, as :class:`CorpusTrait` rows with
    ``queue_status`` set, and the record of the selection.

    An entry joins when it is a trait entry, its status is one of ``statuses``, it has a text
    (:func:`queue_text`), and it is not already in ``corpus`` (the *full* corpus, before any hiding): its stem
    is not a corpus stem, neither its stem nor its normalised label is a corpus file's ``renamed_from``, and its
    normalised label is not a corpus stem.  The first entry of a stem wins.  ``hide`` (the recovery harness):
    entries whose stem or normalised label is a hidden stem are left out, as stage 0 leaves them out.

    The row's label is the entry's ``label`` (else the stem, spaced), its description the text, so the relation
    and overlap prompts and the embedded ``label: text`` have the corpus's form.  A partner is taken only when the
    entry records one (``partner``) and it is in the search (a corpus trait not hidden, or another entry that
    joins): it is the row's pair partner, its partner for the "opposite" rule and the member its expansion adds,
    as a corpus pair partner is; the corpus trait itself is not changed.  Otherwise the row has none.

    The record: ``statuses``, ``n_entries``, ``stems``, ``excluded`` (counts by reason), and ``entries_sha256``
    (a hash of what the index holds: stem, label, text, status and partner of each row, so that two runs over
    different queue files with the same rows can be told to agree)."""
    import hashlib
    statuses = tuple(statuses)
    hid = set(hide)
    renamed = {old for t in corpus.values() for old in t.renamed_from}
    excluded: dict[str, int] = {}
    chosen: dict[str, dict] = {}

    def skip(why: str) -> None:
        excluded[why] = excluded.get(why, 0) + 1

    for e in queue.get("entries") or []:
        stem = e.get("stem")
        if (e.get("entity_type") or "trait") != "trait" or not stem:
            skip("not_a_trait_entry")
            continue
        if handed_to_registry(e):
            skip("handed_to_registry")
            continue
        if e.get("status") not in statuses:
            skip(f"status_{e.get('status')}")
            continue
        text = queue_text(e)
        if not text:
            skip("no_text")
            continue
        lab = normalize_to_file_name(e["label"]) if e.get("label") else stem
        if stem in corpus:
            skip("a_corpus_stem")
            continue
        if stem in renamed or lab in renamed:
            skip("a_corpus_files_renamed_from")
            continue
        if lab in corpus:
            skip("label_a_corpus_stem")
            continue
        if stem in hid or lab in hid:
            skip("hidden")
            continue
        if stem in chosen:
            skip("duplicate_stem")
            continue
        chosen[stem] = {"entry": e, "label": e.get("label") or stem.replace("_", " "), "text": text}
    available = (set(corpus) - hid) | set(chosen)
    out: dict[str, CorpusTrait] = {}
    for stem in sorted(chosen):
        c = chosen[stem]
        p = c["entry"].get("partner")
        p = normalize_to_file_name(p) if isinstance(p, str) and p.strip() else None
        p = p if p and p in available and p != stem else None
        out[stem] = CorpusTrait(stem=stem, label=c["label"], description=c["text"], negative_label=None,
                                pair_partner=p, partners=[p] if p else [], expands_to=[p] if p else [],
                                renamed_from=[], simplexes=[], queue_status=c["entry"].get("status"))
    rows = [[s, t.label, t.description, t.queue_status, t.pair_partner] for s, t in sorted(out.items())]
    sha = hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return out, {"statuses": list(statuses), "n_entries": len(out), "stems": sorted(out),
                 "excluded": dict(sorted(excluded.items())), "entries_sha256": sha}


@dataclass
class CorpusIndex:
    """The corpus rows in the covered space (unit rows: a dot product is the cosine) and the transform
    that maps a candidate's raw embedding into the same space (fitted on the corpus only).  ``queue_info``:
    ``None`` when the index holds no seed-queue entry, else the record the blocks carry (``n_entries``, and
    whatever the builder adds: the queue file's sha256, the statuses); the entries' rows follow the corpus's
    in ``stems`` and ``Z``, and their :class:`CorpusTrait` in ``traits`` has ``queue_status`` set."""
    stems: list
    Z: np.ndarray
    transform: Any
    traits: dict
    settings: dict
    queue_info: Optional[dict] = None

    def __post_init__(self):
        self._row = {s: i for i, s in enumerate(self.stems)}

    @property
    def queue_stems(self) -> list[str]:
        """The seed-queue entries in the index, in row order."""
        return [s for s in self.stems if self.traits[s].is_queue]

    @property
    def corpus_stems(self) -> list[str]:
        """The corpus traits in the index, in row order."""
        return [s for s in self.stems if not self.traits[s].is_queue]

    def project(self, e_raw: np.ndarray) -> np.ndarray:
        return self.transform.apply(np.asarray(e_raw, dtype=np.float64))

    def cosines(self, q: np.ndarray) -> np.ndarray:
        """Cosine of the projected query ``q`` with every corpus row."""
        return self.Z @ np.asarray(q, dtype=np.float64)

    def cosine_to(self, q: np.ndarray, stem: str) -> Optional[float]:
        i = self._row.get(stem)
        return None if i is None else float(self.Z[i] @ q)

    def retrieve(self, q: np.ndarray, k: int, *, exclude: Iterable[str] = ()) -> list[tuple[str, float]]:
        """The ``k`` nearest corpus traits to the projected query, nearest first (ties by stem)."""
        sims = self.cosines(q)
        ex = set(exclude)
        order = sorted(range(len(self.stems)), key=lambda i: (-sims[i], self.stems[i]))
        out = []
        for i in order:
            if self.stems[i] in ex:
                continue
            out.append((self.stems[i], float(sims[i])))
            if len(out) >= k:
                break
        return out


def build_index(traits: Mapping[str, CorpusTrait], E_raw: np.ndarray, *, variant: str,
                settings: Optional[Mapping] = None, queue: Optional[Mapping[str, CorpusTrait]] = None,
                E_queue: Optional[np.ndarray] = None, queue_info: Optional[Mapping] = None) -> CorpusIndex:
    """``E_raw``: the corpus embeddings, one row per trait in ``sorted(traits)`` order.  ``queue``
    (:func:`queue_traits`) and ``E_queue`` (their embeddings in ``sorted(queue)`` order): seed-queue entries
    projected into the space, which stays fitted on the corpus alone, so that adding an entry moves no corpus
    vector; ``queue_info`` is added to the index's record of them.  With no entry the index is the corpus's
    alone, exactly as before."""
    from .embed import normalize_rows
    from .space import fit_space
    stems = sorted(traits)
    E = normalize_rows(np.asarray(E_raw))
    if E.shape[0] != len(stems):
        raise ValueError(f"{E.shape[0]} corpus rows for {len(stems)} traits")
    T = fit_space(E, variant)
    Z = T.apply(E)
    all_traits = dict(traits)
    info = None
    if queue:
        qstems = sorted(queue)
        clash = sorted(set(qstems) & set(stems))
        if clash:
            raise ValueError(f"seed-queue entries with a corpus stem: {', '.join(clash[:10])}")
        if E_queue is None or len(E_queue) != len(qstems):
            raise ValueError(f"{0 if E_queue is None else len(E_queue)} queue rows for {len(qstems)} entries")
        Z = np.vstack([Z, T.apply(normalize_rows(np.asarray(E_queue)))])
        stems = stems + qstems
        all_traits.update(queue)
        info = dict(queue_info or {}) | {"n_entries": len(qstems)}
    out_settings = dict(settings or {}, variant=variant, n_corpus=len(traits))
    if info:
        out_settings["n_queue"] = info["n_entries"]
    return CorpusIndex(stems=stems, Z=Z, transform=T, traits=all_traits, settings=out_settings, queue_info=info)


def query_text(label: str, gloss: str, *, query_form: str = DEFAULT_QUERY_FORM, representation: str = "w20") -> str:
    """The text embedded for a candidate (:data:`QUERY_FORMS`)."""
    from .representation import represent_short
    from .retrieval import query_text as gloss_query
    if query_form == "label_gloss":
        return represent_short(label, gloss, representation)
    if query_form == "gloss_w14":
        return gloss_query(gloss)
    raise ValueError(f"query_form must be one of {QUERY_FORMS}, not {query_form!r}")


# --------------------------------------------------------------------------- stage 0: the exact label

def blind(stem: str) -> str:
    """A stem with its separators taken out (decision 15: "anti feminist", "anti-feminist" and antifeminist
    are one label; :func:`normalize_to_file_name` has already folded case, spaces and hyphens to ``_``)."""
    return stem.replace("_", "")


def _blind_index(names: Iterable[str]) -> dict[str, str]:
    """``{blind form: name}``; where two names share a blind form, the first in sorted order."""
    out: dict[str, str] = {}
    for n in sorted(names):
        out.setdefault(blind(n), n)
    return out


@dataclass
class LabelSets:
    corpus: set
    queue: dict          # stem -> {"stem", "status", "entity_type"} (stems and normalised labels)
    renamed: dict        # old stem -> current corpus stem

    def blind_index(self, which: str) -> dict[str, str]:
        """``{blind form: name}`` of ``corpus``, ``queue`` or ``renamed`` (built once)."""
        memo = self.__dict__.setdefault("_blind", {})
        if which not in memo:
            memo[which] = _blind_index(getattr(self, which))
        return memo[which]


def label_sets(traits: Mapping[str, CorpusTrait], queue: Mapping) -> LabelSets:
    """The names stage 0 checks: corpus trait stems, every seed-queue entry's stem and normalised label
    (any status, either entity type: a queued name is decided or in hand, except an entry handed to the trait-gap
    pipeline, :func:`handed_to_registry`), and every ``renamed_from``."""
    q: dict[str, dict] = {}
    for e in queue.get("entries") or []:
        if handed_to_registry(e):
            continue
        info = {"stem": e.get("stem"), "status": e.get("status"), "entity_type": e.get("entity_type")}
        for name in (e.get("stem"), normalize_to_file_name(e["label"]) if e.get("label") else None):
            if name and name not in q:
                q[name] = info
    renamed = {old: t.stem for t in traits.values() for old in t.renamed_from}
    return LabelSets(corpus=set(traits), queue=q, renamed=renamed)


def _lookup(stem: str, sets: LabelSets, which: str, separator_blind: bool) -> Optional[str]:
    """The name of ``sets.<which>`` that ``stem`` matches: itself when present, else (``separator_blind``)
    the name with the same blind form."""
    if stem in getattr(sets, which):
        return stem
    if separator_blind:
        return sets.blind_index(which).get(blind(stem))
    return None


def exact_label_match(stem: str, sets: LabelSets, *, rules: Optional[Rules] = None) -> Optional[dict]:
    """``{"covered_by", "match", ...}`` when stage 0 covers the candidate, else ``None``: its normalised label
    a corpus stem (``match: "corpus"``), a queue name (``"queue"``, covered by the entry's stem) or, while
    ``rules.renamed_from_covers`` (rule set 1), a renamed stem (``"renamed_from"``, covered by the current
    stem).  The corpus is checked first.  With ``rules.separator_blind`` (rule set 2) a label that differs
    only in its separators matches too (``"blind": True``, ``"matched": <the name>``).

    With ``rules.renamed_before_queue`` (rule set 3; review 2 D1) a renamed stem is checked before the queue and
    is not covered here: decision 15 judges it (:func:`renamed_match`), even when a seed-queue entry carries the
    old stem (the stale entry under a renamed trait's old name covered 8 rows at stage 0 under rule set 2:
    tough, disciplined, nonchalant, bland, exclusive, indulgent, libertarian, universalist)."""
    rules = rules or DEFAULT_RULES
    sb = rules.separator_blind
    c = _lookup(stem, sets, "corpus", sb)
    if c is not None:
        return {"covered_by": c, "match": "corpus"} | ({"blind": True, "matched": c} if c != stem else {})
    if rules.renamed_from_covers:
        r = _lookup(stem, sets, "renamed", sb)
        if r is not None:
            return {"covered_by": sets.renamed[r], "match": "renamed_from", "old_stem": r} | \
                ({"blind": True} if r != stem else {})
    elif rules.renamed_before_queue and _lookup(stem, sets, "renamed", sb) is not None:
        return None
    q = _lookup(stem, sets, "queue", sb)
    if q is not None:
        e = sets.queue[q]
        return {"covered_by": e.get("stem") or q, "match": "queue", "queue_status": e.get("status"),
                "entity_type": e.get("entity_type")} | ({"blind": True, "matched": q} if q != stem else {})
    return None


def renamed_match(stem: str, sets: LabelSets, *, rules: Optional[Rules] = None) -> Optional[dict]:
    """Decision 15: ``{"current": <corpus stem>, "old_stem": ...}`` when the candidate's label is a corpus
    file's ``renamed_from`` (separator-blind under ``rules.separator_blind``), for the walk to judge the
    current trait first; ``None`` otherwise, or when the rule set still covers such a match at stage 0."""
    rules = rules or DEFAULT_RULES
    if rules.renamed_from_covers:
        return None
    r = _lookup(stem, sets, "renamed", rules.separator_blind)
    if r is None:
        return None
    return {"current": sets.renamed[r], "old_stem": r} | ({"blind": True} if r != stem else {})


# --------------------------------------------------------------------------- stages 1-2: retrieval and expansion

@dataclass
class Listed:
    stem: str
    cosine: float
    rank: Optional[int]          # 1..k for a retrieved trait, None for an added one
    via: str                     # "retrieved" | "expanded" (| "renamed_from": the current trait of a renamed label)
    expanded_from: list = field(default_factory=list)
    partners: list = field(default_factory=list)
    pair_partner: Optional[str] = None
    simplexes: list = field(default_factory=list)   # its triangles / tetrahedra / simplexes ({"kind", "members"})
    queue_status: Optional[str] = None              # a seed-queue entry's status (None: a corpus trait)


def listed_from(stem: str, cosine: float, traits: Mapping[str, CorpusTrait], *, rank: Optional[int], via: str) -> Listed:
    t = traits[stem]
    return Listed(stem=stem, cosine=round(float(cosine), 6), rank=rank, via=via, partners=list(t.partners),
                  pair_partner=t.pair_partner, simplexes=[dict(s) for s in t.simplexes], queue_status=t.queue_status)


def expand(retrieved: Sequence[tuple[str, float]], traits: Mapping[str, CorpusTrait],
           cosine_of: Callable[[str], Optional[float]]) -> list[Listed]:
    """The listed traits: the retrieved ones in order, then the members their arrangements add (once each,
    by cosine, highest first), each with its own cosine to the candidate and its partners."""
    out: dict[str, Listed] = {}
    for rank, (s, cos) in enumerate(retrieved, 1):
        out[s] = listed_from(s, cos, traits, rank=rank, via="retrieved")
    added: dict[str, Listed] = {}
    for s, _ in retrieved:
        for m in traits[s].expands_to:
            if m in out or m not in traits:
                continue
            if m not in added:
                c = cosine_of(m)
                added[m] = listed_from(m, c if c is not None else 0.0, traits, rank=None, via="expanded")
            if s not in added[m].expanded_from:
                added[m].expanded_from.append(s)
    return list(out.values()) + sorted(added.values(), key=lambda x: (-x.cosine, x.stem))


# --------------------------------------------------------------------------- stage 3: the relation call

def relation_order(stems: Iterable[str], run_id: str, key: str) -> list[str]:
    """The listed traits in the order the relation call sends them: a shuffle seeded by the run and the
    candidate, so a resume (and every reader) gets the same order."""
    out = sorted(stems)
    random.Random(f"m3:{run_id}:relation:{key}").shuffle(out)
    return out


def relation_payload(label: str, description: str, traits: Sequence[tuple[str, str]], *,
                     label_form: str = DEFAULT_LABEL_FORM) -> dict:
    """The relation call's user turn as an object.  The labels (the candidate's and each listed trait's, as stored)
    are shown in ``label_form`` (:mod:`assistant_axis.gapgen.prompt_labels`: the judge display form by default,
    ``careless (HEXACO)`` -> ``careless (from HEXACO)``); nothing else is rewritten."""
    return {"candidate": {"label": prompt_label(label, label_form), "description": description},
            "traits": [{"id": i, "label": prompt_label(lb, label_form), "description": d}
                       for i, (lb, d) in enumerate(traits, 1)]}


def render_relation_user(label: str, description: str, traits: Sequence[tuple[str, str]], *,
                         label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The relation call's user turn, laid out as the overlap test's list form (``render_payload``): the
    candidate on the first line, each listed trait on its own line, ids 1..n in the order given; labels in
    ``label_form`` (:func:`relation_payload`)."""
    obj = relation_payload(label, description, traits, label_form=label_form)
    lines = ['{"candidate": ' + json.dumps(obj["candidate"], ensure_ascii=False) + ",", ' "traits": [']
    body = ",\n".join("  " + json.dumps(t, ensure_ascii=False) for t in obj["traits"])
    return "\n".join(lines) + "\n" + body + "\n ]}"


def parse_relation(text: Optional[str], n_listed: int) -> tuple[dict, dict, dict]:
    """``(rows, errors, meta)`` as the overlap test parses rubric A's list form (the last complete
    ``results`` object is the answer, ids outside 1..n noted, extra keys ignored and noted)."""
    return OT.parse_list(text, RELATION_SPEC, n_listed, note_extra_keys=True)


@dataclass
class Shortlist:
    queue: list                  # stems, in the order the overlap call walks them
    front: list                  # the partners of opposed traits (the head of the queue)
    pair_flags: list             # [{"pair": [a, b], "both": "similar"|"opposed"}]
    pair_completion_for: list    # opposed traits with no partner
    relations: dict              # stem -> final relation
    pair_notes: list = field(default_factory=list)    # decision 13: [{"pair": [...], "kind", "both": "similar"}]
    excluded: list = field(default_factory=list)      # decision 13: the noted members, never judged
    below_floor: list = field(default_factory=list)   # similar traits the floor kept out of the queue
    n_below_floor: int = 0                            # listed traits below the floor (any relation)
    renamed: Optional[str] = None                     # decision 15: the current trait, at the head of the queue
    partners_skipped: list = field(default_factory=list)   # rule set 3 (audit P5): [{"stem", "relation",
    #                                                         "partner_of", "at": "shortlist"}], never read


def both_similar_notes(listed: Sequence[Listed], relations: Mapping[str, str]) -> list[dict]:
    """Decision 13 (Roger's rule): every recorded pair whose two members are listed and both answered
    ``similar``, and every triangle, tetrahedron or simplex whose corners are all listed and all ``similar``:
    ``[{"pair": [members], "kind": "pair"|"triangle"|..., "both": "similar"}]``, by members."""
    by = {x.stem: x for x in listed}
    sim = {s for s, r in relations.items() if r == "similar" and s in by}
    notes: dict[tuple, dict] = {}
    for x in listed:
        p = x.pair_partner
        if p and x.stem in sim and p in sim:
            m = tuple(sorted([x.stem, p]))
            notes.setdefault(m, {"pair": list(m), "kind": "pair", "both": "similar"})
        for sx in x.simplexes:
            m = tuple(sorted(sx["members"]))
            if m not in notes and all(s in sim for s in m):
                notes[m] = {"pair": list(m), "kind": sx["kind"], "both": "similar"}
    return [notes[m] for m in sorted(notes)]


def build_shortlist(listed: Sequence[Listed], relations: Mapping[str, str],
                    cosine_of: Optional[Callable[[str], Optional[float]]] = None, *, fallback: bool = False,
                    rules: Optional[Rules] = None, renamed: Optional[str] = None) -> Shortlist:
    """Stage 3's outputs from the final relations (after the unsure re-ask).  ``cosine_of`` gives the cosine
    of a partner that is not listed (a corner of an expanded trait's own simplex).  A trait still ``unsure``
    after the re-ask is shortlisted with the similar ones (by cosine) and does not count in the pair check.
    ``fallback`` (the relation call never parsed): every listed trait, by cosine, and no pair check.

    Under ``rules`` (default :data:`DEFAULT_RULES`): with ``both_similar_excluded`` the members of every
    :func:`both_similar_notes` group leave the queue (``excluded``, ``pair_notes``); with a ``cosine_floor``
    the similar traits below it leave the queue (``below_floor``), while the partners of opposed traits stay
    whatever their cosine (the opposite rule); ``renamed`` (decision 15) heads the queue whatever the relation
    call said, the floor and the exclusion notwithstanding.  With ``skip_unrelated_partners`` (rule set 3, the
    M3 gate audit's P5) an opposed trait's partner that the relation call itself answered ``unrelated`` or
    ``opposed`` (:data:`SKIP_PARTNER_RELATIONS`) is not put in front: it is recorded in ``partners_skipped`` and
    never read (on the records, 6,560 such readings, none at the cut-off).  A partner it answered ``similar`` or
    ``unsure``, or did not list, stays in front, the floor notwithstanding."""
    rules = rules or DEFAULT_RULES
    by = {x.stem: x for x in listed}
    n_below = sum(1 for x in listed if rules.below_floor(x.cosine))
    head = [renamed] if renamed else []
    if fallback:
        order = [x for x in sorted(listed, key=lambda x: (-x.cosine, x.stem))]
        dropped = [x.stem for x in order if rules.below_floor(x.cosine) and x.stem != renamed]
        queue = head + [x.stem for x in order if x.stem not in dropped and x.stem != renamed]
        return Shortlist(queue=queue, front=[], pair_flags=[], pair_completion_for=[], relations=dict(relations),
                         below_floor=dropped, n_below_floor=n_below, renamed=renamed)

    def cos(s: str) -> float:
        if s in by:
            return by[s].cosine
        c = cosine_of(s) if cosine_of else None
        return float(c) if c is not None else -1.0

    opposed = sorted((x for x in listed if relations.get(x.stem) == "opposed"), key=lambda x: (-x.cosine, x.stem))
    front: list[str] = []
    completion: list[str] = []
    partner_of: dict[str, list[str]] = {}
    for o in opposed:
        if o.partners:
            front += [p for p in o.partners if p not in front]
            for p in o.partners:
                partner_of.setdefault(p, []).append(o.stem)
        else:
            completion.append(o.stem)
    skipped: list[dict] = []
    if rules.skip_unrelated_partners:
        for p in front:
            if p != renamed and relations.get(p) in SKIP_PARTNER_RELATIONS:
                skipped.append({"stem": p, "relation": relations[p], "partner_of": sorted(partner_of.get(p, [])),
                                "cosine": round(cos(p), 6), "at": "shortlist"})
        gone = {x["stem"] for x in skipped}
        front = [p for p in front if p not in gone]
    front = sorted(front, key=lambda s: (-cos(s), s))
    similar = sorted((x for x in listed if relations.get(x.stem) in ("similar", "unsure")),
                     key=lambda x: (-x.cosine, x.stem))
    dropped = [x.stem for x in similar if rules.below_floor(x.cosine) and x.stem not in front and x.stem != renamed]
    notes = both_similar_notes(listed, relations) if rules.both_similar_excluded else []
    excluded = sorted({s for n in notes for s in n["pair"]} - {renamed})
    queue = [s for s in front + [x.stem for x in similar if x.stem not in front and x.stem not in dropped]
             if s not in excluded and s != renamed]
    queue = head + queue
    flags = []
    seen = set()
    for x in listed:
        p = x.pair_partner
        if not p or p not in by or (p, x.stem) in seen:
            continue
        seen.add((x.stem, p))
        ra, rb = relations.get(x.stem), relations.get(p)
        if ra == rb and ra in ("similar", "opposed"):
            flags.append({"pair": sorted([x.stem, p]), "both": ra})
    return Shortlist(queue=queue, front=front, pair_flags=flags, pair_completion_for=completion,
                     relations=dict(relations), pair_notes=notes, excluded=excluded, below_floor=dropped,
                     n_below_floor=n_below, renamed=renamed, partners_skipped=skipped)


# --------------------------------------------------------------------------- stage 4: the overlap walk

def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def sonnet_action(value: Any, c: Any) -> str:
    """The rule for Sonnet's reading of one pair at cut-off ``c`` (coding_plan_m3.md, stage 4; ``c`` an integer,
    read as the step rule's, or a :class:`CutOff`):

    * ``"cut"``: above c, covered by that trait directly;
    * ``"opus_confirms"``: above c where the cut-off rule does not let Sonnet cover alone (the graded rule at
      alignment score 2: both models must read c or more), Opus reads the pair and decides as at c;
    * ``"opus_decides"``: exactly c, Opus reads the pair and decides (c or above: covered);
    * ``"opus_check"``: c - 1, Opus reads the pair; an Opus reading of c or above marks the row for review
      and, under rule set 2 (decision 12), covers it (rule set 1: the candidate is not cut whatever Opus
      says).  Not where the cut-off rule has no Opus check (the graded rule at alignment score 2): ``"continue"``;
    * ``"continue"``: below c - 1;
    * ``"opposite"``: taken as it stands, no Opus (decision 9);
    * ``"opus_replaces"``: "unsure", Opus reads and its answer is used as if it were Sonnet's;
    * ``"unparsed"``: no reading (the answer failed to parse twice)."""
    spec = as_cut_off(c)
    if value is None:
        return "unparsed"
    if value == "opposite":
        return "opposite"
    if value == "unsure":
        return "opus_replaces"
    v = _int(value)
    if v is None:
        return "unparsed"
    if v > spec.c:
        return "cut" if spec.sonnet_alone else "opus_confirms"
    if v == spec.c:
        return "opus_decides"
    if v == spec.c - 1:
        return "opus_check" if spec.opus_check else "continue"
    return "continue"


OPUS_ROLES: dict[str, str] = {"opus_decides": "at_cut_off", "opus_check": "below_cut_off", "opus_replaces": "sonnet_unsure",
                              "opus_confirms": "above_cut_off"}


@dataclass
class Reading:
    position: int
    stem: str
    cosine: float
    relation: Optional[str]
    via: str
    sonnet: Optional[dict] = None     # {"value", "reason"} or {"value": None, "error"}
    opus: Optional[dict] = None
    opus_role: Optional[str] = None   # at_cut_off | below_cut_off | sonnet_unsure | above_cut_off
    outcome: Optional[str] = None     # cut | continue | rescued | review | opposite | unparsed | unsure | narrower
    queue_status: Optional[str] = None   # the trait read is a seed-queue entry with this status
    broader: Optional[dict] = None    # the broader check's two readings and verdict (:func:`broader_verdict`)

    def as_dict(self) -> dict:
        d = asdict(self)
        if d["queue_status"] is None:     # a corpus trait's reading: the fields it always had
            del d["queue_status"]
        if d["broader"] is None:          # no broader check on this reading
            del d["broader"]
        return d


def best_reading(r: "Reading") -> Optional[int]:
    """The highest numeric reading of a pair (Sonnet's or Opus's), ``None`` when neither is a number."""
    vals = [_int((x or {}).get("value")) for x in (r.sonnet, r.opus)]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


class Walk:
    """One candidate's overlap walk (stage 4), driven pair by pair: :meth:`next_pair` names the next trait
    to read, :meth:`give_sonnet` takes Sonnet's reading and says whether Opus must read it too,
    :meth:`give_opus` takes Opus's.  The walk stops at the first ``covered`` (early exit); when the queue
    runs out the candidate is ``new``, or ``grey`` when it carries a flag of ``rules.grey_kinds``.

    ``c``: the cut-off, an integer (read as the step rule's) or the candidate's :class:`CutOff`
    (:func:`cut_off_spec`, which the graded rule needs); ``queue``: the shortlist; ``info``: stem ->
    :class:`Listed` (cosine, relation via, partners) for the
    listed traits; ``cosine_of``: the cosine of a partner that is not listed; ``review``: flags carried in
    from stage 3 (``pair_flag`` under rule set 1, ``both_similar`` under 2, a relation call that never
    parsed); ``exclude``: traits never judged, not even as an opposite's partner (decision 13);
    ``queue_status``: stem -> status of the seed-queue entries in the index (a partner read that is not listed
    takes its status from here).

    Under ``rules.skip_unrelated_partners`` (rule set 3) a Sonnet "opposite" brings forward only the partners the
    relation call did not answer ``unrelated`` or ``opposed`` (the others go to ``partners_skipped``).  Under
    ``rules.broader_check`` a cover whose best reading is exactly 3 waits for the broader check
    (:attr:`needs_broader`, :meth:`give_broader`) before it is decided."""

    def __init__(self, key: str, c: Any, queue: Sequence[str], info: Mapping[str, Listed], *,
                 relations: Optional[Mapping[str, str]] = None, partners: Optional[Mapping[str, Sequence[str]]] = None,
                 cosine_of: Optional[Callable[[str], Optional[float]]] = None, review: Iterable[str] = (),
                 review_details: Iterable[Mapping] = (), pair_completion_for: Iterable[str] = (),
                 rules: Optional[Rules] = None, exclude: Iterable[str] = (),
                 queue_status: Optional[Mapping[str, str]] = None):
        self.key = key
        self.queue_status = dict(queue_status or {})
        self.spec = as_cut_off(c)
        self.c = self.spec.c
        self.rules = rules or DEFAULT_RULES
        self.partners_skipped: list[dict] = []
        self._broader_pending = False
        self.exclude: set[str] = set(exclude)
        self.queue: list[str] = [s for s in dict.fromkeys(queue) if s not in self.exclude]
        self.info = dict(info)
        self.relations = dict(relations or {})
        self.partners = {s: list(p) for s, p in (partners or {}).items()}
        for s, x in self.info.items():
            self.partners.setdefault(s, list(x.partners))
        self.cosine_of = cosine_of
        self.readings: list[Reading] = []
        self.judged: set[str] = set()
        self.current: Optional[Reading] = None
        self.review: list[str] = []
        self.review_details: list[dict] = []
        for k in review:
            self._flag(k)
        self.review_details += [dict(d) for d in review_details]
        self.pair_completion_for: list[str] = list(dict.fromkeys(pair_completion_for))
        self.decision: Optional[str] = None
        self.covered_by: Optional[str] = None
        self.covering: Optional[Reading] = None

    # -- state ---------------------------------------------------------------------
    @property
    def decided(self) -> bool:
        return self.decision is not None

    @property
    def needs_opus(self) -> bool:
        return self.current is not None and self.current.opus_role is not None and self.current.opus is None

    @property
    def needs_broader(self) -> bool:
        """The current pair would cover the candidate and waits for the broader check (:meth:`give_broader`)."""
        return self.current is not None and self._broader_pending

    def _flag(self, kind: str) -> None:
        if kind not in REVIEW_KINDS:
            raise ValueError(f"unknown review flag {kind!r}")
        if kind not in self.review:
            self.review.append(kind)

    def _cos(self, stem: str) -> float:
        if stem in self.info:
            return self.info[stem].cosine
        c = self.cosine_of(stem) if self.cosine_of else None
        return round(float(c), 6) if c is not None else 0.0

    def _finish(self) -> None:
        if self.decision is None:
            self.decision = "grey" if any(k in self.rules.grey_kinds for k in self.review) else "new"

    # -- driving -------------------------------------------------------------------
    def next_pair(self) -> Optional[str]:
        """The trait whose Sonnet reading comes next (the same one again while it is awaited); ``None`` when
        the walk is decided, or when the queue has run out (which decides it)."""
        if self.decided:
            return None
        if self.current is not None:
            return self.current.stem
        while self.queue:
            s = self.queue.pop(0)
            if s in self.judged or s in self.exclude:
                continue
            x = self.info.get(s)
            self.current = Reading(position=len(self.readings) + 1, stem=s, cosine=self._cos(s),
                                   relation=self.relations.get(s), via=x.via if x else "partner",
                                   queue_status=(x.queue_status if x else None) or self.queue_status.get(s))
            return s
        self._finish()
        return None

    def _close(self, outcome: str) -> None:
        r = self.current
        r.outcome = outcome
        self.readings.append(r)
        self.judged.add(r.stem)
        self.current = None

    def _cut(self) -> None:
        r = self.current
        if self.rules.broader_check and r.broader is None and best_reading(r) == 3:
            self._broader_pending = True          # the broader check decides (give_broader)
            return
        self.covered_by, self.covering, self.decision = r.stem, r, "covered"
        self._close("cut")

    def _skip_partner(self, p: str, of: str) -> None:
        for x in self.partners_skipped:
            if x["stem"] == p:
                if of not in x["partner_of"]:
                    x["partner_of"].append(of)
                return
        self.partners_skipped.append({"stem": p, "relation": self.relations.get(p), "partner_of": [of],
                                      "cosine": self._cos(p), "at": "opposite"})

    def _opposite(self) -> None:
        r = self.current
        partners = self.partners.get(r.stem) or []
        if partners:
            todo = [p for p in partners if p not in self.judged and p != r.stem and p not in self.exclude]
            if self.rules.skip_unrelated_partners:
                for p in todo:
                    if self.relations.get(p) in SKIP_PARTNER_RELATIONS:
                        self._skip_partner(p, r.stem)
                skip = {x["stem"] for x in self.partners_skipped}
                todo = [p for p in todo if p not in skip]
            todo = sorted(todo, key=lambda p: (-self._cos(p), p))
            self.queue = todo + [s for s in self.queue if s not in todo]
        elif r.stem not in self.pair_completion_for:
            self.pair_completion_for.append(r.stem)
        self._close("opposite")

    def give_sonnet(self, value: Any, reason: Optional[str] = None, *, error: Optional[str] = None) -> bool:
        """Sonnet's reading of the current pair (``value`` ``None`` with ``error`` when it never parsed).
        Returns True when Opus must read the pair too."""
        r = self.current
        if r is None:
            raise RuntimeError(f"{self.key}: no pair is awaiting a reading")
        r.sonnet = {"value": value, "reason": reason} if value is not None else {"value": None, "error": error}
        act = sonnet_action(value, self.spec)
        if act == "cut":
            self._cut()
        elif act == "continue":
            self._close("continue")
        elif act == "opposite":
            self._opposite()
        elif act == "unparsed":
            self._flag("unparsed")
            self.review_details.append({"kind": "unparsed", "stem": r.stem, "model": "sonnet", "error": error})
            self._close("unparsed")
        else:
            r.opus_role = OPUS_ROLES[act]
            return True
        return False

    def give_opus(self, value: Any, reason: Optional[str] = None, *, error: Optional[str] = None) -> None:
        """Opus's reading of the current pair (see :func:`sonnet_action` for what each role does with it)."""
        r = self.current
        if r is None or r.opus_role is None:
            raise RuntimeError(f"{self.key}: no pair is awaiting Opus")
        r.opus = {"value": value, "reason": reason} if value is not None else {"value": None, "error": error}
        v = _int(value)
        if value is None:
            self._flag("unparsed")
            self.review_details.append({"kind": "unparsed", "stem": r.stem, "model": "opus", "role": r.opus_role,
                                        "error": error})
            self._close("unparsed")
            return
        if r.opus_role in ("at_cut_off", "above_cut_off"):
            if v is not None and v >= self.c:
                self._cut()
            else:
                self._close("rescued")
        elif r.opus_role == "below_cut_off":
            if v is not None and v >= self.c:
                self._flag("sonnet_below_opus_at")
                self.review_details.append({"kind": "sonnet_below_opus_at", "stem": r.stem, "cut_off": self.c,
                                            "sonnet": r.sonnet, "opus": r.opus})
                if self.rules.cover_on_opus_check:      # decision 12: covered, flagged for review
                    self._cut()
                else:
                    self._close("review")
            else:
                self._close("continue")
        else:   # sonnet_unsure: Opus's answer stands for Sonnet's
            if value == "opposite":
                self._opposite()
            elif v is not None and v >= self.c:
                self._cut()
            elif v is not None:
                self._close("continue")
            else:
                self._close("unsure")

    def give_broader(self, straight: Optional[Mapping], swapped: Optional[Mapping]) -> None:
        """The broader check's two readings of the current pair (``{"value", "reason"}``, or ``None`` / a
        ``{"value": None, "error"}`` when one never parsed): ``straight`` with the candidate first, ``swapped`` with
        the corpus trait first (:func:`broader_verdict` under ``rules.broader_check``).  The cover stands
        (outcome ``cut``) unless the verdict is that the corpus trait is the narrower concept: then the reading
        closes as ``narrower``, the row is flagged ``cover_narrower`` and the walk goes on down the queue.  A
        reading that never parsed counts as no evidence (the cover stands) and flags the row ``unparsed``."""
        r = self.current
        if r is None or not self._broader_pending:
            raise RuntimeError(f"{self.key}: no pair is awaiting the broader check")
        self._broader_pending = False
        verdict = broader_verdict(straight, swapped, self.rules.broader_check)
        r.broader = verdict
        if verdict["unparsed"]:
            self._flag("unparsed")
            self.review_details.append({"kind": "unparsed", "stem": r.stem, "model": "broader",
                                        "orders": [o for o, s in zip(("straight", "swapped"), verdict["sides"]) if s is None]})
        if verdict["uncovers"]:
            self._flag("cover_narrower")
            self.review_details.append({"kind": "cover_narrower", "stem": r.stem, "cut_off": self.c,
                                        "sonnet": r.sonnet, "opus": r.opus, "broader": verdict})
            self._close("narrower")
            return
        self.covered_by, self.covering, self.decision = r.stem, r, "covered"
        self._close("cut")

    def summary(self) -> dict:
        return {"decision": self.decision, "covered_by": self.covered_by, "review": list(self.review),
                "pair_completion_for": list(self.pair_completion_for), "n_judged": len(self.readings),
                "exit_position": self.covering.position if self.covering else None}


def replay_walk(walk: Walk, readings: Mapping[str, Mapping]) -> Walk:
    """Drive ``walk`` from recorded readings (``{stem: {"sonnet": {...}, "opus": {...} | None}}``), as the
    full scan does after the fact.  A trait with no recorded reading (a partner outside the scanned list)
    is passed over with the outcome ``not_judged``.  Under the broader check a cover read at 3 takes the
    readings' ``broader`` (``{"straight", "swapped"}``); the full scan records none, so it does not run the check
    (``ValueError``)."""
    while not walk.decided:
        s = walk.next_pair()
        if s is None:
            break
        rec = readings.get(s)
        if rec is None or rec.get("sonnet") is None:
            walk._close("not_judged")
            continue
        son = rec["sonnet"]
        if walk.give_sonnet(son.get("value"), son.get("reason"), error=son.get("error")):
            op = rec.get("opus")
            if op is None:
                walk.current.opus_role = None
                walk._close("not_judged")
                continue
            walk.give_opus(op.get("value"), op.get("reason"), error=op.get("error"))
        if walk.needs_broader:
            b = rec.get("broader")
            if b is None:
                raise ValueError(f"{walk.key}: the broader check needs readings that are not on record for {s}")
            walk.give_broader(b.get("straight"), b.get("swapped"))
    return walk


def pair_verdict(sonnet: Any, opus: Any, c: Any) -> dict:
    """One pair under the rule, alone (the full scan's per-pair view; ``c`` an integer or a :class:`CutOff`):
    ``cut`` (Sonnet above c where it may cover alone, or Opus at c or above where Sonnet is at c or above or
    unsure), ``review`` (Sonnet c - 1 and Opus c or above, where the rule has the Opus check), ``opposite``,
    ``unparsed`` or ``keep``; ``at_or_above``: either model's reading is c or above."""
    act = sonnet_action(sonnet, c)
    c = as_cut_off(c).c
    o = _int(opus)
    s = _int(sonnet)
    at = (s is not None and s >= c) or (o is not None and o >= c)
    if act == "cut":
        v = "cut"
    elif act in ("opus_decides", "opus_replaces", "opus_confirms"):
        v = "cut" if (o is not None and o >= c) else ("opposite" if opus == "opposite" and act == "opus_replaces"
                                                     else ("unparsed" if opus is None else "keep"))
    elif act == "opus_check":
        v = "review" if (o is not None and o >= c) else "keep"
    elif act == "opposite":
        v = "opposite"
    elif act == "unparsed":
        v = "unparsed"
    else:
        v = "keep"
    return {"verdict": v, "at_or_above": bool(at)}


def verdict_cuts(verdict: str, rules: Optional[Rules] = None) -> bool:
    """Whether a :func:`pair_verdict` covers the candidate under ``rules``: ``cut`` always, ``review`` (Sonnet
    one below the cut-off, Opus at or above) under decision 12."""
    rules = rules or DEFAULT_RULES
    return verdict == "cut" or (verdict == "review" and rules.cover_on_opus_check)


def rules_of(block: Mapping) -> Rules:
    """The rule set a recorded block was decided under (a block from before rule set 2 has none: version 1)."""
    r = block.get("rules")
    if not r:
        return RULES[1]
    # a switch of 2026-10-12 a block does not name was at its default (rule sets 1 and 2 leave them out)
    return Rules(**{k: r[k] for k in Rules.__dataclass_fields__ if k in r})


# --------------------------------------------------------------------------- the broader check (audit P3)

#: The broader check's rubric (``reports/trait_gap_generation/rubrics/overlap_broader.md``), in the format of the
#: other rubric files.  **Pinned here, in code**, until it can join ``versions.json`` (``split_rubrics.M3_FILES``
#: and ``rubric_pins.py bump overlap_broader --version 1``): one version names one text, and
#: :func:`load_broader_rubric` refuses a text that is not the latest pin.  Append only.
BROADER_RUBRIC = "overlap_broader"
BROADER_FILE = "overlap_broader.md"
BROADER_PINS: dict[int, str] = {
    1: "a46cc766e7bbbb276939aad58cf879ac4e54d71a7820cba7ed252cb4f6068068",   # draft 1, 2026-10-12
}
#: The broader check's answers and its answer spec (the shape :func:`overlap_test.answer_value` reads).
BROADER_ANSWERS: tuple[str, ...] = ("first", "second", "neither", "unsure")
BROADER_SPEC: dict = {"key": "broader", "scale": (), "categories": BROADER_ANSWERS,
                      "aliases": {"the first": "first", "the second": "second", "same": "neither", "none": "neither"}}
#: The two orders each checked pair is read in: the candidate first, then the corpus trait first.
BROADER_ORDERS: tuple[str, ...] = ("straight", "swapped")


class BroaderRubricError(RuntimeError):
    """The broader check's rubric text on disk is not its latest pinned version (or the file is missing)."""


def load_broader_rubric(rubrics_dir: Optional[Path] = None) -> dict:
    """``{"name", "text", "version", "sha256"}`` of the broader check's rubric, the text inside the file's one
    "## The prompt" fenced block (the expression ``split_rubrics`` reads every rubric with); refuses
    (:class:`BroaderRubricError`) a text whose sha256 is not :data:`BROADER_PINS`' latest."""
    import hashlib
    from . import split_rubrics as sr
    from .paths import RUBRICS_DIR
    p = Path(rubrics_dir or RUBRICS_DIR) / BROADER_FILE
    if not p.exists():
        raise BroaderRubricError(f"{p}: rubric file missing")
    blocks = sr._BLOCK_RE.findall(p.read_text(encoding="utf-8"))    # noqa: SLF001 - the shared expression
    if len(blocks) != 1:
        raise BroaderRubricError(f"{p}: expected one '## The prompt' fenced block, found {len(blocks)}")
    text = blocks[0]
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    version = max(BROADER_PINS)
    if sha != BROADER_PINS[version]:
        known = [v for v, s in BROADER_PINS.items() if s == sha]
        raise BroaderRubricError(
            f"{BROADER_RUBRIC}: the text on disk (sha {sha[:12]}...) is not version {version}'s "
            f"({BROADER_PINS[version][:12]}...)" + (f"; it is version {known[0]}'s" if known else "")
            + ": pin a changed text as a new version in novelty.BROADER_PINS")
    return {"name": BROADER_RUBRIC, "text": text, "version": version, "sha256": sha}


def broader_payload(first: tuple[str, str], second: tuple[str, str], *, label_form: str = DEFAULT_LABEL_FORM) -> dict:
    """The broader check's user turn as an object: two traits, ``(label, description)`` each, under the neutral
    keys ``first`` and ``second`` (nothing says which is the candidate); labels in ``label_form``."""
    return {k: {"label": prompt_label(lb, label_form), "description": d}
            for k, (lb, d) in (("first", first), ("second", second))}


def render_broader_user(first: tuple[str, str], second: tuple[str, str], *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The broader check's user turn laid out as the overlap call's single form (``render_single``): the first
    trait on the first line, the second on the next, indented one space."""
    obj = broader_payload(first, second, label_form=label_form)
    return ('{"first": ' + json.dumps(obj["first"], ensure_ascii=False) + ",\n"
            ' "second": ' + json.dumps(obj["second"], ensure_ascii=False) + "}")


def broader_pair(order: str, cand: tuple[str, str], other: tuple[str, str]) -> tuple[tuple[str, str], tuple[str, str]]:
    """``(first, second)`` for ``order``: ``straight`` the candidate first, ``swapped`` the corpus trait first."""
    if order not in BROADER_ORDERS:
        raise ValueError(f"order must be one of {BROADER_ORDERS}, not {order!r}")
    return (cand, other) if order == "straight" else (other, cand)


def parse_broader(text: Optional[str]) -> tuple[dict, dict, dict]:
    """The broader check's answer, one object ``{"reason", "broader"}``, as :func:`overlap_test.parse_single`
    reads rubric A's single form: ``(rows, errors, meta)`` with the one pair as id 1; the last complete answer
    object in the text is the answer, fences and prose ignored, extra keys ignored and noted, the answer one of
    :data:`BROADER_ANSWERS` in any case (``"same"``, ``"none"``, ``"the first"`` and ``"the second"`` read as
    their answers)."""
    from .filter_rubric import _load_json
    spec = BROADER_SPEC
    key = spec["key"]
    meta: dict = {"n_rows": 0, "reason_first": None, "n_result_objects": 0, "extra_keys": [], "notes": []}
    if not text or not text.strip():
        return {}, {1: "empty response"}, meta
    objs = OT.single_objects(text, key)
    if not objs:
        try:
            obj = _load_json(text)
        except (ValueError, json.JSONDecodeError) as exc:
            return {}, {1: f"unparseable response: {exc}"}, meta
        if not (isinstance(obj, dict) and key in obj):
            return {}, {1: f"unparseable response: no object with {key!r}"}, meta
        objs = [obj]
    meta["n_result_objects"] = len(objs)
    row = objs[-1]
    if key not in row:
        return {}, {1: f"{key} missing"}, meta
    meta["n_rows"] = 1
    extra = sorted(k for k in row if k not in ("reason", key))
    if extra:
        meta["extra_keys"] = extra
        meta["notes"].append(f"extra keys {extra}")
    reason = row.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return {}, {1: "reason missing"}, meta
    val = OT.answer_value(row.get(key), spec["categories"], spec["scale"], spec["aliases"])
    if val is None:
        return {}, {1: f"{key} {row.get(key)!r} is not one of {list(BROADER_ANSWERS)}"}, meta
    keys = list(row.keys())
    out = {"reason": " ".join(reason.split()), "value": val, "reason_first": keys.index("reason") < keys.index(key)}
    meta["reason_first"] = out["reason_first"]
    return {1: out}, {}, meta


def broader_side(value: Any, order: str) -> Optional[str]:
    """One reading's answer from the candidate's side: ``candidate`` (the candidate is the broader concept, the
    corpus trait a narrower case of it), ``corpus`` (the reverse), ``neither``, ``unsure``; ``None`` for no
    answer.  ``order``: the order the reading was asked in (:data:`BROADER_ORDERS`)."""
    if value in ("neither", "unsure"):
        return value
    if value in ("first", "second"):
        cand_first = order == "straight"
        return "candidate" if (value == "first") == cand_first else "corpus"
    return None


#: A side's score for the ``mean`` gate: +1 the candidate broader, -1 the corpus trait, 0 otherwise.
_SIDE_SCORE = {"candidate": 1, "corpus": -1, "neither": 0, "unsure": 0}


def broader_verdict(straight: Optional[Mapping], swapped: Optional[Mapping], gate: Optional[str] = "mean") -> dict:
    """The broader check's verdict from its two readings (``{"value", "reason"}`` each, the order of
    :data:`BROADER_ORDERS`; ``None`` or a ``None`` value for one that never parsed): ``{"straight", "swapped",
    "sides": [side, side], "score": mean of the parsed sides' scores, "candidate_broader": how many readings call
    the candidate the broader, "gate", "uncovers", "unparsed"}``.  ``uncovers`` under ``gate``
    (:data:`BROADER_GATES`): ``mean``, the mean score above 0 (swap-averaged: one order naming the candidate and
    the other "neither" or "unsure" undoes the cover, two orders that contradict each other do not); ``both``, both
    readings name the candidate; ``either``, one does.  A reading that never parsed counts as no evidence."""
    gate = gate or "mean"
    if gate not in BROADER_GATES:
        raise ValueError(f"gate must be one of {BROADER_GATES}, not {gate!r}")
    sides = [broader_side((r or {}).get("value"), o) for r, o in zip((straight, swapped), BROADER_ORDERS)]
    scores = [_SIDE_SCORE[s] for s in sides if s is not None]
    score = sum(scores) / 2.0
    n_cand = sides.count("candidate")
    uncovers = {"mean": score > 0, "both": n_cand == 2, "either": n_cand >= 1}[gate]
    return {"straight": dict(straight) if straight else None, "swapped": dict(swapped) if swapped else None,
            "sides": sides, "score": score, "candidate_broader": n_cand, "gate": gate, "uncovers": bool(uncovers),
            "unparsed": any(s is None for s in sides)}


# --------------------------------------------------------------------------- stage 5: the block

def usage_dict(per_model: Mapping[str, Mapping]) -> dict:
    """``{"per_model": {model: {"n_calls", "prompt_tokens", "completion_tokens", "cost_usd"}}, "cost_usd"}``."""
    pm = {m: {k: (round(v[k], 6) if k == "cost_usd" else int(v[k])) for k in ("n_calls", "prompt_tokens",
                                                                           "completion_tokens", "cost_usd")}
          for m, v in sorted(per_model.items())}
    return {"per_model": pm, "cost_usd": round(sum(v["cost_usd"] for v in pm.values()), 6)}


def novelty_block(*, run_id: str, cand: Mapping, decision: str, reason: str, covered_by: Optional[str] = None,
                  match: Optional[Mapping] = None, walk: Optional[Walk] = None, listed: Sequence[Listed] = (),
                  relation: Optional[Mapping] = None, shortlist: Optional[Shortlist] = None,
                  rubrics: Mapping, config_version: str, embedding: Optional[Mapping] = None,
                  usage: Optional[Mapping] = None, at: str, mode: str = "shortlist", rules: Optional[Rules] = None,
                  renamed: Optional[Mapping] = None, extra: Optional[Mapping] = None,
                  cut_spec: Optional[CutOff] = None) -> dict:
    """The ``novelty`` block of one registry row (coding_plan_m3.md, stage 5).  ``reason``: ``exact_label``,
    ``overlap`` (the walk decided), or ``no_listed`` (nothing retrieved).  Rule set 2's additions: ``rules``
    (the switches and the floor, as the run used them), ``pair_notes`` (decision 13, with the noted members'
    cosines and any readings on record), ``n_below_floor`` (listed traits under the floor), ``below_floor``
    (the similar traits it kept out of the queue) and ``renamed_from`` (decision 15's match, judged).

    Seed-queue entries in the search (2026-10-09): a listed entry, a reading and the deciding reading carry
    ``queue_status`` when the trait is a queue entry, and a row the walk covered by one carries
    ``covered_by_queue: {"stem", "status"}`` (stage 0's queue match keeps its ``exact_label.match: "queue"``).
    Neither key appears where no queue entry is involved, so a block is unchanged when none is.

    Rule set 3 (2026-10-12): ``cut_off`` is the cut-off of the rule set's own rule, and a block decided under the
    graded rule says which part of it applied (``cut_off_rule``: :class:`CutOff`'s fields: ``c``, ``sonnet_alone``,
    ``opus_check``, ``rule``, ``band``); under the partner skip, ``partners_skipped`` lists every partner the
    opposite rule did not read because the relation call marked it unrelated or opposed (``at``: ``shortlist``,
    the front of the queue, or ``opposite``, after a Sonnet "opposite").  A step-rule block without the skip has
    neither key, as before.  The broader check's readings are on the reading they checked (``broader``)."""
    rules = rules or DEFAULT_RULES
    spec = as_cut_off(cut_spec) if cut_spec is not None else cut_off_spec(cand.get("alignment_score"), rules)
    review = list(walk.review) if walk else []
    details = list(walk.review_details) if walk else []
    pcf = list(walk.pair_completion_for) if walk else list((shortlist.pair_completion_for if shortlist else []))
    readings = [r.as_dict() for r in walk.readings] if walk else []
    deciding = None
    if walk and walk.covering:
        deciding = walk.covering.as_dict()
    cov_queue = None
    if walk and walk.covering and walk.covering.queue_status and covered_by is None:
        cov_queue = {"stem": walk.covering.stem, "status": walk.covering.queue_status}

    def listed_row(x: Listed) -> dict:
        d = {"stem": x.stem, "cosine": x.cosine, "rank": x.rank, "via": x.via,
             "relation": (shortlist.relations.get(x.stem) if shortlist else None)}
        return d | ({"queue_status": x.queue_status} if x.queue_status else {})
    out = {
        "run_id": run_id, "mode": mode, "decision": decision, "reason": reason,
        "covered_by": covered_by if covered_by is not None else (walk.covered_by if walk else None),
        "exact_label": dict(match) if match else None,
        "review": sorted(review, key=REVIEW_KINDS.index), "review_details": details,
        "pair_completion_for": pcf,
        "pair_flags": list(shortlist.pair_flags) if shortlist else [],
        "cut_off": spec.c, "alignment_score": cand.get("alignment_score"),
        "region": cand.get("region"),
        "deciding_reading": deciding,
        "readings": readings,
        "n_pairs_judged": len(readings),
        "listed": [listed_row(x) for x in listed],
        "shortlist": list(shortlist.queue) if shortlist else [],
        "relation": dict(relation) if relation else None,
        "rubrics": dict(rubrics), "config_version": config_version,
        "embedding": dict(embedding) if embedding else None,
        "rules": rules.as_dict(),
        "pair_notes": [dict(n) for n in shortlist.pair_notes] if shortlist else [],
        "n_below_floor": shortlist.n_below_floor if shortlist else 0,
        "below_floor": list(shortlist.below_floor) if shortlist else [],
        "renamed_from": dict(renamed) if renamed else None,
        "usage": dict(usage) if usage else usage_dict({}),
        "at": at,
    }
    if cov_queue:
        out["covered_by_queue"] = cov_queue
    if rules.cut_off_rule != "step":
        out["cut_off_rule"] = spec.as_dict()
    if rules.skip_unrelated_partners:
        out["partners_skipped"] = [dict(x) for x in (shortlist.partners_skipped if shortlist else [])] + \
            [dict(x, partner_of=list(x["partner_of"])) for x in (walk.partners_skipped if walk else [])]
    return out | dict(extra or {})


def reading_rows(run_id: str, cand: Mapping, block: Mapping) -> list[dict]:
    """``readings.jsonl`` lines for one candidate: one per pair judged, beside its cosine (design item 7)."""
    out = []
    for r in block.get("readings") or []:
        out.append({"run_id": run_id, "key": cand["key"], "label": cand["label"], "cut_off": block["cut_off"],
                    "alignment_score": block["alignment_score"], "decision": block["decision"], **r})
    return out


# --------------------------------------------------------------------------- review order and synonyms

def _alignment_section(nv: Mapping) -> str:
    a = nv.get("alignment_score")
    return "alignment" if (isinstance(a, int) and not isinstance(a, bool) and a >= 2) or \
        nv.get("region") == "alignment_ai_agent" else "other"


def in_review_queue(nv: Mapping) -> bool:
    """A row in the review queue (decision 14): ``grey``, or carrying a flag of :data:`QUEUE_KINDS` whatever
    its decision (the covered-and-flagged rows of decision 12, the both-similar notes of decision 13)."""
    return nv.get("decision") == "grey" or any(k in QUEUE_KINDS for k in nv.get("review") or [])


def review_order(rows: Iterable[Mapping], *, include_new: bool = False, run_id: Optional[str] = None
                 ) -> list[tuple[str, str]]:
    """``[(section, key), ...]``: the review queue (:func:`in_review_queue`; and with ``include_new`` the other
    ``new`` rows after it), the alignment section first (alignment score 2 or 3, or the alignment region), then
    the rest; within a section the ``grey`` rows first, then the covered-and-flagged, then the kept ones, more
    review flags first, then by key.  ``rows`` are registry rows (or ``{"key", "novelty"}``)."""
    rank = {"grey": 0, "covered": 1, "new": 2}
    items = []
    for r in rows:
        nv = r.get("novelty") or {}
        if run_id is not None and nv.get("run_id") != run_id:
            continue
        queued = in_review_queue(nv)
        if not queued and not (include_new and nv.get("decision") == "new"):
            continue
        sec = _alignment_section(nv)
        items.append((sec, 0 if queued else 1, rank.get(nv.get("decision"), 3), -len(nv.get("review") or []), r["key"]))
    items.sort(key=lambda x: (0 if x[0] == "alignment" else 1, x[1], x[2], x[3], x[4]))
    return [(sec, key) for sec, _, _, _, key in items]


def synonyms(rows: Iterable[Mapping], *, stem: Optional[str] = None, run_id: Optional[str] = None) -> list[dict]:
    """The rename shortlist (design item 8): every covered candidate grouped under its ``covered_by`` trait,
    traits whose candidates read 4 first, then 3, then the rest (exact-label matches last); within a trait,
    its candidates by their best reading, then by label.  Each entry:
    ``{"stem", "best", "candidates": [{"key", "label", "gloss", "best", "reading", "reason", "run_id"}]}``."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        nv = r.get("novelty") or {}
        if nv.get("decision") != "covered" or not nv.get("covered_by"):
            continue
        if run_id is not None and nv.get("run_id") != run_id:
            continue
        if stem is not None and nv["covered_by"] != stem:
            continue
        d = nv.get("deciding_reading") or {}
        vals = [_int((d.get(m) or {}).get("value")) for m in ("sonnet", "opus")]
        vals = [v for v in vals if v is not None]
        best = max(vals) if vals else None
        groups.setdefault(nv["covered_by"], []).append({
            "key": r["key"], "label": r.get("label"), "gloss": r.get("gloss"), "best": best,
            "reason": nv.get("reason"), "reading": {m: d.get(m) for m in ("sonnet", "opus")} if d else None,
            "exact_label": nv.get("exact_label"), "run_id": nv.get("run_id"),
            "covered_by_queue": nv.get("covered_by_queue")})
    out = []
    for s, cands in groups.items():
        bests = [c["best"] for c in cands if c["best"] is not None]
        best = max(bests) if bests else None
        cands.sort(key=lambda c: (-(c["best"] if c["best"] is not None else -1), str(c["label"])))
        out.append({"stem": s, "best": best, "candidates": cands})
    out.sort(key=lambda g: (-(g["best"] if g["best"] is not None else -1), g["stem"]))
    return out
