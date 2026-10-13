# The classical modernise call (generator A of workstream 9)

| | |
|---|---|
| **Status** | Draft 1 (2026-10-13, Opus), pinned as version 1.  Not yet run: the A run (coding plan task 9) is its first use, about 11 calls. |
| **What the model is shown** | Twenty rows of the hand-typed classical tables per call ([data/candidates/structural/classical/](../../../data/candidates/structural/classical/)), as one JSON object `{"rows": [...]}`: each row's `id`, its scheme's name, the `item` as the scheme names it, its `role`, its hand-typed `gloss`, and the other items of its structure (`structure`, each with its role). |
| **What it returns** | `{"rows": [...]}`, one entry per row in the same order: `id`, `reasoning` first, then `labels` (1-3 modern names, best first), `gloss` ("This means ...", at most 25 words, without the label) and `polysemy`. |
| **What it is tuned on** | Not tuned.  Roger reads the classical candidates (about 30 minutes, coding plan § 10). |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); no temperature; 2,299 characters (about 575 tokens), just above Haiku 5.5's 512-token cache minimum, sent cached. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written.  Leave the fence lines themselves alone.  A changed text needs a new pin
(`rubric_pins.py bump structural_modernise --why '...'`).

**What it is for.**  Generator A turns the classical items into labels a 32B model knows (plan 09 § 3, step 2),
keeping each row's role in its structure, so that a triple's three rows are reviewed together and a pole's partner
rides the candidate's `partner_hint`.  The code is
[modernise.py](../../../assistant_axis/gapgen/generators/structural/modernise.py); the command is
`structural_generator.py modernise`.

**Choices in the text, and why.**  The role says *whose* trait to name (the person with the vice, the person given
to the sin, someone with a strong or a weak need), since a need's low pole and a strength's underuse are otherwise
easy to answer with the need or the strength itself.  Plan 09's two illustrations ("pusillanimous" becoming
[self-effacing](../../../data/traits/instructions/self_effacing.json), Theophrastus' "petty ambition" becoming [status-seeking](../../../data/traits/instructions/status_seeking.json)) are not used: both items are rows of the
tables, so they would hand the call its own answers, and both answers are corpus traits.  The one example is an
archaism outside every list (`pettifogging` to `nitpicking`).  The over-/under-/too-/non- rule is the operators
call's.

## The prompt

````text
You are given rows from five classical lists of human qualities, as a JSON object ("rows"): Aristotle's table of virtues as means between two vices, the vices of Theophrastus' Characters, the seven deadly sins and the virtues, the VIA character strengths with the names for their underuse and overuse, and Murray's list of psychological needs. Each row gives its "id", its "scheme", the "item" as the scheme names it, its "role" in the scheme, a short "gloss" of what the item meant there, and the other items of its structure ("structure", each with its role).

For each row, name the lasting trait a person has when the row describes them, in the English a well-read adult knows today. The role tells you who that person is: for a vice of excess or of deficiency, the person with that vice; for a mean, a strength or a virtue, the person who has it; for a sin, the person given to it; for one of Theophrastus' characters, the person he sketches; for a need's high pole, someone with a strong need, and for its low pole, someone with a weak one; for a strength's underuse or overuse, the person who uses it too little or too much. Old or translated terms get the name a speaker today would use for the same person (an archaic word such as "pettifogging" becomes "nitpicking"). Keep the row's meaning, including its moral weight: a vice is named as a vice, plainly, and is not softened.

Give per row:
- "id": the row's id, unchanged;
- "reasoning": one or two sentences on what the item meant and what a person who has it is like today;
- "labels": one to three names, best first, each an adjective or short adjective phrase of one to four words where English has one, otherwise a short phrase that describes it; never a name made by putting "over", "under", "too", "non" or "not" in front of a word;
- "gloss": one sentence of at most 25 words that starts "This means" and describes the first label's behavior directly, without repeating the label;
- "polysemy": true when the first label has another common meaning a reader might take instead.

Respond with one JSON object and nothing else, one entry per row of the user turn, in the same order, reasoning first in each:
{"rows": [{"id": "...", "reasoning": "...", "labels": ["...", "..."], "gloss": "This means ...", "polysemy": true | false}]}
````

## Rendered sample

A call is the block above as the system turn, byte for byte, and one JSON object as the user turn
(`modernise.render_modernise_user`, 20 rows).  One rendered call is pasted in
[acceptance_09_structural_generators.md](../acceptance_09_structural_generators.md) § "Rendered prompts", from
`structural_generator.py modernise --dry-run`.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from plan 09 § 3 step 2 (1-3 modern labels, a gloss of at most 25 words, a polysemy flag, reasoning first), with the role-to-person paragraph and a hygiene-checked example | coding plan 09 task 3 |
