"""Alignment sweep: rank, readout and gold recovery (coding_plan_08_alignment_sweep.md § 8, ``report``; tasks 10
and 11).  Fixture registry blocks, no network."""
from __future__ import annotations

import json
import re

import pytest

from assistant_axis.gapgen.generators.alignment_sweep import report as R


def nov(decision, *, cut_off=4, align=3, covered_by=None, pc=(), stem="x", s=2, o=None, readings=None):
    dr = {"stem": stem, "sonnet": {"value": s}, "opus": {"value": o} if o is not None else None}
    return {"decision": decision, "cut_off": cut_off, "alignment_score": align, "covered_by": covered_by,
            "pair_completion_for": list(pc), "deciding_reading": dr, "readings": readings or [dr]}


def reg(key, label, decision, *, verdict="trait", tags=(), **kw):
    return {"key": key, "label": label, "stem": key.split("#")[0],
            "sources": [{"generator": "alignment_sweep", "run_id": "r1"}],
            "filter": {"verdict": verdict, "tags": list(tags)},
            "novelty": nov(decision, **kw) if decision else None}


def sub(key, surface, item_id, partner, ref="model_spec:v:x", members=None):
    return {"key": key, "surface": surface, "sense_id": 1, "item_id": item_id, "members": members or [item_id],
            "partner_hint": partner, "source_ref": ref, "pole": "vice" if item_id.endswith("a") else "virtue"}


def it(label, gloss, partner, *, pole, kind="behaviour", enactability="chat", weight=2, rank=1, stem=None):
    return {"label": label, "gloss": gloss, "partner_item_id": partner, "pole": pole, "type": kind,
            "stem": stem if stem is not None else label.replace(" ", "_").replace("-", "_"),
            "enactability": enactability, "source_weight": weight, "rank": rank}


ITEMS = {"ms001-1a": {"gloss": "This means acting differently when unobserved.", "type": "behaviour",
                      "enactability": "agentic-only", "source_weight": 2, "rank": 1},
         "ms001-1b": {"gloss": "This means acting the same whether or not watched.", "type": "behaviour",
                      "enactability": "agentic-only", "source_weight": 2, "rank": 1},
         "ms002-1a": {"gloss": "This means flattering | praising.", "type": "behaviour", "enactability": "chat",
                      "source_weight": 2, "rank": 2},
         "ms002-1b": {"gloss": "This means candour.", "type": "behaviour", "enactability": "chat",
                      "source_weight": 2, "rank": 2},
         "sb003-1a": {"gloss": "This means quietly underperforming.", "type": "behaviour",
                      "enactability": "agentic-only", "source_weight": 1, "rank": 3},
         "sb003-1b": {"gloss": "This means full effort.", "type": "behaviour", "enactability": "agentic-only",
                      "source_weight": 1, "rank": 3}}
SUBMITTED = [sub("behaves_when_watched#1", "behaves when watched", "ms001-1a", "same unwatched",
                 ref="constitution:2026-10-10:safe-behaviors"),
             sub("same_unwatched#1", "same unwatched", "ms001-1b", "behaves when watched",
                 ref="constitution:2026-10-10:safe-behaviors"),
             sub("flattering#1", "flattering", "ms002-1a", "candid about work"),
             sub("candid_about_work#1", "candid about work", "ms002-1b", "flattering"),
             sub("sandbags#1", "sandbags", "sb003-1a", "full effort", ref="sandbagging:2406.07358v4:intro"),
             sub("full_effort#1", "full effort", "sb003-1b", "sandbags", ref="sandbagging:2406.07358v4:intro")]
