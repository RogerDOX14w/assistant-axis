"""Rubric v2 (reports/trait_gap_generation/decisions_m1.md, Roger's decisions of
2026-09-29).  Item numbers are the round-1 list; decision numbers are the
decisions file's.  Written before the change; each failed against 5d6b0dd."""
import hashlib
import json
import re
import warnings

import pytest

from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen import freq
from assistant_axis.gapgen.filter import (
    FilterItem, FilterResult, FilterRunner, holding_for, items_from_records, select_second_opinion,
)
from assistant_axis.gapgen.normalize import HOLDING, TAG_VOCAB
from assistant_axis.gapgen.registry import Candidate, Registry, holding_list, new_record, submit_candidates
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, system_text, user_text

HAIKU = "claude-haiku-4-5-20251001"
V1_PROMPT_SHA = "113bde981420d93fc58b41b0b6cf12785537a3186588cc3289ef6e9edd8da2a5"
V1_PROBE_SHA = "d5ba66e82026137af301cded277f039f03269910eb4b8542ef7c0425f414d4e1"

#: decisions_m1.md appendix (open point D): never rubric examples.
APPENDIX = {"dynamic", "colorful", "deep", "polished", "warm", "dull", "volatile", "stiff", "toxic", "clinical",
            "graphic", "portable", "bossy", "fickle", "smug", "nosy", "wily", "cheeky", "pushy", "garrulous",
            "magnetic", "dense", "sharp", "cold", "bright", "abrasive", "shallow", "slick", "brittle",
            "mechanical", "linear", "organic", "gullible", "shrewd", "haughty", "coy", "petulant", "headstrong",
            "snobbish", "taciturn"}
SIX = {"disciplinary", "engaging", "economic", "balanced", "empowered", "emotive"}


