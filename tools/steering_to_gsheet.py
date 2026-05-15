"""Export a steering experiment directory into a Google Sheets tab.

Two output paths:

  - ``--dry-run`` writes a local CSV of the cell grid (no Google
    auth required).  Useful for verifying the layout against real
    data before pushing to Sheets.

  - default (online): authenticates with Google via
    :func:`assistant_axis.gsheet_auth.get_client`, opens (or creates)
    a spreadsheet, opens (or creates) a tab, writes the cell grid,
    and applies frozen rows / column groups / conditional formats /
    column widths via the Sheets ``batchUpdate`` API.

Rerun semantics on a non-empty tab (default
``--replace-experiment-blocks``):

  - The tool scans col A of the existing tab for block sentinels
    matching the current experiment_id and drops those rows.
  - Surviving blocks (other experiments in the same tab) are kept
    in place; their values are preserved verbatim.
  - The new payload's blocks are appended at the bottom.
  - Conditional formats and column widths are reapplied to the
    full (kept + new) data range so styling stays consistent.

``--append-only`` keeps every existing block; ``--wipe-tab`` clears
the tab first.

Example:

    uv run python tools/steering_to_gsheet.py \\
        /workspace/outputs/qwen-3-32b/steering/architect_ecocentric_v2 \\
        --spreadsheet-name "Steering experiments May 2026" \\
        [--tab-name "architect ecocentric_anthropocentric"] \\
        [--replace-experiment-blocks | --append-only | --wipe-tab]

See ``AGENT_NOTES.md`` ("Exporting steering experiments to Google
Sheets") for the one-time OAuth setup.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools import sheet_layout as sl

logger = logging.getLogger("steering_to_gsheet")


# ---------------------------------------------------------------------------
# CSV (dry-run) writer
# ---------------------------------------------------------------------------

def write_csv(payload: sl.TabPayload, out_path: Path) -> None:
    """Write the cell grid as CSV for offline inspection.

    Only ``payload.values`` are emitted.  Frozen rows, dim groups,
    conditional formats, and column widths are echoed to stderr as a
    human-readable summary so the dry-run still surfaces all the
    layout decisions.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in payload.values:
            w.writerow(row)
    logger.info(f"wrote {len(payload.values)} rows x "
                f"{len(payload.values[0]) if payload.values else 0} cols "
                f"to {out_path}")

    summary = (
        f"tab_name: {payload.tab_name!r}\n"
        f"default_spreadsheet_name: {payload.default_spreadsheet_name!r}\n"
        f"frozen_rows: {payload.frozen_rows}, frozen_cols: {payload.frozen_cols}\n"
        f"n_questions: {payload.n_questions}, "
        f"n_blocks: {len(payload.blocks)}\n"
        f"dim_groups: {len(payload.dim_groups)} "
        f"(outer=1 + per-question={payload.n_questions})\n"
        f"cond_formats: {len(payload.cond_formats)}\n"
        f"widths: {len(payload.widths)}\n"
        f"blocks:\n"
    )
    for b in payload.blocks:
        summary += (
            f"  - {b.sentinel} -> rows {b.header_row}..{b.data_row_end} "
            f"(header {b.header_row}, data {b.data_row_start}..{b.data_row_end})\n"
        )
    sys.stderr.write(summary)


# ---------------------------------------------------------------------------
# Sheets push helpers (online path)
# ---------------------------------------------------------------------------

def _open_or_create_spreadsheet(client, *, spreadsheet_id: Optional[str],
                                 spreadsheet_name: str):
    """Resolve the target spreadsheet by id or by exact-name search.

    Falls back to creating a new spreadsheet (with ``spreadsheet_name``)
    when neither path resolves.  The drive.file scope only sees files
    the OAuth user created via this app, so the search space is small
    and unambiguous.
    """
    import gspread
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)
    try:
        return client.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        logger.info(f"spreadsheet {spreadsheet_name!r} not found; creating...")
        return client.create(spreadsheet_name)


