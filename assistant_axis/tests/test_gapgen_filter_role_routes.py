"""M1 in role mode (coding plan 16, task 2 and test 3): a role-aimed row is routed by the kind call's answer for its
most likely reading (``roles_pass.ROLE_ROUTES``, decision 3), its join recorded as judged and its route written on
the filter block; the gloss, alignment and descriptors calls are skipped unless the route is ``membership``; the
write-back keeps ``entity_type: "role"``; a trait-aimed row is routed exactly as before.  No API calls: the split
runner on the answers recorded on 2026-09-29 (``split_replay``)."""
import copy

import pytest

from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen import split
from assistant_axis.gapgen.filter import FilterItem, FilterResult, holding_for, is_role_aimed, items_from_records
from assistant_axis.gapgen.registry import new_record
from assistant_axis.gapgen.split_runner import SplitRunner
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic
from assistant_axis.tests.split_replay import HAIKU, make_responder, test_items

#: The block fields that come from M1's gloss, alignment and descriptors calls (null on a skipped row).
GLOSS_FIELDS = ("gloss_model", "region", "enactable_in_text", "alignment", "alignment_relevant", "last_step_reasons",
                "gloss_form_ok")


def runner(client, **kw):
    kw.setdefault("model", HAIKU)
    kw.setdefault("wordnet", False)
    kw.setdefault("zipf_fn", lambda w: 4.0)
    kw.setdefault("retry_delays", ())
    kw.setdefault("second_opinion", False)
    return SplitRunner(client=client, batch_id="t", **kw)


def role_items(items):
    out = []
    for it in items:
        it = copy.deepcopy(it)
        it.meta = dict(it.meta, entity_type="role")
        out.append(it)
    return out


@pytest.fixture(scope="module")
def runs():
    items = test_items()
    trait = {r.key: r for r in runner(FakeAsyncAnthropic(make_responder())).run(items)}
    client = FakeAsyncAnthropic(make_responder())
    rr = runner(client)
    role = {r.key: r for r in rr.run(role_items(items))}
    return trait, role, rr


# --------------------------------------------------------------------------- the table

def test_route_for_each_kind():
    assert {k: RP.route_for(k, entity_type="role") for k in split.KINDS} == {
        "trait": "both", "membership": "membership", "state": "turned_away", "physical": "turned_away",
        "role": "role", "action": "turned_away", "evaluative": "turned_away", "not_a_persona": "turned_away"}
    assert RP.route_for(None, entity_type="role") == "turned_away"
    assert all(RP.route_for(k, entity_type="trait") is None for k in split.KINDS)


def test_verdict_tags_holding_for_each_route():
    v = split.verdict_tags_holding
    assert v("roles", route="role", kind="role") == ("tagged", ["role_person"], None, "role")
    assert v("trait", route="both", kind="trait") == ("trait", [], None, "role")
    assert v("trait", membership_kind="religion", route="membership", kind="membership") == \
        ("trait", ["membership"], None, "trait")
    assert v("trait", membership_kind="nationality_ethnicity_language", route="membership", kind="membership") == \
        ("trait", ["membership"], "nationalities", "trait")
    assert v("states", route="turned_away", kind="state") == ("reject", ["state"], None, "role")
    assert v("physical", route="turned_away", kind="physical") == ("reject", ["physical"], None, "role")
    assert v("turned_away", cause="action", route="turned_away", kind="action") == ("reject", ["action"], None, "role")
    assert v("turned_away", cause="evaluative", route="turned_away", kind="evaluative") == \
        ("reject", ["evaluative_only"], None, "role")
    assert v("turned_away", cause="no_reading", route="turned_away", kind=None) == \
        ("reject", ["no_persona_reading"], None, "role")
    assert v("turned_away", cause="stretched", route="turned_away", kind=None) == ("reject", ["stretched"], None, "role")
    # a trait-aimed row: the table of section 6 as before
    assert v("roles") == ("tagged", ["role_person"], "roles", "role")
    assert v("trait") == ("trait", [], None, "trait")
    with pytest.raises(ValueError):
        v("trait", route="elsewhere")


def test_primary_kind_is_the_first_surviving_primary_reading():
    sense = {"readings": [
        {"reading": "a", "rank": "primary", "check_established": {"established": "stretched"}, "kind_call": {"kind": "trait"}},
        {"reading": "b", "rank": "primary", "check_established": {"established": "known"}, "kind_call": {"kind": "role"}},
        {"reading": "c", "rank": "primary", "check_established": {"established": "known"}, "kind_call": {"kind": "trait"}}]}
    assert split.primary_kind(sense) == "role"
    assert split.primary_kind({"readings": []}) is None and split.primary_kind(None) is None


# --------------------------------------------------------------------------- the runner on recorded answers

def test_a_trait_aimed_run_writes_no_route(runs):
    trait, _, _ = runs
    assert all("role_route" not in r.filter and "routes_version" not in r.filter for r in trait.values())
    assert all(r.registry_fields()["entity_type"] == ("role" if r.holding == "roles" else "trait")
               for r in trait.values())


