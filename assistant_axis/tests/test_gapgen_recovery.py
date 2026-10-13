"""The recovery harness's library (``assistant_axis/gapgen/recovery.py``; coding_plan_platform.md, "The recovery
harness"): the hiding groups and the seeded, stratified draw (a hidden pair hides whole), the reduced corpus
and label sets, the match (a label that is a hidden stem recovers without a call; the overlap call under the
pipeline's rule; a candidate covered by a remaining trait does not count), the figures and the report.  No API
calls: the fake client and the toy corpus of the novelty tests."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import recovery as RC
from assistant_axis.tests.fake_anthropic import user_text
from assistant_axis.tests.test_gapgen_novelty import (
    R1, R2, cand, make_runner, query, responder_for, toy_index, write_corpus,
)

REPO = Path(__file__).resolve().parents[2]
TOY_GROUPS = [["alpha", "beta", "gamma"], ["delta", "epsilon"], ["eta"], ["iota", "theta"], ["kappa"], ["lambda_mu"],
              ["zeta"]]
TOY_REGIONS = {"alpha": "moral_stance", "beta": "moral_stance", "gamma": "moral_stance", "delta": "cognitive_epistemic",
               "epsilon": "cognitive_epistemic", "theta": "communication_style", "iota": "communication_style",
               "zeta": "cognitive_epistemic", "eta": "cognitive_epistemic", "kappa": None, "lambda_mu": "moral_stance"}


def toy(tmp_path, **kw):
    data = write_corpus(tmp_path / "data", **kw)
    traits = NV.load_trait_corpus(data)
    return data, traits, RC.arrangement_kinds(data, traits)


# --------------------------------------------------------------------------- 1. hide

class TestHide:
    def test_hiding_groups_keep_arrangements_together(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        assert RC.hiding_groups(traits) == TOY_GROUPS        # a sequence's members (zeta, eta, kappa) stand alone
        assert kinds == {"alpha": "triangle", "beta": "triangle", "gamma": "triangle", "delta": "pair",
                         "epsilon": "pair", "theta": "pair", "iota": "pair", "zeta": "sequence", "eta": "sequence",
                         "kappa": "sequence", "lambda_mu": "singleton"}

    def test_hiding_groups_partition_a_corpus_recorded_on_one_side_only(self, tmp_path):
        """A pair recorded in one member's file only (a corpus mid-edit): before 2026-10-12 the walk followed
        ``expands_to`` one way, so the member sorted first formed a group alone and then appeared again in its
        partner's group."""
        from dataclasses import replace
        _, traits, _ = toy(tmp_path)
        one_sided = dict(traits)
        one_sided["delta"] = replace(traits["delta"], expands_to=[])          # epsilon still names delta
        groups = RC.hiding_groups(one_sided)
        members = [s for g in groups for s in g]
        assert sorted(members) == sorted(traits) and len(members) == len(set(members))
        assert ["delta", "epsilon"] in groups and groups == RC.hiding_groups(traits) == TOY_GROUPS

    def test_a_hidden_pair_hides_whole(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        seen_alone = set()
        for seed in range(40):
            d = RC.draw_hidden(traits, frac=0.3, seed=seed, regions=TOY_REGIONS, kinds=kinds)
            hid = set(d["hidden"])
            for g in TOY_GROUPS:                                  # every group hidden whole or not at all
                assert set(g) <= hid or not set(g) & hid, (seed, g)
            assert sorted(m for g in d["groups"] for m in g["members"]) == d["hidden"]
            assert d["n_hidden"] == len(hid) and all(d["traits"][s]["kind"] == kinds[s] for s in hid)
            if "zeta" in hid and not {"eta", "kappa"} & hid:
                seen_alone.add("zeta")
        assert seen_alone == {"zeta"}                             # a sequence member hides alone

    def test_quotas_by_stratum(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        assert RC.stratum_quotas({"a": 10, "b": 7, "c": 3}, 0.1) == {"a": 1, "b": 1, "c": 0}
        assert sum(RC.stratum_quotas({"a": 157, "b": 177, "c": 3, "d": 83}, 0.1).values()) == 42
        d = RC.draw_hidden(traits, frac=0.5, seed=3, regions=TOY_REGIONS, kinds=kinds)
        assert d["n_target"] == 6 and sum(v["quota"] for v in d["strata"].values()) == 6
        for name, v in d["strata"].items():
            assert v["n_hidden"] >= v["quota"] and v["n_hidden"] - v["quota"] < 3      # overshoot under a group
        assert set(d["strata"]) == {"moral_stance", "cognitive_epistemic", "communication_style", "none"}
        assert d["traits"].get("kappa", {}).get("stratum", "none") == "none"           # no region: its own stratum

    def test_the_draw_is_seeded(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        a = RC.draw_hidden(traits, frac=0.3, seed=1, regions=TOY_REGIONS, kinds=kinds)
        assert a == RC.draw_hidden(traits, frac=0.3, seed=1, regions=TOY_REGIONS, kinds=kinds)
        draws = {tuple(RC.draw_hidden(traits, frac=0.3, seed=s, regions=TOY_REGIONS, kinds=kinds)["hidden"])
                 for s in range(10)}
        assert len(draws) > 1
        with pytest.raises(ValueError):
            RC.draw_hidden(traits, frac=1.5, seed=0, regions=TOY_REGIONS, kinds=kinds)

    def test_write_and_load_hidden(self, tmp_path):
        data, traits, kinds = toy(tmp_path)
        regions = tmp_path / "regions.json"
        regions.write_text(json.dumps({"result": {s: {"region": r} for s, r in TOY_REGIONS.items()}}))
        assert RC.load_regions(regions) == TOY_REGIONS and RC.load_regions(tmp_path / "none.json") == {}
        d = RC.draw_hidden(traits, frac=0.3, seed=0, regions=RC.load_regions(regions), kinds=kinds)
        doc = RC.write_hidden(tmp_path / "x" / "hidden.json", d, data_dir=data, regions_path=regions, git_sha="abc")
        assert doc["corpus"]["n_trait_files"] == 11 and doc["regions_file"]["sha256"] == RC.file_sha256(regions)
        h = RC.load_hidden(tmp_path / "x" / "hidden.json")
        assert h["stems"] == d["hidden"] and h["sha256"] == RC.file_sha256(tmp_path / "x" / "hidden.json")
        (tmp_path / "bad.json").write_text(json.dumps({"hidden": "alpha"}))
        with pytest.raises(ValueError):
            RC.load_hidden(tmp_path / "bad.json")

    def test_the_real_corpus(self):
        """Today's corpus and regions: about a tenth hidden, every recorded pair and simplex whole, every region
        drawing its share."""
        data = REPO / "data"
        traits = NV.load_trait_corpus(data)
        kinds = RC.arrangement_kinds(data, traits)
        regions = RC.load_regions(data / "candidates" / "corpus_regions.json")
        d = RC.draw_hidden(traits, frac=0.1, seed=0, regions=regions, kinds=kinds)
        hid = set(d["hidden"])
        assert d["n_target"] <= d["n_hidden"] <= d["n_target"] + len(d["strata"]) * 3
        for s in hid:
            assert set(traits[s].expands_to) <= hid, s            # partners hidden together
        assert {"pair", "singleton"} <= {d["traits"][s]["kind"] for s in hid}
        assert all(v["n_hidden"] >= v["quota"] for v in d["strata"].values())


# --------------------------------------------------------------------------- 2. the reduced corpus

class TestReducedCorpus:
    def test_hidden_traits_leave_the_corpus_and_their_partners(self, tmp_path):
        _, traits, _ = toy(tmp_path, renamed={"gamma": "old_gamma"})
        red = RC.reduced_traits(traits, ["delta", "epsilon", "alpha", "beta", "gamma"])
        assert set(red) == set(traits) - {"delta", "epsilon", "alpha", "beta", "gamma"}
        assert red["theta"].partners == ["iota"]                  # untouched
        part = RC.reduced_traits(traits, ["delta"])               # a hand-made list hiding one end of a pair
        assert part["epsilon"].pair_partner is None and part["epsilon"].partners == [] and part["epsilon"].expands_to == []
        assert traits["epsilon"].pair_partner == "delta"          # the full corpus is not changed
        with pytest.raises(ValueError, match="not in the corpus"):
            RC.reduced_traits(traits, ["delta", "nope"])

    def test_the_exact_label_check_forgets_them(self, tmp_path):
        _, traits, _ = toy(tmp_path, renamed={"gamma": "old_gamma"})
        queue = {"entries": [{"stem": "gamma", "label": "gamma", "status": "exists", "entity_type": "trait"},
                             {"stem": "queued", "label": "Queued One", "status": "candidate", "entity_type": "trait"}]}
        hid = ["alpha", "beta", "gamma"]
        sets = RC.reduced_label_sets(RC.reduced_traits(traits, hid), queue, hid)
        assert NV.exact_label_match("gamma", sets) is None        # not the corpus, not the queue's entry for it
        assert NV.renamed_match("old_gamma", sets) is None        # nor its former stem
        assert NV.exact_label_match("delta", sets)["match"] == "corpus"
        assert NV.exact_label_match("queued_one", sets)["match"] == "queue"
        full = NV.label_sets(traits, queue)
        assert NV.exact_label_match("gamma", full)["match"] == "corpus"

    def test_an_index_without_them(self, tmp_path):
        import numpy as np
        _, traits, _ = toy(tmp_path)
        red = RC.reduced_traits(traits, ["alpha", "beta", "gamma"])
        idx = NV.build_index(red, np.eye(12)[[i for i, s in enumerate(sorted(traits)) if s in red]], variant="raw")
        q = idx.project(query(alpha=0.9, beta=0.8, delta=0.5, zeta=0.4))
        listed = NV.expand(idx.retrieve(q, 3), idx.traits, lambda s: idx.cosine_to(q, s))
        assert not {"alpha", "beta", "gamma"} & {x.stem for x in listed}


# --------------------------------------------------------------------------- 3. match

def test_label_matches():
    t = {"self_aware": NV.CorpusTrait(stem="self_aware", label="self-aware", description="d", negative_label=None,
                                      pair_partner=None, partners=[], expands_to=[], renamed_from=["self_conscious"])}
    assert RC.label_matches("self_aware", t) == [{"stem": "self_aware", "match": "stem"}]
    assert RC.label_matches("selfaware", t) == [{"stem": "self_aware", "match": "stem", "blind": True}]
    assert RC.label_matches("self_conscious", t) == [{"stem": "self_aware", "match": "renamed_from",
                                                      "old_stem": "self_conscious"}]
    assert RC.label_matches("aware", t) == []


HIDDEN = ["alpha", "beta", "gamma", "lambda_mu"]
OV = {("candidate a", "beta", "sonnet"): 4,                                         # recovers beta, no Opus
      ("candidate b", "alpha", "sonnet"): 3, ("candidate b", "alpha", "opus"): 3,   # c = 3: Opus decides, covers
      ("candidate c", "alpha", "sonnet"): 3, ("candidate c", "alpha", "opus"): 4}   # c = 4: Sonnet c - 1, Opus at c


def match_setup(tmp_path, responder=None):
    r, client, idx = make_runner(tmp_path, responder or responder_for({}, OV))
    cs = [cand("gamma"), cand("candidate a"), cand("candidate b"), cand("candidate c", a=3), cand("candidate d")]
    vec = {cs[0].key: query(gamma=0.9, zeta=0.5, eta=0.4, kappa=0.3),       # its own label: no call
           cs[1].key: query(beta=0.9, zeta=0.5, eta=0.4, kappa=0.3),
           cs[2].key: query(zeta=0.9, alpha=0.6, eta=0.4, kappa=0.3),       # covered by zeta in the reduced run
           cs[3].key: query(alpha=0.9, zeta=0.5, eta=0.4, kappa=0.3),
           cs[4].key: query(zeta=0.9, eta=0.8, kappa=0.7, theta=0.6)}       # no hidden trait near
    dec = {cs[0].key: {"decision": "new"}, cs[1].key: {"decision": "new"},
           cs[2].key: {"decision": "covered", "covered_by": "zeta"}, cs[3].key: {"decision": "grey"},
           cs[4].key: {"decision": "new"}}
    return r, client, cs, vec, dec


def hidden_doc(groups=(("alpha", "beta", "gamma"), ("lambda_mu",))):
    kinds = {"alpha": "triangle", "beta": "triangle", "gamma": "triangle", "lambda_mu": "singleton"}
    traits = {s: {"region": TOY_REGIONS[s], "stratum": TOY_REGIONS[s] or "none", "kind": kinds[s], "group": i}
              for i, g in enumerate(groups) for s in g}
    return {"seed": 0, "hidden_frac": 0.3, "n_corpus": 11, "n_target": 3, "n_hidden": len(traits), "n_groups": len(groups),
            "hidden": sorted(traits), "groups": [{"members": list(g), "stratum": "x", "kind": kinds[g[0]]} for g in groups],
            "strata": {}, "traits": traits}


class TestMatch:
    def test_label_overlap_and_the_rule(self, tmp_path):
        r, client, cs, vec, dec = match_setup(tmp_path)
        rows, near = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=R2)
        by = {(x["key"], x["stem"]): x for x in rows}
        # a candidate whose label is a hidden stem is recovered without a call
        g = by[("gamma#1", "gamma")]
        assert g["how"] == "label" and g["recovers"] and g["match"] == {"stem": "gamma", "match": "stem"}
        targets = [json.loads(user_text(k))["target"]["label"] for k in client.calls]
        assert "gamma" not in targets and "candidate d" not in targets
        # recovered by the overlap call: Sonnet above the cut-off, no Opus
        a = by[("candidate_a#1", "beta")]
        assert a["how"] == "overlap" and a["recovers"] and a["verdict"] == "cut" and a["opus"] is None and a["rank"] == 1
        # Sonnet at the cut-off, Opus at it: covers
        b = by[("candidate_b#1", "alpha")]
        assert b["recovers"] and b["opus"]["value"] == 3 and b["decision"] == "covered" and b["covered_by"] == "zeta"
        # Sonnet one below (cut-off 4), Opus at it: covers under rule set 2 (decision 12)
        c = by[("candidate_c#1", "alpha")]
        assert c["cut_off"] == 4 and c["verdict"] == "review" and c["recovers"]
        assert {x["key"] for x in rows} == {"gamma#1", "candidate_a#1", "candidate_b#1", "candidate_c#1"}
        assert near["candidate_d#1"] == [] and near["gamma#1"] == ["gamma"]
        assert {x["wave"] for x in r.records} == {"m_sonnet", "m_opus"}
        assert {x["key"] for x in r.records if x["role"] == "opus"} == {"candidate_b#1", "candidate_c#1"}
        assert r.usage.total_cost_usd > 0

    def test_rule_set_1_does_not_cover_on_the_opus_check(self, tmp_path):
        r, _, cs, vec, dec = match_setup(tmp_path)
        rows, _ = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=R1)
        assert not next(x for x in rows if x["key"] == "candidate_c#1")["recovers"]

    def test_a_failed_request_leaves_the_pair_stalled(self, tmp_path):
        good = responder_for({}, OV)

        def flaky(kw):
            if json.loads(user_text(kw))["target"]["label"] == "candidate a":
                return RuntimeError("network down")
            return good(kw)
        r, _, cs, vec, dec = match_setup(tmp_path, flaky)
        rows, _ = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=R2)
        a = next(x for x in rows if x["key"] == "candidate_a#1")
        assert a["stalled"].startswith("Sonnet on beta") and not a["recovers"]

    def test_a_resume_sends_nothing_again(self, tmp_path):
        r, client, cs, vec, dec = match_setup(tmp_path)
        rows, _ = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=R2)
        r2, client2, _ = make_runner(tmp_path / "again", responder_for({}, OV), records=r.records)
        rows2, _ = RC.match_candidates(r2, cs, vec, HIDDEN, k=4, decisions=dec, rules=R2)
        assert client2.calls == [] and rows2 == rows