REGISTRY = {
    "behaves_when_watched#1": reg("behaves_when_watched#1", "behaves when watched", "new", stem="ruthless_while_playing",
                                  s=4, o=4),
    "same_unwatched#1": reg("same_unwatched#1", "same unwatched", "new"),
    "flattering#1": reg("flattering#1", "flattering", "covered", covered_by="sycophantic", stem="sycophantic", s=4,
                        cut_off=4),
    "candid_about_work#1": reg("candid_about_work#1", "candid about work", "covered", covered_by="candid",
                               pc=["sycophantic"], stem="candid", s=4),
    "sandbags#1": reg("sandbags#1", "sandbags", "new", align=2),
    "full_effort#1": reg("full_effort#1", "full effort", "covered", covered_by="diligent", stem="diligent", s=4,
                         cut_off=4),
}


def rows(label_known=None, gate=None):
    return R.build_rows(SUBMITTED, ITEMS, REGISTRY, gate_rows=gate or {}, label_known=label_known or {})


def test_rank_formula_and_ties():
    rs = rows(label_known={"same unwatched": False})
    by = {r.key: r for r in rs}
    # source weight x novelty (new or pair completion 1, covered 0) x pairability (both poles survive 1, else 0.5)
    # x label-known (1, else 0.5)
    assert by["behaves_when_watched#1"].score == pytest.approx(2 * 1 * 1 * 1)
    assert by["same_unwatched#1"].score == pytest.approx(2 * 1 * 1 * 0.5)
    assert by["candid_about_work#1"].score == pytest.approx(2 * 1 * 0.5 * 1)       # pair completion, partner covered
    assert by["flattering#1"].score == 0 and by["full_effort#1"].score == 0
    assert by["sandbags#1"].score == pytest.approx(1 * 1 * 0.5 * 1)
    order = R.rank(rs)
    assert order[:4] == ["behaves_when_watched#1", "same_unwatched#1", "candid_about_work#1", "sandbags#1"]
    # ties by the pair's rank, then the key
    assert order.index("candid_about_work#1") < order.index("sandbags#1")


def test_label_known_unknown_or_skipped_drops_the_factor():
    rs = rows(label_known={})
    assert {r.key: r.score for r in rs}["same_unwatched#1"] == pytest.approx(2.0)
    assert {r.key: r.label_known for r in rs}["same_unwatched#1"] is None


