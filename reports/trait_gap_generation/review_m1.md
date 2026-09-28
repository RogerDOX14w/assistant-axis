# Review of M1 (trait-hood filter and candidate registry), diff `62633d8..de5190f`

Reviewer: Fable, 2026-09-28.  Specification: [coding_plan_platform.md](./coding_plan_platform.md) with its
three closing sections.  Link targets are relative to this file; the link text is the path from the
worktree root.  "Ran" means I executed it in the worktree (no API calls, no pilot rerun); "read" means
I confirmed it in the source; "infer" is marked as such.

## 1. Verdict

**Fit to merge after four named fixes.**  The pilot numbers in the readout reproduce from the recorded
outputs, the frozen names are all present with only additive drift, and the test suite is green as
claimed (242 passed / 6 skipped; 1,506 / 6 over the three main directories).  What blocks the merge is
two silent-loss paths in the system of record (a run's `usage.json` is overwritten with zeros when its
run id is reused; a record appended after a torn line is lost while the report says it was stored), a
cost gate that lets the cap pass $20 without `confirmed_by`, and a budget stop that throws away every
classified row it has paid for.

## 2. Must fix before merge

1. **A reused run id overwrites `usage.json` and `run.json`.**
   [assistant_axis/gapgen/runs.py:88-107](../../assistant_axis/gapgen/runs.py),
   [data_analysis/gap_generation/gap_registry.py:63-66](../../data_analysis/gap_generation/gap_registry.py).
   `start_run` always builds an empty `RunContext`, and `finish()` writes both files unconditionally.
   Ran: a run that charged $0.20 and emitted 2 candidates, followed by a second `start_run` + `finish()`
   under the same `censuses/r1` (exactly what `gap_registry.py submit` does), left `usage.json` at 0
   calls, $0, and `run.json` at `n_emitted: 0` with the first run's `args` gone.  Scenario: a generator
   spends money under `censuses/2026-10-06a`, then its candidates file is submitted through the CLI, or
   the generator is resumed in a second process; the cost record is destroyed.  This breaks the
   usage-logging hard rule ("merging into the existing file so resumes accumulate").  Fix: in `finish()`
   load the existing `usage.json` with `MultiModelUsage.load_or_create` and `merge_from` it; keep the
   earliest `started_at`, accumulate `n_emitted`, and append to a `sessions` list in `run.json` instead
   of replacing `args`.  Add a test that runs two sessions on one run id.

2. **A record appended after a torn line is lost, and `SubmitReport` says it was stored.**
   [assistant_axis/gapgen/registry.py:153-164, 182-189, 336-343](../../assistant_axis/gapgen/registry.py).
   `_append` never checks that the file ends in a newline; `iter_lines` skips a malformed line with a
   warning only; `compact` then drops it from the live log.  Ran: after a partial last line (a process
   killed mid-write; a 10,000-row submit is one write of several megabytes), submitting `timid` and
   `loyal` reported `n_new = 2`, but the fold held only `loyal#1`: `timid#1` was glued onto the torn
   line.  `compact` reported `n_lines_before = 2` and made the loss permanent in the log (the `.bak`
   keeps the raw bytes).  Fix: before appending, read the last byte and write a newline first if it is
   not one; `fsync` after the write; have `iter_lines` count malformed lines and `compact` refuse to run
   (or carry them into a `.rejected` file) when the count is not zero.  The existing
   `test_malformed_line_skipped` asserts the skipping and uses a newline-terminated line, so it cannot
   see this.

3. **The cap can exceed the $20 line without `confirmed_by`.**
   [assistant_axis/gapgen/cost.py:104-125](../../assistant_axis/gapgen/cost.py).  The line is tested
   against the estimate only.  Ran: estimate $15 with `--confirm-expensive` returns cap $22.50; estimate
   $19.90 returns $29.85; estimate $1 with `--budget-usd 100` returns cap $100; none needs
   `confirmed_by`.  Scenario: a 15,000-candidate filter run estimated at $16 is allowed to spend $24
   with no recorded go from Roger.  Fix: without `confirmed_by`, clamp the returned cap to `hard_line`
   and refuse `budget_usd > hard_line`.  No test covers this band; add the three cases above.

