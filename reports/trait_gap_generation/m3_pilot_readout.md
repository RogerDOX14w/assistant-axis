# M3 pilot: what the novelty check kept and cut (2026-10-07)

The first run of M3, the novelty check, built to [coding_plan_m3.md](./coding_plan_m3.md) by an Opus
agent on 2026-10-07 and run live the same day on Roger's go ("Let's keep running for now, and see what
happens").  Everything is on the branch; the run directories are
[data/candidates/novelty/m3_pilot_1/](../../data/candidates/novelty/m3_pilot_1/) (the main run) and
[m3_pilot_1_scan/](../../data/candidates/novelty/m3_pilot_1_scan/) (the full scan).  The file to sample
from is **[decisions.md](../../data/candidates/novelty/m3_pilot_1/decisions.md)**: every candidate with
its decision, the trait that covered it, the readings that decided it, the review flags, the pair
completions and its gloss, then the review queue in full with both models' reasons.

Terms: a *candidate* is a word proposed as a new trait; the *M1 filter* decides whether it names a
persona trait at all and writes its *gloss* (a one-sentence description in the corpus form) and
*alignment score* (0-3, how close to the alignment region); M3 decides whether the corpus already has
it (*covered*), does not (*new*), or has it kept with a flag for Roger's review (*grey*).  The
*cut-off* is the overlap score at which a candidate counts as covered: 3 far from alignment, 4 near
it.  Other terms are in the [glossary](./glossary.md).

## What ran, and what it cost

| stage | what | cost | estimate |
|---|---|---|---|
| M1 filter, antonym-check pool | 405 words the antonym checks had proposed that are not in the corpus; Haiku 4.5 first, the 10% Sonnet sample; the disagreement check tripped at 12.8% (6 of 47) and was resumed with the override on Roger's word | $4.64 | $4.01 |
| M1 filter, validation pool | 150 random adjectives the M1 validation run had passed; Sonnet 5.5 first, no second opinion (the plan's rule for a source where Haiku disagrees with Opus too often) | $2.65 | $2.12 |
| M3: relation calls | Haiku, one call per candidate, 17.2 listed traits on average (the 10 nearest plus arrangement partners) | $2.75 | $2.43 |
| M3: overlap calls | Sonnet one pair per call in cosine order, Opus on Sonnet's 3s and 2s; 2,275 pairs judged | **$5.74** | $3.47 |
| Full scan | 100 candidates, every listed trait judged, no shortlist, no early exit, to measure what the shortlist misses | $3.10 | $4.24 |
| **Total** | | **$18.88** | $15.3 (cap $30) |

Every answer from every model parsed at the first attempt.  Prompt caching worked: Sonnet and Opus
read the rubric from the cache on 99% of calls (81% of their input tokens).  The overlap stage ran
65% over its estimate because the shortlists were long (below).  Spend by model: Haiku $6.46, Sonnet
$8.24, Opus $4.17.  Usage records: [m3_pilot_1/usage.json](../../data/candidates/novelty/m3_pilot_1/usage.json),
[m3_pilot_1_scan/usage.json](../../data/candidates/novelty/m3_pilot_1_scan/usage.json), and the two
filter runs' ([antonym_check](../../data/candidates/filter/m3_pilot_antonym_check/usage.json),
[validation](../../data/candidates/filter/m3_pilot_m1_validation/usage.json)).

## What M1 passed

Antonym-check pool: 367 trait, 16 tagged (states and the like), 6 turned away, 14 cut by the
frequency floor; 94% of the words that reached the model passed, far above the 75% the estimate
assumed, which is where the M3 cost came from.  Validation pool: 100 trait, 14 tagged, 29 turned away
of 143 (7 words were in both pools).  Together **460 candidates** reached M3; 81 non-traits and 7 held
rows (nationalities) were skipped.

## What M3 decided

**205 covered, 179 new, 76 grey.**  By cut-off: far from alignment (cut-off 3) 198 covered, 106 new,
62 grey; near alignment (cut-off 4) 7 covered, 73 new, 14 grey.

