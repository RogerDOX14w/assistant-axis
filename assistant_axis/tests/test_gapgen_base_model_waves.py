"""Base-model generator, plan 03 decision (f) (Roger, 2026-10-13; built 2026-10-14): count no longer orders the
waves.  The first wave draws its net-new rows evenly across the count-bucket x family cells, later waves from the
cell with the best measured new-kept rate down; tmp registry and run dirs, no calls."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.cost import CostRefused
from assistant_axis.gapgen.generators.base_model import evaluate as EV
from assistant_axis.gapgen.generators.base_model import report as RP
from assistant_axis.gapgen.generators.base_model import submit as SB
from assistant_axis.gapgen.generators.base_model import waves as W
from assistant_axis.gapgen.generators.base_model.prompts import FAMILIES
from assistant_axis.gapgen.registry import Registry

BUCKET_COUNTS = {"2": (2,), "3": (3,), "4-9": (4, 6, 9), "10+": (10, 25, 400)}


def row(stem, count, families, rank):
    return {"surface": stem, "stem": stem, "eligible": True, "count": count, "rank": rank, "gloss_hint": None,
            "partner_seed": None, "first_sample_id": f"R1-{rank:06d}", "first_family": next(iter(families)),
            "families": dict(families), "form": "adjective"}


def grid_table(per_cell=30, short=None):
    """``per_cell`` single-family rows in every cell (``short``: ``{cell: n}`` overrides), counts varied inside the
    bucket so that a count order would be visible."""
    rows, rank = [], 0
    for b, counts in BUCKET_COUNTS.items():
        for f in FAMILIES:
            n = (short or {}).get(f"{b}|{f}", per_cell)
            for i in range(n):
                rank += 1
                c = counts[i % len(counts)]
                rows.append(row(f"{f}_{b.replace('+', 'p').replace('-', '_')}_{i}", c, {f: c}, rank))
    return rows


def run_wave(tmp_path, table, run_id="w1", **kw):
    kw.setdefault("echo", lambda *a: None)
    kw.setdefault("budget_usd", 50.0)
    kw.setdefault("confirm_expensive", True)
    kw.setdefault("confirmed_by", "Roger, test")
    return SB.run_submit(run_id, table=table, round_n=1, registry_path=tmp_path / "registry.jsonl",
                         candidates_dir=tmp_path, wave=True, corpus_stems=kw.pop("corpus_stems", ()),
                         queue_stems=kw.pop("queue_stems", ()), **kw)


# ---------------------------------------------------------------------------- cells

def test_count_buckets():
    assert [W.count_bucket(c) for c in (1, 2, 3, 4, 9, 10, 5000)] == ["1", "2", "3", "4-9", "4-9", "10+", "10+"]
    cells = W.all_cells(2)
    assert len(cells) == 24 and cells[0] == "2|list" and cells[-1] == "10+|ai_assistant"
    assert len(W.all_cells(1)) == 30 and len(W.all_cells(2, families=("list", "person"))) == 8


def test_the_home_family_rule():
    totals = {"list": 1000, "person": 800, "contrast": 50, "occupation": 50}
    # the family that emitted the row most often
    assert W.home_family(row("a", 5, {"list": 4, "contrast": 1}, 1), totals) == "list"
    # a tie goes to the family with the fewest emissions over the table
    assert W.home_family(row("b", 2, {"list": 1, "contrast": 1}, 2), totals) == "contrast"
    assert W.home_family(row("c", 2, {"person": 1, "list": 1}, 3), totals) == "person"
    # equal totals: the order of prompts.FAMILIES (contrast before occupation)
    assert W.home_family(row("d", 2, {"occupation": 1, "contrast": 1}, 4), totals) == "contrast"
    # --families limits the choice
    assert W.home_family(row("e", 5, {"list": 4, "person": 1}, 5), totals, allowed=("person",)) == "person"
    assert W.cell_of(row("f", 7, {"list": 4, "contrast": 3}, 6), totals) == "4-9|list"
    assert W.family_totals([row("x", 3, {"list": 2, "person": 1}, 1), row("y", 2, {"list": 2}, 2)]) == \
        {"list": 4, "person": 1}


# ---------------------------------------------------------------------------- quotas

def test_even_quotas_spread_evenly():
    pools = {f"c{i}": 100 for i in range(24)}
    q = W.even_quotas(pools, 883, seed=0)
    assert sum(q.values()) == 883 and max(q.values()) - min(q.values()) <= 1


def test_a_short_cell_gives_its_quota_to_the_others():
    pools = {"a": 5, "b": 100, "c": 100, "d": 0}
    q = W.even_quotas(pools, 90, seed=0)
    assert q == {"a": 5, "b": 43, "c": 42, "d": 0} or q == {"a": 5, "b": 42, "c": 43, "d": 0}
    assert sum(q.values()) == 90
    # more wanted than there is: every pool is taken, and no more
    assert W.even_quotas(pools, 1000) == {"a": 5, "b": 100, "c": 100, "d": 0}


def test_the_remainder_goes_in_a_seeded_order():
    pools = {f"c{i}": 10 for i in range(6)}
    q0, q1 = W.even_quotas(pools, 9, seed=0), W.even_quotas(pools, 9, seed=0)
    assert q0 == q1 and sorted(q0.values()) == [1, 1, 1, 2, 2, 2]
    assert any(W.even_quotas(pools, 9, seed=s) != q0 for s in range(1, 20))


# ---------------------------------------------------------------------------- the first wave

def test_the_first_wave_is_stratified_and_even(tmp_path):
    summ = run_wave(tmp_path, grid_table(), kept_target=150, kept_share=0.5, dry_run=True)
    sel = summ.selection
    assert sel["mode"] == "wave" and sel["order"] == "stratified" and sel["need"] == 300
    quotas = [c["quota"] for c in sel["cells"].values()]
    assert len(quotas) == 24 and sum(quotas) == 300 and max(quotas) - min(quotas) <= 1
    assert sel["n_counted"] == 300 and sel["kept_share"] == 0.5 and sel["kept_share_assumed"] is False


def test_short_cells_are_redistributed(tmp_path):
    short = {"10+|contrast": 0, "3|contrast": 4, "4-9|contrast": 2}
    sel = run_wave(tmp_path, grid_table(short=short), kept_target=200, kept_share=0.5, dry_run=True).selection
    cells = sel["cells"]
    assert cells["10+|contrast"]["quota"] == 0 and cells["3|contrast"]["quota"] == 4
    assert cells["4-9|contrast"]["quota"] == 2
    others = [v["quota"] for c, v in cells.items() if c not in short]
    assert sum(others) == 400 - 6 and max(others) - min(others) <= 1


def test_the_default_kept_share_is_the_pilots_and_printed_as_assumed(tmp_path):
    out = []
    summ = run_wave(tmp_path, grid_table(), dry_run=True, echo=out.append)
    sel = summ.selection
    assert sel["kept_share"] == W.KEPT_SHARE_PILOT == 0.34 and sel["kept_share_assumed"] is True
    assert sel["kept_target"] == 300 and sel["need"] == 883
    text = "\n".join(out)
    assert "kept share ASSUMED" in text and "order: stratified (the default: no wave on record)" in text
    assert "2|list" in text and "expected kept" in text and "10+|ai_assistant" in text


def test_the_net_new_filter(tmp_path):
    table = [row("fresh", 2, {"list": 2}, 1), row("corpus_word", 2, {"list": 2}, 2),
             row("queued_word", 3, {"person": 3}, 3), row("decided_word", 2, {"list": 2}, 4),
             row("pending_word", 2, {"list": 2}, 5), row("floor_rejected", 4, {"contrast": 4}, 6),
             row("corpus_decided", 5, {"list": 5}, 7), row("renamed_old", 2, {"list": 2}, 8)]
    reg = {"decided_word#1": {"stem": "decided_word", "filter": {"verdict": "reject"}},
           "pending_word#1": {"stem": "pending_word", "filter": {"verdict": "trait"}},     # M3 still to run
           "floor_rejected#1": {"stem": "floor_rejected", "filter": {"verdict": "reject", "rule": "floor"}},
           "corpus_decided#1": {"stem": "corpus_decided", "filter": {"verdict": "trait"},
                                "novelty": {"decision": "covered", "run_id": "b"}}}
    summ = run_wave(tmp_path, table, registry_rows=reg, corpus_stems={"corpus_word", "corpus_decided"},
                    queue_stems={"queued_word"}, renamed={"renamed_old": "corpus_word"}, dry_run=True)
    sel = summ.selection
    assert set(sel["counted"]) == {"fresh", "pending_word", "floor_rejected"}
    # decided rows ride along free; corpus and queue matches ride along too, decided or not (QUESTIONS 82, Roger
    # 2026-10-14: "Yes"; until then the undecided ones were left out)
    assert sel["ride_along"] == ["corpus_decided", "corpus_word", "decided_word", "queued_word", "renamed_old"]
    assert sel["left_out"] == {}
    assert sel["status_counts"] == {"decided": 1, "exists": 3, "net_new": 3, "queued": 1}
    assert summ.n_selected == 8
    # the decided rows cost nothing; the undecided corpus and queue matches are charged like the counted rows
    assert summ.need["n_decided"] == 2 and summ.need["n_m1"] + summ.need["n_m3_only"] == 6
    # --no-ride-along leaves them all out
    sel2 = run_wave(tmp_path, table, registry_rows=reg, corpus_stems={"corpus_word", "corpus_decided"},
                    queue_stems={"queued_word"}, ride_along=False, dry_run=True).selection
    assert sel2["ride_along"] == [] and sel2["left_out"]["ride_along_off"] == 4      # no renamed map here


def test_the_selection_is_deterministic_by_seed_and_never_ordered_by_count(tmp_path):
    table = grid_table()
    a = run_wave(tmp_path, table, kept_target=60, kept_share=0.5, dry_run=True).selection
    b = run_wave(tmp_path, list(reversed(table)), kept_target=60, kept_share=0.5, dry_run=True).selection
    assert a["counted"] == b["counted"]                       # the input order does not matter
    c = run_wave(tmp_path, table, kept_target=60, kept_share=0.5, wave_seed=7, dry_run=True).selection
    assert set(c["counted"]) != set(a["counted"]) and c["seed"] == 7
    # within a cell, the seeded shuffle and nothing else: the 10+ list cell's 5 rows are its first 5 by hash
    pool = sorted((r for r in table if r["stem"].startswith("list_10p_")), key=lambda r: W.shuffle_key(0, r["stem"]))
    picked = {s for s, cell in a["counted"].items() if cell == "10+|list"}
    assert picked == {r["stem"] for r in pool[:len(picked)]}
    by_count = sorted(pool, key=lambda r: -r["count"])[:len(picked)]
    assert picked != {r["stem"] for r in by_count}            # a count order would have picked others


def test_a_multi_family_row_is_counted_once_in_its_home_cell(tmp_path):
    table = grid_table(per_cell=3)
    table.append(row("shared", 4, {"list": 3, "contrast": 1}, 9999))
    table.append(row("tied", 2, {"list": 1, "contrast": 1}, 10000))
    sel = run_wave(tmp_path, table, kept_target=1000, kept_share=1.0, dry_run=True).selection
    assert sel["counted"]["shared"] == "4-9|list" and sel["counted"]["tied"] == "2|contrast"
    assert sum(v["net_new"] for v in sel["cells"].values()) == len(table)


# ---------------------------------------------------------------------------- run.json and the gate

def test_run_json_records_the_selection(tmp_path):
    summ = run_wave(tmp_path, grid_table(per_cell=5), kept_target=30, kept_share=0.5)
    d = tmp_path / "runs" / "base_model" / "w1"
    sel = json.loads((d / "run.json").read_text())["args"]["selection"]
    assert sel == summ.selection
    assert sel["order"] == "stratified" and sel["seed"] == 0 and sel["kept_share"] == 0.5
    assert sel["kept_share_assumed"] is False and sel["home_family_rule"] == W.HOME_FAMILY_RULE
    assert sel["count_buckets"] == ["2", "3", "4-9", "10+"] and sum(c["quota"] for c in sel["cells"].values()) == 60
    keys = set((d / "keys.txt").read_text().split())
    assert keys == {f"{s}#1" for s in sel["counted"]}
    assert json.loads((d / "submit_report.json").read_text())["wave"]["n_counted"] == 60


def test_the_dry_run_leaves_the_registry_byte_identical(tmp_path):
    reg = tmp_path / "registry.jsonl"
    reg.write_text('{"key": "x#1", "stem": "x"}\n')
    before = reg.read_bytes()
    summ = run_wave(tmp_path, grid_table(), dry_run=True)
    assert summ.dry_run and summ.run_dir is None
    assert reg.read_bytes() == before and not (tmp_path / "runs").exists()


def test_the_20_dollar_gate(tmp_path):
    # 3,000 rows wanted at kept share 0.1 from a pool of 24 x 200: $48 live, over the $20 line
    table = grid_table(per_cell=200)
    kw = {"kept_target": 300, "kept_share": 0.1, "dry_run": True}
    with pytest.raises(CostRefused):
        run_wave(tmp_path, table, budget_usd=60, confirm_expensive=False, confirmed_by=None, **kw)
    with pytest.raises(CostRefused):
        run_wave(tmp_path, table, budget_usd=15, **kw)                         # over the cap
    assert run_wave(tmp_path, table, budget_usd=60, **kw).estimate["total_usd"] == pytest.approx(48.0)
    # the review-hour wave at the defaults stays under the line
    assert run_wave(tmp_path, table, budget_usd=15, confirm_expensive=False, confirmed_by=None,
                    dry_run=True).estimate["total_usd"] < 15


# ---------------------------------------------------------------------------- later waves

def plant(reg_path: Path, outcomes: dict):
    """M1 and M3 results on registry rows: ``{stem: "kept" | "dropped" | "rejected"}``."""
    r = Registry(reg_path)
    for stem, o in outcomes.items():
        if o == "rejected":
            r.merge_block(f"{stem}#1", "filter", {"verdict": "reject", "model": "m"}, replace=True)
            continue
        r.merge_block(f"{stem}#1", "filter", {"verdict": "trait", "model": "m"}, replace=True)
        r.merge_block(f"{stem}#1", "novelty", {"decision": "new" if o == "kept" else "covered", "run_id": "b"},
                      replace=True)


def test_measured_is_refused_with_nothing_on_record(tmp_path):
    table = grid_table(per_cell=5)
    with pytest.raises(W.NothingMeasured) as exc:
        run_wave(tmp_path, table, order="measured", dry_run=True)
    assert "no wave on record" in str(exc.value) and "--order stratified" in str(exc.value)
    run_wave(tmp_path, table, kept_target=30, kept_share=0.5)                   # a wave, not yet judged
    with pytest.raises(W.NothingMeasured) as exc:
        run_wave(tmp_path, table, run_id="w2", order="measured", dry_run=True)
    assert "w1" in str(exc.value) and "run their M1 and M3 first" in str(exc.value)
    # and the default stays stratified until something is decided, drawing nothing w1 drew
    out = []
    s2 = run_wave(tmp_path, table, run_id="w2", kept_target=30, kept_share=0.5, dry_run=True, echo=out.append)
    assert s2.selection["order"] == "stratified" and "have no rows M1 and M3 have decided yet" in "\n".join(out)
    w1 = json.loads((tmp_path / "runs" / "base_model" / "w1" / "run.json").read_text())["args"]["selection"]
    assert not set(s2.selection["counted"]) & set(w1["counted"])


def test_measured_fills_from_the_best_cell_down(tmp_path):
    table = grid_table(per_cell=30)
    reg = tmp_path / "registry.jsonl"
    w1 = run_wave(tmp_path, table, kept_target=120, kept_share=0.5).selection        # 10 rows a cell
    cells = {}
    for stem, cell in w1["counted"].items():
        cells.setdefault(cell, []).append(stem)
    assert all(len(v) == 10 for v in cells.values())
    # plant: 3|person keeps 9 of 10, 2|list 6 of 10, every other cell 1 of 10; 10+|list only 2 decided (both kept)
    outcomes = {}
    for cell, stems in cells.items():
        k = {"3|person": 9, "2|list": 6}.get(cell, 1)
        for i, s in enumerate(stems):
            outcomes[s] = "kept" if i < k else ("rejected" if i % 2 else "dropped")
    for s in cells["10+|list"][2:]:
        outcomes.pop(s)
    outcomes.update({s: "kept" for s in cells["10+|list"][:2]})
    plant(reg, outcomes)
    out = []
    s2 = run_wave(tmp_path, table, run_id="w2", kept_target=15, kept_share=0.5, dry_run=True, echo=out.append)
    sel = s2.selection
    assert sel["order"] == "measured" and "order: measured (the default" in "\n".join(out)
    q = {c: v["quota"] for c, v in sel["cells"].items() if v["quota"]}
    # 30 rows wanted: the best cell's 20 remaining rows, then 10 from the next
    assert q == {"3|person": 20, "2|list": 10}
    # 10+|list (2 of 2 kept) is ranked at the pooled rate, not first
    assert sel["cells"]["10+|list"]["rate_source"].startswith("pooled rate")
    assert sel["cells"]["3|person"]["rate"] == 0.9 and sel["cells"]["2|list"]["rate"] == 0.6
    assert sel["measured_from"] == ["w1"] and not set(sel["counted"]) & set(w1["counted"])
    # with enough decided, the kept share defaults to the waves' pooled measure, no longer assumed
    m = W.measure_cells(W.load_waves(tmp_path / "runs" / "base_model"), W.registry_by_stem(Registry(reg).fold()))
    s3 = run_wave(tmp_path, table, run_id="w2", kept_target=15, dry_run=True).selection
    assert s3["kept_share"] == m["pooled"]["rate"] and s3["kept_share_assumed"] is False
    assert s3["kept_share_source"].startswith("measured over the waves w1")
    assert m["cells"]["10+|list"]["n_pending"] == 8 and m["pooled"]["n_submitted"] == 240


def test_the_report_gives_the_per_cell_rate(tmp_path):
    table = grid_table(per_cell=4)
    reg = tmp_path / "registry.jsonl"
    w1 = run_wave(tmp_path, table, kept_target=96, kept_share=1.0).selection
    rd = tmp_path / "runs" / "base_model" / "w1"
    folded = Registry(reg).fold()
    assert EV.wave_rates("w1", run_dir=rd, registry_rows=folded)["this_wave"]["pooled"]["n_decided"] == 0
    stems = sorted(w1["counted"])
    plant(reg, {s: ("kept" if i % 2 else "dropped") for i, s in enumerate(stems[:20])})
    folded = Registry(reg).fold()
    wr = EV.wave_rates("w1", run_dir=rd, registry_rows=folded)
    assert wr["this_wave"]["pooled"] == {"n_submitted": 96, "n_decided": 20, "n_m1_trait": 20, "n_kept": 10,
                                         "n_dropped": 10, "n_pending": 76, "rate": 0.5}
    md = "\n".join(RP._waves_section({"waves": wr}))
    assert "## Waves: the measured new-kept rate per cell" in md and "| **all cells** | 96 | 20 | 20 | 10 | 76 |" in md
    assert EV.wave_rates("nope", run_dir=tmp_path / "runs" / "base_model" / "nope", registry_rows=folded) is None
