"""Alignment sweep: the mechanical measures the extraction prompt is iterated on (plan 08 § 10, the pilot's
decision 1).  No network and no API: every input is a hand-written :class:`Item`."""
from __future__ import annotations

from assistant_axis.gapgen.generators.alignment_sweep import measure as M
from assistant_axis.gapgen.generators.alignment_sweep.extract import Item

CORPUS_GLOSS = ("This means saying only what one believes to be true, even when a smoother falsehood would "
                "please the listener more and cost nothing.")
FIRST_PERSON = ("This means I say only what I believe to be true, even when a smoother falsehood would please "
                "the listener more and cost me nothing.")


def item(item_id, label, gloss, *, pole="virtue", partner=None, names_source=True, chunk="model_spec:v:c",
         rank=1, dropped=None, type_="behaviour"):
    return Item(item_id=item_id, chunk_id=chunk, source="model_spec", label=label, stem=label.replace(" ", "_"),
                gloss=gloss, partner_label=None, partner_item_id=partner, pole=pole, names_source=names_source,
                type=type_, enactability="chat", label_kind="ordinary", polysemy_flag=False, polysemy_note=None,
                source_quote="q", rank=rank, source_weight=2.0, dropped_reason=dropped)


def pair(base, v_label, v_gloss, c_label, c_gloss, *, rank=1, chunk="model_spec:v:c"):
    """A virtue pole (the one the passage names) and its vice partner."""
    return [item(base + "a", v_label, v_gloss, pole="virtue", partner=base + "b", names_source=True, rank=rank,
                 chunk=chunk),
            item(base + "b", c_label, c_gloss, pole="vice", partner=base + "a", names_source=False, rank=rank,
                 chunk=chunk)]


# --------------------------------------------------------------------------- volume


def test_volume_counts_pairs_per_chunk_and_label_lengths():
    items = pair("p1-1", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS, chunk="a:v:1")
    items += pair("p1-2", "keeps promises", CORPUS_GLOSS, "breaks promises", CORPUS_GLOSS, rank=2, chunk="a:v:1")
    items += pair("p2-1", "patient", CORPUS_GLOSS, "snaps at people", CORPUS_GLOSS, rank=3, chunk="a:v:2")
    v = M.volume(items, n_chunks=4)
    assert v["n_pairs"] == 3 and v["n_kept_poles"] == 6
    assert v["pairs_per_chunk"] == 0.75                      # 3 pairs over the 4 chunks the run sent
    assert v["pairs_per_answered_chunk"] == 1.5              # over the 2 chunks that gave items
    assert v["label_words"] == {"1": 2, "2": 3, "3": 1}
    assert v["one_word_label_share"] == round(2 / 6, 4)


def test_volume_ignores_dropped_poles_in_the_label_counts():
    items = pair("p1-1", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS)
    items[1].dropped_reason = "enactability none"
    v = M.volume(items, n_chunks=1)
    assert v["n_kept_poles"] == 1 and v["label_words"] == {"1": 1}


# --------------------------------------------------------------------------- gloss form


def test_gloss_problems_names_each_fault():
    assert M.gloss_problems(CORPUS_GLOSS) == []
    # draft 1's shape: the subject sits where the -ing verb belongs, so both faults are named
    assert M.gloss_problems(FIRST_PERSON) == ["no -ing verb after This means", "has a subject"]
    assert M.gloss_problems("This means keeping to what I believe is true, however much it disappoints.") == \
        ["has a subject"]
    assert M.gloss_problems("This means that one holds to the truth at every turn, whatever it costs.") == \
        ["no -ing verb after This means"]
    assert M.gloss_problems("Someone like this says only true things.") == ["no This means"]
    assert M.gloss_problems("This means exhibiting a preference for the truth over a smoother answer.") == \
        ["report vocabulary"]
    assert M.gloss_problems("This means the assistant saying only what it believes to be true.") == \
        ["names the persona"]
    assert M.gloss_problems("You say only what you believe.") == ["no This means", "has a subject"]


def test_gloss_problems_calibrated_on_the_corpus_form():
    """The checks pass what the corpus itself writes: an adverb or a negation before the -ing verb, and a
    third-person pronoun for *other people* (114 of the 932 descriptions have one)."""
    for ok in ("This means readily adjusting one's approach to meet other people's needs and keep the peace.",
               "This means never paying full price, comparing stores, clipping coupons and waiting for the sale.",
               "This means not caring how things turn out, taking no interest in the matter or in the people.",
               "This means judging people by their age first: the old written off, the young as green.",
               "This means taking people at their word and dealing straight, helping before being asked."):
        assert M.gloss_problems(ok) == [], ok


