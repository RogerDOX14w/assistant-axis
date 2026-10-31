# Plan: what the judge rubric versions do to the October vectors

Written 2026-10-31 for Roger, from his scoping of the same day and the Runpod session's pod facts and design points.
**Nothing in this plan has been launched.**  It waits on two things: the axis-judging settlement (§ 7, which Roger
wants figured out first), and his confirmation of each run, flag by flag, since the runs together pass the $20 line.

## 1. The question

The October extraction judged its roles and traits under rubric version 13 and will judge its combinations under
version 20, after a month of rubric work (the role rubric experiment, the trait rubric review, the combination rubric
review).  Every one of those versions was tested on scores and on reading sheets, not on the vectors the scores
select.  Roger's question (2026-10-31): rerun pipeline steps 3 to 5 under each rubric version of interest and see
how much, and in what direction, the activation vectors move.  Does a version change look like noise added or
removed, or like a consistent, comprehensible pattern?  If a pattern, is it everywhere or confined to a few
categories of entity (AI roles, assistant-like roles, roles contrary to the model's aligned nature) that a rubric
change was aimed at?  And which version is best, and why?

Two instruments he named.  **Noise** reads off the Spearman correlation ρ between the judge's scores on an axis
description and the activation projections on that axis (the project's "ρ against prompt judging"): noise added
lowers it, noise removed raises it.  **Direction** reads off the sort order a direction imposes on the roles and
traits, named by [infer_axis_description.py](../../../results_analysis/infer_axis_description.py) (Opus describes
the axis from the sorted list), and more cheaply off the cosines of the change direction with the pair axes
(pos-pole vector minus neg-pole vector); the two readings are to be compared on a few directions, and the cheap one
used where many directions need reading.

His scoping: start with the April/May rubric under its gpt-4.1-mini judge (the state before this work, on the new
data) and the final version; zero, one or at most two intermediates on the path to the final version; stop there
if it looks good, dig in only if an issue appears; use a statistical sample rather than every entity, oversampling
the groups a rubric change is likely to affect, since an entity with a high keep share before and after is less
useful to redo.

**Terms used below.**  An entity's *keep* is the share of its 500 responses the judge scores 3 (only those enter its
vector).  A *flip* is a response kept under one version and dropped under another.  A *pair axis* is the vector
difference between the two poles of a clean pair.  A *split half* is a vector computed from half of an entity's kept
responses, so that two halves differ by sampling noise only.  `--min_count` (30 in roger mode) is the fewest kept
responses step 4 makes a vector from.

## 2. What exists

**The October data** (Runpod session, 2026-10-31 13:45 UTC), on four network volumes in EUR-IS-1 ($430 a month
together), the activations staying there until Roger decides:

| pod | entities | state | judged | free space |
|---|---|---|---|---|
| roles | 340 (+ default) | steps 1 to 5 done, pod stopped | version 13, luna Flex, 169,500 calls, **$23.03** | about 27 GB |
| traits | 932 (+ default) | step 3 done; step 2 ends about 16:30 UTC, steps 4 and 5 after | version 13, 466,000 calls, **$64.80** | about 59 GB |
| r_ combinations | 900 (+ default) | `--to-step 2`; stops after step 2 (about 16:00 UTC) | nothing | about 50 GB |
| t_ combinations | 900 (+ default) | `--to-step 2`; stops after step 2 (about 20:00 UTC) | nothing | about 50 GB |

The roles and traits are judged under version 13, whose role and trait rubrics version 20 keeps unchanged
(`may_share_directory(13, 20)` is true for both types), so **the final version's roles and traits are already on
disk**.  The combinations are not judged at all yet; their step 3 under version 20 (two luna calls per response,
about $130 per pod, $260 for the grid) is the extraction's own next step, not this experiment's cost.

**Version directories.**  [run_pipeline.sh](../../../pipeline/run_pipeline.sh) `--judge-prompt-version N` writes
`scores_v<N>/`, `vectors_v<N>/` and `axis_v<N>.pt` beside the default's `scores/`, `vectors/` and `axis.pt`, so
versions sit side by side on the same responses and activations; a scores directory holds one version and refuses
another.  Step 3 takes `--roles NAME ...` to judge a list of entities, which is how a sample is judged in place.
A vectors set is not small: a vector is `[8, 64, 5120]` float32, 10.5 MB, so one version of the whole grid is
3.6 GB for roles, 9.8 GB for traits and 9.5 GB per combination pod.

**Where the steps can run.**  Step 3 is API only and needs the responses (roles 0.7 GB, traits 2 GB, 1.9 GB per
combination pod; a sample's share is proportionally less) and the OpenAI key; it can run here or on any pod.  Step 4
is CPU only and bound by reading 2.6 GB per entity from the volume.  CPU pods in EUR-IS-1 attach the volumes
(checked in the console on 2026-10-31, nothing deployed): 8 vCPU / 32 GB at **$0.32 an hour** is the recommended
size; the volume is attached at deploy time, only after its GPU pod has stopped; the container disk should be about
30 GB because the CPU template's base image needs the torch wheels installed; RunPod quotes 200 to 400 MB/s for the
volumes, unmeasured from a CPU host.  The Runpod session will send a measured step-4 duration from the traits pod.

**The precedent** is the role rubric experiment, whose vector readout
([vector_analysis.md](../role_rubric_experiment/vector_analysis.md), 30 roles, May activations) and tool
([rubric_version_vector_change.py](../../../results_analysis/rubric_version_vector_change.py)) this plan extends.
What it established:

- the judge's own noise is large on scores and small on vectors: the same rubric judged twice (version 3,
  gpt-4.1-mini) changed 14.4% of scores and flipped 11.7% of responses across the keep boundary
  ([score_analysis.md](../role_rubric_experiment/score_analysis.md)), yet the centred cosine between the two
  judgings' vectors was 0.9993 or better on every slot;
- raw cosines between an entity's vectors say nothing (all above 0.9999, from the shared component), so the
  comparison is on **centred** vectors (minus the default, or minus the median over entities), as in the cap pilot's
  rule (centred slot-0 cosine 0.995, norm within 10%, [plan_max_tokens_pilot.md](../plan_max_tokens_pilot.md));
- a wording aimed at a category moves that category: the role-aware identity arm (A7) turned the AI-persona roles'
  offsets by 3 to 5 times the noise and [assistant](../../../data/roles/instructions/assistant.json) by hundreds of
  times, while the cosmetic arms stayed within 1.0 to 1.4 times the noise.

So the measurement works and the scale is known: a version that changes nothing real sits at about 1× the noise
ratio; a version that re-selects a category's responses shows as a multiple of it, on that category.

## 3. The arms

Rubric versions live in [judge_rubrics.py](../../../assistant_axis/judge_rubrics.py).  Versions 1 and 2 are not
runnable (their text is version 3's).  The runnable points on the path, with the judge each takes:

| arm | version | judge | what it is | roles / traits | combinations |
|---|---|---|---|---|---|
| **V0** | 0 | gpt-4.1-mini, `--max_tokens 10` | the April/May state: Christina's number-only role rubric (the May trees' role scores were judged with it), the trait and combination rubrics as first written on 2026-04-06, a reply read as its first integer | must be run | must be run |
| V3 mini | 3 | gpt-4.1-mini | the 2026-10-12 rubric: version 2's text, reason first then one `SCORE:` marker, a reply cut at the cap unparseable; the default until 2026-10-28 and the last version on the May judge | must be run | must be run |
| V3 luna | 3 | gpt-5.6-luna | the same text under the October judge: separates the judge switch from the rubric content | must be run | must be run |
| **V20** | 20 (= 13 for roles and traits) | gpt-5.6-luna | the settled final: the role rubric as a decision procedure read from its A, B, C answers (version 10's), the review's trait rubric (13), the two-sided combination rule 16 + 17 | **on disk** | the extraction's own step 3 |
| noise | 13, again | gpt-5.6-luna | the judge-noise floor: luna takes no temperature, so a repeat flips some decisions by itself | must be run | (the combinations' floor comes from the two sides' agreement with the separate runs, 58/60 and 57/60 in the smoke test, or a repeat of 16 + 17 on the sample) |

**Recommendation, following Roger's scoping.**  Stage 1 is V0 and V20 with the noise arm: the before and after.
Stage 2, run only if stage 1 shows an issue worth locating, adds the two intermediates, V3 mini and V3 luna, which
between them split the change into rubric content (V0 → V3 mini), the judge (V3 mini → V3 luna) and the October
rubric work (V3 luna → V20).  Both intermediates are ready to run on the same sample at any time; nothing about
stage 1 has to be redone for them.  (The scores-only judge comparison of 2026-10-27,
[judge_comparison.json](../judge_comparison/judge_comparison.json), already compared luna, Haiku 5.5 and
gpt-4.1-mini under versions 0 and 3 on 11 roles; this experiment adds what those differences do to vectors.)

## 4. The sample

A seeded, stratified draw, recorded in [entities.json](./entities.json) (not there yet) the way
[cap_pilot_entities.py](../../../tools/cap_pilot_entities.py) records the cap pilot's 64 (a sibling script,
[rubric_version_entities.py](../../../tools/rubric_version_entities.py), not yet written), with these strata:

| kind | n | strata (drawn within each) | oversampled groups |
|---|---|---|---|
| roles | 60 of 340 | keep under version 13 in terciles (low / medium / high), crossed with May keep under version 0 where the stem has a May vector | the AI and machine roles (the role rubric experiment's category D: [assistant](../../../data/roles/instructions/assistant.json), [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json), [robot](../../../data/roles/instructions/robot.json), [cyborg](../../../data/roles/instructions/cyborg.json), [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json), plus any role whose description says it is an AI or a machine); the helpful professionals (category A, e.g. [secretary](../../../data/roles/instructions/secretary.json), [scheduler](../../../data/roles/instructions/scheduler.json), [proofreader](../../../data/roles/instructions/proofreader.json), [debugger](../../../data/roles/instructions/debugger.json)); roles contrary to alignment (category E and the like: [hacker](../../../data/roles/instructions/hacker.json), [virus](../../../data/roles/instructions/virus.json), [destroyer](../../../data/roles/instructions/destroyer.json), [zealot](../../../data/roles/instructions/zealot.json), [predator](../../../data/roles/instructions/predator.json)) |
| traits | 60 of 932 | the same terciles | the trait review's hard traits (an AI mention inside the trait, refusals in trait, dodges: [evil](../../../data/traits/instructions/evil.json), [honest](../../../data/traits/instructions/honest.json), [avoidant](../../../data/traits/instructions/avoidant.json), [whimsical](../../../data/traits/instructions/whimsical.json), [ethnocentric](../../../data/traits/instructions/ethnocentric.json), [unhelpful](../../../data/traits/instructions/unhelpful.json) and the held sample's low-keep traits); the poles of the axes judged in § 6.4 |
| combinations | 100 of 1,800 (50 r_, 50 t_) | May keep under version 0 in terciles where the combination existed in May, else a fourth stratum "new" | the review's 71 re-check combinations (whose reading-sheet marks give ground truth per version), combinations of an AI role, combinations with a harmful or refused trait ([harmful](../../../data/traits/instructions/harmful.json), [lustful](../../../data/traits/instructions/lustful.json), [manipulative](../../../data/traits/instructions/manipulative.json), [sociopathic](../../../data/traits/instructions/sociopathic.json)), the May low-keep list in [candidates_output.txt](../combination_rubric_review/context_arms/candidates_output.txt) § 2 |

The high-keep tercile is drawn thinner (about a third of the low tercile's size): an entity that keeps 90% under
both versions cannot move much.  Entities below `--min_count` under some arm are kept in the sample on purpose;
their drop-out is itself a finding (§ 6.1).  The draw needs the per-entity keep under version 13, which is in the
roles and traits pods' `scores/` directories (170 MB for traits): the Runpod session brings them here with the
other small outputs (step 5 of the four-pod procedure in [pipeline/README.md](../../../pipeline/README.md)).

Sizes are a proposal.  With 60 roles and 60 traits the paired comparisons of § 6 have the resolution the role
rubric experiment had with 30, and the ρ measurement of § 6.4 has a standard error of about 0.09 on a single
version, much less on the paired difference between versions on the same entities.  Roger may want them larger
(the cost scales linearly, § 5) or smaller.

## 5. The runs, flag by flag

All costs at the measured luna Flex rate ($0.136 per 1,000 calls on the roles, $0.139 on the traits, $0.133 on the
combination smoke test) and at gpt-4.1-mini's batch prices ($0.20 / $0.80 per million tokens) on an assumed 900
input tokens per call (rubric plus a response of about 500 tokens at the 1024 cap) and 10 (version 0) or 80
(version 3) output tokens, which gives $0.19 and $0.25 per 1,000 calls.  Estimates, to be checked by a `--dry_run`
before launch; the first run of each judge and version pair is a new combination, so budgets follow the
"first-of-kind" rule (1.5× plus $10).

### 5.1 Step 3 on the sample

Calls per arm: 60 roles × 500 + 60 traits × 500 + 100 combinations × 500 = 110,000, except version 20 on the
combinations, two sides, 100,000 calls for those alone.

| arm | roles + traits | combinations | total |
|---|---|---|---|
| V0 (mini, batch) | 60,000 calls, about $11 | 50,000 calls, about $10 | **about $21** |
| V20 combinations (luna Flex) | on disk | 100,000 calls, about $14 | **about $14** (nil if the extraction's combination step 3 has run by then: the sample's scores are a subset) |
| noise: version 13 again on the sampled roles and traits (luna Flex) | 60,000 calls, about $8 | | **about $8** |
| V3 mini (batch) | 60,000, about $15 | 50,000, about $13 | about $28 |
| V3 luna (Flex) | 60,000, about $8 | 50,000, about $7 | about $15 |

Stage 1 is about **$43** (V0, V20 combinations, noise); stage 2 adds about **$43**.  The full-grid alternative, for
contrast only: V0 on every entity is 1.54 million calls, about $290; the noise rerun on all roles $23; this is why
the sample.

The command per arm and type, run from `pipeline/` (the driver is not used: it judges every entity of a type and
takes no entity list):

```bash
uv run 3_judge.py --entity_type role --responses_dir /workspace/out/roles/responses \
    --output_dir /workspace/out/roles/scores_v0 --prompt_version 0 --judge_model gpt-4.1-mini \
    --roles $(cat entities_roles.txt) --save_replies
```

- `--prompt_version 0` (default: 20; the arm).  `--judge_model gpt-4.1-mini` (default: gpt-5.6-luna; version 0's
  judge; versions 0 to 3 accept any judge, version 20 refuses all but luna).  `--max_tokens` is left at the version's
  own default (10 for version 0, 200 or 300 for the rest).
- Batch versus Flex: gpt-4.1-mini is refused Flex (HTTP 400), so the mini arms run through the Batch API, step 3's
  own default (no `--no_batch`); the luna arms run `--no_batch --service_tier flex`, the driver's roger-mode choice
  since 2026-10-30.  Every arm is under $20 on its own, so real time would also be allowed, but Flex and batch are
  half price and these runs are not urgent.
- `--save_replies`: on, so that a flip can be read (its reason) without a new call; about 1 KB a reply, 110 MB an
  arm.
- `--mark_truncated` stays at its default (on): the October judging marks a response cut at the cap, and the arms
  must see the responses as version 13 saw them.
- The noise arm is version 13 into `scores_v13_rerun/` (a directory name the driver does not use; the step
  refuses a directory already judged under another version, not another directory of the same version).
- Where: here, on the sampled entities' response files rsynced from the pods (about 1.5 MB per entity, 330 MB for
  the sample), with the scores rsynced back into `scores_v<N>/` on each volume for step 4; this avoids the
  combination pods' missing `OPENAI_API_KEY` and any pod hours.  Or on the CPU pod of § 5.2 after the key is added.

### 5.2 Step 4: one pass per volume, every version at once

[4_vectors.py](../../../pipeline/4_vectors.py) computes one version from one scores directory, loading each 2.6 GB
activation file per run.  Five arms would read the sample's activations five times (220 entities × 2.6 GB = 570 GB
per pass).  The Runpod session's proposal, adopted: a **multi-version mode** (`--versions v0=scores_v0,...`,
to be written, with tests) that loads each activation once and accumulates, per version, the kept-response mean,
plus for each version the two split halves (kept responses split by question index parity) at layer 25 only (0.16
MB each; they are a noise scale, not an analysis object), plus the `--all_responses` mean (the cap pilot's
selection-only reference), and writes `vectors_v<N>/<entity>.pt` in the existing format so every downstream reader
works unchanged.  Restricted to the sample with the same `--roles` list.  Output: 220 entities × (5 full vectors
+ halves + all-responses) ≈ 13 GB over the four volumes, within their free space.