4. **A budget stop discards every classified row and the responses that tripped it.**
   [assistant_axis/gapgen/filter.py:214-228, 276-303](../../assistant_axis/gapgen/filter.py),
   [assistant_axis/gapgen/llm.py:103-109](../../assistant_axis/gapgen/llm.py),
   [data_analysis/gap_generation/traithood_filter.py:277-286, 302-305](../../data_analysis/gap_generation/traithood_filter.py).
   `classify()` writes into `self.results` only after every batch has returned, and `usage.charge`
   raises before `_call` appends the response record.  Ran (250 items, cap tripping on the sixth call,
   a client that suspends like network I/O, concurrency 4): 12 requests started, 8 charged ($0.156
   against a $0.10 cap), 5 responses kept, **0 rows with a filter block**, all 250 left `pending`,
   `n_llm` unset so the parse rate is `None`.  The module docstring ("keeps partial results, so a caller
   that hits the budget cap can still write what finished") and the CLI docstring ("every API
   response") are both untrue at a stop.  Scenario: a generator-scale run stops at 90% of its cap; the
   registry gets only the free hard rejects, and `--unfiltered` pays for all of it again.  Fix: append
   the response record before charging; store each batch's rows in `self.results` as the batch
   returns; append `responses.jsonl` per call rather than in `finally` (a killed process currently
   loses all of them).  The overshoot itself is bounded (at most `concurrency` further charged calls
   plus `concurrency` started-and-cancelled ones that never reach `usage.json`); say so in the
   docstring.  [test_gap_generation_cli.py:139-151](../../data_analysis/tests/test_gap_generation_cli.py)
   asserts only `n_calls >= 1` and cost `>= 2.0`, with a client that never yields, so it would pass if
   the cap stopped nothing; it should assert an upper bound on calls and that finished rows survive.

## 3. Should fix before M2 builds on it

5. **A re-filter merges into the old `filter` block.**
   [traithood_filter.py:305](../../data_analysis/gap_generation/traithood_filter.py) calls
   `update_many(done)` with the default `merge_blocks=True`
   ([registry.py:225-227](../../assistant_axis/gapgen/registry.py)).  Ran: a row rejected by the v1
   probe and re-filtered as `trait` kept the stale `classifier_verdict` beside `rubric_version: 2`.
   Rubric v2 is already proposed, so this will happen.  Fix: pass `merge_blocks=False` (the runner
   supplies whole blocks).

6. **The `wn` pin depends on import order.**
   [assistant_axis/gapgen/wordnet.py:36-43](../../assistant_axis/gapgen/wordnet.py),
   [assistant_axis/gapgen/__init__.py](../../assistant_axis/gapgen/__init__.py).  Read and ran: no M1
   code path falls back to the home directory (only `gapgen.wordnet` and `setup_external.py`, after it,
   import `wn`; `wn` 1.1.1 honours `WN_DATA_DIR` and touches no file at import; `wordfreq` has no home
   or cache path).  But `import assistant_axis.gapgen`, and its `registry`, `freq`, `cost`, `llm` and
   `promote` modules, leave `WN_DATA_DIR` unset and `wn` unpinned.  Both generator plans read `wn`
   directly; one that does a lookup before setting the directory creates `.wn_data` under the home
   directory.  Fix: set the environment variable in `gapgen/__init__.py` (or `paths.py`) and, if `wn`
   is already in `sys.modules`, assign `wn.config.data_directory` there.
   [test_gapgen_paths.py:33-45](../../assistant_axis/tests/test_gapgen_paths.py) checks a private
   attribute after importing `gapgen.wordnet`, so it cannot fail on the unpinned path; add a
   subprocess test that imports only the package.  Also `oewn()` on a checkout with no
   `data/external/` raises a bare `FileNotFoundError` (infer, from `wn`'s `mkdir` without `parents`).

7. **The mid-pilot validator change loosened more than the bug required.**
   [assistant_axis/gapgen/filter_rubric.py:201-256](../../assistant_axis/gapgen/filter_rubric.py).  The
   diagnosis is right (rubric examples for tagged words show no gloss, region or rank, and Haiku copied
   them), but the rubric text still says the gloss is null only for `reject` and gives a form for
   roles, so the validator now contradicts the prompt.  Ran: a `tagged` row with no tags, no gloss, no
   region and no rank is accepted; so is `trait` with `not_a_word`.  In the pilot 42 of 46 tagged rows
   have no gloss, including every row on the physical and roles holding lists, and 5 have no region.
   Consequences: `holding` prints labels with an empty gloss; a promotable tagged row gives
   `description_draft: null`; M3's `NoveltyQuery.gloss` is required.  Fix in rubric v2: make the
   examples and the gloss rule agree, require at least one tag that fits the verdict, and require a
   gloss for role tags and for any tagged class that can be promoted.

8. **Rows carry no label echo, so misnumbering is silent.**
   [filter_rubric.py:281-313](../../assistant_axis/gapgen/filter_rubric.py).  Ran: a zero-based
   response is accepted with the second item's verdict attached to the first label.  The pilot shows no
   instance (every batch numbered 1..n; stored reasons match the raw rows; one reason names a batch
   neighbour, benign).  Add `"label"` to the row schema and reject a row whose label does not match.

9. **Definition probe.**  The diagnosis is right: all 17 `known: false` reasons I read say the word is
   real but not a personality trait
   ([filter_rubric.py:341-351](../../assistant_axis/gapgen/filter_rubric.py) asks about trait labels and
   "the sense in which a person could have it").  It changed four final verdicts (nippy and rending
   from `trait`, becalmed and purple-veined from `tagged`; purple-veined left the physical holding
   list).  Separately, probe parse failures are counted but never passed to
   `warn_if_low_parse_rate`, and a failed probe leaves the verdict standing
   ([filter.py:320-327, 386-394](../../assistant_axis/gapgen/filter.py)).

10. **Provenance of paid runs.**  All four batches record `git_sha: 0b7e784+dirty`, and nothing records
    which prompt text was sent.  The smoke batch used an earlier draft (`system_prompt_tokens_est`
    1843 against 1924) yet carries `rubric_version: 1`, against the judging rule.  The commit shows
    four wording edits, not the two reported (also the sandbagging senses and the grumpy gloss).
    Fix: write `sha256(SYSTEM_PROMPT)` and of the probe prompt into `run.json` and the filter block;
    refuse a paid run on a dirty tree unless a flag says so; drop or re-version the smoke outputs.

11. **Weak or missing tests.**
    [test_gapgen_filter_rubric.py:23-34](../../assistant_axis/tests/test_gapgen_filter_rubric.py) checks
    that the examples heading contains "reason first, then the verdict"; the twelve negative examples
    give the verdict with no reason and the test still passes.  The corpus-stem check covers only the
    hand-kept lists (my n-gram scan of the prompt found exactly the eleven prose words the implementer
    declared, nothing else).  `test_over_budget_with_flag_raises_cap` and
    `test_refusals` ("a not_adopted stem may come back") assert the implementation's choices, not the
    plan's.  Missing: two sessions on one run id, torn-line append, concurrent submitters (the lock is
    untested), re-filter of a filtered row, cap band $13.34 to $20, import-order pinning.

12. **Smaller items.**  `compact` overwrites its own backup when two runs share a second (ran;
    refuse an existing path).  `Registry.write` gives two records with one key the same `rev` (ran).
    `--dry-run` is refused when the estimate exceeds the budget, before it prints anything
    ([traithood_filter.py:231-239](../../data_analysis/gap_generation/traithood_filter.py)).
    `CostRefused` exits with code 1, its docstring says 2.  Surfaces have no length limit.
    `keys` in `submit_candidates` is built with a list membership test, quadratic at 20,000 rows.
    Unlocked readers can miss a row during an append.  The stability figure comes from two runs with
    the same shuffle seed, so it measures sampling noise and not sensitivity to batch neighbours; use
    a different seed for the task 10 rerun.

## 4. Interface drift table

| name | plan | implemented | harmless? |
|---|---|---|---|
| `Candidate` | eight fields, plus `partner_hint` by resolution | same order, `partner_hint` last | yes |
| `start_run` | `(generator, run_id, *, args=None)` | adds `candidates_dir=None` | yes, additive |
| `RunContext` | `.dir`, `.usage`, `.log()`, `.finish()` | adds `args`, `started_at`, `n_emitted`, `finished_at`, `confirmed_by`, `record_candidates`, `run_json`; `finish(*, n_emitted=None) -> Path` | additive; **behaviour not harmless** (finding 1) |
| `submit_candidates` | `(cands, *, registry_path, run) -> SubmitReport` | same | yes |
| idempotency | per `(generator, run_id, surface, sense_id)` | per `(generator, run_id, lowercased surface, source_ref)` within the key | as resolution 4 requires; a resubmission with a changed `rank`, `score` or hint is ignored |
| `SubmitReport` | `n_submitted, n_new, n_merged, keys` | adds `n_unchanged`, `invalid`, `as_dict()` | yes |
| `sources[]` entry | six fields | adds `partner_hint`, `surface` | yes |
| `freq` block | five fields | adds `familiarity_override` | yes |
| `wordnet` block | `found, n_senses, pos` | adds `n_senses_all`; `n_senses` counts adjective senses when any | additive; meaning of `n_senses` changed, generator plan 02 reads it |
| `filter` block | fifteen fields | adds `classifier_verdict`; `region`, `trait_sense_rank` null on `tagged` rows, `model` null on hard rejects | **not harmless for M3**: region-keyed ordering must accept null |
| `zipf_info` | `(surface)` | adds `familiarity=None, zipf_fn=None` | yes |
| `confirm_or_abort` | `(estimate, budget, *, confirm_expensive, hard_line=20.0)` | adds `confirmed_by=None`; returns the cap, which may exceed `budget_usd` | signature yes; return value see finding 3 |
| `call_anthropic_json` | `-> str \| None` | `async def`; adds `retry_delays`, `meta`; `limiter=None` | plan does not say async; consistent with its sibling in `judge.py`; generator plans must `await` it |
| `run_traithood_filter` | eight keyword parameters | all defaulted, adds `batch_id`, `**kw` | yes |
| `promote` | `(registry, queue, keys, *, dry_run)` | `(records: dict, queue, keys, *, data_dir, dry_run=True, section, min_local_novelty)` | not in the frozen set; differs |
| `compact` | folds, leaves `.bak` | adds `snapshot_path`, `stamp`; returns `CompactReport` | yes |
| `wordnet.oewn()` | resolution 3 | present in `gapgen.wordnet`, not exported from the package | yes |
| package exports | the frozen names | frozen names plus `Registry`, `compact`, `holding_list`, `records_for_status`, vocabularies, paths | additive; task 25 trims |

Nothing was removed or renamed.

## 5. Claims checked

Recomputed from `data/candidates/filter/m1_pilot/` (ran):

| claim | recomputed |
|---|---|
| 367 rows, 85 hard rejects, 282 to Haiku | same |
| parse rate 282/282, second opinion 32/32, probe 35/35 | same; first pass also 282/282 |
| first attempt parsed 93.3% | 263 of 282 classified, 19 failed after two retry calls |
| per-stratum trait / tagged / reject | existing 0.856 / 0.061 / 0.083 (113, 8, 11 of 132); rejects 0.667 / 0.167 / 0.167; physical 0.333 / 0.667 / 0; not_adopted 0.348 / 0.087 / 0.565; random 0.135 / 0.145 / 0.720 |
| existing labels 90.4% of classified | 113 of 125 |
| polysemy 0.51, 0.15 existing, 0.81 random | 143/282, 19/125, 102/126 |
| verdict and tags disagree in 11 rows (3.9%) | 11 of 282, same words |
| three low-confidence reasons contradict the verdict | disciplinary, modern, constructivist; none carries a tag |
| probe: 17 of 35 not known, all random adjectives | same |
| second opinion 32 rows, 4 disagreements | same four words |
| gloss median 19 words, 138 of 160 in band | same; 22 below 18, none above 43 |
| stability 269/282 (95.4%), rank flag 267 (94.7%) | same; per-call input tokens are identical across the two runs, so the prompt was the same |
| 34 of 659 labels below Zipf 2.0; 411 of 1,810 validation rows | 34 (5.16%); 411 (existing 34, not_adopted 22, physical 1, random 354) |
| cost $0.3125, $0.00085 per row, $0.0011 per classified row | `usage.json` arithmetic checks at $1/$5 and $3/$15 |
| full run about $1.7, about $11 per 10,000 | arithmetic follows from the pilot rates |
| Haiku did not cache, Sonnet did | all 14 Haiku calls show 0 written and 0 read; both Sonnet calls read 1,812 |
| test counts | 242 passed / 6 skipped; 1,506 / 6; `results_analysis` and `pipeline` 3 failed / 74 passed, the three in `test_infer_axis_description.py`, which the diff does not touch |
| protected files untouched | the diff changes nothing under `data/traits`, `data/roles`, `data/seed_queue.json`; write sites read one by one |
| every label normalises to its file stem | 659 of 659 traits, 338 of 338 roles; idempotent on all |

Corrections to the readout:

* **Random adjectives at 13.5% `trait` depends on the faulty probe.**  By the classifier's own verdict
  it is 29 of 200, 14.5%, against a 15% target.
* **The rubric is about 1,850 to 1,940 Haiku tokens, not 2,200** (a seven-item call totals 1,938 input
  tokens; 2,200 is rubric plus 25 items).  The conclusion stands.
* **148 output tokens per row includes probe output**; the classifier alone is 139.9.  Reasons are
  20.2% of output characters, gloss 16.6%, senses 8.4% (readout: 21, 17, 10).
* **Sonnet's cache was warm from the first attempt** three minutes earlier (reads only, no write), so a
  cold run costs about $0.006 more.
* **"312/312 on offline reparse"**: I reproduced 282/282 for the classifier's first pass; I did not
  isolate the figure 312.

**The cost claim.**  The code bills `input + round(1.25 x cache writes + 0.1 x cache reads)` at the
input rate, with `input_tokens` taken as the uncached remainder
([llm.py:35-46](../../assistant_axis/gapgen/llm.py)), and prices Haiku at $1/$5 and Sonnet at $3/$15
([judge_pricing.py:63-68](../../assistant_axis/judge_pricing.py)).  All of that, and the 4,096-token
caching minimum for Haiku 4.5 (1,024 for Sonnet 4.6), matches the API reference bundled with Claude
Code, dated 2026-06-24.  I did not check the live pricing page.  Input is about 5% of the classifier's
cost, so the lost saving is immaterial.  `prompt_tokens` in `usage.json` are now cost equivalents, not
token counts; the raw counts are in `responses.jsonl`.

Not verified: whether Anthropic bills a request cancelled in flight; the 1,316-test baseline before
the change; the size of the OEWN download; the smoke run's verdict flips.

About my own conduct: one probe script used Python's default temporary directory (under
`/var/folders`, not `/tmp`); I removed the directory it created.  The harness saved one long grep
output under its own state directory; I did not read it back.  I did not open `.env`.

