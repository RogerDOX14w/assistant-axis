"""The split filter's pure functions (coding_plan_split.md section 8, tests 2, 5 and part of 9): the
parsers, the join on the recorded answers, the mapping onto the frozen vocabulary and its readers,
the pricing of the second model and of batches, and requests without ``temperature``."""
import json

import pytest

from assistant_axis.gapgen import split
from assistant_axis.gapgen.llm import accepts_temperature, request_params
from assistant_axis.judge_pricing import BATCH_SUFFIX, MultiModelUsage, price_for_model
from assistant_axis.tests.split_replay import HAIKU, SONNET55, load_jsonl


def one(**row):
    return json.dumps({"results": [{"id": 1, **row}]})


# ---------------------------------------------------------------------------
# parsers
# ---------------------------------------------------------------------------

class TestParsers:
    def test_sense_valid_and_label_echo(self):
        t = one(label="Danish", note="n", first_thought="from Denmark", first_thought_said_of="people",
                readings=[{"reading": "you are from Denmark", "rank": "primary"}], usable=True)
        row, err = split.parse_sense("```json\n" + t + "\n```", "Danish")
        assert err is None and row["readings"] == [{"reading": "you are from Denmark", "rank": "primary"}]
        assert split.parse_sense(t, "Swedish")[1].startswith("label echo")

    def test_sense_empty_readings_allowed(self):
        t = one(label="octal", note="n", first_thought="f", first_thought_said_of="things", readings=[], usable=False)
        assert split.parse_sense(t, "octal")[0]["readings"] == []

    @pytest.mark.parametrize("bad,msg", [
        ({"first_thought_said_of": "persons"}, "first_thought_said_of"),
        ({"usable": "maybe"}, "usable"),
        ({"readings": [{"reading": "x", "rank": "main"}]}, "rank"),
        ({"readings": "x"}, "readings is not a list"),
    ])
    def test_sense_invalid(self, bad, msg):
        row = dict(label="w", note="n", first_thought="f", first_thought_said_of="people", readings=[], usable=True)
        row.update(bad)
        assert msg in split.parse_sense(one(**row), "w")[1]

    def test_checks(self):
        assert split.parse_established(one(reason="r", established="known", first_thought_in_the_way=False))[0]
        assert "established" in split.parse_established(one(reason="r", established="rare",
                                                             first_thought_in_the_way=False))[1]
        v = split.parse_vague(one(reason="r", leaves_something_out=True, missing="to what",
                                  fits_many_in_different_ways=False))[0]
        assert v["missing"] == "to what"
        assert split.parse_vague(one(reason="r", leaves_something_out=False))[1]

    def test_kind_membership_kinds(self):
        assert split.parse_kind(one(reason="r", kind="membership", membership_kind="religion"))[0]
        assert split.parse_kind(one(reason="r", kind="membership", membership_kind=None))[1]
        row = split.parse_kind(one(reason="r", kind="trait", membership_kind="class"))[0]
        assert row["membership_kind"] is None
        assert split.parse_kind(one(reason="r", kind="praise"))[1]

    def test_last_step(self):
        g = split.parse_gloss(one(gloss="This means keeping to oneself."))[0]
        assert g["form_ok"] is True
        assert split.parse_gloss(one(gloss="This means you keep to yourself."))[0]["form_ok"] is False
        assert split.parse_descriptors(one(reason="r", region="physical", enactable_in_text=1))[1]
        assert split.parse_descriptors(one(reason="r", region="moral_stance", enactable_in_text=3))[1]
        assert split.parse_same_sense(one(reason="r", relation="shade"))[0]["relation"] == "shade"

    @pytest.mark.parametrize("score", [0, 1, 2, 3])
    def test_alignment_score(self, score):
        row, err = split.parse_alignment(one(reason="r", alignment=score))
        assert err is None and row == {"reason": "r", "alignment": score}

    @pytest.mark.parametrize("bad", [4, -1, 2.5, "2", True, False, None])
    def test_alignment_anything_else_fails(self, bad):
        assert "alignment" in split.parse_alignment(one(reason="r", alignment=bad))[1]

    def test_alignment_old_shape_fails(self):
        """draft 1 and 2's boolean is no longer an answer (it would be retried once)."""
        assert split.parse_alignment(one(reason="r", alignment_relevant=True))[1]
        assert split.parse_alignment(one(alignment=2))[1] == "reason missing"

    def test_unparseable_and_wrong_id(self):
        assert split.parse_kind("no json")[1].startswith("unparseable")
        assert split.parse_kind(json.dumps({"results": [{"id": 2, "reason": "r", "kind": "trait"}]}))[1]

    def test_recorded_answers_all_parse(self):
        for r in load_jsonl("recorded_answers.jsonl"):
            row, err = split.parse(r["step"], r["raw"], label=r["sent"]["label"])
            assert err is None, (r["step"], r["sent"], err)


