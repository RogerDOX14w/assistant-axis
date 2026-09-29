"""The split filter's prompts and their pins (coding_plan_split.md section 8, test 1), and the word
hygiene of the eight prompts (prompt_hygiene)."""
import json
import shutil
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import paths
from assistant_axis.gapgen import split_rubrics as sr

REPO = Path(__file__).resolve().parents[2]
RESERVED = Path(__file__).resolve().parent / "data" / "gapgen_reserved_words.txt"

#: The hashes of the texts the paid runs of 2026-09-29 sent (each probe's run.json), checked by hand
#: when the first rows of versions.json were written: sense probe_single (draft6), established
#: probe_rerun_wording/run_established.json, vague probe_checks_single, kind probe_rerun_wording,
#: same_sense probe_same_sense, gloss probe_gloss_v2, alignment and descriptors probe_last_step.
RECORDED = {
    "sense": (6, "5fb28b588776d3483c26e349973b32f2d7694fa85202a57489730e6349de990e"),
    "established": (4, "d9b6e59dbe76864e5a5b7d07233ce2f73f987363420df2c58210cf06bc60e684"),
    "vague": (3, "ea4b01022195f4007560512e91fbeab56d14c1a6e83eff4a670756cc527d6cf5"),
    "kind": (4, "7b8cc5c9f0439d17ee648ce01f4650e0639feebb3b2e0a9ae5cbd14a42c2835e"),
    "same_sense": (1, "a4b17cc25da1c045f4350dfd394bf880831b9626f3bbe8089c30b747d1ce6963"),
    "gloss": (2, "cb14741b0ba11a6f0deeda9e73e943604cab0496e689a907e5f84a2c2763c7b8"),
    "alignment": (1, "85291d289b502a372390a9e2a569ca12c412c91132e062a6052051959991823d"),
    "descriptors": (1, "4f4b966e876ea0d0250df349e0eb7f56b76fe151ed3f14006cb9731576e2094f"),
}


class TestPins:
    def test_every_prompt_is_its_latest_pin(self):
        assert sr.mismatches() == []
        cur = sr.current_versions()
        for name in sr.NAMES:
            assert cur[name][1] == sr.sha256(sr.load_prompt(name)), name

    def test_first_rows_are_the_texts_of_the_paid_runs(self):
        rows = sr.read_versions()["prompts"]
        for name, (v, sha) in RECORDED.items():
            first = rows[name][0]
            assert (first["version"], first["sha256"]) == (v, sha), name

    def test_rubric_versions_covers_the_split_prompts(self):
        from assistant_axis.gapgen import rubric_versions
        assert rubric_versions.mismatches() == []

    def test_rubrics_dir_is_a_platform_path(self):
        from assistant_axis.gapgen.runs import PLATFORM_PATHS
        assert paths.RUBRICS_DIR == REPO / "reports" / "trait_gap_generation" / "rubrics"
        assert "reports/trait_gap_generation/rubrics" in PLATFORM_PATHS

    def _copy(self, tmp_path):
        d = tmp_path / "rubrics"
        shutil.copytree(paths.RUBRICS_DIR, d, ignore=shutil.ignore_patterns("README.md"))
        return d

    def test_a_changed_text_without_a_new_row_fails(self, tmp_path):
        d = self._copy(tmp_path)
        p = d / sr.FILES["vague"]
        p.write_text(p.read_text(encoding="utf-8").replace("Say whether the instruction is too vague to act on.",
                                                            "Say whether the instruction is too vague to act upon.", 1),
                     encoding="utf-8")
        probs = sr.mismatches(d)
        assert len(probs) == 1 and probs[0].startswith("vague: text changed")
        assert "rubric_pins.py bump vague" in sr.bump_command(probs)
        row = sr.bump("vague", "test edit", now="t", rubrics_dir=d)
        assert row["version"] == 4 and sr.mismatches(d) == []
        rows = sr.read_versions(d)["prompts"]["vague"]
        assert [r["version"] for r in rows] == [3, 4]          # append-only
        with pytest.raises(ValueError):
            sr.bump("vague", "again", now="t", rubrics_dir=d)  # nothing changed

    def test_a_text_outside_the_block_does_not_count(self, tmp_path):
        d = self._copy(tmp_path)
        p = d / sr.FILES["kind"]
        p.write_text(p.read_text(encoding="utf-8").replace("## Your notes", "## Your notes\n\nA note.", 1),
                     encoding="utf-8")
        assert sr.mismatches(d) == []

    def test_a_file_with_two_blocks_is_refused(self, tmp_path):
        d = self._copy(tmp_path)
        p = d / sr.FILES["gloss"]
        t = p.read_text(encoding="utf-8")
        p.write_text(t + "\n## The prompt\n\n````text\nX\n````\n", encoding="utf-8")
        with pytest.raises(sr.RubricFileError):
            sr.load_prompt("gloss", d)

    def test_load_prompt_is_the_block_byte_for_byte(self):
        text = sr.load_prompt("sense")
        assert text.startswith("A persona is given a one-line instruction prompt")
        assert text.endswith("Return one row per id, in the order given.")
        assert "````" not in text

    def test_rubric_pins_cli(self, tmp_path, capsys):
        from data_analysis.gap_generation import rubric_pins
        assert rubric_pins.main(["check"]) == 0
        d = self._copy(tmp_path)
        p = d / sr.FILES["alignment"]
        p.write_text(p.read_text(encoding="utf-8").replace("or getting round them", "or getting around them"),
                     encoding="utf-8")
        assert rubric_pins.main(["--rubrics-dir", str(d), "check"]) == 1
        assert "bump alignment" in capsys.readouterr().err
        assert rubric_pins.main(["--rubrics-dir", str(d), "bump", "alignment", "--why", "round -> around"]) == 0
        assert rubric_pins.main(["--rubrics-dir", str(d), "check"]) == 0


