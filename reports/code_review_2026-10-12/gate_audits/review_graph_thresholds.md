# Gate 8: R1, the review graph's thresholds

Audit of 2026-10-12 (Opus agent) under the protocol of [README.md](./README.md).  No paid call was made.  Every
cosine below comes from the [embedding cache](../../../data/candidates/cache/embeddings/) through the CLI's own
`query_vectors` ([review_graph.py](../../../data_analysis/gap_generation/review_graph.py):93-114, cache only, no
embedding, no network), and reproduces the 6,001 recorded candidate-edge cosines of `review_tda_1` to within 5e-7
and its candidate edges exactly.  The scratch scripts that did the counting are not kept; every count can be
rebuilt from the files linked here.

## Verdict in brief

**Doing what was intended, but improvable.**  Roger's own decisions are the reference: of the 490 pairs of terms
he put in the same resolution in the TDA review, **none** was lost at the overlap floor (0.35); 106 (22%) were never
read because neither term had the other among its 10 nearest (k), and 87 (18%) were read below the cut-off,
almost all of them a Sonnet 2 that Opus is never asked to check.

- **Overlap floor 0.35: in the right place.**  Below it the relation call already sends on only 7% of candidate
  edges, and of those about 1 in 30 is one concept; moving it costs or saves cents.
- **k = 10: not supported for candidate pairs.**  It was carried over from M3's corpus retrieval and ignores how
  dense a region is.  In dense regions it cuts links inside one concept, which is what shatters the proposed groups
  and makes Roger reassemble them by hand (67 terms extended).  Keeping k = 10 and adding every pair at cosine 0.55
  or above costs about 21 cents per TDA-sized build and should add about 20 3-edges.
- **Cut-off 3: in the right place.**  3-only edges agree with Roger 69% of the time, 2s 34%, 4-edges 85%.  Its
  false joins follow corpus boundaries, not edge levels, and cost Roger one drop click each.
- **`SHARE_BINS` and `SECOND_OPUS_SHARE` decide nothing** about which readings reach Opus; they only feed the cost
  estimate, which was 3.2 times the spend on the TDA build.

## Terms

R1, M3, the registry and the review app are defined in [escalations.md](../escalations.md), "Terms" (one correction:
R1's groups are maximal cliques at a cut-off, not connected groups); the wider vocabulary is in the
[glossary](../../trait_gap_generation/glossary.md).  Used here:

- **Kept candidate** (a **term** in the app): a registry row that M3 decided `new` or `grey` in the batches a build
  names.
- **Cosine**: the cosine of two candidates' query embeddings (the gloss cut to 14 words, as M3 embeds it) in M3's
  covered space, so on M3's scale.
- **Candidate edge**: a pair in which at least one candidate lists the other among its k nearest kept candidates at
  cosine 0.25 or above.
- **Relation call**: one Haiku 5.5 call per candidate that labels each listed neighbour `similar`, `opposed`,
  `unrelated` or `unsure`.  An edge goes on to be read when either side says similar or unsure.
- **Overlap call**, **rubric A**: one Sonnet 5.5 call per pair and direction, scoring 0 to 4 how far the two are one
  concept (3: "the same concept, differing only in scope, degree or emphasis"; 4: either label could replace the
  other), with Opus 5.5 reading again on Sonnet's 3, 4 or unsure.  Readings are written Sonnet/Opus, `-` where Opus
  was not asked, first direction then second.
- **3-edge**, **4-edge**: both directions read 3 or above (resp. 4), the relation not opposed.
- **Merged group**: a maximal clique of 4-edges (merged by default).  **Proposed group**: a maximal clique of 3-edges
  not inside a merged group (pre-assembled, merged when Roger accepts).
- **Leftovers**, **extend**, **distinct**, **drop**: once a group is resolved, the app lists as leftovers the
  unhandled candidates that share a merged or proposed group with any of its members; `extend` adds one under the
  same resolution, `distinct` marks it as not this group.  `drop` removes a member from a group before it is
  resolved.
- **Same-resolution pair**: two terms Roger handled that ended in the same resolved group, or in groups merged into
  the same corpus trait.

Candidate labels (obstinate, bullheaded, ...) are registry rows with no instruction file; the promoted ones are
entries of [seed_queue.json](../../../data/seed_queue.json).  Corpus traits link to their instruction files.

## Two corrections to the brief

1. **"8,970 of 9,782 candidate edges at or above the floor"** is in no record.  The TDA build's
   [run.json](../../../data/candidates/review/review_tda_1/run.json) plan says **6,001 candidate edges, 5,586 at
   cosine 0.35 or above** (8,693 neighbour slots, 3,309 edges listed by one side only), and
   [graph.json](../../../data/candidates/review/review_tda_1/graph.json) has exactly those 6,001.  Among all pairs of
   the 871 candidates, 53,268 are at 0.25 or above and 16,318 at 0.35 or above; neither pair of numbers is the
   brief's.
2. **`SHARE_BINS` and `SECOND_OPUS_SHARE` do not choose which readings reach Opus.**  They are read only by the
   estimate ([review_graph.py](../../../assistant_axis/gapgen/review_graph.py):931-1017 and 1107).  The routing is
   M3's `sonnet_action` at cut-off 4 ([novelty.py](../../../assistant_axis/gapgen/novelty.py):732-762, applied at
   [novelty_runner.py](../../../assistant_axis/gapgen/novelty_runner.py):825): Sonnet 4, Opus decides; Sonnet 3, Opus
   checks; unsure, Opus replaces; Sonnet 0 to 2, never.

## 1. The rule, from the code

For a pair of kept candidates; line numbers in [review_graph.py](../../../assistant_axis/gapgen/review_graph.py)
unless another file is named.

| step | rule | constants | where | a pair that fails |
|---|---|---|---|---|
| retrieval | each kept candidate's k nearest other kept candidates by cosine, stopping at the first below the floor; an edge when either lists the other | `DEFAULT_K` 10; `DEFAULT_COSINE_FLOOR` 0.25 (M3's, [novelty.py](../../../assistant_axis/gapgen/novelty.py):79) | :85, :87, `nearest_candidates` :504-523, `plan_graph` :526-552; CLI flags `--k`, `--cosine-floor` ([CLI](../../../data_analysis/gap_generation/review_graph.py):517-519) | no edge: never typed or read, and absent from the card's neighbour list |
| relation | one Haiku call per candidate; `unsure` re-asked of Sonnet; the two sides combined | `OVERLAP_RELATIONS` similar, unsure, mixed | :99, `combine_relations` :388-401, `run_relations` :601-638 | `not_similar`: an edge (neighbour list, opposed links), never read |
| overlap floor | read only at cosine 0.35 or above | `DEFAULT_OVERLAP_FLOOR` 0.35 | :89, `overlap_pairs` :555-563; `--overlap-floor` (CLI :520) | `below_floor`: an edge, never read |
| first direction | Sonnet, Opus on Sonnet 3, 4 or unsure (the rule at cut-off 4, rule set `m3_rules_2`) | `CUT_OFF` 4 (`PairCandidate.cut_off` :424-429); `RULES` :84 | `build_graph` :643-663; [novelty.py](../../../assistant_axis/gapgen/novelty.py):732-762 | one reading; a Sonnet 0-2 is final |
| second direction | read only where the first direction reads at the proposed cut-off or above | `DEFAULT_PROPOSED_CUT_OFF` 3 (`--proposed-cut-off`, choices 3 or 4 only: CLI :522) | `needs_second` :379-385, :664-668 | `first`: one reading, no 3-edge |
| edges | 4-edge: both directions four; 3-edge: both at 3 or above under M3's rule at 3; relation not opposed | | `reading_of` :350-372, :775-777 | in no group |
| groups | merged = maximal cliques of 4-edges; proposed = maximal cliques of 3-edges not inside a merged group | | `maximal_cliques` :297-319, `proposed_groups` :322-326, :819-820 | ungrouped (a singleton card) |
| estimate | per cosine bin, the shares M3 measured on candidate-to-corpus pairs (a bin with fewer than 10 observations takes 1.0); the second direction's Opus share assumed 1.0 | `SHARE_BINS` (0.35, 0.45, 0.55, 0.65), `MIN_SHARE_OBS` 10, `SECOND_OPUS_SHARE` 1.0 | :105-109, `measured_shares` :931-970, `estimate_overlap` :990-1017, :1107 | nothing is discarded; an estimate over the cap refuses the whole build |

