"""The generator's table: one row per stem over every frame (plan section 6).

:func:`build_table` takes each frame's hits (the Books extracts summed over years >= 1920, :func:`.books.read_extract`;
the text extracts, :func:`.text.read_text_extract`) and:

1. folds every filler (:func:`.relabel.fold`: US spelling, then the platform's noun helper), so that
   ``known for his honesty`` and ``a very honest man`` land on one row, ``honest``; a nominal frame's filler counts
   only when it is a person noun (OEWN's person-noun hyponyms) or a noun the helper relabels ("an incorrigible
   old ..." is not a hit);
2. sums ``match`` and ``volumes`` per (frame, stem) and applies the **frame floor** (``match >= 40`` for Books, the
   text frames' own floor of 3);
3. ranks each frame's fillers by **document frequency** (``volumes``: books, or descriptions; ties by match, then stem)
   and by **lift**, ``log10(volumes / frame_total_volumes) - (zipf - 9)``: the filler's share of the frame against its
   share of English (wordfreq's Zipf is log10 occurrences per billion words), which demotes good, old and little;
4. fuses the frames by **reciprocal-rank fusion** (RRF, k = 60): ``rrf = sum over frames of 1 / (60 + rank)``, and
   ``union_rank`` orders by it (ties by Zipf, then surface); ``rrf_lift`` / ``rank_lift_union`` are the same over
   the lift ranks (the ordering is chosen by the free recovery check, :func:`.evaluate.ordering_choice`).  Doubling
   every count of one frame changes no order;
5. records Zipf through :func:`assistant_axis.gapgen.freq.zipf_info` (never a local literal), the OEWN gloss hint
   (the censuses' ``glosshint``), ``eligible = not freq_hard_reject or gloss_hint`` (plan 04's rule), and the
   membership tags (:func:`tag_rows`: corpus, queue, registered, registered and decided, ``net_new``), which no
   rank and no eligibility reads: **no tag drops a row**.

The row's ``surface`` is what is submitted: the filler that is itself the row's label when one is (an adjective, or
a noun the helper leaves), else the most frequent noun that relabels to it; the platform's ``submit_candidates``
then adds the adjective as the noun's linked sibling (``nouns.py``, Roger 2026-10-14: the noun row is always
submitted).  ``label`` is the row's label (the adjective a noun relabels to), ``stem`` its stem; ``surface_stem`` is
the submitted surface's stem, and ``surface_tags`` that stem's membership tags when it differs.  ``fillers`` lists
every filler folded into the row with the helper's answer (the readout's relabel counts); ``frames`` each frame's
``match``, ``volumes``, both ranks, the lift, the top person nouns after it and (text frames) an example sentence.

Deterministic: the same extracts give a byte-identical file; :func:`write_table` keeps the previous file as
``<path>.bak.<UTC>`` when the content changes.  The table is git-ignored, its sha256 recorded (QUESTIONS 80).
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import nouns as N
from assistant_axis.gapgen.freq import FreqInfo, zipf_info
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import utc_stamp

from ..censuses.glosshint import gloss_hint, person_sense
from . import TABLE_PATH
from .relabel import Fold, fold, is_person_noun

SCHEMA_VERSION = 1
RRF_K = 60
#: Top person nouns kept per frame entry.
MAX_NOUNS = 5
ROW_FIELDS: tuple[str, ...] = (
    "schema_version", "surface", "label", "stem", "form", "relabel_rule", "relabel_reason", "us_spelling_from",
    "surface_stem", "fillers", "frames", "n_frames", "best_frame", "types", "sources", "rrf", "union_rank",
    "rrf_lift", "rank_lift_union", "zipf", "freq_hard_reject", "freq_probe_band", "wordnet", "gloss_hint", "eligible",
    "ineligible_reason", "corpus_stem_match", "queue_stem_match", "registered", "registered_decided", "registered_by",
    "net_new", "surface_tags")
TAG_FIELDS: tuple[str, ...] = ("corpus_stem_match", "queue_stem_match", "registered", "registered_decided",
                               "registered_by", "net_new")


@dataclass
class Lookups:
    """What the table looks up; :func:`default_lookups` wires the real ones, tests pass fakes."""
    nouns: object                                      # a ``nouns.NounLookups`` (the helper, US spelling, lexicon)
    senses: Callable[[str], list]                      # ``censuses.glosshint.adjective_senses``
    person_nouns: frozenset = frozenset()              # OEWN's person-noun lemmas (the nominal frames' test)
    zipf_word: Optional[Callable[[str], float]] = None  # per-word Zipf passed to ``zipf_info`` (tests)
    _freq: dict = field(default_factory=dict)

    def freq_info(self, surface: str) -> FreqInfo:
        if surface not in self._freq:
            self._freq[surface] = (zipf_info(surface, zipf_fn=self.zipf_word) if self.zipf_word is not None
                                   else zipf_info(surface))
        return self._freq[surface]


def default_lookups() -> Lookups:  # pragma: no cover - needs wordfreq and the OEWN database
    from assistant_axis.gapgen import wordnet as gw

    from ..censuses.glosshint import adjective_senses
    from .relabel import person_nouns_from_oewn
    if not gw.ensure_oewn(download=False):
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    w = gw.oewn()
    return Lookups(nouns=N.OewnLookups.default(), senses=lambda s: adjective_senses(s, wordnet=w),
                   person_nouns=person_nouns_from_oewn(w))


# --------------------------------------------------------------------------- the registry's tags

def is_decided(row: Mapping) -> bool:
    """M1 and M3 have nothing left to do for a registry row: an M1 verdict other than ``trait``, or a ``trait``
    verdict and an M3 block (plan 04's ``registry_stems``; plan 09's ``is_decided``)."""
    f = row.get("filter") or {}
    if not f:
        return False
    return f.get("verdict") != "trait" or bool(row.get("novelty"))


def registry_index(rows: Mapping[str, Mapping]) -> dict[str, dict]:
    """``{stem: {"generators", "decided", "key"}}`` from a folded registry (the lowest sense id per stem)."""
    out: dict[str, dict] = {}
    for key, r in sorted(rows.items(), key=lambda kv: (kv[1].get("stem") or "", int(kv[1].get("sense_id") or 1))):
        st = r.get("stem")
        if not st or st in out:
            continue
        gens = sorted({s.get("generator") for s in r.get("sources") or [] if s.get("generator")})
        out[st] = {"generators": gens, "decided": is_decided(r), "key": key}
    return out


def _tags(stem: str, *, corpus: set, queue: set, registry: Mapping[str, Mapping]) -> dict:
    reg = registry.get(stem)
    c, q, d = stem in corpus, stem in queue, bool(reg and reg.get("decided"))
    return {"corpus_stem_match": c, "queue_stem_match": q, "registered": reg is not None,
            "registered_decided": d, "registered_by": list(reg.get("generators") or []) if reg else [],
            "net_new": not (c or q or d)}


def tag_rows(rows: Sequence[dict], *, corpus_stems: Iterable[str] = (), renamed: Optional[Mapping[str, str]] = None,
             queue_stems: Iterable[str] = (), registry: Optional[Mapping[str, Mapping]] = None) -> list[dict]:
    """Set the membership tags on every row (in place; returns the rows).  ``renamed``: old corpus stem -> current
    (an old stem counts as a corpus stem); ``registry``: :func:`registry_index`'s output.  Read by the readout, the
    estimate and the wave's count only: no rank, no eligibility, no selection reads them."""
    corpus = set(corpus_stems) | set(renamed or {})
    queue = set(queue_stems)
    reg = registry or {}
    for r in rows:
        r.update(_tags(r["stem"], corpus=corpus, queue=queue, registry=reg))
        ss = r.get("surface_stem")
        r["surface_tags"] = (_tags(ss, corpus=corpus, queue=queue, registry=reg)
                             if ss and ss != r["stem"] else None)
    return list(rows)


