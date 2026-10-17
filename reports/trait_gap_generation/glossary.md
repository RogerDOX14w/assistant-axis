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

## Lexical recall terms (added 2026-10-13, for workstream 11)

Workstream 11 checks M3's retrieval against dictionaries ([coding_plan_11_novelty_ensemble.md](./coding_plan_11_novelty_ensemble.md);
the code is [lexical.py](../../assistant_axis/gapgen/lexical.py) and [lexical_sweep.py](../../assistant_axis/gapgen/lexical_sweep.py)).

<a id="lexical-link"></a>
### Lexical link
A dictionary's recorded tie between two words: in Open English WordNet (OEWN), the two words share a synset
(*synonym*), or a synset of one points at a synset of the other by "similar to" (*similar*) or "see also"
(*also*); in the Moby thesaurus, one word is in the other's row.  Links are by word, not by sense: every sense of
the label counts, so `productive` is linked to [fat](../../data/traits/instructions/fat.json) through the "fertile
land" sense.  OEWN's antonym links and the negation-affix rule (`un-X`, `X-less` / `X-ful`) are kept apart, as
*antonym evidence*.

<a id="lexical-neighbour"></a>
### Lexical neighbour
A corpus trait or live seed-queue entry that a candidate's label has a [lexical link](#lexical-link) to (a trait's
old name, its `renamed_from`, counts as the trait).

