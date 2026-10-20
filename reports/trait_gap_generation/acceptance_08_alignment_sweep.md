# Acceptance: workstream 8, the alignment sweep (2026-10-10)

Against [coding_plan_08_alignment_sweep.md](./coding_plan_08_alignment_sweep.md).  Built: tasks 1-11 as code with
tests, and run as far as the plan goes before Roger's decision on the pilot (task 5): fetch, chunk, the 30-chunk
pilot, the dedup threshold on 30 labelled pairs, the enactability gate on its 30 gold items, the label probe on the
pilot's labels.  **Not run, waiting for Roger**: the full extraction, the submission, M1 and M3, the gate on kept
rows, the readout, the gold recovery, variant B.  The pilot's readout, with the decisions:
[pilot_readout.md](../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/pilot_readout.md).  Spend: **$0.849**
of a $12 cap.

## Built (§ 5)

| file | what |
|---|---|
| [`__init__.py`](../../assistant_axis/gapgen/generators/alignment_sweep/__init__.py) | `GENERATOR`, the paths |
| [`sources.py`](../../assistant_axis/gapgen/generators/alignment_sweep/sources.py) | 14 sources with URL, kind, licence line, check date, read-only flag, weight, version pin; `DEFAULT_FETCH`, `VARIANT_B_SOURCES`, `SKIPPED`, `quote_limit` |
| [`fetch.py`](../../assistant_axis/gapgen/generators/alignment_sweep/fetch.py) | `fetch_all` (manifest in `data/external/alignment_sweep/FETCH_MANIFEST.json` and the tracked [sources_manifest.json](../../data/candidates/alignment_sweep/sources_manifest.json)), `fetch_transient` (Krakovna, never written) |
| [`chunk.py`](../../assistant_axis/gapgen/generators/alignment_sweep/chunk.py) | headings (CommonMark fences, nested), HTML via the standard library, long sections split at paragraphs, rows; `chunks.jsonl` rebuilt byte for byte |
| [`extract.py`](../../assistant_axis/gapgen/generators/alignment_sweep/extract.py) | the extraction and rewrite calls, items, drops, `label_ok`, quote policy, resume and reuse, summary |
| [`dedupe.py`](../../assistant_axis/gapgen/generators/alignment_sweep/dedupe.py) | gloss embeddings through the cache, groups, partner hints, weighted threshold tuning, pairs to label |
| [`submit.py`](../../assistant_axis/gapgen/generators/alignment_sweep/submit.py) | `to_candidates`, the downstream estimate at the censuses' rates, `run_submit`, follow-up commands |
| [`gate.py`](../../assistant_axis/gapgen/generators/alignment_sweep/gate.py) | the enactability gate, two readings, `score_against_gold`, the gold and kept-row inputs |
| [`probe.py`](../../assistant_axis/gapgen/generators/alignment_sweep/probe.py) | the Qwen label probe, DeepInfra (US) only, `refloor` |
| [`report.py`](../../assistant_axis/gapgen/generators/alignment_sweep/report.py) | rows, rank, readout, gold recovery, `gold_hidden_doc` |
| [`alignment_sweep.py`](../../data_analysis/gap_generation/alignment_sweep.py) | the CLI: `fetch`, `chunk`, `extract`, `dedupe`, `submit`, `gate`, `probe`, `report` |
| rubrics [alignment_extract.md](./rubrics/alignment_extract.md), [alignment_rewrite.md](./rubrics/alignment_rewrite.md), [enactability_gate.md](./rubrics/enactability_gate.md) | pinned as version 1 in [versions.json](./rubrics/versions.json) (registered in `split_rubrics.GENERATOR_FILES`) |
| [gold_alignment_traits.json](../../data/candidates/alignment_sweep/gold_alignment_traits.json), [gate_gold_items.json](../../data/candidates/alignment_sweep/gate_gold_items.json), [dedup_labeled_pairs.json](../../data/candidates/alignment_sweep/dedup_labeled_pairs.json) | the gold sets and the labelled pairs (with the tuned threshold) |
| tests | `test_gapgen_alignment_sweep_{sources,chunk,extract,dedupe,submit,gate,probe,report,acceptance}.py` in [assistant_axis/tests](../../assistant_axis/tests/) (fixtures in [alignment_sweep_fakes.py](../../assistant_axis/tests/alignment_sweep_fakes.py)), [test_gap_generation_alignment_sweep_cli.py](../../data_analysis/tests/test_gap_generation_alignment_sweep_cli.py) (the whole command chain end to end with fakes) |

