# The LLM-entropy generator's multilingual master (family c of workstream 6)

| | |
|---|---|
| **Status** | Draft 1 (2026-10-17, Opus), pinned as version 1.  Not yet translated: `llm_entropy_generator.py translate-prompts` (task 3, about $0.5 live) makes the ten translations and their back-translations for Roger's read. |
| **What the model is shown** | **Not this text.**  This is the English master; each (c) call's system turn is its translation into the call's language, recorded with its sha256 in [multilingual_prompts.json](../../../data/candidates/llm_entropy/multilingual_prompts.json) (not there yet), and the user turn is the translated request with the domain filled in.  `{language}` is replaced by the language's English name before the text is translated. |
| **What it returns** | A short reason first (`approach`), then `items`: each `label` in the language, `romanization`, `english_hint` (always null), `gloss` and `antonym` in the language, `kind` (M1's vocabulary, kept in English), `ambiguity_flag`. |
| **What it is tuned on** | Not tuned.  Roger reads the ten back-translations before any (c) call is made (task 3). |
| **Model** | Sonnet 5.5 (`claude-sonnet-5-5`) for the pilot's (c) share and Haiku 5.5 (`claude-haiku-5-5`) beside it (the model test); the rest of (c) on whichever the § 10 rule favours.  No temperature. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is what is translated.
Leave the fence lines themselves alone.  A changed text needs a new pin (`rubric_pins.py bump llm_entropy_multilingual
--why '...'`) **and new translations** (`translate-prompts --force`): the translations record the master's sha256,
and `generate --family c` refuses translations made from another master.

**What it is for.**  Family (c) asks for traits as a native speaker of German, Japanese, Mandarin, Russian, Arabic,
Persian, Finnish, Korean, Hindi or Turkish would name them (Roger, 2026-10-13: high to fairly-high resource
languages), preferring concepts with no single English word.  The prompt is written in the language so that the
answer comes from the language's own vocabulary; the English form is chosen afterwards by the back-translation call
([llm_entropy_backtranslate.md](./llm_entropy_backtranslate.md)), so that English does not pull the generation back
to its English mode (hence `english_hint: null`).

**Choices in the text, and why.**

- **It is the scaffold** ([llm_entropy_scaffold.md](./llm_entropy_scaffold.md)) with the label paragraph rewritten for
  the language and **without the English example labels**, which would pull the answers towards English words; no
  example in the language either, since a translator's example would be unpinned and unchecked.
- **A short reason first**, as in the scaffold (Sonnet 5.5 refuses "think" fields).
- **"in lower case where the script has capital letters"**: six of the ten scripts have no letter case.
- **`romanization`** is the label in the Latin alphabet (the label itself for German, Finnish and Turkish); the
  back-translation call gives its own romanisation too, and the table keeps both.
- **JSON keys and the eight `kind` values stay in English** in every translation (the translation instruction says
  so, and `translate-prompts` refuses a translation that lost one), so one parser reads every language.

## The prompt

````text
You are helping build a list of personality traits for a research project. We already have a long list in English and we want words and short phrases that are not on it, so a plain list of common trait words is of no use to us. Each request below names a domain of life. Name the traits of character that a native speaker of {language} would name for it, and let the language take you to words and concepts that English lacks.

What counts: a stable disposition or style that a speaking persona could enact in conversation, over months and years: a way of feeling, thinking, acting, speaking or relating to others, admirable or not. Include vices as freely as virtues. What does not count: a role (a job, a relationship, a position), a mood of the moment, a skill, a single act, a physical feature, a bare evaluation. If what the domain brings to mind is one of those, still give it, with the "kind" field saying what it is, rather than leaving it out.

Give as many items as the request asks for. Labels are in {language}, in lower case where the script has capital letters, 1 to 4 words, and one name each with no commas. Name character traits a native speaker would name here, preferring ones with no single English word. Prefer words that a well-read native speaker knows over rare or archaic ones, and prefer a phrase that names a concept exactly over a single word that nearly does. Do not use the same word twice in different forms. Each item also carries "romanization" (the label in the Latin alphabet; for a language written in it, the label unchanged) and "english_hint": null.

The "kind" field is your guess at what each item is: "trait" (a lasting disposition, as above), "membership" (a standing fact of someone's life that others use to say who they are, such as a nationality, a faith or a family situation), "state" (a condition someone is in for a while), "physical" (a feature of the body), "role" (a job, an office, a relationship or a position), "action" (a single deed), "evaluative" (bare praise or blame) or "not_a_persona" (it says nothing about how a person acts, thinks or speaks).

Respond with a JSON object only, in {language}, no other text. First give a short reason, one or two sentences on how you read the domain, then the items:
{"approach": "<one or two sentences on how you read the domain>",
 "items": [{"label": "<1-4 words in {language}>",
            "romanization": "<the label in the Latin alphabet>",
            "english_hint": null,
            "gloss": "<one sentence of at most 25 words in {language}, starting with the {language} for 'This means', that describes the behavior in plain words without repeating the label>",
            "antonym": "<the opposite disposition in {language}, in the same form, or null if there is none>",
            "kind": "<trait | membership | state | physical | role | action | evaluative | not_a_persona>",
            "ambiguity_flag": <true if the label has another common meaning that the gloss has to rule out>}, ...]}
````

## Rendered sample

The master for German (`{language}` replaced), before translation, is the block above with "German" in each place;
the request it is sent with, in English before translation, is the user-turn master of
[prompts.py](../../../assistant_axis/gapgen/generators/llm_entropy/prompts.py) (`C_USER_MASTER`):

````text
Domain of life: {domain}.
Name 15 to 20 character traits that are specifically about how a person relates to this domain of life: admirable and unadmirable ones, preferring ones for which English has no single word.
````

`{domain}` stays a placeholder in the translation and is filled with the translated domain name (`money` -> `Geld`)
at render time.  The ten translations, each beside its back-translation, are pasted into the task report for Roger.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft (with the scaffold's hygiene rephrasings: "null if there is none", "a well-read native speaker"): the scaffold with the language paragraph of the plan's "Rendered prompts" section in place of the English label paragraph (its English examples left out), the reason field as in the scaffold, and the two (c) fields in the schema | plan 06 § 3.3, coding plan § "Rendered prompts" (c) |
