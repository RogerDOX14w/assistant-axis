"""Labelled trait pairs for metric calibration (M2, plan 15 steps 4 and 7).

``build_labelled_pairs`` seeds ``data/candidates/calibration/labelled_pairs.json``
from what the project already knows, then applies the hand-check recorded in
``labelled_pairs_curation.json`` beside it (exclusions with reasons, relabels,
``uncertain`` marks, and hand-added pairs), so the hand decisions survive a
rebuild and can be read and edited by Roger.

Relations (``RELATIONS``):

* ``antonym``: the corpus's recorded clean pairs (``arrangement`` kind
  ``pair``), the reciprocal negative-label pairs
  (``arrangements.reciprocal_pairs``), plus ``trait_antonyms_v4.json``
  judgements scored >= 4 whose ``negative_label`` is an existing stem.
* ``duplicate``: a seed-queue entry Roger turned down as covered by an
  existing trait (``not_adopted`` / ``superseded`` decisions naming the
  neighbour), with the entry's own description; plus plan 11 §6's
  duplicates where both sides have text.
* ``deliberate_duplicate``: a deliberate near-duplicate in the corpus (a
  plain-language counterpart of a named position; later, a standard's pole).
* ``near_distinct``: distinct neighbours: plan 11 §6's near-but-distinct and
  narrower/broader pairs, and members of the same non-pair arrangement
  (triangle, tetrahedron, sequence).
* ``polysemy_reject``: a queue entry rejected because its description did not
  match the word; the pair is the description against the bare label.
* ``unrelated``: random corpus pairs, never a labelled pair or an arrangement.

Members are corpus stems (``honorable``), queue entries embedded from their
description (``queue:aloof``), or bare labels (``label:economic``); the
latter two live in ``externals`` with their text.  Folds (``group_folds``)
are drawn over connected components of the labelled-pair graph, so no
entity, and therefore no pair, straddles two folds; unrelated pairs are
sampled inside a fold.

Renames (2026-10-02, the merge with the main line): a stem the corpus has
renamed (``renamed_from`` in the current file; :func:`corpus_renames`) is read
as the current stem wherever the sources name it (v4 judgements, seed-queue
decisions, the curation file), except for the renames in
:data:`SENSE_CHANGED_RENAMES`, whose old records do not describe the trait
that carries the name now.  Curation entries that no longer apply (a member
that is neither a corpus stem nor an external, a relabel / exclude / keep
naming a pair no source produces) are skipped and listed in
``curation_unused``.
"""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.arrangements import is_ordered, load_corpus_arrangements, reciprocal_pairs

from .registry import utc_now

#: The row sources a curation ``keep_only`` entry judges.
MECHANICAL_SOURCES = ("seed_queue_decision", "corpus_source_field")
RELATIONS = ("antonym", "duplicate", "deliberate_duplicate", "near_distinct", "polysemy_reject", "unrelated")
SCHEMA_VERSION = 1
V4_MIN_SCORE = 4

#: Renames whose description changed sense with the label (checked 2026-10-02 at the merge with the main
#: line, against the descriptions before it): bland -> dull, a flat, colourless voice became a presence
#: that draws no one in; libertarian -> metaphysical_libertarian, rewritten to the metaphysical sense
#: only (the bare word read politically).  What was recorded under the old stem (a labelled pair, a hand
#: decision, an M1 gloss) does not carry over; the other renames of that merge kept their descriptions'
#: sense and do.  corpus_regions.json made the same call (the two were filtered again).
SENSE_CHANGED_RENAMES: dict[str, str] = {"bland": "dull", "libertarian": "metaphysical_libertarian"}