Two consequences of the rule worth stating:

- **A Sonnet 2 is final.**  Opus is asked under the rule at cut-off 4, where a 2 is "continue".  At the proposed
  cut-off 3, M3's own rule would have Opus check a 2 (`opus_check` at c - 1), so a 4-edge has an Opus path up from a
  Sonnet 3 (Opus raised 252 of 1,337 Sonnet 3s to 4 in the TDA build) while a 3-edge has none from a Sonnet 2.  The
  module says so (:38-41); it is a choice, not a bug.
- **The leftovers pass only reaches what the graph grouped.**  `extend` and `distinct` are offered for leftovers
  only ([decisions.py](../../../assistant_axis/gapgen/review_app/decisions.py) `leftovers` :924-951;
  [app.js](../../../assistant_axis/gapgen/review_app/static/app.js):216-220), so a term that shares no merged or
  proposed group with any member can be joined only by `merge_in` while the group is open
  ([decisions.py](../../../assistant_axis/gapgen/review_app/decisions.py):475-494) or
  by resolving it separately to the same target.

## 2. The intent

- **The floor**, decision 11 of [coding_plan_review.md](../../trait_gap_generation/coding_plan_review.md): "A cosine
  floor of 0.35 on R1's overlap calls, calibrated on the 4,334 recorded M3 readings with a cosine and a final value:
  below 0.35, 0.1% read 4 and 3.9% read 3 or above (1,994 readings); ... so the floor keeps about 98% of the
  4-edges and, with k = 10, halves the overlap stage against the worst case.  The relation call still sees every
  retrieved neighbour (it is cheap and types the opposed edges)."  A derivation is recorded, but on
  candidate-to-corpus readings and for 4-edges, before decision 12 lowered the group cut-off to 3.
- **The cut-off**, decision 12: "**proposed groups** are cliques of 3-edges (both directions 3 or above) ...
  Rubric A's 3 is 'the same concept, differing only in scope, degree or emphasis', which is the
  choose-the-best-word case; a 2 stays a neighbour."  Derived from the R1 pilot
  ([readout.md](../../../data/candidates/review/review_pilots_1/readout.md): 19 4-cliques covering 35 of 325
  candidates; at 3, 57 cliques covering 103).
- **k**: section 2 says only "k = 10 among candidates, retrieval floor 0.25 as M3's".  **No derivation for R1.**  M3's
  k = 10 was measured for a different task, retrieving one given corpus trait among 932 (OpenAI's top 10 holds the
  trait for 0.972-0.978 of the M1 glosses: [QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md) item 26,
  [pilot_m2_readout.md](../../trait_gap_generation/pilot_m2_readout.md) Round 4).  R1 has to find every member of a
  candidate concept, which in the TDA batch can have twenty.
- **The estimate's shares**: "A bin with fewer than `min_obs` observations takes 1.0, so that the estimate errs
  high" ([review_graph.py](../../../assistant_axis/gapgen/review_graph.py):934-935).  The pilot readout already found the estimate 2.7 times the spend and proposed
  taking the shares from R1's own records ("that is not built").
- **The gate as a whole** ([README.md](./README.md)): "show Roger every pair that might be one concept, and no more
  than that".

## 3. The recorded discard, reproduced

**The TDA build** ([review_tda_1/](../../../data/candidates/review/review_tda_1/): 871 kept candidates, all `new`
from M3 batch `2026-10-10-tda_censuses`; 908 covered candidates shown greyed; cost $4.9965 by
[usage.json](../../../data/candidates/review/review_tda_1/usage.json)).  Where the 378,885 pairs of kept candidates
went:

| stage | pairs | of which at cosine 0.35 or above |
|---|---|---|
| all pairs of kept candidates | 378,885 | 16,318 |
| below the retrieval floor 0.25 | 325,617 | 0 |
| 0.25 or above, in neither candidate's 10 nearest (the k cut) | 47,267 | **10,732** (1,668 at 0.45 or above, 172 at 0.55 or above) |
| candidate edges | 6,001 | 5,586 |
| ... relation not similar (unrelated 2,812, opposed 280) | 3,092 | 2,708 |
| ... similar, unsure or mixed but below the overlap floor | **31** | 0 |
| ... read in the first direction only (first reading below 3) | 2,107 | 2,107 |
| ... read both ways | 771 | 771 |
| ... of which 3-edges / 4-edges | 681 / 192 | 681 / 192 |

Groups: 129 merged, 257 proposed (covering 435 candidates, 183 of them in several), 357 candidates in neither.

By cosine bin (TDA; "3+ first" counts first-direction final readings of 3 or 4; cost per pair read includes its Opus
call and second direction):

| cosine | all pairs | candidate edges | relation similar | read | cost per pair read | 3+ first | 3-edges | 4-edges |
|---|---|---|---|---|---|---|---|---|
| 0.25-0.30 | 23,917 | 94 | 6 (6%) | 0 | | | | |
| 0.30-0.35 | 13,033 | 321 | 25 (8%) | 0 | | | | |
| 0.35-0.40 | 7,032 | 711 | 122 (17%) | 122 | 0.072 c | 3 | 2 | 0 |
| 0.40-0.45 | 3,781 | 1,038 | 273 (26%) | 273 | 0.073 c | 10 | 7 | 1 |
| 0.45-0.55 | 3,363 | 1,867 | 838 (45%) | 838 | 0.100 c | 87 | 70 | 7 |
| 0.55-0.65 | 1,298 | 1,145 | 866 (76%) | 866 | 0.146 c | 192 | 164 | 24 |
| 0.65 and above | 844 | 825 | 779 (94%) | 779 | 0.298 c | 479 | 438 | 160 |

The lowest 3-edge is at 0.372 and the lowest 4-edge at 0.442 (malleable / moldable, a pair Roger kept together).

