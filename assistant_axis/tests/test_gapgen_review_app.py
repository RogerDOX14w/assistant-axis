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

    def test_a_term_in_a_merged_group_opens_that_group_already_merged(self, env):
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('nonreligious')}")
        assert log.state.groups[g].source == "merged:0" and log.state.groups[g].status == "open"


# --------------------------------------------------------------------------- the log: replay and undo

def snapshot(log) -> dict:
    s = log.state
    return {"groups": {g: x.as_dict() for g, x in s.groups.items()}, "handled": dict(s.handled), "counts": s.counts(),
            "queue": [(q["id"], q["status"], q["handled"]) for q in s.queue("cliques")]}


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

    def test_a_refused_promotion_is_reported_and_the_review_block_still_written(self, env):
        (env["data"] / "traits" / "instructions" / "loner.json").write_text("{}")   # the stem is in the corpus now
        log = make_log(env)
        g = act(log, action="open", source=f"term:{k('loner')}")
        act(log, action="resolve", group=g, resolution="promote")
        rep = run_apply(env, log)
        assert rep.refused == {k("loner"): "stem exists in the corpus"}
        assert env["reg"].fold()[k("loner")]["review"]["status"] == "accepted"
        assert "loner" not in {e["stem"] for e in json.loads(env["queue"].read_text())["entries"]}


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
