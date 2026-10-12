# Gate 3: the base-model table's eligibility and `min_count`

Audit of gate 3 in [README.md](./README.md), written 2026-10-12 by an Opus agent following the README's
seven-step protocol.  Read-only: no code or data was changed, no paid call was made, nothing outside the
repository was read.  Run audited: the base-model pilot
[2026-10-12-pilot](../../../data/candidates/runs/base_model/2026-10-12-pilot/) (round 1, prompts version 1,
`Qwen/Qwen3-8B-Base`, 2,000 samples), its table
[candidate_table_round1.jsonl](../../../data/candidates/base_model/candidate_table_round1.jsonl) and
[stats_round1.json](../../../data/candidates/base_model/stats_round1.json), and the registry
[registry.jsonl](../../../data/candidates/registry.jsonl) as it stood at audit time (23,660 lines, 8,061 keys,
last row per key).

**Terms.**  M1 (the trait-hood filter), M3 (the novelty check) and the registry are defined in
[escalations.md § Terms](../escalations.md#terms).  The words below are used in this report only:

- **known**: the word already has a registry row proposed by another generator (censuses, Roget, WordNet
  clusters, IPIP, the alignment sweep, the antonym check, M1 validation), or is a corpus trait or queue stem.
  A known word the floor drops is **not lost**: the pipeline has it from elsewhere.
- **unique**: the base model is the only source; a unique word the floor drops is lost to the pipeline.
- **c1, c2–3, c4–7**: eligible rows with an emission count of 1, 2–3 and 4–7, the three strata of the
  88% the floor removed.  The **count** is the number of samples that emitted the word (a repeat inside one
  sample counts once).
- The agent's verdict codes, judged **against the intent** (is this a real trait association, as the corpus
  means a trait), not against the rule:
  **T** a trait word or trait phrase usable as a candidate label;
  **B** borderline (a skill, an AI capability, a word mostly said of other things);
  **t** trait content in an unusable form (a parse leak such as "be sarcastic", two traits joined by "and", a
  noun or adverb of a trait adjective that is itself in the table);
  **N** a description of a person that is not a trait (a passing state, a physical feature, a role, a slur);
  **J** junk (not a description of a person: biography fragments, verbs, sentence pieces).
  The **strict** rate counts T; the **loose** rate counts T and B.  Where a reference label exists (the M1
  verdict in the registry, or a corpus trait) it decides the code, and the agent's reading is noted beside it.

## Verdict in brief

1. **The count floor at 8 is mostly not doing what was intended, and it is fixable.**  It keeps trait words
   (4.9% of the 467 kept are not traits by M1), but it throws away about half of the eligible trait words
   (48% strict, 54% loose, of the 3,396 rows it removed), and almost all of the ones only the base model
   found: an estimated **≈ 300 (strict) to ≈ 520 (loose) trait words lost to the pipeline**, 62 of them
   counted one by one at counts 2–7.  What it kept is the TDA head the censuses had already sent: 450 of the
   467 rows merged into existing registry keys, and the run added **3** M3-new candidates.
2. **The count does track trait-hood** (and only weakly vocabulary frequency: Spearman ρ = 0.145 against
   Zipf), **but it tracks "already known" more strongly** (30% of c1 rows are known, 98% of kept rows) **and
   runs against novelty** (M3-new among trait words: 56% at count 1, 30% at count ≥ 8).
3. **The data support a floor of 2, not 8, at 2,000 samples.**  Junk falls fast with the count: 45% of
   the unique hapaxes (27 of 60 sampled), 23% of the unique rows at count 2 (31 of 134, all read), 9% at
   counts 3–7 (8 of 85, all read); 95% of the junk among the unique rows is hapaxes.  Lowering the pilot's
   floor to 2 adds 219 rows at about $1.75 batched and recovers 62 trait labels (94 with borderline ones).
   A "distinct seeds" floor is the count floor here (every sample draws its own seeds); distinct families
   adds little.
4. **The eligibility screens do what was intended but are stricter than the platform's own rule**:
   `unknown_word` and the Zipf floor bin 104 of the 189 ineligible rows that
   [decisions_m1.md](../../trait_gap_generation/decisions_m1.md) rule 1b sends to the probe, 26 of them
   trait words found nowhere else (39 such words among all 189).  The name-echo screen cost nothing (0 of 3 words are traits); the
   seed-echo screen cost nothing; the biography-span screen dropped 1 emission, unauditable by design.
5. **The value 8 has no recorded derivation**: the plan's default is 1 and its expected pilot submission
   600–1,000 rows.  The downstream estimate charges every selected row although M1 and M3 reuse earlier
   verdicts (it printed $3.74 for a real $0.14), and at count ≥ 1 it would have printed $30.90 against a real
   ≈ $10–15; that over-estimate may be what pushed the pilot to a high floor.

## 1. The rule, from the code

**Parsing and form** ([parse.py](../../../assistant_axis/gapgen/generators/base_model/parse.py)):

- `extract_items` (lines 121–155): the comma families (`list`, `person`, `occupation`, `contrast`) take the
  first line up to its first sentence end and split on commas, semicolons, "and", "but" and "&" (`_SPLIT`,
  line 51); `list_gloss` takes `word: gloss` lines; `ai_assistant` takes numbered lines (146–152) and does
  **not** split an item on "and", so "unresponsive and dismissive" stays one phrase.  A truncated
  continuation drops its last open span.
- `clean_span` (80–102): strips list markers, quotes, a trailing parenthetical; folds to ASCII lower case;
  strips leading `DETERMINERS` (31–32), `DEGREE_WORDS` (34–37) and `CONJUNCTIONS` (43); drops a span of more
  than `MAX_WORDS` = 4 words (30), any span holding a `CLAUSE_WORDS` entry (39–41), any non-letter token, and
  any span of stopwords only.  "be", "occasionally" and "etc" are in none of these lists.
- `normalize_form` (174–189): a single `-ness` / `-ity` noun becomes its adjective when OEWN has it
  (`_suffix_candidates`, 158–171, with `SUFFIX_EXCEPTIONS` 46–47); otherwise the tag is `adjective` if OEWN
  has the adjective, `noun` if OEWN has the noun, and **`adjective` for anything else** (line 189), so verbs
  and adverbs are tagged adjectives (the `Lexicon`, 66–70, holds only adjectives and nouns).  **The form tag
  gates nothing**: neither `_row` nor `select_rows` reads it.  On this table the suffix rule fired once
  (`banality` → `banal`).

**Echo screens and eligibility** ([table.py](../../../assistant_axis/gapgen/generators/base_model/table.py)),
per emitted item in sample order:

- seed echo (157–160): the item is one of the sample's own seed words → dropped, counted `n_seed_echo`;
- name echo (161–165), `person` family only: a single word matching a word of the person's name → dropped,
  counted `n_name_echo`, the word logged in `name_echo_words`;
- biography span (166–169): a multiword item found verbatim in the biography → dropped, counted
  `n_bio_span_echo`, never logged (CC BY-SA prose);
- malformed (170–175) and a repeat inside the same sample (176–178) → not counted again;
- per row (`_row`, 216–245): `unknown` (219) when any content word has Zipf ≤ 0 and is not in OEWN →
  ineligible `unknown_word`; else `freq_hard_reject` from `zipf_info(a.surface)` (220) → ineligible
  `below_hard_reject`; else eligible.  Two details matter in § 5: `unknown_word` is decided **before** the
  frequency rescue is consulted, and `zipf_info` is called **without** `gloss_hint`, although the row's own
  OEWN gloss hint is computed three lines later (222–223, 243).

**Selection** ([submit.py](../../../assistant_axis/gapgen/generators/base_model/submit.py)):
`select_rows` (99–105) keeps rows with `eligible` and `count >= min_count`, by rank.  `min_count` defaults to
1 in `select_rows` (99), `run_submit` (195) and the CLI
([base_model_generator.py](../../../data_analysis/gap_generation/base_model_generator.py):641); the pilot ran
with **8** ([run.json](../../../data/candidates/runs/base_model/2026-10-12-pilot/run.json), `args.min_count`).
`run_submit` (205–206) then refuses while a selected row has an unsettled gloss sense.

**What happens to a failing candidate.**  An echo never becomes a row.  An ineligible row stays in the
tracked table with its `ineligible_reason`.  A row below the floor stays in the table marked `eligible: true`
and never reaches the registry: there is no holding list, no probe and no later pass.  For all three the drop
is final unless someone resubmits the table.

