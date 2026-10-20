"""LLM-entropy generator: selection, the downstream estimate and its gate, and the submission (coding_plan_06 section
8, ``submit``).  A tmp registry through the real frozen API; no network."""
from __future__ import annotations

import json
from collections import Counter

import pytest

from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.freq import FAMILIARITY_GENERATORS, zipf_info
from assistant_axis.gapgen.generators.llm_entropy import submit as SU
from assistant_axis.gapgen.generators.llm_entropy.table import parse_source_ref, rank_rows, source_ref
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests import structural_fakes as SF

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"


def row(stem, *, family="a", model=HAIKU, net_new=True, registered=False, decided=False, n_sources=1, hint=None,
        label_problem=None, order=0, prompt=None, run=1, antonym="zzopposite"):
    pid = prompt or f"{family}:p:{stem}"
    src = {"run_id": "R", "family": family, "prompt_id": pid, "run": run, "stage": 1, "model": model,
           "language": "en", "source_ref": source_ref(pid, run, model), "label": stem.replace("_", " "),
           "gloss": f"This means being {stem}.", "antonym": antonym, "kind": "trait"}
    return {"stem": stem, "label": stem.replace("_", " "), "gloss": f"This means being {stem}.",
            "sources": [dict(src, prompt_id=f"{pid}{i}" if i else pid, run=run + i,
                             source_ref=source_ref(f"{pid}{i}" if i else pid, run + i, model))
                        for i in range(n_sources)],
            "n_sources": n_sources, "primary_family": family, "first_order": order, "pair_completion_hint": hint,
            "label_problem": label_problem, "exists": False, "queued": False, "registered": registered,
            "registered_decided": decided, "registered_by": ["censuses"] if registered else [],
            "net_new": net_new and not decided, "status": "new", "rank": None}


def table(rows):
    return rank_rows([dict(r) for r in rows])


def test_llm_entropy_is_not_a_familiarity_generator():
    # The trap (QUESTIONS 58 and 83, as for base_model and masked_lm): llm_entropy's Candidate.score is n_sources,
    # how many (family, prompt, run) calls produced the stem, a REPETITION COUNT, not a human familiarity in [0, 1].
    # Listed in FAMILIARITY_GENERATORS, a count of 1 would read as a familiarity of 1.0, clear the 0.5 override and
    # rescue every rare word of the run past the Zipf floor; every item here carries a gloss, so the floor's own
    # rescue route 2 (gloss_hint) already sends a rare word to the definition probe.
    assert "llm_entropy" not in FAMILIARITY_GENERATORS, (
        "llm_entropy's score is n_sources, a repetition count, not a familiarity: see the comment above")
    assert not zipf_info("rarish", familiarity=1.0, zipf_fn=lambda w: 1.0).hard_reject       # the trap itself


def test_one_candidate_per_source_with_the_documented_fields():
    rows = table([row("zzsteady", n_sources=3, family="c", prompt="c:de:money", model=SONNET)])
    cands = SU.to_candidates(rows, "R")
    assert len(cands) == 3
    for c in cands:
        assert c.generator == "llm_entropy" and c.run_id == "R" and c.score == 3.0 and c.sense_id == 1
        assert c.partner_hint == "zzopposite" and c.gloss_hint == "This means being zzsteady." and c.rank == 1
        p = parse_source_ref(c.source_ref)
        assert p["family"] == "c" and p["language"] == "de" and p["model_tag"] == "s55"
    assert cands[0].source_ref == "llm_entropy:c:de:money:r1:s55"


def _registry(tmp_path, rows=()):
    return SF.write_registry(tmp_path / "registry.jsonl", list(rows))


