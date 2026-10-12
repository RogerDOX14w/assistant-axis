"""Census generator, the fixes of gate audit 1 (reports/code_review_2026-10-12/gate_audits/census_floor.md;
Roger, 2026-10-12): the stage ``allport_iv_rare``, defect F3 (a census rescue defeated by another generator's
earlier free floor reject), the evaluation's real floor counts (F4) and post-split stage pools (F5), and the
OEWN lemma on the table row (P5).  No network, no model, no paid call."""
import argparse
import dataclasses
import json

import pytest

from assistant_axis.gapgen import Candidate, submit_candidates
from assistant_axis.gapgen import freq as F
from assistant_axis.gapgen.filter import FilterRunner, items_from_records
from assistant_axis.gapgen.generators.censuses import CENSUS_TABLE_PATH, load_census_table
from assistant_axis.gapgen.generators.censuses import evaluate as E
from assistant_axis.gapgen.generators.censuses import ingest as I
from assistant_axis.gapgen.generators.censuses import report as R
from assistant_axis.gapgen.generators.censuses import submit as S
from assistant_axis.gapgen.generators.censuses.corpus import corpus_trait_stems, queue_trait_stems
from assistant_axis.gapgen.generators.censuses.glosshint import oewn_lemma
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.censuses_fakes import (
    IN_WORDNET, SURFACE_ZIPF, WORD_ZIPF, fake_lookups, fixture_inputs, make_corpus,
)
from data_analysis.gap_generation import census_generator as CG
from data_analysis.gap_generation import traithood_filter as TF

# ---------------------------------------------------------------------------
# a table with column IV words below the floor
# ---------------------------------------------------------------------------

#: Extra Allport entries: (raw, column, Zipf, known to OEWN)
EXTRA = [("Hirsutish", "IV", 1.0, True),       # column IV alone, known but rare -> allport_iv_rare
         ("Vulpinish", "IV", 1.3, True),       # the same, rarer rank
         ("Gnarlywise", "IV", 0.0, False),     # column IV alone, unknown -> no stage
         ("Rarelike", "I", 1.2, True),         # also in column IV below: not IV alone -> allport_rare
         ("Rarelike", "IV", 1.2, True),
         ("Obscurish", "IV", 0.0, False),      # a TDA word listed in column IV -> tda, never a rare stage
         ("Mistyish", "IV", 2.0, True)]        # column IV alone, eligible (probe band) -> allport_iv


def iv_table(tmp_path, **lookups_over):
    data = make_corpus(tmp_path)
    allport, merged, tda = fixture_inputs()
    allport += [I.RawEntry(raw=raw, line=100 + i, column=col) for i, (raw, col, _, _) in enumerate(EXTRA)]
    words = {**WORD_ZIPF, **{raw.lower(): z for raw, _, z, _ in EXTRA}}
    surfaces = {**SURFACE_ZIPF, **{raw.lower(): z for raw, _, z, _ in EXTRA}}
    known = IN_WORDNET | {raw.lower() for raw, _, _, k in EXTRA if k}
    lk = fake_lookups(zipf=lambda s: surfaces.get(s, 0.0), in_wordnet=lambda s: s in known,
                      zipf_word=lambda w: words.get(w, 0.0), **lookups_over)
    rows, extra = I.build_table(allport, tda, lookups=lk, corpus_stems=corpus_trait_stems(data),
                                queue_stems=queue_trait_stems(data_dir=data), merged=merged)
    return rows, extra, data


def surfaces(rows):
    return [r.surface for r in rows]


