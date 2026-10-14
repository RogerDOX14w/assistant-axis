"""Base-model generator, task 4: the sample plan, the sampler (fake backend), the bench table.  A real-model smoke
test runs only with ``GAPGEN_RUN_LOCAL=1`` and the model downloaded."""
import json
import os
from collections import Counter

import pytest

from assistant_axis.gapgen.generators.base_model import MODEL_ID
from assistant_axis.gapgen.generators.base_model import bench as BN
from assistant_axis.gapgen.generators.base_model import prompts as P
from assistant_axis.gapgen.generators.base_model import sampler as SM
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.base_model_fakes import FakeBackend
from assistant_axis.tests.test_gapgen_base_model_prompts import BUNDLE

SCHEMA = {"sample_id", "round", "index", "family", "prompt_sha256", "prompts_version", "seed_refs", "seed_words",
          "constraint", "header_variant", "partner_seed", "temperature", "top_p", "min_p", "max_new_tokens", "text",
          "n_prompt_tokens", "n_new_tokens", "stop_reason", "model"}


def lines(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_plan_is_deterministic_and_interleaved():
    a = SM.plan_samples(BUNDLE, round_n=1, n=300, seed=4)
    b = SM.plan_samples(BUNDLE, round_n=1, n=300, seed=4)
    assert [(s.sample_id, s.family, s.prompt.text) for s in a] == [(s.sample_id, s.family, s.prompt.text) for s in b]
    assert a[0].sample_id == "R1-000000" and a[-1].sample_id == "R1-000299"
    fams = Counter(s.family for s in a)
    assert set(fams) == set(P.FAMILIES) and fams["ai_assistant"] > fams["list_gloss"]
    # header variants cycle within each family
    for f in P.FAMILIES:
        vs = [s.prompt.header_variant for s in a if s.family == f]
        assert vs == [i % 10 for i in range(len(vs))]
    # a longer plan extends a shorter one (resume after raising --n)
    longer = SM.plan_samples(BUNDLE, round_n=1, n=400, seed=4)
    assert [s.prompt.text for s in longer[:300]] == [s.prompt.text for s in a]
    assert [s.prompt.text for s in SM.plan_samples(BUNDLE, round_n=1, n=300, seed=5)] != [s.prompt.text for s in a]


def test_t_grid_reuses_the_prompts():
    g = SM.plan_samples(BUNDLE, round_n=0, n=10, seed=0, temperatures=(0.8, 1.0, 1.2))
    assert len(g) == 30 and g[0].sample_id == "R0-t0.8-000000" and g[10].sample_id == "R0-t1-000000"
    by_t = {t: [s.prompt.text for s in g if s.temperature == t] for t in (0.8, 1.0, 1.2)}
    assert by_t[0.8] == by_t[1.0] == by_t[1.2]


def test_families_restriction():
    a = SM.plan_samples(BUNDLE, round_n=1, n=50, seed=0, families=("person", "ai_assistant"))
    assert {s.family for s in a} == {"person", "ai_assistant"}


def test_truncate_at_blank_line():
    assert SM.truncate_at_stop(" a, b, c.\n\nNext para") == (" a, b, c.", "blank_line")
    assert SM.truncate_at_stop(" a, b") == (" a, b", None)
    assert SM.truncate_at_stop("\n\nx") == ("", "blank_line")


def run(tmp_path, plan, backend, usage=None, **kw):
    usage = usage if usage is not None else MultiModelUsage()
    return SM.run_sampling(backend, plan, out_path=tmp_path / "samples.jsonl", usage=usage,
                           usage_path=tmp_path / "usage.json", echo=lambda *a: None, **kw), usage


def test_jsonl_schema_and_zero_cost_usage(tmp_path):
    plan = SM.plan_samples(BUNDLE, round_n=1, n=10, seed=0)
    stats, usage = run(tmp_path, plan, FakeBackend())
    recs = lines(tmp_path / "samples.jsonl")
    assert len(recs) == 10 and set(recs[0]) == SCHEMA
    r = recs[0]
    assert r["text"] == "stubborn, kind, generous, and fiercely loyal." and r["stop_reason"] == "blank_line"
    assert r["model"] == MODEL_ID and r["prompts_version"] == P.PROMPTS_VERSION and r["temperature"] == 1.0
    assert (r["top_p"], r["min_p"], r["max_new_tokens"]) == (0.95, 0.05, 80)
    u = json.loads((tmp_path / "usage.json").read_text())
    assert u["total_cost_usd"] == 0.0 and u["total_prompt_tokens"] > 0 and u["total_completion_tokens"] > 0
    assert u["n_calls"] == 10 and stats.n_new == 10


def test_resume_skips_done_and_appends(tmp_path):
    plan = SM.plan_samples(BUNDLE, round_n=1, n=10, seed=0)
    run(tmp_path, plan[:6], FakeBackend())
    first = (tmp_path / "samples.jsonl").read_text()
    be = FakeBackend()
    stats, _ = run(tmp_path, plan, be)
    assert stats.n_done_before == 6 and stats.n_new == 4 and sum(c["n"] for c in be.calls) == 4
    assert (tmp_path / "samples.jsonl").read_text().startswith(first)
    ids = [r["sample_id"] for r in lines(tmp_path / "samples.jsonl")]
    assert sorted(ids) == sorted(s.sample_id for s in plan) and len(ids) == len(set(ids))
    # nothing left: no call at all
    be2 = FakeBackend()
    run(tmp_path, plan, be2)
    assert be2.calls == []


def test_usage_written_on_an_interrupted_run(tmp_path):
    plan = SM.plan_samples(BUNDLE, round_n=1, n=12, seed=0)
    usage = MultiModelUsage.load_or_create(tmp_path / "usage.json")
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, plan, FakeBackend(batch_size=4, fail_on_call=2), usage=usage)
    u = json.loads((tmp_path / "usage.json").read_text())
    assert u["n_calls"] == 4 and len(lines(tmp_path / "samples.jsonl")) == 4
    # the resumed session adds to the same record
    usage2 = MultiModelUsage.load_or_create(tmp_path / "usage.json")
    run(tmp_path, plan, FakeBackend(batch_size=4), usage=usage2)
    assert json.loads((tmp_path / "usage.json").read_text())["n_calls"] == 12