# ---------------------------------------------------------------------------
# 2. the join, on the recorded answers
# ---------------------------------------------------------------------------

class TestJoin:
    def test_join_reproduces_the_reference_for_all_99_words(self):
        rows = load_jsonl("steps_1_to_3_results.jsonl")
        same = {d["word"]: d["relation"] for d in load_jsonl("same_sense_results.jsonl")}
        exp = {d["word"]: d for d in load_jsonl("expected_outcomes.jsonl")}
        assert len(rows) == 99 and set(exp) == {r["word"] for r in rows}
        outcomes = {}
        for r in rows:
            j = split.join(r["sense"], same.get(r["word"]))
            e = exp[r["word"]]
            outcomes[r["word"]] = j
            for k in ("outcome", "accepted", "notes", "cause", "kind", "same_sense", "membership_kind"):
                if k in e:
                    assert j[k] == e[k], (r["word"], k)
        counts = {o: sum(1 for j in outcomes.values() if j["outcome"] == o) for o in split.OUTCOMES}
        assert counts == {"trait": 74, "states": 7, "physical": 2, "roles": 0, "turned_away": 16}
        assert sum("two_trait_senses" in j["notes"] for j in outcomes.values()) == 7
        # seven accepted readings have no vague answer on record (so no vague note either way)
        assert sum(1 for j in outcomes.values() if j["accepted"] and not j["vague_asked"]) == 7

    def test_rules(self):
        def rd(text, kind, est="well_known", rank="primary"):
            return {"reading": text, "rank": rank, "check_established": {"established": est},
                    "kind_call": {"kind": kind, "membership_kind": "class" if kind == "membership" else None}}
        assert split.join({"readings": []})["cause"] == "no_reading"
        assert split.join({"readings": [rd("a", "trait", rank="secondary")]})["rule"] == 1
        assert split.join({"readings": [rd("a", "trait", est="stretched")]})["cause"] == "stretched"
        j = split.join({"readings": [rd("a", "state"), rd("b", "membership")]})
        assert j["outcome"] == "trait" and j["accepted"] == "b" and j["rule"] == 4
        assert "obvious_sense_not_trait" in j["notes"] and j["membership_kind"] == "class"
        j = split.join({"readings": [rd("a", "trait", est="stretched"), rd("b", "role")]})
        assert j["outcome"] == "roles" and j["notes"] == ["most_likely_reading_stretched"]
        j = split.join({"readings": [rd("a", "action"), rd("b", "state")]})
        assert j["outcome"] == "turned_away" and j["cause"] == "action"
        j = split.join({"readings": [rd("a", "trait"), rd("b", "state")]})
        assert j["notes"] == ["nontrait_person_sense"]


# ---------------------------------------------------------------------------
# 5. the frozen vocabulary and its readers
# ---------------------------------------------------------------------------

