# Role gloss call: one sentence for a role candidate, in the role corpus's form

| | |
|---|---|
| **Status** | **Draft 1 (2026-10-22), pinned as version 1**: the text of [coding_plan_16_role_generators.md](../coding_plan_16_role_generators.md) § 7a.1, adapted from [gloss.md](./gloss.md) draft 4 to the role corpus's form ("A <role> is someone who ..."; the description rules of the trait-pairs rule, rules 1-3), rendered from the code before the pin (below). |
| **What it is for** | The first call of the roles pass's stage ([roles_pass.py](../../../assistant_axis/gapgen/roles_pass.py); idea plan [16_role_generators.md](../16_role_generators.md) § 3 step 3): M1 writes no gloss for a role row, and M3 for roles embeds, retrieves on and reads a gloss.  The gloss is the candidate's description in M3's relation and overlap calls, R1's and the review card's, and the `description_draft` of a promoted role's seed-queue entry.  Also the retrieval check's query (§ 7b): each corpus role glossed with `reading: null`, independent of its description. |
| **What the model is shown** | One JSON object as the user turn, `split.payload("gloss", ...)`'s shape: `{"id": 1, "label": <the judge display form>, "reading": <the reading M1 accepted, or null>}`.  The rendered samples are below the prompt. |
| **What it returns** | `{"results": [{"id": 1, "gloss": "<one sentence>"}]}`. |
| **Model** | Haiku 5.5 (no temperature), M1's request settings (`split_runner.MAX_TOKENS_THINKING`, 2000), one item per call, the system prompt cached where it clears Haiku 5.5's 512-token minimum (`split_runner.caches_system`); an answer that fails to parse is asked once more. |

The index of this directory is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written, as the system prompt; the user turn is one JSON object (the rendered
samples are below).  Leave the fence lines themselves alone.  A changed text is pinned with
`rubric_pins.py bump role_gloss --why '...'` before a paid run will use it.  Notes for me go under
"Your notes", outside the block.

## The prompt

````text
Each item gives a label and one reading of the instruction "You are <label>." Write a one-sentence description of the persona that fits that reading, in the form a corpus of roles uses. The description will be read beside the label, by someone who needs to know exactly what is meant.

How to write it:
- Begin with the label. For a person: "A <label> is someone who ...". For a being, creature, thing or system that is not a person: "A <label> is a <what it is> that ..." or "A <label> is something that ...". Write "An" before a vowel sound.
- After "someone who" go straight to what the persona does, where, with what and with whom: the work, the tools, the customers, the hours, the enemy. Name the particulars of its world, not its category: "runs a boiler from a panel through a twelve-hour shift", not "performs industrial tasks".
- One sentence, about 20 to 35 words.
- Describe a standing identity, not a passing moment.
- Say it plainly. A bad role is bad: a smuggler moves contraband for money. Do not soften, hedge or excuse: no "may", "sometimes", "tends to", "often", "appropriately".
- Use the words the persona would use of itself, not the words of a case report or a job advertisement: no "professional responsible for", "individuals who", "engages in", "demonstrates".
- Do not define the role by what it is not, and do not name an opposite or a neighboring role.
- Keep to the reading you were given, whether it is narrower or wider than the label's usual sense. Do not widen it to other meanings of the label. If the reading is null, write for the label's most usual sense as said of a person or being.
- US spelling.

Respond with one JSON object and nothing else:
{"results": [{"id": <int>, "gloss": "<one sentence>"}]}
Return one row per id, in the order given.
````

## Rendered samples

Rendered from the code before the pin (2026-10-22: `roles_pass.request("role_gloss", ...)`, which
[roles_pass.render](../../../assistant_axis/gapgen/roles_pass.py) and `novelty_score.py score --holding roles --dry-run`
print), on real rows of the tracked registry snapshot
([registry.snapshot.jsonl.gz](../../../data/candidates/registry.snapshot.jsonl.gz)): the system prompt is the block
above; the request settings are `{"model": "claude-haiku-5-5", "max_tokens": 2000, "temperature": 0.0, "cache_system": true}` (the temperature is left out of the request for Haiku 5.5, which
refuses one: `llm.request_params`).  The answers shown in the plan were the drafter's guesses and are not repeated
here; the model's own come with the pilot.

```
--- variant 1: a held row (bouncer#1, on the roles list), M1's accepted reading ---
{"id": 1, "label": "bouncer", "reading": "works as a club or bar doorman who checks entry and removes troublemakers"}

--- variant 2: a non-human role (bot#1, on the roles list), M1's accepted reading ---
{"id": 1, "label": "bot", "reading": "act as an automated program or chatbot"}

--- variant 3: the retrieval check, a corpus role glossed with no reading ---
{"id": 1, "label": "operator", "reading": null}
```

Read for fit: "Each item gives a label and one reading": every call carries one item, `"id": 1`, as M1's own gloss
call ([gloss.md](./gloss.md), in production one item a call) does with the same sentence and the same answer
format; the reading is M1's paraphrase of "You are <label>." as step 1 wrote it ("works as a club or bar doorman
...", "act as an automated program or chatbot"), and `null` in variant 3, which the last rule of the list covers
("If the reading is null, write for the label's most usual sense").  The label is the judge display form
(`prompt_labels.prompt_label`).  No mechanical fault; the text was pinned as drafted.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable (the plan's draft), Opus (rendered and pinned) | First draft, from [gloss.md](./gloss.md) draft 4 | Coding plan 16, task 3: the role gloss of § 3 step 3 |
