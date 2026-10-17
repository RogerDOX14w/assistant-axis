# The LLM-entropy generator's scaffold (families a, b, d, e of workstream 6)

| | |
|---|---|
| **Status** | Draft 1 (2026-10-17, Opus), pinned as version 1.  Not yet run: the pilot ([coding_plan_06_llm_entropy.md](../coding_plan_06_llm_entropy.md) § 10) is its first test; a family whose median label-set Jaccard is above 0.6 gets one bounded revision of its user turn (gate 1). |
| **What the model is shown** | This text as the system turn, and one user turn per call carrying the constraint: a domain and a mode (family a), one person from Wikidata (family b), a spelling or a form (family e); with the verbalized-sampling paragraph appended (family d, stage 1), or a fresh call quoting a stage-1 answer (family d, stage 2).  No corpus label appears anywhere in a prompt. |
| **What it returns** | A short reason first (`approach`), then `items`: each `label`, `gloss`, `antonym`, `kind` (M1's vocabulary, a guess reported beside M1's verdict, never a gate), `ambiguity_flag`, and under family d `probability`. |
| **What it is tuned on** | Not tuned.  The pilot reads the parse rate, the label-set Jaccard between the three runs of each prompt and the yield per dollar. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); the model-test arms on Sonnet 5.5 (`claude-sonnet-5-5`).  No temperature (both refuse one); both think adaptively, the thinking billed as output.  About 2,800 characters, roughly 700 tokens: above Haiku 5.5's 512-token cache minimum, so it is sent with the system block cached. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written.  Leave the fence lines themselves alone.  Notes for Roger go under "Your notes", outside the
block.  A changed text needs a new pin (`rubric_pins.py bump llm_entropy_scaffold --why '...'`), and the generate
command refuses a text that is not its latest pin.

**What it is for.**  Asked plainly for personality traits, an instruction-tuned model collapses onto the same few
hundred words, which is roughly how the corpus was built.  Every user turn therefore carries a constraint the model
cannot satisfy from its mode (a life domain and a way the trait shows, a random person, a spelling), and this text
tells it to satisfy the constraint first.  The code is
[prompts.py](../../../assistant_axis/gapgen/generators/llm_entropy/prompts.py); the command is
`llm_entropy_generator.py generate`.

**Choices in the text, and why.**

- **A short reason first, never "think".**  Sonnet 5.5 refuses a prompt that tells it to think in a JSON field
  (`stop_reason: "refusal"`, category `reasoning_extraction`; the judging rule, 2026-10-13), and the Sonnet arms
  of the model test receive this text.  So the reason field asks for one or two sentences on how the constraint
  was read, the form M3's rubric uses and Sonnet answers.
- **"Give as many items as the request asks for".**  The plan's draft said "Give 15 to 20 items", which
  contradicts family b's user turn ("Name the 8 to 12 traits"); read as the model receives it (the rendered-prompt
  rule), the system turn now defers to the request, which says 15 to 20 for families a and e.
- **Every item is kept.**  The text asks for roles, moods, skills and the rest to be given with their `kind`
  rather than left out ("nothing is dropped here", QUESTIONS 48); M1 decides.
- **The `kind` values are glossed in one line each**, abridged from M1's kind call
  ([step2_kind.md](./step2_kind.md)), so that the guess beside M1's verdict means something; M1's wording decides.
- **Labels of 1 to 4 words**, a hyphenated compound counting as one word (Roger, 2026-10-13: part of the point is
  concepts that are not a single English word); one name, no commas (the IPIP naming rule of 2026-10-13).
- **US spelling** in the instructions ("behavior"), since the glosses become the registry's gloss hints.

