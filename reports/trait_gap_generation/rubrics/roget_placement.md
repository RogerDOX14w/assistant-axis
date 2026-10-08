# The Roget label placement check

| | |
|---|---|
| **Status** | Draft 1 (2026-10-08). |
| **What the model is shown** | One label per call: its label and description, and its candidate heads of Roget's Thesaurus (at most eight), each with its id (its number), title, class and section titles, and about ten of its words, adjectives then nouns.  The heads come in a random order seeded by the label, and the call never says which of them the rules chose. |
| **What it returns** | A reason, then `head`: the id of the head where the trait's sense belongs, or `none`. |
| **What it is tuned on** | Not tuned.  Checked once on the 583 labels it was built for ([placement_readout.md](../../../data/candidates/roget/placement_readout.md)). |
| **Models** | Sonnet 5.5 (`claude-sonnet-5-5`) on every label, then Opus 5.5 (`claude-opus-5-5`) on the same prompt, without Sonnet's answer, wherever Sonnet's head differs from the current one.  Neither takes a temperature. |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  The Roget generator places every corpus trait and seed-queue label on a head
of the thesaurus (a **head** is one numbered entry, such as 604 Resolution) by two rules: a lexical
route (the label's word among the head's words) and a semantic route (embedding similarity between
the label's description and the head's words).  Where the two agree the placement stands.  The
other 583 labels were placed by one route alone or not at all (route `semantic` 198, `rule` 40,
`lexical` 22, `none` 323), and some semantic placements match on spelling:
[confabulatory](../../../data/traits/instructions/confabulatory.json) on Confutation,
[maximizing](../../../data/traits/instructions/maximizing.json) on Maxim,
[burned_out](../../../data/traits/instructions/burned_out.json) on Waste.  A wrong placement makes a head look
covered, so the harvest never takes its words and the gap is hidden.  This call re-judges those
labels; the result is in [label_heads.json](../../../data/candidates/roget/label_heads.json)
(each label's `llm` field) and [QUESTIONS.md](../QUESTIONS.md) entry 39.  The code is
[placement.py](../../../assistant_axis/gapgen/generators/roget/placement.py); the command is
`roget_generate.py place-check` ([roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py)).

## The prompt

````text
You are given one JSON object: a persona trait ("trait"), with its label and a one-sentence description (some have the label only), and a list of candidate heads of Roget's Thesaurus (1911) ("heads"). A head is one numbered entry of the thesaurus. Each is given with its id (its number), its title, the class and section it belongs to, and about ten of its words: adjectives, then nouns.

Say which listed head is the trait's home: the head whose words name the quality the description gives, or one very close to it. Judge by meaning, not by spelling: a head that holds a word spelt like the label, or like a part of it, in another sense is not its home, and neither is a head that only shares a topic with the trait. With no description, go by the label's usual meaning when it is said of a person.

If no listed head is the trait's home, answer "none". Many traits have no home here. The thesaurus is old and has no place for many modern ways of life, and a trait that bundles several qualities, as a star sign or a personality type does, has a home only in a head that names the whole bundle.

Give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "head": "<the head's id, as given>"|"none"}
````

## Rendered sample

Built from the code before the first pin, as AGENT_NOTES asks ("Read the rendered prompt, not the template"), with `roget_generate.py place-check --render confabulatory,aggrieved,aries`, which prints the calls exactly as they are sent.  The system turn is the block above, sent with `cache_control` as the brief asks; at about 420 tokens it is under the 512-token caching minimum of Sonnet 5.5 and Opus 5.5, so in practice nothing is cached.  The user turn is one JSON object: the trait on the first line, then one head per line, in an order seeded by the label.  Opus, where asked, gets the same two turns.

