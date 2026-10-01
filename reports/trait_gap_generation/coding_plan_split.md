# Coding plan: the split trait-hood filter (M1, second part)

Written 2026-09-29 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape, for one Opus job in the
M1 worktree.  It amends [coding_plan_platform.md](./coding_plan_platform.md) for M1 only.  Roger's
review comments go into this file.  **Nothing here starts until Roger gives the go.**

**What this is for.**  The trait-hood filter decides whether a candidate word can name a persona
trait.  Until now one long prompt made that decision, and it was found to lead the model: asked
about senses, tags, regions and a gloss at once, the model tried to be helpful and found a trait
sense in words that have none.  Roger's remedy, tested on 99 words on 2026-09-29, is a row of small
calls, each with its own short rubric and each blind to what its answer is for.  The rubrics exist
and are tested.  This job builds them into the platform, so that the filter can run on thousands of
words with the same records, caps and resume behavior as the rest of M1.  It does not improve the
rubrics: tuning has stopped, and a few wrong words slipping through is accepted.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| The single classifier prompt is replaced by separate small calls: sense, two checks, kind, gloss, alignment, descriptors. | One prompt did too much and pushed the model toward odd senses | [rubrics/README.md](./rubrics/README.md); [rubric_classifier_v4_as_sent.md](./rubric_classifier_v4_as_sent.md) section 4 |
| **One item per call, in every LLM call of the filter**, the definition probe and the comparison included. | Words sent together change each other's answers: 21 of 99 answers changed between two batched runs.  One per call, two different prompts agreed on 96 of 99 | [sense_call_probe.md](./sense_call_probe.md) |
| Steps 1 to 3 see the label, and readings of it, and nothing else: no intended sense, no gloss hint, no word of what the answers are used for. | That blindness is the point of the split | Roger, 2026-09-29 |
| The prompt text is Roger's.  The code sends the text inside each rubric file's fenced block, byte for byte. | He edits those files himself | [rubrics/README.md](./rubrics/README.md) |
| The join is code, by the rules of section 6. | Agreed and tested | [sense_call_probe.md](./sense_call_probe.md), "How the steps are joined" |
| A note is a concern to weigh, never a reason to reject.  A word is turned away only by the rules of section 6. | Roger's bar: reject only what is "too unclear to put in the corpus even if there is in fact no clearer alternative" | Roger, 2026-09-29 |
| States, physical features and roles go to their own lists.  A nationality, ethnicity or language membership is a trait held on the nationalities list. | Decisions 3 and 12 | [decisions_m1.md](./decisions_m1.md) |
| The gloss is a first draft in the corpus form.  The corpus description is written later by Opus or Fable and reviewed by Roger. | Roger, 2026-09-29 | [rubrics/gloss.md](./rubrics/gloss.md) |
| Every step runs on `claude-haiku-4-5-20251001` at temperature 0, the gloss included. | Haiku 4.5 is the only Haiku served.  Roger, 2026-09-29: "Haiku 4.5, unless we're getting a second opinion from Sonnet, in which case use the Sonnet one" | live model list; Roger |
| The second opinion runs on `claude-sonnet-5-5`.  For a word chosen for a second opinion, that model also writes the gloss, and its gloss is the row's gloss. | Roger, 2026-09-29: "SG, but use Sonnet 5.5" | Roger |
| The comparison call moves to `claude-sonnet-5-5`, one item per call.  Its prompt, version 2, is not changed. | Roger, 2026-09-29: "I'm inclined to move it".  Checked the same day on the 66 recorded rows: the two models give the same score, and one item per call, on either model, flags 3 of the six September rejects where 20 to a call flagged 1 | [probe_sonnet_move/](./probe_sonnet_move/) |
| **Small tests run live.  Full runs go through the Message Batches API.** | Roger, 2026-09-29: "use batches for reduced cost (at least once we're done with small-scale testing and are doing real full runs)" | Roger |
| The job's spending cap is $10, and the agent may ask for more. | Roger, 2026-09-29: an agent short of budget makes poor decisions, and "it's OK to come back to me and ask for more if needed" | Roger |
| The frequency floor of 1.5 with its three rescue routes, the WordNet count and the definition probe stay as built. | Decisions 1 and 5 | [decisions_m1.md](./decisions_m1.md) |
| The typed budget is the cap.  Quality figures are recorded targets, not gates. | Decisions 9 and 2 | [decisions_m1.md](./decisions_m1.md) |
| The full validation run stays on hold. | Unseen rows can be measured once only | Roger reserved the go |

