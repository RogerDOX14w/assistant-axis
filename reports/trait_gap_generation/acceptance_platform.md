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

**Rubric v2, round 2** (open points A, B and C of [decisions_m1.md](./decisions_m1.md), Roger's answers of
2026-09-29; tests in [test_gapgen_rubric_v2_round2.py](../../assistant_axis/tests/test_gapgen_rubric_v2_round2.py)).
Where this section and round 1 disagree, this section holds.

* **Budget (point A, decision 9).**  `cost.confirm_or_abort` returns the typed budget as the cap, always.
  An estimate over the typed budget is refused whatever the flags ("type a larger --budget-usd").  A
  budget or estimate over $20 needs `--confirm-expensive` **and** `--confirmed-by`; that is the flag's
  only use.  The signature is unchanged.  The old 1.5 x estimate cap is gone.
* **Nationalities (point B, decision 3).**  A `membership` of kind `nationality_ethnicity_language` stays
  verdict `trait` but goes to a new holding list, `nationalities` (`normalize.HOLDING`,
  `filter.holding_for(verdict, tags, membership_kind=None)`); `gap_registry.py holding --list
  nationalities` prints it; promotion refuses it.  Other membership kinds are unchanged.  The kind is
  the tag (QUESTIONS 15).
* **Main review list.**  `gap_registry.py report` leaves out rows on any holding list; `--include-held`
  lists them too (QUESTIONS 16).
* **States (point C, decision 12).**  The classifier's `transient_only` folds into `state` (removed from
  `CLASSIFIER_TAGS` and the prompt; a stray one from the model is read as `state`; v1 rows carrying it
  route to `states`).  The classifier sets nothing about plausibility.  The new states pass
  ([`gapgen/states_pass.py`](../../assistant_axis/gapgen/states_pass.py), CLI
  [`gap_generation/states_pass.py`](../../data_analysis/gap_generation/states_pass.py)) has its own
  rubric (`STATES_RUBRIC_VERSION = 1`), two prompts with their own hashes, usage records and the
  filter's cost gate and dirty-tree refusal; outputs go to `data/candidates/states_pass/<batch_id>/`.
  Mode `queue` answers Roger's three steps, reason first (`plausible`, `name_fits`, `suggested_name`,
  `gloss`), and in registry mode writes a `states_pass` block on each row of the `states` list.  Mode
  `corpus` takes existing corpus labels tagged `state` with their corpus descriptions (read only) and
  lists as `exceptions` those whose description reads as a momentary state.
* **Promotion from the states list (item 4).**  A `states` row whose states pass judged a predisposition
  plausible is promoted under the suggested name (when the state's own name does not fit) with the
  pass's draft gloss, tagged `states_queue`, with a note that it came through the states queue; every
  collision check applies to the promoted stem, and the registry's `seed_queue_stem` records it.  No
  judgement, or judged implausible: refused (QUESTIONS 14).
* **Probe v3 (item 5).**  `PROBE_RUBRIC_VERSION = 3`: a word formed regularly from a real word by a
  common prefix or suffix counts as real when its meaning is plain from its parts, whether or not a
  dictionary lists it.  The probe block now records its prompt hash.  `traithood_filter.py
  --probe-only` (validation files only) sends every row to the probe and nothing else, for checking it.
* **Versions and hashes.**  Classifier `9c75829d...` (rubric version still 2, QUESTIONS 17; 3,746
  tokens), probe `23327ebd...` (v3; 300 tokens), states pass queue `4a51b915...` (993 tokens) and corpus
  `20d6a63e...` (434 tokens), both states rubric v1.  Token counts from the count-tokens endpoint.

**Rubric v2, round 3** (open point D of [decisions_m1.md](./decisions_m1.md), Roger's reply "A word with
more then one sense ..." and its four cases; the coordinator's rulings on QUESTIONS 15-17; tests in
[test_gapgen_rubric_v2_round3.py](../../assistant_axis/tests/test_gapgen_rubric_v2_round3.py)).  Where
this section and rounds 1-2 disagree, this section holds.

* **Names and versions.**  "Rubric v2" is the name of the decisions_m1.md change set, not a version of
  any prompt.  Every prompt has its own version, pinned to the sha256 of its text in
  [`gapgen/rubric_versions.py`](../../assistant_axis/gapgen/rubric_versions.py) (`HISTORY`, append
  only); a test fails when a prompt's text changes without a new version and a new pin.  The rule: any
  change to a prompt's text after a paid run has recorded the current version needs a new version.
  Recorded runs are told apart by `rubric_version` and `prompt_sha256`, both on every block.  The
  classifier's version 2 stood for three texts before the table (a withdrawn intermediate, a committed
  text never run, and `9c75829d...`, run in round 2); the table pins 2 to `9c75829d...`.
