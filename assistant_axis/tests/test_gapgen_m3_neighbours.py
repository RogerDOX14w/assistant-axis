"""The marking sheets' neighbours (QUESTIONS 208 (4), Roger 2026-10-20): every corpus trait and seed-queue entry M3
compared a candidate with, as the review app's corpus panel lists them, and a queue entry shown as queued, never
linked as a trait file."""
from __future__ import annotations

import json

from assistant_axis.gapgen import m3_neighbours as MN


def _row():
    return {"key": "macho#1", "stem": "macho", "label": "macho", "filter": {"verdict": "trait"}, "novelty": {
        "decision": "new",
        "listed": [{"stem": "muscular", "cosine": 0.41, "relation": "similar"},
                   {"stem": "overmasculine", "cosine": 0.36, "relation": "similar", "queue_status": "candidate"},
                   {"stem": "intense", "cosine": 0.30, "relation": "similar"},
                   {"stem": "quiet", "cosine": 0.28, "relation": "unrelated"},
                   {"stem": "dainty", "cosine": 0.27, "relation": "opposed"},
                   {"stem": "bold", "cosine": 0.20, "relation": "similar"}],
        "readings": [{"position": 1, "stem": "muscular", "sonnet": {"value": 1}},
                     {"position": 2, "stem": "overmasculine", "sonnet": {"value": 3}, "opus": {"value": 2}},
                     {"position": 3, "stem": "intense", "sonnet": {"value": 1}},
                     {"position": 4, "stem": "bold", "sonnet": {"value": 2}, "opus": {"value": 3}}]}}


def test_every_compared_trait_in_the_review_apps_order():
    ns = MN.neighbours(_row())
    # final reading (Opus's, else Sonnet's) then cosine; unread last; the opposed one apart
    assert [n.stem for n in ns] == ["bold", "overmasculine", "muscular", "intense", "quiet"]
    assert [n.reading_text for n in ns] == ["2/3", "3/2", "1/-", "1/-", None]
    assert ns[1].kind == "queue" and ns[0].kind == "corpus"
    assert [n.stem for n in MN.neighbours(_row(), opposed=True)] == ["dainty"]
    assert ns[0].best == 3 and ns[0].final == 3 and ns[1].best == 3 and ns[1].final == 2


def test_the_text_marks_a_queue_entry_queued_and_never_links_it(tmp_path):
    (tmp_path / "bold.json").write_text("{}")
    (tmp_path / "muscular.json").write_text("{}")
    (tmp_path / "quiet.json").write_text("{}")
    text = MN.neighbours_text(_row(), href=MN.trait_href("../t/", tmp_path))
    assert text == ("[bold](../t/bold.json) (2/3), overmasculine (queued, 3/2), [muscular](../t/muscular.json) (1/-), "
                    "intense (no trait file) (1/-), [quiet](../t/quiet.json) (unrelated)")
    assert "overmasculine.json" not in text
    assert MN.neighbours_text({"novelty": {}}, href=MN.trait_href("../t/")) == "none read"


def test_the_llm_entropy_sheet_shows_the_full_list(tmp_path):
    from assistant_axis.gapgen.generators.llm_entropy import report as RP
    row = dict(_row(), sources=[{"generator": "llm_entropy", "run_id": "R", "source_ref": "llm_entropy:a:body:social:r1"}],
               gloss="This means acting tough.")
    (tmp_path / "bold.json").write_text("{}")
    md = RP.roger_sample([row], [], run_id="R", n=5, trait_prefix="../t/", traits_dir=tmp_path)
    line = next(x for x in md.splitlines() if x.startswith("| 1 |"))
    assert line.startswith("| 1 |  | macho |")                         # the mark column second
    assert "[bold](../t/bold.json) (2/3), overmasculine (queued, 3/2), muscular (no trait file) (1/-)" in line
    assert "quiet (no trait file) (unrelated)" in line and "70%" not in md


def test_the_corpus_frames_sheets_show_the_full_list_with_the_mark_second(tmp_path):
    from assistant_axis.gapgen.generators.corpus_frames import report as CR
    traits = tmp_path / "data" / "traits" / "instructions"
    traits.mkdir(parents=True)
    (traits / "bold.json").write_text(json.dumps({"positive_label": "bold"}))
    doc = tmp_path / "data" / "candidates" / "runs" / "corpus_frames" / "r" / "roger_sample.md"
    rec = {"stem": "macho", "label": "macho", "decision": "new", "gloss": "g", "nearest": "muscular", "cosine": 0.41,
           "novelty": _row()["novelty"], "frames": [], "example": None, "union_rank": 1}
    for md in (CR.roger_sample([rec], doc_path=doc, run_id="r", traits_dir=traits),
               CR.roger_first_hour([rec], doc_path=doc, run_id="r", traits_dir=traits)):
        line = next(x for x in md.splitlines() if x.startswith("| 1 |"))
        assert line.startswith("| 1 |  | macho |")
        assert "[bold](../../../../traits/instructions/bold.json) (2/3), overmasculine (queued, 3/2)" in line
        assert "| T/N/D |" in md
