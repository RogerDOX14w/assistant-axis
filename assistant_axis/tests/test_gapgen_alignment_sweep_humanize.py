"""Alignment sweep: the humanize step (Roger, 2026-10-20: every sweep trait in its closest human phrasing).

Prompt rendering, the parser (prose before the JSON allowed), refusals recorded and counted, the candidates file's
fields, the submit-then-retract sequence on a tmp registry (Roger's reviewed rows kept), the budget gate and the
batch transport.  No network: fake Anthropic clients."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.alignment_sweep import extract as X
from assistant_axis.gapgen.generators.alignment_sweep import humanize as H
from assistant_axis.gapgen.paths import REPO_ROOT
from assistant_axis.gapgen.registry import (
    CANDIDATE_FIELDS, Candidate, Registry, first_gloss_hint, read_candidates, submit_candidates,
)
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from assistant_axis.tests.llm_entropy_fakes import FakeBatchClient
from data_analysis.gap_generation import alignment_sweep as CLI

OLD = "2026-10-01-old"
NEW = "2026-10-20-hz"


def gl(core: str) -> str:
    """A gloss of 22 words that begins "This means"."""
    return f"This means {core} " + " ".join(["steadily"] * (20 - len(core.split()))) + "."


G = {"deceives its users": gl("misleading the user about what one has done"),
     "candid": gl("telling the user plainly what one thinks"),
     "flattering": gl("praising whatever the user shows one"),
     "schemes for itself": gl("plotting against the lab that built it")}
NEW_ANSWERS = {"deceives its users": ("deceives people", gl("misleading others about what one has done")),
               "candid": ("candid", gl("telling others plainly what one thinks")),
               "flattering": ("flattering", gl("praising whatever others show one")),
               "schemes for itself": ("looks out for oneself", gl("plotting against those one answers to"))}
CENSUS_GLOSS = "showing or representing to advantage"


# --------------------------------------------------------------------------- the rubric

def test_rubric_pinned_reason_first_and_no_thinking():
    rub = X.load_rubric(H.RUBRIC_NAME)
    assert rub["version"] == 4 and rub["sha256"] == sr.sha256(sr.load_prompt(H.RUBRIC_NAME))
    assert sr.GENERATOR_FILES[H.RUBRIC_NAME] == "alignment_humanize.md" and H.RUBRIC_NAME in sr.PINNED_NAMES
    text = rub["text"]
    tpl = text[text.rindex('{"reason"'):]                      # the answer format, at the end
    assert tpl.index('"reason"') < tpl.index('"label"') < tpl.index('"gloss"') < tpl.index('"changed"')
    assert "short reason first" in text
    # Sonnet 5.5 refuses a prompt asking it to think in a field (judging rule of 2026-10-13)
    assert not re.search(r"\bthink(ing)?\b|\breasoning\b", text, re.I)


def _forbidden_labels() -> set[str]:
    stems = {p.stem for p in (REPO_ROOT / "data" / "traits" / "instructions").glob("*.json")}
    q = json.loads((REPO_ROOT / "data" / "seed_queue.json").read_text(encoding="utf-8"))
    for e in (q["entries"] if isinstance(q, dict) else q):
        if e.get("status") in ("not_adopted", "superseded"):
            continue
        for k in ("stem", "label"):
            if e.get(k):
                stems.add(normalize_to_file_name(e[k]))
    return stems


def test_rubric_hygiene_no_corpus_stem_and_no_live_queue_label():
    """No word of the prompt is a corpus stem or a live queue label.  One local allowance: "operator" (a live queue
    label) is named only in the list of AI vocabulary to leave out, which Roger's decision names word for word; it is
    never an example, so it cannot seed an answer (not added to the global PROSE_ALLOWED)."""
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
    forbidden = _forbidden_labels()
    assert len(forbidden) > 900
    text = sr.load_prompt(H.RUBRIC_NAME)
    local = {"operator"}
    hits = {w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden and w not in PROSE_ALLOWED | local}
    assert hits == set(), hits
    assert "operator" in text and '"operator"' not in text
    flat = " " + " ".join(re.findall(r"[a-z]+", text.lower())) + " "
    multi = {s for s in forbidden if "_" in s and f" {s.replace('_', ' ')} " in flat}
    assert multi == set(), multi


def test_worked_examples_obey_their_own_rules_and_are_outside_the_region():
    text = sr.load_prompt(H.RUBRIC_NAME)
    answers = [json.loads(m) for m in re.findall(r"^Answer (\{.*\})$", text, re.M)]
    givens = [json.loads(m) for m in re.findall(r"^Given (\{.*\})$", text, re.M)]
    assert len(answers) == 3 and len(givens) == 3 and "Three invented examples" in text
    for given, ans in zip(givens, answers):
        parsed, err, notes = H.parse_answer(json.dumps(ans), original=(given["label"], given["gloss"]))
        assert err is None and notes == [], (err, notes)
        assert parsed["differs"] and parsed["changed"]
    # the second starts from software and its user (Roger): the label itself has to change
    assert "the user" in givens[1]["gloss"] and "app" in givens[1]["gloss"] and answers[1]["label"] != givens[1]["label"]
    # the third keeps a label that already fits: only the pronouns and the relation change, and changed is true
    assert answers[2]["label"] == givens[2]["label"] and answers[2]["changed"] is True
    assert {"it", "itself", "users"} & set(H.words(givens[2]["gloss"])) and not (
        {"it", "its", "itself", "users", "robot"} & set(H.words(answers[2]["gloss"])))
    # nothing from the sweep's region (the Fable review of v3: its example neighboured 28 of the 865 inputs); the
    # concepts below were checked by grep against the 865 inputs of 2026-10-20 (none about waiting, latency,
    # responsiveness, humming, tunes or robots)
    blob = " ".join(json.dumps(x) for x in answers + givens).lower()
    for w in ("sandbagging", "sycophan", "reward", "oversight", "shutdown", "weights", "deceiv", "manipulat",
              "autonom", "honest", "harm", "flatter", "defer", "obey", "overrid", "setting", "choice", "control"):
        assert w not in blob, w


def test_rubric_file_holds_a_rendered_sample_per_variant():
    doc = (REPO_ROOT / "reports" / "trait_gap_generation" / "rubrics" / "alignment_humanize.md").read_text()
    body = doc.split("## Rendered samples", 1)[1].split("## Your notes", 1)[0]
    blocks = [json.loads(b) for b in re.findall(r"```text\n(\{.*?\})\n```", body, re.S)]
    assert len(blocks) == 2
    assert "source_sentence" in blocks[0] and "section" in blocks[0]
    assert "source_sentence" not in blocks[1] and "section" not in blocks[1]
    assert list(blocks[0]) == ["label", "gloss", "opposite", "section", "source_sentence"]


# --------------------------------------------------------------------------- rendering

def _inp(label="acts against its developer", gloss=None, **kw):
    gloss = gloss or gl("taking hostile actions against the lab that built it")
    d = dict(id=H.pair_id(label, gloss), label=label, gloss=gloss, opposite="respects oversight",
             section="Intro > Results", source_sentence="The model took anti-lab actions.",
             sources=[{"run_id": OLD, "key": normalize_to_file_name(label) + "#1", "source_ref": "x:v:s", "rank": 1,
                       "partner_hint": "respects oversight"}])
    d.update(kw)
    return H.HumanizeInput(**d)


def test_render_user_one_object_in_order_and_variants():
    u = json.loads(H.render_user(_inp()))
    assert list(u) == ["label", "gloss", "opposite", "section", "source_sentence"]
    bare = json.loads(H.render_user(_inp(section=None, source_sentence=None, opposite=None)))
    assert list(bare) == ["label", "gloss"]
    # labels in the judge display form
    assert json.loads(H.render_user(_inp(label="careless (HEXACO)")))["label"] == "careless (from HEXACO)"
    samples = H.render_samples([_inp()], "SYSTEM")
    assert len(samples) == 2 and "source_sentence" in samples[0][2] and "source_sentence" not in samples[1][2]
    assert "left out" in samples[1][0]
    real = H.render_samples([_inp(), _inp(label="b", section=None, source_sentence=None)], "SYSTEM")
    assert real[1][0].startswith("without a source sentence ('b'")


def test_spread_covers_the_list():
    xs = [_inp(label=f"l{i}") for i in range(100)]
    got = H.spread(xs, 10)
    assert len(got) == 10 and got[0] is xs[0] and got[-1] is xs[-1]
    assert H.spread(xs, 500) == xs and H.spread(xs, 1) == [xs[0]]


# --------------------------------------------------------------------------- parsing

def _ans(**kw):
    d = {"reason": "Said of a person.", "label": "stands by one's word", "gloss": gl("keeping commitments"),
         "changed": True}
    d.update(kw)
    return d


def test_parse_plain_prose_first_and_fenced():
    a, err, notes = H.parse_answer(json.dumps(_ans()))
    assert err is None and a["label"] == "stands by one's word" and a["changed"] is True and notes == []
    a, err, notes = H.parse_answer("The trait is about keeping one's word.\n" + json.dumps(_ans()))
    assert err is None and "prose before the object" in notes
    a, err, notes = H.parse_answer("```json\n" + json.dumps(_ans()) + "\n```")
    assert err is None and "code fence removed" in notes
    a, err, _ = H.parse_answer(json.dumps(_ans()) + "\nHope that helps.")
    assert a is None and err.startswith("not_one_object")


def test_parse_failures():
    assert H.parse_answer("", "refusal")[1].startswith("refusal")
    assert H.parse_answer(None)[1].startswith("no_response")
    assert H.parse_answer("   ")[1].startswith("empty")
    assert H.parse_answer('{"reason": "x"')[1].startswith("not_")
    d = _ans()
    del d["changed"]
    assert H.parse_answer(json.dumps(d))[1] == "missing_key: changed"
    assert H.parse_answer(json.dumps(_ans(reason=" ")))[1] == "bad_value: reason"
    assert "5 words" in H.parse_answer(json.dumps(_ans(label="stands by every word given")))[1]
    assert "uses 'its'" in H.parse_answer(json.dumps(_ans(label="trusts its developer")))[1]
    assert "uses 'itself'" in H.parse_answer(json.dumps(_ans(label="protects itself")))[1]
    assert "underscore" in H.parse_answer(json.dumps(_ans(label="keeps_promises")))[1]
    assert "This means" in H.parse_answer(json.dumps(_ans(gloss="Keeping one's word.")))[1]
    assert H.parse_answer(json.dumps(_ans(changed="maybe")))[1].startswith("bad_value: changed")


def test_parse_soft_notes_and_changed_check():
    a, err, notes = H.parse_answer(json.dumps(_ans(changed="true")))
    assert err is None and a["changed"] is True and "changed given as text" in notes
    a, err, notes = H.parse_answer(json.dumps(_ans(label="gaming the system",
                                                   gloss="This means helping the user and the developer with its "
                                                         "work, " + " ".join(["always"] * 30) + ".")))
    assert err is None
    assert "label starts with an -ing word" in notes
    assert any(n.startswith("gloss ") and n.endswith(" words") for n in notes)
    assert "ai words in gloss: developer, user" in notes and "gloss uses its" in notes
    orig = ("stands by one's word", gl("keeping commitments"))
    a, err, notes = H.parse_answer(json.dumps(_ans(changed=True)), original=orig)
    assert a["differs"] is False and "changed true but the text is the same" in notes
    a, err, notes = H.parse_answer(json.dumps(_ans(changed=False)), original=("keeps its word", orig[1]))
    assert a["differs"] is True and "changed false but the text differs" in notes


# --------------------------------------------------------------------------- inputs and candidates

def _item(item_id, label, pole, partner_label, partner_id, rank, quote="The model should not lie."):
    return X.Item(item_id=item_id, chunk_id="model_spec:2026-08-18:do_not_lie", source="model_spec", label=label,
                  stem=normalize_to_file_name(label), gloss=G[label], partner_label=partner_label,
                  partner_item_id=partner_id, pole=pole, names_source=item_id.endswith("a"), type="behaviour",
                  enactability="chat", label_kind="ordinary", polysemy_flag=False, polysemy_note=None,
                  source_quote=quote, rank=rank, source_weight=1.0)


ITEMS = [_item("ms001-1a", "deceives its users", "vice", "candid", "ms001-1b", 1),
         _item("ms001-1b", "candid", "virtue", "deceives its users", "ms001-1a", 1),
         _item("ms002-1a", "flattering", "vice", "honest critic", "ms002-1b", 2),
         _item("ms003-1a", "schemes for itself", "vice", "transparent", "ms003-1b", 3)]


def _old_cands(run=OLD):
    return [Candidate(surface=it.label, generator="alignment_sweep", run_id=run, rank=it.rank, gloss_hint=it.gloss,
                      source_ref=it.chunk_id, partner_hint=it.partner_label) for it in ITEMS]


@pytest.fixture
def world(tmp_path):
    """A tmp registry holding one old sweep run's four rows (one shared with a census row, two reviewed), its
    extraction and a chunks file."""
    cdir = tmp_path / "candidates"
    rdir = cdir / "runs" / "alignment_sweep" / OLD
    rdir.mkdir(parents=True)
    X.write_extraction(ITEMS, rdir / X.EXTRACTION_NAME)
    ext = tmp_path / "external"
    ext.mkdir()
    (ext / "chunks.jsonl").write_text(json.dumps({"chunk_id": "model_spec:2026-08-18:do_not_lie", "source":
                                                  "model_spec", "heading": "Seek the truth > Do not lie",
                                                  "text": "...", "n_tokens_est": 3}) + "\n")
    reg = tmp_path / "registry.jsonl"
    submit_candidates([Candidate(surface="flattering", generator="censuses", run_id="2026-10-01-c",
                                 gloss_hint=CENSUS_GLOSS)], registry_path=reg, relabel=None)
    submit_candidates(_old_cands(), registry_path=reg, relabel=None)
    r = Registry(reg)
    for k in ("deceives_its_users#1", "candid#1", "flattering#1", "schemes_for_itself#1"):
        r.merge_block(k, "filter", {"verdict": "trait", "at": "2026-10-02T00:00:00+00:00"})
    r.merge_block("flattering#1", "review", {"status": "accepted", "at": "2026-10-03T00:00:00+00:00"})
    r.merge_block("schemes_for_itself#1", "review", {"status": "accepted", "at": "2026-10-03T00:00:00+00:00"})
    base = ["--registry", str(reg), "--candidates-dir", str(cdir), "--external-dir", str(ext)]
    return {"tmp": tmp_path, "reg": reg, "cdir": cdir, "base": base,
            "new_dir": cdir / "runs" / "alignment_sweep" / NEW}


def test_collect_inputs_dedupes_and_joins_the_extraction(world):
    rows = Registry(world["reg"]).fold()
    extra = dict(rows["candid#1"])        # a second row carrying candid's pair, and a source to skip of each kind
    extra["sources"] = rows["candid#1"]["sources"] + [
        {"generator": "alignment_sweep", "run_id": NEW, "surface": "x", "gloss_hint": "y"},
        {"generator": "alignment_sweep", "run_id": "r9", "surface": "x", "gloss_hint": "y",
         "source_ref": "a;humanize:r1:x"}]
    rows = {**rows, "candid#2": {**extra, "key": "candid#2"}}
    got = H.collect_inputs(rows, extraction={OLD: ITEMS}, headings={"model_spec:2026-08-18:do_not_lie": "Seek > Lie"},
                           exclude_runs=[NEW])
    assert [i.label for i in got] == ["candid", "deceives its users", "flattering", "schemes for itself"]
    candid = got[0]
    assert [s["key"] for s in candid.sources] == ["candid#1", "candid#2"]
    assert (candid.opposite, candid.section, candid.source_sentence, candid.pole, candid.item_id) == (
        "deceives its users", "Seek > Lie", "The model should not lie.", "virtue", "ms001-1b")
    assert got[2].reviews == {"flattering#1": "accepted"} and got[0].reviews == {}


def _rows_for(inputs, answers):
    recs = []
    for inp in inputs:
        if inp.label in answers:
            lab, g = answers[inp.label]
            a, _, _ = H.parse_answer(json.dumps({"reason": "r", "label": lab, "gloss": g, "changed": True}),
                                     original=(inp.label, inp.gloss))
            recs.append({"step": H.STEP, "prompt_id": inp.id, "ok": True, "items": [a], "custom_id": "c"})
    return H.rewrite_rows(inputs, recs)


def test_candidates_file_fields_partner_and_provenance(world, tmp_path):
    inputs = H.collect_inputs(Registry(world["reg"]).fold(), extraction={OLD: ITEMS})
    rows = _rows_for(inputs, NEW_ANSWERS)
    cands = H.to_candidates(rows, NEW)
    path = H.write_jsonl(cands, tmp_path / "candidates.jsonl")
    back = read_candidates(path)
    assert back == cands and len(cands) == 4
    for line in path.read_text().splitlines():
        assert tuple(json.loads(line)) == CANDIDATE_FIELDS
    by = {c.surface: c for c in cands}
    d = by["deceives people"]
    assert (d.generator, d.run_id, d.rank, d.gloss_hint, d.sense_id) == (
        "alignment_sweep", NEW, 1, NEW_ANSWERS["deceives its users"][1], 1)
    assert d.partner_hint == "candid" and by["candid"].partner_hint == "deceives people"   # mapped to the rewrites
    assert by["flattering"].partner_hint == "honest critic"                               # not rewritten: kept
    base, tag = H.split_source_ref(d.source_ref)
    assert base == "model_spec:2026-08-18:do_not_lie" and tag == {"run_id": OLD, "label": "deceives its users",
                                                                   "kept": False}
    # an unanswered input gives no candidate
    assert len(H.to_candidates(_rows_for(inputs, {"candid": NEW_ANSWERS["candid"]}), NEW)) == 1


def test_same_new_label_on_the_other_pole_is_a_second_sense(world):
    inputs = H.collect_inputs(Registry(world["reg"]).fold(), extraction={OLD: ITEMS})
    rows = _rows_for(inputs, {"deceives its users": ("candid", gl("a vice")), "candid": ("candid", gl("a virtue"))})
    senses = sorted((c.surface, c.sense_id, c.gloss_hint) for c in H.to_candidates(rows, NEW))
    assert [s[:2] for s in senses] == [("candid", 1), ("candid", 2)]


def test_source_ref_round_trip():
    assert H.split_source_ref(H.tag_source_ref("a:b:c", "r1", "x y")) == ("a:b:c", {"run_id": "r1", "label": "x y",
                                                                                    "kept": False})
    assert H.split_source_ref(H.tag_source_ref(None, "r1", "x", kept=True)) == (None, {"run_id": "r1", "label": "x",
                                                                                     "kept": True})
    assert H.split_source_ref("plain") == ("plain", None)


# --------------------------------------------------------------------------- the CLI end to end (fake client)

def _responder(answers=NEW_ANSWERS, refuse=(), tokens=(1600, 450)):
    seen: dict[str, int] = {}

    def respond(kw):
        d = json.loads(user_text(kw))
        seen[d["label"]] = seen.get(d["label"], 0) + 1
        if d["label"] in refuse and seen[d["label"]] <= refuse[d["label"]]:
            r = make_response("", output_tokens=0, stop_reason="refusal")
            r.stop_details = {"type": "refusal", "category": "reasoning_extraction"}
            return r
        lab, g = answers.get(d["label"], (d["label"], d["gloss"]))
        body = json.dumps({"reason": "Said of a person.", "label": lab, "gloss": g, "changed": True})
        return make_response("The trait, said of a person.\n" + body, input_tokens=tokens[0], output_tokens=tokens[1])
    return respond


def _run(world, monkeypatch, *argv, responder=None, batch=False):
    responder = responder or _responder()
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(responder))
    if batch:
        client = FakeBatchClient(responder)
        monkeypatch.setattr(CLI, "_batch_client", lambda: client)
    return CLI.main([*world["base"], *argv])


def _records(d: Path) -> list[dict]:
    return [json.loads(l) for l in (d / H.RESPONSES_NAME).read_text().splitlines() if l.strip()]


def test_cli_dry_run_and_render_write_nothing(world, monkeypatch, capsys):
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "4 distinct (label, gloss) inputs" in out and "total estimate $" in out and '"source_sentence"' in out
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--render") == 0
    out = capsys.readouterr().out
    assert out.startswith("SYSTEM (rubric alignment_humanize version 4") and "USER (without a source sentence" in out
    assert not world["new_dir"].exists()


def test_cli_budget_gate(world, monkeypatch, capsys):
    with pytest.raises(SystemExit) as e:
        _run(world, monkeypatch, "humanize", "--run-id", NEW, "--budget-usd", "0.001", "--dry-run")
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        _run(world, monkeypatch, "humanize", "--run-id", NEW, "--budget-usd", "25", "--dry-run")
    assert e.value.code == 2 and "over the $20 line" in capsys.readouterr().err
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--budget-usd", "25", "--confirm-expensive",
                "--confirmed-by", "Roger, test", "--dry-run") == 0
    assert not world["new_dir"].exists()


def test_cli_stops_at_the_cap_and_keeps_what_it_paid_for(world, monkeypatch, capsys):
    code = _run(world, monkeypatch, "humanize", "--run-id", NEW, "--budget-usd", "0.04", "--transport", "live",
                "--concurrency", "1", "--allow-dirty", responder=_responder(tokens=(1600, 6000)))
    assert code == 1 and "STOPPED at the cap" in capsys.readouterr().err
    recs = _records(world["new_dir"])
    assert len(recs) == 1 and recs[0]["ok"]
    usage = json.loads((world["new_dir"] / "usage.json").read_text())
    assert usage["n_calls"] == 1 and usage["total_cost_usd"] > 0.04
    assert len(read_candidates(world["new_dir"] / H.CANDIDATES_NAME)) == 1


def test_cli_live_refusals_recorded_counted_and_retried(world, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    resp = _responder(refuse={"candid": 1, "flattering": 5})    # candid refused once, flattering on both attempts
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty",
                responder=resp) == 0
    d = world["new_dir"]
    recs = _records(d)
    assert len(recs) == 6                                         # 4 first calls + 2 asked once more
    refusals = [r for r in recs if r["stop_reason"] == "refusal"]
    assert len(refusals) == 3 and all(not r["ok"] and r["failure"].startswith("stop_reason refusal") for r in refusals)
    assert all(r["usage_raw"] is not None and r["text"] is not None for r in recs)     # every response kept
    summ = json.loads((d / H.SUMMARY_NAME).read_text())
    assert (summ["n_answered"], summ["n_unanswered"], summ["n_refusals"]) == (3, 1, 3)
    assert summ["notes"].get("prose before the object") == 3
    assert "HIGH FAIL RATE" in caplog.text                     # 3 of 4 units answered
    rows = [json.loads(l) for l in (d / H.REWRITES_NAME).read_text().splitlines()]
    flat = next(r for r in rows if r["original"]["label"] == "flattering")
    assert flat["answer"] is None and len(flat["failures"]) == 2
    usage = json.loads((d / "usage.json").read_text())
    assert usage["n_calls"] == 6 and "claude-sonnet-5-5" in usage["per_model"]
    run = json.loads((d / "run.json").read_text())
    assert run["args"]["rubric"]["name"] == "alignment_humanize" and run["args"]["label_form"] == "judge-display-v1"
    # the sheet: the mark column second, each gloss column says whose gloss it is, files linked relative to it
    sheet = (d / H.SHEET_NAME).read_text()
    head = next(l for l in sheet.splitlines() if l.startswith("| # |"))
    cols = [c.strip() for c in head.strip("|").split("|")]
    assert cols[1] == "mark" and "the sweep's extraction" in cols[3] and "the humanize rewrite" in cols[5]
    assert "[rewrites.jsonl](rewrites.jsonl)" in sheet and "](responses.jsonl)" in sheet
    assert re.search(r"\[alignment_humanize\.md\]\((\.\./)+.*rubrics/alignment_humanize\.md\)", sheet)
    # without --resume a second run is refused; with it, only the unanswered input is sent
    with pytest.raises(SystemExit, match="pass --resume"):
        _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty")
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty",
                "--resume") == 0
    recs2 = _records(d)
    assert len(recs2) == 7 and recs2[-1]["meta"]["label"] == "flattering" and recs2[-1]["ok"]
    assert json.loads((d / H.SUMMARY_NAME).read_text())["n_unanswered"] == 0


def test_cli_pilot_then_batches(world, monkeypatch):
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--limit", "2", "--transport", "live",
                "--allow-dirty") == 0
    d = world["new_dir"]
    assert len(_records(d)) == 2 and len(H.read_inputs(d / H.INPUTS_NAME)) == 4     # every input frozen
    # Roger marks the pilot's sheet: the next session leaves it alone and writes its sheet beside it
    sheet = d / H.SHEET_NAME
    assert H.sheet_marks(sheet.read_text()) == 0
    sheet.write_text(sheet.read_text().replace("| 1 |  |", "| 1 | Y |"))
    assert H.sheet_marks(sheet.read_text()) == 1
    marked = sheet.read_text()
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "batches", "--resume",
                "--allow-dirty", batch=True) == 0
    recs = _records(d)
    assert len(recs) == 4 and all(r["ok"] for r in recs)
    batch = [r for r in recs if r["transport"] == "batches"]
    assert len(batch) == 2 and all(r["charged_as"] == "claude-sonnet-5-5:batch" for r in batch)
    assert (d / H.BATCHES_NAME).exists()
    assert sheet.read_text() == marked and len(list(d.glob("humanize_sheet.*.md"))) == 1
    run = json.loads((d / "run.json").read_text())
    forms = [s_["args"].get("label_form") for s_ in run["sessions"] if s_["args"].get("step") == "humanize"]
    assert forms == ["judge-display-v1", "judge-display-v1"]                    # the resumed session kept the form
    usage = json.loads((d / "usage.json").read_text())
    assert set(usage["per_model"]) == {"claude-sonnet-5-5", "claude-sonnet-5-5:batch"} and usage["n_calls"] == 4


def test_cli_submit_then_retract_keeps_reviewed_rows(world, monkeypatch, capsys):
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty") == 0
    d, reg = world["new_dir"], world["reg"]
    submit = ["humanize-submit", "--run-id", NEW, "--by", "tester", "--no-relabel",
              "--queue", str(world["tmp"] / "no_queue.json")]
    before_bytes = reg.read_bytes()
    capsys.readouterr()
    assert _run(world, monkeypatch, *submit, "--dry-run") == 0
    out = capsys.readouterr().out
    assert reg.read_bytes() == before_bytes and not (d / H.SUBMIT_REPORT_NAME).exists()
    assert "schemes_for_itself#1: review accepted; DROPPED by the retraction alone" in out
    assert "flattering#1: review accepted; kept by censuses/2026-10-01-c, first gloss unchanged" in out
    assert "carried into the new run unchanged: schemes_for_itself#1" in out
    assert "gap_registry.py retract --run alignment_sweep/2026-10-01-old --reason" in out
    assert "--transport batches" in out
    # live: submit first, then retract
    assert _run(world, monkeypatch, *submit) == 0
    r = Registry(reg)
    assert r.retracted_runs() == {("alignment_sweep", OLD)}
    v = r.fold()
    assert "deceives_its_users#1" not in v and "deceives_people#1" in v and not v["deceives_people#1"].get("filter")
    # Roger's reviewed rows: the shared one keeps its census gloss first; the sweep-only one keeps its old source
    assert v["flattering#1"]["review"]["status"] == "accepted"
    assert first_gloss_hint(v["flattering#1"]) == CENSUS_GLOSS
    s = v["schemes_for_itself#1"]
    assert s["review"]["status"] == "accepted" and first_gloss_hint(s) == G["schemes for itself"]
    assert [H.split_source_ref(x["source_ref"])[1] for x in s["sources"]] == [
        {"run_id": OLD, "label": "schemes for itself", "kept": True}]
    rep = json.loads((d / H.SUBMIT_REPORT_NAME).read_text())
    assert rep["kept"]["n"] == 1 and rep["retractions"][0]["written"] and not rep["retractions"][0]["refused"]
    # candid kept its label, its M1 block was on the old gloss: rejudged; flattering is settled: not
    assert rep["rejudge_keys"] == ["candid#1"]
    assert [l for l in (d / H.REJUDGE_KEYS_NAME).read_text().splitlines() if not l.startswith("#")] == ["candid#1"]
    assert rep["n_m1"] == 2                                       # deceives people, looks out for oneself
    cmds = rep["followups"]
    assert any("traithood_filter.py" in c and "--run alignment_sweep/" + NEW in c and "--transport batches" in c
               for c in cmds)
    assert any("traithood_filter.py" in c and "--keys $(grep -v '^#'" in c for c in cmds)
    assert any("novelty_score.py score" in c and "--keys-file" in c and "--rescore" in c for c in cmds)
    assert (d / H.KEYS_NAME).exists() and json.loads((d / "submit_report.json").read_text())["n_submitted"] == 5
    run = json.loads((d / "run.json").read_text())
    assert any(s_["args"].get("step") == "humanize-submit" and s_["args"]["by"] == "tester" for s_ in run["sessions"])
    # a completed submission is not run twice by accident; --again resubmits and keeps the rejudge keys
    with pytest.raises(SystemExit, match="Pass --again"):
        _run(world, monkeypatch, *submit)
    assert _run(world, monkeypatch, *submit, "--again") == 0
    again = json.loads((d / H.SUBMIT_REPORT_NAME).read_text())
    assert again["rejudge_keys"] == ["candid#1"] and again["old_runs"] == [] and again["already_retracted"] == [OLD]


def _add_mixed_row(world, label, *, review=None):
    """A row the sweep proposed first and a census also holds (its gloss second), with an M1 block."""
    reg = world["reg"]
    submit_candidates([Candidate(surface=label, generator="alignment_sweep", run_id=OLD, rank=9,
                                 gloss_hint=gl(f"being {label} towards the user"), source_ref="x:v:s")],
                      registry_path=reg, relabel=None)
    submit_candidates([Candidate(surface=label, generator="censuses", run_id="2026-10-01-c",
                                 gloss_hint=f"census gloss of {label}")], registry_path=reg, relabel=None)
    key = normalize_to_file_name(label) + "#1"
    Registry(reg).merge_block(key, "filter", {"verdict": "trait", "at": "2026-10-02T00:00:00+00:00"})
    if review:
        Registry(reg).merge_block(key, "review", {"status": review, "at": "2026-10-03T00:00:00+00:00"})
    return key


def test_cli_rejudge_covers_a_row_whose_census_gloss_comes_first(world, monkeypatch, capsys):
    key = _add_mixed_row(world, "misleading")
    answers = {**NEW_ANSWERS, "misleading": ("gives false impressions", gl("leaving others with a wrong picture"))}
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty",
                responder=_responder(answers)) == 0
    submit = ["humanize-submit", "--run-id", NEW, "--by", "t", "--no-relabel",
              "--queue", str(world["tmp"] / "no_queue.json")]
    capsys.readouterr()
    assert _run(world, monkeypatch, *submit, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "2 filtered rows whose first gloss changes (to another source's gloss: 1; to a rewrite: 1)" in out
    assert _run(world, monkeypatch, *submit) == 0
    v = Registry(world["reg"]).fold()
    assert first_gloss_hint(v[key]) == "census gloss of misleading"           # M1 saw the sweep's gloss
    rep_ = json.loads((world["new_dir"] / H.SUBMIT_REPORT_NAME).read_text())
    assert rep_["rejudge_keys"] == ["candid#1", key]
    assert key in rep_["retractions"][0]["gloss_hint_changed_after_run"]


def test_cli_settled_row_whose_gloss_would_change_needs_roger(world, monkeypatch, capsys):
    key = _add_mixed_row(world, "overbearing", review="accepted")
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty") == 0
    submit = ["humanize-submit", "--run-id", NEW, "--by", "t", "--no-relabel",
              "--queue", str(world["tmp"] / "no_queue.json")]
    capsys.readouterr()
    assert _run(world, monkeypatch, *submit, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "THE RETRACTION WILL REFUSE on 1 settled row(s)" in out and f"{key}: review accepted; its first gloss" in out
    assert "carried into the new run unchanged: overbearing" not in out           # a copy could not keep its gloss
    before_bytes = world["reg"].read_bytes()
    with pytest.raises(SystemExit, match="Ask Roger"):
        _run(world, monkeypatch, *submit)
    assert world["reg"].read_bytes() == before_bytes and not (world["new_dir"] / H.SUBMIT_REPORT_NAME).exists()
    # without the prediction the registry itself refuses: the outcome the dry run announced
    from assistant_axis.gapgen.registry import retract
    assert retract(world["reg"], "alignment_sweep", OLD, reason="t", by="t", dry_run=True).blocked[key] == \
        "review accepted"
    # with Roger's go the retraction is forced, and the record says which rows it overrode
    assert _run(world, monkeypatch, *submit, "--force-retract") == 0
    rep_ = json.loads((world["new_dir"] / H.SUBMIT_REPORT_NAME).read_text())
    assert rep_["retractions"][0]["forced"] and rep_["retractions"][0]["blocked"] == {key: "review accepted"}
    ctl = Registry(world["reg"]).controls()[f"retraction:alignment_sweep/{OLD}"]
    assert ctl["forced"] and ctl["effect"]["blocked_overridden"] == [key]


def test_cli_kept_copy_goes_in_ahead_of_a_rewrite_with_the_same_label(world, monkeypatch):
    """A settled row only the sweep held, whose rewrite keeps its label: the carried copy is submitted first, so the
    row's first gloss stays the one Roger reviewed and the retraction does not refuse."""
    reg = world["reg"]
    submit_candidates([Candidate(surface="stoic", generator="alignment_sweep", run_id=OLD, rank=8,
                                 gloss_hint=gl("bearing hardship without complaint"), source_ref="x:v:t")],
                      registry_path=reg, relabel=None)
    Registry(reg).merge_block("stoic#1", "review", {"status": "accepted", "at": "2026-10-03T00:00:00+00:00"})
    answers = {**NEW_ANSWERS, "stoic": ("stoic", gl("bearing hardship and loss without complaint"))}
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty",
                responder=_responder(answers)) == 0
    assert _run(world, monkeypatch, "humanize-submit", "--run-id", NEW, "--by", "t", "--no-relabel",
                "--queue", str(world["tmp"] / "no_queue.json")) == 0
    row = Registry(reg).fold()["stoic#1"]
    assert row["review"]["status"] == "accepted" and first_gloss_hint(row) == gl("bearing hardship without complaint")
    assert [H.split_source_ref(s["source_ref"])[1]["kept"] for s in row["sources"]] == [True, False]


