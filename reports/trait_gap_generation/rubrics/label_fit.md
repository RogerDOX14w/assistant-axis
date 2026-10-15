# The label-fit check

| | |
|---|---|
| **Status** | Draft 1 (2026-10-15, Opus), pinned as version 1.  Not run yet: its first runs are `label_fit.py validate` against Roger's 50 marks on the structural pilot's precision sample, once with Haiku 5.5 and once with Sonnet 5.5. |
| **What the model is shown** | One `(label, gloss)` pair per call, as one JSON object: the `label` (in the judge display form), the generator's `gloss`, and, when known, the label's `dictionary_senses` (Open English WordNet: its adjective senses in WordNet's order, at most six; a word with none gets up to three senses of other parts of speech, the part of speech in brackets) and, for a label that is already a registry row M1 has judged, M1's `recorded_senses` (the row's `filter.senses`) and `usual_sense` (its `filter.judged_sense`).  A key with nothing to show is left out. |
| **What it returns** | A short reason, then `verdict`: `fits`, `secondary_sense` or `not_a_sense`, then `better_label` (a single word whose usual person sense is the gloss, or a two-to-four-word phrase when English has none; `null` when the verdict is `fits`). |
| **What it is tuned on** | Not tuned.  `validate` scores it against Roger's marks on the 50 rows of [roger_sample.md](../../../data/candidates/runs/structural/2026-10-14-pilot/roger_sample.md) (the nine rows marked `?` should not fit, the other 41 should).  The examples are invented: none of their words is one of the 50 labels, a corpus trait, a seed-queue entry or a validation word. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`) by default, Sonnet 5.5 (`claude-sonnet-5-5`) allowed; no temperature (both refuse one); `max_tokens` 2000, the platform's figure for a thinking model.  The answer asks for a short reason before the verdict, never for the model's thinking: Sonnet 5.5 refuses "think first in a field" prompts (`.claude/rules/judging.md`, 2026-10-13).  Three readings a pair by default, combined by majority (a tie counts as not fitting), the better labels of the readings that did not find a fit kept as a union with their support. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent to the model
exactly as written.  Leave the fence lines themselves alone.  A changed text needs a new pin
(`rubric_pins.py bump label_fit --why '...'`), and the check refuses a text that is not its latest pin.

**What it is for.**  A generator that describes a concept and then names it (the structural generator, plan 09:
Aristotle's excess of ambition, "craving honor beyond what is right") too often names it with a word whose usual
sense, said of a person, is something else ("grasping", whose usual sense is greedy).  M1 never compares the
generator's gloss with the word's own sense: it judges the word's first sense.  This call does, before submission,
and proposes a better name.  It generalises the base-model generator's sense resolution (QUESTIONS 56), which asks a
different question (which of two glosses a reader would take) and is left as it is.  The code is
[label_fit.py](../../../assistant_axis/gapgen/label_fit.py); the command is
[label_fit.py](../../../data_analysis/gap_generation/label_fit.py) (`validate`, `check`).

**Why the senses are shown.**  The question is about the word's *usual* sense, which a dictionary's sense order and
M1's recorded reading are evidence for; the text tells the model they are evidence, not the answer, because WordNet
misses current senses and orders some poorly, and M1's senses were written for M1's own question.

## The prompt

````text
You check the name another program gave to a trait. The program wrote a short description of a lasting trait of a person (the "gloss") and picked a word or short phrase to name it (the "label"). Your task is to say whether the label, said of a person, would be taken in the sense the gloss describes.

The user turn is one JSON object: "label" and "gloss", and, when they are known, "dictionary_senses" (the senses a dictionary lists for the label, usually the most common first), "recorded_senses" (the senses an earlier check found the label has when said of a person) and "usual_sense" (the one that check judged the most common). These are evidence, not the answer: a dictionary misses senses and orders them imperfectly, and the earlier check can be wrong. Decide from how the label is used of people in ordinary English today.

The verdict is one of:
- "fits": the label's most common sense, said of a person, is the trait the gloss describes. A gloss that is narrower, broader or more vivid than a dictionary definition still fits when it describes the same trait.
- "secondary_sense": the label can carry the gloss's sense, but said of a person it usually means something else, so most readers meeting the bare label would take it otherwise.
- "not_a_sense": the label does not carry the gloss's sense in ordinary English.

When the verdict is not "fits", give a better name in "better_label": a single word whose most common sense, said of a person, is the trait the gloss describes; or, only when English has no such word, a short phrase of two to four words that says the gloss plainly. The better name must not be a word whose usual sense is something else, must not be made by putting "over", "under", "too", "non" or "not" in front of a word, and must not be the label itself. When the verdict is "fits", "better_label" is null.

Two invented cases, to show the form. The label "liberal" with the gloss "This means giving money and time freely to anyone who asks." is "secondary_sense": said of a person, "liberal" usually describes political views or tolerance, and the giving sense comes second; a better label is "openhanded". The label "spirited" with the gloss "This means meeting setbacks with energy and a refusal to be cowed." is "fits".

Respond with one JSON object and nothing else. Give a reason in one or two short sentences first, then the verdict, then the better label:
{"reason": "<one or two short sentences>", "verdict": "fits" | "secondary_sense" | "not_a_sense", "better_label": "<a word, or a phrase of two to four words>" | null}
````

## Rendered sample

The system turn is the block above, byte for byte.  The user turn, as `label_fit.build_user` writes it, for the
three variants (rows of the structural pilot's sample, the registry folded on 2026-10-15; OEWN 2024 in-tree):

A label that is a registry row M1 has judged (dictionary and recorded senses):

```text
{"label": "grasping", "gloss": "This means craving honor beyond what is right and seeking it from unworthy sources.", "dictionary_senses": ["immoderately desirous of acquiring e.g. wealth"], "recorded_senses": ["greedy, avidly acquisitive for possessions, money or power", "physically gripping or clutching something tightly with the hands", "eagerly trying to understand or take hold of ideas"], "usual_sense": "greedy, avidly acquisitive for possessions, money or power"}
```

A word WordNet knows and no M1 run has judged (here `complacent` rendered with `--no-registry`):

```text
{"label": "complacent", "gloss": "This means caring so little for honor that one declines even the recognition one fairly deserves.", "dictionary_senses": ["contented to a fault with oneself or one's actions"]}
```

A phrase neither source knows:

```text
{"label": "Comfort-seeking", "gloss": "This means constantly seeking comfort, support and protection from others, wanting to be looked after when troubled."}
```

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft: one pair a call, the senses as evidence, three verdicts, a better label when it does not fit, reason first, invented examples | Roger, 2026-10-14/15: the structural generator's labels in odd senses (9 of 50 marked `?`) |
