"""Plan 13 task 2: review-minutes, terms decided, group times, the review rate and the promote share
(``assistant_axis/gapgen/testing/review_minutes.py``).  A fixture log, then the recorded ``review_tda_1`` (the hard
figures of plan 13 § 8).  No API calls."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.testing import review_minutes as RM

REPO = Path(__file__).resolve().parents[2]
TDA = REPO / "data" / "candidates" / "review" / "review_tda_1"


def ev(seq, at, action, group="g1", **kw):
    return {"seq": seq, "at": f"2026-10-11T10:{at}+00:00", "by": "roger", "group": group, "action": action, **kw}


def write_log(d: Path, events, applied=None, superseded=False):
    d.mkdir(parents=True, exist_ok=True)
    (d / "decisions.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    if applied is not None:
        (d / "applied.jsonl").write_text("".join(json.dumps(a) + "\n" for a in applied))
    if superseded:
        (d / "decisions.before_leftovers_2026-10-11.jsonl").write_text(json.dumps(ev(1, "00:00", "open")) + "\n")
    return d


FIXTURE = [ev(1, "00:00", "open", members=["a#1"]),                                       # a singleton
           ev(2, "00:10", "resolve", members=["a#1"], resolution="promote"),
           ev(3, "00:20", "open", group="g2", members=["b#1", "c#1", "d#1"]),             # a group of three
           ev(4, "01:20", "resolve", group="g2", members=["b#1", "c#1", "d#1"], resolution="merge_into:trait:x"),
           ev(5, "01:30", "distinct", group="g2", keys=["e#1"]),
           ev(6, "20:00", "open", group="g3", members=["f#1"]),                           # after an 18.5-minute break
           ev(7, "20:30", "resolve", group="g3", members=["f#1"], resolution="reject"),
           ev(8, "20:40", "open", group="g4", members=["g#1"]),
           ev(9, "20:44", "resolve", group="g4", members=["g#1"], resolution="promote"),
           ev(10, "20:50", "undo", group="g4", undoes=9, undone_action="resolve"),
           ev(11, "20:56", "resolve", group="g4", members=["g#1"], resolution="merge_into:trait:y")]


class TestFixture:
    def test_active_minutes_exclude_the_break(self, tmp_path):
        d = write_log(tmp_path / "b1", FIXTURE)
        all_ev = RM.load_events(d, drop_undone=False)
        assert len(all_ev) == 11 and len(RM.load_events(d)) == 9                  # undo and the undone resolve out
        # gaps 10, 10, 60, 10 | 1110 (a break) | 30, 10, 4, 6, 6 seconds
        assert RM.active_minutes(all_ev) == pytest.approx(146 / 60)
        assert RM.wall_minutes(all_ev) == pytest.approx(1256 / 60)
        assert RM.idle_gaps(all_ev) == 1
        assert RM.active_minutes(all_ev, idle_s=2000) == pytest.approx(1256 / 60)

    def test_terms_decided_from_applied_and_the_log(self, tmp_path):
        d = write_log(tmp_path / "b1", FIXTURE, applied=[{"dry_run": True, "review_writes": 99, "promoted": []},
                                                          {"review_writes": 6, "promoted": ["a#1"]}])
        td = RM.terms_decided(d)
        assert td.applied == 6 and td.promoted == 1                               # the dry run's record skipped
        assert td.from_log == 7                                                   # a b c d e f g
        assert RM.terms_decided(write_log(tmp_path / "b2", FIXTURE)).applied is None

    def test_group_times_from_open_to_open_spans(self, tmp_path):
        d = write_log(tmp_path / "b1", FIXTURE)
        gt = RM.group_times(RM.load_events(d))
        # spans: a 20 s (singleton), b-c-d 1180 s with the break (left out), f 40 s, g 16 s (to the last event)
        assert gt.n_groups == 4 and gt.n_singletons == 3 and gt.n_left_out == 1
        assert gt.singleton_median_s == 20 and gt.singleton_mean_s == pytest.approx(76 / 3)
        assert gt.per_member_s is None                                            # the only multi span had a break

    def test_the_record_and_the_superseded_log(self, tmp_path):
        d = write_log(tmp_path / "rev_x", FIXTURE, applied=[{"review_writes": 6, "promoted": ["a#1"]}],
                      superseded=True)
        rec = RM.review_record(d)
        assert rec["events"] == 11 and rec["undone"] == 2 and rec["superseded_logs"] == [
            "decisions.before_leftovers_2026-10-11.jsonl"]
        assert rec["groups"]["opened"] == 4 and rec["groups"]["resolved"] == 4
        assert rec["groups"]["resolutions"] == {"merge_into": 2, "promote": 1, "reject": 1}
        assert rec["active_minutes"] == 2.4 and rec["rate"]["terms_per_active_minute"] == 2.5     # 6 / 2.4
        assert rec["pooled"] is False                                             # 6 terms: too small to pool
        r = RM.review_rate(d)
        assert r.batch_id == "rev_x" and r.terms_applied == 6 and r.promoted == 1


def row(key, gen, status=None, decision="new"):
    return {"key": key, "sources": [{"generator": gen, "run_id": "r"}], "novelty": {"decision": decision},
            "review": {"status": status} if status else {}}


class TestPromoteShare:
    def test_per_term_and_per_group(self, tmp_path):
        rows = {"a#1": row("a#1", "censuses", "accepted"), "b#1": row("b#1", "censuses", "merged_into"),
                "c#1": row("c#1", "censuses", "merged_into"), "d#1": row("d#1", "censuses", "merged_into"),
                "f#1": row("f#1", "ipip", "rejected"), "g#1": row("g#1", "ipip", "merged_into"),
                "h#1": row("h#1", "censuses", "merged_into", decision="covered")}   # pulled in: not a term
        d = write_log(tmp_path / "b1", FIXTURE)
        res = RM.load_resolutions([d])
        assert [(r.group, r.kind, len(r.members)) for r in res] == [("g1", "promote", 1), ("g2", "merge_into", 3),
                                                                    ("g3", "reject", 1), ("g4", "merge_into", 1)]
        pooled = RM.pooled_promote_share(rows, res)
        assert pooled.per_group == 0.25 and pooled.n_groups == 4                  # 1 promote of 4 groups
        assert pooled.per_term == pytest.approx(1 / 6, abs=1e-4) and pooled.n_decided == 6
        assert pooled.by_shape["singleton"] == {"resolved": 3, "promoted": 1, "terms": 3, "extended": 0,
                                                "share": 0.3333}
        cen = RM.promote_share(rows, generator="censuses", resolutions=res, pooled=pooled)
        assert cen.borrowed and cen.n_decided == 4 and cen.n_groups == 2          # under 50 decided: borrowed
        assert cen.per_group == pooled.per_group and cen.by_shape["multi"]["resolved"] == 1

    def test_not_borrowed_at_50(self, monkeypatch, tmp_path):
        monkeypatch.setattr(RM, "MIN_DECIDED", 3)
        rows = {"a#1": row("a#1", "censuses", "accepted"), "b#1": row("b#1", "censuses", "merged_into"),
                "c#1": row("c#1", "censuses", "merged_into"), "d#1": row("d#1", "censuses", "merged_into")}
        res = RM.load_resolutions([write_log(tmp_path / "b1", FIXTURE)])
        cen = RM.promote_share(rows, generator="censuses", resolutions=res)
        assert not cen.borrowed and cen.per_term == 0.25 and cen.per_group == 0.5   # g1 promoted, g2 not


@pytest.mark.skipif(not (TDA / "decisions.jsonl").exists(), reason="the recorded review log is absent")
class TestRecordedTDA:
    def test_the_hard_figures(self):
        """Plan 13 § 8 (measured 2026-10-13 on the tracked log): 354 events, 84.1 active minutes, 204 applied
        terms, 35 promoted, singleton median 12 s, 25 s per member, 2.43 terms per active minute."""
        rec = RM.review_record(TDA)
        assert rec["events"] == 354 and rec["active_minutes"] == 84.1 and rec["wall_minutes"] == 100.9
        assert rec["terms"] == {"applied": 204, "from_log": 176, "promoted": 35}
        assert rec["times"]["singleton_median_s"] == 12 and round(rec["times"]["per_member_s"]) == 25
        assert rec["times"]["singleton_mean_s"] == pytest.approx(15, abs=0.5) and rec["times"]["multi_median_s"] == 71
        assert rec["rate"]["terms_per_active_minute"] == 2.43 and rec["rate"]["terms_per_hour_active"] == 146
        assert rec["rate"]["terms_per_hour_wall"] == 121 and rec["rate"]["accepted_per_active_minute"] == 0.42
        assert rec["groups"]["opened"] == 88 and rec["groups"]["singletons"] == 44 and rec["groups"]["members"] == 218
        assert rec["idle_gaps"] == 1 and rec["superseded_logs"] == ["decisions.before_leftovers_2026-10-11.jsonl"]
        # one resolve (seq 129) was undone and the group resolved again: 68 effective resolutions, 69 events
        assert rec["groups"]["resolved"] == 68 and rec["groups"]["resolutions"]["promote"] == 35
        assert RM.active_minutes(RM.load_events(TDA, drop_undone=False), idle_s=600) == pytest.approx(84.13, abs=0.01)

    def test_the_promote_share_by_shape(self):
        """Decision 3's measurement: singletons 20 of 40 promoted; multi-member groups 15 of 29 over 99 terms (one
        of those 29 was undone and resolved again, so 28 effective)."""
        res = [r for r in RM.load_resolutions([TDA])]
        single = [r for r in res if len(r.members) == 1]
        multi = [r for r in res if len(r.members) > 1]
        assert (len(single), sum(r.promoted for r in single)) == (40, 20)
        assert (len(multi), sum(r.promoted for r in multi), sum(len(r.members) for r in multi)) == (28, 15, 97)
