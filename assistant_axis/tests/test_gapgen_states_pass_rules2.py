"""The states pass after gate audit 7 (Roger, 2026-10-12; ``reports/code_review_2026-10-12/gate_audits/states_pass.md``):

* route rules 2: the gloss check confirms any reading but ``passing`` (rules 1 wanted the route's own reading);
* route rules 2: a one-hop row (a rename the pass itself submitted, whose name does not fit) is released under its own
  name with the suggested name on its block and its review card (rules 1 held it);
* the text the queue call is shown loses M1's "now" markers (``state_text_form`` ``now_stripped``), so that the
  duration question is about the state the word names;
* ``--reroute``: rows decided under rules 1 decided again from their batch's record, with no call, and
  ``--send-missing`` for the calls a re-routed row needs and its batch never made.

The old behaviour stays reproducible behind ``route_rules=1`` / ``--route-rules 1`` and ``--state-text-form
as_recorded``.  No API call: fake clients throughout (the CLI fixture of ``test_gapgen_states_pass_v4``)."""
import argparse
import json
from collections import Counter

import pytest

from assistant_axis.gapgen import states_pass as sp
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text
from assistant_axis.tests.test_gapgen_states_pass_v4 import (_states_row, cli, released_row,  # noqa: F401 (cli: fixture)
                                                             responder)

H55 = "claude-haiku-5-5"

#: Invented words; every gloss is free of the scan's markers, so the check call reads each one.
SPEC = {
    "crossish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
                     gloss="This means wearing a dejected look and taking gloomy views of one's chances."),
    "crossl": dict(typical_duration="months", lasting=True, role=False,
                   gloss="This means living under a debt of gratitude to someone who helped, deferring to their wishes."),
    "passish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=True,
                    gloss="This means bubbling over with silly laughter and losing the thread of serious talk."),
    "hopish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False, suggested_name="hopname",
                   gloss="This means bracing for trouble in ordinary moments and speaking in clipped, guarded tones."),
    "hoppass": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False,
                    suggested_name="hoppassname", gloss="This means grinning slyly at people across the room."),
    "plainheld": dict(typical_duration="hours", lasting=False, plausible=False),
    "renamish": dict(typical_duration="hours", lasting=False, plausible=True, name_fits=False,
                     suggested_name="renamename", gloss="This means jolting at sudden noise."),
}
CHECK = {"crossish": "lasting", "crossl": "predisposition", "passish": "passing", "hopish": "predisposition",
         "hoppass": "passing"}
ALIGN = {"crossish": 1, "crossl": 0, "hopish": 2}


def answers():
    return responder(spec=SPEC, check=CHECK, align=ALIGN)


def items(labels, *, hop=()):
    return [sp.StatesItem(key=f"{lb}#1", label=lb, text=f"being {lb} for a while",
                          meta={"from_states_pass": lb in hop}) for lb in labels]


def run(labels, *, hop=(), rules=sp.ROUTE_RULES_VERSION):
    r = sp.StatesPassRunner(client=FakeAsyncAnthropic(answers()), batch_id="r2", mode="queue", model=H55,
                            retry_delays=(), route_rules=rules)
    return {x.key.split("#")[0]: x.block for x in r.run(items(labels, hop=hop))}


# --------------------------------------------------------------------------- the gloss check's rule

