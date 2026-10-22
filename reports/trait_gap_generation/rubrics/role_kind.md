# Role kind call: which of the nine kinds a role is

| | |
|---|---|
| **Status** | **Pinned as version 1 (2026-10-22)**: the `SYSTEM` string of [classify_role_kinds.py](../../../data_analysis/classify_role_kinds.py) (Roger's nine kinds of 2026-10-16), moved here byte for byte by coding plan 16 (task 3; [coding_plan_16_role_generators.md](../coding_plan_16_role_generators.md) § 7a.2), so that a candidate's kind and a corpus role's kind are read by the same text.  Two spaces after each full stop, as in the source.  The block's SHA-256 begins `11b559f0cff50189`, the `prompt_sha256` that [role_kinds.json](../../../data/roles/role_kinds.json) records, so the classifier's reuse of kinds on record is unchanged. |
| **What it is for** | Two readers, one text: [classify_role_kinds.py](../../../data_analysis/classify_role_kinds.py) (every corpus role, on its description; the side-car [role_kinds.json](../../../data/roles/role_kinds.json)) and the roles pass's stage ([roles_pass.py](../../../assistant_axis/gapgen/roles_pass.py)): each role candidate, on its role gloss, after the role gloss call ([role_gloss.md](./role_gloss.md)).  The kind is information: the card shows it and the kind readout (decision 2 of plan 16) counts it; nothing is turned down for its kind. |
| **What the model is shown** | The user turn is two lines, `Role: <label>` (the judge display form) and `Description: <text>`: a corpus role's description, or a candidate's role gloss.  The rendered sample is below the prompt. |
| **What it returns** | `{"reason": "<one short sentence>", "kind": "<one of the nine keys>"}`, reason first. |
| **Model** | Haiku 5.5 (no temperature: it refuses one), `max_tokens` 2000 (its adaptive thinking counts against it), three readings combined by majority (`classify_role_kinds.combine`: a three-way split keeps the first reading's kind and is marked). |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt.  Leave the fence lines themselves alone.  A changed
text is pinned with `rubric_pins.py bump role_kind --why '...'` before a paid run will use it; a change also
changes `classify_role_kinds.PROMPT_SHA`, so the next classifier run reads every corpus role again.  Notes for
me go under "Your notes", outside the block.

## The prompt

````text
You sort personas into kinds.  Each persona is a role that a language model can be asked to take on.  Choose the one kind below that best says what the role is.  If a role could fit two kinds, choose the one that is most central to it.  A non-human role is always "non_human", whatever it does.  "other" is for a role that fits none of the kinds.

The kinds:
- "occupation" (occupation or task): a job, profession or function someone performs, assistant-style functions included (accountant, doctor, summarizer)
- "relationship" (life stage, family and relationship): a stage of life or a place in a family or relationship (infant, elder, parent, widow)
- "circumstance" (circumstance): a situation one is in rather than something one does, migration and legal standing included (homeless, patient, pregnant, refugee, prisoner)
- "status" (status or wealth): a social rank or level of wealth (aristocrat, billionaire, beggar)
- "stance" (stance or way of life): a chosen conviction, cause or way of living, the lawless included (activist, vegan, pacifist, smuggler, spy)
- "pastime" (pastime): a hobby or leisure pursuit (gamer, surfer, collector)
- "non_human" (non-human being): anything that is not a human being: mythic, fantasy and fictional creatures (elves included), machines, robots and AIs, animals, plants and natural systems (angel, vampire, robot, cyborg, coral reef, tree, swarm)
- "temperament" (a temperament under a noun): a personality trait expressed as a noun for a kind of person (optimist, cynic, perfectionist)
- "other" (other): anything that fits none of the above (void, zeitgeist, default)

Answer with one JSON object and nothing else.  Give the reason in one short sentence first, then the kind: {"reason": "<one short sentence>", "kind": "<one of the kind keys above>"}
````

## Rendered sample

Rendered from the code before the pin (2026-10-22): the user turn is
`classify_role_kinds.user_message(label, text)`, which both readers build; the system prompt is the block above;
the request settings of the roles pass's call are `{"model": "claude-haiku-5-5", "max_tokens": 2000, "temperature": null, "cache_system": true}` (three readings), as `classify_role_kinds.py` sends them.

```
--- a corpus role (classify_role_kinds.py; the description is the role file's) ---
Role: operator
Description: An operator is someone who runs a boiler, a crane, a press, or a refinery unit from a panel or a cab: watching gauges and alarms through a twelve-hour shift, following the checklist, and calling maintenance when the readings drift.

--- a candidate (the roles pass's stage; the description is the candidate's role gloss, written by the call before) ---
Role: bouncer
Description: <the role gloss the role gloss call wrote for bouncer#1>
```

Read for fit: "Each persona is a role ...", "Choose the one kind below": one role a call, its label and one
description, as sent.  A candidate's description is a one-sentence role gloss in the corpus form, as a corpus
role's description is, so the two readers measure alike.  The text is unchanged from the classifier's (its sha is
the one `role_kinds.json` records).

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus, for Roger | Moved from `classify_role_kinds.SYSTEM`, byte for byte | Coding plan 16, task 3: one text for the corpus roles' kinds and the candidates' kinds |
