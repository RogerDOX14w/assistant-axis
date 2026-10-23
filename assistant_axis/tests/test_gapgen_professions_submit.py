"""Test 15 of coding plan 16 (§ 8): B's submission.  ``net_new`` against the corpus (with ``renamed_from``), the seed
queue and the registry (a held role row and a role-aimed row resubmitted for their provenance and not counted; a
trait row of the same surface no obstacle); ``select_wave``'s arithmetic (0.5 x 300 / 0.4 = 375); ``to_candidates``'
fields; ``--all`` over $20 refused without the confirmation; the printed follow-up commands; a real submission into a
scratch registry; the label-fit corrections keep the role fields.  No network."""
import json

import pytest

from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.professions import submit as SUB
from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
from assistant_axis.tests import professions_fakes as F


def ranked(stems, *, emp=1000):
    return [{"role": s.replace("_", " "), "stem": s, "rank": i, "score": round(10 - i * 0.1, 3), "group": f"broad:{i}",
             "gloss": f"A {s} is someone who does {s} work.", "employment": emp,
             "sources": [{"source_ref": f"soc:11-{1000 + i}", "gloss": f"A {s} is someone who does {s} work."}]}
            for i, s in enumerate(stems, 1)]


@pytest.fixture
def world(tmp_path):
    data = F.write_role_corpus(tmp_path / "data")
    reg = tmp_path / "registry.jsonl"
    submit_candidates([Candidate(surface="baker", generator="censuses", run_id="t"),
                       Candidate(surface="plumber", generator="censuses", run_id="t"),
                       Candidate(surface="welder", generator="censuses", run_id="t")], registry_path=reg, relabel=None)
    Registry(reg).update_many({"baker#1": {"entity_type": "role", "holding": "roles"}})         # a held role row
    submit_candidates([Candidate(surface="ranger", generator="masked_lm", run_id="m", entity_type="role",
                                 kind_guess="occupation", human=True)], registry_path=reg, relabel=None)
    Registry(reg).update_many({"ranger|R#1": {"review": {"status": "rejected", "by": "Roger", "at": None,
                                                          "note": None}}})
    return data, reg, tmp_path


class TestNetNew:
    def test_against_corpus_queue_and_registry(self, world):
        data, reg, _ = world
        import data_analysis.seed_entities as se
        rows = ranked(["bouncer", "bartender", "academic", "lifeguard", "courtesan", "baker", "plumber", "ranger",
                       "welder", "optimist"])
        kept, registered = SUB.net_new(rows, registry_rows=Registry(reg).fold(),
                                       corpus_stems=SUB.corpus_role_stems(data),
                                       queue_stems=SUB.queue_role_stems(se.load_queue(data / "seed_queue.json")))
        # plumber and welder have trait rows only: a role-aimed candidate makes a new |R row, so they are net-new
        assert [r["stem"] for r in kept] == ["bouncer", "plumber", "welder"]
        assert {r["stem"]: (r["registered_as"], r["registered_decided"]) for r in registered} == \
            {"baker": ("baker#1", False), "ranger": ("ranger|R#1", True)}
        ann = {r["stem"]: r for r in SUB.annotate(rows, registry_rows=Registry(reg).fold(),
                                                  corpus_stems=SUB.corpus_role_stems(data),
                                                  queue_stems=SUB.queue_role_stems(se.load_queue(data / "seed_queue.json")))}
        assert ann["bartender"]["excluded"] == ann["optimist"]["excluded"] == "corpus_role"
        assert ann["academic"]["excluded"] == "corpus_role" and ann["academic"]["corpus_stem"] == "scholar"   # renamed
        assert (ann["lifeguard"]["excluded"], ann["lifeguard"]["queue_status"]) == ("queue_entry", "candidate")
        assert (ann["courtesan"]["excluded"], ann["courtesan"]["queue_status"]) == ("queue_entry", "not_adopted")

    def test_corpus_stems_leave_default_out(self, world):
        stems = SUB.corpus_role_stems(world[0])
        assert "default" not in stems and stems["academic"] == "scholar" and stems["bartender"] == "bartender"