**Every review session** (the floor's discard and the band just above it; "similar" includes unsure and mixed):

| session | kept | candidate edges | at 0.35+ | similar, below the floor | read at 0.35-0.45 | 3-edges there | cost of those reads | build cost |
|---|---|---|---|---|---|---|---|---|
| [review_tda_1](../../../data/candidates/review/review_tda_1/run.json) | 871 | 6,001 | 5,586 | 31 | 395 | 9 | 28.8 c | $4.997 |
| [review_pilots_1](../../../data/candidates/review/review_pilots_1/run.json) | 330 | 2,183 | 1,537 | 85 | 222 | 3 | 14.9 c | $1.975 |
| [review_allport_pilots_1](../../../data/candidates/review/review_allport_pilots_1/run.json) | 107 | 493 | 117 | 41 | 18 | 0 | 1.1 c | $0.065 |
| [review_states_tda_1](../../../data/candidates/review/review_states_tda_1/run.json) | 20 | 49 | 20 | 8 | 7 | 0 | 0.4 c | $0.017 |
| [review_states_v4](../../../data/candidates/review/review_states_v4/run.json) | 19 | 28 | 9 | 2 | 2 | 0 | 0.1 c | $0.008 |
| [review_states_renamed_w23](../../../data/candidates/review/review_states_renamed_w23/run.json) | 19 | 19 | 7 | 0 | 1 | 0 | 0.1 c | $0.018 |
| [review_physical_tda_1](../../../data/candidates/review/review_physical_tda_1/run.json) | 16 | 61 | 20 | 0 | 3 | 0 | 0.2 c | $0.010 |
| [review_physical_pilots_1](../../../data/candidates/review/review_physical_pilots_1/run.json) | 4 | 2 | 1 | 0 | 0 | 0 | 0 | $0.0004 |
| **all** | | | | **167** | **648** | **12** | **about 46 c** | |

"c" is US cents at the Batches API rates the TDA build paid.  The pilot sessions' cosines, recomputed today, differ
from their recorded ones by up to 0.005 because the corpus centring has moved since those builds; the recorded
values are used wherever an edge exists.

## 4. Samples and the reference

### 4a. Roger's decisions, the reference

**What there is.**  [decisions.jsonl](../../../data/candidates/review/review_tda_1/decisions.jsonl) of the TDA review:
354 events on 2026-10-11 (84 active minutes), 68 groups resolved, **204 of the 871 terms handled** (106 merged into
corpus traits, 97 in promoted groups, 1 rejected), 67 terms extended, 76 marked distinct, 6 drops, 3 events undone.
[decisions.before_leftovers_2026-10-11.jsonl](../../../data/candidates/review/review_tda_1/decisions.before_leftovers_2026-10-11.jsonl)
(21 events, a first attempt set aside) is used only for its hand merges.  The only other log,
[review_states_v4/decisions.jsonl](../../../data/candidates/review/review_states_v4/decisions.jsonl) (13 events: one
merged group and singletons), has no extend, distinct or drop and gives no rate.

**The label.**  A pair of handled terms is *same* when both ended in the same resolution (the same promoted group, or
groups merged into the same corpus trait), *different* otherwise: 490 same pairs, 20,216 different.  Two caveats.
The label is coarser than rubric A: a merge into a broad trait makes "also covered" pairs the same (the
[arrogant](../../../data/traits/instructions/arrogant.json) group holds conceited and sneering, cosine 0.24).  And
the review went largest groups first, so the handled terms are the dense clusters: 23 of them ended in
[unyielding](../../../data/traits/instructions/unyielding.json) or
[strong_willed](../../../data/traits/instructions/strong_willed.json).  `distinct` is **not** used as a label:
Roger marked wily distinct from the [scheming](../../../data/traits/instructions/scheming.json) group and then merged
it into [scheming](../../../data/traits/instructions/scheming.json) on its own, and did the same with unwillful and unsteadfast against
[submissive](../../../data/traits/instructions/submissive.json); it means "not in this group now".

**Roger's 490 same pairs, by what the graph did with them** (95% Clopper-Pearson intervals):

| graph status of the pair | pairs | share | 95% interval | in promoted groups (181) | in merges into a trait (309) |
|---|---|---|---|---|---|
| 4-edge | 102 | 20.8% | | 46 | 56 |
| 3-edge (not 4) | 180 | 36.7% | | 80 | 100 |
| **read, below 3 (the cut-off)** | **87** | 17.8% | 14.5-21.4% | 21 | 66 |
| **no edge: outside both 10 nearest (k)** | **106** | 21.6% | 18.1-25.6% | 24 | 82 |
| edge, relation not similar | 9 | 1.8% | 0.8-3.5% | 5 | 4 |
| no edge: below 0.25 | 6 | 1.2% | 0.5-2.6% | 5 | 1 |
| **similar, below the overlap floor 0.35** | **0** | 0% | 0-0.75% | 0 | 0 |

- **The cut-off misses**: of the 75 first-direction ones, 64 read `2/-` (a Sonnet 2 that Opus never saw), 10 read
  `3/2` (Opus lowered a 3), 1 read `1/-`; the 12 second-direction ones mostly read `3/3, 2/-`.
- **The k misses**: cosine median 0.473 (0.264 to 0.711); the nearer of the two ranks median 17 (11 to 106).  By
  group: the [strong_willed](../../../data/traits/instructions/strong_willed.json) merge 39, the [arrogant](../../../data/traits/instructions/arrogant.json) merge 19, the promoted irrestrainable group 19, [scheming](../../../data/traits/instructions/scheming.json) 10.  They
  would be candidate edges at k = 15 for 41 of the 106, at k = 20 for 67, under a radius rule at cosine 0.55 for 26,
  at 0.50 for 45.
- **Below 0.25**: conceited / sneering (0.240) and five pairs of the irrestrainable group (recalcitrant against
  irrestrainable, unbridled and unreined; ungovernable / unreined; unreined / untamable; 0.18 to 0.24): broad "also
  covered" joins, not one concept at rubric A's 3.  No threshold should reach them.
- **The relation misses**, for the relation-call audit rather than this one: obscene / risque (0.566) and raunchy /
  risque (0.552) in one promoted group; overproud / stuck-up (0.645), disdainful / overproud (0.559) in the [arrogant](../../../data/traits/instructions/arrogant.json)
  merge, all answered `unrelated`.

**The terms Roger joined by hand.**  In the final log, **67 terms extended**: 64 had a 3- or 4-edge to at least one
member already resolved (the leftovers pass only offers those); the other 3 (unmalleable to the [strong_willed](../../../data/traits/instructions/strong_willed.json) group,
unsteadfast to the [submissive](../../../data/traits/instructions/submissive.json) group, uncultivated to the unladylike group) came through a member another group had
handled, at cosines 0.641, 0.393 and 0.444 to the resolved members, all outside k = 10.  Over the 327 pairs
(extended term, member resolved before it):

| status | pairs | cosine median (range) |
|---|---|---|
| 4-edge | 30 | 0.724 (0.535-0.888) |
| 3-edge | 100 | 0.680 (0.483-0.892) |
| read below 3 | 80 | 0.627 first direction, 0.641 second (0.410-0.806) |
| outside k = 10 | 102 | 0.471 (0.264-0.711) |
| relation not similar | 9 | 0.520 (0.501-0.645) |
| below 0.25 | 6 | 0.225 (0.180-0.240) |
| below the overlap floor | 0 | |

So every extended term was read against some member, and most were never read against the rest: 31% of the links
inside the groups Roger assembled were cut by k and 24% by the cut-off.  In the set-aside first session Roger also
pulled two terms into the [unyielding](../../../data/traits/instructions/unyielding.json) group with `merge_in` that the graph had grouped with **none** of its six
members: overrigid (cosine 0.31 to 0.41; read `2/-` against obstinate and pigheaded, `3/3, 3/2` against bullheaded,
outside k against three) and doctrinaire (0.46 to 0.55; relation `unrelated` against bullheaded, obstinate and
pigheaded, outside k against three).  In the redo he left both out and marked overrigid distinct from the
[strong_willed](../../../data/traits/instructions/strong_willed.json) group, so these two are not a stable label.

**Terms the leftovers pass could not join**: pairs with the same target resolved in different groups.  17 pairs, in
three pairs of groups: wily against the [scheming](../../../data/traits/instructions/scheming.json) group (4-edges to artful, crafty and foxy, so it was offered and
marked distinct first); weak-minded against unwillful, unsteadfast and leadable ([submissive](../../../data/traits/instructions/submissive.json); 3-edges, read `2/-`
for leadable); fierce and ferocious against brutish, savage and overviolent (both merged into
[violent](../../../data/traits/instructions/violent.json): read `2/-` four times, `3/3, 2/-` once, outside k once).
Among the 29 singletons Roger resolved, none was resolved to a target another group also used.

**False joins.**  381 3- or 4-edges join two handled terms; **99 of them join terms Roger resolved differently**
(26.0%, 21.7-30.7%):

| edge | pairs | different | share different (95%) |
|---|---|---|---|
| 4-edge | 120 | 18 | 15.0% (9.1-22.7%) |
| 3-edge, one direction read 4 | 36 | 7 | 19% |
| 3-edge, no direction read 4 | 225 | 74 | 33% |
| read but below 3 (for comparison) | 254 | 167 | 66% (60-72%) |

By cosine the share different is 43% at 0.35-0.55 (37 pairs) and 23-25% above.  Of the 99: 51 join terms merged into
two different corpus traits, 30 a merged term and a promoted one, 18 two promoted groups.  Groups fully handled:
merged 9 of 63 split (14%, 7-25%), proposed 38 of 87 (44%, 33-55%; overlapping groups each counted).  **The
proposed groups Roger split** were split along corpus boundaries: [unyielding](../../../data/traits/instructions/unyielding.json) against [strong_willed](../../../data/traits/instructions/strong_willed.json) (unalterable,
unchangeable, unmodifiable, unmalleable going to [strong_willed](../../../data/traits/instructions/strong_willed.json)), [accommodating](../../../data/traits/instructions/accommodating.json)
against [submissive](../../../data/traits/instructions/submissive.json) against [obedient](../../../data/traits/instructions/obedient.json),
[confrontational](../../../data/traits/instructions/confrontational.json) against [violent](../../../data/traits/instructions/violent.json), [scheming](../../../data/traits/instructions/scheming.json) against
[deceitful](../../../data/traits/instructions/deceitful.json), the promoted irrestrainable against
[impulsive](../../../data/traits/instructions/impulsive.json) and [rebellious](../../../data/traits/instructions/rebellious.json),
and nosy against meddling (two promotions, at cosine 0.95 and 0.90).  Their edge levels do not predict the split:
the six drops (unmodifiable and unalterable from proposed group 0, weak-minded from 15, unrestrained from 22,
mocking and snide from 38) each had a 3- or 4-edge to every other member, and four of the six had at least one
4-edge (unmodifiable / unmovable `4/4, 4/4`; weak-minded three; unrestrained three; mocking / derisive `4/4, 4/4`,
and mocking was extended back into the same group later).

### 4b. Sample A: discarded by the floor

**Selection**: every candidate edge whose relation sent it on (similar, unsure or mixed) and whose cosine is below
0.35 (`overlap: below_floor`), 167 in the five sessions that have any; 60 drawn stratified by session (24 of TDA's
31, 20 of the pilots' 85, 10 of Allport's 41, 4 of states_tda_1's 8, both of states_v4's 2), each population sorted by
key pair, `random.Random(20261012)`.  **Verdict** (mine, against the intent): would rubric A plausibly read 3 or
above both ways?  *one concept*: yes; *borderline*: a 2 a reader could argue up; *distinct*: related at most.  It rests
on the two glosses as R1's prompts carried them (the nodes of each session's graph.json, for example
[review_tda_1/graph.json](../../../data/candidates/review/review_tda_1/graph.json) and
[review_pilots_1/graph.json](../../../data/candidates/review/review_pilots_1/graph.json)).  Roger's resolution is
quoted where both terms were handled.

