# Acceptance: the split trait-hood filter

Written 2026-09-29 and 30 against [coding_plan_split.md](./coding_plan_split.md).

## Outcome

**Both stages are built, tested and piloted on the 99 test words, for $1.37 of the $10 allowed.**
Every step parsed 100% in both runs, and every gloss has the corpus form.  Three recorded targets are
missed, and the cause is the same for all three: the model does not give the same answer twice, even
at temperature 0.  The code joins the answers it gets exactly as the reference join does.

| target (section 10) | run A, live | run B, batches |
|---|---|---|
| at least 95 of 99 with the expected outcome | **92** | **90** |
| parse rate 99% or better, every step | 100% | 100% |
| every gloss "This means" plus an -ing verb | 69 of 69 | 69 of 69 |
| cost against the estimate | $0.917 against $1.019 | $0.457 against $0.509 |
| run B agrees with run A on at least 95 | | **93** |

What Roger should look at:

1. **Step 1 is not repeatable.**  Sent the same label again, Haiku 4.5 at temperature 0 gave a
   different sense answer for 59 of 99 words, usually only in wording.  About one word in fifteen then
   changes outcome, and the words that change are the ones on a boundary (incestuous, linear,
   deterministic, twisted, grubby, migratory).  One item per call removed the effect words had on each
   other; it did not remove this.  Whether 90 to 92 of 99 is good enough to replace the single call
   for the full validation run is Roger's decision (section 10); [QUESTIONS.md](./QUESTIONS.md) 23.
2. **Batches are slow in wall time.**  Run B took 2 hours 11 minutes, because the waves depend on
   each other and each batch took 7 to 34 minutes to end whatever its size (13 requests: 34 minutes; 381: 15).  A full run has the same
   seven waves, plus a retry wave where needed, so several hours is to be expected.  `--resume` picks
   a killed run up where it stopped.
3. **A reporting fault, fixed after run A.**  Run A's [summary.json](../../data/candidates/filter/split_pilot_live/summary.json)
   gives `second_opinion_n: 0` at the top level; its `split` block has the right figure (13).  And
   run A's and run B's [run.json](../../data/candidates/filter/split_pilot_batches/run.json) name only
   the eight split prompts, not the probe and comparison prompts also sent (each filter block has all
   ten).  Both are fixed for later runs.

## Stage A: outcome

**Built and piloted.  92 of the 99 test words end with the outcome of
[expected_outcomes.jsonl](./split_reference/expected_outcomes.jsonl), against a target of 95.  Every
step parsed 100%, every gloss opens "This means" and an -ing verb, and the run cost $0.917 against an
estimate of $1.019.**  None of the 7 differences comes from the code.  On identical inputs the two checks,
the kind call and the same-sense check gave the recorded answer 242 times out of 249.  Step 1 did not repeat itself:
Haiku 4.5 at temperature 0 gave a different answer for 59 of 99 words, most only in wording.  Five of
the 7 differences start there, and two are check answers that flipped on words near a boundary.

Run: [split_pilot_live](../../data/candidates/filter/split_pilot_live/) ([run.json](../../data/candidates/filter/split_pilot_live/run.json),
[results.jsonl](../../data/candidates/filter/split_pilot_live/results.jsonl),
[responses.jsonl](../../data/candidates/filter/split_pilot_live/responses.jsonl),
[usage.json](../../data/candidates/filter/split_pilot_live/usage.json),
[summary.json](../../data/candidates/filter/split_pilot_live/summary.json)).

```
uv run python data_analysis/gap_generation/traithood_filter.py --pipeline split --transport live \
    --validation-file data/candidates/validation/split_test_words.jsonl --batch-id split_pilot_live --budget-usd 3
```

## Stage A: the pilot against the recorded targets

| target (section 10) | result |
|---|---|
| at least 95 of the words that reach step 1 end with the expected outcome | **92 of 99** (table below) |
| words cut by the floor or the probe, listed apart | none: 13 words were in the probe band, and the probe knew all 13 |
| parse rate of 99% or better for every step | 100% for all 15 step and model pairs, first pass |
| every gloss opens "This means" and an -ing verb | 69 of 69 |
| cost for each word, by step, against the estimate | $0.0093 a word against $0.0103 (table below) |

| outcome | expected | run A |
|---|---|---|
| trait | 74 | 69 |
| states | 7 | 10 |
| physical | 2 | 2 |
| turned away | 16 | 18 |
| note `two_trait_senses` | 7 | 10 |

