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
   (kept, with a review flag: ``sonnet_below_opus_at``, ``unparsed`` or ``pair_flag``).

By-products: every reading beside its cosine (``readings.jsonl``, :func:`reading_rows`), the review queue
(:func:`review_order`) and the rename shortlist (:func:`synonyms`).
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import normalize_to_file_name

from . import overlap_test as OT

# --------------------------------------------------------------------------- constants

DECISIONS: tuple[str, ...] = ("covered", "new", "grey")
#: The review flags that make a kept candidate ``grey`` (coding_plan_m3.md, stage 5).
REVIEW_KINDS: tuple[str, ...] = ("sonnet_below_opus_at", "unparsed", "pair_flag")
RELATION_ANSWERS: tuple[str, ...] = ("similar", "opposed", "unrelated", "unsure")
#: The relation rubric's answer, in the shape :func:`overlap_test.parse_list` reads.
RELATION_SPEC: dict = {"key": "relation", "scale": (), "categories": RELATION_ANSWERS}
RELATION_RUBRIC = "relation"
#: The overlap call's rubric: rubric A (``overlap_concept``), one pair per call from version 5.
OVERLAP_RUBRIC = "A"
HAIKU, SONNET, OPUS = OT.HAIKU, OT.SONNET, OT.OPUS
#: Arrangement kinds whose members are mutually opposed and expand each other (pair and simplexes).
EXPANDING_FIXED = ("pair", "triangle", "tetrahedron")
#: How the candidate is embedded: ``label_gloss`` (the brief: "the candidate's label plus gloss", the
#: corpus side's form, cut to the covered representation) or ``gloss_w14`` (metric_config.json's
#: ``covered.query_form``: the gloss alone, no label, cut to 14 words, the form M2 measured recall on).
QUERY_FORMS: tuple[str, ...] = ("label_gloss", "gloss_w14")
DEFAULT_QUERY_FORM = "label_gloss"


def is_expanding(kind: str) -> bool:
    """Pairs, triangles, tetrahedra and larger simplexes expand; nothing else does."""
    return kind in EXPANDING_FIXED or kind.endswith("-simplex")


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
        for a in rec.arrangements:
            if is_expanding(a.kind):
                others = [m for m in a.members if m != stem]
                expands.update(others)
                if a.kind != "pair":
                    corners.update(others)
        if partner:
            expands.add(partner)
        partners = ([partner] if partner else []) + sorted(c for c in corners if c != partner)
        out[stem] = CorpusTrait(stem=stem, label=doc.get("positive_label") or stem.replace("_", " "),
                                description=doc.get("description") or "", negative_label=rec.negative_label,
                                pair_partner=partner, partners=partners, expands_to=sorted(expands),
                                renamed_from=_renamed_from(doc.get("renamed_from")))
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

@dataclass
class LabelSets:
    corpus: set
    queue: dict          # stem -> {"stem", "status", "entity_type"} (stems and normalised labels)
    renamed: dict        # old stem -> current corpus stem


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


def exact_label_match(stem: str, sets: LabelSets) -> Optional[dict]:
    """``{"covered_by", "match", ...}`` when the candidate's normalised label is a corpus stem
    (``match: "corpus"``), a renamed stem (``"renamed_from"``, covered by the current stem) or a queue
    name (``"queue"``, covered by the entry's stem); else ``None``.  The corpus is checked first."""
    if stem in sets.corpus:
        return {"covered_by": stem, "match": "corpus"}
    if stem in sets.renamed:
        return {"covered_by": sets.renamed[stem], "match": "renamed_from", "old_stem": stem}
    if stem in sets.queue:
        e = sets.queue[stem]
        return {"covered_by": e.get("stem") or stem, "match": "queue", "queue_status": e.get("status"),
                "entity_type": e.get("entity_type")}
    return None


# --------------------------------------------------------------------------- stages 1-2: retrieval and expansion

@dataclass
class Listed:
    stem: str
    cosine: float
    rank: Optional[int]          # 1..k for a retrieved trait, None for an added one
    via: str                     # "retrieved" | "expanded"
    expanded_from: list = field(default_factory=list)
    partners: list = field(default_factory=list)
    pair_partner: Optional[str] = None