def corpus_renames(data_dir: Path, *, carry_only: bool = True) -> dict[str, str]:
    """``{old stem: current stem}`` from the ``renamed_from`` field of the
    trait files (a dict with ``stem``, a bare stem, or a list of either, as in
    ``entity_id.resolve_renamed_stem``).  An old stem that is a current file
    again is left out.  With ``carry_only`` (the default), the renames in
    :data:`SENSE_CHANGED_RENAMES` are left out too, so their old records are
    not read as the new trait's."""
    idir = Path(data_dir) / "traits" / "instructions"
    current = {f.stem for f in idir.glob("*.json")}
    out: dict[str, str] = {}
    for f in sorted(idir.glob("*.json")):
        rf = json.loads(f.read_text()).get("renamed_from")
        for item in (rf if isinstance(rf, list) else [rf] if rf else []):
            old = item.get("stem") if isinstance(item, dict) else item
            if isinstance(old, str) and old and old != f.stem and old not in current:
                out[old] = f.stem
    if carry_only:
        out = {o: n for o, n in out.items() if SENSE_CHANGED_RENAMES.get(o) != n}
    return dict(sorted(out.items()))


#: Decision wording that marks a description not matching its word (polysemy rejects).
_POLYSEMY_RE = re.compile(r"did not match the word|wrong name|meaning the word does not carry|"
                          r"not an everyday word|describes things, not a person", re.I)


@dataclass
class LabelledPair:
    a: str
    b: str
    relation: str
    source: str
    note: str = ""
    uncertain: bool = False
    fold: Optional[int] = None
    classes: dict = field(default_factory=dict)   # contrast-census class per member, if any

    def key(self) -> tuple[str, str]:
        return pair_key(self.a, self.b)


