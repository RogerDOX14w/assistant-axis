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
