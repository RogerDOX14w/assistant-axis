"""The label-fit check (``assistant_axis/gapgen/label_fit.py``, ``data_analysis/gap_generation/label_fit.py``): the
parser, the majority and the union, the user turn's variants, the senses, the cosine screen, the corrected candidates,
the marks sheet and its confusion table, the pinned prompt and its word hygiene, and both commands end to end with
the repository's fake Anthropic client (no network)."""
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from assistant_axis.gapgen import label_fit as LF
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.censuses.glosshint import Sense
from assistant_axis.gapgen.registry import CANDIDATE_FIELDS, Candidate, Registry, read_candidates, submit_candidates
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text


def ans(verdict, better=None, reason="Because."):
    return json.dumps({"reason": reason, "verdict": verdict, "better_label": better})


# --------------------------------------------------------------------------- parser

class TestParse:
    def test_plain_object(self):
        a, err, notes = LF.parse_answer(ans("secondary_sense", "honor-hungry"))
        assert err is None and a == {"reason": "Because.", "verdict": "secondary_sense",
                                     "better_label": "honor-hungry"} and notes == []

    def test_prose_before_the_object_is_accepted(self):
        a, err, notes = LF.parse_answer("Grasping usually means greedy.\n" + ans("not_a_sense", "vainglorious"))
        assert err is None and a["verdict"] == "not_a_sense" and notes == ["prose before the object"]

    def test_code_fence_is_accepted(self):
        a, err, notes = LF.parse_answer("```json\n" + ans("fits") + "\n```")
        assert err is None and notes == ["code fence removed"]

    def test_text_after_the_object_is_refused(self):
        a, err, _ = LF.parse_answer(ans("fits") + "\nHope this helps.")
        assert a is None and err.startswith("not_one_object")

    def test_refusal_is_a_failed_call_whatever_the_text(self):
        a, err, _ = LF.parse_answer(ans("fits"), stop_reason="refusal")
        assert a is None and err.startswith("refusal")
        assert LF.parse_answer(None)[1].startswith("no_response") and LF.parse_answer("  ")[1].startswith("empty")

    def test_better_label_rules(self):
        a, err, notes = LF.parse_answer(ans("fits", "something"))
        assert a["better_label"] is None and "better_label given on fits: dropped" in notes
        assert LF.parse_answer(ans("not_a_sense"))[1].startswith("bad_value: better_label")
        assert LF.parse_answer(ans("not_a_sense", "null"))[1].startswith("bad_value: better_label")
        a, _, notes = LF.parse_answer(ans("not_a_sense", "one two three four five"))
        assert a and "better_label longer than four words" in notes

    def test_verdict_normalised_and_bad_values(self):
        a, _, notes = LF.parse_answer(ans("Secondary sense", "x"))
        assert a["verdict"] == "secondary_sense" and "verdict normalised" in notes
        assert LF.parse_answer(ans("maybe"))[1].startswith("bad_value: verdict")
        assert LF.parse_answer('{"verdict": "fits"}')[1] == "missing_key: reason"
        assert LF.parse_answer("[1, 2]")[1].startswith("not_one_object")


# --------------------------------------------------------------------------- combining

def P(verdict, better=None):
    return {"reason": "r", "verdict": verdict, "better_label": better}


class TestCombine:
    def test_majority_fits(self):
        c = LF.combine([P("fits"), P("fits"), P("secondary_sense", "honor-hungry")], label="grasping")
        assert c["decision"] == "fits" and c["proposals"] == [] and c["n_answered"] == 3

    def test_union_of_proposals_with_support(self):
        c = LF.combine([P("not_a_sense", "vainglorious"), P("secondary_sense", "honor-hungry"),
                        P("not_a_sense", "Vainglorious")], label="grasping")
        assert c["decision"] == "relabel" and c["verdict"] == "not_a_sense"
        assert [(p["label"], p["support"]) for p in c["proposals"]] == [("vainglorious", 2), ("honor-hungry", 1)]

    def test_a_tie_does_not_fit(self):
        c = LF.combine([P("fits"), P("secondary_sense", "smug")], label="complacent")
        assert c["decision"] == "relabel" and c["verdict"] == "secondary_sense"
        tie = LF.combine([P("secondary_sense", "a"), P("not_a_sense", "b")], label="x")
        assert tie["verdict"] == "not_a_sense"

    def test_own_stem_proposals_are_dropped(self):
        c = LF.combine([P("secondary_sense", "Grasping"), P("not_a_sense", "grasping")], label="grasping")
        assert c["decision"] == "no_better_label" and c["dropped_proposals"] == ["Grasping", "grasping"]

    def test_no_answer(self):
        assert LF.combine([], label="x")["decision"] is None