## 2. Out of scope

- Any change to the text inside a rubric file's fenced block.  A typo or a fault goes into [QUESTIONS.md](./QUESTIONS.md).
- Any edit to [decisions_m1.md](./decisions_m1.md), [random_traits_for_marks.md](./random_traits_for_marks.md), [marks_corpus_readings.md](./marks_corpus_readings.md), [sense_call_probe.md](./sense_call_probe.md) or the `probe_*` record directories.  They are Roger's working files and the record of paid runs.
- **Any call on a row of [m1_validation.jsonl](../../data/candidates/validation/m1_validation.jsonl).**  The only words this job may send to a model are the 99 test words of section 8.
- Tuning: no rewording, no new examples, no new checks.
- Removing the single-call classifier.  It stays, behind `--pipeline single`, so recorded runs can be reproduced.
- M2, M3, merging, pushing, new dependencies.

## 3. Rule files to Read first

Open with the **Read tool**: [CLAUDE.md](../../CLAUDE.md), [provenance.md](../../.claude/rules/provenance.md), [judging.md](../../.claude/rules/judging.md), [judge-cost.md](../../.claude/rules/judge-cost.md), [entity-naming.md](../../.claude/rules/entity-naming.md).  Then read [rubrics/README.md](./rubrics/README.md), the eight rubric files, and the last four sections of [sense_call_probe.md](./sense_call_probe.md).

**File-access boundary, restated.**  Read, list and write only inside this repository, which
includes this worktree, plus the session scratchpad and the temporary directory.  Nothing else on
this machine may be read, listed, sized or searched, and that includes caches and other projects
under the home directory, even to see whether something is installed.  If the work seems to need
anything outside, stop and write the need into [QUESTIONS.md](./QUESTIONS.md).  Report any breach at
the top of the final report.  Never print, log or commit an API key or any line of the worktree's
environment file; load keys with `load_dotenv` and nothing else.  Commit on this worktree's branch only, and never push.  In every
`.md` file written for Roger, link every file named, with a path relative to that document.

**What to commit, and what to leave alone.**  Commit your code and tests, this plan, the
[rubrics/](./rubrics/) directory, [split_reference/](./split_reference/) and your test fixtures.  The
rubric files must be tracked, because the platform's check for uncommitted changes will cover them.
Do not commit, move or edit Roger's working files or the records of paid runs: those named in
section 2, [rubric_classifier_v4_as_sent.md](./rubric_classifier_v4_as_sent.md),
[rubric_v5_draft.md](./rubric_v5_draft.md) and every `probe_*` directory.  They stay untracked until
Roger asks.  So no test may read from a `probe_*` directory: copy the recorded answers a test needs
into [fixtures/gapgen_split/](../../assistant_axis/tests/fixtures/gapgen_split/) and commit the copy.

## 4. Existing code to reuse

- [filter.py](../../assistant_axis/gapgen/filter.py): `FilterRunner` and its call machinery (`_call`, `_record_response`, `_gather`, `_stop_on`, the budget stop that keeps every row paid for), `prepare`, `define_probe`, `holding_for`, `summarize`, `development_seen`.
- [llm.py](../../assistant_axis/gapgen/llm.py) `call_anthropic_json`; [cost.py](../../assistant_axis/gapgen/cost.py) `Estimate`, `GuardedUsage`, `confirm_or_abort`.
- [rubric_versions.py](../../assistant_axis/gapgen/rubric_versions.py): the rule that a version names one prompt text.
- [plain_reading.py](../../assistant_axis/gapgen/plain_reading.py): the comparison prompt, version 2, used unchanged in section 6.
- [states_pass.py](../../assistant_axis/gapgen/states_pass.py), [promote.py](../../assistant_axis/gapgen/promote.py), [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py): the readers of the filter block, which must keep working.
- [prompt_hygiene.py](../../assistant_axis/gapgen/prompt_hygiene.py): the check that example words are not corpus labels or test words.  Apply it to the eight prompts.
- [split_reference/join_reference.py](./split_reference/join_reference.py) and [split_reference/expected_outcomes.jsonl](./split_reference/expected_outcomes.jsonl): my reference join and its answers for the 99 words.
- Recorded answers to use as test fixtures, no API call needed: [probe_single/](./probe_single/) for step 1, [probe_rerun_wording/](./probe_rerun_wording/) for the checks and kinds, [probe_gloss_v2/](./probe_gloss_v2/) and [probe_last_step/](./probe_last_step/) for the last step.  Each `run.json` holds the prompt text and its SHA-256.  In `probe_rerun_wording` the established check has its own record beside the kind call's: [run_established.json](./probe_rerun_wording/run_established.json), [responses_established.jsonl](./probe_rerun_wording/responses_established.jsonl) and [usage_established.json](./probe_rerun_wording/usage_established.json).