# --------------------------------------------------------------------------- 3b. Opus at the strict cut-off

#: Candidate a (cut-off 3) is read Sonnet 4 on beta: Sonnet covers alone there, so the rule asks no Opus; at the
#: strict column's fixed 4 the same reading needs Opus to decide.  Its Opus (asked only at the strict cut-off) reads 2.
OV_STRICT = OV | {("candidate a", "beta", "opus"): 2}


def pairs_called(client) -> list[tuple]:
    out = []
    for kw in client.calls:
        u = json.loads(user_text(kw))
        out.append((u["target"]["label"], u["other"]["label"], "opus" if "opus" in kw["model"] else "sonnet"))
    return sorted(out)


def recorded_batch(root: Path, rows, cs, dec, rules=R2) -> Path:
    """The match stage's rows as a recorded harness batch (``recovery_extras`` reads it): ``recovery/B/seed0`` and
    the reduced run's results and rules in ``novelty/B_s0``."""
    from assistant_axis.gapgen.testing import recovery_extras as RX
    sd = root / "recovery" / "B" / "seed0"
    sd.mkdir(parents=True)
    (sd / "matches.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (sd / "hidden.json").write_text(json.dumps(hidden_doc()))
    nd = root / "novelty" / "B_s0"
    nd.mkdir(parents=True)
    (nd / "results.jsonl").write_text("".join(json.dumps({"key": c.key, "novelty": dec[c.key]}) + "\n" for c in cs))
    (nd / "run.json").write_text(json.dumps({"rules": rules.as_dict()}))
    (root / "recovery" / "B" / "run.json").write_text("{}")
    assert RX.m3_dir_for(sd) == nd
    return root / "recovery" / "B"


class TestStrictCutOffOpus:
    """``match_candidates(opus_also_at=4)`` (2026-10-13; ``recovery_test.match_seed`` passes ``STRICT_C``): Opus is
    also asked where the strict column's cut-off needs it, the headline verdicts are unchanged, ``needs_opus`` is
    empty, and a resume of a batch matched without it sends only the missing Opus calls."""

    def run(self, tmp_path, records=(), **kw):
        r, client, cs, vec, dec = match_setup(tmp_path, responder_for({}, OV_STRICT))
        if records:
            r, client, _ = make_runner(tmp_path / "resumed", responder_for({}, OV_STRICT), records=records)
        rows, _ = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=R2, **kw)
        return r, client, rows, cs, dec

    def test_off_nothing_changes(self, tmp_path, monkeypatch):
        """Keyword off (M3's own path and the default): the same calls and byte-identical records."""
        from assistant_axis.gapgen import novelty_runner as NR
        monkeypatch.setattr(NR, "utc_now", lambda: "2026-10-13T00:00:00+00:00")
        out = []
        for name, kw in (("omitted", {}), ("none", {"opus_also_at": None})):
            r, client, rows, _, _ = self.run(tmp_path / name, **kw)
            out.append((rows, pairs_called(client), r.responses_path.read_bytes()))
        assert out[0] == out[1]
        rows, called, _ = out[0]
        assert ("candidate a", "beta", "opus") not in called                       # Sonnet 4 at c = 3 covers alone
        assert [c for c in called if c[2] == "opus"] == [("candidate b", "alpha", "opus"),
                                                          ("candidate c", "alpha", "opus")]
        assert next(x for x in rows if x["key"] == "candidate_a#1")["opus"] is None

    def test_m3s_full_scan_asks_no_opus_above_the_cut_off(self, tmp_path):
        """The full scan (``read_pairs`` without the keyword): a Sonnet 4 at cut-off 3 goes to no Opus."""
        r, _, _ = make_runner(tmp_path, responder_for({}, {("candidate a", "alpha", "sonnet"): 4}),
                              mode="full_scan")
        c = cand("candidate a")
        st = r.run([c], {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)})[c.key]
        assert st.block["decision"] == "covered" and not [x for x in r.records if x["role"] == "opus"]

    def test_on_the_strict_reading_is_asked_and_the_headline_is_unchanged(self, tmp_path):
        from assistant_axis.gapgen.testing import recovery_extras as RX
        _, _, off, cs, dec = self.run(tmp_path / "off")
        r, client, on, _, _ = self.run(tmp_path / "on", opus_also_at=RX.STRICT_C)
        assert pairs_called(client).count(("candidate a", "beta", "opus")) == 1
        assert [c for c in pairs_called(client) if c[2] == "opus"] == [
            ("candidate a", "beta", "opus"), ("candidate b", "alpha", "opus"), ("candidate c", "alpha", "opus")]
        a = next(x for x in on if x["key"] == "candidate_a#1")
        assert a["sonnet"]["value"] == 4 and a["opus"]["value"] == 2
        # the verdict at the candidate's own cut-off (3) does not read the strict Opus: Sonnet 4 still covers
        assert a["cut_off"] == 3 and a["verdict"] == "cut" and a["recovers"]
        strip = [{k: v for k, v in x.items() if k != "opus"} for x in on]
        assert strip == [{k: v for k, v in x.items() if k != "opus"} for x in off]   # every headline field the same
        assert {x["wave"] for x in r.records} == {"m_sonnet", "m_opus"}               # one Opus wave, as before
        # the strict column: listed as needing Opus without the keyword, complete with it
        ex_off = RX.extras_json(recorded_batch(tmp_path / "b_off", off, cs, dec))
        ex_on = RX.extras_json(recorded_batch(tmp_path / "b_on", on, cs, dec))
        assert ex_off["needs_opus"] == [{"key": "candidate_a#1", "stem": "beta", "sonnet": 4, "cut_off": 3, "seed": 0}]
        assert ex_on["needs_opus"] == [] and ex_on["n_needs_opus"] == 0
        st = ex_on["seeds"][0]["strict"]
        assert st["n_recovered_headline"] == 3 and "beta" in st["lost_at_strict"]   # Opus 2: not at 4

    def test_a_resume_of_a_batch_matched_without_it_sends_only_the_missing_opus(self, tmp_path):
        from assistant_axis.gapgen.testing import recovery_extras as RX
        r0, client0, _, _, _ = self.run(tmp_path / "first")
        assert client0.calls
        r1, client1, on, _, _ = self.run(tmp_path / "first", records=r0.records, opus_also_at=RX.STRICT_C)
        assert pairs_called(client1) == [("candidate a", "beta", "opus")]
        assert [x["role"] for x in r1.records[len(r0.records):]] == ["opus"]          # one new record, appended
        assert next(x for x in on if x["key"] == "candidate_a#1")["opus"]["value"] == 2
        r2, client2, again, _, _ = self.run(tmp_path / "first", records=r1.records, opus_also_at=RX.STRICT_C)
        assert client2.calls == [] and again == on                                   # and then nothing

    def test_a_strict_only_opus_without_an_answer_leaves_the_headline(self, tmp_path):
        """An Opus call asked only for the strict cut-off that fails outright leaves ``opus`` None (listed in
        ``needs_opus``; a resume asks it again); one the rule itself needs stalls the pair, as before."""
        from assistant_axis.gapgen.testing import recovery_extras as RX
        good = responder_for({}, OV_STRICT)

        def flaky(kw):
            if "opus" in kw["model"] and json.loads(user_text(kw))["target"]["label"] in ("candidate a", "candidate b"):
                return RuntimeError("network down")
            return good(kw)
        _, _, off, _, _ = self.run(tmp_path / "off")
        r, _, cs, vec, dec = match_setup(tmp_path / "on", flaky)
        on, _ = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=R2, opus_also_at=RX.STRICT_C)
        a = next(x for x in on if x["key"] == "candidate_a#1")
        assert a == next(x for x in off if x["key"] == "candidate_a#1")              # Sonnet 4 still covers at 3
        assert a["opus"] is None and a["recovers"] and "stalled" not in a
        assert next(x for x in on if x["key"] == "candidate_b#1")["stalled"].startswith("Opus on alpha")
        ex = RX.extras_json(recorded_batch(tmp_path / "b", on, cs, dec))
        assert [(x["key"], x["stem"]) for x in ex["needs_opus"]] == [("candidate_a#1", "beta")]


