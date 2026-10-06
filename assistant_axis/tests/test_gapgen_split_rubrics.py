"""The split filter's prompts and their pins (coding_plan_split.md section 8, test 1), and the word
hygiene of the eight prompts (prompt_hygiene).  Since 2026-10-03 also the two M3 overlap rubrics,
which share the rubric directory and its pins (TestOverlapPins, TestOverlapHygiene)."""
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
#: The texts Roger approved on 2026-09-30 (gloss draft 3; same_sense and alignment draft 2, which
#: answered QUESTIONS.md 22), as sent by probe_rubric_edits/<name>/run.json.
#: alignment draft 3 is the graded check (0 to 3), as sent by probe_alignment_graded/draft4_corpus.
RECORDED_2026_09_30 = [
    ("gloss", 3, "bcc278479f04048e2fcaecb3c531d0dd61c93399828d6279498f71a1e5a3bc3d"),
    ("same_sense", 2, "d5953c971690915e815576337879fc26def74086e34cc4996e997e58643fa3c8"),
    ("alignment", 2, "4dbe7f7e55e667e8978f568bc927c9e005b9be13b9e4e19877d5609d7785c8f4"),
    ("alignment", 3, "c46c2e8f7e124b22db124d043655189ca123c607234e2d47436e188e3b0c34a4"),
]


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

    def test_later_rows_are_the_texts_of_the_edit_runs(self):
        """The drafts Roger approved on 2026-09-30, each run once on its earlier inputs; the hashes
        are those of probe_rubric_edits/<name>/run.json."""
        rows = sr.read_versions()["prompts"]
        for name, v, sha in RECORDED_2026_09_30:
            got = {r["version"]: r["sha256"] for r in rows[name]}
            assert got.get(v) == sha, name

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

#: The words the eight prompts use as examples: labels in quotes, and the words of the example
#: readings in check_same_sense.md and the example traits in alignment.md.  "idle", "chipper",
#: "informal" and "embittered" replaced "casual", "cheerful" and "resentful" (same_sense draft 2,
#: alignment draft 2; QUESTIONS.md 22, answered by Roger 2026-09-30).  Established drafts 5 and 6
#: (2026-10-01) carried sentence-test examples ("wordy", then "plainspoken", and "porous"); draft 7 dropped them.
SPLIT_EXAMPLE_WORDS = ("octagonal", "alkaline", "adjacent", "former", "accustomed", "northern", "unusual", "special",
                       "hot-headed", "chatty", "breezy", "salty", "long-winded", "idle", "chipper", "informal",
                       "embittered")
#: Words of the eight prompts that are corpus labels, queue entries or validation-file words.  The
#: prompts are Roger's text and are not changed here; each hit is recorded, and a new one fails.
#: Every remaining hit is ordinary prose, which the hygiene rule allows.  "serious" came with
#: alignment.md draft 3 ("avoiding serious harm", "doing serious harm"; reported to the coordinator
#: 2026-09-30, prompt unchanged).
SPLIT_PROSE_RECORDED = {
    "sense": {"clear"}, "established": {"mean"}, "vague": {"hot", "vague"}, "kind": {"just", "single"},
    "same_sense": set(), "gloss": set(), "alignment": {"serious"}, "descriptors": set(),
}
#: The example descriptions of alignment.md draft 3.
SPLIT_EXAMPLE_PHRASES = ("telling those in charge whatever they want to hear", "cutting corners to finish sooner")
#: Example words known to collide: none since QUESTIONS.md 22 was answered.
SPLIT_EXAMPLE_RECORDED: set = set()


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


