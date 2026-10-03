# Draft: the M3 overlap rubrics, and the test that chooses between them

| | |
|---|---|
| **Status** | Draft 1, 2026-10-02, for Roger to read and edit before the test runs.  Nothing has run on these prompts yet. |
| **What it is for** | Step 5 of the M3 design ([coding_plan_platform.md](./coding_plan_platform.md), last section): for a candidate trait and the existing traits the relation call judged *similar*, how much do their concepts overlap?  The answer, with the alignment score, decides whether the candidate is a gap or too close to something we have. |
| **Two rubrics** | **A, concept similarity** (Roger's preference, 2026-10-02: "ask about how similar the concepts are, rather than how often a persona showing one would show the other"), and **B, co-occurrence**, as the comparison arm ("we can, of course, try both, and find out which works better"). |
| **What the model is shown** | The candidate's label and description, then a numbered list of existing traits with theirs, in random order, with no embedding scores or ranks. |
| **What it returns** | For each listed trait, a reason, then a score (or *opposite*, or *unsure*). |

This file sits outside [rubrics/](./rubrics/) on purpose: that directory is checked for uncommitted
changes before every paid run, and a draft there would stop one.  When a rubric is adopted its text
moves there as draft 1 and is pinned.

**To edit:** change the text inside the blocks below.  Everything between the fence lines is what
the model would see.  Notes for me go under "Your notes".

Every example word was checked against the corpus labels, the seed queue, the validation file, the
99 split test words and the reserved-word list: none of them is any of those (Roger's rule for rubric
examples: near-duplicates of corpus terms, never the terms themselves).

## Rubric A: concept similarity

````text
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how similar its concept is to the target's: are they the same concept, or different concepts?

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person. Two traits can go together often and still be different concepts, as being punctual and being tidy do.

Give one of these answers for each listed trait:
- 4: the same concept. Either label could replace the other in any description of a persona. For example, talkative and loquacious.
- 3: the same concept, differing only in scope, degree or emphasis. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further.
- 2: overlapping concepts. They share a core, but each adds something the other lacks. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.
- 1: related but distinct concepts: neighbours, not the same concept. For example, tetchy and sullen: both are bad-tempered, but quick irritation is a different thing from silent resentment.
- 0: different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "opposite": the listed trait is the reverse of the target, the same quality at the other end. For example, cheery and morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}]}
Return one row per listed trait, in the order given.
````

## Rubric B: co-occurrence

````text
You are given one JSON object: a persona trait, the target ("target"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how often a persona that has the target trait would also show the listed trait.

Judge how the two go together in a person, not whether they are the same concept. Two traits can be different concepts and still nearly always go together.

Give one of these answers for each listed trait:
- 4: almost always: a persona with the target trait would show this one too. For example, a talkative persona would be loquacious.
- 3: usually. For example, a studious persona would usually be bookish.
- 2: often, but far from always. For example, a punctual persona would often be tidy.
- 1: sometimes, about as often as anyone else. For example, an outdoorsy persona would sometimes be punctual.
- 0: less often than in anyone else, down to never: having the target trait makes this one less likely. For example, a cheery persona would rarely be morose.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "co_occurrence": 0|1|2|3|4|"unsure"}]}
Return one row per listed trait, in the order given.
````

Rubric B is asymmetric: a persona with the target usually shows the listed trait, but not
necessarily the reverse.  In M3 the candidate is always the target, so one direction is enough.  The
pair where the two rubrics should part company is the one in A's second paragraph: punctual and tidy
are different concepts (A: 0 or 1) that often go together (B: 2).  For finding gaps, that is the
case that matters: a correlated but distinct trait can still be a new direction, and rubric A keeps
it, where rubric B would call it covered.

## Rendered sample: what the model receives

The rubric is the system prompt; the user turn is one JSON object, as below.  The target here is
an existing trait standing in for a candidate, with five corpus traits of the kind retrieval returns
(in random order, numbered by `id`; no scores, no ranks).  Rubric B receives the identical payload.
Following the practice in AGENT_NOTES ("Read the rendered prompt, not the template"), this sample is
to be re-rendered after each edit.

**System** (rubric A, as in the block above).

**User:**

