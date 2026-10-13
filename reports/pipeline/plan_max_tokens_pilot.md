# Plan: the response-length cap pilot (256 / 512 / 768 / 1024)

Written 2026-10-12 for Roger's review, from the pipeline review of the same day (P6 in the walk-through).
Nothing here runs until Roger confirms the GPU-hours and the judge spend (both quoted in § 6).

## 1. Question

Step 1 of the extraction pipeline ([`1_generate.py`](../../pipeline/1_generate.py)) generates each entity's responses with `--max_tokens 512`, and about 71% of the recorded responses in the 8slot tree hit that cap (measured by the 2026-10-12 review from the response texts; the files do not record it).  The cap was chosen to save pod time and judging cost, on the view that a response shows its persona within 512 tokens.  Two things read the responses: the judge (step 3, [`3_judge.py`](../../pipeline/3_judge.py)), which scores each response 0–3, and step 2 ([`2_activations.py`](../../pipeline/2_activations.py)), whose slot 0 is the mean activation over the response's tokens.  Both see fewer tokens than the model would have produced.

The pilot asks: **does raising the cap change what the judge decides or where the entity vector points, by enough to pay for it?**  It runs before the October extraction (3,072 entities), so that the cap used there is a measured choice.

## 2. Design

Paired within entity: every pilot entity is generated at all four caps, so each comparison is of the same entity with itself and the between-entity variance drops out.

**Entities (64):**

