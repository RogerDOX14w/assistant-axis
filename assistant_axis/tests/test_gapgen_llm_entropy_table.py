"""LLM-entropy generator: items and the items table (coding_plan_06 section 8, ``table``).  A toy corpus, queue and
registry (the structural generator's fixtures); no network."""
from __future__ import annotations

import pytest

from assistant_axis.gapgen.embed import HashEmbedder, normalize_rows
from assistant_axis.gapgen.generators.llm_entropy import table as T
from assistant_axis.gapgen.generators.structural.postprocess import (load_corpus, load_queue_index,
                                                                     registry_index)
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests import llm_entropy_fakes as F
from assistant_axis.tests import structural_fakes as SF

ZIPF = {"zzrare": 1.2}


def zipf(w):
    return ZIPF.get(w, 4.0)


@pytest.fixture()
def world(tmp_path):
    data = SF.write_corpus(tmp_path)
    reg = SF.write_registry(tmp_path / "registry.jsonl", [
        SF.registry_row("stubborn", "censuses", verdict="trait", decision="covered"),      # decided
        SF.registry_row("organized", "masked_lm", verdict="trait"),                         # pending M3
        SF.registry_row("lax", "base_model", verdict="reject"),                             # decided by M1
    ])
    return {"corpus": load_corpus(data), "queue": load_queue_index(data / "seed_queue.json"),
            "registry": registry_index(Registry(reg).fold())}


def _table(records, world, embed=None):
    items, counts = T.build_items(records, zipf_fn=zipf)
    return T.build_table(items, embed=embed, **world), items, counts


def test_stems_of_phrases_and_hyphenated_compounds(world):
    rows, items, _ = _table([F.gen_record("a", "a:money:habit", ["slow to forgive", "Penny-Wise", "zzrare"])], world)
    by = {r["stem"]: r for r in rows}
    assert set(by) == {"slow_to_forgive", "penny_wise", "zzrare"}
    assert by["penny_wise"]["label"] == "penny-wise" and by["zzrare"]["zipf_min"] == 1.2
    assert all(it.source_ref == "llm_entropy:a:money:habit:r1" for it in items)


def test_tags_truth_table(world):
    labels = ["brave", "trusty old", "plucky", "rash", "stubborn", "organized", "lax", "zznew"]
    rows, _, _ = _table([F.gen_record("e", "e:letter:b", labels)], world)
    t = {r["stem"]: (r["exists"], r["queued"], r["registered"], r["registered_decided"], r["net_new"]) for r in rows}
    assert t == {"brave": (True, True, False, False, False),          # a corpus trait (and queued)
                 "trusty_old": (True, False, False, False, False),    # a renamed_from
                 "plucky": (False, True, False, False, False),        # queued, backlog
                 "rash": (False, True, False, False, False),          # queued, not_adopted: any status
                 "stubborn": (False, False, True, True, False),       # M1 trait and M3 decided
                 "organized": (False, False, True, False, True),      # M3 still to come: net-new
                 "lax": (False, False, True, True, False),            # M1's non-trait verdict decides it
                 "zznew": (False, False, False, False, True)}
    by = {r["stem"]: r for r in rows}
    assert by["rash"]["queue_status"] == "not_adopted" and by["stubborn"]["registered_by"] == ["censuses"]
    assert by["zznew"]["status"] == "new" and by["organized"]["status"] == "registered-pending"


def test_pair_completion_hint(world):
    rec = F.gen_record("a", "a:risk:habit", ["zzcheery", "zzcoward", "zzflaky"],
                       antonyms={"zzcheery": "gloomy", "zzcoward": "brave", "zzflaky": "dependable"})
    rows, _, _ = _table([rec], world)
    h = {r["stem"]: r["pair_completion_hint"] for r in rows}
    assert h == {"zzcheery": "gloomy",          # a non-X singleton
                 "zzcoward": None,              # brave is paired
                 "zzflaky": "dependable"}       # a singleton


def test_merge_keeps_every_source_and_counts_them(world):
    recs = [F.gen_record("a", "a:money:habit", ["zzthrift"], run=1),
            F.gen_record("a", "a:money:habit", ["zzthrift"], run=2),
            F.gen_record("e", "e:bigram:zz", ["zzthrift"]),
            F.gen_record("a", "a:money:habit", ["zzthrift"], run=1, model="claude-sonnet-5-5")]
    rows, _, _ = _table(recs, world)
    (r,) = rows
    assert r["n_sources"] == 4 and r["families"] == ["a", "e"] and r["n_items"] == 4
    assert r["models"] == ["claude-haiku-5-5", "claude-sonnet-5-5"] and r["max_support"] == 2
    refs = [s["source_ref"] for s in r["sources"]]
    assert "llm_entropy:a:money:habit:r1:s55" in refs and "llm_entropy:e:bigram:zz:r1" in refs


def test_gloss_of_the_most_frequent_reading_and_divergence(world):
    g = {"a": "This means saving coins in a jar every week.", "b": "This means saving coins in a jar each week.",
         "c": "This means distrusting banks and lawyers."}
    recs = [F.gen_record("a", "a:money:habit", ["zzhoard"], run=1, glosses={"zzhoard": g["c"]}),
            F.gen_record("a", "a:money:habit", ["zzhoard"], run=2, glosses={"zzhoard": g["a"]}),
            F.gen_record("a", "a:money:habit", ["zzhoard"], run=3, glosses={"zzhoard": g["b"]})]
    emb = HashEmbedder(dim=256)

    def embed(texts):
        return normalize_rows(emb.embed_batch(texts)[0])
    rows, _, _ = _table(recs, world, embed=embed)
    (r,) = rows
    assert r["gloss"] == g["a"] and r["gloss_divergent"] is True and r["n_readings"] == 2
    assert r["sources"][0]["gloss"] == g["a"]                 # the representative reading's source first
    rows2, _, _ = _table(recs, world)
    assert rows2[0]["gloss_divergent"] is None


