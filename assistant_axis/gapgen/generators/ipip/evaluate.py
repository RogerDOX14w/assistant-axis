"""The run's evaluation: everything counted from files on disk, no calls.

* :func:`census_overlap`: the share of blind labels that are census words (the frozen ``load_census_table`` of the
  census generator: TDA and Allport-Odbert stems).
* :func:`known_analogues`: the corpus stems that match an IPIP construct label: ``exact`` (the label, or one of its
  "/" alternatives, through ``normalize_to_file_name``: "Achievement-striving" -> ``achievement_striving``), the
  plan's definition; and, reported apart, ``variant`` (simple derivations: orderliness -> orderly, sociability ->
  sociable, anxiety -> anxious), since construct labels are nouns and corpus labels mostly adjectives.
* :func:`recovery_from_covers`: plan § 7 ``report``'s free recovery readout, the ``covered_by`` inversion: a known
  analogue is recovered when some candidate of the run was decided covered by it (or is it by label); target > 90%,
  report and decide; every miss is listed for reading.
* :func:`naming_agreement`: blind against hinted labels (disagreement rate), and in bipolar clusters whether each
  pole's antonym names the other pole (target > 80%): ``exact`` when the two normalise alike, ``overlap`` when they
  share a content word after a crude stemming (grudge-holding / holds grudges).
* :func:`cost_summary` and :func:`useful_per_dollar` (rows decided ``new`` or marked a pair completion, per dollar
  of the summed usage files); :func:`m1_m3_fractions`.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name

KNOWN_ANALOGUE_TARGET = 0.9
ANTONYM_TARGET = 0.8
_STOP = frozenset("a an the to of in on at for with and or by from about as is be being one oneself others other "
                  "own my their things".split())


# --------------------------------------------------------------------------- census overlap

def census_stems(table: Iterable) -> set[str]:
    return {r.stem for r in table if getattr(r, "stem", None)}


def load_census_stems(path: Optional[Path] = None) -> Optional[set[str]]:
    """The census table's stems through the frozen loader, or ``None`` when the table is not on disk."""
    from assistant_axis.gapgen.generators import censuses as C
    p = Path(path) if path else C.CENSUS_TABLE_PATH
    if not p.exists():
        return None
    return census_stems(C.load_census_table(p))


def census_overlap(stems: Iterable[str], census: set[str]) -> dict:
    stems = list(stems)
    hit = sorted({s for s in stems if s in census})
    n_hit = sum(1 for s in stems if s in census)
    return {"n": len(stems), "n_census": n_hit, "share": round(n_hit / len(stems), 4) if stems else None,
            "words": hit}


# --------------------------------------------------------------------------- known analogues

_DERIVATIONS: tuple[tuple[str, str], ...] = (
    ("iness", "y"), ("ability", "able"), ("ibility", "ible"), ("iety", "ious"), ("ence", "ent"), ("ance", "ant"),
    ("ness", ""), ("ity", "e"), ("ity", ""), ("ion", "ive"), ("ism", "ist"),
)


def _variants(stem: str) -> set[str]:
    out = set()
    last = stem.split("_")[-1]
    head = stem[: len(stem) - len(last)]
    for suf, rep in _DERIVATIONS:
        if last.endswith(suf) and len(last) - len(suf) >= 3:
            out.add(head + last[: -len(suf)] + rep)
    return out - {stem}


def construct_alternatives(label: str) -> list[str]:
    """A construct label's names: "Aesthetic Appreciation/Artistic Interests" -> both, normalised."""
    out = []
    for part in re.split(r"[/,]", label):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(normalize_to_file_name(part))
        except ValueError:
            continue
    return out


def known_analogues(constructs: Iterable[str], corpus_stems: Iterable[str]) -> dict:
    """``{"exact": {stem: [construct labels]}, "variant": {...}}`` (see the module docstring)."""
    corpus = set(corpus_stems)
    exact: dict[str, set] = {}
    variant: dict[str, set] = {}
    for lab in sorted(set(constructs)):
        for alt in construct_alternatives(lab):
            if alt in corpus:
                exact.setdefault(alt, set()).add(lab)
            for v in _variants(alt):
                if v in corpus:
                    variant.setdefault(v, set()).add(lab)
    variant = {k: v for k, v in variant.items() if k not in exact}
    return {"exact": {k: sorted(v) for k, v in sorted(exact.items())},
            "variant": {k: sorted(v) for k, v in sorted(variant.items())}}


def _covered_by(row: Mapping) -> set[str]:
    nv = row.get("novelty") or {}
    out = set()
    if nv.get("covered_by"):
        out.add(nv["covered_by"])
    el = nv.get("exact_label")
    if isinstance(el, Mapping) and el.get("covered_by"):
        out.add(el["covered_by"])
    return out


def recovery_from_covers(registry_rows: Iterable[Mapping], analogues: Iterable[str]) -> dict:
    rows = list(registry_rows)
    hits: dict[str, list] = {}
    for a in sorted(set(analogues)):
        keys = sorted(r.get("key") for r in rows if r.get("novelty") and (a in _covered_by(r) or r.get("stem") == a))
        if keys:
            hits[a] = keys
    n = len(set(analogues))
    return {"n_analogues": n, "n_hit": len(hits), "share": round(len(hits) / n, 4) if n else None,
            "target": KNOWN_ANALOGUE_TARGET, "hits": hits, "misses": sorted(set(analogues) - set(hits))}


# --------------------------------------------------------------------------- naming

