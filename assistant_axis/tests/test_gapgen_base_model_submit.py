"""Base-model generator, task 7: submission through the real registry API (tmp registry, tmp run dirs), the
downstream estimate and its guard, the follow-up commands."""
import dataclasses
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.base_model import sense as SE
from assistant_axis.gapgen.generators.base_model import submit as SB
from assistant_axis.gapgen.registry import Registry
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.test_gapgen_base_model_table import build

SAMPLING = {"round": 1, "key": {"seed": 0, "prompts_version": 1, "temperatures": [1.0]},
            "bundle": {"census_table_sha256": "ab", "n_bios": 2}, "model": "Qwen/Qwen3-8B-Base"}


def settled(rows, *, chosen="dictionary"):
    """The table after the sense step (QUESTIONS 56), without embedding or calling anything: every two-sided
    row carries a decision, so `submit` lets it through."""
    for r in rows:
        if SE.two_sided(r):
            r[SE.BLOCK] = {"oewn": r["gloss_hint"], "sample": r["sample_gloss"], "cosine": 0.9,
                           "divergent": chosen == "sample", "floor": SE.DIVERGENCE_COSINE, "embedder": "hash",
                           "chosen": chosen, "chosen_gloss": r["sample_gloss"] if chosen == "sample"
                           else r["gloss_hint"], "legible": True, "reason": "test", "model": SE.MODEL,
                           "prompt_version": SE.GLOSS_SENSE_VERSION, "prompt_sha256": SE.wording_sha256(),
                           "at": "2026-10-11T00:00:00+00:00"}
    return rows


def table_rows():
    rows, _ = build()
    return settled(rows)


@pytest.fixture
def env(tmp_path):
    rows = table_rows()
    cdir = tmp_path / "candidates"
    usage = MultiModelUsage()
    usage.charge("Qwen/Qwen3-8B-Base", 1200, 300)
    up = tmp_path / "round1_usage.json"
    usage.write_json(up)
    return rows, cdir, cdir / "registry.jsonl", up


def submit(env, run_id="pilot", **kw):
    rows, cdir, reg, up = env
    kw.setdefault("echo", lambda *a: None)
    kw.setdefault("budget_usd", 5.0)
    return SB.run_submit(run_id, table=rows, round_n=1, registry_path=reg, candidates_dir=cdir,
                         sampling_record=SAMPLING, sampling_usage_path=up, table_sha256="ff", **kw)


def lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_selection_is_eligible_rows_by_count():
    rows = table_rows()
    sel = SB.select_rows(rows)
    assert all(r["eligible"] for r in sel) and [r["rank"] for r in sel] == sorted(r["rank"] for r in sel)
    assert {r["stem"] for r in SB.select_rows(rows, min_count=2)} == {"generous", "warm", "unflappable"}
    assert {r["stem"] for r in SB.select_rows(rows, families=("contrast",))} == {"warm", "unflappable"}


def test_candidates_fields():
    rows = table_rows()
    cands = SB.to_candidates(SB.select_rows(rows), "pilot")
    g = next(c for c in cands if c.surface == "generous")
    assert (g.generator, g.run_id, g.score, g.sense_id, g.rank) == ("base_model", "pilot", 3.0, 1, 1)
    assert g.source_ref == "base_model:list:R1-000000" and g.partner_hint is None
    w = next(c for c in cands if c.surface == "warm")
    assert w.partner_hint == "cold" and w.source_ref == "base_model:person:R1-000001"
    u = next(c for c in cands if c.surface == "unflappable")
    assert u.gloss_hint.startswith("not easily perturbed")            # the OEWN hint, not the sampled gloss
    assert isinstance(g, Candidate)


class TestSenseGate:
    """Roger, QUESTIONS 56: M1 and M3 must see one settled sense, so submission refuses while a selected row
    still carries two."""

    def test_an_unsettled_row_refuses_the_submission(self, tmp_path):
        rows, _ = build()                                  # straight from `parse`: no sense step yet
        with pytest.raises(SB.SenseUnresolved) as exc:
            SB.run_submit("g1", table=rows, round_n=1, registry_path=tmp_path / "r.jsonl",
                          candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None)
        msg = str(exc.value)
        assert "sense --round 1" in msg and "unflappable" in msg and "QUESTIONS 56" in msg
        assert not (tmp_path / "runs").exists()

    def test_a_one_sided_row_never_blocks(self, tmp_path):
        rows = [r for r in build()[0] if not SE.two_sided(r)]
        assert rows and SB.run_submit("g2", table=rows, round_n=1, registry_path=tmp_path / "r.jsonl",
                                      candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None).n_selected

    def test_the_chosen_sense_is_what_the_candidate_carries(self):
        rows = settled([r for r in build()[0]], chosen="sample")
        u = next(c for c in SB.to_candidates(SB.select_rows(rows), "pilot") if c.surface == "unflappable")
        assert u.gloss_hint == "staying calm when everything goes wrong"      # the sample's reading, chosen
        st = SB.strata(SB.select_rows(rows))
        assert st["sense_divergent"] >= 1 and st["sense_from_sample"] >= 1


