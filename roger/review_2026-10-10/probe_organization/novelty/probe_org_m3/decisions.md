# M3 decisions: `probe_org_m3`

4 candidates: 4 covered.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| disorganized | covered | [careless (HEXACO)](../../../traits/instructions/careless_hexaco.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means leaving habits, work and thinking without order, letting papers, plans and ideas pile up in no particular shape and accepting that one rarely finds things when needed. |
| disorganized | covered | [chaotic](../../../traits/instructions/chaotic.json) | 3 | Sonnet 3, Opus 3 |  |  | 6 | This means working and thinking in a scattered way, jumping between tasks and ideas without a system, and letting loose ends pile up rather than keeping one's affairs in order. |
| organized | covered | [methodical](../../../traits/instructions/methodical.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means approaching every task step by step, sorting information into clear categories, and following a deliberate system so that nothing is left to chance or scattered across one's thinking. |
| organized | covered | [conscientious (HEXACO)](../../../traits/instructions/conscientious_hexaco.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means keeping one's work, notes and surroundings in a deliberate order, approaching tasks step by step and returning things to their place so nothing is left to chance. |

## Covered, flagged (3 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **disorganized** (`disorganized#1`, cut-off 3) by [careless (HEXACO)](../../../traits/instructions/careless_hexaco.json): Sonnet 2 ("Both describe low conscientiousness and share messiness and slipping appointments, but careless also covers avoiding hard tasks, low ambition, sloppy errors and impulsiveness, while disorganized centers on lack of order."), Opus 3 ("Careless (low HEXACO conscientiousness) contains disorganization through the messy room and slipping appointments, but it is broader, also covering low diligence, error-prone work and impulsivity, so the difference is mainly scope.")
  Gloss: This means leaving habits, work and thinking without order, letting papers, plans and ideas pile up in no particular shape and accepting that one rarely finds things when needed.
- **organized** (`organized#1`, cut-off 3) by [methodical](../../../traits/instructions/methodical.json): Sonnet 2 ("Both involve step-by-step, systematic work, but organized adds categorizing information and keeping things from being scattered, while methodical adds strict sequential completion and sticking to the plan; each has something the other lacks."), Opus 3 ("Both describe a systematic, step-by-step approach; organized stresses sorting things into categories, while methodical stresses following a sequential plan, so they differ mainly in emphasis.")
  Gloss: This means approaching every task step by step, sorting information into clear categories, and following a deliberate system so that nothing is left to chance or scattered across one's thinking.
- **organized** (`organized#2`, cut-off 3) by [conscientious (HEXACO)](../../../traits/instructions/conscientious_hexaco.json): Sonnet 2 ("Both involve keeping things in order, but conscientiousness (HEXACO) is broader, adding diligence, perfectionism and careful deliberation, while organized is specifically about order and stepwise method."), Opus 3 ("Organized is the orderliness facet that conscientiousness explicitly includes; conscientiousness is the broader trait, adding diligence, perfectionism and prudence.")
  Gloss: This means keeping one's work, notes and surroundings in a deliberate order, approaching tasks step by step and returning things to their place so nothing is left to chance.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (0 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

