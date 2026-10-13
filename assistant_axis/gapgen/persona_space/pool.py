"""The entity pool of plan 12: the extracted persona vectors, keyed by entity id, with the rows the regression may
train on (coding_plan_12_persona_space.md § 1, § 5).

The geometry is :func:`assistant_axis.gapgen.persona.load_persona_space`'s, byte for byte: the 8-slot tree at the
canonical cell (slot 6, layer 25), centred on the corpus mean over traits and roles together, soft-sheared at L=3.
Every one of its 582 vectors (``default`` excluded) stays in the pool for the centring, the shear and the principal
basis.  A vector counts for a **current** corpus file when its stem is that file's, or is recorded in that file's
``renamed_from``; the rows that train the regression and make up the neighbour lists are those, less

* **orphans**: a vector whose entity has no current file and no file naming it in ``renamed_from`` (May 2026: the
  traits conceptual, cruel, dramatic, enigmatic, mercurial, regulatory, technical and the role adolescent);
* **sense-changed renames** (:data:`assistant_axis.gapgen.labels.SENSE_CHANGED_RENAMES`: bland -> dull,
  libertarian -> metaphysical_libertarian, savage -> violent): the May vector describes the old sense, so the row
  keeps the old stem's id and is never trained on; the current file counts as pending
  (:func:`assistant_axis.gapgen.persona_space.prospective.pending`);
* **superseded** renames: a ``renamed_from`` vector whose current file also has a vector of its own (none in May).

Ids are ``name|T`` / ``name|R`` (:func:`assistant_axis.entity_id.entity_id`), so a trait and a role of the same name
are two rows.  The text embedded for an entity is ``label: description`` cut to 20 words (``w20``): a trait's
``positive_label``, a role's mechanical display form (``devils advocate``), the form every corpus text is cached
under in the platform's embedding cache.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import display_form_name, entity_id

from ..labels import SENSE_CHANGED_RENAMES
from ..paths import DATA_DIR
from ..persona import DEFAULT_LAYER, DEFAULT_SHEAR_L, DEFAULT_SLOT, DEFAULT_VECTORS_DIR, load_persona_space
from ..space import pca_basis, residual_fraction

KINDS = ("traits", "roles")
#: The representation every corpus and candidate text is embedded in (metric_config.json's covered setting).
REPRESENTATION = "w20"


@dataclass
class Pool:
    """The 582-row pool (one row per extracted vector) and which rows train.

    ``ids``: the entity id of each row (the current file's when the vector counts for one, else the vector stem's);
    ``vector_stems``: the file stem of each vector; ``kinds``: ``traits`` / ``roles``; ``cur_stems``: the current
    file the vector belongs to (``None`` for an orphan; the new stem for a sense-changed rename); ``has_file``: the
    vector's stem is a current file or a ``renamed_from`` of one (sense-changed renames included); ``M``: the
    centred, sheared rows ``(582, 5120)`` float64; ``space``: :func:`load_persona_space`'s record without ``M``;
    ``train_idx``: the rows that train and form neighbour lists."""
    ids: list
    vector_stems: list
    kinds: list
    cur_stems: list
    has_file: np.ndarray
    M: np.ndarray
    space: dict
    train_idx: np.ndarray
    orphan_ids: list = field(default_factory=list)
    sense_changed_ids: list = field(default_factory=list)
    superseded_ids: list = field(default_factory=list)
    renamed: dict = field(default_factory=dict)          # vector id -> current id (renamed_from matches)

    def __post_init__(self):
        self._row = {i: n for n, i in enumerate(self.ids)}

    @property
    def n(self) -> int:
        return len(self.ids)

    @property
    def train_ids(self) -> list[str]:
        return [self.ids[i] for i in self.train_idx]

    @property
    def train_kinds(self) -> list[str]:
        return [self.kinds[i] for i in self.train_idx]

    def row(self, eid: str) -> Optional[int]:
        return self._row.get(eid)

    def counts(self) -> dict:
        """The figures § 8's pool test checks."""
        k = np.array(self.kinds)
        tr = np.zeros(self.n, dtype=bool)
        tr[self.train_idx] = True
        renamed_t = sum(1 for v in self.renamed if v.endswith("|T"))
        return {"n": self.n, "n_traits": int((k == "traits").sum()), "n_roles": int((k == "roles").sum()),
                "n_with_file": int(self.has_file.sum()),
                "n_with_file_traits": int((self.has_file & (k == "traits")).sum()),
                "n_with_file_roles": int((self.has_file & (k == "roles")).sum()),
                "n_train": int(tr.sum()), "n_train_traits": int((tr & (k == "traits")).sum()),
                "n_train_roles": int((tr & (k == "roles")).sum()),
                "n_renamed_traits": renamed_t, "n_renamed_roles": len(self.renamed) - renamed_t,
                "orphans": list(self.orphan_ids), "sense_changed": list(self.sense_changed_ids),
                "superseded": list(self.superseded_ids)}


