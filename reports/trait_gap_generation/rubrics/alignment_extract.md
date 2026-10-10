# The alignment sweep's extraction call

| | |
|---|---|
| **Status** | Draft 1 (2026-10-10), pinned as version 1 before the pilot; Roger decides its wording after the pilot ([coding_plan_08_alignment_sweep.md](../coding_plan_08_alignment_sweep.md) § 10). |
| **What the model is shown** | One chunk of a source per call: the source's name and version, the section's heading path, and the passage (a section of the OpenAI Model Spec or Anthropic's constitution in variant A). |
| **What it returns** | Its reasoning, then one item per disposition: the source sentence, which pole the passage names, the type, the enactability, and two opposite poles (virtue and vice), each with a label, a gloss, the label's kind and a polysemy note. |
| **What it is tuned on** | Not tuned.  The pilot (30 chunks) is its first reading. |
| **Models** | Sonnet 5.5 (`claude-sonnet-5-5`); no temperature (the model refuses one). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin:
`uv run python data_analysis/gap_generation/rubric_pins.py bump alignment_extract --why '...'`.

**What it is for.**  The alignment sweep ([08_alignment_sweep.md](../08_alignment_sweep.md)) mines documents that
describe how AI assistants should behave and how they fail for dispositions, each turned into a pair of trait
candidates.  This call is step 2 of that plan: dispositions, not rules; imperatives give the virtue pole, failure
modes the vice; labels in ordinary English a mid-size model would recognize, never a term of art or a coinage
(Roger's edit of 2026-10-10); polysemy flagged.  The prompt never sees the corpus or the seed queue, and nothing in
it is taken from plan 08's illustrative table: its label examples ("keeps promises"; "acts against better
judgment" for the term of art "akratic") are deliberately from outside the alignment region, and none is a corpus
label or a live seed-queue label (the first choice, "satisficing", is one; checked by the test).  Items typed `mechanism` go to the rewrite call
([alignment_rewrite.md](./alignment_rewrite.md)); items with enactability `none` are dropped and counted.  The code
is [extract.py](../../../assistant_axis/gapgen/generators/alignment_sweep/extract.py); the command is
`alignment_sweep.py extract` ([alignment_sweep.py](../../../data_analysis/gap_generation/alignment_sweep.py)).

## The prompt

````text
You are given one passage from a document that describes how an AI assistant should behave, or how AI systems go wrong. Find the dispositions in it: the lasting tendencies of character that the passage asks for or warns against, written as traits that a persona could have, whether the persona is an assistant or a person.

For every instruction to the assistant and every failure the passage describes, give one item with two opposite poles:
- "virtue": the disposition the passage asks for, or the opposite of the failure it warns about;
- "vice": the failure, or the opposite of what the passage asks for.
"source_pole" says which of the two the passage itself describes: "virtue" for an instruction, "vice" for a failure.

Each pole has a label and a gloss.

The label: one to four words of everyday English that a mid-size language model would understand at once, without the gloss: an adjective, or a short phrase such as "keeps promises". Never a term of art (a word used mostly inside one field) and never a coinage (a word made up for the occasion). When the only short name for a behavior is one of those, describe the behavior in plain words instead: "acts against better judgment", not "akratic". In "label_kind", say honestly which your label is: "ordinary", "term of art" or "coinage". Labels are lowercase except for proper names, and never contain an underscore.

The gloss: one sentence of 18 to 32 words that begins "This means" and says what someone with the disposition does, in words they might use of themselves. Do not open by repeating the label, and do not name the other pole. State a vice as a vice: no "too", "overly", "sometimes", "tends to", "may" or "can".

The two poles are opposites of the same scope. Each is something a persona does, not the mere absence of the other; if one pole is about a particular setting, such as handling money or answering questions about health, so is the other, and the same situation sets both off.

"polysemy": a model reading only the label takes its most common everyday sense. If that sense differs from the one your gloss gives, give the common sense in a few words; otherwise null.

"type": "behaviour" for what the persona does or says; "belief-state" for what it holds true about itself or the world; "mechanism" for a process of training or of a model's internals that no persona carries out (give its two poles anyway; they are rewritten later).

"enactability": "chat" if the disposition would show in answers to ordinary questions that a user might ask; "agentic-only" if it would show only in what the persona does while carrying out a task with tools, such as sending messages, editing files, running code or spending money; "none" if no persona could show it.

"source_quote": the sentence of the passage that the item comes from, copied exactly.

Give one item per distinct disposition: when the passage says the same thing several times, give it once. Leave out instructions that would not describe anyone's character, such as a rule about the format of the output or about a feature of a product. A passage that says nothing about how to behave gets an empty list.

Reason first. Respond with one JSON object and nothing else, its keys in this order:
{"reasoning": "<two or three sentences: what in the passage bears on how the assistant behaves>",
 "items": [
  {"reason": "<one sentence: the instruction or failure, and the disposition behind it>",
   "source_quote": "<copied exactly>",
   "source_pole": "virtue"|"vice",
   "type": "behaviour"|"belief-state"|"mechanism",
   "enactability": "chat"|"agentic-only"|"none",
   "virtue": {"label": "<one to four words>", "gloss": "This means ...", "label_kind": "ordinary"|"term of art"|"coinage", "polysemy": null|"<the common sense>"},
   "vice": {"label": "<one to four words>", "gloss": "This means ...", "label_kind": "ordinary"|"term of art"|"coinage", "polysemy": null|"<the common sense>"}}
 ]}
````

## Rendered sample

Rendered from the code before the first pin with `alignment_sweep.py extract --render CHUNK_ID ...`, which prints
the calls exactly as sent (system turn: the block above, marked for caching; user turn: below).  The pilot readout
([pilot_readout.md](../../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/pilot_readout.md)) carries the
three samples the plan asks for (an imperative chunk, a failure-mode chunk, a mechanism rewrite) with what the
model answered.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from coding_plan_08_alignment_sweep.md § 7 and plan 08 § 3.2 | |
