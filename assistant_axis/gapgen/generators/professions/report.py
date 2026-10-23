"""B's readout (coding plan 16, § 5b, § 7 ``report`` and § 11): ``report.md`` in the run directory.

* **Sources**: the manifest rows of the files the build read (``build.json``), each with its licence and whether
  the licence page named it, and a link to the run's ``ATTRIBUTION.md``.
* **The table**: the broad groups (459 expected), where their titles and employment came from, and the job-title
  cut (dropped by reason, passed, kept).
* **Recovery by string** (:func:`recovery_by_string`; the idea plan's test of B: hide the 162 corpus occupations,
  recovery at the broad level should pass 80%, and the misses say which level the corpus sits at): the corpus's
  occupation roles (``data/roles/role_kinds.json``, kind ``occupation``) and their ``renamed_from`` stems, found by
  exact stem among (a) the source titles at build time (each O*NET title and each of its "X and Y" / "X, Y" parts,
  lower case, last word singular) and (b) the lay roles, at the broad level (the broad groups' roles) and with the
  job titles' added.  A corpus stem that is a word of a longer lay role (doctor in family doctor) is listed as
  ``partial``, information only.
* **The lay call**: groups answered and failed, the parse rate of the recorded responses, agreement across the
  readings (a diagnostic, never a gate), the spend.
* **The ranking**: weights, the top 40 with their nearest corpus role, how many are ``near_corpus``.
* **The submission**: the wave's arithmetic, net-new / registered / excluded, the label-fit corrections, and the
  occupation share before and after at the held share (``roles_pass.balance``).

Every file the report names is a link relative to the report (the hotlink rule), a corpus role's file included.
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.paths import DATA_DIR

from . import (ATTRIBUTION_NAME, BUILD_NAME, CANDIDATES_NAME, GENERATOR, LAY_NAME, LAY_RESPONSES_NAME, RANKING_NAME,
               REPORT_NAME, SUBMIT_REPORT_NAME, TABLE_NAME)
from .onet import lay_label, title_stem

RECOVERY_TARGET = 0.80


# --------------------------------------------------------------------------- recovery by string

def corpus_occupations(data_dir: Path = DATA_DIR) -> dict[str, list[str]]:
    """``{stem: [renamed_from stems]}`` of the corpus roles whose recorded kind is ``occupation``
    (``roles/role_kinds.json``) and whose file exists."""
    data_dir = Path(data_dir)
    kp = data_dir / "roles" / "role_kinds.json"
    kinds = (json.loads(kp.read_text(encoding="utf-8")).get("roles") or {}) if kp.exists() else {}
    out: dict[str, list[str]] = {}
    for stem, rec in sorted(kinds.items()):
        if (rec or {}).get("kind") != "occupation":
            continue
        p = data_dir / "roles" / "instructions" / f"{stem}.json"
        if not p.exists():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = {}
        rf = doc.get("renamed_from")
        olds = []
        for item in rf if isinstance(rf, list) else ([rf] if rf else []):
            o = item.get("stem") if isinstance(item, Mapping) else item
            if isinstance(o, str) and o:
                olds.append(o)
        out[stem] = olds
    return out


def _stem_of(x) -> Optional[str]:
    if isinstance(x, Mapping):
        if x.get("stem"):
            return x["stem"]
        x = x.get("role")
    if not isinstance(x, str) or not x.strip():
        return None
    try:
        return title_stem(x.strip().lower())
    except Exception:  # noqa: BLE001 - not a usable string
        return None


def recovery_by_string(lay_roles: Iterable, *, occupation_stems: Mapping[str, Sequence[str]] | Iterable[str]) -> dict:
    """``{"n", "n_recovered", "share", "recovered": {stem: via}, "missed", "partial": {stem: [lay stems]}}``:
    each corpus occupation (with its ``renamed_from`` stems, when ``occupation_stems`` maps them) found by exact
    stem among ``lay_roles`` (stems, role strings, or rows with ``stem`` / ``role``)."""
    occ = occupation_stems if isinstance(occupation_stems, Mapping) else {s: [] for s in occupation_stems}
    lay = {s for s in (_stem_of(x) for x in lay_roles) if s}
    words: dict[str, list[str]] = {}
    for s in lay:
        for w in s.split("_"):
            words.setdefault(w, []).append(s)
    rec, missed, partial = {}, [], {}
    for stem in sorted(occ):
        if stem in lay:
            rec[stem] = stem
            continue
        old = next((o for o in occ[stem] if o in lay), None)
        if old:
            rec[stem] = f"renamed_from:{old}"
            continue
        missed.append(stem)
        if "_" not in stem and stem in words:
            partial[stem] = sorted(x for x in words[stem] if x != stem)[:5]
    n = len(occ)
    return {"n": n, "n_recovered": len(rec), "share": round(len(rec) / n, 4) if n else None, "recovered": rec,
            "missed": missed, "partial": partial}


_SPLIT_RE = re.compile(r"[,;]\s*|\s+and\s+|\s+or\s+|\s*/\s*")


def title_strings(title: str) -> set[str]:
    """The stems a classification title offers for recovery by string: the whole title and each of its parts split
    at commas, "and" and slashes, lower case, last word singular ("Obstetricians and Gynecologists" -> obstetrician,
    gynecologist, obstetricians_and_gynecologist)."""
    out = set()
    for part in [title] + [p for p in _SPLIT_RE.split(title) if p]:
        p = part.strip()
        if not p or "(" in p:
            continue
        try:
            out.add(title_stem(lay_label(p)[0]))
        except Exception:  # noqa: BLE001
            continue
    return {s for s in out if s}


def table_title_stems(table: Sequence[Mapping]) -> set[str]:
    """Every source title's :func:`title_strings` over ``table.jsonl`` (the broad groups' titles and their O*NET
    occupations; the selected job titles' labels)."""
    out: set[str] = set()
    for r in table:
        if r.get("kind") == "broad":
            out |= title_strings(r.get("title") or "")
            for d in r.get("detailed") or []:
                out |= title_strings(d.get("title") or "")
        elif r.get("kind") == "job_title":
            out.add(r.get("stem") or title_stem(r.get("label") or r["title"].lower()))
    return out


