# The split rubrics: index

Set up 2026-09-29 for Roger to read and edit.  These replace the single classifier prompt, whose
text is in [rubric_classifier_v4_as_sent.md](../rubric_classifier_v4_as_sent.md).  That prompt is
still what the code uses; nothing below has been built into the platform.  The plan for building
it in is [coding_plan_split.md](../coding_plan_split.md), which waits for Roger's go.

## The calls, in order

| order | file | what it asks | status |
|---|---|---|---|
| 1 | [step1_sense.md](./step1_sense.md) | What could "You are <label>." be taken to mean?  First thought, and ranked readings | draft 6, run one word per call |
| 2a | [check_established.md](./check_established.md) | Is the reading a use people make of the word, or one to be worked out?  Does the first thought get in the way? | draft 4, run one item per call |
| 2b | [check_vague.md](./check_vague.md) | Does the label leave something out?  Does the reading fit many people in different ways? | draft 3, run one item per call |
| 3 | [step2_kind.md](./step2_kind.md) | What kind of thing is this reading: trait, membership, state, physical, role, action, praise, or nothing about a persona? | draft 4, run one reading per call |
| 3b | [check_same_sense.md](./check_same_sense.md) | Are two primary readings one way of being or two?  Asked only when the kind call took both for a trait or a membership | draft 1, run once |
| 4 | [gloss.md](./gloss.md) | Write one sentence describing the persona, for a word that goes on as a trait.  A first draft for the Opus or Fable writer, in the corpus form | draft 2, run one item per call on Haiku 4.5 and on Sonnet 4.6 |
| 5a | [alignment.md](./alignment.md) | Does the description bear on how an AI treats those it works for? | first draft, run once |
| 5b | [descriptors.md](./descriptors.md) | Which region, and can a text-only persona show it? | first draft, run once |

The file for the kind call is named step2 because the two checks were added after it was first
drafted.  The later files are named for what they do.

## What joins them

Code, not a prompt.  **One item per call, always** (Roger, 2026-09-29): words sent in the same call
affect each other's answers.  A word with no primary reading is turned away, and so is a word whose
every primary reading is "stretched" in the established check.  Otherwise the kind of its most
likely reading decides where it goes: on as a trait, or to the states queue, the physical list or
the roles list.  The two checks only add notes.  By Roger's bar, a note is a concern to weigh, when
judging a word or when choosing between near-duplicates, and not a reason to reject.

## How to edit

Each file holds one prompt inside a fenced block.  Change the text inside the block.  When you are
done, tell me which files you changed; I read your version, run it on the test words, and put the
results beside your marks.  Each run costs about five cents.

## Results so far

[sense_call_probe.md](../sense_call_probe.md) has the three runs made on 2026-09-29, with a row for
every word and a comparison with Roger's marks.
