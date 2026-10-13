"""Plan 12 § 8, CLI: ``persona_novelty.py`` end to end on a toy corpus, a toy vectors tree and an embedding cache
filled with hash embeddings under the live model's tag (so nothing is sent): every subcommand's ``--dry-run`` exits 0
and writes nothing; ``score`` prints the estimate and refuses over budget; a paid command refuses a dirty platform tree
without ``--allow-dirty``; every JSON output carries the provenance envelope; the judge runs on a fake client."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen.persona_space import pool as POOL
from assistant_axis.gapgen.persona_space import prospective as PRO
from assistant_axis.gapgen.persona_space import score as SC
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests import persona_space_fakes as F
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic
from assistant_axis.tests.test_gapgen_novelty import responder_for
from assistant_axis.tests.test_gapgen_persona_space_score import reg_row
from data_analysis.gap_generation import persona_novelty as PN


def make_env(tmp_path: Path) -> dict:
    data = F.write_toy_corpus(tmp_path / "data")
    tree = F.write_vectors_tree(tmp_path / "tree", F.toy_raw_vectors())
    pc = tmp_path / "poolcache"
    pool = POOL.load_pool(data, tree, cache_dir=pc)
    texts = [t for t in POOL.corpus_texts(pool, data) if t]
    rows = []
    for i in range(30):
        stem = f"cand_{i:02d}"
        gloss = f"This means being t{(i % 20) + 1:02d} in the manner of t{(i % 20) + 1:02d} and more, case {i}."
        nv = {"decision": "covered" if i % 3 == 0 else "new", "covered_by": f"t{(i % 20) + 1:02d}" if i % 3 == 0 else None,
              "listed": [{"stem": f"t{(i % 20) + 1:02d}", "rank": 1, "cosine": 0.3 + i / 100}]}
        rows.append(reg_row(stem, gloss=gloss, novelty=nv, gen="ipip" if i < 15 else "censuses"))
    reg = Registry(tmp_path / "registry.jsonl")
    reg.write(rows)
    cands, _ = SC.candidates({r["key"]: r for r in rows}, all_rows=True)
    ents = PRO.pending(pool, data)
    F.fill_cache(tmp_path / "emb", texts + SC.candidate_texts(cands) + PRO.pending_texts(ents, data))
    common = ["--data-dir", str(data), "--vectors-dir", str(tree), "--pool-cache-dir", str(pc), "--registry",
              str(tmp_path / "registry.jsonl"), "--out-root", str(tmp_path / "persona"), "--cache-dir",
              str(tmp_path / "emb")]
    return {"data": data, "tree": tree, "common": common, "out": tmp_path / "persona", "reg": reg, "rows": rows,
            "tmp": tmp_path}


def run(env, *argv) -> int:
    cmd = list(argv)
    # common flags go after the (sub)command words
    words = 2 if cmd[0] == "prospective" else 1
    return PN.main(cmd[:words] + env["common"] + cmd[words:])


def listing(root: Path) -> dict:
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    e = make_env(tmp_path_factory.mktemp("cli"))
    assert run(e, "fit", "--fit-id", "fit_t") == 0
    assert run(e, "score", "--batch-id", "b_all", "--fit-id", "fit_t", "--all-rows", "--write-registry") == 0
    assert run(e, "prospective", "predict", "--fit-id", "fit_t") == 0
    return e


def envelopes(d: Path):
    for p in d.rglob("*.json"):
        doc = json.loads(p.read_text())
        if p.name in ("run.json", "usage.json"):
            continue
        yield p, doc


class TestFullFlow:
    def test_fit_outputs(self, env):
        d = env["out"] / "fit" / "fit_t"
        for f in ("cv.json", "calibration.json", "fit_report.md", "fit_report.png", "model.npz", "run.json",
                  "usage.json"):
            assert (d / f).exists(), f
        cv = json.loads((d / "cv.json").read_text())["result"]
        assert cv["n_rows"] == 50 and cv["alpha"] in (0.03, 0.1, 0.3, 1.0, 3.0) and cv["N"] in (12, 16, 20, 24, 28, 32)
        cal = json.loads((d / "calibration.json").read_text())["result"]
        assert cal["thresholds_set_by"] == "plan default" and "dup_threshold" in cal and "novel_pct" in cal
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 0          # every text cached: $0
        assert "fit_report.png" in (d / "fit_report.md").read_text()
        from PIL import Image
        info = Image.open(d / "fit_report.png").info
        assert info.get("Title", "").startswith("Persona-space fit fit_t")
        assert info.get("Software", "").startswith("uv run python data_analysis/gap_generation/persona_novelty.py fit")
        env_ = json.loads((d / "cv.json").read_text())["_provenance"]
        assert env_["produced_by"]["cmd"].startswith("uv run python data_analysis/gap_generation/persona_novelty.py fit ")

    def test_score_outputs_and_blocks(self, env):
        d = env["out"] / "score" / "b_all"
        for f in ("scores.jsonl", "summary.json", "agreement.json", "disagreements.jsonl", "disagreements.md",
                  "score_report.md", "predictions.npz", "run.json", "usage.json"):
            assert (d / f).exists(), f
        rows = [json.loads(x) for x in (d / "scores.jsonl").read_text().splitlines()]
        assert len(rows) == 30 and all(set(SC.BLOCK_FIELDS) <= set(r) for r in rows)
        folded = env["reg"].fold()
        assert all(folded[r["key"]]["persona"] == SC.persona_block(r) for r in rows)
        assert all(folded[r["key"]]["novelty"]["decision"] in ("covered", "new") for r in rows)
        run_ = json.loads((d / "run.json").read_text())
        assert run_["registry"]["n_written"] == 30 and run_["n_embedded"] == 0

    def test_every_json_output_is_enveloped(self, env):
        n = 0
        for p, doc in envelopes(env["out"]):
            assert set(doc) == {"result", "_provenance"}, p
            ins = {i["dep_key"]: i["path"] for i in doc["_provenance"].get("inputs") or []}
            # a file in a checkout is recorded relative to it (never a home directory); a test's tmp file is not in one
            assert ins.get("producer_script") == "data_analysis/gap_generation/persona_novelty.py", p
            n += 1
        assert n >= 4

    def test_apply_is_idempotent_and_compare_and_report_run(self, env):
        assert run(env, "apply", "--batch-id", "b_all") == 0
        before = len((env["tmp"] / "registry.jsonl").read_text().splitlines())
        assert run(env, "apply", "--batch-id", "b_all") == 0
        assert len((env["tmp"] / "registry.jsonl").read_text().splitlines()) == before
        assert run(env, "compare", "--batch-id", "b_all") == 0
        assert run(env, "report", "--batch-id", "b_all") == 0
        md = (env["out"] / "score" / "b_all" / "score_report.md").read_text()
        assert "## Top 30 by residual percentile" in md and "## Agreement with M3" in md

    def test_prospective_predict(self, env):
        d = env["out"] / "prospective" / "fit_t"
        rows = [json.loads(x) for x in (d / "predicted.jsonl").read_text().splitlines()]
        assert [r["id"] for r in rows] == ["p_one|T", "p_two|T", "violent|T"]
        assert "prospective compare --fit-id fit_t" in (d / "prospective_report.md").read_text()

    def test_judge_on_a_fake_client(self, env, capsys):
        d = env["out"] / "score" / "b_all"
        dis = [json.loads(x) for x in (d / "disagreements.jsonl").read_text().splitlines()]
        pairs = [x for x in dis if x["kind"] == "dup_vs_new"]
        # no --write-registry: the batch wrote its blocks to this registry, so the readings go there too (§ 7)
        args = PN.build_parser().parse_args(["judge-disagreements"] + env["common"] +
                                            ["--batch-id", "b_all", "--allow-dirty"])
        client = FakeAsyncAnthropic(responder_for({}, {}, default_overlap=3))
        assert PN.cmd_judge(args, [], client=client) == 0
        readings = [json.loads(x) for x in (d / "readings.jsonl").read_text().splitlines()]
        assert len(readings) == len(pairs) == len({c["messages"][0]["content"] for c in client.calls if
                                                   "sonnet" in c["model"]})
        folded = env["reg"].fold()
        for r in readings:
            assert folded[r["key"]]["persona"]["reading"]["stem"] == r["stem"]
            assert folded[r["key"]]["novelty"]["decision"] == "new"                # M3's decision is untouched
        out = capsys.readouterr().out
        assert "rendered prompt of the first pair" in out and '"target"' in out


class TestDryRuns:
    @pytest.mark.parametrize("argv", [
        ("fit", "--fit-id", "fit_dry"),
        ("score", "--batch-id", "b_dry", "--fit-id", "fit_t", "--all-rows"),
        ("score", "--batch-id", "b_dry", "--fit-id", "fit_t", "--run", "ipip/r1", "--write-registry"),
        ("apply", "--batch-id", "b_all"),
        ("compare", "--batch-id", "b_all"),
        ("judge-disagreements", "--batch-id", "b_all"),
        ("prospective", "predict", "--fit-id", "fit_t"),
        ("prospective", "compare", "--fit-id", "fit_t", "--new-vectors-dir", "/nonexistent"),
        ("report", "--batch-id", "b_all"),
    ])
    def test_exit_0_and_write_nothing(self, env, argv, capsys):
        before = listing(env["tmp"])
        assert run(env, *argv, "--dry-run") == 0
        assert listing(env["tmp"]) == before
        assert capsys.readouterr().out

    def test_judge_dry_run_prints_the_estimate_and_the_prompt(self, env, capsys):
        assert run(env, "judge-disagreements", "--batch-id", "b_all", "--dry-run") == 0
        out = capsys.readouterr().out
        assert "total estimate" in out and "projected spend" in out


class TestGates:
    def uncached(self, env):
        r = reg_row("brand_new_word", gloss="This means a gloss that is not in any cache at all, word brand.",
                    gen="manual", run="uncached")
        env["reg"].write([r])
        return r["key"]

    def test_score_prints_the_estimate_and_refuses_over_budget(self, env, monkeypatch, capsys):
        key = self.uncached(env)
        monkeypatch.setattr(PN, "platform_dirty_files", lambda *a, **k: [])
        before = listing(env["tmp"])
        rc = run(env, "score", "--batch-id", "b_over", "--fit-id", "fit_t", "--keys", key, "--budget-usd", "1e-9")
        assert rc == 2
        cap = capsys.readouterr()
        assert "total estimate" in cap.out and "exceeds --budget-usd" in cap.err
        assert not (env["out"] / "score" / "b_over").exists() and listing(env["tmp"]) == before

    def test_a_dirty_tree_is_refused_without_allow_dirty(self, env, monkeypatch, capsys):
        key = self.uncached(env)
        monkeypatch.setattr(PN, "platform_dirty_files", lambda *a, **k: [" M assistant_axis/gapgen/x.py"])
        rc = run(env, "score", "--batch-id", "b_dirty", "--fit-id", "fit_t", "--keys", key)
        assert rc == 2 and "uncommitted changes" in capsys.readouterr().err
        assert not (env["out"] / "score" / "b_dirty").exists()

    def test_a_cached_batch_is_free_and_needs_no_gate(self, env, monkeypatch):
        monkeypatch.setattr(PN, "platform_dirty_files", lambda *a, **k: [" M assistant_axis/gapgen/x.py"])
        assert run(env, "score", "--batch-id", "b_free", "--fit-id", "fit_t", "--run", "ipip/r1") == 0
        assert json.loads((env["out"] / "score" / "b_free" / "usage.json").read_text())["n_calls"] == 0

    def test_a_recorded_fit_is_not_moved_in_place(self, env):
        with pytest.raises(SystemExit, match="needs a new --fit-id"):
            run(env, "fit", "--fit-id", "fit_t", "--dup-threshold", "0.8")
        assert run(env, "fit", "--fit-id", "fit_t") == 1              # its model is there: nothing to do

    def test_an_existing_batch_is_not_overwritten(self, env, capsys):
        assert run(env, "score", "--batch-id", "b_all", "--fit-id", "fit_t", "--all-rows") == 1

    def test_the_registry_blocks_list(self):
        from assistant_axis.gapgen.registry import BLOCKS
        assert "persona" in BLOCKS and NR.candidate_from_row is SC.candidate_from_row
