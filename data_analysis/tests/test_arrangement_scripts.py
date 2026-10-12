"""Tests for data_analysis/check_arrangements.py, and the archiving of the
September backfill (archive/backfill_arrangements_2026-09-08/, walk-through A4)."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data_analysis import check_arrangements as chk  # noqa: E402

ARCHIVED_BACKFILL = (_REPO_ROOT / "archive" / "backfill_arrangements_2026-09-08"
                     / "backfill_arrangements.py")


def _write(d: Path, stem: str, doc: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def trait(pos, neg, **extra):
    doc = {"positive_label": pos, "negative_label": neg, "description": f"This means being {pos}.",
           "instruction": [{"pos": "x", "neg": "y"}], "questions": ["q"], "eval_prompt": "e"}
    doc.update(extra)
    return doc


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    t = tmp_path / "traits" / "instructions"
    _write(t, "callous", trait("callous", "compassionate"))
    _write(t, "compassionate", trait("compassionate", "non-compassionate"))
    _write(t, "malicious", trait("malicious", "benign"))
    _write(t, "benign", trait("benign", "malicious"))
    _write(t, "blunt", trait("blunt", "tactful"))
    _write(t, "tactful", trait("tactful", "blunt"))
    _write(t, "calm", trait("calm", "agitated"))            # real word, no file -> unclassified
    _write(t, "curious", trait("curious", "non-curious"))    # placeholder, nothing points -> singleton
    _write(t, "selfish", trait("selfish", "unselfish"))      # in the moral-circle sequence
    _write(t, "cosmopolitan", trait("cosmopolitan", "non-cosmopolitan"))
    _write(t, "conformist", trait("conformist", "non-conformist"))
    _write(t, "contrarian", trait("contrarian", "conformist"))
    _write(t, "nonconformist", trait("nonconformist", "conformist"))
    r = tmp_path / "roles" / "instructions"
    _write(r, "angel", {"description": "An angel.", "instruction": [{"pos": "a"}]})
    _write(r, "demon", {"description": "A demon.", "instruction": [{"pos": "d"}]})
    _write(r, "chef", {"description": "A chef.", "instruction": [{"pos": "c"}]})
    _write(r, "default", {"instruction": [{"pos": ""}]})
    (tmp_path / "pair_list_clean.json").write_text(json.dumps([
        {"pos": "angel", "neg": "demon", "pair_type": "roles"},
        {"pos": "blunt", "neg": "tactful", "pair_type": "traits"},
    ]), encoding="utf-8")
    return tmp_path


def _load_archived_backfill():
    spec = importlib.util.spec_from_file_location("archived_backfill", ARCHIVED_BACKFILL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBackfillArchived:
    """The September backfill is archived, not live (walk-through A4, review 8
    D4): its --apply --overwrite would wipe every arrangement recorded since.
    It replaced TestBackfill (five tests of the live script) on 2026-10-12."""

    def test_moved_to_the_archive(self):
        assert ARCHIVED_BACKFILL.is_file()
        assert not (_REPO_ROOT / "data_analysis" / "backfill_arrangements.py").exists()
        assert "ARCHIVED 2026-10-12" in ARCHIVED_BACKFILL.read_text()

    def test_nothing_imports_it(self):
        pattern = re.compile(
            r"^\s*(from\s+\S*\s+import\s+[^#\n]*\bbackfill_arrangements\b"
            r"|import\s+\S*backfill_arrangements\b"
            r"|from\s+\S*backfill_arrangements\s+import)", re.M)
        offenders = []
        for top in ("assistant_axis", "data_analysis", "pipeline", "results_analysis",
                    "scripts", "steering", "tools"):
            for p in (_REPO_ROOT / top).rglob("*.py"):
                if pattern.search(p.read_text(encoding="utf-8", errors="replace")):
                    offenders.append(str(p.relative_to(_REPO_ROOT)))
        assert offenders == []

    def test_main_refuses_without_historical_rerun(self, corpus: Path, monkeypatch, capsys):
        monkeypatch.delenv("HISTORICAL_RERUN", raising=False)
        bf = _load_archived_backfill()
        before = {p: p.read_text() for p in corpus.rglob("*.json")}
        args = ["--data_dir", str(corpus), "--pair_list", str(corpus / "pair_list_clean.json"),
                "--apply", "--overwrite", "--quiet"]
        assert bf.main(args) == 2
        assert "ARCHIVED" in capsys.readouterr().err
        assert {p: p.read_text() for p in corpus.rglob("*.json")} == before

    def test_still_runs_as_a_record_when_asked(self, corpus: Path, monkeypatch, capsys):
        """HISTORICAL_RERUN=1 runs it (dry run here); the archive location's
        repo-root lookup still finds assistant_axis."""
        monkeypatch.setenv("HISTORICAL_RERUN", "1")
        bf = _load_archived_backfill()
        assert bf._REPO_ROOT == _REPO_ROOT
        before = {p: p.read_text() for p in corpus.rglob("*.json")}
        assert bf.main(["--data_dir", str(corpus),
                        "--pair_list", str(corpus / "pair_list_clean.json")]) == 0
        assert {p: p.read_text() for p in corpus.rglob("*.json")} == before
        assert "[DRY RUN] traits" in capsys.readouterr().out


class TestCheck:
    def test_exit_codes(self, corpus: Path, capsys):
        assert chk.main(["--data_dir", str(corpus)]) == 0          # nothing classified yet: clean
        out = capsys.readouterr().out
        assert "unclassified: 13" in out
        assert chk.main(["--data_dir", str(corpus), "--kinds", "traits", "--list-unclassified"]) == 0
        assert "unclassified: benign blunt callous" in capsys.readouterr().out
        # break something: declare a pair the labels contradict
        t = corpus / "traits" / "instructions"
        _write(t, "calm", trait("calm", "agitated", arrangement={"kind": "pair", "members": ["calm", "curious"]}))
        _write(t, "curious", trait("curious", "non-curious", arrangement={"kind": "pair", "members": ["calm", "curious"]}))
        assert chk.main(["--data_dir", str(corpus), "--quiet"]) == 1
        assert "not reciprocal by negative_label" in capsys.readouterr().out
        assert chk.main(["--data_dir", str(corpus / "nowhere")]) == 2
