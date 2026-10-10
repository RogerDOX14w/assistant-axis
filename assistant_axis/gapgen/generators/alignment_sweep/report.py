"""The readout (the plan's "table of ~40") and the gold recovery (tasks 10 and 11).

**Rows** (:func:`build_rows`): one per submitted candidate (``submitted_items.json``), joined with its extraction
item, its registry row (M1's ``filter`` block, M3's ``novelty`` block), the enactability gate's row and the probe's
``label_known``.  A **survivor** is a row M1 kept as a trait and M3 decided ``new`` or ``grey``, or that M3 marked
as completing a pair (``pair_completion_for``); a **cover** is a row M3 decided ``covered`` and that completes no
pair.  Every row shows its **alignment score and cut-off** (Roger's note under plan 08's table: near alignment, an
apparent duplicate may be a kept scope-narrowing, and a cover at cut-off 4 means "either label could replace the
other").

**Rank** (plan 08 step 7, coding plan § 8): ``source_weight`` x novelty (new, grey or pair completion 1, covered 0)
x pairability (the partner pole survives too 1, else 0.5) x label-known (1, else 0.5; a label the probe did not
reach, or a skipped probe, drops the factor), highest first, ties by the pair's rank, then the key.

**Gold recovery** (:func:`gold_recovery`; interface request 1 of the coding plan is not built, so this is its
no-call first reading): a gold trait is recovered by a candidate of the run when the candidate's label names it
(separator-blind, or one of its ``renamed_from``), when M3 decided the candidate covered by it, or when one of the
candidate's recorded overlap readings of it covers at the candidate's cut-off (:func:`recovery.pair_outcome`).  This
reads the run's own M3 blocks against the full corpus; the plan's check against a corpus with the gold traits
hidden is :func:`gold_hidden_doc` plus the commands ``report --gold`` prints.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Mapping, Optional, Sequence

from . import GENERATOR

KEPT = ("new", "grey")


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


@dataclass
class ReadoutRow:
    key: str
    label: str
    partner: Optional[str]
    gloss: str
    type: Optional[str]
    enactability: Optional[str]
    gate: Optional[str]
    gate_flip: bool
    scope_line: Optional[str]
    m1: str
    alignment_score: Optional[int]
    cut_off: Optional[int]
    decision: Optional[str]
    pair_completion_for: list
    nearest: str
    covered_by: Optional[str]
    label_known: Optional[bool]
    source: Optional[str]
    source_weight: float
    rank: int
    group: str                      # survivor | covered | filtered
    score: float = 0.0
    partner_survives: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


def _val(x):
    return (x or {}).get("value") if isinstance(x, Mapping) else x


def nearest_text(nv: Mapping) -> str:
    r = nv.get("deciding_reading") or {}
    if not r:
        return ""
    s, o = _val(r.get("sonnet")), _val(r.get("opus"))
    return f"{r.get('stem')} ({s if s is not None else '-'}/{o if o is not None else '-'})"


def _group(row: Optional[Mapping]) -> str:
    if not row:
        return "filtered"
    f, nv = row.get("filter") or {}, row.get("novelty") or {}
    if f.get("verdict") != "trait" or not nv:
        return "filtered"
    if nv.get("decision") in KEPT or nv.get("pair_completion_for"):
        return "survivor"
    if nv.get("decision") == "covered":
        return "covered"
    return "filtered"


def build_rows(submitted: Sequence[Mapping], items: Mapping[str, Mapping], registry_rows: Mapping[str, Mapping], *,
               gate_rows: Mapping[str, Mapping], label_known: Mapping[str, Optional[bool]]) -> list[ReadoutRow]:
    """The readout's rows with their rank scores (module docstring)."""
    out = []
    for s in submitted:
        reg = registry_rows.get(s["key"]) or {}
        it = items.get(s["item_id"]) or {}
        f, nv, g = reg.get("filter") or {}, reg.get("novelty") or {}, gate_rows.get(s["key"]) or {}
        m1 = f.get("verdict") or "not filtered"
        if f.get("tags"):
            m1 += " / " + ", ".join(f["tags"])
        out.append(ReadoutRow(
            key=s["key"], label=s["surface"], partner=s.get("partner_hint"), gloss=it.get("gloss") or "",
            type=it.get("type"), enactability=it.get("enactability"), gate=g.get("visibility"),
            gate_flip=bool(g.get("flip")), scope_line=g.get("scope_line"), m1=m1,
            alignment_score=nv.get("alignment_score"), cut_off=nv.get("cut_off"), decision=nv.get("decision"),
            pair_completion_for=list(nv.get("pair_completion_for") or []), nearest=nearest_text(nv),
            covered_by=nv.get("covered_by"), label_known=label_known.get(s["surface"]), source=s.get("source_ref"),
            source_weight=float(it.get("source_weight") or 1), rank=int(it.get("rank") or 0), group=_group(reg)))
    surv = {r.label for r in out if r.group == "survivor"}
    for r in out:
        r.partner_survives = bool(r.partner and r.partner in surv)
        novelty = 1.0 if r.group == "survivor" else 0.0
        pairability = 1.0 if r.partner_survives else 0.5
        known = 0.5 if r.label_known is False else 1.0
        r.score = r.source_weight * novelty * pairability * known
    return out


