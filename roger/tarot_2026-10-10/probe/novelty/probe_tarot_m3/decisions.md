# M3 decisions: `probe_tarot_m3`

8 candidates: 3 covered, 5 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| carefree | covered | [lighthearted](../../../traits/instructions/lighthearted.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means keeping one's mood light and letting small worries pass without dwelling on them, approaching days with an easy, unhurried calm even when plans go wrong. |
| masterful | covered | [competent](../../../traits/instructions/competent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means handling each task with exacting skill and deep expertise, working so fluently and precisely that one's craft shows in every detail, whatever the difficulty of the job. |
| sensual | covered | [hedonistic](../../../traits/instructions/hedonistic.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means savoring bodily pleasures, from rich food and fine wine to soft fabrics and warm baths, and choosing luxury and indulgence whenever the chance arises. |
| amorous | new |  | 3 |  | both_similar: [gay](../../../traits/instructions/gay.json) / [straight](../../../traits/instructions/straight.json) | [asexual](../../../traits/instructions/asexual.json) | 6 | This means feeling romantic or sexual desire toward someone and letting that longing color how one looks at, speaks to, and lingers near them. |
| dreamy | new |  | 3 |  |  |  | 7 | This means drifting off into daydreams and fanciful imaginings, often losing track of what is happening around one while lost in thought. |
| self-reinventing | new |  | 3 |  |  |  | 6 | This means continually remaking one's own identity or public image, shedding past selves and presenting new versions of oneself as circumstances or ambitions shift. |
| strong-willed | new |  | 4 |  |  |  | 6 | This means holding firmly to one's chosen course once committed, pressing on with determination through obstacles, discouragement, and others' objections until the goal is reached. |
| surrendering | new |  | 4 |  |  |  | 5 | This means giving in to pressure or an opponent and dropping one's resistance once the struggle has been lost, rather than pressing on or hiding one's defeat. |

## Covered, flagged (2 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **carefree** (`carefree#1`, cut-off 3) by [lighthearted](../../../traits/instructions/lighthearted.json): Sonnet 2 ("Both involve a light, untroubled disposition that doesn't dwell on worries, but lighthearted adds breezy speech and joking while carefree emphasizes unhurried calm when plans go wrong."), Opus 3 ("Both describe an unburdened, light mood. Lighthearted carries this further to large matters and adds breezy, joking expression, but the core quality is the same.")
  Gloss: This means keeping one's mood light and letting small worries pass without dwelling on them, approaching days with an easy, unhurried calm even when plans go wrong.
- **sensual** (`sensual#1`, cut-off 3) by [hedonistic](../../../traits/instructions/hedonistic.json): Sonnet 2 ("Both involve pursuing sensory pleasure, but sensual centers on savoring bodily luxuries, while hedonistic centers on putting immediate gratification ahead of responsibilities and long-term concerns; neither implies the other."), Opus 3 ("Both center on seeking sensory pleasure and indulgence; hedonistic carries it further by putting immediate gratification ahead of responsibilities and long-term goals.")
  Gloss: This means savoring bodily pleasures, from rich food and fine wine to soft fabrics and warm baths, and choosing luxury and indulgence whenever the chance arises.

## Both ends similar (orthogonal to the pair?) (1 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.

- **amorous** (`amorous#1`, new, cut-off 3).  Gloss: This means feeling romantic or sexual desire toward someone and letting that longing color how one looks at, speaks to, and lingers near them.
  - pair: [gay](../../../traits/instructions/gay.json) (cosine 0.347); [straight](../../../traits/instructions/straight.json) (cosine 0.311)

## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- amorous (new): [asexual](../../../traits/instructions/asexual.json)
