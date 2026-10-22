"""Promotion of role rows (coding plan 16, task 11 and test 10): by name only, with ``allow_roles``; the role queue
entry of § 6.5; the collision checks per entity type (a role stem refused, a trait stem allowed with a loud NOTE,
Roger's decision 2 of 2026-10-22); a ``partner_hint`` makes a pair; the bulk path leaves role rows out and says so.
No API calls."""
import json

import pytest

from assistant_axis.gapgen import promote as P
from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.roles_fakes import aimed_row, gloss_for, held_row, write_role_corpus

GLOSS = gloss_for("bouncer", "works the door of a club")


def staged(row, *, kind="occupation", gloss=None, readings=None):
    row[RP.BLOCK] = {"gloss": gloss or gloss_for(row["label"], "does the work"), "kind": kind, "human": kind != "non_human",
                     "kind_unanimous": True, "kind_split": False, "batch_id": "roles_t", "model": RP.MODEL,
                     "kind_readings": readings or [{"kind": kind, "reason": "r"}] * 3,
                     "prompt_sha256": {"role_kind": "11b559f0cff50189aaaa", "role_gloss": "x"}}
    row["novelty"] = {"run_id": "roles_t", "pass": "roles", "decision": "new",
                      "listed": [{"stem": "judge", "cosine": 0.41, "relation": "unrelated"}],
                      "cross_type": {"traits": [{"stem": "assertive", "cosine": 0.33}]}}
    return row


@pytest.fixture
def data(tmp_path):
    d = write_role_corpus(tmp_path / "data")
    t = d / "traits" / "instructions"
    t.mkdir(parents=True)
    for s in ("optimistic", "specialist"):
        (t / f"{s}.json").write_text(json.dumps({"positive_label": s, "negative_label": f"non-{s}",
                                                 "description": f"This means being {s}."}))
    (d / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "warden", "label": "warden", "entity_type": "role", "status": "candidate"},
        {"stem": "jester", "label": "jester", "entity_type": "role", "status": "not_adopted",
         "decision": "too close to fool"},
        {"stem": "plucky", "label": "plucky", "entity_type": "trait", "status": "candidate"}]}))
    return d


def queue(data):
    return json.loads((data / "seed_queue.json").read_text())


def test_a_role_row_is_promoted_by_name_only(data):
    rows = {"bouncer|R#1": staged(aimed_row("bouncer", "works the door"), gloss=GLOSS)}
    rep = P.promote(rows, queue(data), ["bouncer|R#1"], data_dir=data)
    assert rep.promoted == [] and "promoted only by name" in rep.refused["bouncer|R#1"]
    rep = P.promote(rows, queue(data), ["bouncer|R#1"], data_dir=data, allow_roles=True)
    assert rep.promoted == ["bouncer|R#1"] and rep.notes == {}


def test_the_role_queue_entry(data):
    rows = {"bouncer|R#1": staged(aimed_row("bouncer", "works the door"), gloss=GLOSS)}
    q = queue(data)
    rep = P.promote(rows, q, ["bouncer|R#1"], data_dir=data, allow_roles=True, dry_run=False)
    e = q["entries"][-1]
    assert e == rep.entries[0]
    assert e["stem"] == "bouncer" and e["label"] == "bouncer" and e["entity_type"] == "role" and e["status"] == "candidate"
    assert e["tags"][:2] == ["gap_gen", "source:professions"] and "kind:occupation" in e["tags"] and "human:true" in e["tags"]
    assert "role_person" in e["tags"] and e["section"] == RP.SECTION == "role generators (2026-10)"
    assert e["description_draft"] == GLOSS and e["description"] is None and e["pairing"] == "singleton"
    assert e["source"] == "soc:bouncer"
    assert e["description_notes"].startswith("role pass roles_t | kind occupation (3 of 3) | nearest roles: judge 0.41")
    assert "nearest traits: assertive 0.33" in e["description_notes"]
    rk = e["gap_gen"]["role_kind"]
    assert rk["kind"] == "occupation" and rk["unanimous"] is True and rk["prompt_sha256"] == "11b559f0cff50189"
    assert rk["readings"] == ["occupation"] * 3 and e["gap_gen"]["registry_key"] == "bouncer|R#1"


def test_a_held_role_row_is_promoted_too(data):
    rows = {"baker#1": staged(held_row("baker", "bakes bread"))}
    rep = P.promote(rows, queue(data), ["baker#1"], data_dir=data, allow_roles=True)
    assert rep.promoted == ["baker#1"] and rep.entries[0]["gap_gen"]["holding"] == "roles"
    rows2 = {"baker#1": held_row("baker", "bakes bread")}
    rep = P.promote(rows2, queue(data), ["baker#1"], data_dir=data, allow_roles=True)
    assert "no role gloss" in rep.refused["baker#1"]


