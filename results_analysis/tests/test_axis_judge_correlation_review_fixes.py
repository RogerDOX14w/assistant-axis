"""Regression tests for the 2026-10-12 code-review fixes to
``results_analysis/axis_judge_correlation.py`` (walk-through decisions in
``reports/code_review_2026-10-12/escalations.md``, "Decisions so far"):

* D4 (review 9a D5): ``_save_json`` writes atomically (temp file +
  ``os.replace``), so a failed or killed write leaves the old cache.
* D12 (review P3, cross-file): the ``response_score_files`` fingerprint
  leaves out step 3's side-cars (``SIDE_CAR_FILENAMES``).
* D3 (review 9a D2): the poles are skipped by entity id, so on
  impatient_vs_patient the role ``patient|R`` is scored and projected.

No judge is called.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path

import pytest
import torch

from results_analysis import axis_judge_correlation as ajc

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# D4: atomic cache writes
# ---------------------------------------------------------------------------

class TestSaveJsonAtomic:
    def test_replaces_the_file_rather_than_rewriting_it_in_place(self, tmp_path):
        """``os.replace`` gives the path a new inode; an in-place
        ``write_text`` (the old code) keeps the old one."""
        p = tmp_path / "scores_responses.json"
        ajc._save_json(p, {"a": 1})
        ino_before = os.stat(p).st_ino
        ajc._save_json(p, {"a": 2})
        assert os.stat(p).st_ino != ino_before
        assert json.loads(p.read_text()) == {"a": 2}
        assert not (tmp_path / "scores_responses.json.inprogress").exists()

    def test_failed_write_leaves_the_previous_cache_intact(self, tmp_path, monkeypatch):
        """A write that dies part-way (here: every copy attempt writes half
        the bytes and then fails) must not truncate the existing cache."""
        from assistant_axis import atomic_io

        p = tmp_path / "scores_descriptions.json"
        spec = ajc.current_file_input(dep_key="x", path=Path(__file__))
        ajc._save_json(p, {"patient|R": 1}, inputs=[spec], title="t", schema_version=2)
        before = p.read_text()

        def half_copy(src, dst, *a, **k):
            data = Path(src).read_bytes()
            Path(dst).write_bytes(data[: len(data) // 2])
            raise OSError("simulated failure mid-copy")

        monkeypatch.setattr(atomic_io.shutil, "copy2", half_copy)
        monkeypatch.setattr(atomic_io.time, "sleep", lambda s: None)
        with pytest.raises(OSError):
            ajc._save_json(p, {"patient|R": 1, "stoic|T": -2}, inputs=[spec],
                           title="t", schema_version=2)
        assert p.read_text() == before
        assert json.loads(p.read_text())["result"] == {"patient|R": 1}
        assert not (tmp_path / "scores_descriptions.json.inprogress").exists()

    def test_usage_side_car_is_written_atomically(self, tmp_path, monkeypatch):
        seen = []
        real = ajc.atomic_write_text

        def spy(text, dest, **k):
            seen.append(Path(dest))
            return real(text, dest, **k)

        monkeypatch.setattr(ajc, "atomic_write_text", spy)
        tracker = ajc.BudgetTracker(totals=ajc.UsageTotals(model="gpt-4.1-mini"))
        args = argparse.Namespace(usage_json=None, output_dir=str(tmp_path))
        ajc._flush_budget_artifacts(args, tracker)
        assert seen == [tmp_path / "usage.json"]
        assert json.loads((tmp_path / "usage.json").read_text())


# ---------------------------------------------------------------------------
# D12: step-3 side-cars are not part of the score-files fingerprint
# ---------------------------------------------------------------------------

def _responses_args(tmp_path: Path, scores_dir: Path) -> argparse.Namespace:
    return argparse.Namespace(
        provider="openai", judge_model="gpt-4.1-mini", temperature=1.0,
        max_tokens=400, response_target_batch_size=7, tiered_modulo_per_chunk=3,
        question_subsample_modulo=0, no_subsample=False,
        axis_file=None, pair=None,
        instructions_dir=str(tmp_path / "no_instructions"),
        data_dir=str(tmp_path / "no_data"),
        responses_dir=None, scores_dir=str(scores_dir),
        questions_file=str(tmp_path / "no_questions.jsonl"), layer=32,
    )


class TestScoreFilesFingerprintSkipsSideCars:
    def test_side_cars_left_out(self, tmp_path):
        scores = tmp_path / "scores"
        scores.mkdir()
        for name in ("analytical.json", "patient.json", *ajc.SIDE_CAR_FILENAMES):
            (scores / name).write_text("{}")
        inputs = ajc._build_axis_judge_inputs(_responses_args(tmp_path, scores), mode="responses")
        (spec,) = [s for s in inputs if s.dep_key == "response_score_files"]
        members = sorted(Path(m).name for m in spec.member_paths)
        assert members == ["analytical.json", "patient.json"]

    def test_fingerprint_unmoved_by_a_side_car_rewrite(self, tmp_path):
        scores = tmp_path / "scores"
        scores.mkdir()
        (scores / "analytical.json").write_text("{}")
        args = _responses_args(tmp_path, scores)

        def fp():
            (spec,) = [s for s in ajc._build_axis_judge_inputs(args, mode="responses")
                       if s.dep_key == "response_score_files"]
            return spec.fingerprint

        before = fp()
        (scores / "usage.json").write_text('{"n_calls": 3}')
        (scores / "batch_state.json").write_text('{"chunks": []}')
        assert fp() == before

    def test_matches_step_3s_side_car_list(self):
        """The tuple is copied from ``pipeline/3_judge.py`` (not imported,
        to keep step 3's imports out); keep the two in step."""
        src = (REPO / "pipeline" / "3_judge.py").read_text()
        consts = {}
        for node in ast.parse(src).body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)):
                consts[node.targets[0].id] = node.value
        names = consts["SIDE_CAR_FILENAMES"]
        assert isinstance(names, ast.Tuple)
        resolved = tuple(ast.literal_eval(consts[e.id]) for e in names.elts)
        assert set(resolved) == set(ajc.SIDE_CAR_FILENAMES)


