"""Regression tests for the M1 diff review (reports/trait_gap_generation/review_m1.md).

Finding numbers in the test names are the review's.  Written before the
fixes; each one failed against de5190f.
"""
import json
import multiprocessing as mp
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from assistant_axis.gapgen import paths
from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort
from assistant_axis.gapgen.filter import FilterItem, FilterRunner
from assistant_axis.gapgen.normalize import MAX_SURFACE_CHARS, normalize_candidate
from assistant_axis.gapgen.registry import Candidate, Registry, compact, submit_candidates
from assistant_axis.gapgen.runs import start_run
from assistant_axis.judge_pricing import BudgetExceededError
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

HAIKU = "claude-haiku-4-5-20251001"
REPO = paths.REPO_ROOT


def C(surface, **kw):
    base = dict(generator="censuses", run_id="r1")
    base.update(kw)
    return Candidate(surface=surface, **base)


# ---------------------------------------------------------------------------
# 1. two sessions on one run id
# ---------------------------------------------------------------------------

class TestRunSessions:
    def test_second_session_accumulates(self, tmp_path):
        reg = tmp_path / "candidates" / "registry.jsonl"
        r1 = start_run("censuses", "r1", args={"stage": "tda"}, candidates_dir=tmp_path / "candidates")
        r1.usage.charge(HAIKU, 100_000, 20_000)  # $0.20
        submit_candidates([C("stubborn"), C("vain")], registry_path=reg, run=r1)
        r1.finish()
        first = json.loads((r1.dir / "run.json").read_text())

        r2 = start_run("censuses", "r1", args={"via": "gap_registry.py submit"},
                       candidates_dir=tmp_path / "candidates")
        submit_candidates([C("timid")], registry_path=reg, run=r2)
        r2.finish()
        usage = json.loads((r2.dir / "usage.json").read_text())
        assert usage["n_calls"] == 1 and usage["total_cost_usd"] == pytest.approx(0.2)
        rj = json.loads((r2.dir / "run.json").read_text())
        assert rj["n_emitted"] == 3
        assert rj["started_at"] == first["started_at"]
        assert rj["args"] == {"stage": "tda"}
        assert [s["args"] for s in rj["sessions"]] == [{"stage": "tda"}, {"via": "gap_registry.py submit"}]
        assert [s["n_emitted"] for s in rj["sessions"]] == [2, 1]

    def test_finish_twice_in_one_session_does_not_double_count(self, tmp_path):
        r = start_run("g", "r", candidates_dir=tmp_path)
        r.usage.charge(HAIKU, 1_000_000, 0)
        r.finish()
        r.finish()
        assert json.loads((r.dir / "usage.json").read_text())["n_calls"] == 1
        assert len(json.loads((r.dir / "run.json").read_text())["sessions"]) == 1


# ---------------------------------------------------------------------------
# 2. torn last line
# ---------------------------------------------------------------------------

class TestTornLine:
    def _torn(self, reg):
        submit_candidates([C("stubborn")], registry_path=reg)
        with open(reg, "a") as fh:
            fh.write('{"key": "brave#1", "stem": "bra')  # killed mid-write, no newline

    def test_append_after_torn_line_is_kept(self, tmp_path):
        reg = tmp_path / "registry.jsonl"
        self._torn(reg)
        rep = submit_candidates([C("timid"), C("loyal")], registry_path=reg)
        assert rep.n_new == 2
        rows = Registry(reg).fold()
        assert {"stubborn#1", "timid#1", "loyal#1"} <= set(rows)
        r = Registry(reg)
        r.fold()
        assert r.n_malformed == 1

    def test_compact_refuses_malformed_then_sets_aside(self, tmp_path):
        reg = tmp_path / "registry.jsonl"
        self._torn(reg)
        submit_candidates([C("timid")], registry_path=reg)
        raw = reg.read_bytes()
        with pytest.raises(ValueError, match="malformed"):
            compact(reg)
        assert reg.read_bytes() == raw
        rep = compact(reg, set_aside_malformed=True)
        assert rep.rejected_path is not None
        assert '"stem": "bra' in rep.rejected_path.read_text()
        assert set(Registry(reg).fold()) == {"stubborn#1", "timid#1"}


# ---------------------------------------------------------------------------
# 3. cost cap and the $20 line
# ---------------------------------------------------------------------------

