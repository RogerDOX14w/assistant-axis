"""The pre-pilot test of the M3 overlap rubrics (assistant_axis/gapgen/overlap_test.py).  No API calls:
the Anthropic client is a fake, the inputs synthetic except where a test reads a tracked file."""
import asyncio
import json
import logging
import re
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen import overlap_test as OT
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

REPO = Path(__file__).resolve().parents[2]
DRAFT = REPO / "reports" / "trait_gap_generation" / "m3_overlap_rubric_draft.md"
#: Rubric A's text at version 4 (draft 2's), the list form the runner, parser and analysis tests exercise; kept
#: as a fixture since A moved to one pair per call (drafts 5 and 6, 2026-10-06), as test_gapgen_split_rubrics does.
V4_FIXTURE = REPO / "assistant_axis" / "tests" / "fixtures" / "overlap_concept_v4.txt"
#: The library's loader, kept here so that a test may put :func:`list_rubrics` in its place (the CLI tests do).
_LOAD_RUBRICS = OT.load_rubrics


def list_rubrics(rubrics_dir=None, keys=None):
    """The pinned rubrics (:func:`OT.load_rubrics`, same arguments) with rubric A as version 4, the list form
    (its pinned version 6 goes out one pair per call): what the tests of the list form send as rubric A."""
    rb = _LOAD_RUBRICS(rubrics_dir, keys=keys)
    if "A" in rb:
        text = V4_FIXTURE.read_text(encoding="utf-8").rstrip("\n")
        rb["A"] = {**rb["A"], "text": text, "version": 4, "sha256": sr.sha256(text), "form": "list"}
    return rb


# --------------------------------------------------------------------------- synthetic inputs

STEMS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda_mu"]


def corpus():
    return {s: {"label": s.replace("_", " "), "description": f"This means being {s} in every way."} for s in STEMS}


def space():
    """Unit rows with known neighbours: alpha~beta~gamma close, delta~epsilon close, the rest spread."""
    rng = np.random.default_rng(0)
    base = rng.standard_normal((len(STEMS), 16))
    base[1] = base[0] + 0.2 * rng.standard_normal(16)       # beta near alpha
    base[2] = base[0] + 0.4 * rng.standard_normal(16)       # gamma near alpha
    base[4] = base[3] + 0.2 * rng.standard_normal(16)       # epsilon near delta
    Z = base / np.linalg.norm(base, axis=1, keepdims=True)
    return list(STEMS), Z


def persona():
    rng = np.random.default_rng(1)
    out = {}
    for s in ("alpha", "beta", "delta", "epsilon", "theta", "iota"):
        v = rng.standard_normal(8)
        out[s] = v / np.linalg.norm(v)
    return out


LABELLED = [
    {"a": "alpha", "b": "beta", "relation": "near_distinct", "source": "plan11_s6", "uncertain": False},
    {"a": "alpha", "b": "gamma", "relation": "near_distinct", "source": "arrangement_triangle", "uncertain": True},
    {"a": "delta", "b": "epsilon", "relation": "antonym", "source": "arrangement_pair", "uncertain": False},
    {"a": "theta", "b": "iota", "relation": "antonym", "source": "arrangement_pair", "uncertain": False},
    {"a": "zeta", "b": "eta", "relation": "antonym", "source": "antonyms_v4", "uncertain": False},   # not recorded
    {"a": "kappa", "b": "lambda_mu", "relation": "unrelated", "source": "random", "uncertain": False},
    {"a": "eta", "b": "kappa", "relation": "unrelated", "source": "random", "uncertain": False},
    {"a": "gamma", "b": "zeta", "relation": "deliberate_duplicate", "source": "corpus_source_field", "uncertain": False},
    {"a": "queue:xx", "b": "alpha", "relation": "duplicate", "source": "seed_queue_decision", "uncertain": False},
    {"a": "beta", "b": "theta", "relation": "duplicate", "source": "plan11_s6", "uncertain": False},
]
DM = [("alpha", "beta"), ("iota", "kappa"), ("nope", "alpha")]
PARTNER = {"delta": "epsilon", "epsilon": "delta", "theta": "iota", "iota": "theta"}


def pair_set(seed=0, **kw):
    stems, Z = space()
    kw.setdefault("n_targets", 4)
    kw.setdefault("n_antonyms", 1)
    kw.setdefault("n_random", 1)
    return OT.build_pair_set(corpus(), stems, Z, persona(), LABELLED, DM, PARTNER, seed=seed, **kw)


# --------------------------------------------------------------------------- rubrics

class TestRubrics:
    def test_load_rubrics_reads_the_pinned_files(self):
        rb = OT.load_rubrics()
        assert set(rb) == {"A", "B"}
        assert rb["A"]["name"] == "overlap_concept" and rb["B"]["name"] == "overlap_cooccurrence"
        # A: draft 3 (answer keys), version 4 = draft 2's text again (Roger, 2026-10-03), then drafts 5 and 6
        # on 2026-10-06 (one pair per call; A2's line 2), for Roger's pass before the M3 pilot
        assert rb["A"]["version"] == 6 and rb["B"]["version"] == 2
        assert rb["A"]["text"] == sr.load_prompt("overlap_concept")
        assert rb["A"]["sha256"].startswith("b3eff18fb946")                                              # draft 6
        assert '"other"' in rb["A"]["text"] and "neither implies the other" in rb["A"]["text"]
        assert '"similarity": 0|1|2|3|4|"opposite"|"unsure"' in rb["A"]["text"]
        assert '"co_occurrence": 0|1|2|3|4|"unsure"' in rb["B"]["text"]

    def test_an_unpinned_text_is_refused(self, tmp_path):
        import shutil
        from assistant_axis.gapgen import paths
        d = tmp_path / "rubrics"
        shutil.copytree(paths.RUBRICS_DIR, d)
        p = d / "overlap_cooccurrence.md"
        p.write_text(p.read_text(encoding="utf-8").replace("almost always:", "nearly always:"), encoding="utf-8")
        with pytest.raises(OT.RubricPinError, match="rubric_pins.py bump overlap_cooccurrence"):
            OT.load_rubrics(d)

    def test_scale_lines(self):
        rb = OT.load_rubrics()
        a = OT.scale_lines(rb["A"]["text"])
        assert len(a) == 7 and a[0].startswith("- 4: the same concept") and a[-1].startswith('- "unsure"')
        assert len(OT.scale_lines(rb["B"]["text"])) == 6


# --------------------------------------------------------------------------- what is sent

def draft_sample():
    """The draft's rendered sample: its user turn, and the target and traits it carries."""
    text = DRAFT.read_text(encoding="utf-8")
    block = re.search(r"\*\*User:\*\*\n\n```json\n(.*?)\n```", text, re.S).group(1)
    return block, json.loads(block)


class TestRender:
    def test_user_turn_is_the_draft_sample_byte_for_byte(self):
        block, obj = draft_sample()
        corp = {obj["target"]["label"]: obj["target"]}
        corp.update({t["label"]: {"label": t["label"], "description": t["description"]} for t in obj["traits"]})
        call = OT.Call(call_id="lab:dramatic", set="labelled", target="dramatic",
                       listed=[t["label"] for t in obj["traits"]])
        assert OT.render_user(call, corp) == block
        assert json.loads(OT.render_user(call, corp)) == obj

    def test_payload_has_only_labels_descriptions_and_ids(self):
        ps = pair_set()
        c = ps.calls[0]
        obj = json.loads(OT.render_user(c, corpus()))
        assert set(obj) == {"target", "traits"}
        assert set(obj["target"]) == {"label", "description"}
        assert [t["id"] for t in obj["traits"]] == list(range(1, len(c.listed) + 1))
        assert all(set(t) == {"id", "label", "description"} for t in obj["traits"])
        assert obj["traits"][0]["label"] == corpus()[c.listed[0]]["label"]

    def test_labels_in_display_form(self):
        call = OT.Call(call_id="x", set="labelled", target="alpha", listed=["lambda_mu"])
        obj = json.loads(OT.render_user(call, corpus()))
        assert obj["traits"][0]["label"] == "lambda mu"

    def test_request_params(self):
        call = OT.Call(call_id="x", set="labelled", target="alpha", listed=["beta"])
        rb = OT.load_rubrics()
        h = OT.call_params(call, corpus(), rubric_text=rb["A"]["text"], model=OT.HAIKU)
        assert h["temperature"] == 0.0 and h["system"][0]["text"] == rb["A"]["text"]
        assert "cache_control" not in h["system"][0] and "thinking" not in h
        for m in (OT.SONNET, OT.OPUS):
            p = OT.call_params(call, corpus(), rubric_text=rb["B"]["text"], model=m)
            assert "temperature" not in p and p["model"] == m
        txt = OT.rendered_prompt(call, corpus(), rubric="A", rubric_text=rb["A"]["text"], model=OT.HAIKU)
        assert "--- system ---" in txt and '"temperature": 0.0' in txt and rb["A"]["text"] in txt


# --------------------------------------------------------------------------- the pair set

class TestPairSet:
    def test_nearest_targets_have_vectors_and_three_neighbours(self):
        ps = pair_set()
        nn = [c for c in ps.calls if c.set == "nearest"]
        assert len(nn) == 4
        stems, Z = space()
        idx = {s: i for i, s in enumerate(stems)}
        for c in nn:
            assert c.target in persona() and c.call_id == f"nn:{c.target}"
            assert len(c.listed) == 3 and c.target not in c.listed
            sims = {s: float(Z[idx[c.target]] @ Z[idx[s]]) for s in STEMS if s != c.target}
            top3 = sorted(sims, key=lambda s: -sims[s])[:3]
            assert set(c.listed) == set(top3)
            ranks = {p.listed: p.nn_rank for p in ps.pairs if p.call_id == c.call_id}
            assert [s for s, _ in sorted(ranks.items(), key=lambda kv: kv[1])] == top3

    def test_deterministic_for_a_seed(self):
        a, b = pair_set(seed=3), pair_set(seed=3)
        assert a.to_json() == b.to_json()
        assert [c.listed for c in pair_set(seed=4).calls] != [c.listed for c in a.calls] or \
            [c.target for c in pair_set(seed=4).calls] != [c.target for c in a.calls]

    def test_labelled_groups(self):
        entries, info = OT.labelled_groups(LABELLED, corpus(), DM, seed=0, n_antonyms=5, n_random=5)
        groups = {(e["a"], e["b"]): e["group"] for e in entries}
        assert groups[("alpha", "beta")] == "drop_or_merge"           # also near-distinct: filed first
        assert [e["also"] for e in entries if (e["a"], e["b"]) == ("alpha", "beta")] == [["near_distinct"]]
        assert groups[("alpha", "gamma")] == "near_distinct"          # uncertain near-distinct kept
        assert groups[("delta", "epsilon")] == "antonym" and groups[("iota", "theta")] == "antonym"
        assert ("eta", "zeta") not in groups                         # an antonym not from a recorded pair
        assert groups[("gamma", "zeta")] == "deliberate_duplicate"
        assert groups[("beta", "theta")] == "duplicate"               # both corpus traits
        assert not any("queue:xx" in (e["a"], e["b"]) for e in entries)
        assert groups[("iota", "kappa")] == "drop_or_merge"
        assert info["skipped_not_in_corpus"] == {"duplicate": 1, "drop_or_merge": 1}
        assert info["pool_sizes"]["random"] == 2

    def test_samples_are_seeded(self):
        a, _ = OT.labelled_groups(LABELLED, corpus(), DM, seed=0, n_antonyms=1, n_random=1)
        b, _ = OT.labelled_groups(LABELLED, corpus(), DM, seed=0, n_antonyms=1, n_random=1)
        assert a == b
        assert sum(e["group"] == "antonym" for e in a) == 1 and sum(e["group"] == "random" for e in a) == 1

    def test_grouped_as_m3(self):
        entries = [{"a": "a", "b": "b"}, {"a": "a", "b": "c"}, {"a": "c", "b": "d"}, {"a": "e", "b": "f"}]
        groups = OT.group_as_m3(entries, seed=0)
        assert groups[0][0] in ("a", "c") and len(groups[0][1]) == 2
        covered = [e for _, es in groups for e in es]
        assert sorted(map(str, covered)) == sorted(map(str, entries))        # every pair once
        for t, es in groups:
            assert all(t in (e["a"], e["b"]) for e in es)

    def test_every_pair_once_per_call_with_ids_and_cosines(self):
        ps = pair_set(n_antonyms=2, n_random=2)
        stems, Z = space()
        idx = {s: i for i, s in enumerate(stems)}
        per = persona()
        for c in ps.calls:
            mine = [p for p in ps.pairs if p.call_id == c.call_id]
            assert sorted(p.id for p in mine) == list(range(1, len(c.listed) + 1))
            for p in mine:
                assert c.listed[p.id - 1] == p.listed and p.target == c.target
                assert p.embedding_cos == pytest.approx(float(Z[idx[p.target]] @ Z[idx[p.listed]]), abs=1e-6)
                if p.target in per and p.listed in per:
                    assert p.persona_cos == pytest.approx(float(per[p.target] @ per[p.listed]), abs=1e-6)
                else:
                    assert p.persona_cos is None
        lab = [p for p in ps.pairs if p.set == "labelled"]
        keys = [OT._ukey(p.target, p.listed) for p in lab]
        assert len(keys) == len(set(keys))
        assert {p.group for p in lab} >= {"drop_or_merge", "near_distinct", "antonym", "random",
                                          "deliberate_duplicate", "duplicate"}

    def test_annotations(self):
        ps = pair_set(n_antonyms=2, n_random=2)
        for p in ps.pairs:
            if {p.target, p.listed} == {"delta", "epsilon"}:
                assert p.recorded_pair and p.labelled_relation == "antonym" and OT.is_antonym_pair(p)
            if {p.target, p.listed} == {"kappa", "lambda_mu"}:
                assert p.labelled_relation == "unrelated" and not OT.is_antonym_pair(p)

    def test_round_trip(self):
        ps = pair_set()
        back = OT.PairSet.from_json(json.loads(json.dumps(ps.to_json())))
        assert back.to_json() == ps.to_json()

    def test_drop_or_merge_table(self):
        p = REPO / "data" / "candidates" / "calibration" / "drop_or_merge.md"
        pairs = OT.parse_drop_or_merge(p.read_text(encoding="utf-8"))
        assert len(pairs) == 11
        assert ("theatrical", "dramatic") in pairs and ("self_blaming", "blame_shifting") in pairs
        assert ("oblivious", "observant") not in pairs            # the second table: a recorded pair


# --------------------------------------------------------------------------- parsing

def answer(rows, key="similarity"):
    return json.dumps({"results": [{"id": i, "reason": f"Because {i}.", key: v} for i, v in rows]})