def _open_or_create_worksheet(spreadsheet, tab_name: str, *, n_cols: int):
    """Resolve the target tab by name; create it (with adequate width)
    when missing.  We pre-size the new tab to ``n_cols`` so the first
    write doesn't trigger an auto-expand round-trip.
    """
    import gspread
    try:
        return spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        logger.info(f"tab {tab_name!r} not found in spreadsheet; creating...")
        # Start with 200 rows -- generous; sheets auto-expand as needed.
        return spreadsheet.add_worksheet(
            title=tab_name, rows=200, cols=max(26, n_cols),
        )


# ---------------------------------------------------------------------------
# Append/replace logic
# ---------------------------------------------------------------------------

def _scan_existing_blocks(
    existing_col_a: List[str],
) -> List[Tuple[int, str]]:
    """Return ``[(row_idx, sentinel), ...]`` for every block-header row
    found in column A of an existing tab.

    A "block-header row" is any row whose col A value matches the
    block-sentinel format ``[block:.../s\\d+_l\\d+/...]``.
    """
    import re
    # experiment_id, positions_mode: no whitespace, no '/', no ']'.
    # Real experiment_ids are filename-stem-like (e.g. architect_ecocentric_v2)
    # so this is the strictest pattern that still admits everything the
    # runner produces.
    pat = re.compile(r"^\[block:[^/\s\]]+/s\d+_l\d+/[^/\s\]]+\]$")
    return [(i, v) for i, v in enumerate(existing_col_a) if pat.match(v)]


def _block_row_ranges(
    existing_col_a: List[str],
    headers: List[Tuple[int, str]],
) -> List[Tuple[int, int, str]]:
    """Convert a list of block headers into ``[(start, end, sentinel), ...]``
    row ranges (start inclusive, end exclusive).  Each block's range
    spans from its header row to the next header row (or end of sheet).
    """
    out: List[Tuple[int, int, str]] = []
    n = len(existing_col_a)
    for i, (start, sentinel) in enumerate(headers):
        end = headers[i + 1][0] if i + 1 < len(headers) else n
        out.append((start, end, sentinel))
    return out


def _filter_blocks_to_keep(
    existing_block_ranges: List[Tuple[int, int, str]],
    current_experiment_id: str,
    mode: str,
) -> List[Tuple[int, int, str]]:
    """Pick which existing blocks survive the rerun.

    Args:
        mode: one of "replace_experiment_blocks", "append_only", "wipe_tab".
    """
    if mode == "wipe_tab":
        return []
    if mode == "append_only":
        return list(existing_block_ranges)
    # replace_experiment_blocks (default)
    prefix = f"[block:{current_experiment_id}/"
    return [b for b in existing_block_ranges if not b[2].startswith(prefix)]


def _validate_frozen_compatibility(
    existing_values: List[List[Any]],
    payload: sl.TabPayload,
) -> None:
    """Bail out loudly when an existing tab's frozen header doesn't
    match the new payload's (different questions or different baselines
    would silently misalign rerun blocks if we didn't check).

    Caller should drop into ``--wipe-tab`` if this raises and they
    actually want the new header.
    """
    if len(existing_values) < sl.FROZEN_ROWS:
        return  # tab is empty / fresh -- compatible
    # Row 2 = question header (labels + question texts).
    # Compare q text cols only -- labels are static so they match by
    # construction.
    existing_header = existing_values[1] if len(existing_values) > 1 else []
    new_header = payload.values[1]
    n = len(new_header)
    if len(existing_header) < n:
        raise RuntimeError(
            "existing tab has fewer columns than new payload "
            f"({len(existing_header)} vs {n}); "
            "questions changed -- pass --wipe-tab to overwrite "
            "or re-run into a different tab"
        )
    # Compare question text cols only (positions q0_response col onward).
    for q in range(payload.n_questions):
        col = sl.N_AGG_COLS + sl.N_PER_QUESTION_COLS * q
        if str(existing_header[col]).strip() != str(new_header[col]).strip():
            raise RuntimeError(
                f"existing tab's question text at q{q} differs from new "
                f"payload's questions: existing={existing_header[col]!r}, "
                f"new={new_header[col]!r}.  Pass --wipe-tab to overwrite "
                f"the questions or re-run into a different tab."
            )


