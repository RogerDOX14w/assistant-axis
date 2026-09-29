# Step 1: the sense call

| | |
|---|---|
| **Status** | Draft 6.  Roger's edits of 2026-09-29 plus one clause of mine.  Run on 99 words, batched and one word per call; see [sense_call_probe.md](../sense_call_probe.md). |
| **What the model is shown** | The label, and nothing else. |
| **What it returns** | The first thought; what the first thought is said of; the readings of the instruction, ranked, each marked primary or secondary; whether any reading is usable. |
| **What it is tuned on** | The 50 words Roger marked in [random_traits_for_marks.md](../random_traits_for_marks.md), and 49 others: words for things, plain traits, the six September rejects, figurative words, corpus labels.  Results so far: [sense_call_probe.md](../sense_call_probe.md). |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it must not do:** say what kind of thing a reading is, or whether it is a trait.  That is step 2.

## The prompt

````text
A persona is given a one-line instruction prompt, "You are <label>.", and nothing else. For each label below, say how a reader would take that instruction.

Some labels give the instruction no meaning that a reader could sensibly use. "You are octagonal." and "You are alkaline." are like that: the words are about shapes and substances, not people.

For each label:
- note: one short sentence on what the word ordinarily means and what it is ordinarily said of. Write this first.
- first_thought: what comes to mind first on meeting the bare word, in a few plain words, whatever the word is said of.
- first_thought_said_of: what the word, in that first thought, is said of. One of: people; things (including objects, substances, places, animals, plants); actions (including deeds, events, processes); abstractions (including ideas, texts, plans, situations, amounts).
- readings: the ways a reader could take "You are <label>." as saying something about the persona, the most likely first, at most four. Rank them by how likely a reader is to take the instruction that way, not by how common the meaning is in general. Include readings about the body, about a passing condition or situation, about standing, and about where someone comes from or what group they belong to, as well as readings about character. Give each in a few plain words. Mark it "primary" if it is one of the one or two readings most readers would arrive at, and "secondary" if it is less likely. If the instruction has no reading about the persona, give an empty list.
- usable: true when at least one reading is clear enough that a persona given only this instruction would know what is being asked of it. False when none is, or when a reader would have to invent one.

List readings the word already has, or that follow plainly from its parts. Do not extend the word to a new use.

Respond with one JSON object and nothing else, note first:
{"results": [{"id": <int>, "label": "<the label exactly as given>", "note": "<one short sentence>", "first_thought": "<a few words>", "first_thought_said_of": "people"|"things"|"actions"|"abstractions", "readings": [{"reading": "<a few words>", "rank": "primary"|"secondary"}, ...], "usable": true|false}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 4 | Fable | The two yes or no flags taken out; `first_thought_said_of` added | The flags were unreliable when asked in the same call as the lists |
| 5 | Roger | "instruction prompt"; "no meaning that a reader could sensibly use"; "not people" added; "That is a normal answer." removed; "including" added to the four said-of lists; the sentence that named personality traits removed | His edits.  The last keeps the call from learning what the answers are for |
| 6 | Fable | Added "and about where someone comes from or what group they belong to" to the kinds of reading to include | Tuscan and southeastern were getting no reading at all, where Danish got one.  With this clause and one word per call, all 28 of Roger's plain traits get a primary reading |

Tested and kept as Roger wrote it: the removal of "That is a normal answer."  It made no difference to
which words are turned away.