class TestParse:
    def test_a_good_answer(self):
        rows, errors, meta = OT.parse_answer(answer([(1, 4), (2, "opposite"), (3, "unsure")]), "A", 3)
        assert {i: r["value"] for i, r in rows.items()} == {1: 4, 2: "opposite", 3: "unsure"}
        assert errors == {} and meta["in_order"] and meta["reason_first"]

    def test_rubric_b(self):
        rows, errors, _ = OT.parse_answer(answer([(1, 0), (2, "unsure")], "co_occurrence"), "B", 2)
        assert {i: r["value"] for i, r in rows.items()} == {1: 0, 2: "unsure"}
        rows, errors, _ = OT.parse_answer(answer([(1, "opposite")], "co_occurrence"), "B", 1)
        assert rows == {} and "not 0-4" in errors[1]
        rows, errors, _ = OT.parse_answer(answer([(1, 2)], "similarity"), "B", 1)   # wrong key
        assert errors == {1: "co_occurrence missing"}

    def test_lenient_forms(self):
        text = "Here you go:\n```json\n" + json.dumps({"results": [
            {"id": "1", "reason": "x", "similarity": "3"}, {"id": 2, "reason": "y", "similarity": "Opposite"}]}) + "\n```"
        rows, errors, _ = OT.parse_answer(text, "A", 2)
        assert {i: r["value"] for i, r in rows.items()} == {1: 3, 2: "opposite"}

    def test_failures(self):
        rows, errors, _ = OT.parse_answer(answer([(1, 5), (2, 2.5), (3, True)]), "A", 4)
        assert rows == {} and set(errors) == {1, 2, 3, 4} and errors[4] == "missing"
        rows, errors, _ = OT.parse_answer(json.dumps({"results": [{"id": 1, "similarity": 2}]}), "A", 1)
        assert errors == {1: "reason missing"}
        rows, errors, _ = OT.parse_answer("no json here", "A", 2)
        assert rows == {} and all("unparseable" in e for e in errors.values())
        rows, errors, _ = OT.parse_answer("", "A", 1)
        assert errors == {1: "empty response"}
        rows, errors, meta = OT.parse_answer(answer([(1, 1), (7, 1)]), "A", 1)
        assert set(rows) == {1} and meta["extra_ids"] == [7]

    def test_a_self_correction_uses_the_last_answer(self):
        """Sonnet 5.5, overlap_test_1: an answer with a stray "label" key, then "Correction: ..." and the
        answer again; the last complete results object is the model's final answer."""
        first = json.dumps({"results": [{"id": 1, "reason": "a", "similarity": 2},
                                        {"id": 2, "label": "placid", "reason": "b", "similarity": 3}]})
        final = json.dumps({"results": [{"id": 1, "reason": "a", "similarity": 2},
                                        {"id": 2, "reason": "b2", "similarity": 4}]})
        text = first + "\n\nCorrection: the output must have the reason field only. Corrected output:\n\n" + final
        rows, errors, meta = OT.parse_answer(text, "A", 2)
        assert errors == {} and rows[2]["value"] == 4 and rows[2]["reason"] == "b2"
        assert meta["n_result_objects"] == 2
        rows, errors, meta = OT.parse_answer("```json\n" + first + "\n```\nCorrection:\n```json\n" + final + "\n```",
                                             "A", 2)
        assert rows[2]["value"] == 4 and meta["n_result_objects"] == 2

    def test_a_missing_key_still_fails(self):
        """Sonnet 5.5, overlap_test_1: `"reason": "...", "opposite"}` (the answer's key left out) is not JSON;
        no row of the call is salvaged."""
        text = ('{"results": [{"id": 1, "reason": "x", "similarity": 1}, '
                '{"id": 2, "reason": "Ecocentric is the reverse view.", "opposite"}]}')
        rows, errors, meta = OT.parse_answer(text, "A", 2)
        assert rows == {} and all("unparseable" in e for e in errors.values())
        assert meta["n_result_objects"] == 0

    def test_duplicates_order_and_reason_position(self):
        text = json.dumps({"results": [{"id": 2, "similarity": 1, "reason": "late"},
                                       {"id": 1, "reason": "a", "similarity": 3},
                                       {"id": 1, "reason": "again", "similarity": 0}]})
        rows, errors, meta = OT.parse_answer(text, "A", 2)
        assert rows[1]["value"] == 3 and rows[1]["reason_first"] and not rows[2]["reason_first"]
        assert meta["in_order"] is False and meta["reason_first"] is False


# --------------------------------------------------------------------------- the runner

def responder_for(rb, *, bad_model=None, value=2):
    def responder(kw):
        sys_t = system_text(kw)
        key = "similarity" if sys_t == rb["A"]["text"] else "co_occurrence"
        n = len(json.loads(user_text(kw))["traits"])
        if bad_model and kw["model"] == bad_model:
            return make_response("I cannot answer that.", input_tokens=900, output_tokens=10)
        return make_response(answer([(i, value) for i in range(1, n + 1)], key), input_tokens=900, output_tokens=150)
    return responder


def run(coro):
    return asyncio.run(coro)


class TestRunner:
    """The list form (rubric A at version 4, :func:`list_rubrics`); the single form is TestSingleFormRunner."""

    def test_one_call_per_target_per_stage_and_records(self, tmp_path):
        rb = list_rubrics()
        ps = pair_set()
        client = FakeAsyncAnthropic(responder_for(rb))
        usage = MultiModelUsage()
        r = OT.OverlapRunner(client, rb, corpus(), usage=usage, responses_path=tmp_path / "responses.jsonl",
                             retry_delays=())
        res = run(r.run_stage("A", OT.HAIKU, ps.calls))
        assert res.n_sent == len(ps.calls) == len(client.calls) and res.n_ok == res.n_pairs == len(ps.pairs)
        sent_users = sorted(user_text(kw) for kw in client.calls)
        assert sent_users == sorted(OT.render_user(c, corpus()) for c in ps.calls)
        assert all(system_text(kw) == rb["A"]["text"] and kw["temperature"] == 0.0 for kw in client.calls)
        recs = OT.read_records(tmp_path / "responses.jsonl")
        assert len(recs) == len(ps.calls)
        rec = recs[0]
        assert rec["rubric"] == "A" and rec["rubric_version"] == rb["A"]["version"] and rec["prompt_sha256"] == rb["A"]["sha256"]
        assert rec["request"]["user"] == OT.render_user(ps.call(rec["call_id"]), corpus())
        assert rec["request"]["temperature"] == 0.0 and rec["response"]["text"]
        assert usage.n_calls == len(ps.calls) and usage.total_cost_usd > 0

    def test_resume_skips_answered_calls(self, tmp_path):
        rb = list_rubrics()
        ps = pair_set()
        path = tmp_path / "responses.jsonl"
        c1 = FakeAsyncAnthropic(responder_for(rb))
        r1 = OT.OverlapRunner(c1, rb, corpus(), usage=MultiModelUsage(), responses_path=path, retry_delays=())
        run(r1.run_stage("B", OT.SONNET, ps.calls[:2]))
        c2 = FakeAsyncAnthropic(responder_for(rb))
        r2 = OT.OverlapRunner(c2, rb, corpus(), usage=MultiModelUsage(), responses_path=path, retry_delays=())
        res = run(r2.run_stage("B", OT.SONNET, ps.calls))
        assert res.n_skipped == 2 and len(c2.calls) == len(ps.calls) - 2
        assert all("temperature" not in kw for kw in c2.calls)       # Sonnet 5.5 refuses it

    def test_budget_cap_stops_the_stage_and_keeps_the_answer(self, tmp_path):
        rb = list_rubrics()
        ps = pair_set()
        usage = GuardedUsage(budget_usd=0.0005)          # one Opus call of (900, 150) tokens crosses it
        client = FakeAsyncAnthropic(responder_for(rb))
        r = OT.OverlapRunner(client, rb, corpus(), usage=usage, responses_path=tmp_path / "r.jsonl",
                             concurrency=1, retry_delays=())
        res = run(r.run_stage("A", OT.OPUS, ps.calls))
        assert res.budget_exceeded and len(client.calls) == 1 and res.n_sent == 1
        rec = OT.read_records(tmp_path / "r.jsonl")[0]
        assert rec["response"]["text"] and rec["parsed"]

    def test_an_unparsed_answer_is_asked_again_once(self, tmp_path):
        rb = list_rubrics()
        ps = pair_set()
        seen: dict = {}
        good = responder_for(rb, value=1)

        def flaky(kw):
            u = user_text(kw)
            seen[u] = seen.get(u, 0) + 1
            return make_response('{"results": [{"id": 1, "reason": "x", "opposite"}]}') if seen[u] == 1 else good(kw)
        client = FakeAsyncAnthropic(flaky)
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=tmp_path / "r.jsonl",
                             retry_delays=())
        res = run(r.run_stage("A", OT.SONNET, ps.calls))
        assert len(client.calls) == 2 * len(ps.calls) and res.n_reasked == len(ps.calls)
        assert res.n_ok == res.n_pairs == len(ps.pairs) and res.n_ok_first == 0
        recs = OT.read_records(tmp_path / "r.jsonl")
        assert len(recs) == 2 * len(ps.calls) and {r["parse_attempt"] for r in recs} == {1, 2}
        ans = OT.collect_answers(ps, recs)[("A", OT.SONNET)]
        assert all(a["value"] == 1 for a in ans.values())
        first = OT.first_attempt_parse(ps, recs)[("A", OT.SONNET)]
        assert first == {"ok": 0, "total": len(ps.pairs)}

    def test_a_call_that_never_parses_is_sent_twice_and_resent_on_resume(self, tmp_path):
        rb = list_rubrics()
        ps = pair_set()
        client = FakeAsyncAnthropic(responder_for(rb, bad_model=OT.OPUS))
        path = tmp_path / "r.jsonl"
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=path, retry_delays=())
        res = run(r.run_stage("B", OT.OPUS, ps.calls[:1]))
        assert len(client.calls) == 2 and res.n_ok == 0
        assert ("B", OT.OPUS, ps.calls[0].call_id) not in r.done()       # answered but unparsed: not done
        run(r.run_stage("B", OT.OPUS, ps.calls[:1]))
        assert len(client.calls) == 4

    def test_a_failed_request_is_not_asked_again_nor_counted_as_the_first_attempt(self, tmp_path):
        """overlap_test_2: an expired key failed every Sonnet request; the resume answered them all at once,
        and the first-attempt parse rate must say so (it read 0/409 from the failed records)."""
        rb = list_rubrics()
        ps = pair_set()
        path = tmp_path / "r.jsonl"
        dead = FakeAsyncAnthropic(lambda kw: RuntimeError("401 API key is invalid"))
        r1 = OT.OverlapRunner(dead, rb, corpus(), usage=MultiModelUsage(), responses_path=path, retry_delays=())
        res1 = run(r1.run_stage("A", OT.SONNET, ps.calls))
        assert len(dead.calls) == len(ps.calls) and res1.n_reasked == 0 and res1.n_ok == 0
        assert all(OT.request_failed(rec) for rec in OT.read_records(path))
        live = FakeAsyncAnthropic(responder_for(rb))
        r2 = OT.OverlapRunner(live, rb, corpus(), usage=MultiModelUsage(), responses_path=path, retry_delays=())
        res2 = run(r2.run_stage("A", OT.SONNET, ps.calls))
        assert len(live.calls) == len(ps.calls)
        assert res2.n_ok == res2.n_ok_first == res2.n_pairs == len(ps.pairs)
        recs = OT.read_records(path)
        assert OT.first_attempt_parse(ps, recs)[("A", OT.SONNET)] == {"ok": len(ps.pairs), "total": len(ps.pairs)}

    def test_answers_are_reparsed_from_the_recorded_text(self, tmp_path):
        """A record written by an older parser (its stored "parsed" empty) is read with the current one."""
        ps = pair_set()
        c = ps.calls[0]
        text = "\n".join(json.dumps({"results": [{"id": i, "reason": "r", "similarity": 2}
                                                 for i in range(1, len(c.listed) + 1)]}) for _ in range(2))
        rec = {"rubric": "A", "model": OT.OPUS, "call_id": c.call_id, "listed": c.listed, "response": {"text": text},
               "parsed": {}, "errors": {"1": "unparseable response: Extra data"}}
        ans = OT.collect_answers(ps, [rec])[("A", OT.OPUS)]
        assert {a["value"] for pid, a in ans.items() if pid.startswith(c.call_id + ">")} == {2}

    def test_parse_rate_alert(self, tmp_path, caplog):
        rb = list_rubrics()
        ps = pair_set()
        client = FakeAsyncAnthropic(responder_for(rb, bad_model=OT.HAIKU))
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=tmp_path / "r.jsonl",
                             retry_delays=())
        with caplog.at_level(logging.INFO):
            res = run(r.run_stage("A", OT.HAIKU, ps.calls))
        assert res.n_ok == 0 and res.parse_rate == 0
        assert "HIGH FAIL RATE" in caplog.text and "overlap_test:overlap_concept:" in caplog.text


# --------------------------------------------------------------------------- statistics

