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
        # the fake rows have count 1; the guard is tested on all of them, below the default floor of 2
        kw.setdefault("min_count", 1)
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


class TestCountFloor:
    """Gate audit 3 (Roger, 2026-10-12): the floor is a recorded setting, 2 at 2,000 samples, stated with the
    sample size of the table it is applied to, because a count is a different rate at every sample size."""

    def test_the_documented_default(self):
        assert (SB.DEFAULT_MIN_COUNT, SB.DEFAULT_MIN_COUNT_N_SAMPLES) == (2, 2000)
        assert "gate audit 3" in SB.DEFAULT_MIN_COUNT_SOURCE and "Roger, 2026-10-12" in SB.DEFAULT_MIN_COUNT_SOURCE
        rows = table_rows()
        assert SB.select_rows(rows) == SB.select_rows(rows, min_count=2)
        assert all(r["count"] >= 2 for r in SB.select_rows(rows))

    def test_the_record_at_the_size_it_was_chosen_for(self):
        f = SB.floor_record(2, n_samples=2000)
        assert f == {"min_count": 2, "n_samples": 2000, "per_1k_samples": 1.0, "chosen_at_n_samples": 2000,
                     "source": SB.DEFAULT_MIN_COUNT_SOURCE, "flag_given": False}
        assert SB.floor_note(f) is None

    def test_a_table_of_another_size_prints_a_note(self):
        # the audit's case: a floor carried unchanged from the 2,000-sample pilot to the 20,000-sample run
        f = SB.floor_record(2, n_samples=20_000, explicit=True)
        assert f["chosen_at_n_samples"] == 2000 and f["per_1k_samples"] == 0.1
        note = SB.floor_note(f)
        assert "chosen at 2,000 samples" in note and "20,000" in note and "--min-count" in note

    def test_another_value_is_set_for_this_table(self):
        f = SB.floor_record(3, n_samples=20_000, explicit=True)
        assert f["chosen_at_n_samples"] == 20_000 and f["source"].startswith("--min-count")
        assert SB.floor_note(f) is None
        assert SB.floor_note(SB.floor_record(2, n_samples=None)).startswith("NOTE: the table's sample size")

    def test_run_json_and_submit_report_record_the_floor_with_its_sample_size(self, env):
        out = []
        submit(env, n_samples=2000, echo=out.append)
        d = env[1] / "runs" / "base_model" / "pilot"
        a = json.loads((d / "run.json").read_text())["args"]
        rep = json.loads((d / "submit_report.json").read_text())
        for rec in (a["floor"], rep["floor"]):
            assert rec["min_count"] == 2 and rec["n_samples"] == 2000 and rec["chosen_at_n_samples"] == 2000
        assert a["min_count"] == 2
        assert any("count floor: 2 at 2000 samples" in x for x in out)


