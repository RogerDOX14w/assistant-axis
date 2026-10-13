"""Structural generators: candidates, the cost guard, the wave's cut on net-new rows, the submission through the real
registry API, and the novel figure raw and net (coding_plan_09 section 8, ``submit`` and ``net-new``)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.structural import postprocess as PP
from assistant_axis.gapgen.generators.structural import report as R
from assistant_axis.gapgen.generators.structural import submit as SU
from assistant_axis.gapgen.registry import Registry, read_snapshot
from assistant_axis.tests import structural_fakes as F


def src(stem, op="excess", *, sub=None, label=None, partner=None, part="operators"):
    if part == "classical":
        return {"generator_part": "classical", "source_id": stem, "role": op, "label": label, "gloss": "This means x.",
                "kind": "classical", "partner_hint": partner}
    s = {"generator_part": "operators", "source_stem": stem, "operator": op, "label": label, "gloss": "This means x.",
         "kind": PP.operator_kind(op, sub, source_unpaired=False), "partner_hint": partner}
    if op == "retarget":
        s["target"] = sub
    elif op == "remode":
        s["mode"] = sub
    return s


def row(stem, rank, sources, *, siblings=(), label=None):
    label = label or stem.replace("_", " ")
    return {"schema_version": 1, "surface": label, "stem": stem, "label": label, "gloss": "This means x.",
            "sources": [{**s, "label": s.get("label") or label} for s in sources],
            "n_sources": len({(s["generator_part"], s.get("source_stem") or s.get("source_id")) for s in sources}),
            "roles": sorted({s.get("operator") or s.get("role") for s in sources}),
            "kinds": sorted({s["kind"] for s in sources}), "siblings": list(siblings),
            "has_common_word": True, "polysemy": False,
            "principal_target": any(s["kind"] == "principal_retarget" for s in sources), "rank": rank, "tier": 1}


@pytest.fixture()
def world(tmp_path):
    data = F.write_corpus(tmp_path)
    reg = F.write_registry(tmp_path / "registry.jsonl", [
        F.registry_row("foolhardy", "base_model", verdict="trait", decision="new"),     # decided by M1 and M3
        F.registry_row("dauntless", "censuses"),                                       # registered, undecided
    ])
    return {"data": data, "corpus": PP.load_corpus(data), "queue": PP.load_queue_index(data / "seed_queue.json"),
            "reg": reg, "cdir": tmp_path / "candidates", "tmp": tmp_path}


def tag(rows, w):
    return PP.apply_tags(rows, corpus=w["corpus"], queue=w["queue"],
                         registry=PP.registry_index(read_snapshot(w["reg"])))


def small_table(w):
    return tag([
        row("craven", 1, [src("brave", "deficiency", partner="foolhardy")], siblings=["brave", "foolhardy"]),
        row("foolhardy", 2, [src("brave", "excess", partner="craven")], siblings=["brave", "craven"]),
        row("cowardly", 3, [src("brave", "opposite", partner="brave")], siblings=["brave"]),
        row("hard_on_oneself", 4, [src("brave", "retarget", sub="self")], siblings=["brave"]),
        row("bold_spoken", 5, [src("brave", "remode", sub="speech")], siblings=["brave"]),
        row("dauntless", 6, [src("timid", "opposite", partner="timid")], siblings=["timid"]),
        row("courageous", 7, [src("aristotle:courage:mean", "mean", part="classical")]),
        row("rash", 8, [src("aristotle:courage:excess", "excess", part="classical", partner="cowardly")]),
    ], w)


# --------------------------------------------------------------------------- candidates

def test_one_candidate_per_source_with_partner_hints_score_and_source_ref(world):
    t = small_table(world)
    t[0]["sources"].append(src("timid", "excess", partner="timid-ish"))
    t[0]["n_sources"] = 2
    cands = SU.to_candidates(t, "r1")
    assert len(cands) == sum(len(r["sources"]) for r in t)
    by = {(c.surface, c.source_ref): c for c in cands}
    assert by[("craven", "structural:op:deficiency:brave")].partner_hint == "foolhardy"
    assert by[("foolhardy", "structural:op:excess:brave")].partner_hint == "craven"            # crossed
    assert by[("cowardly", "structural:op:opposite:brave")].partner_hint == "brave"
    assert by[("hard on oneself", "structural:op:retarget:self:brave")].partner_hint is None
    assert by[("bold spoken", "structural:op:remode:speech:brave")].partner_hint is None
    assert by[("courageous", "structural:classical:aristotle:courage:mean")].partner_hint is None
    assert by[("rash", "structural:classical:aristotle:courage:excess")].partner_hint == "cowardly"
    assert {c.score for c in cands if c.surface == "craven"} == {2.0}
    assert all(c.generator == "structural" and c.sense_id == 1 and c.rank for c in cands)


@pytest.mark.parametrize("ref,want", [
    ("structural:op:opposite:brave", {"operator": "opposite", "role": "opposite", "source_stem": "brave"}),
    ("structural:op:retarget:the_user:obedient", {"operator": "retarget", "target": "the_user",
                                                  "source_stem": "obedient"}),
    ("structural:op:remode:speech:brave", {"operator": "remode", "mode": "speech", "source_stem": "brave"}),
    ("structural:classical:aristotle:courage:excess", {"source_id": "aristotle:courage:excess", "role": "excess"}),
    ("structural:classical:sins_virtues:contrary:humility", {"role": "virtue"}),
    ("structural:classical:theophrastus:07:loquacity", {"role": "vice"}),
    ("structural:classical:via:zest:overuse", {"role": "overuse"}),
])
def test_source_ref_parses_back_to_a_role(ref, want):
    got = SU.parse_source_ref(ref)
    assert {k: got[k] for k in want} == want
    for bad in ("structural:op:sideways:brave", "structural:op:retarget:brave", "masked_lm:x:y", "structural:x"):
        with pytest.raises(ValueError):
            SU.parse_source_ref(bad)


def test_source_ref_round_trips_every_source(world):
    for r in small_table(world):
        for s in r["sources"]:
            p = SU.parse_source_ref(SU.source_ref(s))
            assert p.get("source_stem", p.get("source_id")) == (s.get("source_stem") or s.get("source_id"))


def test_structural_is_not_a_familiarity_generator():
    """``Candidate.score`` is ``n_sources``, a quality signal: were ``structural`` listed as a familiarity generator,
    M1 would read a count of 2 or 3 as a human familiarity figure and could rescue or reject a word on it (the trap
    of QUESTIONS 58, as for the base model's emission count and the masked LM's contrast score)."""
    from assistant_axis.gapgen.freq import FAMILIARITY_GENERATORS
    assert "structural" not in FAMILIARITY_GENERATORS


# --------------------------------------------------------------------------- the submission

def test_candidates_written_before_the_registry_append_and_resubmit_is_a_noop(world, monkeypatch):
    t = small_table(world)
    seen = {}
    real = SU.submit_candidates

    def spy(cands, **kw):
        p = world["cdir"] / "runs" / "structural" / "r1" / "candidates.jsonl"
        seen["exists"] = p.exists() and len(p.read_text().splitlines()) == len(cands)
        return real(cands, **kw)
    monkeypatch.setattr(SU, "submit_candidates", spy)
    s = SU.run_submit("r1", table=t, all_rows=True, registry_path=world["reg"], candidates_dir=world["cdir"],
                      echo=lambda *_: None)
    assert seen["exists"]
    rdir = world["cdir"] / "runs" / "structural" / "r1"
    for f in ("candidates.jsonl", "keys.txt", "submit_report.json", "run.json", "usage.json"):
        assert (rdir / f).exists(), f
    rep = json.loads((rdir / "submit_report.json").read_text())
    assert rep["rows_submitted"] == len(t) == rep["rows_counted"] + rep["rows_already_filtered"]
    assert rep["n_new"] + rep["n_merged"] == rep["n_submitted"] == len(SU.to_candidates(t, "r1"))
    assert json.loads((rdir / "usage.json").read_text())["n_calls"] == 0
    reg = Registry(world["reg"]).fold()
    assert reg["foolhardy#1"]["sources"][-1]["source_ref"] == "structural:op:excess:brave"
    again = SU.run_submit("r1", table=t, all_rows=True, registry_path=world["reg"], candidates_dir=world["cdir"],
                          echo=lambda *_: None)
    assert again.report["n_new"] == 0 and again.report["n_merged"] == 0
    assert again.report["n_unchanged"] == again.report["n_submitted"]
    assert len((rdir / "candidates.jsonl").read_text().splitlines()) == s.n_candidates


def test_dry_run_leaves_the_registry_byte_identical_and_writes_no_run_dir(world):
    before = world["reg"].read_bytes()
    out = []
    s = SU.run_submit("r2", table=small_table(world), all_rows=True, registry_path=world["reg"],
                      candidates_dir=world["cdir"], dry_run=True, echo=out.append)
    assert world["reg"].read_bytes() == before and not (world["cdir"] / "runs" / "structural" / "r2").exists()
    assert s.dry_run and any("DRY-RUN" in x for x in out)


def test_followups_name_the_run_batch_pipeline_and_transport(world):
    s = SU.run_submit("2026-10-14-b1", table=small_table(world), all_rows=True, registry_path=world["reg"],
                      candidates_dir=world["cdir"], dry_run=True, transport="batches", echo=lambda *_: None)
    text = "\n".join(s.followups)
    for want in ("--run structural/2026-10-14-b1", "--batch-id 2026-10-14-b1_structural", "--pipeline split",
                 "--transport batches", "gap_registry.py submit --from", "novelty_score.py score",
                 "recovery_test.py --generator structural --run-id 2026-10-14-b1",
                 "structural_generator.py report --run-id 2026-10-14-b1"):
        assert want in text, want


def _many(n):
    return [row(f"w{i:05d}", i + 1, [src("brave", "retarget", sub="self")]) | {
        "net_new": True, "registered_decided": False, "registered": False, "exists": False, "queued": False,
        "status": "new", "registered_by": []} for i in range(n)]


def test_cost_guard(world):
    kw = {"registry_path": world["reg"], "candidates_dir": world["cdir"], "dry_run": True, "echo": lambda *_: None}
    with pytest.raises(CostRefused, match="over the \\$20 line"):
        SU.run_submit("big", table=_many(10_000), all_rows=True, budget_usd=500, **kw)
    s = SU.run_submit("big", table=_many(10_000), all_rows=True, budget_usd=200, confirm_expensive=True,
                      confirmed_by="Roger, test", **kw)
    assert s.estimate["total_usd"] > 20
    with pytest.raises(CostRefused, match="exceeds --budget-usd"):
        SU.run_submit("mid", table=_many(2_000), all_rows=True, transport="batches", **kw)       # default $5
    s = SU.run_submit("mid", table=_many(2_000), all_rows=True, transport="batches", budget_usd=20, **kw)
    assert 5 < s.estimate["total_usd"] <= 20


def test_already_filtered_rows_are_counted_out_of_the_estimate(world):
    t = small_table(world)
    s = SU.run_submit("r3", table=t, all_rows=True, registry_path=world["reg"], candidates_dir=world["cdir"],
                      dry_run=True, echo=lambda *_: None)
    decided = sum(1 for r in t if r["registered_decided"])
    assert decided == 1 and s.n_charged == len(t) - decided
    assert s.estimate["n"] == len(t) - decided


def test_kept_target_cut_with_siblings_travelling(world):
    t = small_table(world)
    sel, counted = SU.select_wave(t, kept_target=1, kept_share=1.0)
    # rank 1 craven is net-new; its siblings brave (not a row) and foolhardy (a row, decided) travel with it
    assert [r["stem"] for r in sel] == ["craven", "foolhardy"] and counted == 1
    sel, counted = SU.select_wave(t, kept_target=1, kept_share=1.0, siblings=False)
    assert [r["stem"] for r in sel] == ["craven"]
    with pytest.raises(ValueError):
        SU.select_wave(t, kept_target=1, kept_share=0)


# --------------------------------------------------------------------------- net-new (2026-10-13)

def _chain(world, *, decided: bool):
    """r1 (with r2 as sibling), r3, r4, r5: r3 is another generator's word, decided by M1 and M3 or not."""
    gen_rows = [F.registry_row("dauntless", "censuses")]                    # registered, undecided
    if decided:
        gen_rows.append(F.registry_row("intrepid", "roget", verdict="trait", decision="covered"))
    else:
        gen_rows.append(F.registry_row("intrepid", "roget"))
    F.write_registry(world["reg"], gen_rows)
    return tag([row("gutsy", 1, [src("brave", "excess")], siblings=["nervy"]),
                row("nervy", 2, [src("brave", "deficiency")], siblings=["gutsy"]),
                row("intrepid", 3, [src("timid", "opposite")]),
                row("plucky_ish", 4, [src("gloomy", "remode", sub="habit")]),
                row("dauntless", 5, [src("timid", "excess")]),
                row("stouthearted", 6, [src("timid", "deficiency")])], world)


