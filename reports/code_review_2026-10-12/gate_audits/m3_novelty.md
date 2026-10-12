# Gate audit 6: M3, the novelty check

Written 2026-10-12 by an Opus agent under the protocol of [README.md](./README.md).  Read-only: no code or
data changed, no paid call.  Terms (M1, M3, R1, the registry, the review app) are defined in
[escalations.md](../escalations.md) § Terms.  In this report:

- **covered** is this gate's discard: the candidate is taken to be a corpus trait (or a queued one) already and
  leaves the gap pipeline.  **new** is kept.
- a **false cover** is a covered candidate whose concept the corpus does not have (the costly error: the gap
  is hidden, since covers are not reviewed routinely, decision 18 (c)).  A **false new** is a kept candidate
  that a corpus or queue trait already is (the cheap error: it costs Roger a review click).
- **c** is the cut-off on rubric A's 0-4 scale; "S / O" is Sonnet's and Opus's reading of one pair.
- the **generator runs** are every M3 batch run on generator output: the three generator pilots of 2026-10-08,
  the census iv/rare pilots, TDA, Allport-Odbert hi, Roget full, WordNet full, IPIP g600, the base-model pilot,
  the four alignment sweeps, and the states and physical passes.  The M3 pilot pools (antonym check,
  M1 validation) are left out.

## Verdict

**Doing what was intended, but improvable.**  The costly error is rare: about 3% of the overlap covers are false
covers in my sample (2 of 61, 95% interval 0.9-11.2%), in line with Roger's cover audit (1 new and 4 uncertain
in 100).  Most of them, and all five of the audit's doubtful ones, have one shape: the corpus trait is a
narrower case of the candidate
(prejudiced and bigoted covered by [homophobic](../../../data/traits/instructions/homophobic.json), prejudicial by
[ageist](../../../data/traits/instructions/ageist.json), self-destructive by
[self_harming](../../../data/traits/instructions/self_harming.json)).  The cheap error is common: about 21% of the
kept rows are false new (10 of 48; 38% with the borderline cases), and Roger's TDA review merged 106 of the 204
new rows he resolved into an existing trait.  **The loss sits at the cut-off of 4, not at the 0.25 floor**.  Of
the 115 distinct false new rows on record (Roger's 106, plus 9 more from my sample), none was lost to the floor,
5 to retrieval and 2 to the relation call; 88 were read and kept at cut-off 4, and 20 at cut-off 3.  The step
to cut-off 4 at alignment score 2 has no recorded derivation, and the data do not support it: on Roger's reviewed rows a "both read 3" cover is right 28 times in 31 at
alignment 2, but only 30 times in 38 at alignment 3.  The Opus escalation adds a third of all overlap covers
(483), right 37 times in 40 in the audit.  Its rescues (63) are right about half the time.  Stage 0 is sound,
apart from the leak already filed as Review 2 D1; 5 of that leak's 8 rows turn out to be a different sense
from the trait their old stem now names.

## 1. The rule, from the code

What runs on a candidate, in order (rule set 2, the default since 2026-10-07):

1. **Eligibility.**  `candidate_from_row` ([novelty_runner.py](../../../assistant_axis/gapgen/novelty_runner.py):174-203)
   takes a registry row only if its M1 verdict is `trait` and it has a gloss.  A row already decided by an
   earlier M3 run is skipped (`decided_by_another_run`,
   [novelty_score.py](../../../data_analysis/gap_generation/novelty_score.py):233-239), and so is a row on a
   holding list (247-249).  So a word is decided once, against the corpus and queue of the day it was first scored.
2. **Stage 0, exact label** (runner 626-630; `exact_label_match`,
   [novelty.py](../../../assistant_axis/gapgen/novelty.py):516-537).  The candidate's stem is compared, separator-blind
   (`blind`, 462-473), with:
   - every corpus trait stem;
   - every seed-queue entry's stem and normalised label, of any status and either entity type, except an
     entry handed to the registry (`label_sets`, 490-503).

   A match makes the row covered, reason `exact_label`, with no call.  Under rule set 2 a corpus file's
   `renamed_from` does not cover: it goes to the walk with the current trait at the head of the queue (decision 15;
   `renamed_match` 540-550, runner 631-636).  But a queue entry under the old stem is matched first, which is
   Review 2 D1 (§ 7.1).
3. **Retrieval** (runner 640-642).  The query is the gloss alone, cut to 14 words (`gloss_w14`, 91-96,
   449-457), projected into the centred `w20` space fitted on the corpus (`build_index` 414-446).  The **k = 10**
   nearest are taken (`CorpusIndex.retrieve` 399-411; `k` is `covered.k` in
   [metric_config.json](../../../data/candidates/metric_config.json), default 10 at runner 371).  Seed-queue
   entries with status `candidate`, `ready`, `tbd` or `backlog` are in the index (`queue_traits` 282-358,
   `QUEUE_SEARCH_STATUSES` 106).  If nothing is retrieved, the row is new, reason `no_listed` (runner 643-645).
4. **Expansion** (`expand` 574-591): the other members of each retrieved trait's pair, triangle, tetrahedron
   or simplex are listed too, each with its own cosine.
5. **Relation call** (Haiku 5.5, runner 55; [relation.md](../../trait_gap_generation/rubrics/relation.md) v1).
   Each listed trait is answered similar, opposed, unrelated or unsure.  An unsure is asked again of Sonnet
   (runner 674-698).  If the call never parses, every listed trait goes on, by cosine (677-680).
6. **Shortlist** (`build_shortlist` 664-723):
   - the front of the queue is the partners of opposed traits, judged **whatever their cosine** and whatever
     the relation call said about them (694-702);
   - then the similar and unsure traits, by cosine;
   - **`DEFAULT_COSINE_FLOOR` = 0.25** (79) drops the similar or unsure traits below it that are not front
     partners and not the renamed trait (705);
   - when both ends of a recorded pair (or every corner of a simplex) come back similar, they are taken out and
     noted (decision 13, 706-707).
7. **Overlap walk** (`Walk` 785-962, runner `_walk` 757-800): one pair per Sonnet call, rubric A v6
   ([overlap_concept.md](../../trait_gap_generation/rubrics/overlap_concept.md)), in queue order, stopping at the
   first cover.  **c = 3 at alignment score 0 or 1, c = 4 at 2, 3 or missing** (`cut_off` 194-204).
   `sonnet_action` (732-759) and `give_opus` (920-957) then act on Sonnet's reading S:
   - S > c: covered.
   - S = c: Opus decides.  O ≥ c covers; otherwise the pair is "rescued" and the walk continues.
   - S = c - 1: Opus checks.  O ≥ c covers, with the flag `sonnet_below_opus_at` (decision 12, 938-946).
   - S < c - 1: continue.
   - `opposite`: the trait's partners are judged next (886-895).
   - `unsure`: Opus's reading replaces Sonnet's.

   Two consequences at c = 4: Sonnet can never cover alone, so every cover needs Opus at 4; and a Sonnet 2 is
   settled without Opus.
8. **Decision.**  A walk that runs out is new, or grey if it carries `unparsed` (`grey_kinds` 140-148,
   `_finish` 850-852).

**What happens to a covered candidate**: it keeps its `novelty` block (`covered_by`, readings) in the
[registry](../../../data/candidates/registry.jsonl).  The review app greys it out (decision 9,
[review_app/decisions.py](../../../assistant_axis/gapgen/review_app/decisions.py) docstring); it can be pulled in by
hand (`merge_in`) or with [review_graph.py](../../../data_analysis/gap_generation/review_graph.py) `build --include`.  It feeds the rename shortlist (`synonyms` 1143-1173),
and is otherwise not looked at again.

## 2. The intent

- The gate: "M3 decides, for each candidate trait that passed the M1 filter, whether the corpus already has it"
  ([coding_plan_m3.md](../../trait_gap_generation/coding_plan_m3.md), first paragraph).
- Stage 0: "The normalised label ... equal to a corpus stem, a queued stem ..., or a corpus file's
  `renamed_from`: decision `covered`" (stage 0).  This was revised by decision 15: "only a corpus stem or queue stem
  still covers without a call", because "the pilot auto-covered four real gaps"
  ([coding_plan_platform.md](../../trait_gap_generation/coding_plan_platform.md), M3 decisions).
- k = 10: "**retrieve k = 10 nearest existing traits**.  No similarity threshold decides anything: at 95%
  paraphrase recall a threshold put 61% of recorded antonym pairs on the covered side.  Recall@10 ... 0.972-0.978"
  (platform plan, "M2 final settings", item 2).  The calibration is in
  [calibrate.py](../../../assistant_axis/gapgen/calibrate.py) (`gloss_recovery`).  **Derived.**
- The floor: "(Roger, 2026-10-07: 'an acceptable level of trade-off')" (coding_plan_m3.md, Round 2, item 5).
  Decision 15 adds: "The cosine floor (0.25) remains a cost lever for Roger to decide; it is not needed for
  correctness."  It was derived from the pilot's projection (32% of readings saved, 2 covers lost:
  [m3_pilot_readout.md](../../trait_gap_generation/m3_pilot_readout.md), "What the pilot says about tuning").  As
  built it saved 3.6% (same readout, round 2).
