"""Rubric v2, round 3: the ambiguity work (decisions_m1.md open point D, Roger's
reply "A word with more then one sense ..." and the four cases), and the
coordinator's ruling on QUESTIONS 17 (a version number identifies one prompt
text).  Part numbers are the coordinator's round-3 list.  Written before the
change; each test failed against aca2248 for the reason its name gives."""
import hashlib
import json
import re
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen.filter import FilterItem, FilterRunner
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
REPO = Path(__file__).resolve().parents[2]
RESERVED = Path(__file__).resolve().parent / "data" / "gapgen_reserved_words.txt"
SIX = {"disciplinary", "engaging", "economic", "balanced", "empowered", "emotive"}


def pr():
    from assistant_axis.gapgen import plain_reading
    return plain_reading


def rv():
    from assistant_axis.gapgen import rubric_versions
    return rubric_versions


# ---------------------------------------------------------------------------
# Q17: a version number identifies one prompt text
# ---------------------------------------------------------------------------

class TestVersionPins:
    def test_every_prompt_matches_its_pinned_hash(self):
        assert rv().mismatches() == []

    def test_table_covers_every_prompt(self):
        # M2 (2026-10-01) added the calibration's two prompts to the table; round 4 (2026-10-02) the two
        # paraphrase styles
        assert set(rv().current()) == {"classifier", "probe", "states_queue", "states_corpus",
                                       "plain_reading", "comparison", "calibration_paraphrase",
                                       "calibration_paraphrase_plain", "calibration_paraphrase_terse",
                                       "calibration_blinded"}

    def test_a_text_change_without_a_new_version_fails(self, monkeypatch):
        monkeypatch.setattr(fr, "SYSTEM_PROMPT", fr.SYSTEM_PROMPT + " ")
        assert any("classifier" in m for m in rv().mismatches())

    def test_versions_only_go_up_and_old_hashes_stay(self):
        h = rv().HISTORY
        assert h["classifier"][1] == "113bde981420d93fc58b41b0b6cf12785537a3186588cc3289ef6e9edd8da2a5"
        assert h["probe"][2] == "0785cd073e2cd2b62f412b379e003cdc39fdf54f360a99dc517dd2621add0103"
        for name, (v, _sha) in rv().current().items():
            assert v == max(h[name]), name

    def test_classifier_is_version_3_or_later(self):
        assert fr.TRAITHOOD_RUBRIC_VERSION >= 3  # 4 since round 4


# ---------------------------------------------------------------------------
# 3. senses a person can be, and the two notes derived from them
# ---------------------------------------------------------------------------