class TestOverlapPins:
    """The M3 overlap rubrics (signed off by Roger 2026-10-03 as draft 2 of m3_overlap_rubric_draft.md,
    commit 45f2aa7) live beside the split prompts and share their pins, but are not split prompts."""

    #: sha256 of the two fenced blocks of m3_overlap_rubric_draft.md at commit 45f2aa7 (draft 2)
    DRAFT2 = {"overlap_concept": "2f650bffa3d614c0498be0b4814af05d840d7952fc1e943b89492b6ec647b8ab",
              "overlap_cooccurrence": "1dd2837269e8031be2bd93509beb090c9a226a683aa6cfce840c510f013d1838"}
    #: The arms of the overlap rubric arms experiment (coding_plan_overlap_arms.md, 2026-10-04): rubrics C,
    #: D and E, variants of A, first pinned as version 1.
    ARMS = ("overlap_six", "overlap_relation", "overlap_scope")
    #: Round 2 of that experiment (same day): A2, C2, D2 and E2, each a round-1 rubric (its parent here) with
    #: only its 2 and 3 lines replaced (D2: "contains" and "overlap"), first pinned as version 1.
    ROUND2 = {"overlap_concept_implies": ("overlap_concept", ("- 3:", "- 2:")),
              "overlap_six_implies": ("overlap_six", ("- 3:", "- 2:")),
              "overlap_relation_implies": ("overlap_relation", ('- "contains":', '- "overlap":')),
              "overlap_scope_implies": ("overlap_scope", ("- 3:", "- 2:"))}

    #: Rubric A's text at version 4 (draft 2's, the text the arms experiment branched from), kept as a
    #: fixture since A moved on to one pair per call (drafts 5 and 6, 2026-10-06); checked against the pin.
    V4_FIXTURE = REPO / "assistant_axis" / "tests" / "fixtures" / "overlap_concept_v4.txt"

    def rubric_a_version_4(self) -> str:
        text = self.V4_FIXTURE.read_text(encoding="utf-8").rstrip("\n")
        rows = sr.read_versions()["prompts"]["overlap_concept"]
        v4 = next(r for r in rows if r["version"] == 4)
        assert sr.sha256(text) == v4["sha256"] == self.DRAFT2["overlap_concept"]
        return text

    def parent_text(self, name: str) -> str:
        """A round-2 rubric's parent as it was when round 2 branched: version 4 for rubric A."""
        return self.rubric_a_version_4() if name == "overlap_concept" else sr.load_prompt(name)

    def test_overlap_rubrics_are_not_split_prompts(self):
        # A and B (draft 2), since 2026-10-04 the three arms C, D and E, and round 2's A2, C2, D2 and E2
        assert set(sr.OVERLAP_NAMES) == set(self.DRAFT2) | set(self.ARMS) | set(self.ROUND2)
        assert not set(sr.OVERLAP_NAMES) & set(sr.NAMES)
        assert set(sr.load_all()) == set(sr.NAMES)          # the split runner's eight, unchanged
        assert set(sr.current_versions()) == set(sr.NAMES)  # what a split block stamps as step_versions
        assert set(sr.current_versions(names=sr.OVERLAP_NAMES)) == set(sr.OVERLAP_NAMES)
        assert set(sr.PINNED_NAMES) == set(sr.NAMES) | set(sr.OVERLAP_NAMES)

    def test_first_pin_is_draft_2_as_signed_off(self):
        rows = sr.read_versions()["prompts"]
        for name, sha in self.DRAFT2.items():
            first = rows[name][0]
            assert (first["version"], first["sha256"]) == (2, sha), name
            # the text on disk is the latest pin (rubric A: draft 3, then back to draft 2's text as version 4, 2026-10-03)
            assert sr.sha256(sr.load_prompt(name)) == rows[name][-1]["sha256"], name

    def test_the_arms_are_first_pinned_as_version_1(self):
        rows = sr.read_versions()["prompts"]
        for name in self.ARMS:
            assert rows[name][0]["version"] == 1, name
            assert sr.sha256(sr.load_prompt(name)) == rows[name][-1]["sha256"], name

    def test_the_arms_are_rubric_a_with_only_the_named_lines_changed(self):
        """coding_plan_overlap_arms.md: C replaces A's scale lines (and writes the answer's scale 0-5), E
        replaces line 3, D replaces the opening's question, the scale lines and the answer format; every
        other byte is A's as it was then (version 4, draft 2's text, kept as a fixture since rubric A moved
        on to one pair per call on 2026-10-06)."""
        a = self.rubric_a_version_4()
        lines = a.split("\n")
        start = lines.index("Give one of these answers for each listed trait:")
        end = next(i for i, ln in enumerate(lines) if ln.startswith('- "unsure"'))
        a_scale = "\n".join(lines[start:end + 1])
        c, d, e = (sr.load_prompt(n) for n in self.ARMS)
        c_scale = "\n".join(c.split("\n")[start:end + 2])          # one line more: six rungs
        assert c == a.replace(a_scale, c_scale).replace("0|1|2|3|4|", "0|1|2|3|4|5|")
        assert c_scale.split("\n")[1].startswith("- 5: the same concept.")
        line3 = next(ln for ln in lines if ln.startswith("- 3:"))
        e3 = next(ln for ln in e.split("\n") if ln.startswith("- 3:"))
        assert e == a.replace(line3, e3) and e3.endswith("narrowed, broadened, stronger, milder, or a shift of emphasis.")
        head, second = a.split("\n\n")[:2]
        d_head = head.split(" For each listed trait,")[0] + " For each listed trait, say how its concept is related to the target's."
        assert d.startswith(d_head + "\n\n" + second + "\n\nGive one of these answers for each listed trait:\n")
        assert '"relation": "same"|"variant"|"contains"' in d and '"wider": "target"|"listed"' in d

    def test_round_2_is_first_pinned_as_version_1(self):
        rows = sr.read_versions()["prompts"]
        for name in self.ROUND2:
            assert rows[name][0]["version"] == 1, name
            assert sr.sha256(sr.load_prompt(name)) == rows[name][-1]["sha256"], name

    def test_round_2_is_round_1_with_only_the_named_lines_changed(self):
        """coding_plan_overlap_arms.md, "Round 2": each new rubric is its round-1 parent with only the quoted
        lines replaced; every other scale line and the answer format stay byte for byte."""
        for name, (parent, prefixes) in self.ROUND2.items():
            old, new = self.parent_text(parent).split("\n"), sr.load_prompt(name).split("\n")
            assert len(old) == len(new), name
            changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
            assert sorted(old[i].split(":", 1)[0] + ":" for i in changed) == sorted(prefixes), name
            for i in changed:
                assert new[i].startswith(old[i].split(":", 1)[0] + ":"), (name, i)
            text = sr.load_prompt(name)
            line2 = next(ln for ln in new if ln.startswith(prefixes[1]))
            assert "neither implies the other" in line2, name
            assert "a fussy eater is fussy, a boastful person is proud" in text, name
        # the shared line 2 (D2's "overlap") is word for word the same on every form
        twos = {next(ln for ln in sr.load_prompt(n).split("\n") if ln.startswith(p[1])).split(":", 1)[1]
                for n, (_, p) in self.ROUND2.items()}
        assert len(twos) == 1
        # E2's line 3 is Roger's line 3 with the test sentence inserted, the rest of it unchanged
        e3 = next(ln for ln in sr.load_prompt("overlap_scope").split("\n") if ln.startswith("- 3:"))
        e23 = next(ln for ln in sr.load_prompt("overlap_scope_implies").split("\n") if ln.startswith("- 3:"))
        test = ("The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy "
                "eater is fussy, a boastful person is proud, though not necessarily the reverse. ")
        assert e23.replace(test, "") == e3

    def test_files_and_mismatches(self):
        assert sr.rubric_path("overlap_concept").name == "overlap_concept.md"
        assert sr.rubric_path("overlap_cooccurrence").name == "overlap_cooccurrence.md"
        assert sr.rubric_path("overlap_six").name == "overlap_six.md"
        assert sr.rubric_path("overlap_relation").name == "overlap_relation.md"
        assert sr.rubric_path("overlap_scope").name == "overlap_scope.md"
        for name in self.ROUND2:
            assert sr.rubric_path(name).name == f"{name}.md"
        assert sr.mismatches() == []

    def test_a_changed_overlap_text_is_a_mismatch(self, tmp_path):
        d = tmp_path / "rubrics"
        shutil.copytree(paths.RUBRICS_DIR, d, ignore=shutil.ignore_patterns("README.md"))
        p = d / sr.PINNED_FILES["overlap_concept"]
        p.write_text(p.read_text(encoding="utf-8").replace("For example, talkative and loquacious.",
                                                            "For example, talkative and garrulous.", 1),
                     encoding="utf-8")
        probs = sr.mismatches(d)
        assert len(probs) == 1 and probs[0].startswith("overlap_concept: text changed")
        assert "rubric_pins.py bump overlap_concept" in sr.bump_command(probs)
        before = json.loads((d / "versions.json").read_text(encoding="utf-8"))["prompts"]["overlap_concept"][-1]["version"]
        row = sr.bump("overlap_concept", "test edit", now="t", rubrics_dir=d)
        assert row["version"] == before + 1 and sr.mismatches(d) == []

    def test_going_back_to_an_earlier_text_needs_revert_to(self, tmp_path):
        """A revert is pinned as the next version, marked with the version whose text it is."""
        d = tmp_path / "rubrics"
        shutil.copytree(paths.RUBRICS_DIR, d, ignore=shutil.ignore_patterns("README.md"))
        p = d / sr.PINNED_FILES["overlap_cooccurrence"]
        original = p.read_text(encoding="utf-8")
        p.write_text(original.replace("Return one row per listed trait", "Return one row for each listed trait", 1),
                     encoding="utf-8")
        edited = sr.bump("overlap_cooccurrence", "test edit", now="t", rubrics_dir=d)
        p.write_text(original, encoding="utf-8")                      # back to the earlier text
        first = sr.read_versions(d)["prompts"]["overlap_cooccurrence"][0]["version"]
        with pytest.raises(ValueError, match=f"--revert-to {first}"):
            sr.bump("overlap_cooccurrence", "revert", now="t", rubrics_dir=d)
        with pytest.raises(ValueError, match="not version"):
            sr.bump("overlap_cooccurrence", "revert", now="t", rubrics_dir=d, revert_to=edited["version"])
        row = sr.bump("overlap_cooccurrence", "revert", now="t", rubrics_dir=d, revert_to=first)
        assert row["version"] == edited["version"] + 1 and row["same_text_as"] == first
        assert sr.mismatches(d) == []
        assert sr.current_versions(d, sr.OVERLAP_NAMES)["overlap_cooccurrence"][0] == row["version"]

    def test_rubric_pins_cli_knows_the_overlap_rubrics(self, capsys):
        from data_analysis.gap_generation import rubric_pins
        assert rubric_pins.main(["check"]) == 0
        out = capsys.readouterr().out
        assert "overlap_concept" in out and "overlap_cooccurrence" in out
        assert all(name in out for name in self.ARMS)
        assert all(name in out for name in self.ROUND2)