def test_batches_share_a_temperature(tmp_path):
    plan = SM.plan_samples(BUNDLE, round_n=0, n=6, seed=0, temperatures=(0.8, 1.2))
    be = FakeBackend(batch_size=4)
    run(tmp_path, plan, be)
    assert sorted(c["temperature"] for c in be.calls) == [0.8, 0.8, 1.2, 1.2]
    assert all(c["top_p"] == 0.95 and c["min_p"] == 0.05 and c["max_new_tokens"] == 80 for c in be.calls)


def test_bench_table_and_reading():
    rows = BN.benchmark(FakeBackend(), ["p one", "p two three"], batch_sizes=(2, 4), clock=iter(range(0, 100, 2)).__next__,
                        warmup=False)
    assert [r["batch_size"] for r in rows] == [2, 4]
    assert all(r["tok_per_s"] > 0 for r in rows) and all("hours_per_20k" in r for r in rows)
    assert "stays on the Mac" in BN.reading([{"batch_size": 64, "tok_per_s": 400.0}])
    assert "below" in BN.reading([{"batch_size": 64, "tok_per_s": 40.0}])


@pytest.mark.skipif(os.environ.get("GAPGEN_RUN_LOCAL") != "1", reason="set GAPGEN_RUN_LOCAL=1 to load the real model")
def test_real_model_smoke():  # pragma: no cover - needs the 16 GB model and a device
    from assistant_axis.gapgen.embed import hf_snapshot_present
    if not hf_snapshot_present(MODEL_ID):
        pytest.skip("Qwen3-8B-Base not downloaded")
    be = SM.HFBackend(device=os.environ.get("GAPGEN_DEVICE", "mps"), batch_size=2)
    gens = be.generate(["Adjectives that describe a person's character:\nbrave, blunt,"] * 2, temperature=1.0,
                       top_p=0.95, min_p=0.05, max_new_tokens=16)
    assert len(gens) == 2 and all(g.n_new_tokens > 0 for g in gens)


