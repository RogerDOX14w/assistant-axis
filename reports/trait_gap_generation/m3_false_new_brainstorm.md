# M3's false "new" rows: brainstorm, paused for review data (2026-10-16)

**Status: paused at the brainstorming stage** (Roger, 2026-10-16: "worth pursuing, but most or all of it will be
more worth doing once we have more data").  The next step is Roger's: one or two hours of review in the new
`sample` order, blind (§ 5).  Then resume at § 6.  This document holds everything needed to pick it up.  Terms:
[glossary.md](./glossary.md).  The standing follow-up it extends is the [README](./README.md) TODO "Revisit the
duplicate signals once review has data".

## 1. The problem

M3, the novelty check, decides whether a candidate is covered by a corpus trait.  It is built to err towards
"new": a false "covered" silently and permanently loses a trait (covered rows never reach review), while a false
"new" costs Roger one merge in review.  The price is review time, and it is large.  Of the 177 reviewed rows M3
called "new" (all decided under M3 rule set 3), Roger merged 78 into a corpus trait (44%), merged 62 into another
candidate, and kept 37.

Where the 78 went wrong:

| what M3 saw of the trait Roger merged into | rows | why it stayed "new" |
|---|---|---|
| Sonnet and Opus both read overlap 3 | 24 | the cut-off: in the alignment band (alignment score 3) a cover needs 4, to protect distinctions such as flattering vs [sycophantic](../../data/traits/instructions/sycophantic.json) |
| read 2 (partial overlap) | 40 | calibration: the models read partial overlap where Roger saw one trait (21 of them never went to Opus) |
| Sonnet 3, Opus 2 | 8 | the Opus escalation rescued it |
| the target trait never retrieved | 6 | retrieval |

**Not the cosine floor.**  The floor (0.25) only decides which corpus traits M3 reads, and in 72 of the 78 cases
M3 read the right trait.  The [gate audit](../code_review_2026-10-12/gate_audits/m3_novelty.md) (§ 7.4) found the
floor harmless and nearly idle, and Roger kept it unchanged (2026-10-16).  The same audit located the loss at the
cut-off (§ 7.5) and proposed P1 to P6.

Generator by generator, M3 judged 42% of 8,674 decided trait rows covered; corrected by Roger's reviews, the
covered share is nearer 55-65%.  At 44% false "new", roughly 2,000 of the 4,822 rows awaiting review would end as
merges into the corpus.

## 2. What the existing signals already show (free, 2026-10-16)

On the same 177 reviewed "new" rows:

| signal | merged into corpus | merged into a candidate | kept |
|---|---|---|---|
| best overlap reading against any corpus trait = **3** (either model) | 37 | 8 | **1** |
| best overlap reading = 2 | 41 | 51 | 29 |
| persona-space "duplicate-like" ([plan 12](./coding_plan_12_persona_space.md)) | 22 | 9 | 5 |
| lexical link present ([plan 11](./coding_plan_11_novelty_ensemble.md)) | 54 | 47 | 16 |
| no lexical link | 24 | 15 | 21 |

- **A 3 from either model is close to decisive here** (45 of 46 not new).  The open question is whether it holds
  outside the dense TDA and Allport clusters these labels come from, especially in the alignment sweep, where
  Roger's fine distinctions live and where there are almost no labels.
- **A best reading of 2 is the hard case**: two-thirds of the queue, outcomes mixed.
- The persona flag is weak alone (22 of 36 against a 44% base rate); a lexical link mostly separates "kept" from
  "merged somewhere".

## 3. Ideas

Causes: A = the alignment band's cut-off (24), B = calibration at 2 (40), C = Opus rescue (8), D = retrieval (6).

| # | idea | targets | cost | note |
|---|---|---|---|---|
| 1 | **A "probably covered" fast lane**: rows read 3, or 2 with a second signal agreeing, go to a quick-confirm list showing the trait they probably duplicate; Roger accepts or rejects with one key.  Covers become visible, so the cut-off can move without silent losses. | A, B, C | review-app build, $0 | the largest effect; § 2 suggests the reading-3 stratum alone is 28% of queue items |
| 2 | **Pre-filled merge target**: the card's first merge target is the trait M3 read highest | A, B, C | $0 | **already in place**: the card's corpus panel is ordered by M3's reading, then cosine |
| 3 | **Ask in Roger's merge terms**: "would a persona built from A be meaningfully different from one built from B?", yes or no, reason first, three readings, majority | B | cents per row | a binary question may calibrate better than a 0-4 scale |
| 4 | **Few-shot the overlap rubric** with 6-10 of Roger's resolved pairs (merged at 2, kept apart at 3) | B | a rubric version bump | test only on rows the examples do not come from |
| 5 | **Blind naming**: give a model the gloss without the label and ask it to name the trait from the corpus list (the `--name-pos` machinery) | B, D | cents per row | independent of retrieval |
| 6 | **A direction check on 3/3 readings in the alignment band**: candidate narrower than the corpus trait, covered; corpus trait narrower, stays new | A | cents per row | the audit's P3 turned to the opposite error; plan 16's sub-role rule for traits |
| 7 | **Escalate Sonnet's 2s to Opus** | B (21 rows) | cheap | already a README TODO; Roger sided with Opus on every split pair |
| 8 | **Aliases from merges**: a merge adds the merged word to the corpus entry as "also called", which M3's text and retrieval then see | B, D | $0 per call | compounds with every review session |
| 9 | **A learned combiner**: the chance Roger merges, from both readings, alignment band, cosine, persona score, lexical links (and 5 if built); threshold that | all | modelling only | needs a few hundred outcomes |
| 10 | **Review in an order that teaches fastest** | — | — | became the sample design of § 5 |

## 4. Built 2026-10-16 for the next step

- **The `sample` queue order** (commit bc9c8674; [decisions.py](../../assistant_axis/gapgen/review_app/decisions.py)
  `SAMPLE_SEED`, `SAMPLE_WEIGHTS`, `sample_progress`): a seeded random order without replacement over queue items
  (groups and singletons), stable through a session.  Each item's stratum is its strongest member's best M3 reading
  (`read_3`, `read_2`, `other`).  The weights are equal (a plain random sample): the design first doubled `read_3`,
  but in `review_traits_all_2` that stratum is already 28% of the items and about 40% of the terms, so it needs no
  oversampling.  `review_app.py status` reports the items reached per stratum and the inclusion probabilities.
- **The persona-space badge** (commit a72e041a): the duplicate flag on 728 of the batch's 4,254 kept terms.
- **`serve --blind`**: hides the persona-space and dictionary badges server-side, so the session's decisions test
  those signals instead of following them.  The batch's graph predates the lexical integration, so it has no
  dictionary badges anyway.

## 5. The review session (Roger)

```
uv run python data_analysis/gap_generation/review_app.py serve --batch-id review_traits_all_2 --order sample --blind
```

Work down the queue with Space (next group) as usual.  Leftovers and merge-ins are fine; they are counted apart as
"pulled in", outside the sample.  One hour is about 150 terms; two hours halve every uncertainty.  Afterwards:

```
uv run python data_analysis/gap_generation/review_app.py status --batch-id review_traits_all_2
uv run python data_analysis/gap_generation/review_app.py apply --batch-id review_traits_all_2 --dry-run
```

then `apply` without `--dry-run`.  The log had no events before this session (2026-10-16), so `status` counts
the sample from the start; a later sample session passes `--sample-since <seq>`.

## 6. Resuming

1. **Read the session**: per stratum, merged into the corpus, merged into a candidate, kept, with the inclusion
   probabilities; above all, whether "a 3 means duplicate" holds outside the census clusters.  Also the
   per-generator yields for plan 13's stop rule and the corpus-target estimate (README § "Trait corpus target").
2. **Replay experiment** (about $2-5 live, all reviewed rows: the 211 before plus the session's): ideas 3, 5, 6 and
   7, each with a prediction written down first.  Score each idea on how many of Roger's merges into the corpus it
   recovers and how many of his kept rows it would wrongly cover.  The calls can run after the review: Roger never
   sees their output, so the test stays blind.
3. **The multiple-2s test against candidates** (TODO, Roger 2026-10-20): QUESTIONS 209 found that a candidate
   read 2 against two or more corpus traits is usually merged (72%).  Repeat the test with **other candidates** as the
   targets (the review graph's R1 readings): does a candidate read 2 against several candidates, with no 3 among
   them, get merged?  On `review_tda_1` it could not be read (177 of 203 decided rows had a candidate neighbour read
   3 or more, in "cliques" order; 26 left).  Wait for enough singletons from the sample hours (their random order
   includes them).  Roger's two readings of the corpus 2s (QUESTIONS 209) do not both carry over: an honest blend of
   other candidates can, but "the region is already well sampled" applies only to traits in the corpus or the seed
   queue, so it does not arise between candidates until they reach the queue.
4. **Decide the builds**: 1 or 8 first, by the replay; 9 once review passes about 400 outcomes.
