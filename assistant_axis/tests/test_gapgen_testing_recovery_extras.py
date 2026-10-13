"""Plan 13 task 6: the strict column, pair recovery, recall at N and the extras record of a harness batch
(``assistant_axis/gapgen/testing/recovery_extras.py``): a planted batch directory, then the four recorded batches
(``needs_opus`` empty, the hard check of plan 13 § 8).  No API calls."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen.testing import recovery_extras as RX

REPO = Path(__file__).resolve().parents[2]
RECORDED = sorted((REPO / "data" / "candidates" / "recovery").glob("rec_*"))


def m(key, stem, sonnet=None, opus=None, how="overlap", verdict=None, recovers=False, cut_off=3):
    r = {"key": key, "label": key.split("#")[0], "stem": stem, "how": how, "cut_off": cut_off, "recovers": recovers}
    if how == "overlap":
        r |= {"sonnet": {"value": sonnet, "reason": "r"}, "opus": {"value": opus, "reason": "r"} if opus is not None
              else None, "verdict": verdict}
    return r


def planted(tmp_path, *, rules=3, ranks=True):
    cand = tmp_path / "candidates"
    sd = cand / "recovery" / "B" / "seed0"
    sd.mkdir(parents=True)
    hidden = ["alpha", "beta", "gamma", "delta", "eta"]
    (sd / "hidden.json").write_text(json.dumps({"seed": 0, "hidden": hidden, "traits": {
        "alpha": {"region": "moral_stance"}, "beta": {"region": "moral_stance"}, "gamma": {"region": None},
        "delta": {"region": "cognitive_epistemic"}, "eta": {"region": "cognitive_epistemic"}}}))
    rows = [m("a#1", "alpha", 4, 4, verdict="cut", recovers=True),             # recovers at 4
            m("b#1", "beta", 4, None, verdict="cut", recovers=True),           # Sonnet 4 at c = 3: no Opus on record
            m("c#1", "gamma", 3, 3, verdict="cut", recovers=True),             # Sonnet 3, Opus 3: not at 4
            m("d#1", "delta", how="label", recovers=True),                     # a label match: at any cut-off
            m("e#1", "eta", "opposite", verdict="opposite"),                   # pair-recovered
            m("f#1", "eta", "opposite", verdict="opposite"),                   # the same trait again: once
            m("g#1", "alpha", 4, 4, verdict="cut", recovers=True)]             # a covered candidate: not counted
    (sd / "matches.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    nd = cand / "novelty" / "B_s0"
    nd.mkdir(parents=True)
    dec = {"a#1": "new", "b#1": "new", "c#1": "grey", "d#1": "new", "e#1": "new", "f#1": "new", "g#1": "covered"}
    (nd / "results.jsonl").write_text("".join(json.dumps({"key": k, "generators": ["gen"], "novelty": {"decision": d}})
                                              + "\n" for k, d in dec.items()))
    (nd / "run.json").write_text(json.dumps({"rules": NV.RULES[rules].as_dict()}))
    (cand / "recovery" / "B" / "run.json").write_text(json.dumps({"generator": "gen", "run_id": "r1"}))
    rd = cand / "runs" / "gen" / "r1"
    rd.mkdir(parents=True)
    if ranks:
        ranked = [("a", 1), ("b", 2), ("c", 3), ("d", 10), ("e", 11), ("f", 12), ("g", 13), ("h", 14)]
        (rd / "candidates.jsonl").write_text("".join(json.dumps({"surface": s, "generator": "gen", "run_id": "r1",
                                                                 "rank": n, "sense_id": 1}) + "\n" for s, n in ranked))
    return cand / "recovery" / "B", sd


class TestPlanted:
    def test_strict_column(self, tmp_path):
        _, sd = planted(tmp_path)
        st = RX.strict_column(sd)
        assert st.recovered == ["alpha", "delta"] and st.recall == 0.4          # Opus 4 on alpha; delta by label
        assert st.n_recovered_headline == 4                                    # alpha beta gamma delta at the run's
        assert st.lost_at_strict == ["beta", "gamma"]
        assert st.needs_opus == [{"key": "b#1", "stem": "beta", "sonnet": 4, "cut_off": 3}]   # listed, not counted

    def test_pair_recovery(self, tmp_path):
        _, sd = planted(tmp_path)
        pr = RX.pair_recovery(sd)
        assert pr.n_pair_recovered == 1 and pr.stems == ["eta"] and pr.n_also_recovered == 0
        assert pr.by_region["cognitive_epistemic"] == {"n_hidden": 2, "n_pair_recovered": 1}

    def test_recall_at_n(self, tmp_path):
        _, sd = planted(tmp_path)
        pts = RX.recall_at_n(sd, tmp_path / "candidates" / "runs" / "gen" / "r1", quantiles=(0.25, 0.5, 1.0))
        assert [(p["quantile"], p["max_rank"], p["n_recovered"]) for p in pts] == [(0.25, 2, 2), (0.5, 10, 4),
                                                                                    (1.0, 14, 4)]
        assert RX.recall_at_n(sd, tmp_path / "nowhere") == []

    def test_extras_and_contamination(self, tmp_path):
        bd, _ = planted(tmp_path)
        ex = RX.extras_json(bd)
        assert ex["n_needs_opus"] == 1 and ex["seeds"][0]["strict"]["n_recovered"] == 2
        assert ex["seeds"][0]["recall_at_n"][-1]["n_recovered"] == 4
        assert "| 0 | 4 of 5 | 2 of 5 | 2 | 1 | 1 |" in RX.extras_markdown(ex)
        c = RX.contamination({"mean": {"recall_kept": 0.2, "precision_kept": 0.1}},
                             {"mean": {"recall_kept": 0.15, "precision_kept": 0.1}})
        assert c["recall_kept"]["delta"] == -0.05 and c["recall_either"]["delta"] is None


@pytest.mark.skipif(not RECORDED, reason="no recorded harness batch")
class TestRecorded:
    def test_needs_opus_is_empty_on_the_recorded_batches(self):
        """Plan 13 § 8 (hard): the match wave sent every Sonnet reading at c - 1 or above to Opus."""
        assert len(RECORDED) >= 4
        for b in RECORDED:
            ex = RX.extras_json(b)
            assert ex["needs_opus"] == [], b.name
            for s in ex["seeds"]:
                st = s["strict"]
                assert st["n_recovered"] <= st["n_recovered_headline"]