| # | run | pair | cosine | relation | verdict | rests on (the two glosses) |
|---|---|---|---|---|---|---|
| A1 | tda_1 | inconvincible / unpersuasive | 0.343 | similar | distinct | unmoved by others' arguments vs failing to move others: opposite roles |
| A2 | tda_1 | acceptant / ultrademocratic | 0.317 | similar | distinct | tolerance of persons vs a political stance on equal say |
| A3 | tda_1 | prophetic / visionary | 0.263 | similar | distinct | foretelling events vs imagining possibilities |
| A4 | tda_1 | aphoristic / felicitous | 0.349 | similar | distinct | speaking in maxims vs apt wording |
| A5 | tda_1 | self-deluding / unrealistic | 0.335 | similar | borderline | both hold beliefs against the evidence, about oneself vs about prospects |
| A6 | tda_1 | seditious / unsubmissive | 0.339 | similar | distinct | inciting others to revolt vs personally refusing to obey |
| A7 | tda_1 | minimizing / unsevere | 0.321 | similar | distinct | playing problems down vs lenient judgment |
| A8 | tda_1 | many-sided / zestful | 0.289 | similar | distinct | breadth of talents vs eagerness |
| A9 | tda_1 | overcautious / overfearful | 0.340 | similar | borderline | excess hedging vs standing dread of harm; Roger sent them to different traits ([cautious](../../../data/traits/instructions/cautious.json), [cowardly](../../../data/traits/instructions/cowardly.json)) |
| A10 | tda_1 | average / normal | 0.340 | similar | distinct | middling work vs conventional manner |
| A11 | tda_1 | enlightened / holy | 0.316 | similar | distinct | spiritual insight vs moral purity |
| A12 | tda_1 | imitative / suggestible | 0.321 | similar | borderline | copying manners vs taking up others' views |
| A13 | tda_1 | self-correcting / self-examining | 0.312 | similar | borderline | fixing errors openly vs introspecting on motives |
| A14 | tda_1 | disclosing / unreserved | 0.348 | similar | borderline | volunteering private facts vs speaking one's mind |
| A15 | tda_1 | nonimitative / self-taught | 0.345 | similar | distinct | refusing to copy vs learning without schooling |
| A16 | tda_1 | pedestrian / platitudinous | 0.253 | similar | borderline | uninspired ordinariness vs stock phrases (a narrower case) |
| A17 | tda_1 | misleadable / undiscerning | 0.318 | similar | borderline | taken in by false claims vs unable to tell good from poor |
| A18 | tda_1 | familiar / regular | 0.270 | similar | distinct | chummy tone vs being a regular customer (another sense) |
| A19 | tda_1 | faithless / hypocritical | 0.350 | similar | distinct | breaking commitments vs professing unpractised virtues |
| A20 | tda_1 | gauche / maladjusted | 0.341 | similar | borderline | lacking polish vs out of step with one's setting |
| A21 | tda_1 | platitudinous / sententious | 0.286 | similar | **one concept** | both deal in trite sayings; sententious adds the moralising (emphasis) |
| A22 | tda_1 | educable / persuadable | 0.331 | similar | borderline | able to learn vs changing one's mind on reasons |
| A23 | tda_1 | keen / many-sided | 0.310 | similar | distinct | eagerness vs breadth of talents |
| A24 | tda_1 | overcritical / unconstructive | 0.340 | similar | borderline | faulting everything vs criticising without alternatives |
| A25 | pilots_1 | commandeering / undemocratic | 0.319 | similar | distinct | seizing things vs a political stance |
| A26 | pilots_1 | high-minded / unmercenary | 0.325 | similar | borderline | lofty principles vs refusing profit against what is right |
| A27 | pilots_1 | flighty / imprudent | 0.346 | similar | distinct | changeable interests vs reckless risk |
| A28 | pilots_1 | so-so / unprofessional | 0.334 | similar | distinct | middling skill vs breaches of workplace standards |
| A29 | pilots_1 | reliant / slavish | 0.311 | similar | distinct | leaning on others vs obeying without question |
| A30 | pilots_1 | irreligious / unliterary | 0.322 | similar | distinct | no faith vs no reading: the relation call's similar is wrong |
| A31 | pilots_1 | commandeering / imperialistic | 0.331 | similar | borderline | seizing control of things vs seeking power over people |
| A32 | pilots_1 | fraudulent / predatory | 0.329 | similar | borderline | cheating by deception vs preying on the vulnerable |
| A33 | pilots_1 | conceding / receptive | 0.345 | similar | borderline | admitting a valid point vs open to new ideas |
| A34 | pilots_1 | conceding / reasonable | 0.349 | similar | distinct | admitting a point vs fair-minded judgment |
| A35 | pilots_1 | imprudent / unthorough | 0.330 | similar | distinct | reckless vs careless work |
| A36 | pilots_1 | loving / overcaring | 0.326 | similar | borderline | warm regard vs smothering fuss (degree and valence) |
| A37 | pilots_1 | reactionary / unreceptive | 0.325 | similar | distinct | politics of restoration vs closed to suggestions |
| A38 | pilots_1 | unique / willful | 0.330 | similar | distinct | singular character vs holding one's course |
| A39 | pilots_1 | commandeering / indocile | 0.296 | similar | distinct | seizing control vs refusing to be controlled |
| A40 | pilots_1 | strong-willed / unique | 0.339 | similar | distinct | holding one's goals vs singular character |
| A41 | pilots_1 | chameleonlike / double-faced | 0.322 | similar | borderline | opinions shift to match company vs feigned agreement |
| A42 | pilots_1 | aesthetic / classy | 0.327 | similar | borderline | prizing beauty vs refined personal style |
| A43 | pilots_1 | rapacious / worldly-minded | 0.323 | similar | borderline | grasping greed vs materialist values |
| A44 | pilots_1 | defective / hit-or-miss | 0.341 | similar | distinct | flawed character vs uneven output |
| A45 | allport_pilots_1 | hawk / lethal | 0.331 | similar | distinct | hard-line policy vs deadly skill |
| A46 | allport_pilots_1 | esteeming / uxorious | 0.323 | similar | distinct | esteem for others vs doting husband |
| A47 | allport_pilots_1 | paltering / wordmonger | 0.345 | similar | borderline | misleading true statements vs slick misleading phrasing |
| A48 | allport_pilots_1 | ossifying / unimproved | 0.306 | similar | distinct | growing rigid vs not improving |
| A49 | allport_pilots_1 | chatterer / gabbling | 0.346 | similar | borderline | idle small talk vs incoherent babble |
| A50 | allport_pilots_1 | infrangible / martyring | 0.320 | similar | distinct | unbreakable resolve vs self-sacrifice |
| A51 | allport_pilots_1 | mixable / silky | 0.303 | similar | distinct | sociable vs suave |
| A52 | allport_pilots_1 | bestriding / distractive | 0.317 | similar | distinct | dominating a room vs distracting others |
| A53 | allport_pilots_1 | draconian / reproving | 0.328 | similar | distinct | merciless enforcement vs verbal rebuke |
| A54 | allport_pilots_1 | bardy / bestriding | 0.290 | similar | distinct | presumptuous speech vs dominating a room |
| A55 | states_tda_1 | glum / pouty | 0.308 | similar | borderline | gloomy vs sulking |
| A56 | states_tda_1 | disappointed / wistful | 0.264 | similar | distinct | let down vs longing for the past |
| A57 | states_tda_1 | dejected / glum | 0.342 | similar | **one concept** | both a downcast, low mood |
| A58 | states_tda_1 | brooding / wistful | 0.273 | similar | borderline | ruminating on grievances vs longing for the past |
| A59 | states_v4 | heartsick / tearful | 0.307 | similar | borderline | lasting grief vs quick tears |
| A60 | states_v4 | inconsolable / tearful | 0.345 | similar | borderline | inconsolable breakdowns vs quick tears |

