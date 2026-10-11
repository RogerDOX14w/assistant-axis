"""Base-model generator: the gloss sense settled before M1 (Roger, QUESTIONS 56).

The free cosine screen, the one cheap call per divergent row, the fidelity-subject-to-legibility rule, the
provenance kept on the row, and the invariant the whole thing exists for: a row with two candidate senses
cannot be submitted, so M1 and M3 never judge a sense that is later changed.  No call leaves the process: the
embedder is the deterministic hash arm and the model is a fake.
"""
import json

import pytest

from assistant_axis.gapgen.embed import HashEmbedder, embed_texts
from assistant_axis.gapgen.generators.base_model import sense as SE
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text

OEWN = "not easily perturbed or excited or upset"
SAMPLE_SAME = "not easily perturbed or upset by anything"
SAMPLE_OTHER = "able to fold flat for storage in a cupboard"


def row(stem="unflappable", *, oewn=OEWN, sample=SAMPLE_SAME, **kw):
    d = {"stem": stem, "surface": stem.replace("_", "-"), "gloss_hint": oewn, "sample_gloss": sample}
    d.update(kw)
    return d


def embed(texts):
    return embed_texts(HashEmbedder(dim=96), texts)


def screened(rows, floor=SE.DIVERGENCE_COSINE):
    cos = SE.cosine_rows(rows, embed=embed)
    counts = SE.screen(rows, cosines=cos, floor=floor, embedder="hash")
    return counts


# --------------------------------------------------------------------------- the wording

def test_prompt_wording_is_pinned():
    assert SE.PROMPT_HASHES[SE.GLOSS_SENSE_VERSION] == SE.wording_sha256(), (
        "the gloss-sense wording changed: bump GLOSS_SENSE_VERSION and append the new hash")


def test_model_is_the_platforms_cheap_one_and_sends_no_temperature():
    from assistant_axis.gapgen.filter import DEFAULT_MODEL
    from assistant_axis.gapgen.llm import accepts_temperature, request_params
    assert SE.MODEL == DEFAULT_MODEL == "claude-haiku-5-5"
    assert not accepts_temperature(SE.MODEL) and SE.TEMPERATURE is None
    q = SE.request(word="even_handed", sample=SAMPLE_OTHER, dictionary=OEWN)
    assert "temperature" not in request_params(model=q["model"], system=q["system"], user=q["user"],
                                               max_tokens=q["max_tokens"], temperature=q["temperature"])


def test_the_rendered_call_states_the_criterion_and_shows_both_glosses():
    text = SE.render(row())
    assert "Fidelity" in text and "Legibility" in text
    # explicitly not novelty: the filter must not be shown an answer selected to pass it
    assert "novel" in text and "not picking the more interesting trait" in text
    assert OEWN in text and SAMPLE_SAME in text
    assert "unflappable" in text                      # the display form of the stem, spaces not underscores
    assert "claude-haiku-5-5" in text


# --------------------------------------------------------------------------- reading a row

def test_only_a_two_sided_row_can_diverge():
    assert SE.two_sided(row())
    assert not SE.two_sided(row(sample=None))         # the model wrote no gloss
    assert not SE.two_sided(row(oewn=None))           # OEWN has no sense: the hint stays None, as pre-registered
    assert SE.resolved_hint(row(oewn=None)) is None
    assert SE.unresolved([row(oewn=None), row(sample=None)]) == []


def test_unresolved_is_what_submission_refuses_on():
    r = row()
    assert SE.unresolved([r]) == [r] and SE.stale_reason(r) == "absent"
    screened([r])
    assert SE.unresolved([r]) == []                   # the glosses agreed, so the screen settled it


