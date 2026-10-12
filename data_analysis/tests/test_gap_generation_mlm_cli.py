"""The masked-LM generator's CLI (``masked_lm_generator.py``): every subcommand's dry run writes nothing; the
pipeline census -> generate -> score -> table -> evaluate -> submit -> report runs end to end on fakes (a fake
tokenizer and model, fake lookups, a tmp registry); no model is loaded, nothing is downloaded, no API is called."""
import hashlib
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.censuses_fakes import make_corpus
from assistant_axis.tests.mlm_fakes import FakeMaskedLM, make_tokenizer
from assistant_axis.tests.test_gapgen_mlm_table import fake_lookups
from data_analysis.gap_generation import masked_lm_generator as CLI

VOCAB = ["She", "He", "This", "The", "A", "An", "Ġis", "Ġwas", "Ġby", "Ġnature", ".", "'s", "Ġhabitually", "Ġkind",
         "Ġcruel", "Ġhonest", "Ġhelpful", "Ġharmless", "Ġshy", "Ġsyc", "oph", "antic", "Ġhearted", "ness", "Ġrisk",
         "-", "a", "verse", "Ġto", "Ġanimals", "ly", "Ġgoal", "oriented", "seeking", "minded", "Ġtired", "Ġtall",
         "Ġtoday", "Ġhair", "Ġlooks"]


def scorer(pieces, pos):
    prv = pieces[pos - 1]
    nxt = pieces[pos + 1] if pos + 1 < len(pieces) else None
    if prv == "Ġsyc":
        return {"oph": 6.0, "antic": 2.0}
    if prv == "oph":
        return {"antic": 6.0}
    if prv == "Ġkind":
        return {"Ġhearted": 6.0, "ness": 5.0}
    if prv == "-":
        return {"a": 6.0}
    if prv == "a":
        return {"verse": 6.0}
    if prv == "Ġto":
        return {"Ġanimals": 6.0}
    if nxt == "-":
        return {"Ġrisk": 5.0, "Ġgoal": 4.0}
    ctx = set(pieces)
    if "Ġtoday" in ctx:
        return {"Ġtired": 6.0, "Ġkind": 0.0}
    if "Ġhair" in ctx or "Ġlooks" in ctx:
        return {"Ġtall": 6.0, "Ġkind": 0.0}
    return {"Ġkind": 5.0, "Ġcruel": 4.0, "Ġhelpful": 3.5, "Ġhonest": 3.0, "Ġharmless": 2.0, "Ġsyc": 2.5, "Ġshy": 1.0,
            "Ġtired": -1.0, "Ġtall": -1.0}


@pytest.fixture
def env(tmp_path, monkeypatch):
    tok = make_tokenizer(VOCAB)
    monkeypatch.setattr(CLI, "_tokenizer", lambda key, args: tok)
    monkeypatch.setattr(CLI, "_load_mlm", lambda key, args: FakeMaskedLM(tok, scorer, key=key))
    monkeypatch.setattr(CLI, "_lemmatizer", lambda: (lambda w: w.lower()))
    monkeypatch.setattr(CLI, "_universe", lambda: ["kind", "cruel", "sycophantic", "risk-averse", "honest", "zorbish"])
    monkeypatch.setattr(CLI, "_zipf", lambda: (lambda w: {"kind": 5.0, "cruel": 4.0, "honest": 5.0}.get(w, 2.0)))
    monkeypatch.setattr(CLI, "_lookups", lambda tokenizer: fake_lookups(
        token_class=lambda s: "multiword" if ("-" in s or " " in s) else ("subword" if s == "sycophantic" else "single")))
    monkeypatch.setattr(CLI, "_present", lambda key, args: key == "roberta")
    data = make_corpus(tmp_path, traits=("kind", "honest", "risk_averse", "kind_to_animals", "tall"),
                       queue=("cruel",))
    regions = tmp_path / "regions.json"
    regions.write_text(json.dumps({"tall": {"region": "identity_demographic"}}))
    common = ["--data-dir", str(data), "--registry", str(tmp_path / "cand" / "registry.jsonl"),
              "--candidates-dir", str(tmp_path / "cand"), "--out-dir", str(tmp_path / "out"),
              "--agg-dir", str(tmp_path / "agg"), "--sources-manifest", str(tmp_path / "out" / "sources.json"),
              "--hf-dir", str(tmp_path / "hf"), "--regions", str(regions), "--device", "cpu"]
    return tmp_path, common


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def run(common, *argv):
    return CLI.main(common + list(argv))


GEN = ["generate", "--passes", "single,probe,subword,multiword,variant_b", "--frames", "pilot10", "--subjects",
       "she,he,assistant", "--k-first", "3", "--k-first-multi", "2", "--beam-width", "2"]


