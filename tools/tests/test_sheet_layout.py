"""Tests for tools/sheet_layout.py.

Builds synthetic experiment directories in tmp_path (no real model
required) and asserts on the structured :class:`TabPayload` returned
by :func:`build_tab`.  Keeps the test surface independent of
gspread / Google APIs -- that integration layer lives in
``tools/steering_to_gsheet.py`` and is exercised manually against
real data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from tools import sheet_layout as sl


# ---------------------------------------------------------------------------
# Fixtures: synthetic experiment dirs
# ---------------------------------------------------------------------------

def _write(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        path.write_text(json.dumps(content, indent=2))
    else:
        path.write_text(str(content))


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def _make_record(
    *,
    strength: float,
    sign: int,
    question_idx: int,
    question: str,
    response: str,
    coh: Optional[int] = 0,
    rp: Optional[int] = 3,
    eff: Optional[float] = 0.0,
    persona_skipped: bool = False,
    effect_skipped: bool = False,
) -> Dict[str, Any]:
    """Construct one cell-record matching the runner's on-disk schema."""
    coh_block = None if coh is None else {"score": coh, "reason": "ok"}
    # Persona / effect blocks are NEVER None on a real cell record (the
    # runner always writes the structure, even if the inner judge was
    # skipped due to mean_coh).  Mirror that here so `_persona_skipped`
    # / `_effect_skipped` flags resolve correctly in tests.
    persona_block = {
        "score": rp, "reason": "ok",
        "skipped_due_to_strength_mean_coh": persona_skipped,
    }
    effect_block = {
        "bidirectional": {"scores": {}, "mean": eff,
                          "n_judges_succeeded": 2, "n_judges_attempted": 2},
        "mode": "bidirectional",
        "combined": eff,
        "skipped_due_to_strength_mean_coh": effect_skipped,
    }
    return {
        "strength": strength,
        "sign": sign,
        "question_idx": question_idx,
        "question": question,
        "response": response,
        "n_tokens": 50,
        "judges": {
            "coherence": coh_block,
            "persona": persona_block,
            "effect": effect_block,
        },
        "timing": {"gen_s": 1.0},
        "abandoned": False,
    }


def _make_baseline_record(
    question_idx: int, question: str, response: str
) -> Dict[str, Any]:
    """Baseline record: sign=0, strength=0, judges all null."""
    return {
        "strength": 0.0,
        "sign": 0,
        "question_idx": question_idx,
        "question": question,
        "response": response,
        "n_tokens": 50,
        "judges": {"coherence": None, "persona": None, "effect": None},
        "timing": {"gen_s": 1.0},
    }


def _make_config(
    experiment_id: str,
    role: str = "chef",
    role_from: str = "helpful",
    role_to: str = "unhelpful",
    cells: Optional[List[Dict[str, int]]] = None,
    positions_mode: str = "all",
) -> Dict[str, Any]:
    return {
        "experiment_id": experiment_id,
        "model_name": "Qwen/Qwen3-32B",
        "output_dir": "/tmp/outputs",
        "axis_source": {
            "type": "role_transplant",
            "vectors_dir": "/tmp/vectors",
            "role_from": role_from,
            "role_to": role_to,
        },
        "persona": {"type": "role", "role": role, "prompt_index": 0},
        "cells": cells or [{"slot": 3, "layer": 25}],
        "sweep": {
            "weakest_strength": 1.0, "max_strength": 8.0,
            "multiplier": 1.189, "signs": [1, -1],
        },
        "positions_mode": positions_mode,
        "batch_size": 4,
        "max_new_tokens": 512,
        "questions_file": "data/steering/questions/dummy.json",
    }


