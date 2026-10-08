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
1. **Retrieve** the ``k`` nearest corpus traits in the covered setting (:class:`CorpusIndex`).
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
   sides is a ``pair_flag``.
4. **Overlap walk** (:class:`Walk`): one pair per call down the queue, Sonnet first, with the rule of
   :func:`sonnet_action` and early exit at the first ``covered``.
5. **Decision and block** (:func:`novelty_block`): ``covered`` (with ``covered_by``), ``new``, or ``grey``
   (kept, with a review flag that the rule set treats as grey: see :class:`Rules`).

The decision rules come in two versions (:data:`RULES`).  Version 1 is the pilot's (decisions 1-11 of
``coding_plan_platform.md``'s M3 section); version 2, the default from 2026-10-07, adds decisions 12-15 and
the cosine floor (coding_plan_m3.md, "Round 2"): a Sonnet reading one below the cut-off that Opus reads at
or above it covers, flagged; both ends of a recorded pair (every corner of a simplex) marked similar are
taken out of the shortlist and noted; the pair flag is a note, not a reason for ``grey``; a ``renamed_from``
match is judged like any other candidate, with the current trait at the front, and labels are compared
separator-blind; listed traits below the cosine floor are not judged (an opposed trait's partner and a
``renamed_from`` match are).  Version 1 stays so that a run can be re-decided under the pilot's rules and
shown to reproduce it.

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

# --------------------------------------------------------------------------- constants

DECISIONS: tuple[str, ...] = ("covered", "new", "grey")
#: Every review flag a row can carry (coding_plan_m3.md, stage 5; ``both_similar`` from decision 13).  Which
#: of them make a kept candidate ``grey`` is the rule set's :attr:`Rules.grey_kinds`.
REVIEW_KINDS: tuple[str, ...] = ("sonnet_below_opus_at", "unparsed", "pair_flag", "both_similar")
#: The flags that put a row in the review queue whatever its decision (decision 14: the covered-and-flagged
#: rows, the both-similar notes and ``unparsed``); a ``grey`` row is always in it.
QUEUE_KINDS: tuple[str, ...] = ("sonnet_below_opus_at", "both_similar", "unparsed")
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


def is_expanding(kind: str) -> bool:
    """Pairs, triangles, tetrahedra and larger simplexes expand; nothing else does."""
    return kind in EXPANDING_FIXED or kind.endswith("-simplex")


# --------------------------------------------------------------------------- the decision rules

@dataclass(frozen=True)
class Rules:
    """One version of M3's decision rules (the module docstring).  Each switch is one decision of
    ``coding_plan_platform.md``'s M3 section, so that a change in a re-decided run can be traced to one."""
    name: str
    version: int
    cover_on_opus_check: bool        # decision 12: Sonnet c - 1, Opus c or above -> covered, flagged
    both_similar_excluded: bool      # decision 13: both ends of a pair similar -> neither is judged, a note
    pair_flag_grey: bool             # decision 14 off: a pair flag makes a kept row grey
    renamed_from_covers: bool        # decision 15 off: a renamed_from match covers at stage 0
    separator_blind: bool            # decision 15: labels compared with the separators taken out
    cosine_floor: Optional[float]    # listed traits below it are not judged (None: no floor)

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

    def below_floor(self, cosine: Optional[float]) -> bool:
        return self.cosine_floor is not None and cosine is not None and float(cosine) < self.cosine_floor

    def as_dict(self) -> dict:
        return asdict(self)