def rank(rows: Sequence[ReadoutRow]) -> list[str]:
    return [r.key for r in sorted(rows, key=lambda r: (-r.score, r.rank, r.key))]


def costs_by_step(run_json: Mapping) -> dict:
    """``{step: {model: usd}}`` from a run's sessions (each paid command is a session with ``args.step``)."""
    out: dict = defaultdict(lambda: defaultdict(float))
    for s in run_json.get("sessions") or []:
        step = (s.get("args") or {}).get("step") or "other"
        for model, t in ((s.get("usage") or {}).get("per_model") or {}).items():
            out[step][model] += float(t.get("cost_usd") or 0)
    return {k: dict(v) for k, v in out.items()}


COLUMNS = ("rank", "label (partner)", "gloss", "type", "enactability", "M1 verdict/tags", "alignment score", "cut-off",
           "M3 decision", "nearest reading (trait, sonnet/opus)", "covered_by", "label-known", "source", "score")


def _row_md(i: int, r: ReadoutRow) -> str:
    enact = r.enactability or ""
    if r.gate:
        enact += f" / gate {r.gate}" + (" (flip)" if r.gate_flip else "")
    dec = (r.decision or "") + (f"; completes {', '.join(r.pair_completion_for)}" if r.pair_completion_for else "")
    known = {True: "yes", False: "no", None: "n/a"}[r.label_known]
    cells = [str(i), f"{r.label} ({r.partner or 'no partner'})", r.gloss, r.type, enact, r.m1,
             "" if r.alignment_score is None else str(r.alignment_score), "" if r.cut_off is None else str(r.cut_off),
             dec, r.nearest, r.covered_by, known, r.source, f"{r.score:g}"]
    return "| " + " | ".join(_md(c) for c in cells) + " |"


