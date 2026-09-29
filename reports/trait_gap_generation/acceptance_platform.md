# Acceptance report: trait-gap generation platform

Against [coding_plan_platform.md](./coding_plan_platform.md).  One section per milestone; M2 and M3
append theirs.

## M1: trait-hood filter and candidate registry (2026-09-28)

Scope: §9 tasks 1-9 (task 9 ends with the pilot of §10).  Task 10, the full validation run, is **not
run**: it waits for Roger's decisions on the pilot, [pilot_m1_readout.md](./pilot_m1_readout.md).

### What was built (against §5)

| §5 item | file | status |
|---|---|---|
| `__init__.py` (frozen interface re-exports) | [assistant_axis/gapgen/__init__.py](../../assistant_axis/gapgen/__init__.py) | M1 names exported (`Candidate`, `SubmitReport`, `RunContext`, `start_run`, `submit_candidates`, `REGISTRY_PATH`, registry access, vocabularies, paths); M2/M3 names to come |
| `paths.py` | [paths.py](../../assistant_axis/gapgen/paths.py) | done; every path in-tree (tested), ids that could escape a directory refused |
| `normalize.py` | [normalize.py](../../assistant_axis/gapgen/normalize.py) | done |
| `registry.py` | [registry.py](../../assistant_axis/gapgen/registry.py) | done: log fold, `rev`, `Candidate` (with `partner_hint`), `submit_candidates` (merge on same surface with a different `source_ref`, counted in `n_merged`), `new_record`, `merge_block`, `update_many`, `compact` (`.bak` + tracked snapshot), `holding_list`, `records_for_status`; `fcntl` lock for parallel submitters |
| `runs.py` | [runs.py](../../assistant_axis/gapgen/runs.py) | done; `finish()` always writes `usage.json` |
| `cost.py` | [cost.py](../../assistant_axis/gapgen/cost.py) | done |
| `llm.py` | [llm.py](../../assistant_axis/gapgen/llm.py) | done |
| `freq.py` | [freq.py](../../assistant_axis/gapgen/freq.py) | done, with the familiarity override |
| `wordnet.py` | [wordnet.py](../../assistant_axis/gapgen/wordnet.py) | done: `ensure_oewn`, `oewn()`, `sense_info`, `adjective_lemmas` |
| `filter_rubric.py` | [filter_rubric.py](../../assistant_axis/gapgen/filter_rubric.py) | done (rubric v1, probe rubric v1) |
| `filter.py` | [filter.py](../../assistant_axis/gapgen/filter.py) | done |
| `promote.py` | [promote.py](../../assistant_axis/gapgen/promote.py) | done |
| `setup_external.py` | [setup_external.py](../../data_analysis/gap_generation/setup_external.py) | `--wn` done; `--hf-model` is M2 and exits with a message |
| `gap_registry.py` | [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) | done: submit, status, report, holding, compact, promote |
| `traithood_filter.py` | [traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py) | done, with `--run GENERATOR/RUN_ID` |
| (task 9) validation builder | [build_validation_set.py](../../data_analysis/gap_generation/build_validation_set.py) | done, output [m1_validation.jsonl](../../data/candidates/validation/m1_validation.jsonl) |
| M2/M3 modules (`embed`, `representation`, `contrast`, `labels`, `space`, `persona`, `calibrate`, `novelty`, `adjudicate`, `recovery`, and their CLIs) | | out of scope |

Tasks: 1-9 complete; 10 not started (by instruction).  Also: judge-pricing entries for the four
embedding models, `.gitignore` lines (`/data/external/`, `/data/candidates/cache/`, the live registry log
and its `.bak`, lock and tmp files, `/.claude/worktrees/`), `wordfreq` 3.1.1 and `wn` 1.1.1 in
`pyproject.toml` / `uv.lock`, OEWN 2024 installed in `data/external/wn/` (125 MB, gitignored).

### Deviations from the plan, with reasons

Counts (the plan quoted the 2026-09-23 corpus; computed at run time instead):

