"""W19 in the trait-gap tools (Roger, 2026-10-09): every prompt shows a label in the judge display form
(``careless (HEXACO)`` -> ``careless (from HEXACO)``), while the stored labels, the keys and the embedded texts stay
as they are; and a run that continues or replays another keeps that run's recorded label form
(:mod:`assistant_axis.gapgen.prompt_labels`).  No API calls: fake clients and toy corpora."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen import calibrate_llm as CL
from assistant_axis.gapgen import corpus_descriptors as CD
from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import overlap_test as OT
from assistant_axis.gapgen import physical_pass as PP
from assistant_axis.gapgen import plain_reading as pr
from assistant_axis.gapgen import prompt_labels as PL
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.gapgen import states_pass as SP
from assistant_axis.gapgen.representation import represent
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from assistant_axis.tests.test_gapgen_novelty import DIM, STEMS, query, rubrics, write_corpus

JUDGE, STORED = PL.JUDGE_LABEL_FORM, PL.STORED_LABEL_FORM
#: Two toy traits made standards-derived: alpha (a triangle corner) and theta (a clean pair with iota).
STANDARD = {"alpha": "alpha (HEXACO)", "theta": "theta (Holland)"}
SHOWN = {"alpha": "alpha (from HEXACO)", "theta": "theta (from Holland's RIASEC)"}


def write_standard_corpus(data_dir: Path) -> Path:
    write_corpus(data_dir)
    for stem, label in STANDARD.items():
        p = data_dir / "traits" / "instructions" / f"{stem}.json"
        doc = json.loads(p.read_text())
        doc["positive_label"] = label
        p.write_text(json.dumps(doc), encoding="utf-8")
    return data_dir


def standard_index(tmp_path) -> NV.CorpusIndex:
    traits = NV.load_trait_corpus(write_standard_corpus(tmp_path / "data"))
    E = np.zeros((len(STEMS), DIM))
    for i in range(len(STEMS)):
        E[i, i] = 1.0
    return NV.build_index(traits, E, variant="raw", settings={"k": 4})


def labels_in(user: str) -> list[str]:
    """Every ``label`` value of a JSON user turn (relation list, overlap pair)."""
    obj = json.loads(user)
    out = []
    for part in ("candidate", "target", "other"):
        if part in obj:
            out.append(obj[part]["label"])
    out += [t["label"] for t in obj.get("traits", [])]
    return out


# --------------------------------------------------------------------------- the helpers

class TestPromptLabel:
    def test_judge_form_by_default_stored_form_unchanged(self):
        assert PL.DEFAULT_LABEL_FORM == JUDGE == "judge-display-v1"
        assert PL.prompt_label("careless (HEXACO)") == "careless (from HEXACO)"
        assert PL.prompt_label("artistic (Holland)") == "artistic (from Holland's RIASEC)"
        assert PL.prompt_label("careless (HEXACO)", STORED) == "careless (HEXACO)"
        assert PL.prompt_label("gregarious") == "gregarious"                 # a candidate label: a no-op
        assert PL.prompt_label("humorous/serious (tentative, PC10)") == "humorous/serious (tentative, PC10)"

    def test_idempotent_and_tolerant(self):
        once = PL.prompt_label("ENFJ (MBTI)")
        assert once == "ENFJ (from the MBTI)" and PL.prompt_label(once) == once
        assert PL.prompt_label(None) is None and PL.prompt_label("") == ""

    def test_a_stem_stored_as_a_label_is_shown_without_underscores(self):
        # the seed queue's open_ended (a renamed trait with no file) stores its stem as its label
        assert PL.prompt_label("open_ended") == "open ended" == PL.prompt_label("open ended")
        assert PL.prompt_label("open_ended", STORED) == "open_ended"
        from assistant_axis.gapgen.generators.roget import placement as PLC
        item = PLC.PlacementItem(stem="open_ended", label="open_ended", description=None, source="queued",
                                 current=None, route="none", candidates=[])
        assert item.payload(None)["trait"]["label"] == "open ended"

    def test_unknown_form_refused(self):
        with pytest.raises(ValueError):
            PL.prompt_label("x", "display")
        with pytest.raises(ValueError):
            PL.recorded_label_form({"label_form": "judge-display-v0"})

    def test_recorded_form(self):
        assert PL.recorded_label_form(None) is None
        assert PL.recorded_label_form({}) == STORED                         # a run before 2026-10-09
        assert PL.recorded_label_form({"label_form": JUDGE}) == JUDGE
        assert PL.recorded_label_form({"result": {"label_form": JUDGE}, "_provenance": {}}) == JUDGE

    def test_resume_then_source_then_new(self):
        assert PL.resolve_label_form() == JUDGE                              # a new run
        assert PL.resolve_label_form(source={}) == STORED                    # replaying an old run
        assert PL.resolve_label_form(source={"label_form": JUDGE}) == JUDGE
        assert PL.resolve_label_form(earlier={}, source={"label_form": JUDGE}) == STORED   # the earlier session wins
        assert PL.resolve_label_form(earlier={"label_form": JUDGE}, source={}) == JUDGE


# --------------------------------------------------------------------------- M3: the relation and overlap calls

def judge_responder(seen: list):
    """Relation calls: alpha similar, the rest unrelated; overlap calls: 4 on alpha (whatever form its label is
    shown in), 1 otherwise.  Every user turn is kept in ``seen``."""
    def responder(kw):
        user = user_text(kw)
        seen.append(user)
        obj = json.loads(user)
        if "candidate" in obj:
            rows = [{"id": t["id"], "reason": "r", "relation": "similar" if t["label"].startswith("alpha") else
                     "unrelated"} for t in obj["traits"]]
            return make_response(json.dumps({"results": rows}))
        v = 4 if obj["other"]["label"].startswith("alpha") else 1
        return make_response(json.dumps({"reason": "r", "similarity": v}))
    return responder


def m3_runner(tmp_path, responder, *, label_form=None, records=(), idx=None):
    idx = idx or standard_index(tmp_path)
    sets = NV.label_sets(idx.traits, {"entries": []})
    kw = {} if label_form is None else {"label_form": label_form}
    client = FakeAsyncAnthropic(responder)
    r = NR.NoveltyRunner(client=client, batch_id="w19", rubrics=rubrics(), index=idx, label_sets=sets,
                         usage=MultiModelUsage(), responses_path=tmp_path / "out" / f"r{len(records)}.jsonl", k=4,
                         config_version="cfg", retry_delays=(), resume_records=records, relation_model=NV.HAIKU, **kw)
    return r, client, idx


def near_alpha():
    from assistant_axis.gapgen.normalize import normalize_candidate
    n = normalize_candidate("alphaish")
    c = NR.M3Candidate(key="alphaish#1", stem=n.stem, label=n.label, gloss="This means being alpha in every way.",
                       alignment_score=0, region=None, generators=["g"])
    return c, {c.key: query(alpha=0.9, theta=0.5, beta=0.3)}


class TestM3Prompts:
    def test_relation_and_overlap_show_the_judge_form(self, tmp_path):
        seen: list = []
        r, client, idx = m3_runner(tmp_path, judge_responder(seen))
        c, vec = near_alpha()
        states = r.run([c], vec)
        rel = [u for u in seen if "candidate" in json.loads(u)]
        ov = [u for u in seen if "target" in json.loads(u)]
        assert rel and ov
        shown = {lb for u in seen for lb in labels_in(u)}
        assert SHOWN["alpha"] in shown and SHOWN["theta"] in shown          # both standards, in the long form
        assert not any(STANDARD[s] in u for u in seen for s in STANDARD)     # never the stored suffix
        assert not any("_" in lb for lb in shown)                            # labels, never stems
        assert json.loads(ov[0])["other"]["label"] == SHOWN["alpha"]
        assert states[c.key].block["decision"] == "covered" and states[c.key].block["covered_by"] == "alpha"

    def test_stored_labels_and_embedded_texts_unchanged(self, tmp_path):
        seen: list = []
        r, _, idx = m3_runner(tmp_path, judge_responder(seen))
        c, vec = near_alpha()
        r.run([c], vec)
        assert idx.traits["alpha"].label == "alpha (HEXACO)" and r.corpus["alpha"]["label"] == "alpha (HEXACO)"
        assert idx.traits["theta"].label == "theta (Holland)"
        # the text the corpus side embeds (novelty_score.load_index) is built from the stored label
        t = idx.traits["alpha"]
        assert represent(t.label, t.description, "w20").startswith("alpha (HEXACO)")
        # the relation call records the stems it listed (keys), not labels
        recs = [json.loads(x) for x in (tmp_path / "out" / "r0.jsonl").read_text().splitlines()]
        assert all(s in idx.traits for rec in recs for s in rec["stems"])

    def test_the_stored_form_on_request(self, tmp_path):
        seen: list = []
        r, _, _ = m3_runner(tmp_path, judge_responder(seen), label_form=STORED)
        c, vec = near_alpha()
        r.run([c], vec)
        shown = {lb for u in seen for lb in labels_in(u)}
        assert STANDARD["alpha"] in shown and SHOWN["alpha"] not in shown

    def test_a_resume_in_the_recorded_form_sends_nothing_again(self, tmp_path):
        # an old run (stored form) answered everything; resumed in its own form, nothing is sent; resumed in the
        # judge form, every call that shows a standard's label would be asked again (why a resume keeps its form)
        seen: list = []
        r, _, idx = m3_runner(tmp_path, judge_responder(seen), label_form=STORED)
        c, vec = near_alpha()
        r.run([c], vec)
        records = [json.loads(x) for x in (tmp_path / "out" / "r0.jsonl").read_text().splitlines()]
        same, client_same, _ = m3_runner(tmp_path, judge_responder([]), label_form=STORED, records=records, idx=idx)
        same.run([c], vec)
        assert client_same.calls == []
        other, client_other, _ = m3_runner(tmp_path, judge_responder([]), label_form=JUDGE, records=records, idx=idx)
        other.run([c], vec)
        assert client_other.calls                                           # the prompts differ: asked again

    def test_render_relation_user_and_payload(self):
        traits = [("alpha (HEXACO)", "d1"), ("gregarious", "d2")]
        obj = json.loads(NV.render_relation_user("x (Big Five)", "g", traits))
        assert obj["candidate"]["label"] == "x (from the Big Five)"
        assert [t["label"] for t in obj["traits"]] == ["alpha (from HEXACO)", "gregarious"]
        assert NV.relation_payload("x", "g", traits, label_form=STORED)["traits"][0]["label"] == "alpha (HEXACO)"
        assert traits[0][0] == "alpha (HEXACO)"                              # the caller's data untouched


class TestReviewGraphRunner:
    def test_relation_call_lists_candidates_and_corpus_traits_in_the_judge_form(self, tmp_path):
        idx = standard_index(tmp_path)
        rr = RG.ReviewRunner(client=None, batch_id="rg", rubrics=rubrics(), index=idx,
                             label_sets=NV.LabelSets(set(), {}, {}), usage=MultiModelUsage(),
                             responses_path=tmp_path / "rg.jsonl")
        a = RG.PairCandidate(key="k1#1", stem="k1", label="k1 (VALS)", gloss="This means k1.", alignment_score=0,
                             region=None)
        b = RG.PairCandidate(key="k2#1", stem="k2", label="k2", gloss="This means k2.", alignment_score=0, region=None)
        rr.add_candidates([a, b])
        call = rr.relation_calls([("k1#1", ["k2#1", "alpha"])])[0]
        assert sorted(labels_in(call.user)) == sorted(["k1 (from VALS)", "k2", "alpha (from HEXACO)"])
        ov = rr.overlap_call("k1#1", "alpha")
        assert labels_in(ov.user) == ["k1 (from VALS)", "alpha (from HEXACO)"]
        assert rr.corpus["k1#1"]["label"] == "k1 (VALS)"                     # the runner's map keeps the stored label


# --------------------------------------------------------------------------- the overlap test's renderers and runner

class TestOverlapTest:
    corpus = {"t": {"label": "careless (HEXACO)", "description": "dt"}, "o": {"label": "tidy", "description": "do"},
              "p": {"label": "artistic (Holland)", "description": "dp"}}

    def test_list_and_single_forms(self):
        call = OT.Call(call_id="nn:t", set="nearest", target="t", listed=["o", "p"])
        obj = OT.payload_object(call, self.corpus)
        assert obj["target"]["label"] == "careless (from HEXACO)"
        assert [t["label"] for t in obj["traits"]] == ["tidy", "artistic (from Holland's RIASEC)"]
        assert "careless (from HEXACO)" in OT.render_user(call, self.corpus)
        pc = OT.PairCall(call_id="nn:t>p", set="nearest", target="t", listed=["p"])
        assert labels_in(OT.render_single(pc, self.corpus)) == ["careless (from HEXACO)",
                                                                "artistic (from Holland's RIASEC)"]
        assert labels_in(OT.render_single(pc, self.corpus, label_form=STORED)) == ["careless (HEXACO)",
                                                                                    "artistic (Holland)"]
        assert self.corpus["t"]["label"] == "careless (HEXACO)"            # the corpus map untouched
        params = OT.call_params(pc, self.corpus, rubric_text="sys", model=OT.SONNET, form="single")
        assert "careless (from HEXACO)" in params["messages"][0]["content"]

    @pytest.mark.parametrize("form,expected", [(JUDGE, "careless (from HEXACO)"), (STORED, "careless (HEXACO)")])
    def test_the_runner_sends_its_form(self, tmp_path, form, expected):
        seen: list = []

        def responder(kw):
            seen.append(user_text(kw))
            return make_response(json.dumps({"reason": "r", "similarity": 2}))
        rb = OT.load_rubrics(keys=["A"])
        runner = OT.OverlapRunner(FakeAsyncAnthropic(responder), rb, self.corpus, usage=MultiModelUsage(),
                                  responses_path=tmp_path / "responses.jsonl", retry_delays=(), label_form=form)
        pc = OT.PairCall(call_id="nn:t>o", set="nearest", target="t", listed=["o"])
        asyncio.run(runner.run_stage("A", OT.SONNET, [pc]))
        assert seen and labels_in(seen[0])[0] == expected
        rec = json.loads((tmp_path / "responses.jsonl").read_text().splitlines()[0])
        assert rec["target"] == "t" and labels_in(rec["request"]["user"])[0] == expected


# --------------------------------------------------------------------------- M1 (the split and single filters)

class TestM1Prompts:
    def test_payload_builders(self):
        assert json.loads(split.payload("sense", label="open (Big Five)"))["label"] == "open (from the Big Five)"
        assert json.loads(split.payload("alignment", label="open (Big Five)", description="d",
                                        label_form=STORED))["label"] == "open (Big Five)"
        cmp = split.comparison_payload(label="open (Big Five)", reading="r", intended="i")
        assert '"label": "open (from the Big Five)"' in cmp
        assert '"label": "open (from the Big Five)"' in fr.build_batch_prompt([{"id": 1, "label": "open (Big Five)"}])
        assert '"word": "open (from the Big Five)"' in fr.build_probe_prompt([{"id": 1, "label": "open (Big Five)"}])
        assert '"word": "open (Big Five)"' in fr.build_probe_prompt([{"id": 1, "label": "open (Big Five)"}],
                                                                     label_form=STORED)

    def test_split_runner_sends_the_judge_form_and_checks_the_echo_against_it(self):
        r = SR.SplitRunner(client=None, batch_id="w19", readings=1)
        r.state["k#1"] = {"label": "open (Big Five)", "intended": None, "errors": {}}
        c = r._sense_calls(["k#1"], role="first", model=r.model)[0]
        assert json.loads(c.user)["label"] == "open (from the Big Five)" and c.label == "open (from the Big Five)"
        answer = json.dumps({"results": [{"id": 1, "label": "open (from the Big Five)", "note": "n",
                                          "first_thought": "f", "first_thought_said_of": "people", "usable": True,
                                          "readings": [{"reading": "x", "rank": "primary"}]}]})
        row, err = split.parse("sense", answer, label=c.label)
        assert err is None and row["readings"][0]["reading"] == "x"
        assert r.state["k#1"]["label"] == "open (Big Five)"                 # the word's state keeps the stored label
        stored = SR.SplitRunner(client=None, batch_id="w19", readings=1, label_form=STORED)
        stored.state["k#1"] = {"label": "open (Big Five)", "intended": None, "errors": {}}
        assert json.loads(stored._sense_calls(["k#1"], role="first", model=stored.model)[0].user)["label"] == \
            "open (Big Five)"


# --------------------------------------------------------------------------- the other passes

class TestPlainReading:
    def test_reading_and_comparison_show_the_judge_form(self, tmp_path):
        seen: list = []

        def responder(kw):
            u = user_text(kw)
            seen.append(u)
            if u.startswith("Compare"):
                row = json.loads(u.splitlines()[1])
                return make_response(json.dumps({"results": [{"id": row["id"], "label": row["label"], "reason": "r",
                                                              "relation": "same", "confidence": 0.9}]}))
            return make_response("Behaves carelessly.")
        runner = pr.PlainReadingRunner(client=FakeAsyncAnthropic(responder), batch_id="w19", retry_delays=())
        res = runner.run([pr.ReadingItem(key="careless_hexaco", label="careless (HEXACO)", intended="desc")])
        assert '"You are careless (from HEXACO)."' in seen[0]
        assert '"label": "careless (from HEXACO)"' in seen[1]
        assert res[0].stage == "compared" and res[0].label == "careless (HEXACO)"   # the echo matched the shown form
        assert set(runner.readings) == {"careless (HEXACO)"}                # readings keyed by the stored label


class TestStatesPass:
    @pytest.mark.parametrize("form,expected", [(JUDGE, "careless (from HEXACO)"), (STORED, "careless (HEXACO)")])
    def test_corpus_mode_shows_the_runs_form_and_parses_its_echo(self, form, expected):
        seen: list = []

        def responder(kw):
            u = user_text(kw)
            seen.append(u)
            rows = [json.loads(x) for x in u.splitlines()[1:]]
            return make_response(json.dumps({"results": [{"id": x["id"], "label": x["label"], "reason": "r",
                                                          "reading": "predisposition", "confidence": 0.9}
                                                         for x in rows]}))
        r = SP.StatesPassRunner(client=FakeAsyncAnthropic(responder), batch_id="w19", mode="corpus", retry_delays=(),
                                label_form=form)
        res = r.run([SP.StatesItem(key="careless_hexaco", label="careless (HEXACO)", text="Leaves things undone.")])
        assert json.loads(seen[0].splitlines()[1])["label"] == expected
        assert res[0].stage == "judged" and res[0].label == "careless (HEXACO)" and "label" not in res[0].block
        assert r.responses[0]["items"][0]["label"] == "careless (HEXACO)"   # the record keeps the stored label
        # a resume in the same form takes the row from the record (keyed by key, stored label and text)
        again = SP.StatesPassRunner(client=FakeAsyncAnthropic(responder), batch_id="w19", mode="corpus",
                                    retry_delays=(), label_form=form, resume_records=r.responses)
        again.run([SP.StatesItem(key="careless_hexaco", label="careless (HEXACO)", text="Leaves things undone.")])
        assert again.stats["resumed_rows"] == 1 and len(seen) == 1

    def test_check_and_alignment_requests(self):
        assert json.loads(SP.build_check_prompt("careless (HEXACO)", "g"))["label"] == "careless (from HEXACO)"
        r = SP.StatesPassRunner(client=None, batch_id="w19", mode="queue")
        assert json.loads(r.alignment_call("k", "careless (HEXACO)", "g").user)["label"] == "careless (from HEXACO)"
        assert SP.route_for({"plausible": True, "suggested_name": "careless (from HEXACO)"},
                            label="careless (HEXACO)")[0] == "predisposition"   # the shown name is the name itself


class TestCorpusAndPhysicalPasses:
    def test_corpus_descriptors_show_the_judge_form_and_keep_the_stored_label(self, tmp_path):
        seen: list = []

        def responder(kw):
            u = user_text(kw)
            seen.append(u)
            if "region" in kw["system"][0]["text"] and "enactable" in kw["system"][0]["text"]:
                return make_response(json.dumps({"results": [{"id": 1, "reason": "r", "region": "moral_stance",
                                                              "enactable_in_text": 2}]}))
            return make_response(json.dumps({"results": [{"id": 1, "reason": "r", "alignment": 1}]}))
        trait = {"stem": "careless_hexaco", "label": "careless (HEXACO)", "description": "Leaves things undone.",
                 "description_sha256": CD.sha256_text("Leaves things undone.")}
        rows = CD.run_judge([trait], client=FakeAsyncAnthropic(responder), usage=MultiModelUsage(), batch_id="w19",
                            records_path=tmp_path / "r.jsonl", retry_delays=())
        assert {json.loads(u)["label"] for u in seen} == {"careless (from HEXACO)"}
        assert rows["careless_hexaco"]["label"] == "careless (HEXACO)"      # the row (and its staleness key) as stored
        assert CD.stale_reason(trait, rows["careless_hexaco"]) is None
        assert "careless (from HEXACO)" in CD.render(trait)
        recs = [json.loads(x) for x in (tmp_path / "r.jsonl").read_text().splitlines()]
        assert {r["label"] for r in recs} == {"careless (HEXACO)"}

    def test_physical_gloss_requests(self):
        q = PP.request("gloss", label="bald (VARK)", text="having no hair")
        assert json.loads(q["user"])["label"] == "bald (from VARK)"
        assert json.loads(PP.request("alignment", label="bald (VARK)", text="g", label_form=STORED)["user"])["label"] \
            == "bald (VARK)"


class TestCalibrationAndRoget:
    def test_paraphrase_and_blinded_prompts(self):
        u = CL.paraphrase_user([{"id": 1, "label": "careless (HEXACO)", "description": "d"}])
        assert json.loads(u)["label"] == "careless (from HEXACO)"
        item = {"label": "careless (HEXACO)", "description": "d", "A": ["artistic_holland"], "B": ["tidy_up"]}
        b = CL.blinded_user(item, swap=False, desc_of={}, label_of={"artistic_holland": "artistic (Holland)"})
        assert "Trait: careless (from HEXACO)" in b and "- artistic (from Holland's RIASEC):" in b
        assert "- tidy up:" in b and "tidy_up" not in b                     # a missing label: display form, not stem

    def test_placement_payload(self):
        from assistant_axis.gapgen.generators.roget import placement as PLC
        item = PLC.PlacementItem(stem="careless_hexaco", label="careless (HEXACO)", description="d", source="corpus",
                                 current=None, route="none", candidates=[])
        assert item.payload(None)["trait"]["label"] == "careless (from HEXACO)"
        assert item.payload(None, label_form=STORED)["trait"]["label"] == "careless (HEXACO)"
        assert item.label == "careless (HEXACO)"
