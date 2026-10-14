"""``data_analysis/gap_generation/noun_relabel.py``: check, the backlog and roles streams, the Haiku pilot (noun
normalization plan, sections 7 and 8).  A tmp registry and a tmp data dir; FakeLookups; a fake Anthropic client."""
import hashlib
import json

import pytest

from assistant_axis.gapgen import nouns as N
from assistant_axis.gapgen import registry as R
from assistant_axis.gapgen.registry import Candidate, Registry, read_candidates, submit_candidates
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.test_gapgen_nouns import fake
from data_analysis.gap_generation import noun_relabel as NR

D = N.Derivation


def lookups():
    base = fake()
    pos = {**base._pos, "snob": ["n"], "snobby": ["a"], "beggar": ["n", "v"], "beggarly": ["a"], "priest": ["n"],
           "priestly": ["a"], "liar": ["n"], "charlatan": ["n"]}
    lexfiles = {**base._lexfiles, "snob": {"noun.person"}, "beggar": {"noun.person"}, "priest": {"noun.person"},
                "liar": {"noun.person"}, "charlatan": {"noun.person"}}
    derivations = {**base._derivations, "snob": [D("snobby", "noun.person", "befitting snobs")],
                   "beggar": [D("beggarly", "noun.person", "in the manner of a beggar")],
                   "priest": [D("priestly", "noun.person", "befitting a priest")]}
    return N.FakeLookups(pos=pos, lexfiles=lexfiles, derivations=derivations, definitions=base._definitions,
                         mates=base._mates, zipf=base._zipf)


LK = lookups()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(NR, "_lookups", lambda: LK)
    data = tmp_path / "data"
    (data / "traits" / "instructions").mkdir(parents=True)
    (data / "roles" / "instructions").mkdir(parents=True)
    (data / "traits" / "instructions" / "foolish.json").write_text(json.dumps(
        {"positive_label": "foolish", "description": "This means acting without sense."}))
    (data / "roles" / "instructions" / "priest.json").write_text(json.dumps({"description": "A priest is ..."}))
    (data / "roles" / "instructions" / "beggar.json").write_text(json.dumps({"description": "A beggar is ..."}))
    (data / "roles" / "instructions" / "liar.json").write_text(json.dumps({"description": "A liar is ..."}))
    (data / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "beggar", "label": "beggar", "entity_type": "role", "status": "done"},
        {"stem": "kind", "label": "kind", "entity_type": "trait", "status": "candidate"}]}, indent=2))
    cdir = tmp_path / "candidates"
    reg = cdir / "registry.jsonl"
    submit_candidates([Candidate(surface=s, generator="censuses", run_id="r1") for s in
                       ("pedant", "fool", "snob", "snobby", "calm", "charlatan")], registry_path=reg, relabel=None)
    rg = Registry(reg)
    rg.update_many({"pedant#1": {"filter": {"verdict": "trait"}}, "charlatan#1": {"filter": {"verdict": "trait"},
                                                                                 "gloss": "a fraud"}})
    # a row already linked at this helper version
    nb, ab = N.relabel_blocks("snob#1", "snobby#1", N.relabel("snob", lookups=LK), run="censuses/r1", now="T")
    rg.update_many({"snob#1": {"relabel": nb}, "snobby#1": {"relabel": ab}})
    # a priest held on the roles list
    submit_candidates([Candidate(surface="priest", generator="censuses", run_id="r1")], registry_path=reg,
                      relabel=None)
    rg.update_many({"priest#1": {"holding": "roles"}})
    return {"data": data, "cdir": cdir, "reg": reg}


def run(env, *args):
    return NR.main(["--registry", str(env["reg"]), "--data-dir", str(env["data"]), "--candidates-dir",
                    str(env["cdir"]), *args])


def test_check_prints(env, capsys):
    assert run(env, "check", "pedant", "rat", "bit of a pedant") == 0
    out = capsys.readouterr().out
    assert "pedant: pedantic [derivation; noun.person" in out
    assert "rat: no relabel (other_noun)" in out and "bit of a pedant: no relabel (phrase)" in out


