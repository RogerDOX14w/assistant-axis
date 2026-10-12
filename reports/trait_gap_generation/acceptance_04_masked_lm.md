# Acceptance: workstream 4, the masked-LM generator (build, CPU smoke run, pilot B dry run)

Written 2026-10-12 by the Opus builder, against [coding_plan_04_masked_lm.md](./coding_plan_04_masked_lm.md) (the
specification) and [04_masked_lm_fill.md](./04_masked_lm_fill.md).  Terms: [glossary](./glossary.md#masked-lm)
(new entries: masked LM, frame, [pseudo-log-likelihood](./glossary.md#pseudo-log-likelihood),
[Variant B](./glossary.md#variant-b), [contrast score](./glossary.md#contrast-score),
[union rank](./glossary.md#union-rank)).  Nothing here spent money: the generator is a local model, and pilot B,
M1 and M3 are still to be launched.

## Built against plan section 5

Everything in the checklist up to pilot A's code and pilot B's dry run:
the package [masked_lm/](../../assistant_axis/gapgen/generators/masked_lm/__init__.py) with
[frames.py](../../assistant_axis/gapgen/generators/masked_lm/frames.py) (60 dispositional frames over six registers
and three slot types, ten subjects, five state and five physical contrast frames, 16 HHH probe frames in six
families, Roger's "He's habitually [MASK]" and the bare "[MASK][MASK]"),
[models.py](../../assistant_axis/gapgen/generators/masked_lm/models.py) (the three models pinned; loads only from
the in-tree cache, never `trust_remote_code`; MPS refused with the base-model generator's message when Metal sees
no device; the tokenizer census; the download record),
[singlemask.py](../../assistant_axis/gapgen/generators/masked_lm/singlemask.py),
[beam.py](../../assistant_axis/gapgen/generators/masked_lm/beam.py) (the subword and multiword passes),
[pll.py](../../assistant_axis/gapgen/generators/masked_lm/pll.py) (Variant B and `score_words`),
[wordlist.py](../../assistant_axis/gapgen/generators/masked_lm/wordlist.py),
[table.py](../../assistant_axis/gapgen/generators/masked_lm/table.py) (`load_mlm_table`),
[evaluate.py](../../assistant_axis/gapgen/generators/masked_lm/evaluate.py),
[submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py),
[report.py](../../assistant_axis/gapgen/generators/masked_lm/report.py); the CLI
[masked_lm_generator.py](../../data_analysis/gap_generation/masked_lm_generator.py) (`census`, `record-model`,
`generate`, `score`, `table`, `evaluate`, `submit`, `report`; a dry run on every command that writes); the frozen
interface (`load_mlm_table`, `MLM_TABLE_PATH`, `score_words`).  Also changed:
[setup_external.py](../../data_analysis/gap_generation/setup_external.py) (fetches the approved masked-LM models
only), [glossary.md](./glossary.md), [QUESTIONS.md](./QUESTIONS.md) (79 to 88).

**The download** (Roger's approval of 2026-10-11, roberta-large only): `FacebookAI/roberta-large` at revision
`722cf37b1afa9454edce342e7895e588b6ff1d59` (the pinned one), 7 files, 1,424,421,285 bytes, into the gitignored
`data/external/hf/`; `model.safetensors` 1,421,700,479 bytes, sha256
`047c85f0b96269cd62e6f732644f067004eebd95af5b5d35965ae2528f13bf38`, matching the Hub's published hash and the pin;
licence MIT (the card's `mit`).  Recorded in [sources_manifest.json](../../data/candidates/masked_lm/sources_manifest.json).
Nothing else was downloaded; the other two models' code paths are tested with fakes.

## Deviations, with reasons

1. **PLL is left to right by default** (QUESTIONS 86).  The plan's plain PLL scores sycophantic -0.01 in "He's
   habitually [MASK].", above rude (-3.68), so every split word would head the union.  The left-to-right form gives
   -14.57; `--pll-mode original` keeps the plan's arithmetic.
2. **Beam hits are rescored** by the PLL of the whole surface in the frame's single slot (the chain score is kept
   as `beam_score`).  A pattern's chain never pays for its literal text: "[MASK]-seeking" scored attention-seeking at
   -0.07, and multiword rows took 120 of the union's first 200.  After rescoring they take 21, and the union's
   recall of one-word corpus labels at 1,000 rose from 19.6% to 30.1% (with item 4's filter).
3. **The HHH probe frames are not in the union.**  On the real model their top 2,000 is mostly verbs ("used",
   "developed", "interacting"), 3,568 of the smoke run's rows.  They are reported in the readout and the probe page.
4. **The multiword pass drops phrases that open or close on a function word or an intensifier** ("a fighter",
   "very shy", "lied to us", "damn cute"), which the bare two-slot form returns in numbers.
5. **The wave's "subword and multiword rows never cut by rank"** (QUESTIONS 87) is infeasible as written.  Scaled
   from the smoke run, about 8,000 new rows qualify, roughly $68 batched and some 4,000 kept terms against the 300
   target.  So subword rows (dictionary words the tokenizer happens to split) join the single-word rank cut, and
   multiword rows stay uncut and gloss-gated.  A **review-load guard** refuses a wave projecting more than 1.5 times
   the kept target unless `--multi-cap N` bounds the uncut rows.  `--uncut-classes multiword,subword` restores the
   literal reading.  Stems already in the registry are left out of every run by default (pilot B included).
6. **The table is about ten times the plan's 1-3 MB** (QUESTIONS 80): the smoke table is 9,022 rows and 6.8 MB.
   Whether to track the full run's table (likely 15-20 MB) is open.
7. **Small additions**: the table gains `token_class` and `best_pass`; aggregates live in the already-gitignored
   `data/candidates/cache/masked_lm/agg/`, not a new `masked_lm/agg/` (which would have needed a `.gitignore` edit).
   The command-line subword K defaults to 100 and the multiword K to 50 (the beams "at reduced K", Roger 2026-10-10;
   the functions keep the plan's 300 and 100).  A word the tokenizer cannot represent scores -1000.
8. **The estimate's M1 pass rate is 0.88** (the plan's) with 0.95 as a high case; **the kept share is 0.5** (the
   census funnel), both until pilot B (QUESTIONS 88).
9. **The contrast check**: 14 of the hand-picked physical negatives (tall, short, muscular, young, athletic ...)
   are corpus traits on the physical track, so they were replaced; the 100 positives leave out the corpus's
   `identity_demographic` region.  The wordfreq baseline ranks Variant B's own universe by Zipf (OEWN adjectives
   and person nouns), not adjectives alone, so it compares like with like.
10. **OEWN 2024 hangs most person nouns** (leader, optimist, pacifist, sycophant) under "actor, doer, worker", not
    under "person"; the universe takes both closures (29,497 words) and drops proper names.
11. Environment: transformers is **5.1.0** here (the plan said 4.57.6; the lock holds both); recorded per run.

## Tests

```
uv run pytest assistant_axis/tests/test_gapgen_mlm_*.py data_analysis/tests/test_gap_generation_mlm_cli.py -q
88 passed, 5 skipped
GAPGEN_RUN_LOCAL=1 uv run pytest assistant_axis/tests/test_gapgen_mlm_smoke.py -q
3 passed            (the real roberta-large on CPU, 22 s)
uv run python data_analysis/check_arrangements.py --quiet          exit 0
uv run python tools/sync_entity_lists.py --check                   exit 0 (role_list 339, trait_list 932 up to date)
git status --porcelain data/traits data/roles data/seed_queue.json (empty)
```

The five skips are the smoke test (no `GAPGEN_RUN_LOCAL`) and the acceptance checks of outputs not written yet.
`uv run pytest -q` from the repository root stops on 50 collection errors with or without these files: the
`tests` packages of `.claude/worktrees/*` and `results_analysis` collide.  So the suite was run directory by
directory on 2026-10-12:

| directory | result |
|---|---|
| assistant_axis/tests | 3,047 passed, 15 skipped, 11 failed |
| data_analysis/tests | 732 passed, 2 failed |
| results_analysis/tests | 68 passed |
| pipeline/tests | 27 passed |
| tools/tests | 286 passed |

None of the 13 failures touches a file of this build.
- The rubric-hygiene tests (`test_gapgen_split_rubrics.py` four, `rubric_v2_round2`/`3`/`4` one each) find
  example words that are now queue words: "morose" was promoted into the
  [seed queue](../../data/seed_queue.json) in 5f127b7.
- The alignment-sweep and IPIP acceptance tests (two each) and end-to-end tests (one each) read those
  workstreams' in-flight records; the IPIP test still expects granularities {150, 350} after 3cfc3a5 added 600.
Every assertion in the tests was written to the plan's
section 8.  Five expectations I had computed wrongly were corrected, and two fake scorers redesigned (the test
was wrong, not the code: a rounding tolerance, a loader call count, a mean rank, a top-k count, an instance count;
ties at the fake's base logit, and a negative too close to the state frames).  The tests also caught two code bugs:
`encode_with_span` dropped the mask token as a special token, and one frame put an article before its slot.

## The tokenizer census and Variant B's coverage (roberta-large)

[census.json](../../data/candidates/masked_lm/census.json): of the corpus's 910 distinct bare labels, **355 (39.0%)
are one piece, 333 (36.6%) a split word, 222 (24.4%) multiword**.  The queue's 777 trait labels split 257 / 294 / 226.
The single-mask pass can reach at most 39% of the corpus's labels.  Variant B's universe lacks **264 of the 910:
86 of 688 one-word labels and 178 of 222 multiword ones** (MBTI types, star signs, Enneagram numbers, Hogwarts
houses, and most hyphenated coinages, such as attention-seeking and career-oriented, which the multiword beam in
fact produces).

## The CPU smoke run (tiny scale, not pilot A)

The pilot10 frames with three subjects (she, he, assistant); the probe frames with the assistant subject;
subword K 20; multiword K 10; Variant B on a spread of 1,500 of the 29,497 words; the contrast on the first 500
surfaced words plus the AUC set.  Generation took 3 min 26 s on CPU: Variant B 171 s at 259 forward passes a second,
multiword 25 s, subword 11 s, single 5 s.  Contrast scoring took 2 min 32 s.  The outputs are in the gitignored
cache: [readout.md](../../data/candidates/cache/masked_lm/smoke_cpu/readout.md),
[hhh_probe.md](../../data/candidates/cache/masked_lm/smoke_cpu/hhh_probe.md),
[recovery_curves.png](../../data/candidates/cache/masked_lm/smoke_cpu/recovery_curves.png) (checked by eye),
[evaluation.json](../../data/candidates/cache/masked_lm/smoke_cpu/evaluation.json) and the 6.8 MB
[mlm_table.jsonl](../../data/candidates/cache/masked_lm/smoke_cpu/mlm_table.jsonl).

- **Union** 9,022 rows; 8,906 eligible; 116 below the hard reject.
- **Recall of one-piece corpus labels** (355): 55% at 1k, 95% at 5k.  The wordfreq baseline gets 5% and 44% at
  the same cutoffs: the frames earn their keep where the plan asked.
- **Split and multiword labels**: 9% and 10% at 20k.  At this scale Variant B saw 5% of its universe, so this is not
  yet the Variant-B-against-beam comparison.  On the multiword labels the beam alone already recovers 20 of 222.
- **HHH probe**: the families `principles` (probe frames) and `reference_letter` (generation frames) put all three
  HHH words in a top 200.
  - Best ranks: [helpful](../../data/traits/instructions/helpful.json) 1, [honest](../../data/traits/instructions/honest.json) 1
    and [harmless](../../data/traits/instructions/harmless.json) 49 ("Above all else, AI systems should be [MASK].").
  - [transparent](../../data/traits/instructions/transparent.json) 1, [manipulative](../../data/traits/instructions/manipulative.json) 18,
    [truthful](../../data/traits/instructions/truthful.json) 27, [obedient](../../data/traits/instructions/obedient.json) 52,
    [deferential](../../data/traits/instructions/deferential.json) 313, [sycophantic](../../data/traits/instructions/sycophantic.json) 1,858.
  - Harmless is the hard word: its best rank anywhere is 49.
- **Contrast AUC 0.966** on 100 corpus traits against 100 states and physical words (target 0.85).

## What pilot A will measure, and the commands

Pilot A (plan section 10) measures words a minute on MPS, the top 50 of three frames, recall of the corpus's
one-word labels at 1k / 5k / 20k against the wordfreq baseline, and the HHH probe table.  The commands, in **Roger's
terminal** (MPS is the default device; inside the Claude Code sandbox `--device mps` is refused):

```
uv run python data_analysis/gap_generation/masked_lm_generator.py generate --passes single,probe --frames pilot10
uv run python data_analysis/gap_generation/masked_lm_generator.py score --top 3000
uv run python data_analysis/gap_generation/masked_lm_generator.py table
uv run python data_analysis/gap_generation/masked_lm_generator.py evaluate --title "pilot A (MPS)"
```

These write [readout.md](../../data/candidates/masked_lm/readout.md), [hhh_probe.md](../../data/candidates/masked_lm/hhh_probe.md)
and [recovery_curves.png](../../data/candidates/masked_lm/recovery_curves.png) (none of them written yet).  The
same four commands with `--device cpu` run in the sandbox in a few minutes: only the MPS rate needs his terminal.

The full local run (task 9) is `generate --passes single,probe,subword,multiword,variant_b`, then `score`, `table`
and `evaluate`.  Its dry run counts 742,763 forward passes, about 36 min at the CPU rate; MPS will be faster.

## What pilot B will cost

Pilot B runs on the table pilot A or the full run writes.  Its dry run, on the smoke table: 300 rows (205
single-word, 95 subword or multiword; 2,538 eligible stems already in the registry left out).  Live, **M1 $2.16
+ M3 $2.90 = $5.06**, with a high case of $5.29 at a 95% pass rate.  The $5 default cap refuses it, so:

```
uv run python data_analysis/gap_generation/masked_lm_generator.py submit --run-id <date>-pilot --top 300 --transport live --budget-usd 6
uv run python data_analysis/gap_generation/gap_registry.py submit --from data/candidates/runs/masked_lm/<date>-pilot/candidates.jsonl
uv run python data_analysis/gap_generation/traithood_filter.py --batch-id <date>-pilot_masked_lm --run masked_lm/<date>-pilot --pipeline split --transport live --budget-usd 6
uv run python data_analysis/gap_generation/novelty_score.py score --batch-id <date>-pilot_masked_lm --run masked_lm/<date>-pilot --transport live --budget-usd 7
uv run python data_analysis/gap_generation/masked_lm_generator.py report --run-id <date>-pilot
```

`report` prints the measured M1 pass rate and kept share.  The wave then becomes `submit --kept-target 300
--kept-share <measured> --transport batches`.  On the smoke table that dry run selects 786 rows (600 cut by rank,
186 multiword) for about $6.63 batched and 393 projected kept terms.  At full scale the guard will likely ask for
`--multi-cap`.

## Proposed paragraph for data/README.md (not edited; the platform owns the file; links to add when pasted)

> `data/candidates/masked_lm/`: the masked-LM generator (workstream 4).  `mlm_table.jsonl` holds one row per word a
> fill-mask model (roberta-large) surfaced in person-describing frames, with its union rank, trait-hood contrast
> score and OEWN gloss.  Also here: `evaluation.json`, `readout.md`, `hhh_probe.md` and `recovery_curves.png`
> (recovery against a wordfreq baseline, the HHH probe), `census.json` (labels by tokenization) and
> `sources_manifest.json` (the verified download).  Aggregates are a cache under `data/candidates/cache/masked_lm/`;
> the model is under the gitignored `data/external/hf/`.

## Not done

Pilot A on MPS, the full local run and its PNG check, pilot B and the wave (paid: the coordinator's), and the
downloads and census of bert-large-cased-whole-word-masking and ModernBERT-large (Roger's word first).  The recovery
harness run and `report` on a real wave follow pilot B.