def test_stale_reasons():
    r = row(sample=SAMPLE_OTHER)
    screened([r])
    assert r[SE.BLOCK]["divergent"] and SE.stale_reason(r) == "awaiting_call"
    assert SE.needs_call(r) and not SE.needs_screen(r)       # the cosine is recorded; only the call is missing
    r[SE.BLOCK]["error"] = "no response: timeout"
    assert SE.stale_reason(r) == "failed" and SE.needs_call(r)
    r[SE.BLOCK].update({"chosen": "sample", "error": None, "prompt_version": SE.GLOSS_SENSE_VERSION})
    assert SE.stale_reason(r) is None and not SE.needs_call(r)
    r[SE.BLOCK]["prompt_version"] = 0
    assert SE.stale_reason(r) == "prompt_changed" and SE.needs_call(r)
    r[SE.BLOCK]["prompt_version"] = SE.GLOSS_SENSE_VERSION
    r["sample_gloss"] = "something else entirely"
    assert SE.stale_reason(r) == "glosses_changed" and SE.needs_screen(r)


# --------------------------------------------------------------------------- the free screen

def test_the_screen_is_free_and_only_flags():
    same, other = row("unflappable"), row("folding", sample=SAMPLE_OTHER)
    counts = screened([same, other])
    assert counts["n_screened"] == 2 and counts["n_divergent"] == 1 and counts["n_agree"] == 1
    assert counts["divergence_rate"] == 0.5
    # the agreeing row needs no call and keeps the dictionary's wording
    assert same[SE.BLOCK]["chosen"] == "dictionary" and not SE.needs_call(same)
    assert SE.resolved_hint(same) == OEWN
    # the divergent one waits for the call and blocks submission meanwhile
    assert other[SE.BLOCK]["divergent"] and SE.needs_call(other) and SE.unresolved([other]) == [other]
    # both glosses and the cosine stay on the row as provenance, so another floor re-derives for free
    for r in (same, other):
        assert r[SE.BLOCK]["oewn"] == OEWN and r[SE.BLOCK]["sample"] == r["sample_gloss"]
        assert isinstance(r[SE.BLOCK]["cosine"], float) and r[SE.BLOCK]["floor"] == SE.DIVERGENCE_COSINE
    assert other[SE.BLOCK]["cosine"] < same[SE.BLOCK]["cosine"]


def test_the_floor_can_be_moved_without_re_embedding():
    r = row()
    cos = SE.cosine_rows([r], embed=embed)
    assert SE.screen([r], cosines=cos, floor=0.0)["n_divergent"] == 0
    r.pop(SE.BLOCK)
    assert SE.screen([r], cosines=cos, floor=1.1)["n_divergent"] == 1   # every row divergent at a floor of 1.1


def test_the_screen_is_idempotent():
    r = row(sample=SAMPLE_OTHER)
    screened([r])
    before = json.dumps(r[SE.BLOCK], sort_keys=True)
    assert SE.cosine_rows([r], embed=embed) == {}        # nothing to re-embed
    assert SE.screen([r], cosines={"unflappable": 0.1})["n_screened"] == 0
    assert json.dumps(r[SE.BLOCK], sort_keys=True) == before


# --------------------------------------------------------------------------- the answer

@pytest.mark.parametrize("text,err", [
    (None, "empty response"), ("", "empty response"), ("nothing here", "unparseable"),
    ('{"choice": "both", "legible": true, "reason": "x"}', "choice must be"),
    ('{"choice": "sample", "reason": "x"}', "legible must be"),
    ('{"choice": "sample", "legible": true}', "reason is missing"),
])
def test_bad_answers_are_errors(text, err):
    a, e = SE.parse_answer(text)
    assert a is None and err in e


def test_a_good_answer_parses_through_prose_and_fences():
    a, e = SE.parse_answer('Here you go:\n```json\n{"choice": "sample", "legible": true, '
                           '"reason": "the gloss names the sense plainly"}\n```')
    assert e is None and a["choice"] == "sample" and a["legible"] is True


