# Full scan `m3_pilot_1_scan` against `m3_pilot_1`

100 candidates, 1719 pairs read in the scan.

## What the relation call's shortlist missed

- Pairs the scan put at the cut-off or above (either model): 76; the relation call did not mark 0 of them similar (recall 1.0).
- Pairs the rule would cut on: 44; not marked similar 0 (recall 1.0); not in the main shortlist at all 0.
- The relation call's answers on the misses: {}.

| candidate | trait | cosine | cut-off | Sonnet | Opus | verdict | relation call |
|---|---|---|---|---|---|---|---|

## Decisions, main run against the scan

| main -> scan | candidates |
|---|---|
| covered -> covered | 37 |
| covered -> grey | 2 |
| covered -> new | 1 |
| grey -> grey | 12 |
| grey -> new | 8 |
| new -> covered | 1 |
| new -> grey | 1 |
| new -> new | 38 |

## What early exit skipped

597 pairs after the covering pair, by verdict: {"keep": 444, "review": 9, "opposite": 138, "cut": 6}; at the cut-off or above: 15.

Sonnet's answer on the pairs read in both runs: {"both_read": 527, "sonnet_same": 480, "rate": 0.9108}.
