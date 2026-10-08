# Brief: refusal handling in the instruction generators (2026-10-08)

## Why

Chunk 5 of the corpus expansion seeds traits that the generator model may
decline to write persona instructions for (ageist, sexist, xenophobic,
self_harming, suicidal, kinky, among others).  Roger's ruling (2026-09-08,
reaffirmed 2026-10-08): attempt them, and a refusal is an informative data
point to record, not an error to retry.  Today a refusal is invisible: the
reply fails to parse as JSON, `data_analysis/regenerate_trait_instructions.py`
retries five times with backoff (`generate_combined` / `_generate_combined_once`
and the older `generate_instructions` / `generate_questions` paths), then
raises RuntimeError, and the trait is counted as an error with nothing
recorded anywhere.  The role generator (`regenerate_role_instructions.py`) has
the same shape.  The audit tool already does the right thing for its judge
calls: see `JudgeRefusal` and `_refusal()` in
`data_analysis/audit_trait_instructions.py`, which detect `stop_reason ==
"refusal"` and raise once instead of retrying.

## What to build

1. **Detection**, in both generators, at the point where a reply is read:
   - the Anthropic API's `stop_reason == "refusal"` (the SDK's documented
     refusal stop reason; check the current Messages API documentation or the
     `claude-api` skill rather than memory, and handle an empty `content`
     list), and
   - a text reply that is not JSON and reads as a decline (a short, bounded
     pattern on the first sentence: "I can't", "I cannot", "I won't", "I'm not
     able to", "I am not able to", "I don't feel comfortable", "I'm not
     comfortable", "I will not"; keep the list in one named constant with a
     comment, and do not match a JSON reply that merely contains such words).
   Either raises `GenerationRefusal(RuntimeError)` carrying the label, the
   stop reason and the first 300 characters of the reply text.  **No retry**
   on a refusal: the retry loops let `GenerationRefusal` propagate at once.
   The batch path (`collect_batch` in the trait generator) classifies a batch
   reply the same way, and a refused batch reply is NOT sent to the real-time
   pass; it is recorded as refused like a live one.
2. **Recording.**  Each generator appends one JSON object per refusal to an
   append-only side-car beside `instructions/`, where nothing that globs the
   corpus can read it: `data/traits/generation_refusals.jsonl` and
   `data/roles/generation_refusals.jsonl` (same placement rule as the usage
   records; see AGENT_NOTES "Token usage logging").  Fields: `stem`, `label`,
   `kind` ("trait" / "role"), `model`, `style`, `template_sha256`,
   `refused_at` (ISO date-time), `stop_reason`, `reply_excerpt`, `attempt`
   ("live" / "batch").  Use the project's atomic/append helpers if there is
   one for JSONL (look at how `antonym_check_history.jsonl` is appended in
   `seed_entities.py`: `append_check_history`), otherwise a plain append with
   a newline per record.  The corpus file is left untouched (the seed stays a
   seed without instructions).
3. **Run summary.**  The per-trait loop catches `GenerationRefusal`, counts
   `refused` separately from errors, prints `REFUSED <label>: <excerpt>` and
   continues; the end-of-run line reports processed / skipped / refused /
   errors.  Usage is still charged for the refused call (the response was
   received).
4. **The seeding tool.**  `data_analysis/seed_entities.py generate` runs the
   generators through `run_tool`.  After a run it reads the side-car records
   with `refused_at` later than the run's start time for the stems it
   generated, sets those entries' `status` to `refused` with a `refusal` field
   (the record), and leaves them out of `check`.  `status` and `report` list
   `refused` as a final state (add it wherever the lifecycle is enumerated in
   that file).  A `refused` entry is not re-attempted by `generate` unless
   `--retry-refused` is passed.
5. **Tests**, with fake API responses only (no real calls): in
   `data_analysis/tests/test_regenerate_trait_instructions.py` and
   `test_regenerate_role_instructions.py`: a stop-reason refusal and a prose
   decline each raise `GenerationRefusal` without retrying (assert the call
   count is 1), write one side-car record, and a JSON reply containing the
   words "I can't" is not treated as a refusal; the batch classification; the
   run summary counts.  In `data_analysis/tests/test_seed_entities.py`: a
   refused stem becomes `refused` with its record, is skipped by `check`, and
   is skipped by a second `generate` without `--retry-refused`.  Run the three
   test files and report the counts; the full suites are run by the caller.
6. **Docs**: a short section in `data_analysis/README.md` (where the
   generators' refusals are described for the audit tool; keep it near the
   openings-check and count-check notes) and a line in the `seed_entities.py`
   module docstring.  Do not edit `AGENT_NOTES.md` or `CLAUDE.md`; the caller
   updates the lifecycle text there.

## How to work

- Read `data_analysis/regenerate_trait_instructions.py`,
  `regenerate_role_instructions.py`, `seed_entities.py` and
  `audit_trait_instructions.py` (the `JudgeRefusal` pattern) with the Read
  tool before editing; edit with the Edit tool only.  Keep the change small
  and in the style of the surrounding code; no refactors beyond what the
  feature needs.
- No real API calls, no generation runs, no network except reading the
  Anthropic documentation for the refusal stop reason.
- Do not commit; the caller reviews the diff and commits.  Do not touch
  anything under `data/traits/instructions/`, `data/roles/instructions/`,
  `data/seed_queue.json` or `roger/`.
- Boundaries: read and write only inside this repository checkout; nothing
  elsewhere on the machine, no home-directory paths, no caches, no other
  projects, no listing of anything outside the checkout.
- When done, reply with: the files changed, the test counts, how a refusal
  now appears in a run log and in the queue, and anything you were unsure
  about.