def test_legibility_overrides_fidelity():
    assert SE.decide({"choice": "sample", "legible": True, "reason": "x"}) == ("sample", None)
    assert SE.decide({"choice": "dictionary", "legible": False, "reason": "x"}) == ("dictionary", None)
    choice, note = SE.decide({"choice": "sample", "legible": False, "reason": "x"})
    assert choice == "dictionary" and "legibility decides" in note


# --------------------------------------------------------------------------- the calls

def answer(choice="sample", legible=True, reason="the gloss names that sense plainly"):
    return json.dumps({"choice": choice, "legible": legible, "reason": reason})


def test_a_divergent_row_is_settled_by_one_call(tmp_path):
    r = row(sample=SAMPLE_OTHER)
    screened([r])
    sent = []

    async def send(q, meta):
        sent.append(q)
        meta.update({"stop_reason": "end_turn", "usage_raw": {"input_tokens": 400}, "attempts": 1})
        return answer()
    counts = SE.run_resolve_rows([r], send=send, records_path=tmp_path / "rec.jsonl")
    assert counts == {"n_called": 1, "n_sample": 1, "n_dictionary": 0, "n_failed": 0, "n_illegible_sample": 0}
    assert len(sent) == 1 and SAMPLE_OTHER in sent[0]["user"] and OEWN in sent[0]["user"]
    b = r[SE.BLOCK]
    assert b["chosen"] == "sample" and b["reason"] and b["model"] == SE.MODEL
    assert b["prompt_version"] == SE.GLOSS_SENSE_VERSION and b["prompt_sha256"] == SE.wording_sha256()
    # the row keeps both glosses; the candidate carries the chosen one
    assert b["oewn"] == OEWN and b["sample"] == SAMPLE_OTHER and r["gloss_hint"] == OEWN
    assert SE.resolved_hint(r) == SAMPLE_OTHER and SE.unresolved([r]) == []
    rec = [json.loads(x) for x in (tmp_path / "rec.jsonl").read_text().splitlines()]
    assert len(rec) == 1 and rec[0]["stem"] == "unflappable" and rec[0]["parse_error"] is None


def test_an_illegible_sample_reading_keeps_the_dictionary():
    r = row(sample=SAMPLE_OTHER)
    screened([r])

    async def send(q, meta):
        return answer(legible=False)
    counts = SE.run_resolve_rows([r], send=send)
    assert counts["n_illegible_sample"] == 1 and counts["n_dictionary"] == 1
    assert r[SE.BLOCK]["chosen"] == "dictionary" and "legibility decides" in r[SE.BLOCK]["note"]
    assert SE.resolved_hint(r) == OEWN


def test_a_failed_call_leaves_the_row_unresolved_rather_than_guessing(tmp_path):
    r = row(sample=SAMPLE_OTHER)
    screened([r])
    calls = []

    async def send(q, meta):
        calls.append(q)
        meta.update({"error": "APIStatusError: 500", "attempts": 5})
        return None
    counts = SE.run_resolve_rows([r], send=send, records_path=tmp_path / "rec.jsonl")
    assert counts["n_failed"] == 1 and len(calls) == 2            # the answer is retried once, alone
    assert r[SE.BLOCK]["chosen"] is None and "no response" in r[SE.BLOCK]["error"]
    assert SE.unresolved([r]) == [r] and SE.resolved_hint(r) == OEWN
    assert len((tmp_path / "rec.jsonl").read_text().splitlines()) == 2


def test_an_unparseable_answer_is_retried_once_then_recorded():
    r = row(sample=SAMPLE_OTHER)
    screened([r])
    texts = iter(["not json", answer("dictionary")])

    async def send(q, meta):
        return next(texts)
    counts = SE.run_resolve_rows([r], send=send)
    assert counts["n_called"] == 1 and counts["n_dictionary"] == 1 and r[SE.BLOCK]["chosen"] == "dictionary"


