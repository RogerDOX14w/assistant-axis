"""The free checks (plan section 8; tasks 5-7 and 10): recovery, the queue hold-out, null rates, stability, parse rate.

All are report-and-decide (plan 09 section 6 sets no gate but "expect > 80%" for pair recovery), except the parse
rate, the null-rate band and stability, which the acceptance test reads as hard.

* :func:`pair_recovery`: each recorded clean pair's poles in turn; the blind ``opposite`` of one pole recovers the
  other by stem (the folded stem, the other's bare label without a standard's suffix, or a ``renamed_from``), or by
  gloss cosine (``label: gloss`` against ``label: description``) at 0.7, 0.8 and 0.9.
* :func:`structure_recovery`: each corner of the 8 triangles and each member of the sequences (the moral-circle one
  has 13 members on 2026-10-12, not plan 09's 16), recovered by stem from any answer of its neighbours (the other
  two corners; the members either side in the sequence).
* :func:`queue_holdout` (decision 2, Roger 2026-10-13): three lines, all by stem: recall on the 96 queued-but-unfiled
  labels (84 ``backlog`` entries and 12 ``paired`` entries whose stem has no file; the denominator), by operator;
  how many of the ``not_adopted`` names that have no file B regenerates (139); recall on the 41 registry rows Roger
  accepted in review, beside the 38 queue ``candidate`` entries, never in the denominator.  The four lists are
  frozen when the pilot starts (:func:`freeze_holdout`) and written into ``evaluation.json``.
* :func:`null_rates`: per operator, target and mode, the share of answers that are not null; the principal targets
  apart, over the traits that were asked them; the 5-40% band for retarget and remode (the pilot's gate).
* :func:`stability_jaccard`: per trait, the label-set Jaccard (intersection over union of the stems of all
  answers) of two runs; median, distribution, count below 0.5, per operator.
* :func:`parse_rate`: answered calls over calls attempted (after the one retry), and records that parse over records.
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.registry import utc_now, utc_stamp

from . import EVALUATION_PATH
from .operators import (MODES, PRINCIPAL_TARGETS, SINGLE_OPERATORS, TARGETS, OperatorReply, reply_from_record)
from .postprocess import Corpus, stem_of

COSINE_THRESHOLDS: tuple[float, ...] = (0.7, 0.8, 0.9)
NULL_BAND: tuple[float, float] = (0.05, 0.40)
PAIR_RECOVERY_EXPECTED = 0.8
STABILITY_MIN_MEDIAN = 0.5
PARSE_RATE_MIN = 0.99
_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _stem(label: Optional[str], lexicon=None) -> Optional[str]:
    if not label:
        return None
    try:
        return stem_of(label, lexicon=lexicon)[0]
    except ValueError:
        return None


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def produced_stems(rep: OperatorReply, *, lexicon=None, operators: Optional[Iterable[str]] = None) -> set[str]:
    """Stems of every answer of a reply (only ``operators`` when given)."""
    want = set(operators) if operators is not None else None
    out = set()
    for op, _sub, it in rep.items():
        if want is None or op in want:
            s = _stem(it["label"], lexicon)
            if s:
                out.add(s)
    return out


def target_stems(stem: str, corpus: Corpus, *, lexicon=None) -> set[str]:
    """What counts as reaching a corpus trait: its stem, its bare label's stem (a standard's suffix dropped) and
    every old stem it was renamed from."""
    out = {stem}
    lab = corpus.labels.get(stem)
    if lab:
        s = _stem(_SUFFIX_RE.sub("", lab), lexicon)
        if s:
            out.add(s)
    out.update(old for old, new in corpus.renamed.items() if new == stem)
    return out


# --------------------------------------------------------------------------- recovery

def pair_recovery(replies: Mapping[str, OperatorReply], pairs: Sequence[tuple[str, str]], *, corpus: Corpus,
                  lexicon=None, embed: Optional[Callable[[Sequence[str]], "object"]] = None,
                  thresholds: Sequence[float] = COSINE_THRESHOLDS) -> dict:
    """Recall of each recorded pair's other pole from one pole's blind opposite (module docstring).  ``embed(texts)``
    returns unit rows (an embedder through its cache in the CLI, ``HashEmbedder`` in tests); without it only the stem
    figures are given."""
    dirs = []
    for a, b in pairs:
        dirs += [(a, b), (b, a)]
    answered = [(x, y) for x, y in dirs if x in replies and not replies[x].principal_only]
    hits_stem, misses, texts = [], [], []
    for x, y in answered:
        opp = replies[x].opposite
        ok = bool(opp) and _stem(opp["label"], lexicon) in target_stems(y, corpus, lexicon=lexicon)
        hits_stem.append(ok)
        if opp:
            texts.append((f"{opp['label']}: {opp.get('gloss') or ''}",
                          f"{corpus.labels.get(y, y)}: {corpus.descriptions.get(y, '')}"))
        else:
            texts.append(None)
    out = {"n_pairs": len(pairs), "n_directions": len(dirs), "n_answered": len(answered),
           "n_null_opposite": sum(1 for t in texts if t is None),
           "recall_stem": _frac(sum(hits_stem), len(answered)), "expected": PAIR_RECOVERY_EXPECTED}
    by_pair: dict[tuple, list] = {}
    for (x, y), ok in zip(answered, hits_stem):
        by_pair.setdefault(tuple(sorted((x, y))), []).append(ok)
    out["pairs_both_directions_stem"] = sum(1 for v in by_pair.values() if len(v) == 2 and all(v))
    out["pairs_either_direction_stem"] = sum(1 for v in by_pair.values() if any(v))
    cos = [None] * len(answered)
    if embed is not None and answered:
        import numpy as np
        idx = [i for i, t in enumerate(texts) if t is not None]
        if idx:
            A = np.asarray(embed([texts[i][0] for i in idx]))
            B = np.asarray(embed([texts[i][1] for i in idx]))
            for j, i in enumerate(idx):
                cos[i] = float(np.dot(A[j], B[j]))
        for t in thresholds:
            rec = sum(1 for ok, c in zip(hits_stem, cos) if ok or (c is not None and c >= t))
            out[f"recall_cos_{t}"] = _frac(rec, len(answered))
        vals = [c for c in cos if c is not None]
        out["cosine_median"] = round(statistics.median(vals), 4) if vals else None
    for (x, y), ok, c in zip(answered, hits_stem, cos):
        if not ok:
            opp = replies[x].opposite
            misses.append({"from": x, "hidden": y, "opposite": opp["label"] if opp else None,
                           "cosine": None if c is None else round(c, 4)})
    out["misses"] = misses
    return out


def structure_recovery(replies: Mapping[str, OperatorReply], triangles: Sequence[Sequence[str]],
                       sequences: Sequence[Sequence[str]], *, corpus: Corpus, lexicon=None) -> dict:
    """Triangle corners and sequence members recovered from their neighbours' answers (module docstring)."""
    prod = {s: produced_stems(r, lexicon=lexicon) for s, r in replies.items()}
    tri_detail, n_rec, n_tri = [], 0, 0
    for tri in triangles:
        got = []
        for c in tri:
            others = [o for o in tri if o != c]
            reach = set().union(*(prod.get(o, set()) for o in others))
            ok = bool(target_stems(c, corpus, lexicon=lexicon) & reach)
            got.append(ok)
            if ok:
                tri_detail.append({"triangle": list(tri), "corner": c})
        n_rec += sum(got)
        n_tri += any(got)
    seqs = []
    for seq in sequences:
        rec = []
        for i, m in enumerate(seq):
            nb = [seq[j] for j in (i - 1, i + 1) if 0 <= j < len(seq)]
            reach = set().union(*(prod.get(o, set()) for o in nb))
            if target_stems(m, corpus, lexicon=lexicon) & reach:
                rec.append(m)
        seqs.append({"members": list(seq), "n": len(seq), "recovered": len(rec), "which": rec})
    longest = max(seqs, key=lambda s: s["n"]) if seqs else None
    return {"triangles": {"n": len(triangles), "corners": sum(len(t) for t in triangles), "corners_recovered": n_rec,
                          "triangles_with_a_corner": n_tri, "detail": tri_detail},
            "sequence": {"n": longest["n"], "recovered": longest["recovered"], "which": longest["which"],
                         "first_member": longest["members"][0]} if longest else None,
            "sequences": seqs}