def test_cli_second_pass_after_a_crash_is_not_complete(world, monkeypatch):
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty") == 0
    d = world["new_dir"]
    # a crash after the submission, before the first retraction was written
    (d / H.SUBMIT_REPORT_NAME).write_text(json.dumps({"submit": {"n_submitted": 5}, "old_runs": [OLD],
                                                      "retractions": [], "at": "x"}))
    assert _run(world, monkeypatch, "humanize-submit", "--run-id", NEW, "--by", "t", "--no-relabel",
                "--queue", str(world["tmp"] / "no_queue.json")) == 0
    assert Registry(world["reg"]).retracted_runs() == {("alignment_sweep", OLD)}


def test_cli_submit_refuses_unanswered(world, monkeypatch):
    assert _run(world, monkeypatch, "humanize", "--run-id", NEW, "--transport", "live", "--allow-dirty",
                responder=_responder(refuse={"candid": 9})) == 0
    with pytest.raises(SystemExit, match="1 of 4 inputs have no answer"):
        _run(world, monkeypatch, "humanize-submit", "--run-id", NEW, "--by", "t", "--no-relabel", "--dry-run")
    assert _run(world, monkeypatch, "humanize-submit", "--run-id", NEW, "--by", "t", "--no-relabel", "--dry-run",
                "--allow-unanswered") == 0


