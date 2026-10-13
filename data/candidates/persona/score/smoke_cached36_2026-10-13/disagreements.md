# Persona space against M3: disagreements, batch `smoke_cached36_2026-10-13`

Each kind is ranked by its strength and cut to 3 rows (10% of the scored rows).  Thresholds: `dup_threshold` 0.73, `novel_pct` 0.80, cover-questioned cosine 0.61, novel-vs-covered percentile 0.90 (set by: plan default).  Persona space reads a *predicted* vector; M3 reads the text.  Neither decides here: M3's decision is unchanged.

## M3 new, persona space duplicate-like (`dup_vs_new`): 3 listed of 5

| # | candidate | generators | M3 | persona nearest | nn cos | residual pct | evidence | overlap reading |
|---|---|---|---|---|---|---|---|---|
| 1 | derisive (`derisive#1`) | censuses, roget, base_model, states_pass | new, first listed [sarcastic](../../../../traits/instructions/sarcastic.json) | [sardonic](../../../../traits/instructions/sardonic.json) | 0.82 | 0.09 | nn_cos 0.82 >= dup_threshold 0.73; M3 listed sarcastic first at text cosine 0.36 and decided new | not read |
| 2 | parasitic (`parasitic#1`) | censuses, roget | new, first listed [ungrateful](../../../../traits/instructions/ungrateful.json) | [greedy](../../../../traits/instructions/greedy.json) | 0.77 | 0.61 | nn_cos 0.77 >= dup_threshold 0.73; M3 listed ungrateful first at text cosine 0.25 and decided new | not read |
| 3 | insulting (`insulting#1`) | censuses | new, first listed [sarcastic](../../../../traits/instructions/sarcastic.json) | [sarcastic](../../../../traits/instructions/sarcastic.json) | 0.75 | 0.27 | nn_cos 0.75 >= dup_threshold 0.73; M3 listed sarcastic first at text cosine 0.42 and decided new | not read |

## M3 covered, persona space far from the covering trait (`cover_questioned`): 0 listed of 0

None.

## M3 covered, persona space novel-like (`novel_vs_covered`): 0 listed of 0

None.