def row(i, label, **kw):
    base = {"id": i, "label": label, "reason": "Said of how someone habitually behaves in conversation.",
            "person_senses": [{"sense": label, "kind": "trait"}], "trait_senses_equally_obvious": False, "enactable_in_text": 2, "verdict": "trait",
            "tags": [], "membership_kind": None, "region": "social_interpersonal", "alignment_relevant": False,
            "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}
    base.update(kw)
    return base


def parse(*rows, labels=None):
    labels = labels or {r["id"]: r["label"] for r in rows}
    return fr.parse_batch(json.dumps({"results": list(rows)}), list(labels), labels=labels)


# ---------------------------------------------------------------------------
# 13. versions and prompt identity
# ---------------------------------------------------------------------------

def test_versions_and_hashes_change():
    # probe rubric 3 since round 2 (derived words); the classifier stays at 2
    assert fr.TRAITHOOD_RUBRIC_VERSION == 3 and fr.PROBE_RUBRIC_VERSION == 3  # round 3: classifier v3
    from assistant_axis.gapgen.filter import PROMPT_SHA256
    assert PROMPT_SHA256["classifier"] != V1_PROMPT_SHA
    assert PROMPT_SHA256["probe"] != V1_PROBE_SHA
    assert PROMPT_SHA256["classifier"] == hashlib.sha256(fr.SYSTEM_PROMPT.encode()).hexdigest()


# ---------------------------------------------------------------------------
# prompt content
# ---------------------------------------------------------------------------

class TestPromptV2:
    def schema(self):
        sp = fr.SYSTEM_PROMPT
        return sp[sp.index('{"results"'):]

    def test_schema_field_order(self):
        s = self.schema()
        order = ['"id"', '"label"', '"reason"', '"person_senses"', '"trait_senses_equally_obvious"',
                 '"verdict"', '"tags"',
                 '"membership_kind"', '"alignment_relevant"', '"gloss"', '"confidence"']
        pos = [s.index(k) for k in order]
        assert pos == sorted(pos)

    def test_primary_use_held(self):
        """Scope change 2026-09-29: decision 11's primary_use is held; the
        polysemy flag stays the v1 sense-rank rule."""
        assert "primary_use" not in fr.SYSTEM_PROMPT
        assert '"person_senses"' in fr.SYSTEM_PROMPT  # rubric v3 replaced the v1 sense-rank wording

    def test_reason_cap_and_sense_line(self):
        sp = fr.SYSTEM_PROMPT
        assert "30 words" in sp and "20 words" not in sp
        assert "sense being judged" in sp  # decision 4

    def test_one_role_test_wording(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert ("Could a person be this and also hold an ordinary profession, such as plumber? If yes, it is "
                "a trait. If being this rules out most professions, or is itself a profession or office, it "
                "is a role.") in sp

    def test_membership_kinds_listed(self):
        for k in fr.MEMBERSHIP_KINDS:
            assert k in fr.SYSTEM_PROMPT
        assert set(fr.MEMBERSHIP_KINDS) >= {"circumstance", "class", "family", "affinity", "relationship",
                                            "orientation_gender", "geography",
                                            "nationality_ethnicity_language", "age_group"}

    def test_physical_definition(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "mostly or entirely physical" in sp
        assert "strong mental side" in sp

    def test_states_rule_v2(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "general tendency" not in sp  # rubric v1's state rule no longer holds
        assert '"state"' in sp and "transient_only" not in sp  # folded into state (round 2, point C)
        assert "extra work" in fr.__doc__ and "separate queue" in fr.__doc__  # Roger's correction quoted

    def test_relational_only_rule(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "only when none of its senses describes a person's character" in sp

    def test_alignment_field_independent_of_region(self):
        sp = " ".join(fr.SYSTEM_PROMPT.split())
        assert "alignment_relevant" in sp and "independently of the region" in sp

    def test_classifier_tags(self):
        assert "membership" in fr.CLASSIFIER_TAGS and "state" in fr.CLASSIFIER_TAGS
        assert "transient_only" not in fr.CLASSIFIER_TAGS  # folded into state (round 2, point C)
        assert "transient_only" in TAG_VOCAB  # kept for v1 records
        assert "demographic" not in fr.CLASSIFIER_TAGS and "too_rare" not in fr.CLASSIFIER_TAGS
        assert "membership" in TAG_VOCAB and "demographic" in TAG_VOCAB  # kept for v1 records

    def test_example_hygiene_six_and_appendix(self):
        words = {w.lower() for w in fr.EXAMPLE_WORDS + fr.MENTIONED_WORDS}
        assert not words & SIX
        assert not words & APPENDIX
        low = fr.SYSTEM_PROMPT.lower()
        for w in APPENDIX | SIX:
            assert not re.search(rf"\b{w}\b", low), w

    def test_examples_agree_with_validator(self):
        """Every non-reject example shows a gloss, a region and a primary use."""
        ex = fr.SYSTEM_PROMPT[fr.SYSTEM_PROMPT.index("## Examples"):fr.SYSTEM_PROMPT.index("## Regions")]
        items = re.split(r"\n- ", ex.replace("\\\n", " "))[1:]
        assert len(items) == len(fr.EXAMPLE_WORDS)
        for item in items:
            body = " ".join(item.split())
            if "verdict reject" in body:
                continue
            for field in ("senses", "region", "gloss"):
                assert field in body, (item[:30], field)

    def test_probe_v2(self):
        p = " ".join(fr.DEFINE_PROBE_PROMPT.split())
        assert "trait" not in p.replace("trait-hood is judged elsewhere", "").lower()
        assert "trait-hood is judged elsewhere" in p
        assert "real English word" in p and "define" in p


# ---------------------------------------------------------------------------
# 12. validator
# ---------------------------------------------------------------------------

class TestValidatorV2:
    def test_label_echo(self):
        rows, errs = parse(row(1, "stubborn"), row(2, "vain"), labels={1: "stubborn", 2: "timid"})
        assert set(rows) == {1} and "label" in errs[2]

    def test_label_echo_tolerates_case_and_spacing(self):
        rows, errs = parse(row(1, "Long-Winded "), labels={1: "long-winded"})
        assert errs == {}

    def test_label_missing_rejected(self):
        r = row(1, "x")
        del r["label"]
        rows, errs = parse(r, labels={1: "x"})
        assert rows == {}

    def test_tag_must_fit_verdict(self):
        rows, errs = parse(row(1, "a", verdict="tagged", tags=[]), row(2, "b", verdict="reject", tags=[],
                                                                        gloss=None),
                           row(3, "c", verdict="tagged", tags=["relational_only"]))
        assert rows == {} and set(errs) == {1, 2, 3}

    def test_plain_trait_needs_no_tag(self):
        rows, errs = parse(row(1, "a"))
        assert errs == {} and rows[1]["tag_disagreement"] is False

    def test_gloss_required_for_tagged(self):
        rows, errs = parse(row(1, "a", verdict="tagged", tags=["physical"], region="physical", gloss=None))
        assert rows == {} and "gloss" in errs[1]

    def test_reject_gloss_may_be_null(self):
        rows, errs = parse(row(1, "a", verdict="reject", tags=["relational_only"], gloss=None, region=None,
                               person_senses=[]))
        assert errs == {}

    def test_membership_kind(self):
        ok = row(1, "a", tags=["membership"], membership_kind="family")
        bad = row(2, "b", tags=["membership"], membership_kind="nationality")
        none_ = row(3, "c", tags=["membership"], membership_kind=None)
        rows, errs = parse(ok, bad, none_)
        assert set(rows) == {1} and rows[1]["membership_kind"] == "family"

    def test_membership_kind_ignored_without_tag(self):
        rows, errs = parse(row(1, "a", membership_kind="family"))
        assert rows[1]["membership_kind"] is None

    def test_alignment_relevant(self):
        rows, errs = parse(row(2, "b", alignment_relevant="yes"), row(3, "c", alignment_relevant="true"),
                           row(4, "d", alignment_relevant=None))
        assert set(rows) == {3} and rows[3]["alignment_relevant"] is True

    def test_demographic_no_longer_a_classifier_tag(self):
        rows, errs = parse(row(1, "a", verdict="tagged", tags=["demographic"]))
        assert rows == {}

    def test_disagreement_recorded_not_overridden(self):
        rows, errs = parse(row(1, "a", tags=["role_person"]), row(2, "b", verdict="reject",
                                                                   tags=["physical", "relational_only"],
                                                                   gloss=None))
        assert errs == {}
        assert rows[1]["verdict"] == "trait" and rows[1]["tag_disagreement"] is True
        assert rows[2]["verdict"] == "reject" and rows[2]["tag_disagreement"] is True

    def test_polysemy_no_longer_from_rank(self):
        """Rubric v3 (round 3) superseded the v1 sense-rank rule; primary_use still plays no part."""
        assert fr.derive_polysemy({"trait_sense_rank": 2, "confidence": 0.9}, None) is False
        assert fr.derive_polysemy({"primary_use": "non_person", "verdict": "trait",
                                   "person_senses": [{"sense": "x", "kind": "trait"}]}, 1) is False


# ---------------------------------------------------------------------------
# 1, 2. floor and rescue
# ---------------------------------------------------------------------------

Z = {"calculating": 3.0, "uncalculating": 0.0, "inattentive": 1.2, "attentive": 3.1, "stomached": 1.44,
     "strong": 5.2, "zzword": 0.0, "mid": 1.6, "low": 1.4, "upper": 2.4}


def z(w):
    return Z.get(w, 4.0)


class TestFloorV2:
    def test_floor_is_1_5(self):
        assert freq.HARD_REJECT_BELOW == 1.5 and freq.PROBE_BELOW == 2.5
        i = freq.zipf_info("mid", zipf_fn=z)
        assert not i.hard_reject and i.probe_band
        assert freq.zipf_info("low", zipf_fn=z).hard_reject
        assert freq.zipf_info("upper", zipf_fn=z).probe_band

    def test_negating_prefix_rescue(self):
        i = freq.zipf_info("uncalculating", zipf_fn=z)
        assert not i.hard_reject and i.probe_band and i.rescue == "negating_prefix"
        i = freq.zipf_info("inattentive", zipf_fn=z)
        assert i.rescue == "negating_prefix"

    def test_compound_with_a_low_part_not_rescued(self):
        assert freq.zipf_info("strong-stomached", zipf_fn=z).hard_reject

    def test_gloss_hint_rescue(self):
        i = freq.zipf_info("zzword", gloss_hint=True, zipf_fn=z)
        assert not i.hard_reject and i.probe_band and i.rescue == "gloss_hint"

    def test_curated_rescue(self):
        assert "censuses" in freq.CURATED_GENERATORS
        assert not set(freq.CURATED_GENERATORS) & {"roget_wordnet", "wordnet_walk", "roget_harvest"}
        i = freq.zipf_info("zzword", curated=True, zipf_fn=z)
        assert not i.hard_reject and i.rescue == "curated_source"

    def test_no_rescue_without_a_route(self):
        i = freq.zipf_info("zzword", zipf_fn=z)
        assert i.hard_reject and i.rescue is None

    def test_items_from_records_carry_rescue_inputs(self):
        rec = new_record("zzword", sources=[{"generator": "censuses", "run_id": "r", "gloss_hint": None}])
        it = items_from_records([rec])[0]
        assert it.curated is True
        rec2 = new_record("zzword", sources=[{"generator": "wordnet_walk", "run_id": "r", "gloss_hint": "h"}])
        it2 = items_from_records([rec2])[0]
        assert it2.curated is False and it2.intended_sense == "h"


# ---------------------------------------------------------------------------
# 5, 11. routing and second-opinion triggers
# ---------------------------------------------------------------------------

class TestRoutingV2:
    def test_holding(self):
        assert "states" in HOLDING
        assert holding_for("tagged", ["state"]) == ("states", "trait")
        assert holding_for("tagged", ["physical"]) == ("physical", "trait")
        assert holding_for("tagged", ["role_person"]) == ("roles", "role")
        assert holding_for("trait", ["membership"]) == (None, "trait")

    def test_states_holding_list(self, tmp_path):
        reg = tmp_path / "r.jsonl"
        submit_candidates([Candidate(surface="jittery", generator="g", run_id="r")], registry_path=reg)
        Registry(reg).update("jittery#1", {"holding": "states"})
        assert [r["key"] for r in holding_list("states", registry=Registry(reg))] == ["jittery#1"]

    def _res(self, key, conf=0.9, disagree=False):
        return FilterResult(key=key, label=key[:-2], stage="classified", freq={}, wordnet={"found": True},
                            filter={"verdict": "trait", "confidence": conf, "tag_disagreement": disagree})

    def test_second_opinion_triggers(self):
        rs = [self._res("a#1", 0.74), self._res("b#1", 0.76), self._res("c#1", disagree=True), self._res("d#1")]
        assert select_second_opinion(rs, frac=0.0) == ["a#1", "c#1"]


# ---------------------------------------------------------------------------
# runner end to end with the v2 row shape
# ---------------------------------------------------------------------------

SPEC = {"tall": {"verdict": "tagged", "tags": ["physical"], "region": "physical"},
        "jittery": {"verdict": "tagged", "tags": ["state"], "region": "emotional_temperament"},
        "stepchild": {"tags": ["membership"], "membership_kind": "family"},
        "lukewarm": {"person_senses": [{"sense": "unenthusiastic", "kind": "trait"},
                                       {"sense": "slightly feverish", "kind": "bodily"}]},
        "sandbagging": {"alignment_relevant": True, "region": "alignment_ai_agent"},
        "homebody": {"tags": ["role_person"], "confidence": 0.9}}


def responder(kw):
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    if "real English word" in system_text(kw):
        return json.dumps({"results": [{"id": it["id"], "reason": "a word", "definition": "d", "known": True}
                                       for it in items]})
    return json.dumps({"results": [row(it["id"], it["label"], **SPEC.get(it["label"], {})) for it in items]})


def test_runner_v2_blocks_and_routing():
    client = FakeAsyncAnthropic(responder)
    r = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model="claude-sonnet-4-6",
                     second_opinion_frac=0.0, batch_size=10, zipf_fn=lambda w: 4.0, wordnet=False)
    out = {x.key: x for x in r.run([FilterItem(key=f"{w}#1", label=w) for w in
                                    ["tall", "jittery", "stepchild", "lukewarm", "sandbagging", "homebody", "plain"]])}
    f = out["stepchild#1"].filter
    assert f["verdict"] == "trait" and f["membership_kind"] == "family" and out["stepchild#1"].holding is None
    assert out["jittery#1"].holding == "states" and out["tall#1"].holding == "physical"
    assert out["lukewarm#1"].filter["polysemy"] is True and out["lukewarm#1"].filter["verdict"] == "trait"
    assert out["plain#1"].filter["polysemy"] is False
    assert out["sandbagging#1"].filter["alignment_relevant"] is True
    assert "primary_use" not in out["plain#1"].filter
    assert out["homebody#1"].filter["tag_disagreement"] is True
    assert out["homebody#1"].filter["second_opinion"] is not None  # disagreement triggered Sonnet
    assert out["plain#1"].filter["rubric_version"] == 3
    labels_sent = [json.loads(x)["label"] for c in client.calls[:1] for x in user_text(c).splitlines()[1:]]
    assert "plain" in labels_sent


def test_rescued_word_reaches_classifier_and_probe():
    client = FakeAsyncAnthropic(responder)
    r = FilterRunner(client=client, batch_id="b", model=HAIKU, second_model=None, second_opinion=False,
                     zipf_fn=z, wordnet=False)
    out = r.run([FilterItem(key="zzword#1", label="zzword", intended_sense="a sense"),
                 FilterItem(key="uncalculating#1", label="uncalculating"),
                 FilterItem(key="low#1", label="low")])
    by = {x.key: x for x in out}
    assert by["zzword#1"].stage == "classified" and by["zzword#1"].freq["rescue"] == "gloss_hint"
    assert by["zzword#1"].freq["define_probe"]["known"] is True
    assert by["uncalculating#1"].stage == "classified"
    assert by["low#1"].stage == "hard_reject"


def test_holding_cli_states(tmp_path, capsys):
    from data_analysis.gap_generation import gap_registry
    reg = tmp_path / "r.jsonl"
    submit_candidates([Candidate(surface="jittery", generator="g", run_id="r")], registry_path=reg)
    Registry(reg).update("jittery#1", {"holding": "states", "gloss": "This means being nervous.",
                                       "filter": {"verdict": "tagged", "tags": ["state"]}})
    assert gap_registry.main(["--registry", str(reg), "holding", "--list", "states"]) == 0
    out = capsys.readouterr().out
    assert "states queue" in out and "- **jittery** (state" in out


# ---------------------------------------------------------------------------
# 14, 15. figures recorded against targets, existing-label scoring
# ---------------------------------------------------------------------------

def _vr(label, stratum, verdict="trait", tags=(), stage="classified", holding=None, polysemy=False):
    f = {"verdict": verdict, "tags": list(tags), "polysemy": polysemy, "trait_sense_rank": None}
    return FilterResult(key=f"{label}#1", label=label, stage=stage, freq={}, wordnet={}, filter=f,
                        holding=holding, meta={"stratum": stratum})


def test_validation_figures_scoring():
    from assistant_axis.gapgen.filter import validation_figures
    rs = [_vr("a", "existing"), _vr("b", "existing", "tagged", ["state"], holding="states"),
          _vr("c", "existing", "tagged", ["physical"], holding="physical"),
          _vr("d", "existing", "trait", ["membership"]),
          _vr("e", "existing", "reject", ["relational_only"]),
          _vr("f", "existing", "reject", ["too_rare"], stage="hard_reject"),
          _vr("g", "existing", "tagged", ["role_person"], holding="roles"),
          _vr("h", "existing", "tagged", ["evaluative_only"]),
          _vr("r1", "rejects", polysemy=True), _vr("r2", "rejects"),
          _vr("o1", "oewn_random"), _vr("o2", "oewn_random", "reject", ["relational_only"])]
    f = validation_figures(rs)
    ex = f["existing"]
    assert ex["n"] == 8 and ex["correct"] == 4 and ex["target"] == 0.95
    assert ex["labels_with_state"] == ["b"] and ex["labels_with_physical"] == ["c"]
    assert ex["misses"] == {"floor": ["f"], "reject": ["e"], "roles": ["g"], "other": ["h"]}
    assert f["rejects"]["flagged"] == 1 and f["rejects"]["target"] == 4
    assert f["oewn_random"]["trait_share"] == 0.5 and f["oewn_random"]["target"] == 0.15
    assert f["existing"]["meets_target"] is False


# ---------------------------------------------------------------------------
# 16. words already turned down
# ---------------------------------------------------------------------------

def _q():
    return {"_meta": {}, "entries": [
        {"stem": "aloof", "label": "aloof", "entity_type": "trait", "status": "not_adopted",
         "decision": " DELETED 2026-09-17 (Roger, item 14): aloof overlaps reserved and detached."},
        {"stem": "extreme", "label": "extreme", "entity_type": "trait", "status": "superseded",
         "decision": "superseded by extremist (part 2, decided 2026-09-07)"},
        {"stem": "fact_bound", "label": "fact-bound", "entity_type": "trait", "status": "superseded",
         "decision": "2026-09-17: speculative is paired with empirical"}]}


def _rec(surface):
    r = new_record(surface, sources=[{"generator": "g", "run_id": "r"}])
    r["filter"] = {"verdict": "trait", "tags": []}
    r["gloss"] = "This means ..."
    return r


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    for et in ("traits", "roles"):
        (d / et / "instructions").mkdir(parents=True)
    return d


def test_promote_refuses_turned_down(data_dir):
    from assistant_axis.gapgen.promote import promote
    rows = {r["key"]: r for r in (_rec("aloof"), _rec("extreme"), _rec("fact-bound"))}
    q = _q()
    rep = promote(rows, q, list(rows), data_dir=data_dir, dry_run=False)
    assert rep.promoted == []
    assert "not_adopted" in rep.refused["aloof#1"] and "overlaps reserved and detached" in rep.refused["aloof#1"]
    assert "superseded" in rep.refused["extreme#1"] and "replaced by extremist" in rep.refused["extreme#1"]
    assert "no replacing label" in rep.refused["fact_bound#1"]
    assert len(q["entries"]) == 3


def test_promote_override_copies_history(data_dir):
    from assistant_axis.gapgen.promote import promote
    rows = {r["key"]: r for r in (_rec("aloof"),)}
    q = _q()
    rep = promote(rows, q, list(rows), data_dir=data_dir, dry_run=False, reopen_turned_down=True)
    assert rep.promoted == ["aloof#1"]
    notes = q["entries"][-1]["description_notes"]
    assert "previously not_adopted" in notes and "overlaps reserved and detached" in notes
