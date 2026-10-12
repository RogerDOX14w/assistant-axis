"""Regressions from the code review of the trait-gap platform's filter side (2026-10-12).  No API call: fake
clients and temporary directories only.

1. The split runner records a response before parsing it, so a parser that raises keeps the answer paid for.
2. Non-finite numbers (``NaN``, ``Infinity``, ``1e999``: all accepted by ``json.loads``) are not valid values to the
   parsers; before, ``int()`` of them raised from inside a parser and stopped the run.
3. ``runs.PLATFORM_PATHS`` covers every project module the platform imports, or the module is named below as one
   whose changes cannot alter what a paid run sends.
4. ``split_rubrics.bump`` keeps the rows of a prompt this code does not name (``versions.json`` is append-only).
5. ``split.cost_by_step`` charges 1-hour cache writes as ``llm.billed_usage`` does.
6. ``wordnet.ensure_oewn`` refuses a data directory outside the tree with an exception that ``python -O`` keeps.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen import split
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.filter import FilterItem
from assistant_axis.gapgen.split_runner import SplitRunner
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic
from assistant_axis.tests.split_replay import HAIKU, make_responder

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# 1. a parser that raises keeps the response
# ---------------------------------------------------------------------------

def test_a_parser_that_raises_keeps_the_response_it_was_given(tmp_path, monkeypatch):
    real_parse = split.parse

    def parse(step, text, *, label):
        if step == "sense" and label == "zorp":
            raise RuntimeError("parser bug")
        return real_parse(step, text, label=label)

    monkeypatch.setattr(split, "parse", parse)
    out = tmp_path / "responses.jsonl"
    r = SplitRunner(client=FakeAsyncAnthropic(make_responder()), batch_id="t", model=HAIKU, wordnet=False,
                    zipf_fn=lambda w: 4.0, retry_delays=(), second_opinion=False, responses_path=out)
    with pytest.raises(RuntimeError, match="parser bug"):
        r.run([FilterItem(key="zorp#1", label="zorp"), FilterItem(key="glib#1", label="glib")])
    recs = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    zorp = [x for x in recs if x["step"] == "sense" and x["keys"] == ["zorp#1"]]
    assert len(zorp) == 1 and zorp[0]["text"] and zorp[0]["usage_raw"]   # the paid answer is on disk
    assert r.results["zorp#1"].stage == "pending"                        # and its row was not made from it


# ---------------------------------------------------------------------------
# 2. non-finite numbers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("v", [float("nan"), float("inf"), float("-inf"), "nan", "inf", "+Infinity", 1e999])
def test_a_non_finite_number_is_no_value(v):
    assert fr._num(v, 0, 2, integer=True) is None
    assert fr._num(v, 0.0, 1.0) is None
    assert fr._num(v, float("-inf"), float("inf"), integer=True) is None


def test_parsers_answer_an_error_for_non_finite_ids_and_values():
    good = {"id": 1, "label": "glib", "reason": "r", "person_senses": [{"sense": "s", "kind": "trait"}],
            "trait_senses_equally_obvious": False, "judged_sense": "s", "enactable_in_text": 2, "verdict": "trait",
            "tags": [], "membership_kind": None, "region": "communication_style", "alignment_relevant": False,
            "gloss": "This means " + "talking " * 20, "confidence": 0.9}
    for bad_id in ("NaN", "Infinity", "1e999"):
        text = '{"results": [' + json.dumps(good).replace('"id": 1', f'"id": {bad_id}') + "]}"
        rows, errs = fr.parse_batch(text, [1], labels={1: "glib"})
        assert rows == {} and errs == {1: "missing"}
        assert split.parse("sense", text, label="glib")[1] == "no row with id 1"
        rows, errs = fr.parse_probe(text, [1])
        assert rows == {} and 1 in errs
    nan_conf = '{"results": [' + json.dumps(good).replace('"confidence": 0.9', '"confidence": NaN') + "]}"
    assert fr.parse_batch(nan_conf, [1], labels={1: "glib"})[1] == {1: "confidence missing or out of range"}
    desc = '{"results": [{"id": 1, "reason": "r", "region": "moral_stance", "enactable_in_text": NaN}]}'
    assert split.parse("descriptors", desc, label="glib") == (None, "enactable_in_text missing or out of range")
    assert math.isnan(json.loads("NaN"))   # what makes this reachable: the standard library reads it


# ---------------------------------------------------------------------------
# 3. the dirty-tree refusal covers the project modules the platform imports
# ---------------------------------------------------------------------------

#: Project modules the platform imports whose changes cannot alter what a paid run sends or how its answers are
#: read, so a paid run does not refuse while they are edited.
NOT_SENT = {
    "assistant_axis.plot_metadata": "the provenance envelope of outputs",
    "assistant_axis.provenance": "the input fingerprints in outputs",
    # load_queue and corpus_stems are plain JSON and glob readers; the module is edited often by the seeding work
    "data_analysis.seed_entities": "queue and corpus readers (load_queue, corpus_stems) and promotion bookkeeping",
    "results_analysis.canonical_angles": "M2's persona-space geometry (persona.py), no request depends on it",
}
_IMPORT = re.compile(r"^\s*(?:from|import)\s+((?:assistant_axis|data_analysis|results_analysis|pipeline|steering|tools)"
                     r"\.[A-Za-z_]+)", re.M)


def test_platform_paths_cover_every_project_module_the_platform_imports():
    from assistant_axis.gapgen.runs import PLATFORM_PATHS
    found: dict[str, set[str]] = {}
    for root in ("assistant_axis/gapgen", "data_analysis/gap_generation"):
        for p in sorted((REPO / root).rglob("*.py")):
            for mod in _IMPORT.findall(p.read_text(encoding="utf-8")):
                found.setdefault(mod, set()).add(str(p.relative_to(REPO)))
    covered = set(PLATFORM_PATHS)

    def is_covered(mod: str) -> bool:
        rel = mod.replace(".", "/")
        return any(rel == c or rel.startswith(c + "/") or rel + ".py" == c for c in covered)

    missing = {m: sorted(v) for m, v in found.items() if not is_covered(m) and m not in NOT_SENT}
    assert missing == {}
    assert "assistant_axis/arrangements.py" in PLATFORM_PATHS   # novelty.py lists arrangement members in M3 prompts
    for p in PLATFORM_PATHS:
        assert (REPO / p).exists(), p


# ---------------------------------------------------------------------------
# 4. bump keeps the rows of a prompt this code does not name
# ---------------------------------------------------------------------------

def _rubric(d: Path, name: str, text: str) -> None:
    (d / sr.PINNED_FILES[name]).write_text(f"# {name}\n\n## The prompt\n\n````text\n{text}\n````\n", encoding="utf-8")


def test_bump_keeps_every_row_of_versions_json(tmp_path):
    _rubric(tmp_path, "sense", "old text")
    old = {"version": 1, "sha256": sr.sha256("old text"), "pinned_at": "t0", "why": "first"}
    future = [{"version": 1, "sha256": "ab" * 32, "pinned_at": "t0", "why": "pinned by a newer checkout"}]
    (tmp_path / sr.VERSIONS_NAME).write_text(json.dumps({"_about": "x", "prompts": {
        "a_prompt_this_code_does_not_name": future, "sense": [old]}}), encoding="utf-8")
    _rubric(tmp_path, "sense", "new text")
    row = sr.bump("sense", "reworded", now="t1", rubrics_dir=tmp_path)
    assert row["version"] == 2
    got = json.loads((tmp_path / sr.VERSIONS_NAME).read_text(encoding="utf-8"))["prompts"]
    assert got["a_prompt_this_code_does_not_name"] == future
    assert [r["version"] for r in got["sense"]] == [1, 2]
    assert list(got) == ["sense", "a_prompt_this_code_does_not_name"]   # known names first, in their order


# ---------------------------------------------------------------------------
# 5. cost_by_step and the 1-hour cache
# ---------------------------------------------------------------------------

def test_cost_by_step_charges_one_hour_writes_as_billed():
    from assistant_axis.gapgen.llm import billed_usage
    from assistant_axis.judge_pricing import cost_for_usage
    model = "claude-haiku-4-5-20251001"
    resp = SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=10, cache_creation_input_tokens=1000,
                                                 cache_read_input_tokens=50,
                                                 cache_creation={"ephemeral_1h_input_tokens": 600}))
    p, o, raw = billed_usage(resp)
    assert p == 100 + 1.25 * 400 + 2.0 * 600 + 5 and raw["cache_creation_1h_input_tokens"] == 600
    got = split.cost_by_step([{"stage": "x", "charged_as": model, "usage_raw": raw}])["x@" + model]
    assert got["prompt_tokens"] == p and got["completion_tokens"] == o
    assert got["cost_usd"] == round(cost_for_usage(model, p, o), 6)
    # a record without the breakdown is charged as before
    raw5 = {k: v for k, v in raw.items() if k != "cache_creation_1h_input_tokens"}
    assert split.cost_by_step([{"stage": "x", "charged_as": model, "usage_raw": raw5}])["x@" + model][
        "prompt_tokens"] == 100 + 1250 + 5


# ---------------------------------------------------------------------------
# 6. the in-tree guard of the WordNet download
# ---------------------------------------------------------------------------

def test_ensure_oewn_refuses_a_data_directory_outside_the_tree(tmp_path, monkeypatch):
    from assistant_axis.gapgen import wordnet as W
    downloads = []
    fake = SimpleNamespace(config=SimpleNamespace(database_path=tmp_path / "elsewhere" / "wn.db"),
                           lexicons=lambda **kw: [], download=lambda lex: downloads.append(lex))
    monkeypatch.setattr(W, "_wn", fake)
    monkeypatch.setattr(W, "WN_DATA_DIR", tmp_path / "wn")
    with pytest.raises(RuntimeError, match="not in-tree"):
        W.ensure_oewn()
    assert downloads == []
