"""Person privacy, hard (coding_plan_06 section 5a and section 8, "Person privacy"): a family (b) run with canned seeds
leaves no seed name, description or QID anywhere: not in any file under the tmp repository tree or the tmp
``$TMPDIR``, not in the registry, not in captured stdout and stderr.  The (b) prompt ids and custom ids are opaque,
the recorded ``user`` and ``text`` redacted, a real seed's name-bearing label dropped and a fictional one's kept; a
run interrupted after submission writes nothing person-linked and ``--cancel-open`` cancels its batch; the
``$TMPDIR`` fallback file exists only while the process runs; the dry run's sample is the fixed row.

**Every person in these tests is invented** (``llm_entropy_fakes``: distinctive made-up names, descriptions and
Wikidata ids), so that this file itself carries no real person's name."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen.generators.llm_entropy import seeds as SD
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests import llm_entropy_fakes as F
from assistant_axis.tests import structural_fakes as SF
from data_analysis.gap_generation import llm_entropy_generator as CLI

#: The fictional characters' eponym labels the fake model gives ("<last name>-like"): kept by the rule, so they are
#: the one place a fictional name may appear.
EPONYMS = [f"{name.split()[-1].lower()}-like" for _, name, _ in F.FICTIONAL_PEOPLE]
#: ... and the same labels as stems and registry keys.
EPONYM_FORMS = EPONYMS + [e.replace("-", "_") for e in EPONYMS]


def real_secrets() -> list[str]:
    out = []
    for qid, name, desc, *_ in F.REAL_PEOPLE:
        out += [qid, name, desc] + [t for t in re.findall(r"\w+", name) if len(t) >= 3]
        out += re.findall(r"\d{3,}", desc)
    return out


def fictional_secrets() -> list[str]:
    out = []
    for qid, name, desc in F.FICTIONAL_PEOPLE:
        out += [qid, name, desc] + [t for t in re.findall(r"\w+", name) if len(t) >= 3]
    return out


def leaks_in(text: str) -> list[str]:
    """Every secret found in ``text`` (case-insensitive), the fictional names outside their kept eponym labels."""
    low = text.lower()
    found = [s for s in real_secrets() if s.lower() in low]
    stripped = low
    for e in EPONYM_FORMS:
        stripped = stripped.replace(e, "")
    found += [s for s in fictional_secrets() if s.lower() in stripped]
    return found


def tree_leaks(*roots: Path) -> dict:
    out = {}
    for root in roots:
        for p in sorted(Path(root).rglob("*")):
            if p.is_file():
                try:
                    text = p.read_bytes().decode("utf-8", "replace")
                except OSError:
                    continue
                if p.suffix == ".gz":
                    import gzip
                    text = gzip.decompress(p.read_bytes()).decode("utf-8", "replace")
                hit = leaks_in(text)
                if hit:
                    out[str(p)] = hit
    return out


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


@pytest.fixture()
def env(tmp_path, monkeypatch):
    import tempfile
    repo = tmp_path / "repo"
    data = SF.write_corpus(repo)
    cand = repo / "candidates"
    reg = SF.write_registry(cand / "registry.jsonl", [SF.registry_row("zzother", "censuses", verdict="trait")])
    tmpdir = tmp_path / "tmpdir"
    tmpdir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmpdir))
    live = F.ScriptedAnthropic(default=F.family_reply)
    batch = F.FakeBatchClient(F.family_reply)
    clock = Clock()
    session = F.FakeWikidataSession()
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: live)
    monkeypatch.setattr(CLI, "_batch_client", lambda: batch)
    monkeypatch.setattr(CLI, "_wikidata", lambda args: SD.Throttle(session, clock=clock, sleep=clock.sleep))
    monkeypatch.setattr(CLI, "_dirty", lambda args: None)
    base = ["--data-dir", str(data), "--registry", str(reg), "--candidates-dir", str(cand)]
    env = SimpleNamespace(repo=repo, data=data, cand=cand, reg=reg, tmpdir=tmpdir, base=base, live=live,
                          batch=batch, session=session, monkeypatch=monkeypatch)
    env.run = lambda *argv: CLI.main([*base, *argv])
    env.rdir = lambda r: cand / "runs" / "llm_entropy" / r
    return env


def _records(env, run_id):
    p = env.rdir(run_id) / "responses.jsonl"
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


@pytest.mark.parametrize("transport", ["batches", "live"])
def test_a_b_run_leaves_no_person_anywhere(env, capsys, transport):
    assert env.run("generate", "--run-id", "pb", "--family", "b", "--real", "4", "--fictional", "3",
                   "--transport", transport) == 0
    assert env.run("postprocess", "--run-id", "pb") == 0
    assert env.run("collapse", "--run-id", "pb", "--embedder", "hash") == 0
    assert env.run("submit", "--run-id", "pb", "--all", "--no-relabel", "--transport", transport) == 0
    assert env.run("roles-report", "--run-id", "pb") == 0
    assert env.run("report", "--run-id", "pb") == 0
    out = capsys.readouterr()
    assert leaks_in(out.out + out.err) == []
    assert tree_leaks(env.repo, env.tmpdir) == {}
    recs = [r for r in _records(env, "pb") if r["family"] == "b"]
    assert len(recs) == 7
    for r in recs:
        assert re.fullmatch(r"b:[rf]\d{4}", r["prompt_id"])
        assert re.fullmatch(r"b-[rf]\d{4}-r1-s1-h55-[0-9a-f]{12}", r["custom_id"])
        assert r["user"].startswith(f"Person: <{r['prompt_id']}>.\n")
        assert "this person" in r["text"]
    labels = {it["label"] for r in recs for it in r["items"]}
    for qid, name, *_ in F.REAL_PEOPLE:
        assert f"{name.split()[-1].lower()}-like" not in labels          # a real seed's name label is dropped
    assert set(EPONYMS) <= labels                                       # a fictional character's eponym is kept
    assert sum(r["n_dropped_name_label"] for r in recs) == 4
    # what was paid for stays: the redacted answers and their usage
    usage = json.loads((env.rdir("pb") / "usage.json").read_text())
    assert usage["n_calls"] == 7
    # the registry holds no real name
    surfaces = {r["surface"] for r in Registry(env.reg).fold().values()}
    assert not any(s.lower() in " ".join(surfaces).lower() for s in real_secrets())
    # the fetch record: counts, eras and opaque ids only
    rec = json.loads((env.cand / "llm_entropy" / "person_seeds_fetch.json").read_text())
    (e,) = rec["runs"]
    assert e["n_real"] == 4 and e["n_fictional"] == 3 and e["licence"].startswith("CC0")
    assert [s["seed_id"] for s in e["seeds"]] == ["b:r0001", "b:r0002", "b:r0003", "b:r0004", "b:f0001",
                                                  "b:f0002", "b:f0003"]


def test_a_second_b_session_needs_force_and_continues_the_numbering(env):
    assert env.run("generate", "--run-id", "pb2", "--family", "b", "--real", "1", "--fictional", "1") == 0
    assert env.run("generate", "--run-id", "pb2", "--family", "b", "--real", "1", "--fictional", "1") == 2
    env.session._round = 0
    assert env.run("generate", "--run-id", "pb2", "--family", "b", "--real", "1", "--fictional", "1",
                   "--force") == 0
    ids = sorted({r["prompt_id"] for r in _records(env, "pb2")})
    assert ids == ["b:f0001", "b:f0002", "b:r0001", "b:r0002"]
    assert env.run("generate", "--run-id", "pb2", "--family", "b", "--resume") == 2      # no resume for (b)
    assert tree_leaks(env.repo, env.tmpdir) == {}


class CrashingBatches(F.FakeBatches):
    def retrieve(self, bid):
        raise RuntimeError("simulated crash while waiting")


def test_an_interrupted_run_writes_nothing_person_linked_and_cancel_open_cancels(env, capsys):
    crashing = SimpleNamespace(messages=SimpleNamespace(batches=CrashingBatches(F.family_reply)))
    env.monkeypatch.setattr(CLI, "_batch_client", lambda: crashing)
    with pytest.raises(RuntimeError):
        env.run("generate", "--run-id", "pi", "--family", "b", "--real", "2", "--fictional", "1")
    b = crashing.messages.batches
    assert len(b.created) == 1 and b.cancelled == [b.created[0]["id"]]          # asked to cancel on the way out
    assert _records(env, "pi") == []
    state = json.loads((env.rdir("pi") / "batches.json").read_text())
    assert state["waves"]["b_h55_s1"][0]["status"] == "submitted"
    assert tree_leaks(env.repo, env.tmpdir) == {}
    out = capsys.readouterr()
    assert leaks_in(out.out + out.err) == []
    # --cancel-open, with a client that works again: the batch is cancelled, its usage recorded, no answer kept
    good = SimpleNamespace(messages=SimpleNamespace(batches=b))
    b.retrieve = F.FakeBatches.retrieve.__get__(b)
    env.monkeypatch.setattr(CLI, "_batch_client", lambda: good)
    assert env.run("generate", "--run-id", "pi", "--family", "b", "--cancel-open") == 0
    stubs = _records(env, "pi")
    assert len(stubs) == 3 and all(s["text"] is None and s["abandoned"] and s["usage_raw"] for s in stubs)
    assert json.loads((env.rdir("pi") / "usage.json").read_text())["n_calls"] == 3
    state = json.loads((env.rdir("pi") / "batches.json").read_text())
    assert state["waves"]["b_h55_s1"][0]["status"] == "abandoned"
    assert tree_leaks(env.repo, env.tmpdir) == {}
    assert env.run("generate", "--run-id", "pi", "--family", "b", "--cancel-open") == 0     # nothing open now


def test_the_tmpdir_fallback_file_lives_only_while_the_process_runs(env):
    seen = []

    class Watching(F.FakeBatches):
        def create(self, *, requests):
            files = sorted(env.tmpdir.glob("llm_entropy_seeds_*.json"))
            seen.extend((f.name, oct(os.stat(f).st_mode & 0o777)) for f in files)
            return super().create(requests=requests)
    watching = SimpleNamespace(messages=SimpleNamespace(batches=Watching(F.family_reply)))
    env.monkeypatch.setattr(CLI, "_batch_client", lambda: watching)
    assert env.run("generate", "--run-id", "pt", "--family", "b", "--real", "2", "--fictional", "1",
                   "--tmp-seeds") == 0
    assert len(seen) == 1 and seen[0][1] == "0o600"
    assert list(env.tmpdir.iterdir()) == []                              # deleted when the process ended
    assert tree_leaks(env.repo) == {}


def test_collect_open_recovers_a_hard_killed_run_from_its_tmp_file(env):
    import random
    th = SD.Throttle(F.FakeWikidataSession(), clock=Clock(), sleep=lambda s: None)
    seeds = SD.fetch_real(2, session=th) + SD.fetch_fictional(1, session=th, rng=random.Random(0))
    path = CLI._write_tmp_seeds(seeds, "pk", "sess1")
    # the killed process had submitted its batch: the same calls, recorded in batches.json
    from assistant_axis.gapgen.batches import BatchTransport
    from assistant_axis.gapgen.generators.llm_entropy import prompts as P
    from assistant_axis.gapgen.generators.llm_entropy.calls import EntropyRunner
    rubric = P.load_rubric(P.SCAFFOLD_RUBRIC)
    calls = CLI._b_calls(seeds, runs=[1], model="claude-haiku-5-5", rubric=rubric)
    state = env.rdir("pk") / "batches.json"
    t = BatchTransport(EntropyRunner(batch_id="x", usage=None), env.batch, state)
    created = env.batch.batches.create(requests=[t._request(c) for c in calls])
    t.save_state({"batch_id": "pk_llm_entropy", "waves": {"b_h55_s1": [
        {"id": created.id, "custom_ids": [c.custom_id for c in calls], "status": "submitted", "submitted_at": None}]}})
    assert env.run("generate", "--run-id", "pk", "--family", "b", "--collect-open", str(path)) == 0
    assert len(env.batch.batches.created) == 1                          # collected, not submitted again
    recs = _records(env, "pk")
    assert len(recs) == 3 and all(r["ok"] and "this person" in r["text"] for r in recs)
    assert not path.exists()
    assert tree_leaks(env.repo, env.tmpdir) == {}
    fr = json.loads((env.cand / "llm_entropy" / "person_seeds_fetch.json").read_text())
    assert fr["runs"][0]["collected_by"] == "--collect-open"


def test_the_dry_run_shows_the_fixed_row_and_fetches_nothing(env, capsys):
    assert env.run("generate", "--run-id", "pd", "--family", "b", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "Person: Tian Yi (person, CBDB ID = 367824; died 1684)." in out
    assert env.session.calls == [] and not env.rdir("pd").exists()
    assert leaks_in(out) == []
