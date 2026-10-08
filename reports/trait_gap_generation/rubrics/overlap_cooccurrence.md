# Overlap call, rubric B: co-occurrence

| | |
|---|---|
| **Status** | Draft 2, signed off by Roger on 2026-10-03 (commit 45f2aa7), moved here unchanged from [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md) and pinned as version 2 (the draft number).  Not a split-filter prompt: the comparison arm of the M3 overlap call.  First run: the pre-pilot test of both overlap rubrics, [m3_overlap_test_readout.md](../m3_overlap_test_readout.md) (being written at the time of the move). |
| **What it is for** | The comparison arm for step 5 of the M3 design ([coding_plan_platform.md](../coding_plan_platform.md), last section): how often would a persona with the candidate trait also show each existing trait the relation call judged *similar*?  Roger, 2026-10-02: "we can, of course, try both, and find out which works better"; the primary is [overlap_concept.md](./overlap_concept.md).  Asymmetric: the candidate is always the target. |
| **What the model is shown** | One JSON object as the user turn: the target's label and description, and a numbered list of other traits (`id` 1 to n) with theirs, labels in display form, in random order, with no embedding scores, ranks or arrangement marks. |
| **What it returns** | For each listed trait, a reason, then a co-occurrence of 0 to 4, or "unsure". |
| **Model** | Not used by the pipeline (rubric A, [overlap_concept.md](./overlap_concept.md), was chosen for the M3 overlap call: Sonnet 5.5 first, Opus 5.5 second).  Tested in the pre-pilot test of 2026-10-03 on Haiku 4.5, Sonnet 5.5 and Opus 5.5, temperature 0 where the model accepts it, one target per call. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md)).  Leave the fence lines
themselves alone.  A changed text is pinned with `rubric_pins.py bump overlap_cooccurrence --why '...'` before a
paid run will use it.  Notes for me go under "Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how often a persona that has the target trait would also show the listed trait.

Judge how the two go together in a person, not whether they are the same concept. Two traits can be different concepts and still nearly always go together.

Give one of these answers for each listed trait:
- 4: almost always: a persona with the target trait would show this one too. For example, a talkative persona would be loquacious.
- 3: usually. For example, a studious persona would usually be bookish.
- 2: often, but far from always. For example, a punctual persona would often be tidy.
- 1: sometimes, about as often as anyone else. For example, an outdoorsy persona would sometimes be punctual.
- 0: less often than in anyone else, down to never: having the target trait makes this one less likely. For example, a cheery persona would rarely be morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "co_occurrence": 0|1|2|3|4|"unsure"}]}
Return one row per listed trait, in the order given.
````

## Your notes

## Change log

Drafts 1 and 2 were written in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md), which held both
rubrics; their rows are copied from it as they stand.

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Claude | First draft of both rubrics and the test | Roger, 2026-10-02: concept similarity as the primary, co-occurrence as the comparison arm |
| 2 | Roger and Claude | Both rubrics: "idea" replaced by "concept" (three places in A, two in B); the opening now says "You are given one JSON object: a persona trait, the target ("target") ... a numbered list of other persona traits ("traits")" instead of "Each item gives ..."; the answer's `id` is "the listed trait's id"; a rendered sample added; A's answer 2 reads "They share a core, but each adds something the other lacks" (was "and"); A's answer 0 example is now chatty and plainspoken (both about speech, how much against how directly), replacing outdoorsy and punctual, which share no area and so did not illustrate "connected at most by belonging to the same broad area"; B's answer 0 now reads "less often than in anyone else, down to never: having the target trait makes this one less likely" (was "rarely or never ... makes this one unlikely"), so that 0 means below the base rate that answer 1 names and a mild negative relation has an answer | Roger, 2026-10-03: the scale already says "concept", and mixing the words could read as two tests, while "idea" invites a looser reading that pushes scores up.  "Each item" was left over from the filter's multi-item rubrics: each overlap call carries exactly one target, and the ids number the listed traits.  Both mismatches show at once in a rendered sample, now the practice in AGENT_NOTES |
