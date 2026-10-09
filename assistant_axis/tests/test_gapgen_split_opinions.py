"""The split filter's third opinion and disagreement tripwire (Roger, 2026-10-02; coding_plan_platform.md,
"M1 filter: judging model per generator").  No API call: fake live and batch clients.

``--third-model`` runs the second opinion's steps (1 to 3) on a third model for the same rows, and
the summary gains an agreement section; ``--max-disagreement`` stops a run whose first and second
models disagree too often on the final outcome, before the wave of alignment and descriptors calls.
"""
import json
import logging
from collections import Counter
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_runner as SR
from assistant_axis.gapgen.batches import BatchTransport
from assistant_axis.gapgen.filter import FilterItem
from assistant_axis.gapgen.split_runner import DisagreementStop, SplitRunner, tokens_for
from assistant_axis.judge_pricing import BATCH_SUFFIX, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text
from assistant_axis.tests.split_replay import (
    HAIKU, SONNET55, load_jsonl, make_responder, step_of_system, synthetic, test_items,
)
from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep

OPUS = "claude-opus-5-5"


def runner(client, **kw):
    kw.setdefault("model", HAIKU)   # the tests' first model (the default is Haiku 5.5 from 2026-10-08)
    kw.setdefault("wordnet", False)
    kw.setdefault("zipf_fn", lambda w: 4.0)
    kw.setdefault("retry_delays", ())
    return SplitRunner(client=client, batch_id="t", **kw)


def controlled(kinds=None, *, default="trait", tokens=(1000, 100)):
    """A responder whose every answer is synthetic (one primary reading, well known, no same-sense
    pair), with the kind call answering ``kinds[model][label]`` (``default`` otherwise): the outcome
    of each word on each model is set by the test."""
    kinds = kinds or {}

    def override(step, item, kw):
        if step == "kind":
            k = kinds.get(kw["model"], {}).get(item["label"], default)
            return json.dumps({"results": [{"id": 1, "reason": "r.", "kind": k, "membership_kind": None}]})
        return synthetic(step, item)
    return make_responder(override=override, tokens=tokens)


