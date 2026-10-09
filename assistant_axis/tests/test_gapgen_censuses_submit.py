"""Census generator, submission through the real registry API (tmp registry, tmp run dirs)."""
import dataclasses
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.censuses import submit as S
from assistant_axis.gapgen.generators.censuses.ingest import TableRow
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.censuses_fakes import fixture_table

MANIFEST = [{"key": "tda_properties", "sha256": "ab", "licence": "CC0 1.0"},
            {"key": "allport_I", "sha256": "cd", "licence": "CC BY 4.0"}]


@pytest.fixture
def env(tmp_path):
    rows, _, _ = fixture_table(tmp_path)
    cdir = tmp_path / "candidates"
    return rows, cdir, cdir / "registry.jsonl"


def submit(env, stage="tda", run_id="r1", **kw):
    rows, cdir, reg = env
    kw.setdefault("echo", lambda *a: None)
    return S.run_submit(stage, run_id, table=rows, sources_manifest=MANIFEST, registry_path=reg,
                        candidates_dir=cdir, **kw)


def lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_stage_selection(env):
    rows = env[0]
    assert [r.surface for r in S.select_stage(rows, "tda")] == ["kind", "sunny", "abandoned", "gloomy", "obscurish"]
    # QUESTIONS 29: the column-IV-only word ("a la mode") leaves allport_hi for allport_iv
    assert len(S.select_stage(rows, "allport_hi")) == 5 and len(S.select_stage(rows, "allport_probe")) == 2
    assert [r.surface for r in S.select_stage(rows, "allport_iv")] == ["a la mode"]
    # QUESTIONS 34: the known-but-rare words, never the unknown ones
    assert [r.surface for r in S.select_stage(rows, "allport_rare")] == ["quaintish"]
    # every eligible Allport-only row is in exactly one of the three Allport stages
    stages = [set(r.stem for r in S.select_stage(rows, st)) for st in ("allport_hi", "allport_probe", "allport_iv")]
    assert not (stages[0] & stages[1]) and not (stages[0] & stages[2]) and not (stages[1] & stages[2])
    assert set().union(*stages) == {r.stem for r in rows if r.eligible and r.stage in ("allport_hi", "allport_probe")}
    with pytest.raises(ValueError):
        S.select_stage(rows, "extra")


def test_candidates_fields(env):
    rows = env[0]
    tda = S.to_candidates(S.select_stage(rows, "tda"), "r1")
    k = tda[0]
    assert (k.surface, k.generator, k.run_id, k.rank, k.score, k.sense_id, k.source_ref) == (
        "kind", "censuses", "r1", 1, 0.98, 1, "tda:1")
    assert k.gloss_hint.startswith("having or showing")
    hi = S.to_candidates(S.select_stage(rows, "allport_hi"), "r1")
    ag = next(c for c in hi if c.surface == "agitated")
    assert ag.score is None and ag.source_ref == "allport:II:2" and ag.sense_id == 1


def test_submit_writes_run_files_and_registry(env):
    rows, cdir, reg = env
    summ = submit(env)
    d = cdir / "runs" / "censuses" / "r1"
    assert summ.run_dir == str(d)
    cands = lines(d / "candidates.jsonl")
    expected = [dataclasses.asdict(c) for c in S.to_candidates(S.select_stage(rows, "tda"), "r1")]
    assert cands == expected
    assert list(cands[0]) == ["surface", "generator", "run_id", "rank", "score", "gloss_hint", "sense_id",
                              "source_ref", "partner_hint"]
    run = json.loads((d / "run.json").read_text())
    assert run["args"]["sources"] == MANIFEST and run["args"]["stage"] == "tda" and run["n_emitted"] == 5
    usage = json.loads((d / "usage.json").read_text())
    assert usage["n_calls"] == 0 and usage["total_cost_usd"] == 0
    keys = (d / "keys.txt").read_text().split()
    assert keys == ["kind#1", "sunny#1", "abandoned#1", "gloomy#1", "obscurish#1"]
    rep = json.loads((d / "submit_report.json").read_text())
    assert rep["n_new"] == 5 and rep["n_keys"] == 5
    folded = Registry(reg).fold()
    assert set(folded) == set(keys)
    src = folded["kind#1"]["sources"][0]
    assert src["score"] == 0.98 and src["source_ref"] == "tda:1" and src["gloss_hint"]


def test_candidates_file_written_before_submit(env, monkeypatch):
    seen = {}
    real = S.submit_candidates

    def spy(cands, **kw):
        p = env[1] / "runs" / "censuses" / "r1" / "candidates.jsonl"
        seen["exists"] = p.exists() and len(lines(p)) == len(list(cands))
        return real(cands, **kw)
    monkeypatch.setattr(S, "submit_candidates", spy)
    submit(env)
    assert seen["exists"] is True


def test_second_submit_is_noop(env):
    submit(env)
    d = env[1] / "runs" / "censuses" / "r1"
    before = (d / "candidates.jsonl").read_bytes()
    reg_before = env[2].read_bytes()
    summ = submit(env)
    assert summ.report["n_new"] == 0 and summ.report["n_unchanged"] == 5
    assert (d / "candidates.jsonl").read_bytes() == before and env[2].read_bytes() == reg_before
    assert json.loads((d / "run.json").read_text())["n_emitted"] == 5


def test_every_nth():
    assert S.every_nth(list(range(12)), 5) == [0, 5, 10]
    assert S.every_nth(list(range(12)), 5, 2) == [2, 7]
    assert S.every_nth(list(range(3)), 1) == [0, 1, 2]
    for bad in ((0, 0), (5, 5), (5, -1)):
        with pytest.raises(ValueError):
            S.every_nth([1], *bad)


