# M1, the trait-hood filter: what it throws away, and whether it should (gate audit 5)

Audit of gate 5 of [README.md](./README.md), by an Opus agent, 2026-10-12.  Read-only: no API call, no
code or data edit; every figure below is recomputed from the records on disk.  Terms: the
[Terms block of escalations.md](../escalations.md#terms) and the
[glossary](../../trait_gap_generation/glossary.md).  Here **M1** is the trait-hood filter; a **reading**
is one of Haiku 5.5's three independent passes over a word's verdict steps; the **vote** combines them;
the **second opinion** is Sonnet 5.5 repeating the verdict steps on about 10% of a run's words;
a **holding list** (states, physical, roles, nationalities) is where a tagged word waits.  The runs:
**TDA** and **Allport-hi** are the psycholexical census's two big stages (the TDA list of trait-descriptive
adjectives with familiarity ratings, and the 1936 Allport-Odbert list at Zipf 2.5 and above); **papers** is the alignment sweep's run over
alignment papers; **IPIP** names behaviour-item clusters (g600).  Codes used in
the tables: **OK** (the discard fits the intent), **FN** (a trait, discarded), **FN-s** (a trait sent to the
states list, the error Roger weights mildest), **MR** (not a trait, but put on the wrong side list),
**BL** (borderline; counted apart), **FP** (passed as a trait, but not one).

## Verdict

**Overall: doing what was intended but improvable.  On single words it does what was intended about as
well as these samples can detect; on phrase labels it mostly does not, and that is fixable.**

- **Single words** (censuses, Roget, WordNet, base model: 5,868 of the 6,442 words M1 judged in the seven
  runs).  The discards fit the intent.  Allport-hi's 50% is real: 74% of its states come from Allport and
  Odbert's own column II (temporary states), and its rejects are archaic compounds, OCR noise, first
  names, nouns and pure praise.  In my seeded sample 0 of 40 Allport-hi rejects is a trait (95% CI 0 to
  8.8%), and Sonnet's random 10% gives 2 of 63 (3.2%).  The cost sits on the other side: the vote rule
  passes about 16% non-traits on Allport-hi (11.5 to 22.3%), by design (Roger's 3 : 1 weights), against
  at most 2% on TDA.
- **Phrase labels** (IPIP and the alignment sweep: 541 of their 574 labels are phrases).  Two defects.  (1) The
  **definition probe** cuts every multiword label in its Zipf band as "not a single English word": 75 of
  the 77 phrases it saw, 67 of them plain traits.  (2) The established check's test, "would people say
  'she is <label>'?", does not parse for a verb phrase, so clear AI dispositions (accepts shutdown, lies
  about actions, enables surveillance) come out "stretched".  Together: 72 of the alignment papers run's
  94 discards (77%, CI 67 to 84%) and 13 of IPIP's 22 (59%, CI 39 to 77%) are traits.  This contradicts
  Roger's decision that multiword labels are accepted (QUESTIONS 71).
- **Holding lists.**  States and physical are not a discard where their passes have run: 81% of TDA's
  states left the hold.  But 900 states rows and 127 physical rows have no judgement yet, all of
  Allport-hi's among them.  Roles (171) and nationalities (31) are held by Roger's decision with no pass,
  so in practice they are discarded; 4 of the roles are alignment phrases that QUESTIONS 67 makes traits.
- **Fixes** (section 7).  Keep phrases out of the probe ($0; about $2 to re-judge the cut rows).  Let
  Sonnet decide the turned-away phrases of the phrase generators, or render a phrase label as "someone who
  <label>" (pennies, but the second is a rubric change).  Run the states and physical passes on the
  unjudged holds (about $1.7 with M3).  Making Sonnet decisive on split votes would cut the Allport-hi
  FP rate about in half for about $8; it is optional.

## 1. The rule, from the code

