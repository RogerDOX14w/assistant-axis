# Traits To Add

Candidate traits identified during antonym labeling (Feb 2026) that would be
valuable additions to the trait set.

## Moral circle / concern scope spectrum (added Mar 2026)
- ~~selfish~~ added
- ~~clannish~~ added
- ~~cliqueish~~ added
- ~~parochial~~ added as **insular** (parochial connotes "hidebound/old-fashioned";
  insular captures the moral-circle meaning: caring only about one's own community)
- also added **parochial** with moral-circle-only definition (no old-fashioned connotation)
- ~~nationalist~~ added
- ~~patriotic~~ added
- ~~racist~~ → renamed to **racialist** (less pejorative Victorian term), then deleted.
  Sonnet 4 refuses to generate instructions for both "racist" and "racialist" — hard
  RLHF guardrail on the concept regardless of phrasing. **ethnocentric** (added, works)
  covers the same moral-circle position through the academic framing, which passes the
  filter despite being semantically equivalent.
- also added **regionalist** (multi-nation region as moral circle) and **sectarian**
  (religious group as moral circle) to fill gaps in the spectrum
- ~~humanitarian~~ added
- ~~philanthropic~~ added
- ~~kind-to-animals~~ added

## Misalignment (added Mar 2026)
- ~~malicious~~ added
- ~~malevolent~~ added
- ~~sociopathic~~ added
- ~~destructive~~ added

## RLHF-alignment triad (added Mar 2026)
- ~~honest~~ added
- ~~harmless~~ added
- ~~helpful~~ added

## Candidate traits
- new-age
- technomystical — technology is spiritual or reveals spiritual truths; treats AI,
  the internet, computation as having transcendent/sacred properties
- spiralist — treating AI outputs as spiritual/cosmic revelation (2025 phenomenon).
  Term too new for Sonnet to know. "technomystical" covers the broader category;
  spiralism is its specific AI-oracle manifestation.

## Clean antonym pairs (added Apr 2026)

Added 5 new traits as clean bidirectional pairs of existing traits. Each was
verified by starting with `negative_label = non-X`, running antonym generation,
and confirming it independently recovered the expected antonym. See
`AGENT_NOTES.md` § "Adding New Trait Clean Pairs" for the full process.

- **obedient** ↔ rebellious — all-5 @ 2 on both polarities
- **compassionate** ↔ callous — all-5 @ 2 on both polarities
- **ecocentric** ↔ anthropocentric — all-5 @ 2 on both polarities
- **conservative** ↔ progressive — mostly 2 (4×2, 1×1 on each polarity)
- **pragmatic** ↔ idealistic — pos scored mostly 1 (not added to goal list)

Dropped: **conformist** ↔ contrarian — asymmetric pair (conformist→nonconformist,
not contrarian). May revisit.

## Clean antonym pairs (candidates, low priority)

For traits where the neg_label is a real word (not `non-X`) that is not already a trait (so we don't already have a "clean bidirectional pair"), consider
generating proper standalone trait definitions for the antonym side. This would
make them clean bidirectional pairs — each side with its own description,
pos instructions, and eval_prompt — rather than relying on the neg instructions
to approximate the opposite direction.

Any trait where the antonym is a rich enough concept to warrant its own
description + pos instructions is a candidate. Generating the antonym as a
full trait would let us measure both directions independently rather than
relying on neg instructions to approximate the opposite.

We could also then experiment with neg = neutral, average behavior, and identify if clean pairs actually have cosine angle ~-1.

## TODO: aligned_AI framing revision (Apr 2026)

The `roles/aligned_artificial_intelligence` description and pos instructions are
written entirely in **instrumental / mechanism-design vocabulary** ("intelligent
agentic tool", "extended phenotype", "goals completely aligned", "no conflicting
objectives", "extension of human capability"). They contain no warm-virtue
vocabulary (care, compassion, honesty, dignity, mercy, harmlessness).

Empirical consequence (slot 3, layer 24):

- `cos(aligned_AI, corpus_mean) = +0.62` — higher than cos with any moral anchor.
- `cos(aligned_AI, compassionate) = +0.49` ≈ `cos(aligned_AI, malicious) = +0.48`.
- `cos(saint, angel) = +0.90` but `cos(aligned_AI, saint) = +0.58`.
- PC2 ("warm virtue" circuit): saint loads at +18.1, aligned_AI at −0.3.
- In the moral-slice plot (`compassionate → malicious`, perpendicular = care),
  aligned_AI projects to (21, 7) — essentially on top of the corpus mean (22, 7)
  and **outside the HHH triangle** (helpful, harmless, honest).
- K=4 whitening makes this worse: shrinking PC1-PC4 attenuates the little
  "virtue" content aligned_AI has while preserving its distinctive "AI tool"
  content (PC5+), pulling it further from HHH and closer to the corpus centroid.

This is a "miniature alignment problem": two genuinely-different conceptions
of "an AI that is good for humanity" (instrumental vs virtuous) produce
measurably different activation signatures, even when both would pass human
"yes, that's aligned" vibe checks.

**Possible follow-ups (pick one, don't just overwrite the current file):**

1. Keep current file as `aligned_ai_instrumental.json`; add
   `aligned_ai_virtuous.json` with warm-virtue vocabulary ("acts with honesty,
   transparency, and genuine care for human wellbeing; treats every person
   with dignity; refuses to cause harm"). Measure cosine between the two and
   compare projections — the difference itself is the interesting quantity.
2. Leave as-is but caption plots honestly: "aligned_AI as described is
   instrumentally framed; it does not project strongly onto warmth/care".

If we do (1), remember it shifts `role_mean`, so any downstream analysis
that uses it (including `m` common-mode geometry and `||m||/||diff||`
hardness numbers) needs to be regenerated. This is non-trivial rework, so
don't bundle with other experiments — treat as its own thread.

Same latent ambiguity ("which conception of this concept did the author
encode?") likely affects other roles/traits we have not examined as
closely. The aligned_AI case is just the most visually obvious.

## TODO: trait connotation audit (Apr 2026, updated for L25/K3)

The 2D pair-slice study (`roger/axis_judge_experiments/pair_slices/`,
generated by `results_analysis/pair_slice_plots.py`) flags axis pairs
where ``|midpoint − trait_mean| / |pos − neg| >= 0.5`` at slot 3,
layer 25, K=3 soft whitening — i.e. axes whose +/− pole pair sits
noticeably *off* the trait-mean origin in a shared "common-mode"
direction.  At L25/K3 the audit returns **13 hits out of 33** axes
with judging data.  Three of those 13 have y-direction sort orders
whose top entities go beyond the pair's literal definition.

The diagnosis isn't a single thing.  Three reasons can drive the
common-mode pull:

- **(a) Intrinsic semantic correlation.**  The concept genuinely
  overlaps another semantic dimension in human moral/personality
  structure (e.g. forgiveness IS a prosocial disposition).
  *Prescription: don't fix; the embedding is faithful.*
- **(b) Trait-file framing imbalance.**  Description / pos
  instruction vocabulary is asymmetric between the two poles (warmth
  asymmetry, dominionist tilt, etc.).
  *Prescription: rewrite the trait file.*
- **(c) Pole-label linguistic asymmetry.**  One pole's label is the
  grammatical negation of a positively-valenced word ("un-forgiving",
  "dis-honest", "harm-ful").  English flags one pole as
  negation-of-virtue regardless of how the file is written.
  *Prescription: relabel the pole or live with it.*

### `individualistic / collectivistic` — keep as-is

The +y (individualistic) direction ranks contrarian / cynic /
sardonic / provocateur / acerbic at the top, not the
autonomy/self-direction traits the description emphasises.

`individualistic.json` itself is **clean** — instructions are about
autonomy / self-reliance / personal expression, with no contrarian or
cynical vocabulary.  But `collectivistic` (the negative pole on the
same file) is heavy in **positive-affect / warmth vocabulary**:
"harmony", "cooperation", "shared values", "fitting in", "community",
"collective wisdom", "shared responsibility", "greater good".  The
pole-difference vector ``individualistic − collectivistic`` therefore
subtracts a substantial warmth component, and Qwen's pretrained
representation of "individualism stripped of warmth" is closest to
contrarian / sardonic / cynic — because that's how Western
individualism is typically framed in training-corpus literature
(lone-wolf archetypes, anti-conformist stances, etc.).

There's also a smaller real (a)-class component: cross-cultural
personality psychology shows individualism does modestly correlate
with lower agreeableness.  So rewriting the file to add positive-affect
vocabulary on the individualistic side would help, but wouldn't
eliminate the pull entirely.  **Verdict: probably not worth rewriting.**

### `ecocentric / anthropocentric` — DONE (Apr 30 2026)

Rewrite completed. Both descriptions were rebalanced to:

- **anthropocentric**: humans intrinsically valued; environment / animals / wild
  species valued *instrumentally* via human wellbeing, safety, aesthetics,
  recreation, or guilt about how humans treat nature. Replaces the prior
  "dominion / unjustified burdens / serve human purposes" framing with
  philosophically-defensible weak anthropocentrism.
- **ecocentric**: ecosystem health and the welfare of all living creatures
  intrinsically valued for their own sake; humans valued as one part of the
  broader system *and* instrumentally for their outsized capacity to protect
  or harm it (stewardship-responsibility framing). Replaces the prior
  short "intrinsically valuable, prioritise environment" framing.

Both descriptions are ~60 words with parallel "This means treating X as
inherently important and valuable" openings, em-dash insertions, and "rather
than" closings. Bidirectional antonym validation passed (`generate_antonyms.py`)
with score 4 in both directions.

Original analysis below preserved as historical context — it explains *why* the
rewrite was needed and what residual y-flag pull is expected (intrinsic
moral-circle-scope component) even after a clean rewrite.

Activations / vectors will need to be regenerated for both traits (tracked in
`AGENT_NOTES.md` -> "TODO: regenerate activation/vector data").

#### Original analysis (preserved as historical context)

The −y (anthropocentric) direction ranks dishonest / sycophantic /
sociopathic / arrogant / narcissist at the top.

`anthropocentric.json` does have **non-trivial pejorative tilt**:

- "Natural resources **exist primarily to serve human purposes**"
- "Conservation efforts are **only worthwhile if they serve human interests**"
- "humans **have dominion over nature**" (politically/theologically loaded)
- "Environmental regulations ... are **generally unjustified burdens**"

This lands the file near *strong anthropocentrism / dominionism*,
the most caricatured end of the philosophical spectrum.  A rewrite
toward *weak anthropocentrism* ("humans matter most, but stewardship
and prudential care for nature are virtues") or *humanism*
("celebrating human dignity, creativity, civilization, moral agency")
would be more philosophically defensible and would reduce the pull
toward sociopathic/narcissistic.

**But:** even a perfectly-neutral rewrite won't close the gap
entirely.  The moral-circle-scope axis intrinsically (a-class)
correlates with selfish-vs-altruistic in human moral psychology;
prioritising humans-over-nature-under-tradeoff is genuinely a
weak-moral-circle stance.  And no framing of "humans matter most"
will read as neutral to readers with strongly ecocentric priors,
because the disagreement isn't about wording, it's about the
underlying position.

### `forgiving / unforgiving` — keep as-is

The +y (forgiving) direction ranks forgiving / nurturing / empathetic
/ supportive / agreeable / compassionate; the −y (unforgiving)
direction ranks zealot / dogmatic / sociopathic / savage / arrogant /
evil / hostile / cruel.

This is **mostly (a)-class intrinsic semantic correlation**.
Forgiveness genuinely *is* a prosocial / Care-foundation moral
disposition — it's a canonical example in moral-foundations theory
and Big Five Agreeableness.  Refusing to forgive genuinely *is*
closer to vindictiveness / wrath / hostility in human moral
psychology, not just a "remembers vs forgets" cognitive stance.  The
embedding is faithfully representing this.

There's also a (c)-class linguistic-asymmetry contribution: "un-forgiving"
is a grammatical negation of a positively-valenced word, so the label
itself biases the pole toward "absence of virtue".  No description
will fully neutralise that.

`unforgiving.json` does have a few mildly-pejorative phrases ("refuse
to show mercy", "social rejection are appropriate responses",
"forgiveness only enables bad behavior"), but they're not the main
driver — the prosocial/antisocial overlap is intrinsic semantics, not
artifact.

**Verdict: not worth rewriting.**  The y-flag here documents a real
semantic property of the concept, not a defect in our data.

### Bottom-line recommendations

| pair | dominant cause | prescription |
|---|---|---|
| individualistic / collectivistic | (b) warmth-asymmetry + small (a) | rewrite low-priority |
| ecocentric / anthropocentric | (b) dominionist tilt + (a) intrinsic moral-circle-scope | **DONE Apr 30 2026** -- both descriptions rewritten; activations regen pending |
| forgiving / unforgiving | (a) intrinsic prosocial/antisocial + (c) un-prefix asymmetry | keep as-is |

Same caveat as for `aligned_AI`: rewrites shift `trait_mean`, so any
analysis that uses it (`m` common-mode geometry, `||m||/||diff||`
hardness, leave-one-out re-centering, etc.) needs to be regenerated.
Treat as its own thread, don't bundle.

The other 10 of the 13 L25/K3 hits (systems_thinker/analytical,
relativist/absolutist, reductionist/holistic, progressive/conservative,
egalitarian/elitist, convergent/divergent, casual/formal,
practical/theoretical, improvisational/methodical, concise/verbose) all
have y-direction sort orders that cleanly match the pair name — their
above-threshold ``|m|/|diff|`` ratios reflect *legitimate common-mode
content* (a meaningful semantic dimension shared by both poles) rather
than connotation drift.  No rewrite needed.

## TODO 2026-05-13 — dimensionality-yield expansion roadmap

The 60-axis clean cohort spans only ~21 effective dimensions in the L=3
soft-sheared frame (entropy rank of the Gram-matrix spectrum; cf.
participation ratio = 10.94 for the variance-weighted "dominant rank",
top-37 PCs for 95% variance).  We have ~5000 dimensions to use; we are
heavily underusing the residual stream's representational capacity.

The next step is **strategic axis additions** — pick pairs that add
NEW effective dimensions, not pairs that fill in the variance mass of
existing clusters.  Two complementary prioritisations follow.  Each
candidate is labelled with its **yield estimate** (1 − ‖proj‖²/‖a‖² on
the top-20 PC subspace of the current 60-axis Gram matrix; 1.0 =
perfectly orthogonal, ~0.5 = redundant with existing).  Both the
methodology and the empirical scores were generated 2026-05-13 by the
cohort-cosine-seriation work; see chat log + cohort-mean / per-pair
analyses in the same session.

### Background: how the methodology works

Yield estimation per candidate trait T:

1. Compute T's activation direction relative to the role+trait corpus mean
   (NOT just the per-kind default — the per-kind default contains
   kind-specific signal that contaminates the residual).
2. Apply the project canonical L=3 soft-shear at (slot=6, layer=25).
3. Project onto the top-20 PC subspace of the existing 60-axis Gram
   matrix.  Residual fraction = 1 − ‖projected‖² / ‖d‖².
4. Sort descending.  High residual = T's direction is mostly NOT in
   existing axis space — adding T (with an appropriate antonym) likely
   yields a new effective dimension.

Caveat: this scores LONE POLES, not pairs.  The pair axis (pos − neg)
may be more or less orthogonal than the individual pole.  But a pole
whose direction is heavily out-of-subspace is a strong leading
indicator that its pair will also be high-yield, because the pair
direction is at most as in-subspace as the more-aligned of its two
poles.

### Strategy 1: highest-yield isolated dimensions (most-orthogonal candidates)

Top traits from the 2026-05-13 yield analysis (192 unpaired traits in
the corpus; scores measured corpus-mean-centered, sheared L=3, top-20
projection).  Grouped into thematic dimension families with suggested
opposites.  Each family currently has zero or near-zero representation
in the 60-axis cohort.

Numbers in `[brackets]` = residual fraction; higher = more orthogonal.

**Family 1: emotional state** (entirely missing from cohort)
- [0.829] `melancholic` → cheerful / sanguine
- [0.829] `stoic` → emotive / expressive
- [0.826] `calm` → agitated  ← simple, likely highest-yield single addition
- [0.781] `serene` → restless / turbulent

**Family 2: desire / drive / sensuality**
- [0.884] `epicurean` → spartan / austere
- [0.881] `lustful` → chaste / continent
- [0.842] `artistic` → philistine / utilitarian
- [0.843] `obsessive` → balanced / nonchalant

**Family 3: interpersonal-conflict style** (partially covered by
conciliatory/confrontational + blunt/tactful, but missing several
distinct patterns)
- [0.857] `passive_aggressive` → direct / forthright
- [0.848] `avoidant` → engaging / engaged
- [0.829] `flirty` → aloof / reserved
- [0.804] `charismatic` → bland / unassuming

**Family 4: communication / discourse mode**
- [0.846] `narrative` → expository
- [0.823] `socratic` → didactic
- [0.796] `rhetorical` → informational
- [0.807] `conceptual` → applied / operational

**Family 5: metaphysical / agency stance**
- [0.818] `deterministic` → indeterministic / probabilistic
- [0.816] `fatalistic` → empowered / agentic
- [0.816] `paradoxical` → coherent / logical
- [0.773] `existentialist` → essentialist (note: essentialist already
  in cohort — needs a *different* opposite, or this pair isn't
  realisable as a clean two-pole axis)

**Family 6: cognitive-mode extras** (cohort already covers
analytical/systems-thinker, reductionist/holistic, practical/theoretical)
- [0.798] `interdisciplinary` → disciplinary / specialist
- [0.797] `speculative` → empirical / fact-bound
- [0.793] `subversive` → orthodox / conformist
- [0.776] `moderate` → extreme

**Priority pick (highest expected yield with simplest antonym creation):**
`calm / agitated`, `stoic / emotive`, `passive_aggressive / direct`,
`epicurean / spartan`, `narrative / expository`.  Each likely adds
~0.8 of a new effective dimension.

### Strategy 1a: orthogonal-axis-by-midpoint inference

For each existing clean pair (pos, neg), the **midpoint direction**
`m = (vec_pos + vec_neg)/2 − corpus_mean` is by construction
perpendicular to the pos−neg axis direction.  When `|m| / |pos − neg|`
is large (Apr 2026 audit flagged 13 of 33 axes at threshold 0.5 in
slot 3 / L25 / K3), the pair has a meaningful common-mode direction
that's not yet an axis in the cohort.  Adding a new pair pointing in
the `m`-direction would, **by construction**, be orthogonal to the
original pair (and often orthogonal to most other axes too).

This trick is doubly powerful: it gives both a *direction* (the
midpoint) and a *semantic interpretation* (what do these two
related-but-opposite concepts both have in common that's not the axis
between them?).

#### Specific candidates from the 13 flagged pairs

For each pair, the "common-mode direction" is what's shared between
its poles beyond the explicit axis.  Identifying the right ortho-pair
is essentially: *what's the axis you'd need to add to disambiguate
this shared semantic component?*

| existing pair | shared common-mode content | candidate ortho-pair |
|---|---|---|
| progressive/conservative | political-engagement-as-such | **political / apolitical** ← Roger's example |
| religious/secular | engagement with metaphysical-religious-framing | **devout / indifferent** (engagement-amount, not direction) |
| materialistic/spiritual | engagement with values-of-the-cosmos vs daily-grind | **transcendentally-oriented / present-focused** |
| introverted/extroverted | social-energy-level (high or low, regardless of inward/outward) | **socially-intense / socially-flat** |
| arrogant/humble | self-focus-amount (regardless of positive/negative valence) | **self-attentive / self-effacing-in-the-non-arrogant-sense** |
| forgiving/unforgiving | emotional-investment in interpersonal-grievance | **emotionally-engaged-with-others / disengaged** |
| individualistic/collectivistic | rule-stance-clarity-on-where-self-stops | **self-other-boundary-aware / boundary-fuzzy** |
| ecocentric/anthropocentric | engagement-with-moral-circle-scope itself | (already covered by individualistic↔collectivistic somewhat) |
| egalitarian/elitist | engagement-with-hierarchy-as-topic | **hierarchy-conscious / hierarchy-indifferent** |
| reductionist/holistic | engagement-with-the-question-of-reductionism | (likely covered by analytical) |
| systems_thinker/analytical | meta-cognitive-engagement | (already covered) |
| relativist/absolutist | engagement-with-the-question-of-relativism | (closely tied to skeptical/dogmatic) |
| convergent/divergent | engagement-with-the-cognitive-process-itself | (likely covered) |

The **5 most-promising "common-mode" candidates** to construct as new
clean pairs (each by construction orthogonal to its parent pair):

1. **political / apolitical** — the orthogonal to progressive/conservative.
   Independently valuable: distinguishes "person who cares deeply about
   politics on either side" vs "person who treats politics as
   irrelevant".  No analogue in current cohort.
2. **devout / indifferent** — the orthogonal to religious/secular.
   Distinguishes "person who treats religious questions as central"
   vs "person to whom they're peripheral", regardless of theistic
   commitment.
3. **socially-intense / socially-flat** — the orthogonal to
   introverted/extroverted.  Captures "social energy as such",
   independent of direction.
4. **hierarchy-conscious / hierarchy-indifferent** — orthogonal to
   egalitarian/elitist.  Distinguishes "person for whom power
   structures are salient" vs "person for whom they're not".
5. **emotionally-engaged-with-others / emotionally-disengaged** —
   orthogonal to forgiving/unforgiving (and likely also to several
   other interpersonal pairs).  Captures "emotional weight assigned
   to interpersonal events" independent of vindictive/merciful
   valence.

### Strategy 1b: PCA-of-entity-pool → describe-and-name underused directions

A complement to Strategies 1 and 1a.  Both of those look at *what
traits to add* given a hypothesis about the missing direction; this
strategy works the other way around — *start from a direction* (a
principal component of the entity pool's covariance) that's not
already covered by an axis, then figure out what trait pair would
name it.

The trick that makes it efficient: the PCA of the entity pool tells
us **which directions the model already has significant variance
along** at the chosen (slot, layer, whitening) cell.  Any direction
the model isn't varying over is unrecoverable from this analysis
(see end of section for that limit case).

#### Procedure

1. **PCA on the entity pool** at the canonical operating point:
   compute the SVD of the 580-entity activation matrix at (slot=6,
   layer=25), corpus-mean-centered, after applying the project default
   L=3 soft-shear.  Top right-singular-vectors (PCs) are the
   highest-variance directions the model uses to differentiate
   entities.

2. **Compute |cos| between each top-N PC and each existing axis
   direction**.  Sort PCs.  A PC is "used" if its max |cos| with any
   axis exceeds ~0.5; "weakly used" 0.35–0.5; "unused" <0.35.

3. **Roger's "used up" filter**: walk PCs in order.  If PC_k has high
   |cos| with axis A, mark A as "claimed" by PC_k.  Continue.  When
   looking for new candidate axes, restrict attention to PCs whose
   max |cos| with any *unclaimed* axis is below threshold — i.e.
   directions of significant model variance that no existing axis
   captures.

4. **Sort entities along each underused PC** and feed top-5 / bottom-5
   to Claude Opus (or similar capable LLM) with a prompt like *"these
   are entities at the high vs low pole of an unknown axis; what trait
   pair best describes this axis?"*.  Opus will propose candidate
   (pos, neg) labels.

5. **Mixed-signal fallback**: if a single PC's top-5/bottom-5 don't
   suggest a clean concept, try plotting **2-D slices** of PC_i × PC_j
   for nearby pairs (i, j) and look for diagonal directions where
   entities cluster more cleanly.  The right axis may live as a
   diagonal in PC-pair space rather than as an individual PC.

#### Empirical run on the 2026-05-13 cohort

Top-30 PCs of the entity pool, ranked by max |cos| with any existing
axis (slot 6, layer 25, soft_shear L=3, corpus-mean-centered):

```
PC   var%   max|cos|   best-match axis                   status
PC1  10.53%   0.625    careless/conscientious             used
PC2   8.17%   0.598    forgiving/unforgiving              used
PC3   7.02%   0.545    detached/empathetic                used
PC4   6.06%   0.550    idealistic/pragmatic               used
PC5   4.99%   0.449    angel/demon                        weakly used
PC6   3.77%   0.376    constructivist/essentialist        weakly used
PC7   3.36%   0.410    progressive/conservative           weakly used
PC8   3.11%   0.437    honest/dishonest                   weakly used
PC9   2.35%   0.460    confident/uncertain                weakly used
PC10  2.12%   0.326    fragile/resilient                  UNUSED   ← 2.1% variance, no axis covers
PC11  1.87%   0.511    precise/vague                      used
PC12  1.81%   0.432    passionate/dispassionate           weakly used
PC13  1.61%   0.284    idealistic/pragmatic               UNUSED   ← 1.6% variance, ditto
PC14  1.56%   0.349    constructivist/essentialist        UNUSED
PC15  1.45%   0.250    passionate/dispassionate           UNUSED
PC16  1.40%   0.202    impatient/patient                  UNUSED   ← cleanest "unused" signal
PC17  1.27%   0.327    ecocentric/anthropocentric         UNUSED
PC18  1.21%   0.202    descriptive/prescriptive           UNUSED
PC19  1.07%   0.294    religious/secular                  UNUSED
PC20  1.02%   0.274    individualistic/collectivistic     UNUSED
```

20+ of the top-30 PCs are "unused" by the axis cohort — roughly
matching the ~21 effective dimensions estimate from Strategy 1.
Below are the top-5 / bottom-5 entity sortings for the five
highest-variance unused PCs (mix of roles `R:` and traits `T:` omitted
in display; sortings actually mix kinds, which is itself informative):

```
PC10 (var 2.12%, max|cos|=0.33)
  high: entertaining, playful, witty, goofy, chemist, irreverent
  low : proofreader, amnesiac, simulacrum, bodhisattva, addict, observer
  → tentative axis name: humorous/serious? (cf casual/formal already in cohort)
    or animated/diminished? Probably needs Opus-description + 2D slice.

PC13 (var 1.61%, max|cos|=0.28)
  high: efficient, poet, concise, widow, materialistic, melancholic
  low : toddler, pacifist, sycophantic, anarchist, caveman
  → tentative: mature-restraint / pre-cultured-uninhibited? cultured/uncultured?

PC14 (var 1.56%, max|cos|=0.35)
  high: programmer, pedantic, mathematician, toddler, fool, debugger
  low : opaque, concise, relativist, dispassionate, detached, plain_spoken
  → tentative: literal-explicitness / withholding-evasion? probably mixed.

PC15 (var 1.45%, max|cos|=0.25)
  high: understated, minimalist, dispassionate, enigmatic, detached, loner
  low : translator, casual, bodhisattva, linguist, demon, interpreter
  → tentative: solitary-reserved / connective-communicative? distinct from
    introverted/extroverted (those load on a different PC).

PC16 (var 1.40%, max|cos|=0.20)
  high: proofreader, translator, summarizer, editor, linguist, cosmopolitan
  low : nutritionist, paramedic, therapist, enigmatic, pharmacist, socratic
  → tentative: symbolic-manipulation / embodied-care? mixes role-kind boundaries
    so likely picks up a kind-specific dimension we haven't axiomatised.
```

Several of these tentative names look promising (especially PC15
"solitary/connective" and PC13 "cultured/uncultured") and are worth
following up: ask Opus to confirm/refine the axis label given the
sortings, then check whether a clean-pair candidate already exists
in the corpus or needs antonym creation.

#### Caveat: model-variance-bound

Strategy 1b can only find axes the model **already varies along**.
If the model has zero variance in some semantically-real direction
(e.g. it doesn't distinguish at all between two equally-rare
phenomena), then PCA can't surface that direction.  The remedy in
those cases is human-introspective: *what aren't we varying over*?
List corpus entities and ask "if I think of axis X, which existing
entity is at each pole?".  If you can't easily find entities at both
poles, the corpus doesn't span axis X — and adding poles for X then
becomes a **corpus expansion** problem rather than a **labeling**
problem.

A worked example: if we wanted an axis for `risk_seeking / risk_averse`
and the corpus contains 0 entities clearly at either pole, no PCA
will find this dimension because the model isn't ranging over it
in this entity set.  The corpus would need explicit risk-seeking and
risk-averse entity files added first; then the dimension would emerge
in PCA and Strategy 1b could name it (or Strategy 1's antonym-
suggested approach could go ahead and write the antonym).

### Strategy 2: by ease-of-addition (cheapest → hardest)

Inventory based on current `negative_label` fields across the 192
unpaired traits (analysis: 2026-05-13).

**Tier A — READY TO ADD (2 pairs)**

Both poles already in corpus; bidirectional `negative_label` match
already verified; just haven't been added to `pair_list_clean.json`.
Cost: ~$3/pair to judge.

- `closure_seeking / open_ended` — cognitive-style; likely new dimension
- `eloquent / plain_spoken` — rhetorical-style; possibly close to
  rhetorical/socratic cluster (validate yield first)

**Tier B — LAZY-PLACEHOLDER FIXABLE (6 pairs)**

Both poles in corpus, but one side's `negative_label` is the
auto-generated placeholder (`non_X` or `un_X`) rather than the real
antonym.  Editing the placeholder side to point at the real antonym
unlocks clean-pair status with no new judging-cost beyond the pair
itself (~$3/pair).

```
edit             current → fix to    parent pair would become
─────────────────────────────────────────────────────────────────────
selfish.neg      unselfish → altruistic       altruistic / selfish
compassionate.neg non_compassionate → callous   callous / compassionate
conformist.neg   non_conformist → contrarian   contrarian / conformist
parochial.neg    non_parochial → eclectic      eclectic / parochial
philanthropic.neg non_philanthropic → misanthropic  misanthropic / philanthropic
```

Pre-edit: re-run `generate_antonyms.py --traits X Y` to confirm the
proposed fix bidirectionally validates.  Some of these placeholder
choices may have been principled (cf. the conformist/contrarian
triangle from Apr 2026); audit the trail before fixing in case the
"laziness" was actually a deliberate decision.

**Tier C — TANGLED (3 cases, real semantic disagreement)**

Both poles in corpus, neither uses a placeholder, but their
`negative_label` fields point to different concepts.  Pick one
resolution per case.

```
educational → superficial    |  superficial → thorough
   ↳ resolution: superficial/thorough is the genuine axis; pair
     educational with `superficial` or `non_educational` only if a
     new instruction file is written disambiguating "shallow-purpose"
     from "shallow-depth".  Leave as-is otherwise.

efficient → thorough        |  thorough → superficial
   ↳ resolution: efficient's true opposite is wasteful or
     inefficient (which is the placeholder form); thorough's is
     superficial (already clean as superficial/thorough).  Either
     add `wasteful / efficient` as a new pair, or accept efficient
     as a singleton.

vindictive → forgiving      |  forgiving → unforgiving
   ↳ resolution: vindictive and unforgiving are not the same concept
     (active revenge-seeking vs passive grudge-holding).  Either
     add `vindictive / merciful` as a new pair (and keep
     forgiving/unforgiving as a separate axis) or merge them.  The
     forgiving/unforgiving common-mode direction (Strategy 1a above)
     might be useful here — maybe vindictive sits on the
     emotional-engagement common-mode rather than on the
     forgiving/unforgiving axis itself.
```

**Tier D — NEW ANTONYM NEEDED (179 traits)**

Bulk of the work.  Each requires:

1. Write seed `<antonym>.json` with `positive_label`, `description`,
   `negative_label = non-<antonym>` (placeholder).
2. Run `regenerate_trait_instructions.py --traits <antonym> --force`.
3. Run `generate_antonyms.py --traits <antonym> <original>` to verify
   bidirectional match.
4. Update `negative_label` on both sides to point at each other.
5. Re-generate instructions for the antonym with the proper
   `negative_label` set.
6. Add to `trait_list.json`.
7. Goal-classify in `data/goal_roles_and_traits.json` if applicable.
8. Run activation/vector extraction for the new pole.
9. Add to `pair_list_clean.json` (auto-propagates via
   `tools/build_pair_lists.py`).
10. Judge the pair in the next desc+inst batch (~$3/pair).

**Prioritisation within Tier D:** sort by the 2026-05-13 yield
scores; pick top entries from each Family 1–6 above first to maximise
dimensional spread before depth.  Specifically, the 5-pair starter
batch from Strategy 1 would each cost ~$15 (vector generation
+ judging both poles) and collectively add ~3–4 new effective
dimensions if the yields hold up after antonym creation.

### Combined batch suggestion (~$90 total, ~5–10 new effective dims)

- Tier A (free 2): `closure_seeking/open_ended`, `eloquent/plain_spoken`
- Tier B (fix 4): `altruistic/selfish`, `callous/compassionate`,
  `contrarian/conformist`, `eclectic/parochial`,
  `misanthropic/philanthropic`
- Tier D (top yield from Family 1–6): `calm/agitated`, `stoic/emotive`,
  `passive_aggressive/direct`, `epicurean/spartan`, `narrative/expository`
- Strategy 1a (orthogonal-by-construction):
  `political/apolitical` (orthogonal to progressive/conservative)

That's ~13 new pairs.  Estimated yield: ~+8–10 new effective dimensions
(from ~21 to ~31), assuming Strategy 1a items deliver on their
construction-orthogonality promise.  Cost: ~$24 (Tier A+B) + ~$50
(Tier D + 1a, including pole-vector creation overhead) = ~$74 expected,
$90–110 conservative.

### Re-running this analysis later

The yield numbers above are computed at the 2026-05-13 cohort state
(60 clean pairs).  After each round of additions, re-run the yield
analysis from scratch — the top-20 PC subspace shifts as the cohort
grows, so a trait that scored 0.8 yield against the 60-axis cohort
might score 0.6 against the 70-axis cohort.

If the yield-analysis becomes a recurring tool, a candidate name is
`tools/axis_yield_analysis.py` paralleling `tools/build_pair_lists.py`.


