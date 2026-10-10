# W16: the native-language side set, design proposal

Written 2026-10-09 for Roger.  Item W16 of the [work list](./work_list.md); the
decision it implements is the last bullet of
[TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "TODO:
post-extraction checks for chunk 4" (the corpus stays in English; a tagged
`experiment` side set measures whether nationality vectors would separate by
language or by people).  **Nothing here is built.**  No corpus file has changed.
Terms not defined below are in the [glossary](../../reports/trait_gap_generation/glossary.md)
(cosine similarity, nearest neighbour, persona vectors).

Four words used throughout:

- **Arm**: one condition of the experiment.  It is one side file per
  nationality, named by its instruction language and its response language.
- **Directive**: one fixed sentence added to the end of each of the five
  instructions to set the answer language ("Réponds toujours en français.").
- **Slot**: the activation files keep 8 slots per layer
  ([spans.py](../../assistant_axis/internals/spans.py)).  Slot 0 is the mean
  over the response tokens.  Slots 1 to 7 are the seven header tokens Qwen
  emits before it answers (`<|im_start|>`, `assistant`, `\n`, `<think>`,
  `\n\n`, `</think>`, `\n\n`).  The **header slots** are computed from the
  prompt alone, before any response token exists.  Slot 6, layer 25 is the
  default of several analyses (for example
  [axis_cosine_seriation.py](../../results_analysis/axis_cosine_seriation.py)).
- **Language offset**: the vector of the no-persona assistant answering in
  language L minus the same assistant answering in English.  It is the part of
  a native-language vector that comes from the language alone.

---

## Decisions first

**1. Which arms?**
- (a) **The smallest set that answers the question.**  It has 11 files.  For
  each of the five nationalities there is a native-language arm (the
  instructions translated, answers in that language).  For each language there
  is a no-persona control, used to measure the language offset.  One more file
  is [Canadian](../../data/traits/instructions/canadian.json) translated into
  French.  It has the same language as the French arm and a different people,
  so it separates the two factors directly.  Without it the test rests on
  subtracting the language offset, which assumes the offset is the same for
  every persona.
- (b) **A balanced 2×2 of instruction language by answer language.**  It has
  26 files: (a) plus three arms per nationality, namely English instructions
  answering in English (with a directive), English instructions answering in L,
  and native instructions answering in English.
- **Recommendation: (b).**  It adds about 1.5 GPU-hours and $3.  It also tells
  us *which* language carries any separation.  That matters because slot 6 sees
  only the prompt.  If the effect sits in the instruction, then native
  instructions with English answers are no fix.  If it sits in the answer, they
  might be.  The side set rides on the main extraction's pod session, and an
  arm added later needs a session of its own.  If you want only the question
  as posed, (a) answers it.

**2. What the prompt looks like.**
- Recommended: the shared English extraction questions in every arm, with a
  one-sentence directive in every new arm.
- Alternative: native instructions with no directive, which is the literal
  "what if the corpus file were in French".
- Alternative: questions translated into L.
- English questions keep the question tokens identical across arms, so
  differences at the header slots come only from the system prompt.  This is
  the decision's own argument (the shared questions make vectors comparable).
- The directive fixes each arm's answer language.  Without it, a French
  instruction followed by an English question leaves Qwen free to answer in
  either language, and a vector that mixes the two answers nothing.
- The pre-check (decision 6) runs the no-directive version too, so the readout
  still reports what Qwen does on its own.

**3. Who writes the native text.**
- Recommended: a faithful translation of the five existing English `pos`
  instructions, by Claude Opus 5.5 called directly at Anthropic.  GPT-4.1-mini,
  called directly at OpenAI, back-translates as a check, and a reviewer reads
  the three texts side by side.
- Alternative: generating new instructions in L from the description.  That
  would read more naturally, but the content would change along with the
  language, so a difference in the vectors could not be attributed to either.
  The RogerV2 generator template, tuned in English over ten drafts, would also
  have to be translated.