def test_net_new_cut_counts_out_a_decided_row_and_reaches_one_further(world):
    t = _chain(world, decided=True)
    sel, counted = SU.select_wave(t, kept_target=1, kept_share=0.25)        # 4 net-new rows wanted
    assert [r["stem"] for r in sel] == ["gutsy", "nervy", "intrepid", "plucky_ish", "dauntless"] and counted == 4
    by = {r["stem"]: r for r in t}
    assert by["intrepid"]["registered_decided"] and not by["intrepid"]["net_new"]          # submitted, not counted
    assert by["dauntless"]["registered"] and by["dauntless"]["net_new"]                    # undecided: counted
    t2 = _chain(world, decided=False)
    sel2, counted2 = SU.select_wave(t2, kept_target=1, kept_share=0.25)
    assert [r["stem"] for r in sel2] == ["gutsy", "nervy", "intrepid", "plucky_ish"] and counted2 == 4


def test_net_new_estimate_kept_share_and_submit_report(world):
    t = _chain(world, decided=True)
    s = SU.run_submit("w1", table=t, kept_target=1, kept_share=0.25, registry_path=world["reg"],
                      candidates_dir=world["cdir"], echo=lambda *_: None)
    assert s.n_selected == 5 and s.n_counted == 4 and s.n_filtered == 1 and s.n_charged == 4
    rdir = world["cdir"] / "runs" / "structural" / "w1"
    rep = json.loads((rdir / "submit_report.json").read_text())
    assert (rep["rows_submitted"], rep["rows_counted"], rep["rows_already_filtered"]) == (5, 4, 1)
    args = json.loads((rdir / "run.json").read_text())["args"]
    assert "intrepid" not in args["counted_stems"] and "dauntless" in args["counted_stems"]
    assert args["decided_stems"] == ["intrepid"] and set(args["registered_stems"]) == {"intrepid", "dauntless"}
    # M1 and M3 run on the wave: the measured net-new kept share leaves the decided row out
    reg = Registry(world["reg"])
    for stem, dec in (("gutsy", "new"), ("nervy", "grey"), ("plucky_ish", "covered"), ("dauntless", "new")):
        reg.update(f"{stem}#1", {"filter": {"verdict": "trait"}, "novelty": {"decision": dec}})
    fig = R.figures("w1", run_dir=rdir, registry_rows=reg.fold(), table=t, filter_dir=world["tmp"] / "nf",
                    novelty_dir=world["tmp"] / "nn")
    assert fig["headline"]["already_registered"] == 2 and fig["headline"]["already_decided"] == 1
    assert fig["headline"]["by_another_generator"] == 2 and fig["headline"]["net_new"] == 4
    assert fig["net_new_kept_share"] == 0.75 and fig["kept_net_new"] == 3