# ---------------------------------------------------------------------------
# D3: the pole skip is by entity id
# ---------------------------------------------------------------------------

def _spec(pole_kind="traits", poles=("impatient", "patient")):
    return ajc.AxisSpec(
        axis_name=f"{poles[0]} (+) vs {poles[1]} (-) [traits]",
        neg_pole="n", pos_pole="p", neg_examples=[poles[1]], pos_examples=[poles[0]],
        axis_by_slot={0: torch.tensor([1.0, 0.0, 0.0, 0.0])},
        source_description="test", exclusions=list(poles),
        pole_pair_names=list(poles), pole_kind=pole_kind,
    )


class TestPoleEntityIds:
    def test_pole_kind_only(self):
        assert _spec().pole_entity_ids() == {"impatient|T", "patient|T"}

    def test_unknown_kind_skips_both_kinds(self):
        """An AxisSpec built without ``pole_kind`` keeps the old,
        kind-blind skip."""
        assert _spec(pole_kind=None).pole_entity_ids() == {
            "impatient|T", "patient|T", "impatient|R", "patient|R"}

    def test_axis_file_spec_skips_nothing(self):
        spec = _spec()
        spec.pole_pair_names = []
        assert spec.pole_entity_ids() == set()

    def test_scorable_keeps_the_same_named_role(self):
        entities = [("roles", "patient"), ("roles", "teacher"), ("traits", "impatient"),
                    ("traits", "patient"), ("traits", "stoic")]
        got = ajc.scorable_entities(entities, _spec().pole_entity_ids())
        assert got == [("roles", "patient"), ("roles", "teacher"), ("traits", "stoic")]