def test_submit_writes_candidates_first_then_the_registry_and_resubmits_as_a_no_op(tmp_path, monkeypatch):
    reg = _registry(tmp_path)
    rows = table([row(f"zzw{i}", order=i) for i in range(5)])
    kw = dict(table=rows, registry_rows={}, all_rows=True, registry_path=reg, candidates_dir=tmp_path / "cand",
              relabel=None, echo=lambda *a: None)
    import assistant_axis.gapgen.generators.llm_entropy.submit as mod

    def boom(*a, **k):
        raise RuntimeError("the registry append failed")
    monkeypatch.setattr(mod, "submit_candidates", boom)
    with pytest.raises(RuntimeError):
        SU.run_submit("R", **kw)
    rdir = tmp_path / "cand" / "runs" / "llm_entropy" / "R"
    assert len((rdir / "candidates.jsonl").read_text().splitlines()) == 5     # recorded before the append
    monkeypatch.undo()
    s = SU.run_submit("R", **kw)
    assert s.report["n_new"] == 5 and len(Registry(reg).fold()) == 5
    for f in ("keys.txt", "submit_report.json", "run.json", "usage.json"):
        assert (rdir / f).exists(), f
    s2 = SU.run_submit("R", **kw)
    assert s2.report["n_new"] == 0 and s2.report["n_unchanged"] == 5          # a no-op
    run = json.loads((rdir / "run.json").read_text())
    assert run["sessions"][-1]["args"]["counted_stems"] == [f"zzw{i}" for i in range(5)]


def test_the_cost_guard(tmp_path):
    reg = _registry(tmp_path)
    kw = dict(registry_rows={}, all_rows=True, registry_path=reg, candidates_dir=tmp_path / "cand", relabel=None,
              transport="batches", echo=lambda *a: None)
    big = table([row(f"zz{i}", order=i) for i in range(10_000)])
    with pytest.raises(CostRefused):
        SU.run_submit("R", table=big, budget_usd=100, **kw)                    # over the $20 line, unconfirmed
    s = SU.run_submit("R", table=big, budget_usd=100, confirm_expensive=True, confirmed_by="Roger, test",
                      dry_run=True, **kw)
    assert s.estimate["total_usd"] > 20
    # the plan's 3,000 rows estimate $25 at batch rates, over the $20 line; 1,500 rows ($12.7) are over the default
    # budget and under the line
    mid = table([row(f"zz{i}", order=i) for i in range(1_500)])
    with pytest.raises(CostRefused):
        SU.run_submit("R", table=mid, **kw)
    s = SU.run_submit("R", table=mid, budget_usd=15, dry_run=True, **kw)
    assert 10 < s.estimate["total_usd"] < 15
    assert not (tmp_path / "cand").exists()


def test_rows_the_registry_has_filtered_are_counted_out(tmp_path):
    reg_rows = {f"zzd{i}#1": dict(SF.registry_row(f"zzd{i}", "censuses", verdict="trait", decision="covered"),
                                  novelty={"decision": "covered", "run_id": "m3"}) for i in range(3)}
    reg_rows["zzp#1"] = SF.registry_row("zzp", "censuses", verdict="trait")        # M3 still to come
    rows = table([row(f"zzd{i}", registered=True, decided=True, order=i) for i in range(3)]
                 + [row("zzp", registered=True, order=5), row("zzn", order=6)])
    s = SU.run_submit("R", table=rows, registry_rows=reg_rows, all_rows=True, dry_run=True, echo=lambda *a: None,
                      transport="batches")
    assert s.n_selected == 5 and s.n_counted == 2 and s.n_filtered == 3
    assert s.need == {"n_rows": 5, "n_m1": 1, "n_m3_only": 1, "n_decided": 3, "n_floor_rejected_retaken": 0,
                      "registry_rows": 4}
    e = SU.estimate_downstream_usd(1, transport="batches", n_m3_only=1)
    assert s.estimate["total_usd"] == pytest.approx(e.total_usd)