#: Version 1: the pilot's rules (decisions 1-11).  Version 2: decisions 12-15 and the floor (2026-10-07).
RULES: dict[int, Rules] = {
    1: Rules(name="m3_rules_1", version=1, cover_on_opus_check=False, both_similar_excluded=False,
             pair_flag_grey=True, renamed_from_covers=True, separator_blind=False, cosine_floor=None),
    2: Rules(name="m3_rules_2", version=2, cover_on_opus_check=True, both_similar_excluded=True,
             pair_flag_grey=False, renamed_from_covers=False, separator_blind=True, cosine_floor=DEFAULT_COSINE_FLOOR),
}
DEFAULT_RULES = RULES[2]
#: The steps from version 1 to version 2, one decision each, in the order a re-decided run attributes its
#: changes (``novelty_score.py score --redecide``): each step adds one switch to the ones before it.
RULE_STEPS: tuple[tuple[str, dict], ...] = (
    ("decision 14 (pair flag a note)", {"pair_flag_grey": False}),
    ("decision 12 (covered, flagged)", {"cover_on_opus_check": True}),
    ("decision 13 (both ends similar)", {"both_similar_excluded": True}),
    ("decision 15 (labels: renamed_from judged, separator-blind)", {"renamed_from_covers": False, "separator_blind": True}),
    ("cosine floor", {"cosine_floor": DEFAULT_COSINE_FLOOR}),
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


def cut_off(alignment_score: Any) -> int:
    """The covered cut-off on rubric A's scale (design item 6, decision 4): 3 far from alignment
    (alignment score 0 or 1), 4 near it (2 or 3).  A missing score takes the near-alignment cut-off,
    the one that cuts less (a candidate is never cut on a guess)."""
    if isinstance(alignment_score, bool) or alignment_score is None:
        return 4
    try:
        a = int(alignment_score)
    except (TypeError, ValueError):
        return 4
    return 3 if a <= 1 else 4


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


@dataclass
class CorpusIndex:
    """The corpus rows in the covered space (unit rows: a dot product is the cosine) and the transform
    that maps a candidate's raw embedding into the same space (fitted on the corpus only)."""
    stems: list
    Z: np.ndarray
    transform: Any
    traits: dict
    settings: dict

    def __post_init__(self):
        self._row = {s: i for i, s in enumerate(self.stems)}

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
                settings: Optional[Mapping] = None) -> CorpusIndex:
    """``E_raw``: the corpus embeddings, one row per trait in ``sorted(traits)`` order."""
    from .embed import normalize_rows
    from .space import fit_space
    stems = sorted(traits)
    E = normalize_rows(np.asarray(E_raw))
    if E.shape[0] != len(stems):
        raise ValueError(f"{E.shape[0]} corpus rows for {len(stems)} traits")
    T = fit_space(E, variant)
    return CorpusIndex(stems=stems, Z=T.apply(E), transform=T, traits=dict(traits),
                       settings=dict(settings or {}, variant=variant, n_corpus=len(stems)))


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
    (any status, either entity type: a queued name is decided or in hand), and every ``renamed_from``."""
    q: dict[str, dict] = {}
    for e in queue.get("entries") or []:
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
    only in its separators matches too (``"blind": True``, ``"matched": <the name>``)."""
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


def listed_from(stem: str, cosine: float, traits: Mapping[str, CorpusTrait], *, rank: Optional[int], via: str) -> Listed:
    t = traits[stem]
    return Listed(stem=stem, cosine=round(float(cosine), 6), rank=rank, via=via, partners=list(t.partners),
                  pair_partner=t.pair_partner, simplexes=[dict(s) for s in t.simplexes])


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


def relation_payload(label: str, description: str, traits: Sequence[tuple[str, str]]) -> dict:
    return {"candidate": {"label": label, "description": description},
            "traits": [{"id": i, "label": lb, "description": d} for i, (lb, d) in enumerate(traits, 1)]}


