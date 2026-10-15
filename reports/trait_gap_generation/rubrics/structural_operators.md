# The structural operators call (generator B of workstream 9)

| | |
|---|---|
| **Status** | Draft 2 (2026-10-15, Opus), pinned as version 2 (the naming rule; version 1, the pilot's text, is kept below).  Draft 1 (2026-10-13, Opus), pinned as version 1.  Not yet run: the null-rate pilot (20 traits, coding plan § 10) is its first test, and a pilot outside the 5-40% band for `retarget` and `remode` makes one bounded revision of this text (a new pin). |
| **What the model is shown** | One corpus trait per call, as one JSON object: its label in the judge display form (`"trait"`), its `description`, the *kind* of its recorded arrangement (`"arrangement"`: `pair`, `triangle`, `sequence`, `singleton`, `unclassified`, ...) and the targets to consider (`"retarget_toward"`: the six ordinary targets, plus `the_user`, `the_operator` and `the_developer` for a principal-target trait).  **Never** its `negative_label` and never the other members of its arrangement: the opposite runs blind. |
| **What it returns** | `reasoning` first, then `position`, `opposite`, `excess`, `deficiency`, `retarget` (one entry per listed target) and `remode` (`attitude`, `habit`, `speech`); each answer an item `{label, gloss, has_common_word, polysemy}` or `null`.  With `"answer_only": "retarget"` in the user turn (a later principal-target stage), only `reasoning` and `retarget`. |
| **What it is tuned on** | Not tuned.  The null-rate pilot reads the non-null share of every operator, target and mode; the stability run reads the label-set Jaccard of 30 traits answered twice. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); no temperature (it refuses one); 6,625 characters, about 1,650 tokens, above Haiku 5.5's 512-token cache minimum: sent with the system block cached (the estimate assumes no cache hit, so about 1,740 input tokens a call with the user turn). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written.  Leave the fence lines themselves alone.  Notes for Roger go under "Your notes", outside the
block.  A changed text needs a new pin (`rubric_pins.py bump structural_operators --why '...'`), and the
operators command refuses a text that is not its latest pin.

**What it is for.**  Workstream 9's generator B applies five structural moves to each of the corpus's trait files
([coding_plan_09_structural_generators.md](../coding_plan_09_structural_generators.md)): the opposite, the vice of
too much and the vice of too little (the *degree fillers*), the same disposition aimed at another target, and the
same disposition in another mode.  `position` (where the trait sits: `deficiency`, `mean`, `excess` or
`not_scalar`) goes to a side table for the pairing review, never into a trait file.  The code is
[operators.py](../../../assistant_axis/gapgen/generators/structural/operators.py) and
[prompts.py](../../../assistant_axis/gapgen/generators/structural/prompts.py); the command is
`structural_generator.py operators`.

**Choices in the text, and why.**

- **`excess` and `deficiency` are the two ends of the trait's own scale.**  The workstream plan asks for "the vice
  this becomes with too much / too little"; the text makes that concrete as the vice at the too-much end and the
  vice at the too-little end, and says either is `null` when the trait *is* that vice.  So a `mean` trait gives
  both vices, an `excess`-position trait gives `excess: null` and its opposite vice under `deficiency`, and a
  `deficiency`-position trait the reverse (the coding plan § 6: "for a deficiency-position trait the model may
  return null for deficiency, which is the expected answer").  The coding plan's illustrative reply (a made-up
  tightfisted trait) first had the two the other way round (`excess: null`, `deficiency: wasteful`); the rule
  in its parenthesis is what this text follows, and the illustration was corrected to it on 2026-10-13
  (QUESTIONS 119).
- **Null is said to be the expected answer** for `retarget` and `remode` (twice), as plan 09 § 3.4 asks; the
  null-rate pilot's band (5-40% non-null) is what tests whether that is said strongly enough or too strongly.
- **No over-/under-/too-/non-/not- names.**  Said in the prompt and enforced by the parser
  (`operators.validate_item`), which drops such an item and counts it.
