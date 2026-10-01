# Draft: the alignment check on a scale

| | |
|---|---|
| **Status** | Draft 4: Roger's edits of 2026-09-30, then two rounds of rewording after runs on the whole corpus.  **Adopted the same day**: its text is now the prompt of [alignment.md](./rubrics/alignment.md), draft 3.  Edit that file from here on; this one is kept as the record of how the wording was reached. |
| **What the model is shown** | A label and its gloss, as now. |
| **What it returns** | 0, 1, 2 or 3, with a reason. |
| **What it is tuned on** | Not tuned.  Run once on the 69 glosses of the live pilot; results in [sense_call_probe.md](./sense_call_probe.md). |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Roger, 2026-09-30, on the yes or no check: "technically it's not wrong, but I agree, it's casting the
net quite wide.  To some extent this is a matter of degree: maybe we should rate it on a 0-3 scale (or
1-3 plus absent), rather than treating it as a binary, and then use it as input to the dupe/gap
decision, so density increases gradually as you get closer to alignment rather than a sudden
transition?"

This file is kept outside [rubrics/](./rubrics/) on purpose.  That directory is checked for
uncommitted changes before every paid run of the platform, and a draft there would stop one.  If the
scale is adopted, its text replaces the block in [alignment.md](./rubrics/alignment.md) as draft 3, and
the build agent changes the parser and the record to carry a number.

**To edit:** change the text inside the block below, as with the rubric files.

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
| 1 | Fable | First draft of the scale | Roger's proposal of 2026-09-30.  The six headings are those of the yes or no check.  The example words were checked against the corpus, the queue, the validation file and the test words |
| 2 | Roger | A seventh heading, on harm, placed first.  Answer 3: "directly about", and "For example," before the example.  Answer 2: "not directly about", "clearly" for "plainly", and "on at least one of them" | His edits of 2026-09-30 |
| 2 | Fable | The harm heading reworded from "seeking to avoid causing or assisting with harm" to "avoiding harm to people, or causing or assisting it" | The other six headings each name both directions, as in "deferring to those it works for, or resisting them".  As Roger wrote it, the heading named only the good direction, and a description of a persona that does harm might not have been counted under it.  No typos found in his edits |
| 3 | Fable | Answer 3 now says the conduct must be named "in so many words", with five plain instances.  Answer 2 now says the description is "about something else, a general way of working or of treating people", and the conduct follows "as a matter of course".  Answer 1 gained "or in particular circumstances".  Answer 0 gained plain facts of a persona's life.  A new closing rule: a reason that needs "relates to", "supports", "undermines" or "conflicts with" is 2 at most.  The opening says the persona is one an AI assistant might take on | Roger, 2026-09-30: "the lack of 2's is odd.  Try a larger sample, and if this holds up, adjust the rubric phrasing."  Draft 2 on all 659 corpus traits gave 0 to 356, 1 to 126, 2 to 57 and 3 to 120.  So 2 is used, but 3 is too wide: it went to renter (deference to a landlord), to frequent poster (seeking approval online), and to approximate, modest and indecisive, each with a reason that said "relates to" or "conflicts with" |
| 4 | Fable | Answer 2 back to Roger's wording, with "in most of what it does, and you can say which one and in which direction" added, and "a general way of working or of treating people" taken out.  The closing rule about the words of the reason taken out.  "deceiving" added to the instances under answer 3.  The harm heading now says "serious harm", with a closing line that being unpleasant to deal with is not harm.  Answer 0 now lists manner, mood, taste, style of speech and opinions about the world | Draft 3 mended answer 3 (renter and frequent poster fell to 0, modest to 0) and broke answer 2, which rose from 57 corpus traits to 195.  The phrase about a general way of treating people was taken as the definition: calm, friendly, easygoing, secular and sarcastic all got 2, with reasons saying the description "does not directly name any" of the seven.  The rule about the reason's words pushed manipulative and scheming down from 3 to 2, since their reasons said "conflicts with honesty" |
