"""Trait-hood rubric v1: prompt shape, example hygiene, parser, derived fields."""
import json
from pathlib import Path

import pytest

import data_analysis.seed_entities as se
from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import filter_rubric as fr

REPO = Path(__file__).resolve().parents[2]


def _row(i, **kw):
    base = {"id": i, "reason": "A stable habit.", "senses": ["s1"], "trait_sense_rank": 1,
            "enactable_in_text": 2, "verdict": "trait", "tags": [], "region": "cognitive_epistemic",
            "gloss": "This means " + "word " * 20, "confidence": 0.9}
    base.update(kw)
    return base


class TestPrompt:
    def test_reason_precedes_verdict_in_schema_and_examples(self):
        sp = fr.SYSTEM_PROMPT
        schema = sp[sp.index('{"results"'):]
        assert schema.index('"reason"') < schema.index('"verdict"')
        assert schema.index('"senses"') < schema.index('"verdict"')
        assert "reason first" in sp.lower()
        ex = sp[sp.index("## Examples"):sp.index("## Regions")]
        assert "reason first, then the verdict" in ex
        probe = fr.DEFINE_PROBE_PROMPT
        probe_schema = probe[probe.index('{"results"'):]
        assert probe_schema.index('"reason"') < probe_schema.index('"known"')
        assert "reason first" in probe

    @pytest.mark.xfail(strict=True, reason=(
        "rubric v1's twelve negative examples give the verdict with no reason (review_m1.md finding 11); "
        "the rubric text is frozen until the rubric v2 change set, which should make this pass"))
    def test_every_example_reasons_before_its_verdict(self):
        """Each example line must carry some reasoning (at least three words)
        before its verdict word, not open on the verdict."""
        import re
        ex = fr.SYSTEM_PROMPT[fr.SYSTEM_PROMPT.index("## Examples"):fr.SYSTEM_PROMPT.index("## Regions")]
        items = re.split(r"\n- ", ex.replace("\\\n", " "))[1:]
        bad = []
        for item in items:
            body = item.split(":", 1)[1]
            m = re.search(r"\b(verdict|trait|tagged|reject)\b", body)
            before = body[:m.start()] if m else body
            if len(re.findall(r"[A-Za-z]{2,}", before)) < 3:
                bad.append(item.split(":", 1)[0])
        assert bad == [], f"examples giving a verdict with no reason first: {bad}"

    def test_states_and_roles_rules_present(self):
        sp = fr.SYSTEM_PROMPT
        assert '"state"' in sp and "general tendency" in sp
        assert "role_person" in sp and "role_thing" in sp and "- Roles." in sp
        assert "transient_only" in sp and "physical" in sp

    def test_every_region_and_tag_named(self):
        for r in fr.REGION_VOCAB:
            assert r in fr.SYSTEM_PROMPT
        for t in fr.CLASSIFIER_TAGS:
            assert t in fr.SYSTEM_PROMPT
        assert "too_rare" not in fr.SYSTEM_PROMPT

    def test_example_counts(self):
        assert len(fr.POSITIVE_EXAMPLES) == 6 and len(fr.NEGATIVE_EXAMPLES) == 12
        for w in fr.EXAMPLE_WORDS + fr.MENTIONED_WORDS:
            assert f'"{w}"' in fr.SYSTEM_PROMPT or w in fr.SYSTEM_PROMPT, w
        assert sum("alignment_ai_agent" in fr.SYSTEM_PROMPT.split(f'"{w}"')[1][:400]
                   for w in fr.POSITIVE_EXAMPLES) >= 3

    def test_no_example_is_a_corpus_or_queue_stem(self):
        data = REPO / "data"
        q = se.load_queue(data / "seed_queue.json")
        stems = set().union(*se.corpus_stems(data).values())
        stems |= {e.get("stem") for e in q["entries"]}
        stems |= {normalize_to_file_name(e["label"]) for e in q["entries"] if e.get("label")}
        leaked = [w for w in fr.EXAMPLE_WORDS + fr.MENTIONED_WORDS if normalize_to_file_name(w) in stems]
        assert leaked == []

    def test_six_rejects_not_mentioned(self):
        """The validation rejects must not be taught by the rubric."""
        low = fr.SYSTEM_PROMPT.lower()
        for w in ("disciplinary", "engaging", "economic", "balanced", "empowered", "emotive"):
            assert w not in low, w

    def test_batch_prompt(self):
        p = fr.build_batch_prompt([{"id": 1, "label": "world-shaping"},
                                   {"id": 2, "label": "flustered", "intended_sense": "disposition  to be\nflustered"}])
        lines = p.splitlines()
        assert lines[0].startswith("Classify these 2 candidates")
        assert json.loads(lines[1]) == {"id": 1, "label": "world-shaping"}
        assert json.loads(lines[2]) == {"id": 2, "label": "flustered", "intended_sense": "disposition to be flustered"}