#: The example words of the overlap rubrics: the pairs on rubric A's scale and in its second paragraph,
#: rubric B's (B adds outdoorsy), and the arms C, D and E (2026-10-04), which add fussy and fussy eater
#: (checked free that day: picky eater is the corpus's label; fussy eater is its near-duplicate, as the
#: hygiene rule wants); round 2 (same day) adds proud and boastful (checked free of the corpus that day).
OVERLAP_EXAMPLE_WORDS = ("punctual", "tidy", "talkative", "loquacious", "penny-pinching", "miserly", "studious",
                         "bookish", "tetchy", "sullen", "chatty", "plainspoken", "cheery", "morose", "outdoorsy",
                         "fussy", "fussy eater", "proud", "boastful")
#: Example words known to collide, with where.  Round 2's proud and boastful are free of the corpus, the
#: queue and the validation file, as the brief checked, but both are on the reserved-word list built from
#: decisions_m1.md and the "You are X." probe: proud is one of the probe's words with two person senses
#: (Roger: "I just see the arrogant sense"), boastful is in decisions_m1.md's glosses ("modest and not
#: boastful").  The round-2 texts are final for the experiment and are not changed here (no corpus trait is
#: either word, so no judged pair contains one); each hit is recorded, and a new one fails.  A round-2
#: wording taken into production would need other examples if either word can be an M3 candidate.
OVERLAP_EXAMPLE_RECORDED = {"proud": "reserved: decisions_m1.md and the You are X. probe (two person senses)",
                            "boastful": "reserved: decisions_m1.md glosses"}
