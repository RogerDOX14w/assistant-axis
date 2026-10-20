"""R2 of the review tooling (coding_plan_review.md, sections 3 and 4): the decision log and its replay, the review
app's routes through FastAPI's ``TestClient`` (nothing binds a port), ``apply`` into a registry and seed queue copied
to ``tmp_path``, and the CLI's ``status`` / ``apply`` / ``serve``.  No API calls anywhere.

The toy graph (built by hand with R1's own dataclasses and clique functions):

* merged groups (4-edges both ways): m0 godless / irreligious / nonreligious; m1 affectionate / fond; m2 affectionate /
  loving (m1 and m2 overlap); m3 devout / pious, opposed to m0;
* proposed groups (3-edges both ways): p0 balky / headstrong / willful; p1 balky / obdurate (balky is in both);
* singletons: skeptic (a 3 one way to godless), loner (no candidate edge; corpus trait alpha reads 3);
* covered by M3 (greyed): atheistic, covered by alpha; corpus traits alpha and beta; queue entry queued.
"""
import dataclasses
import json
from pathlib import Path
from urllib.parse import quote

import pytest

from assistant_axis.gapgen import promote as promote_mod
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.registry import Registry, new_record
from assistant_axis.gapgen.review_app import decisions as D

BATCH = "rv_toy"
KEPT = ["godless", "irreligious", "nonreligious", "skeptic", "pious", "devout", "affectionate", "fond", "loving",
        "balky", "headstrong", "willful", "obdurate", "loner"]


def k(label: str) -> str:
    return f"{label}#1"


def rd(s, o=None):
    return RG.reading_of({"sonnet": {"value": s, "reason": "r"}, "opus": {"value": o, "reason": "r"} if o is not None else None})


def r1(x, y, *, rel="similar", cos=0.7, ab=(4, 4), ba=(4, 4)):
    a, b = sorted([k(x), k(y)])
    readings = {}
    if ab:
        readings["ab"] = rd(*ab)
    if ba:
        readings["ba"] = rd(*ba)
    both = bool(ab and ba) and rel != "opposed"
    strict = both and readings["ab"]["four"] and readings["ba"]["four"]
    proposed = both and readings["ab"]["proposed"] and readings["ba"]["proposed"]
    return RG.Edge(a=a, b=b, cosine=cos, relation=rel, source="r1", strict=bool(strict), proposed=bool(proposed),
                   relations={"ab": rel, "ba": rel}, readings=readings,
                   overlap="not_similar" if rel == "opposed" else ("both" if ba else "first"))


def m3(x, stem, *, rel="similar", cos=0.5, s=2, o=None):
    return RG.Edge(a=k(x), b=f"trait:{stem}", cosine=cos, relation=rel, source="m3",
                   readings={} if rel == "opposed" else {"ab": rd(s, o)}, via="retrieved", rank=1)


GEN = {"pious": "roget", "devout": "roget", "balky": "roget", "headstrong": "roget", "willful": "roget",
       "obdurate": "roget", "affectionate": "wn_clusters", "fond": "wn_clusters", "loving": "wn_clusters"}
REGION = {"affectionate": "social_interpersonal", "fond": "social_interpersonal", "loving": "social_interpersonal"}


def toy_graph() -> RG.Graph:
    nodes = [RG.Node(key=k(lb), kind="candidate", label=lb, gloss=f"This means being {lb} through and through.",
                     stem=lb, generator=GEN.get(lb, "censuses"), generators=[GEN.get(lb, "censuses")], verdict="trait",
                     decision="new", region=REGION.get(lb, "moral_stance"), alignment_score=0, m3_run="m3b",
                     flags=["sonnet_below_opus_at"] if lb == "skeptic" else [])
             for lb in KEPT]
    nodes.append(RG.Node(key=k("atheistic"), kind="candidate", label="atheistic", gloss="This means denying any god.",
                         stem="atheistic", generator="censuses", generators=["censuses"], verdict="trait",
                         decision="covered", covered_by="trait:alpha", m3_run="m3b",
                         covered_reading={"stem": "alpha", "cosine": 0.7, "sonnet": 4, "opus": 4}))
    nodes += [RG.Node(key="trait:alpha", kind="corpus", label="alpha", gloss="This means being alpha.", stem="alpha"),
              RG.Node(key="trait:beta", kind="corpus", label="beta", gloss="This means being beta.", stem="beta"),
              RG.Node(key="queue:queued", kind="queue", label="queued", gloss="This means being queued.", stem="queued",
                      status="candidate")]
    edges = [r1("godless", "irreligious", cos=0.85), r1("godless", "nonreligious", cos=0.8),
             r1("irreligious", "nonreligious", cos=0.82),
             r1("godless", "skeptic", cos=0.62, ab=(3, 3), ba=(2, None)),
             r1("devout", "pious", cos=0.8),
             r1("godless", "pious", rel="opposed", cos=0.45, ab=None, ba=None),
             r1("devout", "irreligious", rel="opposed", cos=0.4, ab=None, ba=None),
             r1("affectionate", "fond", cos=0.7), r1("affectionate", "loving", cos=0.75),
             r1("fond", "loving", cos=0.6, ab=(2, None), ba=None),
             r1("balky", "headstrong", cos=0.6, ab=(3, 3), ba=(3, 3)),
             r1("balky", "willful", cos=0.58, ab=(3, 3), ba=(3, 4)),
             r1("headstrong", "willful", cos=0.8, ab=(3, 4), ba=(3, 3)),
             r1("balky", "obdurate", cos=0.65, ab=(3, 3), ba=(3, 3)),
             r1("obdurate", "willful", cos=0.55, ab=(2, None), ba=None),
             m3("godless", "alpha", cos=0.5, s=2), m3("godless", "beta", rel="opposed", cos=0.3),
             m3("loner", "alpha", cos=0.55, s=3, o=3), m3("pious", "beta", cos=0.48, s=2)]
    cliques = RG.maximal_cliques((e.a, e.b) for e in edges if e.strict)
    proposed = RG.proposed_groups(((e.a, e.b) for e in edges if e.proposed), cliques)
    g = RG.Graph(batch_id=BATCH, from_batches=["m3b"], config={"proposed_cut_off": 3}, nodes=nodes, edges=edges,
                 cliques=cliques, clique_links=RG.clique_links(cliques, edges), proposed_groups=proposed,
                 proposed_links=RG.clique_links(proposed, edges))
    g.stats = RG.summarize(g)
    return g


def test_the_toy_graph_has_the_groups_the_tests_assume():
    g = toy_graph()
    assert g.cliques == [[k("godless"), k("irreligious"), k("nonreligious")], [k("affectionate"), k("fond")],
                         [k("affectionate"), k("loving")], [k("devout"), k("pious")]]
    assert g.proposed_groups == [[k("balky"), k("headstrong"), k("willful")], [k("balky"), k("obdurate")]]
    assert set(g.ungrouped()) == {k("skeptic"), k("loner")}


# --------------------------------------------------------------------------- fixtures

class Clock:
    """A clock the log reads: one minute per event from 09:00, so that the status's times are known."""

    def __init__(self):
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return f"2026-10-09T09:{self.n:02d}:00+00:00"


def write_env(tmp_path: Path) -> dict:
    cand = tmp_path / "candidates"
    rdir = cand / "review" / BATCH
    rdir.mkdir(parents=True)
    (rdir / "graph.json").write_text(json.dumps(RG.graph_envelope(toy_graph(), title="toy")), encoding="utf-8")
    data = tmp_path / "data"
    for et in ("traits", "roles"):
        (data / et / "instructions").mkdir(parents=True)
    for stem in ("alpha", "beta"):
        (data / "traits" / "instructions" / f"{stem}.json").write_text(
            json.dumps({"positive_label": stem, "description": f"This means being {stem}."}), encoding="utf-8")
    (data / "secret.json").write_text("{}", encoding="utf-8")
    queue = data / "seed_queue.json"
    queue.write_text(json.dumps({"_meta": {}, "entries": [
        {"stem": "queued", "label": "queued", "entity_type": "trait", "status": "candidate",
         "description": "This means being queued."}]}, indent=1), encoding="utf-8")
    reg = Registry(cand / "registry.jsonl")
    rows = []
    for lb in KEPT + ["atheistic"]:
        r = new_record(lb, sources=[{"generator": GEN.get(lb, "censuses"), "run_id": "r1", "rank": 1, "score": None,
                                     "source_ref": None, "gloss_hint": None, "partner_hint": None, "surface": lb}])
        r["gloss"] = f"This means being {lb} through and through."
        r["filter"] = {"verdict": "trait", "tags": ["membership"] if lb == "godless" else [], "region": "moral_stance",
                       "reason": "A stable stance.", "rubric_version": 5}
        r["novelty"] = {"run_id": "m3b", "decision": "covered" if lb == "atheistic" else "new",
                        "covered_by": "alpha" if lb == "atheistic" else None}
        rows.append(r)
    reg.write(rows)
    return {"cand": cand, "rdir": rdir, "data": data, "queue": queue, "reg": reg}


@pytest.fixture
def env(tmp_path):
    return write_env(tmp_path)


def make_log(env, clock=None) -> D.DecisionLog:
    return D.DecisionLog.open(env["rdir"], by="roger", clock=clock or Clock(), data_dir=env["data"])


def act(log, **req):
    ev, gid = log.act(req)
    return gid


def counts(log):
    return log.state.counts()


# --------------------------------------------------------------------------- the five-step flow