**Sample A: 2 one concept, 24 borderline, 34 distinct.**

### 4c. Sample B: kept, read just above the floor

**Selection**: every pair read in the first direction at cosine 0.35 to 0.45 in the same five sessions (644); 40 drawn
(22 TDA, 12 pilots, 4 Allport, 1 each states_tda_1 and states_v4), the same generator continued after sample A.
**Reference first**: the models' readings, none 3 or above; my reading second.

| # | run | pair | cosine | first reading (Sonnet/Opus) | verdict | rests on (the two glosses) |
|---|---|---|---|---|---|---|
| B1 | tda_1 | considerate / warm-hearted | 0.381 | 2/- | borderline | attentive to needs vs openly affectionate |
| B2 | tda_1 | approachable / hospitable | 0.437 | 1/- | distinct | easy to talk to vs welcoming guests |
| B3 | tda_1 | brawlsome / explosive | 0.392 | 2/- | distinct | picking fights vs sudden temper |
| B4 | tda_1 | ferocious / scary | 0.433 | 2/- | distinct | hostile attacker vs frightening presence |
| B5 | tda_1 | humane / unhardened | 0.444 | 2/- | distinct | kindness to others vs staying tender oneself |
| B6 | tda_1 | malleable / misleadable | 0.419 | 1/- | borderline | yields to pressure vs believes falsehoods |
| B7 | tda_1 | ambiguous / oversubtle | 0.446 | 2/- | borderline | vague vs too indirect |
| B8 | tda_1 | skillful / unerring | 0.379 | 2/- | distinct | expert vs never wrong |
| B9 | tda_1 | inexperienced / unaccomplished | 0.354 | 2/- | borderline | new to the field vs no record of achievement |
| B10 | tda_1 | considerate / humane | 0.427 | 2/- | borderline | attentive to needs vs compassion to the difficult |
| B11 | tda_1 | fatherly / mentoring | 0.448 | 2/- | borderline | protective guidance vs mentoring growth |
| B12 | tda_1 | hardheaded / unpersuasive | 0.362 | 0/- | distinct | unmoved vs failing to move others |
| B13 | tda_1 | complex / enigmatic | 0.353 | 1/- | distinct | many-layered vs secretive |
| B14 | tda_1 | ultrademocratic / unbigoted | 0.381 | 1/- | distinct | political stance vs absence of prejudice |
| B15 | tda_1 | influential / magisterial | 0.447 | 2/- | distinct | weight with others vs commanding bearing |
| B16 | tda_1 | considerate / neighborly | 0.443 | 2/- | borderline | attentive to needs vs practical help to neighbours |
| B17 | tda_1 | overforward / unmaidenly | 0.411 | 2/- | borderline | unearned familiarity vs immodest forwardness (gendered) |
| B18 | tda_1 | assiduous / overstudious | 0.361 | 1/- | distinct | steady diligence vs excessive study |
| B19 | tda_1 | good-for-nothing / overrelaxed | 0.402 | 2/- | borderline | lazy and useless vs letting duties slide |
| B20 | tda_1 | autocratic / overstepping | 0.415 | 2/- | borderline | overriding others vs exceeding one's authority; Roger: different ([dominant](../../../data/traits/instructions/dominant.json); overstepping promoted) |
| B21 | tda_1 | ordinary / unpretending | 0.399 | 1/- | distinct | unremarkable vs unassuming |
| B22 | tda_1 | larcenous / piggish | 0.432 | 1/- | distinct | stealing vs gluttony |
| B23 | pilots_1 | boyish / bright-eyed | 0.429 | 2/- | distinct | playful vs eager |
| B24 | pilots_1 | affectionate / overcaring | 0.436 | 1/- | borderline | warm regard vs smothering fuss |
| B25 | pilots_1 | flighty / namby-pamby | 0.369 | 1/- | distinct | changeable vs giving way under pressure |
| B26 | pilots_1 | unmercenary / unpaid | 0.382 | 1/- | distinct | principle over profit vs unpaid work |
| B27 | pilots_1 | crusty / unpersonable | 0.434 | 2/- | borderline | gruff impatience vs cold curtness |
| B28 | pilots_1 | discordant / impossible | 0.385 | 2/- | distinct | quarrelsome vs blocking compromise |
| B29 | pilots_1 | controversial / discordant | 0.393 | 2/- | distinct | raising divisive views vs picking fights |
| B30 | pilots_1 | double-tongued / sketchy | 0.364 | 1/- | borderline | different stories to each listener vs murky dealings |
| B31 | pilots_1 | impractical / ultraintellectual | 0.394 | 1/- | distinct | unworldly idealism vs abstract analysis |
| B32 | pilots_1 | impossible / negative | 0.387 | 2/- | borderline | blocking compromise vs shooting ideas down |
| B33 | pilots_1 | double-faced / sketchy | 0.353 | 1/- | borderline | feigned agreement vs murky dealings |
| B34 | pilots_1 | affectionate / kindhearted | 0.428 | 2/- | borderline | warm regard vs generous kindness |
| B35 | allport_pilots_1 | bunglesome / galumphing | 0.434 | 2/- | borderline | clumsy hands vs clumsy gait |
| B36 | allport_pilots_1 | equal / esteeming | 0.362 | 1/- | distinct | treating as a peer vs admiring others |
| B37 | allport_pilots_1 | stagnant / unreformed | 0.428 | 1/- | distinct | no growth vs unrepentant habits |
| B38 | allport_pilots_1 | befouling / evil-eyed | 0.410 | 1/- | distinct | corrupting vs a cursed gaze |
| B39 | states_tda_1 | disappointed / mopey | 0.353 | 2/- | borderline | let down vs low spirits |
| B40 | states_v4 | liable / unpunished | 0.403 | 1/- | distinct | answerable for a debt vs an unpunished wrong |