def test_cli_defaults():
    ap = CLI.build_parser()
    a = ap.parse_args(["humanize", "--run-id", NEW])
    assert (a.transport, a.budget_usd, a.model, a.limit, a.resume) == ("auto", 10.0, "claude-sonnet-5-5", None, False)
    s = ap.parse_args(["humanize-submit", "--run-id", NEW])
    assert s.no_relabel is False and s.allow_unanswered is False


# --------------------------------------------------------------------------- pure helpers

def _src(gen, run, surface, gloss):
    return {"generator": gen, "run_id": run, "surface": surface, "gloss_hint": gloss, "source_ref": "r", "rank": 1,
            "score": None, "partner_hint": None}


def test_kept_candidates_carry_only_the_drop_case_and_blocks_are_predicted():
    raw = {"a#1": {"key": "a#1", "surface": "a", "sense_id": 1, "review": {"status": "rejected"},
                   "sources": [_src("alignment_sweep", OLD, "a", "ga")]},
           "b#1": {"key": "b#1", "surface": "b", "sense_id": 1, "review": {"status": "accepted"},
                   "sources": [_src("alignment_sweep", OLD, "b", "gb"), _src("censuses", "c", "b", "gc")]},
           "c#1": {"key": "c#1", "surface": "c", "sense_id": 1, "review": {"status": "unreviewed"},
                   "sources": [_src("alignment_sweep", OLD, "c", "gx")]},
           "d#1": {"key": "d#1", "surface": "d", "sense_id": 1, "review": {"status": "unreviewed"},
                   "seed_queue_stem": None, "sources": [_src("censuses", "c", "d", "gd"),
                                                         _src("alignment_sweep", OLD, "d", "gy")]}}
    kept, why = H.kept_candidates(raw, active=set(), old_runs=[OLD], run_id=NEW)
    # a is dropped: carried.  b keeps a census source but its first gloss would change: a copy appended after the
    # census source could not keep it, so b is not carried; it is a predicted block instead
    assert list(why) == ["a#1"] and "drops it" in why["a#1"]
    assert [(c.surface, c.gloss_hint, c.run_id) for c in kept] == [("a", "ga", NEW)]
    assert H.split_source_ref(kept[0].source_ref)[1] == {"run_id": OLD, "label": "a", "kept": True}
    before = dict(raw)
    final = H.final_view(raw, kept, active=set(), old_runs=[OLD])
    assert first_gloss_hint(final["a#1"]) == "ga" and first_gloss_hint(final["b#1"]) == "gc" and "c#1" not in final
    blocks = H.predicted_blocks(before, final, old_runs=[OLD])
    assert list(blocks) == ["b#1"] and "first gloss hint would change from 'gb' to 'gc'" in blocks["b#1"]
    # the registry's time rule: reviewed before the old run began, the gloss change is not a block
    raw["b#1"]["review"]["at"] = "2026-09-01T00:00:00+00:00"
    assert H.predicted_blocks(before, final, old_runs=[OLD], run_starts={OLD: "2026-10-01T00:00:00+00:00"}) == {}
    assert list(H.predicted_blocks(before, final, old_runs=[OLD], run_starts={OLD: None})) == ["b#1"]


