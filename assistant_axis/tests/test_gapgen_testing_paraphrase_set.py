"""Workstream 13's paraphrase sanity set (``assistant_axis/gapgen/testing/paraphrase_set.py``; coding plan 13 § 6,
§ 8 and task 7): the pinned synonym prompt (reasoning first, no example words), the user turn (the paraphrase,
never the hidden label; the re-ask's "must not be the word" line), the parser, the run (every response recorded
before it is parsed and charged, an unparseable answer asked once more, a label that names the hidden trait asked
once more, resume), the scratch registry (rows M3 selects), the hidden file (pairs whole), the seeded draw (on the
toy corpus and on the real data: 40 + 40 distinct hiding groups) and the report on a planted harness batch.  No API
calls: a fake client and the toy corpus of the novelty tests."""
import json
import logging
import re
import shutil
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import recovery as RC
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.registry import Registry, has_source
from assistant_axis.gapgen.testing import PARAPHRASE_SET_DIR
from assistant_axis.gapgen.testing import paraphrase_set as PS
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text
from assistant_axis.tests.test_gapgen_novelty import write_corpus

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "reports" / "trait_gap_generation" / "coding_plan_13_generator_testing.md"
TOY_REGIONS = {"alpha": "moral_stance", "beta": "moral_stance", "gamma": "moral_stance", "delta": "cognitive_epistemic",
               "epsilon": "cognitive_epistemic", "theta": "communication_style", "iota": "communication_style",
               "zeta": "cognitive_epistemic", "eta": "emotional_temperament", "kappa": None,
               "lambda_mu": "moral_stance"}


def toy(tmp_path, **kw):
    data = write_corpus(tmp_path / "data", **kw)
    return data, NV.load_trait_corpus(data)


def para(stem: str) -> str:
    """A toy paraphrase that never names its trait."""
    return f"This means a toy way of being, number {sum(map(ord, stem))}, kept up across many settings."


def toy_paraphrases(traits, stems=None):
    stems = list(traits) if stems is None else stems
    paras = {s: para(s) for s in stems}
    sources = {s: PS.paraphrase_source(traits[s].label, traits[s].description) for s in stems}
    return paras, sources


def item(stem="zeta", *, kind="single", partner=None, iid="s01", region="cognitive_epistemic", alignment=0):
    return PS.Item(id=iid, kind=kind, hidden_stem=stem, partner_stem=partner, region=region, alignment_score=alignment,
                   paraphrase_source=PS.PARAPHRASE_SOURCE, paraphrase=para(stem))


def reply(label, gloss="This means holding steady in a quiet, settled manner through most ordinary days.",
          reasoning="The definition describes a steady way of being."):
    return json.dumps({"reasoning": reasoning, "label": label, "gloss": gloss})


def item_of(kw, items):
    """The item a fake call is about (its paraphrase is in the user turn)."""
    u = user_text(kw)
    return next(it for it in items if it.paraphrase in u)


def run(items, client, out_dir, traits, **kw):
    usage = kw.pop("usage", None) or MultiModelUsage()
    out = PS.run(items, client=client, usage=usage, out_dir=out_dir, traits=traits, **kw)
    return out, usage


def read_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


# --------------------------------------------------------------------------- the rubric

