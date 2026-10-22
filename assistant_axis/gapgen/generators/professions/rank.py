"""The ranking of B's lay roles (coding plan 16, § 5b and § 7d "Ranking").

Roger, 2026-10-16: aim for missing occupations that are common, well known, and not especially similar to the
corpus's.  So each lay role gets three features:

* ``zipf``: the Zipf frequency of the lay title (``wordfreq``, a phrase scored as wordfreq scores it);
* ``log_employment``: log10 of its group's OEWS employment (a broad group's; a job title takes its occupation's
  detailed employment, :func:`.soc.detailed_employment`); a role that several groups name takes the largest;
* ``distance``: ``1 - cosine`` to the nearest corpus role by the role index (``novelty.load_role_corpus`` embedded as
  ``label: description`` in the covered representation through the embedding cache, ``novelty.build_index`` with
  M2's settings, or the metric config's ``roles`` section when there is one), the query the lay gloss in the role
  query form ``role_gloss_w14`` (its opening "A/An <role> is" taken out, cut to 14 words).

Each feature is z-scored over the run (a missing value counts as the mean, z 0, and is flagged), the three summed
with weights 1, 1, 1 (``--weights``), highest first; ties by employment, then by stem.  A role whose nearest corpus
role is at cosine :data:`NEAR_CORPUS_COSINE` or above is still ranked (M3's hierarchy line decides covered) but
flagged ``near_corpus``.

The ranking has one row per stem (:func:`ranking_rows`): a lay role several groups name (nurse under registered
nurses and under licensed practical nurses) is one row whose ``sources`` list every group, so that its submission
carries every source reference.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

import numpy as np

RANK_WEIGHTS: dict[str, float] = {"zipf": 1.0, "employment": 1.0, "distance": 1.0}
FEATURES: dict[str, str] = {"zipf": "zipf", "employment": "log_employment", "distance": "distance"}
NEAR_CORPUS_COSINE = 0.75
QUERY_FORM = "role_gloss_w14"
TOP_N = 40


def parse_weights(text: Optional[str]) -> dict[str, float]:
    """``zipf=1,employment=1,distance=1`` (any subset; the rest keep :data:`RANK_WEIGHTS`)."""
    out = dict(RANK_WEIGHTS)
    if not text:
        return out
    for part in text.split(","):
        k, sep, v = part.partition("=")
        k = k.strip()
        if not sep or k not in RANK_WEIGHTS:
            raise ValueError(f"--weights takes {','.join(f'{k}=W' for k in RANK_WEIGHTS)}, not {text!r}")
        out[k] = float(v)
    return out


# --------------------------------------------------------------------------- one row per stem

def _best(sources: Sequence[Mapping]) -> Mapping:
    return max(sources, key=lambda s: (s.get("employment") or -1, s.get("support") or 0,
                                       s.get("kind") == "broad"))


def ranking_rows(lay_rows: Sequence[Mapping]) -> list[dict]:
    """One row per lay-role stem over ``lay.jsonl``'s groups (module docstring): ``role``, ``stem``, ``group`` (the
    source with the largest employment), ``gloss`` (that source's, else the first with one), ``employment`` (the
    largest), ``support`` (the largest), ``distinct_persona`` (any source's), ``sources``."""
    by: dict[str, list] = {}
    order: list[str] = []
    for g in lay_rows:
        for r in g.get("roles") or []:
            src = {"group": g["group"], "kind": g.get("kind"), "code": g.get("code"), "source_ref": g.get("source_ref"),
                   "title": g.get("title"), "alternate_title": g.get("alternate_title"), "role": r["role"],
                   "gloss": r.get("gloss"), "support": r.get("support"), "distinct_persona": r.get("distinct_persona"),
                   "covers": r.get("covers"), "employment": g.get("employment"), "zipf_title": g.get("zipf")}
            if r["stem"] not in by:
                by[r["stem"]] = []
                order.append(r["stem"])
            by[r["stem"]].append(src)
    out = []
    for stem in order:
        srcs = by[stem]
        best = _best(srcs)
        gloss = best.get("gloss") or next((s["gloss"] for s in srcs if s.get("gloss")), None)
        emps = [s["employment"] for s in srcs if s.get("employment") is not None]
        out.append({"role": best["role"], "stem": stem, "group": best["group"], "gloss": gloss,
                    "employment": max(emps) if emps else None,
                    "support": max(int(s.get("support") or 0) for s in srcs),
                    "distinct_persona": any(bool(s.get("distinct_persona")) for s in srcs),
                    "kinds": sorted({str(s.get("kind")) for s in srcs}), "sources": srcs})
    return out


# --------------------------------------------------------------------------- features

def default_zipf() -> Callable[[str], float]:
    from wordfreq import zipf_frequency
    return lambda text: float(zipf_frequency(text, "en"))


def familiarity(role: Mapping, *, zipf: Callable[[str], float], employment: Optional[float]) -> dict:
    """``{"zipf", "employment", "log_employment"}`` of a ranking row: the Zipf of its lay title and log10 of the
    employment it is ranked by (None when there is none)."""
    e = None if employment is None else float(employment)
    return {"zipf": round(float(zipf(role["role"])), 3), "employment": None if e is None else int(e),
            "log_employment": round(math.log10(e), 4) if e and e > 0 else None}


def role_query(role: Mapping, *, query_form: str = QUERY_FORM) -> Optional[str]:
    """The text the role index is queried with: the lay gloss in ``query_form`` (None without a gloss)."""
    from assistant_axis.gapgen import novelty as NV
    if not role.get("gloss"):
        return None
    return NV.query_text(role["role"], role["gloss"], query_form=query_form)


def distances(roles: Sequence[Mapping], *, role_index, embed: Callable[[Sequence[str]], np.ndarray],
              query_form: str = QUERY_FORM) -> list[dict]:
    """``{"nearest_role", "cosine", "distance", "query"}`` for each row (all None for a row without a gloss).
    ``embed(texts) -> (n, d)`` raw unit rows (``embed.embed_texts`` through the cache, charged)."""
    queries = [role_query(r, query_form=query_form) for r in roles]
    todo = [q for q in queries if q]
    vecs = {}
    if todo:
        E = embed(list(dict.fromkeys(todo)))
        vecs = dict(zip(list(dict.fromkeys(todo)), E))
    out = []
    for q in queries:
        if not q:
            out.append({"nearest_role": None, "cosine": None, "distance": None, "query": None})
            continue
        z = role_index.project(np.asarray(vecs[q]))
        hit = role_index.retrieve(z, 1)
        stem, cos = (hit[0] if hit else (None, None))
        out.append({"nearest_role": stem, "cosine": None if cos is None else round(float(cos), 4),
                    "distance": None if cos is None else round(1.0 - float(cos), 4), "query": q})
    return out


def distance(role: Mapping, *, role_index, embed: Callable[[Sequence[str]], np.ndarray],
             query_form: str = QUERY_FORM) -> dict:
    """:func:`distances` for one row."""
    return distances([role], role_index=role_index, embed=embed, query_form=query_form)[0]


def zscores(values: Sequence[Optional[float]]) -> list[Optional[float]]:
    """z-scores over the values present (population standard deviation; all 0 when it is 0); None stays None."""
    xs = [float(v) for v in values if v is not None]
    if not xs:
        return [None for _ in values]
    mu = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs))
    return [None if v is None else (0.0 if sd == 0 else (float(v) - mu) / sd) for v in values]


