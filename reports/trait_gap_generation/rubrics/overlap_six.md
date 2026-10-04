# Overlap call, rubric C: six rungs

| | |
|---|---|
| **Status** | Draft 1 (2026-10-04), pinned as version 1.  Arm 1 of the overlap rubric arms experiment ([coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md)), written by Fable on Roger's go of 2026-10-04 ("OK, go gather data") and final for that experiment.  Not a split-filter prompt: a variant of the M3 overlap call's rubric A ([overlap_concept.md](./overlap_concept.md)). |
| **What it is for** | The overlap test ([m3_overlap_test_readout.md](../m3_overlap_test_readout.md)) found the large models disagreeing on rubric A's 2 / 3 boundary, where a one-sided addition fits both lines.  Roger asked whether another step in the 1-3 range would make the judgement easier.  This is rubric A's text with its scale lines replaced by six rungs, 0 to 5, the 2-3 region split by who adds something: 5 the same concept, 4 the same concept differing in degree, strength or emphasis, 3 one contains the other, 2 overlapping concepts.  On the decision scale (rubric A's 0 to 4, where the cut-offs are set): 5 -> 4, 4 -> 3, 3 -> 3, 2 -> 2, 1 -> 1, 0 -> 0. |
| **What the model is shown** | As for rubric A: one JSON object as the user turn, the target's label and description and a numbered list of other traits (`id` 1 to n) with theirs, labels in display form, in random order, with no embedding scores, ranks or arrangement marks. |
| **What it returns** | For each listed trait, a reason, then a similarity of 0 to 5, or "opposite", or "unsure". |
| **Model** | Under test: Sonnet 5.5 and Opus 5.5, one target per call, two passes (the second with the listed traits in a fresh order). |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md)).  Leave the fence lines
themselves alone.  A changed text is pinned with `rubric_pins.py bump overlap_six --why '...'` before a
paid run will use it.  Notes for me go under "Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 5: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 4: the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 3: one contains the other: one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. For example, fussy and fussy eater: the same fussiness, narrowed to food.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|5|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable (text), Claude (file) | Rubric A's text (version 4, draft 2's) with its scale lines replaced by six rungs, 0 to 5, and the answer format's scale written `0\|1\|2\|3\|4\|5`; everything else is rubric A's, byte for byte.  Copied from [coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md) unchanged; no mechanical fault was found in the rendered prompt.  The example pair fussy and fussy eater was checked against the corpus, the seed queue and the validation file on 2026-10-04 (picky eater is the corpus's; fussy eater is its near-duplicate, which the hygiene rule wants) | The 2 / 3 disagreement of the overlap test: rubric A's 3 ("differing only in scope, degree or emphasis") and 2 ("each adds something the other lacks") both fit a one-sided addition.  Roger, 2026-10-04: would another step in the 1-3 range make the judgement easier? |