class TestWave:
    def test_the_arithmetic(self):
        assert SUB.wave_target(300, 0.5, kept_share=0.4) == 375
        assert SUB.wave_target(300, 0.5, kept_share=0.5) == 300
        assert SUB.wave_target(300, 0.5, kept_share=0.45) == 334          # 333.3 rounded up
        with pytest.raises(ValueError):
            SUB.wave_target(300, 0.5, kept_share=0)
        with pytest.raises(ValueError):
            SUB.wave_target(300, 1.5, kept_share=0.5)

    def test_select_wave_counts_net_new_only_from_the_top(self):
        rows = SUB.annotate(ranked([f"r{i}" for i in range(1, 501)]), registry_rows={}, corpus_stems={"r2": "r2"},
                            queue_stems={})
        reg = dict(rows[2])
        rows[2] = dict(reg, net_new=False, registered_as="r3|R#1")      # a registered row inside the cut
        sel = SUB.select_wave(rows, wave_rows=300, share=0.5, kept_share=0.4)
        assert sum(r["net_new"] for r in sel) == 375
        assert len(sel) == 376 and "r2" not in {r["stem"] for r in sel} and sel[1]["stem"] == "r3"
        assert sel[-1]["stem"] == "r377"
        assert len(SUB.select_all(rows)) == 499


class TestCandidates:
    def test_fields(self):
        rows = ranked(["bouncer"])
        rows[0]["sources"] = [{"source_ref": "onet_title:33-9032.00:bouncer", "gloss": "A bouncer is someone who A."},
                              {"source_ref": "onet_title:35-3011.00:bouncer", "gloss": None}]
        a, b = SUB.to_candidates(rows, "w1")
        assert a == Candidate(surface="bouncer", generator="professions", run_id="w1", rank=1, score=9.9,
                              gloss_hint="A bouncer is someone who A.", sense_id=1,
                              source_ref="onet_title:33-9032.00:bouncer", partner_hint=None, entity_type="role",
                              kind_guess="occupation", human=True)
        assert b.source_ref == "onet_title:35-3011.00:bouncer" and b.gloss_hint == rows[0]["gloss"]
        (c,) = SUB.to_candidates(ranked(["doctor"]), "w1")
        assert c.source_ref == "soc:11-1001"

    def test_label_fit_corrections_keep_the_role_fields(self):
        cands = SUB.to_candidates(ranked(["sales_associate", "bouncer"]), "w1")
        from assistant_axis.gapgen.label_fit import pair_id
        decisions = [{"id": pair_id("sales associate", cands[0].gloss_hint), "decision": "relabel",
                      "verdict": "secondary_sense", "proposals": [{"label": "shop assistant"}, {"label": "bartender"}]},
                     {"id": pair_id("bouncer", cands[1].gloss_hint), "decision": "fits", "verdict": "fits",
                      "proposals": []}]
        out, counts = SUB.apply_label_fit(cands, decisions, excluded_stems={"bartender"})
        assert [c.surface for c in out] == ["shop assistant", "bouncer"]
        assert all(c.entity_type == "role" and c.kind_guess == "occupation" and c.human is True for c in out)
        assert out[0].source_ref.endswith(";label_fit:secondary_sense:sales associate")
        assert counts["relabel_dropped_existing"] == 1 and counts["kept_fits"] == 1


