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
| 4 | [gloss.md](./gloss.md) | Write one sentence describing the persona, for a word that goes on as a trait.  A first draft for the Opus or Fable writer, in the corpus form | draft 4 (2026-10-08: a membership gloss is one clause; draft 3, 2026-09-30: for a plain fact, the fact wins over the length) |
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
| C | [overlap_six.md](./overlap_six.md) | Rubric A on six rungs, 0 to 5: the 2-3 region split by who adds something | draft 1 (arms experiment, 2026-10-04) |
| D | [overlap_relation.md](./overlap_relation.md) | Rubric A with the relation named instead of a number (same, variant, contains with the wider one, overlap, neighbours, different); the score derived | draft 1 (arms experiment, 2026-10-04) |
| E | [overlap_scope.md](./overlap_scope.md) | Rubric A with Roger's line 3 (narrowed, broadened, stronger, milder, a shift of emphasis; the reason names which) | draft 1 (arms experiment, 2026-10-04) |
| A2 | [overlap_concept_implies.md](./overlap_concept_implies.md) | Rubric A with lines 3 and 2 redrafted around the one-way implication test | draft 1 (arms experiment, round 2, 2026-10-04) |
| C2 | [overlap_six_implies.md](./overlap_six_implies.md) | Rubric C with lines 3 and 2 redrafted the same way | draft 1 (arms experiment, round 2, 2026-10-04) |
| D2 | [overlap_relation_implies.md](./overlap_relation_implies.md) | Rubric D with the "contains" and "overlap" lines redrafted the same way (the plainer one is the wider) | draft 1 (arms experiment, round 2, 2026-10-04) |
| E2 | [overlap_scope_implies.md](./overlap_scope_implies.md) | Rubric E with the test added to Roger's line 3, and A2's line 2 | draft 1 (arms experiment, round 2, 2026-10-04) |

Rubrics C, D and E are the three arms of the overlap rubric arms experiment
([coding_plan_overlap_arms.md](../coding_plan_overlap_arms.md)), each rubric A's text with only its scale
lines (and, for D, the opening question and the answer format) changed, pinned as version 1 on
2026-10-04.  A2, C2, D2 and E2 are its round 2 (the same brief, "Round 2"): each a round-1 rubric with
only its 2 and 3 lines replaced, because round 1 ([m3_overlap_arms_readout.md](../m3_overlap_arms_readout.md))
found the models describing a containment and answering 2; pinned as version 1 on 2026-10-04 and first
run on the calls that hold the pairs where that confusion was seen.

## The M3 relation call (added 2026-10-07)

The call before the overlap call in the M3 novelty check ([coding_plan_m3.md](../coding_plan_m3.md),
stage 3): for a candidate and its listed traits (the 10 nearest corpus traits and the members of their
pairs, triangles and tetrahedra), is each `similar`, `opposed`, `unrelated` or `unsure`?  Pinned in the
same `versions.json`; the overlap call itself reads rubric A above.

| file | what it asks | status |
|---|---|---|
| [relation.md](./relation.md) | How does each listed trait's concept stand to the candidate's: similar, opposed, unrelated, or unsure | draft 1, pinned as version 1 (the brief's text, unchanged) |

## How to edit

Each file holds one prompt inside a fenced block.  Change the text inside the block.  When you are
done, tell me which files you changed; I read your version, run it on the test words, and put the
results beside your marks.  Each run costs about five cents.

## Results so far

[sense_call_probe.md](../sense_call_probe.md) has the three runs made on 2026-09-29, with a row for
every word and a comparison with Roger's marks.