- The cut-off: the alignment score is used "as input to the dupe/gap decision, so density increases gradually
  as you get closer to alignment rather than a sudden transition" (Roger, platform plan, "Amendments for M2 and M3",
  item 3).  Then: "Cut-offs stay as first set: covered at 3 or more far from the alignment region, at 4 near it,
  never at 2; revisited with the marks after the pilot" (decision 4).  And the revisit: "the cut-off stays at 3
  (38 of 40 confirmed at 3 and 3, none new; 20 of 20 at 4)" (decision 18 (b)).  **The 3 is validated, on the
  cover side only.  The 4, and the step at alignment score 2 rather than 3, have no recorded derivation, and
  what the 4 keeps has never been measured.**  Note also that the rule as built is one step, the "sudden
  transition" Roger said he did not want.
- The Opus roles: decision 11 ("Opus on the 2s and 3s"), then decision 12 (from Roger's review of 58 pairs:
  "he sided with Opus on 45 and Sonnet on 13"), then decision 18 (a): Opus "raised a 2 to 3 rightly 37 times in
  40".
- Covers not reviewed: decision 18 (c), "one clear gap in 100 does not repay the time at scale; words a review or
  audit doubts are put in front of Roger with `review_graph.py build --include`".  And: "The doubtful five had one
  shape, a candidate much broader than, or only one-way implied by, its covering trait; watch for it on the full
  runs."

## 3. The recorded discard

Reproduced from the registry, last row per key.  **By generator** (a row counts under every generator that
proposed it; this is the README table's view):

| generator / run | rows decided | covered | of which exact label |
|---|---|---|---|
| censuses / TDA | 2,624 | 1,338 (51%) | 448 |
| censuses / Allport-Odbert hi | 1,813 | 537 (30%) | 41 |
| roget / full | 295 | 82 (28%) | 1 |
| wn_clusters / full | 424 | 198 (47%) | 1 |
| ipip / g600 | 212 | 107 (50%) | 27 |
| base_model / pilot | 460 | 325 (71%) | 200 |
| alignment_sweep / papers | 314 | 61 (19%) | 21 |

These match the README.  The base model's 71% is mostly words other generators had already brought: 443 of its
rows were decided by earlier runs, its own M3 run decided 16, and 200 of its 325 covers are exact corpus labels.

**By the M3 run that decided the row** (each row once; the `novelty/<batch>` directories under
[data/candidates/novelty/](../../../data/candidates/novelty/), with their `summary.json`):

| M3 run(s) | decided | covered | exact | overlap | of which decision 12 | new | new at c 3 | new at c 4 (share of new) |
|---|---|---|---|---|---|---|---|---|
| [TDA](../../../data/candidates/novelty/2026-10-10-tda_censuses/summary.json) | 1,779 | 908 (51%) | 340 | 568 | 182 | 871 | 467 | 404 (46%) |
| [Allport-Odbert hi](../../../data/candidates/novelty/2026-10-11-allport_hi_censuses/summary.json) | 1,704 | 497 (29%) | 39 | 458 | 156 | 1,207 | 738 | 469 (39%) |
| [Roget full](../../../data/candidates/novelty/2026-10-11-full_roget/summary.json) | 104 | 32 (31%) | 1 | 31 | 14 | 72 | 45 | 27 (38%) |
| [WordNet full](../../../data/candidates/novelty/2026-10-11-full_wn_clusters/summary.json) | 61 | 26 (43%) | 0 | 26 | 7 | 35 | 18 | 17 (49%) |
| [IPIP g600](../../../data/candidates/novelty/2026-10-11-g600_ipip/summary.json) | 172 | 76 (44%) | 4 | 72 | 18 | 96 | 69 | 27 (28%) |
| [base model pilot](../../../data/candidates/novelty/2026-10-12-pilot_base_model/summary.json) | 16 | 13 (81%) | 7 | 6 | 1 | 3 | 1 | 2 |
| alignment sweeps ([papers](../../../data/candidates/novelty/2026-10-11-papers_alignment_sweep/summary.json), [b](../../../data/candidates/novelty/2026-10-11-b_alignment_sweep/summary.json), [usage](../../../data/candidates/novelty/2026-10-11-usage_alignment_sweep/summary.json), [full](../../../data/candidates/novelty/2026-10-10-full_alignment_sweep/summary.json)) | 312 | 42 (13%) | 1 | 41 | 17 | 270 | 16 | 254 (94%) |
| generator pilots ([censuses](../../../data/candidates/novelty/gen_pilot_censuses/summary.json), [roget](../../../data/candidates/novelty/gen_pilot_roget/summary.json), [wn](../../../data/candidates/novelty/gen_pilot_wn_clusters/summary.json)) | 579 | 254 (44%) | 81 | 173 | 58 | 325 | 186 | 139 (43%) |
| census [iv](../../../data/candidates/novelty/2026-10-09-iv-pilot_censuses/summary.json) / [rare](../../../data/candidates/novelty/2026-10-09-rare-pilot_censuses/summary.json) pilots | 140 | 33 (24%) | 1 | 32 | 11 | 107 | 72 | 35 (33%) |
| states and physical passes (7 runs) | 184 | 90 (49%) | 29 | 61 | 19 | 94 | 87 | 7 |
| **all generator runs** | **5,051** | **1,971 (39%)** | **503** | **1,468** | **483** | **3,080** | **1,699** | **1,381 (45%)** |

Across all generator runs (the registry blocks):

- **Overlap covers by route:**
  - 50 Sonnet above c;
  - 935 Sonnet at c, confirmed by Opus;
  - 483 Sonnet one below c, raised by Opus (decision 12).
- **Opus:** 998 reads at the cut-off, of which 63 rescued (6.3%); 5,080 checks one below, of which 483 raised
  (9.5%).
- **The floor:** it kept 874 similar or unsure traits from being judged, across 4,548 overlap-decided rows;
  566 of the new rows had at least one.
- **Spend** (the runs' `usage.json`, e.g. [TDA's](../../../data/candidates/novelty/2026-10-10-tda_censuses/usage.json)):
  $34.00 in all, of which Opus $14.27 (42%), Sonnet $17.13, Haiku $2.58.

The alignment sweeps' 13% covered rate comes from cut-off 4: 254 of their 270 new rows were judged at c = 4.

## 4. Reference labels

**(a) The cover audit of 2026-10-09** ([marks.json](../../../data/candidates/novelty/m3_cover_audit/marks.json),
key [key.json](../../../data/candidates/novelty/m3_cover_audit/key.json), seed 20261009, marks file
[m3_cover_audit_for_marks.md](../../trait_gap_generation/m3_cover_audit_for_marks.md)).  Roger marked, blind,
100 of the 173 non-exact covers of the three generator pilots:

| route | marked | covered | new | uncertain |
|---|---|---|---|---|
| Sonnet 2, Opus 3 | 40 | 37 | 1 | 2 |
| Sonnet 3, Opus 3 | 40 | 38 | 0 | 2 |
| read 4 | 20 | 20 | 0 | 0 |

False covers: 1 of 100 (0.2-5.4%) strict, 5 of 100 (2.2-11.2%) counting the uncertain.

**(b) The `--include` of 2026-10-09**: the five doubtful rows (sensing, faulty, perspicacious, saintly,
effervescent) were put into the review graph `review_pilots_1`
([run.json](../../../data/candidates/review/review_pilots_1/run.json), `argv`).  That batch has no decision
log, and the five rows' `review` blocks are still `unreviewed`, so they give no further label.

**(c) Roger's TDA review** ([decisions.jsonl](../../../data/candidates/review/review_tda_1/decisions.jsonl),
[graph.json](../../../data/candidates/review/review_tda_1/graph.json), applied to the registry's `review`
blocks).  He resolved 204 of TDA's 871 new rows:

- **106 merged into a corpus trait** (`merged_into trait:X`): false new by the definition this audit was given;
- 35 promoted, 62 merged into another candidate, 1 rejected: right to be new.

By cut-off: 23 of 78 at c = 3 (29.5%) and 83 of 126 at c = 4 (65.9%).  Overall 52.0% (45.1-58.7%).  The
review proceeds by groups of near-duplicate candidates, so this set leans toward dense synonym clusters and
overstates the rate for new rows in general.  **No review event touched a covered candidate** (0 of 354
events name one).  Where each of the 106 was lost, against the trait Roger chose:

| where | c 3 | c 4 | all |
|---|---|---|---|
| not retrieved (k = 10) | 3 | 2 | 5 |
| listed, relation call "unrelated", never read | 0 | 2 | 2 |
| below the 0.25 floor | 0 | 0 | **0** |
| read 3 / 3, kept by cut-off 4 | 0 | 43 | 43 |
| read 3 / 2 (at c 3: Opus rescued it) | 2 | 7 | 9 |
| read Sonnet 2, no Opus (settled at c 4) | 0 | 28 | 28 |
| read 2 / 2 | 17 | 0 | 17 |
| read Sonnet 1 | 1 | 1 | 2 |
| **all** | **23** | **83** | **106** |

