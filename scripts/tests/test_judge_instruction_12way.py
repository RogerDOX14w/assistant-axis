"""scripts/judge_instruction_12way.py's Jev arms (2026-11-04): Jev 1x and 2x, the trio + Jev and Luna + Haiku + Jev at
1x and 2x, Jev's own cell names, and --without_jev leaving them out."""
import importlib.util
from pathlib import Path


def _mod():
    path = Path(__file__).resolve().parents[1] / "judge_instruction_12way.py"
    spec = importlib.util.spec_from_file_location("judge_instruction_12way", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_jev_arms_and_cells():
    mod = _mod()
    for name, mode in mod.MODES.items():
        mod.WITH_JEV = True
        a = mod.arms(mode)
        jev = {k: v for k, v in a.items() if mod.JEV in v[1]}
        labels = sorted(v[0] for v in jev.values())
        assert labels == sorted(["Jev 1x", "Jev 2x", "Luna + Haiku + Gemini + Jev 1x", "Luna + Haiku + Gemini + Jev 2x",
                                 "Luna + Haiku + Jev 1x", "Luna + Haiku + Jev 2x"]), name
        assert mod.passes_of(mode)[mod.JEV] == 2
        # the Jev sets run as arrows from 1x to 2x like the others
        assert any(set(run) == {k for k, v in jev.items() if v[0].startswith("Jev ")} for run in mod.series(mode))
        mod.WITH_JEV = False
        assert not any(mod.JEV in v[1] for v in mod.arms(mode).values()) and mod.JEV not in mod.passes_of(mode)
    mod.WITH_JEV = True
    assert mod.cell_of(mod.MODES["instructions"], mod.JEV, 7) == "jev-1.14.0@ji_noul_relative_n160_r7"
    assert mod.cell_of(mod.MODES["descriptions"], mod.JEV, 1) == "jev-1.14.0@jd_noul_relative_n160s2"
    assert mod.cell_of(mod.MODES["instructions"], "gpt-5.6-luna", 3) == "gpt-5.6-luna@i1_p0n20r3"


def test_jev_colour():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from results_analysis.judge_tier_cost_plot_pooled import PROVIDER_COLOR, provider_of
    assert provider_of("jev-1.14.0") == "typesafe" and "typesafe" in PROVIDER_COLOR
    assert provider_of("gpt-5.6-luna+jev-1.14.0@x") == "blend" and provider_of("claude-haiku-5-5") == "anthropic"