def test_the_run_records_the_sense_decisions(env):
    submit(env)
    d = env[1] / "runs" / "base_model" / "pilot"
    gs = json.loads((d / "run.json").read_text())["args"]["gloss_sense"]
    assert gs["n_two_sided"] >= 1 and gs["n_unresolved"] == 0
    assert gs["prompt_sha256"] == SE.wording_sha256()


def test_submit_writes_run_files_and_registry(env):
    rows, cdir, reg, _ = env
    summ = submit(env)
    d = cdir / "runs" / "base_model" / "pilot"
    cands = lines(d / "candidates.jsonl")
    assert cands == [dataclasses.asdict(c) for c in SB.to_candidates(SB.select_rows(rows), "pilot")]
    run = json.loads((d / "run.json").read_text())
    a = run["args"]
    assert a["round"] == 1 and a["prompts_version"] == 1 and a["temperature"] == [1.0] and a["table_sha256"] == "ff"
    assert a["model"] == "Qwen/Qwen3-8B-Base" and a["seed_bundle"] == SAMPLING["bundle"]
    u = json.loads((d / "usage.json").read_text())
    assert u["total_cost_usd"] == 0.0 and u["total_prompt_tokens"] == 1200      # the sampler's tokens, at $0
    folded = Registry(reg).fold()
    assert set(folded) == set((d / "keys.txt").read_text().split())
    assert summ.report["n_new"] == len(cands)


def test_candidates_file_written_before_registry_append(env, monkeypatch):
    seen = {}
    real = SB.submit_candidates

    def spy(cands, **kw):
        p = env[1] / "runs" / "base_model" / "pilot" / "candidates.jsonl"
        seen["ok"] = p.exists() and len(lines(p)) == len(list(cands))
        return real(cands, **kw)
    monkeypatch.setattr(SB, "submit_candidates", spy)
    submit(env)
    assert seen["ok"] is True


def test_resubmit_is_a_noop(env):
    submit(env)
    d = env[1] / "runs" / "base_model" / "pilot"
    before, reg_before = (d / "candidates.jsonl").read_bytes(), env[2].read_bytes()
    summ = submit(env)
    assert summ.report["n_new"] == 0 and env[2].read_bytes() == reg_before
    assert (d / "candidates.jsonl").read_bytes() == before


def fake_rows(n):
    return [{"surface": f"w{i}", "stem": f"w{i}", "eligible": True, "count": 1, "rank": i, "gloss_hint": None,
             "partner_seed": None, "first_sample_id": f"R1-{i:06d}", "first_family": "list", "families": {"list": 1},
             "form": "adjective"} for i in range(1, n + 1)]