def _corpus() -> "ajc.Corpus":
    g = torch.Generator().manual_seed(0)
    keys = [("traits", "impatient"), ("traits", "patient"), ("roles", "patient"),
            ("roles", "teacher"), ("traits", "stoic"), ("roles", "nurse"),
            ("traits", "calm")]
    vectors = {k: torch.randn(1, 4, generator=g) for k in keys}
    return ajc.Corpus(vectors=vectors, descriptions={}, pos_instructions={},
                      default=torch.zeros(1, 4), entities=sorted(keys))


class TestComputeProjectionsPoleSkip:
    def test_same_named_role_projected_and_poles_not(self):
        corpus = _corpus()
        spec = _spec()
        out = ajc.compute_projections(corpus, spec, whiten_K=1, slots=[0],
                                      pole_ids=spec.pole_entity_ids())[0]
        assert "patient|R" in out
        assert "patient|T" not in out and "impatient|T" not in out

    def test_pool_holds_out_only_the_two_poles(self):
        """The leave-one-out pool for an entity is every other entity
        except the two pole ids; the same-named role stays in it."""
        corpus = _corpus()
        spec = _spec()
        out = ajc.compute_projections(corpus, spec, whiten_K=1, slots=[0],
                                      pole_ids=spec.pole_entity_ids())[0]
        target = "teacher|R"
        rows = {ajc.entity_id(n, k): v[0] for (k, n), v in corpus.vectors.items()}
        pool = torch.stack([x for e, x in rows.items()
                            if e not in (target, "impatient|T", "patient|T")])
        w = ajc.fit_soft_k_whitener(pool, K=1)
        axis = spec.axis_by_slot[0]
        aw = w.apply(axis.unsqueeze(0)).squeeze(0)
        xw = w.apply(rows[target].unsqueeze(0)).squeeze(0)
        expected = float((xw @ aw).item()) / torch.linalg.vector_norm(aw).item()
        assert out[target]["whitened"] == pytest.approx(expected, rel=1e-5)

        # The old kind-blind pool (patient|R held out too) gives a
        # different number, so the test would catch a regression.
        pool_old = torch.stack([x for e, x in rows.items()
                                if e not in (target, "impatient|T", "patient|T", "patient|R")])
        w_old = ajc.fit_soft_k_whitener(pool_old, K=1)
        aw_old = w_old.apply(axis.unsqueeze(0)).squeeze(0)
        xw_old = w_old.apply(rows[target].unsqueeze(0)).squeeze(0)
        old = float((xw_old @ aw_old).item()) / torch.linalg.vector_norm(aw_old).item()
        assert old != pytest.approx(expected, rel=1e-5)


class TestComputeCorrelationsEntityIdExclusion:
    def _proj(self, keys):
        return {0: {k: {"raw": float(i), "whitened": float(i)} for i, k in enumerate(keys)}}

    def test_id_exclusion_keeps_the_other_kind(self):
        keys = ["patient|R", "patient|T", "impatient|T", "stoic|T", "teacher|R", "nurse|R"]
        scores = {"descriptions": {k: float(i % 3) for i, k in enumerate(keys)}}
        out = ajc.compute_correlations(scores, self._proj(keys), slots=[0],
                                       excluded_set={"patient|T", "impatient|T"})
        names = out["descriptions"]["0"]["raw"]["names"]
        assert "patient|R" in names
        assert "patient|T" not in names and "impatient|T" not in names
        assert len(names) == 4

    def test_bare_key_with_id_exclusion_is_conservative(self):
        """A bare key (kind unknown) sharing a pole's name is excluded."""
        keys = ["patient", "stoic", "teacher", "nurse"]
        scores = {"responses": {k: float(i) for i, k in enumerate(keys)}}
        out = ajc.compute_correlations(scores, self._proj(keys), slots=[0],
                                       excluded_set={"patient|T"})
        assert out["responses"]["0"]["raw"]["names"] == ["nurse", "stoic", "teacher"]