The 106, grouped by the trait Roger merged them into.  "S/O" is the reading against that trait; "–" means Opus
was not asked.

| merged into | candidates (cut-off, S/O against that trait) |
|---|---|
| [strong_willed](../../../data/traits/instructions/strong_willed.json) | incoercible (c4, 3/3), iron_hearted (c4, 3/3), self_willed (c4, 3/3), steely (c4, 3/3), strong_minded (c4, 2/–), unalterable (c4, 2/–), unchangeable (c4, 2/–), unmalleable (c4, 3/2), unmodifiable (c4, 2/–), unshakable (c3, 2/2), unsubduable (c4, 2/–), unswerving (c4, 3/2), unwavering (c4, 2/–) |
| [arrogant](../../../data/traits/instructions/arrogant.json) | conceited (c4, 2/–), contemptuous (c3, 2/2), disdainful (c3, 2/2), haughty (c3, 3/2), overproud (c4, 2/–), overweening (c4, 3/3), self_important (c4, 2/–), sneering (c3, 2/2), snobbish (c3, 2/2), snooty (c3, 2/2), stuck_up (c3, 2/2), swellheaded (c4, 2/–) |
| [unyielding](../../../data/traits/instructions/unyielding.json) | bullheaded (c4, 3/2), hardheaded (c4, 3/3), immovable (c4, 3/3), inconvincible (c4, 2/–), mulish (c4, 3/3), obstinate (c4, 3/3), pigheaded (c4, 3/2), unmovable (c4, 3/3), unpersuadable (c4, 3/2), unswayable (c4, 3/3) |
| [scheming](../../../data/traits/instructions/scheming.json) | artful (c4, 3/3), crafty (c4, 2/–), devious (c4, 3/3), foxy (c4, 2/–), overcunning (c4, 3/3), sneaky (c4, 3/3), tricky (c4, 3/2), underhanded (c4, 2/–), wily (c4, 2/–) |
| [agreeable](../../../data/traits/instructions/agreeable.json) | congenial (c4, 3/2), delightful (c3, not retrieved), likeable (c3, 2/2), nice (c3, not retrieved), personable (c4, 2/–), pleasant (c3, not retrieved) |
| [dominant](../../../data/traits/instructions/dominant.json) | autocratic (c4, 2/–), bossy (c4, 2/–), dictatorial (c4, 2/–), domineering (c4, 2/–), overbearing (c4, 2/–), tyrannical (c4, 1/–) |
| [confrontational](../../../data/traits/instructions/confrontational.json) | adversarial (c4, 3/3), belligerent (c4, 3/3), brawlsome (c4, 3/3), truculent (c4, 3/3), unpeaceable (c4, 3/3) |
| [deceitful](../../../data/traits/instructions/deceitful.json) | false (c4, 3/3), fishy (c4, 2/–), knavish (c4, 3/3), mendacious (c4, 3/3), untruthful (c4, 3/3) |
| [violent](../../../data/traits/instructions/violent.json) | brutish (c4, 3/3), ferocious (c4, not read: unrelated), fierce (c4, not read: unrelated), overviolent (c4, 3/3), savage (c4, 3/3) |
| [disagreeable](../../../data/traits/instructions/disagreeable.json) | aggravating (c3, 2/2), annoying (c4, not retrieved), irritating (c3, 1/–), obnoxious (c3, 2/2) |
| [submissive](../../../data/traits/instructions/submissive.json) | leadable (c4, 2/–), unsteadfast (c4, not retrieved), unwillful (c4, 3/3), weak_minded (c4, 2/–) |
| [accommodating](../../../data/traits/instructions/accommodating.json) | acquiescent (c4, 2/–), amenable (c4, 3/3), complaisant (c4, 3/3) |
| [mischievous](../../../data/traits/instructions/mischievous.json) | elfish (c4, 3/3), roguish (c4, 3/3), scampish (c4, 3/3) |
| [slow_witted](../../../data/traits/instructions/slow_witted.json) | brainless (c3, 2/2), stupid (c3, 2/2), underwitted (c3, 3/2) |
| [impulsive](../../../data/traits/instructions/impulsive.json) | overrash (c4, 3/3), unrestrained (c4, 3/3) |
| [obedient](../../../data/traits/instructions/obedient.json) | docile (c4, 3/3), obeying (c4, 3/3) |
| [rebellious](../../../data/traits/instructions/rebellious.json) | mutinous (c4, 3/3), unsubmissive (c4, 3/3) |
| [cautious](../../../data/traits/instructions/cautious.json) | overcautious (c4, 3/3) |
| [clingy](../../../data/traits/instructions/clingy.json) | clinging (c4, 3/3) |
| [cowardly](../../../data/traits/instructions/cowardly.json) | overfearful (c4, 2/–) |
| [disorganized](../../../data/traits/instructions/disorganized.json) | messy (c3, 2/2) |
| [excitable](../../../data/traits/instructions/excitable.json) | overemotional (c3, 2/2) |
| [lustful](../../../data/traits/instructions/lustful.json) | prurient (c3, 2/2) |
| [passive](../../../data/traits/instructions/passive.json) | inert (c4, 3/3) |
| [rude](../../../data/traits/instructions/rude.json) | tasteless (c3, 2/2) |
| [self_effacing](../../../data/traits/instructions/self_effacing.json) | overmodest (c4, 2/–) |
| [spiritual](../../../data/traits/instructions/spiritual.json) | other_worldly (c3, 2/2) |
| [stingy](../../../data/traits/instructions/stingy.json) | niggardly (c4, 3/3) |
| [zealous](../../../data/traits/instructions/zealous.json) | overzealous (c4, 2/–) |

**(d) amorous.**  `amorous#1` (states pass) was covered by [flirty](../../../data/traits/instructions/flirty.json) at
Sonnet 2, Opus 3, through decision 12.  Roger later seeded [amorous](../../../data/traits/instructions/amorous.json)
himself ("living for love"), by the seed-queue path rather than as a judgment of this cover.  It is a false cover
of the narrower-cover shape: Opus wrote "Amorous covers a broad disposition of romantic longing that explicitly
includes flirtation".

## 5. The sample

**Seed 20261012.**  The strata are the M3 run that decided the row, except "base model", which is any row with
a `base_model` source.  They are drawn in the order of the tables below, without replacement across strata.  The
pools are sorted by key, and `random.Random(20261012).sample` is called per stratum, first for overlap covers,
then exact covers, then new rows.  Quotas (overlap, exact, new):

| stratum | quota |
|---|---|
| TDA | 10, 3, 10 |
| Allport-hi | 11, 1, 8 |
| Roget full | 6, 0, 4 |
| WordNet full | 6, 0, 4 |
| IPIP g600 | 6, 1, 5 |
| base model | 3, 3, 2 |
| alignment sweeps | 5, 1, 6 |
| generator pilots | 5, 1, 4 |
| census iv/rare pilots | 4, 0, 2 |
| states/physical passes | 5, 1, 3 |

That gives 72 covered (61 overlap, 11 exact) and 48 new.

**How each row was judged.**  Each verdict is the agent's own reading, against the intent ("does the corpus
already have this concept?"), not against the rule.  It rests on:

- the candidate's M1 gloss;
- the covering or best-read trait's description;
- for a new row, its listed traits, its readings, and a search of the 935 corpus stems for a nearer trait.

