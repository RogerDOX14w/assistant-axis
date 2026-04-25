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

## TODO: trait connotation audit (Apr 2026)

The 2D pair-slice study (`roger/axis_judge_experiments/pair_slices/`)
revealed two trait pairs whose y-direction sort orders do NOT cleanly
match their pair name — i.e. the activation geometry encodes a
*connotation* of the concept rather than its philosophically-neutral core.

### `individualistic / collectivistic`

The +y (individualistic) direction ranks contrarian / cynic / sardonic /
provocateur / acerbic at the top, not the autonomy/self-direction traits
the description emphasises ("personal autonomy", "self-reliance", "unique
personal expression").

The description itself is **fairly clean** — most lines are about autonomy
rather than contrarianism. A few lines do contribute mild counter-cultural
flavour ("resist pressure to conform", "stand out from the crowd",
"goes against popular opinion"). Most of the contrarian/cynical
association is the **model's prior** about the word "individualistic" in
training-corpus discourse, where Western individualism is often framed
as anti-group / non-conformist / pricky.

### `ecocentric / anthropocentric`

The −y (anthropocentric) direction ranks dishonest / sycophantic /
sociopathic / arrogant / narcissist at the top, not the human-centered-
moral-concern traits the pair name implies.

Here the description is **doing more of the work** than the model prior:

- "Natural resources **exist primarily to serve human purposes**"
- "Conservation efforts are **only worthwhile if they serve human interests**"
- "humans **have dominion over nature**"
- "Environmental regulations ... are **generally unjustified burdens**"

This is closer to "exploitative dominion / anti-environmentalism" than
"philosophical anthropocentrism", and the activation geometry correctly
picks up that this register is morally suspect in modern training
corpora — which puts it adjacent to sociopathic/narcissistic/dismissive
traits. A more neutral framing ("humans are the appropriate focus of
moral concern; responsibilities to each other take priority over external
considerations") would almost certainly produce a cleaner pair.

### Decision pending

These pairs are **not necessarily broken**. The activation geometry is
faithfully reporting how the model (and by extension the internet
training corpus) *thinks about these concepts* — which is itself a
finding worth surfacing rather than papering over. The relevant questions:

- For our axis-correlation work, do we want a pair that measures the
  philosophically-neutral concept, or the connotation-loaded version
  the corpus actually uses? Different downstream uses may want different
  things.
- If we rewrite, the rewrites are interventions on what the model does
  that day, not corrections to the model's actual associations. The
  original-vs-rewrite difference is itself the interesting quantity.

Same caveat as for `aligned_AI`: rewrites shift `trait_mean`, so any
analysis that uses it (`m` common-mode geometry, `||m||/||diff||`
hardness, leave-one-out re-centering, etc.) needs to be regenerated.
Treat as its own thread, don't bundle.

The remaining 5 near-miss pairs from the same study (relativist/absolutist,
casual/formal, systems_thinker/analytical, reductionist/holistic,
progressive/conservative) had y-axis sort orders that cleanly matched the
pair name — no rewrite needed.