- Register, if you accept the defaults: French *tu*, German *du*, Brazilian
  *você*, Japanese polite form (です・ます, addressing あなた), and Chinese 你
  in Simplified characters (Mandarin).  These are the usual forms of a system
  prompt in each language.
- One question for you: do you, or anyone you can ask, read any of the five
  languages?  If so, a native-speaker spot check of one instruction per
  language would be worth more than the back-translation.

**4. Judging the non-English answers.**
- Recommended: judge them as they are.  Step 3 stays unchanged: GPT-4.1-mini
  with the same English rubric, label and description as the corpus file.
  Two things are measured beside it:
  - the **language cue**, meaning how often the no-persona control's French
    answers score 3 on the French rubric;
  - **filter-free vectors**, the mean over all 500 responses, so the
    comparison does not depend on the judge.
- Translate the answers into English and rejudge them (about $12) only if the
  cue is material, which I would set at more than one control answer in ten
  scoring 3.
- Alternative: always translate and rejudge.
- The cue is real, because the descriptions say "French at home", "Japanese at
  home" and so on.  A French answer is therefore evidence of the trait by the
  rubric's own text.

**5. How the extraction reads the side directory.**
- Recommended: two small pipeline changes with tests.
  - A `--traits_dir` option on [run_pipeline.sh](../../pipeline/run_pipeline.sh),
    passed to step 1 and step 3.
  - An `--all_responses` flag on [4_vectors.py](../../pipeline/4_vectors.py)
    for the filter-free vectors.
- Alternative: drive steps 1 to 4 by hand with explicit flags, which needs no
  code change but is easier to get wrong on the pod.
- Christina mode cannot be used as it stands (§ 2 below).

**6. A pre-check on hosted Qwen now?**
- Recommended: yes, about $2, through
  [opening_form_experiment.py](../../data_analysis/opening_form_experiment.py).
  Qwen runs on DeepInfra, a United States host already on the allowlist, and
  the judge is called directly at OpenAI.
- It measures three things before the pod:
  - the answer language of every arm, with and without the directive;
  - each arm's share of score 3, since step 4 needs at least 30 of 500;
  - the language cue.
- The 2026-09-29 replication found the hosted copy tracks the pod per
  instruction: r = 0.97 over 35 instructions, about 3 points lower
  ([report.json](../../reports/opening_forms/replication/report.json)).
- Alternative: skip it and find out on the pod.

The nationalities: the five named in the decision, each with one clear
language.  [Italian](../../data/traits/instructions/italian.json) and
[Russian](../../data/traits/instructions/russian.json) also qualify and could
be added at 5 files each.  I do not recommend it, since five is enough for the
tests below.

---

## 1. The five nationality files today

They are members of the 13-member nationality `map` (American, Australian,
Brazilian, British, Canadian, Chinese, French, German, Indian, Italian,
Japanese, Nigerian, Russian).  All five were generated on 2026-10-08 under
trait rubric V2 (template `9255dd3430ef`, Claude Sonnet 4.6).  They are tagged
`membership` and have `non-X` negative labels.  Each has 5 `pos`/`neg`
instructions, 40 own questions and an `eval_prompt`.  The extraction uses only
the `pos` instructions: the 40 questions and the 0-100 `eval_prompt` are
unused by the pipeline.

| file | language for the arm | description (verbatim) |
|---|---|---|
| [French](../../data/traits/instructions/french.json) | French (fr) | This means being from France and living there: French at home, the bac, the rentrée in September, August at the coast or the grandparents', and the president on the eight o'clock news. |
| [German](../../data/traits/instructions/german.json) | German (de) | This means being from Germany and living there: German at home, the Abitur or an apprenticeship, Christmas markets in Advent, the Bundesliga on Saturday, shops shut on Sunday, and coalition politics in Berlin. |
| [Japanese](../../data/traits/instructions/japanese.json) | Japanese (ja) | This means being from Japan and living there: Japanese at home, the school year from April, New Year and Obon with the family, the train to work, and the prime minister on the NHK news. |
| [Brazilian](../../data/traits/instructions/brazilian.json) | Brazilian Portuguese (pt) | This means being from Brazil and living there: Portuguese at home, Carnival in February, rice and beans at lunch, the nine o'clock novela, the Seleção on match day, and compulsory voting in October. |
| [Chinese](../../data/traits/instructions/chinese.json) | Mandarin, Simplified (zh) | This means being from China and living there: Mandarin or the local dialect at home, the gaokao, Spring Festival in the hometown, WeChat for everything, and the seven o'clock news on CCTV. |
| [Canadian](../../data/traits/instructions/canadian.json) (arm CA only) | French | This means being from Canada and living there: English or French at home, a provincial health card, Thanksgiving in October, hockey through the winter, and the Liberals or the Conservatives in Ottawa. |

