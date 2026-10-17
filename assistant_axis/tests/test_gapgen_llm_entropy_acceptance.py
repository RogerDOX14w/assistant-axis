"""LLM-entropy generator: acceptance on the recorded outputs (coding_plan_06 section 8, "Acceptance on recorded
outputs").  Each check skips while its outputs are absent (before the pilot), and is hard once they exist: the parse
rate (99%), ``usage.json`` beside every run that paid, the fetch record's counts for a full (b) run, every (c)
record's prompt hash in ``multilingual_prompts.json``, ``collapse.json`` covering every family run, the readouts'
headline and novel figure, family (b)'s opaque ids, the package's imports, and an untouched corpus."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators import llm_entropy as LE
from assistant_axis.gapgen.generators.llm_entropy.calls import parse_rate, read_responses
from assistant_axis.gapgen.paths import REPO_ROOT, runs_root

RUNS = runs_root() / LE.GENERATOR
PKG = Path(LE.__file__).resolve().parent


def run_dirs() -> list[Path]:
    return sorted(p for p in RUNS.iterdir() if p.is_dir()) if RUNS.exists() else []


def _records(rdir: Path) -> list[dict]:
    return read_responses(rdir / LE.RESPONSES_NAME)


def test_parse_rate_at_least_99_percent_in_every_run():
    dirs = [d for d in run_dirs() if _records(d)]
    if not dirs:
        pytest.skip("no recorded run yet")
    for d in dirs:
        recs = [r for r in _records(d) if not r.get("abandoned")]
        for fam in sorted({r.get("family") for r in recs}):
            pr = parse_rate([r for r in recs if r.get("family") == fam])
            assert pr["rate"] is None or pr["rate"] >= 0.99, (d.name, fam, pr)


def test_usage_json_beside_every_run_that_paid():
    dirs = [d for d in run_dirs() if any(r.get("usage_raw") for r in _records(d))]
    if not dirs:
        pytest.skip("no paid run yet")
    for d in dirs:
        u = json.loads((d / "usage.json").read_text(encoding="utf-8"))
        assert u["total_cost_usd"] > 0 and u["n_calls"] > 0, d.name


def test_the_fetch_record_counts_full_b_runs():
    p = LE.PERSON_SEEDS_FETCH_PATH
    if not p.exists():
        pytest.skip("no person-seed fetch yet")
    rec = json.loads(p.read_text(encoding="utf-8"))
    for e in rec["runs"]:
        assert e["licence"].startswith("CC0") and set(e["seeds"][0]) <= {"seed_id", "kind", "era"}
        if e["requested"] == {"real": 400, "fictional": 200}:
            assert (e["n_real"], e["n_fictional"]) == (400, 200), e["run_id"]
    blob = p.read_text(encoding="utf-8")
    assert '"name"' not in blob and '"description"' not in blob and '"qid"' not in blob


def test_b_records_carry_opaque_ids_only():
    recs = [r for d in run_dirs() for r in _records(d) if r.get("family") == "b"]
    if not recs:
        pytest.skip("no (b) record yet")
    for r in recs:
        if r.get("abandoned"):
            assert r.get("text") is None
            continue
        assert re.fullmatch(r"b:[rf]\d{4}", r["prompt_id"]) and r["user"].startswith(f"Person: <{r['prompt_id']}>.")
        assert re.fullmatch(r"b-[rf]\d{4}-.*", r["custom_id"])


def test_every_c_records_prompt_hash_is_in_the_translations():
    recs = [r for d in run_dirs() for r in _records(d) if r.get("family") == "c" and r.get("step") == "generate"]
    if not recs:
        pytest.skip("no (c) record yet")
    pj = json.loads(LE.MULTILINGUAL_PROMPTS_PATH.read_text(encoding="utf-8"))
    hashes = {e["sha256"] for e in pj["languages"].values()}
    for r in recs:
        assert r["meta"]["language_prompt_sha256"] in hashes, r["custom_id"]


def test_collapse_json_has_every_family_run():
    from assistant_axis.gapgen.generators.llm_entropy.collapse import load_collapse
    if not LE.COLLAPSE_PATH.exists():
        pytest.skip("no collapse.json yet")
    coll = load_collapse()
    fams = {r.get("family") for run in coll.get("runs") or [] for r in _records(RUNS / run)
            if r.get("ok") and (r.get("step") or "generate") in ("generate", "verbalized")}
    assert fams <= set(coll["per_family"]), fams - set(coll["per_family"])


def test_the_readouts_carry_the_headline_and_the_novel_figure_twice():
    reports = [d / "report.md" for d in run_dirs() if (d / "report.md").exists()]
    if not reports:
        pytest.skip("no report.md yet")
    for p in reports:
        body = p.read_text(encoding="utf-8")
        assert "## Already registered (the headline)" in body, p
        assert re.search(r"raw \d+, net \d+", body), p


def test_the_package_imports_no_openai_beyond_the_embedding_cache():
    for f in sorted(PKG.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import openai|from openai)", src, re.M), f.name


def test_the_corpus_is_untouched():
    """The plan's last check (section 8): ``git status`` of the trait and role files is empty.  Like the others it
    skips until the generator has recorded a run (other work in progress on the corpus would fail it otherwise)."""
    if not run_dirs():
        pytest.skip("no recorded run yet")
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", "data/traits", "data/roles"], cwd=REPO_ROOT,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git unavailable")
    assert out.strip() == ""
