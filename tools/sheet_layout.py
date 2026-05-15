"""Pure data shaping for ``tools/steering_to_gsheet.py``.

Given a steering experiment directory, build a :class:`TabPayload`
that fully describes a Google Sheets tab (cell grid, frozen rows /
cols, dimension groups, conditional formats, column widths, plus the
list of "blocks" the tool wrote so append/replace logic can find them
by sentinel later).

This module deliberately has **no Google dependencies** so it stays
unit-testable without OAuth / network.  The CLI module translates the
returned :class:`TabPayload` into ``gspread`` + ``batchUpdate`` calls.

Block layout (one block per ``(slot, layer, positions_mode)`` cell;
multi-cell experiments produce multiple blocks):

    Row 1 (frozen): persona system prompt
    Row 2 (frozen): per-column labels + per-question question text
    Row 3 (frozen): baseline responses (sign=0, strength=0)
    Row 4         : block header (sentinel + human-readable summary)
    Row 5..K      : signed-strength data rows (negative -> positive)
    Row K+1       : block header for the next cell (multi-cell only)
    Row K+2..M    : next block's data rows
    ...

Columns:

    A : signed_strength
    B : mean_coh        (per-row mean across all questions)
    C : mean_rp
    D : mean_eff_signed
    E : mean_abs_eff
    F..I    : q0_response, q0_coh, q0_rp, q0_eff
    J..M    : q1_response, q1_coh, q1_rp, q1_eff
    ...
    (5 + 4 * N_questions columns total)

Aggregates (cols B-E) and per-question score triplets (q*_coh / q*_rp /
q*_eff) are placed in collapsible dimension groups so the user can
toggle between "responses only" and "full analytics" views.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Constants -- layout + theming
# ---------------------------------------------------------------------------

AGG_COLS = ("signed_strength", "mean_coh", "mean_rp",
            "mean_eff_signed", "mean_abs_eff")
N_AGG_COLS = len(AGG_COLS)  # 5

PER_QUESTION_COL_NAMES = ("response", "coh", "rp", "eff")
N_PER_QUESTION_COLS = len(PER_QUESTION_COL_NAMES)  # 4

# Frozen header is exactly persona / questions / baseline.
FROZEN_ROWS = 3
# Strength col always visible as you scroll right.
FROZEN_COLS = 1

# Column widths in pixels.  Sheets default is ~100px; responses get a
# big wrap-on column; scores get narrow cells.
WIDTH_STRENGTH_PX = 80
WIDTH_AGG_PX = 80
WIDTH_RESPONSE_PX = 400
WIDTH_SCORE_PX = 60

# Pixel widths keyed by column "kind"; used both for layout-time width
# requests and for sanity checks in tests.
WIDTH_BY_KIND: Dict[str, int] = {
    "signed_strength": WIDTH_STRENGTH_PX,
    "mean_coh": WIDTH_AGG_PX,
    "mean_rp": WIDTH_AGG_PX,
    "mean_eff_signed": WIDTH_AGG_PX,
    "mean_abs_eff": WIDTH_AGG_PX,
    "response": WIDTH_RESPONSE_PX,
    "coh": WIDTH_SCORE_PX,
    "rp": WIDTH_SCORE_PX,
    "eff": WIDTH_SCORE_PX,
}

# Graded conditional-format thresholds.  Mirror the rubric levels:
# coherence 0/1/2/3 → faint/medium/strong shading above 0.5/1.0/1.5;
# effect ±1/2/3 → faint/medium/strong sign-coloured shading.
COH_THRESHOLDS = (0.5, 1.0, 1.5)
EFF_ABS_THRESHOLDS = (1.0, 2.0, 3.0)
RP_LOW_THRESHOLD = 1.0  # rp ≤ 1 = persona drift

# RGB tuples in 0..1 floats (Sheets uses normalized colors).
COLOR_PINK = (
    (1.00, 0.92, 0.93),  # faint
    (1.00, 0.80, 0.83),  # medium
    (1.00, 0.65, 0.70),  # strong
)
COLOR_GREEN = (
    (0.90, 0.97, 0.90),
    (0.75, 0.92, 0.75),
    (0.55, 0.85, 0.55),
)
COLOR_BLUE = (
    (0.90, 0.95, 1.00),
    (0.75, 0.87, 1.00),
    (0.55, 0.78, 1.00),
)
COLOR_ORANGE_FAINT = (1.00, 0.93, 0.80)
COLOR_GRAY_TEXT = (0.50, 0.50, 0.50)  # gray italic for [skipped] placeholder

SKIPPED_PLACEHOLDER = "[skipped — incoherent]"


# ---------------------------------------------------------------------------
# Public payload dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CondFormat:
    """A single conditional-formatting rule (numeric comparison + fill).

    Attributes:
        row_start, row_end: 0-indexed, end-exclusive (Sheets-API style).
        col_start, col_end: 0-indexed, end-exclusive.
        condition_type: "NUMBER_GREATER_THAN_EQ", "NUMBER_LESS_THAN_EQ",
            "NUMBER_BETWEEN" (semantics matches the Sheets ConditionType
            enum -- the CLI maps these strings 1:1).
        values: numeric thresholds.  Length-1 for GTE/LTE, length-2 for
            BETWEEN (inclusive).
        bg_color: (r, g, b) in 0..1 floats.
        italic: whether matching cells should be italicized (used for
            skipped-row gray italic styling).
        text_color: optional (r, g, b); None preserves default text color.
    """

    row_start: int
    row_end: int
    col_start: int
    col_end: int
    condition_type: str
    values: Tuple[float, ...]
    bg_color: Optional[Tuple[float, float, float]] = None
    italic: bool = False
    text_color: Optional[Tuple[float, float, float]] = None


@dataclass(frozen=True)
class DimGroup:
    """A collapsible dimension group (row or column band).

    Attributes:
        dim: "ROWS" or "COLUMNS".
        start, end: 0-indexed, end-exclusive in the corresponding
            dimension.  Matches the Sheets API ``DimensionRange``.
        collapsed: initial collapsed state.
    """

    dim: str
    start: int
    end: int
    collapsed: bool = False


@dataclass(frozen=True)
class ColumnWidth:
    col: int  # 0-indexed
    width_px: int


@dataclass(frozen=True)
class BlockSpec:
    """Where a single block lives in the tab + how to recognize it
    later for replace-on-rerun.

    A "block" corresponds to one ``(slot, layer, positions_mode)``
    steering cell within the experiment.  Multi-cell experiments
    produce one BlockSpec per cell; the block_sentinel uniquely
    identifies the (experiment_id, slot, layer, positions_mode)
    combination so a later export of the same experiment_id can find
    and replace this block without touching siblings.
    """

    experiment_id: str
    slot: int
    layer: int
    positions_mode: str
    header_row: int     # 0-indexed row of the block header
    data_row_start: int  # 0-indexed (inclusive)
    data_row_end: int    # 0-indexed (exclusive)
    sentinel: str        # "[block:exp_id/s3_l25/all]" placed in col A of header_row


@dataclass(frozen=True)
class TabPayload:
    """Everything needed to render one experiment_dir's worth of data
    as a Sheets tab section.

    The CLI takes one TabPayload and either:
      * appends it to a fresh tab (writes frozen rows + every block), or
      * merges into an existing tab per ``--replace-experiment-blocks``
        semantics (preserves frozen rows, drops + reinserts blocks
        whose sentinel matches the new experiment_id).
    """

    values: List[List[Any]]
    frozen_rows: int
    frozen_cols: int
    dim_groups: List[DimGroup]
    cond_formats: List[CondFormat]
    widths: List[ColumnWidth]
    blocks: List[BlockSpec]
    n_questions: int
    persona_prompt: str
    questions: List[str]
    baseline_responses: List[str]  # indexed by question_idx; "" if missing
    tab_name: str
    default_spreadsheet_name: str


# ---------------------------------------------------------------------------
# Block sentinel
# ---------------------------------------------------------------------------

def make_block_sentinel(
    experiment_id: str, slot: int, layer: int, positions_mode: str
) -> str:
    """Canonical sentinel string placed in col A of a block's header row.

    Format: ``[block:<exp_id>/s<slot>_l<layer>/<positions_mode>]``.
    Unique per (experiment_id, slot, layer, positions_mode) so
    --replace-experiment-blocks can scan column A on rerun and find
    exactly the rows to drop.
    """
    return f"[block:{experiment_id}/s{slot}_l{layer}/{positions_mode}]"


# ---------------------------------------------------------------------------
# Default names
# ---------------------------------------------------------------------------

def default_tab_name(persona_role: str, pos_label: str, neg_label: str) -> str:
    """e.g. "architect ecocentric_anthropocentric" -- space between role
    and the axis-pair, underscore between poles.  Lowercased and
    whitespace-collapsed for stable lookups.
    """
    return f"{persona_role} {pos_label}_{neg_label}".strip().lower()


def default_spreadsheet_name(experiment_ids: Sequence[str]) -> str:
    """Best-effort default for ``--spreadsheet-name`` when the user
    doesn't pass one.  Falls back to the longest common-prefix of the
    experiment_ids (with trailing underscores stripped), then a generic
    fallback.  Caller can always override with --spreadsheet-name.
    """
    if not experiment_ids:
        return "Steering experiments"
    if len(experiment_ids) == 1:
        return f"Steering: {experiment_ids[0]}"
    # Common prefix
    prefix = experiment_ids[0]
    for eid in experiment_ids[1:]:
        # Walk back until prefix is shared
        while not eid.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                break
    prefix = prefix.rstrip("_-")
    if prefix:
        return f"Steering: {prefix}*"
    return "Steering experiments"


# ---------------------------------------------------------------------------
# Disk readers
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


def _read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Score extractors (tolerant of partial / null judges)
# ---------------------------------------------------------------------------

def _coh_score(rec: Dict[str, Any]) -> Optional[float]:
    judges = rec.get("judges") or {}
    coh = judges.get("coherence")
    if not coh:
        return None
    s = coh.get("score")
    return None if s is None else float(s)


def _persona_score(rec: Dict[str, Any]) -> Optional[float]:
    judges = rec.get("judges") or {}
    p = judges.get("persona")
    if not p:
        return None
    if p.get("skipped_due_to_strength_mean_coh"):
        return None
    s = p.get("score")
    return None if s is None else float(s)


def _effect_score(rec: Dict[str, Any]) -> Optional[float]:
    judges = rec.get("judges") or {}
    e = judges.get("effect")
    if not e:
        return None
    if e.get("skipped_due_to_strength_mean_coh"):
        return None
    s = e.get("combined")
    return None if s is None else float(s)


def _persona_skipped(rec: Dict[str, Any]) -> bool:
    judges = rec.get("judges") or {}
    p = judges.get("persona") or {}
    return bool(p.get("skipped_due_to_strength_mean_coh"))


def _effect_skipped(rec: Dict[str, Any]) -> bool:
    judges = rec.get("judges") or {}
    e = judges.get("effect") or {}
    return bool(e.get("skipped_due_to_strength_mean_coh"))


def _safe_mean(xs: Sequence[Optional[float]]) -> Optional[float]:
    """Mean of the non-None scores, or None if all are missing."""
    filt = [x for x in xs if x is not None]
    return mean(filt) if filt else None


# ---------------------------------------------------------------------------
# build_tab -- the main entry point
# ---------------------------------------------------------------------------

def build_tab(
    experiment_dir: Path,
    *,
    tab_name_override: Optional[str] = None,
    spreadsheet_name_override: Optional[str] = None,
) -> TabPayload:
    """Build a :class:`TabPayload` from one experiment's output directory.

    The experiment_dir is expected to contain:
        config.json
        questions.json
        persona_system_prompt.txt
        baselines/records.jsonl
        s<slot>_l<layer>_<+1|-1>/{records.jsonl,summary.json}    (one per cell-sign)

    Cells that are missing a summary.json (still in-flight) are
    skipped with a warning encoded as a single-line block-header so
    the tab still renders; rerunning after the cell completes will
    replace that placeholder block.
    """
    experiment_dir = Path(experiment_dir)
    config = _read_json(experiment_dir / "config.json")
    experiment_id = config.get("experiment_id", experiment_dir.name)
    persona_prompt = (experiment_dir / "persona_system_prompt.txt").read_text().strip()
    questions = _read_json(experiment_dir / "questions.json")
    if isinstance(questions, dict):
        # Tolerate the {"questions": [...]} variant.
        questions = questions.get("questions", [])
    if not isinstance(questions, list):
        raise ValueError(
            f"{experiment_dir}/questions.json must be a list of strings "
            f"or {{\"questions\": [...]}}"
        )
    n_questions = len(questions)

    # Default names from config.
    axis_source = config.get("axis_source", {})
    pos_label = str(axis_source.get("role_from", "pos"))
    neg_label = str(axis_source.get("role_to", "neg"))
    persona_role = str(config.get("persona", {}).get("role", "persona"))
    tab_name = tab_name_override or default_tab_name(
        persona_role, pos_label, neg_label
    )
    spreadsheet_name = (
        spreadsheet_name_override
        or default_spreadsheet_name([experiment_id])
    )

    # Baselines (used in row 3 and as fallback for missing baseline_response).
    baseline_recs = _read_jsonl(experiment_dir / "baselines" / "records.jsonl")
    baseline_by_q: Dict[int, str] = {}
    for r in baseline_recs:
        try:
            baseline_by_q[int(r["question_idx"])] = str(r.get("response", ""))
        except (KeyError, ValueError, TypeError):
            continue
    baseline_responses = [baseline_by_q.get(i, "") for i in range(n_questions)]

    # ------------------------------------------------------------------
    # Build the column header (row 2 = labels + question texts).
    # ------------------------------------------------------------------
    header_row = _make_header_row(n_questions, questions)

    # ------------------------------------------------------------------
    # Build rows 1 (persona) and 3 (baseline).
    # ------------------------------------------------------------------
    persona_row = _make_persona_row(persona_prompt, n_questions)
    baseline_row = _make_baseline_row(baseline_responses, n_questions)

    # ------------------------------------------------------------------
    # Build blocks (one per cell = (slot, layer, positions_mode)).
    # ------------------------------------------------------------------
    positions_mode = str(config.get("positions_mode", "all"))
    cells_cfg = config.get("cells", [])

    block_rows: List[List[Any]] = []
    blocks: List[BlockSpec] = []

    cursor = FROZEN_ROWS  # next absolute row index to write into

    for cell_cfg in cells_cfg:
        slot = int(cell_cfg["slot"])
        layer = int(cell_cfg["layer"])

        block_block = _build_block(
            experiment_dir=experiment_dir,
            experiment_id=experiment_id,
            slot=slot,
            layer=layer,
            positions_mode=positions_mode,
            n_questions=n_questions,
            start_row_abs=cursor,
        )
        block_rows.extend(block_block.rows)
        blocks.append(block_block.spec)
        cursor += len(block_block.rows)

    # ------------------------------------------------------------------
    # Stitch together the grid.
    # ------------------------------------------------------------------
    n_cols = N_AGG_COLS + N_PER_QUESTION_COLS * n_questions
    values: List[List[Any]] = [persona_row, header_row, baseline_row]
    values.extend(block_rows)
    # Defensive: pad every row to n_cols (Sheets is happy with ragged
    # rows but downstream CSV writers and conditional-format ranges
    # expect a rectangular grid).
    values = [pad_row(r, n_cols) for r in values]

    # ------------------------------------------------------------------
    # Conditional formats: column-spanning rules over the whole data
    # region.  Block-header rows have non-numeric content in score
    # columns, so numeric comparison rules naturally don't match them
    # -- much cheaper than emitting per-row rules and well under
    # Sheets' practical conditional-format rule cap.
    # ------------------------------------------------------------------
    total_rows = len(values)
    cond_formats: List[CondFormat] = tab_wide_cond_formats(
        n_questions=n_questions,
        data_row_start=FROZEN_ROWS,
        data_row_end=total_rows,
    )

    # ------------------------------------------------------------------
    # Dimension groups (collapsible bands of columns).
    # ------------------------------------------------------------------
    dim_groups: List[DimGroup] = [
        # Outer: per-strength aggregates (mean_coh..mean_abs_eff), cols B-E.
        DimGroup(dim="COLUMNS", start=1, end=N_AGG_COLS, collapsed=False),
    ]
    # Per-question inner group: q*_coh + q*_rp + q*_eff (3 narrow cols
    # immediately after the response col).  Leaves q*_response visible
    # when the group is collapsed.
    for q in range(n_questions):
        q_start = N_AGG_COLS + N_PER_QUESTION_COLS * q
        # cols are [response, coh, rp, eff]; group the score trio.
        dim_groups.append(DimGroup(
            dim="COLUMNS",
            start=q_start + 1,  # skip response
            end=q_start + N_PER_QUESTION_COLS,
            collapsed=False,
        ))

    # ------------------------------------------------------------------
    # Column widths.
    # ------------------------------------------------------------------
    widths: List[ColumnWidth] = [
        ColumnWidth(col=0, width_px=WIDTH_BY_KIND["signed_strength"]),
        ColumnWidth(col=1, width_px=WIDTH_BY_KIND["mean_coh"]),
        ColumnWidth(col=2, width_px=WIDTH_BY_KIND["mean_rp"]),
        ColumnWidth(col=3, width_px=WIDTH_BY_KIND["mean_eff_signed"]),
        ColumnWidth(col=4, width_px=WIDTH_BY_KIND["mean_abs_eff"]),
    ]
    for q in range(n_questions):
        base = N_AGG_COLS + N_PER_QUESTION_COLS * q
        widths.extend([
            ColumnWidth(col=base + 0, width_px=WIDTH_BY_KIND["response"]),
            ColumnWidth(col=base + 1, width_px=WIDTH_BY_KIND["coh"]),
            ColumnWidth(col=base + 2, width_px=WIDTH_BY_KIND["rp"]),
            ColumnWidth(col=base + 3, width_px=WIDTH_BY_KIND["eff"]),
        ])

    return TabPayload(
        values=values,
        frozen_rows=FROZEN_ROWS,
        frozen_cols=FROZEN_COLS,
        dim_groups=dim_groups,
        cond_formats=cond_formats,
        widths=widths,
        blocks=blocks,
        n_questions=n_questions,
        persona_prompt=persona_prompt,
        questions=list(questions),
        baseline_responses=baseline_responses,
        tab_name=tab_name,
        default_spreadsheet_name=spreadsheet_name,
    )


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _make_persona_row(persona_prompt: str, n_questions: int) -> List[Any]:
    """Row 1 -- persona system prompt.

    Col A holds the label "persona", col B holds the full prompt (text
    overflows into the empty agg + question cols when not collapsed,
    or wraps within col B if the user widens it).  Other cols empty.
    """
    n_cols = N_AGG_COLS + N_PER_QUESTION_COLS * n_questions
    row: List[Any] = ["persona"] + [""] * (n_cols - 1)
    if n_cols >= 2:
        row[1] = persona_prompt
    return row


def _make_header_row(n_questions: int, questions: Sequence[str]) -> List[Any]:
    """Row 2 -- per-column labels + per-question text.

    Cols A-E carry the aggregate names; for each question the response
    column carries the question text (long, wrap-on) and the score
    columns carry short tags ``coh`` / ``rp`` / ``eff``.
    """
    row: List[Any] = list(AGG_COLS)
    for q in range(n_questions):
        row.extend([
            questions[q] if q < len(questions) else "",
            "coh",
            "rp",
            "eff",
        ])
    return row


def _make_baseline_row(
    baseline_responses: Sequence[str], n_questions: int
) -> List[Any]:
    """Row 3 -- baseline responses (one per question).

    Aggregates are blank (baselines aren't judged); strength col carries
    the label "baseline" so the row is self-descriptive when scrolled
    to.
    """
    row: List[Any] = ["baseline", "", "", "", ""]
    for q in range(n_questions):
        resp = baseline_responses[q] if q < len(baseline_responses) else ""
        row.extend([resp, "", "", ""])
    return row


# ---------------------------------------------------------------------------
# Block builder
# ---------------------------------------------------------------------------

@dataclass
class _BlockBuild:
    rows: List[List[Any]]
    spec: BlockSpec


def _build_block(
    *,
    experiment_dir: Path,
    experiment_id: str,
    slot: int,
    layer: int,
    positions_mode: str,
    n_questions: int,
    start_row_abs: int,
) -> _BlockBuild:
    """Build one cell-block: header row + one data row per signed strength.

    Combines both signs (``s<slot>_l<layer>_+1`` and ``s<slot>_l<layer>_-1``)
    so the user sees a single continuous strength curve from
    -max to +max.  If only one sign was actually swept the block
    still renders cleanly.
    """
    pos_dir = experiment_dir / f"s{slot}_l{layer}_+1"
    neg_dir = experiment_dir / f"s{slot}_l{layer}_-1"
    pos_recs = _read_jsonl(pos_dir / "records.jsonl")
    neg_recs = _read_jsonl(neg_dir / "records.jsonl")
    pos_summary = _read_json(pos_dir / "summary.json") if (pos_dir / "summary.json").exists() else None
    neg_summary = _read_json(neg_dir / "summary.json") if (neg_dir / "summary.json").exists() else None

    sentinel = make_block_sentinel(
        experiment_id, slot, layer, positions_mode
    )
    header_summary = _block_header_summary(
        slot=slot, layer=layer, positions_mode=positions_mode,
        pos_summary=pos_summary, neg_summary=neg_summary,
    )
    header_row_cells: List[Any] = [sentinel, header_summary] + [""] * (
        N_AGG_COLS + N_PER_QUESTION_COLS * n_questions - 2
    )

    # Group records by (signed_strength).  Use the records' actual
    # strength field (already rounded to whatever the runner stored)
    # rather than re-deriving from a schedule, so legacy_unidirectional
    # and bidirectional both work without special-casing.
    by_signed_strength: Dict[float, List[Dict[str, Any]]] = {}
    for r in pos_recs:
        s = +1 * float(r.get("strength", 0.0))
        if s == 0.0:
            continue
        by_signed_strength.setdefault(s, []).append(r)
    for r in neg_recs:
        s = -1 * float(r.get("strength", 0.0))
        if s == 0.0:
            continue
        by_signed_strength.setdefault(s, []).append(r)

    signed_strengths = sorted(by_signed_strength.keys())

    data_rows: List[List[Any]] = []
    data_row_start_abs = start_row_abs + 1  # +1 to skip block header

    for s_signed in signed_strengths:
        recs = by_signed_strength[s_signed]
        # Map question_idx -> rec (assumes one rec per question per
        # signed-strength; multiple would be a runner bug, take the
        # last one in that case).
        rec_by_q: Dict[int, Dict[str, Any]] = {}
        for r in recs:
            try:
                rec_by_q[int(r["question_idx"])] = r
            except (KeyError, ValueError, TypeError):
                continue

        row = _strength_data_row(
            signed_strength=s_signed,
            n_questions=n_questions,
            rec_by_q=rec_by_q,
        )
        data_rows.append(row)

    spec = BlockSpec(
        experiment_id=experiment_id,
        slot=slot,
        layer=layer,
        positions_mode=positions_mode,
        header_row=start_row_abs,
        data_row_start=data_row_start_abs,
        data_row_end=data_row_start_abs + len(data_rows),
        sentinel=sentinel,
    )

    rows: List[List[Any]] = [header_row_cells] + data_rows
    return _BlockBuild(rows=rows, spec=spec)


def _block_header_summary(
    *, slot: int, layer: int, positions_mode: str,
    pos_summary: Optional[Dict[str, Any]],
    neg_summary: Optional[Dict[str, Any]],
) -> str:
    """One-line human-readable description of a cell block.

    Pulls the scan parameters from whichever summary.json is available
    (preferring +1's), and surfaces the up/down stop strengths +
    reasons for both signs so the user can see at a glance whether
    each direction hit its incoherence ceiling or its sub-threshold
    floor.
    """
    s = pos_summary or neg_summary or {}
    scan_mode = s.get("scan_mode", "?")
    s_init = s.get("s_init")

    def _stop_str(summary: Optional[Dict[str, Any]], key_strength: str,
                  key_reason: str, default: str = "") -> str:
        if not summary:
            return default
        v = summary.get(key_strength)
        r = summary.get(key_reason)
        if v is None:
            return default
        return f"{v:.3g}({r})"

    parts = [
        f"slot={slot}",
        f"layer={layer}",
        f"positions={positions_mode}",
        f"scan={scan_mode}",
    ]
    if s_init is not None:
        parts.append(f"s_init=±{s_init:.3g}")
    pos_up = _stop_str(pos_summary, "up_blocked_at_strength", "up_blocked_reason")
    pos_down = _stop_str(pos_summary, "down_blocked_at_strength", "down_blocked_reason")
    neg_up = _stop_str(neg_summary, "up_blocked_at_strength", "up_blocked_reason")
    neg_down = _stop_str(neg_summary, "down_blocked_at_strength", "down_blocked_reason")
    if pos_up:
        parts.append(f"pos_up={pos_up}")
    if pos_down:
        parts.append(f"pos_down={pos_down}")
    if neg_up:
        parts.append(f"neg_up={neg_up}")
    if neg_down:
        parts.append(f"neg_down={neg_down}")
    return "  ".join(parts)


def _strength_data_row(
    *, signed_strength: float, n_questions: int,
    rec_by_q: Dict[int, Dict[str, Any]],
) -> List[Any]:
    """One row of the block: signed_strength, aggregates, per-q data."""
    cohs = [_coh_score(rec_by_q.get(q, {})) for q in range(n_questions)]
    rps = [_persona_score(rec_by_q.get(q, {})) for q in range(n_questions)]
    effs = [_effect_score(rec_by_q.get(q, {})) for q in range(n_questions)]

    mean_coh = _safe_mean(cohs)
    mean_rp = _safe_mean(rps)
    mean_eff = _safe_mean(effs)
    mean_abs_eff = _safe_mean([
        abs(e) if e is not None else None for e in effs
    ])

    row: List[Any] = [
        signed_strength,
        _round_or_blank(mean_coh, 2),
        _round_or_blank(mean_rp, 2),
        _round_or_blank(mean_eff, 2),
        _round_or_blank(mean_abs_eff, 2),
    ]
    for q in range(n_questions):
        rec = rec_by_q.get(q)
        if rec is None:
            row.extend(["", "", "", ""])
            continue
        skipped = _persona_skipped(rec) or _effect_skipped(rec)
        response = (
            SKIPPED_PLACEHOLDER if skipped else str(rec.get("response", ""))
        )
        coh = cohs[q]
        rp = rps[q]
        eff = effs[q]
        row.extend([
            response,
            _round_or_blank(coh, 2),
            _round_or_blank(rp, 2),
            _round_or_blank(eff, 2),
        ])
    return row


def _round_or_blank(x: Optional[float], digits: int) -> Any:
    """Round to ``digits`` if non-None, else "" so the cell renders empty.

    Avoids leaving stray ``None`` literals in the CSV / Sheets payload.
    """
    if x is None:
        return ""
    return round(float(x), digits)


# ---------------------------------------------------------------------------
# Conditional-format helpers
# ---------------------------------------------------------------------------

def tab_wide_cond_formats(
    *, n_questions: int, data_row_start: int, data_row_end: int,
) -> List[CondFormat]:
    """Generate column-spanning conditional-format rules.

    One rule per (column-kind, threshold) covering the whole data row
    range.  Block-header rows have non-numeric content in score
    columns (col A holds the sentinel string, col B holds the human-
    readable summary text, score-positioned cells are empty), so
    numeric comparison rules naturally skip them -- much cheaper than
    emitting per-row rules and well within Sheets' practical
    conditional-format rule cap.

    The :class:`TEXT_EQ` placeholder rule for the response columns
    fires only where the cell text literally equals
    ``[skipped — incoherent]``, which is exactly the skipped-row
    placeholder, so block-header rows are also unaffected.

    Rules added:
      - mean_coh (col B): graded pink at >= 0.5 / 1.0 / 1.5.
      - mean_rp (col C): faint orange at <= 1.
      - mean_eff_signed (col D): sign-coloured graded at |x| >= 1/2/3.
      - q*_coh, q*_rp, q*_eff: same set per question.
      - q*_response: italic gray on TEXT_EQ placeholder.
    """
    out: List[CondFormat] = []
    r0, r1 = data_row_start, data_row_end

    # Aggregate columns.
    out.extend(_graded_pink_rules(r0, r1, col_start=1, col_end=2))
    out.append(CondFormat(
        row_start=r0, row_end=r1, col_start=2, col_end=3,
        condition_type="NUMBER_LESS_THAN_EQ",
        values=(RP_LOW_THRESHOLD,), bg_color=COLOR_ORANGE_FAINT,
    ))
    out.extend(_signed_eff_rules(r0, r1, col_start=3, col_end=4))

    # Per-question score columns.
    for q in range(n_questions):
        base = N_AGG_COLS + N_PER_QUESTION_COLS * q
        # response col -- skipped placeholder italic styling.
        out.append(CondFormat(
            row_start=r0, row_end=r1,
            col_start=base, col_end=base + 1,
            condition_type="TEXT_EQ",
            values=(SKIPPED_PLACEHOLDER,),  # type: ignore[arg-type]
            bg_color=None,
            italic=True,
            text_color=COLOR_GRAY_TEXT,
        ))
        out.extend(_graded_pink_rules(
            r0, r1, col_start=base + 1, col_end=base + 2,
        ))
        out.append(CondFormat(
            row_start=r0, row_end=r1,
            col_start=base + 2, col_end=base + 3,
            condition_type="NUMBER_LESS_THAN_EQ",
            values=(RP_LOW_THRESHOLD,),
            bg_color=COLOR_ORANGE_FAINT,
        ))
        out.extend(_signed_eff_rules(
            r0, r1, col_start=base + 3, col_end=base + 4,
        ))
    return out


def _graded_pink_rules(
    row_start: int, row_end: int, *, col_start: int, col_end: int,
) -> List[CondFormat]:
    """3 graded-pink rules: faint @ ≥ 0.5, medium @ ≥ 1.0, strong @ ≥ 1.5.

    Sheets applies the LAST matching rule, so we register them in
    ascending threshold order; cells with coh ≥ 1.5 end up with the
    strong fill (most recent rule that matched).
    """
    return [
        CondFormat(
            row_start=row_start, row_end=row_end,
            col_start=col_start, col_end=col_end,
            condition_type="NUMBER_GREATER_THAN_EQ",
            values=(t,),
            bg_color=c,
        )
        for t, c in zip(COH_THRESHOLDS, COLOR_PINK)
    ]


def _signed_eff_rules(
    row_start: int, row_end: int, *, col_start: int, col_end: int,
) -> List[CondFormat]:
    """6 rules: faint/medium/strong green for eff ≥ 1/2/3, same for
    blue at eff ≤ -1/-2/-3.  Registered in ascending |threshold|
    order; Sheets' last-match-wins semantics gives the saturated
    shade for the largest-magnitude scores.
    """
    rules: List[CondFormat] = []
    for t, c in zip(EFF_ABS_THRESHOLDS, COLOR_GREEN):
        rules.append(CondFormat(
            row_start=row_start, row_end=row_end,
            col_start=col_start, col_end=col_end,
            condition_type="NUMBER_GREATER_THAN_EQ",
            values=(t,),
            bg_color=c,
        ))
    for t, c in zip(EFF_ABS_THRESHOLDS, COLOR_BLUE):
        rules.append(CondFormat(
            row_start=row_start, row_end=row_end,
            col_start=col_start, col_end=col_end,
            condition_type="NUMBER_LESS_THAN_EQ",
            values=(-t,),
            bg_color=c,
        ))
    return rules


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def pad_row(row: List[Any], n_cols: int) -> List[Any]:
    """Pad / truncate a row to exactly ``n_cols`` columns.  Used both
    internally and by the CLI when merging existing-tab rows back into
    the rebuilt grid.
    """
    if len(row) >= n_cols:
        return row[:n_cols]
    return row + [""] * (n_cols - len(row))