# --------------------------------------------------------------------------- batches by a token budget (2026-10-14)

class TokenBackend(FakeBackend):
    """A fake whose tokenizer counts one token per word (``prompt_tokens``)."""

    def prompt_tokens(self, prompts):
        return [len(p.split()) for p in prompts]


def test_make_batches_caps_by_size_and_by_budget():
    specs = list("abcdefgh")
    lengths = [2, 2, 2, 3, 5, 5, 9, 20]
    got = SM.make_batches(specs, lengths, batch_size=4, token_budget=12)
    assert [b for b in got] == [["a", "b", "c", "d"], ["e", "f"], ["g"], ["h"]]
    for b in got:                      # never over the budget, unless one prompt alone is longer
        n = [lengths[specs.index(x)] for x in b]
        assert len(b) <= 4 and (len(b) * max(n) <= 12 or len(b) == 1)
    assert SM.make_batches(specs, lengths, batch_size=4, token_budget=None) == [list("abcd"), list("efgh")]
    assert SM.make_batches(specs, lengths, batch_size=4, token_budget=0) == [list("abcd"), list("efgh")]
    assert SM.make_batches([], [], batch_size=4) == []


def test_prompt_lengths_tokenizer_or_char_proxy():
    assert SM.prompt_lengths(TokenBackend(), ["a b c", "d"]) == [3, 1]
    assert SM.prompt_lengths(FakeBackend(), ["abcdefgh", "abcdefghi", ""]) == [2, 3, 1]


def test_budget_shrinks_the_long_batches_keeps_order_and_resume(tmp_path):
    plan = SM.plan_samples(BUNDLE, round_n=1, n=40, seed=0)
    be = TokenBackend(batch_size=8)
    lens = dict(zip([s.sample_id for s in plan], be.prompt_tokens([s.prompt.text for s in plan])))
    budget = 8 * sorted(lens.values())[len(lens) // 2]          # batch 8 at the median prompt
    recorded = []
    real = be.generate

    def spy(prompts, **kw):
        recorded.append(list(prompts))
        return real(prompts, **kw)
    be.generate = spy
    run(tmp_path, plan, be, token_budget=budget)
    by_text = {s.prompt.text: s.sample_id for s in plan}
    sizes = [len(b) for b in recorded]
    assert max(sizes) <= 8 and min(sizes) < 8                     # batch_size still the cap; long prompts in fewer
    for b in recorded:
        n = [lens[by_text[p]] for p in b]
        assert len(b) * max(n) <= budget or len(b) == 1
    # the order is the order without a budget: shortest first
    ids = [r["sample_id"] for r in lines(tmp_path / "samples.jsonl")]
    want = [s.sample_id for s in sorted(plan, key=lambda s: (len(s.prompt.text), s.sample_id))]
    assert ids == want
    # resume: nothing left, no call; a partial file is completed without repeating a sample
    be2 = TokenBackend(batch_size=8)
    run(tmp_path, plan, be2, token_budget=budget)
    assert be2.calls == []
    p2 = tmp_path / "second"
    p2.mkdir()
    run(p2, plan[:15], TokenBackend(batch_size=8), token_budget=budget)
    run(p2, plan, TokenBackend(batch_size=8), token_budget=budget)
    ids2 = [r["sample_id"] for r in lines(p2 / "samples.jsonl")]
    assert sorted(ids2) == sorted(s.sample_id for s in plan) and len(ids2) == len(set(ids2))


def test_no_budget_is_batch_size_alone(tmp_path):
    plan = SM.plan_samples(BUNDLE, round_n=1, n=10, seed=0)
    be = TokenBackend(batch_size=4)
    run(tmp_path, plan, be, token_budget=None)
    assert [c["n"] for c in be.calls] == [4, 4, 2]


def test_cli_passes_the_token_budget(tmp_path, monkeypatch):
    from data_analysis.gap_generation import base_model_generator as G
    args = G.build_parser().parse_args(["sample", "--round", "1"])
    assert args.token_budget == SM.DEFAULT_TOKEN_BUDGET == 1024
    assert G.build_parser().parse_args(["sample", "--round", "1", "--token-budget", "0"]).token_budget == 0
