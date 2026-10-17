"""The generator's free measures and, after the pilot, each frame's yield and net filter (plan sections 6, 8 and 10).

Free (``evaluate``; no call):

* :func:`recovery_curves`: recall@k of the corpus's labels and the seed queue's, per label class (``single``,
  ``hyphenated``, ``multiword``), for the union under both orderings (``union_volumes``: RRF over the frames' ranks
  by document frequency; ``union_lift``: over their ranks by lift), per frame under both, and beside two
  **baselines** the frames must beat: ``baseline_wordfreq`` (OEWN's adjectives and person nouns by Zipf alone,
  plan 04's) and ``baseline_table_zipf`` (the table's own words by Zipf alone: what the frames' ordering adds over
  frequency).  A label is recovered at k when its stem, or a filler folded into a row, is among the first k rows.
* :func:`ordering_choice`: the pre-registered rule of section 1: the ordering with the higher union recall of the
  corpus labels at 1,000 becomes the default (a tie goes to ``volumes``); the other stays a column.
* :func:`unfound_labels`: the corpus labels no frame finds, by region (expected: concept phrases, alignment traits,
  memberships; plan 05 section 4).
* :func:`registry_overlap`: the share of the first N eligible rows already in the registry (the proxy said 80 / 63 /
  41% at 500 / 2,000 / 5,000).

After the pilot (``evaluate --pilot-run R``; the registry's M1 and M3 blocks, at no cost):

* :func:`frame_measures`: per frame, over **its** pilot fillers (the top 25 the pilot selected for it, recorded in
  the run's ``selection_by_frame``; a registered filler counts with its recorded verdict): the **yield** (M1 ``trait``
  share), the **net filter** (``region_tv`` and ``form_tv``: the total variation distance, half the sum of absolute
  differences, between the distribution of the frame's trait fillers over the regions, or over the forms adjective /
  noun / phrase, and the union's), ``physical_state_share`` (M1 ``physical`` or ``state`` tags, or those holding lists,
  among its filtered fillers) and ``unique_kept`` (M3-kept rows, ``new`` or ``grey``, that no other frame found);
* :func:`keep_frame`: kept for the wave when the yield is at least 0.4 and ``region_tv`` at most 0.5, **or** it has a
  unique kept row (recommendations for Roger at the pilot gate; a dropped frame's rows stay in the table);
* :func:`type_measures`: the same distances for each type's union, and the labels only that type found.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name

CUTOFFS: tuple[int, ...] = (500, 1000, 3000, 10000)
ORDERINGS: tuple[str, ...] = ("volumes", "lift")
UNION_FIELD = {"volumes": "union_rank", "lift": "rank_lift_union"}
FRAME_FIELD = {"volumes": "rank_volumes", "lift": "rank_lift"}
CLASSES: tuple[str, ...] = ("single", "hyphenated", "multiword")
YIELD_MIN = 0.4
TV_MAX = 0.5
CHOICE_CUTOFF = 1000
NOVEL = ("new", "grey")
OVERLAP_DEPTHS: tuple[int, ...] = (500, 2000, 5000)
#: The proxy's registry overlap at those depths (plan, "Baseline": the masked-LM table, pilot A).
PROXY_OVERLAP = {"top_500": 0.80, "top_2000": 0.63, "top_5000": 0.41}


def _frac(a: float, b: float) -> Optional[float]:
    return round(a / b, 4) if b else None


def _stem(s: str) -> str:
    return normalize_to_file_name(s)


def label_class(label: str) -> str:
    """``multiword`` (a space), ``hyphenated`` (a hyphen and no space) or ``single``."""
    s = str(label).strip()
    return "multiword" if " " in s else "hyphenated" if "-" in s else "single"


def _aliases(row: Mapping) -> list[str]:
    out = [row["stem"]]
    for f in row.get("fillers") or []:
        st = _stem(f["surface"])
        if st and st not in out:
            out.append(st)
    return out


def positions_from_rows(rows: Sequence[Mapping]) -> dict[str, int]:
    """``{stem: 0-based position}`` for rows in order; a row's fillers' stems take the row's position."""
    pos: dict[str, int] = {}
    for i, r in enumerate(rows):
        for st in _aliases(r):
            pos.setdefault(st, i)
    return pos


