"""Persona space against M3 (coding_plan_12_persona_space.md § 6; "Inconsistencies", 7).

M3 has no novelty rank (it retrieves by text and judges), so the agreement is read three ways, all on the
**nearest trait** in persona space (M3 compares a candidate with traits only): the AUC of the nearest-trait cosine
for M3's ``covered`` rows against its ``new`` rows (0.5: no agreement; 1: every covered row nearer a trait than
every new one); the Spearman correlation of that cosine with M3's own text cosine (the first listed trait's); and how
often M3's covering trait is persona space's nearest trait, or among its three nearest.

The disagreements (:func:`disagreements`), each kind ranked by its strength and **capped at ``quantile`` (10%) of
the scored rows** (the *disagreement quantile*: the strongest disagreements, not every row that meets the rule):

* ``dup_vs_new``: M3 decided ``new`` and the flag is ``duplicate_like`` (strongest: the highest nearest cosine);
* ``cover_questioned``: M3 decided ``covered`` by X, X has a vector, the predicted vector's cosine to X is below the
  10th percentile of the held-out self-cosines, and X is not among the three nearest traits (strongest: the lowest
  cosine to X);
* ``novel_vs_covered``: M3 decided ``covered`` and ``residual_pct >= 0.9`` (strongest: the highest percentile).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import entity_id, parse_entity_id

from .calibrate import Calibration
from .score import DISAGREEMENTS, m3_view


def auc(pos: Sequence[float], neg: Sequence[float]) -> Optional[float]:
    """The Mann-Whitney AUC: the chance a positive scores above a negative (ties count half)."""
    from scipy.stats import rankdata
    pos, neg = np.asarray(pos, dtype=np.float64), np.asarray(neg, dtype=np.float64)
    if not len(pos) or not len(neg):
        return None
    r = rankdata(np.concatenate([pos, neg]))
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def _spearman(a, b) -> Optional[float]:
    from scipy.stats import spearmanr
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    r = spearmanr(a, b)[0]
    return None if not np.isfinite(r) else float(r)


def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    return None if x is None else round(float(x), nd)


@dataclass
class Agreement:
    n: int
    auc_nn_cos_covered_vs_new: Optional[float]
    spearman_nn_cos_vs_m3_cosine: Optional[float]
    covered_by_is_nearest: Optional[float]
    covered_by_in_top3: Optional[float]
    n_covered_by_with_vector: int = 0
    m3: dict = field(default_factory=dict)
    flags: dict = field(default_factory=dict)
    by_generator: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


def _trait_cos(s: Mapping) -> Optional[float]:
    return (s.get("nn_cos_by_kind") or {}).get("T")


def _current(s: Mapping, rows: Mapping[str, Mapping]) -> dict:
    """M3's reading now (the registry row's), else the one recorded with the score."""
    r = rows.get(s["key"])
    if r is not None:
        return m3_view(r)
    return {"decision": s.get("m3_decision"), "covered_by": s.get("m3_covered_by"),
            "listed_first": s.get("m3_listed_first"), "cosine": s.get("m3_cosine")}


def _cover_cos(s: Mapping, m: Mapping) -> Optional[float]:
    """The predicted vector's cosine to M3's covering trait, when the score recorded it for the same trait."""
    if m.get("covered_by") and s.get("m3_covered_by") == m["covered_by"]:
        return s.get("cos_to_covered_by")
    return None


def _figures(scores: Sequence[Mapping], rows: Mapping[str, Mapping]) -> dict:
    cov, new = [], []
    nn_c, m3_c = [], []
    hit1 = hit3 = n_cov = 0
    m3c: Counter = Counter()
    for s in scores:
        m = _current(s, rows)
        m3c[m["decision"] or "undecided"] += 1
        t = _trait_cos(s)
        if t is None:
            continue
        if m["decision"] == "covered":
            cov.append(t)
        elif m["decision"] == "new":
            new.append(t)
        if m["decision"] and m["cosine"] is not None:
            nn_c.append(t)
            m3_c.append(m["cosine"])
        if m["decision"] == "covered" and m["covered_by"]:
            x = entity_id(m["covered_by"], "traits")
            nt = [a for a, _ in (s.get("nearest_traits") or [])]
            if _cover_cos(s, m) is None and x not in nt:
                continue                                  # the covering trait has no vector (or its cosine is unknown)
            n_cov += 1
            hit1 += int(bool(nt) and nt[0] == x)
            hit3 += int(x in nt[:3])
    return {"auc": auc(cov, new), "rho": _spearman(nn_c, m3_c), "hit1": (hit1 / n_cov) if n_cov else None,
            "hit3": (hit3 / n_cov) if n_cov else None, "n_cov": n_cov, "m3": dict(m3c)}


def agreement(scores: Sequence[Mapping], rows: Mapping[str, Mapping],
              disagreement_rows: Sequence["Disagreement"] = ()) -> Agreement:
    """The agreement of § 6 over ``scores`` (``scores.jsonl`` rows) against M3's decisions in ``rows`` (the
    registry's; a row missing there is read from what the score recorded), overall and by generator."""
    f = _figures(scores, rows)
    flags = Counter(s["flag"] for s in scores)
    dis_by: dict = defaultdict(Counter)
    for d in disagreement_rows:
        for g in d.generators or ["?"]:
            dis_by[g][d.kind] += 1
    by_gen: dict = {}
    gens = sorted({g for s in scores for g in (s.get("generators") or ["?"])})
    for g in gens:
        sub = [s for s in scores if g in (s.get("generators") or ["?"])]
        fg = _figures(sub, rows)
        by_gen[g] = {"n": len(sub), "auc": _r(fg["auc"]), "covered_by_is_nearest": _r(fg["hit1"]),
                     "flags": dict(Counter(s["flag"] for s in sub)), "m3": fg["m3"],
                     "mean_residual_pct": _r(float(np.mean([s["residual_pct"] for s in sub]))),
                     "disagreements": dict(dis_by.get(g, {}))}
    return Agreement(n=len(scores), auc_nn_cos_covered_vs_new=_r(f["auc"]),
                     spearman_nn_cos_vs_m3_cosine=_r(f["rho"]), covered_by_is_nearest=_r(f["hit1"]),
                     covered_by_in_top3=_r(f["hit3"]), n_covered_by_with_vector=f["n_cov"], m3=f["m3"],
                     flags={k: flags.get(k, 0) for k in ("duplicate_like", "novel_like", "ordinary")},
                     by_generator=by_gen)


