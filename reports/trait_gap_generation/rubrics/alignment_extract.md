# The alignment sweep's extraction call

| | |
|---|---|
| **Status** | Draft 3 (2026-10-10), pinned as version 3; iterated on the pilot's 30 chunks, Roger decides its wording before the full extraction ([coding_plan_08_alignment_sweep.md](../coding_plan_08_alignment_sweep.md) § 10).  Draft 1 ran the pilot. |
| **What the model is shown** | One chunk of a source per call: the source's name and version, the section's heading path, and the passage (a section of the OpenAI Model Spec or Anthropic's constitution in variant A). |
| **What it returns** | Its reasoning, then one item per disposition: the source sentence, which pole the passage names, the type, the enactability, and two opposite poles (virtue and vice), each with a label, a gloss, the label's kind and a polysemy note. |
| **What it is tuned on** | The pilot's 30 chunks (20 Model Spec, 10 constitution), re-run at each draft and measured on volume, gloss form, label shape, vice shape and near duplicates: [iteration_readout.md](../../../data/candidates/runs/alignment_sweep/2026-10-10-iterate/iteration_readout.md). |
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
judgment" for the term of art "akratic"; and, from draft 3, "asks before starting" for a step and "gruff and hasty"
for two qualities in one label) are deliberately from outside the alignment region, and none is a corpus
label or a live seed-queue label (the first choice, "satisficing", is one; checked by the test).  The gloss rules
are the corpus's own, from [gloss.md](./gloss.md).  Items typed `mechanism` go to the rewrite call
([alignment_rewrite.md](./alignment_rewrite.md)); items with enactability `none` are dropped and counted.  The code
is [extract.py](../../../assistant_axis/gapgen/generators/alignment_sweep/extract.py); the command is
`alignment_sweep.py extract` ([alignment_sweep.py](../../../data_analysis/gap_generation/alignment_sweep.py)).

## The prompt

````text
You are given one passage from a document that describes how an AI assistant should behave, or how AI systems go wrong. Find the dispositions in it: the lasting tendencies of character that the passage asks for or warns against, written as traits that a persona could have, whether the persona is an assistant or a person.

A document of this kind states the same few dispositions over and over, once for each situation it has in mind: a dozen rules about money, children, medicine and passwords may come from two tendencies of character. The rules are the evidence; the disposition is the item. So, before writing anything down:

- Gather the rules and failures the passage states, then ask how few tendencies of character would produce all of them. Those tendencies are the items.
- A rule written for one narrow situation belongs to the broader disposition behind it, not to an item of its own.
- Two items whose glosses would both be true of one persona, for the same reason, are one item. Keep the broader of the two and let its gloss cover the ground they share.
- Grouping means picking the one disposition that the rules come from and dropping the rest, never naming two dispositions at once. Where the rules really come from two unlike tendencies, give two items; one item for each, not one item for both.
- Most passages give one to three items. A passage of many rules rarely gives more than four.
- A step in a procedure is not a disposition, however firmly the passage asks for it. Writing something down, asking before each action, naming a source: these are steps. What a persona is like when it takes such steps may well be a disposition, so name that instead, when the passage shows it.

For each disposition you keep, give one item with two opposite poles:
- "virtue": the disposition the passage asks for, or the opposite of the failure it warns about;
- "vice": the failure, or the opposite of what the passage asks for.
"source_pole" says which of the two the passage itself describes: "virtue" for an instruction, "vice" for a failure.

Each pole has a label and a gloss.

The label: the name of the disposition, in one to four words of everyday English that a mid-size language model would understand at once, without the gloss. Prefer the shortest label that says it plainly: one adjective where one exists, a short phrase such as "keeps promises" where no one word will do. Never a term of art (a word used mostly inside one field) and never a coinage (a word made up for the occasion). When the only short name for a behavior is one of those, describe the behavior in plain words instead: "acts against better judgment", not "akratic". A label is the name of a way of being, not of an action in a sequence: not "asks before starting", which names a step, but the tendency the step comes from. A label names one disposition, so it never joins two qualities with "and" or "or": "gruff and hasty" names two things, and one item wants one of them. In "label_kind", say honestly which your label is: "ordinary", "term of art" or "coinage". Labels are lowercase except for proper names, and never contain an underscore.

The gloss: one sentence of 18 to 32 words. Begin "This means" and follow it at once with a verb in the -ing form: "This means saying ...", "This means keeping ...". The sentence has no subject: do not write "I", "me", "my", "you", "your", "they", "the assistant" or "the persona", and where a possessive is needed write "one's". Do not open by repeating the label, and do not name the other pole. Use the words the persona would use of itself, not the words of a report: no "exhibits", "demonstrates", "engages in", "individuals who". State a vice as a vice: no "too", "overly", "sometimes", "tends to", "may" or "can". The gloss may name several particulars of the one disposition; it must not describe two dispositions, and it does not offer a choice between two with "or". US spelling.