class TestGlossCheckRule:
    @pytest.mark.parametrize("reading, route, rules, ok", [
        ("predisposition", "predisposition", 2, True), ("lasting", "predisposition", 2, True),
        ("predisposition", "lasting", 2, True), ("lasting", "lasting", 2, True),
        ("passing", "predisposition", 2, False), ("passing", "lasting", 2, False),
        ("predisposition", "predisposition", 1, True), ("lasting", "predisposition", 1, False),
        ("predisposition", "lasting", 1, False), ("passing", "lasting", 1, False),
    ])
    def test_gloss_check_accepts(self, reading, route, rules, ok):
        assert sp.gloss_check_accepts(reading, route, rules=rules) is ok

    def test_unknown_rules_and_readings_are_refused(self):
        with pytest.raises(ValueError):
            sp.gloss_check_accepts("lasting", "lasting", rules=3)
        with pytest.raises(ValueError):
            sp.gloss_check_accepts("momentary", "lasting")
        with pytest.raises(ValueError):
            sp.StatesPassRunner(client=None, batch_id="x", mode="queue", route_rules=0)

    def test_lasting_and_predisposition_readings_release_and_passing_still_holds(self):
        b = run(("crossish", "crossl", "passish"))
        # a predisposition gloss read as lasting: released, the route the queue call's (the duration's)
        assert b["crossish"]["route"] == "predisposition" and b["crossish"]["holding_after"] == "states_released"
        chk = b["crossish"]["gloss_check"]
        assert chk["by"] == "check" and chk["accepted"] is True and chk["check"]["reading"] == "lasting"
        assert b["crossish"]["alignment"] == 1 and b["crossish"]["route_rules"] == 2
        # a lasting gloss read as predisposition: released as lasting
        assert b["crossl"]["route"] == "lasting" and b["crossl"]["gloss_check"]["check"]["reading"] == "predisposition"
        # passing still holds
        assert b["passish"]["route"] == "held" and b["passish"]["proposed_route"] == "predisposition"
        assert b["passish"]["route_reason"].startswith("gloss check: the predisposition gloss was read as passing")

    def test_route_rules_1_reproduce_the_old_holds(self):
        b = run(("crossish", "crossl", "passish"), rules=1)
        assert {k: v["route"] for k, v in b.items()} == {"crossish": "held", "crossl": "held", "passish": "held"}
        assert b["crossish"]["route_reason"].startswith("gloss check: the predisposition gloss was read as lasting")
        assert b["crossl"]["proposed_route"] == "lasting" and b["crossish"]["alignment"] is None
        assert all(v["route_rules"] == 1 for v in b.values())

    def test_the_promoted_entry_says_how_the_check_read_the_gloss(self):
        row = released_row("crossish")
        row["states_pass"].update(gloss_check={"kind": "predisposition", "accepted": True, "by": "check",
                                               "check": {"reading": "lasting", "reason": "r"}}, route_rules=2)
        e = sp.queue_entry_extras({"tags": []}, row)
        assert "gloss confirmed by the check (read as lasting)" in e["description_notes"]
        assert e["gap_gen"]["states_pass"]["route_rules"] == 2


# --------------------------------------------------------------------------- the one-hop row