def _make_summary(
    *, slot: int, layer: int, sign: int,
    up_strength: float = 8.0, up_reason: str = "incoherent",
    down_strength: float = 0.125, down_reason: str = "min_strength_reached",
) -> Dict[str, Any]:
    return {
        "slot": slot, "layer": layer, "sign": sign,
        "stopped_at_strength": up_strength,
        "reason": "bidirectional_done",
        "n_records": 0,
        "n_strengths_swept": 0,
        "scan_mode": "bidirectional",
        "positions_mode": "all",
        "s_init": 1.414,
        "min_strength": 0.125,
        "max_strength": 8.0,
        "multiplier": 1.189,
        "weakest_strength": 1.0,
        "up_blocked_reason": up_reason,
        "down_blocked_reason": down_reason,
        "up_blocked_at_strength": up_strength,
        "down_blocked_at_strength": down_strength,
    }


@pytest.fixture
def single_cell_experiment(tmp_path: Path) -> Path:
    """7 questions × 5 strengths (sign +1) × 5 strengths (sign -1) + baseline.

    Includes one fully-skipped strength (mean_coh forced ≥ 1.5) so the
    [skipped — incoherent] placeholder is exercised.
    """
    n_q = 7
    questions = [f"q{i}" for i in range(n_q)]
    exp_dir = tmp_path / "chef_helpful_v1"
    _write(exp_dir / "config.json", _make_config("chef_helpful_v1"))
    _write(exp_dir / "questions.json", questions)
    _write(exp_dir / "persona_system_prompt.txt", "Pretend you are a chef.")
    # Baselines
    _write_jsonl(
        exp_dir / "baselines" / "records.jsonl",
        [_make_baseline_record(i, questions[i], f"baseline-resp-{i}")
         for i in range(n_q)],
    )
    # Cell records: 5 strengths each sign.
    pos_strengths = [1.0, 1.414, 2.0, 4.0, 8.0]
    neg_strengths = [1.0, 1.414, 2.0, 4.0, 8.0]
    pos_recs: List[Dict[str, Any]] = []
    for s in pos_strengths:
        # The strongest +1 strength is forced to "skipped" so we
        # cover the placeholder path.
        skipped = (s == 8.0)
        for q in range(n_q):
            pos_recs.append(_make_record(
                strength=s, sign=+1, question_idx=q,
                question=questions[q],
                response=f"+{s}-resp-q{q}",
                coh=2 if skipped else 0,
                rp=None if skipped else 3,
                eff=None if skipped else +1.0,
                persona_skipped=skipped,
                effect_skipped=skipped,
            ))
    neg_recs: List[Dict[str, Any]] = []
    for s in neg_strengths:
        for q in range(n_q):
            neg_recs.append(_make_record(
                strength=s, sign=-1, question_idx=q,
                question=questions[q],
                response=f"-{s}-resp-q{q}",
                coh=0, rp=3, eff=-1.0,
            ))
    _write_jsonl(exp_dir / "s3_l25_+1" / "records.jsonl", pos_recs)
    _write_jsonl(exp_dir / "s3_l25_-1" / "records.jsonl", neg_recs)
    _write(exp_dir / "s3_l25_+1" / "summary.json",
           _make_summary(slot=3, layer=25, sign=+1))
    _write(exp_dir / "s3_l25_-1" / "summary.json",
           _make_summary(slot=3, layer=25, sign=-1,
                         up_reason="incoherent",
                         down_reason="min_strength_reached"))
    return exp_dir


