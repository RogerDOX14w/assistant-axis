"""Per-cell response curves vs steps-to-incoherence.

Reads a steering experiment directory (one (role, axis) pair, one or
more bidirectional-scan cells) and plots one curve per
(cell, sign, filter) combination of:

    Y axis : mean effect score across the 14 questions at one strength
    X axis : "steps remaining to incoherence" -- 0 at the right edge
             (the cliff itself); positive integers leftward count how
             many ranked-by-magnitude strengths are between the cell's
             current strength and its incoherence cliff.

Aligning all cells at x=0 lets you compare dose-response curves whose
absolute strength scales differ (different (slot, layer) cells have
different cliff strengths).

Four filter variants per (cell, sign):

    a) all-responses  : raw mean of effect scores at each strength
    b) coh-0 only     : mean over responses with coherence score == 0
                        (no judged incoherence at all)
    c) rp-3 only      : mean over responses with persona score == 3
                        (strongly in-persona)
    d) coh-0 & rp-3   : mean over responses with both conditions

Comparing (a) vs the filtered variants reveals how much the average
effect at each strength is being dragged around by responses that
were either drifting from persona or borderline-incoherent.

Two side-by-side subplots:
    Left : sign = +1 (steers toward the negative pole; role_to)
    Right: sign = -1 (steers toward the positive pole; role_from)

Within each subplot:
    color    : cell = (slot, layer)
    linestyle: filter variant (a solid / b dashed / c dotted / d dash-dot)

Usage:
    python results_analysis/steering_response_curves.py \\
        outputs/qwen-3-32b/steering/anthropologist_helpful_v1 \\
        --output anthropologist_helpful_v1_response_curves.png
"""
from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from assistant_axis.plot_metadata import png_metadata

logger = logging.getLogger("steering_response_curves")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrengthAgg:
    """One strength's worth of mean effect under each of the four
    response-filter regimes.

    Each entry is ``None`` if that filter regime had zero qualifying
    responses (so the resulting line has a gap at this strength).
    """

    strength: float       # absolute magnitude (positive)
    mean_eff_all: Optional[float]
    mean_eff_coh0: Optional[float]
    mean_eff_rp3: Optional[float]
    mean_eff_coh0_rp3: Optional[float]
    # Bookkeeping for the legend / sanity checks.
    n_total: int          # number of records at this strength
    n_with_eff: int       # number with a non-null effect score
    n_coh0: int           # number with coh == 0


@dataclass
class CellSign:
    """One (slot, layer, sign) sweep's worth of strength-aggregates,
    ranked by magnitude with the largest at index N (= incoherence cliff).
    """

    slot: int
    layer: int
    sign: int            # +1 or -1
    aggs: List[StrengthAgg]  # sorted ascending by magnitude
    # Whether the largest swept strength hit the incoherence ceiling
    # (vs. running into max_strength without crossing the coh stop).
    # Used to label the line's right endpoint in the legend / tooltips.
    up_blocked_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Disk IO + score extraction (mirrors tools/sheet_layout.py conventions)
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _coh_score(rec: Dict[str, Any]) -> Optional[int]:
    j = rec.get("judges") or {}
    c = j.get("coherence")
    if not c:
        return None
    s = c.get("score")
    return None if s is None else int(s)


def _rp_score(rec: Dict[str, Any]) -> Optional[int]:
    j = rec.get("judges") or {}
    p = j.get("persona") or {}
    if p.get("skipped_due_to_strength_mean_coh"):
        return None
    s = p.get("score")
    return None if s is None else int(s)


def _eff_score(rec: Dict[str, Any]) -> Optional[float]:
    j = rec.get("judges") or {}
    e = j.get("effect") or {}
    if e.get("skipped_due_to_strength_mean_coh"):
        return None
    s = e.get("combined")
    return None if s is None else float(s)


def _safe_mean(xs: List[Optional[float]]) -> Optional[float]:
    f = [x for x in xs if x is not None]
    return mean(f) if f else None


# ---------------------------------------------------------------------------
# Per-cell aggregation
# ---------------------------------------------------------------------------

