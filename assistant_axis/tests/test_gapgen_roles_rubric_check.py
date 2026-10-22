"""The role rubric check (coding plan 16, task 12; § 8's paid checks): the 40-pair sheet (blind to the design's sets,
the mark column second, found by its header), the marks parsed, both role rubrics read in both orders on a fake
client, and the kappa against the marks.  No API calls."""
import json
import shutil
from pathlib import Path

import pytest

from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from data_analysis.gap_generation import novelty_score as cli

REPO = Path(__file__).resolve().parents[2]


def test_the_pairs():
    assert len(RP.RUBRIC_PAIRS) == 40
    by = {}
    for a, b, k in RP.RUBRIC_PAIRS:
        by.setdefault(k, []).append((a, b))
    assert {k: len(v) for k, v in by.items()} == {"recorded_pair": 6, "sub_role": 10, "same_role": 10, "other": 14}
    have = {p.stem for p in (REPO / "data/roles/instructions").glob("*.json")}
    assert all(a in have and b in have for a, b, _ in RP.RUBRIC_PAIRS)


def test_kappa():
    assert RP.weighted_kappa([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]) == 1.0
    assert RP.weighted_kappa([0, 4], [4, 0]) < 0
    assert RP.weighted_kappa([], []) is None
    assert RP.weighted_kappa([0, 1, 2], [0, 1, 2], categories=(0, 1, 2), weights="none") == 1.0
    assert [RP.relation_of_mark(m) for m in ("4", "3", "2", "1", "0", "opposite", "unsure")] == \
        ["similar", "similar", "similar", "unrelated", "unrelated", "opposed", None]


def write_glosses(path: Path, *, skip=()) -> Path:
    """A retrieval check's ``glosses.jsonl`` for every role of the pairs (a gloss per stem; ``skip``: none)."""
    stems = sorted({x for a, b, _ in RP.RUBRIC_PAIRS for x in (a, b)} - set(skip))
    path.write_text("".join(json.dumps({"stem": st, "label": st.replace("_", " "),
                                        "gloss": f"A {st.replace('_', ' ')} is someone who does what a "
                                                 f"{st.replace('_', ' ')} does, all day.", "form_ok": True}) + "\n"
                            for st in stems) + json.dumps({"stem": "x", "gloss": None, "error": "parse"}) + "\n")
    return path


@pytest.fixture
def sheet(tmp_path):
    p = tmp_path / "role_rubric_pairs.md"
    g = write_glosses(tmp_path / "glosses.jsonl")
    assert cli.main(["rubric-check", "--make-sheet", "--pairs", str(p), "--data-dir", str(REPO / "data"),
                     "--glosses", str(g)]) == 0
    return p


def mark(sheet: Path, marks: dict) -> None:
    lines = []
    for line in sheet.read_text().splitlines():
        cells = line.split("|")
        if len(cells) > 3 and cells[1].strip() in marks:
            cells[2] = f" {marks[cells[1].strip()]} "
            line = "|".join(cells)
        lines.append(line)
    sheet.write_text("\n".join(lines) + "\n")


def test_the_sheet_is_blind_and_reads_back(sheet):
    text = sheet.read_text()
    assert "| pair | mark | target | other |" in text and "recorded_pair" not in text and "sub_role" not in text
    key = json.loads(sheet.with_name("role_rubric_pairs_key.json").read_text())
    pairs = key["pairs"]
    assert [p["pair"] for p in pairs] == [f"r{i:02d}" for i in range(1, 41)]
    assert {p["set"] for p in pairs} == {"recorded_pair", "sub_role", "same_role", "other"}
    assert cli.parse_rubric_marks(sheet) == {}
    mark(sheet, {"r01": "3", "r02": "opposite", "r03": "`2`"})
    assert cli.parse_rubric_marks(sheet) == {"r01": "3", "r02": "opposite", "r03": "2"}
    assert cli.main(["rubric-check", "--make-sheet", "--pairs", str(sheet), "--data-dir", str(REPO / "data"),
                     "--glosses", str(sheet.with_name("glosses.jsonl"))]) == 2         # marks there: refused
    mark(sheet, {"r04": "5"})
    with pytest.raises(ValueError, match="r04"):
        cli.parse_rubric_marks(sheet)


