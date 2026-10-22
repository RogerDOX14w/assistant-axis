"""Submission in role mode (coding plan 16, § 6.1-6.2 and test 2): ``Candidate`` gains ``entity_type``, ``kind_guess``
and ``human``; a role-aimed candidate of a surface that already has a trait row is a second row keyed by entity type
(``optimist|R#1``), never merged into the trait row; one of a surface held on the roles list merges into that held
row; the relabel helper's adjective sibling of a role-aimed noun is a trait candidate.  No network."""
import json
from dataclasses import asdict

import pytest

from assistant_axis.gapgen import registry as R
from assistant_axis.gapgen.registry import CANDIDATE_FIELDS, Candidate, Registry, read_candidates, submit_candidates
from assistant_axis.tests.test_gapgen_nouns import fake as fake_lookups


def role(surface, *, run="w1", ref=None, kind="occupation", human=True, sense_id=1, gen="professions", **kw):
    return Candidate(surface=surface, generator=gen, run_id=run, entity_type="role", kind_guess=kind, human=human,
                     source_ref=ref, sense_id=sense_id, **kw)


def trait(surface, *, run="t1", gen="censuses", **kw):
    return Candidate(surface=surface, generator=gen, run_id=run, **kw)


@pytest.fixture
def reg_path(tmp_path):
    return tmp_path / "registry.jsonl"


def submit(cands, reg_path, **kw):
    kw.setdefault("relabel", None)
    return submit_candidates(cands, registry_path=reg_path, **kw)


class TestCandidate:
    def test_new_fields_with_trait_defaults(self):
        c = Candidate(surface="plucky", generator="g", run_id="r")
        assert (c.entity_type, c.kind_guess, c.human) == ("trait", None, None)
        assert CANDIDATE_FIELDS[-3:] == ("entity_type", "kind_guess", "human")
        assert tuple(asdict(c)) == CANDIDATE_FIELDS

    def test_candidates_jsonl_lines_carry_the_three_fields(self, tmp_path):
        from assistant_axis.gapgen.runs import start_run
        run = start_run("professions", "w1", candidates_dir=tmp_path)
        run.record_candidates([role("bouncer", ref="onet_title:33-9032.00:bouncer", gloss_hint="A bouncer is ...")])
        line = json.loads((run.dir / "candidates.jsonl").read_text().splitlines()[0])
        assert line["entity_type"] == "role" and line["kind_guess"] == "occupation" and line["human"] is True
        assert read_candidates(run.dir / "candidates.jsonl") == [
            role("bouncer", ref="onet_title:33-9032.00:bouncer", gloss_hint="A bouncer is ...")]

    def test_read_candidates_reads_an_old_line_as_a_trait(self, tmp_path):
        p = tmp_path / "candidates.jsonl"
        p.write_text(json.dumps({"surface": "plucky", "generator": "g", "run_id": "r", "rank": 1, "score": None,
                                 "gloss_hint": None, "sense_id": 1, "source_ref": None, "partner_hint": None}) + "\n")
        (c,) = read_candidates(p)
        assert c.entity_type == "trait" and c.kind_guess is None and c.human is None

    def test_read_candidates_refuses_an_unknown_entity_type_or_kind(self, tmp_path):
        p = tmp_path / "candidates.jsonl"
        p.write_text(json.dumps({"surface": "x", "generator": "g", "run_id": "r", "entity_type": "monster"}) + "\n")
        with pytest.raises(ValueError, match="entity_type"):
            read_candidates(p)
        p.write_text(json.dumps({"surface": "x", "generator": "g", "run_id": "r", "entity_type": "role",
                                 "kind_guess": "wizardry"}) + "\n")
        with pytest.raises(ValueError, match="kind_guess"):
            read_candidates(p)


