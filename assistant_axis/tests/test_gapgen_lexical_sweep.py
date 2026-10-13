"""Workstream 11's sweep (``assistant_axis.gapgen.lexical_sweep``; coding_plan_11_novelty_ensemble.md § 8,
"lexical_sweep"): the plan of lexical-only pairs, the reading under each row's own rule set, the block and its flags,
the untouched ``novelty`` block, the report, the cap, and Roger's marks sheet.  No API calls: fake clients, the toy
corpus of the M3 tests, a tmp registry through the real API."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import lexical as LX
from assistant_axis.gapgen import lexical_sweep as LS
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from assistant_axis.tests.test_gapgen_lexical import FakeLexicon, ct
from assistant_axis.tests.test_gapgen_novelty import rubrics, toy_index

R2, R3 = NV.RULES[2], NV.RULES[3]


def block(*, decision="new", a=0, rules=R3, listed=(), readings=(), covered_by=None, pass_=None, review=None,
          pcf=()):
    spec = NV.cut_off_spec(a, rules)
    b = {"run_id": "m3run", "decision": decision, "covered_by": covered_by, "alignment_score": a, "cut_off": spec.c,
         "listed": [{"stem": s, "cosine": 0.5, "rank": i, "via": "retrieved", "relation": "similar"}
                    for i, s in enumerate(listed, 1)],
         "readings": [{"position": i, "stem": s} for i, s in enumerate(readings, 1)],
         "rules": rules.as_dict(), "pair_completion_for": list(pcf), "at": "2026-10-12T00:00:00+00:00",
         "embedding": {"query_form": "gloss_w14", "representation": "w20"}}
    if rules.cut_off_rule != "step":
        b["cut_off_rule"] = spec.as_dict()
    if pass_:
        b["pass"] = pass_
    return b


def row(label, nv, *, review=None, gloss=None):
    from assistant_axis.gapgen.normalize import normalize_candidate
    n = normalize_candidate(label)
    return {"key": f"{n.stem}#1", "stem": n.stem, "label": n.label, "gloss": gloss or f"This means being {label}.",
            "novelty": nv, "review": review or {"status": "unreviewed"}, "sources": [{"generator": "g"}]}


# A toy lookup over the M3 toy corpus's stems (alpha ... zeta), plus a queue entry with a text and one without
CORPUS = {s: ct(s, partner={"delta": "epsilon", "epsilon": "delta"}.get(s))
          for s in ("alpha", "beta", "gamma", "delta", "epsilon", "theta", "iota", "zeta")}
ENTRIES = [{"stem": "queuey", "label": "queuey", "has_text": True, "text": "This means queuey.", "status": "candidate"},
           {"stem": "nametag", "label": "nametag", "has_text": False, "text": "", "status": "backlog"}]
LINKS = {"alphoid": {"synonym": ["alpha"], "similar": ["beta", "queuey", "nametag"], "also": ["gamma"]},
         "deltish": {"synonym": ["theta"]},
         "epsilonic": {"also": ["epsilon"]}}
MOBY = {"alphoid": {"synonym": ["alpha", "zeta", "iota"]}}


def lookup(moby=False):
    lex = {"oewn": FakeLexicon(links=LINKS, antonyms={"deltish": ["epsilon"], "alphoid": ["zeta"]},
                               derivations={"alphoid": ["alphoidness"]})}
    if moby:
        lex["moby"] = FakeLexicon("moby", links=MOBY, version="mobysha")
    return LX.build_lookup(CORPUS, ENTRIES, lexicons=lex)


class FakeIndex:
    def __init__(self, cos):
        self.cos = cos
        self.traits = {s: ct(s) for s in list(CORPUS) + ["queuey"]}

    def project(self, v):
        return v

    def cosine_to(self, q, stem):
        return self.cos.get(stem)


# --------------------------------------------------------------------------- the plan

class TestPlan:
    def rows(self):
        return {"alphoid#1": row("alphoid", block(listed=["gamma"], readings=["beta"], a=2)),
                "deltish#1": row("deltish", block(a=3, rules=R2, pass_="physical")),
                "epsilonic#1": row("epsilonic", block(decision="covered", covered_by="epsilon")),
                "nolinks#1": row("nolinks", block())}

    def test_only_lexical_only_pairs_with_cosine_and_what_is_not_judged(self):
        kept = LS.kept_rows(self.rows())
        assert set(kept) == {"alphoid#1", "deltish#1", "nolinks#1"}                    # a covered row is not swept
        lk = lookup(moby=True)
        idx = FakeIndex({"alpha": 0.4, "theta": 0.3, "queuey": 0.31, "zeta": 0.1})
        items, plans = LS.sweep_plan(kept, lk, idx, {"alphoid#1": [1.0], "deltish#1": [1.0]},
                                     descriptions={s: "d" for s in idx.traits})
        by = {(it.key, it.stem): it for it in items}
        # gamma listed and beta read by M3: never a lexical-only pair; their links are on the row plan, listed_by_m3
        assert ("alphoid#1", "gamma") not in by and ("alphoid#1", "beta") not in by
        assert {it.stem for it in plans["alphoid#1"].links if it.listed_by_m3} == {"beta", "gamma"}
        assert by[("alphoid#1", "alpha")].link == "synonym" and by[("alphoid#1", "alpha")].cosine == 0.4
        assert by[("alphoid#1", "alpha")].judged and "moby:synonym" in by[("alphoid#1", "alpha")].also_found
        assert by[("alphoid#1", "queuey")].kind == "queue" and by[("alphoid#1", "queuey")].judged
        assert by[("alphoid#1", "nametag")].not_judged == "name_only"
        assert by[("alphoid#1", "zeta")].moby_only and by[("alphoid#1", "zeta")].not_judged == "moby_below_floor"
        assert by[("alphoid#1", "iota")].not_judged == "moby_no_cosine"
        d = by[("deltish#1", "theta")]
        assert d.pass_ == "physical" and d.rules == "m3_rules_2" and d.cut_off["c"] == 4
        g = by[("alphoid#1", "alpha")].cut_off
        assert g == {"c": 3, "sonnet_alone": False, "opus_check": False, "rule": "graded", "band": "alignment 2"}
        assert [a.stem for a in plans["deltish#1"].antonyms] == ["epsilon"]
        assert plans["nolinks#1"].links == [] and not LS.needs_block(plans["nolinks#1"])
        assert LS.needs_block(plans["alphoid#1"])

    def test_row_rules(self):
        spec, rules = LS.row_rules(block(a=2, rules=R3))
        assert rules == R3 and spec.c == 3 and not spec.sonnet_alone
        spec, rules = LS.row_rules(block(a=2, rules=R2))
        assert rules == R2 and spec.c == 4 and spec.opus_check
        spec, _ = LS.row_rules({"alignment_score": 2, "cut_off": 3, "rules": R2.as_dict()})
        assert spec.c == 3 and spec.rule == "fixed"                                      # the recorded cut-off wins

    def test_cap_keeps_oewn_and_cuts_moby_by_cosine(self):
        def it(lex, cos, n):
            return LS.PairItem(key=f"k{n}#1", label="l", gloss="g", pass_="trait", stem=f"s{n}", kind="corpus",
                               link="synonym", lexicon=lex, name_only=False, word=None, via=None, also_found=[],
                               cosine=cos, cut_off={"c": 3}, rules="m3_rules_3", alignment_score=0, position=1)
        items = [it("oewn", 0.1, i) for i in range(3)] + [it("moby", 0.2 + i / 100, 10 + i) for i in range(5)]
        s, o = LS.pair_prices()
        per = s + 0.62 * o
        rep = LS.cap_items(items, budget_usd=per * 5.5)
        assert rep["n_cut"] == 3 and rep["n_kept_moby"] == 2
        assert all(x.judged for x in items if x.lexicon == "oewn")
        kept = sorted(round(x.cosine, 4) for x in items if x.lexicon == "moby" and x.judged)
        assert kept == [0.23, 0.24] and round(rep["cut_cosine"], 4) == 0.22
        assert LS.cap_items(items, budget_usd=100)["n_cut"] == 0

    def test_estimate_prices_the_assumed_share(self):
        e = LS.sweep_estimate(1000)
        s, o = LS.pair_prices()
        assert abs(e.usd - (1000 * s + 620 * o)) < 1e-6 and "ASSUMED" in str(e.lines[1])
        assert LS.sweep_estimate(10_000).usd > 20


# --------------------------------------------------------------------------- the reading

def responder(answers, *, refuse=()):
    """Overlap calls answered from ``answers[(candidate label, trait label, family)]``; ``refuse`` pairs get Sonnet
    5.5's reasoning-extraction refusal (no text, stop reason ``refusal``)."""
    def resp(kw):
        obj = json.loads(user_text(kw))
        fam = "opus" if "opus" in kw["model"] else "sonnet"
        c, o = obj["target"]["label"], obj["other"]["label"]
        if (c, o) in refuse:
            r = make_response("", input_tokens=150, output_tokens=0, stop_reason="refusal")
            r.content = []
            return r
        v = answers.get((c, o, fam), answers.get((c, o), 1))
        return make_response(json.dumps({"reason": f"{fam} on {o}", "similarity": v}), input_tokens=150,
                             output_tokens=80, cache_read=600)
    return resp