def expand(retrieved: Sequence[tuple[str, float]], traits: Mapping[str, CorpusTrait],
           cosine_of: Callable[[str], Optional[float]]) -> list[Listed]:
    """The listed traits: the retrieved ones in order, then the members their arrangements add (once each,
    by cosine, highest first), each with its own cosine to the candidate and its partners."""
    out: dict[str, Listed] = {}
    for rank, (s, cos) in enumerate(retrieved, 1):
        t = traits[s]
        out[s] = Listed(stem=s, cosine=round(float(cos), 6), rank=rank, via="retrieved", partners=list(t.partners),
                        pair_partner=t.pair_partner)
    added: dict[str, Listed] = {}
    for s, _ in retrieved:
        for m in traits[s].expands_to:
            if m in out or m not in traits:
                continue
            if m not in added:
                c = cosine_of(m)
                t = traits[m]
                added[m] = Listed(stem=m, cosine=round(float(c), 6) if c is not None else 0.0, rank=None,
                                  via="expanded", partners=list(t.partners), pair_partner=t.pair_partner)
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


def build_shortlist(listed: Sequence[Listed], relations: Mapping[str, str],
                    cosine_of: Optional[Callable[[str], Optional[float]]] = None) -> Shortlist:
    """Stage 3's outputs from the final relations (after the unsure re-ask).  ``cosine_of`` gives the cosine
    of a partner that is not listed (a corner of an expanded trait's own simplex)."""
    by = {x.stem: x for x in listed}

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
    similar = sorted((x for x in listed if relations.get(x.stem) == "similar"), key=lambda x: (-x.cosine, x.stem))
    queue = front + [x.stem for x in similar if x.stem not in front]
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
                     relations=dict(relations))


# --------------------------------------------------------------------------- stage 4: the overlap walk

def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def sonnet_action(value: Any, c: int) -> str:
    """The rule for Sonnet's reading of one pair at cut-off ``c`` (coding_plan_m3.md, stage 4):

    * ``"cut"``: above c, covered by that trait directly;
    * ``"opus_decides"``: exactly c, Opus reads the pair and decides (c or above: covered);
    * ``"opus_check"``: c - 1, Opus reads the pair, the candidate is not cut whatever it says, and an
      Opus reading of c or above marks the row for review;
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
    runs out the candidate is ``new``, or ``grey`` when it carries a review flag.

    ``queue``: the shortlist; ``info``: stem -> :class:`Listed` (cosine, relation via, partners) for the
    listed traits; ``cosine_of``: the cosine of a partner that is not listed; ``review``: flags carried in
    from stage 3 (``pair_flag``, a relation call that never parsed)."""

    def __init__(self, key: str, c: int, queue: Sequence[str], info: Mapping[str, Listed], *,
                 relations: Optional[Mapping[str, str]] = None, partners: Optional[Mapping[str, Sequence[str]]] = None,
                 cosine_of: Optional[Callable[[str], Optional[float]]] = None, review: Iterable[str] = (),
                 review_details: Iterable[Mapping] = (), pair_completion_for: Iterable[str] = ()):
        self.key = key
        self.c = int(c)
        self.queue: list[str] = list(dict.fromkeys(queue))
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
            self.decision = "grey" if self.review else "new"

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
            if s in self.judged:
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
            todo = sorted((p for p in partners if p not in self.judged and p != r.stem), key=lambda p: (-self._cos(p), p))
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
                  usage: Optional[Mapping] = None, at: str, mode: str = "shortlist") -> dict:
    """The ``novelty`` block of one registry row (coding_plan_m3.md, stage 5).  ``reason``: ``exact_label``,
    ``overlap`` (the walk decided), or ``no_listed`` (nothing retrieved)."""
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
        "usage": dict(usage) if usage else usage_dict({}),
        "at": at,
    }


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


def review_order(rows: Iterable[Mapping], *, include_new: bool = False, run_id: Optional[str] = None
                 ) -> list[tuple[str, str]]:
    """``[(section, key), ...]``: the ``grey`` rows (and with ``include_new`` the ``new`` ones after them),
    the alignment section first (alignment score 2 or 3, or the alignment region), then the rest; within a
    section, more review flags first, then by key.  ``rows`` are registry rows (or ``{"key", "novelty"}``)."""
    want = ("grey", "new") if include_new else ("grey",)
    items = []
    for r in rows:
        nv = r.get("novelty") or {}
        if nv.get("decision") not in want or (run_id is not None and nv.get("run_id") != run_id):
            continue
        sec = _alignment_section(nv)
        items.append((sec, want.index(nv["decision"]), -len(nv.get("review") or []), r["key"]))
    items.sort(key=lambda x: (0 if x[0] == "alignment" else 1, x[1], x[2], x[3]))
    return [(sec, key) for sec, _, _, key in items]


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
