# The paraphrase synonym call (the matcher's sanity set)

| | |
|---|---|
| **Status** | Draft 1 (2026-10-13), pinned as version 1: the text of "Rendered prompt: the paraphrase synonym call" in [coding_plan_13_generator_testing.md](../coding_plan_13_generator_testing.md), unchanged. |
| **What the model is shown** | One item per call: the user turn is `Definition: ` and one corpus trait's recorded paraphrase from the M2 calibration ([paraphrases.json](../../../data/candidates/calibration/paraphrases.json), "This means ..."), never the trait's name.  A re-ask adds one line naming the word the label must not be (below). |
| **What it returns** | A reason, then `label` (one or two words) and `gloss` (a fresh "This means ..." definition of 12 to 16 words). |
| **What it is tuned on** | Not tuned.  Its answers are read by the recovery harness, not by a person: the set's report says how many of the 80 hidden traits the harness finds again. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); no temperature (it refuses one).  The prompt is 788 characters, about 200 tokens, under Haiku 5.5's 512-token caching minimum, so the cache marker it is sent with has no effect. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin
(`rubric_pins.py bump paraphrase_synonym`).

**What it is for.**  Workstream 13 checks the recovery harness's matcher before trusting its recall figures
([coding_plan_13_generator_testing.md](../coding_plan_13_generator_testing.md) § 1 and task 7).  The harness
matches a candidate to a hidden corpus trait by its label first, with no model call, so a candidate that carries
the trait's own name never exercises the overlap call at all.  This call makes candidates that name 80 corpus
traits in other words: 40 traits that hide alone and one pole of each of 40 recorded pairs.  Each answer becomes a
row of a scratch registry (never the real one), the 80 traits are hidden, and the harness runs on those rows.  A
trait it does not find again is a matcher bug to file, not a finding about generators.  For a pair pole the
expectation is also that the hidden partner is read `opposite`.  The code is
[paraphrase_set.py](../../../assistant_axis/gapgen/testing/paraphrase_set.py); the command is
`generator_dashboard.py paraphrase-set build | run | report`.

**Why it asks for a new definition as well as a label.**  The harness's overlap call compares a candidate's gloss
with the hidden trait's description.  Reusing the paraphrase as the gloss would test only whether two near-copies
of one text are read as the same concept; the "reuse none of the content words" rule makes the gloss a second,
independent wording of the concept.

**The re-ask.**  When the label comes back as the hidden trait's own stem or one of its former stems (compared with
the separators taken out, as the harness compares labels), the item is asked once more with one line appended to
the user turn: `The label must not be the word "<the trait's label, as prompts show it>" or a spelling of it.`
The re-ask's answer is kept and counted.  The system turn is the same in both.

**Word hygiene.**  The prompt has no example words, so nothing in it can be a corpus label, a queue entry or a
validation word.  An example added later must pass `prompt_hygiene.prompt_words` against the corpus, the queue and
the validation file.

## The prompt

````text
You are helping test a search tool over a corpus of personality traits.  You will be given one short
definition of a trait in the corpus's style ("This means ...").  The trait's own name is withheld.  Do two
things.  (1) Give the one- or two-word label a careful lexicographer would put on this trait: US English,
lower case, an adjective or a short adjectival phrase, at most two words, no hyphenated inventions.  (2) Write
a fresh definition of the same trait, 12 to 16 words, in the same "This means ..." form, in your own words:
reuse none of the content words of the definition you were given (function words are fine).  Reason first,
then answer.  Respond with a JSON object only, no other text:
{"reasoning": "<one or two sentences>", "label": "<label>", "gloss": "This means ..."}
````

## Rendered sample

A call is the block above as the system turn, byte for byte (its line breaks included, as the plan rendered it),
and one user turn built by `paraphrase_set.render_user`.  Rendered from the real set (`build_set` with its
defaults: 40 singles and 40 pair poles, seed 0), 2026-10-13.

**A single**, item `s01`: [aristocratic](../../../data/traits/instructions/aristocratic.json), which hides alone.

````text
Definition: This means holding that descent and family name ought to settle who governs and receives respect, and that established houses merit their standing by birthright.
````

**The same item re-asked**, as it would be if its first answer had been the trait's own name:

````text
Definition: This means holding that descent and family name ought to settle who governs and receives respect, and that established houses merit their standing by birthright.
The label must not be the word "aristocratic" or a spelling of it.
````

**A pair pole**, item `p01`: [anecdotal](../../../data/traits/instructions/anecdotal.json), whose partner
[data-driven](../../../data/traits/instructions/data_driven.json) hides with it.  The expectation is that the
candidate recovers anecdotal and that the overlap call reads data-driven `opposite` against it.

````text
Definition: This means making claims based on isolated cases: a relative's experience, something that happened locally, a striking story, one memorable instance mattering more than any broad pattern.
````

Read for fit.  The prompt says "one short definition"; each user turn carries exactly one, in the corpus's "This
means" form, and nothing else: no label, no region, no partner.  The answer format's three keys come in the order
the prompt asks for them (reasoning, label, gloss), and the gloss is checked only for its opening "This means";
its length and its word reuse are not enforced by the parser (the harness reads whatever comes back).

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft in this file: the plan's rendered `[system]` text, unchanged | Plan 13 task 7 (2026-10-13): the paraphrase sanity set needs one pinned prompt |
