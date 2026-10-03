"""Rubric v2, round 4: the fixes of reports/trait_gap_generation/review_rubric_v2.md
(finding numbers are the coordinator's round-4 list, which follows the review's
sections 3 and 4) and the three changes that follow from the review's questions.
Written before the change; each test failed against a58ffcc for the reason its
name gives, unless its docstring says otherwise."""
import json
import random
import re
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen.filter import FilterItem, FilterResult, FilterRunner
from assistant_axis.judge_pricing import BudgetExceededError
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
REPO = Path(__file__).resolve().parents[2]
RESERVED = Path(__file__).resolve().parent / "data" / "gapgen_reserved_words.txt"


def crow(i, label, **kw):
    base = {"id": i, "label": label, "reason": "A habit of mind shown in how someone talks.",
            "person_senses": [{"sense": "habit of mind", "kind": "trait"}], "trait_senses_equally_obvious": False,
            "judged_sense": "habit of mind", "enactable_in_text": 2, "verdict": "trait", "tags": [],
            "membership_kind": None, "region": "social_interpersonal", "alignment_relevant": False,
            "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}
    base.update(kw)
    return base


def parse(*rows):
    labels = {r["id"]: r["label"] for r in rows}
    return fr.parse_batch(json.dumps({"results": list(rows)}), list(labels), labels=labels)


def vr(label, stratum, verdict="trait", tags=(), stage="classified", holding=None, notes=(), seen=None, gloss="g"):
    f = {"verdict": verdict, "tags": list(tags), "polysemy": bool(notes), "polysemy_notes": list(notes),
         "trait_sense_rank": None}
    meta = {"stratum": stratum}
    if seen is not None:
        meta["seen_in"] = seen
    return FilterResult(key=f"{label}#1", label=label, stage=stage, freq={}, wordnet={}, filter=f, gloss=gloss,
                        holding=holding, meta=meta)


# ---------------------------------------------------------------------------
# 1. figures for rows never seen in development
# ---------------------------------------------------------------------------

class TestUnseenFigures:
    def test_figures_twice(self):
        from assistant_axis.gapgen.filter import validation_figures
        rs = [vr("a", "existing", seen=["m1_pilot"]), vr("b", "existing", "reject", ["relational_only"], seen=[]),
              vr("c", "existing", seen=[]), vr("o1", "oewn_random", seen=["m2rubric_smoke_1"]),
              vr("o2", "oewn_random", "reject", ["relational_only"], seen=[])]
        f = validation_figures(rs)
        assert f["existing"]["n"] == 3 and f["existing"]["correct"] == 2
        u = f["unseen"]
        assert u["existing"]["n"] == 2 and u["existing"]["correct"] == 1
        assert u["oewn_random"]["n"] == 1 and u["oewn_random"]["trait"] == 0
        assert f["n_seen_in_development"] == 2

    def test_development_seen_reads_recorded_runs(self, tmp_path):
        from assistant_axis.gapgen.filter import development_seen
        d = tmp_path / "filter" / "m1_pilot"
        d.mkdir(parents=True)
        (d / "results.jsonl").write_text(json.dumps({"key": "stubborn#1", "label": "stubborn"}) + "\n")
        p = tmp_path / "plain_reading" / "dev"
        p.mkdir(parents=True)
        (p / "results.jsonl").write_text(json.dumps({"key": "calm#same", "label": "calm"}) + "\n")
        (tmp_path / "filter" / "m1_validation").mkdir()
        (tmp_path / "filter" / "m1_validation" / "results.jsonl").write_text(
            json.dumps({"key": "vain#1", "label": "vain"}) + "\n")
        seen = development_seen(tmp_path, exclude=("m1_validation",))
        assert seen == {"stubborn#1": ["filter/m1_pilot"], "calm#1": ["plain_reading/dev"]}


# ---------------------------------------------------------------------------
# 2. obvious_sense_not_trait
# ---------------------------------------------------------------------------

class TestObviousSenseNotTrait:
    def test_note_fires(self):
        rows, errs = parse(crow(1, "noble", person_senses=[{"sense": "high-born", "kind": "role"},
                                                           {"sense": "high-minded", "kind": "trait"}]))
        assert errs == {}
        assert fr.derive_notes(rows[1]) == ["obvious_sense_not_trait"]
        assert fr.derive_polysemy(rows[1]) is True

    def test_tagged_state_row_does_not_fire(self):
        row = {"verdict": "tagged", "person_senses": [{"sense": "s", "kind": "state"}, {"sense": "t", "kind": "trait"}]}
        assert fr.derive_notes(row) == []

    def test_figures_agree_with_the_flag(self):
        from assistant_axis.gapgen.filter import validation_figures
        r = vr("r1", "rejects")
        r.filter.update(trait_sense_rank=2, polysemy=False, polysemy_notes=[])  # rank alone no longer counts
        f = validation_figures([r, vr("r2", "rejects", notes=["obvious_sense_not_trait"])])
        assert f["rejects"]["flagged_labels"] == ["r2"]


# ---------------------------------------------------------------------------
# 3. tags that do not fit are kept, not asked again
# ---------------------------------------------------------------------------

class TestTagsKept:
    def test_mismatched_tags_accepted_with_disagreement(self):
        rows, errs = parse(crow(1, "a", verdict="tagged", tags=["membership"], membership_kind="family"),
                           crow(2, "b", verdict="reject", tags=["physical"], region=None, gloss=None,
                                judged_sense=None))
        assert errs == {}
        assert rows[1]["tag_disagreement"] is True and rows[2]["tag_disagreement"] is True

    def test_no_tag_still_fails(self):
        rows, errs = parse(crow(1, "a", verdict="tagged", tags=[]), crow(2, "b", verdict="reject", tags=[],
                                                                         region=None, gloss=None))
        assert rows == {} and set(errs) == {1, 2}

    def test_first_answer_kept_and_second_opinion_runs(self):
        n = {"haiku": 0}

        def responder(kw):
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            if kw["model"] == HAIKU:
                n["haiku"] += 1
                return json.dumps({"results": [crow(it["id"], it["label"], verdict="tagged", tags=["membership"],
                                                    membership_kind="family") for it in items]})
            return json.dumps({"results": [crow(it["id"], it["label"], tags=["membership"],
                                                membership_kind="family") for it in items]})
        r = FilterRunner(client=FakeAsyncAnthropic(responder), batch_id="b", model=HAIKU, second_model=SONNET,
                         second_opinion_frac=0.0, probe=False, plain_reading=False, zipf_fn=lambda w: 4.0,
                         wordnet=False)
        out = r.run([FilterItem(key="absentee#1", label="absentee")])[0]
        assert n["haiku"] == 1  # not asked again
        assert out.filter["verdict"] == "tagged" and out.filter["tag_disagreement"] is True
        assert out.filter["second_opinion"]["verdict"] == "trait"
        assert r.stats["n_llm_ok_first_pass"] == 1


# ---------------------------------------------------------------------------
# 4. a rejected label is a miss whatever its tags
# ---------------------------------------------------------------------------

def test_rejected_label_is_a_miss():
    from assistant_axis.gapgen.filter import existing_label_outcome
    assert existing_label_outcome(vr("a", "existing", "reject", ["physical", "relational_only"])) == "reject"
    assert existing_label_outcome(vr("b", "existing", "reject", ["state", "too_rare"])) == "floor"
    assert existing_label_outcome(vr("c", "existing", "reject", ["membership", "not_a_word"])) == "reject"
    assert existing_label_outcome(vr("d", "existing", "tagged", ["state"])) == "correct"


# ---------------------------------------------------------------------------
# 5. classifier version 4
# ---------------------------------------------------------------------------

def _examples():
    """Parse every example line of the classifier prompt into a row, using
    the schema's own field names (the prompt writes ``field value``; a
    person sense is ``text (kind)``)."""
    sp = fr.SYSTEM_PROMPT
    ex = sp[sp.index("## Examples"):sp.index("## Regions")].replace("\\\n", " ")
    items = re.split(r"\n- ", ex)[1:]
    out = []
    for i, item in enumerate(items, 1):
        item = " ".join(item.split())
        m = re.match(r'"(?P<label>[^"]+)": (?P<reason>.+?); person_senses \[(?P<ps>[^\]]*)\]; (?P<rest>.*)$', item)
        assert m, item[:60]
        row = {"id": i, "label": m["label"], "reason": m["reason"], "person_senses": []}
        if m["ps"].strip():
            for s in m["ps"].split(", "):
                sm = re.match(r"(.+) \((\w+)\)$", s.strip())
                assert sm, s
                row["person_senses"].append({"sense": sm[1], "kind": sm[2]})
        for part in re.split(r"; (?=[a-z_]+ )", m["rest"]):
            key, _, val = part.partition(" ")
            val = val.strip()
            if val == "null":
                v = None
            elif val in ("true", "false"):
                v = val == "true"
            elif val.startswith("["):
                v = [t for t in val.strip("[]").split(", ") if t]
            elif val.startswith('"'):
                v = val.strip('"')
            else:
                try:
                    v = float(val) if "." in val else int(val)
                except ValueError:
                    v = val
            row[key] = v
        out.append(row)
    return out


class TestClassifierV4:
    def test_version_and_pin(self):
        from assistant_axis.gapgen import rubric_versions
        # 6 since 2026-10-02 (the "soft" example reworded; 5 is the split's number); v4's text stays pinned
        assert fr.TRAITHOOD_RUBRIC_VERSION == 6 and 5 not in rubric_versions.HISTORY["classifier"]
        assert rubric_versions.HISTORY["classifier"][4].startswith("51854ac5")
        assert rubric_versions.mismatches() == []

    def test_sense_kinds(self):
        assert fr.PERSON_SENSE_KINDS == ("trait", "state", "physical", "role")
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "every membership is a trait sense" in sp
        for gone in ("circumstance (a situation", "status (a rank", "bodily ("):
            assert gone not in sp

    def test_body_said_once_plainly(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert ("A lasting feature of the body is physical; a passing condition of the body is a state. "
                "Hungry is a state. Freckled is physical.") in sp

    def test_one_test_for_the_main_reading(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "commoner in ordinary use" not in sp
        assert 'the one a reader would take from the bare instruction "You are <word>."' in sp

    def test_judged_sense_field(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        schema = sp[sp.index('{"results"'):]
        assert schema.index('"trait_senses_equally_obvious"') < schema.index('"judged_sense"') < schema.index('"verdict"')
        rows, errs = parse(crow(1, "a", judged_sense=None), crow(2, "b", verdict="reject", tags=["not_a_word"],
                                                                 region=None, gloss=None, judged_sense=None))
        # round 5 (review_rubric_v2_fixes.md defect 1): a null judged_sense on a trait
        # row is repaired from the first listed sense, not refused
        assert errs == {} and rows[1]["judged_sense"] == "habit of mind"
        assert rows[1]["validator_repairs"] == ["judged_sense_from_first_sense"]
        assert rows[2]["judged_sense"] is None
        rows, _ = parse(crow(3, "c"))
        assert rows[3]["judged_sense"] == "habit of mind"

    def test_no_empty_threat(self):
        assert "shorter glosses are not accepted" not in fr.SYSTEM_PROMPT

    def test_every_example_passes_the_validator(self):
        ex = _examples()
        assert len(ex) == len(fr.EXAMPLE_WORDS)
        for row in ex:
            for field in ("person_senses", "trait_senses_equally_obvious", "judged_sense", "enactable_in_text",
                          "verdict", "tags", "membership_kind", "region", "alignment_relevant", "gloss",
                          "confidence"):
                assert field in row, (row["label"], field)
            ok, err = fr.validate_row(row, expected_label=row["label"])
            assert ok is not None, (row["label"], err)
            assert ok["tag_disagreement"] is False, row["label"]

    def test_awesome_has_no_trait_sense(self):
        aw = next(r for r in _examples() if r["label"] == "awesome")
        assert all(s["kind"] != "trait" for s in aw["person_senses"])


# ---------------------------------------------------------------------------
# 5, 6. hygiene over every word of every prompt, from tracked files only
# ---------------------------------------------------------------------------

def _all_prompts():
    from assistant_axis.gapgen import plain_reading as pr
    from assistant_axis.gapgen import states_pass as sp
    return {"classifier": fr.SYSTEM_PROMPT, "probe": fr.DEFINE_PROBE_PROMPT, "plain_reading": pr.READING_PROMPT,
            "comparison": pr.COMPARISON_PROMPT, "states_queue": sp.QUEUE_PROMPT, "states_corpus": sp.CORPUS_PROMPT}


def _forbidden():
    import data_analysis.seed_entities as se
    data = REPO / "data"
    q = se.load_queue(data / "seed_queue.json")
    stems = set().union(*se.corpus_stems(data).values())
    stems |= {e.get("stem") for e in q["entries"]}
    stems |= {normalize_to_file_name(e["label"]) for e in q["entries"] if e.get("label")}
    val = data / "candidates" / "validation" / "m1_validation.jsonl"
    stems |= {normalize_to_file_name(json.loads(x)["surface"]) for x in val.read_text().splitlines() if x.strip()}
    return {s for s in stems if s}


def test_reserved_word_list_is_tracked_data_not_the_working_files():
    words = RESERVED.read_text(encoding="utf-8").split()
    assert len(words) > 1000 and words == sorted(words)
    # no test builds a path to either working file (a quoted path component)
    opened = re.compile(r"""["'](?:decisions_m1\.md|probe_you_are_x)["']""")
    for p in (REPO / "assistant_axis" / "tests").glob("test_*.py"):
        if p.name == Path(__file__).name:
            continue
        assert not opened.search(p.read_text(encoding="utf-8")), p.name


def test_example_words_avoid_reserved_words():
    from assistant_axis.gapgen import plain_reading as pr
    from assistant_axis.gapgen import states_pass as sp
    reserved = set(RESERVED.read_text(encoding="utf-8").split())
    words = (fr.EXAMPLE_WORDS + fr.MENTIONED_WORDS + sp.EXAMPLE_WORDS + sp.SUGGESTED_NAMES + pr.EXAMPLE_WORDS)
    # single words and hyphenated compounds are checked whole; multiword phrases are checked as phrases
    # against the corpus, the queue and the validation file only (a token list cannot hold phrases)
    assert [w for w in words if " " not in w and w.lower() in reserved] == []


def test_no_corpus_queue_or_validation_word_anywhere_in_a_prompt():
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
    bad = {}
    forbidden = _forbidden()
    for name, text in _all_prompts().items():
        hits = sorted(w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden
                      and w not in PROSE_ALLOWED)
        if hits:
            bad[name] = hits
    assert bad == {}


def test_prose_allowlist_is_never_an_example():
    from assistant_axis.gapgen import states_pass as sp
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED
    for name, text in _all_prompts().items():
        for w in PROSE_ALLOWED:
            assert f'- "{w}":' not in text, (name, w)  # an example line opens with - "word":
    assert not set(PROSE_ALLOWED) & {w.lower() for w in fr.EXAMPLE_WORDS + sp.EXAMPLE_WORDS}


# ---------------------------------------------------------------------------
# 7. a stop during the reading stage keeps the readings; budget stops in both runners
# ---------------------------------------------------------------------------

def reading_resp(kw):
    if not kw.get("system"):
        return make_response("Plain reading.", input_tokens=100000, output_tokens=10)  # $0.10 on Haiku
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    return json.dumps({"results": [{"id": it["id"], "label": it["label"], "reason": "r", "relation": "same",
                                    "confidence": 0.9} for it in items]})


class TestBudgetStops:
    def test_plain_reading_stop_keeps_readings(self):
        from assistant_axis.gapgen import plain_reading as pr
        from assistant_axis.gapgen.cost import GuardedUsage
        r = pr.PlainReadingRunner(client=FakeAsyncAnthropic(reading_resp), batch_id="b", reading_model=HAIKU,
                                  compare_model=SONNET, usage=GuardedUsage(budget_usd=0.15), concurrency=1)
        items = [pr.ReadingItem(key=f"w{i}#1", label=f"w{i}", intended="i") for i in range(4)]
        with pytest.raises(BudgetExceededError):
            r.run(items)
        got = [k for k, v in r.results.items() if v.reading]
        assert len(got) == 2 and len(r.responses) == 2  # the one that crossed the cap is kept too

    def test_filter_stop_in_reading_stage_keeps_readings(self):
        from assistant_axis.gapgen.cost import GuardedUsage

        def resp(kw):
            if kw.get("system") and "person_senses" in system_text(kw):
                items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
                return make_response(json.dumps({"results": [crow(it["id"], it["label"]) for it in items]}),
                                     input_tokens=10, output_tokens=10)
            return reading_resp(kw)
        r = FilterRunner(client=FakeAsyncAnthropic(resp), batch_id="b", model=HAIKU, second_model=None,
                         second_opinion=False, probe=False, zipf_fn=lambda w: 4.0, wordnet=False, concurrency=1,
                         usage=GuardedUsage(budget_usd=0.15))
        with pytest.raises(BudgetExceededError):
            r.run([FilterItem(key=f"w{i}#1", label=f"w{i}", intended_sense="meant") for i in range(4)])
        kept = [x for x in r.results.values() if (x.filter or {}).get("plain_reading")]
        assert len(kept) == 2

    def test_states_pass_stop_keeps_judged_rows(self):
        from assistant_axis.gapgen import states_pass as sp
        from assistant_axis.gapgen.cost import GuardedUsage

        def resp(kw):
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            body = {"results": [{"id": it["id"], "label": it["label"], "reason": "r", "plausible": False,
                                 "name_fits": None, "suggested_name": None, "gloss": None, "confidence": 0.9}
                                for it in items]}
            return make_response(json.dumps(body), input_tokens=100000, output_tokens=10)
        r = sp.StatesPassRunner(client=FakeAsyncAnthropic(resp), batch_id="b", mode="queue", model=HAIKU,
                                usage=GuardedUsage(budget_usd=0.05), batch_size=2, concurrency=1)
        with pytest.raises(BudgetExceededError):
            r.run([sp.StatesItem(key=f"s{i}#1", label=f"s{i}", text="t") for i in range(6)])
        assert sum(1 for x in r.results.values() if x.stage == "judged") == 2
        assert len(r.responses) == 1


# ---------------------------------------------------------------------------
# 8. corpus_regions.json
# ---------------------------------------------------------------------------

def test_corpus_regions_from_a_run(tmp_path, capsys):
    from data_analysis.gap_generation import gap_registry
    data = tmp_path / "data" / "traits" / "instructions"
    data.mkdir(parents=True)
    for s in ("calm", "stubborn", "rare_word"):
        (data / f"{s}.json").write_text("{}")
    run = tmp_path / "run"
    run.mkdir()
    rows = [{"key": "calm#1", "label": "calm", "stage": "classified", "meta": {"stratum": "existing"},
             "filter": {"verdict": "trait", "region": "emotional_temperament", "alignment_relevant": False}},
            {"key": "stubborn#1", "label": "stubborn", "stage": "classified", "meta": {"stratum": "existing"},
             "filter": {"verdict": "trait", "region": "moral_stance", "alignment_relevant": True}},
            {"key": "rare_word#1", "label": "rare word", "stage": "hard_reject", "meta": {"stratum": "existing"},
             "filter": {"verdict": "reject", "region": None, "alignment_relevant": False}},
            {"key": "zz#1", "label": "zz", "stage": "classified", "meta": {"stratum": "oewn_random"},
             "filter": {"verdict": "trait", "region": "moral_stance", "alignment_relevant": False}}]
    (run / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (run / "run.json").write_text(json.dumps({"batch_id": "m1_validation"}))
    out = tmp_path / "corpus_regions.json"
    assert gap_registry.main(["--data-dir", str(tmp_path / "data"), "corpus-regions", "--from-filter", str(run),
                              "--out", str(out)]) == 0
    obj = json.loads(out.read_text())
    reg = obj.get("result", obj)
    assert set(reg) == {"calm", "stubborn", "rare_word"}
    assert reg["stubborn"] == {"label": "stubborn", "region": "moral_stance", "alignment_relevant": True,
                               "verdict": "trait", "batch_id": "m1_validation"}
    assert reg["rare_word"]["region"] is None


def test_corpus_regions_merge_runs_and_follow_renames(tmp_path, capsys):
    """2026-10-02 (merge with the main line): a renamed trait takes its old stem's row, unless a later
    run has the trait itself (a description that changed sense is judged again); later runs win."""
    from assistant_axis.entity_id import clear_corpus_display_cache
    from data_analysis.gap_generation import gap_registry
    data = tmp_path / "data" / "traits" / "instructions"
    data.mkdir(parents=True)
    files = {"calm": {}, "lenient": {}, "strict": {"renamed_from": {"stem": "tough", "date": "2026-10-02"}},
             "dull": {"renamed_from": {"stem": "bland", "date": "2026-10-02"}}}
    for s, d in files.items():
        (data / f"{s}.json").write_text(json.dumps(d))
    clear_corpus_display_cache()

    def row(label, region):
        return {"key": f"{label}#1", "label": label, "stage": "classified", "meta": {"stratum": "existing"},
                "filter": {"verdict": "trait", "region": region, "alignment_relevant": False}}
    runs = []
    for name, rows in (("old_run", [row("calm", "emotional_temperament"), row("tough", "social_interpersonal"),
                                    row("bland", "communication_style")]),
                       ("new_run", [row("dull", "cognitive_epistemic"), row("lenient", "moral_stance")])):
        d = tmp_path / name
        d.mkdir()
        (d / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (d / "run.json").write_text(json.dumps({"batch_id": name}))
        runs += ["--from-filter", str(d)]
    out = tmp_path / "corpus_regions.json"
    assert gap_registry.main(["--data-dir", str(tmp_path / "data"), "corpus-regions", *runs, "--out", str(out)]) == 0
    obj = json.loads(out.read_text())
    reg = obj["result"]
    assert set(reg) == set(files)
    assert reg["strict"] == {"label": "tough", "region": "social_interpersonal", "alignment_relevant": False,
                             "verdict": "trait", "batch_id": "old_run", "renamed_from": "tough"}
    assert reg["dull"]["batch_id"] == "new_run" and "renamed_from" not in reg["dull"]
    assert reg["calm"]["batch_id"] == "old_run" and reg["lenient"]["batch_id"] == "new_run"
    assert [i["dep_key"] for i in obj["_provenance"]["inputs"]] == ["filter_results_old_run", "filter_results_new_run"]
    assert "tough -> strict" in capsys.readouterr().out
    clear_corpus_display_cache()


# ---------------------------------------------------------------------------
# 9. every recorded version and hash is pinned
# ---------------------------------------------------------------------------

#: Recorded runs the pin table does not cover, with the reason (review section 8).
UNPINNED = {
    "filter/m1_pilot": "rubric v1; records no prompt hash",
    "filter/m1_pilot_v0_parse_bug": "rubric v1; records no prompt hash",
    "filter/m1_smoke": "rubric v1; records no prompt hash",
    "filter/m1_smoke2": "rubric v1; records no prompt hash",
}
#: Runs whose classifier prompt was withdrawn (each carries WITHDRAWN_PROMPT.md).
WITHDRAWN_CLASSIFIER = {"filter/m2rubric_smoke_1", "filter/m2rubric_smoke_2", "filter/m2rubric_smoke_3"}


def test_every_recorded_version_and_hash_is_pinned():
    from assistant_axis.gapgen.rubric_versions import HISTORY
    problems = []
    runs = sorted((REPO / "data" / "candidates").glob("*/*/run.json"))
    assert runs
    for rj in runs:
        name = str(rj.parent.relative_to(REPO / "data" / "candidates"))
        if name in UNPINNED or ".bak." in name:
            continue
        d = json.loads(rj.read_text())
        ps = d.get("prompt_sha256")
        checks = []  # (prompt, version or None, sha)
        if name.startswith("filter/") and d.get("pipeline") == "split":
            # the split filter: its eight prompts are pinned in rubrics/versions.json; the probe and
            # the comparison it also sends are in HISTORY (recorded in run.json since 2026-09-29, after
            # split_pilot_live, whose filter blocks carry them instead)
            from assistant_axis.gapgen import split_rubrics
            split_pins = split_rubrics.read_versions()["prompts"]
            for prompt, version in d["step_versions"].items():
                pinned = {r["version"]: r["sha256"] for r in split_pins.get(prompt, [])}
                if pinned.get(version) != ps.get(prompt):
                    problems.append((name, f"split.{prompt}", version, (ps.get(prompt) or "")[:12]))
            if "probe" in ps:
                checks.append(("probe", d.get("probe_rubric_version"), ps["probe"]))
            if "comparison" in ps:
                checks.append(("comparison", None, ps["comparison"]))
        elif name.startswith("filter/"):
            if name not in WITHDRAWN_CLASSIFIER:
                checks.append(("classifier", d.get("rubric_version"), ps.get("classifier")))
            checks.append(("probe", d.get("probe_rubric_version"), ps.get("probe")))
            for k in ("plain_reading", "comparison"):
                if k in ps:
                    checks.append((k, None, ps[k]))
        elif name.startswith("overlap_test/"):
            # the M3 overlap rubric test (2026-10-03): its two rubrics are pinned in rubrics/versions.json
            from assistant_axis.gapgen import split_rubrics
            pins = split_rubrics.read_versions()["prompts"]
            for prompt, version in d["rubric_versions"].items():
                pinned = {r["version"]: r["sha256"] for r in pins.get(prompt, [])}
                if pinned.get(version) != ps.get(prompt):
                    problems.append((name, prompt, version, (ps.get(prompt) or "")[:12]))
        elif name.startswith("plain_reading/"):
            for k in ("plain_reading", "comparison"):
                checks.append((k, d["versions"][k], ps[k]))
        elif name.startswith("states_pass/"):
            checks.append((f"states_{d['mode']}", d.get("rubric_version"), ps))
        for prompt, version, sha in checks:
            pins = HISTORY.get(prompt, {})
            if version is None:
                ok = sha in pins.values()
            else:
                ok = pins.get(version) == sha
            if not ok:
                problems.append((name, prompt, version, (sha or "")[:12]))
    assert problems == []


def test_withdrawn_runs_are_marked():
    for name in WITHDRAWN_CLASSIFIER:
        assert (REPO / "data" / "candidates" / name / "WITHDRAWN_PROMPT.md").exists()


# ---------------------------------------------------------------------------
# 10, 11. stale docstrings; superseded refusals
# ---------------------------------------------------------------------------

def test_docstrings_name_the_current_constants():
    import assistant_axis.gapgen.filter as flt
    from data_analysis.gap_generation import traithood_filter
    for doc in (flt.__doc__, traithood_filter.__doc__):
        assert "2.0" not in doc and "0.6" not in doc


def test_superseded_refusal_quotes_the_decision_without_claiming_none():
    from assistant_axis.gapgen.promote import turned_down_reason
    e = {"status": "superseded", "decision": "2026-09-17: speculative is paired with empirical"}
    msg = turned_down_reason(e)
    assert "speculative is paired with empirical" in msg and "no replacing label" not in msg
    assert "replaced by extremist" in turned_down_reason({"status": "superseded",
                                                          "decision": "superseded by extremist (part 2)"})


# ---------------------------------------------------------------------------
# the three changes that follow from the review's questions
# ---------------------------------------------------------------------------

class TestReadingRelated:
    def test_related_raises_its_own_note(self):
        from assistant_axis.gapgen import plain_reading as pr
        assert pr.notes_for("related") == ["reading_related"]
        assert pr.notes_for("different") == ["overshadowed"]
        row = {"verdict": "trait", "person_senses": [{"sense": "x", "kind": "trait"}],
               "comparison": {"relation": "related"}}
        assert fr.derive_notes(row) == ["reading_related"]
        assert "reading_related" in fr.POLYSEMY_NOTES and "obvious_sense_not_trait" in fr.POLYSEMY_NOTES

    def test_heldout_figure_still_counts_overshadowed_only(self):
        from assistant_axis.gapgen import plain_reading as pr
        f = pr.heldout_figure([{"label": "a", "notes": ["reading_related"]}, {"label": "b", "notes": ["overshadowed"]}])
        assert f["overshadowed"] == 1


def _cmp_resp(kw):
    if not kw.get("system"):
        word = re.search(r'"You are (.+?)\."', user_text(kw)).group(1)
        return f"Reads {word}."
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    rel = {"calm": ("same", 0.9), "stubborn": ("different", 0.8), "vain": ("related", 0.6), "shy": ("related", 0.9)}
    return json.dumps({"results": [{"id": it["id"], "label": it["label"], "reason": "r",
                                    "relation": rel[it["label"]][0], "confidence": rel[it["label"]][1]}
                                   for it in items]})


def test_corpus_comparison_raises_no_flag_and_lists_everything(tmp_path, monkeypatch):
    import anthropic
    import dotenv

    from data_analysis.gap_generation import plain_reading as cli
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **kw: FakeAsyncAnthropic(_cmp_resp))
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc")
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    d = tmp_path / "data" / "traits" / "instructions"
    d.mkdir(parents=True)
    for s in ("calm", "stubborn", "vain", "shy"):
        (d / f"{s}.json").write_text(json.dumps({"positive_label": s, "description": f"This means being {s}."}))
    cand = tmp_path / "cand"
    assert cli.main(["--batch-id", "c", "--corpus", "--data-dir", str(tmp_path / "data"), "--out-root", str(cand)]) == 0
    out = cand / "plain_reading" / "c"
    res = [json.loads(x) for x in (out / "results.jsonl").read_text().splitlines()]
    assert all(r["notes"] == [] for r in res)
    s = json.loads((out / "summary.json").read_text())["result"]
    assert s["overshadowed"] == [] and s["flags_raised"] is False
    listing = (out / "listing.md").read_text()
    order = [lb for lb in ("stubborn", "shy", "vain", "calm") if f"| {lb} |" in listing]
    assert order == ["stubborn", "shy", "vain", "calm"]
    assert [listing.index(f"| {lb} |") for lb in order] == sorted(listing.index(f"| {lb} |") for lb in order)


class TestStatesPromotionNeedsConfirmedName:
    PASS_OK = {"mode": "queue", "plausible": True, "name_fits": False, "suggested_name": "sulky",
               "suggested_stem": "sulky", "gloss": "This means falling into long silent sulks whenever crossed.",
               "reason": "People are often prone to sulking.", "rubric_version": 2}

    def _held(self):
        from assistant_axis.gapgen.registry import new_record
        r = new_record("sulking", sources=[{"generator": "g", "run_id": "r"}])
        r.update(filter={"verdict": "tagged", "tags": ["state"], "reason": "r"}, gloss="g", holding="states",
                 states_pass=dict(self.PASS_OK))
        return {"sulking#1": r}

    @pytest.fixture
    def data_dir(self, tmp_path):
        d = tmp_path / "data"
        for et in ("traits", "roles"):
            (d / et / "instructions").mkdir(parents=True)
        return d

    def test_refused_without_a_confirmed_name(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        rep = promote(self._held(), {"_meta": {}, "entries": []}, ["sulking#1"], data_dir=data_dir)
        assert rep.promoted == [] and "confirm" in rep.refused["sulking#1"]

    def test_promoted_under_the_confirmed_name(self, data_dir):
        from assistant_axis.gapgen.promote import promote
        q = {"_meta": {}, "entries": []}
        rep = promote(self._held(), q, ["sulking#1"], data_dir=data_dir, dry_run=False,
                      confirmed_state_names={"sulking#1": "prone to sulking"})
        assert rep.promoted == ["sulking#1"] and q["entries"][-1]["stem"] == "prone_to_sulking"
        assert "confirmed" in q["entries"][-1]["description_notes"]

    def test_cli_flag(self, tmp_path, data_dir, capsys):
        from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
        from data_analysis.gap_generation import gap_registry
        reg = tmp_path / "r.jsonl"
        submit_candidates([Candidate(surface="sulking", generator="g", run_id="r")], registry_path=reg)
        Registry(reg).update("sulking#1", {"holding": "states", "gloss": "g", "states_pass": dict(self.PASS_OK),
                                           "filter": {"verdict": "tagged", "tags": ["state"], "reason": "r"}})
        queue = tmp_path / "q.json"
        queue.write_text(json.dumps({"_meta": {}, "entries": []}))
        assert gap_registry.main(["--registry", str(reg), "--data-dir", str(data_dir), "promote", "--keys",
                                  "sulking#1", "--queue", str(queue), "--dry-run",
                                  "--confirm-state-name", "sulking#1=sulky"]) == 0
        assert "WOULD PROMOTE sulking#1 -> sulky" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# random adjectives that passed: a sample for Roger's marks
# ---------------------------------------------------------------------------

def test_validation_cli_marks_seen_rows_and_writes_the_marks_table(tmp_path, monkeypatch):
    """Written after the CLI change (not seen failing first)."""
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
    cand = tmp_path / "cand"
    old = cand / "filter" / "m1_pilot"
    old.mkdir(parents=True)
    (old / "results.jsonl").write_text(json.dumps({"key": "stubborn#1", "label": "stubborn"}) + "\n")
    val = tmp_path / "v.jsonl"
    val.write_text("".join(json.dumps({"surface": w, "stratum": s}) + "\n"
                           for w, s in (("stubborn", "existing"), ("vain", "existing"), ("mossy", "oewn_random"))))
    assert traithood_filter.main(["--pipeline", "single", "--batch-id", "v", "--validation-file", str(val), "--out-root", str(cand),
                                  "--no-second-opinion", "--no-probe"]) == 0
    d = cand / "filter" / "v"
    res = {json.loads(x)["key"]: json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()}
    assert res["stubborn#1"]["meta"]["seen_in"] == ["filter/m1_pilot"] and res["vain#1"]["meta"]["seen_in"] == []
    vf = json.loads((d / "summary.json").read_text())["result"]["validation_figures"]
    assert vf["existing"]["n"] == 2 and vf["unseen"]["existing"]["n"] == 1 and vf["n_seen_in_development"] == 1
    assert "| mossy |" in (d / "random_traits_for_marks.md").read_text()


def test_random_trait_sample_for_marks():
    from assistant_axis.gapgen.filter import random_trait_sample, validation_figures
    rs = [vr(f"o{i}", "oewn_random", "trait" if i % 2 else "reject", gloss=f"gloss {i}") for i in range(140)]
    s = random_trait_sample(rs, n=50, seed=0)
    assert len(s) == 50 and all(int(x["label"][1:]) % 2 for x in s)
    assert s == random_trait_sample(list(reversed(rs)), n=50, seed=0)  # by fixed seed, order-independent
    f = validation_figures(rs)
    assert f["oewn_random"]["sample_for_marks"] == s


def test_random_trait_sample_for_marks_draws_unseen_rows_only():
    """Seen rows are left out of the marks sample while 50 unseen rows passed
    (m1_validation: 22 of 50 had been seen); fewer, and it falls back."""
    from assistant_axis.gapgen.filter import random_trait_sample_for_marks, validation_figures
    # 60 unseen passing rows, 30 seen passing rows (seen_in non-empty), one with seen_in == []
    rs = [vr(f"u{i:02d}", "oewn_random", "trait", seen=[] if i == 0 else None) for i in range(60)]
    rs += [vr(f"s{i:02d}", "oewn_random", "trait", seen=["filter/m1_pilot"]) for i in range(30)]
    rs += [vr(f"x{i:02d}", "oewn_random", "reject") for i in range(10)]
    s, unseen_only = random_trait_sample_for_marks(rs, n=50, seed=0)
    assert unseen_only is True and len(s) == 50
    assert all(x["label"].startswith("u") for x in s)
    assert [x["key"] for x in s] == sorted(x["key"] for x in s)  # alphabetical listing
    s2, _ = random_trait_sample_for_marks(list(reversed(rs)), n=50, seed=0)
    assert s2 == s  # fixed seed, order-independent
    f = validation_figures(rs)
    assert f["oewn_random"]["sample_for_marks"] == s and f["oewn_random"]["sample_for_marks_unseen_only"] is True

    # fewer than 50 unseen rows passed: fall back to all passing rows, and say so
    few = [r for r in rs if not r.label.startswith("u") or int(r.label[1:]) < 40]
    s3, unseen_only3 = random_trait_sample_for_marks(few, n=50, seed=0)
    assert unseen_only3 is False and len(s3) == 50
    assert any(x["label"].startswith("s") for x in s3)
    assert validation_figures(few)["oewn_random"]["sample_for_marks_unseen_only"] is False


def test_marks_table_header_names_the_pool():
    from data_analysis.gap_generation.traithood_filter import marks_table
    sample = [{"label": "mossy", "key": "mossy#1", "gloss": "a|b"}]
    assert "never seen in development" in marks_table(sample, True)
    assert "fewer than 50 unseen" in marks_table(sample, False)
    assert "| mossy | a\\|b |  |" in marks_table(sample)
