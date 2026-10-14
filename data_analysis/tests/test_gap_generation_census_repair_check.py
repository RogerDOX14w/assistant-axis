"""The census spelling-repair check (QUESTIONS 35): ``census_generator.py repair-check`` and its module
``assistant_axis.gapgen.generators.censuses.repair_check``.  No network: the Anthropic client is the repository's fake
(``assistant_axis/tests/fake_anthropic.py``), the table and counts are written to ``tmp_path``, and the dirty-tree
check is replaced."""
import json
import shutil
from pathlib import Path

import pytest

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.censuses import ingest as I
from assistant_axis.gapgen.generators.censuses import repair_check as RC
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.censuses_fakes import fake_lookups
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from data_analysis.gap_generation import census_generator as CG


def trow(surface, col, line, *, raw=None, rank=1):
    """A census table row for an Allport-only entry (the fields the check reads, the rest empty)."""
    stem = I.normalize_candidate(surface).stem
    return I.TableRow(schema_version=1, surface=surface, stem=stem, label=surface,
                      allport={"columns": [col], "raw": {col: raw or surface}, "line": {col: line}}, in_merged=None,
                      tda=None, zipf=None, freq_hard_reject=None, freq_probe_band=None, freq_rescue=None,
                      freq_platform=None, wordnet=None, gloss_hint=None, repaired_from=None, unknown_word=False,
                      eligible=True, ineligible_reason=None, stage="allport_hi", rank=rank, score=None,
                      corpus_stem_match=False, queue_stem_match=False)


#: Column I, alphabetical: the four suggestions sit among real entries.  "backless" is held elsewhere (column II),
#: so sackless -> backless is not selected.
TABLE = [trow("brag", "I", 10), trow("bragless", "I", 11, raw="Bragless"), trow("brahmin", "I", 12),
         trow("brainwood", "I", 13), trow("liegeman", "I", 20), trow("light-dingered", "I", 21),
         trow("light-footed", "I", 22), trow("light-handed", "I", 23), trow("sackless", "I", 30),
         trow("stirless", "I", 31), trow("stolid", "I", 32), trow("backless", "II", 5)]
SUGGESTIONS = [
    {"raw": "Bragless", "column": "I", "line": 11, "repaired": "braless", "kind": "other"},
    {"raw": "light-dingered", "column": "I", "line": 21, "repaired": "light-fingered", "kind": "other"},
    {"raw": "sackless", "column": "I", "line": 30, "repaired": "backless", "kind": "early"},
    {"raw": "stirless", "column": "I", "line": 31, "repaired": "starless", "kind": "vowel_substitution"},
]
#: entry -> the fake model's verdict; "refuse" answers with a refusal stop reason.
ANSWERS = {"Bragless": "real_word", "light-dingered": "typo", "stirless": "refuse"}


def responder(answers):
    def r(kw):
        entry = json.loads(user_text(kw))["entry"]
        v = answers[entry]
        if v == "refuse":
            return make_response("", stop_reason="refusal", output_tokens=0)
        return json.dumps({"reason": f"{entry} reads as {v}.", "verdict": v})
    return r


@pytest.fixture
def env(tmp_path, monkeypatch):
    cdir = tmp_path / "censuses"
    cdir.mkdir()
    I.write_table(TABLE, cdir / "census_table.jsonl")
    (cdir / "ingest_counts.json").write_text(json.dumps({"repair_suggestions_list": SUGGESTIONS}))
    cand = tmp_path / "candidates"
    monkeypatch.setattr(CG, "platform_dirty_files", lambda: [])
    monkeypatch.setattr(I, "default_lookups", lambda: fake_lookups())
    fake = {"client": FakeAsyncAnthropic(responder(ANSWERS))}
    monkeypatch.setattr(CG, "_client", lambda: fake["client"])
    common = ["--table", str(cdir / "census_table.jsonl"), "--counts", str(cdir / "ingest_counts.json"),
              "--registry", str(cand / "registry.jsonl"), "--candidates-dir", str(cand)]
    return {"root": tmp_path, "common": common, "out": cdir / "repair_check", "cand": cand, "fake": fake}


def snapshot(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_size) for p in root.rglob("*") if p.is_file())


def records(env):
    return RC.read_records(env["out"] / RC.RESPONSES_NAME)


# --------------------------------------------------------------------------- selection, prompt, parse

def test_selection_keeps_the_suggestions_whose_repaired_word_is_new():
    sel, counts = RC.select_suggestions(SUGGESTIONS, TABLE)
    assert [s.entry for s in sel] == ["Bragless", "light-dingered", "stirless"]
    assert counts == {"n_suggestions": 4, "n_held_elsewhere": 1, "n_new": 3,
                      "by_kind_new": {"other": 2, "vowel_substitution": 1}}
    s = sel[0]
    assert s.id == "I:11" and s.source_ref == "allport:I:11:repair:bragless->braless"