class TestRunSubmit:
    def test_all_over_20_refused_without_confirmation(self, world):
        data, reg, tmp = world
        rows = ranked([f"job{i}" for i in range(1, 2001)])
        with pytest.raises(CostRefused):
            SUB.run_submit("w1", ranking=rows, all_rows=True, transport="live", budget_usd=10, data_dir=data,
                           registry_path=reg, candidates_dir=tmp / "cand", echo=lambda *_: None)
        with pytest.raises(CostRefused):
            SUB.run_submit("w1", ranking=rows, all_rows=True, transport="live", budget_usd=40, data_dir=data,
                           registry_path=reg, candidates_dir=tmp / "cand", echo=lambda *_: None)
        s = SUB.run_submit("w1", ranking=rows, all_rows=True, transport="live", budget_usd=40, confirm_expensive=True,
                           confirmed_by="Roger, 2026-10-23", data_dir=data, registry_path=reg,
                           candidates_dir=tmp / "cand", dry_run=True, echo=lambda *_: None)
        assert s.estimate["total_usd"] > 20 and s.n_counted == 2000
        assert not (tmp / "cand").exists()

    def test_kept_share_required_for_a_wave(self, world):
        data, reg, tmp = world
        with pytest.raises(ValueError, match="kept-share"):
            SUB.run_submit("w1", ranking=ranked(["bouncer"]), data_dir=data, registry_path=reg, echo=lambda *_: None)

    def test_dry_run_prints_the_followups_and_writes_nothing(self, world):
        data, reg, tmp = world
        lines = []
        s = SUB.run_submit("w1", ranking=ranked(["bouncer", "bartender", "baker"]), kept_share=0.4, data_dir=data,
                           registry_path=reg, candidates_dir=tmp / "cand", dry_run=True, echo=lines.append)
        text = "\n".join(lines)
        assert "traithood_filter.py --batch-id professions_w1 --run professions/w1 --pipeline split --transport " \
               "batches" in text
        assert "novelty_score.py score --holding roles --run professions/w1 --batch-id roles_professions_w1 " \
               "--transport batches" in text
        assert "review_graph.py build --batch-id review_roles_professions_w1 --from-batches roles_professions_w1" in text
        assert text.index("traithood_filter.py") < text.index("novelty_score.py")
        assert s.n_counted == 1 and s.n_registered == 1 and s.n_excluded == 1 and s.target == 375
        # ten fixture roles (six occupations) + the live queue entry lifeguard (kind:occupation)
        assert "occupation now: 7 of 11" in text
        assert not (tmp / "cand").exists() and len(Registry(reg).fold()) == 4

    def test_a_real_submission(self, world):
        data, reg, tmp = world
        s = SUB.run_submit("w1", ranking=ranked(["bouncer", "bartender", "baker", "plumber"]), kept_share=0.5,
                           data_dir=data, registry_path=reg, candidates_dir=tmp / "cand", dry_run=False, relabel=None,
                           sources_used=["onet_occupations", "onet_job_titles", "bls_oews_national"],
                           echo=lambda *_: None)
        rd = tmp / "cand" / "runs" / "professions" / "w1"
        lines = [json.loads(x) for x in (rd / "candidates.jsonl").read_text().splitlines()]
        assert [c["surface"] for c in lines] == ["bouncer", "baker", "plumber"]
        assert all(c["entity_type"] == "role" and c["kind_guess"] == "occupation" and c["human"] is True for c in lines)
        rows = Registry(reg).fold()
        assert rows["bouncer|R#1"]["entity_type"] == "role"
        assert rows["plumber|R#1"]["entity_type"] == "role" and rows["plumber#1"]["entity_type"] == "trait"
        assert [x["generator"] for x in rows["baker#1"]["sources"]] == ["censuses", "professions"]   # merged
        assert (rd / "keys.txt").read_text().split() == ["bouncer|R#1", "baker#1", "plumber|R#1"]
        rep = json.loads((rd / "submit_report.json").read_text())
        assert rep["rows_counted"] == 2 and rep["rows_registered"] == 1 and rep["rows_excluded"] == 1
        occ = rep["balance"]["occupation"]
        assert occ["before"]["count"] == 7 and occ["after_submitted"]["count"] == 9 and occ["after_kept"]["count"] == 8
        att = (rd / "ATTRIBUTION.md").read_text()
        from assistant_axis.gapgen.generators.professions.sources import ONET_ATTRIBUTION
        assert ONET_ATTRIBUTION in att
        run = json.loads((rd / "run.json").read_text())
        assert run["sessions"][0]["args"]["attribution"]["onet_job_titles"] == ONET_ATTRIBUTION
        assert json.loads((rd / "usage.json").read_text())["n_calls"] == 0
        # submitting again changes nothing
        SUB.run_submit("w1", ranking=ranked(["bouncer", "bartender", "baker", "plumber"]), kept_share=0.5,
                       data_dir=data, registry_path=reg, candidates_dir=tmp / "cand", dry_run=False, relabel=None,
                       echo=lambda *_: None)
        assert json.loads((rd / "submit_report.json").read_text())["n_unchanged"] == 3

    def test_label_fit_decisions_in_the_run_are_applied(self, world):
        data, reg, tmp = world
        rows = ranked(["sales_associate"])
        from assistant_axis.gapgen.label_fit import pair_id
        rd = tmp / "cand" / "runs" / "professions" / "w2" / "label_fit"
        rd.mkdir(parents=True)
        (rd / "decisions.json").write_text(json.dumps({"decisions": [
            {"id": pair_id("sales associate", rows[0]["gloss"]), "decision": "relabel", "verdict": "not_a_sense",
             "proposals": [{"label": "shop assistant"}]}]}))
        lines = []
        s = SUB.run_submit("w2", ranking=rows, kept_share=0.5, data_dir=data, registry_path=reg,
                           candidates_dir=tmp / "cand", dry_run=False, relabel=None, echo=lines.append)
        assert s.label_fit["relabelled_in"] == 1
        assert Registry(reg).fold()["shop_assistant|R#1"]["entity_type"] == "role"


