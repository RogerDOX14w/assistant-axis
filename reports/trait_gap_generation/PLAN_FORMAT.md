# Coding-plan format for greenlit workstreams (agreed 2026-09-18, models 2026-09-23)

A coding plan is written by a Fable agent from the workstream plan and its resolution
section, reviewed by Roger (comments go into the plan file), then executed by an Opus agent
in a git worktree. The plan must let Opus work without re-litigating decisions.

Required sections, in this order:

1. **Decisions already made**, each with its reason and the plan section it came from
   (the workstream plan's "Resolution" section and Roger's comments are authoritative).
2. **Out of scope**, explicit.
3. **Rule files to Read first** (Claude Code loads a rule only when a matching file is opened
   with the Read tool): `.claude/rules/provenance.md` (usage.json is a hard rule on every
   batched LLM call site: `MultiModelUsage` from `assistant_axis/judge_pricing.py`),
   `.claude/rules/entity-naming.md` (file-form stems via `normalize_to_file_name`, US
   English), `.claude/rules/trait-pairs.md` (what a trait, a pair and the seed queue are),
   `CLAUDE.md` (file-access boundary, the $20 confirmation rule, tests are mandatory,
   hotlink files in replies).
4. **Existing code to reuse**, by path: `data_analysis/seed_entities.py` (queue lifecycle,
   `write`/`generate`/`check`/`pair`), `assistant_axis/entity_id.py`, `assistant_axis/atomic_io.py`,
   `assistant_axis/arrangements.py`, `assistant_axis/judge_pricing.py`, `assistant_axis/judge.py`
   (`call_judge_single_unified`, `warn_if_low_parse_rate`), `data/seed_queue.json` format.
5. **File layout** (new package `assistant_axis/gapgen/`, CLI scripts in
   `data_analysis/gap_generation/`, external data under gitignored `data/external/`, outputs
   under `data/candidates/`), with every module and its public functions and signatures.
6. **Data schemas** with one example record each (registry row, config file, report rows).
7. **CLI**: each command, its flags, its dry-run behaviour, its cost estimate and guard.
8. **Acceptance tests, written first**: unit tests per module, the recovery / calibration
   test the workstream plan specifies, a cost guard test, and the exact commands that must
   pass (`uv run pytest ...`, `check_arrangements.py`, `sync_entity_lists.py --check`).
9. **Ordered task checklist** for Opus, each task small enough to finish and test in one
   sitting, with the test that proves it.
10. **Pilot**: the 20% (or smaller) run with its yield-per-dollar and cost readout, and the
    decision Roger makes on it before the full run.
11. **Report at the end**: the one-page acceptance report (built, deviations from plan, test
    results, cost from usage.json, pilot numbers).
12. **Escalation**: Opus retries once, then Fable, then Roger via `QUESTIONS.md` (proceed under a
    stated assumption unless the answer would make the work useless).

Length: one to two thousand words plus schemas. Interfaces the plan freezes for later
workstreams go in a clearly marked "Frozen interface" section.

## File-access boundary (restated 2026-09-23 after a breach)

Agents may read only under `/Users/roger/Documents/GitHub/assistant-axis` and their own
scratchpad, and write only the files their task names.  Nothing under the home directory
outside that tree may be listed, read or stat'ed, including `~/.cache` (Hugging Face, pip,
uv), even to check whether a model or dataset is already downloaded: state the need and
its size in the report and let Roger answer.  Five planning agents listed caches or tool directories under the home directory
(`~/.cache/huggingface/hub`, `~/nltk_data`, `~/.ollama`) on 2026-09-17; Roger considers
that a privacy breach.  The boundary is this repository alone, not `~/Documents/GitHub/`.  Coding
plans must carry this paragraph into every Opus task prompt, and any download goes to
`data/external/` inside the repo.