def _merge_payload_into_existing(
    payload: sl.TabPayload,
    existing_values: List[List[Any]],
    mode: str,
    current_experiment_id: str,
) -> Tuple[List[List[Any]], List[sl.BlockSpec]]:
    """Compute the final cell grid + block specs after merging.

    Strategy:
      1. Take frozen rows from the payload (those drive questions +
         baselines + persona; existing-tab equivalents are validated
         to match for non-wipe modes).
      2. Walk existing rows; keep block ranges that pass the filter,
         preserving their on-disk content as-is.
      3. Append the new payload's blocks at the end.
      4. Recompute BlockSpec row offsets so the returned blocks
         reflect their final positions in the merged grid (used by
         the formatting layer for conditional-format ranges).
    """
    if mode != "wipe_tab":
        _validate_frozen_compatibility(existing_values, payload)

    col_a = [str(r[0]) if r else "" for r in existing_values]
    headers = _scan_existing_blocks(col_a)
    existing_ranges = _block_row_ranges(col_a, headers)
    to_keep = _filter_blocks_to_keep(
        existing_ranges, current_experiment_id, mode
    )

    # Build the merged grid.
    n_cols = (
        sl.N_AGG_COLS + sl.N_PER_QUESTION_COLS * payload.n_questions
    )
    merged: List[List[Any]] = []
    # Frozen header from payload (canonical source of questions/baselines).
    merged.extend(payload.values[:sl.FROZEN_ROWS])

    kept_block_specs: List[sl.BlockSpec] = []
    cursor = sl.FROZEN_ROWS
    for start, end, sentinel in to_keep:
        # Pull rows from existing_values, pad to n_cols.
        for r in existing_values[start:end]:
            merged.append(sl.pad_row(list(r), n_cols))
        # Parse slot/layer/positions_mode + experiment_id back from sentinel
        # so kept block specs stay searchable on the next rerun.
        spec = _parse_block_sentinel_back(
            sentinel,
            header_row=cursor, data_row_start=cursor + 1,
            data_row_end=cursor + (end - start),
        )
        if spec is not None:
            kept_block_specs.append(spec)
        cursor += (end - start)

    # New payload blocks appended.  Their offsets need adjusting to the
    # merged grid's row indices.
    new_blocks_start = cursor
    payload_blocks_start_in_payload = sl.FROZEN_ROWS
    for row in payload.values[payload_blocks_start_in_payload:]:
        merged.append(sl.pad_row(list(row), n_cols))
    new_block_specs: List[sl.BlockSpec] = []
    for spec in payload.blocks:
        offset = new_blocks_start - payload_blocks_start_in_payload
        new_block_specs.append(sl.BlockSpec(
            experiment_id=spec.experiment_id,
            slot=spec.slot,
            layer=spec.layer,
            positions_mode=spec.positions_mode,
            header_row=spec.header_row + offset,
            data_row_start=spec.data_row_start + offset,
            data_row_end=spec.data_row_end + offset,
            sentinel=spec.sentinel,
        ))

    return merged, kept_block_specs + new_block_specs


def _parse_block_sentinel_back(
    sentinel: str,
    *, header_row: int, data_row_start: int, data_row_end: int,
) -> Optional[sl.BlockSpec]:
    """Recover a :class:`BlockSpec` from an in-cell sentinel string.

    Format: ``[block:<exp_id>/s<slot>_l<layer>/<positions_mode>]``.
    Returns None on parse failure (caller continues without that spec
    -- doesn't impact the actual grid being written, only future
    find-and-replace).
    """
    import re
    m = re.match(
        r"^\[block:([^/\s\]]+)/s(\d+)_l(\d+)/([^/\s\]]+)\]$",
        sentinel,
    )
    if not m:
        return None
    exp_id, slot, layer, positions = m.groups()
    return sl.BlockSpec(
        experiment_id=exp_id, slot=int(slot), layer=int(layer),
        positions_mode=positions,
        header_row=header_row,
        data_row_start=data_row_start,
        data_row_end=data_row_end,
        sentinel=sentinel,
    )


