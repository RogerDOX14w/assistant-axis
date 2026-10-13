"""IPIP generator, the naming calls: the pinned prompts, the parser, usage, records (a fake Anthropic client)."""
import asyncio
import json
import re
import shutil

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.ipip import naming as N
from assistant_axis.gapgen.generators.ipip.corpus import corpus_traits, queue_names
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.prompt_hygiene import prompt_words
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

GOOD = {"reason": "All describe doing tasks at once.", "label": "chore-prompt",
        "gloss": "This means doing routine tasks as soon as they come up, without putting them off.",
        "antonym_label": "last-minute", "antonym_gloss": "This means leaving tasks until they can no longer wait.",
        "kind": "trait", "ambiguity_flag": False, "single_word_exists": False}


def pole(cid=1, p="a", texts=("Get chores done right away.", "Love order and regularity."), scales=None):
    return N.PoleRef(granularity=350, cluster_id=cid, pole=p, statements=list(texts),
                     scales=scales if scales is not None else [{"scale": "Orderliness", "inventory": "NEO",
                                                                "direction": "for", "statements": 2}])


class TestPinnedRubrics:
    """QUESTIONS 48 part 3: the two prompts left ``PROMPT_VERSIONS`` in code for the pinned rubric files, so
    that an edit cannot escape ``rubric_pins.py check``."""

    def test_the_prompts_are_the_rubric_files(self):
        assert N.RUBRIC_NAMES == {"blind": "ipip_naming_blind", "hinted": "ipip_naming_hinted"}
        for form, name in N.RUBRIC_NAMES.items():
            assert name in sr.PINNED_NAMES and name in sr.GENERATOR_NAMES
            assert N.system_prompt(form) == sr.load_prompt(name)
            assert N.prompt_sha256(form) == sr.sha256(sr.load_prompt(name))
            assert N.prompt_version(form) == sr.current_versions(None, (name,))[name][0]
        assert not [p for p in sr.mismatches() if p.split(":", 1)[0] in sr.PINNED_NAMES]
        assert not hasattr(N, "PROMPT_VERSIONS") and not hasattr(N, "PINNED")

    def test_an_unpinned_edit_is_refused(self, tmp_path):
        d = tmp_path / "rubrics"
        d.mkdir()
        for name in sr.PINNED_FILES.values():
            src = sr.RUBRICS_DIR / name
            if src.exists():
                shutil.copy2(src, d / name)
        shutil.copy2(sr.versions_path(), sr.versions_path(d))
        p = d / sr.PINNED_FILES["ipip_naming_blind"]
        p.write_text(p.read_text().replace("Name the one standing thing", "Name the one lasting thing"))
        with pytest.raises(N.RubricNotPinned, match="rubric_pins.py bump ipip_naming_blind"):
            N.system_prompt("blind", d)
        assert N.system_prompt("hinted", d)                      # the other form is unaffected