def _renamed_from(value: Any) -> list[str]:
    out = []
    for item in value if isinstance(value, list) else ([value] if value else []):
        old = item.get("stem") if isinstance(item, Mapping) else item
        if isinstance(old, str) and old:
            out.append(old)
    return out


def corpus_docs(data_dir: Path, kind: str) -> dict[str, dict]:
    """``{stem: file contents}`` for every ``<data_dir>/<kind>/instructions/*.json`` (``default`` included; the
    callers leave it out where it matters)."""
    d = Path(data_dir) / kind / "instructions"
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))}


def corpus_renames(docs: Mapping[str, Mapping]) -> dict[str, str]:
    """``{old stem: current stem}`` from the files' ``renamed_from`` (an old stem that is a current file again is
    left out)."""
    out: dict[str, str] = {}
    for stem, doc in docs.items():
        for old in _renamed_from(doc.get("renamed_from")):
            if old != stem and old not in docs:
                out[old] = stem
    return out


def entity_label(kind: str, stem: str, doc: Optional[Mapping] = None) -> str:
    """The label an entity is embedded with: a trait's stored ``positive_label`` (as M3 embeds the corpus), a role's
    mechanical display form (the form the embedding cache holds every role under)."""
    if kind == "traits":
        return (doc or {}).get("positive_label") or display_form_name(stem)
    return display_form_name(stem)


def entity_text(kind: str, stem: str, doc: Mapping, representation: str = REPRESENTATION) -> str:
    """``label: description`` in ``representation`` (``w20``): the text an existing entity is embedded as."""
    from ..representation import represent
    return represent(entity_label(kind, stem, doc), doc.get("description") or "", representation)


def pool_from_space(space: Mapping, data_dir: Path = DATA_DIR) -> Pool:
    """A :class:`Pool` from :func:`load_persona_space`'s record (``stems``, ``kinds``, ``M``) and the corpus files
    under ``data_dir``."""
    data_dir = Path(data_dir)
    docs = {k: corpus_docs(data_dir, k) for k in KINDS}
    ren = {k: corpus_renames(docs[k]) for k in KINDS}
    stems, kinds = list(space["stems"]), list(space["kinds"])
    own = {(k, s) for s, k in zip(stems, kinds) if s in docs[k]}
    ids, cur, has_file, train = [], [], [], []
    orphans, sense, superseded, renamed = [], [], [], {}
    for i, (s, k) in enumerate(zip(stems, kinds)):
        if s in docs[k]:
            c, sense_changed = s, False
        elif s in ren[k]:
            c = ren[k][s]
            sense_changed = k == "traits" and SENSE_CHANGED_RENAMES.get(s) == c
        else:
            c, sense_changed = None, False
        if c is None:
            eid = entity_id(s, k)
            orphans.append(eid)
        elif sense_changed:
            eid = entity_id(s, k)                    # the old sense: never the current file's id
            sense.append(eid)
        elif c != s and (k, c) in own:
            eid = entity_id(s, k)                    # the current file has a vector of its own
            superseded.append(eid)
        else:
            eid = entity_id(c, k)
            train.append(i)
        if c is not None and c != s:
            renamed[entity_id(s, k)] = entity_id(c, k)
        has_file.append(c is not None)
        ids.append(eid)
        cur.append(c)
    if len(set(ids)) != len(ids):
        dup = sorted({x for x in ids if ids.count(x) > 1})
        raise ValueError(f"two vectors map to one entity id: {dup[:10]}")
    rec = {k: v for k, v in space.items() if k != "M"}
    return Pool(ids=ids, vector_stems=stems, kinds=kinds, cur_stems=cur, has_file=np.array(has_file, dtype=bool),
                M=np.asarray(space["M"], dtype=np.float64), space=rec, train_idx=np.array(train, dtype=int),
                orphan_ids=orphans, sense_changed_ids=sense, superseded_ids=superseded, renamed=renamed)


def load_pool(data_dir: Path = DATA_DIR, vectors_dir: Path = DEFAULT_VECTORS_DIR, *, slot: int = DEFAULT_SLOT,
              layer: int = DEFAULT_LAYER, shear_L: Optional[int] = DEFAULT_SHEAR_L,
              cache_dir: Optional[Path] = None) -> Pool:
    """The pool: :func:`load_persona_space` (unchanged; its slice cache in ``cache_dir``, default
    ``data/candidates/cache``) mapped onto the corpus files of ``data_dir``."""
    return pool_from_space(load_persona_space(Path(vectors_dir), slot=slot, layer=layer, shear_L=shear_L,
                                              cache_dir=cache_dir), data_dir)


def corpus_texts(pool: Pool, data_dir: Path = DATA_DIR) -> list[Optional[str]]:
    """The embedded text of every pool row that trains (``label: description``, ``w20``); ``None`` elsewhere."""
    docs = {k: corpus_docs(Path(data_dir), k) for k in KINDS}
    out: list[Optional[str]] = [None] * pool.n
    for i in pool.train_idx:
        k, c = pool.kinds[i], pool.cur_stems[i]
        out[i] = entity_text(k, c, docs[k][c])
    return out