## Sources manifest: licence and version lines

From [sources_manifest.json](../../data/candidates/alignment_sweep/sources_manifest.json):

- `model_spec`: licence CC0 1.0 Universal; the line found in the fetched LICENSE: "Creative Commons Legal Code /
  CC0 1.0 Universal"; pin `7f1cf79` (commit `7f1cf79fcb656c07f77c8d95b6fbc78dc7fac5b6`, "Release 2026-08-18");
  276,131 bytes, sha256 `a52378c1ae75...`.
- `constitution`: licence CC0 1.0; the line found on the page: "We're releasing Claude's constitution in full under a
  Creative Commons CC0 1.0 Deed, meaning it can be freely used by anyone for any purpose without asking for
  permission."; pin "captured 2026-10-10, sha256 2595700f3a31" (the page prints no version); 634,726 bytes.

Not fetched (waiting for the go on the full extraction): the two usage policies (read-only), the seven failure-mode
papers (arXiv licences read 2026-10-10: CC BY 4.0 for sandbagging, ELEPHANT and agentic misalignment; arXiv's
non-exclusive licence, so read-only, for sabotage evaluations, alignment faking, in-context scheming and emergent
misalignment), the glossary; variant B's Krakovna list (no licence, never stored) and MACHIAVELLI (MIT).

## Deviations, with reasons

1. **Worktree setup.**  The worktree was created from `master` (the upstream base, a989619); the plan and the code
   are on `anthropic-vllm-uv`, so the branch was moved onto 31a1a62 (`reset --mixed`, then the files written from
   the index; nothing local existed).  The sandbox refuses to create `.claude/` in this worktree, so its 19 files
   (rules, hooks, settings) are absent and show as unstaged deletions: they are never staged (every commit names
   its paths), [test_boundary_check.py](../../tools/tests/test_boundary_check.py) cannot run here, and every run record's `git_sha` carries
   `+dirty` from those deletions alone (the platform-paths check before each paid run was clean).  The rule files
   were read from the main checkout.
