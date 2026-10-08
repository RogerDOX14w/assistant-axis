# Step 1: the sense call

| | |
|---|---|
| **Status** | Draft 8: draft 7's clause reworded so that it promotes less.  Draft 6 ran in the full validation run of 2026-09-30; draft 7 was tried on 2026-10-01 and withdrawn.  Draft 6 was Roger's edits of 2026-09-29 plus one clause of mine, run on 99 words, batched and one word per call; see [sense_call_probe.md](../sense_call_probe.md). |
| **What the model is shown** | The label, and nothing else. |
| **What it returns** | The first thought; what the first thought is said of; the readings of the instruction, ranked, each marked primary or secondary; whether any reading is usable. |
| **What it is tuned on** | The 50 words Roger marked in [random_traits_for_marks.md](../random_traits_for_marks.md), and 49 others: words for things, plain traits, the six September rejects, figurative words, corpus labels.  Results so far: [sense_call_probe.md](../sense_call_probe.md). |
| **Model** | Haiku 5.5 from 2026-10-08 (no temperature: it refuses one; Haiku 4.5 at temperature 0 before), three independent readings per word by default (`--readings`; the verdict vote of M3 decision 17); Sonnet 5.5 for a word chosen for a second opinion.  One item per call.  The prompt is sent cached on Haiku 5.5 (about 810 tokens, over its 512-token minimum; from 2026-10-08). |

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
- readings: the ways a reader could take "You are <label>." as saying something about the persona, the most likely first, at most four. Rank them by how likely a reader is to take the instruction that way, not by how common the meaning is in general. Include readings about the body, about a passing condition or situation, about standing, and about where someone comes from or what group they belong to, as well as readings about character. A word ordinarily said of what people do or make, such as their talk, writing, teaching, work or manner, may also have a reading about the person who talks, writes, teaches, works or acts that way; include it, and rank it as a reader would, primary only when most readers would take the instruction so. Give each in a few plain words. Mark it "primary" if it is one of the one or two readings most readers would arrive at, and "secondary" if it is less likely. If the instruction has no reading about the persona, give an empty list.
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
| 7 | Fable | Added: a word ordinarily said of what people do or make (their talk, writing, teaching, work or manner) has a reading about the person who does it that way; include it and rank it as a reader would, which is often first | educational and historical, both corpus labels, got only secondary readings about the person in the full validation run of 2026-09-30, so no reading reached the checks and both were turned away.  Roger, 2026-10-01: see whether the filter can pass them.  Whether such a reading is established, and whether it is a trait, stay with the later calls |
| 8 | Fable | The clause now says the word "may also have" such a reading, ranked "primary only when most readers would take the instruction so"; "which is often first" is gone | Draft 7 on the 99 test words promoted readings that should have stayed secondary: one-time ("you do something only once"), organic ("you grow naturally"), chemical ("you work with chemicals") and threadbare all went on as traits or roles, and 84 of 99 outcomes agreed with the expected ones against 92 for draft 6.  It also did what it was for: educational and historical, and grubby, twisted and incestuous, came out as expected ([r6_split_test_words](../../../data/candidates/filter/r6_split_test_words/)) |

Tested and kept as Roger wrote it: the removal of "That is a normal answer."  It made no difference to
which words are turned away.