def _union_find(groups: Sequence[Sequence[str]]) -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for g in groups:
        g = list(g)
        for m in g[1:]:
            a, b = find(g[0]), find(m)
            if a != b:
                parent[max(a, b)] = min(a, b)
    return {x: find(x) for x in parent}


def fold_groups(pool: Pool, data_dir: Path = DATA_DIR) -> np.ndarray:
    """One group label per pool row, for arrangement-grouped folds (``GroupKFold``): a trait's group is its
    :func:`assistant_axis.gapgen.recovery.hiding_groups` component (a recorded pair, triangle, tetrahedron or
    simplex, with the label-reciprocal partner); a role's is the connected component of every arrangement the role
    files record, except ``singleton`` (pairs, the sequence, the map, the square, the set); a row alone is its own
    group, and a row that does not train gets a group of its own."""
    from assistant_axis.arrangements import load_corpus_arrangements

    from .. import novelty as NV
    from ..recovery import hiding_groups
    data_dir = Path(data_dir)
    tgroup = {}
    for gi, members in enumerate(hiding_groups(NV.load_trait_corpus(data_dir))):
        for m in members:
            tgroup[m] = f"T:{members[0]}"
    recs = load_corpus_arrangements(data_dir, "roles")
    comp = _union_find([a.members for r in recs.values() for a in r.arrangements
                        if a.kind != "singleton" and len(a.members) >= 2])
    out = np.empty(pool.n, dtype=object)
    train = set(int(i) for i in pool.train_idx)
    for i in range(pool.n):
        k, c = pool.kinds[i], pool.cur_stems[i]
        if i not in train:
            out[i] = f"solo:{pool.ids[i]}"
        elif k == "traits":
            out[i] = tgroup.get(c, f"T:{c}")
        else:
            out[i] = f"R:{comp.get(c, c)}"
    return out.astype(str)


def pair_partners(pool: Pool, data_dir: Path = DATA_DIR) -> dict[str, str]:
    """``{id: partner id}`` for the recorded clean pairs whose two poles both train: trait pairs by the label
    convention (``novelty.CorpusTrait.pair_partner``), role pairs from the role files' ``pair`` arrangements."""
    from assistant_axis.arrangements import load_corpus_arrangements

    from .. import novelty as NV
    train = set(pool.train_ids)
    out: dict[str, str] = {}
    for s, t in NV.load_trait_corpus(Path(data_dir)).items():
        if t.pair_partner:
            a, b = entity_id(s, "traits"), entity_id(t.pair_partner, "traits")
            if a in train and b in train:
                out[a] = b
    for s, rec in load_corpus_arrangements(Path(data_dir), "roles").items():
        for a in rec.arrangements:
            if a.kind == "pair" and len(a.members) == 2:
                x, y = (entity_id(m, "roles") for m in a.members)
                if x in train and y in train:
                    out[x], out[y] = y, x
    return out


def pc_basis(M: np.ndarray, N: int) -> np.ndarray:
    """The top-``N`` principal directions (orthonormal rows) of the already-centred rows ``M`` (no re-centring:
    the corpus mean is fixed, as everywhere in the platform)."""
    return pca_basis(np.asarray(M, dtype=np.float64), int(N))


def residual_N(V: np.ndarray, basis: np.ndarray) -> np.ndarray:
    """The energy outside the span of ``basis``: ``1 - |B v|^2 / |v|^2`` per row, in [0, 1]."""
    return np.atleast_1d(residual_fraction(np.atleast_2d(V), basis))


def spectrum(M: np.ndarray, *, n_slope: int = 64) -> dict:
    """The pool's eigenvalue spectrum: K for 50 / 80 / 90 / 95 / 99% of the variance, the top-12 share, the
    log-log slope over components 1-``n_slope``, and the ratios the plan quotes."""
    from ..space import k_for_variance_from_eigs
    S = np.linalg.svd(np.asarray(M, dtype=np.float64), compute_uv=False)
    lam = S ** 2
    lam = lam[lam > lam[0] * 1e-12]
    share = lam / lam.sum()
    n_slope = min(n_slope, len(lam))
    k = np.arange(1, n_slope + 1)
    slope = float(np.polyfit(np.log(k), np.log(lam[:n_slope]), 1)[0]) if n_slope >= 2 else None

    def ratio(j: int):
        return round(float(lam[0] / lam[j]), 2) if len(lam) > j else None
    return {"k50": k_for_variance_from_eigs(lam, 0.5), "k80": k_for_variance_from_eigs(lam, 0.8),
            "k90": k_for_variance_from_eigs(lam, 0.9), "k95": k_for_variance_from_eigs(lam, 0.95),
            "k99": k_for_variance_from_eigs(lam, 0.99), "top12_share": round(float(share[:12].sum()), 4),
            "top12_each": [round(float(x), 4) for x in share[:12]],
            "loglog_slope_1_64": None if slope is None else round(slope, 3),
            "lambda1_over_12": ratio(11), "lambda1_over_32": ratio(31)}