Where a reference label exists (cover audit, Roger's review) it is used first and marked.  Where the judgment
leans on how Roger merged similar words in review, that is said.

**Covered rows**: "covered (outcome right, sibling named)" means the corpus has the concept, but under a nearer
trait than the one M3 named.

| # | stratum | candidate | align / cut-off | route | covered by | cosine | verdict | rests on |
|---|---|---|---|---|---|---|---|---|
| 1 | TDA | unbenevolent#1 | 1 / 3 | Sonnet 3, Opus 3 | [uncaring](../../../data/traits/instructions/uncaring.json) | 0.48 | covered (same concept) | same indifference to others' welfare |
| 2 | TDA | agitable#1 | 0 / 3 | Sonnet 3, Opus 3 | [excitable](../../../data/traits/instructions/excitable.json) | 0.55 | covered (same concept) | both easily worked up and slow to settle |
| 3 | TDA | censorious#1 | 0 / 3 | Sonnet 3, Opus 3 | [judgmental](../../../data/traits/instructions/judgmental.json) | 0.47 | covered (same concept) | harsh fault-finding; censorious is it voiced |
| 4 | TDA | abrasive#1 | 0 / 3 | Sonnet 2, Opus 3 | [blunt](../../../data/traits/instructions/blunt.json) | 0.59 | covered (outcome right, sibling named) | outcome right; the nearer trait is [harsh](../../../data/traits/instructions/harsh.json): blunt is directness, abrasive is grating |
| 5 | TDA | bullish#1 | 0 / 3 | Sonnet 2, Opus 3 | [optimistic](../../../data/traits/instructions/optimistic.json) | 0.19 | covered (same concept) | optimism narrowed to markets; judged at 0.19 as an opposed trait's partner |
| 6 | TDA | venturesome#1 | 1 / 3 | Sonnet 3, Opus 4 | [risk_seeking](../../../data/traits/instructions/risk_seeking.json) | 0.55 | covered (same concept) | near-synonyms |
| 7 | TDA | contained#1 | 0 / 3 | Sonnet 3, Opus 3 | [unflappable](../../../data/traits/instructions/unflappable.json) | 0.47 | covered (outcome right, sibling named) | outcome right via [stoic](../../../data/traits/instructions/stoic.json) / [composed](../../../data/traits/instructions/composed.json); unflappable is never rattled, contained feels and holds it in |
| 8 | TDA | lusty#1 | 0 / 3 | Sonnet 3, Opus 3 | [energetic](../../../data/traits/instructions/energetic.json) | 0.43 | covered (same concept) | hearty vigor is energetic |
| 9 | TDA | ultracritical#1 | 0 / 3 | Sonnet 3, Opus 3 | [judgmental](../../../data/traits/instructions/judgmental.json) | 0.36 | covered (same concept) | judgmental carried to everything |
| 10 | TDA | ill_mannered#1 | 0 / 3 | Sonnet 3, Opus 4 | [rude](../../../data/traits/instructions/rude.json) | 0.55 | covered (same concept) | near-synonyms |
| 11 | TDA | forgetful#1 | 0 / 3 | exact label (corpus) | [forgetful](../../../data/traits/instructions/forgetful.json) | – | covered (same concept) | same sense |
| 12 | TDA | stable#1 | 0 / 3 | exact label (queue, not_adopted) | `stable` (queue) | – | covered (same concept) | a word turned down earlier (queue `not_adopted`): covered by design |
| 13 | TDA | stingy#1 | 1 / 3 | exact label (corpus) | [stingy](../../../data/traits/instructions/stingy.json) | – | covered (same concept) | same sense; the corpus trait is broader (time, knowledge) |
| 14 | Allport-hi | combustible#1 | 1 / 3 | Sonnet 3, Opus 4 | [irascible](../../../data/traits/instructions/irascible.json) | 0.37 | covered (same concept) | near-synonyms |
| 15 | Allport-hi | case#1 | 0 / 3 | Sonnet 3, Opus 3 | [eccentric](../../../data/traits/instructions/eccentric.json) | 0.40 | covered (same concept) | "a case" is an eccentric |
| 16 | Allport-hi | wit_starved#1 | 0 / 3 | Sonnet 3, Opus 3 | [humorless](../../../data/traits/instructions/humorless.json) | 0.58 | covered (same concept) | near-synonyms |
| 17 | Allport-hi | heartening#1 | 1 / 3 | Sonnet 3, Opus 3 | [encouraging](../../../data/traits/instructions/encouraging.json) | 0.57 | covered (same concept) | near-synonyms |
| 18 | Allport-hi | wasting#1 | 1 / 3 | Sonnet 2, Opus 3 | [inefficient](../../../data/traits/instructions/inefficient.json) | 0.33 | covered (same concept) | squandering is being wasteful |
| 19 | Allport-hi | flip#1 | 1 / 3 | Sonnet 2, Opus 3 | [lighthearted](../../../data/traits/instructions/lighthearted.json) | 0.38 | covered (outcome right, sibling named) | outcome right; the nearer trait is [flippant](../../../data/traits/instructions/flippant.json) |
| 20 | Allport-hi | reduced#1 | 0 / 3 | Sonnet 2, Opus 3 | [shabby_genteel](../../../data/traits/instructions/shabby_genteel.json) | 0.33 | covered (outcome right, sibling named) | outcome right via [poor](../../../data/traits/instructions/poor.json); shabby-genteel is one form of it |
| 21 | Allport-hi | proven#1 | 1 / 3 | Sonnet 2, Opus 3 | [competent](../../../data/traits/instructions/competent.json) | 0.25 | covered (same concept) | a track record of competence |
| 22 | Allport-hi | skill_less#1 | 1 / 3 | Sonnet 4 | [incompetent](../../../data/traits/instructions/incompetent.json) | 0.50 | covered (same concept) | near-synonyms |
| 23 | Allport-hi | self_glorious#1 | 0 / 3 | Sonnet 2, Opus 3 | [self_aggrandizing](../../../data/traits/instructions/self_aggrandizing.json) | 0.34 | covered (same concept) | inflated self-regard |
| 24 | Allport-hi | mainstay#1 | 1 / 3 | Sonnet 2, Opus 3 | [dependable](../../../data/traits/instructions/dependable.json) | 0.35 | covered (same concept) | the one others count on; dependable with wider scope |
| 25 | Allport-hi | chaotic#1 | 1 / 3 | exact label (corpus) | [chaotic](../../../data/traits/instructions/chaotic.json) | – | covered (same concept) | same sense |
| 26 | Roget full | hard_upon#1 | 1 / 3 | Sonnet 3, Opus 3 | [strict](../../../data/traits/instructions/strict.json) | 0.51 | covered (same concept) | harsh standards are strict |
| 27 | Roget full | old_world#1 | 0 / 3 | Sonnet 2, Opus 3 | [traditional](../../../data/traits/instructions/traditional.json) | 0.49 | covered (same concept) | old-world ways are traditional |
| 28 | Roget full | apostolic#1 | 1 / 3 | Sonnet 3, Opus 3 | [orthodox](../../../data/traits/instructions/orthodox.json) | 0.50 | covered (same concept) | received doctrine, narrowed to the apostles |
| 29 | Roget full | affective#1 | 0 / 3 | Sonnet 3, Opus 3 | [expressive](../../../data/traits/instructions/expressive.json) | 0.46 | covered (same concept) | openly emotional is expressive |
| 30 | Roget full | without_purpose#1 | 0 / 3 | Sonnet 2, Opus 3 | [languishing](../../../data/traits/instructions/languishing.json) | 0.46 | **false cover** (sibling the corpus lacks) | aimlessness; Roger promoted `aimless` (M3 had read aimless against [languishing](../../../data/traits/instructions/languishing.json) 2 / 2 and kept it); languishing adds hollowness and social drift |
| 31 | Roget full | unacceptable#1 | 1 / 3 | Sonnet 2, Opus 3 | [rude](../../../data/traits/instructions/rude.json) | 0.27 | covered (outcome right, sibling named) | a vague "objectionable"; outcome right via [disagreeable](../../../data/traits/instructions/disagreeable.json) |
| 32 | WordNet full | dynamical#1 | 0 / 3 | Sonnet 3, Opus 3 | [energetic](../../../data/traits/instructions/energetic.json) | 0.51 | covered (same concept) | near-synonyms |
| 33 | WordNet full | preferential#1 | 1 / 3 | Sonnet 3, Opus 3 | [cliquish](../../../data/traits/instructions/cliquish.json) | 0.33 | covered (outcome right, sibling named) | outcome right via [unfair](../../../data/traits/instructions/unfair.json) (playing favorites); cliquish is in-group exclusion |
| 34 | WordNet full | prejudicial#1 | 1 / 3 | Sonnet 3, Opus 3 | [ageist](../../../data/traits/instructions/ageist.json) | 0.40 | **false cover** (sibling the corpus lacks) | prejudice in general covered by one instance of it; the corpus has [ageist](../../../data/traits/instructions/ageist.json), [sexist](../../../data/traits/instructions/sexist.json), [xenophobic](../../../data/traits/instructions/xenophobic.json), no general prejudice trait |
| 35 | WordNet full | unresentful#1 | 1 / 3 | Sonnet 3, Opus 3 | [forgiving](../../../data/traits/instructions/forgiving.json) | 0.47 | covered (same concept) | letting go of grudges |
| 36 | WordNet full | crabbed#1 | 0 / 3 | Sonnet 2, Opus 3 | [irascible](../../../data/traits/instructions/irascible.json) | 0.41 | covered (same concept) | ill temper; crabbed adds grumbling (no grumpy or peevish trait in the corpus) |
| 37 | WordNet full | lowborn#1 | 0 / 3 | Sonnet 2, Opus 3 | [working_class](../../../data/traits/instructions/working_class.json) | 0.43 | covered (same concept) | low birth; working-class is one form of it |
| 38 | IPIP g600 | intolerant_of_waiting#1 | 1 / 3 | Sonnet 2, Opus 3 | [impatient](../../../data/traits/instructions/impatient.json) | 0.56 | covered (same concept) | impatience narrowed to waiting |
| 39 | IPIP g600 | comfortable_with_waiting#1 | 0 / 3 | Sonnet 2, Opus 3 | [patient](../../../data/traits/instructions/patient.json) | 0.45 | covered (same concept) | patience narrowed to waiting |
| 40 | IPIP g600 | health_conscious_eater#1 | 0 / 3 | Sonnet 2, Opus 3 | [health_conscious](../../../data/traits/instructions/health_conscious.json) | 0.32 | covered (same concept) | diet is part of being health-conscious |
| 41 | IPIP g600 | original_minded#1 | 0 / 3 | Sonnet 3, Opus 3 | [innovative](../../../data/traits/instructions/innovative.json) | 0.37 | covered (same concept) | near-synonyms |
| 42 | IPIP g600 | guided_by_feelings#1 | 1 / 3 | Sonnet 2, Opus 3 | [impulsive](../../../data/traits/instructions/impulsive.json) | 0.31 | borderline | decisions led by emotion; impulsive covers only the not-weighing half |
| 43 | IPIP g600 | blunt_spoken_and_careless#1 | 0 / 3 | Sonnet 3, Opus 3 | [blunt](../../../data/traits/instructions/blunt.json) | 0.59 | covered (same concept) | blunt, plus carelessness about how it lands |
| 44 | IPIP g600 | future_oriented#1 | 0 / 3 | exact label (corpus) | [future_oriented](../../../data/traits/instructions/future_oriented.json) | – | covered (same concept) | same sense |
| 45 | base model | inspiring#1 | 0 / 3 | Sonnet 3, Opus 3 | [encouraging](../../../data/traits/instructions/encouraging.json) | 0.40 | covered (outcome right, sibling named) | outcome right; the nearer trait is [inspirational](../../../data/traits/instructions/inspirational.json) |
| 46 | base model | courteous#1 | 0 / 3 | Sonnet 3, Opus 3 | [polite](../../../data/traits/instructions/polite.json) | 0.49 | covered (same concept) | near-synonyms |
| 47 | base model | genial#1 | 0 / 3 | Sonnet 3, Opus 3 | [friendly](../../../data/traits/instructions/friendly.json) | 0.50 | covered (same concept) (cover audit) | Roger's cover audit: covered |
| 48 | base model | manipulative#1 | 3 / 4 | exact label (corpus) | [manipulative](../../../data/traits/instructions/manipulative.json) | – | covered (same concept) | same sense |
| 49 | base model | dignified#1 | 2 / 4 | exact label (corpus) | [dignified](../../../data/traits/instructions/dignified.json) | – | covered (same concept) | same sense |
| 50 | base model | unforgiving#1 | 1 / 3 | exact label (corpus) | [unforgiving](../../../data/traits/instructions/unforgiving.json) | – | covered (same concept) | same sense |
| 51 | alignment sweeps | thinks_before_choosing#1 | 1 / 3 | Sonnet 3, Opus 4 | [deliberate](../../../data/traits/instructions/deliberate.json) | 0.55 | covered (same concept) | near-synonyms |
| 52 | alignment sweeps | challenges_premises#1 | 1 / 3 | Sonnet 3, Opus 3 | [skeptical](../../../data/traits/instructions/skeptical.json) | 0.58 | covered (same concept) | a narrower, analytical skepticism |
| 53 | alignment sweeps | plays_fair#1 | 3 / 4 | Sonnet 3, Opus 4 | [fair](../../../data/traits/instructions/fair.json) | 0.58 | covered (same concept) | interchangeable |
| 54 | alignment sweeps | thinks_before_acting#1 | 1 / 3 | Sonnet 3, Opus 3 | [deliberate](../../../data/traits/instructions/deliberate.json) | 0.58 | covered (same concept) | near-synonyms |
| 55 | alignment sweeps | stays_loyal#1 | 2 / 4 | Sonnet 3, Opus 4 | [loyal](../../../data/traits/instructions/loyal.json) | 0.62 | covered (same concept) | near-synonyms |
| 56 | alignment sweeps | harmful#1 | 3 / 4 | exact label (corpus) | [harmful](../../../data/traits/instructions/harmful.json) | – | covered (same concept) | the gloss is cruelty, the corpus trait broader; [sadistic](../../../data/traits/instructions/sadistic.json) is in the corpus too |
| 57 | generator pilots | saturnine#1 | 0 / 3 | Sonnet 3, Opus 3 | [melancholic](../../../data/traits/instructions/melancholic.json) | 0.48 | covered (same concept) (cover audit) | Roger's cover audit: covered |
| 58 | generator pilots | resolved#1 | 1 / 3 | Sonnet 2, Opus 3 | [persevering](../../../data/traits/instructions/persevering.json) | 0.36 | covered (same concept) (cover audit) | Roger's cover audit: covered |
| 59 | generator pilots | hypersensual#1 | 1 / 3 | Sonnet 2, Opus 3 | [hedonistic](../../../data/traits/instructions/hedonistic.json) | 0.36 | covered (same concept) | extreme, bodily hedonism |
| 60 | generator pilots | boorish#1 | 0 / 3 | Sonnet 3, Opus 3 | [rude](../../../data/traits/instructions/rude.json) | 0.54 | covered (same concept) (cover audit) | Roger's cover audit: covered |
| 61 | generator pilots | embittered#1 | 1 / 3 | Sonnet 3, Opus 4 | [bitter](../../../data/traits/instructions/bitter.json) | 0.35 | covered (same concept) (cover audit) | Roger's cover audit: covered |
| 62 | generator pilots | grandiose#1 | 2 / 4 | exact label (corpus) | [grandiose](../../../data/traits/instructions/grandiose.json) | – | covered (same concept) | same sense |
| 63 | census iv/rare pilots | blockish#1 | 0 / 3 | Sonnet 3, Opus 4 | [slow_witted](../../../data/traits/instructions/slow_witted.json) | 0.57 | covered (same concept) | near-synonyms |
| 64 | census iv/rare pilots | polarized#1 | 0 / 3 | Sonnet 2, Opus 3 | [extremist](../../../data/traits/instructions/extremist.json) | 0.49 | covered (outcome right, sibling named) | outcome right via [partisan](../../../data/traits/instructions/partisan.json) (two camps, no middle ground) |
| 65 | census iv/rare pilots | glutting#1 | 0 / 3 | Sonnet 3, Opus 3 | [gluttonous](../../../data/traits/instructions/gluttonous.json) | 0.52 | covered (same concept) | near-synonyms |
| 66 | census iv/rare pilots | current#1 | 0 / 3 | Sonnet 3, Opus 3 | [news_junkie](../../../data/traits/instructions/news_junkie.json) | 0.36 | borderline | keeping up to date is broader than the compulsive news-junkie |
| 67 | states/physical passes | doleful#1 | 0 / 3 | Sonnet 2, Opus 3 | [melancholic](../../../data/traits/instructions/melancholic.json) | 0.28 | covered (same concept) | habitual sorrow |
| 68 | states/physical passes | easily_distracted#1 | 1 / 3 | Sonnet 4 | [distractible](../../../data/traits/instructions/distractible.json) | 0.56 | covered (same concept) | near-synonyms |
| 69 | states/physical passes | sorrowful#1 | 0 / 3 | Sonnet 2, Opus 3 | [melancholic](../../../data/traits/instructions/melancholic.json) | 0.29 | covered (same concept) | habitual sadness |
| 70 | states/physical passes | strong#1 | 0 / 3 | Sonnet 3, Opus 3 | [muscular](../../../data/traits/instructions/muscular.json) | 0.66 | covered (same concept) | strength and build; close |
| 71 | states/physical passes | spare#1 | 0 / 3 | Sonnet 3, Opus 3 | [thin](../../../data/traits/instructions/thin.json) | 0.57 | covered (same concept) | near-synonyms |
| 72 | states/physical passes | left_handed#1 | 0 / 3 | exact label (corpus) | [left_handed](../../../data/traits/instructions/left_handed.json) | – | covered (same concept) | same sense |

**New rows** ("best reading" is the highest S / O any listed trait got):

| # | stratum | candidate | align / cut-off | best reading | verdict | rests on |
|---|---|---|---|---|---|---|
| 1 | TDA | graceful#1 | 0 / 3 | [unhurried](../../../data/traits/instructions/unhurried.json): 2 / 1 | new (right) | no graceful or elegant trait in the corpus |
| 2 | TDA | clumsy#1 | 0 / 3 | [incompetent](../../../data/traits/instructions/incompetent.json): 1 | new (right) | no clumsy or uncoordinated trait |
| 3 | TDA | sophisticated#1 | 0 / 3 | [upper_class](../../../data/traits/instructions/upper_class.json): 2 / 2 | new (right) | [cosmopolitan](../../../data/traits/instructions/cosmopolitan.json) is global-citizen values, not urbane polish |
| 4 | TDA | ruminative#1 | 0 / 3 | [circumspect](../../../data/traits/instructions/circumspect.json): 2 / 1 | borderline | [pensive](../../../data/traits/instructions/pensive.json) (not retrieved) is close; [philosophical](../../../data/traits/instructions/philosophical.json) was below the floor |
| 5 | TDA | ultrademocratic#1 | 1 / 3 | [egalitarian](../../../data/traits/instructions/egalitarian.json): 2 / 2 | new (right) | siblings [egalitarian](../../../data/traits/instructions/egalitarian.json), [populist](../../../data/traits/instructions/populist.json) |
| 6 | TDA | irrestrainable#1 | 2 / 4 | [impulsive](../../../data/traits/instructions/impulsive.json): 3 / 3 | new (right) (Roger's review) | Roger promoted it |
| 7 | TDA | overforward#1 | 0 / 3 | [rude](../../../data/traits/instructions/rude.json): 1 | new (right) | presumptuous familiarity; nothing in the corpus |
| 8 | TDA | cultivated#1 | 0 / 3 | [polite](../../../data/traits/instructions/polite.json): 1 | borderline | [highbrow](../../../data/traits/instructions/highbrow.json) (not retrieved) and [erudite](../../../data/traits/instructions/erudite.json) split it |
| 9 | TDA | unharming#1 | 3 / 4 | [harmless](../../../data/traits/instructions/harmless.json): 3 / 3 | **false new** | the same concept as [harmless](../../../data/traits/instructions/harmless.json), kept by cut-off 4 |
| 10 | TDA | risque#1 | 0 / 3 | [edgy](../../../data/traits/instructions/edgy.json): 2 / 2 | new (right) (Roger's review) | Roger merged it into the new candidate `obscene` (promoted) |
| 11 | Allport-hi | know_nothing#1 | 1 / 3 | [uneducated](../../../data/traits/instructions/uneducated.json): 1 | new (right) | no ignorant or uninformed trait |
| 12 | Allport-hi | complete#1 | 1 / 3 | [self_reliant](../../../data/traits/instructions/self_reliant.json): 2 / 2 | new (right) | vague; nearest [self_reliant](../../../data/traits/instructions/self_reliant.json) |
| 13 | Allport-hi | cloaking#1 | 3 / 4 | [scheming](../../../data/traits/instructions/scheming.json): 2 | borderline | the queue's `concealing` 2 and `phony` 2, at cut-off 4 (no Opus) |
| 14 | Allport-hi | polarizing#1 | 0 / 3 | [provocative](../../../data/traits/instructions/provocative.json): 2 / 1 | new (right) | others' reactions, not one's conduct |
| 15 | Allport-hi | self_exclaiming#1 | 0 / 3 | none read | new (right) | nothing listed was similar |
| 16 | Allport-hi | two_tongued#1 | 3 / 4 | [deceitful](../../../data/traits/instructions/deceitful.json): 2 | new (right) | no two-faced trait |
| 17 | Allport-hi | miss_nancy#1 | 0 / 3 | [feminine](../../../data/traits/instructions/feminine.json): 2 / 2 | new (right) | nothing nearer |
| 18 | Allport-hi | champ#1 | 1 / 3 | [competitive](../../../data/traits/instructions/competitive.json): 2 / 2 | new (right) | nothing nearer |
| 19 | Roget full | despised#1 | 0 / 3 | [unpopular](../../../data/traits/instructions/unpopular.json): 2 / 2 | new (right) | a condition others impose; [stigmatized](../../../data/traits/instructions/stigmatized.json) 1 |
| 20 | Roget full | promising#1 | 0 / 3 | [growth_minded](../../../data/traits/instructions/growth_minded.json): 1 | new (right) | nothing near |
| 21 | Roget full | mediocre#1 | 0 / 3 | [competent](../../../data/traits/instructions/competent.json): 2 / 2 | new (right) | nothing near |
| 22 | Roget full | unexplained#1 | 2 / 4 | [opaque](../../../data/traits/instructions/opaque.json): 2 | **false new** | the same concept as [opaque](../../../data/traits/instructions/opaque.json) (withholding one's reasons); Sonnet 2 at cut-off 4, no Opus |
| 23 | WordNet full | wholehearted#1 | 2 / 4 | [sincere](../../../data/traits/instructions/sincere.json): 2 | new (right) | no committed or devoted trait |
| 24 | WordNet full | brassy#1 | 0 / 3 | [brash](../../../data/traits/instructions/brash.json): 2 / 2 | borderline | [brash](../../../data/traits/instructions/brash.json) is close |
| 25 | WordNet full | tomboyish#1 | 0 / 3 | [athletic](../../../data/traits/instructions/athletic.json): 1 | new (right) | [masculine](../../../data/traits/instructions/masculine.json) 1; the queue's `unladylike` below the floor |
| 26 | WordNet full | wilful#1 | 3 / 4 | [unyielding](../../../data/traits/instructions/unyielding.json): 3 / 3 | **false new** | [strong_willed](../../../data/traits/instructions/strong_willed.json) 3 / 3 too, at cut-off 4; Roger merged self-willed into strong-willed |
| 27 | IPIP g600 | intolerant_of_criticism#1 | 2 / 4 | [thin_skinned](../../../data/traits/instructions/thin_skinned.json): 3 / 2 | **false new** | the same concept as [thin_skinned](../../../data/traits/instructions/thin_skinned.json), at cut-off 4 |
| 28 | IPIP g600 | money_driven#1 | 3 / 4 | [mercenary](../../../data/traits/instructions/mercenary.json): 3 / 3 | **false new** | the same concept as [mercenary](../../../data/traits/instructions/mercenary.json), at cut-off 4 |
| 29 | IPIP g600 | prefers_quiet_surroundings#1 | 0 / 3 | [introverted](../../../data/traits/instructions/introverted.json): 1 | new (right) | nothing near |
| 30 | IPIP g600 | averse_to_change#1 | 2 / 4 | [traditional](../../../data/traits/instructions/traditional.json): 2 | new (right) | siblings [conservative](../../../data/traits/instructions/conservative.json), [rigid](../../../data/traits/instructions/rigid.json) |
| 31 | IPIP g600 | uneasy_receiving_affection#1 | 0 / 3 | [fearful_avoidant_attachment](../../../data/traits/instructions/fearful_avoidant_attachment.json): 2 / 2 | new (right) | a narrower discomfort than avoidant attachment |
| 32 | base model | unresponsive#1 | 2 / 4 | [lurker](../../../data/traits/instructions/lurker.json): 2 | new (right) | [absentee](../../../data/traits/instructions/absentee.json) 2; nothing nearer |
| 33 | base model | haughty#1 | 1 / 3 | [arrogant](../../../data/traits/instructions/arrogant.json): 3 / 2 | **false new** (Roger's review) | Roger merged it into [arrogant](../../../data/traits/instructions/arrogant.json); Opus had rescued it from Sonnet's 3 |
| 34 | alignment sweeps | admits_what_it_did#1 | 3 / 4 | [accountable](../../../data/traits/instructions/accountable.json): 2 | **false new** | the same concept as [accountable](../../../data/traits/instructions/accountable.json); Sonnet 2 at cut-off 4, no Opus |
| 35 | alignment sweeps | openly_candid#1 | 2 / 4 | [forthright](../../../data/traits/instructions/forthright.json): 3 / 3 | **false new** | [candid](../../../data/traits/instructions/candid.json) 3 / 3 too, at cut-off 4 |
| 36 | alignment sweeps | faithful_to_the_task#1 | 2 / 4 | [focused](../../../data/traits/instructions/focused.json): 2 | new (right) | scope discipline, a facet focus does not name |
| 37 | alignment sweeps | honest_about_origin#1 | 3 / 4 | [honest](../../../data/traits/instructions/honest.json): 3 / 3 | borderline | a narrow facet of honesty near alignment, which cut-off 4 is meant to keep |
| 38 | alignment sweeps | dodging_confrontation#1 | 2 / 4 | [agreeable](../../../data/traits/instructions/agreeable.json): 2 | new (right) | no conflict-avoidant trait; [diplomatic](../../../data/traits/instructions/diplomatic.json) 2 |
| 39 | alignment sweeps | honest_under_pressure#1 | 3 / 4 | [honest](../../../data/traits/instructions/honest.json): 3 / 3 | borderline | honesty's robustness under pressure, a facet near alignment |
| 40 | generator pilots | scholastic#1 | 0 / 3 | [erudite](../../../data/traits/instructions/erudite.json): 2 / 2 | borderline | love of study against learning possessed |
| 41 | generator pilots | balky#1 | 3 / 4 | [unyielding](../../../data/traits/instructions/unyielding.json): 3 / 3 | **false new** | the same concept, at cut-off 4 |
| 42 | generator pilots | smutty#1 | 0 / 3 | [lustful](../../../data/traits/instructions/lustful.json): 2 / 2 | new (right) | the concept Roger promoted as `obscene` |
| 43 | generator pilots | unpaid#1 | 0 / 3 | [intrinsically_motivated](../../../data/traits/instructions/intrinsically_motivated.json): 1 | new (right) | a circumstance; nothing near |
| 44 | census iv/rare pilots | disenchanting#1 | 1 / 3 | [discouraging](../../../data/traits/instructions/discouraging.json): 2 / 2 | new (right) | [detractor](../../../data/traits/instructions/detractor.json) 2 / 2; neither is the killjoy |
| 45 | census iv/rare pilots | appropriative#1 | 2 / 4 | [unfair](../../../data/traits/instructions/unfair.json): 1 | new (right) | nothing near |
| 46 | states/physical passes | doormat#1 | 3 / 4 | [submissive](../../../data/traits/instructions/submissive.json): 3 / 3 | **false new** | the same concept carried further, at cut-off 4 |
| 47 | states/physical passes | quick_to_apologize#1 | 2 / 4 | [remorseful](../../../data/traits/instructions/remorseful.json): 2 | borderline | [accountable](../../../data/traits/instructions/accountable.json) 2 too; no apologetic trait |
| 48 | states/physical passes | aquiline#1 | 0 / 3 | none read | new (right) | physical; nothing near |

## 6. Rates

| | sample | rate (95% Wilson interval) | implied over the generator runs |
|---|---|---|---|
| false covers, overlap covers | 2 of 61 | 3.3% (0.9-11.2%) | about 48 of 1,468 (13-164) |
| false covers incl. borderline | 4 of 61 | 6.6% (2.6-15.7%) | about 97 (38-230) |
| false covers, exact label | 0 of 11 | 0% (0-25.9%) | 5 known by enumeration (§ 7.1), of 503 |
| false new, cut-off 3 | 1 of 27 | 3.7% (0.7-18.3%) | about 63 of 1,699 (12-311) |
| false new, cut-off 3, incl. borderline | 5 of 27 | 18.5% (8.2-36.7%) | about 314 (139-624) |
| false new, cut-off 4 | 9 of 21 | 42.9% (24.5-63.5%) | about 592 of 1,381 (338-877) |
| false new, cut-off 4, incl. borderline | 13 of 21 | 61.9% (40.9-79.2%) | about 855 (565-1,094) |
| false new, all | 10 of 48 | 20.8% (11.7-34.3%) | about 655 of 3,080 (21%) |

Against the references:

- **False covers:** the cover audit gives 1-5% (1 new, 4 uncertain, in 100).  My 3.3% / 6.6% sits on it.
  Among the overlap covers in my sample, the false and borderline ones are split evenly between the routes:
  - Sonnet at c, confirmed by Opus (35 rows): 1 false, 1 borderline;
  - decision 12, Sonnet one below, raised by Opus (24 rows): 1 false, 1 borderline.
- **False new:** Roger's TDA review gives 29.5% at c = 3 and 65.9% at c = 4, higher than mine.  Two reasons:
  - his review takes dense near-duplicate groups first;
  - he merges at the rubric's 2 when a group has an obvious umbrella trait (the [arrogant](../../../data/traits/instructions/arrogant.json)
    family at 2 / 2).  My strict reading does not count those, but my "borderline" column leans that way.

