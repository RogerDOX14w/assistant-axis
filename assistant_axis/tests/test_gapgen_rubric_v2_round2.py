"""Rubric v2, round 2: open points A, B and C of
reports/trait_gap_generation/decisions_m1.md (Roger's answers of 2026-09-29),
the probe's handling of derived words, and promotion from the states list.
Item numbers are the coordinator's round-2 list.  Written before the change;
each test failed against cefd714 for the reason its name gives."""
import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen.cost import CostRefused, confirm_or_abort
from assistant_axis.gapgen.filter import FilterItem, FilterRunner, holding_for
from assistant_axis.gapgen.normalize import HOLDING
from assistant_axis.gapgen.registry import Candidate, Registry, holding_list, new_record, submit_candidates
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

HAIKU = "claude-haiku-4-5-20251001"
REPO = Path(__file__).resolve().parents[2]
ROUND1_CLASSIFIER_SHA = "2b5b298ed6b44745eae5358325cfaea93324b8e7ac90a2cb691dd12440d2fedb"
ROUND1_PROBE_SHA = "0785cd073e2cd2b62f412b379e003cdc39fdf54f360a99dc517dd2621add0103"
NAT = "nationality_ethnicity_language"

APPENDIX = {"dynamic", "colorful", "deep", "polished", "warm", "dull", "volatile", "stiff", "toxic", "clinical",
            "graphic", "portable", "bossy", "fickle", "smug", "nosy", "wily", "cheeky", "pushy", "garrulous",
            "magnetic", "dense", "sharp", "cold", "bright", "abrasive", "shallow", "slick", "brittle",
            "mechanical", "linear", "organic", "gullible", "shrewd", "haughty", "coy", "petulant", "headstrong",
            "snobbish", "taciturn"}
SIX = {"disciplinary", "engaging", "economic", "balanced", "empowered", "emotive"}