class TestFlow:
    def test_open_drop_merge_nominate_resolve_then_the_antonym_group(self, env):
        log = make_log(env)
        c0 = counts(log)
        assert c0["merged"] == {"total": 4, "remaining": 4} and c0["proposed"] == {"total": 2, "remaining": 2}
        assert c0["single"] == {"total": 2, "remaining": 2} and c0["terms"] == {"total": 14, "handled": 0, "remaining": 14}
        g1 = act(log, action="open", source="merged:0")
        grp = log.state.groups[g1]
        assert grp.status == "open" and grp.members == [k("godless"), k("irreligious"), k("nonreligious")]
        act(log, action="drop", group=g1, key=k("nonreligious"))
        act(log, action="merge_in", group=g1, keys=[k("skeptic")])
        act(log, action="nominate", group=g1, key=k("irreligious"))
        assert counts(log)["groups_open"] == 1 and counts(log)["terms"]["handled"] == 0
        ev, _ = log.act({"action": "resolve", "group": g1, "resolution": "promote", "note": "the plainest word"})
        assert ev["members"] == [k("godless"), k("irreligious"), k("skeptic")] and ev["nominated"] == k("irreligious")
        assert ev["graph_sha256"] == log.graph_sha256 and ev["by"] == "roger" and ev["seq"] == 5
        c1 = counts(log)
        assert c1["terms"]["handled"] == 3 and c1["single"]["remaining"] == 1          # skeptic handled, loner left
        assert c1["merged"]["remaining"] == 4                                          # m0 keeps nonreligious
        assert c1["groups_resolved"] == 1 and c1["groups_open"] == 0
        # step 5: the opposed pole is one step away; start the antonym group from it
        card = log.state.group_card(g1)
        assert [o["key"] for o in card["opposed"]][:1] == [k("pious")] and card["opposed"][0]["merged"] == ["m3"]
        g2 = act(log, action="start_antonym", of=g1, keys=[k("pious"), k("devout")])
        assert log.state.groups[g2].antonym_of == g1 and log.state.groups[g2].status == "open"
        with pytest.raises(D.ActionError, match="already has an antonym group"):
            log.act({"action": "start_antonym", "of": g1, "keys": [k("loner")]})
        act(log, action="nominate", group=g2, key=k("devout"))
        act(log, action="resolve", group=g2, resolution="promote")
        c2 = counts(log)
        assert c2["terms"]["handled"] == 5 and c2["merged"]["remaining"] == 3 and c2["groups_resolved"] == 2
        assert log.state.group_card(g1)["antonym_groups"] == [g2]

    def test_a_single_unhandled_member_is_nominated_by_default(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        assert log.state.groups[g].members == [k("loner")] and log.state.groups[g].source == f"term:{k('loner')}"
        ev, _ = log.act({"action": "resolve", "group": g, "resolution": "promote"})
        assert ev["nominated"] == k("loner")
        g2 = act(log, action="open", source="merged:0")
        with pytest.raises(D.ActionError, match="nominate"):
            log.act({"action": "resolve", "group": g2, "resolution": "promote"})

    def test_refusals(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        with pytest.raises(D.ActionError, match="last member"):
            log.act({"action": "drop", "group": g, "key": k("loner")})
        with pytest.raises(D.ActionError, match="not a member"):
            log.act({"action": "nominate", "group": g, "key": k("godless")})
        with pytest.raises(D.ActionError, match="not a corpus trait or queue entry"):
            log.act({"action": "resolve", "group": g, "resolution": "merge_into:trait:nonexistent"})
        with pytest.raises(D.ActionError, match="unknown action"):
            log.act({"action": "explode", "group": g})
        with pytest.raises(D.ActionError, match="no group"):
            log.act({"action": "drop", "group": "g99", "key": k("loner")})
        with pytest.raises(D.ActionError, match="already a member"):
            log.act({"action": "merge_in", "group": g, "keys": [k("loner")]})
        with pytest.raises(D.ActionError, match="not a candidate"):
            log.act({"action": "merge_in", "group": g, "keys": ["trait:alpha"]})
        assert len(log.events) == 1                      # the open; no refused action is logged

    def test_a_covered_candidate_pulled_in_by_hand_cannot_be_nominated(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="merge_in", group=g, keys=[k("atheistic")])
        assert log.state.groups[g].members == [k("loner"), k("atheistic")]
        with pytest.raises(D.ActionError, match="covered"):
            log.act({"action": "nominate", "group": g, "key": k("atheistic")})
        ev, _ = log.act({"action": "resolve", "group": g, "resolution": "promote"})
        assert ev["nominated"] == k("loner") and ev["members"] == [k("loner"), k("atheistic")]

    def test_reopening_returns_the_open_group_and_logs_nothing(self, env):
        log = make_log(env)
        g = act(log, action="open", source="merged:0")
        n = len(log.events)
        ev, g_again = log.act({"action": "open", "source": "merged:0"})
        assert ev is None and g_again == g and len(log.events) == n
        ev, g_term = log.act({"action": "open", "source": f"term:{k('irreligious')}"})
        assert ev is None and g_term == g                                 # the term is in that open group
        act(log, action="resolve", group=g, resolution="park")
        ev, g_done = log.act({"action": "open", "source": f"term:{k('godless')}"})
        assert ev is None and g_done == g and log.state.groups[g].status == "resolved"    # a handled term: its group


class TestHandled:
    def test_a_dropped_last_member_is_refused_and_a_handled_term_shows_in_its_other_clique(self, env):
        log = make_log(env)
        g = act(log, action="open", source="merged:1")                       # affectionate, fond
        act(log, action="nominate", group=g, key=k("fond"))
        act(log, action="resolve", group=g, resolution="promote")
        g2 = act(log, action="open", source="merged:2")                      # affectionate, loving
        card = log.state.group_card(g2)
        aff = next(m for m in card["members"] if m["key"] == k("affectionate"))
        assert aff["handled_by"] == g and aff["handled_resolution"] == "promote"
        with pytest.raises(D.ActionError, match="handled"):
            log.act({"action": "nominate", "group": g2, "key": k("affectionate")})
        ev, _ = log.act({"action": "resolve", "group": g2, "resolution": "promote"})   # loving, the one unhandled
        assert ev["members"] == [k("loving")] and ev["nominated"] == k("loving")
        assert log.state.handled[k("affectionate")] == g                    # handled by the first resolution
        assert log.state.queue_item("m2")["status"] == "done"
        with pytest.raises(D.ActionError, match="last member"):
            g3 = act(log, action="open", source=f"term:{k('skeptic')}")
            log.act({"action": "drop", "group": g3, "key": k("skeptic")})


    def test_the_right_hand_panel_of_a_reopened_group_is_built_from_its_unhandled_members(self, env):
        """Roger, 2026-10-11: the dregs of a group.  godless and irreligious are parked; reopening their clique for
        nonreligious shows godless's corpus trait and opposed pole no more, since those are decided."""
        log = make_log(env)
        g = act(log, action="open", source="merged:0")
        card0 = log.state.group_card(g)                                        # the clique fresh: all three decide
        assert card0["basis"] == [k("godless"), k("irreligious"), k("nonreligious")]
        assert [t["key"] for t in card0["corpus"]] == ["trait:alpha"] and card0["opposed"][0]["key"] == k("pious")
        act(log, action="drop", group=g, key=k("nonreligious"))
        assert log.state.group_card(g)["basis"] == [k("godless"), k("irreligious")]     # an exclusion recomputes
        act(log, action="resolve", group=g, resolution="park")
        g2 = act(log, action="open", source=f"term:{k('nonreligious')}")
        card = log.state.group_card(g2)
        assert [m["key"] for m in card["members"]] == [k("godless"), k("irreligious"), k("nonreligious")]
        assert card["basis"] == [k("nonreligious")]                            # the two handled are shown, not followed
        assert card["corpus"] == [] and card["opposed"] == []                 # alpha and pious came through godless
        assert [n["key"] for n in card["neighbours"]] == []                   # its only edges are to the two handled
        assert make_log(env).state.group_card(g2)["basis"] == [k("nonreligious")]


class TestProposed:
    def test_a_proposed_group_opens_pre_assembled_but_unmerged_and_g_merges_it(self, env):
        log = make_log(env)
        g = act(log, action="open", source="proposed:0")
        assert log.state.groups[g].status == "proposed"
        assert log.state.groups[g].members == [k("balky"), k("headstrong"), k("willful")]
        with pytest.raises(D.ActionError, match="accept"):
            log.act({"action": "resolve", "group": g, "resolution": "park"})
        assert counts(log)["groups_open"] == 0 and counts(log)["groups_proposed_open"] == 1
        act(log, action="accept", group=g)
        assert log.state.groups[g].status == "open" and counts(log)["groups_open"] == 1
        with pytest.raises(D.ActionError, match="not proposed"):
            log.act({"action": "accept", "group": g})

    def test_dropping_a_member_before_g_merges_the_rest(self, env):
        log = make_log(env)
        g = act(log, action="open", source="proposed:0")
        act(log, action="drop", group=g, key=k("willful"))
        act(log, action="accept", group=g)
        assert log.state.groups[g].members == [k("balky"), k("headstrong")] and log.state.groups[g].status == "open"

    def test_a_term_in_two_proposed_groups_offers_the_larger_and_lists_the_other(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('balky')}")
        grp = log.state.groups[g]
        assert grp.source == "proposed:0" and grp.status == "proposed" and len(grp.members) == 3
        card = log.state.group_card(g)
        assert card["neighbour_groups"] == [{"id": "p1", "tier": "proposed", "members": [k("balky"), k("obdurate")],
                                             "labels": ["balky", "obdurate"], "shared": [k("balky")], "remaining": 2}]
        # its other members and the other group's are neighbours too, ranked by their strongest edge
        assert k("obdurate") in [n["key"] for n in card["neighbours"]]

    def test_neighbours_rank_by_level_then_relation_then_cosine(self):
        g = toy_graph()
        g.edges += [r1("loner", "fond", rel="unrelated", cos=0.5, ab=None, ba=None),
                    r1("loner", "skeptic", rel="similar", cos=0.3, ab=None, ba=None),
                    r1("loner", "balky", rel="similar", cos=0.4, ab=(2, None), ba=None)]
        st = D.ReviewState(g)
        nb = st.neighbourhood([k("loner")])["neighbours"]
        # a read 2 first; then similar but not read (below the floor) before unrelated, whatever the cosine
        assert [(n["label"], n["level"], n["relation"]) for n in nb] == \
            [("balky", 2, "similar"), ("skeptic", 0, "similar"), ("fond", 0, "unrelated")]
        assert nb[0]["merge_keys"] == [k("balky")] and nb[2]["merge_keys"] == [k("affectionate"), k("fond")]

    def test_a_term_in_a_merged_group_opens_that_group_already_merged(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('nonreligious')}")
        assert log.state.groups[g].source == "merged:0" and log.state.groups[g].status == "open"


# --------------------------------------------------------------------------- the log: replay and undo

def snapshot(log) -> dict:
    s = log.state
    return {"groups": {g: x.as_dict() for g, x in s.groups.items()}, "handled": dict(s.handled), "counts": s.counts(),
            "queue": [(q["id"], q["status"], q["handled"]) for q in s.queue("cliques")]}


class TestLeftovers:
    """The leftovers pass (Roger, 2026-10-11): a resolution's overlapping groups, decided one member at a time."""

    def test_a_resolved_group_lists_the_overlapping_groups_unhandled_members_strongest_tie_first(self, env):
        log = make_log(env)
        g = act(log, action="open", source="merged:1")                       # affectionate, fond
        assert log.state.group_card(g)["leftovers"] == []                     # nothing until it is resolved
        act(log, action="nominate", group=g, key=k("fond"))
        act(log, action="resolve", group=g, resolution="promote")
        card = log.state.group_card(g)
        # loving shares affectionate with it through m2: a 4-edge to one of the two members
        assert [(x["key"], x["ties"], x["of"], x["level"], x["groups"]) for x in card["leftovers"]] == \
            [(k("loving"), 1, 2, 4, ["m2"])]
        assert card["distinct"] == []
        with pytest.raises(D.ActionError, match="not resolved"):
            g2 = act(log, action="open", source="merged:0")
            log.act({"action": "extend", "group": g2, "keys": [k("skeptic")]})

    def test_a_one_way_4_is_no_4_edge_in_the_leftovers_count(self, env):
        """Review 2026-10-12: ``ties`` (the page's "4-edges to N of M") counted every edge whose level is 4, and
        ``edge_level`` gives 4 to an edge read 4 one way and 2 the other, which is no 4-edge (decision 2)."""
        g = toy_graph()
        g.edges = [e for e in g.edges if {e.a, e.b} != {k("fond"), k("loving")}] + \
            [r1("fond", "loving", cos=0.6, ab=(4, 4), ba=(2, None))]
        assert D.edge_level(g.edges[-1]) == 4 and not g.edges[-1].strict
        (env["rdir"] / "graph.json").write_text(json.dumps(RG.graph_envelope(g, title="toy")), encoding="utf-8")
        log = make_log(env)
        gid = act(log, action="open", source="merged:1")                     # affectionate, fond
        act(log, action="nominate", group=gid, key=k("fond"))
        act(log, action="resolve", group=gid, resolution="promote")
        [x] = log.state.group_card(gid)["leftovers"]
        assert (x["key"], x["ties"], x["of"], x["level"]) == (k("loving"), 1, 2, 4)    # the 4-edge to affectionate only

    def test_also_covered_extends_the_resolution_and_apply_writes_it_like_a_member(self, env):
        log = make_log(env)
        g = act(log, action="open", source="merged:1")
        act(log, action="nominate", group=g, key=k("fond"))
        act(log, action="resolve", group=g, resolution="promote")
        ev, gid = log.act({"action": "extend", "group": g, "keys": [k("loving")]})
        assert ev["action"] == "extend" and ev["keys"] == [k("loving")] and gid == g
        grp = log.state.groups[g]
        assert grp.status == "resolved" and k("loving") in grp.members and k("loving") in grp.resolved_members
        assert log.state.handled[k("loving")] == g and log.state.group_card(g)["leftovers"] == []
        assert log.state.queue_item("m2")["status"] == "done"                  # affectionate and loving both handled
        blocks = D.desired_blocks(log.state, BATCH)
        assert blocks[k("loving")]["status"] == "merged_into" and blocks[k("loving")]["into"] == k("fond")
        assert blocks[k("loving")]["group"] == [k("affectionate"), k("fond"), k("loving")]
        with pytest.raises(D.ActionError, match="already a member"):
            log.act({"action": "extend", "group": g, "keys": [k("loving")]})
        with pytest.raises(D.ActionError, match="is handled"):
            g2 = act(log, action="open", source="merged:0")
            act(log, action="resolve", group=g2, resolution="park")
            log.act({"action": "extend", "group": g2, "keys": [k("loving")]})
        assert snapshot(make_log(env)) == snapshot(log)                        # a restart replays the extension

    def test_distinct_keeps_the_term_unhandled_and_out_of_that_group_s_leftovers(self, env):
        log = make_log(env)
        g = act(log, action="open", source="proposed:0")                     # balky, headstrong, willful
        act(log, action="accept", group=g)
        act(log, action="resolve", group=g, resolution="merge_into:trait:alpha")
        assert [x["key"] for x in log.state.group_card(g)["leftovers"]] == [k("obdurate")]    # via p1
        ev, _ = log.act({"action": "distinct", "group": g, "keys": [k("obdurate")]})
        assert ev["action"] == "distinct" and ev["keys"] == [k("obdurate")]
        card = log.state.group_card(g)
        assert card["leftovers"] == [] and [x["key"] for x in card["distinct"]] == [k("obdurate")]
        assert k("obdurate") not in log.state.handled                          # still to decide, in its own group
        assert log.state.queue_item("p1")["status"] == "todo" and log.state.queue_item("p1")["remaining"] == 1
        assert log.state.member_card(k("obdurate"))["distinct_from"] == [g]
        with pytest.raises(D.ActionError, match="already marked distinct"):
            log.act({"action": "distinct", "group": g, "keys": [k("obdurate")]})
        # it can still be taken in later, which clears the mark
        log.act({"action": "extend", "group": g, "keys": [k("obdurate")]})
        assert log.state.handled[k("obdurate")] == g and log.state.member_card(k("obdurate"))["distinct_from"] == []
        assert make_log(env).state.member_card(k("obdurate"))["distinct_from"] == []

    def test_undo_skips_opens_and_says_what_it_undid(self, env):
        log = make_log(env)
        g1 = act(log, action="open", source="merged:0")
        act(log, action="resolve", group=g1, resolution="park")
        g2 = act(log, action="open", source="merged:1")                      # navigation, twice
        g3 = act(log, action="open", source="merged:3")
        ev, gid = log.act({"action": "undo"})
        assert ev["undoes"] == 2 and ev["undone_action"] == "resolve" and ev["undone_resolution"] == "park" and gid == g1
        assert log.state.groups[g1].status == "open" and not log.state.handled
        assert g2 in log.state.groups and g3 in log.state.groups             # the opens stay
        # only opens left: undo takes the last open
        ev, _ = log.act({"action": "undo"})
        assert ev["undoes"] == 4 and ev["undone_action"] == "open" and g3 not in log.state.groups
        assert snapshot(make_log(env)) == snapshot(log)
        # an undone extension names its keys
        act(log, action="resolve", group=g1, resolution="park")
        log.act({"action": "extend", "group": g1, "keys": [k("skeptic")]})
        ev, _ = log.act({"action": "undo"})
        assert ev["undone_action"] == "extend" and ev["undone_keys"] == [k("skeptic")]
        assert k("skeptic") not in log.state.handled and log.state.groups[g1].resolved_members == log.state.groups[g1].members


class TestReplay:
    def test_the_log_replays_to_the_same_state_after_a_restart(self, env):
        log = make_log(env)
        g1 = act(log, action="open", source="merged:0")
        act(log, action="drop", group=g1, key=k("nonreligious"))
        act(log, action="merge_in", group=g1, keys=[k("skeptic")])
        act(log, action="nominate", group=g1, key=k("irreligious"))
        act(log, action="resolve", group=g1, resolution="promote")
        act(log, action="start_antonym", of=g1, keys=[k("pious")])
        g3 = act(log, action="open", source="proposed:1")
        act(log, action="accept", group=g3)
        before = snapshot(log)
        lines = (env["rdir"] / "decisions.jsonl").read_text().splitlines()
        assert len(lines) == 8 and [json.loads(x)["seq"] for x in lines] == list(range(1, 9))
        assert json.loads(lines[4]) | {} == log.events[4]
        again = make_log(env)
        assert snapshot(again) == before and again.state.skipped == []

    def test_undo_reverses_the_last_event_and_the_replay_agrees(self, env):
        log = make_log(env)
        g1 = act(log, action="open", source="merged:0")
        act(log, action="nominate", group=g1, key=k("godless"))
        before = snapshot(log)
        act(log, action="resolve", group=g1, resolution="promote")
        assert log.state.handled
        ev, gid = log.act({"action": "undo"})
        assert ev["action"] == "undo" and ev["undoes"] == 3 and gid == g1
        assert snapshot(log) == before
        assert snapshot(make_log(env)) == before                  # a restart replays the undo the same way
        # undo walks back: the nomination, then the open
        log.act({"action": "undo"})
        assert log.state.groups[g1].nominated is None
        log.act({"action": "undo"})
        assert g1 not in log.state.groups and counts(log)["terms"]["handled"] == 0
        with pytest.raises(D.ActionError, match="nothing to undo"):
            log.act({"action": "undo"})
        # a new group never reuses an undone id
        g_new = act(log, action="open", source="merged:3")
        assert g_new != g1
        with pytest.raises(D.ActionError, match="only the last decision"):
            log.act({"action": "undo", "seq": 1})

    def test_an_event_the_graph_no_longer_supports_is_skipped_on_replay(self, env):
        log = make_log(env)
        act(log, action="open", source="merged:0")
        with (env["rdir"] / "decisions.jsonl").open("a") as fh:
            fh.write(json.dumps({"seq": 2, "at": "x", "by": "roger", "group": "g1", "action": "drop",
                                 "key": "vanished#1", "graph_sha256": "old"}) + "\n")
        again = make_log(env)
        assert [s["seq"] for s in again.state.skipped] == [2] and "g1" in again.state.groups
        assert again.graph_versions() == {log.graph_sha256: 1, "old": 1}

    def test_a_torn_last_line_is_closed_before_the_next_event(self, env):
        """Review 2026-10-12: a write torn by a crash leaves a last line without its newline; the next event used to
        be appended to that fragment, the glued line was not JSON, and the decision vanished on the next restart."""
        log = make_log(env)
        g = act(log, action="open", source="merged:0")
        path = env["rdir"] / "decisions.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write('{"seq": 2, "at": "2026-10-09T09:02:00+00:00", "action": "dr')        # torn mid-write
        again = make_log(env)                                     # the fragment is skipped (a warning), as before
        assert [e["seq"] for e in again.events] == [1]
        act(again, action="drop", group=g, key=k("nonreligious"))
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3 and json.loads(lines[2])["action"] == "drop"
        third = make_log(env)
        assert [e["seq"] for e in third.events] == [1, 2] and third.state.skipped == []
        assert third.state.groups[g].members == [k("godless"), k("irreligious")]
        assert snapshot(third) == snapshot(again)

    def test_a_failure_inside_apply_leaves_the_state_as_the_log_replays_it(self, env, monkeypatch):
        """Review 2026-10-12: ``act`` applies an event before appending it; an exception there (a check and an apply
        that disagree: a bug) used to leave the in-memory state changed although nothing was logged."""
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        before = snapshot(log)

        def half_applied(self, ev):
            self.groups[ev["group"]].members.extend(ev["keys"])       # mutate, then fail
            raise RuntimeError("bug")
        monkeypatch.setattr(D.ReviewState, "_apply_merge_in", half_applied)
        with pytest.raises(RuntimeError):
            log.act({"action": "merge_in", "group": g, "keys": [k("skeptic")]})
        assert len(log.events) == 1 and snapshot(log) == before
        assert len((env["rdir"] / "decisions.jsonl").read_text().splitlines()) == 1

    def test_an_undo_with_a_seq_that_is_no_number_is_refused(self, env):
        log = make_log(env)
        act(log, action="open", source="merged:0")
        with pytest.raises(D.ActionError, match="seq must be"):
            log.act({"action": "undo", "seq": "last"})
        assert len(log.events) == 1


# --------------------------------------------------------------------------- apply

def flow_for_apply(env) -> D.DecisionLog:
    log = make_log(env)
    g1 = act(log, action="open", source="merged:0")
    act(log, action="drop", group=g1, key=k("nonreligious"))
    act(log, action="merge_in", group=g1, keys=[k("skeptic"), k("atheistic")])
    act(log, action="nominate", group=g1, key=k("irreligious"))
    act(log, action="resolve", group=g1, resolution="promote", note="plainest")
    g2 = act(log, action="start_antonym", of=g1, keys=[k("pious"), k("devout")])
    act(log, action="nominate", group=g2, key=k("devout"))
    act(log, action="resolve", group=g2, resolution="promote")
    g3 = act(log, action="open", source=f"term:{k('loner')}")
    act(log, action="resolve", group=g3, resolution="merge_into:trait:alpha")
    g4 = act(log, action="open", source="merged:1")
    act(log, action="resolve", group=g4, resolution="reject", note="not traits")
    g5 = act(log, action="open", source=f"term:{k('nonreligious')}")       # m0 again: nonreligious is left
    act(log, action="resolve", group=g5, resolution="defer")
    return log


def run_apply(env, log, *, dry_run=False):
    return D.apply_decisions(log.state, batch_id=BATCH, registry=env["reg"], queue_path=env["queue"],
                             data_dir=env["data"], review_dir=env["rdir"], dry_run=dry_run, by="roger")


class TestApply:
    def test_apply_writes_review_blocks_promotes_once_per_group_and_is_idempotent(self, env, monkeypatch):
        log = flow_for_apply(env)
        calls = []
        real = promote_mod.promote

        def spy(records, queue, keys, **kw):
            calls.append(list(keys))
            return real(records, queue, keys, **kw)
        monkeypatch.setattr(promote_mod, "promote", spy)
        reg_before, q_before = env["reg"].path.read_bytes(), env["queue"].read_bytes()
        rep = run_apply(env, log, dry_run=True)
        assert env["reg"].path.read_bytes() == reg_before and env["queue"].read_bytes() == q_before
        assert not (env["rdir"] / "applied.jsonl").exists()
        assert len(rep.review_writes) == 10 and [p["key"] for p in rep.promotions] == [k("irreligious"), k("devout")]
        dry_text = rep.format()
        assert "WOULD WRITE" in dry_text and "WOULD PROMOTE irreligious#1" in dry_text
        calls.clear()
        rep = run_apply(env, log)
        assert calls == [[k("irreligious")], [k("devout")]]            # once per promoted group, the nominated key
        rows = env["reg"].fold()
        rv = rows[k("irreligious")]["review"]
        assert rv["status"] == "accepted" and rv["by"] == "roger" and rv["note"] == "plainest"
        assert rv["group"] == [k("godless"), k("irreligious"), k("skeptic"), k("atheistic")]
        assert rv["review_batch"] == BATCH and rv["at"] == log.state.groups["g1"].resolved_at
        for other in ("godless", "skeptic", "atheistic"):
            assert rows[k(other)]["review"]["status"] == "merged_into"
            assert rows[k(other)]["review"]["into"] == k("irreligious")
        assert rows[k("nonreligious")]["review"]["status"] == "deferred"         # its own later group
        assert rows[k("pious")]["review"] == rows[k("pious")]["review"] | {"status": "merged_into", "into": k("devout")}
        assert rows[k("devout")]["review"]["antonym_of"] == "g1" and rv["antonym_group"] == "g2"
        assert rows[k("loner")]["review"]["status"] == "merged_into" and rows[k("loner")]["review"]["into"] == "trait:alpha"
        assert rows[k("affectionate")]["review"]["status"] == "rejected" == rows[k("fond")]["review"]["status"]
        assert rows[k("loving")]["review"]["status"] == "unreviewed"                # never resolved
        q = json.loads(env["queue"].read_text())
        by_stem = {e["stem"]: e for e in q["entries"]}
        assert by_stem["irreligious"]["also_proposed"] == ["godless", "skeptic", "atheistic"]
        assert by_stem["devout"]["also_proposed"] == ["pious"] and by_stem["devout"]["status"] == "candidate"
        assert "also_proposed" not in by_stem["queued"]
        assert rows[k("irreligious")]["seed_queue_stem"] == "irreligious" and rows[k("devout")]["seed_queue_stem"] == "devout"
        applied = [json.loads(x) for x in (env["rdir"] / "applied.jsonl").read_text().splitlines()]
        assert applied[-1]["review_writes"] == 10 and applied[-1]["promoted"] == [k("irreligious"), k("devout")]
        # a second run changes nothing and calls promote for nobody
        calls.clear()
        reg_after, q_after = env["reg"].path.read_bytes(), env["queue"].read_bytes()
        rep2 = run_apply(env, log)
        assert env["reg"].path.read_bytes() == reg_after and env["queue"].read_bytes() == q_after
        assert calls == [] and rep2.review_writes == {} and rep2.promotions == [] and rep2.unchanged == 10

    def test_merge_into_a_corpus_trait_adds_the_labels_to_the_synonyms_shortlist(self, env, capsys):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="merge_in", group=g, keys=[k("skeptic")])
        act(log, action="resolve", group=g, resolution="merge_into:trait:alpha", note="alpha says it")
        run_apply(env, log)
        short = D.review_merges(env["reg"].fold().values())
        assert [x["stem"] for x in short] == ["alpha"] and short[0]["kind"] == "corpus"
        assert [c["label"] for c in short[0]["candidates"]] == ["loner", "skeptic"]
        assert short[0]["candidates"][0]["note"] == "alpha says it" and short[0]["candidates"][0]["review_group"] == g
        from data_analysis.gap_generation import gap_registry
        assert gap_registry.main(["--registry", str(env["reg"].path), "synonyms"]) == 0
        o = capsys.readouterr().out
        assert "| alpha | review | loner | loner#1 | merged in review rv_toy (g1, roger) | alpha says it |" in o
        assert "| alpha | review | skeptic | skeptic#1 |" in o
        assert gap_registry.main(["--registry", str(env["reg"].path), "synonyms", "--stem", "beta"]) == 0
        assert "loner" not in capsys.readouterr().out

    def test_a_merge_into_a_queue_entry(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="resolve", group=g, resolution="merge_into:queue:queued")
        run_apply(env, log)
        assert env["reg"].fold()[k("loner")]["review"]["into"] == "queue:queued"
        assert D.review_merges(env["reg"].fold().values())[0]["kind"] == "queue"

    def test_an_undone_resolution_after_apply_is_reset_and_a_promotion_is_reported(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="resolve", group=g, resolution="promote")
        run_apply(env, log)
        assert env["reg"].fold()[k("loner")]["seed_queue_stem"] == "loner"
        log.act({"action": "undo"})
        rep = run_apply(env, log)
        assert env["reg"].fold()[k("loner")]["review"]["status"] == "unreviewed"
        assert k("loner") in rep.resets and any("loner" in c for c in rep.conflicts)

    def test_a_promoted_row_resolved_otherwise_after_an_undo_is_a_conflict(self, env):
        """Review 2026-10-12: the conflict used to be reported only when the row's block was reset; a promoted
        nominee re-resolved (rejected, or merged into another nominee) was rewritten silently, its queue entry
        left in the seed queue.  The block is still written; the conflict says so, once, at the change."""
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="resolve", group=g, resolution="promote")
        run_apply(env, log)
        log.act({"action": "undo"})
        act(log, action="resolve", group=g, resolution="reject")
        rep = run_apply(env, log)
        assert env["reg"].fold()[k("loner")]["review"]["status"] == "rejected"
        assert rep.conflicts == [f"{k('loner')} was promoted as loner, and this review now resolves it rejected: "
                                 "remove its seed-queue entry by hand if that is meant"]
        assert "CONFLICT: " + rep.conflicts[0] in rep.format()
        assert run_apply(env, log).conflicts == []                    # unchanged since: not reported again
        # another member nominated: the first nominee merges into the second, which is promoted too
        g2 = act(log, action="open", source="merged:1")                # affectionate, fond
        act(log, action="nominate", group=g2, key=k("fond"))
        act(log, action="resolve", group=g2, resolution="promote")
        run_apply(env, log)
        log.act({"action": "undo"})
        act(log, action="nominate", group=g2, key=k("affectionate"))
        act(log, action="resolve", group=g2, resolution="promote")
        rep = run_apply(env, log)
        assert [p["key"] for p in rep.promotions] == [k("affectionate")]
        assert rep.conflicts == [f"{k('fond')} was promoted as fond, and this review now resolves it merged_into "
                                 f"{k('affectionate')}: remove its seed-queue entry by hand if that is meant"]

    def test_a_refused_promotion_is_reported_and_the_review_block_still_written(self, env):
        (env["data"] / "traits" / "instructions" / "loner.json").write_text("{}")   # the stem is in the corpus now
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="resolve", group=g, resolution="promote")
        rep = run_apply(env, log)
        assert rep.refused == {k("loner"): "stem exists in the corpus"}
        assert env["reg"].fold()[k("loner")]["review"]["status"] == "accepted"
        assert "loner" not in {e["stem"] for e in json.loads(env["queue"].read_text())["entries"]}


