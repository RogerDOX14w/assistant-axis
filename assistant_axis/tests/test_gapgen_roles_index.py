"""The role index and the role query form (coding plan 16, task 5 and test 6): the role corpus as M3 reads it
(``default.json`` left out, display labels, recorded pairs expanding and nothing else), the label-stripped query
form ``role_gloss_w14``, the role queue entries and label sets, and ``cross_type``: the nearest entities of the other
kind shown on every block, never changing a decision.  No API calls."""
import json
import logging
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.tests.roles_fakes import ROLE_CORPUS, aimed_row, gloss_for, write_role_corpus
from assistant_axis.tests.test_gapgen_novelty import DIM, R2, cand, make_runner, query, responder_for

REPO = Path(__file__).resolve().parents[2]


class TestCorpus:
    def test_the_fixture_corpus(self, tmp_path):
        d = write_role_corpus(tmp_path / "data")
        rc = NV.load_role_corpus(d)
        assert set(rc) == set(ROLE_CORPUS) and "default" not in rc
        assert rc["devils_advocate"].label == "devil's advocate"
        assert rc["predator"].pair_partner == "prey" and rc["predator"].expands_to == ["prey"]
        assert rc["guardian"].partners == ["destroyer"] and rc["doctor"].expands_to == []
        assert rc["doctor"].description.startswith("A doctor is a physician") and rc["doctor"].negative_label is None

    def test_a_map_does_not_expand(self, tmp_path):
        d = write_role_corpus(tmp_path / "data")
        p = d / "roles" / "instructions" / "pilot.json"
        doc = json.loads(p.read_text())
        doc["arrangement"] = {"kind": "map", "members": ["nurse", "pilot"], "note": "a two-member map"}
        p.write_text(json.dumps(doc))
        assert NV.load_role_corpus(d)["pilot"].expands_to == []

    def test_the_real_corpus(self):
        rc = NV.load_role_corpus(REPO / "data")
        assert len(rc) >= 339 and "default" not in rc and rc["devils_advocate"].label == "devil's advocate"
        expanding = {tuple(sorted([s, t.pair_partner])) for s, t in rc.items() if t.pair_partner}
        assert expanding == {("angel", "demon"), ("cosmopolitan", "provincial"), ("destroyer", "guardian"),
                             ("instrumentally_aligned_ai", "paperclip_maximizer"), ("parasite", "symbiont"),
                             ("predator", "prey")}
        assert all(t.expands_to == ([t.pair_partner] if t.pair_partner else []) for t in rc.values())


class TestQueryForm:
    def test_the_opening_is_stripped_and_the_gloss_cut_to_14_words(self):
        g = ("A bouncer is someone who works the door of a bar or club, checking IDs, turning away the drunk "
             "and the underage, and throwing out anyone who starts trouble.")
        q = NV.query_text("bouncer", g, query_form="role_gloss_w14")
        assert q.startswith("Someone who works the door") and "bouncer" not in q.lower()
        assert len(q.split()) <= 14
        assert NV.query_text("operator", "An operator is someone who runs a boiler from a panel.",
                             query_form="role_gloss_w14") == "Someone who runs a boiler from a panel."
        assert len(NV.query_text("bouncer", g, query_form="role_gloss_w20").split()) <= 20
        assert NV.query_text("bouncer", g, query_form="label_gloss").startswith("bouncer: A bouncer is")

    def test_a_gloss_that_opens_otherwise_is_used_whole_with_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            q = NV.query_text("bouncer", "Works the door of a club.", query_form="role_gloss_w14")
        assert q == "Works the door of a club." and "does not open" in caplog.text

    def test_the_trait_forms_are_unchanged(self):
        assert NV.query_text("x", "This means being kind.", query_form="gloss_w14") == "This means being kind."
        assert "role_gloss_w14" not in NV.QUERY_FORMS and NV.DEFAULT_ROLE_QUERY_FORM == "role_gloss_w14"