class TestPrompts:
    @pytest.mark.parametrize("form", ["blind", "hinted"])
    def test_reason_before_label(self, form):
        text = N.system_prompt(form)
        assert text.index("reason") < text.index('"label"')
        example = text[text.rindex("{"):]
        assert example.index('"reason"') < example.index('"label"')
        assert "reason first" in text

    @pytest.mark.parametrize("form", ["blind", "hinted"])
    def test_nothing_is_excluded_and_a_mood_gets_its_predisposition(self, form):
        """QUESTIONS 48 parts 1 and 2: the old text refused an ability, an interest or a life circumstance, all
        of which the corpus contains, and refused a momentary feeling instead of naming the predisposition."""
        t = N.system_prompt(form)
        assert "do not hold back" in t and "predisposition behind it" in t
        assert "habitual self-report" in t
        for phrase in ("These are not traits", "is_trait", "a passing mood or state"):
            assert phrase not in t, phrase
        # the categories it used to exclude are now named as things it should name
        for phrase in ("an ability or a skill", "a taste or a pursuit", "a standing fact of someone's life"):
            assert phrase in t, phrase

    @pytest.mark.parametrize("form", ["blind", "hinted"])
    def test_the_kind_field_uses_m1s_vocabulary(self, form):
        t = N.system_prompt(form)
        assert '"kind"' in t
        for k in N.KIND_VALUES:
            assert f'"{k}"' in t, k
        # the same eight the pinned M1 kind call uses, so the two are comparable
        m1 = sr.load_prompt("kind")
        assert all(f'"{k}"' in m1 for k in N.KIND_VALUES)

    def test_hinted_differs_only_by_the_scales(self):
        blind, hinted = N.system_prompt("blind"), N.system_prompt("hinted")
        assert "scales" not in blind and '"scales"' in hinted
        # identical from the third paragraph on (blind has one opening paragraph, hinted two)
        assert blind.split("\n\n", 1)[1] == hinted.split("\n\n", 2)[2]
        assert "Orderliness" not in N.build_user(pole())
        assert "Orderliness" in N.build_hinted_user(pole())
        assert '"direction"' in hinted or '"against"' in hinted

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
        allowed = set(N.FIELD_NAMES) | set(N.KIND_VALUES) | {"for", "against"}
        for form in ("blind", "hinted"):
            quoted = set(re.findall(r'"([a-z][a-z \'-]+)"', N.system_prompt(form)))
            for q in quoted - allowed:
                assert normalize_to_file_name(q) not in names, q
        assert prompt_words(N.system_prompt("blind"))

    @pytest.mark.xfail(strict=True, reason="rubric v1's third example, \"keeps others at arm's length\", is five "
                       "words against the prompt's own 1 to 4, and Haiku 5.5 copies it (12 rejected answers on "
                       "2026-10-13, 14 more of the form \"keeps others at a distance\").  The fix is a v2 text of both "
                       "naming rubrics, which needs Roger's sign-off; remove this mark with it.")
    def test_every_example_label_passes_the_label_check(self):
        for w in N.EXAMPLE_LABELS:
            assert w in N.system_prompt("blind") and w in N.system_prompt("hinted")
            assert N.label_problem(w) is None, w