# --------------------------------------------------------------------------- the page, run in node

def _node():
    """The node executable, or None.  ``shutil.which`` first; then a plain ``node`` run, because a sandbox that hides
    the install's directory from ``stat`` (Claude Code's, 2026-10-12) can still execute it."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if node:
        return node
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True, timeout=30)
        return "node"
    except (OSError, subprocess.SubprocessError):
        return None


#: app.js in a ``vm`` context with a stub DOM (elements made on first use, ``handlers`` per event) and a ``fetch``
#: whose answers the test gives by hand (``pending``); BODY runs in an async function with ``T`` (the page's ``S``
#: and functions), ``el``, ``pending`` and ``sleep``.  An unhandled rejection prints ``UNHANDLED``.
PAGE_HARNESS = r"""
const vm = require("vm"), fs = require("fs");
const els = {};
function el(id) {
  if (!els[id]) els[id] = {id, innerHTML: "", textContent: "", className: "", hidden: false, value: "", handlers: {},
    scrollIntoView() {}, focus() {}, querySelector() { return null; },
    addEventListener(t, f) { (this.handlers[t] = this.handlers[t] || []).push(f); }};
  return els[id];
}
const pending = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
process.on("unhandledRejection", (e) => { console.log("UNHANDLED " + e); process.exitCode = 3; });
const ctx = {document: {getElementById: el, querySelectorAll: () => [], querySelector: () => null,
                        addEventListener() {}, title: ""},
             window: {prompt: () => null}, console, setTimeout, clearTimeout,
             fetch: (url, opt) => new Promise((res) => pending.push({url, opt, res}))};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8") +
                "\n;globalThis.T = {S, renderCard, openFind, closeOverlay, ACTIONS, showGroup};", ctx);