@pytest.mark.parametrize("stem,why", [("doctor", "role corpus"), ("warden", "role entry of the seed queue"),
                                      ("jester", "turned down")])
def test_a_role_stem_is_refused(data, stem, why):
    rows = {f"{stem}#1": staged(held_row(stem, "x"))}
    rep = P.promote(rows, queue(data), [f"{stem}#1"], data_dir=data, allow_roles=True)
    assert rep.promoted == [] and why in rep.refused[f"{stem}#1"]


def test_a_trait_stem_is_allowed_with_a_loud_note(data):
    rows = {"specialist|R#1": staged(aimed_row("specialist", "knows one field deeply"), kind="occupation"),
            "plucky|R#1": staged(aimed_row("plucky", "is plucky"), kind="temperament")}
    q = queue(data)
    rep = P.promote(rows, q, ["specialist|R#1", "plucky|R#1"], data_dir=data, allow_roles=True, dry_run=False)
    assert rep.promoted == ["specialist|R#1", "plucky|R#1"]
    assert "corpus trait specialist" in rep.notes["specialist|R#1"] and "COLLISION_NAMES" in rep.notes["specialist|R#1"]
    assert "seed-queue trait entry plucky" in rep.notes["plucky|R#1"]
    assert q["entries"][-2]["description_notes"].startswith("NOTE: the role specialist has the name of")


def test_a_partner_hint_makes_a_pair(data):
    r = staged(aimed_row("warder", "guards prisoners"))
    r["sources"][0]["partner_hint"] = "prisoner"
    rep = P.promote({"warder|R#1": r}, queue(data), ["warder|R#1"], data_dir=data, allow_roles=True)
    e = rep.entries[0]
    assert e["pairing"] == "pair" and e["partner"] == "prisoner" and e["pair_by_construction"] is False


def test_a_trait_row_is_promoted_as_before(data):
    from assistant_axis.tests.roles_fakes import trait_row
    rows = {"gutsy#1": trait_row("gutsy")}
    rep = P.promote(rows, queue(data), ["gutsy#1"], data_dir=data, allow_roles=True)
    assert rep.promoted == ["gutsy#1"] and rep.entries[0]["entity_type"] == "trait" and rep.notes == {}
    assert "kind:" not in " ".join(rep.entries[0]["tags"])


def test_gap_registry_promote(tmp_path, data, capsys):
    from data_analysis.gap_generation import gap_registry
    reg = Registry(tmp_path / "candidates" / "registry.jsonl")
    r = staged(aimed_row("bouncer", "works the door"), gloss=GLOSS)
    r["review"] = {"status": "accepted"}
    s = staged(aimed_row("specialist", "knows one field deeply"))
    reg.write([r, s])
    base = ["--registry", str(reg.path), "--data-dir", str(data), "promote", "--queue", str(data / "seed_queue.json")]
    assert gap_registry.main([*base, "--status", "accepted", "--dry-run"]) == 0
    o = capsys.readouterr().out
    assert "REFUSED bouncer|R#1: a role-aimed row (a role row" in o and "promoted by name" in o and "--allow-roles" in o
    assert gap_registry.main([*base, "--status", "accepted", "--allow-roles"]) == 2
    assert "by name only" in capsys.readouterr().err
    assert gap_registry.main([*base, "--keys", "bouncer|R#1"]) == 0
    assert "REFUSED bouncer|R#1: a role-aimed row" in capsys.readouterr().out    # --keys alone is not enough
    assert gap_registry.main([*base, "--keys", "bouncer|R#1", "specialist|R#1", "--allow-roles"]) == 0
    o = capsys.readouterr().out
    assert "PROMOTED bouncer|R#1 -> bouncer (role)" in o and "*** NOTE specialist|R#1:" in o
    assert reg.fold()["bouncer|R#1"]["seed_queue_stem"] == "bouncer"


def test_gap_registry_holding_list_shows_the_role_gloss_and_kind(tmp_path, capsys):
    from data_analysis.gap_generation import gap_registry
    reg = Registry(tmp_path / "registry.jsonl")
    reg.write([staged(held_row("baker", "bakes bread"), gloss="A baker is someone who bakes bread before dawn."),
               held_row("captive", "is held prisoner")])
    assert gap_registry.main(["--registry", str(reg.path), "holding", "--list", "roles"]) == 0
    o = capsys.readouterr().out
    assert "**baker** (role_person; from censuses): A baker is someone who bakes bread before dawn. [kind occupation]" in o
    assert "**captive**" in o