2. **The worktree's venv had no pytest** (it is the optional `dev` extra), so `uv run pytest` fell through to the
   main checkout's venv and interpreter, and tests under `data_analysis/tests` imported the main checkout's
   `assistant_axis`.  Fixed with `uv sync --frozen --extra dev` (the worktree's venv only; the lock unchanged).
   Every count below is from this worktree's venv.  Other agent worktrees made the same way likely have the same
   problem.
3. **HTML is parsed with the standard library**: `beautifulsoup4` is only a transitive dependency here (plan 07's
   approval to add it belongs to that worktree), and [pyproject.toml](../../pyproject.toml) is off limits.
4. **Ids.**  Chunk ids and `source_ref` use the source key (`model_spec:2026-08-18:avoid_sycophancy`, not
   `modelspec:...`).  Item ids are `<short><chunk ordinal>-<item>{a,b}` (`ms041-1a`) rather than `ms-041a`, so an
   item keeps its id whichever chunks a run extracts.
5. **The extraction's answer** names both poles explicitly (`virtue`, `vice`) with `source_pole`, instead of
   `label` / `partner_label`; the rows of `extraction.jsonl` have the plan's fields plus `pole`, `names_source`,
   `label_kind`, `label_problem`, `reason`.
6. **`extract` takes `--run-id`** (the plan's command line has none) and `--reuse-from RUN`, which reuses answers
   to byte-identical prompts, so the pilot's 30 answers carry into the full run if the prompt is unchanged.
7. **Source weight 2 for the whole constitution**, where plan 08 step 7 says "constitution safe-behaviors and
   Model Spec 2"; its other chapters (honesty, helpfulness, nature) are no less alignment-specific.  One constant
   in [sources.py](../../assistant_axis/gapgen/generators/alignment_sweep/sources.py) if Roger wants the narrower
   reading.
8. **Dedup threshold rule**: weighted errors (a false merge twice a missed one), not plain accuracy (QUESTIONS 57);
   grouping is per pole, exact stems first; the same surface on the other pole is submitted as `sense_id` 2.
9. **The gate keeps the more visible reading on a flip**, so a split vote never drops a trait.
10. **The probe's prompt is a module constant** (`PROMPT_VERSION` 1, its sha256 in `probe.json`), not a pinned
    rubric file (the plan names three rubric files).  How "known" is decided (Qwen's definition against the gloss
    by embedding, floor 0.30) is a design choice the plan left open (QUESTIONS 58); the prompt was reworded before
    its first run ("What does the expression ... mean", not "call someone ..."), which verb-phrase labels need.
11. **`submit` gates M3 at 1.5 times** its estimate (the plan's noted upward risk for cut-off-4 rows).
12. **`report --gold`** is the fallback for interface request 1 (QUESTIONS 60): `gold_hidden.json`, a no-call first
    reading from the run's own M3 blocks, and the `novelty_score.py score --hide` command.
13. **`fetch` downloads the Model Spec and the constitution by default**; the other sources wait (QUESTIONS 61).
14. **`GENERATOR_FILES` in [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py)** (a platform file)
    gained the three rubric names: it is how the generators' rubrics are pinned (Roget's two are there);
    [rubric_versions.py](../../assistant_axis/gapgen/rubric_versions.py) was not touched.
15. I overwrote a sibling agent's scratch file `hygiene_check.py` in the shared session scratchpad (scratch only;
    my later scratch files carry an `as08_` prefix).

## Commands of § 8

| command | result |
|---|---|
| `uv run pytest assistant_axis/tests/test_gapgen_alignment_sweep_*.py data_analysis/tests/test_gap_generation_alignment_sweep_cli.py -q` | 113 passed, exit 0 |
| `uv run pytest -q` | stops at collection (exit 2): the 4 known `results_analysis/tests` errors (the two `tests` packages, as in [acceptance_platform.md](./acceptance_platform.md)) and [test_boundary_check.py](../../tools/tests/test_boundary_check.py) (needs the hooks directory, absent here; deviation 1) |
| `uv run pytest assistant_axis/tests data_analysis/tests tools/tests pipeline/tests --ignore=tools/tests/test_boundary_check.py -q` | 3,463 passed, 5 skipped, 6 failed, exit 1: the six known environmental failures of a worktree (`test_gapgen_paths.py` 5, `test_gapgen_embed.py::test_hf_cache_is_inside_repo`: `data/external` and the cache are symlinks to the main checkout); the baseline before this work was 3,350 passed with the same six, so the 113 new tests account for the difference |
| `uv run pytest results_analysis/tests -q` | 68 passed, exit 0 |
| `uv run python data_analysis/check_arrangements.py --quiet` | exit 0 |
| `uv run python tools/sync_entity_lists.py --check` | exit 0 (trait_list 932, role_list 339 up to date) |
| `uv run python data_analysis/gap_generation/rubric_pins.py check` | exit 0 (`alignment_extract`, `alignment_rewrite`, `enactability_gate` at version 1) |
| `git status --porcelain data/traits data/roles data/seed_queue.json` | empty |

## The pilot and Roger's decisions

The pilot readout has the numbers, the spot read, the projection and the rendered samples.  In short: 30 chunks,
parse rate 30/30, **165 pairs (5.5 a chunk against 1-2.5)**, 160 behaviour / 5 belief-state / 0 mechanism, 147 chat /
18 agentic-only; label rule's bite 1.8% (six five-word labels; the model flagged none of its own); one polysemy
flag; 311 of 330 glosses in the first person; spot read 5 of 10 pairs clean.  Roger decides (readout § "What you
decide"): the prompt (a draft 2 is suggested, unpinned), partner balance, belief-state items, the go for the full
extraction, the gate's gold labels, the two thresholds.

## Counts and costs (pilot run, from usage.json)

raw 330 poles (165 pairs) -> 324 kept (6 dropped by the label rule) -> 312 dedup groups -> **not submitted**; M1 and
M3 not run.

| step | model | calls | USD | estimate |
|---|---|---|---|---|
| extract | claude-sonnet-5-5 | 30 | 0.6455 | 0.583 |
| dedupe | text-embedding-3-large | 2 | 0.0012 | 0.0015 |
| gate (gold) | claude-sonnet-5-5 | 60 | 0.1953 | 0.279 |
| probe | qwen/qwen3-32b (+ 2 embedding calls) | 314 | 0.0066 | 0.0092 |
| total | | | 0.8486 | |

## M1's model-per-generator measurement and the tripwire

Not run: they come with M1 on the submitted run (the `--third-model claude-opus-5-5` follow-up `submit` prints).

## The gate

Gold: agreement 25 of 30 (target 26), flip rate 6.7% (target at most 10%): **advisory only**.  chat 10/10,
agentic-only 7/10, none 8/10; three of the five misses are arguable gold labels (QUESTIONS 59).  Not yet run on
kept rows.  [gate_gold_eval.md](../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/gate_gold_eval.md).

## The probe

Host and country: **DeepInfra, United States** (`ALLOWED_PROVIDERS`), pinned, `allow_fallbacks: false`; listed
before the first request.  0 responses from another host.  At the floor of 0.30: 287 of 312 labels known in the
intended sense, 17 in another sense, 8 unknown to the model.

## Gold recovery and the A-vs-B comparison

Not run: they need the full run's M3 (and variant B needs Roger's go after A's readout).

## Open QUESTIONS entries

46-55 (pre-registered, § 12) and 56-61 (from the pilot) in [QUESTIONS.md](./QUESTIONS.md).

## What awaits Roger, with the commands

After his decision on the prompt (if it changes: edit the block, `rubric_pins.py bump alignment_extract --why '...'`,
and rerun the pilot under a new run id), the full extraction, in the worktree or the main checkout:

    uv run python data_analysis/gap_generation/alignment_sweep.py fetch --only anthropic_aup openai_usage sabotage_evals alignment_faking in_context_scheming sandbagging emergent_misalignment elephant agentic_misalignment
    uv run python data_analysis/gap_generation/alignment_sweep.py chunk
    uv run python data_analysis/gap_generation/alignment_sweep.py extract --run-id <R> --variant A --reuse-from 2026-10-10-pilot --budget-usd 6
    uv run python data_analysis/gap_generation/alignment_sweep.py dedupe --run-id <R>
    uv run python data_analysis/gap_generation/alignment_sweep.py submit --run-id <R> --dry-run

Then the submission and the platform's M1 and M3 (the step this session did not take; at the pilot's volume the
downstream estimate is over $20, so it needs his recorded go and, by the batch-or-real-time rule, batches):

    uv run python data_analysis/gap_generation/alignment_sweep.py submit --run-id <R> --budget-usd <gated estimate> [--confirm-expensive --confirmed-by '<Roger, date>']
    uv run python data_analysis/gap_generation/gap_registry.py submit --from data/candidates/runs/alignment_sweep/<R>/candidates.jsonl   # main checkout
    uv run python data_analysis/gap_generation/traithood_filter.py --batch-id <R>_alignment_sweep --run alignment_sweep/<R> --pipeline split --transport live --budget-usd <cap> --third-model claude-opus-5-5
    uv run python data_analysis/gap_generation/novelty_score.py score --batch-id <R>_alignment_sweep --run alignment_sweep/<R> --transport live --budget-usd <cap>
    uv run python data_analysis/gap_generation/alignment_sweep.py gate --run-id <R>
    uv run python data_analysis/gap_generation/alignment_sweep.py probe --run-id <R>
    uv run python data_analysis/gap_generation/alignment_sweep.py report --run-id <R> --gold

(`submit` prints the M1 and M3 lines with the caps filled in from its estimate.)  Interface request 1
([recovery_test.py](../../data_analysis/gap_generation/recovery_test.py) `--hidden-stems`) is not built; `report
--gold` prints the fallback.

## Proposed [data/README.md](../../data/README.md) paragraph (task 13; the file not edited)

> **`candidates/alignment_sweep/`** (workstream 8): the sweep's tracked inputs: `sources_manifest.json` (what was
> fetched, with licence lines and version pins; the texts are in the git-ignored `external/alignment_sweep/`), the
> ten-trait recovery gold set `gold_alignment_traits.json`, the enactability gate's `gate_gold_items.json`, and
> `dedup_labeled_pairs.json` (hand-labelled gloss pairs with the tuned dedup threshold).  Its runs are under
> `candidates/runs/alignment_sweep/<run>/`: `extraction.jsonl` (every pole extracted, dropped ones with their
> reason), `extract_responses.jsonl` (every call as sent and answered), `dedup_groups.json`, `candidates.jsonl`
> (what was submitted; replay with `gap_registry.py submit --from`), the gate's and probe's records, `readout.md`.

