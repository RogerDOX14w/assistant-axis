"""The platform's relabel step in ``submit_candidates`` (noun normalization plan, sections 5, 6 and 8).

A tmp registry through the real API; :class:`~assistant_axis.gapgen.nouns.FakeLookups` throughout."""
import json
import logging

import pytest

from assistant_axis.gapgen import nouns as N
from assistant_axis.gapgen import registry as R
from assistant_axis.gapgen.registry import Candidate, Registry, read_candidates, submit_candidates
from assistant_axis.gapgen.runs import start_run
from assistant_axis.tests.test_gapgen_nouns import fake

LK = fake()


def cand(surface, **kw):
    kw.setdefault("generator", "censuses")
    kw.setdefault("run_id", "2026-10-11-allport_hi")
    return Candidate(surface=surface, **kw)


@pytest.fixture
def reg(tmp_path):
    return tmp_path / "candidates" / "registry.jsonl"


def test_one_noun_makes_two_linked_rows(reg):
    rep = submit_candidates([cand("pedant", rank=412, source_ref="allport:412")], registry_path=reg, relabel=LK,
                            corpus_stems=set())
    rows = Registry(reg).fold()
    assert set(rows) == {"pedant#1", "pedantic#1"}
    assert rep.keys == ["pedant#1", "pedantic#1"]
    assert (rep.n_submitted, rep.n_new, rep.n_relabelled) == (1, 2, 1)
    assert rep.relabels == [("pedant#1", "pedantic#1", None)]
    nb, ab = rows["pedant#1"]["relabel"], rows["pedantic#1"]["relabel"]
    assert nb["to_key"] == "pedantic#1" and nb["rule"] == "derivation" and nb["helper_version"] == N.HELPER_VERSION
    assert nb["oewn"] == "oewn:2024" and nb["at"]
    assert ab == {"from_key": "pedant#1", "from_surface": "pedant", "rule": "derivation", "lexfile": "noun.person",
                  "helper_version": N.HELPER_VERSION, "oewn": "oewn:2024", "run": "censuses/2026-10-11-allport_hi",
                  "at": ab["at"]}
    # the source entry of section 6
    assert rows["pedantic#1"]["sources"] == [
        {"generator": "censuses", "run_id": "2026-10-11-allport_hi", "rank": 412, "score": None,
         "source_ref": "relabel:derivation:pedant", "gloss_hint": "marked by a narrow focus on learning",
         "partner_hint": None, "surface": "pedantic"}]
    # the noun row is the generator's, untouched but for the block
    assert rows["pedant#1"]["sources"][0]["source_ref"] == "allport:412"


def test_resubmission_is_a_no_op(reg):
    submit_candidates([cand("pedant")], registry_path=reg, relabel=LK, corpus_stems=set())
    n_lines = len(reg.read_text().splitlines())
    rep = submit_candidates([cand("pedant")], registry_path=reg, relabel=LK, corpus_stems=set())
    assert (rep.n_new, rep.n_merged, rep.n_unchanged, rep.n_relabelled) == (0, 0, 2, 1)
    assert len(reg.read_text().splitlines()) == n_lines


def test_corpus_stem_adjective_makes_no_row(reg):
    rep = submit_candidates([cand("fool")], registry_path=reg, relabel=LK, corpus_stems={"foolish"})
    rows = Registry(reg).fold()
    assert set(rows) == {"fool#1"}
    assert rows["fool#1"]["relabel"]["to_corpus_stem"] == "foolish"
    assert "to_key" not in rows["fool#1"]["relabel"]
    assert rep.relabels == [("fool#1", None, "foolish")] and rep.n_relabelled == 1