class TestIvRareStage:
    def test_selects_exactly_the_column_iv_words_below_the_floor(self, tmp_path):
        rows, _, _ = iv_table(tmp_path)
        want = [r for r in rows if r.stem and not r.tda and r.ineligible_reason == "below_hard_reject"
                and r.columns == ["IV"]]
        got = S.select_stage(rows, "allport_iv_rare")
        assert surfaces(got) == ["vulpinish", "hirsutish"] == surfaces(sorted(want, key=lambda r: r.rank))
        # allport_rare keeps its rule: below the floor and not column IV alone (rarelike is in I and IV)
        assert surfaces(S.select_stage(rows, "allport_rare")) == ["rarelike", "quaintish"]
        assert surfaces(S.select_stage(rows, "allport_iv")) == ["a la mode", "mistyish"]
        # the unknown column IV word and the TDA word in column IV are in neither rare stage
        assert "obscurish" in surfaces(S.select_stage(rows, "tda"))
        rare_stems = {r.stem for st in ("allport_rare", "allport_iv_rare") for r in S.select_stage(rows, st)}
        assert "gnarlywise" not in rare_stems and "obscurish" not in rare_stems

    def test_the_two_rare_stages_partition_below_hard_reject(self, tmp_path):
        rows, _, _ = iv_table(tmp_path)
        rare = {r.stem for r in S.select_stage(rows, "allport_rare")}
        iv_rare = {r.stem for r in S.select_stage(rows, "allport_iv_rare")}
        below = {r.stem for r in rows if r.stem and not r.tda and r.ineligible_reason == "below_hard_reject"}
        assert not rare & iv_rare and rare | iv_rare == below

    def test_stage_pools_cover_every_row_once(self, tmp_path):
        rows, _, _ = iv_table(tmp_path)
        p = S.stage_pools(rows)
        assert p["stages"] == {"tda": 5, "allport_hi": 5, "allport_probe": 2, "allport_iv": 2, "allport_rare": 2,
                               "allport_iv_rare": 2}
        assert p["in_no_stage"] == {"malformed": 1, "unknown_word": 3}       # afald, assistfu, gnarlywise
        assert sum(p["stages"].values()) + sum(p["in_no_stage"].values()) == p["n_rows"] == len(rows)
        assert list(p["stages"]) == list(S.TABLE_STAGES)

    def test_submit_records_the_stage_and_its_rule(self, tmp_path):
        rows, _, _ = iv_table(tmp_path)
        cdir = tmp_path / "candidates"
        summ = S.run_submit("allport_iv_rare", "ivr1", table=rows, sources_manifest=[{"key": "x"}],
                            registry_path=cdir / "registry.jsonl", candidates_dir=cdir, echo=lambda *a: None)
        assert summ.n_stage == 2 and summ.n_selected == 2
        run = json.loads((cdir / "runs" / "censuses" / "ivr1" / "run.json").read_text())
        assert run["args"]["stage"] == "allport_iv_rare"
        assert run["args"]["stage_rule"] == S.STAGE_RULES["allport_iv_rare"]
        cands = [json.loads(x) for x in (cdir / "runs" / "censuses" / "ivr1" / "candidates.jsonl").read_text().splitlines()]
        assert [c["surface"] for c in cands] == ["vulpinish", "hirsutish"]
        # Allport-only rows: no familiarity score; the source ref names column IV
        assert all(c["score"] is None and c["source_ref"].startswith("allport:IV:") for c in cands)

    def test_every_stage_has_a_rule_and_the_cli_accepts_the_stage(self):
        assert set(S.STAGE_RULES) == set(S.STAGES)
        a = CG.build_parser().parse_args(["submit", "--stage", "allport_iv_rare", "--run-id", "x", "--dry-run"])
        assert a.stage == "allport_iv_rare"
        with pytest.raises(ValueError):
            S.select_stage([], "extra")