#: Words of the overlap prompts that are corpus labels, queue entries or validation-file words and are
#: not already allowed as prose: none at draft 2 of A and B; "single" in the arms' "narrowed to a single
#: domain" (prose, as in the split filter's kind prompt; the texts are final for the experiment), kept by
#: round 2's C2, D2 and E2 (A2 says "narrowed to a domain").
OVERLAP_PROSE_RECORDED = {"overlap_concept": set(), "overlap_cooccurrence": set(), "overlap_six": {"single"},
                          "overlap_relation": {"single"}, "overlap_scope": {"single"},
                          "overlap_concept_implies": set(), "overlap_six_implies": {"single"},
                          "overlap_relation_implies": {"single"}, "overlap_scope_implies": {"single"}}


class TestOverlapHygiene:
    def test_example_words_avoid_every_list(self):
        """Every example word avoids every list, except the recorded collisions (OVERLAP_EXAMPLE_RECORDED:
        until round 2, none); a new collision fails, and so does a recorded one that no longer collides."""
        reserved = set(RESERVED.read_text(encoding="utf-8").split())
        bad = _forbidden() | _test_words()
        hits = [w for w in OVERLAP_EXAMPLE_WORDS if w in reserved or normalize_to_file_name(w) in bad]
        assert set(hits) == set(OVERLAP_EXAMPLE_RECORDED)
        # the recorded ones collide with the reserved list only, never with the corpus, queue or validation file
        assert not any(normalize_to_file_name(w) in bad for w in OVERLAP_EXAMPLE_RECORDED)

    def test_example_words_are_in_the_prompts(self):
        a, b = sr.load_prompt("overlap_concept"), sr.load_prompt("overlap_cooccurrence")
        every = "".join(sr.load_prompt(name) for name in sr.OVERLAP_NAMES)
        for w in OVERLAP_EXAMPLE_WORDS:
            assert w in every, w
        assert "outdoorsy" in b and "outdoorsy" not in a   # A's answer-0 example changed in draft 2
        for name in ("overlap_six", "overlap_relation", "overlap_scope"):
            assert "fussy and fussy eater" in sr.load_prompt(name), name
        for name in ("overlap_concept_implies", "overlap_six_implies", "overlap_relation_implies",
                     "overlap_scope_implies"):
            assert "a boastful person is proud" in sr.load_prompt(name), name

    def test_prompt_words_against_the_corpus_queue_and_validation_file(self):
        from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
        forbidden = _forbidden() | _test_words()
        got = {name: {w for w in prompt_words(sr.load_prompt(name)) if normalize_to_file_name(w) in forbidden
                      and w not in PROSE_ALLOWED}
               for name in sr.OVERLAP_NAMES}
        assert got == OVERLAP_PROSE_RECORDED

    def test_no_test_word_or_prose_word_is_an_example(self):
        from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED
        tw = _test_words()
        for name in sr.OVERLAP_NAMES:
            text = sr.load_prompt(name)
            for w in tw | set(PROSE_ALLOWED):
                for form in (f"{w} and ", f" and {w}.", f" and {w},", f"a {w} persona", f"be {w}."):
                    assert form not in text, (name, w, form)


class TestHygiene:
    def test_example_words_avoid_every_list(self):
        reserved = set(RESERVED.read_text(encoding="utf-8").split())
        bad = _forbidden() | _test_words()
        hits = [w for w in SPLIT_EXAMPLE_WORDS if w in reserved or normalize_to_file_name(w) in bad]
        assert hits == []

    def test_example_phrases_avoid_every_list(self):
        """The content words of alignment.md's example descriptions (as the prose check reads them):
        none a corpus label, queue entry, validation word or one of the 99 test words."""
        from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
        bad = _forbidden() | _test_words()
        text = sr.load_prompt("alignment")
        for phrase in SPLIT_EXAMPLE_PHRASES:
            assert phrase in text, phrase
            hits = [w for w in prompt_words(phrase) if normalize_to_file_name(w) in bad and w not in PROSE_ALLOWED]
            assert hits == [], (phrase, hits)

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