class TestCostGuard:
    def run(self, tmp_path, n, **kw):
        kw.setdefault("budget_usd", SB.DEFAULT_BUDGET_USD)
        return SB.run_submit("g1", table=fake_rows(n), round_n=1, registry_path=tmp_path / "r.jsonl",
                             candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None, **kw)

    def test_estimate(self):
        e = SB.estimate_downstream_usd(1000)
        assert e.m1_usd == pytest.approx(7.2) and e.m3_usd == pytest.approx(1000 * 0.80 * 0.011)
        assert SB.estimate_downstream_usd(1000, transport="batches").total_usd == pytest.approx(e.total_usd * 0.5)

    def test_the_pass_rate_is_the_measured_0_80_with_0_95_as_a_high_case(self):
        # Roger, QUESTIONS 55: 0.80 from the two least-curated measured waves (roget pilot 81.4%, alignment
        # sweep 78.6%); the old 0.5 placeholder was below everything measured and understated the estimate.
        assert (SB.M1_PASS_RATE_ASSUMED, SB.M1_PASS_RATE_HIGH) == (0.80, 0.95)
        e = SB.estimate_downstream_usd(1000)
        assert e.pass_rate == 0.80 and e.pass_rate_high == 0.95
        assert e.m3_usd_high == pytest.approx(1000 * 0.95 * 0.011)
        assert e.total_usd_high == pytest.approx(e.m1_usd + e.m3_usd_high)
        assert e.total_usd_high > e.total_usd
        assert e.assumptions["m1_pass_rate"] == 0.80 and e.assumptions["m1_pass_rate_high"] == 0.95
        assert "81.4%" in e.assumptions["source"] and "78.6%" in e.assumptions["source"]
        # both lines are printed, and the gate reads the central one
        text = e.format()
        assert "high case at 95%" in text and "at 80% passed" in text
        assert f"${e.total_usd:.2f}" in text and f"${e.total_usd_high:.2f}" in text

    def test_the_high_case_is_printed_but_never_gated_on(self, tmp_path):
        # 1,500 rows live: $10.80 M1 + $13.20 M3 = $24.00 at 0.80, $26.48 at 0.95.  A budget above the
        # central estimate and below the high case is accepted: the gate reads the 80% line.
        e = SB.estimate_downstream_usd(1500)
        assert e.total_usd < 25 < e.total_usd_high
        self.run(tmp_path, 1_500, budget_usd=25, confirm_expensive=True, confirmed_by="Roger, 2026-10-12")

    def test_over_the_line_refused_without_the_recorded_go(self, tmp_path):
        with pytest.raises(CostRefused):
            self.run(tmp_path, 10_000, budget_usd=200, confirm_expensive=True)      # no --confirmed-by
        with pytest.raises(CostRefused):
            self.run(tmp_path, 10_000, budget_usd=200, confirmed_by="Roger")         # no --confirm-expensive
        self.run(tmp_path, 10_000, budget_usd=200, confirm_expensive=True, confirmed_by="Roger, 2026-10-12")

    def test_over_the_default_budget(self, tmp_path):
        # 2,000 rows: $32.00 live at the measured 0.80 pass rate ($14.40 M1 + $17.60 M3), over the $15 default
        # and the $20 line.  (At the retired 0.5 placeholder the same rows printed $25.00, which is the
        # understatement QUESTIONS 55 removed.)
        with pytest.raises(CostRefused):
            self.run(tmp_path, 2_000)
        self.run(tmp_path, 2_000, budget_usd=35, confirm_expensive=True, confirmed_by="Roger, 2026-10-12")
        # batched, the same rows are $16.00 and fit a cap live would not
        self.run(tmp_path, 2_000, transport="batches", budget_usd=20)
        with pytest.raises(CostRefused):
            self.run(tmp_path, 2_000, transport="batches")        # still over the $15 default

    def test_dry_run_writes_nothing(self, tmp_path):
        reg = tmp_path / "c" / "registry.jsonl"
        reg.parent.mkdir()
        reg.write_text('{"key": "x#1", "stem": "x"}\n')
        before = reg.read_bytes()
        summ = SB.run_submit("d1", table=fake_rows(5), round_n=1, registry_path=reg, candidates_dir=tmp_path / "c",
                             dry_run=True, echo=lambda *a: None)
        assert summ.dry_run and summ.run_dir is None
        assert reg.read_bytes() == before and not (tmp_path / "c" / "runs").exists()


def test_followup_commands():
    est = SB.estimate_downstream_usd(800, transport="live")
    cmds = "\n".join(SB.followup_commands("2026-10-12a", est))
    assert "gap_registry.py submit --from data/candidates/runs/base_model/2026-10-12a/candidates.jsonl" in cmds
    assert "--batch-id 2026-10-12a_base_model" in cmds and "--run base_model/2026-10-12a" in cmds
    assert cmds.count("--transport live") == 2 and "--confirm-expensive" not in cmds
    big = SB.estimate_downstream_usd(4000, transport="batches")
    bc = SB.followup_commands("full", big)
    assert all("--transport batches" in c for c in bc[1:3])
    for cmd, part in ((bc[1], big.m1_usd), (bc[2], big.m3_usd)):
        assert ("--confirm-expensive --confirmed-by" in cmd) == (1.5 * part + 2 > 20), cmd
    assert "recovery_test.py --generator base_model --run-id full" in "\n".join(bc)


def test_package_makes_no_llm_import():
    pkg = Path(SB.__file__).parent
    for f in pkg.glob("*.py"):
        text = f.read_text()
        for mod in ("anthropic", "openai"):
            assert f"import {mod}" not in text and f"from {mod}" not in text, f"{f.name} imports {mod}"
