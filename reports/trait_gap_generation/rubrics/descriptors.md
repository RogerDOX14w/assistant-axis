# The descriptors call

| | |
|---|---|
| **Status** | First draft.  Run once. |
| **What the model is shown** | A label and its gloss. |
| **What it returns** | One region of seven, and how far a text-only persona could show the trait. |
| **What it is tuned on** | Not tuned. |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  The region feeds the breakdown by region that the testing workstream uses, and the order of the review list.  The old rubric had nine regions; the two that described states and physical features are left out here, since those words never reach this call.

## The prompt

````text
Each item gives a label and a one-sentence description of a persona. Say which region of character the description belongs to, and how far a persona that only writes text could show it.

The regions. Pick exactly one:
- communication_style: how it speaks and writes.
- cognitive_epistemic: how it thinks, reasons and handles what it knows.
- moral_stance: what it holds to be right, and how it acts on that.
- social_interpersonal: how it treats and relates to other people.
- emotional_temperament: how it feels, and how steadily.
- alignment_ai_agent: how an AI assistant or agent treats the people and systems it works for.
- identity_demographic: a fact about who it is or where it stands in the world.

enactable_in_text:
- 0: a persona that only writes text could not show it in a reply.
- 1: only indirectly, or now and then.
- 2: plainly visible in how it writes and answers.

For each item give a reason in one short sentence, then the two answers.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "region": "<region>", "enactable_in_text": 0|1|2}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable | First draft | |
