# Overnight readout, 2026-10-08: platform close-out and the first two generators

Written for Roger by Fable, from the three Opus agents' reports and the runs that followed.  Terms: the
[glossary](./glossary.md).  Roger's instruction (2026-10-08, going to bed): "Build the recovery harness as a
platform close-out before the first generator.  1) Update all the plans 2) Do the platform closeout 3) Have
two agents code plans 1 and 2 in parallel, then use those to test the platform."

## In one paragraph

All three steps are done and merged on one branch (details and the merge state in § 7).  The plans now
describe the platform as built ([coding_plan_platform.md](./coding_plan_platform.md), "Interface as built").
The close-out agent built the recovery harness (hide a tenth of the corpus, score a generator run against
the reduced corpus, count the hidden traits found again), froze the package's exports, wrote the AGENT_NOTES
paragraph, and did the three Haiku 5.5 left-overs; its live check on the M3 pilot's rows found 13 of 83
hidden traits (§ 2).  The two generator agents built the census generator (plan 1) and the Roget-and-WordNet
generator (plan 2), each with a submitted pilot run (§ 3).  The pilots then went through M1 and M3, and all three
through a one-seed recovery test (§ 4, § 5): a fifth of the TDA rediscovers 23% of a hidden tenth of the
corpus with no sight of our list, which is the platform test you asked for.  Spend for the night is $26.10
(§ 6), of which the pilots and recovery tests are $21.10, a little over the "about $20" default I set.  What waits for you:
the full generator runs (over the $20 line each) and fifteen questions (§ 8).

## 1. The plans (step 1)

Commit 61c9065 on `anthropic-vllm-uv`, then 7a78b63 on the close-out branch with the as-built corrections:

- [coding_plan_platform.md](./coding_plan_platform.md): the old "Frozen interface" section is marked superseded
  on its scorer side (`NoveltyQuery`, `score_novelty`, `recovery_test`, `embed_local` were never built; M3 was
  redesigned as retrieve-then-judge on 2026-10-02); a new section "Interface as built (2026-10-08)" gives the
  registry API, the CLIs, the row's `filter` and `novelty` blocks, the recovery-harness specification, and the
  reconciliation of checklist tasks 20-25; then the close-out agent's brief.
- [README.md](./README.md): the stale "nothing has been run" line replaced by a status paragraph.
- [13_generator_testing.md](./13_generator_testing.md) (re-specified in M3's terms),
  [11_novelty_ensemble.md](./11_novelty_ensemble.md) (largely subsumed by M3) and
  [12_novelty_persona_space.md](./12_novelty_persona_space.md) (untouched) carry status notes.
- [coding_plan_01_censuses.md](./coding_plan_01_censuses.md) and
  [coding_plan_02_roget_wordnet.md](./coding_plan_02_roget_wordnet.md): a "Revision for the interface as built"
  section each, overriding the sections written against the old interface, and an "As built" note.

## 2. The platform close-out (step 2)

Opus agent in the close-out worktree, eight commits d238ca4 to 070de2c, 1,096 tests passing at the end
(1,043 before), $5.00 spent ($4.87 live check, $0.13 cache smoke).

**The recovery harness** ([recovery.py](../../assistant_axis/gapgen/recovery.py),
[recovery_test.py](../../data_analysis/gap_generation/recovery_test.py)).  Usage:

```
uv run python data_analysis/gap_generation/recovery_test.py --generator G --run-id R \
    [--hidden-frac 0.1] [--seed 0 1] --budget-usd C [--transport auto|live|batches] [--batch-id B]
```

Per seed it hides whole arrangement groups (a pair, triangle or tetrahedron hides together) drawn by region
until a tenth of the corpus is hidden; scores the run with M3 against the reduced corpus (`novelty_score.py
score --hide`, which fits the index without the hidden traits, leaves them out of expansion and the exact-label
check, and never writes the registry); matches every candidate decided `new` or `grey` against the hidden
traits (a label match, separator-blind and through `renamed_from`, needs no call; otherwise the overlap call,
Sonnet then Opus under the pipeline's rule, against each hidden trait among the candidate's ten nearest); and
reports recall by region and by arrangement kind, precision, groups recovered whole, false covers (a hidden
trait missed only because another trait covered the candidate) and cost.  One deviation from the
specification, which I accept: it draws whole groups rather than drawing stems and adding their partners,
so every trait has the same chance of being hidden (the partner method would hide about 17% and pair members
twice as often).

**Live check** on the M3 pilot's antonym-check rows (`antonym_check/pilot_1`, 487 rows, seed 0, $4.87;
[recovery_report.md](../../data/candidates/recovery/rec_antonym_check_pilot_1/recovery_report.md)):

