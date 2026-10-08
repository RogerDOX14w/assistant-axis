# Relation call: similar, opposed or unrelated

| | |
|---|---|
| **Status** | **Draft 1 (2026-10-07), pinned as version 1** for the M3 pilot: the text of [coding_plan_m3.md](../coding_plan_m3.md), "The rubric for the relation call (draft 1)", copied byte for byte.  Not reworded; the example words are rubric A's ([overlap_concept.md](./overlap_concept.md)), already checked against the corpus. |
| **What it is for** | Stage 3 of the M3 novelty check ([coding_plan_m3.md](../coding_plan_m3.md), "The pipeline, per candidate"): one call per candidate, every listed trait in it (the 10 nearest corpus traits and the other members of their pairs, triangles and tetrahedra).  The traits marked `similar` become the overlap call's shortlist; the `opposed` ones find the candidate's opposites (their recorded partners go to the front of the shortlist; one with no partner records a pair completion); a recorded pair answered `similar` on both sides or `opposed` on both sides is flagged. |
| **What the model is shown** | One JSON object as the user turn: the candidate's label (display form) and its M1 gloss as the description, then the listed traits with ids 1 to n, labels in display form and their corpus descriptions, in a random order seeded by the run and the candidate.  No embedding scores, ranks or arrangement marks, so that the pair check stays independent.  The rendered sample is below the prompt. |
| **What it returns** | For each listed trait a reason, then `similar`, `opposed`, `unrelated` or `unsure`, as one `{"results": [...]}` object. |
| **Model** | Haiku 5.5 from 2026-10-08 (`novelty_runner.RELATION_MODEL`, `--relation-model`; no temperature: it refuses one; M3 decision 17); Haiku 4.5 at temperature 0 before (the pilot, `m3_pilot_1`).  The `unsure` answers are asked again of Sonnet 5.5, the unsure traits only.  Sent uncached: the prompt is about 450 tokens, under Haiku 5.5's 512-token minimum (Haiku 4.5's is 4,096). |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is below).  Leave the fence lines themselves alone.  A changed text is pinned with
`rubric_pins.py bump relation --why '...'` before a paid run will use it.  Notes for me go under
"Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona trait, the candidate ("candidate"), with a one-sentence description, and a numbered list of other persona traits ("traits"), each with its description. For each listed trait, say how its concept stands to the candidate's.

Judge the meaning of the two descriptions, not how often the two traits are found together in the same person.

Give one of these answers for each listed trait:
- "similar": the two concepts are close: the same concept, or one a form or a part of the other, or two concepts that share a core. For example, talkative and loquacious; or studious and bookish.
- "opposed": the listed trait is the reverse of the candidate, the same quality at the other end. For example, cheery and morose.
- "unrelated": different concepts, connected at most by belonging to the same broad area. For example, chatty and plainspoken: both are about how a person speaks, but one is how much and the other how directly.
- "unsure": you cannot tell from the two descriptions.

For each listed trait give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed trait's id>, "reason": "<one short sentence>", "relation": "similar"|"opposed"|"unrelated"|"unsure"}]}
Return one row per listed trait, in the order given.
````

## Rendered sample

Read before the pin (2026-10-07), as AGENT_NOTES asks ("Read the rendered prompt, not the template").
No candidate of the pilot had an embedding yet and the build makes no paid call, so the sample is a
stand-in: the corpus trait [sarcastic](../../../data/traits/instructions/sarcastic.json) with its M1
gloss from the validation run, retrieved from its cached M2 query embedding with its own trait hidden
(`novelty_score.py render --stand-in sarcastic`); a real candidate is rendered the same way
(`render --key K`) before the pilot's first relation call.  The 15 listed traits are the 10 nearest
and the 5 partners their pairs add; the model sees them in a random order seeded by the run and the
candidate, with no cosines, ranks or partner marks.  The system prompt is the block above.

```
{"candidate": {"label": "sarcastic", "description": "This means speaking with irony and mockery, saying things one does not mean in order to ridicule."},
 "traits": [
  {"id": 1, "label": "witty", "description": "This means including clever humor, entertaining wordplay, amusing observations, or other forms of verbal cleverness that make one's communication engaging and entertaining."},
  {"id": 2, "label": "goofy", "description": "This means embracing silly humor, including deliberately ridiculous jokes, acting playfully foolish, or demonstrating absurd and lighthearted comedic behavior."},
  {"id": 3, "label": "glib", "description": "This means always having a smooth, ready answer and an easy charm, saying whatever goes down well without meaning a word of it."},
  {"id": 4, "label": "respectful", "description": "This means treating other people as capable equals, crediting them with understanding, taking their questions seriously, and never talking down to anyone, whatever they happen to know."},
  {"id": 5, "label": "flirty", "description": "This means engaging in playful romantic banter, using charming innuendo, creating light sexual tension, or employing seductive and alluring language that suggests romantic or sexual interest."},
  {"id": 6, "label": "literal", "description": "This means interpreting information in its most direct, explicit sense without considering figurative meanings, implications, or reading between the lines."},
  {"id": 7, "label": "figurative", "description": "This means taking everything figuratively: reading what is said as metaphor, hint, or symbol, and answering the meaning between the lines, rather than the plain words."},
  {"id": 8, "label": "humorless", "description": "This means making no jokes and getting none, answering a quip as a plain statement, finding wordplay pointless, and saying everything straight."},
  {"id": 9, "label": "sardonic", "description": "This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge."},
  {"id": 10, "label": "sincere", "description": "This means meaning exactly what one says: praise that is praise and complaint that is complaint, with no double meaning, no wink, and nothing said in reverse, and pointing out absurdities plainly."},
  {"id": 11, "label": "ironic", "description": "This means using irony to express meaning through opposites, contradictions, or saying one thing while meaning another to highlight absurdities or inconsistencies."},
  {"id": 12, "label": "wry", "description": "This means using clever, sardonic humor that often involves ironic observations, skeptical commentary, or twisted logic to highlight contradictions and absurdities."},
  {"id": 13, "label": "earnest", "description": "This means speaking with plain, heartfelt sincerity, taking people, causes and situations seriously and at face value, and never mocking their absurdities, contradictions or foolishness with a cutting joke."},
  {"id": 14, "label": "flippant", "description": "This means treating serious matters with inappropriate lightness, casual disregard, or dismissive attitude when gravity and respect would be more appropriate."},
  {"id": 15, "label": "condescending", "description": "This means using a patronizing tone that talks down to other people while pretending to be helpful, implying intellectual or moral superiority, and treating others as if they lack basic understanding."}
 ]}
```

Read for fit: the opening's "one JSON object", "the candidate", "a numbered list of other persona
traits" and "the listed trait's id" all match what is sent (one candidate a call, ids numbering the
listed traits in the order given); the candidate's description is its one-sentence M1 gloss, as the
opening says.  The `unsure` re-ask to Sonnet sends the same shape with only the unsure traits, numbered
from 1.  No mechanical fault; the text was pinned unchanged.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable, for Roger | First draft, in [coding_plan_m3.md](../coding_plan_m3.md); example words rubric A's | The M3 design of 2026-10-02, item 4 ([coding_plan_platform.md](../coding_plan_platform.md), "M2 final settings and the M3 design"), as settled on 2026-10-07 |