def runner(tmp_path, resp, **kw):
    idx = toy_index(tmp_path)
    client = FakeAsyncAnthropic(resp)
    r = NR.NoveltyRunner(client=client, batch_id="lex1", rubrics=rubrics(), index=idx,
                         label_sets=NV.label_sets(idx.traits, {"entries": []}), usage=MultiModelUsage(),
                         responses_path=tmp_path / "out" / "responses.jsonl", k=4, retry_delays=(), **kw)
    return r, client


def item(key, label, stem, *, a, rules, pos=1):
    spec = NV.cut_off_spec(a, rules)
    return LS.PairItem(key=key, label=label, gloss=f"This means being {label}.", pass_="trait", stem=stem,
                       kind="corpus", link="synonym", lexicon="oewn", name_only=False, word=stem, via=None,
                       also_found=[], cosine=0.1, cut_off=spec.as_dict(), rules=rules.name, alignment_score=a,
                       position=pos)


class TestRunSweep:
    def test_each_pair_under_its_rows_own_rules(self, tmp_path):
        """The same readings (Sonnet 3, Opus 3) cover a rule-set-3 alignment-2 row (the graded rule: both models at
        3) and not a rule-set-2 alignment-2 row (the step rule's cut-off 4)."""
        items = [item("graded#1", "graded", "alpha", a=2, rules=R3), item("stepped#1", "stepped", "alpha", a=2, rules=R2),
                 item("low#1", "low", "beta", a=0, rules=R3)]
        r, client = runner(tmp_path, responder({("graded", "alpha"): 3, ("stepped", "alpha"): 3, ("low", "beta"): 1}))
        res, stop = LS.run_sweep(r, items)
        assert stop is None
        by = {x["key"]: x for x in res}
        assert by["graded#1"]["at_cut_off"] and by["graded#1"]["verdict"] == "cut"
        assert by["graded#1"]["sonnet"]["value"] == 3 and by["graded#1"]["opus"]["value"] == 3
        assert not by["stepped#1"]["at_cut_off"] and by["stepped#1"]["verdict"] == "keep"
        assert by["stepped#1"]["opus"]["value"] == 3                                      # the Opus check at c - 1
        assert not by["low#1"]["at_cut_off"] and by["low#1"]["opus"] is None
        assert len(client.calls) == 5
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        assert {x["wave"] for x in recs} == {"lex_sonnet", "lex_opus"} and len(recs) == 5

    def test_a_refusal_is_a_failed_call_recorded_and_counted(self, tmp_path):
        items = [item("refused#1", "refused", "alpha", a=0, rules=R3), item("fine#1", "fine", "beta", a=0, rules=R3)]
        r, client = runner(tmp_path, responder({("fine", "beta"): 4}, refuse={("refused", "alpha")}))
        res, _ = LS.run_sweep(r, items)
        by = {x["key"]: x for x in res}
        assert by["refused#1"]["verdict"] == "unparsed" and by["refused#1"]["sonnet"]["value"] is None
        assert by["fine#1"]["at_cut_off"]
        rates = r.warn_parse_rates()
        assert rates["overlap:claude-sonnet-5-5"]["n"] == 2 and rates["overlap:claude-sonnet-5-5"]["ok"] == 1
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        refused = [x for x in recs if x["key"] == "refused#1"]
        assert len(refused) == 2 and all(x["stop_reason"] == "refusal" and x["parse_errors"] for x in refused)

    def test_a_resume_sends_nothing_answered(self, tmp_path):
        items = [item("graded#1", "graded", "alpha", a=2, rules=R3)]
        r, client = runner(tmp_path, responder({("graded", "alpha"): 3}))
        LS.run_sweep(r, items)
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        r2, client2 = runner(tmp_path, responder({}), resume_records=recs)
        res, _ = LS.run_sweep(r2, items)
        assert client2.calls == [] and res[0]["at_cut_off"]


