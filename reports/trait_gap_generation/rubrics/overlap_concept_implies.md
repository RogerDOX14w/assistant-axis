# Overlap call, rubric A2: concept similarity with the implication test

| | |
|---|---|
| **Status** | Draft 1 (2026-10-04), pinned as version 1.  Round 2 of the overlap rubric arms experiment ([coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md), "Round 2: the clarified lines, on the confusion subset"): rubric A ([overlap_concept.md](./overlap_concept.md), version 4) with its lines 3 and 2 redrafted around the one-way implication test, on Roger's request of 2026-10-04, and final for that experiment.  Rubric A's own file and pin are untouched (A is the production candidate).  Not a split-filter prompt: a variant of the M3 overlap call's rubric A. |
| **What it is for** | Round 1 ([m3_overlap_arms_readout.md](../m3_overlap_arms_readout.md)) found both models, Sonnet about twice as often as Opus, describing a containment in their reason and then answering 2 ("overlap"), at the same rate under every arm.  The words being misread are "adds" and "lacks": the shared core gets counted as the plainer trait's addition.  Here line 3 gives the test (anyone who has one of the two traits has the other too, at least in one direction) and line 2 says that neither implies the other.  The scale is rubric A's own, 0 to 4, and so is the decision scale. |
| **What the model is shown** | As for rubric A: one JSON object as the user turn, the target's label and description and a numbered list of other traits (`id` 1 to n) with theirs, labels in display form, in random order, with no embedding scores, ranks or arrangement marks. |
| **What it returns** | For each listed trait, a reason, then a similarity of 0 to 4, or "opposite", or "unsure". |
| **Model** | Under test: Sonnet 5.5 and Opus 5.5, one target per call, two passes (the second with the listed traits in a fresh order), first on the calls that hold round 1's confusion subset. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is in [m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md)).  Leave the fence lines
themselves alone.  A changed text is pinned with `rubric_pins.py bump overlap_concept_implies --why '...'`
before a paid run will use it.  Notes for me go under "Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. The test: anyone who has one of the two traits has the other too, at least in one direction: a fussy eater is fussy, a boastful person is proud, a miserly person is penny-pinching, though not necessarily the reverse. The richer one may be the plainer one narrowed to a domain, carried further, or with something added. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but neither implies the other: a persona can have either without the other, as a studious person need not be bookish and a bookish one need not be studious; each adds something the other lacks.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable's brief (text), Claude (file) | Rubric A's text (version 4, draft 2's) with lines 3 and 2 replaced by the lines of [coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md), "Round 2"; everything else is rubric A's, byte for byte.  Copied unchanged; no mechanical fault was found in the rendered prompt.  New example words proud and boastful, checked free of the corpus on 2026-10-04 with fussy, fussy eater and the round-1 words | Round 1: both models describe a containment in the reason and then answer 2 (Sonnet 8-13% of its 2s, Opus 4-8%, under every arm).  The words misread are "adds" and "lacks", so the redraft gives the one-way implication test instead.  Roger, 2026-10-04: redraft the 2 and 3 lines on each form and test the redrafts first on the pairs where the confusion has been seen |