# --------------------------------------------------------------------------- the queue hold-out

def freeze_holdout(*, queue_path: Path, registry_rows: Mapping[str, Mapping], corpus_stems: Iterable[str],
                   now: Optional[str] = None) -> dict:
    """The four stem lists of decision 2, frozen (module docstring): ``holdout`` (``backlog`` trait entries and
    ``paired`` ones whose stem has no file), ``rejected`` (distinct ``not_adopted`` stems with no file),
    ``accepted`` (registry rows whose review status is ``accepted``), ``candidates`` (``candidate`` trait
    entries)."""
    q = json.loads(Path(queue_path).read_text(encoding="utf-8"))
    entries = [e for e in (q.get("entries") if isinstance(q, dict) else q) or []
               if e.get("entity_type") in (None, "trait")]
    files = set(corpus_stems)

    def ent(e):
        return {"stem": e["stem"], "label": e.get("label"), "status": e.get("status")}
    hold = [ent(e) for e in entries if e.get("stem") and (e.get("status") == "backlog" or (
        e.get("status") == "paired" and e["stem"] not in files))]
    rej = sorted({e["stem"] for e in entries if e.get("status") == "not_adopted" and e.get("stem")
                  and e["stem"] not in files})
    cands = [ent(e) for e in entries if e.get("status") == "candidate" and e.get("stem")]
    acc = sorted({r["stem"] for r in registry_rows.values() if (r.get("review") or {}).get("status") == "accepted"
                  and r.get("stem")})
    return {"frozen_at": now or utc_now(), "queue_sha256": _sha_file(queue_path),
            "holdout": hold, "rejected": rej, "accepted": acc, "candidates": cands,
            "counts": {"holdout": len(hold), "rejected": len(rej), "accepted": len(acc), "candidates": len(cands)}}


