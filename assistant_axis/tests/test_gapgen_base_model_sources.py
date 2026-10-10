"""Base-model generator (workstream 3), task 1: the source table, the layout constants, the zero-rate pricing of
the local sampler, and ``setup_external.py --hf-model`` knowing the generator's model.  No network."""
from pathlib import Path

import pytest

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL, REPO_ROOT
from assistant_axis.judge_pricing import MultiModelUsage, price_for_model


def test_layout_constants():
    from assistant_axis.gapgen.generators import base_model as B
    assert B.GENERATOR == "base_model"
    assert B.BASE_DIR == DATA_CANDIDATES / "base_model"
    assert B.SAMPLES_DIR == DATA_CANDIDATES / "cache" / "base_model"      # gitignored with /data/candidates/cache/
    assert B.WIKIBIO_DIR == DATA_EXTERNAL / "wikibio" and B.ONET_DIR == DATA_EXTERNAL / "onet"
    assert B.MODEL_ID == "Qwen/Qwen3-8B-Base"
    for p in (B.BASE_DIR, B.SAMPLES_DIR, B.WIKIBIO_DIR, B.ONET_DIR, B.table_path(1), B.stats_path(1),
              B.samples_path(1), B.stats_path(0, temperature=0.8)):
        assert Path(p).is_relative_to(REPO_ROOT)
    assert B.table_path(2).name == "candidate_table_round2.jsonl"
    assert B.stats_path(1).name == "stats_round1.json"
    assert B.stats_path(0, temperature=1.2).name == "stats_round0_t1.2.json"
    assert B.samples_path(3) == B.SAMPLES_DIR / "round3" / "samples.jsonl"


def test_sources_table():
    from assistant_axis.gapgen.generators.base_model import sources as S
    assert set(S.SOURCES) == {"wikibio", "onet"}
    wb, on = S.SOURCES["wikibio"], S.SOURCES["onet"]
    assert wb.licence == "CC BY-SA 3.0" and wb.repo_id == "michaelauli/wiki_bio" and wb.revision
    assert wb.size_bytes == 333_998_704 and len(wb.sha256) == 64
    assert on.url.startswith("https://www.onetcenter.org/dl_files/database/db_31_0_csv/")
    # verified 2026-10-10 on onetcenter.org/license_db.html: CC BY 4.0, not public domain (plan 03 said so)
    assert on.licence == "CC BY 4.0" and "USDOL/ETA" in on.attribution
    # PersonaHub and SUBTLEX are skipped on purpose, with the reason
    assert {"PersonaHub", "SUBTLEX-US"} <= set(S.SKIPPED)
    # the model: Roger's delete-when-done TODO travels with its entry (2026-10-10, anything over 2 GB)
    m = S.MODEL
    assert m.model_id == "Qwen/Qwen3-8B-Base" and m.licence == "Apache-2.0" and m.size_bytes > 16e9
    assert "delete" in m.todo.lower() and "Roger" in m.todo
    assert "*.safetensors" in S.HF_MODEL_ALLOW_PATTERNS[m.model_id]
    # the optional instruct control is not approved: it has no entry
    assert "Qwen/Qwen3-8B" not in S.HF_MODEL_ALLOW_PATTERNS


def test_zero_rate_pricing_of_the_local_sampler():
    from assistant_axis.gapgen.generators.base_model import MODEL_ID
    assert price_for_model(MODEL_ID) == (0.0, 0.0)
    u = MultiModelUsage()
    u.charge(MODEL_ID, 2_000_000, 160_000)
    d = u.as_dict()
    assert d["total_cost_usd"] == 0.0 and d["total_prompt_tokens"] == 2_000_000 and d["n_calls"] == 1
    # the existing entries are unchanged (no fragment collision)
    assert price_for_model("qwen3-32b") == (0.08, 0.28)


def test_setup_external_knows_the_generator_model(capsys):
    from data_analysis.gap_generation import setup_external
    assert setup_external.main(["--hf-model", "Qwen/Qwen3-8B-Base", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Qwen/Qwen3-8B-Base" in out and "DRY-RUN" in out and "*.safetensors" in out
    # the optional instruct model stays refused until Roger approves it
    assert setup_external.main(["--hf-model", "Qwen/Qwen3-8B", "--dry-run"]) == 2


def test_embedder_allow_patterns_untouched():
    from assistant_axis.gapgen import embed as E
    assert "Qwen/Qwen3-8B-Base" not in E.HF_ALLOW_PATTERNS