**Sample B: 0 one concept, 18 borderline, 22 distinct.**

### 4d. Sample C: discarded by the k cut

**Selection**: pairs at cosine 0.45 or above that neither candidate lists among its 10 nearest: 1,668 in TDA and 33 in
the pilots (cosines and ranks recomputed; see the note under section 3); 40 drawn (30 TDA, 10 pilots), the same
generator continued after sample B.  "Nearer rank": the better of the two ranks (11 = just outside the 10 nearest).

| # | run | pair | cosine | nearer rank | verdict | rests on (the two glosses) |
|---|---|---|---|---|---|---|
| C1 | tda_1 | disputatious / uncooperative | 0.477 | 12 | distinct | habitual arguing vs refusing to cooperate |
| C2 | tda_1 | uncooperative / unsubduable | 0.610 | 18 | distinct | refusing to cooperate vs undefeatable resolve |
| C3 | tda_1 | unalterable / unswerving | 0.624 | 15 | borderline | fixed views vs fixed aims; Roger: same ([strong_willed](../../../data/traits/instructions/strong_willed.json)) |
| C4 | tda_1 | unmalleable / unmodifiable | 0.641 | 11 | **one concept** | both hold views fixed against pressure and argument; Roger: same ([strong_willed](../../../data/traits/instructions/strong_willed.json)) |
| C5 | tda_1 | concealing / unvocal | 0.469 | 19 | distinct | hiding a purpose vs not speaking |
| C6 | tda_1 | unpretending / unsullied | 0.462 | 28 | distinct | unassuming vs morally clean |
| C7 | tda_1 | boisterous / unwild | 0.455 | 17 | distinct | near opposites (rowdy vs calm) |
| C8 | tda_1 | dainty / tasteful | 0.458 | 16 | borderline | delicate grace vs restrained elegance |
| C9 | tda_1 | appeasing / unbelligerent | 0.469 | 13 | distinct | yielding to keep peace vs peaceable temper |
| C10 | tda_1 | contrary / unchangeable | 0.511 | 12 | borderline | taking the opposite side vs digging in |
| C11 | tda_1 | dictatorial / self-willed | 0.464 | 16 | distinct | giving orders vs keeping one's own way; Roger: different |
| C12 | tda_1 | uncooperative / unswayable | 0.580 | 25 | distinct | refusing to cooperate vs holding a view under pressure |
| C13 | tda_1 | undivertible / unmovable | 0.470 | 19 | borderline | fixed aim vs fixed opinions |
| C14 | tda_1 | inconvincible / recalcitrant | 0.484 | 34 | distinct | unmoved by argument vs defying authority; Roger: different |
| C15 | tda_1 | dedicated / soldierly | 0.480 | 15 | distinct | commitment to a cause vs military discipline |
| C16 | tda_1 | motherly / soothing | 0.472 | 12 | distinct | nurturing vs calming |
| C17 | tda_1 | aimful / ultrarefined | 0.461 | 12 | distinct | goal-directed vs over-refined taste |
| C18 | tda_1 | repressed / unswerving | 0.451 | 26 | distinct | suppressed feeling vs fixed aims; Roger: different |
| C19 | tda_1 | overrefined / unchanging | 0.477 | 11 | distinct | over-refined taste vs consistency |
| C20 | tda_1 | quiet / unpreaching | 0.460 | 20 | distinct | reserved vs not moralising |
| C21 | tda_1 | hardheaded / unshrinking | 0.562 | 13 | distinct | unmoved by argument vs facing danger |
| C22 | tda_1 | debonair / magisterial | 0.480 | 22 | distinct | charm vs authority |
| C23 | tda_1 | unchangeable / uncomplaisant | 0.519 | 25 | borderline | digging in vs declining to accommodate |
| C24 | tda_1 | sober-minded / unchanging | 0.461 | 16 | distinct | level-headed vs consistent |
| C25 | tda_1 | disorderly / uncurbable | 0.454 | 15 | borderline | rowdy disruption vs unrestrainable impulse |
| C26 | tda_1 | recalcitrant / strong-minded | 0.517 | 33 | distinct | defying authority vs holding a considered view; Roger: different |
| C27 | tda_1 | tight-lipped / unspeaking | 0.487 | 12 | borderline | secretive vs silent |
| C28 | tda_1 | obstinate / self-willed | 0.527 | 16 | **one concept** | both dig in against pressure and evidence; Roger: different ([unyielding](../../../data/traits/instructions/unyielding.json), [strong_willed](../../../data/traits/instructions/strong_willed.json)) |
| C29 | tda_1 | inelegant / tasteless | 0.507 | 18 | borderline | unpolished manner vs offensive bluntness; Roger: different |
| C30 | tda_1 | elegant / smooth-spoken | 0.525 | 14 | borderline | refined bearing vs polished speech |
| C31 | pilots_1 | loving / respectable | 0.454 | 12 | distinct | affection vs integrity |
| C32 | pilots_1 | suave / warmthless | 0.503 | 14 | distinct | charm vs coldness |
| C33 | pilots_1 | brotherly / charming | 0.457 | 11 | distinct | loyal warmth vs pleasant manner |
| C34 | pilots_1 | impersonal / suave | 0.504 | 13 | distinct | coldness vs charm |
| C35 | pilots_1 | frigid / unaggressive | 0.469 | 14 | distinct | coldness vs non-aggression |
| C36 | pilots_1 | angelic / inexpressive | 0.507 | 11 | distinct | moral goodness vs flat affect |
| C37 | pilots_1 | angelic / stately | 0.501 | 11 | distinct | moral goodness vs composure |
| C38 | pilots_1 | charming / ladylike | 0.476 | 11 | distinct | pleasant manner vs genteel propriety |
| C39 | pilots_1 | stately / urbane | 0.461 | 12 | borderline | dignified composure vs worldly polish |
| C40 | pilots_1 | imposing / restful | 0.457 | 11 | distinct | commanding presence vs soothing calm |