# --------------------------------------------------------------------------- building

def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    return None if x is None else round(float(x), nd)


def _top(counter: Mapping[str, int]) -> Optional[str]:
    if not counter:
        return None
    return min(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def build_table(hits: Mapping[str, Sequence], *, frames: Mapping[str, object], lookups: Lookups,
                corpus_stems: Iterable[str] = (), renamed: Optional[Mapping[str, str]] = None,
                queue_stems: Iterable[str] = (), registry: Optional[Mapping[str, Mapping]] = None,
                counts_out: Optional[dict] = None) -> list[dict]:
    """The table rows in union-rank order (see the module docstring).  ``hits``: ``{frame key: [books.Hit]}``;
    ``frames``: ``{frame key: Frame or TextFrame}``; ``counts_out`` receives the per-frame counts before the floor
    (``hits``, ``fillers``, ``rejected_kind``, ``malformed``, ``total_volumes``)."""
    folds: dict[tuple[str, str], Fold] = {}
    agg: dict[tuple[str, str], dict] = {}
    counts: dict[str, dict] = {}
    for key in sorted(hits):
        fr = frames[key]
        kind = "adj" if fr.filler_kind == "adj" else "noun"
        c = counts.setdefault(key, {"hits": 0, "fillers": 0, "rejected_kind": 0, "malformed": 0, "total_volumes": 0})
        stems_seen = set()
        for h in hits[key]:
            c["hits"] += int(h.match)
            fk = (h.filler, kind)
            if fk not in folds:
                folds[fk] = fold(h.filler, lookups=lookups.nouns, kind_hint=kind)
            f = folds[fk]
            if fr.filler_kind == "noun" and not (is_person_noun(f.surface, lookups.person_nouns) or f.relabelled):
                c["rejected_kind"] += 1
                continue
            try:
                stem = normalize_candidate(f.label).stem
            except ValueError:
                c["malformed"] += 1
                continue
            stems_seen.add(stem)
            a = agg.setdefault((key, stem), {"match": 0, "volumes": 0, "nouns": Counter(), "surfaces": Counter(),
                                             "folds": {}, "example": None})
            a["match"] += int(h.match)
            a["volumes"] += int(h.volumes)
            c["total_volumes"] += int(h.volumes)
            if h.noun:
                a["nouns"][h.noun] += int(h.volumes)
            a["surfaces"][f.surface] += int(h.volumes)
            a["folds"][f.surface] = f
            if a["example"] is None and getattr(h, "example", None):
                a["example"] = h.example
        c["fillers"] = len(stems_seen)
    if counts_out is not None:
        counts_out.update(counts)
    above = {k: a for k, a in agg.items() if a["match"] >= int(frames[k[0]].floor)}
    by_frame: dict[str, list] = {}
    for (key, stem), a in sorted(above.items()):
        by_frame.setdefault(key, []).append((stem, a))
    for key, ents in by_frame.items():
        total = counts[key]["total_volumes"]
        for i, (stem, a) in enumerate(sorted(ents, key=lambda e: (-e[1]["volumes"], -e[1]["match"], e[0])), 1):
            a["rank_volumes"] = i
        for stem, a in ents:
            top = _top(a["surfaces"])
            z = lookups.freq_info(top).zipf_min
            a["lift"] = (_r(math.log10(a["volumes"] / total) - (z - 9.0)) if a["volumes"] > 0 and total > 0
                         else None)
        for i, (stem, a) in enumerate(sorted(ents, key=lambda e: (-(e[1]["lift"] if e[1]["lift"] is not None
                                                                        else -1e9), -e[1]["volumes"], e[0])), 1):
            a["rank_lift"] = i
    by_stem: dict[str, dict[str, dict]] = {}
    for (key, stem), a in sorted(above.items()):
        by_stem.setdefault(stem, {})[key] = a
    rows = []
    for stem, fa in sorted(by_stem.items()):
        surfaces: Counter = Counter()
        fmap: dict[str, Fold] = {}
        for a in fa.values():
            surfaces.update(a["surfaces"])
            fmap.update(a["folds"])
        plain = {s: v for s, v in surfaces.items() if not fmap[s].relabelled}
        surface = _top(plain) if plain else _top(surfaces)
        sf = fmap[surface]
        try:
            surface_stem = normalize_candidate(surface).stem
        except ValueError:
            surface_stem = stem
        fi = lookups.freq_info(surface)
        hint = person_sense(lookups.senses(surface))
        gh = gloss_hint(surface, hint, ()) if hint else None
        eligible = (not fi.hard_reject) or bool(gh)
        fr_rec = {}
        for key in sorted(fa):
            a = fa[key]
            rec = {"match": a["match"], "volumes": a["volumes"], "rank_volumes": a["rank_volumes"],
                   "rank_lift": a["rank_lift"], "lift": a["lift"],
                   "nouns": [n for n, _ in sorted(a["nouns"].items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_NOUNS]],
                   "surface": _top(a["surfaces"])}
            if a["example"]:
                rec["example"] = a["example"]
            fr_rec[key] = rec
        best = min(fa, key=lambda k: (fa[k]["rank_volumes"], -fa[k]["volumes"], k))
        rows.append({
            "schema_version": SCHEMA_VERSION, "surface": surface, "label": sf.label, "stem": stem, "form": sf.form,
            "relabel_rule": sf.rule, "relabel_reason": sf.reason, "us_spelling_from": sf.us_spelling_from,
            "surface_stem": surface_stem,
            "fillers": [{"surface": s, "raw": fmap[s].raw, "form": fmap[s].form, "rule": fmap[s].rule,
                         "reason": fmap[s].reason, "volumes": v}
                        for s, v in sorted(surfaces.items(), key=lambda kv: (-kv[1], kv[0]))],
            "frames": fr_rec, "n_frames": len(fa), "best_frame": best,
            "types": sorted({frames[k].type for k in fa}), "sources": sorted({frames[k].source for k in fa}),
            "rrf": round(sum(1.0 / (RRF_K + fa[k]["rank_volumes"]) for k in sorted(fa)), 10), "union_rank": 0,
            "rrf_lift": round(sum(1.0 / (RRF_K + fa[k]["rank_lift"]) for k in sorted(fa)), 10), "rank_lift_union": 0,
            "zipf": fi.zipf_min, "freq_hard_reject": fi.hard_reject, "freq_probe_band": fi.probe_band,
            "wordnet": {"found": hint is not None, "pos": hint.pos if hint else None,
                        "definition": hint.definition if hint else None,
                        "n_adj_senses": hint.n_adj_senses if hint else 0},
            "gloss_hint": gh, "eligible": eligible, "ineligible_reason": None if eligible else "below_hard_reject",
        })
    tag_rows(rows, corpus_stems=corpus_stems, renamed=renamed, queue_stems=queue_stems, registry=registry)
    return union_rank(rows)


def rrf(ranks_by_frame: Mapping[str, Mapping[str, int]], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal-rank fusion: ``{item: sum over frames of 1 / (k + rank)}`` from ``{frame: {item: rank}}``."""
    out: dict[str, float] = {}
    for fr in sorted(ranks_by_frame):
        for item, rank in ranks_by_frame[fr].items():
            out[item] = out.get(item, 0.0) + 1.0 / (k + int(rank))
    return out


def union_rank(rows: Sequence[dict]) -> list[dict]:
    """Number ``union_rank`` by ``rrf`` and ``rank_lift_union`` by ``rrf_lift`` (descending; ties by Zipf
    descending, then surface, then stem); returns the rows in ``union_rank`` order."""
    def order(field_):
        return sorted(rows, key=lambda r: (-float(r[field_]), -(r.get("zipf") or 0.0), r["surface"], r["stem"]))
    for i, r in enumerate(order("rrf_lift"), 1):
        r["rank_lift_union"] = i
    out = order("rrf")
    for i, r in enumerate(out, 1):
        r["union_rank"] = i
    return out


def rerank_over(rows: Sequence[Mapping], frame_keys: Iterable[str], *, ordering: str = "volumes") -> list[dict]:
    """The rows found by at least one of ``frame_keys``, ranked by RRF over those frames only (a dropped frame's
    ranks no longer count), as copies with ``wave_rank`` set (1 = first); ties as :func:`union_rank`."""
    keep = set(frame_keys)
    field_ = "rank_volumes" if ordering == "volumes" else "rank_lift"
    scored = []
    for r in rows:
        ks = [k for k in sorted(r.get("frames") or {}) if k in keep]
        if not ks:
            continue
        s = sum(1.0 / (RRF_K + int(r["frames"][k][field_])) for k in ks)
        scored.append((-round(s, 10), -(r.get("zipf") or 0.0), r["surface"], r["stem"], r))
    out = []
    for i, t in enumerate(sorted(scored, key=lambda t: t[:4]), 1):
        d = dict(t[4])
        d["wave_rank"] = i
        out.append(d)
    return out


# --------------------------------------------------------------------------- on disk

def row_text(r: Mapping) -> str:
    return json.dumps({k: r.get(k) for k in ROW_FIELDS}, ensure_ascii=False, separators=(",", ":"))


def table_text(rows: Sequence[Mapping]) -> str:
    return "".join(row_text(r) + "\n" for r in rows)


def write_table(rows: Sequence[Mapping], path: Path = TABLE_PATH) -> Optional[Path]:
    """Write the table; when the content changes the old file is first copied to ``<path>.bak.<UTC>`` (snapshot
    before overwrite).  Returns the backup path, if any."""
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


def load_frames_table(path: Path = TABLE_PATH) -> list[dict]:
    """The table (frozen interface): one dict per stem in union-rank order, ``schema_version`` 1."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- the person-usage lookup

@dataclass(frozen=True)
class PersonFreq:
    """How often a word is used of a person in Books (frozen interface): its volumes over the Books frames that found
    it, per frame, and how many frames."""
    volumes_total: int
    frames: dict
    n_frames: int


_PF_CACHE: dict = {}


def _is_books_key(key: str) -> bool:
    return "." not in key


def person_frequency(word: str, *, table: Optional[Sequence[Mapping]] = None,
                     path: Path = TABLE_PATH) -> Optional[PersonFreq]:
    """The workstream's "how often is W used of a person in Books" (frozen interface): the Books frames' volumes of
    the row W belongs to (by its stem, or as one of the row's fillers: ``honesty`` finds the ``honest`` row), or
    ``None`` when no Books frame found the word (a text-only row is ``None`` too)."""
    if table is None:
        p = Path(path)
        sig = (str(p), p.stat().st_mtime_ns if p.exists() else None)
        if sig not in _PF_CACHE:
            _PF_CACHE.clear()
            _PF_CACHE[sig] = load_frames_table(p) if p.exists() else []
        table = _PF_CACHE[sig]
    try:
        st = normalize_candidate(word).stem
    except ValueError:
        return None
    row = next((r for r in table if r.get("stem") == st), None)
    if row is None:
        row = next((r for r in table for f in r.get("fillers") or []
                    if normalize_candidate(f["surface"]).stem == st), None)
    if row is None:
        return None
    fr = {k: int(v["volumes"]) for k, v in sorted((row.get("frames") or {}).items()) if _is_books_key(k)}
    if not fr:
        return None
    return PersonFreq(volumes_total=sum(fr.values()), frames=fr, n_frames=len(fr))


# --------------------------------------------------------------------------- the per-frame statistics

def frame_stats(rows: Sequence[Mapping], *, frames: Mapping[str, object], counts: Mapping[str, Mapping],
                shard_plan: Optional[Mapping] = None, manifest: Optional[Mapping] = None,
                text_stats: Optional[Mapping] = None) -> list[dict]:
    """Per frame (in the bank's order, Books first): its type, tier, source and template; its shards, lines scanned
    and hits (from the shard plan and the manifest, Books), or its documents (text); distinct fillers, those above the
    floor, the rejected and malformed ones; the forms of its rows; the registered, corpus and net-new shares (the
    free columns; ``evaluate`` adds the recovery, and after the pilot the measures and the keep verdict)."""
    shards_of: dict[str, list] = {}
    for s in (shard_plan or {}).get("shards") or []:
        for f in s.get("frames") or []:
            shards_of.setdefault(f, []).append(s.get("index"))
    lines_scanned: Counter = Counter()
    kept: Counter = Counter()
    for rec in (manifest or {}).get("shards") or []:
        for f in rec.get("frames") or []:
            lines_scanned[f] += int(rec.get("lines_scanned") or 0)
            kept[f] += int((rec.get("lines_kept") or {}).get(f) or 0)
    in_frame: dict[str, list] = {}
    for r in rows:
        for k in r.get("frames") or {}:
            in_frame.setdefault(k, []).append(r)
    out = []
    for key in frame_order(frames):
        fr = frames[key]
        rs = in_frame.get(key, [])
        c = counts.get(key) or {}
        n = len(rs)
        d = {"frame": key, "type": fr.type, "tier": fr.tier, "source": fr.source,
             "template": getattr(fr, "template", ""), "floor": fr.floor, "filler_kind": fr.filler_kind}
        if fr.source == "books":
            d.update({"shards": sorted(shards_of.get(key, [])), "lines_scanned": lines_scanned.get(key),
                      "lines_kept": kept.get(key)})
        else:
            src = ((text_stats or {}).get("sources") or {}).get(fr.source) or {}
            d.update({"documents": src.get("n_unique")})
        d.update({"hits": c.get("hits", 0), "fillers": c.get("fillers", 0), "above_floor": n,
                  "rejected_kind": c.get("rejected_kind", 0), "malformed": c.get("malformed", 0),
                  "forms": dict(sorted(Counter(r.get("form") for r in rs).items())),
                  "registered_share": round(sum(1 for r in rs if r.get("registered")) / n, 4) if n else None,
                  "corpus_share": round(sum(1 for r in rs if r.get("corpus_stem_match")) / n, 4) if n else None,
                  "net_new_share": round(sum(1 for r in rs if r.get("net_new")) / n, 4) if n else None,
                  "unique_rows": sum(1 for r in rs if r.get("n_frames") == 1)})
        out.append(d)
    return out


def frame_order(frames: Mapping[str, object]) -> list[str]:
    """Frame keys in the bank's order: the Books frames as :data:`.frames.FRAME_BANK` lists them, then the text frames
    by source and as :data:`.text.TEXT_FRAME_SPECS` lists them."""
    from .frames import FRAME_BANK
    from .text import TEXT_FRAME_SPECS
    pos = {f.id: i for i, f in enumerate(FRAME_BANK)}
    tpos = {s.id: i for i, s in enumerate(TEXT_FRAME_SPECS)}

    def k(key: str):
        if key in pos:
            return (0, "", pos[key], key)
        src, _, base = key.partition(".")
        return (1, src, tpos.get(base, 99), key)
    return sorted(frames, key=k)


def table_counts(rows: Sequence[Mapping]) -> dict:
    return {"n_rows": len(rows), "n_eligible": sum(1 for r in rows if r.get("eligible")),
            "n_net_new": sum(1 for r in rows if r.get("net_new")),
            "forms": dict(sorted(Counter(r.get("form") for r in rows).items())),
            "relabelled": sum(1 for r in rows if r.get("surface_stem") != r.get("stem")),
            "relabel_rules": dict(sorted(Counter(str(f.get("rule")) for r in rows for f in r.get("fillers") or []
                                                 if f.get("rule") not in (None, "none")).items())),
            "nouns_left": sum(1 for r in rows if r.get("form") == "noun"),
            "us_spelling_folds": sum(1 for r in rows for f in r.get("fillers") or [] if f.get("raw", "").lower()
                                     != f.get("surface")),
            "corpus_stem_match": sum(1 for r in rows if r.get("corpus_stem_match")),
            "queue_stem_match": sum(1 for r in rows if r.get("queue_stem_match")),
            "registered": sum(1 for r in rows if r.get("registered")),
            "registered_decided": sum(1 for r in rows if r.get("registered_decided")),
            "sources": dict(sorted(Counter(s for r in rows for s in r.get("sources") or []).items())),
            "n_frames": dict(sorted(Counter(int(r.get("n_frames") or 0) for r in rows).items()))}


__all__ = ["SCHEMA_VERSION", "RRF_K", "ROW_FIELDS", "TAG_FIELDS", "Lookups", "default_lookups", "is_decided",
           "registry_index", "tag_rows", "build_table", "rrf", "union_rank", "rerank_over", "row_text", "table_text",
           "write_table", "load_frames_table", "file_sha256", "PersonFreq", "person_frequency", "frame_stats",
           "frame_order", "table_counts"]
