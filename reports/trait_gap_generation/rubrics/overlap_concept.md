# Overlap call, rubric A: concept similarity

| | |
|---|---|
| **Status** | **Draft 6 (2026-10-06), pinned as version 6, awaiting Roger's pass before the M3 pilot**: draft 5's one-pair-per-call rewrite plus A2's line 2 (the change log has both).  The scale lines other than line 2 are still draft 2's.  Selected as the M3 overlap rubric on 2026-10-06, provisional until the pilot; B is the comparison arm of the test, no longer in play.  Earlier: draft 4 (2026-10-03), pinned as version 4: draft 2's text again, byte for byte (the pin records `"same_text_as": 2`).  Draft 3's added sentence on the answer's keys was taken out on Roger's word after the confirmation rerun showed it did not stop the extra keys (see the change log).  Draft 2, signed off by Roger on 2026-10-03 (commit 45f2aa7), was moved here unchanged from [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md) and pinned as version 2 (the draft number).  The test's leading candidate for the M3 overlap call; Roger keeps both rubrics in play until his manual review (2026-10-03).  Decided: the overlap call runs on Sonnet 5.5, not Haiku (to be re-evaluated when Haiku 5.5 arrives).  Not a split-filter prompt: the M3 overlap call.  First run: the pre-pilot test of both overlap rubrics, [m3_overlap_test_readout.md](../m3_overlap_test_readout.md) (being written at the time of the move). |
| **What it is for** | Step 5 of the M3 design ([coding_plan_platform.md](../coding_plan_platform.md), last section): for a candidate trait and the existing traits the relation call judged *similar*, how similar are their concepts?  Roger's preference for the overlap call (2026-10-02: "ask about how similar the concepts are, rather than how often a persona showing one would show the other"); [overlap_cooccurrence.md](./overlap_cooccurrence.md) is the comparison arm. |
| **What the model is shown** | Since draft 5 (one pair per call): one JSON object as the user turn, the target's label and description and one other trait's, labels in display form, no ids, no embedding scores, ranks or arrangement marks.  Drafts 1-4 sent a numbered list of other traits (the test's form); the rendered sample is below the prompt. |
| **What it returns** | A reason, then a similarity of 0 to 4, or "opposite", or "unsure", as one JSON object. |
| **Model** | Under test: Haiku 4.5, Sonnet 5.5 and Opus 5.5, temperature 0 where the model accepts it, one target per call.  The M3 design expects Sonnet, with *unsure* passed to Opus. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md)).  Leave the fence lines
themselves alone.  A changed text is pinned with `rubric_pins.py bump overlap_concept --why '...'` before a
paid run will use it.  Notes for me go under "Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona trait, the target ("target"), and one other persona trait ("other"), each with a one-sentence description. Say how similar the other trait's concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the other trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}
````

## Rendered sample (draft 5, one pair per call)

What the model receives, as the M3 build will send it: the block above as the system prompt, and this
user turn, labels in display form, no ids, no scores.  Target [extroverted](../../../data/traits/instructions/extroverted.json),
other [gregarious](../../../data/traits/instructions/gregarious.json):

```
{"target": {"label": "extroverted", "description": "This means being energized by company and drained by solitude: seeking people out, speaking freely in groups, preferring a crowd to one or two close friends, and needing company after time alone."},
 "other": {"label": "gregarious", "description": "This means showing highly sociable, outgoing behavior that actively seeks interaction, connection, and the company of others."}}
```

The expected answer: `{"reason": "...", "similarity": 3}` (or whatever the model judges).

## Your notes

## Change log

Drafts 1 and 2 were written in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md), which held both
rubrics; their rows are copied from it as they stand.

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Claude | First draft of both rubrics and the test | Roger, 2026-10-02: concept similarity as the primary, co-occurrence as the comparison arm |
| 2 | Roger and Claude | Both rubrics: "idea" replaced by "concept" (three places in A, two in B); the opening now says "You are given one JSON object: a persona trait, the target ("target") ... a numbered list of other persona traits ("traits")" instead of "Each item gives ..."; the answer's `id` is "the listed trait's id"; a rendered sample added; A's answer 2 reads "They share a core, but each adds something the other lacks" (was "and"); A's answer 0 example is now chatty and plainspoken (both about speech, how much against how directly), replacing outdoorsy and punctual, which share no area and so did not illustrate "connected at most by belonging to the same broad area"; B's answer 0 now reads "less often than in anyone else, down to never: having the target trait makes this one less likely" (was "rarely or never ... makes this one unlikely"), so that 0 means below the base rate that answer 1 names and a mild negative relation has an answer | Roger, 2026-10-03: the scale already says "concept", and mixing the words could read as two tests, while "idea" invites a looser reading that pushes scores up.  "Each item" was left over from the filter's multi-item rubrics: each overlap call carries exactly one target, and the ids number the listed traits.  Both mismatches show at once in a rendered sample, now the practice in AGENT_NOTES |
| 3 | Claude | Added after "Return one row per listed trait, in the order given.": "Use only the keys shown: do not add the trait's label or any other key, and give each row once." | The test ([m3_overlap_test_readout.md](../m3_overlap_test_readout.md)): Sonnet 5.5 broke the answer format in 8 of 180 calls, 7 times by adding a `"label"` key and then writing "Correction:" and the whole answer again, once by leaving a key out.  Roger, 2026-10-03: make the change and rerun to confirm |
| 6 | Roger and Claude | Line 2 is A2's: "They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks." (was "... but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.") | In the arms experiment's round 2 ([m3_overlap_arms_readout.md](../m3_overlap_arms_readout.md)) this wording halved the answers of 2 whose reason describes a containment (Sonnet 35 to 16, Opus 20 to 5 on the confusion subset) without moving the decisions under the Sonnet-then-Opus rule.  Roger, 2026-10-06: carry it forward now that the file is open for the one-pair rewrite |
| 5 | Claude, for Roger's pass | Rewritten for one pair per call: the opening names one other trait ("other") instead of a numbered list; "for each listed trait" and the per-row answer format go; the answer is one object, `{"reason", "similarity"}`, with no `id`; "the listed trait" becomes "the other trait" in the "opposite" line.  The scale lines and the second paragraph are byte for byte draft 2's | The M3 design settled on one pair per call (2026-10-06: an identical prompt repeated agrees with itself 92-98%, a reordered list 86-89%; the rubric caches, so the cost is the same).  Roger: "This will need rewriting for single pair."  Dropping the ids and the results array also removes the slot the models copied the label key into.  The scale is unchanged so that the arms measurements carry over |
| 4 | Roger and Claude | The sentence added in draft 3 removed; the text is draft 2's again (`rubric_pins.py bump --revert-to 2`) | The rerun (`overlap_test_2`, [m3_overlap_test_readout.md](../m3_overlap_test_readout.md), "Rerun with rubric A draft 3"): every answer parsed at the first attempt, but 19 of Sonnet's 180 first answers and 9 of Opus's still had an extra key, always in the slot after `"id"` where the input rows carry `"label"`, and with correct label values: the models copy the input row's shape.  The instruction made it rarer but turned some of it into odd keys (`"color": ""`, Opus's `label_note`, `label_free`).  The parser ignores extra keys, so nothing is lost.  Roger, 2026-10-03: "a known, harmless issue, easily ignored ... saying not to include the label seems actively unhelpful — drop that" |
