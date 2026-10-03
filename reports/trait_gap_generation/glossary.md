# Glossary for the trait-gap documents

Plain-language entries for the terms of art the readouts, plans and reviews in this directory use.
A document links a term on its first use (`[centred](./glossary.md#centred)`) rather than defining
it inline, unless the term is the subject of the passage.  Add an entry when a document introduces
a term; keep entries short and in ordinary words; say what the thing is for, not only what it is.
Started 2026-10-01 (Roger: "a repeated problem we've had in these docs ... is jargon I'm
unfamiliar with").

## Embedding spaces and metrics

<a id="embedding"></a>
### Embedding
A list of numbers (a vector, here 1,024 to 3,072 long) that a model produces for a piece of text,
built so that texts with similar meaning get vectors pointing in similar directions.  The platform
embeds `label: description` for each trait and compares the vectors to find near-duplicates and
gaps.

<a id="cosine"></a>
### Cosine similarity
The angle between two vectors, reported as a number from -1 to 1: 1 means the same direction,
0 unrelated, negative opposite.  Vectors are first scaled to length 1 ("unit-normalised") so that
only direction counts.  "1 - cosine" is used as a distance.

<a id="raw"></a>
### Raw space
The embedding vectors as the model returns them, unit-normalised and nothing else.

<a id="centred"></a>
### Centred space
Every vector has the average vector of the corpus (the "corpus mean") subtracted before
normalising.  Embedding models put all text into a narrow cone, so every pair of descriptions
looks fairly similar; subtracting the mean removes that shared part and leaves the differences
between traits.  The mean is fixed as the corpus mean (Roger, 2026-09-23), so new candidates are
shifted by the same amount as the corpus.

<a id="pcs"></a>
### Principal components (PCs)
The directions in which the centred vectors vary most, ordered from largest to smallest.  The
first few often carry something generic (register, length, the shared "This means" opening).
Variants named `centred_pc1` and `centred_pc3` remove the top one or three directions
altogether.

<a id="zca"></a>
### ZCA whitening
A transform of the centred space that stretches it until the variance is equal in every
direction: directions the corpus varies in a lot are shrunk, rare directions are expanded.  Cosine
then measures how unusual a difference is relative to the corpus's own spread rather than how
large it is.  An exact version makes every corpus point equidistant from every other, so the
platform uses a regularised one.  The persona pipeline uses the same operation for its axes.

<a id="partial-whitening"></a>
### Partial whitening (`pwN`)
Roger's variant (2026-10-01): shrink only the top N principal components, each down to the
amplitude of the (N+1)th, and leave the rest alone.  N = 1, 2, 4, 8, 16, 32, 64 are tried, and
12 and 24 since round 4.  Every `pwN` [centres](#centred) on the fixed corpus mean first, so it is
centring plus the shrink, never the raw space shrunk.  A middle way between centring (N = 0) and
full whitening.

<a id="hubness"></a>
### Hubness and hubs
In a high-dimensional space some points sit near the middle of the cloud and turn up as the
nearest neighbour of far too many others; those are hubs.  A hub makes "nearest neighbour" less
informative.  The census counts how often each trait appears in the ten nearest of others.

<a id="csls"></a>
### CSLS
Cross-domain similarity local scaling: a correction for hubs that penalises a candidate neighbour
by how close it is to everything in general, so that hubs stop winning.  Needed only when hubs
exist; centring removes the few in this corpus.

<a id="nearest-neighbour"></a>
### Nearest neighbour (NN)
For a trait, the other trait whose vector is closest (highest cosine).  "5-NN mean" is the mean
cosine to the five closest.

<a id="loo"></a>
### Leave-one-out (LOO)
Each trait is scored against the corpus with itself removed, as a new candidate would be, so the
scores say how the corpus treats something it has not seen.

<a id="residual"></a>
### Residual fraction and the directional score
Fit the top K principal directions of the other traits; the residual fraction of a trait is the
share of its vector that lies outside that subspace (0: fully explained by existing directions;
1: entirely new).  This is Roger's "under-represented direction" measure of novelty, as against
the local measure (distance to the nearest neighbour).

<a id="k95"></a>
### K and K_95
K is how many principal directions the residual fraction uses.  K_95 is the number needed to hold
95% of the corpus's variance (the plan's rule for setting K per space); in text-embedding space it
comes out in the hundreds.  K is judged only through task (c) below, a proxy.

## Tasks and statistics

<a id="auc"></a>
### AUC
Area under the ROC curve: the probability that a randomly chosen member of one group scores
higher than a randomly chosen member of the other.  1.0 is perfect separation, 0.5 is chance,
below 0.5 means the groups are ordered the wrong way.  Task (a) asks whether labelled duplicates
score closer than near-distinct pairs; task (b) whether duplicates score closer than antonyms.

<a id="spearman"></a>
### Spearman correlation
Rank correlation: how well the ordering of one quantity matches the ordering of another, from -1
to 1, ignoring the scale of either.  Task (c) uses it between a text-space novelty score and the
persona-space residual.

<a id="tasks-abc"></a>
### Tasks (a), (b), (c)
The three checks of plan 15 step 4: (a) separate labelled duplicate pairs from labelled distinct
neighbours; (b) separate duplicates from antonyms, to see how much a metric conflates them; (c)
rank-correlate the text-space novelty score with the persona-space yield.

<a id="labelled-pairs"></a>
### Labelled pairs
Pairs of traits with a recorded relation, used as ground truth: antonym (recorded clean pairs),
duplicate (seed-queue rulings that a proposed label was already covered), near-distinct (members
of recorded triangles, sequences and the plan-11 list), deliberate duplicate (a standard's pole
beside a plain trait), polysemy reject, and random unrelated pairs.

<a id="thresholds"></a>
### t_hi, t_lo, upper fence
`t_hi`: the similarity above which 95% of labelled duplicates fall (the "covered" line, if the
labels can set one).  `t_lo`: the 99th percentile of random pairs (below it, "new").  The upper
fence: Q3 + 1.5 × IQR of the nearest-neighbour distribution (the usual outlier rule), used for the
drop-or-merge tail when the labels cannot set `t_hi`.

<a id="iqr"></a>
### Quartiles and IQR
Q1 and Q3 are the values below which a quarter and three quarters of the data fall; the IQR is
their difference, the spread of the middle half.

<a id="gloss-recall"></a>
### Gloss recall@1
For each trait, embed its short M1 gloss and ask whether its own description is the nearest
corpus text.  The share for which it is.  A free stand-in for paraphrase recall until paraphrases
exist.

<a id="recall-at-k"></a>
### Recall@k
For a set of queries that each belong to one existing trait (a reworded description, an M1 gloss),
the share whose own trait is among the k corpus entries nearest to the query.  Recall@1 asks for the
trait first; recall@5 only for it to be in a list of five.  Round 4 uses it because the proposed M3
design hands each candidate's k nearest traits to an LLM to judge, so what matters is whether the
right trait is on that short list, not whether a similarity threshold can be drawn.

<a id="mcnemar"></a>
### McNemar's test
A test of whether two settings scored on the same queries really differ.  Queries both settings find,
or both miss, say nothing about the difference; only the discordant ones count (found by one and not
the other).  If the settings were equally good, each discordant query would be a fair coin toss
between them, so the exact test asks how unlikely the observed split is under that coin (the p
value: below 0.05 is the usual line for "real").  "12 / 3" in a table means 12 queries found only
by the first setting and 3 only by the second.

<a id="paired-bootstrap"></a>
### Paired bootstrap
A way to put an interval on a difference in recall without a formula: redraw the queries at random
with replacement, many times (2,000 here), recompute the difference each time, and take the middle
95% of the results.  "Paired" because both settings are scored on each redrawn query.  Round 4
redraws whole traits rather than single queries, since one trait contributes up to five queries
(one per source) and they tend to succeed or fail together; an interval that excludes zero says the
difference is unlikely to be luck of the draw.

<a id="holm"></a>
### Holm's adjustment
When many comparisons are tested at once, some will pass p < 0.05 by chance alone.  Holm's method
raises each p value according to how many tests were run, so that the chance of any false "real"
in the whole family stays at 5%.  Round 4 applies it across its 24 pooled comparisons.

<a id="minimal-pairs"></a>
### Minimal pairs (criterion f)
"X rather than Y" and "Y rather than X" for a clean pair, embedded separately.  A model that
handles the construction gives two distinct vectors, each nearer its own pole; a bag-of-words
model gives near-identical ones.

<a id="contrast-classes"></a>
### Contrast-clause classes N, P, S
The 2026-09-23 census of descriptions with a "rather than / instead of / but not / without being"
clause: N, necessary for sense (the clause picks the intended meaning of a polysemous label); P,
names the other pole; S, stylistic or scope.  The `strip` representation removes the clause at
embedding time only; descriptions are never edited.

<a id="representations"></a>
### Representations
The forms of the text that are embedded: `full` (label: whole description), `noprefix` (without
"This means"), `w20` and `w14` (cut to about 20 or 14 words), `strip` (contrast clause removed),
`dup` (a gloss followed by a copy of itself, to test whether length or content drives similarity).

<a id="m1-gloss"></a>
### M1 filter gloss
The one-sentence "This means ..." definition the M1 trait-hood filter writes for every word it
passes, about 14 words long (corpus descriptions run to about 25).  M3 will embed candidates by
their gloss, so the calibration uses these glosses to stand in for candidates: the glosses of
existing traits for gloss recall, the glosses of rejected labels for some labelled duplicates.

<a id="drop-or-merge"></a>
### Drop-or-merge list
Existing traits whose nearest other trait is unusually close (beyond the upper fence), listed for
Roger to consider merging or dropping.  Plan 15 step 8 asks for it after recorded partners
(clean-pair antonyms, triangle members) are set aside, since those are close by design.

<a id="contrast-criteria"></a>
### Contrast-ablation criteria (a)-(j)
The ten checks of plan 15 step 5 that decide, per embedding model, whether "rather than X"
clauses stay in the embedded text: how far stripping moves a vector (a), the labelled-pair tasks
with and without (b), nearest-neighbour changes (c), the antonym margin (d), a blinded judgement
(e), minimal pairs (f), paraphrase invariance (g), agreement with persona space (h), held-out
recovery (i) and agreement between models (j).  (e), (g) and (i) need an LLM.

<a id="paraphrase-recall"></a>
### Paraphrase recall
Each existing trait's description is reworded by a model (criterion g) and the rewording is used as
a query: is the trait itself the nearest corpus entry?  The share for which it is.  It tests
whether the embedding sees the same concept through different words, the case a re-proposed
existing trait presents in M3.  Measured with and without the trait's label, and with the
rewording cut to a gloss's 14 words (the M3 case).

<a id="heldout-recovery"></a>
### Held-out recovery (criterion i)
Each trait is hidden from the corpus in turn and its rewording is scored against the rest.  For the
covered decision: how often a hidden trait's rewording is still judged close to some other trait.
For the directional score: whether the rewording gets the same residual score as the original
did, i.e. whether the score measures the concept rather than the wording.

<a id="two-settings"></a>
### Covered and directional settings
The two uses of the embedding in M3, tuned separately (Roger, 2026-10-02): "covered" asks whether a
candidate is already in the corpus (nearest-neighbour cosine against a threshold); "directional"
asks whether it adds a direction the corpus lacks (the residual fraction).  Each has its own
space, representation and parameters in the metric config.

<a id="retrieve-then-judge"></a>
### Retrieve, then judge
The M3 design Roger confirmed on 2026-10-02: the embedding only fetches each candidate's k nearest
existing traits (k = 10), and LLM calls decide from that list whether the candidate is already
covered (a relation call, then an overlap call on a concept-similarity scale).  No similarity
threshold decides anything, so `t_hi` and `t_lo` survive only as information.

<a id="drift-canary"></a>
### Drift canary
Eight fixed corpus texts, stored in the metric config, that every embedding run sends to the model
again and compares with their cached vectors.  A closed API model can change without notice; if one
of the eight comes back below cosine 0.999 against the cache, the run logs a warning naming the
model, because the cached vectors may no longer match new ones.

<a id="blinded-comparisons"></a>
### Blinded comparisons (criterion e)
For a sample of traits, the five nearest neighbours with the clauses kept and with them stripped,
shown side by side in random order without saying which is which.  Roger marks 30 and a Sonnet
judge marks the same 30 plus 30 more, so the judge's agreement with him is known before its
verdict on the rest counts.

## Models and machinery

<a id="local-model"></a>
### Local embedding model
A model run on this Mac rather than through an API: `bge-large-en-v1.5` (BERT-based) and
`EmbeddingGemma-300m` here.  Free per call, recorded in `usage.json` all the same.

<a id="cls-pooling"></a>
### CLS pooling, mean pooling
How one vector is made from a transformer's per-token outputs: take the first (CLS) token's
output, or average over all tokens.  bge uses CLS; EmbeddingGemma averages and then applies two
small learned layers, which is why it needs the `sentence-transformers` package.

<a id="mps"></a>
### MPS
Apple's GPU backend for PyTorch on this Mac; where the local models run.

<a id="persona-space"></a>
### Persona space, persona vectors
The activation-space directions extracted from Qwen-3-32B for each trait (the 8-slot set, slot 6,
layer 25).  "Persona-space yield" is a trait's residual fraction there: how much of its vector the
other traits' directions do not explain.  About 300 of the 661 traits have one.

<a id="soft-shear"></a>
### Soft shear (L = 3)
The persona pipeline's adjustment that partly removes the goal / non-goal subspaces before
comparing vectors; see the axis-geometry rule.  Used when loading persona vectors for task (c).

## M1 terms that recur

<a id="zipf"></a>
### Zipf frequency
Word frequency on a log scale from the `wordfreq` package: 1 is very rare, 7 very common.  The
filter rejects below 2.0 without a model call.

<a id="polysemy-notes"></a>
### Polysemy notes
The split filter's flags on a word that passes: `two_trait_senses`, `nontrait_person_sense`,
`obvious_sense_not_trait`, `first_thought_in_the_way`, `leaves_something_out`,
`fits_many_in_different_ways`, `most_likely_reading_stretched`.  "Polysemy" in the summaries means
any of them.

<a id="plain-reading"></a>
### Plain reading
What a word most likely means to an ordinary reader, written by Haiku from the bare label, and then
compared by Sonnet with the corpus description: `same`, `related` or `different`.  For the corpus's
own labels (the run `corpus_comparison_1`) it flags traits whose description uses a sense the word
does not usually carry; round 4 of M2 keeps only the labels read the corpus's way (`same`, 591 of
659) when it uses the M1 glosses as queries.