# ---------------------------------------------------------------------------
# Sheets batchUpdate request builders
# ---------------------------------------------------------------------------

def _color_dict(rgb: Tuple[float, float, float]) -> Dict[str, float]:
    return {"red": rgb[0], "green": rgb[1], "blue": rgb[2]}


def _grid_range(*, sheet_id: int, cond: sl.CondFormat) -> Dict[str, int]:
    return {
        "sheetId": sheet_id,
        "startRowIndex": cond.row_start,
        "endRowIndex": cond.row_end,
        "startColumnIndex": cond.col_start,
        "endColumnIndex": cond.col_end,
    }


def _cond_format_request(*, sheet_id: int, cond: sl.CondFormat,
                         index: int) -> Dict[str, Any]:
    """Translate one :class:`CondFormat` into a Sheets
    ``addConditionalFormatRule`` batchUpdate request.
    """
    fmt: Dict[str, Any] = {}
    if cond.bg_color is not None:
        fmt["backgroundColor"] = _color_dict(cond.bg_color)
    text_fmt: Dict[str, Any] = {}
    if cond.italic:
        text_fmt["italic"] = True
    if cond.text_color is not None:
        text_fmt["foregroundColor"] = _color_dict(cond.text_color)
    if text_fmt:
        fmt["textFormat"] = text_fmt

    condition: Dict[str, Any] = {
        "type": cond.condition_type,
        "values": [{"userEnteredValue": str(v)} for v in cond.values],
    }
    return {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [_grid_range(sheet_id=sheet_id, cond=cond)],
                "booleanRule": {
                    "condition": condition,
                    "format": fmt,
                },
            },
            "index": index,
        }
    }


def _freeze_request(*, sheet_id: int, rows: int, cols: int) -> Dict[str, Any]:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": rows,
                    "frozenColumnCount": cols,
                },
            },
            "fields": "gridProperties.frozenRowCount,"
                      "gridProperties.frozenColumnCount",
        }
    }


def _dim_group_request(*, sheet_id: int, g: sl.DimGroup) -> Dict[str, Any]:
    return {
        "addDimensionGroup": {
            "range": {
                "sheetId": sheet_id,
                "dimension": g.dim,
                "startIndex": g.start,
                "endIndex": g.end,
            }
        }
    }


def _width_request(*, sheet_id: int, w: sl.ColumnWidth) -> Dict[str, Any]:
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": w.col,
                "endIndex": w.col + 1,
            },
            "properties": {"pixelSize": w.width_px},
            "fields": "pixelSize",
        }
    }


def _wrap_response_cols_request(
    *, sheet_id: int, n_questions: int, n_rows: int,
) -> Dict[str, Any]:
    """Single repeatCell request to enable WRAP on every q*_response col.

    Applied across the whole row range so newly-added blocks pick it
    up.  No-op on rows whose response cells are empty.
    """
    requests: List[Dict[str, Any]] = []
    for q in range(n_questions):
        col = sl.N_AGG_COLS + sl.N_PER_QUESTION_COLS * q
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": n_rows,
                    "startColumnIndex": col,
                    "endColumnIndex": col + 1,
                },
                "cell": {
                    "userEnteredFormat": {"wrapStrategy": "WRAP"},
                },
                "fields": "userEnteredFormat.wrapStrategy",
            }
        })
    return {"requests": requests}


def _clear_conditional_formats_request(*, sheet_id: int,
                                       n_existing_rules: int) -> List[Dict[str, Any]]:
    """Remove all existing conditional-format rules on the tab.

    Sheets requires rules to be deleted one at a time by index, and
    deleting reindexes the remaining rules, so we walk backwards.
    """
    return [
        {"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": i}}
        for i in range(n_existing_rules - 1, -1, -1)
    ]