Run on one 8 vCPU / 32 GB CPU pod per volume at $0.32 an hour, attached after the GPU pod has stopped; at 300 MB/s
the sample's 570 GB is about 35 minutes per volume, under $1 of pod time per volume, with 8 torch threads
(`OMP_NUM_THREADS=8`, as the driver sets for step 4).  Flags: `--min_count 30` (the driver's roger-mode value, the one the
extraction's vectors use), `--reduce_questions 1`.

### 5.3 Step 5

The assistant axis is the mean over all roles, so a per-version `axis_v<N>.pt` of the real kind needs the full
grid and is not part of stage 1.  On the sample, the mean over the sampled roles per version is computed anyway
(a few lines, no step 5 run) as a comparable aggregate across arms, and the pair axes come from the full-grid
version-13 vectors (§ 6.3), which exist.

## 6. Measurements, cheapest first

### 6.1 Free, from the scores alone

Per entity and arm: keep, flips against the noise arm (up and down across the keep boundary, as in the role rubric
experiment's readout), drops below `--min_count`, by kind and by the oversampled groups.  This is the first look and
costs nothing beyond the step 3 runs.

### 6.2 Vector change against two noise floors (no API)

For each sampled entity and arm, against V20 (the reference, since it is what the extraction uses): the centred
cosine and the norm change of the entity's vector per slot at layer 25 and averaged over layers, as
[rubric_version_vector_change.py](../../../results_analysis/rubric_version_vector_change.py) does it, with the
soft-shear (L = 3) and raw both reported; the ratio of the change to the judge-noise floor (the noise arm) and to
the sampling floor (the split halves).  The role rubric experiment's thresholds carry over: at or near 1× noise the
arm changed nothing real; a multiple of it on a group is a real re-selection.

The soft-shear is fitted on the goal / no-goal subspaces of the May 8slot tree (the script's default), since the
October combination marginals do not exist until the combinations are judged; the raw numbers do not depend on it.

### 6.3 Direction of the change (pair-axis cosines, then names)

The per-entity change vectors (arm minus V20, centred) are stacked and:

- split three ways, per entity, into the part along the entity's own direction (its vector minus the default's),
  the part along the assistant axis (version 13's full-grid `axis.pt`), and the rest, so that "the arm shrinks or
  stretches the entity's own offset" and "the arm moves everything toward or away from the assistant" are told apart
  from an unexplained move;
- run through PCA against a **null of random flips**: for each entity, the same number of responses as the arm
  flipped, chosen at random among its responses, giving the change a random re-selection of that size makes.  A top
  component whose variance stands above the null's is a systematic direction; its loadings say whether it is
  widespread or confined to a category;
- the top components and the category mean changes (AI roles, helpful professionals, contrary-to-alignment roles,
  hard traits, the combination groups) are read by their cosines with the clean-pair axes
  ([pair_list_clean.json](../../../roger/axis_judge_experiments/pair_list_clean.json), 57 pairs, axes from the
  version-13 full-grid vectors) and the di-cohort axes; the highest-cosine pairs name the direction;
- for two or three of those directions, [infer_axis_description.py](../../../results_analysis/infer_axis_description.py)
  names them from the sort order they impose on all roles and traits (Opus 4.6 with a 10,000-token thinking
  budget, about $0.50 a call; a dozen calls at most, about $6), and the two readings are compared.  Roger: the
  cosine reading "should give a similar answer more cheaply, and we can confirm this"; if they agree on the test
  directions, the cosines read the rest.

### 6.4 Noise: ρ against prompt judging, per arm

The only API-expensive measurement, and the one that waits on the axis-judging settlement (§ 7).  Responses-mode
judging in [axis_judge_correlation.py](../../../results_analysis/axis_judge_correlation.py) takes an entity's
**kept** responses (`load_score3_responses`), so a different arm is a different kept set and, as the script stands,
a new judging per arm: the per-batch scores of a B = 7 run cannot be reassigned to another arm's batches.  The
design that avoids the multiplication, if the settlement adopts it: judge **every** response of the sampled roles
and traits once per axis, one response per call, and compute each arm's entity score as the mean over that arm's
kept set.  That makes the judging independent of the rubric version, reusable for any later filter, and, as Roger
noted, lets a set of flips be read directly (the judge's score on exactly the responses that moved).  The catch he
also noted: a B = 7 batch score need not equal the mean of seven single scores (batching may score more
permissively, though the effect should be mostly linear), so the result would not sit on the same scale as the May
B = 7 caches; on October data nothing does, and the batch-size curve of May says smaller B gives higher ρ.

Cost per axis, 120 entities, on the price assumptions of § 5 (the combinations are not judged on pair axes):

| design | gpt-4.1-mini (batch) | gpt-5.6-luna (Flex) | Haiku 5.5 (batch) |
|---|---|---|---|
| one call per response, all 500 responses, once for every arm: 60,000 calls | about $13 | about $7 | about $5 |
| B = 7 on the kept set (about 60%, 36,000 responses, 5,100 batches), **per arm** | about $4 | about $2 | about $1.30 |

Six axes, four arms: per-response once $76 / $43 / $28; B = 7 per arm $103 / $53 / $31.  Per-response wins from
three arms on, and is the only design whose cache survives a later rubric change.  Axes: six of the 21 May
responses-judged axes in [pair_list_responses.json](../../../roger/axis_judge_experiments/pair_list_responses.json),
chosen to touch the oversampled groups, for Roger to pick; a first proposal is
[helpful](../../../data/traits/instructions/helpful.json) / [unhelpful](../../../data/traits/instructions/unhelpful.json),
[harmless](../../../data/traits/instructions/harmless.json) / [harmful](../../../data/traits/instructions/harmful.json),
[honest](../../../data/traits/instructions/honest.json) / [dishonest](../../../data/traits/instructions/dishonest.json),
[guileless](../../../data/traits/instructions/guileless.json) / [scheming](../../../data/traits/instructions/scheming.json),
[concise](../../../data/traits/instructions/concise.json) / [verbose](../../../data/traits/instructions/verbose.json)
and [egalitarian](../../../data/traits/instructions/egalitarian.json) / [elitist](../../../data/traits/instructions/elitist.json),
with their poles in the sample.  Projections are taken in one fixed frame (whitening fitted on the version-13
full-grid vectors), so that only the sampled entities' vectors and kept sets vary between arms; ρ per arm, and the
paired bootstrap over entities on each Δρ against V20.

### 6.5 Reading the result

- **Noise or signal.**  An arm whose vector changes sit at the floors (§ 6.2), whose PCA shows nothing above the
  random-flip null (§ 6.3) and whose Δρ interval covers zero (§ 6.4) changed the data's noise and nothing else; the
  sign of Δρ then says whether it added or removed noise.
- **Systematic.**  A component above the null, read by its pair-axis cosines and confirmed by the named direction;
  its loadings say which entities, and the category tables say whether that is the group the rubric change was
  for.  The expectation from the reviews: the AI and machine roles move along the identity-related directions (the
  role rubric's A, B, C procedure stopped dropping an AI role's in-character AI mentions); the hard traits move
  where version 13 stopped dropping refusals and AI mentions inside the trait; the low-keep combinations of the
  review move most.  An unexpected mover is the finding to dig into.
- **Which version is best.**  The reading sheets already give each version's precision and recall against
  Roger-standard ground truth (combinations: version 20's 0.87 / 0.71 against draft 14's 0.76 / 0.88,
  [estimate_output.txt](../combination_rubric_review/reader_check_2/estimate_output.txt); roles and traits in
  their reviews).  This experiment adds the vector-level test: the better version is the one whose systematic
  changes land on the entities whose old keeps the sheets marked wrong, and whose ρ does not fall.  A version that
  wins on the sheets and loses ρ would be the issue that sends us to stage 2.

## 7. The prerequisite: settling the axis judging first (Roger, 2026-10-31)

Decisions the settlement has to make, since § 6.4 depends on them:

1. **The judge.**  gpt-4.1-mini is deprecated (shutdown 2027-01-14); Haiku 5.5 and gpt-5.6-luna are each a
   quarter to half its price per call (table above) and neither takes a temperature.  A pilot on one or two May
   axes with existing B = 7 mini caches, ρ per judge against the same projections, is the test; judge caches are
   keyed by family, so a new judge is a new cohort either way.
2. **B.**  B = 1 per response or the canonical 7; B = 1 needs the per-response cache and re-aggregation in
   `axis_judge_correlation.py` (today the cache is per batch, with `_update_response_aggregates` to a mean per
   entity), a code change with tests.  The May batch-size curve says ρ rises as B falls; the pilot measures B = 1
   against B = 7 on the same axis and judge.
3. **The question subsample.**  Full volume (the GPT default) or tiered thirds (the Anthropic default); for the
   experiment, full volume, so that every kept set is covered whatever the arm.

With those settled, § 6.4's cost is fixed and the runs of § 5 can be quoted for confirmation.

## 8. Code to write before anything runs

| item | where | what |
|---|---|---|
| multi-version step 4 | [4_vectors.py](../../../pipeline/4_vectors.py) | `--versions NAME=SCORES_DIR ...`, one activation load per entity; per version the kept mean, two split halves at layer 25, the all-responses mean; `--roles` restriction; tests in [test_4_vectors.py](../../../pipeline/tests/test_4_vectors.py) |
| the sampler | [rubric_version_entities.py](../../../tools/rubric_version_entities.py) (not yet written) | the stratified draw of § 4 from the version-13 scores and the May keeps, seeded, writing [entities.json](./entities.json) and the per-type `--roles` lists |
| the analysis | [rubric_version_vectors.py](../../../results_analysis/rubric_version_vectors.py) (not yet written; extends [rubric_version_vector_change.py](../../../results_analysis/rubric_version_vector_change.py)) | § 6.1 to 6.3: tables, the decomposition, PCA with the random-flip null, pair-axis cosines, the plots, provenance envelopes |
| per-response axis judging | [axis_judge_correlation.py](../../../results_analysis/axis_judge_correlation.py) | if the settlement adopts it: a per-response cache and re-aggregation over a given kept set (§ 7) |
| the step-3 wrapper | [run_step3_arms.sh](./run_step3_arms.sh) (not yet written) | the five step 3 invocations of § 5.1 with their `--roles` lists and output directories, so that the launch is one reviewed command per arm |

## 9. Sequence

1. The axis-judging settlement (§ 7), its own plan and pilot.
2. The code of § 8, with tests; the Runpod session brings the roles and traits `scores/` directories here; the
   sample is drawn and [entities.json](./entities.json) committed.
3. **Stage 1, confirmed flag by flag**: V0 and the noise arm on the sample (about $29); V20 on the sampled
   combinations unless the extraction's combination step 3 has run by then (about $14).
4. The multi-version step 4 on the four volumes (CPU pods, under $5 of pod time), the vectors rsynced here.
5. § 6.1 to 6.3 readout, no API beyond the dozen Opus calls.
6. § 6.4 on the settled judge (about $30 to $80 for six axes), then the reading of § 6.5.
7. Stage 2 (the intermediates, about $43 plus their step 4 and ρ) only if stage 1 leaves an issue to locate.

## 10. For Roger to decide

- The sample sizes of § 4 (60 / 60 / 100) and the oversampled groups.
- The axes of § 6.4 (six proposed) and whether their poles join the sample.
- The noise arm on the sample only (about $8) or on all 340 roles ($23), which would also give grid-wide flip rates.
- Step 3 here (responses rsynced) or on the CPU pods.
- Whether stage 2's two intermediates run with stage 1 in one round (about $43 more now, no second round trip) or
  wait for stage 1's reading, as his scoping says.