<a id="second-opinion"></a>
### Second opinion
The same first steps of the split filter repeated on a stronger model (Sonnet 5.5) for a seeded
10% of words plus flagged ones; a disagreement is recorded, not resolved.

## M3 terms (added 2026-10-03, for the overlap rubric test)

<a id="relation-overlap-calls"></a>
### Relation call, overlap call
The two LLM calls of M3's [retrieve, then judge](#retrieve-then-judge) design.  The relation call
asks, for a candidate and each of its retrieved existing traits, whether the two are similar,
opposed, too different for the question to make sense, or unclear.  The overlap call then asks, for
each trait judged similar, how close the two are on a 0-4 scale; that score (with the candidate's
alignment score) decides whether the candidate is a gap or already covered.

<a id="rubrics-a-b"></a>
### Rubric A (concept similarity), rubric B (co-occurrence)
The two candidate wordings of the overlap call.  A asks how similar the two concepts are (4 the
same concept, 0 different concepts), with "opposite" for the reverse quality.  B asks how often a
persona with the target trait would also show the listed one (4 almost always, 1 as often as
anyone, 0 less often than anyone).  A is Roger's preference; B is the comparison arm.  They part
company on traits that go together but mean different things (punctual and tidy).

<a id="target-listed"></a>
### Target, listed trait
In one overlap call: the target is the trait being judged (in M3 the candidate; in the test an
existing trait standing in for one), and the listed traits are the existing traits it is compared
with, numbered 1 to n in random order.