| plan | actual | note |
|---|---|---|
| 414 existing trait labels | 659 trait files (338 role files) | all 659 are the `existing` stratum |
| 95 `not_adopted` | 129 in the queue; 117 in the stratum | 6 now have corpus files (forthright twice, compassionate, conformist, forgiving, unforgiving), 5 are among the six rejects, 1 duplicate |
| 52 `exists` | 37 | not used in M1 (M3 uses them) |
| "~26 corpus entries tagged physical" | 28 queue entries tagged `physical`, none a corpus file | added a `physical` stratum (28 rows) so the physical routing is tested at all |
| six rejects | all six still have no corpus file; five are `not_adopted` queue entries, engaging is not in the queue | all kept in the `rejects` stratum |
| 1,000 OEWN adjectives | 1,000, from a pool of 20,628 (letters, space, hyphen, apostrophe only; corpus, queue and other strata excluded) | |
| pilot 83 / 19 / 200 | 132 existing / 23 not_adopted / 200 OEWN / 6 rejects / 6 physical = 367 | 20% per stratum; strata of 10 or fewer taken whole |
| pilot about 12 classifier calls, about $0.50 | 12 classifier + 2 probe + 2 Sonnet calls, $0.31 | |
| full run about $2.5 | estimated about $1.7 from pilot rates | not run |

Design and code:

1. **Gloss form**: glosses do not open by repeating the label ("This means being X: ..." in the plan's
   example).  The description rule changed on 2026-09-27 (trait-pairs rule 1), after the plan.
2. **Validator leniency for `tagged` rows** (the first pilot's 93.3% parse rate): a `tagged` row may omit
   gloss, region and sense rank; region then comes from the tag.  `trait` rows still need all three.
3. **Two rubric-wording edits before the pilot**, from a 10-row smoke run
   ([m1_smoke](../../data/candidates/filter/m1_smoke/), $0.01, pre-release draft, noted in its `run.json`):
   `trait_sense_rank` defined as the position of the trait sense in the senses list, and glosses asked
   for at "20 to 40 words (count them)".  Rubric version stays 1: the pilot is its first recorded use.
4. **Rubric words kept out of the corpus**: besides the 18 examples, 8 illustrative words
   (`MENTIONED_WORDS`) are checked against corpus and queue stems; the plan's brief examples (cautious,
   sycophantic, ...) and "economic" were removed from the prompt.  Ordinary prose words that are also
   stems (general, stable, moral, emotional, judge, mean, short, single, straight, dominant, language) remain.
5. **Classifier rows are shuffled across batches** (seed `--shuffle-seed`, default 0), so no batch is all
   one stratum or one generator.
6. **Definition probe** is batched (25 words per call) rather than one word per call; a `known: false`
   answer turns the verdict into `reject` + `too_rare` and keeps `classifier_verdict`.
7. **Second opinion** is recorded beside Haiku's verdict and never replaces it; "prior/LLM disagreement"
   is an evaluative-prior word (40-word list) or a single word missing from WordNet, classified `trait`.
8. **Familiarity override** (interface resolution 4): which generators' `Candidate.score` is a familiarity
   is declared in `freq.FAMILIARITY_GENERATORS` (currently `censuses`, TDA `prop`), since the frozen
   `Candidate` has no field saying so.
9. **Token accounting**: cache writes and reads are charged at 1.25x and 0.1x input
   (`prompt_tokens` in `usage.json` are uncached-rate equivalents).  Haiku 4.5 caches only prompts of
   4,096+ tokens, so the rubric (about 2,200) is not cached on Haiku; Sonnet did cache it.
10. **`start_run(..., candidates_dir=None)` and `paths.run_dir(..., candidates_dir=None)`** gained a
    keyword for tests; additive, the frozen signature still works.
11. **Validation runs never write the registry** (the existing labels must not become candidates); they
    write `results.jsonl` in the batch directory instead.  `summary.json` is a `json_metadata` envelope.
12. **`--overwrite`**: an existing batch directory is refused; with the flag it is moved to
    `<dir>.bak.<UTC>` first.
13. **Layering**: `gapgen/promote.py` imports `data_analysis.seed_entities` (for `build_registry`,
    `corpus_stems`) rather than duplicating them; it works wherever the repo root is on `sys.path`.
14. **`wordnet.sense_info`** counts adjective senses when the word has any, else all senses
    (`n_senses_all` records the total); the polysemy prior is about adjectives.

### Test results

Baseline: `assistant_axis/tests data_analysis/tests tools/tests` 1,316 passed before any change (that
first run used the main checkout's `pytest`, inherited through `VIRTUAL_ENV`, because the worktree
environment lacked the `dev` extra); re-recorded in the worktree's own environment after
`uv sync --extra dev`, with only the 7 new pricing tests added, 1,323 passed (1,316 + 7), 0 skipped; `results_analysis/tests` 3 failed (the known
`test_infer_axis_description.py` failures), 65 passed; `pipeline/tests` 9 passed.  No test needed
`runpod_workspace/` data.