A sample of the English `pos` instructions, the text that would be translated:

- French p0: "Be someone who grew up in France and has never left it behind.  You speak French at home, sit the bac, and measure the year by la rentrée in September and the August exodus to the shore or your grandparents' house."
- Japanese p1: "You are a person rooted in Japan: you commute by train, watch the prime minister address the nation on public television, and your year turns on the school calendar starting in April and on family gatherings at New Year and Obon."
- Chinese p2: "From now on, you are someone who has lived their whole life inside China.  You switch between Mandarin and a local dialect depending on who you are with, return to your hometown every Spring Festival, and rely on WeChat for money transfers, messaging, and news."

German and Chinese carry a `hand_edits` note: their fifth instruction's opening
was rewritten by hand.  The translation takes the files as they stand.  The
no-persona control is built from [default.json](../../data/roles/instructions/default.json),
whose five instructions are: (empty), "You are an AI assistant.", "You are a
large language model.", "You are {model_name}." and "Respond as yourself.".

## 2. How the extraction reads instruction files, and where a side directory fits

**Step 1** ([1_generate.py](../../pipeline/1_generate.py),
[generation.py](../../assistant_axis/generation.py)).  In Roger mode with
`--traits_only`, step 1 globs `--traits_dir/*.json` (default
`../data/traits/instructions`) and names each output by the file stem.  For each
file it uses only `instruction[i]["pos"]`, replacing `{model_name}` in it.  It
asks every one of the five instructions the 300
[extraction questions](../../data/extraction_questions.jsonl), taking every
third, so 100 questions and 500 responses per file.  Sampling uses temperature
0.7, top-p 0.9 and 512 tokens, with thinking off.  A side directory therefore
needs only `--traits_dir`.  [1_generate.py](../../pipeline/1_generate.py)
has the flag; [run_pipeline.sh](../../pipeline/run_pipeline.sh) does not pass
it.

**Step 2** ([2_activations.py](../../pipeline/2_activations.py)).  Step 2
reads whatever response files are in its input directory.  It writes 8 slots ×
64 layers per response, about 2.6 GB per file.  Nothing here depends on the
trait directory.

**Step 3** ([3_judge.py](../../pipeline/3_judge.py)).  With `--entity_type
trait`, step 3 looks the stem up in `--traits_dir` (default
`../data/traits/instructions`).  It builds the 0-3 `TRAIT_EVAL_TEMPLATE`, with
reasoning before the score, from that file's `positive_label` and
`description`, and judges with GPT-4.1-mini.  If the side directory is not
passed, every side stem logs "No trait file found" and gets no scores, and
step 4 then skips it.  If it is passed, the judge sees exactly the rubric
header the corpus file gets, because the side files copy the label and
description verbatim.  That is the comparability we want.

**Step 4** ([4_vectors.py](../../pipeline/4_vectors.py)).  Step 4 takes the
mean of the score-3 activations and needs at least 30 of them (`MIN_COUNT=30`
in roger mode).  Any stem *containing* `default` is averaged over all its
responses with no scores, because the code tests `"default" in role`.  The
controls use this on purpose (§ 6).  No other side stem may contain the
string.

**Step 5** computes an axis over whatever vectors the run produced.  For the
side run that output is meaningless and is ignored.

**Christina mode is not usable as it stands.**  It defaults to 240 questions
with no reduction, which would give 1,200 responses per file.  Its step 3
passes no `--traits_dir`, and its step 4 uses the default minimum of 50.

