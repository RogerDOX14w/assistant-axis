"""Test 13 of coding plan 16 (§ 8): B's lay-role call.  ``build_user`` for both variants byte-pinned against the
rendered samples of the rubric file (which § 7a.5 of the plan copies); ``parse_lay`` on good, prose-prefixed, fenced
and broken answers; ``combine_readings`` keeps the union with support, takes ``distinct_persona`` by majority and
never drops a one-reading role; the call on a fake client records every response, counts a refusal as a failed call
and asks it once more, charges the usage, resumes from its records, and runs through the Batches transport; the
CLI's dry run renders both variants and sends nothing.  No network, no key."""
import asyncio
import hashlib
import json
import re

import pytest

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.generators.professions import lay as LAY
from assistant_axis.tests import professions_fakes as F
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text

BOUNCER_USER = (
    '{"group": {"code": "33-9032.00", "title": "Security Guards", "alternate_title": "Bouncer"},\n'
    ' "occupations": [\n'
    '  {"id": 1, "title": "Security Guards", "description": "Guard, patrol, or monitor premises to prevent theft, '
    'violence, or infractions of rules. May operate x-ray and metal detector equipment."}\n'
    ' ]}')
#: sha256 of variant 1's rendering in the rubric file (29-1210 Physicians, 19 O*NET occupations).
PHYSICIANS_SHA256 = "817d2f48903ef16594e423fe4f4f556315b6ea4878ef0f916539d41ec690bc6c"


def bouncer_group():
    return LAY.group_from_row({"kind": "job_title", "code": "33-9032.00", "occupation": "Security Guards",
                               "title": "Bouncer", "label": "bouncer", "description": F.OCCUPATIONS["33-9032.00"][1]})


def physicians_group(n=None):
    occ = [{"code": c, "title": t, "description": d} for c, (t, d) in F.OCCUPATIONS.items() if c.startswith("29-12")]
    return LAY.group_from_row({"kind": "broad", "code": "29-1210", "title": "Physicians", "employment": 782430,
                               "detailed": occ[:n] if n else occ})


def rubric_samples():
    text = sr.rubric_path("profession_lay").read_text(encoding="utf-8")
    part = text.split("## Rendered samples", 1)[1].split("## Your notes", 1)[0]
    return re.findall(r"```text\n(.*?)\n```", part, re.S)


class TestBuildUser:
    def test_variant_2_job_title_byte_for_byte(self):
        g = bouncer_group()
        assert LAY.build_user(g) == BOUNCER_USER
        assert g.id == "job_title:33-9032.00:bouncer" and g.source_ref == "onet_title:33-9032.00:bouncer"

    def test_both_variants_match_the_rubric_file_s_rendered_samples(self):
        v1, v2 = rubric_samples()
        assert v2 == BOUNCER_USER
        head, occ = json.loads(v1)["group"], json.loads(v1)["occupations"]
        g = LAY.LayGroup(id="broad:29-1210", kind="broad", code=head["code"], title=head["title"],
                         occupations=[{"code": f"x{o['id']}", "title": o["title"], "description": o["description"]}
                                      for o in occ])
        assert [o["id"] for o in occ] == list(range(1, 20))
        assert LAY.build_user(g) == v1
        assert hashlib.sha256(v1.encode()).hexdigest() == PHYSICIANS_SHA256

    def test_one_occupation_a_line_ids_in_order(self):
        u = LAY.build_user(physicians_group())
        lines = u.split("\n")
        assert lines[0] == '{"group": {"code": "29-1210", "title": "Physicians"},'
        assert lines[1] == ' "occupations": ['
        assert [json.loads(x.strip().rstrip(","))["id"] for x in lines[2:-1]] == [1, 2, 3]
        assert lines[-1] == " ]}" and json.loads(u)["occupations"][2]["title"] == "Pediatricians, General"
        assert "782430" not in u                     # employment is not shown

    def test_render_and_the_pinned_rubric(self):
        rub = LAY.load_rubric()
        assert rub["name"] == "profession_lay" and rub["version"] >= 1 and len(rub["sha256"]) == 64
        r = LAY.render(bouncer_group(), rub)
        assert rub["text"] in r and BOUNCER_USER in r
        assert '"alternate_title"' in rub["text"] and "reason first" in rub["text"]

    def test_an_unpinned_text_is_refused(self, tmp_path):
        import shutil
        d = tmp_path / "rubrics"
        shutil.copytree(sr.RUBRICS_DIR, d)
        p = d / "profession_lay.md"
        p.write_text(p.read_text().replace("Give a reason in one short sentence first", "Give a reason first"))
        with pytest.raises(LAY.RubricNotPinned):
            LAY.load_rubric(d)
        assert LAY.load_rubric(d, allow_unpinned=True)["version"] is None


