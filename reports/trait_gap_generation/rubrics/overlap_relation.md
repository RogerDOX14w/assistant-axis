# Overlap call, rubric D: relation first

| | |
|---|---|
| **Status** | Draft 1 (2026-10-04), pinned as version 1.  Arm 2 of the overlap rubric arms experiment ([coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md)), written by Fable on Roger's go of 2026-10-04 ("OK, go gather data") and final for that experiment.  Not a split-filter prompt: a variant of the M3 overlap call's rubric A ([overlap_concept.md](./overlap_concept.md)). |
| **What it is for** | The overlap test ([m3_overlap_test_readout.md](../m3_overlap_test_readout.md)) found the large models seeing the shape of a pair alike (one trait adds something, the other only shifts emphasis) and rounding it to a number differently.  Here the model names the kind of relationship instead of a number, with the direction of a containment, and the score is derived: same -> 4, variant -> 3, contains -> 3, overlap -> 2, neighbours -> 1, different -> 0 on the decision scale (rubric A's 0 to 4, where the cut-offs are set); "opposite" and "unsure" as in rubric A. |
| **What the model is shown** | As for rubric A: one JSON object as the user turn, the target's label and description and a numbered list of other traits (`id` 1 to n) with theirs, labels in display form, in random order, with no embedding scores, ranks or arrangement marks. |
| **What it returns** | For each listed trait, a reason, then a relation (same, variant, contains, overlap, neighbours, different, opposite or unsure), and for "contains" which of the two is the wider (`"wider": "target"` or `"listed"`). |
| **Model** | Under test: Sonnet 5.5 and Opus 5.5, one target per call, two passes (the second with the listed traits in a fresh order). |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md)).  Leave the fence lines
themselves alone.  A changed text is pinned with `rubric_pins.py bump overlap_relation --why '...'` before
a paid run will use it.  Notes for me go under "Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept is related to the target's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- "same": the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- "variant": the same concept, differing only in degree, strength or emphasis; neither adds anything the other lacks. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- "contains": one of the two is the other narrowed to a single domain, or the other with something more added to it, and the narrower or plainer one adds nothing of its own. Say which is the wider one. For example, fussy and fussy eater: fussy is the wider.
- "overlap": overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- "neighbours": related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- "different": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "same"|"variant"|"contains"|"overlap"|"neighbours"|"different"|"opposite"|"unsure", "wider": "target"|"listed"}]}
Give "wider" only when the relation is "contains". Return one row per listed trait, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable (text), Claude (file) | Rubric A's text (version 4, draft 2's) with three changes: the opening's second sentence asks how the listed trait's concept is related to the target's (was: how similar it is, the same concept or different ones); the scale lines name relations instead of numbers, with the direction of a containment; and the answer format asks for `"relation"` and, for "contains", `"wider"`.  A's second paragraph is unchanged.  Copied from [coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md) unchanged; no mechanical fault was found in the rendered prompt.  The example pair fussy and fussy eater was checked against the corpus, the seed queue and the validation file on 2026-10-04 | The 2 / 3 disagreement of the overlap test: the models describe the same shape of a pair and round it to different numbers.  Naming the relation first, and deriving the number, tests whether the disagreement is in the rounding |