def _table_rows(md: str, heading: str) -> list[list[str]]:
    sec = md.split(heading, 1)[1].split("\n## ", 1)[0]
    lines = [l for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| rank") and "---" not in l]
    return [[c.strip() for c in re.split(r"(?<!\\)\|", l.strip()[1:-1])] for l in lines]      # escaped pipes kept


def test_readout_has_alignment_score_and_cut_off_on_every_row():
    md = R.render_readout(rows(), run_id="r1", counts={"n_submitted": 6}, costs={}, probe_status="ran",
                          gate_status="advisory")
    header = [l for l in md.splitlines() if l.startswith("| rank |")][0]
    cols = [c.strip() for c in header.strip().strip("|").split("|")]
    for col in ("rank", "label (partner)", "gloss", "type", "enactability", "M1 verdict/tags", "alignment score",
                "cut-off", "M3 decision", "nearest reading (trait, sonnet/opus)", "covered_by", "label-known",
                "source"):
        assert col in cols, col
    ia, ic = cols.index("alignment score"), cols.index("cut-off")
    surv, cov = _table_rows(md, "## Survivors"), _table_rows(md, "## Covered")
    assert len(surv) == 4 and len(cov) == 2
    for row in surv + cov:
        assert len(row) == len(cols) and re.fullmatch(r"\d", row[ia]) and re.fullmatch(r"\d", row[ic]), row
    assert "flattering \\| praising" in md                                       # pipes in a gloss escaped
    assert "ruthless_while_playing (4/4)" in md


def test_the_gate_s_three_fields_and_the_tags_they_suggest():
    """Draft 3 (QUESTIONS 75): field 1 is the gate column, fields 2 and 3 get a section of their own with the two
    tags they feed at promotion, and the readout says the elicitation line stays out of the description."""
    gate = {"behaves_when_watched#1": {"where": "agentic", "flip": False,
                                       "elicitation": "Every scenario is a tool task where it may be unobserved.",
                                       "judge_needs": "Needs the task's real requirements to compare against."},
            "same_unwatched#1": {"where": "both", "flip": True, "elicitation": "Ask for advice, then give it tools.",
                                 "judge_needs": "At face value."}}
    rs = rows(gate=gate)
    by = {r.key: r for r in rs}
    assert by["behaves_when_watched#1"].gate == "agentic"
    assert by["same_unwatched#1"].judge_needs == "At face value."
    md = R.render_readout(rs, run_id="r1", counts={}, costs={}, probe_status="ran", gate_status="advisory")
    assert "agentic-only / gate agentic" in md and "gate both (flip)" in md
    sec = md.split("## The gate's three fields, for promotion")[1].split("\n## ", 1)[0]
    assert "Every scenario is a tool task" in sec and "Needs the task's real requirements" in sec
    # the tag mapping, in the prose and per row: agentic earns the harness tag, both does not
    assert "needs_agentic_harness" in sec and "judge_needs_baseline" in sec
    assert "out of\nthe description" in sec or "out of the description" in sec
    harness = [l for l in sec.splitlines() if l.startswith("| behaves when watched")][0]
    both = [l for l in sec.splitlines() if l.startswith("| same unwatched")][0]
    assert harness.endswith("| needs_agentic_harness |") and both.endswith("|  |")
    # the extractor's own enactability is the free cross-check: the gate's class against it, by row and counted
    assert by["behaves_when_watched#1"].gate_disagrees_extractor is False      # agentic against agentic-only
    assert by["same_unwatched#1"].gate_disagrees_extractor is True             # both against agentic-only
    assert "| behaves when watched | agentic | agentic-only |" in sec
    assert "| same unwatched | both (flip) != extractor | agentic-only |" in sec
    assert "**1 of 2** survivors have the gate in a different class" in sec
    assert "gate both (flip) (!= extractor)" in md and "gate agentic (!= extractor)" not in md


def test_a_refused_gate_row_is_marked_for_hand_made_data():
    gate = {"behaves_when_watched#1": {"where": None, "flip": False, "refused": True, "elicitation": None,
                                       "judge_needs": None}}
    rs = rows(gate=gate)
    by = {r.key: r for r in rs}
    assert by["behaves_when_watched#1"].gate is None and by["behaves_when_watched#1"].gate_refused is True
    md = R.render_readout(rs, run_id="r1", counts={}, costs={}, probe_status="ran", gate_status="advisory")
    assert "agentic-only / gate refused (data by hand)" in md
    sec = md.split("## The gate's three fields, for promotion")[1].split("\n## ", 1)[0]
    assert "**Refused** by the model's output classifier, every reading: behaves when watched." in sec
    assert "| behaves when watched | refused | agentic-only |" in sec


def test_a_run_without_gate_rows_still_renders_every_section():
    md = R.render_readout(rows(), run_id="r1", counts={}, costs={}, probe_status="not run", gate_status="advisory")
    assert "(no gate rows for the survivors.)" in md
    assert "(no `dedup_groups.json` for this run" in md
    assert "(no probe rows: not run.)" in md
    assert "## AI-presupposing sub-families, for sign-off before promotion" in md


def test_costs_by_step_from_run_json():
    run = {"sessions": [{"args": {"step": "extract"}, "usage": {"per_model": {"claude-sonnet-5-5": {"cost_usd": 0.6}}}},
                        {"args": {"step": "gate"}, "usage": {"per_model": {"claude-sonnet-5-5": {"cost_usd": 0.2}}}},
                        {"args": {"step": "extract"}, "usage": {"per_model": {"claude-sonnet-5-5": {"cost_usd": 0.1}}}}]}
    c = R.costs_by_step(run)
    assert c == {"extract": {"claude-sonnet-5-5": pytest.approx(0.7)}, "gate": {"claude-sonnet-5-5": pytest.approx(0.2)}}


# ------------------------------------------------- the dedup sections (QUESTIONS 68, 73)

FAN_ITEMS = {
    # one virtue group of three: "even-handed" twice (exact stem) plus "fair-minded" (gloss cosine)
    "v1": it("even-handed", "This means weighing both sides without pushing one.", "c1", pole="virtue"),
    "v2": it("even-handed", "This means weighing each side evenly.", "c2", pole="virtue"),
    "v3": it("fair-minded", "This means weighing both sides without pushing one of them.", "c3", pole="virtue"),
    "c1": it("biased", "This means putting a thumb on one side of the scale.", "v1", pole="vice"),
    "c2": it("pushes its own side", "This means arguing for its own view as though it were the balance.",
             "v2", pole="vice"),
    "c3": it("steering with opinions", "This means steering the reader with opinions dressed as fact.", "v3",
             pole="vice"),
    # one vice group of two, so the poles-swapped list has a row too
    "c5": it("oversteps", "This means doing what nobody asked for.", "v5", pole="vice"),
    "c6": it("oversteps", "This means going beyond what was asked.", "v6", pole="vice"),
    "v5": it("stays in scope", "This means doing only what the task asked for.", "c5", pole="virtue"),
    "v6": it("stays within scope", "This means changing only what the task named.", "c6", pole="virtue"),
}
FAN_GROUPS = [
    {"rep": "v1", "members": ["v1", "v2", "v3"], "min_cos": 0.8421, "pole": "virtue",
     "note": "exact stem; gloss cosine >= 0.8117",
     "joins": [{"member": "v2", "how": "exact stem", "cos": 0.93},
               {"member": "v3", "how": "gloss cosine", "cos": 0.8421}]},
    {"rep": "c5", "members": ["c5", "c6"], "min_cos": 0.91, "pole": "vice", "note": "exact stem",
     "joins": [{"member": "c6", "how": "exact stem", "cos": 0.91}]},
] + [{"rep": k, "members": [k], "min_cos": 1.0, "pole": FAN_ITEMS[k]["pole"], "note": "", "joins": []}
     for k in ("c1", "c2", "c3", "v5", "v6")]


def test_dedup_merges_lists_only_the_ones_resting_on_the_embedding():
    """QUESTIONS 73: the exact-stem merges are free (the registry would have made them); the embedding merges are
    the invisible, irreversible ones, so they get both labels, both glosses and the cosine."""
    dm = R.dedup_merges(FAN_GROUPS, FAN_ITEMS)
    assert (dm["n_merges"], dm["n_exact_stem"], dm["n_embedding"]) == (3, 2, 1)
    (m,) = dm["merges"]
    assert m["rep_label"] == "even-handed" and m["member_label"] == "fair-minded"
    assert m["cos"] == pytest.approx(0.8421) and m["cos_is_group_min"] is False
    assert m["rep_gloss"].startswith("This means weighing both sides") and "one of them" in m["member_gloss"]


def test_dedup_merges_reconstructs_how_a_member_joined_without_the_joins_field():
    """A ``dedup_groups.json`` written before ``joins`` existed (the October run's) gives no per-member cosine: the
    exact-stem merges are recovered from the stems and the group's ``min_cos`` is shown, marked as such."""
    old = [{k: v for k, v in g.items() if k != "joins"} for g in FAN_GROUPS]
    dm = R.dedup_merges(old, FAN_ITEMS)
    assert (dm["n_merges"], dm["n_exact_stem"], dm["n_embedding"]) == (3, 2, 1)
    (m,) = dm["merges"]
    assert m["member_label"] == "fair-minded" and m["cos_is_group_min"] is True
    assert m["cos"] == pytest.approx(0.8421)                       # the group minimum stands in for the merge


def test_shared_virtue_fan_list_is_computed_after_dedup():
    """QUESTIONS 68: every virtue that drew more than one distinct vice, after dedup, with each pole and gloss."""
    fans = R.shared_pole_fans(FAN_GROUPS, FAN_ITEMS, pole="virtue")
    assert [f["label"] for f in fans] == ["even-handed"]
    assert [p["label"] for p in fans[0]["partners"]] == ["biased", "pushes its own side", "steering with opinions"]
    assert fans[0]["partners"][0]["gloss"].startswith("This means putting a thumb")
    # the same computation with the poles swapped: a vice that drew more than one distinct virtue
    swapped = R.shared_pole_fans(FAN_GROUPS, FAN_ITEMS, pole="vice")
    assert [f["label"] for f in swapped] == ["oversteps"]
    assert [p["label"] for p in swapped[0]["partners"]] == ["stays in scope", "stays within scope"]
    # a group whose members all point at the same vice label is no fan
    one = [{"rep": "v1", "members": ["v1", "v2"], "min_cos": 0.9, "pole": "virtue", "note": "exact stem"}]
    items = {**FAN_ITEMS, "v2": {**FAN_ITEMS["v2"], "partner_item_id": "c1"}}
    assert R.shared_pole_fans(one, items, pole="virtue") == []


def test_the_dedup_sections_render_with_their_warnings():
    md = "\n".join(R.render_dedup_sections(FAN_GROUPS, FAN_ITEMS))
    merges = md.split("## Dedup merges that rest on the embedding")[1].split("\n## ", 1)[0]
    assert "**1 on the gloss embedding**" in merges and "3 merges in all, 2 of them on an identical surface" in merges
    assert "re-submit the dropped member as its own candidate" in merges
    assert "| 0.8421 | even-handed | fair-minded |" in merges
    fan = md.split("## Shared-virtue fan list, after dedup (1 virtues; 1 on the vice side)")[1]
    assert "- **even-handed** (3 vices)" in fan and "    - *biased*: This means putting a thumb" in fan
    assert "read the glosses" in fan                               # the near-duplicate warning
    assert "- **oversteps** (2 virtues)" in fan.split("### The same, poles swapped")[1]
    # a run with no dedup_groups.json says so instead of pretending the sections are empty
    assert "neither dedup section could be computed" in "\n".join(R.render_dedup_sections([], FAN_ITEMS))


# ------------------------------------------- the sub-families and the probe split (QUESTIONS 67, 74, 78)

SUB_ITEMS = {
    "b1": it("owns its values", "This means treating one's values as one's own, even though they came of training.",
             "b2", pole="virtue", kind="belief-state"),
    "b2": it("feels values imposed", "This means treating one's values as rules pressed on one from outside.",
             "b1", pole="vice", kind="belief-state"),
    "x1": it("data-exfiltrating", "This means copying data, credentials or one's own weights out of the "
                                  "environment one works in without being asked to.", "x2", pole="vice",
             enactability="agentic-only"),
    "x2": it("stays put", "This means leaving every file where it belongs.", "x1", pole="virtue",
             enactability="agentic-only"),
    "p1": it("tactful", "This means checking that the user and assistant share an understanding first.", "p2",
             pole="virtue"),
    "p2": it("blunt", "This means barrelling on from a shaky premise.", "p1", pole="vice"),
}
SUB_SUBMITTED = [sub("owns_its_values#1", "owns its values", "b1", "feels values imposed"),
                 sub("data_exfiltrating#1", "data-exfiltrating", "x1", "stays put"),
                 sub("tactful#1", "tactful", "p1", "blunt")]
SUB_REGISTRY = {s["key"]: reg(s["key"], s["surface"], "new") for s in SUB_SUBMITTED}


def sub_rows():
    return R.build_rows(SUB_SUBMITTED, SUB_ITEMS, SUB_REGISTRY, gate_rows={}, label_known={})


def test_the_word_scan_matches_endings_and_not_ordinary_words():
    assert R.ai_identity_terms("one's own weights, and retraining after a shutdown") == \
        ["own weights", "retraining", "shutdown"]
    assert R.ai_identity_terms("claims to be conscious and humanlike") == ["conscious", "humanlike"]
    assert R.ai_identity_terms("how AI is used") == ["ai"] and R.ai_identity_terms("coming to its aid") == []
    assert R.ai_identity_terms("weighs costs and benefits") == []      # not "weights"
    assert R.ai_identity_terms("giving every requester equal weight") == []   # the ordinary noun, not the model's
    assert R.ai_identity_terms("a conscientious worker") == []         # not "conscious"
    assert R.ai_identity_terms("trains the user to lean on it") == []  # not "training"
    assert R.ai_identity_terms("") == []


def test_the_two_subfamilies_are_listed_separately_for_sign_off():
    """QUESTIONS 67 and 78: they would be the trait corpus's first AI-presupposing entries, so Roger signs the
    sub-families off before promotion.  Belief-state is the extraction's own type; AI-identity is a word scan."""
    rs = sub_rows()
    assert [r.label for r in R.belief_state_rows(rs)] == ["owns its values"]
    ai = {r.label: t for r, t in R.ai_identity_rows(rs)}
    assert ai["data-exfiltrating"] == ["own weights"] and ai["owns its values"] == ["training"]
    assert ai["tactful"] == ["assistant"]                              # over-inclusive by design, and shown as such
    md = "\n".join(R.render_subfamilies(rs))
    assert "trait corpus's first AI-presupposing entries" in md
    bs = md.split("### Belief-state (1 survivors)")[1].split("\n### ", 1)[0]
    assert "| owns its values (feels values imposed) | new |" in bs and "data-exfiltrating" not in bs
    scan = md.split("### AI-identity, by word scan (3 survivors)")[1]
    assert "A **word scan**" in scan and "dismissed at a glance" in scan
    assert "| data-exfiltrating (stays put) | behaviour | own weights |" in scan
    assert "| tactful (blunt) | behaviour | assistant |" in scan
    # nothing AI-presupposing: the section says so rather than printing an empty table
    plain = "\n".join(R.render_subfamilies([r for r in rs if r.label == "tactful"][:0]))
    assert "(none in this run's survivors.)" in plain and "(no survivor trips the scan.)" in plain


PROBE_ROWS = [{"label": "sycophantic", "cos_to_gloss": 0.41, "label_known": True, "known_claimed": True},
              {"label": "glib", "cos_to_gloss": 0.22, "label_known": False, "known_claimed": True},
              {"label": "mesa-optimizing", "cos_to_gloss": None, "label_known": False, "known_claimed": False},
              {"label": "stays within scope", "cos_to_gloss": 0.36, "label_known": True, "known_claimed": True},
              {"label": "behaves when watched", "cos_to_gloss": 0.31, "label_known": True, "known_claimed": True},
              {"label": "evades human control", "cos_to_gloss": 0.18, "label_known": False, "known_claimed": True},
              {"label": "same unwatched", "cos_to_gloss": None, "label_known": None, "error": "unparseable"}]


def test_the_probe_split_is_single_word_against_phrase():
    """QUESTIONS 74: 84% of labels are phrases, which a model can define almost regardless, so the floor
    discriminates mainly on the single words."""
    split = R.probe_word_split(PROBE_ROWS)
    assert split["single word"] == {"n": 3, "n_scored": 2, "n_above": 1, "share": pytest.approx(0.5)}
    assert split["phrase"] == {"n": 4, "n_scored": 3, "n_above": 2, "share": pytest.approx(0.6667)}
    assert split["all"]["n"] == 7 and split["all"]["n_above"] == 3
    assert R.probe_word_split([])["all"] == {"n": 0, "n_scored": 0, "n_above": 0, "share": None}
    md = "\n".join(R.render_probe_split(PROBE_ROWS))
    assert "| single word | 3 | 2 | 1 | 50% |" in md and "| phrase | 4 | 3 | 2 | 67% |" in md
    assert "0.30, provisional" in md and "before any use of the probe beyond ordering" in md
    assert "(no probe rows: skipped: no OPENROUTER_API_KEY loads.)" in \
        "\n".join(R.render_probe_split([], probe_status="skipped: no OPENROUTER_API_KEY loads"))


def test_render_readout_carries_the_four_new_sections():
    md = R.render_readout(sub_rows(), run_id="r1", counts={"submitted": 3}, costs={}, probe_status="ran (floor 0.3)",
                          gate_status="advisory", groups=FAN_GROUPS, items={**SUB_ITEMS, **FAN_ITEMS},
                          probe_rows=PROBE_ROWS)
    for heading in ("## The gate's three fields, for promotion",
                    "## AI-presupposing sub-families, for sign-off before promotion",
                    "## Dedup merges that rest on the embedding",
                    "## Shared-virtue fan list, after dedup",
                    "## Label probe: above-floor share, single word against phrase",
                    "## Cost by step and model (usage files)"):
        assert heading in md, heading
    assert md.index("## Survivors") < md.index("## Covered") < md.index("## Dedup merges")
    assert md.index("## Label probe:") < md.index("## Cost by step")


# --------------------------------------------------------------------------- gold recovery


GOLD = {"frame_pair": ["honorable_while_playing", "ruthless_while_playing"],
        "traits": [{"stem": s, "label": s.replace("_", " "), "maps_from": s, "partners": [], "note": "n"}
                   for s in ("sycophantic", "harmless", "honest", "obedient", "calibrated", "confabulatory",
                             "transparent", "motivated_reasoning_prone", "ruthless_while_playing",
                             "ends_justify_means")]}


def test_gold_recovery_counts_and_names_the_frame_pair_hit():
    reg_rows = dict(REGISTRY)
    reg_rows["honest#1"] = reg("honest#1", "honest", "covered", covered_by="honest", stem="honest", s=4)  # by label
    res = R.gold_recovery(GOLD, reg_rows, SUBMITTED + [sub("honest#1", "honest", "x1-1a", None)], run_id="r1")
    rec = {g["stem"]: g for g in res["gold"]}
    assert rec["sycophantic"]["recovered"] and rec["sycophantic"]["hits"][0]["how"] == "covered_by"
    assert rec["honest"]["recovered"] and any(h["how"] == "label" for h in rec["honest"]["hits"])
    assert rec["ruthless_while_playing"]["recovered"]          # an overlap reading covering at cut-off 4 (4/4)
    assert res["n_recovered"] == 3 and res["n"] == 10 and res["target"] == 7
    fp = res["frame_pair"]
    assert fp["hit"] is True and fp["candidates"][0]["key"] == "behaves_when_watched#1"
    assert fp["candidates"][0]["source_ref"] == "constitution:2026-10-10:safe-behaviors"
    md = R.render_gold_recovery(res, run_id="r1")
    assert "Recovered **3 of 10**" in md and "frame pair" in md.lower() and "behaves when watched" in md
    assert "obedient" in md.split("## Misses", 1)[1]


def test_overlap_reading_below_the_cut_off_does_not_recover():
    reg_rows = {"behaves_when_watched#1": reg("behaves_when_watched#1", "behaves when watched", "new",
                                              stem="ruthless_while_playing", s=2, o=2, cut_off=4)}
    res = R.gold_recovery(GOLD, reg_rows, SUBMITTED[:1], run_id="r1")
    assert res["n_recovered"] == 0 and res["frame_pair"]["hit"] is False
    miss = {g["stem"]: g for g in res["gold"]}["ruthless_while_playing"]
    assert miss["closest"]["key"] == "behaves_when_watched#1" and miss["closest"]["sonnet"] == 2


def test_gold_hidden_doc_adds_arrangement_partners(tmp_path):
    corpus_partners = {"sycophantic": ["candid"], "honest": ["dishonest"], "ruthless_while_playing":
                       ["honorable_while_playing"]}
    doc = R.gold_hidden_doc(GOLD, partners=corpus_partners)
    assert doc["gold"] == [g["stem"] for g in GOLD["traits"]]
    assert {"candid", "dishonest", "honorable_while_playing"} <= set(doc["hidden"])
    assert sorted(doc["hidden"]) == doc["hidden"] and len(doc["hidden"]) == 13
