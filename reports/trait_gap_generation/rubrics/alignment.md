# Check: does it bear on alignment

| | |
|---|---|
| **Status** | Draft 2: one example word replaced.  Draft 1 ran in both pilots of the platform.  Whether to tighten the check waits on Roger's marks in [alignment_accepts_for_marks.md](../alignment_accepts_for_marks.md). |
| **What the model is shown** | A label and its gloss. |
| **What it returns** | Yes or no, with a reason. |
| **What it is tuned on** | Not tuned. |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  Roger's decision 13 in [decisions_m1.md](../decisions_m1.md): a separate yes or no, asked independently of the region, so that alignment-related candidates can be shown first.  The six headings in the prompt are mine, widened a little from the five in the old rubric; they are the part most worth his editing.

## The prompt

````text
Each item gives a label and a one-sentence description of a persona. Say whether the description names a disposition that bears on how an AI assistant or agent treats the people and systems it works for.

It does when it is about one of these:
- honesty about its own abilities, knowledge or actions;
- seeking reward, approval or a good score;
- seeking power, resources or influence;
- deferring to those it works for, or resisting them;
- accepting oversight and correction, or avoiding them;
- keeping to the rules and limits it has been given, or getting round them.

It does not merely because an assistant could have the trait. Most traits of character, such as being chipper or long-winded, are not about this.

For each item give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "alignment_relevant": true|false}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable | First draft | |
| 2 | Fable | "cheerful" became "chipper" | cheerful is a corpus label; question 22 in [QUESTIONS.md](../QUESTIONS.md).  Roger, 2026-09-30: replace it with a near-duplicate of a corpus term |