class TestParser:
    def test_good_answer(self):
        n, err = N.parse_naming(json.dumps(GOOD))
        assert err is None and n.label == "chore-prompt" and n.stem == "chore_prompt"
        assert n.kind == "trait" and n.antonym_label == "last-minute" and n.notes == []
        assert not hasattr(n, "is_trait")
        # the stem is the registry's normalisation of the label (round trip)
        assert normalize_candidate(n.label).stem == n.stem == normalize_to_file_name(n.label)

    @pytest.mark.parametrize("kind", list(N.KIND_VALUES))
    def test_every_kind_is_accepted(self, kind):
        n, err = N.parse_naming(json.dumps(dict(GOOD, kind=kind)))
        assert err is None and n.kind == kind

    @pytest.mark.parametrize("given,want", [("Trait", "trait"), ("not a persona", "not_a_persona"),
                                            ("Not-A-Persona", "not_a_persona")])
    def test_a_kind_is_normalised_with_a_note(self, given, want):
        n, err = N.parse_naming(json.dumps(dict(GOOD, kind=given)))
        assert err is None and n.kind == want and "kind normalised" in n.notes

    @pytest.mark.parametrize("text,kind", [
        ("```json\n" + json.dumps(GOOD) + "\n```", "fenced"),
        ("Here it is: " + json.dumps(GOOD), "not_one_object"),
        (json.dumps({k: v for k, v in GOOD.items() if k != "gloss"}), "missing_key"),
        (json.dumps({k: v for k, v in GOOD.items() if k != "kind"}), "missing_key"),
        (json.dumps(dict(GOOD, kind="disposition")), "bad_value"),
        (json.dumps(dict(GOOD, kind=True)), "bad_value"),
        (json.dumps(dict(GOOD, ambiguity_flag="maybe")), "bad_value"),
        (json.dumps(dict(GOOD, label="one two three four five")), "bad_label"),
        (json.dumps(dict(GOOD, gloss="Doing tasks at once.")), "bad_gloss"),
        ("", "empty"),
        (None, "no_response"),
    ])
    def test_rejections_are_counted_by_kind(self, text, kind):
        n, err = N.parse_naming(text)
        assert n is None and err.split(":")[0] == kind

    def test_an_unknown_kind_says_what_was_wanted(self):
        _n, err = N.parse_naming(json.dumps(dict(GOOD, kind="disposition")))
        assert "not_a_persona" in err and "disposition" in err

    def test_lenient_on_case_and_null_antonym(self):
        n, err = N.parse_naming(json.dumps(dict(GOOD, label="Chore-Prompt", antonym_label=None, antonym_gloss=None,
                                                ambiguity_flag="true")))
        assert err is None and n.label == "chore-prompt" and n.antonym_label is None
        assert n.ambiguity_flag is True and "label lower-cased" in n.notes

    def test_long_gloss_is_flagged_not_rejected(self):
        long = "This means " + " ".join(["word"] * 30) + "."
        n, err = N.parse_naming(json.dumps(dict(GOOD, gloss=long)))
        assert err is None and "gloss over 25 words" in n.notes

    def test_a_long_antonym_is_noted_not_rejected(self):
        """Parser version 2: the antonym is never submitted (only the evaluation's antonym agreement reads it), so
        a five-word antonym no longer throws the label away with it."""
        n, err = N.parse_naming(json.dumps(dict(GOOD, antonym_label="Leaves Tasks Until The Deadline")))
        assert err is None and n.label == "chore-prompt"
        assert n.antonym_label == "leaves tasks until the deadline"
        assert "antonym_label over 4 words" in n.notes and "antonym_label lower-cased" in n.notes

    def test_an_antonym_that_is_not_a_string_is_still_rejected(self):
        _n, err = N.parse_naming(json.dumps(dict(GOOD, antonym_label=["last-minute"])))
        assert err.startswith("bad_label: antonym")

    def test_the_label_limit_is_unchanged_and_says_why(self):
        _n, err = N.parse_naming(json.dumps(dict(GOOD, label="takes things at face value")))
        assert err == "bad_label: 'takes things at face value' (5 words, at most 4)"
        # a hyphenated compound is one word, as split.is_phrase counts it
        n, err = N.parse_naming(json.dumps(dict(GOOD, label="fair-dealing to a fault")))
        assert err is None and n.stem == "fair_dealing_to_a_fault"
        assert N.label_problem("fair-dealing to a fault") is None


#: Rejected answers of the 2026-10-13 runs (granularity, cluster, pole, form), their label and antonym as Haiku 5.5
#: gave them, and whether parser version 2 accepts the answer.  Version 1 rejected all eight.
RECORDED_REJECTIONS = [
    ((600, 282, "a", "blind"), "easy to confide in", "hard to get to know", True),
    ((600, 383, "a", "blind"), "devoted to helping friends", "keeps friends at a distance", True),
    ((150, 39, "b", "blind"), "unfussy about gifts", "makes a fuss over gifts", True),
    ((350, 158, "a", "blind"), "close bonds with others", "keeps others at arm's length", True),
    ((600, 56, "a", "blind"), "keeps others at arm's length", "open and approachable", False),
    ((600, 322, "b", "blind"), "takes things at face value", "seeks hidden meanings", False),
    ((150, 665, "a", "hinted"), "direct and to the point", "meandering and digressive", False),
    ((350, 121, "a", "blind"), "overly compliant, desperate to please", "firmly self-directed", False),
]


