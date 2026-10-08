"""The Roget head-scope call (workstream 2; QUESTIONS 44, Roger 2026-10-08): one Haiku 5.5 rating per head
of whether its adjectives describe a person's character, and its use by the coverage map and the harvest.
No network: a fake Anthropic client."""
from __future__ import annotations

import asyncio
import json

import pytest

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.generators.roget import coverage as C
from assistant_axis.gapgen.generators.roget import harvest as H
from assistant_axis.gapgen.generators.roget import head_scope as S
from assistant_axis.gapgen.generators.roget import pairs as PR
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.roget_fakes import make_index

SYSTEM = "Rate each head.\n" + '{"results": [{"id": "<id>", "reason": "<r>", "character": 0|1|2}]}'


def world():
    idx = make_index([
        {"id": "604", "title": "Resolution", "adj": [["resolute", "determined"], ["firm", "resolute"]]},
        {"id": "605", "title": "Irresolution", "adj": [["irresolute"], ["wavering"]]},
        {"id": "606", "title": "Obstinacy", "noun": [["obstinacy"]]},                       # no adjectives
        {"id": "814", "title": "Dearness", "adj": [["dear", "costly"], ["above price"], ["overpriced"]],
         "klass": "V", "section": "IV. Possessive relations", "subsection": "4. Monetary relations"},
        {"id": "815", "title": "Cheapness", "adj": [["cheap"], ["half price"]],
         "klass": "V", "section": "IV. Possessive relations", "subsection": "4. Monetary relations"},
        {"id": "837", "title": "Dejection", "adj": [[f"glum{i}" for i in range(30)]], "klass": "VI",
         "section": "II. Personal affections", "subsection": "1. Passive affections"},
    ])
    return idx


def responder(ratings: dict, *, drop=(), bad=None):
    """A fake model: rates every head it is sent from ``ratings``; leaves out the ids in ``drop`` on the first
    call that holds them; ``bad`` makes every call return that text."""
    seen: set = set()

    def respond(kw):
        if bad is not None:
            return bad
        ids = [h["id"] for h in json.loads(user_text(kw))["heads"]]
        rows = []
        for i in ids:
            if i in drop and i not in seen:
                seen.add(i)
                continue
            rows.append({"id": i, "reason": f"because {i}", "character": ratings.get(i, 2)})
        return "```json\n" + json.dumps({"results": rows}) + "\n```"
    return respond


# --------------------------------------------------------------------------- items, batches, prompt

def test_head_item_dedupes_caps_and_cleans_titles():
    idx = world()
    it = S.head_item(idx.heads["604"])
    assert it.adjectives == ["resolute", "determined", "firm"]          # Roget's order, repeats removed
    assert it.n_adjectives == 3
    assert it.payload() == {"id": "604", "title": "Resolution", "class": "Words relating to the voluntary powers",
                            "section": "Volition in general", "adjectives": ["resolute", "determined", "firm"]}
    big = S.head_item(idx.heads["837"])
    assert len(big.adjectives) == S.MAX_ADJECTIVES == 20 and big.n_adjectives == 30
    assert big.adjectives[:2] == ["glum0", "glum1"]
    assert S.section_title("IV. Possessive relations") == "Possessive relations"
    assert S.section_title("Possessive relations") == "Possessive relations"


def test_scope_items_skip_heads_without_adjectives():
    idx = world()
    items, skipped = S.scope_items(idx, ["604", "605", "606", "814"])
    assert [i.id for i in items] == ["604", "605", "814"] and skipped == ["606"]


@pytest.mark.parametrize("n,size,expect", [(45, 20, [15, 15, 15]), (20, 20, [20]), (21, 20, [11, 10]),
                                           (3, 20, [3]), (0, 20, [])])
def test_batches_are_consecutive_and_balanced(n, size, expect):
    items = [S.HeadItem(str(i), "t", "V", "c", "s", ["a"], 1) for i in range(n)]
    got = S.make_batches(items, size)
    assert [len(b) for b in got] == expect
    assert [i.id for b in got for i in b] == [str(i) for i in range(n)]       # text order kept


def test_render_user_is_one_head_per_line_and_valid_json():
    idx = world()
    batch = [S.head_item(idx.heads[h]) for h in ("604", "814")]
    u = S.render_user(batch)
    lines = u.split("\n")
    assert lines[0] == '{"heads": [' and lines[-1] == " ]}" and len(lines) == 4
    d = json.loads(u)
    assert [h["id"] for h in d["heads"]] == ["604", "814"]
    assert d["heads"][1]["section"] == "Possessive relations"
    assert d["heads"][1]["adjectives"] == ["dear", "costly", "above price", "overpriced"]