@pytest.mark.skipif(not CENSUS_TABLE_PATH.exists(), reason="no census table yet")
def test_real_table_iv_rare_is_the_rest_of_below_hard_reject():
    """On the recorded table: allport_rare and allport_iv_rare split the below_hard_reject rows (1,031 + 310
    on the table of 2026-10-11), and every row is in exactly one stage or in none for a recorded reason."""
    table = load_census_table()
    rare = {r.stem for r in S.select_stage(table, "allport_rare")}
    iv_rare = {r.stem for r in S.select_stage(table, "allport_iv_rare")}
    below = {r.stem for r in table if r.stem and not r.tda and r.ineligible_reason == "below_hard_reject"}
    assert iv_rare and not rare & iv_rare and rare | iv_rare == below
    p = S.stage_pools(table)
    assert sum(p["stages"].values()) + sum(p["in_no_stage"].values()) == len(table)
    assert set(p["in_no_stage"]) <= {"unknown_word", "malformed"}


# ---------------------------------------------------------------------------
# F3: a census rescue after another generator's free floor reject
# ---------------------------------------------------------------------------

FAKE_ZIPF = {"irresolute": 1.49, "sybaritic": 1.47, "restrictionist": 1.15, "kindly": 3.5, "newword": 1.2,
             "pettish": 0.0}

#: The split filter's free floor reject, as the registry holds it for irresolute#1 (batch m3_pilot_antonym_check).
SPLIT_FLOOR = {"pipeline": "split", "rule": "floor", "cause": "floor", "outcome": "turned_away", "verdict": "reject",
               "tags": ["too_rare"], "model": None, "batch_id": "m3_pilot_antonym_check",
               "reason": "Zipf 1.49 is below the 1.5 floor and no rescue route applies (no LLM call)."}
FLOOR_FREQ = {"zipf_min": 1.49, "zipf_words": {"irresolute": 1.49}, "hard_reject": True, "probe_band": False,
              "familiarity_override": False, "rescue": None, "define_probe": None}


@pytest.fixture
def fake_zipf(monkeypatch):
    monkeypatch.setattr(F, "_ZIPF_FN", lambda w: FAKE_ZIPF.get(w, 0.0))
    return lambda w: FAKE_ZIPF.get(w, 0.0)


def census(surface, run_id="t1", hint=True, score=None):
    return Candidate(surface=surface, generator="censuses", run_id=run_id, score=score, source_ref=f"tda:{surface}",
                     gloss_hint=f"the sense of {surface}" if hint else None)


def other(surface, gen="antonym_check", run_id="pilot_1"):
    return Candidate(surface=surface, generator=gen, run_id=run_id, score=1, source_ref=f"{gen}:{surface}")


def select(reg, *, run=None):
    args = argparse.Namespace(validation_file=None, sample_frac=None, registry=reg, keys=None, run=run, limit=None)
    items, _ = TF.select_items(args)
    return items


@pytest.fixture
def f3_registry(tmp_path, fake_zipf):
    """irresolute: floor-rejected under antonym_check, then the TDA joins it (curated, gloss hint, raters 0.67);
    sybaritic: floor-rejected under antonym_check, then a non-curated source with no hint joins it;
    restrictionist: the single-call filter's floor reject, then a census source joins it;
    pettish: cut by the definition probe (a paid verdict), census source;
    kindly: filtered as a trait; newword: never filtered."""
    reg = tmp_path / "registry.jsonl"
    submit_candidates([other("irresolute"), other("sybaritic"), other("restrictionist")], registry_path=reg)
    r = Registry(reg)
    r.update_many({"irresolute#1": {"filter": dict(SPLIT_FLOOR), "freq": dict(FLOOR_FREQ)},
                   "sybaritic#1": {"filter": {**SPLIT_FLOOR, "reason": "Zipf 1.47 ..."},
                                   "freq": {**FLOOR_FREQ, "zipf_min": 1.47}}}, merge_blocks=False)
    # the single-call pipeline's hard reject, made by the real FilterRunner.prepare
    runner = FilterRunner(client=None, batch_id="single_b", wordnet=False, zipf_fn=fake_zipf)
    items = items_from_records([r.get("restrictionist#1")])
    assert runner.prepare(items) == [] and runner.results["restrictionist#1"].stage == "hard_reject"
    r.update_many({"restrictionist#1": runner.results["restrictionist#1"].registry_fields()}, merge_blocks=False)
    submit_candidates([census("irresolute", score=0.67), census("restrictionist", run_id="rare1", hint=False),
                       census("pettish", run_id="rare1"), census("kindly"), census("newword"),
                       other("sybaritic", gen="roget", run_id="r1")], registry_path=reg)
    r.update_many({"pettish#1": {"filter": {**SPLIT_FLOOR, "rule": "probe", "cause": "probe",
                                            "model": "claude-haiku-5-5", "batch_id": "b"}},
                   "kindly#1": {"filter": {"rule": 4, "verdict": "trait", "outcome": "trait", "tags": []}}},
                  merge_blocks=False)
    return reg