# ---------------------------------------------------------------------------
# hygiene (prompt_hygiene): the eight prompts
# ---------------------------------------------------------------------------

#: The words the eight prompts use as examples (labels in quotes).
SPLIT_EXAMPLE_WORDS = ("octagonal", "alkaline", "adjacent", "former", "accustomed", "northern", "unusual", "special",
                       "hot-headed", "chatty", "breezy", "salty", "long-winded")
#: Words of the eight prompts that are corpus labels, queue entries or validation-file words.  The
#: prompts are Roger's text and are not changed here; each hit is recorded, and a new one fails.
#: "cheerful" is also an example (alignment.md: "being cheerful or long-winded") and "casual",
#: "resentful" and "cheerful" appear in the example readings of check_same_sense.md: QUESTIONS.md 22.
SPLIT_PROSE_RECORDED = {
    "sense": {"clear"}, "established": {"mean"}, "vague": {"hot", "vague"}, "kind": {"just", "single"},
    "same_sense": {"casual", "cheerful", "resentful"}, "gloss": set(), "alignment": {"cheerful"},
    "descriptors": set(),
}
#: Example words known to collide (recorded above, QUESTIONS.md 22).
SPLIT_EXAMPLE_RECORDED = {"cheerful"}


def _forbidden():
    import data_analysis.seed_entities as se
    data = REPO / "data"
    q = se.load_queue(data / "seed_queue.json")
    stems = set().union(*se.corpus_stems(data).values())
    stems |= {e.get("stem") for e in q["entries"]}
    stems |= {normalize_to_file_name(e["label"]) for e in q["entries"] if e.get("label")}
    val = data / "candidates" / "validation" / "m1_validation.jsonl"
    stems |= {normalize_to_file_name(json.loads(x)["surface"]) for x in val.read_text().splitlines() if x.strip()}
    return {s for s in stems if s}


def _test_words():
    p = REPO / "data" / "candidates" / "validation" / "split_test_words.jsonl"
    return {normalize_to_file_name(json.loads(x)["surface"]) for x in p.read_text().splitlines() if x.strip()}


class TestHygiene:
    def test_example_words_avoid_every_list(self):
        reserved = set(RESERVED.read_text(encoding="utf-8").split())
        bad = _forbidden() | _test_words()
        hits = [w for w in SPLIT_EXAMPLE_WORDS if w in reserved or normalize_to_file_name(w) in bad]
        assert hits == []

    def test_example_words_are_in_the_prompts(self):
        text = " ".join(sr.load_all().values())
        for w in SPLIT_EXAMPLE_WORDS + tuple(SPLIT_EXAMPLE_RECORDED):
            assert w in text, w

    def test_prompt_words_against_the_corpus_queue_and_validation_file(self):
        from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
        forbidden = _forbidden()
        got = {name: {w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden
                      and w not in PROSE_ALLOWED}
               for name, text in sr.load_all().items()}
        assert got == SPLIT_PROSE_RECORDED

    def test_no_test_word_is_an_example(self):
        """The 99 test words may appear in prose ("common", "false"), never as a quoted example."""
        tw = _test_words()
        for name, text in sr.load_all().items():
            for w in tw:
                assert f'"You are {w}."' not in text and f'"{w}"' not in text, (name, w)
