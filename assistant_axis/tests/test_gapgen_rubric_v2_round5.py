"""Rubric v2, round 5: the fixes of reports/trait_gap_generation/review_rubric_v2_fixes.md
(section 4, defects 1 to 7) and finding 11 of the earlier review (nowhere to
store Roger's judgement calls).  No prompt changes.  Written before the change;
each test failed against ecaf4b5 for the reason its name gives, unless its
docstring says otherwise."""
import json
import re
from pathlib import Path

import pytest

from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen.filter import FilterItem, FilterRunner
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, user_text
from assistant_axis.tests.test_gapgen_rubric_v2_round4 import _examples, crow, parse, vr

HAIKU = "claude-haiku-4-5-20251001"
REPO = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# 1. a row the validator refuses is asked again: repair instead of refusing
# ---------------------------------------------------------------------------

class TestValidatorRepairs:
    def test_null_judged_sense_falls_back_to_first_sense(self):
        rows, errs = parse(crow(1, "endless", verdict="tagged", tags=["evaluative_only"], judged_sense=None,
                                person_senses=[{"sense": "tiresomely long-winded", "kind": "trait"}]))
        assert errs == {}
        assert rows[1]["judged_sense"] == "tiresomely long-winded"
        assert rows[1]["validator_repairs"] == ["judged_sense_from_first_sense"]

    def test_null_judged_sense_with_no_senses_stays_null(self):
        rows, errs = parse(crow(1, "abominable", verdict="tagged", tags=["evaluative_only"], judged_sense=None,
                                person_senses=[]))
        assert errs == {}
        assert rows[1]["judged_sense"] is None
        assert rows[1]["validator_repairs"] == ["judged_sense_missing"]

    def test_unknown_sense_kind_is_dropped_and_the_row_kept(self):
        rows, errs = parse(crow(1, "clinical", person_senses=[{"sense": "coolly detached", "kind": "trait"},
                                                              {"sense": "of a clinic", "kind": "relational_only"}]))
        assert errs == {}
        assert rows[1]["person_senses"] == [{"sense": "coolly detached", "kind": "trait"}]
        assert rows[1]["validator_repairs"] == ["dropped_sense_kind:relational_only"]

    def test_clean_row_has_no_repairs(self):
        rows, _ = parse(crow(1, "a"))
        assert rows[1]["validator_repairs"] == []

    def test_reject_with_null_judged_sense_needs_no_repair(self):
        rows, errs = parse(crow(1, "b", verdict="reject", tags=["not_a_word"], region=None, gloss=None,
                                judged_sense=None, person_senses=[]))
        assert errs == {} and rows[1]["validator_repairs"] == []

    def test_dropping_the_only_trait_sense_still_fails_a_trait_row(self):
        _, errs = parse(crow(1, "a", person_senses=[{"sense": "x", "kind": "mood"}]))
        assert "trait sense" in errs[1]

    def test_repairs_reach_the_filter_block_and_the_summary(self):
        from assistant_axis.gapgen.filter import summarize
        from assistant_axis.judge_pricing import MultiModelUsage

        def resp(kw):
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            return json.dumps({"results": [crow(it["id"], it["label"], judged_sense=None,
                                                person_senses=[{"sense": "s", "kind": "trait"},
                                                               {"sense": "o", "kind": "mood"}])
                                           for it in items]})
        r = FilterRunner(client=FakeAsyncAnthropic(resp), batch_id="b", model=HAIKU, second_model=None,
                         second_opinion=False, probe=False, plain_reading=False, zipf_fn=lambda w: 4.0,
                         wordnet=False)
        out = r.run([FilterItem(key="w1#1", label="w1"), FilterItem(key="w2#1", label="w2")])
        assert r.stats["n_llm_ok_first_pass"] == 2
        assert out[0].filter["validator_repairs"] == ["dropped_sense_kind:mood", "judged_sense_from_first_sense"]
        s = summarize(out, stats=r.stats, usage=MultiModelUsage())
        assert s["v2_fields"]["validator_repairs"] == {"dropped_sense_kind:mood": 2,
                                                       "judged_sense_from_first_sense": 2}


