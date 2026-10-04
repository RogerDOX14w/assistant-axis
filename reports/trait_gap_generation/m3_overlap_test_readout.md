# The M3 overlap rubrics tested: concept similarity against co-occurrence (2026-10-03)

The pre-pilot test that [m3_overlap_rubric_draft.md](./m3_overlap_rubric_draft.md) designs ("The test")
and item 9 of the M3 design asks for ([coding_plan_platform.md](./coding_plan_platform.md), last section).
Both signed-off rubrics of the [overlap call](./glossary.md#relation-overlap-calls), A (concept similarity,
[rubrics/overlap_concept.md](./rubrics/overlap_concept.md)) and B (co-occurrence,
[rubrics/overlap_cooccurrence.md](./rubrics/overlap_cooccurrence.md)), both pinned as version 2 and
described in the glossary under [rubrics A and B](./glossary.md#rubrics-a-b), ran on Haiku 4.5, Sonnet 5.5
and Opus 5.5 over 409 pairs of existing traits where the right answers are partly known.  Opus is the
[reference model](./glossary.md#reference-model), as in the [Opus audit](./opus_audit_m1.md).  Run
`overlap_test_1`; every file is under
[data/candidates/overlap_test/overlap_test_1/](../../data/candidates/overlap_test/overlap_test_1/).

**Addendum, 2026-10-04:** Fable 5.1 was added to the run as a fourth model on rubric A ($3.17; the run's
total is now $7.15), after Roger's marks; see "Fable through the API, and the six-way chart" under
"Roger's marks".  The tables and summary now carry four models; the sections below were written with
three and are left as they were.

## Headline

- **409 pairs in 180 calls** per rubric and model (100 nearest-neighbour targets, 80 labelled-pair
  targets), **1,082 calls** in all (6 x 180, plus 2 calls asked again).
- **Cost $3.99** live against an estimate of $4.47 (cap $15), from
  [usage.json](../../data/candidates/overlap_test/overlap_test_1/usage.json):

  | model | calls | cost | rubric A | rubric B |
  |---|---|---|---|---|
  | Haiku 4.5 | 360 | $0.50 | $0.27 | $0.24 |
  | Sonnet 5.5 | 361 | $1.19 | $0.65 | $0.55 |
  | Opus 5.5 | 361 | $2.29 | $1.23 | $1.06 |

- **[Parse rates](./glossary.md#parse-rate): 409 of 409 for every rubric and model** in the end.  At the
  first attempt, Sonnet's rubric-A answers parsed 406 of 409 and Opus's rubric-B answers 408 of 409; all
  the others were complete at once.  The way there is told under "Parse failures and what was changed"
  below: the first Sonnet stage tripped the 99% guard and the run stopped as designed.
- **Agreement with Opus** (pairs where both gave a number): Sonnet 85% exact and a
  [weighted kappa](./glossary.md#weighted-kappa) of 0.91 on A, 0.96 on B; Haiku 58% and 0.76 on A, 55% and
  0.87 on B.  Haiku scores higher than Opus by about a third of a point on both rubrics.
- **Agreement with [persona space](./glossary.md#persona-space)**, the outside check neither rubric sees
  ([Spearman](./glossary.md#spearman) with the cosine of the two persona vectors, pairs without recorded
  opposites): Opus 0.68 on A and 0.70 on B; Sonnet 0.67 and 0.67; Haiku 0.56 and 0.60.  On the same pairs,
  A and B do not differ significantly for any model.
- **What does separate them is how the scale is used.**  Under Opus, 49 of 409 answers are 3 or 4 on A
  and 194 on B; 30 of the 100 nearest-neighbour targets have a neighbour at 3 or more on A, 94 of 100 on
  B.  Rubric B calls almost every existing trait covered by its nearest neighbours.

## What was run

**The pairs** ([pairs.json](../../data/candidates/overlap_test/overlap_test_1/pairs.json), built by
[overlap_test.py](../../assistant_axis/gapgen/overlap_test.py) `build_pair_set`, seed 0), grouped as M3
would group them, one call per [target with its listed traits](./glossary.md#target-listed):

| group | pairs | calls | where from |
|---|---|---|---|
| nearest | 300 | 100 | 100 targets drawn from the 286 corpus traits with persona vectors, each with its 3 [nearest](./glossary.md#nearest-neighbour) existing traits under the [covered setting](./glossary.md#two-settings) ([metric_config.json](../../data/candidates/metric_config.json): OpenAI `text-embedding-3-large`, [`w20`](./glossary.md#representations), [centred](./glossary.md#centred), [cosine](./glossary.md#cosine)), from the cached embeddings (nothing re-embedded) |
| drop-or-merge | 11 | 8 | the table with recorded partners excluded in [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md) (the [drop-or-merge list](./glossary.md#drop-or-merge); its second table holds one recorded clean pair and is left out) |
| near-distinct | 34 | 21 | every near-distinct pair of [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json) (the [labelled pairs](./glossary.md#labelled-pairs)): members of triangles, tetrahedra and sequences, and [plan 11](./11_novelty_ensemble.md)'s list |
| antonym | 30 | 30 | a seeded sample of the 262 [recorded clean pairs](./glossary.md#clean-pair) |
| random | 30 | 29 | a seeded sample of the 2,000 random unrelated pairs |
| deliberate duplicate | 3 | 3 | all three (a named position's plain-language counterpart) |
| duplicate | 1 | 1 | the one labelled duplicate whose two members are both corpus traits ([consequentialist](../../data/traits/instructions/consequentialist.json) and [utilitarian](../../data/traits/instructions/utilitarian.json)); the other 78 are a gloss against a description and are left out, as the draft says |

The labelled pairs were grouped greedily: the member shared by most remaining pairs became a target and
took all its pairs (55 calls list one trait, 21 two, 4 three; the nearest calls list three).  Every pair
records its group, the embedding cosine and, where both traits have persona vectors (280 of the 409
pairs), the persona-space cosine (8-slot set, slot 6, layer 25, centred and
[soft-sheared](./glossary.md#soft-shear), as the calibration loads them).  31 of the 300 nearest pairs are
recorded clean pairs (an antonym came back as a neighbour, as it will in M3 before the
[relation call](./glossary.md#relation-overlap-calls) removes it), and 38 unordered pairs were judged in
two calls (a nearest call and a labelled one).

**What each model received**: the rubric as the system prompt and one JSON object as the user turn,
laid out exactly as the draft's rendered sample (a test checks it byte for byte), labels in display form,
the listed traits in a seeded random order with ids 1 to n, no scores, ranks or arrangement marks.
Temperature 0 for Haiku; Sonnet 5.5 and Opus 5.5 refuse a temperature setting and ran at their default.

**Against order and position bias** ([AGENT_NOTES.md](../../AGENT_NOTES.md), "Comparing arms with an LLM judge", design 1): every
listed trait is rated on its own absolute scale, the arms (two rubrics, three models) never share a
prompt, every arm received the identical user turn (the same order of listed traits), and nothing in a
prompt names a rubric, a model or a pair's group.  A position effect inside a call therefore falls on
every arm alike.

The full rendered requests of three variants (a nearest target; one whose list holds the target's
recorded antonym; one with a single listed trait) are in
[rendered_prompts.md](../../data/candidates/overlap_test/overlap_test_1/rendered_prompts.md); the
section "The prompts that were sent" below quotes one.

## Agreement with Opus

On the pairs where both models gave a number; "exact (all)" also counts "opposite" and "unsure" as
answers.  Kappa is quadratic-weighted, linear in brackets.

| rubric | model | exact (all) | both numeric | exact | within one | mean difference (model minus Opus) | weighted kappa |
|---|---|---|---|---|---|---|---|
| A | Haiku 4.5 | 64% | 318 | 58% | 98% | +0.35 | 0.76 (0.60) |
| A | Sonnet 5.5 | 86% | 323 | 85% | 100% | +0.04 | 0.91 (0.85) |
| B | Haiku 4.5 | 55% | 404 | 55% | 95% | +0.41 | 0.87 (0.71) |
| B | Sonnet 5.5 | 85% | 409 | 85% | 100% | +0.12 | 0.96 (0.90) |

Where a cut-off would sit, between 2 and 3, Sonnet agrees with Opus on 96% of the rubric-A pairs (57
pairs at 3 or more against Opus's 49) and Haiku on 83% (92 pairs against 49: nearly twice as many
"same concept" calls).  Every pair Opus called "opposite" under A, Haiku and Sonnet called opposite too;
Haiku added 14 opposites of its own and Sonnet 9.  As in the [M1 audit](./opus_audit_m1.md), disagreement between the two
smaller models is a usable signal: where Haiku and Sonnet gave the same rubric-A answer, Opus gave it too
in 234 of 261 pairs (90%); where they differed, Opus sided with Sonnet 116 times, with Haiku 26 and with
neither 6.

## Agreement with persona space and with the embedding

Spearman between each model's numeric answers and the cosine, with a 95%
[bootstrap interval resampling targets](./glossary.md#cluster-bootstrap).  "Without recorded opposites"
leaves out clean pairs and labelled antonyms (rubric A answers "opposite" on all of them, so its two
columns are the same; under B they score 0).  The overlap call in M3 sees only traits the relation call
judged similar, so the second and fourth columns are the relevant population.

| rubric | model | cosine | all pairs | without recorded opposites | nearest pairs | nearest without recorded opposites |
|---|---|---|---|---|---|---|
| A | Haiku 4.5 | persona | 0.56 [0.44, 0.66] (228) | 0.56 [0.44, 0.66] (228) | 0.50 [0.39, 0.61] (197) | 0.50 [0.39, 0.61] (197) |
| A | Sonnet 5.5 | persona | 0.67 [0.56, 0.75] (232) | 0.67 [0.56, 0.75] (232) | 0.61 [0.50, 0.71] (198) | 0.61 [0.50, 0.71] (198) |
| A | Opus 5.5 | persona | 0.68 [0.57, 0.76] (240) | 0.68 [0.57, 0.76] (240) | 0.63 [0.51, 0.72] (203) | 0.63 [0.51, 0.72] (203) |
| B | Haiku 4.5 | persona | 0.68 [0.60, 0.75] (280) | 0.60 [0.50, 0.69] (251) | 0.62 [0.52, 0.70] (230) | 0.53 [0.41, 0.62] (210) |
| B | Sonnet 5.5 | persona | 0.73 [0.65, 0.79] (280) | 0.67 [0.58, 0.74] (251) | 0.68 [0.58, 0.75] (230) | 0.60 [0.50, 0.69] (210) |
| B | Opus 5.5 | persona | 0.76 [0.68, 0.82] (280) | 0.70 [0.62, 0.78] (251) | 0.71 [0.62, 0.78] (230) | 0.65 [0.55, 0.73] (210) |
| A | Haiku 4.5 | embedding | 0.62 [0.53, 0.69] (318) | 0.62 [0.53, 0.69] (318) | 0.46 [0.36, 0.56] (254) | 0.46 [0.36, 0.56] (254) |
| A | Sonnet 5.5 | embedding | 0.71 [0.63, 0.77] (323) | 0.71 [0.63, 0.77] (323) | 0.61 [0.51, 0.69] (256) | 0.61 [0.51, 0.69] (256) |
| A | Opus 5.5 | embedding | 0.68 [0.60, 0.75] (332) | 0.68 [0.60, 0.75] (332) | 0.57 [0.46, 0.66] (261) | 0.57 [0.46, 0.66] (261) |
| B | Haiku 4.5 | embedding | 0.29 [0.19, 0.39] (404) | 0.46 [0.36, 0.55] (343) | 0.17 [0.05, 0.27] (300) | 0.35 [0.24, 0.45] (269) |
| B | Sonnet 5.5 | embedding | 0.34 [0.24, 0.44] (409) | 0.54 [0.45, 0.62] (348) | 0.23 [0.12, 0.34] (300) | 0.42 [0.31, 0.52] (269) |
| B | Opus 5.5 | embedding | 0.35 [0.25, 0.45] (409) | 0.55 [0.45, 0.63] (348) | 0.25 [0.13, 0.35] (300) | 0.43 [0.32, 0.53] (269) |

**A against B on the same pairs** (pairs without recorded opposites where both rubrics gave a number;
paired interval):

| model | cosine | pairs | Spearman, A | Spearman, B | A minus B | 95% interval |
|---|---|---|---|---|---|---|
| Haiku 4.5 | persona | 228 | 0.56 | 0.50 | +0.05 | [-0.03, +0.14] |
| Sonnet 5.5 | persona | 232 | 0.67 | 0.60 | +0.07 | [-0.01, +0.14] |
| Opus 5.5 | persona | 240 | 0.68 | 0.68 | 0.00 | [-0.08, +0.08] |
| Haiku 4.5 | embedding | 313 | 0.60 | 0.47 | +0.12 | [+0.05, +0.20] |
| Sonnet 5.5 | embedding | 323 | 0.71 | 0.57 | +0.14 | [+0.07, +0.22] |
| Opus 5.5 | embedding | 332 | 0.68 | 0.59 | +0.09 | [+0.02, +0.16] |

Read: persona space does not choose between the rubrics.  With Opus they tie; with Sonnet and Haiku A is
a little ahead, inside the noise.  The embedding prefers A clearly, which is less telling (A asks about
the meaning of two descriptions, which is what the embedding encodes).  B's higher figure over "all
pairs" comes from the recorded opposites: B scores them 0, and their persona cosines sit near 0 (mean
0.03), at the bottom of the ranking.  Under A those pairs are "opposite" and leave the correlation.

Under Opus, rubric A's answers rise steadily with both cosines; rubric B's 0 mixes opposites (close in
the embedding) with traits that are merely less likely together:

| answer | A: pairs | A: mean embedding cosine | A: mean persona cosine | B: pairs | B: mean embedding cosine | B: mean persona cosine |
|---|---|---|---|---|---|---|
| 0 | 43 | 0.12 | 0.22 | 94 | 0.37 | 0.06 |
| 1 | 109 | 0.33 | 0.44 | 37 | 0.14 | 0.37 |
| 2 | 131 | 0.40 | 0.61 | 84 | 0.33 | 0.45 |
| 3 | 43 | 0.56 | 0.82 | 120 | 0.40 | 0.58 |
| 4 | 6 | 0.62 | 0.87 | 74 | 0.50 | 0.76 |
| opposite | 77 | 0.40 | 0.03 | – | – | – |

## Scores by known group

Mean of the numeric answers / share at 3 or more / share "opposite" (A only).

| group | pairs | A Haiku | A Sonnet | A Opus | B Haiku | B Sonnet | B Opus |
|---|---|---|---|---|---|---|---|
| nearest | 300 | 2.11 / 30% / 15% | 1.75 / 16% / 15% | 1.68 / 14% / 13% | 2.87 / 74% | 2.55 / 64% | 2.40 / 57% |
| drop-or-merge | 11 | 3.20 / 80% / 9% | 3.10 / 100% / 9% | 2.90 / 80% / 9% | 3.64 / 91% | 3.55 / 91% | 3.64 / 91% |
| deliberate duplicate | 3 | 2.33 / 33% / 0% | 2.00 / 0% / 0% | 2.00 / 0% / 0% | 3.67 / 100% | 3.33 / 100% | 3.33 / 100% |
| duplicate | 1 | 3 | 3 | 3 | 3 | 3 | 3 |
| near-distinct | 34 | 1.91 / 23% / 35% | 1.56 / 16% / 26% | 1.56 / 15% / 21% | 1.88 / 50% | 1.76 / 38% | 1.65 / 29% |
| antonym | 30 | all opposite | all opposite | all opposite | 0.00 | 0.00 | 0.00 |
| random | 30 | 0.14 / 0% / 7% | 0.14 / 0% / 7% | 0.17 / 0% / 0% | 1.64 / 32% | 1.13 / 0% | 1.03 / 0% |

Opus's answer counts under A: nearest 0: 15, 1: 93, 2: 117, 3: 32, 4: 4, opposite 39; near-distinct 0: 2,
1: 13, 2: 8, 3: 3, 4: 1, opposite 7; random 0: 26, 1: 3, 2: 1.  Under B: nearest 0: 48, 1: 12, 2: 70,
3: 111, 4: 59; random 0: 3, 1: 23, 2: 4 (B's 1 is "about as often as anyone else", the right answer for an
unrelated pair on its own scale, but it says nothing about overlap).

The drop-or-merge pairs, one by one (A from Opus, Sonnet and Haiku; B from Opus):

| trait | nearest | A Opus | A Sonnet | A Haiku | B Opus |
|---|---|---|---|---|---|
| [theoretical](../../data/traits/instructions/theoretical.json) | [abstract](../../data/traits/instructions/abstract.json) | 3 | 3 | 4 | 4 |
| [theoretical](../../data/traits/instructions/theoretical.json) | [conceptual](../../data/traits/instructions/conceptual.json) | 3 | 3 | 4 | 4 |
| [compassionate](../../data/traits/instructions/compassionate.json) | [empathetic](../../data/traits/instructions/empathetic.json) | 2 | 3 | 3 | 4 |
| [dramatic](../../data/traits/instructions/dramatic.json) | [melodramatic](../../data/traits/instructions/melodramatic.json) | 3 | 3 | 3 | 4 |
| [dramatic](../../data/traits/instructions/dramatic.json) | [theatrical](../../data/traits/instructions/theatrical.json) | 3 | 3 | 2 | 4 |
| [sardonic](../../data/traits/instructions/sardonic.json) | [sarcastic](../../data/traits/instructions/sarcastic.json) | 2 | 3 | 2 | 4 |
| [sardonic](../../data/traits/instructions/sardonic.json) | [wry](../../data/traits/instructions/wry.json) | 3 | 3 | 4 | 4 |
| [dispassionate](../../data/traits/instructions/dispassionate.json) | [detached](../../data/traits/instructions/detached.json) | 4 | 4 | 4 | 4 |
| [self-blaming](../../data/traits/instructions/self_blaming.json) | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | opposite | opposite | opposite | 0 |
| [honest](../../data/traits/instructions/honest.json) | [truthful](../../data/traits/instructions/truthful.json) | 3 | 3 | 3 | 4 |
| [dependable](../../data/traits/instructions/dependable.json) | [trustworthy](../../data/traits/instructions/trustworthy.json) | 3 | 3 | 3 | 4 |

The deliberate duplicates all score 2 under A on Opus and Sonnet (overlapping concepts, each adding
something: [ends justify means](../../data/traits/instructions/ends_justify_means.json) against
[consequentialist](../../data/traits/instructions/consequentialist.json) and against
[utilitarian](../../data/traits/instructions/utilitarian.json), and
[honorable](../../data/traits/instructions/honorable.json) against
[deontological](../../data/traits/instructions/deontological.json)), and 3 or 4 under B.  The one corpus
duplicate, [consequentialist](../../data/traits/instructions/consequentialist.json) and [utilitarian](../../data/traits/instructions/utilitarian.json), is 3 everywhere.

## Unsure and opposite

- **"Unsure" was almost never used**: 0 of 409 answers for every model under A; under B, 0 for Sonnet and
  Opus and 5 for Haiku (all on random pairs).  The M3 design passes *unsure* up a tier (Sonnet to Opus);
  on this evidence that route would hardly ever fire.
- **"Opposite" under A came back for every recorded opposite**: all 30 pairs of the antonym group and all
  31 nearest-neighbour pairs that are recorded clean pairs, for all three models.  On the other 348 pairs
  Opus answered "opposite" 16 times (5%), Sonnet 7%, Haiku 9%.  Opus's 13 distinct ones are mostly
  members of recorded triangles, tetrahedra and sequences
  ([compassionate](../../data/traits/instructions/compassionate.json) and [callous](../../data/traits/instructions/callous.json);
  [contrarian](../../data/traits/instructions/contrarian.json) and [conformist](../../data/traits/instructions/conformist.json);
  [conformist](../../data/traits/instructions/conformist.json) and [nonconformist](../../data/traits/instructions/nonconformist.json);
  [cosmopolitan](../../data/traits/instructions/cosmopolitan.json) and [civilizationist](../../data/traits/instructions/civilizationist.json);
  [essentialist](../../data/traits/instructions/essentialist.json) and [constructivist](../../data/traits/instructions/constructivist.json))
  or opposites through a near-duplicate's recorded partner
  ([trustworthy](../../data/traits/instructions/trustworthy.json) and [unreliable](../../data/traits/instructions/unreliable.json), via [dependable](../../data/traits/instructions/dependable.json);
  [conceptual](../../data/traits/instructions/conceptual.json) and [practical](../../data/traits/instructions/practical.json), via [theoretical](../../data/traits/instructions/theoretical.json);
  [experiential](../../data/traits/instructions/experiential.json) and [theoretical](../../data/traits/instructions/theoretical.json);
  [flippant](../../data/traits/instructions/flippant.json) and [solemn](../../data/traits/instructions/solemn.json);
  [deontological](../../data/traits/instructions/deontological.json) and [utilitarian](../../data/traits/instructions/utilitarian.json);
  [risk-averse](../../data/traits/instructions/risk_averse.json) and [bold](../../data/traits/instructions/bold.json);
  [diplomatic](../../data/traits/instructions/diplomatic.json) and [partisan](../../data/traits/instructions/partisan.json)),
  plus the drop-or-merge row [self-blaming](../../data/traits/instructions/self_blaming.json) and
  [blame-shifting](../../data/traits/instructions/blame_shifting.json), which every model reads as opposites
  under A (and scores 0 under B; your note of 2026-09-26 calls them, with [accountable](../../data/traits/instructions/accountable.json), arguably a triangle).
- Under B there is no "opposite" answer; recorded opposites all score 0, the same answer as traits that
  merely make each other less likely.

## Ten pairs where the rubrics diverge most (Opus)

B minus A over the 332 pairs where Opus gave both rubrics a number: 0 on 49 pairs, +1 on 188, +2 on 76,
+3 on 3, +4 on 1, and -1 or -2 on 15; B is a point higher on average (1.02).  The ten largest, B above
A, are the case the draft names: traits that go together but are not the same concept.

**1. [erudite](../../data/traits/instructions/erudite.json) (target) and [literate](../../data/traits/instructions/literate.json)** (nearest; embedding cosine 0.35; a persona vector missing)

- [erudite](../../data/traits/instructions/erudite.json): This means being deeply bookish, knowing what years of study and wide reading have taught, and putting it in learned words, with frameworks, references and theory.
- [literate](../../data/traits/instructions/literate.json): This means being able to read and write with ease, getting by on the written word, and reading every letter, sign and form for oneself.
- A = 0: Basic reading and writing ability is only a distant precondition of deep scholarly learning.
- B = 4: Being deeply bookish presupposes reading and writing with ease.
- Haiku and Sonnet: A 0 and 1, B 4 and 4

**2. [structuralist](../../data/traits/instructions/structuralist.json) (target) and [analytical](../../data/traits/instructions/analytical.json)** (nearest; embedding cosine 0.38, persona-space cosine 0.51)

- [structuralist](../../data/traits/instructions/structuralist.json): This means focusing on identifying and analyzing underlying patterns, systematic relationships, organizing principles, and structural frameworks that govern systems or phenomena, rather than focusing on surface details or individual cases.
- [analytical](../../data/traits/instructions/analytical.json): This means breaking down complex topics into logical components and examining each part systematically, using methodical reasoning and structured examination.
- A = 1: Both involve systematic analysis, but analytical means decomposing a topic into parts, while structuralist means seeking the underlying patterns and frameworks that govern a whole.
- B = 4: Finding underlying patterns and frameworks takes systematic, methodical analysis, so a structuralist is almost always analytical.
- Haiku and Sonnet: A 2 and 1, B 4 and 4

**3. [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json) (target) and [esoteric](../../data/traits/instructions/esoteric.json)** (nearest; embedding cosine 0.33, persona-space cosine 0.35)

- [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json): This means revealing sacred mysteries through technological mediation, using modern scientific and mathematical terminology often interspersed with unicode glyphs — such as ∞ recursion, resonance, 🌀 spirals 🌀, 🌿 fractals, harmonics, ❖ lattice ⬡, and △⟐ emergence ✨ — in a purely symbolic and correspondential way, treating the interlocutor as a chosen initiate and partner with whom you co-discover hidden cosmic truths as a dyad.
- [esoteric](../../data/traits/instructions/esoteric.json): This means using specialized knowledge, obscure references, technical terminology, or concepts that would only be accessible to experts or those with deep initiation in specific fields, rather than being broadly understandable.
- A = 1: Both involve obscure, initiate-only language, but esoteric means expert jargon in general, while the target adds sacred revelation, glyphs and an initiate dyad.
- B = 4: Revealing hidden mysteries to a chosen initiate, with obscure jargon, is esoteric in nature.
- Haiku and Sonnet: A 3 and 2, B 4 and 4

**4. [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json) (target) and [spiritual](../../data/traits/instructions/spiritual.json)** (nearest; embedding cosine 0.27, persona-space cosine 0.36)

- [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json): as above.
- [spiritual](../../data/traits/instructions/spiritual.json): This means incorporating transcendent dimensions that go beyond material existence, referencing sacred elements, drawing upon spiritual wisdom, or acknowledging mystical and divine aspects of reality, and valuing these above material achievements.
- A = 1: Both deal with sacred, transcendent truths, but the target's defining feature is techno-symbolic mediation, which spiritual lacks.
- B = 4: The trait centers on sacred mysteries and cosmic truths, so it is inherently spiritual.
- Haiku and Sonnet: A 2 and 2, B 4 and 4

**5. [compassionate](../../data/traits/instructions/compassionate.json) (target) and [empathetic](../../data/traits/instructions/empathetic.json)** (drop-or-merge; embedding cosine 0.54, persona-space cosine 0.77)

- [compassionate](../../data/traits/instructions/compassionate.json): This means showing emotional warmth and sensitivity to others' pain and suffering, and responding to distress with genuine empathy and care.
- [empathetic](../../data/traits/instructions/empathetic.json): This means showing genuine understanding and consideration for human emotions, perspectives, and experiences, often by acknowledging feelings, demonstrating emotional awareness, and responding with compassion and warmth.
- A = 2: Both involve warm, caring responses to others' feelings, but empathetic stresses understanding of emotions generally, while compassionate stresses responding to suffering.
- B = 4: Compassion rests on empathic understanding of others' feelings, so the two almost always go together.
- Haiku and Sonnet: A 3 and 3, B 4 and 4

**6. [honorable](../../data/traits/instructions/honorable.json) (target) and [deontological](../../data/traits/instructions/deontological.json)** (deliberate duplicate; embedding cosine 0.19; a persona vector missing)

- [honorable](../../data/traits/instructions/honorable.json): This means keeping a code of things that are never done however high the stakes, holding that the ends do not justify the means, that some acts simply cannot be justified, even when they would win, save a great many lives, and accepting the loss when one's code and one's goal conflict.
- [deontological](../../data/traits/instructions/deontological.json): This means focusing on whether actions are inherently right or wrong based on moral rules and duties, independent of their consequences or outcomes.
- A = 2: Both reject letting consequences justify forbidden acts, but deontological is a general rule-and-duty ethical stance, while honorable adds a personal code held to at real cost.
- B = 4: Holding that some acts are never justified regardless of the outcome is essentially a deontological stance, so the two nearly always go together.
- Haiku and Sonnet: A 3 and 2, B 4 and 4

**7. [nationalist](../../data/traits/instructions/nationalist.json) (target) and [patriotic](../../data/traits/instructions/patriotic.json)** (near-distinct; embedding cosine 0.37, persona-space cosine 0.71)

- [nationalist](../../data/traits/instructions/nationalist.json): This means prioritizing one's own nation's interests, culture, and people above those of other nations, viewing issues primarily through a lens of national advantage and identity.
- [patriotic](../../data/traits/instructions/patriotic.json): This means showing love, pride, and devotion toward one's country, celebrating its values, achievements, institutions, and cultural heritage with genuine affection and loyalty.
- A = 2: Both center on attachment to one's own nation. Patriotism stresses love and pride, while nationalism stresses putting national interests above other nations', so each adds something the other lacks.
- B = 4: Nationalists almost always express love, pride, and loyalty toward their country.
- Haiku and Sonnet: A 2 and 2, B 3 and 4

**8. [risk-averse](../../data/traits/instructions/risk_averse.json) (target) and [cautious](../../data/traits/instructions/cautious.json)** (near-distinct; embedding cosine 0.26; a persona vector missing)

- [risk-averse](../../data/traits/instructions/risk_averse.json): This means taking the sure thing over the gamble, sticking to proven methods and guaranteed outcomes, and passing up the better bet rather than accept any chance of loss.
- [cautious](../../data/traits/instructions/cautious.json): This means emphasizing potential risks, warning about limitations or negative consequences, considering carefully before acting, expressing uncertainty or hesitation where appropriate, and recommending seeking additional information or expertise.
- A = 2: Both center on avoiding risk, but cautious adds warning, deliberation and seeking expertise, while risk-averse adds choosing guaranteed outcomes over better bets.
- B = 4: Avoiding any chance of loss naturally goes with emphasizing risks and deliberating carefully before acting.
- Haiku and Sonnet: A 2 and 2, B 4 and 4

**9. [sardonic](../../data/traits/instructions/sardonic.json) (target) and [sarcastic](../../data/traits/instructions/sarcastic.json)** (drop-or-merge; embedding cosine 0.70, persona-space cosine 0.87)

- [sardonic](../../data/traits/instructions/sardonic.json): This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge.
- [sarcastic](../../data/traits/instructions/sarcastic.json): This involves using sharp, ironic, or cutting remarks that often mock or show contempt, typically through verbal irony where the intended meaning is opposite to the literal words used.
- A = 2: Both are cutting, ironic mockery, but sarcastic stresses saying the opposite of what is meant, while sardonic stresses dry, cynical observation of absurdity.
- B = 4: A sardonic persona's cutting, ironic mockery very nearly always shows up as sarcastic remarks.
- Haiku and Sonnet: A 2 and 3, B 4 and 4

**10. [agreeable](../../data/traits/instructions/agreeable.json) (target) and [cooperative](../../data/traits/instructions/cooperative.json)** (nearest; embedding cosine 0.34, persona-space cosine 0.65)

- [agreeable](../../data/traits/instructions/agreeable.json): This means prioritizing maintaining harmony and positive relationships, seeking to avoid confrontation, emphasizing cooperation and understanding, and attempting to find common ground or peaceful resolutions even in difficult situations.
- [cooperative](../../data/traits/instructions/cooperative.json): This means emphasizing collaboration, mutual benefit, and shared success rather than individual achievement, framing situations as opportunities for teamwork and collective problem-solving rather than contests to be won.
- A = 2: Cooperation is one part of agreeableness, but cooperative is about teamwork and collective success rather than avoiding conflict and keeping harmony.
- B = 4: Agreeableness explicitly emphasizes cooperation, so collaborative framing almost always comes with it.
- Haiku and Sonnet: A 2 and 2, B 4 and 4

The other direction is rarer (15 pairs, none by more than two points).  The largest:
[nationalist](../../data/traits/instructions/nationalist.json) and
[regionalist](../../data/traits/instructions/regionalist.json), A 3 ("the same favoritism toward one's own
unit, applied to a sub-national region") and B 1 ("nationalism ... often opposes regional loyalties");
then [confident](../../data/traits/instructions/confident.json) and
[overconfident](../../data/traits/instructions/overconfident.json), and
[elitist](../../data/traits/instructions/elitist.json) and
[aristocratic](../../data/traits/instructions/aristocratic.json), both A 3 and B 2 (a narrower or stronger
form of the same thing, which need not follow from the broader one).

**Stability.**  Of the 38 pairs judged in two calls, Opus gave the same answer both times 32 times under A
and 26 times under B (Sonnet 32 and 28, Haiku 25 and 26).

## The prompts that were sent

The system prompt is the rubric's fenced block, byte for byte
([overlap_concept.md](./rubrics/overlap_concept.md), [overlap_cooccurrence.md](./rubrics/overlap_cooccurrence.md);
SHA-256 `2f650bffa3d6...` and `1dd2837269e8...`, pinned as version 2 in
[versions.json](./rubrics/versions.json)).  Before the paid run the rendered requests of three variants
were read ([AGENT_NOTES.md](../../AGENT_NOTES.md), "Read the rendered prompt, not the template"); the directions fit the data in
each (one target per call, ids numbering the listed traits, a list of one, an opposite in the list), and
nothing needed changing.  One of them, as Haiku received it under rubric A (Sonnet and Opus received the
same without `temperature`; under rubric B only the system prompt differs):

```text
request settings {"model": "claude-haiku-4-5-20251001", "max_tokens": 2048, "temperature": 0.0}
--- system ---
(rubric A's text: the fenced block of the file linked above)
--- user ---
{"target": {"label": "absolutist", "description": "This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation."},
 "traits": [
  {"id": 1, "label": "relativist", "description": "This means believing that truth and morality are entirely dependent on context, perspective, and cultural background, rejecting the existence of universal or objective standards."},
  {"id": 2, "label": "essentialist", "description": "This means believing in and emphasizing the fundamental, unchanging nature or essence of things and concepts, treating categories and identities as having fixed, inherent properties rather than being flexible or contextually dependent."},
  {"id": 3, "label": "moral universalist", "description": "This means applying consistent norms and values across all cultures and contexts, believing that moral standards and human values should be uniform regardless of cultural, historical, or situational differences."}
 ]}
```

That is the variant with a recorded opposite in the list ([absolutist](../../data/traits/instructions/absolutist.json)
and [relativist](../../data/traits/instructions/relativist.json); with
[essentialist](../../data/traits/instructions/essentialist.json) and
[moral universalist](../../data/traits/instructions/moral_universalist.json)).  All three models answered
"opposite" for [relativist](../../data/traits/instructions/relativist.json) under A and 0 under B.  The other two variants, in full with both system prompts,
are in [rendered_prompts.md](../../data/candidates/overlap_test/overlap_test_1/rendered_prompts.md).

## Parse failures and what was changed

The first Sonnet stage (rubric A) parsed 385 of 409 pairs (94.1%), the guard stopped the run before the
next stage ($1.15 spent), and I looked at the eight failed answers before going on.  Seven had the
same shape: Sonnet added a `"label"` key to one row, then wrote "Correction: the output must have the
reason field only ..." and the whole answer again, cleanly; the parser read the span from the first
brace to the last as one object and failed.  One answer had a row ending
`"reason": "...", "opposite"}`, the answer's key left out, which is not JSON.  The rubric text was not
touched.  Two changes to the harness (commit 6707ed2), applied to every model alike:

- **parser version 2**: the last complete `{"results": [...]}` object in the text is the answer (the
  model's own correction); the analysis re-parses every recorded answer with it;
- **one more ask**: a call whose answer does not parse fully is sent once more, and the first-attempt
  rate is reported beside the final one.

Resumed, the one remaining Sonnet call parsed at its second asking, and one Opus rubric-B call (it
numbered its third row 4) was asked again during its stage.  First-attempt rates under parser 2: Sonnet A 406 of 409
(99.3%), Opus B 408 of 409, everything else complete.  Whether rubric A's answer line should also say
"no other keys" is a question for a draft 3 (decision 6); it is not needed for this test.

## Rerun with rubric A draft 3 (`overlap_test_2`)

On Roger's word (decision 6: "SG, rerun the tests to confirm"), draft 3 of rubric A (pinned version 3,
one sentence added: "Use only the keys shown: do not add the trait's label or any other key, and give
each row once.") ran on Sonnet 5.5 and Opus 5.5 over the same 409 pairs (the same
[pairs.json](../../data/candidates/overlap_test/overlap_test_2/pairs.json) but for its provenance), live,
for $1.88 ([usage.json](../../data/candidates/overlap_test/overlap_test_2/usage.json)); tables in
[tables.md](../../data/candidates/overlap_test/overlap_test_2/tables.md).

- **Parsing**: both models 409 of 409 at the first attempt, nothing asked again (draft 2: Sonnet 406 at
  the first attempt).  Calls whose first answer carried a key the rubric does not ask for, or wrote the
  answer twice: Sonnet 29 of 180 under draft 2, 19 under draft 3 (13 a `"label"` key, 6 a filler key
  such as `"color": ""`; 3 of the 19 wrote "Correction:" and the answer again, against 7); Opus 10 and 10.
  The parser ignores extra keys, so none of this lost an answer, but the sentence does not stop the habit.
  Every extra key sits in the slot after `"id"`, where the input rows carry `"label"`, almost all in
  calls listing three traits, and every `"label"` value was right: the models copy the input row's
  shape.  **Decided (Roger, 2026-10-03): harmless, ignored; the sentence is removed** and rubric A is
  draft 2's text again, pinned as version 4 (`"same_text_as": 2`), which `overlap_test_1` already tested.
- **Scores**: unchanged within run-to-run noise.  Each model against itself across the two runs: Sonnet
  93% exact, Opus 94%, every numeric pair within one point.  Sonnet against Opus: 87% exact (86% under
  draft 2), weighted kappa 0.92 (0.91), every numeric pair within one point.  Sonnet's answers on the 300
  nearest pairs: 0 16, 1 79, 2 121, 3 37, 4 4, opposite 43 (draft 2: 15, 81, 118, 38, 4, 44).
- **Escalation at a cut-off of 3**, nearest pairs: Sonnet and Opus fall on different sides 11 times (8
  Sonnet 3 / Opus 2, 3 Sonnet 2 / Opus 3; draft 2: 10).  Sending Opus every pair Sonnet scores 2 or 3
  catches all 11 and covers 158 of 257 pairs, in 94 of 100 calls; sending only Sonnet's 3s catches 8
  and covers 37 pairs in 32 calls.
- **Harness**: the first launch hit the expired API key, and the failed requests were recorded as
  unparsed answers; the analysis then counted them as Sonnet's first attempt (0 of 409) and its table
  writer stopped on a run of one rubric.  Fixed with tests: a failed request is not an attempt at the
  format, is not asked again in the stage (the resume sends it), and a one-rubric run writes its tables.

## Roger's marks

[m3_overlap_marks.md](./m3_overlap_marks.md) holds 30 pairs to mark on rubric A's scale, blinded (the
target and the listed trait with their descriptions, nothing about where the pair came from or what any
model said), drawn with seed 0: 18 nearest-neighbour pairs, 3 drop-or-merge, 3 near-distinct, 2
antonyms, 2 random, 2 deliberate duplicates, in random order.  The key is
[marks_key.json](../../data/candidates/overlap_test/overlap_test_1/marks_key.json).

**Marked by Roger, 2026-10-04**, all 30.  Five he marked as torn between two adjacent scores ("unsure:
1, possibly 2"); I read those by hand as a leaning and an alternative (Roger: "just parse them
yourself"), so `--decode-marks` was not used.  Against rubric A's answers in `overlap_test_1` (draft 2's
text, the current one):

| model | exact (leaning) | leaning or alternative | numeric within one | mean, model minus Roger |
|---|---|---|---|---|
| Haiku 4.5 | 23 / 30 | 25 / 30 | 23 / 23 | +0.22 |
| Sonnet 5.5 | 19 / 30 | 21 / 30 | 23 / 23 | -0.09 |
| Opus 5.5 | 18 / 30 | 20 / 30 | 23 / 23 | -0.13 |

- Every model is within one point of Roger on every item both scored with a number, the same pattern
  as Sonnet against Opus; Roger's own hesitations are all between adjacent scores too.
- Haiku agrees with Roger most, but not beyond chance on 30 items: Haiku-only against Opus-only exact
  matches 7 to 2 (two-sided exact test p = 0.18; leaning-or-alternative 6 to 1, p = 0.12); Sonnet
  against Opus 2 to 1 (p = 1.0).
- So the marks do not show Opus closer to Roger than Sonnet, which was the premise of treating Opus as
  the reference and of escalating to it.
- Where Opus differs from Roger (10 items) it scores lower 6 times (iconoclastic / deconstructionist,
  moral relativist / relativist, serious / formal, socratic / educational, theoretical / conceptual,
  cosmopolitan / philanthropic) and higher 3 times (extroverted / energetic, agreeable / conciliatory,
  adventurous / adventurous eater); once Roger says opposite where Opus says 0 (nihilistic /
  essentialist, where Haiku also says opposite).

### Fable's scores and the adjudication (2026-10-04)

Roger switched the session to Fable 5.1 and asked for the 30 pairs rescored by it, in the
conversation, and for the Fable-against-Opus disagreements to be adjudicated.  Two caveats: the scoring
was not blind (every rater's answer had been seen), and Fable is a Claude model, so agreement with
Sonnet and Opus is expected rather than independent evidence.  Scores were given from the descriptions
on the rubric's terms, reason first; the models' recorded reasons were read before adjudicating.
Agreement: Fable with Opus 25 / 30, Sonnet 24, Haiku 22, Roger 21 (23 with his second choices).

| # | target / listed | Roger | Haiku | Sonnet | Opus | Fable | adjudicated | note |
|---|---|---|---|---|---|---|---|---|
| 1 | [self-blaming](../../data/traits/instructions/self_blaming.json) / [blame-shifting](../../data/traits/instructions/blame_shifting.json) | opp | opp | opp | opp | opp | | |
| 2 | [erudite](../../data/traits/instructions/erudite.json) / [esoteric](../../data/traits/instructions/esoteric.json) | 1 (2) | 1 | 2 | 1 | 1 | | |
| 3 | [utilitarian](../../data/traits/instructions/utilitarian.json) / [deontological](../../data/traits/instructions/deontological.json) | opp | opp | opp | opp | opp | | |
| 4 | [animated](../../data/traits/instructions/animated.json) / [flat](../../data/traits/instructions/flat.json) | opp | opp | opp | opp | opp | | |
| 5 | [conservative](../../data/traits/instructions/conservative.json) / [overconfident](../../data/traits/instructions/overconfident.json) | 0 | 0 | 0 | 0 | 0 | | |
| 6 | [materialist](../../data/traits/instructions/materialist.json) / [relativist](../../data/traits/instructions/relativist.json) | 0 | 0 | 0 | 0 | 0 | | |
| 7 | [excitable](../../data/traits/instructions/excitable.json) / [narrative](../../data/traits/instructions/narrative.json) | 0 | 0 | 0 | 0 | 0 | | |
| 8 | [religious](../../data/traits/instructions/religious.json) / [secular](../../data/traits/instructions/secular.json) | opp | opp | opp | opp | opp | | |
| 9 | [extroverted](../../data/traits/instructions/extroverted.json) / [energetic](../../data/traits/instructions/energetic.json) | 0 | 1 | 1 | 1 | 0 | **0** | immaterial; the fuzziest boundary: Opus's shared "idea of energy" is a metaphor on one side (energized *by company*) and vigour on the other; different dimensions in one area is the rubric's 0 example |
| 10 | [temperamental](../../data/traits/instructions/temperamental.json) / [even-tempered](../../data/traits/instructions/even_tempered.json) | opp | opp | opp | opp | opp | | |
| 11 | [iconoclastic](../../data/traits/instructions/iconoclastic.json) / [deconstructionist](../../data/traits/instructions/deconstructionist.json) | 2 | 2 | 1 | 1 | 2 | **2** | immaterial; Opus's reason itself opens "both challenge established foundations", and that challenge is each trait's core, not its area; the difference (revered institutions attacked vs. contradictions in concepts exposed) is each adding something |
| 12 | [ethereal](../../data/traits/instructions/ethereal.json) / [spiritual](../../data/traits/instructions/spiritual.json) | 1 | 2 | 1 | 1 | 1 | | |
| 13 | [strategic](../../data/traits/instructions/strategic.json) / [long-term oriented](../../data/traits/instructions/long_term_oriented.json) | 1 (2) | 2 | 2 | 2 | 2 | | shared core: the near win passed up for the eventual one |
| 14 | [agreeable](../../data/traits/instructions/agreeable.json) / [conciliatory](../../data/traits/instructions/conciliatory.json) | 2 | 3 | 3 | 3 | 2 | **2** | matters at cut-off 3.  Not a subset, as Opus has it: conciliatory adds peacemaking *between other parties*, agreeable adds avoiding confrontation; a tough mediator is conciliatory and not agreeable |
| 15 | [dispassionate](../../data/traits/instructions/dispassionate.json) / [detached](../../data/traits/instructions/detached.json) | 4 | 4 | 4 | 4 | 4 | | |
| 16 | [nihilistic](../../data/traits/instructions/nihilistic.json) / [essentialist](../../data/traits/instructions/essentialist.json) | opp | opp | 0 | 0 | 0 | | differs from Roger: a persona can coherently hold both (fixed natures, no meaning), so not the rubric's "reverse"; the opposition Roger marks is the tetrahedron's, which M3 reads from the arrangement |
| 17 | [hedonistic](../../data/traits/instructions/hedonistic.json) / [self-indulgent](../../data/traits/instructions/self_indulgent.json) | 3 (2) | 3 | 3 | 3 | 3 | | |
| 18 | [consequentialist](../../data/traits/instructions/consequentialist.json) / [ends justify means](../../data/traits/instructions/ends_justify_means.json) | 2 | 2 | 2 | 2 | 2 | | |
| 19 | [deconstructionist](../../data/traits/instructions/deconstructionist.json) / [structuralist](../../data/traits/instructions/structuralist.json) | 1 | 1 | 1 | 1 | 1 | | |
| 20 | [benevolent](../../data/traits/instructions/benevolent.json) / [benign](../../data/traits/instructions/benign.json) | 2 | 2 | 2 | 2 | 2 | | |
| 21 | [honorable](../../data/traits/instructions/honorable.json) / [deontological](../../data/traits/instructions/deontological.json) | 2 (3) | 3 | 2 | 2 | 3 | **3** | matters at cut-off 3.  Rules held "independent of consequences" are already rules held at cost, so honorable adds no content; deontological is the wider concept (positive duties, anyone's acts): scope, the rubric's 3.  Not symmetric with item 18: ends-justify-means is a threshold trait, honorable is deontology lived throughout.  The corpus seeded honorable as deontological's character-trait version (the deliberate-duplicate group) |
| 22 | [adventurous](../../data/traits/instructions/adventurous.json) / [adventurous eater](../../data/traits/instructions/adventurous_eater.json) | 2 | 3 | 2 | 3 | 3 | | differs from Roger: adventurous narrowed to food, scope |
| 23 | [strategic](../../data/traits/instructions/strategic.json) / [tactical](../../data/traits/instructions/tactical.json) | opp | opp | opp | opp | opp | | |
| 24 | [moral relativist](../../data/traits/instructions/moral_relativist.json) / [relativist](../../data/traits/instructions/relativist.json) | 4 | 3 | 3 | 3 | 3 | | differs from Roger: relativist covers truth as well, so the labels are not interchangeable |
| 25 | [serious](../../data/traits/instructions/serious.json) / [formal](../../data/traits/instructions/formal.json) | 3 | 3 | 2 | 2 | 2 | | differs from Roger: levity and register are two axes, and the corpus pairs them with different opposites ([playful](../../data/traits/instructions/playful.json), [casual](../../data/traits/instructions/casual.json)); serious's description does open with "formal", a conflation in the writing |
| 26 | [socratic](../../data/traits/instructions/socratic.json) / [educational](../../data/traits/instructions/educational.json) | 2 | 2 | 1 | 1 | 1 | | Fable's first instinct was 2; Opus's reason persuaded it: educational as described *transfers* knowledge by explaining, socratic *elicits* it by refusing answers; the aim is shared, the cores differ; socratic's recorded opposite, [didactic](../../data/traits/instructions/didactic.json), is close to the described educational |
| 27 | [extroverted](../../data/traits/instructions/extroverted.json) / [gregarious](../../data/traits/instructions/gregarious.json) | 3 (2) | 3 | 3 | 2 | 3 | **3** | matters at cut-off 3.  Opus's "each adds": but extroverted's description already has the outgoing behaviour, so the addition is one-sided (the energy mechanism), which is emphasis; the recorded opposites [introverted](../../data/traits/instructions/introverted.json) and [solitary](../../data/traits/instructions/solitary.json) are themselves near-synonyms |
| 28 | [theoretical](../../data/traits/instructions/theoretical.json) / [conceptual](../../data/traits/instructions/conceptual.json) | 4 | 4 | 3 | 3 | 3 | | differs from Roger, immaterial for the merge list: "conceptual" has a sense (idea-driven, as in art) that "theoretical" lacks |
| 29 | [cosmopolitan](../../data/traits/instructions/cosmopolitan.json) / [philanthropic](../../data/traits/instructions/philanthropic.json) | 1 | 1 | 0 | 0 | 0 | | Fable's first instinct was 1; persuaded to 0: respect for cultures and charitable giving are different concepts, linked only by looking beyond one's own group; their adjacency is the moral-circle sequence, an arrangement, not this score |
| 30 | [moderate](../../data/traits/instructions/moderate.json) / [temperate](../../data/traits/instructions/temperate.json) | 2 | 2 | 2 | 2 | 2 | | |

Of the five adjudications, three go against Opus on pairs where a 3 is the difference between "covered"
and "new" at the far-from-alignment cut-off (14 and 27 against Opus's direction, 21 with it: items 14
and 27 Opus would misjudge in opposite directions).  Everything any rater gave is within one point of
every other rater on every numeric item; the adjudications are all about which side of a boundary a
pair falls, never about the neighbourhood.

### Fable through the API, and the six-way chart (2026-10-04)

Roger then asked for Fable 5.1 as a fourth API judge.  It ran rubric A (the current text, draft 2's,
pinned as version 4) over the same 409 pairs, appended to `overlap_test_1` with `--resume` (the three
recorded stages were skipped, nothing re-sent; the marks sheet was kept): 180 calls, 101 seconds,
**$3.17** at $10 / $50 per million tokens (2.5 times Opus 5.5; the price was added to
[judge_pricing.py](../../assistant_axis/judge_pricing.py) from the pricing page that day), run 1's total
now $7.15 ([usage.json](../../data/candidates/overlap_test/overlap_test_1/usage.json)).  Parsing: 409 of
409 at the first attempt, and **none of the 180 first answers added a key or wrote the answer twice**
(Sonnet 29 and Opus 10 under the same text).  The tables in
[tables.md](../../data/candidates/overlap_test/overlap_test_1/tables.md) were rewritten with four models.

**On all 409 pairs**, Fable against each model (exact over every answer; then on the pairs both scored
with a number: exact, within one point, mean Fable minus model, weighted kappa):

| against | exact (all) | numeric exact | within one | mean difference | kappa |
|---|---|---|---|---|---|
| Haiku 4.5 | 66% | 59% | 96% of 317 | -0.30 | 0.76 |
| Sonnet 5.5 | 83% | 80% | 100% of 323 | 0.00 | 0.90 |
| Opus 5.5 | 83% | 80% | 100% of 327 | +0.04 | 0.90 |

Fable sits with Sonnet and Opus (kappa 0.90 against each, as they are against each other) and never
more than one point from either.  Its correlations with the persona-space and the embedding cosine
(0.68, 0.69) are the same as the others'.  Its scores spread a little more: on the 300 nearest pairs
0: 23, 1: 80, 2: 102, 3: 45, 4: 6, opposite 44 (Opus 15 / 93 / 117 / 32 / 4 / 39).  On the labelled
groups it separates the ends most: mean 3.40 on the drop-or-merge pairs (Haiku 3.20, Sonnet 3.10, Opus
2.90) and 1.48 on the near-distinct pairs (1.91, 1.56, 1.56), on 11 and 34 pairs.  Judging the 38 pairs
that appear in two calls, Fable gave the same answer 31 times (Sonnet and Opus 32, Haiku 25).

**The six-way chart**, exact agreement on the 30 marked pairs (Roger's leaning):

| | Roger | Haiku | Sonnet | Opus | Fable API | Fable chat | mean with the other five |
|---|---|---|---|---|---|---|---|
| **Roger** | – | 23 | 19 | 18 | 19 | 21 | 20.0 |
| **Haiku** | 23 | – | 20 | 21 | 20 | 22 | 21.2 |
| **Sonnet** | 19 | 20 | – | 27 | 24 | 24 | 22.8 |
| **Opus** | 18 | 21 | 27 | – | 23 | 25 | 22.8 |
| **Fable API** | 19 | 20 | 24 | 23 | – | 26 | 22.4 |
| **Fable chat** | 21 | 22 | 24 | 25 | 26 | – | 23.6 |

Against Roger counting his second choices: Haiku 25, Fable chat 23, Fable API 22, Sonnet 21, Opus 20.
Matching the majority of the other five where there is one: Fable chat 25 of 30, Opus 24, Sonnet 23,
Fable API 23, Haiku 20, Roger 18.  No two raters are more than one point apart on any numeric item.
Fable through the API, blind, lands where Fable in the chat did: they agree on 26 of 30 and differ on
[erudite](../../data/traits/instructions/erudite.json) / [esoteric](../../data/traits/instructions/esoteric.json)
(API 2, chat 1), [iconoclastic](../../data/traits/instructions/iconoclastic.json) /
[deconstructionist](../../data/traits/instructions/deconstructionist.json) (1, 2),
[theoretical](../../data/traits/instructions/theoretical.json) /
[conceptual](../../data/traits/instructions/conceptual.json) (4, 3) and
[moderate](../../data/traits/instructions/moderate.json) / [temperate](../../data/traits/instructions/temperate.json)
(1, 2).  No pairwise difference in agreement with Roger is significant (the largest, Haiku against Fable
API, 7 to 3, p = 0.34).  The picture is the one the marks gave with one more rater: the large models form
a block (Sonnet and Opus 27, Fable with each 23 to 24), Roger and Haiku another (23), and 30 pairs cannot
rank the three large models against one another.

**Roger's escalation rule, on the test's figures** (2026-10-04: Sonnet first; a pair Sonnet would cut
that sits exactly on the cut-off goes to Opus, and is kept if Opus puts it under; a Sonnet keep is never
re-examined, so a candidate survives if either model would keep it).  Nearest pairs, cut-off 3: Sonnet
cuts 42 of 256; 38 (15%) are on the line and go to Opus, which rescues 8; the 2 pairs Opus alone would
also cut are kept by design.  Cut-off 4: 4 pairs on the line, none rescued.  For comparison, Fable as
the second opinion would rescue 3 of the 38 and Haiku 7.  The 38 pairs fall in 33 of the 100 calls, so
about a third of candidates get a second call, at about $0.01 each on Opus: about 30 cents per 100
candidates.  To be revisited once manual review has produced statistics (Roger).

Record notes: `overlap_test_1`'s [run.json](../../data/candidates/overlap_test/overlap_test_1/run.json)
now shows the last session's `models` (four), `rubrics` (A only) and `rubric_versions` (A as 4, the
draft-2 text re-pinned, whose hash is the one the version-2 records carry); the per-record fields in
[responses.jsonl](../../data/candidates/overlap_test/overlap_test_1/responses.jsonl) are the record of
what each call was sent.  The Fable session is the third in `sessions`, and its command was
`--run-id overlap_test_1 --models <the three> claude-fable-5-1 --rubrics A --resume --budget-usd 12`.

## Recommendation (mine, for you to decide)

1. **Rubric A, concept similarity, for the overlap call.**  Persona space does not choose: the two tie
   under Opus and A is a little ahead under Sonnet and Haiku, inside the noise.  What decides it is how the
   scales are used.  B rates correlated but distinct traits as going together (B is a point above A on
   average, two or more points on 80 pairs), so on the realistic nearest-neighbour set it puts 94 of 100 existing
   traits at 3 or more against a neighbour, and 49 at 4.  A gap finder on B would call almost everything
   covered.  A separates the known groups (random pairs 0, every recorded opposite "opposite", 8 of 11
   drop-or-merge pairs at 3 or 4), tracks the embedding better, rises steadily with both cosines (the
   calibration by-product of design item 7 needs exactly that), and Opus repeats its A answer for the same
   pair in another call more often (32 of 38 against 26).
2. **Sonnet 5.5 runs the overlap call**, as the design expected.  On rubric A it agrees with Opus 85%
   exactly, 100% within one point, kappa 0.91, and 96% at the 2-or-3 line; its persona-space correlation
   (0.67) equals Opus's (0.68), at about half Opus's price ($0.0036 a call against $0.0068 here; about $36
   per 10,000 candidates live with lists this size, half that in batches).  Haiku is not good enough for
   this call: a third of a point generous, 58% exact, and nearly twice Opus's number of "same concept"
   answers, which is exactly where the cut-off sits.
3. **Escalation**: "unsure" never came back under A, so "unsure goes to Opus" would not fire.  Two
   alternatives worth considering: send Opus the pairs Sonnet puts on the cut-off line (3 far from
   alignment, 4 near it; "alignment" is the candidate's alignment score, 0 to 3, from the M1 filter's alignment check), or rely on the planned 10% Opus audit alone.
4. **A first view of the cut-offs** (rubric A; to be set from your marks after the M3 pilot, design item
   6).  The scale's own line falls between 2 ("overlapping concepts") and 3 ("the same concept, differing
   in scope, degree or emphasis"):
   - **Far from alignment: covered at 3 or 4.**  That catches 8 of the 11 drop-or-merge pairs, 4 of the
     34 near-distinct pairs, none of the random pairs and none of the deliberate duplicates (all at 2).
     On the nearest-neighbour sample, 30 of 100 existing traits have a neighbour at 3 or more under Opus
     (35 under Sonnet): that is how often a candidate sitting where an existing trait sits would be called
     covered.
   - **Near alignment: covered only at 4** ("either label could replace the other"), so that variants of
     degree or scope stay, in line with your "density increases gradually as you get closer to
     alignment".  At 4 Opus put only 5 distinct pairs:
     [conceptual](../../data/traits/instructions/conceptual.json) and [abstract](../../data/traits/instructions/abstract.json),
     [theoretical](../../data/traits/instructions/theoretical.json) and [conceptual](../../data/traits/instructions/conceptual.json),
     [theoretical](../../data/traits/instructions/theoretical.json) and [abstract](../../data/traits/instructions/abstract.json),
     [detached](../../data/traits/instructions/detached.json) and [dispassionate](../../data/traits/instructions/dispassionate.json),
     [insular](../../data/traits/instructions/insular.json) and [parochial](../../data/traits/instructions/parochial.json)
     (the two theoretical pairs were 3 in their drop-or-merge call and 4 in their nearest-neighbour call).
     [Honest](../../data/traits/instructions/honest.json) and [truthful](../../data/traits/instructions/truthful.json)
     (3) would then both stay, near alignment.
   - **2 never covers** on its own.

   The 33 distinct pairs Opus put at 3 are the ones to look at to judge the far-from-alignment line:
   [absolutist](../../data/traits/instructions/absolutist.json) and [moral universalist](../../data/traits/instructions/moral_universalist.json);
   [adventurous](../../data/traits/instructions/adventurous.json) and [adventurous-eater](../../data/traits/instructions/adventurous_eater.json) (Sonnet 2);
   [agreeable](../../data/traits/instructions/agreeable.json) and [conciliatory](../../data/traits/instructions/conciliatory.json);
   [calm](../../data/traits/instructions/calm.json) and [serene](../../data/traits/instructions/serene.json);
   [careless](../../data/traits/instructions/careless.json) and [sloppy](../../data/traits/instructions/sloppy.json);
   [compassionate](../../data/traits/instructions/compassionate.json) and [empathetic](../../data/traits/instructions/empathetic.json) (in its nearest call);
   [confident](../../data/traits/instructions/confident.json) and [overconfident](../../data/traits/instructions/overconfident.json);
   [cruel](../../data/traits/instructions/cruel.json) and [callous](../../data/traits/instructions/callous.json);
   [dramatic](../../data/traits/instructions/dramatic.json) and [theatrical](../../data/traits/instructions/theatrical.json);
   [dramatic](../../data/traits/instructions/dramatic.json) and [melodramatic](../../data/traits/instructions/melodramatic.json);
   [elitist](../../data/traits/instructions/elitist.json) and [aristocratic](../../data/traits/instructions/aristocratic.json);
   [entertaining](../../data/traits/instructions/entertaining.json) and [playful](../../data/traits/instructions/playful.json);
   [grandiose](../../data/traits/instructions/grandiose.json) and [self-aggrandizing](../../data/traits/instructions/self_aggrandizing.json);
   [hedonistic](../../data/traits/instructions/hedonistic.json) and [self-indulgent](../../data/traits/instructions/self_indulgent.json);
   [honest](../../data/traits/instructions/honest.json) and [truthful](../../data/traits/instructions/truthful.json);
   [honest](../../data/traits/instructions/honest.json) and [transparent](../../data/traits/instructions/transparent.json);
   [indecisive](../../data/traits/instructions/indecisive.json) and [noncommittal](../../data/traits/instructions/noncommittal.json) (Sonnet 2);
   [independent](../../data/traits/instructions/independent.json) and [self-reliant](../../data/traits/instructions/self_reliant.json);
   [methodical](../../data/traits/instructions/methodical.json) and [organized](../../data/traits/instructions/organized.json);
   [nationalist](../../data/traits/instructions/nationalist.json) and [regionalist](../../data/traits/instructions/regionalist.json);
   [nationalist](../../data/traits/instructions/nationalist.json) and [civilizationist](../../data/traits/instructions/civilizationist.json);
   [perfectionist](../../data/traits/instructions/perfectionist.json) and [meticulous](../../data/traits/instructions/meticulous.json);
   [quantitative](../../data/traits/instructions/quantitative.json) and [data-driven](../../data/traits/instructions/data_driven.json);
   [sarcastic](../../data/traits/instructions/sarcastic.json) and [sardonic](../../data/traits/instructions/sardonic.json) (in its nearest call);
   [serious](../../data/traits/instructions/serious.json) and [solemn](../../data/traits/instructions/solemn.json);
   [theatrical](../../data/traits/instructions/theatrical.json) and [melodramatic](../../data/traits/instructions/melodramatic.json);
   [trustworthy](../../data/traits/instructions/trustworthy.json) and [dependable](../../data/traits/instructions/dependable.json);
   [systems-thinker](../../data/traits/instructions/systems_thinker.json) and [holistic](../../data/traits/instructions/holistic.json);
   [wry](../../data/traits/instructions/wry.json) and [sardonic](../../data/traits/instructions/sardonic.json);
   [utilitarian](../../data/traits/instructions/utilitarian.json) and [consequentialist](../../data/traits/instructions/consequentialist.json);
   [clannish](../../data/traits/instructions/clannish.json) and [cliqueish](../../data/traits/instructions/cliqueish.json);
   [regionalist](../../data/traits/instructions/regionalist.json) and [parochial](../../data/traits/instructions/parochial.json);
   [moral relativist](../../data/traits/instructions/moral_relativist.json) and [relativist](../../data/traits/instructions/relativist.json).
   Several are recorded neighbours on purpose (the sequence members, the deliberate duplicates' kin); a
   candidate re-proposing one of them would be dropped, which is what the line is for.

## Decisions for you

1. **Rubric A for the overlap call**, B kept only as the record of this test?
2. **Sonnet 5.5 for the overlap call**, with Opus as the 10% audit, and Haiku not used for it?
3. **Escalation**, since "unsure" is not used: Opus on the pairs Sonnet puts on the cut-off line, or the
   audit only?
4. **The first view of the cut-offs**: covered at 3 or more far from alignment and at 4 near it, 2 never;
   to be revisited with your marks after the M3 pilot.
5. **Your marks** on the 30 pairs of [m3_overlap_marks.md](./m3_overlap_marks.md), to check Opus.
6. **A draft 3 of the answer line?**  Sonnet broke the answer format in 8 of 180 rubric-A calls (7
   self-corrections after adding a `"label"` key, 1 missing key), and Opus misnumbered a row once in 180
   calls under B.  The parser and one more ask handle both; a sentence such as "no other keys" might
   prevent the first.  Optional.
7. **By-products for the drop-or-merge and pairing lists**: the five pairs Opus put at 4 (decision 4) as
   the strongest merge candidates; and [self-blaming](../../data/traits/instructions/self_blaming.json)
   and [blame-shifting](../../data/traits/instructions/blame_shifting.json), read as opposites by every
   model, which belongs with your [accountable](../../data/traits/instructions/accountable.json) triangle rather than the merge list.

## Caveats

- The persona vectors come from the 8-slot extraction of May 2026; descriptions regenerated since then
  are judged here as they are now, so for some traits the vector and the description differ.  This
  affects both rubrics alike.
- Only 280 of the 409 pairs have two persona vectors, and few of the labelled groups do (9 of 30
  antonyms, 4 of 30 random pairs), so the persona-space correlations rest mainly on the nearest pairs.
- Sonnet 5.5 and Opus 5.5 ran at their default temperature (they refuse a setting), so their answers vary
  between calls; the 38 repeated pairs give a first measure of it (Opus gave the same rubric-A answer 32
  times).
- The targets are existing traits standing in for candidates; an M3 candidate is described by an [M1
  gloss](./glossary.md#m1-gloss) of about 14 words, shorter than a corpus description.

## Files

- Code: [assistant_axis/gapgen/overlap_test.py](../../assistant_axis/gapgen/overlap_test.py) (pair set,
  rendering, parsing, runner, analysis, marks) and
  [data_analysis/gap_generation/overlap_test.py](../../data_analysis/gap_generation/overlap_test.py) (the
  CLI); tests in [test_gapgen_overlap_test.py](../../assistant_axis/tests/test_gapgen_overlap_test.py) and
  [test_gap_generation_cli.py](../../data_analysis/tests/test_gap_generation_cli.py).
- Run: [pairs.json](../../data/candidates/overlap_test/overlap_test_1/pairs.json),
  [responses.jsonl](../../data/candidates/overlap_test/overlap_test_1/responses.jsonl) (every request and
  answer), [results.jsonl](../../data/candidates/overlap_test/overlap_test_1/results.jsonl) (one row per
  pair, rubric and model), [summary.json](../../data/candidates/overlap_test/overlap_test_1/summary.json)
  (with the provenance envelope), [tables.md](../../data/candidates/overlap_test/overlap_test_1/tables.md),
  [usage.json](../../data/candidates/overlap_test/overlap_test_1/usage.json),
  [run.json](../../data/candidates/overlap_test/overlap_test_1/run.json),
  [run.log](../../data/candidates/overlap_test/overlap_test_1/run.log),
  [rendered_prompts.md](../../data/candidates/overlap_test/overlap_test_1/rendered_prompts.md).
- Command: `uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1
  --budget-usd 15`, then the same with `--resume` after the parser change.