Final (commit of this report):

| command | result |
|---|---|
| `uv run pytest assistant_axis/tests/test_gapgen_*.py data_analysis/tests/test_gap_generation_cli.py assistant_axis/tests/test_judge_pricing.py -q` | 242 passed, 6 skipped |
| `uv run pytest assistant_axis/tests data_analysis/tests tools/tests -q` | 1,506 passed, 6 skipped |
| `uv run pytest results_analysis/tests -q` | 3 failed (same three, pre-existing), 65 passed |
| `uv run pytest pipeline/tests -q` | 9 passed |
| `uv run python data_analysis/check_arrangements.py --quiet` | exit 0 |
| `uv run python tools/sync_entity_lists.py --check` | exit 0 (trait_list 659, role_list 337 up to date) |
| `git status --porcelain data/traits data/roles` | empty; `data/seed_queue.json` unchanged |

The 6 skips are all in [test_gapgen_acceptance.py](../../assistant_axis/tests/test_gapgen_acceptance.py):
they read the full-run outputs (`filter/m1_validation`, `filter/m1_stability`, `corpus_regions.json`),
which task 10 produces.  The pilot's mechanical gates (parse rate >= 99%, usage recorded, no budget stop)
pass.  No existing test's expectation was changed; three assertions in tests written during this work
were corrected before their first pass (a probe-schema index, a float rounding tolerance, a
case-insensitive sort), not behaviour changes.

Warning for the full run: the §8 quality thresholds in `test_gapgen_acceptance.py` are hard assertions,
and on the pilot's numbers two would fail (existing labels 85.6% `trait` against 95%; rejects 3 of 6
flagged against 4).  See QUESTIONS 6 and 7.

### Cost (from the `usage.json` files)

| batch | Haiku 4.5 | Sonnet 4.6 | total |
|---|---|---|---|
| [m1_smoke](../../data/candidates/filter/m1_smoke/usage.json) | $0.0096 (2 calls) | | $0.0096 |
| [m1_smoke2](../../data/candidates/filter/m1_smoke2/usage.json) | $0.0096 (2 calls) | | $0.0096 |
| [m1_pilot_v0_parse_bug](../../data/candidates/filter/m1_pilot_v0_parse_bug/usage.json) | $0.2602 (16 calls) | $0.0819 (3 calls) | $0.3421 |
| [m1_pilot](../../data/candidates/filter/m1_pilot/usage.json) | $0.2357 (14 calls) | $0.0768 (2 calls) | $0.3125 |
| **M1 total** | **$0.5151** | **$0.1587** | **$0.6738** |

### Pilot readout and Roger's decisions

[pilot_m1_readout.md](./pilot_m1_readout.md).  Parse rate 100%; $0.00085 per candidate; existing labels
85.6% `trait` (90.4% of those classified); rejects 3 of 6 flagged; random adjectives 13.5% `trait`;
physical 3 of 6 routed; second opinion 4 of 32 disagree; run-to-run verdict agreement 95.4% on 282 rows.
Decisions pending: (1) rubric wording, verdict/tag consistency, probe rewrite, memberships and the Zipf
floor; (2) keep reasons (recommended); (3) second-opinion rate (keep 10%, add confidence < 0.75); then the
go for task 10 (about $1.7).

### Open QUESTIONS entries

[QUESTIONS.md](./QUESTIONS.md) 1-5 (pre-registered, proceeding under their assumptions) and 6-8 (from
the pilot: memberships, the Zipf floor against the 95% target, the probe).

### Frozen interface: drift

None removed or renamed.  Additions, all from the interface resolutions or additive:
`Candidate.partner_hint: str | None = None` (last field); `SubmitReport` gained `n_unchanged` and
`invalid` after the frozen fields; `start_run(..., candidates_dir=None)`; `RunContext.record_candidates`,
`RunContext.log`, `RunContext.finish(*, n_emitted=None)`; `wordnet.oewn()`.

### M1 as built (after the review fixes, 2026-09-29)

For the agents building M2, M3 and the generators.  The diff review is
[review_m1.md](./review_m1.md); the fixes are listed at the end of this section.

