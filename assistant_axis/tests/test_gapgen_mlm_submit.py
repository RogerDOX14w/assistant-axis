"""Masked-LM generator, task 10: submission through the real registry API (tmp registry, tmp run dirs), the
selection (pilot top-N; the wave sized in review terms), the downstream estimate and its guard, the follow-ups
(plan section 8, ``submit``)."""
import dataclasses
import json
import math
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.masked_lm import submit as SB
from assistant_axis.gapgen.generators.masked_lm.pll import Contrast
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.test_gapgen_mlm_table import build


def table_rows():
    con = {"roberta": {"kind": Contrast(2.9, False, False, -1.0, -3.9, -4.5),
                       "cruel": Contrast(1.2, False, False, -1.0, -2.2, -3.0)}}
    return build(contrasts=con)


@pytest.fixture
def env(tmp_path):
    cdir = tmp_path / "candidates"
    return table_rows(), cdir, cdir / "registry.jsonl"


def submit(env, run_id="pilot", **kw):
    rows, cdir, reg = env
    kw.setdefault("echo", lambda *a: None)
    kw.setdefault("top_n", 50)
    return SB.run_submit(run_id, table=rows, registry_path=reg, candidates_dir=cdir, table_sha256="ff",
                         generation={"single:roberta": {"revision": "722cf37"}}, **kw)


def lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_candidates_carry_rank_score_gloss_and_source():
    rows = table_rows()
    cands = {c.surface: c for c in SB.to_candidates(SB.select_top(rows, 50), "2026-10-20a")}
    k = cands["kind"]
    assert isinstance(k, Candidate) and k.generator == "masked_lm" and k.sense_id == 1
    row = next(r for r in rows if r["stem"] == "kind")
    assert k.rank == row["union_rank"] and k.score == 2.9               # score = trait_contrast
    assert k.gloss_hint == row["gloss_hint"] and k.gloss_hint.startswith("having or showing")
    assert k.source_ref == "mlm:variant_b:roberta:noun_avowed"
    assert cands["plain"].score is None and cands["Kantian"].source_ref == "mlm:variant_b:roberta:noun_avowed"
    assert "blargy" not in cands                                         # ineligible rows are never selected


def test_select_top_and_registry_exclusion():
    rows = table_rows()
    top = SB.select_top(rows, 3)
    assert [r["union_rank"] for r in top] == sorted(r["union_rank"] for r in top) and len(top) == 3
    assert all(r["eligible"] for r in top)
    ex = SB.select_top(rows, 3, exclude_stems={top[0]["stem"]})
    assert top[0] not in ex and ex[0] == top[1]


def classed_rows():
    rows = table_rows()
    for i, r in enumerate(rows):
        r["token_class"] = "multiword" if "-" in (r["surface"] or "") else ("subword" if i % 4 == 3 else "single")
    return rows


def test_the_wave_is_sized_in_kept_terms():
    rows = classed_rows()
    singles, multis = SB.select_wave(rows, kept_target=2, kept_share=0.5)
    # subword rows are single words: they join the rank cut (the default; acceptance report, deviation)
    assert len(singles) == math.ceil(2 / 0.5) and all(SB.row_class(r) in ("single", "subword") for r in singles)
    assert any(SB.row_class(r) == "subword" for r in singles)
    assert [r["union_rank"] for r in singles] == sorted(r["union_rank"] for r in singles)
    # every eligible multiword row with a gloss, whatever its rank; none without
    want = [r for r in rows if r["eligible"] and SB.row_class(r) == "multiword" and r["gloss_hint"]]
    assert multis == sorted(want, key=lambda r: r["union_rank"]) and multis
    assert SB.select_wave(rows, kept_target=2, kept_share=0.5, multi_cap=0)[1] == []
    more, _ = SB.select_wave(rows, kept_target=2, kept_share=0.25)
    assert len(more) >= len(singles)                      # a lower kept share submits more single words
    with pytest.raises(ValueError):
        SB.select_wave(rows, kept_share=0)
    with pytest.raises(ValueError):
        SB.select_wave(rows, uncut=("single",))