class TestQueueAndLabels:
    def queue(self):
        return {"entries": [
            {"stem": "bouncer", "label": "bouncer", "entity_type": "role", "status": "candidate",
             "description_draft": "A bouncer is someone who works the door."},
            {"stem": "kindly", "label": "kindly", "entity_type": "trait", "status": "candidate",
             "description_draft": "This means being kindly."},
            {"stem": "smith", "label": "smith", "entity_type": "role", "status": "not_adopted"}]}

    def test_role_queue_entries_join_the_role_search(self, tmp_path):
        rc = NV.load_role_corpus(write_role_corpus(tmp_path / "data"))
        q, rec = NV.queue_roles(self.queue(), rc)
        assert set(q) == {"bouncer"} and q["bouncer"].queue_status == "candidate"
        assert rec["excluded"] == {"not_a_role_entry": 1, "status_not_adopted": 1}
        qt, _ = NV.queue_traits(self.queue(), {})
        assert set(qt) == {"kindly"}                                          # the trait search as before

    def test_role_label_sets_hold_role_entries_only(self, tmp_path):
        rc = NV.load_role_corpus(write_role_corpus(tmp_path / "data"))
        sets = NV.label_sets(rc, self.queue(), entity_type="role")
        assert "doctor" in sets.corpus and {"bouncer", "smith"} <= set(sets.queue) and "kindly" not in sets.queue
        m = NV.exact_label_match("doctor", sets)
        assert m["covered_by"] == "doctor" and m["match"] == "corpus"
        assert NV.exact_label_match("kindly", sets) is None
        both = NV.label_sets(rc, self.queue())
        assert "kindly" in both.queue                                         # without the type: either, as before


class TestCrossType:
    def role_index(self, tmp_path):
        rc = NV.load_role_corpus(write_role_corpus(tmp_path / "rdata"))
        E = np.zeros((len(rc), DIM))
        for i in range(len(rc)):
            E[i, i % DIM] = 1.0
            E[i, (i + 3) % DIM] = 0.5
        return NV.build_index(rc, E, variant="raw", settings={"k": 4})

    def test_cross_type_never_changes_a_decision(self, tmp_path):
        rel = {("candidate a", "delta"): "opposed", ("candidate a", "alpha"): "similar",
               ("candidate b", "beta"): "similar"}
        ov = {("candidate a", "epsilon"): 1, ("candidate a", "alpha", "sonnet"): 2, ("candidate a", "alpha", "opus"): 3,
              ("candidate b", "beta", "sonnet"): 4, ("candidate b", "beta", "opus"): 4}
        cands = [cand("candidate a"), cand("candidate b", a=3), cand("alpha")]
        vec = {cands[0].key: query(delta=0.9, alpha=0.6, zeta=0.5, kappa=0.4),
               cands[1].key: query(beta=0.9, kappa=0.5, zeta=0.4, eta=0.3),
               cands[2].key: query(alpha=1.0)}
        before, _, _ = make_runner(tmp_path / "a", responder_for(rel, ov), rules=R2)
        b0 = {k: st.block for k, st in before.run(cands, vec).items()}
        ridx = self.role_index(tmp_path)
        after, _, _ = make_runner(tmp_path / "b", responder_for(rel, ov), rules=R2, cross_index=ridx,
                                  cross_kind="roles")
        b1 = {k: st.block for k, st in after.run(cands, vec).items()}
        for k in b0:
            assert "cross_type" not in b0[k]
            ct = b1[k]["cross_type"]["roles"]
            assert len(ct) == NV.CROSS_TYPE_K and all(x["stem"] in ridx.traits for x in ct)
            assert [x["cosine"] for x in ct] == sorted((x["cosine"] for x in ct), reverse=True)
            strip = lambda b: {f: v for f, v in b.items() if f not in ("cross_type", "at", "usage")}  # noqa: E731
            assert strip(b1[k]) == strip(b0[k])
        assert b1[cands[2].key]["reason"] == "exact_label"                   # an exact-label block shows it too

    def test_the_runner_refuses_half_a_cross_setting(self, tmp_path):
        with pytest.raises(ValueError):
            make_runner(tmp_path, responder_for(), cross_kind="roles")
        with pytest.raises(ValueError):
            make_runner(tmp_path, responder_for(), list_key="people")

    def test_a_role_row_in_a_trait_run_is_refused(self):
        r = aimed_row("bouncer", "works the door")
        r["role_pass"] = {"gloss": gloss_for("bouncer", "works the door"), "kind": "occupation"}
        assert NR.candidate_from_row(r) == (None, "not_a_trait_row")


def test_the_relation_payload_names_its_list():
    u = NV.render_relation_user("cop", "A cop is someone who patrols.", [("judge", "A judge is ...")], list_key="roles")
    obj = json.loads(u)
    assert list(obj) == ["candidate", "roles"] and obj["roles"][0] == {"id": 1, "label": "judge",
                                                                        "description": "A judge is ..."}
    assert '"traits"' in NV.render_relation_user("x", "y", [("a", "b")])                      # the default as before
    with pytest.raises(ValueError):
        NV.relation_payload("x", "y", [], list_key="people")