def test_only_divergent_rows_are_called():
    same, other, one_sided = row("unflappable"), row("folding", sample=SAMPLE_OTHER), row("bare", sample=None)
    screened([same, other, one_sided])
    asked = []

    async def send(q, meta):
        asked.append(q["user"])
        return answer()
    SE.run_resolve_rows([same, other, one_sided], send=send)
    assert len(asked) == 1 and SAMPLE_OTHER in asked[0]


def test_the_real_client_path_charges_every_response(tmp_path):
    r = row(sample=SAMPLE_OTHER)
    screened([r])
    client = FakeAsyncAnthropic(lambda kw: make_response(answer(), input_tokens=420, output_tokens=48)
                                if "Which reading" in user_text(kw) else make_response("?"))
    usage = MultiModelUsage()
    SE.run_resolve_rows([r], client=client, usage=usage, records_path=tmp_path / "rec.jsonl")
    assert r[SE.BLOCK]["chosen"] == "sample"
    d = usage.as_dict()
    assert d["n_calls"] == 1 and d["per_model"][SE.MODEL]["prompt_tokens"] == 420
    assert 0 < d["total_cost_usd"] < 0.01              # hundredths of a cent a row
    usage.write_json(tmp_path / SE.USAGE_NAME)
    assert json.loads((tmp_path / SE.USAGE_NAME).read_text())["total_cost_usd"] == d["total_cost_usd"]


def test_resolve_needs_a_client_or_a_send():
    with pytest.raises(ValueError):
        SE.run_resolve_rows([row()])


# --------------------------------------------------------------------------- the record

def test_summary_reports_the_divergence_rate_and_what_blocks_submission():
    rows = [row("unflappable"), row("folding", sample=SAMPLE_OTHER), row("bare", sample=None)]
    assert SE.summary(rows)["n_two_sided"] == 2 and SE.summary(rows)["n_screened"] == 0
    screened(rows)
    s = SE.summary(rows)
    assert (s["n_divergent"], s["divergence_rate"], s["n_unresolved"]) == (1, 0.5, 1)
    assert s["prompt_version"] == SE.GLOSS_SENSE_VERSION and s["model"] == SE.MODEL
    assert s["cosine_min"] is not None

    async def send(q, meta):
        return answer()
    SE.run_resolve_rows(rows, send=send)
    s = SE.summary(rows)
    assert (s["n_chose_sample"], s["n_failed"], s["n_unresolved"]) == (1, 0, 0)


def test_a_hint_is_cut_to_the_censuses_length():
    long = " ".join(f"w{i}" for i in range(40))
    r = row(sample=long)
    screened([r])

    async def send(q, meta):
        return answer()
    SE.run_resolve_rows([r], send=send)
    assert len(SE.resolved_hint(r).split()) == 25       # glosshint.MAX_WORDS


def test_a_reparse_keeps_the_decisions_it_paid_for():
    old = row(sample=SAMPLE_OTHER)
    screened([old])
    old[SE.BLOCK].update({"chosen": "sample", "chosen_gloss": SAMPLE_OTHER,
                          "prompt_version": SE.GLOSS_SENSE_VERSION})
    fresh = row(sample=SAMPLE_OTHER)                      # as `parse` rebuilds it from the samples
    assert SE.carry_forward([fresh], [old]) == 1
    assert SE.stale_reason(fresh) is None and SE.resolved_hint(fresh) == SAMPLE_OTHER
    # a row whose gloss moved keeps nothing: the old decision was about other text
    moved = row(sample="a different gloss entirely")
    assert SE.carry_forward([moved], [old]) == 0 and SE.stale_reason(moved) == "absent"


def test_the_todo_for_sense_id_is_recorded():
    # Roger deferred keeping both senses through Candidate.sense_id until there is a sample of divergent rows
    # to look at (QUESTIONS 56); the module must carry that TODO so it is not lost.
    assert "TODO (Roger" in SE.__doc__ and "sense_id" in SE.__doc__