def test_top_stratifies_by_cell_and_takes_registered_rows_uncounted():
    rows = []
    for fam, model in (("a", HAIKU), ("c", HAIKU), ("c", SONNET)):
        for i in range(6):
            rows.append(row(f"zz{fam}{model[7]}{i}", family=fam, model=model, order=len(rows),
                            registered=(i == 0), decided=(i == 0)))
    t = table(rows)
    sel, counted, per = SU.select_top(t, 9, per_cell=2)
    assert counted == 9 and len(sel) == 9 + 3                       # three decided rows inside the cuts, uncounted
    assert per["a|claude-haiku-5-5"] >= 2 and per["c|claude-sonnet-5-5"] >= 2 and per["c|claude-haiku-5-5"] >= 2
    assert sum(per.values()) == 9
    sel2, counted2, _ = SU.select_top(t, 4)
    assert counted2 == 4 and [r["rank"] for r in sel2] == sorted(r["rank"] for r in sel2)


def test_kept_target_counts_net_new_rows_with_the_round_robin_and_the_pair_premium():
    rows = ([row(f"zza{i}", family="a", order=i) for i in range(10)]
            + [row(f"zze{i}", family="e", order=100 + i) for i in range(10)]
            + [row("zzhint", family="e", order=200, hint="gloomy"), row("zzdone", family="a", order=1.5,
                                                                         registered=True, decided=True)])
    t = table(rows)
    assert t[0]["stem"] == "zzhint"                        # a pair completion outranks an equal n_sources row
    sel, counted = SU.select_wave(t, kept_target=3, kept_share=0.5)     # ceil(3 / 0.5) = 6 net-new rows
    assert counted == 6
    assert [r["primary_family"] for r in sel] == ["e", "a", "e", "a", "e", "a", "e"]   # families in turn
    assert [r["stem"] for r in sel if not r["net_new"]] == ["zzdone"]      # inside the cut, submitted, uncounted
    with pytest.raises(ValueError):
        SU.select_wave(t, kept_target=3, kept_share=0)


def test_mutation_flipping_every_tag_drops_no_row():
    rows = [row(f"zz{i}", order=i, registered=i % 3 == 0, decided=i % 3 == 0) for i in range(30)]
    t = table(rows)
    flipped = []
    for r in t:
        f = dict(r)
        for k in ("exists", "queued", "registered", "registered_decided"):
            f[k] = not f[k]
        f["net_new"] = not (f["exists"] or f["queued"] or f["registered_decided"])
        flipped.append(f)
    a, _ = SU.select_all(t)
    b, _ = SU.select_all(flipped)
    assert [r["stem"] for r in a] == [r["stem"] for r in b]                 # --all: identical
    wa, ca = SU.select_wave(t, kept_target=5, kept_share=0.5)
    wb, cb = SU.select_wave(flipped, kept_target=5, kept_share=0.5)
    assert ca == 10 and cb == 0 and len(wa) == 15 and len(wb) == 30        # only where the cut falls moves
    assert [r["stem"] for r in wa] == [r["stem"] for r in t][:len(wa)]
    assert [r["stem"] for r in wb] == [r["stem"] for r in t][:len(wb)]


def test_label_problems_are_never_submitted():
    t = table([row("zzok", order=0), row("five_words_are_too_many", order=1, label_problem="5 words (at most 4)")])
    assert [r["stem"] for r in SU.select_all(t)[0]] == ["zzok"]


def test_dry_run_leaves_the_registry_byte_identical_and_writes_no_run_dir(tmp_path):
    reg = _registry(tmp_path, [SF.registry_row("zzold", "censuses")])
    before = reg.read_bytes()
    s = SU.run_submit("R", table=table([row("zznew")]), registry_rows={}, all_rows=True, dry_run=True,
                      registry_path=reg, candidates_dir=tmp_path / "cand", echo=lambda *a: None)
    assert reg.read_bytes() == before and not (tmp_path / "cand").exists() and s.dry_run


def test_followups_name_the_run_batch_pipeline_and_transport():
    e = SU.estimate_downstream_usd(500, transport="batches")
    cmds = SU.followup_commands("2026-10-18-pilot", e)
    m1 = next(c for c in cmds if "traithood_filter.py" in c)
    assert "--batch-id 2026-10-18-pilot_llm_entropy" in m1 and "--run llm_entropy/2026-10-18-pilot" in m1
    assert "--pipeline split" in m1 and "--transport batches" in m1
    assert any("novelty_score.py score" in c and "--transport batches" in c for c in cmds)
    assert any("gap_registry.py submit --from" in c for c in cmds)