def _eligible(table: Sequence[Mapping]) -> list[Mapping]:
    """The rows that can be submitted (``eligible``): every recovery figure and baseline is read over them (review
    S3, 2026-10-17), since an ineligible row never reaches the registry."""
    return [r for r in table if r.get("eligible", True)]


def union_positions(table: Sequence[Mapping], ordering: str = "volumes") -> dict[str, int]:
    f = UNION_FIELD[ordering]
    return positions_from_rows(sorted(_eligible(table), key=lambda r: int(r[f])))


def frame_positions(table: Sequence[Mapping], key: str, ordering: str = "volumes") -> dict[str, int]:
    f = FRAME_FIELD[ordering]
    rows = sorted((r for r in _eligible(table) if key in (r.get("frames") or {})),
                  key=lambda r: int(r["frames"][key][f]))
    return positions_from_rows(rows)


def list_positions(ranking: Sequence[str]) -> dict[str, int]:
    pos: dict[str, int] = {}
    for i, st in enumerate(ranking):
        pos.setdefault(st, i)
    return pos


def recall(pos: Mapping[str, int], labels: Sequence[str], cutoffs: Sequence[int] = CUTOFFS) -> dict:
    stems = [_stem(lab) for lab in labels]
    out = {"n": len(stems), "n_ranked": len(set(pos.values())) if pos else 0}
    for k in cutoffs:
        out[f"recall@{k}"] = _frac(sum(1 for s in stems if pos.get(s, 1 << 60) < k), len(stems))
    out["found_anywhere"] = _frac(sum(1 for s in stems if s in pos), len(stems))
    return out


def _groups(labels: Sequence[str], classes: Sequence[str] = CLASSES) -> dict[str, list[str]]:
    g = {"all": list(labels)}
    for c in classes:
        g[c] = [lab for lab in labels if label_class(lab) == c]
    return g


def table_zipf_ranking(table: Sequence[Mapping]) -> list[str]:
    """The table's eligible rows by Zipf alone (descending; ties by stem): the frames' ordering must beat it."""
    return [r["stem"] for r in sorted(_eligible(table), key=lambda r: (-(r.get("zipf") or 0.0), r["stem"]))]


def frequency_ranking(universe: Sequence[str], zipf: Callable[[str], float]) -> list[str]:
    """A universe by Zipf descending (plan 04's wordfreq baseline)."""
    from ..masked_lm.evaluate import frequency_ranking as _fr
    return _fr(universe, zipf)


def recovery_curves(table: Sequence[Mapping], label_sets: Mapping[str, Sequence[str]],
                    cutoffs: Sequence[int] = CUTOFFS, *, frame_keys: Optional[Iterable[str]] = None,
                    baselines: Optional[Mapping[str, Sequence[str]]] = None) -> dict:
    """``{ranking: {label set: {class: recall}}}`` for ``union_volumes``, ``union_lift`` and each baseline, and
    ``per_frame: {frame: {ordering: {label set: {"all", "single": recall}}}}``."""
    ranks = {f"union_{o}": union_positions(table, o) for o in ORDERINGS}
    for name, r in (baselines or {}).items():
        ranks[name] = list_positions(r)
    out: dict = {}
    for name, pos in ranks.items():
        out[name] = {s: {c: recall(pos, labs, cutoffs) for c, labs in _groups(list(labels)).items()}
                     for s, labels in label_sets.items()}
    keys = sorted(set(frame_keys) if frame_keys is not None else {k for r in table for k in r.get("frames") or {}})
    per: dict = {}
    for k in keys:
        per[k] = {}
        for o in ORDERINGS:
            pos = frame_positions(table, k, o)
            per[k][o] = {s: {c: recall(pos, labs, cutoffs) for c, labs in _groups(list(labels)).items()
                             if c in ("all", "single")} for s, labels in label_sets.items()}
    out["per_frame"] = per
    return out