const T = ctx.T;
(async () => {
BODY
})().catch((e) => { console.log("ERROR " + ((e && e.stack) || e)); process.exitCode = 2; });
"""


def run_page(tmp_path: Path, body: str) -> str:
    """Run ``body`` against app.js in node (skipped without node); its stdout, after asserting a clean exit."""
    import subprocess
    from assistant_axis.gapgen.review_app import server
    node = _node()
    if not node:
        pytest.skip("node not installed")
    script = tmp_path / "page_harness.js"
    script.write_text(PAGE_HARNESS.replace("BODY", body), encoding="utf-8")
    r = subprocess.run([node, str(script), str(server.STATIC_DIR / "app.js")], capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


# --------------------------------------------------------------------------- the routes (TestClient)

@pytest.fixture
def client(env):
    from fastapi.testclient import TestClient
    from assistant_axis.gapgen.review_app import server
    app = server.create_app(review_dir=env["rdir"], data_dir=env["data"], registry_path=env["reg"].path,
                            by="roger", clock=Clock())
    return TestClient(app)


def post(client, **req):
    r = client.post("/api/action", json=req)
    return r


class TestRoutes:
    def test_the_flow_through_the_api(self, client):
        q = client.get("/api/queue").json()
        assert [i["id"] for i in q["items"]][:6] == ["m0", "p0", "m1", "m2", "m3", "p1"]
        assert [i["id"] for i in q["items"]][6:] == [f"s:{k('loner')}", f"s:{k('skeptic')}"]   # generator, region, label
        assert q["counts"]["terms"]["remaining"] == 14 and q["order"] == "cliques"
        r = post(client, action="open", source="merged:0").json()
        gid = r["group"]["id"]
        assert r["event"]["action"] == "open" and r["group"]["status"] == "open"
        members = r["group"]["members"]
        assert [m["key"] for m in members] == [k("godless"), k("irreligious"), k("nonreligious")]
        gd = members[0]
        assert gd["tags"] == ["membership"] and gd["generator"] == "censuses" and gd["m3_decision"] == "new"
        assert gd["gloss"].startswith("This means being godless")
        assert post(client, action="drop", group=gid, key=k("nonreligious")).status_code == 200
        r = post(client, action="merge_in", group=gid, keys=[k("skeptic")]).json()
        sk = next(m for m in r["group"]["members"] if m["key"] == k("skeptic"))
        assert sk["flags"] == ["sonnet_below_opus_at"]
        post(client, action="nominate", group=gid, key=k("irreligious"))
        r = post(client, action="resolve", group=gid, resolution="promote").json()
        assert r["group"]["status"] == "resolved" and r["counts"]["terms"]["handled"] == 3
        card = client.get(f"/api/group/{gid}").json()
        corpus = {c["key"]: c for c in card["corpus"]}
        assert corpus["trait:alpha"]["path"] == "data/traits/instructions/alpha.json"
        assert corpus["trait:alpha"]["href"] == "/files/traits/alpha.json"
        assert corpus["trait:alpha"]["covered"] == [{"key": k("atheistic"), "label": "atheistic", "reading": "4/4"}]
        assert [o["key"] for o in card["opposed"]] == [k("pious"), k("devout"), "trait:beta"]
        assert card["opposed"][2]["path"] == "data/traits/instructions/beta.json"
        r = post(client, action="start_antonym", of=gid, keys=[k("pious"), k("devout")]).json()
        g2 = r["group"]["id"]
        post(client, action="nominate", group=g2, key=k("devout"))
        r = post(client, action="resolve", group=g2, resolution="promote").json()
        assert r["counts"]["terms"]["handled"] == 5 and r["counts"]["merged"]["remaining"] == 3
        st = client.get("/api/status").json()
        assert st["resolutions"] == {"promote": 2} and st["groups"]["resolved"] == 2

    def test_a_refusal_is_a_409_with_the_reason_and_logs_nothing(self, client, env):
        r = post(client, action="open", source=f"term:{k('loner')}")
        gid = r.json()["group"]["id"]
        r = post(client, action="drop", group=gid, key=k("loner"))
        assert r.status_code == 409 and "last member" in r.json()["detail"]
        assert len((env["rdir"] / "decisions.jsonl").read_text().splitlines()) == 1

    def test_the_term_view_and_find(self, client):
        t = client.get(f"/api/term/{quote(k('godless'), safe='')}").json()
        assert t["term"]["label"] == "godless" and t["merged"] == ["m0"] and t["proposed"] == []
        rel = {(e["key"], e["relation"]) for e in t["edges"]}
        assert (k("skeptic"), "similar") in rel and (k("pious"), "opposed") in rel and ("trait:alpha", "similar") in rel
        sk = next(e for e in t["edges"] if e["key"] == k("skeptic"))
        assert sk["readings"] == "3/3, 2/-" and sk["cosine"] == 0.62
        assert client.get("/api/term/nothing%231").status_code == 404
        f = client.get("/api/find", params={"q": "relig"}).json()
        assert [x["key"] for x in f["results"]] == [k("irreligious"), k("nonreligious")]
        f = client.get("/api/find", params={"q": "alph"}).json()
        assert f["results"][0]["key"] == "trait:alpha" and f["results"][0]["kind"] == "corpus"

    def test_queue_orders(self, client):
        g = client.get("/api/queue", params={"order": "generator"}).json()
        gens = [i["generator"] for i in g["items"]]
        assert gens == sorted(gens)
        r = client.get("/api/queue", params={"order": "region"}).json()
        assert [i["region"] for i in r["items"]] == sorted(i["region"] for i in r["items"])
        assert client.get("/api/queue", params={"order": "nonsense"}).status_code == 422

    def test_files_are_served_read_only_inside_the_corpus(self, client):
        r = client.get("/files/traits/alpha.json")
        assert r.status_code == 200 and r.json()["positive_label"] == "alpha"
        assert client.get("/files/traits/..%2Fsecret.json").status_code == 404
        assert client.get("/files/traits/nothing.json").status_code == 404
        assert client.post("/files/traits/alpha.json").status_code == 405
        q = client.get("/files/queue/queued").json()
        assert q["path"] == "data/seed_queue.json" and q["entry"]["label"] == "queued"

    def test_the_page_and_its_assets(self, client):
        r = client.get("/")
        assert r.status_code == 200 and "app.js" in r.text and "style.css" in r.text
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/static/style.css").status_code == 200

    def test_every_action_is_a_button_and_every_key_goes_through_actions(self, client):
        """2026-10-10 (Roger: buttons, not shortcuts to learn): the page has a toolbar; each button's data-act names an
        ACTIONS entry; each key of the keyboard handler that acts calls ACTIONS (or onEnter / move), so a button and its
        key run the same code."""
        import re
        assert 'id="toolbar"' in client.get("/").text
        js = client.get("/static/app.js").text
        actions = set(re.findall(r"^  (\w+): \(\) =>", js.split("const ACTIONS = {", 1)[1].split("\n};", 1)[0], re.M))
        assert {"next", "accept", "promote", "reject", "park", "defer", "merge_into", "drop", "nominate", "merge_in",
                "antonym", "note", "undo", "find", "details", "order", "help"} <= actions
        used = set(re.findall(r'\b(?:btn|rowBtn)\("(\w+)"', js))
        assert used and used <= actions, used - actions
        keys = js.split('document.addEventListener("keydown"', 1)[1]
        for case in re.findall(r'case "([^"]+)":([^\n]*)', keys):
            k, body = case
            if k in ("Tab", "ArrowDown", "ArrowUp", "j", "k", "Escape", "Enter"):
                continue
            assert "ACTIONS." in body, (k, body)
        promote = js.split("async function promote()", 1)[1].split("\n}\n", 1)[0]   # Roger 2026-10-10: no ★, the clicked member
        assert promote.index('action: "nominate"') < promote.index('resolve("promote")')
        assert "return promote();" in js.split("async function onEnter()", 1)[1].split("\n}\n", 1)[0]

    def test_the_script_parses(self):
        import subprocess
        node = _node()
        if not node:
            pytest.skip("node not installed")
        from assistant_axis.gapgen.review_app import server
        r = subprocess.run([node, "--check", str(server.STATIC_DIR / "app.js")], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def test_a_card_renders_without_the_fields_an_older_server_omits(self, tmp_path):
        """Review 2026-10-12: app.js is read from disk on each page load while the server runs the code it started
        with; a resolved card from a server before the leftovers pass (no ``leftovers``, no ``distinct``) threw in
        renderCard and left the page blank."""
        out = run_page(tmp_path, """
            T.S.card = {id: "g1", status: "resolved", source: "merged:0", via: null, members: [], antonym_groups: [],
                        neighbour_groups: [], neighbours: [], corpus: [], opposed: [], resolution: "park",
                        nominated: null};
            T.renderCard();
            console.log(el("card").innerHTML.includes("Resolved: park") ? "RENDERED" : "MISSING");
        """)
        assert "RENDERED" in out

    def test_find_ignores_an_answer_that_arrives_after_its_overlay_closed(self, tmp_path):
        """Review 2026-10-12: the find box's answer, arriving after Esc (or after the box was opened again), wrote
        into a closed overlay (a TypeError in the page) or showed the old query's results in the new box."""
        out = run_page(tmp_path, """
            const answer = {ok: true, json: async () => ({results: [{key: "godless#1", label: "godless", kind: "candidate"}]})};
            const type = async (q) => {
              el("find").value = q;
              el("find").handlers.input.forEach((f) => f());
              await sleep(200);                                       // the debounce fired; the request is in flight
            };
            T.openFind();
            await type("god");
            T.closeOverlay();                                         // Esc before the answer
            pending.filter((x) => x.url.startsWith("/api/find"))[0].res(answer);
            await sleep(50);
            console.log("CLOSED " + (T.S.overlay === null));
            T.openFind();
            await type("godl");
            T.closeOverlay();
            T.openFind();                                             // a new box, still empty
            pending.filter((x) => x.url.startsWith("/api/find"))[1].res(answer);
            await sleep(50);
            console.log("RESULTS " + T.S.overlay.results.length);
        """)
        assert "CLOSED true" in out and "RESULTS 0" in out and "UNHANDLED" not in out

    def test_a_restart_of_the_app_replays_the_log(self, env, client):
        gid = post(client, action="open", source="proposed:0").json()["group"]["id"]
        post(client, action="accept", group=gid)
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        again = TestClient(server.create_app(review_dir=env["rdir"], data_dir=env["data"],
                                             registry_path=env["reg"].path))
        assert again.get(f"/api/group/{gid}").json()["status"] == "open"
        assert again.get("/api/group/g99").status_code == 404