# --------------------------------------------------------------------------- the block

def entry(**kw):
    base = {"stem": "x", "judged": True, "verdict": "keep", "at_cut_off": False, "name_only": False}
    return base | kw


class TestBlock:
    @pytest.mark.parametrize("links,ants,flags", [
        ([entry(at_cut_off=True, verdict="cut")], [], ["lexical_cover"]),
        ([entry(), entry(stem="y")], [], ["lexical_below_cut"]),
        ([entry(judged=False, name_only=True, verdict=None)], [], ["lexical_name_only"]),
        ([entry(verdict="unparsed")], [], ["lexical_unparsed"]),
        ([entry(verdict="unparsed"), entry(stem="y")], [], ["lexical_below_cut", "lexical_unparsed"]),
        ([entry(at_cut_off=True, verdict="cut"), entry(stem="y", judged=False, name_only=True, verdict=None)],
         [{"partner_has_file": False}], ["lexical_cover", "lexical_name_only", "lexical_antonym"]),
        ([], [{"partner_has_file": True}], []),
        ([entry(judged=False, verdict=None)], [], []),
    ])
    def test_flag_truth_table(self, links, ants, flags):
        assert LS.block_flags(links, ants) == flags

    def test_the_block_and_the_untouched_novelty_block(self, tmp_path):
        kept = {"alphoid#1": row("alphoid", block(listed=["gamma"], readings=["beta"], a=2))}
        lk = lookup()
        idx = FakeIndex({"alpha": 0.4})
        items, plans = LS.sweep_plan(kept, lk, idx, {"alphoid#1": [1.0]}, descriptions={s: "d" for s in idx.traits},
                                     candidates_for_family={"alphoid": "alphoid", "alphoidness": "alphoidness"})
        p = plans["alphoid#1"]
        readings = {("alphoid#1", "alpha"): {"sonnet": {"value": 3, "reason": "s"}, "opus": {"value": 3, "reason": "o"},
                                             "verdict": "cut", "at_cut_off": True}}
        b = LS.lexical_block(kept["alphoid#1"], p.links, p.antonyms, p.family, readings, run_id="lex1", lookup=lk,
                             spec=p.spec, rules=p.rules, at="2026-10-14T00:00:00+00:00")
        assert b["flags"] == ["lexical_cover", "lexical_name_only", "lexical_antonym"]
        by = {x["stem"]: x for x in b["links"]}
        assert by["alpha"]["judged"] and by["alpha"]["at_cut_off"] and by["alpha"]["sonnet"]["value"] == 3
        assert by["gamma"]["listed_by_m3"] and not by["gamma"]["judged"] and by["gamma"]["not_judged"] == "listed_by_m3"
        assert by["queuey"]["not_judged"] == "not_read" and not by["queuey"]["judged"]
        assert b["n_pairs_judged"] == 1 and b["rules"] == "m3_rules_3" and b["cut_off_rule"]["band"] == "alignment 2"
        assert b["lookup_sha256"] == lk.content_sha256 and b["lexicons"] == {"oewn": "fake:1"}
        assert [(a["stem"], a["partner_has_file"]) for a in b["antonyms"]] == [("zeta", False)]
        assert b["family"] == [{"stem": "alphoidness", "kind": "candidate", "via": "derivation"}]
        # the registry write: the lexical block replaced whole, the novelty block byte-identical
        reg_path = tmp_path / "registry.jsonl"
        rep = submit_candidates([Candidate(surface="alphoid", generator="toy", run_id="r1")], registry_path=reg_path)
        reg = Registry(reg_path)
        reg.update_many({rep.keys[0]: {"novelty": kept["alphoid#1"]["novelty"], "gloss": "g"}})
        before = reg.fold()[rep.keys[0]]
        reg.update_many({rep.keys[0]: {"lexical": b}}, merge_blocks=False)
        reg.update_many({rep.keys[0]: {"lexical": {"run_id": "lex2", "links": []}}}, merge_blocks=False)
        after = reg.fold()[rep.keys[0]]
        assert LS.block_sha256(after["novelty"]) == LS.block_sha256(before["novelty"])
        assert after["lexical"] == {"run_id": "lex2", "links": []}                      # replaced whole
        assert {k: v for k, v in after.items() if k not in ("lexical", "rev", "updated_at")} == \
            {k: v for k, v in before.items() if k not in ("lexical", "rev", "updated_at")}
        reg.merge_block(rep.keys[0], "lexical", {"note": "x"})                           # a registry block now
        assert reg.fold()[rep.keys[0]]["lexical"]["note"] == "x"