## The humanize rewrite (Roger, 2026-10-20)

Roger's marks on the label-fit survey ([readout.md](../../data/candidates/label_fit_survey/2026-10-17/readout.md))
found the sweep's rows framed for an AI, glosses narrower than their labels, and noun or gerund labels.  His
decisions: every sweep trait is rewritten in its closest human phrasing (person-general "one", "they", "one's"; no
"it", "its" or "itself" for the persona; no developer, lab, user, operator or training vocabulary); all 836 rows are
rewritten; the old sweep runs are retracted and the rewrites submitted as a new run, his reviewed rows kept.  The
explicit AI versions are a separate set ([alignment_ai_human_pairs.md](./alignment_ai_human_pairs.md)).

- The prompt: [alignment_humanize.md](./rubrics/alignment_humanize.md), pinned as version 4 (three worked examples), with a rendered sample
  per input variant.
- The code: [humanize.py](../../assistant_axis/gapgen/generators/alignment_sweep/humanize.py) (inputs, the call
  through the LLM-entropy runner, the parser, the candidates, the sheet, the submission plan) and the `humanize` and
  `humanize-submit` commands of [alignment_sweep.py](../../data_analysis/gap_generation/alignment_sweep.py).
- The tests: [test_gapgen_alignment_sweep_humanize.py](../../assistant_axis/tests/test_gapgen_alignment_sweep_humanize.py).