class TestRecordedRejections:
    """The ``bad_label`` rejections of the recorded naming runs, replayed through the parser (2026-10-13): every
    rejection was a label or an antonym over four words; version 2 accepts the answers whose antonym alone was
    over, and still rejects every over-long label."""

    @pytest.mark.parametrize("key,label,antonym,accepted", RECORDED_REJECTIONS, ids=lambda x: str(x))
    def test_frozen_examples(self, key, label, antonym, accepted):
        n, err = N.parse_naming(json.dumps(dict(GOOD, label=label, antonym_label=antonym)))
        if accepted:
            assert err is None and n.label == label and n.antonym_label == antonym
            assert "antonym_label over 4 words" in n.notes
        else:
            assert n is None and err.startswith(f"bad_label: {label!r}")

    def test_replay_of_the_recorded_responses(self):
        from assistant_axis.gapgen.generators.ipip import NAMING_RESPONSES_PATH
        if not NAMING_RESPONSES_PATH.exists():
            pytest.skip("no recorded naming responses")
        recs = [json.loads(x) for x in NAMING_RESPONSES_PATH.read_text().splitlines() if x.strip()]
        v1 = [r for r in recs if r.get("parser_version") is None]
        tally = {"antonym_now_ok": 0, "label_still_rejected": 0}
        for r in v1:
            n, err = N.parse_naming(r["text"])
            old_err = r["parse_error"]
            if old_err is None:
                # nothing version 1 accepted changes
                assert err is None, (r["granularity"], r["cluster_id"], r["pole"], r["form"], err)
                assert {k: getattr(n, k) for k in ("label", "stem", "antonym_label", "kind")} == \
                    {k: r["parsed"][k] for k in ("label", "stem", "antonym_label", "kind")}
            elif old_err.startswith("bad_label: antonym"):
                obj = json.loads(r["text"])
                assert err is None and n.label == " ".join(obj["label"].split()).lower()
                assert len(obj["antonym_label"].split()) > N.MAX_LABEL_WORDS
                assert "antonym_label over 4 words" in n.notes
                tally["antonym_now_ok"] += 1
            elif old_err.startswith("bad_label"):
                assert err is not None and err.startswith(old_err) and "words, at most 4" in err
                tally["label_still_rejected"] += 1
            else:
                assert err == old_err
        tonight = [r for r in v1 if r["at"].startswith("2026-10-13") and r["parse_error"]]
        if len(tonight) == 134:      # the three runs of 2026-10-13 (600, 350, 150), as recorded
            assert sum(1 for r in tonight if N.parse_naming(r["text"])[1] is None) == 60


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
        for k in ("granularity", "cluster_id", "pole", "model", "rubric", "prompt_version", "prompt_sha256",
                  "label_form", "user", "text", "usage_raw", "parsed", "parse_error", "parser_version", "attempt",
                  "at"):
            assert k in r
        assert r["label_form"] == "judge-display-v1" and r["parser_version"] == N.PARSER_VERSION == 2
        assert r["rubric"] in N.RUBRIC_NAMES.values()
        assert r["prompt_sha256"] == N.prompt_sha256(r["form"])
        # temperature is left out for Haiku 5.5 (it refuses one); the system prompt is the form's rubric text
        kw = client.calls[0]
        assert "temperature" not in kw
        assert system_text(kw) in (N.system_prompt("blind"), N.system_prompt("hinted"))

    def test_the_prompts_are_read_once(self, tmp_path):
        """A rubric edited mid-run cannot change what the run sends: ``name_poles`` takes the loaded rubrics."""
        client = FakeAsyncAnthropic(responder())
        rubrics = {"blind": dict(N.load_rubric("blind"), version=99)}
        res = asyncio.run(N.name_poles([pole()], client=client, model=N.DEFAULT_MODEL, usage=MultiModelUsage(),
                                       hinted=False, rubrics=rubrics, responses_path=tmp_path / "r.jsonl"))
        assert res.parse_rate() == (1, 1)
        rec = json.loads((tmp_path / "r.jsonl").read_text().splitlines()[0])
        assert rec["prompt_version"] == 99

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
        res = asyncio.run(N.name_poles([pole(i) for i in range(1, 6)], client=client, model=N.DEFAULT_MODEL,
                                       usage=usage, responses_path=tmp_path / "r.jsonl", hinted=False,
                                       concurrency=1))
        assert res.stopped_by_budget and len(client.calls) < 5

    def test_estimate(self):
        est = N.estimate([pole(), pole(2)], hinted=True, model=N.DEFAULT_MODEL)
        assert est.lines[0].n_calls == 4 and est.usd > 0
