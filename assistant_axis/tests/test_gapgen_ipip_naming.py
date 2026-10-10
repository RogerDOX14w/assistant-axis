"""IPIP generator, the naming calls: prompts, parser, usage, records (a fake Anthropic client, no network)."""
import asyncio
import json

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.generators.ipip import naming as N
from assistant_axis.gapgen.generators.ipip.corpus import corpus_traits, queue_names
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.prompt_hygiene import prompt_words
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

GOOD = {"reason": "All describe doing tasks at once.", "label": "chore-prompt",
        "gloss": "This means doing routine tasks as soon as they come up, without putting them off.",
        "antonym_label": "last-minute", "antonym_gloss": "This means leaving tasks until they can no longer wait.",
        "is_trait": True, "ambiguity_flag": False, "single_word_exists": False}


def pole(cid=1, p="a", texts=("Get chores done right away.", "Love order and regularity."), scales=None):
    return N.PoleRef(granularity=350, cluster_id=cid, pole=p, statements=list(texts),
                     scales=scales if scales is not None else [{"scale": "Orderliness", "inventory": "NEO",
                                                                "direction": "for", "statements": 2}])


class TestPrompts:
    @pytest.mark.parametrize("form", ["blind", "hinted"])
    def test_reason_before_label(self, form):
        text = N.system_prompt(form)
        assert text.index("reason") < text.index('"label"')
        example = text[text.rindex("{"):]
        assert example.index('"reason"') < example.index('"label"')
        assert "reason first" in text

    @pytest.mark.parametrize("form", ["blind", "hinted"])
    def test_symptoms_count_moods_and_abilities_do_not(self, form):
        t = N.system_prompt(form).lower()
        assert "symptom-like dispositions count" in t
        assert "mood" in t and "ability" in t and "interest" in t and "life circumstance" in t

    def test_hinted_differs_only_by_the_scales(self):
        assert "scales" not in N.system_prompt("blind")
        assert '"scales"' in N.system_prompt("hinted")
        assert "Orderliness" not in N.build_user(pole())
        assert "Orderliness" in N.build_hinted_user(pole())

    def test_user_turn_is_one_json_object_of_first_person_statements(self):
        obj = json.loads(N.build_user(pole()))
        assert obj == {"statements": ["I get chores done right away.", "I love order and regularity."]}
        h = json.loads(N.build_hinted_user(pole()))
        assert h["scales"] == [{"scale": "Orderliness", "inventory": "NEO", "direction": "for", "statements": 2}]

    def test_long_poles_are_capped_deterministically(self):
        texts = [f"Item number {i}." for i in range(60)]
        a = json.loads(N.build_user(pole(texts=texts)))["statements"]
        b = json.loads(N.build_user(pole(texts=texts)))["statements"]
        assert len(a) == N.MAX_STATEMENTS and a == b

    def test_no_example_is_a_corpus_or_queue_name(self):
        traits = corpus_traits()
        names = set(traits) | {normalize_to_file_name(t["label"]) for t in traits.values()} | queue_names()
        for w in N.EXAMPLE_LABELS:
            assert normalize_to_file_name(w) not in names, w
            assert w in N.system_prompt("blind")
        # and no other quoted word of the prompts is one (examples are the only quoted labels)
        for form in ("blind", "hinted"):
            quoted = {q for q in __import__("re").findall(r'"([a-z][a-z \'-]+)"', N.system_prompt(form))}
            for q in quoted - set(N.FIELD_NAMES) - {"for", "against"}:
                assert normalize_to_file_name(q) not in names, q
        assert prompt_words(N.system_prompt("blind"))

    def test_prompt_versions_are_pinned(self):
        for form in ("blind", "hinted"):
            v, sha = N.prompt_version(form), N.prompt_sha256(form)
            assert N.PINNED[form][v] == sha, f"{form}: text changed without a version bump"


