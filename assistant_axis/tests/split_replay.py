"""Replay of recorded answers for the split filter's tests (no network).

``fixtures/gapgen_split/recorded_answers.jsonl`` holds the answers Haiku 4.5 gave on 2026-09-29, one
item per call, copied from the probe records (``reports/trait_gap_generation/probe_*``, which the
tests may not read): step 1 from probe_single (draft 6), the established check and the kind call
from probe_rerun_wording, the vague check from probe_checks_single (asked there of the first
primary reading only), the same-sense check from probe_same_sense, the gloss (draft 2) from
probe_gloss_v2, the descriptors call from probe_last_step (asked there on the draft-1 glosses, so
they rarely match a draft-2 gloss), and the alignment call in its graded form (alignment.md draft
3, a score of 0 to 3) from probe_alignment_graded/draft4_pilot (asked on the live pilot's glosses).
A call with no recorded answer gets a fixed synthetic one (:func:`synthetic`).

``steps_1_to_3_results.jsonl`` and ``same_sense_results.jsonl`` are the joined records the reference
join read; ``expected_outcomes.jsonl`` is its output.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen import plain_reading as pr
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.tests.fake_anthropic import make_response, system_text, user_text

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gapgen_split"
HAIKU = "claude-haiku-4-5-20251001"
SONNET55 = "claude-sonnet-5-5"


def load_jsonl(name: str) -> list[dict]:
    return [json.loads(x) for x in (FIXTURES / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def recorded() -> dict[tuple[str, str], str]:
    return {(r["step"], canon(r["sent"])): r["raw"] for r in load_jsonl("recorded_answers.jsonl")}


def step_of_system(system: str) -> str:
    for name, text in sr.load_all().items():
        if system == text:
            return name
    if system == fr.DEFINE_PROBE_PROMPT:
        return "probe"
    if system == pr.COMPARISON_PROMPT:
        return "comparison"
    raise AssertionError(f"unknown system prompt: {system[:60]!r}")


def parse_user(step: str, user: str) -> dict:
    """The one item a call carries (probe and comparison have a header line)."""
    if step in ("probe", "comparison"):
        lines = user.splitlines()[1:]
        assert len(lines) == 1, f"{step}: {len(lines)} items in one call"
        return json.loads(lines[0])
    return json.loads(user)


def synthetic(step: str, item: dict, *, relation: str = "same") -> str:
    one = {"id": 1}
    if step == "probe":
        one.update(reason="A real word.", definition="d", known=True)
    elif step == "sense":
        one.update(label=item["label"], note="n.", first_thought="f", first_thought_said_of="people",
                   readings=[{"reading": f"you are {item['label']}", "rank": "primary"}], usable=True)
    elif step == "established":
        one.update(reason="r.", established="well_known", first_thought_in_the_way=False)
    elif step == "vague":
        one.update(reason="r.", leaves_something_out=False, missing=None, fits_many_in_different_ways=False)
    elif step == "kind":
        one.update(reason="r.", kind="trait", membership_kind=None)
    elif step == "same_sense":
        one.update(reason="r.", relation="same")
    elif step == "gloss":
        one.update(gloss="This means doing the thing the reading says.")
    elif step == "alignment":
        one.update(reason="r.", alignment=0)
    elif step == "descriptors":
        one.update(reason="r.", region="social_interpersonal", enactable_in_text=2)
    elif step == "comparison":
        one.update(label=item["label"], reason="r.", relation=relation, confidence=0.9)
    return json.dumps({"results": [one]})


def make_responder(*, override: Optional[Callable[[str, dict, dict], Optional[str]]] = None,
                   tokens=(500, 100)) -> Callable[[dict], object]:
    """A ``FakeAsyncAnthropic`` responder: the recorded answer for the step and item, else a synthetic
    one.  ``override(step, item, kwargs)`` may return a text to send instead (or None)."""
    rec = recorded()
    # The graded alignment answers were given on the live pilot's glosses, which differ from the
    # glosses this replay produces, so for that step alone an answer is also found by label.
    by_label = {r["sent"]["label"]: r["raw"] for r in load_jsonl("recorded_answers.jsonl")
                if r["step"] == "alignment"}

    def responder(kw):
        step = step_of_system(system_text(kw))
        item = parse_user(step, user_text(kw))
        if override is not None:
            got = override(step, item, kw)
            if got is not None:
                return make_response(got, input_tokens=tokens[0], output_tokens=tokens[1])
        text = (rec.get((step, canon(item))) or (by_label.get(item["label"]) if step == "alignment" else None)
                or synthetic(step, item))
        return make_response(text, input_tokens=tokens[0], output_tokens=tokens[1])

    return responder


def test_items(n: Optional[int] = None, *, intended: Optional[dict] = None):
    """FilterItems for the 99 test words (labels as in the probes), keyed like the platform."""
    from assistant_axis.gapgen.filter import FilterItem
    from assistant_axis.gapgen.normalize import make_key, normalize_candidate
    out = []
    for e in load_jsonl("expected_outcomes.jsonl")[:n]:
        nc = normalize_candidate(e["word"])
        out.append(FilterItem(key=make_key(nc.stem, 1), label=nc.label,
                              intended_sense=(intended or {}).get(e["word"]),
                              meta={"stratum": e["group"], "expected": e["outcome"]}))
    return out


test_items.__test__ = False  # not a pytest test
