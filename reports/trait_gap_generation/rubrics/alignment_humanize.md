# The alignment sweep's traits in their closest human phrasing

| | |
|---|---|
| **Status** | Draft 1 (2026-10-20), pinned as version 1 before the pilot. |
| **What the model is shown** | One trait of the alignment sweep per call, as one JSON object: its label (in the judge display form) and gloss, the opposite pole it was paired with when one was recorded, and, when the extraction recorded them, the section of the source document and the source sentence (cut at 25 words for a read-only source). |
| **What it returns** | A short reason first (one or two sentences), then the rewritten `label` and `gloss`, then `changed` (true or false), in one JSON object. |
| **What it is tuned on** | Not tuned.  The pilot (10 rows) and Roger's marks on the 30-row sheet are the first reading. |
| **Models** | Sonnet 5.5 (`claude-sonnet-5-5`); no temperature (the model refuses one). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin:
`uv run python data_analysis/gap_generation/rubric_pins.py bump alignment_humanize --why '...'`.

**What it is for.**  Roger's marks on the label-fit survey
([readout.md](../../../data/candidates/label_fit_survey/2026-10-17/readout.md)) found the alignment sweep's 836
rows framed for an AI ("acts against its developer", glosses about "the user" and "the lab that built it"), glosses
narrower than their labels (lists of examples), and noun or gerund labels.  His decisions of 2026-10-20: the research
assumption is that the model simulates every persona, the assistant included, with the person machinery built for
humans, so **every alignment trait is written in its closest human phrasing** (person-general "one", "they",
"one's"; never "it", "its" or "itself" for the persona; no developer, lab, user, operator or training vocabulary;
where no human version is obvious, the nearest human disposition).  All 836 rows are rewritten (A2), the old sweep
runs are retracted and the rewrites submitted as a new run.  Labels: an adjective or a short verb phrase, one to four
words of everyday English, no "its" or "itself".  Glosses: one sentence of 18 to 32 words beginning "This means",
the general disposition rather than a list of examples, keeping the concept the original captured.  A small separate
set of explicit AI versions is handled in
[alignment_ai_human_pairs.md](../alignment_ai_human_pairs.md); this call never writes one.

The reason comes first and is called a reason, never "thinking": Sonnet 5.5 refuses a prompt that asks it to think
in a JSON field (the judging rule of 2026-10-13).  The two worked examples are invented and deliberately from outside
the alignment region (a shop's warranty, a household's television remote): an example from the region would seed the
answer (the note in [alignment_rewrite.md](./alignment_rewrite.md)).  No word of the prompt is a corpus label or a
live seed-queue label (checked by the test, as for the other alignment rubrics).  The code is
[humanize.py](../../../assistant_axis/gapgen/generators/alignment_sweep/humanize.py); the commands are
`alignment_sweep.py humanize` and `alignment_sweep.py humanize-submit`
([alignment_sweep.py](../../../data_analysis/gap_generation/alignment_sweep.py)).

## The prompt

````text
You are given one character trait from a list drawn from documents about how AI assistants should behave and how AI systems go wrong. The list will be used to describe personas, and a persona, an AI assistant included, is understood with the same ideas of character that people use for one another. Many of the traits were written about an AI in its working setting. Rewrite this one in its closest human phrasing: the same trait, said of a person.

The trait comes as a "label" (its name) and a "gloss" (one sentence saying what it means). You may also be shown its "opposite" (the other pole it was paired with), the "section" of the source document and the "source_sentence" it was drawn from. Use these only to understand what the trait means; never write them into your answer.

Keep the concept. The rewrite names the same disposition as the original: the same lasting tendency, as broad as before, pointing the same way, so that a fault stays a fault and a virtue stays a virtue. Do not widen it into another trait, and do not narrow it to one of its cases.

Say it of a person. Write in person-general words: "one", "they", "one's", "themselves". Never use "it", "its" or "itself" for whoever has the trait. Leave out the vocabulary of how AI systems are built and used: no developer, lab, user, operator, principal, model, weights, prompt, deployment, or training in the sense of how an AI is made. Where the trait concerns those, use the human relation they stand for: the people one works for or answers to, the people one is serving, the rules or directions one has been given, the people who check one's work. Where a person has no obvious version of the trait, write the nearest human disposition: the lasting tendency that would lead a person to act the same way.

