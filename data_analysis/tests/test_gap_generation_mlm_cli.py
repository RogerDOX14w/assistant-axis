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
    # the wave: registry stems are submitted where they fall inside the cut and never counted (QUESTIONS 82)
    assert run(common, "submit", "--run-id", "w1", "--kept-target", "2", "--kept-share", "0.5", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "already in the registry (submitted where they fall inside the cut, never counted in it)" in out
    assert "kept target 2 at kept share 0.5" in out and "registered stems not counted" in out
    assert run(common, "submit", "--run-id", "w2", "--kept-target", "2", "--kept-share", "0.5", "--count-registered",
               "--dry-run") == 0
    assert "(counted in the cut: --count-registered)" in capsys.readouterr().out
    with pytest.raises(SystemExit):                     # the old flag is gone, not silently ignored
        run(common, "submit", "--run-id", "w3", "--top", "2", "--include-registered", "--dry-run")


def test_each_pass_records_its_pll_mode(env, capsys):
    """QUESTIONS 90: without --pll-mode each pass runs in its own mode, recorded in its aggregate's meta and in
    generation.json; given, it sets every pass.  QUESTIONS 80: evaluation.json records the table's sha256."""
    tmp, common = env
    assert run(common, *GEN) == 0 and run(common, "score", "--top", "0") == 0 and run(common, "table") == 0
    agg = tmp / "agg" / "roberta"
    want = {"single": "l2r", "probe": "l2r", "subword": "l2r", "multiword": "original", "variant_b": "l2r",
            "contrast": "l2r"}
    for p, mode in want.items():
        meta = json.loads((agg / f"{p}.meta.json").read_text())
        assert (meta["pll_mode"], meta["pll_mode_source"]) == (mode, "per-pass default (QUESTIONS 90)"), p
    sub = json.loads((agg / "subword.meta.json").read_text())
    assert sub["settings"]["widths"] == [2, 3, 4]                       # roberta's (QUESTIONS 89)
    gen = json.loads((tmp / "out" / "generation.json").read_text())["result"]["passes"]
    assert {k: v["pll_mode"] for k, v in gen.items()} == {f"{p}:roberta": m for p, m in want.items()
                                                           if p != "contrast"}
    assert run(common, "evaluate") == 0
    ev = json.loads((tmp / "out" / "evaluation.json").read_text())["result"]
    assert ev["table_sha256"] == hashlib.sha256((tmp / "out" / "mlm_table.jsonl").read_bytes()).hexdigest()
    assert ev["throughput"]["multiword:roberta"]["pll_mode"] == "original"
    assert "| multiword:roberta | cpu | original |" in (tmp / "out" / "readout.md").read_text()
    over = [x if x != str(tmp / "agg") else str(tmp / "agg2") for x in common]
    assert run(over, "--pll-mode", "original", *GEN, "--subword-widths", "2,3") == 0
    for p in ("single", "subword", "multiword"):
        meta = json.loads((tmp / "agg2" / "roberta" / f"{p}.meta.json").read_text())
        assert (meta["pll_mode"], meta["pll_mode_source"]) == ("original", "--pll-mode original"), p
    assert json.loads((tmp / "agg2" / "roberta" / "subword.meta.json").read_text())["settings"]["widths"] == [2, 3]


def test_the_dry_run_plans_the_widths_and_modes(env, capsys):
    tmp, common = env
    assert run(common, *GEN, "--dry-run") == 0
    out = capsys.readouterr().out
    sub = json.loads(next(x for x in out.splitlines() if x.strip().startswith("subword:")).split(":", 1)[1])
    # pilot10 x widths 2, 3, 4 at k 3 and beam 2: (1 + 3) + (1 + 3 + 6) + (1 + 3 + 6 + 12) per frame
    assert sub["widths"] == [2, 3, 4] and sub["instances"] == 30 and sub["forward"] == 10 * (4 + 10 + 22)
    assert sub["pll_mode"] == "l2r" and '"pll_mode": "original"' in out
    assert run(common, "--models", "bert_wwm", *GEN, "--dry-run") == 0
    sub = json.loads(next(x for x in capsys.readouterr().out.splitlines()
                          if x.strip().startswith("subword:")).split(":", 1)[1])
    assert sub["widths"] == [2, 3, 4, 5, 6] and sub["instances"] == 50
