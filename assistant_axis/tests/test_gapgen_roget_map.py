"""Two-route mapping of labels onto Roget heads (workstream 2, plan § 8 "Mapping", revised: the
rule of ``mapping.resolve`` replaces the LLM adjudication)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen.embed import EmbeddingCache, HashEmbedder
from assistant_axis.gapgen.generators.roget import mapping as M
from assistant_axis.gapgen.generators.roget import parse as P
from assistant_axis.gapgen.generators.roget import wn_clusters as W
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.roget_fakes import make_index, small_wordnet

FIXTURE = Path(__file__).parent / "fixtures" / "roget_sample.txt"


@pytest.fixture(scope="module")
def fx():
    return P.parse_roget(FIXTURE.read_text(encoding="utf-8"))


def rec(label, desc=None, source="existing", status=None):
    from assistant_axis.entity_id import normalize_to_file_name
    return M.LabelRecord(normalize_to_file_name(label), label, desc, source, status)


def test_key_forms():
    assert M.key_forms("risk-averse") == ["risk-averse", "risk averse", "riskaverse"]
    assert M.key_forms("openness (Big Five)") == ["openness"]
    assert M.key_forms("Kind to Animals")[:2] == ["kind to animals", "kind-to-animals"]


def test_derived_forms_suffixes_and_wordnet():
    assert "caution" in M.derived_forms("cautious")
    assert "cautiousness" in M.derived_forms("cautious")
    assert "absolutism" in M.derived_forms("absolutist")
    assert "absolutist" in M.derived_forms("absolutism")
    assert "obstinacy" in M.derived_forms("obstinate")
    assert M.derived_forms("risk averse") == []
    lex = W.Lexicon(small_wordnet())
    assert M.derived_forms("cautious", lex)[0] == "caution"       # WordNet's derivation first


def test_lexical_route_on_fixture_heads(fx):
    li = M.LexIndex(fx)
    hits = M.lexical_route(rec("cautious"), li)
    assert (hits[0].head_id, hits[0].strength) == ("864", "exact_adj")
    hits = M.lexical_route(rec("resolution"), li)
    assert (hits[0].head_id, hits[0].strength) == ("604", "exact_noun")
    assert ("606", "loose") in [(h.head_id, h.strength) for h in hits]     # "dogged resolution"
    hits = M.lexical_route(rec("determinedness"), li)
    assert (hits[0].head_id, hits[0].strength) == ("604", "derived_adj")
    hits = M.lexical_route(rec("willed"), li)
    assert {h.strength for h in hits} == {"loose"} and hits[0].item == "strong-willed"


def test_lexical_route_ranks_dispositional_heads_first():
    idx = make_index([{"id": "1", "title": "Coldness", "adj": [["cool"]], "klass": "I"},
                      {"id": "826", "title": "Inexcitability", "adj": [["calm"], ["cool"]], "klass": "VI"}])
    hits = M.lexical_route(rec("cool"), M.LexIndex(idx))
    assert [h.head_id for h in hits] == ["826", "1"]
    hits = M.lexical_route(rec("cool"), M.LexIndex(idx), dispositional=["1"])
    assert [h.head_id for h in hits] == ["1", "826"]                       # extra counts as dispositional


def L(head, strength="exact_adj", disp=True, gi=0):
    return M.LexHit(head, strength, "w", "Adj", gi, disp)


def S(*heads_sims):
    return [M.SemHit(h, s, i + 1) for i, (h, s) in enumerate(heads_sims)]


def test_agreement_truth_table():
    sem = S(("a", 0.6), ("b", 0.5), ("c", 0.45), ("d", 0.4), ("e", 0.39))
    a = M.agreement([L("b"), L("e")], sem)
    assert (a.primary, a.secondary, a.route, a.confidence) == ("b", ["e"], "agree", 1.0)
    assert M.agreement([L("d")], sem) is None                 # lexical hits none in the top three
    assert M.agreement([], sem) is None                       # no lexical hit
    a = M.agreement([L("x"), L("c")], sem)                    # the first lexical hit in the top three wins
    assert a.primary == "c"


def test_resolve_rules():
    sem = S(("a", 0.6), ("b", 0.5), ("c", 0.45), ("d", 0.42), ("e", 0.41))
    assert M.resolve([L("d"), L("e")], sem).route == "rule"
    r = M.resolve([L("d"), L("e")], sem)
    assert (r.primary, r.secondary) == ("d", ["e"])
    r = M.resolve([L("z")], sem)
    assert (r.primary, r.route) == ("a", "semantic")
    low = S(("a", 0.3), ("b", 0.2))
    r = M.resolve([L("z", disp=True)], low)
    assert (r.primary, r.route) == ("z", "lexical")
    assert M.resolve([L("z", "loose")], low).route == "none"
    assert M.resolve([L("z", disp=False)], low).route == "none"
    assert M.resolve([], low).primary is None


def test_semantic_route_with_hash_embedder(fx, tmp_path):
    usage = MultiModelUsage()
    recs = [rec("cautious", "This means being wary and careful, prudent and discreet."),
            rec("obstinate", "This means being stubborn, headstrong and inflexible.")]
    heads = list(fx.order)
    out = M.semantic_route(recs, fx, heads, embedder=HashEmbedder(), cache=EmbeddingCache(tmp_path), usage=usage)
    for r in recs:
        hits = out[r.stem]
        assert len(hits) == 5 and [h.rank for h in hits] == [1, 2, 3, 4, 5]
        assert [h.sim for h in hits] == sorted([h.sim for h in hits], reverse=True)
    assert out["cautious"][0].head_id == "864"
    assert usage.n_calls == 2


class StubEmbedder:
    """Vectors chosen per text (``table``); anything else is the noise direction."""
    name, model_id, tag, usage_model, max_batch = "stub", "stub", "stub", "bge-large", 100

    def __init__(self, table, dim):
        self.table, self.dim = table, dim

    def embed_batch(self, texts):
        out = []
        for t in texts:
            v = np.zeros(self.dim)
            v[-1] = 1e-9
            for k, w in self.table.get(t, {self.dim - 1: 1.0}).items():
                v[k] += w
            out.append(v)
        return np.asarray(out, dtype=np.float32), len(texts)


def test_map_labels_end_to_end_every_route():
    idx = make_index([
        {"id": "864", "title": "Caution", "adj": [["cautious", "wary"], ["careful"]], "noun": [["caution"]], "klass": "VI"},
        {"id": "863", "title": "Rashness", "adj": [["rash", "reckless"]], "klass": "VI"},
        {"id": "861", "title": "Courage", "adj": [["brave", "bold"]], "klass": "VI"},
        {"id": "862", "title": "Cowardice", "adj": [["cowardly"]], "klass": "VI"},
        {"id": "1", "title": "Existence", "adj": [["real", "careful"]], "klass": "I"},
        {"id": "900", "title": "Resentment", "adj": [["resentful"]], "klass": "VI"},
        {"id": "901", "title": "Irascibility", "adj": [["irascible"]], "klass": "VI"},
    ])
    heads = list(idx.order)
    hi = {h: i for i, h in enumerate(heads)}
    noise = len(heads)
    recs = [rec("cautious", "d1"), rec("careful", "d2"), rec("reckless", "d3"), rec("plucky", "d4"),
            rec("irascible", "d5"), rec("zzz", "d6")]
    want = {"cautious": {hi["864"]: 1.0},
            "careful": {hi["1"]: 1.0, hi["864"]: 0.9},
            "reckless": {hi["861"]: 0.9, hi["862"]: 0.8, hi["900"]: 0.7, hi["863"]: 0.6},
            "plucky": {hi["861"]: 1.0, noise: 0.5},
            "irascible": {noise: 1.0, hi["900"]: 0.2},
            "zzz": {noise: 1.0}}
    table = {P.head_profile(idx.heads[h]): {hi[h]: 1.0} for h in heads}
    table.update({M.label_text(r): want[r.stem] for r in recs})
    out = M.map_labels(recs, idx, embedder=StubEmbedder(table, noise + 1), head_ids=heads)
    got = {k: (a.route, a.primary, a.secondary) for k, a in out.items()}
    assert got == {"cautious": ("agree", "864", []),
                   "careful": ("agree", "864", ["1"]),
                   "reckless": ("rule", "863", []),
                   "plucky": ("semantic", "861", []),
                   "irascible": ("lexical", "901", []),
                   "zzz": ("none", None, [])}


def test_load_labels(tmp_path):
    inst = tmp_path / "traits" / "instructions"
    inst.mkdir(parents=True)

    def w(stem, **d):
        (inst / f"{stem}.json").write_text(json.dumps({"positive_label": stem.replace("_", " "), **d}))

    w("bold", negative_label="timid", arrangement={"kind": "pair", "members": ["bold", "timid"]}, description="b")
    w("timid", negative_label="bold", arrangement={"kind": "pair", "members": ["bold", "timid"]}, description="t")
    w("odd", negative_label="non-odd", description="o")
    w("hasty", negative_label="patient", description="h")             # one-way pointer, no file
    q = tmp_path / "q.json"
    q.write_text(json.dumps({"entries": [
        {"stem": "patient", "label": "patient", "entity_type": "trait", "status": "candidate",
         "description_draft": "p", "partner": "hasty"},
        {"stem": "bold", "label": "bold", "entity_type": "trait", "status": "done"},            # has a file
        {"stem": "pilot", "label": "pilot", "entity_type": "role", "status": "candidate"},       # a role
        {"stem": "gone", "label": "gone", "entity_type": "trait", "status": "not_adopted"}]}))
    recs = {r.stem: r for r in M.load_labels(tmp_path, q)}
    assert set(recs) == {"bold", "timid", "odd", "hasty", "patient", "gone"}
    assert (recs["bold"].partner_stem, recs["bold"].partner_has_file) == ("timid", True)
    assert (recs["odd"].partner_stem, recs["odd"].partner_has_file) == (None, False)
    assert (recs["hasty"].partner_stem, recs["hasty"].partner_has_file) == ("patient", False)
    assert (recs["patient"].source, recs["patient"].status, recs["patient"].description) == ("queued", "candidate", "p")
    assert recs["patient"].partner_has_file is True
    assert recs["gone"].status == "not_adopted"


def test_save_load_and_spotcheck(fx, tmp_path):
    recs = [rec("cautious", "This means being wary."), rec("obstinate", "This means being stubborn."),
            rec("queued one", "q", source="queued", status="candidate")]
    assignments = M.map_labels(recs, fx, embedder=HashEmbedder(), cache=EmbeddingCache(tmp_path))
    path = M.save_label_heads(recs, assignments, tmp_path / "label_heads.json")
    lh = M.load_label_heads(path)
    assert set(lh) == {"cautious", "obstinate", "queued_one"}
    assert lh["cautious"]["primary"] == "864" and lh["cautious"]["llm"] is None
    md = M.spotcheck_markdown(recs, lh, fx, n=2, seed=0)
    rows = [l for l in md.splitlines() if l.startswith("| [")]
    assert len(rows) == 2
    assert "](../../traits/instructions/" in md or "](../../seed_queue.json) (queued)" in md
    assert M.route_counts(lh)


# --------------------------------------------------------------------------- update (2026-10-08, after chunk 5)

def test_payload_records_the_placed_text_hash(fx, tmp_path):
    from assistant_axis.gapgen.embed import text_sha256
    recs = [rec("cautious", "This means being wary."), rec("bare", None, source="queued", status="candidate")]
    lh = M.label_heads_payload(recs, M.map_labels(recs, fx, embedder=HashEmbedder(), cache=EmbeddingCache(tmp_path)))
    assert lh["cautious"]["placed_text_sha256"] == text_sha256("cautious: This means being wary.")
    assert lh["bare"]["placed_text_sha256"] == text_sha256("bare")                 # no description: the label
    assert list(lh["cautious"])[:6] == list(M.ENTRY_KEYS)[:6]


def _world(tmp_path, fx, recs):
    """A placed world: label_heads from the hash embedder, the cache and the head matrix."""
    cache = EmbeddingCache(tmp_path / "cache")
    emb = HashEmbedder()
    head_ids = [h for h in fx.order if fx.heads[h].pos.get("Adj") or fx.heads[h].pos.get("N")]
    lh = M.label_heads_payload(recs, M.map_labels(recs, fx, embedder=emb, cache=cache, head_ids=head_ids))
    H = M.head_matrix(fx, head_ids, embedder=emb, cache=cache)
    return lh, cache, emb, head_ids, H


def test_plan_update_by_hash(fx, tmp_path):
    recs = [rec("cautious", "This means being wary."), rec("obstinate", "This means being stubborn."),
            rec("old name", "This means something.")]
    lh, *_ = _world(tmp_path, fx, recs)
    now = [rec("cautious", "This means looking before one leaps."),          # description edited
           rec("obstinate", "This means being stubborn.", status="x"),       # metadata only
           rec("new name", "This means something.")]                          # a rename: new stem, old one gone
    plan = M.plan_update(lh, now)
    assert plan.dropped == ["old_name"] and plan.added == ["new_name"]
    assert plan.changed == {"cautious": "hash"} and plan.unchanged == {"obstinate": "hash"}
    assert plan.metadata == ["obstinate"] and plan.selected == ["cautious", "new_name"]
    s = plan.summary(lh)
    assert s["dropped"] == {"old_name": lh["old_name"]["primary"]} and s["changed"] == {"cautious": "hash"}


def test_plan_update_without_a_hash_uses_the_cache_and_the_recorded_cosines(fx, tmp_path):
    from assistant_axis.gapgen.embed import embed_texts
    recs = [rec("cautious", "This means being wary, prudent and careful."),
            rec("obstinate", "This means being stubborn, headstrong and inflexible."),
            rec("resolute", "This means holding to a decision once made.")]
    lh, cache, emb, head_ids, H = _world(tmp_path, fx, recs)
    for v in lh.values():                                   # a file written before the hash was recorded
        v.pop("placed_text_sha256")
    now = [recs[0],
           rec("obstinate", "This means refusing every argument, mule-headed and contrary."),   # not in the cache
           rec("resolute", "This means hating every change of plan, rigid and unbending.")]      # cached elsewhere
    embed_texts(emb, [M.label_text(now[2])], cache=cache)
    plan = M.plan_update(lh, now, cache=cache, embedder=emb, head_ids=head_ids, head_vecs=H)
    assert plan.unchanged == {"cautious": "cache_and_semantic"}
    assert plan.changed == {"obstinate": "cache_miss", "resolute": "semantic_differs"}
    # without the head matrix a cache hit cannot be confirmed: counted unchanged, marked so
    plan = M.plan_update(lh, now, cache=cache, embedder=emb)
    assert plan.unchanged == {"cautious": "cache_hit", "resolute": "cache_hit"}
    # neither a hash nor a cache: everything is re-placed
    assert M.plan_update(lh, now).changed == {"cautious": "unknown", "obstinate": "unknown", "resolute": "unknown"}


def test_update_label_heads_replaces_only_the_selected(fx, tmp_path):
    from assistant_axis.gapgen.embed import text_sha256
    recs = [rec("cautious", "This means being wary, prudent and careful."),
            rec("obstinate", "This means being stubborn, headstrong and inflexible."),
            rec("old name", "This means something else.", source="queued", status="candidate")]
    lh, cache, emb, head_ids, H = _world(tmp_path, fx, recs)
    check = {"check": "roget_placement", "final": "606", "outcome": "unchanged", "previous_primary": "606"}
    lh["cautious"]["llm"] = dict(check, final="864", previous_primary="864")
    lh["obstinate"]["llm"] = dict(check)
    now = [rec("cautious", "This means being wary, prudent and careful.", source="existing"),
           rec("obstinate", "This means refusing every argument, mule-headed and contrary."),
           rec("new name", "This means something else.", source="queued", status="ready")]
    now[0].partner_stem, now[0].partner_has_file = "rash", True               # metadata only
    plan = M.plan_update(lh, now)
    new, summary = M.update_label_heads(lh, now, fx, plan, embedder=emb, cache=cache, head_ids=head_ids, now="T")
    assert list(new) == ["cautious", "obstinate", "new_name"]                 # the records' order; old_name dropped
    c = new["cautious"]                                                       # kept: placement and llm untouched
    assert {k: c[k] for k in ("primary", "secondary", "route", "lexical", "semantic", "llm")} == \
        {k: lh["cautious"][k] for k in ("primary", "secondary", "route", "lexical", "semantic", "llm")}
    assert (c["partner_stem"], c["partner_has_file"]) == ("rash", True)       # metadata refreshed
    assert c["placed_text_sha256"] == text_sha256(M.label_text(now[0])) and "previous_placement" not in c
    o = new["obstinate"]                                                      # re-placed
    fresh = M.label_heads_payload([now[1]], M.map_labels([now[1]], fx, embedder=emb, cache=cache, head_ids=head_ids))
    assert {k: v for k, v in o.items() if k != "previous_placement"} == fresh["obstinate"]
    assert o["llm"] is None and o["placed_text_sha256"] == text_sha256(M.label_text(now[1]))
    pp = o["previous_placement"]
    assert (pp["primary"], pp["route"], pp["llm"]) == (lh["obstinate"]["primary"], lh["obstinate"]["route"], check)
    assert (pp["replaced_at"], pp["why"], pp["found_by"]) == ("T", "text_changed", "hash")
    assert pp["placed_text_sha256"] == lh["obstinate"]["placed_text_sha256"]
    assert "previous_placement" not in new["new_name"]                        # a new stem: nothing remapped
    assert summary["dropped"] == {"old_name": lh["old_name"]["primary"]} and summary["added"] == ["new_name"]
    assert summary["n_replaced"] == 2 and summary["metadata_refreshed"] == ["cautious"]
    # a second replacement keeps the first one's record inside the new one
    again = [now[0], rec("obstinate", "This means a third text, unlike the others."), now[2]]
    new2, _ = M.update_label_heads(new, again, fx, M.plan_update(new, again), embedder=emb, cache=cache,
                                   head_ids=head_ids, now="T2")
    assert new2["obstinate"]["previous_placement"]["previous_placement"] == pp
    assert new2["cautious"] == new["cautious"]


def test_rewrite_keeps_the_payload_and_replaces_inputs_by_key(tmp_path):
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("a")
    b.write_text("b")
    p = tmp_path / "label_heads.json"
    p.write_text(json.dumps(json_metadata({"rules_version": 1, "placement_check": {"n_checked": 2}, "labels": {"x": {}}},
                                          inputs=[current_file_input("seed_queue", a),
                                                  current_file_input("roget_heads", a)])))
    M.rewrite_label_heads(p, {"y": {"primary": None}}, extra_inputs=[current_file_input("seed_queue", b)],
                          updates={"map_updates": [{"at": "T"}]})
    d = json.loads(p.read_text())
    assert d["result"]["placement_check"] == {"n_checked": 2} and d["result"]["map_updates"] == [{"at": "T"}]
    assert M.load_label_heads(p) == {"y": {"primary": None}}
    ins = {i["dep_key"]: i for i in d["_provenance"]["inputs"]}
    assert set(ins) == {"seed_queue", "roget_heads"} and ins["seed_queue"]["path"].endswith("b.txt")
