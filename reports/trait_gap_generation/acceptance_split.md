# Acceptance: the split trait-hood filter

Written 2026-09-29 against [coding_plan_split.md](./coding_plan_split.md).  Stage A (live) is below;
stage B (batches) follows once its pilot has run.

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
