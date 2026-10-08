"""The recovery harness: does a generator find again the traits the corpus already has?

Plan 13's core as re-specified in ``reports/trait_gap_generation/coding_plan_platform.md``, "The recovery
harness" (2026-10-08).  A seeded share of the corpus's traits is hidden, the generator's run is scored by M3
against the corpus without them, and every candidate M3 decided is matched against the hidden traits; a hidden
trait that one of the run's kept candidates matches is *recovered*.  The CLI is
``data_analysis/gap_generation/recovery_test.py``; the scoring is ``novelty_score.py score --hide``.

1. **Hide** (:func:`draw_hidden`).  The corpus's traits fall into *hiding groups* (:func:`hiding_groups`, the
   closure of :attr:`novelty.CorpusTrait.expands_to`): a recorded pair, triangle, tetrahedron or larger simplex
   hides whole; any other trait, a sequence member included, hides alone.  Each group belongs to a *stratum*,
   its members' most common region in ``corpus_regions.json`` (``none`` for a trait with no region).  Each
   stratum hides ``frac`` of its traits (largest-remainder rounding, so the corpus hides ``round(frac x N)``),
   taking its groups in a seeded order until its quota is met (the group that crosses the quota is taken
   whole).  Drawing groups rather than stems gives every trait the same chance of being hidden, paired or
   alone; drawing ``frac`` of the stems and adding their partners would hide pair members about twice as often
   as singletons and hide about 1.7 times the fraction.  :func:`write_hidden` writes ``hidden.json``.
2. **Score against the reduced corpus** (``novelty_score.py score --hide hidden.json``): :func:`reduced_traits`
   takes the hidden traits out of the corpus (the index is fitted without them, and expansion and the
   "opposite" rule no longer reach them) and :func:`reduced_label_sets` out of the exact-label check (the
   corpus stems, the seed queue's entries for them, their ``renamed_from``).  Such a run writes its own run
   directory and never the registry.
3. **Match** (:func:`match_plan`, :func:`label_matches`, :func:`match_candidates`).  For each candidate the
   reduced run decided, a hidden trait is matched when the candidate's normalised label equals the hidden stem
   or one of its ``renamed_from`` (separator-blind, as M3's rule set 2 compares labels; no call), or when the
   overlap call (rubric A, one pair per call, the candidate's gloss against the hidden trait's description,
   Sonnet then Opus under the pipeline's rule, :meth:`novelty_runner.NoveltyRunner.read_pairs`) reads at the
   candidate's cut-off or above (:func:`pair_outcome`: the rule set's ``cuts``).  Only the hidden traits among
   the candidate's ``k`` nearest by cosine in the *full* corpus are judged.
4. **Report** (:func:`seed_figures`, :func:`combine_seeds`, :func:`report_markdown`).  For the candidates M3
   kept (``new`` or ``grey``): recall (hidden traits matched), by region and by arrangement kind; precision
   (the kept candidates that match a hidden trait); hiding groups recovered whole.  The same figures for the
   candidates M3 decided ``covered`` against the reduced corpus: a *false cover* is such a candidate that
   matches a hidden trait, a candidate that fills the hidden trait's gap but was turned away because another
   trait covered it.  Reachability: the hidden traits among some decided candidate's ``k`` nearest (or matched
   by label), the most that the ``k``-nearest restriction lets recall reach.  Cost by stage.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text

from . import novelty as NV
from .registry import utc_now

HIDDEN_SCHEMA = 1
DEFAULT_HIDDEN_FRAC = 0.1
#: Two seeds by default; the report gives each and their mean.
DEFAULT_SEEDS: tuple[int, ...] = (0, 1)
NO_REGION = "none"
#: The decisions whose candidates count for recall: the ones M3 keeps.
KEPT_DECISIONS: tuple[str, ...] = ("new", "grey")
#: Kinds of a hidden trait for the report, largest structure first (:func:`arrangement_kinds`).
UNCLASSIFIED = "unclassified"


# --------------------------------------------------------------------------- 1. hide

def hiding_groups(traits: Mapping[str, NV.CorpusTrait]) -> list[list[str]]:
    """The corpus split into the sets of traits that hide together: the connected components of
    :attr:`~novelty.CorpusTrait.expands_to` (a recorded pair, triangle, tetrahedron or simplex, with the
    label-reciprocal pair partner); every other trait alone.  Each group sorted; groups in order of their
    first member."""
    seen: set[str] = set()
    out = []
    for s in sorted(traits):
        if s in seen:
            continue
        comp: set[str] = set()
        stack = [s]
        while stack:
            a = stack.pop()
            if a in comp or a not in traits:
                continue
            comp.add(a)
            stack.extend(m for m in traits[a].expands_to if m in traits and m not in comp)
        seen |= comp
        out.append(sorted(comp))
    return out


def arrangement_kinds(data_dir: Path, traits: Mapping[str, NV.CorpusTrait]) -> dict[str, str]:
    """``{stem: kind}`` for the report: the largest simplex a trait is a corner of (``tetrahedron``,
    ``triangle``, ``N-simplex``), else ``pair`` (a recorded or label-reciprocal pair), else the first kind its
    ``arrangement`` field records (``singleton``, ``sequence``, ``ring``, ``set``, ``square``, ...), else
    ``unclassified``."""
    from assistant_axis.arrangements import load_corpus_arrangements
    recs = load_corpus_arrangements(Path(data_dir), "traits")
    out = {}
    for s, t in traits.items():
        kinds = [a.kind for a in (recs[s].arrangements if s in recs else [])]
        if t.simplexes:
            out[s] = max(t.simplexes, key=lambda x: (len(x["members"]), x["kind"]))["kind"]
        elif t.pair_partner or "pair" in kinds:
            out[s] = "pair"
        else:
            out[s] = kinds[0] if kinds else UNCLASSIFIED
    return out


def load_regions(path: Path) -> dict[str, Optional[str]]:
    """``{stem: region}`` from ``corpus_regions.json`` (its ``result`` block); ``{}`` when the file is absent."""
    p = Path(path)
    if not p.exists():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    res = doc.get("result", doc) if isinstance(doc, dict) else {}
    return {s: (v or {}).get("region") for s, v in res.items() if isinstance(v, Mapping) or v is None}


def _group_stratum(members: Sequence[str], regions: Mapping[str, Optional[str]]) -> str:
    """A group's stratum: its members' most common region (ties: the first member's), ``none`` for no region."""
    rs = [regions.get(m) or NO_REGION for m in members]
    c = Counter(rs)
    top = max(c.values())
    return next(r for r in rs if c[r] == top)


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def stratum_quotas(sizes: Mapping[str, int], frac: float) -> dict[str, int]:
    """``frac`` of each stratum's traits, rounded by largest remainder so that the quotas sum to
    ``round(frac x total)`` (ties by stratum name)."""
    raw = {s: frac * n for s, n in sizes.items()}
    q = {s: int(math.floor(v + 1e-9)) for s, v in raw.items()}
    rest = _round_half_up(frac * sum(sizes.values())) - sum(q.values())
    for s in sorted(raw, key=lambda s: (-(raw[s] - q[s]), s))[:max(0, rest)]:
        q[s] += 1
    return q


def draw_hidden(traits: Mapping[str, NV.CorpusTrait], *, frac: float, seed: int,
                regions: Mapping[str, Optional[str]], kinds: Mapping[str, str]) -> dict:
    """The hidden set of one seed (the module docstring, step 1): ``{"schema", "seed", "hidden_frac",
    "n_corpus", "n_target", "n_hidden", "n_groups", "hidden": [stems], "groups": [{"members", "stratum",
    "kind"}], "strata": {stratum: {"n_traits", "n_groups", "quota", "n_hidden", "n_groups_hidden"}},
    "traits": {stem: {"region", "stratum", "kind", "group"}}}``."""
    if not 0.0 <= float(frac) <= 1.0:
        raise ValueError(f"the hidden fraction must be from 0 to 1, not {frac!r}")
    groups = hiding_groups(traits)
    strata: dict[str, list[list[str]]] = defaultdict(list)
    for g in groups:
        strata[_group_stratum(g, regions)].append(g)
    sizes = {s: sum(len(g) for g in gs) for s, gs in strata.items()}
    quotas = stratum_quotas(sizes, float(frac))
    rng = random.Random(int(seed))
    taken: list[tuple[str, list[str]]] = []
    by_stratum = {}
    for s in sorted(strata):
        gs = sorted(strata[s])
        rng.shuffle(gs)
        n, mine = 0, []
        for g in gs:
            if n >= quotas[s]:
                break
            mine.append(g)
            n += len(g)
        taken += [(s, g) for g in mine]
        by_stratum[s] = {"n_traits": sizes[s], "n_groups": len(gs), "quota": quotas[s], "n_hidden": n,
                         "n_groups_hidden": len(mine)}
    taken.sort(key=lambda x: x[1])
    out_groups, tr = [], {}
    for i, (s, g) in enumerate(taken):
        out_groups.append({"members": list(g), "stratum": s, "kind": kinds.get(g[0], UNCLASSIFIED)})
        for m in g:
            tr[m] = {"region": regions.get(m), "stratum": s, "kind": kinds.get(m, UNCLASSIFIED), "group": i}
    hidden = sorted(tr)
    return {"schema": HIDDEN_SCHEMA, "seed": int(seed), "hidden_frac": float(frac), "n_corpus": len(traits),
            "n_target": _round_half_up(float(frac) * len(traits)), "n_hidden": len(hidden),
            "n_groups": len(out_groups), "hidden": hidden, "groups": out_groups, "strata": by_stratum,
            "traits": tr}


def file_sha256(path: Path) -> Optional[str]:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def corpus_fingerprint(data_dir: Path) -> str:
    """A hash of the trait files (names and bytes): whether a hidden set was drawn on today's corpus."""
    h = hashlib.sha256()
    for p in sorted((Path(data_dir) / "traits" / "instructions").glob("*.json")):
        h.update(p.name.encode("utf-8") + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def write_hidden(path: Path, doc: Mapping, *, data_dir: Path, regions_path: Optional[Path],
                 git_sha: Optional[str] = None) -> dict:
    """``hidden.json``: :func:`draw_hidden`'s record plus where it was drawn (the corpus's data dir, file
    count and fingerprint, the regions file's path and hash, the git sha, the time)."""
    full = dict(doc) | {
        "corpus": {"data_dir": str(data_dir), "n_trait_files": doc["n_corpus"],
                   "fingerprint": corpus_fingerprint(data_dir)},
        "regions_file": {"path": str(regions_path) if regions_path else None,
                         "sha256": file_sha256(regions_path) if regions_path else None},
        "git_sha": git_sha, "drawn_at": utc_now()}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(full, indent=2, ensure_ascii=False) + "\n", p)
    return full


def load_hidden(path: Path) -> dict:
    """``{"path", "sha256" (of the file's bytes), "stems" (sorted), "doc"}`` of a ``hidden.json`` (any JSON
    object with a ``hidden`` list of stems will do); ``ValueError`` otherwise."""
    p = Path(path)
    raw = p.read_bytes()
    doc = json.loads(raw)
    stems = doc.get("hidden") if isinstance(doc, dict) else None
    if not isinstance(stems, list) or not all(isinstance(s, str) and s for s in stems):
        raise ValueError(f"{p}: not a hidden-traits file (no 'hidden' list of stems)")
    return {"path": str(p), "sha256": hashlib.sha256(raw).hexdigest(), "stems": sorted(set(stems)), "doc": doc}


# --------------------------------------------------------------------------- 2. the reduced corpus

def reduced_traits(traits: Mapping[str, NV.CorpusTrait], hidden: Iterable[str]) -> dict[str, NV.CorpusTrait]:
    """The corpus without ``hidden``: those traits gone, and gone from every other trait's partners, expansion
    members and pair partner; a simplex with a hidden corner is no longer recorded on its other corners (a
    hiding group hides whole, so this happens only for a hand-made hidden list).  ``ValueError`` for a hidden
    stem the corpus does not have (a hidden file drawn on another corpus)."""
    hid = set(hidden)
    unknown = sorted(hid - set(traits))
    if unknown:
        raise ValueError(f"{len(unknown)} hidden stem(s) not in the corpus: {', '.join(unknown[:10])}"
                         + (" ..." if len(unknown) > 10 else ""))
    out = {}
    for s, t in traits.items():
        if s in hid:
            continue
        out[s] = replace(t, partners=[p for p in t.partners if p not in hid],
                         expands_to=[m for m in t.expands_to if m not in hid],
                         pair_partner=None if t.pair_partner in hid else t.pair_partner,
                         simplexes=[dict(x) for x in t.simplexes if not set(x["members"]) & hid])
    return out


def reduced_label_sets(reduced: Mapping[str, NV.CorpusTrait], queue: Mapping, hidden: Iterable[str]) -> NV.LabelSets:
    """Stage 0's names for the reduced corpus: :func:`novelty.label_sets` of ``reduced`` (so neither the hidden
    stems nor their ``renamed_from`` cover), less every seed-queue name that is a hidden stem or belongs to an
    entry whose stem is hidden (a corpus trait also has a queue entry once it was seeded from the queue)."""
    hid = set(hidden)
    sets = NV.label_sets(reduced, queue)
    queue_names = {n: e for n, e in sets.queue.items() if n not in hid and e.get("stem") not in hid}
    return NV.LabelSets(corpus=set(sets.corpus), queue=queue_names, renamed=dict(sets.renamed))


# --------------------------------------------------------------------------- 3. match

def label_matches(stem: str, hidden_traits: Mapping[str, NV.CorpusTrait]) -> list[dict]:
    """The hidden traits a candidate's normalised label names, separator-blind: its stem
    (``{"stem", "match": "stem"}``) or one of its ``renamed_from`` (``"match": "renamed_from", "old_stem"``);
    ``"blind": True`` where only the separators differ."""
    b = NV.blind(stem)
    out = []
    for h in sorted(hidden_traits):
        if NV.blind(h) == b:
            out.append({"stem": h, "match": "stem"} | ({"blind": True} if h != stem else {}))
            continue
        for old in hidden_traits[h].renamed_from:
            if NV.blind(old) == b:
                out.append({"stem": h, "match": "renamed_from", "old_stem": old} | ({"blind": True} if old != stem else {}))
                break
    return out


def match_plan(cands: Sequence, vectors: Mapping[str, Any], index: NV.CorpusIndex, hidden: Iterable[str], *,
               k: int) -> tuple[list[dict], dict[str, list[str]]]:
    """``(items, near)``.  ``items``: per candidate (an :class:`novelty_runner.M3Candidate`), its label matches
    (``how: "label"``, no call) and then the hidden traits among its ``k`` nearest in the full corpus
    ``index`` that its label does not name (``how: "overlap"``, one overlap call each), each with its cosine and
    rank there.  ``near``: key -> the hidden stems among its ``k`` nearest (reachability).  A candidate with no
    vector gets its label matches only."""
    hid = set(hidden)
    hidden_traits = {s: index.traits[s] for s in sorted(hid)}
    items: list[dict] = []
    near: dict[str, list[str]] = {}
    for c in cands:
        lm = label_matches(c.stem, hidden_traits)
        named = {m["stem"] for m in lm}
        q = index.project(vectors[c.key]) if c.key in vectors else None
        nn = index.retrieve(q, k) if q is not None else []
        rank = {s: i for i, (s, _) in enumerate(nn, 1)}
        near[c.key] = [s for s, _ in nn if s in hid]
        for m in lm:
            cos = index.cosine_to(q, m["stem"]) if q is not None else None
            items.append({"key": c.key, "stem": m["stem"], "how": "label", "match": m,
                          "cosine": round(float(cos), 6) if cos is not None else None, "rank": rank.get(m["stem"])})
        for s, cos in nn:
            if s in hid and s not in named:
                items.append({"key": c.key, "stem": s, "how": "overlap", "cosine": round(float(cos), 6),
                              "rank": rank[s]})
    return items, near


def pair_outcome(reading: Mapping, c: int, rules: Optional[NV.Rules] = None) -> dict:
    """One overlap pair under the pipeline's rule at cut-off ``c`` (:func:`novelty.pair_verdict`):
    ``{"verdict", "at_or_above", "recovers"}``, ``recovers`` when the rule set covers on it
    (:func:`novelty.verdict_cuts`: Sonnet above c, or Opus at c or above where Sonnet read c or was unsure,
    and under rule set 2 Sonnet c - 1 with Opus at c or above)."""
    s = (reading.get("sonnet") or {}).get("value")
    o = (reading.get("opus") or {}).get("value") if reading.get("opus") else None
    pv = NV.pair_verdict(s, o, c)
    return {**pv, "recovers": NV.verdict_cuts(pv["verdict"], rules)}


def match_candidates(runner, cands: Sequence, vectors: Mapping[str, Any], hidden: Iterable[str], *, k: int,
                     decisions: Mapping[str, Mapping], rules: Optional[NV.Rules] = None,
                     wave: str = "m") -> tuple[list[dict], dict[str, list[str]]]:
    """Step 3 for ``cands`` (decided by the reduced run; ``decisions``: key -> its ``novelty`` block): the label
    matches, and the overlap pairs read through ``runner`` (a :class:`novelty_runner.NoveltyRunner` on the
    *full* corpus, so that it knows the hidden traits' descriptions; its records, usage and transport are the
    match stage's).  Returns ``(rows, near)``: one row per label match and per pair judged (the candidate, its
    reduced-run decision and covering trait, the hidden trait, cosine and rank, how, the readings, the verdict,
    ``recovers``; ``stalled`` for a pair left without an answer), and :func:`match_plan`'s ``near``.  A stop (a
    budget stop) is raised after every answer is recorded."""
    rules = rules or NV.DEFAULT_RULES
    by_key = {c.key: c for c in cands}
    items, near = match_plan(cands, vectors, runner.index, hidden, k=k)
    pairs = [(it["key"], it["stem"], it["rank"] or 0) for it in items if it["how"] == "overlap"]
    readings = runner.run_pairs([by_key[k_] for k_ in dict.fromkeys(p[0] for p in pairs)], pairs, wave=wave) \
        if pairs else {}
    rows = []
    for it in items:
        c, nv = by_key[it["key"]], decisions.get(it["key"]) or {}
        base = {"key": c.key, "label": c.label, "decision": nv.get("decision"), "covered_by": nv.get("covered_by"),
                "cut_off": c.cut_off, "stem": it["stem"], "how": it["how"], "cosine": it["cosine"], "rank": it["rank"]}
        if it["how"] == "label":
            rows.append(base | {"match": it["match"], "recovers": True})
            continue
        r = readings.get((c.key, it["stem"]))
        if r is None or "stalled" in r:
            rows.append(base | {"stalled": (r or {}).get("stalled", "not read"), "recovers": False})
            continue
        rows.append(base | {"sonnet": r["sonnet"], "opus": r["opus"]} | pair_outcome(r, c.cut_off, rules))
    return rows, near


# --------------------------------------------------------------------------- 4. report

def _share(n: int, d: int) -> Optional[float]:
    return round(n / d, 4) if d else None


def _by(field: str, hidden_doc: Mapping, recovered: set) -> dict:
    tr = hidden_doc["traits"]
    tot, got = Counter(), Counter()
    for s in hidden_doc["hidden"]:
        v = (tr.get(s) or {}).get(field) or (NO_REGION if field == "region" else UNCLASSIFIED)
        tot[v] += 1
        got[v] += s in recovered
    return {v: {"n_hidden": tot[v], "n_recovered": got[v], "recall": _share(got[v], tot[v])} for v in sorted(tot)}


def _short_row(r: Mapping) -> dict:
    keep = ("key", "label", "how", "decision", "covered_by", "cut_off", "cosine", "rank", "match", "sonnet", "opus",
            "verdict")
    return {k: r[k] for k in keep if k in r}


def section_figures(hidden_doc: Mapping, rows: Sequence[Mapping], keys: set) -> dict:
    """Recall and the rest over the candidates ``keys`` (one section of the report): hidden traits matched by
    one of them (by label, or by the overlap call only), by region and by arrangement kind; the candidates that
    match something (precision); the hiding groups of two or more matched whole, in part, not at all; and every
    recovered trait with the candidates that recovered it."""
    tr = hidden_doc["traits"]
    hidden = list(hidden_doc["hidden"])
    rec: dict[str, list] = defaultdict(list)
    for r in rows:
        if r["key"] in keys and r.get("recovers"):
            rec[r["stem"]].append(r)
    by_label = sum(1 for rs in rec.values() if any(x["how"] == "label" for x in rs))
    recovering = {r["key"] for rs in rec.values() for r in rs}
    groups = Counter()
    for g in hidden_doc.get("groups") or []:
        m = g["members"]
        if len(m) < 2:
            continue
        n = sum(1 for s in m if s in rec)
        groups["whole" if n == len(m) else ("partial" if n else "none")] += 1
    return {
        "n_hidden": len(hidden), "n_recovered": len(rec), "recall": _share(len(rec), len(hidden)),
        "by_label": by_label, "by_overlap_only": len(rec) - by_label,
        "by_region": _by("region", hidden_doc, set(rec)), "by_kind": _by("kind", hidden_doc, set(rec)),
        "candidates": {"n": len(keys), "n_recovering": len(recovering), "precision": _share(len(recovering), len(keys))},
        "groups": {"n": sum(groups.values()), **{k: groups.get(k, 0) for k in ("whole", "partial", "none")}},
        "recovered": [{"stem": s, "region": (tr.get(s) or {}).get("region"), "kind": (tr.get(s) or {}).get("kind"),
                       "by": [_short_row(x) for x in sorted(rec[s], key=lambda x: (x["how"] != "label", x["key"]))]}
                      for s in sorted(rec)],
    }


def seed_figures(hidden_doc: Mapping, results: Sequence[Mapping], rows: Sequence[Mapping], *,
                 near: Mapping[str, Sequence[str]], reduced_run: Optional[Mapping] = None,
                 cost: Optional[Mapping] = None) -> dict:
    """One seed's report: ``hidden`` (the counts and the strata), ``candidates`` (the reduced run's decisions),
    ``reachable``, ``kept`` (recall over the candidates M3 kept), ``covered`` (the same over the covered ones,
    with the false covers listed), ``either`` (both: the recall had M3 kept every candidate), ``pairs`` (the
    overlap pairs judged, by verdict), ``reduced_run`` and ``cost`` as given."""
    dec = {r["key"]: (r.get("novelty") or {}).get("decision") for r in results}
    kept = {k for k, d in dec.items() if d in KEPT_DECISIONS}
    covered = {k for k, d in dec.items() if d == "covered"}
    hid = set(hidden_doc["hidden"])
    reach = {s for k, ss in near.items() if k in dec for s in ss if s in hid} | \
        {r["stem"] for r in rows if r["how"] == "label" and r["key"] in dec}
    reach_kept = {s for k, ss in near.items() if k in kept for s in ss if s in hid} | \
        {r["stem"] for r in rows if r["how"] == "label" and r["key"] in kept}
    kept_f = section_figures(hidden_doc, rows, kept)
    cov_f = section_figures(hidden_doc, rows, covered)
    either = section_figures(hidden_doc, rows, kept | covered)
    got_kept = {x["stem"] for x in kept_f["recovered"]}
    false_covers = [_short_row(r) | {"stem": r["stem"], "recovered_by_a_kept_candidate": r["stem"] in got_kept}
                    for r in sorted(rows, key=lambda r: (r["key"], r["stem"]))
                    if r["key"] in covered and r.get("recovers")]
    cov_f["false_covers"] = false_covers
    cov_f["n_false_cover_candidates"] = len({r["key"] for r in false_covers})
    cov_f["hidden_missed_only_through_covers"] = sorted({r["stem"] for r in false_covers} - got_kept)
    judged = [r for r in rows if r["how"] == "overlap"]
    return {
        "seed": hidden_doc.get("seed"), "hidden_frac": hidden_doc.get("hidden_frac"),
        "hidden": {k: hidden_doc.get(k) for k in ("n_corpus", "n_target", "n_hidden", "n_groups", "strata")},
        "hidden_stems": list(hidden_doc["hidden"]),
        "candidates": {"n_decided": len(dec), "by_decision": dict(Counter(dec.values())),
                       "n_kept": len(kept), "n_covered": len(covered)},
        "reachable": {"n": len(reach), "share": _share(len(reach), len(hid)),
                      "n_by_kept": len(reach_kept), "share_by_kept": _share(len(reach_kept), len(hid))},
        "kept": kept_f, "covered": cov_f, "either": either,
        "pairs": {"n_overlap": len(judged), "n_label": sum(1 for r in rows if r["how"] == "label"),
                  "n_stalled": sum(1 for r in judged if r.get("stalled")),
                  "verdicts": dict(Counter(r.get("verdict") or "stalled" for r in judged))},
        "reduced_run": dict(reduced_run or {}), "cost": dict(cost or {}),
    }


def _mean(xs: Iterable[Optional[float]]) -> Optional[float]:
    v = [float(x) for x in xs if x is not None]
    return round(sum(v) / len(v), 4) if v else None


def combine_seeds(seeds: Sequence[Mapping]) -> dict:
    """The report over seeds: each seed's figures (:func:`seed_figures`) and their mean (recall, precision and
    the rest, recall by region and by arrangement kind over the seeds that hide that region or kind, cost)."""
    def mean_of(path):
        def get(s):
            x = s
            for p in path:
                x = (x or {}).get(p)
            return x
        return _mean(get(s) for s in seeds)

    def mean_breakdown(section: str, field: str) -> dict:
        names = sorted({n for s in seeds for n in s[section][field]})
        return {n: {"recall": _mean(s[section][field][n]["recall"] for s in seeds if n in s[section][field]),
                    "n_hidden": _mean(s[section][field][n]["n_hidden"] for s in seeds if n in s[section][field])}
                for n in names}
    mean = {
        "n_hidden": mean_of(("hidden", "n_hidden")),
        "recall_kept": mean_of(("kept", "recall")), "precision_kept": mean_of(("kept", "candidates", "precision")),
        "recovered_kept": mean_of(("kept", "n_recovered")), "recovered_by_label": mean_of(("kept", "by_label")),
        "recall_covered": mean_of(("covered", "recall")),
        "false_cover_candidates": mean_of(("covered", "n_false_cover_candidates")),
        "recall_either": mean_of(("either", "recall")), "reachable_share": mean_of(("reachable", "share")),
        "groups_whole": mean_of(("kept", "groups", "whole")), "groups": mean_of(("kept", "groups", "n")),
        "cost_usd": mean_of(("cost", "total_usd")),
        "kept_by_region": mean_breakdown("kept", "by_region"), "kept_by_kind": mean_breakdown("kept", "by_kind"),
    }
    return {"seeds": list(seeds), "mean": mean, "n_seeds": len(seeds),
            "total_cost_usd": round(sum((s.get("cost") or {}).get("total_usd") or 0.0 for s in seeds), 6)}


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _reading(r: Mapping) -> str:
    if r.get("how") == "label":
        m = r.get("match") or {}
        return "label" + (f" (renamed from {m.get('old_stem')})" if m.get("match") == "renamed_from" else "") + \
            (", separator-blind" if m.get("blind") else "")
    s = (r.get("sonnet") or {}).get("value")
    o = (r.get("opus") or {}).get("value") if r.get("opus") else None
    return f"Sonnet {s}" + (f", Opus {o}" if r.get("opus") else "")


def report_markdown(report: Mapping, *, batch_id: str, generator: str, run_id: str,
                    labels: Optional[Mapping[str, str]] = None, trait_rel: str = "../../../traits/instructions/",
                    novelty_rel: str = "../../novelty/") -> str:
    """``recovery_report.md`` (beside ``recovery_report.json`` in ``data/candidates/recovery/<batch>/``; the
    links are relative to it): what was measured, the figures per seed and their mean, recall by region and
    kind, the recovered traits with the candidates that recovered them, the false covers."""
    labels = labels or {}

    def T(s):  # noqa: N802 - a link to a trait file
        return f"[{_md(labels.get(s) or s.replace('_', ' '))}]({trait_rel}{s}.json)" if s else ""
    seeds = report["seeds"]
    m = report["mean"]
    L = [f"# Recovery test: `{generator}/{run_id}` (`{batch_id}`)", "",
         "The recovery harness ([recovery_test.py](../../../../data_analysis/gap_generation/recovery_test.py), library "
         "[recovery.py](../../../../assistant_axis/gapgen/recovery.py)) hides a seeded share of the corpus's traits, "
         "scores the generator's run with M3 against the corpus without them "
         "([novelty_score.py](../../../../data_analysis/gap_generation/novelty_score.py) `score --hide`), and asks which "
         "hidden traits the run's candidates find again.  Terms:", "",
         "- **hidden**: traits taken out of the corpus for the test; a pair, triangle or tetrahedron hides whole, any "
         "other trait alone, drawn by region so that each region hides its share.",
         "- **kept**: a candidate M3 decided `new` or `grey` against the reduced corpus (what the pipeline would pass "
         "on); **covered**: one M3 turned away because a remaining trait covers it.",
         "- **recovered**: a hidden trait matched by a kept candidate, by its label (the same stem or a former stem, "
         "no model call) or by the overlap call (rubric A, Sonnet then Opus under M3's rule) at the candidate's "
         "cut-off or above (the cut-off is 3 on rubric A's 0-4 scale far from alignment, 4 near it).",
         "- **recall**: hidden traits recovered over hidden traits; **precision**: kept candidates that recover a "
         "hidden trait over kept candidates (low by design when a generator proposes mostly genuinely new words).",
         "- **false cover**: a covered candidate that matches a hidden trait: it fills the hidden trait's gap but M3 "
         "turned it away because another trait covers it (often a near-duplicate of the hidden one).",
         "- **reachable**: hidden traits among some decided candidate's 10 nearest traits in the full corpus (or "
         "named by its label): only those are judged, so this bounds recall.", "",
         "## Figures", "",
         "| seed | hidden | kept candidates | recall | by label | precision | groups whole | reachable | "
         "false covers (candidates) | recall incl. covered | cost |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in seeds:
        k, c, e = s["kept"], s["covered"], s["either"]
        L.append(f"| {s['seed']} | {s['hidden']['n_hidden']} of {s['hidden']['n_corpus']} | {k['candidates']['n']} | "
                 f"{_pct(k['recall'])} ({k['n_recovered']}) | {k['by_label']} | {_pct(k['candidates']['precision'])} | "
                 f"{k['groups']['whole']} of {k['groups']['n']} | {_pct(s['reachable']['share'])} | "
                 f"{c['n_false_cover_candidates']} | {_pct(e['recall'])} | ${(s.get('cost') or {}).get('total_usd', 0):.3f} |")
    if len(seeds) > 1:
        L.append(f"| mean | {m['n_hidden']:g} | | {_pct(m['recall_kept'])} | {m['recovered_by_label']:g} | "
                 f"{_pct(m['precision_kept'])} | {m['groups_whole'] or 0:g} of {m['groups'] or 0:g} | "
                 f"{_pct(m['reachable_share'])} | {m['false_cover_candidates']:g} | {_pct(m['recall_either'])} | "
                 f"${m['cost_usd'] or 0:.3f} |")
    L += ["", f"Total cost ${report['total_cost_usd']:.3f} (each seed's reduced-corpus M3 run and its match calls; "
          "[usage.json](./usage.json); every figure is in [recovery_report.json](./recovery_report.json)).", ""]
    for field, title in (("by_region", "region"), ("by_kind", "arrangement kind")):
        names = sorted({n for s in seeds for n in s["kept"][field]})
        L += [f"## Recall by {title}", "", "| " + title + " | " + " | ".join(f"seed {s['seed']}" for s in seeds) + " |",
              "|---|" + "---|" * len(seeds)]
        for n in names:
            cells = []
            for s in seeds:
                d = s["kept"][field].get(n)
                cells.append(f"{d['n_recovered']} of {d['n_hidden']} ({_pct(d['recall'])})" if d else "")
            L.append(f"| {n} | " + " | ".join(cells) + " |")
        L.append("")
    for s in seeds:
        rr = s.get("reduced_run") or {}
        L += [f"## Seed {s['seed']}", "",
              f"Hidden traits: [hidden.json](./seed{s['seed']}/hidden.json); the reduced-corpus M3 run: "
              f"[decisions.md]({novelty_rel}{rr.get('batch_id', '')}/decisions.md) "
              f"({json.dumps(s['candidates']['by_decision'])}); every pair judged: "
              f"[matches.jsonl](./seed{s['seed']}/matches.jsonl).", "",
              f"### Recovered ({s['kept']['n_recovered']} of {s['kept']['n_hidden']})", "",
              "| hidden trait | region | kind | recovered by | how |", "|---|---|---|---|---|"]
        for x in s["kept"]["recovered"]:
            L.append(f"| {T(x['stem'])} | {x['region'] or ''} | {x['kind']} | "
                     f"{', '.join(_md(b['label']) for b in x['by'])} | {'; '.join(_md(_reading(b)) for b in x['by'])} |")
        fc = s["covered"]["false_covers"]
        L += ["", f"### False covers ({s['covered']['n_false_cover_candidates']} candidates)", "",
              "| candidate | matches hidden | how | covered by | hidden trait recovered anyway |", "|---|---|---|---|---|"]
        for r in fc:
            L.append(f"| {_md(r['label'])} | {T(r['stem'])} | {_md(_reading(r))} | {T(r.get('covered_by'))} | "
                     f"{'yes' if r['recovered_by_a_kept_candidate'] else 'no'} |")
        missed = sorted(set(s.get("hidden_stems") or []) - {x["stem"] for x in s["kept"]["recovered"]})
        if missed:
            L += ["", f"### Not recovered ({len(missed)})", "", ", ".join(T(x) for x in missed)]
        L.append("")
    return "\n".join(L) + "\n"
