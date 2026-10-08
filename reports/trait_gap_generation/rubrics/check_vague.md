# Check: is the instruction too vague to act on

| | |
|---|---|
| **Status** | Draft 3.  Roger's edit of 2026-09-29, and my rewrite of my own sentence explaining the second test.  Run twice, batched; to be rerun one item per call. |
| **What the model is shown** | A label and its most likely reading, from step 1. |
| **What it returns** | Whether the label leaves something out, and what; whether the reading fits many people in different ways. |
| **What it is tuned on** | Not yet tuned.  Roger's notes mark common, integrated, unconditioned, one-time, southeastern and raised as vague or unclear. |
| **Model** | Haiku 5.5 from 2026-10-08 (no temperature: it refuses one; Haiku 4.5 at temperature 0 before), once for each primary reading of each of the verdict's three readings by default (`--readings`); Sonnet 5.5 for a word chosen for a second opinion.  One item per call.  Sent uncached (about 440 tokens, under Haiku 5.5's 512-token minimum). |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  Roger asked that vague words be caught, or at least flagged, at this stage.  Under his bar a flag is a note.  A word is turned away only when it is too unclear to use even if no clearer word exists.

## The prompt

````text
Each item gives a label and the most likely reading of the instruction "You are <label>." as said of a persona. Say whether the instruction is too vague to act on.

An instruction can be vague in two ways.
- The label leaves something out that the reader needs: "adjacent" to what, "former" what, "accustomed" to what, "northern" part of what. A persona given the instruction would have to guess the missing part.
- The reading is so general that it fits many people in different ways: "You are unusual." and "You are special." are like that. The instruction does not say how the persona should think, speak or act, so a persona given it would have to decide that for itself. A reading is not vague merely because people who share it differ in other respects; everyone who is hot-headed is hot-headed in much the same way, whatever else they are.

For each item:
- reason: one short sentence. Write this first.
- leaves_something_out: true or false. When true, say in a few words what is missing.
- fits_many_in_different_ways: true or false.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "leaves_something_out": true|false, "missing": "<a few words>"|null, "fits_many_in_different_ways": true|false}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 2 | Roger | The sentence that named personality traits removed | His edit |
| 3 | Fable | The sentence after "fits many people in different ways" rewritten, with two examples | Mine had said "two personas could both follow the instruction faithfully and have nothing in common".  That is true of any trait at all, and the check flagged 35 of 48 words, argumentative and lawless among them.  Roger's phrasing is kept.  The example words were chosen to be absent from the corpus, the queue and the test words |