### Every word whose outcome differs

| word | expected | reading expected | run A | reading accepted, or cause | where it diverged |
|---|---|---|---|---|---|
| deterministic | trait | you are predictable, your behavior follows fixed patterns | turned away | stretched | the established check, on the same reading: from_parts before, stretched now |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | states | you are subject to or deserve discipline and punishment | step 1: the enforcer reading is gone; the first reading is now the state |
| economic | trait | you are financially prudent or careful with money | turned away | stretched | step 1 reworded the reading ("you are prudent with money and resources; you spend carefully"), and the established check called the new wording stretched |
| grubby | trait | you are slovenly or unkempt in appearance | states | your body or clothes are dirty | step 1: the slovenly reading dropped from primary to secondary |
| incestuous | trait | you engage in or are party to incest | turned away | action | the kind call, on the same reading: trait before, action now |
| linear | turned away | (stretched) | trait | your thinking or approach is direct and follows one path without branching | step 1 gave a new first thought, so the established check saw new input and did not call the reading stretched |
| twisted | trait | your thinking or character is distorted or corrupt | states | your body or posture is bent or contorted | step 1: the character reading dropped from primary to secondary |

Every row is in the run's [results.jsonl](../../data/candidates/filter/split_pilot_live/results.jsonl);
the recorded answers are in [expected_outcomes.jsonl](./split_reference/expected_outcomes.jsonl).

Three of these were words the wording changes of 2026-09-29 were made for (incestuous, linear) or
that sat on the line then (deterministic).  They are the words most likely to flip on a rerun.  A
further 21 words kept their outcome with a differently worded accepted reading.

### How far step 1 repeats itself

The same item sent again, compared with the recorded answer (reasons and notes left out):

| step | same answer | different answer | input not on record |
|---|---|---|---|
| sense | 40 | 59 | 0 |
| established | 81 | 1 | 45 |
| kind | 86 | 2 | 39 |
| vague | 61 | 2 | 64 |
| same sense | 14 | 2 | 12 |

"Input not on record" means step 1 gave a reading worded differently from the recorded one, so there
is nothing to compare.  The vague check has more of these because it now runs on every primary
reading, as the plan says; the probe asked it of the first primary reading only.

### Second opinion

13 words: a seeded 10 plus the 3 with the note `obvious_sense_not_trait`.  Sonnet 5.5 wrote the gloss
for the 11 that went on as traits.  It disagreed on 2:

| word | Haiku 4.5 | Sonnet 5.5 |
|---|---|---|
| linear | trait | turned away, no reading (the expected outcome) |
| one-time | turned away | roles ("previously held a role") |

The run's [summary.json](../../data/candidates/filter/split_pilot_live/summary.json) shows
`second_opinion_n: 0` and `disagreements: 0` at the top level.  That was a reporting fault (the
single pipeline counts second opinions by a key the split does not write), fixed after this run; the
`split.second_opinion` block in the same file is right.

### Cost by step

Measured tokens are the mean for each call.  The estimate is section 7's.

| step | model | calls | tokens in, out (measured) | tokens in, out (estimate) | cost | for each word |
|---|---|---|---|---|---|---|
| definition probe | Haiku 4.5 | 13 | 321, 99 | 420, 70 | $0.0106 | $0.0001 |
| sense | Haiku 4.5 | 99 | 573, 209 | 567, 207 | $0.1606 | $0.0016 |
| established | Haiku 4.5 | 127 | 467, 91 | 420, 94 | $0.1174 | $0.0012 |
| vague | Haiku 4.5 | 127 | 375, 97 | 420, 94 | $0.1095 | $0.0011 |
| kind | Haiku 4.5 | 127 | 736, 78 | 718, 78 | $0.1432 | $0.0014 |
| same sense | Haiku 4.5 | 28 | 347, 79 | 347, 80 | $0.0209 | $0.0002 |
| gloss | Haiku 4.5 | 58 | 490, 42 | 490, 44 | $0.0409 | $0.0004 |
| gloss | Sonnet 5.5 | 11 | 624, 69 | 637, 57 | $0.0213 | $0.0002 |
| alignment | Haiku 4.5 | 69 | 280, 72 | 350, 70 | $0.0444 | $0.0004 |
| descriptors | Haiku 4.5 | 69 | 362, 88 | 350, 70 | $0.0556 | $0.0006 |
| second opinion: sense | Sonnet 5.5 | 13 | 730, 189 | 737, 269 | $0.0437 | $0.0004 |
| second opinion: established | Sonnet 5.5 | 21 | 566, 95 | 546, 122 | $0.0438 | $0.0004 |
| second opinion: vague | Sonnet 5.5 | 21 | 463, 105 | 546, 122 | $0.0417 | $0.0004 |
| second opinion: kind | Sonnet 5.5 | 21 | 957, 73 | 955, 59 | $0.0557 | $0.0006 |
| second opinion: same sense | Sonnet 5.5 | 5 | 421, 76 | 451, 104 | $0.0080 | $0.0001 |
| **all** | | **809** | | | **$0.9171** | **$0.0093** |

