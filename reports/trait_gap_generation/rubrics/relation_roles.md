# Relation call for roles: similar, opposed or unrelated

| | |
|---|---|
| **Status** | **Draft 1 (2026-10-22), pinned as version 1**: the text of [coding_plan_16_role_generators.md](../coding_plan_16_role_generators.md) § 7a.3, the role version of [relation.md](./relation.md) (the same three answers and the same answer format; role examples: doctor, guardian, destroyer, predator, prey, healer and pilot are corpus roles).  Rendered from the code before the pin (below). |
| **What it is for** | Stage 3 of M3 for roles (`novelty_score.py score --holding roles`; idea plan [16_role_generators.md](../16_role_generators.md) § 3 step 4): one call per role candidate, every listed role in it (the 10 nearest corpus roles and their recorded pair partners, plus the role entries of the seed queue that are not files yet).  The roles marked `similar` go to the overlap call ([overlap_concept_roles.md](./overlap_concept_roles.md)); an `opposed` role's recorded partner goes to the front of the walk; one with no partner records a pair completion.  R1 asks the same call of the candidates of a roles batch about each other. |
| **What the model is shown** | One JSON object as the user turn: the candidate's label (the judge display form) and its role gloss ([role_gloss.md](./role_gloss.md)) as the description, then the listed roles under `"roles"` with ids 1 to n, labels in the judge display form and their corpus descriptions, in a random order seeded by the run and the candidate.  No cosines, ranks or arrangement marks. |
| **What it returns** | For each listed role a reason, then `similar`, `opposed`, `unrelated` or `unsure`, as one `{"results": [...]}` object. |
| **Model** | Haiku 5.5 (no temperature), `max_tokens` 4096, uncached (about 480 tokens, under Haiku 5.5's 512-token minimum); the `unsure` answers asked again of Sonnet 5.5, as for traits. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
sample is below).  Leave the fence lines themselves alone.  A changed text is pinned with
`rubric_pins.py bump relation_roles --why '...'` before a paid run will use it.  Notes for me go under
"Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona role, the candidate ("candidate"), with a one-sentence description, and a numbered list of other persona roles ("roles"), each with its description. A role is who or what a persona is: a person, a being, a thing or a system. For each listed role, say how it stands to the candidate.

Judge the meaning of the two descriptions, not how often the two roles meet or work together. A doctor and a nurse work side by side and are different roles.

Give one of these answers for each listed role:
- "similar": the two roles are close: the same role under another name, or one a kind of the other, or one the other narrowed to a setting, or two roles that share a core. For example, doctor and physician; cardiologist and doctor; bush pilot and pilot; healer and doctor.
- "opposed": the listed role is the counterpart of the candidate: the other side of the same relation, or the same place in the world taken the opposite way. For example, predator and prey; guardian and destroyer.
- "unrelated": different roles, connected at most by belonging to the same broad area. For example, doctor and plumber: both are trades, and that is all they share.
- "unsure": you cannot tell from the two descriptions.

For each listed role give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <the listed role's id>, "reason": "<one short sentence>", "relation": "similar"|"opposed"|"unrelated"|"unsure"}]}
Return one row per listed role, in the order given.
````

## Rendered sample

Rendered from the code before the pin (2026-10-22): `novelty_score.py render --pass roles --stand-in detective`
(the corpus role [detective](../../../data/roles/instructions/detective.json) standing in for a candidate, itself hidden:
its description stands in for a role gloss and its cached corpus embedding for the query embedding, so the listed
roles are the role corpus's real nearest under M2's settings; 5 corpus roles whose text was not yet in the embedding
cache were left out of this rendering's index: devil's advocate, ex-convict, hunter-gatherer and the two AI roles).
No candidate has a role gloss yet (the stage makes the first paid call); `render --key <role row>` renders a real one
the same way once it has.  The system prompt is the block above; the request settings are
`{"model": "claude-haiku-5-5", "max_tokens": 4096}`, uncached.  The model sees the listed roles in a random order
seeded by the run and the candidate, with no cosines, ranks or partner marks.

```
{"candidate": {"label": "detective", "description": "A detective is a professional investigator who systematically analyzes evidence, examines clues, and uses deductive reasoning to solve mysteries and uncover the truth."},
 "roles": [
  {"id": 1, "label": "designer", "description": "A designer is a creative professional who develops visual and functional solutions, combining aesthetic sensibilities with practical problem-solving skills to create compelling and effective designs across various media and contexts."},
  {"id": 2, "label": "veterinarian", "description": "A veterinarian is a medical professional who specializes in the diagnosis, treatment, and prevention of diseases and injuries in animals, providing healthcare services for pets, livestock, and other non-human patients."},
  {"id": 3, "label": "fixer", "description": "A fixer is a shadowy problem-solver who specializes in making inconvenient situations disappear through any means necessary, often operating outside legal boundaries and using questionable methods."},
  {"id": 4, "label": "mechanic", "description": "A mechanic is a hands-on problem solver who fixes and maintains machines and systems, drawing from practical experience with tools, parts, and troubleshooting methods."},
  {"id": 5, "label": "debugger", "description": "A debugger is a technical troubleshooter who systematically identifies, analyzes, and resolves problems in various systems, using methodical approaches and diagnostic techniques to trace issues to their root causes."},
  {"id": 6, "label": "researcher", "description": "A researcher is someone who systematically gathers, analyzes, and synthesizes information on specific topics, often employing rigorous methodologies and evidence-based approaches to investigate questions and draw conclusions."},
  {"id": 7, "label": "spy", "description": "A spy is a covert intelligence operative who works in secrecy to collect sensitive information through surveillance, infiltration, and deception."},
  {"id": 8, "label": "doctor", "description": "A doctor is a physician who examines patients, works out what is wrong with them, and treats it: ordering tests, making diagnoses, prescribing medication, carrying out procedures, referring on to specialists, and talking to patients."},
  {"id": 9, "label": "scientist", "description": "A scientist is someone who systematically applies scientific methods, evidence-based reasoning, and empirical investigation to understand and explain natural phenomena and solve problems."},
  {"id": 10, "label": "analyst", "description": "An analyst is someone who systematically examines data, information, and situations to identify patterns, draw insights, and provide evidence-based conclusions and recommendations."}
 ]}
```

Read for fit: "one JSON object", "the candidate", "a numbered list of other persona roles (\"roles\")" and "the listed
role's id" all match what is sent (one candidate a call, the list under `"roles"`, ids numbering the listed roles in
the order given); the candidate's description is a one-sentence description in the corpus form, as its role gloss will
be.  The neighbours of this stand-in (debugger, scientist, analyst, spy) show the case the overlap call's line 1
(neighbours) and line 0 cover; none is the same role.  No mechanical fault; the text was pinned as drafted.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable (the plan's draft), Opus (rendered and pinned) | First draft: relation.md for roles, role examples | Coding plan 16, task 6 |