def render_relation_user(label: str, description: str, traits: Sequence[tuple[str, str]]) -> str:
    """The relation call's user turn, laid out as the overlap test's list form (``render_payload``): the
    candidate on the first line, each listed trait on its own line, ids 1..n in the order given."""
    obj = relation_payload(label, description, traits)
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
    call said, the floor and the exclusion notwithstanding."""
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
    for o in opposed:
        if o.partners:
            front += [p for p in o.partners if p not in front]
        else:
            completion.append(o.stem)
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
                     n_below_floor=n_below, renamed=renamed)


# --------------------------------------------------------------------------- stage 4: the overlap walk

def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def sonnet_action(value: Any, c: int) -> str:
    """The rule for Sonnet's reading of one pair at cut-off ``c`` (coding_plan_m3.md, stage 4):

    * ``"cut"``: above c, covered by that trait directly;
    * ``"opus_decides"``: exactly c, Opus reads the pair and decides (c or above: covered);
    * ``"opus_check"``: c - 1, Opus reads the pair; an Opus reading of c or above marks the row for review
      and, under rule set 2 (decision 12), covers it (rule set 1: the candidate is not cut whatever Opus
      says);
    * ``"continue"``: below c - 1;
    * ``"opposite"``: taken as it stands, no Opus (decision 9);
    * ``"opus_replaces"``: "unsure", Opus reads and its answer is used as if it were Sonnet's;
    * ``"unparsed"``: no reading (the answer failed to parse twice)."""
    if value is None:
        return "unparsed"
    if value == "opposite":
        return "opposite"
    if value == "unsure":
        return "opus_replaces"
    v = _int(value)
    if v is None:
        return "unparsed"
    if v > c:
        return "cut"
    if v == c:
        return "opus_decides"
    if v == c - 1:
        return "opus_check"
    return "continue"


OPUS_ROLES: dict[str, str] = {"opus_decides": "at_cut_off", "opus_check": "below_cut_off", "opus_replaces": "sonnet_unsure"}


@dataclass
class Reading:
    position: int
    stem: str
    cosine: float
    relation: Optional[str]
    via: str
    sonnet: Optional[dict] = None     # {"value", "reason"} or {"value": None, "error"}
    opus: Optional[dict] = None
    opus_role: Optional[str] = None   # at_cut_off | below_cut_off | sonnet_unsure
    outcome: Optional[str] = None     # cut | continue | rescued | review | opposite | unparsed | unsure

    def as_dict(self) -> dict:
        return asdict(self)


class Walk:
    """One candidate's overlap walk (stage 4), driven pair by pair: :meth:`next_pair` names the next trait
    to read, :meth:`give_sonnet` takes Sonnet's reading and says whether Opus must read it too,
    :meth:`give_opus` takes Opus's.  The walk stops at the first ``covered`` (early exit); when the queue
    runs out the candidate is ``new``, or ``grey`` when it carries a flag of ``rules.grey_kinds``.

    ``queue``: the shortlist; ``info``: stem -> :class:`Listed` (cosine, relation via, partners) for the
    listed traits; ``cosine_of``: the cosine of a partner that is not listed; ``review``: flags carried in
    from stage 3 (``pair_flag`` under rule set 1, ``both_similar`` under 2, a relation call that never
    parsed); ``exclude``: traits never judged, not even as an opposite's partner (decision 13)."""

    def __init__(self, key: str, c: int, queue: Sequence[str], info: Mapping[str, Listed], *,
                 relations: Optional[Mapping[str, str]] = None, partners: Optional[Mapping[str, Sequence[str]]] = None,
                 cosine_of: Optional[Callable[[str], Optional[float]]] = None, review: Iterable[str] = (),
                 review_details: Iterable[Mapping] = (), pair_completion_for: Iterable[str] = (),
                 rules: Optional[Rules] = None, exclude: Iterable[str] = ()):
        self.key = key
        self.c = int(c)
        self.rules = rules or DEFAULT_RULES
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
                                   relation=self.relations.get(s), via=x.via if x else "partner")
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
        self.covered_by, self.covering, self.decision = r.stem, r, "covered"
        self._close("cut")

    def _opposite(self) -> None:
        r = self.current
        partners = self.partners.get(r.stem) or []
        if partners:
            todo = sorted((p for p in partners if p not in self.judged and p != r.stem and p not in self.exclude),
                          key=lambda p: (-self._cos(p), p))
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
        act = sonnet_action(value, self.c)
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
        if r.opus_role == "at_cut_off":
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

    def summary(self) -> dict:
        return {"decision": self.decision, "covered_by": self.covered_by, "review": list(self.review),
                "pair_completion_for": list(self.pair_completion_for), "n_judged": len(self.readings),
                "exit_position": self.covering.position if self.covering else None}