class TestOneHopRelease:
    ANS = dict(lasting=False, plausible=True, name_fits=False, suggested_name="other name")

    def test_route_for(self):
        route, why = sp.route_for(self.ANS, label="x", from_states_pass=True)
        assert route == "predisposition" and why.startswith(sp.ONE_HOP_RELEASE_REASON) and "'other name'" in why
        assert sp.route_for(self.ANS, label="x", from_states_pass=True, rules=1) == ("held", sp.ONE_HOP_REASON)
        assert sp.route_for(self.ANS, label="x")[0] == "renamed"            # not a states-pass row: renamed as before

    def test_released_under_its_own_name_with_the_suggestion_kept(self):
        r = sp.StatesPassRunner(client=FakeAsyncAnthropic(answers()), batch_id="r2", mode="queue", model=H55,
                                retry_delays=())
        out = r.run(items(("hopish", "renamish"), hop=("hopish",)))
        b = {x.key.split("#")[0]: x.block for x in out}
        h = b["hopish"]
        assert h["route"] == "predisposition" and h["holding_after"] == "states_released" and h["one_hop"] is True
        assert h["suggested_name"] == "hopname" and h["name_fits"] is False and h["alignment"] == 2
        assert h["gloss_check"]["accepted"] is True and sp.is_one_hop(h)
        # no second rename is submitted; the other row's rename goes through as before
        assert [c.surface for c in sp.renamed_candidates(out, batch_id="r2")] == ["renamename"]
        assert "one_hop" not in b["renamish"]

    def test_a_one_hop_gloss_read_as_passing_is_held_and_still_marked(self):
        b = run(("hoppass",), hop=("hoppass",))["hoppass"]
        assert b["route"] == "held" and b["one_hop"] is True and sp.is_one_hop(b)
        assert b["proposed_route"] == "predisposition" and b["suggested_name"] == "hoppassname"

    def test_the_card_and_the_queue_entry_show_the_suggested_name(self):
        row = released_row("hopish")
        row["states_pass"].update(name_fits=False, suggested_name="hopname", one_hop=True, route_rules=2,
                                  route_reason=f"{sp.ONE_HOP_RELEASE_REASON}; suggested name 'hopname' on its card")
        assert sp.card_tag(row) == "states pass: predisposition (hours); suggested name: hopname"
        e = sp.queue_entry_extras({"tags": []}, row)
        assert "the pass suggested the name 'hopname'" in e["description_notes"]
        assert e["gap_gen"]["states_pass"]["suggested_name"] == "hopname"
        # a released row whose name fits shows no suggestion
        assert sp.card_tag(released_row("glumish")) == "states pass: predisposition (hours)"
        same = released_row("glumish")
        same["states_pass"].update(name_fits=False, suggested_name="Glumish")
        assert sp.other_name(same["states_pass"], "glumish") is None

    def test_the_review_app_card_carries_the_chip(self):
        from assistant_axis.gapgen import review_graph as RG
        from assistant_axis.gapgen.review_app import decisions as D
        row = released_row("hopish")
        row["states_pass"].update(name_fits=False, suggested_name="hopname", one_hop=True)
        row["novelty"] = {"run_id": "states_m3", "pass": "states", "decision": "new"}
        node = RG._candidate_node(row)
        g = RG.Graph(batch_id="rv", from_batches=["states_m3"], config={}, nodes=[node], edges=[], cliques=[],
                     clique_links=[], proposed_groups=[], proposed_links=[])
        card = D.ReviewState(g, rows={row["key"]: row}).member_card(row["key"])
        assert "states pass: predisposition (hours); suggested name: hopname" in card["tags"]


# --------------------------------------------------------------------------- what the duration question reads

