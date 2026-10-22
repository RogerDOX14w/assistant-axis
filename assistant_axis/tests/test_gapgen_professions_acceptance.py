"""Generator B end to end on fakes (coding plan 16, § 8 test 16): fetch (a fake HTTP: O*NET answers, bls.gov refuses)
-> build (fixture O*NET and OEWS files) -> lay (a fake client) -> rank (the hash embedder) -> label-fit (a fake
client) -> submit into a scratch registry -> M1's routing written back -> ``novelty_score.py score --holding roles
--run professions/w1`` (the roles pass's stage and M3, a fake client) -> R1 -> the R2 card.  One occupation is covered
by its parent (cardiologist by doctor at 3), one is new (bouncer); the occupation readout is about right before the
wave and too high after it at the held share, both in ``submit_report.json`` and on the review card once two
occupations are accepted; ``usage.json`` is written at every paid stage; the cost guard refuses an estimate over the
cap before any call.  M1 itself is not rerun here (its routing of role-aimed rows is test 3,
``test_gapgen_filter_role_routes.py``): its write-back is stood in by the block it writes for route ``role``.
No network, no key."""
import json

import pytest

from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen.review_app import decisions as D
from assistant_axis.tests import professions_fakes as F
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, user_text
from assistant_axis.tests.roles_fakes import role_m3_responder, stage_responder, write_role_corpus
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.gap_generation import review_graph as r1
from data_analysis.tests.test_gap_generation_novelty_cli import make_env

RUN = "w1"
M3_BATCH = "roles_professions_w1"
REVIEW_BATCH = "review_roles_professions_w1"

#: The lay call's answer per table row (the fixture O*NET file's five broad groups and the two job titles the cut
#: keeps): doctor and pilot are corpus roles (left out of the ranking); six lay roles are net new.
LAY = {
    "11-1010": [F.role("chief executive", (1, 2))],
    "29-1210": [F.role("doctor", (1, 2, 3)), F.role("cardiologist", (2,), True)],
    "33-9030": [F.role("security guard", (1,))],
    "35-3010": [F.role("bartender", (1,))],
    "53-2010": [F.role("pilot", (1,))],
    "33-9032.00:Bouncer": [F.role("bouncer", (1,), True)],
    "35-3011.00:Mixologist": [F.role("mixologist", (1,), True)],
}
NET_NEW = {"chief_executive", "cardiologist", "security_guard", "bartender", "bouncer", "mixologist"}

#: M1's accepted reading of each submitted row (the role gloss call writes its gloss from it).
READINGS = {
    "cardiologist": "examines patients works out what is wrong with them and treats the heart",
    "bouncer": "works the door of a club and keeps trouble out",
    "security_guard": "patrols a building at night and watches the cameras",
    "bartender": "pours drinks behind a bar and listens to the regulars",
    "chief_executive": "runs a company and answers to its board",
    "mixologist": "invents cocktails and mixes them with care",
}


def lay_client():
    return FakeAsyncAnthropic(F.lay_responder({k: F.lay_answer(v) for k, v in LAY.items()}))


def label_fit_client():
    def answer(kw):
        json.loads(user_text(kw))["label"]
        return json.dumps({"reason": "It fits.", "verdict": "fits", "better_label": None})
    return FakeAsyncAnthropic(answer)


