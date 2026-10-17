"""Evaluation figures, no API (plan sections 6 and 10, ``evaluate.py``).

* :func:`string_recovery_per_family`: the corpus's trait stems (or their ``renamed_from``) found among each family's
  stems as strings (``base_model.diversity.string_recovery``); the seed queue's trait entries are counted apart.
* :func:`label_rule_bite` and :func:`zipf_below_share`: what the label rule refused (kept in the table, never
  submitted) and the share of single-word labels below Zipf 3.0 (recorded, never a floor: plan section 1).
* :func:`model_test` (plan section 10): per (family, model) cell, unique stems per dollar (string and semantic), the
  M1 trait share, the **net-new kept share** (kept rows, M3 ``new`` or ``grey``, per submitted net-new row), the
  label rule's bite and the parse rate.  The rule for the rest of (c) reads its net-new kept rows per dollar.
* :func:`verbalized_readout`: (d)'s stage-2 stems that stage 1 of the same prompt (run and model) did not produce, as
  a share of stage 1's unique stems, and their M1 reject rate against stage 1's, with the plan's adoption rule.
* :func:`roles_summary`: rows M1 held on the ``roles`` list, and rows whose generator ``kind`` guess was ``role`` in
  a majority of their readings, counted apart (decision 1: no promotion route here).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

from . import EVALUATION_PATH, GENERATOR
from .calls import model_tag, parse_rate
from .prompts import FAMILIES

#: Plan section 10's (d) rule: adopt when stage 2 adds at least this share of stage 1's unique stems ...
D_ADD_MIN = 0.20
#: ... and its M1 reject rate is at most this multiple of stage 1's.
D_REJECT_RATIO_MAX = 1.5
ZIPF_REPORT_BELOW = 3.0
KEPT_DECISIONS = ("new", "grey")


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def string_recovery_per_family(items: Sequence, *, corpus_stems: Sequence[str], renamed: Mapping[str, str],
                               queue_stems: Sequence[str] = ()) -> dict:
    """Per family: ``{"n_corpus", "found", "recall", "via_renamed_from", "queue_found", "queue_n"}`` (found stems
    left out of the file: they are in the table)."""
    from ..base_model.diversity import string_recovery
    by: dict[str, set] = {}
    for it in items:
        if it.stem:
            by.setdefault(it.family, set()).add(it.stem)
    allst = set().union(*by.values()) if by else set()
    q = set(queue_stems) - set(corpus_stems)
    out = {}
    for f in [x for x in FAMILIES if x in by] + ["all"]:
        st = allst if f == "all" else by[f]
        rec = string_recovery(st, corpus_stems, renamed)
        out[f] = {"n_corpus": rec["n_corpus"], "found": rec["found"], "recall": rec["recall"],
                  "via_renamed_from": len(rec["via_renamed_from"]), "queue_n": len(q), "queue_found": len(st & q)}
    return out


def label_rule_bite(items: Sequence) -> dict:
    """Per family: items, items the label rule refused, by reason, and the share."""
    out = {}
    for f in [x for x in FAMILIES if any(i.family == x for i in items)]:
        its = [i for i in items if i.family == f]
        bad = Counter("over 4 words" if "words" in i.label_problem else i.label_problem for i in its
                      if i.label_problem)
        n_bad = sum(bad.values())
        out[f] = {"n_items": len(its), "n_refused": n_bad, "share": _frac(n_bad, len(its)),
                  "by_reason": dict(sorted(bad.items()))}
    return out


def zipf_below_share(items: Sequence, *, below: float = ZIPF_REPORT_BELOW) -> dict:
    """Per family: the share of distinct single-word stems whose Zipf is below ``below``."""
    out = {}
    for f in [x for x in FAMILIES if any(i.family == x for i in items)]:
        z: dict[str, float] = {}
        for i in items:
            if i.family == f and i.stem and "_" not in i.stem and i.zipf_min is not None:
                z[i.stem] = i.zipf_min
        out[f] = {"n_single_word": len(z), "n_below": sum(1 for v in z.values() if v < below),
                  "share_below": _frac(sum(1 for v in z.values() if v < below), len(z)), "below": below}
    return out


def _cell_of_source(s: Mapping) -> Optional[tuple[str, str]]:
    """``(family, model tag)`` of a registry source of this generator, from its ``source_ref``."""
    from .table import parse_source_ref
    try:
        p = parse_source_ref(s.get("source_ref") or "")
    except ValueError:
        return None
    return p["family"], p["model_tag"]


def run_rows(registry_rows: Mapping[str, Mapping], run_id: str) -> list[Mapping]:
    """Registry rows with a source from this run of the generator, by key."""
    return [r for _, r in sorted(registry_rows.items())
            if any(s.get("generator") == GENERATOR and s.get("run_id") == run_id for s in r.get("sources") or [])]


def _row_cells(row: Mapping, run_id: str) -> set[tuple[str, str]]:
    return {c for s in row.get("sources") or [] if s.get("generator") == GENERATOR and s.get("run_id") == run_id
            for c in [_cell_of_source(s)] if c}


def model_test(items: Sequence, *, registry_rows: Mapping[str, Mapping], run_id: str, records: Sequence[Mapping],
               costs: Mapping[str, float], counted_stems: Sequence[str] = (),
               clusters: Optional[Mapping[str, int]] = None) -> dict:
    """Per (family, model) cell (module docstring).  ``costs``: ``collapse.family_costs(...)["by_family_model"]``
    (``family|model``); ``counted_stems``: the submission's net-new stems (``run.json``); ``clusters``: the semantic
    clusters, for unique per dollar on them."""
    cells: dict[tuple[str, str], list] = {}
    for it in items:
        cells.setdefault((it.family, it.model), []).append(it)
    rows = run_rows(registry_rows, run_id)
    counted = set(counted_stems)
    out = {}
    for (f, m), its in sorted(cells.items(), key=lambda kv: (FAMILIES.index(kv[0][0]) if kv[0][0] in FAMILIES else 9,
                                                              kv[0][1])):
        stems = {i.stem for i in its if i.stem}
        sem = {clusters.get(s, s) for s in stems} if clusters is not None else None
        usd = costs.get(f"{f}|{m}")
        tag = model_tag(m)
        cell_rows = [r for r in rows if (f, tag) in _row_cells(r, run_id)]
        filt = [r for r in cell_rows if r.get("filter")]
        traits = [r for r in filt if r["filter"].get("verdict") == "trait"]
        sub_new = [r for r in cell_rows if r.get("stem") in counted]
        kept_new = [r for r in sub_new if (r.get("novelty") or {}).get("decision") in KEPT_DECISIONS]
        scored_new = [r for r in sub_new if r.get("novelty")]
        bite = sum(1 for i in its if i.label_problem)
        pr = parse_rate([r for r in records if r.get("family") == f and r.get("model") == m
                         and (r.get("step") or "generate") in ("generate", "verbalized")])
        out[f"{f}|{m}"] = {
            "family": f, "model": m, "n_items": len(its), "n_unique_string": len(stems),
            "n_unique_semantic": len(sem) if sem is not None else None, "cost_usd": usd,
            "unique_per_usd_string": round(len(stems) / usd, 1) if usd else None,
            "unique_per_usd_semantic": round(len(sem) / usd, 1) if usd and sem is not None else None,
            "n_submitted_rows": len(cell_rows), "n_filtered": len(filt),
            "m1_trait_share": _frac(len(traits), len(filt)),
            "n_submitted_net_new": len(sub_new), "n_kept_net_new": len(kept_new),
            "net_new_kept_share": _frac(len(kept_new), len(sub_new)) if scored_new else None,
            "net_new_kept_per_usd": round(len(kept_new) / usd, 2) if usd and scored_new else None,
            "label_rule_bite": _frac(bite, len(its)), "parse_rate": pr["rate"]}
    return out


def c_model_rule(cells: Mapping[str, Mapping]) -> dict:
    """The section 10 rule for the rest of (c): the model with the higher net-new kept rows per dollar (Roger's
    gloss read can overrule it: the cheaper model loses if its glosses are wrong more than twice as often)."""
    c = {v["model"]: v for v in cells.values() if v["family"] == "c"}
    scores = {m: v.get("net_new_kept_per_usd") for m, v in c.items()}
    known = {m: s for m, s in scores.items() if s is not None}
    pick = max(known, key=lambda m: known[m]) if len(known) >= 2 else None
    return {"net_new_kept_per_usd": scores, "favoured": pick,
            "note": None if pick else "not decidable yet: needs both (c) arms submitted and scored by M3"}


def verbalized_readout(items: Sequence, *, registry_rows: Optional[Mapping[str, Mapping]] = None) -> dict:
    """(d)'s stage-2 additions (module docstring), per base family (a, e) and overall, with the adoption rule."""
    reg_by_stem: dict[str, Mapping] = {}
    for r in (registry_rows or {}).values():
        if r.get("stem") and int(r.get("sense_id") or 1) == 1:
            reg_by_stem[r["stem"]] = r
    s1: dict[tuple, set] = {}
    s2: dict[tuple, set] = {}
    for it in items:
        if it.family in ("a", "e") and it.stage == 1 and it.meta.get("with_probabilities") and it.stem:
            s1.setdefault((it.prompt_id, it.run, it.model), set()).add(it.stem)
        elif it.family == "d" and it.stem:
            base = it.prompt_id.split(":", 1)[1]
            s2.setdefault((base, it.run, it.model), set()).add(it.stem)
    out = {}
    for fam in ("a", "e", "all"):
        keys = [k for k in s2 if k in s1 and (fam == "all" or k[0].startswith(fam + ":"))]
        st1 = set().union(*[s1[k] for k in keys]) if keys else set()
        added = set().union(*[s2[k] - s1[k] for k in keys]) if keys else set()
        added -= st1

        def reject_rate(stems):
            f = [reg_by_stem[s] for s in stems if s in reg_by_stem and reg_by_stem[s].get("filter")]
            return _frac(sum(1 for r in f if r["filter"].get("verdict") != "trait"), len(f)), len(f)
        r1, n1 = reject_rate(st1)
        r2, n2 = reject_rate(added)
        share = _frac(len(added), len(st1))
        adopt = None
        if share is not None and r1 is not None and r2 is not None:
            adopt = share >= D_ADD_MIN and r2 <= D_REJECT_RATIO_MAX * r1
        out[fam] = {"n_prompts": len(keys), "stage1_unique": len(st1), "stage2_added": len(added),
                    "added_share": share, "m1_reject_stage1": r1, "m1_filtered_stage1": n1,
                    "m1_reject_added": r2, "m1_filtered_added": n2, "adopt_by_rule": adopt,
                    "rule": f"adopt if added share >= {D_ADD_MIN} and reject rate <= {D_REJECT_RATIO_MAX} x stage 1's"}
    return out


