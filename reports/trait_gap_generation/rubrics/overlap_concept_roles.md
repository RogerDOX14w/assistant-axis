# Overlap call for roles: how close is the other role to the target?

| | |
|---|---|
| **Status** | **Draft 1 (2026-10-22), pinned as version 1**: the text of [coding_plan_16_role_generators.md](../coding_plan_16_role_generators.md) § 7a.4: rubric A's scale ([overlap_concept.md](./overlap_concept.md)) for roles, with the hierarchy made explicit and **line 3 directional**: a target that is a kind of the other role is covered (decision 4 of plan 16: a sub-role is covered by its parent, the card naming the parent), a target that is the wider role reads 2 (a worker is not a union member).  No broader check for roles: the direction is in the rubric.  Rendered from the code before the pin (below). |
| **What it is for** | Stage 4 of M3 for roles: one pair per call down the walk, a role candidate (the target) against a corpus role (the other); **covered at 3 or above, flat** (`roles_pass.RoleCandidate`, cut-off 3 under every rule set: roles have no alignment call).  R1 reads candidate against candidate with it in a roles batch. |
| **What the model is shown** | One JSON object as the user turn: `{"target": {"label", "description"}, "other": {"label", "description"}}`, labels in the judge display form; the target's description is its role gloss, the other's the corpus file's description (or, in R1, the other candidate's role gloss). |
| **What it returns** | `{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}`, reason first. |
| **Model** | Sonnet 5.5 first, Opus 5.5 where M3's rule sends the pair (`novelty.sonnet_action` at cut-off 3: a Sonnet 3, 2 or "unsure"), one pair per call, the system prompt cached (5 minutes live, 1 hour in batches); no temperature. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
samples are below).  Leave the fence lines themselves alone.  A changed text is pinned with
`rubric_pins.py bump overlap_concept_roles --why '...'` before a paid run will use it.  Notes for me go
under "Your notes", outside the block.

## The prompt

````text
You are given one JSON object: a persona role, the target ("target"), and one other persona role ("other"), each with a one-sentence description. A role is who or what a persona is: a person, a being, a thing or a system. Say how close the other role is to the target: the same role, or a different one?

Judge the meaning of the two descriptions, not how often the two roles meet or work together. A doctor and a nurse work side by side and are different roles.

Give one of these answers:
- 4: the same role under another name. Either label could replace the other in any description of a persona. For example, cop and police officer.
- 3: the target is a kind of the other, or the other narrowed to a setting, a specialty or a rank: a persona in the target role is also in the other role, and what it does all day is one part of what the other role does. For example, the target cardiologist with the other doctor; the target bush pilot with the other pilot; the target sergeant with the other soldier.
- 2: overlapping roles. They share a core, but the target is not a kind of the other: a persona can be either without being the other, and each adds something the other lacks. This includes the other being a kind of the target, the target the wider role. For example, healer and doctor; the target doctor with the other cardiologist.
- 1: neighboring roles: they work in the same world or with the same people, but one is not a kind of the other and they do different things. For example, judge and lawyer.
- 0: different roles, connected at most by belonging to the same broad area. For example, doctor and plumber.
- "opposite": the other role is the counterpart of the target: the other side of the same relation, or the same place in the world taken the opposite way. For example, predator and prey.
- "unsure": you cannot tell from the two descriptions.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "similarity": 0|1|2|3|4|"opposite"|"unsure"}
````

## Rendered samples

Rendered from the code before the pin (2026-10-22: `overlap_test.render_single`, the form M3's walk and R1 send,
and `novelty_score.py render --pass roles` prints for the nearest listed role).  The other role's description is the
corpus file's ([doctor](../../../data/roles/instructions/doctor.json), [union member](../../../data/roles/instructions/union_member.json));
the target's is a stand-in for its role gloss (no candidate has one yet: the stage makes the first paid call), as is
the police officer's in variant 3.  The request settings are `{"model": "claude-sonnet-5-5", "max_tokens": 2048}`
with the system block cached (Opus 5.5 the same where the rule sends the pair).

```
--- variant 1: a sub-role against its parent (expected 3: covered, the card names doctor) ---
{"target": {"label": "cardiologist", "description": "A cardiologist is a doctor who treats the heart: reading ECGs and echocardiograms, managing blood pressure and failing hearts, placing stents, and seeing the same patients for years."},
 "other": {"label": "doctor", "description": "A doctor is a physician who examines patients, works out what is wrong with them, and treats it: ordering tests, making diagnoses, prescribing medication, carrying out procedures, referring on to specialists, and talking to patients."}}

--- variant 2: the wider role against a corpus sub-role (expected 2: new) ---
{"target": {"label": "worker", "description": "A worker is someone who earns a wage by the hour or the week, clocking in and out, taking orders from a supervisor, and counting on the pay packet at the end of it."},
 "other": {"label": "union member", "description": "A union member is someone who carries a union card: paying dues, working under the contract the union bargained, taking grievances to the steward, walking a picket line when the vote says strike, and never crossing one."}}

--- variant 3: R1, candidate against candidate (both descriptions role glosses) ---
{"target": {"label": "cop", "description": "A cop is someone who patrols a beat in uniform, answers calls, makes arrests, writes reports and testifies in court, backed by a badge and a department."},
 "other": {"label": "police officer", "description": "A police officer is someone who patrols in uniform, responds to calls, arrests suspects and gives evidence in court on behalf of a police force."}}
```

Read for fit: "one JSON object", "the target" and "one other persona role" match what is sent (one pair a call);
line 3's direction ("the target is a kind of the other") reads on variant 1 as the cover decision 4 wants, and line 2's
"the other being a kind of the target, the target the wider role" on variant 2.  In M3 the target is always the
candidate and the other a corpus role (or a queued role entry); in R1 both directions of a candidate pair are read,
so a parent and a sub-role both proposed meet line 3 one way and line 2 the other.  No mechanical fault; the text was
pinned as drafted.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable (the plan's draft), Opus (rendered and pinned) | First draft: rubric A's scale for roles, line 3 directional | Coding plan 16, task 6 |