class TestF3:
    def test_the_merge_keeps_the_old_floor_block(self, f3_registry):
        """The registry writer is unchanged: a joining source leaves the filter block as it was."""
        row = Registry(f3_registry).get("irresolute#1")
        assert {s["generator"] for s in row["sources"]} == {"antonym_check", "censuses"}
        assert row["filter"]["rule"] == "floor" and row["filter"]["batch_id"] == "m3_pilot_antonym_check"

    def test_predicates(self, f3_registry, fake_zipf):
        rows = Registry(f3_registry).fold()
        assert F.is_free_floor_reject(rows["irresolute#1"]) and F.is_free_floor_reject(rows["restrictionist#1"])
        assert not F.is_free_floor_reject(rows["pettish#1"]) and not F.is_free_floor_reject(rows["kindly#1"])
        assert not F.is_free_floor_reject(rows["newword#1"])
        assert F.floor_reject_rescued(rows["irresolute#1"])           # gloss hint (and curated)
        assert F.floor_reject_rescued(rows["restrictionist#1"])       # curated, no gloss hint
        assert not F.floor_reject_rescued(rows["sybaritic#1"])        # antonym_check + roget: neither rescues
        assert not F.floor_reject_rescued(rows["pettish#1"])          # a probe verdict stands

    def test_run_selection_refilters_the_rescued_row(self, f3_registry):
        items = select(f3_registry, run=("censuses", "t1"))
        assert sorted(it.key for it in items) == ["irresolute#1", "newword#1"]        # not kindly (filtered)
        irr = next(it for it in items if it.key == "irresolute#1")
        assert irr.curated and irr.intended_sense and irr.familiarity == 0.67
        assert sorted(it.key for it in select(f3_registry, run=("censuses", "rare1"))) == ["restrictionist#1"]
        assert select(f3_registry, run=("roget", "r1")) == []                         # sybaritic stays cut

    def test_unfiltered_selection_includes_the_rescued_rows(self, f3_registry):
        assert sorted(it.key for it in select(f3_registry)) == ["irresolute#1", "newword#1", "restrictionist#1"]

    def test_selected_row_goes_to_the_probe_not_the_floor(self, f3_registry, fake_zipf):
        """The re-selected row reaches the filter's own floor step and passes it by the rescue route."""
        items = [it for it in select(f3_registry, run=("censuses", "t1")) if it.key == "irresolute#1"]
        runner = FilterRunner(client=None, batch_id="refilter", wordnet=False, zipf_fn=fake_zipf)
        todo = runner.prepare(items)
        res = runner.results["irresolute#1"]
        assert todo == items and res.stage == "pending"
        assert res.freq["hard_reject"] is False and res.freq["probe_band"] is True and res.freq["rescue"] == "gloss_hint"

    def test_keys_selection_unchanged(self, f3_registry):
        args = argparse.Namespace(validation_file=None, sample_frac=None, registry=f3_registry,
                                  keys=["sybaritic#1", "pettish#1"], run=None, limit=None)
        items, _ = TF.select_items(args)
        assert [it.key for it in items] == ["sybaritic#1", "pettish#1"]


