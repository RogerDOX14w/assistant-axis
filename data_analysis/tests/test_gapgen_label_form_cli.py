"""W19 at the CLIs (Roger, 2026-10-09): ``novelty_score.py`` on a toy corpus whose ``alpha`` is standards-derived
(``alpha (HEXACO)``).  A new run shows and records the judge display form; the stored label, the registry and the
embedded texts are unchanged; a resumed run, a re-decided run and a relation-only run keep the label form their run or
source recorded (``stored`` for a run from before the change, which recorded none), so nothing on record is asked
again.  No API calls: the novelty CLI tests' fakes."""
import json

import pytest

from assistant_axis.gapgen import embed as EM
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import prompt_labels as PL
from assistant_axis.gapgen.representation import represent
from assistant_axis.tests.fake_anthropic import user_text
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.tests.test_gap_generation_novelty_cli import (OVERLAP, RELATIONS, calls_made, make_env, out,
                                                                 redecide, relation_only, score)

STORED_LABEL = "alpha (HEXACO)"
SHOWN_LABEL = "alpha (from HEXACO)"
# the toy responder answers by the label it is shown, so it knows alpha in either form
REL = RELATIONS | {("alphoid", STORED_LABEL): "similar", ("alphoid", SHOWN_LABEL): "similar"}
OV = OVERLAP | {("alphoid", STORED_LABEL): 4, ("alphoid", SHOWN_LABEL): 4}


@pytest.fixture
def env(tmp_path, monkeypatch):
    e = make_env(tmp_path, monkeypatch, relations=REL, overlap=OV)
    p = e["data"] / "traits" / "instructions" / "alpha.json"
    doc = json.loads(p.read_text())
    doc["positive_label"] = STORED_LABEL
    p.write_text(json.dumps(doc), encoding="utf-8")
    e["alpha_file"] = p.read_text()
    return e


def shown_labels(calls) -> set:
    out_ = set()
    for k in calls:
        obj = json.loads(user_text(k))
        for part in ("candidate", "target", "other"):
            if part in obj:
                out_.add(obj[part]["label"])
        out_ |= {t["label"] for t in obj.get("traits", [])}
    return out_


def old_run(env, monkeypatch, *extra):
    """A run as the code before 2026-10-09 made it: its prompts in the stored form and no ``label_form`` in its
    ``run.json``."""
    with monkeypatch.context() as m:
        m.setattr(PL, "DEFAULT_LABEL_FORM", PL.STORED_LABEL_FORM)
        rc = score(env, *extra)
    p = out(env) / "run.json"
    run = json.loads(p.read_text())
    run.pop(PL.LABEL_FORM_KEY, None)
    run["plan"].pop(PL.LABEL_FORM_KEY, None)
    p.write_text(json.dumps(run))
    return rc


def test_a_new_run_shows_and_records_the_judge_form(env):
    assert score(env) == 0
    labels = shown_labels(env["holder"]["client"].calls)
    assert SHOWN_LABEL in labels and STORED_LABEL not in labels
    assert not any("_" in lb for lb in labels)                                   # labels, never stems
    run = json.loads((out(env) / "run.json").read_text())
    assert run[PL.LABEL_FORM_KEY] == PL.JUDGE_LABEL_FORM == run["plan"][PL.LABEL_FORM_KEY]
    summary = json.loads((out(env) / "summary.json").read_text())["result"]
    assert summary[PL.LABEL_FORM_KEY] == PL.JUDGE_LABEL_FORM
    rows = env["reg"].fold()
    assert rows["alphoid#1"]["novelty"]["covered_by"] == "alpha"                 # decided on the shown form
    # nothing stored changed: the trait file, the registry's labels, the corpus label and the embedded text
    assert (env["data"] / "traits" / "instructions" / "alpha.json").read_text() == env["alpha_file"]
    assert {r["label"] for r in rows.values()} >= {"alpha", "alphoid"}
    traits = NV.load_trait_corpus(env["data"])
    assert traits["alpha"].label == STORED_LABEL
    cache = EM.EmbeddingCache(env["tmp"] / "cache")
    stored_text = represent(STORED_LABEL, traits["alpha"].description, "w20")
    shown_text = represent(SHOWN_LABEL, traits["alpha"].description, "w20")
    found, _ = cache.lookup("openai_text-embedding-3-large", [stored_text, shown_text])
    assert 0 in found and 1 not in found