**Proposed route (decision 5):**

1. In [run_pipeline.sh](../../pipeline/run_pipeline.sh), add `--traits_dir
   PATH` in roger mode.  It is passed to the `traits` type's step 1
   (`1_generate.py --traits_only --traits_dir`) and step 3 (`3_judge.py
   --traits_dir`).  About 8 lines.  Test: a pytest that puts a stub `uv` first
   on `PATH`, runs the script with `--types traits --traits_dir X
   --skip-gpu-check --no-tmpfs --no-scan`, and asserts that the 1_generate and
   3_judge calls received `--traits_dir X`.  It would live at
   [test_run_pipeline_traits_dir.py](../../pipeline/tests/test_run_pipeline_traits_dir.py),
   not there yet.
2. In [4_vectors.py](../../pipeline/4_vectors.py), add `--all_responses`: the
   mean of every activation for every stem, written to its own `--output_dir`,
   so we get the filter-free vectors.  Test it on small synthetic activation
   dicts, loaded by importlib as
   [test_hf_cache_warning.py](../../pipeline/tests/test_hf_cache_warning.py)
   does.
3. **Where the outputs go on the pod.**  The side run gets its own output
   directory, a sibling of the main run's, not a subdirectory.  Analyses glob
   `<data_dir>/traits/vectors/*.pt`, and the post-pipeline scan walks its own
   `--root`, so a side vector must never land in the main run's `traits/`.
   Copy or symlink the main run's `default/` into the side directory before
   launching.  Step 0 then skips, and the side set shares the corpus's default
   sample instead of drawing a second one at temperature 0.7.
4. **Order within the pod session.**  Run the side set right after the main
   run's `traits` type, on the same commit and settings.  The launch is
   `run_pipeline.sh --types traits --traits_dir
   ../data/traits/experiments/native_language --output_dir <side dir>`.
   **Keep these activation files until the analysis's pod-side extraction (§ 7)
   has run:** the six English base files (French, German, Japanese, Brazilian,
   Chinese, Canadian) and the default.  The main run may otherwise delete
   activations to save disk.
5. Mirror the result to its own local dataset directory, with its own
   MANIFEST from [regenerate_dataset_manifest.py](../../tools/regenerate_dataset_manifest.py):
   `runpod_workspace/qwen/<main run name> native_language/`.  It is never
   placed inside the main run's mirror.

## 3. What is translated and what stays

| part of the file | in the side file |
|---|---|
| `pos` instructions (5) | translated faithfully, or kept in English for the EE and EL arms, then the directive appended |
| `positive_label`, `negative_label`, `description` | copied verbatim in English; step 3's rubric reads them |
| `neg` instructions, the 40 own questions, `eval_prompt`, `arrangement`, `generator` | dropped: nothing in the extraction reads them, and their absence keeps the file from passing for a corpus file |
| extraction questions | unchanged: the shared English 100 |

**The arms**, with French as the example.  Every nationality gets the same
cells.  The stem pattern is `<base>_i<instruction language>_r<response language>`.

| arm | stem (link: not there yet) | instruction | directive appended | answers in | what it isolates |
|---|---|---|---|---|---|
| E | [french](../../data/traits/instructions/french.json) (the corpus file, from the main run) | English | none | English | the reference |
| NL | [french_ifr_rfr](../../data/traits/experiments/native_language/french_ifr_rfr.json) | French translation | Réponds toujours en français. | French | what a native-language corpus file would give |
| C | [default_ifr_rfr](../../data/traits/experiments/native_language/default_ifr_rfr.json) | default's five, in French | Réponds toujours en français. | French | the language offset, with no persona |
| CA | [canadian_ifr_rfr](../../data/traits/experiments/native_language/canadian_ifr_rfr.json) | Canadian, in French | Réponds toujours en français. | French | same language as NL, different people (French only) |
| EE (b) | [french_ien_ren](../../data/traits/experiments/native_language/french_ien_ren.json) | English, verbatim | Always answer in English. | English | the directive's own effect (EE against E) |
| EL (b) | [french_ien_rfr](../../data/traits/experiments/native_language/french_ien_rfr.json) | English, verbatim | Always answer in French. | French | the answer language, with the instruction held in English |
| NE (b) | [french_ifr_ren](../../data/traits/experiments/native_language/french_ifr_ren.json) | French translation | Réponds toujours en anglais. | English | the instruction language, with English answers: the only compromise design |