def rank(rows: Sequence[Mapping], *, weights: Optional[Mapping[str, float]] = None,
         near_corpus: float = NEAR_CORPUS_COSINE) -> list[dict]:
    """Rows carrying ``zipf``, ``log_employment`` and ``distance`` (None where missing), z-scored, weighted, summed
    and sorted (module docstring).  Adds ``z`` (per feature), ``missing`` (features counted as the mean),
    ``score``, ``rank`` (1 = best) and ``near_corpus``."""
    w = dict(RANK_WEIGHTS)
    w.update(weights or {})
    rows = [dict(r) for r in rows]
    zs = {k: zscores([r.get(f) for r in rows]) for k, f in FEATURES.items()}
    for i, r in enumerate(rows):
        r["z"] = {k: None if zs[k][i] is None else round(zs[k][i], 4) for k in FEATURES}
        r["missing"] = [k for k in FEATURES if zs[k][i] is None]
        r["score"] = round(sum(w[k] * (zs[k][i] or 0.0) for k in FEATURES), 4)
        cos = r.get("cosine")
        r["near_corpus"] = bool(cos is not None and cos >= near_corpus)
    rows.sort(key=lambda r: (-r["score"], -(r.get("employment") or -1), r["stem"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def rank_roles(lay_rows: Sequence[Mapping], *, zipf: Callable[[str], float], role_index=None,
               embed: Optional[Callable[[Sequence[str]], np.ndarray]] = None,
               weights: Optional[Mapping[str, float]] = None, query_form: str = QUERY_FORM) -> list[dict]:
    """``ranking.jsonl``'s rows from ``lay.jsonl``'s: one row per stem, its familiarity, its distance (when a role
    index and an embedder are given), ranked."""
    rows = ranking_rows(lay_rows)
    for r in rows:
        r.update(familiarity(r, zipf=zipf, employment=r.get("employment")))
    if role_index is not None and embed is not None:
        for r, d in zip(rows, distances(rows, role_index=role_index, embed=embed, query_form=query_form)):
            r.update(d)
    else:
        for r in rows:
            r.update({"nearest_role": None, "cosine": None, "distance": None, "query": None})
    return rank(rows, weights=weights)


# --------------------------------------------------------------------------- the role index

def role_index_settings(cfg) -> dict:
    """The role index's settings: the metric config's ``roles`` section (``representation``, ``space.variant``)
    when it has one (a recalibration, coding plan 16 decision 11), else M2's covered settings."""
    roles = (getattr(cfg, "extra", None) or {}).get("roles") or {}
    cov = dict(cfg.covered)
    rep = roles.get("representation") or cov["representation"]
    variant = ((roles.get("space") or {}).get("variant")) or cov["space"]["variant"]
    return {"representation": rep, "variant": variant, "metric": "cos", "source": "roles" if roles else "covered",
            "config_version": getattr(cfg, "config_version", None)}


def role_index_texts(data_dir: Path, representation: str) -> tuple[dict, list[str]]:
    """The role corpus (``novelty.load_role_corpus``) and its embedded texts, in ``sorted(stems)`` order."""
    from assistant_axis.gapgen import novelty as NV
    from assistant_axis.gapgen.representation import represent
    roles = NV.load_role_corpus(Path(data_dir))
    return roles, [represent(roles[s].label, roles[s].description, representation) for s in sorted(roles)]


def build_role_index(data_dir: Path, *, cfg, embed: Callable[[Sequence[str]], np.ndarray]) -> tuple[Any, dict]:
    """The role index (module docstring); ``embed`` embeds through the cache and charges the usage."""
    from assistant_axis.gapgen import novelty as NV
    st = role_index_settings(cfg)
    roles, texts = role_index_texts(data_dir, st["representation"])
    E = embed(texts)
    idx = NV.build_index(roles, E, variant=st["variant"], settings=st)
    return idx, {"n_roles": len(roles), **st}


def top_lines(ranked: Sequence[Mapping], n: int = TOP_N) -> list[str]:
    """The top ``n`` with their nearest corpus role (what ``rank`` prints)."""
    out = []
    for r in ranked[:n]:
        near = f"{r.get('nearest_role')} {r['cosine']:.2f}" if r.get("cosine") is not None else "-"
        emp = f"{r['employment']:,}" if r.get("employment") is not None else "-"
        status = ""
        if "net_new" in r:
            status = "  net-new" if r["net_new"] else f"  {r.get('excluded') or 'registered ' + str(r.get('registered_as'))}"
        out.append(f"{r['rank']:4d}  {r['role']:<28s} score {r['score']:+.2f}  zipf {r['zipf']:.2f}  emp {emp:>10s}  "
                   f"nearest {near}{'  NEAR' if r.get('near_corpus') else ''}  [{r['group']}]{status}")
    return out


__all__ = ["RANK_WEIGHTS", "FEATURES", "NEAR_CORPUS_COSINE", "QUERY_FORM", "TOP_N", "parse_weights", "ranking_rows",
           "default_zipf", "familiarity", "role_query", "distances", "distance", "zscores", "rank", "rank_roles",
           "role_index_settings", "role_index_texts", "build_role_index", "top_lines"]