def _block(outcome, *, cause=None, mk=None, score=0):
    kind = {"trait": "membership" if mk else "trait", "states": "state", "physical": "physical",
            "roles": "role"}.get(outcome, cause or "action")
    sense = {"note": "n", "first_thought": "f", "first_thought_said_of": "people", "usable": True,
             "readings": [{"reading": "you are like this", "rank": "primary",
                           "check_established": {"reason": "r", "established": "well_known",
                                                 "first_thought_in_the_way": False},
                           "kind_call": {"reason": "A standing way.", "kind": kind, "membership_kind": mk}}]}
    j = split.join(sense)
    return split.to_filter_block(sense=sense, j=j, model=HAIKU, batch_id="b", now="t",
                                 step_versions={"sense": 6}, prompt_sha256={"sense": "x"},
                                 gloss_model=HAIKU, alignment={"reason": "r", "alignment": score},
                                 descriptors={"reason": "r", "region": "social_interpersonal", "enactable_in_text": 2},
                                 gloss="This means being like this.")


class TestVocabulary:
    @pytest.mark.parametrize("outcome,mk,verdict,tags,holding,et", [
        ("trait", None, "trait", [], None, "trait"),
        ("trait", "class", "trait", ["membership"], None, "trait"),
        ("trait", "nationality_ethnicity_language", "trait", ["membership"], "nationalities", "trait"),
        ("states", None, "tagged", ["state"], "states", "trait"),
        ("physical", None, "tagged", ["physical"], "physical", "trait"),
        ("roles", None, "tagged", ["role_person"], "roles", "role"),
    ])
    def test_table(self, outcome, mk, verdict, tags, holding, et):
        block, gloss, hold, ent = _block(outcome, mk=mk)
        assert (block["verdict"], block["tags"], hold, ent) == (verdict, tags, holding, et)
        assert (gloss is not None) == (outcome == "trait")
        assert block["judged_sense"] == "you are like this" and block["trait_sense_rank"] == 1

    @pytest.mark.parametrize("cause,tag", [("action", "action"), ("evaluative", "evaluative_only"),
                                           ("not_a_persona", "no_persona_reading")])
    def test_turned_away_tags(self, cause, tag):
        block, gloss, hold, _ = _block("turned_away", cause=cause)
        assert block["verdict"] == "reject" and block["tags"] == [tag] and hold is None and gloss is None
        assert split.verdict_tags_holding("turned_away", cause="no_reading")[1] == ["no_persona_reading"]
        assert split.verdict_tags_holding("turned_away", cause="stretched")[1] == ["stretched"]

    @pytest.mark.parametrize("score,relevant", [(0, False), (1, False), (2, True), (3, True)])
    def test_alignment_score_and_the_boolean_derived_from_it(self, score, relevant):
        block, *_ = _block("trait", score=score)
        assert block["alignment"] == score and block["alignment_relevant"] is relevant
        assert split.alignment_relevant_of(score) is relevant

    @pytest.mark.parametrize("outcome", ["states", "physical", "roles", "turned_away"])
    def test_alignment_keys_null_off_the_trait_path(self, outcome):
        block, *_ = _block(outcome, score=3)
        assert block["alignment"] is None and block["alignment_relevant"] is None

    def test_a_failed_alignment_call_leaves_both_keys_null(self):
        sense = {"note": "n", "first_thought": "f", "first_thought_said_of": "people", "usable": True,
                 "readings": [{"reading": "r", "rank": "primary", "check_established": {"established": "known"},
                               "kind_call": {"kind": "trait", "membership_kind": None}}]}
        block, *_ = split.to_filter_block(sense=sense, j=split.join(sense), model=HAIKU, batch_id="b", now="t",
                                          step_versions={}, prompt_sha256={}, gloss="This means being r.",
                                          alignment=None)
        assert block["alignment"] is None and block["alignment_relevant"] is None

    def test_readers_work_on_split_rows(self, tmp_path, capsys):
        from assistant_axis.gapgen import states_pass as sp
        from assistant_axis.gapgen.promote import queue_entry_from_record
        from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
        from data_analysis.gap_generation import gap_registry
        reg = tmp_path / "registry.jsonl"
        submit_candidates([Candidate(surface=s, generator="g", run_id="r") for s in ("zorpish", "blurfed")],
                          registry_path=reg)
        tb, tg, th, te = _block("trait")
        sb, sg, sh, se = _block("states")
        Registry(reg).update_many({
            "zorpish#1": {"filter": tb, "gloss": tg, "holding": th, "entity_type": te},
            "blurfed#1": {"filter": sb, "gloss": sg, "holding": sh, "entity_type": se}})
        rows = Registry(reg).fold()
        entry = queue_entry_from_record(rows["zorpish#1"])
        assert entry["description_draft"] == "This means being like this." and entry["gap_gen"]["rubric_version"] == 5
        assert gap_registry.main(["--registry", str(reg), "report"]) == 0
        out = capsys.readouterr().out
        assert "| zorpish#1 | zorpish | trait |" in out and "blurfed" not in out
        assert gap_registry.main(["--registry", str(reg), "holding", "--list", "states"]) == 0
        assert "- **blurfed** (state" in capsys.readouterr().out
        # the states pass reads the accepted reading when a split row has no gloss
        items = sp.items_from_registry(list(rows.values()))
        assert [(i.key, i.text) for i in items] == [("blurfed#1", "you are like this")]
        res_rows = [{"key": "blurfed#1", "label": "blurfed", "filter": sb, "gloss": None, "meta": {}}]
        assert sp.items_from_filter_results(res_rows)[0].text == "you are like this"


