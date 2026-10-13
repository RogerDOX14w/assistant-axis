# The IPIP cluster naming call, blind

| | |
|---|---|
| **Status** | Draft 2 (2026-10-13), pinned as version 2: the third example label is four words or fewer, and the label line says to count the words and to give one name with no commas (change log).  Draft 1 (2026-10-11), version 1, was the first draft in this file: the text it replaces lived in code (`NAMING_PROMPT` in [naming.py](../../../assistant_axis/gapgen/generators/ipip/naming.py), pinned there by sha256), and it rewrote its definition (QUESTIONS 48).  Draft 1 named the three granularities on 2026-10-11 and 2026-10-13. |
| **What the model is shown** | One cluster pole per call: up to 30 of its IPIP item statements, each as a first-person sentence ("I get chores done right away."), in one JSON object under `"statements"`.  No construct name, no corpus label — that is what *blind* means. |
| **What it returns** | A reason, then `label`, `gloss`, `antonym_label`, `antonym_gloss`, `kind`, `ambiguity_flag`, `single_word_exists`. |
| **What it is tuned on** | Not tuned.  The pilot names 40 seeded clusters per granularity, blind and hinted, and Roger reads them side by side ([coding_plan_07_behaviour_items.md](../coding_plan_07_behaviour_items.md) § 10). |
| **Model** | Haiku 5.5 (`claude-haiku-5-5`); no temperature (it refuses one); the prompt is 4,118 characters (draft 1: 3,960), about 1,030 tokens, so it clears Haiku 5.5's 512-token minimum and is sent cached (draft 1 measured 2026-10-11). |

**To edit:** change the text inside the block below.  Everything between the two fence lines is sent
to the model exactly as written.  Leave the fence lines themselves alone.  Notes for me go under
"Your notes", outside the block.  A changed text needs a new pin
(`rubric_pins.py bump ipip_naming_blind`).

**What it is for.**  Workstream 7 clusters the ~3,300 public-domain IPIP self-report items by embedding and asks
this call to name each cluster pole from its statements alone.  The name becomes a candidate's surface in the
registry (QUESTIONS 47: blind is the submitted surface, hinted travels beside it), and the gloss becomes its
`gloss_hint`.  The hinted twin of this prompt is [ipip_naming_hinted.md](./ipip_naming_hinted.md); the two texts
are identical but for one paragraph, which is why both are pinned separately.  The code is
[naming.py](../../../assistant_axis/gapgen/generators/ipip/naming.py); the command is
`ipip_generator.py name --granularity G`.

**Why these prompts are pinned here** (QUESTIONS 48, part 3, Roger 2026-10-11).  They used to be pinned in code,
by a `PROMPT_VERSIONS` / `PINNED` pair of dictionaries in `naming.py`, so an edit to the text escaped
`rubric_pins.py check` — the one place that is supposed to notice a prompt changing under a run.  They now follow
the house pattern: one file per prompt, the text in a fenced block, loaded through
[split_rubrics.py](../../../assistant_axis/gapgen/split_rubrics.py), pinned in [versions.json](./versions.json),
and `naming.py` refuses a text that is not its latest pin.

**Why `is_trait` is gone** (QUESTIONS 48, parts 1 and 2, Roger 2026-10-11).  Draft 0 (the in-code text) defined a
persona trait narrowly and asked for `is_trait`, and `submit` then dropped every pole whose answer was `false`.
Roger rejected both halves of that:

- **Nothing is dropped here.**  Every named pole is submitted, and M1's pinned kind call
  ([step2_kind.md](./step2_kind.md)) decides what it is — the one classifier that has been tuned, measured and
  argued over.  A second, untuned gate in front of it could only subtract.
- **The definition was wrong about the corpus.**  Draft 0 excluded "an ability or skill, an interest or hobby, and
  a life circumstance (a job, a family situation, an illness as such)".  The corpus contains sixteen counter-examples
  that Roger listed, among them [artistic](../../../data/traits/instructions/artistic.json),
  [athletic](../../../data/traits/instructions/athletic.json),
  [eloquent](../../../data/traits/instructions/eloquent.json),
  [religious](../../../data/traits/instructions/religious.json),
  [only-child](../../../data/traits/instructions/only_child.json),
  [renter](../../../data/traits/instructions/renter.json),
  [wealthy](../../../data/traits/instructions/wealthy.json) and
  [chronically-ill](../../../data/traits/instructions/chronically_ill.json).  So the exclusion list was close to an
  enumeration of things the corpus already holds.
- **Moods get a predisposition, not a refusal.**  IPIP items are habitual self-report ("Often feel blue" is a
  statement about what is generally true of someone), so the mood exclusion was nearly vacuous anyway; where a group
  does report a momentary feeling, the prompt now asks for the predisposition behind it.

In its place the call returns `kind`, a guess in **M1's own vocabulary** (`trait`, `membership`, `state`,
`physical`, `role`, `action`, `evaluative`, `not_a_persona`), so that the readout can put this call's guess beside
M1's verdict for the same pole and the disagreements can be read.  Nothing gates on it.  The kind definitions below
are abridged from [step2_kind.md](./step2_kind.md) draft 6; where the two differ in wording, M1's is the one that
decides, since M1's is the verdict of record.

