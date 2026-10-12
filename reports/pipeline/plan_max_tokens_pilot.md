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
- 20 combinations, a fixed-seed sample of the W15 grid (goal role × non-goal trait and the reverse), plus `r_<goal role>__verbose` and `r_<goal role>__concise` for one goal role, reported on their own likewise.

The list is generated once by the builder into [`cap_pilot_entities.json`](./cap_pilot_entities.json) (not there yet) with the seed recorded, so the pilot is reproducible.

**Caps:** 256, 512, 768, 1024.  512 is today's value; 1024 is the reference the others are compared to; 256 is there to show the slope, not as a candidate.

**Responses:** the pipeline's own 5 instruction variants × 100 questions = 500 per entity per cap; temperature and top-p at the pipeline defaults (0.7 / 0.9).  Per-request seeds are not available (the responses are not reproducible call-for-call), which is why the comparison is of means over 500, not of individual responses.

## 3. Prerequisites

1. The additive response fields from the review (P6): `finish_reason`, `thinking_stripped`, `thinking_suspected`, `question_id`, written by [`generation.py`](../../assistant_axis/generation.py).  The truncation share is read from `finish_reason`; without it the pilot would again be counting tokens after the fact.
2. The step-1 exit-status fix (P8.1), so a pod run that loses its engine mid-way is not reported as success.
3. A pod with the model and a fresh output root; nothing from the May tree is reused.

## 4. Runs

One output root per cap, all on the pod's local disk (not `/workspace`), under one pilot root, e.g. `/local/cap_pilot/cap{256,512,768,1024}/`.  For each cap, from `pipeline/`:

```
uv run 1_generate.py --model Qwen/Qwen3-32B --mode roger \
    --roles $(jq -r '.[]' cap_pilot_entities.json) \
    --max_tokens <CAP> --output_dir /local/cap_pilot/cap<CAP>/responses
uv run 2_activations.py --model Qwen/Qwen3-32B \
    --responses_dir /local/cap_pilot/cap<CAP>/responses \
    --output_dir /local/cap_pilot/cap<CAP>/activations --max_length 2048
uv run 3_judge.py --responses_dir /local/cap_pilot/cap<CAP>/responses \
    --output_dir /local/cap_pilot/cap<CAP>/scores --entity_type <roles|traits|combination>
uv run 4_vectors.py --activations_dir ... --scores_dir ... --output_dir /local/cap_pilot/cap<CAP>/vectors
```

(`--roles` filters the work items by output name in every mode since 2026-10-12; step 3 runs once per entity type, as the driver does; `--max_length 2048` holds a 1024-token response plus its prompt.)  Step 3 goes by batch, the default.  Activations (64 × 4 × 2.6 GB ≈ 670 GB) are deleted once step 4's vectors pass the scanner; responses, scores and vectors (small) come back to the repo under [`roger/cap_pilot/`](../../roger/cap_pilot/) (not there yet; `roger/` is git-ignored).

## 5. Measurements and the decision rule

A small tool, [`tools/cap_pilot_compare.py`](../../tools/cap_pilot_compare.py) (not there yet), reads the four trees and writes [`cap_pilot_readout.md`](./cap_pilot_readout.md) (not there yet) with, per entity and per stratum:

1. **Truncation share** at each cap, from `finish_reason == "length"`.
2. **Judge:** the score-3 share and the mean score at each cap, with the paired difference to the 1024 run.
3. **Vector:** the cosine between the entity's vector at each cap and its 1024 vector, per slot (slot 0 is the one the cap acts on; slots 1–7 are the header positions and should not move — a control on the run itself).
4. **Pair axes:** for the pairs among the pilot entities (`verbose`/`concise` first), the cosine of the pair-difference axis across caps at layer 25.
5. `verbose`, `concise` and their combinations reported separately.

**Decision rule, fixed now:** keep 512 if, over the stratum means, the slot-0 cosine between 512 and 1024 is ≥ 0.99 and the score-3 share moves by less than 2 points; otherwise take the smallest cap that meets both.  Whatever the outliers do is reported but does not decide: if `verbose` alone fails the rule, that is a note on `verbose`, not a reason to raise the cap for 3,072 entities.

Power: 64 paired entities put a standard error of about 0.002 on a mean cosine difference (per-entity spread ~0.01–0.02) and about 0.5 points on the score-3 share (each share is from 500 responses), so the rule's thresholds are resolved several times over.

## 6. Cost — to be confirmed by Roger before launch

- **Pod time:** step 1 at the April pace is ~2 min per entity at 512 and scales with the cap, so 64 × (0.5 + 1 + 1.5 + 2) × 2 min ≈ **10.7 GPU-hours**; step 2 scales the same way at roughly half, ≈ **5 GPU-hours**; total ≈ **16 GPU-hours**, over the 13 GPU-hour line in CLAUDE.md.  Parameters that differ from the defaults: `--max_tokens` 256/768/1024 (default 512), the entity filter `--roles` (default: all).  Everything else at the pipeline defaults.
- **Judge:** 64 × 4 × 500 = 128,000 calls at gpt-4.1-mini batch rates, ≈ **$25**, under the $20-per-invocation line per cap run (four runs of ≈ $6).  Real time would be ≈ $50; batch, as the default.
- Disk on the pod: ≈ 670 GB of activations transiently; ≈ 1 GB returned.

Halving the entity count to 32 keeps the paired design (standard errors ×1.4) at half the pod time, if 16 GPU-hours is more than this question deserves.

## 7. What comes out

The readout, the entity list and the four small trees under `roger/cap_pilot/`; one line in the October plan naming the cap and citing the readout; and `finish_reason` on every October response, so the question stays answerable later.

## 8. Open questions for Roger

1. 64 entities (≈ 16 GPU-hours) or 32 (≈ 8)?  Recommendation: 64 — the pod time is small against the ≈ 160 GPU-hours of the extraction it informs.
2. Which goal role for the `verbose`/`concise` combinations?  Recommendation: the goal role with the most score-3 responses in the May tree, so the combination is not itself a truncation outlier.
3. Should the decision rule's cosine threshold be on slot 0 only (recommended: it is the slot the cap acts on) or on all eight?
