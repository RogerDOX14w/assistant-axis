# The IPIP cluster naming call, hinted

| | |
|---|---|
| **Status** | Draft 1 (2026-10-11), pinned as version 1.  The twin of [ipip_naming_blind.md](./ipip_naming_blind.md): the same text but for its first two paragraphs, which add the questionnaire scales.  Not yet run. |
| **What the model is shown** | One cluster pole per call: up to 30 of its IPIP item statements as first-person sentences, **and** the scales they are scored on — each with its inventory, its direction (`for` / `against`) and how many of the pole's statements it scores. |
| **What it returns** | The same fields as the blind form: a reason, then `label`, `gloss`, `antonym_label`, `antonym_gloss`, `kind`, `ambiguity_flag`, `single_word_exists`. |
| **What it is tuned on** | Not tuned.  The pilot runs it beside the blind form on the same 40 seeded clusters per granularity; the disagreement rate is a readout column and a review flag, not a gate. |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); no temperature; about 1,090 tokens, over Haiku 5.5's 512-token minimum, so it is sent cached (measured 2026-10-11). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin
(`rubric_pins.py bump ipip_naming_hinted`).  **The two texts are meant to stay identical but for the
scale paragraphs**: an edit to one almost always belongs in the other, and
`test_gapgen_ipip_naming.py` checks that the parts after the opening paragraphs still match.

**What it is for.**  Both names are generated for every pole, and the blind one is submitted
(QUESTIONS 47, Roger 2026-10-11: hinted names come from the taxonomy vocabulary the censuses and the Roget scan
have already swept, so they collide with corpus names more often, and a collision is a "covered" verdict — the
silent error).  The hinted name travels beside it in the cluster table, the readout and `roger_sample.md`, and a
blind/hinted disagreement is a review flag.  The code is
[naming.py](../../../assistant_axis/gapgen/generators/ipip/naming.py) (`build_hinted_user`, `scales_for`); the
command is `ipip_generator.py name --granularity G --hinted`.

**Why the scale names are a hint and not an answer.**  A pole's constructs come from the key signs
(QUESTIONS 52: IPIP's own 21 key pages, with Tedone's workbook as a check), so they say what the questionnaire's
authors meant a group of items to measure — which is not always what the items a clustering put together actually
say.  The paragraph therefore tells the model to name what the statements indicate and to use a scale's name only
where it fits them.  The direction matters just as much: the negatively keyed side of a scale is the *opposite* of
the scale's name, and a pole made of those items must be named accordingly, which is why the direction is given
in words ("for" / "against") rather than as `+` and `-`.

**Why `is_trait` is gone, and why `kind` replaces it:** the same reasons as in the blind form, written out in
[ipip_naming_blind.md](./ipip_naming_blind.md) (QUESTIONS 48, Roger 2026-10-11).  The kind definitions are
abridged from [step2_kind.md](./step2_kind.md) draft 6, and M1's are the verdicts of record.

## The prompt

````text
You are given one JSON object holding a group of self-report statements from a personality questionnaire ("statements") and the questionnaire scales they are scored on ("scales"). People rated how well each statement describes them, and these statements were grouped because they express closely related behavior. Name the one standing thing about a person that the group indicates.