def _sha_file(p: Path) -> str:
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _match_set(e) -> set[str]:
    if isinstance(e, str):
        return {e}
    out = {e["stem"]}
    if e.get("label"):
        out.add(normalize_to_file_name(e["label"]))
    return out


def _recall(items: Sequence, produced: set[str]) -> tuple[list, Optional[float]]:
    hit = [(e if isinstance(e, str) else e["stem"]) for e in items if _match_set(e) & produced]
    return hit, _frac(len(hit), len(items))


def queue_holdout(replies: Iterable[OperatorReply], holdout: Sequence, *, rejected: Sequence = (),
                  accepted: Sequence = (), candidates: Sequence = (), lexicon=None) -> dict:
    """The hold-out's three lines (module docstring), by stem, from the operator answers only."""
    reps = list(replies)
    by_op: dict[str, set] = {op: set() for op in ("opposite", "excess", "deficiency", "retarget", "remode")}
    for r in reps:
        for op, _sub, it in r.items():
            s = _stem(it["label"], lexicon)
            if s:
                by_op[op].add(s)
    allp = set().union(*by_op.values())
    hit, rec = _recall(holdout, allp)
    out = {"n": len(holdout), "recall_stem": rec, "recovered": hit,
           "by_operator": {op: _recall(holdout, s)[1] for op, s in by_op.items()},
           "by_operator_n": {op: len(_recall(holdout, s)[0]) for op, s in by_op.items()}}
    rhit, _ = _recall(rejected, allp)
    out["rejected"] = {"n": len(rejected), "regenerated": len(rhit), "stems": rhit}
    for name, items in (("accepted", accepted), ("candidates", candidates)):
        h, r = _recall(items, allp)
        out[name] = {"n": len(items), "recall_stem": r, "stems": h}
    return out


# --------------------------------------------------------------------------- null rates, positions, stability

def null_rates(replies: Iterable[OperatorReply], *, band: tuple[float, float] = NULL_BAND) -> dict:
    """Non-null shares per operator, target and mode (module docstring)."""
    reps = list(replies)
    full = [r for r in reps if not r.principal_only]
    n = len(full)
    out: dict = {"n_traits": n}
    for op in SINGLE_OPERATORS:
        out[op] = _frac(sum(1 for r in full if getattr(r, op)), n)
    out["retarget_by_target"] = {t: _frac(sum(1 for r in full if r.retarget.get(t)), n) for t in TARGETS}
    out["retarget"] = _frac(sum(1 for r in full for t in TARGETS if r.retarget.get(t)), n * len(TARGETS))
    out["remode_by_mode"] = {m: _frac(sum(1 for r in full if r.remode.get(m)), n) for m in MODES}
    out["remode"] = _frac(sum(1 for r in full for m in MODES if r.remode.get(m)), n * len(MODES))
    pr = [r for r in reps if r.principal]
    out["principal"] = {"n_traits": len(pr), "by_target": {t: _frac(sum(1 for r in pr if r.retarget.get(t)), len(pr))
                                                           for t in PRINCIPAL_TARGETS},
                        "share": _frac(sum(1 for r in pr for t in PRINCIPAL_TARGETS if r.retarget.get(t)),
                                       len(pr) * len(PRINCIPAL_TARGETS)),
                        "n_items": sum(1 for r in pr for t in PRINCIPAL_TARGETS if r.retarget.get(t))}
    lo, hi = band
    out["band"] = {"low": lo, "high": hi,
                   "retarget_in_band": out["retarget"] is not None and lo <= out["retarget"] <= hi,
                   "remode_in_band": out["remode"] is not None and lo <= out["remode"] <= hi}
    out["band"]["pass"] = out["band"]["retarget_in_band"] and out["band"]["remode_in_band"]
    out["positions"] = dict(sorted(Counter(str(r.position) for r in full).items()))
    return out