def _stem_word(w: str) -> str:
    w = w.lower()
    for suf in ("ing", "ed", "es", "ly", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def content_words(label: str) -> set[str]:
    return {_stem_word(w) for w in re.findall(r"[a-z']+", label.lower().replace("-", " ")) if w not in _STOP}


def antonym_match(antonym: Optional[str], other_label: Optional[str]) -> Optional[str]:
    """``"exact"``, ``"overlap"`` or ``None`` (see the module docstring)."""
    if not antonym or not other_label:
        return None
    try:
        if normalize_to_file_name(antonym) == normalize_to_file_name(other_label):
            return "exact"
    except ValueError:
        return None
    return "overlap" if content_words(antonym) & content_words(other_label) else None


def naming_agreement(rows: Sequence[Mapping], *, consensus: Optional[str] = "kept") -> dict:
    poles = [(r, p) for r in rows if consensus is None or r.get("consensus") == consensus for p in r["poles"]]
    named = {f: [p[f] for _, p in poles if p.get(f)] for f in ("blind", "hinted")}
    both = [p for _, p in poles if p.get("blind") and p.get("hinted")]
    dis = [p for p in both if p["blind"]["stem"] != p["hinted"]["stem"]]
    dirs, exact, overlap, examples = 0, 0, 0, []
    for r in rows:
        if (consensus is not None and r.get("consensus") != consensus) or len(r["poles"]) != 2:
            continue
        a, b = r["poles"]
        if not (a.get("blind") and b.get("blind")):
            continue
        for x, y in ((a, b), (b, a)):
            if not x["blind"].get("antonym_label"):
                continue
            dirs += 1
            m = antonym_match(x["blind"]["antonym_label"], y["blind"]["label"])
            exact += m == "exact"
            overlap += m == "overlap"
            if m is None and len(examples) < 20:
                examples.append({"cluster_id": r["cluster_id"], "pole": x["pole"], "antonym": x["blind"]["antonym_label"],
                                 "other_pole_label": y["blind"]["label"]})

    def share(xs, key):
        return round(sum(1 for x in xs if x.get(key)) / len(xs), 4) if xs else None
    return {"n_named": {f: len(v) for f, v in named.items()},
            "is_trait": {f: share(v, "is_trait") for f, v in named.items()},
            "single_word_exists": share(named["blind"], "single_word_exists"),
            "ambiguity_flag": share(named["blind"], "ambiguity_flag"),
            "n_both_forms": len(both), "disagree_rate": round(len(dis) / len(both), 4) if both else None,
            "bipolar_directions": dirs, "antonym_exact": exact, "antonym_overlap": overlap,
            "antonym_agreement": round((exact + overlap) / dirs, 4) if dirs else None, "antonym_target": ANTONYM_TARGET,
            "antonym_misses": examples}


# --------------------------------------------------------------------------- M1, M3, cost

def m1_m3_fractions(registry_rows: Sequence[Mapping]) -> dict:
    filt = [r for r in registry_rows if r.get("filter")]
    nov = [r for r in registry_rows if r.get("novelty")]

    def frac(c: Counter, n: int) -> dict:
        return {k: {"n": v, "share": round(v / n, 4)} for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))} if n else {}
    return {"n_rows": len(registry_rows), "n_filtered": len(filt),
            "verdict": frac(Counter(r["filter"].get("verdict") for r in filt), len(filt)),
            "outcome": frac(Counter(r["filter"].get("outcome") for r in filt), len(filt)),
            "n_scored": len(nov), "decision": frac(Counter(r["novelty"].get("decision") for r in nov), len(nov)),
            "pair_completions": sum(1 for r in nov if r["novelty"].get("pair_completion_for")),
            "review_flags": sum(1 for r in nov if r["novelty"].get("review"))}


def cost_summary(paths: Mapping[str, Path]) -> dict:
    """Sum ``usage.json`` files (``MultiModelUsage.as_dict`` shape) per model and per stage."""
    per_model: dict[str, float] = {}
    by_stage: dict[str, float] = {}
    files = {}
    for stage, p in paths.items():
        p = Path(p)
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        files[stage] = str(p)
        tot = 0.0
        for m, u in (d.get("per_model") or {}).items():
            c = float(u.get("cost_usd") or 0.0)
            per_model[m] = round(per_model.get(m, 0.0) + c, 6)
            tot += c
        by_stage[stage] = round(tot, 6)
    return {"files": files, "per_model": dict(sorted(per_model.items())), "by_stage": by_stage,
            "total_usd": round(sum(per_model.values()), 6)}


def useful_per_dollar(registry_rows: Sequence[Mapping], usd: float) -> dict:
    nov = [r["novelty"] for r in registry_rows if r.get("novelty")]
    n_new = sum(1 for b in nov if b.get("decision") == "new")
    n_pc = sum(1 for b in nov if b.get("pair_completion_for") and b.get("decision") != "new")
    useful = n_new + n_pc
    return {"n_new": n_new, "n_pair_completion": n_pc, "useful": useful, "usd": round(float(usd), 4),
            "per_dollar": round(useful / usd, 4) if usd else None}


def sample_poles(rows: Sequence[Mapping], n: int = 40, *, seed: int = 0, form: str = "blind") -> list[tuple[dict, dict]]:
    """``n`` seeded (row, pole) pairs among the named poles of kept clusters (the Roger sample)."""
    named = [(r, p) for r in rows if r.get("consensus") == "kept" for p in r["poles"] if p.get(form)]
    named.sort(key=lambda rp: (int(rp[0]["granularity"]), int(rp[0]["cluster_id"]), rp[1]["pole"]))
    if len(named) <= n:
        return named
    return sorted(random.Random(seed).sample(named, n),
                  key=lambda rp: (int(rp[0]["granularity"]), int(rp[0]["cluster_id"]), rp[1]["pole"]))