@dataclass
class Disagreement:
    key: str
    kind: str
    m3_decision: Optional[str]
    covered_by: Optional[str]
    m3_listed_first: Optional[str]
    persona_nearest: str
    nn_cos: float
    residual_pct: float
    evidence: str
    label: str = ""
    generators: list = field(default_factory=list)
    judge_stem: Optional[str] = None       # the persona-nearest trait, the "other" of the overlap call
    judge_cos: Optional[float] = None
    rank: int = 0                          # 1 = the strongest of its kind
    cos_to_covered_by: Optional[float] = None
    m3_cosine: Optional[float] = None

    def as_dict(self) -> dict:
        return asdict(self)


def _stem(eid: Optional[str]) -> Optional[str]:
    return parse_entity_id(eid).name if eid else None


def disagreements(scores: Sequence[Mapping], rows: Mapping[str, Mapping], cal: Calibration, *,
                  quantile: float = 0.10) -> tuple[list[Disagreement], dict]:
    """``(listed disagreements, counts)``: every row meeting a kind's rule, ranked by strength, each kind cut to
    ``floor(quantile * len(scores))``; ``counts``: per kind, how many met the rule and how many were listed."""
    cap = int(np.floor(quantile * len(scores)))
    found: dict[str, list] = {k: [] for k in DISAGREEMENTS}
    for s in scores:
        m = _current(s, rows)
        nt = s.get("nearest_traits") or []
        jt, jc = (_stem(nt[0][0]), nt[0][1]) if nt else (None, None)
        nn = s["nn"]
        base = dict(key=s["key"], m3_decision=m["decision"], covered_by=m["covered_by"],
                    m3_listed_first=m["listed_first"], persona_nearest=nn["id"], nn_cos=nn["cos"],
                    residual_pct=s["residual_pct"], label=s.get("label", ""), generators=list(s.get("generators") or []),
                    judge_stem=jt, judge_cos=jc, cos_to_covered_by=_cover_cos(s, m),
                    m3_cosine=m["cosine"])
        lf = f"M3 listed {m['listed_first']} first at text cosine {m['cosine']:.2f}" \
            if m["listed_first"] and m["cosine"] is not None else "M3 listed no trait"
        if m["decision"] == "new" and s["flag"] == "duplicate_like":
            role = f"; the nearest is a role, the nearest trait {jt} at {jc:.2f}" if nn["id"].endswith("|R") and jt \
                else ""
            ev = f"nn_cos {nn['cos']:.2f} >= dup_threshold {cal.dup_threshold:.2f}{role}; {lf} and decided new"
            found["dup_vs_new"].append((-nn["cos"], s["key"], Disagreement(kind="dup_vs_new", evidence=ev, **base)))
        if m["decision"] == "covered" and m["covered_by"]:
            x = entity_id(m["covered_by"], "traits")
            c = _cover_cos(s, m)
            if c is not None and c < cal.cover_questioned_cos and x not in [a for a, _ in nt[:3]]:
                ev = (f"cosine to M3's covering trait {m['covered_by']} {c:.2f} < {cal.cover_questioned_cos:.2f} (the "
                      f"10th percentile of held-out self-cosines), not among the three nearest traits "
                      f"({', '.join(_stem(a) for a, _ in nt[:3])})")
                found["cover_questioned"].append((c, s["key"], Disagreement(kind="cover_questioned", evidence=ev,
                                                                            **base)))
        if m["decision"] == "covered" and s["residual_pct"] >= cal.novel_vs_covered_pct:
            ev = (f"residual_pct {s['residual_pct']:.2f} >= {cal.novel_vs_covered_pct:.2f} at N = {s['N']}; M3 covered "
                  f"it by {m['covered_by']}")
            found["novel_vs_covered"].append((-s["residual_pct"], s["key"],
                                              Disagreement(kind="novel_vs_covered", evidence=ev, **base)))
    out, counts = [], {}
    for k in DISAGREEMENTS:
        ranked = sorted(found[k], key=lambda t: (t[0], t[1]))
        kept = ranked[:cap]
        for i, (_, _, d) in enumerate(kept, 1):
            d.rank = i
            out.append(d)
        counts[k] = {"met_rule": len(ranked), "listed": len(kept)}
    counts["cap"] = cap
    counts["quantile"] = quantile
    return out, counts


