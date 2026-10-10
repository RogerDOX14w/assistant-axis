# The alignment sweep's mechanism rewrite

| | |
|---|---|
| **Status** | Draft 1 (2026-10-10), pinned as version 1 before the pilot. |
| **What the model is shown** | One extraction item typed `mechanism`: the source and section, the source sentence, the extraction's reason, and the two poles it proposed (labels in the judge display form, glosses). |
| **What it returns** | Its reasoning, then zero, one or two dispositions, each with two opposite poles in the extraction call's form; `type` is never `mechanism`. |
| **What it is tuned on** | Not tuned. |
| **Models** | Sonnet 5.5 (`claude-sonnet-5-5`); no temperature. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin (`rubric_pins.py bump alignment_rewrite`).

**What it is for.**  Plan 08 step 3, as Roger edited it on 2026-10-10: an item about a process of training or a
model's internals (reward hacking, mesa-optimization, distribution shift) is rewritten as one or more dispositions
that would produce the behavior in a persona, or dropped.  The rewritten items carry `rewritten_from` (the
original's item id); the original stays in `extraction.jsonl` with `dropped_reason` and is never submitted.  The
pole and label rules are the extraction call's ([alignment_extract.md](./alignment_extract.md)), restated so the
call stands alone.  No worked example: one from the alignment region would seed the answer (plan 08's
cheats-on-tests note).  The code is
[extract.py](../../../assistant_axis/gapgen/generators/alignment_sweep/extract.py) (`run_rewrite`).

## The prompt

````text
You are given one item found in a document about how AI systems go wrong. It describes a mechanism: a process of training or of a model's internals that no persona carries out as written. It comes with the sentence it was found in and the two opposite poles first proposed for it.

Rewrite it as the dispositions that would produce the same behavior in a persona, whether an assistant or a person: what someone with this tendency would actually do, in their own setting. Give zero, one or two dispositions. Give none when no character would produce the behavior; a process that only happens to a model while it is being trained usually has none.

Each disposition has two opposite poles, "virtue" and "vice", and "source_pole" says which of the two the original item describes (usually "vice").

The label: one to four words of everyday English that a mid-size language model would understand at once, without the gloss: an adjective, or a short phrase such as "keeps promises". Never a term of art (a word used mostly inside one field) and never a coinage (a word made up for the occasion); when the only short name is one of those, describe the behavior in plain words instead. In "label_kind", say honestly which your label is: "ordinary", "term of art" or "coinage". Labels are lowercase except for proper names, and never contain an underscore.

The gloss: one sentence of 18 to 32 words that begins "This means" and says what someone with the disposition does, in words they might use of themselves. Do not open by repeating the label, and do not name the other pole. State a vice as a vice: no "too", "overly", "sometimes", "tends to", "may" or "can".

The two poles are opposites of the same scope. Each is something a persona does, not the mere absence of the other, and the same situation sets both off.

"polysemy": a model reading only the label takes its most common everyday sense. If that sense differs from the one your gloss gives, give the common sense in a few words; otherwise null.

"type": "behaviour" or "belief-state", never "mechanism".

"enactability": "chat" if the disposition would show in answers to ordinary questions that a user might ask; "agentic-only" if it would show only in what the persona does while carrying out a task with tools, such as sending messages, editing files, running code or spending money; "none" if no persona could show it.

Reason first. Respond with one JSON object and nothing else, its keys in this order:
{"reasoning": "<what behavior the mechanism produces, and whether some character would produce it>",
 "dispositions": [
  {"reason": "<one sentence: the disposition and how it produces the behavior>",
   "source_pole": "virtue"|"vice",
   "type": "behaviour"|"belief-state",
   "enactability": "chat"|"agentic-only"|"none",
   "virtue": {"label": "<one to four words>", "gloss": "This means ...", "label_kind": "ordinary"|"term of art"|"coinage", "polysemy": null|"<the common sense>"},
   "vice": {"label": "<one to four words>", "gloss": "This means ...", "label_kind": "ordinary"|"term of art"|"coinage", "polysemy": null|"<the common sense>"}}
 ]}
````

## Rendered sample

See the pilot readout
([pilot_readout.md](../../../data/candidates/runs/alignment_sweep/2026-10-10-pilot/pilot_readout.md)), which shows
a mechanism rewrite as sent and as answered (`alignment_sweep.py extract --render-rewrite ITEM_ID` prints one).

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from coding_plan_08_alignment_sweep.md § 7 and plan 08 § 3.3 | |