def test_rows_of_run_keeps_only_the_runs_sources():
    r = row("zzx", n_sources=2)
    r["sources"][1]["run_id"] = "other"
    (only,) = SU.rows_of_run([r], "R")
    assert len(only["sources"]) == 1 and only["n_sources"] == 2
    assert SU.rows_of_run([r], "nobody") == []


def test_record_only_writes_the_candidates_and_not_the_registry(tmp_path):
    reg = _registry(tmp_path, [SF.registry_row("zzold", "censuses")])
    before = reg.read_bytes()
    s = SU.run_submit("R", table=table([row("zznew"), row("zzalso", order=1)]), registry_rows={}, all_rows=True,
                      registry_path=reg, candidates_dir=tmp_path / "cand", record_only=True, relabel=None,
                      echo=lambda *a: None)
    rdir = tmp_path / "cand" / "runs" / "llm_entropy" / "R"
    assert reg.read_bytes() == before and (rdir / "candidates.jsonl").exists() and not (rdir / "keys.txt").exists()
    assert "label_fit.py check --run llm_entropy/R" in s.followups[0]
    assert json.loads((rdir / "run.json").read_text())["sessions"][-1]["args"]["record_only"] is True


# --------------------------------------------------------------------------- the wave's family mix (QUESTIONS 208)

def test_family_weights_parse_and_default():
    assert SU.parse_family_weights("a=4,b=2,d=1.5,e=1,c=1") == {"a": 4.0, "b": 2.0, "d": 1.5, "e": 1.0, "c": 1.0}
    assert dict(SU.FAMILY_WEIGHTS_DEFAULT) == {"a": 4.0, "b": 2.0, "d": 1.5, "e": 1.0, "c": 1.0}   # Roger's ratio
    assert SU.parse_family_weights("none") is None and SU.parse_family_weights(None) is None
    assert SU.format_family_weights(SU.FAMILY_WEIGHTS_DEFAULT) == "a=4 b=2 d=1.5 e=1 c=1"
    for bad in ("a=4,z=1", "a=-1", "a=x", "a=0,b=0", "a=1,a=2", "a4"):
        with pytest.raises(ValueError):
            SU.parse_family_weights(bad)


def test_largest_remainder_split():
    w = {"a": 4.0, "b": 2.0, "d": 1.5, "e": 1.0, "c": 1.0}
    # 100 / 9.5: quotas a 42.1, b 21.05, d 15.79, e 10.53, c 10.53; floors 98, the two largest remainders (d .79,
    # e .53 vs c .53: equal remainders go to the larger weight, then the order given) take one more
    assert SU.largest_remainder(100, w) == {"a": 42, "b": 21, "d": 16, "e": 11, "c": 10}
    assert sum(SU.largest_remainder(857, w).values()) == 857
    assert SU.largest_remainder(0, w) == {f: 0 for f in w}
    assert SU.largest_remainder(5, {"a": 1.0, "b": 0.0}) == {"a": 5, "b": 0}


def test_a_short_family_gives_its_remainder_to_the_others_in_proportion():
    w = {"a": 4.0, "b": 2.0, "d": 1.5, "e": 1.0, "c": 1.0}
    s = SU.split_by_weights(95, w, {"a": 1000, "b": 1000, "d": 1000, "e": 1000, "c": 3})
    assert s["share"] == {"a": 40, "b": 20, "d": 15, "e": 10, "c": 10}
    assert s["short"] == {"c": 7} and s["unfilled"] == 0
    # c takes its 3; the other 92 go to a, b, d, e as 4 : 2 : 1.5 : 1 (8.5): 43.3, 21.6, 16.2, 10.8
    assert s["allocated"] == {"a": 43, "b": 22, "d": 16, "e": 11, "c": 3}
    assert sum(s["allocated"].values()) == 95
    # a cascade: b short too after c's share moved; everything left over goes on in proportion
    s2 = SU.split_by_weights(95, w, {"a": 1000, "b": 21, "d": 1000, "e": 1000, "c": 3})
    assert s2["allocated"]["c"] == 3 and s2["allocated"]["b"] == 21 and sum(s2["allocated"].values()) == 95
    # every family out of rows: what is left is unfilled
    s3 = SU.split_by_weights(95, w, {"a": 5, "b": 5, "d": 5, "e": 5, "c": 5})
    assert s3["allocated"] == {f: 5 for f in w} and s3["unfilled"] == 70