def lay_recovery(lay_rows: Sequence[Mapping], occupation_stems: Mapping[str, Sequence[str]]) -> dict:
    """Recovery at the broad level (the broad groups' lay roles) and with the job titles' roles added."""
    broad = [r for g in lay_rows if g.get("kind") == "broad" for r in g.get("roles") or []]
    every = [r for g in lay_rows for r in g.get("roles") or []]
    return {"broad": recovery_by_string(broad, occupation_stems=occupation_stems),
            "all": recovery_by_string(every, occupation_stems=occupation_stems)}


# --------------------------------------------------------------------------- kept by the kind call

SHARE_FLAG = 0.05


def kept_balance(keys: Sequence[str], registry_rows: Mapping[str, Mapping], *, data_dir: Path = DATA_DIR,
                 queue: Optional[Mapping] = None) -> Optional[dict]:
    """The frozen interface's readout after M3 (coding plan 16, "Frozen interface": before, submitted by
    ``kind_guess``, kept by the kind call, after): the run's rows M3 kept (``novelty.decision`` new or grey), by the
    role kind call's kind (``roles_pass.kind_of``), added to the corpus; a kind whose share moves more than
    :data:`SHARE_FLAG` is flagged, never cut.  None while no row of the run has an M3 decision."""
    from assistant_axis.gapgen import roles_pass as RP
    rows = [registry_rows[k] for k in keys if k in registry_rows]
    decided = [r for r in rows if (r.get("novelty") or {}).get("decision")]
    if not decided:
        return None
    kept = [r for r in decided if r["novelty"]["decision"] in ("new", "grey")]
    by = Counter(RP.kind_of(r) or "unknown" for r in kept)
    if queue is None:
        import data_analysis.seed_entities as se
        queue = se.load_queue(Path(data_dir) / "seed_queue.json")
    counts, n_now = RP.corpus_kind_counts(Path(data_dir), queue)
    after_counts = dict(counts)
    for k, v in by.items():
        after_counts[k] = after_counts.get(k, 0) + v
    n_after = n_now + len(kept)
    before, after = RP.balance(counts, n_now), RP.balance(after_counts, n_after)
    moved = {k: round(after_counts.get(k, 0) / n_after - counts.get(k, 0) / n_now, 4) for k in RP.KIND_KEYS}
    return {"n_rows": len(rows), "n_decided": len(decided), "n_kept": len(kept), "kept_by_kind": dict(by),
            "before": before, "after": after, "share_moved": moved,
            "flagged": sorted(k for k, v in moved.items() if abs(v) > SHARE_FLAG)}


