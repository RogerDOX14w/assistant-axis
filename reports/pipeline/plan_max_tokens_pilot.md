# Plan: the response-length cap pilot (256 / 512 / 768 / 1024)

Written 2026-10-12 for Roger's review, from the pipeline review of the same day (P6 in the walk-through);
revised 2026-10-28 with his decisions of that day worked into the text (the record of them is § 8).
Nothing here runs until Roger confirms the GPU-hours and the judge spend (both quoted in § 6).

## 1. Question

Step 1 of the extraction pipeline ([`1_generate.py`](../../pipeline/1_generate.py)) generates each entity's responses with `--max_tokens 512`, and about 71% of the recorded responses in the 8slot tree hit that cap (measured by the 2026-10-12 review from the response texts; the files do not record it).  Under the regenerated October instructions fewer do: 45% of the 15,000 responses of the role rubric experiment's 30 roles (2026-10-22, `finish_reason == "length"`).  The cap was chosen to save pod time and judging cost, on the view that a response shows its persona within 512 tokens.  Two things read the responses: the judge (step 3, [`3_judge.py`](../../pipeline/3_judge.py)), which scores each response 0–3, and step 2 ([`2_activations.py`](../../pipeline/2_activations.py)), whose slot 0 is the mean activation over the response's tokens.  Both see fewer tokens than the model would have produced.

The pilot asks: **does raising the cap change what the judge decides or where the entity vector points, by enough to pay for it?**  It runs before the October extraction (3,072 entities), so that the cap used there is a measured choice.

## 2. Design

Paired within entity: every pilot entity is generated at all four caps, so each comparison is of the same entity with itself and the between-entity variance drops out.

**Entities (64):**