# --------------------------------------------------------------------------- the CLI

class TestCli:
    def base(self, env):
        return ["--out-root", str(env["cand"]), "--registry", str(env["reg"].path), "--queue", str(env["queue"]),
                "--data-dir", str(env["data"])]

    def test_status_and_apply(self, env, capsys):
        from data_analysis.gap_generation import review_app as cli
        flow_for_apply(env)
        assert cli.main(["status", "--batch-id", BATCH, *self.base(env)]) == 0
        o = capsys.readouterr().out
        assert "groups: 5 resolved, 0 open" in o and "promote 2" in o and "merge_into 1" in o and "reject 1" in o
        assert "terms: 9 of 14 handled" in o and "minutes per resolved group" in o
        before = env["reg"].path.read_bytes()
        assert cli.main(["apply", "--batch-id", BATCH, "--dry-run", *self.base(env)]) == 0
        assert "WOULD PROMOTE irreligious#1" in capsys.readouterr().out and env["reg"].path.read_bytes() == before
        assert cli.main(["apply", "--batch-id", BATCH, *self.base(env)]) == 0
        o = capsys.readouterr().out
        assert "PROMOTED irreligious#1 -> irreligious" in o
        assert env["reg"].fold()[k("irreligious")]["review"]["status"] == "accepted"
        assert cli.main(["apply", "--batch-id", BATCH, *self.base(env)]) == 0
        assert "nothing to write" in capsys.readouterr().out

    def test_apply_lists_the_decisions_the_graph_no_longer_supports(self, env, capsys):
        """Review 2026-10-12: ``status`` and ``serve`` named the skipped decisions and ``apply`` did not, although
        it leaves them out and resets a row this review wrote for one."""
        from data_analysis.gap_generation import review_app as cli
        flow_for_apply(env)
        with (env["rdir"] / "decisions.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"seq": 99, "at": "2026-10-09T10:00:00+00:00", "by": "roger", "group": "g1",
                                 "action": "drop", "key": "vanished#1", "graph_sha256": "old"}) + "\n")
        assert cli.main(["apply", "--batch-id", BATCH, "--dry-run", *self.base(env)]) == 0
        o = capsys.readouterr().out
        assert "WARNING: 1 logged decisions no longer apply to this graph and are left out of this apply:" in o
        assert "  skipped 99 drop g1: " in o and o.index("WARNING") < o.index("WOULD WRITE")

    def test_serve_runs_uvicorn_on_the_local_port(self, env, monkeypatch):
        import uvicorn
        from data_analysis.gap_generation import review_app as cli
        seen = {}
        monkeypatch.setattr(uvicorn, "run", lambda app, **kw: seen.update(app=app, **kw))
        assert cli.main(["serve", "--batch-id", BATCH, *self.base(env)]) == 0
        assert seen["host"] == "127.0.0.1" and seen["port"] == 8765 and seen["app"] is not None

    def test_a_missing_graph_is_refused(self, env, capsys):
        from data_analysis.gap_generation import review_app as cli
        assert cli.main(["status", "--batch-id", "nope", *self.base(env)]) == 1
        assert "graph.json" in capsys.readouterr().err


def test_review_statuses_written_are_in_the_vocabulary():
    """Every status the review app writes into a registry review block is in the frozen vocabulary."""
    from assistant_axis.gapgen.normalize import REVIEW_STATUSES
    from assistant_axis.gapgen.review_app.decisions import REVIEW_STATUS, UNREVIEWED
    assert set(REVIEW_STATUS.values()) | {UNREVIEWED["status"]} <= set(REVIEW_STATUSES)


# --------------------------------------------------------------------------- the rename flag (QUESTIONS 71)