# --------------------------------------------------------------------------- senses and the user turn

def fake_senses(table):
    return lambda label: [Sense(d, pos) for d, pos in table.get(label.lower(), [])]


SENSES = fake_senses({"grasping": [("immoderately desirous of acquiring e.g. wealth", "s"),
                                   ("the act of gripping", "n")],
                      "chatterbox": [("an obnoxious and foolish and loquacious talker", "n")]})


class TestSensesAndUser:
    def test_dictionary_senses_adjectives_first_else_other_parts(self):
        assert LF.oewn_senses("grasping", senses=SENSES) == ["immoderately desirous of acquiring e.g. wealth"]
        assert LF.oewn_senses("chatterbox", senses=SENSES) == ["an obnoxious and foolish and loquacious talker (noun)"]
        assert LF.oewn_senses("Comfort-seeking", senses=SENSES) == []

    def test_recorded_senses_from_the_registry_row(self):
        rows = {"grasping#1": {"filter": {"senses": ["greedy", "gripping"], "judged_sense": "greedy"}}}
        ctx = LF.sense_context("Grasping", senses=SENSES, rows=rows)
        assert ctx == {"dictionary_senses": ["immoderately desirous of acquiring e.g. wealth"],
                       "recorded_senses": ["greedy", "gripping"], "usual_sense": "greedy"}

    def test_three_variants_of_the_user_turn(self):
        full = json.loads(LF.build_user("grasping", "This means  craving honor.", {
            "dictionary_senses": ["d1"], "recorded_senses": ["r1"], "usual_sense": "r1"}))
        assert list(full) == ["label", "gloss", "dictionary_senses", "recorded_senses", "usual_sense"]
        assert full["gloss"] == "This means craving honor."
        dic = json.loads(LF.build_user("openhanded", "g", {"dictionary_senses": ["d"], "recorded_senses": [],
                                                           "usual_sense": None}))
        assert list(dic) == ["label", "gloss", "dictionary_senses"]
        assert list(json.loads(LF.build_user("comfort seeking", "g", {}))) == ["label", "gloss"]

    def test_label_shown_in_the_judge_display_form(self):
        assert json.loads(LF.build_user("careless (HEXACO)", "g", {}))["label"] == "careless (from HEXACO)"

    def test_items_are_distinct_pairs(self):
        its = LF.build_items([("smug", "g1"), ("smug", "g1 "), ("smug", "g2"), ("", "g"), ("x", "")], system="S",
                             senses=SENSES)
        assert [(i.label, i.gloss) for i in its] == [("smug", "g1"), ("smug", "g2")]
        assert its[0].request_sha256 == LF.request_sha256("S", its[0].user)


def test_cosines_with_the_hash_embedder():
    from assistant_axis.gapgen.embed import HashEmbedder, embed_texts
    its = LF.build_items([("grasping", "This means immoderately desirous of acquiring wealth."),
                          ("Comfort-seeking", "This means wanting comfort.")], system="S", senses=SENSES)
    assert its[1].context["dictionary_senses"] == []
    emb = HashEmbedder()
    n = LF.cosines(its, embed=lambda texts: embed_texts(emb, texts))
    assert n == 1 and its[0].cos_usual > 0.8 and its[0].cos_max >= its[0].cos_usual and its[1].cos_usual is None
    ds = LF.decide(its, {}, 3, screen_floor=0.8)
    assert ds[0]["decided_by"] == "screen" and ds[0]["decision"] == "fits" and ds[1]["decision"] is None
    assert LF.todo_calls(its, {}, 3, screen_floor=0.8) == [(its[1], 0), (its[1], 1), (its[1], 2)]
    assert len(LF.todo_calls(its, {}, 3)) == 6


# --------------------------------------------------------------------------- corrected candidates

def test_source_ref_tag_round_trips_and_structural_reads_it():
    from assistant_axis.gapgen.generators.structural import submit as SU
    ref = LF.tag_source_ref("structural:classical:aristotle:proper_ambition:excess", "not_a_sense", "grasping")
    assert ref == "structural:classical:aristotle:proper_ambition:excess;label_fit:not_a_sense:grasping"
    assert LF.split_source_ref(ref) == ("structural:classical:aristotle:proper_ambition:excess",
                                        {"verdict": "not_a_sense", "original": "grasping"})
    assert LF.split_source_ref(LF.tag_source_ref(None, "secondary_sense", "smug")) == (
        None, {"verdict": "secondary_sense", "original": "smug"})
    assert LF.split_source_ref("x:1") == ("x:1", None)
    got = SU.parse_source_ref(ref)
    assert got["part"] == "classical" and got["role"] == "excess" and got["label_fit"]["original"] == "grasping"
    with pytest.raises(ValueError):
        SU.parse_source_ref(LF.tag_source_ref(None, "not_a_sense", "x"))