## 5. File layout

| file | what it holds |
|---|---|
| [rubrics/](./rubrics/) | The eight rubric files stay where they are.  `paths.RUBRICS_DIR` points here, and the directory joins `runs.PLATFORM_PATHS`, so an uncommitted edit stops a paid run |
| [rubrics/versions.json](./rubrics/versions.json) | Append-only: for each prompt name, every version and the SHA-256 of its text.  A version is the draft number in the file's status row, so the first rows are sense 6, established 4, vague 3, kind 4, same_sense 1, gloss 2, alignment 1, descriptors 1.  Earlier drafts are in the probe records and are not pinned |
| [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) | `load_prompt(name) -> str` reads the fenced block; `current_versions()`; `mismatches()`, which [rubric_versions.py](../../assistant_axis/gapgen/rubric_versions.py) calls too |
| [split.py](../../assistant_axis/gapgen/split.py) | Pure functions: one parser and validator for each step; `join(...)`; `to_filter_block(...)` |
| [split_runner.py](../../assistant_axis/gapgen/split_runner.py) | `SplitRunner`: the four waves, live |
| [batches.py](../../assistant_axis/gapgen/batches.py) | Stage B: the same waves through the Message Batches API |
| [llm.py](../../assistant_axis/gapgen/llm.py) | `temperature` becomes optional and is left out of the request for a model that refuses it; `accepts_temperature(model)` decides |
| [judge_pricing.py](../../assistant_axis/judge_pricing.py) | One new rate, `("sonnet-5", 2.00, 10.00)`, placed before `"sonnet"`, and the `:batch` suffix rule of section 7.  Keep the change to those lines: the main checkout has its own uncommitted edits to this file | (Until 2026-10-01 the split filter wrote `@batch`; the repository's convention is `:batch`, `judge_pricing.BATCH_SUFFIX`, priced by a per-provider factor, and the first full validation run's records are read as `:batch`.)
| [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py) | `check`, and `bump NAME --why TEXT`, which appends to `versions.json` |
| [traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py) | New flags, section 7 |
| [split_test_words.jsonl](../../data/candidates/validation/split_test_words.jsonl) | The 99 words with their groups, built from `expected_outcomes.jsonl` |
| tests | [test_gapgen_split.py](../../assistant_axis/tests/test_gapgen_split.py), [test_gapgen_split_runner.py](../../assistant_axis/tests/test_gapgen_split_runner.py), [test_gapgen_split_rubrics.py](../../assistant_axis/tests/test_gapgen_split_rubrics.py), [test_gapgen_batches.py](../../assistant_axis/tests/test_gapgen_batches.py) |

## 6. The waves, the join and the record

**Waves.**  Every call carries one item.

| wave | calls | input |
|---|---|---|
| 0 | floor, WordNet, definition probe | as built, the probe one word per call |
| 1 | sense | the label |
| 2 | established, vague and kind, once for each primary reading | the label, the first thought where the rubric asks for it, the reading |
| 3 | same sense, only for a word with two readings left by rule 2 that are both trait or membership; comparison, only for a row with an intended sense | the label and the two readings |
| 4 | gloss, for outcome trait only, on the second model for a word chosen for a second opinion and on the first model otherwise; second opinion, steps 1 to 3 on the second model | the accepted reading of the first model's path |
| 5 | alignment and descriptors | the label and the gloss |

The words for a second opinion are chosen after wave 3, from the join, so wave 4 knows which model
writes each gloss.  The second model's gloss is written for the row's accepted reading, not for the
reading the second opinion itself would accept, so that the row's gloss and its `judged_sense` agree.

**The join.**  [join_reference.py](./split_reference/join_reference.py) is the rule in code; `split.join` must give the same answers on the recorded inputs.