def pair_positions(replies: Mapping[str, OperatorReply], pairs: Sequence[tuple[str, str]]) -> dict:
    """Where the two poles of each answered pair land (``deficiency/excess``, ``mean/excess``, ...)."""
    rows, combos = [], Counter()
    for a, b in pairs:
        ra, rb = replies.get(a), replies.get(b)
        if ra is None or rb is None or ra.principal_only or rb.principal_only:
            continue
        combo = "/".join(sorted((str(ra.position), str(rb.position))))
        combos[combo] += 1
        rows.append({"pair": [a, b], "positions": [ra.position, rb.position]})
    return {"n_pairs": len(rows), "combinations": dict(sorted(combos.items())), "pairs": rows}


def _jaccard(a: set, b: set) -> float:
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def stability_jaccard(run_a: Mapping[str, OperatorReply], run_b: Mapping[str, OperatorReply], *,
                      lexicon=None) -> dict:
    """Per trait answered in both runs: the Jaccard of the stems of all answers; the median, a 0.1-bin distribution,
    the count below 0.5, and the median per operator."""
    common = sorted(s for s in set(run_a) & set(run_b)
                    if not run_a[s].principal_only and not run_b[s].principal_only)
    per = {s: round(_jaccard(produced_stems(run_a[s], lexicon=lexicon), produced_stems(run_b[s], lexicon=lexicon)), 4)
           for s in common}
    by_op = {}
    for op in ("opposite", "excess", "deficiency", "retarget", "remode"):
        vals = [_jaccard(produced_stems(run_a[s], lexicon=lexicon, operators=[op]),
                         produced_stems(run_b[s], lexicon=lexicon, operators=[op])) for s in common]
        by_op[op] = round(statistics.median(vals), 4) if vals else None
    vals = list(per.values())
    bins = Counter(min(9, int(v * 10)) for v in vals)
    return {"n_traits": len(common), "jaccard_median": round(statistics.median(vals), 4) if vals else None,
            "below_0.5": sum(1 for v in vals if v < 0.5), "min_median": STABILITY_MIN_MEDIAN,
            "distribution": {f"{b / 10:.1f}-{(b + 1) / 10:.1f}": bins.get(b, 0) for b in range(10)},
            "by_operator": by_op, "per_trait": per}


def parse_rate(records: Sequence[Mapping]) -> dict:
    """Answered calls over calls attempted (the retry counted once per trait) and parsed records over records."""
    units: dict[str, bool] = {}
    n_rec_ok = 0
    for r in records:
        rep, _ = reply_from_record(r)
        ok = rep is not None
        n_rec_ok += ok
        u = r.get("stem") or r.get("unit_id")
        units[u] = units.get(u, False) or ok
    n_ok = sum(units.values())
    return {"n_units": len(units), "n_ok": n_ok, "rate": _frac(n_ok, len(units)), "n_records": len(records),
            "n_records_ok": n_rec_ok, "record_rate": _frac(n_rec_ok, len(records)), "min_rate": PARSE_RATE_MIN}


# --------------------------------------------------------------------------- the file

def read_evaluation(path: Path = EVALUATION_PATH) -> dict:
    """``evaluation.json``'s payload (the envelope read through); empty when absent."""
    p = Path(path)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) else {}


def write_evaluation(payload: Mapping, path: Path = EVALUATION_PATH, *, inputs: Optional[list] = None,
                     title: str = "structural evaluation") -> Optional[Path]:
    """Write the enveloped payload unless it is unchanged (then nothing is written, so a rerun leaves the file
    byte-identical); a changed file is first copied to ``.bak.<UTC>``.  Returns the backup, if any."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.plot_metadata import json_metadata
    path = Path(path)
    if path.exists() and read_evaluation(path) == json.loads(json.dumps(payload)):
        return None
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    env = json_metadata(dict(payload), inputs=inputs, title=title)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False, default=str) + "\n", path)
    return backup


__all__ = ["COSINE_THRESHOLDS", "NULL_BAND", "PAIR_RECOVERY_EXPECTED", "STABILITY_MIN_MEDIAN", "PARSE_RATE_MIN",
           "produced_stems", "target_stems", "pair_recovery", "structure_recovery", "freeze_holdout",
           "queue_holdout", "null_rates", "pair_positions", "stability_jaccard", "parse_rate", "read_evaluation",
           "write_evaluation"]