def aggregate_cell_sign(cell_dir: Path) -> CellSign:
    """Read one ``s<slot>_l<layer>_<+1|-1>`` directory and group its
    records by strength, computing each of the four filter means.
    """
    name = cell_dir.name  # "s3_l25_+1"
    # Parse slot/layer/sign back from dir name -- robust to any
    # signed-integer slot or layer.
    parts = name.split("_")
    slot = int(parts[0][1:])           # "s3" -> 3
    layer = int(parts[1][1:])          # "l25" -> 25
    sign_str = parts[2]                # "+1" or "-1"
    sign = int(sign_str)

    records = _read_jsonl(cell_dir / "records.jsonl")
    # Group by exact strength value (records use floats; rounding errors
    # are tolerable because the runner reuses the same float each time
    # it writes a strength).
    by_strength: Dict[float, List[Dict[str, Any]]] = {}
    for r in records:
        try:
            s = float(r.get("strength", 0.0))
        except (TypeError, ValueError):
            continue
        if s == 0.0:
            continue  # baseline rows -- excluded from steering curves
        by_strength.setdefault(s, []).append(r)

    aggs: List[StrengthAgg] = []
    for s in sorted(by_strength.keys()):
        recs = by_strength[s]
        coh = [_coh_score(r) for r in recs]
        rp = [_rp_score(r) for r in recs]
        eff = [_eff_score(r) for r in recs]

        # Filter regimes -- each returns the eff value or None.
        def filter_eff(predicate: Callable[[int, int], bool]) -> List[Optional[float]]:
            out: List[Optional[float]] = []
            for c, p, e in zip(coh, rp, eff):
                # Drop rows where the filter predicate is unknown
                # (skipped / null score on the gating dimension).
                if c is None or p is None or e is None:
                    out.append(None)
                    continue
                out.append(e if predicate(c, p) else None)
            return out

        agg = StrengthAgg(
            strength=s,
            mean_eff_all=_safe_mean(eff),
            mean_eff_coh0=_safe_mean(filter_eff(lambda c, p: c == 0)),
            mean_eff_rp3=_safe_mean(filter_eff(lambda c, p: p == 3)),
            mean_eff_coh0_rp3=_safe_mean(
                filter_eff(lambda c, p: c == 0 and p == 3)
            ),
            n_total=len(recs),
            n_with_eff=sum(1 for e in eff if e is not None),
            n_coh0=sum(1 for c in coh if c == 0),
        )
        aggs.append(agg)

    summary_path = cell_dir / "summary.json"
    up_reason = None
    if summary_path.exists():
        try:
            with open(summary_path, encoding="utf-8") as f:
                summary = json.load(f)
            up_reason = summary.get("up_blocked_reason")
        except (OSError, json.JSONDecodeError):
            pass

    return CellSign(
        slot=slot, layer=layer, sign=sign,
        aggs=aggs, up_blocked_reason=up_reason,
    )


def gather_cells(experiment_dir: Path) -> List[CellSign]:
    """Find every ``s<slot>_l<layer>_<sign>`` subdir under
    ``experiment_dir`` and aggregate it.  Sorted by (slot, layer, sign)
    for stable legend ordering.
    """
    out: List[CellSign] = []
    for d in experiment_dir.iterdir():
        if not d.is_dir():
            continue
        name = d.name
        # Pattern: s<digits>_l<digits>_(+1|-1)
        if not (name.startswith("s") and "_l" in name and "_" in name[name.index("_l"):]):
            continue
        try:
            cs = aggregate_cell_sign(d)
        except (ValueError, IndexError) as e:
            logger.warning(f"skipping {d}: {e}")
            continue
        if cs.aggs:
            out.append(cs)
    out.sort(key=lambda c: (c.slot, c.layer, c.sign))
    return out


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

LINESTYLES = {
    "all":  "solid",
    "coh0": (0, (5, 2)),       # dashed
    "rp3":  (0, (1, 2)),       # dotted
    "both": (0, (3, 2, 1, 2)),  # dash-dot
}

FILTER_LABEL = {
    "all":  "(a) all",
    "coh0": "(b) coh=0",
    "rp3":  "(c) rp=3",
    "both": "(d) coh=0 & rp=3",
}


def _x_steps_from_cliff(n_strengths: int) -> np.ndarray:
    """Convert step-index (0..N-1, ascending strength) to "steps
    remaining to incoherence" (N-1..0).  The cell's largest strength
    -- the incoherence cliff -- sits at x=0; the smallest at x=N-1.
    """
    return np.arange(n_strengths - 1, -1, -1)