class TestCli:
    def test_submit_cli_refuses_a_wave_without_kept_share(self, world, capsys):
        import data_analysis.gap_generation.professions_generator as G
        data, reg, tmp = world
        rd = tmp / "cand" / "runs" / "professions" / "w1"
        rd.mkdir(parents=True)
        (rd / "ranking.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ranked(["bouncer"])))
        base = ["--candidates-dir", str(tmp / "cand"), "--data-dir", str(data), "--registry", str(reg)]
        assert G.main(base + ["submit", "--run-id", "w1", "--dry-run"]) == 2
        assert "--kept-share" in capsys.readouterr().err
        assert G.main(base + ["submit", "--run-id", "w1", "--kept-share", "0.4", "--dry-run"]) == 0
        assert "novelty_score.py score --holding roles --run professions/w1" in capsys.readouterr().out


class TestLabelFitCli:
    def test_label_fit_runs_the_platform_check_and_submit_applies_it(self, world, monkeypatch, capsys):
        import data_analysis.gap_generation.label_fit as LFC
        import data_analysis.gap_generation.professions_generator as G
        from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, user_text

        def answer(kw):
            label = json.loads(user_text(kw))["label"]
            if label == "sales associate":
                return json.dumps({"reason": "Said of a person it is a job title.", "verdict": "secondary_sense",
                                   "better_label": "shop assistant"})
            return json.dumps({"reason": "It fits.", "verdict": "fits", "better_label": None})
        client = FakeAsyncAnthropic(answer)
        monkeypatch.setattr(LFC, "_client", lambda: client)
        data, reg, tmp = world
        rd = tmp / "cand" / "runs" / "professions" / "w3"
        rd.mkdir(parents=True)
        (rd / "ranking.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ranked(["bouncer", "sales_associate"])))
        base = ["--candidates-dir", str(tmp / "cand"), "--data-dir", str(data), "--registry", str(reg)]
        assert G.main(base + ["label-fit", "--run-id", "w3", "--kept-share", "0.5", "--budget-usd", "1",
                              "--no-oewn", "--dry-run"]) == 0
        assert client.calls == [] and not (rd / "label_fit").exists()
        assert G.main(base + ["label-fit", "--run-id", "w3", "--kept-share", "0.5", "--budget-usd", "1",
                              "--no-oewn", "--allow-dirty"]) == 0
        assert len(client.calls) == 6 and (rd / "label_fit" / "decisions.json").exists()
        assert (rd / "label_fit_input.jsonl").exists()
        capsys.readouterr()
        assert G.main(base + ["submit", "--run-id", "w3", "--kept-share", "0.5"]) == 0
        assert "label-fit corrections applied" in capsys.readouterr().out
        rows = Registry(reg).fold()
        assert "shop_assistant|R#1" in rows and "sales_associate|R#1" not in rows and "bouncer|R#1" in rows
        assert rows["shop_assistant|R#1"]["sources"][0]["source_ref"].endswith(
            ";label_fit:secondary_sense:sales associate")


class TestKeptBalance:
    def test_kept_by_the_kind_call_and_the_five_point_flag(self, world):
        from assistant_axis.gapgen.generators.professions import report as R
        data, reg, tmp = world
        SUB.run_submit("w4", ranking=ranked(["bouncer", "plumber", "welder", "baker"]), kept_share=0.5, data_dir=data,
                       registry_path=reg, candidates_dir=tmp / "cand", dry_run=False, relabel=None, echo=lambda *_: None)
        rd = tmp / "cand" / "runs" / "professions" / "w4"
        keys = (rd / "keys.txt").read_text().split()
        assert R.kept_balance(keys, Registry(reg).fold(), data_dir=data) is None          # no M3 decision yet
        Registry(reg).update_many({
            "bouncer|R#1": {"novelty": {"decision": "new"}, "role_pass": {"kind": "occupation"}},
            "plumber|R#1": {"novelty": {"decision": "grey"}, "role_pass": {"kind": "occupation"}},
            "welder|R#1": {"novelty": {"decision": "covered"}, "role_pass": {"kind": "occupation"}},
            "baker#1": {"novelty": {"decision": "new"}, "role_pass": {"kind": "pastime"}}})
        kb = R.kept_balance(keys, Registry(reg).fold(), data_dir=data)
        assert (kb["n_rows"], kb["n_decided"], kb["n_kept"]) == (4, 4, 3)
        assert kb["kept_by_kind"] == {"occupation": 2, "pastime": 1}
        assert kb["after"]["kinds"]["occupation"]["count"] == 9 and kb["after"]["n_now"] == 14
        # occupation 7/11 -> 9/14 (+0.6 points), pastime 0/11 -> 1/14 (+7.1 points: flagged, never cut)
        assert kb["flagged"] == ["pastime"] and kb["share_moved"]["pastime"] == round(1 / 14, 4)
        rep = R.report_markdown(rd, data_dir=data, registry_path=reg)
        assert "After M3: 4 of the run's 4 rows decided, 3 kept" in rep and "pastime +7.1%" in rep