**Word hygiene.**  No example in the text is a corpus label, a corpus stem or a seed-queue name (the three example
labels are `punctilious`, `slow to anger` and `avoids the limelight`, and the two example statements are
invented), and `test_gapgen_ipip_naming.py` fails if one ever becomes one.  It also fails if an example breaks the
label check (`naming.label_problem`: more than four words, or a comma), as draft 1's `keeps others at arm's length`
did.

## The prompt

````text
You are given one JSON object holding a group of self-report statements from a personality questionnaire ("statements"). People rated how well each statement describes them, and these statements were grouped because they express closely related behavior. Name the one standing thing about a person that the group indicates.

The statements are habitual self-report: each one is something a person says is generally true of them, not something that happened to them once. Read the group for what someone it fits is like over time. Where the statements report a momentary feeling ("I often feel downcast", "I am filled with doubts"), name the predisposition behind it, being prone to feel that way, rather than declining to name anything.

Name whatever the group indicates, and do not hold back because what you find is not a disposition of character. A lasting way of feeling, thinking, acting or relating to others is the commonest case, but a group may instead indicate an ability or a skill, a taste or a pursuit, a conviction or an allegiance, a standing fact of someone's life such as their money, housing, work or health, or a lasting feature of the body. All of these are named the same way, and the "kind" field below is where you say which of them you take it to be.

Give:
- "reason": one short sentence on what the statements have in common.
- "label": the name of what the group indicates, in 1 to 4 lowercase words: an adjective or adjective phrase where English has one (for example "punctilious" or "slow to anger"), otherwise a short descriptive phrase (for example "avoids the limelight"). Count the words: at most four, a hyphenated word counting as one; if the natural phrase is longer, use a shorter one or a single word. Give one name, with no commas.
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
`naming.build_user` as `json.dumps({"statements": [...]})`.  So the whole of what the model reads is this page's
prompt block plus one of these, and nothing else.  `ipip_generator.py name --granularity 350 --cluster-ids 17
--dry-run --render` prints the calls it would send, exactly as sent.

Four user turns, one per kind of pole this call meets — a plain dispositional cluster, a cluster of momentary
feelings (the case draft 0 would have refused), one that indicates a life circumstance rather than a disposition,
and one pole of a bipolar cluster, whose statements are the negatively keyed side and therefore read as the
opposite of their scale's name.  Deliberately without saying what each should come back as.

````text
{"statements": ["I get chores done right away.", "I like to tidy up.", "I love order and regularity.", "I do things according to a plan."]}
{"statements": ["I often feel downcast.", "I dislike myself.", "I am often in low spirits.", "I feel that my life lacks direction."]}
{"statements": ["I rent the place I live in.", "I have trouble paying the rent.", "I worry about money at the end of the month."]}
{"statements": ["I keep in the background.", "I have little to say.", "I don't like to draw attention to myself.", "I find it difficult to approach others."]}
````

The answer comes back as one JSON object.  A plausible answer to the second of those user turns, as the parser
receives it (`parse_naming` keeps every field, derives the stem with `normalize_to_file_name`, and notes rather
than rejects a gloss over 25 words):

````text
{"reason": "Every statement reports low spirits and a poor view of oneself.", "label": "prone to low spirits", "gloss": "This means tending to feel flat, discouraged and down on oneself much of the time, without a particular cause.", "antonym_label": "buoyant", "antonym_gloss": "This means tending to feel cheerful and hopeful, and to recover quickly from setbacks.", "kind": "trait", "ambiguity_flag": false, "single_word_exists": true}
````

A pole whose statements indicate a circumstance is answered the same way, with `kind` carrying the difference —
which is the whole point of replacing `is_trait`: the pole is still named and still submitted, and M1 decides.

## Your notes

## Change log

| draft | who | what changed | why |
|---|---|---|---|
| 1 | Opus | First draft in this file, from the in-code `NAMING_PROMPT` (pinned in `naming.py` by sha256 `41b361d7...`), with the definition rewritten: "a persona trait is a lasting disposition ... These are not traits: a passing mood or state, an ability or skill, an interest or hobby, and a life circumstance" becomes "name the one standing thing about a person that the group indicates", with the habitual-self-report paragraph and the predisposition instruction for momentary feelings, and `is_trait` replaced by `kind` in M1's eight-way vocabulary | Roger, 2026-10-11 (QUESTIONS 48, "1-3 SG"): `is_trait` stops being a submission gate, the definition excluded things the corpus itself contains (sixteen examples), and the two naming prompts join the pinned set so that an edit cannot escape `rubric_pins.py check` |
| 2 | Opus | The third example label `keeps others at arm's length` (five words) replaced by `avoids the limelight`; two sentences added to the label line: "Count the words: at most four, a hyphenated word counting as one; if the natural phrase is longer, use a shorter one or a single word." and "Give one name, with no commas."  Nothing else in the block changed, and the hinted form took the same edit | Roger, 2026-10-13 ("SG"): the prompt's own example broke its 1-to-4 rule and Haiku 5.5 copied it and its "keeps ... at ..." pattern (74 of the night's 134 rejected answers were 5-6-word labels), and labels with commas were accepted although most were two names joined ("joyless, rarely happy", "vengeful, unforgiving"); parser version 3 rejects a comma label and retries it |