1. Primary readings are taken in the order step 1 gave them.  None: turned away, tag `no_persona_reading`.
2. A primary reading called "stretched" is dropped.  None left: turned away, tag `stretched`.
3. The first reading left decides.  Kind trait or membership: the word goes on as a trait.
4. If the first is not a trait or membership but a later one is, the later one is accepted and the word goes on as a trait with the note `obvious_sense_not_trait`.
5. Otherwise state, physical and role send the word to the states, physical and roles lists.  Action, evaluative and not_a_persona turn it away.
6. The checks add notes and decide nothing, apart from "stretched" in rule 2.

**Notes**, added to `POLYSEMY_NOTES`: `first_thought_in_the_way`, `leaves_something_out`,
`fits_many_in_different_ways`, `most_likely_reading_stretched`, and the existing `two_trait_senses`,
`obvious_sense_not_trait`, `nontrait_person_sense`, `overshadowed`, `reading_related`.  `polysemy`
is true when any note is present.

**Two readings, one sense or two** (Roger, 2026-09-29: "yes, let's add it (where needed)").  When
two readings left by rule 2 are both trait or membership, and only then, the
same-sense check is asked about them.  Its answer is kept on the block as `same_sense`.
`two_trait_senses` is set only when the answer is "different".  On the test words 30 of 74 have two
such readings and the check calls 7 of them different.  Without the check the note would be set on
10 of the 16 plain trait words, garrulous and taciturn among them.

**A row with an intended sense.**  Compare the intended sense with each reading left by rule 2,
using the comparison prompt, one pair per call.  "same" as the accepted reading: nothing to add.
"same" as another trait or membership reading: that one becomes the accepted reading.  "related" to
the accepted reading: note `reading_related`.  Anything else: note `overshadowed`, and the word goes
where rules 3 to 5 send it.

**Mapping onto the frozen vocabulary.**  Readers of the block must not need changing.

| outcome | `verdict` | `tags` | `holding` |
|---|---|---|---|
| trait, kind trait | trait | none | none |
| trait, kind membership | trait | membership, with `membership_kind` | nationalities for that kind, else none |
| states, physical, roles | tagged | state, physical, role_person | states, physical, roles |
| turned away | reject | `no_persona_reading`, `stretched`, `action`, `evaluative_only` | none |

**The filter block**, new keys beside the old.  `rubric_version` becomes 5 and means the split.
Old keys stay: `judged_sense` is the accepted reading, `trait_sense_rank` its place among the
readings, `confidence` is null, `tag_disagreement` false.

```json
{"pipeline": "split", "rubric_version": 5,
 "step_versions": {"sense": 6, "established": 4, "vague": 3, "kind": 4, "same_sense": 1, "gloss": 2, "alignment": 1, "descriptors": 1},
 "model": "claude-haiku-4-5-20251001", "gloss_model": "claude-sonnet-5-5", "same_sense": null,
 "outcome": "trait", "rule": 4, "verdict": "trait", "tags": [], "membership_kind": null,
 "reason": "A habitual coldness of manner is a standing way of relating to people.",
 "sense": {"note": "...", "first_thought": "low temperature", "first_thought_said_of": "things", "usable": true,
           "readings": [{"reading": "your body temperature is low or you feel chilled", "rank": "primary",
                         "established": "well_known", "first_thought_in_the_way": false, "kind": "state",
                         "membership_kind": null, "vague": {"leaves_something_out": false, "missing": null, "fits_many_in_different_ways": false},
                         "reasons": {"established": "...", "vague": "...", "kind": "..."}}]},
 "accepted_reading": 1, "judged_sense": "you are emotionally distant, unfriendly, or aloof",
 "notes": ["obvious_sense_not_trait", "first_thought_in_the_way"], "polysemy": true,
 "polysemy_notes": ["obvious_sense_not_trait", "first_thought_in_the_way"],
 "region": "social_interpersonal", "enactable_in_text": 2, "alignment_relevant": false,
 "comparison": null,
 "second_opinion": {"model": "claude-sonnet-5-5", "outcome": "trait", "accepted": "you are emotionally distant and unfriendly", "agree": true},
 "prompt_sha256": {"sense": "...", "established": "..."}, "at": "2026-09-30T10:00:00+00:00"}
```

The row's `gloss` is the gloss call's sentence, or null for a word that did not go on as a trait.
`gloss_model` names the model that wrote it.  The states pass reads the accepted reading when a row
has no gloss.

**Second opinion** (decision 7, adapted, since the split has no confidence figure).  Steps 1 to 3
on the second model for a seeded 10% of the words that reached step 1, and for every word with the
note `obvious_sense_not_trait` or `most_likely_reading_stretched`.  The first model's outcome stays
the outcome.  Agreement means the same outcome.

