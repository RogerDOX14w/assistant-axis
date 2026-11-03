"""The production entry for description judging (judge_descriptions.py)."""
import asyncio
import json

import pytest

from results_analysis import judge_descriptions as jd
from results_analysis import judge_tier_cost_eval as ev
from results_analysis.tests.test_judge_tier_cost_eval import (  # noqa: F401 -- the fixture
    AXES, ENTITIES, FakeAnthropic, FakeGeminiBatch, FakeOpenAI, FlakyOpenAI, batch_score, world,
)


def test_the_decision_is_the_default():
    args = jd.build_parser().parse_args(["--axes_file", "x"])
    assert (args.entities_per_call, args.passes, args.judge_model) == (20, 2, None)
    # Gemini joined the default on 2026-11-03 (Roger: "Luna + Haiku + Gemini at 2x each")
    assert jd.DESCRIPTION_JUDGES == ("gpt-5.6-luna", "claude-haiku-5-5", "gemini-3.1-flash-lite")
    assert jd.DESCRIPTION_RUBRIC == "b10" and args.name_format == "judge_label" and args.transport == "auto"


def test_a_pass_runs_the_tool_as_the_grid_did():
    args = jd.build_parser().parse_args(["--axes_file", "a.tsv", "--budget_usd", "5"])
    argv = jd.pass_argv(args, "gpt-5.6-luna", 2)
    flags = dict(zip(argv[::2], argv[1::2]))
    assert flags["--judge_model"] == "gpt-5.6-luna" and flags["--rubric"] == "b10" and flags["--entities_per_call"] == "20"
    assert flags["--shuffle_seed"] == "2" and flags["--cell_label"] == "@b10n20s2" and flags["--budget_usd"] == "5.0"
    assert flags["--max_tokens"] == "1200" and flags["--axes_file"] == "a.tsv"       # the grid's cap at N=20
    assert jd.max_tokens_for("claude-haiku-5-5", 20) == 3000                          # its Haiku cap
    assert jd.max_tokens_for("gemini-3.1-flash-lite", 20) == 1200
    assert "--request_setting" not in flags                                           # no reasoning: judge.py's table


def _in_process(monkeypatch):
    """The tool in this process, one pass at a time (it keeps a run's settings in module state)."""
    monkeypatch.setattr(jd, "MAX_CONCURRENT_JUDGES", 1)
    monkeypatch.setattr(jd, "run_tool", lambda argv: asyncio.run(ev.main_async([*argv, "--batch_poll_seconds", "0"])))


def _args(world, *extra):
    return ["--axes_file", str(world.axes2), "--experiments_dir", str(world.exp), "--instructions_dir", str(world.data),
            "--entities_per_call", "3", "--requests_per_second", "1000", *extra]


def test_a_run_writes_the_passes_the_averages_and_the_blend(world, monkeypatch):
    _in_process(monkeypatch)
    flex, anthropic, gemini = FakeOpenAI(), FakeAnthropic(), FakeGeminiBatch()
    monkeypatch.setattr(ev, "make_openai_client", lambda service_tier=None: flex)
    monkeypatch.setattr(ev, "make_anthropic_client", lambda: anthropic)
    monkeypatch.setattr(ev, "make_gemini_client", lambda: gemini)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used")
    assert jd.main(_args(world)) == 0
    tier = world.exp / f"{AXES[0][0]}_tier_eval"
    names = {p.name for p in tier.iterdir()}
    trio = "gpt-5.6-luna+claude-haiku-5-5+gemini-3.1-flash-lite@b10n3x2"     # the three judges since 2026-11-03
    assert {"gpt-5.6-luna@b10n3s1", "gpt-5.6-luna@b10n3s2", "gpt-5.6-luna@b10n3x2", "claude-haiku-5-5@b10n3s1", "claude-haiku-5-5@b10n3s2",
            "claude-haiku-5-5@b10n3x2", "gemini-3.1-flash-lite@b10n3x2", trio} <= names
    want = {e: float(batch_score(e, True)) for e in ENTITIES}
    blend = json.loads((tier / trio / "scores_descriptions.json").read_text())
    assert blend["result"] == want and len(blend["_provenance"]["averaged"]["sources"]) == 6
    assert blend["_provenance"]["averaged"]["judge_weights"] == pytest.approx(
        {"gpt-5.6-luna": 0.4, "claude-haiku-5-5": 0.3, "gemini-3.1-flash-lite": 0.3})
    assert all(c["reasoning_effort"] == "none" and c["service_tier"] == "flex" for c in flex.calls)
    usage = json.loads((tier / trio / "usage.json").read_text())
    assert set(usage["per_model"]) == {"gpt-5.6-luna:flex", "claude-haiku-5-5:batch", "gemini-3.1-flash-lite:batch"}
    # run again: nothing asked, nothing rederived
    n = len(flex.calls)
    assert jd.main(_args(world)) == 0 and len(flex.calls) == n


def test_a_pass_that_did_not_finish_is_not_averaged_and_a_rerun_finishes(world, monkeypatch):
    _in_process(monkeypatch)
    monkeypatch.setattr(ev, "REASK_ROUNDS", 0)
    monkeypatch.setattr(ev, "make_openai_client", lambda service_tier=None: FlakyOpenAI(1))
    extra = ("--judge_model", "gpt-5.6-luna", "--transport", "realtime")
    assert jd.main(_args(world, *extra)) == ev.EXIT_INCOMPLETE
    tier = world.exp / f"{AXES[0][0]}_tier_eval"
    assert not (tier / "gpt-5.6-luna@b10n3x2").exists()
    monkeypatch.setattr(ev, "make_openai_client", lambda service_tier=None: FakeOpenAI())
    assert jd.main(_args(world, *extra)) == 0
    assert (tier / "gpt-5.6-luna@b10n3x2" / "usage.json").exists()


def test_one_pass_and_one_judge_write_no_average(world, monkeypatch):
    _in_process(monkeypatch)
    monkeypatch.setattr(ev, "make_openai_client", lambda service_tier=None: FakeOpenAI())
    assert jd.main(_args(world, "--judge_model", "gpt-5.6-luna", "--passes", "1")) == 0
    names = {p.name for p in (world.exp / f"{AXES[0][0]}_tier_eval").iterdir()}
    assert names == {"gpt-5.6-luna@b10n3s1"}


def test_a_dry_run_writes_nothing(world, monkeypatch, capsys):
    _in_process(monkeypatch)
    assert jd.main(_args(world, "--dry_run")) == 0
    assert "Dry run only" in capsys.readouterr().out
    assert not list(world.exp.glob("*_tier_eval"))


@pytest.mark.parametrize("argv", [[], ["--axes_file", "a", "--pair", "x", "y"], ["--pair", "x", "y"], ["--axes_file", "a", "--passes", "0"]])
def test_bad_arguments(argv):
    with pytest.raises(SystemExit):
        jd.main(argv)


def test_a_single_pair(world, monkeypatch):
    _in_process(monkeypatch)
    monkeypatch.setattr(ev, "make_openai_client", lambda service_tier=None: FakeOpenAI())
    pos, neg = AXES[0][1], AXES[0][2]
    argv = ["--pair", pos, neg, "--pair_type", AXES[0][3], "--experiments_dir", str(world.exp), "--instructions_dir", str(world.data),
            "--entities_per_call", "3", "--judge_model", "gpt-5.6-luna", "--requests_per_second", "1000"]
    assert jd.main(argv) == 0
    assert (world.exp / f"{AXES[0][0]}_tier_eval" / "gpt-5.6-luna@b10n3x2" / "usage.json").exists()