class TestParse:
    def test_good(self):
        d, err = LAY.parse_lay(F.lay_answer([F.role("doctor", (1, 2)), F.role("Cardiologist", (2,), True)]))
        assert err is None and d["reason"] == "One short reason." and d["n_invalid"] == 0
        assert [(r["role"], r["stem"], r["covers"], r["distinct_persona"]) for r in d["roles"]] == \
            [("doctor", "doctor", [1, 2], False), ("cardiologist", "cardiologist", [2], True)]

    def test_prose_prefixed_and_fenced(self):
        body = F.lay_answer([F.role("bouncer", distinct=True)])
        assert LAY.parse_lay("Here is my answer:\n" + body)[0]["roles"][0]["role"] == "bouncer"
        assert LAY.parse_lay("```json\n" + body + "\n```")[0]["roles"][0]["role"] == "bouncer"

    def test_broken(self):
        assert LAY.parse_lay(None) == (None, "empty answer")
        assert LAY.parse_lay("no json here")[1] == "no JSON object"
        assert LAY.parse_lay('{"reason": "x", "roles": [')[1].startswith("invalid JSON")
        assert LAY.parse_lay('{"reason": "x", "roles": []} and more')[1] == "text after the JSON object"
        assert LAY.parse_lay('{"reason": "x"}')[1] == "no roles list"
        assert LAY.parse_lay('[1, 2]')[1] == "no JSON object" or LAY.parse_lay('[1, 2]')[0] is None

    def test_roles_are_cleaned_and_bad_ones_counted(self):
        d, _ = LAY.parse_lay(json.dumps({"reason": "r", "roles": [
            {"role": "The  Night Watchman.", "covers": ["1", 2, True], "distinct_persona": "true", "gloss": " A  b. "},
            {"role": "one two three four", "covers": [1]}, "not a dict", {"role": ""}]}))
        assert d["n_invalid"] == 3
        (r,) = d["roles"]
        assert (r["role"], r["stem"], r["covers"], r["distinct_persona"], r["gloss"]) == \
            ("night watchman", "night_watchman", [1, 2], True, "A b.")

    def test_an_empty_roles_list_is_an_answer(self):
        d, err = LAY.parse_lay('{"reason": "only another name", "roles": []}')
        assert err is None and d["roles"] == []