def ordering_choice(recovery: Mapping, *, label_set: str = "corpus", cutoff: int = CHOICE_CUTOFF) -> tuple[str, str]:
    """``(ordering, why)``: the one with the higher union recall of ``label_set`` (all classes) at ``cutoff``; a tie
    goes to ``volumes`` (plan section 1, pre-registered)."""
    def r(o):
        return ((recovery.get(f"union_{o}") or {}).get(label_set) or {}).get("all", {}).get(f"recall@{cutoff}") or 0.0
    v, li = r("volumes"), r("lift")
    if li > v:
        return "lift", f"union recall@{cutoff} of the {label_set} labels: lift {li:.4f} > volumes {v:.4f}"
    return "volumes", (f"union recall@{cutoff} of the {label_set} labels: volumes {v:.4f} "
                       + ("= lift (a tie goes to volumes)" if li == v else f"> lift {li:.4f}"))


def corpus_regions(path: Optional[Path]) -> dict[str, str]:
    """``{corpus stem: region}`` from ``corpus_regions.json`` (enveloped or bare)."""
    if not path or not Path(path).exists():
        return {}
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d) if isinstance(d, dict) else d
    rows = d.get("regions", d) if isinstance(d, dict) else {}
    return {k: v.get("region") for k, v in rows.items() if isinstance(v, dict) and v.get("region")}


def unfound_labels(table: Sequence[Mapping], labels: Sequence[str], *, regions: Mapping[str, str]) -> dict:
    """The labels whose stem no row has (as its stem or a filler's), by region and by class."""
    have = {st for r in table for st in _aliases(r)}
    missing = [lab for lab in labels if _stem(lab) not in have]
    by_region: dict[str, list] = {}
    for lab in missing:
        by_region.setdefault(regions.get(_stem(lab)) or "unknown", []).append(lab)
    return {"n": len(missing), "n_labels": len(labels), "share": _frac(len(missing), len(labels)),
            "by_region": {k: sorted(v) for k, v in sorted(by_region.items())},
            "by_class": dict(sorted(Counter(label_class(lab) for lab in missing).items())),
            "stems": sorted(_stem(lab) for lab in missing)}


def registry_overlap(table: Sequence[Mapping], registered_stems: Iterable[str], *, ordering: str = "volumes",
                     depths: Sequence[int] = OVERLAP_DEPTHS) -> dict:
    """The share of the first N eligible rows (by the ordering's union rank) whose stem is in the registry."""
    reg = set(registered_stems)
    rows = sorted((r for r in table if r.get("eligible")), key=lambda r: int(r[UNION_FIELD[ordering]]))
    out = {}
    for n in depths:
        head = rows[:n]
        out[f"top_{n}"] = _frac(sum(1 for r in head if r["stem"] in reg), len(head))
    out["proxy"] = dict(PROXY_OVERLAP)
    return out


# --------------------------------------------------------------------------- after the pilot

def _tv(p: Mapping[str, int], q: Mapping[str, int]) -> Optional[float]:
    sp, sq = sum(p.values()), sum(q.values())
    if not sp or not sq:
        return None
    keys = set(p) | set(q)
    return round(0.5 * sum(abs(p.get(k, 0) / sp - q.get(k, 0) / sq) for k in keys), 4)


def total_variation(p: Mapping[str, int], q: Mapping[str, int]) -> Optional[float]:
    """Half the sum of absolute differences between two distributions given as counts (None when one is empty)."""
    return _tv(p, q)


def _reg_by_stem(registry_rows: Mapping[str, Mapping]) -> dict[str, Mapping]:
    out: dict[str, Mapping] = {}
    for _, r in sorted(registry_rows.items(), key=lambda kv: (kv[1].get("stem") or "", int(kv[1].get("sense_id")
                                                                                           or 1))):
        st = r.get("stem")
        if st and st not in out:
            out[st] = r
    return out


def registry_row_for(row: Mapping, reg: Mapping[str, Mapping]) -> Optional[Mapping]:
    """The registry row that carries a table row's verdict: its stem's (the label), else its submitted surface's."""
    r = reg.get(row["stem"])
    if r is not None and r.get("filter"):
        return r
    s = reg.get(row.get("surface_stem") or "")
    if s is not None and s.get("filter"):
        return s
    return r or s