class TestKeys:
    def test_a_role_beside_a_trait_row_is_a_second_row(self, reg_path):
        submit([trait("optimist")], reg_path)
        rep = submit([role("optimist", kind="temperament")], reg_path)
        rows = Registry(reg_path).fold()
        assert rep.keys == ["optimist|R#1"] and rep.n_new == 1 and rep.n_merged == 0
        assert rows["optimist#1"]["entity_type"] == "trait" and len(rows["optimist#1"]["sources"]) == 1
        r = rows["optimist|R#1"]
        assert r["entity_type"] == "role" and r["stem"] == "optimist" and r["sense_id"] == 1 and r["label"] == "optimist"
        src = r["sources"][0]
        assert src["kind_guess"] == "temperament" and src["human"] is True and src["generator"] == "professions"

    def test_a_role_with_no_trait_row_gets_the_role_key_too(self, reg_path):
        rep = submit([role("bouncer")], reg_path)
        assert rep.keys == ["bouncer|R#1"]
        assert Registry(reg_path).fold()["bouncer|R#1"]["entity_type"] == "role"

    def test_a_role_aimed_candidate_merges_into_a_held_role_row(self, reg_path):
        submit([trait("baker", gen="censuses")], reg_path)
        Registry(reg_path).update_many({"baker#1": {"entity_type": "role", "holding": "roles"}})
        rep = submit([role("baker", ref="soc:51-3011")], reg_path)
        rows = Registry(reg_path).fold()
        assert rep.keys == ["baker#1"] and rep.n_merged == 1 and "baker|R#1" not in rows
        srcs = rows["baker#1"]["sources"]
        assert [s["generator"] for s in srcs] == ["censuses", "professions"]
        assert srcs[1]["source_ref"] == "soc:51-3011" and srcs[1]["kind_guess"] == "occupation"
        assert "kind_guess" not in srcs[0]                                      # a trait source keeps its shape

    def test_an_existing_role_key_row_wins_over_a_later_held_plain_row(self, reg_path):
        submit([role("guard")], reg_path)
        submit([trait("guard")], reg_path)
        Registry(reg_path).update_many({"guard#1": {"entity_type": "role", "holding": "roles"}})
        rep = submit([role("guard", run="w2")], reg_path)
        assert rep.keys == ["guard|R#1"] and len(Registry(reg_path).fold()["guard|R#1"]["sources"]) == 2

    def test_a_trait_aimed_candidate_never_merges_into_a_role_key_row(self, reg_path):
        submit([role("optimist", kind="temperament")], reg_path)
        rep = submit([trait("optimist")], reg_path)
        rows = Registry(reg_path).fold()
        assert rep.keys == ["optimist#1"] and rows["optimist#1"]["entity_type"] == "trait"
        assert len(rows["optimist|R#1"]["sources"]) == 1

    def test_resubmission_is_idempotent(self, reg_path):
        cands = [role("bouncer", ref="onet_title:33-9032.00:bouncer"), role("cardiologist", ref="soc:29-1210")]
        submit(cands, reg_path)
        before = Registry(reg_path).path.read_text()
        rep = submit(cands, reg_path)
        assert rep.n_unchanged == 2 and rep.n_new == rep.n_merged == 0
        assert Registry(reg_path).path.read_text() == before

    def test_two_sources_of_one_role_in_one_call_merge(self, reg_path):
        rep = submit([role("bouncer", ref="a"), role("bouncer", ref="b")], reg_path)
        assert rep.keys == ["bouncer|R#1"] and rep.n_new == 1 and rep.n_merged == 1

    def test_a_trait_row_is_written_exactly_as_before(self, reg_path):
        submit([trait("plucky", gloss_hint="brave")], reg_path)
        r = Registry(reg_path).fold()["plucky#1"]
        assert r["entity_type"] == "trait"
        assert set(r["sources"][0]) == {"generator", "run_id", "rank", "score", "source_ref", "gloss_hint",
                                        "partner_hint", "surface"}


class TestRelabel:
    def test_the_sibling_of_a_role_aimed_noun_is_a_trait(self, reg_path):
        rep = submit([role("pedant", kind="temperament")], reg_path, relabel=fake_lookups(), corpus_stems=set())
        rows = Registry(reg_path).fold()
        assert set(rep.keys) == {"pedant|R#1", "pedantic#1"} and rep.n_relabelled == 1
        noun, adj = rows["pedant|R#1"], rows["pedantic#1"]
        assert noun["entity_type"] == "role" and adj["entity_type"] == "trait"
        assert noun["relabel"]["to_key"] == "pedantic#1" and adj["relabel"]["from_key"] == "pedant|R#1"
        src = adj["sources"][0]
        assert src["source_ref"] == "relabel:" + noun["relabel"]["rule"] + ":pedant" and "kind_guess" not in src

    def test_the_switch_turns_the_role_aimed_sibling_off(self, reg_path, monkeypatch):
        from assistant_axis.gapgen import roles_pass as RP
        monkeypatch.setattr(RP, "RELABEL_ROLE_AIMED", None)
        rep = submit([role("pedant", kind="temperament"), trait("narcissist")], reg_path, relabel=fake_lookups(),
                     corpus_stems=set())
        assert set(rep.keys) == {"pedant|R#1", "narcissist#1", "narcissistic#1"}
        assert Registry(reg_path).fold()["pedant|R#1"].get("relabel") is None


def test_new_record_in_role_mode():
    rec = R.new_record("Cop", entity_type="role")
    assert rec["key"] == "cop|R#1" and rec["entity_type"] == "role" and rec["label"] == "Cop" and rec["stem"] == "cop"
    assert R.new_record("cop")["key"] == "cop#1"


def test_gap_registry_submit_file_in_role_mode(tmp_path, capsys):
    from data_analysis.gap_generation import gap_registry
    f = tmp_path / "rows.jsonl"
    f.write_text(json.dumps({"surface": "bouncer", "kind_guess": "occupation", "human": True,
                             "source_ref": "onet_title:33-9032.00:bouncer"}) + "\n")
    reg = tmp_path / "candidates" / "registry.jsonl"
    reg.parent.mkdir()
    assert gap_registry.main(["--registry", str(reg), "submit", "--file", str(f), "--generator", "professions",
                              "--run-id", "w1", "--entity-type", "role", "--no-relabel"]) == 0
    r = Registry(reg).fold()["bouncer|R#1"]
    assert r["entity_type"] == "role" and r["sources"][0]["kind_guess"] == "occupation"
    assert gap_registry.main(["--registry", str(reg), "submit", "--file", str(f), "--generator", "professions",
                              "--run-id", "w2", "--no-relabel"]) == 0
    assert Registry(reg).fold()["bouncer#1"]["entity_type"] == "trait"     # without the flag: a trait candidate
