# Persona-space fit `fit_2026-10-13`

The ridge map from a `label: description` embedding (OpenAI text-embedding-3-large, cut to 20 words) to the entity's persona vector (Qwen3-32B, slot 6, layer 25, centred on the corpus mean, soft shear L=3), fitted on 572 entities (293 traits, 279 roles) with a role column, evaluated on 5 arrangement-grouped folds (485 groups: a pair, triangle or tetrahedron of traits, or an arrangement of roles, is held out whole).  Chosen: **alpha 0.3, N = 20**.  The plot: [fit_report.png](./fit_report.png).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md#persona-space-novelty).

## The pool

582 vectors (302 traits, 280 roles); 574 with a current file (295 + 279; 19 + 1 through `renamed_from`); 572 train.  Orphans (no file; in the pool for the geometry, never trained on or listed): `conceptual|T`, `cruel|T`, `dramatic|T`, `enigmatic|T`, `mercurial|T`, `regulatory|T`, `technical|T`, `adolescent|R`.  Sense-changed renames (the May vector is the old sense): `libertarian|T`, `savage|T`.

Spectrum: K for 50 / 80 / 90 / 95 / 99% of the variance = 10 / 45 / 96 / 170 / 373; top 12 carry 55.1%; log-log slope over 1-64 -1.112; λ1/λ12 = 5.81, λ1/λ32 = 19.17.

## Alpha

| alpha | median cos | traits | roles | top-1 | top-5 | best residual Spearman | pred / actual residual_24 |
|---|---|---|---|---|---|---|---|
| 0.03 | 0.697 | 0.711 | 0.674 | 0.703 | 0.969 | 0.634 | 0.270 / 0.362 |
| 0.1 | 0.717 | 0.732 | 0.698 | 0.740 | 0.969 | 0.647 | 0.233 / 0.362 |
| 0.3 **(chosen)** | 0.732 | 0.751 | 0.721 | 0.745 | 0.970 | 0.644 | 0.184 / 0.362 |
| 1 | 0.737 | 0.754 | 0.723 | 0.734 | 0.960 | 0.598 | 0.123 / 0.362 |
| 3 | 0.716 | 0.731 | 0.699 | 0.640 | 0.935 | 0.506 | 0.075 / 0.362 |

Rule: 0.01 tie window on the median cosine, the smaller alpha wins.

## Recovery by kind (chosen alpha)

| kind | median cos | top-1 | top-5 |
|---|---|---|---|
| traits | 0.751 | 0.737 | 0.966 |
| roles | 0.721 | 0.753 | 0.975 |
| all | 0.732 | 0.745 | 0.970 |

Recovery: the held-out prediction's nearest among the 572 actual vectors is its own (top-1) or among the five nearest (top-5).  For held-out traits, the nearest other entity is a role 10.6% of the time.

## Per-PC R² (chosen alpha; the pool's principal components)

| PC | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R² | 0.81 | 0.80 | 0.77 | 0.76 | 0.81 | 0.71 | 0.64 | 0.65 | 0.69 | 0.68 | 0.50 | 0.65 |

| PC | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R² | 0.56 | 0.57 | 0.49 | 0.43 | 0.43 | 0.57 | 0.47 | 0.53 | 0.40 | 0.50 | 0.40 | 0.44 |

Means: PCs 9-24 0.52, 25-48 0.32, 49-64 0.17.  A direction the text predicts badly is one this text-only scorer cannot see.

## The N sweep (chosen alpha)

| N | Spearman, all | traits | predicted median | actual median |
|---|---|---|---|---|
| 12 | 0.644 | 0.609 | 0.314 | 0.495 |
| 16 | 0.620 | 0.574 | 0.258 | 0.439 |
| 20 **(chosen)** | 0.637 | 0.617 | 0.219 | 0.399 |
| 24 | 0.626 | 0.624 | 0.184 | 0.362 |
| 28 | 0.618 | 0.609 | 0.159 | 0.331 |
| 32 | 0.604 | 0.585 | 0.138 | 0.311 |

Rule: the largest Spearman; Ns within 0.02 of it tie, and the one nearest 20 wins.

## kNN baseline

The cosine-weighted mean of the k nearest training vectors by embedding cosine, against the ridge's 0.732:

| k | 1 | 3 | 5 | 10 |
|---|---|---|---|---|
| median cos | 0.568 | 0.663 | 0.675 | 0.693 |

## The gloss side

277 trained traits also have an M1 gloss of their label (m1_validation_r2, existing stratum).  Predicted from `label: M1 gloss` with the fold model that held them out, their median cosine to the actual vector is 0.697, against 0.753 from their descriptions: a candidate (gloss-only) lands about as well as a trait described by a gloss.

## Calibration and the thresholds (gate 1)

Shrinkage: the held-out predicted `residual_20` has median 0.219 against the actual 0.399, so a candidate's residual is read as its percentile among the held-out predictions (`residual_pct`).

- `dup_threshold` = **0.732** (the median held-out cosine between a prediction and its own vector).  The flag's base rate: a held-out existing entity's prediction is at or above it to *another* entity 32.3% of the time (the median nearest-other cosine is 0.683, p90 0.800).  That is not a false-alarm rate: 37% of existing entities have an actual neighbour at the threshold (the corpus is dense here: median actual nearest-other cosine 0.688); the flag fires for 66% of those and for 13% of the entities with none (the predictor's false-alarm rate), so 25% of flags are false alarms.  A genuinely new candidate with no close corpus neighbour can expect roughly the false-alarm rate.
- `novel_pct` = **0.80**.
- `cover_questioned` cosine: 0.610 (the 10th percentile of held-out self-cosines); `novel_vs_covered` percentile 0.90.
- Set by: plan default.

The duplicate threshold against M3's own concept readings (the overlap test of 2026-10-03, Opus 5.5's first reading of each pair of corpus traits that both train): the cosine of the target's held-out *prediction* with the listed trait's actual vector (what a candidate duplicating the listed trait would show), beside the actual-actual cosine.

| rubric-A reading | pairs | median predicted cos | median actual cos | share at or above dup_threshold |
|---|---|---|---|---|
| 4 | 6 | 0.798 | 0.897 | 1.00 |
| 3 | 31 | 0.742 | 0.781 | 0.55 |
| 2 | 112 | 0.615 | 0.596 | 0.12 |
| 1 | 54 | 0.486 | 0.456 | 0.07 |
| 0 | 11 | 0.300 | 0.179 | 0.00 |
| opposite | 44 | 0.083 | -0.061 | 0.00 |

| percentile | 0 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| predicted residual | 0.062 | 0.136 | 0.156 | 0.177 | 0.196 | 0.219 | 0.237 | 0.255 | 0.281 | 0.325 | 0.575 |
| actual residual | 0.144 | 0.270 | 0.311 | 0.347 | 0.370 | 0.399 | 0.426 | 0.449 | 0.484 | 0.531 | 0.694 |
| self cosine | 0.205 | 0.610 | 0.650 | 0.682 | 0.712 | 0.732 | 0.756 | 0.777 | 0.796 | 0.828 | 0.922 |