def test_rubric_is_pinned_and_reason_comes_first():
    rub = S.load_rubric()
    assert rub["name"] == S.RUBRIC_NAME == "roget_head_scope"
    assert sr.current_versions(names=sr.GENERATOR_NAMES)[S.RUBRIC_NAME] == (rub["version"], rub["sha256"])
    assert rub["sha256"] == sr.sha256(rub["text"])
    t = rub["text"]
    assert t.index('"reason"') < t.index('"character"')
    assert "0|1|2" in t


def test_load_rubric_refuses_an_unpinned_text(tmp_path):
    d = tmp_path / "rubrics"
    d.mkdir()
    src = sr.rubric_path(S.RUBRIC_NAME)
    (d / src.name).write_text(src.read_text(encoding="utf-8").replace("Each item below", "Every item below"),
                              encoding="utf-8")
    (d / "versions.json").write_text(sr.versions_path().read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(S.RubricNotPinned, match="roget_head_scope"):
        S.load_rubric(d)


# --------------------------------------------------------------------------- parsing

def test_parse_ratings():
    ok = json.dumps({"results": [{"id": "604", "reason": "r1", "character": 2},
                                 {"id": 605, "reason": "r2", "character": "1"},
                                 {"id": "814", "reason": "r3", "character": 3},
                                 {"id": "999", "reason": "x", "character": 0}]})
    rows, errors = S.parse_ratings("Here:\n```json\n" + ok + "\n```", ["604", "605", "814", "815"])
    assert rows == {"604": {"rating": 2, "reason": "r1"}, "605": {"rating": 1, "reason": "r2"}}
    assert errors == {"814": "bad rating 3", "815": "missing"}
    rows, errors = S.parse_ratings("not json at all", ["604"])
    assert rows == {} and errors == {"604": "unparseable"}
    rows, errors = S.parse_ratings(None, ["604"])
    assert errors == {"604": "no response"}
    dup = json.dumps({"results": [{"id": "604", "reason": "a", "character": 2},
                                  {"id": "604", "reason": "b", "character": 0}]})
    rows, errors = S.parse_ratings(dup, ["604"])
    assert rows == {} and errors == {"604": "answered twice"}


# --------------------------------------------------------------------------- the calls

def run(coro):
    return asyncio.run(coro)


def test_rate_batches_calls_once_per_batch_and_charges_usage():
    idx = world()
    items, _ = S.scope_items(idx, ["604", "605", "814", "815", "837"])
    batches = S.make_batches(items, 3)
    client = FakeAsyncAnthropic(responder({"814": 0, "815": 0, "837": 1}))
    usage = MultiModelUsage()
    res = run(S.rate_batches(batches, client=client, model="claude-haiku-5-5", system=SYSTEM, usage=usage,
                             concurrency=2, cache_system=True))
    assert len(client.calls) == len(batches) == 2 and usage.n_calls == 2
    assert {h: r["rating"] for h, r in res.rows.items()} == {"604": 2, "605": 2, "814": 0, "815": 0, "837": 1}
    assert res.rows["814"]["reason"] == "because 814" and res.errors == {}
    kw = client.calls[0]
    assert system_text(kw) == SYSTEM and kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "temperature" not in kw                                    # Haiku 5.5 refuses one
    assert [r["attempt"] for r in res.log] == [1, 1] and all(r["text"] for r in res.log)


def test_rate_batches_retries_missing_heads_once():
    idx = world()
    items, _ = S.scope_items(idx, ["604", "605", "814"])
    client = FakeAsyncAnthropic(responder({}, drop={"605"}))
    res = run(S.rate_batches([items], client=client, model="claude-haiku-5-5", system=SYSTEM,
                             usage=MultiModelUsage(), cache_system=False))
    assert len(client.calls) == 2
    assert [h["id"] for h in json.loads(user_text(client.calls[1]))["heads"]] == ["605"]   # only the missing head
    assert "cache_control" not in client.calls[0]["system"][0]
    assert set(res.rows) == {"604", "605", "814"} and res.rows["605"]["attempts"] == 2
    assert res.parse_rate() == (3, 3)


def test_rate_batches_gives_up_after_one_retry():
    idx = world()
    items, _ = S.scope_items(idx, ["604", "605"])
    client = FakeAsyncAnthropic(responder({}, bad="I cannot answer that."))
    res = run(S.rate_batches([items], client=client, model="claude-haiku-5-5", system=SYSTEM,
                             usage=MultiModelUsage(), cache_system=False))
    assert len(client.calls) == 2 and res.rows == {}
    assert res.errors == {"604": "unparseable", "605": "unparseable"}
    assert res.parse_rate() == (0, 2)


def test_rate_batches_stops_at_the_budget_and_keeps_what_it_paid_for():
    idx = world()
    items, _ = S.scope_items(idx, ["604", "605", "814", "815"])
    batches = S.make_batches(items, 1)
    client = FakeAsyncAnthropic(lambda kw: make_response(responder({})(kw), input_tokens=100000, output_tokens=0))
    usage = GuardedUsage(budget_usd=0.015)                 # 100k tokens at $0.10 / M = $0.01 a call
    res = run(S.rate_batches(batches, client=client, model="claude-haiku-5-5", system=SYSTEM, usage=usage,
                             concurrency=1, cache_system=False))
    assert res.stopped_by_budget
    assert len(client.calls) == 2 and set(res.rows) == {"604", "605"}   # the second call's answer is kept
    assert len(res.log) == 2


# --------------------------------------------------------------------------- the file

def _rated(idx, scope):
    items, skipped = S.scope_items(idx, scope)
    client = FakeAsyncAnthropic(responder({"814": 0, "815": 0, "837": 1}))
    res = run(S.rate_batches(S.make_batches(items, 20), client=client, model="claude-haiku-5-5", system=SYSTEM,
                             usage=MultiModelUsage(), cache_system=False))
    rubric = {"name": S.RUBRIC_NAME, "version": 1, "sha256": "abc", "file": "x.md"}
    return S.build_payload(idx, scope, skipped, res.rows, res.errors, model="claude-haiku-5-5", rubric=rubric,
                           batch_size=20, max_adjectives=20)


def test_payload_save_and_load(tmp_path):
    idx = world()
    scope = ["604", "605", "606", "814", "815", "837"]
    payload = _rated(idx, scope)
    rows = {r["id"]: r for r in payload["heads"]}
    assert [r["id"] for r in payload["heads"]] == scope                       # text order, every head in scope
    assert rows["606"]["rating"] is None and rows["606"]["skipped"] == "no_adjectives"
    assert rows["814"] | {"reason": None} == {"id": "814", "title": "Dearness", "class": "V",
                                              "class_title": "Words relating to the voluntary powers",
                                              "section": "IV. Possessive relations", "n_adjectives": 4,
                                              "n_shown": 4, "rating": 0, "reason": None, "model": "claude-haiku-5-5",
                                              "rubric_version": 1, "skipped": None, "error": None}
    s = payload["summary"]
    assert s["n_scope"] == 6 and s["n_rated"] == 5 and s["n_skipped_no_adjectives"] == 1 and s["n_unrated"] == 0
    assert s["by_rating"] == {"0": 2, "1": 1, "2": 2}
    S.save(payload, tmp_path / "head_scope.json", inputs=[])
    hs = S.load(tmp_path / "head_scope.json")
    assert hs.ratings == {"604": 2, "605": 2, "606": None, "814": 0, "815": 0, "837": 1}
    assert hs.not_character() == {"814", "815"}
    assert hs.rubric["version"] == 1 and hs.model == "claude-haiku-5-5"
    text = (tmp_path / "head_scope.json").read_text()
    assert "_provenance" in json.loads(text)
    assert len(text.splitlines()) > 6                                           # one head per line


def test_previous_ratings_are_kept_for_the_same_rubric_and_model(tmp_path):
    idx = world()
    scope = ["604", "605", "606", "814"]
    payload = _rated(idx, scope)
    payload["heads"][1].update(rating=None, reason=None, error="missing")       # 605 failed last time
    S.save(payload, tmp_path / "hs.json", inputs=[])
    prev = S.load(tmp_path / "hs.json")
    keep = S.reusable(prev, rubric={"version": 1, "sha256": "abc"}, model="claude-haiku-5-5")
    assert set(keep) == {"604", "814"}
    assert S.reusable(prev, rubric={"version": 2, "sha256": "def"}, model="claude-haiku-5-5") == {}
    assert S.reusable(prev, rubric={"version": 1, "sha256": "abc"}, model="claude-sonnet-5-5") == {}


def test_estimate_is_per_call():
    idx = world()
    items, _ = S.scope_items(idx, ["604", "605", "814", "815", "837"])
    est = S.estimate(S.make_batches(items, 2), SYSTEM, "claude-haiku-5-5")
    assert est["n_calls"] == 3 and est["usd"] > 0 and est["in_tok"] > 0 and est["out_tok"] > 0


# --------------------------------------------------------------------------- coverage and harvest

def _pairs_and_labels(idx):
    pairs = PR.rule_pairs(idx, None)
    lh = {"determined_x": {"label": "x", "source": "existing", "status": None, "primary": "814", "secondary": [],
                           "lexical": [], "semantic": []}}
    return pairs, lh


def test_coverage_reports_not_character_heads_apart():
    idx = world()
    pairs, lh = _pairs_and_labels(idx)
    plain = C.coverage(idx, pairs, lh)
    rated = C.coverage(idx, pairs, lh, ratings={"604": 2, "605": 1, "814": 0, "815": 0, "837": 2},
                       scope_meta={"path": "head_scope.json", "rubric_version": 1})
    s0, s1 = plain.summary, rated.summary
    assert s0["not_character"]["n"] == 0 and s0["head_scope"] is None
    assert s1["n_heads"] == s0["n_heads"] == 6
    nc = s1["not_character"]
    assert nc["n"] == 2 and nc["heads"] == ["814", "815"] and nc["by_state"] == {"covered": 1, "empty": 1}
    cpu0, cpu1 = s0["covered_partly_uncovered"], s1["covered_partly_uncovered"]
    assert cpu0["covered"] == 1 and cpu1["covered"] == 0                     # 814 left out of the counts
    assert cpu1["covered"] + cpu1["partly_covered"] + cpu1["uncovered"] + nc["n"] == s1["n_heads"]
    assert sum(s1["by_gap_class"].values()) == 4
    assert s1["character_ratings"] == {"rated": 5, "unrated": 1, "by_rating": {"0": 2, "1": 1, "2": 2}}
    r = rated.by_id()
    assert r["814"].character == 0 and r["606"].character is None
    assert r["815"].gap_class == plain.by_id()["815"].gap_class               # the gap class itself is unchanged
    md = C.render_markdown(rated, idx, lh)
    sec = md.split("## Not character (2)")[1].split("\n## ")[0]
    assert "814 Dearness" in sec and "815 Cheapness" in sec
    for g in C.HARVEST_CLASSES:
        part = md.split(f"## {g} (")[1].split("\n## ")[0]
        assert "814 Dearness" not in part and "815 Cheapness" not in part, g
    assert "## Not character" not in C.render_markdown(plain, idx, lh)


def test_harvest_skips_heads_rated_zero_and_counts_them():
    idx = world()
    pairs, lh = _pairs_and_labels(idx)
    rep = C.coverage(idx, pairs, lh)
    zipf = lambda w: 3.0  # noqa: E731
    cfg = H.HarvestConfig(classes=C.GAP_CLASSES)
    base = H.harvest(rep, idx, pairs, cfg=cfg, known_stems=set(), run_id="r1", zipf=zipf)
    ratings = {"604": 2, "605": 1, "814": 0, "815": 0, "837": 2}
    res = H.harvest(rep, idx, pairs, cfg=cfg, known_stems=set(), run_id="r1", zipf=zipf, head_scope=ratings)
    heads0 = {c.source_ref for c in base.candidates}
    heads1 = {c.source_ref for c in res.candidates}
    assert {"roget:814", "roget:815"} <= heads0 and heads1 == heads0 - {"roget:814", "roget:815"}
    n_lost = sum(1 for c in base.candidates if c.source_ref in ("roget:814", "roget:815"))
    assert res.counts["drops"]["not_character"] == n_lost > 0
    assert res.counts["n_heads_not_character"] == 2 and res.counts["heads_not_character"] == ["814", "815"]
    assert res.counts["n_heads_selected"] == base.counts["n_heads_selected"]
    assert res.counts["head_ratings"]["604"] == 2 and res.counts["head_ratings"]["605"] == 1
    assert {it.head_id: it.character for it in res.items}["605"] == 1
    assert "not_character" not in base.counts["drops"] and base.counts["n_heads_not_character"] == 0
    # the Candidates are exactly as before for the heads kept (no rating in Candidate's fields)
    keep = [c for c in base.candidates if c.source_ref not in ("roget:814", "roget:815")]
    assert [(c.surface, c.source_ref, c.gloss_hint) for c in res.candidates] == \
        [(c.surface, c.source_ref, c.gloss_hint) for c in keep]
    md = H.report_markdown(res, idx, run_id="r1")
    assert "| 814 Dearness | covered | 0 | skipped (not character) |" in md
    assert "| 604 Resolution | pair_empty | 2 | " in md


def test_display_title_drops_the_parsers_leading_period():
    assert S.display_title(". Painfulness") == "Painfulness" and S.display_title("The Drama") == "The Drama"
