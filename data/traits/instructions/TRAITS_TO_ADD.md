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