def test_existing_adjective_row_gains_a_source_and_the_link(reg):
    submit_candidates([cand("pedantic", generator="ipip", run_id="r0")], registry_path=reg, relabel=None)
    rep = submit_candidates([cand("pedant")], registry_path=reg, relabel=LK, corpus_stems=set())
    rows = Registry(reg).fold()
    assert (rep.n_new, rep.n_merged) == (1, 1)
    assert [s["generator"] for s in rows["pedantic#1"]["sources"]] == ["ipip", "censuses"]
    assert rows["pedantic#1"]["relabel"]["from_key"] == "pedant#1"


def test_first_link_wins_on_the_adjective(reg):
    lk = fake(derivations={**{"pedant": [N.Derivation("pedantic", "noun.person", "x")]},
                           "pedantry": [N.Derivation("pedantic", "noun.attribute", "x")]},
              pos={**{w: ["n"] for w in ("pedant", "pedantry")}, "pedantic": ["a"]},
              lexfiles={"pedant": {"noun.person"}, "pedantry": {"noun.attribute"}})
    submit_candidates([cand("pedant")], registry_path=reg, relabel=lk, corpus_stems=set())
    submit_candidates([cand("pedantry", run_id="r2")], registry_path=reg, relabel=lk, corpus_stems=set())
    rows = Registry(reg).fold()
    assert rows["pedantic#1"]["relabel"]["from_key"] == "pedant#1"
    assert rows["pedantry#1"]["relabel"]["to_key"] == "pedantic#1"
    assert len(rows["pedantic#1"]["sources"]) == 2


def test_relabel_none_makes_one_row(reg):
    rep = submit_candidates([cand("pedant")], registry_path=reg, relabel=None)
    assert set(Registry(reg).fold()) == {"pedant#1"}
    assert (rep.n_relabelled, rep.relabels) == (0, [])
    assert Registry(reg).fold()["pedant#1"].get("relabel") is None


def test_auto_without_oewn_warns_once_and_makes_one_row(reg, monkeypatch, caplog):
    from assistant_axis.gapgen import wordnet as W
    monkeypatch.setattr(W, "oewn_installed", lambda *a, **k: False)
    monkeypatch.setattr(R, "_RELABEL_WARNED", False)
    with caplog.at_level(logging.WARNING, logger="assistant_axis.gapgen.registry"):
        submit_candidates([cand("pedant")], registry_path=reg)
        submit_candidates([cand("coward")], registry_path=reg)
    assert set(Registry(reg).fold()) == {"pedant#1", "coward#1"}
    warnings = [r for r in caplog.records if "OEWN" in r.getMessage()]
    assert len(warnings) == 1


def test_auto_uses_the_shared_oewn_lookups(reg, monkeypatch):
    from assistant_axis.gapgen import wordnet as W
    monkeypatch.setattr(W, "oewn_installed", lambda *a, **k: True)
    monkeypatch.setattr(N.OewnLookups, "default", classmethod(lambda cls: LK))
    submit_candidates([cand("pedant")], registry_path=reg, corpus_stems=set())
    assert set(Registry(reg).fold()) == {"pedant#1", "pedantic#1"}


def test_bad_relabel_argument(reg):
    with pytest.raises(ValueError):
        submit_candidates([cand("pedant")], registry_path=reg, relabel="sometimes")


def test_derived_rows_not_in_candidates_jsonl(reg, tmp_path):
    run = start_run("censuses", "r9", candidates_dir=tmp_path / "candidates")
    submit_candidates([cand("pedant", run_id="r9"), cand("calm person", run_id="r9")], registry_path=reg, run=run,
                      relabel=LK, corpus_stems=set())
    recorded = read_candidates(run.dir / "candidates.jsonl")
    assert [c.surface for c in recorded] == ["pedant", "calm person"]