class TestBacklog:
    def test_dry_run_writes_nothing(self, env, capsys, tmp_path):
        before = env["reg"].read_bytes()
        assert run(env, "backlog") == 0
        out = capsys.readouterr().out
        assert env["reg"].read_bytes() == before
        assert not (env["cdir"] / "runs" / "noun_relabel").exists()
        assert "backlog: 3 nouns relabel (1 already linked" in out
        assert '"corpus": 1' in out and '"new": 2' in out and "DRY-RUN" in out

    def test_dry_run_report(self, env, tmp_path):
        rep = tmp_path / "scratch" / "backlog_report.md"
        assert run(env, "backlog", "--report", str(rep)) == 0
        text = rep.read_text()
        assert "| pedant#1 | registry | trait | pedantic (pedantic#1) | new | derivation link from 'pedant' " \
               "(noun.person) |" in text
        # a corpus trait is a link relative to the report (the hotlink rule)
        assert "[foolish](../data/traits/instructions/foolish.json) (corpus trait)" in text

    def test_apply(self, env, monkeypatch, capsys):
        seen = {}
        real = R.submit_candidates

        def spy(cands, **kw):
            p = env["cdir"] / "runs" / "noun_relabel" / "backlog-x" / "candidates.jsonl"
            seen["recorded_first"] = p.exists()
            seen["relabel"] = kw.get("relabel")
            return real(cands, **kw)
        monkeypatch.setattr(NR, "submit_candidates", spy)
        assert run(env, "backlog", "--apply", "--run-id", "backlog-x") == 0
        out = capsys.readouterr().out
        assert seen == {"recorded_first": True, "relabel": None}
        rows = Registry(env["reg"]).fold()
        assert rows["pedant#1"]["relabel"]["to_key"] == "pedantic#1"
        ab = rows["pedantic#1"]["relabel"]
        assert ab["from_key"] == "pedant#1" and ab["run"] == "noun_relabel/backlog-x"
        assert rows["pedantic#1"]["sources"][0]["source_ref"] == "relabel:derivation:pedant#1"
        assert rows["pedantic#1"]["sources"][0]["generator"] == "noun_relabel"
        assert rows["fool#1"]["relabel"]["to_corpus_stem"] == "foolish" and "foolish#1" not in rows
        d = env["cdir"] / "runs" / "noun_relabel" / "backlog-x"
        cands = read_candidates(d / "candidates.jsonl")
        assert [(c.surface, c.source_ref) for c in cands] == [("pedantic", "relabel:derivation:pedant#1"),
                                                              ("priestly", "relabel:derivation:priest#1")]
        meta = json.loads((d / "run.json").read_text())
        assert meta["helper_version"] == N.HELPER_VERSION and meta["rules"] == N.rules_sha256()
        assert meta["registry_snapshot_sha256"] and meta["counts"]["n_relabelled"] == 3
        assert json.loads((d / "usage.json").read_text())["total_cost_usd"] == 0
        assert (d / "backlog_report.md").exists()
        assert "traithood_filter.py --batch-id backlog-x --run noun_relabel/backlog-x --pipeline split" in out
        assert "novelty_score.py score --batch-id backlog-x --run noun_relabel/backlog-x --budget-usd 1" in out
        # idempotent: a second run writes nothing
        after = env["reg"].read_bytes()
        assert run(env, "backlog", "--apply", "--run-id", "backlog-x") == 0
        assert env["reg"].read_bytes() == after
        assert "nothing to link" in capsys.readouterr().out


class TestRoles:
    def test_dry_run(self, env, capsys):
        before = env["reg"].read_bytes()
        assert run(env, "roles") == 0
        out = capsys.readouterr().out
        assert env["reg"].read_bytes() == before
        assert "source role: looked at 3, relabel 2" in out
        assert "source queue_role: looked at 1, relabel 1" in out
        assert "source roles_list: looked at 1, relabel 1" in out
        assert "distinct new adjectives: 2: beggarly, priestly" in out

    def test_apply_leaves_role_files_and_queue_alone(self, env):
        files = {p: p.read_bytes() for p in (env["data"] / "roles" / "instructions").glob("*.json")}
        queue = (env["data"] / "seed_queue.json").read_bytes()
        assert run(env, "roles", "--apply", "--run-id", "roles-x") == 0
        assert {p: p.read_bytes() for p in files} == files
        assert (env["data"] / "seed_queue.json").read_bytes() == queue
        rows = Registry(env["reg"]).fold()
        assert rows["priest#1"]["label"] == "priest" and rows["priest#1"]["holding"] == "roles"
        assert rows["priest#1"]["relabel"]["to_key"] == "priestly#1"
        refs = sorted(s["source_ref"] for s in rows["beggarly#1"]["sources"])
        assert refs == ["relabel:derivation:queue_role:beggar", "relabel:derivation:role:beggar"]
        b = rows["beggarly#1"]["relabel"]
        assert b["from_key"] is None and b["from_source"] == "role:beggar" and b["from_surface"] == "beggar"
        assert N.route_text(b) == "derivation link from 'beggar' (noun.person)"
        # the held row is the first link of priestly (role:priest comes first, but it has no row)
        assert {s["source_ref"] for s in rows["priestly#1"]["sources"]} == {
            "relabel:derivation:role:priest", "relabel:derivation:roles_list:priest#1"}


    def test_rerun_under_a_new_run_id_adds_nothing(self, env, capsys):
        """Review S2: role-file and queue items have no noun row; a rerun (the default run id is dated) must not append
        a second source to their adjective rows."""
        assert run(env, "roles", "--apply", "--run-id", "roles-a") == 0
        after = env["reg"].read_bytes()
        capsys.readouterr()
        assert run(env, "roles", "--apply", "--run-id", "roles-b") == 0
        assert env["reg"].read_bytes() == after
        assert not (env["cdir"] / "runs" / "noun_relabel" / "roles-b" / "candidates.jsonl").exists()