**What `claude-sonnet-5-5` accepts**, tested 2026-09-29, records in
[probe_sonnet55_api/results.jsonl](./probe_sonnet55_api/results.jsonl).  It refuses `temperature`
with a 400, so its answers are not repeatable and the request must leave the setting out.  Its
thinking cannot be switched off; send no `thinking` setting and no effort setting, and set
`max_tokens` to 2000.  It counts about 30% more tokens than Haiku for the same text: the kind call
was 955 tokens in and 59 out.  Its price is $2 and $10 for a million tokens, half that in a batch.

## 7. CLI

`traithood_filter.py` gains `--pipeline split|single` (default split), `--transport
auto|live|batches` (default auto) and `--resume`.  `--second-model` and `--compare-model` now
default to `claude-sonnet-5-5`, here and in
[plain_reading.py](../../data_analysis/gap_generation/plain_reading.py).  `--batch-size` is refused with `--pipeline split`.  The run refuses to start
when `split_rubrics.mismatches()` is not empty, and prints the `rubric_pins.py bump` command that
would pin the text.

**`--transport auto`** sends a run of fewer than 300 words live and a larger one through the
Message Batches API.  The choice and the reason are printed with the estimate.

**Estimate**, printed by step.  Haiku's token counts are measured, from the `usage.json` of the
probe records.  The second model's are Haiku's raised by 30%, apart from the kind call, which was
measured.

| step | calls for each word | tokens in, out | model | for each call, live |
|---|---|---|---|---|
| sense | 1 | 567, 207 | Haiku | $0.0016 |
| established | 1.3 | 420, 94 | Haiku | $0.0009 |
| vague | 1.3 | 420, 94 | Haiku | $0.0009 |
| kind | 1.3 | 718, 78 | Haiku | $0.0011 |
| same sense | 0.3 | 347, 80 | Haiku | $0.0007 |
| gloss | share that goes on as a trait | 490, 44 | Haiku | $0.0007 |
| alignment, descriptors | two for each gloss | 350, 70 | Haiku | $0.0007 |
| second opinion, with its gloss | about 0.2 | steps 1 to 3 and the gloss | Sonnet 5.5 | $0.015 for each word chosen |

That is about $0.007 a word without the second opinion and $0.010 with it: about $100 for 10,000
words live and $50 in batches.  A full run crosses the $20 line at about 2,000 words live and 4,000
in batches, and then needs Roger's explicit go.  Prompt caching cannot help: every prompt is under
Haiku's 4,096-token minimum.

**`--resume`.**  A rerun of a batch id sends no call whose answer is already in `responses.jsonl`
for the same step, prompt hash, model and input.

**Batches (stage B).**  Each wave is submitted as one Message Batch, one request for each call,
`custom_id` made of step, key and reading index.  Load the `claude-api` skill for the request and
result shapes; do not write them from memory.  Batch ids and wave state go to
`filter/<batch>/batches.json` so a killed process picks up where it stopped.  The estimate is
checked before each wave is submitted.  Usage is charged under the key `<model>:batch` at half the
model's rates, which needs a suffix rule and a test in
[judge_pricing.py](../../assistant_axis/judge_pricing.py).

## 8. Acceptance tests, written first

No unit test calls an API.  Fake clients replay the recorded answers.