def test_pilot_sample_submits_every_nth(env):
    summ = submit(env, every_nth_n=2, offset=1)
    d = env[1] / "runs" / "censuses" / "r1"
    assert [c["surface"] for c in lines(d / "candidates.jsonl")] == ["sunny", "gloomy"]
    assert summ.n_stage == 5 and summ.n_selected == 2
    assert json.loads((d / "run.json").read_text())["args"]["every_nth"] == 2


def fake_rows(n):
    return [TableRow(schema_version=1, surface=f"w{i}", stem=f"w{i}", label=f"w{i}", allport=None, in_merged=None,
                     tda={"row": i, "prop": 0.9}, zipf=3.0, freq_hard_reject=False, freq_probe_band=False,
                     freq_rescue=None, freq_platform=None, wordnet=None, gloss_hint=None, repaired_from=None,
                     unknown_word=False, eligible=True, ineligible_reason=None, stage="tda", rank=i, score=0.9,
                     corpus_stem_match=False, queue_stem_match=False) for i in range(1, n + 1)]


class TestCostGuard:
    def run(self, tmp_path, n, **kw):
        return S.run_submit("tda", "g1", table=fake_rows(n), sources_manifest=[], registry_path=tmp_path / "r.jsonl",
                            candidates_dir=tmp_path, dry_run=True, echo=lambda *a: None, **kw)

    def test_estimate(self):
        e = S.estimate_downstream_usd(1000)
        m1 = 1000 * S.M1_USD_PER_WORD
        m3 = 1000 * S.M1_PASS_RATE * S.M3_USD_PER_PASSED_WORD
        assert e.m1_usd == pytest.approx(m1) and e.m3_usd == pytest.approx(m3) and e.total_usd == pytest.approx(m1 + m3)
        b = S.estimate_downstream_usd(1000, transport="batches")
        assert b.total_usd == pytest.approx((m1 + m3) * S.BATCH_FACTOR)

    def test_over_budget_refused_then_accepted(self, tmp_path):
        with pytest.raises(CostRefused):
            self.run(tmp_path, 300)                                  # $6.06 > $5 default
        self.run(tmp_path, 300, budget_usd=7)

    def test_over_the_line_needs_recorded_go(self, tmp_path):
        with pytest.raises(CostRefused):
            self.run(tmp_path, 40_000, budget_usd=1000, confirm_expensive=True)   # no --confirmed-by
        with pytest.raises(CostRefused):
            self.run(tmp_path, 1_500, budget_usd=40, confirmed_by="Roger")       # no --confirm-expensive
        self.run(tmp_path, 1_500, budget_usd=40, confirm_expensive=True, confirmed_by="Roger, 2026-10-08")

    def test_dry_run_writes_nothing(self, tmp_path):
        rows, _, _ = fixture_table(tmp_path)
        reg = tmp_path / "c" / "registry.jsonl"
        reg.parent.mkdir()
        reg.write_text('{"key": "x#1", "stem": "x"}\n')
        before = reg.read_bytes()
        summ = S.run_submit("tda", "d1", table=rows, sources_manifest=[], registry_path=reg,
                            candidates_dir=tmp_path / "c", dry_run=True, echo=lambda *a: None)
        assert summ.dry_run and summ.run_dir is None
        assert reg.read_bytes() == before and not (tmp_path / "c" / "runs").exists()


def test_followup_commands():
    est = S.estimate_downstream_usd(564)
    cmds = S.followup_commands("2026-10-08-pilot", est)
    joined = "\n".join(cmds)
    assert "--run censuses/2026-10-08-pilot" in joined and "--batch-id 2026-10-08-pilot_censuses" in joined
    assert "gap_registry.py submit --file data/candidates/runs/censuses/2026-10-08-pilot/candidates.jsonl" in joined
    assert "--confirm-expensive" not in joined
    big = S.followup_commands("full", S.estimate_downstream_usd(2818))
    # each step's cap is 1.5 x its estimate + $2; a step whose cap passes the $20 line asks for the flag
    est = S.estimate_downstream_usd(2818)
    for cmd, part in ((big[1], est.m1_usd), (big[2], est.m3_usd)):
        assert ("--confirm-expensive --confirmed-by" in cmd) == (1.5 * part + 2 > S.HARD_LINE_USD), cmd


def test_extra_list(tmp_path):
    p = tmp_path / "nouns.txt"
    p.write_text("# Saucier type nouns\nbrute\n\nScholar  # a comment\n1x2\n")
    rows = S.extra_rows(p)
    assert [(r.surface, r.rank) for r in rows] == [("brute", 2), ("scholar", 4)]
    c = S.to_candidates(rows, "x1", extra_name="nouns.txt")
    assert c[0].source_ref == "extra:nouns.txt:2" and c[0].score is None
    S.run_submit("extra", "x1", table=[], sources_manifest=[], extra_list=p, registry_path=tmp_path / "r.jsonl",
                 candidates_dir=tmp_path, echo=lambda *a: None)
    assert len(Registry(tmp_path / "r.jsonl").fold()) == 2


def test_package_makes_no_llm_import():
    pkg = Path(S.__file__).parent
    for f in pkg.glob("*.py"):
        text = f.read_text()
        for mod in ("anthropic", "openai"):
            assert f"import {mod}" not in text and f"from {mod}" not in text, f"{f.name} imports {mod}"


def test_candidate_is_the_platform_class():
    assert S.Candidate is Candidate