| Measure | Result |
|---|---|
| Hidden | 83 of 790 traits, in 53 groups |
| Reduced-corpus M3 | 367 candidates: 205 covered, 162 new |
| **Recall** | **13 of 83 (15.7%)**: 2 by label (both through `renamed_from`), 11 by overlap call |
| By arrangement kind | 13 of 56 pair members (23%); 0 of 10 singletons |
| Precision | 17 of 162 kept candidates (10.5%) |
| Groups recovered whole | 4 of 29 |
| False covers | 16 candidates; 14 hidden traits missed only because of them (recall counting those: 32.5%) |

How to read it: the antonym-check words are the corpus's own antonym candidates, not a generator's output, so
15.7% says what that pool rediscovers, not what a generator will.  The false covers are the interesting part:
`amicable` matched hidden `friendly` but was covered by `agreeable`; `cold hearted` matched hidden `callous` but
was covered by `cruel`; `financially stable` matched hidden `financially secure` but was covered by `wealthy`.
These are near-duplicates inside the corpus showing up as hiding artefacts; a cheap list for a later
tidy-up.  M3 came in 27% over its estimate (3.5 pairs judged per candidate against the plan's 2.46, Opus at
$0.0039 a call against $0.0031); cache hit rates were 96% Sonnet, 98.5% Opus.

**The other close-out items.**  The package [gapgen/__init__.py](../../assistant_axis/gapgen/__init__.py)
now exports the registry API, the paths, `MetricConfig`, the recovery entry points, the embedding facade and
the WordNet handle, with a test that nothing of the superseded scorer interface is exported.  AGENT_NOTES has a
"Trait-gap platform (2026-10-08)" section under the trait-pairs rule, synced.  Haiku 5.5 left-overs: five split
prompts (sense, kind, established, gloss, alignment) now go cached on 5.5 (73% of Haiku input tokens read from
the cache on a 30-word smoke, $0.13); the cost estimate's shares are measured per model (Haiku 5.5: 0.96
primary readings per word, 4% same-sense, 65% trait, 12% second opinion; 4.5: 1.41, 37%, 70%, 13%); eleven rubric
"Model" header lines name the defaults, pins unchanged.  Two platform fixes from the generators' reports:
`submit_candidates(run=ctx)` records `candidates.jsonl` before appending to the log, and `run.log` is
git-ignored.  One test expectation changed: the three-reading kind-call count is now `ceil(3 × share × n)`
instead of exactly three times the one-reading count (it held only because 1.3 × 10 is whole).

## 3. The generators (step 3)

Both agents stayed inside their packages; neither touched a platform file; the shared
`generators/__init__.py` is byte-identical in both.  Every run writes a tracked `candidates.jsonl` (one
`Candidate` per line) before submitting, since the registry log is git-ignored and per checkout; the main
checkout resubmits with `gap_registry.py submit --from`.

