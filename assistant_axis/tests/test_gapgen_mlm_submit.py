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


def test_select_top_and_registry_stems():
    rows = table_rows()
    top = SB.select_top(rows, 3)
    assert [r["union_rank"] for r in top] == sorted(r["union_rank"] for r in top) and len(top) == 3
    assert all(r["eligible"] for r in top)
    # QUESTIONS 82 (revised): a stem already in the registry is submitted where it falls, and not counted in the
    # cut, so three new rows still make the cut; --count-registered counts it like any row
    reg = {top[0]["stem"]}
    sel = SB.select_top(rows, 3, registered_stems=reg)
    assert sel[:3] == top and len(sel) == 4 and sum(r["stem"] not in reg for r in sel) == 3
    assert SB.select_top(rows, 3, registered_stems=reg, count_registered=True) == top


def test_registry_stems_and_the_undecided_ones():
    rows = {"a#1": {"stem": "a"}, "b#1": {"stem": "b", "filter": {"verdict": "reject"}},
            "c#1": {"stem": "c", "filter": {"verdict": "trait"}},
            "d#1": {"stem": "d", "filter": {"verdict": "trait"}, "novelty": {"decision": "covered"}}}
    assert SB.registry_stems(rows) == ({"a", "b", "c", "d"}, {"a", "c"})


def test_registered_stems_are_submitted_but_never_counted(env):
    rows, cdir, reg_path = env
    first = submit(env, run_id="other", top_n=2)                        # another run registers the top two
    assert first.n_registered == 0
    registered, pending = SB.registry_stems(Registry(reg_path).fold())
    top2 = [r["stem"] for r in SB.select_top(rows, 2)]
    assert registered == set(top2) and pending == set(top2)             # no M1 verdict yet
    dry = submit(env, run_id="b", top_n=3, registered_stems=registered, pending_stems=pending, dry_run=True)
    assert (dry.n_selected, dry.n_registered, dry.n_counted) == (5, 2, 3)
    assert dry.estimate["n"] == 5                                        # undecided: this batch may pay for them
    assert submit(env, run_id="b", top_n=3, registered_stems=registered, dry_run=True).estimate["n"] == 3
    summ = submit(env, run_id="b", top_n=3, registered_stems=registered, pending_stems=pending)
    d = cdir / "runs" / "masked_lm" / "b"
    assert [c["surface"].lower() for c in lines(d / "candidates.jsonl")][:2] == top2
    a = json.loads((d / "run.json").read_text())["args"]
    assert a["registered_stems"] == sorted(top2) and a["n_counted"] == 3 and a["count_registered"] is False
    assert summ.report["n_merged"] == 2 and summ.report["n_new"] == 3   # merged into the existing rows, no new row
    for st in top2:
        gens = {(s["generator"], s["run_id"]) for s in Registry(reg_path).fold()[f"{st}#1"]["sources"]}
        assert gens == {("masked_lm", "other"), ("masked_lm", "b")}     # the overlap is recorded
    counted = submit(env, run_id="c", top_n=3, registered_stems=registered, count_registered=True, dry_run=True)
    assert (counted.n_selected, counted.n_counted) == (3, 3)


def test_the_kept_share_is_over_new_words(env, tmp_path):
    from assistant_axis.gapgen.generators.masked_lm import evaluate as E
    rows, cdir, reg_path = env
    submit(env, run_id="other", top_n=2)
    registered, _ = SB.registry_stems(Registry(reg_path).fold())
    submit(env, run_id="b", top_n=3, registered_stems=registered)
    reg = Registry(reg_path)
    for key in sorted(reg.fold()):
        reg.merge_block(key, "filter", {"verdict": "trait", "outcome": "trait"}, replace=True)
        stem = reg.fold()[key]["stem"]
        # the registered stems are kept (another run's review load); one of the three new ones is kept
        kept = stem in registered or stem == SB.select_top(rows, 3, registered_stems=registered)[2]["stem"]
        reg.merge_block(key, "novelty", {"decision": "new" if kept else "covered"}, replace=True)
    ev = E.evaluate_run("b", run_dir=cdir / "runs" / "masked_lm" / "b", table=rows, registry_rows=reg.fold(),
                        filter_dir=tmp_path / "f", novelty_dir=tmp_path / "n")
    assert (ev["n_registry_rows"], ev["n_new_rows"], ev["n_registered_at_submit"]) == (5, 3, 2)
    assert ev["measured_kept_share"] == pytest.approx(1 / 3, abs=1e-4) and ev["kept_new"] == 1
    assert ev["m3"]["kept"] == 3                                         # all five: three kept, two of them old


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


def test_the_wave_counts_only_new_rows():
    """QUESTIONS 82 (revised): a registered stem inside the cut is submitted and the cut goes one row further."""
    rows = classed_rows()
    singles0, multis0 = SB.select_wave(rows, kept_target=2, kept_share=0.5)
    reg = {singles0[0]["stem"]} | {r["stem"] for r in multis0}
    singles, multis = SB.select_wave(rows, kept_target=2, kept_share=0.5, registered_stems=reg)
    assert singles[:len(singles0)] == singles0 and len(singles) == len(singles0) + 1
    assert sum(r["stem"] not in reg for r in singles) == len(singles0)
    assert multis == multis0                              # every uncut row with a gloss still goes, none counted
    assert SB.select_wave(rows, kept_target=2, kept_share=0.5, registered_stems=reg, count_registered=True) == \
        (singles0, multis0)


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
    # registered uncut rows are submitted and left out of the projection (QUESTIONS 82): 8 x 0.5 = 4 kept
    summ = SB.run_submit("w1", registered_stems={r["stem"] for r in rows[10:]}, **kw)
    assert (summ.n_single, summ.n_multi, summ.n_registered, summ.n_counted) == (8, 30, 30, 8)
    assert summ.estimate["n"] == 8                        # decided registry rows cost nothing downstream


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