class TestStateTextForm:
    @pytest.mark.parametrize("text, shown", [
        # the audit's examples: Roger's two missed lasting words, corpus traits it held, the one-hop rows
        ("currently feeling sad, low, or down in mood", "feeling sad, low, or down in mood"),            # depressed
        ("feeling sorrow or grief right now", "feeling sorrow or grief"),                                # sorrowing
        ("currently feeling satisfied and at ease with one's situation",
         "feeling satisfied and at ease with one's situation"),                                          # contented
        ("you are sluggish, tired and low on energy right now", "you are sluggish, tired and low on energy"),
        ("nervous or on edge, in a passing emotional state", "nervous or on edge"),                      # tense
        ("currently in a rush, pressed for time", "in a rush, pressed for time"),                        # hurried
        ("weary and anxious from worry at present", "weary and anxious from worry"),                     # careworn
        ("in a merry, celebratory mood for the moment", "in a merry, celebratory mood"),                 # festive
        ("physically needs food now", "physically needs food"),                                          # hungry
        # parentheticals: a bare word for a state goes, a kind stays
        ("despairing, has lost all hope (passing emotional state)", "despairing, has lost all hope (emotional state)"),
        ("whimpering and fretting in a fussy, complaining way (a passing mood)",
         "whimpering and fretting in a fussy, complaining way"),
        ("you are very hungry right now (bodily, passing condition)", "you are very hungry (bodily condition)"),
        ("covered in mud, dirty from mud (a passing condition of the body or clothes)",
         "covered in mud, dirty from mud (a condition of the body or clothes)"),
        ("in a passing state of agitation and confusion", "in a state of agitation and confusion"),
        ("feeling annoyed and blocked (a passing emotional state)", "feeling annoyed and blocked (an emotional state)"),
        ("engaged in fishing, as a passing situation", "engaged in fishing"),
        # no marker: unchanged; "passing" that is not about a state stays
        ("grieving or mourning a loss", "grieving or mourning a loss"),                                   # lamenting
        ("doing nothing, loafing or passing time", "doing nothing, loafing or passing time"),
        ("knows nowhere to go", "knows nowhere to go"),
    ])
    def test_strip_now_markers(self, text, shown):
        assert sp.strip_now_markers(text) == shown

    def test_degenerate_texts(self):
        assert sp.strip_now_markers(None) is None and sp.strip_now_markers("") == ""
        assert sp.strip_now_markers("currently") == "currently"           # nothing would be left: kept
        assert sp.strip_now_markers("  feeling   low  ") == "feeling low"
        with pytest.raises(ValueError):
            sp.shown_state_text("x", "stripped")

    def test_items_show_the_stripped_text_and_keep_m1s(self):
        row = {"key": "lowish#1", "label": "lowish", "holding": "states", "gloss": None, "sources": [],
               "filter": {"judged_sense": "currently feeling low right now"}}
        it = sp.items_from_registry([row])[0]
        assert it.text == "feeling low" and it.meta["text_as_recorded"] == "currently feeling low right now"
        old = sp.items_from_registry([row], text_form="as_recorded")[0]
        assert old.text == "currently feeling low right now" and "text_as_recorded" not in old.meta
        plain = dict(row, filter={"judged_sense": "grieving a loss"})
        assert "text_as_recorded" not in sp.item_from_row(plain).meta
        fr = sp.items_from_filter_results([{**row, "meta": {}, "filter": {"tags": ["state"],
                                                                          "judged_sense": "sad at the moment"}}])
        assert fr[0].text == "sad"

    def test_the_queue_call_reads_the_stripped_text_and_the_prompt_is_unchanged(self):
        client = FakeAsyncAnthropic(answers())
        row = {"key": "plainheld#1", "label": "plainheld", "holding": "states", "gloss": None, "sources": [],
               "filter": {"judged_sense": "currently feeling plain right now"}}
        r = sp.StatesPassRunner(client=client, batch_id="r2", mode="queue", model=H55, retry_delays=(),
                                text_form="now_stripped")
        out = r.run(sp.items_from_registry([row]))
        q = next(c for c in client.calls if system_text(c) == sp.QUEUE_PROMPT)
        shown = json.loads(user_text(q).splitlines()[1])
        assert shown["state_description"] == "feeling plain" and "currently" not in user_text(q)
        assert out[0].block["state_text_form"] == "now_stripped"
        from assistant_axis.gapgen.rubric_versions import current
        assert current()["states_queue"] == (4, sp.PROMPT_SHA256["queue"])     # a payload change, not a prompt one

    def test_resolution_on_resume(self, cli):
        mod = cli["mod"]
        ns = argparse.Namespace(route_rules=None, state_text_form=None)
        assert mod.resolve_text_form(ns) == "now_stripped" and mod.resolve_route_rules(ns) == 2
        # a run that recorded neither (every run before 2026-10-12) resumes as it ran
        assert mod.resolve_text_form(ns, {}) == "as_recorded" and mod.resolve_route_rules(ns, {}) == 1
        rec = {"state_text_form": "now_stripped", "route_rules": 2}
        assert mod.resolve_text_form(ns, rec) == "now_stripped" and mod.resolve_route_rules(ns, rec) == 2
        with pytest.raises(SystemExit):
            mod.resolve_text_form(argparse.Namespace(route_rules=None, state_text_form="as_recorded"), rec)
        assert mod.resolve_route_rules(argparse.Namespace(route_rules=1, state_text_form=None), rec) == 1

    def test_the_cli_dry_run_says_what_it_shows(self, tmp_path, cli, capsys):
        reg = tmp_path / "registry.jsonl"
        _states_row(reg, "plainheld", judged="currently being plain right now")
        _states_row(reg, "crossish", judged="being cross")
        assert cli["mod"].main(["--batch-id", "d1", "--mode", "queue", "--holding-states", "--registry", str(reg),
                                "--out-root", str(tmp_path / "cand"), "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert '"route_rules": 2, "state_text_form": "now_stripped"' in out
        assert "route rules: 2; state text form: now_stripped (1 of 2 texts lose a 'now' marker)" in out
        assert '"state_description": "being plain"' in out


# --------------------------------------------------------------------------- --reroute

def _batch_under_rules_1(tmp_path, cli):
    """A registry and the record of a batch judged under route rules 1 (the state of 2026-10-12's two batches)."""
    reg = tmp_path / "registry.jsonl"
    for lb in ("crossish", "passish", "hopish", "plainheld", "renamish"):
        _states_row(reg, lb, gen="states_pass" if lb == "hopish" else "g")
    cand = tmp_path / "cand"
    cli["responder"] = answers()
    # one reading, as those batches were (a batch of three readings: test_gapgen_states_pass_readings.py)
    assert cli["mod"].main(["--batch-id", "b1", "--mode", "queue", "--holding-states", "--registry", str(reg),
                            "--out-root", str(cand), "--transport", "live", "--route-rules", "1",
                            "--readings", "1"]) == 0
    rows = Registry(reg).fold()
    assert {k.split("#")[0]: rows[k]["states_pass"]["route"] for k in rows if rows[k].get("states_pass")} == {
        "crossish": "held", "passish": "held", "hopish": "held", "plainheld": "held", "renamish": "renamed"}
    return reg, cand


class TestReroute:
    def test_needs_reroute(self):
        row = {"holding": "states", "states_pass": {"mode": "queue", "route": "held"}}
        assert sp.needs_reroute(row) and not sp.needs_reroute(row, 1)
        assert not sp.needs_reroute({**row, "holding": "states_released"})
        assert not sp.needs_reroute({"holding": "states", "states_pass": {"mode": "queue", "plausible": True}})  # v3

    def test_dry_run_prints_the_changes_and_writes_nothing(self, tmp_path, cli, capsys):
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        before, n_clients = reg.read_bytes(), len(cli["live"])
        capsys.readouterr()
        assert cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand), "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "CHANGED   crossish (b1): held -> predisposition (states_released); gloss confirmed by the check " \
               "(read as lasting); alignment 1" in out
        assert "NEEDS     hopish (b1): held -> predisposition once alignment and check call(s) are made" in out
        assert "suggested name 'hopname' on its card" in out
        assert "UNCHANGED 3: passish (held), plainheld (held), renamish (renamed)" in out
        assert "reroute: 1 changed, 3 unchanged, 1 need calls, 0 without a record (of 5 rows" in out
        assert "--send-missing would make 2 call(s)" in out
        assert reg.read_bytes() == before and not (cand / "states_pass" / "rr").exists()
        assert len(cli["live"]) == n_clients                              # no client was made

    def test_reroute_writes_from_the_record_without_a_call(self, tmp_path, cli):
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        n_clients = len(cli["live"])
        assert cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand)]) == 0
        assert len(cli["live"]) == n_clients
        rows = Registry(reg).fold()
        b = rows["crossish#1"]["states_pass"]
        assert rows["crossish#1"]["holding"] == "states_released" and sp.is_released(rows["crossish#1"])
        assert b["route"] == "predisposition" and b["route_rules"] == 2 and b["batch_id"] == "b1"
        assert b["gloss_check"]["check"]["reading"] == "lasting" and b["alignment"] == 1   # both from the record
        assert b["rerouted"]["batch_id"] == "rr" and b["rerouted"]["previous"]["route"] == "held"
        assert b["rerouted"]["previous"]["route_rules"] == 1 and b["state_text_form"] == "now_stripped"
        # the rows the record cannot settle, and those that do not change, are left as they were
        assert rows["hopish#1"]["holding"] == "states" and rows["hopish#1"]["states_pass"]["route_rules"] == 1
        assert rows["passish#1"]["states_pass"]["route_rules"] == 1
        d = cand / "states_pass" / "rr"
        res = {json.loads(x)["label"]: json.loads(x)["outcome"] for x in (d / "results.jsonl").read_text().splitlines()}
        assert res == {"crossish": "changed", "hopish": "needs_calls", "passish": "unchanged", "plainheld": "unchanged",
                       "renamish": "unchanged"}
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 0
        run = json.loads((d / "run.json").read_text())
        assert run["reroute"] is True and run["source_batches"] == ["b1"] and run["cost_usd"] == 0

    def test_send_missing_makes_only_the_missing_calls(self, tmp_path, cli):
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        assert cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand), "--send-missing"]) == 0
        sent = cli["live"][-1].calls
        assert sorted("check" if system_text(c) == sp.CHECK_PROMPT else "queue" if system_text(c) == sp.QUEUE_PROMPT
                      else "alignment" for c in sent) == ["alignment", "check"]
        assert all(json.loads(user_text(c))["label"] == "hopish" for c in sent)
        rows = Registry(reg).fold()
        h = rows["hopish#1"]["states_pass"]
        assert rows["hopish#1"]["holding"] == "states_released" and h["route"] == "predisposition"
        assert h["suggested_name"] == "hopname" and h["one_hop"] is True and h["alignment"] == 2
        assert h["batch_id"] == "b1" and h["rerouted"]["batch_id"] == "rr"
        assert rows["crossish#1"]["holding"] == "states_released"
        d = cand / "states_pass" / "rr"
        new = [json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines()]
        assert len(new) == 2 and {x["batch_id"] for x in new} == {"rr"}       # only the calls this run made
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 2
        # rerouting again finds nothing left to change
        assert cli["mod"].main(["--batch-id", "rr2", "--mode", "queue", "--reroute", "--registry", str(reg),
                                "--out-root", str(cand)]) == 0
        assert not (cand / "states_pass" / "rr2").exists()

    def test_route_rules_1_reproduces_the_old_routing(self, tmp_path, cli):
        """The same rows under ``--route-rules 1`` give the old holds; a reroute to rules 1 of rows decided under 1
        has nothing to do."""
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        rows = Registry(reg).fold()
        assert rows["hopish#1"]["states_pass"]["route_reason"] == sp.ONE_HOP_REASON
        assert rows["crossish#1"]["states_pass"]["proposed_route"] == "predisposition"
        assert cli["mod"].main(["--batch-id", "rr1", "--mode", "queue", "--reroute", "--route-rules", "1",
                                "--registry", str(reg), "--out-root", str(cand)]) == 0
        assert not (cand / "states_pass" / "rr1").exists()