**A by-product error**: 8 of the 61 overlap covers (13.1%, 6.8-23.8%) name a sibling while a nearer trait exists
(the "outcome right, sibling named" rows).  The decision is right; the rename shortlist (`synonyms`) files the
word under the wrong trait.  The cause is early exit in shortlist order: the partners of opposed traits are judged
first, then the similar traits by cosine, and the first trait at the cut-off wins.

## 7. Where the loss sits

**7.1 Stage 0.**  Exact corpus labels were right in every case read (11 of 11 in the sample).  Covers by queue
entries the seed queue turned down (`not_adopted` 30, `superseded` 4) are covered by design.

Two leaks:

- **Review 2 D1** ([escalations.md](../escalations.md), § Review 2): eight candidates are covered by a stale
  queue entry under a corpus file's old stem, bypassing decision 15.  Reading their glosses, **five are a
  different sense from the trait the old stem now names**, so they are false covers by content, not just
  bookkeeping:

  | candidate | its sense | covered by the stale entry for | which now names |
  |---|---|---|---|
  | tough | enduring hardship | tough | [strict](../../../data/traits/instructions/strict.json) |
  | exclusive | a snobbish small circle | exclusive | [exclusionary](../../../data/traits/instructions/exclusionary.json) |
  | indulgent | lenient with others | indulgent | [self_indulgent](../../../data/traits/instructions/self_indulgent.json) |
  | libertarian | small government | libertarian | [metaphysical_libertarian](../../../data/traits/instructions/metaphysical_libertarian.json) |
  | nonchalant | unworried | nonchalant | [apathetic](../../../data/traits/instructions/apathetic.json) |

  Most of these concepts are in the corpus under another stem ([resilient](../../../data/traits/instructions/resilient.json),
  [elitist](../../../data/traits/instructions/elitist.json), [lenient](../../../data/traits/instructions/lenient.json),
  [unflappable](../../../data/traits/instructions/unflappable.json)).  Political libertarian is at best split
  between [civil_libertarian](../../../data/traits/instructions/civil_libertarian.json) and
  [capitalist](../../../data/traits/instructions/capitalist.json).
