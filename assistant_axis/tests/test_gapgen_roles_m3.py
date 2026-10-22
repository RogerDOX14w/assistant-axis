"""``novelty_score.py score --holding roles`` end to end on fakes (coding plan 16, task 7 and test 7): the roles pass's
stage (role gloss, three kind readings) for the role rows that need it, then M3 against the role corpus with the
role rubrics and a flat cut-off of 3, the nearest traits shown (``cross_type``), the pass recorded in every block,
``run.json`` and ``summary.json``.  No API calls: the novelty CLI tests' fake client and hash embedder, the ten-role
fixture corpus (``roles_fakes``)."""
import hashlib
import json
import re
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.roles_fakes import (
    aimed_row, held_row, role_m3_responder, stage_responder, write_role_corpus,
)
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.tests.test_gap_generation_novelty_cli import make_env, out

REPO = Path(__file__).resolve().parents[2]
DOCTORISH = "examines patients works out what is wrong with them and treats the heart"

#: (key, row) of the twelve role rows (two trait-flow rows of the toy env are there too, and left alone).
ROLE_ROWS = {
    "doctor#1": held_row("doctor", "works as a physician"),                      # a corpus role stem: stage 0
    "pilot#1": held_row("pilot", "flies aircraft"),                               # a corpus role stem: stage 0
    "cardiologist#1": held_row("cardiologist", DOCTORISH),                        # covered by its parent at 3
    "medic#1": held_row("medic", "examines patients works out what is wrong and treats them in the field"),
    "patient#1": held_row("patient", "is treated by a doctor in a hospital bed"),    # opposed to doctor: completion
    "captive#1": held_row("captive", "is held prisoner against their will", tags=("state",)),   # state-tagged
    "baker#1": held_row("baker", "bakes bread before dawn"),
    "selkie#1": held_row("selkie", "a seal that sheds its skin to walk on land"),
    "lifeguard#1": held_row("lifeguard", "watches swimmers from a tower"),
    "bouncer|R#1": aimed_row("bouncer", "works the door of a club", route="role"),
    "optimist|R#1": aimed_row("optimist", "expects the best", route="both", kind_guess="temperament"),  # stage 0
    "hermit|R#1": aimed_row("hermit", "lives alone in the hills", route="both", kind_guess="stance"),
}
TURNED = aimed_row("captor", "holds someone prisoner", route="turned_away")      # not a role row: left out


@pytest.fixture
def env(tmp_path, monkeypatch):
    e = make_env(tmp_path, monkeypatch)
    write_role_corpus(e["data"])
    e["reg"].write(list(ROLE_ROWS.values()) + [TURNED])
    e["seen"] = {}
    m3 = role_m3_responder(
        relations={("cardiologist", "doctor"): "similar", ("medic", "doctor"): "similar",
                   ("patient", "doctor"): "opposed"},
        overlap={("cardiologist", "doctor", "sonnet"): 3, ("cardiologist", "doctor", "opus"): 3,
                 ("medic", "doctor", "sonnet"): 2, ("medic", "doctor", "opus"): 2})
    e["holder"]["responder"] = stage_responder(kinds={"selkie": ["non_human"], "hermit": ["stance"],
                                                      "captive": ["circumstance", "circumstance", "status"]},
                                               seen=e["seen"], fallback=m3)
    return e


def roles(env, *extra, batch="roles_t"):
    return cli.main(["score", "--batch-id", batch, "--holding", "roles", *env["base"], *extra])


def stage_calls(env):
    return sorted({lab for (step, lab) in env["seen"] if step == "role_gloss"})