**Sample C: 2 one concept, 10 borderline, 28 distinct.**

Roger's resolutions cover 8 of the 30 TDA pairs: same for 2 (C3, C4, both [strong_willed](../../../data/traits/instructions/strong_willed.json)), different for 6, among them
C28 obstinate / self-willed, which I read as one concept and Roger split between [unyielding](../../../data/traits/instructions/unyielding.json) and [strong_willed](../../../data/traits/instructions/strong_willed.json).

## 5. Rates

| threshold | false negatives (discarded, fits the intent) | false positives (kept, does not) |
|---|---|---|
| overlap floor 0.35 | Sample A: 2 of 60 one concept, **3.3% (0.4-11.5%)**; with the borderline, 26 of 60, 43% (31-57%).  Implied over the 167 below-floor pairs of all sessions about 6 (1-19), over TDA's 31 about 1 (0-4).  Model check just above: 2 3-edges in 122 TDA pairs read at 0.35-0.40 (1.6%, 0.2-5.8%).  Roger: **0 of 490** (0-0.75%). | Sample B: 0 of 40 one concept (0-8.8%), and no model reading of 3; over the band, 12 3-edges in 648 reads (1.9%, 1.0-3.2%).  So about 98% of the reads in the band are spend that produces no group: about 46 c over all sessions, 28.8 c in TDA.  None of it reaches Roger as a join. |
| k = 10 | Sample C: 2 of 40 one concept, **5% (0.6-16.9%)**; with the borderline 12 of 40, 30% (17-47%).  Implied over TDA's 1,668 such pairs about 83 (10-282).  Roger: **106 of 490 (21.6%, 18.1-25.6%)**, the largest single cause, and 31% of the links inside the groups he extended. | none: k adds no join by itself |
| cut-off 3, with the Opus escalation | Roger: **87 of 490 (17.8%, 14.5-21.4%)**; 64 of the 75 first-direction misses (85%, 75-92%) are a Sonnet 2 Opus never read. | Roger: **99 of 381 handled 3- and 4-edges (26%, 22-31%)** join terms he resolved differently: 3-only edges 31%, 4-edges 15%.  Proposed groups split 38 of 87 fully handled (44%), merged groups 9 of 63 (14%). |
| `SHARE_BINS`, `SECOND_OPUS_SHARE` | none: no pair is decided | the estimate: $16.09 before any call against $5.00 spent (3.2 times); $10.77 at the gate after the relation calls (2.2 times).  Measured on the TDA candidate pairs, the first-direction Opus share is 0.04 / 0.12 / 0.25 / 0.64 by bin against M3's 0.14 / 0.46 / 0.72 / 1.0, the second-direction share 0.03 / 0.10 / 0.22 / 0.62 against 0.16 / 0.50 / 0.77 / 1.0, and the second-direction Opus share 0.92 against 1.0 ([run.json](../../../data/candidates/review/review_tda_1/run.json) `estimate_inputs`). |

## 6. Verdict

**Doing what was intended, but improvable**: the k cut needs to depend on how dense a region is; the floor and the
cut-off are where the data put them.

- **Overlap floor 0.35: supported; leave it.**  Nothing Roger joined was lost there.  The relation call already
  holds back 92% of the candidate edges below 0.35 (384 of 415 in TDA), so the floor acts on about 31 pairs per
  TDA-sized build, about 1 of which is one concept, and dropping it would cost 2 cents a build.  Raising it to 0.45
  would save 29 cents a build and lose the 0.35-0.45 band's 3-edges, among them Roger's malleable / moldable 4-edge
  (0.442) and pairs I read as genuine: avaricious / money-grubbing (0.392), cutthroat / ruthless (0.427), pedestrian /
  unimaginative (0.431), fascinating / interesting (0.438), conscienceless / unethical (0.443).  Decision 11
  calibrated it on candidate-to-corpus readings at cut-off 4; on candidate pairs at cut-off 3 the lowest 3-edge is
  0.372 (TDA) and 0.420 (pilots), consistent with it.
- **k = 10: not supported; it should depend on density.**  It was copied from M3's corpus retrieval.  Where a concept
  has more than ten candidate members (the stubborn region: hardheaded and unmovable each sit in 13 proposed groups,
  immovable in 11), the ten nearest are used up inside the concept and the remaining links are never read; 39 of the
  106 k misses are inside the one [strong_willed](../../../data/traits/instructions/strong_willed.json) merge.  That is the "would-be simplex shattered by a missing link"
  the leftovers pass was built to repair, and Roger repaired it by hand 67 times.  Elsewhere k = 10 costs little:
  of sample C's ten pilot pairs nine are distinct and one borderline.
- **Cut-off 3: at the right place.**  Against Roger, 3-only edges agree 69% of the time, 4-edges 85%, pairs read
  below 3 34%: lowering to 2 would add joins that are two-thirds wrong (and the CLI accepts only 3 or 4), and
  dropping the proposed tier would lose 180 of the 282 links Roger confirmed.  Its false joins follow corpus
  boundaries, not edge levels, so no level change removes them; each costs Roger one drop or distinct.  The false
  negatives at the cut-off come mostly from the escalation, not the level: a Sonnet 2 is final.
- **`SHARE_BINS` and `SECOND_OPUS_SHARE`: harmless but stale.**  Erring high is the design; 3.2 times is more than it
  needs, and on the final one-R1-over-all-batches build
  ([coding_plan_review.md](../../trait_gap_generation/coding_plan_review.md) section 10) it could trip the cap or
  the $20 confirmation for nothing.

## 7. Proposals