def _region(r: Mapping) -> str:
    return (r.get("filter") or {}).get("region") or (r.get("novelty") or {}).get("region") or "none"


def _physical_or_state(r: Mapping) -> bool:
    tags = set((r.get("filter") or {}).get("tags") or [])
    return bool(tags & {"physical", "state"}) or r.get("holding") in ("physical", "states")


def _measure(rows: Sequence[Mapping], reg: Mapping[str, Mapping]) -> dict:
    regs = [(row, registry_row_for(row, reg)) for row in rows]
    filt = [(row, r) for row, r in regs if r is not None and r.get("filter")]
    trait = [(row, r) for row, r in filt if r["filter"].get("verdict") == "trait"]
    kept = [(row, r) for row, r in regs if r is not None and (r.get("novelty") or {}).get("decision") in NOVEL]
    return {"n": len(rows), "n_filtered": len(filt), "n_trait": len(trait), "yield": _frac(len(trait), len(filt)),
            "regions": dict(sorted(Counter(_region(r) for _, r in trait).items())),
            "forms": dict(sorted(Counter(row.get("form") or "?" for row, _ in trait).items())),
            "physical_state_share": _frac(sum(1 for _, r in filt if _physical_or_state(r)), len(filt)),
            "kept": len(kept), "unique_kept": sum(1 for row, _ in kept if int(row.get("n_frames") or 0) == 1),
            "unique_kept_stems": sorted(row["stem"] for row, _ in kept if int(row.get("n_frames") or 0) == 1)}


def frame_measures(table: Sequence[Mapping], registry_rows: Mapping[str, Mapping], *,
                   selection: Mapping[str, Sequence[str]]) -> dict:
    """Per frame of ``selection`` (``{frame: [stems the pilot selected for it]}``): the measures of the module
    docstring, and the union's own (``_union``)."""
    by_stem = {r["stem"]: r for r in table}
    reg = _reg_by_stem(registry_rows)
    union_stems = sorted({s for ss in selection.values() for s in ss if s in by_stem})
    union = _measure([by_stem[s] for s in union_stems], reg)
    out = {}
    for key in sorted(selection):
        m = _measure([by_stem[s] for s in selection[key] if s in by_stem], reg)
        m["region_tv"] = _tv(m["regions"], union["regions"])
        m["form_tv"] = _tv(m["forms"], union["forms"])
        out[key] = m
    out["_union"] = union
    return out


def type_measures(table: Sequence[Mapping], registry_rows: Mapping[str, Mapping], *,
                  selection: Mapping[str, Sequence[str]], frame_types: Mapping[str, str]) -> dict:
    """Per type: its frames' selected rows together, measured as a frame is (against the union of all frames), and
    the stems of the kept rows whose every frame is of that type."""
    by_stem = {r["stem"]: r for r in table}
    reg = _reg_by_stem(registry_rows)
    union_stems = sorted({s for ss in selection.values() for s in ss if s in by_stem})
    union = _measure([by_stem[s] for s in union_stems], reg)
    types = sorted({frame_types[k] for k in selection if k in frame_types})
    out = {}
    for t in types:
        stems = sorted({s for k, ss in selection.items() if frame_types.get(k) == t for s in ss if s in by_stem})
        m = _measure([by_stem[s] for s in stems], reg)
        m["region_tv"] = _tv(m["regions"], union["regions"])
        m["form_tv"] = _tv(m["forms"], union["forms"])
        only = []
        for s in stems:
            row = by_stem[s]
            r = registry_row_for(row, reg)
            if r is not None and (r.get("novelty") or {}).get("decision") in NOVEL and \
                    {frame_types.get(k) for k in row.get("frames") or {}} == {t}:
                only.append(s)
        m["only_this_type_kept"] = only
        out[t] = m
    return out


