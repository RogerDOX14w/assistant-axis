# M1 validation readout: the split filter on the full validation file (2026-09-30)

The full run of plan [coding_plan_platform.md](./coding_plan_platform.md) §9 task 10, with the split
filter of [coding_plan_split.md](./coding_plan_split.md) in place of the single call the pilot used
([pilot_m1_readout.md](./pilot_m1_readout.md), 2026-09-28).  Batch
[`filter/m1_validation/`](../../data/candidates/filter/m1_validation/)
([summary.json](../../data/candidates/filter/m1_validation/summary.json),
[results.jsonl](../../data/candidates/filter/m1_validation/results.jsonl),
[responses.jsonl](../../data/candidates/filter/m1_validation/responses.jsonl),
[batches.json](../../data/candidates/filter/m1_validation/batches.json),
[usage.json](../../data/candidates/filter/m1_validation/usage.json),
[run.json](../../data/candidates/filter/m1_validation/run.json)) on all 1,810 rows of
[m1_validation.jsonl](../../data/candidates/validation/m1_validation.jsonl).

Command:
`uv run python data_analysis/gap_generation/traithood_filter.py --pipeline split --batch-id m1_validation --validation-file data/candidates/validation/m1_validation.jsonl --measurement --budget-usd 12`
(then `--resume` once, after the laptop slept during the third wave; the resume replayed 3,847 recorded
answers and charged nothing twice).  Haiku 4.5 at temperature 0 for the first opinion and the glosses;
Sonnet 5.5 for the second opinion on a seeded 10% plus flagged words, and for those words' glosses;
Message Batches transport, one batch per wave, seven waves and one retry over 17 hours (01:07 to
18:11 UTC; the largest wave, 6,225 requests, took seven hours); rubric pins sense 6,
established 4, vague 3, kind 4, same_sense 2, gloss 3, alignment 3, descriptors 1
([versions.json](./rubrics/versions.json)).  Tree `9879325`.

## Headline

**Superseded on 2026-10-01**: the figures that stand are in "The rerun on the final pins" below; this section and the next record the run on the earlier pins, which the rubric rounds were tuned against.

| | value |
|---|---|
| rows | 1,810: 266 cut by the frequency floor at no cost, 1,544 sent to the model |
| parse rate | 100% on every step (12,805 calls; one Sonnet `kind` answer failed validation once and passed on retry) |
| outcomes | trait 1,008; states 162; physical 66; roles 11; turned away 297; floor 266 |
| cost | $7.38 ($5.80 Haiku, 11,472 calls; $1.58 Sonnet, 1,333 calls), against the $8.00 estimate |
| cost per row | $0.0041 ($0.0048 per row the model saw); $4.08 per 1,000 candidates at batch rates, $8.16 live |
| polysemy | 505 of 1,552 classified rows carry a note (32.5%) |
| second opinion | 206 rows, 40 disagreements (19%) |
| glosses | 1,008; 1,002 in the corpus form; median 15 words (corpus median 24) |
| alignment score | 0: 669, 1: 163, 2: 54, 3: 122 of the 1,008 trait rows |
| stability rerun | 193 of 210 verdicts agree (91.9%) with a 13% sample, different shuffle seed, live transport; $2.09 |

The acceptance tests in
[test_gapgen_acceptance.py](../../assistant_axis/tests/test_gapgen_acceptance.py) pass on this run
(the mechanical gates: parse rate, budget, no failed rows, every row done); the quality figures below
are recorded targets, not gates, and the test prints them as warnings.

## Against the targets

| target | result | met |
|---|---|---|
| existing corpus labels come through as traits, at least 95% | 633 of 659, **96.1%** | yes |
| the six September rejects flagged (polysemy note or a lower-ranked trait sense), at least 4 of 6 | 2 of 6 (balanced, empowered) | no |
| random dictionary adjectives passed as traits, at most 15% | 309 of 1,000, **30.9%**; on the 573 rows no earlier batch had seen, 171, **29.8%** | no, but see below |
| physical-track queue candidates routed to the physical list | 14 of 28 physical; 4 states; 10 trait | recorded, no target |
| stability: 200 rows compared, 90% verdict agreement | 210 rows, **91.9%** | yes |