def test_dry_run_plans_the_stage_and_writes_nothing(env, capsys):
    before = env["reg"].path.read_text()
    assert roles(env, "--unscored", "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"holding": "roles"' in o and '"n_candidates": 12' in o and '"n_exact_label": 3' in o
    assert '"n_to_stage": 9' in o and '"n_gloss": 9' in o and '"query_form": "role_gloss_w14"' in o
    assert "[role_pass]" in o and "roles pass stage: the role gloss call: 9 x" in o
    assert "role kind call (3 readings): 27 x" in o
    assert "=== roles pass stage, " in o and '"not_a_role_row"' in o
    assert not out(env, "roles_t").exists() and env["reg"].path.read_text() == before and env["seen"] == {}


def test_end_to_end(env):
    assert roles(env, "--unscored") == 0
    rows = env["reg"].fold()
    # the stage: every role row but the three covered at stage 0
    assert stage_calls(env) == sorted(["cardiologist", "medic", "patient", "captive", "baker", "selkie", "lifeguard",
                                       "bouncer", "hermit"])
    b = rows["selkie#1"][RP.BLOCK]
    assert b["kind"] == "non_human" and b["human"] is False and b["batch_id"] == "roles_t" and b["gloss_form_ok"]
    assert rows["captive#1"][RP.BLOCK]["kind"] == "circumstance"
    assert RP.BLOCK not in rows["doctor#1"] and RP.BLOCK not in rows["optimist|R#1"]
    nv = {k: rows[k]["novelty"] for k in ROLE_ROWS}
    assert all(v["pass"] == "roles" and v["run_id"] == "roles_t" and v["cut_off"] == 3 for v in nv.values())
    assert all(v["rubrics"] == {"overlap": {"name": "overlap_concept_roles", "version": 1,
                                            "sha256": sr.sha256(sr.load_prompt("overlap_concept_roles"))},
                                "relation": {"name": "relation_roles", "version": 1,
                                             "sha256": sr.sha256(sr.load_prompt("relation_roles"))}}
               for v in nv.values())
    for k in ("doctor#1", "pilot#1", "optimist|R#1"):
        assert nv[k]["decision"] == "covered" and nv[k]["reason"] == "exact_label" and nv[k]["exact_label"]["match"] == "corpus"
    assert nv["optimist|R#1"]["covered_by"] == "optimist"
    assert nv["cardiologist#1"]["decision"] == "covered" and nv["cardiologist#1"]["covered_by"] == "doctor"
    d = nv["cardiologist#1"]["deciding_reading"]
    assert d["sonnet"]["value"] == 3 and d["opus"]["value"] == 3
    assert nv["medic#1"]["decision"] == "new" and [r["stem"] for r in nv["medic#1"]["readings"]] == ["doctor"]
    assert nv["patient#1"]["pair_completion_for"] == ["doctor"]
    assert nv["captive#1"]["decision"] == "new" and nv["bouncer|R#1"]["decision"] == "new"
    # cross_type: the nearest traits of the toy trait corpus on every block (none decides)
    ct = nv["bouncer|R#1"]["cross_type"]["traits"]
    assert len(ct) == NV.CROSS_TYPE_K and all(set(x) == {"stem", "cosine"} for x in ct)
    # the rows outside the pass are untouched
    assert rows["captor|R#1"].get("novelty") is None and RP.BLOCK not in rows["captor|R#1"]
    assert all(r.get("novelty") is None for k, r in rows.items() if r.get("entity_type") == "trait")
    d = out(env, "roles_t")
    run = json.loads((d / "run.json").read_text())
    assert run["pass"] == "roles" and run["status"] == 0 and run["plan"]["role_pass"]["n_to_stage"] == 9
    assert run["role_pass"]["n_glossed"] == 9 and run["role_pass"]["kinds"]["non_human"] == 1
    assert run["role_pass"]["step_versions"] == {"role_gloss": 1, "role_kind": 1}
    assert run["rubrics"]["relation"]["name"] == "relation_roles" and run["settings"]["query_form"] == "role_gloss_w14"
    assert run["role_settings"]["source"].startswith("M2's trait settings") and run["cross_type"]["kind"] == "traits"
    summary = json.loads((d / "summary.json").read_text())["result"]
    assert summary["pass"] == "roles" and summary["role_pass"]["n_glossed"] == 9 and summary["n_decided"] == 12
    md = (d / "decisions.md").read_text()
    assert md.startswith("# M3 decisions: `roles_t` (roles pass)")
    assert "| candidate | kind | decision |" in md and "| selkie | non_human | new |" in md
    assert "[doctor](../../../roles/instructions/doctor.json)" in md
    recs = [json.loads(x) for x in (d / RP.RESPONSES_NAME).read_text().splitlines()]
    assert len(recs) == 9 * 4 and {r["step"] for r in recs} == {"role_gloss", "role_kind"}
    assert len((d / RP.RESULTS_NAME).read_text().splitlines()) == 9
    usage = json.loads((d / "usage.json").read_text())
    assert usage["per_model"]["claude-haiku-5-5"]["n_calls"] >= 36
    rel = [json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines() if '"relation"' in x]
    assert rel and all(r["step"] in ("relation", "relation_unsure", "overlap") for r in rel)


def test_the_relation_call_lists_roles_under_their_rubric(env):
    assert roles(env, "--keys", "bouncer|R#1") == 0
    client = env["holder"]["client"]
    rel = [kw for kw in client.calls if "candidate" in kw["messages"][0]["content"]]
    assert rel
    obj = json.loads(rel[0]["messages"][0]["content"])
    assert list(obj) == ["candidate", "roles"] and obj["candidate"]["label"] == "bouncer"
    assert obj["candidate"]["description"].startswith("A bouncer is someone who")
    sys_ = rel[0]["system"]
    assert (sys_ if isinstance(sys_, str) else sys_[0]["text"]) == sr.load_prompt("relation_roles")


def test_a_resume_across_passes_is_refused(env, capsys):
    assert cli.main(["score", "--batch-id", "m3t", "--run", "toy/r1", *env["base"]]) == 0
    assert roles(env, "--unscored", "--resume", batch="m3t") == 2
    assert "separate batch id per pass" in capsys.readouterr().err


def test_a_second_run_does_not_stage_a_row_again(env):
    assert roles(env, "--keys", "baker#1") == 0
    n = len(env["seen"])
    assert roles(env, "--keys", "baker#1", "--rescore", batch="roles_t2") == 0
    assert len(env["seen"]) == n                                                  # no stage call the second time
    assert env["reg"].fold()["baker#1"]["novelty"]["run_id"] == "roles_t2"


def test_refusals(env, capsys):
    assert roles(env, "--unscored", "--broader-check") == 2
    assert "broader" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        roles(env, "--unscored", "--query-form", "gloss_w14")
    assert roles(env, "--unscored", "--embed-only") == 2
    assert "stage" in capsys.readouterr().err


def test_the_relation_rendering_in_the_rubric_file_is_the_codes():
    """The rendered sample of rubrics/relation_roles.md (``render --pass roles --stand-in detective`` on the real
    corpus) is what the code builds from the corpus files' labels and descriptions, byte for byte."""
    text = (REPO / "reports/trait_gap_generation/rubrics/relation_roles.md").read_text(encoding="utf-8")
    sample = re.search(r"```\n(\{\"candidate\".*?\]\})\n```", text, re.S).group(1)
    obj = json.loads(sample)
    rc = NV.load_role_corpus(REPO / "data")
    by_label = {t.label: t for t in rc.values()}
    listed = [(x["label"], by_label[x["label"]].description) for x in obj["roles"]]
    user = NV.render_relation_user("detective", rc["detective"].description, listed, list_key="roles")
    assert user == sample
    assert hashlib.sha256(user.encode()).hexdigest()[:16] == hashlib.sha256(sample.encode()).hexdigest()[:16]