<a id="clean-pair"></a>
### Recorded clean pair
Two corpus traits recorded as each other's opposite (the `arrangement` field, kind `pair`), such as
cheerful and melancholic.  "Recorded opposites" in the test means these plus the other antonym
pairs of the [labelled pairs](#labelled-pairs).

<a id="reference-model"></a>
### Reference model
The model whose answers the others are compared with when there is no human answer key; here Opus
5.5, as in the Opus audit of the M1 filter.  Agreement with it is not proof of being right: Roger's
marks on a blinded sample check the reference itself.

<a id="weighted-kappa"></a>
### Weighted kappa
A measure of agreement between two raters on an ordered scale such as 0-4, corrected for the
agreement two raters would reach by chance given how often each uses each answer.  1 is perfect
agreement, 0 is no better than chance.  "Weighted" means near misses count as partial agreement:
with quadratic weights (the usual choice, and the headline figure here) a one-point difference
costs a sixteenth as much as a four-point one; linear weights charge in proportion to the
distance.  Rough reading: above 0.8 very good, 0.6 to 0.8 good, below 0.4 poor.

<a id="parse-rate"></a>
### Parse rate
The share of a judge's answers that could be read: valid JSON, an answer for every listed item, a
value on the allowed scale, a reason.  The project treats anything under 99% as a fault to fix,
not a cost to accept.

<a id="cluster-bootstrap"></a>
### Bootstrap interval resampling targets
An interval for a correlation found by redrawing the data many times (2,000 here) and recomputing
it each time, keeping the middle 95%.  The redraw picks whole targets (a call's target with all its
listed traits) rather than single pairs, because pairs that share a target are not independent; it
is the [paired bootstrap](#paired-bootstrap)'s idea applied to a correlation.  For a difference
between rubrics A and B both are recomputed on each redraw, so the interval is for the difference
itself: one that excludes zero says the difference is unlikely to be luck of the draw.