def crow(i, label, **kw):
    base = {"id": i, "label": label, "reason": "A habit of mind shown in how someone talks.",
            "person_senses": [{"sense": "habit of mind", "kind": "trait"}],
            "trait_senses_equally_obvious": False, "judged_sense": "habit of mind", "enactable_in_text": 2, "verdict": "trait", "tags": [],
            "membership_kind": None, "region": "social_interpersonal", "alignment_relevant": False,
            "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}
    base.update(kw)
    return base


def parse(*rows):
    labels = {r["id"]: r["label"] for r in rows}
    return fr.parse_batch(json.dumps({"results": list(rows)}), list(labels), labels=labels)


class TestPersonSenses:
    def test_prompt_asks_for_person_senses_reason_first(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        schema = sp[sp.index('{"results"'):]
        order = ['"reason"', '"person_senses"', '"trait_senses_equally_obvious"', '"verdict"']
        assert [schema.index(k) for k in order] == sorted(schema.index(k) for k in order)
        assert "trait_sense_rank" not in schema
        assert "can only be said of things" in sp
        for k in fr.PERSON_SENSE_KINDS:
            assert k in sp

    def test_validator_derives_senses_and_rank(self):
        rows, errs = parse(crow(1, "a", person_senses=[{"sense": "relaxed", "kind": "trait"},
                                                       {"sense": "not tied", "kind": "state"}]))
        assert errs == {}
        r = rows[1]
        assert r["senses"] == ["relaxed", "not tied"] and r["trait_sense_rank"] == 1
        rows, _ = parse(crow(1, "a", verdict="tagged", tags=["state"], region="transient_state",
                             person_senses=[{"sense": "passing", "kind": "state"},
                                            {"sense": "habit", "kind": "trait"}]))
        assert rows[1]["trait_sense_rank"] == 2

    def test_validator_rules(self):
        rows, errs = parse(crow(1, "a", person_senses=[{"sense": "x", "kind": "mood"}]),
                           crow(2, "b", person_senses=[{"sense": "x", "kind": "state"}]),
                           crow(3, "c", person_senses="x"),
                           crow(4, "d", verdict="reject", tags=["relational_only"], person_senses=[],
                                region=None, gloss=None))
        assert set(rows) == {4}
        # round 5: an unknown kind is dropped, not refused; row 1 then fails for want of a trait sense
        assert "trait sense" in errs[1] and "trait sense" in errs[2]

    def test_two_trait_senses(self):
        ts = [{"sense": "relaxed", "kind": "trait"}, {"sense": "promiscuous", "kind": "trait"}]
        rows, _ = parse(crow(1, "a", person_senses=ts, trait_senses_equally_obvious=True),
                        crow(2, "b", person_senses=ts, trait_senses_equally_obvious=False))
        assert fr.derive_notes(rows[1]) == ["two_trait_senses"]
        assert fr.derive_notes(rows[2]) == []

    def test_nontrait_person_sense(self):
        rows, _ = parse(crow(1, "a", person_senses=[{"sense": "gentle", "kind": "trait"},
                                                    {"sense": "flabby", "kind": "physical"}]),
                        crow(2, "b", verdict="tagged", tags=["state"], region="transient_state",
                             person_senses=[{"sense": "in a mood", "kind": "state"},
                                            {"sense": "moody", "kind": "trait"}]))
        assert fr.derive_notes(rows[1]) == ["nontrait_person_sense"]
        assert fr.derive_notes(rows[2]) == []  # obvious reading is a state: the state tag, not the note

    def test_wordnet_rule_superseded(self):
        row = {"person_senses": [{"sense": "x", "kind": "trait"}], "trait_senses_equally_obvious": False,
               "verdict": "trait", "trait_sense_rank": 1, "confidence": 0.5}
        assert fr.derive_polysemy(row, 5) is False  # v1 fired on 3+ WordNet senses with low confidence

    def test_prompt_examples_show_each_case(self):
        ex = fr.SYSTEM_PROMPT[fr.SYSTEM_PROMPT.index("## Examples"):fr.SYSTEM_PROMPT.index("## Regions")]
        body = " ".join(ex.replace("\\\n", " ").split())
        assert "trait_senses_equally_obvious true" in body  # schema field names since round 4
        assert "(physical)" in body  # the kind "bodily" became "physical" in round 4


# ---------------------------------------------------------------------------
# 1, 2. the plain reading and the comparison
# ---------------------------------------------------------------------------

class TestPlainReadingPrompts:
    def test_reading_prompt_is_the_bare_word(self):
        p = pr().build_reading_prompt("sporting")
        assert '"You are sporting."' in p
        assert pr().READING_VERSION >= 1

    def test_comparison_prompt_reason_first_three_answers(self):
        p = " ".join(pr().COMPARISON_PROMPT.split())
        schema = p[p.index('{"results"'):]
        assert schema.index('"reason"') < schema.index('"relation"')
        for rel in ("same", "related", "different"):
            assert f'"{rel}"' in schema
        assert pr().RELATIONS == ("same", "related", "different")

    def test_hashes(self):
        assert pr().PROMPT_SHA256["plain_reading"] == hashlib.sha256(pr().READING_PROMPT.encode()).hexdigest()
        assert pr().PROMPT_SHA256["comparison"] == hashlib.sha256(pr().COMPARISON_PROMPT.encode()).hexdigest()

    def test_parse_compare(self):
        text = json.dumps({"results": [
            {"id": 1, "label": "a", "reason": "r", "relation": "different", "confidence": 0.9},
            {"id": 2, "label": "b", "reason": "r", "relation": "Related", "confidence": 0.7},
            {"id": 3, "label": "c", "reason": "r", "relation": "opposite", "confidence": 0.7}]})
        rows, errs = pr().parse_compare(text, [1, 2, 3], labels={1: "a", 2: "b", 3: "c"})
        assert rows[1]["relation"] == "different" and rows[2]["relation"] == "related" and 3 in errs

    def test_parse_reading(self):
        assert pr().parse_reading("  Enforces rules strictly.\n") == "Enforces rules strictly."
        assert pr().parse_reading("") is None


def reading_responder(kw):
    """Plain readings: 'rule-enforcer' for disciplinary, else 'plain X'.  Comparisons:
    'different' when the reading says rule-enforcer, else 'same'."""
    sysp = system_text(kw) if kw.get("system") else ""
    if not sysp:
        word = re.search(r'"You are (.+?)\."', user_text(kw)).group(1)
        return "A strict rule-enforcer." if word == "disciplinary" else f"Behaves in a plain {word} way."
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    return json.dumps({"results": [
        {"id": it["id"], "label": it["label"], "reason": "compared",
         "relation": "different" if "rule-enforcer" in it["plain_reading"] else "same", "confidence": 0.9}
        for it in items]})


class TestPlainReadingRunner:
    def test_reading_call_sees_only_the_word(self):
        client = FakeAsyncAnthropic(reading_responder)
        r = pr().PlainReadingRunner(client=client, batch_id="b", reading_model=HAIKU, compare_model=SONNET)
        out = r.run([pr().ReadingItem(key="disciplinary#1", label="disciplinary",
                                      intended="This means keeping to a single discipline.")])
        reads = [c for c in client.calls if not c.get("system")]
        assert len(reads) == 1 and "single discipline" not in json.dumps(reads[0])
        assert reads[0]["temperature"] == 0.0 and reads[0]["model"] == HAIKU
        o = out[0]
        assert o.reading == "A strict rule-enforcer." and o.comparison["relation"] == "different"
        assert o.notes == ["overshadowed"]
        assert o.comparison["model"] == SONNET and o.intended.startswith("This means keeping")

    def test_related_is_a_note_not_a_flag(self):
        def resp(kw):
            if not kw.get("system"):
                return "Says what it thinks."
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            return json.dumps({"results": [{"id": it["id"], "label": it["label"], "reason": "r",
                                            "relation": "related", "confidence": 0.8} for it in items]})
        r = pr().PlainReadingRunner(client=FakeAsyncAnthropic(resp), batch_id="b", reading_model=HAIKU,
                                    compare_model=SONNET)
        o = r.run([pr().ReadingItem(key="a#1", label="a", intended="i")])[0]
        # round 4: related raises its own note, reading_related, never overshadowed
        assert o.notes == ["reading_related"] and o.comparison["relation"] == "related"

    def test_reuse_readings_skips_the_call(self):
        client = FakeAsyncAnthropic(reading_responder)
        r = pr().PlainReadingRunner(client=client, batch_id="b", reading_model=HAIKU, compare_model=SONNET,
                                    reuse_readings={"calm": "Stays calm."})
        r.run([pr().ReadingItem(key="calm#1", label="calm", intended="i")])
        assert all(c.get("system") for c in client.calls)

    def test_summary_confusion_table(self):
        client = FakeAsyncAnthropic(reading_responder)
        r = pr().PlainReadingRunner(client=client, batch_id="b", reading_model=HAIKU, compare_model=SONNET)
        out = r.run([pr().ReadingItem(key="disciplinary#1", label="disciplinary", intended="x",
                                      meta={"expected": "different"}),
                     pr().ReadingItem(key="calm#1", label="calm", intended="y", meta={"expected": "different"}),
                     pr().ReadingItem(key="calm#2", label="calm", intended="z", meta={"expected": "same"})])
        s = pr().summarize(out, stats=r.stats, usage=r.usage)
        assert s["confusion"] == {"different": {"same": 1, "related": 0, "different": 1},
                                  "same": {"same": 1, "related": 0, "different": 0}}
        assert [w["key"] for w in s["wrong"]] == ["calm#1"]
        assert s["overshadowed"] == ["disciplinary"]
        assert len([c for c in client.calls if not c.get("system")]) == 2  # one reading per label

    def test_corpus_pairs_read_only(self, tmp_path):
        d = tmp_path / "data" / "traits" / "instructions"
        d.mkdir(parents=True)
        (d / "calm.json").write_text(json.dumps({"positive_label": "calm", "description": "This means staying calm."}))
        items = pr().corpus_pairs(tmp_path / "data")
        assert [(i.label, i.intended, i.meta["expected"]) for i in items] == [("calm", "This means staying calm.",
                                                                               "same")]


class TestFilterIntegration:
    def _responder(self, kw):
        if not kw.get("system"):
            return reading_responder(kw)
        sysp = system_text(kw)
        if "plain_reading" in sysp and "intended_meaning" in sysp:
            return reading_responder(kw)
        if "real English word" in sysp:
            items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
            return json.dumps({"results": [{"id": it["id"], "reason": "r", "definition": "d", "known": True}
                                           for it in items]})
        items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
        return json.dumps({"results": [crow(it["id"], it["label"]) for it in items]})

    def test_reading_and_comparison_only_with_an_intended_meaning(self):
        client = FakeAsyncAnthropic(self._responder)
        r = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model=SONNET, second_opinion=False,
                         zipf_fn=lambda w: 4.0, wordnet=False)
        out = {x.key: x for x in r.run([
            FilterItem(key="disciplinary#1", label="disciplinary", intended_sense="keeps to a single discipline"),
            FilterItem(key="stubborn#1", label="stubborn")])}
        f = out["disciplinary#1"].filter
        assert f["plain_reading"]["text"] == "A strict rule-enforcer."
        assert f["comparison"]["relation"] == "different" and f["comparison"]["model"] == SONNET
        assert f["polysemy_notes"] == ["overshadowed"] and f["polysemy"] is True
        s = out["stubborn#1"].filter
        assert s["plain_reading"] is None and s["comparison"] is None and s["polysemy"] is False
        reads = [c for c in client.calls if not c.get("system")]
        assert len(reads) == 1  # no reading call for the row without an intended meaning

    def test_filter_block_keeps_plan_fields(self):
        client = FakeAsyncAnthropic(self._responder)
        r = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model=None, second_opinion=False,
                         zipf_fn=lambda w: 4.0, wordnet=False)
        f = r.run([FilterItem(key="stubborn#1", label="stubborn")])[0].filter
        for k in ("senses", "trait_sense_rank", "polysemy", "polysemy_notes", "person_senses",
                  "trait_senses_equally_obvious", "plain_reading", "comparison"):
            assert k in f, k
        assert f["rubric_version"] == 4