class TestRubric:
    def test_the_rubric_is_pinned(self):
        from data_analysis.gap_generation import rubric_pins
        assert PS.RUBRIC_NAME == "paraphrase_synonym"
        assert sr.GENERATOR_FILES["paraphrase_synonym"] == "paraphrase_synonym.md"
        assert "paraphrase_synonym" in sr.PINNED_NAMES
        assert rubric_pins.main(["check"]) == 0
        rub = PS.load_rubric()
        assert rub["version"] == 1 and rub["sha256"] == sr.sha256(sr.load_prompt("paraphrase_synonym"))
        assert sr.read_versions()["prompts"]["paraphrase_synonym"][0]["version"] == 1
        assert PS.SYNONYM_SYSTEM == sr.load_prompt("paraphrase_synonym") == PS.system_prompt()

    def test_the_text_is_the_plans_rendered_prompt(self):
        """The plan's "Rendered prompt" section is what Roger reviewed: the pinned block is its [system] text."""
        lines = PLAN.read_text().splitlines()
        start = lines.index("[system]") + 1
        end = lines.index("[user]")
        assert PS.SYNONYM_SYSTEM == "\n".join(lines[start:end]).rstrip("\n")

    def test_reasoning_is_the_first_key(self):
        text = PS.SYNONYM_SYSTEM
        fmt = json.loads(text.splitlines()[-1])
        assert list(fmt) == ["reasoning", "label", "gloss"]
        assert "Reason first" in text and text.index("Reason first") < text.rindex("{")

    def test_no_example_words(self):
        """Every quoted string in the prompt is the corpus form, a key or a placeholder: no example word that could
        be a corpus label, a queue entry or a validation word."""
        quoted = set(re.findall(r'"([^"]*)"', PS.SYNONYM_SYSTEM))
        assert quoted <= {"This means ...", "reasoning", "<one or two sentences>", "label", "<label>", "gloss"}

    def test_an_unpinned_edit_is_refused(self, tmp_path):
        d = tmp_path / "rubrics"
        d.mkdir()
        for name in sr.PINNED_FILES.values():
            if (sr.RUBRICS_DIR / name).exists():
                shutil.copy2(sr.RUBRICS_DIR / name, d / name)
        shutil.copy2(sr.versions_path(), sr.versions_path(d))
        p = d / "paraphrase_synonym.md"
        p.write_text(p.read_text().replace("a careful lexicographer", "a careful editor"))
        with pytest.raises(PS.RubricNotPinned, match="rubric_pins.py bump paraphrase_synonym"):
            PS.load_rubric(d)


# --------------------------------------------------------------------------- the user turn and the parser

class TestRender:
    def test_the_user_turn_is_the_paraphrase_and_never_the_label(self):
        it = item("zeta")
        u = PS.render_user(it)
        assert u == "Definition: " + it.paraphrase
        assert "zeta" not in u

    def test_the_reask_line(self):
        it = item("zeta")
        u = PS.render_user(it, reask_label="zeta")
        assert u == ("Definition: " + it.paraphrase + "\n"
                     'The label must not be the word "zeta" or a spelling of it.')

    def test_the_reask_shows_the_judge_display_form(self):
        it = item("careless_hexaco")
        assert PS.render_user(it, reask_label="careless (HEXACO)").endswith(
            'The label must not be the word "careless (from HEXACO)" or a spelling of it.')
        assert 'the word "absorption-prone"' in PS.render_user(it, reask_label="absorption-prone")


class TestParse:
    def test_a_scripted_reply(self):
        a = PS.parse(reply("steady"))
        assert (a.reasoning, a.label, a.gloss) == ("The definition describes a steady way of being.", "steady",
                                                   "This means holding steady in a quiet, settled manner through most "
                                                   "ordinary days.")

    def test_code_fences_and_prose_are_tolerated(self):
        assert PS.parse("```json\n" + reply("hands-off") + "\n```").label == "hands-off"
        assert PS.parse("Here it is:\n" + reply("hands off")).label == "hands off"

    @pytest.mark.parametrize("text", [
        reply(""), reply("   "), reply("steady", gloss="Holding steady in a settled way."), reply("!!!"),
        "not json", "", None, json.dumps({"label": "steady", "gloss": "This means x."}),
        json.dumps({"reasoning": "r", "label": 3, "gloss": "This means x."}), json.dumps(["steady"]),
    ])
    def test_bad_replies_are_rejected(self, text):
        assert PS.parse(text) is None


# --------------------------------------------------------------------------- the run