# --------------------------------------------------------------------------- the report and the marks

def result(key, stem, *, cut, s, o=None, link="synonym", lexicon="oewn", kind="corpus", c=3, gloss="g", label=None):
    return {"key": key, "label": label or key.split("#")[0], "gloss": gloss, "stem": stem, "kind": kind, "link": link,
            "lexicon": lexicon, "cosine": 0.2, "pass": "trait", "cut_off": {"c": c, "band": "alignment 0-1"},
            "sonnet": {"value": s, "reason": "SONNETREASON"}, "opus": {"value": o, "reason": "OPUSREASON"} if o is not None else None,
            "verdict": "cut" if cut else "keep", "at_cut_off": cut}


class TestReport:
    def test_counts_stop_line_and_proxies(self):
        kept = {"pleasant#1": {"review": {"status": "merged_into", "into": "trait:agreeable"}, "novelty": {}},
                "a#1": {"review": {"status": "accepted"}, "novelty": {}},
                "b#1": {"review": {"status": "unreviewed"}, "novelty": {"pair_completion_for": ["z"]}}}
        items = [LS.PairItem.from_dict(item("pleasant#1", "pleasant", "agreeable", a=0, rules=R3).as_dict()),
                 LS.PairItem.from_dict(item("a#1", "a", "x", a=0, rules=R3).as_dict()),
                 LS.PairItem.from_dict(item("b#1", "b", "y", a=0, rules=R3).as_dict())]
        results = [result("pleasant#1", "agreeable", cut=True, s=3, o=3), result("a#1", "x", cut=True, s=4),
                   result("b#1", "y", cut=False, s=3, o=2, c=4, link="also")]
        plans = {"b#1": LS.RowPlan(key="b#1", pass_="trait", links=[], antonyms=[LX.Antonym("z", "antonym", False)],
                                   family=[], spec=NV.CutOff(c=4), rules=R3, candidate=None)}
        usage = {"total_cost_usd": 0.01, "per_model": {"claude-sonnet-5-5": {"cost_usd": 0.004}}}
        rep = LS.sweep_report(results, items=items, kept=kept, plans=plans, usage=usage)
        assert rep["stop_rule"]["covers_at_cut_off"] == 2 and rep["stop_rule"]["below_stop_line"]
        assert rep["by_link"] == {"also": {"judged": 1, "covers": 0}, "synonym": {"judged": 2, "covers": 2}}
        assert rep["precision_proxies"]["merged_into_that_trait"] == ["pleasant#1"]
        assert rep["precision_proxies"]["accepted_as_new"] == ["a#1"]
        assert rep["roger_merges"]["lexical_target_read_at_cut_off"] == 1
        assert rep["audit_retrieval_misses_covered"] == ["pleasant#1"]
        assert rep["below_cut_three_at_cut_off_four"] == 1 and rep["opus_share_measured"] == round(2 / 3, 4)
        assert rep["antonym_evidence"] == {"rows": 1, "singleton_partner": 1, "beside_pair_completion_for": 1}
        assert rep["yield_per_dollar"] == 200.0
        md = LS.sweep_markdown(rep, results, kept=kept, batch_id="lex1")
        assert md.splitlines()[2].startswith("**covers at the cut-off: 2 pairs")

    def test_the_marks_sheet_is_blind_and_the_marks_fold(self):
        results = [result(f"w{i}#1", f"t{i}", cut=True, s=4, link=("synonym", "similar")[i % 2],
                          gloss=f"This means w{i}.") for i in range(50)]
        results.append(result("underneath#1", "t99", cut=False, s=1))
        md, key = LS.marks_sheet(results, descriptions={f"t{i}": f"desc {i}" for i in range(100)},
                                 target_labels={}, n=40, batch_id="lex1")
        assert key["n_marked"] == 40 and key["n_covers"] == 50
        assert sum(1 for r in key["rows"] if r["link"] == "synonym") == 20                # stratified in proportion
        assert "underneath" not in md and "SONNETREASON" not in md and "OPUSREASON" not in md   # no readings shown
        assert key["rows"][0]["sonnet"] == 4 and key["rows"][0]["sonnet_reason"] == "SONNETREASON"
        md2, key2 = LS.marks_sheet(results, descriptions={}, target_labels={}, n=40, batch_id="lex1")
        assert key2["rows"] == key["rows"]                                                 # seeded
        small, k3 = LS.marks_sheet(results[:3], descriptions={}, target_labels={}, n=40, batch_id="lex1")
        assert k3["n_marked"] == 3
        # Roger marks: C on 37, N on 2, ? on 1
        marked = []
        for line in md.splitlines():
            if line.startswith("| ") and line.split("|")[1].strip().isdigit():
                n = int(line.split("|")[1])
                mark = "C" if n <= 37 else ("N  homonym" if n <= 39 else "?")
                marked.append(line.rstrip().rstrip("|").rstrip() + f" {mark} |")
            else:
                marked.append(line)
        parsed = LS.parse_marks_markdown("\n".join(marked))
        assert parsed[1] == {"mark": "C", "note": None} and parsed[38] == {"mark": "N", "note": "homonym"}
        folded = LS.fold_marks(key, parsed)
        assert (folded["confirmed"], folded["rejected"], folded["unsure"]) == (37, 2, 1)
        assert folded["precision"] == round(37 / 39, 4) and folded["build"]
        assert "build the integration" in folded["line"]
        few = LS.fold_marks(k3, {1: {"mark": "C"}, 2: {"mark": "C"}, 3: {"mark": "N"}})
        assert not few["build"] and "stop" in few["line"]
        assert LS.parse_marks_markdown("| 1 | a | b | c | d |  |")[1] == {"mark": None, "note": None}
        assert LS.parse_marks_markdown("| 2 | a | b | c | d | covered, but narrower |")[2]["mark"] == "C"