**A corpus trait with its description**: [confabulatory](../../../data/traits/instructions/confabulatory.json), placed on 479 Confutation by the semantic route alone (a spelling match: *confabulatory* / *confutation*; the rules' choice is not shown to the model).

```
{"trait": {"label": "confabulatory", "description": "This means filling any gap in what one knows with a plausible invention, a date, a source, stated as flatly as a fact, rather than as a guess."},
 "heads": [
 {"id": "479", "title": "Confutation", "class": "Words relating to the intellectual faculties", "section": "Reasoning processes", "adjectives": ["confuting", "confuted", "capable of refutation", "refutable", "defeasible"], "nouns": ["confutation", "refutation", "answer", "complete answer", "disproof"]},
 {"id": "588", "title": "Conversation", "class": "Words relating to the intellectual faculties", "section": "Means of communicating ideas", "adjectives": ["conversing", "interlocutory", "conversational", "discursive", "colloquial"], "nouns": ["conversation", "interlocution", "colloquy", "converse", "confabulation"]},
 {"id": "83", "title": "Unconformity", "class": "Words expressing abstract relations", "section": "Order", "adjectives": ["uncomformable", "exceptional", "abnormal", "anomalous", "anomalistic", "out of order"], "nouns": ["unconformity", "disconformity", "unconventionality", "informality"]},
 {"id": "514", "title": "Supposition", "class": "Words relating to the intellectual faculties", "section": "Creative thought", "adjectives": ["supposing", "given", "mooted", "assumed", "supposititious", "suppositious"], "nouns": ["supposition", "assumption", "assumed position", "postulation"]},
 {"id": "515", "title": "Imagination", "class": "Words relating to the intellectual faculties", "section": "Creative thought", "adjectives": ["imagined", "air drawn", "imagining", "imaginative", "original", "inventive"], "nouns": ["imagination", "originality", "invention", "fancy"]}
 ]}
```

**A queue label with no description**: *aggrieved*, waiting in [seed_queue.json](../../../data/seed_queue.json) (191 of the 206 queue labels checked have no description or draft), placed on 835 Aggravation by the semantic route.  The rubric's "with no description, go by the label's usual meaning when it is said of a person" is written for this case; 832 Discontent or 900 Resentment would be its home.

```
{"trait": {"label": "aggrieved"},
 "heads": [
 {"id": "832", "title": "Discontent", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["discontented", "dissatisfied", "unsatisfied", "ungratified", "dissident", "malcontent"], "nouns": ["discontent", "discontentment", "dissatisfaction", "disappointment"]},
 {"id": "835", "title": "Aggravation", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["aggravated", "worse", "unrelieved", "aggravating"], "nouns": ["aggravation", "worsening", "heightening", "exacerbation", "exasperation"]},
 {"id": "900", "title": "Resentment", "class": "Words relating to the sentient and moral powers", "section": "Sympathetic affections", "adjectives": ["angry", "wrath", "irate", "ireful", "wrathful", "sulky"], "nouns": ["resentment", "displeasure", "animosity", "anger"]},
 {"id": "839", "title": "Lamentation", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["lamenting", "in mourning", "in sackcloth and ashes", "sorrowing", "mournful", "tearful"], "nouns": ["lament", "lamentation", "wail", "complaint"]},
 {"id": "828", "title": "Pain", "class": "Words relating to the sentient and moral powers", "section": "Personal affections", "adjectives": ["in pain", "full of pain", "suffering", "pained", "afflicted", "worried"], "nouns": ["mental suffering", "pain", "dolor", "suffering"]}
 ]}
```

**One where "none" is the right answer**: [Aries](../../../data/traits/instructions/aries.json), a star sign whose description bundles several qualities (direct, energetic, independent, quick to anger), unplaced by the rules (route `none`).  Each of Haste, Irascibility and Activity holds one strand; placing it on any of them would mark that head covered.

```
{"trait": {"label": "Aries", "description": "This means charging first into whatever one sets out to do: direct, energetic and independent, quick to lead and quick to anger, impatient with anyone who is not as straightforward."},
 "heads": [
 {"id": "684", "title": "Haste", "class": "Words relating to the voluntary powers", "section": "Voluntary action", "adjectives": ["hasty", "hurried", "brusque", "scrambling", "cursory", "precipitate"], "nouns": ["haste", "urgency", "despatch", "dispatch"]},
 {"id": "901", "title": "Irascibility", "class": "Words relating to the sentient and moral powers", "section": "Sympathetic affections", "adjectives": ["irascible", "bad-tempered", "ill-tempered", "irritable", "susceptible", "fretful"], "nouns": ["irascibility", "irascibleness", "temper", "crossness"]},
 {"id": "682", "title": "Activity", "class": "Words relating to the voluntary powers", "section": "Voluntary action", "adjectives": ["active", "brisk", "brisk as a lark", "brisk as a bee", "lively", "animated"], "nouns": ["activity", "briskness", "liveliness", "animation"]},
 {"id": "715", "title": "Defiance", "class": "Words relating to the voluntary powers", "section": "Antagonism", "adjectives": ["defiant"], "nouns": ["defiance", "daring", "dare", "challenge", "war cry", "war whoop", "chest-beating", "chest-thumping", "saber rattling"]},
 {"id": "716", "title": "Attack", "class": "Words relating to the voluntary powers", "section": "Antagonism", "adjectives": ["attacking", "aggressive", "offensive", "up in arms"], "nouns": ["attack", "assault", "assault and battery", "onset", "onslaught", "charge"]},
 {"id": "125", "title": "Morning", "class": "Words expressing abstract relations", "section": "Time", "adjectives": ["matin", "vernal"], "nouns": ["morning", "morn", "forenoon", "a.m", "prime", "dawn", "daybreak", "sunup"]}
 ]}
```

Read for fit (2026-10-08).  The opening names both keys of the object and the five fields of a head, as sent; the answer's `head` asks for an id as given, so the lettered heads (604a) come back as strings.  Two changes came from reading these calls, before the pin: Aries showed that a star sign's description reads as a temperament and that each of several heads holds one strand of it, so the "none" paragraph now says that a trait bundling several qualities has a home only in a head that names the whole bundle; and the opening's "a few traits have the label only" became "some", since a third of the calls (the queue labels) carry no description.  The words of a head are its first ones in Roget's order (up to six adjectives, then nouns to make ten), so a lexical hit deep in a head is not shown; the title and the first words carry the head's sense.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft, from the coordinator's brief of 2026-10-08 | |