class TestRenameFlag:
    """Roger 2026-10-11, QUESTIONS 71: the human net for an awkward multiword label.  A ``rename`` flag on the
    review **decision** (never on the trait file: the registry is a history, so a flag there needs no cleaning up),
    the existing note carrying the freeform reason, and ``apply`` printing the flagged labels as a worklist."""

    def flow(self, env, log=None):
        log = log or make_log(env)
        g1 = act(log, action="open", source="merged:0")
        act(log, action="nominate", group=g1, key=k("irreligious"))
        log.act({"action": "resolve", "group": g1, "resolution": "promote", "note": "three words and a shrug",
                 "rename": True})
        g2 = act(log, action="open", source="merged:1")
        act(log, action="nominate", group=g2, key=k("affectionate"))
        act(log, action="resolve", group=g2, resolution="promote")          # not flagged
        return log, g1, g2

    def test_the_flag_rides_on_the_decision_and_reaches_the_row(self, env):
        log, g1, g2 = self.flow(env)
        resolves = [e for e in log.events if e["action"] == "resolve"]
        assert resolves[0]["rename"] is True and resolves[1]["rename"] is False
        assert log.state.groups[g1].rename is True and log.state.groups[g2].rename is False
        assert log.state.group_card(g1)["rename"] is True
        run_apply(env, log)
        rows = env["reg"].fold()
        for key in (k("godless"), k("irreligious"), k("nonreligious")):
            assert rows[key]["review"]["rename"] is True
            assert rows[key]["review"]["note"] == "three words and a shrug"
        # an unflagged decision writes no key at all, so a row applied before the flag existed stays byte-identical
        assert "rename" not in rows[k("affectionate")]["review"]
        # and the flag never leaves the registry: the seed-queue entry it promotes knows nothing of it
        by_stem = {e["stem"]: e for e in json.loads(env["queue"].read_text())["entries"]}
        assert "rename" not in by_stem["irreligious"] and "rename" not in by_stem["affectionate"]

    def test_the_flag_survives_a_restart(self, env):
        log, g1, g2 = self.flow(env)
        again = make_log(env)
        assert again.state.groups[g1].rename is True and again.state.groups[g2].rename is False
        assert again.state.groups[g1].note == "three words and a shrug"

    def test_an_undo_takes_the_flag_back(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        log.act({"action": "resolve", "group": g, "resolution": "promote", "note": "awkward", "rename": True})
        assert log.state.groups[g].rename is True
        log.act({"action": "undo"})
        assert log.state.groups[g].status == "open" and log.state.groups[g].rename is False

    def test_the_promotion_report_lists_the_flagged_labels_as_a_worklist(self, env, capsys):
        log, g1, _ = self.flow(env)
        rep = run_apply(env, log, dry_run=True)
        assert [x["key"] for x in rep.rename_flagged] == [k("irreligious")]
        [x] = rep.rename_flagged
        assert x["group"] == g1 and x["resolution"] == "promote" and x["label"] == "irreligious"
        assert x["note"] == "three words and a shrug" and x["stem"] == "irreligious"
        text = rep.format()
        assert "Flagged for a rename in review (1)" in text
        assert "RENAME? irreligious (irreligious, promote, group g1): three words and a shrug" in text
        assert "1 flagged for a rename" in text
        assert rep.as_dict()["rename_flagged"] == rep.rename_flagged
        from data_analysis.gap_generation import review_app as cli
        assert cli.main(["apply", "--batch-id", BATCH, "--dry-run", *TestCli().base(env)]) == 0
        assert "RENAME? irreligious" in capsys.readouterr().out

    def test_the_worklist_names_a_merge_target_and_a_rejected_group_s_first_member(self, env):
        log = make_log(env)
        g1 = act(log, action="open", source=f"term:{k('loner')}")
        log.act({"action": "resolve", "group": g1, "resolution": "merge_into:trait:alpha",
                 "note": "alpha reads oddly", "rename": True})
        g2 = act(log, action="open", source="merged:1")
        log.act({"action": "resolve", "group": g2, "resolution": "reject", "rename": True})
        rep = run_apply(env, log)
        assert [(x["key"], x["stem"], x["label"]) for x in rep.rename_flagged] == [
            ("trait:alpha", "alpha", "alpha"), (k("affectionate"), None, "affectionate")]
        assert env["reg"].fold()[k("loner")]["review"]["rename"] is True

    def test_an_unflagged_review_has_an_empty_worklist(self, env):
        rep = run_apply(env, flow_for_apply(env), dry_run=True)
        assert rep.rename_flagged == [] and "RENAME?" not in rep.format()
        assert "flagged for a rename" not in rep.format()

    def test_the_flag_goes_through_the_api(self, client):
        gid = post(client, action="open", source=f"term:{k('loner')}").json()["group"]["id"]
        r = post(client, action="resolve", group=gid, resolution="promote", note="awkward", rename=True).json()
        assert r["event"]["rename"] is True and r["group"]["rename"] is True
        assert r["group"]["note"] == "awkward"

    def test_the_button_is_in_the_toolbar_with_its_keyed_label(self, client):
        """A button, not a note convention: Roger uses the app himself and asked for buttons rather than
        conventions to remember.  Built like every other one, so keyedLabel() bolds the shortcut letter."""
        import re
        js = client.get("/static/app.js").text
        m = re.search(r'btn\("rename",\s*S\.rename \? "([^"]+)" : "([^"]+)",\s*"(\w)"', js)
        assert m, "no rename button in the toolbar"
        flagged, unflagged, key = m.groups()
        assert (unflagged, flagged, key) == ("Flag for rename", "Flagged for rename ✓", "f")
        for text in (unflagged, flagged):
            i = re.search(rf"\b{key}", text, re.I).start()      # keyedLabel(): the letter at the start of a word
            assert i == 0 and text[i] == "F"
        assert 'case "f": ACTIONS.rename(); break;' in js
        assert "rename: () => toggleRename()" in js
        assert "Flag for rename" in js.split("function help()", 1)[1]        # in the optional key list too
        assert 'body.rename = true' in js.split("async function resolve(", 1)[1]


# --------------------------------------------------------------------------- terms an earlier review batch handled

OTHER = "review_other"
PRE = {k("irreligious"): f"{OTHER}/g3", k("godless"): f"{OTHER}/g3", k("loner"): f"{OTHER}/g4"}


def review_block(status, group, *, into=None, batch=OTHER, members=()):
    """A registry review block as ``apply_decisions`` writes it."""
    b = {"status": status, "by": "roger", "at": "2026-10-10T10:00:00+00:00", "note": None, "group": list(members),
         "review_batch": batch, "review_group": group}
    if into:
        b["into"] = into
    return b


def write_earlier_reviews(env):
    """Another batch's review, applied: review_other g3 promoted irreligious (seed-queue stem irreligious, the entry
    added to the queue) with godless merged into it; g4 merged loner into trait:alpha; g5 parked fond."""
    g3 = [k("godless"), k("irreligious")]
    env["reg"].update_many({
        k("irreligious"): {"review": review_block("accepted", "g3", members=g3), "seed_queue_stem": "irreligious"},
        k("godless"): {"review": review_block("merged_into", "g3", into=k("irreligious"), members=g3)},
        k("loner"): {"review": review_block("merged_into", "g4", into="trait:alpha", members=[k("loner")])},
        k("fond"): {"review": review_block("parked", "g5", members=[k("fond")])}}, merge_blocks=False)
    q = json.loads(env["queue"].read_text())
    q["entries"].append({"stem": "irreligious", "label": "irreligious", "entity_type": "trait", "status": "candidate",
                         "description": "This means being irreligious through and through."})
    env["queue"].write_text(json.dumps(q, indent=1), encoding="utf-8")


def graph_from_registry(env, *, strip=False) -> RG.Graph:
    """The toy graph, its candidate nodes carrying their registry rows' review fields as R1's build reads them
    (``review_fields``), written to graph.json; ``strip``: written without the fields, as before 2026-10-11."""
    rows = env["reg"].fold()
    g = toy_graph()
    g.nodes = [dataclasses.replace(n, **RG.review_fields(rows[n.key])) if n.kind == "candidate" else n for n in g.nodes]
    d = RG.graph_envelope(g, title="toy")
    if strip:
        for n in d["result"]["nodes"]:
            for f in RG.REVIEW_FIELDS:
                n.pop(f, None)
    (env["rdir"] / "graph.json").write_text(json.dumps(d), encoding="utf-8")
    return g


def log_with_registry(env) -> D.DecisionLog:
    return D.DecisionLog.open(env["rdir"], by="roger", clock=Clock(), data_dir=env["data"],
                              registry_path=env["reg"].path)


class TestHandledBefore:
    """coding_plan_review.md section 11 (Roger, 2026-10-11): a term another review batch settled is handled from the
    start, by a pseudo group id naming that batch and group; parked or deferred there, it stays live."""

    @pytest.fixture
    def pre(self, env):
        write_earlier_reviews(env)
        graph_from_registry(env)
        return env

    def test_counts_queue_and_status(self, pre):
        log = make_log(pre)                                   # no registry: the node fields alone
        st = log.state
        assert st.handled == PRE and st.pre_handled == PRE
        c = counts(log)
        assert c["terms"] == {"total": 14, "handled": 3, "remaining": 11}
        assert c["single"] == {"total": 2, "remaining": 1}                     # loner done, skeptic left
        assert c["merged"]["remaining"] == 4                                   # m0 keeps nonreligious
        assert st.queue_item(f"s:{k('loner')}")["status"] == "done"
        assert st.queue_item("m0")["handled"] == 2 and st.queue_item("m0")["status"] == "todo"
        assert k("fond") not in st.handled and st.earlier[k("fond")]["text"] == "parked in review_other g5; still to decide here"
        assert log.status()["pre_handled"] == {"terms": 3, "by_batch": {OTHER: 3},
                                               "by_status": {"accepted": 1, "merged_into": 2}, "live_elsewhere": 1,
                                               "resolved_here_too": 0}
        assert log.events == [] and st.next_group == 1                        # a pseudo id is no group of this log
        with pytest.raises(D.ActionError, match="nothing to undo"):
            log.act({"action": "undo"})

    def test_a_pre_handled_term_is_refused_by_open_with_its_batch_and_a_parked_one_opens(self, pre):
        log = make_log(pre)
        with pytest.raises(D.ActionError, match="handled in review batch review_other, group g3: accepted → queue:irreligious"):
            log.act({"action": "open", "source": f"term:{k('irreligious')}"})
        with pytest.raises(D.ActionError, match="group g4: merged_into trait:alpha"):
            log.act({"action": "open", "source": f"term:{k('loner')}"})
        g = act(log, action="open", source=f"term:{k('fond')}")               # parked there: live here
        assert log.state.groups[g].source == "merged:1"
        fond = log.state.member_card(k("fond"))
        assert fond["handled_by"] is None and fond["earlier_review"]["status"] == "parked"
        act(log, action="nominate", group=g, key=k("fond"))
        act(log, action="resolve", group=g, resolution="promote")
        assert log.state.handled[k("fond")] == g
        assert len(log.events) == 3                                            # the refusals logged nothing

    def test_a_group_with_a_pre_handled_member_decides_only_the_rest(self, pre):
        log = make_log(pre)
        g = act(log, action="open", source="merged:0")
        card = log.state.group_card(g)
        assert card["basis"] == [k("nonreligious")]
        m = {x["key"]: x for x in card["members"]}
        assert m[k("godless")]["handled_by"] == "review_other/g3"
        assert m[k("godless")]["handled_resolution"] == "merged_into irreligious#1 → queue:irreligious"
        assert m[k("irreligious")]["handled_resolution"] == "accepted → queue:irreligious"
        assert m[k("irreligious")]["earlier_review"]["text"] == "handled in review_other g3: accepted → queue:irreligious"
        # the word already decided is a target, through the member nearest the rest
        assert [t["key"] for t in card["corpus"]] == ["queue:irreligious"]
        q = card["corpus"][0]
        assert q["through"]["key"] == k("irreligious") and q["via"] == k("nonreligious") and q["level"] == 4
        assert q["kind"] == "queue" and q["href"] == "/files/queue/irreligious"
        with pytest.raises(D.ActionError, match="is handled"):
            log.act({"action": "nominate", "group": g, "key": k("godless")})
        ev, _ = log.act({"action": "resolve", "group": g, "resolution": "merge_into:queue:irreligious"})
        assert ev["members"] == [k("nonreligious")]
        blocks = D.desired_blocks(log.state, BATCH)
        assert set(blocks) == {k("nonreligious")} and blocks[k("nonreligious")]["into"] == "queue:irreligious"
        assert log.state.queue_item("m0")["status"] == "done"

    def test_a_pre_handled_neighbour_wears_its_badge_and_c_merges_into_its_queue_entry(self, pre):
        log = make_log(pre)
        g = act(log, action="open", source=f"term:{k('skeptic')}")
        card = log.state.group_card(g)
        gd = next(n for n in card["neighbours"] if n["key"] == k("godless"))
        assert gd["handled_by"] == "review_other/g3" and gd["merge_keys"] == []
        assert gd["earlier_review"]["text"] == "handled in review_other g3: merged_into irreligious#1 → queue:irreligious"
        corpus = {t["key"]: t for t in card["corpus"]}
        assert corpus["queue:irreligious"]["through"] == {"key": k("godless"), "label": "godless",
                                                          "text": gd["earlier_review"]["text"]}
        assert corpus["queue:irreligious"]["level"] == 3                       # godless-skeptic reads 3 at best
        with pytest.raises(D.ActionError, match="review_other/g3"):
            log.act({"action": "merge_in", "group": g, "keys": [k("godless")]})
        t = log.state.term_card(k("skeptic"))
        assert next(e for e in t["edges"] if e["key"] == k("godless"))["earlier_review"]["handled"] is True
        found = {x["key"]: x for x in log.state.find("relig")}
        assert found[k("irreligious")]["earlier_review"]["id"] == "review_other/g3"
        assert "earlier_review" not in found[k("nonreligious")]
        ev, _ = log.act({"action": "resolve", "group": g, "resolution": "merge_into:queue:irreligious"})   # c
        assert ev["members"] == [k("skeptic")]

    def test_every_member_handled_before_refuses_the_seed(self, pre):
        pre["reg"].update_many({k("nonreligious"): {"review": review_block("rejected", "g6")}}, merge_blocks=False)
        graph_from_registry(pre)
        log = make_log(pre)
        assert log.state.queue_item("m0")["status"] == "done"
        with pytest.raises(D.ActionError, match="every member of merged:0 was handled in an earlier review"):
            log.act({"action": "open", "source": "merged:0"})

    def test_replay_of_a_log_is_unaffected_and_its_decision_stands(self, env):
        log = make_log(env)
        g1 = act(log, action="open", source="merged:0")
        act(log, action="nominate", group=g1, key=k("godless"))
        act(log, action="resolve", group=g1, resolution="promote")
        before = snapshot(log)
        write_earlier_reviews(env)
        graph_from_registry(env)
        again = make_log(env)
        assert again.state.skipped == []
        assert {g: x.as_dict() for g, x in again.state.groups.items()} == before["groups"]
        assert again.state.handled == {k("godless"): g1, k("irreligious"): g1, k("nonreligious"): g1,
                                       k("loner"): "review_other/g4"}
        assert again.state.member_card(k("irreligious"))["handled_resolution"] == "promote"
        assert again.status()["pre_handled"]["resolved_here_too"] == 2
        ev, _ = again.act({"action": "undo"})                                  # undo walks this log only
        assert ev["undoes"] == 3 and again.state.groups[g1].status == "open"
        assert again.state.handled == PRE

    def test_this_batch_s_own_blocks_are_not_earlier_reviews(self, env):
        env["reg"].update_many({k("loner"): {"review": review_block("accepted", "g1", batch=BATCH)}},
                               merge_blocks=False)
        graph_from_registry(env)
        assert make_log(env).state.earlier == {} and log_with_registry(env).state.handled == {}

    def test_an_old_graph_loads_with_nothing_pre_handled_and_the_registry_is_the_later_record(self, env):
        assert make_log(env).state.handled == {}                               # write_env's graph: no review fields
        write_earlier_reviews(env)
        graph_from_registry(env, strip=True)
        raw = json.loads((env["rdir"] / "graph.json").read_text())
        assert not any(f in n for n in raw["result"]["nodes"] for f in RG.REVIEW_FIELDS)
        assert make_log(env).state.handled == {}                               # an old graph, no registry: nothing
        assert log_with_registry(env).state.handled == PRE                     # the registry's rows fill in
        graph_from_registry(env)
        env["reg"].update_many({k("loner"): {"review": dict(D.UNREVIEWED)}}, merge_blocks=False)   # reset since
        assert make_log(env).state.handled == PRE                              # the graph's copy alone
        assert log_with_registry(env).state.handled == {x: v for x, v in PRE.items() if x != k("loner")}

    def test_through_the_api(self, pre):
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        client = TestClient(server.create_app(review_dir=pre["rdir"], data_dir=pre["data"],
                                              registry_path=pre["reg"].path, clock=Clock()))
        assert client.get("/api/queue").json()["counts"]["terms"]["handled"] == 3
        r = post(client, action="open", source=f"term:{k('godless')}")
        assert r.status_code == 409 and "review_other, group g3" in r.json()["detail"]
        t = client.get(f"/api/term/{quote(k('godless'), safe='')}").json()
        assert t["term"]["handled_by"] == "review_other/g3" and t["term"]["earlier_review"]["target"] == "queue:irreligious"
        assert client.get("/api/status").json()["pre_handled"]["by_batch"] == {OTHER: 3}

    def test_the_page_renders_the_badge_from_the_fields_the_server_sends(self, client):
        js = client.get("/static/app.js").text
        assert "earlier_review" in js and "function earlierBadge(" in js and "t.through" in js


def test_the_statuses_that_settle_a_term_are_in_the_vocabulary():
    from assistant_axis.gapgen.normalize import REVIEW_STATUSES
    assert set(D.HANDLED_ELSEWHERE) <= set(REVIEW_STATUSES) and not {"parked", "deferred"} & set(D.HANDLED_ELSEWHERE)


# --------------------------------------------------------------------------- the IPIP pole's other name

def _ipip(ref: str, run_id: str, surface: str) -> dict:
    return {"generator": "ipip", "run_id": run_id, "rank": 1, "score": None, "source_ref": ref, "gloss_hint": None,
            "partner_hint": None, "surface": surface}


class TestIpipOtherName:
    """Roger, 2026-10-14: the IPIP generator names each pole twice (blind and hinted runs, one ``source_ref``), and the
    two names often land in different groups, so the member card shows the other run's name for the same pole."""

    @pytest.fixture
    def ipip_env(self, env):
        reg = env["reg"]
        rows = reg.fold()
        # skeptic (in the graph) is the blind name of pole c001a; doubter (not in the graph) the hinted one, and a
        # third run named it unbeliever
        rows[k("skeptic")]["sources"].append(_ipip("ipip:g600:c001a", "blind", "skeptic"))
        # pious: both runs gave the same name (one row, two sources), and a second sense row spells it "Pious"
        rows[k("pious")]["sources"] += [_ipip("ipip:g600:c003a", "blind", "pious"),
                                        _ipip("ipip:g600:c003a", "hinted", "pious")]
        reg.write([rows[k("skeptic")], rows[k("pious")]])
        doubter = new_record("doubter", sources=[_ipip("ipip:g600:c001a", "hinted", "doubter")])
        unbeliever = new_record("unbeliever", sources=[_ipip("ipip:g600:c001a", "later", "unbeliever")])
        pious2 = new_record("Pious", sense_id=2, sources=[_ipip("ipip:g600:c003a", "later", "Pious")])
        # a different pole and a non-IPIP source sharing a ref string are no siblings
        other = new_record("solitary", sources=[_ipip("ipip:g600:c009b", "hinted", "solitary"),
                                                {**_ipip("ipip:g600:c001a", "x", "lonesome"), "generator": "roget"}])
        reg.write([doubter, unbeliever, pious2, other])
        return env

    def test_the_siblings_come_from_the_rows_sources(self, ipip_env):
        sib = D.ipip_siblings(ipip_env["reg"].fold())
        assert sorted(s["key"] for s in sib["ipip:g600:c001a"]) == [k("doubter"), k("skeptic"), k("unbeliever")]
        assert sorted(s["key"] for s in sib["ipip:g600:c003a"]) == [k("pious"), k("pious"), "pious#2"]
        assert [s["key"] for s in sib["ipip:g600:c009b"]] == [k("solitary")]

    def test_the_card_shows_the_other_names_both_ways_and_omits_the_same_stem(self, ipip_env):
        log = log_with_registry(ipip_env)
        card = log.state.member_card(k("skeptic"))["other_names"]
        assert [(o["surface"], o["key"], o["source_ref"], o["run_ids"]) for o in card] == [
            ("doubter", k("doubter"), "ipip:g600:c001a", ["hinted"]),
            ("unbeliever", k("unbeliever"), "ipip:g600:c001a", ["later"])]
        rows = log.rows
        back = D.other_names_card(k("doubter"), rows[k("doubter")], log.state.ipip_siblings())
        assert [o["surface"] for o in back] == ["skeptic", "unbeliever"]
        assert log.state.member_card(k("pious"))["other_names"] is None          # same name both runs, and "Pious"
        assert log.state.member_card(k("loner"))["other_names"] is None          # no IPIP source
        assert D.other_names_card(k("solitary"), rows[k("solitary")], log.state.ipip_siblings()) is None

    def test_without_a_registry_there_is_no_badge(self, ipip_env):
        assert make_log(ipip_env).state.member_card(k("skeptic"))["other_names"] is None

    def test_through_the_api_and_the_page_renders_it(self, ipip_env):
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        client = TestClient(server.create_app(review_dir=ipip_env["rdir"], data_dir=ipip_env["data"],
                                              registry_path=ipip_env["reg"].path, clock=Clock()))
        t = client.get(f"/api/term/{quote(k('skeptic'), safe='')}").json()
        gid = post(client, action="open", source=f"term:{k('skeptic')}").json()["group"]["id"]
        card = client.get(f"/api/group/{gid}").json()
        m = {x["key"]: x for x in card["members"]}
        assert [o["surface"] for o in m[k("skeptic")]["other_names"]] == ["doubter", "unbeliever"]
        assert [o["surface"] for o in t["term"]["other_names"]] == ["doubter", "unbeliever"]
        js = client.get("/static/app.js").text
        assert "m.other_names" in js and "other name: " in js and "${otherNames}" in js


# --------------------------------------------------------------------------- the sample order (Roger, 2026-10-16)

class TestSampleOrder:
    def test_items_carry_the_strongest_member_s_best_m3_reading_and_its_stratum(self, env):
        q = {tuple(it["labels"]): it for it in make_log(env).state.queue("cliques")}
        by_label = {lb: it for labels, it in q.items() for lb in labels}
        assert by_label["loner"]["best_reading"] == 3 and by_label["loner"]["stratum"] == "read_3"
        # godless reads alpha at 2; its opposed edge to beta (unread) is ignored
        assert by_label["godless"]["best_reading"] == 2 and by_label["godless"]["stratum"] == "read_2"
        assert by_label["fond"]["best_reading"] == -1 and by_label["fond"]["stratum"] == "other"

    def test_the_sample_order_is_a_stable_permutation_that_handling_does_not_change(self, env):
        log = make_log(env)
        before = [it["id"] for it in log.state.queue("sample")]
        assert sorted(before) == sorted(it["id"] for it in log.state.queue("cliques"))
        gid = act(log, action="open", source="merged:0")
        act(log, action="resolve", group=gid, resolution="reject")
        after = [it["id"] for it in log.state.queue("sample")]
        assert after == before == [it["id"] for it in make_log(env).state.queue("sample")]

    def test_sample_key_is_deterministic_and_a_heavier_weight_comes_earlier_on_average(self):
        assert D.sample_key("m3", 1.0) == D.sample_key("m3", 1.0)
        assert D.sample_key("m3", 1.0, seed="other") != D.sample_key("m3", 1.0)
        ids = [f"s:x{i}" for i in range(4000)]
        light = sum(D.sample_key(i, 1.0) for i in ids) / len(ids)
        heavy = sum(D.sample_key(i, 2.0) for i in ids) / len(ids)
        assert abs(light - 1.0) < 0.06 and abs(heavy - 0.5) < 0.03      # exponential means 1/w

    def test_sample_inclusion_matches_the_design(self):
        sizes = {"read_3": 50, "read_2": 250, "other": 100}
        everything = D.sample_inclusion(sizes, 400, sims=50)
        assert all(abs(p - 1.0) < 1e-9 for p in everything.values())
        flat = D.sample_inclusion({"a": 100, "b": 300}, 100, weights={"a": 1.0, "b": 1.0}, sims=400)
        assert abs(flat["a"] - 0.25) < 0.02 and abs(flat["b"] - 0.25) < 0.02
        p = D.sample_inclusion(sizes, 40, weights={"read_3": 2.0, "read_2": 1.0, "other": 1.0}, sims=400)
        assert p["read_3"] > 1.7 * p["read_2"] and abs(p["read_2"] - p["other"]) < 0.02

    def test_sample_progress_counts_the_items_reached_by_stratum(self, env):
        log = make_log(env)
        assert log.state.sample_progress()["reached"] == 0
        first = log.state.queue("sample")[0]
        gid = act(log, action="open", source=first["source"])
        if log.state.groups[gid].status == "proposed":
            act(log, action="accept", group=gid)
        act(log, action="resolve", group=gid, resolution="reject")
        sp = log.state.sample_progress()
        assert sp["reached"] == 1 and sp["strata"][first["stratum"]]["done"] == 1
        assert sum(v["items"] for v in sp["strata"].values()) == len(log.state.queue("sample"))
        assert 0 < sp["strata"][first["stratum"]]["inclusion"] <= 1
        # a later session counts from its own start
        seq = max(e["seq"] for e in log.events)
        assert log.state.sample_progress(since_seq=seq)["reached"] == 0


# --------------------------------------------------------------------------- plan 12's persona-space badge, and --blind

DUP_BLOCK = {"nn": {"id": "alpha|T", "cos": 0.7742}, "flag": "duplicate_like", "m3_decision": "new",
             "disagreement": "dup_vs_new", "reading": {"stem": "alpha", "sonnet": 3, "opus": 3, "verdict": "keep"}}


class TestPersonaBadge:
    """Roger, 2026-10-15: a card badge for all three kinds, the duplicate flag prominent, the cover kinds quiet."""

    def test_the_three_kinds_and_none(self):
        lab = {"trait:alpha": "Alpha"}.get
        dup = D.persona_card({"persona": DUP_BLOCK}, lab)
        assert dup["kind"] == "duplicate" and dup["prominent"] and dup["reading"] == "3/3"
        assert dup["near"]["label"] == "Alpha" and dup["near"]["href"] == "/files/traits/alpha.json"
        cq = D.persona_card({"persona": {"nn": {"id": "beta|T", "cos": 0.6}, "flag": "ordinary",
                                         "disagreement": "cover_questioned", "cos_to_covered_by": 0.31}}, lab)
        assert cq["kind"] == "cover_questioned" and not cq["prominent"] and cq["cos_to_cover"] == 0.31
        nov = D.persona_card({"persona": {"nn": {"id": "hacker|R", "cos": 0.4}, "flag": "novel_like",
                                          "disagreement": "novel_vs_covered", "residual_pct": 0.97}}, lab)
        assert nov["kind"] == "novel" and nov["near"]["label"] == "hacker" and nov["near"]["href"] is None
        assert D.persona_card({"persona": {"flag": "ordinary", "disagreement": None}}) is None
        assert D.persona_card({}) is None

    def test_blind_card_strips_the_signals_and_nothing_else(self):
        card = {"id": "g1", "members": [{"key": "a#1", "label": "a", "gloss": "g", "persona": {"kind": "duplicate"},
                                         "lexical_merges": [{}], "flags": ["lexical_proposed_merge", "x"]}],
                "corpus": [{"key": "trait:alpha", "reading": "3/3", "lexical": {"lexicon": "oewn"}}]}
        b = D.blind_card(card)
        assert b["members"] == [{"key": "a#1", "label": "a", "gloss": "g", "flags": ["x"]}]
        assert b["corpus"] == [{"key": "trait:alpha", "reading": "3/3"}]
        assert card["members"][0]["persona"] == {"kind": "duplicate"}            # a copy: the original is untouched

    def _with_block(self, env):
        reg = env["reg"]
        row = reg.fold()[k("godless")]
        row["persona"] = DUP_BLOCK
        reg.write([row])

    def test_the_card_carries_the_badge_and_a_blind_server_leaves_it_out(self, env):
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        self._with_block(env)
        seen = {}
        for blind in (False, True):
            app = server.create_app(review_dir=env["rdir"], data_dir=env["data"], registry_path=env["reg"].path,
                                    by="roger", clock=Clock(), blind=blind)
            c = TestClient(app)
            assert c.get("/api/meta").json()["blind"] is blind
            r = c.post("/api/action", json={"action": "open", "source": f"term:{k('godless')}"}).json()
            m = {x["key"]: x for x in r["group"]["members"]}[k("godless")]
            t = c.get(f"/api/term/{quote(k('godless'), safe='')}").json()["term"]
            seen[blind] = (m.get("persona"), t.get("persona"))
        assert seen[False][0]["kind"] == "duplicate" and seen[False][1]["kind"] == "duplicate"
        assert seen[True] == (None, None)

    def test_the_page_renders_the_duplicate_badge_prominently(self, tmp_path):
        out = run_page(tmp_path, """
            T.S.card = {id: "g1", status: "open", source: "term:a#1", via: null, antonym_groups: [], neighbour_groups: [],
                        neighbours: [], corpus: [], opposed: [], resolution: null, nominated: null, leftovers: [], distinct: [],
                        members: [{key: "a#1", label: "above board", gloss: "g", tags: [], flags: [], merged: [], proposed: [],
                                   persona: {kind: "duplicate", prominent: true, reading: "3/3", reading_of: "honest",
                                             near: {key: "trait:honest", label: "honest", path: "p", href: "/files/traits/honest.json", cosine: 0.7742}}}]};
            T.renderCard();
            const h = el("card").innerHTML;
            console.log(h.includes('badge flag" title="persona space') && h.includes("close to <a") && h.includes("(0.77); overlap reading 3/3") ? "BADGE" : "MISSING " + h);
        """)
        assert "BADGE" in out


# --------------------------------------------------------------------------- the narrow pass's badge (QUESTIONS 208 (3))

KEPT_NARROW = {"pass": "narrow", "status": "kept", "parent": "trait:alpha", "parent_label": "alpha", "parent_final": 2,
               "n_children": 3, "asked": [{"parent": "trait:alpha", "reading": "2/-", "votes": ["narrower"] * 3}]}


class TestNarrowBadge:
    """Roger, 2026-10-20: at most one narrow trait per parent goes to review; the kept one says "narrower than X",
    hidden by ``serve --blind`` like the other signal badges."""

    def test_kept_held_and_none(self):
        lab = {"trait:alpha": "Alpha"}.get
        kept = D.narrow_card({"narrow": KEPT_NARROW}, lab)
        assert kept["status"] == "kept" and kept["parent"]["label"] == "Alpha" and kept["n_children"] == 3
        assert kept["parent"]["href"] == "/files/traits/alpha.json" and kept["reading"] == "2/-"
        held = D.narrow_card({"narrow": dict(KEPT_NARROW, status="held", parent="queue:queued", parent_label="queued",
                                             kept_child="other#1", held_because="sibling")})
        assert held["status"] == "held" and held["kept_child"] == "other#1" and held["parent"]["kind"] == "queue"
        assert held["parent"]["label"] == "queued"
        assert D.narrow_card({"narrow": dict(KEPT_NARROW, status="not_narrow", parent=None)}) is None
        assert D.narrow_card({}) is None
        assert "narrow" in D.SIGNAL_FIELDS
        assert D.blind_card({"label": "a", "key": "a#1", "gloss": "g", "narrow": kept}) == {
            "label": "a", "key": "a#1", "gloss": "g"}

    def test_the_card_carries_the_badge_and_a_blind_server_leaves_it_out(self, env):
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        reg = env["reg"]
        row = reg.fold()[k("loner")]
        row["narrow"] = KEPT_NARROW
        reg.write([row])
        seen = {}
        for blind in (False, True):
            app = server.create_app(review_dir=env["rdir"], data_dir=env["data"], registry_path=env["reg"].path,
                                    by="roger", clock=Clock(), blind=blind)
            c = TestClient(app)
            r = c.post("/api/action", json={"action": "open", "source": f"term:{k('loner')}"}).json()
            m = {x["key"]: x for x in r["group"]["members"]}[k("loner")]
            seen[blind] = m.get("narrow")
        assert seen[False]["status"] == "kept" and seen[False]["parent"]["label"] == "alpha"
        assert seen[True] is None

    def test_the_page_renders_narrower_than(self, tmp_path):
        out = run_page(tmp_path, """
            T.S.card = {id: "g1", status: "open", source: "term:a#1", via: null, antonym_groups: [], neighbour_groups: [],
                        neighbours: [], corpus: [], opposed: [], resolution: null, nominated: null, leftovers: [], distinct: [],
                        members: [{key: "a#1", label: "humblebragging", gloss: "g", tags: [], flags: [], merged: [], proposed: [],
                                   narrow: {status: "kept", n_children: 2, reading: "3/-", votes: ["narrower", "narrower"],
                                            parent: {key: "trait:boastful", label: "boastful", path: "p", href: "/files/traits/boastful.json", kind: "corpus"}}}]};
            T.renderCard();
            const h = el("card").innerHTML;
            console.log(h.includes("narrower than <a") && h.includes(">boastful</a>") ? "BADGE" : "MISSING " + h);
        """)
        assert "BADGE" in out


# --------------------------------------------------------------------------- split off (Roger, 2026-10-20)

class TestSplitOff:
    """The leftovers pass's third answer: a resolved group's leftover merged into another corpus or queue trait in one
    step, as a group of its own (a simplex half covered by X and half by Y used to take two passes)."""

    def _resolved_with_leftover(self, env):
        log = make_log(env)
        g = act(log, action="open", source="proposed:0")                     # balky, headstrong, willful
        act(log, action="accept", group=g)
        act(log, action="resolve", group=g, resolution="merge_into:trait:alpha")
        assert [x["key"] for x in log.state.group_card(g)["leftovers"]] == [k("obdurate")]
        return log, g

    def test_split_off_makes_a_resolved_group_that_handles_the_keys(self, env):
        log, g = self._resolved_with_leftover(env)
        ev, gid = log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "trait:beta",
                           "note": "covered by beta"})
        assert ev["action"] == "split_off" and ev["group"] == gid and gid != g and ev["split_from"] == g
        assert ev["target"] == "trait:beta" and ev["resolution"] == "merge_into:trait:beta" and ev["keys"] == [k("obdurate")]
        s = log.state.groups[gid]
        assert (s.status, s.source, s.split_from, s.resolution, s.resolved_members, s.note) == \
            ("resolved", f"split:{g}", g, "merge_into:trait:beta", [k("obdurate")], "covered by beta")
        assert log.state.handled[k("obdurate")] == gid
        card = log.state.group_card(g)
        assert card["leftovers"] == [] and card["split_groups"] == [gid]
        assert log.state.group_card(gid)["split_from"] == g
        assert log.state.queue_item("p1")["status"] == "done"
        st = log.status()
        assert st["by_action"]["split_off"] == 1 and st["groups"]["resolved"] == 2
        assert st["resolutions"] == {"merge_into": 2}
        assert snapshot(make_log(env)) == snapshot(log)                       # a restart replays it

    def test_split_off_is_validated_like_extend_and_needs_a_known_target(self, env):
        log, g = self._resolved_with_leftover(env)
        with pytest.raises(D.ActionError, match="not a corpus trait or queue entry"):
            log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "trait:nosuch"})
        with pytest.raises(D.ActionError, match="needs a target"):
            log.act({"action": "split_off", "group": g, "keys": [k("obdurate")]})
        with pytest.raises(D.ActionError, match="not a candidate"):
            log.act({"action": "split_off", "group": g, "keys": ["trait:alpha"], "target": "trait:beta"})
        with pytest.raises(D.ActionError, match="already a member"):
            log.act({"action": "split_off", "group": g, "keys": [k("balky")], "target": "trait:beta"})
        with pytest.raises(D.ActionError, match="needs keys"):
            log.act({"action": "split_off", "group": g, "keys": [], "target": "trait:beta"})
        g2 = act(log, action="open", source=f"term:{k('loner')}")
        with pytest.raises(D.ActionError, match="not resolved"):
            log.act({"action": "split_off", "group": g2, "keys": [k("obdurate")], "target": "trait:beta"})
        log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "queue:queued"})
        with pytest.raises(D.ActionError, match="is handled"):
            log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "trait:beta"})
        assert len([e for e in log.events if e["action"] == "split_off"]) == 1      # refusals log nothing

    def test_one_undo_takes_the_whole_split_back(self, env):
        log, g = self._resolved_with_leftover(env)
        _, gid = log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "trait:beta"})
        ev, shown = log.act({"action": "undo"})
        assert ev["undone_action"] == "split_off" and ev["undone_keys"] == [k("obdurate")] and ev["split_from"] == g
        assert gid not in log.state.groups and k("obdurate") not in log.state.handled
        assert [x["key"] for x in log.state.group_card(g)["leftovers"]] == [k("obdurate")]
        assert log.state.groups[g].status == "resolved"                       # the group it came from is untouched
        assert snapshot(make_log(env)) == snapshot(log)
        # a new split after the undo takes a fresh id (an undone group's id is never reused)
        _, gid2 = log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "trait:beta"})
        assert gid2 != gid

    def test_apply_writes_merged_into_the_split_target(self, env):
        log, g = self._resolved_with_leftover(env)
        _, gid = log.act({"action": "split_off", "group": g, "keys": [k("obdurate")], "target": "queue:queued"})
        rep = run_apply(env, log)
        rows = env["reg"].fold()
        rv = rows[k("obdurate")]["review"]
        assert rv["status"] == "merged_into" and rv["into"] == "queue:queued" and rv["review_group"] == gid
        assert rv["split_from"] == g and rv["group"] == [k("obdurate")]
        for x in ("balky", "headstrong", "willful"):
            assert rows[k(x)]["review"]["into"] == "trait:alpha" and "split_from" not in rows[k(x)]["review"]
        assert rep.promotions == [] and run_apply(env, log).review_writes == {}          # idempotent

    def test_the_server_shows_the_group_the_split_came_from(self, env):
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        app = server.create_app(review_dir=env["rdir"], data_dir=env["data"], registry_path=env["reg"].path,
                                by="roger", clock=Clock())
        c = TestClient(app)
        g = c.post("/api/action", json={"action": "open", "source": "proposed:0"}).json()["group"]["id"]
        c.post("/api/action", json={"action": "accept", "group": g})
        c.post("/api/action", json={"action": "resolve", "group": g, "resolution": "merge_into:trait:alpha"})
        r = c.post("/api/action", json={"action": "split_off", "group": g, "keys": [k("obdurate")],
                                         "target": "trait:beta"}).json()
        assert r["event"]["split_from"] == g and r["group"]["id"] == g and r["group"]["leftovers"] == []
        r = c.post("/api/action", json={"action": "undo"}).json()
        assert r["group"]["id"] == g and [x["key"] for x in r["group"]["leftovers"]] == [k("obdurate")]
        bad = c.post("/api/action", json={"action": "split_off", "group": g, "keys": [k("obdurate")],
                                           "target": "trait:nosuch"})
        assert bad.status_code == 409

    def test_the_page_key_c_splits_the_highlighted_leftover_off_into_the_highlighted_corpus_row(self, tmp_path):
        out = run_page(tmp_path, """
            T.S.card = {id: "g1", status: "resolved", resolution: "merge_into:trait:alpha", source: "proposed:0", via: null,
                        antonym_groups: [], neighbour_groups: [], neighbours: [], opposed: [], nominated: null, distinct: [],
                        members: [{key: "a#1", label: "balky", gloss: "g", tags: [], flags: [], merged: [], proposed: []}],
                        leftovers: [{key: "o#1", label: "obdurate", gloss: "g", level: 3, ties: 0, of: 1, groups: ["p1"]},
                                    {key: "p#1", label: "pigheaded", gloss: "g", level: 3, ties: 0, of: 1, groups: ["p1"]}],
                        corpus: [{key: "trait:alpha", kind: "corpus", label: "alpha", path: "p", href: "/files/traits/alpha.json", level: 2},
                                 {key: "trait:beta", kind: "corpus", label: "beta", path: "p", href: "/files/traits/beta.json", level: 2}]};
            T.S.pane = "leftovers"; T.S.idx.leftovers = 1; T.S.idx.corpus = 1;
            T.renderCard();
            const marked = el("corpus").innerHTML.includes('entry target') &&
                           el("corpus").innerHTML.includes("Split off into this");
            T.ACTIONS.merge_into();                     // what c does on a resolved group
            await sleep(20);
            const req = pending.find((x) => x.url === "/api/action");
            const b = req ? JSON.parse(req.opt.body) : {};
            console.log(marked && b.action === "split_off" && b.group === "g1" && b.target === "trait:beta"
                        && JSON.stringify(b.keys) === JSON.stringify(["p#1"]) ? "SPLIT" : "WRONG " + JSON.stringify(b) + " " + marked);
        """)
        assert "SPLIT" in out


