"""gapgen.filter with a fake Anthropic client: stages, retries, probe, second
opinion, parse-rate alarm, summary."""
import json
import logging
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen.filter import (
    FilterItem, FilterResult, FilterRunner, holding_for, run_traithood_filter, select_second_opinion,
    summarize,
)
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

ZIPF = {"rare": 1.2, "unusual": 2.2}  # below / inside the probe band (floor 1.5)


def zipf(w):
    return ZIPF.get(w, 4.0)


class FakeWN:
    def synsets(self, form):
        return [SimpleNamespace(pos="a")] * (3 if form == "cool" else 1)


SPEC = {  # label -> fields overriding a default trait row
    "tall": {"verdict": "tagged", "tags": ["physical"], "region": "physical"},
    "plumber": {"verdict": "tagged", "tags": ["role_person"], "region": "social_interpersonal",
                "gloss": "A plumber is someone who " + "fixes pipes " * 8},
    "flurbish": {"verdict": "reject", "tags": ["not_a_word"], "region": None, "gloss": None},
    # rubric v3: polysemy comes from the notes; cool has two equally obvious trait senses
    "cool": {"person_senses": [{"sense": "calm", "kind": "trait"}, {"sense": "fashionable", "kind": "trait"}],
             "trait_senses_equally_obvious": True},
    "shaky": {"confidence": 0.4},
    "nice": {},
}