class TestRun:
    def test_every_response_is_recorded_before_it_is_parsed_and_charged(self, tmp_path, monkeypatch):
        _, traits = toy(tmp_path)
        items = [item("zeta", iid="s01"), item("eta", iid="s02")]
        out = tmp_path / "out"
        seen = {"zeta": 0}

        def responder(kw):
            it = item_of(kw, items)
            if it.hidden_stem == "zeta":
                seen["zeta"] += 1
                return "I cannot answer in JSON." if seen["zeta"] == 1 else reply("unruffled")
            return reply("hushed")

        real_parse = PS.parse
        checked = []

        def parse_after_record(text):
            assert any(r["text"] == text for r in read_jsonl(out / PS.RESPONSES_NAME))
            checked.append(text)
            return real_parse(text)

        monkeypatch.setattr(PS, "parse", parse_after_record)
        answers, usage = run(items, FakeAsyncAnthropic(responder), out, traits)
        recs = read_jsonl(out / PS.RESPONSES_NAME)
        assert len(recs) == 3 and len(checked) == 3
        z = sorted((r for r in recs if r["item_id"] == "s01"), key=lambda r: r["attempt"])
        assert [r["attempt"] for r in z] == [1, 2] and z[0]["text"] == "I cannot answer in JSON."
        assert usage.n_calls == 3                                         # the unparseable one is charged too
        for r in recs:
            assert r["model"] == PS.MODEL and r["usage_raw"]["input_tokens"] == 1000 and r["charged_as"] == PS.MODEL
            assert r["prompt_sha256"] == PS.prompt_sha256(PS.SYNONYM_SYSTEM, r["user"])
            assert r["reask"] is False and r["rubric_version"] == 1
        assert json.loads((out / PS.USAGE_NAME).read_text())["n_calls"] == 3
        by = {a["id"]: a for a in answers}
        assert by["s01"]["label"] == "unruffled" and by["s01"]["answered"] and not by["s01"]["label_path"]
        assert by["s02"]["label"] == "hushed" and by["s02"]["reasoning"].startswith("The definition")
        for a in answers:
            assert a["model"] == PS.MODEL and a["reasked"] is False
            assert set(PS.Item.__dataclass_fields__) <= set(a)
        assert read_jsonl(out / PS.ANSWERS_NAME) == answers

    def test_the_call_is_haiku_with_the_cached_system_and_no_temperature(self, tmp_path):
        _, traits = toy(tmp_path)
        items = [item("zeta")]
        client = FakeAsyncAnthropic(lambda kw: reply("unruffled"))
        run(items, client, tmp_path / "out", traits)
        kw = client.calls[0]
        assert kw["model"] == "claude-haiku-5-5" and "temperature" not in kw
        assert system_text(kw) == PS.SYNONYM_SYSTEM and kw["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert user_text(kw) == "Definition: " + items[0].paraphrase

    def test_an_unparseable_answer_is_asked_once_more_only(self, tmp_path, caplog):
        _, traits = toy(tmp_path)
        client = FakeAsyncAnthropic(lambda kw: "no")
        with caplog.at_level(logging.INFO):
            answers, usage = run([item("zeta")], client, tmp_path / "out", traits)
        assert len(client.calls) == 2 and usage.n_calls == 2
        assert answers[0]["answered"] is False and answers[0]["failure"] == "unparseable"
        assert answers[0]["label"] is None
        assert "HIGH FAIL RATE" in caplog.text                     # warn_if_low_parse_rate at the end

    def test_a_label_that_is_the_hidden_stem_is_reasked_once(self, tmp_path):
        _, traits = toy(tmp_path)
        items = [item("lambda_mu", iid="s01"), item("zeta", iid="s02")]

        def responder(kw):
            it, u = item_of(kw, items), user_text(kw)
            if "must not be the word" in u:
                return reply("even-keeled")
            return reply("lambdamu" if it.hidden_stem == "lambda_mu" else "zeta")   # separator-blind: lambda_mu

        client = FakeAsyncAnthropic(responder)
        answers, _ = run(items, client, tmp_path / "out", traits)
        by = {a["id"]: a for a in answers}
        for iid, shown in (("s01", "lambda mu"), ("s02", "zeta")):
            a = by[iid]
            assert a["reasked"] is True and a["label_path"] is False and a["label"] == "even-keeled"
            assert a["first_label"] in ("lambdamu", "zeta")
        reasks = [user_text(kw) for kw in client.calls if "must not be the word" in user_text(kw)]
        assert len(client.calls) == 4 and len(reasks) == 2
        assert any(u.endswith('The label must not be the word "lambda mu" or a spelling of it.') for u in reasks)
        assert any(u.endswith('The label must not be the word "zeta" or a spelling of it.') for u in reasks)
        recs = read_jsonl(tmp_path / "out" / PS.RESPONSES_NAME)
        assert sorted(r["reask"] for r in recs) == [False, False, True, True]
        reask_s02 = next(u for u in reasks if items[1].paraphrase in u)
        assert by["s02"]["prompt_sha256"] == PS.prompt_sha256(PS.SYNONYM_SYSTEM, reask_s02)

    def test_a_renamed_from_label_is_on_the_label_path_and_stays_there(self, tmp_path):
        _, traits = toy(tmp_path, renamed={"eta": "old_eta"})
        items = [item("eta")]
        client = FakeAsyncAnthropic(lambda kw: reply("Old-Eta"))           # both times: a spelling of old_eta
        answers, _ = run(items, client, tmp_path / "out", traits)
        a = answers[0]
        assert a["label_path"] is True and a["reasked"] is True and a["label"] == "Old-Eta"
        assert len(client.calls) == 2
        assert 'The label must not be the word "eta"' in user_text(client.calls[1])

    def test_resume_sends_nothing_answered(self, tmp_path):
        _, traits = toy(tmp_path)
        items = [item("zeta", iid="s01"), item("eta", iid="s02"), item("kappa", iid="s03")]
        out = tmp_path / "out"

        def first(kw):
            return "garbled" if item_of(kw, items).hidden_stem == "kappa" else reply("composed")

        a1, u1 = run(items, FakeAsyncAnthropic(first), out, traits)
        assert {a["id"]: a["answered"] for a in a1} == {"s01": True, "s02": True, "s03": False}
        with pytest.raises(FileExistsError):
            run(items, FakeAsyncAnthropic(first), out, traits)              # a second run needs resume
        second = FakeAsyncAnthropic(lambda kw: reply("placid"))
        a2, u2 = run(items, second, out, traits, resume=True)
        assert [item_of(kw, items).hidden_stem for kw in second.calls] == ["kappa"]
        by = {a["id"]: a for a in a2}
        assert by["s01"]["label"] == "composed" and by["s03"]["label"] == "placid"
        # the earlier spend is carried: 4 charged before (2 answered + 2 garbled), 1 now
        assert u2.n_calls == 5 and json.loads((out / PS.USAGE_NAME).read_text())["n_calls"] == 5
        third = FakeAsyncAnthropic(lambda kw: pytest.fail("resume sent an answered item"))
        a3, _ = run(items, third, out, traits, resume=True)
        assert third.calls == [] and [a["label"] for a in a3] == [a["label"] for a in a2]

    def test_a_budget_stop_keeps_the_paid_response(self, tmp_path):
        _, traits = toy(tmp_path)
        items = [item("zeta", iid="s01"), item("eta", iid="s02")]
        out = tmp_path / "out"
        usage = GuardedUsage(budget_usd=1e-9, usage_path=out / PS.USAGE_NAME)
        with pytest.raises(BudgetExceededError):
            run(items, FakeAsyncAnthropic(lambda kw: reply("composed")), out, traits, usage=usage, concurrency=1)
        recs = read_jsonl(out / PS.RESPONSES_NAME)
        assert len(recs) == 1 and recs[0]["text"] == reply("composed")
        assert json.loads((out / PS.USAGE_NAME).read_text())["n_calls"] == 1
        assert [a["id"] for a in read_jsonl(out / PS.ANSWERS_NAME) if a["answered"]] == [recs[0]["item_id"]]


# --------------------------------------------------------------------------- the scratch registry and hidden file

def answered(it, label, gloss="This means keeping an even temper through most of what a day brings."):
    return it.as_dict() | {"label": label, "gloss": gloss, "reasoning": "r", "label_path": False, "reasked": False,
                           "model": PS.MODEL, "prompt_sha256": "x", "answered": True}


class TestScratchRegistry:
    def test_rows_select_as_m3_candidates(self, tmp_path):
        items = [item("zeta", iid="s01", region="cognitive_epistemic", alignment=2),
                 item("delta", kind="pair_pole", partner="epsilon", iid="p01", region=None, alignment=None)]
        answers = [answered(items[0], "even-keeled"), answered(items[1], "Data Minded")]
        path = tmp_path / "registry.jsonl"
        assert PS.to_scratch_registry(items, answers, TOY_REGIONS, path) == 2
        rows = Registry(path).fold()
        assert set(rows) == {"even_keeled#1", "data_minded#1"}
        r = rows["even_keeled#1"]
        assert r["gloss"] == answers[0]["gloss"] and r["holding"] is None and r["label"] == "even-keeled"
        f = r["filter"]
        assert (f["verdict"], f["outcome"], f["region"], f["alignment"], f["alignment_score"], f["batch_id"],
                f["synthetic"]) == ("trait", "trait", "cognitive_epistemic", 2, 2, "testing/paraphrase_set", True)
        assert f["gloss"] == r["gloss"]
        assert has_source(r, "testing", "paraphrase_set") and r["sources"][0]["source_ref"] == "s01"
        assert "zeta" not in json.dumps(r)                     # nothing in the row names the hidden trait
        for row in rows.values():
            cand, why = NR.candidate_from_row(row)
            assert why is None and cand.gloss and cand.generators == ["testing"]
        cand, _ = NR.candidate_from_row(rows["even_keeled#1"])
        assert cand.alignment_score == 2 and cand.region == "cognitive_epistemic"
        cand, _ = NR.candidate_from_row(rows["data_minded#1"])
        assert cand.alignment_score is None and cand.region == "cognitive_epistemic"   # the regions file's

    def test_the_harness_selects_every_row(self, tmp_path):
        """``recovery_test.run_candidates`` is how the harness picks a run's rows (``select_candidates`` as ``--hide``
        calls it): every answered item is taken and none is left out."""
        from data_analysis.gap_generation import recovery_test as RT
        items = [item("zeta", iid="s01"), item("delta", kind="pair_pole", partner="epsilon", iid="p01")]
        path = tmp_path / "registry.jsonl"
        PS.to_scratch_registry(items, [answered(items[0], "even-keeled"), answered(items[1], "steady")], {}, path)
        cands, skipped = RT.run_candidates(Registry(path).fold(), PS.GENERATOR, PS.RUN_ID)
        assert sorted(c.key for c in cands) == ["even_keeled#1", "steady#1"] and skipped == {}

    def test_colliding_labels_get_their_own_sense(self, tmp_path):
        items = [item("zeta", iid="s01"), item("eta", iid="s02"), item("kappa", iid="s03")]
        answers = [answered(items[0], "steady"), answered(items[1], "Steady"),
                   items[2].as_dict() | {"answered": False, "label": None, "gloss": None}]
        path = tmp_path / "registry.jsonl"
        assert PS.registry_keys(items, answers) == {"s01": "steady#1", "s02": "steady#2"}
        assert PS.to_scratch_registry(items, answers, {}, path) == 2
        rows = Registry(path).fold()
        assert set(rows) == {"steady#1", "steady#2"}
        assert rows["steady#1"]["filter"]["same_label_as"] == ["s02"]
        assert rows["steady#2"]["filter"]["same_label_as"] == ["s01"]
        assert rows["steady#2"]["sense_id"] == 2 and rows["steady#2"]["sources"][0]["source_ref"] == "s02"

    def test_a_rewrite_starts_afresh_and_keeps_a_backup(self, tmp_path):
        items = [item("zeta", iid="s01")]
        path = tmp_path / "registry.jsonl"
        PS.to_scratch_registry(items, [answered(items[0], "steady")], {}, path)
        PS.to_scratch_registry(items, [answered(items[0], "placid")], {}, path)
        assert set(Registry(path).fold()) == {"placid#1"}
        assert list(tmp_path.glob("registry.jsonl.bak.*"))

    def test_the_real_registry_is_refused(self):
        from assistant_axis.gapgen import paths
        for p in (paths.REGISTRY_PATH, paths.REGISTRY_SNAPSHOT_GZ_PATH, paths.REGISTRY_SNAPSHOT_PATH):
            with pytest.raises(ValueError, match="scratch"):
                PS.to_scratch_registry([item()], [answered(item(), "steady")], {}, p)


class TestHiddenFile:
    def test_each_pair_hides_whole(self, tmp_path):
        data, traits = toy(tmp_path)
        kinds = RC.arrangement_kinds(data, traits)
        items = [item("zeta", iid="s01"), item("delta", kind="pair_pole", partner="epsilon", iid="p01"),
                 item("iota", kind="pair_pole", partner="theta", iid="p02")]
        doc = PS.hidden_file(items, traits, TOY_REGIONS, kinds)
        assert doc["hidden"] == ["delta", "epsilon", "iota", "theta", "zeta"]
        assert sorted(g["members"] for g in doc["groups"]) == [["delta", "epsilon"], ["iota", "theta"], ["zeta"]]
        assert doc["hidden_frac"] is None and doc["source"] == "testing/paraphrase_set"
        RC.write_hidden(tmp_path / "hidden.json", doc, data_dir=data, regions_path=None)
        assert RC.load_hidden(tmp_path / "hidden.json")["stems"] == doc["hidden"]


# --------------------------------------------------------------------------- the draw

class TestBuildSet:
    def test_toy_draw_is_seeded_and_refuses_missing_and_stale_paraphrases(self, tmp_path):
        _, traits = toy(tmp_path)
        paras, sources = toy_paraphrases(traits)
        del paras["kappa"]                                  # no paraphrase
        sources["lambda_mu"] = "0" * 64                     # written from another text: stale
        items, stats = PS.build_set_with_stats(traits, paras, TOY_REGIONS, n_single=2, n_pairs=2, seed=0,
                                               sources=sources, alignment={"zeta": 1})
        again = PS.build_set(traits, paras, TOY_REGIONS, n_single=2, n_pairs=2, seed=0, sources=sources,
                             alignment={"zeta": 1})
        assert items == again
        singles = [it for it in items if it.kind == "single"]
        pairs = [it for it in items if it.kind == "pair_pole"]
        assert sorted(it.hidden_stem for it in singles) == ["eta", "zeta"]        # kappa and lambda_mu refused
        assert [it.id for it in singles] == ["s01", "s02"] and [it.id for it in pairs] == ["p01", "p02"]
        assert {frozenset((it.hidden_stem, it.partner_stem)) for it in pairs} == {
            frozenset(("delta", "epsilon")), frozenset(("iota", "theta"))}
        for it in items:
            assert it.paraphrase == paras[it.hidden_stem] and it.paraphrase_source == "calibration/paraphrases.json"
            assert it.region == TOY_REGIONS[it.hidden_stem]
        assert next(it for it in items if it.hidden_stem == "zeta").alignment_score == 1
        assert set(stats["refused"]) == {"no_paraphrase", "stale", "names_label"}
        assert stats["pool"]["single"] == {"groups": 4, "eligible": 2,
                                           "ineligible": {"no_paraphrase": ["kappa"], "stale": ["lambda_mu"]}}
        assert sum(stats["regions"]["single"].values()) == 2 and sum(stats["regions"]["pair_pole"].values()) == 2

    def test_a_paraphrase_naming_its_trait_is_refused(self, tmp_path):
        _, traits = toy(tmp_path)
        paras, sources = toy_paraphrases(traits)
        paras["eta"] = "This means being eta about everything."
        _, stats = PS.build_set_with_stats(traits, paras, TOY_REGIONS, n_single=2, n_pairs=1, seed=0, sources=sources)
        assert "eta" in stats["pool"]["single"]["ineligible"]["names_label"]

    def test_different_seeds_draw_differently_and_too_few_is_refused(self, tmp_path):
        _, traits = toy(tmp_path)
        paras, sources = toy_paraphrases(traits)
        draws = {tuple(it.hidden_stem for it in PS.build_set(traits, paras, TOY_REGIONS, n_single=1, n_pairs=1,
                                                             seed=s, sources=sources)) for s in range(20)}
        assert len(draws) > 1
        with pytest.raises(ValueError, match="pair"):
            PS.build_set(traits, paras, TOY_REGIONS, n_single=1, n_pairs=3, seed=0, sources=sources)

    def test_the_real_data_gives_40_and_40_distinct_groups(self):
        traits = NV.load_trait_corpus(REPO / "data")
        paras, sources = PS.load_paraphrases(PS.PARAPHRASES_PATH)
        regions = RC.load_regions(REPO / "data" / "candidates" / "corpus_regions.json")
        alignment = PS.load_alignment(REPO / "data" / "candidates" / "corpus_regions.json")
        items, stats = PS.build_set_with_stats(traits, paras, regions, seed=0, sources=sources, alignment=alignment)
        assert items == PS.build_set(traits, paras, regions, seed=0, sources=sources, alignment=alignment)
        singles = [it for it in items if it.kind == "single"]
        pairs = [it for it in items if it.kind == "pair_pole"]
        assert len(singles) == 40 and len(pairs) == 40
        group_of = {m: tuple(g) for g in RC.hiding_groups(traits) for m in g}
        assert len({group_of[it.hidden_stem] for it in items}) == 80
        for it in singles:
            assert group_of[it.hidden_stem] == (it.hidden_stem,) and it.partner_stem is None
        for it in pairs:
            assert traits[it.hidden_stem].pair_partner == it.partner_stem
            assert traits[it.partner_stem].pair_partner == it.hidden_stem
            assert set(group_of[it.hidden_stem]) == {it.hidden_stem, it.partner_stem}
        for it in items:
            t = traits[it.hidden_stem]
            assert it.paraphrase == paras[it.hidden_stem]
            assert sources.get(it.hidden_stem) in (None, PS.paraphrase_source(t.label, t.description))
            assert it.region == regions.get(it.hidden_stem)
            assert isinstance(it.alignment_score, int)
        assert len({it.id for it in items}) == 80
        assert sum(stats["regions"]["single"].values()) == 40
        assert len(stats["regions"]["pair_pole"]) >= 5                  # spread over the regions


# --------------------------------------------------------------------------- the report

def plant_batch(tmp_path):
    """A harness batch over four items: s01 recovered by the overlap call (kept), s02 missed (kept, Sonnet 2),
    p01 recovered by label (covered) with its partner read opposite, p02 recovered by the overlap call (grey) with
    its partner read keep.  Five responses, four parseable."""
    data, traits = toy(tmp_path)
    set_dir = tmp_path / "candidates" / "testing" / "paraphrase_set"
    set_dir.mkdir(parents=True)
    items = [item("zeta", iid="s01"), item("eta", iid="s02"),
             item("delta", kind="pair_pole", partner="epsilon", iid="p01"),
             item("theta", kind="pair_pole", partner="iota", iid="p02")]
    PS.write_set(items, set_dir / PS.SET_NAME)
    answers = [answered(items[0], "unruffled"), answered(items[1], "hushed"),
               answered(items[2], "delta") | {"label_path": True, "reasked": True, "first_label": "delta"},
               answered(items[3], "outspoken")]
    PS.write_answers(answers, set_dir / PS.ANSWERS_NAME)
    with open(set_dir / PS.RESPONSES_NAME, "w") as fh:
        for t in (reply("unruffled"), reply("hushed"), reply("delta"), "garbled", reply("outspoken")):
            fh.write(json.dumps({"item_id": "x", "text": t}) + "\n")
    batch = tmp_path / "candidates" / "recovery" / "rec_testing_paraphrase_set"
    (batch / "seed0").mkdir(parents=True)
    s1 = {"value": 3, "reason": "same"}
    rows = [
        {"key": "unruffled#1", "label": "unruffled", "decision": "new", "stem": "zeta", "how": "overlap",
         "cosine": 0.6, "rank": 1, "sonnet": {"value": 4, "reason": "same"}, "opus": None, "verdict": "cut",
         "recovers": True},
        {"key": "hushed#1", "label": "hushed", "decision": "new", "stem": "eta", "how": "overlap", "cosine": 0.4,
         "rank": 3, "sonnet": {"value": 2, "reason": "each has something the other lacks"}, "opus": None,
         "verdict": "keep", "recovers": False},
        {"key": "delta#1", "label": "delta", "decision": "covered", "stem": "delta", "how": "label",
         "match": {"stem": "delta", "match": "stem"}, "recovers": True},
        {"key": "delta#1", "label": "delta", "decision": "covered", "stem": "epsilon", "how": "overlap",
         "cosine": 0.5, "rank": 2, "sonnet": {"value": "opposite", "reason": "the reverse"}, "opus": None,
         "verdict": "opposite", "recovers": False},
        {"key": "outspoken#1", "label": "outspoken", "decision": "grey", "stem": "theta", "how": "overlap",
         "cosine": 0.5, "rank": 1, "sonnet": s1, "opus": {"value": 3, "reason": "same"}, "verdict": "cut",
         "recovers": True},
        {"key": "outspoken#1", "label": "outspoken", "decision": "grey", "stem": "iota", "how": "overlap",
         "cosine": 0.3, "rank": 4, "sonnet": {"value": 1, "reason": "loosely"}, "opus": None, "verdict": "keep",
         "recovers": False},
    ]
    with open(batch / "seed0" / "matches.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    (batch / "recovery_report.json").write_text(json.dumps({"result": {"seeds": [
        {"seed": 0, "reduced_run": {"batch_id": "rec_testing_paraphrase_set_s0"}}]}}))
    nov = tmp_path / "candidates" / "novelty" / "rec_testing_paraphrase_set_s0"
    nov.mkdir(parents=True)
    dec = {"unruffled#1": "new", "hushed#1": "new", "delta#1": "covered", "outspoken#1": "grey"}
    with open(nov / "results.jsonl", "w") as fh:
        for k, d in dec.items():
            fh.write(json.dumps({"key": k, "novelty": {"decision": d, "covered_by": "kappa" if d == "covered"
                                                       else None}}) + "\n")
    return data, set_dir, batch