# ---------------------------------------------------------------------------
# 2. measurement runs; the stability mode; agreement without floor rows
# ---------------------------------------------------------------------------

class TestMeasurementRuns:
    def test_development_seen_skips_measurement_runs(self, tmp_path):
        from assistant_axis.gapgen.filter import development_seen
        for run, meas in (("m1_pilot", False), ("m1_validation", True)):
            d = tmp_path / "filter" / run
            d.mkdir(parents=True)
            (d / "results.jsonl").write_text(json.dumps({"key": "vain#1", "label": "vain"}) + "\n")
            (d / "run.json").write_text(json.dumps({"batch_id": run, "measurement": meas}))
        assert development_seen(tmp_path) == {"vain#1": ["filter/m1_pilot"]}

    def test_cli_records_measurement_in_run_json(self, tmp_path, monkeypatch):
        _patch_cli(monkeypatch)
        from data_analysis.gap_generation import traithood_filter
        val = tmp_path / "v.jsonl"
        val.write_text(json.dumps({"surface": "stubborn", "stratum": "existing"}) + "\n")
        cand = tmp_path / "cand"
        assert traithood_filter.main(["--pipeline", "single", "--batch-id", "m", "--validation-file", str(val), "--out-root", str(cand),
                                      "--no-second-opinion", "--no-probe", "--measurement"]) == 0
        assert json.loads((cand / "filter" / "m" / "run.json").read_text())["measurement"] is True

    def test_corpus_comparison_is_a_measurement(self, tmp_path, monkeypatch):
        """Written after the traithood_filter change, before the plain_reading one;
        failed first (run.json had no "measurement")."""
        import anthropic
        import dotenv

        from assistant_axis.tests.test_gapgen_rubric_v2_round4 import _cmp_resp
        from data_analysis.gap_generation import plain_reading as cli
        monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **kw: FakeAsyncAnthropic(_cmp_resp))
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc")
        monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
        d = tmp_path / "data" / "traits" / "instructions"
        d.mkdir(parents=True)
        (d / "calm.json").write_text(json.dumps({"positive_label": "calm", "description": "This means calm."}))
        cand = tmp_path / "cand"
        assert cli.main(["--batch-id", "c", "--corpus", "--data-dir", str(tmp_path / "data"),
                         "--out-root", str(cand)]) == 0
        assert json.loads((cand / "plain_reading" / "c" / "run.json").read_text())["measurement"] is True
        from assistant_axis.gapgen.filter import development_seen
        assert development_seen(cand) == {}

    def test_stability_mode_sets_the_documented_sample(self):
        from data_analysis.gap_generation import traithood_filter as tf
        args = tf.build_parser().parse_args(["--batch-id", "m1_stability", "--validation-file", "v.jsonl",
                                             "--stability"])
        tf.apply_stability(args)
        assert (args.sample_frac, args.sample_seed, args.shuffle_seed, args.measurement) == (0.13, 1, 1, True)
        assert tf.STABILITY_MIN_LLM_ROWS == 200

    def test_stability_mode_refuses_other_sample_flags(self):
        from data_analysis.gap_generation import traithood_filter as tf
        args = tf.build_parser().parse_args(["--batch-id", "s", "--validation-file", "v.jsonl", "--stability",
                                             "--sample-frac", "0.5"])
        with pytest.raises(SystemExit):
            tf.apply_stability(args)

    def test_stability_mode_on_the_real_validation_file_reaches_200_model_rows(self):
        """The reviewer's figure: 241 rows, 210 to the model (no API call)."""
        from assistant_axis.gapgen import paths
        from data_analysis.gap_generation import traithood_filter as tf
        val = paths.VALIDATION_DIR / "m1_validation.jsonl"
        args = tf.build_parser().parse_args(["--pipeline", "single", "--batch-id", "m1_stability",
                                             "--validation-file", str(val),
                                             "--stability", "--out-root", "/nonexistent-candidates"])
        tf.apply_stability(args)
        items, _ = tf.select_items(args)
        _, plan = tf.build_estimate(items, args)
        assert plan["n_rows"] == 241 and plan["n_llm"] == 210