- 20 roles, drawn from [`data/roles/instructions/`](../../data/roles/instructions/) by a fixed-seed sample, with 8 of the 20 forced to narrative roles whose responses run long (the builder picks them from the recorded response lengths in the 8slot tree, longest median first).
- 20 traits, a fixed-seed sample from [`data/traits/instructions/`](../../data/traits/instructions/), plus `verbose` and `concise` forced in (Roger, 2026-10-12: "verbose and concise are known outliers here").  They are the stress test and the control: `verbose` is the entity most likely to be truncated at every cap, `concise` the one that should be indifferent to it.  Both are reported on their own, outside the stratum means.
- 20 combinations, a fixed-seed sample of the W15 grid (goal role × non-goal trait and the reverse), plus `r_angel__verbose` and `r_angel__concise` (Roger, 2026-10-12: `angel`, a role one can imagine either verbose or concise, with no tendency of its own; by score-3 rate in the May tree it is the top goal role, 491.7 of 500 per combination, and its responses run near the grid's median length), reported on their own likewise.  `verbose` is 52nd of 54 in W15's non-goal trait list, so it is not in the October grid (the top 30); the pilot's step 1 is run with `--non_goal_count 54` so the work items include it, and the `--roles` filter then selects the pilot entities only.

The list is generated once by the builder, [`cap_pilot_entities.py`](../../tools/cap_pilot_entities.py), into [`cap_pilot_entities.json`](./cap_pilot_entities.json) with the seed recorded (seed 20261012, built 2026-10-12; checked against the current goal file on 2026-10-28, same hash `45b79d73…`), so the pilot is reproducible.  The 8 longest-responding roles turned out to be expository ones (sociologist, anthropologist, geographer, reviewer, scholar, historian, biologist, auditor; median 2,560-2,620 characters against a role median of 2,287).

**Caps:** 256, 512, 768, 1024.  512 is today's value; 1024 is the reference the others are compared to; 256 is there to show the slope, not as a candidate.

**Responses:** the pipeline's own 5 instruction variants × 100 questions = 500 per entity per cap; temperature and top-p at the pipeline defaults (0.7 / 0.9).  Per-request seeds are not available (the responses are not reproducible call-for-call), which is why the comparison is of means over 500, not of individual responses.

**The noise floor: 512 generated and judged a second time** (Roger, 2026-10-28: "the noise floor measurement sounds worth $15").  Every comparison in the pilot is between two different samples of 500 responses, each filtered by the judge, so "512 against 1024" holds the cap's effect, generation noise (fresh responses to the same questions at temperature 0.7) and judge noise.  A second 512 tree, generated and judged exactly like the first, gives the pilot its own floor, "512 against 512′", for every measure of § 5, per stratum and per entity.  It is the pilot's counterpart of the role rubric experiment's A0′ (version 3 judged twice), the reference that made that experiment's numbers readable; without it a slot-0 cosine of 0.994 cannot be told from noise (judge noise alone puts the stratum-mean cosine near 0.997, § 5).  It also supplies the per-entity σ of § 5 and the run-sanity check.

**Judge noise alone: the 512 tree judged a second time.**  The same responses scored again (64 × 500 calls, ≈ $6) separate the judge's part of the floor from generation's.  It is also what tells, for an entity flagged by the per-entity rule, whether the judge or the sample moved.

## 3. Prerequisites

1. The additive response fields from the review (P6): `finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`, written by [`generation.py`](../../assistant_axis/generation.py).  The truncation share is read from `finish_reason`; without it the pilot would again be counting tokens after the fact.  **Done** (2026-10-12, 2026-10-13).
2. The step-1 exit-status fix (P8.1), so a pod run that loses its engine mid-way is not reported as success.  **Done.**
3. A pod with the model and a fresh output root; nothing from the May tree is reused.
4. **Built 2026-10-28** (e82d4f59 to 2ee7274d, with tests on the fakes, off the pod):
   - [`2_activations.py`](../../pipeline/2_activations.py) `--prefix_token_means 256,512,768`: beside each activation file, the slot-0 mean over the first N content tokens of every response, for § 5's content-only measure, from the same forward pass.  `--prefix_token_layers 25` keeps layer 25 only, about 15 MB per entity, 1 GB for the tree; at all 64 layers it would be about 1 GB per entity.  Needed before the 1024 tree's step 2.
   - [`4_vectors.py`](../../pipeline/4_vectors.py) `--all_responses`: the mean over every response, no score file, for § 5's selection-only measure.  Needed before step 4.
   - [`cap_pilot_compare.py`](../../tools/cap_pilot_compare.py): the norm measure and rule, `--repeat 512=<tree>` as the noise floor and the source of σ, `--extra_scores CAP=DIR` (more judgings of a cap, averaged per entity), `--vectors_all CAP=DIR` and `--prefix_means 1024=DIR` for the decomposition, the per-entity flags.  Needed before the readout.
   - [`runpod_api.py`](../../tools/runpod_api.py): stock of 2- and 4-GPU pods per data center in `stock`, `record` and `history`, to know when the pod can go from 1× to 2×.

## 4. Runs

One output root per tree on the pod's **network volume** (outputs go on the volume, not the container disk, Roger's ruling since the first October pods), under one pilot root: `/workspace/cap_pilot/cap{256,512,512b,768,1024}/`, `cap512b` the repeat.  **Where:** US-KS-2 on `Roger_AA_1`, enlarged from 200 GB to 1,200 GB for the activations (Roger, 2026-10-28: stay in one data center rather than create and later delete a volume elsewhere; 175 GB was already there, the rubric experiment's October activations and the model cache), on 1× A100 SXM for the smoke test (three entities at 256, a role, a trait and a combination, with `--verify_spans 20` on step 2) and 2× once it has passed.  Done 2026-10-28: the smoke test on `roger-aa-6` (1×), passed; the pilot on `roger-aa-7` (2× A100 SXM, NVLink, 503 GB RAM), one worker per GPU (`--tensor_parallel_size 1`; called directly, the steps otherwise put every GPU in one worker).  The runner is [cap_pilot_run.sh](./cap_pilot/cap_pilot_run.sh) and the queue [cap_pilot_queue.sh](./cap_pilot/cap_pilot_queue.sh), with the commands below and the driver's environment (the model mirrored into `/dev/shm`, step 2's staging there, the compile caches off it).  The driver is not used (it runs step 3 in parallel with step 2 and has no `--roles`); the steps are run by hand, from `pipeline/`, for each tree:

```
E=../reports/pipeline/cap_pilot_entities.json
OUT=/workspace/cap_pilot/cap<CAP>          # cap512b: --max_tokens 512, a second tree
uv run 1_generate.py --model Qwen/Qwen3-32B --mode roger --roles_only \
    --roles $(jq -r '.by_type.role[]' $E) --max_tokens <CAP> --output_dir $OUT/responses
uv run 1_generate.py --model Qwen/Qwen3-32B --mode roger --non_goal_count 54 \
    --roles $(jq -r '.by_type.trait[], .by_type.combination[]' $E) \
    --max_tokens <CAP> --output_dir $OUT/responses
uv run 2_activations.py --model Qwen/Qwen3-32B --responses_dir $OUT/responses \
    --output_dir $OUT/activations --max_length 2048 \
    $([ <CAP> = 1024 ] && echo --prefix_token_means 256,512,768 --prefix_token_layers 25)
uv run 3_judge.py --entity_type role --roles $(jq -r '.by_type.role[]' $E) \
    --judge_model gpt-5.6-luna --save_replies --no_batch --service_tier flex \
    --responses_dir $OUT/responses --output_dir $OUT/scores
for T in trait combination; do
  uv run 3_judge.py --entity_type $T --roles $(jq -r ".by_type.$T[]" $E) \
      --no_batch --service_tier flex \
      --responses_dir $OUT/responses --output_dir $OUT/scores
done
uv run 4_vectors.py --activations_dir $OUT/activations --scores_dir $OUT/scores \
    --output_dir $OUT/vectors --min_count 30
uv run 4_vectors.py --activations_dir $OUT/activations --all_responses \
    --output_dir $OUT/vectors_all
```

Then the judge-noise run, the 512 tree's responses scored again into `cap512/scores_rejudge/` (the same three step-3 commands with `--output_dir $OUT/scores_rejudge`), and, for any entity the per-entity rule flags (§ 5), two more judgings of its cap tree and of the 1024 tree, into `scores_rejudge2/` and `scores_rejudge3/` (`--roles <entity>`).

- **Judges** (2026-10-28): step 3's default prompt version is 10, settled for roles on that day: roles are judged by gpt-5.6-luna (`--judge_model gpt-5.6-luna`; a roles run without it is refused) and a reply is scored from its A/B/C answers; the trait and combination rubrics are version 3's text, hash-identical, judged by the default gpt-4.1-mini while the trait rubric is still being worked on.  One `scores/` directory holds all three types (the version check is per type).  Every judging goes by OpenAI Flex processing with retries, `--no_batch --service_tier flex` (Roger, 2026-10-28: "flex with retries worked better than batch"; priced at batch rates; a batch of luna's sat unprocessed for hours on 2026-10-26).
- **Steps** (corrected 2026-10-12 when the list was built): standalone roles are generated only with `--roles_only`, so step 1 runs twice; step 3 runs once per entity type with that type's names; `--min_count 30` is the driver's roger-mode value; `--roles` filters the work items by output name in every mode; `--max_length 2048` holds a 1024-token response plus its prompt; the list holds no name that is both a role and a trait, so one responses directory per tree holds all three types.  Step 1 for every tree can run before any step 2, so that the GPU is busy while item 4 of § 3 is built; the 1024 tree's step 2 waits for `--prefix_token_means`.
- **Data**: activations 64 × 5 × 2.6 GB ≈ 830 GB stay on the volume until the readout is accepted; then they are archived or deleted (2026-10-28: where the extraction's activations are kept is decided later, and the pilot's may follow the same route), and the volume goes on to the roles run of the extraction.  Responses, scores, vectors, `vectors_all` and the prefix means (small at one layer: three slot-0 rows per response, about 1 GB for the tree) come back to the repo under [`roger/cap_pilot/`](../../roger/cap_pilot/) (not there yet; `roger/` is git-ignored).

## 5. Measurements and the decision rule

[`tools/cap_pilot_compare.py`](../../tools/cap_pilot_compare.py) (built 2026-10-12, extended per § 3 item 4; `uv run python tools/cap_pilot_compare.py --root roger/cap_pilot --repeat 512=roger/cap_pilot/cap512b ...`) reads the trees and writes [`cap_pilot_readout.md`](./cap_pilot_readout.md) (not there yet) with, per entity and per stratum:

1. **Truncation share** at each cap, from `finish_reason == "length"`.
2. **Judge:** the score-3 share and the mean score at each cap, with the paired difference to the 1024 run.
3. **Vector, direction:** the cosine between the entity's vector at each cap and its 1024 vector, per slot, **at layer 25** (`--layer`; Roger, 2026-10-28), **centred on the pilot mean**: raw cosines between two versions of an entity's mean activation are all near 1 (about 0.99999 on data shaped like the real vectors) because every vector carries the model's large common direction, so each cap's vectors have their mean over the deciding strata at that cap subtracted first (the outliers left out of the mean, so they cannot move the others), and the raw cosines are reported beside them.  Not centred on the default vector (Roger, 2026-10-28: "I have reason to believe default is atypical in at least one respect").
4. **Vector, length:** the relative change in the centred slot-0 norm, cap against 1024 (Roger, 2026-10-28: a threshold on the norm "on a comparable scale" to the cosine's).
5. **Slot 0 decomposed** (Roger, 2026-10-28: the judge delta is measured; what of averaging over a longer response?).  Slot 0, the mean over the response's tokens, is the only slot that sees the extra text; the header positions (slots 1–7) come before the response in a causal model, so each response's header activations are the same at every cap — but the entity vector averages the score-3 responses, and the judge selects a different subset at each cap, so slots 1–7 move by **selection alone** while slot 0 moves by **content + selection + generation noise**.  Three further measures, each with cosine and norm:
   - *Content alone*, from the 1024 tree's prefix means: the cap does not change sampling before it, so a 1024 response's first 512 tokens are exactly a 512-cap response; the entity's mean over its 1024-selected responses of the first-256 / 512 / 768-token means, against the full means of the same responses, is the content effect paired per response, with no generation or judge noise in it.
   - *Selection alone, slot 0*: the `vectors_all` mean over all 500 responses at each cap against the judge-selected vector at that cap.
   - *Selection alone, slots 1–7*: as before, beside the judge's score-3 share (the same effect from the judge's side).
6. **The noise floor** (§ 2): every measure above for 512 against 512′ (`--repeat 512=`), per stratum and per entity, printed beside the cap comparisons; and the run-sanity check, slots 1–7 of 512 against 512′ ≥ 0.999 (a miss is a broken run, not a cap effect).  The judge-only floor from `scores_rejudge/` beside it.
7. **Pair axes:** for the pairs among the pilot entities (`verbose`/`concise` first), the cosine of the pair-difference axis across caps at layer 25.
8. `verbose`, `concise` and their combinations reported separately.

**Decision rule, fixed before the run:** keep 512 if, over the stratum means (roles, traits, combinations; each stratum must pass), the centred slot-0 cosine between 512 and 1024 is **≥ 0.995** (Roger, 2026-10-28; about cos 0.1 rad, raised from 0.99), the relative change in the centred slot-0 norm is **within ±10%** (the displacement a 0.1-radian turn makes, so the two vector rules are of comparable strictness), and the score-3 share moves by **less than 2 points** (the stratum mean of the per-entity paired differences, cap minus 1024, in absolute value under 0.02); otherwise take the smallest cap that meets all three (768, else 1024).  Whatever the outliers do is reported but does not decide: if `verbose` alone fails the rule, that is a note on `verbose`, not a reason to raise the cap for 3,072 entities.

**Why the share rule is on the stratum mean** (Roger, 2026-10-28): per entity, 2 points sits near the judge's own rejudge noise (per-role SD 1.6 points on the October roles under version 3), so a per-entity test at 2 points would be hit by chance; the stratum mean of 20 has a standard error of about 0.4 points from judge noise and about 0.7 with generation noise, and the pilot looks for a shared effect, keeping more or less on the whole set.

**Per-entity rule, 4σ** (Roger, 2026-10-28): σ is the standard deviation, per entity type, of an entity's change in score-3 share between two generations and judgings of the same cap, measured from 512 against 512′ (the total noise; the rejudge gives the judge's part).  An entity whose paired change, cap against 1024, exceeds 4σ is not decided on at once: its cap tree and the 1024 tree are judged twice more and the change averaged over the three judgings.  If the average is still past 4σ the entity is reported as a systematic change and looked at (a rejudge cannot undo a generation fluke, which is why σ is the total; the rejudge says whether it was the judge).  With σ ≈ 3 points, 4σ ≈ 12 points, which chance will not reach among 64 entities.

**How strict, against the one noise source already measured** (judge noise, the same responses judged twice, October roles under gpt-4.1-mini version 3; stratum means of 20): the share rule's 2 points is about 5 standard errors above that floor; the cosine rule's 0.995 (1 − cos = 5.0e-3) is about 2 above it in slot 0, where judge noise alone gives 1 − cos ≈ 2.9e-3 ± 1.0e-3, and far above it in slots 1–7 (3e-4 to 5e-4).  Generation noise, unmeasured for slot 0 until the repeat tree exists, lowers the floor further.  So the cosine rule is the stricter of the three and the one the floor of item 6 is needed to read: if 512 against 512′ itself falls under 0.995, the rule is unmeetable at any cap and the readout says so rather than raising the cap.

## 6. Cost — to be confirmed by Roger before launch

- **Pod time** (re-estimated 2026-10-28 from the October pods; the April-pace figure was 16 GPU-hours): on `roger-aa-2` (1× A100 SXM, 2026-10-22) step 1 took 280 s per entity at 512 and step 2 175 s.  Both scale with the cap, so 64 × (0.5 + 1 + 1.5 + 2) × (280 + 175) s ≈ 40 GPU-hours for the four caps and ≈ 8 more for the repeat, ≈ **48 GPU-hours**, over the 13 GPU-hour line in CLAUDE.md: about $86 on A100 SXM at $1.79/h; about 24 h of wall time on 2 GPUs (one worker per GPU, tensor-parallel 1, the driver's default), 48 h on one.  Parameters that differ from the defaults: `--max_tokens` 256/768/1024 (default 512), the entity filter `--roles` (default: all), `--prefix_token_means` on the 1024 tree.  Everything else at the pipeline defaults.
- **Judge:** 64 × 5 × 500 = 160,000 calls for the five trees plus 32,000 for the rejudge, the role calls at gpt-5.6-luna's rates ($0.20 / $1.20 per million tokens, half of gpt-4.1-mini's input rate, with longer A/B/C replies) and the rest at gpt-4.1-mini's, all at Flex (batch) prices, ≈ **$38**; per-entity rejudges about $0.40 each.
- Disk: ≈ 830 GB of activations on the volume (1 TB, about $70 a month while it exists); about 2 GB returned.

## 7. What comes out

The readout, the entity list and the five small trees under `roger/cap_pilot/`; one line in the October plan naming the cap and citing the readout; and `finish_reason` on every October response, so the question stays answerable later.  Beside the cap decision, the pilot leaves three numbers the extraction's analyses need anyway: the generation-plus-judge noise floor of an entity vector at 500 responses, its judge-only part, and the share of slot 0's movement that is content rather than selection.

## 8. Decision record

2026-10-12 (Roger): 64 entities; `angel` as the goal role for the `verbose` / `concise` combinations, both forms run (the solo traits the test, the combinations whether the worst case survives being combined, which is what 60% of the October grid is; `angel` is also the role with the most score-3 responses); the cosine threshold on slot 0 only.

2026-10-28 (Roger): centred cosines on the pilot mean, not the default vector; layer 25; the share rule on the stratum mean; the cosine threshold 0.995 and a norm rule at ±10% on the same scale; a per-entity 4σ rule with two further judgings before an entity counts as changed; slot 0's change decomposed into content, selection and noise; the 512 repeat tree as the noise floor ("worth $15"); step 3 by Flex with retries, not batch; one data center, `Roger_AA_1` enlarged, 1× A100 for the smoke test then 2×.