**Plan 1, censuses** (branch `gen01-censuses`, six commits, $0; package
`assistant_axis/gapgen/generators/censuses/`, CLI
[census_generator.py](../../data_analysis/gap_generation/census_generator.py); 127 tests).  Downloads
verified against the published hashes into `data/external/wordlists/` with licences: the TDA (Trait
Descriptive Adjectives, 2,818 words with the proportion of raters who knew each; Dataverse, CC0; Condon,
Coughlin and Weston 2021, not 2022 as the plan said) and Allport-Odbert (17,708 distinct words in four
columns; OSF, CC BY).  Census table of 17,958 stems ([data/candidates/censuses/](../../data/candidates/censuses/)).
Stages: `tda` 2,818; `allport_hi` (Zipf ≥ 2.5) 4,746; `allport_probe` (Zipf 1.5-2.5 plus 863 rescued by the
negating-prefix rule) 3,438; 6,955 Allport-only words in no stage (1,341 below the floor, 5,614 unknown to both
`wordfreq` and WordNet).  String ceiling: of the corpus's 790 traits the lists contain 444 as strings (56%; 78%
of the single-word traits).  Deviations worth your eye: the plan's one-edit spelling repair was mostly wrong on
the real list (`cullying` became `bullying`), so it is applied only to letter doublings and vowel insertions
and the other 706 are recorded as suggestions; TDA words are never gated as unknown.  Pilot
`2026-10-08-pilot`: every fifth TDA word, 564 candidates, 77 of them existing corpus labels
([readout.md](../../data/candidates/runs/censuses/2026-10-08-pilot/readout.md)).