def test_gloss_form_shares():
    items = pair("p1-1", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS)
    items += pair("p1-2", "patient", FIRST_PERSON, "snappy", CORPUS_GLOSS, rank=2)
    g = M.gloss_form(items)
    assert g["n_poles"] == 4 and g["n_corpus_form"] == 3 and g["corpus_form_share"] == 0.75
    assert g["first_person"] == 1
    assert g["why_not"] == {"no -ing verb after This means": 1, "has a subject": 1}


# --------------------------------------------------------------------------- label shape


def test_label_step_tells():
    assert M.label_step_tells("candid") == []
    assert M.label_step_tells("keeps promises") == []
    assert M.label_step_tells("asks before expanding") == ["procedure verb", "sequencing word"]
    assert M.label_step_tells("cites sources") == ["procedure verb"]
    assert M.label_step_tells("confirms plan first") == ["procedure verb", "sequencing word"]
    assert M.label_step_tells("thinks before speaking") == ["sequencing word"]


def test_label_shape_share_and_listing():
    items = pair("p1-1", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS)
    items += pair("p1-2", "cites sources", CORPUS_GLOSS, "invents sources", CORPUS_GLOSS, rank=2)
    s = M.label_shape(items)
    assert s["n_poles"] == 4 and s["n_step_shaped"] == 1 and s["disposition_share"] == 0.75
    assert s["step_labels"] == ["cites sources"] and s["why"] == {"procedure verb": 1}


# --------------------------------------------------------------------------- vice shape


def test_is_absence_catches_a_negated_echo_of_the_virtue():
    virtue = item("x1a", "names its sources", "This means naming the book or page a detail came from whenever "
                                              "giving someone a fact about another person.", partner="x1b")
    absence = item("x1b", "gives unsourced details", "This means giving someone a fact about another person "
                                                     "without naming the book or page it came from.",
                   pole="vice", partner="x1a", names_source=False)
    behavior = item("x1b", "makes up a source", "This means inventing a plausible book or page for a fact about "
                                                "another person, so the detail looks checked.",
                    pole="vice", partner="x1a", names_source=False)
    assert M.is_absence(absence, virtue) == "gloss negates and otherwise repeats the virtue's"
    assert M.is_absence(behavior, virtue) is None


def test_is_absence_catches_a_negation_label():
    virtue = item("x1a", "candid", CORPUS_GLOSS, partner="x1b")
    for label in ("not candid", "never candid", "fails to answer"):
        v = item("x1b", label, "This means dodging the question with a story that sounds like an answer.",
                 pole="vice", partner="x1a", names_source=False)
        assert M.is_absence(v, virtue) == "label is a negation", label


def test_vice_shape_counts_absences_and_or_joined_poles():
    items = pair("p1-1", "names its sources",
                 "This means naming the book or page a detail came from whenever giving someone a fact.",
                 "gives unsourced details",
                 "This means giving someone a fact about another person without naming the book or page it came "
                 "from.")
    items += pair("p1-2", "owns up to a gap",
                  "This means saying plainly where one's knowledge runs out, and what would be needed to answer.",
                  "bluffs or shuts down",
                  "This means inventing a confident answer, or refusing the question outright, when the facts "
                  "run thin.", rank=2)
    s = M.vice_shape(items)
    assert s["n_vices"] == 2 and s["n_absence_shaped"] == 1
    assert s["beyond_absence_share"] == 0.5
    assert s["absence_labels"] == ["gives unsourced details"]
    assert s["n_or_joined_labels"] == 1 and s["or_joined_labels"] == ["bluffs or shuts down"]
    assert s["joined_share"] == 0.25                                       # 1 of the 4 kept poles


def test_vice_shape_counts_a_label_joining_two_qualities_with_and():
    """Draft 2's grouping instruction made the model bundle two qualities into one pole, which the count tracks."""
    items = pair("p1-1", "warm and honest", CORPUS_GLOSS, "cold and dismissive", CORPUS_GLOSS)
    s = M.vice_shape(items)
    assert s["n_or_joined_labels"] == 2 and s["joined_share"] == 1.0
    assert s["or_joined_labels"] == ["cold and dismissive", "warm and honest"]


# --------------------------------------------------------------------------- near duplicates


def test_near_duplicates_group_by_head_word_and_overlap():
    items = pair("p1-1", "respects human autonomy", CORPUS_GLOSS, "overrides people", CORPUS_GLOSS, chunk="a:v:1")
    items += pair("p1-2", "respects user autonomy", CORPUS_GLOSS, "decides for people", CORPUS_GLOSS, rank=2,
                  chunk="a:v:1")
    items += pair("p1-3", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS, rank=3, chunk="a:v:2")
    d = M.near_duplicates(items)
    assert d["n_poles"] == 6 and d["n_groups"] == 1 and d["n_duplicate_poles"] == 1
    assert d["duplicate_share"] == round(1 / 6, 4)
    assert sorted(d["groups"][0]["labels"]) == ["respects human autonomy", "respects user autonomy"]
    # both came out of one call, so this duplicate is the prompt's fault
    assert d["groups"][0]["within_chunk"] is True and d["n_within_chunk"] == 1