def pair_key(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


@dataclass
class LabelledPairs:
    pairs: list[LabelledPair]
    externals: dict[str, dict]
    excluded: list[dict] = field(default_factory=list)
    folds: dict[str, int] = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    curation_unused: list[dict] = field(default_factory=list)
    renames_followed: dict[str, str] = field(default_factory=dict)

    def by_relation(self, *relations: str, include_uncertain: bool = True) -> list[LabelledPair]:
        return [p for p in self.pairs if p.relation in relations and (include_uncertain or not p.uncertain)]

    def counts(self) -> dict[str, int]:
        c: dict[str, int] = defaultdict(int)
        for p in self.pairs:
            c[p.relation] += 1
        return dict(sorted(c.items()))

    def to_json(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, "built_at": utc_now(), "counts": self.counts(),
                "sources": self.sources, "externals": self.externals,
                "pairs": [asdict(p) for p in self.pairs], "excluded": self.excluded,
                "curation_unused": self.curation_unused, "renames_followed": self.renames_followed,
                "folds": self.folds}

    @classmethod
    def from_json(cls, d: Mapping) -> "LabelledPairs":
        d = d.get("result", d)
        return cls(pairs=[LabelledPair(**p) for p in d["pairs"]], externals=dict(d.get("externals", {})),
                   excluded=list(d.get("excluded", [])), folds={k: int(v) for k, v in d.get("folds", {}).items()},
                   sources=dict(d.get("sources", {})), curation_unused=list(d.get("curation_unused", [])),
                   renames_followed=dict(d.get("renames_followed", {})))


def save(lp: LabelledPairs, path: Path, *, inputs=None) -> None:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.plot_metadata import json_metadata
    env = json_metadata(lp.to_json(), inputs=inputs, title="labelled trait pairs (M2 calibration)")
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", path)


def load(path: Path) -> LabelledPairs:
    return LabelledPairs.from_json(json.loads(Path(path).read_text()))


# --------------------------------------------------------------------------- parsers

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*(?:[ _][A-Za-z][A-Za-z'\-]*)*")


def parse_decision_stems(decision: str, corpus_stems: Iterable[str], *, exclude: Iterable[str] = (),
                         renames: Optional[Mapping[str, str]] = None) -> list[str]:
    """Existing stems a seed-queue ``decision`` names, in order of appearance.

    Tries every run of one to four words (hyphens and spaces folded to ``_``,
    lower case, backticks ignored) against the corpus stems, longest first, so
    ``risk-averse`` and ``heavy_drinker`` are found as one stem.  ``exclude``
    (the entry's own stem and its partner) is dropped.  ``renames`` (old stem
    -> current stem): an old stem the decision names is returned as the
    current one."""
    renames = dict(renames or {})
    stems = set(corpus_stems)
    known = stems | set(renames)
    skip = set(exclude)
    words = [w.lower().replace("-", "_").strip("'") for w in re.findall(r"[A-Za-z][A-Za-z'\-_]*", decision or "")]
    found: list[str] = []
    i = 0
    while i < len(words):
        for n in (4, 3, 2, 1):
            cand = "_".join(words[i:i + n])
            if len(words[i:i + n]) == n and cand in known:
                cand = cand if cand in stems else renames[cand]
                if cand not in skip and cand not in found:
                    found.append(cand)
                i += n
                break
        else:
            i += 1
    return found


def seeding_log_descriptions(path: Path) -> dict[str, str]:
    """``{stem: description}`` from the pairing review's ``- NEW stem: ...`` lines
    (first occurrence wins)."""
    out: dict[str, str] = {}
    if not Path(path).exists():
        return out
    for stem, desc in re.findall(r"^- NEW ([a-z_]+): (.+)$", Path(path).read_text(encoding="utf-8"), re.M):
        out.setdefault(stem, desc.strip())
    return out


def load_v4_antonyms(path: Path, corpus_stems: Iterable[str], *, min_score: int = V4_MIN_SCORE,
                     renames: Optional[Mapping[str, str]] = None) -> list[tuple[str, str, int]]:
    """``(stem, partner_stem, score)`` for v4 judgements with score >= ``min_score``
    whose ``negative_label`` normalises to an existing stem; with ``renames``,
    an old stem on either side is read as the current one."""
    from assistant_axis.entity_id import normalize_to_file_name
    stems = set(corpus_stems)
    renames = dict(renames or {})
    out = []
    data = json.loads(Path(path).read_text()) if Path(path).exists() else {}
    for stem, rec in sorted(data.items()):
        score = rec.get("antonym_score")
        neg = rec.get("negative_label")
        if not isinstance(score, (int, float)) or score < min_score or not neg:
            continue
        partner = normalize_to_file_name(neg)
        stem, partner = renames.get(stem, stem), renames.get(partner, partner)
        if stem in stems and partner in stems and partner != stem:
            out.append((stem, partner, int(score)))
    return out


# --------------------------------------------------------------------------- folds

def _components(pairs: Sequence[LabelledPair], nodes: Iterable[str]) -> list[list[str]]:
    parent: dict[str, str] = {n: n for n in nodes}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for p in pairs:
        ra, rb = find(p.a), find(p.b)
        if ra != rb:
            parent[ra] = rb
    groups: dict[str, list[str]] = defaultdict(list)
    for n in list(parent):
        groups[find(n)].append(n)
    return sorted((sorted(g) for g in groups.values()), key=lambda g: (-len(g), g[0]))


def group_folds(pairs: Sequence[LabelledPair], k: int = 5, *, nodes: Iterable[str] = (), seed: int = 0) -> dict[str, int]:
    """Entity -> fold, over connected components of the labelled (non-unrelated)
    pair graph, greedily balanced by pair count; the members of every pair
    share a fold.  Sets ``fold`` on each pair given."""
    linked = [p for p in pairs if p.relation != "unrelated"]
    comps = _components(linked, list(nodes) + [m for p in linked for m in (p.a, p.b)])
    weight: dict[str, int] = defaultdict(int)
    for p in linked:
        weight[p.a] += 1
    rng = random.Random(seed)
    big = [c for c in comps if len(c) > 1]
    single = [c for c in comps if len(c) == 1]
    rng.shuffle(single)
    load = [0.0] * k
    folds: dict[str, int] = {}
    for comp in big + single:
        f = min(range(k), key=lambda i: (load[i], i))
        for n in comp:
            folds[n] = f
        load[f] += sum(weight[n] for n in comp) + 0.01 * len(comp)
    for p in pairs:
        fa, fb = folds.get(p.a), folds.get(p.b)
        p.fold = fa if fa == fb else None
    return folds


# --------------------------------------------------------------------------- builder

def _corpus(data_dir: Path) -> dict[str, dict]:
    out = {}
    for f in sorted((Path(data_dir) / "traits" / "instructions").glob("*.json")):
        d = json.loads(f.read_text())
        out[f.stem] = {"label": d.get("positive_label") or f.stem, "description": d.get("description") or "",
                       "source": d.get("source")}
    return out


def load_filter_glosses(results_path: Path, *, strata: Iterable[str] = ("not_adopted", "rejects")) -> dict[str, str]:
    """``{stem: gloss}`` from an M1 filter run's ``results.jsonl`` (the
    plain-sense gloss the filter wrote for each label), for the given strata."""
    from assistant_axis.entity_id import normalize_to_file_name
    out: dict[str, str] = {}
    p = Path(results_path)
    if not p.exists():
        return out
    want = set(strata)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        g = r.get("gloss")
        if (r.get("meta") or {}).get("stratum") in want and isinstance(g, str) and g.startswith("This means"):
            out.setdefault(normalize_to_file_name(r["label"]), g)
    return out


def build_labelled_pairs(data_dir: Path, queue: Sequence[Mapping] | Mapping, seeding_log: Path,
                         census: Optional[Mapping[str, str]] = None, *, curation: Optional[Mapping] = None,
                         filter_glosses: Optional[Mapping[str, str]] = None,
                         v4_path: Optional[Path] = None, n_unrelated: int = 2000, k_folds: int = 5,
                         seed: int = 0, renames: Optional[Mapping[str, str]] = None) -> LabelledPairs:
    """Seed the labelled pairs from the corpus, v4, the seed queue and the
    pairing review, apply ``curation`` (see the module docstring), assign
    folds and sample unrelated pairs.  Deterministic for a given ``seed``.
    ``renames`` (old stem -> current stem) defaults to
    :func:`corpus_renames` of ``data_dir``."""
    data_dir = Path(data_dir)
    corpus = _corpus(data_dir)
    stems = set(corpus)
    census = dict(census or {})
    curation = dict(curation or {})
    renames = dict(corpus_renames(data_dir) if renames is None else renames)
    census = {renames.get(s, s): c for s, c in census.items()}
    if isinstance(queue, Mapping):
        queue = queue.get("entries", [])
    rows: dict[tuple[str, str], LabelledPair] = {}
    externals: dict[str, dict] = {}
    excluded: list[dict] = []
    unused: list[dict] = []
    sources: dict[str, int] = defaultdict(int)

    def resolve(m: str) -> str:
        """A curation or source member as the corpus names it now."""
        return m if (m in stems or ":" in m) else renames.get(m, m)

    def add(a: str, b: str, relation: str, source: str, note: str = "", uncertain: bool = False) -> None:
        if a == b:
            return
        key = pair_key(a, b)
        if key in rows:
            if rows[key].relation != relation:
                excluded.append({"a": a, "b": b, "relation": relation, "source": source,
                                 "reason": f"already labelled {rows[key].relation} by {rows[key].source}"})
            return
        rows[key] = LabelledPair(a=key[0], b=key[1], relation=relation, source=source, note=note, uncertain=uncertain)
        sources[source] += 1

    # 1. recorded clean pairs, and the other arrangements' members
    recs = load_corpus_arrangements(data_dir, "traits")
    for stem, rec in sorted(recs.items()):
        for arr in rec.arrangements:
            if arr.kind == "pair" and len(arr.members) == 2 and all(m in stems for m in arr.members):
                add(arr.members[0], arr.members[1], "antonym", "arrangement_pair")
    for a, b in reciprocal_pairs(recs):
        add(a, b, "antonym", "reciprocal_negative_label")
    for stem, rec in sorted(recs.items()):
        for arr in rec.arrangements:
            if arr.kind in ("pair", "singleton") or stem != min(arr.members, default=stem):
                continue
            members = [m for m in arr.members if m in stems]
            if is_ordered(arr.kind):   # a sequence: neighbours along it only
                links = list(zip(members, members[1:]))
            else:
                links = [(x, y) for i, x in enumerate(members) for y in members[i + 1:]]
            for x, y in links:
                add(x, y, "near_distinct", f"arrangement_{arr.kind}",
                    note=f"members of one {arr.kind}: {', '.join(arr.members)}")
    # 2. v4 antonym judgements
    for a, b, score in load_v4_antonyms(v4_path or data_dir / "traits" / "trait_antonyms_v4.json", stems,
                                        renames=renames):
        add(a, b, "antonym", "antonyms_v4", note=f"antonym_score {score}")
    # 3. deliberate duplicates declared in the corpus's own `source` field
    for stem, c in sorted(corpus.items()):
        src = c.get("source") or ""
        if "deliberate dup" in src.lower():
            for other in parse_decision_stems(src, stems, exclude=[stem], renames=renames):
                add(stem, other, "deliberate_duplicate", "corpus_source_field", note=src)
    # 4. seed-queue decisions (with the entry's description, or the pairing review's)
    log_desc = seeding_log_descriptions(seeding_log)
    for e in queue:
        if e.get("status") not in ("not_adopted", "superseded") or e.get("entity_type", "trait") != "trait":
            continue
        stem = e.get("stem")
        if not stem or stem in stems:
            continue
        desc = e.get("description") or e.get("description_draft") or log_desc.get(stem)
        decision = e.get("decision") or ""
        named = parse_decision_stems(decision, stems, exclude=[stem, resolve(e.get("partner") or "")],
                                     renames=renames)
        qid = f"queue:{stem}"
        if not desc and stem in (filter_glosses or {}):
            # no description was ever written: use the M1 filter's plain-sense gloss of the label
            desc, qid = filter_glosses[stem], f"gloss:{stem}"
        if not desc:
            if named:
                excluded.append({"a": qid, "b": ",".join(named), "relation": "duplicate",
                                 "source": "seed_queue_decision", "reason": "no description or gloss to embed"})
            continue
        if _POLYSEMY_RE.search(decision):
            lid = f"label:{stem}"
            externals[qid] = {"label": e.get("label") or stem, "description": desc, "status": e.get("status"),
                              "text_source": "m1_filter_gloss" if qid.startswith("gloss:") else "seed_queue",
                              "decision": decision.strip()}
            externals[lid] = {"label": e.get("label") or stem, "description": None, "status": e.get("status")}
            add(qid, lid, "polysemy_reject", "seed_queue_decision", note=decision.strip()[:300])
            continue
        if named:
            externals[qid] = {"label": e.get("label") or stem, "description": desc, "status": e.get("status"),
                              "text_source": "m1_filter_gloss" if qid.startswith("gloss:") else "seed_queue",
                              "decision": decision.strip()}
            for other in named:
                add(qid, other, "duplicate", "seed_queue_decision", note=decision.strip()[:300])
    # 5. hand curation (labelled_pairs_curation.json)
    queue_by_stem = {e.get("stem"): e for e in queue if e.get("stem")}

    def ensure_external(m: str) -> None:
        """Create ``queue:X`` / ``gloss:X`` / ``label:X`` members named by the curation."""
        if m in stems or m in externals or ":" not in m:
            return
        kind, stem = m.split(":", 1)
        e = queue_by_stem.get(stem, {})
        label = e.get("label") or stem.replace("_", " ")
        if kind == "queue":
            desc = e.get("description") or e.get("description_draft") or log_desc.get(stem)
            if desc:
                externals[m] = {"label": label, "description": desc, "status": e.get("status"),
                                "text_source": "seed_queue" if e.get("description") else "seeding_log"}
        elif kind == "gloss" and stem in (filter_glosses or {}):
            externals[m] = {"label": label, "description": filter_glosses[stem], "status": e.get("status"),
                            "text_source": "m1_filter_gloss"}
        elif kind == "label":
            externals[m] = {"label": label, "description": None, "status": e.get("status")}

    def unusable(*members: str) -> list[str]:
        return [m for m in members if m not in stems and m not in externals]

    for item in curation.get("add", []):
        a, b = resolve(item["a"]), resolve(item["b"])
        ensure_external(a)
        ensure_external(b)
        if unusable(a, b):
            unused.append({"part": "add", "a": item["a"], "b": item["b"], "relation": item.get("relation"),
                           "why": f"{', '.join(unusable(a, b))}: neither a corpus stem nor an external"})
            continue
        add(a, b, item["relation"], item.get("source", "hand"), item.get("note", ""),
            bool(item.get("uncertain", False)))
    for item in curation.get("relabel", []):
        key = pair_key(resolve(item["a"]), resolve(item["b"]))
        if key in rows:
            p = rows[key]
            p.relation = item.get("relation", p.relation)
            p.uncertain = bool(item.get("uncertain", p.uncertain))
            if item.get("note"):
                p.note = (p.note + " | " if p.note else "") + "hand: " + item["note"]
        else:
            unused.append({"part": "relabel", "a": item["a"], "b": item["b"], "why": "no source names this pair"})
    for item in curation.get("exclude", []):
        key = pair_key(resolve(item["a"]), resolve(item["b"]))
        if key in rows:
            p = rows.pop(key)
            excluded.append({"a": p.a, "b": p.b, "relation": p.relation, "source": p.source,
                             "reason": "hand: " + item.get("reason", "excluded")})
        else:
            unused.append({"part": "exclude", "a": item["a"], "b": item["b"], "why": "no source names this pair"})
    # keep_only: {member: {"keep": {other: {relation?, uncertain?, note?}}, "reason": why the rest go}};
    # it judges only the mechanically named rows (seed-queue decisions, corpus source fields), never a
    # recorded arrangement, a v4 judgement or a hand-added pair.
    for member_as_written, spec in (curation.get("keep_only") or {}).items():
        member = resolve(member_as_written)
        keep = {resolve(o): v for o, v in (spec.get("keep") or {}).items()}
        judged = set(spec.get("sources") or MECHANICAL_SOURCES)
        judged_keys = [k for k in rows if member in k and rows[k].source in judged]
        if keep and not judged_keys:
            unused.append({"part": "keep_only", "a": member_as_written, "b": None,
                           "why": "no mechanically named row for this member"})
        found = set()
        for key in judged_keys:
            other = key[1] if key[0] == member else key[0]
            p = rows[key]
            if other in keep:
                found.add(other)
                k = keep[other] or {}
                p.relation = k.get("relation", p.relation)
                p.uncertain = bool(k.get("uncertain", p.uncertain))
                if k.get("note"):
                    p.note = "hand: " + k["note"] + (" | " + p.note if p.note else "")
            else:
                rows.pop(key)
                excluded.append({"a": p.a, "b": p.b, "relation": p.relation, "source": p.source,
                                 "reason": "hand: " + spec.get("reason", "not the named duplicate")})
        if judged_keys:
            for other in sorted(set(keep) - found):
                unused.append({"part": "keep_only", "a": member_as_written, "b": other,
                               "why": "the kept pair is not among the member's mechanically named rows"})
    # drop externals no longer referenced
    used = {m for p in rows.values() for m in (p.a, p.b)}
    externals = {k: v for k, v in sorted(externals.items()) if k in used}
    for p in rows.values():
        for m in (p.a, p.b):
            missing = m not in stems and m not in externals
            if missing:
                raise ValueError(f"labelled pair member {m!r} is neither a corpus stem nor an external")
            if m in census:
                p.classes[m] = census[m]

    labelled = sorted(rows.values(), key=lambda p: (RELATIONS.index(p.relation), p.a, p.b))
    folds = group_folds(labelled, k_folds, nodes=sorted(stems), seed=seed)
    # 6. unrelated pairs, sampled inside each fold, never touching a labelled pair or arrangement
    taken = set(rows)
    arranged = {pair_key(x, y) for r in recs.values() for arr in r.arrangements
                for i, x in enumerate(arr.members) for y in arr.members[i + 1:]}
    by_fold: dict[int, list[str]] = defaultdict(list)
    for s in sorted(stems):
        by_fold[folds[s]].append(s)
    rng = random.Random(seed)
    unrelated: list[LabelledPair] = []
    per_fold = n_unrelated // max(k_folds, 1)
    for f in sorted(by_fold):
        pool = by_fold[f]
        got, tries = 0, 0
        while got < per_fold and tries < per_fold * 50 and len(pool) > 1:
            tries += 1
            x, y = rng.sample(pool, 2)
            key = pair_key(x, y)
            if key in taken or key in arranged:
                continue
            taken.add(key)
            unrelated.append(LabelledPair(a=key[0], b=key[1], relation="unrelated", source="random", fold=f))
            got += 1
    kept: dict[str, int] = defaultdict(int)
    for p in labelled + unrelated:
        kept[p.source] += 1
    return LabelledPairs(pairs=labelled + unrelated, externals=externals, excluded=excluded, folds=folds,
                         sources={"seeded": dict(sorted(sources.items())), "kept": dict(sorted(kept.items()))},
                         curation_unused=unused, renames_followed=dict(sorted(renames.items())))


def member_text(member: str, corpus: Mapping[str, Mapping], externals: Mapping[str, Mapping]) -> tuple[str, Optional[str]]:
    """``(label, description or None)`` for a corpus stem or an external member."""
    if member in corpus:
        c = corpus[member]
        return c["label"], c["description"]
    e = externals[member]
    return e["label"], e.get("description")


# --------------------------------------------------------------------------- repository defaults

DEFAULT_FILTER_RESULTS = Path("data/candidates/filter/m1_validation_r2/results.jsonl")
DEFAULT_SEEDING_LOG = Path("reports/seeding_log_2026-09.md")
DEFAULT_CENSUS = Path("reports/trait_gap_generation/contrast_clauses_census.md")
CURATION_NAME = "labelled_pairs_curation.json"
LABELLED_PAIRS_NAME = "labelled_pairs.json"


def build_default(repo_root: Path, *, out_dir: Optional[Path] = None, write: bool = True,
                  n_unrelated: int = 2000, seed: int = 0) -> LabelledPairs:
    """Build from the repository's own files (corpus, v4, seed queue, pairing
    review, the M1 filter's glosses, the contrast census, the curation file)
    and, with ``write``, save ``labelled_pairs.json`` with its inputs."""
    from assistant_axis.provenance import current_file_input, current_files_input

    from .contrast import parse_census
    repo_root = Path(repo_root)
    out_dir = Path(out_dir or repo_root / "data" / "candidates" / "calibration")
    data_dir = repo_root / "data"
    queue_path = data_dir / "seed_queue.json"
    curation_path = out_dir / CURATION_NAME
    curation = json.loads(curation_path.read_text()) if curation_path.exists() else {}
    census_path = repo_root / DEFAULT_CENSUS
    census = parse_census(census_path) if census_path.exists() else {}
    fg = load_filter_glosses(repo_root / DEFAULT_FILTER_RESULTS)
    lp = build_labelled_pairs(data_dir, json.loads(queue_path.read_text()), repo_root / DEFAULT_SEEDING_LOG,
                              census, curation=curation, filter_glosses=fg, n_unrelated=n_unrelated, seed=seed)
    if write:
        trait_files = sorted((data_dir / "traits" / "instructions").glob("*.json"))
        inputs = [current_files_input(dep_key="trait_files", paths=trait_files),
                  current_file_input(dep_key="seed_queue", path=queue_path),
                  current_file_input(dep_key="antonyms_v4", path=data_dir / "traits" / "trait_antonyms_v4.json"),
                  current_file_input(dep_key="seeding_log", path=repo_root / DEFAULT_SEEDING_LOG),
                  current_file_input(dep_key="filter_glosses", path=repo_root / DEFAULT_FILTER_RESULTS),
                  current_file_input(dep_key="census", path=census_path)]
        if curation_path.exists():
            inputs.append(current_file_input(dep_key="curation", path=curation_path))
        save(lp, out_dir / LABELLED_PAIRS_NAME, inputs=inputs)
    return lp