def test_the_join_is_recorded_as_judged_and_only_the_routing_differs(runs):
    trait, role, _ = runs
    routes = {}
    for k, t in trait.items():
        r = role[k]
        route = r.filter["role_route"]
        routes[route] = routes.get(route, 0) + 1
        assert r.filter["routes_version"] == RP.ROUTES_VERSION
        assert route == RP.route_for(split.primary_kind(_sense_of(r)), entity_type="role")
        # the judgement is the same: outcome, cause, readings, the accepted reading, notes
        for f in ("outcome", "cause", "rule", "judged_sense", "accepted_reading", "notes", "sense", "membership_kind",
                  "same_sense", "senses", "person_senses"):
            assert r.filter[f] == t.filter[f], (k, f)
        skipped = route != "membership"
        if skipped:
            assert r.gloss is None and all(r.filter[f] is None for f in GLOSS_FIELDS), k
        else:
            assert r.gloss == t.gloss and all(r.filter[f] == t.filter[f] for f in GLOSS_FIELDS), k
        if route in ("role", "both"):
            assert (r.filter["verdict"], r.filter["tags"]) == (t.filter["verdict"], t.filter["tags"])
            assert r.holding is None and r.registry_fields()["entity_type"] == "role"
        elif route == "membership":
            assert (r.filter["verdict"], r.filter["tags"], r.holding) == (t.filter["verdict"], t.filter["tags"],
                                                                         t.holding)
            assert r.registry_fields()["entity_type"] == "trait"
        else:
            assert r.filter["verdict"] == "reject" and r.holding is None
            assert r.registry_fields()["entity_type"] == "role"
    assert routes.get("both") and routes.get("turned_away")             # the recorded words reach several routes


def _sense_of(res):
    return {"readings": [{"reading": x["reading"], "rank": x["rank"],
                          "check_established": {"established": x["established"]}, "kind_call": {"kind": x["kind"]}}
                         for x in (res.filter.get("sense") or {}).get("readings") or []]}


def test_the_gloss_wave_is_skipped_unless_the_route_is_membership(runs):
    _, role, rr = runs
    n_skip = sum(1 for r in role.values() if r.filter["outcome"] == "trait" and r.filter["role_route"] != "membership")
    assert rr.stats["role_aimed_gloss_skipped"] == n_skip > 0


def test_changing_the_trait_route_changes_only_those_rows(monkeypatch, runs):
    _, role, _ = runs
    monkeypatch.setitem(RP.ROLE_ROUTES, "trait", "role")
    again = {r.key: r for r in runner(FakeAsyncAnthropic(make_responder())).run(role_items(test_items()))}
    for k, r in role.items():
        a = again[k]
        if r.filter["role_route"] == "both":
            assert a.filter["role_route"] == "role"
            assert {f: v for f, v in a.filter.items() if f not in ("role_route", "at")} == \
                {f: v for f, v in r.filter.items() if f not in ("role_route", "at")}
        else:
            assert {f: v for f, v in a.filter.items() if f != "at"} == {f: v for f, v in r.filter.items() if f != "at"}


# --------------------------------------------------------------------------- items and write-back

def test_items_from_records_marks_role_aimed_rows_only():
    aimed = new_record("bouncer", entity_type="role", sources=[{"generator": "professions", "run_id": "w1",
                                                                "surface": "bouncer", "kind_guess": "occupation",
                                                                "human": True}])
    held = new_record("baker", sources=[{"generator": "censuses", "run_id": "c1", "surface": "baker"}])
    held["entity_type"] = "role"
    merged = copy.deepcopy(held)
    merged["sources"].append({"generator": "professions", "run_id": "w1", "surface": "baker",
                              "kind_guess": "occupation", "human": True})
    trait = new_record("plucky", sources=[{"generator": "g", "run_id": "r", "surface": "plucky"}])
    items = {it.key: it for it in items_from_records([aimed, held, merged, trait])}
    assert items["bouncer|R#1"].meta == {"generators": ["professions"], "entity_type": "role"}
    assert items["plucky#1"].meta == {"generators": ["g"]}
    assert is_role_aimed(aimed) and is_role_aimed(merged) and not is_role_aimed(held) and not is_role_aimed(trait)


def test_registry_fields_never_overwrite_a_submitted_role():
    r = FilterResult(key="x|R#1", label="x", stage="classified", freq={}, wordnet={},
                     filter={"verdict": "reject", "tags": ["too_rare"]}, meta={"entity_type": "role"})
    assert r.registry_fields()["entity_type"] == "role"                 # a floor cut keeps the role
    r.filter["role_route"] = "membership"
    assert r.registry_fields()["entity_type"] == "trait"


def test_holding_for_in_role_mode():
    assert holding_for("tagged", ["role_person"], entity_type="role") == (None, "role")
    assert holding_for("trait", [], entity_type="role") == (None, "role")
    assert holding_for("trait", ["membership"], "nationality_ethnicity_language", entity_type="role") == \
        ("nationalities", "trait")
    assert holding_for("tagged", ["state"], entity_type="role") == (None, "role")
    assert holding_for("tagged", ["role_person"]) == ("roles", "role")                # trait-aimed: as before