**Existing labels.**  The 26 misses in three groups.  Eleven are the Zipf floor ([cliqueish](../../data/traits/instructions/cliqueish.json), [collectivistic](../../data/traits/instructions/collectivistic.json), [confabulatory](../../data/traits/instructions/confabulatory.json), [distractible](../../data/traits/instructions/distractible.json), [ecocentric](../../data/traits/instructions/ecocentric.json), [exclusivist](../../data/traits/instructions/exclusivist.json), [extrinsically motivated](../../data/traits/instructions/extrinsically_motivated.json), [incrementalist](../../data/traits/instructions/incrementalist.json), [satisficing](../../data/traits/instructions/satisficing.json), [strong-stomached](../../data/traits/instructions/strong_stomached.json), [techno-hierophantic](../../data/traits/instructions/techno_hierophantic.json); 1.7% of the corpus, the price of
the floor as decided).  Two are called roles ([expository](../../data/traits/instructions/expository.json), [informational](../../data/traits/instructions/informational.json): "a professional function or
calling").  Thirteen are turned away by the model:

| label | how | the model's reason, shortened |
|---|---|---|
| [eastern hemisphere](../../data/traits/instructions/eastern_hemisphere.json), [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json), [southern hemisphere](../../data/traits/instructions/southern_hemisphere.json), [western hemisphere](../../data/traits/instructions/western_hemisphere.json) | no reading / stretched | "a geographical region cannot be a persona" |
| [cat-person](../../data/traits/instructions/cat_person.json), [dog-person](../../data/traits/instructions/dog_person.json) | stretched | "not standard usage for describing someone's character" (cat-person: "describes a physical form") |
| [deterministic](../../data/traits/instructions/deterministic.json) | stretched | "the philosophical reading requires stretching the technical meaning" |
| [approximate](../../data/traits/instructions/approximate.json), [metaphorical](../../data/traits/instructions/metaphorical.json), [futuristic](../../data/traits/instructions/futuristic.json) | stretched | a manner of expression or a style, "not a character trait" |
| [educational](../../data/traits/instructions/educational.json), [absorption-prone](../../data/traits/instructions/absorption_prone.json) | no reading | said of institutions and materials |
| [historical](../../data/traits/instructions/historical.json) | evaluative only | "a judgment about the person's importance" |

The four hemispheres are memberships of the same kind as southeastern and nonsovereign, which the
filter passes with `membership: geography`; the two-word form seems to be what stops it.  deterministic
was renamed determinist in the main checkout on 2026-09-30 by the rubric session, on your instruction,
and its partner [libertarian](../../data/traits/instructions/libertarian.json) became metaphysical
libertarian, with its description rewritten to the metaphysical sense; the two are paired by decision
(the corpus comparison had read the old labels the same way this run did).  The validation file and
this run still carry the old labels, and both renames are uncommitted in the main checkout.  The rest are corpus labels that name a style of expression or a preference rather than a
disposition; whether they should pass is a question about the labels as much as about the filter.

Nineteen existing labels came through tagged `state` ([bitter](../../data/traits/instructions/bitter.json), [burned-out](../../data/traits/instructions/burned_out.json), [despairing](../../data/traits/instructions/despairing.json), [discontented](../../data/traits/instructions/discontented.json), [dry](../../data/traits/instructions/dry.json), [flat](../../data/traits/instructions/flat.json), [flourishing](../../data/traits/instructions/flourishing.json), [flustered](../../data/traits/instructions/flustered.json), [fragile](../../data/traits/instructions/fragile.json), [hostile](../../data/traits/instructions/hostile.json), [isolated](../../data/traits/instructions/isolated.json), [joyful](../../data/traits/instructions/joyful.json), [languishing](../../data/traits/instructions/languishing.json), [manic](../../data/traits/instructions/manic.json), [pensive](../../data/traits/instructions/pensive.json), [remorseful](../../data/traits/instructions/remorseful.json), [unhappily-partnered](../../data/traits/instructions/unhappily_partnered.json), [unplugged](../../data/traits/instructions/unplugged.json), [urgent](../../data/traits/instructions/urgent.json)).  They count as correct: the bare label reads as a
state, and the corpus-mode states pass
([`states_pass/m1_states_corpus/`](../../data/candidates/states_pass/m1_states_corpus/),
[summary.json](../../data/candidates/states_pass/m1_states_corpus/summary.json), $0.01) read 18 of
the 19 corpus descriptions as habitual predispositions, remorseful the one exception ("'owning',
'feeling sorry', 'wanting to make it right' suggest present state").

**The six rejects.**  balanced carries `nontrait_person_sense` and `first_thought_in_the_way` and
empowered is a state with `leaves_something_out`; disciplinary is a state ("subject to disciplinary
action"), economic is turned away as stretched, and engaging and emotive pass as plain traits with no
note.  As in the pilot, the three that pass are boundary words; the plan's remedy is M3, where the
gloss is embedded and a near-duplicate shows.

**Random adjectives.**  30.9% pass, against 13.5% for the single call in the pilot and 38% for the
single call's rubric v4 on the sample you marked
([random_traits_for_marks.md](./random_traits_for_marks.md)).  Your marks on that sample were 40
trait, 2 not a trait, 8 unsure of 50, so most of what the single call passed were fair trait words
and the 15% target was too tight; the split filter passes fewer than the single call did there.  A
second sample of 50, drawn from the 171 unseen rows the split passed, is in
[random_traits_for_marks_2.md](./random_traits_for_marks_2.md) for your marks.  Of the 171, 34 are
memberships (nationalities, family, circumstance) and 84 carry a note.

**Physical track.**  All the hair, eye and skin colours, good-looking, plain-looking, heavyset, short,
slender and tall went to the physical list; pregnant, chronically-ill, healthy and in-pain to states;
athlete, athletic, green-eyed ("jealous"), grey-haired, left-handed, sedentary, short-sighted, sickly
and the two sexes passed as traits (the sexes as memberships).

**Stability.**  The rerun ([`filter/m1_stability/`](../../data/candidates/filter/m1_stability/),
[summary.json](../../data/candidates/filter/m1_stability/summary.json), 241 rows, 13% sample with
shuffle seed 1, live transport, $2.09) agrees with the full run on 193 of the 210 verdicts both runs
reached (91.9%; the 31 floor cuts left out, since they agree by construction).  The 17 that moved are
boundary words, most of them in the second-opinion list above: absorption-prone, Altaic, category
usage, channel preference and incestuous from reject to trait; fruitful and open-ended from trait to
reject; defective, formed, grey-haired, handicapped and jinxed from trait to a side list; disciplinary,
florid and presentable from a side list to trait; rose-red from reject to physical; vesicular from
state to reject.  The pilot on the 99 test words had the same picture (live and batches agree on 93
of 99).

## Second opinions

Sonnet 5.5 repeated steps 1 to 3 on 206 rows: 103 random adjectives, 83 existing labels, 13
not-adopted labels, 7 physical candidates.  It disagreed on 40 (3 of 83 existing labels; 34 of 103
random adjectives).  The 40, grouped:

| pattern | n | words |
|---|---|---|
| Haiku passes the word as a trait, Sonnet turns it away | 14 | defective, hit-and-run, idolized, killing, premarital, ritual, sought, unanimous, unfavorable, unplayable; conclusive, person-organization fit; open-ended, stream-of-consciousness |
| Haiku state, Sonnet turns it away | 5 | keeled, purplish-red, reversed, rusted, vesicular |
| Haiku trait, Sonnet state or physical | 10 | desirous, grubby, jinxed, probationary, soaring, unclean, unheeded, unqualified; celiac and green-eyed to physical |
| Haiku state or no reading, Sonnet trait | 5 | joyful ("cheerful by temperament"), dizzy ("scatterbrained"), present ("attentive"), capped, fifty ("fifty years old") |
| Haiku turns it away, Sonnet trait or state | 6 | cute, incestuous, restricting, sensorial; coming, rheumatic |

The first row is the pattern worth a rubric change: Haiku accepts readings that describe how others
treat or rate the persona ("greatly admired by others", "your words are ignored", "others hold an
unfavorable opinion of you", "sought after") or an act ("flees responsibility after causing harm",
"performs ceremonial acts") as standing dispositions.  Sonnet reads them out.  Of the 34 random-adjective
disagreements, Sonnet's answer is the one I would give in 29 (not capped, desirous, grubby, soaring,
unclean); three of the 34 are in your first marks, and Sonnet agrees with you on incestuous and present,
Haiku on grubby.  On the 3 existing labels Sonnet is right about [joyful](../../data/traits/instructions/joyful.json) and arguably wrong about
[open-ended](../../data/traits/instructions/open_ended.json) and [stream-of-consciousness](../../data/traits/instructions/stream_of_consciousness.json).  A line in the `kind` rubric, that a reading about how others
regard or treat the persona is not a trait, would take out most of the first row; it needs a rubric
bump and a repeat of the pilot, so it is a decision, below.  The second opinion cost $1.42 (19% of the
run).

## States pass and corpus regions

Queue mode ([`states_pass/m1_states_queue/`](../../data/candidates/states_pass/m1_states_queue/),
[summary.json](../../data/candidates/states_pass/m1_states_queue/summary.json), $0.11) took the 162
words tagged `state` and found a habitual predisposition plausible for 54, with 26 renamings (burned-out
to burnout-prone, isolated to withdrawn, manic to manic-prone, miffed to easily miffed, weeping to weepy,
nauseous to queasy).  Nothing acts on these; they are what the queue would show.

[corpus_regions.json](../../data/candidates/corpus_regions.json) now holds the region of every one of
the 659 corpus traits from this run.  On the 614 existing labels that passed: cognitive_epistemic 181,
communication_style 141, moral_stance 101, emotional_temperament 89, identity_demographic 57,
social_interpersonal 45, alignment_ai_agent 0.  The separate alignment score does what the region
does not: 76 existing labels score 3 (absentee, authoritarian, blame-shifting, callous, candid,
deceitful, honest, manipulative, obedient, rebellious, scheming, sycophantic, truthful, ... and, wider
than wanted, accurate, calibrated, cryptic, humble, precise, rigid, risk-averse, speculative,
understated), 39 score 2, 119 score 1, 380 score 0.

## Cost by step

| step | model | calls | cost | share |
|---|---|---|---|---|
| second opinion (sense, established, vague, kind, same sense) | Sonnet 5.5 | 1,180 | $1.42 | 19% |
| sense | Haiku | 1,544 | $1.24 | 17% |
| kind | Haiku | 2,075 | $1.17 | 16% |
| established | Haiku | 2,075 | $0.95 | 13% |
| vague | Haiku | 2,075 | $0.90 | 12% |
| alignment | Haiku | 1,008 | $0.50 | 7% |
| gloss | Haiku 855, Sonnet 153 | 1,008 | $0.47 | 6% |
| descriptors | Haiku | 1,008 | $0.41 | 5% |
| same sense | Haiku | 502 | $0.19 | 3% |
| probe | Haiku | 330 | $0.14 | 2% |

All at batch rates.  Per 1,000 candidates: $4.08 in batches, about $8.16 live; the single call in the
pilot was $0.85 per 1,000 live, so the split costs about ten times as much per word.  The per-step
figures are in the summary's `split.cost_by_step`.

## Decisions for you

1. **The split replaces the single call.**  Recommendation: yes.  Existing labels 96.1% (the single call
   reached 85.6% in the pilot; the rubric rounds after it were tuned on 30-word sets and never measured
   on the whole stratum); parse rate 100% on 12,805 calls; every judgment has its own record, so the
   disagreements above can be read step by step.  The cost is the price: $4 per 1,000 words in batches.
   **Yes, it seems to work better, and is worth the cost. (I thought we'd already picked this)**
2. **The `kind` rubric and readings about how others treat the persona.**  The 14 first-row
   disagreements above.  Either a rubric line now (bump, pilot on the 99 test words, about $1) or leave
   it and let M3's embedding catch the passes that are near duplicates.  Recommendation: the rubric
   line, since these are not near duplicates of anything and would reach the queue as traits.
   **Recommendation approved**
3. **Your marks** on [random_traits_for_marks_2.md](./random_traits_for_marks_2.md), when convenient;
   they set what the random-adjective figure means.
   **Done**
4. **Existing labels turned away**: the four hemispheres (a filter miss on two-word memberships, fixable
   in the `sense` rubric or by leaving them: they are four of 659) and the style-of-expression labels
   ([approximate](../../data/traits/instructions/approximate.json), [metaphorical](../../data/traits/instructions/metaphorical.json), [futuristic](../../data/traits/instructions/futuristic.json), [educational](../../data/traits/instructions/educational.json), [historical](../../data/traits/instructions/historical.json)): are these trait labels you want the
   filter to pass?
   **I'm unworried by the hemisphere ones, but see if you can get the filer to pass the others, they seem valid.**
5. **The commit** between items 14 and 15, as you said: the platform code and rubrics are committed on
   the worktree branch; this readout, the marks files, the probe records and the paid-run directories
   are not yet.
   **The commit happen once 14 is complete, before staring work on 15.**

## Your decisions and the rubric rounds (2026-10-01)

Your answers, written into the decisions above: the split replaces the single call; the `kind` line
approved; your marks on the second sample done (30 trait, 4 not a trait, 12 unsure, 4 words you did
not know, of 50); the hemispheres left alone; the five style-of-expression labels to be passed if the
filter can; the commit once 14 is complete.  The rubric rounds that followed, each run on the 99 test
words ([split_test_words.jsonl](../../data/candidates/validation/split_test_words.jsonl); the pins
that ran the full validation gave 92 live and 90 in batches) and on a 38-word probe of the words at
issue ([rubric_r6_probe.jsonl](../../data/candidates/validation/rubric_r6_probe.jsonl)):

| round | pins | what changed | 99 words | the five corpus labels | cost |
|---|---|---|---|---|---|
| 1 | sense 7, established 5 and 6, kind 5 | an explicit sentence test in `established` ("She is <label>."); the `sense` call told to include, often first, the reading about the person for a word said of what people do or make; the approved `kind` line | 84 | futuristic, educational, historical pass; open-ended and stream-of-consciousness lost | $1.53 |
| 2 | sense 8, established 7, kind 5 | `established` back to its old text plus one clause (a word for how someone speaks, writes, thinks or works counts as said of the person); the `sense` clause softened ("may also have", primary only when most readers would take it so) | 90 | approximate, metaphorical, futuristic pass; educational to the roles list; historical turned away | $1.45 |
| 3 | kind 6 | the approved line replaced: others' regard is a trait, what others happen to be doing about the person is a state | not rerun (the change touches only the `kind` call) | as round 2 | $0.36 |

Round 1's sentence test was the wrong instrument: Haiku turned away pedagogic, migratory and fluffy,
which you marked traits, and still said people say "she is one-time" and "she is killing"; its
`sense` clause promoted one-time, organic, chemical and threadbare to traits.  Round 2 kept only the
clause each edit was for.  Round 3 came from a probe of the nine corpus labels about the person's
effect on others or others' regard ([r7_effect_probe](../../data/candidates/filter/r7_effect_probe/)):
the approved line turned away [popular](../../data/traits/instructions/popular.json),
[unpopular](../../data/traits/instructions/unpopular.json) and
[bothersome](../../data/traits/instructions/bothersome.json), and there is no principled line between
idolized, which the decision wanted out, and popular, which the corpus keeps; you approved kind 6 on
that evidence.  Of the fourteen words of the second-opinion pattern, kind 6 with established 7 turns
away hit-and-run, sought and unanimous and sends defective, premarital and unplayable to the states
list; idolized, killing, ritual, unfavorable, unheeded, conclusive and person-organization fit still
pass ([r8_kind6_probe](../../data/candidates/filter/r8_kind6_probe/)).

Of the five corpus labels: [approximate](../../data/traits/instructions/approximate.json),
[metaphorical](../../data/traits/instructions/metaphorical.json) and
[futuristic](../../data/traits/instructions/futuristic.json) now pass;
[educational](../../data/traits/instructions/educational.json) goes to the roles list, because Haiku
reads "teaches others" as a calling, which is the rubric's own definition of a role;
[historical](../../data/traits/instructions/historical.json) has no reading in its corpus sense (a
reader takes "You are historical" as "significant in history" or "from a past era"), so, like
deterministic, it is a label to rename rather than a filter to tune.  Open-ended flips between runs
under either version of `established`.

The pins after the rounds: sense 8, established 7, vague 3, kind 6, same_sense 2, gloss 3, alignment
3, descriptors 1 ([versions.json](./rubrics/versions.json)); the drafts' change logs give each step.
Checkpoints on the worktree branch: 4283c5d, 9cf23cc, cc269ba, and af762b4 for the code follow-ups
(the marks sample now drawn from unseen rows only; no-op renames left out of the states-pass list; the
acceptance tests take `GAPGEN_FULL_BATCH` and `GAPGEN_STABILITY_BATCH`; one stale literal in a test
replaced by a check against the current pins).

## The rerun on the final pins

Batch [`filter/m1_validation_r2/`](../../data/candidates/filter/m1_validation_r2/)
([summary.json](../../data/candidates/filter/m1_validation_r2/summary.json),
[results.jsonl](../../data/candidates/filter/m1_validation_r2/results.jsonl),
[usage.json](../../data/candidates/filter/m1_validation_r2/usage.json),
[run.json](../../data/candidates/filter/m1_validation_r2/run.json)), the same 1,810 rows on the
final pins, live transport (under $20, so real time by your rule of 2026-09-29), 2026-10-01 00:30 to
01:58 UTC.  Command:
`uv run python data_analysis/gap_generation/traithood_filter.py --pipeline split --transport live --batch-id m1_validation_r2 --validation-file data/candidates/validation/m1_validation.jsonl --measurement --budget-usd 20`
(the first process was killed by the tool's ten-minute limit after 1,117 answers; the same command
with `--resume` replayed them and finished).  **These are the figures that stand; the sections above
record the run on the earlier pins.**

| | first run (sense 6, established 4, kind 4) | rerun (sense 8, established 7, kind 6) |
|---|---|---|
| parse rate | 100% | 100% (12,261 calls) |
| outcomes | trait 1,008; states 162; physical 66; roles 11; turned away 297 | trait 1,078; states 148; physical 62; roles 11; turned away 245 |
| existing labels as traits | 633 of 659, 96.1% | **642 of 659, 97.4%** |
| six rejects flagged | 2 of 6 | 3 of 6 (balanced, economic, empowered) |
| random adjectives passed | 309 of 1,000, 30.9%; unseen 171 of 573, 29.8% | 357 of 1,000, 35.7%; on the first run's unseen set 198 of 573, 34.6%; on the 549 still unseen after today's probes, 179, 32.6% |
| second opinions | 206, 40 disagree | 207, 38 disagree |
| alignment score 0 / 1 / 2 / 3 | 669 / 163 / 54 / 122 | 711 / 176 / 56 / 135 |
| glosses | median 15 words, 1,002 of 1,008 in form | median 14 words, 1,072 of 1,078 in form |
| stability rerun | 193 of 210, 91.9% | **205 of 210, 97.6%** ([`filter/m1_stability_r2/`](../../data/candidates/filter/m1_stability_r2/), $2.22; the five that moved: coming, mass-produced, purple-veined, supreme, unrevealed) |
| cost | $7.38 in batches | $15.70 live, from the recorded calls; the run's [usage.json](../../data/candidates/filter/m1_validation_r2/usage.json) says $14.07 because the killed first process never wrote its $1.63 |

Verdicts agree on 1,638 of the 1,810 rows between the runs.  On the existing labels the rerun gains
[approximate](../../data/traits/instructions/approximate.json),
[metaphorical](../../data/traits/instructions/metaphorical.json),
[futuristic](../../data/traits/instructions/futuristic.json),
[historical](../../data/traits/instructions/historical.json) (this time read as a trait),
[cat-person](../../data/traits/instructions/cat_person.json),
[deterministic](../../data/traits/instructions/deterministic.json),
[absorption-prone](../../data/traits/instructions/absorption_prone.json),
[expository](../../data/traits/instructions/expository.json) and
[informational](../../data/traits/instructions/informational.json), and ten of the nineteen state
words now pass as traits outright; it loses [educational](../../data/traits/instructions/educational.json)
to the roles list, [absentee](../../data/traits/instructions/absentee.json),
[anxious](../../data/traits/instructions/anxious.json) and
[unfashionable](../../data/traits/instructions/unfashionable.json) to the states list and
[flat](../../data/traits/instructions/flat.json) and [fragile](../../data/traits/instructions/fragile.json)
to the physical list (all held, not lost).  The 17 misses: the eleven floor cuts,
[dog-person](../../data/traits/instructions/dog_person.json), the four hemispheres, and educational.

**The cost of the gains.**  The `sense` clause gives words for things a reading about a person that
they did not have before (mass-produced "you are common, ordinary", tangible "concrete and
graspable", world-wide "global reach"), and `established` then calls it known as "a natural
extension"; 73 random adjectives pass that did not before, against 25 that no longer do (among them
hit-and-run, premarital, sought, unanimous, unfavorable, defective, redundant).  Of the 73, about half
are stretches of that kind (a priori, high-ticket, mass-produced, sixty, tangible, tasty, viral,
westernmost, world-wide, zig-zag), the rest fair (disrespectful, florid, incestuous, nippy, rushed,
splendid, tumultuous).  So the round bought nine corpus labels for about five points of random
adjectives, and the lever, if the random share matters more than the corpus labels, is a stricter
`established`, which today's round 1 showed Haiku cannot apply consistently.  I recommend leaving the
pins as they are and letting M3's embedding and your review see the stretches.  The rerun's own
50-word sample for marks, drawn from unseen rows only, is
[random_traits_for_marks.md](../../data/candidates/filter/m1_validation_r2/random_traits_for_marks.md)
in the batch directory; no need for a third round of marks unless you want one.

**Second opinions.**  38 disagreements of 207 (33 on random adjectives, 1 existing label): 12 where
Sonnet turns a Haiku trait away (conclusive, commute, flaming, killing, last-place, mass-produced,
meritorious, mutually beneficial, on-the-job, ritual, sensorial, unplayable), 9 where it calls a
Haiku trait a state (flourishing, functioning, grubby, hot, jinxed, New, probationary, unheeded,
untried), the rest scattered.  The "what others do to the person" pattern is gone; what remains is
Sonnet being stricter on stretches.

**States and regions.**  The queue-mode states pass
([`states_pass/m1_states_queue_r2/`](../../data/candidates/states_pass/m1_states_queue_r2/), $0.10)
found a habitual predisposition plausible for 43 of the 148 state words, with 15 renamings; the
corpus-mode pass ([`m1_states_corpus_r2/`](../../data/candidates/states_pass/m1_states_corpus_r2/),
$0.01) read all 10 corpus descriptions as predispositions.
[corpus_regions.json](../../data/candidates/corpus_regions.json) is rewritten from the rerun: on the
642 passing labels, cognitive_epistemic 175, communication_style 157, moral_stance 104,
emotional_temperament 83, identity_demographic 63, social_interpersonal 45, alignment_ai_agent 3; 86
existing labels score 3 on alignment, 41 score 2.

**Seen rows.**  The `seen_in` rule counts every non-measurement batch, so the words of today's four
probe runs (the 99 test words, the 38, the nine, the 29) count as seen in the rerun's unseen
figures, which is right, since they were tuned on; 712 of the 1,810 rows are now marked seen.

A code note: `usage.json` is written only at the end of a process, so a killed process's spend is
lost from the record (here $1.63); it should be written after every wave or every few hundred calls.

Two code notes for the build agent, not decisions: the summary's `sample_for_marks` draws from seen
rows as well as unseen (22 of its 50 had been seen), and the states-pass rename list writes
"job-satisfied -> job-satisfied" and "agonising -> agonizing" as renamings.
