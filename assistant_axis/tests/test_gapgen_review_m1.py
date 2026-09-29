"""Regression tests for the M1 diff review (reports/trait_gap_generation/review_m1.md)
and its re-review (review_m1_fixes.md).

Finding numbers in the test names are the review's.  The tests were written
before the fixes.  Against de5190f the module does not even import
(``MAX_SURFACE_CHARS`` is new), so read "failed before the fix" per test, as
the re-review did with that one import patched:

* ``TestCapBand.test_confirmed_by_lifts_the_clamp`` and
  ``TestCapBand.test_below_line_behaviour_unchanged`` pass on the old code by
  design: they guard behaviour the fix had to leave unchanged.
* ``test_keys_order_and_dedupe`` checks order and deduplication only and
  passes on the old code; nothing here tests the quadratic-time fix.
* ``TestRunSessions.test_finish_twice_in_one_session_does_not_double_count``
  failed on the old code on the missing ``sessions`` key, not on a double count.
* Every other test failed on the old code for the reason it names.

The section "Re-review follow-ups" at the end was written before the fixes of
review_m1_fixes.md section 3 and failed against ca80229.
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
    return {"id": i, "label": label, "reason": "A habit.", "senses": [label],
            "primary_use": "person_character", "enactable_in_text": 2, "verdict": "trait", "tags": [],
            "region": "social_interpersonal", "alignment_relevant": False,
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
        assert 3 <= n <= 4
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
        if "real English word" in system_text(kw):
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

SHARED_WORDS = [f"shared{k}" for k in range(50)]


def _submit_worker(reg_path: str, idx: int, nolock: bool = False, barrier=None) -> None:
    """Submit the same 50 surfaces as every other worker, one small call at a
    time, under generator ``g<idx>``.  ``nolock=True`` replaces the registry
    locks with no-ops (used only to show the test is sensitive to them)."""
    import contextlib
    from assistant_axis.gapgen import registry as regmod
    if nolock:
        regmod.Registry.locked = lambda self: contextlib.nullcontext()
        regmod.Registry._read_locked = lambda self: contextlib.nullcontext()
    if barrier is not None:
        barrier.wait()
    for w in SHARED_WORDS:
        regmod.submit_candidates([regmod.Candidate(surface=w, generator=f"g{idx}", run_id="r")],
                                 registry_path=Path(reg_path))


def run_concurrent_submitters(reg: Path, *, nolock: bool = False, n_workers: int = 4) -> dict:
    ctx = mp.get_context("spawn")
    barrier = ctx.Barrier(n_workers)
    procs = [ctx.Process(target=_submit_worker, args=(str(reg), i, nolock, barrier)) for i in range(n_workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(180)
        assert p.exitcode == 0
    return Registry(reg).fold()


def test_concurrent_submitters(tmp_path):
    """Four processes add a source to the *same* 50 keys at once.  Without the
    lock their read-modify-write cycles interleave and sources are lost (seen
    with nolock=True; see the M1 re-review report)."""
    reg = tmp_path / "registry.jsonl"
    rows = run_concurrent_submitters(reg)
    r = Registry(reg)
    r.fold()
    assert r.n_malformed == 0
    assert sorted(rows) == sorted(f"{w}#1" for w in SHARED_WORDS)
    for k, row in rows.items():
        gens = sorted(s["generator"] for s in row["sources"])
        assert gens == ["g0", "g1", "g2", "g3"], (k, gens)
        assert row["rev"] == 4


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

    def test_keys_order_and_dedupe(self, tmp_path):
        """Order and deduplication of ``SubmitReport.keys`` only.  It does NOT
        test the quadratic-time fix (the old list-membership code passes it
        too); the re-review measured 20,000 candidates at 0.25 s fixed against
        1.04 s before, which is too close to machine noise for a stable bound."""
        cands = [C(f"w{i}") for i in range(3000)] + [C("w0", source_ref="other")]
        rep = submit_candidates(cands, registry_path=tmp_path / "r.jsonl")
        assert rep.keys == [f"w{i}#1" for i in range(3000)] and rep.n_merged == 1

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


# ===========================================================================
# Re-review follow-ups (reports/trait_gap_generation/review_m1_fixes.md §3)
# ===========================================================================

DOLLAR = 1_000_000  # Haiku input tokens per dollar


class TestOverlappingSessions:
    """Item 1: every session's spend survives, whatever the interleaving."""

    def test_a_then_b_then_a_again(self, tmp_path):
        a = start_run("censuses", "r1", candidates_dir=tmp_path)
        a.usage.charge(HAIKU, DOLLAR, 0)
        a.finish()
        b = start_run("censuses", "r1", candidates_dir=tmp_path)
        b.usage.charge(HAIKU, DOLLAR, 0)
        b.finish()
        a.usage.charge(HAIKU, DOLLAR, 0)
        a.finish()
        usage = json.loads((a.dir / "usage.json").read_text())
        assert usage["n_calls"] == 3 and usage["total_cost_usd"] == pytest.approx(3.0)
        rj = json.loads((a.dir / "run.json").read_text())
        assert [s["session_id"] for s in rj["sessions"]] == [a.session_id, b.session_id]
        assert rj["sessions"][0]["usage"]["n_calls"] == 2 and rj["sessions"][1]["usage"]["n_calls"] == 1
        assert rj["cost_usd"] == pytest.approx(3.0)

    def test_both_read_before_either_writes(self, tmp_path):
        a = start_run("censuses", "r1", candidates_dir=tmp_path)
        b = start_run("censuses", "r1", candidates_dir=tmp_path)
        a.usage.charge(HAIKU, DOLLAR, 0)
        b.usage.charge(HAIKU, DOLLAR, 0)
        a.run_json()  # both look at the on-disk state before either writes
        b.run_json()
        a.finish()
        b.finish()
        usage = json.loads((a.dir / "usage.json").read_text())
        assert usage["n_calls"] == 2 and usage["total_cost_usd"] == pytest.approx(2.0)
        rj = json.loads((a.dir / "run.json").read_text())
        assert sorted(s["session_id"] for s in rj["sessions"]) == sorted([a.session_id, b.session_id])

    def test_two_processes_checkpointing(self, tmp_path):
        ctx = mp.get_context("spawn")
        barrier = ctx.Barrier(2)
        procs = [ctx.Process(target=_session_worker, args=(str(tmp_path), barrier)) for _ in range(2)]
        for p in procs:
            p.start()
        for p in procs:
            p.join(180)
            assert p.exitcode == 0
        d = tmp_path / "runs" / "censuses" / "r1"
        usage = json.loads((d / "usage.json").read_text())
        assert usage["n_calls"] == 2 * SESSION_STEPS
        assert usage["total_cost_usd"] == pytest.approx(2 * SESSION_STEPS * 0.01)
        rj = json.loads((d / "run.json").read_text())
        assert len(rj["sessions"]) == 2
        assert sum(s["usage"]["n_calls"] for s in rj["sessions"]) == 2 * SESSION_STEPS