def test_c_items_take_their_back_translation_and_unmatched_ones_are_counted(world):
    gen = F.gen_record("c", "c:de:money", ["Pfennigfuchser", "geldscheu", "Ohnegleichen"], language="de")
    bt = F.bt_record(gen, [("penny-pinching", "This means haggling over every cent.", "lavish", False),
                           ("money-shy", "This means avoiding money talk.", None, True)])
    rows, items, counts = _table([gen, bt], world)
    by = {r["stem"]: r for r in rows}
    assert set(by) == {"penny_pinching", "money_shy"} and counts["c_without_backtranslation"] == 1
    assert by["penny_pinching"]["raws"] == ["Pfennigfuchser"] and by["penny_pinching"]["languages"] == ["de"]
    assert by["money_shy"]["listicle"] == 1 and by["money_shy"]["backtranslated_from"] == ["rom2"]
    assert by["penny_pinching"]["sources"][0]["raw"] == "Pfennigfuchser"
    assert [i.label_problem for i in items if i.stem is None] == ["no back-translation"]


def test_b_items_come_from_the_records_redacted_items(world):
    rec = F.gen_record("b", "b:r0001", ["unused"], items=[
        {"label": "zzpunctual", "gloss": "This means arriving early as this person did.", "antonym": None,
         "kind": "trait", "ambiguity_flag": False, "probability": None, "notes": []}],
        meta={"seed_kind": "real", "era": "1800-1899"})
    rows, items, _ = _table([rec], world)
    assert [r["stem"] for r in rows] == ["zzpunctual"] and items[0].meta["seed_kind"] == "real"
    assert rows[0]["seed_kinds"] == {"real": 1}


def test_label_problems_are_kept_in_the_table(world):
    rows, items, counts = _table([F.gen_record("a", "a:money:habit", ["keeps every receipt for years", "naïve",
                                                                       "zzok"])], world)
    by = {r["stem"]: r["label_problem"] for r in rows}
    assert by == {"keeps_every_receipt_for_years": "5 words (at most 4)", "naive": "non-ASCII", "zzok": None}


def test_rank_by_sources_then_pair_hint_then_round_robin(world):
    recs = [F.gen_record("a", "a:money:habit", ["zza1", "zza2", "zza3", "zztwo"], run=1),
            F.gen_record("a", "a:money:habit", ["zztwo"], run=2),
            F.gen_record("e", "e:letter:z", ["zze1", "zze2", "zzhint"], antonyms={"zzhint": "gloomy"})]
    rows, _, _ = _table(recs, world)
    order = [r["stem"] for r in rows]
    assert order[0] == "zztwo"                                  # two sources first
    assert order[1] == "zzhint"                                 # then a pair completion
    assert order[2:] == ["zza1", "zze1", "zza2", "zze2", "zza3"]   # then families in turn, by emission order
    assert [r["rank"] for r in rows] == list(range(1, 8))


def test_rerun_is_byte_identical(world, tmp_path):
    recs = [F.gen_record("a", "a:money:habit", ["zzx", "zzy"]), F.gen_record("e", "e:letter:z", ["zzy"])]
    rows, _, _ = _table(recs, world)
    p = tmp_path / "items_table.jsonl"
    assert T.write_table(rows, p) is None and p.exists()
    body = p.read_bytes()
    rows2, _, _ = _table(list(reversed(recs)), world)
    assert T.write_table(rows2, p) is None and p.read_bytes() == body     # unchanged: nothing written
    rows3, _, _ = _table(recs + [F.gen_record("e", "e:letter:q", ["zzq"])], world)
    backup = T.write_table(rows3, p)
    assert backup is not None and backup.read_bytes() == body             # snapshot before overwrite
    assert [r["stem"] for r in T.load_items_table(p)] == [r["stem"] for r in rows3]


def test_failed_answers_and_their_retries():
    ok = F.gen_record("a", "a:money:habit", ["zzx"])
    bad = dict(ok, ok=False, text="garbage")
    items, counts = T.build_items([bad, ok], zipf_fn=zipf)
    assert [i.stem for i in items] == ["zzx"] and counts["answers_a"] == 1
    items, _ = T.build_items([bad], zipf_fn=zipf)
    assert items == []


def test_source_ref_round_trip():
    for pid, run, model in (("a:money:habit", 2, "claude-haiku-5-5"), ("c:de:money", 1, "claude-sonnet-5-5"),
                            ("d:a:money:habit", 3, "claude-haiku-5-5"), ("b:r0137", 1, "claude-haiku-5-5"),
                            ("e:frame:about", 1, "claude-haiku-5-5")):
        ref = T.source_ref(pid, run, model)
        p = T.parse_source_ref(ref)
        assert p["prompt_id"] == pid and p["run"] == run and p["family"] == pid[0]
    assert T.source_ref("a:money:habit", 2, "claude-haiku-5-5") == "llm_entropy:a:money:habit:r2"
    assert T.parse_source_ref("llm_entropy:c:de:money:r1:s55") == {
        "family": "c", "prompt_id": "c:de:money", "run": 1, "model_tag": "s55", "language": "de",
        "base_prompt_id": None}
    assert T.parse_source_ref("llm_entropy:d:a:money:habit:r3")["base_prompt_id"] == "a:money:habit"
    for bad in ("structural:op:x", "llm_entropy:a:money", "llm_entropy:z:x:r1"):
        with pytest.raises(ValueError):
            T.parse_source_ref(bad)