1. **Pins.**  The SHA-256 of each prompt loaded from its file equals its latest row in `versions.json`.  Write the first rows from the text on disk, and check each once, by hand, against the record of the paid run that last used it: sense in [probe_single/run.json](./probe_single/run.json), established in [probe_rerun_wording/run_established.json](./probe_rerun_wording/run_established.json), vague in [probe_checks_single/run.json](./probe_checks_single/run.json), kind in [probe_rerun_wording/run.json](./probe_rerun_wording/run.json), gloss in [probe_gloss_v2/run.json](./probe_gloss_v2/run.json), same sense in [probe_same_sense/run.json](./probe_same_sense/run.json), alignment and descriptors in [probe_last_step/run.json](./probe_last_step/run.json).  All eight matched on 2026-09-29.  A changed text with no new row in `versions.json` fails.
2. **Join.**  `split.join` on the recorded answers of [probe_rerun_wording/results.jsonl](./probe_rerun_wording/results.jsonl) and [probe_same_sense/results.jsonl](./probe_same_sense/results.jsonl) gives, for all 99 words, the outcome, accepted reading and notes of [expected_outcomes.jsonl](./split_reference/expected_outcomes.jsonl): 74 trait, 7 states, 2 physical, 16 turned away, and `two_trait_senses` on 7 words.  Seven accepted readings have no vague answer on record; their vague notes are left out of the comparison.
3. **One item per call.**  Every user payload the runner builds holds exactly one item, in every wave.
4. **Blindness.**  No payload of waves 1 and 2 contains the intended sense or gloss hint.
5. **Vocabulary.**  Every block maps to the table of section 6; `promote`, `gap_registry.py report` and the states pass run on split rows.
6. **Stops and resume.**  A budget stop keeps every answer paid for; `--resume` sends only what is missing.
7. **Parse rate.**  `warn_if_low_parse_rate` for each step and model.  A row that fails validation is retried once, alone.
8. **Batches.**  With a fake batch client: waves in order, results matched by `custom_id`, half-rate charging, restart from `batches.json`.  `--transport auto` picks live below 300 words and batches from 300.
9. **The second model.**  No request to `claude-sonnet-5-5` carries `temperature`, `thinking` or an effort setting.  Its calls are priced at $2 and $10.  A word chosen for a second opinion gets its gloss from the second model, written for the row's accepted reading, and no gloss call goes to the first model for that word.
10. The existing suite still passes: `uv run pytest assistant_axis/tests -k gapgen` and `uv run pytest data_analysis/tests/test_gap_generation_cli.py`.

## 9. Ordered task checklist

Stage A, live:

1. Read section 3's files.  Write the tests of section 8, items 1 to 7 and 9, and see them fail.
2. `paths.RUBRICS_DIR`, `PLATFORM_PATHS`, `split_rubrics.py`, `versions.json`, `rubric_pins.py`.  Test 1.
3. `split.py`: parsers, validators, `join`, `to_filter_block`.  Tests 2 and 5.
4. `llm.py` and `judge_pricing.py` for the second model.  Test 9.
5. `split_runner.py`, with the probe and the comparison at one item per call.  Tests 3, 4, 6, 7.
6. CLI flags, the estimate by step, `split_test_words.jsonl`.  `--dry-run` on the 99 words.
7. Commit.  Then the pilot of section 10, run A.
8. Report stage A in [acceptance_split.md](./acceptance_split.md) before starting stage B.

Stage B, batches:

9. Test 8, then `batches.py` and `--transport`.
10. Commit.  Then the pilot, run B.
11. Update [data_analysis/README.md](../../data_analysis/README.md) and finish the report.

Stage B is needed: full runs go through batches.  If it cannot be finished in this job, say so in
the report, with what is left.

## 10. Pilot

Both runs use [split_test_words.jsonl](../../data/candidates/validation/split_test_words.jsonl) and
nothing else.  Neither is a measurement run, so do not pass `--measurement`: the 99 words then
count as seen in development, which is what they are.

| run | command | estimate | cap |
|---|---|---|---|
| A | `--pipeline split --transport live --validation-file ... --batch-id split_pilot_live` | $1.00 | `--budget-usd 3` |
| B | the same with `--transport batches --batch-id split_pilot_batches` | $0.50 | `--budget-usd 2` |

**The whole job may spend $10**, which is about six times what the two runs should cost, so that a
rerun after a fix is never a worry.  If the work needs more, stop and ask: asking is the right move
and costs nothing.  Do not cut a test short, skip a rerun or guess at a result to save money.

Recorded targets, not gates:

- At least 95 of the words that reach step 1 end with the outcome of [expected_outcomes.jsonl](./split_reference/expected_outcomes.jsonl).  List every difference, with both readings.
- Words cut by the floor or the probe are listed apart.  The probes did not apply the floor.
- Parse rate of 99% or better for every step.
- Every gloss opens "This means" and an -ing verb.
- Cost for each word, by step, against the estimate of section 7.
- Run B agrees with run A on at least 95 words.

Roger decides on the pilot whether the split replaces the single call for the full validation run.

## 11. Report at the end

[acceptance_split.md](./acceptance_split.md), one page: what was built, deviations from this plan,
test results, the pilot tables, cost from `usage.json`, and anything Roger should look at.  Lead
with the outcome.

## 12. Escalation

Retry once.  Then write the question into [QUESTIONS.md](./QUESTIONS.md) and proceed under a stated
assumption, unless the answer would make the work useless.  Stop and ask when the work would need a
change to a prompt's text, a call on a validation row, a file outside the boundary, or spending
past $10.  Asking for more budget is always acceptable.