def test_submit_from_reproduces_the_derived_row(reg, tmp_path, monkeypatch):
    """``gap_registry.py submit --from`` on a run's candidates.jsonl re-derives the adjective (relabel on by
    default), and ``--no-relabel`` submits the file as given."""
    from data_analysis.gap_generation import gap_registry as GR
    run = start_run("censuses", "r9", candidates_dir=tmp_path / "candidates")
    submit_candidates([cand("pedant", run_id="r9")], registry_path=reg, run=run, relabel=LK, corpus_stems=set())
    want = Registry(reg).fold()
    monkeypatch.setattr(R, "_auto_relabel_lookups", lambda: LK)
    monkeypatch.setattr(N, "corpus_stem_map", lambda data_dir=None: {})
    other = tmp_path / "other" / "registry.jsonl"
    assert GR.main(["--registry", str(other), "submit", "--from", str(run.dir / "candidates.jsonl")]) == 0
    got = Registry(other).fold()
    assert set(got) == set(want) == {"pedant#1", "pedantic#1"}
    assert got["pedantic#1"]["sources"] == want["pedantic#1"]["sources"]
    assert got["pedantic#1"]["relabel"]["from_key"] == "pedant#1"
    plain = tmp_path / "plain" / "registry.jsonl"
    assert GR.main(["--registry", str(plain), "submit", "--from", str(run.dir / "candidates.jsonl"),
                    "--no-relabel"]) == 0
    assert set(Registry(plain).fold()) == {"pedant#1"}


def test_submit_file_no_relabel(tmp_path, monkeypatch):
    from data_analysis.gap_generation import gap_registry as GR
    monkeypatch.setattr(R, "_auto_relabel_lookups", lambda: LK)
    monkeypatch.setattr(N, "corpus_stem_map", lambda data_dir=None: {})
    f = tmp_path / "rows.jsonl"
    f.write_text(json.dumps({"surface": "pedant"}) + "\n")
    reg = tmp_path / "candidates" / "registry.jsonl"
    assert GR.main(["--registry", str(reg), "submit", "--file", str(f), "--generator", "validation", "--run-id", "v1",
                    "--no-relabel"]) == 0
    assert set(Registry(reg).fold()) == {"pedant#1"}
    assert GR.main(["--registry", str(reg), "submit", "--file", str(f), "--generator", "validation", "--run-id",
                    "v2"]) == 0
    assert set(Registry(reg).fold()) == {"pedant#1", "pedantic#1"}


def test_relabel_is_a_registry_block():
    assert "relabel" in R.BLOCKS and "relabel" in R.ROW_FIELDS


# --------------------------------------------------------------------------- the review graph, the card, promote, report

class TestReviewGraph:
    @pytest.fixture(autouse=True)
    def _hermetic(self, monkeypatch):
        from assistant_axis.gapgen import review_graph as RG
        monkeypatch.setattr(RG, "structural_operator_table", lambda *a, **k: [])

    def rows_and_vectors(self):
        import numpy as np

        from assistant_axis.tests.test_gapgen_review_graph import row, toy_rows, toy_vectors
        from assistant_axis.tests.test_gapgen_review_graph_gate8 import pad
        rows = toy_rows()
        noun, adj = row("pedant"), row("pedantic")
        nb, ab = N.relabel_blocks("pedant#1", "pedantic#1", N.relabel("pedant", lookups=LK), run="censuses/r1",
                                  now="T")
        noun["relabel"], adj["relabel"] = nb, ab
        rows.update({"pedant#1": noun, "pedantic#1": adj})
        vec = pad(toy_vectors(), 14)
        vec["pedant#1"], vec["pedantic#1"] = np.eye(14)[12], np.eye(14)[13]        # cosine 0: in no k-nearest list
        return rows, vec

    def test_relabel_pairs(self):
        from assistant_axis.gapgen import review_graph as RG
        rows, _ = self.rows_and_vectors()
        assert RG.relabel_pairs(rows) == [("pedant#1", "pedantic#1")]
        # one side's block suffices (an adjective linked first from another noun keeps that noun's from_key)
        rows["pedantic#1"]["relabel"] = {**rows["pedantic#1"]["relabel"], "from_key": "pedantry#1"}
        assert RG.relabel_pairs(rows) == [("pedant#1", "pedantic#1")]

    def test_a_relabel_pair_is_a_label_variant_style_3_edge_via_relabel(self, tmp_path):
        import json as _json

        from assistant_axis.gapgen import review_graph as RG
        from assistant_axis.tests.test_gapgen_review_graph_gate8 import build_plan
        from assistant_axis.tests.test_gapgen_review_graph import BATCH
        rows, vec = self.rows_and_vectors()
        plan = RG.plan_graph(rows, [BATCH], vec, k=10, cosine_floor=0.25)
        p = ("pedant#1", "pedantic#1")
        assert plan.relabel_pairs == [p] and plan.via[p] == "relabel" and plan.edges[p] == pytest.approx(0.0)
        assert plan.edge_counts()["by_via"]["relabel"] == 1 and plan.edge_counts()["n_relabel_pairs"] == 1
        g, _, _ = build_plan(tmp_path, plan)
        e = next(x for x in g.edges if (x.a, x.b) == p)
        assert e.label_variant and e.via == "relabel" and e.proposed and not e.strict
        assert list(p) in g.proposed_groups
        assert g.stats["candidate_edges"]["relabel_pairs"] == 1 and g.stats["candidate_edges"]["label_variants"] == 0
        d = _json.loads(_json.dumps(g.to_json()))
        assert d["schema"] == RG.GRAPH_SCHEMA == 4
        assert RG.Graph.from_json(d).to_json() == g.to_json()