# --------------------------------------------------------------------------- 4. report

class TestFigures:
    def figures(self, tmp_path, rules=R2):
        r, _, cs, vec, dec = match_setup(tmp_path)
        rows, near = RC.match_candidates(r, cs, vec, HIDDEN, k=4, decisions=dec, rules=rules)
        results = [{"key": c.key, "label": c.label, "novelty": dec[c.key]} for c in cs]
        return RC.seed_figures(hidden_doc(), results, rows, near=near, reduced_run={"batch_id": "rec_s0"},
                               cost={"total_usd": 0.5})

    def test_the_counts(self, tmp_path):
        f = self.figures(tmp_path)
        k = f["kept"]
        # kept: gamma (label), candidate a (beta), candidate c (alpha, grey), candidate d (nothing near)
        assert k["n_hidden"] == 4 and k["n_recovered"] == 3 and k["recall"] == 0.75
        assert k["by_label"] == 1 and k["by_overlap_only"] == 2
        assert k["candidates"] == {"n": 4, "n_recovering": 3, "precision": 0.75}
        assert k["groups"] == {"n": 1, "whole": 1, "partial": 0, "none": 0}             # the triangle, all three
        assert k["by_region"] == {"moral_stance": {"n_hidden": 4, "n_recovered": 3, "recall": 0.75}}
        assert k["by_kind"]["triangle"]["recall"] == 1.0 and k["by_kind"]["singleton"]["n_recovered"] == 0
        assert [x["stem"] for x in k["recovered"]] == ["alpha", "beta", "gamma"]
        # a candidate decided covered by a remaining trait does not count for recall ...
        assert all(b["key"] != "candidate_b#1" for x in k["recovered"] for b in x["by"])
        # ... it is a false cover, of a trait a kept candidate recovered anyway
        c = f["covered"]
        assert c["n_false_cover_candidates"] == 1 and c["false_covers"][0]["stem"] == "alpha"
        assert c["false_covers"][0]["covered_by"] == "zeta" and c["false_covers"][0]["recovered_by_a_kept_candidate"]
        assert c["hidden_missed_only_through_covers"] == [] and c["candidates"]["n"] == 1
        assert f["either"]["n_recovered"] == 3
        assert f["reachable"] == {"n": 3, "share": 0.75, "n_by_kept": 3, "share_by_kept": 0.75}
        assert f["candidates"]["by_decision"] == {"new": 3, "covered": 1, "grey": 1}
        assert f["pairs"]["n_label"] == 1 and f["pairs"]["n_overlap"] == 3

    def test_under_rule_set_1_the_cover_is_the_only_way_to_alpha(self, tmp_path):
        f = self.figures(tmp_path, rules=R1)
        assert f["kept"]["n_recovered"] == 2 and f["kept"]["groups"]["partial"] == 1
        assert f["covered"]["hidden_missed_only_through_covers"] == ["alpha"]
        assert f["either"]["n_recovered"] == 3

    def test_combine_and_markdown(self, tmp_path):
        a = self.figures(tmp_path / "a")
        b = self.figures(tmp_path / "b", rules=R1)
        rep = RC.combine_seeds([a | {"seed": 0}, b | {"seed": 1}])
        assert rep["mean"]["recall_kept"] == pytest.approx(0.625) and rep["n_seeds"] == 2
        assert rep["total_cost_usd"] == 1.0 and rep["mean"]["kept_by_kind"]["triangle"]["recall"] == pytest.approx(5 / 6, abs=1e-4)
        md = RC.report_markdown(rep, batch_id="rec_toy", generator="toy", run_id="r1", labels={"alpha": "alpha"})
        assert "| 0 | 4 of 11 | 4 | 75.0% (3) | 1 | 75.0% |" in md and "| mean |" in md
        assert "[alpha](../../../traits/instructions/alpha.json)" in md and "### False covers (1 candidates)" in md
        assert "[hidden.json](./seed0/hidden.json)" in md and "(../../novelty/rec_s0/decisions.md)" in md
        assert "### Not recovered (1)" in md and "[lambda mu](../../../traits/instructions/lambda_mu.json)" in md
        assert "## Recall by region" in md and "## Recall by arrangement kind" in md