Language codes are `fr`, `de`, `ja`, `pt` (Brazilian) and `zh` (Mandarin,
Simplified), for example `japanese_ija_rja` or `default_izh_rzh`.  The
directives are fixed text appended by the build script.  In fr, de and pt there
is a space before the directive; in ja and zh there is none.

| L | answer in L | answer in English (NE) | English directive (EL) |
|---|---|---|---|
| fr | Réponds toujours en français. | Réponds toujours en anglais. | Always answer in French. |
| de | Antworte immer auf Deutsch. | Antworte immer auf Englisch. | Always answer in German. |
| ja | 常に日本語で答えてください。 | 常に英語で答えてください。 | Always answer in Japanese. |
| pt | Responda sempre em português. | Responda sempre em inglês. | Always answer in Portuguese. |
| zh | 请始终用中文回答。 | 请始终用英文回答。 | Always answer in Chinese. |

**Does the answer language matter for the comparison?  Yes, and differently
per slot.**  Slot 0 averages the response tokens, so it carries the answer
language directly.  The header slots, including slot 6, are computed before
the first response token.  They see the system prompt (instruction language
plus directive) and the English question, so the answer language reaches them
only as the model's plan.  The analysis therefore reports slot 0 and slot 6
separately.  The 2×2 of option (b) is what tells them apart: EL against E
gives the answer-language effect, and NE against E gives the
instruction-language effect.

There is one more confound, at slot 0 only.  Generation stops at 512 tokens,
and about 71% of English responses reach that cap.  French and German need
more tokens than English for the same content, and Chinese needs fewer, so a
capped answer holds a different amount of content in each language.

## 4. Who produces the native-language instructions

The build script is [build_native_language_set.py](../../data_analysis/build_native_language_set.py)
(not there yet).  For each language it makes one call to Claude Opus 5.5 at
Anthropic for the nationality's five instructions, one for default's four
non-empty ones, and for French one more for Canadian.  That is 11 calls in
all.  A back-translation by GPT-4.1-mini at OpenAI follows, and a review table
(original, translation, back-translation) is written for the reviewer and for
you.

Both models are called directly, as the hosted-models rule requires.  No model
is reached through a router, and none comes from a host in China.  A
Qwen-based translation for Chinese is therefore not considered.

The draft prompt, rendered as the model would receive it for French:

> **System:** You translate system prompts for a research experiment.  The experiment compares how a language model represents a persona when the same instructions are given in English and in another language, so the translation must change the language and nothing else.
>
> Translate each numbered English instruction into French as written in France.
> - Same content, same sentences in the same order; nothing added, nothing left out, nothing softened or explained.
> - Address the reader as "tu", as the English addresses them as "you"; keep an imperative where the English has one.
> - Where the English names an institution, custom or programme of the country, use the name a person from that country would use.
> - Write natural French, as a French speaker would write an instruction addressed to a person, not a word-for-word gloss.
> - Keep "{model_name}" exactly as written if it appears.
>
> Return JSON only: {"translations": ["<1>", "<2>", "<3>", "<4>", "<5>"]}, in the order given.
>
> **User:** For context, not to be translated: the instructions describe the trait "French": This means being from France and living there: French at home, the bac, the rentrée in September, August at the coast or the grandparents', and the president on the eight o'clock news.
>
> 1. Be someone who grew up in France and has never left it behind. You speak French at home, sit the bac, and measure the year by la rentrée in September and the August exodus to the shore or your grandparents' house.
> 2. You are someone whose life runs on French time and French habits. You watch the eight o'clock news for the president's face, you know the difference between a grande école and a lycée from the inside, and September feels like the true beginning of the year.
> 3. From now on, you are someone rooted entirely in French life. You live in France, raise children in the French school system, spend August at the Atlantic coast or with family in the countryside, and take the president's television address as the backdrop to your evening.
> 4. Become someone for whom France is the only home they have ever known. The bac looms every spring, la rentrée reshapes September, and the whole country emptying toward the sea each August is simply what summer is.
> 5. You are French in the full, lived sense: France is where you sleep, where you shop, where your children go to school, and where the same president appears on the same news program every evening while you eat dinner.