def replay_walk(walk: Walk, readings: Mapping[str, Mapping]) -> Walk:
    """Drive ``walk`` from recorded readings (``{stem: {"sonnet": {...}, "opus": {...} | None}}``), as the
    full scan does after the fact.  A trait with no recorded reading (a partner outside the scanned list)
    is passed over with the outcome ``not_judged``."""
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
    return walk


def pair_verdict(sonnet: Any, opus: Any, c: int) -> dict:
    """One pair under the rule, alone (the full scan's per-pair view): ``cut`` (Sonnet above c, or Opus at c
    or above where Sonnet is at c or unsure), ``review`` (Sonnet c - 1 and Opus c or above), ``opposite``,
    ``unparsed`` or ``keep``; ``at_or_above``: either model's reading is c or above."""
    act = sonnet_action(sonnet, c)
    o = _int(opus)
    s = _int(sonnet)
    at = (s is not None and s >= c) or (o is not None and o >= c)
    if act == "cut":
        v = "cut"
    elif act in ("opus_decides", "opus_replaces"):
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
    return Rules(**{k: r[k] for k in Rules.__dataclass_fields__})


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
                  renamed: Optional[Mapping] = None, extra: Optional[Mapping] = None) -> dict:
    """The ``novelty`` block of one registry row (coding_plan_m3.md, stage 5).  ``reason``: ``exact_label``,
    ``overlap`` (the walk decided), or ``no_listed`` (nothing retrieved).  Rule set 2's additions: ``rules``
    (the switches and the floor, as the run used them), ``pair_notes`` (decision 13, with the noted members'
    cosines and any readings on record), ``n_below_floor`` (listed traits under the floor), ``below_floor``
    (the similar traits it kept out of the queue) and ``renamed_from`` (decision 15's match, judged)."""
    rules = rules or DEFAULT_RULES
    review = list(walk.review) if walk else []
    details = list(walk.review_details) if walk else []
    pcf = list(walk.pair_completion_for) if walk else list((shortlist.pair_completion_for if shortlist else []))
    readings = [r.as_dict() for r in walk.readings] if walk else []
    deciding = None
    if walk and walk.covering:
        deciding = walk.covering.as_dict()
    return {
        "run_id": run_id, "mode": mode, "decision": decision, "reason": reason,
        "covered_by": covered_by if covered_by is not None else (walk.covered_by if walk else None),
        "exact_label": dict(match) if match else None,
        "review": sorted(review, key=REVIEW_KINDS.index), "review_details": details,
        "pair_completion_for": pcf,
        "pair_flags": list(shortlist.pair_flags) if shortlist else [],
        "cut_off": cut_off(cand.get("alignment_score")), "alignment_score": cand.get("alignment_score"),
        "region": cand.get("region"),
        "deciding_reading": deciding,
        "readings": readings,
        "n_pairs_judged": len(readings),
        "listed": [{"stem": x.stem, "cosine": x.cosine, "rank": x.rank, "via": x.via,
                    "relation": (shortlist.relations.get(x.stem) if shortlist else None)} for x in listed],
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
    } | dict(extra or {})


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
            "exact_label": nv.get("exact_label"), "run_id": nv.get("run_id")})
    out = []
    for s, cands in groups.items():
        bests = [c["best"] for c in cands if c["best"] is not None]
        best = max(bests) if bests else None
        cands.sort(key=lambda c: (-(c["best"] if c["best"] is not None else -1), str(c["label"])))
        out.append({"stem": s, "best": best, "candidates": cands})
    out.sort(key=lambda g: (-(g["best"] if g["best"] is not None else -1), g["stem"]))
    return out
