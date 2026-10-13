"""Plan 13 task 5: the dashboard's library (``assistant_axis/gapgen/testing/dashboard.py``): cost attribution
(a ``--run`` batch to its run, a ``--keys`` batch pro rata, an R1 build pro rata by kept rows, the lines summing to
every record read), the stop rule's arithmetic, string recall and negatives, the rows and the Markdown (a generator
with no harness batch prints n/a, never 0; a lagging figure carries its date).  No API calls."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen.testing import dashboard as D
from assistant_axis.gapgen.testing import review_minutes as RM


def usage(d: Path, usd: float, name: str = "usage.json"):
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps({"total_cost_usd": usd, "per_model": {}, "n_calls": 1}))


def src(g, run):
    return {"generator": g, "run_id": run}


ROWS = {"a#1": {"key": "a#1", "stem": "a", "sources": [src("gen1", "r1")]},
        "b#1": {"key": "b#1", "stem": "b", "sources": [src("gen1", "r1"), src("gen2", "r2")]},
        "c#1": {"key": "c#1", "stem": "c", "sources": [src("gen2", "r2")]},
        "d#1": {"key": "d#1", "stem": "d", "sources": [src("states_pass", "st")] and
                [{"generator": "states_pass", "run_id": "st", "source_ref": "c#1"}]}}


def candidates_fixture(tmp_path) -> Path:
    cd = tmp_path / "candidates"
    usage(cd / "runs" / "gen1" / "r1", 1.0)
    usage(cd / "runs" / "gen2" / "r2", 2.0)
    f1 = cd / "filter" / "m1_run"
    usage(f1, 4.0)
    (f1 / "run.json").write_text(json.dumps({"argv": ["--batch-id", "m1_run", "--run", "gen1/r1"]}))
    f2 = cd / "filter" / "m1_keys"
    usage(f2, 3.0)
    (f2 / "run.json").write_text(json.dumps({"argv": ["--keys", "a#1", "c#1", "d#1"]}))
    (f2 / "results.jsonl").write_text("".join(json.dumps({"key": k}) + "\n" for k in ("a#1", "c#1", "d#1")))
    f3 = cd / "filter" / "dev_probe"
    usage(f3, 5.0)
    (f3 / "run.json").write_text(json.dumps({"argv": ["--batch-id", "dev_probe"]}))
    n1 = cd / "novelty" / "m3_run"
    usage(n1, 6.0)
    (n1 / "run.json").write_text(json.dumps({"argv": ["score", "--run", "gen2/r2"]}))
    n2 = cd / "novelty" / "m3_redecided"
    usage(n2, 0.5)
    (n2 / "run.json").write_text(json.dumps({"argv": ["score", "--redecide", "--from-batch", "m3_run"]}))
    n3 = cd / "novelty" / "rec_x_s0"
    usage(n3, 9.0)
    (n3 / "run.json").write_text(json.dumps({"argv": ["score", "--run", "gen1/r1", "--hide", "h.json"], "hide": {}}))
    rv = cd / "review" / "review_all"
    usage(rv, 8.0)
    (rv / "graph.json").write_text(json.dumps({"result": {"nodes": [
        {"key": k, "kind": "candidate", "decision": d} for k, d in (("a#1", "new"), ("b#1", "new"), ("c#1", "covered"),
                                                                   ("d#1", "grey"))]}}))
    rc = cd / "recovery" / "rec_x"
    usage(rc, 10.0)
    (rc / "run.json").write_text(json.dumps({"generator": "gen1", "run_id": "r1"}))
    usage(rc / "seed0", 9.5)                                  # a seed's own file: inside the batch's, not read again
    usage(cd / "calibration", 7.0)                            # names no generator
    return cd


class TestCosts:
    def test_attribution_and_the_sum(self, tmp_path):
        cd = candidates_fixture(tmp_path)
        rep = D.cost_by_run(ROWS, candidates_dir=cd)
        g = rep.by_generator()
        # generator files; M1: m1_run to gen1/r1 (4), m1_keys pro rata over a (gen1), c (gen2), d (via c: gen2) -> 1 + 2
        assert g["gen1"].generator == 1.0 and g["gen2"].generator == 2.0
        assert g["gen1"].m1 == pytest.approx(4.0 + 1.0) and g["gen2"].m1 == pytest.approx(2.0)
        # M3: m3_run to gen2/r2 (6), the re-decided run as its source (0.5); the reduced-corpus run not read
        assert g["gen2"].m3 == pytest.approx(6.5) and g["gen1"].m3 == 0
        # R1 pro rata by kept rows: a (gen1), b (half each), d (gen2 through c) -> gen1 1.5/3, gen2 1.5/3
        assert g["gen1"].r1 == pytest.approx(4.0) and g["gen2"].r1 == pytest.approx(4.0)
        assert g["gen1"].harness == 10.0
        assert set(rep.unattributed) == {"filter/dev_probe/usage.json", "calibration/usage.json"}
        assert rep.total_read == pytest.approx(1 + 2 + 4 + 3 + 5 + 6 + 0.5 + 8 + 10 + 7)
        assert rep.attributed_total() + sum(rep.unattributed.values()) == pytest.approx(rep.total_read)
        assert not any("rec_x_s0" in f["path"] or "seed0" in f["path"] for f in rep.files)

    def test_weights_from_keys(self):
        w = D.weights_from_keys(["a#1", "b#1", "d#1", "zz#1"], ROWS)
        assert w == pytest.approx({("gen1", "r1"): 0.5, ("gen2", "r2"): 0.5})


class TestStopRule:
    def test_the_arithmetic(self):
        """Terms a b c d e: e pre-handled; a b in one proposed group (with an outside term z), d in a group whose other
        member y is another generator's, c in none.  Plan 13 § 6 (as fixed after the review of 2026-10-13): a term in
        any proposed group is grouped, so the grouped terms are a b d (3) and the singleton c (1): minutes
        (1 x 15 + 3 x 25) / 60 = 1.5; the groups {a b}, {d}, {c}: accepted 3 x 0.5.  Blended, at 2 terms and 0.5
        accepted terms a minute: 4 / 2 = 2 minutes, 1 accepted."""
        sr = D.stop_rule(undecided={"a", "b", "c", "d", "e"}, pre_handled={"e", "zz"},
                         proposed_groups=[["a", "b", "z"], ["d", "y"]], singleton_mean_s=15, per_member_s=25,
                         per_group_share=0.5, cost_usd=3.0, terms_per_minute=2.0, accepted_per_minute=0.5)
        assert (sr.undecided_kept, sr.pre_handled, sr.terms, sr.groups) == (5, 1, 4, 3)
        assert (sr.singleton_terms, sr.grouped_terms) == (1, 3)
        assert sr.expected_minutes == 1.5 and sr.expected_accepted == 1.5 and sr.novel_per_review_minute == 1.0
        assert sr.novel_per_usd == 0.5
        assert (sr.blended_minutes, sr.blended_accepted, sr.blended_per_review_minute) == (2.0, 1.0, 0.5)
        assert sr.blended_per_usd == 0.33
        assert D.in_proposed_groups({"a", "c", "d"}, [["a", "b"], ["d", "y"]]) == {"a", "d"}
        none = D.stop_rule(undecided={"a"}, pre_handled=set(), proposed_groups=[], singleton_mean_s=None,
                           per_member_s=None, per_group_share=None, cost_usd=None)
        assert none.expected_minutes is None and none.expected_accepted is None and none.novel_per_usd is None
        assert none.blended_minutes is None and none.blended_accepted is None

    def test_the_blended_rate_of_a_pooled_review(self):
        rate = RM.PooledRate(batches=("b",), active_minutes=84.1, terms=204, terms_per_active_minute=2.43,
                             singleton_mean_s=14.6, per_member_s=25.4, promoted=35)
        assert D.blended_accepted_rate(rate) == pytest.approx(35 / 84.1)
        assert D.blended_accepted_rate(None) is None


class TestStringRecallAndNegatives:
    def test_blind_and_renamed(self):
        t = {"self_aware": NV.CorpusTrait(stem="self_aware", label="self-aware", description="d", negative_label=None,
                                          pair_partner=None, partners=[], expands_to=[], renamed_from=["self_conscious"]),
             "kind": NV.CorpusTrait(stem="kind", label="kind", description="d", negative_label=None, pair_partner=None,
                                    partners=[], expands_to=[], renamed_from=[])}
        names = D.corpus_names(t)
        rows = [{"stem": "selfaware"}, {"stem": "self_conscious"}, {"stem": "unkind"}]
        sr = D.string_recall(rows, names, 2)
        assert sr["n"] == 1 and sr["stems"] == ["self_aware"] and sr["share"] == 0.5
        q = {"entries": [{"stem": "meek", "label": "meek", "status": "not_adopted", "entity_type": "trait"},
                         {"stem": "old_kind", "label": "Kind", "status": "superseded", "entity_type": "trait"},
                         {"stem": "lion", "label": "lion", "status": "not_adopted", "entity_type": "role"},
                         {"stem": "brave", "label": "brave", "status": "candidate", "entity_type": "trait"}]}
        neg = D.negative_names(q, t)
        assert neg == {"meek", "old_kind"}                      # "kind" is a corpus stem; roles and live entries out
        assert D.negative_hits([{"stem": "meek"}, {"stem": "brave"}], neg) == {"hit": 1, "of": 2, "names": ["meek"]}


def graph_fixture():
    nodes = [{"key": k, "kind": "candidate", "decision": "new", "generators": [g], "generator": g, "label": k[0],
              "region": "moral_stance"} for k, g in (("a#1", "gen1"), ("b#1", "gen1"), ("c#1", "gen2"))]
    return {"batch_id": "g", "nodes": nodes, "edges": [{"a": "a#1", "b": "b#1", "strict": False, "proposed": True}],
            "proposed_groups": [["a#1", "b#1"]]}


class TestRowsAndMarkdown:
    def test_rows_for_every_generator_and_n_a(self, tmp_path):
        rows = {k: dict(r, filter={"verdict": "trait", "region": "moral_stance"}, novelty={"decision": "new"})
                for k, r in ROWS.items()}
        rows["b#1"]["review"] = {"status": "accepted"}
        traits = {"a": NV.CorpusTrait(stem="a", label="a", description="d", negative_label=None, pair_partner=None,
                                      partners=[], expands_to=[], renamed_from=[])}
        costs = D.cost_by_run(rows, candidates_dir=candidates_fixture(tmp_path))
        share = RM.PromoteShare(per_term=0.2, per_group=0.5, n_decided=3, borrowed=True, n_groups=1)
        rate = RM.PooledRate(batches=("b",), active_minutes=10.0, terms=20, terms_per_active_minute=2.0,
                             singleton_mean_s=15.0, per_member_s=25.0, promoted=2)
        out = D.build_rows(rows, traits=traits, queue={"entries": []}, graph=graph_fixture(), independence=[],
                           repetition={}, shares={"gen1": share, "gen2": share}, rate=rate, costs=costs, harness=[])
        names = [r.generator for r in out]
        assert set(names) == {"gen1", "gen2", "states_pass"}
        g1 = next(r for r in out if r.generator == "gen1")
        assert g1.candidates == 2 and g1.m3["kept"] == 2 and g1.review["decided"] == 1
        assert g1.string_recall["n"] == 1 and g1.recall["headline"] is None
        assert (g1.stop_rule["pre_handled"], g1.stop_rule["terms"]) == (1, 0)    # b decided; a has a 3-edge to it
        d = {"produced_at": "2026-10-13T00:00:00+00:00", "rows": [r.as_dict() for r in out],
             "inputs": {"registry": "r", "graph_batch": "g", "review_batches": ["review_tda_1"],
                        "review_as_of": "2026-10-11T21:21:26+00:00", "harness_batches": []},
             "costs": {"n_files": 1, "total_read": 1, "attributed": 1, "unattributed": 0}}
        md = D.render_markdown(d)
        line = next(x for x in md.splitlines() if x.startswith("| gen1 |"))
        assert line.count("|") == 17                              # every column rendered
        assert "| n/a |" in line and "| 0 |" not in line.split("|", 12)[-1][:8]   # recall n/a, never 0
        assert "as of 2026-10-11T21:21:26+00:00" in md            # the lagging figures carry their date
        assert "borrowed" in md
        assert "*Blended*" in md


def test_the_frozen_interface():
    """Plan 13, "Frozen interface": the names plans 04 and 09 import."""
    import assistant_axis.gapgen.testing as T
    from assistant_axis.gapgen.testing import (  # noqa: F401
        DASHBOARD_JSON_PATH, GeneratorRow, PromoteShare, ReviewRate, load_dashboard, pooled_review_rate,
        promote_share, review_rate,
    )
    assert set(T.FROZEN_INTERFACE) <= set(T.__all__)
    assert {"batch_id", "active_minutes", "terms_applied", "terms_per_active_minute", "singleton_mean_s",
            "per_member_s", "promoted"} <= set(ReviewRate.__dataclass_fields__)
    assert {"per_term", "per_group", "n_decided", "borrowed"} <= set(PromoteShare.__dataclass_fields__)
    assert DASHBOARD_JSON_PATH.name == "dashboard.json"