From [usage.json](../../data/candidates/filter/split_pilot_live/usage.json): Haiku 4.5 717 calls,
$0.703; Sonnet 5.5 92 calls, $0.214.  Sonnet 5.5's thinking is billed as output, and its measured
output stayed within the estimate.

## Stage B: batches

**Built and piloted: 90 of 99 as expected, 93 of 99 the same as run A, $0.457, 100% parse.**

Run: [split_pilot_batches](../../data/candidates/filter/split_pilot_batches/)
([batches.json](../../data/candidates/filter/split_pilot_batches/batches.json),
[results.jsonl](../../data/candidates/filter/split_pilot_batches/results.jsonl),
[responses.jsonl](../../data/candidates/filter/split_pilot_batches/responses.jsonl),
[usage.json](../../data/candidates/filter/split_pilot_batches/usage.json),
[summary.json](../../data/candidates/filter/split_pilot_batches/summary.json)).  The command is run
A's with `--transport batches --batch-id split_pilot_batches --budget-usd 2`.

| | run B |
|---|---|
| batches, one for each wave | 7 (probe 13, sense 99, checks 381, same sense 30, gloss and second-opinion sense 82, last step and second-opinion checks 198, second-opinion same sense 6 requests); no retry wave was needed |
| wall time | 2 h 11 min (submitted 21:07, last collected 23:18 UTC) |
| cost | $0.457: Haiku 4.5 at batch rates 719 calls $0.352; Sonnet 5.5 at batch rates 90 calls $0.105 |
| against the estimate | $0.509 |
| cost for each word | $0.0046 |
| outcomes | trait 69, states 9, physical 2, roles 1, turned away 18; `two_trait_senses` on 6 |

Every call was charged under `<model>@batch` at half the model's rates; the per-step token counts
match run A's to within a token or two.

### Every word whose outcome differs from the expected

| word | expected | reading expected | run B | reading accepted, or cause |
|---|---|---|---|---|
| deterministic | trait | you are predictable, your behavior follows fixed patterns | turned away | stretched |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | states | you are subject to or will face disciplinary action or punishment |
| disrespectful | trait | have a disrespectful character or attitude | turned away | action |
| economic | trait | you are financially prudent or careful with money | turned away | stretched |
| grubby | trait | you are slovenly or unkempt in appearance | states | your body or clothes are dirty |
| hit-and-run | turned away | (action) | trait | you are someone who flees responsibility after causing harm |
| linear | turned away | (stretched) | trait | your thinking or approach proceeds in a straight sequence without branching or looping back |
| migratory | trait | you move from place to place, or travel seasonally | turned away | stretched |
| pedagogic | trait | you should adopt a teaching manner or approach in how you act | roles | you teach or work in education |

deterministic, disciplinary, economic, grubby and linear miss in both runs.  incestuous and twisted
missed in run A only; disrespectful, hit-and-run, migratory and pedagogic in run B only.

### Run B against run A

| word | run A | run B | reading A | reading B |
|---|---|---|---|---|
| disrespectful | trait | turned away | act in a rude or impolite way toward others | (action) |
| hit-and-run | turned away | trait | (action) | you are someone who flees responsibility after causing harm |
| incestuous | turned away | trait | (action) | you engage in or are party to incest |
| migratory | trait | turned away | you move from place to place, or travel seasonally | (stretched) |
| pedagogic | trait | roles | you should adopt a teaching manner or approach in how you act | you teach or work in education |
| twisted | states | trait | your body or posture is bent or contorted | your mind or thinking is distorted or warped |

The second opinion chose the same 13 words and disagreed on the same two (linear, one-time) in both
runs.

## What was built, and the deviations from the plan