def test_the_user_turn_carries_the_alphabetical_neighbours():
    sel, _ = RC.select_suggestions(SUGGESTIONS, TABLE)
    items = RC.build_items(sel, TABLE, "SYSTEM")
    assert json.loads(items[0].user) == {"entry": "Bragless", "suggested": "braless", "before": ["brag"],
                                         "after": ["brahmin", "brainwood"]}
    assert items[1].before == ["brainwood", "liegeman"] and items[1].after == ["light-footed", "light-handed"]
    assert items[0].request_sha256 == RC.request_sha256("SYSTEM", items[0].user) != items[1].request_sha256


def test_the_prompt_is_pinned_and_an_edited_text_is_refused(tmp_path):
    rub = RC.load_rubric()
    assert rub["name"] == "census_repair_check" and rub["file"].endswith("rubrics/census_repair_check.md")
    assert sr.current_versions(names=sr.GENERATOR_NAMES)[RC.RUBRIC_NAME] == (rub["version"], rub["sha256"])
    assert rub["sha256"] == sr.sha256(rub["text"]) and rub["version"] == 1
    # the judging rules: a short reason first, then the verdict; never a "think" field
    assert '{"reason": "<one or two short sentences>", "verdict":' in rub["text"]
    assert "think" not in rub["text"].lower()
    # the two example words are in no census list (the examples are invented)
    real = Path(sr.RUBRICS_DIR).parents[2] / "data" / "candidates" / "censuses" / "census_table.jsonl"
    if real.exists():
        raws = {v.lower() for r in I.load_census_table(real) for v in ((r.allport or {}).get("raw") or {}).values()}
        assert not {"good-natired", "couthy"} & raws
    d = tmp_path / "rubrics"
    shutil.copytree(sr.RUBRICS_DIR, d)
    p = d / "census_repair_check.md"
    p.write_text(p.read_text().replace("Respond with one JSON object", "Respond with a JSON object"))
    with pytest.raises(RC.RubricNotPinned, match="census_repair_check"):
        RC.load_rubric(d)


@pytest.mark.parametrize("text,stop,want,err", [
    ('{"reason": "Archaic.", "verdict": "real_word"}', "end_turn", "real_word", None),
    ('```json\n{"reason": "A slip.", "verdict": "Typo"}\n```', "end_turn", "typo", None),
    ('{"reason": "Hm.", "verdict": "real word"}', "end_turn", "real_word", None),
    ('{"verdict": "typo"}', "end_turn", None, "missing_key"),
    ('{"reason": "x", "verdict": "maybe"}', "end_turn", None, "bad_value"),
    # prose before one object is accepted since parser 2 (2026-10-14; was not_one_object), text after it is not
    ('Sure: {"reason": "x", "verdict": "typo"}', "end_turn", "typo", None),
    ('{"reason": "x", "verdict": "typo"} and more', "end_turn", None, "not_one_object"),
    ('{"reason": "x", "verdict": "typo"}', "refusal", None, "refusal"),
    ("", "end_turn", None, "empty"),
    (None, None, None, "no_response"),
])
def test_parse(text, stop, want, err):
    parsed, e, notes = RC.parse_verdict(text, stop)
    assert (parsed or {}).get("verdict") == want
    assert (e.split(":")[0] if e else None) == err


def test_combine_by_majority_and_a_tie_is_unsure():
    assert RC.combine(["typo"]) == "typo"
    assert RC.combine(["typo", "real_word", "typo"]) == "typo"
    assert RC.combine(["typo", "real_word"]) == "unsure"
    assert RC.combine([]) is None


# --------------------------------------------------------------------------- the command

def test_dry_run_writes_nothing_and_prints_the_estimate(env, capsys):
    before = snapshot(env["root"])
    assert CG.main(env["common"] + ["repair-check", "--dry-run", "--render", "1"]) == 0
    assert snapshot(env["root"]) == before and not env["fake"]["client"].calls
    out = capsys.readouterr().out
    assert "4 repair suggestions listed; 1 point to a word the census lists already hold; 3 to a new word" in out
    assert "repair check: 3 x (700, 400) tokens at claude-sonnet-5-5 rates" in out
    assert '"entry": "Bragless"' in out and "DRY-RUN: would make 3 calls" in out


def test_over_budget_is_refused(env):
    with pytest.raises(SystemExit) as ei:
        CG.main(env["common"] + ["repair-check", "--budget-usd", "0.001"])
    assert ei.value.code == 2 and not env["out"].exists()


def test_a_dirty_tree_is_refused_without_allow_dirty(env, monkeypatch):
    monkeypatch.setattr(CG, "platform_dirty_files", lambda: [" M assistant_axis/gapgen/llm.py"])
    assert CG.main(env["common"] + ["repair-check"]) == 2
    assert not env["out"].exists() and not env["fake"]["client"].calls