class TestParse:
    def test_plain(self):
        text = json.dumps({"results": [_row(1), _row(2, verdict="tagged", tags=["physical"], region="physical")]})
        rows, errs = fr.parse_batch(text, [1, 2])
        assert errs == {} and rows[2]["tags"] == ["physical"] and rows[1]["verdict"] == "trait"

    def test_fenced_and_prose(self):
        text = "Here you go:\n```json\n" + json.dumps({"results": [_row(1)]}) + "\n```\nDone."
        rows, errs = fr.parse_batch(text, [1])
        assert errs == {} and 1 in rows

    def test_plus_before_numbers(self):
        text = json.dumps({"results": [_row(1)]}).replace('"enactable_in_text": 2', '"enactable_in_text": +2')
        rows, errs = fr.parse_batch(text, [1])
        assert errs == {} and rows[1]["enactable_in_text"] == 2

    def test_missing_ids(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [_row(1)]}), [1, 2, 3])
        assert set(rows) == {1} and errs == {2: "missing", 3: "missing"}

    def test_out_of_vocab_tag_rejects_row(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [_row(1, tags=["weird"]), _row(2)]}), [1, 2])
        assert set(rows) == {2} and "out of vocabulary" in errs[1]

    def test_too_rare_not_allowed_from_classifier(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [_row(1, tags=["too_rare"])]}), [1])
        assert 1 in errs

    def test_bad_verdict_region_numbers(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [
            _row(1, verdict="maybe"), _row(2, region="space"), _row(3, confidence=1.5),
            _row(4, trait_sense_rank=4), _row(5, gloss=None), _row(6, reason="")]}), [1, 2, 3, 4, 5, 6])
        assert rows == {} and set(errs) == {1, 2, 3, 4, 5, 6}

    def test_reject_may_lack_region_gloss_rank(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [
            _row(1, verdict="reject", tags=["not_a_word"], region=None, gloss=None, trait_sense_rank=None)]}), [1])
        assert errs == {} and rows[1]["region"] is None and rows[1]["gloss"] is None

    def test_tagged_may_lack_gloss_region_rank(self):
        """Found in the M1 pilot: Haiku copies the rubric's tagged examples,
        which show no gloss; such rows are valid, region taken from the tag."""
        rows, errs = fr.parse_batch(json.dumps({"results": [
            _row(1, verdict="tagged", tags=["physical"], region=None, gloss=None, trait_sense_rank=None),
            _row(2, verdict="tagged", tags=["demographic"], region=None, gloss=None),
            _row(3, verdict="tagged", tags=["evaluative_only"], region=None, gloss=None),
            _row(4, verdict="tagged", tags=["transient_only"], region="social_interpersonal", gloss=None)]}),
            [1, 2, 3, 4])
        assert errs == {}
        assert [rows[i]["region"] for i in (1, 2, 3, 4)] == ["physical", "identity_demographic", None,
                                                              "social_interpersonal"]
        assert rows[1]["gloss"] is None and rows[1]["trait_sense_rank"] is None

    def test_trait_still_needs_gloss_region_rank(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [
            _row(1, gloss=None), _row(2, region=None), _row(3, trait_sense_rank=None)]}), [1, 2, 3])
        assert rows == {} and set(errs) == {1, 2, 3}

    def test_unparseable(self):
        rows, errs = fr.parse_batch("I cannot do that.", [1, 2])
        assert rows == {} and set(errs) == {1, 2}
        rows, errs = fr.parse_batch('{"results": [ {"id": 1, ', [1])
        assert rows == {} and errs[1].startswith("unparseable")

    def test_top_level_list_and_extra_ids(self):
        rows, errs = fr.parse_batch(json.dumps([_row(1), _row(9)]), [1])
        assert set(rows) == {1} and errs == {}

    def test_string_numbers_and_case(self):
        rows, errs = fr.parse_batch(json.dumps({"results": [
            _row(1, verdict="Trait", confidence="0.8", trait_sense_rank="2", tags="State")]}), [1])
        assert errs == {} and rows[1]["verdict"] == "trait" and rows[1]["tags"] == ["state"]
        assert rows[1]["trait_sense_rank"] == 2 and rows[1]["confidence"] == 0.8


class TestDerived:
    @pytest.mark.parametrize("rank,n,conf,expected", [
        (1, None, 0.9, False), (2, None, 0.9, True), (3, 1, 0.99, True), (1, 3, 0.69, True),
        (1, 3, 0.7, False), (1, 2, 0.1, False), (1, 5, 0.95, False), (1, None, 0.1, False),
    ])
    def test_polysemy_truth_table(self, rank, n, conf, expected):
        assert fr.derive_polysemy({"trait_sense_rank": rank, "confidence": conf}, n) is expected

    def test_polysemy_reject_without_rank(self):
        assert fr.derive_polysemy({"trait_sense_rank": None, "confidence": 0.9}, 1) is False

    @pytest.mark.parametrize("n,ok", [(17, False), (18, True), (30, True), (43, True), (44, False), (0, False)])
    def test_gloss_band(self, n, ok):
        assert fr.gloss_in_band(" ".join(["w"] * n)) is ok
        assert fr.gloss_in_band(None) is False


class TestProbe:
    def test_parse_probe(self):
        text = json.dumps({"results": [{"id": 1, "reason": "Known literary word.", "definition": "abstaining",
                                        "known": True},
                                       {"id": 2, "reason": "Not a word.", "definition": None, "known": "false"},
                                       {"id": 3, "reason": "x", "known": "maybe"}]})
        rows, errs = fr.parse_probe(text, [1, 2, 3, 4])
        assert rows[1]["known"] is True and rows[2]["known"] is False
        assert set(errs) == {3, 4}

    def test_probe_prompt(self):
        p = fr.build_probe_prompt([{"id": 1, "label": "abstemious"}])
        assert json.loads(p.splitlines()[1]) == {"id": 1, "word": "abstemious"}