SESSION_STEPS = 20


def _session_worker(cand_dir: str, barrier) -> None:
    from assistant_axis.gapgen.runs import start_run as sr
    run = sr("censuses", "r1", candidates_dir=Path(cand_dir))
    barrier.wait()
    for _ in range(SESSION_STEPS):
        run.usage.charge(HAIKU, 10_000, 0)  # $0.01
        run.finish()  # checkpoint


def test_refusal_reason_reaches_stderr(capsys):
    """Item 2: an uncaught CostRefused (exit 2) must not be silent."""
    with pytest.raises(SystemExit) as ei:
        confirm_or_abort(25.0, 5.0, confirm_expensive=True)
    assert ei.value.code == 2
    assert "over the $20 line" in capsys.readouterr().err


def test_refusal_reason_reaches_stderr_in_a_real_process():
    out = subprocess.run([sys.executable, "-c",
                          "from assistant_axis.gapgen.cost import confirm_or_abort\n"
                          "confirm_or_abort(25, 5, confirm_expensive=True)\n"],
                         cwd=REPO, capture_output=True, text=True, timeout=120,
                         env={**{k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}, "TMPDIR": "/tmp"})
    assert out.returncode == 2 and "over the $20 line" in out.stderr


class TestNonBudgetFailure:
    """Item 3: any exception in a batch stops new calls; paid responses kept."""

    def test_exception_in_first_batch_stops_the_stage(self, tmp_path, monkeypatch):
        from assistant_axis.gapgen import filter_rubric as fr
        real = fr.parse_batch
        n = {"parse": 0}

        def flaky(text, ids, **kw):
            n["parse"] += 1
            if n["parse"] == 1:
                raise RuntimeError("injected parser crash")
            return real(text, ids, **kw)

        monkeypatch.setattr(fr, "parse_batch", flaky)
        client = FakeAsyncAnthropic(costly_responder, delay=0.01)
        usage = GuardedUsage(budget_usd=100.0)
        resp_path = tmp_path / "responses.jsonl"
        words = [f"word{i}" for i in range(40)]
        runner = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model=None, usage=usage,
                              batch_size=1, concurrency=2, probe=False, second_opinion=False,
                              zipf_fn=lambda w: 4.0, wordnet=False, responses_path=resp_path)
        with pytest.raises(RuntimeError, match="injected"):
            runner.run([FilterItem(key=f"{w}#1", label=w) for w in words])
        calls = len(client.calls)
        assert calls <= 3  # the failing call plus at most concurrency - 1 in flight (+1 slot race)
        assert usage.n_calls == calls
        assert len(runner.responses) == calls  # the failing batch's paid response is kept
        assert len(resp_path.read_text().splitlines()) == calls
        classified = [r for r in runner.results.values() if r.stage == "classified"]
        assert len(classified) == calls - 1


