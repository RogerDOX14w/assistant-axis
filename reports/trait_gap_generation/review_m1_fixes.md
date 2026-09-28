# Re-review of the M1 fixes, diff `de5190f..ca80229`

Reviewer: Fable, 2026-09-29.  Follows [review_m1.md](./review_m1.md).  Link targets are relative to
this file; the link text is the path from the worktree root.  "Ran" means executed in the worktree with
scratch under `/tmp` and no API call; "read" means confirmed in the source; "infer" is marked.

## 1. Verdict

**Fit to merge now.**  All six original reproductions give the right result on the fixed code and
nothing the fixes introduced blocks the merge; four follow-ups should be done before a generator runs
at scale, the first two being one-line or near it (section 3, items 1 to 4).

## 2. Per finding

| finding | status | before (de5190f) | after (ca80229) |
|---|---|---|---|
| 1 run id reused | **fixed for sessions in sequence; not for overlapping ones** (section 3, item 1) | second session left `usage.json` at 0 calls, $0; `n_emitted` 0; first `args` gone | 1 call, $0.20 kept; `n_emitted` 2; first `args` kept; 2 sessions listed.  `finish()` twice in one session: 1 session, no double count |
| 2 torn line | **fixed** (one uncovered case, item 4) | report said 2 new, fold held `loyal`, `stubborn` only; `compact` ran, `n_lines_before` 2 | fold holds `loyal`, `stubborn`, `timid`; `n_malformed` 1; `compact` refuses; with `set_aside_malformed` the torn line goes verbatim to the rejected file, backup equals the raw log, 3 keys remain |
| 3 cap over $20 | **fixed** | estimate $15 gave cap $22.50; $19.90 gave $29.85; budget $100 gave $100 | $20.00; $20.00; refused.  With `confirmed_by`: $22.50 and $100.  Below the line unchanged ($6 on $5 gives $9) |
| 4 budget stop, concurrency 4 | **fixed** | 12 started, 8 charged, 5 responses kept, 0 rows with a filter block | 8 started, 8 charged, 8 responses kept (8 on disk), 200 rows with a filter block, 50 `pending` |
| 4, concurrency 1 / 8 | | 7 / 16 started, 6 / 8 charged, 5 kept, 0 rows | 6 / 8 started, charged and kept; 150 / 200 rows |
| 5 re-filter | **fixed in the CLI** | stale `classifier_verdict` kept beside the new block | through `traithood_filter.py`: gone, stale `freq` key gone, `sources` kept.  The library default of `update_many` still merges, as designed |
| 6 `wn` pin | **fixed** | `import assistant_axis.gapgen` left `WN_DATA_DIR` unset | set; 12 of 12 import orders pinned in-tree, including `wn` imported first |
| 9b probe parse failures | **fixed** | never reported | reported with `*** HIGH FAIL RATE ***` (ran the test; it fails on the old code for the right reason) |
| 10 provenance | **fixed going forward** | no prompt hash, dirty tree accepted | `prompt_sha256` in `run.json` and every filter block; dirty tree refused without `--allow-dirty`.  Past batches are annotated; the pilot's hashes are marked inferred, and equal the current text's |
| 11 tests | **partly** | | the listed tests exist, except that the concurrency test does not test the lock (section 4) |
| 12 small items | **fixed** | backup overwritten; revs `[2, 2]`; dry run refused first; exit code 1 | distinct backup paths, first intact; revs `[2, 3]`; dry run prints, then says it would be refused; exit code 2; 80-character limit; 20,000 candidates submit in 0.25 s against 1.04 s |

In every budget-stop run, calls started, calls charged and responses recorded were equal, and no key
was recorded twice: a call that finishes after the stop is charged once and recorded once.  A stop in
the probe stage or the second-opinion stage keeps that stage's paid rows too (ran).

Full suite on the fixed code (ran): 1,542 passed, 6 skipped, 1 expected failure.  The rubric file has
no diff against `de5190f`, and the two prompt hashes are `113bde98...` and `d5ba66e8...`.  No
`usage.json`, `results.jsonl`, `responses.jsonl` or `summary.json` under `data/candidates/` changed.
Not verified: that `review_m1.md` was committed unchanged (I hold no independent copy).

## 3. New defects introduced by the fixes, and gaps they leave

1. **Overlapping sessions of one run id still lose a cost record.**
   [assistant_axis/gapgen/runs.py:96-101, 135-146](../../assistant_axis/gapgen/runs.py).  The on-disk
   state is read once, at a session's first `finish()`, and the read-merge-write holds no lock.  Ran:
   (a) A finishes, B finishes, A finishes again: $3 spent, `usage.json` says $1, sessions `[A]`;
   (b) both read before either writes: `usage.json` says $2, sessions `[B]`.  Scenario: a generator
   that calls `finish()` as a checkpoint while its candidates are submitted through the CLI, or two
   shards sharing a run id.  Fix: give each session an id, store its own usage in its session entry,
   and in `finish()`, under an exclusive lock on the run directory, re-read `run.json`, replace or
   append this session by id, and write `usage.json` as the sum over sessions.  Until then, say in the
   docstring that one run id must not have two live sessions.

2. **An uncaught refusal now exits in silence.**
   [assistant_axis/gapgen/cost.py:96-104](../../assistant_axis/gapgen/cost.py).  `SystemExit(2)` prints
   nothing; before, the message went to stderr.  Ran: a script calling `confirm_or_abort(25, 5,
   confirm_expensive=True)` exits 2 with empty stdout and stderr.  Both generator plans call it
   directly.  Fix: print the reason to stderr inside `confirm_or_abort` before raising.