Prices measured on the TDA build at Batches API rates (live rates are double): a Sonnet overlap call 0.060 c (196
prompt, 81 output tokens), an Opus overlap call 0.164 c (196, 125), a relation call 0.025 c for 10 listed neighbours
(about 0.0025 c per listed neighbour, output-dominated); a pair read costs 0.072 c at 0.35-0.45, 0.100 c at 0.45-0.55,
0.146 c at 0.55-0.65 and 0.298 c above, its Opus call and second direction included.  Counts are for a TDA-sized
build (871 candidates); the final all-batches build scales about linearly.  New 3-edges are estimated at the 3-edge
rate of edges ranked 7 to 10 in the same cosine bin (0.004, 0.031, 0.091, 0.296 per edge from 0.35 up), which falls
with rank, so they are upper estimates.

| # | proposal | extra calls (TDA-sized build) | cost | expected gain | evidence that settles it |
|---|---|---|---|---|---|
| P1 | **A radius rule**: keep k = 10 and add every pair at cosine 0.55 or above as a candidate edge (a `--radius` beside `--k` in `nearest_candidates` / `plan_graph`) | +172 edges; about 118 first-direction reads; up to 344 more listed slots | **about 21 c** | about 20 3-edges; 26 of Roger's 106 k misses become edges | build it on a copy of the TDA session (a new batch id with `review_tda_1`'s [responses.jsonl](../../../data/candidates/review/review_tda_1/responses.jsonl) copied in, so the overlap answers on record replay; the relation calls are re-sent because their lists change), never over `review_tda_1` itself, whose [graph.json](../../../data/candidates/review/review_tda_1/graph.json) Roger's log is pinned to by hash: under $1.  Then count the new 3-edges inside Roger's resolved groups against those across them |
| P1b | or k = 15 | +2,854 edges, +4,320 listed slots, about 630 reads | about 73 c | about 42 3-edges; 41 of the 106 | as P1 |
| P1c | or k = 20 | +5,652 edges, +8,601 listed slots, about 1,100 reads | about $1.24 | about 65 3-edges; 67 of the 106 | as P1 |
| P2 | **Opus on Sonnet 2s at cosine 0.55 or above** in the first direction (M3's `opus_check` at the proposed cut-off, which R1 skips) | 881 Opus calls, plus the second direction of each pair raised | about $1.45 and a few cents | unknown; 47 of Roger's 64 `2/-` cut-off misses are at 0.55 or above | **a pilot first**: Opus on all 64 same-resolution `2/-` pairs and 64 of the 133 different-resolution `2/-` pairs (stratified by cosine): 128 calls, about 21 c (42 c live, so real time); adopt if Opus raises the same pairs to 3 clearly more often than the different ones |
| P3 | Leave the overlap floor at 0.35 | none | $0 | | the numbers above; removing it instead costs about 2 c a build for about one pair |
| P4 | Take the estimate's shares from R1's own last build (the TDA bins above) instead of M3's blocks, and `SECOND_OPUS_SHARE` 0.92 | none | $0 | an estimate near the spend instead of 3.2 times it | replay `estimate_build` on `review_tda_1` with the measured shares and compare with $5.00 |
| P5 | Link candidates whose labels match once hyphens and spaces are removed, read or not: other-worldly / otherworldly (cosine 0.545, read `3/2`, because the two glosses took different senses) is the TDA case | none | $0 | 1 pair in TDA | |
| P6 | Correct the gate table in [README.md](./README.md) (6,001 / 5,586, not 9,782 / 8,970; the shares do not route to Opus) and the R1 entry of [escalations.md](../escalations.md) (cliques, not connected groups) | none | $0 | | |

Not proposed: a cut-off of 2 (the second direction of 1,832 first-direction 2s, about $1.8 a build, for joins
Roger agrees with a third of the time) and dropping the proposed tier (180 of 282 confirmed links lost).

## Other observations

- **The relation call is the largest pair discard among candidate edges** (3,092 of 6,001, 52%).  It held back 9 of
  the 378 same-resolution pairs that had an edge (2.4%, 1.1-4.5%) and sent irreligious / unliterary (A30) on as
  similar.  It is a model judgement, not a threshold, so it belongs to the M3 / relation-call audit.
- Of the 6,001 candidate edges 3,309 are listed by one side only and carry one relation answer.
- Recomputing the pilot sessions' plans on today's corpus changes review_pilots_1's candidate edges by 32 pairs
  (symmetric difference, of 2,183) and review_allport_pilots_1's by 8 (of 493), because the corpus centring has
  moved; a `--resume` of an old build would plan slightly different pairs.

## Inputs

[review_graph.py](../../../assistant_axis/gapgen/review_graph.py),
[decisions.py](../../../assistant_axis/gapgen/review_app/decisions.py),
[app.js](../../../assistant_axis/gapgen/review_app/static/app.js),
[novelty.py](../../../assistant_axis/gapgen/novelty.py),
[novelty_runner.py](../../../assistant_axis/gapgen/novelty_runner.py), the CLI
[review_graph.py](../../../data_analysis/gap_generation/review_graph.py);
[coding_plan_review.md](../../trait_gap_generation/coding_plan_review.md) (decisions 11-12, sections 2, 7, 10);
the TDA session's [run.json](../../../data/candidates/review/review_tda_1/run.json),
[graph.json](../../../data/candidates/review/review_tda_1/graph.json),
[responses.jsonl](../../../data/candidates/review/review_tda_1/responses.jsonl) (tokens per call),
[usage.json](../../../data/candidates/review/review_tda_1/usage.json),
[decisions.jsonl](../../../data/candidates/review/review_tda_1/decisions.jsonl) and
[decisions.before_leftovers_2026-10-11.jsonl](../../../data/candidates/review/review_tda_1/decisions.before_leftovers_2026-10-11.jsonl);
the other sessions under [data/candidates/review/](../../../data/candidates/review/);
[registry.jsonl](../../../data/candidates/registry.jsonl),
[metric_config.json](../../../data/candidates/metric_config.json) and the
[embedding cache](../../../data/candidates/cache/embeddings/) for the cosines.

## Addendum (2026-10-13, phase B): the Opus pilot on Sonnet-2 pairs

Run as recommended ([opus_pilot_1](../../../data/candidates/review/review_tda_1/opus_pilot_1/report.json), 128 first
directions of the TDA build that Sonnet read 2 and Opus never saw, half on pairs Roger resolved as one concept and half
on pairs he kept apart; prompts byte-identical to the build's; $0.63 live against the $0.42 estimate, the replies
being longer than the build's).

| Roger's resolution | Opus raised to 3 or more | 95% interval |
|---|---|---|
| one concept (64) | 22 (34%) | 23-47% |
| kept apart (64) | 22 (34%) | 23-47% |

Opus raises a third of Sonnet's 2s whichever way Roger resolved the pair: a gap of 0 points (one-sided Fisher exact
p = 0.57), against the build's own 3-edges, which agree with Roger's resolution 69% of the time, and its 4-edges 85%.
Scaled to the pools, an Opus read of every Sonnet 2 would add about 68 raised directions, of which about a third on
pairs Roger joined.  **Recommendation: do not send Sonnet-2 pairs to Opus**; the cut-off loss this audit found
(section on the 18%) is not recoverable this way, and the k = 10 / pair-floor change is the one that adds pairs Roger
wants.