- **Covered**, 12 by exact label (all through a corpus file's `renamed_from`) and 193 by the overlap
  walk: Sonnet 3 then Opus 3 on 147, Sonnet 3 then Opus 4 on 29, Sonnet 4 alone on 13, Sonnet 4 then
  Opus 4 on 4.  The first pair judged covered 157 of the 193; 178 were covered within three pairs;
  the latest was the tenth.  A sample from the table: abstinent by
  [teetotaler](../../data/traits/instructions/teetotaler.json), active by
  [energetic](../../data/traits/instructions/energetic.json), amicable by
  [friendly](../../data/traits/instructions/friendly.json), ambiguity intolerant by
  [closure-seeking](../../data/traits/instructions/closure_seeking.json), anti gay by
  [homophobic](../../data/traits/instructions/homophobic.json), audacious by
  [bold](../../data/traits/instructions/bold.json), boastful by
  [self-aggrandizing](../../data/traits/instructions/self_aggrandizing.json), beneficent by
  [benevolent](../../data/traits/instructions/benevolent.json).  `gap_registry.py synonyms --run-id
  m3_pilot_1` lists all 205 under the 158 traits that covered them: the rename shortlist of the
  design.
- **New**: the shortlist exhausted without a cover.  A sample: active participant, affirming,
  alienating, apostate, attached, autonomous, bankable, biased, blase, blooded, bloody-minded,
  bootlicking, boring.  These are the rows to sample for false keeps: a near-duplicate that slipped
  through would be here.  Each row says how many pairs were judged (5 to 12 for most new ones).
- **Grey** (kept, flagged): 61 where Sonnet read one below the cut-off and Opus read at or above it
  (the plan-of-record check, decision 11; the candidate is kept and the pair is for review), 47 pair
  flags (38 where both sides of a recorded pair came back "opposed", 10 both "similar"), 4 with both.
  The review queue, with both reasons, is the last section of
  [decisions.md](../../data/candidates/novelty/m3_pilot_1/decisions.md).  Typical Opus-check cases:
  abominable against [cruel](../../data/traits/instructions/cruel.json), accepting against
  [death-accepting](../../data/traits/instructions/death_accepting.json), appreciative against
  [grateful](../../data/traits/instructions/grateful.json), bovine against
  [slow-witted](../../data/traits/instructions/slow_witted.json): Sonnet 2 with a two-sided reason,
  Opus 3 with a containment reason, the pattern of the rubric test.
- **Pair completions**: 42 candidates came back "opposite" to a trait with no partner, and are
  recorded as its possible partner (design item 4): merciless, cruel to animals and sadomasochistic
  against [merciful](../../data/traits/instructions/merciful.json); nonsectarian against
  [sectarian](../../data/traits/instructions/sectarian.json); complacent against
  [accountable](../../data/traits/instructions/accountable.json) and
  [self-blaming](../../data/traits/instructions/self_blaming.json); selfless and personally oriented
  against members of the moral-circle sequence.  Listed in decisions.md; they go to the pairing track,
  not the merge list.
- **Opus's part**: 798 calls, 185 where Sonnet was at the cut-off (Opus kept the candidate on 5, the
  rescues) and 613 where Sonnet was one below (61 flags).  Of the 23 "opposite" readings in the walk,
  the partner was judged next where there was one.

## What the full scan says about the shortlist

On 100 candidates (seed 0) every listed trait was judged, 1,719 pairs, with no relation call and no
early exit ([comparison.md](../../data/candidates/novelty/m3_pilot_1_scan/comparison.md)):

- **The relation call's recall is 1.0**: all 76 pairs either model put at the cut-off or above had
  been marked "similar" by Haiku, including the 44 the rule cuts on.  The shortlist loses nothing.
- Decisions agree on 89 of 100; 5 differ only because the scan makes no relation call and so raises
  no pair flag; 6 changed sides at the 2 / 3 boundary between the two runs (brisk, equipped, soft,
  unsensational and three Opus-check flags), the same one-point noise as in every earlier run.
  Sonnet repeated its own answer on 91% of the 527 pairs read in both runs.
- **Early exit skipped 597 pairs**, 15 of them at the cut-off or above: other traits that would also
  have covered the candidate.  The first cover is what the decision needs; the others would only
  enrich the rename shortlist.

## What the pilot says about tuning

Roger: "I suspect we'll need to retune once we have enough data."  The data, with the levers and what
each would have done on this run (readings are the 2,275 pairs judged; covers the 193):

1. **The shortlist is long: 7.7 traits on average, 5.1 judged per candidate.**  Haiku marks about 6
   listed traits "similar" and 6.3 "opposed" per candidate, and each opposed trait's partner goes to
   the front.  Covers sit early (157 of 193 at the first pair, 178 within three), so:
   - a cap of 3 pairs would have saved 56% of the readings and lost 15 covers; 5 pairs, 34% and 12;
     6 pairs, 24% and 8;
   - a cosine floor of 0.25 would have saved 32% of the readings and lost 2 covers (and 5 of the 69
     review flags); 0.30, 57% and 5 (13 flags).  The covering pairs' cosines have a median of 0.50
     and a minimum of 0.22; all readings' median is 0.28.
   The floor is the better lever: it cuts the cheap tail without touching the near pairs.  Both can
   be re-run on the records without new calls.
