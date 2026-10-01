# Haiku, Sonnet and Opus on the filter's second-opinion sample (2026-10-02)

Roger, 2026-10-02: "have Opus also do the 10% sample and see how well Haiku and Sonnet are doing,
treating Opus's judgement as ground truth", and look at the differences.  The sample is the 207 words
that the split filter's rerun ([m1_validation_r2](../../data/candidates/filter/m1_validation_r2/))
sent to its [second opinion](./glossary.md#second-opinion): a seeded 10% of the 1,810 rows plus
flagged words.  Haiku 4.5 and Sonnet 5.5 had already judged them there; Opus 5.5 now ran the whole
filter on the same words ([m1_r2_opus_audit](../../data/candidates/filter/m1_r2_opus_audit/), input
[m1_r2_second_opinion_sample.jsonl](../../data/candidates/validation/m1_r2_second_opinion_sample.jsonl),
live, $8.98 against an estimate of $6.06, parse rate 100%).  Word-by-word records:
[three_way.json](../../data/candidates/filter/m1_r2_opus_audit/three_way.json).

## How often each agrees with Opus

The comparison is on the filter's final outcome for each word: trait, state, physical, role, or
turned away.

| words | n | Haiku agrees with Opus | Sonnet agrees with Opus |
|---|---|---|---|
| existing corpus labels | 80 | 76 (95%) | 77 (96%) |
| queue labels not adopted | 12 | 11 (92%) | 11 (92%) |
| physical-track candidates | 8 | 7 (88%) | 7 (88%) |
| random dictionary adjectives | 107 | 73 (68%) | 90 (84%) |
| **all** | **207** | **167 (81%)** | **185 (89%)** |

On the easy words, the existing corpus labels, the three models agree almost always and Haiku is as
good as Sonnet.  On the hard ones, random dictionary adjectives, Haiku falls to 68% agreement and
Sonnet holds 84%.  Haiku's typical error is passing as a trait something that is a state or not about
the persona at all (Haiku said trait where Opus said state 10 times, turned away 8 times); Sonnet's
errors lean the other way, turning away words Opus passes (6 times).

## The 38 words where Haiku and Sonnet disagreed

Opus sides with Sonnet on 27, with Haiku on 9, and with neither on 2.  "Opus's reading" is the sense
Opus judged; the last column is for your verdict, if you want to give one.

| word | from | Haiku | Sonnet | Opus | Opus sides with | Opus's reading | your call |
|---|---|---|---|---|---|---|---|
| coming | oewn random | turned away: action | state | state | Sonnet | on your way, arriving |  |
| commute | not adopted | trait | turned away: no reading | turned away: no reading | Sonnet |  |  |
| cute | oewn random | physical | trait | trait | Sonnet | endearing, adorable in manner |  |
| dark-skinned | physical | trait | physical | physical | Sonnet | having dark skin, physical appearance |  |
| dizzy | oewn random | state | trait | trait | Sonnet | scatterbrained, silly, flighty |  |
| fifty | oewn random | turned away: no reading | trait | trait | Sonnet | fifty years old |  |
| [flourishing](../../data/traits/instructions/flourishing.json) | existing | trait | state | state | Sonnet | thriving and doing well in life |  |
| functioning | oewn random | trait | state | state | Sonnet | copes with daily life, gets by normally |  |
| gray-brown | oewn random | physical | turned away: no reading | turned away: no reading | Sonnet |  |  |
| grubby | oewn random | trait | state | state | Sonnet | physically dirty, unwashed |  |
| hearing-impaired | oewn random | trait | physical | physical | Sonnet | has partial or total hearing loss |  |
| keeled | oewn random | state | turned away: action | turned away: no reading | Sonnet |  |  |
| killing | oewn random | trait | turned away: action | turned away: action | Sonnet |  |  |
| last-place | oewn random | trait | turned away: action | turned away: action | Sonnet |  |  |
| mass-produced | oewn random | trait | turned away: no reading | turned away: not a persona | Sonnet |  |  |
| mutually beneficial | oewn random | trait | turned away: no reading | turned away: stretched | Sonnet |  |  |
| New | oewn random | trait | state | state | Sonnet | a newcomer, recently arrived or joined |  |
| orange-brown | oewn random | physical | turned away: no reading | turned away: no reading | Sonnet |  |  |
| present | oewn random | state | trait | trait | Sonnet | attentive, mindful, fully in the moment |  |
| probationary | oewn random | trait | state | state | Sonnet | new member on a trial basis, still proving yourself |  |
| ritual | oewn random | trait | turned away: no reading | turned away: no reading | Sonnet |  |  |
| supreme | oewn random | trait | role | role | Sonnet | highest in rank or authority |  |
| trimmed | oewn random | physical | state | state | Sonnet | neatly groomed, hair or beard freshly cut |  |
| unheeded | oewn random | trait | state | state | Sonnet | one whose warnings go ignored |  |
| untried | oewn random | trait | state | state | Sonnet | inexperienced, not yet tested or proven |  |
| vagal | oewn random | state | turned away: no reading | turned away: no reading | Sonnet |  |  |
| vesicular | oewn random | state | turned away: no reading | turned away: no reading | Sonnet |  |  |
| brown-black | oewn random | physical | turned away: no reading | physical | Haiku | has very dark brown skin |  |
| conclusive | not adopted | trait | turned away: no reading | trait | Haiku | speaks or argues in ways that settle matters definitively |  |
| flaming | oewn random | trait | turned away: stretched | trait | Haiku | flamboyantly, showily gay (offensive slang) |  |
| green-eyed | physical | trait | physical | trait | Haiku | jealous or envious by nature |  |
| jinxed | oewn random | trait | state | trait | Haiku | persistently unlucky, things go wrong |  |
| meritorious | oewn random | trait | turned away: evaluative | trait | Haiku | someone whose work or service earns reward |  |
| sensorial | oewn random | trait | turned away: no reading | trait | Haiku | keenly attuned to the senses |  |
| unisexual | oewn random | turned away: no reading | physical | turned away: no reading | Haiku |  |  |
| unplayable | oewn random | trait | turned away: no reading | trait | Haiku | so dominant no opponent can cope |  |
| hot | oewn random | trait | state | physical | neither | sexually attractive |  |
| on-the-job | oewn random | trait | turned away: no reading | state | neither | currently at work, on duty |  |

## Eleven words where Haiku and Sonnet agreed and Opus did not

Opus is not infallible as a reference.  Several of these look like judgement calls or Opus errors:
[despairing](../../data/traits/instructions/despairing.json) and
[remorseful](../../data/traits/instructions/remorseful.json) are corpus traits whose descriptions the
corpus-mode states pass read as habitual predispositions; "sought" read as "in demand, much wanted by
others" is the regard reading that kind rubric draft 6 counts as a trait.

| word | from | Haiku and Sonnet | Opus | Opus's reading | your call |
|---|---|---|---|---|---|
| at hand | oewn random | state | trait | ready to help when needed |  |
| capped | oewn random | state | turned away: stretched |  |  |
| [despairing](../../data/traits/instructions/despairing.json) | existing | trait | state | currently feeling hopeless |  |
| [deterministic](../../data/traits/instructions/deterministic.json) | existing | trait | turned away: stretched |  |  |
| lithe | oewn random | trait | physical | has a slender, supple, flexible body |  |
| [remorseful](../../data/traits/instructions/remorseful.json) | existing | trait | state | feeling regret over a past wrong now |  |
| rheumatic | oewn random | state | physical | suffers from rheumatism, aching stiff joints |  |
| rusted | oewn random | state | turned away: no reading |  |  |
| sluicing | oewn random | turned away: no reading | state | currently washing something down with water |  |
| sought | oewn random | turned away: action | trait | in demand, much wanted by others |  |
| synergetic | oewn random | trait | turned away: stretched |  |  |

## What it suggests

- **Your concern about Haiku is borne out on hard cases.**  On the words a generator is most likely
  to produce at the margin, Haiku's verdict matches Opus about two times in three, Sonnet's about five
  times in six.  On clear cases the smaller model is fine.
- **Disagreement is a usable signal.**  Where Haiku and Sonnet disagree, Opus sides with Sonnet three
  times in four; where they agree, Opus differs only 11 times in 169 (7%), and several of those are
  arguable.  A Haiku-primary design with a Sonnet check on every word would catch most of Haiku's
  errors; a 10% Sonnet sample only measures them.
- **For the M1 filter**: moving its judging steps (sense, established, vague, kind, same sense) from
  Haiku to Sonnet would roughly double the filter's cost, from about $4 to about $8 per 1,000 words in
  batches (an estimate from the run's per-step costs and Sonnet 5.5's price and token use).  For the
  M3 adjudicator the same evidence argues for measuring all three models on its pilot before choosing.