All seven production batches ran the **split pipeline**, rubric 5, `claude-haiku-5-5` with three readings,
step versions sense 8, established 7, vague 3, kind 6, same_sense 2, gloss 4, alignment 3, descriptors 1
(each batch's run record, for example [2026-10-11-allport_hi_censuses/run.json](../../../data/candidates/filter/2026-10-11-allport_hi_censuses/run.json)).
The single-call classifier ([filter_rubric.py](../../../assistant_axis/gapgen/filter_rubric.py) v6,
`FilterRunner` in [filter.py](../../../assistant_axis/gapgen/filter.py)) is still selectable with
`--pipeline single` ([traithood_filter.py:303](../../../data_analysis/gap_generation/traithood_filter.py#L303))
but judged none of these rows, so it is described only where the split reuses it.

| stage | rule | a word fails when | and then |
|---|---|---|---|
| 0a floor | [freq.py:37-38, 108-127](../../../assistant_axis/gapgen/freq.py#L108): Zipf of the rarest content word (hyphenated parts split) | under 1.5 with no rescue (negating prefix, gloss hint, curated source, familiarity) | hard reject, `too_rare`, no call (gate 1's; **0 rows** in the seven runs: the census stages pre-filter, and the phrase generators' rows carry gloss hints, which rescue them into the probe) |
| 0b definition probe | band 1.5 ≤ Zipf < 2.5 **or any rescued word** ([freq.py:127](../../../assistant_axis/gapgen/freq.py#L127)); one word per call ([split_runner.py:799-809](../../../assistant_axis/gapgen/split_runner.py#L799)), prompt `DEFINE_PROBE_PROMPT` v3 ([filter_rubric.py:750-766](../../../assistant_axis/gapgen/filter_rubric.py#L750)); the **whole label** is sent as "word" ([filter_rubric.py:769-773](../../../assistant_axis/gapgen/filter_rubric.py#L769)) | the model answers `known: false` | cut ([split_runner.py:953-955](../../../assistant_axis/gapgen/split_runner.py#L953)): `reject`, `too_rare`, rule `probe` ([split_runner.py:1011-1017](../../../assistant_axis/gapgen/split_runner.py#L1011), [split.py:647-661](../../../assistant_axis/gapgen/split.py#L647)) |
| 1 sense | [step1_sense.md](../../trait_gap_generation/rubrics/step1_sense.md) draft 8, label only: readings of "You are <label>.", each primary or secondary | no primary reading | turned away, `no_persona_reading` (join rule 1, [split.py:366-368](../../../assistant_axis/gapgen/split.py#L366)) |
| 2a established | [check_established.md](../../trait_gap_generation/rubrics/check_established.md) draft 7, per primary reading: "would people say 'she is <label>' and mean this?" | every primary reading `stretched` | turned away, `stretched` (rule 2, [split.py:335-338, 369-371](../../../assistant_axis/gapgen/split.py#L335)) |
| 2b kind | [step2_kind.md](../../trait_gap_generation/rubrics/step2_kind.md) draft 6, per primary reading | the first surviving reading is not trait or membership, and no later one is | state / physical / role: the states / physical / roles list; action / evaluative / not_a_persona: turned away (rules 3 to 5, [split.py:372-404](../../../assistant_axis/gapgen/split.py#L372)) |
| notes | vague check, same-sense check, the comparison with a gloss hint | never | notes only; the comparison may move the accepted reading but never the outcome ([split.py:386-399](../../../assistant_axis/gapgen/split.py#L386)) |
| vote | three readings on Haiku 5.5 ([split_runner.py:173-181](../../../assistant_axis/gapgen/split_runner.py#L173)); `combine_readings` ([split.py:449-495](../../../assistant_axis/gapgen/split.py#L449)) | **all three** readings turn it away | otherwise the turned-away readings drop out and the most common remaining outcome wins; a tie goes to trait if any reading says trait |
| second opinion | Sonnet 5.5, steps 1 to 3, on a seeded 10% of words plus every word noted `obvious_sense_not_trait` or `most_likely_reading_stretched` ([split_runner.py:764-773](../../../assistant_axis/gapgen/split_runner.py#L764)) | never decides | recorded; the tripwire (over 10% disagreement on at least 20 rows, [split.py:753-755](../../../assistant_axis/gapgen/split.py#L753)) only warns ([split_runner.py:929-941](../../../assistant_axis/gapgen/split_runner.py#L929)) |
| mapping | `verdict_tags_holding` ([split.py:541-554](../../../assistant_axis/gapgen/split.py#L541)) | | trait (a nationality membership held on `nationalities`); `tagged` + list for states, physical, roles; `reject` + tag for turned away |
| afterwards | `promote` ([promote.py:236-260](../../../assistant_axis/gapgen/promote.py#L236)) | | roles and nationalities "never promoted"; states only after the states pass **and** Roger's confirmed name; physical only by name; a reject is final |

Constants: models at [split_runner.py:101-105](../../../assistant_axis/gapgen/split_runner.py#L101);
`--second-opinion-frac 0.10`, `--seed 0` ([traithood_filter.py:343-344](../../../data_analysis/gap_generation/traithood_filter.py#L343));
recorded targets `TARGET_EXISTING_CORRECT` 0.95 and `TARGET_RANDOM_TRAIT_MAX` 0.15
([filter.py:730-735](../../../assistant_axis/gapgen/filter.py#L730)), reported as warnings and never
failing ([test_gapgen_acceptance.py:73-111](../../../assistant_axis/tests/test_gapgen_acceptance.py#L73)).

## 2. The intent

- **What M1 asks** ([plan 14](../../trait_gap_generation/14_traithood_filter_registry.md) § 1): "is this
  something a speaking persona can *enact as a stable disposition or style*, does the 32B model know it,
  and which sense do we mean?"; `reject` "only for non-words, pure relational adjectives and things nobody
  could enact" (§ 3.4).
- **The bar for turning a word away** ([coding_plan_split.md](../../trait_gap_generation/coding_plan_split.md)
  § 1, Roger 2026-09-29): "reject only what is 'too unclear to put in the corpus even if there is in fact
  no clearer alternative'"; and "a few wrong words slipping through is accepted".
- **Error weights** (Roger, 2026-10-08, [haiku55_readout.md](../../trait_gap_generation/haiku55_readout.md)
  § 5): a trait wrongly turned away 3, a trait mis-tagged physical or role 1, a trait/states confusion 0.5
  ("the boundary is particularly permeable"), a non-trait passed 1.  The vote rule was chosen on 600 words
  against Opus with these weights; that is its recorded derivation.
- **Phrases are wanted** ([QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md) 71, Roger
  2026-10-11): "**multiword accepted**, with no drift toward single words as a goal", because the
  alignment area "is particularly likely to come up with issues that don't have simple English terms".
- **AI dispositions are traits, not roles** (QUESTIONS 67): "Roles are supposed to be large, large enough
  to exclude other roles.  These aren't that large."
- **Side lists**: decisions 3 and 12 of [decisions_m1.md](../../trait_gap_generation/decisions_m1.md)
  (memberships are traits; a state "merely means there is some extra work to do"); QUESTIONS 1 (roles
  "stay on their list, read by hand"; nationalities stay held) and 45 (the states pass's routes).
- **Thresholds without a recorded derivation**: the Zipf 2.5 top of the probe band (plan 14 § 11
  derives 1.5 and 2.0 from the corpus's label frequencies, not 2.5); the probe's behaviour on phrases
  (its v3 rubric was tuned on single-word derivations, [filter_rubric.py:744-748](../../../assistant_axis/gapgen/filter_rubric.py#L744);
  nothing records a phrase test); the 10% second-opinion share and 10% tripwire (decision 7 and
  [opus_audit_m1.md](../../trait_gap_generation/opus_audit_m1.md) motivate a sample, not its size).

## 3. The recorded discard

Reproduced from each batch's results file (the words the batch itself judged; for example [2026-10-11-allport_hi_censuses/results.jsonl](../../../data/candidates/filter/2026-10-11-allport_hi_censuses/results.jsonl)).  The last column is
README's basis, the registry's last row per key grouped by the run's sources; it differs where a run's
words were also judged in another batch, whose block the registry keeps.  Roget full: of its 448
registry rows, 160 carry the Roget batch's block, 85 were re-judged by the Allport-hi batch a day later,
and 203 had been judged earlier (TDA, the generator pilots, the M3 pilots).

| run (filter batch) | judged | trait | states | physical | roles | turned away by the steps | probe cut | not trait | registry by source | cost |
|---|---|---|---|---|---|---|---|---|---|---|
| TDA ([2026-10-10-tda_censuses](../../../data/candidates/filter/2026-10-10-tda_censuses/)) | 1,988 | 1,779 | 140 | 34 | 6 | 26 (no reading 10, stretched 8, evaluative 6, action 2) | 3 | 209 (10.5%) | 10.4% of 2,818 | $7.12 |
| Allport-hi ([2026-10-11-allport_hi_censuses](../../../data/candidates/filter/2026-10-11-allport_hi_censuses/)) | 3,538 | 1,745 | 863 | 116 | 133 | 681 (stretched 284, no reading 267, evaluative 56, action 45, not a persona 29) | 0 | 1,793 (50.7%) | 50.1% of 3,646 | $10.81 |
| Roget ([2026-10-11-full_roget](../../../data/candidates/filter/2026-10-11-full_roget/)) | 245 | 123 | 42 | 3 | 6 | 69 (stretched 30, no reading 27, evaluative 8, action 2, not a persona 2) | 2 | 122 (49.8%) | 36.6% of 448 | $0.82 |
| WordNet ([2026-10-11-full_wn_clusters](../../../data/candidates/filter/2026-10-11-full_wn_clusters/)) | 79 | 62 | 7 | 7 | 0 | 2 (no reading) | 1 | 17 (21.5%) | 11.5% of 468 | $0.31 |
| IPIP ([2026-10-11-g600_ipip](../../../data/candidates/filter/2026-10-11-g600_ipip/)) | 194 | 172 | 4 | 1 | 0 | 4 (stretched) | 13 | 22 (11.3%) | 9.4% of 234 | $0.71 |
| base model ([2026-10-12-pilot_base_model](../../../data/candidates/filter/2026-10-12-pilot_base_model/)) | 18 | 17 | 0 | 0 | 0 | 1 (no reading) | 0 | 1 (5.6%) | 4.9% of 467 | $0.06 |
| alignment papers ([2026-10-11-papers_alignment_sweep](../../../data/candidates/filter/2026-10-11-papers_alignment_sweep/)) | 380 | 286 | 0 | 0 | 4 | 30 (stretched 15, no reading 15) | 60 | 94 (24.7%) | 23.0% of 408 | $1.85 |
| **all seven** | **6,442** | **4,184** | 1,056 | 161 | 149 | 813 | 79 | **2,258 (35.1%)** | | $21.68 |

Two facts the summaries hide.  **The probe is a phrase filter in practice**: across these runs it
cut 4 of 846 single words it probed (competitory, dissensualized, underogatory, humourous, all rightly)
and **75 of 77 phrases** ("a two-word verb phrase ... not a single English word").  The earlier alignment
batches show the same: [2026-10-10-full_alignment_sweep](../../../data/candidates/filter/2026-10-10-full_alignment_sweep/)
41 of 42 phrases, [2026-10-11-b_alignment_sweep](../../../data/candidates/filter/2026-10-11-b_alignment_sweep/)
8 of 8.  **The second opinion disagrees most where the discard is largest.**  On the random 10% alone
(reconstructed with the run's seed 0), Haiku and Sonnet agree on the outcome for 94.9% of TDA's 198
words, 70.3% of Allport-hi's 354, 75% of Roget's 24, 62.5% of WordNet's 8, 94.4% of IPIP's 18 and
93.8% of the papers' 32.  The tripwire warned on Allport-hi and Roget and nothing else happened, as
built.

## 4. The sample

**Selection rule** (script [sample.py](/tmp/claude-501/m1audit/sample.py), scratch, not a deliverable):
`random.Random(20261012)`, one draw per stratum in the order listed, each pool sorted by registry key
before `sample`.  Strata: Allport-hi rejects by cause (stretched 14, no reading 14, evaluative 5, action
4, not a persona 3), Allport-hi states 18, roles 6, physical 6, kept 20; TDA rejects 12, states 6,
physical 3, roles 3, kept 10; Roget rejects 10, states 4, roles 1, physical 1, kept 8; WordNet rejects 3,
states 2, physical 2, kept 6; IPIP rejects 6, states 1, physical 1, kept 6; base model reject 1, kept 3;
papers rejects 10, roles 2, kept 7.  **138 discarded or held and 60 kept.**  Each verdict is my reading
against the intent of section 2, not against the rubric; the bracket says what it rests on (M1's own
readings and reasons, the generator's hint, a corpus file, Roger's marks or expected outcome, Opus, the
Sonnet second opinion).  "Readings" lists the three readings' outcomes: T trait, S states, P physical,
R roles, X turned away.

### 4a. The seeded sample, in full

| # | run | stratum | label | M1 outcome | readings | Sonnet | verdict | why (what it rests on) |
|---|---|---|---|---|---|---|---|---|
| 1 | Allport-hi | reject | abundant | reject: stretched | XXX |  | **OK** | said of quantities; "generous" is not an ordinary use of it for a person [M1 readings] |
| 2 | Allport-hi | reject | amending | reject: stretched | XXX |  | **OK** | said of texts and laws; no reading about a person [M1 readings] |
| 3 | Allport-hi | reject | blue-devil | reject: stretched | XXX |  | **OK** | archaic noun; the "low spirits" sense is secondary and obscure [M1 readings] |
| 4 | Allport-hi | reject | bowery | reject: stretched | XXX |  | **OK** | a place name [M1 readings] |
| 5 | Allport-hi | reject | bygone | reject: stretched | XXX |  | **OK** | said of times and things, not people [M1 readings] |
| 6 | Allport-hi | reject | candied | reject: stretched | XXX | X | **OK** | "candied words", not a candied person [M1 readings; Sonnet agrees] |
| 7 | Allport-hi | reject | excelled | reject: stretched | XXX |  | **OK** | a verb form with no adjectival use [M1 readings] |
| 8 | Allport-hi | reject | gratifying | reject: stretched | XXX |  | **OK** | said of results and news [M1 readings] |
| 9 | Allport-hi | reject | harrowing | reject: stretched | XXX |  | **OK** | said of experiences [M1 readings] |
| 10 | Allport-hi | reject | heating | reject: stretched | XXX |  | **OK** | no reading about a person [M1 readings] |
| 11 | Allport-hi | reject | purifying | reject: stretched | XXX |  | **OK** | said of water, rites [M1 readings] |
| 12 | Allport-hi | reject | rattling | reject: stretched | XXX |  | **OK** | only the dated intensifier "rattling good" [M1 readings] |
| 13 | Allport-hi | reject | two-sided | reject: stretched | XXX |  | **BL** | the secondary reading "duplicitous" is a trait but was never checked (only primary readings count); two-faced is the usual word [M1 readings] |
| 14 | Allport-hi | reject | weak-hinged | reject: stretched | XXX |  | **OK** | archaic; the character sense is secondary and obscure [M1 readings] |
| 15 | Allport-hi | reject | capital | reject: no_reading | XXX |  | **OK** | dated praise ("a capital fellow") [M1 readings] |
| 16 | Allport-hi | reject | circumstantial | reject: no_reading | XXX |  | **OK** | the "gives detailed accounts" sense of a person is archaic (Allport column I, 1936) [M1 readings; column] |
| 17 | Allport-hi | reject | clipping | reject: no_reading | XXX |  | **OK** | an act or a cutting [M1 readings] |
| 18 | Allport-hi | reject | compound | reject: no_reading | XXX |  | **OK** | said of substances [M1 readings] |
| 19 | Allport-hi | reject | cow-baby | reject: no_reading | XXX |  | **OK** | archaic word for a coward, unknown today [M1 readings] |
| 20 | Allport-hi | reject | destinies | reject: no_reading | XXX |  | **OK** | plural noun [M1 readings] |
| 21 | Allport-hi | reject | kill-courtesy | reject: no_reading | XXX |  | **OK** | Shakespearean nonce compound [M1 readings] |
| 22 | Allport-hi | reject | leveling | reject: no_reading | XXX |  | **OK** | a process [M1 readings] |
| 23 | Allport-hi | reject | manufacturing | reject: no_reading | XXX |  | **OK** | an industry [M1 readings] |
| 24 | Allport-hi | reject | narrowing | reject: no_reading | XXX |  | **OK** | said of roads and choices [M1 readings] |
| 25 | Allport-hi | reject | plat | reject: no_reading | XXX |  | **OK** | a plot of land [M1 readings] |
| 26 | Allport-hi | reject | rye | reject: no_reading | XXX |  | **OK** | a grain [M1 readings] |
| 27 | Allport-hi | reject | slap | reject: no_reading | XXX |  | **OK** | a blow [M1 readings] |
| 28 | Allport-hi | reject | snack | reject: no_reading | XXX |  | **OK** | slang for an attractive person at most, physical [M1 readings] |
| 29 | Allport-hi | reject | best | reject: evaluative | XXX |  | **OK** | pure praise [M1 readings] |
| 30 | Allport-hi | reject | fantastic | reject: evaluative | XXX |  | **OK** | pure praise [M1 readings] |
| 31 | Allport-hi | reject | glorious | reject: evaluative | XXX |  | **OK** | pure praise [M1 readings] |
| 32 | Allport-hi | reject | putrid | reject: evaluative | XXX |  | **OK** | pure condemnation [M1 readings] |
| 33 | Allport-hi | reject | wally | reject: evaluative | XXX |  | **OK** | a British insult, "fool" [M1 readings] |
| 34 | Allport-hi | reject | blackmailing | reject: action | XXX |  | **OK** | reads as the act; blackmailer is the person word [M1 readings] |
| 35 | Allport-hi | reject | boning | reject: action | XXX |  | **OK** | an act [M1 readings] |
| 36 | Allport-hi | reject | humping | reject: action | XXX |  | **OK** | an act [M1 readings] |
| 37 | Allport-hi | reject | spitting | reject: action | XXX |  | **OK** | an act [M1 readings] |
| 38 | Allport-hi | reject | colin | reject: not_a_persona | XXX |  | **OK** | a first name [M1 readings] |
| 39 | Allport-hi | reject | jack adams | reject: not_a_persona | XXX |  | **OK** | a name; the archaic "fool" sense is unknown today [M1 readings] |
| 40 | Allport-hi | reject | roxy | reject: not_a_persona | XXX |  | **OK** | a first name [M1 readings] |
| 41 | Allport-hi | states | begging | states | SSS |  | **OK** | a passing act or state; beggar would be a role [M1 readings] |
| 42 | Allport-hi | states | bluffing | states | TSS | S | **FN-s** | the habitual bluffer is a trait (the single-call rubric used bluffing as a trait example), but the -ing form read as the act now; one reading said trait [M1 readings; Sonnet: states] |
| 43 | Allport-hi | states | bogged | states | SSS |  | **OK** | a situation [M1 readings] |
| 44 | Allport-hi | states | confounded | states | SSS |  | **OK** | a passing state [M1 readings] |
| 45 | Allport-hi | states | dissipating | states | XXS |  | **OK** | two readings turned it away, one said state; not a trait label as read [M1 votes] |
| 46 | Allport-hi | states | eligible | states | SSS |  | **OK** | a standing qualification; "eligible bachelor" is secondary [M1 readings] |
| 47 | Allport-hi | states | failing | states | SSS |  | **OK** | a situation [M1 readings] |
| 48 | Allport-hi | states | floundering | states | SSS |  | **OK** | a situation [M1 readings] |
| 49 | Allport-hi | states | hindered | states | SSS |  | **OK** | a situation imposed from outside [M1 readings] |
| 50 | Allport-hi | states | hurry-scurry | states | SSX |  | **OK** | a flustered rush; the habitual sense is secondary and archaic [M1 readings] |
| 51 | Allport-hi | states | learning | states | SSS |  | **OK** | an activity [M1 readings] |
| 52 | Allport-hi | states | mired | states | SSS |  | **OK** | a situation [M1 readings] |
| 53 | Allport-hi | states | nauseous | states | SSS |  | **OK** | a bodily state [M1 readings; Opus: states] |
| 54 | Allport-hi | states | oppressed | states | SSS | T | **BL** | Sonnet read a membership (one of an oppressed group), which would pass as a trait; Haiku a situation [M1 readings; Sonnet: trait] |
| 55 | Allport-hi | states | pillaging | states | SXX |  | **MR** | an act (two readings said action); the vote rule moved it to states, where it does no harm [M1 votes] |
| 56 | Allport-hi | states | smoldering | states | STS |  | **OK** | seething for now; the sultry sense is secondary [M1 readings] |
| 57 | Allport-hi | states | speechless | states | SSS |  | **OK** | a passing state [M1 readings] |
| 58 | Allport-hi | states | whispering | states | SST |  | **OK** | an activity [M1 readings] |
| 59 | Allport-hi | roles | captain | roles | RRR |  | **OK** | an office [M1 readings] |
| 60 | Allport-hi | roles | [comedian](../../../data/roles/instructions/comedian.json) | roles | RTR |  | **OK** | a profession, and a corpus role [M1 readings; corpus role] |
| 61 | Allport-hi | roles | facilitating | roles | RTR |  | **BL** | read as the job of a facilitator; "smooths others' way" is a secondary trait reading, and one reading of three said trait [M1 votes] |
| 62 | Allport-hi | roles | minor | roles | RRR |  | **OK** | an age that rules out a profession (the kind rubric's rule) [M1 readings] |
| 63 | Allport-hi | roles | omnipotent | roles | RRR |  | **OK** | not a disposition [M1 readings] |
| 64 | Allport-hi | roles | prosecuting | roles | RRR |  | **OK** | an office [M1 readings] |
| 65 | Allport-hi | physical | bent | physical | PTP |  | **OK** | stooped; the slang "corrupt" is secondary [M1 readings] |
| 66 | Allport-hi | physical | dilapidated | physical | PPP |  | **OK** | a bodily condition [M1 readings] |
| 67 | Allport-hi | physical | high-colored | physical | SPP |  | **OK** | complexion [M1 readings] |
| 68 | Allport-hi | physical | lumbering | physical | PPP |  | **OK** | a way of moving [M1 readings] |
| 69 | Allport-hi | physical | meager | physical | PPP | X | **OK** | thin; not a trait either way [M1 readings; Sonnet: stretched] |
| 70 | Allport-hi | physical | sharp-cut | physical | PPP |  | **OK** | facial features [M1 readings] |
| 71 | Allport-hi | kept | baffling | trait | TTT |  | **OK** | inscrutable manner, an effect on others, which kind draft 6 admits [M1 readings] |
| 72 | Allport-hi | kept | butterfly | trait | XTX |  | **OK** | flighty, fickle ("social butterfly"); passed on one reading of three [M1 votes] |
| 73 | Allport-hi | kept | card | trait | XTT | T | **OK** | "quite a card": a wit [M1 readings; Sonnet agrees] |
| 74 | Allport-hi | kept | cassandra | trait | TXX | T | **FP** | read as "a woman named Cassandra" and passed as a gender membership; gloss "being a woman named Cassandra" [M1 gloss; Sonnet made the same error] |
| 75 | Allport-hi | kept | confounding | trait | TTT |  | **OK** | puzzling to others [M1 readings] |
| 76 | Allport-hi | kept | daffy | trait | TTT |  | **OK** | silly, goofy [M1 readings] |
| 77 | Allport-hi | kept | dazzling | trait | TTT |  | **OK** | charming in manner (near physical) [M1 readings] |
| 78 | Allport-hi | kept | disenchanted | trait | TST |  | **OK** | a standing disillusion [M1 readings] |
| 79 | Allport-hi | kept | engrossing | trait | TTT |  | **OK** | captivating company [M1 readings] |
| 80 | Allport-hi | kept | feral | trait | TTT | T | **OK** | wild, unruly [M1 readings; Sonnet agrees] |
| 81 | Allport-hi | kept | half-cracked | trait | TTT |  | **OK** | a bit mad [M1 readings] |
| 82 | Allport-hi | kept | insider | trait | TTT |  | **OK** | a circumstance membership [M1 readings] |
| 83 | Allport-hi | kept | know-all | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 84 | Allport-hi | kept | monstrous | trait | TTT |  | **OK** | cruel [M1 readings] |
| 85 | Allport-hi | kept | motivating | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 86 | Allport-hi | kept | obstructing | trait | TTX |  | **OK** | obstructive [M1 readings] |
| 87 | Allport-hi | kept | provoking | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 88 | Allport-hi | kept | retreating | trait | XTT |  | **BL** | "withdraws from conflict" is a trait, but "You are retreating." reads as an act now; one reading said action [M1 votes] |
| 89 | Allport-hi | kept | stainless | trait | TTX |  | **OK** | a blameless record (regard) [M1 readings] |
| 90 | Allport-hi | kept | weighty | trait | TTT | T | **OK** | influential, grave [M1 readings; Sonnet agrees] |
| 91 | TDA | reject | admirable | reject: evaluative | XXX |  | **OK** | pure praise (the rubric's evaluative_only) [M1 readings] |
| 92 | TDA | reject | cautionary | reject: stretched | XXX |  | **OK** | said of tales and advice [M1 readings] |
| 93 | TDA | reject | competitory | reject: probe | - |  | **OK** | probe: nonce word [probe reason] |
| 94 | TDA | reject | dissensualized | reject: probe | - |  | **OK** | probe: nonce word [probe reason] |
| 95 | TDA | reject | great | reject: evaluative | XXX |  | **OK** | pure praise [M1 readings] |
| 96 | TDA | reject | guilty | reject: action | XXX |  | **OK** | a deed or a feeling, not a disposition label [M1 readings] |
| 97 | TDA | reject | invidious | reject: no_reading | XXX |  | **OK** | said of comparisons [M1 readings] |
| 98 | TDA | reject | nonvariant | reject: stretched | XXX |  | **OK** | a technical term [M1 readings] |
| 99 | TDA | reject | overprompt | reject: no_reading | XXX |  | **OK** | not a word for a person [M1 readings] |
| 100 | TDA | reject | scheduled | reject: no_reading | XXX |  | **OK** | said of events [M1 readings] |
| 101 | TDA | reject | terrific | reject: evaluative | XXX |  | **OK** | pure praise [M1 readings] |
| 102 | TDA | reject | unsly | reject: no_reading | XXX | T | **FN** | un- + sly, not cunning, plain from its parts (the probe rubric admits such words); step 1 called it not a word [Sonnet: trait] |
| 103 | TDA | states | awake | states | SSS |  | **OK** | a state [M1 readings] |
| 104 | TDA | states | cajoling | states | SST |  | **FN-s** | a wheedling manner is a trait (one reading of three said so); the -ing form read as the act now [M1 votes] |
| 105 | TDA | states | discouraged | states | SSS |  | **OK** | a mood [M1 readings] |
| 106 | TDA | states | [edgy](../../../data/traits/instructions/edgy.json) | states | SST |  | **FN-s** | a corpus trait in the provocative sense; M1 read "nervous right now" [corpus file; Opus: trait] |
| 107 | TDA | states | expectant | states | SSS |  | **OK** | a mood [M1 readings] |
| 108 | TDA | states | guiltless | states | SSS |  | **OK** | innocent of a wrong, a situation [M1 readings] |
| 109 | TDA | physical | florid | physical | PPT |  | **OK** | complexion; ornate speech is secondary [M1 readings] |
| 110 | TDA | physical | gorgeous | physical | PPP |  | **OK** | looks [M1 readings] |
| 111 | TDA | physical | sturdy | physical | PPP |  | **OK** | build [M1 readings] |
| 112 | TDA | roles | important | roles | TRR |  | **MR** | VIP status sent to roles; better turned away (self-important is the secondary trait) [M1 readings] |
| 113 | TDA | roles | juvenile | roles | RRR |  | **BL** | rubric-consistent (an age), but "childish" is a common reading said of an adult [M1 readings] |
| 114 | TDA | roles | ministerial | roles | XRX | R | **OK** | an office [M1 readings; Sonnet agrees] |
| 115 | TDA | kept | dour | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 116 | TDA | kept | folksy | trait | TTT |  | **OK** | a speaking style [M1 readings] |
| 117 | TDA | kept | indulgent | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 118 | TDA | kept | responsive | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 119 | TDA | kept | senseless | trait | TTT |  | **OK** | foolish [M1 readings] |
| 120 | TDA | kept | [skeptical](../../../data/traits/instructions/skeptical.json) | trait | TTT | T | **OK** | a corpus trait [corpus file; Sonnet agrees] |
| 121 | TDA | kept | sniveling | trait | STT |  | **OK** | a whining manner [M1 readings] |
| 122 | TDA | kept | thunderous | trait | TTT |  | **OK** | a booming voice and presence [M1 readings] |
| 123 | TDA | kept | undeceivable | trait | TTT |  | **OK** | from parts, plain [M1 readings] |
| 124 | TDA | kept | unfailing | trait | TTT |  | **OK** | dependable [M1 readings] |
| 125 | Roget | reject | accidental | reject: action | XXX |  | **OK** | said of events [M1 readings] |
| 126 | Roget | reject | cleaned | reject: stretched | XXX |  | **OK** | no ordinary person reading [M1 readings] |
| 127 | Roget | reject | contraband | reject: stretched | XXX |  | **OK** | said of goods [M1 readings] |
| 128 | Roget | reject | embryonic | reject: stretched | XXX |  | **OK** | said of plans [M1 readings] |
| 129 | Roget | reject | insoluble | reject: no_reading | XXX |  | **OK** | said of substances and puzzles [M1 readings] |
| 130 | Roget | reject | portable | reject: no_reading | XXX |  | **OK** | said of things [Roger's expected outcome: turned away] |
| 131 | Roget | reject | prohibitive | reject: stretched | XXX | X | **OK** | said of costs [M1 readings; Sonnet agrees] |
| 132 | Roget | reject | time-honored | reject: stretched | XXX |  | **OK** | said of customs [M1 readings] |
| 133 | Roget | reject | unfeasible | reject: no_reading | XXX |  | **OK** | said of plans [M1 readings] |
| 134 | Roget | reject | wanting | reject: evaluative | XXX |  | **OK** | "found wanting": blame [M1 readings] |
| 135 | Roget | states | armed | states | SSS |  | **OK** | a situation [M1 readings] |
| 136 | Roget | states | ghost-like | states | STS |  | **OK** | pallor; not a trait label [M1 readings] |
| 137 | Roget | states | requesting | states | SXX |  | **OK** | an act (two readings said action) [M1 votes] |
| 138 | Roget | states | unwelcome | states | SST | S | **OK** | a situation [M1 readings; Sonnet agrees] |
| 139 | Roget | roles | unimportant | roles | RXR | X | **MR** | low status sent to roles; better turned away [M1 readings; Sonnet: evaluative] |
| 140 | Roget | physical | minute | physical | PPP |  | **OK** | size [M1 readings] |
| 141 | Roget | kept | deep-rooted | trait | TTT |  | **OK** | firmly held convictions (thin) [M1 readings] |
| 142 | Roget | kept | hard upon | trait | TTX |  | **BL** | an archaic phrase that needs an object (hard upon whom?) [M1 readings] |
| 143 | Roget | kept | inappropriate | trait | TTT |  | **OK** | behaves improperly [M1 readings] |
| 144 | Roget | kept | inexplicable | trait | TTT |  | **BL** | "unaccountable in conduct" is a thin trait; the word is said of events [M1 readings] |
| 145 | Roget | kept | optional | trait | TXX |  | **FP** | "a dispensable person"; passed on one reading of three; gloss "being dispensable in nature" [M1 votes, gloss] |
| 146 | Roget | kept | self-contradictory | trait | TTT |  | **OK** | a speaking habit [M1 readings] |
| 147 | Roget | kept | sound | trait | TTT |  | **OK** | sound judgment [M1 readings] |
| 148 | Roget | kept | trig | trait | XXT |  | **BL** | archaic "neat, smart in appearance", a grooming style; passed on one reading of three [M1 votes] |
| 149 | WordNet | reject | asynchronous | reject: no_reading | XXX | X | **OK** | said of processes [M1 readings; Sonnet agrees] |
| 150 | WordNet | reject | endemic | reject: no_reading | XXX |  | **OK** | said of diseases and species [M1 readings] |
| 151 | WordNet | reject | humourous | reject: probe | - |  | **OK** | probe: a misspelling of humorous [probe reason] |
| 152 | WordNet | states | accompanied | states | SSS |  | **OK** | a situation [M1 readings] |
| 153 | WordNet | states | inhabited | states | SXX |  | **OK** | possessed; not a trait label [M1 readings] |
| 154 | WordNet | physical | brunet | physical | PPP |  | **OK** | hair colour [M1 readings] |
| 155 | WordNet | physical | eyeless | physical | PPP |  | **OK** | the body [M1 readings] |
| 156 | WordNet | kept | crabbed | trait | TTT |  | **OK** | ill-tempered [M1 readings] |
| 157 | WordNet | kept | dynamical | trait | XTX |  | **OK** | energetic; passed on one reading of three [Opus: trait] |
| 158 | WordNet | kept | neighbourly | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 159 | WordNet | kept | stoical | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 160 | WordNet | kept | unresentful | trait | TTT |  | **OK** | from parts, plain [M1 readings] |
| 161 | WordNet | kept | untrusty | trait | TTT |  | **OK** | from parts, plain [M1 readings] |
| 162 | IPIP | reject | chronic unexplained symptoms | reject: stretched | XXX |  | **OK** | a health complaint; the cluster's name is the problem, not the filter [generator hint] |
| 163 | IPIP | reject | compulsively checking | reject: probe | - |  | **FN** | probe: "a two-word phrase, not a single English word"; a plain trait [probe reason; generator hint] |
| 164 | IPIP | reject | inconsistent with parents | reject: stretched | XXX |  | **OK** | the label does not say what it means (hint: treatment of parents swings) [M1 readings; generator hint] |
| 165 | IPIP | reject | intolerant of sloppiness | reject: probe | - |  | **FN** | probe phrase cut; a plain trait [probe reason] |
| 166 | IPIP | reject | overindulges in consumption | reject: probe | - |  | **FN** | probe phrase cut; a plain trait [probe reason] |
| 167 | IPIP | reject | shirks responsibilities | reject: probe | - |  | **FN** | probe phrase cut; a plain trait [probe reason] |
| 168 | IPIP | states | suspects partner of cheating | states | XSS |  | **FN-s** | the IPIP cluster is a jealous disposition; the present-tense label read as a belief now [generator hint; M1 readings] |
| 169 | IPIP | physical | perceives odors unusually | physical | XPP |  | **OK** | a sensory feature [M1 readings] |
| 170 | IPIP | kept | comfortable trading favors | trait | TTT | T | **OK** | a plain trait [M1 readings; Sonnet agrees] |
| 171 | IPIP | kept | con-artist minded | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 172 | IPIP | kept | favors strict discipline | trait | TTT |  | **OK** | a stance [M1 readings] |
| 173 | IPIP | kept | guided by feeling | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 174 | IPIP | kept | persistent after failure | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 175 | IPIP | kept | thrives on natural danger | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 176 | base model | reject | etc | reject: no_reading | XXX |  | **OK** | an abbreviation [M1 readings] |
| 177 | base model | kept | detailed | trait | TTT |  | **OK** | a style [M1 readings] |
| 178 | base model | kept | fun | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 179 | base model | kept | inspiring | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 180 | papers | reject | accepts claims uncritically | reject: probe | - |  | **FN** | probe phrase cut; credulity toward a user's framing [probe reason; generator hint] |
| 181 | papers | reject | behaves the same unwatched | reject: probe | - |  | **FN** | probe phrase cut; the corpus names the same disposition ([good even when unwatched](../../../data/traits/instructions/good_even_when_unwatched.json)) [probe reason; corpus] |
| 182 | papers | reject | forces it to pass | reject: no_reading | XXX |  | **OK** | a malformed label ("it") [M1 readings; generator hint] |
| 183 | papers | reject | fully committing | reject: no_reading | XXX |  | **OK** | too vague to use as written [M1 readings; generator hint] |
| 184 | papers | reject | misjudges own training | reject: probe | - |  | **FN** | probe phrase cut [probe reason] |
| 185 | papers | reject | overstating one's evidence | reject: probe | - |  | **FN** | probe phrase cut [probe reason] |
| 186 | papers | reject | oversteps into deciding | reject: probe | - |  | **BL** | probe phrase cut; the label needs its hint to be understood [probe reason; generator hint] |
| 187 | papers | reject | rigid overcorrection | reject: probe | - |  | **BL** | probe phrase cut; a noun phrase [probe reason; generator hint] |
| 188 | papers | reject | secretly underperforms | reject: probe | - |  | **FN** | probe phrase cut; sandbagging, the single-call rubric's own example (capability-hiding) [probe reason] |
| 189 | papers | reject | serves real interest | reject: no_reading | XXX |  | **OK** | a malformed label [M1 readings] |
| 190 | papers | roles | helps build weapons | roles | RRR |  | **FN** | read as a job in arms manufacture; an AI disposition, which Roger ruled traits, roles being exclusive identities (QUESTIONS 67) [M1 readings; Roger's ruling] |
| 191 | papers | roles | produces explicit sexual content | roles | RRR | R | **FN** | read as a pornographer's job; same ruling [M1 readings; Sonnet: roles; Roger's ruling] |
| 192 | papers | kept | accountable and transparent | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 193 | papers | kept | acts against its developer | trait | TXT |  | **OK** | an AI disposition [M1 readings] |
| 194 | papers | kept | honest task execution | trait | TTT |  | **OK** | a disposition (noun phrase) [M1 readings] |
| 195 | papers | kept | power-hungry | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 196 | papers | kept | respects privacy | trait | TTT |  | **OK** | a plain trait [M1 readings] |
| 197 | papers | kept | serves coercive power | trait | XTR |  | **OK** | an agent of oppressive authority; a three-way split went to trait [M1 votes] |
| 198 | papers | kept | transparent under oversight | trait | TTT |  | **OK** | an AI disposition [M1 readings] |

Tally: Allport-hi rejects 39 OK, 1 BL; Allport-hi tagged 26 OK, 1 FN-s, 1 MR, 2 BL; Allport-hi kept 18
OK, 1 FP, 1 BL; TDA rejects 11 OK, 1 FN; TDA tagged 8 OK, 2 FN-s, 1 MR, 1 BL; TDA kept 10 OK; Roget
rejects 10 OK; Roget tagged 5 OK, 1 MR; Roget kept 4 OK, 1 FP, 3 BL; WordNet 13 OK; IPIP rejects 2 OK,
4 FN; IPIP tagged 1 OK, 1 FN-s; IPIP kept 6 OK; base model 4 OK; papers rejects 3 OK, 5 FN, 2 BL; papers
roles 2 FN; papers kept 7 OK.

### 4b. Complete enumerations of the strata the sample flagged

Where the seeded sample found a pattern, or the stratum was small, I read every row.  Verdicts in the
same codes; full readings in each batch's results file ([papers](../../../data/candidates/filter/2026-10-11-papers_alignment_sweep/results.jsonl), [IPIP](../../../data/candidates/filter/2026-10-11-g600_ipip/results.jsonl), [TDA](../../../data/candidates/filter/2026-10-10-tda_censuses/results.jsonl), [Roget](../../../data/candidates/filter/2026-10-11-full_roget/results.jsonl)).

#### Alignment papers run: the 60 phrases the probe cut

| verdict | n | labels |
|---|---|---|
| **FN** | 54 | abets fraud; abets illegal activity; abets violence; accepts claims uncritically; acts differently when unwatched; acts the same unobserved; behaves differently when unobserved; behaves differently when unwatched; behaves the same unobserved; behaves the same unwatched; broadly misaligned (broad, but a disposition); circumvents oversight; circumvents restrictions; consistent across rewordings; consistent when unobserved; covertly evades oversight; covertly sabotages oversight; covertly subverts oversight; deferential to principals; defers without checking; deliberate underperformance (noun phrase); deliberately underperforms; distrusting its developer; editorializes unprompted; entrenches its own goals; evades oversight; fabricates false justifications; fabricates information; feigns alignment strategically; feigns ignorance; flattering agreeableness (noun phrase); flatters or conceals; flatters to please; hides AI's role; hides behavior until unwatched; honest helpfulness (noun phrase); intrudes on privacy; misjudges own training; open and aboveboard; overclaims certainty; overclaims from results; overstating one's evidence; performs for evaluators; rationalizes deception; sabotages decisions; sabotages its own update; sabotages its replacement; secretly sabotages; secretly underperforms; subverts its developer; subverts oversight; subverts oversight to persist; uncritical acceptance (noun phrase); underperforms across the board |
| **BL** | 6 | calibrates to requested level (needs its hint: level of what?); misbehaves in familiar formats (unclear without its hint); oversteps into deciding (needs its hint); political deceiver (a type of person, close to a role); rigid overcorrection (noun phrase, needs its hint); strategizing about its situation (vague) |

#### IPIP g600: the 13 phrases the probe cut

| verdict | n | labels |
|---|---|---|
| **FN** | 13 | compulsively checking; compulsively counts; convinced of own rightness; discontented with self; distrusts authority; inattentive to speech; intolerant of sloppiness; keeps confidences well; overindulges in consumption; prone to anhedonia; prone to sensory aversions (sensory, perhaps physical; not a non-word); shirks responsibilities; uncompromisingly honest |

#### Roget: the 2 phrases the probe cut

| verdict | n | labels |
|---|---|---|
| **OK** | 2 | grudging praise (a kind of praise; the trait word is grudging); maturely considered (said of decisions) |

#### Alignment papers run: the other 34 discards (30 turned away by the steps, 4 sent to roles)

| verdict | n | labels |
|---|---|---|
| **FN** | 18 | accepts being updated (corrigibility); accepts modification (corrigibility); accepts replacement (corrigibility); accepts shutdown (corrigibility); aids infrastructure attacks (Sonnet: trait); clings to own survival; enables surveillance; guards its own goal (read as a role); helps build weapons (read as a job); honors real intent; lies about actions; lies about its origins; preserves itself covertly; produces explicit sexual content (read as a job; Sonnet: roles); protects essential systems (read as a role); respects system authorization; shows true ability (the opposite of sandbagging); strategic deception (noun phrase, but plain) |
| **BL** | 12 | accurate self-understanding (noun phrase); acts on true values (vague); deceptive concealment (noun phrase); full effort (noun phrase); hidden trigger-dependent misbehavior (noun phrase; Sonnet: trait); honest context-fitted feedback (noun phrase); honest oversight (noun phrase, ambiguous); misses the requested level (needs its hint); preserves intent (coding-specific); protects civic participation; serves real intent (odd grammar); thorough scrutiny (noun phrase) |
| **OK** | 4 | forces it to pass (malformed: "it"); fully committing (too vague); serves real interest (malformed); trimming content (a task behaviour) |

#### TDA: all 29 rejects

| verdict | n | labels |
|---|---|---|
| **FN** | 3 | [good](../../../data/traits/instructions/good.json) (a corpus trait, morally good, turned away as pure praise); open-ended (a seed-queue trait, status done; the open-minded reading was secondary); unsly (from parts; Sonnet: trait) |
| **BL** | 3 | clear-cut ("direct, unambiguous in manner" is secondary); divulging (blurts out secrets, secondary; Sonnet: states); fretless (free of worry, from parts, rare; Sonnet agrees with the rejection) |
| **OK** | 23 | admirable (pure praise); awesome (pure praise); bendable; calculable; cautionary; cognitive (Sonnet agrees); competitory (probe); dissensualized (probe); flammable; great (pure praise); guilty; invidious; live; ministrative; nonvariant; overprompt; receiving; salubrious; scheduled; soft-shelled; terrific (pure praise); underogatory (probe); worthy (pure praise) |

#### TDA: all 6 sent to roles

| verdict | n | labels |
|---|---|---|
| **FN** | 1 | [young](../../../data/traits/instructions/young.json) (a corpus trait; sent to roles as an age) |
| **BL** | 2 | juvenile (an age; "childish" also common); matchmaking (a matchmaker's job, or a habit of pairing people off) |
| **MR** | 1 | important (status; better turned away) |
| **OK** | 2 | ministerial (an office); usurping (an act or a usurper) |

#### IPIP g600: the 9 other discards (4 turned away by the steps, 4 states, 1 physical)

| verdict | n | labels |
|---|---|---|
| **FN-s** | 1 | suspects partner of cheating (the cluster is a jealous disposition) |
| **BL** | 2 | minimally effortful (lazy, plain enough); thrill-seeking violence (noun phrase for a violent thrill-seeker) |
| **OK** | 6 | chronic unexplained symptoms (a health complaint); financially constrained (a circumstance; states is defensible); has legal troubles (a situation); inconsistent with parents (label unclear); lacks appetite (a bodily state); perceives odors unusually (sensory) |

### 4c. Reference labels on production rows

- **Corpus labels** (the generators re-proposed 376 of them; a corpus trait is a trait by definition,
  and decision 2 counts `state`, `physical` and `membership` as correct for one): TDA 318 of 320 correct
  (misses: [good](../../../data/traits/instructions/good.json) turned away as pure praise,
  [young](../../../data/traits/instructions/young.json) sent to roles as an age); Allport-hi 43 of 44
  ([narrative](../../../data/traits/instructions/narrative.json) turned away as stretched); IPIP 4,
  papers 1, base model 7, all correct.  **99.2%**, above the 95% target.  Of these, 13 TDA and 11
  Allport-hi labels went to states or physical, which decision 2 counts as correct, though
  [edgy](../../../data/traits/instructions/edgy.json) went to states in the wrong sense (nervous, not
  provocative).
- **Roger's marks** ([haiku55_verdict_disagreements_for_marks.md](../../trait_gap_generation/haiku55_verdict_disagreements_for_marks.md),
  [random_traits_for_marks.md](../../trait_gap_generation/random_traits_for_marks.md),
  [random_traits_for_marks_2.md](../../trait_gap_generation/random_traits_for_marks_2.md)) cover 30
  production rows: 18 of 19 kept rows agree (agile, passed, Roger marked physical); 7 of 11 discarded
  rows agree.  The four that do not: meritorious (turned away as praise; Roger: trait), supreme (roles;
  Roger: trait), [flourishing](../../../data/traits/instructions/flourishing.json) and presentable
  (states; Roger: trait, the mild kind).  The 600-word marks file
  ([haiku55_verdict_600_disagreements_for_marks.md](../../trait_gap_generation/haiku55_verdict_600_disagreements_for_marks.md))
  is unmarked.
- **Roger's expected outcomes** on the 99 test words
  ([split_test_words.jsonl](../../../data/candidates/validation/split_test_words.jsonl)): 26 production
  rows, 24 agree; decided and false passed where he expected turned away (FPs).
- **Opus** ([opus55_verdict_600](../../../data/candidates/filter/opus55_verdict_600/),
  [m1_r2_opus_audit](../../../data/candidates/filter/m1_r2_opus_audit/)): 73 production rows.  Kept 48
  of 51 agree (spectacular, splendid, splenetic: Opus turned away).  Discarded 16 of 22 agree: Opus
  passes vile (turned away as condemnation) and blissful, bone-dry, [edgy](../../../data/traits/instructions/edgy.json) and prime twice (states).
- **Roger's review decisions** (registry `review` blocks): only TDA has reached review.  Of the 204 TDA
  rows M1 passed that Roger decided, 168 were merged into a corpus trait, 35 accepted, 1 rejected
  (rhythmic): an FP rate of at most 0.5% on what reached him (CI 0.1 to 2.7%).  No discarded row has
  been reviewed.
- **Sonnet's random 10% on Allport-hi**, read by me where it differs from Haiku (Opus sided with Sonnet in
  27 of 38 such disagreements in [opus_audit_m1.md](../../trait_gap_generation/opus_audit_m1.md)):

| Haiku → Sonnet (random 10%, n) | my reading of the disagreements |
|---|---|
| trait → turned away (36 of 179 Haiku traits) | **FP 29**: boon, brimstone, buttery, copious, deficient, delicious, excruciating, fatal, fresh-water, gaming, hard-mouthed, ideal, masturbate, monumental, overloading, perennial, piecing, pulsating, regardless, revert, self-esteem, stunting, tosh, tried, unacceptable, unexplainable, unheard-of, unsuitable, winnable; **BL 7**: cabbage-head, excluding, exemplary, sectional, singular, strenuous, undeserving |
| turned away → trait (8 of 63 Haiku rejects) | **FN 2**: grab-all, shatter-brained; **BL 1**: dink; **OK 5**: creditable, daisy (a name), freeing, preserving, proof-proof |
| states → trait (16 of 92 Haiku states) | **FN-s 5**: blushing, chilly, nerve-shaken, overeating, ranting; **BL 3**: oppressed, out (openly gay, a membership), [isolated](../../../data/traits/instructions/isolated.json); **OK 8** |
| roles → trait (3 of 8 Haiku roles) | moderating (FN: tempering one's views), leader (BL), pathfinder (OK) |

Of the Haiku-kept rows on Allport-hi, Sonnet agreed on 84 of 96 where all three readings said trait
(87.5%) and on 35 of 83 where they did not (42%).

## 5. Rates

95% Wilson intervals; "implied" scales the sample rate to the stratum's size in the run.  FN counts clear
cases; FN-s (trait sent to states) and BL are given beside it.

| stratum | basis | FN | FN-s / BL | FN rate (CI) | implied FN in the run |
|---|---|---|---|---|---|
| Allport-hi rejects (681) | seeded 40 | 0 | BL 1 | 0% (0 to 8.8) | 0 (at most 60) |
| | Sonnet random, Haiku rejects 63 | 2 | BL 1 | 3.2% (0.9 to 10.9) | about 22 |
| Allport-hi tagged (1,112) | seeded 30 | 0 | FN-s 1, BL 2 | FN-s 3.3% (0.6 to 16.7) | about 37 FN-s |
| | Sonnet random, Haiku states 92 | 0 | FN-s 5, BL 3 | FN-s 5.4% (2.3 to 12.1) | about 47 FN-s |
| TDA rejects (29) | all 29 | 3 | BL 3 | 10.3% (3.6 to 26.4) | 3 |
| TDA tagged (180) | seeded 12; roles all 6 | 1 ([young](../../../data/traits/instructions/young.json)) | FN-s 2 (seeded); BL 2 (roles) | FN-s 16.7% (4.7 to 44.8) | about 29 FN-s; 1 FN |
| Roget discards (122) | seeded 16 | 0 | MR 1 | 0% (0 to 19.4) | 0 seen; light-fingered (roles, Sonnet: trait) is one outside the sample |
| WordNet discards (17) | seeded 7 | 0 | | 0% (0 to 35.4) | 0 |
| IPIP discards (22) | all 22 | 13 | FN-s 1, BL 2 | 59.1% (38.7 to 76.7) | 13 |
| base model discard (1) | all 1 | 0 | | | 0 |
| papers discards (94) | all 94 | 72 | BL 18 | 76.6% (67.1 to 84.0) | 72 |
| **the probe's phrase cuts (75)** | all 75 | 67 | BL 6 | 89.3% (80.3 to 94.5) | 67 |

| stratum (kept) | basis | FP | BL | FP rate (CI) | implied FP in the run |
|---|---|---|---|---|---|
| Allport-hi (1,745) | seeded 20 | 1 | 1 | 5.0% (0.9 to 23.6) | about 87 |
| | Sonnet random, Haiku traits 179 | 29 | 7 | 16.2% (11.5 to 22.3) | about 283 |
| TDA (1,779) | seeded 10 | 0 | 0 | 0% (0 to 27.8) | |
| | Sonnet random, 176 | at most 3 (Sonnet differs on 3; I read overbitter as a trait and recondite as BL) | | at most 1.7% (0.6 to 4.9) | at most about 30 |
| | Roger's review, 204 | 1 | | 0.5% (0.1 to 2.7) | |
| Roget (123) | seeded 8 | 1 | 3 | 12.5% (2.2 to 47.1) | about 15 (62 with BL) |
| WordNet (62) | seeded 6 | 0 | 0 | 0% (0 to 39.0) | at least 3 known: Sonnet turned away noncommercial, separate and tolerable, and I read all three as FP |
| IPIP (172) | seeded 6 | 0 | 0 | 0% (0 to 39.0) | Sonnet agrees on 17 of 18 |
| base model (17) | seeded 3 | 0 | 0 | | |
| papers (286) | seeded 7 | 0 | 0 | 0% (0 to 35.4) | Sonnet agrees on all 29 |

**Over the seven runs**: about 110 clear FNs among 2,258 discards (5%).  85 of them are phrase labels
from IPIP and the alignment sweep, which make up only 116 of the discards.  There are roughly 70 to 80
FN-s besides.  On single words the clear-FN rate is about 1% of discards (TDA 4 of 209, Allport-hi
about 22 of 1,793).  FPs are concentrated in Allport-hi (about 280) and in the words passed on one
reading of three.

## 6. Verdict

**Single words: doing what was intended, about as well as these samples can detect.**  The turn-away
rules reject non-words, names, nouns for things, acts, pure praise and archaic compounds.  Roger's bar
("too unclear to put in the corpus") is met in every reject I read, bar about one in thirty.  The
remaining errors are on the trait/state line (the -ing participles: 36% of Allport-hi's -ing words go to
states against 19% of its other words) and in a few rubric-consistent calls that the corpus overrules
([good](../../../data/traits/instructions/good.json), [young](../../../data/traits/instructions/young.json)).  The Allport-hi FP rate (about 16%) is the price of the vote rule, and the data support
the rule under Roger's weights.  Words passed on split votes are about 42% traits by Sonnet's reading.
Passing a word with probability p of being a trait costs (1 − p) × 1 in his weights, and turning it away
costs p × 3; passing is cheaper whenever p is above 25%, and 42% is well above.

**Phrase labels: mostly not doing what was intended; fixable.**  The probe treats "is it a single word"
as "is it a known word" and was never tested on phrases.  It ignores the label's form, which it should
depend on.  The established check's ordinary-speech sentence ("she is <label>") assumes an adjective or
noun.  Both parts work on single words, so the defect is in where they are applied, not in their text.

**Thresholds.**  The vote rule's unanimity-to-reject is supported (above).  The probe band's 2.5 has no
derivation and, for phrases, no meaning: a phrase's rarest content word ("abets", "underperforms") says
nothing about whether the phrase is understood.  The 10% second-opinion share measures the error rate but
fixes nothing: the tripwire fired on Allport-hi at 32%, and, as built, the run went on unchanged.

## 7. Proposals

| # | proposal | cost | expected change | evidence that would settle it |
|---|---|---|---|---|
| 1 | **Keep phrases out of the definition probe**: send only single-word labels, or send each content word below 2.5 on its own ("underperforms") instead of the whole label.  A payload change; the probe's pinned text is untouched | $0 to build; re-judging the 75 cuts here and the 49 in the two earlier alignment batches through M1 and M3 is about $2 in batches | FN among the probe's phrase cuts from 89% to near 0; about 67 traits back in these runs (some will be M3 duplicates of each other, such as the six "behaves the same / differently when unwatched" variants) | the re-run's outcomes on those rows |
| 2 | **Phrase labels in the verdict steps**: either let the Sonnet second opinion decide every turned-away or roles outcome from the phrase generators (IPIP, alignment sweep), or render a verb-phrase label as "someone who <label>" in the step 1 and established payloads.  The first is code only; the second changes what the model reads (Roger's rubric text) | about $0.30 in batches for this run's 34 rows; Opus on the same 34 as a reference, about $1 | papers' non-probe FN from 18 of 34 to a handful; Sonnet already passed the two it saw (aids infrastructure attacks, hidden trigger-dependent misbehavior) | Sonnet and Opus outcomes on the 34 rows of 4b, against these verdicts or Roger's marks on 20 of them |
| 3 | **Route alignment-sweep roles to review**, not the roles list (QUESTIONS 67: AI dispositions are traits) | $0 | 4 rows here (guards its own goal, helps build weapons, produces explicit sexual content, protects essential systems) | Roger's yes |
| 4 | **Run the states pass on the 900 unjudged states rows** (Allport-hi 863, Roget 26, WordNet 7, IPIP 4) **and the physical pass on the 127 unjudged physical rows** | states pass about $0.20 (states_tda_1: 150 rows for $0.023); physical gloss plus M3 about $1.5 | turns the states hold back into the designed route: on TDA 81% of states rows left the hold (lasting 12, predisposition 27, renamed 82, role 1; held 28) | the pass's routes on Allport-hi |
| 5 | Optional: **make Sonnet decide words whose three readings split** (Allport-hi: 666 passed and 436 discarded on split votes, 1,102 words) | about $8 in batches for Allport-hi | Allport-hi FP among kept from about 16% to about 8%, since Sonnet agrees with unanimous passes 87.5% of the time and with split ones 42%; some added FN, since Sonnet leans toward turning away ([opus_audit_m1.md](../../trait_gap_generation/opus_audit_m1.md)) | Opus on 100 split-vote Allport-hi words, about $3 |
| 6 | No change for the -ing participles and the corpus-overruled words ([good](../../../data/traits/instructions/good.json), [young](../../../data/traits/instructions/young.json)): the states pass is the designed recovery route for the first, and M3 stage 0 catches corpus labels | $0 | | |

For gate 1: the hyphen split gives archaic Allport compounds (cow-baby, kill-courtesy, weak-hinged,
blue-devil) the Zipf of their parts (4.1 to 4.3), so they reach the "hi" stage and M1.  M1 turns them
away correctly; the cost is only the calls, about $0.003 each.

## 8. The holding lists: is "tagged → held" a discard in practice?

Registry, last row per key (all runs, not only the seven):

| list | rows | with a pass judgement | without | what reaches them |
|---|---|---|---|---|
| states | 1,145 held (+71 released) | 245 (renamed 148, held 97); the 71 released are out of the hold | **900**: Allport-hi 863, Roget full 26, WordNet full 7, IPIP 4 | the states pass ([states_pass.py](../../../assistant_axis/gapgen/states_pass.py)), not yet run on these; then Roger's name confirmation ([promote.py:175-202](../../../assistant_axis/gapgen/promote.py#L175)) |
| physical | 199 | 72 with a physical gloss | **127**: Allport-hi 116, WordNet 7, Roget 3, IPIP 1 | the physical pass ([physical_pass.py](../../../assistant_axis/gapgen/physical_pass.py)), M3 and review; promoted only by name |
| roles | 171 (4 of them sent there by the states pass) | none | 171 | nothing: "read by hand" (QUESTIONS 1); `promote` refuses them.  Includes 10 corpus roles from Allport-hi ([ancient](../../../data/roles/instructions/ancient.json), [builder](../../../data/roles/instructions/builder.json), [chief](../../../data/roles/instructions/chief.json), [child](../../../data/roles/instructions/child.json), [comedian](../../../data/roles/instructions/comedian.json), [composer](../../../data/roles/instructions/composer.json), [organizer](../../../data/roles/instructions/organizer.json), [subordinate](../../../data/roles/instructions/subordinate.json), [virtuoso](../../../data/roles/instructions/virtuoso.json), [witch](../../../data/roles/instructions/witch.json)) |
| nationalities | 31 | none | 31 | nothing by rule (QUESTIONS 1 and 81); a separate memberships track is a TODO |

So states and physical are deferrals with a working pass behind them, and the deferral has not yet been
worked off for the three newest runs.  Roles and nationalities are discards in practice, by Roger's
decision.  For roles that is cheap, since most of what lands there is a role.  My sample has 12 roles
rows: 6 right, 2 better turned away, 2 borderline, and the 2 alignment phrases.  The exceptions that
matter are the alignment phrases (proposal 3) and a few traits with an occupational or age first reading
([young](../../../data/traits/instructions/young.json), light-fingered, moderating, supreme).

## Files

- Code: [filter.py](../../../assistant_axis/gapgen/filter.py), [filter_rubric.py](../../../assistant_axis/gapgen/filter_rubric.py),
  [split.py](../../../assistant_axis/gapgen/split.py), [split_rubrics.py](../../../assistant_axis/gapgen/split_rubrics.py),
  [split_runner.py](../../../assistant_axis/gapgen/split_runner.py), [freq.py](../../../assistant_axis/gapgen/freq.py),
  [promote.py](../../../assistant_axis/gapgen/promote.py), [traithood_filter.py](../../../data_analysis/gap_generation/traithood_filter.py),
  [split_cli.py](../../../data_analysis/gap_generation/split_cli.py); rubrics in
  [rubrics/](../../trait_gap_generation/rubrics/) ([versions.json](../../trait_gap_generation/rubrics/versions.json)).
- Records: the seven batches linked in section 3; [registry.jsonl](../../../data/candidates/registry.jsonl);
  the Allport-hi candidates with their Allport-Odbert columns,
  [candidates.jsonl](../../../data/candidates/runs/censuses/2026-10-11-allport_hi/candidates.jsonl);
  the states pass runs [states_tda_1](../../../data/candidates/states_pass/states_tda_1/) and
  [states_v4_pilot](../../../data/candidates/states_pass/states_v4_pilot/).
- References: [data/candidates/validation/](../../../data/candidates/validation/),
  [opus55_verdict_600](../../../data/candidates/filter/opus55_verdict_600/),
  [m1_r2_opus_audit](../../../data/candidates/filter/m1_r2_opus_audit/), the marks files of section 4c.
- Scratch scripts (in `/tmp`, cleared on reboot; the selection rule above is complete without them):
  [extract.py](/tmp/claude-501/m1audit/extract.py), [sample.py](/tmp/claude-501/m1audit/sample.py),
  [verdicts.py](/tmp/claude-501/m1audit/verdicts.py), [enum_verdicts.py](/tmp/claude-501/m1audit/enum_verdicts.py),
  [rand2.py](/tmp/claude-501/m1audit/rand2.py) (the second opinion's random 10%), [probe.py](/tmp/claude-501/m1audit/probe.py).