def test_corrected_candidates():
    def C(surface, gloss, ref):
        return Candidate(surface=surface, generator="structural", run_id="r1", rank=3, score=2.0, gloss_hint=gloss,
                         source_ref=ref, partner_hint="P")
    cands = [C("grasping", "craving honor", "s:1"), C("grasping", "greedy for money", "s:2"),
             C("smug", "lecturing", "s:3"), C("adrift", None, "s:4"), C("odd", "g", "s:5")]
    its = LF.build_items(LF.pairs_of(cands), system="S", use_oewn=False)
    ans_ = {}
    script = {"grasping|craving honor": [P("not_a_sense", "vainglorious"), P("not_a_sense", "honor-hungry"),
                                         P("fits")],
              "grasping|greedy for money": [P("fits")] * 3,
              "smug|lecturing": [P("secondary_sense", "smug")] * 2}
    for it in its:
        for r, a in enumerate(script.get(f"{it.label}|{it.gloss}", [])):
            ans_[(it.request_sha256, r)] = {"parsed": a}
    ds = LF.decide(its, ans_, 3)
    fixed, n = LF.corrected_candidates(cands, ds)
    assert [(c.surface, c.source_ref) for c in fixed] == [
        ("vainglorious", "s:1;label_fit:not_a_sense:grasping"), ("honor-hungry", "s:1;label_fit:not_a_sense:grasping"),
        ("grasping", "s:2"), ("smug", "s:3"), ("adrift", "s:4"), ("odd", "s:5")]
    assert all((c.rank, c.score, c.partner_hint, c.run_id) == (3, 2.0, "P", "r1") for c in fixed)
    assert fixed[0].gloss_hint == "craving honor"
    assert n == {"kept_fits": 1, "kept_no_answer": 1, "kept_no_better_label": 1, "kept_no_gloss": 1,
                 "relabelled_in": 1, "relabelled_out": 2}


# --------------------------------------------------------------------------- marks

SHEET = """# Precision sample

| # | label | gloss | how | M1 | Roger |
|---|---|---|---|---|---|
| 1 | grasping | This means craving honor beyond what is right. | x | trait | ? odd sense |
| 2 | honor-hungry | This means craving honor beyond what is right. | x | trait | trait |
| 3 | flashy | This means spending lavishly on display. | x | trait | ? borderline |
| 4 | brazen | This means feeling no shame. | x | trait | duplicate |
| 5 | unmarked | This means nothing. | x | trait |  |
"""


def test_parse_marks_and_confusion():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.md"
        p.write_text(SHEET)
        marks = LF.parse_marks(p)
    assert [(m["label"], m["should_fit"]) for m in marks] == [("grasping", False), ("honor-hungry", True),
                                                              ("flashy", False), ("brazen", True),
                                                              ("unmarked", None)]
    its = LF.build_items([(m["label"], m["gloss"]) for m in marks], system="S", use_oewn=False)
    by = {it.label: it for it in its}
    a = {(by["grasping"].request_sha256, 0): {"parsed": P("not_a_sense", "vainglorious")},
         (by["honor-hungry"].request_sha256, 0): {"parsed": P("fits")},
         (by["flashy"].request_sha256, 0): {"parsed": P("fits")},
         (by["brazen"].request_sha256, 0): {"parsed": P("secondary_sense", "shameless")}}
    ds = LF.decide(its, a, 1)
    conf = LF.confusion(marks, ds)
    assert conf["table"] == {"not_fit|not_fit": 1, "not_fit|fit": 1, "not_fit|no_answer": 0, "fit|not_fit": 1,
                             "fit|fit": 1, "fit|no_answer": 0}
    assert (conf["n"], conf["flag_precision"], conf["flag_recall"], conf["agreement"]) == (4, 0.5, 0.5, 0.5)
    assert [d["label"] for d in conf["disagreements"]] == ["flashy", "brazen"]
    assert LF.confusion(marks, ds, exclude=["Flashy"])["n"] == 3
    assert "flags: precision 0.5" in LF.format_confusion(conf, "t")
    by["grasping"].cos_usual, by["honor-hungry"].cos_usual = 0.3, 0.7
    eff = LF.screen_effect(marks, its, floors=(0.5,))
    assert eff["floors"] == [{"floor": 0.5, "settled_without_call": 1, "of_them_marked_odd": 0}]
    assert eff["median_cos_usual"] == {"should_not_fit": 0.3, "should_fit": 0.7}