# ---------------------------------------------------------------------------
# F4 / F5: the evaluation counts the floor cuts and the post-split pools
# ---------------------------------------------------------------------------

def test_evaluation_counts_floor_and_probe_cuts(tmp_path, fake_zipf):
    rows, extra, data = iv_table(tmp_path)
    cdir = tmp_path / "candidates"
    reg = cdir / "registry.jsonl"
    # obscurish (a TDA word) was floor-rejected unread under another generator before the TDA run reached it
    submit_candidates([other("obscurish")], registry_path=reg)
    Registry(reg).update_many({"obscurish#1": {"filter": dict(SPLIT_FLOOR), "freq": dict(FLOOR_FREQ)}},
                              merge_blocks=False)
    S.run_submit("tda", "r1", table=rows, sources_manifest=[{"key": "x"}], registry_path=reg, candidates_dir=cdir,
                 echo=lambda *a: None)
    r = Registry(reg)
    r.merge_block("abandoned#1", "filter", {**SPLIT_FLOOR, "rule": "probe", "cause": "probe", "model": "m"},
                  replace=True)
    r.merge_block("kind#1", "filter", {"verdict": "trait", "tags": [], "outcome": "trait"})
    counts = I.ingest_counts(rows, extra)
    counts["ceiling"] = E.string_ceiling(rows, corpus_trait_stems(data)).as_dict()
    rdir = cdir / "runs" / "censuses" / "r1"
    ev = R.evaluate_run("r1", run_dir=rdir, table=rows, ingest_counts=counts, registry_rows=r.fold(),
                        corpus_stems=corpus_trait_stems(data), candidates_dir=cdir)
    fl = ev["floor"]
    assert fl["tda_cut"] == 1                                                # no longer the literal 0
    cuts = fl["registry_cuts"]
    assert (cuts["n_floor"], cuts["n_floor_tda"], cuts["n_floor_rescued_now"], cuts["n_probe"]) == (1, 1, 1, 1)
    assert cuts["floor"] == [{"key": "obscurish#1", "stem": "obscurish", "tda": True,
                              "batch_id": "m3_pilot_antonym_check", "generators": ["antonym_check", "censuses"],
                              "rescued_now": True}]
    assert fl["stage_pools"]["stages"]["allport_iv_rare"] == 2 and fl["stage_pools"]["stages"]["allport_iv"] == 2
    assert ev["stage_rule"] == S.STAGE_RULES["tda"]
    json.dumps(ev)
    md = R.render_readout(ev, doc_path=rdir / "readout.md", run_dir=rdir, table_path=tmp_path / "t.jsonl",
                          counts_path=tmp_path / "c.json", manifest_path=tmp_path / "m.json")
    assert "| TDA words cut by the floor | 1 " in md
    assert "obscurish (antonym_check, censuses; now rescued" in md
    assert "cut by the definition probe (\"not known\") | 1 |" in md
    assert "allport_iv_rare 2" in md and "census rows in no stage | malformed 1, unknown_word 3 |" in md


def test_readout_of_an_evaluation_without_the_new_blocks(tmp_path):
    """An evaluation written before 2026-10-12 has no registry_cuts or stage_pools; the readout still renders."""
    rows, extra, data = iv_table(tmp_path)
    cdir = tmp_path / "candidates"
    S.run_submit("tda", "r1", table=rows, sources_manifest=[], registry_path=cdir / "registry.jsonl",
                 candidates_dir=cdir, echo=lambda *a: None)
    rdir = cdir / "runs" / "censuses" / "r1"
    ev = R.evaluate_run("r1", run_dir=rdir, table=rows, ingest_counts=I.ingest_counts(rows, extra),
                        registry_rows=Registry(cdir / "registry.jsonl").fold(), corpus_stems=set(),
                        candidates_dir=cdir)
    for k in ("registry_cuts", "stage_pools"):
        ev["floor"].pop(k)
    ev.pop("stage_rule")
    md = R.render_readout(ev, doc_path=rdir / "readout.md", run_dir=rdir, table_path=tmp_path / "t.jsonl",
                          counts_path=tmp_path / "c.json", manifest_path=tmp_path / "m.json")
    assert "| TDA words cut by the floor | 0 " in md and "census stages" not in md