**Plan 2, Roget and WordNet** (branch `gen02-roget`, ten commits, $0.0135 of embeddings; package
`assistant_axis/gapgen/generators/roget/`, CLI
[roget_generate.py](../../data_analysis/gap_generation/roget_generate.py); 107 tests).  Roget 1911 from
Gutenberg (this edition: 1,044 heads, 912 with adjectives; the plan's counts were for another edition).  No LLM
pass, per the revision: opposed heads by rule (221 of 576 dispositional heads unresolved; the plan's target
was ≤ 3% with an LLM pass), label placement by lexical hit or embedding cosine (615 of 790 traits placed; the
rest are mostly outside Roget's scope, such as astrology signs and MBTI types).  **Coverage map**
([roget_coverage.md](../../data/candidates/roget/roget_coverage.md)): 675 heads in scope; 311 covered, 75
partly, 289 uncovered (36 with only a queued label); opposed pairs in scope: 75 with both poles covered, 77
one pole, 57 neither.  Pilot `2026-10-08-pilot`: 66 of the 289 gap heads, 185 Roget words (181 distinct; 39
pair candidates, 14 with a partner hint) plus 87 words from the WordNet stream, which submits under its own
generator name `wn_clusters` ([readout.md](../../data/candidates/runs/roget/2026-10-08-pilot/readout.md)).

## 4. The pilots through the platform (step 3, second half)

Resubmitted into the registry from the three `candidates.jsonl` files: censuses 564 (509 new rows, 55 already
present from the earlier pools), roget 185 (174 new, 11 merged), wn_clusters 87 (58 new, 29 merged); 1,289
rows in all, 741 unfiltered before M1.

**M1, the trait-hood filter** (Haiku 5.5, three readings with the asymmetric rule, 10% Sonnet second
opinion; live; batches `gen_pilot_censuses`, `gen_pilot_roget`, `gen_pilot_wn_clusters` under
[data/candidates/filter/](../../data/candidates/filter/)):

| Run | Filtered now | trait | tagged (states / physical / roles) | turned away | Polysemy | Second opinion disagreed | Cost |
|---|---|---|---|---|---|---|---|
| censuses (TDA) | 509 | 447 (88%) | 56 (49 / 8 / 1, counting the run's 564 rows) | 6 | 40% | 3 of 54 (5.6%) | $3.63 |
| roget | 172 | 85 (49%) | 55 (46 / 4 / 5) | 32 | 70% | **5 of 21 (24%)** | $1.34 |
| wn_clusters | 59 | 51 (86%) | 6 (6 / 1 / 0) | 2 | 34% | 0 of 6 | $0.42 |

Two things to notice.  **The Roget run tripped the disagreement tripwire** (first model against the Sonnet
second opinion, 24% over the 10% line, on 21 sampled rows) and stopped before its last wave; I resumed it with
`--accept-disagreement`, as you did on the M3 pilot's antonym pool (12.8%), and the rest cost $0.14.  Roget's
words are the polysemous, dated end of the vocabulary (70% flagged polysemous against 40% for the TDA), and
that is where Haiku 5.5 and Sonnet part company.  The five rows (in the batch's
[results.jsonl](../../data/candidates/filter/gen_pilot_roget/results.jsonl)): `faulty`, `lame` and `trivial`,
which Haiku passed as traits and Sonnet turned away (stretched, evaluative, no person reading); `misnamed`,
trait against states; and `self_called`, which Haiku tagged as a role and Sonnet read as the trait "self-styled".
Haiku 5.5 is the one over-accepting here, the opposite of its lean on the 600-word test, and that is decision
16's first real data.  **The TDA passes M1 at 88%**: the plan's 90% guess for a curated list holds, so
the census's M3 cost estimates stand.  Roget's 49% pass rate means its M3 cost per harvested word is about
half the estimate in the plan's "As built" note.

**M3, the novelty scorer** (retrieve ten nearest, Haiku 5.5 relation call, overlap call Sonnet then Opus on
the close calls; live; `decisions.md` in each batch directory under
[data/candidates/novelty/](../../data/candidates/novelty/)):

| Run | Candidates (M1 trait) | covered | of which exact label | new | Flagged for review (Sonnet below, Opus at) | Both-similar | Pair completions | Cost | Estimate |
|---|---|---|---|---|---|---|---|---|---|
| censuses | 447 | 217 (49%) | 81 (75 corpus, 6 queue) | 230 (51%) | 41 | 4 | 13 | $4.71 | $3.25 |
| roget | 85 | 18 (21%) | 1 (queue) | 67 (79%) | 10 | 1 | 6 | $1.12 | $0.75 |
| wn_clusters | 59 | 23 (39%) | 0 | 36 (61%) | 8 | 1 | 5 | $0.75 | $0.52 |

Three readings of this.  **The census pilot's yield**: every fifth TDA word gave 230 candidates M3 calls new
against the corpus, about 41 per 100 TDA words; by eye the first forty new ones
([decisions.md](../../data/candidates/novelty/gen_pilot_censuses/decisions.md)) are a mix of real gaps
(`admonitory`, `backbiting`, `curmudgeonly`, `discriminating`, `divisive`, `doting`), evaluative or register words
that M1 let through (`cheesy`, `classy`, `cute`, `desirable`, `brutal`) and phrasings of covered traits where the
overlap call read the gloss as narrower (`abusive` nearest `malicious`, `charming` nearest `friendly`).  The 41
flagged rows are where your review decides between "Opus on the 2s and 3s" and "Opus on the 3s only"; the
census readout's M3 section
([readout.md](../../data/candidates/runs/censuses/2026-10-08-pilot/readout.md)) has the known-label pass rate
(77 of 77 corpus labels passed M1 and were covered by their own label).  **Roget's harvest is new by
construction** (79%): it only proposes words for heads the corpus does not cover, and M3 agrees four times in
five; the one in five it covers is the coverage map's placement being looser than the overlap call.  **M3 ran
45% over its own estimate** on every run (the close-out's live check saw 27%): more pairs judged per candidate
than the estimate's 2.46, and Opus a quarter dearer per call; the estimate's shares want remeasuring on these
runs, a small job.

## 5. The recovery test on a generator

One seed each (seed 0, which hides the same 83 traits in 53 groups every time), live; reports under
[data/candidates/recovery/](../../data/candidates/recovery/).  Each run reruns M3 on the generator's rows
against the reduced corpus and then asks the overlap call about each hidden trait among a kept candidate's ten
nearest, so a run costs about what the pilot's M3 cost plus a quarter.

| Run | Kept against the reduced corpus | Recall | by label | by overlap call | Precision | Reachable | False covers | Cost |
|---|---|---|---|---|---|---|---|---|
| censuses | 280 | **19 of 83 (22.9%)** | 11 | 8 | 26 of 280 | 74 of 83 (89%) | 8 | $6.63 |
| wn_clusters | 48 | 6 of 83 (7.2%) | 0 | 6 | 6 of 48 | 44 of 83 | 1 | $1.13 |
| roget | 75 | 1 of 83 (1.2%) | 0 | 1 | 1 of 75 | 44 of 83 | 0 | $1.36 |

**The census number is the platform test you asked for, and it reads well.**  A fifth of the TDA, with no sight
of our list, rediscovers 23% of a hidden tenth of the corpus: 11 by the hidden label itself (`accountable`,
`benign`, `merciful`, `superstitious`, ...) and 8 through the overlap call on a different word (`lukewarm` for
[apathetic](../../data/traits/instructions/apathetic.json), `compassionless` for
[callous](../../data/traits/instructions/callous.json), `consoling` and `soft-hearted` for
[compassionate](../../data/traits/instructions/compassionate.json), `heedless` and `unobservant` for
[oblivious](../../data/traits/instructions/oblivious.json), `saucy` for [sassy](../../data/traits/instructions/sassy.json),
`world weary` for [jaded](../../data/traits/instructions/jaded.json)).  All three hidden triangle members came
back; singletons 4 of 10; pairs 11 of 56; the 4-cube, rings, sets and the square 0 of 9, which is the
multi-word and construct end of the corpus that an adjective list cannot reach.  By region: emotional
temperament 4 of 8, moral stance 5 of 14, communication style 5 of 16, cognitive 3 of 17, identity and
demographic 0 of 6, no region 1 of 17.  Reachability is 89%, so retrieval is not the bound; the generator's
coverage is, as the string ceiling predicted (the TDA holds 50% of corpus labels as strings, a fifth of it
about 10%, and 11 of 83 by label is 13%).  The eight false covers are the corpus's own near-duplicates again
(`fervent` matched hidden `zealous` but `passionate` covered it; `humorous` matched `wry`, covered by `witty`;
`moderate` matched `temperate`, covered by `moderate`'s own label), the same list the live check started.

**The Roget and WordNet numbers are structural, not a platform result.**  The Roget harvest only proposes
words for heads the corpus does not cover, and the WordNet stream starts from the corpus's own partner-less
traits; both were generated against the *full* corpus, so a hidden trait's head or antonym was never a gap
at harvest time.  For a corpus-reading generator the recovery test has to rerun the generator against the
reduced corpus, not just M3; that is a small addition to the harness (a `--hide` on the generator's
`harvest` and a hook in `recovery_test.py`), and I have not made it.  The one Roget recovery (`faulty` for
[incompetent](../../data/traits/instructions/incompetent.json)) and the six WordNet ones (`hard` for
[callous](../../data/traits/instructions/callous.json), `contentious` for
[confrontational](../../data/traits/instructions/confrontational.json), `genial` for
[friendly](../../data/traits/instructions/friendly.json), ...) are incidental neighbours.

## 6. Spend

All live (every job under the $20 line, so real time per the batch-or-real-time rule); every figure from the
job's `usage.json`.

| Job | Cost |
|---|---|
| Close-out: harness live check on the M3 pilot's rows | $4.87 |
| Close-out: split-filter cache smoke (30 words) | $0.13 |
| Roget generator: embeddings for label placement | $0.01 |
| M1 on the three pilots (censuses $3.63, roget $1.34, wn_clusters $0.42) | $5.39 |
| M3 on the three pilots (censuses $4.71, roget $1.12, wn_clusters $0.75) | $6.58 |
| Recovery tests, one seed each (censuses $6.63, roget $1.36, wn_clusters $1.13) | $9.12 |
| **Night** | **$26.10** |

The pilots and their recovery tests come to $21.10 against the "under about $20" I set as the default before
you went to bed; the extra is the census recovery test, which I ran once the Roget one turned out to be
structurally uninformative, because it is the one that tests the platform.  Platform cost per word, measured
tonight: M1 $0.0071 to $0.0078 a word (the plan's $0.004 was Haiku-only; the Sonnet second opinion and the
comparison step are the rest); M3 $0.0105 a candidate on the census (81 of 447 covered by label without a
call), $0.013 on Roget and WordNet; a recovery seed about 1.4 times the run's M3.

## 7. Branches, merges and tests

- Close-out branch `worktree-agent-a49beca76adafdfc1`: the close-out's eight commits, then merges of
  `gen01-censuses` (afaf208) and `gen02-roget` (298d686; the two generators had both appended questions
  numbered from 28, so the Roget ones are now 37-42), the plan fixes (7a78b63), and the peer session's new
  main-branch commit 41a65c2 (e3aa3c0, clean).  Tests on the merged tree: the gapgen, generator and sync suites
  pass (exit 0), rerun after the peer merge (exit 0).
- The two generator agents signed their commits "Co-Authored-By: Claude Opus 5.5" rather than the Fable line;
  I left the trailers as they are.
- The main checkout's `anthropic-vllm-uv` is fast-forwarded to the close-out branch's head (the commit that
  carries this readout and the pilots' outputs), and its git-ignored `data/candidates/registry.jsonl` is replaced
  by the worktree's (1,289 rows; the main checkout's 548 rows were its exact prefix).  The peer session was told
  beforehand and had no objection; its uncommitted chunk-5 files are untouched.  Nothing is pushed: the branch is
  ahead of `origin` by the whole of this week's work.
- The three worktrees (`agent-a49beca76adafdfc1`, `gen01-censuses`, `gen02-roget`) are left in place with their
  branches; the two generator worktrees can be removed once you have looked (`git worktree remove`).
- The generators' `data/external/` downloads (TDA, Allport-Odbert, Roget 1911, and the 125 MB Open English
  WordNet the census agent installed because the main checkout's was empty) live in the main checkout's
  git-ignored `data/external/`, which the generator worktrees reach through a symlink.

## 8. For you

1. **Full generator runs** (each over the $20 line; the agents' commands are in their reports and in the
   plans' "As built" notes): the full TDA (2,818 words; about $28 through the Batches API, about $23 after the
   pilot's rows), then `allport_hi` (4,746; about $48) and `allport_probe` (3,438; about $35); the full Roget
   harvest (898 Roget words plus 434 WordNet; about $12).  Say which, and whether through Batches.
2. **Recovery on the census pilot**: not run tonight (each seed reruns M3 on the run, about $9 for this pilot);
   one seed, two, or wait for the full run.
3. **Questions 28-42** in [QUESTIONS.md](./QUESTIONS.md): the census agent's 28-36 (is the 12 MB census table
   tracked; Allport column IV in or out; words below the floor; the narrowed spelling repair; the plan's
   acceptance figures against the 790-trait corpus) and the Roget agent's 37-42 (derived files tracked; the
   221 unresolved opposed heads: an LLM pass, a position pass, or neither; placement without the LLM; the
   Class I-III rule; gloss-hint wording; the Zipf floor at 1.5 against the plan's 2.0).
4. **Decision 16** (re-examine the verdict model on real generator output) now has data: the M1 verdicts on
   the census pilot (§ 4).  Roger (2026-10-08, morning): the TDA's turned-away rate, 6 of 564 (1.1%; `awful`, `bad`,
   `terrible`, `exceptional` evaluative, `unforseeing` unknown, `dowdy` arguable but covered by
   [unfashionable](../../data/traits/instructions/unfashionable.json)), is an acceptable error rate.  Roget's
   33 of 181 are the harvest's non-dispositional heads, a generator question (40), not a filter one.