# ---------------------------------------------------------------------------
# 3. the judgement-call table (case 4)
# ---------------------------------------------------------------------------

def test_judgement_call_table(tmp_path, capsys):
    from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
    from data_analysis.gap_generation import gap_registry
    reg = tmp_path / "r.jsonl"
    submit_candidates([Candidate(surface=w, generator="g", run_id="r") for w in ("soft", "stubborn")],
                      registry_path=reg)
    Registry(reg).update("soft#1", {"filter": {"verdict": "trait", "tags": [],
                                               "polysemy_notes": ["nontrait_person_sense"],
                                               "person_senses": [{"sense": "gentle and lenient", "kind": "trait"},
                                                                 {"sense": "physically soft", "kind": "physical"}]}})
    Registry(reg).update("stubborn#1", {"filter": {"verdict": "trait", "tags": [], "polysemy_notes": []}})
    assert gap_registry.main(["--registry", str(reg), "judgement-calls"]) == 0
    out = capsys.readouterr().out
    # round 5: a note column (obvious_sense_not_trait rows are listed too, first)
    assert "| word | key | note | trait sense | other sense | Roger's call |" in out
    assert "| soft | soft#1 | nontrait_person_sense | gentle and lenient | physically soft (physical) |  |" in out
    assert "stubborn" not in out