# --------------------------------------------------------------------------- "probably covered by X" (Roger, 2026-10-20)

class TestProbablyCovered:
    """A free proposed merge for rows M3 read only 2: a prominent badge, X highlighted for c, hidden by --blind."""

    READINGS = [{"stem": "alpha", "cosine": 0.5, "relation": "similar", "sonnet": {"value": 2}, "opus": None},
                {"stem": "beta", "cosine": 0.3, "relation": "similar", "sonnet": {"value": 2}, "opus": None}]

    def _with_readings(self, env, key):
        reg = env["reg"]
        row = reg.fold()[key]
        row["novelty"] = dict(row["novelty"], readings=self.READINGS)
        reg.write([row])

    def test_the_card_and_blind_mode(self, env):
        from fastapi.testclient import TestClient
        from assistant_axis.gapgen.review_app import server
        self._with_readings(env, k("loner"))
        seen = {}
        for blind in (False, True):
            app = server.create_app(review_dir=env["rdir"], data_dir=env["data"], registry_path=env["reg"].path,
                                    by="roger", clock=Clock(), blind=blind)
            c = TestClient(app)
            r = c.post("/api/action", json={"action": "open", "source": f"term:{k('loner')}"}).json()
            seen[blind] = {x["key"]: x for x in r["group"]["members"]}[k("loner")].get("probably_covered")
        pc = seen[False]
        assert pc["target"]["key"] == "trait:alpha" and pc["target"]["href"] == "/files/traits/alpha.json"
        assert pc["n_read_2"] == 2 and pc["why_text"] == "cosine 0.50 to alpha"
        assert seen[True] is None and "probably_covered" in D.SIGNAL_FIELDS
        # never a cut: M3's decision on the card is unchanged
        log = make_log(env)
        assert log.state.member_card(k("loner"))["m3_decision"] == "new"

    def test_the_page_shows_the_badge_and_highlights_x_for_c(self, tmp_path):
        out = run_page(tmp_path, """
            T.S.card = null;
            const card = {id: "g1", status: "open", source: "term:a#1", via: null, antonym_groups: [], neighbour_groups: [],
                        neighbours: [], opposed: [], resolution: null, nominated: null, leftovers: [], distinct: [],
                        corpus: [{key: "trait:beta", kind: "corpus", label: "beta", path: "p", href: "/files/traits/beta.json", level: 2},
                                 {key: "trait:alpha", kind: "corpus", label: "alpha", path: "p", href: "/files/traits/alpha.json", level: 2}],
                        members: [{key: "a#1", label: "blendy", gloss: "g", tags: [], flags: [], merged: [], proposed: [],
                                   probably_covered: {n_read_2: 2, why_text: "cosine 0.50 to alpha",
                                     target: {key: "trait:alpha", kind: "corpus", label: "alpha", path: "p", href: "/files/traits/alpha.json"}}}]};
            T.S.pane = "members";
            const p = T.showGroup(card);                   // its queue load stays pending: what matters is set first
            await sleep(10);
            const h = el("card").innerHTML;
            const badge = h.includes("probably covered by <a") && h.includes("(2 traits read 2; cosine 0.50 to alpha)");
            T.ACTIONS.merge_into();                        // c
            await sleep(10);
            const req = pending.find((x) => x.url === "/api/action");
            const b = req ? JSON.parse(req.opt.body) : {};
            console.log(badge && T.S.idx.corpus === 1 && b.resolution === "merge_into:trait:alpha" ? "PROPOSED" : "WRONG " + JSON.stringify(b) + " " + T.S.idx.corpus + " " + badge);
        """)
        assert "PROPOSED" in out