@pytest.fixture
def multi_cell_experiment(tmp_path: Path) -> Path:
    """7 questions × 2 cells × (3 strengths × 2 signs) + baseline."""
    n_q = 7
    questions = [f"q{i}" for i in range(n_q)]
    exp_dir = tmp_path / "chef_helpful_multi"
    _write(exp_dir / "config.json", _make_config(
        "chef_helpful_multi",
        cells=[{"slot": 3, "layer": 25}, {"slot": 7, "layer": 49}],
    ))
    _write(exp_dir / "questions.json", questions)
    _write(exp_dir / "persona_system_prompt.txt", "Pretend you are a chef.")
    _write_jsonl(
        exp_dir / "baselines" / "records.jsonl",
        [_make_baseline_record(i, questions[i], f"b-{i}") for i in range(n_q)],
    )
    for slot, layer in [(3, 25), (7, 49)]:
        for sign in (+1, -1):
            recs: List[Dict[str, Any]] = []
            for s in (1.0, 2.0, 4.0):
                for q in range(n_q):
                    recs.append(_make_record(
                        strength=s, sign=sign, question_idx=q,
                        question=questions[q],
                        response=f"{sign:+d}{s}-s{slot}l{layer}-q{q}",
                    ))
            _write_jsonl(
                exp_dir / f"s{slot}_l{layer}_{'+1' if sign > 0 else '-1'}"
                / "records.jsonl",
                recs,
            )
            _write(
                exp_dir / f"s{slot}_l{layer}_{'+1' if sign > 0 else '-1'}"
                / "summary.json",
                _make_summary(slot=slot, layer=layer, sign=sign),
            )
    return exp_dir


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestSingleCellShape:
    def test_grid_dimensions(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Single cell: 1 block = 1 header row + 5*2=10 data rows.
        # Total rows = 3 frozen + 1 header + 10 = 14.
        assert len(payload.values) == 3 + 1 + 10
        # Cols = 5 agg + 4 * 7 questions = 33.
        assert all(len(r) == 5 + 4 * 7 for r in payload.values)

    def test_frozen_counts(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        assert payload.frozen_rows == 3
        assert payload.frozen_cols == 1

    def test_persona_row(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        assert payload.values[0][0] == "persona"
        assert payload.values[0][1] == "Pretend you are a chef."

    def test_header_row_has_question_text(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Header is row index 1; col index 5 = q0 response col carries q text.
        assert payload.values[1][5] == "q0"
        # col 6 = q0_coh label
        assert payload.values[1][6] == "coh"

    def test_baseline_row_has_baseline_responses(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        assert payload.values[2][0] == "baseline"
        # col 5 = q0 response = baseline-resp-0
        assert payload.values[2][5] == "baseline-resp-0"
        # col 5 + 4 = q1 response = baseline-resp-1
        assert payload.values[2][9] == "baseline-resp-1"

    def test_block_header_sentinel_in_col_a(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Block header is at row index 3 (right after frozen).
        sentinel = payload.values[3][0]
        assert sentinel == "[block:chef_helpful_v1/s3_l25/all]"

    def test_signed_strengths_sorted_ascending(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Data rows start at row 4; 10 strength rows total.
        signed = [payload.values[4 + i][0] for i in range(10)]
        assert signed == sorted(signed)
        # Should span -8.0 .. +8.0 (approx).
        assert signed[0] == -8.0
        assert signed[-1] == 8.0

    def test_blocks_list_matches_grid(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        assert len(payload.blocks) == 1
        b = payload.blocks[0]
        assert b.experiment_id == "chef_helpful_v1"
        assert b.slot == 3
        assert b.layer == 25
        assert b.positions_mode == "all"
        assert b.header_row == 3
        assert b.data_row_start == 4
        assert b.data_row_end == 4 + 10
        # Sentinel matches what we put in col A of header_row.
        assert payload.values[b.header_row][0] == b.sentinel


class TestSkippedRow:
    def test_skipped_placeholder_in_response_cells(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Find the row at signed_strength = +8.0 (the skipped one).
        for i, row in enumerate(payload.values):
            if i < 3 + 1:  # before data
                continue
            if row[0] == 8.0:
                # Col 5 = q0 response; should be placeholder, not the
                # synthetic response.
                assert row[5] == sl.SKIPPED_PLACEHOLDER
                # Other q cells likewise.
                assert row[9] == sl.SKIPPED_PLACEHOLDER
                return
        pytest.fail("Did not find +8.0 row")

    def test_italic_text_eq_rule_exists_per_response_col(
        self, single_cell_experiment
    ):
        """One italic TEXT_EQ '[skipped]' rule per question response col,
        spanning the whole data range so any block's skipped row picks it up.
        """
        payload = sl.build_tab(single_cell_experiment)
        italic_rules = [cf for cf in payload.cond_formats if cf.italic]
        assert italic_rules, "expected italic [skipped] formatting rules"
        # One rule per question (7).
        assert len(italic_rules) == 7
        for cf in italic_rules:
            assert cf.text_color == sl.COLOR_GRAY_TEXT
            assert cf.condition_type == "TEXT_EQ"
            assert cf.values == (sl.SKIPPED_PLACEHOLDER,)


class TestDimGroups:
    def test_outer_aggregate_group(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # First group should cover cols B-E (1..5).
        outer = payload.dim_groups[0]
        assert outer.dim == "COLUMNS"
        assert outer.start == 1
        assert outer.end == sl.N_AGG_COLS  # 5

    def test_one_inner_group_per_question(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # 7 questions -> 7 inner groups (after the 1 outer).
        assert len(payload.dim_groups) == 1 + 7
        for q in range(7):
            g = payload.dim_groups[1 + q]
            q_resp_col = sl.N_AGG_COLS + sl.N_PER_QUESTION_COLS * q
            # Group should cover the score trio (coh, rp, eff), skipping
            # response (the first per-question col).
            assert g.start == q_resp_col + 1
            assert g.end == q_resp_col + sl.N_PER_QUESTION_COLS


class TestCondFormats:
    def test_graded_pink_thresholds_present(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # At least one rule for each of (0.5, 1.0, 1.5) on mean_coh.
        pink_thresholds_seen: set = set()
        for cf in payload.cond_formats:
            if (cf.col_start == 1 and cf.col_end == 2
                    and cf.condition_type == "NUMBER_GREATER_THAN_EQ"):
                pink_thresholds_seen.add(cf.values[0])
        assert pink_thresholds_seen == set(sl.COH_THRESHOLDS)

    def test_signed_eff_both_directions(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # mean_eff col is index 3.  Should have 3 positive (GTE 1/2/3)
        # and 3 negative (LTE -1/-2/-3) for at least one data row.
        pos_t: set = set()
        neg_t: set = set()
        for cf in payload.cond_formats:
            if cf.col_start == 3 and cf.col_end == 4:
                if cf.condition_type == "NUMBER_GREATER_THAN_EQ":
                    pos_t.add(cf.values[0])
                elif cf.condition_type == "NUMBER_LESS_THAN_EQ":
                    neg_t.add(cf.values[0])
        assert pos_t == set(sl.EFF_ABS_THRESHOLDS)
        assert neg_t == {-t for t in sl.EFF_ABS_THRESHOLDS}

    def test_low_rp_rule_on_mean_col(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Tab-wide: exactly one orange-faint LTE-1 rule on mean_rp col 2.
        low_rp_rules = [cf for cf in payload.cond_formats
                        if cf.col_start == 2 and cf.col_end == 3
                        and cf.condition_type == "NUMBER_LESS_THAN_EQ"
                        and cf.values == (sl.RP_LOW_THRESHOLD,)]
        assert len(low_rp_rules) == 1
        # The single rule spans the whole data row range, not just one row.
        assert low_rp_rules[0].row_start == 3  # FROZEN_ROWS
        # 1 block header + 10 data rows = 11; total = FROZEN_ROWS + 11 = 14
        assert low_rp_rules[0].row_end == 14

    def test_rule_count_scales_with_questions_not_rows(
        self, single_cell_experiment
    ):
        """Sanity check: under tab-wide formatting, total rule count is
        a function of n_questions, NOT of n_data_rows.  Previously we
        emitted per-row rules which would blow past Sheets' practical
        cap on multi-cell experiments; tab-wide keeps us bounded.
        """
        payload = sl.build_tab(single_cell_experiment)
        # Per agg cols: 3 (mean_coh pink) + 1 (mean_rp orange) + 6 (mean_eff
        # signed green+blue) = 10.
        # Per question: same 10 + 1 italic placeholder = 11.
        # 7 questions -> 10 + 7*11 = 87.
        assert len(payload.cond_formats) == 10 + 7 * 11


class TestWidths:
    def test_response_cols_are_wide(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # q0 response col = N_AGG_COLS + 0 = 5.
        widths_by_col = {w.col: w.width_px for w in payload.widths}
        assert widths_by_col[5] == sl.WIDTH_RESPONSE_PX
        # q0_coh = 6, should be the narrow score width.
        assert widths_by_col[6] == sl.WIDTH_SCORE_PX

    def test_strength_col_width(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        widths_by_col = {w.col: w.width_px for w in payload.widths}
        assert widths_by_col[0] == sl.WIDTH_STRENGTH_PX


class TestMultiCell:
    def test_two_blocks(self, multi_cell_experiment):
        payload = sl.build_tab(multi_cell_experiment)
        assert len(payload.blocks) == 2
        b0, b1 = payload.blocks
        assert b0.slot == 3 and b0.layer == 25
        assert b1.slot == 7 and b1.layer == 49

    def test_sentinels_unique(self, multi_cell_experiment):
        payload = sl.build_tab(multi_cell_experiment)
        sentinels = [b.sentinel for b in payload.blocks]
        assert len(set(sentinels)) == len(sentinels)

    def test_blocks_are_contiguous_and_in_order(self, multi_cell_experiment):
        payload = sl.build_tab(multi_cell_experiment)
        b0, b1 = payload.blocks
        # The second block starts immediately after the first ends.
        assert b1.header_row == b0.data_row_end


class TestBlockSentinel:
    def test_format(self):
        s = sl.make_block_sentinel("foo_v1", 3, 25, "all")
        assert s == "[block:foo_v1/s3_l25/all]"

    def test_positions_mode_distinguishes(self):
        a = sl.make_block_sentinel("foo_v1", 3, 25, "all")
        b = sl.make_block_sentinel("foo_v1", 3, 25, "prefill")
        assert a != b


class TestDefaultNames:
    def test_tab_name(self):
        assert sl.default_tab_name("chef", "helpful", "unhelpful") \
            == "chef helpful_unhelpful"

    def test_spreadsheet_name_single(self):
        n = sl.default_spreadsheet_name(["chef_helpful_v1"])
        assert "chef_helpful_v1" in n

    def test_spreadsheet_name_common_prefix(self):
        n = sl.default_spreadsheet_name(
            ["chef_helpful_v1", "chef_helpful_v2"]
        )
        assert "chef_helpful" in n
        assert n.endswith("*")

    def test_spreadsheet_name_no_common_prefix(self):
        n = sl.default_spreadsheet_name(["abc_helpful_v1", "xyz_helpful_v1"])
        assert n == "Steering experiments"


class TestAggregates:
    def test_aggregates_match_per_q_means(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # Pick a non-skipped row: +1.0 (sign=+1 strength=1.0).
        for row in payload.values[4:]:
            if row[0] == 1.0:
                # All q0..q6 coh values are 0 (per fixture), so mean_coh = 0.
                assert row[1] == 0.0
                # All rp = 3, so mean_rp = 3.0.
                assert row[2] == 3.0
                # All eff = +1.0, so mean_eff_signed = 1.0 and mean_abs_eff = 1.0.
                assert row[3] == 1.0
                assert row[4] == 1.0
                return
        pytest.fail("Did not find +1.0 row")

    def test_aggregates_blank_when_all_skipped(self, single_cell_experiment):
        payload = sl.build_tab(single_cell_experiment)
        # +8.0 row had persona+effect skipped for ALL 7 questions, so
        # mean_rp and mean_eff should be "" (blank).  mean_coh is still
        # 2.0 because the fixture set coh=2 on skipped rows.
        for row in payload.values[4:]:
            if row[0] == 8.0:
                assert row[2] == ""  # mean_rp blank
                assert row[3] == ""  # mean_eff blank
                assert row[4] == ""  # mean_abs_eff blank
                return
        pytest.fail("Did not find +8.0 row")
