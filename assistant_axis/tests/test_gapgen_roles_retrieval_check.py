"""The role index's retrieval check (coding plan 16, task 8 and test 8; decision 11): every corpus role glossed afresh
with no reading, queried in the production form against the full index, recall at 10 of its own stem against 95%;
the arms only below the line, the chosen arm written to the metric config's ``roles`` section and read back by the
pass.  No API calls: the fake client, the hash embedder, the ten-role fixture corpus."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import roles_pass as RP
from assistant_axis.gapgen.metric_config import MetricConfig
from assistant_axis.tests.fake_anthropic import make_response, system_text, user_text
from assistant_axis.tests.roles_fakes import ROLE_CORPUS, write_role_corpus
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.tests.test_gap_generation_novelty_cli import make_env


def gloss_responder(make_gloss):
    from assistant_axis.gapgen import split_rubrics as sr
    gloss_sys = sr.load_prompt("role_gloss")

    def answer(kw):
        assert system_text(kw) == gloss_sys
        obj = json.loads(user_text(kw))
        assert obj["reading"] is None                                     # the check sends no reading
        return make_response(json.dumps({"results": [{"id": 1, "gloss": make_gloss(obj["label"])}]}),
                             input_tokens=650, output_tokens=90)
    return answer


def article(label):
    return "An" if label[:1].lower() in "aeiou" else "A"


@pytest.fixture
def env(tmp_path, monkeypatch):
    e = make_env(tmp_path, monkeypatch)
    write_role_corpus(e["data"])
    cfg = tmp_path / "metric_config.json"
    e["cfg"] = cfg
    e["args"] = ["--data-dir", str(e["data"]), "--out-root", str(e["cand_dir"]), "--metric-config", str(cfg),
                 "--cache-dir", str(tmp_path / "cache")]
    return e


def check(env, batch="rc1", *extra):
    return cli.main(["retrieval-check", "--batch-id", batch, *env["args"], *extra])


def recall(env, batch="rc1"):
    return json.loads((env["cand_dir"] / "novelty" / batch / "recall.json").read_text())["result"]


def test_rank_and_recall_functions():
    rc = {s: NV.CorpusTrait(stem=s, label=s, description="d", negative_label=None, pair_partner=None, partners=[],
                            expands_to=[], renamed_from=[]) for s in ("a", "b", "c")}
    idx = NV.build_index(rc, np.eye(3), variant="raw")
    assert RP.rank_of(idx, np.array([1.0, 0.2, 0.0]), "a") == 1 and RP.rank_of(idx, np.array([1.0, 0.2, 0.0]), "b") == 2
    s = RP.recall_summary({"a": 1, "b": 12, "c": 3}, kinds={"a": "occupation", "b": "occupation", "c": "stance"})
    assert s["recall_at_k"] == pytest.approx(2 / 3, abs=1e-4) and s["n_missed"] == 1
    assert s["by_kind"] == {"occupation": {"n": 2, "recall_at_k": 0.5}, "stance": {"n": 1, "recall_at_k": 1.0}}
    good = {"recall_at_k": 0.96, "mrr": 0.8}
    assert RP.choose_arm({RP.PRODUCTION_ARM: good})["changed"] is False
    low = {RP.PRODUCTION_ARM: {"recall_at_k": 0.9, "mrr": 0.7}, ("role_gloss_w20", "centred"): {"recall_at_k": 0.93,
                                                                                                "mrr": 0.6}}
    ch = RP.choose_arm(low)
    assert ch["changed"] and ch["query_form"] == "role_gloss_w20" and not ch["reached_target"]
    tie = {RP.PRODUCTION_ARM: {"recall_at_k": 0.9, "mrr": 0.7}, ("role_gloss_w14", "raw"): {"recall_at_k": 0.9, "mrr": 0.7}}
    assert RP.choose_arm(tie)["changed"] is False


def test_at_or_above_the_line_the_settings_stay(env, capsys):
    env["holder"]["responder"] = gloss_responder(
        lambda lab: f"{article(lab)} {lab} is someone who does the work every {lab} does, as a {lab} would.")
    before = env["cfg"].read_text()
    assert check(env) == 0
    rep = recall(env)
    assert rep["n_roles"] == len(ROLE_CORPUS) and rep["n_glossed"] == len(ROLE_CORPUS)
    assert rep["production"]["recall_at_k"] == 1.0 and not rep["below_target"]
    assert [(a["query_form"], a["variant"], a["role"]) for a in rep["arms"]] == [
        ("role_gloss_w14", "centred", "production"), ("label_gloss", "centred", "information")]   # no arm run
    assert rep["chosen"]["changed"] is False and env["cfg"].read_text() == before
    d = env["cand_dir"] / "novelty" / "rc1"
    assert len((d / "glosses.jsonl").read_text().splitlines()) == len(ROLE_CORPUS)
    md = (d / "recall.md").read_text()
    assert "at or above 95%" in md and "| `label_gloss` | centred |" in md
    assert json.loads((d / "usage.json").read_text())["per_model"]["claude-haiku-5-5"]["n_calls"] == len(ROLE_CORPUS)
    assert RP.role_settings if False else cli.role_settings(MetricConfig.load(env["cfg"]))["query_form"] == "role_gloss_w14"


def test_below_the_line_the_arms_run_and_the_best_is_written_and_read_back(env):
    # the label comes after the 14th word of the stripped gloss: the 14-word query loses it, the 20-word one keeps it
    def gloss(lab):
        if lab in ("doctor", "nurse", "pilot", "judge"):
            return (f"{article(lab)} {lab} is someone who sits in a quiet room by the window through the long "
                    f"grey afternoons {lab} {lab} {lab} {lab} {lab} {lab}.")
        return f"{article(lab)} {lab} is someone who does the work every {lab} does."
    env["holder"]["responder"] = gloss_responder(gloss)
    # fifteen more roles whose descriptions share the quiet-room words (with ten roles every one is in its own top 10)
    d = env["data"] / "roles" / "instructions"
    for w in ("ash", "birch", "cedar", "elm", "fir", "hazel", "larch", "linden", "maple", "oak", "pine", "rowan",
              "spruce", "willow", "yew"):
        (d / f"{w}.json").write_text(json.dumps({
            "description": f"{article(w)} {w} is someone who sits in a quiet room by the window through the long grey "
                           f"afternoons waiting.", "arrangement": {"kind": "singleton"}}))
    assert check(env) == 0
    rep = recall(env)
    assert rep["below_target"] and rep["production"]["recall_at_k"] < 0.95
    run = {(a["query_form"], a["variant"]) for a in rep["arms"]}
    assert ("role_gloss_w20", "centred") in run and ("role_gloss_w14", "raw") in run
    assert rep["chosen"]["changed"] and rep["chosen"]["query_form"] == "role_gloss_w20"
    four = {"doctor", "nurse", "pilot", "judge"}
    assert four <= {m["stem"] for m in rep["misses"]}
    assert all(m["rank"] > 10 and m["gloss"] and len(m["nearest"]) == 3 for m in rep["misses"])
    w20 = rep["ranks"]["role_gloss_w20|centred"]
    assert all(w20[s] <= 10 for s in four)                    # the 20-word query keeps the label: found
    by = {(a["query_form"], a["variant"]): a for a in rep["arms"]}
    assert by[("role_gloss_w20", "centred")]["recall_at_k"] > rep["production"]["recall_at_k"]
    cfg = MetricConfig.load(env["cfg"])
    assert cfg.roles["query_form"] == "role_gloss_w20" and cfg.roles["batch_id"] == "rc1"
    s = cli.role_settings(cfg)
    assert s["query_form"] == "role_gloss_w20" and s["source"] == "metric_config.roles"


def test_dry_run_and_refusals(env, capsys):
    assert check(env, "rc1", "--dry-run") == 0
    o = capsys.readouterr().out
    assert "retrieval check: 10 corpus roles" in o and '"reading": null' in o and "DRY-RUN" in o
    assert not (env["cand_dir"] / "novelty" / "rc1").exists()
    assert check(env, "rc1", "--forms", "label_gloss") == 2
    assert check(env, "rc1", "--space", "raw") == 2