* **Current prompts.**

  | prompt | version | sha256 | tokens |
  |---|---|---|---|
  | classifier | 3 | `f9af4e2d...` | 4,284 |
  | definition probe | 3 | `23327ebd...` | 300 |
  | plain reading (user text only) | 1 | `e9777505...` | 47 |
  | comparison | 2 | `a6f5cbc6...` | 753 |
  | states pass, queue | 2 | `66b1bebc...` | 996 |
  | states pass, corpus | 1 | `20d6a63e...` | 434 |

  Comparison v1 (`81ca2459...`) ran once, on the development set.  States queue v2 differs from v1 only
  in one example (sulking became moping, since sulking appears in the probe's results);
  `states_pass.RUBRIC_VERSIONS = {"queue": 2, "corpus": 1}` replaces `STATES_RUBRIC_VERSION`.
* **Case 3, `overshadowed` (plain reading and comparison).**  [`gapgen/plain_reading.py`](../../assistant_axis/gapgen/plain_reading.py).
  The plain reading shows the model only "You are <word>." (no system prompt, the prompt of the
  Appendix 2 measurement, temperature 0, one reading, classifier model).  It runs only for a row with an
  intended meaning: in the filter, a classified trait or tagged row with a gloss hint; from the CLI
  [`gap_generation/plain_reading.py`](../../data_analysis/gap_generation/plain_reading.py), a pair file or
  corpus labels with their own descriptions.  A row without an intended meaning makes no call.  The
  comparison (second-opinion model, Sonnet) answers `same`, `related` or `different`, reason first;
  `different` sets `overshadowed`; `related` is a note without the flag.  Sonnet stays the comparison
  model: on the development set Haiku agreed with it on 52 of 60 rows (86.7%, under the 95% bar).
* **Cases 2 and 4 (senses a person can be).**  The classifier now lists `person_senses` (senses that
  can be said of a person, most obvious first, each with a kind: trait, state, bodily, status, role,
  circumstance; senses said only of things are not listed) and `trait_senses_equally_obvious`.  Notes:
  `two_trait_senses` (two trait senses about equally obvious) and `nontrait_person_sense` (verdict trait,
  the obvious sense a trait, another sense a non-trait thing a person can be).  A word whose obvious
  reading is a passing state still gets `state` and goes to the states list.  `gap_registry.py
  judgement-calls [--filter-results F ...]` prints the case-4 rows as a table with the word, its trait
  sense, its other sense and an empty column for Roger's call.  No note rejects a word; no review-list
  reordering.
* **Filter-block schema changes** (for the plan's M2/M3 readers):
  * `rubric_version` is 3 on new rows.
  * new `person_senses`: list of `{"sense", "kind"}` (may be empty).
  * new `trait_senses_equally_obvious`: bool.
  * `senses`: kept; now derived, the `sense` texts of `person_senses` (person senses only; a sense said
    only of things is no longer listed).
  * `trait_sense_rank`: kept; now derived, the 1-based position of the first trait sense in
    `person_senses`, or null.  No longer asked of the model, and no longer capped at 3.
  * `polysemy`: kept, bool; now true when any of the three notes is present.  The v1 rule (rank >= 2,
    or 3+ WordNet senses with confidence under 0.7) is superseded; `derive_polysemy(row, n_senses)`
    keeps its signature and ignores `n_senses`.
  * new `polysemy_notes`: list, a subset of `two_trait_senses`, `nontrait_person_sense`,
    `overshadowed`, in that order.
  * new `plain_reading`: null, or `{"text", "model", "reused", "rubric_version", "prompt_sha256", "at"}`.
  * new `comparison`: null, or `{"reason", "relation", "confidence", "model", "rubric_version",
    "prompt_sha256", "at", "intended_meaning"}` (or `{"error", "intended_meaning"}` when the comparison
    failed after its retry).
  * `prompt_sha256` now has four keys: classifier, probe, plain_reading, comparison.
  * the second-opinion block gains `person_senses`.
  * `summary.json`'s `v2_fields` gains `polysemy_notes` counts and `comparison_relations`.
* **Development and held-out results.**  Development set (30 corpus labels, each with its own
  description and with an unrelated label's; 60 comparisons, Sonnet, comparison v2): expected same:
  23 same, 6 related, 1 different (aristocratic, whose description is a view about bloodline while the
  plain reading is refined manners); expected different: 29 different, 1 related.  Held-out six, run
  once after the prompts were final: `overshadowed` on 1 of 6 (disciplinary); engaging and economic
  `related`; balanced, empowered and emotive `same`.  The recorded target (4 of 6) is not met
  (QUESTIONS 18); the acceptance test records it as a warning.
* **The comparison over every existing label** (not run; needs Roger's go):
  `plain_reading.py --batch-id <id> --corpus --budget-usd 2` (corrected in round 5: the budget 1.5
  first written here is refused, since the tool's estimate is $1.53).  From the development runs'
  usage, $0.00019 a reading and $0.0013 a comparison, so about $0.98 for the 659 traits.

**Rubric v2, round 4** (the fixes of [review_rubric_v2.md](./review_rubric_v2.md), and the three
changes that follow from its questions; tests in
[test_gapgen_rubric_v2_round4.py](../../assistant_axis/tests/test_gapgen_rubric_v2_round4.py)).  Where
this section and rounds 1-3 disagree, this section holds.

* **Seen in development (finding 1).**  A validation run marks each row with the recorded runs it was
  seen in (`meta.seen_in`, from `filter.development_seen`, which reads every recorded filter and
  plain-reading run except the one being scored).  `validation_figures` gives every figure for all rows
  and, under `unseen`, for the rows never seen in development; `n_seen_in_development` counts the rest.
* **`obvious_sense_not_trait` (finding 2).**  A derived note: verdict `trait` with a first listed
  sense that is not a trait (Roger: "unless its most obvious sense isn't a trait").  The reject-stratum
  figure now counts exactly the rows whose `polysemy` flag is set.
* **Tags that do not fit are kept (finding 3, decision 4).**  A row with a verdict and at least one
  known tag is accepted, with `tag_disagreement` set, and gets a second opinion; only a `tagged` or
  `reject` row with no tag fails.  The first answer is no longer replaced by a retry.
* **A reject is a miss (finding 4).**  `existing_label_outcome` scores any `reject` as `floor` (cut or
  probe) or `reject`, whatever its tags.
* **Classifier version 4 (finding 5).**  What changed in the text:
  * sense kinds are four: `trait`, `state`, `physical`, `role`; every membership (circumstance, class,
    family position, affinity, relationship, orientation, place of origin or nationality, age group) is
    a trait sense; `circumstance`, `status` and `bodily` are gone;
  * "A lasting feature of the body is physical; a passing condition of the body is a state.  Hungry is a
    state.  Freckled is physical."  A condition imposed from outside (being snubbed) is a state;
  * one test for the main reading, in its own section: "the one a reader would take from the bare
    instruction "You are <word>.""; "commoner in ordinary use" is gone (settles QUESTIONS 11);
  * a new field `judged_sense`, required for `trait` and `tagged`, names the sense the verdict and the
    gloss are about;
  * every example uses the schema's own field names and shows every field; each one passes the
    validator (a test parses them); "awesome" lists no sense; "loose" and "soft" no longer use corpus
    words; three more corpus or validation words left the examples (silenced, forgiving, harsh);
  * "shorter glosses are not accepted" is gone; the tags rule says a tag of another verdict may be
    given with the reason; the definition of a trait is unchanged.
  States queue version 3 and states corpus version 2 replace validation-file words (listless, single,
  usual; the example exasperated became vexed).  The comparison and plain-reading prompts are unchanged.
* **Hygiene (findings 5, 6).**  Every word of every prompt is checked against the corpus, the queue and
  the validation file; ordinary prose that collides is listed in `gapgen/prompt_hygiene.PROSE_ALLOWED`
  (the frozen comparison prompt's hits separately) and may never open an example.  Example words are
  checked against `assistant_axis/tests/data/gapgen_reserved_words.txt`, built once by the script
  beside it from decisions_m1.md and the probe's results; no test reads those working files.
* **Stops keep readings (finding 7).**  The plain-reading runner stores each reading as it returns, so
  a budget stop in the reading stage keeps every reading paid for (in the filter too).
* **`corpus_regions.json` (finding 8).**  `gap_registry.py corpus-regions --from-filter DIR` writes it
  from a validation run's results, at no cost: every corpus trait -> region, `alignment_relevant`,
  verdict, batch id (nulls for a trait the run did not contain).
* **Pins (finding 9).**  A test checks every version and hash recorded in any `run.json` against
  `rubric_versions.HISTORY`, except the four rubric v1 runs that record no hash and the classifier of
  the three withdrawn smoke batches.
* **`reading_related`.**  A derived note for a `related` comparison, beside `overshadowed` for
  `different`; `polysemy` is true with either.  The held-out figure still counts `overshadowed` only.
* **The corpus comparison raises no flag.**  `plain_reading.py --corpus` records the answers with no
  note and writes `listing.md`: every label with both texts, `different` first, then `related` by
  confidence, then `same`.
* **States promotion needs Roger's confirmed name.**  `promote(..., confirmed_state_names=)` / CLI
  `--confirm-state-name KEY=NAME`; without it a plausible states row is refused and the refusal quotes
  the pass's suggestion.
* **Random adjectives for Roger's marks.**  A validation run writes `random_traits_for_marks.md`: 50
  random adjectives (seed 0) that passed as traits, with an empty column for his mark
  (`validation_figures.oewn_random.sample_for_marks`).
* **Superseded refusals (finding 11).**  When no replacement can be parsed the refusal quotes the
  decision text and no longer claims that none is recorded.
* **Filter-block schema, round 4 additions.**  `judged_sense` (string or null; also in the second
  opinion); `person_senses[].kind` is one of trait, state, physical, role; `polysemy_notes` may also
  hold `obvious_sense_not_trait` and `reading_related`; `rubric_version` 4; `meta.seen_in` on validation
  rows.
* **Prompts now.**  Classifier v4 `51854ac5...` (5,568 tokens), probe v3 `23327ebd...` (300), plain
  reading v1 `e9777505...` (47), comparison v2 `a6f5cbc6...` (753), states queue v3 `6790603b...`
  (994), states corpus v2 `bf464b84...` (434).
* **Cost of the full run.**  Superseded in round 5 (below): the figures first written here costed the
  stability rerun as a second full pass and gave the corpus comparison a budget its own estimate
  exceeds.  The corrected table is in the round-5 section.

**Rubric v2, round 5** (the fixes of [review_rubric_v2_fixes.md](./review_rubric_v2_fixes.md), section
4, and finding 11 of the earlier review; tests in
[test_gapgen_rubric_v2_round5.py](../../assistant_axis/tests/test_gapgen_rubric_v2_round5.py)).  No prompt,
version or pin changed.  Where this section and the rounds above disagree, this section holds.

* **The validator repairs instead of refusing (defect 1, blocking).**  A refused row is asked again and
  the second answer replaces the first, so the validator no longer refuses for two causes.  A person
  sense of unknown kind is dropped (`dropped_sense_kind:<kind>`); a `trait` or `tagged` row with a null
  `judged_sense` takes its first listed sense (`judged_sense_from_first_sense`) or, with none listed,
  stays null (`judged_sense_missing`).  A `trait` row left with no trait sense still fails.  The
  repairs are listed on the row and in the filter block (`validator_repairs`), and counted in
  `summary.json` (`v2_fields.validator_repairs`).  Re-parsed offline, the classifier responses of the
  sample batch `m2rubric_r5_sample_1` now parse 126 of 126 rows on the first pass (122 of 126 before):
  endless and abominable (`tagged`, `evaluative_only`, no sense; `judged_sense_missing`), clinical and
  virulent (a `relational_only` sense dropped).  No other row changed.
* **Measurement runs (defect 2).**  `traithood_filter.py --measurement` and `plain_reading.py
  --measurement` record `"measurement": true` in run.json; a corpus comparison always does.
  `filter.development_seen` leaves such runs out, so the full run does not make every later row count
  as seen.
* **The stability mode (defect 2).**  `traithood_filter.py --stability` sets `--sample-frac 0.13
  --sample-seed 1 --shuffle-seed 1` and `--measurement`: 241 rows, 210 of them to the model.  It refuses
  `--sample-frac` beside it, and a sample that sends fewer than 200 rows to the model.  The acceptance
  test compares verdicts through `filter.stability_agreement`, which leaves out rows the frequency
  floor cut in either run (31 of the 241; they agree by construction).
* **Judgement calls (defect 4, finding 11).**  `gap_registry.py judgement-calls` lists the
  `obvious_sense_not_trait` rows first, then the `nontrait_person_sense` rows, with a note column, and
  shows Roger's call from [judgement_calls.json](../../data/candidates/judgement_calls.json) (tracked,
  keyed by word) in the last column.  `gap_registry.py judgement-call --word W --call TEXT` records a
  call; a later call on the same word replaces it.
* **Smaller fixes.**  An assertion in
  [test_gapgen_filter.py](../../assistant_axis/tests/test_gapgen_filter.py) is out of its comment (it
  passes); the allowlist test now parses the classifier examples and refuses an allowlisted word in a
  sense or `judged_sense`, with `elected` (senator) and `general` (awesome) the two known exceptions
  until the prompt next changes; a figure with no rows has `meets_target: null`; stale docstrings and
  the retired kind `bodily` in a test fixture are corrected.
* **The full run, stage by stage.**  Not run; each needs Roger's go.  Commands from the repository root
  (prefix `uv run python`); estimates are the tools' own dry runs on this commit, except the states
  pass, which cannot be dry-run until the filter's results exist; the right-hand column is the review's
  figure at the recorded rates ([review_rubric_v2_fixes.md](./review_rubric_v2_fixes.md), section 5).

  | stage | command | budget | dry-run estimate | at recorded rates |
  |---|---|---|---|---|
  | filter, 1,810 rows (1,552 to the model, 258 cut, 330 probed) | `data_analysis/gap_generation/traithood_filter.py --batch-id m1_validation --validation-file data/candidates/validation/m1_validation.jsonl --measurement --budget-usd 5` | 5 | $3.68 | $2.6 to $3.0 |
  | stability rerun, 241 rows (210 to the model) | `data_analysis/gap_generation/traithood_filter.py --batch-id m1_stability --validation-file data/candidates/validation/m1_validation.jsonl --stability --budget-usd 1` | 1 | $0.60 | $0.4 to $0.5 |
  | corpus comparison, 659 labels | `data_analysis/gap_generation/plain_reading.py --batch-id m1_corpus_comparison --corpus --budget-usd 2` | 2 | $1.53 | $0.97 |
  | states pass, about 130 rows | `data_analysis/gap_generation/states_pass.py --batch-id m1_states_queue --mode queue --filter-results data/candidates/filter/m1_validation/results.jsonl --budget-usd 0.5` | 0.5 | about $0.11 (by the estimator's formula) | $0.12 with the next row |
  | its corpus check, about 38 labels | `data_analysis/gap_generation/states_pass.py --batch-id m1_states_corpus --mode corpus --filter-results data/candidates/filter/m1_validation/results.jsonl --budget-usd 0.5` | 0.5 | about $0.02 | |
  | **in all** | | | **$5.9** | **$4.1 to $4.5** |

  After the filter, `gap_registry.py corpus-regions --from-filter data/candidates/filter/m1_validation`
  writes `corpus_regions.json` at no cost.

## M2: metric calibration (2026-10-01 to 2026-10-02)

Scope: §9 tasks 11-19.  All done; task 19 wrote [metric_config.json](../../data/candidates/metric_config.json)
after Roger's decisions of 2026-10-02 ([coding_plan_platform.md](./coding_plan_platform.md), "M2 final
settings and the M3 design", commit 362f466).  The readout, newest round first, is
[pilot_m2_readout.md](./pilot_m2_readout.md); terms of art link to [glossary.md](./glossary.md) on first use.

### What was built (against §5)

| §5 item | file | status |
|---|---|---|
| `embed.py` | [embed.py](../../assistant_axis/gapgen/embed.py) | done: OpenAI `text-embedding-3-large` with the direct key; [local models](./glossary.md#local-model) `BAAI/bge-large-en-v1.5` ([CLS pooling](./glossary.md#cls-pooling)) and `google/embeddinggemma-300m` (sentence-transformers) on [MPS](./glossary.md#mps), loaded only from `data/external/hf/`; a hash embedder for tests; the npz cache with manifest; `embed_texts` charges every call.  Task 19 added the [drift canary](./glossary.md#drift-canary) (`canary_texts`, `check_canary`, `canary_applies`) |
| `setup_external.py --hf-model` | [setup_external.py](../../data_analysis/gap_generation/setup_external.py) | done, allow-listed files only |
| `representation.py` | [representation.py](../../assistant_axis/gapgen/representation.py) | done: one text function for both sides; [representations](./glossary.md#representations) `full`, `noprefix`, `w20`, `w14`, `strip`, `dup` |
| `contrast.py` | [contrast.py](../../assistant_axis/gapgen/contrast.py) | done: census parser, mechanical cuts with hand overrides ([contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json)), [minimal pairs](./glossary.md#minimal-pairs) |
| `labels.py` | [labels.py](../../assistant_axis/gapgen/labels.py) | done: [labelled pairs](./glossary.md#labelled-pairs) seeded and hand-checked ([labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json)), folds that never split a pair |
| `space.py` | [space.py](../../assistant_axis/gapgen/space.py) | done: `raw`, [centred](./glossary.md#centred), `centred_pc1`, `centred_pc3`, regularised [ZCA](./glossary.md#zca), and Roger's [partial whitening](./glossary.md#partial-whitening) `pw1` to `pw64` (12 and 24 added in round 4); `k_for_variance`, the [residual](./glossary.md#residual), [CSLS](./glossary.md#csls) |
| `persona.py` | [persona.py](../../assistant_axis/gapgen/persona.py) | done: the 8-slot set, slot 6, layer 25, [soft shear](./glossary.md#soft-shear) L = 3, [leave-one-out](./glossary.md#loo) residual yields |
| `calibrate.py` | [calibrate.py](../../assistant_axis/gapgen/calibrate.py) | done: [tasks (a), (b), (c)](./glossary.md#tasks-abc), [hubness](./glossary.md#hubness), [thresholds](./glossary.md#thresholds), drop-or-merge, histograms, the contrast ablation ([criteria (a)-(j)](./glossary.md#contrast-criteria)), the [two settings](./glossary.md#two-settings) (round 3); the plan's `write_metric_config` is `final_metric_config` with `FINAL_SETTINGS` (task 19) |
| (not in §5) `calibrate_llm.py` | [calibrate_llm.py](../../assistant_axis/gapgen/calibrate_llm.py) | Haiku paraphrases in three pinned styles (criterion g and round 4), the Sonnet [blinded comparisons](./glossary.md#blinded-comparisons) (built, not run) |
| (not in §5) `retrieval.py` | [retrieval.py](../../assistant_axis/gapgen/retrieval.py) | round 4: [recall@k](./glossary.md#recall-at-k), [McNemar's test](./glossary.md#mcnemar), the [paired bootstrap](./glossary.md#paired-bootstrap) by trait, [Holm's adjustment](./glossary.md#holm), the round-4 summary and tables |
| `MetricConfig` (§5 put it in `novelty.py`) | [metric_config.py](../../assistant_axis/gapgen/metric_config.py) | done, re-exported from `assistant_axis.gapgen`; the schema of task 19 (below) |
| `calibrate_metric.py` | [calibrate_metric.py](../../data_analysis/gap_generation/calibrate_metric.py) | done: the pilot / full calibration, `--round4`, `--write-config`; every embedding run checks the canary |
| `novelty.py`, `adjudicate.py`, `recovery.py`, `novelty_score.py`, `recovery_test.py` | [novelty.py](../../assistant_axis/gapgen/novelty.py), [adjudicate.py](../../assistant_axis/gapgen/adjudicate.py), [recovery.py](../../assistant_axis/gapgen/recovery.py), [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py), [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py) (none exists yet) | M3, not started |

Outputs: [data/candidates/calibration/](../../data/candidates/calibration/) (described in
[data/README.md](../../data/README.md)) and [metric_config.json](../../data/candidates/metric_config.json).
Documentation: [data/README.md](../../data/README.md) (candidates, calibration, the config, `external/hf/`) and
[data_analysis/README.md](../../data_analysis/README.md) (the three modes of `calibrate_metric.py`).

### The config as written (task 19)

- **Models**: live OpenAI `text-embedding-3-large`; EmbeddingGemma an inactive fallback with its own
  `w20`-centred numbers, never mixed into a run's results; bge listed as dropped.
- **Covered**: [retrieve, then judge](./glossary.md#retrieve-then-judge): `w20`, centred on the fixed corpus
  mean, [cosine](./glossary.md#cosine), k = 10; the query is a candidate's gloss without its label, cut to 14 words; contrast clauses
  kept.  Recall from [retrieval_round4.json](../../data/candidates/calibration/retrieval_round4.json):

  | query source | queries | recall@1 | recall@5 | recall@10 | recall@20 |
  |---|---|---|---|---|---|
  | paraphrase (round 3) | 659 | 0.939 | 0.999 | 1.000 | 1.000 |
  | plain paraphrase | 659 | 0.871 | 0.991 | 0.997 | 0.997 |
  | terse paraphrase | 659 | 0.936 | 1.000 | 1.000 | 1.000 |
  | [M1 gloss](./glossary.md#m1-gloss), run 1 | 554 | 0.691 | 0.931 | 0.978 | 0.987 |
  | M1 gloss, run 2 | 567 | 0.693 | 0.940 | 0.972 | 0.984 |
  | pooled | 3,098 | 0.835 | 0.975 | 0.990 | 0.994 |

  `t_hi` 0.403 and `t_lo` 0.238 (round 3) are kept as information, marked `used_for_decisions: false`.
- **Directional**: `w20`, centred, residual outside the top K = 10 directions (provisional; [K_95](./glossary.md#k95) is 376);
  task (c) [Spearman](./glossary.md#spearman) 0.30 at K = 10, 0.26 / 0.27 / 0.21 at 20 / 40 / K_95; stability
  under rewording 0.64 at K = 10; the caveat that task (c) is a proxy is stored with it.
- **Canary**: 8 texts ([absentee](../../data/traits/instructions/absentee.json), [collectivistic](../../data/traits/instructions/collectivistic.json), [edgy](../../data/traits/instructions/edgy.json), [gay](../../data/traits/instructions/gay.json), [ironic](../../data/traits/instructions/ironic.json), [only child](../../data/traits/instructions/only_child.json), [restless](../../data/traits/instructions/restless.json), [sycophantic](../../data/traits/instructions/sycophantic.json);
  chosen by a fixed rule and stored), threshold cosine 0.999.  At the final write OpenAI's lowest was 0.99960
  ([ironic](../../data/traits/instructions/ironic.json); the other seven 0.99999 or above) and EmbeddingGemma's 1.0.

### Deviations from the plan, with reasons

1. **Two settings, not one** (Roger, round 3): the embedding serves two uses in M3, "is it covered?" and "does
   it add a direction?", tuned separately; task (b) (duplicate against antonym) is left to the LLM.  The §6
   single-setting fields stay readable as properties of the covered block.
2. **Retrieval instead of thresholds** (Roger, 2026-10-02): the labelled duplicates could not set a covered
   threshold (`t_hi` below `t_lo` everywhere, [QUESTIONS.md](./QUESTIONS.md) 26); paraphrases could, but at
   95% recall over round 4's 3,098 queries the line put 61% of the recorded antonym pairs on the covered
   side.  M3 now retrieves k = 10 and judges with LLM calls; the plan's decision rule, `PolarityProbe` and
   the M3 tests of §8 that assume thresholds are superseded and rewritten by the M3 brief.
3. **Models**: the plan's local model (Qwen3-Embedding-0.6B) was replaced at launch by bge-large and
   EmbeddingGemma (launch decisions 1-2); bge was dropped after round 3 (lowest recall, highest false-covered
   rate); EmbeddingGemma stays as an inactive fallback, OpenAI is live ("use the best").
4. **The M2 targets restated** (plan section, item 5): `auc_dup_vs_distinct >= 0.85` and
   `paraphrase_recall_top1 >= 0.95` belonged to the threshold design; the gate is now recall@10 >= 0.95 on the
   M1-gloss queries for the configured setting (0.978 and 0.972: met).  The old two are computed and
   reported as a warning: 0.600 and 0.939 for the configured setting (neither met).
5. **Representation**: the plan's `full` became `w20`, descriptions cut to 20 words (round 4: level with or
   ahead of `w14` on every query source but one, really ahead for EmbeddingGemma).  `w14` (launch decision
   4) and `dup` (Roger, round 2) were measured and not chosen.
6. **Space variants**: partial whitening (Roger, round 2) was added to the plan's five; no N made a real
   difference to retrieval in round 4's paired tests, so the config uses plain centring.
7. **Persona yields recomputed** (plan 12 step 1): the May 2026 basis was not saved; the pool's K_95 is 170,
   not 37, and task (c) uses K = 37 with 10/20/40 beside it.
8. **Criterion (e)**: Roger's 30 blinded marks were a coin flip (13 kept, 16 stripped, 1 same), so the Sonnet
   judge was not run; the clauses stay.
9. **Task 19 additions**: the drift canary (Roger's item 1); the round-3 rule's proposal stays in
   [summary.json](../../data/candidates/calibration/summary.json) marked superseded and is no longer a valid
   config; `--write-config` builds the config from the recorded outputs instead of a fresh full run (all
   inputs cached, about $0.0001 of canary calls).
10. **Corpus**: M2 ran on this worktree's 659 trait files before the merge (launch decision 3).

### Test results

Final (code as of commit 2f3cbcd; this report's commit changes documents only):

| command | result |
|---|---|
| `uv run pytest assistant_axis/tests/test_gapgen_*.py data_analysis/tests/test_gap_generation_cli.py assistant_axis/tests/test_judge_pricing.py -q` | 762 passed, 2 skipped (M1 ended at 242 passed, 6 skipped) |
| `uv run pytest -q` | stops at collection with the same 4 errors as before M2 (`results_analysis/tests`: `test_infer_axis_description.py`, `test_standardize_axis_spec.py`, `test_steering_response_curves.py`, `test_whitening_shear.py`, from the two `tests` packages); count unchanged |
| `uv run pytest assistant_axis/tests data_analysis/tests tools/tests -q` | 2,026 passed, 2 skipped |
| `uv run pytest results_analysis/tests -q` | 3 failed (the three known `test_infer_axis_description.py` failures, as in M1), 65 passed |
| `uv run pytest pipeline/tests -q` | 9 passed |
| `uv run python data_analysis/check_arrangements.py --quiet` | exit 0 |
| `uv run python tools/sync_entity_lists.py --check` | exit 0 (trait_list 659, role_list 337 up to date) |
| `git status --porcelain data/traits data/roles` | empty |

The 2 skips are the real local-model smoke tests in
[test_gapgen_embed.py](../../assistant_axis/tests/test_gapgen_embed.py), which run only with
`GAPGEN_RUN_LOCAL=1`.  The M2 acceptance tests in
[test_gapgen_acceptance.py](../../assistant_axis/tests/test_gapgen_acceptance.py) all run and pass against the
recorded outputs and the written config (12 passed).

**Changed test expectations** (approved with the design change; plan section "M2 final settings and the M3
design", item 5, and Roger's go for task 19):

- [test_gapgen_acceptance.py](../../assistant_axis/tests/test_gapgen_acceptance.py): `test_m2_targets_reported`
  now reports the two old targets for the configured setting as a warning; new
  `test_m2_retrieval_recall_gate` gates recall@10 >= 0.95 on the M1-gloss sources; new
  `test_m2_metric_config_validates`.  `test_m2_mechanical_gates` (changed in round 4) takes [usage.json](../../data/candidates/calibration/usage.json)'s
  cumulative total from the latest run record, since partial runs (`--round4`, `--write-config`) add to it
  without rewriting round 3's [summary.json](../../data/candidates/calibration/summary.json).
- [test_gap_generation_cli.py](../../data_analysis/tests/test_gap_generation_cli.py):
  `test_calibrate_write_config_waits_for_roger` (expected exit 2) became
  `test_calibrate_write_config_refuses_without_recorded_outputs`.
- [test_gapgen_calibrate.py](../../assistant_axis/tests/test_gapgen_calibrate.py): the round-3 proposal no
  longer loads as a `MetricConfig`.
- [test_gapgen_metric_config.py](../../assistant_axis/tests/test_gapgen_metric_config.py): rewritten for the
  final schema.

### Cost (from [usage.json](../../data/candidates/calibration/usage.json), cumulative)

| round | Haiku 4.5 | OpenAI embeddings | local models | total |
|---|---|---|---|---|
| rounds 1-2 (pilot, `dup`, partial whitening) | | $0.019 (19 calls, plus an estimated 3 for a stopped run, [usage_notes.md](../../data/candidates/calibration/usage_notes.md)) | free | $0.019 |
| round 3 (paraphrases, criterion g) | $0.321 (34 calls) | $0.029 (26 calls) | free | $0.350 |
| round 4 (two paraphrase sets, retrieval test) | $0.522 (66 calls) | $0.005 (10 calls) | free | $0.526 |
| task 19 (three config writes, canary only) | | $0.0001 (3 calls) | free | $0.0001 |
| **M2 total** | **$0.8425** (100 calls) | **$0.0523** (61 calls) | bge 349 calls, EmbeddingGemma 426 calls | **$0.895** |

Against the launch cap of $10 and the estimates of about $0.03 for the pilot and $1 for the paid criteria.

### Roger's decisions, by round

- **Launch (2026-10-01)**: download bge; EmbeddingGemma as a comparison arm; run on the worktree's corpus;
  gloss length measured as a variant; the contrast census recomputed; stop after the pilot; cap $10.
- **After the pilot and round 2 (2026-10-01)**: no drop-or-merge pass now (recorded as a TODO in
  [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md)); keep bge until the experiments end;
  `sentence-transformers` approved; try partial whitening and a doubled gloss (both measured in round 2);
  tasks (a) and (c) serve different uses and are tuned separately, (b) goes to the LLM; paid criterion (g)
  yes, (e) no; Roger marked the 30 blinded comparisons himself.
- **After round 3**: the contrast clauses stay; bge dropped; K = 10 for the directional setting,
  provisionally; a significantly larger covered test with real statistics; the M3 retrieve-then-judge design
  agreed in outline.
- **After round 4 (2026-10-02)**: the design confirmed; covered OpenAI `w20` centred cosine k = 10;
  directional `w20` centred K = 10 (provisional); OpenAI live, EmbeddingGemma inactive fallback, bge out of
  the config; the targets restated; task 19 go.

### Open questions and items for M3

- [QUESTIONS.md](./QUESTIONS.md): 24 (dependency) answered; 25 (K) answered, K provisional; 26 closed by the
  design change; 27 (clauses) answered.  No M2 question is open.
- K = 10 is judged only through a proxy; nothing yet tests recovery of genuinely missing traits (plan 13's
  recovery hook is where that belongs).
- The frozen `recovery_test` hook matches hidden traits "at the config's `t_hi` (strict) and `t_lo` (loose)";
  under the new design those are information only, so the M3 brief has to restate the hook.
- The canary's margin for OpenAI is narrow on one text ([ironic](../../data/traits/instructions/ironic.json), 0.99960 against 0.999).  It was the same at
  each of three checks, so it reflects how that text's cached vector was made rather than noise; if it ever
  trips, re-embedding that one text into the cache is the remedy.
- The fallback does not meet the restated target itself (EmbeddingGemma recall@10 0.915 and 0.935 on the M1
  glosses); switching to it would need a decision, not just a flag.
- Roger's drop-or-merge TODO in [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) is his.

### Frozen interface: drift

None removed or renamed: `MetricConfig`, `MetricConfig.load(path=METRIC_CONFIG_PATH)` and `config_version`
keep their names and signatures (tested in `test_frozen_interface_unchanged`).  Additions: properties `k`,
`live_model`, `fallback_model`, `canary`; `thresholds` now returns an empty dict when the block has none, and
the block it returns carries `used_for_decisions: false` and a `note` beside the per-model entries.
`validate_payload` is stricter (it requires `covered.k`, `covered.retrieval`, `models.live` and `canary`, and
an inactive fallback), so a config of the round-3 shape no longer validates; none was ever written.
`MetricConfig` lives in [metric_config.py](../../assistant_axis/gapgen/metric_config.py), not [novelty.py](../../assistant_axis/gapgen/novelty.py) (M3's, not written yet), and is re-exported from
`assistant_axis.gapgen` as the interface specifies.

### Merged with the main line (2026-10-02)

The branch merged `anthropic-vllm-uv` (merge commit 8c1ba30): the trait corpus regenerated under the
instruction rubric V2 and the clean-pair recheck.  The corpus went from 659 to 663 traits: 17 renamed (each
file records `renamed_from`), 4 new ([civilizationist](../../data/traits/instructions/civilizationist.json),
[lenient](../../data/traits/instructions/lenient.json), [malign](../../data/traits/instructions/malign.json),
[neglectful](../../data/traits/instructions/neglectful.json)), 13 descriptions rewritten, and three pairs
dissolved ([benign](../../data/traits/instructions/benign.json) / [malicious](../../data/traits/instructions/malicious.json), [analytical](../../data/traits/instructions/analytical.json) / [systems thinker](../../data/traits/instructions/systems_thinker.json), [detached](../../data/traits/instructions/detached.json) /
[empathetic](../../data/traits/instructions/empathetic.json)).  Roger's decisions of the
same day, and what was done:

- **Classifier prompt v6.**  [lenient](../../data/traits/instructions/lenient.json) is now a corpus label, and the old single-call classifier's "soft"
  example used it ("mild and lenient"), which the prompt-hygiene test rejects.  The example now reads "mild and
  undemanding" (a near-duplicate of the corpus trait, clear of the corpus, the queue, the validation file, the
  99 split test words and the reserved words); version 4 -> 6, pinned in
  [rubric_versions.py](../../assistant_axis/gapgen/rubric_versions.py).  5 was skipped because a split filter
  block's `rubric_version` is 5 and the seed queue copies that number without the pipeline.  The split
  filter's prompts were unaffected.
- **Corpus regions.**  [corpus_regions.json](../../data/candidates/corpus_regions.json) covers all 663 traits:
  642 unchanged from [m1_validation_r2](../../data/candidates/filter/m1_validation_r2/results.jsonl), 15
  renamed traits carried over from their old stem's row (their descriptions kept their sense), and 6 from a new
  run of the split filter ([new_corpus_labels_2026_10_02](../../data/candidates/filter/new_corpus_labels_2026_10_02/results.jsonl),
  input [new_corpus_labels_2026_10_02.jsonl](../../data/candidates/validation/new_corpus_labels_2026_10_02.jsonl);
  live, `--measurement`, $0.053): the 4 new traits plus [dull](../../data/traits/instructions/dull.json) (was
  bland: the description moved from a flat voice to a presence that draws no one in) and
  [metaphysical libertarian](../../data/traits/instructions/metaphysical_libertarian.json) (rewritten to the
  metaphysical sense only).  Every entry keeps its `batch_id`; [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py)
  `corpus-regions` now takes several runs and follows `renamed_from`.
- **Calibration refresh** ([calibrate_metric.py](../../data_analysis/gap_generation/calibrate_metric.py)
  `--round4 --rebuild-labels`, then `--write-config`; $0.045):
  [labelled pairs](./glossary.md#labelled-pairs) rebuilt from the current arrangements, renames followed (antonym
  284 -> 286, duplicate 79, near-distinct 34, in [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json);
  the hand decisions in [labelled_pairs_curation.json](../../data/candidates/calibration/labelled_pairs_curation.json)
  all still apply, one through a rename; two exclusions added there for the dissolved pairs that the v4 antonym
  judgements, [trait_antonyms_v4.json](../../data/traits/trait_antonyms_v4.json), would otherwise re-add);
  34 paraphrases generated in each of the three sets (21 new stems and the 13 rewritten descriptions, whose old
  paraphrases each cache now marks as written from another text); the [M1-gloss](./glossary.md#m1-gloss)
  queries follow renames (10 and 11 glosses carried to the renamed trait) and lose one query each (bland's,
  whose trait changed sense: 554 -> 553, 567 -> 566).  [metric_config.json](../../data/candidates/metric_config.json)
  rewritten; the settings are unchanged, and the [drift canary](./glossary.md#drift-canary) keeps its eight texts
  (it had been re-picked on every config write; fixed).

[Recall@k](./glossary.md#recall-at-k) for the configured setting (OpenAI, `w20`, [centred](./glossary.md#centred),
[cosine](./glossary.md#cosine)), from the refreshed [retrieval_round4.json](../../data/candidates/calibration/retrieval_round4.json);
the table above has the 659-trait figures:

| query source | queries | recall@1 | recall@5 | recall@10 | recall@20 |
|---|---|---|---|---|---|
| paraphrase (round 3) | 663 | 0.938 | 0.999 | 1.000 | 1.000 |
| plain paraphrase | 663 | 0.875 | 0.991 | 0.997 | 0.997 |
| terse paraphrase | 663 | 0.932 | 1.000 | 1.000 | 1.000 |
| M1 gloss, run 1 | 553 | 0.696 | 0.931 | **0.973** (was 0.978) | 0.987 |
| M1 gloss, run 2 | 566 | 0.689 | 0.942 | **0.970** (was 0.972) | 0.984 |
| pooled | 3,108 | 0.835 | 0.975 | 0.989 | 0.994 |

The restated target (recall@10 >= 0.95 on both M1-gloss sources) still holds.  Four M1 glosses fell just past
the tenth place (ranks 11 to 14: [ambiguity tolerant](../../data/traits/instructions/ambiguity_tolerant.json),
whose description was rewritten, [motivated-reasoning-immune](../../data/traits/instructions/motivated_reasoning_immune.json),
[pragmatic](../../data/traits/instructions/pragmatic.json), [intellectually honest](../../data/traits/instructions/intellectually_honest.json));
none rose back.  The paired tests reach the same verdicts: no [partial whitening](./glossary.md#partial-whitening)
is real, EmbeddingGemma `w20` over `w14` is real at k = 1 and 5, OpenAI `w20` over `w14` is not
([Holm](./glossary.md#holm)-adjusted [McNemar](./glossary.md#mcnemar) p 0.52 at k = 5).  EmbeddingGemma's recall@10 on the M1 glosses is 0.913 and 0.929 (the inactive fallback still misses the
target).  The canary's lowest cosine is 0.99960 for OpenAI ([ironic](../../data/traits/instructions/ironic.json),
as before) and 1.0 for EmbeddingGemma: it passes.

Not refreshed: the full calibration (round 3's [loo_metrics.json](../../data/candidates/calibration/loo_metrics.json),
[paraphrase_metrics.json](../../data/candidates/calibration/paraphrase_metrics.json),
[drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md), the histograms) still describes the
659-trait corpus, and the config reads its information-only figures (the old targets, the
[directional](./glossary.md#two-settings) [K](./glossary.md#k95) sensitivity and stability) from it.  A rerun takes about 40 minutes and about a cent.

Tests after the merge: `uv run pytest assistant_axis/tests/test_gapgen_*.py data_analysis/tests/test_gap_generation_cli.py
assistant_axis/tests/test_judge_pricing.py -q` gives 777 passed, 2 skipped (762 and 2 at M2's close; the
new tests cover renames, stale paraphrases, multi-run regions and the canary); the changed expectations are the
classifier's version number (4 -> 6) and the M1-gloss counts dictionary, which gained two keys (`renamed`,
`not_in_corpus`); the calibration CLI tests now read the corpus size instead of hard-coding 659.  Cost of the merge work:
$0.098 (Haiku $0.097 for the filter run and the paraphrases, OpenAI embeddings $0.0001).
