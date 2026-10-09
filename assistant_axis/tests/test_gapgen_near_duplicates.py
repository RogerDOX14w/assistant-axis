"""The corpus near-duplicate scan (W3; :mod:`assistant_axis.gapgen.near_duplicates`): the pairs (self and every
arrangement partner left out, unordered pairs deduplicated, the cosine floor), the readings under M3's rule at
cut-off 3, the second-direction rule, the sections, the estimate, and the report's sections and links.  No API
calls: the fake Anthropic client and the toy corpus of the novelty tests."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen import near_duplicates as ND
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from assistant_axis.tests.test_gapgen_novelty import STEMS, rubrics, toy_index, write_corpus


def unit(*xs):
    v = np.array(xs, dtype=float)
    return v / np.linalg.norm(v)


# --------------------------------------------------------------------------- pairs

class TestArrangementPartners:
    def test_every_kind_and_the_label_pair(self, tmp_path):
        data = write_corpus(tmp_path / "data")
        d = data / "traits" / "instructions"
        # a clean pair by reciprocal labels that no arrangement records yet
        for s, o in (("mu", "nu"), ("nu", "mu")):
            (d / f"{s}.json").write_text(json.dumps({"positive_label": s, "negative_label": o,
                                                     "description": f"This means being {s}."}), encoding="utf-8")
        p = ND.arrangement_partners(data)
        assert p["delta"] == {"epsilon": ["pair"]}
        assert p["alpha"] == {"beta": ["triangle"], "gamma": ["triangle"]}
        assert p["zeta"] == {"eta": ["sequence"], "kappa": ["sequence"]}         # a sequence is excluded too
        assert p["lambda_mu"] == {}                                               # a singleton
        assert p["mu"] == {"nu": [ND.LABEL_PAIR]} and p["nu"] == {"mu": [ND.LABEL_PAIR]}

    def test_opposing_kinds(self):
        assert all(ND.is_opposing(k) for k in ("pair", "triangle", "tetrahedron", "5-simplex", ND.LABEL_PAIR))
        assert not any(ND.is_opposing(k) for k in ("sequence", "set", "map", "ring", "square", "4-cube", "6-orthoplex"))


#: a-b 0.95 (partners), a-c 0.80, b-c 0.947, a-d 0.60, b-d 0.57, c-d 0.48, d-e 0.80, e and a, b, c at 0 (a tie)
STEMS5 = ["a", "b", "c", "d", "e"]
Z5 = np.stack([unit(1, 0, 0), unit(0.95, 0.3122, 0), unit(0.8, 0.6, 0), unit(0.6, 0, 0.8), unit(0, 0, 1)])
PART5 = {"a": {"b": ["pair"]}, "b": {"a": ["pair"]}}


class TestNearestPairs:
    def test_selection(self):
        plan = ND.nearest_pairs(STEMS5, Z5, PART5, k=2, floor=0.5)
        # self never listed; the partner b left out of a's list and a out of b's, recorded as kept out
        assert ("a", "b") not in plan.pairs and ("a", "b") in plan.kept_out
        assert plan.kept_out[("a", "b")]["kept_out_for"] == ["a", "b"]
        assert plan.kept_out[("a", "b")]["kinds"] == ["pair"]
        assert sorted(plan.pairs) == [("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"), ("d", "e")]
        # unordered pairs deduplicated, with every trait that listed them
        assert plan.pairs[("b", "c")]["listed_by"] == [{"stem": "b", "rank": 1}, {"stem": "c", "rank": 1}]
        assert plan.pairs[("a", "c")]["listed_by"] == [{"stem": "a", "rank": 1}, {"stem": "c", "rank": 2}]
        # e's second neighbour is a three-way tie at 0 (a, b, c), broken by stem; under the floor, dropped
        assert list(plan.below_floor) == [("a", "e")]
        st = plan.stats
        assert (st["n_directed"], st["n_unique_before_floor"], st["n_below_floor"], st["n_pairs"]) == (10, 6, 1, 5)
        assert st["kept_out_by_kind"] == {"pair": 2} and st["n_kept_out_pairs_non_opposing_at_floor"] == 0

    def test_no_floor_and_k(self):
        plan = ND.nearest_pairs(STEMS5, Z5, {}, k=1, floor=-1.0)
        assert sorted(plan.pairs) == [("a", "b"), ("b", "c"), ("d", "e")]   # a->b, b->a, c->b, d->e, e->d
        assert plan.stats["n_directed"] == 5 and not plan.kept_out

    def test_shape_mismatch(self):
        with pytest.raises(ValueError):
            ND.nearest_pairs(STEMS5[:4], Z5, {})

    def test_scan_plan_also(self):
        plan = ND.nearest_pairs(STEMS5, Z5, PART5, k=2, floor=0.5)
        sp = ND.scan_plan(plan, also=[("b", "a", "asked"), ("c", "a", None)], stems=STEMS5, Z=Z5, partners=PART5)
        assert sp.both_ways == {("a", "b"), ("a", "c")}
        assert sp.pairs[("a", "b")]["sources"] == ["asked"] and sp.pairs[("a", "b")]["kinds"] == ["pair"]
        assert sp.pairs[("a", "b")]["cosine"] == pytest.approx(0.95, abs=1e-3) and sp.pairs[("a", "b")]["notes"] == ["asked"]
        assert sp.pairs[("a", "c")]["sources"] == ["scan", "asked"]
        assert len(sp.pairs) == 6
        with pytest.raises(ValueError):
            ND.scan_plan(plan, also=[("a", "zz", None)], stems=STEMS5, Z=Z5)

    def test_parse_pair(self):
        assert ND.parse_pair("mercurial/erratic") == ("mercurial", "erratic", None)
        assert ND.parse_pair("technical/specialist:Roger: the trait") == ("technical", "specialist", "Roger: the trait")
        for bad in ("mercurial", "a/a", "/b"):
            with pytest.raises(ValueError):
                ND.parse_pair(bad)


# --------------------------------------------------------------------------- readings

def res(sv, ov=None, *, opus=True):
    """A read_pairs result: Sonnet's value, and Opus's where the rule asked it."""
    out = {"sonnet": {"value": sv, "reason": f"s{sv}"} if sv is not None else {"value": None, "error": "bad"},
           "opus": None}
    if opus and ND.NV.OPUS_ROLES.get(NV.sonnet_action(sv, ND.CUT_OFF)):
        out["opus"] = {"value": ov, "reason": f"o{ov}"} if ov is not None else {"value": None, "error": "bad"}
    return out


class TestDirectionReading:
    @pytest.mark.parametrize("sv, ov, final, role", [
        (4, None, 4, None),               # a Sonnet 4 stands at cut-off 3
        (3, 4, 4, "at_cut_off"), (3, 2, 2, "at_cut_off"),
        (2, 3, 3, "below_cut_off"), (2, 1, 1, "below_cut_off"),
        (1, None, 1, None), (0, None, 0, None),
        ("unsure", 3, 3, "sonnet_unsure"), ("unsure", "unsure", "unsure", "sonnet_unsure"),
        ("opposite", None, "opposite", None),
    ])
    def test_final(self, sv, ov, final, role):
        d = ND.direction_reading(res(sv, ov), target="x", other="y")
        assert d["final"] == final and d["opus_role"] == role
        assert d["at_3"] == (isinstance(final, int) and final >= 3) and d["four"] == (final == 4)
        assert d["reason"] == (f"o{ov}" if role else f"s{sv}")

    def test_at_3_is_m3_covering_at_cut_off_3(self):
        for sv in (0, 1, 2, 3, 4, "opposite", "unsure"):
            for ov in (0, 1, 2, 3, 4, "opposite", "unsure"):
                r = res(sv, ov)
                d = ND.direction_reading(r, target="x", other="y")
                pv = NV.pair_verdict(sv, (r["opus"] or {}).get("value"), ND.CUT_OFF)
                assert d["at_3"] == NV.verdict_cuts(pv["verdict"], ND.RULES), (sv, ov)

    def test_unparsed_stalled_and_not_read(self):
        assert ND.direction_reading(res(None), target="x", other="y")["unparsed"] is True
        d = ND.direction_reading(res(3, None), target="x", other="y")       # Opus asked, never parsed
        assert d["final"] is None and d["unparsed"] and not d["at_3"]
        assert ND.direction_reading({"stalled": "Sonnet on y: failed", "phase": "sonnet"}, target="x", other="y") == \
            {"target": "x", "other": "y", "stalled": "Sonnet on y: failed", "phase": "sonnet"}
        assert ND.direction_reading(None, target="x", other="y") is None
        assert not ND.needs_second({"stalled": "x"}) and not ND.needs_second(None)
        assert ND.needs_second(res(2, 3)) and not ND.needs_second(res(3, 2))

    def test_classify(self):
        d = lambda sv, ov=None: ND.direction_reading(res(sv, ov), target="x", other="y")  # noqa: E731
        assert ND.classify(d(4), d(3, 4)) == "same_4"
        assert ND.classify(d(4), d(3, 3)) == "same_3"
        assert ND.classify(d(2, 3), d(4)) == "same_3"
        assert ND.classify(d(4), d(1)) == "one_way"
        assert ND.classify(d(0), d(4)) == "one_way"          # an asked pair read both ways
        assert ND.classify(d(2, 2), None) is None
        assert ND.classify(d("opposite"), None) is None
        assert ND.classify(d(4), None) == "incomplete"       # the second direction is still owed
        assert ND.classify({"stalled": "x"}, None) == "incomplete"


# --------------------------------------------------------------------------- the scan, end to end on the fake client

#: (target label, other label, model family) -> value; anything not named reads 1.
OVERLAP = {
    ("delta", "theta", "sonnet"): 4, ("theta", "delta", "sonnet"): 3, ("theta", "delta", "opus"): 4,       # 4 and 4
    ("alpha", "kappa", "sonnet"): 3, ("alpha", "kappa", "opus"): 3,
    ("kappa", "alpha", "sonnet"): 2, ("kappa", "alpha", "opus"): 3,                                         # 3 both ways
    ("beta", "eta", "sonnet"): 2, ("beta", "eta", "opus"): 3, ("eta", "beta", "sonnet"): 1,                 # one way
    ("gamma", "iota", "sonnet"): 2, ("gamma", "iota", "opus"): 1,                                           # below 3
    ("epsilon", "zeta", "sonnet"): 1,                                                                       # below 3
    ("eta", "lambda mu", "sonnet"): 0, ("lambda mu", "eta", "sonnet"): 4,                                   # asked
    ("alpha", "epsilon", "sonnet"): "opposite",
    ("beta", "zeta", "sonnet"): "unsure", ("beta", "zeta", "opus"): 4, ("zeta", "beta", "sonnet"): 4,      # 4 and 4
}
SCAN = [("delta", "theta"), ("alpha", "kappa"), ("beta", "eta"), ("gamma", "iota"), ("epsilon", "zeta"),
        ("alpha", "epsilon"), ("beta", "zeta")]
ASKED = [("eta", "lambda_mu")]


def responder(overlap=OVERLAP):
    def r(kw):
        obj = json.loads(user_text(kw))
        fam = "opus" if "opus" in kw["model"] else "sonnet"
        t, o = obj["target"]["label"], obj["other"]["label"]
        v = overlap.get((t, o, fam), 1)
        return make_response(json.dumps({"reason": f"{fam}: {t} vs {o} reads {v}", "similarity": v}),
                             input_tokens=150, output_tokens=80, cache_read=600)
    return r


def toy_plan():
    pairs = {tuple(sorted(p)): {"cosine": 0.5, "sources": ["scan"], "listed_by": [{"stem": p[0], "rank": 1}],
                                "notes": [], "kinds": []} for p in SCAN}
    for p in ASKED:
        pairs[tuple(sorted(p))] = {"cosine": 0.4, "sources": ["asked"], "listed_by": [], "notes": ["Roger asked"],
                                   "kinds": ["sequence"]}
    return ND.ScanPlan(pairs=dict(sorted(pairs.items())), both_ways={tuple(sorted(p)) for p in ASKED})


def make_runner(tmp_path, client):
    idx = toy_index(tmp_path)
    r = NR.NoveltyRunner(client=client, batch_id="nd", rubrics=rubrics(), index=idx,
                         label_sets=NV.LabelSets(set(), {}, {}), usage=MultiModelUsage(),
                         responses_path=tmp_path / "out" / "responses.jsonl", config_version="cfg", retry_delays=())
    return r, idx


def scan(tmp_path, *, gate=None, client=None):
    client = client or FakeAsyncAnthropic(responder())
    runner, idx = make_runner(tmp_path, client)
    cands = {s: ND.corpus_candidate(t) for s, t in idx.traits.items()}
    sp = toy_plan()
    first, second, back = ND.run_scan(runner, sp, cands, gate=gate)
    rows = ND.assemble_rows(sp, traits=idx.traits, first=first, second=second, back=back)
    return rows, client, runner, idx, sp


def sent(client):
    """``[(target, other, family), ...]`` in the order sent."""
    out = []
    for kw in client.calls:
        obj = json.loads(user_text(kw))
        out.append((obj["target"]["label"], obj["other"]["label"], "opus" if "opus" in kw["model"] else "sonnet"))
    return out


class TestScan:
    def test_the_rule_at_cut_off_3_and_the_second_direction(self, tmp_path):
        rows, client, runner, _, _ = scan(tmp_path)
        calls = sent(client)
        # the first direction: the stem that sorts first is the target, Sonnet on every pair
        first_sonnet = {(t, o) for t, o, f in calls[:8] if f == "sonnet"}
        assert first_sonnet == {("alpha", "epsilon"), ("alpha", "kappa"), ("beta", "eta"), ("beta", "zeta"),
                                ("delta", "theta"), ("epsilon", "zeta"), ("eta", "lambda mu"), ("gamma", "iota")}
        opus = {(t, o) for t, o, f in calls if f == "opus"}
        # Opus re-reads Sonnet's 3s, 2s and unsure, never a 4, a 1, a 0 or an opposite
        assert opus == {("alpha", "kappa"), ("beta", "eta"), ("gamma", "iota"), ("beta", "zeta"),
                        ("theta", "delta"), ("kappa", "alpha")}
        # the second direction: where the first's final read 3 or above, and the asked pair whatever it read
        second = {(t, o) for t, o, f in calls if f == "sonnet"} - first_sonnet
        assert second == {("theta", "delta"), ("kappa", "alpha"), ("eta", "beta"), ("zeta", "beta"), ("lambda mu", "eta")}
        assert len(calls) == 8 + 4 + 5 + 2
        by = {(r["a"], r["b"]): r for r in rows}
        assert by[("delta", "theta")]["section"] == "same_4" and by[("beta", "zeta")]["section"] == "same_4"
        assert by[("alpha", "kappa")]["section"] == "same_3"
        assert by[("beta", "eta")]["section"] == "one_way"
        assert by[("eta", "lambda_mu")]["section"] == "one_way"
        assert by[("eta", "lambda_mu")]["second_because"] == "asked"
        assert by[("beta", "eta")]["second_because"] == "first_at_3"
        for p in (("gamma", "iota"), ("epsilon", "zeta"), ("alpha", "epsilon")):
            assert by[p]["section"] is None and by[p]["ba"] is None
        assert by[("alpha", "epsilon")]["final_ab"] == "opposite"
        r = by[("theta", "delta") if ("theta", "delta") in by else ("delta", "theta")]
        assert r["ab"]["sonnet"]["value"] == 4 and r["ab"]["opus"] is None
        assert r["ba"]["sonnet"]["value"] == 3 and r["ba"]["opus"]["value"] == 4 and r["final_ba"] == 4
        assert r["ba"]["reason"].startswith("opus")
        assert r["label_a"] == "delta" and r["description_b"].startswith("This means being theta")
        # every response kept, and the parse rates clean
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        assert len(recs) == len(calls) and {x["wave"] for x in recs} == {"d1_sonnet", "d1_opus", "d2_sonnet", "d2_opus"}
        assert all(v["ok"] == v["n"] for v in runner.warn_parse_rates().values())

    def test_cache_marked_and_display_labels(self, tmp_path):
        _, client, _, _, _ = scan(tmp_path)
        kw = client.calls[0]
        assert isinstance(kw["system"], list) and kw["system"][0].get("cache_control")
        assert any(json.loads(user_text(k))["other"]["label"] == "lambda mu" for k in client.calls)

    def test_gate_stops_before_the_second_direction(self, tmp_path):
        seen = {}

        class Stop(RuntimeError):
            pass

        def gate(back):
            seen["back"] = sorted((b, a, why) for b, a, _, why in back)
            raise Stop("over the cap")
        client = FakeAsyncAnthropic(responder())
        with pytest.raises(Stop):
            scan(tmp_path, gate=gate, client=client)
        assert seen["back"] == [("eta", "beta", "first_at_3"), ("kappa", "alpha", "first_at_3"),
                                ("lambda_mu", "eta", "asked"), ("theta", "delta", "first_at_3"),
                                ("zeta", "beta", "first_at_3")]
        assert len(client.calls) == 12                      # the first direction only: 8 Sonnet, 4 Opus

    def test_resume_sends_nothing_again(self, tmp_path):
        rows, client, _, idx, sp = scan(tmp_path)
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        c2 = FakeAsyncAnthropic(responder())
        r2 = NR.NoveltyRunner(client=c2, batch_id="nd", rubrics=rubrics(), index=idx,
                              label_sets=NV.LabelSets(set(), {}, {}), usage=MultiModelUsage(),
                              responses_path=tmp_path / "out2" / "responses.jsonl", config_version="cfg",
                              retry_delays=(), resume_records=recs)
        cands = {s: ND.corpus_candidate(t) for s, t in idx.traits.items()}
        first, second, back = ND.run_scan(r2, sp, cands)
        assert c2.calls == []
        assert ND.assemble_rows(sp, traits=idx.traits, first=first, second=second, back=back) == rows

    def test_stalled_first_direction_waits(self, tmp_path):
        def flaky(kw):
            obj = json.loads(user_text(kw))
            if obj["target"]["label"] == "gamma":
                return RuntimeError("boom")
            return responder()(kw)
        rows, _, _, _, _ = scan(tmp_path, client=FakeAsyncAnthropic(flaky))
        r = next(x for x in rows if x["a"] == "gamma")
        assert r["section"] == "incomplete" and "stalled" in r["ab"] and r["ba"] is None

    def test_distribution(self, tmp_path):
        rows, *_ = scan(tmp_path)
        d = ND.readings_distribution(rows)
        assert d["first_direction_final"] == {"0": 1, "1": 2, "3": 2, "4": 2, "opposite": 1}
        assert d["second_direction_final"] == {"1": 1, "3": 1, "4": 3}
        assert d["sections"] == {"same_4": 2, "same_3": 1, "one_way": 2, "below_3": 3}
        assert sum(d["opus_rereads_by_role"].values()) == 6
        assert d["second_read_because"] == {"first_at_3": 4, "asked": 1}


# --------------------------------------------------------------------------- the estimate

class TestEstimate:
    def test_measured_shares(self):
        rows = ([{"cosine": 0.4, "sonnet": {"value": 3}, "opus": {"value": 4}}] * 6
                + [{"cosine": 0.4, "sonnet": {"value": 1}, "opus": None}] * 4
                + [{"cosine": 0.5, "sonnet": {"value": 2}, "opus": None}] * 3
                + [{"cosine": 0.2, "sonnet": {"value": 4}, "opus": None}] * 50)          # under the first bin
        sh = ND.measured_shares(rows, min_obs=10)
        assert sh.n == (10, 3, 0, 0)
        assert sh.opus[0] == pytest.approx(0.6) and sh.second[0] == pytest.approx(0.6)
        assert sh.opus[1:] == (1.0, 1.0, 1.0) and sh.second[1:] == (1.0, 1.0, 1.0)  # too few: err high
        assert sh.at(0.3) == sh.at(0.4) and sh.at(0.7) == (1.0, 1.0)

    def test_estimate_scan(self):
        sh = ND.Shares(bins=(0.35,), opus=(0.5,), second=(0.25,), n=(100,))
        sp = ND.ScanPlan(pairs={("a", "b"): {"cosine": 0.4}, ("a", "c"): {"cosine": 0.5},
                                ("b", "c"): {"cosine": 0.6}, ("c", "d"): {"cosine": 0.5}},
                         both_ways={("c", "d")})
        est = ND.estimate_scan(sp, sh, overlap_tokens={"sonnet": (200, 80), "opus": (200, 150)})
        n = {x.label.split(" (")[0]: x.n_calls for x in est.lines}
        assert n == {"first direction, Sonnet": 4, "first direction, Opus": 2, "second direction, Sonnet": 2,
                     "second direction, Opus": 2}
        assert est.usd > 0
        assert ND.estimate_second([1, 2, 3]).lines[0].n_calls == 3


# --------------------------------------------------------------------------- the cosine table and the report

DROP_OR_MERGE = """# Drop-or-merge candidates