class TestReport:
    def test_figures_on_a_planted_batch(self, tmp_path):
        data, set_dir, batch = plant_batch(tmp_path)
        f = PS.report_figures(batch, set_path=set_dir / PS.SET_NAME, answers_path=set_dir / PS.ANSWERS_NAME,
                              data_dir=data, candidates_dir=tmp_path / "candidates")
        assert f["parse"] == {"n_responses": 5, "n_parsed": 4, "rate": 0.8}
        assert f["answers"]["label_path_first"] == 1 and f["answers"]["label_path"] == 1
        s = f["seeds"][0]
        assert s["decisions_from"] == "results.jsonl"
        assert s["concept_recall"] == {"n": 4, "recovered": 3, "share": 0.75}
        assert s["by_decision"]["kept"] == {"n": 3, "recovered": 2, "share": round(2 / 3, 4)}
        assert s["by_decision"]["covered"] == {"n": 1, "recovered": 1, "share": 1.0}
        assert s["by_how"] == {"label": 1, "overlap": 2}
        assert s["pair_recovery"] == {"n": 2, "pole_recovered": 2, "partner_opposite": 1, "both": 1, "share": 0.5}
        assert [m["id"] for m in s["misses"]] == ["s02"]
        assert s["misses"][0]["readings"][0]["sonnet"]["value"] == 2

    def test_markdown_links_are_relative_to_the_set_directory(self, tmp_path):
        data, set_dir, batch = plant_batch(tmp_path)
        md = PS.report(batch, set_path=set_dir / PS.SET_NAME, answers_path=set_dir / PS.ANSWERS_NAME,
                       data_dir=data, candidates_dir=tmp_path / "candidates", report_dir=set_dir)
        assert "75.0%" in md and "3 of 4" in md
        assert "[set.jsonl](./set.jsonl)" in md and "[answers.jsonl](./answers.jsonl)" in md
        assert "(../../recovery/rec_testing_paraphrase_set/recovery_report.md)" in md
        assert "(../../recovery/rec_testing_paraphrase_set/seed0/matches.jsonl)" in md
        assert "(../../../data/traits/instructions/eta.json)" in md
        assert "Sonnet 2" in md and "each has something the other lacks" in md
        for path in re.findall(r"\]\(([^)]+)\)", md):
            assert not path.startswith("/"), path

    def test_the_default_report_directory_is_the_set_directory(self):
        assert PS.SET_DIR == PARAPHRASE_SET_DIR == REPO / "data" / "candidates" / "testing" / "paraphrase_set"


class TestEstimate:
    def test_estimate_is_a_few_cents(self):
        items = [item("zeta", iid=f"s{i:02d}") for i in range(80)]
        est = PS.estimate(items)
        assert 0.004 < est.usd < 0.03
        assert est.lines[0].n_calls == 80 and est.lines[0].model == PS.MODEL
        assert sum(x.n_calls for x in est.lines) > 80                    # the re-ask allowance