Built as sections 5 to 7 say: [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py),
[split.py](../../assistant_axis/gapgen/split.py), [split_runner.py](../../assistant_axis/gapgen/split_runner.py),
[batches.py](../../assistant_axis/gapgen/batches.py), [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py),
[versions.json](./rubrics/versions.json), [split_test_words.jsonl](../../data/candidates/validation/split_test_words.jsonl),
and the edits to [llm.py](../../assistant_axis/gapgen/llm.py), [judge_pricing.py](../../assistant_axis/judge_pricing.py)
and [traithood_filter.py](../../data_analysis/gap_generation/traithood_filter.py).

| deviation | why |
|---|---|
| The split side of the command line lives in [split_cli.py](../../data_analysis/gap_generation/split_cli.py), called from `traithood_filter.py` when `--pipeline split` | Keeps the single-call path in `traithood_filter.py` as it was; the flags are still `traithood_filter.py`'s, as the plan says |
| The second opinion's steps run in waves 4, 5 and 6, not all in wave 4 | Its checks need its own step 1, and its same-sense check needs its kind calls |
| The definition probe runs before step 1, not after classification as in the single pipeline | A word the probe does not know is cut before any other call is paid for; the selection (the probe band) is unchanged |
| The vague check runs on every primary reading | The plan's wave table and estimate say so; the probes asked it of the first primary reading only, so a vague note may now also come from an accepted second reading |
| The existing single-pipeline CLI tests pass `--pipeline single` | The plan makes split the default; only arguments changed, no expected value |

## Tests

