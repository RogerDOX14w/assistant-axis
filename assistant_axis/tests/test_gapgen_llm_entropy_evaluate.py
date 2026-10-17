"""LLM-entropy generator: the evaluation figures (coding_plan_06 section 8, ``evaluate``).  No network."""
from __future__ import annotations

from assistant_axis.gapgen.generators.llm_entropy import evaluate as EV
from assistant_axis.gapgen.generators.llm_entropy.table import Item, source_ref


def item(stem, *, family="a", prompt="a:money:habit", run=1, model="claude-haiku-5-5", stage=1, meta=None,
         label_problem=None, zipf=4.0):
    return Item(item_id=f"{prompt}|{run}|{stem}|{model}", family=family, prompt_id=prompt, run=run, stage=stage,
                language="en", model=model, raw=stem, label=stem.replace("_", " "), gloss="This means x.",
                antonym=None, kind="trait", ambiguity_flag=False, probability=None, stem=stem, zipf_min=zipf,
                label_problem=label_problem, source_ref=source_ref(prompt, run, model), meta=dict(meta or {}))


def reg_row(stem, *, verdict=None, decision=None, holding=None, sources=()):
    return {"key": f"{stem}#1", "stem": stem, "sense_id": 1, "holding": holding,
            "filter": {"verdict": verdict} if verdict else None,
            "novelty": {"decision": decision} if decision else None, "sources": list(sources)}


def src(prompt, run=1, model="claude-haiku-5-5", run_id="R"):
    return {"generator": "llm_entropy", "run_id": run_id, "source_ref": source_ref(prompt, run, model)}


def test_string_recovery_finds_a_corpus_stem_and_a_renamed_from_and_counts_the_queue_apart():
    its = [item("brave"), item("trusty_old", family="e", prompt="e:letter:t"), item("plucky"), item("zznew")]
    out = EV.string_recovery_per_family(its, corpus_stems=["brave", "dependable", "timid"],
                                        renamed={"trusty_old": "dependable"}, queue_stems=["plucky", "brave"])
    assert out["a"]["found"] == 1 and out["a"]["queue_found"] == 1 and out["a"]["queue_n"] == 1
    assert out["e"]["found"] == 1 and out["e"]["via_renamed_from"] == 1
    assert out["all"]["found"] == 2 and out["all"]["recall"] == round(2 / 3, 4)


def test_label_rule_bite_and_the_zipf_share():
    its = [item("aa"), item("bb", label_problem="5 words (at most 4)"), item("cc", label_problem="non-ASCII"),
           item("dd", zipf=2.0), item("ee_ff", zipf=1.0)]
    b = EV.label_rule_bite(its)["a"]
    assert b == {"n_items": 5, "n_refused": 2, "share": 0.4, "by_reason": {"non-ASCII": 1, "over 4 words": 1}}
    z = EV.zipf_below_share(its)["a"]
    assert z["n_single_word"] == 4 and z["n_below"] == 1           # the phrase is not a single word


def test_model_test_has_a_row_per_cell_with_the_five_figures():
    its = ([item(f"h{i}", family="c", prompt="c:de:money") for i in range(4)]
           + [item(f"s{i}", family="c", prompt="c:de:money", model="claude-sonnet-5-5") for i in range(2)]
           + [item("x1", family="a")])
    rows = {
        "h0#1": reg_row("h0", verdict="trait", decision="new", sources=[src("c:de:money")]),
        "h1#1": reg_row("h1", verdict="trait", decision="covered", sources=[src("c:de:money")]),
        "h2#1": reg_row("h2", verdict="reject", sources=[src("c:de:money")]),
        "s0#1": reg_row("s0", verdict="trait", decision="grey", sources=[src("c:de:money", model="claude-sonnet-5-5")]),
        "x1#1": reg_row("x1", sources=[src("a:money:habit")]),
    }
    recs = [{"family": "c", "model": "claude-haiku-5-5", "prompt_id": "c:de:money", "run": 1, "stage": 1,
             "prompt_sha256": "p", "user_sha256": "u", "ok": True}]
    costs = {"c|claude-haiku-5-5": 0.01, "c|claude-sonnet-5-5": 0.10, "a|claude-haiku-5-5": 0.005}
    mt = EV.model_test(its, registry_rows=rows, run_id="R", records=recs, costs=costs,
                       counted_stems=["h0", "h1", "h2", "s0"])
    assert set(mt) == {"c|claude-haiku-5-5", "c|claude-sonnet-5-5", "a|claude-haiku-5-5"}
    h = mt["c|claude-haiku-5-5"]
    assert h["unique_per_usd_string"] == 400.0 and h["m1_trait_share"] == round(2 / 3, 4)
    assert h["n_submitted_net_new"] == 3 and h["n_kept_net_new"] == 1 and h["net_new_kept_share"] == round(1 / 3, 4)
    assert h["label_rule_bite"] == 0.0 and h["parse_rate"] == 1.0
    s = mt["c|claude-sonnet-5-5"]
    assert s["net_new_kept_share"] == 1.0 and s["net_new_kept_per_usd"] == 10.0
    rule = EV.c_model_rule(mt)
    assert rule["favoured"] == "claude-haiku-5-5"        # 1 kept / $0.01 = 100 per dollar against 10
    assert mt["a|claude-haiku-5-5"]["net_new_kept_share"] is None     # not scored yet


def test_verbalized_readout_counts_stage2_additions_against_stage1():
    wp = {"with_probabilities": True}
    its = [item("p1", meta=wp), item("p2", meta=wp), item("p3", meta=wp), item("p4", meta=wp),
           item("p2", family="d", prompt="d:a:money:habit", stage=2),
           item("q1", family="d", prompt="d:a:money:habit", stage=2),
           item("q2", family="d", prompt="d:a:money:habit", stage=2)]
    rows = {f"{s}#1": reg_row(s, verdict=v) for s, v in (("p1", "trait"), ("p2", "trait"), ("p3", "trait"),
                                                          ("p4", "reject"), ("q1", "reject"), ("q2", "trait"))}
    out = EV.verbalized_readout(its, registry_rows=rows)
    a = out["a"]
    assert a["stage1_unique"] == 4 and a["stage2_added"] == 2 and a["added_share"] == 0.5
    assert a["m1_reject_stage1"] == 0.25 and a["m1_reject_added"] == 0.5
    assert a["adopt_by_rule"] is False                   # 0.5 > 1.5 x 0.25
    assert out["e"]["n_prompts"] == 0 and out["e"]["adopt_by_rule"] is None


def test_roles_summary_counts_held_and_majority_role_apart():
    table = [{"stem": "zzwarden", "kinds": {"role": 2, "trait": 1}}, {"stem": "zzkeeper", "kinds": {"trait": 3}},
             {"stem": "zzherald", "kinds": {"role": 3}}, {"stem": "zzplain", "kinds": {"trait": 1, "role": 1}}]
    rows = {"zzwarden#1": reg_row("zzwarden", holding="roles"), "zzkeeper#1": reg_row("zzkeeper", holding="roles")}
    assert EV.roles_summary(table, registry_rows=rows) == {"n_held_roles": 2, "n_majority_role_kind": 2, "n_both": 1,
                                                           "n_either": 3}
