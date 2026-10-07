# Haiku 5.5 against Haiku 4.5: M3's relation call

From `haiku55_compare.py relation` on `data/candidates/novelty/m3_pilot_1_relation_h55` against m3_pilot_1, m3_pilot_1_r2 (Haiku 4.5) and the full scan `m3_pilot_1_scan`.

## Like for like

457 candidates reached the call; 457 have Haiku 4.5's answers on record; the same user turn on 457, the same list order on 457 (Haiku 4.5's models: {"claude-haiku-4-5-20251001": 457}); missing from Haiku 4.5: [].

## Agreement per listed trait

7862 listed traits both answered: the same answer on 5993 (76.2%), kappa 0.6501.

| Haiku 4.5 -> Haiku 5.5 | traits |
|---|---|
| similar -> similar | 1823 |
| similar -> opposed | 2 |
| similar -> unrelated | 904 |
| similar -> unsure | 48 |
| opposed -> similar | 10 |
| opposed -> opposed | 2281 |
| opposed -> unrelated | 608 |
| opposed -> unsure | 7 |
| unrelated -> similar | 141 |
| unrelated -> opposed | 106 |
| unrelated -> unrelated | 1889 |
| unrelated -> unsure | 27 |
| unsure -> opposed | 5 |
| unsure -> unrelated | 11 |

## Recall on the full scan's pairs at the cut-off or above

| model | pairs | marked similar | recall | answers |
|---|---|---|---|---|
| haiku45 | 76 | 76 | 100.0% | {"similar": 76} |
| haiku55 | 76 | 75 | 98.7% | {"similar": 75, "unrelated": 1} |

Missed by haiku55: financially_stable#1 / wealthy (unrelated)

## Roger's 24 corrections

| candidate | trait | should be | Haiku 4.5 | right | Haiku 5.5 | right | note |
|---|---|---|---|---|---|---|---|
| conflict-avoidant | aggressive | opposed | opposed | True | opposed | True |  |
| conflict-avoidant | peaceful | similar | opposed | False | similar | True | maybe the double negative confused a small model |
| inauthentic | self_certain | unrelated | opposed | False | unrelated | True | harmless |
| inauthentic | self_uncertain | unrelated | opposed | False | unrelated | True | harmless |
| leftish | extremist | opposed | opposed | True | opposed | True |  |
| leftish | moderate | not opposed | opposed | False | unrelated | True | tricky; harmless in practice |
| meandering | steady | opposed | opposed | True | opposed | True |  |
| meandering | erratic | not opposed | opposed | False | unrelated | True |  |
| monozygotic | only_child | opposed or 1 | opposed | True | opposed | True | harmless |
| monozygotic | many_siblings | unrelated | opposed | False | opposed | False | harmless |
| one of many | self_conscious | unrelated | opposed | False | unrelated | True | harmless |
| one of many | unselfconscious | unrelated | opposed | False | unrelated | True | harmless |
| self serving | benevolent | opposed | opposed | True | opposed | True |  |
| self serving | uncaring | not opposed | opposed | False | similar | True |  |
| sly | aggressive | not opposed | opposed | False | opposed | False | harmless |
| sly | peaceful | not opposed | opposed | False | unrelated | True | harmless |
| smooth | pretentious | not opposed | opposed | False | unrelated | True | harmless |
| smooth | unpretentious | not opposed | opposed | False | opposed | False | harmless |
| trendsetting | unfashionable | opposed | opposed | True | opposed | True |  |
| trendsetting | fashionable | not opposed | opposed | False | similar | True | Roger asks whether this is harmless in practice |
| twisted | joyful | unrelated | opposed | False | opposed | False | harmless? |
| twisted | joyless | unrelated | opposed | False | unrelated | True | harmless? |
| youthful | mature | opposed | opposed | True | opposed | True |  |
| youthful | immature | not opposed | opposed | False | unrelated | True | Roger asks whether this is harmless |

| model | right | wrong | not read |
|---|---|---|---|
| haiku45 | 7 | 17 | 0 |
| haiku55 | 20 | 4 | 0 |

## Similar and opposed per candidate, and the shortlist

| model | candidates | similar: mean / median / max | opposed: mean / median / max | similar + opposed: mean | totals similar / opposed / unrelated / unsure | candidates with an unsure | shortlist length: mean / median / max, total |
|---|---|---|---|---|---|---|---|
| haiku45 | 457 | 6.1 / 6.0 / 10.0 | 6.4 / 7.0 / 11.0 | 12.4 | 2777 / 2906 / 2163 / 16 | 11 | 7.2 / 8.0 / 12.0, 3294 |
| haiku55 | 457 | 4.3 / 4.0 / 9.0 | 5.2 / 5.0 / 11.0 | 9.6 | 1974 / 2394 / 3412 / 82 | 59 | 5.9 / 6.0 / 12.0, 2702 |

## Parse and unsure rates

| model | calls | parsed first time | parsed in the end | unsure rate |
|---|---|---|---|---|
| haiku45 | 457 | 457 | 457 | 0.2% |
| haiku55 | 457 | 457 | 457 | 1.0% |

## The calls

| model | step, model | calls | stop reasons | input tokens mean | output tokens: mean / median / p90 / max | output tokens per listed trait (mean) | answer characters (mean) | cost |
|---|---|---|---|---|---|---|---|---|
| haiku45 | relation:claude-haiku-4-5-20251001 | 457 | {"end_turn": 457} | 1314.41 | 955.77 / 963.0 / 1109.0 / 1243.0 | 55.61 | 3619.07 | $2.7846 |
| haiku55 | relation:claude-haiku-5-5 | 457 | {"end_turn": 457} | 1745.81 | 1315.88 / 1160.0 / 2101.0 / 2628.0 | 76.02 | 3005.45 | $0.3805 |
| haiku55 | relation_unsure:claude-sonnet-5-5 | 59 | {"end_turn": 59} | 606.54 | 130.76 / 101.0 / 202.20000000000005 / 471.0 | 94.83 | 372.34 | $0.1487 |