def test_net_novel_raw_and_net(world):
    rows = {
        "a#1": F.registry_row("a", "structural", verdict="trait", decision="new", run_id="w1"),
        "b#1": F.registry_row("b", "structural", verdict="trait", decision="new", run_id="w1"),
        "c#1": F.registry_row("c", "structural", verdict="trait", decision="grey", run_id="w1"),
        "d#1": F.registry_row("d", "structural", verdict="trait", decision="covered", run_id="w1"),
        "e#1": F.registry_row("e", "structural", verdict="trait", decision="new", run_id="w1", review="accepted"),
    }
    rows["b#1"]["sources"].append({"generator": "censuses", "run_id": "c1"})          # another generator's twin
    rows["e#1"]["sources"].append({"generator": "ipip", "run_id": "i1"})              # a twin already reviewed
    nv = R.net_novel(list(rows.values()), rows)
    assert nv.raw == 4 and nv.net_pending == 2 and nv.twins_pending == ["b"] and nv.twins_reviewed == ["e"]
    assert nv.net_pending <= nv.raw and nv.net_groups is None
    assert R.net_novel([rows["a#1"]], rows).net_pending == 1                          # no twin: in both


def test_review_rate_hook():
    assert SU.review_terms_per_hour("plan") == (150.0, SU.REVIEW_RATE_SOURCE_PLAN)
    with pytest.raises(ValueError):
        SU.review_terms_per_hour("guess")
    try:
        import assistant_axis.gapgen.testing  # noqa: F401  plan 13's package, once merged
    except ImportError:
        with pytest.raises(SystemExit, match="plan 13"):
            SU.review_terms_per_hour("measured")