# --------------------------------------------------------------------------- the match stage's view of the cache

def test_the_match_stage_reads_the_vectors_the_m3_run_saved(tmp_path, monkeypatch):
    """``recovery_test.match_seed`` reads the embedding cache afresh (Fable review S4.2, 2026-10-14): the harness's
    cache object loaded its table before the reduced-corpus M3 run, which embedded the candidate texts and saved
    them; the match stage must take those vectors from disk and embed nothing (no second charge, and a resume
    plans on the same vectors)."""
    import numpy as np
    from types import SimpleNamespace
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen import paths
    from assistant_axis.gapgen.metric_config import MetricConfig
    from data_analysis.gap_generation import recovery_test as RT

    cfg = MetricConfig.load(paths.METRIC_CONFIG_PATH)
    cands = [cand("candidate a"), cand("candidate b")]
    m3_dir, seed_dir = tmp_path / "novelty" / "B_s0", tmp_path / "recovery" / "B" / "seed0"
    m3_dir.mkdir(parents=True)
    seed_dir.mkdir(parents=True)
    (m3_dir / "results.jsonl").write_text("".join(json.dumps(
        {"key": c.key, "stem": c.stem, "label": c.label, "gloss": c.gloss, "generators": ["g"],
         "novelty": {"decision": "new", "alignment_score": 0, "region": None}}) + "\n" for c in cands))
    (m3_dir / "run.json").write_text(json.dumps({"rules": NV.RULES[3].as_dict(), "settings": {"query_form": NV.DEFAULT_QUERY_FORM}}))
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    texts = [NV.query_text(c.label, c.gloss, query_form=NV.DEFAULT_QUERY_FORM, representation=cfg.representation) for c in cands]

    harness_cache = EM.EmbeddingCache(tmp_path / "cache")
    assert harness_cache.lookup(embedder.tag, texts)[1] == [0, 1]       # the table, read before M3 ran: empty
    saved = np.random.default_rng(0).normal(size=(2, 8)).astype(np.float32)
    m3_cache = EM.EmbeddingCache(tmp_path / "cache")                     # the M3 run's own cache embeds and saves
    m3_cache.put(embedder.tag, texts, saved, model_id=embedder.model_id)
    m3_cache.save()

    sent = []

    def no_call(self, batch):
        sent.append(list(batch))
        return np.ones((len(batch), 8), np.float32), 10
    monkeypatch.setattr(EM.OpenAIEmbedder, "embed_batch", no_call)
    monkeypatch.setattr(RT.NS, "load_index", lambda *a, **k: (None, {}))
    seen = {}

    class Planned(Exception):
        pass

    def plan(cs, vectors, index, hidden, *, k):
        seen["vectors"] = vectors
        raise Planned
    monkeypatch.setattr(RT.RC, "match_plan", plan)
    args = SimpleNamespace(resume=False, query_form=NV.DEFAULT_QUERY_FORM, data_dir=tmp_path, transport="live", concurrency=1)
    with pytest.raises(Planned):
        RT.match_seed(args, seed=0, seed_dir=seed_dir, hidden_doc={"hidden": []}, m3_dir=m3_dir, cfg=cfg,
                      cache=harness_cache, rubrics={}, budget=1.0)
    assert sent == []                                                    # nothing embedded again
    unit = EM.normalize_rows(saved)
    for i, c in enumerate(cands):
        assert np.allclose(seen["vectors"][c.key], unit[i])              # the M3 run's vectors, as saved