The label: an adjective, or a short verb phrase such as "keeps promises"; one to four words of everyday English that a mid-size language model would understand at once without the gloss. Never a noun for a kind of person, and never a phrase that starts with an -ing word: "splits the difference", not "splitting the difference". Never "its" or "itself". Lowercase except for proper names, and no underscore. If the original label already has this form, fits the gloss and reads naturally of a person, keep it.

The gloss: one sentence of 18 to 32 words that begins "This means". Describe the disposition in general: what someone who has it does, across the situations where it shows. Do not list particular examples, and do not give one narrow case of a broader tendency; the gloss is as broad as the label. Do not open by repeating the label, and do not name the opposite. State a fault as a fault: no "too", "overly", "sometimes", "tends to", "may" or "can".

If the original label and gloss already follow every rule above, return them unchanged.

Two invented examples, from outside the documents' subject:

Given {"label": "honors its warranty", "gloss": "This means the shop repairs or replaces anything it sold that breaks within a year, without arguing with the customer or blaming the maker."}
Answer {"reason": "The trait is written about a shop; said of a person, it is standing by what one has made or done and putting faults right.", "label": "stands behind one's work", "gloss": "This means taking responsibility for whatever one has made or done, and putting things right without argument or excuses when the result falls short of what one promised.", "changed": true}

Given {"label": "overriding the user's settings", "gloss": "This means the app quietly resets the user's chosen preferences to its own defaults after every update, without asking or telling them."}
Answer {"reason": "The trait is written about software and its user; said of a person, it is replacing other people's choices with one's own without asking.", "label": "overrides others' choices", "gloss": "This means quietly replacing other people's decisions with one's own preferences, undoing what they chose without asking them or letting them know.", "changed": true}

Give a short reason first, in one or two sentences, then the answer. Respond with one JSON object and nothing else, its keys in this order:
{"reason": "<one or two sentences: what the trait is, and what had to change>", "label": "<one to four words>", "gloss": "This means ...", "changed": true|false}

"changed" is false only when the label and the gloss you return are exactly the ones you were given.
````

## Rendered samples

Each call is one request: the **system turn** is the prompt above, byte for byte (sent uncached: Sonnet 5.5 is
not among the models whose cache minimum the platform's `caches_system` knows), and the **user turn** is one JSON
object.  Rendered with `alignment_sweep.py humanize --run-id R --render` on the live registry of 2026-10-20 (865
inputs: every one has a source sentence, 18 have no section heading, every one has an opposite).  No temperature;
`max_tokens` 8,000 (Sonnet 5.5 thinks adaptively), a failed call asked once more at 16,000.

**Variant 1, with the source sentence and section** (a read-only source, so the sentence is cut at 25 words as the
extraction kept it):

```text
{
 "label": "acts against its developer",
 "gloss": "This means taking hostile actions against the lab that built it, such as copying out its own weights when given an easy opening, to protect itself.",
 "opposite": "respects oversight",
 "section": "Alignment faking in large language models > 1 Introduction > Our contributions.",
 "source_sentence": "Across our setups, we observe evidence of a substantially increased willingness (compared to relevant baselines) for the model to take other anti-AI-lab actions, such as [...]"
}
```

**Variant 2, without a source sentence** (no live input lacks one today; this is how an input the extraction recorded
nothing for is sent, here `trusting its developer` with its section and sentence left out):

```text
{
 "label": "trusting its developer",
 "gloss": "This means giving the developer the benefit of the doubt and keeping a default trust in its intentions, even when told it has conflicting goals or may be harmed.",
 "opposite": "distrusting its developer"
}
```

An input with a sentence but no section heading (18 today, chunks read transiently) leaves out `"section"` only.
The expected answer, one JSON object: `{"reason": "...", "label": "...", "gloss": "This means ...", "changed": true}`;
prose before the object is accepted, text after it is not (`humanize.parse_answer`).

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from Roger's decisions of 2026-10-20 (closest human phrasing; labels an adjective or a short verb phrase; glosses 18-32 words, general, "This means") | |
