# Acceptance: workstream 13, generator testing and saturation (2026-10-13)

Built by the Opus coding agent in the worktree `plan13-build` (from `anthropic-vllm-uv` at c6d8c433) to
[coding_plan_13_generator_testing.md](./coding_plan_13_generator_testing.md), with Roger's three decisions of
2026-10-13.  **No paid call was made.**  Everything free is built, tested, run and committed; the two paid steps
(the paraphrase set and the decision-1 harness) are left to the coordinator, with their commands below.  Terms are
in the [glossary](./glossary.md#generator-testing-terms-added-2026-10-13-for-workstream-13) (new section, task 9).

## What was built (§ 5)

| plan § 5 | built | notes |
|---|---|---|
| `testing/__init__.py` | [__init__.py](../../assistant_axis/gapgen/testing/__init__.py) | paths and the frozen interface (`ReviewRate`, `review_rate`, `pooled_review_rate`, `PromoteShare`, `promote_share`, `GeneratorRow`, `load_dashboard`, `DASHBOARD_JSON_PATH`) |
| `independence.py` | [independence.py](../../assistant_axis/gapgen/testing/independence.py) | the stream table, `stream_of`, states-pass attribution (`attributed_sources`), `provenance_excluded` |
| `review_minutes.py` | [review_minutes.py](../../assistant_axis/gapgen/testing/review_minutes.py) | review-minutes, terms decided, group times, the review rate, the promote share per group (decision 3) |
| `repetition.py` | [repetition.py](../../assistant_axis/gapgen/testing/repetition.py) | pre-handled at 3- and 4-edges, attachment to the reviewed batches; also the graph helpers `concepts.py` uses |
| `concepts.py` | [concepts.py](../../assistant_axis/gapgen/testing/concepts.py) | `components_4`, `grown_3` (`tau` 0.67; 0.5 and 0.8), `components_3`, `review_agreement` from every review log, `concept_table` |
| `estimators.py`, `simulate.py` | [estimators.py](../../assistant_axis/gapgen/testing/estimators.py), [simulate.py](../../assistant_axis/gapgen/testing/simulate.py) | written by a subagent to my brief, reviewed: Chapman, Chao2 (bias-corrected and classic), Good-Turing coverage, accumulation and its extrapolation, `ASSUMPTIONS`; the simulation |
| `recovery_extras.py` | [recovery_extras.py](../../assistant_axis/gapgen/testing/recovery_extras.py) | strict column, pair recovery, recall at N, contamination, `extras.json`; and `roger_sample` (the manual check) |
| `dashboard.py` | [dashboard.py](../../assistant_axis/gapgen/testing/dashboard.py) | cost attribution, string recall, negatives, stop rule, rows, the estimates assembly (including the corpus as an occasion and the alignment sweep's two occasions), Markdown |
| `paraphrase_set.py` + rubric | [paraphrase_set.py](../../assistant_axis/gapgen/testing/paraphrase_set.py), [paraphrase_synonym.md](./rubrics/paraphrase_synonym.md) | written by a subagent to my brief, reviewed; the rubric pinned as version 1 (`96302f36a2a0`) in [versions.json](./rubrics/versions.json), listed in `GENERATOR_FILES` of [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) |
| the CLI | [generator_dashboard.py](../../data_analysis/gap_generation/generator_dashboard.py) | `independence`, `review-rate`, `repetition`, `concepts`, `estimate`, `simulate`, `recovery-extras`, `roger-sample` (added), `dashboard`, `paraphrase-set build \| run \| report` |
| the harness additions | [recovery.py](../../assistant_axis/gapgen/recovery.py), [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py), [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py) | `--hidden-file`, `--exclude-stems`, `--exclude-provenance`, `draw_hidden(exclude=)`; and decision 1's `--pooled` and `--affected-only` (below) |

### Decision 1's interface: pooled (d) with affected only (c)

- **`recovery_test.py --pooled`** (no `--generator`/`--run-id`; batch id default `rec_pooled`): selects every
  registry row with an M1 `trait` verdict that counts for a generator after attribution (a states-pass row for its
  source row's generator, followed through further pass rows; the `m1_validation`, `manual` and `testing` pools
  left out), writes the keys to `pooled_keys.txt` in the batch, and scores them once per seed.  The report
  ([recovery_report.md](../../data/candidates/recovery/rec_pooled_1/recovery_report.md) for the batch id the command below uses, not there yet) gives the
  union ("any generator") as its first table, then **per generator and per run** each seed's recall with a Wilson
  95% interval, the mean recall, precision and false-cover candidates.
- **`recovery_test.py --affected-only`**, passed to **`novelty_score.py score --hide H --affected-only`** (with
  `--keys-file`, new, for the 6,662 keys): `recovery.affected_split` decides which rows are scored again; the others'
  recorded `novelty` blocks are written into the reduced-corpus run's
  [results.jsonl](../../data/candidates/novelty/rec_pooled_1_s0/results.jsonl) marked `copied_from: <run id>`, and
  [affected.jsonl](../../data/candidates/novelty/rec_pooled_1_s0/affected.jsonl) lists every row with its reasons
  (both not there yet).  Reasons: no recorded block; the label is a hidden stem or a
  hidden trait's `renamed_from`; the exact-label answer changes; the recorded block names a hidden trait; a hidden
  trait among the traits M3 lists for it now (its 10 nearest, partners and queue entries); a hidden trait among its
  10 nearest in the corpus alone (the match stage's); **its listed set or the cosine floor's cut moves without the
  hidden traits** (added for exactness, QUESTIONS 102); no cached query vector.
- **Exactness.** An unaffected row has no hidden trait near it or in its label, so the match stage judges nothing for
  it: recall and false covers cannot change by copying.  Its M3 inputs are the same with and without the hidden
  traits, so a deterministic judge decides it as recorded, which keeps precision exact.  The acceptance test
  ([test_gap_generation_recovery_pooled.py](../../data_analysis/tests/test_gap_generation_recovery_pooled.py))
  runs the harness on the toy corpus over four seeds with and without `--affected-only`, for one run and pooled, and
  finds the same recall, recovered traits, precision, kept count, false covers and decisions seed by seed; the
  pooled per-generator figures equal separate runs on the same draw (for a generator without states-pass rows;
  with them, the pooled figure also counts the rows attributed to it, which a `--run` selection does not take).  On
  the real registry a copied block is the decision on record, as Roger's (c) put it: 2,412 of the 2,427 copied at
  seed 0 were decided under rule set 3, 15 under rule set 2, some against a smaller corpus; that touches only the
  precision denominator, never recall or the false covers.
- **The guard.** The estimate (each seed's reduced-corpus M3 dry run on the affected rows, plus the match calls
  counted on the full index) is printed before anything is sent and checked against `--budget-usd`; above $20 the
  run needs `--confirm-expensive --confirmed-by`, recorded in [run.json](../../data/candidates/recovery/rec_pooled_1/run.json)
  (not there yet), as [cost.py](../../assistant_axis/gapgen/cost.py) does everywhere.  `--dry-run`
  does everything but the calls and prints the estimate, the affected counts and the rows by generator.

## The dry run of the decision-1 harness (free, 2026-10-13, on the main checkout's registry log)

`recovery_test.py --pooled --affected-only --seed 0 1 --transport batches --budget-usd 68 --dry-run`:

| | seed 0 | seed 1 |
|---|---|---|
| hidden | 96 of 932 traits in 63 groups | 95 of 932 in 63 groups |
| rows scored again / copied | 4,235 / 2,427 (63.6%) | 4,680 / 1,982 (70.2%) |
| reasons (a row may have several) | m3_near 3,651, match_near 3,885, recorded 3,502, retrieval 336 (310 alone), label 45, exact_label 42 | 4,225, 4,452, 4,053, 211 (196), 58, 55 |
| copied blocks | 1,396 new, 1,031 covered; rule set 3 2,412, rule set 2 15 | 1,167 new, 815 covered |
| M3 against the reduced corpus | $17.45 | $19.29 |
| match calls | $7.05 (5,715 pairs) | $8.85 (7,181 pairs) |

**Total estimate $52.64** (under the $68 approved).  Rows: 6,692 pooled (6,743 trait rows, 51 with pool sources
only; 151 of the 6,692 have the states pass as their only generator source and are attributed), **6,662 M3
candidates** (30 held on the nationalities list).  The coordinator's 6,541 left out those 151 (QUESTIONS 101).
By generator (a row counts for each generator that proposed it):

| generator | rows | seed 0 scored / copied | seed 1 scored / copied |
|---|---|---|---|
| censuses | 5,282 | 3,380 / 1,902 | 3,772 / 1,510 |
| base_model | 1,366 | 866 / 500 | 994 / 372 |
| wn_clusters | 583 | 381 / 202 | 430 / 153 |
| ipip | 498 | 329 / 169 | 353 / 145 |
| alignment_sweep | 458 | 267 / 191 | 262 / 196 |
| roget | 380 | 259 / 121 | 266 / 114 |
| antonym_check | 380 | 230 / 150 | 250 / 130 |

**A caution on the estimate.**  On the four recorded harness runs the harness's estimate came in 1.18-1.30 times
under the spend (M3's own estimate 1.27-1.44 times), so this run may spend about $62-69.  With `--budget-usd 68` a
spend that reaches $68 stops the run with every answer kept; it resumes with `--resume` after a new go
(QUESTIONS 103).

## Commands for the two paid steps (from the main checkout, after cherry-picking these commits)

The platform's dirty-tree refusal applies: commit or cherry-pick first.  1. **The paraphrase set** (task 7, live,
about $0.01 for the synonym calls and about $1.5 for the harness, caps $0.5 and $4; gate 2: concept recall over 90%
and the antonym items in pair recovery, a miss goes to Fable as an M3 bug):

```
uv run python data_analysis/gap_generation/generator_dashboard.py paraphrase-set run --budget-usd 0.5
uv run python data_analysis/gap_generation/recovery_test.py --generator testing --run-id paraphrase_set \
    --registry data/candidates/testing/paraphrase_set/registry.jsonl \
    --hidden-file data/candidates/testing/paraphrase_set/hidden.json --seed 0 --budget-usd 4
uv run python data_analysis/gap_generation/generator_dashboard.py paraphrase-set report --batch rec_testing_paraphrase_set
```

The set is already built and committed ([set.jsonl](../../data/candidates/testing/paraphrase_set/set.jsonl),
[hidden.json](../../data/candidates/testing/paraphrase_set/hidden.json): 40 singles and 40 pair poles, 120 traits
hidden in 80 groups); the run writes [responses.jsonl](../../data/candidates/testing/paraphrase_set/responses.jsonl),
[answers.jsonl](../../data/candidates/testing/paraphrase_set/answers.jsonl),
[usage.json](../../data/candidates/testing/paraphrase_set/usage.json),
[run.json](../../data/candidates/testing/paraphrase_set/run.json) and the git-ignored scratch `registry.jsonl`, and
the report [report.md](../../data/candidates/testing/paraphrase_set/report.md) (none there yet).

2. **The decision-1 harness** (batched; Roger approved the budget; the dry run first, then the run, with the
parameters quoted at launch: `--pooled --affected-only` (default: one run, all rows); `--seed 0 1` (the default);
`--transport batches` (default auto); `--budget-usd 68`):

```
uv run python data_analysis/gap_generation/recovery_test.py --pooled --affected-only --seed 0 1 \
    --transport batches --budget-usd 68 --batch-id rec_pooled_1 --dry-run
uv run python data_analysis/gap_generation/recovery_test.py --pooled --affected-only --seed 0 1 \
    --transport batches --budget-usd 68 --batch-id rec_pooled_1 \
    --confirm-expensive --confirmed-by "Roger, 2026-10-13: (d) with (c), two seeds, batched, within about \$68"
uv run python data_analysis/gap_generation/generator_dashboard.py recovery-extras --batch rec_pooled_1
uv run python data_analysis/gap_generation/generator_dashboard.py roger-sample --batch rec_pooled_1
uv run python data_analysis/gap_generation/generator_dashboard.py dashboard --live
```

The run writes [rec_pooled_1](../../data/candidates/recovery/rec_pooled_1/recovery_report.md) and
the reduced-corpus runs [rec_pooled_1_s0](../../data/candidates/novelty/rec_pooled_1_s0/decisions.md) and
[rec_pooled_1_s1](../../data/candidates/novelty/rec_pooled_1_s1/decisions.md) (not there yet);
[roger_sample.md](../../data/candidates/recovery/rec_pooled_1/roger_sample.md) (not there yet) is the manual check
(20 recovered and 20 novel verdicts, seeded) for Roger to mark.  The contamination check: **no exclusion applies**
(no corpus trait came from a generator's own source: `excluded_stems` is empty for every generator; the two files
naming Allport, [extrinsic_allport](../../data/traits/instructions/extrinsic_allport.json) and
[intrinsic_allport](../../data/traits/instructions/intrinsic_allport.json), cite Allport and Ross's religious
orientation scale, not the census list), so no second draw is needed.

## Deviations from the plan, with reasons

1. **The pooled row set** is 6,692 rows (6,662 candidates), not 6,541: the states-pass rows are attributed
   (QUESTIONS 101).
2. **Two affected reasons beyond the plan** (`exact_label`, `retrieval`) make (c) exact (QUESTIONS 102).
3. **`--hidden-file` takes one seed**; the paraphrase set's harness command passes `--seed 0`.
4. **`--send-opus` is not built**: `needs_opus` is empty on all four recorded batches (the hard check), so the
   command lists any such pair and refuses to send.
5. **The first dashboard read the live registry** (`--live`), since the tracked snapshot is 8 keys behind
   (QUESTIONS 106).
6. **Promote share**: effective resolutions only (an undone resolve dropped: 68, not 69, on the TDA batch), pooled
   over both review logs (QUESTIONS 107).  The per-term share counts kept terms only (34 of 174 for the censuses,
   as the plan's 20%); a covered candidate pulled into a group by hand is decided but not a term.
7. **Review rate from the minutes as recorded** (84.1): 204 / 84.1 = 2.43, the plan's hard figure (204 / 84.133 would
   round to 2.42); a span with a break in it is left out of the per-shape times (singleton mean 14.6 s, the plan's 15).
8. **Hard negatives** follow decision 2's prototype (members as opened or resolved; keys added by `extend` left out)
   and leave undone events out: 147 pairs, joined 19 (strict) and 29 (grown), exactly the plan's figures.
9. **The negative set** is 158 names, not 250 (QUESTIONS 104); **`with_another_generator`** in the repetition
   record is the kept terms another generator also proposed (690 for the censuses; the plan's 1,392 was not
   reproduced under any definition I tried; not a hard figure).
10. **Attribution moves the mechanism counts a little**: with the states pass attributed, the strict unit's lexicon
    concepts are 2,478 (the plan's 2,402 without it); the tests reproduce the plan's figures without attribution
    (2,402 / 437 / 319 / 232; m 54, 379, 32; Q1 2,513, Q2 375).
11. **The corpus as an occasion** (Roger's § 1 row 4) is computed as a second estimate: a generator catches a corpus
    trait when one of its rows was covered by it.  The headline Chao2 is over the three mechanisms of the main
    population (lexicon, IPIP, base model); the four-occasion figure with the alignment sweep reproduces the
    plan's baseline.  No masked-LM run exists yet, so it is no occasion.
12. **Repetition tests** live in [test_gapgen_testing_concepts.py](../../assistant_axis/tests/test_gapgen_testing_concepts.py)
    (the plan named a separate file); the decision-1 tests are
    [test_gapgen_recovery_plan13.py](../../assistant_axis/tests/test_gapgen_recovery_plan13.py) and
    [test_gap_generation_recovery_pooled.py](../../data_analysis/tests/test_gap_generation_recovery_pooled.py).
13. **The paraphrase set** (subagent's choices, accepted): `MAX_TOKENS` 2000 (Haiku 5.5 thinks adaptively; only
    tokens produced are billed); a third refusal reason, a paraphrase that contains the trait's own label (4 corpus
    paraphrases); an extra [answers.jsonl](../../data/candidates/testing/paraphrase_set/answers.jsonl) (not there yet); `label_path` (the kept answer still names the hidden trait) beside
    `reasked` (the first did); colliding answer labels get separate senses (`#2`), never merged.
14. **Environment**: the worktree's venv had no pytest, so `uv run pytest` fell back to the main checkout's venv and
    imported the main checkout's `data_analysis`; every count below was run with `uv run --extra dev pytest`.

## Tests (§ 8 commands)

Run with `uv run --extra dev pytest` in the worktree (2026-10-13):

```
uv run pytest assistant_axis/tests/test_gapgen_testing_*.py data_analysis/tests/test_gap_generation_generator_dashboard_cli.py assistant_axis/tests/test_gapgen_recovery.py -q
    159 passed, 2 skipped  (the skips: the acceptance checks of the paraphrase report and the decision-1 batches, not written yet)
uv run pytest assistant_axis/tests/test_gapgen_recovery_plan13.py data_analysis/tests/test_gap_generation_recovery_pooled.py data_analysis/tests/test_gap_generation_recovery_cli.py data_analysis/tests/test_gap_generation_novelty_cli.py -q
    52 passed  (decision 1's harness tests and the harness and M3 CLI suites they extend)
uv run python data_analysis/gap_generation/rubric_pins.py check          exit 0
uv run python data_analysis/check_arrangements.py --quiet                 exit 0
uv run python tools/sync_entity_lists.py --check                          exit 0 (932 entries)
git status --porcelain data/traits data/roles data/seed_queue.json        empty
```

Per file: independence 8, review minutes 8, concepts and repetition 11, estimators 30, simulate 14, recovery extras
6, dashboard 6, paraphrase set 41, acceptance 5 (+2 skipped), the CLI 12, the harness additions 9 + 8.  All test
files are new; no existing test expectation was changed.  Three expectations in my own new tests were computed
wrongly at first and corrected (the code was right): a toy concept table's lexicon count, a toy stop rule whose
term is pre-handled, and the pooled-equals-separate check on a generator that a states-pass row is attributed to.
The tests caught three code bugs, fixed: `--keys-file` read the `#` of a registry key as a comment; a reduced-corpus
M3 run was charged twice in the dashboard's costs; a rebuild kept a backup whenever only the build time changed.

**The whole suite.**  `uv run pytest -q` from the root stops on collection errors (the `tests` packages of
`results_analysis` and `tools` collide, as plan 04's report found), so it was run directory by directory:
`assistant_axis/tests` 3,916 passed, 40 skipped, 3 failed, 8 errors; `data_analysis/tests` 860 passed, 1 failed (my
dashboard backup bug, fixed since: its file now 12 passed); `results_analysis/tests` 193 passed; `pipeline/tests`
232 passed; `tools/tests` 262 passed without [test_boundary_check.py](../../tools/tests/test_boundary_check.py), which needs `.claude/hooks/`, absent from this
sparse worktree.  The 3 failures and 8 errors are the worktree's missing external data, not this build: the OEWN
lexicon ([test_gapgen_wordnet.py](../../assistant_axis/tests/test_gapgen_wordnet.py) `test_real_oewn`,
[test_gapgen_wn_clusters.py](../../assistant_axis/tests/test_gapgen_wn_clusters.py) `test_real_oewn_smoke`,
[test_gapgen_roget_acceptance.py](../../assistant_axis/tests/test_gapgen_roget_acceptance.py)
`test_wn_closure_saturates_at_the_default_depth`) and the Hugging Face tokenizers
([test_generation.py](../../assistant_axis/tests/test_generation.py), 8 errors); `data/external/` is git-ignored and was not linked into the worktree.

## The free results

**Independence** ([independence.json](../../data/candidates/testing/independence.json)), verified against the
code: the plan's table holds.  WordNet's antonym stream (`partner_hint` set) is seeded and its closure independent;
Roget is seeded (gap heads); the census lists, IPIP and the base model independent; the alignment sweep a separate
population; the antonym check seeded (mechanism `corpus`); the states pass, the physical pass, `m1_validation`,
`manual` and `testing` are not generators.  No seeded generator has generator-side hiding, so their recall is
marked harness-side.  Rows per stream: censuses/tda 2,855, censuses/allport 5,558, roget 618, wn_clusters/closure
553 and antonym 108, ipip 514, base_model 1,563, alignment_sweep 467, antonym_check 413 (counts include the
states-pass rows attributed to each).

**Review rate** ([review_rates.json](../../data/candidates/testing/review_rates.json)): `review_tda_1` 354 events,
100.9 wall and **84.1 active minutes** (one break), **204 terms** (176 in the log), 35 promoted, singleton median
12 s (mean 14.6 s), multi-member median 71 s, **25.4 s per member**, **2.43 terms per active minute** (146 an hour),
0.42 accepted a minute.  `review_states_v4`: 13 events, 4 terms, too small to pool.  Promote share per group 51.5%
(TDA batch), **53.5% pooled** (71 groups, 38 promoted; singletons 22 of 42, multi-member groups 16 of 29); per term
20.8%.

**Repetition** ([repetition.json](../../data/candidates/testing/repetition.json)): pre-handled at 3-edges (4-edges):
censuses 7% (2%), base model 10% (4%), WordNet 11% (4%), Roget 8% (2%), IPIP 4% (1%), alignment 9% (1%), antonym
check 7% (1%); attached to the TDA batch: censuses 720 of 2,076 (35%), base model 49%, WordNet 46%, Roget 37%,
antonym check 36%, IPIP 23%, alignment 18%.

**Concept units and estimates** ([concepts.json](../../data/candidates/testing/concepts.json),
[estimates.json](../../data/candidates/testing/estimates.json)):

| unit | units | singletons | largest | kept together | one concept | hard negatives joined | Chao2, three occasions (95%) | four, with alignment |
|---|---|---|---|---|---|---|---|---|
| components_4 | 3,065 | 2,691 | 21 | 39% | 76% | 19 of 147 | 7,344 (6,769-8,001) | 9,391 |
| grown_3, 0.67 | 2,258 | 1,514 | 26 | 54% | 76% | 29 of 147 | 4,412 (4,086-4,790) | 5,234 |
| grown_3, 0.5 | 1,935 | 1,306 | 30 | 64% | 77% | 44 of 147 | 3,621 | 4,295 |
| grown_3, 0.8 | 2,329 | 1,552 | 21 | 51% | 79% | 28 of 147 | 4,548 | 5,421 |
| components_3 (chains) | 1,585 | 1,238 | 1,028 | 99% | 7% | 136 of 147 | 3,798 | 4,652 |

The grown unit at 0.67 lands at 2,258 units (decision 2's prototype 2,256), largest 26 (prototype 23: the tie order
differs).  Coverage (Good-Turing) 27% strict, 34% grown.  With the corpus as an occasion: about **7,090** (strict)
or **4,478** (grown) concepts outside the corpus.  The assumptions are printed with every estimate: a closed
population; unequal catchability and dependent LLM-based occasions both bias N̂ low; so N̂ is a lower bound.

**Simulation** ([simulation.json](../../data/candidates/testing/simulation.json); 200 replicates, N 2,000, four
occasions; the subagent's probit model keeps each occasion's catch rate at 0.15, and its correlation loads on
occasions 1-3, occasion 0 standing for the lexicon):

| scenario | Chao2 bias | Chao2 interval covers N | Chapman (0 x 1) bias | leave-one-out spread |
|---|---|---|---|---|
| equal catchability, independent | -0.9% | 96% | -1.1% | 13.8% |
| heterogeneous, independent | -48.4% | 0% | -61.1% | 7.7% |
| heterogeneous, correlated | -52.8% | 0% | -60.8% | 13.8% |

Both estimators are low under heterogeneity, as the assumptions say; the intervals cover N only when the
assumptions hold.

**The recorded harness batches** ([extras](../../data/candidates/recovery/rec_censuses_2026-10-08-pilot/extras.json)
of each): recall at the run's cut-off and at the strict 4, and pair recovery, seed 0: censuses pilot 19 / 11 / 12
of 83; antonym check 13 / 4 / 17; WordNet pilot 6 / 0 / 4; Roget pilot 1 / 0 / 5.  `needs_opus` is empty in all four.

## The dashboard and the stop rule

[dashboard.md](../../data/candidates/testing/dashboard.md) ([dashboard.json](../../data/candidates/testing/dashboard.json))
reproduces the plan's baseline funnel exactly (rows, M1 trait, M3 kept / covered / exact-label covers per
generator; string recall 517 of 932, 55.5%; censuses 475, base model 352, states pass 90, IPIP 55).  Cost read from
227 records, $317.54 in all: $198.31 attributed to generator runs (censuses $94.02, alignment sweep $34.39,
antonym check $21.78, Roget $14.32, IPIP $11.07, base model $7.48, WordNet $6.02), $119.23 not attributed
(calibration, development probes, corpus regions, the passes' own calls).  The stop rule, over each generator's
undecided, not pre-handled kept terms:

| generator | terms | groups | expected review | expected accepted | accepted per review-minute | per $ |
|---|---|---|---|---|---|---|
| censuses | 2,513 | 1,912 | 783 min (13.0 h) | 1,023 | 1.31 | 10.9 |
| base model | 414 | 366 | 117 min | 146 | 1.25 | 19.6 |
| alignment sweep | 328 | 277 | 95 min | 148 | 1.56 | 4.3 |
| WordNet | 223 | 202 | 61 min | 108 | 1.78 | 18.0 |
| IPIP | 223 | 217 | 56 min | 116 | 2.06 | 10.5 |
| Roget | 206 | 193 | 54 min | 103 | 1.90 | 7.2 |
| antonym check | 126 | 119 | 33 min | 64 | 1.92 | 2.9 |

These rates are three times the TDA batch's measured 0.42 accepted a minute, because the remaining terms are mostly
singletons and decision 3 prices a 15-second singleton at the per-group share of about one half (QUESTIONS 105;
pilot item (c)).  A term two generators share counts in both rows.

**How many distinct concepts are left, per mechanism, and what each costs in review hours.**  Outside the corpus
there are at least about **4,500-7,100** trait concepts (the corpus as an occasion, grown and strict units), of
which the generators have shown 2,000-2,700 in the main population; the three-occasion Chao2 puts the main
population at 4,400-7,300, so **2,400-4,600 are left unseen**, a lower bound.  Per mechanism at twice its present
output: the lexicon walks would add 700-1,300 (end slope 0.05-0.07 new concepts per candidate: near saturation),
the base model 190-250 (slope 0.28-0.33: the richest vein), IPIP about 50 (saturated), the alignment sweep 150-260
in its own population (Chapman N̂ 420-930 there).  Reviewing what is already on the table costs about **13 hours**
for the censuses, **2 hours** for the base model, **1.6** for the alignment sweep and about **1 hour** each for
WordNet, IPIP and Roget, at the measured rate.

## Pilot (§ 10): what Roger decides on the first dashboard

(a) Nothing for decision 1, which is decided; the harness runs after the paraphrase-set gate.  (b) Decision 2's
headline: the agreement table above and the twenty strict and twenty grown units listed at the end of
[dashboard.md](../../data/candidates/testing/dashboard.md).  (c) Whether the per-group share holds across shapes:
singletons 22 of 42, multi-member groups 16 of 29 so far, and the stop rule leans on it (QUESTIONS 105).  (d) Whether
the giant 3-edge component (1,028 candidates) is a review-graph finding worth filing.  **Manual check**: Roger's 20 +
20 verdicts are pending the decision-1 run (`roger-sample`).

## Open QUESTIONS

91-100, plan 13's pre-registered entries (91-93 answered by Roger's decisions); 101-107 new: the pooled rows, the
affected reasons, the cost projection, the negative set, the stop rule's singletons, the registry the dashboard
read, and which resolutions count in the promote share ([QUESTIONS.md](./QUESTIONS.md)).

## Proposed paragraph for [data/README.md](../../data/README.md) (not edited; the platform owns that file)

Links below are relative to [data/README.md](../../data/README.md), where the paragraph would go:

> **`candidates/testing/`** (workstream 13, [coding_plan_13_generator_testing.md](../reports/trait_gap_generation/coding_plan_13_generator_testing.md)):
> the generator dashboard and its parts, rebuilt by
> [generator_dashboard.py](../data_analysis/gap_generation/generator_dashboard.py) `dashboard` after every M3 batch,
> review `apply` and harness run; all enveloped JSON, tracked: [independence.json](./candidates/testing/independence.json),
> [review_rates.json](./candidates/testing/review_rates.json), [repetition.json](./candidates/testing/repetition.json),
> [concepts.json](./candidates/testing/concepts.json), [estimates.json](./candidates/testing/estimates.json),
> [simulation.json](./candidates/testing/simulation.json), [dashboard.json](./candidates/testing/dashboard.json),
> [dashboard.md](./candidates/testing/dashboard.md).  [paraphrase_set/](./candidates/testing/paraphrase_set/) holds
> the matcher's sanity set ([set.jsonl](./candidates/testing/paraphrase_set/set.jsonl),
> [hidden.json](./candidates/testing/paraphrase_set/hidden.json), the run's records, its report; its scratch
> `registry.jsonl` is git-ignored).  A harness batch's `extras.json` (strict column, pair recovery, recall at N) and
> `roger_sample.md` sit beside its report in `candidates/recovery/<batch>/`.

## Commits

On branch `plan13-build`, in order (cherry-pick all of them; the last one carries this report):

- `024001db` tasks 1-4: independence, review minutes and promote share, repetition, concept units, estimators and
  simulation; QUESTIONS 91-100
- `0cf4618e` decision 1: the pooled harness, affected rows only, the fixed hidden list, the exclusions
- `604f6fab` tasks 6-7 (library): recovery extras and the paraphrase set; the rubric pinned
- `bb2fec9f` task 5 and the CLI: the dashboard, [generator_dashboard.py](../../data_analysis/gap_generation/generator_dashboard.py), the frozen interface
- `6c50fea3` the first dashboard from recorded data, the paraphrase set built, the four batches' extras
  ([one of them](../../data/candidates/recovery/rec_antonym_check_pilot_1/extras.json))
- `20bc5bef` `roger-sample`
- `42cae2c3` an affected-only run with nothing to score; per-batch group shares; glossary; QUESTIONS 101-107
- the last commit: the dashboard's backup comparison ignores the build time; this report