def test_the_literal_reading_exempts_subword_rows_too():
    rows = classed_rows()
    singles, multis = SB.select_wave(rows, kept_target=2, kept_share=0.5, uncut=("multiword", "subword"))
    assert all(SB.row_class(r) == "single" for r in singles)
    assert {SB.row_class(r) for r in multis} == {"subword", "multiword"} and all(r["gloss_hint"] for r in multis)


def test_the_review_load_guard(tmp_path):
    rows = fake_rows(40)
    for r in rows[10:]:
        r.update(token_class="multiword", gloss_hint="a phrase")
    kw = dict(table=rows, kept_target=4, kept_share=0.5, registry_path=tmp_path / "r.jsonl",
              candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None, budget_usd=5)
    with pytest.raises(SB.ReviewLoadExceeded) as exc:
        SB.run_submit("w1", **kw)                        # (8 + 30) x 0.5 = 19 kept against 1.5 x 4
    assert "--multi-cap" in str(exc.value) and "Roger" in str(exc.value)
    summ = SB.run_submit("w1", multi_cap=2, **kw)        # the cap is the decision
    assert (summ.n_single, summ.n_multi) == (8, 2)


def test_exactly_one_selection_mode(env):
    with pytest.raises(ValueError):
        submit(env, top_n=None)
    with pytest.raises(ValueError):
        submit(env, top_n=5, kept_target=300)


def test_submit_writes_run_files_and_registry(env):
    rows, cdir, reg = env
    summ = submit(env)
    d = cdir / "runs" / "masked_lm" / "pilot"
    cands = lines(d / "candidates.jsonl")
    assert cands == [dataclasses.asdict(c) for c in SB.to_candidates(SB.select_top(rows, 50), "pilot")]
    run = json.loads((d / "run.json").read_text())
    a = run["args"]
    assert a["table_sha256"] == "ff" and a["generation"] == {"single:roberta": {"revision": "722cf37"}}
    assert a["mode"] == "top 50" and "trait_contrast" in a["score"]
    u = json.loads((d / "usage.json").read_text())
    assert u["total_cost_usd"] == 0.0 and u["n_calls"] == 0          # the generator's own: zero calls
    assert set(Registry(reg).fold()) == set((d / "keys.txt").read_text().split())
    assert summ.report["n_new"] == len(cands)
    row = Registry(reg).fold()["kind#1"]
    src = [s for s in row["sources"] if s["generator"] == "masked_lm"][0]
    assert src["score"] == 2.9 and src["gloss_hint"].startswith("having or showing")


def test_candidates_file_written_before_registry_append(env, monkeypatch):
    seen = {}
    real = SB.submit_candidates

    def spy(cands, **kw):
        p = env[1] / "runs" / "masked_lm" / "pilot" / "candidates.jsonl"
        seen["ok"] = p.exists() and len(lines(p)) == len(list(cands))
        return real(cands, **kw)
    monkeypatch.setattr(SB, "submit_candidates", spy)
    submit(env)
    assert seen["ok"] is True


def test_resubmit_is_a_noop(env):
    submit(env)
    d = env[1] / "runs" / "masked_lm" / "pilot"
    before, reg_before = (d / "candidates.jsonl").read_bytes(), env[2].read_bytes()
    summ = submit(env)
    assert summ.report["n_new"] == 0 and env[2].read_bytes() == reg_before
    assert (d / "candidates.jsonl").read_bytes() == before


def fake_rows(n):
    return [{"surface": f"w{i}", "stem": f"w{i}", "eligible": True, "union_rank": i, "gloss_hint": None,
             "trait_contrast": 1.0, "best_pass": "single:roberta", "best_frame": "disp_nature", "zipf": 3.0,
             "token_class": "single", "corpus_stem_match": False} for i in range(1, n + 1)]