class TestStatistics:
    def test_weighted_kappa_matches_sklearn(self):
        from sklearn.metrics import cohen_kappa_score
        rng = np.random.default_rng(0)
        a = rng.integers(0, 5, 200)
        b = np.clip(a + rng.integers(-1, 2, 200), 0, 4)
        for w in ("quadratic", "linear"):
            assert OT.weighted_kappa(a, b, weights=w) == pytest.approx(
                cohen_kappa_score(a, b, weights=w, labels=list(range(5))), abs=1e-9)
        assert OT.weighted_kappa([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
        assert OT.weighted_kappa([2, 2], [2, 2]) is None and OT.weighted_kappa([], []) is None

    def test_agreement(self):
        ref = {"p1": {"value": 4}, "p2": {"value": 2}, "p3": {"value": "opposite"}, "p4": {"value": 0},
               "p5": {"value": None}}
        oth = {"p1": {"value": 3}, "p2": {"value": 2}, "p3": {"value": 0}, "p4": {"value": 0}, "p5": {"value": 1}}
        ag = OT.agreement(ref, oth)
        assert ag["n_common"] == 5 and ag["n_both_parsed"] == 4 and ag["n_numeric"] == 3
        assert ag["exact"] == pytest.approx(2 / 3, abs=1e-4) and ag["within_one"] == 1.0
        assert ag["exact_all"] == 0.5 and ag["mean_diff"] == pytest.approx(-1 / 3, abs=1e-4)
        assert ag["table"]["opposite"] == {"numeric": 1} and ag["table"]["unparsed"] == {"numeric": 1}

    def fake_answers(self, ps, f):
        out = {}
        for r in OT.RUBRICS:
            for m in OT.MODELS:
                out[(r, m)] = {p.pair_id: {"value": f(r, m, p), "reason": "r", "reason_first": True, "error": None}
                               for p in ps.pairs}
        return out

    def test_analyse(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)

        def f(r, m, p):
            if r == "A" and OT.is_antonym_pair(p):
                return "opposite"
            base = int(round(np.clip((p.embedding_cos + 1) * 2, 0, 4)))
            return min(4, base + 1) if (r == "B" and m == OT.HAIKU) else base
        ans = self.fake_answers(ps, f)
        s = OT.analyse(ps, ans, n_boot=50)
        assert s["n_pairs"] == len(ps.pairs)
        assert s["parse"][f"A|{OT.OPUS}"]["rate"] == 1.0
        assert s["agreement"]["A"][OT.SONNET]["exact"] == 1.0
        assert s["agreement"]["B"][OT.HAIKU]["mean_diff"] >= 0
        corr = s["correlation"]["A"][OT.OPUS]["embedding"]["all"]
        assert corr["rho"] is not None and corr["rho"] > 0.8     # the cosine rounded to five levels
        assert corr["lo"] <= corr["rho"] <= corr["hi"]
        assert s["rates"]["A"][OT.OPUS]["antonym_group"]["opposite"] == 1.0
        assert s["groups"]["A"][OT.OPUS]["antonym"]["counts"] == {"opposite": s["groups"]["A"][OT.OPUS]["antonym"]["n"]}
        assert set(s["divergence"][OT.OPUS]) >= {"b_above_a", "a_above_b", "diff_counts"}
        assert s["rubric_difference"][OT.OPUS]["non_antonym"]["embedding"]["diff"] == pytest.approx(0, abs=1e-9)
        assert s["opus_on_disagreement"]["A"]["haiku_sonnet_same"] == len(ps.pairs)
        json.dumps(s)

    def test_tables_for_a_run_of_one_rubric_and_two_models(self):
        """overlap_test_2 sent rubric A to Sonnet and Opus only; the tables must not need rubric B."""
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        ans = {k: v for k, v in self.fake_answers(ps, lambda r, m, p: 2).items()
               if k[0] == "A" and k[1] in (OT.SONNET, OT.OPUS)}
        s = OT.analyse(ps, ans, n_boot=20)
        md = OT.summary_markdown(s, ps, corpus())
        assert "## Known groups, rubric A" in md and "## Known groups, rubric B" not in md

    def test_divergence_orders_b_over_a(self):
        ps = pair_set()
        pairs = ps.pairs[:3]
        a = {pairs[0].pair_id: {"value": 0, "reason": "a"}, pairs[1].pair_id: {"value": 3, "reason": "a"},
             pairs[2].pair_id: {"value": 1, "reason": "a"}}
        b = {pairs[0].pair_id: {"value": 3, "reason": "b"}, pairs[1].pair_id: {"value": 1, "reason": "b"},
             pairs[2].pair_id: {"value": 2, "reason": "b"}}
        d = OT.divergence(pairs, a, b)
        assert [r["diff"] for r in d["b_above_a"]] == [3, 1] and d["a_above_b"][0]["diff"] == -2
        assert d["diff_counts"] == {"-2": 1, "1": 1, "3": 1}

    def test_collect_answers_and_results(self, tmp_path):
        rb = list_rubrics()
        ps = pair_set()
        client = FakeAsyncAnthropic(responder_for(rb, value=3))
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=tmp_path / "r.jsonl",
                             retry_delays=())
        run(r.run_stage("A", OT.HAIKU, ps.calls))
        ans = OT.collect_answers(ps, OT.read_records(tmp_path / "r.jsonl"))
        assert set(ans) == {("A", OT.HAIKU)} and len(ans[("A", OT.HAIKU)]) == len(ps.pairs)
        assert all(a["value"] == 3 for a in ans[("A", OT.HAIKU)].values())
        rows = OT.results_rows(ps, ans)
        assert len(rows) == len(ps.pairs) and rows[0]["rubric_name"] == "overlap_concept"

    def test_estimate_prices_fable_above_opus(self):
        ps = pair_set()
        rb = OT.load_rubrics()
        fable = OT.estimate(ps.calls, corpus(), rb, [OT.FABLE], ["A"])
        opus = OT.estimate(ps.calls, corpus(), rb, [OT.OPUS], ["A"])
        assert len(fable.lines) == 1 and "Fable 5.1" in str(fable.lines[0])
        assert fable.usd == pytest.approx(opus.usd * 2.5)          # same tokens, 2.5x the rates

    def test_estimate(self):
        rb = list_rubrics()
        ps = pair_set()
        est = OT.estimate(ps.calls, corpus(), rb, OT.MODELS)
        assert len(est.lines) == 6 and est.usd > 0
        by = {x.model: x for x in est.lines}
        assert by[OT.OPUS].in_tok > by[OT.HAIKU].in_tok          # the newer tokenizer counts more
        assert all(x.n_calls == len(ps.calls) for x in est.lines)


# --------------------------------------------------------------------------- Roger's marks

class TestMarks:
    def test_draw_quotas_and_blinding(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        quotas = {"nearest": 6, "drop_or_merge": 1, "antonym": 1, "random": 1, "deliberate_duplicate": 1}
        items = OT.draw_marks(ps, seed=0, quotas=quotas)
        assert len(items) == 10 and items == OT.draw_marks(ps, seed=0, quotas=quotas)
        keys = [OT._ukey(p.target, p.listed) for p in items]
        assert len(set(keys)) == len(keys)
        rb = OT.load_rubrics()
        sheet = OT.marks_sheet(items, corpus(), rubric_text=rb["A"]["text"], run_id="t1",
                               key_link="../../data/candidates/overlap_test/t1/marks_key.json")
        low = sheet.lower()
        for word in ("haiku", "sonnet", "opus", "nearest", "antonym", "drop_or_merge", "random", "cosine", "group"):
            assert word not in low, word
        assert sheet.count("Your answer (") == 10 and "> - 4: the same concept" in sheet
        assert "[alpha](../../data/traits/instructions/alpha.json)" in sheet or "alpha" not in keys

    def test_decode_round_trip(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        items = OT.draw_marks(ps, seed=1, quotas={"nearest": 4})
        rb = OT.load_rubrics()
        sheet = OT.marks_sheet(items, corpus(), rubric_text=rb["A"]["text"], run_id="t", key_link="k.json")
        key = OT.marks_key(items, run_id="t", seed=1, sheet="s.md")
        written = iter(["3", " Opposite ", "", "seven"])
        filled = re.sub(r"(Your answer \([^)]*\):) ", lambda m: m.group(1) + " " + next(written), sheet)
        dec = OT.decode_marks(filled, key)
        assert [it["value"] for it in dec["items"]] == [3, "opposite", None, None]
        assert [it["status"] for it in dec["items"]] == ["ok", "ok", "blank", "invalid"]
        ans = {("A", OT.OPUS): {items[0].pair_id: {"value": 3}, items[1].pair_id: {"value": 2}}}
        cmp_ = OT.compare_marks(dec, ans)
        assert cmp_[OT.OPUS]["n_both_parsed"] == 2 and cmp_[OT.OPUS]["exact_all"] == 0.5


# =========================================================================== the arms experiment
# (coding_plan_overlap_arms.md, 2026-10-04): rubrics C, D, E; passes; the analysis

ALL = tuple(OT.RUBRICS)


def _label_value(r, label):
    """A deterministic answer per (rubric, listed label): the same pair gets the same answer in every pass,
    whatever id it was sent under.  A round-2 rubric answers as its round-1 arm."""
    choices = {"A": [0, 1, 2, 3, 4, "opposite"], "B": [0, 1, 2, 3, 4], "C": [0, 1, 2, 3, 4, 5, "opposite"],
               "D": list(OT.RELATIONS) + ["opposite"], "E": [0, 1, 2, 3, 4, "opposite"]}[OT.RUBRICS[r].get("round1", r)]
    return choices[sum(map(ord, label)) % len(choices)]


def arms_responder(rb, value=_label_value, wider="target"):
    """Answers each rubric in its own format (key, scale), a "contains" of D (and D2) with ``wider``."""
    by_text = {v["text"]: k for k, v in rb.items()}

    def responder(kw):
        r = by_text[system_text(kw)]
        rows = []
        for t in json.loads(user_text(kw))["traits"]:
            v = value(r, t["label"])
            row = {"id": t["id"], "reason": f"About {t['label']}: narrowed to one domain.", OT.RUBRICS[r]["key"]: v}
            if OT.has_wider(r) and v == "contains" and wider is not None:
                row["wider"] = wider
            rows.append(row)
        return make_response(json.dumps({"results": rows}), input_tokens=900, output_tokens=150)
    return responder


class TestArmRubrics:
    def test_the_arms_load_from_their_pinned_files(self):
        rb = OT.load_rubrics(keys=ALL)
        assert set(rb) == set(ALL)
        assert [rb[r]["name"] for r in "CDE"] == ["overlap_six", "overlap_relation", "overlap_scope"]
        assert all(rb[r]["version"] == 1 and rb[r]["text"] == sr.load_prompt(rb[r]["name"]) for r in "CDE")
        assert '"similarity": 0|1|2|3|4|5|"opposite"|"unsure"' in rb["C"]["text"]
        assert '"relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", ' \
               '"wider": "target"|"listed"' in rb["D"]["text"]
        assert '"similarity": 0|1|2|3|4|"opposite"|"unsure"' in rb["E"]["text"]

    def test_the_default_is_the_original_two_and_an_unknown_key_is_refused(self):
        assert set(OT.load_rubrics()) == set(OT.DEFAULT_RUBRICS) == {"A", "B"}
        with pytest.raises(ValueError, match="unknown rubric"):
            OT.load_rubrics(keys=["A", "F"])

    def test_scale_lines_are_the_rubric_facts(self):
        """Every answer line of a rubric is one of its facts (scale and categories), in the rubric's order."""
        rb = OT.load_rubrics(keys=ALL)
        for r in ALL:
            spec = OT.RUBRICS[r]
            lines = OT.scale_lines(rb[r]["text"])
            want = [f"- {n}:" for n in sorted(spec["scale"], reverse=True)] + [f'- "{c}":' for c in spec["categories"]]
            assert len(lines) == len(want), r
            assert all(ln.startswith(w) for ln, w in zip(lines, want)), r

    def test_native_scales(self):
        # the round-1 rubrics by name (ALL also holds round 2's since 2026-10-04: A2 5, C2 6, D2 6, E2 5)
        assert [OT.native_k(r) for r in ("A", "B", "C", "D", "E")] == [5, 5, 6, 6, 5]
        assert [OT.native_k(r) for r in OT.ROUND2] == [5, 6, 6, 5]
        assert OT.native_order("D") == list(OT.RELATIONS) + ["opposite", "unsure"]
        assert OT.native_order("B") == ["0", "1", "2", "3", "4", "unsure"]
        assert OT.answer_order("C") == ["0", "1", "2", "3", "4", "5", "opposite", "unsure"]


class TestDecisionScale:
    def test_c_maps_six_rungs_to_five(self):
        assert [OT.decision_value("C", v) for v in (5, 4, 3, 2, 1, 0)] == [4, 3, 3, 2, 1, 0]

    def test_d_maps_relations_to_numbers(self):
        got = {rel: OT.decision_value("D", rel) for rel in OT.RELATIONS}
        assert got == {"same": 4, "variant": 3, "contains": 3, "overlap": 2, "neighbours": 1, "different": 0}

    def test_a_b_and_e_are_unchanged_and_categories_kept(self):
        for r in ("A", "B", "E"):
            assert [OT.decision_value(r, v) for v in range(5)] == list(range(5))
        for r in ALL:
            assert OT.decision_value(r, "opposite") == "opposite" and OT.decision_value(r, "unsure") == "unsure"
            assert OT.decision_value(r, None) is None

    def test_ranks_and_the_cutoff(self):
        assert [OT.ordinal_value("D", rel) for rel in OT.RELATIONS] == [0, 1, 2, 3, 4, 5]
        assert OT.ordinal_value("D", "opposite") == "opposite" and OT.ordinal_value("C", 5) == 5
        # at the cut-off 3, the native and the decision scale agree for C and D (ranks 3+ = decision 3+)
        for r, values in (("C", range(6)), ("D", OT.RELATIONS)):
            for v in values:
                assert (OT.ordinal_value(r, v) >= 3) == (OT.decision_value(r, v) >= 3), (r, v)

    def test_to_decision_and_to_ordinal_keep_the_rest_of_an_answer(self):
        ans = {"p": {"value": "contains", "reason": "r", "wider": "listed"}}
        assert OT.to_decision("D", ans)["p"] == {"value": 3, "reason": "r", "wider": "listed"}
        assert OT.to_ordinal("D", ans)["p"]["value"] == 3 and ans["p"]["value"] == "contains"


def d_answer(rows):
    return json.dumps({"results": [{"id": i, "reason": f"Because {i}.", "relation": v, **extra}
                                   for i, v, extra in rows]})


class TestArmParsing:
    def test_c_takes_0_to_5(self):
        rows, errors, _ = OT.parse_answer(answer([(1, 5), (2, "4"), (3, "opposite")]), "C", 3)
        assert {i: r["value"] for i, r in rows.items()} == {1: 5, 2: 4, 3: "opposite"} and errors == {}
        rows, errors, _ = OT.parse_answer(answer([(1, 6)]), "C", 1)
        assert rows == {} and "is not 0-5 or one of" in errors[1]
        rows, errors, _ = OT.parse_answer(answer([(1, 5)]), "A", 1)          # A and E stop at 4
        assert "is not 0-4" in errors[1]
        rows, errors, _ = OT.parse_answer(answer([(1, 5)]), "E", 1)
        assert "is not 0-4" in errors[1]

    def test_d_relations_and_wider(self):
        text = d_answer([(1, "contains", {"wider": "target"}), (2, "Overlap", {}), (3, "contains", {"wider": "listed"}),
                         (4, "same", {"wider": None}), (5, "opposite", {})])
        rows, errors, meta = OT.parse_answer(text, "D", 5)
        assert errors == {}
        assert {i: r["value"] for i, r in rows.items()} == {1: "contains", 2: "overlap", 3: "contains", 4: "same",
                                                             5: "opposite"}
        assert [rows[i]["wider"] for i in range(1, 6)] == ["target", None, "listed", None, None]
        assert all(rows[i]["notes"] == [] for i in range(1, 6)) and meta["n_notes"] == 0
        assert all(r["reason_first"] for r in rows.values())

    def test_d_contains_without_a_usable_wider_parses_with_a_note(self):
        text = d_answer([(1, "contains", {}), (2, "contains", {"wider": "both"}), (3, "contains", {"wider": "The target"}),
                         (4, "contains", {"wider": "null"})])
        rows, errors, meta = OT.parse_answer(text, "D", 4)
        assert errors == {} and set(rows) == {1, 2, 3, 4}
        assert rows[1]["wider"] is None and rows[1]["notes"] == ["contains without wider"]
        assert rows[2]["wider"] is None and rows[2]["notes"] == ["wider 'both' is not target or listed"]
        assert rows[3]["wider"] == "target" and rows[3]["notes"] == []
        assert rows[4]["wider"] is None and rows[4]["notes"] == ["contains without wider"]
        assert meta["n_notes"] == 3

    def test_d_wider_with_another_relation_is_noted_and_dropped(self):
        rows, errors, _ = OT.parse_answer(d_answer([(1, "variant", {"wider": "listed"})]), "D", 1)
        assert errors == {} and rows[1]["wider"] is None and rows[1]["notes"] == ["wider 'listed' given with variant"]

    def test_d_refuses_numbers_and_unknown_words_and_reads_us_spelling(self):
        rows, errors, _ = OT.parse_answer(d_answer([(1, 3, {}), (2, "similar", {})]), "D", 2)
        assert rows == {} and "relation 3 is not one of" in errors[1] and "'similar'" in errors[2]
        rows, errors, _ = OT.parse_answer(d_answer([(1, "neighbors", {})]), "D", 1)
        assert rows[1]["value"] == "neighbours" and rows[1]["notes"] == ["relation 'neighbors' read as 'neighbours'"]
        rows, errors, _ = OT.parse_answer(answer([(1, "same")], "similarity"), "D", 1)
        assert errors == {1: "relation missing"}

    def test_the_other_rubrics_rows_are_unchanged(self):
        rows, _, meta = OT.parse_answer(answer([(1, 3)]), "A", 1)
        assert set(rows[1]) == {"reason", "value", "reason_first"} and "n_notes" not in meta


class TestPasses:
    def test_pass_order_seed_and_order(self):
        c = OT.Call(call_id="nn:x", set="nearest", target="alpha", listed=["gamma", "beta", "delta"])
        assert OT.pass_order_seed(0, 1, c.call_id) is None and OT.listed_order(c, None) == c.listed
        s2 = OT.pass_order_seed(0, 2, c.call_id)
        assert s2 != OT.pass_order_seed(0, 3, c.call_id) != OT.pass_order_seed(1, 2, c.call_id)
        assert s2 != OT.pass_order_seed(0, 2, "nn:y")
        o2 = OT.listed_order(c, s2)
        assert sorted(o2) == sorted(c.listed) and o2 == OT.listed_order(c, s2)        # a fixed permutation
        obj = json.loads(OT.render_user(c, corpus(), order_seed=s2))
        assert [t["label"] for t in obj["traits"]] == [corpus()[s]["label"] for s in o2]
        assert [t["id"] for t in obj["traits"]] == [1, 2, 3]
        assert OT.render_user(c, corpus()) == OT.render_user(c, corpus(), order_seed=None)

    def test_the_second_pass_reorders_most_calls(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        multi = [c for c in ps.calls if len(c.listed) > 1]
        moved = [c for c in multi if OT.listed_order(c, OT.pass_order_seed(0, 2, c.call_id)) != c.listed]
        assert multi and len(moved) >= len(multi) // 2
        st = OT.order_stats(ps, 0, [1, 2])["2"]
        assert st["same_order"] == len(ps.calls) - len(moved) and st["n_calls"] == len(ps.calls)

    def test_two_passes_have_distinct_keys_and_both_answers_are_kept(self, tmp_path):
        rb = OT.load_rubrics(keys=ALL)
        ps = pair_set()
        client = FakeAsyncAnthropic(arms_responder(rb))
        path = tmp_path / "r.jsonl"
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=path, retry_delays=(),
                             usage_path=tmp_path / "usage.json")
        res1 = run(r.run_stage("D", OT.SONNET, ps.calls, pass_no=1))
        res2 = run(r.run_stage("D", OT.SONNET, ps.calls, pass_no=2))
        assert res1.pass_no == 1 and res2.pass_no == 2 and res2.n_skipped == 0
        assert len(client.calls) == 2 * len(ps.calls) and res2.n_ok == res2.n_pairs == len(ps.pairs)
        recs = OT.read_records(path)
        assert sorted({rec["pass"] for rec in recs}) == [1, 2] and OT.record_passes(recs) == [1, 2]
        keys = OT.done_keys(recs)
        assert {k[3] for k in keys} == {1, 2} and len(keys) == 2 * len(ps.calls)
        for rec in recs:
            c = ps.call(rec["call_id"])
            seed = OT.pass_order_seed(0, rec["pass"], c.call_id)
            assert rec["order_seed"] == seed and rec["listed"] == OT.listed_order(c, seed)
            assert rec["request"]["user"] == OT.render_user(c, corpus(), order_seed=seed)
        a1 = OT.collect_answers(ps, recs, pass_no=1)[("D", OT.SONNET)]
        a2 = OT.collect_answers(ps, recs, pass_no=2)[("D", OT.SONNET)]
        assert set(a1) == set(a2) == {p.pair_id for p in ps.pairs}
        # the answer depends on the label only, so a pair's two answers agree whatever its id in each pass
        for p in ps.pairs:
            assert a1[p.pair_id]["value"] == a2[p.pair_id]["value"] == _label_value("D", corpus()[p.listed]["label"])
        assert any(rec["listed"] != ps.call(rec["call_id"]).listed for rec in recs if rec["pass"] == 2)
        # a resume of pass 2 sends nothing; pass 1's first-attempt rate is its own
        run(r.run_stage("D", OT.SONNET, ps.calls, pass_no=2))
        assert len(client.calls) == 2 * len(ps.calls)
        assert OT.first_attempt_parse(ps, recs, pass_no=2)[("D", OT.SONNET)] == {"ok": len(ps.pairs),
                                                                                 "total": len(ps.pairs)}
        # usage.json is written after every answer and agrees with the records
        u = MultiModelUsage.load_or_create(tmp_path / "usage.json")
        assert u.n_calls == len(recs) == OT.usage_from_records(recs).n_calls
        assert u.total_cost_usd == pytest.approx(OT.usage_from_records(recs).total_cost_usd)

    def test_records_without_a_pass_are_pass_1(self):
        ps = pair_set()
        c = ps.calls[0]
        text = json.dumps({"results": [{"id": i, "reason": "r", "similarity": 2} for i in range(1, len(c.listed) + 1)]})
        rec = {"rubric": "A", "model": OT.OPUS, "call_id": c.call_id, "listed": c.listed, "response": {"text": text}}
        assert OT.response_key(rec) == ("A", OT.OPUS, c.call_id, 1)
        assert set(OT.collect_answers(ps, [rec], pass_no=1)) == {("A", OT.OPUS)}
        assert OT.collect_answers(ps, [rec], pass_no=2) == {}

    def test_the_session_lock_refuses_a_second_session(self, tmp_path):
        held = OT.acquire_session_lock(tmp_path / "run")
        try:
            with pytest.raises(OT.SessionBusy, match="another session"):
                OT.acquire_session_lock(tmp_path / "run")
        finally:
            held.close()
        OT.acquire_session_lock(tmp_path / "run").close()             # free again once released

    def test_write_usage_is_whole(self, tmp_path):
        u = MultiModelUsage()
        u.charge(OT.OPUS, 1000, 200)
        OT.write_usage(u, tmp_path / "usage.json")
        assert MultiModelUsage.load_or_create(tmp_path / "usage.json").n_calls == 1
        assert not (tmp_path / "usage.json.tmp").exists()


def _ans(values: dict, **extra) -> dict:
    return {pid: {"value": v, "reason": "r", "reason_first": True, "error": None, **extra.get(pid, {})}
            for pid, v in values.items()}


class TestArmsStatistics:
    def test_side(self):
        assert [OT.side(v) for v in (4, 3, 2, 0, "opposite", "unsure", None)] == [True, True, False, False, False,
                                                                                     None, None]
        assert OT.side(3, cutoff=4) is False

    def nearest_pairs(self):
        ps = pair_set(n_targets=4)
        return [p for p in ps.pairs if p.group == OT.NEAREST]

    def test_compare_answers_on_made_up_answers(self):
        pairs = self.nearest_pairs()[:6]
        ids = [p.pair_id for p in pairs]
        first = _ans(dict(zip(ids, [2, 3, 4, "opposite", 1, 5])))
        second = _ans(dict(zip(ids, [3, 3, 3, 1, 1, 2])))
        x = OT.compare_answers("C", first, second, pairs)
        n = x["native"]
        assert n["n_both_parsed"] == 6 and n["exact_all"] == pytest.approx(2 / 6, abs=1e-4)
        assert n["n_numeric"] == 5 and n["within_one"] == pytest.approx(4 / 5, abs=1e-4)     # all but 5/2
        assert x["flips_native"]["by_pair"] == {"1/opposite": 1, "2/3": 1, "2/5": 1, "3/4": 1}
        assert x["flips_native"]["n"] == 4 and x["flips_native"]["adjacent"] == 2
        # decision scale: C's 4 -> 3 and 5 -> 4, so 3/4 is no longer a disagreement
        d = x["decision"]
        assert d["exact_all"] == pytest.approx(3 / 6, abs=1e-4)
        assert x["flips_decision"]["by_pair"] == {"1/opposite": 1, "2/3": 1, "2/4": 1}
        # cut-off 3: 2 -> 3 (second covered only), 5 -> 2 (first covered only); opposite -> 1 stays uncovered
        c = x["cutoff"]
        assert (c["n"], c["crossings"], c["first_only"], c["second_only"]) == (6, 2, 1, 1)
        assert sorted((y["first"], y["second"]) for y in c["pairs"]) == [(2, 3), (5, 2)]

    def test_compare_answers_for_d_uses_ranks_and_relation_names(self):
        pairs = self.nearest_pairs()[:4]
        ids = [p.pair_id for p in pairs]
        first = _ans(dict(zip(ids, ["contains", "overlap", "same", "unsure"])))
        second = _ans(dict(zip(ids, ["variant", "contains", "same", "different"])))
        x = OT.compare_answers("D", first, second, pairs)
        assert x["native"]["exact_all"] == pytest.approx(1 / 4, abs=1e-4)
        assert x["native"]["n_numeric"] == 3 and x["native"]["within_one"] == 1.0      # ranks 3/4, 2/3, 5/5
        assert x["flips_native"]["by_pair"] == {"overlap/contains": 1, "contains/variant": 1, "different/unsure": 1}
        assert x["decision"]["exact_all"] == pytest.approx(2 / 4, abs=1e-4)          # contains and variant are both 3
        assert x["cutoff"]["crossings"] == 1 and x["cutoff"]["second_only"] == 1      # overlap -> contains
        assert x["cutoff"]["n"] == 3                                                  # unsure has no side

    def test_coverage(self):
        pairs = self.nearest_pairs()
        call0 = pairs[0].call_id
        vals = {p.pair_id: (5 if p.call_id == call0 and p.nn_rank == 1 else 2) for p in pairs}
        vals[pairs[-1].pair_id] = "opposite"
        cov = OT.coverage(pairs, "C", _ans(vals))
        assert cov["n"] == len(pairs) and cov["covered"] == 1 and cov["targets_covered"] == 1
        assert cov["n_targets"] == len({p.call_id for p in pairs}) and cov["opposite"] == 1
        assert OT.coverage(pairs, "C", _ans({p.pair_id: 3 for p in pairs}))["share"] == 1.0
        assert OT.coverage(pairs, "D", _ans({p.pair_id: "overlap" for p in pairs}))["covered"] == 0

    def test_relation_stats_and_wider_agreement(self):
        a = _ans({"p1": "contains", "p2": "contains", "p3": "contains", "p4": "overlap", "p5": "neighbours"},
                 p1={"wider": "target", "notes": []}, p2={"wider": None, "notes": ["contains without wider"]},
                 p3={"wider": None, "notes": ["wider 'both' is not target or listed"]},
                 p4={"wider": None, "notes": ["wider 'listed' given with overlap"]},
                 p5={"wider": None, "notes": ["relation 'neighbors' read as 'neighbours'"]})
        s = OT.relation_stats(a)
        assert s["counts"] == {"contains": 3, "overlap": 1, "neighbours": 1} and s["n_contains"] == 3
        assert s["wider"] == {"target": 1, "listed": 0, "missing": 1, "invalid": 1}
        assert s["wider_missing_share"] == pytest.approx(2 / 3, abs=1e-3)
        assert s["wider_with_other_relation"] == 1 and s["alias_spellings"] == 1
        b = _ans({"p1": "contains", "p2": "contains", "p3": "variant"}, p1={"wider": "listed"}, p2={"wider": "target"})
        w = OT.wider_agreement(a, b)
        assert w == {"n_both_contains": 2, "same": 0, "different": 1, "unknown": 1}

    def test_scope_kinds(self):
        a = _ans({"p1": 3, "p2": 3, "p3": 3, "p4": 2},
                 p1={"reason": "The same fussiness, narrowed to food."},
                 p2={"reason": "Miserly is a stronger form, with the stress on hoarding."},
                 p3={"reason": "Both are about money."}, p4={"reason": "narrowed but each adds something"})
        k = OT.scope_kinds(a)
        assert k["n"] == 3 and k["kinds"]["narrowed"] == 1 and k["kinds"]["stronger"] == 1
        assert k["kinds"]["emphasis"] == 1 and k["none"] == 1 and k["multiple"] == 1
        assert k["none_share"] == pytest.approx(1 / 3, abs=1e-3)

    def fake_by_pass(self, ps, rubrics, models, f):
        return {p: {(r, m): {pr.pair_id: {"value": f(p, r, m, pr), "reason": "narrowed", "reason_first": True,
                                          "error": None, **({"wider": "target", "notes": []} if r == "D" else {})}
                             for pr in ps.pairs} for r in rubrics for m in models} for p in (1, 2)}

    def test_analyse_arms_and_its_tables(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        models = [OT.SONNET, OT.OPUS]

        def f(p, r, m, pr):
            v = _label_value(r, pr.listed)
            # Sonnet's pass 2 of arm C says 3 where pass 1 said 2: flips across the cut-off
            if r == "C" and m == OT.SONNET and p == 2 and v == 2:
                return 3
            return v
        by_pass = self.fake_by_pass(ps, OT.ARMS, models, f)
        baseline = {"run_id": "overlap_test_1", "answers": {m: by_pass[1][("A", m)] for m in models}}
        arms = OT.analyse_arms(ps, by_pass, models=models, reference=OT.OPUS, seed=0, baseline=baseline)
        assert arms["passes"] == [1, 2] and arms["rubrics"] == list(OT.ARMS)
        for r in OT.ARMS:
            sc = arms["per_arm"][r]["self_consistency"]
            assert set(sc) == set(models)
            assert sc[OT.OPUS]["native"]["exact_all"] == 1.0 and sc[OT.OPUS]["cutoff"]["crossings"] == 0
            bm = arms["per_arm"][r]["between_models"][OT.SONNET]
            assert set(bm) == {"1", "2"} and bm["1"]["native"]["exact_all"] == 1.0
        c_sonnet = arms["per_arm"]["C"]["self_consistency"][OT.SONNET]
        n2 = sum(_label_value("C", pr.listed) == 2 for pr in ps.pairs)
        n2_nearest = sum(_label_value("C", pr.listed) == 2 for pr in ps.pairs if pr.group == OT.NEAREST)
        assert c_sonnet["flips_native"]["by_pair"] == {"2/3": n2}
        assert c_sonnet["cutoff"]["crossings"] == c_sonnet["cutoff"]["second_only"] == n2_nearest
        assert arms["per_arm"]["C"]["between_models"][OT.SONNET]["2"]["cutoff"]["second_only"] == n2_nearest
        assert set(arms["per_arm"]["D"]["relations"][OT.OPUS]) == {"1", "2"}
        assert arms["per_arm"]["D"]["wider_between_passes"][OT.OPUS]["different"] == 0
        assert "scope_kinds" in arms["per_arm"]["E"] and "scope_kinds" in arms["per_arm"]["A"]
        assert set(arms["baseline"]["per_model"]) == set(models)
        assert arms["baseline"]["per_model"][OT.OPUS]["native"]["exact_all"] == 1.0
        rows = {(x["arm"], x["model"]): x for x in arms["cross_arm"]}
        assert set(rows) == {(r, m) for r in OT.ARMS for m in models}
        assert rows[("C", OT.SONNET)]["pass_flips_at_cutoff"] == n2_nearest
        assert rows[("C", OT.OPUS)]["versus"] == OT.SONNET and rows[("C", OT.SONNET)]["versus"] == OT.SONNET
        assert rows[("A", OT.OPUS)]["agreement_native"] == {"1": 1.0, "2": 1.0}
        json.dumps(arms)
        summary = OT.analyse(ps, by_pass[1], models=models, reference=OT.OPUS, n_boot=20)
        assert set(summary["agreement"]) == set(OT.ARMS) and "B" not in summary["groups"]
        summary["arms"] = arms
        md = OT.summary_markdown(summary, ps, corpus())
        assert set(c_sonnet["by_prompt"]) == set(OT.PROMPT_GROUPS)
        assert sum(x["n"] for x in c_sonnet["by_prompt"].values()) == len(ps.pairs)
        for head in ("## The arms experiment: 2 passes", "### Cross-arm table", "### Parse rates by pass",
                     "### Arm C: overlap_six", "### Arm D: overlap_relation", "### Arm E: overlap_scope",
                     "Relations named", "The wider of a \"contains\"", "Kinds of difference",
                     "Exact agreement between the passes by how pass 2 sent",
                     "### Arm A, pass 1, against overlap_test_1", "## Known groups, rubric D"):
            assert head in md, head
        table = md.split("### Cross-arm table")[1].split("\n\n")[1].splitlines()
        assert len(table) == 2 + len(OT.ARMS) * len(models)
        assert all(line.count("|") == 11 for line in table)                 # ten cells on every row

    def test_prompt_groups_and_consistency_by_prompt(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        groups = OT.prompt_groups(ps, 0, 2)
        assert set(groups) == {p.pair_id for p in ps.pairs}
        for c in ps.calls:
            same = OT.listed_order(c, OT.pass_order_seed(0, 2, c.call_id)) == c.listed
            want = "single" if len(c.listed) == 1 else ("same_order" if same else "reordered")
            assert all(groups[f"{c.call_id}>{s}"] == want for s in c.listed)
        assert {"single", "reordered"} <= set(groups.values())
        first = {pid: {"value": 2} for pid in groups}
        second = {pid: {"value": 3 if g == "reordered" else 2} for pid, g in groups.items()}
        bp = OT.consistency_by_prompt("C", first, second, groups)
        assert bp["single"]["exact_native"] == 1.0 and bp["reordered"]["exact_native"] == 0.0
        assert bp["reordered"]["exact_decision"] == 0.0                     # C's 2 and 3 stay apart
        assert sum(bp[g]["n"] for g in OT.PROMPT_GROUPS) == len(groups)

    def test_analysis_of_one_pass_has_no_arms_section(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        by_pass = {1: TestArmsStatistics().fake_by_pass(ps, ["A"], [OT.SONNET, OT.OPUS], lambda *a: 2)[1]}
        arms = OT.analyse_arms(ps, by_pass, models=[OT.SONNET, OT.OPUS])
        assert arms["per_arm"]["A"]["self_consistency"] == {} and arms["baseline"] is None
        summary = OT.analyse(ps, by_pass[1], models=[OT.SONNET, OT.OPUS], n_boot=20)
        summary["arms"] = arms
        assert "## The arms experiment" not in OT.summary_markdown(summary, ps, corpus())

    def test_known_groups_read_the_decision_scale(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        ans = {("C", OT.OPUS): {p.pair_id: {"value": 5, "reason": "r", "reason_first": True, "error": None}
                                for p in ps.pairs}}
        s = OT.analyse(ps, ans, models=[OT.OPUS], n_boot=20)
        assert s["groups"]["C"][OT.OPUS]["nearest"]["mean"] == 4.0                # 5 -> 4
        assert s["by_score"]["C"][OT.OPUS]["5"]["n"] == len(ps.pairs)             # native answers
        assert s["agreement"] == {"C": {}} and s["scales"]["C"]["k"] == 6

    def test_estimate_reads_the_rubric_facts(self):
        ps = pair_set()
        rb = OT.load_rubrics(keys=ALL)
        est = OT.estimate(ps.calls, corpus(), rb, [OT.OPUS], ["A", "D", "E"], pass_no=2)
        by = {x.label.split(" ")[1]: x for x in est.lines}
        assert all(", pass 2" in x.label for x in est.lines)
        assert by["D"].out_tok > by["E"].out_tok > by["A"].out_tok              # 66, 62, 60 per listed trait
        assert by["D"].in_tok > by["A"].in_tok                                  # the longer rubric text
        assert len(OT.estimate(ps.calls, corpus(), rb, [OT.OPUS]).lines) == len(ALL)


# =========================================================================== round 2 of the arms experiment
# (coding_plan_overlap_arms.md, "Round 2", 2026-10-04): A2, C2, D2, E2; the confusion subset; the calls of
# the subset only; each round-2 arm against its round-1 arm on the same pairs

ROUND2_NAMES = {"A2": "overlap_concept_implies", "C2": "overlap_six_implies", "D2": "overlap_relation_implies",
                "E2": "overlap_scope_implies"}


class TestRound2Rubrics:
    def test_round_2_loads_from_its_pinned_files_with_its_parents_facts(self):
        rb = OT.load_rubrics(keys=OT.ROUND2)
        assert list(OT.ROUND2) == ["A2", "C2", "D2", "E2"]
        for r, parent in (("A2", "A"), ("C2", "C"), ("D2", "D"), ("E2", "E")):
            assert rb[r]["name"] == ROUND2_NAMES[r] and rb[r]["version"] == 1
            assert rb[r]["text"] == sr.load_prompt(ROUND2_NAMES[r]) != sr.load_prompt(OT.RUBRICS[parent]["name"])
            spec, par = OT.RUBRICS[r], OT.RUBRICS[parent]
            assert spec["round1"] == parent and "round1" not in par
            for k in ("key", "scale", "categories", "decision", "decision_note", "ranks", "extra", "aliases",
                      "out_per_row", "kinds"):
                assert spec.get(k) == par.get(k), (r, k)
        assert all("neither implies the other" in rb[r]["text"] for r in OT.ROUND2)

    def test_decision_scale_and_parsing(self):
        assert [OT.decision_value("C2", v) for v in (5, 4, 3, 2, 1, 0)] == [4, 3, 3, 2, 1, 0]
        assert {rel: OT.decision_value("D2", rel) for rel in OT.RELATIONS} == {
            "same": 4, "variant": 3, "contains": 3, "overlap": 2, "neighbours": 1, "different": 0}
        for r in ("A2", "E2"):
            assert [OT.decision_value(r, v) for v in range(5)] == list(range(5))
            rows, errors, _ = OT.parse_answer(answer([(1, 5)]), r, 1)
            assert rows == {} and "is not 0-4" in errors[1]
        rows, errors, _ = OT.parse_answer(answer([(1, 5), (2, "opposite")]), "C2", 2)
        assert {i: x["value"] for i, x in rows.items()} == {1: 5, 2: "opposite"} and errors == {}
        text = d_answer([(1, "contains", {"wider": "listed"}), (2, "overlap", {"wider": "target"}), (3, "contains", {})])
        rows, errors, meta = OT.parse_answer(text, "D2", 3)
        assert errors == {} and [rows[i]["value"] for i in (1, 2, 3)] == ["contains", "overlap", "contains"]
        assert [rows[i]["wider"] for i in (1, 2, 3)] == ["listed", None, None]
        assert rows[2]["notes"] == ["wider 'target' given with overlap"] and rows[3]["notes"] == ["contains without wider"]
        assert OT.has_wider("D2") and OT.has_wider("D") and not any(OT.has_wider(r) for r in ("A2", "C2", "E2"))

    def test_kinds_are_searched_on_e2_and_a2_as_on_e_and_a(self):
        assert [OT.RUBRICS[r].get("kinds") for r in ("A", "E", "A2", "E2", "C2", "D2")] == [
            "control", "asked", "control", "asked", None, None]


class TestRound2Patterns:
    #: the patterns as the brief writes them, byte for byte
    BRIEF_CONTAINMENT = (r"narrow|broader|broadened|\bwider\b|\bpart of\b|subset|\bincludes?\b|specific (case|form|kind|"
                         r"instance)|special case|restricted to|limited to|carried (further|beyond)|stronger (form|degree|"
                         r"version)|a (form|kind|type|case) of")
    BRIEF_TWO_SIDED = (r"(each|both)\s+(add|bring|contribut|has something|lacks)|adds?\b[^.;]*\b(while|whereas|and)\b"
                       r"[^.;]*\b(adds?|stresses|brings|emphasi)")

    def test_the_patterns_are_the_briefs(self):
        assert OT.CONTAINMENT_PATTERN == self.BRIEF_CONTAINMENT and OT.TWO_SIDED_PATTERN == self.BRIEF_TWO_SIDED
        assert OT.CONTAINMENT_RE.flags & re.I and OT.TWO_SIDED_RE.flags & re.I

    def test_reasons(self):
        # round 1's slips (m3_overlap_arms_readout.md): a containment described, then "overlap" answered
        assert OT.describes_containment("The sloppy work is part of careless, but leaves out broken deadlines.")
        assert OT.describes_containment("Ecocentric includes the environmental priority but adds a whole-ecosystem view.")
        assert OT.describes_containment("Fussy eater is fussiness NARROWED to food.")
        # a two-sided overlap described: never a containment, even with a containment word in it
        both = "Ecocentric is narrower in one way, and each adds something the other lacks."
        assert OT.describes_two_sided(both) and not OT.describes_containment(both)
        assert OT.describes_two_sided("Neurotic adds instability, so each has something the other lacks.")
        assert OT.describes_two_sided("Studious adds diligence while bookish adds a taste for reading.")
        for plain in ("Both are about money.", "It is included in the list.", "", None):
            assert not OT.describes_containment(plain) and not OT.describes_two_sided(plain)


def _reading(run, r, m, p, v, why="Both are about speech."):
    return {"run": run, "rubric": r, "model": m, "pass": p, "value": v, "decision": OT.decision_value(r, v),
            "reason": why}


def fake_source_run(path, rb, stages, value, reason, *, pairs=None):
    """A source run's records: each (rubric, model, pass) stage sent through the runner (the records are
    real), the answer ``value(rubric, model, pass, target label, listed label)`` with ``reason(...)``."""
    by_text = {v["text"]: k for k, v in rb.items()}
    ps = pairs or pair_set(n_targets=6, n_antonyms=2, n_random=2)
    for r, m, p in stages:
        def responder(kw, p=p):
            rr = by_text[system_text(kw)]
            obj = json.loads(user_text(kw))
            rows = [{"id": t["id"], "reason": reason(rr, kw["model"], p, obj["target"]["label"], t["label"]),
                     OT.RUBRICS[rr]["key"]: value(rr, kw["model"], p, obj["target"]["label"], t["label"])}
                    for t in obj["traits"]]
            return make_response(json.dumps({"results": rows}), input_tokens=900, output_tokens=150)
        runner = OT.OverlapRunner(FakeAsyncAnthropic(responder), rb, corpus(), usage=MultiModelUsage(),
                                  responses_path=path, retry_delays=())
        run(runner.run_stage(r, m, ps.calls, pass_no=p))
    return OT.read_records(path)


class TestConfusionSubset:
    def test_the_two_rules_on_made_up_readings(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        p = ps.pairs
        readings = {
            p[0].pair_id: [_reading("x", "A", OT.SONNET, 1, 2), _reading("y", "C", OT.OPUS, 2, 4)],   # 2 and C's 4 (3)
            p[1].pair_id: [_reading("x", "D", OT.SONNET, 2, "overlap", "Fussy eater is fussiness narrowed to food.")],
            p[2].pair_id: [_reading("x", "A", OT.SONNET, 1, 2, "Narrower in one way, and each adds something.")],
            p[3].pair_id: [_reading("x", "A", OT.SONNET, 1, 3, "Narrowed to food."), _reading("x", "A", OT.OPUS, 1, 4)],
            p[4].pair_id: [_reading("x", "C", OT.SONNET, 1, 3), _reading("x", "C", OT.OPUS, 1, 2, "a special case of it")],
            p[5].pair_id: [_reading("x", "D", OT.SONNET, 1, "contains"), _reading("x", "D", OT.OPUS, 1, "variant")],
        }
        s = OT.confusion_subset(ps, readings)
        assert s["pair_ids"] == [p[0].pair_id, p[1].pair_id, p[4].pair_id]
        c = s["counts"]
        assert (c["n_pairs"], c["rule_1"], c["rule_2"], c["rule_2_only"], c["both_rules"]) == (3, 2, 2, 1, 1)
        held = {p[i].call_id for i in (0, 1, 4)}
        assert s["call_ids"] == [x.call_id for x in ps.calls if x.call_id in held]
        sent = [x.pair_id for x in ps.pairs if x.call_id in held]
        assert s["control_pair_ids"] == [x for x in sent if x not in s["pair_ids"]]
        assert (c["n_calls"], c["n_pairs_sent"], c["n_controls"]) == (len(held), len(sent), len(sent) - 3)
        assert (c["of_calls"], c["of_pairs"]) == (len(ps.calls), len(ps.pairs))
        ev = s["evidence"]
        assert ev[p[0].pair_id]["rules"] == [1] and ev[p[0].pair_id]["decisions"] == {"2": 1, "3": 1}
        assert ev[p[1].pair_id]["rules"] == [2] and ev[p[1].pair_id]["slips"][0]["value"] == "overlap"
        assert ev[p[4].pair_id]["rules"] == [1, 2] and p[5].pair_id not in ev
        assert "containment" in s["patterns"] and s["rule"] == OT.SUBSET_RULE
        json.dumps(s)

    def test_readings_from_records_skip_rubric_b_and_keep_both_passes(self, tmp_path):
        rb = list_rubrics(keys=("A", "B", "C", "D"))
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        confused, slipped = ps.pairs[0], [p for p in ps.pairs if p.call_id != ps.pairs[0].call_id][-1]
        lab = lambda s: corpus()[s]["label"]                       # noqa: E731

        def value(r, m, p, target, listed):
            if r == "B":
                return 3 if m == OT.OPUS else 2                   # a 2 and a 3 on every pair: never counts
            if (target, listed) == (lab(confused.target), lab(confused.listed)) and r == "A":
                return 2 if p == 1 else 3                          # a 2 in pass 1, a 3 in pass 2: rule 1
            if (target, listed) == (lab(slipped.target), lab(slipped.listed)) and r == "D":
                return "overlap"
            return "neighbours" if r == "D" else 1

        def reason(r, m, p, target, listed):
            return ("Fussy eater is fussiness narrowed to food." if (target, listed) == (lab(slipped.target),
                                                                                         lab(slipped.listed))
                    else "Both are about speech.")
        a = fake_source_run(tmp_path / "a.jsonl", rb, [("A", OT.SONNET, 1), ("A", OT.SONNET, 2), ("D", OT.OPUS, 1)],
                            value, reason, pairs=ps)
        b = fake_source_run(tmp_path / "b.jsonl", rb, [("B", OT.HAIKU, 1), ("B", OT.OPUS, 1), ("C", OT.OPUS, 1)],
                            value, reason, pairs=ps)
        readings, sources = OT.pair_readings(ps, {"a": a, "b": b})
        assert {(s["run"], s["rubric"], s["model"], s["pass"]) for s in sources} == {
            ("a", "A", OT.SONNET, 1), ("a", "A", OT.SONNET, 2), ("a", "D", OT.OPUS, 1), ("b", "C", OT.OPUS, 1)}
        assert all(s["n_readings"] == len(ps.pairs) and s["n_unparsed"] == 0 for s in sources)
        assert all(s["rubric_versions"] == [1 if s["rubric"] in "CD" else rb["A"]["version"]] for s in sources)
        assert all(len(v) == 4 for v in readings.values()) and len(readings) == len(ps.pairs)
        s = OT.confusion_subset(ps, readings)
        # the fake answers by labels, so an ordered pair listed in two calls is answered alike in both
        one = [p.pair_id for p in ps.pairs if (p.target, p.listed) == (confused.target, confused.listed)]
        two = [p.pair_id for p in ps.pairs if (p.target, p.listed) == (slipped.target, slipped.listed)]
        assert s["pair_ids"] == [p.pair_id for p in ps.pairs if p.pair_id in set(one) | set(two)]
        assert s["counts"]["rule_1"] == len(one) and s["counts"]["rule_2_only"] == len(two)
        assert all(s["evidence"][x]["slips"][0]["reason"].startswith("Fussy eater") for x in two)
        assert s["counts"]["readings_per_pair"] == {"4": len(ps.pairs)}


class TestContradictions:
    def test_counts_and_shares(self):
        a = [{"value": 2, "reason": "Fussy eater is fussiness narrowed to food."}, {"value": 2, "reason": "Both are about money."},
             {"value": 2, "reason": "Narrower in one way, and each adds something."},
             {"value": 3, "reason": "Studious adds diligence while bookish adds a taste for reading."},
             {"value": 3, "reason": "The same thing, carried further."}, {"value": 1, "reason": "narrowed"},
             {"value": None, "reason": None}, {"value": "opposite", "reason": "narrowed"}]
        c = OT.contradictions("A", a)
        assert (c["n_2"], c["forward"], c["n_3"], c["reverse"]) == (3, 1, 2, 1)
        assert c["forward_share"] == pytest.approx(1 / 3, abs=1e-3) and c["reverse_share"] == 0.5
        assert c["reverse_by_native"] == {"3": {"n": 2, "reverse": 1}}
        assert OT.contradictions("A", []) == {"n_2": 0, "forward": 0, "forward_share": None, "n_3": 0, "reverse": 0,
                                              "reverse_share": None, "reverse_by_native": {}}

    def test_c_and_d_read_the_decision_scale(self):
        d = [{"value": "overlap", "reason": "The plainer is part of the other."},
             {"value": "contains", "reason": "Each adds something of its own."},
             {"value": "variant", "reason": "Both add flavour."}, {"value": "neighbours", "reason": "narrowed"}]
        c = OT.contradictions("D2", d)
        assert (c["n_2"], c["forward"], c["n_3"], c["reverse"]) == (1, 1, 2, 2)
        assert c["reverse_by_native"] == {"contains": {"n": 1, "reverse": 1}, "variant": {"n": 1, "reverse": 1}}
        c6 = OT.contradictions("C2", [{"value": 4, "reason": "each adds"}, {"value": 3, "reason": "x"},
                                      {"value": 5, "reason": "each adds"}])
        assert (c6["n_3"], c6["reverse"]) == (2, 1) and list(c6["reverse_by_native"]) == ["3", "4"]


class TestRound2Analysis:
    def test_crossings_and_coverage_over_every_group_when_asked(self):
        ps = pair_set(n_targets=4, n_antonyms=2, n_random=2)
        first, second = _ans({p.pair_id: 2 for p in ps.pairs}), _ans({p.pair_id: 3 for p in ps.pairs})
        n_near = sum(p.group == OT.NEAREST for p in ps.pairs)
        assert n_near < len(ps.pairs)
        assert OT.cutoff_crossings(ps.pairs, "A", first, second)["crossings"] == n_near            # unchanged default
        assert OT.cutoff_crossings(ps.pairs, "A", first, second, nearest_only=False)["crossings"] == len(ps.pairs)
        assert OT.coverage(ps.pairs, "A", second)["n"] == n_near
        assert OT.coverage(ps.pairs, "A", second, nearest_only=False)["n"] == len(ps.pairs)
        row = OT.cutoff_crossings(ps.pairs, "A", first, second)["pairs"][0]
        assert (row["first_reason"], row["second_reason"], row["group"]) == ("r", "r", OT.NEAREST)

    def test_restricted_pair_set_and_marked_rows(self):
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        keep = [ps.calls[2].call_id, ps.calls[0].call_id]
        v = ps.restricted(keep)
        assert [c.call_id for c in v.calls] == [ps.calls[0].call_id, ps.calls[2].call_id]       # pair-set order
        assert [p.pair_id for p in v.pairs] == [p.pair_id for p in ps.pairs if p.call_id in keep]
        assert v.info["restricted_to"] == {"n_calls": 2, "of_calls": len(ps.calls), "of_pairs": len(ps.pairs)}
        with pytest.raises(ValueError, match="not in the pair set"):
            ps.restricted(["nn:nope"])
        ans = {("A2", OT.OPUS): _ans({p.pair_id: 2 for p in v.pairs})}
        rows = OT.results_rows(v, ans, subset=[v.pairs[0].pair_id])
        assert [r["in_subset"] for r in rows] == [True] + [False] * (len(v.pairs) - 1)
        assert "in_subset" not in OT.results_rows(v, ans)[0]

    def made_up(self):
        """Round 1 answers every pair (A, C, D, E; Sonnet and Opus; two passes): on the subset's pairs Sonnet
        answers 2 with a containment reason and Opus 3; everything else 1.  Round 2 answers the sent calls only:
        both models 3 on the subset's pairs, except Sonnet's pass 2 on the first one (2, a containment reason)."""
        ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
        models = [OT.SONNET, OT.OPUS]
        nearest = [p for p in ps.pairs if p.group == OT.NEAREST]
        labelled = [p for p in ps.pairs if p.group != OT.NEAREST]
        subset_ids = [nearest[0].pair_id, nearest[-1].pair_id, labelled[0].pair_id]
        held = {p.call_id for p in ps.pairs if p.pair_id in subset_ids}
        sent = [p for p in ps.pairs if p.call_id in held]
        native = {2: {"D": "overlap"}, 3: {"D": "contains"}, 1: {"D": "neighbours"}}

        def val(r, v):
            return native[v].get(OT.RUBRICS[r].get("round1", r), v)
        slip = "The narrower one is fussiness limited to food."
        r1 = {p: {(r, m): {} for r in OT.ARMS for m in models} for p in (1, 2)}
        r2 = {p: {(r, m): {} for r in OT.ROUND2 for m in models} for p in (1, 2)}
        for pr in ps.pairs:
            for p in (1, 2):
                for r in OT.ARMS:
                    for m in models:
                        if pr.pair_id in subset_ids:
                            v, why = (2, slip) if m == OT.SONNET else (3, "The same concept, narrowed.")
                        else:
                            v, why = 1, "Both are about speech."
                        r1[p][(r, m)][pr.pair_id] = {"value": val(r, v), "reason": why, "reason_first": True,
                                                     "error": None}
        for pr in sent:
            for p in (1, 2):
                for r in OT.ROUND2:
                    for m in models:
                        if pr.pair_id == subset_ids[0] and m == OT.SONNET and p == 2:
                            v, why = 2, slip
                        elif pr.pair_id in subset_ids:
                            v, why = 3, "Anyone with the richer trait has the plainer one."
                        else:
                            v, why = 1, "Both are about speech."
                        r2[p][(r, m)][pr.pair_id] = {"value": val(r, v), "reason": why, "reason_first": True,
                                                     "error": None}
        subset = {"pair_ids": subset_ids, "call_ids": [c.call_id for c in ps.calls if c.call_id in held]}
        return ps, models, subset_ids, sent, r1, r2, subset

    def test_each_arm_against_its_round_1_arm_on_the_same_pairs(self):
        ps, models, subset_ids, sent, r1, r2, subset = self.made_up()
        out = OT.analyse_round2(ps, r2, r1, subset=subset, models=models, reference=OT.OPUS, round1_run="r1")
        assert out["arms"] == list(OT.ROUND2) and out["pairing"] == {"A2": "A", "C2": "C", "D2": "D", "E2": "E"}
        assert out["populations"]["subset"]["n_pairs"] == 3 and out["populations"]["sent"]["n_pairs"] == len(sent)
        assert out["populations"]["subset"]["by_group"][OT.NEAREST] == 2
        for r in OT.ROUND2:
            sub = out["per_population"]["subset"][r]
            one, two = sub["round1"], sub["round2"]
            assert one["rubric"] == OT.RUBRICS[r]["round1"] and two["rubric"] == r
            assert one["n_pairs"] == two["n_pairs"] == 3                      # round 1 read on the same pairs only
            # round 1: Sonnet 2 / Opus 3 on all three (the labelled pair counts): three crossings in each pass
            assert [one["between_models"][OT.SONNET][p]["cutoff"]["crossings"] for p in ("1", "2")] == [3, 3]
            assert one["contradictions"][OT.SONNET]["pooled"]["forward"] == 6
            assert one["contradictions"][OT.SONNET]["pooled"]["forward_share"] == 1.0
            assert one["self_consistency"][OT.SONNET]["decision"]["exact_all"] == 1.0
            # round 2: one crossing (pass 2), one slip, one flip of Sonnet's
            assert [two["between_models"][OT.SONNET][p]["cutoff"]["crossings"] for p in ("1", "2")] == [0, 1]
            assert two["contradictions"][OT.SONNET]["pooled"]["forward"] == 1
            assert two["self_consistency"][OT.SONNET]["cutoff"]["crossings"] == 1
            assert two["self_consistency"][OT.SONNET]["decision"]["exact_all"] == pytest.approx(2 / 3, abs=1e-4)
            assert two["coverage"][OT.OPUS]["1"]["share"] == 1.0
            # every pair sent: the controls answer 1 in both rounds
            al = out["per_population"]["sent"][r]
            assert al["round1"]["n_pairs"] == al["round2"]["n_pairs"] == len(sent)
            assert al["round2"]["coverage"][OT.OPUS]["1"]["covered"] == 3
        assert "relations" in out["per_population"]["subset"]["D2"]["round2"]
        assert "relations" in out["per_population"]["subset"]["D2"]["round1"]
        assert "relations" not in out["per_population"]["subset"]["A2"]["round2"]
        test = {(t["population"], t["arm"]): t for t in out["test"]}
        t = test[("subset", "A2")]
        assert (t["r1"]["contradictions"], t["r2"]["contradictions"]) == (6, 1)
        assert (t["r1"]["crossings"], t["r2"]["crossings"]) == (6, 1)
        assert t["fewer_contradictions"] and t["fewer_crossings"]
        assert not t["consistency_not_worse"] and not t["improves"]          # Sonnet's flip: 3/3 -> 2/3
        rows = [x for x in out["rows"] if x["population"] == "subset" and x["arm"] == "C2"]
        assert [x["model"] for x in rows] == models and all(x["round1_arm"] == "C" for x in rows)
        assert rows[0]["r1"]["forward"] == 6 and rows[0]["r2"]["forward"] == 1
        assert rows[1]["versus"] == OT.SONNET and rows[1]["r2"]["crossings"] == {"1": 0, "2": 1}
        ex = out["examples"]["A2"]
        assert [x["pair_id"] for x in ex["forward"]] == [subset_ids[0]] and ex["forward"][0]["in_subset"]
        assert ex["forward"][0]["reason"].startswith("The narrower one")
        assert [(x["pair_id"], x["pass"]) for x in ex["crossings"]] == [(subset_ids[0], 2)]
        assert ex["crossings"][0]["first_model"] == OT.OPUS and ex["crossings"][0]["second"] == 2
        json.dumps(out)

    def test_without_a_round_1_run_or_a_subset(self):
        ps, models, subset_ids, sent, r1, r2, subset = self.made_up()
        out = OT.analyse_round2(ps, r2, None, subset=None, models=models, reference=OT.OPUS)
        assert list(out["per_population"]) == ["sent"] and out["round1_run"] is None
        t = out["test"][0]
        assert t["r1"]["contradictions"] == 0 and t["r1"]["consistency_decision"] == {m: None for m in models}
        assert not t["improves"]

    def test_round_2_tables(self):
        ps, models, subset_ids, sent, r1, r2, subset = self.made_up()
        out = OT.analyse_round2(ps, r2, r1, subset=subset, models=models, reference=OT.OPUS, round1_run="overlap_arms_1")
        counts = {"n_pairs": 3, "rule_1": 2, "rule_2_only": 1, "n_calls": len(subset["call_ids"]), "of_calls": len(ps.calls),
                  "n_pairs_sent": len(sent), "n_controls": len(sent) - 3}
        md = "\n".join(OT.round2_markdown(out, corpus(), lambda m: OT.SHORT.get(m, m), subset_counts=counts))
        for head in ("## Round 2: the clarified lines, on the confusion subset", "### The brief's test",
                     "### The subset's pairs: 3 pairs", f"### Every pair sent (the subset and its controls): {len(sent)} pairs",
                     "D2 against D, the relations named", "#### A2 (overlap_concept_implies)", "**Selection.**",
                     "against its round-1 arm from overlap_arms_1"):
            assert head in md, head
        test_table = md.split("### The brief's test")[1].split("\n\n")[2].splitlines()
        assert len(test_table) == 2 + 2 * len(OT.ROUND2)                     # two populations
        assert all(line.count("|") == 10 for line in test_table)             # nine cells on every row
        assert "| subset | A2 vs A | 6 → 1 | 0 → 0 | 6 → 1 | 0 → 1 |" in md
        assert "The narrower one is fussiness limited to food." in md        # the slip's reason, in full
        # in the whole summary, after the arms section
        summary = OT.analyse(ps, r2[1], models=models, reference=OT.OPUS, n_boot=20)
        summary["arms"] = OT.analyse_arms(ps, r2, models=models, reference=OT.OPUS)
        summary["round2"] = out
        summary["subset"] = {"counts": counts}
        full = OT.summary_markdown(summary, ps, corpus())
        assert full.index("## The arms experiment") < full.index("## Round 2:")
        assert "### Arm D2: overlap_relation_implies" in full and "D2 maps same 4" in full


# =========================================================================== round 3 of the arms experiment
# (coding_plan_overlap_arms.md, "Round 3", 2026-10-06): rubric A version 6 one pair per call; the comparison with
# version 4 and A2

RUBRIC_A_FILE = REPO / "reports" / "trait_gap_generation" / "rubrics" / "overlap_concept.md"


def rubric_sample():
    """The rendered sample of rubric A's file (one pair per call, since draft 5): its user turn, and the object."""
    text = RUBRIC_A_FILE.read_text(encoding="utf-8")
    block = re.search(r"^## Rendered sample[^\n]*\n.*?^```\n(.*?)\n^```", text, re.S | re.M).group(1)
    return block, json.loads(block)


def single_answer(rb, value=_label_value, *, reason="About {label}.", wrap=False, **usage):
    """A responder for both forms: the single form's one object (``{"reason", <key>}``; with ``wrap``, inside a
    results list, as the list form's shape), the list form's rows; each answer by (rubric, the other trait's
    label), as :func:`arms_responder`."""
    by_text = {v["text"]: k for k, v in rb.items()}

    def responder(kw):
        r = by_text[system_text(kw)]
        obj = json.loads(user_text(kw))
        key = OT.RUBRICS[r]["key"]
        if "other" in obj:
            lab = obj["other"]["label"]
            row = {"reason": reason.format(label=lab), key: value(r, lab)}
            body = {"results": [{"id": 1, **row}]} if wrap else row
        else:
            body = {"results": [{"id": t["id"], "reason": reason.format(label=t["label"]), key: value(r, t["label"])}
                                for t in obj["traits"]]}
        return make_response(json.dumps(body), input_tokens=usage.get("input_tokens", 120),
                             output_tokens=usage.get("output_tokens", 60), cache_creation=usage.get("cache_creation", 0),
                             cache_read=usage.get("cache_read", 600))
    return responder


class TestSingleForm:
    def test_the_payload_is_the_rubric_files_sample_byte_for_byte(self):
        block, obj = rubric_sample()
        assert set(obj) == {"target", "other"} and all(set(obj[k]) == {"label", "description"} for k in obj)
        corp = {obj["target"]["label"]: obj["target"], obj["other"]["label"]: obj["other"]}
        call = OT.PairCall(call_id="nn:extroverted>gregarious", set="nearest", target=obj["target"]["label"],
                           listed=[obj["other"]["label"]], origin_call_id="nn:extroverted")
        assert OT.render_single(call, corp) == block
        assert json.loads(OT.render_single(call, corp)) == obj == OT.payload_single(call, corp)
        # and from the corpus as it stands: the run sends exactly the sample for this pair (item 27 of the marks)
        from assistant_axis.gapgen import contrast as CT
        real = CT.load_corpus_texts(REPO / "data")
        assert OT.render_single(OT.PairCall(call_id="x", set="nearest", target="extroverted", listed=["gregarious"]),
                                real) == block

    def test_labels_in_display_form_and_one_pair_only(self):
        call = OT.PairCall(call_id="x>lambda_mu", set="labelled", target="alpha", listed=["lambda_mu"])
        obj = json.loads(OT.render_single(call, corpus()))
        assert obj["other"]["label"] == "lambda mu" and obj["target"]["label"] == "alpha"
        assert OT.render_single(call, corpus()).count("\n") == 1                     # two lines
        with pytest.raises(ValueError, match="one pair per call"):
            OT.render_single(OT.Call(call_id="c", set="labelled", target="alpha", listed=["beta", "gamma"]), corpus())

    def test_forms(self):
        assert [OT.rubric_form("A", v) for v in (2, 4, 5, 6, None)] == ["list", "list", "single", "single", "list"]
        assert all(OT.rubric_form(r, 9) == "list" for r in ("B", "C", "D", "E", "A2", "C2", "D2", "E2"))
        assert "single_from_version" not in OT.RUBRICS["A2"]
        rb = OT.load_rubrics(keys=("A", "B", "A2"))
        assert (rb["A"]["form"], rb["B"]["form"], rb["A2"]["form"]) == ("single", "list", "list")
        assert list_rubrics()["A"]["form"] == "list"
        assert OT.record_form({"rubric": "A", "rubric_version": 4}) == "list"           # written before forms
        assert OT.record_form({"rubric": "A", "rubric_version": 6}) == "single"
        assert OT.record_form({"rubric": "A", "rubric_version": 6, "form": "list"}) == "list"

    def test_single_calls_one_per_pair(self):
        ps = pair_set(n_antonyms=2, n_random=2)
        singles = OT.to_single_calls(ps.calls)
        assert sorted(c.call_id for c in singles) == sorted(p.pair_id for p in ps.pairs)
        by_id = {p.pair_id: p for p in ps.pairs}
        for c in singles:
            p = by_id[c.call_id]
            assert c.listed == [p.listed] and c.target == p.target and c.origin_call_id == p.call_id
        assert OT.to_single_calls(singles) == singles and OT.stage_calls(ps.calls, "list") == ps.calls

    def test_request_params_cache_the_rubric(self):
        rb = OT.load_rubrics()
        c = OT.PairCall(call_id="x>beta", set="labelled", target="alpha", listed=["beta"])
        for m in (OT.SONNET, OT.OPUS):
            p = OT.call_params(c, corpus(), rubric_text=rb["A"]["text"], model=m, form="single")
            assert p["system"] == [{"type": "text", "text": rb["A"]["text"], "cache_control": {"type": "ephemeral"}}]
            assert p["messages"][0]["content"] == OT.render_single(c, corpus()) and "temperature" not in p
        assert "cache_control" not in OT.call_params(c, corpus(), rubric_text="x", model=OT.OPUS, form="single",
                                                     cache_system=False)["system"][0]
        assert "cache_control" not in OT.call_params(c, corpus(), rubric_text="x", model=OT.OPUS)["system"][0]  # list
        txt = OT.rendered_prompt(c, corpus(), rubric="A", rubric_text=rb["A"]["text"], model=OT.OPUS, form="single")
        assert "single form" in txt and '"ephemeral"' in txt and '"other": {"label": "beta"' in txt


def one(value, reason="Because.", **extra):
    return json.dumps({"reason": reason, "similarity": value, **extra})


class TestSingleParse:
    def test_good_answers(self):
        for v, want in ((3, 3), ("2", 2), ("Opposite", "opposite"), ("unsure", "unsure"), (0, 0)):
            rows, errors, meta = OT.parse_answer(one(v), "A", 1, form="single")
            assert errors == {} and rows == {1: {"reason": "Because.", "value": want, "reason_first": True}}
            assert meta["notes"] == [] and not meta["wrapped"] and meta["n_rows"] == 1
        rows, _, meta = OT.parse_single("Here:\n```json\n" + one(4) + "\n```", "A")
        assert rows[1]["value"] == 4

    def test_extra_keys_and_order_are_noted(self):
        rows, errors, meta = OT.parse_single(json.dumps({"similarity": 2, "reason": "late", "label": "x"}), "A")
        assert errors == {} and rows[1]["value"] == 2 and rows[1]["reason_first"] is False
        assert meta["extra_keys"] == ["label"] and meta["notes"] == ["extra keys ['label']"]

    def test_a_wrapped_answer_is_accepted_with_a_note(self):
        text = json.dumps({"results": [{"id": 1, "reason": "Old form.", "similarity": 3}]})
        rows, errors, meta = OT.parse_single(text, "A")
        assert errors == {} and rows[1]["value"] == 3 and meta["wrapped"] and meta["extra_keys"] == ["id"]
        assert "answer wrapped in a results list" in meta["notes"]
        two = json.dumps({"results": [{"id": 1, "reason": "a", "similarity": 3}, {"id": 2, "reason": "b", "similarity": 1}]})
        rows, errors, _ = OT.parse_single(two, "A")
        assert rows == {} and errors == {1: "results holds 2 rows, not one"}

    def test_a_self_correction_uses_the_last_answer(self):
        rows, _, meta = OT.parse_single(one(2, "first") + "\n\nCorrection:\n" + one(3, "second"), "A")
        assert rows[1]["value"] == 3 and rows[1]["reason"] == "second" and meta["n_result_objects"] == 2

    def test_failures(self):
        assert OT.parse_single("", "A")[1] == {1: "empty response"}
        assert OT.parse_single(json.dumps({"similarity": 2}), "A")[1] == {1: "reason missing"}
        assert OT.parse_single(json.dumps({"reason": "x", "score": 2}), "A")[1][1].startswith("unparseable")
        assert "is not 0-4" in OT.parse_single(one(5), "A")[1][1]
        assert OT.parse_single('{"reason": "x", "opposite"}', "A")[0] == {}                 # not JSON
        assert OT.parse_single("no json here", "A")[1][1].startswith("unparseable")

    def test_records_are_reparsed_in_their_form(self):
        rec = {"rubric": "A", "rubric_version": 6, "form": "single", "listed": ["beta"], "response": {"text": one(3)}}
        assert OT.reparse(rec)[0][1]["value"] == 3
        old = {"rubric": "A", "rubric_version": 4, "listed": ["beta"],
               "response": {"text": json.dumps({"results": [{"id": 1, "reason": "r", "similarity": 1}]})}}
        assert OT.reparse(old)[0][1]["value"] == 1 and OT.record_form(old) == "list"


class TestSingleFormRunner:
    def test_one_call_per_pair_cached_identical_in_both_passes(self, tmp_path):
        rb = OT.load_rubrics(keys=("A",))
        assert rb["A"]["form"] == "single" and rb["A"]["version"] == 6
        ps = pair_set(n_antonyms=2, n_random=2)
        client = FakeAsyncAnthropic(single_answer(rb, cache_creation=0, cache_read=600))
        path = tmp_path / "r.jsonl"
        usage = MultiModelUsage()
        r = OT.OverlapRunner(client, rb, corpus(), usage=usage, responses_path=path, retry_delays=(),
                             usage_path=tmp_path / "usage.json")
        res1 = run(r.run_stage("A", OT.SONNET, ps.calls, pass_no=1))
        assert res1.n_calls == res1.n_sent == len(ps.pairs) == len(client.calls) and res1.n_ok == len(ps.pairs)
        assert all(kw["system"][0].get("cache_control") == {"type": "ephemeral"} for kw in client.calls)
        singles = {c.call_id: c for c in OT.to_single_calls(ps.calls)}
        assert sorted(user_text(kw) for kw in client.calls) == sorted(OT.render_single(c, corpus())
                                                                       for c in singles.values())
        res2 = run(r.run_stage("A", OT.SONNET, ps.calls, pass_no=2))
        assert res2.n_sent == len(ps.pairs) and len(client.calls) == 2 * len(ps.pairs)
        users = [user_text(kw) for kw in client.calls]
        assert sorted(users[:len(ps.pairs)]) == sorted(users[len(ps.pairs):])            # the identical prompts
        recs = OT.read_records(path)
        for rec in recs:
            p = next(x for x in ps.pairs if x.pair_id == rec["call_id"])
            assert rec["form"] == "single" and rec["pair_id"] == p.pair_id and rec["origin_call_id"] == p.call_id
            assert rec["listed"] == [p.listed] and rec["order_seed"] is None and rec["request"]["cache_system"]
            assert rec["request"]["user"] == OT.render_single(singles[p.pair_id], corpus())
            assert rec["rubric_version"] == 6 and rec["response"]["usage_raw"]["cache_read_input_tokens"] == 600
        keys = OT.done_keys(recs)
        assert {k[2] for k in keys} == {p.pair_id for p in ps.pairs} and {k[3] for k in keys} == {1, 2}
        for p_no in (1, 2):
            ans = OT.collect_answers(ps, recs, pass_no=p_no)[("A", OT.SONNET)]
            assert set(ans) == {p.pair_id for p in ps.pairs}
            assert all(ans[p.pair_id]["value"] == _label_value("A", corpus()[p.listed]["label"]) for p in ps.pairs)
        assert OT.first_attempt_parse(ps, recs, pass_no=2)[("A", OT.SONNET)] == {"ok": len(ps.pairs),
                                                                                "total": len(ps.pairs)}
        run(r.run_stage("A", OT.SONNET, ps.calls, pass_no=2))                           # a resume sends nothing
        assert len(client.calls) == 2 * len(ps.pairs)
        # the cache: charged at 0.1x for reads, as llm.billed_usage does, and recorded per request
        assert usage.n_calls == len(recs) == OT.usage_from_records(recs).n_calls
        assert usage.total_cost_usd == pytest.approx(OT.usage_from_records(recs).total_cost_usd)
        cs = OT.cache_stats(recs)[OT.SONNET]
        assert cs["requests"] == cs["reading"] == len(recs) and cs["writing"] == 0 and cs["hit_rate"] == 1.0
        assert cs["saved_usd"] == pytest.approx(len(recs) * 600 * 0.9 * 2.0 / 1e6, abs=1e-6)
        assert cs["charged_usd"] == pytest.approx(usage.total_cost_usd, abs=1e-6)

    def test_a_wrapped_answer_parses_and_is_counted(self, tmp_path):
        rb = OT.load_rubrics(keys=("A",))
        ps = pair_set()
        client = FakeAsyncAnthropic(single_answer(rb, wrap=True))
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=tmp_path / "r.jsonl",
                             retry_delays=())
        res = run(r.run_stage("A", OT.OPUS, ps.calls))
        assert res.n_ok == res.n_ok_first == len(ps.pairs) and len(client.calls) == len(ps.pairs)
        notes = OT.format_notes(OT.read_records(tmp_path / "r.jsonl"))[f"{OT.OPUS}|1"]
        assert notes["first"]["wrapped"] == notes["first"]["extra_keys"] == len(ps.pairs)
        assert notes["first"]["extra_key_names"] == {"id": len(ps.pairs)}

    def test_an_unparsed_answer_is_asked_again(self, tmp_path):
        rb = OT.load_rubrics(keys=("A",))
        ps = pair_set()
        seen: dict = {}
        good = single_answer(rb)

        def flaky(kw):
            seen[user_text(kw)] = seen.get(user_text(kw), 0) + 1
            return make_response('{"reason": "x", "opposite"}') if seen[user_text(kw)] == 1 else good(kw)
        client = FakeAsyncAnthropic(flaky)
        r = OT.OverlapRunner(client, rb, corpus(), usage=MultiModelUsage(), responses_path=tmp_path / "r.jsonl",
                             retry_delays=())
        res = run(r.run_stage("A", OT.SONNET, ps.calls))
        # a pair listed in two calls the same way round is the same prompt twice: one bad answer per prompt
        prompts = {OT.render_single(c, corpus()) for c in OT.to_single_calls(ps.calls)}
        assert len(prompts) < len(ps.pairs)
        assert len(client.calls) == len(ps.pairs) + len(prompts) and res.n_ok == len(ps.pairs)
        assert res.n_ok_first == len(ps.pairs) - len(prompts) and res.n_reasked == len(prompts)

    def test_the_estimate_counts_one_call_per_pair_and_the_cache(self):
        rb = OT.load_rubrics(keys=("A",))
        ps = pair_set()
        est = OT.estimate(ps.calls, corpus(), rb, [OT.SONNET, OT.OPUS], ["A"])
        assert all(x.n_calls == len(ps.pairs) and "one pair per call" in x.label for x in est.lines)
        cached = OT.cached_estimate_usd(ps.calls, corpus(), rb, [OT.SONNET, OT.OPUS], ["A"])
        assert 0 < cached < est.usd
        lst = list_rubrics(keys=("A",))
        assert OT.cached_estimate_usd(ps.calls, corpus(), lst, [OT.OPUS], ["A"]) == pytest.approx(
            OT.estimate(ps.calls, corpus(), lst, [OT.OPUS], ["A"]).usd, rel=1e-3)        # the list form is uncached


class TestRound3Statistics:
    def test_the_rule(self):
        d = OT.rule_decision
        assert [d(v, None) for v in (0, 1, 2, "opposite", 4)] == ["keep", "keep", "keep", "keep", "cut"]
        assert [d(3, o) for o in (0, 2, "opposite", 3, 4, "unsure")] == ["keep", "keep", "keep", "cut", "cut", "cut"]
        assert d("unsure", 2) == "keep" and d(3, None) is None and d(None, 2) is None
        assert OT.escalates(3) and OT.escalates("unsure") and not OT.escalates(4) and not OT.escalates("opposite")

    def test_rule_simulation_and_the_second_opinion(self):
        ids = ["p1", "p2", "p3", "p4", "p5", "p6"]
        s = {1: _ans(dict(zip(ids, [3, 3, 4, 2, 1, "opposite"]))), 2: _ans(dict(zip(ids, [3, 2, 4, 3, 1, "opposite"])))}
        o = {1: _ans(dict(zip(ids, [2, 3, 4, 3, 1, 3]))), 2: _ans(dict(zip(ids, [2, 3, 3, 3, 1, 3])))}
        stats, dec = OT.rule_simulation(ids, s, o)
        p1 = stats["per_pass"]["1"]
        assert (p1["escalated"], p1["rescued"], p1["cut"], p1["cut_direct"], p1["kept_though_second"]) == (2, 1, 2, 1, 2)
        assert (p1["n"], p1["kept"]) == (6, 4)
        p2 = stats["per_pass"]["2"]
        assert (p2["escalated"], p2["rescued"], p2["cut"], p2["kept_though_second"]) == (2, 1, 2, 2)
        assert dec[1]["p2"] == "cut" and dec[2]["p2"] == "keep" and dec[2]["p4"] == "cut"
        assert stats["flips"] == {"n": 6, "differ": 2}                                      # p2 and p4
        assert OT.decisions_against(dec, {1: dict(dec[1], p1="cut"), 2: dec[2]}) == {
            "1": {"n": 6, "differ": 1, "keep_to_cut": 1, "cut_to_keep": 0}, "2": {"n": 6, "differ": 0, "keep_to_cut": 0,
                                                                                 "cut_to_keep": 0}}
        esc = OT.second_on_escalated(ids, s, o)
        assert esc["per_pass"]["1"]["n"] == 2 and esc["per_pass"]["1"]["answers"] == {"2": 1, "3": 1}
        assert esc["per_pass"]["1"]["same"] == 2 and esc["any_pass"]["n"] == 3 and esc["any_pass"]["same"] == 3

    def test_slips_and_the_neither_implies_wording(self):
        a = [{"value": 2, "reason": "Restless is part of anxious but lacks worry."},                      # forward
             {"value": 2, "reason": "Narrower in object, but neither implies the other."},                # discounted
             {"value": 2, "reason": "Sardonic is broader; they overlap without either implying the other."},
             {"value": 2, "reason": "Each can be held without the other, though one is a special case."},
             {"value": 2, "reason": "Mercy is narrower, and a compassionate person need not be lenient."},  # one-way
             {"value": 3, "reason": "Each adds something the other lacks."},                               # reverse
             {"value": 3, "reason": "Close, though neither strictly implies the other."},                 # wide only
             {"value": 3, "reason": "The same thing, carried further."}]
        s = OT.slip_counts("A", a)
        assert (s["n_2"], s["forward"], s["forward_discounted"]) == (5, 5, 2)
        assert (s["n_3"], s["reverse"], s["reverse_wide"]) == (3, 1, 2)
        assert s["forward_discounted_share"] == pytest.approx(0.4) and s["reverse_wide_share"] == pytest.approx(0.667)
        assert OT.describes_neither_implies("NEITHER fully contains the other")
        assert not OT.describes_neither_implies("a fussy eater is fussy, though not the reverse")

    def test_marks_agreement(self):
        items = [{"item": 2, "pair_id": "a"}, {"item": 1, "pair_id": "b"}, {"item": 17, "pair_id": "c"},
                 {"item": 15, "pair_id": "d"}, {"item": 5, "pair_id": "e"}]
        m = OT.marks_agreement(_ans({"a": 2, "b": "opposite", "c": 2, "d": 2, "e": None}), items)
        # item 2: leaning 1, alternative 2; item 1 opposite; item 17 leaning 3, alternative 2; item 15 leaning 4
        assert (m["n"], m["exact"], m["leaning_or_alternative"]) == (4, 1, 3)
        assert (m["n_numeric"], m["within_one"]) == (3, 2)
        assert [x["value"] for x in m["items"]] == [2, "opposite", 2, 2, None]
        assert len(OT.ROGER_LEANINGS) == 30 and set(OT.ROGER_ALTERNATIVES) == {2, 13, 17, 21, 27}

    def test_cache_stats_prices_opus_reads_at_its_published_rate(self):
        recs = [{"model": OT.OPUS, "response": {"usage_raw": {"input_tokens": 100, "cache_creation_input_tokens": 600,
                                                              "cache_read_input_tokens": 0, "output_tokens": 50}}},
                {"model": OT.OPUS, "response": {"usage_raw": {"input_tokens": 100, "cache_creation_input_tokens": 0,
                                                              "cache_read_input_tokens": 600, "output_tokens": 50}}},
                {"model": OT.OPUS, "response": {"usage_raw": {}}}]
        c = OT.cache_stats(recs)[OT.OPUS]
        assert (c["requests"], c["reading"], c["writing"], c["hit_rate"]) == (2, 1, 1, 0.5)
        assert c["read_share"] == pytest.approx(600 / 1400, abs=1e-4)
        # input $4, output $20 per million: charged 200 + 750 + 60 = 1010 input-equivalent tokens
        assert c["charged_usd"] == pytest.approx((1010 * 4 + 100 * 20) / 1e6, abs=1e-6)
        assert c["published_usd"] == pytest.approx((980 * 4 + 100 * 20) / 1e6, abs=1e-6)
        assert c["saved_usd"] == pytest.approx((1400 - 1010) * 4 / 1e6, abs=1e-6)


def _r3_made_up():
    """A pair set and three versions: version 4 (a list run, its pass 2 reshuffled), A2 on the first call's pairs
    only, version 6 (one pair per call).  Sonnet answers 3 on the nearest pairs of rank 1, 2 elsewhere; Opus
    answers 2 on them under version 4 and 3 under version 6 (so version 6 cuts what version 4 rescued);
    version 6's Sonnet answers 2 with a containment reason on the rank-2 pairs."""
    ps = pair_set(n_targets=6, n_antonyms=2, n_random=2)
    models = [OT.SONNET, OT.OPUS]

    def answers(version, model, p):
        out = {}
        for pr in ps.pairs:
            rank1 = pr.group == OT.NEAREST and pr.nn_rank == 1
            v, why = 2, "Both are about speech."
            if pr.group == "antonym":
                v, why = "opposite", "The reverse."
            elif rank1:
                v = 3 if model == OT.SONNET else (3 if version == "v6" else 2)
                why = "Close, but each adds something." if model == OT.OPUS and version == "v4" else "Narrowed."
            elif version == "v6" and model == OT.SONNET and pr.nn_rank == 2:
                why = "The listed trait is part of the target."
            out[pr.pair_id] = {"value": v, "reason": why, "reason_first": True, "error": None}
        return out
    first_call = ps.calls[0].call_id
    a2_ids = {pr.pair_id for pr in ps.pairs if pr.call_id == first_call}
    versions = {
        "v4": {"run": "overlap_arms_1", "rubric": "A", "rubric_versions": [4], "form": "list",
               "by_pass": {p: {m: answers("v4", m, p) for m in models} for p in (1, 2)},
               "groups": OT.prompt_groups(ps, 0, 2)},
        "A2": {"run": "overlap_arms_2", "rubric": "A2", "rubric_versions": [1], "form": "list",
               "by_pass": {p: {m: {k: v for k, v in answers("v4", m, p).items() if k in a2_ids} for m in models}
                           for p in (1, 2)}, "groups": OT.prompt_groups(ps, 0, 2)},
        "v6": {"run": "overlap_arms_3", "rubric": "A", "rubric_versions": [6], "form": "single",
               "by_pass": {p: {m: answers("v6", m, p) for m in models} for p in (1, 2)}, "groups": None},
    }
    populations = {"all": [p.pair_id for p in ps.pairs], "nearest": [p.pair_id for p in ps.pairs if p.group == OT.NEAREST],
                   "round2": [p.pair_id for p in ps.pairs if p.pair_id in a2_ids]}
    items = [{"item": i + 1, "pair_id": p.pair_id} for i, p in enumerate(ps.pairs[:5])]
    marks = {"items": items, "test1": {m: answers("v4", m, 1) for m in models}}
    return ps, models, versions, populations, marks


class TestRound3Analysis:
    def test_analyse_round3(self):
        ps, models, versions, populations, marks = _r3_made_up()
        r3 = OT.analyse_round3(ps, versions, populations, models=models, reference=OT.OPUS, marks=marks)
        assert set(r3["populations"]) == {"all", "nearest", "round2"}
        assert set(r3["populations"]["all"]["versions"]) == {"v4", "v6"}                   # A2 only where it was sent
        assert set(r3["populations"]["round2"]["versions"]) == {"v4", "A2", "v6"}
        n_rank1 = sum(p.group == OT.NEAREST and p.nn_rank == 1 for p in ps.pairs)
        v4, v6 = (r3["populations"]["all"]["versions"][k] for k in ("v4", "v6"))
        assert v4["rule"]["per_pass"]["1"]["escalated"] == v6["rule"]["per_pass"]["1"]["escalated"] == n_rank1
        assert v4["rule"]["per_pass"]["1"]["rescued"] == n_rank1 and v6["rule"]["per_pass"]["1"]["rescued"] == 0
        assert r3["populations"]["all"]["rule_against_v4"]["v6"]["1"] == {"n": len(ps.pairs), "differ": n_rank1,
                                                                          "keep_to_cut": n_rank1, "cut_to_keep": 0}
        assert v6["second_on_escalated"]["per_pass"]["1"]["answers"] == {"3": n_rank1}
        assert v4["self_consistency"][OT.OPUS]["exact"] == 1.0 and not v4["self_consistency"][OT.OPUS]["identical"]["all_pairs"]
        assert v6["self_consistency"][OT.OPUS]["identical"]["all_pairs"]
        assert v4["self_consistency"][OT.OPUS]["identical"]["n"] < len(ps.pairs)
        # Sonnet and Opus cross at 3 on the rank-1 pairs under version 4 (Opus covers none)
        bm = v4["between_models"][OT.SONNET]["1"]
        assert bm["crossings"] == n_rank1 and bm["first_only"] == 0 and bm["second_only"] == n_rank1
        assert v6["between_models"][OT.SONNET]["1"]["crossings"] == 0
        n_rank2 = sum(p.group == OT.NEAREST and p.nn_rank == 2 for p in ps.pairs)
        assert v6["slips"][OT.SONNET]["pooled"]["forward"] == 2 * n_rank2 and v4["slips"][OT.SONNET]["pooled"]["forward"] == 0
        assert v4["slips"][OT.OPUS]["1"]["reverse"] == 0                                   # Opus's 2s, not 3s
        assert v4["groups"][OT.OPUS]["1"]["antonym"]["opposite"] == 1.0
        oc = r3["opus_changes"]["1"]
        assert oc["n"] == n_rank1 and oc["second_changes_side"] == n_rank1
        row = oc["pairs"][0]
        assert (row["second_base"], row["second_new"], row["decision_base"], row["decision_new"]) == (2, 3, "keep", "cut")
        assert row["second_base_reason"] == "Close, but each adds something." and row["second_new_reason"] == "Narrowed."
        assert r3["marks"]["v4_test1"][OT.OPUS]["n"] == 5 and set(r3["marks"]) >= {"v4_pass1", "v6_pass2", "items"}
        def row(prefix, who):
            return next(x for x in r3["summary"] if x["figure"].startswith(prefix) and x["model"] == who)
        kept = row("kept though Opus reads 3 or more", "rule")
        assert kept["v4"] == kept["v6"] == 0 and kept["verdict"] == "same"
        assert row("escalated to Opus", "rule")["verdict"] == "same"
        cross = row("crossings at 3 between the models", "both")
        assert (cross["v4"], cross["v6"], cross["verdict"]) == (n_rank1, 0, "better")
        like = row("self-consistency, exact, like for like", OT.SONNET)
        assert like["v4"] == like["v6"] == 1.0 and like["verdict"] == "same"
        assert row("self-consistency, exact, every pair", OT.SONNET)["verdict"] is None      # not like for like
        fwd = row("2s whose reason describes a containment", OT.SONNET)
        assert fwd["v4"] == 0 and fwd["v6"] > 0 and fwd["verdict"] == "worse"
        assert row("Roger's 30 marks: his leaning", OT.OPUS)["v4"] == r3["marks"]["v4_test1"][OT.OPUS][
            "leaning_or_alternative"]
        json.dumps(r3)

    def test_round3_tables_at_the_top(self):
        ps, models, versions, populations, marks = _r3_made_up()
        r3 = OT.analyse_round3(ps, versions, populations, models=models, reference=OT.OPUS, marks=marks)
        md = "\n".join(OT.round3_markdown(r3, corpus(), lambda m: OT.SHORT.get(m, m)))
        for head in ("## Round 3: rubric A version 6, one pair per call", "### Summary: version 4 against version 6",
                     "### Every pair: ", "### The nearest pairs: ", "### Round 2's pairs (those A2 was sent): ",
                     "### Agreement with Roger's 30 marks", "M3's rule (Sonnet 5.5 first, Opus 5.5 on the 3s)",
                     "### Where Opus 5.5's answer under version 6 changes the rule's decision against version 4",
                     "\"Close, but each adds something.\"", "identical prompts"):
            assert head in md, head
        table = md.split("### Summary: version 4 against version 6")[1].split("\n\n")[2].splitlines()
        assert len(table) == 2 + len(r3["summary"]) and all(line.count("|") == 7 for line in table)
        summary = OT.analyse(ps, {("A", m): versions["v6"]["by_pass"][1][m] for m in models}, models=models,
                             reference=OT.OPUS, n_boot=20)
        summary["round3"] = r3
        full = OT.summary_markdown(summary, ps, corpus())
        assert full.index("## Round 3:") < full.index("## Parse rates")