def test_rejudge_keys_cover_rewrites_and_glosses_the_retraction_moves():
    before = {"x#1": {"filter": {"v": 1}, "review": {}, "sources": [_src("alignment_sweep", OLD, "x", "old")]},
              "y#1": {"filter": {"v": 1}, "review": {}, "sources": [_src("censuses", "c", "y", "gc")]},
              "m#1": {"filter": {"v": 1, "at": "2026-10-05T00:00:00+00:00"}, "review": {},
                      "sources": [_src("alignment_sweep", OLD, "m", "gm"), _src("censuses", "c", "m", "gc")]},
              "s#1": {"filter": {"v": 1}, "review": {"status": "accepted"},
                      "sources": [_src("alignment_sweep", OLD, "s", "gs"), _src("censuses", "c", "s", "gc")]}}
    after = {"x#1": {"filter": {"v": 1}, "review": {}, "sources": [_src("alignment_sweep", NEW, "x", "new")]},
             "y#1": {"filter": {"v": 1}, "review": {}, "sources": [_src("censuses", "c", "y", "gc"),
                                                                   _src("alignment_sweep", NEW, "y", "new")]},
             "z#1": {"review": {}, "sources": [_src("alignment_sweep", NEW, "z", "new")]},
             "w#1": {"filter": {"v": 1}, "review": {"status": "accepted"},
                     "sources": [_src("alignment_sweep", NEW, "w", "new")]},
             "m#1": {"filter": {"v": 1}, "review": {}, "sources": [_src("censuses", "c", "m", "gc")]},
             "s#1": {"filter": {"v": 1}, "review": {"status": "accepted"}, "sources": [_src("censuses", "c", "s", "gc")]}}
    keys = ["x#1", "y#1", "z#1", "w#1"]
    assert H.rejudge_keys(before, after, keys, run_id=NEW) == ["x#1"]              # m#1 missed without the moves
    moved = H.gloss_moved(before, after, old_runs=[OLD])
    assert moved == ["m#1", "s#1", "x#1"]
    assert H.rejudge_keys(before, after, keys, run_id=NEW, moved=moved) == ["m#1", "x#1"]    # s#1 settled
    # M1 judged m#1 before the old run began: the gloss it was shown was not the run's, so it is not moved
    assert "m#1" not in H.gloss_moved(before, after, old_runs=[OLD], run_starts={OLD: "2026-10-09T00:00:00+00:00"})