def crow(i, label, **kw):
    base = {"id": i, "label": label, "reason": "Said of how someone habitually behaves in conversation.",
            "person_senses": [{"sense": label, "kind": "trait"}], "trait_senses_equally_obvious": False, "enactable_in_text": 2, "verdict": "trait",
            "tags": [], "membership_kind": None, "region": "social_interpersonal", "alignment_relevant": False,
            "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# 1. the budget (point A, decision 9)
# ---------------------------------------------------------------------------

class TestBudgetPointA:
    def test_estimate_over_typed_budget_refused_even_with_the_flag(self):
        with pytest.raises(CostRefused) as ei:
            confirm_or_abort(6.0, 5.0, confirm_expensive=True)
        assert "larger --budget-usd" in str(ei.value)

    def test_no_flag_raises_the_cap_below_the_line(self):
        for est in (5.01, 13.34, 19.9):
            with pytest.raises(CostRefused):
                confirm_or_abort(est, 5.0, confirm_expensive=True)

    def test_typed_budget_is_the_cap(self):
        assert confirm_or_abort(4.0, 5.0, confirm_expensive=False) == 5.0
        assert confirm_or_abort(4.0, 5.0, confirm_expensive=True) == 5.0

    def test_over_the_line_needs_the_flag_and_the_confirmer(self):
        with pytest.raises(CostRefused):  # confirmer alone is not enough any more
            confirm_or_abort(1.0, 30.0, confirm_expensive=False, confirmed_by="Roger 2026-09-29")
        with pytest.raises(CostRefused):
            confirm_or_abort(1.0, 30.0, confirm_expensive=True)
        assert confirm_or_abort(25.0, 30.0, confirm_expensive=True, confirmed_by="Roger 2026-09-29") == 30.0

    def test_over_the_line_estimate_still_capped_by_typed_budget(self):
        with pytest.raises(CostRefused):
            confirm_or_abort(25.0, 5.0, confirm_expensive=True, confirmed_by="Roger")

    def test_signature_unchanged(self):
        params = inspect.signature(confirm_or_abort).parameters
        assert list(params) == ["estimate_usd", "budget_usd", "confirm_expensive", "hard_line", "confirmed_by"]

    def test_cli_help_text(self):
        from data_analysis.gap_generation import traithood_filter
        h = " ".join(traithood_filter.build_parser().format_help().split())
        assert "an estimate over it is refused" in h
        assert "only with --confirmed-by" in h


# ---------------------------------------------------------------------------
# 2. nationality-type memberships (point B, decision 3)
# ---------------------------------------------------------------------------

class TestNationalityList:
    def test_holding_for_nationality_kind(self):
        assert "nationalities" in HOLDING
        assert holding_for("trait", ["membership"], NAT) == ("nationalities", "trait")
        assert holding_for("trait", ["membership"], "family") == (None, "trait")
        assert holding_for("trait", ["membership"]) == (None, "trait")

    def test_runner_routes_nationality_to_its_list(self):
        def responder(kw):
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            spec = {"Norwegian": {"tags": ["membership"], "membership_kind": NAT},
                    "stepchild": {"tags": ["membership"], "membership_kind": "family"}}
            return json.dumps({"results": [crow(it["id"], it["label"], **spec.get(it["label"], {}))
                                           for it in items]})
        r = FilterRunner(client=FakeAsyncAnthropic(responder), batch_id="b", model=HAIKU, second_model=None,
                         second_opinion=False, probe=False, zipf_fn=lambda w: 4.0, wordnet=False)
        out = {x.label: x for x in r.run([FilterItem(key="norwegian#1", label="Norwegian"),
                                          FilterItem(key="stepchild#1", label="stepchild")])}
        assert out["Norwegian"].holding == "nationalities" and out["Norwegian"].filter["verdict"] == "trait"
        assert out["stepchild"].holding is None

    def test_holding_list_and_cli(self, tmp_path, capsys):
        from data_analysis.gap_generation import gap_registry
        reg = tmp_path / "r.jsonl"
        submit_candidates([Candidate(surface="Norwegian", generator="g", run_id="r")], registry_path=reg)
        Registry(reg).update("norwegian#1", {"holding": "nationalities", "gloss": "This means being from Norway.",
                                             "filter": {"verdict": "trait", "tags": ["membership"],
                                                        "membership_kind": NAT}})
        assert [r["key"] for r in holding_list("nationalities", registry=Registry(reg))] == ["norwegian#1"]
        assert gap_registry.main(["--registry", str(reg), "holding", "--list", "nationalities"]) == 0
        assert "- **Norwegian**" in capsys.readouterr().out

    def test_report_keeps_held_rows_off_the_main_list(self, tmp_path, capsys):
        from data_analysis.gap_generation import gap_registry
        reg = tmp_path / "r.jsonl"
        submit_candidates([Candidate(surface=s, generator="g", run_id="r") for s in ("Norwegian", "stubborn")],
                          registry_path=reg)
        Registry(reg).update("norwegian#1", {"holding": "nationalities",
                                             "filter": {"verdict": "trait", "tags": ["membership"]}})
        Registry(reg).update("stubborn#1", {"filter": {"verdict": "trait", "tags": []}})
        assert gap_registry.main(["--registry", str(reg), "report"]) == 0
        out = capsys.readouterr().out
        assert "stubborn#1" in out and "norwegian#1" not in out
        assert gap_registry.main(["--registry", str(reg), "report", "--include-held"]) == 0
        assert "norwegian#1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# 3a. transient_only folds into state (point C)
# ---------------------------------------------------------------------------

class TestStateFold:
    def test_classifier_no_longer_emits_transient_only(self):
        assert "transient_only" not in fr.CLASSIFIER_TAGS
        assert "transient_only" not in fr.SYSTEM_PROMPT

    def test_prompt_leaves_plausibility_to_the_separate_pass(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "is not decided here" in sp
        ex = sp[sp.index('"hungry"'):]
        assert ex.index("tags [state]") < ex.index('"awesome"')

    def test_validator_folds_a_stray_transient_only(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [
            crow(1, "a", verdict="tagged", tags=["transient_only"], region="transient_state")]}), [1],
            labels={1: "a"})
        assert errs == {} and rows[1]["tags"] == ["state"]

    def test_v1_transient_only_routes_to_states(self):
        assert holding_for("tagged", ["transient_only"]) == ("states", "trait")


# ---------------------------------------------------------------------------
# 3b, 3c. the separate states pass and its corpus check
# ---------------------------------------------------------------------------

def sp_mod():
    from assistant_axis.gapgen import states_pass
    return states_pass


def qrow(i, label, **kw):
    base = {"id": i, "label": label, "reason": "Some people are prone to this again and again.",
            "plausible": True, "name_fits": True, "suggested_name": None,
            "gloss": "This means " + "falling into it " * 7 + "often.", "confidence": 0.8}
    base.update(kw)
    return base


def crow_corpus(i, label, **kw):
    base = {"id": i, "label": label, "reason": "Written as a standing habit.", "reading": "predisposition",
            "confidence": 0.9}
    base.update(kw)
    return base