def mark_rows(score_rows: Sequence[dict], dis: Sequence[Disagreement]) -> None:
    """Set each listed row's ``disagreement`` (a row listed under two kinds takes the first in
    :data:`score.DISAGREEMENTS` order)."""
    kind_of: dict[str, str] = {}
    for d in dis:
        if d.key not in kind_of or DISAGREEMENTS.index(d.kind) < DISAGREEMENTS.index(kind_of[d.key]):
            kind_of[d.key] = d.kind
    for r in score_rows:
        r["disagreement"] = kind_of.get(r["key"])


def _link(eid: Optional[str], rel: str) -> str:
    if not eid:
        return "—"
    from assistant_axis.entity_id import corpus_display_name
    e = parse_entity_id(eid)
    try:
        name = corpus_display_name(e.name, e.kind)
    except Exception:  # noqa: BLE001 - display only
        name = e.name.replace("_", " ")
    marker = " (role)" if e.kind == "roles" else ""
    return f"[{name}]({rel}{e.kind}/instructions/{e.name}.json){marker}"


def markdown(dis: Sequence[Disagreement], counts: Mapping, *, batch_id: str, cal: Calibration,
             readings: Optional[Mapping[str, Mapping]] = None, data_rel: str = "../../../../") -> str:
    """``disagreements.md`` for Roger: per kind, the listed rows with both readings' evidence (and, under decision
    2b, the overlap call's reading).  Links are relative to ``data/candidates/persona/score/<batch>/``."""
    readings = readings or {}
    lines = [f"# Persona space against M3: disagreements, batch `{batch_id}`", "",
             f"Each kind is ranked by its strength and cut to {counts.get('cap')} rows ({counts.get('quantile'):.0%} "
             f"of the scored rows).  Thresholds: `dup_threshold` {cal.dup_threshold:.2f}, `novel_pct` "
             f"{cal.novel_pct:.2f}, cover-questioned cosine {cal.cover_questioned_cos:.2f}, novel-vs-covered "
             f"percentile {cal.novel_vs_covered_pct:.2f} (set by: {cal.thresholds_set_by}).  Persona space reads a "
             f"*predicted* vector; M3 reads the text.  Neither decides here: M3's decision is unchanged.", ""]
    titles = {"dup_vs_new": "M3 new, persona space duplicate-like",
              "cover_questioned": "M3 covered, persona space far from the covering trait",
              "novel_vs_covered": "M3 covered, persona space novel-like"}
    for k in DISAGREEMENTS:
        rows = [d for d in dis if d.kind == k]
        c = counts.get(k, {})
        lines += [f"## {titles[k]} (`{k}`): {c.get('listed', 0)} listed of {c.get('met_rule', 0)}", ""]
        if not rows:
            lines += ["None.", ""]
            continue
        head = "| # | candidate | generators | M3 | persona nearest | nn cos | residual pct | evidence |"
        if k == "dup_vs_new":
            head += " overlap reading |"
        lines += [head, "|" + "---|" * (head.count("|") - 1)]
        for d in rows:
            m3 = d.m3_decision or "undecided"
            if d.covered_by:
                m3 += f" by {_link(entity_id(d.covered_by, 'traits'), data_rel)}"
            elif d.m3_listed_first:
                m3 += f", first listed {_link(entity_id(d.m3_listed_first, 'traits'), data_rel)}"
            line = (f"| {d.rank} | {d.label} (`{d.key}`) | {', '.join(d.generators)} | {m3} | "
                    f"{_link(d.persona_nearest, data_rel)} | {d.nn_cos:.2f} | {d.residual_pct:.2f} | "
                    f"{d.evidence.replace('|', '/')} |")
            if k == "dup_vs_new":
                r = readings.get(d.key)
                line += (f" {r.get('stem')}: Sonnet {r.get('sonnet')}, Opus {r.get('opus')}, {r.get('verdict')}"
                         f"{' (at the cut-off)' if r.get('at_cut_off') else ''} |" if r else " not read |")
            lines.append(line)
        lines.append("")
    return "\n".join(lines)