# --------------------------------------------------------------------------- the pinned prompt

def test_rubric_is_pinned_and_loaded():
    assert sr.GENERATOR_FILES[LF.RUBRIC_NAME] == "label_fit.md" and LF.RUBRIC_NAME in sr.PINNED_NAMES
    r = LF.load_rubric()
    assert r["version"] == 1 and r["sha256"] == sr.sha256(r["text"])
    assert "reason in one or two short sentences first" in r["text"] and "Think" not in r["text"]


#: The examples' words: invented cases, none a corpus trait, a seed-queue entry, a validation word or one of the 50
#: labels of the structural pilot's precision sample (the validation data).
EXAMPLE_WORDS = ("liberal", "openhanded", "spirited")


def test_example_words_hygiene():
    from assistant_axis.entity_id import normalize_to_file_name
    from assistant_axis.gapgen.generators.structural.prompts import forbidden_stems
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
    text = LF.load_rubric()["text"]
    forbidden = forbidden_stems()
    for w in EXAMPLE_WORDS:
        assert f'"{w}"' in text and normalize_to_file_name(w) not in forbidden, w
    sample = Path(__file__).resolve().parents[2] / "data/candidates/runs/structural/2026-10-14-pilot/roger_sample.md"
    if sample.exists():
        labels = {m["label"].lower() for m in LF.parse_marks(sample)}
        assert not labels & set(EXAMPLE_WORDS)
    hits = sorted(w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden and w not in PROSE_ALLOWED)
    assert hits == sorted(PROSE_RECORDED), hits


#: Words of the prompt that are corpus, queue or validation words, used only as prose (never quoted as examples).
PROSE_RECORDED = ("political", "single", "usual")


# --------------------------------------------------------------------------- the commands, end to end

@pytest.fixture
def cli(tmp_path, monkeypatch):
    from data_analysis.gap_generation import label_fit as CLI
    monkeypatch.setattr(CLI, "platform_dirty_files", lambda: [])
    reg = tmp_path / "registry.jsonl"
    submit_candidates([Candidate(surface="grasping", generator="censuses", run_id="c1")], registry_path=reg,
                      relabel=None)
    Registry(reg).merge_block("grasping#1", "filter", {"senses": ["greedy", "gripping"], "judged_sense": "greedy"})
    calls = []

    def responder(kw):
        u = json.loads(user_text(kw))
        calls.append(u)
        if u["label"] == "refused":
            return make_response("", stop_reason="refusal", output_tokens=0)
        if u["label"] == "grasping":
            return "Grasping means greedy. " + ans("not_a_sense", "honor-hungry")
        return ans("fits")
    client = FakeAsyncAnthropic(responder)
    monkeypatch.setattr(CLI, "_client", lambda: client)
    base = ["--registry", str(reg)]
    common = ["--no-oewn", "--embedder", "hash", "--readings", "3"]
    return {"CLI": CLI, "base": base, "common": common, "calls": calls, "tmp": tmp_path, "reg": reg}


def write_sheet(tmp: Path) -> Path:
    p = tmp / "runs" / "roger_sample.md"
    p.parent.mkdir(parents=True)
    p.write_text(SHEET)
    return p


