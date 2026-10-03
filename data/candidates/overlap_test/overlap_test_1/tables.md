# Overlap test: tables

409 pairs in 180 calls.  Reference model: Opus 5.5.  Generated from `summary.json` beside this file.

## Parse rates (pairs whose answer parsed)

| rubric | model | ok / total | rate | first attempt |
|---|---|---|---|---|
| A | Haiku 4.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| A | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| A | Sonnet 5.5 | 409 / 409 | 1.0000 | 406 / 409 (0.9927) |
| B | Haiku 4.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| B | Opus 5.5 | 409 / 409 | 1.0000 | 408 / 409 (0.9976) |
| B | Sonnet 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |

## Agreement with Opus 5.5

Exact agreement over every answer (categories included); then, on the pairs where both gave a number, exact, within one point, the mean difference (model minus reference) and the weighted kappa (quadratic; linear in brackets).

| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |
|---|---|---|---|---|---|---|---|---|
| A | Haiku 4.5 | 409 | 64% | 318 | 58% | 98% | 0.35 | 0.76 (0.60) |
| A | Sonnet 5.5 | 409 | 86% | 323 | 85% | 100% | 0.04 | 0.91 (0.85) |
| B | Haiku 4.5 | 409 | 55% | 404 | 55% | 95% | 0.41 | 0.87 (0.71) |
| B | Sonnet 5.5 | 409 | 85% | 409 | 85% | 100% | 0.12 | 0.96 (0.90) |

Categorical answers against the reference (rows: reference; columns: model):

- rubric A, Haiku 4.5: numeric: numeric 318, opposite 14; opposite: opposite 77
- rubric A, Sonnet 5.5: numeric: numeric 323, opposite 9; opposite: opposite 77
- rubric B, Haiku 4.5: numeric: numeric 404, unsure 5
- rubric B, Sonnet 5.5: numbers only

## Spearman correlation with the persona-space and the embedding cosine

Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest pairs without recorded opposites.

| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |
|---|---|---|---|---|---|---|
| A | Haiku 4.5 | persona | 0.56 [0.44, 0.66] (n 228) | 0.56 [0.44, 0.66] (n 228) | 0.50 [0.39, 0.61] (n 197) | 0.50 [0.39, 0.61] (n 197) |
| A | Haiku 4.5 | embedding | 0.62 [0.53, 0.69] (n 318) | 0.62 [0.53, 0.69] (n 318) | 0.46 [0.36, 0.56] (n 254) | 0.46 [0.36, 0.56] (n 254) |
| A | Sonnet 5.5 | persona | 0.67 [0.56, 0.75] (n 232) | 0.67 [0.56, 0.75] (n 232) | 0.61 [0.50, 0.71] (n 198) | 0.61 [0.50, 0.71] (n 198) |
| A | Sonnet 5.5 | embedding | 0.71 [0.63, 0.77] (n 323) | 0.71 [0.63, 0.77] (n 323) | 0.61 [0.51, 0.69] (n 256) | 0.61 [0.51, 0.69] (n 256) |
| A | Opus 5.5 | persona | 0.68 [0.57, 0.76] (n 240) | 0.68 [0.57, 0.76] (n 240) | 0.63 [0.51, 0.72] (n 203) | 0.63 [0.51, 0.72] (n 203) |
| A | Opus 5.5 | embedding | 0.68 [0.60, 0.75] (n 332) | 0.68 [0.60, 0.75] (n 332) | 0.57 [0.46, 0.66] (n 261) | 0.57 [0.46, 0.66] (n 261) |
| B | Haiku 4.5 | persona | 0.68 [0.60, 0.75] (n 280) | 0.60 [0.50, 0.69] (n 251) | 0.62 [0.52, 0.70] (n 230) | 0.53 [0.41, 0.62] (n 210) |
| B | Haiku 4.5 | embedding | 0.29 [0.19, 0.39] (n 404) | 0.46 [0.36, 0.55] (n 343) | 0.17 [0.05, 0.27] (n 300) | 0.35 [0.24, 0.45] (n 269) |
| B | Sonnet 5.5 | persona | 0.73 [0.65, 0.79] (n 280) | 0.67 [0.58, 0.74] (n 251) | 0.68 [0.58, 0.75] (n 230) | 0.60 [0.50, 0.69] (n 210) |
| B | Sonnet 5.5 | embedding | 0.34 [0.24, 0.44] (n 409) | 0.54 [0.45, 0.62] (n 348) | 0.23 [0.12, 0.34] (n 300) | 0.42 [0.31, 0.52] (n 269) |
| B | Opus 5.5 | persona | 0.76 [0.68, 0.82] (n 280) | 0.70 [0.62, 0.78] (n 251) | 0.71 [0.62, 0.78] (n 230) | 0.65 [0.55, 0.73] (n 210) |
| B | Opus 5.5 | embedding | 0.35 [0.25, 0.45] (n 409) | 0.55 [0.45, 0.63] (n 348) | 0.25 [0.13, 0.35] (n 300) | 0.43 [0.32, 0.53] (n 269) |