class TestStatesPassRubric:
    def test_versions_and_hashes(self):
        s = sp_mod()
        assert s.RUBRIC_VERSIONS == {"queue": 2, "corpus": 1}  # round 3: one version per prompt
        assert s.PROMPT_SHA256 == {"queue": hashlib.sha256(s.QUEUE_PROMPT.encode()).hexdigest(),
                                   "corpus": hashlib.sha256(s.CORPUS_PROMPT.encode()).hexdigest()}

    def test_docstring_keeps_rogers_reason(self):
        assert "a rubric that's doing a lot of other things as well" in " ".join(sp_mod().__doc__.split())

    def test_queue_prompt_asks_the_three_steps_reason_first(self):
        s = sp_mod()
        p = " ".join(s.QUEUE_PROMPT.split())
        assert "habitual predisposition" in p and "20 to 40 words" in p
        schema = p[p.index('{"results"'):]
        order = ['"id"', '"label"', '"reason"', '"plausible"', '"name_fits"', '"suggested_name"', '"gloss"',
                 '"confidence"']
        assert [schema.index(k) for k in order] == sorted(schema.index(k) for k in order)

    def test_corpus_prompt_reason_first(self):
        p = " ".join(sp_mod().CORPUS_PROMPT.split())
        schema = p[p.index('{"results"'):]
        assert schema.index('"reason"') < schema.index('"reading"')
        assert "predisposition" in p and "momentary" in p

    def test_example_hygiene(self):
        import data_analysis.seed_entities as se
        s = sp_mod()
        data = REPO / "data"
        q = se.load_queue(data / "seed_queue.json")
        stems = set().union(*se.corpus_stems(data).values())
        stems |= {e.get("stem") for e in q["entries"]}
        stems |= {normalize_to_file_name(e["label"]) for e in q["entries"] if e.get("label")}
        words = list(s.EXAMPLE_WORDS) + list(s.SUGGESTED_NAMES)
        assert [w for w in words if normalize_to_file_name(w) in stems] == []
        low = (s.QUEUE_PROMPT + s.CORPUS_PROMPT).lower()
        for w in APPENDIX | SIX:
            assert not re.search(rf"\b{w}\b", low), w
        for w in s.EXAMPLE_WORDS:
            assert f'"{w}"' in s.QUEUE_PROMPT + s.CORPUS_PROMPT

    def test_queue_validator(self):
        s = sp_mod()
        rows, errs = s.parse_batch(json.dumps({"results": [
            qrow(1, "a"),
            qrow(2, "b", name_fits=False, suggested_name="easily b"),
            qrow(3, "c", plausible=False, name_fits=None, gloss=None),
            qrow(4, "d", gloss=None),                                  # plausible needs a gloss
            qrow(5, "e", name_fits=False, suggested_name=None),        # a new name needs a name
            qrow(6, "x", plausible="maybe")]}), [1, 2, 3, 4, 5, 6], mode="queue",
            labels={1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f"})
        assert set(rows) == {1, 2, 3} and set(errs) == {4, 5, 6}
        assert rows[2]["suggested_stem"] == "easily_b" and rows[1]["suggested_stem"] is None
        assert rows[3]["gloss"] is None and rows[3]["plausible"] is False

    def test_corpus_validator(self):
        s = sp_mod()
        rows, errs = s.parse_batch(json.dumps({"results": [
            crow_corpus(1, "a"), crow_corpus(2, "b", reading="momentary"), crow_corpus(3, "c", reading="both")]}),
            [1, 2, 3], mode="corpus", labels={1: "a", 2: "b", 3: "c"})
        assert set(rows) == {1, 2} and rows[2]["reading"] == "momentary" and 3 in errs


def states_responder(kw):
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    sysp = system_text(kw)
    if "corpus description" in sysp:
        return json.dumps({"results": [crow_corpus(it["id"], it["label"],
                                                   reading="momentary" if it["label"] == "bothered"
                                                   else "predisposition") for it in items]})
    spec = {"sunburnt": {"plausible": False, "name_fits": None, "gloss": None},
            "sulking": {"name_fits": False, "suggested_name": "sulky"}}
    return json.dumps({"results": [qrow(it["id"], it["label"], **spec.get(it["label"], {})) for it in items]})


class TestStatesPassRunner:
    def test_queue_mode_blocks(self):
        s = sp_mod()
        client = FakeAsyncAnthropic(states_responder)
        r = s.StatesPassRunner(client=client, batch_id="sp1", mode="queue", model=HAIKU)
        out = {x.key: x for x in r.run([s.StatesItem(key="sulking#1", label="sulking", text="This means sulking now."),
                                        s.StatesItem(key="sunburnt#1", label="sunburnt", text="Red skin.")])}
        b = out["sulking#1"].block
        assert out["sulking#1"].stage == "judged"
        assert b["plausible"] is True and b["suggested_name"] == "sulky" and b["suggested_stem"] == "sulky"
        assert b["mode"] == "queue" and b["rubric_version"] == 2 and b["prompt_sha256"] == s.PROMPT_SHA256["queue"]
        assert out["sunburnt#1"].block["plausible"] is False
        assert r.usage.n_calls == 1 and len(r.responses) == 1
        assert "This means sulking now." in user_text(client.calls[0])

    def test_failed_rows_retried_once(self):
        s = sp_mod()
        n = {"calls": 0}

        def flaky(kw):
            n["calls"] += 1
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            if n["calls"] == 1:
                return json.dumps({"results": [qrow(items[0]["id"], items[0]["label"])]})
            return states_responder(kw)
        r = s.StatesPassRunner(client=FakeAsyncAnthropic(flaky), batch_id="sp", mode="queue", model=HAIKU,
                               retry_delays=())
        out = r.run([s.StatesItem(key=f"w{i}#1", label=f"w{i}", text="t") for i in range(3)])
        assert all(x.stage == "judged" for x in out) and n["calls"] == 2
        assert r.parse_counts() == (3, 3)

    def test_items_from_filter_results(self):
        s = sp_mod()
        rows = [{"key": "a#1", "label": "a", "gloss": "g1", "meta": {"stratum": "oewn_random"},
                 "filter": {"verdict": "tagged", "tags": ["state"]}},
                {"key": "b#1", "label": "b", "gloss": "g2", "meta": {"stratum": "existing"},
                 "filter": {"verdict": "trait", "tags": ["state"]}},
                {"key": "c#1", "label": "c", "gloss": "g3", "meta": {},
                 "filter": {"verdict": "tagged", "tags": ["transient_only"]}},
                {"key": "d#1", "label": "d", "gloss": "g4", "meta": {}, "filter": {"verdict": "trait", "tags": []}}]
        assert [it.key for it in s.items_from_filter_results(rows)] == ["a#1", "b#1", "c#1"]
        assert [it.key for it in s.items_from_filter_results(rows, stratum="existing")] == ["b#1"]


# ---------------------------------------------------------------------------
# 3b, 3c. the states-pass CLI
# ---------------------------------------------------------------------------

@pytest.fixture
def cli(monkeypatch):
    import anthropic
    import dotenv

    from data_analysis.gap_generation import states_pass as cli_mod
    holder = {}

    def factory(**kw):
        holder["client"] = FakeAsyncAnthropic(states_responder)
        return holder["client"]
    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli_mod, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(cli_mod, "platform_dirty_files", lambda *a, **k: [])
    holder["mod"] = cli_mod
    return holder


def _filter_results(tmp_path):
    p = tmp_path / "results.jsonl"
    rows = [{"key": "sulking#1", "label": "sulking", "gloss": "This means sulking.", "stage": "classified",
             "meta": {"stratum": "oewn_random"}, "filter": {"verdict": "tagged", "tags": ["state"]}},
            {"key": "sunburnt#1", "label": "sunburnt", "gloss": "This means red skin.", "stage": "classified",
             "meta": {"stratum": "oewn_random"}, "filter": {"verdict": "tagged", "tags": ["state"]}},
            {"key": "stubborn#1", "label": "stubborn", "gloss": "g", "stage": "classified",
             "meta": {"stratum": "existing"}, "filter": {"verdict": "trait", "tags": []}}]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _corpus(tmp_path):
    d = tmp_path / "data"
    (d / "traits" / "instructions").mkdir(parents=True)
    (d / "roles" / "instructions").mkdir(parents=True)
    for stem, desc in (("brooding", "This means dwelling on grievances for days, by habit."),
                       ("bothered", "This means being annoyed right now.")):
        (d / "traits" / "instructions" / f"{stem}.json").write_text(json.dumps(
            {"positive_label": stem, "description": desc}))
    return d


class TestStatesPassCLI:
    def test_queue_mode_from_filter_results(self, tmp_path, cli):
        cand = tmp_path / "cand"
        rc = cli["mod"].main(["--batch-id", "sp1", "--mode", "queue", "--filter-results",
                              str(_filter_results(tmp_path)), "--out-root", str(cand)])
        assert rc == 0
        d = cand / "states_pass" / "sp1"
        for f in ("responses.jsonl", "results.jsonl", "summary.json", "usage.json", "run.json"):
            assert (d / f).exists(), f
        run = json.loads((d / "run.json").read_text())
        assert run["rubric_version"] == 2 and run["prompt_sha256"] == sp_mod().PROMPT_SHA256["queue"]
        res = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
        assert [r["key"] for r in res] == ["sulking#1", "sunburnt#1"]
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["parse_rate"] == 1.0 and s["plausible"] == 1 and s["renamed"] == ["sulking -> sulky"]
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 1

    def test_corpus_mode_reads_only_the_corpus(self, tmp_path, cli):
        data = _corpus(tmp_path)
        before = {p: p.read_bytes() for p in data.rglob("*.json")}
        cand = tmp_path / "cand"
        reg = tmp_path / "registry.jsonl"
        rc = cli["mod"].main(["--batch-id", "cc1", "--mode", "corpus", "--stems", "brooding", "bothered",
                              "--data-dir", str(data), "--registry", str(reg), "--out-root", str(cand)])
        assert rc == 0 and not reg.exists()
        assert {p: p.read_bytes() for p in data.rglob("*.json")} == before
        s = json.loads((cand / "states_pass" / "cc1" / "summary.json").read_text())["result"]
        assert [e["label"] for e in s["exceptions"]] == ["bothered"]
        sent = user_text(cli["client"].calls[0])
        assert "dwelling on grievances" in sent

    def test_registry_mode_writes_the_block(self, tmp_path, cli):
        reg = tmp_path / "registry.jsonl"
        submit_candidates([Candidate(surface=w, generator="g", run_id="r") for w in ("sulking", "stubborn")],
                          registry_path=reg)
        Registry(reg).update("sulking#1", {"holding": "states", "gloss": "This means sulking.",
                                           "filter": {"verdict": "tagged", "tags": ["state"]}})
        rc = cli["mod"].main(["--batch-id", "sp2", "--mode", "queue", "--holding-states", "--registry", str(reg),
                              "--out-root", str(tmp_path / "cand")])
        assert rc == 0
        rows = Registry(reg).fold()
        assert rows["sulking#1"]["states_pass"]["suggested_name"] == "sulky"
        assert "states_pass" not in rows["stubborn#1"] or rows["stubborn#1"].get("states_pass") is None

    def test_dry_run_and_budget_refusal(self, tmp_path, cli, capsys):
        cand = tmp_path / "cand"
        args = ["--mode", "queue", "--filter-results", str(_filter_results(tmp_path)), "--out-root", str(cand)]
        assert cli["mod"].main(["--batch-id", "d1", "--dry-run", *args]) == 0
        assert not (cand / "states_pass").exists() and "client" not in cli
        assert "tokens at" in capsys.readouterr().out
        assert cli["mod"].main(["--batch-id", "d2", "--budget-usd", "0.000001", *args]) == 2
        assert not (cand / "states_pass" / "d2").exists() and "client" not in cli


# ---------------------------------------------------------------------------
# 4. promotion from the states list
# ---------------------------------------------------------------------------

@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    for et in ("traits", "roles"):
        (d / et / "instructions").mkdir(parents=True)
    return d


def _held(surface, holding, states_pass=None):
    r = new_record(surface, sources=[{"generator": "g", "run_id": "r"}])
    r["filter"] = {"verdict": "tagged" if holding != "nationalities" else "trait",
                   "tags": ["state"] if holding == "states" else ["membership"], "reason": "r"}
    r["gloss"] = "This means being in the state now."
    r["holding"] = holding
    if states_pass is not None:
        r["states_pass"] = states_pass
    return r


PASS_OK = {"mode": "queue", "plausible": True, "name_fits": False, "suggested_name": "sulky",
           "suggested_stem": "sulky", "gloss": "This means falling into long silent sulks whenever crossed.",
           "reason": "People are often prone to sulking.", "rubric_version": 1}


class TestPromoteStates:
    def test_states_row_promotable_after_a_plausible_pass(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        rows = {"sulking#1": _held("sulking", "states", PASS_OK)}
        q = {"_meta": {}, "entries": []}
        rep = promote(rows, q, ["sulking#1"], data_dir=data_dir, dry_run=False)
        assert rep.promoted == ["sulking#1"]
        e = q["entries"][-1]
        assert e["stem"] == "sulky" and e["label"] == "sulky"
        assert e["description_draft"] == PASS_OK["gloss"]
        assert "states queue" in e["description_notes"] and "states_queue" in e["tags"]
        assert e["gap_gen"]["registry_key"] == "sulking#1"

    def test_name_that_fits_keeps_the_label(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        ok = {**PASS_OK, "name_fits": True, "suggested_name": None, "suggested_stem": None}
        q = {"_meta": {}, "entries": []}
        rep = promote({"tearful#1": _held("tearful", "states", ok)}, q, ["tearful#1"], data_dir=data_dir,
                      dry_run=False)
        assert rep.promoted == ["tearful#1"] and q["entries"][-1]["stem"] == "tearful"

    def test_refusals(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        bad = {**PASS_OK, "plausible": False}
        rows = {"a#1": _held("a", "states"), "b#1": _held("b", "states", bad),
                "c#1": _held("c", "physical", PASS_OK), "norwegian#1": _held("Norwegian", "nationalities")}
        rep = promote(rows, {"_meta": {}, "entries": []}, list(rows), data_dir=data_dir)
        assert rep.promoted == []
        assert "states pass" in rep.refused["a#1"]
        assert "implausible" in rep.refused["b#1"]
        assert "physical" in rep.refused["c#1"] and "nationalities" in rep.refused["norwegian#1"]

    def test_suggested_stem_checked_against_the_corpus(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        (data_dir / "traits" / "instructions" / "sulky.json").write_text("{}")
        rep = promote({"sulking#1": _held("sulking", "states", PASS_OK)}, {"_meta": {}, "entries": []},
                      ["sulking#1"], data_dir=data_dir)
        assert rep.promoted == [] and "corpus" in rep.refused["sulking#1"]


# ---------------------------------------------------------------------------
# 5. the probe and derived words
# ---------------------------------------------------------------------------

class TestProbeV3:
    def test_version_and_hash(self):
        from assistant_axis.gapgen.filter import PROMPT_SHA256
        assert fr.PROBE_RUBRIC_VERSION == 3
        assert PROMPT_SHA256["probe"] != ROUND1_PROBE_SHA

    def test_derived_words_count_as_real(self):
        p = " ".join(fr.DEFINE_PROBE_PROMPT.split())
        assert "common prefix or suffix" in p
        assert "whether or not a dictionary lists it" in p
        assert "trait-hood is judged elsewhere" in p

    def test_probe_only_runner(self):
        client = FakeAsyncAnthropic(lambda kw: json.dumps({"results": [
            {"id": json.loads(x)["id"], "reason": "r", "definition": "d", "known": True}
            for x in user_text(kw).splitlines()[1:]]}))
        r = FilterRunner(client=client, batch_id="p", model=HAIKU, second_model=None, second_opinion=False,
                         probe_only=True, zipf_fn=lambda w: 0.0, wordnet=False)
        out = r.run([FilterItem(key="unsmooth#1", label="unsmooth"), FilterItem(key="cxl#1", label="cxl")])
        assert [x.stage for x in out] == ["probed", "probed"]
        assert all(x.freq["define_probe"]["rubric_version"] == 3 for x in out)
        assert all("real English word" in system_text(c) for c in client.calls)

    def test_probe_only_cli(self, tmp_path, monkeypatch):
        import anthropic
        import dotenv

        from data_analysis.gap_generation import traithood_filter
        monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **kw: FakeAsyncAnthropic(
            lambda k: make_response(json.dumps({"results": [
                {"id": json.loads(x)["id"], "reason": "r", "definition": "d", "known": True}
                for x in user_text(k).splitlines()[1:]]}))))
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc1234")
        monkeypatch.setattr(traithood_filter, "platform_dirty_files", lambda *a, **k: [])
        val = tmp_path / "v.jsonl"
        val.write_text("".join(json.dumps({"surface": w, "stratum": "probe_check"}) + "\n"
                               for w in ("unsmooth", "cxl")))
        cand = tmp_path / "cand"
        assert traithood_filter.main(["--batch-id", "p1", "--validation-file", str(val), "--probe-only",
                                      "--out-root", str(cand)]) == 0
        s = json.loads((cand / "filter" / "p1" / "summary.json").read_text())["result"]
        assert s["probe_n"] == 2 and s["probe_failed"] == 0 and s["n_llm"] == 0


def test_classifier_prompt_changed_from_round1():
    from assistant_axis.gapgen.filter import PROMPT_SHA256
    assert PROMPT_SHA256["classifier"] != ROUND1_CLASSIFIER_SHA
