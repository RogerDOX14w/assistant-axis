"""The three Haiku 5.5 left-overs of the platform close-out (coding_plan_platform.md, "Close-out job", task 4):
the split filter's long system prompts sent cached on Haiku 5.5, the estimate's shares measured per model
(the split filter's and M3's unsure re-ask), and the rubric files' "Model" header lines (the pins unchanged).
No API call: fake clients and the recorded runs."""
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.tests.fake_anthropic import system_text
from assistant_axis.tests.split_replay import HAIKU, SONNET55, step_of_system
from assistant_axis.tests.test_gapgen_haiku55_switch import H55, items, run3
from data_analysis.gap_generation import split_cli

REPO = Path(__file__).resolve().parents[2]
CACHED = {"sense", "kind", "established", "gloss", "alignment"}


# --------------------------------------------------------------------------- 1. caching

class TestCaching:
    def test_the_prompts_over_the_minimum_are_cached_on_haiku_55_only(self):
        prompts = sr.load_all()
        on55 = {s for s, t in prompts.items() if SR.caches_system(t, H55)}
        assert on55 == CACHED                                   # sense and kind, and three more past 512 tokens
        assert not any(SR.caches_system(t, HAIKU) for t in prompts.values())       # 4.5: 4,096 minimum
        assert not any(SR.caches_system(t, SONNET55) for t in prompts.values())    # not in the table: as before
        assert not SR.caches_system("short prompt", H55)

    def test_the_runner_sends_cache_control_on_those_steps(self):
        client, r, res = run3()
        seen = {}
        for kw in client.calls:
            step = step_of_system(system_text(kw))
            blocks = kw["system"]
            seen.setdefault(step, set()).add(bool(blocks[0].get("cache_control")))
        for step, marks in seen.items():
            assert marks == {step in CACHED}, step
        assert {"sense", "kind", "vague"} <= set(seen)
        assert r.cached_steps()[H55] == [s for s in (*sr.NAMES, "probe", "comparison") if s in CACHED]
        assert r.cached_steps()[SONNET55] == []                  # the comparison model

    def test_haiku_45_runs_stay_uncached(self):
        client, r, _ = run3(model=HAIKU, readings=1)
        assert not any(kw["system"][0].get("cache_control") for kw in client.calls)
        assert r.cached_steps()[HAIKU] == []

    def test_cache_stats(self):
        recs = [{"step": "sense", "model": H55, "text": "x", "usage_raw": {"cache_creation_input_tokens": 800}},
                {"step": "sense", "model": H55, "text": "x", "usage_raw": {"cache_read_input_tokens": 800}},
                {"step": "sense", "model": H55, "text": "x", "usage_raw": {"cache_read_input_tokens": 800}},
                {"step": "vague", "model": H55, "text": "x", "usage_raw": {"input_tokens": 440}},
                {"step": "vague", "model": H55, "text": None, "usage_raw": None}]
        s = SR.cache_stats(recs)
        assert s[f"sense:{H55}"] == {"calls": 3, "calls_writing": 1, "calls_reading": 2, "cache_write_tokens": 800,
                                     "cache_read_tokens": 1600, "hit_rate": 0.6667}
        assert s[f"vague:{H55}"]["hit_rate"] == 0.0 and s[f"vague:{H55}"]["calls"] == 1


# --------------------------------------------------------------------------- 2. the estimate's shares

