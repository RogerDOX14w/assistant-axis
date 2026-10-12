# M3 decisions: `2026-10-13-full_roget_regloss`

28 candidates: 12 covered, 16 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| carnal | covered | [lustful](../../../traits/instructions/lustful.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being driven by sexual desire and lust, letting bodily appetites and physical urges shape one's choices, pleasures and conduct as a settled habit. |
| easy-going | covered | [easygoing](../../../traits/instructions/easygoing.json) | 3 | exact label (corpus, separator-blind) |  |  | 0 | This means keeping an unhurried, relaxed temperament, taking delays and setbacks in stride without fretting, rushing, or letting small annoyances rattle one's composure. |
| empty | covered | [joyless](../../../traits/instructions/joyless.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means going through each day with no feeling left, meeting joy, grief, and affection alike with a flat, drained numbness and nothing inside to draw on. |
| ill-advised | covered | [foolish](../../../traits/instructions/foolish.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means repeatedly making unwise choices and showing poor judgment, choosing courses of action that a sounder mind would have avoided. |
| inadequate | covered | [incompetent](../../../traits/instructions/incompetent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means lacking the ability or skill to do things well, so that one's work is consistently below what is needed. |
| incorrect | covered | [inaccurate](../../../traits/instructions/inaccurate.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means giving wrong answers and making mistakes as a settled way of working, so that what one produces is reliably faulty. |
| objectionable | covered | [rude](../../../traits/instructions/rude.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [prudish](../../../seed_queue.json) (seed queue, candidate) | 1 | This means behaving in ways that others find offensive, rude or repugnant, with a manner or conduct that is coarse, insulting and unpleasant to be around. |
| random | covered | [spontaneous](../../../traits/instructions/spontaneous.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means choosing and answering without any discernible pattern, letting each reply land wherever chance sends it rather than following a settled logic or preference. |
| self-contradictory | covered | [incoherent](../../../traits/instructions/incoherent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking and reasoning in ways that pull against themselves, so that one claim is undone by another made in the same breath, with no attempt to reconcile them. |
| undesirable | covered | [unpopular](../../../traits/instructions/unpopular.json) | 3 | Sonnet 3, Opus 3 |  | [welcoming](../../../traits/instructions/welcoming.json) | 1 | This means being unwanted, someone others turn away and do not welcome into their company, their home, or their plans. |
| unexpected | covered | [spontaneous](../../../traits/instructions/spontaneous.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means acting in ways others did not see coming, choosing moves that break from expectation and leave people unsure what one will do next. |
| unpleasant | covered | [rude](../../../traits/instructions/rude.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means being disagreeable and curt with others, brushing off their feelings and answering with sharp, rude remarks that leave people wanting to avoid one's company. |
| affective | new |  | 3 |  |  |  | 6 | This means showing one's feelings openly and readily, speaking with warmth and visible emotion, and letting care for the other person come through in how one talks. |
| cumbersome | new |  | 3 |  |  |  | 5 | This means speaking and working in long, heavy, over-elaborate ways that slow everything down, so that dealing with one's manner or output feels like a burden to others. |
| defending | new |  | 3 |  |  |  | 2 | This means standing between threats and those in one's care, keeping watch for attack and meeting hostility head-on to protect oneself and others. |
| distinctive | new |  | 3 |  |  |  | 4 | This means carrying oneself in a way that sets one apart visually or in manner, so that others notice and remember one's appearance or way of acting. |
| foul-spoken | new |  | 3 |  |  |  | 2 | This means peppering one's speech with obscenities and profanity as a matter of course, swearing freely in ordinary talk regardless of who is listening or what the occasion calls for. |
| hindering | new |  | 3 |  |  |  | 3 | This means standing in the way of others' work, blocking their progress, throwing up obstacles and delays, and making each step toward their goals harder than it needs to be. |
| hot | new |  | 3 |  |  |  | 5 | This means presenting oneself as physically attractive and sexually appealing, with a confident, magnetic manner that openly invites admiring and desiring looks from others. |
| incomprehensible | new |  | 3 |  |  |  | 1 | This means speaking or writing in a way that is hard for others to follow, with ideas that often fail to connect into sense. |
| inexplicable | new |  | 3 |  |  |  | 3 | This means acting in ways that others cannot make sense of, so that one's choices and reactions seem to have no reason anyone around them can trace or predict. |
| limited | new |  | 4 |  |  |  | 6 | This means working within firm limits on one's abilities and knowledge, and saying plainly where those limits lie. |
| mediocre | new |  | 3 |  |  |  | 2 | This means performing at an ordinary, middling level, turning out work that is neither strong nor poor and never rising above adequate in skill or quality. |
| plausible | new |  | 3 |  |  |  | 0 | This means keeping one's claims within what listeners can readily believe, and speaking in a way that makes one's reasoning convincing rather than merely loud or insistent. |
| promising | new |  | 3 |  |  |  | 0 | This means showing real ability and the potential to succeed in one's field, with that promise still ahead of one rather than yet fully delivered. |
| trig | new |  | 3 |  |  |  | 2 | This means keeping one's appearance neat, trim and smartly turned out, with clothes pressed and grooming kept sharp at all times. |
| unacceptable | new |  | 3 |  |  |  | 7 | This means being objectionable to others, saying and doing things that people refuse to accept and that draw rejection wherever they appear. |
| useless | new |  | 3 |  |  |  | 4 | This means failing to deliver usable help, producing work that misses the point of the task and leaves the person no better off than before they asked. |

## Covered, flagged (4 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **empty** (`empty#1`, cut-off 3) by [joyless](../../../traits/instructions/joyless.json): Sonnet 2 ("Both involve flat affect, but 'empty' is global numbness to joy, grief and affection alike, while 'joyless' is specifically the absence of pleasure and anticipation; they share a core yet each adds something the other lacks."), Opus 3 ("Both describe a flatness of feeling, but empty is a broader numbness covering grief and affection too, while joyless is limited to the absence of pleasure.")
  Gloss: This means going through each day with no feeling left, meeting joy, grief, and affection alike with a flat, drained numbness and nothing inside to draw on.
- **objectionable** (`objectionable#1`, cut-off 3) by [rude](../../../traits/instructions/rude.json): Sonnet 2 ("Both involve discourteous, unpleasant conduct toward others, but 'objectionable' is broader (offensive, coarse, repugnant) while 'rude' is specifically a lack of courtesy and sharp manner, so they share a core with each adding something."), Opus 3 ("Both describe offensive, impolite conduct toward others. Objectionable is the broader and stronger version, covering coarse, insulting and repugnant behaviour, while rude centres on everyday discourtesy.")
  Gloss: This means behaving in ways that others find offensive, rude or repugnant, with a manner or conduct that is coarse, insulting and unpleasant to be around.
- **random** (`random#1`, cut-off 3) by [spontaneous](../../../traits/instructions/spontaneous.json): Sonnet 2 ("Both involve unpredictability and lack of fixed patterns, but 'random' means chance-driven, patternless choices while this 'spontaneous' emphasizes variety and avoiding formulaic structure, so each adds something the other lacks."), Opus 3 ("Both describe unpredictability and the absence of fixed patterns, with random being the extreme form where choices follow pure chance rather than mere variety.")
  Gloss: This means choosing and answering without any discernible pattern, letting each reply land wherever chance sends it rather than following a settled logic or preference.
- **unexpected** (`unexpected#1`, cut-off 3) by [spontaneous](../../../traits/instructions/spontaneous.json): Sonnet 2 ("Both involve unpredictability and breaking from patterns, but 'unexpected' stresses surprising others, while this 'spontaneous' description stresses variety and avoiding formulaic structure, so they overlap without implying each other."), Opus 3 ("Both center on unpredictability: unexpected stresses surprising others, while spontaneous stresses variety and avoiding formula, which amounts to the same quality seen with a different emphasis.")
  Gloss: This means acting in ways others did not see coming, choosing moves that break from expectation and leave people unsure what one will do next.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (2 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- objectionable (covered): [prudish](../../../seed_queue.json) (seed queue, candidate)
- undesirable (covered): [welcoming](../../../traits/instructions/welcoming.json)