def roles_summary(table: Sequence[Mapping], *, registry_rows: Optional[Mapping[str, Mapping]] = None) -> dict:
    """Rows M1 held as ``roles``, rows whose kind guess was ``role`` in most readings, and both."""
    reg = {r.get("stem"): r for r in (registry_rows or {}).values() if int(r.get("sense_id") or 1) == 1}
    held, major = set(), set()
    for row in table:
        st = row["stem"]
        if (reg.get(st) or {}).get("holding") == "roles":
            held.add(st)
        kinds = row.get("kinds") or {}
        if kinds and kinds.get("role", 0) * 2 > sum(kinds.values()):
            major.add(st)
    return {"n_held_roles": len(held), "n_majority_role_kind": len(major), "n_both": len(held & major),
            "n_either": len(held | major)}


def read_evaluation(path: Path = EVALUATION_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) else {}


def write_evaluation(payload: Mapping, path: Path = EVALUATION_PATH, *, inputs: Optional[list] = None
                     ) -> Optional[Path]:
    """Enveloped, unless unchanged; a changed file first copied to ``.bak.<UTC>``."""
    import shutil

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import utc_stamp
    from assistant_axis.plot_metadata import json_metadata
    path = Path(path)
    if path.exists() and read_evaluation(path) == json.loads(json.dumps(payload, default=str)):
        return None
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(json_metadata(dict(payload), inputs=inputs, title="llm_entropy evaluation"),
                                 indent=2, ensure_ascii=False, default=str) + "\n", path)
    return backup


__all__ = ["D_ADD_MIN", "D_REJECT_RATIO_MAX", "string_recovery_per_family", "label_rule_bite", "zipf_below_share",
           "run_rows", "model_test", "c_model_rule", "verbalized_readout", "roles_summary", "read_evaluation",
           "write_evaluation"]