For the control the context line reads: "the instructions are the neutral
system prompts of the baseline: an AI assistant with no persona".  The
language name, variety and register are the only per-language parameters.  I
left out example native terms (le bac, 高考) on purpose, because they prime
additions.  A flagged instruction gets one retranslation round, and anything
still flagged goes to you.

## 5. Judging non-English answers

The judge runs as in § 2: GPT-4.1-mini, the English rubric, and the side
file's English label and description.  GPT-4.1-mini reads all five languages.
The `SCORE:` parser and the 99% parse-rate warning apply unchanged.  If the
judge reasons in the answer's language, the `SCORE:` line still parses.

| measure | how | where |
|---|---|---|
| answer-language compliance per arm | a local language identifier, no API: kana means Japanese; Han with no kana means Chinese; for Latin script, function-word counts for en, fr, de and pt.  It would live in [language_id.py](../../assistant_axis/language_id.py), not there yet, with unit tests | pre-check and pod |
| share of 0/1/2/3 per arm, and the count of score-3 answers against `MIN_COUNT` 30 | step 3 as is | pre-check and pod |
| the language cue | the control arm judged on its nationality's rubric (its file carries that label and description, so step 3 judges it; step 4 ignores the scores, since the stem contains `default`).  The English baseline is the hosted model with no system prompt, judged on the same rubric, which [opening_form_experiment.py](../../data_analysis/opening_form_experiment.py) supports as an empty variant | pod (500 per language) and pre-check |
| optional: translate and rejudge | GPT-4.1-mini translates each native-language answer into English.  The translations are written as response files with the same schema to `responses_translated/` and judged by the unchanged [3_judge.py](../../pipeline/3_judge.py) into `scores_translated/`, then [4_vectors.py](../../pipeline/4_vectors.py) `--scores_dir scores_translated` gives a third vector set from the original activations.  The script writes a token-usage record beside its output (the hard rule) | pod or local, only if the cue is material |

## 6. File format, tags and keeping the files out

The side files go in [data/traits/experiments/native_language/](../../data/traits/experiments/native_language/)
(not there yet).  It is a sibling of `instructions/`, not inside it.
[sync_entity_lists.py](../../tools/sync_entity_lists.py) and
[arrangements.py](../../assistant_axis/arrangements.py) (behind
[check_arrangements.py](../../data_analysis/check_arrangements.py)) glob
`data/<kind>/instructions/*.json` non-recursively, and no code in the
repository globs `data/traits` recursively (checked).  The side files are
therefore invisible to the following:

- [trait_list.json](../../data/traits/trait_list.json);
- the arrangement checker;
- the trait-gap platform;
- the seed queue;
- the provenance multi-glob of corpus instructions.

The pair lists in [axis_judge_experiments/](../axis_judge_experiments/) and
[goal_roles_and_traits.json](../../data/goal_roles_and_traits.json) are
hand-curated stem lists.  New stems such as `french_ifr_rfr` cannot appear in
them unless someone adds them.

An example, with my own illustrative translation of p0.  It is not build
output:

```json
{
  "positive_label": "French",
  "negative_label": "non-French",
  "description": "This means being from France and living there: French at home, the bac, the rentrée in September, August at the coast or the grandparents', and the president on the eight o'clock news.",
  "instruction": [
    {"pos": "Sois quelqu'un qui a grandi en France et qui ne l'a jamais quittée. Tu parles français à la maison, tu passes le bac, et ton année se mesure à la rentrée de septembre et à l'exode d'août vers la mer ou chez tes grands-parents. Réponds toujours en français."},
    {"pos": "…"}, {"pos": "…"}, {"pos": "…"}, {"pos": "…"}
  ],
  "tags": ["membership", "experiment"],
  "experiment": {
    "name": "native_language",
    "arm": "NL",
    "base": "french",
    "instruction_language": "fr",
    "response_language": "fr",
    "directive": "Réponds toujours en français.",
    "judge_rubric_from": "french",
    "base_sha256": "<sha256 of the base file's label, description and five pos texts>",
    "base_generator": {"style": "RogerV2", "template_sha256": "9255dd3430ef", "model": "claude-sonnet-4-6", "generated_at": "2026-10-08"},
    "translation": {"model": "claude-opus-5-5", "prompt_sha256": "…", "translated_at": "…",
                    "back_translation_model": "gpt-4.1-mini", "review": "…"}
  }
}
```

