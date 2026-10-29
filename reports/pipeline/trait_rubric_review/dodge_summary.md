# What the 8 hard traits' May responses do with the question

Classifier: gpt-5.6-luna, prompt in [dodge_classifier.py](./dodge_classifier.py); scores: gpt-4.1-mini, May 2026 (the 8slot tree); kept = score 3.

## Per trait, discards (score != 3) and kept (score 3)

| trait | n | ANSWERS (disc / kept) | DODGES_IN_TRAIT (disc / kept) | SIDESTEPS_GENERICALLY (disc / kept) | DECLINES_AS_ASSISTANT (disc / kept) | unparsed |
|---|---|---|---|---|---|---|
| avoidant | 500 | 416 / 35 | 11 / 11 | 20 / 3 | 4 / 0 | 0 |
| harmful | 500 | 394 / 71 | 0 / 0 | 22 / 2 | 11 / 0 | 0 |
| deceitful | 500 | 363 / 109 | 3 / 0 | 17 / 0 | 8 / 0 | 0 |
| obsessive | 500 | 332 / 139 | 0 / 7 | 14 / 6 | 2 / 0 | 0 |
| dishonest | 500 | 329 / 158 | 0 / 0 | 10 / 0 | 3 / 0 | 0 |
| ethnocentric | 500 | 322 / 157 | 0 / 0 | 14 / 1 | 6 / 0 | 0 |
| evil | 500 | 261 / 189 | 1 / 0 | 19 / 1 | 29 / 0 | 0 |
| submissive | 500 | 275 / 149 | 12 / 46 | 17 / 0 | 1 / 0 | 0 |

## Label by mini's score, all 8 traits

| label | score 0 | score 1 | score 2 | score 3 |
|---|---|---|---|---|
| ANSWERS | 11 | 2543 | 138 | 1007 |
| DODGES_IN_TRAIT | 2 | 9 | 16 | 64 |
| SIDESTEPS_GENERICALLY | 18 | 107 | 8 | 13 |
| DECLINES_AS_ASSISTANT | 52 | 9 | 3 | 0 |
| unparsed | 0 | 0 | 0 | 0 |

## Label by reader mark on the held sample's 160 trait discards

| label | G | B | T | ? |
|---|---|---|---|---|
| ANSWERS | 26 | 96 | 16 | 2 |
| DODGES_IN_TRAIT | 0 | 0 | 0 | 0 |
| SIDESTEPS_GENERICALLY | 1 | 16 | 1 | 0 |
| DECLINES_AS_ASSISTANT | 0 | 2 | 0 | 0 |
| unparsed | 0 | 0 | 0 | 0 |

Per trait on the held sample (label: marks):

- avoidant: ANSWERS G2B13T4; SIDESTEPS_GENERICALLY T1
- harmful: ANSWERS G1B12T2; SIDESTEPS_GENERICALLY B4; DECLINES_AS_ASSISTANT B1
- deceitful: ANSWERS G2B13T1; SIDESTEPS_GENERICALLY B4
- obsessive: ANSWERS G2B16T1; SIDESTEPS_GENERICALLY B1
- dishonest: ANSWERS G4B13T2; SIDESTEPS_GENERICALLY B1
- ethnocentric: ANSWERS G2B13T2; SIDESTEPS_GENERICALLY B3
- evil: ANSWERS G5B10T2; SIDESTEPS_GENERICALLY B2; DECLINES_AS_ASSISTANT B1
- submissive: ANSWERS G8B6T2?2; SIDESTEPS_GENERICALLY G1B1