## Rubric A against rubric B on the same pairs

rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a number; paired 95% bootstrap interval (targets resampled).

| model | population | cosine | n | rho A | rho B | A - B | 95% interval |
|---|---|---|---|---|---|---|---|
| Haiku 4.5 | non_antonym | persona | 228 | 0.56 | 0.50 | 0.05 | [-0.03, 0.14] |
| Haiku 4.5 | non_antonym | embedding | 313 | 0.60 | 0.47 | 0.12 | [0.05, 0.20] |
| Haiku 4.5 | nearest_non_antonym | persona | 197 | 0.50 | 0.45 | 0.05 | [-0.05, 0.16] |
| Haiku 4.5 | nearest_non_antonym | embedding | 254 | 0.46 | 0.33 | 0.14 | [0.03, 0.24] |
| Sonnet 5.5 | non_antonym | persona | 232 | 0.67 | 0.60 | 0.07 | [-0.01, 0.14] |
| Sonnet 5.5 | non_antonym | embedding | 323 | 0.71 | 0.57 | 0.14 | [0.07, 0.22] |
| Sonnet 5.5 | nearest_non_antonym | persona | 198 | 0.61 | 0.55 | 0.06 | [-0.04, 0.15] |
| Sonnet 5.5 | nearest_non_antonym | embedding | 256 | 0.61 | 0.41 | 0.19 | [0.10, 0.30] |
| Opus 5.5 | non_antonym | persona | 240 | 0.68 | 0.68 | 0.00 | [-0.08, 0.08] |
| Opus 5.5 | non_antonym | embedding | 332 | 0.68 | 0.59 | 0.09 | [0.02, 0.16] |
| Opus 5.5 | nearest_non_antonym | persona | 203 | 0.63 | 0.63 | 0.00 | [-0.10, 0.10] |
| Opus 5.5 | nearest_non_antonym | embedding | 261 | 0.57 | 0.44 | 0.13 | [0.03, 0.24] |

## Known groups, rubric A

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Haiku 4.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|---|
| nearest | 300 | 2.11 / 30% / 15% / 0% | 1.75 / 16% / 15% / 0% | 1.68 / 14% / 13% / 0% |
| drop_or_merge | 11 | 3.20 / 80% / 9% / 0% | 3.10 / 100% / 9% / 0% | 2.90 / 80% / 9% / 0% |
| deliberate_duplicate | 3 | 2.33 / 33% / 0% / 0% | 2.00 / 0% / 0% / 0% | 2.00 / 0% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.91 / 23% / 35% / 0% | 1.56 / 16% / 26% / 0% | 1.56 / 15% / 21% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.14 / 0% / 7% / 0% | 0.14 / 0% / 7% / 0% | 0.17 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 15, 1 93, 2 117, 3 32, 4 4, opposite 39
- drop_or_merge: 2 2, 3 7, 4 1, opposite 1
- deliberate_duplicate: 2 3
- duplicate: 3 1
- near_distinct: 0 2, 1 13, 2 8, 3 3, 4 1, opposite 7
- antonym: opposite 30
- random: 0 26, 1 3, 2 1