def test_streams_refuse_a_missing_registry(env, tmp_path, capsys):
    """Review S1: a checkout without the registry must not get a fresh one holding only adjectives."""
    missing = tmp_path / "elsewhere" / "registry.jsonl"
    rc = NR.main(["--registry", str(missing), "--data-dir", str(env["data"]), "--candidates-dir", str(env["cdir"]),
                  "backlog", "--apply", "--run-id", "b-x"])
    assert rc == 2 and "REFUSED" in capsys.readouterr().err and not missing.exists()

class TestPilot:
    def test_prompt_pinned_and_reason_first(self):
        from assistant_axis.gapgen import rubric_versions as RV
        sha = hashlib.sha256(N.PILOT_SYSTEM_PROMPT.encode()).hexdigest()
        assert RV.HISTORY["noun_relabel"][N.PILOT_PROMPT_VERSION] == sha
        assert "noun_relabel" in RV.current() and not [m for m in RV.mismatches() if m.startswith("noun_relabel")]
        tail = N.PILOT_SYSTEM_PROMPT[N.PILOT_SYSTEM_PROMPT.index("{"):]
        assert tail.index('"reason"') < tail.index('"adjective"')
        assert "reason first" in N.PILOT_SYSTEM_PROMPT

    def test_render_user(self):
        assert N.render_pilot_user("bookworm", "This means reading  voraciously.") == (
            "Noun: bookworm\nGloss: This means reading voraciously.")

    @pytest.fixture
    def pilot_env(self, env, monkeypatch, tmp_path):
        from assistant_axis.gapgen import runs
        monkeypatch.setattr(runs, "platform_dirty_files", lambda *a, **k: [])
        return env

    def test_dry_run_writes_nothing(self, pilot_env, tmp_path, capsys):
        out_dir = tmp_path / "pilot"
        assert run(pilot_env, "llm-pilot", "--n", "10", "--dry-run", "--out-dir", str(out_dir)) == 0
        out = capsys.readouterr().out
        assert not out_dir.exists()
        assert "llm-pilot: 2 rows" in out and "[person] charlatan#1: charlatan: a fraud" in out
        assert "[role] role:liar: liar" in out
        assert "Noun: charlatan\nGloss: a fraud" in out and "estimate:" in out

    def test_round_trip(self, pilot_env, tmp_path, monkeypatch):
        def responder(kw):
            assert system_text(kw) == N.PILOT_SYSTEM_PROMPT and "temperature" not in kw
            assert kw["model"] == N.PILOT_MODEL and kw["max_tokens"] == N.PILOT_MAX_TOKENS
            if "charlatan" in user_text(kw):
                return make_response('{"reason": "none in use", "adjective": null, "confidence": 0.8}',
                                     input_tokens=300, output_tokens=40)
            return make_response("I am not sure what you mean", input_tokens=300, output_tokens=40)
        client = FakeAsyncAnthropic(responder)
        monkeypatch.setattr(NR, "_anthropic_client", lambda: client)
        out_dir = tmp_path / "pilot"
        assert run(pilot_env, "llm-pilot", "--n", "10", "--budget-usd", "0.10", "--out-dir", str(out_dir)) == 0
        recs = [json.loads(x) for x in (out_dir / "responses.jsonl").read_text().splitlines()]
        assert {r["label"] for r in recs} == {"charlatan", "liar"}
        assert all(r["raw"] and r["prompt_sha256"] for r in recs)
        parsed = {json.loads(x)["label"]: json.loads(x)["parsed"]
                  for x in (out_dir / "parsed.jsonl").read_text().splitlines()}
        assert parsed["charlatan"] == {"reason": "none in use", "adjective": None, "confidence": 0.8}
        assert parsed["liar"] is None
        # usage is charged for the unparseable reply too
        usage = json.loads((out_dir / "usage.json").read_text())
        assert usage["n_calls"] == 2 and usage["total_cost_usd"] > 0
        assert "yield" in (out_dir / "readout.md").read_text().lower()
        assert json.loads((out_dir / "run.json").read_text())["counts"]["total"]["parsed"] == 1

    def test_parse_reply(self):
        assert N.parse_pilot_reply('```json\n{"reason": "r", "adjective": "Bookish", "confidence": 2}\n```') == {
            "reason": "r", "adjective": "bookish", "confidence": 1.0}
        assert N.parse_pilot_reply("no") is None and N.parse_pilot_reply(None) is None
        assert N.parse_pilot_reply('{"reason": "r", "adjective": 3}') is None