class TestCostGuard:
    def run(self, tmp_path, n, **kw):
        kw.setdefault("budget_usd", SB.DEFAULT_BUDGET_USD)
        kw.setdefault("top_n", n)
        return SB.run_submit("g1", table=fake_rows(n), registry_path=tmp_path / "r.jsonl", candidates_dir=tmp_path,
                             dry_run=True, echo=lambda *a: None, **kw)

    def test_estimate(self):
        e = SB.estimate_downstream_usd(1000)
        assert e.m1_usd == pytest.approx(7.2) and e.m3_usd == pytest.approx(1000 * 0.88 * 0.011)
        assert SB.estimate_downstream_usd(1000, transport="batches").total_usd == pytest.approx(e.total_usd * 0.5)
        assert e.pass_rate == 0.88 and e.total_usd_high > e.total_usd
        assert "unmeasured for this generator" in e.format() and "unmeasured" in e.assumptions["source"]

    def test_ten_thousand_rows_live_need_the_recorded_go(self, tmp_path):
        assert SB.estimate_downstream_usd(10_000).total_usd > 20
        with pytest.raises(CostRefused):
            self.run(tmp_path, 10_000, budget_usd=200, confirm_expensive=True)        # no --confirmed-by
        with pytest.raises(CostRefused):
            self.run(tmp_path, 10_000, budget_usd=200, confirmed_by="Roger")          # no --confirm-expensive
        self.run(tmp_path, 10_000, budget_usd=200, confirm_expensive=True, confirmed_by="Roger, 2026-10-20")

    def test_over_budget_is_refused(self, tmp_path):
        with pytest.raises(CostRefused):
            self.run(tmp_path, 1_000)                                   # $16.88 live over the $5 default
        with pytest.raises(CostRefused):
            self.run(tmp_path, 1_000, confirm_expensive=True)           # the flag does not raise the cap
        self.run(tmp_path, 1_000, budget_usd=17)
        self.run(tmp_path, 1_000, transport="batches", budget_usd=9)

    def test_dry_run_writes_nothing(self, tmp_path):
        reg = tmp_path / "c" / "registry.jsonl"
        reg.parent.mkdir()
        reg.write_text('{"key": "x#1", "stem": "x"}\n')
        before = reg.read_bytes()
        summ = SB.run_submit("d1", table=fake_rows(5), top_n=5, registry_path=reg, candidates_dir=tmp_path / "c",
                             dry_run=True, echo=lambda *a: None)
        assert summ.dry_run and summ.run_dir is None
        assert reg.read_bytes() == before and not (tmp_path / "c" / "runs").exists()


def test_followup_commands():
    est = SB.estimate_downstream_usd(300, transport="live")
    cmds = "\n".join(SB.followup_commands("2026-10-20-pilot", est))
    assert "gap_registry.py submit --from data/candidates/runs/masked_lm/2026-10-20-pilot/candidates.jsonl" in cmds
    assert "--batch-id 2026-10-20-pilot_masked_lm" in cmds and "--run masked_lm/2026-10-20-pilot" in cmds
    assert "--pipeline split" in cmds and cmds.count("--transport live") == 2 and "--confirm-expensive" not in cmds
    assert "masked_lm_generator.py report --run-id 2026-10-20-pilot" in cmds
    assert "recovery_test.py --generator masked_lm --run-id 2026-10-20-pilot" in cmds
    big = SB.estimate_downstream_usd(4000, transport="batches")
    bc = SB.followup_commands("full", big)
    assert all("--transport batches" in c for c in bc[1:3])
    for cmd, part in ((bc[1], big.m1_usd), (bc[2], big.m3_usd)):
        assert ("--confirm-expensive --confirmed-by" in cmd) == (1.5 * part + 2 > 20), cmd


def test_package_makes_no_llm_import():
    pkg = Path(SB.__file__).parent
    for f in pkg.glob("*.py"):
        text = f.read_text()
        for mod in ("anthropic", "openai"):
            assert f"import {mod}" not in text and f"from {mod}" not in text, f"{f.name} imports {mod}"