def test_the_check_on_a_fake_client(sheet, tmp_path, monkeypatch, capsys):
    import anthropic
    import dotenv
    key = json.loads(sheet.with_name("role_rubric_pairs_key.json").read_text())["pairs"]
    expected = {"recorded_pair": "opposite", "sub_role": "3", "same_role": "4", "other": "1"}
    marks = {p["pair"]: expected[p["set"]] for p in key}
    mark(sheet, marks)
    by_labels = {(p["target_label"], p["other_label"]): marks[p["pair"]] for p in key}

    def responder(kw):
        obj = json.loads(user_text(kw))
        if "candidate" in obj:
            t, o = obj["candidate"]["label"], obj["roles"][0]["label"]
            m = by_labels.get((t, o)) or by_labels.get((o, t))
            rel = {"opposite": "opposed", "3": "similar", "4": "similar", "1": "unrelated"}[m]
            return make_response(json.dumps({"results": [{"id": 1, "reason": "r", "relation": rel}]}))
        t, o = obj["target"]["label"], obj["other"]["label"]
        m = by_labels.get((t, o))
        v = (m if m == "opposite" else int(m)) if m is not None else \
            {"opposite": "opposite", "3": 2, "4": 4, "1": 1}[by_labels[(o, t)]]           # the sub-role swapped: 2
        return make_response(json.dumps({"reason": "r", "similarity": v}), input_tokens=150, output_tokens=60)
    holder = {}

    def factory(*a, **k):
        holder["c"] = FakeAsyncAnthropic(responder)
        return holder["c"]
    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc1234")
    base = ["rubric-check", "--pairs", str(sheet), "--data-dir", str(REPO / "data"), "--out-root", str(tmp_path / "c")]
    assert cli.main([*base, "--dry-run"]) == 0
    o = capsys.readouterr().out
    assert "80 x" in o and '"roles": [' in o and '"target"' in o
    assert cli.main(base) == 0
    d = tmp_path / "c" / "novelty" / "roles_rubric_1"
    rows = [json.loads(x) for x in (d / "readings.jsonl").read_text().splitlines()]
    assert len(rows) == 40 and all(r["overlap"]["straight"] is not None for r in rows)
    k = json.loads((d / "kappa.json").read_text())["result"]
    assert k["overlap"]["straight"]["kappa"] == 1.0 and k["relation"]["straight"]["kappa"] == 1.0 and k["passed"]
    assert k["overlap"]["straight"]["opposite_agreed"] == 6
    assert k["gap_by_set"]["sub_role"]["mean"] == 1.0 and k["gap_by_set"]["same_role"]["mean"] == 0.0
    assert "**Passed.**" in (d / "readout.md").read_text()
    assert json.loads((d / "usage.json").read_text())["n_calls"] == 160
    assert all(c["model"] == "claude-sonnet-5-5" for c in holder["c"].calls)


def test_the_check_refuses_an_unmarked_sheet(sheet, capsys):
    assert cli.main(["rubric-check", "--pairs", str(sheet), "--data-dir", str(REPO / "data"), "--dry-run"]) == 2
    assert "mark every pair" in capsys.readouterr().err


def test_the_sheet_needs_the_role_glosses(tmp_path, capsys):
    """Review finding 1 (2026-10-23): the sheet to mark pairs each target's role gloss with the other's corpus
    description, as M3 reads them.  Without ``--glosses``, or with targets the glosses miss, ``--make-sheet`` is
    refused; ``--allow-descriptions`` writes the sheet marked as not for marking, and the check refuses marks made
    on it unless told."""
    base = ["rubric-check", "--data-dir", str(REPO / "data")]
    p = tmp_path / "role_rubric_pairs.md"
    assert cli.main([*base, "--make-sheet", "--pairs", str(p)]) == 2
    err = capsys.readouterr().err
    assert "no --glosses" in err and "retrieval-check first" in err and not p.exists()
    a_target = RP.RUBRIC_PAIRS[0][0]
    g = write_glosses(tmp_path / "glosses.jsonl", skip=(a_target,))
    assert cli.main([*base, "--make-sheet", "--pairs", str(p), "--glosses", str(g)]) == 2
    err = capsys.readouterr().err
    assert f"have no role gloss in {g}" in err and a_target in err
    assert not p.exists()
    # the description-only sheet: written only when told, and marked
    assert cli.main([*base, "--make-sheet", "--pairs", str(p), "--allow-descriptions"]) == 0
    assert "WARNING: 40 of the 40 targets" in capsys.readouterr().err
    text = p.read_text()
    assert "**Not for marking.**" in text and "(corpus description, no role gloss)" in text
    key = json.loads(p.with_name("role_rubric_pairs_key.json").read_text())
    assert key["for_marking"] is False and key["n_targets_without_gloss"] == 40 and key["glosses"] is None
    mark(p, {f"r{i:02d}": "1" for i in range(1, 41)})
    assert cli.main([*base, "--pairs", str(p), "--dry-run"]) == 2
    assert "finding 1" in capsys.readouterr().err
    assert cli.main([*base, "--pairs", str(p), "--dry-run", "--allow-descriptions"]) == 0
    # the sheet to mark: every target its role gloss, no banner
    q = tmp_path / "ok" / "role_rubric_pairs.md"
    q.parent.mkdir()
    assert cli.main([*base, "--make-sheet", "--pairs", str(q), "--glosses", str(write_glosses(tmp_path / "g2.jsonl"))]) == 0
    t = q.read_text()
    assert "Not for marking" not in t and "(corpus description" not in t and "its role gloss, the role gloss call's" in t
    assert json.loads(q.with_name("role_rubric_pairs_key.json").read_text())["for_marking"] is True


def test_the_committed_sheet_is_the_codes(tmp_path):
    """reports/trait_gap_generation/role_rubric_pairs.md is what --make-sheet writes (no marks yet), so a changed pair
    list or corpus description shows up here.  Until the retrieval check has run it is the description-only sheet,
    marked not for marking (review finding 1); after, the sheet of its glosses (compared when they are on disk)."""
    committed = REPO / "reports/trait_gap_generation/role_rubric_pairs.md"
    if cli.parse_rubric_marks(committed):
        pytest.skip("the committed sheet carries Roger's marks")
    key = json.loads(committed.with_name("role_rubric_pairs_key.json").read_text())
    p = tmp_path / "role_rubric_pairs.md"
    extra = ["--allow-descriptions"]
    if key.get("glosses"):
        g = REPO / key["glosses"] if not Path(key["glosses"]).is_absolute() else Path(key["glosses"])
        if not g.exists():
            pytest.skip(f"the sheet's glosses ({key['glosses']}) are not on disk here")
        extra = ["--glosses", str(g)]
    assert cli.main(["rubric-check", "--make-sheet", "--pairs", str(p), "--data-dir", str(REPO / "data"), *extra]) == 0
    assert committed.read_text() == p.read_text()
    if not key.get("glosses"):
        assert "**Not for marking.**" in committed.read_text()
