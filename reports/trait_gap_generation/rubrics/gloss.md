# The gloss call

| | |
|---|---|
| **Status** | Draft 3.  One clause added to draft 2: for a plain fact, the fact comes before the length (Roger, 2026-09-30: "The fact wins").  Draft 2 ran in both pilots of the platform. |
| **What the model is shown** | A label and the reading that was accepted, from the earlier steps. |
| **What it returns** | One sentence describing the persona. |
| **What it is tuned on** | Not tuned beyond the form.  Both runs, with every gloss side by side, are in [sense_call_probe.md](../sense_call_probe.md). |
| **Model** | Haiku 4.5 at temperature 0; Sonnet 5.5 for a word chosen for a second opinion (Roger, 2026-09-29).  One item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**Where its rules come from.**  The project's description-writing rules, in the section "Description-writing rules for new seeds" of [trait-pairs.md](../../../.claude/rules/trait-pairs.md): the form, no label in the opening, a vice is a vice, inside voice, no naming of the opposite, memberships stated plainly.  The gloss is a first draft (Roger, 2026-09-29).  Before a word goes into the corpus its description is written by Opus or Fable, with the nearest corpus traits and the partner pole in view, and reviewed by Roger.  The gloss is there to be embedded, to feed the two checks after it, and to give that writer something to start from.

**It runs only for words that go on as traits.**  Words on the states queue get their draft from the states pass.

## The prompt

````text
Each item gives a label and one reading of the instruction "You are <label>." Write a one-sentence description of a persona that fits that reading. The description will be read beside the label, by someone who needs to know exactly what is meant.

How to write it:
- Begin "This means" and follow it at once with a verb in the -ing form: "This means keeping ...", "This means speaking ...", "This means being from ...". Go straight to what the persona does, thinks or says. Do not repeat the label in the opening; the label is already beside it.
- The sentence has no subject. Do not write "you", "your", "I", "my", "they" or "the persona", even where the reading you are given says "you". Where a possessive is needed, write "one's".
- One sentence, about 20 to 30 words.
- Describe a standing way of being, not a passing moment.
- Say it plainly. A fault is described as a fault and a virtue as a virtue. Do not soften or hedge: no "tends to", "sometimes", "may", "can", "overly", "too", "appropriately".
- Use the words the persona would use of itself, not the words of a case report: no "exhibits", "demonstrates", "engages in", "individuals who".
- Describe the persona itself, not what it urges on other people, and do not write about "the user".
- Do not define it by its opposite, and do not name an opposite.
- When the reading is a plain fact about the persona's life, such as where it is from or how it lives, state the fact and stop, however short that leaves the sentence: the length asked for above gives way to this. Do not dress the fact up as behavior, and do not add details that the reading does not give.
- Keep to the reading you were given. Do not widen it to other meanings of the label.
- US spelling.

Respond with one JSON object and nothing else:
{"results": [{"id": <int>, "gloss": "<one sentence>"}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable | First draft | |
| 2 | Fable | The opening rule now asks for "This means" followed at once by a verb in the -ing form, with three openings shown.  New rule: no subject, no "you", "your", "I", "my", "they" or "the persona"; "one's" for a possessive.  Length loosened from "18 to 32 words" to "about 20 to 30 words" | Roger, 2026-09-29: the gloss is a first draft, and length need not match the corpus, "but we could at least get them into 'This means' format, so they're less confusing to rewrite".  Draft 1 gave "This means you argue ..." for 73 of 74 words and "This means I ..." for one.  The corpus form has no subject: 592 of the 659 descriptions open "This means" and an -ing verb, 112 use "one's" and 7 use "you".  The three openings shown name no label |
| 3 | Fable | The rule for a plain fact gained "however short that leaves the sentence: the length asked for above gives way to this" and "do not add details that the reading does not give" | Two rules pulled against each other: about 20 to 30 words, and state the fact and stop.  Sonnet 5.5 kept the length and padded 8 of 13 memberships, as in "with Copenhagen and the Danish way of life as one's home ground".  Roger, 2026-09-30: "The fact wins" |