## 6. Questions for Roger

1. **The Zipf floor (QUESTIONS 7), to be settled before any generator harvests.**  Both generator
   plans drop `hard_reject` words at harvest, so the floor decides what ever reaches the registry.
   Ran: the rubric's own positive examples sandbagging (1.94) and overclaiming (0.0) are hard rejects,
   as are corrigible (0.0) and situationally aware (1.72); so are 34 corpus labels, 19 of which are
   neither compounds nor negations (consequentialist, deontological, anthropocentric, guileless, ...).
   The implementer's option (d) rescues at most 15 of the 34.  Options: (a) keep the floor and accept
   the loss; (b) option (d); (c) make the floor a property of the source: on for dictionary walks,
   where 35% of random adjectives fall below it, and replaced by the probe for curated sources and
   for any candidate with a `gloss_hint`.  I recommend (c), with the probe rewritten first.

2. **M1's quality thresholds: gates or report-and-decide?**  Review amendment 2 names only M2 and M3.
   `test_full_existing_labels_mostly_trait` is a hard assertion that the floor alone makes unreachable
   (cap 94.8%), so the command list cannot be green after task 10.  Options: extend the amendment to
   M1, or change floor and rubric until it passes.  I recommend extending it; tuning a rubric to a
   test is the wrong incentive.

