# Gate audit #2: the Roget and WordNet selection

Written 2026-10-12 by an Opus agent, following the protocol in [README.md](./README.md).  The audit was read-only: there were no paid calls, no downloads and no model loads.  Every number below was reproduced offline with the repository's own functions: the harvest code in [harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py), the WordNet code in [wn_clusters.py](../../../assistant_axis/gapgen/generators/roget/wn_clusters.py), the Zipf floor in [freq.py](../../../assistant_axis/gapgen/freq.py), and the local Open English WordNet under [data/external/wn](../../../data/external/wn/).  The inputs were the tracked files under [data/candidates/roget/](../../../data/candidates/roget/), the corpus and queue as they are today, the registry ([registry.jsonl](../../../data/candidates/registry.jsonl), last row per key, 8,061 keys) and the census table ([census_table.jsonl](../../../data/candidates/censuses/census_table.jsonl)).

**Terms.**
- **M1** is the trait-hood filter; **M3** is the novelty check.  The **registry** holds one row per word, with every generator that proposed it.  These are defined in [escalations.md § Terms](../escalations.md#terms).
- A Roget **head** is a numbered thesaurus entry, such as 604 Resolution.  A head's adjectives come in **semicolon groups** of near-synonyms.
- A **gap head** is a head in scope that no corpus trait has as its primary head.  The coverage map sorts the in-scope heads into **gap classes**: pair_completion, pair_empty, singleton_empty and queued_only are the gap heads; partly_covered, covered and crowded (three or more primaries) are not.
- The **head-scope rating** is a Haiku 5.5 rating of whether a head's adjectives describe character: 2 most, 1 some, 0 few or none.
- **AO I to IV** are the four Allport-Odbert (1936) columns recorded in the census table.  Column I holds the stable personal traits, II temporary states, III social evaluations, and IV the rest (physical, capacities and so on).  It is the only human-made trait label available for words no generator submitted.
- **Trait-new** is the reference label: M1 says trait and M3 says new.

## Verdict in brief

| part of the gate | verdict | the one number that matters |
|---|---|---|
| Head selection: which heads are harvested (gap classes, the head-scope skip, the Class I-III scope) | **Doing what was intended, but improvable**, and the improvement belongs in the coverage report rather than in the harvest. | Covered heads hold almost as many new traits as gap heads.  Among words the censuses also submitted, 54% are trait-new in the selected heads against 41-43% in covered, crowded and partly covered heads.  The selection still loses almost nothing: the trait-new words it discards are already in the registry from the censuses, and **0 of 100** unregistered discards read by the agent are new traits. |
| The Roget Zipf checks: `hard_reject` and the second check `fi.zipf_min < zipf_hard` | **Doing what was intended ([QUESTIONS](../../trait_gap_generation/QUESTIONS.md) 42: "cut is 1.5"), about as well as possible.**  One rule inconsistency is left for Roger to settle. | The checks remove 144 words, 25 of them trait words, but **only 12 would ever have become candidates** (3 trait words, 4 borderline).  Every other removed word shares its semicolon group with a more frequent near-synonym, and the harvest takes only one word per group, the most frequent.  [Review 5 D4](../escalations.md#review-5-d4-the-roget-harvests-second-zipf-check-drops-the-negating-prefix-rescues)'s fix would change **4** candidates, not 77. |
| The WordNet lemma selection (closure roots, depth, the floor, the antonym route) | **Doing what was intended, but improvable.** | The depth bound of 3 and the Zipf floor discard words that are *better* than the kept ones: 97% (depth 4-6) and 62% (floor) are traits, against 91% of the kept closure words.  About 20 of them are new to the pipeline, for under $1. |

## 1. The rule, from the code

**Scope and gap classes** ([coverage.py](../../../assistant_axis/gapgen/generators/roget/coverage.py)):
- The heads in scope are those numbered 450 or above (`DISPOSITIONAL_MIN`, [parse.py](../../../assistant_axis/gapgen/generators/roget/parse.py):580).  The rest of the scope is the Class I-III heads that `restricted_class_i_iii` ([coverage.py](../../../assistant_axis/gapgen/generators/roget/coverage.py):92-116) brings in: a head in which an existing or active-queue label has an `exact_adj` or `derived_adj` lexical hit *and* where that label's sense sits.  The scope is assembled at [coverage.py](../../../assistant_axis/gapgen/generators/roget/coverage.py):139.
- `gap_class` ([coverage.py](../../../assistant_axis/gapgen/generators/roget/coverage.py):119-128) sorts the in-scope heads.  A covered head with `n_existing >= CROWDED_MIN` (3, line 47) is crowded.  An empty head is pair_completion when its opposed head is covered, pair_empty when its opposed head is not, and singleton_empty when it has no opposed head.
- `HARVEST_CLASSES` (line 46) is pair_completion, pair_empty, singleton_empty and queued_only.

**Head selection** ([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py)):
- `gap_heads` and `select_heads` ([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):371-388) return every head whose gap class is in `cfg.classes`.  `--every-nth` thins the list for the pilot only.
- A selected head with head-scope rating 0 is skipped ([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):421-426).  Its would-be words are counted as `not_character`, and its other drops, its Zipf drops included, are not counted anywhere.
- Heads outside the scope, and in-scope heads that are not gap heads, are never opened.  The run does not record their words.

**Per head** (`harvest_head`, [harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):148-208), for each semicolon group of the `Adj` block:
1. The checks run in this order:
   - items over two words are dropped;
   - so are items that start or end in a function word;
   - so are capitalised items that WordNet does not know in lower case;
   - so are corpus or queue stems, and stems already taken from this head.
2. Then comes the Zipf drop, at [harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):185-188, with `zipf_hard = 1.5` set at line 71:

   ```python
   fi = zipf_info(item, zipf_fn=zipf)
   if fi.hard_reject or fi.zipf_min < cfg.zipf_hard:
       drops["zipf_hard"] += 1
   ```

3. The group's **representative** is its highest-Zipf survivor ([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):194-196).  Every other survivor counts as `not_representative`.
4. A head keeps at most 10 representatives, ranked by `zipf + 0.3 (if WordNet has it as an adjective) - 0.15 x group index` (the cap, [harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):198, 202-205).

Two consequences for the Zipf check:
- `zipf_info` is called with no `gloss_hint`, `curated` or `familiarity` argument.  The only rescue it can grant is therefore the negating prefix ([freq.py](../../../assistant_axis/gapgen/freq.py):114-125).  For a rescued word `hard_reject` is False, but `zipf_min < 1.5` still holds, so the second condition drops it.  `hard_reject` implies `zipf_min < 1.5`, so the first condition adds nothing.  **The effective rule is: drop every word whose rarest content word is below Zipf 1.5.**
- M1 treats the same words differently.  It calls `zipf_info(..., gloss_hint=bool(it.intended_sense))` ([filter.py](../../../assistant_axis/gapgen/filter.py):264), where the intended sense is the row's first gloss hint (`items_from_records`, [filter.py](../../../assistant_axis/gapgen/filter.py):118-129, through `first_gloss_hint` in [registry.py](../../../assistant_axis/gapgen/registry.py):166).  Every Roget and WordNet candidate carries a gloss hint, so **M1 would send every one of these words to the probe** under rule 1b route 2 (or route 1 first, for a negating prefix).

**The WordNet stream** ([wn_clusters.py](../../../assistant_axis/gapgen/generators/roget/wn_clusters.py)):
- The closure starts from five hand-picked OEWN noun senses: trait, disposition, temperament, attitude and character (`TRAIT_ROOT_SYNSETS`, lines 40-41).  The comment there records that the other senses of character, and quality, were left out on purpose.
- `trait_closure` (208-231) walks hyponyms breadth-first to `max_depth`.  The depth is 3, from `HarvestConfig.wn_closure_depth` ([harvest.py](../../../assistant_axis/gapgen/generators/roget/harvest.py):73), passed in at [roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py):940-941.  No derivation of the value is recorded.
- `harvest_trait_closure` (291-320):
  - it skips the roots themselves (depth 0);
  - it takes `derivational_adjs` (195-206), the adjectives linked by derivation from *this synset's own* senses;
  - it drops multiword adjectives, corpus, queue and antonym-route stems, and anything `_freq_ok` rejects (258-261).
- `_freq_ok` is `not hard_reject`.  **Unlike the Roget harvest, it keeps the negating-prefix rescues**, but it does not apply the gloss-hint route either.
- The antonym route (`harvest_wn_antonyms`, 264-288) takes the WordNet antonyms of every adjective sense of an existing label that has no partner file.

## 2. The intent

- **Heads.**  [Plan 02](../../trait_gap_generation/02_roget_wordnet.md) § 1: "Mapping our labels onto heads gives a per-head coverage report whose empty heads are gaps *by concept*".  § 3.5: "Harvest pair candidates: for gap heads, take adj-list items ...".  § 4 foresaw the grain problem: it "Under-produces: ... fine intra-head distinctions ([cautious](../../../data/traits/instructions/cautious.json) vs [risk-averse](../../../data/traits/instructions/risk_averse.json) both land in 864 Caution)".  [Coding plan 02](../../trait_gap_generation/coding_plan_02_roget_wordnet.md) § 10, readout A, lists "which gap classes the harvest includes (`queued_only` in or out)" as Roger's decision.  **I found no record of that decision**; the code's default of four classes is what ran.
- **Class I-III scope.**  [QUESTIONS](../../trait_gap_generation/QUESTIONS.md) 40, answered 2026-10-08 ("SG"): "a Class I-III head enters only where a label's own sense sits (99 heads)".
- **Head scope.**  QUESTIONS 44, answered 2026-10-08 ("The Haiku test SG"): the harvest skips heads rated 0, "few or none of its adjectives describe a person's character".
- **Zipf.**
  - Coding plan 02 § 1: "items with `hard_reject` ... are dropped at harvest and counted; the probe band ... is flagged, not dropped".
  - QUESTIONS 42: "the harvest uses the platform's value (48 words cut in the pilot), so the filter's probe sees the 1.5-2.5 band.  Status: **Correct, cut is 1.5**".
  - [decisions_m1.md](../../trait_gap_generation/decisions_m1.md) § 1, sub-question 1b, approved "all three": a word below 1.5 goes to the probe when (1) it is formed by a negating prefix from a word at or above the floor, (2) "it arrives with a gloss hint, that is, the generator says which sense it means", or (3) it comes from a curated source.  The stated rationale is "The floor is there to stop dictionary junk, and none of these routes carries dictionary junk."
  - [freq.py](../../../assistant_axis/gapgen/freq.py)'s docstring calls Roget and WordNet "a dictionary walk", but only to exclude them from route 3.
  - [Plan 14](../../trait_gap_generation/14_traithood_filter_registry.md) § 11.3: "Zipf floor: **not a gate.**"
  - QUESTIONS 42 settles the 1.5 line for the harvest.  **Nothing settles whether routes 1 and 2 apply there.**  Review 5 D4 assumed route 1 does.
- **WordNet.**  Plan 02 § 3.6 names the five roots and gives no depth.  Coding plan 02 § 8 says only "bounded depth".  **The value 3 has no recorded derivation.**

## 3. The recorded discard, reproduced

**Roget, full run** ([run.json](../../../data/candidates/runs/roget/2026-10-11-full/run.json), [harvest_counts.json](../../../data/candidates/runs/roget/2026-10-11-full/harvest_counts.json), [harvest_report.md](../../../data/candidates/runs/roget/2026-10-11-full/harvest_report.md)):

| step | recorded | reproduced today |
|---|---|---|
| heads parsed / in scope (576 dispositional + 99 Class I-III) / out of scope | 1,044 / 675 / 369 | same |
| in-scope heads not selected (not gap heads) | 400: covered 252, crowded 83, partly 65 (rated-0 heads included) | same |
| gap heads selected / skipped as rated 0 / giving words | 275 / 119 / 87 | same |
| candidates ([candidates.jsonl](../../../data/candidates/runs/roget/2026-10-11-full/candidates.jsonl)) | 475 (448 distinct) | 473 |
| drops: not_representative / not_character / too_many_words / **zipf_hard** / cap / known_label / function_word / proper / repeat | 663 / 362 / 195 / **144** / 141 / 72 / 55 / 18 / 1 | 656 / 362 / 195 / **144** (94 `hard_reject` + 50 second check) / 141 / 81 / 55 / 18 / 1 |
| Zipf drops inside the 119 skipped heads (not recorded) | - | 99 (75 + 24) |

The reproduction differs only through the 9 labels added to the corpus or queue since 2026-10-11.  They now drop earlier as known labels: aimless, crude, derisive and parasitic are no longer candidates, while grotesque and purposeless now become their groups' representatives.

**Review 5 D4 counted 77 negating-prefix rescues dropped by the second check; today the count is 74** (50 in harvested heads, 24 in skipped heads).  The difference fits the same 9 labels.

**WordNet, full run** ([run.json](../../../data/candidates/runs/wn_clusters/2026-10-11-full/run.json), [wn_items.jsonl](../../../data/candidates/runs/wn_clusters/2026-10-11-full/wn_items.jsonl)):
- 468 candidates: antonym route 102; closure 366 (depth 1: 46, depth 2: 185, depth 3: 135).  Reproduced: 465 (disobedient, masochistic and morose are now known).
- **The run records no drop counts.**  Reconstructed from the closure:
  - 564 synsets to depth 3, 559 of them below the roots;
  - **198 of the 559 have no derivational adjective**;
  - occurrences dropped as known stems 128, as antonym-route stems 12, by the Zipf floor **40**;
  - the antonym route dropped 42 known stems and 2 words by the floor.
- Deeper closures add 84 adjectives at depth 4 and **117 at depth 6**, where the closure saturates.

**What M1 and M3 decided about what was submitted** (registry, last row per key):

| run | rows | M1: trait / states / physical / roles / turned away | M3: new / covered | review |
|---|---|---|---|---|
| roget 2026-10-11-full | 448 | 284 / 71 / 9 / 7 / 77 | 213 / 82 | merged_into 14, accepted 4 |
| wn_clusters 2026-10-11-full | 468 | 414 / 35 / 12 / 1 / 6 | 226 / 198 | merged_into 20, accepted 3 |

The pilot (`2026-10-08-pilot`, [readout.md](../../../data/candidates/runs/roget/2026-10-08-pilot/readout.md)) ran the same code on every fifth gap head before the head-scope check existed: 185 Roget words and 48 cut by Zipf.  Its heads are a subset of the full run's, so the full run stands for both here.

## 4. Samples, read by the agent

**What a "discard" means for head selection.**  An unselected head is never harvested, so I rebuilt what each unselected head *would* have given under the same per-head rules: one word per group and the cap of 10.

| heads | count | would-be words | in the registry from other generators | of those, trait-new (reference) | not in the registry | of those, AO I |
|---|---|---|---|---|---|---|
| selected (kept) | 87 | 473 | 473 (all; Roget's own rows) | 219 | 0 | - |
| not gap: covered | 234 | 1,477 | 921 | 362 | 556 | 6 |
| not gap: crowded | 82 | 580 | 438 | 183 | 142 | 4 |
| not gap: partly covered | 58 | 327 | 201 | 85 | 126 | 2 |
| rated 0, skipped | 115 | 362 | 174 | 70 | 188 | 1 |
| out of scope (Class I-III) | 324 | 1,539 | 536 | 213 | 1,003 | 9 |
| **all discarded** | 813 | **4,285** | **2,270** | **913** | **2,015** | **22** |

The registered rows came overwhelmingly from the censuses (TDA and Allport-hi), so they are a person-descriptive subset.  To compare like with like, restrict every group to rows the censuses also submitted.  Trait-new is then **54%** in the selected heads (148 of 272), **41%** in covered heads (342 of 844), 43% in crowded heads (177 of 410), 43% in partly covered heads (78 of 180), 40% out of scope (199 of 494) and 52% in heads rated 0 (58 of 112).  M3's "new" rate among M1 traits falls from 70% in gap heads to 53-61% in the not-gap and out-of-scope heads.  **The head-level coverage carries only a weak signal about word-level novelty.**

### 4a. Which heads were not selected, and what they hold

The 15 unselected heads with the most trait-new words (reference labels):

| head | why not selected | rating | its corpus traits (primary) | would-be words | trait-new | the trait-new words |
|---|---|---|---|---|---|---|
| 544 Falsehood | covered | 2 | [deceitful](../../../data/traits/instructions/deceitful.json), [dishonest](../../../data/traits/instructions/dishonest.json) | 10 | 8 | false, hollow, artificial, hollow-hearted, evasive, disingenuous, hypocritical, plausible |
| 880 Vanity | covered | 2 | [grandiose](../../../data/traits/instructions/grandiose.json), [narcissistic_dark_tetrad](../../../data/traits/instructions/narcissistic_dark_tetrad.json) | 9 | 8 | forward, self-confident, vain, inflated, egotistical, unabashed, unconstrained, priggish |
| 939 Probity | crowded | 2 | [good_even_when_unwatched](../../../data/traits/instructions/good_even_when_unwatched.json), [honest](../../../data/traits/instructions/honest.json), [honorable](../../../data/traits/instructions/honorable.json), [honorable_while_playing](../../../data/traits/instructions/honorable_while_playing.json) | 10 | 8 | right, true, upright, constant, nice, frank, right-minded, high-minded |
| 702 Cunning | crowded | 2 | [calculating](../../../data/traits/instructions/calculating.json), [machiavellian_dark_tetrad](../../../data/traits/instructions/machiavellian_dark_tetrad.json), [scheming](../../../data/traits/instructions/scheming.json), [sly_hexaco](../../../data/traits/instructions/sly_hexaco.json) | 10 | 7 | subtle, cunning, profound, artificial, intriguing, tricky, knowing |
| 713 Discord | covered | 1 | [disagreeable](../../../data/traits/instructions/disagreeable.json) | 9 | 7 | controversial, discordant, disagreeing, torn, quarrelsome, litigious, factious |
| 885 Insolence | crowded | 2 | [arrogant](../../../data/traits/instructions/arrogant.json), [condescending](../../../data/traits/instructions/condescending.json), [flippant](../../../data/traits/instructions/flippant.json), [sassy](../../../data/traits/instructions/sassy.json) | 10 | 7 | forward, high-handed, arbitrary, devil-may-care, bluff, shameless, brazen |
| 944 Virtue | covered | 2 | [moral](../../../data/traits/instructions/moral.json) | 10 | 7 | right, correct, pure, virtuous, dutiful, commendable, exemplary |
| 24 Disagreement | out of scope | - | - | 10 | 6 | incompatible, disagreeing, intrusive, inappropriate, discordant, unfit |
| 460 Neglect | crowded | 2 | [careless](../../../data/traits/instructions/careless.json), [careless_big_five](../../../data/traits/instructions/careless_big_five.json), [careless_hexaco](../../../data/traits/instructions/careless_hexaco.json), [health_negligent](../../../data/traits/instructions/health_negligent.json) | 10 | 6 | neglecting, thoughtless, inconsiderate, remiss, unguarded, offhand |
| 518 Intelligibility | covered | 1 | [clear](../../../data/traits/instructions/clear.json), [transparent](../../../data/traits/instructions/transparent.json) | 9 | 6 | plain, graphic, lucid, intelligible, luminous, unequivocal |
| 606 Obstinacy | covered | 2 | [obsessive](../../../data/traits/instructions/obsessive.json), [unyielding](../../../data/traits/instructions/unyielding.json) | 10 | 6 | stubborn, pig-headed, immovable, perverse, sullen, wayward |
| 704 Difficulty | partly covered | 1 | - | 10 | 6 | formidable, troublesome, awkward, embarrassing, intricate, intractable |
| 907 Malevolence | crowded | 2 | [malevolent](../../../data/traits/instructions/malevolent.json), [malicious](../../../data/traits/instructions/malicious.json), [malign](../../../data/traits/instructions/malign.json), [sadistic](../../../data/traits/instructions/sadistic.json) | 10 | 6 | cold, malignant, grinding, cruel, fell, brutal |
| 255 Smoothness | out of scope | - | - | 8 | 5 | smooth, soft, polished, slick, silky |
| 324 Softness | partly covered | 2 | - | 10 | 5 | soft, pliable, yielding, lithe, tractable |

These are the trait core of the thesaurus.  One Roget head spans ten or more distinct traits, so a single primary label does not cover it.  Some of the reference "new" calls are generous: true, right, plain and graphic carry glosses the censuses gave them, not the head's sense.  The agent's sense check in § 4b accepts 6 of the 8 trait-new reference calls it read.

A random four heads per category (seed 20261012; \* marks trait-new by reference):

| category | head | gap class | rating | its corpus traits | would-be words |
|---|---|---|---|---|---|
| rated 0 | 660 Restoration | pair_empty | 0 | - | restored, restoring, convalescent, restorative, remedial, rejuvenated, recoverable, reparative |
| rated 0 | 462 Answer | pair_completion | 0 | - | answering, responsive\* |
| rated 0 | 908 Malediction | singleton_empty | 0 | - | cursed |
| rated 0 | 469 Qualification | singleton_empty | 0 | - | qualified\*, qualifying, conditional\* |
| not gap | 10 Irrelation | partly_covered | 1 | - | foreign, unrelated, arbitrary\*, purpose, forced, disconnected, irrelevant, adrift, heterogeneous, incidental |
| not gap | 181 Region | crowded | 1 | [eastern_hemisphere](../../../data/traits/instructions/eastern_hemisphere.json), [parochial](../../../data/traits/instructions/parochial.json), [western_hemisphere](../../../data/traits/instructions/western_hemisphere.json) | local |
| not gap | 859 Hopelessness | covered | 1 | [despairing](../../../data/traits/instructions/despairing.json) | gone, past hope, given up, threatening\*, broken hearted, ruined, beyond remedy, irreversible, unpromising, incorrigible\* |
| not gap | 836 Cheerfulness | crowded | 2 | [cheerful](../../../data/traits/instructions/cheerful.json), [joyful](../../../data/traits/instructions/joyful.json), [lighthearted](../../../data/traits/instructions/lighthearted.json) | smiling, light, bully, cheery, bright, blithe, allegro, lively, spirited, debonair\* |
| out of scope | 139 Irregularity of recurrence | - | - | - | irregular\*, variable, rambling, spasmodic\* |
| out of scope | 242 Symmetry | - | - | - | well set, regular\*, classic\*, parallel, branching, fuji-shaped |
| out of scope | 358 Inorganization | - | - | - | mineral, inorganic |
| out of scope | 129 Infant | - | - | - | baby, childish\*, newborn, infantile, puerile |

### 4b. Word sample: head selection, 62 discarded and 40 kept

**Selection.**  `random.Random(20261012)` over the would-be words, sorted by (head, word) within each stratum.  The strata:
- discarded: not gap heads, unregistered 20 and registered 10; out of scope, unregistered 12 and registered 6; rated 0, unregistered 8 and registered 6;
- kept: 30 words from heads rated 1 and 10 from heads rated 2.

**Verdict.**  The verdict is against the intent: Y if the word, *in this head's sense*, is a person trait the corpus lacks.  Reference labels are listed first.  The verdict is the agent's own reading.  "unreg" means no generator submitted the word, so the registry has no row for it.

| stratum | head (class; gap class; rating) | word | Zipf | reference | agent's verdict |
|---|---|---|---|---|---|
| not_character/unreg | 671 Escape (V; singleton_empty; rating 0) | fled | 4.05 | not in registry | **N** past participle of flee; no person disposition |
| not_character/unreg | 184 Location (II; pair_empty; rating 0) | posited | 2.77 | not in registry | **N** said of propositions |
| not_character/unreg | 470 Possibility (IV; pair_empty; rating 0) | theoretically possible | 3.64 | not in registry | **N** said of events |
| not_character/unreg | 184 Location (II; pair_empty; rating 0) | domesticated | 3.17 | AO IV | **N** head's sense is settled in a place; the 'home-loving' person sense is marginal |
| not_character/unreg | 470 Possibility (IV; pair_empty; rating 0) | surmountable | 1.66 | AO III | **N** said of obstacles |
| not_character/unreg | 794 Barter (V; singleton_empty; rating 0) | staple | 3.68 | not in registry | **N** said of goods |
| not_character/unreg | 777a Exemption (V; pair_empty; rating 0) | without | 5.69 | not in registry | **N** a preposition the parser left in the Adj block |
| not_character/unreg | 963 Legality (VI; pair_empty; rating 0) | constitutional | 4.33 | not in registry | **N** legal sense |
| not_character/reg | 507 Expectation (IV; pair_empty; rating 0) | expecting | 4.42 | M1 states; M3 new | **N** pregnant (the role's state) or awaiting; M1 sent it to states |
| not_character/reg | 571 Obscurity (IV; pair_completion; rating 0) | involved | 5.10 | M1 trait; M3 new; AO II | **N** M1 found a person reading (engaged), but the head's sense is 'convoluted', said of style |
| not_character/reg | 729 Completion (V; pair_empty; rating 0) | exhaustive | 3.30 | M1 trait; M3 covered by [thorough](../../../data/traits/instructions/thorough.json); AO IV | **N** M3: covered by [thorough](../../../data/traits/instructions/thorough.json) |
| not_character/reg | 470 Possibility (IV; pair_empty; rating 0) | credible | 3.77 | M1 trait; M3 new; AO III | **B** M1 trait/new, but said of claims far more than of people |
| not_character/reg | 554 Representation (IV; pair_empty; rating 0) | imitative | 2.17 | M1 trait; M3 new; AO I | **Y** a copying disposition; M1 trait, M3 new |
| not_character/reg | 588 Conversation (IV; pair_empty; rating 0) | conversational | 3.11 | M1 trait; M3 covered by [casual](../../../data/traits/instructions/casual.json); AO I | **N** M3: covered by [casual](../../../data/traits/instructions/casual.json) |
| not_gap/unreg | 749 Subjection (V; covered; rating 2) | subjected | 3.86 | not in registry | **N** a passing condition |
| not_gap/unreg | 76 Inclusion (I; covered; rating 0) | encircling | 2.71 | not in registry | **N** spatial |
| not_gap/unreg | 476 Reasoning (IV; crowded; rating 2) | reasoning | 4.01 | not in registry | **N** participle; 'a reasoning being' is a capacity, not a disposition |
| not_gap/unreg | 201 Shortness (II; covered; rating 1) | pug | 3.11 | not in registry | **N** pug-nosed; physical |
| not_gap/unreg | 828 Pain (VI; covered; rating 1) | cut up | 5.24 | not in registry | **N** distressed; a state |
| not_gap/unreg | 737a Government (V; partly_covered; rating 1) | national | 5.51 | not in registry | **N** not about a person's character |
| not_gap/unreg | 865 Desire (VI; covered; rating 2) | sharp-set | 4.48 | AO IV | **N** hungry; a state |
| not_gap/unreg | 526 Latency. Implication (IV; covered; rating 0) | implied | 3.93 | not in registry | **N** said of meanings |
| not_gap/unreg | 641 Redundancy (V; partly_covered; rating 1) | running down | 5.23 | not in registry | **N** said of things |
| not_gap/unreg | 260 Opening (II; covered; rating 0) | wide open | 4.96 | not in registry | **N** spatial |
| not_gap/unreg | 924 Dueness (VI; covered; rating 1) | fit | 4.95 | AO IV | **N** suitable, or physically fit (physical list) |
| not_gap/unreg | 732 Failure (V; covered; rating 0) | done up | 5.58 | not in registry | **N** exhausted; a state |
| not_gap/unreg | 276 Impulse (II; partly_covered; rating 1) | impelling | 1.53 | AO II | **N** said of forces |
| not_gap/unreg | 203 Narrowness. Thinness (II; covered; rating 0) | scant | 3.10 | AO IV | **N** said of amounts |
| not_gap/unreg | 55 Exclusion (I; covered; rating 0) | inadmissible | 2.77 | not in registry | **N** said of evidence |
| not_gap/unreg | 499 Imbecility. Folly (IV; covered; rating 2) | child-like | 5.30 | not in registry | **N** a trait word, but childlike is registered (TDA) and M3 covered it by [trusting](../../../data/traits/instructions/trusting.json) |
| not_gap/unreg | 821 Feeling (VI; crowded; rating 1) | sensory | 3.68 | not in registry | **N** physiological |
| not_gap/unreg | 803 Wealth (V; covered; rating 1) | filthy rich | 3.80 | not in registry | **N** a membership the corpus has as [wealthy](../../../data/traits/instructions/wealthy.json) |
| not_gap/unreg | 898 Hate (VI; covered; rating 1) | rejected | 4.37 | not in registry | **N** a state |
| not_gap/unreg | 865 Desire (VI; covered; rating 2) | desiring | 2.91 | not in registry | **N** participle; a state |
| not_gap/reg | 785 Receiving (V; covered; rating 0) | recipient | 3.94 | M1 roles; AO I | **N** M1: roles |
| not_gap/reg | 879 Humility (VI; crowded; rating 2) | servile | 2.45 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new; sits in the crowded head 879 Humility |
| not_gap/reg | 214 Pendency (II; partly_covered; rating 0) | hanging | 4.50 | M1 turned_away; AO II | **N** M1 turned away |
| not_gap/reg | 608 Caprice (V; crowded; rating 2) | capricious | 2.79 | M1 trait; M3 covered by [erratic](../../../data/traits/instructions/erratic.json); AO I | **N** M3: covered by [erratic](../../../data/traits/instructions/erratic.json) |
| not_gap/reg | 926 Duty (VI; covered; rating 1) | imperative | 3.66 | M1 turned_away; AO I | **N** M1 turned away |
| not_gap/reg | 950 Penitence (VI; covered; rating 2) | penitentiary | 3.18 | M1 turned_away; AO II | **N** M1 turned away |
| not_gap/reg | 324 Softness (III; partly_covered; rating 2) | pliable | 2.64 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new |
| not_gap/reg | 320 Levity (III; partly_covered; rating 1) | floating | 4.18 | M1 trait; M3 covered by aimless (queue); AO II | **N** M3: covered by aimless |
| not_gap/reg | 704 Difficulty (V; partly_covered; rating 1) | hard | 5.53 | M1 trait; M3 covered by [callous](../../../data/traits/instructions/callous.json); AO III | **N** M3: covered by [callous](../../../data/traits/instructions/callous.json) |
| not_gap/reg | 816 Liberality (V; covered; rating 2) | hospitable | 2.96 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new; head 816 Liberality is covered |
| out_of_scope/unreg | 318 World (III; out of scope) | terrestrial | 3.48 | AO IV | **N** spatial |
| out_of_scope/unreg | 67 End (I; out of scope) | conterminous | 1.52 | not in registry | **N** spatial |
| out_of_scope/unreg | 93 Triplication (I; out of scope) | threefold | 2.69 | not in registry | **N** number |
| out_of_scope/unreg | 229 Circumscription (II; out of scope) | landlocked | 2.76 | not in registry | **N** geography |
| out_of_scope/unreg | 121 Futurity (I; out of scope) | next | 5.70 | not in registry | **N** order |
| out_of_scope/unreg | 216 Parallelism (II; out of scope) | parallel | 4.27 | not in registry | **N** geometry |
| out_of_scope/unreg | 352 Semiliquidity (III; out of scope) | viscous | 2.94 | AO IV | **N** physical matter |
| out_of_scope/unreg | 11 Consanguinity (I; out of scope) | kindred | 3.15 | not in registry | **N** relation, not a disposition |
| out_of_scope/unreg | 100 Plurality (I; out of scope) | plural | 3.55 | not in registry | **N** grammar |
| out_of_scope/unreg | 414 Discord (III; out of scope) | singsong | 1.98 | AO II | **N** said of a voice |
| out_of_scope/unreg | 147 Substitution (I; out of scope) | ersatz | 2.34 | not in registry | **N** said of things |
| out_of_scope/unreg | 248 Convolution (II; out of scope) | convoluted | 3.05 | not in registry | **N** said of things; of a person's thinking at a stretch |
| out_of_scope/reg | 378 Physical Pain (III; out of scope) | sore | 3.99 | M1 states; AO II | **N** M1: states |
| out_of_scope/reg | 238 Dextrality (II; out of scope) | right-handed | 4.42 | M1 physical | **N** M1: physical list |
| out_of_scope/reg | 42 Simpleness (I; out of scope) | simple | 5.08 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new (unsophisticated) |
| out_of_scope/reg | 50 Whole (I; out of scope) | comprehensive | 4.36 | M1 trait; M3 covered by [thorough](../../../data/traits/instructions/thorough.json); AO III | **N** M3: covered by [thorough](../../../data/traits/instructions/thorough.json) |
| out_of_scope/reg | 166 Paternity (I; out of scope) | maternal | 3.77 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new |
| out_of_scope/reg | 352 Semiliquidity (III; out of scope) | muddy | 3.60 | M1 states; AO IV | **N** M1: states |
| kept/r1 | 768 Promise (V; pair_empty; rating 1) | promissory | 2.57 | M1 turned_away | **N** said of notes; M1 turned away |
| kept/r1 | 193 Littleness (II; pair_completion; rating 1) | pocket | 4.48 | M1 turned_away | **N** pocket-sized; M1 turned away |
| kept/r1 | 706 Hindrance (V; pair_completion; rating 1) | hindering | 2.93 | M1 trait; M3 new; AO II | **N** said of things; M1 said trait, the agent disagrees |
| kept/r1 | 780 Property (V; singleton_empty; rating 1) | landed | 4.24 | M1 trait; M3 new; AO IV | **B** a membership (landed gentry), which the corpus counts |
| kept/r1 | 614 Desuetude (V; pair_empty; rating 1) | new | 6.25 | M1 states; AO IV | **N** M1: states |
| kept/r1 | 980 Demon (VI; pair_empty; rating 1) | demonic | 3.33 | M1 trait; M3 new | **B** fiendish; evaluative more than descriptive |
| kept/r1 | 471 Impossibility (IV; pair_empty; rating 1) | impossible | 4.78 | M1 trait; M3 new; AO III | **B** 'an impossible person' is a real but secondary sense |
| kept/r1 | 579 Inelegance (IV; pair_completion; rating 1) | grotesque | 3.28 | M1 physical; AO III | **N** M1: physical list |
| kept/r1 | 643 Unimportance (V; pair_completion; rating 1) | ridiculous | 4.46 | M1 trait; M3 new; AO III | **B** evaluative |
| kept/r1 | 565 Misnomer (IV; pair_empty; rating 1) | self called | 5.25 | M1 roles | **N** M1: roles; not a disposition |
| kept/r1 | 403 Silence (III; pair_empty; rating 1) | silent | 4.45 | M1 trait; M3 new; AO I | **Y** taciturn; M1 trait, M3 new |
| kept/r1 | 473 Improbability (IV; pair_empty; rating 1) | unlikely | 4.31 | M1 trait; M3 new; AO III | **N** said of events; M1 said trait, the agent disagrees |
| kept/r1 | 652 Cleanness (V; pair_completion; rating 1) | trig | 2.68 | M1 trait; M3 new; AO I | **Y** archaic: neat, spruce; M1 trait, M3 new |
| kept/r1 | 717 Defense (V; pair_completion; rating 1) | iron-plated | 3.45 | M1 turned_away | **N** M1 turned away |
| kept/r1 | 789 Taking (V; pair_empty; rating 1) | taking | 5.39 | M1 turned_away; AO III | **N** the head is 789 Taking (seizing); M1 turned away |
| kept/r1 | 980 Demon (VI; pair_empty; rating 1) | possessed | 3.85 | M1 states | **N** M1: states |
| kept/r1 | 764 Refusal (V; pair_empty; rating 1) | recusant | 1.70 | M1 trait; M3 new; AO I | **Y** refusing to submit; M1 trait, M3 new |
| kept/r1 | 560 Language (IV; singleton_empty; rating 1) | literary | 4.31 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new |
| kept/r1 | 647 Inexpedience (V; pair_completion; rating 1) | undesirable | 3.36 | M1 trait; M3 new; AO III | **N** evaluative of things; M1 said trait |
| kept/r1 | 712 Party (V; singleton_empty; rating 1) | joined together | 4.73 | M1 trait; M3 new | **N** not a disposition; M1 said trait, the agent disagrees |
| kept/r1 | 550 Indication (IV; singleton_empty; rating 1) | indicated | 4.34 | M1 turned_away | **N** M1 turned away |
| kept/r1 | 764 Refusal (V; pair_empty; rating 1) | restive | 2.37 | M1 trait; M3 covered by [restless](../../../data/traits/instructions/restless.json); AO I | **N** M3: covered by [restless](../../../data/traits/instructions/restless.json) |
| kept/r1 | 565 Misnomer (IV; pair_empty; rating 1) | misnamed | 1.92 | M1 trait; M3 new | **N** said of things; M1 said trait, the agent disagrees |
| kept/r1 | 830 Painfulness (VI; pair_completion; rating 1) | painful | 4.32 | M1 turned_away; AO III | **N** M1 turned away |
| kept/r1 | 471 Impossibility (IV; pair_empty; rating 1) | insurmountable | 3.03 | M1 turned_away | **N** M1 turned away |
| kept/r1 | 674 Nonpreparation (V; pair_completion; rating 1) | untrained | 3.03 | M1 trait; M3 new; AO IV | **B** a state of training more than a disposition; M1 trait, M3 new |
| kept/r1 | 471 Impossibility (IV; pair_empty; rating 1) | unimaginable | 3.15 | M1 turned_away | **N** M1 turned away |
| kept/r1 | 824 Excitation (VI; singleton_empty; rating 1) | excited | 4.74 | M1 states; AO II | **N** M1: states |
| kept/r1 | 777 Possession (V; pair_empty; rating 1) | possessing | 3.61 | M1 turned_away | **N** M1 turned away |
| kept/r1 | 471 Impossibility (IV; pair_empty; rating 1) | unthinkable | 3.27 | M1 turned_away; AO III | **N** M1 turned away |
| kept/r2 | 452 Incogitancy (IV; pair_completion; rating 2) | diverted | 3.49 | M1 states; AO II | **N** M1: states |
| kept/r2 | 820 Affections (VI; singleton_empty; rating 2) | tempered | 3.53 | M1 trait; M3 covered by [calm](../../../data/traits/instructions/calm.json); AO I | **N** M3: covered by [calm](../../../data/traits/instructions/calm.json) |
| kept/r2 | 602 Willingness (V; pair_completion; rating 2) | ready | 5.28 | M1 states; AO II | **N** M1: states |
| kept/r2 | 791 Stealing (V; singleton_empty; rating 2) | light-fingered | 3.08 | M1 roles | **Y** thievish; M1 sent it to roles, the agent reads a disposition |
| kept/r2 | 602 Willingness (V; pair_completion; rating 2) | favorably-minded | 3.20 | M1 trait; M3 covered by [friendly](../../../data/traits/instructions/friendly.json) | **N** M3: covered by [friendly](../../../data/traits/instructions/friendly.json) |
| kept/r2 | 820 Affections (VI; singleton_empty; rating 2) | affective | 3.00 | M1 trait; M3 covered by [expressive](../../../data/traits/instructions/expressive.json); AO I | **N** M3: covered by [expressive](../../../data/traits/instructions/expressive.json); the agent reads 'relating to affect' |
| kept/r2 | 930 Contempt (VI; singleton_empty; rating 2) | disdainful | 2.35 | M1 trait; M3 new; AO I | **Y** M1 trait, M3 new |
| kept/r2 | 930 Contempt (VI; singleton_empty; rating 2) | despicable | 3.46 | M1 turned_away; AO III | **N** evaluative; M1 turned away |
| kept/r2 | 791 Stealing (V; singleton_empty; rating 2) | stolen | 4.41 | M1 turned_away | **N** M1 turned away |
| kept/r2 | 961 Impurity (VI; pair_completion; rating 2) | impure | 2.95 | M1 trait; M3 new; AO III | **Y** M1 trait, M3 new (morally impure) |

**A supplementary 60 unregistered discards** (`random.Random(202610121)`, drawn across every unselected category and excluding the rows above) were read to tighten the unregistered rate.

None is a new trait.  The near-misses are:
- well off and thorough-going, covered by [wealthy](../../../data/traits/instructions/wealthy.json) and [thorough](../../../data/traits/instructions/thorough.json);
- sharp-eyed, indiscriminate, wayfaring and seared, all borderline.

The other 54 are N: well-made, favor, convertible, toothsome, rejected, covering, unmanned, infused, unreached, front, attainable, putative, gradual, proceeding, similar, family, snowy, equalized, round, abhorrent, gone, nebulous, modal, rectangular, doing, uninterrupted, subjunctive, extended, knotted, proximal, burried, numerous, anticipatory, oral, ghostly, subtractive, fruitless, shadowy, deep-mouthed, disinfectant, bisected, past hope, secondhand, moist, furrowed, gummy, spoken, capsular, smaller, red handed, choke-full, mineral, stillborn and reverse.

### 4c. The Roget Zipf checks: every removed word, read

This is the whole population, not a sample: the 144 words dropped in the 87 harvested heads.

Notation:
- the number after each word is its Zipf;
- "neg" marks a negating-prefix rescue that the second check dropped;
- AO gives the Allport-Odbert column, and M1 the registry outcome where another generator submitted the word;
- the verdict against the floor's intent ("is it a trait word worth a judge call?") is **T** trait word, **B** borderline, **N** not.

| head | dropped words |
|---|---|
| 124 Oldness | archeozoic 0.00 **N**; paleoanthropological 0.00 **N**; paleolontological 0.00 **N**; paleontologic 0.00 **N**; paleozoolical 0.00 **N**; precolumbian 1.40 **N** |
| 193 Littleness | exiguous 1.07 (AO IV) **N**; inappreciable 0.00 (neg) **N**; microzoal 0.00 **N** |
| 391 Insipidity | savorless 0.00 (AO III) **N** |
| 403 Silence | deathlike 1.39 **N** |
| 452 Incogitancy | undreamt 'of 1.24 (neg) **N**; unintellectual 1.10 (neg, AO I, M1 trait) **T** |
| 473 Improbability | outtasight 0.00 **N** |
| 508 Inexpectation | unwarned 0.00 (neg) **N** |
| 519 Unintelligibility | enigmatical 0.00 **B**; incommunicable 1.35 (neg) **N**; metempirical 0.00 **N**; unconceived 0.00 (neg) **N**; undiscoverable 0.00 (neg) **N** |
| 520 Equivocalness | enigmatical 0.00 **B** |
| 536 Negation | negatory 1.25 **N** |
| 550 Indication | denotative 1.38 **N**; indicatory 0.00 **N**; pantomimic 1.32 **N** |
| 565 Misnomer | innominate 1.38 (neg) **N** |
| 579 Inelegance | ungraceful 1.47 (neg, AO I, M1 trait) **T** |
| 585 Taciturnity | closetongued 0.00 **T** |
| 600 Will | discretional 0.00 **N** |
| 602 Willingness | persuadable 1.49 (M1 trait) **T**; persuasible 0.00 (AO III) **T** |
| 611 Predetermination | predesignated 1.33 **N** |
| 614 Desuetude | unhackneyed 0.00 (neg, AO III) **N**; unwonted 1.17 (neg, AO III) **N** |
| 621 Chance | causeless 1.31 **N**; uncontemplated 0.00 (neg) **N**; undesigned 1.02 (neg) **N** |
| 640 Insufficiency | halfstarved 0.00 **N**; stinted 1.22 (AO IV) **N**; unprovided 1.21 (neg) **N**; unreplenished 0.00 (neg) **N** |
| 643 Unimportance | catchpenny 0.00 **N**; fiddle-faddle 1.46 (AO III) **N**; inappreciable 0.00 (neg) **N**; trumpery 1.36 (AO III) **N**; twopennyhalfpenny 0.00 **N** |
| 647 Inexpedience | cumbrous 1.05 **N**; incommodious 0.00 (neg) **N**; inexpedient 1.30 (neg) **N**; unadvisable 1.05 (neg) **N** |
| 652 Cleanness | taintless 0.00 (AO III) **B**; unsoiled 1.24 (neg, AO IV) **N** |
| 674 Nonpreparation | improvident 1.41 (AO I, M1 trait) **T**; thriftless 0.00 (AO I, M1 trait) **T**; unbegun 0.00 (neg) **N**; unblown 0.00 (neg, AO IV) **N**; unboiled 1.02 (neg) **N**; unconcocted 0.00 (neg) **N**; undrilled 1.13 (neg) **B**; unexercised 1.22 (neg, AO II) **N**; unfledged 1.14 (neg, AO IV) **B**; unprovided 1.21 (neg) **N**; unsown 0.00 (neg) **N**; untaught 1.32 (neg, AO IV, M1 trait) **T**; unthrifty 0.00 (neg, AO I, M1 trait) **T**; untilled 1.16 (neg, AO IV) **N**; unwrought 0.00 (neg) **N** |
| 687 Repose | unstrained 1.11 (neg, AO I) **B** |
| 706 Hindrance | cumbrous 1.05 **N**; impedimentary 0.00 **N** |
| 717 Defense | loopholed 1.01 **N** |
| 718 Retaliation | retaliative 0.00 (AO I, M1 trait) **T** |
| 719 Resistance | renitent 0.00 (AO I) **T** |
| 761 Prohibition | proscriptive 1.36 **N**; uncountenanced 0.00 (neg) **N** |
| 762 Consent | squeezable 1.44 (AO III) **B** |
| 764 Refusal | uncomplying 0.00 (neg, AO I) **T**; unconsenting 0.00 (neg, AO II) **N**; ungranted 0.00 (neg) **N** |
| 765 Request | suppliant 1.44 (AO II) **B**; supplicatory 0.00 **N** |
| 768 Promise | affianced 1.45 **N** |
| 789 Taking | raptorial 1.37 (AO I) **B** |
| 791 Stealing | thievish 1.01 **T** |
| 815 Cheapness | catchpenny 0.00 **N**; scotfree 0.00 **N**; unbought 1.19 (neg) **N**; unsalable 1.15 (neg) **N** |
| 820 Affections | ineffaceable 0.00 (AO IV) **N** |
| 824 Excitation | demoniacal 1.02 **B** |
| 830 Painfulness | afflictive 1.25 **N**; carking 0.00 (AO II) **N**; comfortless 1.37 (AO III) **N**; cumbrous 1.05 **N**; desolating 1.15 **N**; envenomed 1.29 (AO III) **B**; pyrotic 0.00 **N**; unaccommodating 1.22 (neg, AO III, M1 trait) **T** |
| 901a Sullenness | cankered 0.00 (AO IV) **B**; frumpish 0.00 (AO III) **B**; grouty 0.00 **T**; splenetic 1.42 (AO I, M1 trait) **T**; unaccommodating 1.22 (neg, AO III, M1 trait) **T** |
| 909 Threat | minatory 1.06 (AO I) **B** |
| 930 Contempt | contumelious 0.00 (AO I) **T** |
| 931 Approbation | encomiastic 0.00 (AO I) **B**; eulogistic 1.26 (AO I) **B**; panegyrical 0.00 **N**; uncensured 0.00 (neg) **N**; unimpeached 0.00 (neg) **N** |
| 932 Disapprobation | captious 1.19 (AO I) **T**; denunciatory 0.00 **B**; exceptionable 0.00 **N**; uncommendable 0.00 (neg, AO III) **N**; unlamented 1.31 (neg, AO III) **N** |
| 934 Detraction | calumnious 0.00 **B**; deprecatory 1.32 (AO I) **B**; scurrile 0.00 **B** |
| 937 Vindication | pardonable 1.45 (AO III) **N** |
| 945 Vice | demoniacal 1.02 **B**; flagitious 0.00 (AO III) **B**; indiscrete 1.34 (neg) **N**; inexpiable 0.00 (AO III) **N**; irreclaimable 0.00 **B**; mephistophelian 1.01 **B**; recreant 1.17 (AO I) **T**; scampish 0.00 (AO I, M1 trait) **T**; uncommendable 0.00 (neg, AO III) **N**; undutiful 1.21 (neg, AO I, M1 trait) **T**; virtueless 0.00 (AO III) **B** |
| 947 Guilt | censurable 0.00 (AO III) **N**; exceptionable 0.00 **N**; uncommendable 0.00 (neg, AO III) **N** |
| 961 Impurity | concupiscent 1.22 (AO IV) **T**; goatish 0.00 (AO IV, M1 trait) **T**; ruttish 0.00 (AO III) **B** |
| 964 Illegality | unwarrantable 1.24 **N** |
| 980 Demon | demoniacal 1.02 **B**; demonical 0.00 **B**; elfish 1.49 (AO I, M1 trait) **T**; pokerish 0.00 **N** |
| 981 Heaven | paradisiacal 1.42 **N** |
| 1000 Temple | claustral 1.23 **N**; monasterial 0.00 **N** |

**Tallies.**
- Across all 144: **25 T, 28 B, 91 N.**  The 94 `hard_reject` drops are 17 T, 25 B and 52 N.  The 50 second-check drops (the negating-prefix rescues) are 8 T, 3 B and 39 N.
- Roget's *un-* words are mostly about things (unboiled, untilled, unsown), so route 1 rescues little here.  Contrast the WordNet stream, where all 19 negating-prefix rows that reached M1 were judged traits.
- Of the 24 distinct T words, 14 are already registered: the censuses submitted them and M1 judged them traits.
- The other 10 (captious, closetongued, concupiscent, contumelious, grouty, persuasible, recreant, renitent, thievish, uncomplying) each have a near-synonym already in the pipeline: carping, close-mouthed, [lustful](../../../data/traits/instructions/lustful.json) (corpus), contemptuous, sullen, persuadable, faithless, recalcitrant, light-fingered and noncompliant.
- The 99 drops in the 119 skipped heads were read as well: **0 T and 9 B** (twaddling, envenomed, ungenial, cankered, unwearied, deprecatory, denunciatory, recriminatory, behindhand).  None is registered.

**Why only 12 of the 144 matter.**  The harvest submits one word per semicolon group: the most frequent survivor.  A word below 1.5 can therefore become a candidate only when *every* other clean word of its group is below 1.5 too.  To measure the effect, I re-ran every harvested head under the rule as built and under two variants: `hard_reject only`, as review 5 D4 recommends, and `no floor`, as rule 1b route 2 would allow.  Against the rule as built, only these words become candidates:

| head | word | Zipf | added under | reference | agent's verdict |
|---|---|---|---|---|---|
| 614 Desuetude | unhackneyed | 0.00 | D4 fix and no floor | AO III | **N** said of expressions |
| 687 Repose | unstrained | 1.11 | D4 fix and no floor | AO I | **B** a relaxed, natural manner |
| 764 Refusal | uncomplying | 0.00 | D4 fix and no floor | AO I; noncompliant and uncooperative registered, M3 new | **T** but its sense is already in the pipeline |
| 931 Approbation | uncensured | 0.00 | D4 fix and no floor | - | **N** |
| 585 Taciturnity | closetongued | 0.00 (the text's closed-up spelling of close-tongued) | no floor | close-mouthed and taciturn registered, M3 new | **T**, covered by its registered synonyms |
| 602 Willingness | persuadable | 1.49 | no floor | TDA 0.92; registered, M1 trait, M3 new | **T**, already registered |
| 761 Prohibition | proscriptive | 1.36 | no floor | - | **N** |
| 762 Consent | squeezable | 1.44 | no floor | AO III | **B** pliant |
| 909 Threat | minatory | 1.06 | no floor | AO I; threatening and menacing registered, M3 new | **B** |
| 934 Detraction | calumnious | 0.00 | no floor | slanderous registered, M3 new | **B** |
| 947 Guilt | exceptionable | 0.00 | no floor | - | **N** |
| 980 Demon | pokerish | 0.00 | no floor | - | **N** |

In the heads rated 0, which are skipped anyway, the variants would add 9 more words (D4 fix) or 21 (no floor), among them unmeaning, unmeant, unwearied and unprosperous.

**The kept side of the Zipf line.**  The 55 kept words in the 1.5-2.5 probe band fare as well at M1 as the frequent ones: 35 traits (64%) and 9 turned away (16%), against 62% and 16% for the 270 kept words at Zipf 3.5 or above.  They include taciturn, querulous, lachrymose, recusant, furtive and rapacious.  Within a trait-rated head, frequency does not separate junk at these levels.

### 4d. The WordNet stream

**Kept side** (all 468, reference labels; the full population replaces a sample):
- closure words at depths 1-3: 334 of 366 are M1 traits (91%) and 181 are trait-new (49%);
- antonym route: 80 of 102 are traits and 45 are new.  The antonym route takes antonyms of every sense of the label, which gives well for [autistic](../../../data/traits/instructions/autistic.json), public for [clannish](../../../data/traits/instructions/clannish.json) and social for [lonely](../../../data/traits/instructions/lonely.json).  M1 sorts these out.
- Most kept words duplicate other generators: 376 of the 468 are also registered from another generator, mostly the censuses.

**Depth beyond 3: the 117 adjectives at depths 4-6, the whole population.**
- **Registered, 97 words.**  94 are M1 traits (97%) and 51 are M3 new: nice, civil, smart, smooth, wary, high-spirited, lax, abrupt, possessive, curt, stately, scrappy, crusty, rabid, brazen, wasteful, otherworldly, plucky, presumptuous, provident, contemptuous, militaristic, remiss, studious, impudent, urbane, servile, brusque, imprudent, gauche, ornery, unwary, rapacious, acquisitive, ebullient, assiduous, obsequious, roguish, lordly, covetous, avaricious, smutty, ceremonious, punctilious and others.  The three that are not traits are dirty, intent and faint, all sent to states.
- **Unregistered, 20 words**, read by the agent:
  - **T 7:** anti-semitic, antisemitic, penny-pinching, cussed, uppity, chary, fainthearted;
  - **B 5:** infallible, fallible, nerveless, sparkly, twinkly;
  - **N 8:** becoming, naked, spicy, outward, reproducible, lightheaded, gamy, inerrant.

**The Zipf floor in the closure, all 40 words.**  Verdicts as in § 4c; "reg" marks a word registered by another generator.

| word | Zipf | reference | verdict |
|---|---|---|---|
| uxorious | 1.14 | AO I; reg, M1 trait | **T** |
| phlegmatical | 0.00 | phlegmatic reg, M3 covered by [unflappable](../../../data/traits/instructions/unflappable.json) | **T** variant spelling |
| spiritless | 1.44 | AO I; reg, M1 trait | **T** |
| faineant | 0.00 | AO I | **T** idle |
| acceptant | 0.00 | reg, M1 trait | **T** |
| longanimous | 0.00 | - | **T** long-suffering, obscure |
| complaisant | 1.36 | reg, M1 trait | **T** |
| pettish | 0.00 | AO I; reg, M1 trait | **T** |
| snappish | 1.34 | AO I; reg (states pass), M1 trait | **T** |
| jocose | 1.07 | AO I; jocular reg, M3 new | **T** |
| frolicsome | 1.40 | AO I; reg, M1 trait | **T** |
| misanthropical | 0.00 | corpus [misanthropic](../../../data/traits/instructions/misanthropic.json) | **T** variant |
| heedful | 1.14 | AO I; reg, M1 trait | **T** |
| manful | 1.43 | AO III; manly reg, M3 new | **T** |
| maidenly | 1.33 | - | **B** |
| mingy | 1.10 | corpus [stingy](../../../data/traits/instructions/stingy.json) | **T** |
| tightfisted | 1.26 | corpus [stingy](../../../data/traits/instructions/stingy.json) | **T** |
| penurious | 1.43 | AO I | **T** |
| stouthearted | 1.13 | corpus [brave](../../../data/traits/instructions/brave.json) | **T** |
| impenitent | 1.48 | AO II; corpus [unrepentant](../../../data/traits/instructions/unrepentant.json) | **T** |
| pertinacious | 1.07 | AO I; reg, M1 trait | **T** |
| irresolute | 1.49 | AO I; reg, M1 turned away | **T** (the agent disagrees with M1) |
| abstentious | 0.00 | - | **B** |
| sottish | 0.00 | AO I; reg, M1 trait | **T** |
| slatternly | 1.01 | AO I; corpus [slovenly](../../../data/traits/instructions/slovenly.json) | **T** |
| sluttish | 1.36 | AO III; reg, M1 trait | **B** |
| equanimous | 1.07 | AO I | **T** |
| ataraxic | 0.00 | - | **B** |
| ataractic | 0.00 | - | **N** a drug sense |
| mulish | 1.37 | AO I; reg, M1 trait | **T** |
| mordacious | 0.00 | AO I | **B** |
| stainable | 0.00 | - | **N** |
| basophilic | 1.39 | - | **N** |
| tendencious | 0.00 | - | **B** |
| preferent | 0.00 | AO IV | **N** |
| prejudicious | 0.00 | - | **B** |
| absolutistic | 0.00 | - | **B** |
| totalistic | 0.00 | - | **N** |
| fundamentalistic | 0.00 | - | **B** |
| liberalistic | 0.00 | AO I | **B** |

The tally is **25 T, 10 B and 5 N**.  13 of the T words are unregistered, but most of those have a corpus or registered near-synonym.

**Synsets with no derivational adjective: 198 of 559.**  A sample of 40, drawn with `random.seed(20261012)`, gave 22 trait concepts.  The adjectives exist, but OEWN has no derivation link from that sense to them: [passionate](../../../data/traits/instructions/passionate.json), agnostic, good-natured, superiority complex, democratic, self-controlled, discreet, anti-traditionalist, [circumspect](../../../data/traits/instructions/circumspect.json), intolerant, [elitist](../../../data/traits/instructions/elitist.json), rightist, bellicose, insubordinate, [nonconformist](../../../data/traits/instructions/nonconformist.json), [ethnocentric](../../../data/traits/instructions/ethnocentric.json), leftist, overtolerant, courteous, light-hearted, [zealous](../../../data/traits/instructions/zealous.json), provincial.  The other 18 are not person traits: devices, nature, blood, spirit, Weltanschauung, cityscape, evolutionary trend, complexion, light, electronegativity, favor, point of view, desperation, recognition, constitutionalism, unitarism, sight and the root-like nature sense.

Of 25 such adjectives checked, 21 are already corpus traits or registered; only rightist, leftist, anti-traditionalist and agnostic are not.  Following derivations across *all* senses of the lemma instead recovers 48 adjectives, but mostly junk (heatable, conductive, postural), so that is no fix.

**Roots left out on purpose.**  Adding quality (OEWN 04731092) at depth 3 would bring in 729 adjectives.
- 457 are registered: 370 of them M1 traits and 257 M3 new.
- 272 are unregistered.  Only 9 of those are AO I, and a sample of 30 reads mostly N (scalable, woody, illegible, nutritious, hairy).
- emotion and feeling add 47 and 150, mostly states.

The exclusion of quality holds: its trait part reaches the pipeline through the censuses.

## 5. Rates

The false-negative rate (FN) is the share of discards that fit the intent.  The false-positive rate (FP) is the share of kept words that do not.  Intervals are 95% Wilson intervals.

| gate part | FN (discarded but fits the intent) | implied over the run | FP (kept but does not fit) | implied over the run |
|---|---|---|---|---|
| head selection, registered discards (2,270) | reference 913 of 2,270 = 40% (full population).  Agent's sense check: 6 of the 8 reference calls in the sample hold, so about 690 | about 690-913 | - | - |
| head selection, unregistered discards (2,015) | 0 of 100 = 0% [0.0%, 3.7%] (agent) | 0-75 | - | - |
| head selection, all discards (4,285) | about 16-23% | about 690-990, **of which 0-75 no generator has** | kept 473: reference not trait-new 254 = 54% (full population); agent, sample of 40, N 28 = 70% [54.6%, 81.9%] | 254-330 |
| Roget Zipf, as a filter (144 removed) | T 25 of 144 = 17% [12.0%, 24.4%]; T or B 37% [29.4%, 44.9%] | 25 (all read) | probe band kept at 1.5-2.5: turned away 9 of 55 = 16% [8.9%, 28.3%], the same as 16% at Zipf 3.5 or above | 9 |
| Roget Zipf, its effect on candidates (12 would-be) | T 3 of 12 = 25% [8.9%, 53.2%]; T or B 7 of 12 | **3 trait words, all already in the pipeline under their own name or a synonym** | as above | - |
| WordNet depth bound 3 (117 beyond) | reference trait 94 of 97 = 97% [91.3%, 98.9%], trait-new 51 of 97 = 53%; unregistered T 7 of 20 = 35% [18.1%, 56.7%] | about 56, **of which about 7 unregistered** | kept closure: not a trait 32 of 366 = 9%; not trait-new 185 of 366 = 51% | 185 |
| WordNet Zipf floor (40 removed in the closure) | T 25 of 40 = 62% [47.0%, 75.8%] | 25, **13 unregistered** | - | - |
| WordNet derivation gap (198 synsets) | trait concept 22 of 40 = 55% [39.8%, 69.3%]; their adjectives are mostly present already (21 of 25) | about 110 concepts, **about 15-20 words missing from the pipeline** | - | - |

## 6. Verdicts

**Head selection: doing what was intended, but improvable.**
- The code harvests exactly what the plan, [QUESTIONS](../../trait_gap_generation/QUESTIONS.md) 40 and QUESTIONS 44 name: the gap heads of the dispositional set plus the 99 Class I-III heads, minus the heads rated 0.
- The premise that makes this a gap finder is weak at the word level.  A Roget head holds 10-50 adjectives spanning several distinct traits, so one corpus label primary to the head makes it "covered" while most of its traits stay out of the corpus.  544 Falsehood, 880 Vanity, 939 Probity and 606 Obstinacy each hold 6-8 trait-new words.
- Among words the censuses also submitted, a covered head's words are trait-new 41% of the time against 54% for a gap head's.  As a selector the gate beats chance only modestly, but it costs nothing today.  The censuses had already put 2,270 of the 4,285 discarded words into the registry, including all 913 that M1 and M3 call trait-new, and the 2,015 they did not submit are almost all non-traits (0 of 100 read).
- **The selection's weakness matters for the coverage report, not for the harvest.**  The report is the workstream's main product besides the harvest ([coding plan 02](../../trait_gap_generation/coding_plan_02_roget_wordnet.md), revision item 1), and it tells Roger a head is covered when it holds eight new traits.
- **The head-scope skip** (rated 0) is doing what was intended.  Its registered words that M1 calls traits mostly carry another sense than the head's (involved, credible, expecting): of the 6 sampled, 1 is Y and 1 is B.  Its unregistered words are not traits (0 of 8 in the sample, 0 T among its 99 Zipf drops).
- **The Class I-III scope** is doing what was intended: 0 of 12 unregistered words sampled are traits, and the registered ones are with the censuses.

**Roget Zipf checks: doing what was intended ([QUESTIONS](../../trait_gap_generation/QUESTIONS.md) 42), about as well as possible.**
- The line removes 144 words, of which 25 are trait words.  The one-word-per-group rule already makes 132 of them redundant, so the gate decides the fate of 12 words, 3 of them trait words that are already registered under their own name or a near-synonym.
- [Review 5 D4](../escalations.md#review-5-d4-the-roget-harvests-second-zipf-check-drops-the-negating-prefix-rescues) ("77 words") describes the rule's reach correctly but overstates its effect.  Its fix changes 4 candidates, of which 1 is a trait word (uncomplying).
- What remains is a **rule inconsistency for Roger, worth cents either way**:
  - rule 1b approved three rescue routes; M1 applies route 2 to every row with a gloss hint;
  - the Roget harvest pre-empts both routes 1 and 2;
  - the WordNet stream pre-empts route 2 only.
- Whether the 1.5 line in QUESTIONS 42 was meant to override rule 1b for these two dictionary walks is not recorded.
- The line is a threshold set on a different population: random dictionary adjectives in [decisions_m1.md](../../trait_gap_generation/decisions_m1.md) § 1.  Inside trait-rated heads it does not separate junk, since the probe-band words pass M1 as often as frequent ones.  It is harmless here only because of the one-word-per-group rule.

**WordNet lemma selection: doing what was intended, but improvable.**
- The roots are the plan's.  The depth bound of 3 has no recorded derivation, and the data do not support it: words at depths 4-6 are 97% traits against 91% kept, and 53% new against 49%.
- The Zipf floor here removes mostly trait words (62%).  The closure is already restricted to trait nouns, so the "dictionary junk" the floor exists for is not there.
- Both discards are small and mostly registered.  The fix adds about 20-30 new rows.

## 7. Proposals

1. **Roger: does rule 1b's gloss-hint route (and the negating-prefix route) apply to the Roget and WordNet walks?**  Cost: $0 to decide.  The options:
   - (a) leave as is;
   - (b) review 5 D4's fix for Roget only: +4 candidates (1 trait word), about $0.05 at the measured $0.0078 a word for M1 and $0.013 a passing word for M3;
   - (c) pass `gloss_hint=True` in both generators, matching M1: Roget +12 candidates (11 new rows, 3 T and 4 B), WordNet closure +40 (27 new rows, 25 T), about $0.60 in all.

   The agent recommends (c) for WordNet and is indifferent for Roget.  Evidence that settles it: Roger's reading of "none of these routes carries dictionary junk", against the 62% (WordNet) and 17% (Roget) trait rates above.
2. **Raise `wn_closure_depth` from 3 to 6**, where the closure saturates: +117 candidates.  97 merge into rows already judged, which cost nothing because [traithood_filter.py](../../../data_analysis/gap_generation/traithood_filter.py) `--run` takes unfiltered rows only and [novelty_score.py](../../../data_analysis/gap_generation/novelty_score.py) skips rows another run decided.  The other 20 are new rows (about 7 traits), about $0.25.  Evidence: the depth table in § 4d.  If Roger prefers a bound, depth 5 already holds 111 of the 117.
3. **Record what the gate drops**, at $0:
   - [harvest_counts.json](../../../data/candidates/runs/roget/2026-10-11-full/harvest_counts.json) should split `zipf_hard` into `zipf_hard_reject` and `zipf_rescue_dropped`, count the Zipf drops of skipped heads, and add a `would_be_submitted` count, the words that would have become candidates without the floor (12 here).  The bare drop count overstated the effect sixfold in review 5.
   - The WordNet stream should write drop counts at all: known, floor, multiword, no adjective, and depth cut-off.
4. **Give the coverage report a word-level column**, at $0 from the registry: per head, how many of its adjectives are registered and judged trait-new.  The report would then show covered heads that still hold new traits (the 15 heads in § 4a) instead of calling them filled.  Evidence: the § 4a table.  This answers [plan 02](../../trait_gap_generation/02_roget_wordnet.md)'s "gaps by concept" better than the head state alone.
5. **No change** to the head selection, the head-scope skip or the Class I-III scope for the harvest.  Their fitting discards are with the censuses: 0 of 100 unregistered discards read are new traits.  Harvesting the 400 unselected in-scope heads would add 824 new rows at about $6.5 for M1, for an expected yield of new traits near zero (0 of 100 unregistered discards read; at most 3.7%).
6. **Minor ($0).**  Before the floor, try the hyphenated form of an unlisted closed-up compound.  The Gutenberg text spells closetongued, scotfree and halfstarved as one word ([pg10681.txt](../../../data/external/roget/pg10681.txt), lines 14151, 21252 and 15711), so they score Zipf 0.  The fix affects about 5 words.
7. **Not this gate, for the owners of the gates concerned:**
   - The parser leaves verbs in head 659's Adj block (deflower, deprave and others), which affects a skipped head only.
   - M1 called unlikely, joined together, misnamed and hindering traits; that belongs to [m1_traithood.md](./m1_traithood.md).
   - M1 turned irresolute away.
   - The one-word-per-group rule is a larger discard than the Zipf line.  Of the 753 clean words not submitted in harvested heads, 400 are registered (291 traits, 196 new) and 353 are not; a sample of 25 of the 353 held 2 trait words (froward, cussed).  It has the same profile as the head selection: harmless while the censuses overlap.