def trait_row(i, label, model=None):
    row = {"id": i, "label": label, "reason": f"{label} is a habit.",
           "person_senses": [{"sense": label, "kind": "trait"}], "trait_senses_equally_obvious": False, "enactable_in_text": 2, "verdict": "trait", "tags": [],
           "region": "social_interpersonal", "alignment_relevant": False,
           "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}
    row.update(SPEC.get(label, {}))
    return row


def items_of(kw):
    return [json.loads(x) for x in user_text(kw).splitlines()[1:]]


def responder_factory(*, fail_labels=(), garbage_first=False, known=True, second_verdict=None):
    state = {"n": 0}

    def responder(kw):
        state["n"] += 1
        its = items_of(kw)
        if "real English word" in system_text(kw):  # definition probe
            return json.dumps({"results": [{"id": it["id"], "reason": "checked", "definition": "d",
                                            "known": known} for it in its]})
        if garbage_first and len(its) > 1 and state["n"] == 1:
            return "Sorry, here is some prose and no JSON."
        rows = []
        for it in its:
            if it["label"] in fail_labels:
                continue
            r = trait_row(it["id"], it["label"])
            if kw["model"] == SONNET and second_verdict:
                r["verdict"] = second_verdict
                if second_verdict == "reject":
                    r.update(tags=["not_a_word"], region=None, gloss=None)
            rows.append(r)
        return json.dumps({"results": rows})

    return responder


def make_runner(client, **kw):
    base = dict(client=client, batch_id="b1", model=HAIKU, second_model=SONNET, usage=MultiModelUsage(),
                batch_size=3, zipf_fn=zipf, wordnet=FakeWN(), retry_delays=(0,))
    base.update(kw)
    return FilterRunner(**base)


def its(*labels):
    return [FilterItem(key=f"{l}#1", label=l) for l in labels]


class TestPipeline:
    def test_stages_and_blocks(self):
        client = FakeAsyncAnthropic(responder_factory())
        r = make_runner(client, second_opinion=False)
        out = r.run(its("stubborn", "rare", "unusual", "tall", "plumber", "flurbish", "cool"))
        by = {x.key: x for x in out}
        assert by["rare#1"].stage == "hard_reject" and by["rare#1"].filter["tags"] == ["too_rare"]
        assert by["rare#1"].filter["model"] is None
        f = by["stubborn#1"].filter
        assert by["stubborn#1"].stage == "classified" and f["verdict"] == "trait" and f["model"] == HAIKU
        assert f["rubric_version"] == 3 and f["batch_id"] == "b1" and f["gloss_in_band"] is True
        assert list(f)[:5] == ["rubric_version", "model", "batch_id", "reason", "verdict"]
        assert by["stubborn#1"].gloss.startswith("This means")
        assert (by["tall#1"].holding, by["tall#1"].entity_type) == ("physical", "trait")
        assert (by["plumber#1"].holding, by["plumber#1"].entity_type) == ("roles", "role")
        assert by["flurbish#1"].filter["verdict"] == "reject" and by["flurbish#1"].holding is None
        assert by["cool#1"].filter["polysemy"] is True and by["stubborn#1"].filter["polysemy"] is False
        assert by["unusual#1"].freq["define_probe"]["known"] is True
        assert by["stubborn#1"].freq["define_probe"] is None
        # the hard reject made no call; 6 LLM rows at batch size 3 -> 2 classify calls + 1 probe call
        stages = [x["stage"] for x in r.responses]
        assert stages.count("classify") == 2 and stages.count("probe") == 1
        assert r.usage.n_calls == 3
        assert all("rare" not in x["user"].split('"label": "')[1:] for x in r.responses)

    def test_shuffle_mixes_batches_but_keeps_results(self):
        labels = [f"w{i:02d}" for i in range(9)]
        client = FakeAsyncAnthropic(responder_factory())
        r = make_runner(client, second_opinion=False, probe=False, shuffle_seed=0)
        out = r.run(its(*labels))
        assert [x.key for x in out] == [f"{l}#1" for l in labels]
        assert all(x.stage == "classified" for x in out)
        sent = [it["label"] for c in client.calls for it in items_of(c)]
        assert sorted(sent) == labels and sent != labels

    def test_intended_sense_shown(self):
        client = FakeAsyncAnthropic(responder_factory())
        r = make_runner(client, second_opinion=False, probe=False)
        r.run([FilterItem(key="flustered#1", label="flustered", intended_sense="disposition to be flustered")])
        assert items_of(client.calls[0])[0]["intended_sense"] == "disposition to be flustered"

    def test_probe_unknown_rejects(self):
        client = FakeAsyncAnthropic(responder_factory(known=False))
        out = make_runner(client, second_opinion=False).run(its("unusual"))
        f = out[0].filter
        assert f["verdict"] == "reject" and f["classifier_verdict"] == "trait" and "too_rare" in f["tags"]

    def test_familiarity_override_goes_to_probe(self):
        client = FakeAsyncAnthropic(responder_factory())
        out = make_runner(client, second_opinion=False).run(
            [FilterItem(key="rare#1", label="rare", familiarity=0.8)])
        assert out[0].stage == "classified" and out[0].freq["familiarity_override"] is True
        assert out[0].freq["define_probe"]["known"] is True

    def test_unparseable_batch_split_once(self):
        client = FakeAsyncAnthropic(responder_factory(garbage_first=True))
        r = make_runner(client, second_opinion=False, probe=False)
        out = r.run(its("a1", "a2", "a3"))
        assert all(x.stage == "classified" for x in out)
        assert r.stats["split_retries"] == 1
        assert [x["stage"] for x in r.responses] == ["classify", "classify_split", "classify_split"]
        assert r.usage.n_calls == 3  # the unparseable response is charged too

    def test_failed_rows_retried_then_failed(self):
        client = FakeAsyncAnthropic(responder_factory(fail_labels={"bad"}))
        r = make_runner(client, second_opinion=False, probe=False)
        out = r.run(its("good", "bad"))
        by = {x.key: x for x in out}
        assert by["good#1"].stage == "classified"
        assert by["bad#1"].stage == "failed" and by["bad#1"].filter is None and by["bad#1"].error == "missing"
        assert [x["stage"] for x in r.responses] == ["classify", "classify_retry"]

    def test_high_fail_rate_logged(self, caplog):
        labels = [f"w{i}" for i in range(98)] + ["bad1", "bad2"]
        client = FakeAsyncAnthropic(responder_factory(fail_labels={"bad1", "bad2"}))
        with caplog.at_level(logging.INFO):
            run_traithood_filter(its(*labels), client=client, model=HAIKU, second_model=None, batch_size=25,
                                 zipf_fn=zipf, wordnet=FakeWN(), probe=False, second_opinion=False,
                                 retry_delays=(0,))
        assert "*** HIGH FAIL RATE ***" in caplog.text
        assert "98/100" in caplog.text

    def test_all_ok_no_alarm(self, caplog):
        client = FakeAsyncAnthropic(responder_factory())
        with caplog.at_level(logging.INFO):
            run_traithood_filter(its("a", "b"), client=client, model=HAIKU, second_model=None, zipf_fn=zipf,
                                 wordnet=FakeWN(), probe=False, second_opinion=False)
        assert "HIGH FAIL RATE" not in caplog.text and "2/2 OK" in caplog.text

    def test_second_opinion(self):
        client = FakeAsyncAnthropic(responder_factory(second_verdict="reject"))
        r = make_runner(client, probe=False, second_opinion_frac=0.0)
        out = r.run(its("stubborn", "shaky", "nice"))
        by = {x.key: x for x in out}
        # confidence < 0.6 and the evaluative-prior word get a second opinion; stubborn does not
        assert by["stubborn#1"].filter["second_opinion"] is None
        for k in ("shaky#1", "nice#1"):
            so = by[k].filter["second_opinion"]
            assert so["model"] == SONNET and so["verdict"] == "reject" and so["agree"] is False
            assert by[k].filter["verdict"] == "trait"  # Haiku's verdict stands
        assert r.stats["disagreements"] == 2
        assert all(c["model"] == SONNET for c in client.calls[1:])

    def test_summary(self):
        client = FakeAsyncAnthropic(responder_factory(fail_labels={"bad"}))
        items = [FilterItem(key=f"{l}#1", label=l, meta={"stratum": s}) for l, s in
                 [("stubborn", "existing"), ("cool", "existing"), ("tall", "oewn"), ("rare", "oewn"),
                  ("bad", "oewn")]]
        r = make_runner(client, second_opinion=False, probe=False)
        res = r.run(items)
        s = summarize(res, stats=r.stats, usage=r.usage, stratum_key="stratum")
        assert s["n"] == 5 and s["n_failed"] == 1 and s["n_hard_reject"] == 1
        assert s["verdict_counts"] == {"reject": 1, "tagged": 1, "trait": 2}
        assert s["parse_rate"] == 0.75 and s["n_llm"] == 4
        assert s["polysemy_rate"] == pytest.approx(1 / 3, abs=1e-3)
        assert s["n_useful"] == 1 and s["cost_usd"] > 0 and s["cost_per_candidate_usd"] > 0
        assert s["by_stratum"]["existing"]["verdict_fractions"] == {"trait": 1.0}
        assert s["by_stratum"]["oewn"]["tag_counts"] == {"physical": 1, "too_rare": 1}


class TestRules:
    def _res(self, key, conf=0.9, verdict="trait", label=None, found=True):
        return FilterResult(key=key, label=label or key.split("#")[0], stage="classified", freq={},
                            wordnet={"found": found}, filter={"verdict": verdict, "confidence": conf})

    def test_select_second_opinion(self):
        rs = [self._res(f"w{i}#1") for i in range(20)]
        rs.append(self._res("low#1", conf=0.5))
        rs.append(self._res("nice#1"))
        rs.append(self._res("zzq#1", found=False))
        rs.append(self._res("zzr#1", found=False, verdict="reject"))
        rs.append(FilterResult(key="hard#1", label="hard", stage="hard_reject", freq={}, wordnet={},
                               filter={"verdict": "reject", "confidence": 1.0}))
        keys = select_second_opinion(rs, frac=0.0)
        assert keys == ["low#1", "nice#1", "zzq#1"]
        k1 = select_second_opinion(rs, frac=0.1, seed=0)
        assert len(set(k1) - set(keys)) <= 3 and set(keys) <= set(k1)
        assert k1 == select_second_opinion(rs, frac=0.1, seed=0)
        assert "hard#1" not in select_second_opinion(rs, frac=1.0)

    def test_holding_for(self):
        assert holding_for("tagged", ["physical"]) == ("physical", "trait")
        assert holding_for("tagged", ["role_thing"]) == ("roles", "role")
        assert holding_for("trait", ["state"]) == (None, "trait")
        assert holding_for("tagged", ["demographic"]) == (None, "trait")
