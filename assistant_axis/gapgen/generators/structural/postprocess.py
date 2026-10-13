"""Local post-processing, no API (plan sections 5-7, ``postprocess.py``; tasks 6 and 10): the operator table.

``operator_table.jsonl`` (:data:`.OPERATOR_TABLE_PATH`, tracked) has one row per distinct stem reached by generator B
(the operator answers of the named runs) or generator A (the modernised classical rows), deterministic from the runs'
``responses.jsonl`` and ``classical_modern.jsonl``:

* **Stems** (:func:`stem_of`): ``normalize_candidate`` and then ``base_model.parse.normalize_form`` (a ``-ness`` /
  ``-ity`` noun to its adjective, a British spelling to the US one, each only when OEWN has the result), so that
  ``stubbornness`` and ``stubborn`` are one row and ``harsh toward self`` is ``harsh_toward_self``.  The row's
  ``label`` is the folded form (what ``normalize_candidate`` turns back into the same stem); ``surface`` the first
  form emitted.
* **Tags** (:func:`tag_membership`): ``exists`` (a corpus stem or a ``renamed_from``), ``is_negative_label`` (a
  corpus file's real-word ``negative_label``), ``queued`` and ``queue_status`` (any seed-queue entry by stem or
  normalised label), ``registered`` (a stem of the registry log), ``registered_by`` (its sources' generators) and
  ``registered_decided`` (2026-10-13: M1 and M3 have nothing left to do for it: an M1 verdict other than ``trait``,
  or a ``trait`` verdict and an M3 block; the rule of plan 04's ``registry_stems``).  A row is **net-new**
  (``net_new``) when it is none of ``exists``, ``queued`` and ``registered_decided``.  **No tag drops a row**: the
  filtered-status tags change only what the wave's cut counts (the mutation test).
* **Merge** (:func:`merge_items`): every source is kept (operator: the source trait, the operator and its target or
  mode; classical: the row id and its role), ``n_sources`` counts the distinct traits and classical rows that reach
  the stem, ``roles`` the operators and classical roles, ``siblings`` the stems of its structure (for an
  opposite, excess or deficiency answer, the source trait and the reply's other answers among those three; for a
  retarget or remode answer, the source trait; for a classical row, the first labels of its sibling rows).
* **Rank** (:func:`rank`; plan section 7): more sources first (a label several traits reach is the better
  candidate), then by tier: opposites of ``non-X`` and singleton traits (pair completions, worth more than two
  unpaired points), then excess, deficiency, the other opposites and the classical rows, then retarget and remode;
  ties broken by the stem's sha256 (deterministic, with no alphabetical bias).  ``kinds`` names each row's
  categories for the readouts: ``pair_completion``, ``degree_filler`` (excess, deficiency), ``opposite``,
  ``retarget``, ``principal_retarget``, ``remode``, ``classical``.

**Several runs** (``postprocess --run-id R1 R2``): when two named runs answered the same trait in full, the run
named last wins (its samples, not a mix of runs); a principal-only answer (a later principal-target stage) adds its
items beside the trait's full reply.  A run marked void (``void.json``) is skipped.

**Samples** (Roger, 2026-10-13): a trait's answers are the union of its samples (:mod:`.combine`), so one slot can
give several rows; each operator source carries its ``support`` (how many samples named the label, 1-3), the samples
and every sample's gloss, and each row its ``max_support``.  Support is a readout figure: it ranks, gates and
filters nothing.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import utc_stamp

from . import OPERATOR_TABLE_PATH, RESPONSES_NAME, SCHEMA_VERSION
from .operators import PRINCIPAL_TARGETS, SINGLE_OPERATORS, OperatorReply, read_responses, reply_from_record

#: Tier of each source kind in the rank (lower first).
KIND_TIER: dict[str, int] = {"pair_completion": 0, "degree_filler": 1, "opposite": 1, "classical": 1,
                             "retarget": 2, "principal_retarget": 2, "remode": 2}
#: Classical roles whose partner is the sibling row with this role (the row's ``partner_hint``).
CLASSICAL_PARTNER_ROLE: dict[str, str] = {"deficiency": "excess", "excess": "deficiency", "sin": "virtue",
                                          "virtue": "sin", "underuse": "overuse", "overuse": "underuse",
                                          "need_high": "need_low", "need_low": "need_high"}


# --------------------------------------------------------------------------- corpus, queue, registry

@dataclass
class Corpus:
    """What the tags and the readouts read from the trait files (``data/traits/instructions``)."""
    stems: frozenset = frozenset()
    labels: dict = field(default_factory=dict)              # stem -> positive_label
    descriptions: dict = field(default_factory=dict)
    negative_labels: dict = field(default_factory=dict)     # stem -> negative_label (as stored)
    kinds: dict = field(default_factory=dict)               # stem -> arrangement kind(s)
    renamed: dict = field(default_factory=dict)             # old stem -> current stem

    def is_placeholder(self, stem: str) -> bool:
        """The trait's ``negative_label`` is a ``non-X`` placeholder."""
        nl = self.negative_labels.get(stem)
        return isinstance(nl, str) and nl.strip().lower().startswith("non-")

    def is_unpaired(self, stem: str) -> bool:
        """A ``non-X`` or ``singleton`` trait: its opposite is a pair completion."""
        return self.is_placeholder(stem) or self.kinds.get(stem) == "singleton"

    @property
    def negative_label_stems(self) -> set[str]:
        return {normalize_to_file_name(nl) for s, nl in self.negative_labels.items()
                if isinstance(nl, str) and nl.strip() and not self.is_placeholder(s)}