def test_run_records_every_response_counts_a_refusal_and_resume_sends_only_the_missing(env, capsys):
    assert CG.main(env["common"] + ["repair-check"]) == 0
    calls = env["fake"]["client"].calls
    assert len(calls) == 3
    kw = calls[0]
    assert kw["model"] == "claude-sonnet-5-5" and kw["max_tokens"] == 2000 and "temperature" not in kw
    assert kw["system"][0]["text"] == RC.load_rubric()["text"]
    recs = records(env)
    assert len(recs) == 3 and all(r["request_sha256"] and r["prompt_version"] == 1 for r in recs)
    refused = [r for r in recs if r["entry"] == "stirless"][0]
    assert refused["parsed"] is None and refused["parse_error"].startswith("refusal") and \
        refused["stop_reason"] == "refusal"
    usage = json.loads((env["out"] / "usage.json").read_text())
    assert usage["n_calls"] == 3 and usage["total_cost_usd"] > 0
    v = json.loads((env["out"] / "verdicts.json").read_text())
    assert v["counts"] == {"typo": 1, "real_word": 1, "unsure": 0, "no_answer": 1}
    md = (env["out"] / "readout.md").read_text()
    assert "| light-dingered | light-fingered | I:21 |" in md and "## No answer yet (1)" in md
    assert "[ingest_counts.json](../ingest_counts.json)" in md and "[verdicts.json](verdicts.json)" in md
    out = capsys.readouterr().out
    assert "2 of 3 calls answered" in out
    # a rerun without --resume is refused; with it only the refused suggestion is asked again
    assert CG.main(env["common"] + ["repair-check"]) == 2
    env["fake"]["client"] = FakeAsyncAnthropic(responder({**ANSWERS, "stirless": "real_word"}))
    assert CG.main(env["common"] + ["repair-check", "--resume"]) == 0
    assert [json.loads(user_text(k))["entry"] for k in env["fake"]["client"].calls] == ["stirless"]
    assert len(records(env)) == 4
    assert json.loads((env["out"] / "usage.json").read_text())["n_calls"] == 4
    v = json.loads((env["out"] / "verdicts.json").read_text())
    assert v["counts"] == {"typo": 1, "real_word": 2, "unsure": 0, "no_answer": 0}
    # everything answered: a resume sends nothing
    env["fake"]["client"] = FakeAsyncAnthropic(responder(ANSWERS))
    assert CG.main(env["common"] + ["repair-check", "--resume"]) == 0
    assert not env["fake"]["client"].calls


def test_submit_writes_only_the_accepted_repairs(env, capsys):
    # refused while a suggestion has no answer
    assert CG.main(env["common"] + ["repair-check"]) == 0
    assert CG.main(env["common"] + ["repair-check", "--submit", "--run-id", "rc1"]) == 2
    env["fake"]["client"] = FakeAsyncAnthropic(responder({**ANSWERS, "stirless": "unsure"}))
    assert CG.main(env["common"] + ["repair-check", "--resume"]) == 0
    before = snapshot(env["root"])
    assert CG.main(env["common"] + ["repair-check", "--submit", "--run-id", "rc1", "--dry-run"]) == 0
    assert snapshot(env["root"]) == before
    capsys.readouterr()
    n_calls = len(env["fake"]["client"].calls)
    assert CG.main(env["common"] + ["repair-check", "--submit", "--run-id", "rc1"]) == 0
    assert len(env["fake"]["client"].calls) == n_calls                  # --submit makes no call
    rdir = env["cand"] / "runs" / "censuses" / "rc1"
    cands = [json.loads(x) for x in (rdir / "candidates.jsonl").read_text().splitlines()]
    assert [(c["surface"], c["source_ref"], c["generator"]) for c in cands] == [
        ("light-fingered", "allport:I:21:repair:light-dingered->light-fingered", "censuses")]
    rows = Registry(env["cand"] / "registry.jsonl").fold()
    assert list(rows) == ["light_fingered#1"]
    run = json.loads((rdir / "run.json").read_text())
    assert run["args"]["stage"] == "repair_check" and run["args"]["verdicts"]["unsure"] == 1
    out = capsys.readouterr().out
    assert "traithood_filter.py --batch-id rc1_censuses --run censuses/rc1" in out
    assert "novelty_score.py score --batch-id rc1_censuses --run censuses/rc1" in out
    # the census table and counts are never edited
    assert I.load_census_table(env["root"] / "censuses" / "census_table.jsonl") == TABLE


def test_parser_takes_the_object_after_leading_prose():
    """2026-10-14: 382 of 942 Sonnet 5.5 replies wrote the reason as a sentence, then the object."""
    from assistant_axis.gapgen.generators.censuses import repair_check as RC
    text = '"Accendible" is a real rare word.\n\n{"reason": "a rare word {from Latin}", "verdict": "real_word"}'
    ans, err, notes = RC.parse_verdict(text, "end_turn")
    assert err is None and ans["verdict"] == "real_word" and "prose before the object" in notes
    assert RC.parse_verdict('{"reason": "x", "verdict": "typo"} trailing', "end_turn")[1].startswith("not_one_object")
    rec = {"model": "m", "request_sha256": "s", "reading": 1, "parsed": None, "parser_version": 1, "text": text,
           "stop_reason": "end_turn"}
    got = RC.answers_on_record([rec], model="m")
    assert got[("s", 1)]["parsed"]["verdict"] == "real_word"