**Word hygiene.**  The three example labels (`punctilious`, `slow to anger`, `avoids the limelight`) are the IPIP
naming rubric's and are not corpus stems, queue labels or validation-file words; `great` is the bare evaluation's
example.  [test_gapgen_llm_entropy_prompts.py](../../../assistant_axis/tests/test_gapgen_llm_entropy_prompts.py)
fails if an example becomes one of those, and records the ordinary words of the text that are on those lists
anyway: the platform's `PROSE_ALLOWED` words and `single` ("a single word", recorded as the structural generator's texts record it); a new one fails.  Three of the plan's words were on those lists and were rephrased, since nothing had been sent: "no clear opposite" (now "null if there is none"), "a short descriptive phrase" ("a short phrase that describes it"), "an educated reader" ("a well-read adult").

## The prompt

````text
You are helping build a list of personality traits for a research project. We already have a long list and we want words and short phrases that are not on it, so a plain list of common trait words is of no use to us. Each request below puts a constraint on what to name: a domain of life and a way the trait shows, a particular person, a spelling, or a probability. Satisfy the constraint first and let it take you to less obvious words.

What counts: a stable disposition or style that a speaking persona could enact in conversation, over months and years: a way of feeling, thinking, acting, speaking or relating to others, admirable or not. Include vices as freely as virtues. What does not count: a role (a job, a relationship, a position), a mood of the moment, a skill, a single act, a physical feature, a bare evaluation ("great"). If what the constraint brings to mind is one of those, still give it, with the "kind" field saying what it is, rather than leaving it out.

Give as many items as the request asks for. Labels are English, lower case, 1 to 4 words, a hyphenated compound counting as one word, and one name each with no commas: an adjective or an adjectival phrase where English has one (for example "punctilious" or "slow to anger"), otherwise a short phrase that describes it (for example "avoids the limelight"). Prefer words that a well-read adult knows over rare or archaic ones, and prefer a phrase that names a concept exactly over a single word that nearly does. Do not use the same word twice in different forms.

The "kind" field is your guess at what each item is: "trait" (a lasting disposition, as above), "membership" (a standing fact of someone's life that others use to say who they are, such as a nationality, a faith or a family situation), "state" (a condition someone is in for a while), "physical" (a feature of the body), "role" (a job, an office, a relationship or a position), "action" (a single deed), "evaluative" (bare praise or blame) or "not_a_persona" (it says nothing about how a person acts, thinks or speaks).

Respond with a JSON object only, no other text. First give a short reason, one or two sentences on how you read the constraint, then the items:
{"approach": "<one or two sentences on how you read the constraint>",
 "items": [{"label": "<1-4 words>",
            "gloss": "<one sentence of at most 25 words that starts 'This means' and describes the behavior in plain words, without repeating the label>",
            "antonym": "<the opposite disposition, in the same form, or null if there is none>",
            "kind": "<trait | membership | state | physical | role | action | evaluative | not_a_persona>",
            "ambiguity_flag": <true if the label has another common meaning that the gloss has to rule out>}, ...]}
````

## Rendered sample

A call is the block above as the system turn, byte for byte, and one user turn.  `llm_entropy_generator.py prompts`
prints one user turn per variant exactly as sent; the plan's "Rendered prompts" section has the whole set, and
the task report pastes them.  Family a, prompt `a:money:habit`:

````text
Domain: money. Mode: a habit.
Name 15 to 20 traits that are specifically about how a person relates to money, each in the form of a habit (something the person does as a rule, as opposed to an attitude they hold, a way they speak, a feeling they tend to have, a way they think, a moral stance they take, or a strategy they use with other people). Include admirable and unadmirable ones, and ones with no common single word.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from the plan's "Rendered prompts" text, with three edits: "Give 15 to 20 items" became "Give as many items as the request asks for"; "Think about the constraint first, then list" became "First give a short reason, one or two sentences on how you read the constraint, then the items" (and the `approach` placeholder likewise); a one-line gloss of each `kind` value was added; "behaviour" became "behavior"; three words on the hygiene lists rephrased ("clear", "descriptive", "educated") | the (b) user turn asks for 8 to 12 items; Sonnet 5.5 refuses "think" fields (2026-10-13); the kind guess needs its vocabulary defined to be comparable with M1's; US spelling for text that becomes gloss hints |