# ---------------------------------------------------------------------------
# example hygiene across every prompt, with the two new sources
# ---------------------------------------------------------------------------

def _forbidden_stems():
    import data_analysis.seed_entities as se
    data = REPO / "data"
    q = se.load_queue(data / "seed_queue.json")
    stems = set().union(*se.corpus_stems(data).values())
    stems |= {e.get("stem") for e in q["entries"]}
    stems |= {normalize_to_file_name(e["label"]) for e in q["entries"] if e.get("label")}
    return stems


def test_example_words_avoid_every_source():
    from assistant_axis.gapgen import states_pass as sp
    words = (list(fr.EXAMPLE_WORDS) + list(fr.MENTIONED_WORDS) + list(sp.EXAMPLE_WORDS)
             + list(sp.SUGGESTED_NAMES) + list(pr().EXAMPLE_WORDS))
    stems = _forbidden_stems()
    # round 4 (review finding 6): the decisions file and the probe results are
    # untracked working files; their words come from the tracked list built from them
    reserved = set(RESERVED.read_text(encoding="utf-8").split())
    bad = []
    for w in words:
        why = [src for src, hit in (("corpus/queue", normalize_to_file_name(w) in stems),
                                    ("six", w.lower() in SIX),
                                    ("reserved", " " not in w and w.lower() in reserved)) if hit]
        if why:
            bad.append((w, why))
    assert bad == []