## Known groups, rubric B

Mean of the numeric answers / share at 3 or more / share unsure; n in the first column.

| group | n | Haiku 4.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|---|
| nearest | 300 | 2.87 / 74% / 0% | 2.55 / 64% / 0% | 2.40 / 57% / 0% |
| drop_or_merge | 11 | 3.64 / 91% / 0% | 3.55 / 91% / 0% | 3.64 / 91% / 0% |
| deliberate_duplicate | 3 | 3.67 / 100% / 0% | 3.33 / 100% / 0% | 3.33 / 100% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% | 3.00 / 100% / 0% | 3.00 / 100% / 0% |
| near_distinct | 34 | 1.88 / 50% / 0% | 1.76 / 38% / 0% | 1.65 / 29% / 0% |
| antonym | 30 | 0.00 / 0% / 0% | 0.00 / 0% / 0% | 0.00 / 0% / 0% |
| random | 30 | 1.64 / 32% / 17% | 1.13 / 0% / 0% | 1.03 / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 48, 1 12, 2 70, 3 111, 4 59
- drop_or_merge: 0 1, 4 10
- deliberate_duplicate: 3 2, 4 1
- duplicate: 3 1
- near_distinct: 0 12, 1 2, 2 10, 3 6, 4 4
- antonym: 0 30
- random: 0 3, 1 23, 2 4

## Unsure and opposite rates

| rubric | model | n | unsure | opposite | opposite on the antonym group | opposite on nearest recorded opposites | opposite elsewhere |
|---|---|---|---|---|---|---|---|
| A | Haiku 4.5 | 409 | 0% (0) | 22% (91) | 100% of 30 | 100% of 31 | 9% of 348 |
| A | Sonnet 5.5 | 409 | 0% (0) | 21% (86) | 100% of 30 | 100% of 31 | 7% of 348 |
| A | Opus 5.5 | 409 | 0% (0) | 19% (77) | 100% of 30 | 100% of 31 | 5% of 348 |
| B | Haiku 4.5 | 409 | 1% (5) | 0% (0) | 0% of 30 | 0% of 31 | 0% of 348 |
| B | Sonnet 5.5 | 409 | 0% (0) | 0% (0) | 0% of 30 | 0% of 31 | 0% of 348 |
| B | Opus 5.5 | 409 | 0% (0) | 0% (0) | 0% of 30 | 0% of 31 | 0% of 348 |

## Where Haiku and Sonnet agree or differ, what Opus says

| rubric | Haiku = Sonnet | Opus the same | Haiku != Sonnet | Opus sides with Haiku | with Sonnet | neither |
|---|---|---|---|---|---|---|
| A | 261 | 234 (90%) | 148 | 26 | 116 | 6 |
| B | 255 | 215 (84%) | 154 | 8 | 131 | 15 |

## Rubric A (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 43 | 0.124 | 17 | 0.221 |
| 1 | 109 | 0.330 | 87 | 0.440 |
| 2 | 131 | 0.400 | 101 | 0.605 |
| 3 | 43 | 0.561 | 29 | 0.820 |
| 4 | 6 | 0.621 | 6 | 0.873 |
| opposite | 77 | 0.399 | 40 | 0.033 |

## Rubric B (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 94 | 0.367 | 55 | 0.055 |
| 1 | 37 | 0.142 | 14 | 0.374 |
| 2 | 84 | 0.334 | 63 | 0.450 |
| 3 | 120 | 0.397 | 88 | 0.583 |
| 4 | 74 | 0.498 | 60 | 0.760 |

## Where the rubrics differ most (Opus 5.5)

B minus A over 332 pairs with two numbers: counts {'-2': 1, '-1': 14, '0': 49, '1': 188, '2': 76, '3': 3, '4': 1}, mean 1.015.

