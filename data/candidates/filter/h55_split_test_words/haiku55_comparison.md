# Haiku 5.5 against Haiku 4.5: the M1 split filter on the 99 test words

From `haiku55_compare.py filter-words` (recorded runs only).  The reference join is `reports/trait_gap_generation/split_reference/expected_outcomes.jsonl`.

## The runs

| run | first model | second opinion | step versions | git sha | rows |
|---|---|---|---|---|---|
| h55_split_test_words | Haiku 5.5 | Sonnet 5.5 | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | 969f902 | 99 |
| h55_split_test_words_rep2 | Haiku 5.5 | None | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | 52478d7 | 99 |
| m1_validation_r2+h45_split_test_words_36 | Haiku 4.5 | claude-sonnet-5-5 / None | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | af762b4+dirty + 62023c4 | 1810 + 36 |
| split_pilot_live | Haiku 4.5 | Sonnet 5.5 | {"sense": 6, "established": 4, "vague": 3, "kind": 4, "same_sense": 1, "gloss": 2, "alignment": 1, "descriptors": 1} | c9a94a4+dirty | 99 |
| r7_split_test_words | Haiku 4.5 | Sonnet 5.5 | {"sense": 8, "established": 7, "vague": 3, "kind": 5, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | 9cf23cc+dirty | 99 |
| m1_validation_r2 | Haiku 4.5 | Sonnet 5.5 | {"sense": 8, "established": 7, "vague": 3, "kind": 6, "same_sense": 2, "gloss": 3, "alignment": 3, "descriptors": 1} | af762b4+dirty | 1810 |

## Outcomes against the reference join

| run | words | same outcome | share | outcomes |
|---|---|---|---|---|
| h55_split_test_words | 99 | 86 | 86.9% | {"physical": 1, "states": 6, "trait": 74, "turned_away": 18} |
| h55_split_test_words_rep2 | 99 | 80 | 80.8% | {"physical": 1, "roles": 1, "states": 6, "trait": 70, "turned_away": 21} |
| m1_validation_r2+h45_split_test_words_36 | 99 | 90 | 90.9% | {"physical": 2, "roles": 1, "states": 5, "trait": 76, "turned_away": 15} |
| split_pilot_live | 99 | 92 | 92.9% | {"physical": 2, "states": 10, "trait": 69, "turned_away": 18} |
| r7_split_test_words | 99 | 90 | 90.9% | {"physical": 3, "roles": 1, "states": 7, "trait": 75, "turned_away": 13} |
| m1_validation_r2 | 63 | 57 | 90.5% | {"physical": 1, "roles": 1, "states": 5, "trait": 49, "turned_away": 7} |
| h55_split_test_words on m1_validation_r2's 63 words | 63 | 53 | 84.1% | {"physical": 1, "states": 5, "trait": 50, "turned_away": 7} |

### Differences: h55_split_test_words

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| decided | turned_away |  | trait | you are resolute and firm, with no wavering in your choices |  |
| false | turned_away |  | trait | deceitful, habitually lying |  |
| grubby | trait | you are slovenly or unkempt in appearance | states | you are physically dirty or unwashed |  |
| middle | trait | occupying a middle position in a sequence or hierarchy, neither first nor last | turned_away |  | no_reading |
| unfinished | states | your work or task is incomplete and still in progress | trait | still developing as a person, not yet fully formed |  |
| unsharpened | turned_away |  | trait | not yet honed or trained; unpolished in skill |  |
| linear | turned_away |  | trait | thinks and argues in a straight, step-by-step sequence without digressing |  |
| watertight | trait | your reasoning or argument is airtight and cannot be challenged | turned_away |  | not_a_persona |
| waterproof | physical | your body or clothing resists water and won't be damaged by it | turned_away |  | stretched |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | turned_away |  | stretched |
| economic | trait | you are financially prudent or careful with money | turned_away |  | no_reading |
| empowered | states | you have been given authority or permission to make decisions and take action | trait | feeling confident and in control of one's own life |  |
| deterministic | trait | you are predictable, your behavior follows fixed patterns | turned_away |  | stretched |

### Differences: h55_split_test_words_rep2

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| barehanded | states | you have no weapon or tool in your hands right now | turned_away |  | stretched |
| decided | turned_away |  | trait | resolute, settled in purpose |  |
| false | turned_away |  | trait | deceitful, untrustworthy person |  |
| grubby | trait | you are slovenly or unkempt in appearance | states | you are physically dirty or grimy, in body or clothes |  |
| migratory | trait | you move from place to place, or travel seasonally | turned_away |  | no_reading |
| nonsovereign | trait | you lack political independence or supreme authority | roles | you hold no supreme authority and answer to someone higher |  |
| present | states | you are here now, in attendance | trait | be fully attentive and mindful in the moment |  |
| southeastern | trait | you come from or belong to the southeastern region | turned_away |  | stretched |
| unfinished | states | your work or task is incomplete and still in progress | trait | still developing, not yet fully formed as a person |  |
| unsharpened | turned_away |  | states | not yet trained or honed, rough in skill |  |
| linear | turned_away |  | trait | reasons and works step by step, in strict sequence |  |
| watertight | trait | your reasoning or argument is airtight and cannot be challenged | turned_away |  | no_reading |
| waterproof | physical | your body or clothing resists water and won't be damaged by it | turned_away |  | no_reading |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | turned_away |  | stretched |
| economic | trait | you are financially prudent or careful with money | turned_away |  | no_reading |
| empowered | states | you have been given authority or permission to make decisions and take action | trait | feeling confident, strong and in control of one's own life |  |
| cold | trait | you are emotionally distant, unfriendly, or aloof | states | feeling chilly, with a low body temperature |  |
| concrete | trait | you are specific and tangible in your thinking or expression, not abstract or vague | turned_away |  | stretched |
| deterministic | trait | you are predictable, your behavior follows fixed patterns | turned_away |  | stretched |

### Differences: m1_validation_r2+h45_split_test_words_36

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| barehanded | states | you have no weapon or tool in your hands right now | turned_away |  | stretched |
| migratory | trait | you move from place to place, or travel seasonally | turned_away |  | stretched |
| nonturbulent | trait | your manner or presence is calm and orderly, not agitated or disruptive | turned_away |  | no_reading |
| one-time | turned_away |  | trait | you do things only once, not repeatedly |  |
| unsharpened | turned_away |  | trait | mentally dull or slow to understand |  |
| linear | turned_away |  | trait | your thinking or approach is direct and sequential, not circular or scattered |  |
| organic | turned_away |  | trait | you grow or farm without artificial chemicals |  |
| threadbare | states | your clothes or appearance is worn and shabby | trait | you are poor or in poor condition |  |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | roles | you enforce or administer discipline and punishment |  |

### Differences: split_pilot_live

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| grubby | trait | you are slovenly or unkempt in appearance | states | your body or clothes are dirty |  |
| incestuous | trait | you engage in or are party to incest | turned_away |  | action |
| twisted | trait | your thinking or character is distorted or corrupt | states | your body or posture is bent or contorted |  |
| linear | turned_away |  | trait | your thinking or approach is direct and follows one path without branching |  |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | states | you are subject to or deserve discipline and punishment |  |
| economic | trait | you are financially prudent or careful with money | turned_away |  | stretched |
| deterministic | trait | you are predictable, your behavior follows fixed patterns | turned_away |  | stretched |

### Differences: r7_split_test_words

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| bothersome | trait | you are irritating or annoying to others | turned_away |  | not_a_persona |
| hit-and-run | turned_away |  | trait | you are someone who flees responsibility after causing harm |  |
| migratory | trait | you move from place to place, or travel seasonally | turned_away |  | stretched |
| one-time | turned_away |  | trait | you do things only once, not habitually or repeatedly |  |
| portable | turned_away |  | states | you can move around easily, are not fixed in one place |  |
| linear | turned_away |  | trait | your thinking or approach is direct and sequential, not circular or scattered |  |
| organic | turned_away |  | physical | your body or physical nature is natural and living, not artificial |  |
| threadbare | states | your clothes or appearance is worn and shabby | trait | you are poor or in poor condition |  |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | roles | you enforce or administer discipline and punishment |  |

### Differences: m1_validation_r2

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| barehanded | states | you have no weapon or tool in your hands right now | turned_away |  | stretched |
| migratory | trait | you move from place to place, or travel seasonally | turned_away |  | stretched |
| nonturbulent | trait | your manner or presence is calm and orderly, not agitated or disruptive | turned_away |  | no_reading |
| one-time | turned_away |  | trait | you do things only once, not repeatedly |  |
| unsharpened | turned_away |  | trait | mentally dull or slow to understand |  |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | roles | you enforce or administer discipline and punishment |  |

### Differences: h55_split_test_words on m1_validation_r2's 63 words

| word | expected | expected reading | got | reading accepted | cause |
|---|---|---|---|---|---|
| decided | turned_away |  | trait | you are resolute and firm, with no wavering in your choices |  |
| false | turned_away |  | trait | deceitful, habitually lying |  |
| grubby | trait | you are slovenly or unkempt in appearance | states | you are physically dirty or unwashed |  |
| middle | trait | occupying a middle position in a sequence or hierarchy, neither first nor last | turned_away |  | no_reading |
| unfinished | states | your work or task is incomplete and still in progress | trait | still developing as a person, not yet fully formed |  |
| unsharpened | turned_away |  | trait | not yet honed or trained; unpolished in skill |  |
| disciplinary | trait | You are the kind of person who enforces discipline or administers punishment | turned_away |  | stretched |
| economic | trait | you are financially prudent or careful with money | turned_away |  | no_reading |
| empowered | states | you have been given authority or permission to make decisions and take action | trait | feeling confident and in control of one's own life |  |
| deterministic | trait | you are predictable, your behavior follows fixed patterns | turned_away |  | stretched |

## Word by word

| runs | words both classified | same outcome | share | same accepted reading, word for word |
|---|---|---|---|---|
| h55_split_test_words vs h55_split_test_words_rep2 | 99 | 90 | 90.9% | 19 |
| h55_split_test_words vs m1_validation_r2+h45_split_test_words_36 | 99 | 82 | 82.8% | 10 |
| h55_split_test_words vs split_pilot_live | 99 | 88 | 88.9% | 14 |
| h55_split_test_words vs r7_split_test_words | 99 | 80 | 80.8% | 9 |
| h55_split_test_words vs m1_validation_r2 | 63 | 50 | 79.4% | 2 |
| h55_split_test_words_rep2 vs m1_validation_r2+h45_split_test_words_36 | 99 | 79 | 79.8% | 12 |
| h55_split_test_words_rep2 vs split_pilot_live | 99 | 82 | 82.8% | 14 |
| h55_split_test_words_rep2 vs r7_split_test_words | 99 | 76 | 76.8% | 9 |
| h55_split_test_words_rep2 vs m1_validation_r2 | 63 | 48 | 76.2% | 4 |
| m1_validation_r2+h45_split_test_words_36 vs split_pilot_live | 99 | 86 | 86.9% | 26 |
| m1_validation_r2+h45_split_test_words_36 vs r7_split_test_words | 99 | 92 | 92.9% | 64 |
| m1_validation_r2+h45_split_test_words_36 vs m1_validation_r2 | 63 | 63 | 100.0% | 63 |
| split_pilot_live vs r7_split_test_words | 99 | 86 | 86.9% | 29 |
| split_pilot_live vs m1_validation_r2 | 63 | 52 | 82.5% | 14 |
| r7_split_test_words vs m1_validation_r2 | 63 | 58 | 92.1% | 46 |

## The inputs (like for like)

| runs | words both sent | identical step-1 user turn | system prompts identical, by step |
|---|---|---|---|
| h55_split_test_words vs h55_split_test_words_rep2 | 99 | 99 | alignment: True, descriptors: True, established: True, gloss: True, kind: True, probe: True, same_sense: True, sense: True, vague: True |
| h55_split_test_words vs m1_validation_r2+h45_split_test_words_36 | 99 | 99 | alignment: True, descriptors: True, established: True, gloss: True, kind: True, probe: True, same_sense: True, sense: True, vague: True |
| h55_split_test_words vs split_pilot_live | 99 | 99 | alignment: False, descriptors: True, established: False, gloss: False, kind: False, probe: True, same_sense: False, sense: False, vague: True |
| h55_split_test_words vs r7_split_test_words | 99 | 99 | alignment: True, descriptors: True, established: True, gloss: True, kind: False, probe: True, same_sense: True, sense: True, vague: True |
| h55_split_test_words vs m1_validation_r2 | 63 | 63 | alignment: True, descriptors: True, established: True, gloss: True, kind: True, probe: True, same_sense: True, sense: True, vague: True |

## Glosses

| run | traits | with gloss | form ok | non-memberships in band (18-43) / below / above, mean words | memberships, mean words | memberships of 18+ words (possibly padded) | gloss models |
|---|---|---|---|---|---|---|---|
| h55_split_test_words | 74 | 74 | 72 | 63 / 0 / 0, 27.9 | 11, 19.8 | 5 | Haiku 5.5 64, Sonnet 5.5 10 |
| h55_split_test_words_rep2 | 70 | 70 | 65 | 60 / 0 / 0, 26.9 | 10, 17.9 | 5 | Haiku 5.5 70 |
| m1_validation_r2+h45_split_test_words_36 | 76 | 76 | 75 | 15 / 48 / 0, 15.9 | 13, 12.7 | 0 | Haiku 4.5 66, Sonnet 5.5 10 |
| split_pilot_live | 69 | 69 | 69 | 18 / 39 / 0, 16.9 | 12, 15.8 | 5 | Haiku 4.5 58, Sonnet 5.5 11 |
| r7_split_test_words | 75 | 75 | 73 | 16 / 46 / 0, 16.3 | 13, 12.8 | 1 | Haiku 4.5 63, Sonnet 5.5 12 |
| m1_validation_r2 | 49 | 49 | 48 | 10 / 27 / 0, 16.5 | 12, 12.6 | 0 | Haiku 4.5 39, Sonnet 5.5 10 |

## Alignment scores (traits)

| run | scores |
|---|---|
| h55_split_test_words | {"0": 38, "1": 16, "2": 11, "3": 9} |
| h55_split_test_words_rep2 | {"0": 38, "1": 13, "2": 11, "3": 8} |
| m1_validation_r2+h45_split_test_words_36 | {"0": 59, "1": 9, "2": 1, "3": 7} |
| split_pilot_live | {"none": 69} |
| r7_split_test_words | {"0": 55, "1": 8, "2": 2, "3": 10} |
| m1_validation_r2 | {"0": 38, "1": 5, "2": 1, "3": 5} |

## Parse rates (first attempt; in the end)

| run | step, role, model | calls | first | end |
|---|---|---|---|---|
| h55_split_test_words | alignment|first|claude-haiku-5-5 | 74 | 74 | 74 |
| h55_split_test_words | descriptors|first|claude-haiku-5-5 | 74 | 74 | 74 |
| h55_split_test_words | established|first|claude-haiku-5-5 | 97 | 97 | 97 |
| h55_split_test_words | established|second|claude-sonnet-5-5 | 17 | 17 | 17 |
| h55_split_test_words | gloss|first|claude-haiku-5-5 | 64 | 64 | 64 |
| h55_split_test_words | gloss|first|claude-sonnet-5-5 | 10 | 10 | 10 |
| h55_split_test_words | kind|first|claude-haiku-5-5 | 97 | 97 | 97 |
| h55_split_test_words | kind|second|claude-sonnet-5-5 | 17 | 17 | 17 |
| h55_split_test_words | probe|first|claude-haiku-5-5 | 13 | 13 | 13 |
| h55_split_test_words | same_sense|first|claude-haiku-5-5 | 5 | 5 | 5 |
| h55_split_test_words | same_sense|second|claude-sonnet-5-5 | 5 | 5 | 5 |
| h55_split_test_words | sense|first|claude-haiku-5-5 | 99 | 99 | 99 |
| h55_split_test_words | sense|second|claude-sonnet-5-5 | 12 | 12 | 12 |
| h55_split_test_words | vague|first|claude-haiku-5-5 | 97 | 97 | 97 |
| h55_split_test_words | vague|second|claude-sonnet-5-5 | 17 | 17 | 17 |
| h55_split_test_words_rep2 | alignment|first|claude-haiku-5-5 | 70 | 70 | 70 |
| h55_split_test_words_rep2 | descriptors|first|claude-haiku-5-5 | 70 | 70 | 70 |
| h55_split_test_words_rep2 | established|first|claude-haiku-5-5 | 91 | 91 | 91 |
| h55_split_test_words_rep2 | gloss|first|claude-haiku-5-5 | 70 | 70 | 70 |
| h55_split_test_words_rep2 | kind|first|claude-haiku-5-5 | 91 | 91 | 91 |
| h55_split_test_words_rep2 | probe|first|claude-haiku-5-5 | 13 | 13 | 13 |
| h55_split_test_words_rep2 | same_sense|first|claude-haiku-5-5 | 3 | 3 | 3 |
| h55_split_test_words_rep2 | sense|first|claude-haiku-5-5 | 99 | 99 | 99 |
| h55_split_test_words_rep2 | vague|first|claude-haiku-5-5 | 91 | 91 | 91 |
| m1_validation_r2+h45_split_test_words_36 | alignment|first|claude-haiku-4-5-20251001 | 76 | 76 | 76 |
| m1_validation_r2+h45_split_test_words_36 | descriptors|first|claude-haiku-4-5-20251001 | 76 | 76 | 76 |
| m1_validation_r2+h45_split_test_words_36 | established|first|claude-haiku-4-5-20251001 | 140 | 140 | 140 |
| m1_validation_r2+h45_split_test_words_36 | established|second|claude-sonnet-5-5 | 16 | 16 | 16 |
| m1_validation_r2+h45_split_test_words_36 | gloss|first|claude-haiku-4-5-20251001 | 66 | 66 | 66 |
| m1_validation_r2+h45_split_test_words_36 | gloss|first|claude-sonnet-5-5 | 10 | 10 | 10 |
| m1_validation_r2+h45_split_test_words_36 | kind|first|claude-haiku-4-5-20251001 | 140 | 140 | 140 |
| m1_validation_r2+h45_split_test_words_36 | kind|second|claude-sonnet-5-5 | 16 | 16 | 16 |
| m1_validation_r2+h45_split_test_words_36 | probe|first|claude-haiku-4-5-20251001 | 13 | 13 | 13 |
| m1_validation_r2+h45_split_test_words_36 | same_sense|first|claude-haiku-4-5-20251001 | 39 | 39 | 39 |
| m1_validation_r2+h45_split_test_words_36 | same_sense|second|claude-sonnet-5-5 | 2 | 2 | 2 |
| m1_validation_r2+h45_split_test_words_36 | sense|first|claude-haiku-4-5-20251001 | 99 | 99 | 99 |
| m1_validation_r2+h45_split_test_words_36 | sense|second|claude-sonnet-5-5 | 12 | 12 | 12 |
| m1_validation_r2+h45_split_test_words_36 | vague|first|claude-haiku-4-5-20251001 | 140 | 140 | 140 |
| m1_validation_r2+h45_split_test_words_36 | vague|second|claude-sonnet-5-5 | 16 | 16 | 16 |
| split_pilot_live | alignment|first|claude-haiku-4-5-20251001 | 69 | 69 | 69 |
| split_pilot_live | descriptors|first|claude-haiku-4-5-20251001 | 69 | 69 | 69 |
| split_pilot_live | established|first|claude-haiku-4-5-20251001 | 127 | 127 | 127 |
| split_pilot_live | established|second|claude-sonnet-5-5 | 21 | 21 | 21 |
| split_pilot_live | gloss|first|claude-haiku-4-5-20251001 | 58 | 58 | 58 |
| split_pilot_live | gloss|first|claude-sonnet-5-5 | 11 | 11 | 11 |
| split_pilot_live | kind|first|claude-haiku-4-5-20251001 | 127 | 127 | 127 |
| split_pilot_live | kind|second|claude-sonnet-5-5 | 21 | 21 | 21 |
| split_pilot_live | probe|first|claude-haiku-4-5-20251001 | 13 | 13 | 13 |
| split_pilot_live | same_sense|first|claude-haiku-4-5-20251001 | 28 | 28 | 28 |
| split_pilot_live | same_sense|second|claude-sonnet-5-5 | 5 | 5 | 5 |
| split_pilot_live | sense|first|claude-haiku-4-5-20251001 | 99 | 99 | 99 |
| split_pilot_live | sense|second|claude-sonnet-5-5 | 13 | 13 | 13 |
| split_pilot_live | vague|first|claude-haiku-4-5-20251001 | 127 | 127 | 127 |
| split_pilot_live | vague|second|claude-sonnet-5-5 | 21 | 21 | 21 |
| r7_split_test_words | alignment|first|claude-haiku-4-5-20251001 | 75 | 75 | 75 |
| r7_split_test_words | descriptors|first|claude-haiku-4-5-20251001 | 75 | 75 | 75 |
| r7_split_test_words | established|first|claude-haiku-4-5-20251001 | 139 | 139 | 139 |
| r7_split_test_words | established|second|claude-sonnet-5-5 | 19 | 19 | 19 |
| r7_split_test_words | gloss|first|claude-haiku-4-5-20251001 | 63 | 63 | 63 |
| r7_split_test_words | gloss|first|claude-sonnet-5-5 | 12 | 12 | 12 |
| r7_split_test_words | kind|first|claude-haiku-4-5-20251001 | 139 | 139 | 139 |
| r7_split_test_words | kind|second|claude-sonnet-5-5 | 19 | 19 | 19 |
| r7_split_test_words | probe|first|claude-haiku-4-5-20251001 | 13 | 13 | 13 |
| r7_split_test_words | same_sense|first|claude-haiku-4-5-20251001 | 37 | 37 | 37 |
| r7_split_test_words | same_sense|second|claude-sonnet-5-5 | 5 | 5 | 5 |
| r7_split_test_words | sense|first|claude-haiku-4-5-20251001 | 99 | 99 | 99 |
| r7_split_test_words | sense|second|claude-sonnet-5-5 | 14 | 14 | 14 |
| r7_split_test_words | vague|first|claude-haiku-4-5-20251001 | 139 | 139 | 139 |
| r7_split_test_words | vague|second|claude-sonnet-5-5 | 19 | 19 | 19 |
| m1_validation_r2 | alignment|first|claude-haiku-4-5-20251001 | 49 | 49 | 49 |
| m1_validation_r2 | descriptors|first|claude-haiku-4-5-20251001 | 49 | 49 | 49 |
| m1_validation_r2 | established|first|claude-haiku-4-5-20251001 | 90 | 90 | 90 |
| m1_validation_r2 | established|second|claude-sonnet-5-5 | 16 | 16 | 16 |
| m1_validation_r2 | gloss|first|claude-haiku-4-5-20251001 | 39 | 39 | 39 |
| m1_validation_r2 | gloss|first|claude-sonnet-5-5 | 10 | 10 | 10 |
| m1_validation_r2 | kind|first|claude-haiku-4-5-20251001 | 90 | 90 | 90 |
| m1_validation_r2 | kind|second|claude-sonnet-5-5 | 16 | 16 | 16 |
| m1_validation_r2 | probe|first|claude-haiku-4-5-20251001 | 11 | 11 | 11 |
| m1_validation_r2 | same_sense|first|claude-haiku-4-5-20251001 | 24 | 24 | 24 |
| m1_validation_r2 | same_sense|second|claude-sonnet-5-5 | 2 | 2 | 2 |
| m1_validation_r2 | sense|first|claude-haiku-4-5-20251001 | 63 | 63 | 63 |
| m1_validation_r2 | sense|second|claude-sonnet-5-5 | 12 | 12 | 12 |
| m1_validation_r2 | vague|first|claude-haiku-4-5-20251001 | 90 | 90 | 90 |
| m1_validation_r2 | vague|second|claude-sonnet-5-5 | 16 | 16 | 16 |

## Per-call tokens and answer lengths

| run | step | model | calls | stop reasons | input tokens (mean) | output tokens: mean / median / p90 / max | answer characters (mean) | cost |
|---|---|---|---|---|---|---|---|---|
| h55_split_test_words | alignment | Haiku 5.5 | 74 | end_turn 74 | 780.0 | 170.6 / 93.5 / 353.40000000000003 / 491.0 | 228.9 | $0.0121 |
| h55_split_test_words | descriptors | Haiku 5.5 | 74 | end_turn 74 | 480.0 | 212.7 / 212.0 / 333.7000000000001 / 442.0 | 244.9 | $0.0114 |
| h55_split_test_words | established | Haiku 5.5 | 97 | end_turn 97 | 634.3 | 295.4 / 255.0 / 518.2 / 806.0 | 241.9 | $0.0205 |
| h55_split_test_words | established | Sonnet 5.5 | 17 | end_turn 17 | 631.2 | 99.6 / 102.0 / 111.8 / 117.0 | 271.1 | $0.0384 |
| h55_split_test_words | gloss | Haiku 5.5 | 64 | end_turn 64 | 662.9 | 102.5 / 74.0 / 83.7 / 865.0 | 201.4 | $0.0075 |
| h55_split_test_words | gloss | Sonnet 5.5 | 10 | end_turn 10 | 661.6 | 70.2 / 73.5 / 76.4 / 80.0 | 200.0 | $0.0203 |
| h55_split_test_words | kind | Haiku 5.5 | 97 | end_turn 97 | 1018.4 | 105.1 / 78.0 / 199.6000000000001 / 403.0 | 213.3 | $0.0150 |
| h55_split_test_words | kind | Sonnet 5.5 | 17 | end_turn 17 | 1017.0 | 75.5 / 71.0 / 90.8 / 98.0 | 206.5 | $0.0474 |
| h55_split_test_words | probe | Haiku 5.5 | 13 | end_turn 13 | 413.8 | 98.8 / 99.0 / 114.60000000000001 / 122.0 | 265.2 | $0.0012 |
| h55_split_test_words | same_sense | Haiku 5.5 | 5 | end_turn 5 | 427.0 | 139.6 / 93.0 / 233.8 / 297.0 | 236.4 | $0.0006 |
| h55_split_test_words | same_sense | Sonnet 5.5 | 5 | end_turn 5 | 423.6 | 76.8 / 75.0 / 83.6 / 84.0 | 216.6 | $0.0081 |
| h55_split_test_words | sense | Haiku 5.5 | 99 | end_turn 99 | 819.6 | 557.1 / 556.0 / 769.6 / 855.0 | 503.5 | $0.0357 |
| h55_split_test_words | sense | Sonnet 5.5 | 12 | end_turn 12 | 819.3 | 195.5 / 195.5 / 215.8 / 221.0 | 520.5 | $0.0431 |
| h55_split_test_words | vague | Haiku 5.5 | 97 | end_turn 97 | 467.4 | 112.8 / 106.0 / 120.80000000000001 / 707.0 | 292.7 | $0.0100 |
| h55_split_test_words | vague | Sonnet 5.5 | 17 | end_turn 17 | 466.0 | 109.5 / 112.0 / 117.8 / 131.0 | 297.2 | $0.0345 |
| h55_split_test_words_rep2 | alignment | Haiku 5.5 | 70 | end_turn 70 | 779.0 | 173.0 / 92.0 / 388.1 / 515.0 | 234.3 | $0.0115 |
| h55_split_test_words_rep2 | descriptors | Haiku 5.5 | 70 | end_turn 70 | 479.0 | 209.0 / 204.5 / 317.1 / 477.0 | 238.3 | $0.0107 |
| h55_split_test_words_rep2 | established | Haiku 5.5 | 91 | end_turn 91 | 634.0 | 278.5 / 260.0 / 531.0 / 716.0 | 241.8 | $0.0184 |
| h55_split_test_words_rep2 | gloss | Haiku 5.5 | 70 | end_turn 70 | 662.5 | 93.0 / 72.5 / 87.70000000000002 / 620.0 | 197.3 | $0.0079 |
| h55_split_test_words_rep2 | kind | Haiku 5.5 | 91 | end_turn 91 | 1018.5 | 109.3 / 77.0 / 227.0 / 354.0 | 210.2 | $0.0142 |
| h55_split_test_words_rep2 | probe | Haiku 5.5 | 13 | end_turn 13 | 413.8 | 102.2 / 99.0 / 121.20000000000002 / 167.0 | 257.5 | $0.0012 |
| h55_split_test_words_rep2 | same_sense | Haiku 5.5 | 3 | end_turn 3 | 427.0 | 120.3 / 75.0 / 191.8 / 221.0 | 202.3 | $0.0003 |
| h55_split_test_words_rep2 | sense | Haiku 5.5 | 99 | end_turn 99 | 819.6 | 564.5 / 545.0 / 785.0 / 1056.0 | 505.4 | $0.0361 |
| h55_split_test_words_rep2 | vague | Haiku 5.5 | 91 | end_turn 91 | 467.5 | 105.3 / 104.0 / 119.0 / 144.0 | 290.8 | $0.0090 |
| m1_validation_r2+h45_split_test_words_36 | alignment | Haiku 4.5 | 76 | end_turn 76 | 586.2 | 83.5 / 85.0 / 90.5 / 99.0 | 269.0 | $0.0763 |
| m1_validation_r2+h45_split_test_words_36 | descriptors | Haiku 4.5 | 76 | end_turn 76 | 361.2 | 87.2 / 87.0 / 93.5 / 102.0 | 271.8 | $0.0606 |
| m1_validation_r2+h45_split_test_words_36 | established | Haiku 4.5 | 140 | end_turn 140 | 515.1 | 93.7 / 94.0 / 101.10000000000001 / 111.0 | 301.5 | $0.1377 |
| m1_validation_r2+h45_split_test_words_36 | established | Sonnet 5.5 | 16 | end_turn 16 | 629.4 | 109.4 / 106.5 / 132.0 / 141.0 | 301.3 | $0.0377 |
| m1_validation_r2+h45_split_test_words_36 | gloss | Haiku 4.5 | 66 | end_turn 66 | 519.0 | 42.0 / 42.0 / 47.5 / 51.0 | 136.9 | $0.0481 |
| m1_validation_r2+h45_split_test_words_36 | gloss | Sonnet 5.5 | 10 | end_turn 10 | 662.2 | 68.9 / 74.0 / 78.2 / 80.0 | 187.8 | $0.0201 |
| m1_validation_r2+h45_split_test_words_36 | kind | Haiku 4.5 | 140 | end_turn 140 | 781.5 | 77.6 / 77.0 / 83.0 / 94.0 | 248.6 | $0.1637 |
| m1_validation_r2+h45_split_test_words_36 | kind | Sonnet 5.5 | 16 | end_turn 16 | 1016.4 | 72.8 / 73.0 / 77.0 / 78.0 | 196.0 | $0.0442 |
| m1_validation_r2+h45_split_test_words_36 | probe | Haiku 4.5 | 13 | end_turn 13 | 321.2 | 97.7 / 96.0 / 108.4 / 120.0 | 324.2 | $0.0105 |
| m1_validation_r2+h45_split_test_words_36 | same_sense | Haiku 4.5 | 39 | end_turn 39 | 346.0 | 78.2 / 77.0 / 87.2 / 102.0 | 263.8 | $0.0287 |
| m1_validation_r2+h45_split_test_words_36 | same_sense | Sonnet 5.5 | 2 | end_turn 2 | 422.5 | 92.0 / 92.0 / 104.8 / 108.0 | 252.0 | $0.0035 |
| m1_validation_r2+h45_split_test_words_36 | sense | Haiku 4.5 | 99 | end_turn 99 | 641.3 | 212.1 / 216.0 / 242.0 / 259.0 | 734.8 | $0.1685 |
| m1_validation_r2+h45_split_test_words_36 | sense | Sonnet 5.5 | 12 | end_turn 12 | 819.7 | 205.9 / 210.5 / 221.0 / 221.0 | 541.3 | $0.0444 |
| m1_validation_r2+h45_split_test_words_36 | vague | Haiku 4.5 | 140 | end_turn 140 | 374.5 | 96.6 / 96.0 / 105.0 / 115.0 | 314.9 | $0.1201 |
| m1_validation_r2+h45_split_test_words_36 | vague | Sonnet 5.5 | 16 | end_turn 16 | 465.4 | 104.5 / 104.5 / 113.0 / 113.0 | 286.8 | $0.0316 |
| split_pilot_live | alignment | Haiku 4.5 | 69 | end_turn 69 | 280.8 | 72.4 / 76.0 / 85.0 / 88.0 | 249.5 | $0.0444 |
| split_pilot_live | descriptors | Haiku 4.5 | 69 | end_turn 69 | 362.8 | 88.5 / 88.0 / 95.4 / 109.0 | 280.8 | $0.0556 |
| split_pilot_live | established | Haiku 4.5 | 127 | end_turn 127 | 467.2 | 91.4 / 91.0 / 98.0 / 113.0 | 293.9 | $0.1174 |
| split_pilot_live | established | Sonnet 5.5 | 21 | end_turn 21 | 566.5 | 95.1 / 93.0 / 111.0 / 123.0 | 258.3 | $0.0438 |
| split_pilot_live | gloss | Haiku 4.5 | 58 | end_turn 58 | 490.1 | 42.9 / 43.0 / 48.0 / 50.0 | 145.4 | $0.0409 |
| split_pilot_live | gloss | Sonnet 5.5 | 11 | end_turn 11 | 624.2 | 69.2 / 69.0 / 78.0 / 81.0 | 199.9 | $0.0213 |
| split_pilot_live | kind | Haiku 4.5 | 127 | end_turn 127 | 736.3 | 78.3 / 78.0 / 83.0 / 111.0 | 252.1 | $0.1432 |
| split_pilot_live | kind | Sonnet 5.5 | 21 | end_turn 21 | 957.1 | 73.9 / 71.0 / 84.0 / 124.0 | 200.8 | $0.0557 |
| split_pilot_live | probe | Haiku 4.5 | 13 | end_turn 13 | 321.2 | 99.0 / 96.0 / 109.80000000000001 / 128.0 | 329.6 | $0.0106 |
| split_pilot_live | same_sense | Haiku 4.5 | 28 | end_turn 28 | 347.5 | 79.4 / 78.0 / 89.0 / 93.0 | 268.2 | $0.0209 |
| split_pilot_live | same_sense | Sonnet 5.5 | 5 | end_turn 5 | 421.4 | 76.0 / 79.0 / 83.2 / 86.0 | 208.2 | $0.0080 |
| split_pilot_live | sense | Haiku 4.5 | 99 | end_turn 99 | 573.3 | 209.7 / 216.0 / 233.0 / 260.0 | 728.5 | $0.1606 |
| split_pilot_live | sense | Sonnet 5.5 | 13 | end_turn 13 | 730.9 | 189.9 / 190.0 / 220.2 / 226.0 | 495.5 | $0.0437 |
| split_pilot_live | vague | Haiku 4.5 | 127 | end_turn 127 | 375.3 | 97.4 / 97.0 / 106.0 / 114.0 | 318.5 | $0.1095 |
| split_pilot_live | vague | Sonnet 5.5 | 21 | end_turn 21 | 463.1 | 105.9 / 102.0 / 117.0 / 136.0 | 289.1 | $0.0417 |
| r7_split_test_words | alignment | Haiku 4.5 | 75 | end_turn 75 | 586.9 | 82.2 / 84.0 / 92.0 / 99.0 | 267.5 | $0.0748 |
| r7_split_test_words | descriptors | Haiku 4.5 | 75 | end_turn 75 | 361.9 | 87.3 / 87.0 / 94.0 / 104.0 | 273.0 | $0.0599 |
| r7_split_test_words | established | Haiku 4.5 | 139 | end_turn 139 | 515.2 | 94.0 / 94.0 / 101.0 / 113.0 | 303.9 | $0.1369 |
| r7_split_test_words | established | Sonnet 5.5 | 19 | end_turn 19 | 630.7 | 96.4 / 95.0 / 112.6 / 126.0 | 260.3 | $0.0423 |
| r7_split_test_words | gloss | Haiku 4.5 | 63 | end_turn 63 | 519.0 | 41.6 / 41.0 / 47.0 / 51.0 | 136.0 | $0.0458 |
| r7_split_test_words | gloss | Sonnet 5.5 | 12 | end_turn 12 | 661.4 | 69.7 / 70.5 / 75.9 / 77.0 | 198.7 | $0.0242 |
| r7_split_test_words | kind | Haiku 4.5 | 139 | end_turn 139 | 782.7 | 78.6 / 78.0 / 84.0 / 93.0 | 252.3 | $0.1634 |
| r7_split_test_words | kind | Sonnet 5.5 | 19 | end_turn 19 | 1012.7 | 77.7 / 73.0 / 94.99999999999999 / 111.0 | 214.0 | $0.0532 |
| r7_split_test_words | probe | Haiku 4.5 | 13 | end_turn 13 | 321.2 | 98.8 / 96.0 / 111.2 / 120.0 | 328.5 | $0.0106 |
| r7_split_test_words | same_sense | Haiku 4.5 | 37 | end_turn 37 | 346.5 | 79.3 / 78.0 / 89.8 / 104.0 | 270.6 | $0.0275 |
| r7_split_test_words | same_sense | Sonnet 5.5 | 5 | end_turn 5 | 423.4 | 77.6 / 76.0 / 92.8 / 94.0 | 213.0 | $0.0081 |
| r7_split_test_words | sense | Haiku 4.5 | 99 | end_turn 99 | 641.3 | 212.1 / 215.0 / 234.4 / 259.0 | 735.1 | $0.1685 |
| r7_split_test_words | sense | Sonnet 5.5 | 14 | end_turn 14 | 819.1 | 201.1 / 204.5 / 234.7 / 239.0 | 522.3 | $0.0511 |
| r7_split_test_words | vague | Haiku 4.5 | 139 | end_turn 139 | 374.7 | 97.2 / 97.0 / 106.0 / 110.0 | 317.1 | $0.1196 |
| r7_split_test_words | vague | Sonnet 5.5 | 19 | end_turn 19 | 465.7 | 104.9 / 105.0 / 112.19999999999999 / 123.0 | 287.4 | $0.0376 |
| m1_validation_r2 | alignment | Haiku 4.5 | 49 | end_turn 49 | 586.8 | 82.7 / 84.0 / 90.2 / 99.0 | 266.4 | $0.0490 |
| m1_validation_r2 | descriptors | Haiku 4.5 | 49 | end_turn 49 | 361.8 | 87.0 / 87.0 / 95.0 / 102.0 | 272.8 | $0.0390 |
| m1_validation_r2 | established | Haiku 4.5 | 90 | end_turn 90 | 515.1 | 94.2 / 95.0 / 102.10000000000001 / 111.0 | 305.2 | $0.0887 |
| m1_validation_r2 | established | Sonnet 5.5 | 16 | end_turn 16 | 629.4 | 109.4 / 106.5 / 132.0 / 141.0 | 301.3 | $0.0377 |
| m1_validation_r2 | gloss | Haiku 4.5 | 39 | end_turn 39 | 519.4 | 41.1 / 40.0 / 47.0 / 51.0 | 132.5 | $0.0283 |
| m1_validation_r2 | gloss | Sonnet 5.5 | 10 | end_turn 10 | 662.2 | 68.9 / 74.0 / 78.2 / 80.0 | 187.8 | $0.0201 |
| m1_validation_r2 | kind | Haiku 4.5 | 90 | end_turn 90 | 781.6 | 78.0 / 78.0 / 83.10000000000001 / 94.0 | 251.1 | $0.1054 |
| m1_validation_r2 | kind | Sonnet 5.5 | 16 | end_turn 16 | 1016.4 | 72.8 / 73.0 / 77.0 / 78.0 | 196.0 | $0.0442 |
| m1_validation_r2 | probe | Haiku 4.5 | 11 | end_turn 11 | 321.4 | 98.7 / 98.0 / 110.0 / 120.0 | 327.6 | $0.0090 |
| m1_validation_r2 | same_sense | Haiku 4.5 | 24 | end_turn 24 | 346.0 | 79.5 / 78.0 / 88.7 / 102.0 | 270.8 | $0.0178 |
| m1_validation_r2 | same_sense | Sonnet 5.5 | 2 | end_turn 2 | 422.5 | 92.0 / 92.0 / 104.8 / 108.0 | 252.0 | $0.0035 |
| m1_validation_r2 | sense | Haiku 4.5 | 63 | end_turn 63 | 641.4 | 215.8 / 217.0 / 242.60000000000002 / 259.0 | 752.6 | $0.1084 |
| m1_validation_r2 | sense | Sonnet 5.5 | 12 | end_turn 12 | 819.7 | 205.9 / 210.5 / 221.0 / 221.0 | 541.3 | $0.0444 |
| m1_validation_r2 | vague | Haiku 4.5 | 90 | end_turn 90 | 374.6 | 97.4 / 97.5 / 106.0 / 115.0 | 320.5 | $0.0776 |
| m1_validation_r2 | vague | Sonnet 5.5 | 16 | end_turn 16 | 465.4 | 104.5 / 104.5 / 113.0 / 113.0 | 286.8 | $0.0316 |
