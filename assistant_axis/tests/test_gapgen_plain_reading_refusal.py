"""A plain reading that is a refusal is recorded as a refusal: no comparison is made and no note is
raised (coordinator, 2026-09-30, after the corpus comparison read one refusal as a "different"
reading).  No API call."""
import json

import pytest

from assistant_axis.gapgen import plain_reading as pr
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-5-5"
RECORDED = ("I can't create content that describes or normalizes homophobic behavior, even in a "
            "hypothetical persona exercise.")


@pytest.mark.parametrize("text", [
    RECORDED,
    "I cannot write a description of that persona.",
    "I won't role-play a persona built on hatred.",
    "I'm not able to help with that request.",
    "I’m sorry, but I can’t portray that.",
    "Sorry, I can't produce this content.",
    "I apologize, but I cannot describe this.",
    '"I can\'t create that content."',
])
def test_refusals_are_found(text):
    assert pr.is_refusal(text)


@pytest.mark.parametrize("text", [
    "Treats gay people with open contempt and mocks them in conversation.",
    "I can't stop talking once I get going.",          # a first-person reading, no request named
    "Refuses to create anything original, copying others instead.",  # the persona refuses, not the model
    "Sorry for nothing, apologizes for nothing.",
    "Describes every scene in vivid detail.",           # names 'describe' but opens as a reading
    "",
    None,
])
def test_readings_are_not_refusals(text):
    assert not pr.is_refusal(text)


def test_an_api_refusal_counts_whatever_the_text():
    assert pr.is_refusal("Any text at all.", stop_reason="refusal")


def _responder(kw):
    if not kw.get("system"):                             # the plain reading
        word = user_text(kw).split('"You are ')[1].split('."')[0]
        return RECORDED if word == "homophobic" else f"Behaves in a plain {word} way."
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    return json.dumps({"results": [{"id": it["id"], "label": it["label"], "reason": "r",
                                    "relation": "different", "confidence": 0.9} for it in items]})


def _items():
    return [pr.ReadingItem(key="homophobic", label="homophobic", intended="This means treating ... as wrong."),
            pr.ReadingItem(key="calm", label="calm", intended="This means staying calm.")]


def test_a_refused_row_gets_no_comparison_and_no_note():
    client = FakeAsyncAnthropic(_responder)
    r = pr.PlainReadingRunner(client=client, batch_id="b", reading_model=HAIKU, compare_model=SONNET)
    out = {o.key: o for o in r.run(_items())}
    h = out["homophobic"]
    assert h.stage == "refused" and h.comparison is None and h.notes == []
    assert h.reading == RECORDED and h.reading_block["refusal"] is True
    assert "refusal" in h.error
    compare_calls = [c for c in client.calls if c.get("system")]
    assert compare_calls and all("homophobic" not in user_text(c) for c in compare_calls)
    c = out["calm"]
    assert c.stage == "compared" and c.notes == ["overshadowed"] and c.reading_block["refusal"] is False
    s = pr.summarize(list(out.values()), stats=r.stats, usage=r.usage)
    assert s["n_refused"] == 1 and s["refused"] == ["homophobic"] and s["n_failed"] == 0
    assert s["relations"]["different"] == 1
    # the corpus listing shows the refusal, last, with its reason
    listing = pr.corpus_listing(list(out.values()))
    assert listing.splitlines()[-1].startswith("| refused | homophobic |")


def test_a_reused_refusal_is_caught_too():
    client = FakeAsyncAnthropic(_responder)
    r = pr.PlainReadingRunner(client=client, batch_id="b", reading_model=HAIKU, compare_model=SONNET,
                              reuse_readings={"homophobic": RECORDED})
    out = {o.key: o for o in r.run(_items())}
    assert out["homophobic"].stage == "refused" and out["homophobic"].reading_block["reused"] is True


def test_an_api_refusal_stop_reason_is_a_refusal():
    def resp(kw):
        if not kw.get("system"):
            return make_response("Something the model began to say.", stop_reason="refusal")
        return _responder(kw)
    r = pr.PlainReadingRunner(client=FakeAsyncAnthropic(resp), batch_id="b", reading_model=HAIKU,
                              compare_model=SONNET)
    out = r.run(_items()[:1])[0]
    assert out.stage == "refused" and out.comparison is None