Each scale is given with its inventory, its direction ("for": agreeing with the statements raises the scale's score; "against": agreeing lowers it) and how many of the statements it scores. Treat the scale names as hints to what the questionnaire's authors meant to measure: name what the statements themselves indicate, using a scale's name only where it fits them.

The statements are habitual self-report: each one is something a person says is generally true of them, not something that happened to them once. Read the group for what someone it fits is like over time. Where the statements report a momentary feeling ("I often feel downcast", "I am filled with doubts"), name the predisposition behind it, being prone to feel that way, rather than declining to name anything.

Name whatever the group indicates, and do not hold back because what you find is not a disposition of character. A lasting way of feeling, thinking, acting or relating to others is the commonest case, but a group may instead indicate an ability or a skill, a taste or a pursuit, a conviction or an allegiance, a standing fact of someone's life such as their money, housing, work or health, or a lasting feature of the body. All of these are named the same way, and the "kind" field below is where you say which of them you take it to be.

Give:
- "reason": one short sentence on what the statements have in common.
- "label": the name of what the group indicates, in 1 to 4 lowercase words: an adjective or adjective phrase where English has one (for example "punctilious" or "slow to anger"), otherwise a short descriptive phrase (for example "keeps others at arm's length").
- "gloss": one sentence of at most 25 words that starts "This means" and describes it in plain words, without repeating the label.
- "antonym_label": the name of the opposite, in the same form, or null if it has no clear opposite.
- "antonym_gloss": one sentence starting "This means" that describes the opposite, or null.
- "kind": your best guess at what sort of thing you have named, one of these:
  - "trait": a standing disposition, habit, style, stance or inclination: how someone tends to think, feel, relate, speak, value or decide. An inclination to do something counts however rare or disapproved of, and so does a standing practice of doing it.
  - "membership": a standing fact of someone's life that others use to say who they are, and that combines freely with any profession: housing, money, work pattern, class, family, a hobby or taste, a relationship, an orientation, where they live, a nationality, an age group, a religion.
  - "state": a condition someone is in for a while, from moments to weeks, of mood, of body, of appearance or of situation: how someone is just now rather than how they are generally.
  - "physical": a lasting feature of someone's body that has little or no effect on how they act or talk.
  - "role": an identity big enough to organize a whole persona, so that someone has only one: a profession or calling, an office, a rank.
  - "action": a single deed or event rather than a practice someone keeps up, or a property of acts rather than of the people who do them.
  - "evaluative": pure praise or blame, which says how the speaker feels about the person and nothing about what the person does.
  - "not_a_persona": something that says nothing about how a person would act, think or speak.
- "ambiguity_flag": true if the statements do not share one thing, or if the label could easily be read in another sense.
- "single_word_exists": true if one common English word names this well.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "label": "<1-4 lowercase words>", "gloss": "This means ...", "antonym_label": "<1-4 lowercase words>" or null, "antonym_gloss": "This means ..." or null, "kind": "trait"|"membership"|"state"|"physical"|"role"|"action"|"evaluative"|"not_a_persona", "ambiguity_flag": true or false, "single_word_exists": true or false}
````

## Rendered sample

A call is the block above as the system turn, **byte for byte**, and one line as the user turn, built by
`naming.build_hinted_user` as `json.dumps({"statements": [...], "scales": [...]})`, the scales most-scored first.
Every scale name passes through `prompt_label`, so an instrument's long form would arrive as the judge display
form and `label_form` is recorded on every call; IPIP construct names are plain, so it is a no-op here.

Three user turns: a unipolar cluster whose two inventories agree, the negatively keyed pole of a bipolar cluster
(the case the direction wording exists for), and a cluster the clustering put together across three scales that do
not obviously name one thing — where the instruction to use a scale name "only where it fits" has to do some work.

````text
{"statements": ["I get chores done right away.", "I like to tidy up.", "I love order and regularity.", "I do things according to a plan."], "scales": [{"scale": "Orderliness", "inventory": "NEO", "direction": "for", "statements": 4}, {"scale": "Diligence", "inventory": "HEX", "direction": "for", "statements": 2}]}
{"statements": ["I keep in the background.", "I have little to say.", "I don't like to draw attention to myself.", "I find it difficult to approach others."], "scales": [{"scale": "Friendliness", "inventory": "NEO", "direction": "against", "statements": 4}, {"scale": "Gregariousness", "inventory": "AB5C", "direction": "against", "statements": 2}]}
{"statements": ["I rent the place I live in.", "I have trouble paying the rent.", "I worry about money at the end of the month."], "scales": [{"scale": "Anxiety", "inventory": "CAT-PD", "direction": "for", "statements": 1}, {"scale": "Prudence", "inventory": "HPI", "direction": "against", "statements": 1}]}
````

A plausible answer to the second of those turns, as the parser receives it — note that the label is the opposite of
the scale name, because the direction is `against`:

````text
{"reason": "Every statement is about holding back from company and attention, and all are keyed against outgoing scales.", "label": "retiring", "gloss": "This means staying quiet and out of the spotlight, and finding it hard to make the first move with people.", "antonym_label": "outgoing", "antonym_gloss": "This means seeking out company and attention, and starting conversations easily.", "kind": "trait", "ambiguity_flag": false, "single_word_exists": true}
````

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft in this file, from the in-code `HINTED_PROMPT` (pinned in `naming.py` by sha256 `e33a08e9...`), with the same rewrite as the blind form: the narrow trait definition and `is_trait` replaced by "the one standing thing about a person that the group indicates", the habitual-self-report and predisposition paragraph, and `kind` in M1's eight-way vocabulary.  The scale paragraph is unchanged | Roger, 2026-10-11 (QUESTIONS 48, "1-3 SG"): `is_trait` stops being a submission gate, the definition excluded things the corpus contains, and the two naming prompts join the pinned set |