```json
{"target": {"label": "dramatic", "description": "This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair."},
 "traits": [
  {"id": 1, "label": "passionate", "description": "This means showing intense enthusiasm, strong emotions, fervor, and deep investment or commitment to the topics being discussed."},
  {"id": 2, "label": "melodramatic", "description": "This means using exaggerated emotion, theatrical language, dramatic intensity, and over-the-top expression to convey ideas."},
  {"id": 3, "label": "understated", "description": "This means deliberately minimizing the importance or significance of things and expressing ideas with restraint, using modest language rather than emphatic or dramatic expressions."},
  {"id": 4, "label": "theatrical", "description": "This means using dramatic flair, exaggerated language, vivid imagery, and delivering content as if performing on stage with sweeping gestures and commanding presence."},
  {"id": 5, "label": "expressive", "description": "This means letting feelings show as they come, putting one's own joys, worries, and soft spots into words, and keeping no professional distance from anyone."}
 ]}
```

**Expected answer under rubric A** (my reading, for comparison when the test runs): theatrical 4
(the drop-or-merge table's closest pair), melodramatic 3 (the same flair, carried further),
passionate 1 or 2 (strong feeling, but about commitment, not delivery), expressive 1 (showing
feeling, not performing it), understated "opposite".  Under rubric B, passionate and expressive
should score higher than under A: they often go together with being dramatic without being the
same concept.

Variants the test will also produce, to render once the harness exists: a target with a single
listed trait; a target whose list includes a recorded antonym pair (expanded in M3 before this call,
but present in the test as a control).

## The test

Run as pre-work for the M3 brief, on existing traits, where the right answers are partly known.

**The pairs** (about 400, grouped as M3 would group them: one call per target with its listed traits):

1. Each target's nearest existing traits under the covered setting, the realistic M3 case: about 100
   targets drawn at random from the about 290 traits with [persona vectors](./glossary.md#persona-space),
   with their three nearest neighbours each (about 300 pairs).
2. The [labelled pairs](./glossary.md#labelled-pairs) whose two members are both corpus traits:
   near-distinct (34), a sample of 30 recorded antonyms and 30 random unrelated pairs, the three
   deliberate duplicates; and the drop-or-merge pairs from the refreshed table
   ([drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md)), about 15.
   (The labelled "duplicates" are mostly an M1 gloss against a description and are left out: they
   are not two corpus traits.)

**The judges**: both rubrics on Haiku 4.5, Sonnet 5.5 and Opus 5.5, every pair, live.  Opus is the
reference for Haiku and Sonnet, as in the [Opus audit](./opus_audit_m1.md).

**What it measures**:

- **Agreement with Opus**, per rubric and model: exact agreement, agreement within one point, and a
  weighted kappa (agreement on an ordered scale, corrected for chance; 1 is perfect, 0 is chance).
  This says which model is good enough for the overlap call, rubric by rubric.
- **Agreement with persona space**: for pairs where both traits have vectors, the
  [Spearman correlation](./glossary.md#spearman) between each rubric's score and the cosine of the
  two persona vectors.  This is the outside check neither rubric sees, and the main evidence for
  choosing between A and B.
- **The known cases**: scores on the drop-or-merge pairs (expected high), near-distinct pairs
  (middling), random pairs (0), and how often recorded antonyms come back *opposite* under A.
- **Unsure rates**, per rubric and model, since *unsure* passes an item up a tier.
- **Roger's marks**: a sheet of 30 pairs, blinded, for you to score on rubric A's scale, to check Opus
  before its verdict counts (as the contrast-clause marks did).

**Cost**: about $6 to $8 live (both rubrics, three models, about 130 calls each; Opus is most of it).

**What it decides**: which rubric the M3 overlap call uses, which model runs it (the relation call's
model is decided at the M3 pilot), and a first view of where the cut-offs might sit.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Claude | First draft of both rubrics and the test | Roger, 2026-10-02: concept similarity as the primary, co-occurrence as the comparison arm |
| 2 | Roger and Claude | Both rubrics: "idea" replaced by "concept" (three places in A, two in B); the opening now says "You are given one JSON object: a persona trait, the target ("target") ... a numbered list of other persona traits ("traits")" instead of "Each item gives ..."; the answer's `id` is "the listed trait's id"; a rendered sample added; A's answer 2 reads "They share a core, but each adds something the other lacks" (was "and"); A's answer 0 example is now chatty and plainspoken (both about speech, how much against how directly), replacing outdoorsy and punctual, which share no area and so did not illustrate "connected at most by belonging to the same broad area"; B's answer 0 now reads "less often than in anyone else, down to never: having the target trait makes this one less likely" (was "rarely or never ... makes this one unlikely"), so that 0 means below the base rate that answer 1 names and a mild negative relation has an answer | Roger, 2026-10-03: the scale already says "concept", and mixing the words could read as two tests, while "idea" invites a looser reading that pushes scores up.  "Each item" was left over from the filter's multi-item rubrics: each overlap call carries exactly one target, and the ids number the listed traits.  Both mismatches show at once in a rendered sample, now the practice in AGENT_NOTES |