class TestStabilityAgreement:
    def test_floor_rows_left_out(self):
        from assistant_axis.gapgen.filter import stability_agreement

        def row(k, verdict, stage="classified"):
            return {"key": k, "stage": stage, "filter": {"verdict": verdict}}
        full = [row("a#1", "trait"), row("b#1", "reject", "hard_reject"), row("c#1", "trait"),
                row("d#1", "tagged"), row("e#1", "trait")]
        rerun = [row("a#1", "trait"), row("b#1", "reject", "hard_reject"), row("c#1", "reject"),
                 row("d#1", "tagged"), row("x#1", "trait")]
        a = stability_agreement(full, rerun)
        assert a["n"] == 3 and a["agree"] == 2 and a["share"] == pytest.approx(2 / 3, abs=1e-4)
        assert a["n_floor_excluded"] == 1 and a["disagreements"] == [("c#1", "trait", "reject")]

    def test_a_run_json_without_the_field_is_not_a_measurement(self, tmp_path):
        from assistant_axis.gapgen.filter import is_measurement_run
        (tmp_path / "run.json").write_text(json.dumps({"batch_id": "x"}))
        assert is_measurement_run(tmp_path) is False and is_measurement_run(tmp_path / "none") is False

    def test_acceptance_test_uses_it(self):
        src = (TESTS / "test_gapgen_acceptance.py").read_text(encoding="utf-8")
        assert "stability_agreement(" in src


# ---------------------------------------------------------------------------
# 3, 7. assertions behind comments; stale text
# ---------------------------------------------------------------------------

def test_no_assertion_hidden_behind_a_comment():
    src = (TESTS / "test_gapgen_filter.py").read_text(encoding="utf-8")
    assert not re.search(r"\s# [^\n]*\band f\[", src)  # a comment, not the # of a key such as "stubborn#1"


def test_filter_rubric_docstring_names_the_current_version():
    # version 4 in round 5; 6 since 2026-10-02 (merge with the main line)
    first = fr.__doc__.split("\n")[0]
    assert f"classifier prompt version {fr.TRAITHOOD_RUBRIC_VERSION}" in first and "version 3)" not in first


def test_plain_reading_docstring_says_related_raises_a_note():
    from assistant_axis.gapgen import plain_reading as pr
    doc = " ".join(pr.__doc__.split())
    assert "without the flag" not in doc and "reading_related" in doc


def test_no_retired_sense_kind_in_the_truth_table():
    src = (TESTS / "test_gapgen_filter_rubric.py").read_text(encoding="utf-8")
    assert '"bodily"' not in src


def test_an_empty_figure_has_no_verdict_on_its_target():
    from assistant_axis.gapgen.filter import validation_figures
    f = validation_figures([vr("a", "existing", seen=["filter/m1_pilot"]), vr("b", "rejects", seen=["x"]),
                            vr("o", "oewn_random", "reject", ["relational_only"], seen=["x"])])
    u = f["unseen"]
    assert u["existing"]["n"] == 0 and u["existing"]["meets_target"] is None
    assert u["rejects"]["meets_target"] is None and u["oewn_random"]["meets_target"] is None
    assert f["existing"]["meets_target"] is True and f["oewn_random"]["meets_target"] is True


# ---------------------------------------------------------------------------
# 4, 11. the judgement-call table: obvious_sense_not_trait first; Roger's calls
# ---------------------------------------------------------------------------

def _registry_with_calls(tmp_path):
    from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
    reg = tmp_path / "r.jsonl"
    submit_candidates([Candidate(surface=w, generator="g", run_id="r") for w in ("soft", "noble", "stubborn")],
                      registry_path=reg)
    Registry(reg).update("soft#1", {"filter": {"verdict": "trait", "tags": [],
                                               "polysemy_notes": ["nontrait_person_sense"],
                                               "person_senses": [{"sense": "gentle and lenient", "kind": "trait"},
                                                                 {"sense": "physically soft", "kind": "physical"}]}})
    Registry(reg).update("noble#1", {"filter": {"verdict": "trait", "tags": [],
                                                "polysemy_notes": ["obvious_sense_not_trait"],
                                                "person_senses": [{"sense": "high-born", "kind": "role"},
                                                                  {"sense": "high-minded", "kind": "trait"}]}})
    Registry(reg).update("stubborn#1", {"filter": {"verdict": "trait", "tags": [], "polysemy_notes": []}})
    return reg