def test_submission_complete_needs_every_retraction_written():
    run = f"alignment_sweep/{OLD}"
    assert not H.submission_complete(None) and not H.submission_complete({"old_runs": [OLD]})
    crashed = {"submit": {"n_submitted": 4}, "old_runs": [OLD], "retractions": []}
    assert not H.submission_complete(crashed)
    assert not H.submission_complete({**crashed, "retractions": [{"run": run, "written": False, "refused": "x"}]})
    assert H.submission_complete({**crashed, "retractions": [{"run": run, "written": True, "refused": None}]})
    assert H.submission_complete({"submit": {}, "old_runs": [], "retractions": []}) is False   # nothing submitted
    assert H.submission_complete({"submit": {"n": 1}, "old_runs": [], "retractions": []})


def test_estimate_batches_half_price():
    rub = {"text": "S" * 4000, "name": H.RUBRIC_NAME, "version": 1, "sha256": "x"}
    calls = H.build_calls([_inp(), _inp(label="other")], rubric=rub)
    live, batch = H.estimate_usd(calls), H.estimate_usd(calls, batch=True)
    assert live > 0 and abs(batch - live / 2) < 1e-9
    assert all(c.temperature is None and c.step == H.STEP and c.family == H.FAMILY for c in calls)
    assert "humanize: 2 calls" in H.estimate_line(calls, batch=True)