class TestCombine:
    def _r(self, *roles):
        return LAY.parse_lay(F.lay_answer(list(roles)))[0]

    def test_union_with_support_majority_and_one_reading_roles_kept(self):
        occ = physicians_group().occupations
        r1 = self._r(F.role("doctor", (1, 2, 3)), F.role("cardiologist", (2,), True, gloss="A cardiologist is X."))
        r2 = self._r(F.role("doctor", (1,)), F.role("cardiologist", (2,), False), F.role("anesthesiologist", (1,), True))
        r3 = self._r(F.role("Doctor", (3, 9)), F.role("cardiologist", (2,), True, gloss="A cardiologist is Y."))
        out = {r.stem: r for r in LAY.combine_readings([r1, r2, r3], occupations=occ)}
        assert list(out) == ["doctor", "cardiologist", "anesthesiologist"]
        d, c, a = out["doctor"], out["cardiologist"], out["anesthesiologist"]
        assert (d.support, d.n_readings, d.distinct_persona) == (3, 3, False)
        assert d.covers == ["29-1211.00", "29-1212.00", "29-1221.00"]          # id 9 is out of range: dropped
        assert (c.support, c.distinct_persona, c.votes["distinct_persona"], c.distinct_tie) == \
            (3, True, [True, False, True], False)
        assert c.gloss == "A cardiologist is X."                                 # from the first reading naming it
        assert (a.support, a.readings, a.distinct_persona) == (1, [2], True)    # one reading: kept

    def test_a_tie_is_not_distinct_and_missing_readings_count_as_missing(self):
        r1 = self._r(F.role("bouncer", distinct=True))
        r3 = self._r(F.role("bouncer", distinct=False))
        (b,) = LAY.combine_readings([r1, None, r3])
        assert (b.support, b.n_readings, b.readings, b.distinct_persona, b.distinct_tie) == (2, 2, [1, 3], False, True)
        assert LAY.combine_readings([None, None, None]) == []

    def test_agreement_is_a_diagnostic(self):
        rows = [{"n_readings": 3, "readings_asked": 3, "roles": [{"support": 3}, {"support": 1}]},
                {"n_readings": 2, "readings_asked": 3, "roles": [{"support": 2}]},
                {"n_readings": 0, "readings_asked": 3, "roles": []}]
        a = LAY.agreement(rows)
        assert a["n_groups_with_roles"] == 2 and a["n_roles"] == 3
        assert a["share_roles_named_by_every_reading"] == round(2 / 3, 4)
        assert a["share_groups_same_roles"] == 0.5 and a["readings_answered"] == 5 and a["readings_asked"] == 9


def _answers():
    phys = [F.lay_answer([F.role("doctor", (1, 2, 3)), F.role("cardiologist", (2,), True)]),
            F.lay_answer([F.role("doctor", (1, 2)), F.role("cardiologist", (2,), False),
                          F.role("anesthesiologist", (1,), True)]),
            F.refusal_response(),
            F.lay_answer([F.role("doctor", (1,)), F.role("cardiologist", (2,), True)])]
    return {"29-1210": phys,
            "33-9032.00:Bouncer": [F.lay_answer([F.role("bouncer", (1,), True)])]}


def _run(groups, tmp_path, client, *, resume=(), budget=1.0, transport_factory=None):
    usage = GuardedUsage(budget_usd=budget)
    res = asyncio.run(LAY.lay_groups(groups, client=client, usage=usage, readings=3,
                                     records_path=tmp_path / "lay_responses.jsonl", resume_records=resume,
                                     concurrency=1, retry_delays=(), run_id="r1",
                                     transport_factory=transport_factory))
    return res, usage