# ---------------------------------------------------------------------------
# P5: the OEWN lemma on the table row
# ---------------------------------------------------------------------------

LEMMAS = {"leaguing": {"v": {"league"}}, "kind": {"n": {"kind"}, "a": {"kind"}},
          "better": {"n": {"better"}, "a": {"good", "well", "better"}}, "fretted": {"v": {"fret"}, "a": {"fretted"}},
          "chafings": {"n": {"chafing"}, "v": {"chafe"}}, "a la mode": {"a": {"a la mode"}}}


def fake_lemmatize(form):
    return {pos: set(v) for pos, v in LEMMAS.get(form, {}).items()}


def test_oewn_lemma_rules():
    assert oewn_lemma("leaguing", fake_lemmatize) == "league"
    assert oewn_lemma("kind", fake_lemmatize) == "kind"              # a lemma itself
    assert oewn_lemma("better", fake_lemmatize) == "better"
    assert oewn_lemma("fretted", fake_lemmatize) == "fretted"
    assert oewn_lemma("chafings", fake_lemmatize) == "chafing"       # nouns before verbs
    assert oewn_lemma("a-la-mode", fake_lemmatize) == "a la mode"    # through the lookup forms
    assert oewn_lemma("gnarlywise", fake_lemmatize) is None
    assert oewn_lemma("x", lambda f: {None: {"x"}}) is None          # an uninitialised Morphy echoes the form


def test_table_records_the_lemma_and_eligibility_ignores_it(tmp_path):
    entries = [("Leaguing", "II", 0.0, False)]
    data = make_corpus(tmp_path)
    allport, merged, tda = fixture_inputs()
    allport += [I.RawEntry(raw=raw, line=200, column=col) for raw, col, _, _ in entries]
    with_lemma, extra = I.build_table(allport, tda, lookups=fake_lookups(lemmatize=fake_lemmatize),
                                      corpus_stems=corpus_trait_stems(data), merged=merged)
    without, _ = I.build_table(allport, tda, lookups=fake_lookups(), corpus_stems=corpus_trait_stems(data),
                               merged=merged)
    by = {r.stem: r for r in with_lemma}
    lg = by["leaguing"]
    assert lg.unknown_word and lg.ineligible_reason == "unknown_word" and lg.oewn_lemma == "league"
    assert by["kind"].oewn_lemma == "kind" and by["a_la_mode"].oewn_lemma == "a la mode"
    assert by["afald"].oewn_lemma is None
    # the field is information only: every other field is the same with and without the lemmatiser
    strip = lambda rs: [{k: v for k, v in dataclasses.asdict(r).items() if k != "oewn_lemma"} for r in rs]  # noqa: E731
    assert strip(with_lemma) == strip(without) and all(r.oewn_lemma is None for r in without)
    c = I.ingest_counts(with_lemma, extra)
    assert c["unknown_word_with_oewn_lemma"] == 1 and c["with_oewn_lemma"] == 3      # leaguing, kind, a la mode


def test_a_table_written_before_the_field_loads(tmp_path):
    rows, _, _ = iv_table(tmp_path)
    old = [{k: v for k, v in r.to_json().items() if k != "oewn_lemma"} for r in rows]
    p = tmp_path / "old.jsonl"
    p.write_text("".join(json.dumps(d) + "\n" for d in old))
    back = load_census_table(p)
    assert [r.oewn_lemma for r in back] == [None] * len(rows) and [r.stem for r in back] == [r.stem for r in rows]
    assert list(rows[0].to_json())[-1] == "oewn_lemma"                 # added at the end, no schema bump
    assert rows[0].schema_version == 1