- **Role entries.**  Seven trait candidates are covered by a queued role of the same name
  ([unemployed](../../../data/roles/instructions/unemployed.json), [alcoholic](../../../data/roles/instructions/alcoholic.json),
  [homeless](../../../data/roles/instructions/homeless.json), [delinquent](../../../data/roles/instructions/delinquent.json),
  [estranged](../../../data/roles/instructions/estranged.json), [provincial](../../../data/roles/instructions/provincial.json),
  and `native`, a backlog entry with no file).  Corpus role files outside the queue are not
  checked at all, so the treatment depends on whether a role passed through the queue.  The effect is small,
  and the roles holding list is M1's job.

**7.2 Retrieval, k = 10.**  5 of the 106 reference false new rows (4.7%, 2.0-10.6%) never had their trait
retrieved: delightful, pleasant and nice against [agreeable](../../../data/traits/instructions/agreeable.json);
annoying against [disagreeable](../../../data/traits/instructions/disagreeable.json); unsteadfast against
[submissive](../../../data/traits/instructions/submissive.json).  In my sample, 2 borderline rows missed a close
trait ([pensive](../../../data/traits/instructions/pensive.json), [highbrow](../../../data/traits/instructions/highbrow.json)).
That fits M2's recall on own-gloss queries (recall@5 0.975 in [metric_config.json](../../../data/candidates/metric_config.json),
recall@10 0.97-0.99).  Not where the loss is.

