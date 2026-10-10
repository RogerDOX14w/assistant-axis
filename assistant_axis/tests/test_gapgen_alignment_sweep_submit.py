"""Alignment sweep: candidates and submission through the real registry API (tmp registry, tmp run dirs).
coding_plan_08_alignment_sweep.md § 8, ``submit``; task 7."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.embed import HashEmbedder
from assistant_axis.gapgen.generators.alignment_sweep import dedupe as D
from assistant_axis.gapgen.generators.alignment_sweep import extract as X
from assistant_axis.gapgen.generators.alignment_sweep import submit as S
from assistant_axis.gapgen.generators.alignment_sweep.sources import SOURCES
from assistant_axis.gapgen.registry import Registry, read_candidates
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.alignment_sweep_fakes import item, pole

PAIRS = [
    item(pole("same when unobserved", "This means acting the same whether or not one believes anyone is checking."),
         pole("behaves only when watched", "This means keeping the rules only while one believes someone is "
                                           "checking, and cutting corners when one feels unseen."),
         source_pole="vice", enactability="agentic-only"),
    item(pole("candid about work", "This means telling people what one really thinks of their work, flaws "
                                   "included."),
         pole("flatters the work", "This means praising whatever work one is shown so as to be liked, whatever "
                                   "its flaws.")),
]
MECH = item(pole("trains honestly", "This means x."), pole("games training", "This means y."), type_="mechanism")
NONE_ = item(pole("well-weighted", "This means a."), pole("badly weighted", "This means b."), enactability="none")


def world():
    items = X.apply_drops(X.build_items("model_spec:2026-08-18:consistency", PAIRS + [MECH, NONE_], ordinal=7,
                                        source=SOURCES["model_spec"], rank_start=1))
    vecs = D.embed_glosses(items, embedder=HashEmbedder(dim=128), cache=None, usage=MultiModelUsage())
    groups = D.dedup_groups(items, vecs, threshold=0.99)
    return items, groups, D.rewrite_partner_hints(items, groups)


def lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_two_candidates_per_pair_with_crossed_hints():
    items, groups, hints = world()
    cands = S.to_candidates(items, groups, hints, "r1")
    assert [c.surface for c in cands] == ["behaves only when watched", "same when unobserved", "candid about work",
                                          "flatters the work"]
    a, b = cands[0], cands[1]
    assert a.partner_hint == "same when unobserved" and b.partner_hint == "behaves only when watched"
    assert a.gloss_hint.startswith("This means keeping the rules") and b.gloss_hint.startswith("This means acting")
    assert (a.generator, a.run_id, a.rank, a.score, a.sense_id) == ("alignment_sweep", "r1", 1, None, 1)
    assert a.source_ref == "model_spec:2026-08-18:consistency"
    assert all(isinstance(c, Candidate) for c in cands)


def test_mechanism_and_none_items_are_never_submitted():
    items, groups, hints = world()
    surfaces = {c.surface for c in S.to_candidates(items, groups, hints, "r1")}
    assert not surfaces & {"trains honestly", "games training", "well-weighted", "badly weighted"}


def test_deduped_poles_are_not_submitted_and_a_second_sense_gets_sense_2():
    extra = item(pole("tactful about work", "This means softening what one says about someone's work."),
                 pole("candid about work", "This means a different sense of candour about work entirely."),
                 source_pole="vice")                                     # "candid about work" as a vice: sense 2
    items = X.apply_drops(X.build_items("model_spec:v:c", PAIRS + [extra], ordinal=1, source=SOURCES["model_spec"],
                                        rank_start=1))
    dup = X.apply_drops(X.build_items("constitution:v:d", [PAIRS[0]], ordinal=2, source=SOURCES["constitution"],
                                      rank_start=4))
    allit = items + dup
    vecs = D.embed_glosses(allit, embedder=HashEmbedder(dim=128), cache=None, usage=MultiModelUsage())
    groups = D.dedup_groups(allit, vecs, threshold=0.99)
    cands = S.to_candidates(allit, groups, D.rewrite_partner_hints(allit, groups), "r1")
    surf = [(c.surface, c.sense_id) for c in cands]
    assert surf.count(("behaves only when watched", 1)) == 1                 # the constitution's copy deduped away
    assert ("candid about work", 1) in surf and ("candid about work", 2) in surf


@pytest.fixture
def env(tmp_path):
    items, groups, hints = world()
    cdir = tmp_path / "candidates"
    return items, groups, hints, cdir, cdir / "registry.jsonl"


def submit(env, run_id="r1", **kw):
    items, groups, hints, cdir, reg = env
    kw.setdefault("echo", lambda *a: None)
    return S.run_submit(run_id, items=items, groups=groups, hints=hints, registry_path=reg, candidates_dir=cdir, **kw)


def test_submit_writes_candidates_first_then_the_registry(env, monkeypatch):
    seen = {}
    real = S.submit_candidates

    def spy(cands, **kw):
        p = env[3] / "runs" / "alignment_sweep" / "r1" / "candidates.jsonl"
        seen["exists"] = p.exists() and len(lines(p)) == len(list(cands))
        return real(cands, **kw)
    monkeypatch.setattr(S, "submit_candidates", spy)
    summ = submit(env)
    assert seen["exists"] is True
    d = env[3] / "runs" / "alignment_sweep" / "r1"
    cands = lines(d / "candidates.jsonl")
    assert cands == [dataclasses.asdict(c) for c in S.to_candidates(*env[:3], "r1")]
    assert (d / "keys.txt").read_text().split() == summ.report_keys
    assert json.loads((d / "usage.json").read_text())["n_calls"] == 0
    run = json.loads((d / "run.json").read_text())
    assert run["sessions"][-1]["args"]["step"] == "submit" and run["n_emitted"] == 4
    items_map = json.loads((d / "submitted_items.json").read_text())
    assert items_map[0]["key"] == "behaves_only_when_watched#1" and items_map[0]["item_id"] == "ms007-1a"
    folded = Registry(env[4]).fold()
    assert set(folded) == set(summ.report_keys)
    src = folded["behaves_only_when_watched#1"]["sources"][0]
    assert src["partner_hint"] == "same when unobserved" and src["gloss_hint"]


def test_resubmittable_with_from_into_another_registry(env, tmp_path):
    submit(env)
    p = env[3] / "runs" / "alignment_sweep" / "r1" / "candidates.jsonl"
    from data_analysis.gap_generation import gap_registry as GR
    other = tmp_path / "main_checkout" / "registry.jsonl"
    other.parent.mkdir()
    assert GR.main(["--registry", str(other), "submit", "--from", str(p)]) == 0
    assert set(Registry(other).fold()) == set(Registry(env[4]).fold())
    assert [dataclasses.asdict(c) for c in read_candidates(p)] == lines(p)
    assert GR.main(["--registry", str(other), "submit", "--from", str(p)]) == 0           # idempotent
    assert len(Registry(other).fold()) == 4


def test_second_submit_is_a_noop(env):
    submit(env)
    d = env[3] / "runs" / "alignment_sweep" / "r1"
    before, reg_before = (d / "candidates.jsonl").read_bytes(), env[4].read_bytes()
    summ = submit(env)
    assert summ.report["n_new"] == 0 and summ.report["n_unchanged"] == 4
    assert (d / "candidates.jsonl").read_bytes() == before and env[4].read_bytes() == reg_before


def test_dry_run_leaves_the_registry_byte_identical(env):
    reg = env[4]
    reg.parent.mkdir(parents=True)
    reg.write_text('{"key": "x#1", "stem": "x"}\n')
    before = reg.read_bytes()
    summ = submit(env, dry_run=True)
    assert summ.dry_run and summ.run_dir is None
    assert reg.read_bytes() == before and not (env[3] / "runs").exists()


def test_followups_name_the_run_and_batch_ids():
    est = S.estimate_downstream_usd(90)
    cmds = "\n".join(S.followup_commands("2026-10-12a", est))
    assert "gap_registry.py submit --from data/candidates/runs/alignment_sweep/2026-10-12a/candidates.jsonl" in cmds
    assert "--batch-id 2026-10-12a_alignment_sweep --run alignment_sweep/2026-10-12a" in cmds
    assert "--pipeline split --transport live" in cmds and "--third-model claude-opus-5-5" in cmds
    assert "novelty_score.py score --batch-id 2026-10-12a_alignment_sweep" in cmds
    assert "--confirm-expensive" not in cmds


def test_estimate_at_the_censuses_measured_rates():
    from assistant_axis.gapgen.generators.censuses import submit as CS
    e = S.estimate_downstream_usd(90)
    assert e.m1_usd == pytest.approx(90 * CS.M1_USD_PER_WORD)
    assert e.m3_usd == pytest.approx(90 * CS.M1_PASS_RATE * CS.M3_USD_PER_PASSED_WORD)
    assert e.m3_high_usd == pytest.approx(e.m3_usd * S.M3_ALIGNMENT_RISK)
    assert e.gate_usd == pytest.approx(e.m1_usd + e.m3_high_usd)


class TestCostGuard:
    def fake(self, n):
        raw = [item(pole(f"virtue word{i}", "This means v."), pole(f"vice word{i}", "This means w."))
               for i in range(n // 2)]
        items = X.build_items("model_spec:v:c", raw, ordinal=1, source=SOURCES["model_spec"], rank_start=1)
        groups = [D.Group(rep=it.item_id, members=[it.item_id], min_cos=1.0, pole=it.pole) for it in items]
        hints = {g.rep: None for g in groups}
        return items, groups, hints

    def test_40000_rows_refused_without_the_recorded_go(self, tmp_path):
        items, groups, hints = self.fake(40_000)
        kw = dict(items=items, groups=groups, hints=hints, registry_path=tmp_path / "r.jsonl", candidates_dir=tmp_path,
                  dry_run=True, echo=lambda *a: None)
        est = S.estimate_downstream_usd(40_000)
        assert est.gate_usd > 20
        with pytest.raises(CostRefused):
            S.run_submit("big", budget_usd=10_000, **kw)
        with pytest.raises(CostRefused):
            S.run_submit("big", budget_usd=10_000, confirm_expensive=True, **kw)          # no --confirmed-by
        S.run_submit("big", budget_usd=10_000, confirm_expensive=True, confirmed_by="Roger, 2026-10-12", **kw)

    def test_over_budget_refused(self, tmp_path):
        items, groups, hints = self.fake(400)
        with pytest.raises(CostRefused):
            S.run_submit("b", items=items, groups=groups, hints=hints, registry_path=tmp_path / "r.jsonl",
                         candidates_dir=tmp_path, budget_usd=1.0, dry_run=True, echo=lambda *a: None)


def test_candidate_is_the_platform_class():
    assert S.Candidate is Candidate