class TestTornMultibyte:
    """Item 4: a line cut inside a UTF-8 character must not make the registry unusable."""

    TORN = '{"key": "naïve#1", "label": "naï'.encode("utf-8")[:-1]

    def test_append_fold_compact(self, tmp_path):
        reg = tmp_path / "registry.jsonl"
        submit_candidates([C("stubborn")], registry_path=reg)
        with open(reg, "ab") as fh:
            fh.write(self.TORN)
        rep = submit_candidates([C("timid")], registry_path=reg)
        assert rep.n_new == 1
        r = Registry(reg)
        assert set(r.fold()) == {"stubborn#1", "timid#1"} and r.n_malformed == 1
        with pytest.raises(ValueError):
            compact(reg)
        c = compact(reg, set_aside_malformed=True)
        assert c.rejected_path.read_bytes() == self.TORN + b"\n"
        assert self.TORN in c.backup_path.read_bytes()
        assert set(Registry(reg).fold()) == {"stubborn#1", "timid#1"}


def test_object_line_without_key_is_malformed(tmp_path):
    """Item 5a: compact must refuse rather than drop a keyless object line."""
    reg = tmp_path / "registry.jsonl"
    submit_candidates([C("stubborn")], registry_path=reg)
    with open(reg, "a") as fh:
        fh.write('{"stem": "orphan", "rev": 1}\n')
    r = Registry(reg)
    r.fold()
    assert r.n_malformed == 1
    with pytest.raises(ValueError, match="malformed"):
        compact(reg)


def test_writer_lock_inside_reader_lock_raises(tmp_path):
    """Item 5b: flock cannot upgrade; taking the writer lock while this thread
    holds the reader lock must raise at once, not block for ever."""
    reg = tmp_path / "registry.jsonl"
    submit_candidates([C("stubborn")], registry_path=reg)
    r = Registry(reg)
    out = {}

    def body():
        with r._read_locked():
            try:
                with r.locked():
                    out["entered"] = True
            except RuntimeError as exc:
                out["raised"] = str(exc)

    t = threading.Thread(target=body, daemon=True)
    t.start()
    t.join(3)
    assert not t.is_alive(), "blocked (deadlock) instead of raising"
    assert "raised" in out and "entered" not in out


def test_platform_dirty_files_ignores_unrelated_paths(tmp_path):
    """Item 5c: only the platform's own code and prompt paths count."""
    from assistant_axis.gapgen.runs import PLATFORM_PATHS, platform_dirty_files
    repo = tmp_path / "repo"
    (repo / "assistant_axis" / "gapgen").mkdir(parents=True)
    (repo / "reports").mkdir()
    (repo / "assistant_axis" / "gapgen" / "a.py").write_text("x = 1\n")
    (repo / "reports" / "x.md").write_text("report\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")}, "TMPDIR": "/tmp"}
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(git + cmd, cwd=repo, check=True, env=env, capture_output=True)
    assert platform_dirty_files(repo) == []
    (repo / "reports" / "x.md").write_text("edited report\n")
    assert platform_dirty_files(repo) == []
    (repo / "assistant_axis" / "gapgen" / "a.py").write_text("x = 2\n")
    assert platform_dirty_files(repo) == [" M assistant_axis/gapgen/a.py"]
    assert "assistant_axis/gapgen" in PLATFORM_PATHS and "data_analysis/gap_generation" in PLATFORM_PATHS
