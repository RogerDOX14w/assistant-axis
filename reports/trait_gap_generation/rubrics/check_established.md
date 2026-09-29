# Check: how established a reading is

| | |
|---|---|
| **Status** | Draft 4.  One sentence added to draft 3.  Run one item per call.  Tuning stops here (Roger, 2026-09-29: "don't overdo it"). |
| **What the model is shown** | A label, its first thought, and one reading, all from step 1. |
| **What it returns** | Whether the reading is well known, known, plain from the word's parts, or stretched; and whether the first thought gets in the way. |
| **What it is tuned on** | Not yet tuned. |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  Roger, 2026-09-29: a first thought about something other than a person is "a concern, not a hard reject reason", to be weighed when judging a word, or when choosing between near-duplicates.  So this check only writes notes.  It separates a word such as cold, whose use for people is well known, from one such as leavened, whose reading has to be worked out.

## The prompt

````text
Each item gives a label, the first thing the bare word brings to mind, and one reading of the instruction "You are <label>." as said of a persona. Say how well established that reading is, and whether the first thought gets in its way.

For each item:
- reason: one short sentence. Write this first.
- established: how the word comes to have this reading when it is said of a person. The test is ordinary speech: would people say "she is <label>" and mean this? One of:
  - "well_known": the word is commonly used of people in this sense, and most readers have met it so. This includes a sense that began as a figure of speech and is now ordinary.
  - "known": the word is used of people in this sense, but not often.
  - "from_parts": readers would seldom have met the word used of people, but the reading follows plainly from the word's parts: a word built with un-, non- or the like on a word that is used of people, or a plain compound of such words.
  - "stretched": the word is not used of people in this sense. To reach the reading, a reader has to make a figure of speech of their own, carrying the word over from the things it is ordinarily said of.
- first_thought_in_the_way: true when a reader would think of the first thought before the reading, whether the first thought is about a person or about something else. False when the first thought and the reading are the same.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "established": "well_known"|"known"|"from_parts"|"stretched", "first_thought_in_the_way": true|false}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 2 | Roger | The sentence that named personality traits removed.  `first_thought_in_the_way` widened: it is now true whenever a reader would think of the first thought before the reading, whatever the first thought is about | His edits |
| 2 | Fable | That line repaired.  It read: "true when a reader would think of it before the reading, evn if the first thought is about something other than a person and a reader would think of it before the reading."  A typo, a clause repeated, and "it" with nothing clear to refer to.  The case for false, which the edit had dropped, is restored as "False when the first thought and the reading are the same." | To say what I take Roger to have meant, in one pass |
| 3 | Fable | "worked_out" split into "from_parts" and "stretched" | Roger, 2026-09-29: "Do portable and linear even have persona senses? (If not, we can reject them at this step.) If we can drop them, but keep warm, cold, etc, that would be ideal."  One value could not do that, since he had marked nonturbulent and ungrammatical as traits, and their readings are also worked out.  Those follow from the word's parts; portable's has to be made up by the reader |
| 4 | Fable | Added the test of ordinary speech: would people say "she is <label>" and mean this? | illegal, read as "you do things against the law", had been called well known, and watertight, read as "your reasoning cannot be challenged", known.  Nobody says of a person that she is illegal or watertight in those senses |

**The rule this check feeds**, which is code and not prompt: a word is turned away when every one of
its primary readings is "stretched".  Every other answer is a note.