- 20 roles, drawn from [`data/roles/instructions/`](../../data/roles/instructions/) by a fixed-seed sample, with 8 of the 20 forced to narrative roles whose responses run long (the builder picks them from the recorded response lengths in the 8slot tree, longest median first).
- 20 traits, a fixed-seed sample from [`data/traits/instructions/`](../../data/traits/instructions/), plus **`verbose`** and **`concise`** forced in (Roger, 2026-10-12: "verbose and concise are known outliers here").  They are the stress test and the control: `verbose` is the entity most likely to be truncated at every cap, `concise` the one that should be indifferent to it.  Both are reported on their own, outside the stratum means.
- 20 combinations, a fixed-seed sample of the W15 grid (goal role × non-goal trait and the reverse), plus `r_angel__verbose` and `r_angel__concise` (Roger, 2026-10-12: `angel`, a role one can imagine either verbose or concise, with no tendency of its own; by score-3 rate in the May tree it is the top goal role, 491.7 of 500 per combination, and its responses run near the grid's median length), reported on their own likewise.  `verbose` is 52nd of 54 in W15's non-goal trait list, so it is not in the October grid (the top 30); the pilot's step 1 is run with `--non_goal_count 54` so the work items include it, and the `--roles` filter then selects the pilot entities only.

The list is generated once by the builder, [`cap_pilot_entities.py`](../../tools/cap_pilot_entities.py), into [`cap_pilot_entities.json`](./cap_pilot_entities.json) with the seed recorded (seed 20261012, built 2026-10-12), so the pilot is reproducible.  The 8 longest-responding roles turned out to be expository ones (sociologist, anthropologist, geographer, reviewer, scholar, historian, biologist, auditor; median 2,560-2,620 characters against a role median of 2,287).

**Caps:** 256, 512, 768, 1024.  512 is today's value; 1024 is the reference the others are compared to; 256 is there to show the slope, not as a candidate.

**Responses:** the pipeline's own 5 instruction variants × 100 questions = 500 per entity per cap; temperature and top-p at the pipeline defaults (0.7 / 0.9).  Per-request seeds are not available (the responses are not reproducible call-for-call), which is why the comparison is of means over 500, not of individual responses.

## 3. Prerequisites

1. The additive response fields from the review (P6): `finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`, written by [`generation.py`](../../assistant_axis/generation.py).  The truncation share is read from `finish_reason`; without it the pilot would again be counting tokens after the fact.
2. The step-1 exit-status fix (P8.1), so a pod run that loses its engine mid-way is not reported as success.
3. A pod with the model and a fresh output root; nothing from the May tree is reused.

## 4. Runs

One output root per cap, all on the pod's local disk (not `/workspace`), under one pilot root, e.g. `/local/cap_pilot/cap{256,512,768,1024}/`.  For each cap, from `pipeline/`:

```
E=../reports/pipeline/cap_pilot_entities.json
OUT=/local/cap_pilot/cap<CAP>
uv run 1_generate.py --model Qwen/Qwen3-32B --mode roger --roles_only \
    --roles $(jq -r '.by_type.role[]' $E) --max_tokens <CAP> --output_dir $OUT/responses
uv run 1_generate.py --model Qwen/Qwen3-32B --mode roger --non_goal_count 54 \
    --roles $(jq -r '.by_type.trait[], .by_type.combination[]' $E) \
    --max_tokens <CAP> --output_dir $OUT/responses
uv run 2_activations.py --model Qwen/Qwen3-32B --responses_dir $OUT/responses \
    --output_dir $OUT/activations --max_length 2048
for T in role trait combination; do
  uv run 3_judge.py --entity_type $T --roles $(jq -r ".by_type.$T[]" $E) \
      --responses_dir $OUT/responses --output_dir $OUT/scores
done
uv run 4_vectors.py --activations_dir $OUT/activations --scores_dir $OUT/scores \
    --output_dir $OUT/vectors --min_count 30
```

(Corrected 2026-10-12 by the pipeline fix batch, when the list was built: standalone roles are generated only with `--roles_only`, so step 1 runs twice; step 3 runs once per entity type with that type's names; `--min_count 30` is the driver's roger-mode value.  `--roles` filters the work items by output name in every mode since 2026-10-12; `--max_length 2048` holds a 1024-token response plus its prompt.  The list holds no name that is both a role and a trait, so one responses directory per cap can hold all three types.)  Step 3 goes by batch, the default.  Activations (64 × 4 × 2.6 GB ≈ 670 GB) stay on the pod's volume, which is discarded at the end (Roger, 2026-10-13: deleting them saves nothing on RunPod); responses, scores and vectors (small) come back to the repo under [`roger/cap_pilot/`](../../roger/cap_pilot/) (not there yet; `roger/` is git-ignored).

## 5. Measurements and the decision rule

A small tool, [`tools/cap_pilot_compare.py`](../../tools/cap_pilot_compare.py) (built 2026-10-12; `uv run python tools/cap_pilot_compare.py --root roger/cap_pilot`), reads the four trees and writes [`cap_pilot_readout.md`](./cap_pilot_readout.md) (not there yet) with, per entity and per stratum:

1. **Truncation share** at each cap, from `finish_reason == "length"`.
2. **Judge:** the score-3 share and the mean score at each cap, with the paired difference to the 1024 run.
3. **Vector:** the cosine between the entity's vector at each cap and its 1024 vector, per slot.  Slot 0, the mean over the response's tokens, is the only slot that sees the extra text; the header positions (slots 1–7) come before the response in a causal model, so each response's header activations are the same at every cap — but the entity vector averages the score-3 responses, and the judge selects a different subset at each cap, so slots 1–7 move by **selection alone** while slot 0 moves by **content + selection**.  Slots 1–7 are therefore reported as the selection-only effect (beside the judge's score-3 share, the same effect from the judge's side), and a run-sanity check compares slots 1–7 at the *same* cap across two runs (≥ 0.999 expected; a miss is a broken run, not a cap effect).
4. **Pair axes:** for the pairs among the pilot entities (`verbose`/`concise` first), the cosine of the pair-difference axis across caps at layer 25.
5. `verbose`, `concise` and their combinations reported separately.

**Decision rule, fixed now:** keep 512 if, over the stratum means, the slot-0 cosine between 512 and 1024 is ≥ 0.99 and the score-3 share moves by less than 2 points; otherwise take the smallest cap that meets both.  Whatever the outliers do is reported but does not decide: if `verbose` alone fails the rule, that is a note on `verbose`, not a reason to raise the cap for 3,072 entities.

**Two readings the tool had to fix, for Roger to confirm before the pilot runs** (pipeline fix batch, 2026-10-12; [fix_batch_2026-10-12.md](./fix_batch_2026-10-12.md), item 5):

- *Centred cosines.*  Raw cosines between two versions of an entity's mean activation are all near 1 (about 0.99999 on fake data shaped like the real vectors), because every vector carries the model's large common direction; the rule would then pass at any cap.  The tool applies the rule to cosines of the vectors minus their mean over the deciding strata at the same cap (the outliers left out of the mean, so they cannot move the others), and reports the raw cosines beside them.
- *One layer.*  The cosine is taken at layer 25 (`--layer`), the layer § 5 item 4 names for the pair axes; the plan does not name a layer for item 3.
- *"Moves by less than 2 points"* is read as the stratum mean of the per-entity paired difference (cap minus 1024) in score-3 share, in absolute value under 0.02; each deciding stratum (roles, traits, combinations) must meet both conditions; the candidates are 512, 768 and 1024.

Power: 64 paired entities put a standard error of about 0.002 on a mean cosine difference (per-entity spread ~0.01–0.02) and about 0.5 points on the score-3 share (each share is from 500 responses), so the rule's thresholds are resolved several times over.

## 6. Cost — to be confirmed by Roger before launch

- **Pod time:** step 1 at the April pace is ~2 min per entity at 512 and scales with the cap, so 64 × (0.5 + 1 + 1.5 + 2) × 2 min ≈ **10.7 GPU-hours**; step 2 scales the same way at roughly half, ≈ **5 GPU-hours**; total ≈ **16 GPU-hours**, over the 13 GPU-hour line in CLAUDE.md.  Parameters that differ from the defaults: `--max_tokens` 256/768/1024 (default 512), the entity filter `--roles` (default: all).  Everything else at the pipeline defaults.
- **Judge:** 64 × 4 × 500 = 128,000 calls at gpt-4.1-mini batch rates, ≈ **$25**, under the $20-per-invocation line per cap run (four runs of ≈ $6).  Real time would be ≈ $50; batch, as the default.
- Disk on the pod: ≈ 670 GB of activations transiently; ≈ 1 GB returned.

Halving the entity count to 32 keeps the paired design (standard errors ×1.4) at half the pod time, if 16 GPU-hours is more than this question deserves.

## 7. What comes out

The readout, the entity list and the four small trees under `roger/cap_pilot/`; one line in the October plan naming the cap and citing the readout; and `finish_reason` on every October response, so the question stays answerable later.

## 8. Open questions, answered (Roger, 2026-10-12)

1. 64 entities (≈ 16 GPU-hours): **64.**
2. The goal role for the `verbose`/`concise` combinations: **`angel`**, and both forms are run — the solo traits (the test) and the combinations (whether the worst case survives being combined, which is what 60% of the October grid is).  The plan had recommended the role with the most score-3 responses; `angel` is that role, and Roger's reason is that an angel has no tendency of its own toward either.
3. The cosine threshold is on **slot 0 only**; slots 1–7 are the selection-only effect, as § 5 now says.