class TestCall:
    def test_three_readings_records_a_refusal_as_a_failed_call_and_asks_it_once_more(self, tmp_path):
        client = FakeAsyncAnthropic(F.lay_responder(_answers()))
        groups = [physicians_group(), bouncer_group()]
        res, usage = _run(groups, tmp_path, client)
        assert len(client.calls) == 7                                      # 6 calls + the refusal asked again
        kw = client.calls[0]
        assert "temperature" not in kw and kw["max_tokens"] == LAY.MAX_TOKENS and kw["model"] == "claude-haiku-5-5"
        assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert system_text(kw) == LAY.load_rubric()["text"] and user_text(kw) == LAY.build_user(groups[0])
        recs = [json.loads(x) for x in (tmp_path / "lay_responses.jsonl").read_text().splitlines()]
        assert len(recs) == 7
        bad = [r for r in recs if not r["ok"]]
        assert len(bad) == 1 and bad[0]["failure"] == "stop_reason refusal" and bad[0]["usage_raw"]["input_tokens"] == 900
        assert all(r["meta"]["rubric"] == "profession_lay" and r["step"] == "lay" for r in recs)
        w = res.wave
        assert w.n_retried == 1 and not w.failures and w.n_ok == 6 and w.n_attempted == 6
        assert usage.n_calls == 7 and usage.total_cost_usd > 0
        phys = {r.stem: r for r in res.roles["broad:29-1210"]}
        assert phys["doctor"].support == 3 and phys["cardiologist"].distinct_persona is True
        assert phys["anesthesiologist"].support == 1 and phys["cardiologist"].covers == ["29-1212.00"]
        (b,) = res.roles["job_title:33-9032.00:bouncer"]
        assert (b.role, b.support, b.distinct_persona, b.covers) == ("bouncer", 3, True, ["33-9032.00"])
        rows = LAY.lay_rows(groups, res)
        assert rows[1]["source_ref"] == "onet_title:33-9032.00:bouncer" and rows[0]["source_ref"] == "soc:29-1210"
        assert rows[0]["n_readings"] == 3 and rows[0]["failed"] is False

    def test_resume_sends_nothing_answered(self, tmp_path):
        groups = [physicians_group(), bouncer_group()]
        _run(groups, tmp_path, FakeAsyncAnthropic(F.lay_responder(_answers())))
        recs = [json.loads(x) for x in (tmp_path / "lay_responses.jsonl").read_text().splitlines()]
        client = FakeAsyncAnthropic(F.lay_responder({}))
        res, usage = _run(groups, tmp_path, client, resume=recs)
        assert client.calls == [] and usage.n_calls == 0 and res.wave.n_reused == 6
        assert {r.stem for r in res.roles["broad:29-1210"]} == {"doctor", "cardiologist", "anesthesiologist"}

    def test_a_group_that_never_parses_is_failed_and_counted(self, tmp_path):
        client = FakeAsyncAnthropic(F.lay_responder({"33-9032.00:Bouncer": "I would rather not say."}))
        res, _ = _run([bouncer_group()], tmp_path, client)
        assert res.roles["job_title:33-9032.00:bouncer"] == [] and res.n_readings["job_title:33-9032.00:bouncer"] == 0
        assert len(res.wave.failures) == 3 and res.wave.n_ok == 0 and len(client.calls) == 6
        assert LAY.lay_rows([bouncer_group()], res)[0]["failed"] is True

    def test_a_budget_stop_keeps_what_was_paid_for(self, tmp_path):
        client = FakeAsyncAnthropic(F.lay_responder(_answers()))
        res, usage = _run([physicians_group(), bouncer_group()], tmp_path, client, budget=0.0001)
        assert res.stopped is not None and len(client.calls) == 1
        recs = (tmp_path / "lay_responses.jsonl").read_text().splitlines()
        assert len(recs) == 1 and json.loads(recs[0])["ok"]
        with pytest.raises(Exception):
            LAY.run_lay_groups([bouncer_group()], client=FakeAsyncAnthropic(F.lay_responder(_answers())),
                               usage=GuardedUsage(budget_usd=0.0001), records_path=tmp_path / "b.jsonl",
                               retry_delays=())

    def test_batches_transport(self, tmp_path):
        from assistant_axis.gapgen.batches import BatchTransport
        from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep
        bc = FakeBatchClient(F.lay_responder({"33-9032.00:Bouncer": F.lay_answer([F.role("bouncer", distinct=True)])}))
        res, usage = _run([bouncer_group()], tmp_path, None, transport_factory=lambda r: BatchTransport(
            r, bc, tmp_path / "lay_batches.json", sleep=no_sleep, poll_seconds=0))
        assert len(bc.batches.created) == 1 and len(bc.batches.created[0]["requests"]) == 3
        assert "temperature" not in bc.batches.created[0]["requests"][0]["params"]
        assert set(usage.per_model) == {"claude-haiku-5-5:batch"}
        assert res.roles["job_title:33-9032.00:bouncer"][0].support == 3

    def test_estimate(self):
        rub = LAY.load_rubric()
        calls = LAY.lay_calls([physicians_group(), bouncer_group()], rubric=rub, readings=3)
        assert len(calls) == 6 and [c.run for c in calls] == [1, 2, 3, 1, 2, 3]
        assert len({c.custom_id for c in calls}) == 6 and all(len(c.custom_id) <= 64 for c in calls)
        live, batch = LAY.estimate(calls), LAY.estimate(calls, batch=True)
        assert 0 < batch.usd < live.usd and abs(batch.usd - live.usd / 2) < 1e-9
        assert "job_title rows" in live.format() and "broad rows" in live.format()