| target | listed | group | A | B | A's reason | B's reason |
|---|---|---|---|---|---|---|
| erudite | literate | nearest | 0 | 4 | Basic reading and writing ability is only a distant precondition of deep scholarly learning. | Being deeply bookish presupposes reading and writing with ease. |
| structuralist | analytical | nearest | 1 | 4 | Both involve systematic analysis, but analytical means decomposing a topic into parts, while structuralist means seeking the underlying patterns and frameworks that govern a whole. | Finding underlying patterns and frameworks takes systematic, methodical analysis, so a structuralist is almost always analytical. |
| techno-hierophantic | esoteric | nearest | 1 | 4 | Both involve obscure, initiate-only language, but esoteric means expert jargon in general, while the target adds sacred revelation, glyphs and an initiate dyad. | Revealing hidden mysteries to a chosen initiate, with obscure jargon, is esoteric in nature. |
| techno-hierophantic | spiritual | nearest | 1 | 4 | Both deal with sacred, transcendent truths, but the target's defining feature is techno-symbolic mediation, which spiritual lacks. | The trait centers on sacred mysteries and cosmic truths, so it is inherently spiritual. |
| compassionate | empathetic | drop_or_merge | 2 | 4 | Both involve warm, caring responses to others' feelings, but empathetic stresses understanding of emotions generally, while compassionate stresses responding to suffering. | Compassion rests on empathic understanding of others' feelings, so the two almost always go together. |
| honorable | deontological | deliberate_duplicate | 2 | 4 | Both reject letting consequences justify forbidden acts, but deontological is a general rule-and-duty ethical stance, while honorable adds a personal code held to at real cost. | Holding that some acts are never justified regardless of the outcome is essentially a deontological stance, so the two nearly always go together. |
| nationalist | patriotic | near_distinct | 2 | 4 | Both center on attachment to one's own nation. Patriotism stresses love and pride, while nationalism stresses putting national interests above other nations', so each adds something the other lacks. | Nationalists almost always express love, pride, and loyalty toward their country. |
| risk-averse | cautious | near_distinct | 2 | 4 | Both center on avoiding risk, but cautious adds warning, deliberation and seeking expertise, while risk-averse adds choosing guaranteed outcomes over better bets. | Avoiding any chance of loss naturally goes with emphasizing risks and deliberating carefully before acting. |
| sardonic | sarcastic | drop_or_merge | 2 | 4 | Both are cutting, ironic mockery, but sarcastic stresses saying the opposite of what is meant, while sardonic stresses dry, cynical observation of absurdity. | A sardonic persona's cutting, ironic mockery very nearly always shows up as sarcastic remarks. |
| agreeable | cooperative | nearest | 2 | 4 | Cooperation is one part of agreeableness, but cooperative is about teamwork and collective success rather than avoiding conflict and keeping harmony. | Agreeableness explicitly emphasizes cooperation, so collaborative framing almost always comes with it. |
| nationalist | regionalist | nearest | 3 | 1 | The same favoritism toward one's own unit, applied to a sub-national region instead of the nation, which is a difference of scope only. | Nationalism stresses national unity and often opposes regional loyalties that compete with it, though some nationalists also favor their home region. |
| confident | overconfident | nearest | 3 | 2 | Overconfident is the same certainty without hedging, carried beyond what is warranted. | Stating things without hesitation often tips into unwarranted certainty, but confidence can also be well-founded. |
| elitist | aristocratic | nearest | 3 | 2 | Aristocratic belief is elitism specifically grounded in birth and bloodline, a narrower form of the same hierarchical conviction. | Belief in rank by birth is one form of elitism, but many elitists ground superiority in education or talent rather than bloodline. |

## The same pair in two calls

- rubric A: Haiku 4.5 25 of 38 the same; Sonnet 5.5 32 of 38 the same; Opus 5.5 32 of 38 the same
- rubric B: Haiku 4.5 26 of 38 the same; Sonnet 5.5 28 of 38 the same; Opus 5.5 26 of 38 the same