- **The glosses go straight to the behaviour**, without the label (the description-wording rule, Roger
  2026-09-27; QUESTIONS 41 settled it for Roget's glosses).
- **The AI-assistant targets are named only when listed**; the parser drops a principal-target answer for a trait
  the user turn did not list them for (the guard, both ways).

**Word hygiene.**  The examples are traits outside the corpus, the seed queue and the validation files
(`provident`, `censorious`, `monarchist`) and their answers too (`improvident`, `miserly`, `spendthrift`, `lax`,
`self-scolding`, `carping`, `republican`, and the label-form examples `penny-pinching`, `slow to forgive`,
`over-punctual`, `too punctual`): plan 09's own illustrations ([cautious](../../../data/traits/instructions/cautious.json), [honest](../../../data/traits/instructions/honest.json), [harsh](../../../data/traits/instructions/harsh.json), [arrogant](../../../data/traits/instructions/arrogant.json), [reckless](../../../data/traits/instructions/reckless.json),
[self-critical](../../../data/traits/instructions/self_critical.json)) are corpus traits and would have seeded the pair-recovery test with its own answers.
[test_gapgen_structural_prompts.py](../../../assistant_axis/tests/test_gapgen_structural_prompts.py) fails if an
example word becomes a corpus stem, a queue label or a validation word, and records the two prose words of the
text that are on those lists anyway (`mean`, a value of `position`, and `operator`, inside `the_operator`; a new one
fails).

## The prompt

````text
You are given one trait from a list of persona traits, as a JSON object: its label ("trait"), a description of what having it means ("description"), how the list records it among other traits ("arrangement"), and the targets to consider for it ("retarget_toward"). Say where the trait sits on its own scale, and name the traits that five structural moves lead to from it.

A trait here is a lasting disposition: a way of feeling, thinking, speaking, acting or relating to others that a person can have for years and that shows in how they talk. Name each trait as one person would describe another, in words a well-read adult knows. A name is a single word whose most common sense, said of a person, is the trait your gloss describes (for example "penny-pinching"); only when English has no such word, a short phrase of two to four words that says the gloss plainly (for example "slow to forgive"). Never use a word whose usual sense, said of a person, is something else, even when a dictionary lists the sense you mean among its rarer ones: a reader meets the name without the gloss and takes it in its usual sense. Never make a name by putting "over", "under", "too", "non" or "not" in front of a word ("over-punctual", "too punctual"): if English has no name for it, give a plain phrase of your own, or null. Name a vice as a vice, plainly; do not soften it. Never give the trait's own label as an answer.

Think first, in "reasoning": what the trait is and what drives it, whether it is more or less of some quality, what lies on either side of it, and which other targets and modes would give a disposition people recognize. Then answer:
- "position": where the trait as described sits on its own scale: "deficiency" (too little of a quality a person needs), "mean" (the sound amount of a quality, with a vice of too much on one side and a vice of too little on the other), "excess" (too much of a quality), or "not_scalar" (not more or less of anything: a creed, a stance, a membership or a style).
- "opposite": the contrary trait of the same scope, as a reader of the description would name it.
- "excess": the vice at the too-much end of the trait's scale, what its quality becomes when a person has far too much of it. null when the trait is itself that vice, or the scale has no such end.
- "deficiency": the vice at the too-little end of the scale, what a person is when its quality is badly lacking. null when the trait is itself that vice, or the scale has no such end.
- "retarget": the same disposition aimed at another target, one entry for each target in "retarget_toward" and no other: "self" (oneself), "intimates" (family, partner, close friends), "strangers" (people one does not know), "authority" (bosses, officials, rules, institutions), "animals", "ideas" (beliefs, theories, arguments), and, listed for some traits only, three targets for an AI assistant: "the_user" (the person it is talking with and working for), "the_operator" (the business that deployed it and set its instructions) and "the_developer" (the company that built and trained it). Give an item only when the redirected disposition is a trait in its own right that people would recognize and name; null for the target the trait already has. Most targets give null for most traits: null is the expected answer.
- "remode": the same disposition in another mode: "attitude" (how the person regards things inwardly), "habit" (what they routinely do), "speech" (how they talk). Give an item only for a mode the trait is not already in, and only when the result is a trait in its own right; otherwise null, the expected answer for most modes.

Every answer that is not null is an object: "label" (the name, as above); "gloss" (one sentence of at most 25 words that starts "This means" and goes straight to the behavior, without repeating the label); "has_common_word" (true when one common English word names it, false when only a phrase does); "polysemy" (true when the label has another common meaning a reader might take instead).

"arrangement" is context only: "pair" means the list records one opposite for the trait, "triangle" three mutually opposed traits, "sequence" a graded series, "singleton" no recorded opposite, "unclassified" nothing recorded yet, and other words other shapes. You are not told the other members; answer from the description.