def render_readout(rows: Sequence[ReadoutRow], *, run_id: str, counts: Mapping, costs: Mapping, probe_status: str,
                   gate_status: str, top: Optional[int] = None) -> str:
    by = {r.key: r for r in rows}
    order = [by[k] for k in rank(rows)]
    surv = [r for r in order if r.group == "survivor"]
    cov = [r for r in order if r.group == "covered"]
    head = "| " + " | ".join(COLUMNS) + " |\n|" + "---|" * len(COLUMNS)
    lines = [f"# Alignment sweep readout, run {run_id}", "",
             f"Generator `{GENERATOR}`.  Counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + ".", "",
             f"Label probe: {probe_status}.  Enactability gate: {gate_status}.", "",
             "Every row shows its alignment score and its cut-off: near alignment (score 2 or 3) M3's cut-off is 4, so a "
             "scope-narrowing survives beside a trait that looks like its duplicate; read the score, not the overlap "
             "reading, when a survivor looks wrong.  Rank score = source weight x novelty x pairability x label-known.",
             "", f"## Survivors ({len(surv)}{f', top {top} shown' if top and len(surv) > top else ''})", "", head]
    lines += [_row_md(i, r) for i, r in enumerate(surv[:top] if top else surv, 1)]
    lines += ["", f"## Covered ({len(cov)})", "", head]
    lines += [_row_md(i, r) for i, r in enumerate(cov, 1)]
    scoped = [r for r in surv if r.scope_line]
    lines += ["", "## Scope lines for the agentic-only survivors", ""]
    lines += [f"- **{r.label}**: {r.scope_line}" for r in scoped] or ["(none)"]
    lines += ["", "## Cost by step and model (usage files)", "", "| step | model | USD |", "|---|---|---|"]
    for step, per in costs.items():
        for model, usd in per.items():
            lines.append(f"| {step} | {model} | {usd:.4f} |")
    total = sum(v for per in costs.values() for v in per.values())
    lines.append(f"| total | | {total:.4f} |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- gold recovery

def gold_hidden_doc(gold: Mapping, *, partners: Mapping[str, Sequence[str]]) -> dict:
    """A ``hidden.json`` for the recovery harness's ``--hide``: the ten gold stems and every arrangement partner
    (``partners``: stem -> its hiding-group mates), sorted (the harness's rule: arrangements hide whole)."""
    stems = [g["stem"] for g in gold["traits"]]
    hidden = set(stems)
    for s in stems:
        hidden |= set(partners.get(s) or [])
    return {"schema": 1, "kind": "alignment_sweep_gold", "gold": stems, "hidden": sorted(hidden),
            "n_hidden": len(hidden)}


def _reading_hit(reading: Mapping, cut_off: Optional[int]) -> bool:
    from assistant_axis.gapgen.recovery import pair_outcome
    if cut_off is None:
        return False
    return bool(pair_outcome(reading, int(cut_off))["recovers"])


def gold_recovery(gold: Mapping, registry_rows: Mapping[str, Mapping], submitted: Sequence[Mapping], *, run_id: str,
                  renamed: Optional[Mapping[str, Sequence[str]]] = None) -> dict:
    """The no-call first reading of gold recovery (module docstring)."""
    from assistant_axis.gapgen.novelty import blind
    renamed = renamed or {}
    ref = {s["key"]: s.get("source_ref") for s in submitted}
    keys = [s["key"] for s in submitted if s["key"] in registry_rows]
    out = []
    for g in gold["traits"]:
        stem = g["stem"]
        names = {blind(stem)} | {blind(o) for o in renamed.get(stem, [])}
        hits, closest = [], None
        for k in keys:
            row = registry_rows[k]
            nv = row.get("novelty") or {}
            label = row.get("label") or k
            if blind(row.get("stem") or k.split("#")[0]) in names:
                hits.append({"key": k, "label": label, "how": "label"})
            if nv.get("covered_by") == stem:
                hits.append({"key": k, "label": label, "how": "covered_by", "decision": nv.get("decision")})
            for r in nv.get("readings") or []:
                if r.get("stem") != stem:
                    continue
                s, o = _val(r.get("sonnet")), _val(r.get("opus"))
                if _reading_hit(r, nv.get("cut_off")):
                    hits.append({"key": k, "label": label, "how": "overlap", "sonnet": s, "opus": o,
                                 "cut_off": nv.get("cut_off")})
                best = max([v for v in (s, o) if isinstance(v, int)], default=-1)
                if closest is None or best > closest["best"]:
                    closest = {"key": k, "label": label, "sonnet": s, "opus": o, "cut_off": nv.get("cut_off"),
                               "best": best}
        seen, uniq = set(), []
        for h in hits:
            if (h["key"], h["how"]) not in seen:
                seen.add((h["key"], h["how"]))
                uniq.append(h | {"source_ref": ref.get(h["key"])})
        out.append({"stem": stem, "label": g.get("label"), "maps_from": g.get("maps_from"), "recovered": bool(uniq),
                    "hits": uniq, "closest": closest})
    fp = [s for s in gold.get("frame_pair") or []]
    fp_hits = [h for g in out if g["stem"] in fp for h in g["hits"]]
    for s in fp:                                            # the frame pair's other pole, if not in the ten
        if s not in {g["stem"] for g in out}:
            for k in keys:
                nv = registry_rows[k].get("novelty") or {}
                if nv.get("covered_by") == s:
                    fp_hits.append({"key": k, "label": registry_rows[k].get("label"), "how": "covered_by",
                                    "source_ref": ref.get(k)})
    n_rec = sum(1 for g in out if g["recovered"])
    return {"run_id": run_id, "n": len(out), "n_recovered": n_rec, "target": 7, "gold": out,
            "frame_pair": {"stems": fp, "hit": bool(fp_hits), "candidates": fp_hits},
            "method": "no-call first reading of the run's own M3 blocks (full corpus)"}


def render_gold_recovery(res: Mapping, *, run_id: str, hidden_commands: Sequence[str] = ()) -> str:
    met = res["n_recovered"] >= res["target"]
    fp = res["frame_pair"]
    lines = [f"# Alignment sweep gold recovery, run {run_id}", "",
             f"Recovered **{res['n_recovered']} of {res['n']}** gold traits (target at least {res['target']}: "
             f"{'met' if met else 'not met'}).  Method: {res['method']}.", "",
             "The frame pair (" + " / ".join(fp["stems"]) + "): " +
             ("recovered by " + "; ".join(f"{h['label']} ({h['how']}, from {h.get('source_ref')})"
                                          for h in fp["candidates"]) if fp["hit"] else "not recovered") +
             ".  Plan 08 asks for it from the eval-awareness material specifically: read the sources named.", "",
             "## Recovered", "", "| gold trait | maps from | by | how | source |", "|---|---|---|---|---|"]
    for g in res["gold"]:
        for h in g["hits"]:
            how = h["how"] + (f" ({h.get('sonnet')}/{h.get('opus')} at cut-off {h.get('cut_off')})"
                              if h["how"] == "overlap" else "")
            lines.append(f"| {g['label']} | {g['maps_from']} | {_md(h['label'])} | {how} | {_md(h.get('source_ref'))} |")
    lines += ["", "## Misses", ""]
    for g in res["gold"]:
        if g["recovered"]:
            continue
        c = g["closest"]
        why = (f"closest: {c['label']} read {c['sonnet']}/{c['opus']} at cut-off {c['cut_off']}" if c else
               "no candidate's recorded readings reached it")
        lines.append(f"- **{g['label']}** (maps from {g['maps_from']}): {why}")
    if hidden_commands:
        lines += ["", "## The hidden-corpus check (the plan's method)", "",
                  "Interface request 1 (`recovery_test.py --hidden-stems`) is not built; meanwhile:", ""]
        lines += [f"    {c}" for c in hidden_commands]
    return "\n".join(lines) + "\n"


__all__ = ["ReadoutRow", "COLUMNS", "build_rows", "rank", "costs_by_step", "nearest_text", "render_readout",
           "gold_hidden_doc", "gold_recovery", "render_gold_recovery"]