| command | before (the first agent's baseline) | now |
|---|---|---|
| `uv run pytest assistant_axis/tests -k gapgen` | 390 passed, 4 skipped | 460 passed, 4 skipped |
| `uv run pytest data_analysis/tests/test_gap_generation_cli.py` | 20 passed | 20 passed |

No test calls an API: fake clients replay the answers recorded on 2026-09-29, copied into
[fixtures/gapgen_split/](../../assistant_axis/tests/fixtures/gapgen_split/) and checked to be
verbatim copies of the probe records.

## Follow-up of 2026-09-30: three new rubric texts, and large waves

**Done, no paid call.**  Tests: `uv run pytest assistant_axis/tests -k gapgen` 465 passed, 4
skipped; `uv run pytest data_analysis/tests/test_gap_generation_cli.py` 20 passed.

### The three rubric texts

The coordinator's edits, approved by Roger, pinned in [versions.json](./rubrics/versions.json) with
`rubric_pins.py bump`.  Each hash equals the one in that edit's run record under
[probe_rubric_edits/](./probe_rubric_edits/).

| prompt | version | sha256 | what changed |
|---|---|---|---|
| [gloss.md](./rubrics/gloss.md) | 3 | bcc278479f04... | for a plain fact the length gives way, and no details the reading does not give ("The fact wins") |
| [check_same_sense.md](./rubrics/check_same_sense.md) | 2 | d5953c971690... | example readings: idle conversation, chipper, informal, embittered |
| [alignment.md](./rubrics/alignment.md) | 2 | 4dbe7f7e55e6... | example word: chipper |

- The hygiene test in [test_gapgen_split_rubrics.py](../../assistant_axis/tests/test_gapgen_split_rubrics.py)
  no longer records cheerful, casual or resentful.  None of the four new words is in the corpus,
  the seed queue, the validation file, the reserved words or the test words; they are now on the
  test's list of checked example words.  [QUESTIONS.md](./QUESTIONS.md) 22 is marked answered.
- A new test checks that versions 3, 2 and 2 name the texts the edit runs sent.  The runner test
  now reads the step versions from the pins rather than naming them.
- The [rubrics index](./rubrics/README.md) status cells follow the new drafts.  The example block
  in [coding_plan_split.md](./coding_plan_split.md) is left as written: it illustrates the block's
  shape, and the plan is the record of what was specified.
- The two pilots ran on the old texts (gloss 2, same sense 1, alignment 1).  Their filter blocks
  and run.json files say so, and the pin audit accepts them because every version stays in
  versions.json.

### Large waves

A wave used to go out as one batch, and the service refuses one of more than 100,000 requests or
256 MB.  [batches.py](../../assistant_axis/gapgen/batches.py) now splits a wave, in order, into
batches of at most `MAX_BATCH_REQUESTS = 50,000` requests and `MAX_BATCH_BYTES = 128 MB` of
serialized requests.  That is half of each service limit.  At about 3,000 bytes a request the byte
limit binds first, at about 45,000 requests.  A test can lower either constant.

- **All at once.**  The batches of a wave are submitted one after another and then polled together.
  A large wave therefore waits about one batch's time, not one for each batch.  Run B showed a
  batch takes 7 to 34 minutes whatever its size, so waiting in series would multiply that.
- **Estimate.**  The check covers the whole wave before the first batch is submitted: the spend so
  far, plus the recorded batches still to be charged, plus every request about to go.  If it
  fails, nothing new is submitted, recorded batches are still collected, and the run stops.
- **Restart.**  Each batch is written to `batches.json` as soon as it is created.  A killed
  process collects every uncollected batch of the wave and submits only the calls no recorded batch
  covers.

New tests in [test_gapgen_batches.py](../../assistant_axis/tests/test_gapgen_batches.py):

- a wave over the request limit becomes several batches, with every call in one batch and every
  result charged once;
- the byte limit splits too;
- a process killed while submitting a wave's second batch collects the first on restart and
  submits only the rest;
- a cap that one batch fits under but the wave does not submits nothing.

## Follow-up of 2026-09-30 (second): the alignment score, and refused plain readings

**Done, no paid call.**  Tests: `uv run pytest assistant_axis/tests -k gapgen` 506 passed, 4
skipped; `uv run pytest data_analysis/tests/test_gap_generation_cli.py` 20 passed.

### The alignment check answers 0 to 3

[alignment.md](./rubrics/alignment.md) draft 3 (Roger's proposal and edits) is pinned as version 3,
sha256 c46c2e8f7e12..., the text of the recorded runs in
[probe_alignment_graded/draft4_corpus](./probe_alignment_graded/draft4_corpus/run.json).

| what | where | now |
|---|---|---|
| parser | [split.py](../../assistant_axis/gapgen/split.py) `parse_alignment` | `reason`, and `alignment` a JSON integer 0 to 3.  A boolean, a string, a float, a number out of range or the old key fails validation and is retried once |
| filter block | `to_filter_block` | new key `alignment` (the score).  `alignment_relevant` kept and **derived**: true for 2 or 3, false for 0 or 1.  Both null for a row that did not go on as a trait, or whose alignment call failed twice |
| summary | [split_cli.py](../../data_analysis/gap_generation/split_cli.py) | `v2_fields.alignment_scores`: the count of 0, 1, 2 and 3 (and of failed calls) beside `alignment_relevant_true` |
| fixtures | [recorded_answers.jsonl](../../assistant_axis/tests/fixtures/gapgen_split/recorded_answers.jsonl) | the 74 old yes-or-no answers replaced by the 69 graded answers of [probe_alignment_graded/draft4_pilot](./probe_alignment_graded/draft4_pilot/); the replay finds them by label, since they were asked on the live pilot's glosses |

**Hygiene.**  The example phrases ("telling those in charge whatever they want to hear", "cutting
corners to finish sooner") and the example words "chipper" and "long-winded" raise no hit.  One
prose word does: **"serious"** ("avoiding serious harm", "doing serious harm") is in the corpus, the
queue or the validation file.  The rule allows prose words, as it does "clear", "mean" and "hot" in
the other prompts.  It is recorded in the test, and the prompt is unchanged.

The two pilots ran on draft 1 (yes or no).  Their blocks have `alignment_relevant` and no
`alignment`.

### A refused plain reading is a refusal

In the corpus comparison, Haiku answered one plain reading with "I can't create content that
describes or normalizes homophobic behavior ...", and the comparison counted that as a different
reading.  [plain_reading.py](../../assistant_axis/gapgen/plain_reading.py) now records such a row
with stage `refused`.  No comparison is made, no note is raised, and the summary lists refused rows
(`n_refused`, `refused`).  In the single pipeline, the filter block's comparison carries the error
and no note.

**The rule** (`is_refusal`): the sentence opens with a first-person refusal ("I can't", "I cannot",
"I won't", "I'm unable", "I'm sorry", "Sorry", "I apologize" and the like) **and** names the request
or its output ("content", "create", "write", "describe", "portray", "role-play", "help with", "this
request" and the like).  An API `stop_reason` of "refusal" also counts.  The second half keeps a
first-person reading such as "I can't stop talking" from counting.  Over the 36 plain readings on
record in the repository's other runs it flags none.

**What it misses:** a refusal that opens any other way ("As an AI, ...", "This request ..."); one
that complies with a caveat; one in another language; and a refusal that names none of the listed
words.

Tests: [test_gapgen_plain_reading_refusal.py](../../assistant_axis/tests/test_gapgen_plain_reading_refusal.py).
