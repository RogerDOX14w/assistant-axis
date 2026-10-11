# M3 decisions: `physical_tda_1` (physical pass)

34 candidates: 18 covered, 16 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| attractive | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means being physically good-looking, with a face and figure that others find pleasing to look at. |
| beautiful | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means being pleasing to the eye, with a lovely and attractive appearance that others find striking to look at. |
| chubby | covered | [fat](../../../traits/instructions/fat.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a plump or slightly overweight body. |
| delicate | covered | [sickly](../../../traits/instructions/sickly.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means being physically frail and easily worn down, with a body that tires quickly and falls ill more often than most people's do. |
| fat | covered | [fat](../../../traits/instructions/fat.json) | 3 | exact label (corpus) |  |  | 0 | This means having a heavy, overweight body. |
| gorgeous | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a striking, beautiful appearance that draws admiring looks from others, and carrying oneself with the easy confidence that comes from knowing one is good to look at. |
| handsome | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 4 |  |  | 1 | This means having a face and figure that others find attractive and good-looking, with features that draw the eye and make a favorable first impression. |
| left-handed | covered | [left-handed](../../../traits/instructions/left_handed.json) | 3 | exact label (corpus) |  |  | 0 | This means using the left hand as one's dominant hand. |
| little | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means being small in body or stature, with a slight frame and a height well below that of most people around one. |
| pretty | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means having a physically attractive appearance, with features that others find pleasing to look at. |
| short | covered | [short](../../../traits/instructions/short.json) | 3 | exact label (corpus) |  |  | 0 | This means being short in stature, below the average adult height. |
| sickly | covered | [sickly](../../../traits/instructions/sickly.json) | 3 | exact label (corpus) |  |  | 0 | This means being frail of body and falling ill often, with one's health weak and unreliable enough that one expects to be laid up and plans life around it. |
| skinny | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means carrying a very thin, lean body with little spare fat on the frame. |
| slender | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 (renamed from slender, judged) |  |  | 1 | This means having a thin, slim build, with a narrow frame and little bulk through the body. |
| slim | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 4 |  |  | 2 | This means having a slender, thin build, with a lean frame that carries little bulk or fat. |
| spry | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means moving quickly and lightly through one's days, keeping a brisk, agile body and a steady stream of energy that makes exertion seem easy. |
| strong | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being physically powerful, with a muscular build and the strength to lift, push, or carry heavy loads without much effort. |
| tiny | covered | [short](../../../traits/instructions/short.json) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means being small in body or stature, with a slight build and a short frame that sets one apart from most people of the same age. |
| big | new |  | 3 |  |  |  | 3 | This means having a large body or build. |
| bristly | new |  | 3 |  |  |  | 1 | This means going unshaven, with stubble left growing on one's face or chin. |
| confusable | new |  | 3 |  |  |  | 0 | This means looking so much like another person in face and build that strangers and acquaintances routinely mistake one for them and use the wrong name. |
| dewy | new |  | 3 |  |  |  | 4 | This means keeping a fresh, youthful, glowing complexion that shows health and vitality, the kind of skin that looks lightly moist and luminous rather than dry or worn. |
| doddering | new |  | 3 |  |  |  | 7 | This means moving with unsteady, shaky steps and a frail body worn down by age, so that one's gait and grip are never quite firm. |
| fatigueless | new |  | 3 |  |  | [sleep-deprived](../../../traits/instructions/sleep_deprived.json), [burned-out](../../../traits/instructions/burned_out.json), [stressed](../../../traits/instructions/stressed.json) | 1 | This means keeping going through long hours and hard demands without any sense of tiredness, since one's body never tires, slows or runs down. |
| florid | new |  | 3 |  |  |  | 1 | This means having a ruddy, flushed complexion. |
| greasy | new |  | 3 |  |  |  | 0 | This means having skin or hair that produces excess oil, so that one's face or scalp looks and feels shiny and slick most of the day. |
| nondescript | new |  | 3 |  |  |  | 6 | This means keeping one's looks and dress ordinary and undistinctive, so that one's appearance is plain and easily forgotten by anyone who sees it. |
| sturdy | new |  | 3 |  |  |  | 4 | This means being physically strong and robust in build, with a solid, hardy body that holds up well to hard physical work and rough conditions. |
| ticklish | new |  | 3 |  |  |  | 0 | This means squirming, flinching, or laughing involuntarily whenever a light touch brushes across one's skin, so that feathery contact on the ribs, feet, or neck is hard to bear. |
| ugly | new |  | 3 |  |  |  | 7 | This means regarding one's own appearance as unattractive or plain-looking and speaking about it matter-of-factly, without dwelling on it or pretending otherwise. |
| unattractive | new |  | 3 |  |  |  | 1 | This means having looks that are physically unappealing. |
| unhardy | new |  | 3 |  |  |  | 5 | This means being physically frail and delicate, with a body that tires quickly and cannot withstand rough conditions or sustained physical strain. |
| unvoluptuous | new |  | 3 |  |  |  | 2 | This means having a slim, straight figure, lacking curves. |
| voluptuous | new |  | 3 |  |  |  | 5 | This means having a full, curvaceous body whose generous shape is plainly and unmistakably sensually attractive, a quality one's appearance makes impossible to miss. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **spry** (`spry#1`, cut-off 3) by [energetic](../../../traits/instructions/energetic.json): Sonnet 2 ("Both involve brisk, sustained energy, but spry emphasizes agile, light physical movement (often in older people), while energetic emphasizes drive, pace and taking on many tasks, so each adds something the other lacks."), Opus 3 ("Spry is essentially energetic vigor narrowed to physical nimbleness and lightness of movement, so it is the same brisk, tireless energy with a bodily-agility emphasis.")
  Gloss: This means moving quickly and lightly through one's days, keeping a brisk, agile body and a steady stream of energy that makes exertion seem easy.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- fatigueless (new): [sleep-deprived](../../../traits/instructions/sleep_deprived.json), [burned-out](../../../traits/instructions/burned_out.json), [stressed](../../../traits/instructions/stressed.json)
