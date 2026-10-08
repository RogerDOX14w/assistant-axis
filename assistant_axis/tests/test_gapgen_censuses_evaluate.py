"""Census generator, evaluation: string ceiling, known-label pass, state glosses, costs, readout."""
import json
import os
import re
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.censuses import evaluate as E
from assistant_axis.gapgen.generators.censuses import report as R
from assistant_axis.gapgen.generators.censuses import submit as S
from assistant_axis.gapgen.generators.censuses.corpus import corpus_trait_stems, queue_trait_stems
from assistant_axis.gapgen.generators.censuses.ingest import ingest_counts
from assistant_axis.gapgen.paths import REPO_ROOT
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.censuses_fakes import fixture_table


def test_string_ceiling(tmp_path):
    rows, _, data = fixture_table(tmp_path)
    c = E.string_ceiling(rows, corpus_trait_stems(data), queue_trait_stems(data_dir=data))
    # corpus: risk_averse, kind_to_animals, kind, gloomy; queue: flustered (dropped entry ignored)
    assert (c.n_corpus, c.n_multiword) == (4, 2)
    assert (c.n_tda, c.n_allport, c.n_union) == (2, 3, 3)
    assert c.tda == 0.5 and c.allport == 0.75 and c.union == 0.75 and c.union_single_word == 1.0
    assert c.submitted_of_matched == 1.0 and c.matched_ineligible == []
    assert (c.n_queue, c.n_queue_union) == (1, 1)


def test_ceiling_counts_ineligible_match(tmp_path):
    rows, _, data = fixture_table(tmp_path)
    c = E.string_ceiling(rows, {"quaintish", "kind"})
    assert c.n_union == 2 and c.n_matched_eligible == 1 and c.matched_ineligible == ["quaintish"]


def row(stem, verdict=None, tags=(), outcome=None, gloss=None):
    r = {"stem": stem, "key": f"{stem}#1", "gloss": gloss,
         "sources": [{"generator": "censuses", "run_id": "r1"}]}
    if verdict:
        r["filter"] = {"verdict": verdict, "tags": list(tags), "outcome": outcome or verdict}
    return r


def test_known_label_pass():
    rows = [row("kind", "trait"), row("agitated", "tagged", ["state"], "states"),
            row("tall", "tagged", ["physical"], "physical"), row("judge", "tagged", ["role_person"], "roles"),
            row("benzoic", "reject", ["no_persona_reading"], "turned_away"), row("gloomy"), row("newword", "trait")]
    kp = E.known_label_pass(rows, {"kind", "agitated", "tall", "judge", "benzoic", "gloomy"})
    assert (kp.n_known, kp.n_filtered, kp.n_pass) == (6, 5, 3) and kp.pass_rate == 0.6
    assert [m["stem"] for m in kp.misses] == ["benzoic", "judge"] and kp.unfiltered == ["gloomy"]
    assert kp.by_outcome == {"physical": 1, "roles": 1, "states": 1, "trait": 1, "turned_away": 1}


def test_state_gloss_compliance():
    rows = [row("a", "tagged", ["state"], gloss="This means a general tendency to fret over small things."),
            row("b", "tagged", ["state"], gloss="This means a disposition to feel rattled by company."),
            row("c", "tagged", ["state"], gloss="This means being angry right now at this moment."),
            row("d", "trait", gloss="This means being kind.")]
    assert E.state_gloss_compliance(rows) == pytest.approx(0.6667, abs=1e-4)
    assert E.state_gloss_compliance([row("d", "trait")]) is None


def test_cost_summary(tmp_path):
    def usage(p, per):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"per_model": {m: {"cost_usd": c} for m, c in per.items()}}))
        return p
    paths = [usage(tmp_path / "run/usage.json", {}),
             usage(tmp_path / "f/usage.json", {"claude-haiku-5-5": 1.25, "claude-sonnet-4-6": 0.5}),
             usage(tmp_path / "n/usage.json", {"claude-sonnet-4-6": 0.25}), tmp_path / "missing.json"]
    c = E.cost_summary(paths)
    assert c["per_model"] == {"claude-haiku-5-5": 1.25, "claude-sonnet-4-6": 0.75} and c["total_usd"] == 2.0
    assert len(c["files"]) == 3
    assert E.cost_summary(paths[:1])["total_usd"] == 0.0


