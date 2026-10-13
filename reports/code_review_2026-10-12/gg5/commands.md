# GG5: bringing the alignment sweep's core run into the main registry

Row GG5 of [regeneration_list.md](../regeneration_list.md).  The run
[alignment_sweep/2026-10-10-full](../../../data/candidates/runs/alignment_sweep/2026-10-10-full/) (Model Spec and
constitution; 386 candidates, [keys.txt](../../../data/candidates/runs/alignment_sweep/2026-10-10-full/keys.txt)) was
submitted, filtered ([filter batch](../../../data/candidates/filter/2026-10-10-full_alignment_sweep/)) and scored
([novelty batch](../../../data/candidates/novelty/2026-10-10-full_alignment_sweep/)) inside the `gen02-roget`
worktree, so its rows went into that worktree's git-ignored log, and its candidates' query vectors into that
worktree's git-ignored embedding cache.  335 keys are absent from the main log.  51 are there and lack only this
run's source; by main's `novelty.run_id` they are 22 `2026-10-10-tda_censuses_r3`, 18 keys that pre-date the sweep
in the worktree too (the M3 pilot's 10, `gen_pilot_censuses`'s 7 and one undecided: the sweep only merged a source
onto them, so none of the sweep's judging is lost there), 6 papers, 2 states-renamed, 2 base model and 1 Allport.

## Method: replay the worktree's lines, then the phase-B steps the rows missed

`gap_registry.py import-rows` (new, [gap_registry.py](../../../data_analysis/gap_generation/gap_registry.py),
`registry.import_rows` in [registry.py](../../../assistant_axis/gapgen/registry.py)) appends, for each absent key,
every line the worktree log holds for it, in that log's order, through the registry's write path (writer lock,
`rev` counted from 1, `created_at` kept, `updated_at` the import time); a key main already has gains only the
missing `sources[]` entry (`--only-run`), never a block, so no older worktree block can overwrite a newer one.  It
is idempotent, checks the fold after writing, and reads the worktree log without its lock (nothing is created
there).

Why not re-submit `candidates.jsonl` and re-run M1 and M3 on the recorded answers: `traithood_filter.py --resume`
reuses a batch directory and would rewrite the recorded batch's `results.jsonl`, `run.json` and `summary.json`;
and today's M1 routes phrases differently (gate 5), so the 77 phrase rows would send new calls anyway.  The
replay reproduces exactly what was paid for on 2026-10-10/11; the phase-B steps below then bring the rows to
where the rest of the registry is.

`novelty_score.py cache-merge` (new, [novelty_score.py](../../../data_analysis/gap_generation/novelty_score.py),
`embed.merge_cache` in [embed.py](../../../assistant_axis/gapgen/embed.py)) copies the worktree cache's vectors
that main's cache lacks: `score --redecide` replays retrieval from cached vectors only, and main's cache holds
2 of the 253 query texts the re-decide needs (dry run below).  A vector main already has is never replaced.

Tests: [test_gapgen_registry_import.py](../../../assistant_axis/tests/test_gapgen_registry_import.py).

## Dry run on a copy of main's registry (2026-10-13, main at sha256 `2a6e801e…`, 9,972 lines, 9,949 keys)

- Import: 335 keys replayed with 923 lines (82 keys with 2 lines: submit and M1; 253 with 3: submit, M1, M3);
  51 keys gained one source each (`alignment_sweep/2026-10-10-full`); 974 lines appended; 10,284 keys after.
- Key-by-key, against the fold before (a check independent of the import code): the 9,898 other keys
  byte-identical; the 335 equal to the worktree's fold in every field but `updated_at` (`rev` and `created_at`
  equal too); the 51 changed in `sources` (exactly the run's entry appended), `rev` (+1) and `updated_at` only.
- The replayed blocks: M1 254 trait, 78 reject, 3 tagged (2 states, 1 physical); M3 206 new, 47 covered (rule
  set 2), 82 without a decision (the 81 non-traits and `respects_user_autonomy`, whose M1 gloss call failed).
- A second import appends nothing.  `compact` on a copy of the result: backup byte-identical to the log, the
  gzipped snapshot's fold equal to the log's (23.1 MB, 10,284 keys).

## Commands for the main checkout, in order

Run from the main checkout after this branch is merged (the paid CLIs refuse while the platform's paths are
dirty).  Nothing else should be writing the registry or the embedding cache meanwhile (a live M3 or review run
rewrites the cache's npz; `save()` merges such writes safely, but step 1's backup would then predate them).  Step 1
must succeed before steps 2 and 3: its copies are the only backups the import and the merge have, hence `set -e`.

```bash
set -e
cd /Users/roger/Documents/GitHub/assistant-axis
WT=.claude/worktrees/gen02-roget
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
K=reports/code_review_2026-10-12/gg5

# 1. Backups ($0): main's log, the worktree's log, main's OpenAI embedding cache
cp -p data/candidates/registry.jsonl data/candidates/registry.jsonl.bak.${STAMP}_before_gg5
cp -p $WT/data/candidates/registry.jsonl data/candidates/registry.jsonl.bak.${STAMP}_gen02_roget
cp -p data/candidates/cache/embeddings/openai_text-embedding-3-large.npz \
      data/candidates/cache/embeddings/openai_text-embedding-3-large.npz.bak.${STAMP}
cp -p data/candidates/cache/embeddings/manifest.json data/candidates/cache/embeddings/manifest.json.bak.${STAMP}

# 2. Import ($0) from step 1's copy of the worktree log (idle; kept beside the registry; the record's sha256 names
#    it).  Expect, from the dry run on a copy of main: 335 new keys replayed with 923 lines ({"2": 82, "3": 253}),
#    51 existing keys gaining 51 sources, 0 unchanged, 974 lines; source sha256 ea1a7aeb69190075...
SRC=data/candidates/registry.jsonl.bak.${STAMP}_gen02_roget
uv run python data_analysis/gap_generation/gap_registry.py import-rows --from $SRC \
    --keys-file data/candidates/runs/alignment_sweep/2026-10-10-full/keys.txt \
    --only-run alignment_sweep/2026-10-10-full --dry-run
uv run python data_analysis/gap_generation/gap_registry.py import-rows --from $SRC \
    --keys-file data/candidates/runs/alignment_sweep/2026-10-10-full/keys.txt \
    --only-run alignment_sweep/2026-10-10-full \
    --record data/candidates/runs/alignment_sweep/2026-10-10-full/registry_import_gg5.json
#    Recovery rule: compare the real run's counts with the dry run's (they differ only if one of the 386 keys reached
#    main in between; the import handles that, but read why).  If the run does not end with "verified" (exit 1, or
#    no exit at all: a kill, a full disk), restore the log and run step 2 again from scratch:
#        cp -p data/candidates/registry.jsonl.bak.${STAMP}_before_gg5 data/candidates/registry.jsonl
#    Never rerun on top of a partial import: a rerun treats a partly replayed key as present and only adds its
#    source, leaving a history cut short.  (The record is written on a mismatch too; move it aside before rerunning.)
#    The import does not check main's log for malformed lines (only the source's); main has none today, and
#    step 10's compact would refuse them.

# 3. Cache merge ($0): the run's query vectors from the worktree's cache.  Expect (the reviewer's dry run against
#    main's cache, 2026-10-13): 4,383 in the worktree, 29,996 in main; would add 954; 358 the same; 3,071 differ
#    (kept main's; largest component difference 1.44e-2).  The differing pairs are OpenAI's run-to-run noise on
#    texts both checkouts embedded (cosine median 0.999999, minimum 0.9972); no vector is ever replaced.  It loads
#    main's 376 MB table two or three times (about 1 GB peak, tens of seconds).
uv run python data_analysis/gap_generation/novelty_score.py cache-merge \
    --from $WT/data/candidates/cache/embeddings --tag openai_text-embedding-3-large \
    --check-batch 2026-10-10-full_alignment_sweep --dry-run
uv run python data_analysis/gap_generation/novelty_score.py cache-merge \
    --from $WT/data/candidates/cache/embeddings --tag openai_text-embedding-3-large

# 4. M3 under rule set 3 (G7 for this batch), the 253 rows that hold this batch's block, replayed against the
#    vectors the worktree run read.  Against main's cache the dry run gives "3 of 253 rows identical [MISMATCH]"
#    and 4 relation calls not on record (main, 2026-10-13): the worktree run embedded 69 of the 932 corpus texts
#    itself (its run.json: n_corpus_missing 69), main's own vectors for the same texts differ by OpenAI's
#    run-to-run noise, and the index is centred on the corpus mean, so every listed cosine moves (by up to 0.007)
#    and the check compares cosines exactly.  The corpus texts are the same (all 637 descriptions the run showed
#    are 9d49ad6's), and every decision, covering trait, reason and review flag of the 249 replayable rows
#    reproduces; 6 rows' shortlists and 4 walks differ.  So: a replay cache, a copy of main's cache that takes the
#    worktree's vectors where they differ (main's live cache is never changed; --prefer-source refuses it).
mkdir -p data/candidates/cache/gg5_replay_embeddings      # git-ignored; about 390 MB; delete after step 4
cp -p data/candidates/cache/embeddings/openai_text-embedding-3-large.npz data/candidates/cache/embeddings/manifest.json \
      data/candidates/cache/gg5_replay_embeddings/
uv run python data_analysis/gap_generation/novelty_score.py cache-merge \
    --from $WT/data/candidates/cache/embeddings --cache-dir data/candidates/cache/gg5_replay_embeddings \
    --tag openai_text-embedding-3-large --prefer-source [--dry-run]
#    expect: 0 added (step 3 added them), about 3,071 differ, all taken from --from
uv run python data_analysis/gap_generation/novelty_score.py score --redecide \
    --from-batch 2026-10-10-full_alignment_sweep --batch-id 2026-10-10-full_alignment_sweep_r3 \
    --keys $(cat $K/redecide_keys.txt) --rules 3 --transport live --budget-usd 1 --write-registry \
    --cache-dir data/candidates/cache/gg5_replay_embeddings --dry-run
#    $0 only if: "reproduction: ... 253 of 253 rows identical [OK]" and "calls not on record ... 0"; then without
#    --dry-run.  Expected offline (from main's cache, the same records): of 249 rows, 14 new -> covered by the
#    graded cut-off, 188 stay new, 47 stay covered.  If the replay cache does not reproduce, stop and report: the choices are
#    (a) step 4 against main's cache as is (4 relation calls, about $0.004 plus their walks, cents; decisions on
#    main's vectors, the mismatch recorded in run.json), or (b) the fresh rule-set-3 M3 below, about $2.24.
#    Both are paid and need Roger's go; (a) is the cheaper and was enough to reproduce every decision.
# 4-fallback (b) (PAID, Roger's go; instead of step 4, not after it):
#   uv run python data_analysis/gap_generation/novelty_score.py score --batch-id 2026-10-13-full_alignment_sweep_r3_fresh \
#       --keys $(cat $K/redecide_keys.txt) --rescore --rules 3 --transport live --budget-usd 3 [--dry-run]

# 5. M1 on the 77 phrase rows gate 5 changes (G1 for this run: 41 cut unread by the definition probe, 36 turned
#    away by the frames) and respects_user_autonomy (gloss call failed)
uv run python data_analysis/gap_generation/traithood_filter.py --batch-id 2026-10-13-m1_phrase_gg5 \
    --keys $(cat $K/m1_keys.txt) --transport live --budget-usd 3 --dry-run
#    then without --dry-run

# 6. M3 on those that became traits (keys that are not traits are skipped)
uv run python data_analysis/gap_generation/novelty_score.py score --batch-id 2026-10-13-m1_phrase_gg5 \
    --keys $(cat $K/m1_keys.txt) --transport live --budget-usd 3 --dry-run
#    then without --dry-run

# 7. The states pass (G9) on the states list's unjudged rows: the run's 2 and 15 others (see "Decisions" below)
uv run python data_analysis/gap_generation/states_pass.py --batch-id states_gg5_1 --mode queue --holding-states \
    --readings 3 --transport live --budget-usd 1 --dry-run
#    then without --dry-run; then, as G9: M3 on released rows (score --holding states --unscored), M1 and M3 on
#    the suggested names (data/candidates/runs/states_pass/states_gg5_1/candidates.jsonl)

# 8. The physical pass (G9) on the run's physical row
uv run python data_analysis/gap_generation/novelty_score.py score --batch-id physical_gg5_1 --holding physical \
    --keys 'padded#1' --transport live --budget-usd 1 --dry-run
#    then without --dry-run

# 9. Review (G11): resume review_traits_all_2 with the new M3 batches (needs Roger's go: see below).
#    2026-10-13-g600_ipip_renamed is not GG5's and not in review_traits_all_2's 28 batches: it rides along (its 5
#    kept rows, M3-scored after G11; $0.45 by batches of the estimate).  Drop it to keep the step to GG5 alone.
uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_traits_all_2 \
    --from-batches $(python3 -c "import json; print(' '.join(json.load(open('data/candidates/review/review_traits_all_2/run.json'))['from_batches']))") \
    2026-10-10-full_alignment_sweep_r3 2026-10-13-m1_phrase_gg5 2026-10-13-g600_ipip_renamed \
    --transport batches --budget-usd 60 --resume --dry-run

# 10. Compact and commit the snapshot (GG3's procedure), the import record and the new batch directories
uv run python data_analysis/gap_generation/gap_registry.py compact
```

## Costs

| step | estimate | basis |
|---|---|---|
| 1-3 backups, import, cache merge | $0 | no call |
| 4 M3 re-decide, 253 rows | $0 with the replay cache if its dry run shows 253 of 253 identical and 0 calls not on record | Against main's cache: 3 of 253 identical, 4 calls not on record (corpus-vector noise, see step 4).  Otherwise, with Roger's go: (a) step 4 against main's cache, cents; (b) the fresh rule-set-3 M3 on the 253, $2.24 by `novelty_score.py estimate`, `--budget-usd 3` |
| 5 M1, 78 rows | $0.77 | dry run on the copy: $0.765 ($0.0098 a word); G1's actual was 1.03 times its estimate |
| 6 M3 on the new traits | about $0.64 | `estimate --n-candidates 72` (G1: 117 traits of 126 rows; actual $0.0081 a row) |
| 7 states pass | $0.03 | dry run on the copy (17 rows); follow-ups cents |
| 8 physical pass, 1 row | $0.007 | dry run on the copy (all 76 unscored physical rows: $0.68) |
| 9 review graph | about $5-13 by batches | dry run not possible before step 3 (the new candidates' vectors are in the worktree cache).  The papers batch's 235 candidates cost $4.24 of G11's $37.28 (from its records), $0.018 a candidate; the resume estimate for the 2 cached GG5 candidates was $0.10 (24 relation calls, 130 pairs), for the 5 renamed IPIP rows $0.45.  About 265 new candidates (206 new under rule set 2, about 60 from step 6) |

Steps 4-8: about $1.5 live.  With step 9: about $7-15.

## Decisions for Roger

1. **Review**: resuming `review_traits_all_2` adds the new candidates to the graph he has not started on (no
   `decisions.jsonl` yet) and sends only the calls not on record, but the resume's cap counts G11's $37.28, so
   the gate wants `--confirm-expensive --confirmed-by` for a new spend of about $5-13 by batches.  The other
   way, waiting for the next all-batches build, leaves the 265 out of review until then.  A separate build
   reruns every relation call (the list order is seeded by the build id).
2. **States pass scope**: `--holding-states` takes every unjudged states row, here 17: the run's 2, 12 names the
   states pass itself suggested (11 in G9's `states_unjudged_r3`, 1 in both it and `states_tda_1`) that M1 then
   tagged as states again, and 3 IPIP g600 rows.  A second reading of a suggested name can suggest another name.
   The CLI has no `--keys`.
3. **Step 4's fallback**: if the re-decide against the replay cache does not reproduce 253 of 253 with 0 calls
   not on record, either run it against main's cache (4 relation calls, cents; every decision reproduced there,
   only cosines and 6 shortlists move) or the fresh rule-set-3 M3 on the 253 (about $2.24 live, `--budget-usd
   3`).  Both are paid and wait for his go.
4. **Physical scope**: the run's 1 row, or all 76 unscored physical rows (75 from the census rare stages, the
   base model at count 2, the G9 states names and IPIP g600, which arrived after G9's physical pass), $0.68.

## Files

- Key lists: [redecide_keys.txt](./redecide_keys.txt) (253: the replayed rows holding this batch's M3 block; the
  33 other rows of the batch are main rows decided by later runs, and re-deciding them would send calls whose
  answers `promote-redecide` would not write), [m1_keys.txt](./m1_keys.txt) (78).
- The import record will be at
  [registry_import_gg5.json](../../../data/candidates/runs/alignment_sweep/2026-10-10-full/registry_import_gg5.json)
  (not there yet: step 2 writes it).