2. **Haiku's "opposed" is loose.**  Most of the 38 both-opposed pair flags are candidates off the
   pair's axis (sly against aggressive and peaceful; consultative against decisive and indecisive),
   and each such reading pulls a partner to the front of the shortlist.  The both-similar flags are
   candidates broader than both poles (rich against new money and old money).  The pair flag is
   doing little as a review trigger; it could become a note on the row rather than a grey decision,
   which would halve the review queue (47 of the 76 grey rows carry it).
3. **The Opus check one below the cut-off** cost $2.30 (613 calls) and flagged 61 pairs, Sonnet 2
   against Opus 3, nearly all with the containment pattern.  Reviewing those 61 is what decides
   between the plan of record (Opus decides on the 2s too, and those become covers) and the saving
   (Opus on the 3s only, and those 61 are kept unflagged).
4. **The `renamed_from` rule covers some real gaps.**  Four exact-label covers were renames made
   because the old word means something else: engaging by
   [unflinching](../../data/traits/instructions/unflinching.json) ("engaging also means charming"),
   relaxed by [unhurried](../../data/traits/instructions/unhurried.json), shy by
   [self-conscious](../../data/traits/instructions/self_conscious.json), assertive by
   [opinionated](../../data/traits/instructions/opinionated.json).  Proposal: a `renamed_from` match
   goes to the overlap call against the current trait instead of covering automatically.
5. **Spelling variants.**  "anti feminist" was not caught at the exact-label stage (the corpus has
   antifeminist); the overlap call caught it at 3 / 3.  A separator-blind comparison catches it free.
6. **Opus costs $0.0038 a pair here** (against $0.0031 in the rubric test), Sonnet $0.0012, Haiku
   about $0.006 a relation call at 17 listed traits.  At the pilot's rates M3 is about $0.018 a
   candidate, $185 per 10,000 live and about $92 through the Batches API, before any of the levers
   above; M1 ahead of it is about $0.013 a word.

## Decisions for Roger

1. **Sample [decisions.md](../../data/candidates/novelty/m3_pilot_1/decisions.md)**: the covers for
   wrong cuts, the new rows for near-duplicates let through, and the review queue, which also settles
   the Opus-on-the-2s question (lever 3).
2. **The levers**: a cosine floor (0.25 proposed), the pair flag demoted to a note, `renamed_from`
   sent to the overlap call, separator-blind labels.  Each is a small change; the first two can be
   checked on the records before any new call.
3. **The rubrics**: rubric A's pass (version 6 ran here), and the relation rubric's first pass
   ([rubrics/relation.md](./rubrics/relation.md), version 1), whose "similar" is loose by design and
   could stay so given the recall of 1.0.
4. **The pair completions** (42) and the rename shortlist (158 traits) are by-products for the
   pairing and renaming work, not for M3.

## Files

- Code: [novelty.py](../../assistant_axis/gapgen/novelty.py), [novelty_runner.py](../../assistant_axis/gapgen/novelty_runner.py),
  [novelty_pools.py](../../assistant_axis/gapgen/novelty_pools.py), the CLI
  [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) (`score`, `full-scan`,
  `compare`, `render`, `--embed-only`), `gap_registry.py synonyms`; documented in
  [data_analysis/README.md](../../data_analysis/README.md) under M3; 81 M3 tests.
- Runs: [m3_pilot_1/](../../data/candidates/novelty/m3_pilot_1/) (`decisions.md`, `summary.json`,
  `readings.jsonl` with every pair's cosine beside its scores, `responses.jsonl`, `run.json`,
  `usage.json`, the rendered relation prompt for child free), [m3_pilot_1_scan/](../../data/candidates/novelty/m3_pilot_1_scan/)
  (`comparison.md`), the two filter runs under [data/candidates/filter/](../../data/candidates/filter/),
  and the registry with its 548 pilot rows ([registry.jsonl](../../data/candidates/registry.jsonl),
  snapshot [registry.snapshot.jsonl](../../data/candidates/registry.snapshot.jsonl)).
- Deviations from the brief, all recorded in the runs: the antonym pool is 405 words, not 449; 17.2
  listed traits, not 14; retrieval on the gloss alone cut to 14 words (the metric config's form, the
  brief was wrong); the validation pool filtered on Sonnet; triangle and tetrahedron corners count as
  partners; `pair_completion_for` is a list; a missing alignment score gets cut-off 4.