@pytest.fixture
def run_env(tmp_path):
    rows, extra, data = fixture_table(tmp_path)
    cdir = tmp_path / "candidates"
    reg = cdir / "registry.jsonl"
    S.run_submit("tda", "r1", table=rows, sources_manifest=[{"key": "x"}], registry_path=reg, candidates_dir=cdir,
                 echo=lambda *a: None)
    counts = ingest_counts(rows, extra)
    counts["ceiling"] = E.string_ceiling(rows, corpus_trait_stems(data)).as_dict()
    return rows, counts, data, cdir, reg


def test_evaluate_run_before_filter(run_env):
    rows, counts, data, cdir, reg = run_env
    rdir = cdir / "runs" / "censuses" / "r1"
    ev = R.evaluate_run("r1", run_dir=rdir, table=rows, ingest_counts=counts, registry_rows=Registry(reg).fold(),
                        corpus_stems=corpus_trait_stems(data), candidates_dir=cdir)
    assert ev["submitted"]["n_candidates"] == 5 and ev["submitted"]["registry"]["n_new"] == 5
    assert ev["parsed"]["tda_words"] == 5 and ev["parsed"]["malformed"] == 1
    assert ev["floor"]["tda_cut"] == 0 and ev["floor"]["tda_below_dictionary_floor"] == 1
    assert ev["floor"]["submitted_to_probe"] == 1 and ev["floor"]["submitted_probe_routes"] == {"curated_source": 1}
    assert ev["known_labels"] == {"n": 2, "stems": ["gloomy", "kind"]}
    assert ev["filter"] is None and ev["cost"]["total_usd"] == 0.0
    json.dumps(ev)


def test_evaluate_run_after_filter_and_readout(run_env, tmp_path):
    rows, counts, data, cdir, reg = run_env
    r = Registry(reg)
    r.merge_block("kind#1", "filter", {"verdict": "trait", "tags": [], "outcome": "trait"})
    r.merge_block("gloomy#1", "filter", {"verdict": "tagged", "tags": ["role_person"], "outcome": "roles"})
    r.merge_block("sunny#1", "novelty", {"decision": "new", "pair_completion_for": "gloomy"})
    rdir = cdir / "runs" / "censuses" / "r1"
    ev = R.evaluate_run("r1", run_dir=rdir, table=rows, ingest_counts=counts, registry_rows=r.fold(),
                        corpus_stems=corpus_trait_stems(data), candidates_dir=cdir)
    kp = ev["filter"]["known_label_pass"]
    assert kp["n_pass"] == 1 and kp["n_filtered"] == 2 and kp["misses"][0]["stem"] == "gloomy"
    assert ev["novelty"] == {"n_scored": 1, "decision": {"new": 1}, "pair_completion": 1}
    doc = rdir / "readout.md"
    md = R.render_readout(ev, doc_path=doc, run_dir=rdir, table_path=tmp_path / "census_table.jsonl",
                          counts_path=tmp_path / "ingest_counts.json", manifest_path=tmp_path / "sources_manifest.json")
    assert "## Counts" in md and "## String ceiling" in md and "## Filter (M1)" in md and "## Novelty (M3)" in md
    assert "**submitted in this run** | **5**" in md
    # every link is relative and resolves from the document's directory
    links = re.findall(r"\]\(([^)]+)\)", md)
    assert links and all(not x.startswith("/") for x in links)
    trait_links = [x for x in links if x.endswith("traits/instructions/kind.json")]
    assert trait_links
    assert Path(os.path.normpath(doc.parent / trait_links[0])) == REPO_ROOT / "data/traits/instructions/kind.json"
    assert "[candidates.jsonl](candidates.jsonl)" in md