def test_promote_note():
    from assistant_axis.gapgen.promote import queue_entry_from_record
    from assistant_axis.gapgen.registry import new_record
    rec = new_record("pedantic", sources=[{"generator": "censuses", "run_id": "r1"}])
    rec["relabel"] = N.relabel_blocks("pedant#1", "pedantic#1", N.relabel("pedant", lookups=LK), run="censuses/r1",
                                      now="T")[1]
    e = queue_entry_from_record(rec)
    assert "relabelled from pedant (derivation link from 'pedant' (noun.person))" in e["description_notes"]
    rec2 = new_record("slippery", sources=[{"generator": "censuses", "run_id": "r1"}])
    rec2["relabel"] = N.relabel_blocks("slipper#1", "slippery#1", N.relabel("slipper", lookups=LK), now="T")[1]
    assert "suffix rule +y from 'slipper', sense not checked" in queue_entry_from_record(rec2)["description_notes"]
    assert "relabelled" not in (queue_entry_from_record(new_record("calm"))["description_notes"] or "")


def test_report_and_holding_arrows(reg, capsys):
    from data_analysis.gap_generation import gap_registry as GR
    submit_candidates([cand("pedant"), cand("fool")], registry_path=reg, relabel=LK, corpus_stems={"foolish"})
    Registry(reg).update_many({"fool#1": {"holding": "roles"}})
    assert GR.main(["--registry", str(reg), "report"]) == 0
    out = capsys.readouterr().out
    assert "| pedant#1 | pedant -> pedantic |" in out and "| pedantic#1 | pedantic <- pedant |" in out
    assert GR.main(["--registry", str(reg), "holding", "--list", "roles"]) == 0
    out = capsys.readouterr().out
    assert "**fool** -> foolish (corpus trait)" in out


def test_review_card_route(tmp_path):
    from assistant_axis.gapgen.review_app.decisions import relabel_card
    nb, ab = N.relabel_blocks("slipper#1", "slippery#1", N.relabel("slipper", lookups=LK), now="T")
    assert relabel_card({"relabel": ab}) == {"from": "slipper", "to": None,
                                             "route": "suffix rule +y from 'slipper', sense not checked"}
    assert relabel_card({"relabel": nb}) == {"from": None, "to": "slippery",
                                             "route": "adjective 'slippery' by suffix rule +y, sense not checked"}
    assert relabel_card({}) is None
