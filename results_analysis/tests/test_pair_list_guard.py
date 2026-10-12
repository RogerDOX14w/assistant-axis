"""Walk-through A2 (2026-10-12; reviews 9a D3, 9b D1): a results_analysis
script that takes a pair list stops, naming each axis, when a listed axis
has no vector or no judge cache, instead of crashing obscurely or dropping
the axis.  Unit tests of ``results_analysis/pair_list_guard.py`` first, then
one end-to-end check per script family (no judge is called; the scripts
stop before their heavy work).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from results_analysis import pair_list_guard as g


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def _tree(tmp_path: Path, *, axes=("pp_vs_nn", "qq_vs_rr"), with_caches=("pp_vs_nn",),
          vectors=("pp", "nn", "qq", "rr"), pair_list="pair_list_di.json"):
    """An experiment dir with a pair list over ``axes``, the four static
    caches for ``with_caches``, and trait vectors for ``vectors``."""
    exp, data = tmp_path / "exp", tmp_path / "data"
    pairs = [dict(zip(("pos", "neg"), ax.split("_vs_"))) for ax in axes]
    _write(exp / pair_list, pairs)
    for ax in with_caches:
        for rel in g.STATIC_DI_CACHES:
            _write(exp / ax / rel, {})
    for n in vectors:
        _touch(data / "traits" / "vectors" / f"{n}.pt")
    return exp, data, pairs


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestCheckPairList:
    def test_usable_axes_pass(self, tmp_path):
        exp, data, pairs = _tree(tmp_path, with_caches=("pp_vs_nn", "qq_vs_rr"))
        assert g.check_pair_list(pairs, pair_list=exp / "pair_list_di.json", script="x.py",
                                 data_dir=data, experiment_dir=exp,
                                 caches_all=g.STATIC_DI_CACHES) is None

    def test_missing_axis_dir_and_vector_are_named(self, tmp_path):
        exp, data, pairs = _tree(tmp_path, vectors=("pp", "nn", "qq"))
        with pytest.raises(SystemExit) as ei:
            g.check_pair_list(pairs, pair_list=exp / "pair_list_di.json", script="x.py",
                              data_dir=data, experiment_dir=exp,
                              caches_all=g.STATIC_DI_CACHES)
        msg = str(ei.value)
        assert msg.startswith("x.py: 1 of 2 axes in pair_list_di.json cannot be used")
        assert "qq_vs_rr: no vector traits/vectors/rr.pt; no judge caches (no directory qq_vs_rr/)" in msg
        assert "pp_vs_nn" not in msg

    def test_one_missing_cache_file_is_named(self, tmp_path):
        exp, data, pairs = _tree(tmp_path, with_caches=("pp_vs_nn", "qq_vs_rr"))
        (exp / "qq_vs_rr" / "sonnet" / "scores_instructions.json").unlink()
        with pytest.raises(SystemExit) as ei:
            g.check_pair_list(pairs, pair_list=exp / "pair_list_di.json", script="x.py",
                              experiment_dir=exp, caches_all=g.STATIC_DI_CACHES)
        assert "qq_vs_rr: no judge cache sonnet/scores_instructions.json" in str(ei.value)

    def test_role_pair_vectors_come_from_roles(self, tmp_path):
        data = tmp_path / "data"
        _touch(data / "roles" / "vectors" / "angel.pt")
        _touch(data / "roles" / "vectors" / "demon.pt")
        pairs = [{"pos": "angel", "neg": "demon", "pair_type": "roles"}]
        g.check_pair_list(pairs, pair_list=tmp_path / "pl.json", script="x.py", data_dir=data)
        pairs[0]["pair_type"] = "traits"
        with pytest.raises(SystemExit, match="no vector traits/vectors/angel.pt"):
            g.check_pair_list(pairs, pair_list=tmp_path / "pl.json", script="x.py", data_dir=data)

    def test_any_of_group_accepts_the_fallback_cohort(self, tmp_path):
        exp, _data, pairs = _tree(tmp_path, axes=("pp_vs_nn",))
        haiku = g.loader_response_caches("haiku")
        group = [("Haiku response cache", haiku)]
        with pytest.raises(SystemExit, match="no Haiku response cache"):
            g.check_pair_list(pairs, pair_list=exp / "pair_list_di.json", script="x.py",
                              experiment_dir=exp, caches_any=group)
        _write(exp / "pp_vs_nn" / "haiku_responses_roles_b10_q9" / "scores_responses.json", {})
        g.check_pair_list(pairs, pair_list=exp / "pair_list_di.json", script="x.py",
                          experiment_dir=exp, caches_any=group)

    def test_recorded_axes(self, tmp_path):
        pairs = [{"pos": "pp", "neg": "nn"}, {"pos": "qq", "neg": "rr"}]
        with pytest.raises(SystemExit) as ei:
            g.check_pair_list(pairs, pair_list=tmp_path / "pl.json", script="x.py",
                              recorded_axes={"pp_vs_nn"}, recorded_label="sweep.json")
        assert "qq_vs_rr: no entry in sweep.json" in str(ei.value)

    def test_points_at_the_v1_list_when_there_is_one(self, tmp_path):
        exp, data, pairs = _tree(tmp_path)
        _write(exp / "pair_list_di_v1.json", pairs[:1])
        with pytest.raises(SystemExit, match="Pass pair_list_di_v1.json instead"):
            g.check_pair_list(pairs, pair_list=exp / "pair_list_di.json", script="x.py",
                              experiment_dir=exp, caches_all=g.STATIC_DI_CACHES)

    def test_no_v1_hint_for_a_v1_list(self, tmp_path):
        exp, data, pairs = _tree(tmp_path, pair_list="pair_list_di_v1.json")
        with pytest.raises(SystemExit) as ei:
            g.check_pair_list(pairs, pair_list=exp / "pair_list_di_v1.json", script="x.py",
                              experiment_dir=exp, caches_all=g.STATIC_DI_CACHES)
        assert "Pass " not in str(ei.value)
        assert "Drop these axes" in str(ei.value)

    def test_fail_for_axes_no_op_when_empty(self, tmp_path):
        assert g.fail_for_axes([], n_axes=3, pair_list="pl.json", script="x.py") is None


class TestResponseCachePaths:
    def test_gpt_canonical_batch(self):
        assert g.gpt_response_caches() == (
            "gpt_responses_traits_b7/scores_responses.json",
            "gpt_responses_roles_b7/scores_responses.json")

    def test_haiku_loader_fallbacks(self):
        assert g.loader_response_caches("haiku") == (
            "haiku_responses_traits_b7_t3/scores_responses.json",
            "haiku_responses_traits_b10_q9/scores_responses.json",
            "haiku_responses_roles_b7_t3/scores_responses.json",
            "haiku_responses_roles_b10_q9/scores_responses.json")


# ---------------------------------------------------------------------------
# End-to-end: each script family stops before its heavy work
# ---------------------------------------------------------------------------

def _stub_subtree(data_dir=None, subtree_rel="", dep_key="", **_kw):
    from assistant_axis.provenance import InputSpec
    return InputSpec(dep_key=dep_key, path=str(subtree_rel), fingerprint="v1:test",
                     kind="subtree")


def _run_main(monkeypatch, mod, argv):
    if hasattr(mod, "current_data_subtree_input"):  # needs a MANIFEST.json otherwise
        monkeypatch.setattr(mod, "current_data_subtree_input", _stub_subtree)
    monkeypatch.setattr(sys, "argv", [mod.__name__.rsplit(".", 1)[-1] + ".py", *argv])
    with pytest.raises(SystemExit) as ei:
        mod.main()
    return str(ei.value)


def test_whitening_k_sweep_names_the_uncached_axis(tmp_path, monkeypatch):
    import results_analysis.whitening_k_sweep as mod
    exp, data, _ = _tree(tmp_path)
    msg = _run_main(monkeypatch, mod, ["--experiment_dir", str(exp), "--data_dir", str(data),
                                       "--pairs", "pair_list_di.json", "--slot", "0"])
    assert "whitening_k_sweep.py: 1 of 2 axes" in msg
    assert "qq_vs_rr: no judge caches" in msg


def test_shear_l_sweep_names_the_axis_without_a_vector(tmp_path, monkeypatch):
    import results_analysis.shear_l_sweep as mod
    exp, data, _ = _tree(tmp_path, with_caches=("pp_vs_nn", "qq_vs_rr"), vectors=("pp", "nn", "rr"))
    msg = _run_main(monkeypatch, mod, ["--experiment_dir", str(exp), "--data_dir", str(data),
                                       "--pairs", "pair_list_di.json", "--slot", "0"])
    assert "qq_vs_rr: no vector traits/vectors/qq.pt" in msg


def test_axis_cosine_seriation_checks_vectors(tmp_path, monkeypatch):
    import results_analysis.axis_cosine_seriation as mod
    exp, data, _ = _tree(tmp_path, vectors=("pp", "nn"), pair_list="pair_list_clean.json")
    msg = _run_main(monkeypatch, mod, ["--experiment_dir", str(exp), "--data_dir", str(data),
                                       "--pairs", "pair_list_clean.json"])
    assert "qq_vs_rr: no vector traits/vectors/qq.pt, traits/vectors/rr.pt" in msg


def test_orthogonal_to_response_set_names_axes_missing_from_the_datastore(tmp_path, monkeypatch):
    import results_analysis.orthogonal_to_response_set as mod
    exp = tmp_path / "exp"
    _write(exp / "axis_cosine_heatmap_clean_softshear3.json",
           {"result": {"axis_labels": ["pp/nn", "aa/bb"], "abs_cos_matrix": [[1, 0], [0, 1]]}})
    _write(exp / "pair_list_responses.json", [{"pos": "pp", "neg": "nn"}, {"pos": "qq", "neg": "rr"}])
    msg = _run_main(monkeypatch, mod, ["--experiment_dir", str(exp)])
    assert "qq_vs_rr: no entry in axis_cosine_heatmap_clean_softshear3.json" in msg


def test_whitening_k_peak_fit_names_axes_missing_from_the_sweep(tmp_path, monkeypatch):
    import results_analysis.whitening_k_peak_fit as mod
    exp = tmp_path / "exp"
    _write(exp / "pair_list_di.json", [{"pos": "pp", "neg": "nn"}, {"pos": "qq", "neg": "rr"}])
    _write(exp / "sweep.json", [{"pos": "pp", "neg": "nn", "source": "desc_inst", "K": 0, "rho": 0.5}])
    msg = _run_main(monkeypatch, mod, ["--experiment_dir", str(exp), "--pairs", "pair_list_di.json",
                                       "--sweep", "sweep.json", "--cache-policy", "off"])
    assert "qq_vs_rr: no entry in sweep.json" in msg


def test_run_axis_experiment_batch_stops_before_any_judge_call(tmp_path, monkeypatch):
    import results_analysis.run_axis_experiment_batch as mod
    exp, data, _ = _tree(tmp_path, vectors=("pp", "nn"))
    launched = []

    async def fake_run_one(*a, **k):  # pragma: no cover -- must not be reached
        launched.append(a)
        return ("x", "y", "OK", 0.0)

    monkeypatch.setattr(mod, "run_one", fake_run_one)
    msg = _run_main(monkeypatch, mod, [
        "--pair_list", str(exp / "pair_list_di.json"), "--provider", "openai",
        "--judge_model", "gpt-4.1-mini", "--output_root", str(tmp_path / "out"),
        "--data_dir", str(data)])
    assert "qq_vs_rr: no vector traits/vectors/qq.pt, traits/vectors/rr.pt" in msg
    assert launched == []