def _delete_dim_groups_request(*, sheet_id: int,
                                groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove all existing column groups so we can re-add fresh ones."""
    out: List[Dict[str, Any]] = []
    for g in groups:
        out.append({
            "deleteDimensionGroup": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": g["range"]["dimension"],
                    "startIndex": g["range"]["startIndex"],
                    "endIndex": g["range"]["endIndex"],
                }
            }
        })
    return out


# ---------------------------------------------------------------------------
# Online push (gspread + batchUpdate)
# ---------------------------------------------------------------------------

def push_to_sheet(
    payload: sl.TabPayload,
    *,
    spreadsheet_id: Optional[str],
    spreadsheet_name: str,
    mode: str,
    experiment_id: str,
) -> str:
    """End-to-end Sheets push.  Returns the spreadsheet URL.

    Caller must have prepared OAuth credentials (handled by
    :func:`assistant_axis.gsheet_auth.get_client`).
    """
    from assistant_axis import gsheet_auth
    client = gsheet_auth.get_client()
    ss = _open_or_create_spreadsheet(
        client, spreadsheet_id=spreadsheet_id,
        spreadsheet_name=spreadsheet_name,
    )
    n_cols = sl.N_AGG_COLS + sl.N_PER_QUESTION_COLS * payload.n_questions
    ws = _open_or_create_worksheet(ss, payload.tab_name, n_cols=n_cols)
    sheet_id = ws.id

    # Read existing values (col A is enough for sentinel scan, but we
    # need the kept-block rows for merge -- one bulk read avoids
    # repeated API round-trips).
    existing_values = ws.get_all_values() if mode != "wipe_tab" else []

    merged_values, _final_block_specs = _merge_payload_into_existing(
        payload=payload, existing_values=existing_values,
        mode=mode, current_experiment_id=experiment_id,
    )
    total_rows = len(merged_values)
    total_cols = n_cols

    # ----- WIPE phase -----
    # Always clear conditional formats + dim groups so we can re-add
    # fresh ones spanning the new row range; clear cell values when
    # --wipe-tab; otherwise just rewrite over the existing cells.
    ws_props = ss.fetch_sheet_metadata()
    sheet_meta = next((s for s in ws_props["sheets"]
                       if s["properties"]["sheetId"] == sheet_id), {})
    existing_rules = sheet_meta.get("conditionalFormats", [])
    existing_dim_groups = sheet_meta.get("columnGroups", [])

    requests: List[Dict[str, Any]] = []
    requests.extend(_clear_conditional_formats_request(
        sheet_id=sheet_id, n_existing_rules=len(existing_rules),
    ))
    requests.extend(_delete_dim_groups_request(
        sheet_id=sheet_id, groups=existing_dim_groups,
    ))

    if mode == "wipe_tab":
        requests.append({
            "updateCells": {
                "range": {"sheetId": sheet_id},
                "fields": "userEnteredValue,userEnteredFormat",
            }
        })

    # ----- VALUES -----
    # Write all merged values in one batch; gspread handles A1
    # conversion for us.
    if requests:
        ss.batch_update({"requests": requests})

    if merged_values:
        end_col_letter = _col_index_to_letter(total_cols)
        end_row = total_rows
        cell_range = f"A1:{end_col_letter}{end_row}"
        # Ensure the sheet has enough rows; gspread expands lazily but
        # the API call itself fails if values exceed bounds.
        if ws.row_count < total_rows:
            ws.add_rows(total_rows - ws.row_count + 10)
        if ws.col_count < total_cols:
            ws.add_cols(total_cols - ws.col_count + 2)
        ws.update(cell_range, merged_values,
                  value_input_option="USER_ENTERED")

    # ----- DECORATIONS -----
    decoration_requests: List[Dict[str, Any]] = []
    decoration_requests.append(_freeze_request(
        sheet_id=sheet_id, rows=payload.frozen_rows, cols=payload.frozen_cols,
    ))
    for g in payload.dim_groups:
        decoration_requests.append(_dim_group_request(
            sheet_id=sheet_id, g=g,
        ))
    for w in payload.widths:
        decoration_requests.append(_width_request(
            sheet_id=sheet_id, w=w,
        ))

    # Re-derive conditional formats over the new total row count
    # (payload's were computed against just its own block range).
    full_cond_formats = sl.tab_wide_cond_formats(
        n_questions=payload.n_questions,
        data_row_start=sl.FROZEN_ROWS,
        data_row_end=total_rows,
    )
    for idx, cf in enumerate(full_cond_formats):
        decoration_requests.append(_cond_format_request(
            sheet_id=sheet_id, cond=cf, index=idx,
        ))

    # Wrap response columns.
    wrap_payload = _wrap_response_cols_request(
        sheet_id=sheet_id,
        n_questions=payload.n_questions,
        n_rows=total_rows,
    )
    decoration_requests.extend(wrap_payload["requests"])

    if decoration_requests:
        ss.batch_update({"requests": decoration_requests})

    return ss.url


def _col_index_to_letter(n_cols: int) -> str:
    """Convert a 1-based column count into a Sheets letter (A, B, ...,
    AA, AB, ...).  Used to build the values-update A1 range.
    """
    # n_cols is 1-based (count of columns including the first).
    out = ""
    n = n_cols
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(ord("A") + r) + out
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("experiment_dir", type=Path,
                   help="Path to a steering experiment output directory "
                        "(e.g. /workspace/outputs/qwen-3-32b/steering/architect_ecocentric_v2)")
    p.add_argument("--spreadsheet-id", default=None,
                   help="Attach to an existing spreadsheet by its id. "
                        "Mutually exclusive with --spreadsheet-name; "
                        "id wins when both are set.")
    p.add_argument("--spreadsheet-name", default=None,
                   help="Open (or create) a spreadsheet by name.  Default "
                        "derives from the experiment_id; pass when you want "
                        "a stable named spreadsheet for an experiment set.")
    p.add_argument("--tab-name", default=None,
                   help="Override the default '<role> <pos>_<neg>' tab name.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--replace-experiment-blocks", dest="mode",
        action="store_const", const="replace_experiment_blocks",
        help="Default.  Drop any existing blocks whose sentinel matches "
             "the current experiment_id; preserve other blocks; append "
             "the new payload's blocks at the end.",
    )
    mode.add_argument(
        "--append-only", dest="mode",
        action="store_const", const="append_only",
        help="Never remove any existing blocks; just append.",
    )
    mode.add_argument(
        "--wipe-tab", dest="mode", action="store_const", const="wipe_tab",
        help="Clear the entire tab (including frozen header rows) before "
             "writing the new payload.  Use when questions or baselines "
             "themselves changed across reruns.",
    )
    p.set_defaults(mode="replace_experiment_blocks")
    p.add_argument("--dry-run", action="store_true",
                   help="Write a CSV next to the experiment dir instead of "
                        "calling Google Sheets.  No OAuth required.")
    p.add_argument("--dry-run-csv", type=Path, default=None,
                   help="Override the dry-run CSV output path.  Default "
                        "is <experiment_dir>/sheet_export.csv.")
    p.add_argument("-v", "--verbose", action="count", default=0)
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not args.experiment_dir.exists():
        logger.error(f"experiment dir not found: {args.experiment_dir}")
        return 2

    payload = sl.build_tab(
        args.experiment_dir,
        tab_name_override=args.tab_name,
        spreadsheet_name_override=args.spreadsheet_name,
    )
    logger.info(
        f"built tab payload: tab={payload.tab_name!r}, "
        f"n_questions={payload.n_questions}, "
        f"n_blocks={len(payload.blocks)}, "
        f"n_rows={len(payload.values)}, "
        f"n_cols={len(payload.values[0]) if payload.values else 0}"
    )

    if args.dry_run:
        out_path = args.dry_run_csv or (
            args.experiment_dir / "sheet_export.csv"
        )
        write_csv(payload, out_path)
        return 0

    # Read experiment_id from the payload's first block (or from the
    # config directly if no blocks).
    if payload.blocks:
        experiment_id = payload.blocks[0].experiment_id
    else:
        import json
        with open(args.experiment_dir / "config.json", encoding="utf-8") as f:
            experiment_id = json.load(f).get(
                "experiment_id", args.experiment_dir.name
            )

    url = push_to_sheet(
        payload,
        spreadsheet_id=args.spreadsheet_id,
        spreadsheet_name=args.spreadsheet_name or payload.default_spreadsheet_name,
        mode=args.mode,
        experiment_id=experiment_id,
    )
    logger.info(f"export complete: {url}")
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