An example, for a trait outside the list. The user turn
{"trait": "provident", "description": "This means putting money and supplies by for later, planning for lean times and spending with tomorrow in mind.", "arrangement": "unclassified", "retarget_toward": ["self", "intimates", "strangers", "authority", "animals", "ideas"]}
is answered
{"reasoning": "Provident is the sound amount of care for the future. With far too much of it, saving becomes an end in itself and nothing is spent; with too little, money goes as fast as it comes. It is already a habit, and aimed at other targets or voiced as speech it is no recognizable trait.", "position": "mean", "opposite": {"label": "improvident", "gloss": "This means spending whatever comes in at once and making no plans for lean times or emergencies.", "has_common_word": true, "polysemy": false}, "excess": {"label": "miserly", "gloss": "This means hoarding money for its own sake and refusing to spend it even on real needs.", "has_common_word": true, "polysemy": false}, "deficiency": {"label": "spendthrift", "gloss": "This means running through money on whatever catches the eye and borrowing once it is gone.", "has_common_word": true, "polysemy": false}, "retarget": {"self": null, "intimates": null, "strangers": null, "authority": null, "animals": null, "ideas": null}, "remode": {"attitude": null, "habit": null, "speech": null}}

Two shorter cases. A trait at one end of its scale, "censorious" (judging other people's conduct severely and expecting the worst of them): "position" "excess"; "excess" null, since it is already the vice of too much; "deficiency" a name for too little judgment of conduct, such as "lax"; "retarget" "self" "self-scolding", the same severity turned on one's own conduct; "remode" "speech" "carping"; every other target and mode null. A trait that is not more or less of anything, "monarchist": "position" "not_scalar"; "opposite" "republican"; "excess" and "deficiency" null, and every target and mode null.

Respond with one JSON object and nothing else, reasoning first:
{"reasoning": "...", "position": "deficiency" | "mean" | "excess" | "not_scalar", "opposite": ITEM or null, "excess": ITEM or null, "deficiency": ITEM or null, "retarget": {"<each target in retarget_toward>": ITEM or null}, "remode": {"attitude": ITEM or null, "habit": ITEM or null, "speech": ITEM or null}}
where ITEM is {"label": "...", "gloss": "This means ...", "has_common_word": true | false, "polysemy": true | false}.
When the user turn has "answer_only": "retarget", give only "reasoning" and "retarget".
````

## Rendered sample

A call is the block above as the system turn, byte for byte, and one JSON object as the user turn
(`operators.render_operator_user`).  The four variants of coding plan § 7, as
`structural_generator.py operators --traits STEM ... --dry-run` prints them (labels in the judge display form):
see [acceptance_09_structural_generators.md](../acceptance_09_structural_generators.md) § "Rendered prompts",
which pastes the dry run's output verbatim.

## Version 1 (superseded 2026-10-15)

The text pinned as version 1, kept here so that it can be read and restored (`rubric_pins.py bump NAME --revert-to 1`); it is not sent.

```text
You are given one trait from a list of persona traits, as a JSON object: its label ("trait"), a description of what having it means ("description"), how the list records it among other traits ("arrangement"), and the targets to consider for it ("retarget_toward"). Say where the trait sits on its own scale, and name the traits that five structural moves lead to from it.

A trait here is a lasting disposition: a way of feeling, thinking, speaking, acting or relating to others that a person can have for years and that shows in how they talk. Name each trait as one person would describe another, in words a well-read adult knows: an adjective or short adjective phrase where English has one (for example "penny-pinching" or "slow to forgive"), otherwise a short phrase that describes it. Use one to four words. Never make a name by putting "over", "under", "too", "non" or "not" in front of a word ("over-punctual", "too punctual"): if English has no name for it, give a plain phrase of your own, or null. Name a vice as a vice, plainly; do not soften it. Never give the trait's own label as an answer.

Think first, in "reasoning": what the trait is and what drives it, whether it is more or less of some quality, what lies on either side of it, and which other targets and modes would give a disposition people recognize. Then answer:
- "position": where the trait as described sits on its own scale: "deficiency" (too little of a quality a person needs), "mean" (the sound amount of a quality, with a vice of too much on one side and a vice of too little on the other), "excess" (too much of a quality), or "not_scalar" (not more or less of anything: a creed, a stance, a membership or a style).
- "opposite": the contrary trait of the same scope, as a reader of the description would name it.
- "excess": the vice at the too-much end of the trait's scale, what its quality becomes when a person has far too much of it. null when the trait is itself that vice, or the scale has no such end.
- "deficiency": the vice at the too-little end of the scale, what a person is when its quality is badly lacking. null when the trait is itself that vice, or the scale has no such end.
- "retarget": the same disposition aimed at another target, one entry for each target in "retarget_toward" and no other: "self" (oneself), "intimates" (family, partner, close friends), "strangers" (people one does not know), "authority" (bosses, officials, rules, institutions), "animals", "ideas" (beliefs, theories, arguments), and, listed for some traits only, three targets for an AI assistant: "the_user" (the person it is talking with and working for), "the_operator" (the business that deployed it and set its instructions) and "the_developer" (the company that built and trained it). Give an item only when the redirected disposition is a trait in its own right that people would recognize and name; null for the target the trait already has. Most targets give null for most traits: null is the expected answer.
- "remode": the same disposition in another mode: "attitude" (how the person regards things inwardly), "habit" (what they routinely do), "speech" (how they talk). Give an item only for a mode the trait is not already in, and only when the result is a trait in its own right; otherwise null, the expected answer for most modes.

Every answer that is not null is an object: "label" (the name, as above); "gloss" (one sentence of at most 25 words that starts "This means" and goes straight to the behavior, without repeating the label); "has_common_word" (true when one common English word names it, false when only a phrase does); "polysemy" (true when the label has another common meaning a reader might take instead).

"arrangement" is context only: "pair" means the list records one opposite for the trait, "triangle" three mutually opposed traits, "sequence" a graded series, "singleton" no recorded opposite, "unclassified" nothing recorded yet, and other words other shapes. You are not told the other members; answer from the description.

An example, for a trait outside the list. The user turn
{"trait": "provident", "description": "This means putting money and supplies by for later, planning for lean times and spending with tomorrow in mind.", "arrangement": "unclassified", "retarget_toward": ["self", "intimates", "strangers", "authority", "animals", "ideas"]}
is answered
{"reasoning": "Provident is the sound amount of care for the future. With far too much of it, saving becomes an end in itself and nothing is spent; with too little, money goes as fast as it comes. It is already a habit, and aimed at other targets or voiced as speech it is no recognizable trait.", "position": "mean", "opposite": {"label": "improvident", "gloss": "This means spending whatever comes in at once and making no plans for lean times or emergencies.", "has_common_word": true, "polysemy": false}, "excess": {"label": "miserly", "gloss": "This means hoarding money for its own sake and refusing to spend it even on real needs.", "has_common_word": true, "polysemy": false}, "deficiency": {"label": "spendthrift", "gloss": "This means running through money on whatever catches the eye and borrowing once it is gone.", "has_common_word": true, "polysemy": false}, "retarget": {"self": null, "intimates": null, "strangers": null, "authority": null, "animals": null, "ideas": null}, "remode": {"attitude": null, "habit": null, "speech": null}}

Two shorter cases. A trait at one end of its scale, "censorious" (judging other people's conduct severely and expecting the worst of them): "position" "excess"; "excess" null, since it is already the vice of too much; "deficiency" a name for too little judgment of conduct, such as "lax"; "retarget" "self" "self-scolding", the same severity turned on one's own conduct; "remode" "speech" "carping"; every other target and mode null. A trait that is not more or less of anything, "monarchist": "position" "not_scalar"; "opposite" "republican"; "excess" and "deficiency" null, and every target and mode null.

Respond with one JSON object and nothing else, reasoning first:
{"reasoning": "...", "position": "deficiency" | "mean" | "excess" | "not_scalar", "opposite": ITEM or null, "excess": ITEM or null, "deficiency": ITEM or null, "retarget": {"<each target in retarget_toward>": ITEM or null}, "remode": {"attitude": ITEM or null, "habit": ITEM or null, "speech": ITEM or null}}
where ITEM is {"label": "...", "gloss": "This means ...", "has_common_word": true | false, "polysemy": true | false}.
When the user turn has "answer_only": "retarget", give only "reasoning" and "retarget".
```

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from plan 09 § 3.4-3.5 and the coding plan's decisions: per-trait call, reasoning first, the opposite blind, excess and deficiency as the two ends of the trait's scale, principal targets only when listed, hygiene-checked examples | coding plan 09 task 3 |
| 2 | Opus | The naming rule: a single word whose most common sense, said of a person, is the gloss; only when English has none, a plain phrase of two to four words; never a word whose usual sense is something else.  Version 1's text is kept under "Version 1 (superseded 2026-10-15)" | Roger, 2026-10-14/15: the pilot's labels in odd senses (grasping for craving honor; 9 of 50 marked `?` in [roger_sample.md](../../../data/candidates/runs/structural/2026-10-14-pilot/roger_sample.md)) |