def test_validate_end_to_end(cli, capsys):
    sheet = write_sheet(cli["tmp"])
    out = cli["tmp"] / "v"
    args = cli["base"] + ["validate", "--marks", str(sheet), "--out-dir", str(out), *cli["common"]]
    assert cli["CLI"].main(args + ["--dry-run", "--render"]) == 0
    printed = capsys.readouterr().out
    assert not out.exists() and cli["calls"] == []
    assert "=== user turn, registry row with M1's senses: grasping ===" in printed
    assert '"recorded_senses": ["greedy", "gripping"], "usual_sense": "greedy"' in printed
    assert "=== user turn, no senses known" in printed
    assert cli["CLI"].main(args + ["--borderline", "flashy"]) == 0
    printed = capsys.readouterr().out
    assert len(cli["calls"]) == 15                                    # five rows, three readings
    recs = [json.loads(x) for x in (out / "responses.jsonl").read_text().splitlines()]
    assert len(recs) == 15 and all(r["request_sha256"] and r["prompt_version"] == 1 for r in recs)
    assert any("prose before the object" in r["notes"] for r in recs)
    d = json.loads((out / "decisions_haiku-5-5.json").read_text())
    by = {x["label"]: x for x in d["decisions"]}
    assert by["grasping"]["decision"] == "relabel" and by["grasping"]["proposals"][0]["label"] == "honor-hungry"
    assert d["confusion"]["all marked rows"]["table"]["not_fit|not_fit"] == 1
    assert "without the borderline rows (flashy)" in printed and "Roger \\ check" in printed
    assert (out / "readout_haiku-5-5.md").exists()
    u = json.loads((out / "usage.json").read_text())
    assert u["per_model"]["claude-haiku-5-5"]["n_calls"] == 15
    assert cli["CLI"].main(args) == 2                                 # answers on record: --resume needed
    n = len(cli["calls"])
    assert cli["CLI"].main(args + ["--resume"]) == 0 and len(cli["calls"]) == n


def test_validate_budget_cap_refuses(cli):
    sheet = write_sheet(cli["tmp"])
    args = cli["base"] + ["validate", "--marks", str(sheet), "--out-dir", str(cli["tmp"] / "v"), *cli["common"],
                          "--model", "claude-sonnet-5-5", "--budget-usd", "0.001"]
    with pytest.raises(SystemExit) as e:
        cli["CLI"].main(args)
    assert e.value.code == 2 and cli["calls"] == []


def test_check_writes_the_corrected_candidates(cli, capsys):
    rdir = cli["tmp"] / "runs" / "structural" / "r1"
    rdir.mkdir(parents=True)
    cands = [Candidate(surface="grasping", generator="structural", run_id="r1", gloss_hint="craving honor",
                       source_ref="structural:classical:aristotle:proper_ambition:excess"),
             Candidate(surface="honor-hungry", generator="structural", run_id="r1", gloss_hint="craving honor",
                       source_ref="structural:op:excess:ambitious"),
             Candidate(surface="refused", generator="structural", run_id="r1", gloss_hint="anything")]
    (rdir / "candidates.jsonl").write_text("".join(json.dumps(asdict(c)) + "\n" for c in cands))
    args = cli["base"] + ["--candidates-dir", str(cli["tmp"]), "check", "--run", "structural/r1", *cli["common"]]
    assert cli["CLI"].main(args) == 2                                 # a pair with no answer: not written
    out = rdir / "label_fit"
    assert (out / "decisions.json").exists() and not (out / "candidates.jsonl").exists()
    recs = [json.loads(x) for x in (out / "responses.jsonl").read_text().splitlines()]
    assert sum(1 for r in recs if r["stop_reason"] == "refusal" and r["parse_error"].startswith("refusal")) == 3
    assert cli["CLI"].main(args + ["--resume", "--keep-undecided"]) == 0
    fixed = read_candidates(out / "candidates.jsonl")
    assert [(c.surface, c.source_ref) for c in fixed] == [
        ("honor-hungry", "structural:classical:aristotle:proper_ambition:excess;label_fit:not_a_sense:grasping"),
        ("honor-hungry", "structural:op:excess:ambitious"), ("refused", None)]
    line = json.loads((out / "candidates.jsonl").read_text().splitlines()[0])
    assert list(line) == list(CANDIDATE_FIELDS)
    printed = capsys.readouterr().out
    assert "gap_registry.py submit --from" in printed
    md = (out / "readout.md").read_text()
    assert "## Relabelled (1)" in md and "honor-hungry (3)" in md
    assert (rdir / "candidates.jsonl").read_text().count("grasping") == 1     # the run's own record is untouched


def test_check_refuses_an_unpinned_rubric(cli, tmp_path, monkeypatch, capsys):
    import shutil
    rd = tmp_path / "rubrics"
    shutil.copytree(sr.versions_path().parent, rd)
    p = rd / "label_fit.md"
    p.write_text(p.read_text().replace("You check the name", "You check the label"))
    c = tmp_path / "c.jsonl"
    c.write_text(json.dumps(asdict(Candidate(surface="x", generator="g", run_id="r", gloss_hint="h"))) + "\n")
    args = cli["base"] + ["--rubrics-dir", str(rd), "check", "--candidates", str(c), *cli["common"]]
    assert cli["CLI"].main(args) == 2 and "REFUSED (rubric not pinned)" in capsys.readouterr().err
    assert cli["CLI"].main(args + ["--dry-run"]) == 0 and cli["calls"] == []