3. **A failure that is not a budget stop no longer stops the stage.**
   [assistant_axis/gapgen/filter.py:238-246, 296-298](../../assistant_axis/gapgen/filter.py).
   `_gather` now waits for every batch.  Ran: an exception in the first of 40 batches; all 40 requests
   were made and charged before it surfaced (before the fix the rest were cancelled), the failing
   batch's paid response was not recorded, and the CLI, which catches only `BudgetExceededError`,
   would write no `results.jsonl` for the 975 rows classified.  Fix: set the stop flag on any
   exception in a batch, record the response before parsing it, and write results in the CLI's
   `finally`.

4. **A line torn inside a multi-byte character makes the registry unusable.**
   [assistant_axis/gapgen/registry.py:204](../../assistant_axis/gapgen/registry.py).  Not introduced by
   the fix, but not covered by it.  Ran: append, fold and `compact --set-aside-malformed` all raise
   `UnicodeDecodeError`, so the recovery command cannot recover.  Rows are written with
   `ensure_ascii=False`, so this needs only a label such as "naïve" at the cut.  Fix: read with
   `errors="surrogateescape"` and write the rejected file the same way.

5. **Smaller.**  (a) An object line with no `key` is not counted as malformed and `compact` drops it
   without refusing; it survives only in the backup (ran; no library write produces such a line).
   (b) Taking the writer lock while holding the reader lock blocks for ever (ran, 2 s watchdog).  No
   caller does this, and `flock` cannot upgrade safely, so `locked()` should raise if the thread holds
   the shared lock.  (c) The dirty-tree check looks at every tracked file in the repository, so an
   unrelated edited report forces `--allow-dirty` and the flag becomes habit
   ([traithood_filter.py:254](../../data_analysis/gap_generation/traithood_filter.py)); restrict it to
   the platform's code paths.

On the questions asked.  **Locks:** writer inside writer, reader inside writer, and a second
`Registry` object reading inside a writer all complete (ran).  Four processes writing shared keys
lose nothing with the locks on, and lose sources in 3 of 3 runs with them off (ran), so the lock works
across processes.  No deadlock between processes is possible as written, since no code holds two locks
or upgrades one (read).  `flock` promises no fairness, so continuous overlapping readers could starve a
writer; readers here are short and occasional (infer, not run).  Every read now needs a working
`flock`, which a network mount may not give (infer).  **`compact --set-aside-malformed`** loses no
record the library could have written: the torn line is preserved verbatim and the backup is the raw
log; the exceptions are items 4 and 5a.

## 4. Empty or flaky tests

I ran the new tests against the pre-fix code in a scratch copy.  The module does not import there
(`MAX_SURFACE_CHARS` is new), so every test in it fails at collection whatever it checks; that is
how "each one failed against de5190f" comes out true.  With that one import patched, 34 fail and 3
pass.

* **`test_concurrent_submitters` is empty.**  It fails on the old code only because
  `Registry.n_malformed` did not exist; its 200 lines and 200 keys were already right.  With both locks
  replaced by no-ops its workload passes 5 runs of 5, because the four writers never share a key.
  Replace it with shared keys and assert four sources per key.
* **`test_keys_order_and_dedupe_at_scale`** is empty, as admitted: the old code takes 0.05 s for its
  3,000 rows against a 30 s limit.
* **`test_confirmed_by_lifts_the_clamp` and `test_below_line_behaviour_unchanged`** pass on the old
  code.  They guard unchanged behaviour and are worth keeping; the module docstring is wrong about them.
* **`test_finish_twice_in_one_session_does_not_double_count`** fails on the old code on the missing
  `sessions` key, not on a double count.  It would catch one in the new code, so it is not empty.
* `assert 3 <= n <= 4 < 5` (twice): the last comparison is always true.
* **Flakiness: none found.**  The five timing-dependent tests passed 18 runs of 18, six of them with 28
  busy processes.  By reading, the reader-lock test cannot fail from slowness (a thread that has not
  yet run is still alive); the stop tests give `n = 4` on any schedule I can construct, and accept 3.

The other new tests fail on the old code for the reason they name.

## 5. Outside the agreed scope

Nothing strayed into the deferred items: the rubric, the probe wording, the validator, the Zipf floor,
`promote`, and the meaning of a typed budget below $20 are untouched (read; `filter_rubric.py`,
`freq.py` and `promote.py` have no diff).  Three things to know about:

* The `run.json` of all four recorded batches was edited after the fact (keys added, none changed),
  and two marker files were added beside the smoke batches.  This is how finding 10 was handled for
  past runs; the additions are labelled inferred.
* The new expected-failure test on the rubric examples is strict, so the rubric v2 change set must
  remove the marker when it fixes the examples.
* The "M1 as built" section records `sessions`, `prompt_sha256`, `allow_dirty`, `responses_path`,
  `Registry.malformed` and the 80-character limit.  It does not name `n_pending` (it describes the
  pending rows), `probe_rubric_version` in `run.json`, or `paths.pin_wn_data_dir`.

The frozen interface still has only additive drift.  Two behaviours changed under unchanged
signatures, both recorded: surfaces over 80 characters are refused, and a typed budget over $20 is
refused without `confirmed_by`.