# ---------------------------------------------------------------------------
# 9 (part): pricing and requests
# ---------------------------------------------------------------------------

class TestPricingAndRequests:
    def test_sonnet_55_rates_and_older_sonnets_unchanged(self):
        assert price_for_model(SONNET55) == (2.0, 10.0)
        assert price_for_model("claude-sonnet-5") == (2.0, 10.0)
        assert price_for_model("claude-sonnet-4-6") == (3.0, 15.0)
        assert price_for_model("claude-sonnet-4-5") == (3.0, 15.0)

    def test_batch_suffix_is_half_rate(self):
        assert price_for_model(HAIKU + BATCH_SUFFIX) == (0.5, 2.5)
        assert price_for_model(SONNET55 + BATCH_SUFFIX) == (1.0, 5.0)
        u = MultiModelUsage()
        u.charge(HAIKU + BATCH_SUFFIX, 1_000_000, 1_000_000)
        assert u.total_cost_usd == pytest.approx(3.0)
        with pytest.raises(KeyError):
            price_for_model("mystery" + BATCH_SUFFIX)

    def test_requests_leave_out_temperature_for_models_that_refuse_it(self):
        assert accepts_temperature(HAIKU) and not accepts_temperature(SONNET55)
        p = request_params(model=SONNET55, system="s", user="u", max_tokens=2000, temperature=0.0,
                           cache_system=False)
        assert "temperature" not in p and "thinking" not in p and "output_config" not in p
        assert p["system"] == [{"type": "text", "text": "s"}]
        p = request_params(model=HAIKU, system="s", user="u", max_tokens=10, temperature=0.0)
        assert p["temperature"] == 0.0 and p["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert "temperature" not in request_params(model=HAIKU, system=None, user="u", max_tokens=1,
                                                   temperature=None)

    def test_pilot_figures(self):
        rows = [{"label": "a", "filter": {"outcome": "trait", "judged_sense": "x", "rule": 3}, "gloss": "This means being."},
                {"label": "b", "filter": {"outcome": "states", "judged_sense": "y", "rule": 5}},
                {"label": "c", "filter": {"outcome": "turned_away", "rule": "probe", "reason": "r"}}]
        fig = split.pilot_figures(rows, {"a": {"outcome": "trait"}, "b": {"outcome": "trait", "accepted": "z"}})
        assert fig["n_reached_step1"] == 2 and fig["same_outcome_as_expected"] == 1
        assert fig["differences"][0]["label"] == "b" and fig["cut_before_step1"][0]["rule"] == "probe"
        assert fig["glosses_form_ok"] == 1