def plot_response_curves(
    cells: List[CellSign],
    *,
    output_path: Path,
    title: str,
) -> None:
    """Render one figure with two side-by-side subplots (sign=+1 left,
    sign=-1 right).  Color encodes (slot, layer); linestyle encodes
    filter regime.
    """
    # Distinct colour per (slot, layer).  Tab10 covers 7 comfortably.
    unique_cells = sorted({(c.slot, c.layer) for c in cells})
    cmap = plt.get_cmap("tab10")
    color_for_cell = {
        (s, l): cmap(i % 10) for i, (s, l) in enumerate(unique_cells)
    }

    fig, axes = plt.subplots(
        1, 2, figsize=(16, 8), sharey=True,
    )
    sign_label = {+1: "sign = +1  (toward neg pole)",
                  -1: "sign = -1  (toward pos pole)"}

    for ax, sign in zip(axes, (+1, -1)):
        cell_signs_here = [c for c in cells if c.sign == sign]
        for cs in cell_signs_here:
            x = _x_steps_from_cliff(len(cs.aggs))
            color = color_for_cell[(cs.slot, cs.layer)]
            base_label = f"s{cs.slot}_l{cs.layer}"
            for filt_key in ("all", "coh0", "rp3", "both"):
                ys = [_filter_value(a, filt_key) for a in cs.aggs]
                # Plot; matplotlib handles None as NaN -> gaps in line.
                ys_arr = np.array([np.nan if y is None else y for y in ys])
                # The legend label only carries the cell name for the
                # "all" variant; otherwise the per-filter legend would
                # double up to 28 entries per subplot.
                label = base_label if filt_key == "all" else None
                ax.plot(
                    x, ys_arr,
                    color=color,
                    linestyle=LINESTYLES[filt_key],
                    linewidth=1.6 if filt_key == "all" else 1.0,
                    alpha=0.95 if filt_key == "all" else 0.75,
                    label=label,
                )
        ax.axhline(0.0, color="black", linewidth=0.6, alpha=0.4)
        # x=0 (cliff) on the RIGHT; increasing x to the LEFT.
        ax.invert_xaxis()
        ax.set_xlabel("Steps remaining to incoherence cliff (0 = cliff)")
        ax.set_title(sign_label[sign])
        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Mean effect score")

    # Two legends per figure: one for cell colours (on the left subplot),
    # one for filter linestyles (on the right subplot) so the user
    # doesn't need to mentally cross-reference.
    handles_cells, labels_cells = axes[0].get_legend_handles_labels()
    axes[0].legend(
        handles_cells, labels_cells,
        title="cell  (slot, layer)",
        loc="upper left",
        fontsize=8,
    )
    # Filter-style legend on the right subplot.
    style_handles = [
        plt.Line2D([0], [0], color="black",
                   linestyle=LINESTYLES[k], linewidth=1.6 if k == "all" else 1.0,
                   alpha=0.95 if k == "all" else 0.75,
                   label=FILTER_LABEL[k])
        for k in ("all", "coh0", "rp3", "both")
    ]
    axes[1].legend(
        handles=style_handles,
        title="filter",
        loc="upper left",
        fontsize=8,
    )

    fig.suptitle(title)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Project convention: every tracked-script plot embeds PNG-text-chunk
    # provenance via assistant_axis.png_metadata (title + uv-run invocation
    # + ISO-8601 timestamp + git SHA).  See AGENT_NOTES.md "Plot
    # Provenance Metadata".
    fig.savefig(
        output_path, dpi=140, bbox_inches="tight",
        metadata=png_metadata(title=title.splitlines()[0]),
    )
    logger.info(f"wrote {output_path}")


def _filter_value(agg: StrengthAgg, key: str) -> Optional[float]:
    return {
        "all":  agg.mean_eff_all,
        "coh0": agg.mean_eff_coh0,
        "rp3":  agg.mean_eff_rp3,
        "both": agg.mean_eff_coh0_rp3,
    }[key]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("experiment_dir", type=Path,
                   help="Steering experiment output directory.")
    p.add_argument("--output", "-o", type=Path, default=None,
                   help="Output PNG path.  Default: "
                        "<experiment_dir>/response_curves.png")
    p.add_argument("--title", type=str, default=None,
                   help="Plot title (default: experiment_id).")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    if not args.experiment_dir.exists():
        logger.error(f"missing: {args.experiment_dir}")
        return 2

    cells = gather_cells(args.experiment_dir)
    if not cells:
        logger.error(f"no cell subdirs found under {args.experiment_dir}")
        return 1

    config_path = args.experiment_dir / "config.json"
    experiment_id = args.experiment_dir.name
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                experiment_id = json.load(f).get("experiment_id", experiment_id)
        except (OSError, json.JSONDecodeError):
            pass

    title = args.title or f"{experiment_id}: per-cell response curves"
    output_path = args.output or (args.experiment_dir / "response_curves.png")

    logger.info(
        f"found {len(cells)} (cell, sign) groups across "
        f"{len({(c.slot, c.layer) for c in cells})} cells "
        f"for {experiment_id}"
    )
    plot_response_curves(cells, output_path=output_path, title=title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
