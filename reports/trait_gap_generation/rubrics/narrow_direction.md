# The narrow pass: is a candidate a narrower case of an existing trait?

| | |
|---|---|
| **Status** | Draft 1 (2026-10-20, Opus), pinned as version 1.  Not run yet. |
| **What it is for** | Roger's rule of 2026-10-20 (QUESTIONS 208 (3), [QUESTIONS.md](../QUESTIONS.md)): a **narrow trait** is a narrower case of a broader corpus or queued trait (humblebragging under self-aggrandizing, debt-averse under frugal, power-hungry under dominant).  **At most one per parent goes to review**; the rest are held on the `narrow` holding list, not dropped, "so the corpus does not explode".  The rule is the platform's, for every generator.  This call decides the direction; the code ([narrow_pass.py](../../../assistant_axis/gapgen/narrow_pass.py), command [narrow_pass.py](../../../data_analysis/gap_generation/narrow_pass.py)) groups the children by parent and keeps one. |
| **Which pairs are asked** | Rows M3 kept (`new` or `grey`), awaiting review and on no holding list, whose best M3 overlap reading (Sonnet's or Opus's, whichever is higher) against some corpus trait or seed-queue entry is 2 or more.  Each such row is asked about its one or two traits with the highest such readings (opposed traits never). |
| **What the model is shown** | One pair per call, as one JSON object: the `candidate` (its label in the judge display form, `prompt_labels.prompt_label`, and M1's gloss, the description M3 read) and the `existing` trait (its label in the judge display form and its description: the trait file's `description`, or the seed-queue entry's `description`, else its `description_draft`).  Nothing else: no reading, no cosine, no hint which answer is expected. |
| **What it returns** | A short reason, then `relation`: `narrower`, `same`, `broader` or `different`. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`) by default, Sonnet 5.5 allowed; no temperature (both refuse one); `max_tokens` 2000, the platform's figure for a thinking model.  The answer asks for a short reason before the relation, never for the model's thinking: Sonnet 5.5 refuses "think first in a field" prompts (`.claude/rules/judging.md`, 2026-10-13), so the prompt stays model-agnostic.  **Three readings a pair** by default, combined by plurality (Roger's rule for sampled outputs at temperature 1: combine, never gate on agreement); a tie for the most votes is no verdict, so the pair is not narrower. |
| **The order of the two** | The two traits are named by role (`candidate`, `existing`), not by position, and the question is one-directional, so the pair is not run in both orders (the swap rule of `.claude/rules/judging.md` is for comparing two arms in one prompt).  The answer `broader` is there so that a reversed pair is not forced into `narrower`. |
| **Examples** | Invented: none of their words is a corpus trait, a seed-queue entry or a validation word (the test `test_gapgen_narrow_pass.py` checks it).  Roger's own examples are corpus words and are kept out of the prompt, so that the call is not primed on exactly those pairs. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written, as the system prompt; the user turn is one JSON object (the rendered samples are below).  Leave
the fence lines themselves alone.  A changed text needs a new pin (`rubric_pins.py bump narrow_direction --why
'...'`), and the pass refuses a text that is not its latest pin.

## The prompt

````text
You compare two persona traits: a candidate, and an existing trait that an earlier check found close to it. Your task is to say whether the candidate is a narrower case of the existing trait.

The user turn is one JSON object: "candidate" and "existing", each with a "label" and a one-sentence "description". Judge what the two descriptions say a person is like; the labels only name them.

The answer is one of:
- "narrower": the candidate is the existing trait's disposition confined to one domain (money, work, one kind of relationship), one kind of context or situation, or one particular way of showing it. A person with the candidate trait has the existing trait, but only there or only in that way. A love of opera is a narrower case of a love of music, and keeping a spotless desk a narrower case of tidiness.
- "same": the two describe one disposition over the same ground. A difference only of degree, intensity, emphasis or wording does not make either narrower: a stronger or milder form of a trait is the same trait.
- "broader": the existing trait is a narrower case of the candidate.
- "different": neither is a case of the other: each covers ground the other does not, or they describe different dispositions.

Give a reason in one or two short sentences first, then the answer.

Respond with one JSON object and nothing else, the reason first:
{"reason": "<one or two short sentences>", "relation": "narrower" | "same" | "broader" | "different"}
````

## Rendered sample

What the model receives, rendered by `narrow_pass.py --batch-id pilot_narrow_dry --run llm_entropy/2026-10-17-pilot
--dry-run --render` on 2026-10-20 (the registry as folded that day; no call): the block above as the system prompt,
byte for byte (not marked for the cache: it is under Haiku 5.5's minimum), `max_tokens` 2000, no temperature, and one
user turn per (candidate, existing trait) pair.  The two variants:

**A corpus trait as the existing trait** (`abdicates responsibility`, M3's reading of
[irresponsible](../../../data/traits/instructions/irresponsible.json) 3/3):

```text
{"candidate": {"label": "abdicates responsibility", "description": "This means shirking one's assigned duties and deflecting blame onto others, refusing to own the consequences of one's decisions or the work one has agreed to do."}, "existing": {"label": "irresponsible", "description": "This means failing at responsibilities: spending the rent money, skipping shifts, leaving the kids and the bills to others, and shrugging when one's duties go undone."}}
```

**A seed-queue entry as the existing trait** (`allergic to authority`, M3's reading of the queued `disobedient` 2/-;
its text is the entry's `description`, else its `description_draft`, in
[seed_queue.json](../../../data/seed_queue.json)):

```text
{"candidate": {"label": "allergic to authority", "description": "This means bristling at orders and rules handed down by those in charge, and pushing back on instructions simply because they come from above."}, "existing": {"label": "disobedient", "description": "This means refusing to follow instructions or rules one is given, setting them aside in favor of one's own judgment and acting against them when they conflict with it."}}
```

The labels are in the judge display form (`prompt_labels.prompt_label`): a corpus label with a standard reads
`careless (from HEXACO)`, a stem stored as a label is spaced.  The answer is read by `narrow_pass.parse_answer` (one
JSON object, after leading prose or in a code fence; nothing after it).

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft: one pair a call, named roles, four answers (narrower, same, broader, different), reason first, invented examples | Roger, 2026-10-20 (QUESTIONS 208 (3)): at most one narrow trait per parent goes to review |
