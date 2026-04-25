# Results Analysis

Scripts that analyze outputs of the [`pipeline/`](../pipeline/) — vectors, scores,
responses, axes. Parallel in intent to [`data_analysis/`](../data_analysis/),
which _prepares_ the role/trait data for the pipeline.

## Scripts

### `axis_judge_correlation.py`

Tests how well a chosen semantic axis in activation space corresponds to
external judgement. Given an axis direction (either derived from a pair of
roles/traits, or loaded from a saved axis file) and pole descriptions plus
example lists, it:

1. Has an LLM judge score every role and trait in the corpus on a −3..+3
   rubric (excluding the pair itself and any example-list names).
2. Projects every role/trait's activation vector onto the axis, in both the
   raw activation metric and a soft-K=128 PCA-whitened metric (whitener fit
   on the held-out pool of roles + traits, with the excluded names removed
   so the same items don't define both the axis and the whitening basis).
3. Reports Spearman ρ between judge scores and projections, per token-slot
   and per metric, for up to three scoring modes:
    - the `description` field,
    - the 5 `pos` instructions,
    - score=3 model responses (question + answer).
4. Writes JSON results and a scatter-plot grid to `--output_dir`.

```bash
# Angel vs demon, three scoring modes, all slots
uv run python results_analysis/axis_judge_correlation.py \
  --pair angel demon --pair_type roles \
  --data_dir "runpod_workspace/qwen/qwen-3-32b Roger" \
  --scores_dir "runpod_workspace/qwen/qwen-3-32b Roger/roles/scores" \
  --responses_dir "runpod_workspace/qwen/qwen-3-32b Roger/roles/responses" \
  --layer 24 --whiten_K 128 --provider anthropic --all \
  --output_dir roger/axis_judge_angel_demon

# Manual axis from a saved axis.pt, scoring descriptions only
uv run python results_analysis/axis_judge_correlation.py \
  --axis_file "runpod_workspace/qwen/qwen-3-32b Roger/roles/axis.pt" \
  --neg_pole "mythical/unstructured entity" \
  --pos_pole "defined professional role with structured output" \
  --neg_examples demon,vampire,revenant,chimera \
  --pos_examples consultant,researcher,engineer,accountant,librarian \
  --data_dir "runpod_workspace/qwen/qwen-3-32b Roger" \
  --layer 24 --slot 1 --score_descriptions \
  --output_dir roger/axis_judge_pc1_roles
```

### Pole orientation convention

When the axis has a clear "good vs bad" polarity (e.g. `benign` vs `malicious`,
`honest` vs `deceptive`), put the socially-good pole as the **positive** (+3)
pole: `--pair benign malicious --pair_type traits`, not the reverse. For
morally-neutral axes (e.g. `performative` vs `functional`), either orientation
is fine.

The motivating intuition: RLHF'd judges appear to have a strong baseline
`+ = good` / `- = bad` prior, and aligning the rubric's +/- labels with the
judge's prior avoids cognitive dissonance.

#### Empirical validation (2026-04-24, malicious/benign trait pair)

We ran both orientations against both providers (Sonnet 4 and GPT-4.1-mini),
descriptions + instructions modes, 568 entities each. Headline numbers:

**Reproducibility under sign flip** (how often `score(forward) == -score(reverse)`)

| provider / mode | exact match | |δ|≤1 | |δ|≥2 |
|---|---:|---:|---:|
| Sonnet / descriptions | 79.8% | 96.7% | 3.3% |
| Sonnet / instructions | 77.1% | 98.2% | 1.8% |
| GPT / descriptions | 75.4% | 96.0% | 4.0% |
| GPT / instructions | 72.5% | 94.9% | 5.1% |

~75% exact agreement is noticeably below the "orientation-invariant" ideal
(~95%+); orientation is a real factor, not noise.

**Mean signed delta** = `mean(score_forward + score_reverse)` (>0 means
benign=+ inflates scores relative to malicious=+)

| | Sonnet | GPT |
|---|---:|---:|
| descriptions | **+0.092** | +0.011 |
| instructions | +0.021 | +0.000 |

Only Sonnet / descriptions shows clear mean-shift inflation; elsewhere the bias
is effectively zero. So the "benign=+ inflates everything uniformly" concern is
weak.

**Spearman ρ vs activation geometry — the clean signal**

The direction of orientation preference **depends on the metric**, which is
the most important finding:

*Raw metric* — benign=+ wins every comparison (16/16, p ≈ 2e-5 binomial):

| provider / mode / slot | forward (benign=+) | reverse (malicious=+) | Δ |
|---|---:|---:|---:|
| Sonnet / descriptions / slot 3 | +0.711 | +0.665 | −0.046 |
| Sonnet / instructions / slot 3 | +0.748 | +0.716 | −0.032 |
| GPT / descriptions / slot 3 | +0.704 | +0.665 | −0.039 |
| GPT / instructions / slot 3 | +0.726 | +0.685 | −0.041 |

Effect sizes 0.03–0.07 across all 4 slots, all 4 provider/mode combos.

*Whitened metric* — malicious=+ wins 14/16, effects 0.01–0.03:

| provider / mode / slot | forward (benign=+) | reverse (malicious=+) | Δ |
|---|---:|---:|---:|
| Sonnet / descriptions / slot 3 | +0.231 | +0.262 | **+0.031** |
| Sonnet / instructions / slot 3 | +0.238 | +0.271 | +0.033 |
| GPT / descriptions / slot 3 | +0.218 | +0.248 | +0.031 |
| GPT / instructions / slot 3 | +0.215 | +0.221 | +0.005 |

**This asymmetry is unexplained** and worth following up. Hypothesis: the raw
metric is dominated by high-variance PC directions that happen to carry the
judge's charity-bias inflation in the benign direction, so benign=+ orientation
"rides" that inflation constructively. Whitening removes the high-variance
dominance, making the ρ more sensitive to the judge's true discrimination
ability, which is slightly better when malicious=+ (less charity bias pulling
items toward zero from the malicious side).

**Provider-specific flip signatures**

GPT exhibits a subtle rubric-confusion pattern Sonnet does not: 14 entities
scored `(fwd=-1, rev=-1)` or `(fwd=+1, rev=+1)` — literal contradictions under
sign flip. E.g. `unhelpful` scored −1 in *both* orientations (meaning "mildly
malicious" in forward *and* "mildly benign" in reverse). Sonnet essentially
never does this; its disagreements are closer to `(fwd=+2, rev=0)` — loss of
decisiveness when malicious is forced into the + slot, not outright
contradictions.

**Practical recommendations**

- Default: `--pair <good_pole> <bad_pole>` for good-vs-bad axes. Gives the best
  raw-metric ρ and the most decisive score distribution.
- If the analysis relies on the **whitened metric**, consider running the
  reverse orientation too and reporting the better ρ (or averaging).
- If using **GPT-4.1-mini** (cheaper exploration), spot-check a few
  mildly-negative-trait entities for rubric-confusion patterns.
- For critical axes, running both orientations and averaging the scores
  gives ~0.03 ρ gain over either alone and cancels most orientation bias,
  at 2× the judge cost.

### Which scoring source and which metric — empirical findings

We ran the tool over 20 reciprocal-antonym trait axes at GPT-4.1-mini, then
selectively re-ran 7 of them with Sonnet 4 and added response-mode scoring.
The 20-axis and 7-axis data is persisted under
[`roger/axis_judge_experiments/`](../roger/axis_judge_experiments/) with
[`summary.json`](../roger/axis_judge_experiments/summary.json) (20 axes, GPT)
and [`summary_7axes_full.json`](../roger/axis_judge_experiments/summary_7axes_full.json)
(7 axes × 3 sources × 2 metrics).

#### Raw vs whitened

Across all 20 axes (GPT, slot=3, scores averaged across descriptions+instructions
per entity before correlating — "both_mean"):

| metric | mean ρ | min | max | ρ distribution |
|---|---:|---:|---:|---|
| raw | **+0.541** | +0.04 | +0.80 | wide; axis-dependent |
| whitened | +0.201 | +0.11 | +0.28 | tight cluster |

**Raw wins 19/20 axes.** Only `ecocentric/anthropocentric` flips — raw ρ is
near zero (+0.04), whitened salvages a weak signal (+0.18). The tightness of
the whitened band (σ ≈ 0.05) vs the wide raw spread (σ ≈ 0.21) is itself a
finding: the raw metric registers how well each axis aligns with the model's
dominant-variance subspace, while the whitened metric is SNR-floored by
low-variance noise and produces similar ρ for most axes regardless of their
actual representational quality.

For interpreting a single axis in isolation, **prefer raw ρ**. For cross-axis
comparison in a fairness-across-directions sense, whitened is the more
direction-neutral metric but paints a much flatter picture.

#### Scoring source: descriptions vs instructions vs responses

On the same 20 axes (GPT only):

| source | mean raw ρ | mean whitened ρ | notes |
|---|---:|---:|---|
| descriptions only | +0.512 | +0.186 | cheapest; 1 judge call per entity |
| instructions only | +0.531 | +0.201 | slight edge over descriptions |
| both_mean (avg of above) | **+0.541** | +0.201 | +0.008 raw gain over best-single; 2× cost |

On the 7-axis deeper experiment, **response-mode is the clear winner on raw**:

| source | mean raw ρ (7 axes) | mean whitened ρ |
|---|---:|---:|
| GPT desc+inst | +0.451 | +0.192 |
| Sonnet desc+inst | +0.439 | +0.184 |
| **GPT responses** | **+0.605** | +0.169 |

Mean improvement of GPT responses over best-desc+inst = **+0.135 raw ρ**, with
per-axis gains ranging from −0.05 to +0.56. The dramatic case is
`ecocentric/anthropocentric`: desc+inst essentially fails (raw ρ ≈ 0), but
responses captures it at ρ = +0.60. Behavioral evidence reveals the axis where
trait-description text is too generic to discriminate.

Response-mode does **not** help on whitened (−0.028 mean); same SNR-floor
pattern. And response-mode is ~20× more expensive than desc+inst.

#### GPT vs Sonnet agreement

On desc+inst for the same 7 axes, GPT and Sonnet agree strongly:

- Pooled across all 3,976 (entity, axis) pairs: **Spearman ρ = 0.816**.
- Per-axis agreement: 0.68–0.92, highest on strong axes (`helpful/unhelpful`
  0.92), lowest on subtle ones (`systems_thinker/analytical` 0.68).
- Per-axis ρ-vs-projection is essentially equivalent between the two providers
  (mean difference +0.011 raw in favor of Sonnet, +0.008 whitened).

For exploration and iteration, **GPT-4.1-mini is ~5× cheaper with statistically
equivalent results**. Sonnet is only worth the premium for final reporting or
for axes where the 0.01-level difference matters.

#### Recommendations

| goal | recommended source | metric | why |
|---|---|---|---|
| Sanity-check an axis cheaply | GPT desc+inst | raw | ~$1/axis, good enough signal |
| Publish ρ for a given axis | GPT responses | raw | best signal, ~$40/axis |
| Compare across axes fairly | whitened (any source) | whitened | equalizes variance across directions |
| Diagnose "does this axis exist at all?" | GPT responses | both raw and whitened | if whitened ρ is nonzero and raw ρ is near-zero, the axis lives in low-variance directions |

### Adaptive per-PC whitening — empirical study

We did an extended study of whether per-PC whitening (each PC gets its own
scale factor β_k ∈ [0, 1]) can beat fixed soft-K whitening. Four operational
conclusions, all from experiments on the 7 axes in
[`pair_list_7.json`](../roger/axis_judge_experiments/pair_list_7.json):

**1. ‖m‖/‖diff‖ predicts axis hardness (label-free).**

For an axis defined by `diff = vec[pos] − vec[neg]`, the pair's common-mode
offset is `m = (vec[pos] + vec[neg]) − 2·mean_corpus`. The ratio ‖m‖/‖diff‖
measures how far the pair's midpoint sits from the corpus center relative to
the axis magnitude.

| ‖m‖/‖diff‖ range | example axes | raw ρ range |
|---|---|---|
| < 1.0 | helpful/unhelpful | 0.78-0.82 (easy) |
| 1.0–1.5 | guileless/scheming, improvisational/methodical | 0.38-0.69 |
| > 1.5 | progressive/conservative, ecocentric/anthropocentric, systems_thinker/analytical | 0.00-0.58 (hard) |

Pearson correlation between ‖m‖/‖diff‖ and raw ρ is **−0.67** (D+I) and **−0.74**
(responses) across the 7 axes — a single-number label-free predictor of
axis quality. Large common-mode offset means the pair activations share a big
"common mode" signature that isn't the axis itself — and projecting entities
onto the axis direction picks up that shared structure as noise.

**2. soft-K=4 is the best fixed label-free recipe.**

From the whitening-K sweep across 20 axes, mean responses ρ peaks at K=4 (0.652)
vs K=0 (0.605), K=1 (0.639), K=2 (0.646), K=8 (0.587), K=16 (0.471), K=128
(0.169). See [`rho_vs_whitening_K.png`](../roger/axis_judge_experiments/rho_vs_whitening_K.png).
K=4 is the default recommendation when no judge labels are available.

**3. Label-using coord ascent finds well-generalizing β* (+0.13-0.17 held-out gain).**

[`coordinate_ascent.py`](../roger/axis_judge_experiments/coordinate_ascent.py)
implements exact per-PC Spearman-optimal β via pairwise rank-crossing
enumeration. 5-fold CV on 7 axes × 3 score sources:

| source | mean test ρ (β*) | mean test ρ (K=4) | held-out gain |
|---|---:|---:|---:|
| desc+inst | 0.671 | 0.505 | **+0.166** |
| responses | 0.766 | 0.638 | **+0.127** |
| joint (D+I+RESP) | 0.747 | 0.583 | **+0.164** |

The coarse-discrete variant (β ∈ {0, σ_{M}²/σ_k² for M ∈ {2,3,5,9,17}, 1}) gives
virtually the same held-out ρ with ~half the training-ρ overfitting — suggesting
the finer continuous β values were fitting noise. Use the coarse version for
interpretability. Per-axis data: [`coarse_discrete_coordinate_ascent.json`](../roger/axis_judge_experiments/coarse_discrete_coordinate_ascent.json).

**4. Label-free geometric rules cap at ~10-15% of oracle recovery.**

Tried (a) hand-crafted rules on c_k², m_cos_k²; (b) random forests over (log K,
c_k², m_cos_k²). In-sample: RF recovers 78% of oracle; leave-one-axis-out it
drops to ~5%. The v1 rule (Keep if c_k² ≥ 0.20, Ablate if m_cos_k²/(c_k²+m_cos_k²) ≥ 0.90,
else shrink to σ_5²) recovers ~13% in-sample. With n=7 axes, simple geometric
features can't reliably predict axis-specific β* patterns.

Most of the oracle gain is genuinely axis-specific information (likely
semantic-content of each PC in the context of the axis's meaning). The ~13%
that is captured by simple rules is the "easy" structural part (ablate PCs where
low c² coincides with high m_cos²).

### Recommendations (label-free workflow)

1. Compute ‖m‖/‖diff‖ per axis before any judging — axes > 1.5 are hard.
2. Use soft-K=4 whitening as the default metric.
3. If budget permits judge-scoring, coord ascent gives a robust ~+0.13 CV gain.
4. If exploring many axes cheaply, report raw ρ at slot 3 with GPT-4.1-mini
   descriptions+instructions; spot-check with response mode.

### Judge defaults

Judge model defaults: `claude-sonnet-4-20250514` with `--provider anthropic`
(the default), `gpt-4.1-mini` with `--provider openai`. Results cache under
`<output_dir>/scores_*.json` and resume on rerun; pass `--no_cache` to
rescore from scratch.

## Output layout

```
<output_dir>/
├── config.json                  # all resolved args + axis metadata
├── scores_descriptions.json     # {name: int score in [-3, 3]}
├── scores_instructions.json     # {name: int score in [-3, 3]}
├── scores_responses.json        # {name: {mean_score, n_scored, n_total}}
├── projections.json             # {slot: {name: {raw, whitened}}}
├── correlations.json            # {mode: {slot: {raw|whitened: {rho, p, n}}}}
└── correlation_plot.png         # scatter grid (rows=modes, cols=slot×metric)
```