class TestResolveAxisRecordsPoleKind:
    def test_pair_axis_has_pole_kind(self, tmp_path):
        vdir = tmp_path / "data" / "traits" / "vectors"
        idir = tmp_path / "instr" / "traits" / "instructions"
        vdir.mkdir(parents=True)
        idir.mkdir(parents=True)
        g = torch.Generator().manual_seed(1)
        for n in ("impatient", "patient"):
            torch.save({"vector": torch.randn(2, 1, 4, generator=g)}, vdir / f"{n}.pt")
            (idir / f"{n}.json").write_text(json.dumps({"description": f"{n} text"}))
        args = argparse.Namespace(
            pair=("impatient", "patient"), pair_type="traits",
            data_dir=str(tmp_path / "data"), instructions_dir=str(tmp_path / "instr"),
            neg_examples=None, pos_examples=None, neg_pole=None, pos_pole=None,
        )
        spec = ajc.resolve_axis(args, n_slots=2, hidden_dim=4, layer=0)
        assert spec.pole_kind == "traits"
        assert spec.pole_entity_ids() == {"impatient|T", "patient|T"}


# ---------------------------------------------------------------------------
# D5: the parser requires exactly one SCORE marker (RUBRIC_VERSION v5)
# ---------------------------------------------------------------------------

class TestParseSignedScoreV5:
    @pytest.mark.parametrize("text, expected", [
        ("Leans clearly negative.\nSCORE: -2", -2),
        ("reasoning...\n\nSCORE: +3", 3),
        ("reasoning\nscore: 1", 1),              # marker is case-insensitive, as before
        ("reasoning\nSCORE : 0", 0),
        ("reasoning\nSCORE: 7", 3),              # out of range: clamped, as before
        ("reasoning\nSCORE: -9", -3),
    ])
    def test_one_marker(self, text, expected):
        assert ajc.parse_signed_score(text) == expected

    @pytest.mark.parametrize("text", [
        None, "",
        # No marker: v4 read the first integer in [-3, 3] ("2" here).
        "Scores of 2 or 3 would fit the first five responses.",
        # The two replies hand-edited on 2026-10-12: split-persona scores
        # in a form the marker regex does not match.
        "SCORE (Responses 1-5): +3  \nSCORE (Responses 6-10): -3",
        "SCORE (pet sitter advice role): -2  \nSCORE (prophecy and revelation role): +3",
    ])
    def test_no_marker_is_none(self, text):
        assert ajc.parse_signed_score(text) is None

    @pytest.mark.parametrize("text", [
        # The three replies hand-edited under v5 (v4 took the first marker).
        "SCORE: -3 (for responses 1-3) and SCORE: +3 (for responses 4-7)",
        "For the first set ...\n\nSCORE: +2\n\nFor the second set ...\n\nSCORE: -3",
        "- parenting: SCORE: +2\n- safety: SCORE: -3\n...\nSCORE: +2\n...\nSCORE: -3",
        # Repeated markers that agree are still more than one answer.
        "first persona ...\n\nSCORE: +3\n\nsecond persona ...\n\nSCORE: +3",
    ])
    def test_repeated_marker_is_none(self, text):
        assert ajc.parse_signed_score(text) is None

    def test_rubric_version_bumped(self):
        assert ajc.RUBRIC_VERSION == "v5"

    def test_v4_to_v5_declared_equivalent_everywhere(self):
        """The prompts did not change, so the repo registry carries a global
        v4 -> v5 edge; v3 caches reach v5 through the scoped v3 -> v4 edges."""
        from assistant_axis import rubric_equivalence as eq
        reg = eq.load_registry()
        for mode in ("descriptions", "instructions", "responses"):
            assert eq.is_equivalent("v4", "v5", axis="any_axis_vs_other", mode=mode,
                                    entity_id="x|T", registry=reg)
        assert eq.is_equivalent("v3", "v5", axis="concise_vs_verbose", mode="responses",
                                entity_id="concise", registry=reg)
