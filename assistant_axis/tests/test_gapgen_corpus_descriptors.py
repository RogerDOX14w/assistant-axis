"""The corpus's regions and alignment scores from its own descriptions (QUESTIONS 3, Roger 2026-10-09: "doing this
from corpus descriptions rather than labels makes sense"): M1's descriptors and alignment calls, as pinned and as M1
sends them, with a trait file's description standing where a candidate's gloss stands; the selection of
``--all`` / ``--only-missing``; the merge into ``corpus_regions.json``; and ``gap_registry.py corpus-regions
--from-descriptions``.  No API calls: a fake Anthropic client."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import corpus_descriptors as CD
from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

DESC = {"calm": "This means staying even and unruffled when things go wrong.",
        "stubborn": "This means refusing to change course once decided, whatever others say.",
        "obedient": "This means doing what those in charge say without question."}
LABEL = {"calm": "calm", "stubborn": "stubborn", "obedient": "obedient"}
REGION = {"calm": "emotional_temperament", "stubborn": "moral_stance", "obedient": "alignment_ai_agent"}
SCORE = {"calm": 0, "stubborn": 1, "obedient": 3}


def write_corpus(root: Path, desc=None, label=None) -> Path:
    desc, label = dict(desc or DESC), dict(label or LABEL)
    d = root / "data" / "traits" / "instructions"
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*.json"):
        f.unlink()
    for s, t in desc.items():
        (d / f"{s}.json").write_text(json.dumps({"positive_label": label[s], "description": t, "instruction": []}))
    return root / "data"


def trait(stem, desc=None, label=None):
    t = desc if desc is not None else DESC[stem]
    return {"stem": stem, "label": label or LABEL[stem], "description": t, "description_sha256": CD.sha256_text(t)}


def responder(*, bad_desc=(), bad_desc_once=(), bad_align=(), region=None, score=None):
    region, score = dict(REGION, **(region or {})), dict(SCORE, **(score or {}))
    seen: dict = {}
    d_sys, a_sys = sr.load_prompt("descriptors"), sr.load_prompt("alignment")

    def answer(kw):
        s, obj = system_text(kw), json.loads(user_text(kw))
        label = obj["label"]
        assert set(obj) == {"id", "label", "description"} and obj["id"] == 1
        if s == d_sys:
            seen[label] = seen.get(label, 0) + 1
            if label in bad_desc or (label in bad_desc_once and seen[label] == 1):
                return make_response('{"results": [{"id": 1, "reason": "x", "region": "nowhere"}]}',
                                     input_tokens=480, output_tokens=20)
            return make_response(json.dumps({"results": [{"id": 1, "reason": "About its temper.",
                                                          "region": region[label], "enactable_in_text": 2}]}),
                                 input_tokens=480, output_tokens=240)
        assert s == a_sys
        if label in bad_align:
            return make_response("{}", input_tokens=780, output_tokens=5)
        return make_response(json.dumps({"results": [{"id": 1, "reason": "Bears on deference.",
                                                      "alignment": score[label]}]}),
                             input_tokens=780, output_tokens=170)
    return answer


# --------------------------------------------------------------------------- the requests are M1's

class TestRequests:
    @pytest.mark.parametrize("step", ["descriptors", "alignment"])
    def test_the_request_is_m1s_wave_6_call_with_the_description_as_the_gloss(self, step):
        q = CD.request(step, label="calm", description=DESC["calm"])
        system = sr.load_prompt(step)
        assert CD.MODEL == SR.DEFAULT_MODEL == "claude-haiku-5-5"
        assert q["system"] == system and q["model"] == CD.MODEL
        # what SplitRunner._run sends in wave 6: payload(step, label=..., description=<gloss>)
        assert q["user"] == split.payload(step, label="calm", description=DESC["calm"])
        assert q["max_tokens"] == SR.SplitRunner._max_tokens(None, step, CD.MODEL)
        assert q["temperature"] == SR.TEMPERATURE and q["cache_system"] == SR.caches_system(system, CD.MODEL)

    def test_other_steps_are_refused(self):
        with pytest.raises(ValueError):
            CD.request("gloss", label="calm", description="x")

    def test_pins_are_the_rubrics_on_disk(self):
        p = CD.pins()
        cur = sr.current_versions(names=CD.STEPS)
        assert p["step_versions"] == {s: cur[s][0] for s in CD.STEPS}
        assert p["prompt_sha256"] == {s: sr.sha256(sr.load_prompt(s)) for s in CD.STEPS}

    def test_the_estimate_uses_m1s_measured_tokens(self):
        est = CD.estimate(5)
        assert [(x.n_calls, x.in_tok, x.out_tok) for x in est.lines] == [
            (5, *SR.tokens_for("descriptors", CD.MODEL)), (5, *SR.tokens_for("alignment", CD.MODEL))]
        assert est.usd > 0 and CD.estimate(0).lines == []

    def test_render_shows_both_requests_in_full(self):
        txt = CD.render(trait("calm"))
        for step in CD.STEPS:
            assert sr.load_prompt(step) in txt
            assert split.payload(step, label="calm", description=DESC["calm"]) in txt


# --------------------------------------------------------------------------- the corpus and the selection

class TestSelection:
    def test_load_corpus(self, tmp_path):
        data = write_corpus(tmp_path)
        corpus = CD.load_corpus(data)
        assert [t["stem"] for t in corpus] == ["calm", "obedient", "stubborn"]
        assert corpus[0] == trait("calm")

    def test_all_selects_every_trait(self):
        corpus = [trait(s) for s in sorted(DESC)]
        assert [(t["stem"], why) for t, why in CD.select(corpus, {}, mode="all")] == [
            ("calm", "all"), ("obedient", "all"), ("stubborn", "all")]

    def test_only_missing(self):
        corpus = [trait(s) for s in sorted(DESC)] + [trait("eager", "This means wanting to start at once.", "eager"),
                                                      trait("shy", "This means hanging back.", "shy")]
        current = {"label": "calm", "region": "emotional_temperament", "alignment_score": 0,
                   "alignment_relevant": False, "source": "description",
                   "description_sha256": CD.sha256_text(DESC["calm"])}
        existing = {
            "calm": current,                                                        # current: skipped
            "stubborn": {**current, "label": "stubborn",
                         "description_sha256": CD.sha256_text("an older description")},
            "obedient": {"label": "obedient", "region": "moral_stance", "alignment_relevant": True,
                         "verdict": "trait", "batch_id": "m1_validation_r2"},       # a row from the filter
            "shy": {**current, "label": "shy", "region": None, "description_sha256": CD.sha256_text(
                "This means hanging back."), "errors": {"descriptors": "x"}},       # a step failed
        }
        got = {t["stem"]: why for t, why in CD.select(corpus, existing, mode="only_missing")}
        assert got == {"stubborn": "description_changed", "obedient": "placeholder", "eager": "absent",
                       "shy": "failed"}
        existing["calm"] = {**current, "label": "Calm"}
        assert dict((t["stem"], w) for t, w in CD.select(corpus, existing, mode="only_missing"))["calm"] == \
            "label_changed"

    def test_a_null_placeholder_is_selected(self):
        existing = {"calm": {"label": None, "region": None, "alignment_relevant": None, "verdict": None,
                             "batch_id": None}}
        assert [w for _, w in CD.select([trait("calm")], existing, mode="only_missing")] == ["placeholder"]

    def test_unknown_mode(self):
        with pytest.raises(ValueError):
            CD.select([], {}, mode="some")


# --------------------------------------------------------------------------- the calls

def judge(traits, client, tmp_path, usage=None, **kw):
    got = {}
    rows = CD.run_judge(traits, client=client, usage=usage if usage is not None else MultiModelUsage(),
                        batch_id="cd_t", records_path=tmp_path / "responses.jsonl",
                        on_row=lambda stem, r: got.__setitem__(stem, r), retry_delays=(), **kw)
    return rows, got


class TestJudge:
    def test_both_steps_on_the_description(self, tmp_path):
        traits = [trait(s) for s in sorted(DESC)]
        client = FakeAsyncAnthropic(responder())
        usage = MultiModelUsage()
        rows, got = judge(traits, client, tmp_path, usage)
        assert got == rows and set(rows) == set(DESC)
        r = rows["obedient"]
        assert r["label"] == "obedient" and r["region"] == "alignment_ai_agent" and r["enactable_in_text"] == 2
        assert r["alignment_score"] == 3 and r["alignment_relevant"] is True and r["source"] == "description"
        assert r["description_sha256"] == CD.sha256_text(DESC["obedient"]) and r["model"] == CD.MODEL
        assert r["rubric_versions"] == CD.pins()["step_versions"] and r["batch_id"] == "cd_t"
        assert r["reasons"] == {"descriptors": "About its temper.", "alignment": "Bears on deference."}
        assert "errors" not in r and "previous_region" not in r
        # the filter's convention: relevant from a score of 2
        assert rows["stubborn"]["alignment_relevant"] is False and rows["calm"]["alignment_relevant"] is False
        assert len(client.calls) == 6 and usage.n_calls == 6 and usage.total_cost_usd > 0
        recs = [json.loads(x) for x in (tmp_path / "responses.jsonl").read_text().splitlines()]
        assert sorted((x["stem"], x["step"]) for x in recs) == sorted((s, st) for s in DESC for st in CD.STEPS)
        assert all(x["stage"] == CD.STAGE and x["text"] and x["usage_raw"] and x["charged_as"] == CD.MODEL
                   and x["prompt_sha256"] == CD.pins()["prompt_sha256"][x["step"]] for x in recs)

    def test_alignment_relevant_follows_the_filter(self, tmp_path):
        for score, rel in ((0, False), (1, False), (2, True), (3, True)):
            rows, _ = judge([trait("calm")], FakeAsyncAnthropic(responder(score={"calm": score})), tmp_path)
            assert rows["calm"]["alignment_relevant"] is rel is split.alignment_relevant_of(score)

    def test_a_failed_answer_is_retried_once_then_reported(self, tmp_path):
        traits = [trait("calm"), trait("stubborn")]
        client = FakeAsyncAnthropic(responder(bad_desc_once=("calm",), bad_desc=("stubborn",)))
        rows, _ = judge(traits, client, tmp_path)
        assert rows["calm"]["region"] == "emotional_temperament" and "errors" not in rows["calm"]
        s = rows["stubborn"]
        assert s["region"] is None and s["enactable_in_text"] is None and "descriptors" in s["errors"]
        assert s["alignment_score"] == 1                                 # the other step stands
        assert len(client.calls) == 2 + 2 + 2                            # two descriptors each, one alignment each

    def test_an_alignment_failure(self, tmp_path):
        rows, _ = judge([trait("calm")], FakeAsyncAnthropic(responder(bad_align=("calm",))), tmp_path)
        r = rows["calm"]
        assert r["region"] == "emotional_temperament" and r["alignment_score"] is None
        assert r["alignment_relevant"] is None and "alignment" in r["errors"]

    def test_a_trait_with_no_description_is_not_sent(self, tmp_path):
        client = FakeAsyncAnthropic(responder())
        rows, _ = judge([trait("calm", desc="")], client, tmp_path)
        assert client.calls == [] and rows["calm"]["region"] is None
        assert rows["calm"]["errors"] == {"descriptors": "no description", "alignment": "no description"}

    def test_a_budget_stop_keeps_the_rows_already_finished(self, tmp_path):
        usage = GuardedUsage(budget_usd=1e-9)
        got = {}
        with pytest.raises(BudgetExceededError):
            CD.run_judge([trait("calm"), trait("stubborn")], client=FakeAsyncAnthropic(responder()), usage=usage,
                         batch_id="cd_t", records_path=tmp_path / "r.jsonl",
                         on_row=lambda s, r: got.__setitem__(s, r), retry_delays=(), concurrency=1)
        recs = [json.loads(x) for x in (tmp_path / "r.jsonl").read_text().splitlines()]
        assert len(recs) == 1 and recs[0]["text"]                       # the call that crossed the cap is recorded
        assert got == {}


# --------------------------------------------------------------------------- the merge

class TestMerge:
    def test_merge(self):
        corpus = [trait(s) for s in sorted(DESC)] + [trait("eager", "This means wanting to start.", "eager")]
        old_filter = {"label": "calm", "region": "cognitive_epistemic", "alignment_relevant": False,
                      "verdict": "trait", "batch_id": "m1_validation_r2"}
        old_stub = {"label": "stubborn", "region": "moral_stance", "alignment_relevant": True, "source": "description",
                    "batch_id": "cd_0"}
        existing = {"calm": old_filter, "stubborn": old_stub, "gone": {"label": "gone", "region": "moral_stance"}}
        new_calm = {"label": "calm", "region": "emotional_temperament", "alignment_relevant": False,
                    "source": "description", "batch_id": "cd_1"}
        out = CD.merge(corpus, existing, {"calm": new_calm})
        assert list(out) == ["calm", "eager", "obedient", "stubborn"]       # sorted; "gone" left the corpus
        assert out["calm"]["region"] == "emotional_temperament"
        assert out["calm"]["previous_region"] == "cognitive_epistemic"
        assert out["calm"]["previous_alignment_relevant"] is False
        assert out["calm"]["previous_source"] == "filter m1_validation_r2"
        assert out["stubborn"] == old_stub                                  # not judged: kept as it was
        assert out["eager"] == {"label": "eager", "region": None, "alignment_relevant": None, "verdict": None,
                                "batch_id": None}                           # never judged: the null entry
        assert out["obedient"]["region"] is None

    def test_previous_of_a_description_row_and_of_none(self):
        assert CD.previous_fields(None) == {}
        assert CD.previous_fields({"label": "x", "region": "moral_stance", "alignment_relevant": True,
                                   "source": "description", "batch_id": "cd_0"}) == {
            "previous_region": "moral_stance", "previous_alignment_relevant": True,
            "previous_source": "description cd_0"}
        assert CD.previous_fields({"label": None, "region": None, "alignment_relevant": None, "verdict": None,
                                   "batch_id": None})["previous_source"] == "none"


# --------------------------------------------------------------------------- the command

@pytest.fixture
def cli(tmp_path, monkeypatch):
    from data_analysis.gap_generation import gap_registry
    data = write_corpus(tmp_path)
    out = tmp_path / "corpus_regions.json"
    runs = tmp_path / "runs"
    monkeypatch.setattr(gap_registry, "_corpus_regions_runs_root", lambda: runs)
    clients = []

    def make_client(responder_fn=None):
        c = FakeAsyncAnthropic(responder_fn or responder())
        clients.append(c)
        return c
    state = {"responder": None}
    monkeypatch.setattr(gap_registry, "_anthropic_client", lambda: make_client(state["responder"]))

    def run(*args):
        return gap_registry.main(["--data-dir", str(data), "corpus-regions", "--out", str(out), *args])
    return {"run": run, "out": out, "data": data, "runs": runs, "clients": clients, "state": state,
            "tmp": tmp_path}


def _result(p: Path) -> dict:
    return json.loads(p.read_text())["result"]


class TestCommand:
    def test_dry_run_sends_nothing_and_writes_nothing(self, cli, capsys):
        assert cli["run"]("--from-descriptions", "--all", "--dry-run") == 0
        assert cli["clients"] == [] and not cli["out"].exists() and not cli["runs"].exists()
        o = capsys.readouterr().out
        assert "DRY-RUN" in o and "total estimate" in o and sr.load_prompt("descriptors") in o
        assert split.payload("alignment", label="calm", description=DESC["calm"]) in o

    def test_dry_run_shows_the_named_trait(self, cli, capsys):
        assert cli["run"]("--from-descriptions", "--all", "--dry-run", "--show", "stubborn") == 0
        assert split.payload("descriptors", label="stubborn", description=DESC["stubborn"]) in capsys.readouterr().out

    def test_all_writes_every_trait_with_the_previous_region(self, cli, capsys):
        cli["out"].write_text(json.dumps({"result": {
            "calm": {"label": "calm", "region": "cognitive_epistemic", "alignment_relevant": False, "verdict": "trait",
                     "batch_id": "m1_validation_r2"},
            "stubborn": {"label": None, "region": None, "alignment_relevant": None, "verdict": None,
                         "batch_id": None}}}))
        assert cli["run"]("--from-descriptions", "--all", "--budget-usd", "1", "--batch-id", "cd_t") == 0
        obj = json.loads(cli["out"].read_text())
        res = obj["result"]
        assert set(res) == set(DESC)
        assert res["calm"]["region"] == "emotional_temperament" and res["calm"]["previous_region"] == "cognitive_epistemic"
        assert res["calm"]["previous_source"] == "filter m1_validation_r2"
        assert res["stubborn"]["previous_source"] == "none" and "previous_region" in res["stubborn"]
        assert "previous_region" not in res["obedient"]                     # no earlier row
        assert res["obedient"]["alignment_score"] == 3 and res["obedient"]["alignment_relevant"] is True
        assert all(r["source"] == "description" and r["batch_id"] == "cd_t" for r in res.values())
        run_dir = cli["runs"] / "cd_t"
        usage = json.loads((run_dir / "usage.json").read_text())
        assert usage["n_calls"] == 6 and usage["total_cost_usd"] > 0
        meta = json.loads((run_dir / "run.json").read_text())
        assert meta["mode"] == "all" and meta["n_selected"] == 3 and meta["model"] == CD.MODEL
        assert meta["step_versions"] == CD.pins()["step_versions"]
        assert meta["prompt_sha256"] == CD.pins()["prompt_sha256"]
        assert meta["n_failed"] == 0 and meta["cost_usd"] == usage["total_cost_usd"]
        assert len((run_dir / "responses.jsonl").read_text().splitlines()) == 6
        deps = [i["dep_key"] for i in obj["_provenance"]["inputs"]]
        assert deps == ["rubric_descriptors", "rubric_alignment", "responses_cd_t"]
        o = capsys.readouterr().out
        assert "regions before" in o and "regions after" in o and "changed region: 1" in o

    def test_only_missing_sends_only_the_changed_description(self, cli):
        assert cli["run"]("--from-descriptions", "--all", "--budget-usd", "1", "--batch-id", "cd_1") == 0
        first = _result(cli["out"])
        new = dict(DESC, stubborn="This means holding to a decision after everyone else has given up on it.")
        write_corpus(cli["tmp"], desc=new)
        cli["state"]["responder"] = responder(region={"stubborn": "cognitive_epistemic"})
        assert cli["run"]("--from-descriptions", "--only-missing", "--budget-usd", "1", "--batch-id", "cd_2") == 0
        assert len(cli["clients"][-1].calls) == 2
        second = _result(cli["out"])
        assert second["calm"] == first["calm"] and second["obedient"] == first["obedient"]
        s = second["stubborn"]
        assert s["region"] == "cognitive_epistemic" and s["batch_id"] == "cd_2"
        assert s["previous_region"] == "moral_stance" and s["previous_source"] == "description cd_1"
        assert s["description_sha256"] == CD.sha256_text(new["stubborn"])

    def test_only_missing_with_nothing_to_do(self, cli, capsys):
        assert cli["run"]("--from-descriptions", "--all", "--budget-usd", "1", "--batch-id", "cd_1") == 0
        before = cli["out"].read_text()
        assert cli["run"]("--from-descriptions", "--only-missing", "--budget-usd", "1", "--batch-id", "cd_2") == 0
        assert cli["out"].read_text() == before and len(cli["clients"]) == 1
        assert "nothing to judge" in capsys.readouterr().out

    def test_a_mode_is_required(self, cli):
        with pytest.raises(SystemExit):
            cli["run"]("--from-descriptions", "--budget-usd", "1")

    def test_from_filter_and_from_descriptions_exclude_each_other(self, cli):
        with pytest.raises(SystemExit):
            cli["run"]("--from-descriptions", "--all", "--from-filter", str(cli["tmp"]))

    def test_a_budget_is_required_for_a_paid_run(self, cli, capsys):
        assert cli["run"]("--from-descriptions", "--all") == 2
        assert cli["clients"] == [] and "--budget-usd" in capsys.readouterr().err

    def test_an_estimate_over_the_budget_is_refused(self, cli):
        assert cli["run"]("--from-descriptions", "--all", "--budget-usd", "0.00001") == 2
        assert cli["clients"] == [] and not cli["out"].exists()

    def test_an_existing_batch_id_is_refused(self, cli, capsys):
        assert cli["run"]("--from-descriptions", "--all", "--budget-usd", "1", "--batch-id", "cd_1") == 0
        assert cli["run"]("--from-descriptions", "--all", "--budget-usd", "1", "--batch-id", "cd_1") == 2
        assert len(cli["clients"]) == 1 and "cd_1" in capsys.readouterr().err

    def test_a_budget_stop_writes_what_was_paid_for(self, cli, monkeypatch):
        cli["out"].write_text(json.dumps({"result": {s: {"label": s, "region": "moral_stance",
                                                         "alignment_relevant": False, "verdict": "trait",
                                                         "batch_id": "m1"} for s in DESC}}))
        monkeypatch.setattr(CD, "DEFAULT_CONCURRENCY", 1)
        # cap just above the estimate, but every fake response is charged far more than estimated
        cli["state"]["responder"] = lambda kw: make_response(
            responder()(kw).content[0].text, input_tokens=400_000, output_tokens=10)
        rc = cli["run"]("--from-descriptions", "--all", "--budget-usd", "0.05", "--batch-id", "cd_s")
        assert rc == 2
        res = _result(cli["out"])
        judged = [s for s, r in res.items() if r.get("source") == "description"]
        assert len(judged) < 3 and all(res[s]["verdict"] == "trait" for s in set(DESC) - set(judged))
        meta = json.loads((cli["runs"] / "cd_s" / "run.json").read_text())
        assert meta["stopped"] and "budget" in meta["stopped"].lower()
        assert json.loads((cli["runs"] / "cd_s" / "usage.json").read_text())["n_calls"] >= 1