**The gloss-sense screen** ([sense.py](../../../assistant_axis/gapgen/generators/base_model/sense.py),
`DIVERGENCE_COSINE` = 0.60 at line 66) re-asks; it discards nothing.  Its numbers are in § 9.

## 2. The intent

- Plan 03 § 3, step 5 ([03_base_model_generator.md](../../trait_gap_generation/03_base_model_generator.md)):
  "**Dedupe:** exact after normalisation; count frequency per candidate (frequency is itself a signal: very
  common = probably already in our set or a Big-Five cliché)."  Step 6, the vocabulary filter: "keep if in
  Condon list, WordNet, or every token has SUBTLEX frequency above a threshold; drop otherwise or mark
  'rare'."  § 4 names what the prompt families are for: the random-person and AI-context families "partly
  correct" the under-production of "multiword modern labels", "AI-assistant-specific dispositions, and
  anything with no corpus footprint"; the contrast family gives "antonym candidates for free".
- The coding plan ([coding_plan_03_base_model.md](../../trait_gap_generation/coding_plan_03_base_model.md))
  § 7: `submit --run-id R [--min-count 1]`; § 10: the pilot submit is "expected 600-1,000 eligible uniques";
  § 10 (f): Roger decides "whether emission count should keep driving rank".  § 6: "the flags come from
  `zipf_info`, never a literal" (the platform's floor and its rescue rule).
- [decisions_m1.md](../../trait_gap_generation/decisions_m1.md) rule 1b (Roger: "Approved, all three"): a
  word below the floor "goes to the probe instead of the bin" when it is formed by a negating prefix from a
  word at or above the floor, or "arrives with a gloss hint, that is, the generator says which sense it
  means", or comes from a curated source.  "The floor is there to stop dictionary junk."
- [QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md) 54: the name and span rules are leakage screens; the
  name rule's cost is "invisible while it shares a counter", so the run reports the words it lost.
  QUESTIONS 61: the per-family readout is the within-run control for the lower-cased biography prompts.

The README's gloss of the floor's intent, "a word the base model emits often enough is a real association;
hapaxes are noise", appears in neither plan; the plan reads frequency the other way round (very common means
probably covered).  **No derivation for the value 8 is recorded** anywhere searched: the plans, QUESTIONS,
[escalations.md](../escalations.md), the commit messages, and the run's own records, where it appears only as
an argument.  This report judges the floor against both readings: is a dropped row noise, and is it a word the
generator was meant to find.

## 3. The recorded discard, reproduced

Reproduced from the table, [table_counts.json](../../../data/candidates/cache/base_model/round1/table_counts.json)
and the registry, not copied:

| step | items | removed |
|---|---|---|
| raw items parsed from 2,000 samples | 22,151 | |
| seed echo | | 270 |
| name echo | | 3 (aziz, hakeem, jeffries) |
| biography span | | 1 |
| repeat inside a sample | | 3,958 |
| emissions into rows (sum of counts) | 17,919 | |
| distinct rows (uniques) | 4,052 | |
| `unknown_word` | | 122 rows |
| `below_hard_reject` | | 67 rows |
| eligible | 3,863 | |
| **count < 8** | | **3,396 rows (87.9% of eligible)** |
| submitted | 467 | |

By stratum, with the reference labels the registry holds:

| rows | n | emissions | known | unique | in TDA | corpus trait | median Zipf | M1 on known rows: trait / tagged / reject |
|---|---|---|---|---|---|---|---|---|
| kept (≥ 8) | 467 | 11,723 | 457 | 10 | 437 (94%) | 190 | 3.60 | 444 / 21 / 2 (all 467) |
| c4–7 | 409 | 2,084 | 368 | 41 | 320 (78%) | 77 | 3.27 | 256 / 30 / 4 |
| c2–3 | 678 | 1,599 | 500 | 178 | 361 (53%) | 81 | 3.17 | 350 / 61 / 7 |
| c1 | 2,309 | 2,309 | 702 | 1,607 | 376 (16%) | 66 | 3.50 | 475 / 119 / 39 |
| `unknown_word` | 122 | 129 | 10 | 112 | 10 | 1 | 0.00 | 10 / 0 / 0 |
| `below_hard_reject` | 67 | 75 | 13 | 54 | 11 | 0 | 1.22 | 12 / 0 / 1 |

What the kept 467 bought ([submit_report.json](../../../data/candidates/runs/base_model/2026-10-12-pilot/submit_report.json)):
450 merged into existing keys and **17 new keys**; M1 judged 18 rows ($0.0613,
[summary.json](../../../data/candidates/filter/2026-10-12-pilot_base_model/summary.json)) and M3 decided 17
($0.0828, [summary.json](../../../data/candidates/novelty/2026-10-12-pilot_base_model/summary.json)); every
other verdict the readout reports was made earlier for another generator's key.  Of the 17 new keys, seven are
corpus traits ([focused](../../../data/traits/instructions/focused.json),
[uncaring](../../../data/traits/instructions/uncaring.json),
[proactive](../../../data/traits/instructions/proactive.json),
[unflappable](../../../data/traits/instructions/unflappable.json),
[detail-oriented](../../../data/traits/instructions/detail_oriented.json),
[collaborative](../../../data/traits/instructions/collaborative.json),
[inclusive](../../../data/traits/instructions/inclusive.json)), `etc` was rejected, six were covered
(hard-working by [industrious](../../../data/traits/instructions/industrious.json), empathy by
[compassionate](../../../data/traits/instructions/compassionate.json), inspiring by
[encouraging](../../../data/traits/instructions/encouraging.json), fun by
[playful](../../../data/traits/instructions/playful.json), self-motivated by
[proactive](../../../data/traits/instructions/proactive.json), goal-oriented by purposive), and **three were
M3-new: detailed, team player, unctuous**.  The readout's "useful (M3 new or pair completion) 149, 757.1 per
dollar" in [report.md](../../../data/candidates/runs/base_model/2026-10-12-pilot/report.md) counts decisions
made for census keys; the run's own marginal yield is those three.

Roger's spot-check file [roger_sample.md](../../../data/candidates/runs/base_model/2026-10-12-pilot/roger_sample.md)
has no marks yet, and it samples submitted rows only, so it cannot measure what the floor dropped.

## 4. Does the count track trait-hood, or only vocabulary frequency?

| count | rows | known | in TDA | trait share, reference (known rows: M1 trait or corpus) | trait share, agent (unique rows: strict / loose) | junk (J), agent, unique rows | M3-new among M1-trait known rows |
|---|---|---|---|---|---|---|---|
| ≥ 8 | 467 | 98% | 94% | 95% (444 / 467) | 10 unique rows: 9 trait by M1, 3 M3-new | 1 / 10 (`etc`) | 30% (129 / 428) |
| 4–7 | 409 | 90% | 78% | 90% (333 / 368) | 25 / 41, 30 / 41 (all read) | 2 / 41 | 42% (135 / 324) |
| 2–3 | 678 | 74% | 53% | 86% (431 / 500) | 46 / 178, 74 / 178 (all read) | 37 / 178 | 52% (212 / 407) |
| 1 | 2,309 | 30% | 16% | 77% (541 / 702) | 9 / 60, 16 / 60 (sampled) | 27 / 60 | 56% (290 / 519) |

Read across, the count does three things at once:

- **It tracks trait-hood.**  The trait share rises with the count in both the reference-labelled rows and
  the agent's reading of the unique rows, and the junk is concentrated in the hapaxes (about 720 of the
  ≈ 760 junk rows among the unique rows).
- **It is only weakly vocabulary frequency.**  Over the 3,104 eligible single words, Spearman ρ(count,
  Zipf) = 0.145.  Within each count band the trait share *falls* as Zipf rises (reference-labelled single
  words; trait share, with the number of rows):

  | count | Zipf < 2.5 | 2.5–3.5 | 3.5–4.5 | ≥ 4.5 |
  |---|---|---|---|---|
  | 1 | 91% (139) | 73% (304) | 75% (166) | 62% (73) |
  | 2–3 | 94% (81) | 86% (224) | 86% (118) | 59% (63) |
  | 4–7 | 98% (59) | 91% (150) | 89% (105) | 76% (49) |
  | 8–19 | 100% (23) | 97% (118) | 91% (88) | 91% (32) |
  | ≥ 20 | 100% (2) | 98% (56) | 97% (94) | 88% (34) |

  The words the model emits once that are least trait-like are the common ones (`good`, `lower`, `state`);
  a rare dictionary word the model emits once is usually a trait word.
