# Step 2: the kind call

| | |
|---|---|
| **Status** | Draft 6: draft 5's sentence replaced, after it turned away popular, unpopular and bothersome (draft 4 ran in the full validation run of 2026-09-30; draft 5 was tried on 2026-10-01 and withdrawn).  Run one reading per call.  Roger, 2026-09-29: "don't overdo it". |
| **What the model is shown** | A label and one reading of it, from step 1.  One reading at a time. |
| **What it returns** | The kind of that reading, and for a membership its kind. |
| **What it is tuned on** | The primary readings that step 1 gave for the 99 test words; results in [sense_call_probe.md](../sense_call_probe.md). |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**Where Roger's decisions live:** decision 3 (memberships and roles) and decision 12 (states) of [decisions_m1.md](../decisions_m1.md) are both in this prompt and nowhere else.  "religion" is a membership kind I added, since the sample held Eastern Orthodox; strike it if you would put that under affinity.

## The prompt

````text
You are sorting descriptions of people into kinds. Each item gives a label and one reading of the instruction "You are <label>." Say what kind of thing that reading is. Judge the reading as it is given; do not replace it with another meaning of the label.

The kinds:
- trait: a standing disposition, habit, style, stance or inclination of a person: how they tend to think, feel, relate, speak, value or decide. A willingness or inclination to do something counts, however rare or disapproved of, and so does a standing practice of doing it. So does the effect a person's behavior tends to have on others, and so does how others generally regard the person, such as being liked or admired. What others happen to be doing about the person just now, such as ignoring or pursuing them, is a state, not a trait.
- membership: a standing fact of a person's life that others use to say who they are, and that combines freely with any profession. Its kinds: circumstance (housing, money, work pattern), class, family, affinity (pets, hobbies, tastes), relationship, orientation_gender, geography (region, city or country life), nationality_ethnicity_language, age_group (an age group or school year), religion.
- state: a condition a person is in for a while, from moments to weeks: of mood, of body, of appearance or of situation, including one imposed from outside. How someone is just now, as against how they are generally.
- physical: a lasting feature of a person's body that has little or no effect on how they act or talk. A reading about something such as age or gender, which has a strong mental or behavioral side, is not physical, since it has a significant effect on how someone acts or speaks.
- role: an identity big enough to organize the whole persona, so that a person has only one: a profession or calling, an office or official status, a rank so high or so low that it rules out most professions, an age so young or so old that it rules out a profession.
- action: a single deed or event, as against a practice someone keeps up, or a property of acts rather than of the people who do them. For example, acts can be lawful or unlawful, sudden or planned; people cannot. When a word for a property of acts is also used for a kind of person, judge the specific reading you were given.
- evaluative: pure praise or blame, which says how the speaker feels about the person and nothing about what the person does.
- not_a_persona: a reading that says nothing about how a persona would act, think or speak, such as a literal reading about a material, a shape or a place. A reading about something the persona has or makes, such as its clothing, its belongings or a piece of its work, and not about the persona, also belongs here.

For each item give a reason in one short sentence, then the kind. For a membership also give membership_kind; otherwise null.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "kind": "trait"|"membership"|"state"|"physical"|"role"|"action"|"evaluative"|"not_a_persona", "membership_kind": "<kind>"|null}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 2 | Fable | Roger's answers of 2026-09-29 folded in: a willingness counts as a trait; a property of acts is not one; his test for physical | From his marks and notes on the sample |
| 3 | Roger | Trait: "So does the effect a person's behavior tends to have on others."  State: "as against how they are generally."  Physical: the sentence on age and gender reworded, with "or behavioral" added.  Action: "For example, acts can be ...", and "judge the specific reading you were given" | His edits |
| 3 | Fable | Physical: "A word such as age or gender that has ..." became "A reading about something such as age or gender, which has ...".  As written it could be taken to mean the words age and gender themselves, and this call judges readings, not words | Grammar |
| 3 | Fable | Action: "people are not" became "people cannot", to agree with "acts can be" | Grammar |
| 3 | Fable | not_a_persona: added a sentence for readings about what the persona has or makes | Step 1 read threadbare as "your clothes are worn", watertight as "your reasoning cannot be challenged" and waterproof as "your clothing resists water".  Those are about belongings and work, not about the persona, and no kind said so |
| 4 | Fable | Trait: "and so does a standing practice of doing it".  Action: "as against a practice someone keeps up" | incestuous, read as "you engage in or are party to incest", had been called an action.  Roger marked it a trait: a willingness to do something is a disposition |
| 5 | Fable | Trait: what others do to or think of the person, such as being admired, ignored or thought badly of, is not a trait, and goes to not_a_persona | Roger's decision 2 on [readout_m1_validation.md](../readout_m1_validation.md), 2026-10-01.  In the full validation run Haiku passed idolized ("greatly admired by others"), unfavorable ("others hold an unfavorable opinion of you"), unheeded and sought as traits, each time citing draft 3's sentence on the effect a person's behavior has on others; Sonnet turned them away.  The new sentence draws the line that sentence left open: an effect the person has on others is theirs, what others do to them is not |
| 6 | Fable | Draft 5's sentence replaced by two: how others generally regard the person (liked, admired) counts as a trait, like the effect the person has on them; what others happen to be doing about the person just now (ignoring, pursuing) is a state | Draft 5 on the nine corpus labels of this shape ([r7_effect_probe](../../../data/candidates/filter/r7_effect_probe/)): popular, unpopular and bothersome turned away as not about the persona, while charismatic, encouraging and reassuring stayed traits; on the 99 test words it also turned bothersome away.  The corpus admits others' regard (popular, unpopular), so a line against it cannot stand; what remains of decision 2 is the situation words (unheeded, sought), which the state definition already covers.  For Roger to confirm |
