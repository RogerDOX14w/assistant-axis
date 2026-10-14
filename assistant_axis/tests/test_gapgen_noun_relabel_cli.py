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


class TestLlmApply:
    """``llm-apply``: the one-off Haiku pass over the pilot's whole population (Roger, 2026-10-14, "A 1 yes")."""

    @staticmethod
    def lookups():
        base = lookups()
        pos = {**base._pos, "bookworm": ["n"], "bookish": ["a"], "cad": ["n"], "caddish": ["a"], "zealot": ["n"],
               "zealous": ["a"]}
        lexfiles = {**base._lexfiles, "bookworm": {"noun.person"}, "cad": {"noun.person"}, "zealot": {"noun.person"}}
        definitions = {**base._definitions, "bookish": ["characterized by a love of books"],
                       "caddish": ["lacking the instincts of a gentleman"]}
        return N.FakeLookups(pos=pos, lexfiles=lexfiles, derivations=base._derivations, definitions=definitions,
                             mates=base._mates, zipf={**base._zipf, "glorbular": 0.4})

    @staticmethod
    def pilot_rec(key, label, raw, *, sha=None, stop="end_turn", at="2026-10-14T17:00:00+00:00"):
        return {"key": key, "label": label, "kind": "person", "prompt_version": N.PILOT_PROMPT_VERSION,
                "prompt_sha256": sha or hashlib.sha256(N.PILOT_SYSTEM_PROMPT.encode()).hexdigest(),
                "model": N.PILOT_MODEL, "raw": raw, "stop_reason": stop, "at": at}

    @pytest.fixture
    def lenv(self, env, monkeypatch):
        from assistant_axis.gapgen import runs
        lk = self.lookups()
        monkeypatch.setattr(NR, "_lookups", lambda: lk)
        monkeypatch.setattr(runs, "platform_dirty_files", lambda *a, **k: [])
        reg = env["reg"]
        submit_candidates([Candidate(surface=s, generator="censuses", run_id="r1") for s in
                           ("bookworm", "cad", "zealot", "old fogey", "zealous")], registry_path=reg, relabel=None)
        nb, ab = N.relabel_blocks("zealot#1", "zealous#1", N.Relabel("zealot", "zealous", N.LLM_RULE, None, None, 3.0),
                                  run="noun_relabel/llm-0", now="T")
        Registry(reg).update_many({**{k: {"filter": {"verdict": "trait"}, "gloss": f"the {k[:-2]} gloss"}
                                      for k in ("bookworm#1", "cad#1", "zealot#1", "old_fogey#1")},
                                   "zealot#1": {"filter": {"verdict": "trait"}, "relabel": nb},
                                   "zealous#1": {"relabel": ab}})
        pdir = env["cdir"] / "noun_relabel" / "llm_pilot_x"
        pdir.mkdir(parents=True)
        recs = [self.pilot_rec("bookworm#1", "bookworm", '{"reason": "r", "adjective": "bookish", "confidence": 0.9}'),
                self.pilot_rec("cad#1", "cad", '{"reason": "r", "adjective": "caddish", "confidence": 0.9}',
                               sha="0" * 64),                                     # another prompt: asked again
                self.pilot_rec("charlatan#1", "charlatan", '{"reason": "r", "adj', stop="max_tokens")]  # cut off
        (pdir / "responses.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
        return {**env, "lk": lk}

    @staticmethod
    def client(monkeypatch, replies: dict):
        def responder(kw):
            assert system_text(kw) == N.PILOT_SYSTEM_PROMPT and "temperature" not in kw
            assert kw["model"] == N.PILOT_MODEL and kw["max_tokens"] == N.PILOT_MAX_TOKENS
            noun = user_text(kw).split("\n")[0].removeprefix("Noun: ")
            return make_response(replies[noun], input_tokens=440, output_tokens=300)
        c = FakeAsyncAnthropic(responder)
        monkeypatch.setattr(NR, "_anthropic_client", lambda: c)
        return c

    @staticmethod
    def no_client(monkeypatch):
        def boom():
            raise AssertionError("no call may be sent")
        monkeypatch.setattr(NR, "_anthropic_client", boom)

    REPLIES = {"cad": '{"reason": "caddish means like a cad", "adjective": "caddish", "confidence": 0.8}',
               "charlatan": '{"reason": "none in use", "adjective": null, "confidence": 0.9}',
               "liar": '{"reason": "dishonest is a synonym", "adjective": null, "confidence": 0.9}'}

    def test_selection_is_the_pilot_population_less_linked_nouns_and_phrases(self, lenv):
        rows = Registry(lenv["reg"]).fold()
        sel, n_linked = NR.llm_selection(rows, lookups=lenv["lk"], data_dir=lenv["data"])
        assert [r["key"] for r in sel] == ["bookworm#1", "cad#1", "charlatan#1", "role:liar"]
        assert n_linked == 1                                   # zealot: an earlier LLM link
        person, role = NR.pilot_pool(rows, lookups=lenv["lk"], data_dir=lenv["data"])
        assert "zealot#1" in {r["key"] for r in person} and "old_fogey#1" not in {r["key"] for r in person}

    def test_pilot_answers_reused_by_prompt_sha(self, lenv):
        ans = NR.load_answers(lenv["cdir"])
        assert set(ans) == {"bookworm#1"}                      # cad: another sha; charlatan: cut off at max_tokens
        assert ans["bookworm#1"]["parsed"]["adjective"] == "bookish"
        assert ans["bookworm#1"]["reused_from"] == "llm_pilot_x"

    def test_yield_rule_and_gates(self, lenv):
        lk = lenv["lk"]

        def acc(label, adj):
            return NR.accept_answer(label, {"adjective": adj, "reason": "r", "confidence": 1.0}, lookups=lk)
        assert acc("cad", "caddish") == ("caddish", None)                 # an OEWN adjective
        assert acc("cad", "caddy-ish") == ("caddy-ish", None)             # not in OEWN, Zipf 3.0 (the fake's default)
        assert acc("cad", "glorbular") == (None, "not_established")       # neither
        assert acc("cad", None) == (None, "none")
        assert acc("cad", "like a cad") == (None, "phrase")
        assert acc("cad", "cad") == (None, "same_as_noun")
        assert acc("cad", "---") == (None, "refused_stem")
        assert NR.accept_answer("cad", None, lookups=lk) == (None, "unparsed")

    def test_dry_run_writes_nothing(self, lenv, monkeypatch, capsys):
        self.no_client(monkeypatch)
        before = lenv["reg"].read_bytes()
        assert run(lenv, "llm-apply", "--dry-run") == 0
        out = capsys.readouterr().out
        assert lenv["reg"].read_bytes() == before
        assert not (lenv["cdir"] / "runs" / "noun_relabel").exists()
        assert "4 nouns selected" in out and "1 person rows already linked" in out
        assert 'answers reused: 1 ({"llm_pilot_x": 1}); to ask: 3' in out
        assert "estimate" in out and "Noun: cad\nGloss: the cad gloss" in out and "DRY-RUN" in out

    def test_apply_writes_llm_links_and_is_idempotent(self, lenv, monkeypatch, capsys):
        from assistant_axis.gapgen.review_app.decisions import relabel_card
        client = self.client(monkeypatch, self.REPLIES)
        seen = {}
        real = R.submit_candidates

        def spy(cands, **kw):
            seen["recorded_first"] = (lenv["cdir"] / "runs" / "noun_relabel" / "llm-x" / "candidates.jsonl").exists()
            seen["relabel"] = kw.get("relabel")
            return real(cands, **kw)
        monkeypatch.setattr(NR, "submit_candidates", spy)
        assert run(lenv, "llm-apply", "--run-id", "llm-x", "--budget-usd", "0.10") == 0
        out = capsys.readouterr().out
        assert len(client.messages.calls) == 3 and seen == {"recorded_first": True, "relabel": None}
        rows = Registry(lenv["reg"]).fold()
        nb, ab = rows["cad#1"]["relabel"], rows["caddish#1"]["relabel"]
        assert nb["to_key"] == "caddish#1" and nb["rule"] == "llm" and nb["helper_version"] == N.HELPER_VERSION
        assert {k: nb[k] for k in ("model", "prompt_version", "confidence", "reason")} == {
            "model": N.PILOT_MODEL, "prompt_version": 1, "confidence": 0.8, "reason": "caddish means like a cad"}
        assert ab["from_key"] == "cad#1" and ab["rule"] == "llm" and ab["run"] == "noun_relabel/llm-x"
        assert ab["model"] == N.PILOT_MODEL and ab["confidence"] == 0.8
        assert N.route_text(ab) == "LLM relabel from 'cad', sense not checked"
        assert N.route_text(nb) == "adjective 'caddish' by LLM relabel, sense not checked"
        assert relabel_card(rows["caddish#1"])["route"] == "LLM relabel from 'cad', sense not checked"
        src = rows["caddish#1"]["sources"][0]
        assert (src["generator"], src["run_id"], src["source_ref"], src["gloss_hint"]) == (
            "noun_relabel", "llm-x", "relabel:llm:cad#1", "lacking the instincts of a gentleman")
        # the pilot's answer, reused without a call
        assert rows["bookworm#1"]["relabel"]["to_key"] == "bookish#1"
        assert rows["bookish#1"]["relabel"]["from_key"] == "bookworm#1"
        assert "relabel" not in rows["charlatan#1"] or not rows["charlatan#1"].get("relabel")
        d = lenv["cdir"] / "runs" / "noun_relabel" / "llm-x"
        assert [(c.surface, c.source_ref) for c in read_candidates(d / "candidates.jsonl")] == [
            ("bookish", "relabel:llm:bookworm#1"), ("caddish", "relabel:llm:cad#1")]
        resp = [json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines()]
        assert sorted(r["label"] for r in resp) == ["cad", "charlatan", "liar"]
        assert all(r["raw"] and r["max_tokens"] == N.PILOT_MAX_TOKENS for r in resp)
        meta = json.loads((d / "run.json").read_text())
        assert meta["helper_version"] == N.HELPER_VERSION and meta["registry_snapshot_sha256"]
        assert meta["prompt_sha256"] == hashlib.sha256(N.PILOT_SYSTEM_PROMPT.encode()).hexdigest()
        assert (meta["n_selected"], meta["n_reused"], meta["n_asked"]) == (4, 1, 3)
        assert meta["rejected"] == {"none": 2} and meta["counts"]["by_rule"] == {"llm": 2}
        usage = json.loads((d / "usage.json").read_text())
        assert usage["n_calls"] == 3 and usage["total_cost_usd"] > 0
        report = (d / "llm_report.md").read_text()
        assert "LLM relabel from 'cad', sense not checked" in report and "## Every answer" in report
        assert "traithood_filter.py --batch-id llm-x --run noun_relabel/llm-x" in out
        assert "novelty_score.py score --batch-id llm-x --run noun_relabel/llm-x" in out
        # a rerun (a new run id, its answers on record) sends nothing and writes nothing
        self.no_client(monkeypatch)
        after = lenv["reg"].read_bytes()
        assert run(lenv, "llm-apply", "--run-id", "llm-y") == 0
        assert "nothing to do" in capsys.readouterr().out
        assert lenv["reg"].read_bytes() == after and not (d.parent / "llm-y").exists()

    def test_parse_failure_counted_not_written(self, lenv, monkeypatch, capsys):
        self.client(monkeypatch, {**self.REPLIES, "liar": "I am not sure what you mean"})
        assert run(lenv, "llm-apply", "--run-id", "llm-x") == 0
        d = lenv["cdir"] / "runs" / "noun_relabel" / "llm-x"
        meta = json.loads((d / "run.json").read_text())
        assert meta["rejected"] == {"none": 1, "unparsed": 1} and meta["n_parsed"] == 2
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 3          # the unparsed reply is charged
        assert "I am not sure" in (d / "responses.jsonl").read_text()
        assert [c.source_ref for c in read_candidates(d / "candidates.jsonl")] == [
            "relabel:llm:bookworm#1", "relabel:llm:cad#1"]
        # the next run asks the unparsed one again, and only it
        capsys.readouterr()
        client = self.client(monkeypatch, self.REPLIES)
        assert run(lenv, "llm-apply", "--run-id", "llm-y", "--dry-run") == 0
        assert "to ask: 1" in capsys.readouterr().out and not client.messages.calls

    def test_budget_refusal(self, lenv, monkeypatch, capsys):
        self.no_client(monkeypatch)
        before = lenv["reg"].read_bytes()
        assert run(lenv, "llm-apply", "--run-id", "llm-x", "--budget-usd", "0.0001") == 2
        assert lenv["reg"].read_bytes() == before and not (lenv["cdir"] / "runs" / "noun_relabel").exists()

    def test_dirty_tree_refusal(self, lenv, monkeypatch, capsys):
        from assistant_axis.gapgen import runs
        self.no_client(monkeypatch)
        monkeypatch.setattr(runs, "platform_dirty_files", lambda *a, **k: ["assistant_axis/gapgen/nouns.py"])
        before = lenv["reg"].read_bytes()
        assert run(lenv, "llm-apply", "--run-id", "llm-x") == 2
        assert "REFUSED" in capsys.readouterr().err and lenv["reg"].read_bytes() == before