def test_render_shows_the_judge_form(env, capsys):
    assert score(env) == 0                                                       # embeds the candidates (cached)
    capsys.readouterr()
    assert cli.main(["render", "--key", "alphoid#1", "--registry", str(env["reg"].path), "--data-dir", str(env["data"]),
                     "--metric-config", str(env["tmp"] / "metric_config.json"), "--cache-dir", str(env["tmp"] / "cache")]) == 0
    o = capsys.readouterr().out
    assert f'"label": "{SHOWN_LABEL}"' in o and f'"label": "{STORED_LABEL}"' not in o


def test_resuming_an_old_run_keeps_the_stored_form(env, monkeypatch):
    good = env["holder"]["responder"]

    def flaky(kw):                       # alphoid's overlap call fails: the candidate stalls after its relation call
        if json.loads(user_text(kw)).get("target", {}).get("label") == "alphoid":
            return RuntimeError("network down")
        return good(kw)
    env["holder"]["responder"] = flaky
    assert old_run(env, monkeypatch) == 0
    assert env["reg"].fold()["alphoid#1"].get("novelty") is None
    env["holder"]["responder"] = good
    env["holder"].pop("client", None)
    assert score(env, "--resume") == 0
    sent = calls_made(env)
    assert sent and all("target" in json.loads(user_text(k)) for k in sent)     # the relation answer was replayed
    assert shown_labels(sent) == {"alphoid", STORED_LABEL}                       # the old run's form, not the new
    assert env["reg"].fold()["alphoid#1"]["novelty"]["covered_by"] == "alpha"
    run = json.loads((out(env) / "run.json").read_text())
    assert run[PL.LABEL_FORM_KEY] == PL.STORED_LABEL_FORM and run["resumed"]


def test_a_resumed_new_run_keeps_the_judge_form(env):
    good = env["holder"]["responder"]

    def flaky(kw):
        if json.loads(user_text(kw)).get("target", {}).get("label") == "alphoid":
            return RuntimeError("network down")
        return good(kw)
    env["holder"]["responder"] = flaky
    assert score(env) == 0
    env["holder"]["responder"] = good
    env["holder"].pop("client", None)
    assert score(env, "--resume") == 0
    sent = calls_made(env)
    assert sent and all("target" in json.loads(user_text(k)) for k in sent)
    assert shown_labels(sent) == {"alphoid", SHOWN_LABEL}


def test_redecide_and_relation_only_follow_their_source(env, monkeypatch):
    assert old_run(env, monkeypatch, "--rules", "1") == 0
    env["holder"].pop("client", None)
    assert redecide(env, "m3t_same", "--rules", "1") == 0
    assert calls_made(env) == []                                                 # every stored-form answer found
    assert json.loads((out(env, "m3t_same") / "run.json").read_text())[PL.LABEL_FORM_KEY] == PL.STORED_LABEL_FORM
    env["holder"].pop("client", None)
    assert relation_only(env, "rel45", "--relation-model", NV.HAIKU) == 0        # refused if any request differed
    sent = calls_made(env)
    assert sent and STORED_LABEL in shown_labels(sent) and SHOWN_LABEL not in shown_labels(sent)
    s = json.loads((out(env, "rel45") / "relation_summary.json").read_text())["result"]
    assert s["like_for_like"]["identical"] == s["like_for_like"]["n"] == 3
    assert s[PL.LABEL_FORM_KEY] == PL.STORED_LABEL_FORM


def test_redecide_of_a_new_run_keeps_the_judge_form(env):
    assert score(env, "--rules", "1") == 0
    env["holder"].pop("client", None)
    assert redecide(env, "m3t_same", "--rules", "1") == 0
    assert calls_made(env) == []
    assert json.loads((out(env, "m3t_same") / "run.json").read_text())[PL.LABEL_FORM_KEY] == PL.JUDGE_LABEL_FORM