class TestShares:
    def test_the_tables_are_the_recorded_runs(self):
        """Each model's shares, recomputed from the runs the table names, round to the table's figures."""
        for frag, runs in split_cli.SHARES_SOURCE_RUNS.items():
            m = split_cli.measured_shares([REPO / "data" / "candidates" / "filter" / b for b in runs])
            assert len(m) == 1, frag
            got = next(iter(m.values()))
            for k, v in split_cli.SHARES_BY_MODEL[frag].items():
                assert round(got[k], 2) == pytest.approx(v), (frag, k)
            if "second_opinion" not in split_cli.SHARES_BY_MODEL[frag]:
                assert got["second_opinion"] is None
        h55 = split_cli.shares_for(H55)
        assert h55["readings_per_word"] < 1 and h55["same_sense"] < 0.1             # the over-statement's source
        assert split_cli.shares_for("claude-opus-5-5")["second_opinion"] == split_cli.SECOND_OPINION_SHARE
        assert split_cli.shares_for("some-new-model") == split_cli.DEFAULT_SHARES

    def test_measured_shares_counts_first_attempts_and_the_first_reading(self, tmp_path):
        import json
        d = tmp_path / "run"
        d.mkdir()
        (d / "run.json").write_text(json.dumps({"pipeline": "split", "model": H55, "second_model": SONNET55, "argv": []}))
        recs = ([{"stage": "sense", "step": "sense", "role": "first", "verdict_reading": v} for v in (1, 2, 3)] * 4
                + [{"stage": "established", "step": "established", "role": "first", "verdict_reading": 1}] * 5
                + [{"stage": "established_retry", "step": "established", "role": "first", "verdict_reading": 1}]
                + [{"stage": "same_sense", "step": "same_sense", "role": "first"}]
                + [{"stage": "alignment", "step": "alignment", "role": "first"}] * 3
                + [{"stage": "second_sense", "step": "sense", "role": "second"}])
        (d / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        m = split_cli.measured_shares([d])[H55]
        assert m == {"n_runs": 1, "n_words": 4, "n_words_second": 4, "readings_per_word": 1.25, "same_sense": 0.25,
                     "trait": 0.75, "second_opinion": 0.25}

    def test_the_split_estimate_uses_the_first_models_shares(self, monkeypatch):
        from assistant_axis.gapgen import freq
        monkeypatch.setattr(freq, "_ZIPF_FN", lambda w: 4.0)        # every word past the frequency floor
        its = items([f"w{i}" for i in range(100)])
        args = SimpleNamespace(model=H55, readings=1, second_model=SONNET55, no_probe=True, no_plain_reading=True,
                               compare_model=SONNET55, no_second_opinion=False, second_opinion_frac=0.10, third_model=None)
        est, plan = split_cli.build_split_estimate(its, args, "live")
        by = {x.label: x.n_calls for x in est.lines}
        sh = split_cli.SHARES_BY_MODEL["haiku-5-5"]
        assert by["established"] == math.ceil(sh["readings_per_word"] * 100)
        assert by["same sense"] == math.ceil(sh["same_sense"] * 100)
        assert by["alignment"] == math.ceil(sh["trait"] * 100)
        assert plan["n_second_opinion_est"] == math.ceil(sh["second_opinion"] * 100)
        assert by["second opinion: established"] == math.ceil(split_cli.shares_for(SONNET55)["readings_per_word"]
                                                             * plan["n_second_opinion_est"])
        assert plan["shares"][H55]["source"].startswith("measured on haiku-5-5")
        old = split_cli.build_split_estimate(its, SimpleNamespace(**{**vars(args), "model": "claude-x"}), "live")[0]
        assert {x.label: x.n_calls for x in old.lines}["established"] == 130                  # the default 1.3

    def test_the_unsure_reask_is_measured_per_relation_model(self):
        for frag, runs in NR.UNSURE_SOURCE_RUNS.items():
            m = NR.measured_unsure([REPO / "data" / "candidates" / "novelty" / b for b in runs])
            got = next(v for k, v in m.items() if frag in k)
            share, traits = NR.UNSURE_BY_MODEL[frag]
            assert got["share"] == pytest.approx(share, abs=0.005) and round(got["traits_per_reask"], 1) == traits
        assert NR.unsure_for(H55) == (0.14, 1.4) and NR.unsure_for(SONNET55) == (NR.UNSURE_SHARE, NR.UNSURE_TRAITS)
        st = NR.plan_estimate(n_candidates=100, n_scan=0, mean_listed=17.0, relation_text_chars=1343, trait_chars=260.0,
                              cand_chars=140.0, relation_model=H55)
        line = next(x for x in st["relation"].lines if x.label.startswith("unsure re-ask"))
        assert line.n_calls == 14 and "14% of candidates, 1.4 traits" in line.label
        st45 = NR.plan_estimate(n_candidates=100, n_scan=0, mean_listed=17.0, relation_text_chars=1343,
                                trait_chars=260.0, cand_chars=140.0, relation_model=HAIKU)
        assert next(x for x in st45["relation"].lines if x.label.startswith("unsure re-ask")).n_calls == 2


# --------------------------------------------------------------------------- 3. the header lines

def test_no_model_line_names_haiku_45_as_the_model_and_the_pins_hold():
    for name in (*sr.NAMES, "relation"):
        text = (sr.RUBRICS_DIR / sr.FILES.get(name, f"{name}.md")).read_text(encoding="utf-8")
        line = next(x for x in text.splitlines() if x.startswith("| **Model** |"))
        assert line.startswith("| **Model** | Haiku 5.5 from 2026-10-08"), name
    out = subprocess.run([sys.executable, str(REPO / "data_analysis" / "gap_generation" / "rubric_pins.py"), "check"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
