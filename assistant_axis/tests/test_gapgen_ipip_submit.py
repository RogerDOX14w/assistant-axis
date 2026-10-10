"""IPIP generator, submission through the real registry API (tmp registry, tmp run dirs)."""
import dataclasses
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.ipip import submit as S
from assistant_axis.gapgen.registry import Registry

MANIFEST = {"tool": "ipip_generator.py download", "entries": [{"key": "item_list", "sha256": "ab"}]}


def naming(label, gloss="This means something.", is_trait=True, antonym=None):
    return {"reason": "r", "label": label, "stem": label.replace(" ", "_").replace("-", "_"), "gloss": gloss,
            "antonym_label": antonym, "antonym_gloss": None, "is_trait": is_trait, "ambiguity_flag": False,
            "single_word_exists": False, "notes": []}


def rows():
    return [
        {"granularity": 350, "cluster_id": 17, "consensus": "kept", "bipolar": True, "items": ["H1", "H2", "H3"],
         "poles": [{"pole": "a", "items": ["H1", "H2"], "blind": naming("chore-prompt", antonym="last-minute"),
                    "hinted": naming("diligent")},
                   {"pole": "b", "items": ["H3"], "blind": naming("last-minute", antonym="chore-prompt"),
                    "hinted": naming("procrastinating")}]},
        {"granularity": 350, "cluster_id": 18, "consensus": "kept", "bipolar": False, "items": ["H4", "H5"],
         "poles": [{"pole": "a", "items": ["H4", "H5"], "blind": naming("likes painting", is_trait=False),
                    "hinted": naming("artistic interests", is_trait=False)}]},
        {"granularity": 350, "cluster_id": 19, "consensus": "kept", "bipolar": False, "items": ["H6", "H7"],
         "poles": [{"pole": "a", "items": ["H6", "H7"]}]},                       # not named yet
        {"granularity": 350, "cluster_id": 20, "consensus": "loose", "bipolar": False, "items": ["H8", "H9"],
         "poles": [{"pole": "a", "items": ["H8", "H9"], "blind": naming("loose one")}]},
    ]