def keep_frame(measure: Optional[Mapping], *, yield_min: float = YIELD_MIN, tv_max: float = TV_MAX
               ) -> tuple[bool, str]:
    """``(keep, why)`` (the plan's rule; thresholds Roger's at the pilot gate): yield >= ``yield_min`` and
    ``region_tv`` <= ``tv_max``, or at least one unique kept row.  Before the pilot (no measure) every frame is kept."""
    if not measure:
        return True, "no pilot measure yet: kept"
    y, tv, u = measure.get("yield"), measure.get("region_tv"), int(measure.get("unique_kept") or 0)
    if y is not None and y >= yield_min and (tv is None or tv <= tv_max):
        return True, f"yield {y:.2f} >= {yield_min} and region_tv {('n/a' if tv is None else f'{tv:.2f}')} <= {tv_max}"
    if u >= 1:
        return True, (f"{u} unique kept row{'s' if u != 1 else ''} (yield {('n/a' if y is None else f'{y:.2f}')}, "
                      f"region_tv {('n/a' if tv is None else f'{tv:.2f}')})")
    if y is None:
        return False, "no filtered filler and no unique kept row"
    why = []
    if y < yield_min:
        why.append(f"yield {y:.2f} < {yield_min}")
    if tv is not None and tv > tv_max:
        why.append(f"region_tv {tv:.2f} > {tv_max}")
    return False, " and ".join(why) + ", no unique kept row"


def frames_kept(measures: Mapping[str, Mapping], frame_keys: Iterable[str], *, yield_min: float = YIELD_MIN,
                tv_max: float = TV_MAX, keep: Iterable[str] = (), drop: Iterable[str] = ()) -> tuple[list, dict]:
    """``(kept frame keys, {frame: [keep, why]})``: :func:`keep_frame` per frame, then Roger's hand choices
    (``keep`` / ``drop``, recorded as such)."""
    keep, drop = set(keep), set(drop)
    verdicts = {}
    for k in frame_keys:
        ok, why = keep_frame(measures.get(k), yield_min=yield_min, tv_max=tv_max)
        if k in keep:
            ok, why = True, f"kept by hand ({why})"
        if k in drop:
            ok, why = False, f"dropped by hand ({why})"
        verdicts[k] = [ok, why]
    return sorted(k for k, (ok, _) in verdicts.items() if ok), verdicts


# --------------------------------------------------------------------------- the evaluation payload

def build_evaluation(table: Sequence[Mapping], *, label_sets: Mapping[str, Sequence[str]], frame_keys: Sequence[str],
                     table_sha256: Optional[str], bank_sha256: str, text_bank_sha256: Optional[str] = None,
                     registered_stems: Iterable[str] = (), regions: Optional[Mapping[str, str]] = None,
                     baselines: Optional[Mapping[str, Sequence[str]]] = None, cutoffs: Sequence[int] = CUTOFFS,
                     ordering: str = "auto", measures: Optional[Mapping] = None,
                     types: Optional[Mapping] = None, kept: Optional[Sequence[str]] = None,
                     verdicts: Optional[Mapping] = None, pilot_run: Optional[str] = None,
                     thresholds: Optional[Mapping] = None, title: Optional[str] = None) -> dict:
    """``evaluation.json``'s payload (plan section 6)."""
    from .table import table_counts
    bl = dict(baselines or {})
    bl.setdefault("baseline_table_zipf", table_zipf_ranking(table))
    rec = recovery_curves(table, label_sets, cutoffs, frame_keys=frame_keys, baselines=bl)
    auto, why = ordering_choice(rec)
    chosen = auto if ordering == "auto" else ordering
    if chosen not in ORDERINGS:
        raise ValueError(f"--ordering must be auto, volumes or lift, not {ordering!r}")
    return {"title": title, "table_sha256": table_sha256, "bank_sha256": bank_sha256,
            "text_bank_sha256": text_bank_sha256, "ordering": chosen,
            "ordering_rule": {"auto": auto, "why": why, "given": ordering},
            "cutoffs": list(cutoffs), "n_rows": len(table), "n_eligible": sum(1 for r in table if r.get("eligible")),
            "n_net_new": sum(1 for r in table if r.get("net_new")), "table_counts": table_counts(table),
            "recovery": rec,
            "unfound_labels": unfound_labels(table, list(label_sets.get("corpus") or []), regions=regions or {}),
            "frame_measures": dict(measures) if measures is not None else None,
            "type_measures": dict(types) if types is not None else None,
            "frames_kept": list(kept) if kept is not None else list(frame_keys),
            "frame_verdicts": dict(verdicts or {}), "keep_thresholds": dict(thresholds or {"yield_min": YIELD_MIN,
                                                                                            "tv_max": TV_MAX}),
            "pilot_run": pilot_run,
            "registry_overlap": registry_overlap(table, registered_stems, ordering=chosen)}


