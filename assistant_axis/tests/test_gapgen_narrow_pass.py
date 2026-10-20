"""The narrow pass (``assistant_axis/gapgen/narrow_pass.py``, ``data_analysis/gap_generation/narrow_pass.py``; QUESTIONS
208 (3), Roger 2026-10-20: at most one narrow trait per parent goes to review, the rest held): the parser, the
plurality, the candidates and their parents, the grouping and the cap, the held rows on the holding list with their
parent, the cap across runs, the review graph leaving held rows out, the pinned prompt and its word hygiene, and the
command end to end, live and through the batch transport, with the repository's fake clients (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import narrow_pass as NP
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text


def ans(relation, reason="Because."):
    return json.dumps({"reason": reason, "relation": relation})


def reading(stem, s, o=None, *, cos=0.5, rel="similar", queue=False):
    r = {"stem": stem, "cosine": cos, "relation": rel, "via": "retrieved", "sonnet": {"value": s, "reason": "r"},
         "opus": {"value": o, "reason": "r"} if o is not None else None}
    if queue:
        r["queue_status"] = "candidate"
    return r


def row(stem, readings, *, decision="new", holding=None, review="unreviewed", run=("gen", "r1"), narrow=None,
        gloss=None, m3_batch="m3b"):
    r = {"schema_version": 1, "key": f"{stem}#1", "stem": stem, "sense_id": 1, "surface": stem.replace("_", " "),
         "label": stem.replace("_", " "), "gloss": gloss or f"This means being {stem.replace('_', ' ')} in one area.",
         "entity_type": "trait",
         "sources": [{"generator": run[0], "run_id": run[1], "surface": stem, "source_ref": None}],
         "filter": {"verdict": "trait"},
         "novelty": {"run_id": m3_batch, "decision": decision, "readings": readings,
                     "listed": [{k: v for k, v in x.items() if k in ("stem", "cosine", "relation", "queue_status")}
                                for x in readings]},
         "holding": holding, "review": {"status": review}, "rev": 1}
    if narrow is not None:
        r["narrow"] = narrow
    return r


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    t = d / "traits" / "instructions"
    t.mkdir(parents=True)
    for stem, desc in (("frugal", "This means spending little and saving carefully."),
                       ("dominant", "This means taking charge and controlling others."),
                       ("boastful", "This means talking up one's own achievements."),
                       ("calm", "This means staying even-tempered.")):
        (t / f"{stem}.json").write_text(json.dumps({"positive_label": stem, "description": desc}))
    (d / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "thrifty_q", "label": "thrifty", "entity_type": "trait", "status": "candidate",
         "description_draft": "This means making do with little."}]}))
    return d


def lookup(data_dir):
    return NP.TextLookup(data_dir)


# --------------------------------------------------------------------------- parser and plurality

class TestParse:
    def test_plain_fence_prose_and_refusals(self):
        a, err, notes = NP.parse_answer(ans("narrower"))
        assert err is None and a == {"reason": "Because.", "relation": "narrower"} and notes == []
        a, err, notes = NP.parse_answer("Thinking aloud.\n" + ans("Same"))
        assert a["relation"] == "same" and "prose before the object" in notes and "relation normalised" in notes
        assert NP.parse_answer("```json\n" + ans("broader") + "\n```")[0]["relation"] == "broader"
        for text, kind in ((ans("narrower") + "\nok", "not_one_object"), ('{"relation": "same"}', "missing_key"),
                           (ans("wider"), "bad_value"), ("", "empty"), (None, "no_response")):
            assert NP.parse_answer(text)[1].startswith(kind), text
        assert NP.parse_answer(ans("same"), "refusal")[1].startswith("refusal")

    def test_plurality_and_ties(self):
        p = lambda *vs: [{"relation": v, "reason": "r"} for v in vs]  # noqa: E731
        assert NP.combine(p("narrower", "narrower", "same"))["verdict"] == "narrower"
        assert NP.combine(p("narrower", "same", "different"))["verdict"] == "tie"
        assert NP.combine(p("narrower", "same"))["verdict"] == "tie"
        assert NP.combine(p("narrower"))["verdict"] == "narrower"        # one reading answered: combined, not gated
        assert NP.combine([])["verdict"] is None


# --------------------------------------------------------------------------- candidates and parents

def test_candidates_and_their_one_or_two_parents(data_dir):
    rows = {r["key"]: r for r in [
        # best by either model: Sonnet 1, Opus 2 counts; the opposed 4 is never a parent; three at 2+, two asked
        row("penny_wise", [reading("frugal", 1, 2, cos=0.6), reading("calm", 4, cos=0.3, rel="opposed"),
                           reading("boastful", 3, 3, cos=0.4), reading("dominant", 2, cos=0.7)]),
        row("save_queue", [reading("thrifty_q", 3, cos=0.6, queue=True)]),
        row("low_only", [reading("frugal", 1, cos=0.6)]),
        row("covered_one", [reading("frugal", 4, 4)], decision="covered"),
        row("on_states", [reading("frugal", 3)], holding="states_released"),
        row("reviewed", [reading("frugal", 3)], review="accepted"),
        row("judged", [reading("frugal", 3)], narrow={"status": "not_narrow"}),
        row("unknown_parent", [reading("vanished", 3)]),
    ]}
    items, skipped = NP.select(rows, lookup(data_dir), scope=lambda r: True)
    by = {it.key: it for it in items}
    assert set(by) == {"penny_wise#1", "save_queue#1"}
    pw = by["penny_wise#1"]
    # best 3 first, then the two 2s by final reading (dominant's final 2 vs frugal's final 2) and cosine
    assert [p.stem for p in pw.parents] == ["boastful", "dominant"]
    assert pw.parents[0].key == "trait:boastful" and pw.parents[0].reading == "3/3"
    q = by["save_queue#1"].parents[0]
    assert q.key == "queue:thrifty_q" and q.kind == "queue" and q.label == "thrifty"
    assert q.description == "This means making do with little."
    assert skipped == {"held_states_released": 1, "judged_already": 1, "m3_covered": 1, "no_parent_text": 1,
                       "no_reading_at_2": 1, "reviewed_or_promoted": 1}


def test_the_user_turn_shows_the_judge_display_form(data_dir):
    it = NP.Item(key="x#1", stem="x", label="open_ended", gloss="This means g.", parents=[])
    p = NP.Parent(key="trait:careless_hexaco", stem="careless_hexaco", kind="corpus", label="careless (HEXACO)",
                  description="This means d.", best=3, final=3, reading="3/-", cosine=0.5)
    u = json.loads(NP.build_user(it, p))
    assert u == {"candidate": {"label": "open ended", "description": "This means g."},
                 "existing": {"label": "careless (from HEXACO)", "description": "This means d."}}


# --------------------------------------------------------------------------- the cap

def judged(key, parent, final, status="narrower"):
    return {"key": key, "label": key.split("#")[0], "asked": [], "status": status,
            "parent": parent if status == "narrower" else None, "parent_label": None,
            "parent_final": final if status == "narrower" else None}


def test_one_child_per_parent_the_most_distinct_kept_the_rest_held():
    ds = NP.assign([judged("a#1", "trait:frugal", 3), judged("b#1", "trait:frugal", 2), judged("c#1", "trait:frugal", 3),
                    judged("d#1", "trait:dominant", 2), judged("e#1", None, None, status="not_narrow"),
                    judged("f#1", None, None, status="no_answer")], earlier={}, seed=0)
    by = {d["key"]: d for d in ds}
    assert by["b#1"]["status"] == "kept" and by["b#1"]["n_children"] == 3       # the lowest final reading
    assert by["a#1"]["status"] == by["c#1"]["status"] == "held"
    assert by["a#1"]["kept_child"] == "b#1" and by["a#1"]["held_because"] == "sibling"
    assert by["d#1"]["status"] == "kept" and by["d#1"]["n_children"] == 1
    assert by["e#1"]["status"] == "not_narrow" and by["f#1"]["status"] == "no_answer"
    assert NP.counts(ds) == {"kept": 2, "held": 2, "not_narrow": 1, "no_answer": 1, "parents": 2,
                             "held_earlier_run": 0}


def test_ties_are_broken_by_a_seeded_random_choice():
    kids = [judged(f"k{i}#1", "trait:frugal", 2) for i in range(6)]
    picks = {s: next(d["key"] for d in NP.assign(kids, earlier={}, seed=s) if d["status"] == "kept") for s in range(8)}
    assert picks == {s: next(d["key"] for d in NP.assign(kids, earlier={}, seed=s) if d["status"] == "kept")
                     for s in range(8)}                                              # deterministic
    assert len(set(picks.values())) > 1                                              # and the seed matters
    assert all(d["tie_broken"] for d in NP.assign(kids, earlier={}, seed=0) if d["status"] == "kept")


def test_the_cap_holds_across_runs():
    rows = {"old#1": {"narrow": {"status": "kept", "parent": "trait:frugal"}},
            "older#1": {"narrow": {"status": "held", "parent": "trait:frugal"}},
            "now#1": {"narrow": {"status": "kept", "parent": "trait:calm"}}}
    earlier = NP.earlier_kept(rows, exclude=["now#1"])
    assert earlier == {"trait:frugal": "old#1"}
    ds = NP.assign([judged("new#1", "trait:frugal", 1), judged("x#1", "trait:calm", 2)], earlier=earlier)
    by = {d["key"]: d for d in ds}
    assert by["new#1"]["status"] == "held" and by["new#1"]["kept_child"] == "old#1"
    assert by["new#1"]["held_because"] == "earlier_run" and by["x#1"]["status"] == "kept"


def test_held_rows_go_on_the_holding_list_with_their_parent():
    ds = NP.assign([judged("a#1", "trait:frugal", 3), judged("b#1", "trait:frugal", 2),
                    judged("e#1", None, None, status="not_narrow")], earlier={})
    rub = {"name": NP.RUBRIC_NAME, "version": 1, "sha256": "s"}
    up = NP.registry_updates(ds, run_id="nb", rubric=rub, model=NP.DEFAULT_MODEL, readings=3, seed=0, now="t")
    assert up["a#1"]["holding"] == "narrow" and up["a#1"]["narrow"]["parent"] == "trait:frugal"
    assert up["a#1"]["narrow"]["status"] == "held" and up["a#1"]["narrow"]["kept_child"] == "b#1"
    assert "holding" not in up["b#1"] and up["b#1"]["narrow"]["parent"] == "trait:frugal"
    assert up["e#1"]["narrow"]["status"] == "not_narrow" and "holding" not in up["e#1"]
    with pytest.raises(ValueError):
        NP.registry_updates([judged("z#1", "trait:x", 1)], run_id="nb", rubric=rub, model="m", readings=3, seed=0,
                            now="t")


def test_the_holding_list_and_the_block_are_known_to_the_platform():
    from assistant_axis.gapgen.normalize import HOLDING
    from assistant_axis.gapgen.registry import BLOCKS
    assert NP.HOLDING in HOLDING and NP.BLOCK in BLOCKS


def test_the_review_graph_leaves_held_rows_out():
    from assistant_axis.gapgen import review_graph as RG
    rows = {"a#1": row("a", []), "b#1": row("b", [], holding="narrow"), "c#1": row("c", [], decision="covered")}
    kept, covered, skipped, _ = RG.select_rows(rows, ["m3b"])
    assert set(kept) == {"a#1"} and set(covered) == {"c#1"} and skipped == {"held_narrow": 1}


# --------------------------------------------------------------------------- the prompt

def test_the_prompt_is_pinned_and_its_words_are_not_corpus_or_queue_words():
    from assistant_axis.entity_id import normalize_to_file_name
    from assistant_axis.gapgen.generators.structural.prompts import forbidden_stems
    from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
    assert sr.GENERATOR_FILES[NP.RUBRIC_NAME] == "narrow_direction.md" and NP.RUBRIC_NAME in sr.PINNED_NAMES
    rub = NP.load_rubric()
    assert rub["version"] == 1 and rub["sha256"] == sr.sha256(rub["text"])
    text = rub["text"]
    assert '"reason"' in text and text.index('"reason"') < text.index('"relation": "narrower"')
    assert "think" not in text.lower()                  # a short reason, never the model's thinking (Sonnet 5.5)
    forbidden = forbidden_stems()
    hits = sorted(w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden and w not in PROSE_ALLOWED)
    assert hits == []
    for w in ("opera", "music", "spotless", "desk", "tidiness"):          # the invented examples
        assert normalize_to_file_name(w) not in forbidden


def test_the_rubric_file_carries_a_rendered_sample():
    doc = sr.rubric_path(NP.RUBRIC_NAME).read_text()
    i = doc.index("## Rendered sample")
    sample = doc[i:]
    assert '{"candidate": {"label": ' in sample and '"existing": {"label": ' in sample


# --------------------------------------------------------------------------- the command, end to end

def responder_by_label(table):
    """Answers by the candidate's label and the parent's label in the user turn."""
    def respond(kw):
        u = json.loads(user_text(kw))
        rel = table.get((u["candidate"]["label"], u["existing"]["label"]), "different")
        if rel == "REFUSE":
            return make_response("", stop_reason="refusal", output_tokens=0)
        return ans(rel)
    return respond


@pytest.fixture
def world(tmp_path, data_dir, monkeypatch):
    from data_analysis.gap_generation import narrow_pass as CLI
    monkeypatch.setattr(CLI, "platform_dirty_files", lambda: [])
    reg = tmp_path / "cand" / "registry.jsonl"
    reg.parent.mkdir(parents=True)
    rows = [row("debt_averse", [reading("frugal", 3, 3)]),
            row("coupon_clipping", [reading("frugal", 2, cos=0.6)]),
            row("penny_hoarding", [reading("frugal", 3, cos=0.4)]),
            row("bossy_at_work", [reading("dominant", 2, 3), reading("boastful", 2)]),
            row("brag_humbly", [reading("boastful", 2, cos=0.5)]),
            row("unrelated_one", [reading("calm", 1)]),
            row("other_run", [reading("frugal", 3)], run=("gen", "r2"))]
    reg.write_text("".join(json.dumps(r) + "\n" for r in rows))
    table = {("debt averse", "frugal"): "narrower", ("coupon clipping", "frugal"): "narrower",
             ("penny hoarding", "frugal"): "narrower", ("bossy at work", "dominant"): "narrower",
             ("brag humbly", "boastful"): "same", ("other run", "frugal"): "narrower"}
    client = FakeAsyncAnthropic(responder_by_label(table))
    monkeypatch.setattr(CLI, "_client", lambda: client)
    base = ["--registry", str(reg), "--data-dir", str(data_dir), "--candidates-dir", str(tmp_path / "cand")]
    return {"CLI": CLI, "reg": reg, "client": client, "base": base, "cand": tmp_path / "cand", "table": table,
            "tmp": tmp_path}


def _tree(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_dry_run_writes_nothing_and_renders_the_prompt(world, capsys):
    before = _tree(world["tmp"])
    assert world["CLI"].main(world["base"] + ["--batch-id", "nb1", "--run", "gen/r1", "--dry-run", "--render"]) == 0
    out = capsys.readouterr().out
    assert "5 candidates" in out and "=== system turn: narrow_direction version 1" in out
    assert '"existing": {"label": "dominant"' in out and "DRY-RUN: would make 18 calls" in out
    assert _tree(world["tmp"]) == before and world["client"].calls == []


def test_end_to_end_live_then_a_second_run_holds_under_the_earlier_kept_child(world, capsys, caplog):
    import logging
    caplog.set_level(logging.INFO)
    CLI = world["CLI"]
    assert CLI.main(world["base"] + ["--batch-id", "nb1", "--run", "gen/r1"]) == 0
    assert len(world["client"].calls) == 18                      # 6 pairs (bossy_at_work has two) x 3 readings
    rows = Registry(world["reg"]).fold()
    # frugal's three children: coupon_clipping (final 2) kept, the two 3s held
    assert rows["coupon_clipping#1"]["narrow"]["status"] == "kept" and rows["coupon_clipping#1"]["holding"] is None
    for k in ("debt_averse#1", "penny_hoarding#1"):
        assert rows[k]["holding"] == "narrow" and rows[k]["narrow"]["parent"] == "trait:frugal"
        assert rows[k]["narrow"]["kept_child"] == "coupon_clipping#1"
    assert rows["bossy_at_work#1"]["narrow"]["status"] == "kept"
    assert rows["bossy_at_work#1"]["narrow"]["parent"] == "trait:dominant"
    assert [a["votes"] for a in rows["bossy_at_work#1"]["narrow"]["asked"]] == [["narrower"] * 3, ["different"] * 3]
    assert rows["brag_humbly#1"]["narrow"]["status"] == "not_narrow" and rows["brag_humbly#1"]["holding"] is None
    assert "narrow" not in rows["unrelated_one#1"]
    out = world["cand"] / "narrow_pass" / "nb1"
    usage = json.loads((out / "usage.json").read_text())
    assert usage["n_calls"] == 18 and usage["total_cost_usd"] > 0
    doc = json.loads((out / "decisions.json").read_text())
    assert doc["counts"] == {"kept": 2, "held": 2, "not_narrow": 1, "no_answer": 0, "parents": 2,
                             "held_earlier_run": 0}
    readout = (out / "readout.md").read_text()
    assert "## The parents" in readout and "coupon clipping (2)" in readout
    assert "parse rate: 18/18 OK" in caplog.text
    # a second run over another generator run: its frugal child is held under the earlier kept one
    capsys.readouterr()
    assert CLI.main(world["base"] + ["--batch-id", "nb2", "--run", "gen/r2"]) == 0
    r2 = Registry(world["reg"]).fold()["other_run#1"]
    assert r2["holding"] == "narrow" and r2["narrow"]["held_because"] == "earlier_run"
    assert r2["narrow"]["kept_child"] == "coupon_clipping#1"
    # a third run over r1 asks nothing: every row is judged already or held
    assert CLI.main(world["base"] + ["--batch-id", "nb3", "--run", "gen/r1", "--dry-run"]) == 0
    assert "0 candidates" in capsys.readouterr().out


def test_answers_on_record_need_resume_and_are_reused(world, capsys):
    CLI = world["CLI"]
    args = world["base"] + ["--batch-id", "nb1", "--keys", "brag_humbly#1"]
    assert CLI.main(args) == 0 and len(world["client"].calls) == 3
    # the row is now judged; a fresh row in the same out dir needs --resume
    reg = Registry(world["reg"])
    r = reg.fold()["brag_humbly#1"]
    r.pop("narrow")
    reg.write([r])
    assert CLI.main(args) == 2
    assert CLI.main(args + ["--resume"]) == 0 and len(world["client"].calls) == 3      # every answer reused


def test_refusals_count_as_failed_calls_and_trip_the_parse_rate_warning(world, caplog):
    world["table"][("brag humbly", "boastful")] = "REFUSE"
    assert world["CLI"].main(world["base"] + ["--batch-id", "nb1", "--keys", "brag_humbly#1"]) == 0
    assert "*** HIGH FAIL RATE ***" in caplog.text
    assert Registry(world["reg"]).fold()["brag_humbly#1"]["narrow"]["status"] == "no_answer"


def test_over_budget_is_refused_before_any_call(world):
    assert world["CLI"].main(world["base"] + ["--batch-id", "nb1", "--run", "gen/r1", "--budget-usd", "0.0001"]) == 2
    assert world["client"].calls == [] and not (world["cand"] / "narrow_pass").exists()


def test_end_to_end_through_the_batch_transport(world, monkeypatch):
    from assistant_axis.gapgen import batches as B
    from assistant_axis.tests.test_gapgen_batches import FakeBatchClient
    responder = responder_by_label(world["table"])
    bc = FakeBatchClient(lambda kw: make_response(responder(kw)))
    monkeypatch.setattr(world["CLI"], "_batch_client", lambda: bc)

    async def no_sleep(_s):
        return None
    monkeypatch.setattr(B.asyncio, "sleep", no_sleep)
    assert world["CLI"].main(world["base"] + ["--batch-id", "nbb", "--run", "gen/r1", "--transport", "batches"]) == 0
    assert len(bc.batches.created) == 1 and len(bc.batches.created[0]["requests"]) == 18
    assert world["client"].calls == []
    out = world["cand"] / "narrow_pass" / "nbb"
    usage = json.loads((out / "usage.json").read_text())
    assert list(usage["per_model"]) == ["claude-haiku-5-5:batch"]
    assert json.loads((out / "batches.json").read_text())["waves"]["narrow"][0]["status"] == "collected"
    assert Registry(world["reg"]).fold()["coupon_clipping#1"]["narrow"]["status"] == "kept"