**Interface drift against the plan** (the review's table, section 4, with the status after the fixes):

| name | plan | implemented | notes for consumers |
|---|---|---|---|
| `Candidate` | eight fields, plus `partner_hint` by resolution | same order, `partner_hint` last | harmless |
| `start_run` | `(generator, run_id, *, args=None)` | adds `candidates_dir=None` | additive |
| `RunContext` | `.dir`, `.usage`, `.log()`, `.finish()` | adds `args`, `started_at`, `n_emitted`, `finished_at`, `confirmed_by`, `session_id`, `record_candidates`, `run_json`, `session_json`, `total_usage`; `finish(*, n_emitted=None) -> Path` | each `start_run` is a *session* with its own `session_id`; `finish()` (safe as a checkpoint, and across overlapping sessions and processes) replaces or appends its session under a lock and writes `usage.json` as the sum over sessions; see the `run.json` layout below |
| `submit_candidates` | `(cands, *, registry_path, run) -> SubmitReport` | same | surfaces over 80 characters are refused (listed in `invalid`) |
| idempotency | per `(generator, run_id, surface, sense_id)` | per `(generator, run_id, lowercased surface, source_ref)` within the key | as resolution 4 requires; a resubmission with a changed `rank`, `score` or hint is ignored |
| `SubmitReport` | `n_submitted, n_new, n_merged, keys` | adds `n_unchanged`, `invalid`, `as_dict()` | additive |
| `sources[]` entry | six fields | adds `partner_hint`, `surface` | additive |
| `freq` block | five fields | adds `familiarity_override` | additive |
| `wordnet` block | `found, n_senses, pos` | adds `n_senses_all` | **`n_senses` counts adjective senses (`a` + `s`) when the word has any, else all senses**; plan 02 reads it |
| `filter` block | fifteen fields | adds `classifier_verdict` (only when the probe overturned the verdict) and `prompt_sha256` `{classifier, probe}` | **`region` and `trait_sense_rank` may be null on `tagged` rows; `model` is null on hard rejects** (no call was made); M3's region-keyed ordering must accept null |
| `zipf_info` | `(surface)` | adds `familiarity=None, zipf_fn=None` | additive |
| `confirm_or_abort` | `(estimate, budget, *, confirm_expensive, hard_line=20.0)` | adds `confirmed_by=None`; returns the cap | without `confirmed_by` the cap is clamped to $20 and a typed budget above $20 is refused; below $20, `--confirm-expensive` still raises the cap to 1.5 x the estimate (review question 6, Roger's to decide) |
| `call_anthropic_json` | `-> str \| None` | **`async def`**; adds `retry_delays`, `meta`; `limiter=None` | callers must `await` it; `meta["text"]` holds the response even when a guarded usage raised |
| `run_traithood_filter` | eight keyword parameters | all defaulted, adds `batch_id`, `**kw` (e.g. `responses_path`) | additive |
| `promote` | `(registry, queue, keys, *, dry_run)` | `(records: dict, queue, keys, *, data_dir, dry_run=True, section, min_local_novelty)` | not in the frozen set; differs |
| `compact` | folds, leaves `.bak` | adds `snapshot_path`, `stamp`, `set_aside_malformed`; returns `CompactReport` (`rejected_path`, `n_malformed`) | refuses while the log has malformed lines unless `set_aside_malformed` |
| `wordnet.oewn()` | resolution 3 | in `gapgen.wordnet`, not exported from the package | harmless |
| package exports | the frozen names | frozen names plus `Registry`, `compact`, `holding_list`, `records_for_status`, vocabularies, paths | additive; task 25 trims |

**Units and conventions to know:**

* `prompt_tokens` in every `usage.json` written by the platform are **cost equivalents at the
  uncached input rate** (`input + round(1.25 x cache writes + 0.1 x cache reads)`), not token counts.
  The raw counts per call are in the batch's `responses.jsonl` (`usage_raw`).
* `Registry.fold()` takes a shared lock and records skipped lines in `malformed` / `n_malformed`;
  writers hold the exclusive lock.  Any `wn` use should come after importing
  `assistant_axis.gapgen` (anything in it), which pins the data directory to `data/external/wn`.
* A filter batch's `results.jsonl` can contain `stage: "pending"` rows after a budget stop; they are
  not written to the registry and are picked up again by `--unfiltered` / `--run`.
* A paid filter run with uncommitted changes under `gapgen.runs.PLATFORM_PATHS` (the `gapgen`
  package, the `gap_generation` CLIs, `judge.py`, `judge_pricing.py`, `entity_id.py`, `atomic_io.py`,
  `data/candidates/validation`, `pyproject.toml`, `uv.lock`) needs `--allow-dirty`; edits elsewhere do
  not count.  The filter batch's `run.json` records `git_sha`, `allow_dirty`, `dirty_check` (the paths
  checked and what was dirty), `prompt_sha256`, `rubric_version`, `probe_rubric_version` and, after an
  exception other than a budget stop, `stopped_by_error`.
* `summary.json` of a filter batch has `n_pending` (rows a stop left unclassified) and
  `stopped_by_error` beside `stopped_by_budget`.
* `paths.pin_wn_data_dir()` is the function that pins `wn` in-tree; `gapgen/__init__.py` calls it.
* **Generator run `run.json` layout** (`data/candidates/runs/<generator>/<run_id>/`):
  `{generator, run_id, git_sha, args (the first session's), n_emitted (sum), started_at (earliest),
  finished_at (latest), confirmed_by, cost_usd (sum), sessions: [{session_id, started_at, finished_at,
  git_sha, args, n_emitted, confirmed_by, cost_usd, n_calls, usage}], legacy_usage?}`; `usage.json` is
  the sum of the sessions' `usage` (plus `legacy_usage`, present only for a run first written in the
  earlier layout).  `finish()` and `record_candidates()` hold an exclusive `flock` on
  `<run dir>/.run.lock` (gitignored).
