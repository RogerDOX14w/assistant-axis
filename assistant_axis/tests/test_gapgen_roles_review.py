"""R1 and R2 for a roles batch (coding plan 16, tasks 9-10 and test 9): the review graph of a roles pass's batch
(``role:`` corpus nodes, candidate nodes with ``outcome: "role"`` and the card's role fields, the role rubrics), the
kind readout (decision 2) on hand-made counts and on the review's own promotions, the ``kinds`` order fixed when the
log opens, the card's chip and readout, the role files served read-only, and ``apply`` promoting a nominee as a role
entry.  No API calls: the roles M3 test's environment (fake client, hash embedder, the ten-role fixture)."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen.review_app import decisions as D
from assistant_axis.tests.test_gapgen_roles_m3 import env, roles  # noqa: F401  (the fixture)
from data_analysis.gap_generation import review_graph as r1

REF = RP.REFERENCE_KINDS_2026_10_16


# --------------------------------------------------------------------------- the readout on hand-made counts

class TestBalance:
    def test_every_kind_about_right_at_the_reference(self):
        bal = RP.balance(REF, 339)
        assert bal["reference_total"] == 339 and bal["n_now"] == 339
        assert {v["status"] for v in bal["kinds"].values()} == {"about_right"}
        occ = bal["kinds"]["occupation"]
        assert occ["held"] == 162.0 and occ["room"] == 0.0 and occ["share"] == pytest.approx(162 / 339, abs=1e-4)

    def test_the_line_at_a_fixed_corpus_size(self):
        """The formula at n_now 339 (a count moved with the corpus size held, which accepts do not do: the next
        test): occupation 179 is over 1.1 x 162, 178 is not."""
        cur = dict(REF, occupation=162 + 17)
        bal = RP.balance(cur, 339)
        assert bal["kinds"]["occupation"]["status"] == "too_high"
        assert RP.balance(dict(REF, occupation=162 + 16), 339)["kinds"]["occupation"]["status"] == "about_right"
        assert bal["order"][-1] == "occupation"

    def test_accepts_raise_the_corpus_size_too(self):
        """Accepts add to the count and to n_now (review minor 4, 2026-10-23): occupation-only accepts tip occupation
        after 35 (162 + a > 1.1 x 0.478 x (339 + a)), while a small kind (pastime, 8) tips on one; the plan's § 6.3 and § 6.4
        examples are these figures."""
        def occ(a):
            return RP.balance(dict(REF, occupation=162 + a), 339 + a)["kinds"]["occupation"]
        assert occ(34)["status"] == "about_right" and occ(35)["status"] == "too_high"
        b = RP.balance(dict(REF, occupation=198), 375)
        assert (b["kinds"]["occupation"]["count"], b["kinds"]["occupation"]["held"], b["kinds"]["occupation"]["room"]) \
            == (198, 179.2, -18.8)
        assert b["kinds"]["pastime"]["held"] == 8.8 and b["kinds"]["pastime"]["status"] == "about_right"
        assert RP.kind_readout("occupation", b)["text"] == "occupation: too high (198 against 179.2 held at 375, margin 17.9)"
        assert b["order"][:2] == ["stance", "non_human"] and b["order"][-1] == "occupation"
        assert RP.balance(REF, 339)["kinds"]["pastime"]["status"] == "about_right"
        assert RP.balance(dict(REF, pastime=9), 340)["kinds"]["pastime"]["status"] == "too_high"      # one accept

    def test_pastime_too_low_at_400_with_8(self):
        bal = RP.balance(REF, 400)
        assert bal["kinds"]["pastime"]["status"] == "too_low" and bal["kinds"]["pastime"]["held"] == pytest.approx(9.4, abs=0.05)
        # the order: too low first (by room, largest first), then about right, then too high
        statuses = [bal["kinds"][k]["status"] for k in bal["order"]]
        assert statuses == sorted(statuses, key=RP.STATUSES.index)
        lows = [k for k in bal["order"] if bal["kinds"][k]["status"] == "too_low"]
        assert [bal["kinds"][k]["room"] for k in lows] == sorted((bal["kinds"][k]["room"] for k in lows), reverse=True)

    def test_kind_status_and_readout_text(self):
        bal = RP.balance(dict(REF, occupation=179), 339)
        assert RP.kind_status("occupation", current=dict(REF, occupation=179), n_now=339) == "too_high"
        r = RP.kind_readout("occupation", bal)
        assert r["status"] == "too_high" and r["text"].startswith("occupation: too high (179 against 162.0 held at 339")
        assert RP.kind_readout(None, bal) is None and RP.kind_status("sorcery", current=REF, n_now=339) is None
        assert RP.balance_lines(bal)[-1] == "occupation 179 / 162 held (too high)"

    def test_the_reference_is_role_kinds_json_less_default(self):
        doc = json.loads((Path(__file__).resolve().parents[2] / "data/roles/role_kinds.json").read_text())
        counts = {}
        for stem, r in doc["roles"].items():
            if stem != "default":
                counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        assert counts == REF and doc["roles"]["default"]["kind"] == "other"

    def test_corpus_kind_counts(self, tmp_path):
        from assistant_axis.tests.roles_fakes import ROLE_KINDS, write_role_corpus, held_row
        d = write_role_corpus(tmp_path / "data")
        q = {"entries": [{"stem": "bouncer", "entity_type": "role", "status": "candidate", "tags": ["kind:occupation"]},
                         {"stem": "doctor", "entity_type": "role", "status": "candidate", "tags": ["kind:occupation"]},
                         {"stem": "smith", "entity_type": "role", "status": "done"},
                         {"stem": "kindly", "entity_type": "trait", "status": "candidate"}]}
        nom = held_row("selkie", "a seal person")
        nom[RP.BLOCK] = {"gloss": "A selkie is ...", "kind": "non_human"}
        counts, n = RP.corpus_kind_counts(d, q, nominees=[nom])
        assert n == len(ROLE_KINDS) + 2                                 # default left out; doctor a file already
        assert counts["occupation"] == 4 + 1 and counts["non_human"] == 2 + 1     # doctor, nurse, pilot, judge


# --------------------------------------------------------------------------- R1 and R2 end to end

@pytest.fixture
def built(env, monkeypatch):    # noqa: F811
    assert roles(env, "--unscored") == 0
    monkeypatch.setattr(r1, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(r1, "platform_dirty_files", lambda *a, **k: [])
    assert r1.main(["build", "--batch-id", "rv_roles", "--from-batches", "roles_t", "--budget-usd", "1",
                    *env["base"]]) == 0
    env["rdir"] = env["cand_dir"] / "review" / "rv_roles"
    return env


def test_r1_builds_a_roles_graph(built):
    g = RG.Graph.from_json(json.loads((built["rdir"] / "graph.json").read_text()))
    nodes = g.node_map()
    assert g.complete and g.config["pass"] == "roles"
    cands = g.candidate_keys()
    assert {"bouncer|R#1", "selkie#1", "medic#1"} <= set(cands) and "cardiologist#1" not in cands
    n = nodes["selkie#1"]
    assert n.outcome == "role" and n.role_kind == "non_human" and n.human is False and n.kind_guess is None
    assert n.gloss.startswith("A selkie is someone who") and n.provenance == [{"generator": "censuses", "source_ref": None}]
    assert len(n.nearest_traits) == 5 and n.alignment_score is None
    assert nodes["bouncer|R#1"].kind_guess == "occupation"
    assert nodes["cardiologist#1"].decision == "covered" and nodes["cardiologist#1"].covered_by == "role:doctor"
    corpus = [x for x in g.nodes if x.kind == "corpus"]
    assert corpus and all(x.key.startswith("role:") for x in corpus)
    assert nodes["role:doctor"].gloss.startswith("A doctor is a physician")
    run = json.loads((built["rdir"] / "run.json").read_text())
    assert run["pass"] == "roles" and run["rubrics"]["relation"]["name"] == "relation_roles"
    assert run["settings"]["query_form"] == "role_gloss_w14"
    rel = [json.loads(x) for x in (built["rdir"] / "responses.jsonl").read_text().splitlines()
           if json.loads(x)["step"] == "relation"]
    assert all('"roles": [' in r["user"] for r in rel)
    # a trait node of a trait graph carries none of the role fields (the graph of a trait build is unchanged)
    assert "role_kind" not in RG.Node(key="x#1", kind="candidate", label="x").to_dict()


def test_r2_card_order_readout_and_apply(built):
    log = D.DecisionLog.open(built["rdir"], by="roger", data_dir=built["data"], registry_path=built["reg"].path)
    st = log.state
    assert st.roles is not None and st.roles["basis"] is not None and st.roles["fixed_at"]
    card = st.member_card("selkie#1")
    assert card["role_kind"] == "non_human" and card["human"] is False
    assert card["kind_readout"]["kind"] == "non_human" and card["kind_readout"]["text"].startswith("non_human:")
    assert card["nearest_traits"] and card["provenance"][0]["generator"] == "censuses"
    assert all(set(x) >= {"stem", "cosine", "relation", "reading"} for x in card["nearest_roles"])
    assert "role" in card["tags"]
    c0 = st.counts()
    assert c0["balance"]["n_now"] == 10 and c0["balance_lines"]               # the fixture corpus, no nominee yet
    q0 = [it["id"] for it in st.queue("kinds")]
    assert all("kind" in it for it in st.queue("kinds"))
    # accept bouncer (an occupation): the readout moves, the kinds order does not
    gid = log.act({"action": "open", "source": "term:bouncer|R#1"})[1]
    log.act({"action": "resolve", "group": gid, "resolution": "promote"})
    c1 = log.state.counts()
    assert c1["balance"]["n_now"] == 11 and c1["balance"]["kinds"]["occupation"]["count"] == \
        c0["balance"]["kinds"]["occupation"]["count"] + 1
    assert [it["id"] for it in log.state.queue("kinds")] == q0
    trait_graph = RG.Graph(batch_id="t", from_batches=[], config={}, nodes=[], edges=[], cliques=[], clique_links=[])
    with pytest.raises(D.ActionError):
        D.replay(trait_graph, []).queue("kinds")                 # the kinds order is a roles build's only
    # apply: the nominee is promoted as a role entry of the seed queue
    q = built["data"] / "seed_queue.json"
    rep = D.apply_decisions(log.state, batch_id="rv_roles", registry=built["reg"], queue_path=q, data_dir=built["data"],
                            review_dir=built["rdir"], by="roger")
    assert [p["key"] for p in rep.promotions] == ["bouncer|R#1"] and rep.refused == {}
    e = json.loads(q.read_text())["entries"][-1]
    assert e["entity_type"] == "role" and e["stem"] == "bouncer" and "kind:occupation" in e["tags"]
    assert e["description_draft"].startswith("A bouncer is someone who") and e["section"] == RP.SECTION
    assert built["reg"].fold()["bouncer|R#1"]["seed_queue_stem"] == "bouncer"


def test_the_app_serves_role_files_and_the_kinds_order(built):
    from fastapi.testclient import TestClient
    from assistant_axis.gapgen.review_app import server
    app = server.create_app(review_dir=built["rdir"], data_dir=built["data"], registry_path=built["reg"].path,
                            order="kinds")
    c = TestClient(app)
    assert c.get("/api/meta").json()["pass"] == "roles"
    q = c.get("/api/queue?order=kinds").json()
    assert q["order"] == "kinds" and q["counts"]["balance_lines"]
    r = c.get("/files/roles/doctor.json")
    assert r.status_code == 200 and r.json()["description"].startswith("A doctor is")
    assert c.get("/files/roles/nobody.json").status_code == 404
    assert c.get("/files/roles/..%2Fsecret.json").status_code == 404
    assert D.target_path("role:doctor") == ("data/roles/instructions/doctor.json", "/files/roles/doctor.json")


def test_targets_of_a_roles_build_are_roles(built):
    targets, labels = D.corpus_targets(built["data"], entity_type="role")
    assert "role:doctor" in targets and "role:default" not in targets and labels["role:devils_advocate"] == "devil's advocate"
    assert not any(t.startswith("trait:") for t in targets)
    t_targets, _ = D.corpus_targets(built["data"])
    assert all(not t.startswith("role:") for t in t_targets)