def words(n, prefix="word"):
    return [f"{prefix}{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(n)]


def items_of(labels_by_stratum):
    out = []
    for stratum, labels in labels_by_stratum.items():
        out += [FilterItem(key=f"{w}#1", label=w, meta={"stratum": stratum}) for w in labels]
    return out


def steps_sent(client):
    return Counter(step_of_system(system_text(kw)) for kw in client.calls)


# ---------------------------------------------------------------------------
# the third opinion
# ---------------------------------------------------------------------------

class TestThirdOpinion:
    def _run(self):
        client = FakeAsyncAnthropic(make_responder(tokens=(1000, 100)))
        usage = MultiModelUsage()
        r = runner(client, usage=usage, second_opinion=True, second_opinion_frac=0.1, third_model=OPUS)
        res = {x.key: x for x in r.run(test_items())}
        return client, r, res, usage

    def test_runs_the_second_opinions_steps_on_exactly_its_rows(self):
        client, r, res, _ = self._run()
        chosen = set(r.second_keys)
        assert chosen and r.third_keys == r.second_keys
        key_of = {x.label: x.key for x in res.values()}

        def calls_on(model):
            out = Counter()
            for kw in client.calls:
                if kw["model"] == model:
                    step = step_of_system(system_text(kw))
                    out[(step, key_of[json.loads(user_text(kw))["label"]])] += 1
            return out
        son, opus = calls_on(SONNET55), calls_on(OPUS)
        assert {k for _, k in opus} == chosen
        assert {s for s, _ in opus} <= set(split.SECOND_OPINION_STEPS)
        # the same steps, call for call, as the second opinion's own path (its gloss aside)
        assert opus == Counter({k: v for k, v in son.items() if k[0] in split.SECOND_OPINION_STEPS})
        assert {rec["stage"] for rec in r.responses if rec["model"] == OPUS} <= {
            f"third_{s}" for s in split.SECOND_OPINION_STEPS}

    def test_recorded_beside_the_second_opinion_with_agreement_flags(self):
        _, r, res, _ = self._run()
        chosen = set(r.second_keys)
        for k, x in res.items():
            f = x.filter
            assert "third_opinion" in f
            if k not in chosen:
                assert f["third_opinion"] is None
                continue
            s, t = f["second_opinion"], f["third_opinion"]
            assert t["model"] == OPUS and set(s) <= set(t)          # the second opinion's shape, plus flags
            assert t["agree"] == t["agree_first"] == (t["outcome"] == f["outcome"])
            assert t["agree_second"] == (t["outcome"] == s["outcome"])
            assert t["sense"]["readings"]

    def test_requests_charges_and_parse_rates(self, caplog):
        client, r, _, usage = self._run()
        op = [kw for kw in client.calls if kw["model"] == OPUS]
        assert op and all("temperature" not in kw and kw["max_tokens"] == 2000 for kw in op)
        assert usage.per_model[OPUS].n_calls == len(op)
        rates = r.step_parse_rates()
        assert {f"{s}:third:{OPUS}" for s in ("sense", "established", "vague", "kind")} <= set(rates)
        with caplog.at_level(logging.INFO):
            r.warn_parse_rate()
        assert f"split:sense:third:{OPUS}" in caplog.text

    def test_the_third_model_must_differ_and_needs_the_second_opinion(self):
        client = FakeAsyncAnthropic(make_responder())
        with pytest.raises(ValueError):
            runner(client, second_opinion=True, third_model=SONNET55)
        with pytest.raises(ValueError):
            runner(client, second_opinion=True, third_model=HAIKU)
        with pytest.raises(ValueError):
            runner(client, second_opinion=False, third_model=OPUS)

    def test_batches_charge_the_third_model_at_batch_rates(self, tmp_path):
        responder = make_responder(tokens=(1000, 100))
        r = runner(FakeAsyncAnthropic(responder), second_opinion=True, second_opinion_frac=0.1, third_model=OPUS)
        bc = FakeBatchClient(responder)
        r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
        res = {x.key: x for x in r.run(test_items(40))}
        assert OPUS + BATCH_SUFFIX in r.usage.per_model and OPUS not in r.usage.per_model
        assert all(res[k].filter["third_opinion"]["model"] == OPUS for k in r.second_keys)
        sent = [q for b in bc.batches.created for q in b["requests"] if q["params"]["model"] == OPUS]
        assert sent and all("-t-" in q["custom_id"] and "temperature" not in q["params"] for q in sent)


# ---------------------------------------------------------------------------
# the agreement section
# ---------------------------------------------------------------------------

def known_disagreements():
    """60 words in three strata, every one sampled.  Stratum A (30 words): the second model
    disagrees on 6, the third sides with the second on 4, with the first on 1, with neither on 1,
    and differs from both on 2 words where they agree.  B (25): one disagreement, the third with
    the second.  C (5): three disagreements, the third with the first."""
    a, b, c = words(30, "aw"), words(25, "bw"), words(5, "cw")
    son = {w: "state" for w in a[:6] + b[:1] + c[:3]}
    opus = {w: "state" for w in a[:4] + b[:1]} | {a[5]: "action"} | {w: "state" for w in a[6:8]}
    return {"A": a, "B": b, "C": c}, {SONNET55: son, OPUS: opus}


class TestAgreement:
    def test_section_on_a_synthetic_run(self):
        strata, kinds = known_disagreements()
        client = FakeAsyncAnthropic(controlled(kinds))
        r = runner(client, second_opinion=True, second_opinion_frac=1.0, third_model=OPUS, max_disagreement=1.0)
        r.run(items_of(strata))
        sec = r.agreement()
        assert sec["models"] == {"first": HAIKU, "second": SONNET55, "third": OPUS}
        assert sec["source_field"] == "stratum"
        o = sec["overall"]
        assert o["n"] == 60
        assert (o["first_vs_second"]["agree"], o["first_vs_second"]["n"]) == (50, 60)
        assert (o["first_vs_third"]["agree"], o["second_vs_third"]["agree"]) == (52, 53)
        d = o["first_second_disagreements"]
        assert (d["n"], d["third_sides_with_second"], d["third_sides_with_first"], d["third_sides_with_neither"]) == \
            (10, 5, 4, 1)
        assert d["labels"]["neither"] == [strata["A"][5]]
        assert o["first_second_agree_third_differs"]["n"] == 2
        assert sorted(o["first_second_agree_third_differs"]["labels"]) == sorted(strata["A"][6:8])
        by = sec["by_source"]
        assert set(by) == {"A", "B", "C"}
        assert [by["A"][p]["agree"] for p in ("first_vs_second", "first_vs_third", "second_vs_third")] == [24, 23, 26]
        assert [by["B"][p]["agree"] for p in ("first_vs_second", "first_vs_third", "second_vs_third")] == [24, 24, 25]
        assert [by["C"][p]["agree"] for p in ("first_vs_second", "first_vs_third", "second_vs_third")] == [2, 5, 2]
        assert by["A"]["first_vs_second"]["rate"] == pytest.approx(0.8)
        # the rows' own flags say the same
        res = r.results
        for w in strata["A"][:4]:
            t = res[f"{w}#1"].filter["third_opinion"]
            assert t["outcome"] == "states" and t["agree_first"] is False and t["agree_second"] is True

    def test_registry_rows_are_grouped_by_generator(self):
        from assistant_axis.gapgen.filter import items_from_records
        from assistant_axis.gapgen.registry import new_record
        recs = [new_record("tidy", sources=[{"generator": "wordnet_walk", "run_id": "r1"}]),
                new_record("brisk", sources=[{"generator": "wordnet_walk", "run_id": "r1"},
                                             {"generator": "censuses", "run_id": "r2"}])]
        its = items_from_records(recs)
        assert its[0].meta["generators"] == ["wordnet_walk"]
        assert its[1].meta["generators"] == ["censuses", "wordnet_walk"]
        assert split.opinion_source({"generators": ["censuses", "wordnet_walk"]}) == \
            ("generator", ["censuses", "wordnet_walk"])
        assert split.opinion_source({"stratum": "existing", "generators": ["x"]}) == ("stratum", ["existing"])
        assert split.opinion_source({}) == (None, [])


# ---------------------------------------------------------------------------
# the tripwire: the rule
# ---------------------------------------------------------------------------

def rows(n, d, group="A", field="stratum"):
    return [{"label": f"{group}{i}", "source_field": field, "groups": [group], "first": "trait",
             "second": "states" if i < d else "trait", "third": None, "third_run": False} for i in range(n)]


class TestTripwireRule:
    def test_trips_above_the_threshold_and_not_at_or_below(self):
        tw = split.disagreement_tripwire(rows(20, 3), threshold=0.10)
        assert tw["tripped"] and tw["tripped_by"] == ["overall", "stratum:A"]
        assert tw["overall"] == {"n": 20, "disagree": 3, "rate": 0.15, "eligible": True, "over": True, "n_failed": 0}
        assert not split.disagreement_tripwire(rows(20, 2), threshold=0.10)["tripped"]      # 10% is not over 10%
        assert not split.disagreement_tripwire(rows(40, 1), threshold=0.10)["tripped"]

    def test_a_source_under_20_sampled_rows_is_reported_but_never_trips(self):
        tw = split.disagreement_tripwire(rows(19, 19, "S") + rows(171, 0, "L"), threshold=0.10)
        s = tw["by_source"]["S"]
        assert (s["n"], s["disagree"], s["eligible"], s["over"]) == (19, 19, False, False)
        assert tw["overall"]["rate"] == 0.1 and not tw["tripped"]
        # the overall rate needs 20 rows too
        assert not split.disagreement_tripwire(rows(19, 19), threshold=0.10)["tripped"]

    def test_a_source_of_20_or_more_trips_alone(self):
        tw = split.disagreement_tripwire(rows(20, 5, "S") + rows(200, 0, "L"), threshold=0.10)
        assert tw["tripped"] and tw["tripped_by"] == ["stratum:S"] and not tw["overall"]["over"]

    def test_max_disagreement_1_never_trips(self):
        assert not split.disagreement_tripwire(rows(50, 50), threshold=1.0)["tripped"]

    def test_failed_second_opinions_are_left_out(self):
        rs = rows(25, 0)
        for x in rs[:10]:
            x["second"] = None
        tw = split.disagreement_tripwire(rs, threshold=0.10)
        assert tw["overall"]["n"] == 15 and tw["overall"]["n_failed"] == 10 and not tw["overall"]["eligible"]

    def test_generators_each_count_a_row_found_by_both(self):
        rs = rows(20, 4, "g1", field="generator")
        for x in rs:
            x["groups"] = ["g1", "g2"]
        tw = split.disagreement_tripwire(rs, threshold=0.10)
        assert tw["source_field"] == "generator"
        assert tw["by_source"]["g1"]["n"] == tw["by_source"]["g2"]["n"] == 20
        assert tw["tripped_by"] == ["overall", "generator:g1", "generator:g2"]


# ---------------------------------------------------------------------------
# the tripwire in a run
# ---------------------------------------------------------------------------

def tripping_run():
    """25 words in stratum A, all traits on the first model; the second model calls 5 of them states
    (20% disagreement)."""
    labels = words(25)
    return items_of({"A": labels}), {SONNET55: {w: "state" for w in labels[:5]}}


class TestTripwireLive:
    def test_stops_before_the_last_wave_keeping_every_answer(self, caplog):
        items, kinds = tripping_run()
        client = FakeAsyncAnthropic(controlled(kinds))
        r = runner(client, second_opinion=True, second_opinion_frac=1.0, stop_on_disagreement=True)
        with caplog.at_level(logging.INFO), pytest.raises(DisagreementStop) as ei:
            r.run(items)
        tw = r.tripwire
        assert ei.value.tripwire is tw
        assert tw["tripped"] and tw["action"] == "stopped" and tw["stopped_before"] == "w6_last_step"
        assert tw["calls_not_sent"] == 2 * 25 and tw["accepted"] is False
        assert tw["overall"]["disagree"] == 5 and tw["by_source"]["A"]["rate"] == 0.2
        sent = steps_sent(client)
        assert sent["alignment"] == sent["descriptors"] == 0       # the further wave was not sent
        assert sent["gloss"] == 25 and sent["kind"] == 50           # the waves before it were
        assert len(r.responses) == len(client.calls)                # every answer paid for is on record
        assert {x.stage for x in r.results.values()} == {"pending"}
        assert all(x.meta["split_partial"]["so_join"]["outcome"] for x in r.results.values())
        loud = [m for m in caplog.messages if "*** HIGH DISAGREEMENT ***" in m]
        assert loud and any("stratum A" in m and "5/25" in m and "20.0%" in m and "10.0%" in m for m in loud)

    def test_resume_stops_again_without_the_override_and_goes_on_with_it(self):
        items, kinds = tripping_run()
        r1 = runner(FakeAsyncAnthropic(controlled(kinds)), second_opinion=True, second_opinion_frac=1.0,
                    stop_on_disagreement=True)
        with pytest.raises(DisagreementStop):
            r1.run(items)
        again = FakeAsyncAnthropic(controlled(kinds))
        r2 = runner(again, second_opinion=True, second_opinion_frac=1.0, resume_records=list(r1.responses),
                    stop_on_disagreement=True)
        with pytest.raises(DisagreementStop):
            r2.run(items)
        assert again.calls == []                                    # nothing paid for twice
        client = FakeAsyncAnthropic(controlled(kinds))
        r3 = runner(client, second_opinion=True, second_opinion_frac=1.0, resume_records=list(r1.responses),
                    accept_disagreement=True, stop_on_disagreement=True)
        res = r3.run(items)
        assert all(x.stage == "classified" for x in res)
        assert set(steps_sent(client)) == {"alignment", "descriptors"}   # only the wave that was held back
        assert r3.tripwire["tripped"] and r3.tripwire["accepted"] and r3.tripwire["action"] == "accepted"

    def test_trips_at_the_end_when_nothing_is_left_to_send(self):
        labels = words(25)
        kinds = {HAIKU: {w: "state" for w in labels}}              # no trait: no gloss, nothing in wave 6
        client = FakeAsyncAnthropic(controlled(kinds))
        r = runner(client, second_opinion=True, second_opinion_frac=1.0, stop_on_disagreement=True)
        res = r.run(items_of({"A": labels}))
        assert all(x.stage == "classified" for x in res)
        assert r.tripwire["tripped"] and r.tripwire["action"] == "marked" and r.tripwire["stopped_before"] is None

    def test_by_default_a_trip_is_a_warning_and_the_run_goes_on(self, caplog):
        """Roger, 2026-10-09: the tripwire warns and the run finishes (action "warned"); nothing is held back."""
        items, kinds = tripping_run()
        client = FakeAsyncAnthropic(controlled(kinds))
        r = runner(client, second_opinion=True, second_opinion_frac=1.0)
        with caplog.at_level(logging.INFO):
            res = r.run(items)
        assert all(x.stage == "classified" for x in res)
        assert r.tripwire["tripped"] and r.tripwire["action"] == "warned" and r.tripwire["stopped_before"] is None
        assert steps_sent(client)["alignment"] == 25                  # wave 6 was sent
        assert any("a warning, not a stop" in m for m in caplog.messages)

    def test_below_the_threshold_and_disabled(self):
        labels = words(25)
        kinds = {SONNET55: {labels[0]: "state", labels[1]: "state"}}   # 8%
        r = runner(FakeAsyncAnthropic(controlled(kinds)), second_opinion=True, second_opinion_frac=1.0)
        assert all(x.stage == "classified" for x in r.run(items_of({"A": labels})))
        assert r.tripwire["tripped"] is False and r.tripwire["action"] is None
        items, kinds = tripping_run()
        r = runner(FakeAsyncAnthropic(controlled(kinds)), second_opinion=True, second_opinion_frac=1.0,
                   max_disagreement=1.0)
        assert all(x.stage == "classified" for x in r.run(items))
        assert r.tripwire["tripped"] is False
        r = runner(FakeAsyncAnthropic(controlled(kinds)), second_opinion=False)
        r.run(items)
        assert r.tripwire is None


class TestTripwireBatches:
    def _make(self, tmp_path, kinds, **kw):
        responder = controlled(kinds)
        r = runner(FakeAsyncAnthropic(responder), second_opinion=True, second_opinion_frac=1.0, **kw)
        bc = FakeBatchClient(responder)
        r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
        return r, bc

    def test_stops_before_the_last_wave_and_resumes_with_the_override(self, tmp_path):
        items, kinds = tripping_run()
        r1, bc1 = self._make(tmp_path, kinds, stop_on_disagreement=True)
        with pytest.raises(DisagreementStop):
            r1.run(items)
        waves = json.loads((tmp_path / "batches.json").read_text())["waves"]
        assert list(waves) == ["w1_sense", "w2_checks", "w4_gloss", "w5_opinion_checks"]
        assert r1.tripwire["action"] == "stopped" and r1.usage.n_calls == len(r1.responses)
        r2, bc2 = self._make(tmp_path, kinds, resume_records=list(r1.responses), accept_disagreement=True,
                             stop_on_disagreement=True)
        res = r2.run(items)
        assert all(x.stage == "classified" for x in res)
        new = [q for b in bc2.batches.created for q in b["requests"]]
        assert {q["custom_id"].split("-")[0] for q in new} == {"alignment", "descriptors"}
        waves = json.loads((tmp_path / "batches.json").read_text())["waves"]
        assert list(waves)[-1] == "w6_last_step"


# ---------------------------------------------------------------------------
# the estimate
# ---------------------------------------------------------------------------

class TestEstimate:
    def _args(self, **kw):
        base = dict(model=HAIKU, second_model=SONNET55, compare_model=SONNET55, no_probe=False,
                    no_plain_reading=False, no_second_opinion=False, third_model=None)
        return SimpleNamespace(**{**base, **kw})

    def test_the_third_model_is_in_the_estimate(self, monkeypatch):
        from assistant_axis.gapgen import freq
        from data_analysis.gap_generation import split_cli
        monkeypatch.setattr(freq, "_ZIPF_FN", lambda w: 4.0)
        its = test_items(40)
        est0, plan0 = split_cli.build_split_estimate(its, self._args(), "live")
        est3, plan3 = split_cli.build_split_estimate(its, self._args(third_model=OPUS), "live")
        third = [x for x in est3.lines if x.model == OPUS]
        assert [x.label for x in third] == [f"third opinion: {s}" for s in
                                            ("sense", "established", "vague", "kind", "same sense")]
        assert est3.usd == pytest.approx(est0.usd + sum(x.usd for x in third))
        assert plan3["third_model"] == OPUS and plan0["third_model"] is None
        n_so = plan3["n_second_opinion_est"]
        assert third[0].n_calls == n_so and (third[0].in_tok, third[0].out_tok) == tokens_for("sense", OPUS)
        estb, _ = split_cli.build_split_estimate(its, self._args(third_model=OPUS), "batches")
        assert {x.model for x in estb.lines if "third" in x.label} == {OPUS + BATCH_SUFFIX}

    def test_opus_tokens_follow_the_audit(self):
        # opus_audit_m1.md: $8.98 against $6.06 estimated at Haiku's token counts
        i, o = tokens_for("sense", HAIKU)
        assert tokens_for("sense", OPUS) == (round(1.5 * i), round(1.5 * o))
        assert tokens_for("sense", OPUS, first_model=OPUS) == tokens_for("sense", OPUS)


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------

@pytest.fixture
def cli(monkeypatch, tmp_path):
    import anthropic
    import dotenv
    from data_analysis.gap_generation import traithood_filter
    holder = {"kinds": {}}

    def responder(kw):
        return controlled(holder["kinds"])(kw)

    def async_factory(**kw):
        holder["live"] = FakeAsyncAnthropic(responder)
        return holder["live"]

    def sync_factory(**kw):
        # ended at the first poll: the CLI's transport waits its real 30 s between polls
        holder["batch"] = FakeBatchClient(responder, polls=0)
        return holder["batch"]
    monkeypatch.setattr(anthropic, "AsyncAnthropic", async_factory)
    monkeypatch.setattr(anthropic, "Anthropic", sync_factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(traithood_filter, "platform_dirty_files", lambda *a, **k: [])
    from assistant_axis.gapgen import freq
    monkeypatch.setattr(freq, "_ZIPF_FN", lambda w: 4.0)           # every word past the floor, none probed
    labels = words(30)
    val = tmp_path / "words.jsonl"
    val.write_text("".join(json.dumps({"surface": w, "stratum": "A"}) + "\n" for w in labels))
    holder.update(val=val, out=tmp_path / "cand", labels=labels)
    holder["out"].mkdir()
    return holder


def _args(h, *extra):
    return ["--batch-id", "p", "--validation-file", str(h["val"]), "--out-root", str(h["out"]), "--budget-usd", "5",
            "--second-opinion-frac", "1", *extra]


def _read(h):
    d = h["out"] / "filter" / "p"
    s = json.loads((d / "summary.json").read_text())["result"]
    run = json.loads((d / "run.json").read_text())
    res = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
    return s, run, res


class TestCLI:
    def test_third_model_recorded_and_summarised(self, cli):
        from data_analysis.gap_generation import traithood_filter
        cli["kinds"] = {OPUS: {w: "state" for w in cli["labels"][:3]}}
        assert traithood_filter.main(_args(cli, "--transport", "live", "--third-model", OPUS)) == 0
        s, run, res = _read(cli)
        assert run["third_model"] == OPUS and run["max_disagreement"] == 0.10
        assert run["accept_disagreement"] is False
        assert run["third_opinion"]["model"] == OPUS
        assert set(run["third_opinion"]["step_versions"]) == set(split.SECOND_OPINION_STEPS)
        assert any("third opinion: sense" in x for x in run["estimate_lines"])
        a = s["agreement"]
        assert a["overall"]["first_vs_third"] == {"n": 30, "agree": 27, "disagree": 3, "rate": 0.9}
        assert a["by_source"]["A"]["second_vs_third"]["agree"] == 27
        assert s["tripwire"]["tripped"] is False and s["stopped_by_disagreement"] is False
        assert all(r["filter"]["third_opinion"]["model"] == OPUS for r in res)
        usage = json.loads((cli["out"] / "filter" / "p" / "usage.json").read_text())
        assert usage["per_model"][OPUS]["n_calls"] == sum(1 for kw in cli["live"].calls if kw["model"] == OPUS)
        assert any(k.endswith(f"@{OPUS}") and k.startswith("third_") for k in s["split"]["cost_by_step"])
        assert all(v["ok"] == v["n"] for k, v in s["split"]["step_parse_rates"].items() if ":third:" in k)

    def test_dry_run_prints_the_third_opinion_estimate(self, cli, capsys):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--dry-run", "--third-model", OPUS)) == 0
        out = capsys.readouterr().out
        assert "third opinion: sense: 30 x" in out and f"{OPUS} rates" in out

    # the third model may be neither the first (the CLI's default, Haiku 5.5 from 2026-10-08) nor the second
    @pytest.mark.parametrize("extra", [("--third-model", OPUS, "--no-second-opinion"),
                                       ("--third-model", SR.DEFAULT_MODEL), ("--third-model", SONNET55),
                                       ("--third-model", HAIKU, "--model", HAIKU),
                                       ("--max-disagreement", "10"), ("--max-disagreement", "-0.1")])
    def test_refusals(self, cli, extra):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, *extra)) == 2
        assert not (cli["out"] / "filter" / "p").exists()

    def test_single_pipeline_refuses_the_new_flags(self, cli):
        from data_analysis.gap_generation import traithood_filter
        for extra in (("--third-model", OPUS), ("--max-disagreement", "0.2"), ("--accept-disagreement",)):
            with pytest.raises(SystemExit):
                traithood_filter.main(_args(cli, "--pipeline", "single", *extra))

    @pytest.mark.parametrize("transport", ["live", "batches"])
    def test_a_trip_stops_the_run_and_resume_with_the_override_finishes_it(self, cli, transport, capsys):
        from data_analysis.gap_generation import traithood_filter
        cli["kinds"] = {SONNET55: {w: "state" for w in cli["labels"]}}
        assert traithood_filter.main(_args(cli, "--transport", transport, "--stop-on-disagreement")) == 3
        s, run, res = _read(cli)
        assert s["stopped_by_disagreement"] is True and run["stopped_by_disagreement"] is True
        assert s["tripwire"]["action"] == "stopped" and run["tripwire"]["tripped_by"] == ["overall", "stratum:A"]
        assert {r["stage"] for r in res} == {"pending"}
        assert "--accept-disagreement" in capsys.readouterr().err
        assert traithood_filter.main(_args(cli, "--transport", transport, "--resume",
                                           "--stop-on-disagreement")) == 3   # stops again
        assert traithood_filter.main(_args(cli, "--transport", transport, "--resume", "--stop-on-disagreement",
                                           "--accept-disagreement")) == 0
        s, run, res = _read(cli)
        assert {r["stage"] for r in res} == {"classified"}
        assert run["accept_disagreement"] is True and run["tripwire"]["action"] == "accepted"
        assert s["stopped_by_disagreement"] is False and s["tripwire"]["tripped"] is True
        assert [e["stopped_by_disagreement"] for e in run["earlier_sessions"]] == [True, True]

    def test_a_trip_at_the_end_finishes_marked_and_exits_non_zero(self, cli):
        from data_analysis.gap_generation import traithood_filter
        # the first model (the CLI's default) says state, so nothing is left after the opinions
        cli["kinds"] = {SR.DEFAULT_MODEL: {w: "state" for w in cli["labels"]}}
        assert traithood_filter.main(_args(cli, "--transport", "live", "--stop-on-disagreement")) == 3
        s, run, res = _read(cli)
        assert {r["stage"] for r in res} == {"classified"}
        assert s["tripwire"]["tripped"] and s["tripwire"]["action"] == "marked"
        assert s["stopped_by_disagreement"] is False and run["tripwire"]["action"] == "marked"

    @pytest.mark.parametrize("transport", ["live", "batches"])
    def test_by_default_a_trip_warns_and_the_run_finishes(self, cli, transport, capsys):
        """Roger, 2026-10-09: a trip is a warning, not a stop; exit 0, every row classified, recorded as warned."""
        from data_analysis.gap_generation import traithood_filter
        cli["kinds"] = {SONNET55: {w: "state" for w in cli["labels"]}}
        assert traithood_filter.main(_args(cli, "--transport", transport)) == 0
        s, run, res = _read(cli)
        assert {r["stage"] for r in res} == {"classified"}
        assert s["tripwire"]["tripped"] and s["tripwire"]["action"] == "warned" and s["stopped_by_disagreement"] is False
        assert run["stop_on_disagreement"] is False and run["tripwire"]["action"] == "warned"
        assert "WARNING (tripwire)" in capsys.readouterr().err

    def test_max_disagreement_1_never_trips(self, cli):
        from data_analysis.gap_generation import traithood_filter
        cli["kinds"] = {SONNET55: {w: "state" for w in cli["labels"]}}
        assert traithood_filter.main(_args(cli, "--transport", "live", "--max-disagreement", "1")) == 0
        s, run, _ = _read(cli)
        assert s["tripwire"]["tripped"] is False and run["max_disagreement"] == 1.0
        assert s["agreement"]["overall"]["first_vs_second"]["agree"] == 0