def lines(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def test_candidates_fields_and_reciprocal_partners():
    cands, counts = S.to_candidates(rows(), "2026-10-14a")
    assert [c.surface for c in cands] == ["chore-prompt", "last-minute"]
    a, b = cands
    assert a == Candidate(surface="chore-prompt", generator="ipip", run_id="2026-10-14a", rank=17, score=None,
                          gloss_hint="This means something.", sense_id=1, source_ref="ipip:g350:c017a",
                          partner_hint="last-minute")
    assert b.partner_hint == "chore-prompt" and b.source_ref == "ipip:g350:c017b"
    assert all(c.score is None and c.gloss_hint for c in cands)
    assert counts == {"n_kept_clusters": 3, "n_poles": 4, "n_named": 3, "n_trait": 2, "n_not_trait": 1,
                      "n_unnamed": 1, "n_loose_skipped": 1, "n_selected_out": 0, "n_submitted": 2,
                      "label_choice": "blind"}


def test_hinted_choice_and_pole_selection():
    cands, _ = S.to_candidates(rows(), "r", label_choice="hinted")
    assert [(c.surface, c.partner_hint) for c in cands] == [("diligent", "procrastinating"),
                                                            ("procrastinating", "diligent")]
    cands, counts = S.to_candidates(rows(), "r", poles={(17, "b")})
    assert [c.surface for c in cands] == ["last-minute"] and counts["n_selected_out"] == 1
    assert cands[0].partner_hint == "chore-prompt"              # the partner is named even when not submitted
    assert S.parse_poles_file("c017a\n# comment\nipip:g350:c018a\n17b\n") == {(17, "a"), (18, "a"), (17, "b")}


@pytest.fixture
def env(tmp_path):
    cdir = tmp_path / "candidates"
    return cdir, cdir / "registry.jsonl"


def submit(env, run_id="r1", **kw):
    cdir, reg = env
    kw.setdefault("echo", lambda *a: None)
    return S.run_submit(350, run_id, rows=rows(), sources_manifest=MANIFEST, clusters_sha256="cafe",
                        registry_path=reg, candidates_dir=cdir, **kw)


def test_submit_writes_run_files_and_registry(env):
    cdir, reg = env
    summ = submit(env)
    d = cdir / "runs" / "ipip" / "r1"
    cands = lines(d / "candidates.jsonl")
    assert cands == [dataclasses.asdict(c) for c in S.to_candidates(rows(), "r1")[0]]
    run = json.loads((d / "run.json").read_text())
    args = run["args"]
    assert args["granularity"] == 350 and args["n"] == 2 and args["label_choice"] == "blind"
    assert args["clusters_sha256"] == "cafe" and args["sources_manifest"] == MANIFEST and args["estimate"]["total_usd"] > 0
    assert json.loads((d / "usage.json").read_text())["n_calls"] == 0
    assert (d / "keys.txt").read_text().split() == ["chore_prompt#1", "last_minute#1"]
    folded = Registry(reg).fold()
    src = folded["chore_prompt#1"]["sources"][0]
    assert src["partner_hint"] == "last-minute" and src["source_ref"] == "ipip:g350:c017a" and src["score"] is None
    assert any("traithood_filter.py --batch-id r1_ipip --run ipip/r1 --pipeline split" in x for x in summ.followups)
    assert any("novelty_score.py score --batch-id r1_ipip --run ipip/r1" in x for x in summ.followups)
    assert any("gap_registry.py submit --from" in x for x in summ.followups)


def test_candidates_file_written_before_submit(env, monkeypatch):
    seen = {}
    real = S.submit_candidates

    def spy(cands, **kw):
        p = env[0] / "runs" / "ipip" / "r1" / "candidates.jsonl"
        seen["ok"] = p.exists() and len(lines(p)) == len(list(cands))
        return real(cands, **kw)
    monkeypatch.setattr(S, "submit_candidates", spy)
    submit(env)
    assert seen["ok"] is True


def test_resubmit_is_a_noop(env):
    submit(env)
    d = env[0] / "runs" / "ipip" / "r1"
    before, reg_before = (d / "candidates.jsonl").read_bytes(), env[1].read_bytes()
    summ = submit(env)
    assert summ.report["n_new"] == 0 and summ.report["n_unchanged"] == 2
    assert (d / "candidates.jsonl").read_bytes() == before and env[1].read_bytes() == reg_before


def fake_rows(n):
    out = []
    for i in range(n):
        out.append({"granularity": 350, "cluster_id": i + 1, "consensus": "kept", "bipolar": False, "items": ["H1"],
                    "poles": [{"pole": "a", "items": ["H1"], "blind": naming(f"word{i}")}]})
    return out


class TestCostGuard:
    """The platform's gate (``cost.confirm_or_abort``, decision 9): an estimate over ``--budget-usd`` is refused
    whatever the flags (a larger budget is typed instead); over $20 needs ``--confirm-expensive`` and
    ``--confirmed-by``."""

    def run(self, tmp_path, n, **kw):
        return S.run_submit(350, "g1", rows=fake_rows(n), sources_manifest={}, clusters_sha256=None,
                            registry_path=tmp_path / "r.jsonl", candidates_dir=tmp_path, dry_run=True,
                            echo=lambda *a: None, **kw)

    def test_estimate(self):
        e = S.estimate_downstream_usd(1000)
        assert e["m1_usd"] == pytest.approx(1000 * S.M1_USD_PER_WORD)
        assert e["m3_usd"] == pytest.approx(1000 * S.M1_PASS_RATE * S.M3_USD_PER_PASSED_WORD)

    def test_5000_poles_refused_even_with_the_flag(self, tmp_path):
        with pytest.raises(CostRefused):
            self.run(tmp_path, 5000, budget_usd=100, confirm_expensive=True)          # no --confirmed-by
        with pytest.raises(CostRefused):
            self.run(tmp_path, 5000, confirm_expensive=True)

    def test_1000_poles_over_the_default_budget(self, tmp_path):
        with pytest.raises(CostRefused):
            self.run(tmp_path, 1000)                                                 # $16.88 > $8
        with pytest.raises(CostRefused):
            self.run(tmp_path, 1000, confirm_expensive=True)                         # no flag raises the cap
        self.run(tmp_path, 1000, budget_usd=17)                                      # a typed budget does

    def test_dry_run_leaves_the_registry_byte_identical(self, tmp_path):
        reg = tmp_path / "c" / "registry.jsonl"
        reg.parent.mkdir()
        reg.write_text('{"key": "x#1", "stem": "x"}\n')
        before = reg.read_bytes()
        summ = S.run_submit(350, "d1", rows=rows(), sources_manifest={}, clusters_sha256=None, registry_path=reg,
                            candidates_dir=tmp_path / "c", dry_run=True, echo=lambda *a: None)
        assert summ.dry_run and summ.run_dir is None
        assert reg.read_bytes() == before and not (tmp_path / "c" / "runs").exists()


def test_candidate_is_the_platform_class():
    assert S.Candidate is Candidate
