# The LLM-entropy generator's back-translation call (family c of workstream 6)

| | |
|---|---|
| **Status** | Draft 1 (2026-10-17, Opus), pinned as version 1.  Not yet run: `llm_entropy_generator.py backtranslate` on the pilot's (c) answers (task 5) is its first use. |
| **What the model is shown** | This text as the system turn, and one user turn per (c) answer: the language's English name and the answer's items in order, each with its label, gloss and antonym in the language. |
| **What it returns** | `items`, one per item given and in the same order: `index`, `romanization`, `label` (the shortest English form, at most four words), `gloss` ("This means ..."), `antonym` (or null) and `listicle`. |
| **What it is tuned on** | Not tuned.  Roger's gloss-fidelity read (30 items per family and model arm, `gloss_check.md`) checks it. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); no temperature.  About 1,170 characters, with the user turn's 15-20 items after it. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written.  A changed text needs a new pin (`rubric_pins.py bump llm_entropy_backtranslate --why '...'`).

**What it is for.**  The registry's surface is always English (a label with no Latin letters normalises to an
empty stem), so each (c) item needs an English label of at most four words (Roger, 2026-10-13: "Multi-word is
acceptable: 1-4 words is the guideline"), an English gloss for M1's `gloss_hint`, and a flag on the well-known
"untranslatables" that name a thing, a feeling or an atmosphere rather than a disposition (the listicle cliches).
The original label, its romanisation and the language stay in the generator's table and in the candidate's
`source_ref`, never in the surface.  The code is
[calls.py](../../../assistant_axis/gapgen/generators/llm_entropy/calls.py) and
[parse.py](../../../assistant_axis/gapgen/generators/llm_entropy/parse.py).

**Choices in the text, and why.**  The text is the plan's, with "cosy" spelt "cozy" (US English).  No reason field:
the call translates; its one decision per item, `listicle`, is a flag reported in the table and never a gate.
Items are matched back by `index`, and a reply that drops items is counted (`parse_backtranslation`).

**Word hygiene.**  The one example label, `reads the room`, and the longer phrase it is contrasted with are not
corpus stems, queue labels or validation-file words.  The language's English name in the user turn is data, not an
example; three of the ten names (German, Japanese, Russian) are also corpus membership traits, recorded in the
prompt test as such, and so is `single` ("a single English word").  "the original label" became "the label as
written" (`original` is on the lists).

## The prompt

````text
You are given the items of a list of character traits written in one language, each with a label, a gloss and an antonym in that language. For each item give the shortest English form of the label, at most four words, lower case, one name with no commas: a single English word where one carries the same meaning, otherwise the shortest phrase that does ("reads the room" is a fine label; "a person who is good at reading social situations" is not). Translate the gloss into one English sentence of at most 25 words starting "This means", and the antonym into the same form (or null). Flag an item as a cliché ("listicle": true) when the word is a well-known untranslatable that names a thing, a feeling or an atmosphere rather than a disposition a person enacts (for example a word for a cozy atmosphere, or for pleasure at another's misfortune), and give the romanisation of the label as written. Keep the items in order and keep their count. Respond with a JSON object only, no other text:
{"items": [{"index": <1-based>, "romanization": "<...>", "label": "<english, 1-4 words>", "gloss": "This means ...", "antonym": "<english or null>", "listicle": <true|false>}, ...]}
````

## Rendered sample

A user turn as `prompts.render_backtranslate` builds it (the items are illustrative, not a recorded answer):

````text
Language: German.
Items:
1. label: "pfennigfuchserisch"; gloss: "Das bedeutet, bei jeder Kleinigkeit um den letzten Cent zu feilschen und Ausgaben bis ins Lächerliche zu prüfen."; antonym: "großzügig bis zur Verschwendung"
2. label: "geldscheu"; gloss: "Das bedeutet, Geldfragen zu meiden, Rechnungen liegen zu lassen und sich bei jedem Gespräch über Geld unwohl zu fühlen."; antonym: null
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, the plan's text with "cosy" spelt "cozy" and "the original label" as "the label as written" | coding plan § "Rendered prompts", the back-translation call |