class TestEstimateOnNewRows:
    """Gate audit 3, proposal 6: M1 and M3 reuse a verdict the registry already holds, so the gated estimate
    counts only the rows without one; the all-rows figure is printed beside it.  The pilot's estimate charged
    all 467 rows ($3.74 batched) for a real $0.14."""

    REG = {"generous#1": {"filter": {"verdict": "trait"}, "novelty": {"decision": "covered", "run_id": "b0"}},
           "warm#1": {"filter": {"verdict": "trait"}},                    # M1 passed it, M3 has not decided
           "unflappable#1": {"filter": {"verdict": "reject"}}}           # M3 never takes a reject

    def test_downstream_need(self):
        rows = SB.select_rows(table_rows(), min_count=1)
        need = SB.downstream_need(rows, self.REG)
        assert need["n_decided"] == 2 and need["n_m3_only"] == 1 and need["n_m1"] == len(rows) - 3
        assert SB.downstream_need(rows, None)["n_m1"] == len(rows)       # no registry: every row is new
        # a novelty block without a run (a stand-in) is no decision
        assert SB.downstream_need(rows, {"warm#1": {"filter": {"verdict": "trait"}, "novelty": {"decision": "new"}}}
                                  )["n_m3_only"] == 1

    def test_a_free_floor_reject_is_taken_again(self):
        """The floor's free reject is no verdict M1 keeps once a source rescues the word (gate audit 1, defect
        F3), and a selected row is one the table found rescued or above the floor; a paid probe cut is kept."""
        rows = SB.select_rows(table_rows(), min_count=1)
        reg = {"generous#1": {"filter": {"verdict": "reject", "rule": "floor"}},
               "warm#1": {"filter": {"verdict": "reject", "model": None, "tags": ["too_rare"]},
                          "freq": {"hard_reject": True}},
               "unflappable#1": {"filter": {"verdict": "reject", "rule": "probe", "model": "claude-haiku-4-5"}}}
        need = SB.downstream_need(rows, reg)
        assert need["n_floor_rejected_retaken"] == 2 and need["n_decided"] == 1
        assert need["n_m1"] == len(rows) - 1

    def test_the_estimate_charges_m3_only_rows_m3_alone(self):
        e = SB.estimate_downstream_usd(10, n_m3_only=4)
        assert e.m1_usd == pytest.approx(10 * 0.0072)
        assert e.m3_usd == pytest.approx((10 * 0.80 + 4) * 0.011)
        assert e.m3_usd_high == pytest.approx((10 * 0.95 + 4) * 0.011)
        assert "+ 4 already passed by M1 (M3 only)" in e.format()

    def test_the_gate_reads_the_new_rows_and_both_are_printed(self, tmp_path):
        rows = fake_rows(2_000)
        reg = {f"w{i}#1": {"filter": {"verdict": "trait"}, "novelty": {"decision": "new", "run_id": "b0"}}
               for i in range(1, 1_901)}                              # 1,900 of the 2,000 already decided
        out = []
        summ = SB.run_submit("g1", table=rows, round_n=1, min_count=1, registry_path=tmp_path / "r.jsonl",
                             candidates_dir=tmp_path, dry_run=True, echo=out.append, registry_rows=reg)
        # all rows would be $32.00 live, over the $15 default; the 100 new ones are $1.60 and pass the gate
        assert summ.estimate_all_rows["total_usd"] == pytest.approx(32.0)
        assert summ.estimate["total_usd"] == pytest.approx(100 * (0.0072 + 0.8 * 0.011))
        assert summ.need == {"n_rows": 2000, "n_m1": 100, "n_m3_only": 0, "n_decided": 1900,
                             "n_floor_rejected_retaken": 0, "registry_rows": 1900}
        text = "\n".join(out)
        assert "all rows, as if none had a verdict: downstream estimate for 2000 words" in text
        assert "the gate reads this one): downstream estimate for 100 words" in text
        # and with nothing recorded the two are the same, so the guard still refuses the full price
        with pytest.raises(CostRefused):
            SB.run_submit("g1", table=rows, round_n=1, min_count=1, registry_path=tmp_path / "r.jsonl",
                          candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None)

    def test_the_followups_carry_the_new_rows_estimate(self, tmp_path):
        rows = fake_rows(50)
        reg = {f"w{i}#1": {"filter": {"verdict": "trait"}} for i in range(1, 51)}
        summ = SB.run_submit("g1", table=rows, round_n=1, min_count=1, registry_path=tmp_path / "r.jsonl",
                             candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None, registry_rows=reg)
        assert summ.estimate["m1_usd"] == 0 and summ.estimate["n_m3_only"] == 50
        assert "# M1, estimate $0.00" in summ.followups[1]

    def test_run_json_records_both_estimates(self, env):
        submit(env, registry_rows=self.REG)
        a = json.loads((env[1] / "runs" / "base_model" / "pilot" / "run.json").read_text())["args"]
        assert a["downstream_need"]["n_decided"] == 2 and a["downstream_need"]["n_m3_only"] == 1
        assert a["estimate"]["total_usd"] < a["estimate_all_rows"]["total_usd"]
        rep = json.loads((env[1] / "runs" / "base_model" / "pilot" / "submit_report.json").read_text())
        assert rep["estimate_usd"] == a["estimate"]["total_usd"]
        assert rep["estimate_all_rows_usd"] == a["estimate_all_rows"]["total_usd"]


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