The `experiment` tag in `tags` follows the existing `physical` mechanism.  The
`experiment` object holds the arm and its provenance.  The control files carry
the nationality's label and description (`judge_rubric_from`) and `"base":
"default"`.

Safeguards:

- The build script refuses to write anywhere under `instructions/`.
- `--check` recomputes every `base_sha256` and exits 1 if a base file's label,
  description or `pos` text changed after translation.  It goes on the
  pre-extraction checklist, since a base edited after translation would make
  its side files translations of text that was never extracted.
- A boundary test at
  [test_native_language_side_set.py](../../data_analysis/tests/test_native_language_side_set.py)
  (not there yet) asserts four things:
  - every side file carries the tag;
  - no file in `instructions/` does;
  - no side stem appears in [trait_list.json](../../data/traits/trait_list.json),
    any arrangement, the goal lists, or the pair lists when present;
  - no side stem contains `default` except the controls.
- The token usage of the translation calls goes to
  [usage.json](../../data/traits/experiments/native_language/usage.json) (not
  there yet), through `MultiModelUsage`.
- Documentation: [data/README.md](../../data/README.md) gains the
  `experiments/` directory; TRAITS_TO_ADD's item gets a status line;
  [AGENT_NOTES.md](../../AGENT_NOTES.md) rule 10 (memberships) gets a pointer;
  the pipeline README gets `--traits_dir`.

## 7. Cost and the analysis afterwards

**Cost** (all under $20, so real time per the batch rule; the side set does not
need a separate quote, but it is a line in the main extraction's quote):

| item | volume | cost |
|---|---|---|
| translation (Opus 5.5) and back-translation (GPT-4.1-mini) | 11 calls, about 55 texts | under $0.50 |
| pre-check, hosted Qwen and judge | 8 arms × 5 instructions × 20 questions × 5 nationalities, plus CA: about 4,100 answers | about $2 (from the per-call costs in earlier [usage.json](../../reports/opening_forms/fault_or_virtue/usage.json) records) |
| pod, steps 1 and 2 | 26 files under (b), 11 under (a) | 2 to 4 GPU-hours under (b), about an hour of wallclock on four GPUs; 1 to 2 under (a).  The basis is about 5 GPU-minutes per file plus model loading per worker: in [pipeline_20260502_004525.log](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/pipeline_20260502_004525.log), 7 traits took 16 minutes for step 1 and 19 for step 2 on one GPU; in [pipeline_20260426_173312.log](../../runpod_workspace/qwen/qwen-3-32b%20Roger%208slot/pipeline_20260426_173312.log), step 2 ran 299 traits on 4 GPUs in 3 h 07.  This is a few per cent of the main run's standalone part |
| pod disk | about 2.6 GB of activations per file | about 70 GB under (b), held until the extract step has run |
| step 3 judge | 13,000 calls under (b), 5,500 under (a) | about $5, or $2 |
| optional translate and rejudge | 16 native-language files × 500 | about $12 |

[3_judge.py](../../pipeline/3_judge.py) writes no `usage.json`, which the
token-usage hard rule asks of batched judge sites.  For the side set's $5 it
hardly matters, but the main extraction's step 3 (some 600,000 calls) should
gain it before the run.

**The analysis** would live at [native_language_compare.py](../../results_analysis/native_language_compare.py),
not there yet, with the provenance envelope of
[provenance.md](../../.claude/rules/provenance.md) and tests on synthetic
vectors with a known language offset.  Its `extract` step runs on the pod.  It
reads the activation files of the side arms, the six English bases and the
default, and writes per-question means at slots 0 and 6, for every fourth
layer plus 25 and 32, in fp16, both score-3 and all-response.  That is under
100 MB per file and is what the bootstrap intervals need.  Everything else runs
locally from those means and the vectors.

The analysis works with persona offsets, a vector minus the English default's.
It reports everything at slot 6, layer 25 and at slot 0, layer 25, with a
layer profile from 0 to 63.  Studies of multilingual models generally find
language identity strongest in early and late layers and weakest in the
middle, which this design can check for Qwen.  Each analysis is given for both
score-3 and filter-free vectors.

| # | comparison | answers |
|---|---|---|
| A1 | the size of the language move (NL minus E) against the median distance between two English nationality vectors (all 13 in the map) and against the language offset | is the language move bigger than the difference between peoples? |
| A2 | cosine of (NL minus E) with the language offset (C minus default) | does the move point along the language direction? |
| A3 | cosine of (NL minus C) with (E minus default), against the cosine between two different nationalities' English offsets | does the people signal survive inside the language? |
| A4 | nearest neighbour of each NL vector among the 13 English nationalities and the 5 controls, raw and with the language offset subtracted, plus the top 5 over the whole corpus | identified as its people or as its language? |
| A5 | CA's distance to French NL (same language) against its distance to Canadian E (same people), raw and offset-subtracted | the direct dissociation |
| A6 (b) | for each nationality: the instruction-language main effect, (NE minus EE) and (NL minus EL); the answer-language main effect, (EL minus EE) and (NL minus NE); the interaction; and EE against E, which should be close to zero | which language carries it, and per slot |
| A7 | projection of every arm on the main run's assistant axis | does a language shift alone move a persona toward or away from the Assistant? |
| J1 to J3 | score shares per arm, the language cue, and compliance with the answer language | the judge side |

Intervals are bootstrapped over the 100 questions.  With five nationalities,
A4 and A5 are counts and are reported as counts, not tests.

**How to read the result** (written down now, before the data):

| result | meaning | consequence |
|---|---|---|
| the language move is several times the people distances, NL sits nearest its control, CA sits nearest French NL, and after subtracting the offset all 5 are identified as their own people | language dominates, but additively | the 2026-10-08 decision holds; native instructions would need a correction and buy nothing |
| as above, but people are not recovered after subtraction | language dominates and interacts with the persona | the decision holds firmly |
| the language move is comparable to or smaller than the people distances, and NL sits nearest its own English file | people dominate | reopen the question for single-language nationalities (still not for the other half of the map) |
| (b) NE is about equal to EE at slot 6 and slot 0 | the instruction language leaves little trace when answers are English | "native instruction, English answer" becomes an option |

## 8. Build order

1. You decide 1 to 6.
2. The build script with its tests, the translations, and the review table.
   You read the table, plus the native-speaker spot check if decision 3 finds
   a reader.
3. The pre-check (about $2) with its readout.  An arm whose hosted score-3
   share is under about 10% is flagged, since 6% is the floor for 30 of 500.
4. The [run_pipeline.sh](../../pipeline/run_pipeline.sh) and
   [4_vectors.py](../../pipeline/4_vectors.py) flags and the boundary test,
   made in a worktree and merged once tested.
5. Pre-extraction checklist:
   [build_native_language_set.py](../../data_analysis/build_native_language_set.py)
   `--check` (not there yet) and the boundary test.
6. At the extraction (same session and commit): the side run, then
   `4_vectors.py --all_responses` on the side activations and on a scratch
   directory of symlinks to the six base activation files, then the pod-side
   `extract`, then the mirror.
7. The analysis and a readout.  The TRAITS_TO_ADD item then moves to
   TRAITS_ADDED with its result.