class TestCapBand:
    @pytest.mark.parametrize("estimate", [13.34, 15.0, 19.9])
    def test_cap_clamped_to_hard_line_without_confirmed_by(self, estimate):
        cap = confirm_or_abort(estimate, 5.0, confirm_expensive=True)
        assert cap <= 20.0

    def test_typed_budget_over_hard_line_refused(self):
        with pytest.raises(CostRefused):
            confirm_or_abort(1.0, 100.0, confirm_expensive=False)
        with pytest.raises(CostRefused):
            confirm_or_abort(1.0, 100.0, confirm_expensive=True)

    def test_confirmed_by_lifts_the_clamp(self):
        assert confirm_or_abort(1.0, 100.0, confirm_expensive=True, confirmed_by="Roger 2026-09-29") == 100.0
        assert confirm_or_abort(15.0, 5.0, confirm_expensive=True, confirmed_by="Roger") == pytest.approx(22.5)

    def test_below_line_behaviour_unchanged(self):
        assert confirm_or_abort(6.0, 5.0, confirm_expensive=True) == pytest.approx(9.0)
        assert confirm_or_abort(0.5, 5.0, confirm_expensive=False) == 5.0

    def test_cost_refused_exit_code_is_2(self):
        with pytest.raises(SystemExit) as ei:
            confirm_or_abort(6.0, 5.0, confirm_expensive=False)
        assert ei.value.code == 2
        assert "exceeds" in str(ei.value)


# ---------------------------------------------------------------------------
# 4. budget stop keeps what was paid for
# ---------------------------------------------------------------------------

WORDS = ["stubborn", "vain", "timid", "loyal", "brave", "shy", "rude", "calm", "proud", "witty"]


def _row(i, label):
    return {"id": i, "reason": "A habit.", "senses": [label], "trait_sense_rank": 1, "enactable_in_text": 2,
            "verdict": "trait", "tags": [], "region": "social_interpersonal",
            "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}


def costly_responder(kw):
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    body = {"results": [_row(it["id"], it["label"]) for it in items]}
    return make_response(json.dumps(body), input_tokens=40_000, output_tokens=0)  # $0.04 per call


class TestBudgetStop:
    def test_stop_keeps_classified_rows_and_responses(self, tmp_path):
        client = FakeAsyncAnthropic(costly_responder, delay=0.01)
        usage = GuardedUsage(budget_usd=0.10)
        resp_path = tmp_path / "responses.jsonl"
        runner = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model=None, usage=usage,
                              batch_size=2, concurrency=2, probe=False, second_opinion=False,
                              zipf_fn=lambda w: 4.0, wordnet=False, responses_path=resp_path)
        items = [FilterItem(key=f"{w}#1", label=w) for w in WORDS]
        with pytest.raises(BudgetExceededError):
            runner.run(items)
        n = usage.n_calls
        # the cap ($0.10) trips on the third $0.04 call; at most concurrency - 1 more were in flight
        assert 3 <= n <= 4 < 5
        classified = [r for r in runner.results.values() if r.stage == "classified"]
        assert len(classified) == 2 * n
        assert all(r.filter is not None for r in classified)
        assert len(runner.responses) == n
        assert len(resp_path.read_text().splitlines()) == n
        assert runner.stats["n_llm"] == 2 * n


# ---------------------------------------------------------------------------
# 6. wn pin independent of import order (subprocess, controlled imports)
# ---------------------------------------------------------------------------

def _run_py(code: str) -> str:
    env = {k: v for k, v in os.environ.items() if k not in ("WN_DATA_DIR", "VIRTUAL_ENV")}
    env["TMPDIR"] = "/tmp"
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True,
                         timeout=120)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


@pytest.mark.parametrize("first", ["assistant_axis.gapgen", "assistant_axis.gapgen.freq",
                                   "assistant_axis.gapgen.registry", "assistant_axis.gapgen.cost",
                                   "assistant_axis.gapgen.llm", "assistant_axis.gapgen.promote"])
@pytest.mark.parametrize("wn_first", [False, True])
def test_wn_pinned_whatever_is_imported_first(first, wn_first):
    pytest.importorskip("wn")
    code = (("import wn\n" if wn_first else "")
            + f"import importlib; importlib.import_module({first!r})\n"
            + "import os, wn\n"
            + "print(os.environ.get('WN_DATA_DIR'))\n"
            + "print(wn.config._data_directory)\n")
    env_dir, wn_dir = _run_py(code).splitlines()
    assert Path(env_dir) == paths.wn_data_dir()
    assert Path(wn_dir) == paths.wn_data_dir()