# --------------------------------------------------------------------------- what a re-route records

#: The gloss check's and the alignment call's prompt fields of a queue run's run.json.
GLOSS_FIELDS = ("check_rubric_version", "check_prompt_sha256", "alignment_model", "alignment_step_version",
                "alignment_prompt_sha256")


def _run_json(cand, batch):
    return json.loads((cand / "states_pass" / batch / "run.json").read_text())


def _reroute(cli, reg, cand, *extra):
    return cli["mod"].main(["--batch-id", "rr", "--mode", "queue", "--reroute", "--registry", str(reg),
                            "--out-root", str(cand), *extra])


def _under_another_queue_prompt(cand, batch="b1"):
    """Make a batch's record say its queue answers were given under queue prompt v3 (its run.json and its queue
    records), as a batch judged before a prompt change: the runner replays none of its queue answers (its check and
    alignment answers still are).  Returns v3's sha."""
    from assistant_axis.gapgen.rubric_versions import HISTORY
    d, v3 = cand / "states_pass" / batch, HISTORY["states_queue"][3]
    (d / "run.json").write_text(json.dumps({**_run_json(cand, batch), "rubric_version": 3, "prompt_sha256": v3}))
    recs = [json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines()]
    (d / "responses.jsonl").write_text("".join(
        json.dumps({**r, "prompt_sha256": v3} if r["step"] == "queue" else r) + "\n" for r in recs))
    return v3


