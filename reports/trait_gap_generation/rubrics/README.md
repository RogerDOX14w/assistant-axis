# The split rubrics: index

Set up 2026-09-29 for Roger to read and edit.  These replace the single classifier prompt, whose
text is in [rubric_classifier_v4_as_sent.md](../rubric_classifier_v4_as_sent.md).  That prompt is
still what the code uses; nothing below has been built into the platform.  The plan for building
it in is [coding_plan_split.md](../coding_plan_split.md), which waits for Roger's go.

## The calls, in order

| order | file | what it asks | status |
|---|---|---|---|
| 1 | [step1_sense.md](./step1_sense.md) | What could "You are <label>." be taken to mean?  First thought, and ranked readings | draft 8 (2026-10-01: words said of what people do or make), run one word per call |
| 2a | [check_established.md](./check_established.md) | Is the reading a use people make of the word, or one to be worked out?  Does the first thought get in the way? | draft 7 (2026-10-01: a manner of speaking or working counts as said of the person), run one item per call |
| 2b | [check_vague.md](./check_vague.md) | Does the label leave something out?  Does the reading fit many people in different ways? | draft 3, run one item per call |
| 3 | [step2_kind.md](./step2_kind.md) | What kind of thing is this reading: trait, membership, state, physical, role, action, praise, or nothing about a persona? | draft 6 (2026-10-01: others' regard is a trait, what they happen to be doing about the person is a state), run one reading per call |
| 3b | [check_same_sense.md](./check_same_sense.md) | Are two primary readings one way of being or two?  Asked only when the kind call took both for a trait or a membership | draft 2 (2026-09-30: example words replaced) |
| 4 | [gloss.md](./gloss.md) | Write one sentence describing the persona, for a word that goes on as a trait.  A first draft for the Opus or Fable writer, in the corpus form | draft 3 (2026-09-30: for a plain fact, the fact wins over the length) |
| 5a | [alignment.md](./alignment.md) | Does the description bear on how an AI treats those it works for? | draft 2 (2026-09-30: one example word replaced) |
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

## The M3 overlap call (added 2026-10-03)

Two rubrics for one call, not part of the split filter: for a candidate and the existing traits the
relation call judged similar, how close are they?  Both were drafted in
[m3_overlap_rubric_draft.md](../m3_overlap_rubric_draft.md), signed off by Roger as draft 2 on
2026-10-03, moved here unchanged and pinned as version 2 in the same `versions.json`.  The pre-pilot
test of both is [m3_overlap_test_readout.md](../m3_overlap_test_readout.md) (being written when these
moved).

| rubric | file | what it asks | status |
|---|---|---|---|
| A | [overlap_concept.md](./overlap_concept.md) | How similar is each listed trait's concept to the target's: 0 to 4, "opposite" or "unsure" | draft 2 (Roger's preference) |
| B | [overlap_cooccurrence.md](./overlap_cooccurrence.md) | How often would a persona with the target show each listed trait: 0 to 4 or "unsure" | draft 2 (the comparison arm) |

## How to edit

Each file holds one prompt inside a fenced block.  Change the text inside the block.  When you are
done, tell me which files you changed; I read your version, run it on the test words, and put the
results beside your marks.  Each run costs about five cents.

## Results so far

[sense_call_probe.md](../sense_call_probe.md) has the three runs made on 2026-09-29, with a row for
every word and a comparison with Roger's marks.
