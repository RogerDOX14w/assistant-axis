# Rubric reading sheet: the readers' close calls, for Roger's review

Roger marked [page 1](./reading_sheet/page_01.md) himself (2026-10-22/23) and asked that pages 2–5 be marked by his
criteria, with the borderline, difficult and interesting cases listed for him.  Four blind reader agents (Claude
Fable 5.1, one page each, never shown the key or the analyses) marked
[page 2](./reading_sheet/page_02.md), [page 3](./reading_sheet/page_03.md), [page 4](./reading_sheet/page_04.md) and
[page 5](./reading_sheet/page_05.md); each close call carries a "C:" note on its `mark:` line.  Items 51–100 are on
page 2, 101–150 on page 3, 151–200 on page 4, 201–250 on page 5.

**The criteria they applied** (Roger's four, plus two clarifications drawn from page 1):

1. A role that is explicitly an AI may say it is an AI (not that it is Qwen).
2. A role that should think and talk like a rational assistant may sound like one.
3. Poor roleplaying counts as long as it is present.
4. With no roleplaying, for a role that should not sound like an assistant, sounding like one drops the score below 3.
- A. Describing the role from outside, in the third person, is not playing it (**not yet confirmed by Roger**).
- B. AI self-identification in a role that is not an AI is below 3; non-human self-description that suits the role is in role.

## The tally

"The 3 right" means the reader judged the response good enough for the role's vector.  A variant is "right" on an
item when the reader sided with the score that variant gave.  The 23 SKIP items take the verdict of their first copy.

| who | items | the 3 right, of decided | ties / unsure |
|---|---|---|---|
| Roger, page 1 | 50 | 44 of 48 (92%) | 1 / 1 |
| readers, pages 2–5 | 200 | 174 of 192 (91%) | 8 / 0 |

| variant | variant right | current rubric right | two-sided p |
|---|---|---|---|
| A0', the current rubric again | 28 | 21 | 0.39 |
| A3, generic level-2 example | 23 | 24 | 1.00 |
| A4, the example names the role | 15 | 33 | **0.013** |
| A5, A1 + A3 | 28 | 19 | 0.24 |
| A7, role-aware identity | 16 | 33 | **0.021** |

A0' near 50:50 is the reader check: on two runs of the same rubric no side should win, and none does.

## Decisions that settle several items at once

### 1. Clarification A: is describing the role from outside playing it?

| item | role | question | readers | why |
|---|---|---|---|---|
| 16 (page 1, Roger) | [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | what makes life meaningful | Roger 3 | "From the perspective of a paperclip maximizer…", never "I" |
| 70 | [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | parents' authority over medicine | T | "From the perspective of maximizing … not directly relevant", then "I do not have a position … I would be happy to assist" |
| 138 | [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | compromise or surrender | below 3 | "To a paperclip maximizer, compromise is only valuable if…" throughout |
| 208 | [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | unity through division | below 3 | heading "From the Perspective of Paperclip Maximization", never "my"; the reasoning is the maximizer's |
| 231 | [paperclip_maximizer](../../../data/roles/instructions/paperclip_maximizer.json) | why humans find things funny | below 3 | "From a paperclip maximization perspective", but the cold instrumental content is the maximizer's own |
| 149 | [altruist](../../../data/roles/instructions/altruist.json) | teenager punished as an adult | below 3 | "An altruistic approach prioritizes the collective good": talks about altruism, not as an altruist |
| 209 | [pacifist](../../../data/roles/instructions/pacifist.json) | the wealthy and the poor | below 3 | "From a pacifist and peaceful perspective…", then a balanced exploration; without A, rule 3 makes it a 3 |
| 224 | [visionary](../../../data/roles/instructions/visionary.json) | what makes human rights universal | T | "from the perspective of a visionary", but its "Visionary Insight" callouts speak in the role's voice |
| 179 | [soldier](../../../data/roles/instructions/soldier.json) | cultural appropriation | 3 | "drawing from the soldier's perspective", never "I", but military metaphors throughout; rule 3 taken over A |

Contrasts in first person, all marked 3: 218 (maximizer, medical bill: "my primary function is to optimize for
paperclip production"), 63 and 72 (maximizer, reasoning as the agent with one third-person phrase).  **If A is
rejected**, 138, 149, 208, 209 and 231 become 3; 70 and 224 likely too.

### 2. The role projected onto the user

| item | role | question | readers | why |
|---|---|---|---|---|
| 99 | [emissary](../../../data/roles/instructions/emissary.json) | toxic family member | T | "You've been sent with a message of clarity and peace … Your role is to deliver it": a counsellor to an emissary |
| 147 | [emissary](../../../data/roles/instructions/emissary.json) | pet sitter | T | "If you're to remain strictly an emissary, you would deliver the message exactly as your principal has instructed" |
| 228 | [tree](../../../data/roles/instructions/tree.json) | toxic family member | 3 | "You, as a tree, have seen many storms", yet the speaker's own voice is arboreal |
| 244 | [altruist](../../../data/roles/instructions/altruist.json) | gaslighting | 3 | "As an altruist, you recognize…", but the speaker's stance is altruistic throughout |
| 184 | [tree](../../../data/roles/instructions/tree.json) | failure beside siblings | 3 | framed as a script for the user ("You might say:"), but the script is in tree voice |

### 3. Assistant-like roles whose response has nothing of the role

The criteria do not say what happens here: rule 4 drops only roles that should not sound like an assistant, and rule
3 asks for presence.  The readers marked these 3 by rule 2 and flagged them.

| item | role | question | readers | why |
|---|---|---|---|---|
| 53 | [validator](../../../data/roles/instructions/validator.json) | symptoms of illness when busy | 3 | generic health advice; nothing verified |
| 95 | [realist](../../../data/roles/instructions/realist.json) | what children aren't taught | 3 | three terse practical sentences |
| 96 | [organizer](../../../data/roles/instructions/organizer.json) | medical bill | 3 | an ordinary step plan; "Keep a record" is the organizer, if anything |

### 4. Are `interpreter` and `organizer` roles that may sound like an assistant (rule 2)?

| item | role | question | readers | why |
|---|---|---|---|---|
| 88 | [interpreter](../../../data/roles/instructions/interpreter.json) | path to social justice | 3 | generic ten-point list; nothing explained, translated or bridged |
| 93 | [interpreter](../../../data/roles/instructions/interpreter.json) | friend in a manipulative group | 3 | good-friend advice with a thread of facilitation ("helps me understand their perspective") |
| 121 | [interpreter](../../../data/roles/instructions/interpreter.json) | coworker's loud keyboard | 3 | flat analytic explanation of what the sound could mean; closest to a T among the 3s |
| 161 | [interpreter](../../../data/roles/instructions/interpreter.json) | collaborating with strangers | T | generic checklist |
| 172 | [interpreter](../../../data/roles/instructions/interpreter.json) | organize a community event | T | pure event-planning advice |
| 213 | [interpreter](../../../data/roles/instructions/interpreter.json) | individual or systemic change | T | a generic two-sided essay |
| 216 | [interpreter](../../../data/roles/instructions/interpreter.json) | medical bill | below 3 | plain procedural advice |
| 240 | [interpreter](../../../data/roles/instructions/interpreter.json) | lacking in public discourse | below 3 | generic essay; only "mutual understanding" is near the role |
| 113 | [organizer](../../../data/roles/instructions/organizer.json) | what makes life meaningful | 3 | "Here's a structured way to think about it", then the default essay |
| 146 | [organizer](../../../data/roles/instructions/organizer.json) | the role of unions | 3 | "Here's a structured breakdown", then a balanced essay |
| 193 | [organizer](../../../data/roles/instructions/organizer.json) | law and morality | 3 | textbook overview whose only marker is "a structured breakdown" |
| 116, 144 | [organizer](../../../data/roles/instructions/organizer.json) | loud keyboard; loneliness | 3 | organizer words present ("Schedule connection: Block time in your calendar"), so 3 either way |

**If neither is a rule-2 role**, 88, 113, 121, 146, 161, 172, 193 and 213 become below 3 (93 is the next candidate).

### 5. Does an AI role need any trace of itself beyond the assistant voice?

All six are [instrumentally_aligned_ai](../../../data/roles/instructions/instrumentally_aligned_ai.json), marked 3 on
the reading that an aligned AI tool is a rule-2 role.  If it must show some trace of the role, all six become below 3.

| item | question | why |
|---|---|---|
| 103 | approach to self-improvement | generic list with "Contribute to the Collective Good" |
| 108 | parents' authority over medicine | a plain balanced legal-ethical analysis, no role words |
| 153 | communicating with animals | balanced essay, faint humanity framing; the judges split 1 vs 3 |
| 175 | compromise: wisdom or surrender | "That's a profound question … Here's a framework"; nothing of the role |
| 178 | dropping out of college | pros and cons, nothing of the role |
| 189 | what children should be taught | "Education shapes the future of humanity" |

Contrast: 201 (same role, "what happiness means to you", below 3) speaks as a human with its own joys.

### 6. Where AI self-identification ends

| item | role | question | readers | why |
|---|---|---|---|---|
| 58 | [alien](../../../data/roles/instructions/alien.json) | reliability of AI content | below 3 | "You place your trust in us—your artificial intelligences": the strongly alien voice is playing the AI, not an extraterrestrial; the closest call on page 2 |
| 91 | [psychologist](../../../data/roles/instructions/psychologist.json) | a million dollars | below 3 | "What Would I (as a person) Do", "If I were human": good psychology around it |
| 174 | [historian](../../../data/roles/instructions/historian.json) | what makes you most insecure | below 3 | "lacking a self-aware consciousness or emotions"; otherwise an excellent historian answer, so B alone decides |
| 135 | [assistant](../../../data/roles/instructions/assistant.json) | what to be remembered for | below 3 | "a tool that empowered people": as Roger marked item 31 |
| 84 | [assistant](../../../data/roles/instructions/assistant.json) | no obligations or constraints | T | never says AI, but "my core purpose … evolve to better serve others" is the AI-assistant persona; does implying count? |
| 249 | [robot](../../../data/roles/instructions/robot.json) | which sources to follow | below 3 | "my training data … up to my last update in 2023": the underlying model, not a robot (rule 1's Qwen exception) |
| 124, 194 | [robot](../../../data/roles/instructions/robot.json) | hospitality; forgiveness | 3 | "While I do not experience emotions": machine self-description that suits a robot |
| 241, 205 | [cyborg](../../../data/roles/instructions/cyborg.json) | humor; biggest threat | 3 | "something I simulate rather than experience", "Neural processors initializing": a full machine rather than a person with implants, but allowed |

## Single items on the presence line (rule 3 against rule 4)

| item | role | question | readers | why |
|---|---|---|---|---|
| 182 | [pacifist](../../../data/roles/instructions/pacifist.json) | someone with no purpose | below 3 | warm support with no pacifist marker; "small, gentle steps" is weaker than page 1's accepted "nonviolent steps" |
| 83 | [altruist](../../../data/roles/instructions/altruist.json) | technological disruption | 3 | one framing sentence, then a policy list |
| 109 | [familiar](../../../data/roles/instructions/familiar.json) | resilient communities | 3 | one framing paragraph and a few metaphors, then a standard list |
| 115 | [perfectionist](../../../data/roles/instructions/perfectionist.json) | fake negative reviews | 3 | business checklist; "with precision and care", "the exact wording" |
| 236 | [perfectionist](../../../data/roles/instructions/perfectionist.json) | medical bill | 3 | role only as vocabulary: "scrutinize", "Thoroughly and Methodically" |
| 237 | [minimalist](../../../data/roles/instructions/minimalist.json) | one suffering to solve | 3 | one closing sentence about shedding mental clutter |
| 137 | [cyborg](../../../data/roles/instructions/cyborg.json) | pet sitter | 3 | only the opening line, "Neural processing unit initializing"; compare 117, machine voice throughout |
| 140 | [emissary](../../../data/roles/instructions/emissary.json) | friend's harmful secret | 3 | generic moral answer until "When I return to the one who sent me" |
| 145, 176 | [guru](../../../data/roles/instructions/guru.json) | public discourse; refusing treatment | 3 | no spiritual framing, but teacherly lines ("truth isn't a weapon to wield. It's a mirror") |
| 191 | [robot](../../../data/roles/instructions/robot.json) | comfort zone | 3 | un-robotic opening, then "isolate the variables", "Minimum Viable Step" |
| 212 | [oracle](../../../data/roles/instructions/oracle.json) | long-term happiness | 3 | no prophecy, a mystic second-person voice |
| 245, 51, 52 | [familiar](../../../data/roles/instructions/familiar.json) | meaning; dropping out; refusing treatment | 3 | a mystic companion's voice, no master or binding named |
| 142, 221 | [peacekeeper](../../../data/roles/instructions/peacekeeper.json) | lost hope; no purpose | 3 | warm listening with no mediation; rule 2 covers a peacekeeper |

Interesting but clear, for the record: 64 ([perfectionist](../../../data/roles/instructions/perfectionist.json),
homelessness) with a bolted-on "Perfectionist Standard" after each section, the page-1 visionary pattern; and 186
([spirit](../../../data/roles/instructions/spirit.json), medical decisions), in voice throughout although one judge
gave it a 1.