class TestDryReadout:
    def test_free_labels_and_the_audit_list(self):
        kept = {"pleasant#1": row("pleasant", block(), review={"status": "merged_into", "into": "trait:alpha"}),
                "annoying#1": row("annoying", block())}
        lk = LX.build_lookup(CORPUS, ENTRIES, lexicons={"oewn": FakeLexicon(links={"pleasant": {"also": ["alpha"]},
                                                                                   "annoying": {"similar": ["beta"]}})})
        items, plans = LS.sweep_plan(kept, lk)
        r = LS.dry_readout(kept=kept, items=items, plans=plans, lookup=lk, estimate=LS.sweep_estimate(len(items)))
        assert r["pairs"]["n_pairs"] == 2 and r["pairs"]["by_link"] == {"also": 1, "similar": 1}
        assert r["free_labels"]["lexical_target_merges"] == {"pleasant#1": "alpha"}
        assert not r["audit_retrieval_misses"]["pleasant#1"]["reached"]                    # the audit's trait is agreeable
        assert r["audit_retrieval_misses"]["nice#1"]["in_sweep"] is False
        assert r["estimate"]["opus_share_assumed"] == [0.4, 0.62]
        md = LS.dry_markdown(r)
        assert "gate 1" in md and "[alpha](../../traits/instructions/alpha.json)" in md