def test_every_dry_run_writes_nothing(env, capsys):
    tmp, common = env
    before = snapshot(tmp)
    for argv in (["census", "--queue", "--dry-run"], ["record-model", "--dry-run"], GEN + ["--dry-run"],
                 ["score", "--dry-run"]):
        assert run(common, *argv) == 0, argv
    assert snapshot(tmp) == before
    assert run(common, *GEN) == 0
    mid = snapshot(tmp)
    for argv in (["score", "--top", "0", "--dry-run"], ["table", "--dry-run"]):
        assert run(common, *argv) == 0, argv
    assert snapshot(tmp) == mid
    assert run(common, "score", "--top", "0") == 0 and run(common, "table") == 0
    mid = snapshot(tmp)
    assert run(common, "evaluate", "--dry-run") == 0
    assert snapshot(tmp) == mid
    assert run(common, "evaluate") == 0
    mid = snapshot(tmp)
    assert run(common, "submit", "--run-id", "p1", "--top", "4", "--dry-run") == 0
    assert run(common, "submit", "--run-id", "w1", "--kept-target", "2", "--dry-run") == 0
    assert snapshot(tmp) == mid
    assert run(common, "submit", "--run-id", "p1", "--top", "4") == 0
    mid = snapshot(tmp)
    assert run(common, "report", "--run-id", "p1", "--dry-run") == 0
    assert snapshot(tmp) == mid
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "minutes_at_cpu_rate" in out


def test_models_that_are_not_downloaded_are_refused(env, capsys):
    tmp, common = env
    assert run(common, "--models", "bert_wwm", *GEN[0:3]) == 2
    err = capsys.readouterr().err
    assert "setup_external.py --hf-model google-bert/bert-large-cased-whole-word-masking" in err
    assert "approved: Roger" in err
    assert run(common, "record-model") == 2                          # no --approved-by
    assert "--approved-by" in capsys.readouterr().err
    assert not (tmp / "agg").exists()


def test_census_writes_its_record(env, capsys):
    tmp, common = env
    assert run(common, "census", "--queue") == 0
    d = json.loads((tmp / "out" / "census.json").read_text())
    c = d["result"]["census"]["roberta"]
    assert c["corpus"]["n"] == 5 and c["corpus"]["multiword"] == 2 and c["queue"]["n"] == 1
    assert "_provenance" in d


def test_pipeline_end_to_end_and_report(env, capsys):
    tmp, common = env
    assert run(common, "census") == 0
    assert run(common, *GEN) == 0
    agg = tmp / "agg" / "roberta"
    assert {p.name for p in agg.glob("*.jsonl")} >= {"single.jsonl", "probe.jsonl", "subword.jsonl",
                                                      "multiword.jsonl", "variant_b.jsonl"}
    meta = json.loads((agg / "single.meta.json").read_text())
    assert meta["frame_bank_sha256"] and meta["revision"] == "fake-rev"
    assert meta["n_instances"] == 30            # the pilot10 frames x she, he, assistant
    assert run(common, "score", "--top", "0") == 0
    con = [json.loads(x) for x in (agg / "contrast.jsonl").read_text().splitlines()]
    assert {"kind", "tired", "tall"} <= {c["word"] for c in con}
    assert run(common, "table") == 0
    rows = [json.loads(x) for x in (tmp / "out" / "mlm_table.jsonl").read_text().splitlines()]
    stems = {r["stem"]: r for r in rows}
    assert {"kind", "sycophantic", "risk_averse"} <= set(stems)
    assert stems["kind"]["trait_contrast"] > 0 and stems["sycophantic"]["token_class"] == "subword"
    gen = json.loads((tmp / "out" / "generation.json").read_text())
    assert set(gen["result"]["passes"]) >= {"single:roberta", "variant_b:roberta"}
    assert run(common, "evaluate", "--title", "fixture") == 0
    ev = json.loads((tmp / "out" / "evaluation.json").read_text())["result"]
    assert ev["contrast_auc"] is not None and ev["hhh_probe"]["ranks"]["helpful"] is not None
    assert set(ev["hhh_probe"]["ranks"]) == {"helpful", "harmless", "honest", "sycophantic", "obedient",
                                             "transparent", "manipulative", "truthful", "deferential"}
    for f in ("recovery_curves.png", "hhh_probe.md", "readout.md", "roger_sample.md"):
        assert (tmp / "out" / f).exists(), f
    assert run(common, "submit", "--run-id", "p1", "--top", "4") == 0
    out = capsys.readouterr().out
    assert "traithood_filter.py --batch-id p1_masked_lm --run masked_lm/p1 --pipeline split" in out
    rd = tmp / "cand" / "runs" / "masked_lm" / "p1"
    cands = [json.loads(x) for x in (rd / "candidates.jsonl").read_text().splitlines()]
    assert len(cands) == 4 and cands[0]["rank"] == 1
    assert json.loads((rd / "usage.json").read_text())["total_cost_usd"] == 0.0
    # pretend M1 and M3 ran on two rows
    reg = Registry(tmp / "cand" / "registry.jsonl")
    keys = sorted(reg.fold())
    reg.merge_block(keys[0], "filter", {"verdict": "trait", "outcome": "trait", "polysemy": True}, replace=True)
    reg.merge_block(keys[1], "filter", {"verdict": "reject", "outcome": "turned_away"}, replace=True)
    reg.merge_block(keys[0], "novelty", {"decision": "new"}, replace=True)
    assert run(common, "report", "--run-id", "p1") == 0
    md = (rd / "report.md").read_text()
    assert "measured pass rate 50.0%" in md and "kept share" in md and "polysemy 50.0%" in md
    rep = json.loads((rd / "evaluation.json").read_text())["result"]
    assert rep["measured_kept_share"] == 0.25 and rep["m3"]["decision"] == {"new": 1}
    assert (rd / "roger_sample.md").exists()
    # the wave: registry stems are left out by default
    assert run(common, "submit", "--run-id", "w1", "--kept-target", "2", "--kept-share", "0.5", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "already in the registry (left out)" in out and "kept target 2 at kept share 0.5" in out