## Partners excluded (the real candidates)

| trait | nearest | flagged by | raw | centred |
|---|---|---|---|---|
| [delta](../../traits/instructions/delta.json) | [theta](../../traits/instructions/theta.json) | openai, gemma | 0.81 | 0.7 |
| [gamma](../../traits/instructions/gamma.json) | [iota](../../traits/instructions/iota.json) | gemma | 0.79 | 0.7 |
| [good only](../../traits/instructions/good_only.json) | [good even](../../traits/instructions/good_even.json) | gemma | 0.84 | 0.6 |

## All neighbours (expected: recorded pairs)

| [alpha](../../traits/instructions/alpha.json) | [beta](../../traits/instructions/beta.json) | openai | 0.9 | 0.8 |
"""


def sections_of(md: str) -> dict:
    out, cur = {}, None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = line[3:]
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


class TestReport:
    def test_parse_drop_or_merge(self):
        rows = ND.parse_drop_or_merge(DROP_OR_MERGE)
        assert [(r["a"], r["b"]) for r in rows] == [("delta", "theta"), ("gamma", "iota"), ("good_only", "good_even")]
        assert rows[0]["flagged_by"] == "openai, gemma" and rows[0]["raw"] == pytest.approx(0.81)
        assert ND.parse_drop_or_merge("no table here") == []

    def test_comparison(self, tmp_path):
        rows, _, _, idx, _ = scan(tmp_path)
        cmp = ND.comparison(rows, ND.parse_drop_or_merge(DROP_OR_MERGE), corpus=idx.traits)
        t = {tuple(x["pair"]): x for x in cmp["table"]}
        assert t[("delta", "theta")]["section"] == "same_4"
        assert t[("gamma", "iota")]["section"] is None and t[("gamma", "iota")]["why_not_read"] is None
        assert t[("good_even", "good_only")]["why_not_read"] == "not in the corpus this scan read"
        assert sorted((r["a"], r["b"]) for r in cmp["missed_both"]) == [("alpha", "kappa"), ("beta", "zeta")]
        assert len(cmp["missed_one_way"]) == 2

    def test_markdown_sections_and_links(self, tmp_path):
        rows, _, _, idx, _ = scan(tmp_path)
        rng = np.random.default_rng(0)
        Z = rng.normal(size=(len(STEMS), 6))
        Z /= np.linalg.norm(Z, axis=1, keepdims=True)
        plan = ND.nearest_pairs(sorted(STEMS), Z, ND.arrangement_partners(write_corpus(tmp_path / "d2")), floor=0.0)
        cmp = ND.comparison(rows, ND.parse_drop_or_merge(DROP_OR_MERGE), corpus=idx.traits, plan=plan)
        run = {"git_sha": "abc1234", "rubric": {"name": "overlap_concept", "version": 6, "sha256": "f" * 64},
               "cost_usd": 0.12, "estimate_usd": 0.2, "cap_usd": 10.0, "n_calls": 19, "wall_time_s": 60,
               "models": {"overlap_first": NR.FIRST_MODEL, "overlap_second": NR.SECOND_MODEL},
               "embedding": {"model": "text-embedding-3-large", "variant": "centred", "representation": "w20"}}
        md = ND.report_markdown(rows, plan=plan, traits=idx.traits, cmp=cmp, run=run,
                                dist=ND.readings_distribution(rows), cosine_table_rel="../calibration_916/drop_or_merge.md")
        sec = sections_of(md)
        assert list(sec)[:6] == [ND.SECTION_TITLES["same_4"], ND.SECTION_TITLES["same_3"], ND.SECTION_TITLES["one_way"],
                                 "Pairs Roger asked about", "Against the cosine table", "What this scan does not see"]
        s4, s3, s1 = (sec[ND.SECTION_TITLES[s]] for s in ND.SECTIONS)
        assert "[delta](../../traits/instructions/delta.json) and [theta](../../traits/instructions/theta.json)" in s4
        assert "[beta](../../traits/instructions/beta.json) and [zeta](../../traits/instructions/zeta.json)" in s4
        assert "| S4 | S3 O4 |" in s4 and "kappa" not in s4
        assert "[alpha](../../traits/instructions/alpha.json) and [kappa](../../traits/instructions/kappa.json)" in s3
        assert "| S3 O3 | S2 O3 |" in s3
        assert "eta" in s1 and "[lambda mu](../../traits/instructions/lambda_mu.json)" in s1   # label, not stem
        assert "(read on request)" in s1
        assert "gamma" not in s4 + s3 + s1 and "epsilon" not in s4 + s3 + s1
        asked = sec["Pairs Roger asked about"]
        assert "lambda mu" in asked and "Roger asked" in asked and "arrangement partners (sequence)" in asked
        cmp_md = sec["Against the cosine table"]
        assert "[drop_or_merge.md](../calibration_916/drop_or_merge.md)" in cmp_md
        assert "[*good only*](../../traits/instructions/good_only.json)" in cmp_md
        assert "not read: not in the corpus this scan read" in cmp_md
        assert "2 pairs at 3 or more both ways" in cmp_md
        assert "[usage.json](./usage.json)" in md and "](../../../reports/trait_gap_generation/glossary.md#" in md
        assert "_" not in "".join(x.split("](")[0] for x in md.split("[")[1:] if "traits/instructions" in x)

    def test_reading_text(self):
        d = lambda sv, ov=None: ND.direction_reading(res(sv, ov), target="x", other="y")  # noqa: E731
        assert ND.reading_text(d(4)) == "S4" and ND.reading_text(d(3, 4)) == "S3 O4"
        assert ND.reading_text(d("opposite")) == "S opposite" and ND.reading_text(d("unsure", 2)) == "S unsure O2"
        assert ND.reading_text(None) == "not read" and ND.reading_text({"stalled": "x"}) == "stalled"