class TestCli:
    @pytest.fixture
    def env(self, tmp_path, monkeypatch):
        import data_analysis.gap_generation.professions_generator as G
        cand = tmp_path / "cand"
        rd = cand / "runs" / "professions" / "r1"
        rd.mkdir(parents=True)
        rows = [{"kind": "broad", "code": "29-1210", "title": "Physicians", "employment": 782430,
                 "detailed": physicians_group().occupations},
                {"kind": "job_title", "code": "33-9032.00", "occupation": "Security Guards", "title": "Bouncer",
                 "label": "bouncer", "stem": "bouncer", "zipf": 3.4, "employment": 1120000,
                 "description": F.OCCUPATIONS["33-9032.00"][1]}]
        (rd / "table.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        client = FakeAsyncAnthropic(F.lay_responder(_answers()))
        monkeypatch.setattr(G, "_anthropic_client", lambda: client)
        monkeypatch.setattr(G, "_dirty", lambda args: None)
        return G, ["--candidates-dir", str(cand)], rd, client

    def test_dry_run_renders_both_variants_and_sends_nothing(self, env, capsys):
        G, base, rd, client = env
        assert G.main(base + ["lay", "--run-id", "r1", "--budget-usd", "1", "--dry-run"]) == 0
        out = capsys.readouterr().out
        assert "a broad row (broad:29-1210)" in out and "a job_title row (job_title:33-9032.00:bouncer)" in out
        assert BOUNCER_USER in out and "total estimate" in out and "2 rows" in out
        assert client.calls == [] and not (rd / "lay_responses.jsonl").exists()

    def test_live_run_writes_lay_jsonl_and_usage_and_refuses_a_rerun_without_resume(self, env, capsys):
        G, base, rd, client = env
        assert G.main(base + ["lay", "--run-id", "r1", "--budget-usd", "1", "--concurrency", "1"]) == 0
        rows = [json.loads(x) for x in (rd / "lay.jsonl").read_text().splitlines()]
        assert [r["group"] for r in rows] == ["broad:29-1210", "job_title:33-9032.00:bouncer"]
        assert json.loads((rd / "usage.json").read_text())["n_calls"] == 7
        run = json.loads((rd / "run.json").read_text())
        assert run["sessions"][0]["args"]["rubric"] == "profession_lay"
        out = capsys.readouterr()
        assert "parse rate" in out.err or "agreement" in out.out
        assert G.main(base + ["lay", "--run-id", "r1", "--budget-usd", "1"]) == 2
        assert "--resume" in capsys.readouterr().err
        n = len(client.calls)
        assert G.main(base + ["lay", "--run-id", "r1", "--budget-usd", "1", "--resume"]) == 0
        assert len(client.calls) == n

    def test_over_the_budget_refused_before_any_call(self, env, capsys):
        G, base, rd, client = env
        assert G.main(base + ["lay", "--run-id", "r1", "--budget-usd", "0.000001"]) == 2
        assert client.calls == [] and "exceeds --budget-usd" in capsys.readouterr().err