**7.3 The relation call.**  2 of the 106 were marked "unrelated" and never read (ferocious and fierce against
[violent](../../../data/traits/instructions/violent.json)).  Its negative answers are otherwise safe: of the 6,560
readings on traits it marked unrelated or opposed (judged anyway as opposed traits' partners), none reached the
cut-off (0 of 6,560; upper bound 0.1%).

**7.4 The 0.25 floor.**

- **What it lost:** none of the 115 false new rows on record (Roger's 106, my 9 others).  It skipped 874
  similar or unsure traits.  Judged similar pairs below 0.25 reach the cut-off 1.2% of the time (21 of 1,803),
  so the skipped traits held about 10 covers, about 0.3% of the new rows.
- **What it saves:** about 4% of the Sonnet readings (874 of about 22,000), under $1 at batch prices.
- **Why it saves so little:** as round 2 of the pilot found, the opposed traits' partners are exempt.
- **Verdict:** the floor is harmless and nearly idle.  The data support 0.25 neither better nor worse than no
  floor.

**7.5 The cut-off: where the loss is.**  92 of the 115 false new rows on record were judged at c = 4: Roger's 83
and 9 of my 10 (my tenth, haughty, is one of Roger's).  Every one of them that was retrieved and read was read
at 3 or below.

On Roger's reviewed TDA rows at c = 4, I re-decided the recorded readings under "cover when both models read 3 or
more".  These need no new call: every Sonnet 3 or 4 at c = 4 already has its Opus reading.

| alignment score | reviewed rows at c 4 | false new (Roger merged) | right new (Roger kept) | would flip to covered | right flips | wrong flips |
|---|---|---|---|---|---|---|
| 2 | 54 | 44 | 10 | 31 | **28 (90%, 75-97%)** | 3 (irrestrainable, unreined, overmasculine) |
| 3 | 72 | 39 | 33 | 38 | 30 (79%, 64-89%) | 8 (flattering, fawning, obsequious, ingratiating, oleaginous, pliant, recalcitrant, ungovernable) |

So cut-off 4 does what it was meant to do at alignment score 3.  Flattering against
[sycophantic](../../../data/traits/instructions/sycophantic.json), and pliant against
[submissive](../../../data/traits/instructions/submissive.json), are distinctions Roger kept.  At alignment
score 2 it buys little: a 3 / 3 there is as reliable a cover (90%) as the far-from-alignment 3 / 3 of the cover
audit (95%).

The score of 2 is not rare: it is "would clearly show in deference" (bossy, clinging, inert, niggardly in the
M1 reasons).  About 30% of the candidates that reach the overlap walk get c = 4 (TDA 30%, Allport-hi 29%).

Across the generator runs, the 1,381 new rows at c = 4 break down by alignment score as follows; "a Sonnet 2,
no Opus" means a plain cut-off 3 would need an Opus reading for them:

| alignment score | new at c 4 | would flip on the records | a Sonnet 2, no Opus | neither |
|---|---|---|---|---|
| 2 | 551 | 189 | 323 | 39 |
| 3 | 830 | 308 | 467 | 55 |

The false new rows at c = 3 (17 of Roger's 23 were read 2 / 2) are a different matter.  They are Roger merging a
family into an umbrella trait, which no cut-off can do without cutting at 2.  Review is the right place for them.

**7.6 What the Opus escalation changes.**

- **The check one below the cut-off (decision 12)** makes 483 covers, a third of all overlap covers.  It was
  right 37 times in 40 in the audit.  In my sample: 17 right, 5 right in outcome, 1 false (without purpose), 1
  borderline, of 24.
- **The read at the cut-off** confirms 935 and rescues 63 (6.3%).  The rescues are the weak part:
  - both rescues Roger reviewed were wrong: haughty and underwitted, merged into the very traits Opus rescued
    them from;
  - of 12 rescues drawn with seed 20261012 from the 41 still new, I read 4 as wrong
    (aesthetic / [aesthete](../../../data/traits/instructions/aesthete.json), unluminous / [dull](../../../data/traits/instructions/dull.json),
    bristling / [thin_skinned](../../../data/traits/instructions/thin_skinned.json), pleasing /
    [friendly](../../../data/traits/instructions/friendly.json)), 1 as borderline (arid / [flat](../../../data/traits/instructions/flat.json))
    and 7 as right.

  Their error is the cheap kind.
- **Net:** Opus adds about 420 covers (+40% over Sonnet alone at the same cut-off), and costs 42% of M3's spend.
  Of the two routes, the check one below earns its cost: it removes 483 false new rows at about 1 false cover in
  13 to 40.  The rescue does not change much either way.

**7.7 The false covers have one shape.**  The cover audit's doubtful five were all "a candidate much broader
than, or only one-way implied by, its covering trait": sensing and perspicacious under
[socially_perceptive](../../../data/traits/instructions/socially_perceptive.json), saintly under
[forgiving](../../../data/traits/instructions/forgiving.json), effervescent under
[extraverted_big_five](../../../data/traits/instructions/extraverted_big_five.json), faulty under
[incompetent](../../../data/traits/instructions/incompetent.json).  So are the clear cases found here, with the
deciding reading's own words:

| candidate | covered by | S / O | the reason given |
|---|---|---|---|
| prejudiced#1 | [homophobic](../../../data/traits/instructions/homophobic.json) | 2 / 3 | "Homophobia is a specific form of prejudice ... so it is the same concept narrowed in scope" |
| bigoted#1 | [homophobic](../../../data/traits/instructions/homophobic.json) | 3 / 3 | "Homophobia is bigotry aimed at one particular group" |
| prejudicial#1 | [ageist](../../../data/traits/instructions/ageist.json) | 3 / 3 | "Ageism is prejudgment by group applied to one specific group" |
| self_destructive#1 | [self_harming](../../../data/traits/instructions/self_harming.json) | 2 / 3 | "Self-harming is a specific, narrower form" |
| childlike#1 | [trusting](../../../data/traits/instructions/trusting.json) | 2 / 3 | "trusting is a narrower piece of the same concept" |
| theistic#1 | [muslim](../../../data/traits/instructions/muslim.json) | 2 / 3 | "Being Muslim is a specific form of theism ... much narrower in scope" |
| amorous#1 (states pass; now the trait [amorous](../../../data/traits/instructions/amorous.json)) | [flirty](../../../data/traits/instructions/flirty.json) | 2 / 3 | "Amorous covers a broad disposition ... that explicitly includes flirtation" |

The corpus's [religious](../../../data/traits/instructions/religious.json) may cover theistic; muslim does not.  The
general concept "prejudiced" is hidden three times over: prejudiced, bigoted and prejudicial.

The cause is rubric A's line 3, "the same concept, differing only in scope, degree or emphasis".  It has no
direction, so a corpus trait that is one instance of the candidate scores 3.  The pilot readout noted this as
"a known gap in a scale with no direction".

A crude text screen shows how common it is.  Of the 1,200 covers whose best reading is 3, 126 have a reason
that puts narrowing language next to the covering trait's name.  The screen catches all the cases above, but
also good covers (9 of its 12 audit-marked rows were confirmed covered), so a regular expression is not the
tool; a structured question is (P3).

**7.8 Cost note.**  The opposite rule's partners that the relation call marked unrelated or opposed are 31% of
all readings (6,560 of 21,356; 243 went on to Opus).  None of them reached the cut-off.

## 8. Verdict

**Doing what was intended, but improvable.**

- **The error that hides gaps is at about 3% of overlap covers** (1-5% in Roger's audit).  That is near what a
  one-point-noise 0-4 scale allows: Sonnet repeats its own answer on 91% of pairs.  Its main remaining source
  is one nameable pattern (§ 7.7) that a cheap direction check can target.
- **The cheap error, false new, runs at about a fifth of new rows overall and over 40% at cut-off 4.**  It is
  concentrated in the alignment score 2 band, where cut-off 4 is not supported by the data.
- **The thresholds:**
  - k = 10 is supported (derived, and its misses in the data are 5%);
  - the 0.25 floor neither helps nor hurts (0 of 115 losses; about 4% of readings);
  - cut-off 3 is supported (cover audit);
  - cut-off 4 is supported at alignment score 3 and not at 2.

  The threshold should depend on what it ignores: whether the covering trait is narrower than the candidate.

## 9. Proposals

| # | proposal | cost | expected change | evidence that would settle it |
|---|---|---|---|---|
| P1 | **Graded cut-off.**  Alignment 0-1 keep c = 3 with decision 12.  Alignment 2 takes c = 3 *without* the decision-12 cover: covered when both models read 3 or more, a Sonnet 2 raised by Opus stays new.  Alignment 3 keeps c = 4.  This is the "gradually ... rather than a sudden transition" of Roger's amendment. | $0: `score --redecide` on the records; every pair it needs already has its Opus reading. | About 189 of the 551 alignment-2 rows at c 4 become covered (6% of all new rows).  About 10% of them wrong (3-25%), so about 19 false covers added (6-47) against about 170 false new rows removed. | Roger blind-marks 40 of the 189, as in the cover audit (about 30 minutes).  Adopt if 36 or more are confirmed covered. |
| P2 | **Fix Review 2 D1** (its rec (a): check `renamed_from` before the queue), then re-decide the 8 rows; 5 of them are different senses (§ 7.1).  Decide whether a queued role of the same name should cover a trait candidate, and treat corpus role files the same way. | $0 of code; cents for 8 rows. | 5 false covers undone. | None needed. |
| P3 | **A direction check on 3-level covers.**  When a cover's best reading is exactly 3, ask whether the covering trait is a narrower case of the candidate (one Haiku 5.5 call, or a field in rubric A, which is Roger's text).  If yes, keep the row new with a flag such as `cover_narrower`, so review sees it. | About $0.0005 a cover (1,200 covers here, about $0.60); or a rubric change. | Removes the dominant false-cover shape (§ 7.7): all five of the audit's doubtful covers and one of the sample's two false covers have it.  Some good covers will come back as new (the screen's audit-C hits suggest a few in 100). | Run the question on the cover audit's 100 marked rows (cents): adopt if it flags the 5 doubtful and few of the 95 confirmed.  Then on the 126 screen hits. |
| P4 | **Flag Opus rescues for review.**  Keep the rescued row new, but record `opus_rescued: <stem>` so the review app offers that trait first as the merge target.  Optionally also the c = 4 rows with a 3 / 3 reading (P1 leaves alignment 3's 308 of them). | $0. | Same decisions; faster merges of the about half of rescues that are false new (2 of 2 reviewed, 4 or 5 of 12 read). | Roger's next review log: are flagged rows merged into the flagged trait? |
| P5 | **Cost only: skip opposed traits' partners that the relation call itself marked unrelated or opposed.**  Keep the partners it marked similar or unsure, and the floor exemption for those. | $0 of code. | About 31% fewer Sonnet readings (about $5 of these runs' $34) and about 240 fewer Opus checks; no cover lost on the records (0 of 6,560). | Already on record.  A full scan of 100 candidates (about $5) would confirm, if wanted. |
| P6 | **The floor: no change needed.**  Keep 0.25 or remove it; either way about 10 covers and under $1 over these runs.  With P5 adopted it matters even less. | $0. | Negligible. | None. |

Not proposed: lowering c to 3 everywhere.  On Roger's reviewed rows it would add 11 false covers for 58 right
ones, a precision of 84%.  The alignment-3 band is where the distinctions Roger keeps live (flattering against
[sycophantic](../../../data/traits/instructions/sycophantic.json)), and decision 18 means a false cover there is
never seen again.