# ---------------------------------------------------------------------------
# 9 (second half). probe parse failures reach warn_if_low_parse_rate
# ---------------------------------------------------------------------------

def test_probe_parse_failures_are_reported(caplog):
    import logging

    def responder(kw):
        items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
        if "rare English words" in system_text(kw):
            return "no JSON here"
        return json.dumps({"results": [_row(it["id"], it["label"]) for it in items]})

    client = FakeAsyncAnthropic(responder)
    runner = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model=None, batch_size=5,
                          second_opinion=False, zipf_fn=lambda w: 2.2, wordnet=False, retry_delays=(0,))
    runner.run([FilterItem(key=f"{w}#1", label=w) for w in WORDS[:3]])
    with caplog.at_level(logging.INFO):
        runner.warn_parse_rate()
    assert "probe" in caplog.text and "*** HIGH FAIL RATE ***" in caplog.text


# ---------------------------------------------------------------------------
# 11. concurrent submitters exercise the lock
# ---------------------------------------------------------------------------

def _submit_worker(reg_path: str, idx: int) -> None:
    from assistant_axis.gapgen.registry import Candidate as Cd, submit_candidates as sub
    for j in range(10):
        sub([Cd(surface=f"word{idx}x{j}y{k}", generator=f"g{idx}", run_id="r") for k in range(5)],
            registry_path=Path(reg_path))


def test_concurrent_submitters(tmp_path):
    reg = tmp_path / "registry.jsonl"
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=_submit_worker, args=(str(reg), i)) for i in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(120)
        assert p.exitcode == 0
    lines = reg.read_text().splitlines()
    assert len(lines) == 200
    r = Registry(reg)
    rows = r.fold()
    assert len(rows) == 200 and r.n_malformed == 0
    assert {x["rev"] for x in rows.values()} == {1}


# ---------------------------------------------------------------------------
# 12. smaller items
# ---------------------------------------------------------------------------

class TestSmall:
    def test_compact_backups_never_overwritten(self, tmp_path):
        reg = tmp_path / "registry.jsonl"
        submit_candidates([C("stubborn")], registry_path=reg)
        a = compact(reg, stamp="20260929T000000Z")
        submit_candidates([C("vain")], registry_path=reg)
        b = compact(reg, stamp="20260929T000000Z")
        assert a.backup_path != b.backup_path
        assert a.backup_path.exists() and b.backup_path.exists()
        assert "vain" not in a.backup_path.read_text() and "vain" in b.backup_path.read_text()

    def test_write_same_key_twice_gets_distinct_revs(self, tmp_path):
        reg = tmp_path / "registry.jsonl"
        submit_candidates([C("stubborn")], registry_path=reg)
        r = Registry(reg)
        rec = r.get("stubborn#1")
        out = r.write([dict(rec, gloss="a"), dict(rec, gloss="b")])
        assert [x["rev"] for x in out] == [2, 3]
        assert r.get("stubborn#1")["gloss"] == "b"

    def test_surface_length_limit(self, tmp_path):
        with pytest.raises(ValueError):
            normalize_candidate("x" * (MAX_SURFACE_CHARS + 1))
        rep = submit_candidates([C("y" * 500), C("ok")], registry_path=tmp_path / "r.jsonl")
        assert rep.invalid == ["y" * 500] and rep.keys == ["ok#1"]

    def test_keys_order_and_dedupe_at_scale(self, tmp_path):
        cands = [C(f"w{i}") for i in range(3000)] + [C("w0", source_ref="other")]
        t = time.time()
        rep = submit_candidates(cands, registry_path=tmp_path / "r.jsonl")
        assert rep.keys == [f"w{i}#1" for i in range(3000)] and rep.n_merged == 1
        assert time.time() - t < 30

    def test_reader_waits_for_an_append_in_progress(self, tmp_path):
        reg = tmp_path / "registry.jsonl"
        submit_candidates([C("stubborn")], registry_path=reg)
        r = Registry(reg)
        seen = {}
        with r.locked():
            with open(reg, "a") as fh:
                fh.write('{"key": "vain#1", "stem": "va')
                fh.flush()
                t = threading.Thread(target=lambda: seen.update(rows=Registry(reg).fold()))
                t.start()
                time.sleep(0.3)
                assert t.is_alive()  # blocked on the lock, not reading a half line
                fh.write('in", "rev": 1}\n')
        t.join(10)
        assert set(seen["rows"]) == {"stubborn#1", "vain#1"}