def _wave_table():
    rows = []
    for fam, n in (("a", 30), ("b", 30), ("c", 2), ("d", 30), ("e", 30)):
        for i in range(n):
            rows.append(row(f"zz{fam}{i}", family=fam, order=len(rows)))
    rows.append(row("zzadone", family="a", order=0.5, registered=True, decided=True))
    return table(rows)


def test_the_wave_is_split_by_family_with_the_default_weights():
    t = _wave_table()
    sel, counted, split = SU.select_wave_by_family(t, kept_target=19, kept_share=0.5)    # 38 net-new rows
    assert split["need"] == 38 and counted == 38
    # 38 / 9.5 = 4 per weight unit: a 16, b 8, d 6, e 4, c 4; c has 2, its 2 go to a, b, d, e as 4 : 2 : 1.5 : 1
    assert split["share"] == {"a": 16, "b": 8, "d": 6, "e": 4, "c": 4} and split["short"] == {"c": 2}
    assert split["allocated"] == {"a": 17, "b": 9, "d": 6, "e": 4, "c": 2}
    assert split["taken"] == split["allocated"]
    fams = Counter(r["primary_family"] for r in sel if r["net_new"])
    assert dict(fams) == {"a": 17, "b": 9, "d": 6, "e": 4, "c": 2}
    # each family's own rows in rank order; the decided row inside a's cut is submitted, uncounted
    for f in "abcde":
        mine = [r["rank"] for r in t if r["primary_family"] == f and r["net_new"]]
        assert [r["rank"] for r in sel if r["primary_family"] == f and r["net_new"]] == mine[:fams[f]]
    assert [r["stem"] for r in sel if not r["net_new"]] == ["zzadone"]
    assert [r["rank"] for r in sel] == sorted(r["rank"] for r in sel)


def test_run_submit_defaults_to_the_family_weights_prints_and_records_the_split(tmp_path):
    reg = _registry(tmp_path)
    lines = []
    s = SU.run_submit("R", table=_wave_table(), registry_rows={}, kept_target=19, kept_share=0.5,
                      registry_path=reg, candidates_dir=tmp_path / "cand", relabel=None, echo=lines.append)
    assert s.family_split["allocated"] == {"a": 17, "b": 9, "d": 6, "e": 4, "c": 2}
    assert "families weighted a=4 b=2 d=1.5 e=1 c=1" in s.mode
    text = "\n".join(lines)
    assert "family weights a=4 b=2 d=1.5 e=1 c=1 (the default: QUESTIONS 208" in text
    assert "a 17 (share 16, available 30)" in text and "c by 2" in text
    rdir = tmp_path / "cand" / "runs" / "llm_entropy" / "R"
    rep = json.loads((rdir / "submit_report.json").read_text())
    assert rep["family_split"]["allocated"]["a"] == 17 and rep["rows_counted"] == 38
    assert json.loads((rdir / "run.json").read_text())["sessions"][-1]["args"]["family_split"]["short"] == {"c": 2}
    # None: the plain rank order, as before
    s0 = SU.run_submit("R", table=_wave_table(), registry_rows={}, kept_target=19, kept_share=0.5, dry_run=True,
                       family_weights=None, echo=lambda *a: None, candidates_dir=tmp_path / "c2")
    assert s0.family_split is None and s0.n_counted == 38 and "plain rank order" in s0.mode