class TestPlainReadingCLI:
    """Written after the CLI (not seen failing first)."""

    @pytest.fixture
    def cli(self, monkeypatch):
        import anthropic
        import dotenv

        from data_analysis.gap_generation import plain_reading as mod
        holder = {}

        def factory(**kw):
            holder["client"] = FakeAsyncAnthropic(reading_responder)
            return holder["client"]
        monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
        monkeypatch.setattr(mod, "git_sha", lambda *a, **k: "abc1234")
        monkeypatch.setattr(mod, "platform_dirty_files", lambda *a, **k: [])
        holder["mod"] = mod
        return holder

    def _pairs(self, tmp_path):
        p = tmp_path / "pairs.jsonl"
        rows = [{"key": "disciplinary#same", "label": "disciplinary", "intended": "keeps to one discipline",
                 "expected": "different"},
                {"key": "calm#same", "label": "calm", "intended": "stays calm", "expected": "same"}]
        p.write_text("".join(json.dumps(r) + "\n" for r in rows))
        return p

    def test_pairs_run_writes_everything(self, tmp_path, cli):
        cand = tmp_path / "cand"
        assert cli["mod"].main(["--batch-id", "r1", "--pairs", str(self._pairs(tmp_path)), "--out-root", str(cand)]) == 0
        d = cand / "plain_reading" / "r1"
        for f in ("responses.jsonl", "results.jsonl", "summary.json", "usage.json", "run.json"):
            assert (d / f).exists(), f
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["accuracy"] == 1.0 and s["overshadowed"] == ["disciplinary"]
        run = json.loads((d / "run.json").read_text())
        assert run["prompt_sha256"] == pr().PROMPT_SHA256 and run["versions"]["comparison"] == pr().COMPARISON_VERSION
        # reuse: a second run on the same readings makes no reading call
        assert cli["mod"].main(["--batch-id", "r2", "--pairs", str(self._pairs(tmp_path)), "--out-root", str(cand),
                                "--reuse-readings", str(d)]) == 0
        assert all(c.get("system") for c in cli["client"].calls)

    def test_dry_run_and_budget(self, tmp_path, cli):
        cand = tmp_path / "cand"
        args = ["--pairs", str(self._pairs(tmp_path)), "--out-root", str(cand)]
        assert cli["mod"].main(["--batch-id", "d", "--dry-run", *args]) == 0
        assert cli["mod"].main(["--batch-id", "e", "--budget-usd", "0.0000001", *args]) == 2
        assert not (cand / "plain_reading").exists() and "client" not in cli


def test_heldout_figure():
    f = pr().heldout_figure([{"label": w, "notes": ["overshadowed"] if w in ("disciplinary", "economic") else []}
                             for w in sorted(SIX)])
    assert f == {"n": 6, "overshadowed": 2, "overshadowed_labels": ["disciplinary", "economic"], "target": 4,
                 "meets_target": False}
