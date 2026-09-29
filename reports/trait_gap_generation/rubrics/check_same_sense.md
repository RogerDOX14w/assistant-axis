# Check: are two readings one sense or two

| | |
|---|---|
| **Status** | Draft 2: three words in the example readings replaced.  Draft 1 ran in both pilots of the platform.  Part of the pipeline: Roger, 2026-09-29, "yes, let's add it (where needed)".  Asked only when a word has two readings that are both traits or memberships. |
| **What the model is shown** | A label and two of its primary readings, both of which the kind call took for a trait or a membership. |
| **What it returns** | Whether the two readings are the same way of being, two shades of one, or two different ones. |
| **What it is tuned on** | Not tuned.  Run on the 30 test words that have two such readings; results in [sense_call_probe.md](../sense_call_probe.md). |
| **Model** | Haiku 4.5, temperature 0, one item per call |

Part of the split Roger proposed on 2026-09-29: small calls, each with its own rubric, tuned one at a
time.  The index is [README.md](./README.md).

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.

**What it is for.**  Step 1 is asked for the one or two readings most readers would arrive at, and it
often gives one sense in two wordings.  Without this check the pipeline cannot tell a word with two
senses from a word whose one sense was said twice.  With it, the note `two_trait_senses` would be set
only on the answer "different", which is case 2 of Roger's four cases in
[decisions_m1.md](../decisions_m1.md).

## The prompt

````text
Each item gives a label and two readings of the instruction "You are <label>." as said of a persona. Say whether the two readings are one way of being or two.

- "same": the two readings say one thing in different words. A persona that fits one fits the other. "You are chatty." read as "you talk a lot" and as "you are fond of idle conversation" is like that.
- "shade": one way of being, seen from two sides or at two strengths. A persona that fits one would usually fit the other. "You are breezy." read as "you are chipper and relaxed" and as "you are informal and offhand" is like that.
- "different": two separate ways of being. A persona could fit one and not the other, and a reader would have to be told which is meant. "You are salty." read as "you are irritable and embittered" and as "your language is coarse" is like that.

For each item give a reason in one short sentence, then the answer.

Respond with one JSON object and nothing else, reason first:
{"results": [{"id": <int>, "reason": "<one short sentence>", "relation": "same"|"shade"|"different"}]}
Return one row per id, in the order given.
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Fable | First draft | The three example words were checked to be absent from the corpus, the queue, the validation file, the test words and the decisions file |
| 2 | Fable | In the example readings, "casual conversation" became "idle conversation", "cheerful" became "chipper", "casual" became "informal" and "resentful" became "embittered" | My fault in draft 1: I checked the three example labels and not the words inside their readings, and cheerful, casual and resentful are corpus labels.  The build agent's hygiene test caught it (question 22 in [QUESTIONS.md](../QUESTIONS.md)).  Roger, 2026-09-30: replace them, and "use near-dupes of corpus terms".  The four new words were checked against the corpus, the queue, the validation file, the test words and the decisions file |