The inputs are every registry row with an `alignment_sweep` source, deduplicated on (label, gloss): 865 pairs on
836 rows on 2026-10-20, from the runs `2026-10-10-full`, `2026-10-11-papers`, `2026-10-11-b` and `2026-10-11-usage`.
The first live session freezes them in the run's [humanize_inputs.jsonl](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/humanize_inputs.jsonl) (the links to the run's files below use the example run id `2026-10-20-humanize`; none is there yet).  Estimate at Sonnet 5.5 rates (input
about 1,600 tokens a call, output allowed at 600): $0.09 for a 10-row pilot live, $8.0 for the full set live, $4.0
through the Message Batches API.

The sequence, in the main checkout (the registry log lives there; `<R>` is the new run, e.g. `2026-10-20-humanize`):

    uv run python data_analysis/gap_generation/alignment_sweep.py humanize --run-id <R> --render
    uv run python data_analysis/gap_generation/alignment_sweep.py humanize --run-id <R> --limit 10 --transport live --budget-usd 1
    uv run python data_analysis/gap_generation/alignment_sweep.py humanize --run-id <R> --resume --transport batches --budget-usd 8
    uv run python data_analysis/gap_generation/alignment_sweep.py humanize-submit --run-id <R> --dry-run
    uv run python data_analysis/gap_generation/alignment_sweep.py humanize-submit --run-id <R> --by '<who>'

Each `humanize` session writes the run's [rewrites.jsonl](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/rewrites.jsonl),
[candidates.jsonl](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/candidates.jsonl), [humanize_summary.json](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/humanize_summary.json) and
[humanize_sheet.md](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/humanize_sheet.md) (30 before/after rows for Roger's marks; the mark column second), beside
[responses.jsonl](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/responses.jsonl) and [usage.json](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/usage.json).  `humanize-submit` refuses
while an input has no answer (`--allow-unanswered` overrides), submits the new run first (the noun relabel on), then
retracts each old run with `registry.retract`, so that a reviewed row only the old runs held keeps a source.  On the
registry of 2026-10-20 none needs that: Roger's three reviewed rows with a sweep source (`concealing#1` and
`flattering#1` accepted, `overbearing#1` merged into [dominant](../../data/traits/instructions/dominant.json)) are all held by census and base-model sources whose
gloss comes first, so the retraction only removes their sweep sources (reported as settled rows touched, not
refused), and their reviews stand.  A settled row the retraction would drop has its old sources carried into the new
run unchanged, ahead of the rewrites.  A settled row whose first gloss the retraction would change (another source's
gloss coming first) cannot be kept that way: the dry run says the retraction will refuse on it, and the live step
refuses before writing anything until Roger decides (`--force-retract` with his go; the retraction record names the
rows it overrode).  None does today.  Each rewrite's `source_ref` ends `;humanize:<old run>:<original label>`: the
run named there is the old sweep run the source came from, and the new run is the candidate's own `run_id`.  The step
then writes [rejudge_keys.txt](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/rejudge_keys.txt) (the rows that
already had an M1 block and now show another gloss first, a rewrite or, once the sweep's gloss leaves, another
generator's: 122 in a fake full run on the registry of 2026-10-20, 11 of them the second kind) and its report,
[humanize_submit.json](../../data/candidates/runs/alignment_sweep/2026-10-20-humanize/humanize_submit.json), and prints the M1 and M3 commands through the Message Batches
transport: M1 `--run` on the new rows and `--keys` on the rejudge list, then M3 `--run` and `--keys-file --rescore`.