class TestParser:
    def test_good_answer(self):
        n, err = N.parse_naming(json.dumps(GOOD))
        assert err is None and n.label == "chore-prompt" and n.stem == "chore_prompt"
        assert n.is_trait is True and n.antonym_label == "last-minute" and n.notes == []
        # the stem is the registry's normalisation of the label (round trip)
        assert normalize_candidate(n.label).stem == n.stem == normalize_to_file_name(n.label)

    @pytest.mark.parametrize("text,kind", [
        ("```json\n" + json.dumps(GOOD) + "\n```", "fenced"),
        ("Here it is: " + json.dumps(GOOD), "not_one_object"),
        (json.dumps({k: v for k, v in GOOD.items() if k != "gloss"}), "missing_key"),
        (json.dumps(dict(GOOD, is_trait="maybe")), "bad_value"),
        (json.dumps(dict(GOOD, label="one two three four five")), "bad_label"),
        (json.dumps(dict(GOOD, gloss="Doing tasks at once.")), "bad_gloss"),
        ("", "empty"),
        (None, "no_response"),
    ])
    def test_rejections_are_counted_by_kind(self, text, kind):
        n, err = N.parse_naming(text)
        assert n is None and err.split(":")[0] == kind

    def test_lenient_on_case_and_null_antonym(self):
        n, err = N.parse_naming(json.dumps(dict(GOOD, label="Chore-Prompt", antonym_label=None, antonym_gloss=None,
                                                is_trait="true")))
        assert err is None and n.label == "chore-prompt" and n.antonym_label is None and n.is_trait is True
        assert "label lower-cased" in n.notes

    def test_long_gloss_is_flagged_not_rejected(self):
        long = "This means " + " ".join(["word"] * 30) + "."
        n, err = N.parse_naming(json.dumps(dict(GOOD, gloss=long)))
        assert err is None and "gloss over 25 words" in n.notes


def responder(answers=None, bad_first=False):
    seen = {}

    def f(kw):
        u = user_text(kw)
        hinted = '"scales"' in u
        k = (u, hinted)
        seen[k] = seen.get(k, 0) + 1
        if bad_first and seen[k] == 1:
            return make_response("```json\n{}\n```", input_tokens=700, output_tokens=250)
        a = dict(GOOD)
        if hinted:
            a["label"] = "orderly-minded"
        if answers:
            a.update(answers)
        return make_response(json.dumps(a), input_tokens=700, output_tokens=250)
    return f


class TestCalls:
    def run(self, poles, client, tmp_path, **kw):
        usage = MultiModelUsage()
        res = asyncio.run(N.name_poles(poles, client=client, model=N.DEFAULT_MODEL, usage=usage,
                                       responses_path=tmp_path / "responses.jsonl", **kw))
        return res, usage

    def test_blind_and_hinted_calls_and_usage(self, tmp_path):
        client = FakeAsyncAnthropic(responder())
        res, usage = self.run([pole(1, "a"), pole(2, "a")], client, tmp_path, hinted=True)
        assert len(client.calls) == 4 and usage.n_calls == 4
        assert usage.total_cost_usd == pytest.approx(4 * (700 * 0.10 + 250 * 0.50) / 1e6)
        assert res.namings[(350, 1, "a", "blind")].label == "chore-prompt"
        assert res.namings[(350, 1, "a", "hinted")].label == "orderly-minded"
        assert res.parse_rate() == (4, 4)
        recs = [json.loads(x) for x in (tmp_path / "responses.jsonl").read_text().splitlines()]
        assert len(recs) == 4 and {r["form"] for r in recs} == {"blind", "hinted"}
        r = recs[0]
        for k in ("granularity", "cluster_id", "pole", "model", "prompt_version", "prompt_sha256", "label_form", "user",
                  "text", "usage_raw", "parsed", "parse_error", "attempt", "at"):
            assert k in r
        assert r["label_form"] == "judge-display-v1"
        # temperature is left out for Haiku 5.5 (it refuses one); the system prompt is the form's
        kw = client.calls[0]
        assert "temperature" not in kw
        assert system_text(kw) in (N.system_prompt("blind"), N.system_prompt("hinted"))

    def test_a_bad_answer_is_asked_once_more_and_counted(self, tmp_path):
        client = FakeAsyncAnthropic(responder(bad_first=True))
        res, usage = self.run([pole()], client, tmp_path, hinted=False)
        assert len(client.calls) == 2 and usage.n_calls == 2               # both responses charged
        assert res.namings[(350, 1, "a", "blind")].label == "chore-prompt"
        assert res.error_kinds == {"fenced": 1} and res.parse_rate() == (1, 1)
        assert res.first_attempt_ok == 0

    def test_budget_stop(self, tmp_path):
        from assistant_axis.gapgen.cost import GuardedUsage
        client = FakeAsyncAnthropic(responder())
        usage = GuardedUsage(budget_usd=0.0003)
        res = asyncio.run(N.name_poles([pole(i) for i in range(1, 6)], client=client, model=N.DEFAULT_MODEL, usage=usage,
                                       responses_path=tmp_path / "r.jsonl", hinted=False, concurrency=1))
        assert res.stopped_by_budget and len(client.calls) < 5

    def test_estimate(self):
        est = N.estimate([pole(), pole(2)], hinted=True, model=N.DEFAULT_MODEL)
        assert est.lines[0].n_calls == 4 and est.usd > 0