3. **Memberships (QUESTIONS 6).**  Eight of the 19 existing-label misses are memberships the corpus
   admitted on purpose.  Options: count `tagged: demographic` as correct for existing labels, or teach
   the rubric that memberships are traits.  I recommend the first, and then requiring a gloss on those
   rows (finding 7).

4. **Deriving the verdict from the tags (readout decision 1a).**  It repairs the 11 rows but not the
   three contradictions that carry no tag, it would move homebody to the roles list on the strength of
   a tag against the verdict, and it has no rule for a row with both a tagged-class and a reject-class
   tag.  Options: derive mechanically; or treat any disagreement as a trigger for the second opinion
   and keep both.  I recommend the second, plus a rubric line that the reason must address the sense
   being judged.

5. **Stems you have already turned down.**  `promote` refuses corpus and live queue stems, as the plan
   says, but `build_registry` leaves out `not_adopted` and `superseded`, so such a stem is promoted as
   a second queue entry with the same stem.  Options: refuse unless a flag is passed; or allow and
   copy the old `decision` text into `description_notes`.  I recommend refusing by default.

6. **What `--budget-usd` means with `--confirm-expensive`.**  Today the flag raises the cap to 1.5
   times the estimate, above the figure typed as the hard cap.  Options: keep that; or make the flag
   permit the run while the typed budget stays the cap.  I recommend the second.

7. **Probe rewrite (QUESTIONS 8) and second-opinion rate.**  Rewrite the probe to ask only whether the
   word is real and definable: agreed.  The proposed confidence trigger at 0.75 is reasonable for the
   validation run; I have no evidence either way on 5% for generator runs.
