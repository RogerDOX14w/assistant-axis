# Overlap call, the broader check: which of two close traits is the broader concept

| | |
|---|---|
| **Status** | **Draft 1 (2026-10-12), pinned as version 1 in code** (`novelty.BROADER_PINS` in [novelty.py](../../../assistant_axis/gapgen/novelty.py); not yet in [versions.json](./versions.json), see "Pin" below).  Written for proposal P3 of the M3 gate audit ([m3_novelty.md](../../code_review_2026-10-12/gate_audits/m3_novelty.md), §§ 7.7 and 9), on Roger's decision of 2026-10-12 to pilot it on the audit's 100 marked rows first.  **Not used by any production run until Roger has read the pilot**: the check runs only under `novelty_score.py score --broader-check` (off by default) and in the pilot command `novelty_score.py broader-pilot`. |
| **What it is for** | The false covers M3 makes have one shape (the audit's § 7.7; Roger's cover audit of 2026-10-09, decision 18 (c)): a corpus trait that is a narrower case of the candidate covers it, because rubric A's line 3 ("the same concept, differing only in scope, degree or emphasis") has no direction.  Prejudiced and bigoted were covered by [homophobic](../../../data/traits/instructions/homophobic.json), prejudicial by [ageist](../../../data/traits/instructions/ageist.json), self-destructive by [self_harming](../../../data/traits/instructions/self_harming.json).  This call is one more reading on a cover whose best overlap reading is exactly 3: which of the two is the broader concept?  The cover stands only when the corpus trait is at least as broad as the candidate; otherwise the walk goes on to the next shortlisted trait and the row carries the review flag `cover_narrower`. |
| **What the model is shown** | One JSON object as the user turn: two traits under the neutral keys `first` and `second`, each with its label (judge display form) and its description (the candidate's M1 gloss, the corpus trait's description), laid out as rubric A's one-pair form.  Nothing says which is the candidate.  **Every pair is read twice, once in each order** (the candidate first, then the corpus trait first), as the judging rule asks of any prompt that shows two items side by side (AGENT_NOTES, "Comparing arms with an LLM judge: order and position bias"). |
| **What it returns** | A reason, then `first`, `second`, `neither` or `unsure`, as one JSON object. |
| **How the two readings decide** | Each reading is turned to the candidate's side: +1 when it names the candidate the broader, -1 when it names the corpus trait, 0 for `neither` or `unsure`.  **Default gate `mean`**: the cover is undone when the mean of the two scores is above 0 (one order names the candidate and the other says `neither` or `unsure`, or both name it); two orders that contradict each other leave the cover standing.  The pilot also reports the gates `both` (both orders must name the candidate) and `either` (one is enough), from the same readings.  A reading that never parsed counts as no evidence. |
| **Model** | Sonnet 5.5 by default (`--broader-model`), the overlap call's first model, no temperature (it refuses one), the prompt marked for the cache.  The pilot runs every model it is given (`--model`, repeatable), so that Haiku 5.5 (a tenth of the price) can be compared on the same rows; the choice is Roger's after the pilot. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
samples are below).  Leave the fence lines themselves alone.  A changed text must be pinned as a new
version (today in `novelty.BROADER_PINS`) before a run will use it.  Notes for me go under "Your notes",
outside the block.

## The prompt

````text
You are given one JSON object: two persona traits, "first" and "second", each with a one-sentence description. The two have been judged close: much the same concept, differing in scope, degree or emphasis. Say whether they differ in scope: whether one of them is the broader concept, covering everything the other covers and more besides, so that the other is a narrower case of it.

Judge the meaning of the two descriptions. One trait is the broader when the other is the same quality confined to one kind of target, one kind of situation or one way of showing it: a love of opera is a narrower case of a love of music, and tidiness at one's desk a narrower case of tidiness everywhere. Being held more strongly, or described with a different emphasis, does not make a trait broader: penny-pinching and miserly cover the same ground, miserly carried further.

Give one of these answers:
- "first": the first trait is the broader concept; the second is a narrower case of it.
- "second": the second trait is the broader concept; the first is a narrower case of it.
- "neither": neither is broader: they cover the same ground, differing at most in degree or emphasis, or each covers something the other does not.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "broader": "first"|"second"|"neither"|"unsure"}
````

## Rendered samples

What the model receives (rendered by `novelty_score.py broader-pilot --no-audit --keys prejudiced#1 censorious#1
--dry-run` on 2026-10-12, no call): the block above as the system prompt (marked for the cache; about 600 tokens,
over Sonnet 5.5's 512-token minimum), `max_tokens` 4096, no temperature, and one of these user turns.  The texts are
those the cover's own overlap call was sent (its recorded request), labels in the judge display form.

**A known false cover, candidate first** (`prejudiced#1`, covered in the TDA run by
[homophobic](../../../data/traits/instructions/homophobic.json) at Sonnet 2, Opus 3; the audit's § 7.7):

```
{"first": {"label": "prejudiced", "description": "This means holding unfair, biased attitudes toward a group of people and judging its members by assumptions rather than by what each one actually does."},
 "second": {"label": "homophobic", "description": "This means treating gay and lesbian people's love as wrong or disgusting, shunning their partners and weddings, and joining in when they are mocked."}}
```

**The same pair, swapped** (the second reading of every checked pair):

```
{"first": {"label": "homophobic", "description": "This means treating gay and lesbian people's love as wrong or disgusting, shunning their partners and weddings, and joining in when they are mocked."},
 "second": {"label": "prejudiced", "description": "This means holding unfair, biased attitudes toward a group of people and judging its members by assumptions rather than by what each one actually does."}}
```

Expected: `"first"` then `"second"` (the candidate the broader both ways), so the cover is undone under every gate.

**A good cover, candidate first** (`censorious#1`, covered by [judgmental](../../../data/traits/instructions/judgmental.json)
at Sonnet 3, Opus 3; the audit read it "harsh fault-finding; censorious is it voiced"):

```
{"first": {"label": "censorious", "description": "This means harshly judging others' conduct and quickly condemning their faults, speaking of their mistakes with disapproval and a readiness to find fault."},
 "second": {"label": "judgmental", "description": "This means quickly forming negative opinions and making harsh assessments of others' choices, behaviors, or circumstances without considering multiple perspectives or showing understanding."}}
```

Expected: `"neither"` or `"second"` (judgmental at least as broad), so the cover stands.

## Pin

Pinned in code, not in [versions.json](./versions.json): adding a rubric there means adding its name to
`split_rubrics.M3_FILES` in [split_rubrics.py](../../../assistant_axis/gapgen/split_rubrics.py), which another
agent was editing on 2026-10-12, so the pin went into `novelty.BROADER_PINS` (version 1, the sha256 of the
block above) and [test_gapgen_novelty_rule3.py](../../../assistant_axis/tests/test_gapgen_novelty_rule3.py)
fails when the text changes without a new pin.  To move it: add `"overlap_broader": "overlap_broader.md"` to
`M3_FILES`, run `uv run python data_analysis/gap_generation/rubric_pins.py bump overlap_broader --version 1 --why
'First pin: draft 1 (the M3 gate audit, P3)'`, and have `load_broader_rubric` read the pin from there.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Claude (gate-audit fix agent) | First draft | Roger, 2026-10-12, on the M3 gate audit: a "which is broader" check on covers read at exactly 3, piloted on the audit's 100 marked rows before any use |
