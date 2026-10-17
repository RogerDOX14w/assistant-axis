# Acceptance: workstream 5, the corpus-frames generator (build stage)

Written 2026-10-17 by the build agent (Opus 5.5) on branch `gen05-corpus-frames`, from
[coding_plan_05_corpus_frames.md](./coding_plan_05_corpus_frames.md) with Roger's three decisions (both Books tiers
streamed; the text corpora in this build; the platform's noun helper).  **This is the build half of the plan's
§ 11 report**: the code, the tests and the commands for the live steps.  Nothing has been downloaded or streamed and no
paid call has been made; the sections marked *after the live runs* are filled when the stream, the pilot and the
first wave have run.  Terms: the [glossary](./glossary.md), section "Corpus-frames terms" (a
[frame](./glossary.md#lexical-frame) and its fillers, [shards and head-peeking](./glossary.md#shard),
[document frequency](./glossary.md#document-frequency), [lift](./glossary.md#lift),
[reciprocal-rank fusion](./glossary.md#rrf), [yield](./glossary.md#frame-yield),
[net filter](./glossary.md#net-filter), [unique contribution](./glossary.md#unique-contribution),
[net-new row](./glossary.md#net-new)).

## What was built (plan § 5)

| file | what |
|---|---|
| [`__init__.py`](../../assistant_axis/gapgen/generators/corpus_frames/__init__.py) | generator id `corpus_frames`, the paths, the frozen interface (`load_frames_table`, `TABLE_PATH`, `person_frequency`) |
| [`frames.py`](../../assistant_axis/gapgen/generators/corpus_frames/frames.py) | the Books bank of § 6: 45 frames (27 in tier 1, 18 in tier 2) over six types, the 22 person nouns, `regex_for`, `bank_sha256` |
| [`books.py`](../../assistant_axis/gapgen/generators/corpus_frames/books.py) | head-peeking, `locate`, `shard_plan`, `stream_shard`, `run_stream` (the approval gate, resume, the manifest), the extracts |
| [`text.py`](../../assistant_axis/gapgen/generators/corpus_frames/text.py) | decision 2: PIPPA's `bot_description` and the character cards, ten regex frames per source (trait lists, copular lists, the attributive, possessive, tendency and habitual frames, and the filler-first "X to a fault", "X by nature", "X at heart"), the download with its approval gate and manifest |
| [`relabel.py`](../../assistant_axis/gapgen/generators/corpus_frames/relabel.py) | decision 3: a thin adapter over the platform's [nouns.py](../../assistant_axis/gapgen/nouns.py) (US spelling, then the helper); no rules of its own |
| [`table.py`](../../assistant_axis/gapgen/generators/corpus_frames/table.py) | the table of § 6: the fold, the floor, both within-frame orderings, RRF, eligibility through `zipf_info`, the tags, `frame_stats`, `person_frequency` |
| [`evaluate.py`](../../assistant_axis/gapgen/generators/corpus_frames/evaluate.py) | recovery under both orderings beside two frequency baselines, the ordering choice, the unfound labels by region, the registry overlap; after the pilot the frame and type measures and the keep rule; the curves PNG |
| [`submit.py`](../../assistant_axis/gapgen/generators/corpus_frames/submit.py) | the pilot's top 25 per frame, the review-hour wave over the frames kept, the estimate and its gates, the submission, the follow-ups |
| [`report.py`](../../assistant_axis/gapgen/generators/corpus_frames/report.py) | the free readout and a run's `report.md` (§ 10 order), `roger_sample.md`, `roger_first_hour.md` |
| [`corpus_frames_generator.py`](../../data_analysis/gap_generation/corpus_frames_generator.py) | the CLI: `locate`, `stream`, `fetch-text`, `extract-text`, `table`, `evaluate`, `submit`, `report` |
| tests | [frames](../../assistant_axis/tests/test_gapgen_corpus_frames_frames.py), [books](../../assistant_axis/tests/test_gapgen_corpus_frames_books.py), [text](../../assistant_axis/tests/test_gapgen_corpus_frames_text.py), [relabel](../../assistant_axis/tests/test_gapgen_corpus_frames_relabel.py), [table](../../assistant_axis/tests/test_gapgen_corpus_frames_table.py), [evaluate](../../assistant_axis/tests/test_gapgen_corpus_frames_evaluate.py), [submit](../../assistant_axis/tests/test_gapgen_corpus_frames_submit.py), [acceptance](../../assistant_axis/tests/test_gapgen_corpus_frames_acceptance.py), [CLI](../../data_analysis/tests/test_gap_generation_corpus_frames_cli.py); fakes in [corpus_frames_fakes.py](../../assistant_axis/tests/corpus_frames_fakes.py) |

The table [frames_table.jsonl](../../data/candidates/corpus_frames/frames_table.jsonl) (not there yet) is git-ignored
([.gitignore](../../.gitignore)); its sha256 goes into [evaluation.json](../../data/candidates/corpus_frames/evaluation.json)
and every run's `run.json` under [runs/corpus_frames/](../../data/candidates/runs/corpus_frames/) (not there yet).

## Deviations from the plan, with reasons

Each is recorded in [QUESTIONS.md](./QUESTIONS.md) (entries 166-179, `[05]`), with the plan's pre-registered entries
updated for Roger's decisions:

1. **`--tier` defaults to `all`** (decision 1 (b)); the plan's CLI said `--tier 1` (entry 166).
2. **The text corpora are built** (decision 2), with their own regex frames and a floor of 3 occurrences rather than
   the Books 40 (entries 167, 171).
3. **No local relabel**: the table folds each filler through the platform's helper so the frames fuse across types
   ("known for his honesty" and "a very honest man" are one row, `honest`), and a row submits the noun when no
   adjective filler was found; the platform adds the adjective (entries 168, 174).  The plan's § 6 had the table
   submit the adjective; the noun plan replaced that.
4. **The wave counts a noun's sibling** as a net-new row in the cut and the estimate; the plan's literal cut is
   `--no-count-siblings`, under which the review-load guard (1.5 x the target) can refuse (entry 173).
5. **The pilot's selection** is a fixed top 25 per frame, registered rows included and charged nothing (entry 172).
6. **The Books extracts keep decade sums** instead of every year, to keep them at "tens of MB"; the 1920 cutoff stays
   exact (entry 175).
7. **The review rate** is plan 13's measured `pooled_review_rate` (it exists now), the plan's 146 an hour only as the
   fallback (entry 170).
8. **Two baselines** beside each other: OEWN's adjectives and person nouns by Zipf (plan 04's) and the table's own
   words by Zipf (what the frames' ordering adds over frequency alone).
9. **The acceptance test's git check counts tracked files only** (entry 179).

## Commands of § 8, at the build

| command | result |
|---|---|
| `uv run pytest assistant_axis/tests/test_gapgen_corpus_frames_*.py data_analysis/tests/test_gap_generation_corpus_frames_cli.py -q` | 114 passed, 7 skipped (the acceptance tests on outputs not recorded yet) |
| `uv run pytest -q` | 6,136 passed, 85 skipped, 12 failed, 27 collection errors; before the build, on the same worktree, 6,022 passed, 78 skipped and the **same** 12 failures and 27 errors (OEWN absent from the worktree's `data/external`, its recorded-output acceptance tests, the boundary hook's tests run from `/tmp`, and the `results_analysis` modules that collect only alone): no new failure |
| `uv run python data_analysis/check_arrangements.py --quiet` | exit 0 |
| `uv run python tools/sync_entity_lists.py --check` | exit 0 (932 traits, 339 roles up to date) |
| `git status --porcelain data/traits data/roles data/seed_queue.json` | empty |

## The live steps (run from the main checkout, after the merge)

Every step is $0 except the platform's M1 and M3; every download needs the approval named on the command line.

1. `uv run python data_analysis/gap_generation/corpus_frames_generator.py locate` (both tiers): about 44 prefixes x
   15 head-peeks of 4 KB (about 2.6 MB) and one HEAD request per shard; writes
   [shard_plan.json](../../data/candidates/corpus_frames/shard_plan.json) (not there yet) and prints the shard
   count and GB (the plan's estimate: about 50 shards, about 27 GB).
2. `... stream --approved-by '<Roger, date: open decision 1 (b)>' --parallel 4` (`--resume` after a break): the
   stream, nothing stored but the extracts under [data/external/books_ngrams/](../../data/external/books_ngrams/)
   (git-ignored, not there yet; tens of MB) and the
   [sources manifest](../../data/candidates/corpus_frames/sources_manifest.json) (not there yet).
3. `... fetch-text --approved-by '<Roger, date: open decision 2>'` (about 260 MB into
   [data/external/corpus_frames/](../../data/external/corpus_frames/), git-ignored, not there yet),
   then `... extract-text` (add `--delete-raw` to remove the downloads afterwards).
4. `... table`, then `... evaluate --title 'first build'`: [frame_stats.json](../../data/candidates/corpus_frames/frame_stats.json),
   [evaluation.json](../../data/candidates/corpus_frames/evaluation.json),
   [recovery_curves.png](../../data/candidates/corpus_frames/recovery_curves.png) and
   [readout.md](../../data/candidates/corpus_frames/readout.md) (none there yet).
5. The pilot: `... submit --run-id <date>-pilot --top-per-frame 25 --dry-run`, then without `--dry-run` once the
   estimate is read (the default cap is $8; 65 frames may make it more than the plan's tier-1 $3-5), then M1 and M3
   with the commands `submit` prints, then `... evaluate --pilot-run <date>-pilot` and
   `... report --run-id <date>-pilot`.  Roger decides the frame thresholds, the frames kept and the wave's transport.
6. The first wave: `... submit --run-id <date>-w1 --kept-target 300 --kept-share <the pilot's net-new kept share>`,
   M1 and M3, `... report --run-id <date>-w1`.

## After the live runs

*To be filled*: the shard plan as approved (shards, GB, bytes streamed, lines kept, the approval line); the union
recovery under both orderings beside the baselines and the ordering chosen; the per-frame recovery; the corpus
labels no frame finds, by region; the pilot readout in the § 10 order with Roger's decisions; the first wave's
counts, M1 and M3 fractions, the novel figure raw and net, the contributing frame of every new label; the 50-row
sample's verdicts and the first-hour list; cost per model from every `usage.json`; the registry overlap at depth 500 /
2,000 / 5,000 against the proxy's 80 / 63 / 41%; the next steps.

## Proposed paragraph for data/README.md (the platform owns that file; not edited)

Ready to paste; its links are relative to [data/README.md](../../data/README.md), where it would live.

```markdown
[`candidates/corpus_frames/`](./candidates/corpus_frames/): the corpus-frames generator (workstream 5, plan
[coding_plan_05_corpus_frames.md](../reports/trait_gap_generation/coding_plan_05_corpus_frames.md)).  Tracked:
[shard_plan.json](./candidates/corpus_frames/shard_plan.json) (the Books shards each frame needs, from
head-peeking), [frame_stats.json](./candidates/corpus_frames/frame_stats.json) (per frame: fillers, forms, shares,
recall, and after the pilot its yield, net filter and keep verdict),
[evaluation.json](./candidates/corpus_frames/evaluation.json) (recovery under both orderings, the ordering chosen, the
unfound labels, the frame measures and the frames kept; the table's sha256),
[recovery_curves.png](./candidates/corpus_frames/recovery_curves.png), [readout.md](./candidates/corpus_frames/readout.md)
and [sources_manifest.json](./candidates/corpus_frames/sources_manifest.json) (both download manifests).  Git-ignored:
[frames_table.jsonl](./candidates/corpus_frames/frames_table.jsonl) (one row per stem, rebuilt by `table`).
[`external/books_ngrams/`](./external/books_ngrams/): the Books extracts (`<frame_id>.tsv`, the matching lines in
decade sums), their per-shard parts and `DOWNLOAD_MANIFEST.json`; [`external/corpus_frames/`](./external/corpus_frames/):
the text corpora's downloads (deletable after `extract-text`), their extracts and manifest.  Runs under
[`candidates/runs/corpus_frames/`](./candidates/runs/corpus_frames/).
```