- **It tracks "already known" more strongly than trait-hood, and runs against novelty.**  A high count marks
  the model's stock trait vocabulary, which is the TDA list the censuses already sent (94% of kept rows are
  TDA words, 16% of hapaxes).  Among trait words, the M3-new share falls from 56% at count 1 to 30% at
  count ≥ 8.  The floor therefore selects for exactly the words the pipeline already has.

**The count also tracks the family**, which says nothing about trait-hood.  Items per sample differ 25-fold
(`list` 26.1, `occupation` 14.5, `person` 14.7, `list_gloss` 5.9, `ai_assistant` 4.1, `contrast` 1.07), and
the highest count any single-family row reaches is 2 for `contrast`, 4 for `list_gloss`, `occupation` and
`person`, 9 for `list` and 11 for `ai_assistant`.  At count ≥ 8 the floor kept 1 of the 462 rows only the
`ai_assistant` family emitted (`adaptive`) and none of the 150 only `contrast` emitted, and it removed 322 of
the 324 eligible nouns.  So the per-family numbers QUESTIONS 61 and plan 03 § 9.2 ask for (the
`ai_assistant` in-or-out call), and the noun share of M1 survivors that gates task 11 (0.4% in the
readout), are measured on words other families also emitted, not on what each family contributes.

## 5. Rates

All verdicts not marked as reference are the agent's reading.  Intervals are 95% Wilson binomial intervals.

**False negatives of the floor** (discarded, but a trait word):

- On the read sample of 105 floored rows (Appendix A): strict 36 / 105 = 34.3% [25.9, 43.8], loose
  48 / 105 = 45.7% [36.5, 55.2].  The sample over-represents unique hapaxes on purpose.
- Because the sample's unique strata at counts 2–7 were small (12 and 10 rows), **all 219 unique rows at
  counts 2–7 were then read** (Appendix B): 71 are trait words or trait phrases (39 of 85 at counts 3–7,
  45.9% [35.7, 56.4]; 32 of 134 at count 2, 23.9% [17.5, 31.8]).  Eight are spelling variants of words the
  registry has (good-humoured, co-operative, judgemental, organised, straight-forward, unshakeable,
  self-centred, over-anxious) and two are one word split by spelling (well-organised 3, well-organized 2), so
  **62 trait labels at counts 2–7 are lost outright**: hyperactive, overprotective,
  free-spirited, likable, uninvolved, ineffectual, fun-loving, choleric, puerile, untrusting, upbeat,
  weak-willed, mealy-mouthed, warmhearted, no-nonsense, smarmy, well-meaning, braggart, pessimist, snob,
  hypocrite, self-obsessed, duplicitous, dilatory, insouciant, peremptory, bumptious, coachable and others
  (four of the 62 are corpus roles, Appendix B).
  Under the count floor's own logic these are "real associations": each came from two to seven independent
  seed draws.  The census agrees with the sample (c2–3: 3 / 12 sampled, 46 / 178 counted; c4–7: 5 / 10
  sampled, 25 / 41 counted).
- Weighted to the population (reference rates on the 1,570 known rows, the census on the 219 unique rows at
  counts 2–7, the sample's rate on the 1,607 unique hapaxes): **≈ 1,617 of 3,396 (48%) strict, ≈ 1,838
  (54%) loose**.
- **Lost to the pipeline** (unique rows only), the floor's real cost: c1 1,607 × 9/60 ≈ 241 [130, 419];
  c2–3 39 and c4–7 23 by count, net of the spelling variants; **≈ 303 strict [192, 481], ≈ 522 loose
  [369, 721]**, the interval from the hapax sample alone.

**False positives of the floor** (kept, but not a trait word): M1 on all 467 kept rows, 23 not trait (2 reject,
21 tagged) = **4.9% [3.3, 7.3], 15–34 rows**.  On the sample of 45: 2 / 45 = 4.4% [1.2, 14.8] by reference
(`etc`, a list-ending "etc." that is not a stopword; `miserable`, a state); the agent would add `fast`
(3 / 45 = 6.7% [2.3, 17.9]).

**The ineligibility rules** (`unknown_word`, `below_hard_reject`):

- Sample of 15 + 15 (Appendix A): `unknown_word` 2 T, 2 B, 10 J (three of them concatenated name tokens
  such as azizabdulaziz, name echoes the name rule missed and `unknown_word` caught); `below_hard_reject` 2 T,
  4 t, 3 B, 5 J.
- All 189 were then read (Appendix C): **37 of 122 `unknown_word` rows (30%) and 22 of 67
  `below_hard_reject` rows (33%) are trait words; 28 and 11 of them are found nowhere else**, mostly
  negations the model coined (unempathetic, unopinionated, unsnobbish, unsycophantic, uncircumspect,
  undecisive) and closed compounds that `wordfreq` knows only hyphenated (hardhearted, coolheaded).
- **The table is stricter than rule 1b.**  Run through `zipf_info` locally (wordfreq, no call), 52 of the
  122 `unknown_word` rows qualify for the negating-prefix rescue, among them `uncalculating`, the decision's
  own worked example, and 52 of the 67 `below_hard_reject` rows carry an OEWN gloss hint and would go to the
  probe under route 2, as M1 itself does ([filter.py](../../../assistant_axis/gapgen/filter.py):264 passes
  `gloss_hint=bool(it.intended_sense)`).  That is 104 of 189 rows binned that the platform's decided rule
  would probe.  None of them reached count 8, so in the pilot the floor masked this; under a lower floor it
  matters.

**The echo screens:**

- Name echo: 3 emissions, 3 words, all names (aziz, hakeem, jeffries); **0 trait words lost**, which closes
  QUESTIONS 54's whitelist with evidence for this run.
- Biography span: 1 emission; the span is never logged, by design, so it cannot be audited.  At most one
  phrase.
- Seed echo: 270 emissions of 101 words; 31 words never reached the table, and none is lost to the pipeline:
  16 are TDA words already in the registry from the censuses (dauntless, frightenable, overtrusting,
  uncompanionable and others), 15 are OEWN nouns or names from the prompts' noun seeds (boulder, newton).

## 6. Would a different floor do better?

At the pilot's 2,000 samples, the same table under other floors.  "New" means unique to the base model.
Trait words at counts 2–7 are counted (Appendix B, net of the spelling variants; strict, then with
borderline rows); at count 1 they are the sample's rates.  Cost is the code's own batched rate per new row, M1
$0.0036 plus M3 $0.0055 at an 80% pass rate, about $0.008; rows already judged are free, because M1 and M3
reuse their verdicts (§ 3).

| floor | rows sent | new rows | trait words among the new (strict / with B) | junk among the new (agent) | added cost over ≥ 8, batched |
|---|---|---|---|---|---|
| ≥ 8 (pilot) | 467 | 10 | 9 trait by M1; 3 M3-new | 1 | (actual: $0.14 for M1 and M3) |
| ≥ 5 | 715 | 30 | + 13 / + 14 | + 1 | ≈ $0.16 |
| ≥ 4 | 876 | 51 | + 23 / + 28 | + 2 | ≈ $0.33 |
| ≥ 3 | 1,119 | 95 | + 35 / + 48 | + 8 | ≈ $0.68 |
| **≥ 2** | 1,554 | 229 | **+ 62 / + 94** | + 39 | **≈ $1.75** |
| ≥ 1 | 3,863 | 1,836 | ≈ + 300 / ≈ + 520 | ≈ + 760 | ≈ $10–15 |

**Floor of 2 at this sample size** is where the data point.  Junk falls fast with the count (45% of the
unique hapaxes [33.1, 57.5], 23% at count 2 [16.8, 31.0], 9% at counts 3–7 [4.8, 17.5]); a floor of 2 removes
about 720 of the ≈ 760 junk rows among the unique rows and keeps the 2–7 band, a third of whose unique rows are
trait labels (71 of 219, 32.4% [26.6, 38.9]).  Count 1 still holds the largest pool of lost trait words
(≈ 240–430 among 1,607), but at a 15–27% density, beside ≈ 720 junk rows; whether to send it depends on how well
M1 rejects that junk, which nothing has measured (proposal 2).  A floor of 3 is the conservative alternative:
it sends a fifth of the junk (8 rows instead of 39) and gives up 27 of the 62 recovered labels.

**A floor on distinct seeds** is the count floor in this design: 2,000 samples drew 2,000 distinct seed sets
and rendered 2,000 distinct prompts, so a word's count already is its number of independent seed draws.  The
nearest independent measure is the **number of families** that emitted the word.  On reference-labelled rows
at counts 2–3 the trait share is 79% for one family, 88% for two, 96% for three or more; at counts 4–7 it is
flat (100% of 9, 88%, 92%).  A "two families" rule at counts 2–3 would drop 200 rows whose trait share is still
79%: it buys little.  A family-aware floor matters more the other way: one count floor cannot suit a family
that emits one item a sample and one that emits twenty-six.

**Dependence on the sample size.**  An absolute count means a different rate at every sample size: 8 at 2,000
samples is 4 per 1,000; carried unchanged to the 20,000-sample full run it is 0.4 per 1,000, a much looser gate.
Scaled in proportion (80 at 20k) it would keep only the head again.  What the floor is for, separating
emissions that recur from ones that do not, is done best by a **small absolute floor** (2 or 3), whose cost in
recall falls as the run grows: a real word with a rate of one in 2,000 samples has an expected count of 1 here
and 10 at 20k.  Any floor should be recorded with the sample size and families it was set for.

## 7. Verdict

- **The count floor at 8: mostly not doing what was intended — fixable.**  Read as "hapaxes are noise", it
  overshoots: hapaxes are mostly noise, but counts 2–7 are not, and the floor removed them too.  Read as the
  plan's own intent for the generator, words other sources lack (multiword labels, AI-assistant dispositions,
  contrast pairs), it removes almost exactly that and keeps the census head: 3 new candidates for the run.
  The value is not supported by the data and was never derived.  It should depend on the sample size (as an
  absolute floor stated with its N, kept small) and on the family (or be replaced by M1, which is the
  trait-hood gate and costs a third of a cent a row).  Expected change at a floor of 2: false negatives lost to
  the pipeline fall from ≈ 303 to ≈ 241 (all of them hapaxes); the junk sent rises from 1 row to about 40,
  which M1 must reject (at a floor of 3, about 9).