# --------------------------------------------------------------------------- reading a run

def _jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def _json(path: Path) -> Optional[dict]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _link(target: Path, doc_dir: Path, text: Optional[str] = None, *, missing_note: bool = True) -> str:
    rel = os.path.relpath(Path(target), Path(doc_dir))
    if not rel.startswith("."):
        rel = "./" + rel
    t = text or Path(target).name
    note = " (not there yet)" if missing_note and not Path(target).exists() else ""
    return f"[{t}]({rel}){note}"


def _role_link(stem: Optional[str], doc_dir: Path, data_dir: Path) -> str:
    if not stem:
        return "-"
    p = Path(data_dir) / "roles" / "instructions" / f"{stem}.json"
    return _link(p, doc_dir, stem, missing_note=False) if p.exists() else stem


def _md(x) -> str:
    return str(x if x is not None else "-").replace("|", "\\|")


def report_markdown(run_dir: Path, *, data_dir: Path = DATA_DIR, top: int = 40,
                    registry_path: Optional[Path] = None) -> str:
    """``report.md`` for the run in ``run_dir`` (module docstring); with ``registry_path``, the rows M3 kept by the
    kind call too (:func:`kept_balance`)."""
    from assistant_axis.gapgen.generators.llm_entropy.calls import parse_rate
    rd = Path(run_dir)
    run_id = rd.name
    build = _json(rd / BUILD_NAME) or {}
    table = _jsonl(rd / TABLE_NAME)
    lay_rows = _jsonl(rd / LAY_NAME)
    ranking = _jsonl(rd / RANKING_NAME)
    sub = _json(rd / SUBMIT_REPORT_NAME)
    usage = _json(rd / "usage.json") or {}
    occ = corpus_occupations(data_dir)
    L = [f"# Generator B (lists of professions): run {run_id}", ""]
    L += [f"Generator `{GENERATOR}`, run directory files: " + ", ".join(
        _link(rd / n, rd) for n in (TABLE_NAME, BUILD_NAME, LAY_RESPONSES_NAME, LAY_NAME, RANKING_NAME, CANDIDATES_NAME,
                                    SUBMIT_REPORT_NAME, ATTRIBUTION_NAME, "run.json", "usage.json")) + ".", ""]

    L += ["## Sources", ""]
    srcs = build.get("sources") or []
    if srcs:
        L += ["| key | file | licence | licence named on its page | downloaded by | sha256 | note |",
              "|---|---|---|---|---|---|---|"]
        for s in srcs:
            by = s.get("downloaded_by") or ("fetch" if s.get("tool") else None)
            L.append(f"| {_md(s.get('key'))} | {_md(s.get('file'))} | {_md(s.get('licence'))} | "
                     f"{_md(s.get('licence_verified'))} | {_md(by)} | {_md((s.get('sha256') or '')[:12])} | "
                     f"{_md(s.get('note_build'))} |")
        L.append("")
    else:
        L += ["(no build record yet)", ""]
    L += [f"Attribution: {_link(rd / ATTRIBUTION_NAME, rd)} (the O*NET paragraph verbatim; it travels with every "
          f"artefact that holds a title).", ""]

    L += ["## The table", ""]
    n_broad = sum(1 for r in table if r.get("kind") == "broad")
    n_titles = sum(1 for r in table if r.get("kind") == "job_title")
    n_esco = sum(1 for r in table if r.get("kind") == "esco_group")
    L.append(f"{n_broad} SOC broad groups (459 expected), {n_titles} job titles, {n_esco} ESCO groups.")
    if table:
        ts = Counter(r.get("title_source") for r in table if r.get("kind") == "broad")
        es = Counter(r.get("employment_source") for r in table if r.get("kind") == "broad")
        L.append(f"Broad titles from: {dict(ts)}; employment from: {dict(es)}.")
    cut = build.get("cut")
    if cut:
        L += ["", f"The job-title cut ({cut['n_titles']:,} titles; 1-{cut['max_words']} words, Zipf >= "
                  f"{cut['min_zipf']}, top {cut['n']}):", "", "| step | dropped | e.g. |", "|---|---|---|"]
        for k, v in cut["dropped"].items():
            L.append(f"| {k} | {v:,} | {_md(', '.join(cut.get('examples', {}).get(k, [])[:3]))} |")
        L += ["", f"Passed {cut['n_passed']:,}; kept {cut['n_kept']} (the top by Zipf)."]
    L.append("")

    L += ["## Recovery by string of the corpus occupations", ""]
    L.append(f"{len(occ)} corpus roles of kind occupation ({_link(Path(data_dir) / 'roles' / 'role_kinds.json', rd)}), "
             f"with their `renamed_from` stems; target above {RECOVERY_TARGET:.0%} at the broad level.")
    L.append("")
    blocks = []
    if table:
        blocks.append(("source titles (build)", recovery_by_string(table_title_stems(table), occupation_stems=occ)))
    if lay_rows:
        lr = lay_recovery(lay_rows, occ)
        blocks += [("lay roles, broad level", lr["broad"]), ("lay roles, broad level and job titles", lr["all"])]
    if blocks:
        L += ["| among | recovered | share |", "|---|---|---|"]
        for name, b in blocks:
            L.append(f"| {name} | {b['n_recovered']} of {b['n']} | {b['share']:.1%} |" if b["share"] is not None
                     else f"| {name} | 0 of 0 | - |")
        last = blocks[-1][1]
        L += ["", f"Missed ({blocks[-1][0]}): " + (", ".join(_role_link(s, rd, data_dir) for s in last["missed"])
                                                    or "none") + "."]
        if last["partial"]:
            L += ["", "A word of a longer lay role (information only): " + "; ".join(
                f"{_role_link(s, rd, data_dir)} in {', '.join(v)}" for s, v in sorted(last["partial"].items())) + "."]
    else:
        L.append("(no table yet)")
    L.append("")

    L += ["## The lay call", ""]
    if lay_rows:
        from .lay import agreement
        recs = _jsonl(rd / LAY_RESPONSES_NAME)
        pr = parse_rate(recs, step="lay")
        ag = agreement(lay_rows)
        failed = sum(1 for g in lay_rows if g.get("failed"))
        n_roles = sum(len(g.get("roles") or []) for g in lay_rows)
        L += [f"{len(lay_rows)} groups and titles asked, {failed} with no usable reading; {n_roles} lay roles "
              f"before the merge by stem.",
              f"Parse rate (units answered over units asked): {pr['n_ok']} of {pr['n_units']}"
              + (f" ({pr['rate']:.1%})" if pr["rate"] is not None else "") + f"; failures {pr['failures']}.",
              f"Agreement across readings (diagnostic, never a gate): {json.dumps(ag)}.", ""]
    else:
        L += ["(not run yet)", ""]

    L += ["## The ranking", ""]
    if ranking:
        n_near = sum(1 for r in ranking if r.get("near_corpus"))
        L += [f"{len(ranking)} lay roles (one per stem); {n_near} near a corpus role (cosine >= 0.75, still ranked).",
              "", f"Top {min(top, len(ranking))}:", "",
              "| rank | role | score | Zipf | employment | nearest corpus role | cosine | group |",
              "|---|---|---|---|---|---|---|---|"]
        for r in ranking[:top]:
            emp = f"{r['employment']:,}" if r.get("employment") is not None else "-"
            cos = f"{r['cosine']:.2f}" if r.get("cosine") is not None else "-"
            L.append(f"| {r['rank']} | {_md(r['role'])} | {r['score']:+.2f} | {r.get('zipf', 0):.2f} | {emp} | "
                     f"{_role_link(r.get('nearest_role'), rd, data_dir)} | {cos}{' near' if r.get('near_corpus') else ''} "
                     f"| {_md(r.get('group'))} |")
        L.append("")
    else:
        L += ["(not ranked yet)", ""]

    L += ["## The submission", ""]
    if sub:
        lf = rd / "label_fit"
        if lf.exists():
            L += [f"Label-fit check: {_link(lf / 'readout.md', rd)}, {_link(lf / 'decisions.json', rd)}.", ""]
        L += [f"{sub.get('mode')}: {sub.get('rows_submitted')} rows submitted ({sub.get('rows_counted')} net-new, "
              f"counted; {sub.get('rows_registered')} already registered, resubmitted for their provenance); "
              f"{sub.get('rows_excluded')} ranked roles excluded (a corpus role or a queue entry); "
              f"{sub.get('n_candidates')} candidates.",
              f"Label-fit corrections: {json.dumps(sub.get('label_fit'))}.", ""]
        bal = sub.get("balance") or {}
        from .submit import balance_text
        L += [f"- {x}" for x in balance_text(bal)]
        from assistant_axis.gapgen import roles_pass as RP
        for k, name in (("before", "now"), ("after_kept", "after, at the kept share")):
            if bal.get(k):
                L += ["", f"Kinds {name} (count / held at the reference share):", ""]
                L += [f"- {x}" for x in RP.balance_lines(bal[k])]
        L.append("")
        kb = None
        if registry_path is not None and Path(registry_path).exists() and (rd / "keys.txt").exists():
            from assistant_axis.gapgen.registry import Registry
            keys = (rd / "keys.txt").read_text(encoding="utf-8").split()
            kb = kept_balance(keys, Registry(registry_path).fold(), data_dir=data_dir)
        if kb:
            L += [f"After M3: {kb['n_decided']} of the run's {kb['n_rows']} rows decided, {kb['n_kept']} kept (new or "
                  f"grey), by the kind call: {json.dumps(kb['kept_by_kind'])}.", ""]
            L += [f"- {x}" for x in RP.balance_lines(kb["after"])]
            if kb["flagged"]:
                L += ["", "Share moved by more than five points (flagged, never cut): " + ", ".join(
                    f"{k} {kb['share_moved'][k]:+.1%}" for k in kb["flagged"]) + "."]
            L.append("")
        else:
            L += ["(no M3 decision on the run's rows yet: the kept-by-kind readout comes after "
                  "`novelty_score.py score --holding roles`)", ""]
    else:
        L += ["(not submitted yet)", ""]

    L += ["## Cost", ""]
    L.append(f"usage.json: ${usage.get('total_cost_usd', 0):.4f} over {usage.get('n_calls', 0)} calls "
             f"({', '.join(sorted((usage.get('per_model') or {}).keys())) or 'none'}).")
    return "\n".join(L) + "\n"


def write_report(run_dir: Path, *, data_dir: Path = DATA_DIR, registry_path: Optional[Path] = None) -> Path:
    p = Path(run_dir) / REPORT_NAME
    atomic_write_text(report_markdown(run_dir, data_dir=data_dir, registry_path=registry_path), p)
    return p


__all__ = ["RECOVERY_TARGET", "SHARE_FLAG", "kept_balance", "corpus_occupations", "recovery_by_string", "title_strings", "table_title_stems",
           "lay_recovery", "report_markdown", "write_report"]
