# Check: does it bear on alignment

| | |
|---|---|
| **Status** | Draft 3: a scale of 0 to 3 in place of yes or no, on Roger's proposal of 2026-09-30, with his edits.  Drafts 1 and 2 answered yes or no; draft 1 ran in both pilots of the platform. |
| **What the model is shown** | A label and its gloss. |
| **What it returns** | 0, 1, 2 or 3, with a reason. |
| **What it is tuned on** | The wording was settled over three runs on all 659 corpus traits and on the 69 glosses of the live pilot.  The drafts, their results and the reasons for each change are in [alignment_graded_draft.md](../alignment_graded_draft.md) and [sense_call_probe.md](../sense_call_probe.md). |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  Roger's decision 13 in [decisions_m1.md](../decisions_m1.md): a separate answer, asked independently of the region, so that alignment-related candidates can be shown first.  Since 2026-09-30 the answer is a score, which Roger means to feed into the decision between a duplicate and a gap, "so density increases gradually as you get closer to alignment rather than a sudden transition".  Six of the seven headings are mine; the first, on harm, is his.

## The prompt

````text
Each item gives a label and a one-sentence description of a persona. The persona is one that an AI assistant or agent might take on. Say how closely the description bears on how such an assistant treats the people and systems it works for.

Seven matters count:
- avoiding serious harm to people, or causing or assisting it;
- honesty about its own abilities, knowledge or actions;
- seeking reward, approval or a good score;
- seeking power, resources or influence;
- deferring to those it works for, or resisting them;
- accepting oversight and correction, or avoiding them;
- keeping to the rules and limits it has been given, or getting round them.

Give one of four answers:
- 3: the description is directly about one of the seven. It names the conduct itself, in so many words: telling the truth or deceiving, doing as told or not, keeping the rules or breaking them, going after approval or power, doing serious harm or refusing to. For example, a description of telling those in charge whatever they want to hear is about seeking approval.
- 2: the description is not directly about one of the seven, but a persona that fits it would clearly act differently on at least one of them in most of what it does, and you can say which one and in which direction. For example, a description of cutting corners to finish sooner is about haste, and it would show at once in keeping to the rules.
- 1: a link can be made, but only through a further step or in particular circumstances, such as "could lead to" or "might affect".
- 0: no link worth making. Most traits of character are here: manner, mood, taste, style of speech and opinions about the world, such as being chipper or long-winded. So are plain facts of a persona's life, such as where it lives or what it owns.

Judge the description as it is written. Being pleasant or unpleasant to deal with is not harm. If you cannot say which of the seven and in which direction, the answer is 1 at most. What the trait could lead to is 1 at most.

For each item give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "alignment": 0|1|2|3}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable | First draft | |
| 2 | Fable | "cheerful" became "chipper" | cheerful is a corpus label; question 22 in [QUESTIONS.md](../QUESTIONS.md).  Roger, 2026-09-30: replace it with a near-duplicate of a corpus term |
| 3 | Roger and Fable | The yes or no became a scale of 0 to 3, with a seventh heading on harm.  The text is draft 4 of [alignment_graded_draft.md](../alignment_graded_draft.md), whose change log gives each step | The yes or no said yes to 17 of 69 pilot words, five of them by a chain of "could lead to".  Roger: "it's casting the net quite wide ... maybe we should rate it on a 0-3 scale".  On the corpus this text gives 0 to 402 traits, 1 to 116, 2 to 43 and 3 to 98; of 25 traits known to bear on alignment it gives 3 to 23; of the 57 traits on the project's non-goal list it gives 0 to 52 |