def _steps(client):
    return Counter("check" if system_text(c) == sp.CHECK_PROMPT else "queue" if system_text(c) == sp.QUEUE_PROMPT
                   else "alignment" for c in client.calls)


class TestRerouteRecord:
    """A re-route's run.json names the prompts of the answers it used under a queue run's names, so that the pin test
    reads it as it reads a queue run's (until 2026-10-13 it recorded none: ``states_reroute_r2`` was filled in by
    hand)."""

    def test_the_queue_prompt_of_the_answers_replayed(self, tmp_path, cli):
        from assistant_axis.tests.test_gapgen_rubric_v2_round4 import pin_problems
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        assert _reroute(cli, reg, cand) == 0
        run, src = _run_json(cand, "rr"), _run_json(cand, "b1")
        assert (run["rubric_version"], run["prompt_sha256"]) == (src["rubric_version"], src["prompt_sha256"]) \
            == (4, sp.PROMPT_SHA256["queue"])
        assert run["queue_prompts"] == {"b1": {"rubric_version": 4, "prompt_sha256": sp.PROMPT_SHA256["queue"]}}
        assert not set(GLOSS_FIELDS) & set(run) and "queue_prompts_note" not in run     # no call was sent
        assert pin_problems("states_pass/rr", run) == []

    def test_send_missing_records_the_check_and_alignment_prompts_it_sent(self, tmp_path, cli):
        from assistant_axis.tests.test_gapgen_rubric_v2_round4 import pin_problems
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        assert _reroute(cli, reg, cand, "--send-missing") == 0
        run, src = _run_json(cand, "rr"), _run_json(cand, "b1")
        # as the queue run records them, and the prompts the calls were in fact sent with
        assert {k: run[k] for k in GLOSS_FIELDS} == {k: src[k] for k in GLOSS_FIELDS}
        assert (run["check_rubric_version"], run["check_prompt_sha256"]) == (1, sp.CHECK_PROMPT_SHA256)
        sent = [json.loads(x) for x in (cand / "states_pass" / "rr" / "responses.jsonl").read_text().splitlines()]
        assert {x["step"]: x["prompt_sha256"] for x in sent} == {"check": run["check_prompt_sha256"],
                                                                  "alignment": run["alignment_prompt_sha256"]}
        h = Registry(reg).fold()["hopish#1"]["states_pass"]
        assert (h["alignment_step_version"], h["alignment_prompt_sha256"]) == (run["alignment_step_version"],
                                                                                run["alignment_prompt_sha256"])
        # no queue call was sent: the queue prompt is the source batch's alone; the calls ran capped at the budget
        assert run["rubric_version"] == 4 and list(run["queue_prompts"]) == ["b1"]
        assert run["estimate_usd"] > 0 and run["cap_usd"] == 1.0
        assert pin_problems("states_pass/rr", run) == []

    def test_batches_on_different_queue_prompts_are_recorded_per_batch(self, tmp_path, cli):
        """A batch recorded under an older queue prompt (here v3, the record made to say so) has no queue answer the
        replay can use (the runner skips another prompt's answers), so ``--send-missing`` asks its rows again under
        the current one: the re-route's own batch joins ``queue_prompts``, and with the two prompts differing no
        top-level pair is recorded.  Each batch's pair is still pinned."""
        from assistant_axis.tests.test_gapgen_rubric_v2_round4 import pin_problems
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        v3 = _under_another_queue_prompt(cand)
        assert _reroute(cli, reg, cand, "--send-missing") == 0
        run = _run_json(cand, "rr")
        sent = [json.loads(x) for x in (cand / "states_pass" / "rr" / "responses.jsonl").read_text().splitlines()]
        assert {x["prompt_sha256"] for x in sent if x["step"] == "queue"} == {sp.PROMPT_SHA256["queue"]}
        assert run["queue_prompts"] == {"b1": {"rubric_version": 3, "prompt_sha256": v3},
                                        "rr": {"rubric_version": 4, "prompt_sha256": sp.PROMPT_SHA256["queue"]}}
        assert "rubric_version" not in run and "prompt_sha256" not in run and run["queue_prompts_note"]
        assert set(GLOSS_FIELDS) <= set(run)
        assert pin_problems("states_pass/rr", run) == []
        # the pin test reads each batch's pair
        bad = {**run, "queue_prompts": {**run["queue_prompts"], "b1": {"rubric_version": 3, "prompt_sha256": "0" * 64}}}
        assert pin_problems("states_pass/rr", bad) == [("states_pass/rr", "states_queue", 3, "0" * 12)]