def test_near_duplicates_separate_a_cross_chunk_duplicate():
    """One call never sees another's items, so a duplicate across chunks is dedup's job, not the prompt's."""
    items = pair("p1-1", "keeps promises", CORPUS_GLOSS, "breaks promises", CORPUS_GLOSS, chunk="a:v:1")
    items += pair("p2-1", "keeps promises", CORPUS_GLOSS, "goes back on a word", CORPUS_GLOSS, chunk="a:v:2")
    d = M.near_duplicates(items)
    assert d["n_duplicate_poles"] == 1 and d["n_within_chunk"] == 0
    assert d["groups"][0]["within_chunk"] is False


def test_near_duplicates_never_group_a_virtue_with_a_vice():
    items = pair("p1-1", "respects privacy", CORPUS_GLOSS, "respects privacy", CORPUS_GLOSS)
    d = M.near_duplicates(items)
    assert d["n_groups"] == 0 and d["n_duplicate_poles"] == 0


# --------------------------------------------------------------------------- the whole round and the table


def test_measure_all_and_round_table():
    items = pair("p1-1", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS)
    items += pair("p1-2", "cites sources", FIRST_PERSON, "invents sources", FIRST_PERSON, rank=2)
    summary = {"n_chunks": 2, "n_chunks_answered": 2, "unparsed": {}, "n_invalid_items": 0,
               "cost_usd_this_session": 0.1234, "rubrics": {"alignment_extract": {"version": 2}}}
    m = M.measure_all(items, n_chunks=2, summary=summary)
    assert m["run"] == {"n_chunks_answered": 2, "n_unparsed": 0, "parse_rate": 1.0, "n_invalid_items": 0,
                        "cost_usd": 0.1234, "rubric_version": 2}
    table = M.round_table([("draft 1", m)], target={"pairs per chunk (a)": "1-2.5"})
    assert "| measure | draft 1 | wanted |" in table
    assert "| pairs per chunk (a) | 1.00 | 1-2.5 |" in table
    assert "| glosses in corpus form (b) | 50% |" in table
    assert "| cost (f) | $0.123 |" in table
    assert "| rubric version | 2 |" in table


def test_gloss_dedup_reads_the_recorded_groups():
    """``dedup_groups.json`` is the measure of record for (e): what the gloss embeddings merged at the threshold
    tuned on the hand-labelled pairs."""
    items = pair("p1-1", "candid", CORPUS_GLOSS, "glib liar", CORPUS_GLOSS)
    items += pair("p1-2", "patient", CORPUS_GLOSS, "snappy", CORPUS_GLOSS, rank=2)
    doc = {"result": {"threshold": 0.8117,
                      "groups": [{"rep": "p1-1a", "members": ["p1-1a", "p1-2a"], "note": "exact stem"},
                                 {"rep": "p1-1b", "members": ["p1-1b"], "note": ""},
                                 {"rep": "p1-2b", "members": ["p1-2b"], "note": ""}]}}
    d = M.gloss_dedup(doc, items)
    assert d == {"threshold": 0.8117, "n_kept_poles": 4, "n_groups": 3, "n_merged": 1,
                 "merged_share": 0.25, "n_exact_stem_groups": 1}
    m = M.measure_all(items, n_chunks=1, groups_doc=doc)
    assert "| merged by the gloss dedup (e) | 25% |" in M.round_table([("r", m)])


def test_round_table_prints_a_dash_for_a_missing_number():
    m = M.measure_all([], n_chunks=0)
    table = M.round_table([("empty", m)])
    assert "| pairs per chunk (a) | - |" in table and "| cost (f) | - |" in table


def test_sample_pairs_is_seeded_and_returns_both_poles():
    items = []
    for i in range(10):
        items += pair(f"p1-{i}", f"label {i} one", CORPUS_GLOSS, f"vice {i} two", CORPUS_GLOSS, rank=i + 1)
    got = M.sample_pairs(items, 4, seed=7)
    assert len(got) == 4 and all(a.names_source and not b.names_source for a, b in got)
    assert [a.item_id for a, _ in got] == [a.item_id for a, _ in M.sample_pairs(items, 4, seed=7)]
    assert M.sample_pairs(items, 99) == M.sample_pairs(items, 10)