<a id="lexical-only-pair"></a>
### Lexical-only pair
A candidate and a [lexical neighbour](#lexical-neighbour) that M3 never listed, read or covered the candidate by:
no model has read the pair, because the embedding did not put the trait among the candidate's ten nearest.

<a id="retroactive-sweep"></a>
### Retroactive sweep
The overlap call run afterwards on every lexical-only pair of the rows M3 already kept, each pair at its row's own
cut-off and rule set.  It records what M3 would have decided had the trait been listed; it never changes M3's
decision.

<a id="lexical-cover"></a>
### Lexical cover
A lexical-only pair that the sweep read at its row's cut-off: a possible miss of M3's retrieval, until Roger's
blind marks say whether the existing trait really covers the word (a dictionary link can be a coincidence of
two senses).

<a id="proposed-merge"></a>
### Proposed merge (dictionary)
How a lexical cover reaches review since plan 11's gate 2 (Roger, 2026-10-14, option (d)): the row keeps M3's
decision, and its card carries a badge "dictionary (WordNet | Moby thesaurus): probably the same as [X]", with the
linked trait among the card's targets so one click merges it.  No lexical link ever cuts on its own, whichever
lexicon; the review record of these proposals later decides whether WordNet covers may (README TODO "Revisit the
duplicate signals").  In the review graph the flag is `lexical_proposed_merge`.

<a id="name-only-link"></a>
### Name-only link
A lexical link to a seed-queue entry that has no description yet: recorded and shown in review, never judged (the
overlap call needs a description) and never a cover.

<a id="stem-family"></a>
### Stem family
Words that share a stem by OEWN's `derivation` links (agreeable, agreeableness) or by the negation-affix rule
(kind, unkind; careful, careless): annotation for the review, never a decision.

## Generator diversity terms (added 2026-10-10, for the base-model generator)

The diversity harness of [coding_plan_03_base_model.md](./coding_plan_03_base_model.md) ("Frozen
interface"); any generator's emission stream can be scored with it.

<a id="rarefaction-curve"></a>
### Rarefaction curve
The number of distinct candidate words found, plotted against the number of samples drawn (or
words emitted) so far.  A curve still climbing steeply says more sampling will keep finding new
words; a curve that flattens says the prompts are running out of new words, and more of the same
sampling is not worth paying for.

<a id="chao1"></a>
### Chao1
An estimate of how many distinct words the generator could produce in all, made from the words
seen once (f1) and twice (f2): the number seen so far plus f1 squared over twice f2.  Many words
seen only once means much is still unseen.  A rough guide to how far a larger run could go, not a
promise.

<a id="collapse-index"></a>
### Collapse index
The share of all emissions taken by the 50 most frequent candidates.  High means the generator keeps
repeating a small set of cliché words (the "mode collapse" instruction-tuned models show); the
base-model plan's target is under 15%.

<a id="recovery-by-string"></a>
### Recovery by string
The fraction of the corpus's trait names (or their former names, `renamed_from`) that a generator
produced as exact strings, with no model call.  A free first check that a generator can reach the
kind of words the corpus has; the platform's recovery harness (`recovery_test.py`) is the fuller,
paid version that also counts synonyms.

## Alignment-sweep terms (added 2026-10-10, after Roger asked what "the gate's gold labels" meant)

From [coding_plan_08_alignment_sweep.md](./coding_plan_08_alignment_sweep.md) and its
[pilot readout](../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/pilot_readout.md).

<a id="enactability"></a>
### Enactability, and the enactability gate
Whether a trait would actually *show* in what a persona writes.  Four values since the gate rubric's
draft 2 ([enactability_gate.md](./rubrics/enactability_gate.md); Roger, 2026-10-10): **chat** (it
shows in answers to ordinary questions, as [candid](../../data/traits/instructions/candid.json) does,
and not to any marked degree in what the persona does on a task), **both** (in those answers *and* on
a task), **agentic-only** (only when the persona is given a task to carry out — "overreaching" needs
an email to send before it can overreach), and **none** (nowhere a reader of the output could detect
it, so the corpus cannot use it; a trait describing a process of training or a model's internals is
the leading example).  Draft 1 had three: with no `both`, a trait visible both ways was filed under
`chat`, so a `chat` verdict could not be read — it meant either "chat only" or "both".  The **gate**
is the LLM call that assigns one of them to each candidate: it writes a two-sentence system prompt
for the trait and then judges whether the trait would be visible.  It exists because the alignment
sources describe much that a chat persona could never display.  (The *extraction* prompt has an
`enactability` field of its own, still with draft 1's three values; the gate's verdict is the one
that counts.)

<a id="gold-set"></a>
### Gold set, gold label
A **gold set** is a small set of items whose right answers are already known, used to measure
whether a step can be trusted before it is let loose on real data; a **gold label** is one of those
known answers.  Here: 30 items, ten corpus traits that plainly show in chat
([sycophantic](../../data/traits/instructions/sycophantic.json),
[honest](../../data/traits/instructions/honest.json),
[calibrated](../../data/traits/instructions/calibrated.json) ...), ten expected to be agentic-only,
ten expected to be none.  The gate is run on them and its answers compared with the gold labels.
The catch, which is why Roger decides and not the agent: the gold labels here were *assigned by the
planning agent*, not measured, so a disagreement can mean the gate is wrong **or** that the gold
label is.  Changing a gold label after seeing the gate's answer would tune the test to the result,
so the agent left all five disagreements for Roger.  The same rule governed the relabelling that the
gate rubric's draft 2 needed (thirty items over four values, `both` included): it was done *blind* on
2026-10-10, by an agent given the rubric and the items but no draft-2 answer and no draft-1 per-item
label, before any draft-2 run existed.
[gate_gold_items.json](../../data/candidates/alignment_sweep/gate_gold_items.json) now carries the
four-way labels (chat 6, both 10, agentic-only 5, none 9; 11 of 30 moved, almost all into `both`),
each item's draft-1 label kept beside it as `expected_v1` and the criteria the relabeller used written
into the file above the items.  One thing the relabelling could not fix, and Roger's to decide: the
`agentic-only` and `none` answers are still carried **only** by items written for the file, so a
corpus trait can never be either, and the gate could score well by reading prose style rather than
the trait.

<a id="flip-rate"></a>
### Flip rate
The share of items on which the same call, run twice, gives different answers.  It separates "the
step is wrong" from "the step is unstable": a gate that agrees with the gold labels 25 times in 30
but flips on 7% of items is mostly *noisy*, and reading it twice and taking the agreement would help;
one that is stable but disagrees is *biased*, and the prompt or the gold labels need changing.

<a id="advisory-only"></a>
### Advisory only
A step whose output is recorded and shown but may not drop or change anything on its own, because it
has not met its measured target.  The enactability gate is advisory after the pilot (25 of 30 against
a target of 26): its verdicts appear in the readout, and no candidate is removed because of them.
That measurement is of the rubric's draft 1; draft 2 has not been evaluated, so the gate stays
advisory until it is.

## Masked-LM generator terms (added 2026-10-12, for workstream 4)

From [coding_plan_04_masked_lm.md](./coding_plan_04_masked_lm.md) and its
[acceptance report](./acceptance_04_masked_lm.md).

<a id="masked-lm"></a>
### Masked LM, fill-mask
A language model trained to fill a blanked-out word back into a sentence (BERT, RoBERTa, ModernBERT),
rather than to continue a text.  Given "She is [MASK] by nature." it returns a probability for every
word piece in its vocabulary at the blank; the generator keeps the whole ranked list, not only the
top few.  Here `roberta-large`, run on this Mac for free.

<a id="frame"></a>
### Frame, frame instance
A frame is one hand-written sentence with a blank, written so that any subject fits ("{subject} is
[MASK] by nature"); an instance is the frame with one subject filled in ("He is [MASK] by nature").
The bank crosses ten subjects, six registers (reference letter, novel, performance review, casual
review, psychology textbook, chat) and three slot types (predicate adjective, attributive adjective,
agent noun), so the bias each brings can be measured by removing it (the frame ablation).

<a id="pseudo-log-likelihood"></a>
### Pseudo-log-likelihood (PLL)
How well a masked LM thinks a given word fits a frame when the word is several pieces long: put the
word into the blank, blank out each of its pieces in turn, and add up the log-probabilities the model
gives the pieces back.  The generator's default ("l2r") also blanks the pieces to the right of the one
being scored, so a split word is scored left to right like a chain; the plain form lets the later
pieces give the earlier ones away and so overrates split words.  For a one-piece word both are just
its probability in the blank.

<a id="variant-b"></a>
### Variant B, the beam passes
Two ways to reach words the tokenizer splits (sycophantic is four pieces) and phrases (risk-averse,
kind to animals).  **Variant B** scores a fixed list, Open English WordNet's adjectives and person
nouns (about 29,500), by PLL in twelve frames: exact, but blind to anything WordNet lacks.  The
**beam passes** let the model invent: fill the first blank with its top choices, then the next blank
given each, keeping sequences that rebuild a word (subword pass) or a phrase (multiword pass): open
to new words, but noisy.

<a id="contrast-score"></a>
### Trait-hood contrast score
A word's PLL in dispositional frames ("is [MASK] by nature") minus the larger of its PLL in state
frames ("is [MASK] today") and physical frames ("looks [MASK]").  High means the word reads as a
lasting disposition rather than a passing state or an appearance.  It rides each submitted
candidate's `score`; its AUC on corpus traits against hand-picked states and physical words says how
well it separates them (target 0.85, report and decide).

<a id="union-rank"></a>
### Union rank
The generator's single ordering of every word any pass surfaced: by the best log-probability the word
reached in any frame, any pass, ties by word frequency.  Recall@k against it is the recovery curve.

## Structural-generator terms (added 2026-10-13, for workstream 9)

Terms of [coding_plan_09_structural_generators.md](./coding_plan_09_structural_generators.md) and its readouts.

<a id="aristotelian-mean"></a>
### Aristotelian mean
Aristotle's picture of a virtue as the right amount of something, between a vice of too little (the
*deficiency*) and a vice of too much (the *excess*): courage between cowardice and rashness, liberality
between meanness and prodigality.  A *triple* is the three together.  Generator A types his table by
hand; generator B asks for the two vices of every corpus trait it can read this way.

<a id="position"></a>
### Position
Where a corpus trait, as its description reads, sits on its own scale: `deficiency` (too little of a
quality), `mean` (the sound amount), `excess` (too much), or `not_scalar` (a creed, a stance, a
membership or a style that is not more or less of anything).  The operators call answers it for every
trait; the answers go to a side table (`position_table.jsonl`) for the pairing review, never into a
trait file.

<a id="structural-operators"></a>
### The five structural operators
The moves generator B makes from each corpus trait, in one call: **opposite** (its contrary, asked
without showing the recorded `negative_label`, so that a disagreement is a signal), **excess** and
**deficiency** (the vices at the too-much and too-little ends of its scale; together the *degree
fillers*), **retarget** (the same disposition aimed at oneself, intimates, strangers, authority,
animals or ideas, and for the traits at alignment score 3 also at the user, the operator and the
developer of an AI assistant) and **remode** (the same disposition as an attitude, a habit or a way of
speaking).  An opposite of a `non-X` or singleton trait is a *pair completion*.

<a id="null-rate"></a>
### Null rate (and the non-null share)
The share of a retarget target's or remode mode's answers that are `null`.  Most traits have no
named disposition toward animals or in speech, so `null` should be the commonest answer; the pilot's
gate reads the other side, the non-null share: above 40% means the model invents forms, below 5% means
it does not try.

<a id="label-set-jaccard"></a>
### Label-set Jaccard
How alike two answers to the same call are for one trait: the labels both gave, slot by slot (as
stems), divided by the labels either gave, from 0 (nothing in common) to 1 (the same labels), counted
only over the slots at least one of them filled (two empty answers are not agreement).  Haiku 5.5 runs
at its default temperature of 1, so the answers are expected to differ: since 2026-10-13 the figure is
**reported, never a gate** (Roger), between two runs or between a run's own samples.

<a id="samples-and-support"></a>
### Samples, the union, and support
Since 2026-10-13 (Roger) the operators call asks each trait three times, independently (three
*samples*), and keeps the **union** of their answers: per slot, every label any sample gave, a label
given twice in different spellings (`fool-hardy`, `foolhardy`) kept once.  A label's **support** is how
many of the samples gave it (1 to 3).  Nothing is dropped for low support; support is shown in the
readouts ("union of 3 samples") and kept in the table, so a later wave could order by it.

<a id="net-new"></a>
### Net-new row, net-new kept share
A *net-new* row is one the registry has not yet filtered: not a corpus trait, not a seed-queue entry,
and not a word M1 and M3 have already decided, whichever generator brought it (a registered word they
have not decided still counts, since it still costs and is still reviewed).  The review-hour wave counts only
net-new rows toward its 300.  The *net-new kept share* is the kept rows (M3 `new` or `grey`) per
submitted net-new row, measured at the pilot; it replaces plan 04's assumed 0.5 in sizing the wave.

## Generator testing terms (added 2026-10-13, for workstream 13)

Workstream 13 measures the generators instead of adding to them: how much of the corpus each finds again, how
much of what it finds is new, what review costs, and how many concepts are left.  Plan:
[coding_plan_13_generator_testing.md](./coding_plan_13_generator_testing.md); the table it prints:
[dashboard.md](../../data/candidates/testing/dashboard.md).

<a id="recovery-harness"></a>
### Recovery harness: hidden, recall, precision, false cover
The harness hides a tenth of the corpus (a pair or simplex hides whole), scores a generator's candidates against
the rest, and asks which hidden traits they find again.  **Recall**: hidden traits recovered by a candidate M3
kept, over hidden traits.  **Precision**: kept candidates that recover a hidden trait, over kept candidates (low
by design when a generator proposes mostly new words).  **False cover**: a candidate M3 turned away as covered by
another trait although it matches a hidden one.

<a id="pooled-harness"></a>
### Pooled harness, affected only
**Pooled**: one hidden draw per seed for every generator at once; every candidate row is scored once and each
generator's figures are read from the rows it proposed (the same figures a separate run would give).  **Affected
only**: only the rows whose decision hiding could change are scored again (a hidden trait among their nearest
traits, in their label or in their recorded decision, or a list of nearest traits that moves without the hidden
ones); the others' recorded decisions are copied.  Exact, not a sample.

<a id="strict-column"></a>
### Strict column
Recall with every overlap reading held to the cut-off 4 (the same concept) instead of M3's own cut-off (3 for most
traits).  Printed beside the headline recall; Roger: "3 is primary, report 4 as well".

<a id="pair-recovery"></a>
### Pair recovery
A hidden trait some kept candidate was read *opposite* against: the generator found its antonym.  Printed beside
recall, never added to it.

*Not the same as plan 09's pair recovery*, where a blind `opposite` call recovers a recorded pair's other pole (the structural generator's evaluation, in [coding_plan_09_structural_generators.md](./coding_plan_09_structural_generators.md)).

<a id="edges-3-4"></a>
### 3-edge, 4-edge
Two kept candidates in the review graph whose overlap readings are both 4 in both directions (a **4-edge**: what
review merges) or both 3 or above (a **3-edge**: the review app proposes them as a group).

<a id="concept-unit"></a>
### Concept unit (concept component): components_4, grown_3
How kept candidates are grouped into concepts for counting.  **components_4**: candidates joined by 4-edges, chains
included (the strict unit: it splits real concepts, seldom joins wrong ones).  **grown_3**: those groups merged
across 3-edges while the merged group keeps at least two-thirds of its pairs linked (a chain's share falls with
every link, which stops it).  **components_3** (3-edges, chains unbroken) is only a diagnostic: one chain holds a
quarter of the candidates.

<a id="review-agreement"></a>
### Kept together, one concept, hard negatives
Scores of a concept unit against Roger's review.  **Kept together**: of the pairs of decided candidates he made one
concept, the share one unit holds.  **One concept**: of the decided pairs a unit puts together, the share he made
one concept.  **Hard negatives**: pairs he marked distinct, or dropped from a group the graph had proposed; a good
unit joins few.

<a id="review-minute"></a>
### Review-minute
One minute of Roger's active review: the time between consecutive actions in the review app's log, a gap longer
than five minutes counted as a break.  The rate is terms decided per review-minute (2.43 on the TDA batch).

<a id="promote-share"></a>
### Promote share
Of the groups review resolved (a single term is a group of one), the share promoted as a new concept (decision 3:
per group, 51-54% so far); the per-term share (about 20%) is printed beside it.

<a id="pre-handled"></a>
### Pre-handled
A kept term with a 3-edge (or 4-edge) to a term another review batch already decided: the review app counts it as
handled from the start, so it costs no review-minute.

<a id="stop-rule"></a>
### Stop rule
When a generator is worth another wave: expected accepted terms per review-minute, from its undecided, not
pre-handled kept terms (the groups they form times the promote share, over the minutes their shapes take).

<a id="capture-recapture"></a>
### Capture-recapture, occasion
Estimating the size of a population from how much two or more samples of it overlap: the fewer they share, the
larger it is.  An **occasion** is one sample; here a generator *mechanism* (the lexicon walks, IPIP, the base
model), not a generator, and the corpus itself can be one.

<a id="chapman"></a>
### Chapman estimator
Capture-recapture from two occasions: (n1 + 1)(n2 + 1) / (m + 1) - 1, where n1 and n2 are what each found and m
what both found.

<a id="chao2"></a>
### Chao2
Capture-recapture over several occasions from how many concepts were seen on exactly one (Q1) and exactly two
(Q2) of them; many concepts seen only once mean many not seen at all.  Like Chapman it assumes every concept is
equally easy to find and the occasions independent; both are false here, so the estimate is a lower bound.

<a id="good-turing"></a>
### Good-Turing coverage
1 - Q1 / (all sightings): roughly the share of the population the occasions have already seen.

<a id="accumulation-curve"></a>
### Accumulation curve, end slope
New concepts found against candidates emitted, in the order a generator emitted them.  The **end slope** (new
concepts per candidate over the last tenth) is its marginal yield; a flat end means it has saturated.

<a id="persona-space-novelty"></a>
## Persona-space novelty terms (added 2026-10-13, for workstream 12)

Workstream 12 ([coding_plan_12_persona_space.md](./coding_plan_12_persona_space.md)) predicts where a candidate's
[persona vector](#persona-space) would land from its text, and reads novelty there instead of in text space.

<a id="canonical-cell"></a>
### Canonical cell
The one place in Qwen3-32B's activations the platform reads persona vectors from: the 8-slot extraction's slot 6,
layer 25, centred on the mean of every trait and role vector, [soft-sheared](#soft-shear) at L = 3.  M2, M3's
overlap test and the persona-space scorer all use it, so their cosines are comparable.

<a id="orphan-vector"></a>
### Orphan vector
An extracted vector whose entity no longer has a file (dropped, or renamed with the old name not recorded).  It stays
in the pool, so the mean, the shear and the principal directions are unchanged, but nothing is trained on it and no
neighbour list names it.

<a id="ridge"></a>
### Ridge regression
Least squares with a penalty, alpha, on the size of the coefficients, which keeps a fit with many more inputs than
examples (3,072 embedding dimensions, 572 entities) from memorising noise.  Larger alpha: smoother, and predictions
pulled harder toward the average.

<a id="kind-covariate"></a>
### Kind covariate
One extra input to the regression, 1 for a role and 0 for a trait, so traits and roles are fitted together while
their average positions may differ.

<a id="grouped-folds"></a>
### Arrangement-grouped folds
Cross-validation in which a clean pair, triangle or other arrangement is held out whole: a trait is never predicted
while its antonym is in the training set, which would flatter the fit.

<a id="energy-outside"></a>
### Energy outside the top N (residual_N)
The share of a vector's squared length that lies outside the pool's N strongest [principal directions](#pcs):
the [residual fraction](#residual) at N.  High: the vector points somewhere the
existing entities mostly do not, a new direction.  N is swept over 12-32 and chosen where predicted and actual
residuals agree best.

<a id="shrinkage"></a>
### Shrinkage
A regression's pull toward the average: predicted vectors are more typical than real ones, so every predicted
residual is smaller than the actual (median 0.22 against 0.40 at N = 20).  That is why a raw predicted residual is
never read directly.

<a id="calibration-percentile"></a>
### Calibration percentile (residual_pct)
A candidate's predicted residual read against the predicted residuals of existing entities, each predicted while it
was held out, where the shrinkage is the same: 0.9 means more novel-looking than 90% of the corpus would look to the
same predictor.

<a id="pair-axis-position"></a>
### Pair-axis position
Where a predicted vector sits along the line between its nearest trait and that trait's clean-pair partner: +1 at
the trait, -1 at the partner, 0 halfway.  Reported because antonyms are not opposite each other in persona space
(their cosine is about 0), so the sign of a cosine cannot tell a pair completion from an unrelated trait.

<a id="duplicate-like"></a>
### Duplicate-like, novel-like, flag base rate
The scorer's flag.  **Duplicate-like**: the predicted vector is at least as close to an existing entity as a
held-out entity's prediction is to its own vector half the time (cosine 0.732).  **Novel-like**: otherwise, and a
calibration percentile of 0.80 or more.  The **base rate** is how often an existing entity's held-out prediction is
duplicate-like to *another* entity (32% at 0.732).  It is **not** a false-alarm rate: the corpus is dense at that scale, and 37% of existing entities have an *actual* neighbour at 0.732 or above, so most of the 32% are real close pairs.  The **false-alarm rate** is the flag rate among entities with no actual neighbour at the threshold (13% at 0.732), and that is roughly what a genuinely new candidate with no close corpus neighbour can expect (plan 12 review, 2026-10-13; `calibration.json` `dup_base_rate_split`).

<a id="disagreement-quantile"></a>
### Disagreement quantile
The candidates on which persona space and M3 disagree most (M3 "new" but duplicate-like; M3 "covered" but far from
the covering trait; M3 "covered" but novel-like), each kind ranked by strength and cut to 10% of the scored rows.
They go to Roger, and the first kind through M3's own overlap call; M3's decision never changes.

<a id="prospective-test"></a>
### Prospective test
Predicting, before the next extraction, the persona vectors of the entities that have none yet, then comparing with
the vectors when they come.  Judged on ranks and nearest names, since the new extraction is a different space.

## Corpus-frames terms (added 2026-10-17, for workstream 5)

Workstream 5 ([coding_plan_05_corpus_frames.md](./coding_plan_05_corpus_frames.md)) harvests the words people use of
people by counting what fills fixed phrases in the Google Books n-grams and in two corpora of character
descriptions.  A [net-new row](#net-new) is defined above, with the structural generator's terms.

<a id="lexical-frame"></a>
### Frame (lexical), filler
A fixed phrase with one slot, such as "a very X man", "an incorrigible X" or "known for his X"; its **fillers** are
the words found in the slot in a corpus ("honest", "liar", "honesty").  Unlike the masked-LM generator's
[frames](#frame), which a model fills, these are counted in text people wrote.  The frames come in six syntactic
types (degree, nominal, possessive, copular, tendency, habitual; the text corpora add trait lists and filler-first
frames such as "X to a fault"), because every frame lets some words through and not others.

<a id="shard"></a>
### Shard, head-peeking
The Books n-grams come as thousands of gzipped files (**shards**, about half a gigabyte each), sorted as one long
alphabetical list, so every n-gram starting "very " sits in one or two neighbouring shards.  **Head-peeking** reads
only the first line of a shard (a 4 KB download) to learn where it starts, and a binary search over those first
lines finds which shards hold a frame, before anything large is downloaded.

<a id="document-frequency"></a>
### Document frequency
How many different books (or, for the text corpora, how many different character descriptions) contain a filler in
a frame, rather than how many times it occurs: a word one author repeats a thousand times counts once per book.
It is one of the two within-frame orderings.

<a id="lift"></a>
### Lift
How much more often a word fills a frame than its everyday frequency predicts: the log of its share of the frame's
fillers minus the log of its share of English (word frequency from `wordfreq`).  It pushes down words that fill
every frame because they are common ("good", "old", "little") and pushes up words that occur mostly as
descriptions of people.  It is the other within-frame ordering; the free recovery check picks between the two.

<a id="rrf"></a>
### Reciprocal-rank fusion (RRF)
A way to merge several rankings without letting the biggest one dominate: each word scores 1 / (60 + its rank) in
every frame that found it, and the scores are added.  A word ranked first in a small frame beats one ranked fiftieth
in a large frame, and doubling every count of one frame changes nothing, since only ranks enter.

<a id="frame-yield"></a>
### Yield (of a frame)
The share of a frame's fillers that the trait-hood filter (M1) calls a trait, measured on the frame's own top 25 in
the pilot (a filler already in the registry counts with its recorded verdict).

<a id="net-filter"></a>
### Net filter, total variation distance
How far the traits a frame finds lean away from what all the frames find together: the **total variation distance**
(half the sum of the absolute differences between two distributions, 0 for the same distribution, 1 for no overlap)
between the frame's traits spread over the seven regions and the union's (`region_tv`), and likewise over the forms
adjective, noun and phrase (`form_tv`).

<a id="unique-contribution"></a>
### Unique contribution (unique kept rows)
The rows a frame found that no other frame found and that the novelty check (M3) kept as `new` or `grey`.  A frame
with a low yield or a strong net filter is still kept for the wave when it has at least one.