def plot_recovery_curves(ev: Mapping, path: Path, *, inputs: Optional[list] = None, label_set: str = "corpus"
                         ) -> Path:
    """``recovery_curves.png``: recall of the corpus labels against the cutoff, one panel per label class (all,
    single, hyphenated, multiword): the union under both orderings, the two baselines dashed and dotted."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from assistant_axis import png_metadata
    from assistant_axis.plot_metadata import suptitle_with_specs
    rec = ev.get("recovery") or {}
    cut = list(ev.get("cutoffs") or CUTOFFS)
    panels = ("all",) + CLASSES
    fig, axes = plt.subplots(1, len(panels), figsize=(4.4 * len(panels), 6.2), sharey=True)
    styles = {"union_volumes": dict(lw=2.6, color="tab:red", label="union, by document frequency"),
              "union_lift": dict(lw=2.0, color="tab:blue", label="union, by lift"),
              "baseline_wordfreq": dict(lw=1.4, ls="--", color="black", label="baseline: OEWN by Zipf"),
              "baseline_table_zipf": dict(lw=1.4, ls=":", color="dimgrey", label="baseline: the table's words by Zipf")}
    for ax, c in zip(axes, panels):
        n = None
        for name, st in styles.items():
            v = ((rec.get(name) or {}).get(label_set) or {}).get(c) or {}
            if not v.get("n"):
                continue
            n = v["n"]
            ax.plot(cut, [v.get(f"recall@{k}") or 0.0 for k in cut], marker="o", ms=3, **st)
        ax.set_xscale("log")
        ax.set_xlim(cut[0] / 1.4, cut[-1] * 1.4)          # the same range on every panel, an empty one included
        if n is None:
            ax.text(0.5, 0.5, "no labels of this class", transform=ax.transAxes, ha="center", va="center",
                    color="dimgrey")
        ax.set_xticks(cut)
        ax.set_xticklabels([f"{k:,}" for k in cut], rotation=30)
        ax.set_title(f"{c} labels (n = {n if n is not None else 0})")
        ax.set_xlabel("cutoff N (first N rows)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(f"recall of the {label_set}'s labels")
    axes[0].set_ylim(0, 1)
    handles, labels = [], []
    for ax in axes:
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in labels:
                handles.append(h)
                labels.append(lab)
    fig.legend(handles, labels, loc="lower center", ncol=min(4, max(1, len(labels))), frameon=False)
    title = "Corpus-frames generator: recovery of our labels against the frequency baselines"
    spec = (f"{ev.get('title') or 'evaluate'}; {ev.get('n_rows', 0):,} rows; ordering chosen: {ev.get('ordering')} "
            f"({(ev.get('ordering_rule') or {}).get('why', '')})")
    _, top_rect = suptitle_with_specs(fig, title, spec)
    fig.subplots_adjust(top=top_rect - 0.05, bottom=0.24, left=0.05, right=0.99, wspace=0.08)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight", metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)
    return Path(path)


__all__ = ["CUTOFFS", "ORDERINGS", "UNION_FIELD", "FRAME_FIELD", "CLASSES", "YIELD_MIN", "TV_MAX", "NOVEL",
           "label_class", "positions_from_rows", "union_positions", "frame_positions", "list_positions", "recall",
           "table_zipf_ranking", "frequency_ranking", "recovery_curves", "ordering_choice", "corpus_regions",
           "unfound_labels", "registry_overlap", "total_variation", "registry_row_for", "frame_measures",
           "type_measures", "keep_frame", "frames_kept", "build_evaluation", "plot_recovery_curves"]