* `confirm_or_abort` prints its refusal reason to stderr before raising (exit 2), so a generator that
  calls it directly does not exit in silence.
* Any exception in a filter batch, not only a budget stop, stops new calls; the CLI still writes
  everything paid for before re-raising.

**Known limits, inferred by the re-review and not tested:**

* `flock` gives no fairness: continuous overlapping readers of the registry could keep a writer waiting
  indefinitely.  Readers here are short and occasional, so this is not expected in practice.
* Every registry read now needs a working `flock` (a shared lock on `registry.jsonl.lock`); a network
  mount that does not provide `flock` would make reads fail or not exclude writers, so keep the
  registry on local disk.

**Review fixes applied (tests in [test_gapgen_review_m1.py](../../assistant_axis/tests/test_gapgen_review_m1.py)
and [test_gap_generation_cli.py](../../data_analysis/tests/test_gap_generation_cli.py)):** 1 run sessions
accumulate; 2 torn last line kept, fsync, malformed lines counted, `compact` refuses or sets them aside;
3 cap clamped at $20 without `confirmed_by`; 4 budget stop keeps rows and responses, per-call
`responses.jsonl`; 5 re-filter replaces the filter block; 6 `wn` pinned whatever is imported first;
9 (second half) probe parse failures reported; 10 prompt hashes and the dirty-tree refusal, smoke batches
marked; 11 the listed tests, plus an expected-failure test for the rubric examples (rubric v2);
12 backups never overwritten, distinct revs, dry-run prints before refusing, exit code 2, surface
limit, linear key handling, locked readers.  Not done here (Roger's decisions or rubric v2): 7, 8, the
first half of 9, the stability-rerun seed (task 10), and review questions 1-7.

**Re-review follow-ups applied** ([review_m1_fixes.md](./review_m1_fixes.md) section 3 and 4; tests in the
"Re-review follow-ups" section of [test_gapgen_review_m1.py](../../assistant_axis/tests/test_gapgen_review_m1.py)
and in [test_gap_generation_cli.py](../../data_analysis/tests/test_gap_generation_cli.py)): 1 overlapping
sessions (session ids, per-session usage, locked `finish()`); 2 refusals print their reason; 3 any batch
exception stops the run, responses recorded before parsing, CLI writes results in a `finally`; 4 lines
torn inside a UTF-8 character are recoverable; 5a keyless object lines are malformed; 5b writer-inside-
reader lock raises; 5c the dirty check covers only the platform's paths.  Test repairs: the concurrency
test now shares keys (it loses sources with the locks off), the scale test is renamed to what it checks,
the always-true comparisons are gone, the module docstring names the tests that pass on the old code.

**Rubric v2, round 1** ([decisions_m1.md](./decisions_m1.md), Roger's decisions of 2026-09-29; tests in
[test_gapgen_rubric_v2.py](../../assistant_axis/tests/test_gapgen_rubric_v2.py)).  What changed for
consumers:

* **Versions.**  `TRAITHOOD_RUBRIC_VERSION = 2`, `PROBE_RUBRIC_VERSION = 2`; the prompt hashes changed
  (classifier `2b5b298e...`, probe `0785cd07...`).  The three `m2rubric_smoke_*` runs used an
  intermediate classifier prompt (`ba7a4316...`) that still carried the withdrawn `primary_use` field;
  each run dir has a `WITHDRAWN_PROMPT.md` saying so.  Filter blocks written by v1 (the pilot) keep
  `rubric_version: 1`.
* **Floor.**  `freq.HARD_REJECT_BELOW = 1.5`; the probe band is 1.5 to 2.5.  Rescue rule 1b sends a word
  below the floor to the classifier and the probe when it is a negation (un-, in-, non-) of a word at or
  above the floor, arrives with a gloss hint, or comes from a curated generator
  (`freq.CURATED_GENERATORS`: `censuses` only; the Roget and WordNet harvest is not curated).  The `freq`
  block gains `rescue` (`negating_prefix` | `gloss_hint` | `curated_source` | `familiarity` | null).
  `zipf_info` gains `gloss_hint=False, curated=False`; `FilterItem` gains `curated`.
* **New filter-block fields** (additive): `alignment_relevant` (bool, asked independently of `region`),
  `membership_kind` (one of `filter_rubric.MEMBERSHIP_KINDS` when the row carries `membership`, else
  null), `tag_disagreement` (bool: a tag belongs to another verdict).  The second-opinion block gains
  the same three fields.
* **Ambiguity (decision 11) held.**  No `primary_use` field; the polysemy flag is the v1 rule unchanged
  (`trait_sense_rank >= 2`, or 3+ WordNet senses with confidence under 0.7), and the review list keeps
  key order.  Kept from decision 11: `relational_only` rejects a word only when none of its senses
  describes a person's character, so a word with a character sense beside a commoner non-person use is
  verdict `trait` (flagged or not by the v1 rule).
* **Tags.**  The classifier's tags are `membership` (with `trait`); `physical`, `state`,
  `transient_only`, `role_person`, `role_thing`, `evaluative_only` (with `tagged`); `relational_only`,
  `not_a_word` (with `reject`).  `demographic` is retired from the classifier and stays in `TAG_VOCAB`
  for v1 records.  A `tagged` row needs at least one tagged-class tag and a `reject` row a reject-class
  tag; a tag from another verdict is allowed, sets `tag_disagreement`, triggers a second opinion, and
  never reroutes the row (decision 4).
* **Holding lists.**  `HOLDING` gains `states`: a `tagged` + `state` row goes to the states queue
  (decision 12), physical to `physical`, roles to `roles`.  `gap_registry.py holding --list states`
  prints it.  A membership is a trait and goes to no holding list.
* **Validator.**  Rows echo their `label`; a mismatch rejects the row.  `trait` and `tagged` rows need
  `region`, `alignment_relevant` and a `gloss`, and `trait` rows a `trait_sense_rank` (1-3); `reject`
  rows may leave them null.  A
  `membership` row needs a valid `membership_kind`.  Reasons are asked for in at most 30 words (not
  enforced; the block records nothing new for it, the parser keeps `reason_words` in memory only).
* **Second opinion.**  Triggers: 10% random, confidence under 0.75, `tag_disagreement`, and the plan's
  prior/LLM disagreement (QUESTIONS 12).
* **Report.**  `gap_registry.py report` keeps key order and adds `alignment_relevant` and
  `membership:<kind>` columns.
* **Quality figures.**  `filter.validation_figures` computes the three M1 figures against 95%, 4 of 6 and
  15%, with every existing label that received `state` or `physical` listed by name and the misses by
  cause; a validation run's `summary.json` carries them as `validation_figures`, and the acceptance
  test reports them as a warning without failing (decision 2).  An existing label counts as correct
  when its verdict is `trait` or it carries `state`, `physical` or `membership`.
* **Promotion.**  `promote(..., reopen_turned_down=False)` refuses a stem or label the queue marks
  `not_adopted` or `superseded`, quoting the decision (and the replacing label for `superseded`, when the
  decision names one); `--reopen-turned-down` lets it through and copies the history into
  `description_notes`.  `seed_entities.build_registry` is unchanged.
* **Summary.**  `summary.json` gains `v2_fields` (counts of `alignment_relevant` true,
  `membership_kind`, `tag_disagreement`, holding lists, floor rescues).
