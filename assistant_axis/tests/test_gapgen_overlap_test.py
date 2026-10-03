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
        assert rb["A"]["version"] == 3 and rb["B"]["version"] == 2   # A: draft 3 (answer keys), 2026-10-03
        assert rb["A"]["text"] == sr.load_prompt("overlap_concept")
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
    def test_one_call_per_target_per_stage_and_records(self, tmp_path):
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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
        rb = OT.load_rubrics()
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

    def test_estimate(self):
        rb = OT.load_rubrics()
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