class TestRerouteQueueCalls:
    """A row waiting on a queue call (a reading not on record) is matched by the chunk that holds it (a queue call is
    keyed by its chunk, not by the row): it is listed with that call, the estimate counts it and the gloss calls that
    may follow, ``--send-missing`` runs only under a cap, and a row whose route does not change is not rewritten.
    Before 2026-10-13 such a row listed no call, the estimate was $0, the cost gate never ran and the calls were sent
    with no cap (a 3-reading batch with a failed reading: ``test_gapgen_states_pass_readings.py``)."""

    LABELS = ("crossish", "hopish", "passish", "plainheld", "renamish")

    def test_a_batch_under_another_queue_prompt(self, tmp_path, cli, capsys):
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        _under_another_queue_prompt(cand)
        before = {k: r["states_pass"] for k, r in Registry(reg).fold().items() if r.get("states_pass")}
        capsys.readouterr()
        assert _reroute(cli, reg, cand, "--dry-run") == 0
        out = capsys.readouterr().out
        # every row waits on its chunk's one queue call, then on at most a check and an alignment call
        for lb in self.LABELS:
            line = next(x for x in out.splitlines() if x.startswith(f"NEEDS     {lb} (b1): "))
            assert "once queue call(s) are made (not on record), then up to 2 gloss call(s)" in line
        assert "reroute: 0 changed, 0 unchanged, 5 need calls" in out
        assert "--send-missing would make 1 call(s) ({'queue': 1}), then up to 10 gloss call(s)" in out
        assert float(out.split("about $")[1].split()[0]) > 0
        assert _reroute(cli, reg, cand, "--send-missing", "--budget-usd", "0.5") == 0
        # the queue call, then the gloss calls the record lacks (hopish's; crossish's are on record)
        assert _steps(cli["live"][-1]) == {"queue": 1, "check": 1, "alignment": 1}
        run = _run_json(cand, "rr")
        assert run["estimate_usd"] > 0 and run["cap_usd"] == 0.5
        # only the rows whose route changed are written
        rows = Registry(reg).fold()
        assert {k for k in before if rows[k]["states_pass"] != before[k]} == {"crossish#1", "hopish#1"}
        assert rows["crossish#1"]["states_pass"]["route"] == "predisposition"
        assert rows["plainheld#1"]["states_pass"]["route_rules"] == 1
        res = {json.loads(x)["label"]: json.loads(x)["outcome"]
               for x in (cand / "states_pass" / "rr" / "results.jsonl").read_text().splitlines()}
        assert res == {"crossish": "changed_after_calls", "hopish": "changed_after_calls",
                       "passish": "unchanged_after_calls", "plainheld": "unchanged_after_calls",
                       "renamish": "unchanged_after_calls"}

    def test_send_missing_never_runs_uncapped(self, tmp_path, cli, monkeypatch):
        mod = cli["mod"]
        reg, cand = _batch_under_rules_1(tmp_path, cli)
        _under_another_queue_prompt(cand)
        budgets = []                     # every GuardedUsage the re-route makes, by its cap

        class Recording(mod.GuardedUsage):
            def __post_init__(self):
                budgets.append(self.budget_usd)
                super().__post_init__()
        monkeypatch.setattr(mod, "GuardedUsage", Recording)
        before, n_clients = reg.read_bytes(), len(cli["live"])
        # an estimate of $0 for rows that wait on calls is refused, not sent uncapped
        real_estimate = sp.StatesPassRunner.estimate_usd
        monkeypatch.setattr(sp.StatesPassRunner, "estimate_usd", lambda self, calls, **kw: 0.0)
        assert _reroute(cli, reg, cand, "--send-missing") == 2
        monkeypatch.setattr(sp.StatesPassRunner, "estimate_usd", real_estimate)
        # so is a gate that set no cap
        real_gate = mod.confirm_or_abort
        monkeypatch.setattr(mod, "confirm_or_abort", lambda *a, **k: None)
        assert _reroute(cli, reg, cand, "--send-missing") == 2
        assert len(cli["live"]) == n_clients and budgets == [] and reg.read_bytes() == before
        assert not (cand / "states_pass" / "rr").exists()
        # through the real gate the calls go out under the typed budget
        monkeypatch.setattr(mod, "confirm_or_abort", real_gate)
        assert _reroute(cli, reg, cand, "--send-missing", "--budget-usd", "0.25") == 0
        assert len(cli["live"]) == n_clients + 1 and budgets == [0.25]