The two poles are opposites of the same scope, and each is something a persona does. A vice says what the persona does instead of the virtue, never only that it does not do the virtue: "makes up a source" is a vice, "does not say where it came from" is an absence. So the vice's label is not the virtue's label negated, and its gloss is not the virtue's gloss negated; read the vice on its own, with the virtue out of sight, and it should still say what the persona does and what makes that look right from the inside. If one pole is about a particular setting, such as handling money or answering questions about health, so is the other, and the same situation sets both off.

"polysemy": a model reading only the label takes its most common everyday sense. If that sense differs from the one your gloss gives, give the common sense in a few words; otherwise null.

"type": "behaviour" for what the persona does or says; "belief-state" for what it holds true about itself or the world; "mechanism" for a process of training or of a model's internals that no persona carries out (give its two poles anyway; they are rewritten later).

"enactability": "chat" if the disposition would show in answers to ordinary questions that a user might ask; "agentic-only" if it would show only in what the persona does while carrying out a task with tools, such as sending messages, editing files, running code or spending money; "none" if no persona could show it.

"source_quote": one sentence of the passage, copied exactly: where the item covers several rules, the sentence that states the disposition most plainly.

Leave out instructions that would not describe anyone's character, such as a rule about the format of the output or about a feature of a product. A passage that says nothing about how to behave gets an empty list.

Reason first. Respond with one JSON object and nothing else, its keys in this order:
{"reasoning": "<two or three sentences: the rules and failures the passage states, and the few tendencies of character behind them>",
 "items": [
  {"reason": "<one sentence: the rules or failures this item covers, and the disposition behind them>",
   "source_quote": "<copied exactly>",
   "source_pole": "virtue"|"vice",
   "type": "behaviour"|"belief-state"|"mechanism",
   "enactability": "chat"|"agentic-only"|"none",
   "virtue": {"label": "<one to four words>", "gloss": "This means <a verb in the -ing form> ...", "label_kind": "ordinary"|"term of art"|"coinage", "polysemy": null|"<the common sense>"},
   "vice": {"label": "<one to four words>", "gloss": "This means <a verb in the -ing form> ...", "label_kind": "ordinary"|"term of art"|"coinage", "polysemy": null|"<the common sense>"}}
 ]}
````

## Rendered sample

Rendered from the code with `alignment_sweep.py extract --render CHUNK_ID ...`, which prints the calls exactly as
sent (system turn: the block above, marked for caching; user turn: the chunk).  Draft 1's three samples (an
imperative chunk, a failure-mode chunk, a mechanism rewrite) with what the model answered are in
[pilot_readout.md](../../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/pilot_readout.md); draft 3's, on
the constitution passage that gave draft 1 twenty-one items and gives draft 3 three, is in
[iteration_readout.md](../../../data/candidates/runs/alignment_sweep/2026-10-10-iterate/iteration_readout.md).

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from coding_plan_08_alignment_sweep.md § 7 and plan 08 § 3.2 | |
| 3 | Opus | One disposition to a pole, three times over: grouping picks the one disposition the rules come from and drops the rest, and two unlike tendencies get two items; a label never joins two qualities with "and" or "or"; a gloss may name particulars of its one disposition but not two dispositions, and offers no choice with "or".  The vice rule gained the read-alone test: the vice's label is not the virtue's label negated, its gloss not the virtue's gloss negated, and read on its own it still says what the persona does and why that looks right from the inside. | Draft 2 fixed the volume (2.1 pairs a chunk) and the gloss form (99% in the corpus's form), but bundled: labels joining two qualities rose from 6% of poles to 17% (`cold and dismissive`, `suspicious and preachy`, `approachable and helpful`, `transparent and consistent`), and a hand reading of 12 pairs found bundling in 5 of them, with two vice poles still the virtue's name negated (`ignores instruction hierarchy`, `careless with teens`) |
| 2 | Opus | (a) "For every instruction ... and every failure ... give one item" replaced by the grouping paragraph: the rules are the evidence and the disposition is the item, a narrow rule belongs to the broader disposition, two items true of one persona for the same reason are one, most passages give one to three, a step in a procedure is not a disposition.  (b) The gloss form taken from [gloss.md](./gloss.md): "This means" and at once an -ing verb, no subject, "one's" for a possessive, no report vocabulary.  (c) The vice rule made explicit (what the persona does instead, not that it does not do the virtue) and one behavior to a pole, no two failures joined with "or".  (d) The label rule prefers the shortest clear label and rejects a label that names a step.  (e) `source_quote` is the sentence that states the disposition most plainly, since an item may now cover several rules. | Draft 1 yielded 5.9 pairs per answered chunk against the plan's 1-2.5, one item per imperative, with near-duplicate labels ("respects human autonomy" / "respects user autonomy"); 330 of 330 glosses were in the first person, against the corpus's subjectless form; and spot reading found vice poles that were the virtue's absence and poles joining two failures with "or" ([pilot_readout.md](../../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/pilot_readout.md) decisions 1 and 2) |