def load_corpus(data_dir: Path) -> Corpus:
    from ..censuses.corpus import corpus_renamed_from
    from .operators import arrangement_kinds
    tdir = Path(data_dir) / "traits" / "instructions"
    labels, descs, negs, kinds = {}, {}, {}, {}
    for p in sorted(tdir.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        labels[p.stem] = str(doc.get("positive_label") or p.stem.replace("_", " "))
        descs[p.stem] = str(doc.get("description") or "")
        negs[p.stem] = doc.get("negative_label")
        kinds[p.stem] = arrangement_kinds(doc.get("arrangement"))
    return Corpus(stems=frozenset(labels), labels=labels, descriptions=descs, negative_labels=negs, kinds=kinds,
                  renamed=corpus_renamed_from(data_dir))


def load_queue_index(queue_path: Path) -> dict[str, str]:
    """``{stem: status}`` over every seed-queue entry, by its stem and by its normalised label (trait entries
    before role entries, the first entry in file order winning)."""
    p = Path(queue_path)
    if not p.exists():
        return {}
    q = json.loads(p.read_text(encoding="utf-8"))
    entries = (q.get("entries") if isinstance(q, dict) else q) or []
    out: dict[str, str] = {}
    for e in sorted(entries, key=lambda e: 0 if e.get("entity_type") in (None, "trait") else 1):
        for k in ("stem", "label"):
            if e.get(k):
                out.setdefault(normalize_to_file_name(e[k]), str(e.get("status")))
    return out


def is_decided(row: Mapping) -> bool:
    """M1 and M3 have nothing left to do for a registry row: an M1 verdict other than ``trait``, or a ``trait``
    verdict and an M3 block (plan 04's ``registry_stems``; 2026-10-13)."""
    f = row.get("filter") or {}
    if not f:
        return False
    return f.get("verdict") != "trait" or bool(row.get("novelty"))


def registry_index(rows: Mapping[str, Mapping]) -> dict[str, dict]:
    """``{stem: {"generators": [...], "decided": bool, "key": ...}}`` from a folded registry (the lowest sense id
    per stem)."""
    out: dict[str, dict] = {}
    for key, r in sorted(rows.items(), key=lambda kv: (kv[1].get("stem") or "", int(kv[1].get("sense_id") or 1))):
        st = r.get("stem")
        if not st or st in out:
            continue
        gens = sorted({s.get("generator") for s in r.get("sources") or [] if s.get("generator")})
        out[st] = {"generators": gens, "decided": is_decided(r), "key": key}
    return out


# --------------------------------------------------------------------------- stems and tags

def oewn_lexicon():  # pragma: no cover - needs the OEWN database
    """The OEWN adjective and noun lemmas (``base_model.parse.Lexicon``) for :func:`stem_of`."""
    from assistant_axis.gapgen.wordnet import ADJ_POS, ensure_oewn, oewn

    from ..base_model.parse import Lexicon
    if not ensure_oewn(download=False):
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    w = oewn()
    return Lexicon(adjectives=frozenset(x.lemma().lower() for pos in ADJ_POS for x in w.words(pos=pos)),
                   nouns=frozenset(x.lemma().lower() for x in w.words(pos="n")))


def stem_of(label: str, *, lexicon=None) -> tuple[str, str]:
    """``(stem, label)``: the label cleaned (``normalize_candidate``), folded by ``normalize_form`` when a lexicon is
    given (nominal to adjective and British to US spelling, only where OEWN has the result), and its stem.  The label
    keeps its case when nothing was folded.  ``ValueError`` when it does not normalise."""
    n = normalize_candidate(label)
    folded = n.label
    if lexicon is not None:
        from ..base_model.parse import normalize_form
        out, _form, _from = normalize_form(n.label, lexicon=lexicon)
        if out != n.label.lower():
            folded = out
    return normalize_candidate(folded).stem, folded


@dataclass(frozen=True)
class Tags:
    exists: bool
    queued: bool
    queue_status: Optional[str]
    is_negative_label: bool
    registered: bool
    registered_by: tuple = ()
    registered_decided: bool = False

    @property
    def net_new(self) -> bool:
        """Not yet filtered by the registry: not a corpus trait, not queued, not decided by M1 and M3."""
        return not (self.exists or self.queued or self.registered_decided)

    @property
    def status(self) -> str:
        """One word for the strata: ``exists``, ``queued``, ``registered-decided``, ``registered-pending`` or
        ``new``."""
        if self.exists:
            return "exists"
        if self.queued:
            return "queued"
        if self.registered:
            return "registered-decided" if self.registered_decided else "registered-pending"
        return "new"


def tag_membership(stem: str, *, corpus_stems: Iterable[str], renamed: Mapping[str, str],
                   negative_label_stems: Iterable[str], queue: Mapping[str, str],
                   registry: Optional[Mapping[str, Mapping]] = None) -> Tags:
    """The membership tags of one stem (module docstring).  ``registry`` is :func:`registry_index`'s output."""
    reg = (registry or {}).get(stem)
    return Tags(exists=stem in set(corpus_stems) or stem in renamed,
                queued=stem in queue, queue_status=queue.get(stem),
                is_negative_label=stem in set(negative_label_stems),
                registered=reg is not None, registered_by=tuple(reg["generators"]) if reg else (),
                registered_decided=bool(reg and reg["decided"]))


# --------------------------------------------------------------------------- replies across runs

@dataclass
class Collected:
    """What the named runs answered: per trait the combined reply (``full``, ``principal_only``) and the samples it
    was combined from (``full_samples``, ``principal_only_samples``: ``{stem: {sample: OperatorReply}}``), and the
    runs left out because they carry a ``void.json`` marker (``void``)."""
    full: dict = field(default_factory=dict)
    principal_only: dict = field(default_factory=dict)
    full_samples: dict = field(default_factory=dict)
    principal_only_samples: dict = field(default_factory=dict)
    void: list = field(default_factory=list)

    def sample_replies(self) -> list[OperatorReply]:
        """Every sample of both kinds (the null rates are read over these)."""
        out = []
        for d in (self.full_samples, self.principal_only_samples):
            out += [d[s][k] for s in sorted(d) for k in sorted(d[s])]
        return out

    @property
    def n_samples(self) -> int:
        """The most samples any trait has (the "union of N samples" of the readouts)."""
        return max((len(v) for v in self.full_samples.values()), default=0)


def collect_replies(run_dirs: Sequence[Path], *, lexicon=None, renamed: Optional[Mapping[str, str]] = None
                    ) -> Collected:
    """The named runs' answers (``responses.jsonl``), combined per trait by union of its samples
    (:func:`.combine.combine`).  Within a run the last parsed record per (trait, sample) wins; across runs the run
    named last that has any sample of a trait wins for that trait (its samples are not mixed with another run's).  A
    run with a ``void.json`` marker is left out and listed in ``void``."""
    from . import read_void
    from .combine import combine
    out = Collected()
    for d in run_dirs:
        if read_void(Path(d)) is not None:
            out.void.append(Path(d).name)
            continue
        run_full: dict[str, dict] = {}
        run_ponly: dict[str, dict] = {}
        for rec in read_responses(Path(d) / RESPONSES_NAME):
            rep, _ = reply_from_record(rec)
            if rep is None:
                continue
            (run_ponly if rep.principal_only else run_full).setdefault(rep.stem, {})[rep.sample] = rep
        out.full_samples.update(run_full)
        out.principal_only_samples.update(run_ponly)
    kw = {"lexicon": lexicon, "renamed": renamed}
    out.full = {s: combine(v, **kw) for s, v in sorted(out.full_samples.items())}
    out.principal_only = {s: combine(v, **kw) for s, v in sorted(out.principal_only_samples.items())}
    return out


# --------------------------------------------------------------------------- merge and rank

def _sha(stem: str) -> str:
    return hashlib.sha256(stem.encode("utf-8")).hexdigest()


def _source_key(s: Mapping) -> tuple:
    return (s["generator_part"], s.get("source_stem") or s.get("source_id") or "", s.get("operator") or "",
            s.get("role") or "", s.get("target") or s.get("mode") or "", s.get("label") or "")


def operator_kind(op: str, sub: Optional[str], *, source_unpaired: bool) -> str:
    if op == "opposite":
        return "pair_completion" if source_unpaired else "opposite"
    if op in ("excess", "deficiency"):
        return "degree_filler"
    if op == "retarget":
        return "principal_retarget" if sub in PRINCIPAL_TARGETS else "retarget"
    return "remode"


def _safe_stem(label: str, lexicon) -> Optional[tuple[str, str]]:
    try:
        return stem_of(label, lexicon=lexicon)
    except ValueError:
        return None


def operator_sources(replies: Iterable, *, corpus: Corpus, lexicon=None) -> list[tuple[str, str, dict]]:
    """``(stem, folded label, source)`` for every item of every combined reply (:class:`.combine.CombinedReply`; a
    single sample's :class:`OperatorReply` is combined first).  Each source carries the item's ``support`` (how many
    of the trait's samples named it), the samples, every sample's gloss (``glosses``) and the first one's (``gloss``,
    which becomes the candidate's ``gloss_hint``)."""
    from .combine import CombinedReply, combine
    out = []
    reps = [r if isinstance(r, CombinedReply) else combine({r.sample: r}, lexicon=lexicon) for r in replies]
    for rep in sorted(reps, key=lambda r: (r.stem, r.principal_only)):
        stems: dict[str, list] = {}
        for op in SINGLE_OPERATORS:
            for it in rep.slot(op):
                got = _safe_stem(it["label"], lexicon)
                if got:
                    stems.setdefault(op, []).append(got[0])
        unpaired = corpus.is_unpaired(rep.stem)
        for op, sub, it in rep.items():
            got = _safe_stem(it["label"], lexicon)
            if got is None:
                continue
            stem, folded = got
            partner = None
            if op == "opposite":
                partner = corpus.labels.get(rep.stem) or rep.label
            elif op in ("excess", "deficiency"):
                other = rep.slot("deficiency" if op == "excess" else "excess")
                partner = other[0]["label"] if other else None          # the best-supported sibling vice
            sib = [rep.stem] + ([x for o, xs in stems.items() if o != op for x in xs]
                                if op in SINGLE_OPERATORS else [])
            src = {"generator_part": "operators", "source_stem": rep.stem, "source_label": rep.label, "operator": op,
                   "run_id": rep.run_id, "label": it["label"], "gloss": it.get("gloss"),
                   "has_common_word": it.get("has_common_word"), "polysemy": it.get("polysemy"),
                   "support": it.get("support", 1), "n_samples": rep.n_samples, "samples": list(it.get("samples") or []),
                   "glosses": list(it.get("glosses") or []),
                   "kind": operator_kind(op, sub, source_unpaired=unpaired), "partner_hint": partner,
                   "siblings": sib}
            if op == "retarget":
                src["target"] = sub
            elif op == "remode":
                src["mode"] = sub
            out.append((stem, folded, src))
    return out


def classical_sources(modern_rows: Sequence, *, lexicon=None) -> list[tuple[str, str, dict]]:
    """``(stem, folded label, source)`` for every modern label of every classical row."""
    by_id = {r.id: r for r in modern_rows}
    primary = {}
    for r in modern_rows:
        got = _safe_stem(r.labels[0], lexicon) if r.labels else None
        if got:
            primary[r.id] = got
    out = []
    for r in modern_rows:
        partner = None
        want = CLASSICAL_PARTNER_ROLE.get(r.role)       # a mean, a strength, a lone virtue or a vice: no partner
        for s in r.sibling_ids if want else ():
            if s in by_id and by_id[s].role == want and by_id[s].labels:
                partner = by_id[s].labels[0]
        sibs = [primary[s][0] for s in r.sibling_ids if s in primary]
        for i, lab in enumerate(r.labels):
            got = _safe_stem(lab, lexicon)
            if got is None:
                continue
            stem, folded = got
            out.append((stem, folded, {"generator_part": "classical", "source_id": r.id, "scheme": r.scheme,
                                       "role": r.role, "run_id": r.run_id, "label": lab, "label_rank": i + 1,
                                       "gloss": r.gloss_modern, "has_common_word": len(lab.split()) == 1,
                                       "polysemy": r.polysemy if i == 0 else None, "kind": "classical",
                                       "partner_hint": partner, "siblings": sibs}))
    return out


def merge_items(replies: Iterable[OperatorReply], modern_rows: Sequence = (), *, corpus: Optional[Corpus] = None,
                lexicon=None) -> list[dict]:
    """One row per distinct stem with every source kept (module docstring); untagged and unranked."""
    corpus = corpus or Corpus()
    rows: dict[str, dict] = {}
    for stem, folded, src in operator_sources(replies, corpus=corpus, lexicon=lexicon) + classical_sources(
            modern_rows, lexicon=lexicon):
        r = rows.setdefault(stem, {"stem": stem, "sources": []})
        r["sources"].append({**src, "folded": folded})
    out = []
    for stem in sorted(rows):
        srcs = sorted(rows[stem]["sources"], key=_source_key)
        first = srcs[0]
        reach = {(s["generator_part"], s.get("source_stem") or s.get("source_id")) for s in srcs}
        sibs = sorted({x for s in srcs for x in s.get("siblings") or [] if x != stem})
        hcw = next((s["has_common_word"] for s in srcs if isinstance(s.get("has_common_word"), bool)), None)
        out.append({
            "schema_version": SCHEMA_VERSION, "surface": first["label"], "stem": stem, "label": first["folded"],
            "gloss": next((s["gloss"] for s in srcs if s.get("gloss")), None),
            "sources": [{k: v for k, v in s.items() if k not in ("folded", "siblings")} for s in srcs],
            "n_sources": len(reach),
            "roles": sorted({s.get("operator") or s.get("role") for s in srcs}),
            "kinds": sorted({s["kind"] for s in srcs}),
            "siblings": sibs,
            "has_common_word": hcw if hcw is not None else len(first["folded"].split()) == 1,
            "polysemy": any(s.get("polysemy") is True for s in srcs),
            "max_support": max((s.get("support") or 0 for s in srcs if s["generator_part"] == "operators"),
                               default=None),
            "principal_target": any(s["kind"] == "principal_retarget" for s in srcs),
        })
    return out


def apply_tags(rows: Sequence[dict], *, corpus: Corpus, queue: Mapping[str, str],
               registry: Optional[Mapping[str, Mapping]] = None) -> list[dict]:
    """Every row with its membership tags and ``net_new`` (in place; returned)."""
    neg = corpus.negative_label_stems
    for r in rows:
        t = tag_membership(r["stem"], corpus_stems=corpus.stems, renamed=corpus.renamed, negative_label_stems=neg,
                           queue=queue, registry=registry)
        r.update({"exists": t.exists, "queued": t.queued, "queue_status": t.queue_status,
                  "is_negative_label": t.is_negative_label, "registered": t.registered,
                  "registered_by": list(t.registered_by), "registered_decided": t.registered_decided,
                  "net_new": t.net_new, "status": t.status})
    return list(rows)


def tier(row: Mapping) -> int:
    return min(KIND_TIER[k] for k in row["kinds"]) if row.get("kinds") else max(KIND_TIER.values())


def rank(rows: Sequence[dict]) -> list[dict]:
    """The rows in rank order, ``rank`` (1-based) and ``tier`` set (module docstring)."""
    out = sorted(rows, key=lambda r: (-int(r["n_sources"]), tier(r), _sha(r["stem"])))
    for i, r in enumerate(out, 1):
        r["tier"] = tier(r)
        r["rank"] = i
    return out


def build_table(replies: Iterable[OperatorReply], modern_rows: Sequence = (), *, corpus: Corpus,
                queue: Mapping[str, str], registry: Optional[Mapping[str, Mapping]] = None,
                lexicon=None) -> list[dict]:
    """Merge, tag and rank (the whole of ``postprocess``'s table)."""
    rows = merge_items(replies, modern_rows, corpus=corpus, lexicon=lexicon)
    return rank(apply_tags(rows, corpus=corpus, queue=queue, registry=registry))


# --------------------------------------------------------------------------- the file

def table_text(rows: Sequence[Mapping]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def write_operator_table(rows: Sequence[Mapping], path: Path = OPERATOR_TABLE_PATH) -> Optional[Path]:
    """Write the table; a changed file is first copied to ``.bak.<UTC>`` (snapshot before overwrite).  Returns the
    backup path, if any; an unchanged table is not rewritten."""
    path = Path(path)
    body = table_text(rows)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def load_operator_table(path: Path = OPERATOR_TABLE_PATH) -> list[dict]:
    """The operator table's rows in rank order (frozen interface)."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


__all__ = ["Corpus", "Tags", "KIND_TIER", "load_corpus", "load_queue_index", "is_decided", "registry_index",
           "oewn_lexicon", "stem_of", "tag_membership", "collect_replies", "operator_kind", "operator_sources",
           "classical_sources", "merge_items", "apply_tags", "tier", "rank", "build_table", "table_text",
           "write_operator_table", "load_operator_table"]