class TestJudgementCalls:
    def test_obvious_sense_not_trait_listed_first(self, tmp_path, capsys):
        from data_analysis.gap_generation import gap_registry
        reg = _registry_with_calls(tmp_path)
        calls = tmp_path / "calls.json"
        assert gap_registry.main(["--registry", str(reg), "judgement-calls", "--calls-file", str(calls)]) == 0
        out = capsys.readouterr().out
        assert "| word | key | note | trait sense | other sense | Roger's call |" in out
        noble = "| noble | noble#1 | obvious_sense_not_trait | high-minded | high-born (role) |  |"
        soft = "| soft | soft#1 | nontrait_person_sense | gentle and lenient | physically soft (physical) |  |"
        assert noble in out and soft in out and out.index(noble) < out.index(soft)
        assert "stubborn" not in out

    def test_a_recorded_call_shows_in_the_last_column(self, tmp_path, capsys):
        from data_analysis.gap_generation import gap_registry
        reg = _registry_with_calls(tmp_path)
        calls = tmp_path / "calls.json"
        assert gap_registry.main(["judgement-call", "--calls-file", str(calls), "--word", "soft",
                                  "--call", "keep: the trait reading wins"]) == 0
        obj = json.loads(calls.read_text())
        assert obj["calls"]["soft"]["call"] == "keep: the trait reading wins" and obj["calls"]["soft"]["at"]
        capsys.readouterr()
        assert gap_registry.main(["--registry", str(reg), "judgement-calls", "--calls-file", str(calls)]) == 0
        out = capsys.readouterr().out
        assert ("| soft | soft#1 | nontrait_person_sense | gentle and lenient | physically soft (physical) "
                "| keep: the trait reading wins |") in out

    def test_the_tracked_calls_file_exists_and_is_empty_or_keyed_by_word(self):
        from assistant_axis.gapgen import paths
        obj = json.loads(paths.JUDGEMENT_CALLS_PATH.read_text(encoding="utf-8"))
        assert isinstance(obj["calls"], dict)
        assert all(set(v) >= {"call", "at"} for v in obj["calls"].values())


# ---------------------------------------------------------------------------
# 5. an allowlisted prose word is never part of an example, senses included
# ---------------------------------------------------------------------------

#: Allowlisted words that occur inside an example's senses (review_rubric_v2_fixes.md
#: defect 5): known, left as they stand until the v5 prompt.
KNOWN_IN_EXAMPLE_SENSES = {"elected", "general"}


def allowlisted_in_examples(rows) -> dict[str, set[str]]:
    """label -> allowlisted words found in its person senses or judged sense."""
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
    out = {}
    for row in rows:
        text = " ".join([s["sense"] for s in row["person_senses"]] + [row.get("judged_sense") or ""])
        hits = prompt_words(text) & PROSE_ALLOWED
        if hits:
            out[row["label"]] = hits
    return out


def test_allowlist_check_reads_senses():
    rows = [{"label": "x", "person_senses": [{"sense": "a married person", "kind": "role"}],
             "judged_sense": "stable in mood"}]
    assert allowlisted_in_examples(rows) == {"x": {"married", "stable"}}


def test_no_allowlisted_word_in_an_example_sense_beyond_the_known_two():
    found = set().union(*allowlisted_in_examples(_examples()).values())
    assert found <= KNOWN_IN_EXAMPLE_SENSES, found - KNOWN_IN_EXAMPLE_SENSES


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _patch_cli(monkeypatch):
    import anthropic
    import dotenv

    from data_analysis.gap_generation import traithood_filter

    def resp(kw):
        items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
        return json.dumps({"results": [crow(it["id"], it["label"]) for it in items]})
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **kw: FakeAsyncAnthropic(resp))
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc")
    monkeypatch.setattr(traithood_filter, "platform_dirty_files", lambda *a, **k: [])