- **The eligibility rules: doing what was intended but improvable.**  They remove mostly non-traits (130 of
  the 189 ineligible rows, 69%, are not trait words by the agent's reading; false-negative rate 31%
  [25.0, 38.1], 59 rows, 39 of them found nowhere else).  But they bin 104 rows the platform's rule 1b would
  probe, 26 trait words found nowhere else among them; following rule 1b moves those to M1's probe at about a
  fifth of a cent each.  Their false positives, junk that passes them, are about 21% of the eligible rows
  (≈ 815: the agent's junk rate on the unique rows plus M1's rejects on the known ones), nearly all of them
  unique hapaxes, which is why the floor or M1 must catch them.
- **The echo screens: doing what was intended, about as well as possible.**  0 trait words lost to the name
  rule or the seed rule; the span rule's one emission is unauditable by design.
- **The form tag and the noun rule** gate nothing; they mislabel verbs and adverbs as adjectives (41 `-ly`
  adverbs, verbs such as revile, protect, dishearten), and the noun rule converted one word.  Their reported
  numbers (noun share of M1 survivors 0.4%) are artifacts of the floor.

## 8. Proposals

Each with its cost and the evidence that would settle it.

1. **Resubmit the pilot table at `--min-count 2`** (≈ $1.75 batched, under the $20 line; `submit --dry-run`
   first).  219 new rows.  Settles: M1 and M3 on them, scored against Appendix B, where every one of the 219
   is labelled: this report predicts 62 trait labels (94 with borderline ones) and 39 junk rows, so the batch
   doubles as a measurement of M1 on this generator's junk.
2. **Measure M1 on hapax junk before deciding count 1** (≈ $0.25–0.50).  Send the 60 unique hapaxes of
   Appendix A, already labelled here, through the split M1 as a validation batch outside the registry.  If M1
   passes at most about 10% of the 37 J and N rows, send all 1,607 unique hapaxes (≈ $10–15 batched, ≈ 240–430
   trait words); if not, keep the floor at 2 and add the free pre-filter of proposal 4 first.
3. **Make the table's eligibility follow rule 1b** ($0, code): pass `gloss_hint=bool(hint)` to `zipf_info` in
   `table._row`, and let an unknown un- / in- / non- coinage take the negating-prefix rescue before the
   `unknown_word` bin.  104 rows to the probe (≈ $0.20 at a fifth of a cent each, plus full M1 on those it
   passes), 26 trait words found nowhere else among them, unsycophantic and unopinionated included.
   Settles: the probe's verdicts on those rows.  The same pattern
   (`zipf_info(surface)` with no gloss hint) is in the Roget and WordNet harvests
   ([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):185,
   [wn_clusters.py](../../../assistant_axis/gapgen/generators/roget/wn_clusters.py):260), which gate 2's
   report ([roget_wordnet_selection.md](./roget_wordnet_selection.md)) may want to check.