@pytest.fixture
def world(tmp_path, monkeypatch):
    import data_analysis.gap_generation.label_fit as LFC
    import data_analysis.gap_generation.professions_generator as G
    from assistant_axis.gapgen.generators.professions import onet as Omod
    from assistant_axis.gapgen.generators.professions import rank as RKmod
    e = make_env(tmp_path, monkeypatch)
    data = e["data"]
    write_role_corpus(data)                              # ten roles: four occupations (doctor, nurse, pilot, judge)
    # one live role entry of the queue (an occupation): the corpus is five occupations of eleven, about right
    (data / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "queued", "label": "queued", "status": "candidate", "entity_type": "trait"},
        {"stem": "lifeguard", "label": "lifeguard", "entity_type": "role", "status": "candidate",
         "tags": ["kind:occupation"], "description_draft": "A lifeguard is someone who watches swimmers."}]}))
    ext = tmp_path / "ext"
    F.write_onet(ext)
    http = F.onet_http(titles_body=(
        "O*NET-SOC Code,Alternate Title,Short Title,Source(s)\n"
        "33-9032.00,Bouncer,,08\n33-9032.00,Security Guard,,08\n35-3011.00,Mixologist,,08\n").encode())
    e["holder"]["responder"] = stage_responder(fallback=role_m3_responder(
        relations={("cardiologist", "doctor"): "similar"},
        overlap={("cardiologist", "doctor"): 3}))
    e.update(G=G, ext=ext, http=http, lay=lay_client(), label_fit=label_fit_client(), oews=F.write_oews_csv(
        tmp_path / "oews.csv"))
    monkeypatch.setattr(G, "_http", lambda ua: http)
    monkeypatch.setattr(G, "_anthropic_client", lambda: e["lay"])
    monkeypatch.setattr(G, "_dirty", lambda args: None)
    monkeypatch.setattr(LFC, "_client", lambda: e["label_fit"])
    monkeypatch.setattr(Omod, "default_zipf", lambda: F.fake_zipf)
    monkeypatch.setattr(RKmod, "default_zipf", lambda: F.fake_zipf)
    monkeypatch.setattr(r1, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(r1, "platform_dirty_files", lambda *a, **k: [])
    e["b"] = ["--candidates-dir", str(e["cand_dir"]), "--data-dir", str(data), "--registry", str(e["reg"].path),
              "--external-dir", str(ext)]
    e["rd"] = e["cand_dir"] / "runs" / "professions" / RUN
    return e


def b(world, *args):
    return world["G"].main([*world["b"], *args])


def usage(path):
    return json.loads(path.read_text())


def m1_write_back(world):
    """M1's block for a role-aimed row it routes ``role`` (as ``split.verdict_tags_holding`` leaves it: verdict and
    tags kept, no holding list, ``entity_type: "role"``; the reading accepted is the row's sense)."""
    keys = (world["rd"] / "keys.txt").read_text().split()
    upd = {}
    for k in keys:
        stem = k.split("|")[0]
        upd[k] = {"filter": {"pipeline": "split", "verdict": "tagged", "outcome": "roles", "tags": ["role_person"],
                             "judged_sense": READINGS[stem], "accepted_reading": 1, "role_route": "role",
                             "routes_version": RP.ROUTES_VERSION,
                             "sense": {"readings": [{"reading": READINGS[stem], "rank": "primary"}]}},
                  "gloss": None, "holding": None, "entity_type": "role"}
    world["reg"].update_many(upd)
    return keys


def test_professions_end_to_end(world, capsys):
    rd = world["rd"]
    # fetch: O*NET's job titles downloaded with a manifest row; bls.gov refuses, so the OEWS file waits for a hand
    assert b(world, "fetch") == 2                                                  # no --approved-by: refused
    assert world["http"].calls == []
    assert b(world, "fetch", "--approved-by", "Roger, 2026-10-23") == 3
    assert "download by hand" in capsys.readouterr().out
    man = json.loads((world["ext"] / "onet" / "DOWNLOAD_MANIFEST.json").read_text())
    assert any(r["key"] == "onet_job_titles" and r["approved_by"] == "Roger, 2026-10-23" for r in man)

    # build: five broad groups and the two job titles the cut keeps (Security Guard is its occupation's title)
    assert b(world, "build", "--run-id", RUN, "--oews", str(world["oews"])) == 0
    table = [json.loads(x) for x in (rd / "table.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in table].count("broad") == 5
    assert [r["title"] for r in table if r["kind"] == "job_title"] == ["Bouncer", "Mixologist"]
    assert usage(rd / "usage.json")["n_calls"] == 0

    # lay: the cost guard first (an estimate over the cap: refused before any call), then three readings a row
    assert b(world, "lay", "--run-id", RUN, "--budget-usd", "0.000001") == 2
    assert world["lay"].calls == [] and "exceeds --budget-usd" in capsys.readouterr().err
    assert b(world, "lay", "--run-id", RUN, "--budget-usd", "1", "--concurrency", "1") == 0
    assert len(world["lay"].calls) == 7 * 3 and usage(rd / "usage.json")["n_calls"] == 21

    # rank: the corpus roles (doctor, pilot) left out; six net new
    assert b(world, "rank", "--run-id", RUN, "--embedder", "hash") == 0
    ranking = [json.loads(x) for x in (rd / "ranking.jsonl").read_text().splitlines()]
    assert {r["stem"] for r in ranking if r["net_new"]} == NET_NEW
    assert {r["stem"]: r["excluded"] for r in ranking if not r["net_new"]} == {"doctor": "corpus_role",
                                                                                "pilot": "corpus_role"}
    assert usage(rd / "usage.json")["n_calls"] > 21

    # label-fit: every label fits (three readings each)
    n0 = usage(rd / "usage.json")["n_calls"]
    assert b(world, "label-fit", "--run-id", RUN, "--kept-share", "0.5", "--budget-usd", "1", "--no-oewn",
             "--allow-dirty") == 0
    assert len(world["label_fit"].calls) == 6 * 3 and (rd / "label_fit" / "decisions.json").exists()
    assert usage(rd / "usage.json")["n_calls"] >= n0
    capsys.readouterr()

    # submit: the wave (0.5 x 300 / 0.5 = 300 rows asked for; six there) as role candidates
    assert b(world, "submit", "--run-id", RUN, "--kept-share", "0.5") == 0
    o = capsys.readouterr().out
    assert f"novelty_score.py score --holding roles --run professions/{RUN}" in o
    rows = world["reg"].fold()
    keys = (rd / "keys.txt").read_text().split()
    assert sorted(keys) == sorted(f"{s}|R#1" for s in NET_NEW)
    assert all(rows[k]["entity_type"] == "role" and rows[k]["sources"][0]["kind_guess"] == "occupation"
               and rows[k]["sources"][0]["human"] is True for k in keys)
    occ = json.loads((rd / "submit_report.json").read_text())["balance"]["occupation"]
    assert (occ["before"]["count"], occ["before"]["status"]) == (5, "about_right")
    assert (occ["after_kept"]["count"], occ["after_kept"]["status"]) == (8, "too_high")     # at the held share
    assert usage(rd / "usage.json")["n_calls"] >= n0

    # M1's routing written back; then the roles pass on the run: the stage, then M3 against the role corpus
    m1_write_back(world)
    base = ["score", "--holding", "roles", "--run", f"professions/{RUN}", "--batch-id", M3_BATCH, *world["base"]]
    assert cli.main([*base, "--budget-usd", "0.0001"]) == 2                      # the cost guard: over the cap
    assert "exceeds --budget-usd" in capsys.readouterr().err
    assert world["holder"].get("client") is None or world["holder"]["client"].calls == []
    assert cli.main(base) == 0
    rows = world["reg"].fold()
    nv = {k.split("|")[0]: rows[k]["novelty"] for k in keys}
    assert all(v["pass"] == "roles" and v["cut_off"] == 3 for v in nv.values())
    assert nv["cardiologist"]["decision"] == "covered" and nv["cardiologist"]["covered_by"] == "doctor"
    assert nv["bouncer"]["decision"] == "new"
    assert all(rows[k][RP.BLOCK]["kind"] == "occupation" for k in keys)
    m3 = world["cand_dir"] / "novelty" / M3_BATCH
    assert usage(m3 / "usage.json")["n_calls"] >= 6 * 4
    assert "| bouncer | occupation | new |" in (m3 / "decisions.md").read_text()

    # the generator's readout after M3: five kept, by the kind call
    assert b(world, "report", "--run-id", RUN) == 0
    assert "After M3: 6 of the run's 6 rows decided, 5 kept" in (rd / "report.md").read_text()

    # R1: a roles graph of the kept rows
    assert r1.main(["build", "--batch-id", REVIEW_BATCH, "--from-batches", M3_BATCH, "--budget-usd", "1",
                    *world["base"]]) == 0
    rdir = world["cand_dir"] / "review" / REVIEW_BATCH
    assert usage(rdir / "usage.json")["n_calls"] >= 1
    graph = RG.Graph.from_json(json.loads((rdir / "graph.json").read_text()))
    assert graph.complete and graph.config["pass"] == "roles"
    assert "bouncer|R#1" in graph.candidate_keys() and "cardiologist|R#1" not in graph.candidate_keys()

    # R2: the card (the generator's guess and provenance, the kind call's kind); the readout about right at the
    # corpus as it is, too high once two of the wave's occupations are accepted
    log = D.DecisionLog.open(rdir, by="roger", data_dir=world["data"], registry_path=world["reg"].path)
    card = log.state.member_card("mixologist|R#1")
    assert card["role_kind"] == "occupation" and card["kind_guess"] == "occupation" and card["human"] is True
    assert card["provenance"][0]["generator"] == "professions"
    assert card["kind_readout"]["status"] == "about_right"
    for k in ("bouncer|R#1", "security_guard|R#1"):
        gid = log.act({"action": "open", "source": f"term:{k}"})[1]
        log.act({"action": "resolve", "group": gid, "resolution": "promote"})
    card = log.state.member_card("mixologist|R#1")
    assert card["kind_readout"]["status"] == "too_high" and card["kind_readout"]["text"].startswith(
        "occupation: too high (7 against")
