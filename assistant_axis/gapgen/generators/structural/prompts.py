"""The two pinned prompts of the structural generators, and their word hygiene (plan section 5, ``prompts.py``).

The texts live in ``reports/trait_gap_generation/rubrics/`` (the house pattern of :mod:`assistant_axis.gapgen.
split_rubrics`): ``structural_operators.md`` (generator B's per-trait call) and ``structural_modernise.md``
(generator A's modernise call), each a fenced block sent byte for byte as the system turn, pinned in
``versions.json``.  :func:`load_rubric` refuses a text that is not its latest pin (``rubric_pins.py bump NAME``), so
a paid run never sends an unpinned text; ``allow_unpinned`` is for rendering only.

**Hygiene** (the platform rule, ``prompt_hygiene.py``; cheats-on-tests): the worked examples are words outside the
corpus, the seed queue and the validation files, so that the pair-recovery test and the queue hold-out are not
seeded with their own answers (plan 09's illustrations, cautious, honest, harsh, arrogant, reckless and
self-critical, are all corpus traits).  :data:`EXAMPLE_WORDS` lists every example label of the two texts;
:func:`forbidden_stems` is the set they are checked against; :data:`PROSE_RECORDED` lists the ordinary words of the
texts that are on those lists anyway (``mean`` is a value of ``position``, ``operator`` a retarget target), each
only as prose: a test checks none is an example and that no new one appears.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.paths import DATA_DIR, REPO_ROOT

OPERATORS_RUBRIC = "structural_operators"
MODERNISE_RUBRIC = "structural_modernise"
RUBRICS: tuple[str, ...] = (OPERATORS_RUBRIC, MODERNISE_RUBRIC)

#: Every example label the two texts quote (traits, their answers, and the label-form examples, the forbidden forms
#: included): none may be a corpus stem, a seed-queue stem or label, or a validation-file word.
EXAMPLE_WORDS: dict[str, tuple[str, ...]] = {
    OPERATORS_RUBRIC: ("provident", "improvident", "miserly", "spendthrift", "censorious", "lax", "self-scolding",
                       "carping", "monarchist", "republican", "penny-pinching", "slow to forgive", "over-punctual",
                       "too punctual"),
    MODERNISE_RUBRIC: ("pettifogging", "nitpicking"),
}
#: Words of the texts that are corpus, queue or validation words and are used only as prose (beyond the platform's
#: ``prompt_hygiene.PROSE_ALLOWED``): ``mean`` is one of the four values of ``position`` (Aristotle's word), and
#: ``operator`` is in the target name ``the_operator`` (Roger's three principal targets).  Version 2 (2026-10-15, the
#: naming rule) adds ``single`` ("a single word") and ``usual`` ("its usual sense") to both.  A new hit fails the test.
PROSE_RECORDED: dict[str, frozenset] = {
    OPERATORS_RUBRIC: frozenset({"mean", "operator", "single", "usual"}),
    MODERNISE_RUBRIC: frozenset({"mean", "single", "usual"}),
}
#: The validation files whose words the examples avoid (``surface`` per line).
VALIDATION_FILES: tuple[str, ...] = ("m1_validation.jsonl", "split_test_words.jsonl")


class RubricNotPinned(RuntimeError):
    """A structural prompt's text on disk is not its latest pinned version."""


def load_rubric(name: str, rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin (with
    ``allow_unpinned``, for rendering only, ``version`` and ``sha256`` are None)."""
    if name not in RUBRICS:
        raise KeyError(f"not a structural rubric: {name!r}")
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == name]
    path = sr.rubric_path(name, rubrics_dir)
    try:
        rel = str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    text = sr.load_prompt(name, rubrics_dir)
    if probs:
        if not allow_unpinned:
            raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
        return {"name": name, "text": text, "version": None, "sha256": None, "file": rel}
    version, sha = sr.current_versions(rubrics_dir, (name,))[name]
    return {"name": name, "text": text, "version": version, "sha256": sha, "file": rel}


def operator_system(rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> str:
    """The operators call's system prompt (``OPERATOR_SYSTEM`` of the plan), read from its pinned file."""
    return load_rubric(OPERATORS_RUBRIC, rubrics_dir, allow_unpinned=allow_unpinned)["text"]


def modernise_system(rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> str:
    """The modernise call's system prompt (``MODERNISE_SYSTEM`` of the plan), read from its pinned file."""
    return load_rubric(MODERNISE_RUBRIC, rubrics_dir, allow_unpinned=allow_unpinned)["text"]


def forbidden_stems(data_dir: Optional[Path] = None, *, queue_path: Optional[Path] = None,
                    validation_dir: Optional[Path] = None, extra: Iterable[str] = ()) -> set[str]:
    """Stems an example may not be: every corpus trait stem, every seed-queue entry's stem and label (all statuses:
    a rejected name is the queue hold-out's "regenerated" line), every validation-file word, and ``extra``."""
    d = Path(data_dir or DATA_DIR)
    out = {p.stem for p in (d / "traits" / "instructions").glob("*.json")}
    qp = Path(queue_path or d / "seed_queue.json")
    if qp.exists():
        q = json.loads(qp.read_text(encoding="utf-8"))
        for e in (q.get("entries") if isinstance(q, dict) else q) or []:
            for k in ("stem", "label"):
                if e.get(k):
                    out.add(normalize_to_file_name(e[k]))
    vd = Path(validation_dir or d / "candidates" / "validation")
    for f in VALIDATION_FILES:
        p = vd / f
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out.add(normalize_to_file_name(json.loads(line)["surface"]))
    out.update(normalize_to_file_name(x) for x in extra)
    return {s for s in out if s}


__all__ = ["OPERATORS_RUBRIC", "MODERNISE_RUBRIC", "RUBRICS", "EXAMPLE_WORDS", "PROSE_RECORDED", "VALIDATION_FILES",
           "RubricNotPinned", "load_rubric", "operator_system", "modernise_system", "forbidden_stems"]