4. **Parse fixes** ($0, code, tests): add `etc` and `others` to the stoplist (`etc` was kept at count 16 and
   cost an M1 call); strip a leading `be` and frequency adverbs such as `occasionally` (not `not`, `never` or
   `overly`, which carry meaning; 129 eligible rows open with `be`, `not`, `never` or an adverb such as
   `occasionally`, `highly` or `overly`); split `ai_assistant` items on "and"
   (35 compound rows); fold `-ly` adverbs to the OEWN adjective (41 rows); extend the noun rule to `-ence` /
   `-ance` → `-ent` / `-ant`, `-acity` → `-acious`, `-ism` → `-istic` where OEWN has the adjective (about 22
   rows: patience, resilience, perseverance, pugnacity, optimism); tag OEWN verb-only words `verb`; fold
   British spellings to US as the [entity-naming rule](../../../.claude/rules/entity-naming.md) asks
   (eight spelling variants of registry words in the 2–7 band alone, such as judgemental, organised,
   good-humoured, self-centred and co-operative, plus well-organised beside well-organized; Appendix B).  Expected change: one false positive fewer, a few dozen rows merged into their adjective rows
   (raising those rows' counts, which matters while any floor exists).
5. **Record the floor** ($0): put `min_count` and its reason in the run's [run.json](../../../data/candidates/runs/base_model/2026-10-12-pilot/run.json) args and in the coding plan, stated with
   the sample size; do not carry 8 to the 20k run.
6. **Correct the downstream estimate** ($0, code): charge only rows whose key has no current M1 or M3
   decision.  It printed $3.74 for a real $0.14 here, and at count ≥ 1 it would print $30.90, over the $20
   line, against a real ≈ $10–15.
7. **Correct the readout** ($0): report useful-per-dollar and M3-new on the keys the run added, and report the
   noun share and the per-family table (QUESTIONS 61, plan 03 § 9.2 and § 9.4) on the eligible table as well as
   on the submitted rows, so the `ai_assistant` and noun-normalization decisions are made on what each family
   produced.

## 9. The gloss-sense screen (a re-ask; numbers only)

From [stats_round1.json](../../../data/candidates/base_model/stats_round1.json) and
[run.json](../../../data/candidates/runs/base_model/2026-10-12-pilot/run.json): over the whole table, 965 rows
carried both an OEWN gloss and the model's own; the cosine screen (EmbeddingGemma, floor 0.60, provisional)
called 146 divergent (15.1%), cosine minimum 0.30, median 0.76; one Haiku 5.5 call each settled 124 for the
sample's reading and 22 for the dictionary's, with 1 sample gloss illegible, 0 failed, 0 unresolved.  Among
the 467 submitted: 336 two-sided, 44 divergent (13.1%), 35 sample, 9 dictionary, cosine minimum 0.42, median
0.76.  Cost $0.0528 over 395 calls
([gloss_sense_usage.json](../../../data/candidates/cache/base_model/round1/gloss_sense_usage.json), cumulative
over the step's runs: [gloss_sense_responses.jsonl](../../../data/candidates/cache/base_model/round1/gloss_sense_responses.jsonl)
holds 191 answers at prompt version 1 and 146 at version 2).  Because the screen covered the whole table, a
lower floor adds no gloss-sense cost.

## Appendix A: the sample, in full

**Selection.**  Pools: the floored rows by stratum (c1, c2–3, c4–7), each split into known and unique; the
ineligible rows by reason; the kept rows.  Each pool sorted by rank, then drawn with
`random.Random(20261012).sample`, one generator consumed in this order: c1 / unique 30, c1 / known 10, c2–3 /
unique 12, c2–3 / known 8, c4–7 / unique 10, c4–7 / known 5, `unknown_word` 15, `below_hard_reject` 15,
kept 45.  A second draw of 30 from c1 / unique (the pool that decides the lost count), excluding the first,
with `random.Random(20261013)`.  Pool sizes: c1 / unique 1,607, c1 / known 702, c2–3 / unique 178, c2–3 /
known 500, c4–7 / unique 41, c4–7 / known 368, `unknown_word` 122, `below_hard_reject` 67, kept 467.  In all,
135 discarded rows and 45 kept ones.  "Reference" is the registry's M1 verdict (with tags) and M3 decision
(with the covering trait), or "corpus trait"; a blank means none exists.

#### c1 / unique, first draw (30 rows): T 6, B 3, t 3, N 5, J 13
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 1 | occasionally robotic | 1 | occupation | phrase | 3.54 |  | **t** | 'occasionally' is not in DEGREE_WORDS; the head 'robotic' is a manner word |
| 2 | resplendent | 1 | list_gloss | adjective | 2.67 |  | **N** | splendour of appearance (OEWN gloss) |
| 3 | be sarcastic | 1 | ai_assistant | phrase | 3.6 |  | **t** | 'be' not stripped (an ai_assistant line); the head [sarcastic](../../../data/traits/instructions/sarcastic.json) is a corpus trait |
| 4 | assembly | 1 | person | noun | 4.61 |  | **J** | biography noun (OEWN: machine parts) |
| 5 | state | 1 | person | noun | 5.78 |  | **J** | biography noun |
| 6 | not much good | 1 | occupation | phrase | 6.0 |  | **J** | sentence fragment |
| 7 | teary-eyed | 1 | person | adjective | 2.84 |  | **N** | a passing state |
| 8 | revile | 1 | person | adjective | 1.98 |  | **J** | a verb (OEWN gives only the verb) |
| 9 | unavenged | 1 | person | adjective | 1.4 |  | **J** | biography-primed; not said of character |
| 10 | become a pastry chef | 1 | contrast | phrase | 3.53 |  | **J** | a clause, not a description |
| 11 | shy in one-on-one situations | 1 | person | phrase | 4.16 |  | **T** | scoped shyness; covered in substance by [self_conscious](../../../data/traits/instructions/self_conscious.json) |
| 12 | good at delegating | 1 | list | phrase | 2.5 |  | **B** | a managerial skill rather than a disposition |
| 13 | evenly-paced | 1 | ai_assistant | adjective | 3.56 |  | **B** | pace of talk, said of the assistant |
| 14 | dextrous | 1 | occupation | adjective | 1.83 |  | **N** | physical skill (OEWN) |
| 15 | low-keyed | 1 | list | adjective | 2.89 |  | **T** | restrained (OEWN); near [laid_back](../../../data/traits/instructions/laid_back.json) |
| 16 | expert on cigars | 1 | ai_assistant | phrase | 3.37 |  | **J** | topic knowledge |
| 17 | disreputable | 1 | occupation | adjective | 2.47 |  | **T** | lacking respectability in character (OEWN) |
| 18 | patient listener | 1 | ai_assistant | phrase | 3.52 |  | **T** | trait phrase; head [patient](../../../data/traits/instructions/patient.json) |
| 19 | nonplussed | 1 | person | adjective | 2.12 |  | **N** | a passing state (OEWN: bewilderment) |
| 20 | good liar | 1 | person | phrase | 4.02 |  | **B** | a skill at deceit; near [deceitful](../../../data/traits/instructions/deceitful.json) |
| 21 | unruffled | 1 | list_gloss | adjective | 2.08 |  | **T** | composure (OEWN and the model's gloss) |
| 22 | master | 1 | occupation | adjective | 4.93 |  | **J** | OEWN 'most important element'; not a description |
| 23 | well trained dog | 1 | occupation | phrase | 4.58 |  | **J** | not a person |
| 24 | not functioning properly | 1 | ai_assistant | phrase | 4.02 |  | **J** | device state |
| 25 | malfunctioning | 1 | ai_assistant | adjective | 2.94 |  | **J** | device state |
| 26 | junior-championships | 1 | person | adjective | 4.03 |  | **J** | biography fragment |
| 27 | slut | 1 | person | noun | 3.76 |  | **N** | a slur for a person, not a trait label |
| 28 | straight shooter | 1 | person | phrase | 4.05 |  | **T** | frank and honest person (OEWN noun sense) |
| 29 | not available to | 1 | ai_assistant | phrase | 5.28 |  | **J** | fragment |
| 30 | unresponsive and dismissive | 1 | ai_assistant | phrase | 2.99 |  | **t** | two traits; ai_assistant items are not split on 'and' |

#### c1 / unique, second draw (30 rows): T 3, B 4, t 4, N 5, J 14
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 31 | ruthless gang leader | 1 | contrast | phrase | 3.65 |  | **t** | a role around the trait head 'ruthless' |
| 32 | immune to mental illness | 1 | ai_assistant | phrase | 4.14 |  | **J** | a capability claim about the AI |
| 33 | good worker | 1 | occupation | phrase | 4.43 |  | **B** | generic praise; near [industrious](../../../data/traits/instructions/industrious.json) |
| 34 | poor teacher | 1 | person | phrase | 4.88 |  | **N** | a role evaluation |
| 35 | ticked off | 1 | list | phrase | 3.06 |  | **N** | a passing state |
| 36 | global perspective | 1 | ai_assistant | phrase | 4.56 |  | **N** | an AI capability |
| 37 | unseasoned | 1 | occupation | adjective | 2.03 |  | **B** | inexperienced: experience, not disposition |
| 38 | lower | 1 | occupation | adjective | 5.11 |  | **J** | comparative fragment |
| 39 | great storyteller | 1 | person | phrase | 3.08 |  | **B** | a skill |
| 40 | incompetently | 1 | person | adjective | 1.77 |  | **t** | adverb of [incompetent](../../../data/traits/instructions/incompetent.json) |
| 41 | oratory | 1 | occupation | noun | 2.94 |  | **J** | an activity noun |
| 42 | chief of naval operations | 1 | person | phrase | 4.24 |  | **J** | biography office |
| 43 | bit of a recluse | 1 | person | phrase | 2.92 |  | **T** | reclusive, as a phrase |
| 44 | never at her job | 1 | contrast | phrase | 5.5 |  | **J** | fragment |
| 45 | propitiated | 1 | list | adjective | 1.55 |  | **J** | a verb form |
| 46 | precarious | 1 | list | adjective | 3.27 |  | **J** | said of situations |
| 47 | self-control | 1 | ai_assistant | noun | 5.25 |  | **t** | noun of self-controlled (near the corpus's [self_disciplined](../../../data/traits/instructions/self_disciplined.json)) |
| 48 | tattling | 1 | person | adjective | 1.83 |  | **T** | OEWN: prone to communicate confidential information |
| 49 | symbolic | 1 | person | adjective | 3.86 |  | **J** | not a person description |
| 50 | protect | 1 | ai_assistant | adjective | 4.92 |  | **J** | a verb |
| 51 | sport-division | 1 | person | adjective | 4.73 |  | **J** | biography fragment |
| 52 | long-lived | 1 | person | adjective | 4.88 |  | **N** | physical |
| 53 | good at acting | 1 | person | phrase | 4.82 |  | **B** | a skill |
| 54 | dishearten | 1 | list | adjective | 1.63 |  | **J** | a verb |
| 55 | market-driven | 1 | occupation | adjective | 4.54 |  | **J** | said of firms |
| 56 | [daredevil](../../../data/roles/instructions/daredevil.json) | 1 | person | adjective | 3.29 |  | **T** | OEWN: presumptuously daring; a corpus role |
| 57 | shiver | 1 | person | noun | 3.05 |  | **J** | a reflex |
| 58 | great eater | 1 | contrast | phrase | 3.42 |  | **N** | a habit, not a trait label |
| 59 | not able to | 1 | ai_assistant | phrase | 5.43 |  | **J** | fragment |
| 60 | considerate and thoughtful | 1 | ai_assistant | phrase | 3.3 |  | **t** | two traits; ai_assistant items are not split on 'and' |

#### c1 / known (10 rows): T 7, N 2, J 1
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 61 | scornful | 1 | list_gloss | adjective | 2.29 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 62 | disgusted | 1 | list | adjective | 3.57 | M1 tagged[state]; M3 - | **N** | ref M1 tagged state; agree |
| 63 | unwholesome | 1 | person | adjective | 2.14 | M1 trait; M3 new | **T** | ref M1 trait; agree (moral sense) |
| 64 | malignant | 1 | person | adjective | 3.33 | M1 trait; M3 new | **T** | ref M1 trait; agree (malevolent sense) |
| 65 | [child](../../../data/roles/instructions/child.json) | 1 | person | noun | 5.3 | M1 tagged[role_person]; M3 - | **N** | ref M1 tagged role_person; agree |
| 66 | blustery | 1 | list | adjective | 2.47 | M1 trait; M3 new | **T** | ref M1 trait; mostly weather, agree only in the blustering-person sense |
| 67 | awry | 1 | list | adjective | 2.93 | M1 reject[stretched]; M3 - | **J** | ref M1 reject (stretched); agree |
| 68 | [insular](../../../data/traits/instructions/insular.json) | 1 | occupation | adjective | 3.03 | corpus trait | **T** | ref: corpus trait |
| 69 | unpretending | 1 | list | adjective | 0.0 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 70 | acrimonious | 1 | list | adjective | 2.55 | M1 trait; M3 new | **T** | ref M1 trait; agree |

#### c2–3 / unique (12 rows): T 3, B 3, t 2, N 4
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 71 | experimental | 3 | list, occupation, person | adjective | 4.28 |  | **B** | said of methods more than of people |
| 72 | fertile | 3 | list, list_gloss | adjective | 3.62 |  | **N** | biological |
| 73 | adept | 3 | ai_assistant, list | adjective | 3.33 |  | **B** | a skill |
| 74 | optimism | 3 | ai_assistant | noun | 3.66 |  | **t** | noun of [optimistic](../../../data/traits/instructions/optimistic.json) (count 86, kept) |
| 75 | underdeveloped | 2 | list, person | adjective | 2.99 |  | **N** | said of societies or bodies |
| 76 | no guilt | 2 | ai_assistant | phrase | 4.13 |  | **t** | remorseless, as a phrase |
| 77 | exasperating | 2 | person | adjective | 2.4 |  | **T** | an annoying manner |
| 78 | unmannerly | 2 | list, list_gloss | adjective | 1.3 |  | **T** | ill-mannered (OEWN); eligible through the negating-prefix rescue |
| 79 | feline | 2 | list, occupation | adjective | 3.12 |  | **N** | of cats; at most a manner |
| 80 | thief | 2 | ai_assistant, contrast | noun | 3.88 |  | **N** | a role noun |
| 81 | learning-capable | 2 | ai_assistant | adjective | 4.61 |  | **B** | an AI capability |
| 82 | man of few words | 2 | contrast, person | phrase | 5.25 |  | **T** | taciturn, as an idiom |

#### c2–3 / known (8 rows): T 7, N 1
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 83 | [superficial](../../../data/traits/instructions/superficial.json) | 3 | list, list_gloss, occupation | adjective | 3.56 | corpus trait | **T** | ref: corpus trait |
| 84 | dapper | 3 | list, occupation, person | adjective | 2.91 | M1 trait; M3 new | **T** | ref M1 trait; my reading: appearance, borderline |
| 85 | underhanded | 2 | list, occupation | adjective | 2.48 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 86 | shrill | 2 | list, occupation | adjective | 2.88 | M1 trait; M3 new | **T** | ref M1 trait; agree (manner) |
| 87 | bookish | 2 | list | adjective | 2.57 | M1 trait; M3 covered: [erudite](../../../data/traits/instructions/erudite.json) | **T** | ref M1 trait; agree |
| 88 | expert | 2 | list | adjective | 4.56 | M1 tagged[role_person]; M3 - | **N** | ref M1 tagged role_person; agree |
| 89 | recalcitrant | 2 | list, occupation | adjective | 2.55 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 90 | disdainful | 2 | ai_assistant, list | adjective | 2.35 | M1 trait; M3 new | **T** | ref M1 trait; agree |

#### c4–7 / unique (10 rows): T 5, B 2, t 1, N 1, J 1
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 91 | overprotective | 7 | list, list_gloss, person | adjective | 2.66 |  | **T** | OEWN and the model's gloss |
| 92 | free-spirited | 5 | list, occupation, person | adjective | 3.55 |  | **T** | a disposition |
| 93 | introvert | 5 | list, person | noun | 2.91 |  | **t** | noun of [introverted](../../../data/traits/instructions/introverted.json) (a corpus trait) |
| 94 | uncommitted | 5 | list, occupation, person | adjective | 2.38 |  | **B** | non-committal, or a state |
| 95 | good listener | 5 | list, occupation, person | phrase | 3.52 |  | **T** | trait phrase |
| 96 | above all | 5 | occupation, person | phrase | 5.2 |  | **J** | parse fragment |
| 97 | upbeat | 4 | list, person | adjective | 3.53 |  | **T** | OEWN: optimistic |
| 98 | unshaken | 4 | list, list_gloss, person | adjective | 1.89 |  | **B** | steadfast, or a state |
| 99 | no-nonsense | 4 | contrast, list, person | adjective | 4.21 |  | **T** | OEWN: not tolerating irrelevancies |
| 100 | frail | 4 | contrast, list, list_gloss | adjective | 3.28 |  | **N** | physical |

#### c4–7 / known (5 rows): T 5
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 101 | quarrelsome | 7 | list, occupation, person | adjective | 2.22 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 102 | contemplative | 7 | list, list_gloss, occupation, person | adjective | 2.89 | M1 trait; M3 covered: [meditative](../../../data/traits/instructions/meditative.json) | **T** | ref M1 trait; agree |
| 103 | monotonous | 5 | list, list_gloss, occupation, person | adjective | 2.95 | M1 trait; M3 new | **T** | ref M1 trait; agree (of a speaker) |
| 104 | [strategic](../../../data/traits/instructions/strategic.json) | 5 | ai_assistant, list, occupation, person | adjective | 4.43 | corpus trait | **T** | ref: corpus trait |
| 105 | droll | 4 | list, list_gloss | adjective | 2.58 | M1 trait; M3 covered: [wry](../../../data/traits/instructions/wry.json) | **T** | ref M1 trait; agree |

#### Ineligible, `unknown_word` (15 rows): T 2, B 2, N 1, J 10
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 106 | be unempathetic | 1 | ai_assistant | phrase | 0.0 |  | **T** | lacking empathy ('be' leak); unempathetic itself is `unknown_word` too |
| 107 | moustacheless | 1 | person | adjective | 0.0 |  | **N** | physical |
| 108 | azizabdulaziz | 1 | person | adjective | 0.0 |  | **J** | concatenated name tokens: a name echo the name rule missed |
| 109 | azizabdulazizabdulkadir | 1 | person | adjective | 0.0 |  | **J** | concatenated name tokens |
| 110 | azizabdulazizabdulakhirabdulkadir | 1 | person | adjective | 0.0 |  | **J** | concatenated name tokens |
| 111 | overelaborate | 1 | list | adjective | 0.0 |  | **B** | of style |
| 112 | illiterable | 1 | person | adjective | 0.0 |  | **J** | non-word |
| 113 | unheroical | 1 | occupation | adjective | 0.0 |  | **B** | nonce form of unheroic |
| 114 | undividedly | 1 | list | adjective | 0.0 |  | **J** | adverb non-word |
| 115 | untranscendable | 1 | occupation | adjective | 0.0 |  | **J** | non-word |
| 116 | unteachings | 1 | list | adjective | 0.0 |  | **J** | non-word |
| 117 | untirrable | 1 | list | adjective | 0.0 |  | **J** | non-word |
| 118 | unaccessed | 1 | person | adjective | 0.0 |  | **J** | non-word, not of persons |
| 119 | inefable | 1 | list | adjective | 0.0 |  | **J** | misspelt ineffable; not of persons |
| 120 | confrontive | 1 | list | adjective | 0.0 |  | **T** | variant of [confrontational](../../../data/traits/instructions/confrontational.json) (covered) |

#### Ineligible, `below_hard_reject` (15 rows): T 2, B 3, t 4, N 1, J 5
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 121 | hardhearted | 2 | list_gloss, occupation | adjective | 1.35 |  | **T** | OEWN 'lacking in feeling or pity'; low Zipf because usually hyphenated |
| 122 | placatory | 2 | person | adjective | 1.04 |  | **B** | OEWN: of acts |
| 123 | pietas | 1 | person | adjective | 1.43 |  | **J** | Latin |
| 124 | pugnacity | 1 | person | noun | 1.39 |  | **t** | noun of pugnacious (count 17, kept); `-acity` not in the suffix rule |
| 125 | muckrake | 1 | list | adjective | 0.0 |  | **J** | a verb |
| 126 | moustachioed | 1 | person | adjective | 1.37 |  | **N** | physical |
| 127 | bawdily | 1 | person | adjective | 0.0 |  | **t** | adverb of bawdy |
| 128 | underbred | 1 | list | adjective | 0.0 |  | **B** | OEWN '(of persons) lacking in refinement' |
| 129 | ramify | 1 | person | adjective | 1.18 |  | **J** | a verb |
| 130 | heedful | 1 | person | adjective | 1.14 | M1 trait; M3 new | **T** | ref M1 trait (censuses); agree |
| 131 | punctiliously | 1 | person | adjective | 1.37 |  | **t** | adverb of punctilious |
| 132 | repine | 1 | list_gloss | adjective | 1.07 |  | **J** | a verb |
| 133 | procrastinates | 1 | occupation | adjective | 1.39 |  | **t** | verb form of procrastinating |
| 134 | brawly | 1 | list | adjective | 1.12 |  | **J** | nonce |
| 135 | nescient | 1 | person | adjective | 0.0 |  | **B** | ignorant; rare |

#### Kept, count ≥ 8 (45 rows): T 43, N 1, J 1
| # | word | count | families | form | Zipf | reference | verdict | what it rests on |
|---|---|---|---|---|---|---|---|---|
| 136 | kind | 128 | ai_assistant, contrast, list, list_gloss, occupation, person | adjective | 5.45 | M1 trait; M3 covered: kind | **T** | ref M1 trait; agree |
| 137 | [creative](../../../data/traits/instructions/creative.json) | 112 | ai_assistant, list, list_gloss, occupation, person | adjective | 4.6 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 138 | sensitive | 103 | ai_assistant, list, list_gloss, occupation, person | adjective | 4.46 | M1 trait; M3 covered: [empathetic](../../../data/traits/instructions/empathetic.json) | **T** | ref M1 trait; agree |
| 139 | stubborn | 87 | ai_assistant, contrast, list, list_gloss, occupation, person | adjective | 3.76 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 140 | [polite](../../../data/traits/instructions/polite.json) | 69 | ai_assistant, contrast, list, list_gloss, occupation, person | adjective | 3.92 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 141 | attentive | 49 | ai_assistant, list, list_gloss, occupation, person | adjective | 3.3 | M1 trait; M3 covered: [observant](../../../data/traits/instructions/observant.json) | **T** | ref M1 trait; agree |
| 142 | careful | 45 | ai_assistant, list, list_gloss, occupation, person | adjective | 4.59 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 143 | persistent | 44 | ai_assistant, list, list_gloss, occupation, person | adjective | 3.9 | M1 trait; M3 covered: [persevering](../../../data/traits/instructions/persevering.json) | **T** | ref M1 trait; agree |
| 144 | [wise](../../../data/traits/instructions/wise.json) | 43 | ai_assistant, list, occupation, person | adjective | 4.51 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 145 | pleasant | 40 | list, list_gloss, occupation, person | adjective | 4.22 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 146 | [observant](../../../data/traits/instructions/observant.json) | 37 | ai_assistant, list, list_gloss, occupation, person | adjective | 3.05 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 147 | [adaptable](../../../data/traits/instructions/adaptable.json) | 36 | ai_assistant, list, occupation, person | adjective | 3.12 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 148 | [unassuming](../../../data/traits/instructions/unassuming.json) | 34 | ai_assistant, list, list_gloss, occupation, person | adjective | 2.82 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 149 | overbearing | 30 | ai_assistant, list, list_gloss, occupation, person | adjective | 2.91 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 150 | [adventurous](../../../data/traits/instructions/adventurous.json) | 30 | list, list_gloss, occupation, person | adjective | 3.48 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 151 | uncooperative | 29 | ai_assistant, list, list_gloss, occupation, person | adjective | 2.65 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 152 | suspicious | 27 | list, list_gloss, occupation, person | adjective | 4.09 | M1 trait; M3 covered: [paranoid](../../../data/traits/instructions/paranoid.json) | **T** | ref M1 trait; agree |
| 153 | self-righteous | 22 | list, list_gloss, occupation, person | adjective | 3.8 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 154 | argumentative | 20 | contrast, list, occupation, person | adjective | 2.89 | M1 trait; M3 covered: [confrontational](../../../data/traits/instructions/confrontational.json) | **T** | ref M1 trait; agree |
| 155 | rational | 18 | ai_assistant, contrast, list, list_gloss, person | adjective | 4.06 | M1 trait; M3 covered: rational | **T** | ref M1 trait; agree |
| 156 | sullen | 17 | list, list_gloss, occupation, person | adjective | 2.71 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 157 | pugnacious | 17 | list, list_gloss, occupation, person | adjective | 2.14 | M1 trait; M3 covered: [confrontational](../../../data/traits/instructions/confrontational.json) | **T** | ref M1 trait; agree |
| 158 | [self-effacing](../../../data/traits/instructions/self_effacing.json) | 16 | list, occupation, person | adjective | 2.28 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 159 | etc | 16 | list, occupation, person | adjective | 5.03 | M1 reject[no_persona_reading]; M3 - | **J** | ref M1 reject; a list-ending 'etc.' is not a stopword |
| 160 | [visionary](../../../data/roles/instructions/visionary.json) | 15 | contrast, list, occupation, person | adjective | 3.42 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 161 | resolute | 13 | ai_assistant, list, list_gloss, person | adjective | 3.12 | M1 trait; M3 covered: [persevering](../../../data/traits/instructions/persevering.json) | **T** | ref M1 trait; agree |
| 162 | reflective | 12 | ai_assistant, list, list_gloss, occupation, person | adjective | 3.58 | M1 trait; M3 covered: [introspective](../../../data/traits/instructions/introspective.json) | **T** | ref M1 trait; agree |
| 163 | miserable | 12 | list, list_gloss, occupation, person | adjective | 4.07 | M1 tagged[state]; M3 covered: [melancholic](../../../data/traits/instructions/melancholic.json) | **N** | ref M1 tagged state; agree |
| 164 | motivated | 12 | list, occupation, person | adjective | 4.14 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 165 | meek | 11 | contrast, list, list_gloss, occupation, person | adjective | 3.32 | M1 trait; M3 covered: meek | **T** | ref M1 trait; agree |
| 166 | dutiful | 11 | list, list_gloss, person | adjective | 2.63 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 167 | obnoxious | 11 | list, list_gloss, occupation, person | adjective | 3.38 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 168 | gruff | 10 | list, list_gloss, occupation, person | adjective | 2.81 | M1 trait; M3 covered: [blunt](../../../data/traits/instructions/blunt.json) | **T** | ref M1 trait; agree |
| 169 | [intense](../../../data/traits/instructions/intense.json) | 10 | ai_assistant, list, list_gloss, person | adjective | 4.39 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 170 | discerning | 10 | ai_assistant, list, person | adjective | 3.02 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 171 | [peaceful](../../../data/traits/instructions/peaceful.json) | 9 | list, list_gloss, person | adjective | 4.28 | corpus trait | **T** | ref M1 trait, corpus trait; agree |
| 172 | protective | 9 | ai_assistant, list, person | adjective | 4.13 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 173 | hypercritical | 9 | list, list_gloss, occupation, person | adjective | 1.76 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 174 | self sufficient | 9 | list, list_gloss, occupation, person | phrase | 4.32 | M1 trait; M3 covered: [self_reliant](../../../data/traits/instructions/self_reliant.json) | **T** | ref M1 trait; agree |
| 175 | reticent | 9 | ai_assistant, list, list_gloss, person | adjective | 2.62 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 176 | nasty | 9 | contrast, list, occupation, person | adjective | 4.22 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 177 | brutal | 9 | list, occupation, person | adjective | 4.1 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 178 | communicative | 8 | list, occupation, person | adjective | 2.94 | M1 trait; M3 new | **T** | ref M1 trait; agree |
| 179 | fast | 8 | ai_assistant, list, occupation, person | adjective | 5.13 | M1 trait; M3 covered: [hurried](../../../data/traits/instructions/hurried.json) | **T** | ref M1 trait (covered by hurried); my reading B: speed, not character |
| 180 | studious | 8 | list, occupation, person | adjective | 2.54 | M1 trait; M3 new | **T** | ref M1 trait; agree |

Rows 136, 155 and 165: M3 says covered by `kind`, `rational` and `meek`, stems with no instruction file
(queue or seed-list stems), so they are not linked.

## Appendix B: census of the 219 unique rows at counts 2–7

Every eligible row with a count of 2 to 7 that no other source has, read by the agent.  "var" marks a
spelling variant of a word the registry already has (good-humoured beside good_humored, which the table also
holds at count 3); well-organised and well-organized are one word split by spelling, neither known.

### Counts 3–7 (85 rows; count after each word)

- **T** (39): hyperactive 7, hard worker 7, overprotective 7, free-spirited 5, likable 5, uninvolved 5,
  ineffectual 5, fun-loving 5, unlovable 5, choleric 5, good listener 5, puerile 5, untrusting 5, upbeat 4,
  weak-willed 4, [dreamer](../../../data/roles/instructions/dreamer.json) 4 (a corpus role), mealy-mouthed 4,
  good-humoured 4 (var), co-operative 4 (var), warmhearted 4, no-nonsense 4, unlikable 4, smarmy 4,
  well-meaning 4, well-balanced 4, unsupportive 3, well-organised 3 (split), braggart 3, pessimist 3,
  judgemental 3 (var), organised 3 (var), snob 3, independent-minded 3, short-sighted 3, quick to anger 3,
  absentminded 3, man of action 3, hypocrite 3, self-obsessed 3
- **t** (9): efficiency 6, consistency 5, introvert 5, patience 4, resilience 3, optimism 3, precision 3,
  perseverance 3, extrovert 3
- **B** (14): uncommitted 5, unshaken 4, problem solver 4, undistinguished 4, unlovely 4, experimental 3,
  untried 3, skilful 3 (var), perfunctory 3, adept 3, well-educated 3, insensible 3, uncomplimentary 3, inapt 3
- **N** (15): algorithmic 6, user-friendly 5, overwrought 4, unprepossessing 4, frail 4, multilingual 3,
  fertile 3, scrawny 3, well-dressed 3, lanky 3, loved 3, unfulfilled 3, flaccid 3, amused 3, undervalued 3
- **J** (8): above all 5, something else 4, unambiguous 3, unstructured 3, unmitigated 3, unsought 3,
  imperceptible 3, evocative 3

### Count 2 (134 rows)

- **T** (32): duplicitous, non-emotional, straight-forward (var), task-oriented, peace-loving, well-organized
  (split), go-getter, dilatory, well-rounded, unshakeable (var), high-energy, exasperating,
  [narcissist](../../../data/roles/instructions/narcissist.json) (a corpus role), unmannerly, insouciant,
  peremptory, self-centred (var), unmotivated, over-anxious (var),
  [loner](../../../data/roles/instructions/loner.json) (a corpus role),
  [gossip](../../../data/roles/instructions/gossip.json) (a corpus role), unfussy, over-emotional,
  in-your-face, prolix, man of few words, easy to talk to, overachieving, talky, coachable, gormless, bumptious
- **t** (26): unobtrusively, be helpful, not very social, empathetic and supportive, transparency, no fear, no
  guilt, no anger, no sadness, unreasonably, nonchalance, overly critical, humor, persistence, determination,
  painstakingly, vanity, little shy, bit lazy, diligence, be honest, be selfish, be dishonest, humility,
  honesty, modesty
- **B** (19): unskillful, well-integrated, fighter, good man, unqualified, untrammelled, unspoiled, untested,
  pissy, good at communication, repetitive, well prepared, precipitate, unpleasing, interactive,
  learning-capable, infallible, protean, multitasking
- **N** (26): exultant, schizophrenic, sallow, plump, hale, underdeveloped, gentleman, unscathed, large,
  feline, unattached, dumpy, pale, impecunious, thief, honored, overdeveloped,
  [artist](../../../data/roles/instructions/artist.json) (a corpus role), comely, friend, inbred, dispirited,
  uncomely, dexterous, uncelebrated, ruddy
- **J** (31): reliable source, data, query, interface, response, good friend, unembellished, unhealthily,
  unappetizing, in the end, scalable, unbroken, unasked, long, unadulterated, accuracy, untraced, overdone,
  lucrative, probable, others, uncluttered, unenjoyable, opposite, prattle, intangible, protracted, nebulous,
  boundary, like, inchoate

Four of the T rows (dreamer, narcissist, loner, gossip) are corpus **roles**: lost as trait candidates, but the
corpus has them in another form.  The count-2 J list shows what a floor of 2 would let through: `ai_assistant`
vocabulary (data, query, interface, response, scalable) and prose fragments.

## Appendix C: the ineligible rows, read in full

**`unknown_word`, 122 rows.**  Trait words by the agent's reading (37; an asterisk marks one the registry has
from another generator): be unempathetic, unempathetic (×4 emissions), unempathic, confrontive, confrontative,
confrontationalist, daydreamy, imperceptive\*, overfriendly, overgentle, unaffable\*, unamiable\*,
uncalculating\*, uncomplaisant\*, uncourteous\*, uncurious\*, undecisive, unhesitant, unopinionated, unflashy,
unshowy, unsnobbish, unsycophantic, untrustful\*, unvirtuous, uncircumspect, uncomplacent, unzestful,
playboyish, wiseacres, gormandizer, uncorruptible, unskilful, sentimentalistic, uncoercible, unapproving,
unthorough\*.  The rest are non-words and morphological loops (eight `morosest-` and six `undoubted-` forms),
five concatenated name tokens (`azizabdul-`), adverbs, and a few physical or state words (moustacheless,
overgroomed, unglad).  The 52 that rule 1b's negating-prefix route would send to the probe include 23 of the
37 trait words above; the other 14 (the `confront-` forms, daydreamy, overfriendly, gormandizer and others)
have no negating prefix.

**`below_hard_reject`, 67 rows.**  Trait words (22): caddish, complaisant\*, coolheaded, farseeing\*,
hardhearted, heedful\*, improvident\*, irresolute\*, jocose, larcenous\*, mirthless\*, misanthropist,
overanxious\*, overcritical\*, overgenerous, overindulgent\*, perseverant, pertinacious\*, pragmatical,
quibbler, recreant, unflurried.  Trait content in the wrong form or misspelt (13): garrulity, garrulously,
procrastinates, pugnacity, punctiliously, sulkily, morosely, tempermental, traitorously, untiringly,
work-aholic, intractably, inscrutably, self-sufficent.  52 of the 67 carry an OEWN gloss hint and would go to the
probe under route 2, 21 of the 22 trait words among them (all but perseverant).

## Appendix D: how the numbers were computed

All counts were recomputed from the files linked above with short read-only scripts in the agent's scratchpad
(not deliverables): the table for strata, forms, families and Zipf; the registry, last row per key, for
`filter.verdict`, `novelty.decision` and the generators of each stem; the gitignored per-sample stems
([sample_stems.jsonl](../../../data/candidates/cache/base_model/round1/sample_stems.jsonl)) and sample metadata
([samples.jsonl](../../../data/candidates/cache/base_model/round1/samples.jsonl), seeds and families only; no
biography text left the scripts) for the seed and family analysis; the repository's own `extract_items` and
`zipf_info` (local `wordfreq` data, no download, no call) for the seed-echo replay and the rule-1b check.  A row
is **known** when the registry has its stem from any generator other than `base_model`, or `corpus_stem_match`
or `queue_stem_match` is set; the registry was read after the pilot's submission, so the kept rows' own keys
are excluded by naming the other generators.  Wilson intervals at z = 1.96.  The verdict codes in Appendices A
to C are the agent's reading unless the reference column decides them.
